import select
import socket
import sys
import threading
from typing import override
from client import Client


class Player(Client):
    def __init__(self, host, port, close_event):
        super().__init__(host, port, close_event)

    @override
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
                            self._close_connection_from_server()
                        if decoded_message.endswith("quit the game. You win :)"):
                            self.messages_logger.info(message.decode().strip())
                            self.server_socket.send("quit".encode())
                        else:
                            self.messages_logger.info(message.decode().strip())
            except socket.error as e:
                self.logger.error(f"Error connecting to the server: {e}")


if __name__ == "__main__":
    close_event = threading.Event()

    client = Player("127.0.0.1", 12345, close_event)
    client.connect()

    send_thread = threading.Thread(
        target=client.send_message)
    receive_thread = threading.Thread(target=client.receive_messages)

    send_thread.start()
    receive_thread.start()

    close_event.wait()

    print("Press <Enter> to exit...")
