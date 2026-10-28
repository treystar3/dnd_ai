"""(f360) Known people's lives, without a model call: the engine moves a person's goal a step.

Why: the only way a person the player had met changed was a motive step, rationed to half the eventful pulses and a model call each, so
the clerk the player liked moved about once every three hours of play. A step is now the engine's own (data/rules/motives.yaml): a line
in the first person from the table for the trait the goal came from, kept as their memory and as what is on their mind, so the next talk
brings it up; gossip for the town's news; a mood for a while. After steps_most steps the goal ends as drift's rules decide, and the town
remembers. The model is not called; it is still the one who voices the person when the player talks to them."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
M = yaml.safe_load((ROOT / "data" / "rules" / "motives.yaml").read_text(encoding="utf-8"))


def seed_of(npc) -> str:
    """The table a person's steps come from: the first of their traits that has one, else default."""
    tables = M.get("by_seed") or {}
    return next((tr for tr in getattr(npc, "traits", []) if tr in tables), "default")


def step_for(npc, world, t: int) -> dict:
    """This step's line, gossip and mood, filled with the person's own name, trade and town."""
    from engine import pulse
    table = (M.get("by_seed") or {}).get(seed_of(npc)) or (M.get("by_seed") or {}).get("default") or [{"line": "I have been at my own business.", "gossip": "", "mood": ""}]
    row = table[min(int(getattr(npc, "motive_step", 0) or 0), len(table) - 1)]
    town = pulse.town_of(world, npc.location)
    fmt = {"name": npc.name, "role": npc.role.replace("_", " "), "town": world.places[town].name if town in world.places else "town",
           "motive": (npc.motive or "").strip().rstrip(".")}
    return {k: (row.get(k) or "").format(**fmt) for k in ("line", "gossip", "mood")}


def move(store, world, state: dict, npc, t: int, rng: random.Random) -> bool:
    """One step of this person's goal: memory, concern, mood, gossip; the goal ends after steps_most steps. Saves the person. True always."""
    from engine import clock, drift, pulse
    from npc.models import Memory
    row = step_for(npc, world, t)
    npc.memories.append(Memory(day=clock.day(t), turn=-1, text=f"(my own life) {row['line']}"))
    if not npc.concern_from:                                            # a matter's concern (engine/matters.py) wins
        npc.concern = row["line"]
    if row["mood"]:
        npc.mood = row["mood"]
        npc.mood_until = t + int((pulse.P.get("drift") or {}).get("moods", {}).get("days", 6)) * 1440
    if row["gossip"]:
        pulse.add_news(state, row["gossip"], npc.location, t, [world.locals_group(npc.location) or "everyone"])
    npc.motive_step = int(getattr(npc, "motive_step", 0) or 0) + 1
    state["history"].append({"minute": t, "text": f"{npc.name}: {row['line']}", "place": npc.location})
    ended = False
    if npc.motive_step >= int(M.get("steps_most", 3)):
        D = pulse.P.get("drift") or {}
        drift.motive_ends(npc, store, world, D.get("motives") or {}, D.get("moods") or {}, t, rng)   # made or not, by the drift's chance; the town remembers
        npc.motive_step = 0
        ended = True
    store.save_npc(npc)
    from engine import pulselog
    pulselog.note("motive", f"{npc.name}: {row['line']} [{'ended' if ended else 'step ' + str(npc.motive_step)}]", place=npc.location, engine=True,
                  seed=seed_of(npc))
    return True


def problems(seeds: set[str]) -> list[str]:
    bad = []
    tables = M.get("by_seed") or {}
    if "default" not in tables:
        bad.append("motives.yaml by_seed: needs a default table")
    for k, rows in tables.items():
        if not rows or len(rows) < int(M.get("steps_most", 3)):
            bad.append(f"motives.yaml by_seed.{k}: needs at least steps_most lines")
        for r in rows or []:
            if not (r or {}).get("line"):
                bad.append(f"motives.yaml by_seed.{k}: a step needs a line")
    for k in seeds:
        if k not in tables:
            bad.append(f"motives.yaml by_seed: no table for the seed '{k}' (pulse.yaml drift.motives.seeds)")
    return bad
