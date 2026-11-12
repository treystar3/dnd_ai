"""(f594) An act a character tries, ruled on by the dungeon master and kept (docs/design/02 sections 3, 5 and 8; data/rules/act.yaml).

One call gives the ruling and what the act changes if it works (llm/contracts.py ActRuling), the targets named by their codes
(engine/targets.py) and the changes from the closed list (data/rules/changes.yaml). It is asked before the transaction
(data/rules/budget.yaml asked_outside). The engine then checks it, reading only (validate): what the character can do, that each thing
it relies on is there, and each change in order as one chain, a situation's parts by the situation ruling's own rules
(engine/situation_parts.py ruled). A ruling is kept per character (the save's `act_rulings` row) with what it read, a no among them:
the same act at the same place and time of day, the targets it named and the things lying here in the same state, and the character able
to do the same, is ruled the same with no call (the reuse rule).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from core import yamlio

A = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "act.yaml").read_text(encoding="utf-8"))
_STOP = set(A.get("filler") or ())

SYSTEM = """You are the dungeon master of a fantasy role-playing game. A player has said what their character tries. You rule on it the
way a good dungeon master does at the table: if it makes sense here, for this character, in this world, the world makes room for it; if
not, it does not happen. And you say what it changes if it works.

Rule with:
  sense:    "yes"  - it makes sense and they can simply do it with what they have (walk on, call out, look closely, sit down).
            "cost" - it makes sense, but it takes time, effort or skill, or carries a risk (climbing, digging, swimming, sneaking).
            "no"   - it does not make sense in this world or for this character: impossible for anyone (summoning a dragon from
                     nothing, conjuring gold, making the sun set), or it needs a power they do not have.
  why:      one short line, in the world's terms.
  uses:     the codes from TARGETS the act relies on, if any: the thing to hide behind, the rope to climb, the person spoken to.
  needs:    what the world must hold for it that is NOT in TARGETS: a part of the place (kind "feature"), a person (kind "person", with
            a role from ROLES when one fits), a thing (kind "thing": a loose rock, a rope left behind), or a way (kind "way": a passage
            onward). Only what it cannot happen without; at most two; never treasure, magic items or creatures to fight. Each: name
            (short), what (one sentence of what it is), where (where it is from the player).
  requires: the names from CAPABILITIES the attempt needs, whether or not the character has them. Most attempts need none.
  stakes:   check - one of CHECKS, or an attribute, when chance decides it; hard - easy, fair or hard. Leave empty for a plain yes.
  changes:  what the act, if it works, makes lastingly different, each on one target by its code from TARGETS, named from CHANGES and
            only on the kinds that change lands on: a door barred (state, on a part), a road closed (access), a rope broken (on a
            thing), a frightened clerk (afraid, on a person), a situation's guard won over (open, on its part). n: its number; needs:
            the numbers of earlier changes it cannot stand without; because: what it rests on (words, coin, goods, force, evidence,
            earlier, skill). Most acts change nothing that lasts; leave it empty then. Whether a situation is over is never yours to say.
  fail:     what a failure costs, one of FAIL.
  answer:   for a no only: what happens instead, in the world, second person, as it would be seen.
  instead:  for a no only: one or two things they could try that would make sense.
Respond only with JSON matching the schema."""


# ---------- the request

def request(ws, actor_id: str, T, words: str, text: str) -> str:
    from engine import checks, features, inventory, ruling, targets
    if actor_id != ws.acting:                        # (f594) one character a scene until multiplayer M1: never another's sheet
        raise ValueError(f"an act is ruled for the scene's own character, not {actor_id}")
    c = ws.player.character
    place = ws.place
    gear = ", ".join(i.name for i in c.equipment.values())[:200] or "nothing"
    pack = ", ".join(inventory.label(i) for i in c.inventory[:12]) or "nothing"
    abilities = ", ".join(a.name for a in c.actives[:12]) or "none"
    caps = "\n".join(f"  {k}: {v['about']}" for k, v in ruling.C.items())
    have = ", ".join(sorted(means(ws, actor_id))) or "none"
    changes = "\n".join(f"  {k}: on {', '.join(v['lands_on'])}" for k, v in targets.CH["changes"].items())
    last = ws.recent_narration[-1] if ws.recent_narration else "(none)"
    return (f"PLACE: {place.name} ({place.type}{', ' + place.biome if place.biome else ''}{', dangerous' if place.danger else ''})\n"
            "TARGETS (what the act can name, by code):\n" + ("\n".join(f"  {x}" for x in T.lines()) or "  (none)") + "\n"
            f"THE CHARACTER: level {c.level} {c.custom_class or c.archetype.value}; carries {gear}; in the pack {pack}; abilities {abilities}\n"
            f"WHAT THEY CAN DO BEYOND THE ORDINARY: {have}\n"
            f"CAPABILITIES:\n{caps}\n"
            f"CHECKS: {', '.join(sorted(checks.CHECKS))}, or an attribute ({', '.join(ruling.ATTRS)})\n"
            f"CHANGES:\n{changes}\n"
            f"BECOMES (a part's state): {', '.join(features.F['becomes'])}\n"
            f"FAIL: {', '.join(A['fails'])}\n"
            f"ROLES: {', '.join(sorted(ws.world.roles))}\n"
            f"THE LAST PASSAGE: {last}\n\n"
            f"THE PLAYER TRIES: {words}\nTHEIR WORDS: \"{text}\"")


def means(ws, actor_id: str) -> set[str]:
    """What the acting character can do beyond the ordinary (engine/ruling.py means_of): today the scene's one character."""
    from engine import ruling
    return ruling.means_of(ws) if actor_id == ws.acting else set()


