"""Chains and arcs: quests that turn out bigger than they looked, built as a fixed skeleton.

The ENGINE decides whether a contract is a short job, a chain or an arc (roll_scale), picks every place the story will
visit (plan), and holds the state (advance). The model dresses the skeleton once; nothing it says can add a step."""

import random
from pathlib import Path

import yaml

from engine import quests
from engine import streams

ROOT = Path(__file__).resolve().parent.parent / "data"
A = yaml.safe_load((ROOT / "rules" / "arcs.yaml").read_text(encoding="utf-8"))

def _full(t: dict) -> dict:
    """A template with the defaults and the wording of its kind of subject filled in."""
    out = {**A["template_defaults"], **t}
    out["words"] = {**A["kinds"][out["subject_kind"]], **{k: t[k] for k in ("start", "end") if k in t}}
    out["victims"] = t.get("subjects", [])
    return out


TEMPLATES = {t["id"]: _full(t) for t in yaml.safe_load((ROOT / "world" / "arcs.yaml").read_text(encoding="utf-8"))}
SIZES = ["simple", "chain", "arc"]


def active(data: dict) -> dict | None:
    return next((a for a in data["arcs"] if a["state"] == "active"), None)


def settlements(world) -> list[str]:
    return [p.id for p in world.places.values() if p.type in ("town", "city")]


def cities_reachable(world, hall: str) -> list[str]:
    return [s for s in settlements(world) if world.path(hall, s)]


# ---------- the decision: what is this contract really? ----------

def roll_scale(world, data: dict, quest_id: str, seed: int, level: int, rank: str, hall: str, now: int, tier: int = 0) -> tuple[str, str]:
    """Returns (size, why). Seeded, so the same contract always rolls the same."""
    S = A["scale"]
    rng = random.Random(f"{seed}:arc:{quest_id}")
    weights = dict(S["weights"])
    weights["arc"] += S["hall_tier_bonus"].get(tier, 0)
    reasons = []
    # gates: what is locked right now
    locked = set()
    for size in ("chain", "arc"):
        if level < S["min_level"][size]:
            locked.add(size); reasons.append(f"{size} locked: level {level} < {S['min_level'][size]}")
        elif quests.LETTERS.index(rank or "F") < quests.LETTERS.index(S["min_rank"][size]):
            locked.add(size); reasons.append(f"{size} locked: rank {rank or 'F'} < {S['min_rank'][size]}")
    if S["one_active_arc"] and active(data):
        locked |= {"chain", "arc"}; reasons.append("another chain or arc is running")
    if now // 1440 < data["last_end"] // 1440 + S["cooldown_days"]:
        locked |= {"chain", "arc"}; reasons.append("quiet spell after the last story")
    if len(cities_reachable(world, hall)) < S["min_cities"]["arc"]:
        locked.add("arc"); reasons.append("too few settlements to cross")
    roll = rng.choices(SIZES, weights=[weights[s] for s in SIZES])[0]
    final = roll
    while final in locked:
        final = SIZES[SIZES.index(final) - 1]
    return final, f"rolled {roll}" + (f", fell back to {final} ({'; '.join(reasons)})" if final != roll else "")


# ---------- the skeleton ----------

