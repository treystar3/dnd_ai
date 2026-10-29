"""(f395) The dungeon master's ruling (GOAL.md; BUILD_PLAN.md: RULE, MAKE ROOM, STAKES, SAY NO).

A good dungeon master listens to what a player tries and rules on it: does it make sense here, for this character, in this world? What
must exist for it? What does it cost? When it makes sense and the world does not hold it yet, the world grows to hold it; when it does
not, the world says no in its own words, and nothing is made or broken. "Investigate further into the cave" is met with more cave; "I
grow wings and fly away" is not.

The model rules on sense: it is the dungeon master's imagination and judgement. The engine is the rulebook and memory, and may refuse a
yes on four grounds only:
  means        a yes that needs a capability the character lacks (data/rules/capabilities.yaml) is a no: no wings without something
               that grants flight, whatever the model says;
  consistency  nothing made may contradict what is established (a part of the place that is gone, a person who is dead);
  kind         every addition fits a template: a kind of part, a role; the engine writes every number;
  budget       the world grows outward from the player at a measured pace (engine/features.py budgets; people appearing, per place
               and day).
It asks only past the fast path: an improvised act (the interpreter's `other`). Ordinary play never waits on it."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml

from ui import console

ROOT = Path(__file__).resolve().parent.parent
C = yaml.safe_load((ROOT / "data" / "rules" / "capabilities.yaml").read_text(encoding="utf-8"))
ATTRS = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
HARD = {"easy": 20, "fair": 0, "hard": -20, "": 0}
APPEAR_PER_DAY = 2

SYSTEM = """You are the dungeon master of a fantasy role-playing game. A player has said what their character tries. You rule on it the
way a good dungeon master does at the table: if it makes sense here, for this character, in this world, the world makes room for it; if
not, it does not happen.

Rule with:
  sense:    "yes"  - it makes sense and they can simply do it (light a torch, walk on, call out, look closely).
            "cost" - it makes sense, but it takes time, effort or skill, or carries a risk (climbing, digging, swimming, sneaking).
            "no"   - it does not make sense in this world or for this character: impossible for anyone (summoning a dragon from
                     nothing, conjuring gold, making the sun set), or it needs a power they do not have.
  why:      one short line, in the world's terms.
  needs:    what the world must hold for it to happen that is NOT already listed under PARTS OF THIS PLACE or PEOPLE HERE: a part of the
            place (kind "feature": a ledge, a tunnel, a pool), a person (kind "person", with a role from ROLES when one fits), a
            thing (kind "thing": a loose rock, a rope left behind), or a way (kind "way": a passage onward). Only what it cannot happen
            without; at most two; nothing already listed; never treasure, magic items or creatures to fight - the game decides those.
            Each: name (short, "the high ledge"), what (one sentence of what it is), where (where it is from the player).
  requires: the names from CAPABILITIES the attempt needs, whether or not the character has them. Most attempts need none.
  stakes:   check - one of CHECKS, or an attribute, when chance decides it; hard - easy, fair or hard. Leave empty for a plain yes.
  changes:  what the attempt, if it works, makes lastingly different about a part of the place (one listed, or one under needs): part
            (its name; empty for where the player stands) and becomes (one of BECOMES): a tunnel blocked, a chamber lit, a way cleared.
            Most attempts change nothing that lasts; leave it empty then.
  answer:   for a no only: what happens instead, one or two sentences of the world, second person, as it would be seen.
  instead:  for a no only: one or two things they could try that would make sense.