def context(ws, T) -> dict:
    from engine import checks, ruling, targets
    return {"capabilities": list(ruling.C), "checks": sorted(checks.CHECKS) + list(ruling.ATTRS), "roles": sorted(ws.world.roles),
            "changes": list(targets.CH["changes"]), "codes": T.codes(), "most": int(A["most_changes"]), "fails": list(A["fails"])}


def ask(ws, actor_id: str, T, words: str, text: str):
    """The model's ruling, or None when it cannot give one (the act is then never rolled unruled)."""
    from llm.contracts import ActRuling
    from llm.gateway import LLMError, generate
    from ui import console
    try:
        return generate("act_ruling", SYSTEM, request(ws, actor_id, T, words, text), ActRuling, temperature=0.3, max_tokens=700,
                        validation_context=context(ws, T))
    except LLMError as e:
        console.debug(f"act ruling: none ({e})")
        return None


# ---------- the kept rulings (the reuse rule)

def words_key(text: str) -> str:
    """The act's words as the reuse rule compares them: lower case, plain words, the filler left out."""
    return " ".join(w for w in re.findall(r"[a-z0-9']+", (text or "").lower()) if w not in _STOP)


def _means_key(ws, actor_id: str) -> str:
    return hashlib.sha1("|".join(sorted(means(ws, actor_id))).encode("utf-8")).hexdigest()[:12]


def _named(r) -> list[str]:
    """Every code a ruling names: what it uses and every target, who and about of its changes."""
    out = [u.split(":", 1)[0].strip().lower() for u in r.uses]
    for ch in r.changes:
        out += [x for x in (ch.target, ch.who, ch.about, ch.to) if x]
    return out


def _to_refs(r, T) -> dict:
    """The ruling as kept: every code turned into the record it names, so a later list (where codes may stand elsewhere) reads it."""
    d = r.model_dump()
    ref = lambda c: ("@" + T.get(c).ref) if c and T.get(c) else c
    d["uses"] = [ref(u.split(":", 1)[0].strip().lower()) for u in r.uses]
    for ch in d["changes"]:
        for k in ("target", "who", "about", "to"):
            ch[k] = ref(ch[k])
    return d


def _from_refs(d: dict, T, ctx: dict):
    """A kept ruling read back against today's list: each record to its code now; None when one is no longer there."""
    from llm.contracts import ActRuling
    by_ref = {t.ref: t.code for t in T.rows}
    d = json.loads(json.dumps(d))

    def code(x):
        if isinstance(x, str) and x.startswith("@"):
            if x[1:] not in by_ref:
                raise KeyError(x)
            return by_ref[x[1:]]
        return x
    try:
        d["uses"] = [code(u) for u in d.get("uses") or []]
        for ch in d.get("changes") or []:
            for k in ("target", "who", "about", "to"):
                ch[k] = code(ch.get(k, ""))
        return ActRuling.model_validate(d, context=ctx)
    except (KeyError, ValueError):
        return None


def _scene_key(ws, actor_id: str, T) -> str:
    """What a ruling reads of the scene beyond the targets it names: the time of day, and the things lying here and their state."""
    from engine import clock
    things = sorted(f"{t.ref}={t.state}" for t in T.rows if t.kind == "object" and "carried by you" not in t.line)
    return hashlib.sha1(f"{clock.period(ws.minutes)}|{'|'.join(things)}".encode("utf-8")).hexdigest()[:12]


