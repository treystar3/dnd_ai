"""Audiences (f320): a place can keep some of its people behind a door that does not open for everyone.

A place in places.yaml may say `audience: {keeper: <role>, sees: [<roles>]}`: the people of those roles are not met there unless the
player has been admitted, and the keeper is who decides. The game decides (data/rules/towns.yaml audience) - the town's regard for the
player, their standing with the nobility, or a summons from behind the door - and the keeper voices the decision in their own words.
Admitted, the player has a while (minutes) in which the gated people stand in the scene like anyone else; the truth layer, the narrator
and the interpreter see them only then. A summons from a gated person (engine/matters.py door six) is carried out by a messenger and
opens the door for the day."""
from __future__ import annotations

from pathlib import Path

import yaml

from ui import console
from engine.names import cap_first                      # (f422) a capital first letter, the rest as written

ROOT = Path(__file__).resolve().parent.parent
A = yaml.safe_load((ROOT / "data" / "rules" / "towns.yaml").read_text(encoding="utf-8")).get("audience", {})


def gate(world, place_id: str) -> dict | None:
    p = world.places.get(place_id)
    return (p.audience or None) if p else None


def gated_roles(world, place_id: str) -> set[str]:
    g = gate(world, place_id)
    return set(g.get("sees", [])) if g else set()


def is_gated(world, npc) -> bool:
    return npc.role in gated_roles(world, npc.location)


def is_keeper(world, npc) -> bool:
    g = gate(world, npc.location)
    return bool(g) and npc.role == g.get("keeper")


def admitted(ws, place_id: str) -> bool:
    return ws.player.audiences.get(place_id, -1) > ws.minutes


def visible(ws, npc) -> bool:
    """Whether this person is met where they are: anyone not behind a door, and the gated once the player has been admitted."""
    return not is_gated(ws.world, npc) or admitted(ws, npc.location)


def asks_audience(text: str) -> bool:
    """Whether the player's words ask to be let through to whoever is behind the door (by meaning, engine/relevance)."""
    from engine import relevance
    return bool(relevance.pick(text, [A.get("asks", "I ask to see the king; an audience with the queen; let me through to the throne room; I want to speak to the crown")], 1))


def decide(ws, place_id: str) -> tuple[bool, str]:
    """Whether the door opens for the player now, and why - in the keeper's terms."""
    from engine import pulse, standing, clock
    g = gate(ws.world, place_id) or {}
    town = pulse.town_of(ws.world, place_id)
    rep = ws.player.reputation.get(town, 0)
    need = g.get("reputation", A.get("reputation", 25))
    if admitted(ws, place_id):
        return True, "they were admitted already"
    if rep >= need:
        return True, f"the town knows their name ({ws.reputation_words(town)})"
    nob = standing.value(ws.player, town, "nobility", clock.day(ws.minutes))
    if nob >= A.get("standing_nobility", 10):
        return True, f"the great houses speak well of them ({standing.word(nob)})"
    if rep <= -A.get("refuse_below", 10):
        return False, f"the town thinks ill of them ({ws.reputation_words(town)})"
    return False, "they are nobody the city has heard of yet; a name is earned in the streets before it is heard behind this door"


def grant(ws, place_id: str, why: str, minutes: int | None = None) -> None:
    ws.player.audiences[place_id] = ws.minutes + (minutes or A.get("minutes", 120))
    ws.store.save_player(ws.player)
    if ws.player.location == place_id:
        ws.refresh_present()
    console.debug(f"audience at {place_id}: granted - {why}")


def keeper_lines(ws, npc, speech: str) -> list[str]:
    """For the keeper's prompt: that they keep the door, and - when the player asks - what the game has decided."""
    if not is_keeper(ws.world, npc):
        return []
    g = gate(ws.world, npc.location)
    who = ", ".join(r.replace("_", " ") for r in g.get("sees", []))
    out = [f"YOU KEEP THE DOOR here: nobody sees the {who} unless you admit them, and you decide nothing yourself - the game does, below. "
           "You may say who gets seen and who does not, in your own words, without explaining the rules."]
    if asks_audience(speech):
        ok, why = decide(ws, npc.location)
        if ok:
            grant(ws, npc.location, why)
            out.append(f"THEY HAVE JUST ASKED TO BE SEEN, AND THE ANSWER IS YES: {why}. Say so, and show them through - the doors open for them now.")
        else:
            out.append(f"THEY HAVE JUST ASKED TO BE SEEN, AND THE ANSWER IS NO: {why}. Say so, plainly and without apology; you have said it to better than them.")
    return out


def gated_lines(ws, npc) -> list[str]:
    """For a gated person's prompt: the terms of the audience."""
    if not is_gated(ws.world, npc):
        return []
    left = ws.player.audiences.get(npc.location, 0) - ws.minutes
    return [f"AUDIENCE: the player has been admitted to see you, and has a short while ({max(1, left // 10) * 10} minutes at most). The keeper of the door "
            "stands by. You are not obliged to them, and you do not explain yourself; you hear them out, or you do not."]


def absent_line(ws, npc) -> str:
    """When the player tries to speak to someone behind the door without being admitted."""
    g = gate(ws.world, npc.location) or {}
    keeper = g.get("keeper", "the keeper").replace("_", " ")
    return f"{cap_first(npc.label())} is not seen like that. The {keeper} keeps the door; ask there, or be sent for."


def summon(ws, npc, th: dict) -> bool:
    """A gated person sends for the player (matters, door six): a messenger finds them and the door is open for the day."""
    if not is_gated(ws.world, npc):
        return False
    g = gate(ws.world, npc.location) or {}
    place = ws.world.places[npc.location]
    grant(ws, npc.location, f"sent for by {npc.name}", A.get("summons_minutes", 1440))
    ws.weight_hint = "rich"
    ws.narrate(f"A messenger from {place.name} (one of the {g.get('keeper', 'keeper').replace('_', ' ')}'s people, or a guard in the crown's colours) finds the player "
               f"and tells them, with no more than that, that {npc.label()} will see them at {place.name}, today. Show the messenger arriving and going; "
               "the player decides whether to go.")
    console.debug(f"audience: {npc.name} sends for the player - {th['title']}")
    return True
