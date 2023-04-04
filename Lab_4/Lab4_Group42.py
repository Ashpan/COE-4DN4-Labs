import argparse
import socket
import struct
import threading
import traceback
import pickle

DIRECTORY_SERVER_IP = '127.0.0.1'
DIRECTORY_SERVER_PORT = 5555
MULTICAST_PORT = 5007

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
YOUR_LOCAL_IP = s.getsockname()[0]
s.close()

class MulticastChatClient:

    CURRENT_MODE = "DISCONNECTED"
    JOINED_ROOM = None
    NAME = None
    def __init__(self):
        self.local_ip = YOUR_LOCAL_IP
        
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_sock.bind(('', MULTICAST_PORT))

        self.start()

    def connect(self):
        self.directory_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.directory_sock.connect((DIRECTORY_SERVER_IP, DIRECTORY_SERVER_PORT))
        self.CURRENT_MODE = "CONNECTED"
        print("Connected to directory server.")

    def join_multicast_group(self, multicast_group):
        try:
            group = socket.inet_aton(multicast_group)
        except socket.error:
            print("Invalid multicast group IP address:", multicast_group)
            return
        
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        
        try:
            self.recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            print("Successfully joined multicast group:", multicast_group)
        except socket.error as e:
            print("Failed to join multicast group:", e)
            return
        
    def leave_multicast_group(self, multicast_group):
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)

    def create_chat_room(self, room_name, port, multicast_group):
        self.directory_sock.send(f"makeroom {room_name} {multicast_group} {port}".encode('utf-8'))
        response = self.directory_sock.recv(1024).decode('utf-8')
        print(response)
        return "made room" in response.lower()
    
    def delete_chat_room(self, room_name):
        self.directory_sock.send(f"deleteroom {room_name}".encode('utf-8'))
        response = self.directory_sock.recv(1024).decode('utf-8')
        print(response)
        return "sucessfully deleted" in response.lower()

    def join_chat_room(self, room_name):
        self.directory_sock.send(f"GET_MULTICAST_GROUP {room_name}".encode('utf-8'))
        response = self.directory_sock.recv(1024).decode('utf-8')
        print(response)

        if "not found" not in response.lower():
            # Find IP address in the response string
            ip_start = response.find("(") + 1
            ip_end = response.find(",")
            # Extract the IP address substring
            ip_address = response[ip_start:ip_end].strip('\'')
            self.join_multicast_group(ip_address)

            return True, ip_address
        
        else:
            print(response)
            return False, None

    def receive(self):
        while True:
            try:
                msg, addr = self.recv_sock.recvfrom(1024)
                if msg:
                    decoded_msg = msg.decode('utf-8')
                    if decoded_msg.startswith("[NAME:"):
                        name = decoded_msg.split("]")[0].split(":")[-1]
                        name_removed_message = decoded_msg.split("]")[1]
                    else:
                        name = f"{addr[0]}:{addr[1]}"
                        name_removed_message = decoded_msg
                    print(f"[{name}] {name_removed_message}")

            except Exception as e:
                print(f"[ERROR] {e}")
                self.recv_sock.close()
                break

    def send_chat(self, multicast_group, msg):
        try:
            self.send_sock.sendto(msg.encode('utf-8'), (multicast_group, MULTICAST_PORT))
        except Exception:
            traceback.print_exc()

    def send_command(self, cmd):
        try:
            self.directory_sock.send(cmd.encode('utf-8'))
        except Exception:
            traceback.print_exc()

    def start(self):
        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()
        input_str = ""

        while True:
            if (self.CURRENT_MODE == "CHAT"):
                input_str = "CHAT>"
            elif (self.CURRENT_MODE == "CONNECTED"):
                input_str = "CRDS>"
            else:
                input_str = ">"

            message = input(input_str)

            try:
                command, *args = message.split()
            # There is only a command, no arguments
            except ValueError:
                command = message

            if command.lower() == "name":
                self.NAME = ' '.join(args[0:])
                continue

            if self.CURRENT_MODE == "DISCONNECTED":
                if command.lower() == "connect":
                    self.connect()
                else:
                    print("You are not connected to the directory server. Please connect first.")

            elif self.CURRENT_MODE == "CONNECTED":
                if command.lower() == "makeroom":
                    try:
                        room_name, port, multicast_group = args
                    except ValueError:
                        print("Invalid arguments. Please try again.")
                        continue
                    self.create_chat_room(room_name, port, multicast_group)

                elif command.lower() == "chat":
                    room_name = args[0]
                    success, multicast_group = self.join_chat_room(room_name)
                    if success:
                        print(f"Joined chat room {room_name} with multicast group {multicast_group}.")
                        self.CURRENT_MODE = "CHAT"
                        self.JOINED_ROOM = multicast_group

                elif command.lower() == "getdir":
                    self.send_command(command.lower())
                    response = self.directory_sock.recv(1024)
                    dir = pickle.loads(response)
                    
                    for key, value in dir.items():
                        print(f"Room Name: {key}, Address: {value[0]}, Port: {value[1]}\n")

                elif command.lower() == "deleteroom":
                    try:
                        room_name = args[0]
                    except IndexError:
                        print("Invalid arguments. Please try again.")
                        continue
                    self.delete_chat_room(room_name)
                    continue

                elif command.lower() == "bye":
                    self.directory_sock.close()
                    self.CURRENT_MODE = "DISCONNECTED"
                    print("Disconnected from directory server.")

            elif self.CURRENT_MODE == "CHAT":
                msg = message
                if message == r"\quit":
                    self.CURRENT_MODE = "CONNECTED"
                    self.leave_multicast_group(self.JOINED_ROOM)
                    self.JOINED_ROOM = None
                    continue
                multicast_group = self.JOINED_ROOM
                if (self.NAME != None):
                    name = "[NAME:" + self.NAME + "]"
                else:
                    name = ''
                msg = name + msg
                self.send_chat(multicast_group, msg)


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
    def __init__(self):
        self.directory = ChatRoomDirectory()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((SERVER_IP, SERVER_PORT))
        self.server.listen()

        print("Chat Room Directory Server listening on port " + str(SERVER_PORT))

        self.start()

    def handle_client(self, client, addr):
        while True:
            try:
                msg = client.recv(1024).decode('utf-8')
                if msg:
                    command, *args = msg.split(' ')
                    print(f"command {command}")
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


if __name__ == '__main__':
    roles = {'server': ChatRoomDirectoryServer,'client': MulticastChatClient}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles, 
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()