"""Law: theft rolled on a bar, who notices, how wanted you are, and what that costs. All numbers are in data/rules/law.yaml.

Nothing here talks to a model or to the screen; the scene (scenes/law_actions.py) feeds it facts and acts on what it returns."""
from __future__ import annotations

import math
import random
from pathlib import Path

import yaml

L = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "law.yaml").read_text(encoding="utf-8"))
T, N, H, FB = L["theft"], L["notice"], L["heat"], L["fight_back"]
DEGREES = ("strong success", "success", "partial", "failure")


# ---------- the bar ----------

def zone_level(world, place_id: str) -> int:
    """How hard the place is: the middle of its creature levels in the wild, or of the item levels its merchants stock in a town."""
    from engine import pulse
    place = world.places[place_id]
    if not place.danger:
        place = world.places[pulse.town_of(world, place_id)]
    lo, hi = place.danger or place.trade_level
    return max(1, round((lo + hi) / 2))


def window(zone: int) -> int:
    w = T["window"]
    return max(1, round(max(w["minimum"], w["per_level"] * (zone - 1)) * w["scale"]))


def reference_score(zone: int, investment: float) -> float:
    """The score of a character who put this share of their level-up points into Dexterity, starting from the usual start."""
    dex = T["start_dex"] + investment * T["points_per_level"] * (zone - 1)
    return T["score_per_point"] * (dex - T["attribute_center"])


def reference_bar(zone: int) -> float:
    """The bar for an average steal in a zone: even odds for the anchor build."""
    W = window(zone)
    a = T["anchor"]
    return reference_score(zone, a["investment"]) + W * (1 - a["chance"]) + 1


def item_term(value: int) -> float:
    """Percent of the window a thing's value adds to the bar."""
    i = T["item"]
    if value <= i["baseline"]:
        return 0.0
    return min(i["cap"], i["per_doubling"] * math.log2(value / i["baseline"]))


def situation_term(owner_present: bool, witnesses: int) -> float:
    s = T["situation"]
    return (s["watched"] if owner_present else s["unattended"]) + s["per_witness"] * witnesses


def gear_multiplier(points: float) -> float:
    """Stealth gear is written in points (a +20 ring is 20); it multiplies the roll, never past the cap."""
    return min(T["gear_multiplier_cap"], 1 + max(0, points) / 100)


def score(dexterity: int, percent_bonuses: float, W: int) -> float:
    """Allocated Dexterity (never gear), plus passives, training and scene bonuses, each a percent of the window."""
    return T["score_per_point"] * (dexterity - T["attribute_center"]) + percent_bonuses / 100 * W


def degree_for(margin_pct: float) -> str:
    d = T["degrees"]
    for name in ("strong success", "success", "partial"):
        if margin_pct >= d[name]:
            return name
    return "failure"


def attempt(zone: int, dexterity: int, bonus_pct: float, item_value: int, owner_present: bool, witnesses: int,
            target_pct: float = 0.0, gear_points: float = 0.0, rng: random.Random | None = None) -> dict:
    """One theft roll. bonus_pct: passives, training and scene bonuses (percent of W). target_pct: how much harder the victim's
    character makes it, as a percent of W (a suspicious person is positive). Returns the numbers behind the result."""
    W = window(zone)
    mult = gear_multiplier(gear_points)
    my = score(dexterity, bonus_pct, W)
    bar = reference_bar(zone) + (item_term(item_value) + situation_term(owner_present, witnesses) + target_pct) / 100 * W
    best = (W * mult + my - bar) * 100 / W
    out = {"window": W, "score": my, "bar": bar, "mult": mult, "hopeless": best < T["degrees"]["partial"]}
    if out["hopeless"]:
        out.update(roll=0, degree="failure")
        return out
    roll = (rng or random).randint(1, W)
    out["roll"] = roll
    out["degree"] = degree_for((roll * mult + my - bar) * 100 / W)
    return out


def chance_table(zone: int, dexterity: int, bonus_pct=0.0, item_value=0, owner_present=False, witnesses=0, target_pct=0.0, gear_points=0.0) -> dict:
    """The odds of each degree for a roll, for tests and tuning."""
    W = window(zone)
    mult = gear_multiplier(gear_points)
    my = score(dexterity, bonus_pct, W)
    bar = reference_bar(zone) + (item_term(item_value) + situation_term(owner_present, witnesses) + target_pct) / 100 * W
    count = dict.fromkeys(DEGREES, 0)
    for r in range(1, W + 1):
        count[degree_for((r * mult + my - bar) * 100 / W)] += 1
    return {k: v / W for k, v in count.items()}


# ---------- who notices ----------

def worth_value(tier: str) -> int:
    return T["worth"].get(tier, T["worth"]["ordinary"])


def notice_chance(degree: str, role: str, is_target: bool = False, assault: bool = False) -> float:
    if assault:
        base = N["assault"]
    elif is_target and degree == "failure":
        base = N["target_failure"]
    else:
        base = N["by_degree"][degree]
    return min(100.0, base * N["role_factor"].get(role, 1.0))


def notices(degree: str, role: str, is_target: bool = False, assault: bool = False, rng: random.Random | None = None) -> bool:
    return (rng or random).uniform(0, 100) < notice_chance(degree, role, is_target, assault)


# ---------- heat ----------

def current_heat(player, town: str, day: int) -> int:
    rec = player.heat.get(town)
    if not rec:
        return 0
    from engine import world_perks
    return world_perks.heat_today(getattr(player, "character", None), rec, day, max(0, rec["heat"] - H["decay_per_day"] * max(0, day - rec["day"])))


def set_heat(player, town: str, value: int, day: int) -> int:
    value = max(0, min(100, round(value)))
    if value <= 0:
        player.heat.pop(town, None)
    else:
        player.heat[town] = {"heat": value, "day": day}
    return value


def add_heat(player, town: str, amount: float, day: int) -> int:
    return set_heat(player, town, current_heat(player, town, day) + amount, day)


def tier(heat: int) -> str:
    t = H["tiers"]
    if heat >= t["wanted"]:
        return "wanted"
    if heat >= t["confront"]:
        return "confront"
    if heat >= t["cold"]:
        return "cold"
    return "clear"


def fine(heat: int) -> int:
    return round(H["fine_per_point"] * heat)


def offense_heat(kind: str, value: int, story: bool, only_passersby: bool) -> float:
    base = H["gain"]["assault"] if kind == "assault" else (H["gain"]["story_theft"] if story else H["gain"]["theft"])
    if kind == "theft" and value > H["valuable_over"]:
        base += H["gain"]["valuable_bonus"]
    return base * (H["passerby_share"] if only_passersby else 1)


def price_factor(heat: int) -> float:
    return 1 + H["price_markup"] if heat >= H["tiers"]["cold"] else 1.0


def fights_back(role: str, traits: list[str], rng: random.Random | None = None) -> bool:
    chance = FB["base"] + (FB["armed_bonus"] if role in FB["armed_roles"] else 0) + sum(FB["traits"].get(t, 0) for t in traits)
    return (rng or random).uniform(0, 100) < max(0, min(100, chance))
