"""Matters (f317): how the player comes to meet a situation the world has started, how they look into it, and what the town keeps.

The pulse (engine/pulse.py) makes situations - threads - off-screen. This module gives each one a door (data/rules/doors.yaml): the
guild board, a board posting with more behind it, a person's own trouble (word), a moment walked into (scene), or someone coming to
look for the player (summons). Every thread of every tier also carries the truth of it, the clues its people hold in their own words,
and the real paths that end it, so a thread met through any door can be looked into by talking to people and ended by a deed.

A clue is a fact a person knows (npc/life.converse lists it under WHAT YOU KNOW with the id clue:<thread>:<n>); when their speech
carries it, it is found, and the matter is in the journal. A path met ends the thread (engine/events.after_deed → finish) and the town
remembers who did it (remember → the place's memory, which the truth layer gives to every speaker there).

Thread fields this module keeps: door, hidden, truth, clues [{text, holder, npc, found}], reveal, revealed, touched, moment, summons,
sender, opened, answered."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from ui import console

ROOT = Path(__file__).resolve().parent.parent
D = yaml.safe_load((ROOT / "data" / "rules" / "doors.yaml").read_text(encoding="utf-8"))


# ---------- at birth: the door, and what the thread carries

def choose_door(state: dict, th: dict, has_contract: bool, has_reveal: bool, reputation: int, rng: random.Random) -> str:
    weights = dict(D["weights"].get(th["tier"], D["weights"]["normal"]))
    if not has_contract:
        weights.pop("board", None); weights.pop("board_more", None)
    if not (has_reveal and len(th["stages"]) >= 2):
        weights.pop("board_more", None)
    if reputation < D["summons"]["reputation"]:
        weights.pop("summons", None)
    last = state.setdefault("doors", {}).get(th["place"])
    if D.get("no_repeat_at_town") and last in weights and len(weights) > 1:
        weights.pop(last)
    if not weights:
        return "word"
    door = rng.choices(list(weights), weights=list(weights.values()))[0]
    if door == "board" and has_reveal and len(th["stages"]) >= 2 and rng.random() < D["board_more_share"]:
        door = "board_more"
    return door


def attach(store, world, state: dict, th: dict, proposal, reputation: int, rng: random.Random, t: int, door: str = "") -> None:
    """Give a new thread its truth, clues, door and standing; open the door that opens at once (word). The contract, when the door is
    the board, is posted by the pulse with hidden set for board_more. `door` (f359): forced, for a situation that answers the player's
    own deeds; a summons forced this way comes whatever the town thinks of the player."""
    th["truth"] = proposal.truth.strip()
    th["clues"] = [{"text": c.text.strip(), "holder": c.holder.strip(), "npc": "", "found": False} for c in proposal.clues]
    th["reveal"] = proposal.reveal.strip() if proposal.contract else ""
    th["revealed"] = False
    th["touched"] = False
    th["door"] = door if door in ("summons", "word", "scene", "board") else choose_door(state, th, bool(proposal.contract and proposal.contract.what), bool(th["reveal"]), reputation, rng)
    th["summons_force"] = door == "summons"
    th["hidden"] = th["door"] == "board_more"
    th["opened"] = t
    th["answered"] = False
    th["moment"] = "pending" if th["door"] == "scene" else ""
    th["summons"] = "pending" if th["door"] == "summons" else ""
    th["sender"] = ""
    state.setdefault("doors", {})[th["place"]] = th["door"]
    _bind_holders(store, world, th)
    if th["door"] == "word":
        _open_word(store, th)
    console.debug(f"matter: {th['title']} - door {th['door']}, {len(th['clues'])} clues, {len(th.get('paths') or [])} paths")


def _town(world, place_id: str) -> str:
    from engine import pulse
    return pulse.town_of(world, place_id)


def _bind_holders(store, world, th: dict) -> None:
    """Each clue's holder becomes a real person where one exists: the id the writer gave, else someone of that role in the town. A clue
    for a role nobody fills yet waits for the first of that role (bind_for) - except the first clue of a word door, which goes to whoever
    is there to talk: a thing like this is heard about."""
    from engine import retrieval
    rows = retrieval.people_in_town(store, world, _town(world, th["place"]))
    used = set()
    for i, c in enumerate(th["clues"]):
        if c["npc"]:
            continue
        h = c["holder"]
        if h and store.npc_exists(h) and not store.load_npc(h).gone:
            c["npc"] = h
        else:
            same = [r for r in rows if r.role == h and r.id not in used]
            if same:
                c["npc"] = same[0].id
            elif i == 0 and th.get("door") == "word" and rows:
                free = [r for r in rows if r.id not in used]
                if free:
                    c["npc"] = free[0].id
        if c["npc"]:
            used.add(c["npc"])


def _open_word(store, th: dict) -> None:
    """The first clue becomes its holder's concern: they bring it up the way concerns come up."""
    if not th["clues"]:
        return
    c = th["clues"][0]
    if not c["npc"]:
        return
    npc = store.load_npc(c["npc"])
    npc.concern = c["text"]
    npc.concern_from = th["id"]
    store.save_npc(npc)


