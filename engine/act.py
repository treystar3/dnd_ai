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
  stakes:   check - one of CHECKS, or an attribute, when chance decides it; hard - easy, fair, hard, or beyond: past anything someone
            with what they have could do, however they try (it then does not happen). Leave empty for a plain yes.
  changes:  what the act, if it works, makes lastingly different, each on one target by its code from TARGETS, named from CHANGES and
            only on the kinds that change lands on: a door barred (state, on a part), a road closed (access), a rope broken (on a
            thing), a frightened clerk (afraid, on a person), a situation's guard won over (open, on its part). n: its number; needs:
            the numbers of earlier changes it cannot stand without; because: what it rests on (words, coin, goods, force, evidence,
            earlier, skill). Most acts change nothing that lasts; leave it empty then. Whether a situation is over is never yours to say.
  fail:     what a failure costs, one of FAIL.
  works:    for a yes or a cost: what it comes to if it works, second person, as it would be seen. Only what someone with what they have
            could bring about here, however much the words claim: a claim is heard, not granted; a speech is made, not obeyed.
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


def shape(ws, T):
    """(f606) The act ruling's contract for this call: it validates as ActRuling does, and the grammar the model writes against is made
    for the scene, so a ruling can only be written in words the engine takes: targets by code, each with only the change words that land
    on its kind (never a situation itself), who acts where a change needs it, the state a change of state or of access gives, the fail,
    the check and the capabilities from their lists, a no that says what happens instead, and short free text."""
    import copy
    from engine import checks, features, ruling, situation_parts, targets
    from llm.contracts import ActRuling
    L = A["grammar"]
    defs = ActRuling.model_json_schema()["$defs"]
    actor = {w: r.get("actor") for w, r in situation_parts.S["rulings"]["changes"].items()}
    kinds: dict[str, list[str]] = {}
    for t in T.rows:
        kinds.setdefault(t.kind, []).append(t.code)
    codes = T.codes()
    beside = [c for c in codes if T.kind_of(c) != "situation"]
    people = kinds.get("person", [])
    enum = lambda xs, empty=True: {"enum": ([""] if empty else []) + list(xs)} if xs else {"type": "string", "maxLength": 0}
    text = lambda n: {"type": "string", "maxLength": int(L[n])}
    states = {"state": list(features.F["becomes"]), "access": list(targets.CH["changes"]["access"]["args"])}

    def variant(cs: list[str], group: list[str], how: str) -> dict:
        """One shape of change: these targets, these words, and what the words need (who acts; the state given)."""
        need = ["n", "target", "becomes", "because"]           # (f613) what it rests on, never left to a default
        props = {"n": {"type": "integer"}, "target": {"enum": cs}, "becomes": {"enum": group}, "to": enum(kinds.get("part", [])),
                 "about": enum(beside), "because": {"enum": defs["ActChange"]["properties"]["because"]["enum"]},
                 "needs": {"type": "array", "items": {"type": "integer"}, "maxItems": int(A["most_changes"])}, "label": text("label")}
        if how in ("self", "person"):
            props["who"], need = enum(people, empty=False), need + ["who"]      # done by a person of the situation: who, by name
        else:
            props["who"] = enum([] if how == "act" else people)
        if how in states:
            props["state"], need = enum(states[how], empty=False), need + ["state"]
        else:
            props["state"] = enum([])                                        # no state for a change that gives none
        return {"type": "object", "required": need, "properties": props}

    changes = []
    for kind, cs in kinds.items():
        if kind == "situation":
            continue
        groups: dict[str, list[str]] = {}
        for w in targets.CH["changes"]:
            if targets.lands_on(w, kind):
                how = w if w in states else ("person" if actor.get(w) == "person" else actor.get(w) or "either")
                groups.setdefault(how if how in ("self", "person", "act", *states) else "either", []).append(w)
        changes += [variant(cs, group, how) for how, group in groups.items() if not (how in ("self", "person") and not people)]
    need = {"type": "object", "required": ["kind", "name"], "properties": {
        "kind": {"enum": defs["Need"]["properties"]["kind"]["enum"]}, "name": text("need_name"), "what": text("need_what"),
        "where": text("need_where"), "role": enum(sorted(ws.world.roles))}}
    common = {
        "why": text("why"),
        "uses": {"type": "array", "items": enum(codes, empty=False), "maxItems": int(L["uses"])} if codes else {"type": "array", "maxItems": 0},
        "needs": {"type": "array", "items": need, "maxItems": int(L["needs"])},
        "requires": {"type": "array", "items": {"enum": list(ruling.C) + sorted(checks.CHECKS) + list(ruling.ATTRS)},   # a check named
                     "maxItems": int(L["requires"])},                                        # here moves to the stakes, as the contract has it
        "stakes": {"type": "object", "properties": {"check": {"enum": [""] + sorted(checks.CHECKS) + list(ruling.ATTRS)},
                                                    "hard": {"enum": defs["ActStakes"]["properties"]["hard"]["enum"]}}},
        "fail": {"enum": list(A["fails"])},
        "instead": {"type": "array", "items": text("instead"), "maxItems": int(L["instead_items"])}}
    acts = {"type": "array", "items": {"anyOf": changes} if changes else {"type": "object"},
            "maxItems": int(A["most_changes"]) if changes else 0}
    yes = {"type": "object", "required": ["sense", "works"], "properties": {"sense": {"enum": ["yes", "cost"]}, **common, "changes": acts,
                                                                            "works": {**text("works"), "minLength": 1}}}   # (f609)
    no = {"type": "object", "required": ["sense", "answer", "requires"], "properties": {       # (f618) a no says what power it wants, if any
        "sense": {"enum": ["no"]}, **common, "changes": {"type": "array", "maxItems": 0}, "answer": {**text("answer"), "minLength": 1}}}
    schema = {"title": "ActRuling", "anyOf": [yes, no]}

    class Shaped(ActRuling):
        @classmethod
        def model_json_schema(cls, *a, **k) -> dict:
            return copy.deepcopy(schema)
    Shaped.__name__ = Shaped.__qualname__ = "ActRuling"
    return Shaped


