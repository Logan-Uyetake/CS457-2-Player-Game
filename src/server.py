"""Threaded, terminal-friendly Connect Four TCP server."""

from __future__ import annotations

import argparse
import socket
import threading
import time
from typing import Any

from gamestate import COLUMNS, GameState
from protocol_handler import extract_messages, serialize_message


def _message(msg_type: str, **fields: Any) -> dict[str, Any]:
    return {"msg_type": msg_type, **fields, "timestamp": int(time.time())}


class ClientConnection:
    def __init__(self, sock: socket.socket, address: tuple[str, int]) -> None:
        self.socket = sock
        self.address = address
        self.player_id = ""
        self.role = ""
        self.send_lock = threading.Lock()
        self.game: Game | None = None
        self.closed = False

    def send(self, message: dict[str, Any]) -> None:
        packet = serialize_message(message)
        with self.send_lock:
            self.socket.sendall(packet)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.socket.close()


class Game:
    def __init__(self, server: "GameServer", player_1: ClientConnection,
                 player_2: ClientConnection) -> None:
        self.server = server
        self.players = {"player_1": player_1, "player_2": player_2}
        self.state = GameState()
        self.lock = threading.RLock()
        self.finished = False
        player_1.role = "player_1"
        player_2.role = "player_2"
        player_1.game = self
        player_2.game = self

    def start(self) -> None:
        for player, piece in (
            (self.players["player_1"], "X"),
            (self.players["player_2"], "O"),
        ):
            try:
                player.send(
                    _message(
                        "GAME_START",
                        payload={
                            "player_1": {
                                "player_id": self.players["player_1"].player_id,
                                "piece": "X",
                            },
                            "player_2": {
                                "player_id": self.players["player_2"].player_id,
                                "piece": "O",
                            },
                            "active_player": "player_1",
                        },
                        server_message=f"Game started. You are {piece}.",
                    )
                )
            except OSError:
                self.disconnect(player, "connection_lost")

    def handle(self, client: ClientConnection, message: dict[str, Any]) -> None:
        if message["msg_type"] == "DISCONNECT":
            self.disconnect(client, "forfeit")
            return
        if message["msg_type"] != "MOVE":
            client.send(
                _message(
                    "ERROR",
                    payload={
                        "type_of_error": "unexpected_message",
                        "error_message": "Only MOVE or DISCONNECT is accepted during a game.",
                    },
                )
            )
            return

        with self.lock:
            if self.finished:
                return
            if message["player_id"] != client.player_id:
                self._send_error(
                    client, "player_id_mismatch", "The player_id does not match your connection."
                )
                return
            if client.role != self.state.active_player:
                self._send_error(client, "out_of_turn", "It is not your turn.")
                return

            column = message["payload"]["column"]
            if not 0 <= column < COLUMNS:
                self._send_error(
                    client, "invalid_coordinates", f"Choose a column from 0 to {COLUMNS - 1}."
                )
                return
            piece = "X" if client.role == "player_1" else "O"
            row = self.state.drop_piece(column, piece)
            if row is None:
                self._send_error(
                    client, "invalid_coordinates", "That column is full; choose another."
                )
                return

            if self.state.has_won(row, column, piece):
                self._finish(winner=client.player_id, result="WIN", reason="connect_four")
            elif self.state.is_draw():
                self._finish(winner="", result="DRAW", reason="board_full")
            else:
                self.state.active_player = (
                    "player_2" if client.role == "player_1" else "player_1"
                )
                self._broadcast(
                    _message(
                        "STATE_UPDATE",
                        payload={
                            "board": self.state.board,
                            "active_player": self.state.active_player,
                        },
                    )
                )

    def disconnect(self, client: ClientConnection, reason: str) -> None:
        with self.lock:
            if self.finished:
                return
            opponent = self.players[
                "player_2" if client.role == "player_1" else "player_1"
            ]
            if opponent.closed:
                self.finished = True
                self.server.game_finished(self)
                return
            self._finish(
                winner=opponent.player_id,
                result="FORFEIT",
                reason="opponent_disconnected" if reason != "forfeit" else "opponent_forfeit",
            )

    def _send_error(self, client: ClientConnection, error_type: str, text: str) -> None:
        try:
            client.send(
                _message(
                    "ERROR",
                    payload={"type_of_error": error_type, "error_message": text},
                )
            )
        except OSError:
            self.disconnect(client, "connection_lost")

    def _broadcast(self, message: dict[str, Any]) -> None:
        failed_players = []
        for player in self.players.values():
            try:
                player.send(message)
            except OSError:
                failed_players.append(player)
        for player in failed_players:
            self.disconnect(player, "connection_lost")

    def _finish(self, winner: str, result: str, reason: str) -> None:
        if self.finished:
            return
        self.finished = True
        self._broadcast(
            _message(
                "GAME_OVER",
                payload={
                    "result": result,
                    "winner": winner,
                    "reason": reason,
                    "board": self.state.board,
                },
            )
        )
        self.server.game_finished(self)
        for player in self.players.values():
            player.close()


