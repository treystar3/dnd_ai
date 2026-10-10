"""Money. Stored as a count of the smallest coin; split into denominations only for display."""

from pathlib import Path

import yaml

RULES = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "currency.yaml").read_text(encoding="utf-8"))
DENOMINATIONS = RULES["denominations"]

for _d in DENOMINATIONS[:-1]:
    if not isinstance(_d.get("per_next_smaller"), int) or _d["per_next_smaller"] < 2:
        raise ValueError(f"currency.yaml: '{_d['id']}' needs per_next_smaller, a whole number of 2 or more")


def _values() -> list[tuple[str, str, int]]:
    """(id, symbol, value in smallest coins), largest first."""
    out, value = [], 1
    smallest_first = list(reversed(DENOMINATIONS))
    for i, d in enumerate(smallest_first):
        if i > 0:
            value *= d["per_next_smaller"]
        out.append((d["id"], d["symbol"], value))
    return list(reversed(out))


VALUES = _values()


def split(amount: int) -> list[tuple[str, str, int]]:
    parts, rest = [], max(0, amount)
    for coin_id, symbol, value in VALUES:
        parts.append((coin_id, symbol, rest // value))
        rest %= value
    return parts


def fmt(amount: int) -> str:
    return " ".join(f"{count}{symbol}" for _, symbol, count in split(amount))


def to_smallest(**coins: int) -> int:
    """to_smallest(gold=1, silver=5) -> 10500"""
    return sum(next(v for i, _, v in VALUES if i == k) * n for k, n in coins.items())


def words(amount: int) -> str:
    """Natural form for speech and narration: 250 -> '2 silver and 50 copper'."""
    parts = [f"{count} {coin_id}" for coin_id, _, count in split(amount) if count]
    if not parts:
        return "nothing"
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
