import socket
import struct
import threading
import traceback
import pickle

DIRECTORY_SERVER_IP = '127.0.0.1'
DIRECTORY_SERVER_PORT = 5555
MULTICAST_PORT = 5007

class MulticastChatClient:

    CURRENT_MODE = "DISCONNECTED"
    JOINED_ROOM = None
    NAME = None
    def __init__(self, local_ip):
        self.local_ip = local_ip
        
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_sock.bind(('', MULTICAST_PORT))

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
        except socket.error as e:
            print("Failed to join multicast group:", e)
            return
        
        print("Successfully joined multicast group:", multicast_group)
        
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
            if (self.CURRENT_MODE == "CONNECTED"):
                input_str = "CRDS>"
            elif (self.CURRENT_MODE == "CHAT"):
                input_str = ""
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
                        print(f"\n*** CHATTING IN ROOM: {room_name} ***\n")
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

if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    YOUR_LOCAL_IP = s.getsockname()[0]
    s.close()

    client = MulticastChatClient(YOUR_LOCAL_IP)
    client.start()
