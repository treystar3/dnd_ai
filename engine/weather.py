"""Weather, rolled by the engine from the campaign seed. Rules in data/rules/weather.yaml."""

import random
from pathlib import Path

import yaml

from engine import clock

RULES = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "weather.yaml").read_text(encoding="utf-8"))
CONDITIONS = {c["id"]: c for c in RULES["conditions"]}
BLOCK_MINUTES = RULES["change_every_hours"] * 60


_CHAIN: dict[int, list[str]] = {}


def _condition_for_block(seed: int, block: int) -> str:
    """The weather is a chain (each block leans toward the one before), so it is built forward from block 0 and kept -
    never by recursion, which a long campaign would overflow."""
    chain = _CHAIN.setdefault(seed, [])
    ids = list(CONDITIONS)
    while len(chain) <= block:
        b = len(chain)
        previous = chain[-1] if chain else None
        weights = [CONDITIONS[i]["weight"] * (RULES["stickiness"] if i == previous else 1) for i in ids]
        chain.append(random.Random(f"{seed}:weather:{b}").choices(ids, weights=weights)[0])
    return chain[block]


def condition(seed: int, minutes: int) -> dict:
    block = clock.absolute(minutes) // BLOCK_MINUTES
    return CONDITIONS[_condition_for_block(seed, block)]


def temperature(seed: int, minutes: int) -> str:
    temps = RULES["temperatures"]
    step = RULES["by_period"][clock.period(minutes)] + condition(seed, minutes)["temperature_shift"] + \
        (RULES.get("by_season") or {}).get(clock.season(minutes), 0)                 # (f430) the season counts
    return temps[max(0, min(len(temps) - 1, step))]


def describe(seed: int, minutes: int) -> tuple[str, str]:
    """Returns (emoji, 'Clear, cold')."""
    c = condition(seed, minutes)
    emoji = c.get("night_emoji", c["emoji"]) if clock.is_dark(minutes) else c["emoji"]
    return emoji, f"{c['label']}, {temperature(seed, minutes)}"
