#!/usr/bin/env python3

########################################################################
#
# Simple File Request/Download Protocol
#
########################################################################
#
# When the client connects to the server and wants to request a file
# download, it sends the following message: 1-byte GET command + 1-byte
# filename size field + requested filename, e.g.,

# ------------------------------------------------------------------
# | 1 byte GET command  | 1 byte filename size | ... file name ... |
# ------------------------------------------------------------------

# The server checks for the GET and then transmits the requested file.
# The file transfer data from the server is prepended by an 8 byte
# file size field as follows:

# -----------------------------------
# | 8 byte file size | ... file ... |
# -----------------------------------

# The server needs to have REMOTE_FILE_NAME defined as a text file
# that the client can request. The client will store the downloaded
# file using the filename LOCAL_FILE_NAME. This is so that you can run
# a server and client from the same directory without overwriting
# files.

########################################################################

import socket
import argparse
import threading
import os

########################################################################

# Define all of the packet protocol field lengths.

CMD_FIELD_LEN            = 1 # 1 byte commands sent from the client.
FILENAME_SIZE_FIELD_LEN  = 1 # 1 byte file name size field.
FILESIZE_FIELD_LEN       = 8 # 8 byte file size field.

# Define a dictionary of commands. The actual command field value must
# be a 1-byte integer. For now, we only define the "GET" command,
# which tells the server to send a file.

CMD = {
    "GET" : 1,
    "PUT" : 2,
    "LIST" : 3,}

MSG_ENCODING = "utf-8"

########################################################################
# recv_bytes frontend to recv
########################################################################

# Call recv to read bytecount_target bytes from the socket. Return a
# status (True or False) and the received butes (in the former case).
def recv_bytes(sock, bytecount_target):
    byte_recv_count = 0 # total received bytes
    recv_bytes = b''    # complete received message
    while byte_recv_count < bytecount_target:
        # Ask the socket for the remaining byte count.
        new_bytes = sock.recv(bytecount_target-byte_recv_count)
        # If ever the other end closes on us before we are done,
        # give up and return a False status with zero bytes.
        if not new_bytes:
            return(False, b'')
        byte_recv_count += len(new_bytes)
        recv_bytes += new_bytes
    return (True, recv_bytes)

########################################################################
# SERVER
########################################################################

class Server:

    HOSTNAME = ""

    FSP_PORT = 50000
    RECV_SIZE = 1024
    BACKLOG = 5

    FILE_NOT_FOUND_MSG = "Error: Requested file is not available!"

    REMOTE_FOLDER = os.getcwd() + "/remote_files/"

    def __init__(self):
        self.create_listen_socket()
        udp_thread = threading.Thread(target=self.process_udp_connections_forever)
        tcp_thread = threading.Thread(target=self.process_tcp_connections_forever)
        udp_thread.start()
        tcp_thread.start()

    def list_available_files(self):
        print("Available files:")
        for file in os.listdir(Server.REMOTE_FOLDER):
            print("  " + file)

    def create_listen_socket(self):
        try:
            # Create the TCP server listen socket in the usual way.
            self.sdp_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            self.sdp_socket.bind(("0.0.0.0", Client.SDP_PORT))
            print(f"Listening for service discovery messages on SDP port {Client.SDP_PORT}...")

            self.fsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.fsp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.fsp_socket.bind((Server.HOSTNAME, Server.FSP_PORT))
            self.fsp_socket.listen(Server.BACKLOG)
            print(f"Listening for file sharing connections on port {Server.FSP_PORT}...")
        except Exception as msg:
            print("Create listen socket:", msg)
            exit()

    def process_udp_connections_forever(self):
        while True:
            try:
                data, address = self.sdp_socket.recvfrom(Server.RECV_SIZE)
                decoded_msg = data.decode(MSG_ENCODING)
                if decoded_msg == "SERVICE DISCOVERY":
                    print("Received service discovery message from", address)
                    self.sdp_socket.sendto("Ashpan and Dharak's File Sharing Service".encode(MSG_ENCODING), address)
            except KeyboardInterrupt:
                print(); exit()
            except Exception as msg:
                print(msg)
                break

    def process_tcp_connections_forever(self):
        try:
            while True:
                self.connection_handler(self.fsp_socket.accept())
        except KeyboardInterrupt:
            print()
        finally:
            self.fsp_socket.close()

    def connection_handler(self, client):
        connection, address = client
        print("-" * 72)
        print("Connection received from {}.".format(address))

        ################################################################
        # Process a connection and see if the client wants a file that
        # we have.

        status, cmd_field = recv_bytes(connection, CMD_FIELD_LEN)
        cmd = int.from_bytes(cmd_field, byteorder='big')
        if cmd == CMD["GET"]:
            status, filename_size_field = recv_bytes(connection, FILENAME_SIZE_FIELD_LEN)
            if not status:
                print("Closing connection ...")
                connection.close()
                return

            filename_size_bytes = int.from_bytes(filename_size_field, byteorder='big')
            if not filename_size_bytes:
                print("Connection is closed!")
                connection.close()
                return

            status, filename_bytes = recv_bytes(connection, filename_size_bytes)
            if not status:
                print("Closing connection ...")
                connection.close()
                return
            if not filename_bytes:
                print("Closing connection ...")
                connection.close()
                return

            filename = filename_bytes.decode(MSG_ENCODING)
            print('Requested filename = ', filename)
            filename = Server.REMOTE_FOLDER + filename

            try:
                file = open(filename, 'r').read()
            except FileNotFoundError:
                print(Server.FILE_NOT_FOUND_MSG)
                connection.close()
                return

            # Encode the file contents into bytes, record its size and
            # generate the file size field used for transmission.
            file_bytes = file.encode(MSG_ENCODING)
            file_size_bytes = len(file_bytes)
            file_size_field = file_size_bytes.to_bytes(FILESIZE_FIELD_LEN, byteorder='big')

            # Create the packet to be sent with the header field.
            pkt = file_size_field + file_bytes

            try:
                # Send the packet to the connected client.
                connection.sendall(pkt)
                print("Sending file: ", filename)
            except socket.error:
                # If the client has closed the connection, close the
                # socket on this end.
                print("Closing client connection ...")
                connection.close()
                return
            finally:
                connection.close()
                return