def ask(ws, actor_id: str, T, words: str, text: str):
    """The model's ruling, or None when it cannot give one (the act is then never rolled unruled)."""
    from llm.contracts import ActRuling
    from llm.gateway import LLMError, generate
    from ui import console
    try:
        return generate("act_ruling", SYSTEM, request(ws, actor_id, T, words, text), shape(ws, T), temperature=0.3, max_tokens=700,
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
    without: str = ""          # (f618) the capability it is done without, on what stands in for it


def validate(ws, actor_id: str, T, r) -> Checked:
    """The engine's checks on a ruling, reading only. A no stands; a yes may be refused on the engine's grounds (a power the character
    lacks, a need the world cannot hold); each change is checked in order as one chain, and one that does not hold is dropped with its
    reason and so is every change that needs it."""
    from types import SimpleNamespace
    from engine import ruling
    how, cap, stakes = ruling.standing(means(ws, actor_id), r)   # (f618) the engine decides what lacking a power means
    if r.sense == "no" and how != "stand_in":
        return Checked(False, r, r.answer, list(r.instead), r.why or "it does not make sense here")
    if r.stakes.hard == "beyond":                    # (f613) the ruling's own word: past anyone with what they have
        why = (r.why or "").strip().rstrip(".")
        return Checked(False, r, A["beyond"]["answer"] + (f" ({why})" if why else "") + ".", list(r.instead), A["beyond"]["why"])
    if how == "lacks":
        return Checked(False, r, ruling.C[cap]["lacking"], list(r.instead), f"needs {cap}, which they do not have")
    if how == "stand_in":                            # done without it: a cost on what stands in, whichever way the model ruled
        r = r.model_copy(update={"sense": "cost", "stakes": type(r.stakes)(**stakes)})
    v = ruling.verdict(ws, SimpleNamespace(sense=r.sense, requires=[], needs=r.needs, changes=[], answer=r.answer, instead=r.instead,
                                           why=r.why))
    if not v["ok"]:
        return Checked(False, r, v["answer"], v["instead"], v["why"])
    kept_changes, dropped = _chain(ws, actor_id, T, r)
    out = r.model_copy(update={"changes": kept_changes})
    enabled = any((t := T.get(u)) is not None and (t.kind == "part" or (t.kind == "object" and t.tags)) for u in r.uses)
    return Checked(True, out, "", [], r.why, dropped, enabled, cap if how == "stand_in" else "")


def _chain(ws, actor_id: str, T, r) -> tuple[list, list]:
    from engine import entities, features, situation_parts, targets
    store, world = ws.store, ws.world
    kept, dropped, gone = [], [], set()
    sits: dict[str, list] = {}
    part_of = {t.who: t.code for t in T.rows if t.who}            # a person here who is also a situation's part: that part
    now: dict[str, str] = {}                                      # a thing's state as the changes before leave it
    moves = entities.L["object"].get("moves") or {}
    after = {"broken": "broken", "mended": "here", "found": "here", "hidden_here": "hidden", "destroyed": "destroyed", "moved": "here"}
    layer = {w: x.get("layer") for w, x in situation_parts.S["rulings"]["changes"].items()}
    group = {l: i for i, g in enumerate(A["one_a_person"]) for l in g}
    taken: dict[tuple, str] = {}                                  # (f613) (a person, a group of layers): the change that took it
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
        elif ch.becomes == "access" and ch.state not in ("open", "closed"):
            why = "a way through is opened or closed"
        elif t.kind == "person" and t.code.startswith("c"):
            why = "a companion is moved by their own story, never by a ruling"
        elif t.kind == "person" and not t.code.startswith("s") and ch.becomes not in A["outside_situation"]:
            why = "one outside a situation is moved only in what they believe and how they feel"
        elif t.kind == "object":
            e = store.load_entity(t.ref)
            was = now.get(t.ref, e.state if e is not None else "")
            to = after.get(ch.becomes, was)
            if e is None:
                why = "the thing is gone"
            elif to != was and to not in moves.get(was, []):
                why = f"a thing {was} cannot be {ch.becomes}"
            elif ch.becomes == "moved" and (was != "here" or T.kind_of(ch.to) != "part"):
                why = "a thing lying here is moved to a part of this place"
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
                     "because": _because(ch, r.stakes.check), "hand": r.stakes.check in A["hand_checks"], "about": idx(ch.about),
                     "needs": [n for n in ch.needs if n in {c.n for c in chs}]} for ch in chs]
            act = {"kind": "acted", "by": actor_id, "npc": "", "witnesses": sorted(n.id for n in ws.present), "place": ws.player.location,
                   "coin": 0, "item": "", "count": 1, "degree": "", "words_only": False, "force_by_change": True}   # (f600) never a violent act
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
        t = T.get(ch.target)
        key = (t.ref, group.get(layer.get(ch.becomes))) if t is not None and t.kind == "person" and layer.get(ch.becomes) in group else None
        if key in taken:                               # (f613) over what held only: a refused change takes no one's stance
            dropped.append((ch, f"they cannot be {ch.becomes} as well as {taken[key]}"))
            gone.add(ch.n)
            continue
        if key is not None:
            taken[key] = ch.becomes
        out.append(ch)
    return out, dropped


