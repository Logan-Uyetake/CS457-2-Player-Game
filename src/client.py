"""Terminal client for the threaded Connect Four server."""

from __future__ import annotations

import argparse
import socket
import sys
import time
from typing import Any

from gamestate import COLUMNS
from protocol_handler import extract_messages, serialize_message


def _message(msg_type: str, **fields: Any) -> dict[str, Any]:
    return {"msg_type": msg_type, **fields, "timestamp": int(time.time())}


def _render_board(board: list[list[str | None]]) -> None:
    print("\n  " + "   ".join(str(column) for column in range(COLUMNS)))
    print("+" + "---+" * COLUMNS)
    for row in board:
        print("| " + " | ".join(cell or " " for cell in row) + " |")
        print("+" + "---+" * COLUMNS)


def _receive_message(
    sock: socket.socket, buffer: bytes, pending: list[dict[str, Any]]
) -> tuple[dict[str, Any], bytes]:
    while True:
        if pending:
            return pending.pop(0), buffer
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Server closed the connection.")
        messages, buffer = extract_messages(buffer + chunk)
        pending.extend(messages)


def run_client(hostname: str, port: int, player_id: str) -> int:
    try:
        server_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        print(f"[ERROR] Unable to resolve DNS hostname '{hostname}'.")
        print(
            "Please check your Cisco router DNS configuration "
            "('ip dns server' / 'ip host') or verify domain spelling."
        )
        return 1

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((server_ip, port))
            client_socket.sendall(
                serialize_message(_message("CONNECT", player_id=player_id))
            )
            buffer = b""
            pending_messages: list[dict[str, Any]] = []
            role = ""
            piece = ""
            board = [[None for _ in range(COLUMNS)] for _ in range(6)]
            current_turn = ""

            while True:
                message, buffer = _receive_message(
                    client_socket, buffer, pending_messages
                )
                msg_type = message["msg_type"]
                if msg_type == "LOBBY_WAIT":
                    print(message["server_message"], flush=True)
                elif msg_type == "GAME_START":
                    payload = message["payload"]
                    print(f"\n{message['server_message']}", flush=True)
                    for player_role in ("player_1", "player_2"):
                        player = payload[player_role]
                        if player["player_id"] == player_id:
                            role = player_role
                            piece = player["piece"]
                        print(f"{player['player_id']} plays {player['piece']}")
                    board = [[None for _ in range(COLUMNS)] for _ in range(6)]
                    current_turn = payload["active_player"]
                    _render_board(board)
                elif msg_type == "STATE_UPDATE":
                    board = message["payload"]["board"]
                    current_turn = message["payload"]["active_player"]
                    _render_board(board)
                elif msg_type == "ERROR":
                    error = message["payload"]
                    print(f"[{error['type_of_error']}] {error['error_message']}")
                elif msg_type == "GAME_OVER":
                    payload = message["payload"]
                    board = payload["board"]
                    _render_board(board)
                    winner = payload["winner"]
                    result = payload["result"]
                    if result == "DRAW":
                        print("Game over: draw. Final score: 0.5 - 0.5")
                    else:
                        if winner == player_id:
                            print(f"Game over: you won ({payload['reason']}). Final score: 1 - 0")
                        else:
                            print(
                                f"Game over: {winner} won ({payload['reason']}). "
                                f"Final score: 0 - 1"
                            )
                    return 0

                if role and current_turn == role and msg_type in {
                    "GAME_START",
                    "STATE_UPDATE",
                    "ERROR",
                }:
                    while True:
                        try:
                            choice = input(
                                f"\nYour Turn ({piece}). Enter column 0-{COLUMNS - 1} "
                                "(or q to forfeit): "
                            ).strip().lower()
                        except EOFError:
                            choice = "q"
                        if choice in {"q", "quit"}:
                            client_socket.sendall(
                                serialize_message(
                                    _message(
                                        "DISCONNECT",
                                        player_id=player_id,
                                        payload={"reason": "quit"},
                                    )
                                )
                            )
                            break
                        try:
                            column = int(choice)
                        except ValueError:
                            print("Enter a column number or q to quit.")
                            continue
                        if not 0 <= column < COLUMNS:
                            print(f"Column must be between 0 and {COLUMNS - 1}.")
                            continue
                        client_socket.sendall(
                            serialize_message(
                                _message(
                                    "MOVE",
                                    player_id=player_id,
                                    payload={"column": column},
                                )
                            )
                        )
                        print("Waiting for the other player...")
                        break
    except (ConnectionError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Play Connect Four in the terminal.")
    parser.add_argument("-i", "--hostname", required=True, help="Server DNS hostname")
    parser.add_argument("-p", "--port", type=int, required=True, help="Server TCP port")
    parser.add_argument(
        "-n", "--name", help="Player name (prompted if omitted)"
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    player_id = (args.name or input("Enter your player name: ")).strip()
    if not player_id:
        parser.error("player name cannot be empty")
    sys.exit(run_client(args.hostname, args.port, player_id))


if __name__ == "__main__":
    main()
