"""JSON message serialization and newline-delimited TCP stream framing."""

from __future__ import annotations

import json
from typing import Any


_MESSAGE_KEYS = {
    "CONNECT": {"msg_type", "player_id", "timestamp"},
    "LOBBY_WAIT": {"msg_type", "server_message", "timestamp"},
    "GAME_START": {"msg_type", "payload", "server_message", "timestamp"},
    "MOVE": {"msg_type", "player_id", "payload", "timestamp"},
    "STATE_UPDATE": {"msg_type", "payload", "timestamp"},
    "ERROR": {"msg_type", "payload", "timestamp"},
    "DISCONNECT": {"msg_type", "player_id", "payload", "timestamp"},
    "GAME_OVER": {"msg_type", "payload", "timestamp"},
}


def _require_keys(value: dict[str, Any], keys: set[str], context: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{context} must contain exactly {sorted(keys)}")


def _require_type(value: Any, expected: type, context: str) -> None:
    if expected is int:
        valid = type(value) is int
    else:
        valid = isinstance(value, expected)
    if not valid:
        raise ValueError(f"{context} must be {expected.__name__}")


def _require_string(value: Any, context: str) -> None:
    _require_type(value, str, context)


def validate_schema(msg_dict: dict[str, Any]) -> None:
    """Validate a message against the protocol's exact key and type rules."""
    if not isinstance(msg_dict, dict):
        raise ValueError("A message must be a JSON object")

    msg_type = msg_dict.get("msg_type")
    if not isinstance(msg_type, str) or msg_type not in _MESSAGE_KEYS:
        raise ValueError("msg_type must be one of the eight approved message types")
    _require_keys(msg_dict, _MESSAGE_KEYS[msg_type], msg_type)
    _require_string(msg_dict["msg_type"], f"{msg_type}.msg_type")
    _require_type(msg_dict["timestamp"], int, f"{msg_type}.timestamp")

    if msg_type in {"CONNECT", "MOVE", "DISCONNECT"}:
        _require_string(msg_dict["player_id"], f"{msg_type}.player_id")

    if msg_type == "LOBBY_WAIT":
        _require_string(msg_dict["server_message"], "LOBBY_WAIT.server_message")
    elif msg_type == "GAME_START":
        _require_string(msg_dict["server_message"], "GAME_START.server_message")
        payload = msg_dict["payload"]
        _require_type(payload, dict, "GAME_START.payload")
        _require_keys(
            payload, {"player_1", "player_2", "active_player"}, "GAME_START.payload"
        )
        for player_key in ("player_1", "player_2"):
            player = payload[player_key]
            _require_type(player, dict, f"GAME_START.payload.{player_key}")
            _require_keys(
                player, {"player_id", "piece"}, f"GAME_START.payload.{player_key}"
            )
            _require_string(
                player["player_id"], f"GAME_START.payload.{player_key}.player_id"
            )
            _require_string(player["piece"], f"GAME_START.payload.{player_key}.piece")
        _require_string(payload["active_player"], "GAME_START.payload.active_player")
    elif msg_type == "MOVE":
        payload = msg_dict["payload"]
        _require_type(payload, dict, "MOVE.payload")
        _require_keys(payload, {"column"}, "MOVE.payload")
        _require_type(payload["column"], int, "MOVE.payload.column")
    elif msg_type == "STATE_UPDATE":
        payload = msg_dict["payload"]
        _require_type(payload, dict, "STATE_UPDATE.payload")
        _require_keys(payload, {"board", "active_player"}, "STATE_UPDATE.payload")
        _require_type(payload["board"], list, "STATE_UPDATE.payload.board")
        for row in payload["board"]:
            _require_type(row, list, "STATE_UPDATE.payload.board row")
        _require_string(payload["active_player"], "STATE_UPDATE.payload.active_player")
    elif msg_type == "ERROR":
        payload = msg_dict["payload"]
        _require_type(payload, dict, "ERROR.payload")
        _require_keys(
            payload, {"type_of_error", "error_message"}, "ERROR.payload"
        )
        _require_string(payload["type_of_error"], "ERROR.payload.type_of_error")
        _require_string(payload["error_message"], "ERROR.payload.error_message")
    elif msg_type == "DISCONNECT":
        payload = msg_dict["payload"]
        _require_type(payload, dict, "DISCONNECT.payload")
        _require_keys(payload, {"reason"}, "DISCONNECT.payload")
        _require_string(payload["reason"], "DISCONNECT.payload.reason")
    elif msg_type == "GAME_OVER":
        payload = msg_dict["payload"]
        _require_type(payload, dict, "GAME_OVER.payload")
        _require_keys(
            payload, {"result", "winner", "reason", "board"}, "GAME_OVER.payload"
        )
        for field in ("result", "winner", "reason"):
            _require_string(payload[field], f"GAME_OVER.payload.{field}")
        _require_type(payload["board"], list, "GAME_OVER.payload.board")
        for row in payload["board"]:
            _require_type(row, list, "GAME_OVER.payload.board row")


def serialize_message(msg_dict: dict[str, Any]) -> bytes:
    """Validate and serialize one protocol message, terminated by a newline."""
    validate_schema(msg_dict)
    return (json.dumps(msg_dict, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def extract_messages(buffer_bytes: bytes | bytearray) -> tuple[list[dict[str, Any]], bytes]:
    """Extract and validate complete newline-framed messages from a byte buffer."""
    buffer = bytes(buffer_bytes)
    messages = []
    while b"\n" in buffer:
        frame, buffer = buffer.split(b"\n", 1)
        try:
            message = json.loads(frame.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid JSON message frame: {exc}") from exc
        validate_schema(message)
        messages.append(message)
    return messages, buffer
