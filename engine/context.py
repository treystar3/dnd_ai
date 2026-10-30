"""What goes into a character's prompt for one scene.

Whatever is in a prompt, a model wants to talk about. So everything the game knows about a hire is a tagged record, and each scene says
which records it may carry:

  core      who they are and how they speak: always there.
  trait     a habit, a leaning, a known weakness.
  detail    a small personal fact, written once at hire.
  canon     something they have said about themselves in play; it is now true.
  belief    something they have said about the world; true to them, not necessarily so.
  concern   a background matter (a promotion waiting, what drives them). The engine owns these: each has a cooldown once raised, and comes
            up unasked only when the scene allows it and the cooldown has run out.

A scene offers the records close in meaning to what was said or what brought the talk up, and now and then one thing simply on their mind.
A pressing scene (a wound, a hard fight, a death) offers nothing unasked: the moment is the subject."""
from __future__ import annotations

import random

import config

# How many records each kind of scene carries. Every record comes in only because it is close in meaning to the moment: what the player
# said, or what brought the talk up. Nothing comes in at random - what anyone brings up unasked is decided in one place, the banter hook
# (scenes/banter_actions.py banter_hook), so the scene builder never adds a second, competing topic.
SCENES = {
    "talk":     {"k": 2},        # the player is talking to them: a question gets an answer, not their agenda
    "ease":     {"k": 2},        # banter when nothing presses
    "about":    {"k": 2},        # banter brought up by something of theirs (it is in the hook)
    "pressing": {"k": 1},        # a wound, a hard fight, a loss
    "full":     {},              # writing about them (a summary): everything
}
PRESSING_HOOKS = {"hurt", "carried", "fallen", "lost_fight", "hard_fight", "warned"}
GRAVE_HOOKS = {"hurt", "carried", "fallen"}        # someone badly hurt, carried out, or dead: nothing else competes with it
COOLDOWN = {"promotion": 2 * 1440, "motive": 1440}                    # game minutes before a raised concern may come up unasked again


def scene_for_hook(hook_kind: str) -> str:
    if hook_kind in PRESSING_HOOKS:
        return "pressing"
    if hook_kind in ("promotion", "personal", "motive", "shared", "remembered"):
        return "about"
    return "ease"


def concerns_of(member: dict, motives: dict) -> list[dict]:
    """The background matters on this hire's mind, from the game's state."""
    from engine import party as rules, quirks
    out = []
    if member.get("capped") and rules.next_rank(member.get("rank") or ""):
        out.append({"kind": "concern", "key": "promotion", "label": "your promotion and the guild's fee",
                    "anchor": "the guild, your rank, being promoted, the fee to raise you, getting ahead, your standing",
                    "text": "(private, background) You have gone as far as your rank allows. " + " ".join(quirks.Q["promotion_fact"].split())})
    mt = motives.get(member.get("motive", ""), "")
    if mt:
        out.append({"kind": "concern", "key": "motive", "label": "what drives you", "anchor": mt, "text": f"Privately, underneath it all, {mt}."})
    return out


def raised_at(member: dict, key: str) -> int | None:
    return (member.get("raised") or {}).get(key)


def due(member: dict, key: str, now: int) -> bool:
    last = raised_at(member, key)
    return last is None or now - last >= COOLDOWN.get(key, 1440)


def mark(member: dict, key: str, now: int) -> None:
    member.setdefault("raised", {})[key] = now


def note_spoken(member: dict, text: str, now: int, concerns: list[dict]) -> list[str]:
    """After they speak: any concern their words touched counts as raised. Returns the keys marked."""
    if not text or not concerns:
        return []
    from engine import relevance
    hit = []
    for c in concerns:
        if relevance.pick(text, [c["anchor"]], 1, floor=config.SIM_TOPIC):
            mark(member, c["key"], now)
            hit.append(c["key"])
    return hit


def select(member: dict, records: list[dict], scene: str, query: str | None, now: int, rng: random.Random) -> tuple[list[str], list[str]]:
    """The records this scene carries, and notes for the request (concerns raised lately, to leave alone unless asked)."""
    from engine import relevance
    if scene == "full" or query is None:
        return [r["text"] for r in records if r["kind"] != "core"], []
    spec = SCENES.get(scene, SCENES["talk"])
    chosen, notes = [], []
    for c in (r for r in records if r["kind"] == "concern"):
        if relevance.pick(query, [c["anchor"]], 1):
            chosen.append(c["text"])
        elif not due(member, c["key"], now):
            notes.append(c["label"])
    from engine import gravity                       # a heavier thing comes in only when the moment is clearly about it
    rest = [r for r in records if r["kind"] not in ("core", "concern")]
    near = relevance.ranked(query, [r["text"] for r in rest], [gravity.asked_margin(r.get("gravity", "light")) for r in rest])
    return chosen + near[:spec["k"]], notes


def raised_note(notes: list[str]) -> str:
    if not notes:
        return ""
    return ("ALREADY RAISED LATELY (you have said your piece on these; leave them alone unless they are asked about or the moment is about "
            "them): " + "; ".join(notes) + ".")
