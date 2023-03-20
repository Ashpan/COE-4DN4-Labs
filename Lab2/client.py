import socket

commands = {"GMA": "Midterm Average", "GL1A": "Lab 1 Average", "GL2A": "Lab 2 Average", "GL3A": "Lab 3 Average", "GL4A": "Lab 4 Average", "GEA": "Exam Average", "GG": "Grades"}


class Client:
    def __init__(self):
        print("We have created a Client object: ", self)
        host = socket.gethostname()  # as both code is running on same pc
        port = 5001  # socket server port number

        self.client_socket = socket.socket()  # instantiate
        self.client_socket.connect((host, port))  # connect to the server

        pass


    def client_program(self):

        command = ""
        while command.lower().strip() != 'bye':
            student_number = input("Enter your student number: ")  # take input
            command = input("Enter your command: ")  # take input
            print(f"Command entered: {command}")
            if command not in commands:
                print("Invalid command")
                continue
            else:
                print(f"Fetching {commands[command]}")
            command = student_number + "," + command
            self.client_socket.send(command.encode())  # send command
            data = self.client_socket.recv(1024).decode()  # receive response

            print('Received from server: ' + data)  # show in terminal


        self.client_socket.close()  # close the connection


if __name__ == '__main__':
    client = Client()
    client.client_program()