"""Contracts with a who and a why (f322). A posting on the guild board is not a template line: someone in the town asked for it, for a
reason that grows from the town's trouble and pressures, and when it is done something visible changes.

When a board is refreshed, each new posting of a kind someone would ask for (data/rules/guild.yaml issuers) is given an issuer - a person
of the hall's town, by role - and one model call writes, for the batch, the reason in the issuer's own words and the result that will
show when the job is done. A few postings (guild.yaml chain) are written with more behind them: a truth, a clue, a reveal and a way to
end it, which becomes a matter (engine/matters.py) the moment the job is paid, the way a hidden pulse contract does.

The issuer carries the reason as their concern while the job is open, so they bring it up; their prompt says they posted it; they remember
who took it and who did it. Done, the result lands: a lasting mark where the work was, the town's memory, the issuer's thanks, news, and
for a hunt or bounty a spell of lower danger there."""
from __future__ import annotations

import random
import uuid
from pathlib import Path

import yaml

from ui import console

ROOT = Path(__file__).resolve().parent.parent
G = yaml.safe_load((ROOT / "data" / "rules" / "guild.yaml").read_text(encoding="utf-8"))

STAKES_SYSTEM = """You give the postings on an adventurers' guild board their reasons. Each posting names the person who asked the guild to post
it (the ISSUER: their name and what they do) and the town they live in (its character, what is wrong underneath, how things stand). For
each posting write:
  reason: why they need it, in their own words, one or two plain sentences as they would say them to a stranger - a shepherd's words,
    a smith's, a captain's. Grown from the town's trouble where it fits; never grand, never a saying.
  result: what will be seen to be different when the job is done, one line, plain, in the third person ("the hill's flocks stop
    thinning"; "the road to the mill is used again").
  more: only for a posting marked MORE BEHIND IT - what the job turns out to be the edge of: truth (what is really going on, two
    sentences), reveal (what the one who finishes the job finds that the posting did not say, as a thing seen or found), clue (what one
    person of the town knows about it, in their words), and path {name, how, kind, target}: kind persuade - target a person id from
    PEOPLE whose mind settles it; kind find - target a place id from PLACES where the thing that settles it is; kind kill - target a
    creature id from CREATURES. For every other posting leave more empty.
Use only the people, places and creatures given. Respond only with JSON matching the schema."""


def issuer_for(store, world, town: str, kind: str, rng: random.Random, taken: set[str]) -> object | None:
    """Someone of the town who would ask for this kind of work: by the roles guild.yaml lists for it, the first role with a person; the
    guild's own people when nobody else fits. None when the town has nobody at all."""
    from engine import retrieval
    roles = G.get("issuers", {}).get(kind)
    if not roles:
        return None
    rows = [r for r in retrieval.people_in_town(store, world, town) if r.id not in taken]
    for role in roles:
        same = [r for r in rows if r.role == role]
        if same:
            return rng.choice(same)
    return None