def pattern(size: str, n: int, tpl: dict | None = None, rng: random.Random | None = None) -> list[str]:
    """The kinds of the steps, in order: always a person first, always the finale last, the template's mix between."""
    if size == "simple" or n <= 2:
        return ["contact"] * (n - 1) + ["boss"]
    mix = {k: v for k, v in (tpl or {}).get("mix", {"contact": 3, "lair": 1}).items() if v > 0} or {"contact": 1}
    rng = rng or random.Random(0)
    middle, last = [], "contact"
    for _ in range(n - 2):
        pool = dict(mix)
        if last in ("lair", "site") and len(pool) > 1:
            pool[last] = pool[last] * 0.35          # avoid a long run of the same kind of step
        kind = rng.choices(list(pool), weights=list(pool.values()))[0]
        middle.append(kind)
        last = kind
    if "contact" not in middle and n >= 4:
        middle[len(middle) // 2] = "contact"         # a trail always passes through at least one person
    return ["contact"] + middle + ["boss"]


def ranked(world, ids: list[str], level: int) -> list[str]:
    ok = [i for i in ids if i in world.bestiary] or ["bandit"]
    def gap(i):
        lo, hi = world.bestiary[i].levels
        return 0 if lo <= level <= hi else min(abs(level - lo), abs(level - hi))
    return sorted(ok, key=lambda i: (gap(i), -world.bestiary[i].levels[1]))


def pick_creature(world, ids: list[str], level: int) -> str:
    """The creature from a template's list whose usual levels are nearest the wanted level (the fight is scaled anyway)."""
    ok = [i for i in ids if i in world.bestiary] or ["bandit"]
    def gap(i):
        lo, hi = world.bestiary[i].levels
        return 0 if lo <= level <= hi else min(abs(level - lo), abs(level - hi))
    return min(ok, key=lambda i: (gap(i), -world.bestiary[i].levels[1]))


def plan(world, store, hall: str, level: int, size: str, template: dict, rng: random.Random, taken_places=()) -> list[dict]:
    """Pick the fixed list of steps and the real place of each. The count is final."""
    lo, hi = A["nodes"][size]
    n = rng.randint(lo, hi)
    kinds = pattern(size, n, template, rng)
    towns = sorted((s for s in cities_reachable(world, hall)), key=lambda s: world.path(hall, s)[1])
    here = quests._town(world, hall)
    out_towns = [t for t in towns if t != here] or towns
    wilds = [p for p in world.places.values() if p.danger and p.type not in ("road", "dungeon") and world.path(hall, p.id)]
    nodes, used_t, used_w = [], [], []
    ti = 0
    # the one behind it all lives in the most dangerous land the player can reasonably face
    allowed = [p for p in wilds if p.danger[1] <= max(15, level * 1.3)] or wilds
    boss_place = max(allowed, key=lambda p: (p.danger[1] if p.danger[1] <= max(15, level * 1.3) else 0) + rng.random()).id
    used_w.append(boss_place)
    for i, kind in enumerate(kinds):
        node = {"id": f"n{i + 1}", "kind": kind, "status": "hidden", "attempts": 0, "partial": False, "clue_given": False}
        if kind == "contact":
            pool = [t for t in out_towns if t not in used_t] or out_towns
            pick = pool[0] if size != "arc" else pool[(ti * max(1, len(pool) // max(1, kinds.count("contact")))) % len(pool)]
            ti += 1
            used_t.append(pick)
            node["place"] = pick
            node["role"] = rng.choice([r for r in template["contacts"] if r in world.roles] or ["merchant"])
        elif kind == "boss":
            node["place"] = boss_place
            node["role"] = ""
        elif kind == "site" and template.get("site_in") == "town":
            pool = [t for t in out_towns if t not in used_t] or out_towns
            pick = pool[(ti + 1) % len(pool)] if len(pool) > 1 else pool[0]
            ti += 1
            used_t.append(pick)
            node["place"] = pick
            node["role"] = ""
            node["check"] = list(template["site_checks"])
        else:
            want = level * 0.7
            pool = [p for p in wilds if p.id not in used_w] or wilds
            pool.sort(key=lambda p: abs((p.danger[0] + p.danger[1]) / 2 - want) + rng.random() * 6)
            pick = pool[0]
            used_w.append(pick.id)
            node["place"] = pick.id
            node["role"] = ""
            if kind == "site":
                node["check"] = list(template["site_checks"])
        peoples = world.peoples_at(node["place"]) or {"human": 100}
        node["people"] = max(peoples, key=peoples.get)
        nodes.append(node)
    for a, b in zip(nodes, nodes[1:]):
        a["reveals"] = b["id"]
    nodes[-1]["reveals"] = ""
    nodes[0]["status"] = "known"
    return nodes


def build(world, store, quest: dict, hall: str, level: int, size: str, why: str, now: int, seed: int) -> dict:
    rng = random.Random(f"{seed}:arcplan:{quest['id']}")
    tpl = TEMPLATES.get(quest.get("template")) or rng.choice(list(TEMPLATES.values()))
    nodes = plan(world, store, hall, level, size, tpl, rng)
    return {"id": streams.new_id(8), "template": tpl["id"], "size": size, "why": why, "state": "active",
            "started": now, "deadline": None, "quest": quest["id"], "hall": hall,
            "level": level, "victim_phrase": quest.get("victim") or rng.choice(tpl["victims"]), "revealed": False, "nodes": nodes, "story": None,
            "log": [], "paid": 0, "effects": []}


def site_body(seed, arc: dict, n: dict) -> bool:
    """Whether this site holds a body someone could question. Fixed for the campaign, so it never changes between visits."""
    return n["kind"] == "site" and random.Random(f"{seed}:body:{arc['id']}:{n['id']}").random() < A["body"]["site_chance"]


def finish(data: dict, arc: dict, state: str, now: int) -> None:
    arc["state"] = state
    arc["ended"] = now
    if arc["size"] != "simple":
        data["last_end"] = now           # only a real story earns a quiet spell; a short job does not


# ---------- state ----------

def node(arc: dict, node_id: str) -> dict | None:
    return next((n for n in arc["nodes"] if n["id"] == node_id), None)


def current(arc: dict) -> dict | None:
    return next((n for n in arc["nodes"] if n["status"] in ("known", "active")), None)


def step_text(arc: dict) -> str:
    done = sum(1 for n in arc["nodes"] if n["status"] == "done")
    total = len(arc["nodes"])
    return f"step {done + 1} of {total}" if arc["revealed"] else "still following the trail"


def complete_node(arc: dict, nid: str, partial: bool = False) -> dict | None:
    """Mark a step done and open the next. Returns the next step, or None when the story is at its end."""
    n = node(arc, nid)
    n["status"] = "done"
    n["partial"] = partial
    nxt = node(arc, n["reveals"]) if n["reveals"] else None
    if nxt:
        nxt["status"] = "known"
    idx = arc["nodes"].index(n) + 1
    if A["reveal_at"].get(arc["size"]) and idx >= A["reveal_at"][arc["size"]] and not arc["revealed"] and arc["size"] != "simple":
        arc["revealed"] = True
    return nxt


def reward(arc: dict, rank_letter: str) -> tuple[int, int]:
    r = quests.G["ranks"][rank_letter]["reward"]
    m = A["rewards"][arc["size"]]
    return round(r["coins"] * m), round(r["xp"] * m)


def node_pay(rank_letter: str) -> tuple[int, int]:
    r = quests.G["ranks"][rank_letter]["reward"]
    return round(r["coins"] * A["node_pay"]), round(r["xp"] * A["node_pay"])


def gift_companion(character, arc: dict, world):
    """The animal a grateful ending may leave with someone who keeps no companions, or None."""
    from core.models import Companion
    G = A["gift_companion"]
    if character.uses_companions or any(c.source == "gift" for c in character.companions):
        return None
    rng = random.Random(f"{arc['id']}:gift")
    if rng.random() >= G["chance"].get(arc["size"], 0):
        return None
    animals = [a for a in G["animals"] if a["creature"] in world.bestiary]
    if not animals:
        return None
    a = rng.choice(animals)
    name = rng.choice(G["names"])
    return Companion(id=f"gift_{arc['id']}", name=name, creature=a["creature"], kind="beast", role=a["role"], level=character.level,
                     description=f"{name}, {a['how']}.", source="gift", perks=dict(a.get("perks", {})))


def perk_text(companion) -> str:
    """What a companion's perks do, in the words of the passive they borrow."""
    import yaml
    defs = {m["id"]: m for m in yaml.safe_load((ROOT / "rules" / "passive_mechanics.yaml").read_text(encoding="utf-8"))}
    return " ".join(defs[k]["text"].format(value=f"{v:g}") for k, v in companion.perks.items() if k in defs)
