import pytest

from chess_engine import (
    Bishop,
    Color,
    GameStatus,
    IllegalMoveError,
    King,
    Knight,
    Pawn,
    Queen,
    Rook,
    check_count,
    has_legal_move,
    insufficient_material,
    is_checkmate,
    is_in_check,
    is_stalemate,
    legal_moves,
    parse_move,
    resolve_move,
    square_from_name as sq,
)

WHITE, BLACK = Color.WHITE, Color.BLACK


# ---- check ----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("attacker", "square"),
    [("BR", "e8"), ("BQ", "h4"), ("BB", "b4"), ("BN", "d3"), ("BP", "d2"), ("BP", "f2")],
)
def test_direct_check(setup, attacker, square):
    board = setup({"e1": "WK", "a8": "BK", square: attacker})
    assert is_in_check(board, WHITE)
    assert check_count(board, WHITE) == 1


@pytest.mark.parametrize(
    ("layout"),
    [
        {"e8": "BR", "e2": "WP"},  # blocked by a friendly piece
        {"e8": "BR", "e4": "BN"},  # blocked by an enemy piece
        {"e2": "BP"},              # a pawn does not attack straight ahead
        {"c3": "BN"},              # not a knight's jump away
        {"e8": "BB"},              # a bishop does not attack along a file
    ],
)
def test_no_check(setup, layout):
    board = setup({"e1": "WK", "a8": "BK", **layout})
    assert not is_in_check(board, WHITE)


def test_double_check_allows_only_king_moves(setup):
    board = setup({"e1": "WK", "a1": "WR", "a8": "BK", "e8": "BR", "d3": "BN"})
    assert check_count(board, WHITE) == 2
    moves = legal_moves(board, WHITE)
    assert moves and all(isinstance(m.piece, King) for m in moves)
    with pytest.raises(IllegalMoveError, match="double check"):
        resolve_move(board, WHITE, parse_move("Rxa8"))


def test_game_announces_check(play):
    game = play("e4 d5 Bb5")
    assert game.status is GameStatus.CHECK
    assert game.check_count == 1
    assert not game.is_over


def test_a_check_must_be_answered(play):
    game = play("e4 d5 Bb5")
    with pytest.raises(IllegalMoveError, match="does not save it"):
        game.make_move("a6")
    game.make_move("c6")  # blocking is fine
    assert game.status is GameStatus.ONGOING


# ---- pins and walking into check ------------------------------------------------------------

def test_pinned_knight_cannot_move(setup, targets):
    board = setup({"e1": "WK", "e2": "WN", "e8": "BR", "a8": "BK"})
    assert targets(board, "e2") == set()
    with pytest.raises(IllegalMoveError, match="pinned"):
        resolve_move(board, WHITE, parse_move("Nc3"))


def test_pinned_piece_may_move_along_the_pin(setup, targets):
    board = setup({"e1": "WK", "e2": "WR", "e8": "BR", "a8": "BK"})
    assert targets(board, "e2") == {"e3", "e4", "e5", "e6", "e7", "e8"}


def test_diagonally_pinned_bishop(setup, targets):
    board = setup({"e1": "WK", "d2": "WB", "a5": "BB", "h8": "BK"})
    assert targets(board, "d2") == {"c3", "b4", "a5"}


def test_king_cannot_step_into_check(setup, targets):
    board = setup({"e1": "WK", "d8": "BR", "a8": "BK"})
    assert targets(board, "e1") == {"e2", "f1", "f2"}
    with pytest.raises(IllegalMoveError, match="attacked square"):
        resolve_move(board, WHITE, parse_move("Kd2"))


def test_king_cannot_capture_a_defended_piece(setup, targets):
    board = setup({"e1": "WK", "e2": "BR", "a8": "BK"})
    assert "e2" in targets(board, "e1")
    board = setup({"e1": "WK", "e2": "BR", "e6": "BR", "a8": "BK"})
    assert "e2" not in targets(board, "e1")


def test_king_cannot_hide_behind_itself(setup, targets):
    # stepping back along the rook's line is still in the line of fire
    board = setup({"e2": "WK", "e8": "BR", "a8": "BK"})
    assert "e1" not in targets(board, "e2")


