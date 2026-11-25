from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATS_FILE = ROOT / "stats.json"

ENGINE_CONFIG = {
    "STOCKFISH_PATH": "stockfish",
    "SYZYGY_PATH": None,
    "MAIA3_CMD": [
        "maia3-uci",
        "--model",
        "maia3-79m",
        "--local-files-only",
    ],
}
