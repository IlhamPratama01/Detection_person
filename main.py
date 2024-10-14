import os
import torch
import cv2
import supervision as sv
import sqlite3
import datetime
import pytz
from flask import Flask, request, jsonify, send_file, url_for
from ultralytics import YOLO
from io import BytesIO
import numpy as np
from flasgger import Swagger
from flasgger.utils import swag_from
import subprocess
from flask_cors import CORS
import glob

app = Flask(__name__)
swagger = Swagger(app)
CORS(app)

# Akses folder untuk menyimpan video hasil
OUTPUT_FOLDER = 'output_videos'
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# Mengatur device untuk menggunakan GPU jika tersedia
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Inisialisasi model YOLO
model = YOLO('best.pt')

# Membuat koneksi ke SQLite
def setup_database():
    conn = sqlite3.connect('detections.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS person (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        person_count INTEGER,
        head_count INTEGER,           
        created_at DATETIME DEFAULT (DATETIME('now', 'localtime'))
    )''')
    conn.commit()
    return conn, cursor

# Fungsi untuk mendeteksi objek
def detect_objects(frame):
    results = model(frame)[0]
    detections = sv.Detections.from_ultralytics(results)
    person_count = sum(1 for name in detections.data['class_name'] if name == 'Person')
    head_count = sum(1 for name in detections.data['class_name'] if name == 'Head')
    return detections, person_count, head_count

# Fungsi untuk menyimpan hasil deteksi ke database
def save_detection(cursor, person_count, head_count):
    indonesia_tz = pytz.timezone('Asia/Jakarta')
    timestamp = datetime.datetime.now(indonesia_tz)
    cursor.execute('''INSERT INTO person (person_count, head_count) VALUES (?, ?)''', (person_count, head_count))
    cursor.connection.commit()

# Fungsi untuk menambahkan anotasi pada frame
def annotate_frame(frame, detections, person_count, head_count):
    bounding_box_annotator = sv.BoundingBoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    # Anotasi bounding box dan label
    annotated_frame = bounding_box_annotator.annotate(scene=frame, detections=detections)
    annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections)

    frame_height, frame_width, _ = frame.shape
    text = f'Person: {person_count}'
    text_head = f'Head: {head_count}'
    
    text_x = frame_width - 200
    text_y_person = 30
    text_y_head = 60

    cv2.putText(annotated_frame, text, (text_x, text_y_person), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(annotated_frame, text_head, (text_x, text_y_head), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    if person_count > 15:
        status_text = 'Crowded'
        text_color = (0, 0, 255)
    else:
        status_text = 'Uncrowded'
        text_color = (0, 255, 0)

    text_y_status = text_y_person + 70
    cv2.putText(annotated_frame, status_text, (text_x, text_y_status), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)

    return annotated_frame

# Endpoint untuk upload dan anotasi video
@swag_from({
    'summary': 'Upload video untuk dianotasi',
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'File video (mp4, avi, mov)'
        }
    ],
    'responses': {
        200: {
            'description': 'Video berhasil dianotasi dan dikembalikan',
            'content': {
                'video/mp4': {}
            }
        },
        400: {
            'description': 'Invalid file type or other error'
        }
    }
})
# Endpoint POST untuk upload dan proses video
@app.route('/upload_video/', methods=['POST'])
def upload_video():
    conn, cursor = setup_database()
    file = request.files.get('file')

    if not file:
        return jsonify({"detail": "No file uploaded"}), 400

    # Pastikan file yang diunggah adalah video
    if file.content_type not in ["video/mp4", "video/avi", "video/mov"]:
        return jsonify({"detail": "Invalid file type. Only mp4, avi, or mov allowed."}), 400

    # Hapus video lama sebelum menyimpan video baru
    old_videos = glob.glob(os.path.join(OUTPUT_FOLDER, "final_*.mp4"))
    for old_video in old_videos:
        os.remove(old_video)  # Hapus video lama

    # Simpan file video sementara ke disk
    video_path = os.path.join(OUTPUT_FOLDER, f"temp_{file.filename}")
    file.save(video_path)

    # Membuka video dan proses anotasi
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return jsonify({"detail": "Error opening video file"}), 400

    output_frames = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 480))
        detections, person_count, head_count = detect_objects(frame)  # Fungsi deteksi
        save_detection(cursor, person_count, head_count)
        annotated_frame = annotate_frame(frame, detections, person_count, head_count)  # Fungsi anotasi
        output_frames.append(annotated_frame)

    cap.release()
    conn.close()

    # Hapus file video sementara
    os.remove(video_path)

    # Gabungkan frame yang dianotasi menjadi video kembali
    height, width, _ = output_frames[0].shape
    output_video_path = os.path.join(OUTPUT_FOLDER, f"output_{file.filename}")
    output = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), 20, (width, height))

    for frame in output_frames:
        output.write(frame)

    output.release()

    # Konversi video menggunakan FFmpeg
    final_video_path = os.path.join(OUTPUT_FOLDER, f'final_{file.filename}')
    ffmpeg_command = [
        'ffmpeg',
        '-i', output_video_path,
        '-vcodec', 'libx264',
        '-acodec', 'aac',
        final_video_path
    ]
    subprocess.run(ffmpeg_command)

    # Hapus video sementara setelah konversi
    os.remove(output_video_path)

    # Kembalikan URL video hasil anotasi
    video_url = url_for('get_processed_video', filename=f'final_{file.filename}', _external=True)
    return jsonify({"video_url": video_url})

@app.route('/processed_videos/<filename>', methods=['GET'])
@swag_from({
    'summary': 'Get processed video by filename',
    'description': 'Retrieve a processed video file by providing the filename.',
    'parameters': [
        {
            'name': 'filename',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Name of the processed video file to retrieve (e.g., final_video.mp4)'
        }
    ],
    'responses': {
        200: {
            'description': 'The processed video file',
            'content': {
                'video/mp4': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        404: {
            'description': 'File not found',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'File not found'
                    }
                }
            }
        }
    }
})

def get_processed_video(filename):
    
    output_folder = 'output_videos'
    video_path = os.path.join(output_folder, filename)
    print(f"Looking for video at: {video_path}")  # Log path

    if os.path.exists(video_path):
        print("File found, sending file...")
        return send_file(video_path, mimetype='video/mp4')
    else:
        print("File not found!")
        return jsonify({"detail": "File not found"}), 404

# Endpoint untuk upload dan anotasi gambar
@swag_from({
    'responses': {
        200: {
            'description': 'Gambar berhasil dianotasi',
            'content': {
                'image/jpeg': {}
            }
        },
        400: {
            'description': 'Invalid file type or other error'
        }
    }
})
@app.route("/upload_image/", methods=['POST'])
def upload_image():
    file = request.files.get('file')

    # Pastikan file yang diunggah adalah gambar
    if file.content_type not in ["image/jpeg", "image/png"]:
        return jsonify({"detail": "Invalid file type. Only jpg and png allowed."}), 400

    # Membaca gambar dari UploadFile
    image_bytes = file.read()
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({"detail": "Error reading image file"}), 400

    # Resize gambar agar sesuai
    img = cv2.resize(img, (640, 480))

    # Deteksi objek dalam gambar
    detections, person_count, head_count = detect_objects(img)

    # Anotasi gambar
    annotated_image = annotate_frame(img, detections, person_count, head_count)

    # Simpan gambar yang dianotasi ke buffer
    _, img_encoded = cv2.imencode('.jpg', annotated_image)
    img_bytes = BytesIO(img_encoded.tobytes())

    # Kembalikan gambar yang dianotasi
    return send_file(img_bytes, mimetype="image/jpeg")

# Menjalankan server Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)