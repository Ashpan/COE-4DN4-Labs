import socket
from cryptography.fernet import Fernet


COURSE_GRADES_FILE = "course_grades_2023.csv"

class Server:
    def __init__(self):
        print("We have created a Server object: ", self)
        host = socket.gethostname()  # as both code is running on same pc
        port = 5001  # socket server port number
        self.server_socket = socket.socket()  # get instance
        self.server_socket.bind((host, port))  # bind host address and port together
        self.parsed_data = {}
        self.commands = {"GMA": "Midterm Average", "GL1A": "Lab 1", "GL2A": "Lab 2", "GL3A": "Lab 3", "GL4A": "Lab 4", "GEA": "Exam Average", "GG": "Grades"}

        self.print_course_grades() # Print and parse the data into a dictionary

        print(f"Listening for connections on port {port}")
        pass

    def print_course_grades(self):
        cleaned_data = self.clean_print_data()
        self.parsed_data = self.parse_data(cleaned_data)

    def clean_print_data(self):
        file = open(COURSE_GRADES_FILE, "r")
        cleaned_data = [clean_line for clean_line in
                                    [line.strip() for line in file.readlines()]
                                    if clean_line != '']
        file.close()
        for line in cleaned_data:
            print(line)
        return cleaned_data

    def parse_data(self, cleaned_data):
        self.parsed_data = {}
        for line in cleaned_data:
            if line.startswith("Name"):
                continue
            else:
                student_name, student_number, key, lab1, lab2, lab3, lab4, midterm, exam1, exam2, exam3, exam4 = line.split(",")
                self.parsed_data[int(student_number)] = {"key": key, "Student Name": student_name, "Midterm": int(midterm), "Lab 1": int(lab1), "Lab 2": int(lab2), "Lab 3": int(lab3), "Lab 4": int(lab4), "Exam 1": int(exam1), "Exam 2": int(exam2), "Exam 3": int(exam3), "Exam 4": int(exam4)}
        return self.parsed_data

    def run_command(self, id, command):
        return_string = ""
        if command == "GG":
            for key, value in self.parsed_data[int(id)].items():
                if key == "Student Name":
                    continue
                else:
                    return_string += f"{key}: {value}, "
        elif command == "GMA":
            average = 0
            count = 0
            for key in self.parsed_data:
                average += self.parsed_data[key]["Midterm"]
                count += 1
            return_string = f"{average/count}"
        elif command == "GEA":
            average = 0
            count = 0
            for key in self.parsed_data:
                average += (self.parsed_data[key]["Exam 1"] + self.parsed_data[key]["Exam 2"] + self.parsed_data[key]["Exam 3"] + self.parsed_data[key]["Exam 4"]) / 4
                count += 1
            return_string = f"{average/count}"
        elif command.startswith("GL") and command.endswith("A"):
            average = 0
            count = 0
            for key in self.parsed_data:
                average += self.parsed_data[key][self.commands[command]]
                count += 1
            return_string = f"{average/count}"
        return return_string

    def encrypt_string(self, message, encryption_key):
        message_bytes = message.encode('utf-8')
        encryption_key_bytes = encryption_key.encode('utf-8')
        fernet = Fernet(encryption_key_bytes)
        encrypted_message_bytes = fernet.encrypt(message_bytes)
        return encrypted_message_bytes

    def server_program(self):

        # configure how many client the server can listen simultaneously
        self.server_socket.listen(1)
        conn, address = self.server_socket.accept()  # accept new connection
        incoming_ip_address = address[0]
        incoming_port = address[1]
        print(f"Connection received from {incoming_ip_address} on port {incoming_port}")

        while True:
            # receive data stream. it won't accept data packet greater than 1024 bytes
            data = conn.recv(1024).decode()
            if not data:
                # if data is not received break
                break
            id, command = data.split(",")
            return_value = ""

            print(f"Received {command} command from the client")
            if(int(id) not in self.parsed_data):
                print("User not found")
                continue
            else:
                print("User found")

            if command not in self.commands:
                print("Invalid command")
                continue
            else:
                return_value = self.run_command(id, command) # calculate the value to return
            encrypted_message = self.encrypt_string(return_value, self.parsed_data[int(id)]["key"]) # encrypt the message
            print(encrypted_message)
            # data = input(' -> ')
            conn.send(encrypted_message)  # send data to the client

        conn.close()  # close the connection


if __name__ == '__main__':
    server = Server()
    server.server_program()