# ---- checkmate ------------------------------------------------------------------------------

def test_fools_mate(play):
    game = play("f3 e5 g4 Qh4")
    assert game.status is GameStatus.CHECKMATE
    assert game.winner is BLACK
    assert is_checkmate(game.board, WHITE)
    assert game.legal_moves() == []


def test_scholars_mate(play):
    game = play("e4 e5 Bc4 Nc6 Qh5 Nf6 Qxf7")
    assert game.status is GameStatus.CHECKMATE
    assert game.winner is WHITE
    assert is_checkmate(game.board, BLACK)


def test_no_moves_after_checkmate(play):
    game = play("f3 e5 g4 Qh4")
    with pytest.raises(IllegalMoveError, match="over"):
        game.make_move("e4")


def test_back_rank_mate(setup):
    board = setup({"g1": "WK", "f2": "WP", "g2": "WP", "h2": "WP", "e1": "BR", "a8": "BK"})
    assert is_checkmate(board, WHITE)


def test_mate_by_a_defended_queen(setup):
    board = setup({"e1": "WK", "e2": "BQ", "e3": "BK"})
    assert is_checkmate(board, WHITE)


def test_check_that_can_be_blocked_is_not_mate(setup):
    board = setup({"g1": "WK", "f2": "WP", "g2": "WP", "h2": "WP", "e1": "BR", "a8": "BK", "d3": "WB"})
    assert is_in_check(board, WHITE)
    assert not is_checkmate(board, WHITE)  # Bf1 blocks


def test_check_that_can_be_captured_is_not_mate(setup):
    board = setup({"g1": "WK", "f2": "WP", "g2": "WP", "h2": "WP", "e1": "BR", "a8": "BK", "a1": "WR"})
    assert not is_checkmate(board, WHITE)  # Rxe1


# ---- stalemate and draws --------------------------------------------------------------------

def test_stalemate(setup):
    board = setup({"a8": "BK", "c7": "WQ", "c6": "WK"})
    assert not is_in_check(board, BLACK)
    assert not has_legal_move(board, BLACK)
    assert is_stalemate(board, BLACK)
    assert not is_checkmate(board, BLACK)


def test_game_reports_stalemate(custom_game):
    game = custom_game({"a8": "BK", "c7": "WQ", "b5": "WK"})
    game.make_move("Kc6")
    assert game.status is GameStatus.STALEMATE
    assert game.status.is_draw and game.winner is None


def test_stalemate_with_a_blocked_pawn(setup):
    board = setup({"h8": "BK", "h7": "BP", "h6": "WP", "f7": "WQ", "a1": "WK"})
    # the h7 pawn cannot move and every king square is covered, but black is not in check
    assert is_stalemate(board, BLACK)


@pytest.mark.parametrize(
    ("extra", "draw"),
    [
        ({}, True),
        ({"c3": "WN"}, True),
        ({"c3": "WB"}, True),
        ({"c1": "WB", "f8": "BB"}, True),    # both bishops on dark squares
        ({"c1": "WB", "c8": "BB"}, False),   # bishops on different colors
        ({"c3": "WN", "c6": "BN"}, False),
        ({"a2": "WP"}, False),
        ({"a2": "WR"}, False),
        ({"a2": "BQ"}, False),
    ],
)
def test_insufficient_material(setup, extra, draw):
    board = setup({"e1": "WK", "e8": "BK", **extra})
    assert insufficient_material(board) is draw


def test_threefold_repetition(play):
    game = play("Nf3 Nf6 Ng1 Ng8 Nf3 Nf6 Ng1")
    assert game.status is GameStatus.ONGOING
    game.make_move("Ng8")
    assert game.status is GameStatus.DRAW_BY_REPETITION


def test_fifty_move_rule(custom_game):
    game = custom_game({"e1": "WK", "a1": "WR", "e8": "BK"})
    game.moves_without_progress = 98
    game.make_move("Ra2")
    assert game.status is GameStatus.ONGOING
    game.make_move("Kd8")
    assert game.status is GameStatus.DRAW_BY_FIFTY_MOVES


def test_pawn_move_resets_the_fifty_move_count(play):
    game = play("Nf3 Nf6 e4")
    assert game.moves_without_progress == 0