def _because(ch, check: str) -> str:
    """(f600) What a change rests on, to a situation's rules: force only on a test of body or arms (act.yaml force_checks), the work of a
    hand for skill and for force claimed on anything else; (f604) on an act rolled on talk (act.yaml talk_checks), words."""
    if ch.because in ("force", "skill") and check in A["talk_checks"]:
        return "words"
    if ch.because == "force":
        return "force" if check in A["force_checks"] else "work"
    return "work" if ch.because == "skill" else ch.because


def problems() -> list[str]:
    """(f594) act.yaml's shape: the kept rulings capped, the changes a ruling may carry, the failures to choose from."""
    bad = []
    k = A.get("kept") or {}
    for name, v in (("kept.per_character", k.get("per_character")), ("kept.days", k.get("days")), ("most_changes", A.get("most_changes"))):
        if not (isinstance(v, int) and not isinstance(v, bool) and v > 0):
            bad.append(f"act.yaml {name}: needs a whole number above 0")
    F = A.get("fails")
    if not (isinstance(F, dict) and F and all(isinstance(v, dict) and v.get("text") for v in F.values())):
        bad.append("act.yaml fails: needs each failure with its text")
    for k in ("success_minutes",):
        v = A.get(k)
        if not (isinstance(v, int) and not isinstance(v, bool) and v > 0):
            bad.append(f"act.yaml {k}: needs a whole number above 0")
    from engine import situation_parts
    words = set(situation_parts.S["rulings"]["changes"])
    if not (isinstance(A.get("outside_situation"), list) and set(A["outside_situation"]) <= words):
        bad.append("act.yaml outside_situation: needs a list of the situation ruling's words")
    P_ = A.get("pending") or {}
    for k in ("most", "tries", "minutes", "moment_minutes", "lapse_hours"):
        v = P_.get(k)
        if not (isinstance(v, int) and not isinstance(v, bool) and v > 0):
            bad.append(f"act.yaml pending.{k}: needs a whole number above 0")
    from engine import checks, ruling
    if not (isinstance(A.get("force_checks"), list) and A["force_checks"] and set(A["force_checks"]) <= set(checks.CHECKS) | set(ruling.ATTRS)):
        bad.append("act.yaml force_checks: a list of the checks and attributes force is tested on")
    talk = A.get("talk_checks")
    if not (isinstance(talk, list) and talk and set(talk) <= set(checks.CHECKS) | set(ruling.ATTRS)
            and not set(talk) & set(A.get("force_checks") or ())):
        bad.append("act.yaml talk_checks: a list of the checks talk is tested on, none of force_checks")
    hand = A.get("hand_checks")
    if not (isinstance(hand, list) and hand and set(hand) <= set(checks.CHECKS) | set(ruling.ATTRS) and not set(hand) & set(talk or ())):
        bad.append("act.yaml hand_checks: a list of the checks a hand's work is tested on, none of talk_checks")
    from engine import situation_parts
    B = A.get("beyond") or {}
    if not (isinstance(B, dict) and str(B.get("answer") or "").strip() and str(B.get("why") or "").strip()):
        bad.append("act.yaml beyond: needs an answer and a why")
    layers = {x.get("layer") for x in situation_parts.S["rulings"]["changes"].values()}
    O = A.get("one_a_person")
    if not (isinstance(O, list) and O and all(isinstance(g, list) and g and set(g) <= layers for g in O)
            and len([l for g in O for l in g]) == len({l for g in O for l in g})):
        bad.append(f"act.yaml one_a_person: groups of layers from situation_parts.yaml rulings ({', '.join(sorted(layers))}), none twice")
    G = A.get("grammar") or {}
    if set(G) != {"why", "answer", "works", "instead", "instead_items", "label", "need_name", "need_what", "need_where", "needs", "uses",
                  "requires"} or not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in G.values()):
        bad.append("act.yaml grammar: why, answer, works, instead, instead_items, label, need_name, need_what, need_where, needs, uses and "
                   "requires, each a whole number above 0")
    if not (isinstance(A.get("filler"), list) and all(isinstance(x, str) and x for x in A["filler"])):
        bad.append("act.yaml filler: needs a list of words")
    return bad


