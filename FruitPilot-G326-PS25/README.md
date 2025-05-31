# FruitPilot-G326-PS25 Documentation

## Project Overview
FruitPilot-G326-PS25 is a drone control system that utilizes computer vision for object detection and tracking. The project integrates a drone control library with a YOLO-based detection model to autonomously navigate and interact with its environment.

## Project Structure
```
FruitPilot-G326-PS25
├── src
│   ├── main.py          # Main entry point for the application
│   ├── control.py       # Drone control functions
│   ├── detection.py      # Object detection using YOLO
│   ├── server.py        # TCP server for communication
│   └── __init__.py      # Package initialization
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation
```

## Setup Instructions

1. **Install Dependencies**: 
   Use the `requirements.txt` file to install the necessary libraries. Run the following command in your terminal:
   ```
   pip install -r requirements.txt
   ```

2. **Run the Server**: 
   Navigate to the `src` directory and run the `server.py` file to start the server:
   ```
   python server.py
   ```

3. **Connect the Drone**: 
   Ensure that the drone's `main.py` file is configured to connect to the server's IP address and port. The server should be running before starting the drone script.

4. **Monitor Communication**: 
   The server will listen for incoming messages from the drone and can respond based on the commands received.

5. **Modify Server Logic**: 
   You can customize the `server.py` file to handle specific commands or implement additional functionality as needed.

## Usage

- **Starting the Drone**: 
  After setting up the server, run the `main.py` script to start the drone's operations. The drone will initialize its systems, connect to the server, and begin its state management (takeoff, search, track, etc.).

- **Communication Protocol**: 
  The drone communicates with the server using a simple TCP protocol. The server can receive commands such as "RED", "GREEN", "ORANGE", and respond accordingly.

## Additional Information
Make sure to check the `README.md` for any additional setup or usage instructions specific to your project.