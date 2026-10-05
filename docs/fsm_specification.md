```stateDiagram-v2
stateDiagram-v2
    
    [*] --> INIT : Start-up Server

    INIT --> WAITING_FOR_PLAYERS : Socket Binds Successfully
    
    WAITING_FOR_PLAYERS --> WAITING_FOR_PLAYERS : Client 1 CONNECT Recieved (Goes to LOBBY_WAIT)
    WAITING_FOR_PLAYERS --> GAME_START : Client 2 CONNECT Recieved

    GAME_START --> PLAYER_TURN : Initialize Game Board and Assign Roles

    PLAYER_TURN --> EVALUATE_MOVE : Active Player Sends Any Kind of MOVE
    
    PLAYER_TURN --> GAME_OVER : Client Disconnect / Socket Exception (Opponent Forfeit Win)

    EVALUATE_MOVE --> PLAYER_TURN : Valid Move, Send STATE_UPDATE and Swap Active Player
    EVALUATE_MOVE --> PLAYER_TURN : Move Invalid / Out-of-Bounds / Out-of-Turn / Invalid Payload (Send ERROR to Player)
    EVALUATE_MOVE --> GAME_OVER : Win Condition or Draw Detected

    GAME_OVER --> CLEANUP : Game Ends and Results are Displayed

    CLEANUP --> WAITING_FOR_PLAYERS : Reset Memory State and Tear Down Current Sockets
    CLEANUP --> [*] : Server Process Terminated
```

### State 1: INIT
* **Description:** The system boots, allocates memory, and binds the primary tracking socket to the specified server port.
* **Transition Trigger:** Successful network socket binding pushes the server into the listening and waiting state.

### State 2: WAITING_FOR_PLAYERS
* **Description:** The server enters a listening state waiting for connection requests over the raw TCP socket.
* **Handling Logic:**
  * When **Client 1** connects and sends a valid 'CONNECT' payload, the server stores their player properties, and replies immediately with a 'LOBBY_WAIT' packet. The server remains in this state.
  * When **Client 2** connects and sends their 'CONNECT' payload, the server pairs the two users together,  and advances to the next state.

### State 3: GAME_START
* **Description:** The match parameters are initialized. The engine assigns roles (player_1 as "X", player_2 as "O") and designates player_1 as the initial active player.
* **Handling Logic:** The engine constructs a GAME_START message containing role matrices and broadcasts it to both open clients before shifting processing to the execution loops.

### State 4: PLAYER_TURN
* **Description:** The application enters a blocked polling sequence, waiting for incoming wire messages from the designated active player whos payload holds details about what move the player wants to make.
* **Handling Logic:** 
  * If a 'MOVE' arrives from the correct active player, data passes immediately to 'EVALUATE_MOVE' for validation.
  * **Edge Case (Out-of-Turn Move):** If the inactive player attempts to transmit a 'MOVE' payload, the server intercepts it, rejects processing, generates an 'ERROR' message ('type_of_error: "out_of_turn"'), and replies only to that specific client while holding the current state layout the same.
  * **Edge Case (Abrupt Disconnect):** If a client socket throws an explicit networking exception ('ConnectionResetError' / 'BrokenPipeError') or returns a '0-byte EOF' read flag during this listening state, the server aborts the turn loop immediately and forces a hard transition straight to 'GAME_OVER'.

### State 5: EVALUATE_MOVE
* **Description:** The server uses the payload received from the active player to run internal processing calculations against the active grid coordinate map.
* **Handling Logic:**
  * **Invalid Payloads:** If the integer parsed out of the column parameter resides outside the functional board limits (e.g., column <0 or >5), or if that column data slot is already entirely full, the system drops the placement request, transmits an 'ERROR' message back to the active client ('type_of_error: "invalid_coordinates"'), and loops right back into 'PLAYER_TURN' targeting the same player.
  * **Valid Move Iteration:** If the coordinate checks pass cleanly, the engine updates the games data structure board state, and switches the 'active_player' value to point to the opposing client ID, sends out a 'STATE_UPDATE' broadcast packet to both users, and returns to 'PLAYER_TURN'.
  * **Terminal Calculations:** If the placement completes a winning match combination or consumes the final empty column slot on the array structure, the game terminates the turn sequence entirely and moves to the concluding step.

### State 6: GAME_OVER
* **Description:** The active match structure wraps up and calculates finishing scores.
* **Handling Logic:** The system compiles a terminal 'GAME_OVER' summary block detailing final scores, final gameboard states, and the concluding victory scenario flags ('WIN', 'LOSS','DRAW', or 'FORFEIT'). This payload is sent to all players sockets before releasing execution targets.

### State 7: CLEANUP
* **Description:** The process shuts down current instance of the game and cleans session contexts.
* **Handling Logic:** The internal application engine purges match boards, releases memory references, isolates lingering connection nodes, and issues final TCP FIN teardown arrays to remaining sockets. Once clean, the server goes back into 'WAITING_FOR_PLAYERS' to accept players for the next round.