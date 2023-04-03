import socket
import struct
import threading
import traceback

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
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def leave_multicast_group(self, multicast_group):
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)

    def create_chat_room(self, room_name, multicast_group):
        self.directory_sock.send(f"CREATE {room_name} {multicast_group}".encode('utf-8'))
        response = self.directory_sock.recv(1024).decode('utf-8')
        print(response)
        return "created" in response.lower()

    def join_chat_room(self, room_name):
        self.directory_sock.send(f"GET_MULTICAST_GROUP {room_name}".encode('utf-8'))
        response = self.directory_sock.recv(1024).decode('utf-8')
        print(response)
        if "not found" not in response.lower():
            multicast_group = response.split()[-1]
            self.join_multicast_group(multicast_group)
            return True, multicast_group
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

    def send(self, multicast_group, msg):
        try:
            self.send_sock.sendto(msg.encode('utf-8'), (multicast_group, MULTICAST_PORT))
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
            command, *args = message.split()

            if command.lower() == "name":
                self.NAME = ' '.join(args[0:])
                continue
            if self.CURRENT_MODE == "DISCONNECTED":
                if command.lower() == "connect":
                    self.connect()
                else:
                    print("You are not connected to the directory server. Please connect first.")
            elif self.CURRENT_MODE == "CONNECTED":
                if command.lower() == "makeroom": #TODO: Add port number as a parameter
                    room_name, multicast_group = args
                    self.create_chat_room(room_name, multicast_group)
                elif command.lower() == "chat":
                    room_name = args[0]
                    success, multicast_group = self.join_chat_room(room_name)
                    if success:
                        print(f"Joined chat room {room_name} with multicast group {multicast_group}.")
                        self.CURRENT_MODE = "CHAT"
                        self.JOINED_ROOM = multicast_group
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
                self.send(multicast_group, msg)

# TODO
# 1. Bye command
# 2. Getdir command
# 3. Deleteroom command
            


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    YOUR_LOCAL_IP = s.getsockname()[0]
    s.close()

    client = MulticastChatClient(YOUR_LOCAL_IP)
    client.start()
