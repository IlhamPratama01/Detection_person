import os
import torch
import cv2
import supervision as sv
import sqlite3
import datetime
import pytz
from flask import Flask, request, jsonify, Response, send_from_directory
from ultralytics import YOLO
from flasgger import Swagger, swag_from
from flask_cors import CORS
from vidgear.gears import VideoGear, WriteGear
import threading
import mimetypes

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
    return conn

# Fungsi untuk mendeteksi objek
def detect_objects(frame):
    results = model(frame)[0]
    detections = sv.Detections.from_ultralytics(results)
    person_count = sum(1 for name in detections.data['class_name'] if name == 'Person')
    head_count = sum(1 for name in detections.data['class_name'] if name == 'Head')
    return detections, person_count, head_count

# Fungsi untuk menyimpan hasil deteksi ke database
def save_detection(cursor, person_count, head_count):
    cursor.execute('''INSERT INTO person (person_count, head_count) VALUES (?, ?)''', (person_count, head_count))
    cursor.connection.commit()

# Fungsi untuk menambahkan anotasi pada frame
def annotate_frame(frame, detections, person_count, head_count):
    bounding_box_annotator = sv.BoundingBoxAnnotator()
    label_annotator = sv.LabelAnnotator()
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

    status_text = 'Crowded' if person_count > 15 else 'Uncrowded'
    text_color = (0, 0, 255) if person_count > 15 else (0, 255, 0)

    text_y_status = text_y_person + 70
    cv2.putText(annotated_frame, status_text, (text_x, text_y_status), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)

    return annotated_frame

# Fungsi untuk streaming dan mendeteksi
def stream_and_detect(video_path):
    conn = sqlite3.connect('detections.db')  # Koneksi baru untuk thread ini
    cursor = conn.cursor()
    
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    output_hls_folder = 'hls_output'
    if not os.path.exists(output_hls_folder):
        os.makedirs(output_hls_folder)

    hls_output_path = os.path.join(output_hls_folder, 'output.m3u8')
    
    output_params = {
        "-input_framerate": fps,
        '-s': f'{width}x{height}',
        "-vcodec": "libx264",
        "-preset": "ultrafast",
        "-tune": "zerolatency",
        "-f": "hls",
        "-hls_time": "2",
        "-hls_list_size": "0",
        "-hls_flags": "append_list",
        '-hls_segment_filename': os.path.join(output_hls_folder, 'segment_%03d.ts'),
        "-g": "60"
    }
    
    writer_hls = WriteGear(
        output=hls_output_path, 
        compression_mode=True, 
        logging=True, 
        **output_params
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        detections, person_count, head_count = detect_objects(frame)
        save_detection(cursor, person_count, head_count)
        annotated_frame = annotate_frame(frame, detections, person_count, head_count)

        # Tulis frame ke output HLS
        writer_hls.write(annotated_frame)

    cap.release()
    writer_hls.close()
    conn.close()  # Tutup koneksi database setelah selesai

# Endpoint untuk upload dan streaming video
@app.route('/process_video/', methods=['POST'])
@swag_from({
    'parameters': [
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'File video (mp4, avi, mov) untuk diproses dan dianotasi'
        }
    ],
    'responses': {
        200: {
            'description': 'Streaming video berhasil',
            'content': {
                'image/jpeg': {}
            }
        },
        400: {
            'description': 'Invalid file type or other error'
        }
    }
})
def process_video():
    file = request.files.get('file')
    if not file:
        return jsonify({"detail": "No file uploaded"}), 400

    if file.content_type not in ["video/mp4", "video/avi", "video/mov"]:
        return jsonify({"detail": "Invalid file type. Only mp4, avi, or mov allowed."}), 400

    video_path = os.path.join(OUTPUT_FOLDER, f"temp_{file.filename}")
    file.save(video_path)

    # Menjalankan thread untuk streaming dan deteksi
    stream_thread = threading.Thread(target=stream_and_detect, args=(video_path,))
    stream_thread.start()

    return jsonify({"detail": "Video is being processed and streamed."}), 200

# Endpoint untuk mengakses video HLS
@app.route('/hls_output/<path:filename>')
def serve_hls(filename):
    # Tentukan file path
    file_path = 'D:/7. Project Mandiri/Python/Yolov11/hls_output'

    # Tentukan MIME type berdasarkan file extension
    if filename.endswith('.m3u8'):
        mimetype = 'application/vnd.apple.mpegurl'
    elif filename.endswith('.ts'):
        mimetype = 'video/mp2t'
    else:
        mimetype = None

    # Sajikan file dengan MIME type yang tepat
    return send_from_directory(file_path, filename, mimetype=mimetype)

# Menjalankan server Flask
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