def test_resign_and_agreed_draw(game):
    game.resign()
    assert game.status is GameStatus.RESIGNED and game.winner is BLACK
    other = type(game)()
    other.agree_draw()
    assert other.status is GameStatus.DRAW_BY_AGREEMENT and other.is_over


# ---- promotion ------------------------------------------------------------------------------

@pytest.mark.parametrize(("letter", "cls"), [("Q", Queen), ("R", Rook), ("B", Bishop), ("N", Knight)])
def test_promotion(custom_game, letter, cls):
    game = custom_game({"a7": "WP", "e1": "WK", "h5": "BK"})
    game.make_move("a8=" + letter)
    promoted = game.board.piece_at(sq("a8"))
    assert type(promoted) is cls and promoted.color is WHITE
    assert not any(isinstance(p, Pawn) for p in game.board.pieces_of(WHITE))


def test_promotion_by_capture(custom_game):
    game = custom_game({"a7": "WP", "b8": "BR", "e1": "WK", "h5": "BK"})
    game.make_move("axb8=N")
    assert type(game.board.piece_at(sq("b8"))) is Knight
    assert [p.symbol for p in game.captured] == ["BR"]


def test_black_promotion(custom_game):
    game = custom_game({"h2": "BP", "a8": "BK", "e4": "WK"}, turn=BLACK)
    game.make_move("h1=Q")
    assert game.board.piece_at(sq("h1")).symbol == "BQ"


def test_promotion_piece_can_be_passed_separately(custom_game):
    game = custom_game({"a7": "WP", "e1": "WK", "h5": "BK"})
    game.make_move("a8", promotion="q")
    assert type(game.board.piece_at(sq("a8"))) is Queen


def test_promotion_needs_a_piece(custom_game):
    game = custom_game({"a7": "WP", "e1": "WK", "h5": "BK"})
    with pytest.raises(ValueError):
        game.make_move("a8")
    with pytest.raises(ValueError):
        game.make_move("a8", promotion="K")
    assert game.board.piece_at(sq("a7")).symbol == "WP"  # nothing was played


def test_custom_game_knows_its_starting_status(custom_game):
    assert custom_game({"e1": "WK", "e8": "BR", "a8": "BK"}).status is GameStatus.CHECK
    assert custom_game({"e1": "WK", "e8": "BK"}).status is GameStatus.DRAW_BY_MATERIAL


def test_promoted_queen_gives_check_and_keeps_playing(custom_game):
    game = custom_game({"a7": "WP", "e1": "WK", "e8": "BK"})
    game.make_move("a8=Q")
    assert game.status is GameStatus.CHECK
    game.make_move("Ke7")
    game.make_move("Qa1")
    assert game.board.piece_at(sq("a1")).symbol == "WQ"


# ---- castling -------------------------------------------------------------------------------

CASTLING = {"e1": "WK", "a1": "WR", "h1": "WR", "e8": "BK", "a8": "BR", "h8": "BR"}


def test_castling_king_side(custom_game):
    game = custom_game(CASTLING)
    game.make_move("O-O")
    assert game.board.piece_at(sq("g1")).symbol == "WK"
    assert game.board.piece_at(sq("f1")).symbol == "WR"
    assert game.board.piece_at(sq("e1")) is None and game.board.piece_at(sq("h1")) is None


def test_castling_queen_side_for_black(custom_game):
    game = custom_game(CASTLING, turn=BLACK)
    game.make_move("O-O-O")
    assert game.board.piece_at(sq("c8")).symbol == "BK"
    assert game.board.piece_at(sq("d8")).symbol == "BR"


def test_castling_in_a_real_game(play):
    game = play("e4 e5 Nf3 Nc6 Bc4 Bc5 O-O")
    assert game.board.piece_at(sq("g1")).symbol == "WK"


def test_castling_is_listed_as_a_legal_move(custom_game):
    game = custom_game(CASTLING)
    assert sum(m.rook is not None for m in game.legal_moves()) == 2


def test_no_castling_through_pieces(game):
    with pytest.raises(IllegalMoveError, match="piece between"):
        game.make_move("O-O")


