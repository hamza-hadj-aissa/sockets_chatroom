from enum import Enum
import socket
import threading
import logging
from time import sleep
from typing import List, override

from server import Client
from server import Server, Socket_address, UserInputHandler
logging.basicConfig(level=logging.INFO,
                    format='%(name)s: %(message)s',
                    )


class TooManyPlayersError(Exception):
    pass


class NumberOfInvalidInputsExceeded(Exception):
    pass


class InvalideInput(Exception):
    pass


class RPSEnum(Enum):
    NoChoice = 0
    Rock = 1
    Paper = 2
    Scissors = 3


class Player(Client):
    def __init__(self, client: Client, busy: bool = True):
        super().__init__(client.getSocket(), client.getAddress(), client.getUsername())
        self.__choice: RPSEnum = RPSEnum.NoChoice
        self.__score: int = 0
        self.__lock = threading.Lock()

    def getScore(self):
        return self.__score

    def incrementScore(self):
        self.__score += 1

    def getChoice(self) -> RPSEnum:
        return self.__choice

    def setChoice(self, choice: RPSEnum):
        self.__choice = choice

    def getClient(self):
        return Client(self.getSocket(), self.getAddress(), self.getUsername())

    def do_lock(self):
        self.__lock.acquire()

    def do_unlock(self):
        self.__lock.release()

    def is_locked(self):
        return self.__lock.locked()


