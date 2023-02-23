import socket
import argparse
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os



class Server:
    def __init__(self):
        host = socket.gethostname()  # as both code is running on same pc
        self.commands = {"GMA": "Midterm Average", "GL1A": "Lab 1", "GL2A": "Lab 2", "GL3A": "Lab 3", "GL4A": "Lab 4", "GEA": "Exam Average", "GG": "Grades"}
        self.parsed_data = {}
        load_dotenv()
        port = int(os.getenv("PORT"))  # socket server port number
        self.course_grade_file = os.getenv("COURSE_GRADES_FILE")
        self.server_socket = socket.socket()  # get instance
        self.server_socket.bind((host, port))  # bind host address and port together

        print("We have created a Server object: ", self)
        self.print_course_grades() # Print and parse the data into a dictionary
        print(f"Listening for connections on port {port}")

        self.server_program()
        pass

    def print_course_grades(self):
        cleaned_data = self.clean_data()
        print("Data read from CSV file:")
        print("\n".join(cleaned_data))
        self.parsed_data = self.parse_data(cleaned_data)

    def clean_data(self):
        file = open(self.course_grade_file, "r")
        cleaned_data = [clean_line for clean_line in
                                    [line.strip() for line in file.readlines()]
                                    if clean_line != '']
        file.close()
        return cleaned_data

    def parse_data(self, cleaned_data):
        self.parsed_data = {}
        for line in cleaned_data:
            if not line.startswith("Name"):
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
                break
            else:
                print("User found")

            if command not in self.commands:
                print("Invalid command")
                break
            else:
                return_value = self.run_command(id, command) # calculate the value to return
                encrypted_message = self.encrypt_string(return_value, self.parsed_data[int(id)]["key"]) # encrypt the message
                print("Encrypted message:", encrypted_message)
                conn.send(encrypted_message)  # send data to the client

        conn.close()  # close the connection


class Client:
    def __init__(self):
        print("We have created a Client object: ", self)
        load_dotenv()
        host = socket.gethostname()  # as both code is running on same pc
        port = int(os.getenv("PORT"))  # socket server port number

        self.secret_key_dict = {
            1803933: "M7E8erO15CIh902P8DQsHxKbOADTgEPGHdiY0MplTuY=",
            1884159: "PWMKkdXW4VJ3pXBpr9UwjefmlIxYwPzk11Aw9TQ2wZQ=",
            1853847: "UVpoR9emIZDrpQ6pCLYopzE2Qm8bCrVyGEzdOOo2wXw=",
            1810192: "bHdhydsHzwKdb0RF4wG72yGm2a2L-CNzDl7vaWOu9KA=",
            1891352: "iHsXoe_5Fle-PHGtgZUCs5ariPZT-LNCUYpixMC3NxI=",
            1811313: "IR_IQPnIM1TI8h4USnBLuUtC72cQ-u4Fwvlu3q5npA0=",
            1804841: "kE8FpmTv8d8sRPIswQjCMaqunLUGoRNW6OrYU9JWZ4w=",
            1881925: "_B__AgO34W7urog-thBu7mRKj3AY46D8L26yedUwf0I=",
            1877711: "dLOM7DyrEnUsW-Q7OM6LXxZsbCFhjmyhsVT3P7oADqk=",
            1830894: "aM4bOtearz2GpURUxYKW23t_DlljFLzbfgWS-IRMB3U=",
            1855191: "-IieSn1zKJ8P3XOjyAlRcD2KbeFl_BnQjHyCE7-356w=",
            1821012: "Lt5wWqTM1q9gNAgME4T5-5oVptAstg9llB4A_iNAYMY=",
            1844339: "M6glRgMP5Y8CZIs-MbyFvev5VKW-zbWyUMMt44QCzG4=",
            1898468: "SS0XtthxP64E-z4oB1IsdrzJwu1PUq6hgFqP_u435AA=",
            1883633: "0L_o75AEsOay_ggDJtOFWkgRpvFvM0snlDm9gep786I=",
            1808742: "9BXraBysqT7QZLBjegET0e52WklQ7BBYWXvv8xpbvr8=",
            1863450: "M0PgiJutAM_L9jvyfrGDWnbfJOXmhYt_skL0S88ngkU=",
            1830190: "v-5GfMaI2ozfmef5BNO5hI-fEGwtKjuI1XcuTDh-wsg=",
            1835544: "LI14DbKGBfJExlwLodr6fkV4Pv4eABWkEhzArPbPSR8=",
            1820930: "zoTviAO0EACFC4rFereJuc0A-99Xf_uOdq3GiqUpoeU=",
        }

        self.commands = {"GMA": "Midterm Average", "GL1A": "Lab 1 Average", "GL2A": "Lab 2 Average", "GL3A": "Lab 3 Average", "GL4A": "Lab 4 Average", "GEA": "Exam Average", "GG": "Grades"}
        self.client_socket = socket.socket()  # instantiate
        self.client_socket.connect((host, port))  # connect to the server

        self.client_program()
        pass

    def decode_message_bytes(self, message_bytes, student_number):
        key = self.secret_key_dict[int(student_number)]
        fernet = Fernet(key)
        decrypted_message_bytes =  fernet.decrypt(message_bytes)
        return decrypted_message_bytes.decode('utf-8')

    def client_program(self):

        command = ""
        while command.lower().strip() != 'bye':
            student_number = input("Enter your student number: ")  # take input
            command = input("Enter your command: ")  # take input
            print(f"Command entered: {command}")
            if command not in self.commands:
                print("Invalid command")
                continue
            else:
                print(f"Fetching {self.commands[command]}")
            command = student_number + "," + command
            self.client_socket.send(command.encode())  # send command

            encrpyted_message_bytes = self.client_socket.recv(1024).decode()  # receive response
            message = self.decode_message_bytes(encrpyted_message_bytes, student_number)

            print('Received from server: ' + message)  # show in terminal

        self.client_socket.close()  # close the connection


if __name__ == '__main__':
    roles = {'client': Client,'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles,
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()