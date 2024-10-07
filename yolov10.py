import torch
import cv2
import supervision as sv
import sqlite3
from ultralytics import YOLO
import datetime
import pytz

# Mengatur device untuk menggunakan GPU jika tersedia
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Inisialisasi model YOLOv10 dengan perangkat yang dipilih
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


# Membuka video
def open_video(video_path):
    return cv2.VideoCapture(video_path)

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
    cursor.execute('''INSERT INTO person (person_count) VALUES (?)''', (person_count,))
    cursor.execute('''INSERT INTO person (head_count) VALUES (?)''', (head_count,))
    cursor.connection.commit()

# Fungsi untuk menambahkan anotasi pada frame
def annotate_frame(frame, detections, person_count, head_count):
    # Inisialisasi annotator
    bounding_box_annotator = sv.BoundingBoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    
    # Anotasi bounding box dan label
    annotated_frame = bounding_box_annotator.annotate(scene=frame, detections=detections)
    annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections)

    # Mendapatkan ukuran frame untuk menghitung posisi teks
    frame_height, frame_width, _ = frame.shape
    text = f'Person: {person_count}'
    text_head = f'Head: {head_count}'
    
    # Menentukan posisi teks
    text_x = frame_width - 200  # Untuk posisi teks
    text_y_person = 30
    text_y_head = 50

    # Tambahkan teks jumlah orang dengan warna merah
    cv2.putText(annotated_frame, text, (text_x, text_y_person), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Tambahkan teks jumlah orang dengan warna merah
    cv2.putText(annotated_frame, text_head, (text_x, text_y_head), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Logika tambahan untuk menambahkan teks "Crowded" atau "Aman"
    if person_count > 15:
        status_text = 'Crowded'
        text_color = (0, 0, 255)  # Merah untuk 'Crowded'
    else:
        status_text = 'Uncrowded'
        text_color = (0, 255, 0)  # Hijau untuk 'Aman'

    # Menentukan posisi teks untuk status (di bawah teks jumlah orang)
    text_y_status = text_y_person + 70

    # Tambahkan teks status dengan warna yang sesuai
    cv2.putText(annotated_frame, status_text, (text_x, text_y_status), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)

    return annotated_frame


# Pipeline utama untuk memproses video
def process_video(video_path):
    conn, cursor = setup_database()
    cap = open_video(video_path)
    
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Ubah ukuran frame untuk mempercepat pemrosesan
        frame = cv2.resize(frame, (640, 480))

        detections, person_count, head_count = detect_objects(frame)  
        save_detection(cursor, person_count, head_count)
        annotated_frame = annotate_frame(frame, detections, person_count, head_count)

        # Menampilkan frame dengan anotasi
        cv2.imshow('Annotated Video', annotated_frame)

        # Keluar jika tombol 'q' ditekan
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Bersihkan
    cap.release()
    conn.close()
    cv2.destroyAllWindows()

# Panggil pipeline
process_video('./mall.mp4')

# downloaded_live_video.mp4
