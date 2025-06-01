import cv2
from ultralytics import YOLO
from dronekit import connect, VehicleMode, LocationGlobalRelative
from pymavlink import mavutil
import time
import control
import keyboard
import detection
import argparse
import socket

sonars={}
cap = cv2.VideoCapture(0)


# Frame dimensions
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
frame_center_x = frame_width // 2  # Center x-coordinate of the frame
move_threshold = 50  # Threshold in pixels to initiate drone movement
font = cv2.FONT_HERSHEY_SIMPLEX
org = (00, 185)
fontScale = 1
color = (0, 0, 255)
thickness = 2
SERVER_IP = '192.168.225.246'  # Replace with your server's local IP
PORT = 12345

# Create socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)



# Set up video writer for saving the video feed
output_file = f"output_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
# fourcc = cv2.VideoWriter_fourcc(*'XVID')
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_file, fourcc, 20.0, (frame_width, frame_height))

STATE = "takeoff"
altitude  = 4


def setup():

    # control.connect_drone('/dev/ttyACM0', False, 57600)
    control.connect_drone("tcp:127.0.0.1:5762", True, 57600)

    ret, frame = cap.read()
    # result = detection.get_detections(frame)
    # client_socket.connect((SERVER_IP, PORT))
    # print("SETup done")
    #print("vehicle1 connected")
    #control.connect_drone('udp:192.168.225.141:14551')
    #Real drone 
    #vehicle2 = connect('/dev/ttyACM0', wait_ready=False, baud=57600)
    #print("vehicle2 connected")
    #vehicle2.add_message_listener('DISTANCE_SENSOR',listener)
    # print("Detector Initialized")
    
def init_camera():
      while True:
         ret, frame = cap.read()
         if not ret:
           continue
         cv2.imshow("Setup camera", frame)
         if cv2.waitKey(1) & 0xFF == ord('q'):
           cv2.destroyAllWindows()  
           break

def yaw(speed, duration):
   start = time.time()
   while time.time() - start <=  duration:
        control.send_movement_command_YAW(speed)
        
def search():
    print("State is SEARCH -> " + STATE)
    start = time.time()
    last_yaw_time = start

    while True:
        if cv2.waitKey(1) & 0xFF == ord('q'):
          cv2.destroyAllWindows()  
          break

        # Send yaw command every 3 seconds
        if time.time() - last_yaw_time >= 7:
            yaw(5, 1)
            last_yaw_time = time.time() 

        ret, frame = cap.read()
        if not ret:
           continue

        result = detection.get_detections(frame)
        out.write(frame)
        cv2.imshow("Drone camera", frame)
        if len(result[0].boxes) > 0:
            return "track"
            
    return "idle"
    
def track():

    while True:
      
      ret, frame = cap.read()
      if not ret:
         continue
      
      result = detection.get_detections(frame)
      if len(result[0].boxes) == 0:
         return "search"
        
      for box in result[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        # Calculate the center of the bounding box
        box_center_x = (x1 + x2) // 2
        
        # Calculate the horizontal offset from the center of the frame
        offset_x = box_center_x - frame_center_x
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        #fetch distance
        area = (x2-x1)*(y2-y1)
        
        if(area > 10000):
          return "search"
        cv2.putText(frame, str(area), org, font, fontScale, color, thickness, cv2.LINE_AA, False)
        
        if abs(offset_x) > move_threshold:
            control.send_movement_command_Y(0)
            client_socket.send("ORANGE".encode())
            cv2.line(frame, (box_center_x, y1), (box_center_x, y2), (255, 0, 0), 2)
            angle = -0.5 if offset_x < 0 else 0.5
            control.send_movement_command_YAW(angle)
        else:
            control.send_movement_command_YAW(0)
            cv2.line(frame, (box_center_x, y1), (box_center_x, y2), (0, 255, 0), 2)
            speed = 0.3 if area < 3850  else 0
            if speed == 0:
              client_socket.send("GREEN".encode())
            else:
              client_socket.send("ORANGE".encode())
            control.send_movement_command_Y(speed)
      out.write(frame)
      cv2.imshow("Drone camera", frame)
      
      # Exit loop on 'q' key press
      if cv2.waitKey(1) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        break
    
    return "idle"


setup()
# init_camera()

#Main loop
start = input("Is camera working properly: ")
if (start == "Y"):
   STATE = control.arm_and_takeoff(altitude)
   while True:
      if STATE == "track":
         STATE = track()
      elif STATE == "search":
         STATE = search()
        
      elif STATE == "land":
        control.land()
        break
    
      elif STATE == "RTL":
        control.RTL()
        break
       
      elif STATE == "exit":
        break
        
      elif STATE == "idle":
        client_socket.send("NONE".encode())
        val = input("Drone is in idle state, try to change the state to [search, land, RTL, exit]:")
        if val in ["search", "land", "exit", "RTL"]:
           STATE = val

# Main loop 
# while True:
#     if STATE == "track":
#         STATE = track()

#     elif STATE == "search":
#        client_socket.send("RED".encode())
#        STATE = search()
    
#     elif STATE == "takeoff":
#         init_camera()
#         inpt = input("Enter yes to takeoff : ")
#         if inpt != "yes":
#            continue
#         STATE = control.arm_and_takeoff(altitude)
#         #point = LocationGlobalRelative(17.396973996804782, 78.49031912873349, altitude)
#         #control.goto(point)
        
#     elif STATE == "land":
#         control.land()
#         break
    
#     elif STATE == "RTL":
#         control.RTL()
#         break
       
#     elif STATE == "exit":
#         break
        
#     elif STATE == "idle":
#         client_socket.send("NONE".encode())
#         val = input("Drone is in idle state, try to change the state to [search, land, RTL, exit]:")
#         if val in ["search", "land", "exit", "RTL"]:
#            STATE = val


    

    
# Release resources
cap.release()
out.release()
client_socket.send("EXIT".encode())
cv2.destroyAllWindows()
control.disconnect_drone()
#vehicle2.close()