Respond only with JSON matching the schema."""


def request(ws, words: str, text: str) -> str:
    from engine import features, inventory
    c = ws.player.character
    place = ws.place
    parts = features.lines(ws) or ["(none known)"]
    people = [f"{n.label()} ({n.role.replace('_', ' ')})" for n in ws.present][:8] or ["no one"]
    gear = ", ".join(i.name for i in c.equipment.values())[:200] or "nothing"
    pack = ", ".join(inventory.label(i) for i in c.inventory[:12]) or "nothing"
    abilities = ", ".join(a.name for a in c.actives[:12]) or "none"
    caps = "\n".join(f"  {k}: {v['about']}" for k, v in C.items())
    have = ", ".join(sorted(means_of(ws))) or "none"
    from engine import checks
    last = ws.recent_narration[-1] if ws.recent_narration else "(none)"
    return (f"PLACE: {place.name} ({place.type}{', ' + place.biome if place.biome else ''}{', dangerous' if place.danger else ''})\n"
            f"PARTS OF THIS PLACE:\n" + "\n".join(f"  - {p}" for p in parts) + "\n"
            f"PEOPLE HERE: {', '.join(people)}\n"
            f"THE CHARACTER: level {c.level} {c.custom_class or c.archetype.value}; carries {gear}; in the pack {pack}; abilities {abilities}\n"
            f"WHAT THEY CAN DO BEYOND THE ORDINARY: {have}\n"
            f"CAPABILITIES:\n{caps}\n"
            f"CHECKS: {', '.join(sorted(checks.CHECKS))}, or an attribute ({', '.join(ATTRS)})\n"
            f"BECOMES: {', '.join(features.F['becomes'])}\n"
            f"ROLES: {', '.join(sorted(ws.world.roles))}\n"
            f"THE LAST PASSAGE: {last}\n\n"
            f"THE PLAYER TRIES: {words}\nTHEIR WORDS: \"{text}\"")


def means_of(ws) -> set[str]:
    """What the character can do beyond the ordinary: the story's and items' gifts, their abilities' field uses, their people."""
    c = ws.player.character
    have = set(getattr(c, "capabilities", []) or [])
    fields = {getattr(a, "field_use", "") for a in c.actives}
    effects = {getattr(a.effect, "value", str(a.effect)) for a in c.actives}
    element = ((getattr(c, "look", None) or {}).get("look") or {}).get("element", "")
    for cap, spec in C.items():
        g = spec.get("grants") or {}
        if fields & set(g.get("field", [])) or effects & set(g.get("ability_effect", [])) \
                or (getattr(c, "people", "") in g.get("people", [])) or (element and element in g.get("look_element", [])):
            have.add(cap)
    return have


def ask(ws, words: str, text: str):
    """The model's ruling, or None when it cannot give one (the act is then resolved as an improvisation, as before)."""
    from engine import checks, features
    from llm.contracts import Ruling
    from llm.gateway import LLMError, generate
    try:
        return generate("ruling", SYSTEM, request(ws, words, text), Ruling, temperature=0.3, max_tokens=500,
                        validation_context={"capabilities": list(C), "checks": sorted(checks.CHECKS) + list(ATTRS), "roles": sorted(ws.world.roles),
                                            "becomes": list(features.F["becomes"])})
    except LLMError as e:
        console.debug(f"ruling: none ({e})")
        return None


def verdict(ws, r) -> dict:
    """The engine's checks on a ruling: {ok, answer, instead, why}. A no from the model stands; a yes may be refused on the engine's
    grounds only."""
    if r.sense == "no":
        return {"ok": False, "answer": r.answer, "instead": r.instead, "why": r.why or "it does not make sense here"}
    missing = [cap for cap in r.requires if cap in C and cap not in means_of(ws)]
    if missing:
        return {"ok": False, "answer": C[missing[0]]["lacking"], "instead": r.instead, "why": f"needs {missing[0]}, which they do not have"}
    from engine import features
    for n in r.needs:
        if n.kind in ("feature", "way"):
            e = features.find(ws, n.name)
            name = "the " + n.name.lower().removeprefix("the ").strip()
            gone = None if e is not None else next((x for x in ws.store.find_entities(kind="feature", place=ws.player.location)
                                                     if x.state == "gone" and x.name.lower() == name), None)
            if gone is not None:                       # a part that fell in or was lost is not called back by asking for it
                return {"ok": False, "answer": f"{gone.name[0].upper() + gone.name[1:]} is gone.", "instead": r.instead, "why": "it is gone"}
            if e is None and not features.room(ws, ws.player.location):
                return {"ok": False, "answer": f"There is no {n.name.removeprefix('the ')} here, and nowhere it could be.", "instead": r.instead,
                        "why": "the place holds all it can"}
        if n.kind == "person":
            dead = [x for x in ws.store.npc_rows() if x.name and n.name and x.name.lower() in n.name.lower() and x.gone]
            if dead:
                return {"ok": False, "answer": f"{dead[0].name} is gone from the world.", "instead": r.instead, "why": "they are gone"}
            if appeared_today(ws) >= APPEAR_PER_DAY:
                return {"ok": False, "answer": "Nobody comes.", "instead": r.instead, "why": "no more people appear here today"}
    for ch in r.changes:                               # a change to a part this place does not have, and that is not being made, is no change
        if ch.part and features.find(ws, ch.part) is None and not any(features.find(ws, n.name) is None and _same(n.name, ch.part) for n in r.needs):
            ch.part = "-"
    return {"ok": True, "answer": "", "instead": [], "why": r.why}


