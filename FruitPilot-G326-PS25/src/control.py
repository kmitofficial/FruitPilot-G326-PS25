from dronekit import *
from pymavlink import mavutil

vehicle = None

# Connect to the Vehicle (in this case a UDP endpoint)
def connect_drone(connection_string, waitready=True, baudrate=57600):
    global vehicle
    if vehicle == None:
        vehicle = connect(connection_string, wait_ready=waitready, baud=baudrate)
    print("drone connected")

def arm_and_takeoff(aTargetAltitude):
    """
    Arms vehicle and fly to aTargetAltitude.
    """
    global vehicle
    print("Basic pre-arm checks")
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialise...")
        time.sleep(1)

    print("Arming motors")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)

    print("Taking off!")
    vehicle.simple_takeoff(aTargetAltitude)

    while True:
        print(" Altitude: ", vehicle.location.global_relative_frame.alt)
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)
    
    return "search"

def send_movement_command_Y(velocity_y):
    """
    Send movement command in the Y (left-right) direction.
    Positive velocity moves right; negative moves left.
    """
    msg = vehicle.message_factory.set_position_target_local_ned_encode(
        0, 0, 0, mavutil.mavlink.MAV_FRAME_BODY_NED,
        0b0000111111000111,  # Bitmask to control only Y-velocity
        0, 0, 0,  # Positions not controlled
        velocity_y, 0, 0,  # Move in Y direction
        0, 0, 0, 0, 0)
    
    vehicle.send_mavlink(msg)
    vehicle.flush()

def send_movement_command_YAW(heading):
    global vehicle
    speed = 0 
    direction = 1 #direction -1 ccw, 1 cw
    
    #heading 0 to 360 degree. if negative then ccw 
    
    print("Sending YAW movement command with heading: %f" % heading)

    if heading < 0:
        heading = heading*-1
        direction = -1

    #point drone into correct heading 
    msg = vehicle.message_factory.command_long_encode(
        0, 0,       
        mavutil.mavlink.MAV_CMD_CONDITION_YAW, 
        0,          
        heading,    
        speed,      #speed deg/s
        direction,  
        1,          #relative offset 1
        0, 0, 0)    

    # send command to vehicle
    vehicle.send_mavlink(msg)
    #Vehicle.commands.flush()
    
    
def disconnect_drone():
    vehicle.close()