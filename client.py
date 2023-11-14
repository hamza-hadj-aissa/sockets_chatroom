import socket
import threading
import sys
import select


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.close_event = threading.Event()

    def connect(self):
        connection = self.server_socket.connect_ex((self.host, self.port))
        if connection == 0:
            print(f"Connected to server on {self.host}:{self.port}")
        else:
            print(f"Connection failed to server on {self.host}:{self.port}")
            self.close_event.set()
            sys.exit()

    def receive_messages(self):
        while not self.close_event.is_set():
            sockets_list = [sys.stdin, self.server_socket]
            try:
                read_sockets, write_socket, error_socket = select.select(
                    sockets_list, [], [])
                for socks in read_sockets:
                    if socks == self.server_socket:
                        message = socks.recv(2048)
                        decoded_message = message.decode()
                        if (decoded_message == "close"):
                            print("Server is shutting down...!")
                            self.server_socket.shutdown(socket.SHUT_RDWR)
                            self.server_socket.close()
                            self.close_event.set()
                            # sys.exit()
                        else:
                            print(message.decode(), end="")
            except socket.error as e:
                print(f"Error connecting to the server: {e}")
        print("Closing connection",
              self.close_event.is_set())

    def send_message(self):
        while not self.close_event.is_set() and not sys.stdin.closed:
            try:
                message = sys.stdin.readline()
                if len(message) > 0:
                    self.server_socket.send(message.encode())
            except Exception as e:
                if {e} == "I/O operation on closed file":
                    print({e})
        print("Connection closed..!")


if __name__ == "__main__":
    # address = input("IP Address: ")
    # port = input("Port: ")
    client = Client("127.0.0.1", 12435)
    client.connect()

    send_thread = threading.Thread(target=client.send_message, daemon=True)
    receive_thread = threading.Thread(target=client.receive_messages)

    send_thread.start()
    receive_thread.start()

    receive_thread.join()
    print("Exit...")
    quit()
