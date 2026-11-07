"""(f542) A situation's parts (Stage 4, the owner's decisions of 2026-11-07 in GOALS.md): the engine's check of what the model proposed
(llm/contracts.py SituationParts), part by part, and the fixed render of what passed.

check() is pure: it reads the store and the world and writes nothing. It takes the parts in the order proposed, people first, and drops
a part that fails with its reason while the rest stand: a person neither of the town nor a role the world has, one gone, the player, the
same person twice, or past the caps by tier (data/rules/situations.yaml); a role resolves to a person of that trade in the town first, and
only past them is someone new for the engine to make; a good the world does not have; a holder, a tie's end or what evidence points to
that is not of the situation; a place or road the world does not have; a closure of the only way between two places when the situation
offers no way through it; words that name the game's machinery. Whether each piece of evidence is true is rolled here, once, on the die
passed in (the pulse's seeded one), against its certainty's chance (a sure piece never false); the proposing model is never told.

render() makes THE PARTS lines from the names, trades and goods of the world, never an id, one line per part from the phrase tables,
each drawn on streams.fixed(key, "parts", i), so a situation's lines are the same every time they are told."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine import hygiene, retrieval, roads, streams

ROOT = Path(__file__).resolve().parent.parent
S = yaml.safe_load((ROOT / "data" / "rules" / "situations.yaml").read_text(encoding="utf-8"))
KINDS = ("people", "resources", "ties", "conditions", "evidence")


def _raw(text: str, ids: set[str]) -> bool:
    """Words that name the game's machinery: a snake_case or coded id, a placeholder, or an id of the world or the store."""
    if not text:
        return False
    if "_" in text or hygiene.SNAKE.search(text) or hygiene.CODED.search(text) or hygiene.PLACEHOLDER.search(text):
        return True
    return any(w in ids for w in text.lower().replace(",", " ").replace(".", " ").split())


def check(parts, store, world, tier: str, rng: random.Random, *, town: str = "", ways: bool = True,
          player_id: str = "") -> tuple[list[dict], list[tuple[dict, str]]]:
    """(accepted parts, dropped (part, reason)). `town` is the situation's town (its people are found first for a role); `ways` whether
    the situation offers the player a way through it (a closure of an only way needs one)."""
    from engine import pulse
    caps, why = S["caps"], S["reasons"]
    never = set(S.get("never_roles") or ())
    accepted: list[dict] = []
    dropped: list[tuple[dict, str]] = []
    names = {pid for pid, pl in world.places.items() if pl.name.lower() == pid} | {rid for rid, r in world.roads.items() if r.name.lower() == rid}
    ids = (set(world.places) | set(world.roads)) - names                     # a place called by its own id ("parth") is a name, not an id
    rows = retrieval.people_in_town(store, world, town) if town else []
    used: set[str] = set()
    who_of: dict[str, str] = {}                                              # what the proposal called someone -> who they are

    def room(kind: str) -> str:
        if len(accepted) >= caps["parts"].get(tier, 0):
            return "parts_cap"
        if kind == "person":
            return "people_cap" if sum(a["kind"] == "person" for a in accepted) >= caps["people"] else ""
        return "kind_cap" if sum(a["kind"] == kind for a in accepted) >= caps["each_other"] else ""

    def drop(part, reason: str) -> None:
        dropped.append((part.model_dump() if hasattr(part, "model_dump") else dict(part), why[reason]))

    new = 0
    for p in parts.people:
        w = (p.who or "").strip()
        if w.lower() in ("player", "the player", "you") or (player_id and w == player_id):
            drop(p, "player"); continue
        if _raw(p.label, ids):
            drop(p, "raw_id"); continue
        person, made = "", False
        if store.npc_exists(w):
            n = store.load_npc(w)
            if n.gone:
                drop(p, "gone"); continue
            person = w
        elif w in world.roles and w not in never:
            free = next((r.id for r in rows if r.role == w and r.id not in used), "")
            person, made = (free, False) if free else (w, True)              # (the owner) the town's own of that trade first
        else:
            drop(p, "not_a_person"); continue
        if person in used or w in who_of:
            drop(p, "twice"); continue
        full = room("person")
        if full:
            drop(p, full); continue
        if made and new >= caps["new_people"].get(tier, 0):
            drop(p, "new_cap"); continue
        holds = p.holds if p.holds in _goods() else ""
        new += made
        used.add(person)
        who_of[w] = person
        accepted.append({"kind": "person", "who": person, "new": made, "stake": p.stake, "want": p.want, "condition": p.condition,
                         "holds": holds, "label": p.label})

    def person_of(ref: str) -> str:
        return who_of.get((ref or "").strip(), "")

    for p in parts.resources:
        if p.good not in _goods():
            drop(p, "not_a_good"); continue
        holder = person_of(p.holder) if p.holder else ""
        if p.holder and not holder:
            drop(p, "no_holder"); continue
        if _raw(p.label, ids):
            drop(p, "raw_id"); continue
        full = room("resource")
        if full:
            drop(p, full); continue
        accepted.append({"kind": "resource", "good": p.good, "state": p.state, "holder": holder, "label": p.label})
    for p in parts.ties:
        a, b = person_of(p.a), person_of(p.b)
        if not a or not b:
            drop(p, "no_end"); continue
        if a == b:
            drop(p, "self_tie"); continue
        full = room("tie")
        if full:
            drop(p, full); continue
        accepted.append({"kind": "tie", "a": a, "b": b, "tie": p.tie})
    shut = pulse.shut_roads(store.load_world_state() or {}, world, 0) if parts.conditions else set()
    for p in parts.conditions:
        if not (pulse.known(world, p.on) or p.on in world.roads):
            drop(p, "not_a_place"); continue
        if p.kind == "closed" and p.on in world.roads and not ways and not roads.way_round(world, p.on, shut):
            drop(p, "only_way"); continue
        if _raw(p.label, ids):
            drop(p, "raw_id"); continue
        full = room("condition")
        if full:
            drop(p, full); continue
        accepted.append({"kind": "condition", "on": p.on, "what": p.kind, "label": p.label})
    for p in parts.evidence:
        holder = person_of(p.holder) or (p.holder if pulse.known(world, p.holder) else "")
        if not holder:
            drop(p, "no_holder"); continue
        points = person_of(p.points_to) or (p.points_to if pulse.known(world, p.points_to) or p.points_to in world.roads else "")
        if not points:
            drop(p, "points_nowhere"); continue
        if not p.label.strip() or _raw(p.label, ids):
            drop(p, "raw_id"); continue
        full = room("evidence")
        if full:
            drop(p, full); continue
        false = rng.random() < float(S["false_chance"].get(p.certainty, 0.0))   # (the owner) the engine's, once; a sure piece never false
        accepted.append({"kind": "evidence", "holder": holder, "points_to": points, "certainty": p.certainty, "label": p.label,
                         "true": not false})
    return accepted, dropped


