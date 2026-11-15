"""Connect Four board state and win/draw evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field


ROWS = 6
COLUMNS = 7
CONNECT_LENGTH = 4


@dataclass
class GameState:
    """Represent the Connect Four board and the player whose turn is active."""

    board: list[list[str | None]] = field(
        default_factory=lambda: [[None for _ in range(COLUMNS)] for _ in range(ROWS)]
    )
    active_player: str = "player_1"

    def drop_piece(self, column: int, piece: str) -> int | None:
        """Drop a piece into a column; return its row or None if the move is invalid."""
        if type(column) is not int or not 0 <= column < COLUMNS:
            return None
        for row in range(ROWS - 1, -1, -1):
            if self.board[row][column] is None:
                self.board[row][column] = piece
                return row
        return None

    def has_won(self, row: int, column: int, piece: str) -> bool:
        """Return whether the latest move completes a four-piece line."""
        for row_delta, column_delta in ((0, 1), (1, 0), (1, 1), (1, -1)):
            count = 1
            for direction in (-1, 1):
                next_row = row + row_delta * direction
                next_column = column + column_delta * direction
                while (
                    0 <= next_row < ROWS
                    and 0 <= next_column < COLUMNS
                    and self.board[next_row][next_column] == piece
                ):
                    count += 1
                    next_row += row_delta * direction
                    next_column += column_delta * direction
            if count >= CONNECT_LENGTH:
                return True
        return False

    def is_draw(self) -> bool:
        """Return whether every column is full."""
        return all(self.board[0][column] is not None for column in range(COLUMNS))
