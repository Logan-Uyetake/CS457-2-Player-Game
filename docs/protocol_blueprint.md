## Application Protocol Blueprint

## 1. TCP Stream Packer Framing and Boundary Handling
**Framing Mechanism:** Newline-delimited (`\n`) JSON payloads

**Receiver Extraction Logic:** Read incoming message(could be one or multiple packets strung together) from network socket and scan for the Newline delimiter('\n'). If a Newline is detected, split the chunk at that index. Decode with UTF-8 and pass it to JSON for deserialization.

**Wire Byte Stream Example:** (Back-to-Back Messages)
```json
{"msg_type":"CONNECT","player_id":"Player_Name","timestamp":1727000000}\n{"msg_type":"LOBBY_WAIT","server_message":"Waiting for player 2 to connect...","timestamp":1727000000}\n
```

## 2. Connection Termination and Socket Lifecycle Management
### Graceful Application Disconnection
When a player intends to Quit or Forfeit a match intentionally, it sends a 'DISCONNECT' packet over the wire to the server. Once received, the server finalizes the game and adjusts the victory parameters for the opponent, then the server initiates a TCP FIN teardown handshake and closes down the players socket.

### Abrupt Termination and Network Drop Handling
In the event that a client crashes or encounters a sudden network failure, the server handles the stream drop in the following ways:
* **TCP 0-Byte EOF Detection:** In the server's primary communication loop, calling the network read function('recv()') will return and empty byte string(b'') if a client has closed its end of the socket connection. The server checks for something like len(data) == 0. if True, the server concludes the client has disconnected and moves states from PLAYER_TURN to GAME_OVER with the remaining player being the winner.
* **Socket Error Excpetion Handling:** The network communications will be wrap all socket read and write call in a try-except layer to isolate OS socket exceptions:
  * 'ConnectionResetError': Caught when a client dropts abruptly or forced a hard termination (TCP RST)
  * 'BrokenPipeError': Caught when the server tries to send the STATE_UPDATE packet to a client that has already dropped connection

## Application Message Types


## CONNECT
**Direction:** Client -> Server

**Purpose:** Client requests to join game room with player alias.

**Format:** JSON Schema
```json
{
  "msg_type": "CONNECT",
  "player_id": "Player_Name",
  "timestamp": 1727000000
}
```
**Wire Stream Example:**
```json
{"msg_type":"CONNECT","player_id":"Player_Name","timestamp":1727000000}\n
```

## LOBBY_WAIT
**Direction:** Server -> Client

**Purpose:** Server notifies Client 1 that it is waiting for Player 2 to connect.

**Format:** JSON Schema
```json
{
  "msg_type": "LOBBY_WAIT",
  "server_message": "Waiting for player 2 to connect...",
  "timestamp": 1727000000
}
```
**Wire Stream Example:**
```json
{"msg_type":"LOBBY_WAIT","server_message":"Waiting for player 2 to connect...","timestamp":1727000000}\n
```

## GAME_START
**Direction:** Server -> Client

**Purpose:** Server notifies both clients that game has started and assigns roles (Player 1 / Player 2).

**Format:** JSON Schema
```json
{
  "msg_type": "GAME_START",
  "payload": {
    "player_1": {
        "player_id": "Player_Name",
        "piece": "X"
    },
    "player_2": {
        "player_id": "Player_Name",
        "piece": "O"
    },
    "active_player": "player_1"
  },
  "server_message": "Both players have connected. Starting game.",
  "timestamp": 1727000000
}
```
**Wire Stream Example:**
```json
{"msg_type":"GAME_START","payload":{"player_1":{"player_id":"Player_Name","piece":"X"},"player_2": {"player_id":"Player_Name","piece":"O"},"active_player":"player_1"},"server_message":"Both players have connected. Starting game.","timestamp":1727000000}\n
```

## MOVE
**Direction:** Client -> Server

**Purpose:** Active player submits move coordinates or answer selection.

**Format:** JSON Schema
```json
{
  "msg_type": "MOVE",
  "player_id": "Player_Name",
  "payload": {
    "column": 0
  },
  "timestamp": 1727000000
}
```
**Wire Stream Example:**
```json
{"msg_type":"MOVE","player_id":"Player_Name","payload":{"column":0},"timestamp":1727000000}\n
```

## STATE_UPDATE
**Direction:** Server -> Client

**Purpose:** Server broadcasts updated board state, scores, and active player turn.

**Format:** JSON Schema
```json
{
  "msg_type": "STATE_UPDATE",
  "payload": {
    "board": [
        [],
        [],
        [],
        [],
        [],
        []
    ],
    "active_player": "next player"
  },
  "timestamp": 1727000000
}
```
**Wire Stream Example:**
```json
{"msg_type":"STATE_UPDATE","payload":{"board":[[],[],[],[],[],[]],"active_player":"next player"},"timestamp":1727000000}\n
```

## ERROR
**Direction:** Server -> Client

**Purpose:** Server notifies client of out-of-turn move, invalid coordinates, or malformed message.

**Format:** JSON Schema
```json
{
  "msg_type": "ERROR",
  "payload": {
    "type_of_error": "error type",
    "error_message": "error message"
  },
  "timestamp": 1727000000
}
```
**Wire Stream Example:**
```json
{"msg_type": "ERROR","payload":{"type_of_error":"error type","error_message":"error message"},"timestamp":1727000000}\n
```

## DISCONNECT
**Direction:** Client -> Server

**Purpose:** Client notifies server of intentional departure/quit.

**Format:** JSON Schema
```json
{
  "msg_type": "DISCONNECT",
  "player_id": "Player_Name",
  "payload": {
    "reason": "quit/intentional depart"
  },
  "timestamp": 1727000000
}
```
**Wire Stream Example:**
```json
{"msg_type":"DISCONNECT","player_id":"Player_Name","payload":{"reason":"quit/intentional depart"},"timestamp":1727000000}\n
```

## GAME_OVER
**Direction:** Server -> Client

**Purpose:** Server broadcasts final game outcome (Winner / Draw / Forfeit) and final scores.

**Format:** JSON Schema
```json
{
  "msg_type": "GAME_OVER",
  "payload": {
    "result": "WIN/LOSS/DRAW",
    "winner": "Player_Name/None",
    "reason": "player beath other/won by forfeit",
    "board": [
        [],
        [],
        [],
        [],
        [],
        []
    ]
  },
  "timestamp": 1727000000
}
```
**Wire Stream Example:**
```json
{"msg_type": "GAME_OVER","payload":{"result":"WIN/LOSS/DRAW","winner":"Player_Name/None","reason":"player beath other/won by forfeit","board":[[],[],[],[],[],[]]},"timestamp":1727000000}\n
```