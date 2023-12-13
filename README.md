# Socket chatroom/game

Welcome to the Socket Chatroom! This simple chatroom allows users to connect, chat, and play Rock, Paper, Scissors with others. Please follow the instructions below to make the most of your chatroom experience.
## Table of Contents

-   [Features](#Features)
-   [Usage](#usage)



## Features:

#### User Interaction:

- Joining: Users can effortlessly join the chatroom by connecting to the server over a network using sockets. Upon connection, users are prompted to choose a username, establishing their identity within the chat.

- Exiting: Users have the flexibility to exit the chatroom at any time, closing their connection to the server.

#### Server Administration:

- Admin Capabilities: The server operates as an admin entity, managing the chatroom environment. It has the authority to monitor user activities and enforce rules to maintain a smooth and respectful communication atmosphere.

- Kicking Users: As part of admin capabilities, the server can kick users out of the chatroom when necessary, ensuring control and moderation.

#### Interactive Game: Rock, Paper, Scissors:

- In-Chat Game: A unique feature of this chatroom is the integration of the classic game "Rock, Paper, Scissors." Users can initiate game sessions with other participants, engaging in friendly competitions within the chat environment.

- User vs. User Gameplay: The game mechanics enable users to challenge each other to a round of Rock, Paper, Scissors, enhancing the interactive nature of the chatroom.

## Usage
### Chat
- To connect to the chatroom server, open your terminal and use the following command:
```
python player.py 
```
- Upon successfully connecting to the server, you will be prompted to choose a unique username. Enter your desired username and press Enter.
```
Socket: Connected to server on 127.0.0.1:12345
Chat: Server << Enter your username:
```

- Once you've set your username, you can start broadcasting messages to the chatroom. Type your message and press Enter to send it to all connected users.
```
Chat: Server << Welcome hamza :)
Chat: hamza joined the chatroom
|
```
- To exit the chatroom and close your connection, type the following command:
```
close
```
### Rock, Paper, Scissors game
- If you'd like to play Rock, Paper, Scissors with another user, use the following command:

```
play <opponent-username>
```
Replace <opponent-username> with the username of the user you want to challenge. If the user accepts your request, the game will begin.
- To exit a game in progress, type:
``` 
exit
```

### Admin Commands
Admins have perticular commands to manage the chatroom:

- Kick User:
```
close <username>
```
Replace <username> with the username of the user you want to kick.

- Close Server:

```
close .
```
This command will gracefully close the chatroom server.