class GameServer(Server):
    def __init__(self, server_address, close_event):
        super().__init__(server_address, close_event)
        self.games: List[Game] = list()
        self.clients: List[Player] = list()
        self.logger = logging.getLogger("Game server")
        self.chat_logger = logging.getLogger("Chat")
        self.games_requests: list[tuple(str, str)] = []
        self.games_requests_lock = threading.Lock()

    @override
    def start(self):
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(4)
        self.logger.info(f"Listening on {self.host}:{self.port}")

        while not self.close_event.is_set():
            try:
                client_socket, client_address = self.server_socket.accept()
                self.logger.info(
                    f"Connection from client {client_address[0]}:{client_address[1]}")

                new_player = self._request_client_username(
                    client_socket, client_address, "Server << Enter your username:", 0)
                if new_player:
                    # assign a thread for each new subscribed client
                    client_handler = threading.Thread(
                        target=self._handle_client, args=(new_player,))
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

    @override
    def _request_client_username(self, client_socket, client_address, message, nbr_of_attempts):
        max_nbr_of_attempts = 3
        if nbr_of_attempts >= max_nbr_of_attempts:
            # close client's connection
            client_socket.send(
                "close".encode())
        else:
            # request username
            client_socket.send(message.encode())
            # wait for client's response
            username = client_socket.recv(2048).decode().strip()

            if len(username) > 0:
                # block access to self.clients variable
                self.lock.acquire()
                # check if username is not already taken
                if username not in [client.getUsername() for client in self.clients]:
                    new_player = Player(
                        Client(
                            socket=client_socket,
                            address=Socket_address(
                                ip=client_address[0],
                                port=client_address[1]
                            ),
                            username=username
                        )
                    )
                    # username accepted
                    self.clients.append(
                        new_player
                    )
                    # permet access to self.clients variable
                    self.lock.release()
                    client_socket.send(
                        f"Server << Welcome {username} :)".encode())
                    self.logger.info(f"{username} joined the chatroom")
                    # inform other clients
                    with self.lock:
                        self._broadcast(
                            f"{username} joined the chatroom".encode(), [client for client in self.clients if client.getUsername() != username])
                    return new_player
                else:
                    # permet access to self.clients variable if first condition not satisfied.
                    # Preventing undefinete block of access to self.clients
                    self.lock.release()

                    # request another username
                    self._request_client_username(
                        client_socket, client_address, f"Server << Username is already taken. Connection will be closed on no attempts left. {3 - nbr_of_attempts - 1} attempts left. Enter a different username:", nbr_of_attempts + 1)
            else:
                # invalide username format
                self._request_client_username(
                    client_socket, client_address, f"Server << Invalid username. Connection will be closed on no attempts left. {3 - nbr_of_attempts - 1} attempts left. Enter a different username:", nbr_of_attempts + 1)

    # handle incoming messages for each client

    @override
    def _handle_client(self, player: Player):
        try:
            while not self.close_event.is_set():
                data = player.getSocket().recv(1024)
                if not data:
                    break
                else:
                    message = data.decode().strip()
                    # client requesting closing connection
                    if message == "close":
                        self._disconnect_client(player)
                    # client requesting starting a match with an oppenent
                    elif message.split(" ")[0] == "play":
                        # check if client exists
                        oppenent_username = message.split(" ")[1]
                        oppenent_exists, opponent, error_message = self.__get_opponent(
                            oppenent_username)
                        if oppenent_username == player.getUsername():
                            player.getSocket().send(
                                f"Server << Please enter a valid oppenent's username".encode())
                            if player.is_locked():
                                player.do_unlock()

                        else:
                            if oppenent_exists:
                                self.games_requests.append(
                                    (player.getUsername(), oppenent_username)
                                )
                                opponent.getSocket().send(f"Server << {player.getUsername(
                                )} is requesting to play Rock Paper Scissors with you. Do you accept ?".encode()
                                )
                                # lock the requesting player here,
                                # until the game ends

                                player.do_lock()

                            else:
                                player.getSocket().send(
                                    f"Server << {error_message}".encode()
                                )
                                if player.is_locked():
                                    player.do_unlock()

                    elif message.split(" ")[0].startswith("accept"):
                        oppenent_exists, opponent, error_message = self.__get_game_request(
                            player
                        )
                        if oppenent_exists:
                            with self.games_requests_lock:
                                self.games_requests = [game_request for game_request in self.games_requests if game_request != (
                                    opponent.getUsername(), player.getUsername())
                                ]
                            new_game = Game(self)
                            with new_game.lock:
                                new_game.addPlayer(player)
                                new_game.addPlayer(opponent)
                            with self.lock:
                                self.games.append(new_game)
                            game_thread = threading.Thread(
                                target=new_game.start_game
                            )
                            game_thread.start()
                            # end of game
                            game_thread.join()
                            # release opponenet lock
                            # if player.is_locked():
                            #     player.do_unlock()
                            # # inform opponent
                            # remove the game from the list of games
                            with self.lock:
                                self.games = [
                                    game for game in self.games if game.id != new_game.id
                                ]
                        else:
                            player.getSocket().send(
                                f"Server << {error_message}".encode())
                    else:
                        client_username = player.getUsername()
                        self.chat_logger.info(
                            f"{client_username} << {message}"
                        )
                        with self.lock:
                            players_list = [player.getUsername(
                            ) for game in self.games for player in game.players]

                            self._broadcast(
                                f"{client_username} << {message}".encode(),
                                [
                                    client for client in self.clients
                                    if client.getUsername()
                                    not in players_list
                                    and client_username not in players_list
                                ]
                            )
                        if player.is_locked():
                            player.do_unlock()
        except KeyboardInterrupt:
            self._close_server()
        except socket.error as e:
            # send a close signal to client's socket when ERROR
            self.logger.warning(f"Error handling client: {e}")
            # close connection with client on ERROR
            with self.lock:
                self.clients.remove(player)

    def __get_game_request(self, oppenent: Player) -> (bool, Player | None):
        with self.games_requests_lock:
            error_message = ""
            # check if the request exists
            for games_request in self.games_requests:
                if games_request[1] == oppenent.getUsername():
                    # check if the oppenent exists
                    oppenent_exists, oppenent, message = self.__get_opponent(
                        games_request[0]
                    )
                    error_message = message
                    if oppenent_exists:
                        return True, oppenent, None
        return False, None, error_message

    def __get_opponent(self, oppenent_username: str) -> (bool, Player | None, str | None):
        with self.lock:
            player_busy = [player for game in self.games for player in game.players if player.getUsername(
            ) == oppenent_username]
            if len(player_busy) > 0:
                return False, None, "Player is busy playing another match"

            for client in self.clients:
                if client.getUsername() == oppenent_username:
                    return True, client, None
            return False, None, f"Player <{oppenent_username}> not found"


