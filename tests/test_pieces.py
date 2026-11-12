import pytest

from chess_engine import Bishop, Color, King, Knight, Pawn, PieceType, Queen, Rook, square_from_name as sq

# Kings out of the way of every piece placed on d4.
KINGS = {"h1": "WK", "a8": "BK"}


def test_piece_symbols_and_kinds(board):
    assert board.piece_at(sq("d1")).symbol == "WQ"
    assert board.piece_at(sq("g8")).symbol == "BN"
    assert isinstance(board.piece_at(sq("e8")), King)
    assert Pawn.kind is PieceType.PAWN


# ---- knight ---------------------------------------------------------------------------------

def test_knight_in_the_center_has_eight_moves(setup, targets):
    board = setup({**KINGS, "d4": "WN"})
    assert targets(board, "d4") == {"b3", "b5", "c2", "c6", "e2", "e6", "f3", "f5"}


def test_knight_in_the_corner_stays_on_the_board(setup, targets):
    board = setup({**KINGS, "a1": "WN"})
    assert targets(board, "a1") == {"b3", "c2"}


def test_knight_blocked_by_friendly_piece_but_captures_enemy(setup, targets):
    board = setup({**KINGS, "a1": "WN", "b3": "WP", "c2": "BP"})
    assert targets(board, "a1") == {"c2"}


def test_knight_jumps_over_pieces(board, targets):
    assert targets(board, "b1") == {"a3", "c3"}
    assert targets(board, "g8") == {"f6", "h6"}


# ---- bishop ---------------------------------------------------------------------------------

def test_bishop_moves_along_both_diagonals(setup, targets):
    board = setup({**KINGS, "d4": "WB"})
    assert targets(board, "d4") == {
        "a1", "b2", "c3", "e5", "f6", "g7", "h8",
        "a7", "b6", "c5", "e3", "f2", "g1",
    }


def test_bishop_from_the_corner(setup, targets):
    board = setup({**KINGS, "a1": "WB"})
    assert targets(board, "a1") == {"b2", "c3", "d4", "e5", "f6", "g7", "h8"}


def test_bishop_stops_before_friend_and_on_enemy(setup, targets):
    board = setup({**KINGS, "d4": "WB", "f6": "WP", "b2": "BN"})
    moves = targets(board, "d4")
    assert "e5" in moves and "f6" not in moves and "g7" not in moves
    assert "b2" in moves and "a1" not in moves


def test_bishop_has_no_moves_at_the_start(board, targets):
    assert targets(board, "c1") == set()


# ---- rook -----------------------------------------------------------------------------------

def test_rook_moves_along_rank_and_file(setup, targets):
    board = setup({**KINGS, "d4": "WR"})
    expected = {f + "4" for f in "abcefgh"} | {"d" + r for r in "1235678"}
    assert targets(board, "d4") == expected


def test_rook_from_the_corner_reaches_both_edges(setup, targets):
    board = setup({"h2": "WK", "h8": "BK", "a1": "WR"})
    expected = {"a" + r for r in "2345678"} | {f + "1" for f in "bcdefgh"}
    assert targets(board, "a1") == expected


def test_rook_blocked_by_friend_captures_enemy(setup, targets):
    board = setup({**KINGS, "d4": "WR", "d6": "WP", "f4": "BB"})
    moves = targets(board, "d4")
    assert "d5" in moves and "d6" not in moves and "d7" not in moves
    assert "f4" in moves and "g4" not in moves


# ---- queen ----------------------------------------------------------------------------------

def test_queen_combines_rook_and_bishop(setup, targets):
    board = setup({**KINGS, "d4": "WQ"})
    assert len(targets(board, "d4")) == 27


def test_queen_has_no_moves_at_the_start(board, targets):
    assert targets(board, "d1") == set()