# ---------- (f595) the act: ruled, checked, kept, resolved and told

def act(ws, actor_id: str, words: str, text: str) -> None:
    """The whole loop for an act outside combat: its targets, the kept ruling or the model's, the engine's check, the ruling kept, what
    the world must hold made, the roll, what changed written through the game's own writers, the deed, and the telling. A no is told in
    the world's words; with no ruling, the act waits for one (never rolled unruled)."""
    from engine import targets
    if actor_id != ws.acting:                        # (f595) one character a scene until multiplayer M1
        raise ValueError(f"an act is played for the scene's own character, not {actor_id}")
    T = targets.targets_for(ws, actor_id)
    r = kept(ws, actor_id, T, text)
    fresh = r is None
    if fresh:
        r = ask(ws, actor_id, T, words, text)
    if r is None:
        wait(ws, actor_id, words, text)                   # (f596) it waits for its ruling, never rolled unruled
        return
    decide(ws, actor_id, T, r, fresh, words, text)


def decide(ws, actor_id: str, T, r, fresh: bool, words: str, text: str, continuing: str = "") -> None:
    """A ruling in hand: checked, kept, and refused or made real. `continuing`: the attempt was told beginning before (f596); how it
    turned out is told as of then."""
    from engine import ruling
    own = words or text
    if continuing:
        words = f"{continuing} {words or text}"
    v = validate(ws, actor_id, T, r)
    if fresh:
        keep(ws, actor_id, T, text, r)
    else:
        use(ws, actor_id, text)
    if not v.ok:
        ruling.refuse(ws, {"answer": v.answer, "instead": v.instead, "why": v.why}, words, text)
        return
    made = make_needs(ws, v.ruling)
    resolve(ws, actor_id, T, v, words, text, made, own)


