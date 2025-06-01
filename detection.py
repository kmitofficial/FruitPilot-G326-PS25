import cv2
from ultralytics import YOLO
import time

model = YOLO("old_150.pt")
confidence_threshold = 0.8

def get_detections(frame):
    results = model.predict(source=frame, save=False, verbose=False)
    # results = model.predict(source=frame, conf=confidence_threshold, save=False, verbose=False)
    return results