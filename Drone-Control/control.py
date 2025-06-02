from dronekit import connect, VehicleMode, LocationGlobalRelative, Command
import time
import cv2
from ultralytics import YOLO
import math
from pymavlink import mavutil

# === CONFIGURATION ===
MODEL_PATH = 'distant.pt'
REAL_FRUIT_WIDTH_CM = 19.81
REAL_FRUIT_HEIGHT_CM = 25.14
FOCAL_LENGTH_MM = 3.6
SENSOR_WIDTH_MM = 4.8
SENSOR_HEIGHT_MM = 3.6
IMAGE_WIDTH_PX = 640
IMAGE_HEIGHT_PX = 480

# === GLOBAL STATE ===
vehicle = None
horizontal_fov_deg = None
vertical_fov_deg = None
altitude_to_fly = 10
model = YOLO(MODEL_PATH)
model.fuse()
connected = False
armed = False
search_flag = False

# === DISTANCE ESTIMATION ===
def estimate_distance(focal_length_mm, real_width_cm, bbox_width_px, image_width_px, sensor_width_mm):
    if bbox_width_px == 0:
        return float('inf')
    focal_px = (focal_length_mm / sensor_width_mm) * image_width_px
    return (real_width_cm * focal_px) / bbox_width_px

# === YAW ROTATION FUNCTION ===
def condition_yaw(heading, relative=False):
    is_relative = 1 if relative else 0
    msg = vehicle.message_factory.command_long_encode(
        0, 0, mavutil.mavlink.MAV_CMD_CONDITION_YAW,
        0, heading, 1, 1, is_relative, 0, 0, 0
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()

# === FORWARD MOVEMENT ===
def send_ned_velocity(velocity_x, velocity_y, velocity_z, duration):
    msg = vehicle.message_factory.set_position_target_local_ned_encode(
        0, 0, 0, mavutil.mavlink.MAV_FRAME_BODY_NED,
        0b0000111111000111, 0, 0, 0,
        velocity_x, velocity_y, velocity_z,
        0, 0, 0, 0, 0
    )
    for _ in range(0, duration):
        vehicle.send_mavlink(msg)
        print_telemetry()
        time.sleep(1)

# === DRONE CONNECTION ===
def connect_drone(connection_string, waitready=True, baudrate=57600):
    global vehicle
    if vehicle is None:
        vehicle = connect(connection_string, wait_ready=waitready, baud=baudrate)
    print("Drone connected")

def land():
    global vehicle
    print("Landing...")
    vehicle.mode = VehicleMode("LAND")
    while vehicle.armed:
        print(" Waiting for landing...")
        time.sleep(1)
    print("Landed and disarmed.")

def RTL():
    global vehicle
    print("Returning to Launch (RTL)...")
    vehicle.mode = VehicleMode("RTL")
    while vehicle.armed:
        print(" Waiting for RTL and landing...")
        time.sleep(1)
    print("Returned and disarmed.")

# === TELEMETRY ===
def print_telemetry():
    print(f"\nTelemetry:")
    print(f" Altitude: {vehicle.location.global_relative_frame.alt:.2f} m")
    print(f" GPS: {vehicle.location.global_frame.lat:.6f}, {vehicle.location.global_frame.lon:.6f}")
    print(f" Velocity: {vehicle.velocity}")
    print(f" Battery: {vehicle.battery}")

# === ARM AND TAKEOFF ===
def arm(altitude=4):
    global armed, search_flag
    print("Arming motors...")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)
    armed = True
    print("Armed.")

    print(f"Taking off to {altitude}m")
    vehicle.simple_takeoff(altitude)
    while True:
        print(f" Altitude: {vehicle.location.global_relative_frame.alt:.2f}m")
        if vehicle.location.global_relative_frame.alt >= altitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

    search_flag = True  # Begin search loop

# === DETECTION LOOP ===
def detect_loop():
    global search_flag
    cap = cv2.VideoCapture(0)  # Adjust camera index if needed

    if not cap.isOpened():
        print("Failed to open camera.")
        return

    print("Starting detection loop...")
    while search_flag:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read from camera.")
            break

        results = model(frame, verbose=False)[0]

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = model.names[cls_id] if model.names else str(cls_id)

            bbox_width = x2 - x1
            distance_cm = estimate_distance(
                FOCAL_LENGTH_MM,
                REAL_FRUIT_WIDTH_CM,
                bbox_width,
                IMAGE_WIDTH_PX,
                SENSOR_WIDTH_MM
            )

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            info_text = f"{label} | {conf*100:.1f}% | {distance_cm:.1f}cm"
            cv2.putText(frame, info_text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            if distance_cm < 100:
                print(f"Close to {label}, distance: {distance_cm:.2f} cm")
                send_ned_velocity(0.2, 0, 0, 3)
                search_flag = False
                break

        cv2.imshow("YOLO Detection Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# === MAIN ===
if __name__ == "__main__":
    try:
        connect_drone("tcp:127.0.0.1:5762")
        arm(altitude_to_fly)
        detect_loop()
        land()
    except Exception as e:
        print(f"Error: {e}")
        if vehicle:
            RTL()