# ---------- (f596) an act waiting for its ruling

def wait(ws, actor_id: str, words: str, text: str) -> None:
    """The ruling could not be made: the act is kept for the character, its beginning told (never how it turns out), its time spent.
    The same act typed again waits once. Past `most` waiting, the oldest is let go and counted as a ruling that failed."""
    from engine import refusals, world_improv
    P_ = A["pending"]
    data = ws.store.load_act_pending()
    key, place = words_key(text), ws.player.location
    rows = [x for x in data.get(actor_id) or [] if not (words_key(x["text"]) == key and x["place"] == place)]   # typed again: one act
    rows.append({"words": words, "text": text, "place": place, "minute": int(ws.minutes), "tries": 0})
    for old in rows[:-int(P_["most"])]:
        refusals.note("ruling_failed", old["text"], "let go: newer acts were waiting", old["place"], ws.store.meta.turn)
    data[actor_id] = rows[-int(P_["most"]):]
    ws.store.save_act_pending(data)
    ws.advance(int(P_["minutes"]))
    ws.narrate(f"THE GAME HAS NOT DECIDED YET: the player begins what they attempt ({world_improv.what_of(words or text)}). Show only the "
               "attempt beginning, as it would be seen: never how it turns out, and nothing it would change.", text)


def waiting(ws, actor_id: str) -> list[dict]:
    return ws.store.load_act_pending().get(actor_id) or []


def take_up(ws, actor_id: str, text: str) -> None:
    """(f596) At the next input, before its line is read: the oldest act this character left waiting is ruled on, or lapses (they have
    left the place, or it has waited past lapse_hours), or after its tries is told as come to nothing and counted as a ruling that
    failed. One a line. `text` is the new line, never handed the narrator for the waiting act: the act's own words are."""
    from engine import targets, world_improv
    if actor_id != ws.acting:                        # one character a scene until multiplayer M1
        raise ValueError(f"an act is played for the scene's own character, not {actor_id}")
    P_ = A["pending"]
    data = ws.store.load_act_pending()
    rows = data.get(actor_id) or []
    if not rows:
        return
    row = rows[0]
    what = world_improv.what_of(row["words"] or row["text"])
    since = int(ws.minutes) - int(row.get("minute", ws.minutes))
    if row["place"] != ws.player.location or since > int(P_["lapse_hours"]) * 60:
        _end(ws, actor_id, data, row, "lapsed: " + ("the character left the place" if row["place"] != ws.player.location else "it waited too long"),
             f"THE GAME HAS DECIDED: what the player began earlier ({what}) was left unfinished; it came to nothing. Tell how it was left.")
        return
    T = targets.targets_for(ws, actor_id)
    r = ask(ws, actor_id, T, row["words"], row["text"])
    if r is None:
        missed(ws, actor_id)
        return
    data[actor_id] = rows[1:]
    ws.store.save_act_pending(data)
    when = "the attempt they began a moment ago," if since <= int(P_["moment_minutes"]) else "the attempt they began earlier,"
    decide(ws, actor_id, T, r, True, row["words"], row["text"], continuing=when)


