from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import validator
from .board import Board, Move
from .constants import ALL_SQUARES, FILES, Color, PieceType
from .notation import TypedMove, parse_move
from .pieces import Pawn, Piece, create_piece
from .validator import IllegalMoveError


class GameStatus(Enum):
    ONGOING = "ongoing"
    CHECK = "check"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    DRAW_BY_MATERIAL = "draw by insufficient material"
    DRAW_BY_REPETITION = "draw by threefold repetition"
    DRAW_BY_FIFTY_MOVES = "draw by the fifty-move rule"
    DRAW_BY_AGREEMENT = "draw by agreement"
    RESIGNED = "resigned"

    @property
    def is_over(self) -> bool:
        return self not in (GameStatus.ONGOING, GameStatus.CHECK)

    @property
    def is_draw(self) -> bool:
        return self in (
            GameStatus.STALEMATE,
            GameStatus.DRAW_BY_MATERIAL,
            GameStatus.DRAW_BY_REPETITION,
            GameStatus.DRAW_BY_FIFTY_MOVES,
            GameStatus.DRAW_BY_AGREEMENT,
        )


@dataclass
class PlayedMove:
    color: Color
    move: Move
    promotion: PieceType | None = None


class Game:
    """One game: the position, whose turn it is, the history and everything the rules must remember."""

    def __init__(self) -> None:
        self.board = Board()
        self.turn = Color.WHITE
        self.status = GameStatus.ONGOING
        self.winner: Color | None = None
        self.check_count = 0                       # attackers of the king to move; 2 = double check
        self.history: list[PlayedMove] = []
        self.captured: list[Piece] = []
        self.en_passant_pawn: Piece | None = None  # the pawn that just moved two squares
        self.moves_without_progress = 0            # since the last pawn move or capture
        self.position_counts: dict[str, int] = {self.position_key(): 1}

    @property
    def is_over(self) -> bool:
        return self.status.is_over

    # ---- finding and playing moves ---------------------------------------------------------

    def find_move(self, typed: TypedMove) -> Move:
        """The legal move the player means. Raises IllegalMoveError with the reason otherwise."""
        if self.is_over:
            raise IllegalMoveError("The game is over.")
        return validator.resolve_move(self.board, self.turn, typed, self.en_passant_pawn)

    def needs_promotion(self, move: Move) -> bool:
        return validator.is_promotion(move)

    def legal_moves(self) -> list[Move]:
        return validator.legal_moves(self.board, self.turn, self.en_passant_pawn)

    def play(self, move: Move, promotion: PieceType | str | None = None) -> None:
        """Plays a move returned by find_move(). A promotion needs the piece to promote to."""
        piece = move.piece
        promotion_type = None
        if validator.is_promotion(move):
            if not promotion:
                raise ValueError("a promotion needs a piece: Q, R, B or N")
            promotion_type = PieceType(promotion) if isinstance(promotion, str) else promotion

        self.board.apply(move)
        piece.has_moved = True
        if move.rook is not None:
            move.rook.has_moved = True
        if promotion_type is not None:
            new_piece = create_piece(promotion_type, piece.color, move.target)
            new_piece.has_moved = True
            self.board.replace(piece, new_piece)
        if move.captured is not None:
            self.captured.append(move.captured)
        self.history.append(PlayedMove(self.turn, move, promotion_type))

        if isinstance(piece, Pawn) and abs(move.target[0] - move.origin[0]) == 2:
            self.en_passant_pawn = piece
        else:
            self.en_passant_pawn = None
        if isinstance(piece, Pawn) or move.captured is not None:
            self.moves_without_progress = 0
        else:
            self.moves_without_progress += 1

        self.turn = self.turn.opponent
        self.check_count = validator.check_count(self.board, self.turn)
        position = self.position_key()
        self.position_counts[position] = self.position_counts.get(position, 0) + 1
        self._update_status(position)

    def make_move(self, text: str, promotion: PieceType | str | None = None) -> Move:
        """Finds and plays a move given in notation, like 'e4' or 'e8=Q'."""
        typed = parse_move(text.strip().rstrip("+#"))
        if typed is None:
            raise IllegalMoveError(f"Invalid move: {text!r}")
        move = self.find_move(typed)
        self.play(move, promotion or typed.promotion or None)
        return move

    def resign(self) -> None:
        self.status = GameStatus.RESIGNED
        self.winner = self.turn.opponent

    def agree_draw(self) -> None:
        self.status = GameStatus.DRAW_BY_AGREEMENT

    # ---- game status -----------------------------------------------------------------------

    def _update_status(self, position: str) -> None:
        if not validator.has_legal_move(self.board, self.turn, self.en_passant_pawn):
            if self.check_count > 0:
                self.status = GameStatus.CHECKMATE
                self.winner = self.turn.opponent
            else:
                self.status = GameStatus.STALEMATE
        elif validator.insufficient_material(self.board):
            self.status = GameStatus.DRAW_BY_MATERIAL
        elif self.position_counts[position] >= 3:
            self.status = GameStatus.DRAW_BY_REPETITION
        elif self.moves_without_progress >= 100:
            self.status = GameStatus.DRAW_BY_FIFTY_MOVES
        elif self.check_count > 0:
            self.status = GameStatus.CHECK
        else:
            self.status = GameStatus.ONGOING

    def position_key(self) -> str:
        """Equal for two positions exactly when they count as a repetition: same side to move,
        same pieces on the same squares, same castling rights and same en passant chance."""
        key = self.turn.value[0]
        for square in ALL_SQUARES:
            piece = self.board.piece_at(square)
            key += piece.symbol if piece is not None else "--"
        for color in (Color.WHITE, Color.BLACK):
            for king_side in (True, False):
                key += "c" if validator.has_castling_right(self.board, color, king_side) else "-"
        passed = self.en_passant_pawn
        if passed is not None:
            # a double step only matters when an enemy pawn beside it could capture it
            row, col = passed.square
            for side_col in (col - 1, col + 1):
                neighbour = self.board.piece_at((row, side_col))
                if isinstance(neighbour, Pawn) and neighbour.color == self.turn:
                    key += FILES[col]
                    break
        return key
