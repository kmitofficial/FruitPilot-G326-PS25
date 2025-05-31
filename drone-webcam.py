from dronekit import connect, VehicleMode, LocationGlobalRelative, Command
import cv2
import threading
import time
from pymavlink import mavutil
from pynput import keyboard  # use pynput for key detection on Linux

# ========================
# 1. Connect to the Vehicle
# ========================
print("Connecting to vehicle...")
vehicle = connect('tcp:192.168.1.100:5760', wait_ready=True)  # Replace with your laptop's IP and port
print("Connected to vehicle.")

# ========================
# 2. Webcam Thread with Optional Recording
# ========================
recording = False
out = None

VIDEO_WIDTH = 3840  # Set for 4K: 3840x2160 or 1920x1080 for Full HD
VIDEO_HEIGHT = 2160

def show_webcam():
    global recording, out
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)

    if not cap.isOpened():
        print("Failed to open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Webcam Feed", frame)

        if recording and out is not None:
            out.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()

# Start webcam in a separate thread
threading.Thread(target=show_webcam, daemon=True).start()

# ========================
# 3. Drone Commands
# ========================
def arm_and_takeoff(aTargetAltitude):
    print("Arming motors...")
    while not vehicle.is_armable:
        print("Waiting for vehicle to initialize...")
        time.sleep(1)

    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    while not vehicle.armed:
        print("Waiting for arming...")
        time.sleep(1)

    print("Taking off!")
    vehicle.simple_takeoff(aTargetAltitude)

    while True:
        print(" Altitude: ", vehicle.location.global_relative_frame.alt)
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

def move_relative(dx=0, dy=0, dz=0):
    current_location = vehicle.location.global_relative_frame
    new_location = LocationGlobalRelative(
        current_location.lat + dx * 0.000001,  # very slow movement
        current_location.lon + dy * 0.000001,  # very slow movement
        current_location.alt + dz
    )
    vehicle.simple_goto(new_location, groundspeed=0.25)  # set very low groundspeed
    print(f"Moving to: {new_location}")

def send_yaw_velocity(yaw_rate):
    msg = vehicle.message_factory.set_attitude_target_encode(
        0,
        0,
        0,
        0b00000100,
        [0, 0, 0, 1],  # dummy quaternion
        0, 0, 0,
        yaw_rate
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()

# ========================
# 4. Arrow Key Control with pynput
# ========================

def arrow_key_control():
    print("Use arrow keys to move. Press ESC to exit move control.")
    step = 1  # meters
    yaw_rate = 0.1  # rad/s for slower rotation

    def on_press(key):
        try:
            if key == keyboard.Key.esc:
                print("Exiting move control mode.")
                return False
            elif key == keyboard.Key.up:
                move_relative(dx=step)
            elif key == keyboard.Key.down:
                move_relative(dx=-step)
            elif key == keyboard.Key.left:
                print("Yaw left")
                send_yaw_velocity(-yaw_rate)
            elif key == keyboard.Key.right:
                print("Yaw right")
                send_yaw_velocity(yaw_rate)
            elif key.char == 'u':
                move_relative(dz=-step)
            elif key.char == 'j':
                move_relative(dz=step)
        except AttributeError:
            pass  # for special keys that aren't handled

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ========================
# 5. Command-Line Interface
# ========================
print("\nAvailable commands:")
print("  t - takeoff")
print("  m - move with arrow keys")
print("  r - start/stop webcam recording")
print("  l - land")
print("  e - exit\n")

while True:
    cmd = input(">>> ").strip().lower()
    if cmd == "t":
        try:
            alt = float(input("Enter altitude to take off (in meters): "))
            arm_and_takeoff(alt)
        except:
            print("Invalid altitude value.")
    elif cmd == "m":
        arrow_key_control()
    elif cmd == "r":
        if not recording:
            print("Starting video recording...")
            out = cv2.VideoWriter('drone_feed.avi', cv2.VideoWriter_fourcc(*'XVID'), 20.0, (VIDEO_WIDTH, VIDEO_HEIGHT))
            recording = True
        else:
            print("Stopping video recording...")
            recording = False
            if out:
                out.release()
                out = None
    elif cmd == "l":
        print("Landing...")
        vehicle.mode = VehicleMode("LAND")
    elif cmd == "e":
        print("Exiting...")
        vehicle.close()
        break
    else:
        print("Unknown command. Use 't', 'm', 'r', 'l', or 'e'.")