# ---------- clues in conversation

def bind_for(store, world, npc) -> None:
    """A clue written for a role, not a person, settles on the first person of that role the player talks to in that town."""
    state = store.load_world_state()
    changed = False
    for th in state.get("threads", []):
        if th["status"] != "active" or not th.get("clues"):
            continue
        if _town(world, th["place"]) != _town(world, npc.location):
            continue
        for c in th["clues"]:
            if not c["npc"] and c["holder"] == npc.role and npc.id not in {x["npc"] for x in th["clues"]}:
                c["npc"] = npc.id
                changed = True
    if changed:
        store.save_world_state(state)


def clue_facts(store, world, npc) -> list:
    """The clues this person holds and has not yet given away, as facts for WHAT YOU KNOW (npc/prompts): id clue:<thread>:<n>."""
    from world.loader import Fact
    out = []
    for th in store.load_world_state().get("threads", []):
        if th["status"] != "active":
            continue
        for i, c in enumerate(th.get("clues", [])):
            if c["npc"] == npc.id and not c["found"]:
                out.append(Fact(id=f"clue:{th['id']}:{i}", text=c["text"], known_by=[]))
    return out


def talk_lines(ws, npc) -> list[str]:
    """Extra lines for a person's prompt: that they came looking for the player (a summons they sent), and how they know them."""
    out = []
    for th in ws.store.load_world_state().get("threads", []):
        if th["status"] == "active" and th.get("sender") == npc.id and th.get("summons") == "met":
            clue = next((c["text"] for c in th.get("clues", []) if c["npc"] == npc.id), "")
            out.append("YOU CAME LOOKING FOR THE STRANGER on purpose, just now, because of this: " + (clue or th["stages"][th["stage"]]["description"])
                       + " Say so, and say why you came to them of all people, in your own words. You want their help; ask for it plainly.")
            if not npc.met_player:
                town = _town(ws.world, npc.location)
                out.append(f"You have never spoken to them before, but you know who they are: the town talks about them ({ws.reputation_words(town)}).")
    return out


def spoke(ws, npc) -> None:
    """The player has talked to the one who came looking: they have said their piece, and do not say it again."""
    state = ws.store.load_world_state()
    hit = False
    for th in state.get("threads", []):
        if th["status"] == "active" and th.get("sender") == npc.id and th.get("summons") == "met":
            th["summons"] = "talked"
            th["answered"] = True
            hit = True
    if hit:
        ws.store.save_world_state(state)


def mark_found(ws, npc, revealed: list[str]) -> list[str]:
    """Clues the person's speech carried are now found; the matter is the player's. Returns the clue texts, for the journal."""
    ids = [r for r in revealed if r.startswith("clue:")]
    if not ids:
        return []
    state = ws.store.load_world_state()
    found = []
    for r in ids:
        _, tid, i = r.split(":")
        th = next((x for x in state.get("threads", []) if x["id"] == tid), None)
        if th and int(i) < len(th.get("clues", [])) and not th["clues"][int(i)]["found"]:
            th["clues"][int(i)]["found"] = True
            th["clues"][int(i)]["by"] = npc.label()
            th["touched"] = True
            th["answered"] = True
            found.append(th["clues"][int(i)]["text"])
            console.debug(f"matter: clue found - {th['title']}: {th['clues'][int(i)]['text'][:80]}")
    if found:
        ws.store.save_world_state(state)
    return found


