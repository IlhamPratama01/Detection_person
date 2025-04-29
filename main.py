import os
import cv2
import uuid
import torch
import sqlite3
import threading
import subprocess
import numpy as np
import supervision as sv
from queue import Queue
from flask_cors import CORS
from ultralytics import YOLO
from vidgear.gears import WriteGear
from flasgger import Swagger, swag_from
from ultralytics.solutions import heatmap
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
swagger = Swagger(app)
CORS(app)

OUTPUT_FOLDER = 'output_videos'
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = YOLO('best.pt')

def setup_database():
    conn = sqlite3.connect('detections.db', check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") 
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

def detect_objects(frame):
    results = model(frame)[0]
    detections = sv.Detections.from_ultralytics(results)
    person_count = sum(1 for name in detections.data['class_name'] if name == 'Person')
    head_count = sum(1 for name in detections.data['class_name'] if name == 'Head')
    return detections, person_count, head_count

def save_detection(cursor, person_count, head_count, retries=5):
    for attempt in range(retries):
        try:
            cursor.execute('''INSERT INTO person (person_count, head_count) VALUES (?, ?)''', (person_count, head_count))
            cursor.connection.commit()
            break
        except sqlite3.OperationalError:
            if attempt < retries - 1:
                time.sleep(0.1)
            else:
                raise

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

# def heatmaps(video_path, unique_id):
#     heatmap_obj = heatmap.Heatmap()
#     cap = cv2.VideoCapture(video_path)
#     fps = int(cap.get(cv2.CAP_PROP_FPS))

#     output_heatmap_folder = f'output_heatsmap/{unique_id}'
#     os.makedirs(output_heatmap_folder, exist_ok=True)
#     output_heatmap_path = os.path.join(output_heatmap_folder, 'mapsoutput.m3u8')

#     # Set consistent frame dimensions
#     FRAME_WIDTH = 640  # Desired frame width
#     FRAME_HEIGHT = 360  # Desired frame height# Match accumulator dimensions

#     heatmap_params = {
#         "-input_framerate": fps,
#         '-s': f'{FRAME_WIDTH}x{FRAME_HEIGHT}',  # Match the new dimensions
#         "-vcodec": "libx264",
#         "-preset": "ultrafast",
#         "-tune": "zerolatency",
#         "-f": "hls",
#         "-hls_time": "2",
#         "-hls_list_size": "0",
#         "-hls_flags": "append_list",
#         '-hls_segment_filename': os.path.join(output_heatmap_folder, 'segment_%03d.ts'),
#         "-g": str(fps * 2)
#     }
#     writer_hls2 = WriteGear(output=output_heatmap_path, compression_mode=True, logging=True, **heatmap_params)
    
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
        
#         # Resize frame to match heatmap dimensions
#         frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
#         # Perform tracking and generate heatmap frame
#         tracks = model.track(frame, persist=True)
#         frame_heatmap = heatmap_obj.generate_heatmap(frame, tracks)
        
#         # Write heatmap frame to the output
#         writer_hls2.write(frame_heatmap)

#     cap.release()
#     writer_hls2.close()


def stream_and_detect(video_path, unique_id):
    conn = setup_database()
    cursor = conn.cursor()
    heatmap_obj = heatmap.Heatmap()
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    hls_output = f'hls_output/{unique_id}'
    os.makedirs(hls_output, exist_ok=True)
    hls_output_path = os.path.join(hls_output, 'output.m3u8')

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
        "-g": str(fps * 2)
    }
    writer_hls1 = WriteGear(output=hls_output_path, compression_mode=True, logging=True, **hls_params)

    FRAME_WIDTH = 640  # Define the desired frame width
    FRAME_HEIGHT = 360

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        detections, person_count, head_count = detect_objects(frame)
        save_detection(cursor, person_count, head_count)
        annotated_frame = annotate_frame(frame, detections, person_count, head_count)
        tracks = model.track(frame, persist=True)
        annotated_frame = heatmap_obj.generate_heatmap(frame, tracks)
        writer_hls1.write(annotated_frame)

    cap.release()
    writer_hls1.close()
    conn.close()

@app.route('/process_video/', methods=['POST'])
@swag_from({
    'parameters': [
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'Video file for processing and annotation'
        }
    ],
    'responses': {
        200: {'description': 'Video is being processed and streamed'},
        400: {'description': 'Invalid file type or other error'}
    }
})
def process_video():
    file = request.files.get('file')
    if not file:
        return jsonify({"detail": "No file uploaded"}), 400

    if file.content_type not in ["video/mp4", "video/avi", "video/mov"]:
        return jsonify({"detail": "Invalid file type. Only mp4, avi, or mov allowed."}), 400

    unique_id = str(uuid.uuid4())
    video_path = os.path.join(OUTPUT_FOLDER, f"temp_{unique_id}_{file.filename}")
    file.save(video_path)

    threading.Thread(target=stream_and_detect, args=(video_path, unique_id)).start()
    # threading.Thread(target=heatmaps, args=(video_path, unique_id)).start()
    subprocess.Popen(["python", "main.py", video_path, unique_id], close_fds=True)

    return jsonify({"detail": "Video is being processed and streamed.", "unique_id": unique_id}), 200

@app.route('/hls_output/<unique_id>/<path:filename>')
def serve_hls(unique_id, filename):
    file_path = f'hls_output/{unique_id}'
    mimetype = 'application/vnd.apple.mpegurl' if filename.endswith('.m3u8') else 'video/mp2t'
    return send_from_directory(file_path, filename, mimetype=mimetype)

# @app.route('/heatsmap/<unique_id>/<path:filename>')
# def serve_heatsmap(unique_id, filename):
#     file_path = f'output_heatsmap/{unique_id}'
#     mimetype = 'application/vnd.apple.mpegurl' if filename.endswith('.m3u8') else 'video/mp2t'
#     return send_from_directory(file_path, filename, mimetype=mimetype)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)