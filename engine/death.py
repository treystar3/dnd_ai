"""Death. You lose half your coin; levels and gear are kept. Rule in data/rules/combat.yaml (death)."""

from core.models import Character
from engine import money, pools


def die(c: Character) -> dict:
    from engine import combat
    lose = combat.RULES["death"]["coin_lost"]
    if pools.mechanic(c, "memento_mori") is not None:
        lose /= 2
    if pools.mechanic(c, "faithful_guardian") is not None and c.companions:
        lose = 0.0
    lost_coins = int(c.coins * lose)
    c.coins -= lost_coins
    c.deaths += 1
    c.health = c.stamina = c.mana = None
    return {"level": c.level, "coins": money.fmt(lost_coins), "coins_raw": lost_coins, "kept": money.fmt(c.coins), "deaths": c.deaths}
