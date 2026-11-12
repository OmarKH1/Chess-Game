from __future__ import annotations

from enum import Enum

BOARD_SIZE = 8
FILES = "abcdefgh"
RANKS = "12345678"

# A square is (row, col): row 0 is rank 1 and col 0 is the a-file, so e4 is (3, 4).
Square = tuple[int, int]

# Row by row from a1 to h8. Code that builds position keys relies on this order.
ALL_SQUARES: tuple[Square, ...] = tuple((row, col) for row in range(BOARD_SIZE) for col in range(BOARD_SIZE))


class Color(Enum):
    WHITE = "white"
    BLACK = "black"

    @property
    def opponent(self) -> Color:
        return Color.BLACK if self is Color.WHITE else Color.WHITE

    @property
    def letter(self) -> str:
        """'W' or 'B', the first letter of a piece symbol such as WQ."""
        return "W" if self is Color.WHITE else "B"

    @property
    def forward(self) -> int:
        """The row step of a pawn of this color: white walks up the board, black down."""
        return 1 if self is Color.WHITE else -1

    @property
    def back_row(self) -> int:
        return 0 if self is Color.WHITE else BOARD_SIZE - 1

    @property
    def pawn_row(self) -> int:
        return 1 if self is Color.WHITE else BOARD_SIZE - 2


class PieceType(Enum):
    KING = "K"
    QUEEN = "Q"
    ROOK = "R"
    BISHOP = "B"
    KNIGHT = "N"
    PAWN = "P"


PROMOTION_TYPES: tuple[PieceType, ...] = (PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT)


def is_on_board(square: Square) -> bool:
    row, col = square
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def square_from_name(name: str) -> Square:
    """'e4' -> (3, 4)"""
    if len(name) != 2 or name[0] not in FILES or name[1] not in RANKS:
        raise ValueError(f"not a square: {name!r}")
    return RANKS.index(name[1]), FILES.index(name[0])


def square_name(square: Square) -> str:
    """(3, 4) -> 'e4'"""
    row, col = square
    return FILES[col] + RANKS[row]


def distance(start: Square, end: Square) -> tuple[int, int]:
    """How many rows and how many columns lie between two squares."""
    return abs(start[0] - end[0]), abs(start[1] - end[1])