def _same(a: str, b: str) -> bool:
    norm = lambda s: re.sub(r"^(the|a|an)\s+", "", (s or "").strip().lower())
    return norm(a) == norm(b)


def change_parts(ws, ruled: dict | None, degree: str) -> list[str]:
    """(f395) What the attempt made different about the parts of this place, on a success or a partial (features.change). The lines
    told, as facts."""
    from engine import features
    out = []
    for part, becomes in (ruled or {}).get("changes") or []:
        if part == "-":
            continue
        e = features.find(ws, part) if part else features.spot_of(ws)
        said = features.change(ws, e, becomes, degree)
        if said:
            out.append(said)
    return out


def appeared_today(ws) -> int:
    """People who appeared for an attempt at this place today (the pace: a place does not fill with whoever is called for)."""
    from engine import clock
    return len((ws.__dict__.get("_appeared") or {}).get((ws.player.location, clock.day(ws.minutes)), []))


def make_room(ws, r) -> list[str]:
    """What the world now holds that it did not, made for the attempt: parts of the place (kept, linked to where the player stands), a
    person (made by the engine: name, people, gender; the model's words only say what they are), a thing (a mark on the place)."""
    from engine import features, ledger
    out = []
    for n in r.needs:
        if n.kind in ("feature", "way"):
            if features.find(ws, n.name) is not None:
                continue
            named = features.named_part(n.name) or features.named_part(f"the {n.name.removeprefix('the ')}")
            kind = named[1] if named else ("tunnel" if n.kind == "way" else features.kinds_here(ws.place)[0])
            name = named[0] if named else ("the " + n.name.removeprefix("the ").strip())
            e = features.adopt(ws, ws.player.location, name, kind, "ruled")
            if e is not None:
                if n.what:
                    e.data["what"] = n.what.strip()
                    ws.store.save_entity(e)
                out.append(f"{e.name}: {e.data.get('what', '')}")
        elif n.kind == "person":
            npc = appear(ws, n)
            if npc is not None:
                out.append(f"{npc.label()} ({npc.role.replace('_', ' ')}): {npc.description}")
        elif n.kind == "thing":
            ws.add_mark(f"{n.name}: {n.what}".strip(": "))
            ledger.add("made", ref=f"thing:{n.name}", name=n.name, how="ruled", say=f"{n.name} is here: {n.what}")
            out.append(f"{n.name}: {n.what}")
    return out


