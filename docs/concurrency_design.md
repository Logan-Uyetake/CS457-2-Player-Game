sequenceDiagram
    participant Server
    actor Client1
    actor Client2

    Server->>Server: INIT: Boot & Bind Socket
    activate Server
    Server->>Server: Socket Binds Successfully
    Note over Server: Enter WAITING_FOR_PLAYERS
    deactivate Server

    Client1->>Server: CONNECT Payload
    activate Server
    Server->>Server: Store Player 1 Properties
    Server->>Client1: LOBBY_WAIT
    Note over Server: Remain in WAITING_FOR_PLAYERS
    deactivate Server

    Client2->>Server: CONNECT Payload
    activate Server
    Server->>Server: Pair Players Together
    Note over Server: Transition to GAME_START
    deactivate Server

    Server->>Server: Initialize Game Board
    Server->>Server: Assign Roles (P1=X, P2=O)
    Server->>Server: Set P1 as Active Player
    Note over Server: Enter PLAYER_TURN

    activate Server
    Server->>Client1: GAME_START (roles, board)
    Server->>Client2: GAME_START (roles, board)
    deactivate Server

    loop PLAYER_TURN - EVALUATE_MOVE Cycle
        Client1->>Server: MOVE Payload (Active Player)
        activate Server
        alt Valid Move
            Server->>Server: Update Board State
            Server->>Server: Swap Active Player to P2
            Server->>Client1: STATE_UPDATE
            Server->>Client2: STATE_UPDATE
            Note over Server: Return to PLAYER_TURN
        else Invalid Coordinates
            Server->>Client1: ERROR (invalid_coordinates)
            Note over Server: Stay in PLAYER_TURN (P1 active)
        else Move Out-of-Bounds
            Server->>Client1: ERROR (out_of_bounds)
            Note over Server: Stay in PLAYER_TURN (P1 active)
        else Win or Draw Detected
            Server->>Server: Detect Terminal Condition
            Note over Server: Transition to GAME_OVER
        end
        deactivate Server
    end

    alt Client Disconnect / Socket Exception
        Client1--xServer: ConnectionResetError / BrokenPipeError
        activate Server
        Note over Server: Force Transition to GAME_OVER
        deactivate Server
    end

    Server->>Server: Compile GAME_OVER Summary
    Server->>Server: Calculate Final Scores
    Note over Server: Enter GAME_OVER

    activate Server
    Server->>Client1: GAME_OVER (scores, board, result)
    Server->>Client2: GAME_OVER (scores, board, result)
    deactivate Server

    Server->>Server: Purge Match Board
    Server->>Server: Release Memory References
    Server->>Server: Close Sockets (TCP FIN)
    Note over Server: Enter CLEANUP

    alt Next Round
        Server->>Server: Reset Memory State
        Note over Server: Return to WAITING_FOR_PLAYERS
    else Server Shutdown
        Note over Server: Process Terminated
    end