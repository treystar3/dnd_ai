"""Hunger and fatigue (rules in data/rules/needs.yaml)."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
N = yaml.safe_load((ROOT / "data" / "rules" / "needs.yaml").read_text(encoding="utf-8"))


def on() -> bool:
    """False while the whole system is switched off in needs.yaml: nothing builds, nothing is penalised, nothing is shown."""
    return bool(N.get("enabled", True))


def stage_of(value: float) -> dict:
    return next(s for s in N["stages"] if value >= s["from"])


def levels(c) -> tuple[dict, dict]:
    if not on():
        return N["stages"][-1], N["stages"][-1]
    return stage_of(getattr(c, "hunger", 0.0)), stage_of(getattr(c, "fatigue", 0.0))


def penalties(c) -> dict[str, float]:
    """What hunger and fatigue together cost right now: checks (points), stamina / health / damage (percent), rest_heal (a multiplier)."""
    h, f = levels(c)
    out = {k: h[k] + f[k] for k in ("checks", "stamina", "health", "damage")}
    out["checks"] = max(N["checks_floor"], out["checks"])
    for k, cap in N["max_penalty"].items():
        out[k] = max(-cap, out[k])
    out["rest_heal"] = min(h["rest_heal"], f["rest_heal"])
    return out


def tick(c, minutes: float, exertion: bool = False, sleeping: bool = False, resting: bool = False) -> None:
    """Time passes. Hunger always builds; fatigue builds awake and falls asleep (or a little at rest)."""
    if minutes <= 0 or not on():
        return
    hours = minutes / 60
    hx = N["exertion"]["hunger"] if exertion else 1.0
    fx = N["exertion"]["fatigue"] if exertion else 1.0
    c.hunger = min(100.0, getattr(c, "hunger", 0.0) + N["hunger_per_hour"] * hours * hx)
    f = getattr(c, "fatigue", 0.0)
    if sleeping:
        f -= N["sleep_fatigue_per_hour"] * hours
    elif resting:
        f -= N["rest_fatigue_per_hour"] * hours
    else:
        f += N["fatigue_per_hour"] * hours * fx
    c.fatigue = max(0.0, min(100.0, f))


def fight(c) -> None:
    if not on():
        return
    c.hunger = min(100.0, getattr(c, "hunger", 0.0) + N["fight"]["hunger"])
    c.fatigue = min(100.0, getattr(c, "fatigue", 0.0) + N["fight"]["fatigue"])


def eat(c, feeds: float) -> None:
    c.hunger = max(0.0, getattr(c, "hunger", 0.0) - feeds)


def collapsing(c) -> bool:
    if not on():
        return False
    return getattr(c, "fatigue", 0.0) >= N["collapse_at"]


def marks(c) -> tuple[int, int]:
    """Which stage each meter is in (0 fine .. 3 worst)."""
    return tuple(len(N["stages"]) - 1 - N["stages"].index(s) for s in levels(c))


def voice(was: tuple[int, int], now: tuple[int, int]) -> list[str]:
    """The lines that tell the player how their body feels, when a meter crosses into a new stage."""
    out = []
    for kind, before, after in (("hunger", was[0], now[0]), ("fatigue", was[1], now[1])):
        if after == before:
            continue
        lines = N["voice"][kind]
        if after > before:
            out.append(lines["worse"][after - 1])
        elif after == 0:
            out.append(lines["better"])
    return out


def words(c) -> tuple[str, str]:
    h, f = levels(c)
    return h["hunger"], f["fatigue"]


def warning(c) -> str:
    """A short header tag once either meter is past the first stage, else empty."""
    h, f = levels(c)
    tags = [h["hunger"] if h["from"] else "", f["fatigue"] if f["from"] else ""]
    return " · ".join(t for t in tags if t)
