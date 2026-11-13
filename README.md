# chess-engine

A two-player chess game for the terminal, built as a small Python package with no runtime
dependencies. The rules engine is separate from the interface, so it can be used and tested
without any input or output.

Requires Python 3.10 or newer.

## Rules covered

- Legal move generation for all pieces, including pins and moves that would leave the king in check
- Check, double check (only the king may move), checkmate and stalemate
- Castling on both sides, with all conditions: king and rook unmoved, empty squares between them,
  king not in check and not passing through or landing on an attacked square
- En passant, only on the move right after the double step
- Pawn promotion to queen, rook, bishop or knight
- Draws by insufficient material, threefold repetition and the fifty-move rule
  (both applied automatically, not by claim), plus resignation and draw by agreement

## Architecture

```
src/chess_engine/
    constants.py   Color and PieceType enums, board size, square conversion ('e4' <-> (3, 4))
    pieces.py      Piece and its subclasses; each piece defines which squares it attacks
    board.py       Board (piece placement, lookup, apply/undo, copy) and Move
    notation.py    Parses typed moves such as Nbd2, exd5, e8=Q and O-O into a TypedMove
    validator.py   The rules as pure functions on a Board: legality, check, castling,
                   en passant, promotion, checkmate, stalemate, insufficient material
    game.py        Game: turn, history, captured pieces, en passant state, repetition and
                   fifty-move counters, and GameStatus
    cli.py         Terminal interface: board rendering, prompts and messages
main.py            Entry point
tests/             pytest suite
```

Dependencies only point downwards in this list: `cli` uses `game`, `game` uses `validator`,
`validator` uses `board` and `pieces`. Only `cli.py` calls `print()` or `input()`.

Squares are `(row, col)` tuples where row 0 is rank 1 and col 0 is the a-file.

### Design notes

- **Legality by trial.** `validator.keeps_king_safe()` applies a move to the board, checks whether
  the mover's king is attacked, and undoes it. That single test handles pins, moving into check
  and answering a check, so there is no separate pin detection.
- **Pieces only know how they attack.** Each piece class implements `attacks(board, target)`.
  Pawn pushes, en passant and castling, which do not follow attack patterns, live in `validator.py`.
- **Errors carry the message.** An illegal move raises `IllegalMoveError`; its text is the message
  shown to the player, so the interface does not need to know why a move failed.

### Using the engine directly

```python
from chess_engine import Game, GameStatus, IllegalMoveError

game = Game()
for move in ["f3", "e5", "g4", "Qh4"]:
    game.make_move(move)

assert game.status is GameStatus.CHECKMATE
assert game.winner.value == "black"

try:
    game.make_move("e4")
except IllegalMoveError as error:
    print(error)
```

A game can also start from a custom position:

```python
from chess_engine import Board, Color, Game, King, Pawn, square_from_name

board = Board.empty()
board.add(King(Color.WHITE, square_from_name("e1")))
board.add(King(Color.BLACK, square_from_name("h5")))
board.add(Pawn(Color.WHITE, square_from_name("a7")))

game = Game(board, turn=Color.WHITE)
game.make_move("a8=Q")
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

For development, install the test dependencies as well:

```bash
pip install -e ".[dev]"
```

## Running the game

```bash
python main.py
```

Moves are typed in algebraic notation:

| Input         | Meaning                                        |
|---------------|------------------------------------------------|
| `e4`          | Pawn move                                      |
| `exd5`        | Pawn capture (also en passant)                 |
| `Nf3`, `Qxh3` | Piece move or capture                          |
| `Nbd2`, `R1e2`| Piece move with the starting file or rank      |
| `e8=Q`        | Promotion (`e8Q` also works; `e8` asks)        |
| `O-O`, `O-O-O`| Castling (`0-0` also works)                    |
| `resign`, `draw`, `quit` | Commands                            |

Piece letters may be lowercase. A trailing `+` or `#` is ignored. If two pieces can reach the
target square, the game asks for a move that says which one.

## Tests

```bash
pytest -v
```

The suite covers piece movement, board operations, and the rules: check and double check, pins,
checkmates (including Fool's Mate and Scholar's Mate), stalemate, the draw rules, castling,
en passant and promotion. Fixtures in `tests/conftest.py` build custom positions:

```python
def test_pinned_knight_cannot_move(setup, targets):
    board = setup({"e1": "WK", "e2": "WN", "e8": "BR", "a8": "BK"})
    assert targets(board, "e2") == set()
```

GitHub Actions runs the suite on Python 3.11 and 3.12 for every push and pull request to `main`.

## Roadmap

- **FEN import and export.** Load and save positions as FEN strings. `Game(board, turn)` already
  accepts a custom position; FEN adds castling rights, the en passant square and move counters.
- **PGN serialization.** Write the move history in standard algebraic notation with check and
  mate markers, and replay PGN files. This needs a move-to-SAN formatter alongside the existing parser.
- **Zobrist hashing.** Replace the string built by `Game.position_key()` with an incrementally
  updated 64-bit Zobrist hash. Threefold repetition detection already works with the string key;
  the hash makes it cheaper and is the basis for a transposition table.
- **AI opponent.** Minimax with alpha-beta pruning, move ordering (captures and checks first)
  and a material plus piece-square evaluation, using the Zobrist transposition table.
- **Move generation performance.** `legal_moves()` tries every piece against all 64 squares and
  checks each move by applying it. Generating moves per piece along its directions, and perft
  tests against known node counts, are the prerequisites for a usable search depth.
- **Undo and takeback.** `Board.undo()` exists; the game state (counters, en passant, status)
  needs to be restorable per move as well.
- **FIDE draw handling.** Make threefold repetition and the fifty-move rule claimable, with
  automatic draws at fivefold repetition and 75 moves.