def _goods() -> dict:
    from engine import inventory
    return inventory.GOODS


def render(accepted: list[dict], store, world, key: str, with_truth: bool = False) -> str:
    """THE PARTS: one line per accepted part, names and goods never ids. `with_truth` adds whether each piece of evidence holds (for a
    telling; never for the model that proposed the parts)."""
    P = S["phrases"]
    lines = []

    def name(who: str) -> str:
        if store.npc_exists(who):
            return store.load_npc(who).name
        if who in world.places:
            return world.places[who].name
        if who in world.roads:
            return world.roads[who].name
        return P["new_person"].format(trade=who.replace("_", " "))

    def part_name(a: dict) -> str:
        return name(a["who"])

    def good(g: str) -> str:
        gd = _goods().get(g)
        return gd.name if gd else g.replace("_", " ")

    for i, a in enumerate(accepted):
        rng = streams.fixed(key, "parts", i)
        k = a["kind"]
        if k == "person":
            line = rng.choice(P["stake"][a["stake"]]).format(name=part_name(a)) + " " + rng.choice(P["want"][a["want"]])
            if a.get("condition"):
                line += ", " + rng.choice(P["condition"][a["condition"]])
            if a.get("holds"):
                line += ", " + rng.choice(P["holds"]).format(good=good(a["holds"]))
        elif k == "resource":
            line = rng.choice(P["state"][a["state"]]).format(good=good(a["good"]))
            if a.get("holder"):
                line += ", " + rng.choice(P["held_by"]).format(name=name(a["holder"]))
        elif k == "tie":
            line = rng.choice(P["tie"][a["tie"]]).format(name=name(a["a"]), other=name(a["b"]))
        elif k == "condition":
            line = rng.choice(P["kind"][a["what"]]).format(place=name(a["on"]))
        else:
            line = rng.choice(P["certainty"][a["certainty"]]).format(holder=name(a["holder"]), label=a["label"].strip().rstrip("."),
                                                                      points=name(a["points_to"]))
            if with_truth:
                line += ". " + rng.choice(P["is_true"] if a.get("true", True) else P["is_false"]).rstrip(".")
        lines.append("- " + line[:1].upper() + line[1:].rstrip(".") + ".")
    return ("THE PARTS:\n" + "\n".join(lines)) if lines else ""


