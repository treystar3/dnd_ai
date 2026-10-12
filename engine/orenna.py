"""The quest Orenna: the level-50 quest about the goddess nobody remembers.

The engine owns every part of it: the gate (level 50 and the name said aloud), the fixed ruin, the cities where each step happens, the
evidence the player gathers, the fights and the blessing. The words the player reads are fixed in data/world/orenna.yaml, so the truth
is the same in every campaign. Nothing the model says can add a step or change what is true.

Stages, in order: "" -> named -> contact -> ruin -> order -> trails -> registry -> confront -> done."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine import quests

O = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "world" / "orenna.yaml").read_text(encoding="utf-8"))
STAGES = ["", "named", "contact", "ruin", "leaving", "order", "trails", "registry", "confront", "done"]


def state(player) -> dict:
    return player.orenna


def stage(player) -> str:
    return player.orenna.get("stage", "")


def set_stage(player, name: str) -> None:
    player.orenna["stage"] = name


def name_said(text: str) -> bool:
    return "orenna" in (text or "").lower()


def can_start(player) -> bool:
    return not stage(player) and player.character.level >= O["gate"]["level"]


def pick_cities(world, seed) -> dict:
    """The meeting city and the three trail cities: four different great cities, never the capital. Fixed for the campaign."""
    rng = random.Random(f"{seed}:orenna:cities")
    pool = sorted(p.id for p in world.places.values() if p.type == "city" and p.id != O["keeper_city"])
    rng.shuffle(pool)
    return {"meeting": pool[0], "trails": pool[1:4]}


def due_minutes(now: int, seed) -> int:
    lo, hi = O["gate"]["contact_hours"]
    return now + random.Random(f"{seed}:orenna:due:{now}").randint(lo, hi) * 60


def ruin_dungeon(world, level: int, now: int, seed) -> dict:
    """The First Hall as a dungeon in the usual form, but fixed: written once, never remade, floors in the order of the story."""
    R = O["ruin"]
    base = max(O["gate"]["level"], level)
    floors = []
    for i, spec in enumerate(R["floors"]):
        lvl = base + i
        chambers = []
        for ch in spec["chambers"]:
            c = {"kind": ch["kind"]}
            if ch["kind"] == "fight":
                c.update(creature=ch["creature"], level=lvl + (2 if ch.get("boss") else 0), count=ch.get("count", 1),
                         boss=bool(ch.get("boss") and i == len(R["floors"]) - 1), name=ch.get("name", ""))
            chambers.append(c)
        floors.append({"level": lvl, "letter": quests.letter_for_level(lvl), "chambers": chambers, "title": spec["title"]})
    boss_level = base + len(R["floors"]) + 1
    return {"id": f"dungeon_{R['place']}", "name": R["name"], "theme": R["theme"], "place": R["place"], "entrance": f"dungeon_{R['place']}",
            "seed": str(seed), "made": now, "floors": floors, "cleared": [-1, -1], "fixed": "orenna",
            "boss_letter": quests.letter_for_level(boss_level), "boss_name": R["boss_name"]}


def evidence_text(player) -> str:
    return "strong" if player.orenna.get("evidence", 0) >= 2.5 else "thin"


def add_evidence(player, degree: str) -> None:
    value = {"strong success": 1.0, "success": 1.0, "partial": 0.5}.get(degree, 0.0)
    player.orenna["evidence"] = player.orenna.get("evidence", 0.0) + value


def seal_chance(evidence: float) -> float:
    return max(0.35, min(0.95, 0.35 + 0.2 * evidence))


def seal_prompt(combat, boss) -> None:
    """When the High Keeper is bloodied the seal is within reach: the player may try to wrest it free and free the Executioner."""
    from ui import console
    from engine.combat import tell, who
    S = O["confront"]["seal"]
    bound = next((f for f in combat.enemies() if f.bound and f.alive), None)
    if not bound:
        return
    console.note(S["ask"])
    if console.ask().lower() not in ("y", "yes"):
        tell(combat, S["quiet"])
        return
    rng = random.Random(f"{combat.round}:{boss.id}:seal")
    if rng.random() < seal_chance(boss.boss.get("evidence", 0.0)):
        combat.fighters = [f for f in combat.fighters if f is not bound]
        console.note(S["success"])
        tell(combat, S["success"])
    else:
        bound.weapon_damage *= 1.25
        console.note(S["failure"])
        tell(combat, S["failure"])
