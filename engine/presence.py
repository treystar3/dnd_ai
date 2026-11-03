"""(f485, Bundle D R8) Who is here to hear what is said: the characters in the scene, the hires present and awake, and Maren when she is
at the player's side. What is said aloud goes to every hearer (a hire's talk to the others travelling along; a name a character gives
to the townsfolk standing by); someone not here, downed or fallen hears nothing of it.

A bystander keeps what they heard said aloud as a heard row: the name a character gave (a claim, like any told name, and hearsay to
them: they heard it, they were not introduced), and a fact told that they did not know (the owner's decision of 2026-11-03, Q6)."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_V: dict | None = None


def _rules() -> dict:
    global _V
    if _V is None:
        _V = (yaml.safe_load((ROOT / "data" / "rules" / "voice.yaml").read_text(encoding="utf-8")) or {}).get("conversation") or {}
    return _V


def lines_cap() -> int:
    """The most lines a conversation's record keeps (voice.yaml conversation.lines)."""
    return int(_rules().get("lines", 60))


def hires(ws) -> list[dict]:
    """The hires here and awake: in the party, active, not fallen, and with the player (travelling along, or held where the player is)."""
    p = ws.player
    if getattr(p, "party_mode", "with") == "hold" and p.location != getattr(p, "party_hold_at", ""):
        return []
    return [m for m in p.party if m.get("active", True) and not m.get("fallen") and not m.get("down")]


def hearers(ws) -> list[str]:
    """Everyone who hears what is said here, by id: each character, each hire here and awake (hire:<id>), Maren at the player's side."""
    out = [c.id for c in ws.characters()]
    out += [f"hire:{m['id']}" for m in hires(ws) if m.get("id")]
    if getattr(ws, "mentor_with_you", lambda: False)():
        out.append("maren")
    return out


def bystanders(ws, speaker) -> list:
    """The townsfolk here who are not the one spoken with: they hear what is said aloud."""
    sid = getattr(speaker, "id", speaker)
    return [n for n in ws.present if n.id != sid and not getattr(n, "gone", "")]


def overheard_name(ws, speaker, who: str, name: str) -> list[str]:
    """A character gave their name aloud to `speaker`: each bystander who did not know it keeps it, heard (a heard row, from the
    character, about their name; their view of the character heard of the name, as hearsay). Returns the ids of those who kept it."""
    from engine import clock, memory, regard
    kept = []
    for n in bystanders(ws, speaker):
        seen = regard.of(n, who)
        if seen.knows_as or seen.name_known or (seen.heard_of or {}).get("as") == name:
            continue
        mine = regard.own(n, who)
        mine.heard_of = {"as": name, "by": "their own words, overheard", "day": clock.day(ws.minutes), "line": "", "source": who,
                         "certainty": memory.certainty("heard")}
        memory.keep(n, f"I heard {{them}} give their name as {name}.", day=clock.day(ws.minutes), turn=ws.store.meta.turn, kind="heard",
                    subject=who, source=who, about=f"name:{who}", minute=ws.minutes)
        ws.store.save_npc(n)
        kept.append(n.id)
    return kept


def overheard_facts(ws, speaker, facts: list) -> list[str]:
    """A fact said aloud by `speaker`: each bystander who did not know it keeps it, heard from the speaker. `facts`: world facts (id,
    text). Returns the bystanders who kept something."""
    from engine import circumstance, clock, memory
    kept = []
    for n in bystanders(ws, speaker):
        knew = {f.id for f in ws.world.facts_known_by(circumstance.groups(ws.world, n))}
        new = [f for f in facts if f.id not in knew]
        for f in new:
            memory.keep(n, f"I heard it said: {f.text}", day=clock.day(ws.minutes), turn=ws.store.meta.turn, kind="heard", subject="",
                        source=getattr(speaker, "id", ""), about=f"fact:{f.id}", minute=ws.minutes)
        if new:
            ws.store.save_npc(n)
            kept.append(n.id)
    return kept