########################################################################
# CLIENT
########################################################################

class Client:

    RECV_SIZE = 10
    SDP_PORT = 50001


    # Define the local file name where the downloaded file will be
    # saved.
    DOWNLOADED_FILE_NAME = "filedownload.txt"
    SERVICE_DISCOVERY_MSG = "SERVICE DISCOVERY"
    CLIENT_FILES_DIR = os.getcwd() + "/client_files/"

    def __init__(self):
        self.get_socket()
        self.run_commands()


    def run_commands(self):
        while True:
            cmd = input("Enter a command: ").lower()
            if cmd == "bye":
                break
            elif cmd == "scan":
                self.scan()
            elif cmd == "llist":
                self.list_local_files()
            elif cmd == "rlist":
                break
            elif cmd.startswith("connect"):
                address = cmd.split(" ")[1]
                port = int(cmd.split(" ")[2])
                self.connect_to_server((address, port))
            elif cmd.startswith("get"):
                self.get_file(cmd.split(" ")[1])
            elif cmd.startswith("put"):
                break
            else:
                print("Invalid command.")

    def scan(self):
        sdp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sdp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            encoded_msg = Client.SERVICE_DISCOVERY_MSG.encode(MSG_ENCODING)
            sdp_sock.sendto(encoded_msg, ("255.255.255.255", Client.SDP_PORT))
            response, addr = sdp_sock.recvfrom(1024)
            decoded_response = response.decode(MSG_ENCODING)
            print(decoded_response + " found at " + str(addr[0]), str(Server.FSP_PORT))
        finally:
            sdp_sock.close()

    def list_local_files(self):
        for file in os.listdir(Client.CLIENT_FILES_DIR):
            print(file)

    def get_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as msg:
            print(msg)
            exit()

    def connect_to_server(self, addr):
        self.get_socket()
        try:
            self.socket.connect(addr)
        except Exception as msg:
            print("connect_to_server:", msg)
            exit()

    def get_file(self, filename):

        ################################################################
        # Generate a file transfer request to the server

        # Create the packet cmd field.
        cmd_field = CMD["GET"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        # Create the packet filename field.
        filename_field_bytes = filename.encode(MSG_ENCODING)

        # Create the packet filename size field.
        filename_size_field = len(filename_field_bytes).to_bytes(FILENAME_SIZE_FIELD_LEN, byteorder='big')

        pkt = cmd_field + filename_size_field + filename_field_bytes

        # Send the request packet to the server.
        self.socket.sendall(pkt)

        ################################################################
        # Process the file transfer response from the server

        # Read the file size field returned by the server.
        status, file_size_bytes = recv_bytes(self.socket, FILESIZE_FIELD_LEN)
        print("after recv_bytes")
        if not status:
            print("Closing connection ...")
            self.socket.close()
            return

        print("File size bytes = ", file_size_bytes.hex())
        if len(file_size_bytes) == 0:
            self.socket.close()
            return

        # Make sure that you interpret it in host byte order.
        file_size = int.from_bytes(file_size_bytes, byteorder='big')
        print("File size = ", file_size)

        # self.socket.settimeout(4)
        status, recvd_bytes_total = recv_bytes(self.socket, file_size)
        if not status:
            print("Closing connection ...")
            self.socket.close()
            return
        # Receive the file itself.
        try:
            # Create a file using the received filename and store the
            # data.
            downloaded_file = Client.CLIENT_FILES_DIR + filename
            print("Received {} bytes. Creating file: {}" \
                  .format(len(recvd_bytes_total), filename))

            with open(downloaded_file, 'w') as f:
                recvd_file = recvd_bytes_total.decode(MSG_ENCODING)
                f.write(recvd_file)
            print(recvd_file)
        except KeyboardInterrupt:
            print()
            exit(1)

########################################################################

if __name__ == '__main__':
    roles = {'client': Client,'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles,
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################