def test_queen_attacks_only_on_open_lines(setup):
    board = setup({**KINGS, "d4": "WQ", "d6": "BP"})
    queen = board.piece_at(sq("d4"))
    assert queen.attacks(board, sq("d6"))
    assert not queen.attacks(board, sq("d7"))
    assert not queen.attacks(board, sq("e6"))  # a knight's jump away


# ---- king -----------------------------------------------------------------------------------

def test_king_moves_one_square_each_way(setup, targets):
    board = setup({"e4": "WK", "a8": "BK"})
    assert targets(board, "e4") == {"d3", "d4", "d5", "e3", "e5", "f3", "f4", "f5"}


def test_king_in_the_corner(setup, targets):
    board = setup({"a1": "WK", "h8": "BK"})
    assert targets(board, "a1") == {"a2", "b1", "b2"}


def test_king_blocked_by_own_pieces(setup, targets):
    board = setup({"e1": "WK", "d2": "WP", "e2": "WP", "f2": "WP", "a8": "BK"})
    assert targets(board, "e1") == {"d1", "f1"}


def test_kings_never_stand_next_to_each_other(setup, targets):
    board = setup({"e4": "WK", "e6": "BK"})
    assert targets(board, "e4").isdisjoint({"d5", "e5", "f5"})


# ---- pawn -----------------------------------------------------------------------------------

def test_white_pawn_one_or_two_steps_from_start(setup, targets):
    board = setup({**KINGS, "e2": "WP"})
    assert targets(board, "e2") == {"e3", "e4"}


def test_black_pawn_moves_down_the_board(setup, targets):
    board = setup({**KINGS, "e7": "BP"})
    assert targets(board, "e7") == {"e6", "e5"}


def test_pawn_off_its_start_row_steps_once(setup, targets):
    board = setup({**KINGS, "e3": "WP"})
    assert targets(board, "e3") == {"e4"}


@pytest.mark.parametrize(
    ("blocker", "expected"),
    [("e3", set()), ("e4", {"e3"})],
)
def test_pawn_push_is_blocked_by_any_piece(setup, targets, blocker, expected):
    board = setup({**KINGS, "e2": "WP", blocker: "BN"})
    assert targets(board, "e2") == expected


def test_pawn_captures_diagonally_but_not_forward(setup, targets):
    board = setup({**KINGS, "e4": "WP", "e5": "BP", "d5": "BN", "f5": "WN"})
    assert targets(board, "e4") == {"d5"}


def test_black_pawn_captures_diagonally_downwards(setup, targets):
    board = setup({**KINGS, "e5": "BP", "d4": "WP", "f6": "WP"})
    assert targets(board, "e5") == {"e4", "d4"}


def test_pawn_on_the_edge_captures_one_way(setup, targets):
    board = setup({**KINGS, "a4": "WP", "b5": "BP"})
    assert targets(board, "a4") == {"a5", "b5"}


def test_pawn_attacks_only_forward_diagonals(setup):
    board = setup({**KINGS, "e4": "WP"})
    pawn = board.piece_at(sq("e4"))
    assert pawn.attacks(board, sq("d5")) and pawn.attacks(board, sq("f5"))
    assert not pawn.attacks(board, sq("e5"))
    assert not pawn.attacks(board, sq("d3"))


def test_pawn_direction_and_rows():
    white = Pawn(Color.WHITE, sq("a2"))
    black = Pawn(Color.BLACK, sq("a7"))
    assert (white.direction, white.start_row, white.last_row) == (1, 1, 7)
    assert (black.direction, black.start_row, black.last_row) == (-1, 6, 0)


def test_starting_position_has_twenty_moves(board):
    from chess_engine import legal_moves

    assert len(legal_moves(board, Color.WHITE)) == 20
    assert len(legal_moves(board, Color.BLACK)) == 20


@pytest.mark.parametrize("cls", [Rook, Bishop, Queen, Knight, King])
def test_piece_does_not_attack_its_own_square(setup, cls):
    board = setup(KINGS)
    piece = cls(Color.WHITE, sq("d4"))
    board.add(piece)
    assert not piece.attacks(board, sq("d4"))
