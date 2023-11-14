import socket
import sys
import threading


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.close_event = threading.Event()

    def start(self):
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")

        while not self.close_event.is_set():
            try:
                client_socket, client_address = self.server_socket.accept()
                print(
                    f"Connection from client {client_address[0]}:{client_address[1]}")

                # assign a thread for each new subscribed client
                client_handler = threading.Thread(target=self._handle_client, args=(
                    client_socket, client_address))
                client_handler.start()
                self.clients.append((client_socket, client_address))
            except socket.error as e:
                if 'bad file descriptor' in str(e):
                    print("Server socket is closed or shutdown..!")
                else:
                    print(f"Error accepting or handling new connections: {e}")

    # handle incoming messages for each client
    def _handle_client(self, client_socket, client_address):
        try:
            while not self.close_event.is_set():
                data = client_socket.recv(1024)
                if not data:
                    break
                message = data.decode('utf-8')
                print(client_address[1], "<<", message, end="")
                self._broadcast(
                    f"{client_address[1]} << {message}".encode('utf-8'),
                    [client for client in self.clients if client[1] != client_address]
                )
        except Exception as e:
            # send a close signal to client's socket when ERROR
            print(f"Error handling client: {e}")
            client_socket.send("close".encode('utf-8'))

    # send a message to all clients
    def send_message(self):
        while not self.close_event.is_set():
            if not sys.stdin.closed:
                message = sys.stdin.readline()
                if message.strip() == "close":
                    self._close_server()
                else:
                    self._broadcast(
                        f"server << {message}".encode(), self.clients)

    def _broadcast(self, message, to):
        for client in to:
            try:
                client[0].send(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                # Remove the client from the list if there's an error
                self.clients.remove(client)

    def _close_server(self):
        print("Server is shutting down. Informing clients...")
        # send closing message to all subscribed clients
        for client_socket in self.clients:
            try:
                client_socket[0].send("close".encode('utf-8'))
                print(
                    f"Informeing client {client_socket[1][0]}:{client_socket[1][1]}...")
            except Exception as e:
                print(
                    f"Error sending shutdown message to {client_socket}: {e}")

        try:
            # Close the server socket
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
            self.close_event.set()
        except Exception as e:
            print({e})
        sys.stdin.close()
        print("Server has shut down.")


if __name__ == "__main__":
    # address = input("Host IP Address: ")
    # port = input("Port: ")

    server = Server("127.0.0.1", 12435)
    start_thread = threading.Thread(target=server.start)
    send_thread = threading.Thread(
        target=server.send_message)

    start_thread.start()
    send_thread.start()

    # waiting for the closing flag
    server.close_event.wait()
    server.close_event.set()
    print("Exiting...", server.close_event.is_set())
