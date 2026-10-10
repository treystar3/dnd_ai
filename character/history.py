"""Memory of past playthroughs, kept outside any one save, so new characters don't keep getting the same options.

saves/_history.json: {"runs": [{"class", "families", "offered", "chosen", "stats"}, ...]} - the most recent last.
"""

import json
from pathlib import Path

PATH = Path("saves/_history.json")
KEEP = 6           # remember this many past characters
CHOSEN_RECENT = 3  # mechanics picked in the last few characters are strongly avoided
CHOSEN_FACTOR = 0.15
OFFERED_FACTOR = 0.5   # mechanics merely offered last time are mildly avoided


def load() -> list[dict]:
    try:
        return json.loads(PATH.read_text(encoding="utf-8")).get("runs", [])
    except (OSError, ValueError):
        return []


def record(custom_class: str, families: list[str], offered: list[str], chosen: list[str], stats: list[str]) -> None:
    runs = (load() + [{"class": custom_class, "families": families, "offered": offered, "chosen": chosen,
                       "stats": stats}])[-KEEP:]
    try:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        PATH.write_text(json.dumps({"runs": runs}, indent=1), encoding="utf-8")
    except OSError:
        pass


def factor(mechanic: str, runs: list[dict]) -> float:
    """How much less likely a mechanic should be, given what past characters had."""
    f = 1.0
    if any(mechanic in r["chosen"] for r in runs[-CHOSEN_RECENT:]):
        f *= CHOSEN_FACTOR
    if runs and mechanic in runs[-1]["offered"]:
        f *= OFFERED_FACTOR
    return f


def recent_stats(runs: list[dict], n: int = 2) -> list[str]:
    seen = []
    for r in runs[-n:]:
        seen += r.get("stats", [])
    return sorted(set(seen))