def kept(ws, actor_id: str, T, text: str):
    """The ruling this character was given for the same act here, if all it read is as it was; else None. Reads only: the act that
    stands on it marks it used (use)."""
    rows = ws.store.load_act_rulings().get(actor_id) or []
    key, place, m, scene = words_key(text), ws.player.location, _means_key(ws, actor_id), _scene_key(ws, actor_id, T)
    states = {t.ref: t.state for t in T.rows}
    for row in reversed(rows):
        if (row["key"], row["place"], row["means"], row["scene"]) != (key, place, m, scene):
            continue
        if any(ref not in states or states[ref] != st for ref, st in row["read"].items()):
            continue
        r = _from_refs(row["ruling"], T, context(ws, T))
        if r is not None:
            return r
    return None


def use(ws, actor_id: str, text: str) -> None:
    """A kept ruling stood for an act again: its days unused start over (within the act's operation)."""
    data = ws.store.load_act_rulings()
    key, place = words_key(text), ws.player.location
    for row in data.get(actor_id) or []:
        if row["key"] == key and row["place"] == place:
            row["used"] = int(ws.minutes)
    ws.store.save_act_rulings(data)


def keep(ws, actor_id: str, T, text: str, r) -> None:
    """Keep a ruling for this character with all it read, in place of an older one for the same act here; past per_character, or
    after days unused, the oldest go."""
    data = ws.store.load_act_rulings()
    key, place, now = words_key(text), ws.player.location, int(ws.minutes)
    read = {T.get(c).ref: T.get(c).state for c in _named(r) if T.get(c)}
    rows = [x for x in data.get(actor_id) or [] if not (x["key"] == key and x["place"] == place)
            and now - int(x.get("used", x["minute"])) < int(A["kept"]["days"]) * 1440]
    rows.append({"key": key, "place": place, "means": _means_key(ws, actor_id), "scene": _scene_key(ws, actor_id, T), "read": read,
                 "minute": now, "used": now, "ruling": _to_refs(r, T)})
    data[actor_id] = rows[-int(A["kept"]["per_character"]):]
    ws.store.save_act_rulings(data)


# ---------- the engine's check (reads, never writes)

@dataclass
class Checked:
    ok: bool
    ruling: object = None
    answer: str = ""
    instead: list = field(default_factory=list)
    why: str = ""
    dropped: list = field(default_factory=list)      # (change, why)
    enabled: bool = False      # a real thing it relies on (a tagged thing, the ground of a part): a strong success may match an ability's


def validate(ws, actor_id: str, T, r) -> Checked:
    """The engine's checks on a ruling, reading only. A no stands; a yes may be refused on the engine's grounds (a power the character
    lacks, a need the world cannot hold); each change is checked in order as one chain, and one that does not hold is dropped with its
    reason and so is every change that needs it."""
    from types import SimpleNamespace
    from engine import ruling
    if r.sense == "no":
        return Checked(False, r, r.answer, list(r.instead), r.why or "it does not make sense here")
    lacking = [cap for cap in r.requires if cap in ruling.C and cap not in means(ws, actor_id)]
    if lacking:
        return Checked(False, r, ruling.C[lacking[0]]["lacking"], list(r.instead), f"needs {lacking[0]}, which they do not have")
    v = ruling.verdict(ws, SimpleNamespace(sense=r.sense, requires=[], needs=r.needs, changes=[], answer=r.answer, instead=r.instead,
                                           why=r.why))
    if not v["ok"]:
        return Checked(False, r, v["answer"], v["instead"], v["why"])
    kept_changes, dropped = _chain(ws, actor_id, T, r)
    out = r.model_copy(update={"changes": kept_changes})
    enabled = any((t := T.get(u)) is not None and (t.kind == "part" or (t.kind == "object" and t.tags)) for u in r.uses)
    return Checked(True, out, "", [], r.why, dropped, enabled)


