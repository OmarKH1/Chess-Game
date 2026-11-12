from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from .constants import Color, PieceType, Square, distance

if TYPE_CHECKING:
    from .board import Board


class Piece:
    """A chess piece. Each kind says in attacks() which squares it threatens."""

    kind: ClassVar[PieceType]

    def __init__(self, color: Color, square: Square) -> None:
        self.color = color
        self.square = square
        self.has_moved = False  # castling needs a king and rook that never moved

    @property
    def symbol(self) -> str:
        """The two letters shown on the board, like WQ or BP."""
        return self.color.letter + self.kind.value

    def attacks(self, board: Board, target: Square) -> bool:
        """True when the piece threatens the square: right direction and nothing in the way."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.color.name}, {self.square})"


class Rook(Piece):
    kind = PieceType.ROOK

    def attacks(self, board: Board, target: Square) -> bool:
        rows, cols = distance(self.square, target)
        return target != self.square and (rows == 0 or cols == 0) and board.is_path_clear(self.square, target)


class Bishop(Piece):
    kind = PieceType.BISHOP

    def attacks(self, board: Board, target: Square) -> bool:
        rows, cols = distance(self.square, target)
        return target != self.square and rows == cols and board.is_path_clear(self.square, target)


class Queen(Piece):
    kind = PieceType.QUEEN

    def attacks(self, board: Board, target: Square) -> bool:
        rows, cols = distance(self.square, target)
        on_line = rows == 0 or cols == 0 or rows == cols
        return target != self.square and on_line and board.is_path_clear(self.square, target)


class Knight(Piece):
    kind = PieceType.KNIGHT

    def attacks(self, board: Board, target: Square) -> bool:
        return distance(self.square, target) in ((1, 2), (2, 1))


class King(Piece):
    kind = PieceType.KING

    def attacks(self, board: Board, target: Square) -> bool:
        return max(distance(self.square, target)) == 1


class Pawn(Piece):
    kind = PieceType.PAWN

    @property
    def direction(self) -> int:
        return self.color.forward

    @property
    def start_row(self) -> int:
        return self.color.pawn_row

    @property
    def last_row(self) -> int:
        return self.color.opponent.back_row

    def attacks(self, board: Board, target: Square) -> bool:
        # a pawn captures one square diagonally forward
        row, col = self.square
        return target[0] == row + self.direction and abs(target[1] - col) == 1

    def can_push_to(self, board: Board, target: Square) -> bool:
        # a pawn walks straight ahead onto an empty square: one step, or two from its starting row
        row, col = self.square
        if target[1] != col or board.piece_at(target) is not None:
            return False
        if target[0] == row + self.direction:
            return True
        return (
            row == self.start_row
            and target[0] == row + 2 * self.direction
            and board.piece_at((row + self.direction, col)) is None
        )


PIECE_CLASSES: dict[PieceType, type[Piece]] = {
    cls.kind: cls for cls in (King, Queen, Rook, Bishop, Knight, Pawn)
}


def create_piece(kind: PieceType, color: Color, square: Square) -> Piece:
    return PIECE_CLASSES[kind](color, square)
