from __future__ import annotations

from collections.abc import Callable

import pytest

from chess_engine import (
    Board,
    Color,
    Game,
    Piece,
    PieceType,
    create_piece,
    legal_moves,
    square_from_name,
    square_name,
)

# A layout maps square names to piece symbols, like {"e1": "WK", "e8": "BK"}.
Layout = dict[str, str]


def build_board(layout: Layout) -> Board:
    board = Board.empty()
    for name, symbol in layout.items():
        color = Color.WHITE if symbol[0] == "W" else Color.BLACK
        board.add(create_piece(PieceType(symbol[1]), color, square_from_name(name)))
    return board


def move_targets(board: Board, square: str, en_passant_pawn: Piece | None = None) -> set[str]:
    """The squares the piece on `square` can legally move to (castling not included)."""
    piece = board.piece_at(square_from_name(square))
    assert piece is not None, f"no piece on {square}"
    return {
        square_name(move.target)
        for move in legal_moves(board, piece.color, en_passant_pawn)
        if move.piece is piece and move.rook is None
    }


@pytest.fixture
def board() -> Board:
    return Board()


@pytest.fixture
def empty_board() -> Board:
    return Board.empty()


@pytest.fixture
def setup() -> Callable[[Layout], Board]:
    return build_board


@pytest.fixture
def targets() -> Callable[..., set[str]]:
    return move_targets


@pytest.fixture
def game() -> Game:
    return Game()


@pytest.fixture
def play() -> Callable[[str], Game]:
    """Plays a space-separated list of moves from the starting position."""

    def _play(moves: str) -> Game:
        new_game = Game()
        for text in moves.split():
            new_game.make_move(text)
        return new_game

    return _play


@pytest.fixture
def custom_game() -> Callable[..., Game]:
    """A game that starts from a custom layout."""

    def _custom_game(layout: Layout, turn: Color = Color.WHITE) -> Game:
        return Game(build_board(layout), turn)

    return _custom_game