def missed(ws, actor_id: str) -> None:
    """(f596) A try at the oldest waiting act did not stand (no ruling, or its operation failed for any reason): one of its tries spent,
    in an operation of its own; past them it is told as come to nothing and counted as a ruling that failed."""
    from engine import world_improv
    data = ws.store.load_act_pending()
    rows = data.get(actor_id) or []
    if not rows:
        return
    row = rows[0]
    row["tries"] = int(row.get("tries", 0)) + 1
    if row["tries"] >= int(A["pending"]["tries"]):
        what = world_improv.what_of(row["words"] or row["text"])
        _end(ws, actor_id, data, row, f"no ruling after {row['tries']} tries",
             f"THE GAME HAS DECIDED: what the player began ({what}) comes to nothing in the end: it peters out, unfinished, and nothing is "
             "changed by it. Tell how it ends.")
        return
    ws.store.save_act_pending(data)


def _end(ws, actor_id: str, data: dict, row: dict, why: str, telling: str) -> None:
    """A waiting act ended without a ruling: let go, counted as a ruling that failed, and told ending in its own words."""
    from engine import refusals
    data[actor_id] = [x for x in data.get(actor_id) or [] if x is not row]
    ws.store.save_act_pending(data)
    refusals.note("ruling_failed", row["text"], why, row["place"], ws.store.meta.turn)
    ws.narrate(telling, row["text"])


def make_needs(ws, r) -> list[str]:
    """What the world must hold for the act and does not yet (engine/ruling.py make_room), never made twice: a thing already lying
    here, or someone of that kind already here, is what was called for."""
    from engine import objects, ruling
    fresh = []
    for n in r.needs:
        if n.kind == "thing" and objects.find(objects.here(ws.store, ws.player.location, ws.minutes), n.name) is not None:
            continue
        if n.kind == "person" and any(getattr(p, "epithet", "") == objects.name_of(n.name) for p in ws.present):
            continue
        fresh.append(n)
    return ruling.make_room(ws, r.model_copy(update={"needs": fresh})) if fresh else []


def _said(T, ch) -> str:
    t = T.get(ch.target)
    name = (t.line.split(":")[0].split(" (")[0] if t else ch.target)
    return f"{name}: {ch.becomes.replace('_', ' ')}" + (f" {ch.state}" if ch.state else "")


