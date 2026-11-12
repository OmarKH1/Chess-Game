"""The rules of chess as pure functions on a Board. Nothing here reads input or prints.

Functions that test a move try it on the board and take it back, so the board is left as it was.
"""

from __future__ import annotations

from collections.abc import Iterator

from .board import Board, Move
from .constants import ALL_SQUARES, FILES, Color, PieceType, Square, square_name
from .notation import TypedMove
from .pieces import PIECE_CLASSES, Bishop, Knight, Pawn, Piece, Queen, Rook


class IllegalMoveError(Exception):
    """The move cannot be played. str(error) is the message for the player."""


# ---- attacks and check ---------------------------------------------------------------------

def attackers(board: Board, square: Square, color: Color) -> list[Piece]:
    """The pieces of that color that attack the square."""
    return board.attackers(square, color)


def check_count(board: Board, color: Color) -> int:
    """How many enemy pieces attack the king of that color: 0, 1 or 2 (double check)."""
    return len(board.attackers(board.king(color).square, color.opponent))


def is_in_check(board: Board, color: Color) -> bool:
    return check_count(board, color) > 0


def keeps_king_safe(board: Board, move: Move) -> bool:
    """True when the mover's king is not attacked after the move.

    This one test covers pinned pieces, a king walking into check and having to answer a check.
    """
    color = move.piece.color
    board.apply(move)
    safe = not board.attackers(board.king(color).square, color.opponent)
    board.undo(move)
    return safe


# ---- how pieces move ----------------------------------------------------------------------

def piece_move(board: Board, piece: Piece, target: Square, en_passant_pawn: Piece | None = None) -> Move | None:
    """The move of that piece to that square, or None when the piece does not move like that.

    Check is not looked at here; see keeps_king_safe().
    """
    if isinstance(piece, Pawn):
        return pawn_push(board, piece, target) or pawn_capture(board, piece, target, en_passant_pawn)
    occupant = board.piece_at(target)
    if occupant is not None and occupant.color == piece.color:
        return None
    if piece.attacks(board, target):
        return Move(piece, target, captured=occupant)
    return None


def pawn_push(board: Board, pawn: Pawn, target: Square) -> Move | None:
    if pawn.can_push_to(board, target):
        return Move(pawn, target)
    return None


def pawn_capture(board: Board, pawn: Pawn, target: Square, en_passant_pawn: Piece | None = None) -> Move | None:
    if not pawn.attacks(board, target):
        return None
    occupant = board.piece_at(target)
    if occupant is not None:
        if occupant.color == pawn.color:
            return None
        return Move(pawn, target, captured=occupant)
    # en passant: the enemy pawn that just moved two squares stands beside this pawn,
    # and is captured by moving to the square it jumped over
    passed = en_passant_pawn
    if passed is not None and passed.color != pawn.color and passed.square == (pawn.square[0], target[1]):
        return Move(pawn, target, captured=passed)
    return None


def is_promotion(move: Move) -> bool:
    return isinstance(move.piece, Pawn) and move.target[0] == move.piece.last_row


# ---- castling -----------------------------------------------------------------------------

def has_castling_right(board: Board, color: Color, king_side: bool) -> bool:
    """True while that king and that rook have both never moved and stand on their starting squares."""
    king = board.king(color)
    rook = board.piece_at((color.back_row, 7 if king_side else 0))
    return (
        king.square == (color.back_row, 4)
        and not king.has_moved
        and isinstance(rook, Rook)
        and rook.color == color
        and not rook.has_moved
    )


def castling_move(board: Board, color: Color, king_side: bool) -> Move:
    """The castling move, or IllegalMoveError saying why it is not allowed."""
    king = board.king(color)
    row = color.back_row
    if king_side:
        rook_col, rook_target_col, king_path, must_be_empty = 7, 5, (5, 6), (5, 6)
    else:
        rook_col, rook_target_col, king_path, must_be_empty = 0, 3, (3, 2), (3, 2, 1)
    if not has_castling_right(board, color, king_side):
        raise IllegalMoveError("Illegal move! You cannot castle, the king or that rook has already moved.")
    if any(board.piece_at((row, col)) is not None for col in must_be_empty):
        raise IllegalMoveError("Illegal move! You cannot castle, there is a piece between the king and the rook.")
    if is_in_check(board, color):
        raise IllegalMoveError("Illegal move! You cannot castle while your king is in check.")
    for col in king_path:
        if not keeps_king_safe(board, Move(king, (row, col))):
            raise IllegalMoveError(
                "Illegal move! You cannot castle, the king would cross or land on an attacked square."
            )
    rook = board.piece_at((row, rook_col))
    return Move(king, (row, king_path[-1]), rook=rook, rook_target=(row, rook_target_col))


# ---- all legal moves and how a game ends ---------------------------------------------------

def _piece_moves(board: Board, color: Color, en_passant_pawn: Piece | None) -> Iterator[Move]:
    for piece in board.pieces_of(color):
        for target in ALL_SQUARES:
            move = piece_move(board, piece, target, en_passant_pawn)
            if move is not None and keeps_king_safe(board, move):
                yield move


