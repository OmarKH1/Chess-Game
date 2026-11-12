from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .constants import BOARD_SIZE, Color, Square
from .pieces import Bishop, King, Knight, Pawn, Piece, Queen, Rook

BACK_RANK: tuple[type[Piece], ...] = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)


@dataclass
class Move:
    """One piece going to one square.

    captured is not always on target: in en passant it stands beside the capturing pawn.
    rook and rook_target are only set for castling.
    """

    piece: Piece
    target: Square
    captured: Piece | None = None
    rook: Piece | None = None
    rook_target: Square | None = None
    origin: Square = field(init=False)
    rook_origin: Square | None = field(init=False)

    def __post_init__(self) -> None:
        self.origin = self.piece.square
        self.rook_origin = self.rook.square if self.rook is not None else None


class Board:
    """The 64 squares and the pieces standing on them."""

    def __init__(self, setup: bool = True) -> None:
        self.squares: dict[Square, Piece] = {}
        self.pieces: list[Piece] = []  # every piece ever placed, captured ones included
        self.kings: dict[Color, Piece] = {}
        if setup:
            self._place_initial_pieces()

    @classmethod
    def empty(cls) -> Board:
        return cls(setup=False)

    def _place_initial_pieces(self) -> None:
        for color in (Color.WHITE, Color.BLACK):
            for col in range(BOARD_SIZE):
                self.add(BACK_RANK[col](color, (color.back_row, col)))
                self.add(Pawn(color, (color.pawn_row, col)))

    # ---- lookup ----------------------------------------------------------------------------

    def add(self, piece: Piece) -> None:
        self.squares[piece.square] = piece
        self.pieces.append(piece)
        if isinstance(piece, King):
            self.kings[piece.color] = piece

    def piece_at(self, square: Square) -> Piece | None:
        return self.squares.get(square)

    def king(self, color: Color) -> Piece:
        return self.kings[color]

    def pieces_of(self, color: Color, kind: type[Piece] = Piece) -> list[Piece]:
        """The pieces of that color (and kind) that are on the board right now."""
        return [
            piece
            for piece in self.pieces
            if piece.color == color and isinstance(piece, kind) and self.squares.get(piece.square) is piece
        ]

    def attackers(self, target: Square, color: Color) -> list[Piece]:
        """The pieces of that color that attack the square."""
        return [piece for piece in self.pieces_of(color) if piece.attacks(self, target)]

    def is_path_clear(self, start: Square, end: Square) -> bool:
        """True when every square strictly between start and end is empty.

        start and end must share a rank, file or diagonal.
        """
        rows, cols = abs(end[0] - start[0]), abs(end[1] - start[1])
        if not (rows == 0 or cols == 0 or rows == cols):
            raise ValueError(f"{start} and {end} are not on one line")
        step_row = (end[0] > start[0]) - (end[0] < start[0])
        step_col = (end[1] > start[1]) - (end[1] < start[1])
        row, col = start[0] + step_row, start[1] + step_col
        while (row, col) != end:
            if (row, col) in self.squares:
                return False
            row += step_row
            col += step_col
        return True

    # ---- move execution --------------------------------------------------------------------

    def apply(self, move: Move) -> None:
        if move.captured is not None:
            del self.squares[move.captured.square]
        self.relocate(move.piece, move.target)
        if move.rook is not None and move.rook_target is not None:
            self.relocate(move.rook, move.rook_target)

    def undo(self, move: Move) -> None:
        self.relocate(move.piece, move.origin)
        if move.rook is not None and move.rook_origin is not None:
            self.relocate(move.rook, move.rook_origin)
        if move.captured is not None:
            self.squares[move.captured.square] = move.captured

    def relocate(self, piece: Piece, square: Square) -> None:
        del self.squares[piece.square]
        piece.square = square
        self.squares[square] = piece

    def replace(self, old_piece: Piece, new_piece: Piece) -> None:
        """Puts new_piece on old_piece's square; used when a pawn promotes."""
        self.squares[old_piece.square] = new_piece
        self.pieces.append(new_piece)

    # ---- copying ---------------------------------------------------------------------------

    def copy(self) -> Board:
        """An independent board: moving pieces on the copy leaves this board untouched."""
        clone = Board.empty()
        twins: dict[int, Piece] = {}
        for piece in self.pieces:
            twin = copy.copy(piece)
            twins[id(piece)] = twin
            clone.pieces.append(twin)
        clone.squares = {square: twins[id(piece)] for square, piece in self.squares.items()}
        clone.kings = {color: twins[id(king)] for color, king in self.kings.items()}
        return clone
