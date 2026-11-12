from __future__ import annotations

from .constants import FILES, RANKS, Square, square_name


class TypedMove:
    """A move as the player typed it, split into its parts. It knows nothing about the position."""

    def __init__(self, text: str, promotion: str = "") -> None:
        self.text = text                  # tidied up, like 'Nbxd2', 'e4' or 'O-O'
        self.piece = text[0]              # K, Q, R, B or N, O for castling, or the file of a pawn
        self.promotion = promotion        # Q, R, B or N when typed, as in e8=Q
        self.target: Square | None = None
        self.is_push = len(text) == 2     # only a square, like e4: a pawn walking forward
        self.is_capture = "x" in text
        self.origin_file = ""             # set when the player said where the piece comes from,
        self.origin_rank = ""             # as in Nbd2, R1e2 or Qh4e1
        if self.piece == "O":
            return
        self.target = (RANKS.index(text[-1]), FILES.index(text[-2]))
        if len(text) > 3:
            if text[1] in FILES:
                self.origin_file = text[1]
                if text[2] in RANKS:
                    self.origin_rank = text[2]
            elif text[1] in RANKS:
                self.origin_rank = text[1]

    @property
    def is_castling(self) -> bool:
        return self.piece == "O"

    def fits_origin(self, square: Square) -> bool:
        """True when a piece on that square is one the player can mean."""
        name = square_name(square)
        return self.origin_file in ("", name[0]) and self.origin_rank in ("", name[1])

    def __repr__(self) -> str:
        return f"TypedMove({self.text!r}, promotion={self.promotion!r})"


def parse_move(text: str) -> TypedMove | None:
    """Turns typed text into a TypedMove, or None when it does not look like a move."""
    promotion = ""
    if len(text) > 2 and text[-1] in "QRBNqrbn" and text[-2] in "18=":
        promotion = text[-1].upper()
        text = text[:-1].rstrip("=")
    # Piece letters may be lowercase: nf3, qxh3, kf7, rad1, bc4.
    # A lowercase b is only a bishop when it cannot be the b pawn (b4 and bxc5 are pawn moves).
    if text[:1] in ("n", "r", "q", "k"):
        text = text[0].upper() + text[1:]
    elif text[:1] == "b" and len(text) >= 3 and text[1] != "x":
        text = "B" + text[1:]
    castling = text.upper().replace("0", "O")
    if castling in ("O-O", "O-O-O"):
        return TypedMove(castling)
    if len(text) < 2 or text[-2] not in FILES or text[-1] not in RANKS:
        return None
    return TypedMove(text, promotion)