# ---------- doors that open when the player is there: a moment, or someone coming to find them

def _cooldown_ok(state: dict, town: str, kind: str, now: int) -> bool:
    log = state.setdefault("door_log", {}).setdefault(town, {})
    return now - log.get(kind, -10 ** 9) >= D[kind]["cooldown_days"] * 1440


def _note(state: dict, town: str, kind: str, now: int) -> None:
    state.setdefault("door_log", {}).setdefault(town, {})[kind] = now


def on_arrival(ws) -> None:
    """The player is somewhere in a town, at the end of a turn: a pending moment plays out in front of them, or someone comes looking
    for them. A moment prefers the turn they arrive on."""
    entering = getattr(ws, "_door_loc", None) != ws.player.location
    ws._door_loc = ws.player.location
    if ws.combat or getattr(ws, "halted", False) or ws.player.location not in ws.world.places or ws.world.places[ws.player.location].danger:
        return
    town = _town(ws.world, ws.player.location)
    state = ws.store.load_world_state()
    if not state:
        return
    rng = random.Random(f"{ws.store.meta.seed}:door:{ws.minutes}:{ws.player.location}")
    changed = False
    def touches(x):                                   # a cataclysm (f324) touches every town in its path, not only its origin
        return _town(ws.world, x["place"]) == town or town in x.get("hit_towns", [])
    live = [x for x in state.get("threads", []) if x["status"] == "active" and touches(x)]
    from engine import threads
    for th in live:                                   # (f331) a situation the engine built is re-told in the world's words, once, now that the player is here
        if th.get("made_by") == "engine" and not th.get("told"):
            changed |= threads.tell(ws.store, ws.world, state, th, ws.minutes) or "told_at" in th
            break
    for th in live:
        if th.get("moment") == "pending" and _cooldown_ok(state, town, "scene", ws.minutes):
            if entering and rng.random() > D["scene"]["on_enter_chance"]:
                continue
            _play_moment(ws, state, th)
            _note(state, town, "scene", ws.minutes)
            from engine import pulselog
            pulselog.mark("scene", th["title"], ws.minutes, place=ws.player.location)                  # (f355)
            changed = True
            break
        if th.get("summons") == "pending" and _cooldown_ok(state, town, "summons", ws.minutes):
            if _send_someone(ws, state, th):
                _note(state, town, "summons", ws.minutes)
                from engine import pulselog
                pulselog.mark("summons", th["title"], ws.minutes, place=ws.player.location)            # (f355)
                changed = True
                break
    if changed:
        ws.store.save_world_state(state)


def _play_moment(ws, state: dict, th: dict) -> None:
    """The situation as it would be seen, happening in front of the player, with the people here part of it."""
    stage = th["stages"][th["stage"]]["description"]
    for c in th.get("clues", []):                     # the people here saw it: a clue nobody holds yet settles on one of them, their role first
        if not c["npc"]:
            taken = {x["npc"] for x in th["clues"]}
            free = [n for n in ws.present if n.id not in taken and c["holder"] == n.role] or [n for n in ws.present if n.id not in taken]
            if free:
                c["npc"] = free[0].id
    holders = [n.label() for n in ws.present if n.id in {c["npc"] for c in th["clues"]}]
    from engine import moments, threads
    shape = threads.scene_shape(th)
    if shape and not moments.active(ws.store, ws.player.location, ws.minutes):                     # (f357) the situation's own moment, played by the moments machinery
        m = moments.start(ws, shape, random.Random(f"{ws.store.meta.seed}:scene:{th['id']}"))
        ws.__dict__.setdefault("_arrival_lines", []).append("A MOMENT THE PLAYER WALKS INTO, happening now in front of them: " + m["line"]
                                                             + (f" The people here are part of it ({', '.join(holders)} most of all)." if holders else ""))
        th["moment"] = "shown"
        th["touched"] = True
        console.debug(f"matter: moment shown as a {shape['id']} - {th['title']}")
        return
    ws.weight_hint = "rich"
    ws.narrate("A MOMENT THE PLAYER WALKS INTO, happening now in front of them: " + stage
               + (f" The people here are part of it ({', '.join(holders)} most of all)." if holders else "")
               + " Show it as it would be seen and heard, in the present, and leave the player free to step in or pass by. Nobody addresses them unless it fits.")
    th["moment"] = "shown"
    th["touched"] = True
    console.debug(f"matter: moment shown - {th['title']}")


