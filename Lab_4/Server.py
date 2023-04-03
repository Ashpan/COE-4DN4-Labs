import socket
import threading
import json

SERVER_IP = '127.0.0.1'
SERVER_PORT = 5555

class ChatRoomDirectory:
    def __init__(self):
        self.chat_rooms = {}

    def create_room(self, room_name, multicast_group):
        if room_name not in self.chat_rooms:
            self.chat_rooms[room_name] = multicast_group
            print(self.chat_rooms)
            return True
        print(self.chat_rooms)
        return False

    def get_room_multicast_group(self, room_name):
        return self.chat_rooms.get(room_name)

class ChatRoomDirectoryServer:
    def __init__(self, ip, port):
        self.directory = ChatRoomDirectory()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((ip, port))
        self.server.listen()

    def handle_client(self, client, addr):
        while True:
            try:
                msg = client.recv(1024).decode('utf-8')
                if msg:
                    command, *args = msg.split(' ')
                    if command == 'CREATE':
                        room_name, multicast_group = args
                        if self.directory.create_room(room_name, multicast_group):
                            response = f"Room {room_name} created with multicast group {multicast_group}."
                        else:
                            response = f"Room {room_name} already exists."
                        client.send(response.encode('utf-8'))
                    elif command == 'GET_MULTICAST_GROUP':
                        room_name = args[0]
                        multicast_group = self.directory.get_room_multicast_group(room_name)
                        print(room_name)
                        
                        if multicast_group:
                            response = f"Multicast group for room {room_name}: {multicast_group}"
                        else:
                            response = f"Room {room_name} not found."
                        client.send(response.encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] {e}")
                client.close()
                break

    def start(self):
        print("Server started.")
        while True:
            client, addr = self.server.accept()
            print("Connection established with", addr)
            thread = threading.Thread(target=self.handle_client, args=(client, addr))
            thread.start()

if __name__ == "__main__":
    server = ChatRoomDirectoryServer(SERVER_IP, SERVER_PORT)
    server.start()
