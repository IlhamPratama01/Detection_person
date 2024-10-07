import os
import torch
import cv2
import supervision as sv
import sqlite3
import datetime
import pytz
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
from io import BytesIO
import numpy as np
from fastapi.responses import FileResponse

app = FastAPI()

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
@app.post("/upload_video/")
async def upload_video(file: UploadFile = File(...)):
    # Pastikan file yang diunggah adalah video
    if file.content_type not in ["video/mp4", "video/avi", "video/mov"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only mp4, avi, or mov allowed.")

    # Simpan file video sementara ke disk
    video_path = f"temp_{file.filename}"
    with open(video_path, "wb") as video_file:
        video_file.write(await file.read())

    # Membuka video dan proses
    cap = cv2.VideoCapture(video_path)
    conn, cursor = setup_database()
    
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Error opening video file")

    output_frames = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 480))
        detections, person_count, head_count = detect_objects(frame)
        save_detection(cursor, person_count, head_count)
        annotated_frame = annotate_frame(frame, detections, person_count, head_count)
        output_frames.append(annotated_frame)

    cap.release()
    conn.close()

    # Hapus file video sementara
    os.remove(video_path)

    # Gabungkan frame yang dianotasi menjadi video kembali
    height, width, _ = output_frames[0].shape
    output_video_path = f"output_{file.filename}"
    output = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), 20, (width, height))

    for frame in output_frames:
        output.write(frame)

    output.release()

    # Kembalikan video hasil sebagai file yang bisa di-download
    return FileResponse(output_video_path, media_type="video/mp4", filename=output_video_path)

# Endpoint untuk upload dan anotasi gambar
@app.post("/upload_image/")
async def upload_image(file: UploadFile = File(...)):
    # Pastikan file yang diunggah adalah gambar
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only jpg and png allowed.")

    # Membaca gambar dari UploadFile
    image_bytes = await file.read()
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Error reading image file")

    # Resize gambar agar sesuai
    img = cv2.resize(img, (640, 480))

    # Deteksi objek dalam gambar
    detections, person_count, head_count = detect_objects(img)

    # Anotasi gambar
    annotated_image = annotate_frame(img, detections, person_count, head_count)

    # Simpan gambar yang dianotasi ke buffer
    _, img_encoded = cv2.imencode('.jpg', annotated_image)
    img_bytes = BytesIO(img_encoded.tobytes())

    # Kembalikan gambar yang dianotasi sebagai StreamingResponse
    return StreamingResponse(img_bytes, media_type="image/jpeg")

# Menjalankan server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
