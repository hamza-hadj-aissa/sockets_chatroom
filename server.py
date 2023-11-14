import socket
import sys
from _thread import *
import threading


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []

    def start(self):
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}\n")

        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"Connection from {client_address}")
            client_handler = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
            client_handler.start()
            self.clients.append((client_socket, client_address))

    def handle_client(self, client_socket, client_address):
        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                message = data.decode('utf-8')
                print(f"{client_address[1]} << {message}")
                self.broadcast(message, client_address)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def broadcast(self, message, client_address):
        for client in self.clients:
            try:
                if(client[1][1] != client_address[1]):
                    client[0].send(f"{client[1][1]} << {message}".encode('utf-8'))
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                # Remove the client from the list if there's an error
                self.clients.remove(client)
    
    def close_server(self):
        try:
            while True:
                 message = input(">> ")
                 if(message == "0"):
                     print("Closing server...!")
                     self.server_socket.shutdown(1)
                     self.server_socket.close()
                     return
        except Exception as e:
            print(f"Error closing server: {e}")


if __name__ == "__main__":
    server = Server('127.0.0.1', 12345)
    start_thread = threading.Thread(target=server.start)
    close_thread = threading.Thread(target=server.close_server)

    close_thread.start()
    start_thread.start()

    start_thread.join()
    close_thread.join()