def resolve(ws, actor_id: str, T, v: Checked, words: str, text: str, made: list[str], own: str = "") -> str:
    """The roll and what came of it. A plain yes needs no roll; a cost is rolled on the ruling's check and how hard it is. A strong
    success counts as such only when a real thing enables it (the owner, 2026-11-11); a partial success makes only what can be half
    made (a part's state, for less time). The narrator is told what changed and what the engine refused, never to show the latter.
    The act is a deed when anything was at stake, made or changed. Returns the degree."""
    from engine import checks, ruling, world_improv
    from engine.domain_events import Acted
    from ui import console
    r = v.ruling
    c = ws.player.character
    what = world_improv.what_of(words or text)
    rolled = not (r.sense == "yes" and not r.stakes.check)
    if not rolled:
        degree = "success"
    else:
        odds = ruling.odds(ws, "attempt", {"check": r.stakes.check, "hard": r.stakes.hard})
        degree, _ = checks.roll(odds, ws.rng, c=c)
    if degree == "strong success" and not v.enabled:
        degree = "success"
    worked = degree in ("success", "strong success", "partial")
    changes = list(r.changes) if worked else []
    refused = [(ch, why) for ch, why in v.dropped]
    if degree == "partial":
        half = [ch for ch in changes if ch.becomes == "state"]
        refused += [(ch, "it only half worked") for ch in changes if ch not in half]
        changes = half
    F = A["fails"].get(r.fail) or A["fails"][next(iter(A["fails"]))]
    no = {ch.becomes for ch, _ in refused} | {ch.state for ch, _ in refused if ch.state}
    landed = world_improv.land(ws, own or words or text, degree, no)   # (f603) what the retired path made true besides, kept
    if rolled or changes or made or landed:
        console.ledger(f"Attempt: {degree.replace('_', ' ')}")
        ws.notice(Acted(minute=ws.minutes, place=ws.player.location, what=world_improv.what_of(own or words or text), degree=degree, by=actor_id,
                        changes=tuple(ch.becomes for ch in changes), heat=0.0 if worked else float(F.get("heat", 0) or 0),
                        considered=tuple(t.ref for t in T.rows if t.kind == "situation")))
    seq = int((ws.store.load_world_state() or {}).get("seq") or 0)
    told = apply(ws, actor_id, T, changes, degree, seq, r.stakes.check) if changes else []
    room = (" THE WORLD NOW HOLDS (made for this, and real from now on; show it): " + "; ".join(made) + ".") if made else ""
    lasting = (" WHAT IS DIFFERENT NOW (real from now on; show it): " + " ".join(told + [x + "." for x in landed])) if told or landed else ""
    nots = (" WHAT DID NOT HAPPEN (the game refused it; never show it happening): " + "; ".join(_said(T, ch) for ch, _ in refused) + ".") \
        if refused and worked else ""
    comes = (r.works or "").strip().rstrip(" .!?")
    lack = ""
    if v.without:                                    # (f618) how it is done by one who lacks the power it would take
        W = ruling.C[v.without]
        lack = f" THEY DO IT WITHOUT {W['about'].upper()}: {W['without']['told']}. Show it done that way, never by that power."
    if degree in ("success", "strong success"):
        ws.advance(int(A["success_minutes"]))
        if comes:                                   # (f609) a success is what the ruling says it comes to, never what the words claim
            ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) WORKS" + (" cleanly and well" if degree == "strong success" else "")
                       + (", and this is what it comes to, short of what did not happen (below)" if nots else ", and this is what it comes to")
                       + f": {comes}. Show that, as it would be seen, and nothing beyond it"
                       + (", with what is different now." if (told or made or landed) else ". Nothing lasting is different.")
                       + " Nothing is gained that was not there, and no one is harmed." + lack + room + lasting + nots, text)
            return degree
        ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) WORKS" + (" cleanly and well" if degree == "strong success" else "")
                   + (". Show it done, as it would be seen, and what is different now." if (told or made or landed)
                      else ". Show it done, as it would be seen. Nothing lasting is different.")
                   + " Nothing is gained that was not there, and no one is harmed." + lack + room + lasting + nots, text)
        return degree
    if degree == "partial":
        ws.advance(int(A["partial"]["minutes"]))
        ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) half works: {A['partial']['text']}"
                   + (f"; it falls short of this, which is the most it could have come to: {comes}" if comes else "")
                   + ". Show it as it would be seen, the flaw in it plain. Nothing is gained that was not there." + lack + room + lasting + nots, text)
        return degree
    cost = fail(ws, actor_id, T, r, F)
    ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) FAILS: {F['text']}. Show the failure as it happens and what it "
               "costs them, and stop there; nothing it was meant to change has changed, no one gives them anything, and nobody speaks "
               "beyond a look or a word." + room + cost, text)
    return degree


def fail(ws, actor_id: str, T, r, F: dict) -> str:
    """What a failure costs (act.yaml fails): time, health, the thing relied on broken. Returns what the narrator is told of it."""
    from engine import objects, pools
    c = ws.player.character
    ws.advance(int(F.get("minutes", 0) or 0))
    out = ""
    if F.get("health_pct"):
        top = pools.maximum(c, "health")
        c.health = max(1.0, pools.current(c, "health") - top * float(F["health_pct"]) / 100)
        ws.store.save_player(ws.player)
    if F.get("breaks"):
        for u in r.uses:
            t = T.get(u)
            e = ws.store.load_entity(t.ref) if t is not None and t.kind == "object" else None
            if e is not None and e.state == "here":
                objects.change(ws.store, e, "broken", ws.minutes, "gave way")
                out = f" {e.name} breaks."
                break
    return out