def plan(ws, hall: str, new: list[dict]) -> None:
    """New postings get their issuers and, for a few, more behind them; then one model call writes the reasons and results. Done at
    the board's refresh (scenes/guild_actions.ensure_board)."""
    from engine import pulse, towns
    from llm.gateway import generate, LLMError
    from llm.contracts import BoardStakes
    town = pulse.town_of(ws.world, hall)
    rng = random.Random(f"{ws.store.meta.seed}:stakes:{hall}:{ws.minutes}")
    taken: set[str] = set()
    wanted = []
    for q in new:
        if q.get("issuer") not in (None, "guild") or q["kind"] not in G.get("issuers", {}):
            continue
        who = issuer_for(ws.store, ws.world, town, q["kind"], rng, taken)
        if who is None:
            continue
        taken.add(who.id)
        q["issuer"], q["issuer_name"], q["issuer_role"] = who.id, who.name, who.role.replace("_", " ")
        q["more_wanted"] = rng.random() < G.get("chain", {}).get("chance", {}).get(q["kind"], 0)
        wanted.append(q)
    if not wanted:
        return
    cond = towns.condition(ws.store, ws.world, hall, ws.minutes)
    lines = towns.resident_lines(ws.world, hall, cond)
    from engine import retrieval, events
    people = "; ".join(f"{r.id}: {r.name}, {r.role.replace('_', ' ')}" for r in retrieval.people_in_town(ws.store, ws.world, town)[:24])
    places = ", ".join(p.id for p in ws.world.places.values() if pulse.town_of(ws.world, p.id) == town or p.id in {q.get("place") for q in wanted})
    req = ("TOWN: " + ws.world.places[town].name + "\n" + "\n".join(lines) + "\n"
           + "PRESSURES: " + " ".join(p.description for p in ws.world.pressures.values() if p.place == town) + "\n"
           + f"PEOPLE (id: who): {people}\nPLACES: {places}\nCREATURES: {events.creature_menu(ws.world, hall)}\n\nPOSTINGS:\n"
           + "\n".join(f"  {q['id']}: [{q['letter']}] {q['title']} - ISSUER {q['issuer_name']}, {q['issuer_role']}"
                       + (" - MORE BEHIND IT" if q["more_wanted"] else "") for q in wanted))
    try:
        r = generate("board_stakes", STAKES_SYSTEM, req, BoardStakes, temperature=0.8, max_tokens=1600, retries=1,
                     validation_context={"ids": [q["id"] for q in wanted]})
    except LLMError as e:
        console.debug(f"stakes: the board keeps its plain postings this time ({e})")
        for q in wanted:
            q.pop("more_wanted", None)
        return
    by_id = {s.id: s for s in r.postings}
    for q in wanted:
        s = by_id.get(q["id"])
        more_wanted = q.pop("more_wanted", False)
        if not s:
            continue
        q["reason"] = " ".join(s.reason.split())
        q["result"] = " ".join(s.result.split())
        if more_wanted and s.more and s.more.truth and s.more.reveal:
            q["more"] = s.more.model_dump()
        _concern(ws.store, q)
        console.debug(f"stakes: {q['title']} - for {q['issuer_name']}: {q['reason'][:70]}" + (" (more behind it)" if q.get("more") else ""))


def _concern(store, q: dict) -> None:
    """The issuer carries the reason while the job is open: it is what is on their mind."""
    if not q.get("reason") or not store.npc_exists(q["issuer"]):
        return
    n = store.load_npc(q["issuer"])
    if n.gone:
        return
    n.concern, n.concern_from = q["reason"], f"quest:{q['id']}"
    store.save_npc(n)


def _release(store, npc_id: str, qid: str) -> None:
    if not store.npc_exists(npc_id):
        return
    n = store.load_npc(npc_id)
    if n.concern_from == f"quest:{qid}":
        n.concern, n.concern_from = "", ""
        store.save_npc(n)


def posted_by(ws, npc) -> list[dict]:
    """The postings this person asked for: on the hall's board, or in the player's hands."""
    out = [q for q in ws.player.quests if q.get("issuer") == npc.id]
    hall = ws.hall_here()
    if hall:
        out += [q for q in ws.store.load_place(hall).board if q.get("issuer") == npc.id]
    return out


def talk_lines(ws, npc) -> list[str]:
    """For the issuer's prompt: the job they put up, why, and where it stands."""
    out = []
    for q in posted_by(ws, npc):
        held = any(x["id"] == q["id"] for x in ws.player.quests)
        out.append(f"YOU ASKED THE GUILD TO POST A JOB: {q['title']}. Why: {q.get('reason') or 'you need it done'}. "
                   + ("The stranger in front of you has taken it on and is at it now." if held else "Nobody has taken it yet, as far as you know.")
                   + " You may speak of it as your own trouble; never as a 'quest' or a 'contract' with a number.")
    return out


def taken(ws, q: dict) -> None:
    """The issuer hears who took it on."""
    from engine import clock
    from npc.models import Memory
    if not q.get("issuer") or not ws.store.npc_exists(q["issuer"]):
        return
    n = ws.store.load_npc(q["issuer"])
    n.memories.append(Memory(day=clock.day(ws.minutes), turn=ws.store.meta.turn, text=f"The guild says the stranger has taken on my job: {q['title'].lower()}.", importance=2))
    ws.store.save_npc(n)