def appear(ws, n):
    """(f395) Someone the attempt calls for, made a real person of this place: the engine draws their name, people and gender (as for
    any townsperson); the ruling's words say only what they are. Kept, present at once, and counted per place and day."""
    from engine import clock, ledger
    from npc import life, names
    from npc.models import NPC
    from npc.traits import assign_traits, npc_rng
    pid = ws.player.location
    rng = random.Random(f"{ws.store.meta.seed}:appear:{pid}:{ws.minutes}:{n.name}")
    roles = ws.world.roles
    role = n.role if n.role in roles else next((r for r in roles if r in f"{n.name} {n.what}".lower().replace(" ", "_")), "wanderer")
    peoples = ws.world.peoples_at(pid) or {"human": 1}
    people = rng.choices(list(peoples), weights=list(peoples.values()))[0]
    name, gender = names.pick(people, ws.store.npc_names(), rng)
    label = re.sub(r"^(the|a|an)\s+", "", n.name.strip().lower()) or role.replace("_", " ")
    npc = NPC(id=life._unique_id(ws.store, name), name=name, gender=gender, people=people, role=role, location=pid,
              epithet=f"the {label}", description=(n.what or roles[role].description).strip(), activity="here, as you called for")
    if ws.catalog:
        assign_traits(npc, ws.catalog, npc_rng(ws.store.meta.seed, npc.id))
    life.inner_life(npc, ws.store, ws.world)
    ws.store.save_npc(npc)
    st = ws.store.load_place(pid)
    st.residents.append(npc.id)
    ws.store.save_place(st)
    ws.residents = ws.residents + [npc]
    ws.present = ws.present + [npc]
    ws.__dict__.setdefault("_appeared", {}).setdefault((pid, clock.day(ws.minutes)), []).append(npc.id)
    ledger.add("made", ref=f"person:{npc.id}", name=npc.label(), how="ruled", say=f"{npc.label()} is here now: {npc.description}")
    return npc


def refuse(ws, v: dict, words: str, text: str) -> None:
    """No, in the world's own words: nothing made, nothing broken, a moment spent, and what could be tried instead."""
    from engine import ledger, refusals, world_improv
    ws.advance(1)
    ledger.add("refused", say=f"What the player tries does not happen: {v['answer']}")
    refusals.note("refused", text, v["why"], ws.player.location, ws.store.meta.turn)
    instead = f" They could instead: {'; '.join(v['instead'])}." if v.get("instead") else ""
    ws.narrate(f"THE GAME HAS DECIDED: what the player tries ({world_improv.what_of(words or text)}) does not happen. Show it as it would be "
               f"seen: {v['answer']} Nothing is made, nothing breaks, and nobody makes much of it.{instead} Let the way forward be plain "
               "without telling them what to do.", text)


def run(ws, words: str, text: str) -> None:
    """The whole loop for an improvised act: rule, check, make room, set the stakes, resolve; or say no."""
    from engine import world_improv
    r = ask(ws, words, text)
    if r is None:
        world_improv.resolve(ws, words, text)
        return
    v = verdict(ws, r)
    if not v["ok"]:
        refuse(ws, v, words, text)
        return
    made = make_room(ws, r)
    world_improv.resolve(ws, words, text, ruled={"sense": r.sense, "check": r.stakes.check, "hard": r.stakes.hard, "made": made,
                                                 "changes": [(ch.part, ch.becomes) for ch in r.changes]})


def odds(ws, effect: str, ruled: dict) -> float:
    """The chance an attempt succeeds, from the rules: the ruling's check (a skill, or an attribute), or the act's own attribute, made
    easier or harder by how hard the ruling says it is."""
    from engine import checks, world_improv
    c = ws.player.character
    check = ruled.get("check") or ""
    if check in checks.CHECKS:
        base, _ = checks.chance(c, check, ws.check_triggers(check, False))
    elif check in ATTRS:
        R = checks.RULES
        base = world_improv.W["base_odds"] + (getattr(c.attributes, check) - R["attribute_center"]) * R["attribute_weight"]
    else:
        base = world_improv.odds_for(c, effect)
    return max(world_improv.W["min"], min(world_improv.W["max"], base + HARD.get(ruled.get("hard") or "", 0)))


def problems() -> list[str]:
    bad = []
    for k, spec in C.items():
        if not spec.get("about") or not spec.get("lacking"):
            bad.append(f"capabilities.yaml {k}: needs about and lacking")
    return bad