def _send_someone(ws, state: dict, th: dict) -> bool:
    """Someone of the town comes to find the player: an anchor first, else the holder of the first clue. Only when the town thinks
    enough of the player; a person who never met them comes only when the town knows them by name (doors.yaml summons)."""
    from engine import retrieval
    S = D["summons"]
    town = _town(ws.world, ws.player.location)
    rep = ws.player.reputation.get(town, 0)
    if th.get("summons_force"):
        rep = max(rep, S["known_by_all"])                  # (f359) the town answers the stranger's deeds whatever it thinks of them
    if rep < S["reputation"]:
        return False
    rows = retrieval.people_in_town(ws.store, ws.world, town)
    people = [ws.store.load_npc(r.id) for r in rows]
    people = [n for n in people if not n.gone and n.id not in ws.player.prisoners]
    pick = None
    if S.get("anchors_first"):
        pick = next((n for n in people if n.anchor and (n.met_player or rep >= S["known_by_all"])), None)
    if pick is None:
        holder = next((c["npc"] for c in th.get("clues", []) if c["npc"]), "")
        n = next((x for x in people if x.id == holder), None)
        if n is not None and (n.met_player or rep >= S["known_by_all"]):
            pick = n
    if pick is None:
        pick = next((n for n in people if n.met_player), None) if rep < S["known_by_all"] else (people[0] if people else None)
    if pick is None:
        return False
    if not any(c["npc"] == pick.id for c in th.get("clues", [])) and th.get("clues"):
        th["clues"][0]["npc"] = pick.id                     # what they come with
    th["sender"] = pick.id
    th["summons"] = "met"
    th["touched"] = True
    from engine import court
    if court.summon(ws, pick, th):                       # (f320) someone behind a door sends a messenger, and the door opens for the day
        return True
    ws.visit(pick, ws.minutes + 120)
    known = "someone the player has met" if pick.met_player else "someone the player has not met, who knows them by name"
    ws.weight_hint = "rich"
    ws.narrate(f"{pick.label()} ({known}) comes looking for the player, on purpose, and finds them here. Show them arriving and making "
               "it plain they want a word - what they are doing, how they carry it - without a word of what it is about; the player will ask.")
    console.debug(f"matter: {pick.name} comes looking for the player - {th['title']}")
    return True


# ---------- looking for the thing that settles it (a find path)

def try_find(ws, text: str = "") -> bool:
    """The player searches or looks closely where a matter's find path points: a perception roll, and on a success the thing is found,
    the deed is logged and the matter may end. True when a roll was made and narrated (the caller's own search is done)."""
    from engine import checks
    state = ws.store.load_world_state()
    here = ws.player.location
    for th in state.get("threads", []):
        if th["status"] != "active":
            continue
        path = next((p for p in th.get("paths", []) if p["kind"] == "find" and p["target"] == here and not p["done"]), None)
        if not path:
            continue
        c = ws.player.character
        odds, _ = checks.chance(c, "perception", ws.check_triggers("perception", False))
        degree, _ = checks.roll(odds, ws.rng, c=c)
        console.ledger(checks.label("perception", degree.replace("_", " ")))
        if degree in ("success", "strong success"):
            th["touched"] = True
            th["answered"] = True
            ws.store.save_world_state(state)
            ws.weight_hint = "rich"
            ws.narrate("THE PLAYER FINDS WHAT THEY WERE LOOKING FOR, here, now: " + (path["how"] or path["name"])
                       + " Show the finding as it would be seen and handled, and stop there - no conclusions, no one explaining it.", text)
            console.debug(f"matter: found - {th['title']} at {here}")
            from engine.domain_events import ClueFound
            ws.notice(ClueFound(minute=ws.minutes, place=here, thread=th["id"], what=path["name"]))
        elif degree == "partial":
            ws.narrate("The player searches here and has the feeling something is to be found, without putting a hand on it yet. "
                       "Nothing named.", text)      # (f384) no length
        else:
            ws.narrate("The player searches here and finds nothing out of the ordinary. Describe the search.", text)   # (f413) no length (f375)
        return True
    return False


