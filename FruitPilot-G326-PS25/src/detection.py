def get_detections(frame):
    model = YOLO('../old_150.pt')  # Load the YOLO model
    results = model(frame)  # Perform detection
    return results  # Return detection results