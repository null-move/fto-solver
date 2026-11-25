import chess


RAW_ENDGAME_FENS = {
    "Rook Endgames (Lucena / Philidor / Vancura)": [
        "8/1P1k4/1K6/8/8/8/r7/2R5 w - - 0 1",
        "8/8/8/3k4/8/8/3PK3/5rR1 w - - 0 1",
        "8/8/1k6/8/P7/8/1K1R4/1r6 w - - 0 1",
        "8/1K6/1P6/3k4/8/8/8/2R1r3 w - - 0 1",
        "8/8/8/4k3/1P6/1K6/8/r6R w - - 0 1",
    ],
    "Rook + Pawn Endgames (4v3 Same Side & Cutoffs)": [
        "8/ppp5/1k6/8/1K1R4/PPPP4/8/6r1 w - - 0 1",
        "r7/ppp5/5k2/8/2K4R/PPPP4/8/8 w - - 0 1",
        "4r3/4ppp1/5k2/8/R7/2K5/PPPP4/8 w - - 0 1",
        "8/ppp5/2k5/8/2K1R3/PPPP4/8/4r3 w - - 0 1",
    ],
    "Pawn Endgames (Opposition, Outflanking, Triangulation, Réti)": [
        "8/8/3k4/8/3P4/8/3K4/8 w - - 0 1",
        "8/8/8/2k5/8/4P3/4K3/8 w - - 0 1",
        "8/8/2k5/8/3P4/4K3/8/8 w - - 0 1",
        "8/8/8/8/1k6/1P6/K7/8 w - - 0 1",
        "8/8/8/3k4/8/4P3/4K3/8 w - - 0 1",
    ],
    "Opposite-Colored Bishops (Fortresses & Breakthroughs)": [
        "8/2p5/2k5/8/2K5/2P5/2B5/6b1 w - - 0 1",
        "8/5p2/3k4/8/3K4/5P2/2B5/6b1 w - - 0 1",
        "8/5p2/4k3/8/4K3/5P2/2B5/6b1 w - - 0 1",
        "8/8/2k5/3p4/3K4/8/2B5/6b1 w - - 0 1",
    ],
    "Minor Piece Technique (B+N Checkmate & B vs N Good/Bad)": [
        "k7/8/2K5/8/2N1B3/8/8/8 w - - 0 1",
        "7k/8/5K2/6B1/5N2/8/8/8 w - - 0 1",
        "8/5k2/7n/8/4KB2/8/8/8 w - - 0 1",
        "8/8/8/5k2/5n2/6K1/8/2B5 w - - 0 1",
    ],
    "Queen & Heavy Piece Endgames (Q vs R & Perpetual Traps)": [
        "8/8/4k3/8/8/8/3r4/4K1Q1 w - - 0 1",
        "4k3/8/8/8/8/8/4r3/3QK3 w - - 0 1",
        "6k1/5ppp/8/8/8/8/5PPP/3rQ1K1 w - - 0 1",
    ],
}


def build_endgame_bank(fen_bank=RAW_ENDGAME_FENS):
    bank = {}
    for category, fens in fen_bank.items():
        positions, seen = [], set()
        for fen in fens:
            board = chess.Board(fen)
            if not board.is_valid():
                raise ValueError(f"Invalid endgame FEN in {category}: {fen}")
            position = board.fen()
            if position not in seen:
                positions.append(position)
                seen.add(position)
            if not board.castling_rights:
                mirrored = board.mirror()
                if not mirrored.is_valid():
                    raise ValueError(f"Invalid mirrored FEN in {category}: {fen}")
                mirror_fen = mirrored.fen()
                if mirror_fen not in seen:
                    positions.append(mirror_fen)
                    seen.add(mirror_fen)
        bank[category] = positions
    return bank


ENDGAME_FENS = build_endgame_bank()
CATEGORIES = tuple(ENDGAME_FENS)