# ---------- the road: a happening on the way is part of a matter nearby

def road_matter(ws, a: str, b: str, rng: random.Random):
    """A live situation at either end of the road, if the road's happening is to be part of it (doors.yaml road): (thread, clue text,
    kill target). Each situation shows itself on the road once."""
    from engine import pulse
    Rd = D.get("road", {})
    state = ws.store.load_world_state()
    if not state or rng.random() >= Rd.get("chance", 0.5):
        return None
    towns = {pulse.town_of(ws.world, a), pulse.town_of(ws.world, b)}
    live = [t for t in state.get("threads", []) if t["status"] == "active" and pulse.town_of(ws.world, t["place"]) in towns
            and not t.get("road") and t.get("clues")]
    if not live:
        return None
    live.sort(key=lambda t: t.get("touched", False))               # one the player has not met yet, first
    th = live[0]
    clue = next((c for c in th["clues"] if not c["found"]), None)
    kill = next((p["target"] for p in th.get("paths", []) if p["kind"] == "kill" and not p["done"] and p["target"] in ws.world.bestiary), "")
    return th, (clue["text"] if clue else th["stages"][th["stage"]]["description"]), kill


def road_lines(th: dict, clue: str, hostile: bool) -> str:
    """What the road writer is told to make the happening part of."""
    stage = th["stages"][th["stage"]]["description"]
    if hostile:
        return f" They are part of THE MATTER nearby - {th['title']}: {stage} - and it should show in how they come."
    return (f" It bears on THE MATTER nearby - {th['title']}: {stage}. What the player comes across lets them learn this, as a thing seen "
            f"or said, in the scene or the detail, never as a summary: '{clue}'")


def road_shown(ws, th_id: str, carried: bool = True) -> None:
    """The matter has shown itself on the road; when the happening carried a clue (not an ambush), it is found."""
    state = ws.store.load_world_state()
    th = next((t for t in state.get("threads", []) if t["id"] == th_id), None)
    if not th:
        return
    th["road"] = True
    th["touched"] = True
    c = next((c for c in th.get("clues", []) if not c["found"]), None) if carried else None
    if c:
        c["found"] = True
        c["by"] = "on the road"
        th["touched"] = True
        th["answered"] = True
        console.ledger(f"Noted: {c['text']}")
    ws.store.save_world_state(state)
    console.debug(f"matter: shown on the road - {th['title']}")


# ---------- the board door with more behind it

def reveal(ws, state: dict, th: dict) -> None:
    """The contract is done and paid; what the job did not say comes out, and the matter stays open with its paths."""
    from engine import pulse
    th["revealed"] = True
    th["touched"] = True
    if th["clues"]:
        th["clues"][0]["found"] = True
        th["clues"][0]["by"] = "found on the job"
    if th["stage"] + 1 < len(th["stages"]):
        th["stage"] += 1
        stage = th["stages"][th["stage"]]
        pulse.apply_effects(ws.store, ws.world, ws.catalog, state, stage["effects"], th["tier"], ws.minutes, th["title"], raw=True, thread_id=th["id"])
        pulse.add_news(state, stage["description"], th["place"], ws.minutes, th["groups"], thread=th["id"])
    ws.weight_hint = "rich"
    ws.narrate("THE JOB IS DONE AND PAID, AND THERE IS MORE TO IT THAN THE POSTING SAID. What the player finds, now: " + th["reveal"]
               + " Show it plainly, as a thing seen or found, and stop there: no conclusions, no one explaining it.")
    console.debug(f"matter: revealed - {th['title']}: {th['reveal'][:80]}")


# ---------- a door that went unanswered opens another