class GameServer:
    def __init__(self, port: int) -> None:
        self.port = port
        self.lock = threading.Lock()
        self.waiting_player: ClientConnection | None = None
        self.active_game: Game | None = None

    def game_finished(self, game: Game) -> None:
        with self.lock:
            if self.active_game is game:
                self.active_game = None

    def register(self, client: ClientConnection, player_id: str) -> None:
        with self.lock:
            if self.active_game is not None:
                client.send(
                    _message(
                        "ERROR",
                        payload={
                            "type_of_error": "game_in_progress",
                            "error_message": "A game is already in progress. Try again later.",
                        },
                    )
                )
                client.close()
                return
            if self.waiting_player is None:
                client.player_id = player_id
                self.waiting_player = client
                client.send(
                    _message(
                        "LOBBY_WAIT",
                        server_message="Waiting for player 2 to connect...",
                    )
                )
                print(f"{player_id} joined; waiting for player 2.", flush=True)
                return
            if self.waiting_player.player_id == player_id:
                client.send(
                    _message(
                        "ERROR",
                        payload={
                            "type_of_error": "duplicate_player_id",
                            "error_message": "Choose a player name different from Player 1.",
                        },
                    )
                )
                client.close()
                return

            client.player_id = player_id
            first = self.waiting_player
            self.waiting_player = None
            game = Game(self, first, client)
            self.active_game = game
            print(
                f"Starting game: {first.player_id} (X) vs {player_id} (O).",
                flush=True,
            )
        game.start()

    def remove_waiting(self, client: ClientConnection) -> None:
        with self.lock:
            if self.waiting_player is client:
                self.waiting_player = None

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listening_socket:
            listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listening_socket.bind(("0.0.0.0", self.port))
            listening_socket.listen()
            print(f"Connect Four server listening on 0.0.0.0:{self.port}", flush=True)
            while True:
                client_socket, address = listening_socket.accept()
                client = ClientConnection(client_socket, address)
                worker = threading.Thread(
                    target=self._serve_client,
                    args=(client,),
                    name=f"client-{address[0]}-{address[1]}",
                    daemon=True,
                )
                worker.start()

    def _serve_client(self, client: ClientConnection) -> None:
        buffer = b""
        registered = False
        try:
            while True:
                chunk = client.socket.recv(4096)
                if not chunk:
                    break
                messages, buffer = extract_messages(buffer + chunk)
                for message in messages:
                    if not registered:
                        if message["msg_type"] != "CONNECT":
                            client.send(
                                _message(
                                    "ERROR",
                                    payload={
                                        "type_of_error": "expected_connect",
                                        "error_message": "Send CONNECT before any other message.",
                                    },
                                )
                            )
                            return
                        player_id = message["player_id"].strip()
                        if not player_id or len(player_id) > 24:
                            client.send(
                                _message(
                                    "ERROR",
                                    payload={
                                        "type_of_error": "invalid_player_id",
                                        "error_message": (
                                            "Player names must be 1 to 24 characters."
                                        ),
                                    },
                                )
                            )
                            return
                        self.register(client, player_id)
                        registered = True
                    elif client.game is not None:
                        client.game.handle(client, message)
                    else:
                        client.send(
                            _message(
                                "ERROR",
                                payload={
                                    "type_of_error": "not_in_game",
                                    "error_message": "You are not currently in a game.",
                                },
                            )
                        )
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        except ValueError as exc:
            try:
                client.send(
                    _message(
                        "ERROR",
                        payload={"type_of_error": "malformed_message", "error_message": str(exc)},
                    )
                )
            except OSError:
                pass
        finally:
            if not registered:
                self.remove_waiting(client)
            elif client.game is None:
                self.remove_waiting(client)
            elif not client.game.finished:
                client.game.disconnect(client, "connection_lost")
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the terminal Connect Four server.")
    parser.add_argument("-p", "--port", type=int, required=True, help="TCP listening port")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    GameServer(args.port).serve_forever()


if __name__ == "__main__":
    main()