def test_no_castling_after_the_king_moved(custom_game):
    game = custom_game(CASTLING)
    for move in ["Kf1", "Kf8", "Ke1", "Ke8"]:
        game.make_move(move)
    with pytest.raises(IllegalMoveError, match="already moved"):
        game.make_move("O-O")


def test_no_castling_with_a_moved_rook(custom_game):
    game = custom_game(CASTLING)
    for move in ["Rh2", "Rh7", "Rh1", "Rh8"]:
        game.make_move(move)
    with pytest.raises(IllegalMoveError, match="already moved"):
        game.make_move("O-O")
    game.make_move("O-O-O")  # the other rook never moved


def test_no_castling_without_the_rook(custom_game):
    game = custom_game({"e1": "WK", "e8": "BK", "a8": "BR"})
    with pytest.raises(IllegalMoveError, match="already moved"):
        game.make_move("O-O")


def test_no_castling_out_of_check(custom_game):
    game = custom_game({"e1": "WK", "h1": "WR", "e8": "BR", "a8": "BK"})
    with pytest.raises(IllegalMoveError, match="in check"):
        game.make_move("O-O")


@pytest.mark.parametrize("attacked", ["f8", "g8"])
def test_no_castling_through_or_into_check(custom_game, attacked):
    game = custom_game({"e1": "WK", "a1": "WR", "h1": "WR", "a8": "BK", attacked: "BR"})
    with pytest.raises(IllegalMoveError, match="attacked square"):
        game.make_move("O-O")
    game.make_move("O-O-O")


def test_queen_side_castling_allowed_when_only_b1_is_attacked(custom_game):
    game = custom_game({"e1": "WK", "a1": "WR", "h8": "BK", "b8": "BR"})
    game.make_move("O-O-O")
    assert game.board.piece_at(sq("c1")).symbol == "WK"


def test_no_castling_when_the_king_is_off_its_square(custom_game):
    game = custom_game({"f1": "WK", "h1": "WR", "e8": "BK"})
    with pytest.raises(IllegalMoveError):
        game.make_move("O-O")


# ---- en passant -----------------------------------------------------------------------------

def test_en_passant_for_white(play):
    game = play("e4 a6 e5 d5 exd6")
    assert game.board.piece_at(sq("d6")).symbol == "WP"
    assert game.board.piece_at(sq("d5")) is None
    assert [p.symbol for p in game.captured] == ["BP"]


def test_en_passant_for_black(play):
    game = play("a3 e5 a4 e4 d4 exd3")
    assert game.board.piece_at(sq("d3")).symbol == "BP"
    assert game.board.piece_at(sq("d4")) is None


def test_en_passant_only_right_away(play):
    game = play("e4 a6 e5 d5 h3 h6")
    with pytest.raises(IllegalMoveError):
        game.make_move("exd6")


def test_en_passant_only_after_a_double_step(play):
    game = play("e4 d6 e5 d5")
    with pytest.raises(IllegalMoveError):
        game.make_move("exd6")


def test_en_passant_is_in_the_legal_moves(play):
    game = play("e4 a6 e5 d5")
    captures = [m for m in game.legal_moves() if isinstance(m.piece, Pawn) and m.captured is not None]
    assert [m.captured.square for m in captures] == [sq("d5")]


def test_en_passant_that_exposes_the_king_is_illegal(custom_game):
    game = custom_game({"a5": "WK", "b5": "WP", "c7": "BP", "h5": "BR", "e8": "BK"}, turn=BLACK)
    game.make_move("c5")
    with pytest.raises(IllegalMoveError, match="pinned"):
        game.make_move("bxc6")


# ---- reading moves --------------------------------------------------------------------------

def test_ambiguous_move_asks_for_the_origin(play):
    game = play("d4 d5 Nf3 Nf6")
    with pytest.raises(IllegalMoveError, match="Nbd2 or Nfd2"):
        game.make_move("Nd2")
    game.make_move("Nbd2")
    assert game.board.piece_at(sq("d2")).symbol == "WN"


def test_invalid_notation(game):
    with pytest.raises(IllegalMoveError, match="Invalid"):
        game.make_move("hello")


def test_history_and_turn(play):
    game = play("e4 e5 Nf3")
    assert game.turn is BLACK
    assert [p.color for p in game.history] == [WHITE, BLACK, WHITE]