def problems() -> list[str]:
    """(f542) The lists held equal to the contract's Literals both ways, the caps and chances sound, every phrase table filled."""
    import string
    import typing
    from llm import contracts as c
    bad = []
    L = S.get("lists") or {}

    def lit(model, field) -> set:
        return {x for x in typing.get_args(model.model_fields[field].annotation) if x != ""}
    for name, model, field in (("stakes", c.PartPerson, "stake"), ("wants", c.PartPerson, "want"), ("conditions", c.PartPerson, "condition"),
                               ("ties", c.PartTie, "tie"), ("resource_states", c.PartResource, "state"),
                               ("place_kinds", c.PartCondition, "kind"), ("certainties", c.PartEvidence, "certainty")):
        if set(L.get(name) or ()) != lit(model, field):
            bad.append(f"situations.yaml lists.{name}: {sorted(set(L.get(name) or ()))} differs from the contract's {sorted(lit(model, field))}")
    effects = set(typing.get_args(c.WorldEffect.model_fields["kind"].annotation))
    for k in L.get("place_kinds") or ():
        if k not in effects:
            bad.append(f"situations.yaml lists.place_kinds: '{k}' is not an effect the pulse applies")
    caps = S.get("caps") or {}
    for t in ("parts", "new_people"):
        for tier, n in (caps.get(t) or {}).items():
            if not isinstance(n, int) or n < 0:
                bad.append(f"situations.yaml caps.{t}.{tier}: a whole number of 0 or more")
    for t in ("people", "each_other"):
        if not isinstance(caps.get(t), int) or caps.get(t) < 1:
            bad.append(f"situations.yaml caps.{t}: a whole number of 1 or more")
    fc = S.get("false_chance") or {}
    if set(fc) != set(L.get("certainties") or ()):
        bad.append("situations.yaml false_chance: one chance for each certainty")
    if fc.get("sure", 0) != 0:
        bad.append("situations.yaml false_chance.sure: a sure piece of evidence is never false (the owner)")
    if any(not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in fc.values()):
        bad.append("situations.yaml false_chance: each a chance between 0 and 1")
    P = S.get("phrases") or {}
    sample = {"name": "Hollis", "other": "Maud", "good": "salt", "place": "the ford", "holder": "Hollis", "label": "a cut rope",
              "points": "the toll keeper", "trade": "bargeman"}
    tables = {"stake": L.get("stakes"), "want": L.get("wants"), "condition": L.get("conditions"), "tie": L.get("ties"),
              "state": L.get("resource_states"), "kind": L.get("place_kinds"), "certainty": L.get("certainties")}
    for table, keys in tables.items():
        for k in keys or ():
            got = (P.get(table) or {}).get(k)
            if not isinstance(got, list) or len(got) < 4:
                bad.append(f"situations.yaml phrases.{table}.{k}: four lines or more, so nothing is told the same way twice running")
                continue
            for line in got:
                try:
                    out = line.format(**sample)
                except (KeyError, IndexError, ValueError) as e:
                    bad.append(f"situations.yaml phrases.{table}.{k}: '{line}' ({e})"); continue
                if "{" in out or "}" in out or "_" in out:
                    bad.append(f"situations.yaml phrases.{table}.{k}: '{line}' leaves machinery")
    for flat in ("holds", "held_by", "is_true", "is_false"):
        got = P.get(flat)
        if not isinstance(got, list) or len(got) < 4 or any("{" in x.format(**sample) for x in got):
            bad.append(f"situations.yaml phrases.{flat}: four lines or more, every slot one of {sorted(sample)}")
    if "{trade}" not in str(P.get("new_person") or ""):
        bad.append("situations.yaml phrases.new_person: names someone yet to be made by {trade}")
    for k in ("not_a_person", "gone", "player", "twice", "people_cap", "new_cap", "parts_cap", "kind_cap", "not_a_good", "no_holder",
              "no_end", "self_tie", "not_a_place", "only_way", "points_nowhere", "raw_id"):
        if not (S.get("reasons") or {}).get(k):
            bad.append(f"situations.yaml reasons.{k}: a reason is needed")
    return bad