def _chain(ws, actor_id: str, T, r) -> tuple[list, list]:
    from engine import entities, features, situation_parts, targets
    store, world = ws.store, ws.world
    kept, dropped, gone = [], [], set()
    sits: dict[str, list] = {}
    part_of = {t.who: t.code for t in T.rows if t.who}            # a person here who is also a situation's part: that part
    now: dict[str, str] = {}                                      # a thing's state as the changes before leave it
    moves = entities.L["object"].get("moves") or {}
    after = {"broken": "broken", "mended": "here", "found": "here", "hidden_here": "hidden", "destroyed": "destroyed", "moved": "here"}
    for ch in r.changes:
        t = T.get(ch.target)
        if t is not None and t.kind == "person" and t.ref in part_of and ch.becomes in situation_parts.S["rulings"]["changes"]:
            ch = ch.model_copy(update={"target": part_of[t.ref]})   # the situation's own rules hold for them
            t = T.get(ch.target)
        for k in ("who", "about"):
            x = getattr(ch, k)
            if x and T.get(x) is not None and T.get(x).ref in part_of:
                ch = ch.model_copy(update={k: part_of[T.get(x).ref]})
        why = ""
        if t is None:
            why = "no such target"
        elif not targets.lands_on(ch.becomes, t.kind):
            why = f"{ch.becomes} does not land on a {t.kind}"
        elif set(ch.needs) & gone:
            why = "it needs a change that did not hold"
        elif ch.becomes == "state" and ch.state not in features.F["becomes"]:
            why = f"a part does not become '{ch.state}'"
        elif ch.becomes == "access" and ch.state not in ("open", "closed", "hidden"):
            why = "access is open, closed or hidden"
        elif t.kind == "object":
            e = store.load_entity(t.ref)
            was = now.get(t.ref, e.state if e is not None else "")
            to = after.get(ch.becomes, was)
            if e is None:
                why = "the thing is gone"
            elif to != was and to not in moves.get(was, []):
                why = f"a thing {was} cannot be {ch.becomes}"
            elif ch.becomes == "moved" and T.kind_of(ch.to) != "part":
                why = "a thing is moved to a part of this place"
            else:
                now[t.ref] = to
        if why:
            dropped.append((ch, why))
            gone.add(ch.n)
            continue
        if t.code.startswith("s") and "." in t.code:
            sits.setdefault(t.code.split(".")[0], []).append(ch)
        kept.append(ch)
    for scode, chs in sits.items():                   # a situation's parts by the situation ruling's own chain
        th_id = T.get(scode).ref
        th = next((x for x in (store.load_world_state() or {}).get("threads", []) if x["id"] == th_id), None)
        held: set[int] = set()
        why_of: dict[int, str] = {}
        if th is not None:
            idx = lambda code: int(code.split(".")[1]) if code.startswith(scode + ".") else 0
            rows = [{"n": ch.n, "part": idx(ch.target), "who": idx(ch.who), "becomes": ch.becomes,
                     "because": "force" if ch.because == "skill" else ch.because, "about": idx(ch.about),
                     "needs": [n for n in ch.needs if n in {c.n for c in chs}]} for ch in chs]
            act = {"kind": "acted", "by": actor_id, "npc": "", "witnesses": sorted(n.id for n in ws.present), "place": ws.player.location,
                   "coin": 0, "item": "", "count": 1, "degree": "", "words_only": False}
            ok, bad = situation_parts.ruled(store, th, act, rows, world)
            held = {c["n"] for c in ok}
            why_of = {c.get("n"): w for c, w in bad}
        for ch in chs:
            if ch.n not in held:
                dropped.append((ch, why_of.get(ch.n) or ("the situation is over" if th is None else "it does not hold in the situation")))
                gone.add(ch.n)
    out = []
    for ch in kept:                                    # in order: what needed a dropped change goes too
        if ch.n in gone:
            continue
        if set(ch.needs) & gone:
            dropped.append((ch, "it needs a change that did not hold"))
            gone.add(ch.n)
            continue
        out.append(ch)
    return out, dropped


def problems() -> list[str]:
    """(f594) act.yaml's shape: the kept rulings capped, the changes a ruling may carry, the failures to choose from."""
    bad = []
    k = A.get("kept") or {}
    for name, v in (("kept.per_character", k.get("per_character")), ("kept.days", k.get("days")), ("most_changes", A.get("most_changes"))):
        if not (isinstance(v, int) and not isinstance(v, bool) and v > 0):
            bad.append(f"act.yaml {name}: needs a whole number above 0")
    if not (isinstance(A.get("fails"), list) and A["fails"] and all(isinstance(x, str) and x for x in A["fails"])):
        bad.append("act.yaml fails: needs a list of failures")
    if not (isinstance(A.get("filler"), list) and all(isinstance(x, str) and x for x in A["filler"])):
        bad.append("act.yaml filler: needs a list of words")
    return bad
