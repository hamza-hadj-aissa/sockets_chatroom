import socket
import threading

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.client_socket.connect((self.host, self.port))
        print(f"Connected to server on {self.host}:{self.port}")

    def send_message(self):
        try:
            while True:
                message = input(">> ")
                if not message:
                    pass
                else:
                    self.client_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")
        # finally:
            # self.client_socket.close()

    def receive_messages(self):
        try:
            while True:
                data = self.client_socket.recv(1024)
                if not data:
                    self.client_socket.close()
                    break
                message = data.decode('utf-8')
                print(f"\n{message}", flush=True, end="")
                
        except Exception as e:
            print(f"Error receiving message: {e}")
        # finally:
        #     self.client_socket.close()

if __name__ == "__main__":
    client = Client('127.0.0.1', 12345)
    client.connect()

    send_thread = threading.Thread(target=client.send_message)
    receive_thread = threading.Thread(target=client.receive_messages)

    send_thread.start()
    receive_thread.start()

    send_thread.join()
    receive_thread.join()