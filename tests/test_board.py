import pytest

from chess_engine import (
    ALL_SQUARES,
    Board,
    Color,
    Move,
    Queen,
    is_on_board,
    square_from_name,
    square_name,
)

sq = square_from_name


def test_starting_position_has_32_pieces(board):
    assert len(board.squares) == 32
    assert len(board.pieces_of(Color.WHITE)) == 16
    assert len(board.pieces_of(Color.BLACK)) == 16


def test_starting_position_squares(board):
    back = "RNBQKBNR"
    for col, file in enumerate("abcdefgh"):
        assert board.piece_at(sq(file + "1")).symbol == "W" + back[col]
        assert board.piece_at(sq(file + "2")).symbol == "WP"
        assert board.piece_at(sq(file + "7")).symbol == "BP"
        assert board.piece_at(sq(file + "8")).symbol == "B" + back[col]
        for rank in "3456":
            assert board.piece_at(sq(file + rank)) is None


def test_kings_are_registered(board):
    assert board.king(Color.WHITE).square == sq("e1")
    assert board.king(Color.BLACK).square == sq("e8")


def test_pieces_know_their_square(board):
    for square, piece in board.squares.items():
        assert piece.square == square
        assert not piece.has_moved


def test_empty_board(empty_board):
    assert empty_board.squares == {}
    assert empty_board.pieces == []


# ---- coordinates ----------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("name", "square"),
    [("a1", (0, 0)), ("h1", (0, 7)), ("a8", (7, 0)), ("h8", (7, 7)), ("e4", (3, 4)), ("d5", (4, 3))],
)
def test_square_names_convert_both_ways(name, square):
    assert square_from_name(name) == square
    assert square_name(square) == name


@pytest.mark.parametrize("bad", ["", "e", "e9", "e0", "i4", "E4", "4e", "e44"])
def test_bad_square_names_are_rejected(bad):
    with pytest.raises(ValueError):
        square_from_name(bad)


def test_every_square_round_trips():
    assert len(ALL_SQUARES) == 64
    for square in ALL_SQUARES:
        assert square_from_name(square_name(square)) == square


@pytest.mark.parametrize(("square", "inside"), [((0, 0), True), ((7, 7), True), ((8, 0), False), ((0, -1), False)])
def test_is_on_board(square, inside):
    assert is_on_board(square) is inside


# ---- moving and capturing -------------------------------------------------------------------

def test_moving_a_piece(board):
    pawn = board.piece_at(sq("e2"))
    move = Move(pawn, sq("e4"))
    board.apply(move)
    assert board.piece_at(sq("e4")) is pawn
    assert board.piece_at(sq("e2")) is None
    assert pawn.square == sq("e4")
    assert move.origin == sq("e2")


def test_undoing_a_move(board):
    pawn = board.piece_at(sq("e2"))
    move = Move(pawn, sq("e4"))
    board.apply(move)
    board.undo(move)
    assert board.piece_at(sq("e2")) is pawn
    assert board.piece_at(sq("e4")) is None


def test_capturing_removes_the_piece(setup):
    board = setup({"e1": "WK", "e8": "BK", "d4": "WR", "d7": "BN"})
    rook, knight = board.piece_at(sq("d4")), board.piece_at(sq("d7"))
    move = Move(rook, sq("d7"), captured=knight)
    board.apply(move)
    assert board.piece_at(sq("d7")) is rook
    assert knight not in board.pieces_of(Color.BLACK)
    assert len(board.squares) == 3


def test_undoing_a_capture_restores_the_piece(setup):
    board = setup({"e1": "WK", "e8": "BK", "d4": "WR", "d7": "BN"})
    rook, knight = board.piece_at(sq("d4")), board.piece_at(sq("d7"))
    move = Move(rook, sq("d7"), captured=knight)
    board.apply(move)
    board.undo(move)
    assert board.piece_at(sq("d7")) is knight
    assert board.piece_at(sq("d4")) is rook


def test_castling_move_moves_the_rook_too(setup):
    board = setup({"e1": "WK", "h1": "WR", "e8": "BK"})
    king, rook = board.piece_at(sq("e1")), board.piece_at(sq("h1"))
    move = Move(king, sq("g1"), rook=rook, rook_target=sq("f1"))
    board.apply(move)
    assert board.piece_at(sq("g1")) is king and board.piece_at(sq("f1")) is rook
    board.undo(move)
    assert board.piece_at(sq("e1")) is king and board.piece_at(sq("h1")) is rook


def test_replace_puts_a_new_piece_on_the_square(setup):
    board = setup({"e1": "WK", "e8": "BK", "a8": "WP"})
    pawn = board.piece_at(sq("a8"))
    queen = Queen(Color.WHITE, sq("a8"))
    board.replace(pawn, queen)
    assert board.piece_at(sq("a8")) is queen
    assert queen in board.pieces_of(Color.WHITE)
    assert pawn not in board.pieces_of(Color.WHITE)


@pytest.mark.parametrize(
    ("start", "end", "clear"),
    [("a1", "a8", False), ("a3", "a6", True), ("c1", "h6", False), ("c3", "f6", True), ("e4", "e5", True)],
)
def test_is_path_clear(board, start, end, clear):
    assert board.is_path_clear(sq(start), sq(end)) is clear


@pytest.mark.parametrize(("start", "end"), [("b1", "c3"), ("a3", "h4")])
def test_is_path_clear_needs_a_line(empty_board, start, end):
    # this used to loop forever on an empty board
    with pytest.raises(ValueError):
        empty_board.is_path_clear(sq(start), sq(end))


# ---- copying --------------------------------------------------------------------------------

def test_copy_is_independent(board):
    clone = board.copy()
    pawn = board.piece_at(sq("e2"))
    board.apply(Move(pawn, sq("e4")))
    assert clone.piece_at(sq("e4")) is None
    assert clone.piece_at(sq("e2")).square == sq("e2")


def test_copy_has_its_own_pieces(board):
    clone = board.copy()
    assert len(clone.squares) == 32
    for square, piece in clone.squares.items():
        assert piece is not board.piece_at(square)
        assert piece.symbol == board.piece_at(square).symbol
    assert clone.king(Color.WHITE) is clone.piece_at(sq("e1"))


def test_attackers_of_a_square(board):
    names = sorted(square_name(p.square) for p in board.attackers(sq("f3"), Color.WHITE))
    assert names == ["e2", "g1", "g2"]
    assert board.attackers(sq("e4"), Color.WHITE) == []


def test_new_board_is_a_fresh_start():
    first, second = Board(), Board()
    first.apply(Move(first.piece_at(sq("e2")), sq("e4")))
    assert second.piece_at(sq("e2")) is not None
