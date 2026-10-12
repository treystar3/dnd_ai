"""The party: adventurers the guild sends with you. Pure rules - who is for hire, what they cost, what they fight like.

Rules live in data/rules/party.yaml. The engine decides everything here; the model only voices the scene.
"""

import random
from pathlib import Path

import yaml

from engine import combat

ROOT = Path(__file__).resolve().parent.parent
P = yaml.safe_load((ROOT / "data" / "rules" / "party.yaml").read_text(encoding="utf-8"))


class Shape:
    """A creature-like stand-in so a hireling can be built with the same code as a monster."""
    def __init__(self, member: dict):
        role = P["roles"][member["role"]]
        self.id = member["id"]
        self.name = member["name"]
        self.size, self.category, self.temperament = "Medium", "humanoid", "aggressive"
        self.profile = dict(P["profiles"][role["profile"]])
        self.attacks = list(role["attacks"])
        self.group = (1, 1)


def roster(seed, hall: str, day: int, player_level: int, rank_coins: int, used: list[str]) -> list[dict]:
    """The adventurers free at a hall this week. Same list for the same week; hired ones drop off it."""
    week = day // P["roster_days"]
    rng = random.Random(f"{seed}:party:{hall}:{week}")
    out = []
    roles = list(P["roles"])
    for i in range(P["roster_size"]):
        role = roles[i % len(roles)] if i < len(roles) else rng.choice(roles)
        lo, hi = P["veteran_share"] if rng.random() < P["veteran_chance"] else P["level_share"]
        level = max(1, round(player_level * rng.uniform(lo, hi)))
        name = f"{rng.choice(P['names']['first'])} {rng.choice(P['names']['last'])}"
        out.append({"id": f"{week}-{i}", "name": name, "role": role, "level": level,
                    "blurb": rng.choice(P["roles"][role]["blurb"]), "fee": 0, "hall": hall})
    rng.shuffle(out)
    for m in out:
        m["fee"] = fee(m, player_level, rank_coins)
    return [m for m in out if f"{m['hall']}:{m['id']}" not in used]


def fee(member: dict, player_level: int, rank_coins: int) -> int:
    ratio = member["level"] / max(1, player_level)
    return max(1, round(rank_coins * P["fee_share"] * P["roles"][member["role"]]["fee"] * ratio ** P["fee_power"]))


def fighter(member: dict, fid: str | None = None) -> combat.Fighter:
    f = combat.fighter_from_creature(Shape(member), member["level"], "normal", fid or f"ally_{member['id']}", member["name"], "near")
    f.side = "ally"
    f.ally_role = member["role"]
    return f


def is_scout(member: dict) -> bool:
    return bool(P["roles"][member["role"]].get("scout"))


def sneak_penalty(party: list[dict]) -> int:
    return P["stealth"]["sneak_each"] * sum(1 for m in party if not is_scout(m))


def scout_bonus(party: list[dict]) -> int:
    return min(P["stealth"]["scout_cap"], P["stealth"]["scout_each"] * sum(1 for m in party if is_scout(m)))
