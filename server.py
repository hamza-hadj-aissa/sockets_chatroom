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
                if message.split(" ")[0] == "close":

                    # close a socket, either server or client
                    message_array = message.split(" ")
                    print("message_array", message_array)
                    target_to_close = message_array[1]
                    print("target", target_to_close)
                    if target_to_close == ".":
                        # "." stands for the host machine, which is the server
                        # close the server
                        self.server._close_server()
                    else:
                        # close the client's socket
                        client_username = target_to_close
                        if len(client_username) > 0 or client_username != "":
                            found = False
                            for client in self.server.clients:
                                if client_username == client[0]:
                                    found = True
                                    client[1].send("close".encode())
                                    self.server._disconnect_client(client)
                            if not found:
                                self.logger.warning(
                                    "Username does not exist. Enter a valid username:")
                        else:
                            self.logger.warning("Enter a valid username:")
                else:
                    # broadcast a message to all subscribed clients
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

                username = self._request_client_username(
                    client_socket, client_address, "Server << Enter your username:", 0)
                if username:
                    # assign a thread for each new subscribed client
                    client_handler = threading.Thread(
                        target=self._handle_client, args=((username, client_socket, client_address),))
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
        client_username = client[0]
        client_socket = client[1]
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
                            f"{client_username} << {message}")
                        self._broadcast(
                            f"{client_username} << {message}".encode(),
                            [client_obj for client_obj in self.clients if client_obj != client]
                        )
        except KeyboardInterrupt:
            self._close_server()
        except Exception as e:
            # send a close signal to client's socket when ERROR
            self.logger.warning(f"Error handling client: {e}")
            # close connection with client on ERROR
            with self.lock:
                self.clients.pop(client)

    def _broadcast(self, message, clients):
        for client in clients:
            # client --> (client_username, client_socket, client_address)
            try:
                client[1].send(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to client: {e}")
                # close connection with client on ERROR
                with self.lock:
                    self.clients.pop(client)

    def _request_client_username(self, client_socket, client_address, message, nbr_of_attempts):
        max_nbr_of_attempts = 3
        if nbr_of_attempts >= max_nbr_of_attempts:
            client_socket.send(
                "close\nServer << You have succeded the number of attempts!!".encode())
        else:
            # request username
            client_socket.send(message.encode())
            # wait for client's response
            username = client_socket.recv(2048).decode().strip()

            if len(username) > 0:
                # block access to self.clients variable
                self.lock.acquire()
                if username not in [user[0] for user in self.clients]:
                    # username accepted
                    self.clients.append(
                        (username, client_socket, client_address))
                    # permet access to self.clients variable
                    self.lock.release()
                    client_socket.send(
                        f"Server << Welcome {username} :)".encode())
                    self.logger.info(f"{username} joined the chatroom")
                    # inform other clients
                    self._broadcast(
                        f"{username} joined the chatroom".encode(), [client for client in self.clients if client[0] != username])
                    return username
                else:
                    # permet access to self.clients variable if first condition not satisfied.
                    # Preventing undefinete block of access to self.clients
                    self.lock.release()

                    # request another username
                    self._request_client_username(
                        client_socket, client_address, f"Server << Username is already taken. {3 - nbr_of_attempts - 1} attempts left. Enter a different username:", nbr_of_attempts + 1)
            else:
                # invalide username format
                self._request_client_username(
                    client_socket, client_address, f"Server << Invalid username. {max_nbr_of_attempts - nbr_of_attempts - 1} attempts left. Enter a different username:", nbr_of_attempts + 1)

    def _disconnect_client(self, client):
        client_username = client[0]
        # close connection with client
        with self.lock:
            self.clients.remove(client)
            self.logger.info(
                f"{client_username} has disconnected")
        with self.lock:
            self._broadcast(f"Server << {client_username} has disconnected".encode(),
                            [client_obj for client_obj in self.clients if client_obj != client])

    def _close_server(self):
        self.logger.warning(
            f"Server is shutting down. Informing clients...")
        # send closing message to all subscribed clients
        for client in self.clients:
            client_username = client[0]
            try:
                self.logger.warning(
                    f"Informing client {client_username}...")
                # close connection from client side
                client_socket = client[1]
                client_socket.send("close".encode())
                # close connection from server side
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except Exception as e:
                self.logger.error(
                    f"Error sending shutdown message to {client_username}: {e}")

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
