from dronekit import connect, VehicleMode, LocationGlobalRelative
import cv2
import threading
import time
import keyboard  # for arrow key detection

# ========================
# 1. Connect to the Vehicle
# ========================
print("Connecting to vehicle...")
vehicle = connect('tcp:127.0.0.1:5762', wait_ready=True)  # Adjust this if using a real drone
print("Connected to vehicle.")

# ========================
# 2. Webcam Thread
# ========================
def show_webcam():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open webcam.")
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Webcam Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
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
        current_location.lat + dx * 0.00001,
        current_location.lon + dy * 0.00001,
        current_location.alt + dz
    )
    vehicle.simple_goto(new_location)
    print(f"Moving to: {new_location}")

# ========================
# 4. Arrow Key Control
# ========================
def arrow_key_control():
    print("Use arrow keys to move. Press 'esc' to stop controlling.")
    step = 1  # meters
    while True:
        if keyboard.is_pressed('esc'):
            print("Exiting move control mode.")
            break
        elif keyboard.is_pressed('up'):
            move_relative(dx=step)
            time.sleep(0.5)
        elif keyboard.is_pressed('down'):
            move_relative(dx=-step)
            time.sleep(0.5)
        elif keyboard.is_pressed('left'):
            move_relative(dy=-step)
            time.sleep(0.5)
        elif keyboard.is_pressed('right'):
            move_relative(dy=step)
            time.sleep(0.5)
        elif keyboard.is_pressed('u'):
            move_relative(dz=-step)
            time.sleep(0.5)
        elif keyboard.is_pressed('j'):
            move_relative(dz=step)
            time.sleep(0.5)

# ========================
# 5. Command-Line Interface
# ========================
print("\nAvailable commands:")
print("  t - takeoff")
print("  m - move with arrow keys")
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
    elif cmd == "l":
        print("Landing...")
        vehicle.mode = VehicleMode("LAND")
    elif cmd == "e":
        print("Exiting...")
        vehicle.close()
        break
    else:
        print("Unknown command. Use 't', 'm', 'l', or 'e'.")