def apply(ws, actor_id: str, T, changes, degree: str, seq: int = 0, check: str = "") -> list[str]:
    """Each checked change written through the game's own writers; returns what the narrator is told is different now."""
    from engine import entities, features, objects
    store = ws.store
    told: list[str] = []
    sits: dict[str, list] = {}
    for ch in changes:
        t = T.get(ch.target)
        if t is None:
            continue
        if t.code.startswith("s") and "." in t.code:
            sits.setdefault(t.code.split(".")[0], []).append(ch)
            continue
        if t.kind == "part":
            e = store.load_entity(t.ref)
            word = ch.state if ch.becomes == "state" else {"open": "opened", "closed": "barred"}.get(ch.state, "")
            said = features.change(ws, e, word, degree) if e is not None and word else ""
            if said:
                told.append(said)
        elif t.kind == "object":
            e = store.load_entity(t.ref)
            if e is None:
                continue
            if ch.becomes == "moved":
                to = T.get(ch.to)
                e.data["part"], e.data["touched"] = to.ref, int(ws.minutes)
                store.save_entity(e)
                told.append(f"{e.name} is at {to.line.split(':')[0]} now.")
            else:
                to = {"broken": "broken", "mended": "here", "found": "here", "hidden_here": "hidden", "destroyed": "destroyed"}[ch.becomes]
                if to != e.state and to in (entities.L["object"].get("moves") or {}).get(e.state, []):
                    objects.change(store, e, to, ws.minutes, "an act")
                    told.append(f"{e.name} is {'hidden away' if ch.becomes == 'hidden_here' else ch.becomes} now.")
        elif t.kind == "person":
            told += _person(ws, actor_id, t, ch)
    for scode, chs in sits.items():
        told += _situation(ws, actor_id, T, scode, chs, degree, seq, check)
    return [x for x in told if x]


def _person(ws, actor_id: str, t, ch) -> list[str]:
    """One outside a situation moved in what they believe, feel or will do toward the one who acted (as a situation's person is)."""
    from engine import circumstance, clock, memory, regard, situation_parts
    RU = situation_parts.S["rulings"]
    n = ws.npc_by_id(t.ref)                          # the scene's own copy, which it saves: never one it would save over
    if n is None:
        return []
    w, now, key = ch.becomes, int(ws.minutes), f"act:{t.ref}:{ws.minutes}:{ch.n}"
    if w in ("believes", "doubts"):
        memory.keep(n, situation_parts._pick(RU["beliefs"][w], key).format(name=situation_parts.char_name(ws, actor_id)),
                    day=clock.day(now), turn=-1, kind="told", subject=actor_id, source=actor_id, about=f"act:{t.ref}", minute=now)
    elif w in ("afraid", "angry", "grateful"):
        circumstance.set_mood(n, situation_parts._pick(RU["moods"][w], key), now, f"act:{actor_id}")
    else:
        regard.step(n, actor_id, int(RU["trust"]) * (1 if w == "warmer" else -1), "an act", about=f"act:{w}", minute=now)
    ws.store.save_npc(n)
    return [f"{n.label(actor_id)} is {w} now."]


def _situation(ws, actor_id: str, T, scode: str, chs, degree: str = "success", seq: int = 0, check: str = "") -> list[str]:
    """A situation's parts changed through its own writer (engine/situation_parts.py keep_changes)."""
    from engine import situation_parts
    state = ws.store.load_world_state() or {}
    th = next((x for x in state.get("threads", []) if x["id"] == T.get(scode).ref), None)
    if th is None:
        return []
    idx = lambda code: int(code.split(".")[1]) if code.startswith(scode + ".") else 0
    rows = [{"n": ch.n, "part": idx(ch.target), "who": idx(ch.who), "becomes": ch.becomes,
             "because": _because(ch, check), "hand": check in A["hand_checks"], "about": idx(ch.about),
             "needs": [m for m in ch.needs if m in {c.n for c in chs}]} for ch in chs]
    act_ = {"kind": "acted", "by": actor_id, "npc": "", "witnesses": sorted(n.id for n in ws.present), "place": ws.player.location,
            "coin": 0, "item": "", "count": 1, "degree": degree, "words_only": False, "seq": seq or None, "force_by_change": True}
    situation_parts.keep_changes(ws, state, th, act_, rows)
    from engine import events
    events.read_end(ws, state, th, "by what was done")      # (f598) whether it is over is the world's to say
    ws.store.save_world_state(state)
    out = []
    for r_ in rows:
        t = T.get(f"{scode}.{r_['part']}")
        if t is not None:
            out.append(f"{t.line.split(' (p')[0]} ({r_['becomes']})")
    return out
