import cv2
import os
from ultralytics import YOLO
from ultralytics.solutions import heatmap

# Initialize the heatmap
model = YOLO("best.pt")  # Corrected the assignment syntax
cap = cv2.VideoCapture("mal.mp4")  # Added missing quote

if not cap.isOpened():  # Fixed method name `1sOpened()` to `isOpened()`
    print("Error reading video file")
    exit(0)

class_names = model.names if isinstance(model.names, list) else list(model.names.values())
print(class_names[1])
# Initialize heatmap object
heatmap_obj = heatmap.Heatmap() # Fixed assignment syntax
 # Fixed assignment syntax

# Prepare video writer  # Initialize video writer
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    # Generate the heatmap
    tracks = model.track(frame, persist=True)
    frame_with_heatmap = heatmap_obj.generate_heatmap(frame, tracks)
    cv2.imshow('Heatmap', frame_with_heatmap)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
