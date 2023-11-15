import socket
import sys
import threading
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(name)s: %(message)s',
                    )


class UserInputHandler:
    def __init__(self, server, close_event):
        self.server = server
        self.close_event = close_event
        self.logger = logging.getLogger("Input")

    def start(self):
        try:
            while not self.close_event.is_set():
                print("Enter message (type 'close' to shut down the server)\n")
                message = sys.stdin.readline().strip()
                if message == "close":
                    self.server._close_server()
                elif message.startswith("ban"):
                    client_id = message.split(" ")[1]
                    if len(client_id) > 0:
                        try:
                            client = next(
                                client for client in self.server.clients if str(client[1][1]) == client_id)
                            client[0].send("close".encode())
                            self.server._disconnect_client(client)
                        except StopIteration:
                            self.logger.warning("Enter a valid client ID")
                    else:
                        self.logger.warning("Enter a valid client ID")
                else:
                    self.server._broadcast(
                        f"Server << {message}".encode(), self.server.clients)
        except Exception as e:
            if 'I/O operation on closed file.' in {e}:
                pass

    def stop(self):
        self.close_event.set()


class Server:
    def __init__(self, server_address, close_event):
        self.host = server_address[0]
        self.port = server_address[1]
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.close_event = close_event
        self.lock = threading.Lock()
        self.logger = logging.getLogger("Server")
        self.messages_logger = logging.getLogger("Message")

    def start(self):
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.logger.info(f"Listening on {self.host}:{self.port}")

        while not self.close_event.is_set():
            try:
                client_socket, client_address = self.server_socket.accept()
                self.logger.info(
                    f"Connection from client {client_address[0]}:{client_address[1]}")

                # protect client variable
                with self.lock:
                    self.clients.append((client_socket, client_address))

                # assign a thread for each new subscribed client
                client_handler = threading.Thread(
                    target=self._handle_client, args=((client_socket, client_address),))
                client_handler.start()
            except KeyboardInterrupt:
                self._close_server()
            except socket.error as e:
                if 'bad file descriptor' in str(e):
                    self.logger.error(
                        "Server socket is closed or shutdown..!")
                else:
                    self.logger.error(
                        f"Error accepting or handling new connections: {e}")

    # handle incoming messages for each client
    def _handle_client(self, client):
        client_socket = client[0]
        client_address = client[1]
        try:
            while not self.close_event.is_set():
                data = client_socket.recv(2048)
                if not data:
                    break
                else:
                    message = data.decode().strip()
                    if message == "close":
                        self._disconnect_client(client)
                    else:
                        self.messages_logger.info(
                            f"{client_address[1]} << {message}")
                        self._broadcast(
                            f"{client_address[1]} << {message}".encode(),
                            [client_obj for client_obj in self.clients if client_obj != client]
                        )
        except KeyboardInterrupt:
            self._close_server()
        except Exception as e:
            # send a close signal to client's socket when ERROR
            self.logger.warning(f"Error handling client: {e}")
            # close connection with client on ERROR
            with self.lock:
                self.clients.remove(client)

    def _broadcast(self, message, clients):
        for client in clients:
            # client --> (client_socket, client_address)
            try:
                client[0].send(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to client: {e}")
                # close connection with client on ERROR
                with self.lock:
                    self.clients.remove(client)

    def _disconnect_client(self, client):
        client_address = client[1]
        # close connection with client
        with self.lock:
            self.clients.remove(client)
            self.logger.info(
                f"{client_address[1]} has disconnected")
        with self.lock:
            self._broadcast(f"Server << {client_address[1]} has disconnected".encode(),
                            [client_obj for client_obj in self.clients if client_obj != client])

    def _close_server(self):
        self.logger.warning(
            f"Server is shutting down. Informing clients...")
        # send closing message to all subscribed clients
        for client in self.clients:
            client_address = client[1]
            try:
                self.logger.warning(
                    f"Informing client {client_address[0]}:{client_address[1]}...")
                # close connection from client side
                client[0].send("close".encode())
                client_socket = client[0]
                # close connection from server side
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except Exception as e:
                self.logger.error(
                    f"Error sending shutdown message to {client_address[0]}: {e}")

        # clear clients list
        with self.lock:
            self.clients.clear()

        try:
            # Close the server socket
            if not sys.stdin.closed:
                sys.stdin.close()
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
            self.close_event.set()
        except Exception as e:
            self.logger.error({e})
        self.logger.warning("Server has shut down.")


if __name__ == "__main__":
    # address = input("Host IP Address: ")
    # port = input("Port: ")

    close_event = threading.Event()

    server = Server(("127.0.0.1", 12345), close_event)
    start_thread = threading.Thread(target=server.start)
    # send_thread = threading.Thread(
    #     target=server.send_message)

    user_input_handler = UserInputHandler(server, close_event)
    user_input_thread = threading.Thread(target=user_input_handler.start)

    try:
        start_thread.start()
        # send_thread.start()
        user_input_thread.start()
        # waiting for the closing flag
        server.close_event.wait()
    except KeyboardInterrupt:
        close_event.set()
        logging.warning("Server has shut down.")
    finally:
        user_input_handler.stop()
        user_input_thread.join()
        logging.info(f"Exiting...")
