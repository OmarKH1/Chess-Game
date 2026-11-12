"""Console interface: all printing and reading of input happens here."""

from __future__ import annotations

from .board import Board
from .constants import PROMOTION_TYPES, RANKS, Color
from .game import Game, GameStatus
from .notation import parse_move
from .validator import IllegalMoveError

BORDER = "    +----+----+----+----+----+----+----+----+"
FILE_LABELS = "      a    b    c    d    e    f    g    h"
PROMOTION_LETTERS = {kind.value for kind in PROMOTION_TYPES}
INVALID_INPUT = "Invalid input! Type a move like e4, Nf3, Qxh3, exd5, e8=Q or O-O, or type resign, draw or quit."

DRAW_MESSAGES = {
    GameStatus.STALEMATE: "Stalemate! The game is a draw.",
    GameStatus.DRAW_BY_MATERIAL: "Draw! Neither side has enough pieces left to give checkmate.",
    GameStatus.DRAW_BY_REPETITION: "Draw! The same position has appeared three times.",
    GameStatus.DRAW_BY_FIFTY_MOVES: "Draw! Fifty moves each have been played without a pawn move or a capture.",
}


def color_name(color: Color) -> str:
    return color.value.capitalize()


def render_board(board: Board) -> list[str]:
    """The board as printed lines, white at the bottom."""
    lines = ["", FILE_LABELS, BORDER]
    for row in range(7, -1, -1):
        line = "  " + RANKS[row] + " |"
        for col in range(8):
            piece = board.piece_at((row, col))
            line += f" {piece.symbol} |" if piece is not None else "    |"
        lines.append(line + " " + RANKS[row])
        lines.append(BORDER)
    lines += [FILE_LABELS, ""]
    return lines


def show_board(board: Board) -> None:
    for line in render_board(board):
        print(line)


def status_message(game: Game) -> str | None:
    """What to announce after a move, or None."""
    if game.status is GameStatus.CHECKMATE and game.winner is not None:
        return f"Checkmate! {color_name(game.winner)} wins."
    if game.status in DRAW_MESSAGES:
        return DRAW_MESSAGES[game.status]
    if game.check_count >= 2:
        return "Double check!"
    if game.check_count == 1:
        return "Check!"
    return None


def ask_promotion(promotion: str) -> str:
    while promotion not in PROMOTION_LETTERS:
        promotion = input("Promote the pawn to (Q, R, B or N): ").strip().upper()
    return promotion


def run() -> None:
    game = Game()
    show_board(game.board)
    print("Type a move, or one of these commands: resign, draw, quit")
    while not game.is_over:
        mover = color_name(game.turn)
        waiting = color_name(game.turn.opponent)
        text = input(f"{mover}'s move: ").strip().rstrip("+#")

        command = text.lower()
        if command in ("quit", "exit"):
            print("Game ended without a result.")
            break
        if command == "resign":
            game.resign()
            print(f"{mover} resigns. {waiting} wins.")
            break
        if command == "draw":
            answer = input(f"{mover} offers a draw. {waiting}, do you accept? (yes/no): ")
            if answer.strip().lower() in ("yes", "y"):
                game.agree_draw()
                print("Draw by agreement.")
                break
            print("The draw offer was declined.")
            continue

        typed = parse_move(text)
        if typed is None:
            print(INVALID_INPUT)
            continue
        try:
            move = game.find_move(typed)
        except IllegalMoveError as error:
            print(error)
            continue

        promotion = ask_promotion(typed.promotion) if game.needs_promotion(move) else None
        game.play(move, promotion)

        show_board(game.board)
        message = status_message(game)
        if message is not None:
            print(message)


def main() -> None:
    run()
