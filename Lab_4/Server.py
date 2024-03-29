import socket
import threading
import pickle

SERVER_IP = '127.0.0.1'
SERVER_PORT = 5555

class ChatRoomDirectory:
    def __init__(self):
        self.chat_rooms = {}

    def create_room(self, room_name, port, multicast_group):
        # Check if new room is using a pre-existing multicast and port
        for _, val in self.chat_rooms.items():
             if isinstance(val, tuple) and val == (multicast_group, port):
                print(f"Room with multicast {multicast_group} and port {port} already exists!")
                return False
                  
        self.chat_rooms[room_name] = (multicast_group, port)
        print(self.chat_rooms)

        return True
    
    def delete_room(self, room_name):
        try:
            del self.chat_rooms[room_name]
            print(f"Deleted {room_name}")
        except:
            print(f"Room name {room_name} does not exist")

    def get_room_multicast_group(self, room_name):
        return self.chat_rooms.get(room_name)

    def get_directory_list(self):
        return self.chat_rooms

class ChatRoomDirectoryServer:
    def __init__(self, ip, port):
        self.directory = ChatRoomDirectory()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((ip, port))
        self.server.listen()

        print("Chat Room Directory Server listening on port " + str(port))

    def handle_client(self, client, addr):
        while True:
            try:
                msg = client.recv(1024).decode('utf-8')

                if not msg:
                    # Client has closed the connection
                    print(f"Client {addr} has closed the connection")
                    break

                command, *args = msg.split(' ')

                if command.lower() == 'makeroom':
                    room_name, port, multicast_group = args
                    if self.directory.create_room(room_name, port, multicast_group):
                        response = f"Room {room_name} created with multicast group {multicast_group}."
                    else:
                        response = f"Room {room_name} already exists."
                    client.send(response.encode('utf-8'))

                elif command == 'GET_MULTICAST_GROUP':
                    room_name = args[0]
                    multicast_group, port = self.directory.get_room_multicast_group(room_name)
                    print(f"Device joined {room_name}")
                    
                    if multicast_group:
                        response = f"Multicast group for room {room_name}: {multicast_group, port}"
                    else:
                        response = f"Room {room_name} not found."
                    client.send(response.encode('utf-8'))

                elif command == 'getdir':
                    d = self.directory.get_directory_list()
                    response = pickle.dumps(d)
                    client.send(response)

                elif command == 'deleteroom':
                    room_name = args[0]
                    self.directory.delete_room(room_name)
                    response = f"Room {room_name} sucessfully deleted."
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