def legal_moves(board: Board, color: Color, en_passant_pawn: Piece | None = None) -> list[Move]:
    """Every legal move of that side. A promotion is listed once; the piece is chosen when playing it."""
    moves = list(_piece_moves(board, color, en_passant_pawn))
    for king_side in (True, False):
        try:
            moves.append(castling_move(board, color, king_side))
        except IllegalMoveError:
            pass
    return moves


def has_legal_move(board: Board, color: Color, en_passant_pawn: Piece | None = None) -> bool:
    # castling can be skipped: whenever it is legal, the king can also step one square
    return any(True for _ in _piece_moves(board, color, en_passant_pawn))


def is_checkmate(board: Board, color: Color, en_passant_pawn: Piece | None = None) -> bool:
    return is_in_check(board, color) and not has_legal_move(board, color, en_passant_pawn)


def is_stalemate(board: Board, color: Color, en_passant_pawn: Piece | None = None) -> bool:
    return not is_in_check(board, color) and not has_legal_move(board, color, en_passant_pawn)


def insufficient_material(board: Board) -> bool:
    """True when nobody can mate any more: bare kings, a single knight, or only same-colored bishops."""
    knights = 0
    bishop_square_colors: set[int] = set()
    for piece in board.squares.values():
        if isinstance(piece, (Pawn, Rook, Queen)):
            return False
        if isinstance(piece, Knight):
            knights += 1
        if isinstance(piece, Bishop):
            bishop_square_colors.add(sum(piece.square) % 2)
    if knights == 0:
        return len(bishop_square_colors) <= 1
    return knights == 1 and not bishop_square_colors


# ---- turning typed notation into a legal move ----------------------------------------------

def candidate_moves(board: Board, color: Color, typed: TypedMove, en_passant_pawn: Piece | None = None) -> list[Move]:
    """Every move that fits the typed text and the way the piece moves. Check is not looked at."""
    target = typed.target
    if target is None:
        return []
    moves: list[Move | None] = []
    if typed.piece == "K":
        moves.append(piece_move(board, board.king(color), target))
    elif typed.piece in "QRBN":
        piece_class = PIECE_CLASSES[PieceType(typed.piece)]
        for piece in board.pieces_of(color, piece_class):
            if typed.fits_origin(piece.square):
                moves.append(piece_move(board, piece, target))
    elif typed.piece in FILES:
        for pawn in board.pieces_of(color, Pawn):
            if FILES[pawn.square[1]] != typed.piece:
                continue
            assert isinstance(pawn, Pawn)
            if typed.is_push:
                moves.append(pawn_push(board, pawn, target))
            elif typed.is_capture:
                moves.append(pawn_capture(board, pawn, target, en_passant_pawn))
    return [move for move in moves if move is not None]


def resolve_move(board: Board, color: Color, typed: TypedMove, en_passant_pawn: Piece | None = None) -> Move:
    """The one legal move the player means, or IllegalMoveError with the reason."""
    if typed.is_castling:
        return castling_move(board, color, typed.text == "O-O")
    if check_count(board, color) >= 2 and typed.piece != "K":
        raise IllegalMoveError("Illegal move! It is a double check, only the king can move.")

    possible = candidate_moves(board, color, typed, en_passant_pawn)
    legal = [move for move in possible if keeps_king_safe(board, move)]
    if not legal and typed.text[:2] == "bx":
        # no b pawn can make this capture, so a lowercase "bxe5" is read as a bishop capture
        typed = TypedMove("B" + typed.text[1:])
        bishop_moves = candidate_moves(board, color, typed, en_passant_pawn)
        possible += bishop_moves
        legal = [move for move in bishop_moves if keeps_king_safe(board, move)]

    if len(legal) == 1:
        return legal[0]
    if len(legal) > 1:
        assert typed.target is not None
        raise IllegalMoveError(
            f"Ambiguous move! More than one piece can go to {square_name(typed.target)}. "
            f"Type {_clearer_ways_to_type(legal, typed)}."
        )
    if not possible:
        raise IllegalMoveError("Illegal move! Please try a different move.")
    # the piece can move like that, but its own king would be attacked afterwards
    if is_in_check(board, color):
        raise IllegalMoveError("Illegal move! Your king is in check and that move does not save it.")
    if typed.piece == "K":
        raise IllegalMoveError("Illegal move! The king cannot move to an attacked square.")
    raise IllegalMoveError("Illegal move! That piece is pinned, moving it would leave your king in check.")


def _clearer_ways_to_type(moves: list[Move], typed: TypedMove) -> str:
    """How to type each of several moves the text cannot tell apart, like 'Nbd2 or Nfd2'."""
    assert typed.target is not None
    origins = [square_name(move.origin) for move in moves]
    options = []
    for origin in origins:
        on_same_file = sum(other[0] == origin[0] for other in origins)
        on_same_rank = sum(other[1] == origin[1] for other in origins)
        # the shortest thing that tells this piece apart: its file, else its rank, else its whole square
        if on_same_file == 1:
            start = origin[0]
        elif on_same_rank == 1:
            start = origin[1]
        else:
            start = origin
        capture = "x" if typed.is_capture else ""
        options.append(typed.piece + start + capture + square_name(typed.target))
    return " or ".join(options)
