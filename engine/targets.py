"""(f593) What an act can name, by a short code (docs/design/02 section 4; data/rules/changes.yaml).

An act's ruling names the things it uses and the things it changes. Here they are numbered for the prompt and looked up again by their
code, so a ruling never names a thing by words the engine has to guess at:

    p1  a person here                     (npc id)
    c1  a companion with the character    (hire id)
    f1  a part of this place              (feature ref)
    o1  a thing lying here, or carried    (object ref)
    r1  a road out                        (road id)
    s1  a situation whose trouble is here, and s1.2 its second part, numbered as engine/situation_parts.py parts_lines numbers them

The list is built for one character (its id): the things they carry, what they know of the parts and the people. Built twice on the same
world, the same thing has the same code; a code is a place in this list, so what is kept of a ruling is keyed by `ref` and `state`, never
by code. A person who is also a situation's part is one person: the part's line says so ("(p1)") and carries their id in `who`. What is
gone, or carried by someone else, is not listed. No change lands on a whole situation (s1), only on its parts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core import yamlio

CH = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "changes.yaml").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Target:
    code: str            # p1, f2, o1, r3, s1.2
    kind: str            # a kind of changes.yaml: person, part, object, road, condition, resource, tie, evidence (a situation: "situation")
    ref: str             # the record: an npc id, a feature or object ref, a road id, a thread id (for s1.2: "<thread id>#<index>")
    line: str            # how the prompt shows it
    state: str = ""      # what a ruling on it read of it: a changed state is a changed circumstance (the reuse rule)
    who: str = ""        # a situation's person: their npc id
    tags: tuple = ()     # a thing's tags (data/rules/objects.yaml): what it can be used as or for


@dataclass
class Targets:
    rows: list[Target] = field(default_factory=list)

    def get(self, code: str) -> Target | None:
        code = (code or "").strip().split(":", 1)[0].strip().lower()   # "f2: the brazier" names f2
        return next((t for t in self.rows if t.code == code), None)

    def exists(self, code: str) -> bool:
        return self.get(code) is not None

    def kind_of(self, code: str) -> str:
        t = self.get(code)
        return t.kind if t else ""

    def lines(self) -> list[str]:
        return [f"{t.code} {t.line}" for t in self.rows]

    def codes(self) -> list[str]:
        return [t.code for t in self.rows]


def _state(*parts) -> str:
    return "|".join(str(p) for p in parts if p not in (None, "", [], {}))


def targets_for(ws, actor_id: str) -> Targets:
    """Everything an act of this character here can name: the people present, the parts of the place, the things lying here and the
    things they carry, the roads out, and each live situation whose trouble is here with its parts."""
    from engine import features, objects, pulse, roads, situation_parts
    store, world = ws.store, ws.world
    place = ws.player.location
    out: list[Target] = []
    codes: dict[str, str] = {}
    for i, n in enumerate((n for n in ws.present if not getattr(n, "gone", False)), 1):
        label, role = n.label(actor_id), n.role.replace("_", " ")
        codes[n.id] = f"p{i}"
        out.append(Target(f"p{i}", "person", n.id, f"{label}{'' if role in label else f' ({role})'}, here", state=_state(n.location)))
    for i, m in enumerate(getattr(ws.player, "party", None) or [], 1):          # the character's own companions
        out.append(Target(f"c{i}", "person", str(m.get("id", "")), f"{m.get('name', 'a companion')} ({m.get('role', 'companion')}), "
                          "your companion", state=_state(getattr(ws.player, "party_mode", ""))))
    known = [e for e in sorted(features.here(store, place), key=lambda e: (features.depth(e), e.ref)) if e.state != "unseen"]
    for i, e in enumerate(known, 1):
        now = sorted(features.now_of(e, ws.minutes))
        out.append(Target(f"f{i}", "part", e.ref, f"{e.name}: {e.data.get('what', '')}".rstrip(": "), state=_state(e.state, ",".join(now))))
    things = [(e, "") for e in objects.here(store, place, ws.minutes)] + [(e, "carried by you") for e in objects.carried(store, actor_id)]
    for i, (e, how) in enumerate(things, 1):
        said = [x for x in (e.data.get("what", ""), "broken" if e.state == "broken" else "", how) if x]
        out.append(Target(f"o{i}", "object", e.ref, e.name + (f" ({'; '.join(said)})" if said else ""), state=_state(e.state, e.owner),
                          tags=tuple(e.data.get("tags") or ())))
    town = pulse.town_of(world, place) if place in world.places else ""
    ways = sorted(rid for rid, r in world.roads.items() if {r.from_, r.to} & {place, town} or roads.on_road(world, place, rid))
    shut = pulse.shut_roads(store.load_world_state() or {}, world, ws.minutes)
    for i, rid in enumerate(ways, 1):
        r = world.roads[rid]
        ends = [x for x in (r.from_, r.to) if x in world.places and x not in (place, town)] or [x for x in (r.from_, r.to) if x in world.places]
        out.append(Target(f"r{i}", "road", rid, f"{r.name}, between {' and '.join(world.places[x].name for x in (r.from_, r.to) if x in world.places)}"
                          if len(ends) == 2 else f"{r.name}" + (f", to {world.places[ends[0]].name}" if ends else ""),
                          state=_state("shut" if rid in shut else "")))
    state = store.load_world_state() or {}
    live = sorted((th for th in state.get("threads", []) if th.get("status") == "active" and th.get("parts")),
                  key=lambda th: (int(th.get("made", 0)), th["id"]))
    k = 0
    for th in live:
        near, on = situation_parts.trouble_near(world, th, th["parts"])
        if place not in near and not any(roads.on_road(world, place, rid) for rid in on):
            continue
        k += 1
        out.append(Target(f"s{k}", "situation", th["id"], th.get("title", "a situation")))
        for j, (a, line) in enumerate(zip(th["parts"], situation_parts.parts_lines(store, world, th, actor_id)), 1):
            who = a.get("who", "") if a.get("kind") == "person" else ""
            text = line.split(". ", 1)[-1] if ". " in line else line
            out.append(Target(f"s{k}.{j}", a.get("kind", ""), f"{th['id']}#{j - 1}", text + (f" ({codes[who]})" if who in codes else ""),
                              state=_state(a.get("now"), (a.get("willing") or {}).get(actor_id)), who=who))
    return Targets(out)


def lands_on(change: str, kind: str) -> bool:
    """Whether a change of changes.yaml may land on this kind of target."""
    return kind in ((CH.get("changes") or {}).get(change) or {}).get("lands_on", [])


def problems(C: dict | None = None, S: dict | None = None, becomes: set | None = None) -> list[str]:
    """(f593) changes.yaml's shape: every change lands on known kinds; the situation ruling's words are all here, on at least the kinds
    they land on there; a state's `becomes` are the parts' own (features.yaml)."""
    C = CH if C is None else C
    if S is None:
        S = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "situations.yaml").read_text(encoding="utf-8"))
    if becomes is None:
        from engine import features
        becomes = set(features.F["becomes"])
    bad = []
    kinds, changes = set(C.get("kinds") or ()), C.get("changes") or {}
    if not kinds:
        bad.append("changes.yaml kinds: needs the kinds of target")
    for name, row in changes.items():
        on = (row or {}).get("lands_on") or []
        if not on:
            bad.append(f"changes.yaml changes.{name}: needs `lands_on`, the kinds it may land on")
        for k in on:
            if k not in kinds:
                bad.append(f"changes.yaml changes.{name}: '{k}' is no kind of target")
    theirs_all = (S.get("rulings") or {}).get("changes") or {}
    for word, row in theirs_all.items():
        theirs = set((row or {}).get("kinds") or ())
        mine = set(((changes.get(word) or {}).get("lands_on")) or ())
        if word not in changes:
            bad.append(f"changes.yaml changes: the situation ruling's '{word}' is missing")
        elif not theirs <= mine:
            bad.append(f"changes.yaml changes.{word}: must land on {sorted(theirs)} as the situation ruling's does")
    part_kinds = {"person", "condition", "resource", "tie", "evidence"}           # what only the situation ruling's words write
    for word, row in changes.items():
        if set((row or {}).get("lands_on") or ()) & part_kinds and word not in theirs_all:
            bad.append(f"changes.yaml changes.{word}: lands on a person or a situation's part, but the situation ruling has no such word")
    if "situation" in kinds:
        bad.append("changes.yaml kinds: no change lands on a whole situation, only on its parts")
    if "state" in changes and not becomes:
        bad.append("changes.yaml changes.state: the parts' states (features.yaml becomes) are missing")
    return bad
