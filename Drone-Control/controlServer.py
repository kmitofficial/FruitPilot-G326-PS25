# Workaround for Python 3.10+ compatibility with dronekit is not needed for Python 3.9
# import collections
# collections.MutableMapping = collections.abc.MutableMapping

from dronekit import connect, VehicleMode, LocationGlobalRelative, Command
import time
import cv2
from ultralytics import YOLO
import math
from pymavlink import mavutil
import keyboard
import os
import json

# === CONFIGURATION ===
MODEL_PATH = 'distant.pt'
REAL_FRUIT_WIDTH_CM = 19.81
REAL_FRUIT_HEIGHT_CM = 25.14
FOCAL_LENGTH_MM = 3.6
SENSOR_WIDTH_MM = 4.8
SENSOR_HEIGHT_MM = 3.6
IMAGE_WIDTH_PX = 640
IMAGE_HEIGHT_PX = 480
DEFAULT_ALTITUDE = 10
# Read altitude from a configuration file if it exists
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
        altitude_to_fly = float(config.get('altitude', DEFAULT_ALTITUDE))
        print(f"Using altitude from config.json: {altitude_to_fly}m")
except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
    altitude_to_fly = DEFAULT_ALTITUDE
    print(f"Config file not found or invalid ({e}). Using default altitude: {altitude_to_fly}m. Please create or update config.json with the desired altitude.")

# === GLOBAL STATE ===
connection_string = "tcp:10.147.84.40:5762"
fallback_connection_string = "tcp:127.0.0.1:5762"
vehicle = None
horizontal_fov_deg = None
vertical_fov_deg = None
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
    if vehicle == None:
        vehicle = connect(connection_string, wait_ready=waitready, baud=baudrate)
    print("drone connected")

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
def arm(altitude=altitude_to_fly):
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

# === DETECTION FUNCTION ===
def detect_loop():
    global horizontal_fov_deg, vertical_fov_deg, search_flag
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IMAGE_WIDTH_PX)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IMAGE_HEIGHT_PX)

    horizontal_fov_deg = 2 * math.degrees(math.atan((SENSOR_WIDTH_MM / 2) / FOCAL_LENGTH_MM))
    vertical_fov_deg = 2 * math.degrees(math.atan((SENSOR_HEIGHT_MM / 2) / FOCAL_LENGTH_MM))
    print(f"Calculated FOV: H={horizontal_fov_deg:.2f}°, V={vertical_fov_deg:.2f}°")

    yaw_angle = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera error.")
            break

        results = model.predict(source=frame, conf=0.5, verbose=False)[0]
        boxes = results.boxes

        if search_flag and connected and armed:
            if boxes is None or len(boxes.xyxy) == 0:
                yaw_angle += int(horizontal_fov_deg / 2) - 5
                yaw_angle = yaw_angle % 360
                print(f"No object. Rotating yaw to: {yaw_angle}")
                condition_yaw(yaw_angle)
                time.sleep(3)
            else:
                for i, box in enumerate(boxes.xyxy.cpu()):
                    x1, y1, x2, y2 = box.int().tolist()
                    bbox_width = x2 - x1
                    bbox_center_x = (x1 + x2) // 2
                    frame_center_x = IMAGE_WIDTH_PX // 2
                    error = bbox_center_x - frame_center_x

                    dist_cm = estimate_distance(FOCAL_LENGTH_MM, REAL_FRUIT_WIDTH_CM, bbox_width, IMAGE_WIDTH_PX, SENSOR_WIDTH_MM)

                    if abs(error) > 20:
                        correction = int((error / IMAGE_WIDTH_PX) * horizontal_fov_deg)
                        print(f"Aligning yaw by {correction} degrees")
                        condition_yaw(correction, relative=True)
                        time.sleep(3)

                    print(f"Moving toward object... Estimated distance: {dist_cm:.1f} cm")
                    dist_m = dist_cm / 100.0
                    send_ned_velocity(0.25, 0, 0, int(dist_m / 0.25))

                    print("Returning to base height...")
                    vehicle.simple_goto(LocationGlobalRelative(vehicle.location.global_frame.lat, vehicle.location.global_frame.lon, altitude_to_fly))
                    while abs(vehicle.location.global_relative_frame.alt - altitude_to_fly) > 0.3:
                        print(f" Current Altitude: {vehicle.location.global_relative_frame.alt:.2f}")
                        time.sleep(3)

                    print("Ready to search again.")
                    break

        cv2.imshow("Live Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def init_cam():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IMAGE_WIDTH_PX)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IMAGE_HEIGHT_PX)
    return cap

if __name__ == "__main__":
    try:
        print(f"Attempting to connect to {connection_string}")
        connect_drone(connection_string)
        connected = True
        print("Successfully connected to primary connection string.")
    except Exception as e:
        print(f"Failed to connect to {connection_string}: {e}")
        print(f"Trying fallback connection: {fallback_connection_string}")
        try:
            connect_drone(fallback_connection_string)
            connected = True
            print("Successfully connected to fallback connection string.")
        except Exception as fallback_e:
            print(f"Fallback connection failed: {fallback_e}")
            print("Unable to connect to vehicle. Ensure simulation (e.g., ArduPilot SITL) is running on the specified IP and port.")
            print("For SITL, start with: sim_vehicle.py -v ArduCopter --console --map")
            connected = False
    if connected:
        arm()
        while True:
            detect_loop()