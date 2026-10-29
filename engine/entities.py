"""(f392) The registry: who someone is, and what has become of them.

Two nights of play read by people who knew nothing of the game found the same thing again and again: nobody kept who someone was.
A companion was "she" in the fight and "he" in the frame around her words (four places kept gender, and the narrator was given none of
them); an elf became "the dwarf with the ginger beard"; a captive walked bound at the player's side for a thousand turns because
nothing could become of him; a man who had died yielded; a companion who fell was deleted from the save the moment she fell, so nobody
ever spoke of her again.

identity() is the one answer to "who is this": name, pronoun, people, for the player, Maren, a hire, a beast at the player's side, a
captive, a townsperson. cast_lines() is the one way a writer is told who is who. Townsfolk keep their own records (npc/models.py), read
through the same identity; what is kept here, in the save's `entities` table, is what has no record of its own or loses it: a companion
who fell, a captive. Each has a lifecycle (data/rules/lifecycles.yaml): a state, the moves allowed out of it, a history; every move is
published on the event bus (StateChanged)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from core.models import Entity

ROOT = Path(__file__).resolve().parent.parent
L = yaml.safe_load((ROOT / "data" / "rules" / "lifecycles.yaml").read_text(encoding="utf-8"))
GENDER = {"male": "he", "female": "she"}
HISTORY_KEPT = 12


@dataclass(frozen=True)
class Identity:
    ref: str
    name: str
    pronoun: str                # he | she | they | it
    people: str                 # the people's word ("elf", "half-elf"), or the creature for a beast ("grey wolf")
    kind: str                   # player | maren | hire | companion | captive | npc
    note: str = ""              # what they are to the player, in a few words

    def tag(self) -> str:
        """'she, elf': what a writer must not get wrong."""
        return ", ".join(x for x in (self.pronoun, self.people) if x)


def people_word(world, pid: str) -> str:
    if not pid:
        return ""
    if pid in world.peoples:
        return world.peoples[pid].name.lower()
    if pid in world.bestiary:
        return world.bestiary[pid].name.lower()
    return pid.replace("_", "-")


def identity(ws, ref: str) -> Identity | None:
    """Who this is, by the id the scene knows them by: 'player', 'maren', 'hire:<id>', 'companion:<id>', or a person's id."""
    from engine import party, truth
    world = ws.world
    if ref == "player":
        c = ws.player.character
        return Identity("player", c.name, truth.player_pronoun(c), people_word(world, getattr(c, "people", "")), "player", "the player")
    if ref == "maren":
        from engine import mentor
        return Identity("maren", mentor.NAME, "she", "human", "maren", "the mentor travelling with the player")
    if ref.startswith("hire:"):
        m = ws.hire_by_id(ref) if hasattr(ws, "hire_by_id") else None
        if m is not None:
            return Identity(ref, m["name"], party.pronoun_of(m, ws.store.meta.seed, ws.player.party_used), people_word(world, m.get("people", "")),
                            "hire", f"a hired {m.get('role', 'companion')}, travelling with the player")
    if ref.startswith("companion:"):
        cid = ref.split(":", 1)[1]
        comp = next((c for c in getattr(ws.player.character, "companions", None) or [] if c.id == cid), None)
        if comp is not None:
            return Identity(ref, comp.name, party.companion_pronoun(comp), people_word(world, comp.creature), "companion", "the player's own beast")
    e = ws.store.load_entity(ref)
    if e is not None:
        return Identity(ref, e.name, e.pronoun, people_word(world, e.people), e.kind, e.data.get("note", ""))
    npc = next((n for n in getattr(ws, "present", []) if n.id == ref), None)
    if npc is None and ws.store.npc_exists(ref):
        npc = ws.store.load_npc(ref)
    if npc is not None:
        held = ws.store.load_entity(f"captive:{npc.id}")
        return Identity(ref, npc.name or npc.label(), held.pronoun if held else GENDER.get(npc.gender, "they"), people_word(world, npc.people),
                        "captive" if held else "npc", "the player's captive" if held else "")
    return None


def cast_lines(ws) -> list[str]:
    """Everyone travelling with the player, and who they are: 'Thavathiel: he, elf - a hired mage, travelling with the player'. Given to
    every writer, so nobody is guessed at: these are the people a passage names without the scene describing them."""
    refs = []
    if any(m.get("story") == "maren" for m in ws.player.party) or (hasattr(ws, "mentor_with_you") and ws.mentor_with_you()):
        refs.append("maren")
    refs += [f"hire:{m['id']}" for m in ws.player.party if m.get("permanent") and not m.get("story") and m.get("name")]
    refs += [f"companion:{c.id}" for c in getattr(ws.player.character, "companions", None) or [] if c.active and c.name]
    refs += [e.links.get("npc", "") for e in ws.store.find_entities(kind="captive", state=tuple(L["captive"]["present_with_player"]))]
    out = []
    for r in refs:
        who = identity(ws, r) if r else None
        if who is not None:
            out.append(f"{who.name}: {who.tag()}" + (f" - {who.note}" if who.note else ""))
    return out


def who_is_who(ws, also=()) -> list[str]:
    """cast_lines() and, first, whoever else this writer must not get wrong (the one speaking, the one spoken to)."""
    out = []
    for r in also:
        who = identity(ws, r) if r else None
        if who is not None and who.kind not in ("hire", "companion", "maren", "captive"):
            out.append(f"{who.name}: {who.tag()}")
    return out + [x for x in cast_lines(ws) if x not in out]