class Game():
    id = 0

    def __init__(self, gameServer: GameServer):
        self.gameServer = gameServer
        self.players: List[Player] = list()
        self.lock = threading.Lock()
        self.game_close_event = threading.Event()
        self.logger = logging.getLogger("Game")
        Game.id += 1

    def start_game(self):
        # Start the rock-paper-scissors game logic here
        player1, player2 = self.players

        while not self.game_close_event.is_set():
            self.logger.info(
                f"Game Started {player1.getUsername()} VS {
                    player2.getUsername()}"
            )
            player1.getSocket().send(
                f"Server << You are playing against <{
                    player2.getUsername()}>".encode()
            )
            player2.getSocket().send(
                f"Server << You are playing against <{
                    player1.getUsername()}>".encode()
            )

            self.gameServer._broadcast("Server << Make your choice...\n1- Rock\n2- Paper\n3- Scissors".encode(),
                                       [player1.getClient(), player2.getClient()]
                                       )
            # assign a thread for each new subscribed client
            player1_handler = threading.Thread(
                target=self.__handle_client, args=(player1,), daemon=True)
            player2_handler = threading.Thread(
                target=self.__handle_client, args=(player2,), daemon=True)
            player1_handler.start()
            player2_handler.start()

            player1_handler.join()
            player2_handler.join()
            if self.game_close_event.is_set():
                # Reset players for the next round
                with self.lock:
                    for player in self.players:
                        player.setChoice(RPSEnum.NoChoice)
                break
            result = self.__determine_winner(RPSEnum(player1.getChoice(
            )), RPSEnum(player2.getChoice()))

            if result == 0:
                self.logger.info(
                    f"{player1.getUsername()} VS {player2.getUsername()} << It's a tie!")
                self.server._broadcast("Server << It's a tie!".encode(), [
                    player1.getClient(), player2.getClient()])
            elif result == 1:
                self.logger.info(
                    f"{player1.getUsername()} VS {player2.getUsername()} << {player1.getUsername()} won!!")
                player1.getSocket().send("Server << You win!!".encode())
                self.gameServer._broadcast(f"Server << {player1.getUsername()} wins!".encode(), [
                    player2.getClient()])
                player1.incrementScore()
            else:
                self.logger.info(
                    f"{player1.getUsername()} VS {player2.getUsername()} << {player2.getUsername()} won!!")
                player2.getSocket().send("Server << You win!!".encode())
                self.gameServer._broadcast(f"Server << You lost :((".encode(), [
                    player1.getClient()])
                player2.incrementScore()

            # Reset players for the next round
            with self.lock:
                for player in self.players:
                    player.setChoice(RPSEnum.NoChoice)

    # handle incoming messages for each client
    def __handle_client(self, player: Player):
        while not self.game_close_event.is_set() and player.getChoice() == RPSEnum.NoChoice:
            data = player.getSocket().recv(1024)
            if not data:
                player.setChoice(RPSEnum.NoChoice)
            else:
                message = data.decode().strip()
                if message == "close":
                    self.server._disconnect_client(player.getClient())
                else:
                    player_username = player.getClient().getUsername()
                    with self.lock:
                        opponent = [
                            other_player for other_player in self.players if other_player.getUsername() != player_username
                        ][0]
                    if message in ["1", "2", "3"]:
                        player.setChoice(RPSEnum(int(message)))
                        self.gameServer.logger.info(
                            f"{player_username} VS {opponent.getUsername()} << {player_username} chose {RPSEnum(int(message)).name}")
                    elif message == "exit":
                        opponent = [opponent for oppenent in self.players if opponent.getUsername(
                        ) != player_username
                        ]
                        if len(opponent) > 0:
                            opponent[0].getSocket().send(f"Server << {player_username} quit the game. You win :)".encode()
                                                         )
                            while not self.game_close_event.is_set():
                                player.getSocket().send(
                                    f"Server << Waiting for your oppenent to exit the game...".encode())
                                sleep(1)

                            player.getSocket().send(
                                f"Server << Welcome back to the chat :)".encode())
                            if player.is_locked():
                                player.do_unlock()
                            return
                    elif message == "quit":
                        self.game_close_event.set()
                        player.getSocket().send(f"Server << Welcome back to the chat :)".encode())
                        if player.is_locked():
                            player.do_unlock()
                        return
                    else:
                        if not self.game_close_event.is_set():
                            player.getSocket().send("Server << Please enter a valid choice!".encode())

    def __determine_winner(self, choice1: RPSEnum, choice2: RPSEnum):
        if choice1 == RPSEnum.Rock:
            return self.rock(choice2)
        elif choice1 == RPSEnum.Paper:
            return self.paper(choice2)
        elif choice1 == RPSEnum.Scissors:
            return self.scissors(choice2)
        else:
            return 2

    def addPlayer(self, player: Player):
        if len(self.players) < 2:
            self.players.append(player)
        else:
            raise TooManyPlayersError("Number of players exceeded")

    def rock(self, other_choice):
        if other_choice == 'rock':
            return 0  # Tie
        elif other_choice == 'paper':
            return 2  # Player 2 wins
        elif other_choice == 'scissors':
            return 1  # Player 1 wins

    def paper(self, other_choice):
        if other_choice == 'rock':
            return 1  # Player 1 wins
        elif other_choice == 'paper':
            return 0  # Tie
        elif other_choice == 'scissors':
            return 2  # Player 2 wins

    def scissors(self, other_choice):
        if other_choice == 'rock':
            return 2  # Player 2 wins
        elif other_choice == 'paper':
            return 1  # Player 1 wins
        elif other_choice == 'scissors':
            return 0  # Tie


if __name__ == "__main__":
    close_event = threading.Event()

    server = GameServer(("127.0.0.1", 12345), close_event)
    start_thread = threading.Thread(target=server.start)

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
