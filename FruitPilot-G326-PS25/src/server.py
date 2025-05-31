import socket

def start_server(host='0.0.0.0', port=12345):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr} has been established!")
        handle_client(client_socket)

def handle_client(client_socket):
    while True:
        message = client_socket.recv(1024).decode()
        if not message:
            break
        print(f"Received message: {message}")
        response = process_message(message)
        client_socket.send(response.encode())
    client_socket.close()

def process_message(message):
    if message == "RED":
        return "Searching for target..."
    elif message == "GREEN":
        return "Moving towards target..."
    elif message == "ORANGE":
        return "Adjusting position..."
    elif message == "NONE":
        return "Idle..."
    elif message == "EXIT":
        return "Shutting down server..."
    else:
        return "Unknown command."

if __name__ == "__main__":
    start_server()