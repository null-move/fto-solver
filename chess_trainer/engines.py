import atexit
import math
import os
import shutil
import sysconfig

import chess
import chess.engine

from .config import ENGINE_CONFIG
from .rating import clamp


class LocalEngines:
    def __init__(self, config=ENGINE_CONFIG):
        self.config = config
        self.stockfish = None
        self.maia = None
        atexit.register(self.close)

    @staticmethod
    def _shutdown(engine):
        if engine is not None:
            try:
                engine.quit()
            finally:
                engine.close()

    def close(self):
        stockfish, maia = self.stockfish, self.maia
        self.stockfish = self.maia = None
        try:
            self._shutdown(maia)
        finally:
            self._shutdown(stockfish)

    def _stockfish(self):
        if self.stockfish is None:
            engine = chess.engine.SimpleEngine.popen_uci(
                self.config["STOCKFISH_PATH"]
            )
            try:
                path = self.config["SYZYGY_PATH"]
                if path and os.path.isdir(path):
                    engine.configure({"SyzygyPath": path})
            except Exception:
                self._shutdown(engine)
                raise
            self.stockfish = engine
        return self.stockfish

    def _maia(self):
        if self.maia is None:
            command = self.config["MAIA3_CMD"]
            if command[0] == "maia3-uci" and shutil.which(command[0]) is None:
                scripts = sysconfig.get_path("scripts")
                if scripts:
                    executable = os.path.join(
                        scripts,
                        "maia3-uci.exe" if os.name == "nt" else "maia3-uci",
                    )
                    if os.path.isfile(executable):
                        command = [executable, *command[1:]]
            self.maia = chess.engine.SimpleEngine.popen_uci(command)
        return self.maia

    def analyse(self, board, user_color, depth=15):
        results = self._stockfish().analyse(
            board, chess.engine.Limit(depth=depth), multipv=3
        )
        if isinstance(results, dict):
            results = [results]
        return [
            (info["pv"][0], info["score"].pov(user_color).score(mate_score=10000))
            for info in results
        ]

    def policy(self, board, rating):
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return {}

        elo = round(clamp(rating, 600, 2600))
        results = self._maia().analyse(
            board,
            chess.engine.Limit(nodes=1),
            multipv=min(15, len(legal_moves)),
            options={"SelfElo": elo, "OppoElo": elo},
        )
        if isinstance(results, dict):
            results = [results]

        weights = {}
        for info in results:
            move = info["pv"][0]
            if move in board.legal_moves:
                score = info["score"].pov(board.turn).score(mate_score=10000)
                weights[move] = math.exp(clamp(score / 1000.0, -50.0, 50.0))
        if not weights:
            raise RuntimeError("Maia-3 returned no legal MultiPV candidates.")

        floor = 1e-6
        remaining = 1.0 - floor * len(legal_moves)
        total = sum(weights.values())
        return {
            move: floor + remaining * weights.get(move, 0.0) / total
            for move in legal_moves
        }

    def opponent_move(self, board, rating, deviation):
        if rating - 1.96 * deviation < 2450:
            result = self._maia().play(
                board,
                chess.engine.Limit(nodes=1),
                options={
                    "SelfElo": round(rating + 50),
                    "OppoElo": round(rating),
                },
            )
        else:
            result = self._stockfish().play(
                board, chess.engine.Limit(depth=18)
            )
        return result.move