def done(ws, q: dict) -> None:
    """The job is paid: the result lands where it would be seen, the town remembers, the issuer is grateful, and if there was more
    behind it, the matter opens."""
    from engine import clock, pulse
    from npc.models import Memory
    name = ws.player.character.name
    town = pulse.town_of(ws.world, ws.player.location)                  # paid at the hall: the hall's town is the one that remembers
    if q.get("issuer") and ws.store.npc_exists(q["issuer"]):
        n = ws.store.load_npc(q["issuer"])
        n.memories.append(Memory(day=clock.day(ws.minutes), turn=ws.store.meta.turn,
                                 text=f"{name} did my job - {q['title'].lower()}." + (f" {q['result'][0].upper() + q['result'][1:]}." if q.get("result") else ""), importance=2))
        n.trust = min(100, n.trust + G.get("issuer_thanks_trust", 5))
        ws.store.save_npc(n)
        _release(ws.store, q["issuer"], q["id"])
    if q.get("result"):
        spot = q.get("place") if q.get("place") in ws.world.places else ws.player.location
        ps = ws.store.load_place(spot)
        ps.marks = (ps.marks + [f"{q['result']} (since {name} {q['title'].lower()})"])[-12:]
        ws.store.save_place(ps)
        if town in ws.world.places and not ws.world.places[town].danger:
            tp = ws.store.load_place(town)
            tp.memory = (tp.memory + [{"text": f"{q['title']}, for {q.get('issuer_name', 'the guild')}: done by {name}; {q['result']}", "minute": ws.minutes}])[-12:]
            ws.store.save_place(tp)
        state = ws.store.load_world_state()
        if state:
            pulse.add_news(state, f"{q['result'][0].upper() + q['result'][1:]} - {name}'s doing, they say.", town, ws.minutes, ["everyone"])
            if q["kind"] in ("hunt", "bounty") and q.get("place") in ws.world.places:
                D = G.get("done_danger", {"value": -15, "days": 5})
                state["effects"].append({"kind": "danger", "place": q["place"], "value": D["value"], "until": ws.minutes + D["days"] * 1440, "cause": q["title"]})
            ws.store.save_world_state(state)
        ws.weight_hint = "rich"
        ws.narrate(f"THE JOB IS DONE AND PAID. What is different now, seen or heard of: {q['result']}. Show it in a sentence or two, as it would be noticed; no speeches.")
    if q.get("more"):
        _open_matter(ws, q)


def _open_matter(ws, q: dict) -> None:
    """A job with more behind it: the reveal is shown and a matter opens with its clue and its path (engine/matters.py)."""
    from engine import events, matters, pulse
    from llm.contracts import PathProposal
    m = q["more"]
    state = ws.store.load_world_state()
    if not state:
        return
    tid = uuid.uuid4().hex[:8]
    th = {"id": tid, "title": q["title"], "tier": "uncommon", "place": q.get("place") if q.get("place") in ws.world.places else ws.player.location,
          "pressure": "", "stage": 0, "status": "active", "made": ws.minutes,
          "stages": [{"description": m.get("reveal", ""), "effects": []}], "fallout": {"description": "It comes to nothing, in the end.", "effects": []},
          "times": [ws.minutes, ws.minutes + G.get("chain", {}).get("days", 7) * 1440], "groups": ["everyone"], "resolution": "", "contract": None,
          "truth": m.get("truth", ""), "clues": [{"text": m["clue"], "holder": "", "npc": "", "found": False}] if m.get("clue") else [],
          "reveal": m.get("reveal", ""), "revealed": True, "touched": True, "door": "board_more", "hidden": True, "opened": ws.minutes,
          "answered": True, "moment": "", "summons": "", "sender": "", "posted": True, "road": False}
    paths = []
    p = m.get("path") or {}
    if p.get("kind") in ("kill", "persuade", "find") and p.get("target"):
        try:
            paths = [PathProposal(**p)]
        except Exception:
            paths = []
    state["threads"].append(th)
    th["paths"] = events.build_paths(ws.store, ws.world, state, paths, th, False)
    matters._bind_holders(ws.store, ws.world, th)
    if th["clues"] and not th["clues"][0]["npc"] and q.get("issuer"):
        th["clues"][0]["npc"] = q["issuer"]
    ws.store.save_world_state(state)
    ws.weight_hint = "rich"
    ws.narrate("AND THERE IS MORE TO IT THAN THE POSTING SAID. What the player finds, now: " + m.get("reveal", "")
               + " Show it plainly, as a thing seen or found, and stop there: no conclusions, no one explaining it.")
    console.debug(f"stakes: more behind {q['title']} - matter {tid} opened, {len(th['paths'])} paths")
