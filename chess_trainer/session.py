import math
import random
import time

import chess

from .engines import LocalEngines
from .positions import CATEGORIES, ENDGAME_FENS
from .rating import choose_category, fluency_penalty, update_rating, win_percent
from .stats import load_stats, save_stats


class DrillSession:
    def __init__(self, engines=None, stats_path=None):
        self.engines = engines or LocalEngines()
        self.stats_path = stats_path
        self.stats = load_stats(CATEGORIES, stats_path) if stats_path else load_stats(CATEGORIES)
        self.board = chess.Board()
        self.category = CATEGORIES[0]
        self.user_color = chess.WHITE
        self.active = False
        self.rows = []
        self.result = None
        self.last_move_time = time.monotonic()

    def start_drill(self):
        self.category = choose_category(self.stats, CATEGORIES)
        self.board = chess.Board(random.choice(ENDGAME_FENS[self.category]))
        self.user_color = self.board.turn
        self.active = True
        self.rows = []
        self.result = None
        self.last_move_time = time.monotonic()

    def _finish(self, result):
        updated = {key: value.copy() for key, value in self.stats.items()}
        updated[self.category] = update_rating(updated[self.category], result)
        if self.stats_path:
            save_stats(updated, self.stats_path)
        else:
            save_stats(updated)
        self.stats = updated
        self.active = False
        self.result = result

    def resign(self):
        if self.active:
            self._finish(0.0)

    def play_move(self, text):
        if not self.active or self.board.turn != self.user_color:
            raise RuntimeError("Start a drill before entering a move.")
        text = text.strip()
        try:
            move = self.board.parse_uci(text)
        except (ValueError, chess.InvalidMoveError):
            try:
                move = self.board.parse_san(text)
            except (ValueError, chess.InvalidMoveError, chess.AmbiguousMoveError):
                raise ValueError("Enter a legal SAN or UCI move.") from None
        if move not in self.board.legal_moves:
            raise ValueError("Enter a legal SAN or UCI move.")

        category_stats = self.stats[self.category]
        before = self.engines.analyse(self.board, self.user_color)
        if not before:
            raise RuntimeError("Stockfish returned no analysis for this position.")
        policy = self.engines.policy(self.board, category_stats["mu"])
        optimal_move = before[0][0]
        if optimal_move not in policy:
            raise RuntimeError("Maia-3 policy did not include the optimal move.")

        elapsed = max(0.05, time.monotonic() - self.last_move_time)
        surprisal = -math.log2(policy[optimal_move])
        entropy = -sum(probability * math.log2(probability) for probability in policy.values())
        ranked = [candidate for candidate, _ in before]
        accuracy = max(100.0 - 30.0 * ranked.index(move), 40.0) if move in ranked else 50.0
        san = self.board.san(move)
        snapshot, row_count = self.board.copy(stack=True), len(self.rows)

        try:
            self.board.push(move)
            outcome = self.board.outcome(claim_draw=True)
            if outcome is None:
                after = self.engines.analyse(self.board, self.user_color)
                if not after:
                    raise RuntimeError("Stockfish returned no analysis after the move.")
                after_cp = after[0][1]
            elif outcome.winner is None:
                after_cp = 0
            else:
                after_cp = 10000 if outcome.winner == self.user_color else -10000

            win_loss = max(0.0, win_percent(before[0][1]) - win_percent(after_cp))
            accuracy = max(0.0, min(100.0, (accuracy + 100.0 * (1.0 - win_loss)) / 2.0))
            self.rows.append({
                "move": san,
                "accuracy": accuracy,
                "surprisal": surprisal,
                "entropy": entropy,
                "fluency": fluency_penalty(elapsed),
            })

            if outcome is not None:
                self._finish(
                    0.5 if outcome.winner is None else float(outcome.winner == self.user_color)
                )
            else:
                opponent = self.engines.opponent_move(
                    self.board, category_stats["mu"], category_stats["phi"]
                )
                if opponent is None or opponent not in self.board.legal_moves:
                    raise RuntimeError("The engine returned no legal reply.")
                self.board.push(opponent)
                outcome = self.board.outcome(claim_draw=True)
                if outcome is not None:
                    self._finish(
                        0.5 if outcome.winner is None else float(outcome.winner == self.user_color)
                    )
            self.last_move_time = time.monotonic()
        except Exception:
            self.board = snapshot
            del self.rows[row_count:]
            raise
