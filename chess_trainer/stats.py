import json
import time

from .config import STATS_FILE


DEFAULT_STAT = {"mu": 1500.0, "phi": 350.0, "sigma": 0.06}


def load_stats(categories, path=STATS_FILE):
    if not path.exists():
        return {category: DEFAULT_STAT.copy() for category in categories}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    source = data.get("categories", data)
    if not isinstance(source, dict):
        raise ValueError(f"Invalid stats data in {path}")

    result = {}
    for category in categories:
        item = source.get(category, DEFAULT_STAT)
        if not isinstance(item, dict):
            raise ValueError(f"Invalid stats for category {category!r}")
        result[category] = {
            key: float(item.get(key, default))
            for key, default in DEFAULT_STAT.items()
        }
    return result


def save_stats(stats, path=STATS_FILE):
    payload = {"categories": stats, "updated_at": time.time()}
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