def reopen(store, world, state: dict, th: dict, t: int) -> bool:
    """After reopen_after_days with nobody listening, a word becomes a scene, and a scene becomes a posting if there is a contract."""
    if th.get("answered") or t - th.get("opened", t) < D["reopen_after_days"] * 1440:
        return False
    if th.get("door") == "word" and th.get("moment") != "shown":
        th["door"], th["moment"], th["opened"] = "scene", "pending", t
        console.debug(f"matter: {th['title']} - nobody listened; it will be seen")
        return True
    if th.get("door") == "scene" and th.get("moment") == "shown" and th.get("contract") and not th.get("posted"):
        from engine import pulse
        from llm.contracts import QuestOffer
        if pulse.post_contract(store, world, QuestOffer(**th["contract"]), th, t):
            th["posted"] = True
            th["door"], th["opened"] = "board", t
            console.debug(f"matter: {th['title']} - the town gave up and paid the guild")
            return True
    return False


# ---------- what the town keeps

def remember(store, world, th: dict, how: str, name: str, minutes: int, turn: int) -> None:
    """A matter ended: the town's memory (the truth layer gives it to every speaker there), and the people in it remember too.
    how is settled (by the player) or ignored (they were asked, and let it be)."""
    from engine import clock
    from npc.models import Memory
    M = D["memory"]
    town = _town(world, th["place"])
    if town not in world.places or world.places[town].danger:
        return
    when = f"{clock.season(minutes)}, day {clock.day(minutes)}"
    text = M[how].format(title=th["title"], name=name, when=when)
    ps = store.load_place(town)
    ps.memory = (ps.memory + [{"text": text, "minute": minutes}])[-12:]
    store.save_place(ps)
    line = f"{name} settled {th['title'].lower()}." if how == "settled" else f"{name} was asked about {th['title'].lower()}, and let it be."
    for nid in {c["npc"] for c in th.get("clues", []) if c["npc"]} | ({th["sender"]} if th.get("sender") else set()):
        if store.npc_exists(nid):
            n = store.load_npc(nid)
            n.memories.append(Memory(day=clock.day(minutes), turn=turn, text=line, importance=2))
            store.save_npc(n)
    console.debug(f"matter: {town} remembers - {text}")


def town_note(store, world, place_id: str, text: str, minutes: int) -> None:
    """(f323) A line in the town's memory that is not the player's doing: what its own people settled."""
    from engine import pulse, clock
    town = pulse.town_of(world, place_id)
    if town not in world.places or world.places[town].danger:
        return
    ps = store.load_place(town)
    ps.memory = (ps.memory + [{"text": f"{text} ({clock.season(minutes)}, day {clock.day(minutes)})", "minute": minutes}])[-12:]
    store.save_place(ps)


def town_memory(store, world, place_id: str, now: int) -> list[str]:
    """What this town remembers of the matters that ended here lately."""
    from engine import pulse
    town = pulse.town_of(world, place_id)
    if town not in world.places or world.places[town].danger:
        return []
    keep = D["memory"]["keep_days"] * 1440
    return [m["text"] for m in store.load_place(town).memory if now - m["minute"] <= keep and m.get("until", now + 1) > now]   # a moment's memory fades sooner (engine/moments.py)


# ---------- the journal

def journal(ws) -> list[dict]:
    """The matters the player has touched: what they have found of each, in the order found, and how it stands. Nothing they have not found."""
    from engine import pulse
    out = []
    state = ws.store.load_world_state()
    for th in reversed(state.get("threads", [])):
        if not th.get("touched"):
            continue
        found = [c for c in th.get("clues", []) if c["found"]]
        if th["status"] == "active":
            standing = "still going on"
        elif th.get("result") == "player":
            standing = "settled by you"
        elif th["status"] == "resolved":
            standing = "settled by others"
        else:
            standing = "over, one way or another"
        lines = [f"{c['text']} ({c.get('by', '')})" if c.get("by") else c["text"] for c in found]
        if th.get("revealed") and th.get("reveal"):
            lines.append(th["reveal"])
        place = ws.world.places[th["place"]].name if th["place"] in ws.world.places else th["place"]
        out.append({"title": th["title"], "place": place, "standing": standing, "found": lines})
    return out
