"""Leveling and attribute allocation. Rules in data/rules/progression.yaml."""

import re
from core.models import AllocationRecord, Character
from core.rules import ATTRIBUTES
from engine import pools

from engine.stats import RULES

POINTS_PER_LEVEL = int(RULES["points_per_level"])

SHORT = {a[:3]: a for a in ATTRIBUTES}


def level_up(c: Character, levels: int = 1) -> None:
    before = pools.snapshot(c)
    c.level += levels
    c.unspent_points += POINTS_PER_LEVEL * levels
    pools.apply_growth(c, before)


def parse_allocation(text: str) -> tuple[dict[str, int] | None, str | None]:
    """Read '#allocate str 3 dex 2' style input. Accepts 'str 3', '3 str', or full names."""
    tokens = re.findall(r"[a-zA-Z]+|\d+", text.lower())
    spend: dict[str, int] = {}
    pending_stat, pending_num = None, None
    for tok in tokens:
        if tok.isdigit():
            if pending_stat:
                spend[pending_stat] = spend.get(pending_stat, 0) + int(tok)
                pending_stat = None
            else:
                pending_num = int(tok)
        else:
            stat = tok if tok in ATTRIBUTES else SHORT.get(tok[:3])
            if not stat:
                return None, f"'{tok}' isn't an attribute. Use str, dex, con, int, wis or cha."
            if pending_num is not None:
                spend[stat] = spend.get(stat, 0) + pending_num
                pending_num = None
            else:
                pending_stat = stat
    if pending_stat or pending_num is not None or not spend:
        return None, "Give each attribute an amount, e.g. #allocate str 3 dex 2"
    if any(v <= 0 for v in spend.values()):
        return None, "Amounts must be above zero."
    return spend, None


def check_allocation(c: Character, spend: dict[str, int]) -> str | None:
    total = sum(spend.values())
    if total > c.unspent_points:
        return f"That's {total} points, but you only have {c.unspent_points} to spend."
    return None


def allocate(c: Character, spend: dict[str, int]) -> None:
    before = pools.snapshot(c)
    for stat, amount in spend.items():
        setattr(c.attributes, stat, getattr(c.attributes, stat) + amount)
    c.unspent_points -= sum(spend.values())
    c.allocation_log.append(AllocationRecord(level=c.level, spend=dict(spend)))
    pools.apply_growth(c, before)


XP_RULES = __import__("engine.combat", fromlist=["RULES"]).RULES["xp"]


def xp_to_next(level: int) -> int:
    late = XP_RULES.get("need_late")
    extra = 1 + late["per_level"] * max(0, level - late["start_level"]) if late else 1
    return round(XP_RULES["need_base"] * max(1, level) ** XP_RULES["need_exponent"] * extra)


def kill_xp(player_level: int, enemy_level: int, rank: str = "normal") -> int:
    base = XP_RULES["kill_base"] * max(1, enemy_level) ** XP_RULES["kill_exponent"] * XP_RULES["rank"][rank]
    if enemy_level < player_level:
        base *= (enemy_level / player_level) ** XP_RULES["lower_level_exponent"]
    else:
        base *= min(XP_RULES["higher_level_cap"], enemy_level / player_level)
    return max(0, round(base))


def gain_xp(c: Character, amount: int) -> int:
    """Add XP and level up as many times as earned. Returns levels gained."""
    c.xp += amount
    gained = 0
    while c.xp >= xp_to_next(c.level):
        c.xp -= xp_to_next(c.level)
        level_up(c)
        gained += 1
    return gained