WHO_HEAD = "WHO IS WHO (each one's pronoun and people: never write them otherwise)"


# ---------- words for the engine's own lines

WORDS = {"he": {"they": "he", "them": "him", "their": "his", "theirs": "his", "themselves": "himself"},
         "she": {"they": "she", "them": "her", "their": "her", "theirs": "hers", "themselves": "herself"},
         "it": {"they": "it", "them": "it", "their": "its", "theirs": "its", "themselves": "itself"}}
_AGREE = {"are": "is", "were": "was", "have": "has", "do": "does", "go": "goes", "aren't": "isn't", "weren't": "wasn't", "don't": "doesn't",
          "haven't": "hasn't", "'re": "'s", "'ve": "'s"}
_MODAL = {"can", "could", "will", "would", "shall", "should", "may", "might", "must", "used", "can't", "won't", "wouldn't", "couldn't",
          "shouldn't", "did", "didn't", "had", "hadn't", "'d", "'ll"}
_ADVERB = {"always", "never", "often", "sometimes", "still", "also", "only", "just", "rarely", "ever", "even", "once", "now", "already",
           "seldom", "usually", "really", "nearly", "almost", "quietly", "openly"}
_NOT_VERB = {"him", "her", "his", "hers", "himself", "herself", "it", "its", "itself", "and", "or", "but", "who", "that", "all", "both",
             "too", "is", "was", "has", "does", "goes", "the", "a", "an", "not"}


def _agree(verb: str) -> str:
    """'keep' -> 'keeps': the verb after 'they', as it goes after 'she' or 'he'."""
    v = verb.lower()
    if v in _AGREE:
        out = _AGREE[v]
    elif v in _MODAL or not v.isalpha():
        out = v
    elif re.search(r"[^aeiou]y$", v):
        out = v[:-1] + "ies"
    elif re.search(r"(s|sh|ch|x|z|o)$", v):
        out = v + "es"
    else:
        out = v + "s"
    return out.capitalize() if verb[:1].isupper() else out


def gendered(text: str, pronoun: str) -> str:
    """A line written about someone as 'they' ('turns their back on you, which they do with no one'), said with their own pronoun and
    the verbs to match ('turns his back on you, which he does with no one'). 'they' and anything not he, she or it is left as written.
    The engine's lines about one person were written with 'they' so they would fit anyone; read so, they invited the model to guess."""
    w = WORDS.get(pronoun)
    if not w or not text:
        return text

    def word(m: re.Match) -> str:
        t = m.group(0)
        new = w[t.lower()]
        return new.capitalize() if t[0].isupper() else new
    out = re.sub(r"\b(they|them|their|theirs|themselves)\b", word, text, flags=re.I)
    subj = w["they"]
    out = re.sub(rf"\b({subj})'(re|ve)\b", r"\1's", out, flags=re.I)              # they're, they've
    out = re.sub(rf"\b({subj})(\s+)((?:(?:{'|'.join(_ADVERB)})\s+)*)([A-Za-z']+)",
                 lambda m: m.group(1) + m.group(2) + m.group(3) + (m.group(4) if m.group(4).lower() in _NOT_VERB else _agree(m.group(4))),
                 out, flags=re.I)
    return out


# ---------- the registry and its lifecycles

def get(store, ref: str) -> Entity | None:
    return store.load_entity(ref)


def begin(store, kind: str, ref: str, name: str, minute: int, **fields) -> Entity:
    """A new entity in its kind's first state, published."""
    spec = L[kind]
    e = Entity(ref=ref, kind=kind, name=name, state=spec["start"], since=minute, **fields)
    e.history = [[minute, "", e.state, fields.get("data", {}).get("how", "")]]
    store.save_entity(e)
    _publish(e, "", e.state, minute, "")
    return e


def move(store, e: Entity, to: str, minute: int, why: str = "") -> Entity:
    """Move it to another state of its lifecycle: refused (ValueError) if its kind does not allow it. Kept, and published."""
    spec = L[e.kind]
    if to not in (spec.get("moves") or {}).get(e.state, []):
        raise ValueError(f"a {e.kind} cannot go from {e.state} to {to}")
    was = e.state
    e.state, e.since = to, minute
    if to in spec.get("final", []):
        e.owner, e.deadline = "", 0
    e.history = (e.history + [[minute, was, to, why]])[-HISTORY_KEPT:]
    store.save_entity(e)
    _publish(e, was, to, minute, why)
    return e


def final(e: Entity) -> bool:
    return e.state in L[e.kind].get("final", [])


def _publish(e: Entity, was: str, now: str, minute: int, why: str) -> None:
    from engine.domain_events import StateChanged, publish
    publish(StateChanged(minute=minute, ref=e.ref, name=e.name, of=e.kind, was=was, now=now, why=why))


def problems() -> list[str]:
    bad = []
    for kind, spec in L.items():
        states = set(spec.get("states") or [])
        if spec.get("start") not in states:
            bad.append(f"lifecycles.yaml {kind}: start '{spec.get('start')}' is not one of its states")
        for a, tos in (spec.get("moves") or {}).items():
            for b in [a] + list(tos):
                if b not in states:
                    bad.append(f"lifecycles.yaml {kind}: '{b}' in moves is not one of its states")
        for f in spec.get("final") or []:
            if f not in states:
                bad.append(f"lifecycles.yaml {kind}: final '{f}' is not one of its states")
            if (spec.get("moves") or {}).get(f):
                bad.append(f"lifecycles.yaml {kind}: '{f}' is final, so nothing moves on from it")
    return bad
