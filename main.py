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
from ultralytics.solutions import heatmap

app = Flask(__name__)
swagger = Swagger(app)
CORS(app)

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

def heatmaps(video_path):

    heatmap_obj = heatmap.Heatmap()
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Ensure heatmap output folder exists
    output_heatsmap = 'output_heatsmap'
    os.makedirs(output_heatsmap, exist_ok=True)
    output_heatsmap_path = os.path.join(output_heatsmap, 'mapsoutput.m3u8')

    heatmap_params = {
        "-input_framerate": fps,
        '-s': f'{width}x{height}',
        "-vcodec": "libx264",
        "-preset": "veryfast",  # Adjusted for better balance between speed and quality
        "-tune": "zerolatency",
        "-f": "hls",
        "-hls_time": "2",
        "-hls_list_size": "0",
        "-hls_flags": "delete_segments",  # Automatically clean up segments
        '-hls_segment_filename': os.path.join(output_heatsmap, 'segment_%03d.ts'),
        "-g": str(fps * 2)  # Adjusted GOP size to match segment duration
    }

    # WriteGear for the heatmap HLS output
    writer_hls2 = WriteGear(output=output_heatsmap_path, compression_mode=True, logging=True, **heatmap_params)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Generate the heatmap
        tracks = model.track(frame, persist=True)
        frame_with_heatmap = heatmap_obj.generate_heatmap(frame, tracks)

        # Write both normal and heatmap frames to respective HLS outputs
        writer_hls2.write(frame_with_heatmap)

    # Release resources
    cap.release()
    writer_hls2.close()

# Fungsi untuk streaming dan mendeteksi
def stream_and_detect(video_path):
    # Database connection setup
    conn = sqlite3.connect('detections.db')  
    cursor = conn.cursor()

    # Initialize heatmap object
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Ensure HLS output folder exists
    hls_output = 'hls_output'
    os.makedirs(hls_output, exist_ok=True)
    hls_output_path = os.path.join(hls_output, 'output.m3u8')

    # HLS output parameters for normal video
    hls_params = {
        "-input_framerate": fps,
        '-s': f'{width}x{height}',
        "-vcodec": "libx264",
        "-preset": "ultrafast",
        "-tune": "zerolatency",
        "-f": "hls",
        "-hls_time": "2",
        "-hls_list_size": "0",
        "-hls_flags": "append_list",
        '-hls_segment_filename': os.path.join(hls_output, 'segment_%03d.ts'),
        "-g": "60"
    }

    # WriteGear for the regular HLS output
    writer_hls1 = WriteGear(output=hls_output_path, compression_mode=True, logging=True, **hls_params)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect objects and update the database
        detections, person_count, head_count = detect_objects(frame)
        save_detection(cursor, person_count, head_count)
        
        # Annotate the frame with detection info
        annotated_frame = annotate_frame(frame, detections, person_count, head_count)
    
        # Write both normal and heatmap frames to respective HLS outputs
        writer_hls1.write(annotated_frame)


    # Release resources
    cap.release()
    writer_hls1.close()
    conn.close()

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
    heatmap_thread = threading.Thread(target=heatmaps, args=(video_path,))
    stream_thread.start()
    heatmap_thread.start()

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

@app.route('/heatsmap/<path:filename>')
def serve_heatsmap(filename):
    # Tentukan file path
    file_path = 'D:/7. Project Mandiri/Python/Yolov11/output_heatsmap'

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