"""(f495) The script of the kept recording stub_fight (data/replay/sessions/stub_fight): the fights the two other kept recordings never
reach. stub_short's fights are three short brawls with no one at the player's side; stub_party has none. Bundle E rewrites the fight
code with no balance number changed (decision 10), and these are the paths it must keep: a hire fighting and falling, a round that
cannot be read, a round that cannot be told, a draught drunk in the middle, a boss's drops named, a level gained, a fight run from.
Recorded on the tree before the rewrite (f495), with the stand-in model's answers, and kept by tools/rerun.py --golden stub_fight.

    the save   a warrior of level 18 at the south fields with two hires from the home hall, one of them badly hurt (five per cent of
               their health, so the first blow puts them down and the dice decide whether they die); three healing draughts; the
               experience one short of the next level; and a campaign boss, a bandit captain, loose in the fields (a world event's
               spawn, as engine/events.py add_spawn writes one), who lets a warrior this far above the land pass by (roads.yaml
               deterrence), so they are seen keeping their distance and must be crept up on
    the lines  searching the fields until the captain is seen; creeping up to strike (the sneaking start); a word to the standing hire
               before the first blow (a companion's reply, in the fight); the first round, in which the hurt hire goes down; a round
               whose reading fails (every try of the combat intent fails: the line is not taken) and the same line again; a round
               whose telling fails (the round stands, the numbers carry it); a draught drunk mid-fight (#useitem); blows until the
               captain falls, with his drops named (a rare or epic piece, a legendary piece, and his relic) and the level gained; then
               searching again until something of the fields is found, and running from it

The seed is the one on which the dice gave what the census asks: the player alive at the end (about half the seeds die to the
captain), a hire dead (party.yaml death_when_down, a coin's toss for each who goes down; on this seed the standing one, Dade Bromwood,
and the hurt one carried out alive) and a legendary among the captain's two drops (combat.yaml loot.boss rarity_weights, about one in
five). Another seed is another recording; the census refuses one that holds less. CENSUS (census()) is what the recording must hold,
or the maker refuses it."""
from __future__ import annotations

import random
import shutil
from pathlib import Path

from llm.errors import Failure                  # (f527) a planted failure is the interface's own, no longer the old client's

SEED = 18
SAVE = "rerun_make_stub_fight"
PLACE = "south_fields"
BOSS = "bandit_captain"
BOSS_NAME = "Marrow Hask"
LEVEL = 18
BOSS_LEVEL = 13
BOSS_HEALTH = 3                   # times a normal creature's health (events.yaml spawn.boss_health is 4; a boss's rank alone is 6)
MOST_LINES = 80


def record(folder: Path, root: Path) -> Path:
    import sys
    sys.path.insert(0, str(root / "tools"))
    import simlib
    stub = simlib.Stub("warrior", SEED)
    held = simlib.install(stub)
    from engine import leveling, pulse, recording
    from engine.session import CampaignSession
    from npc.traits import load_traits
    from storage.campaign import PlayerState
    from ui import console
    import nightrun

    shutil.rmtree(root / "saves" / SAVE, ignore_errors=True)
    session = CampaignSession.open(SAVE)
    store = session.store
    now = 8 * 60 + 600 * 1440
    store.meta.seed, store.meta.turn, store.meta.minutes = SEED, 1, now
    store.save_meta()
    rng = random.Random(SEED)
    char, spec = simlib.make_character("warrior", rng)
    leveling.level_up(char, LEVEL - 1)                             # a warrior of this level, as a night's run makes one (tools/nightrun.py)
    nightrun.spend_points(char, spec)
    nightrun.outfit(char, spec, LEVEL, rng)                        # the class's weapon and armour at the level, draughts, coin
    char.xp = leveling.xp_to_next(LEVEL) - 1                       # the next kill is a level
    player = PlayerState(character=char, location="parth")
    player.mentor["never"] = True
    player.guild_rank = "D"
    store.save_player(player)
    for name in recording.STORY:
        if hasattr(console, name):
            setattr(console, name, lambda *a, **k: None)
    console.panel = lambda name, data: False
    for name in ("out", "status_block", "combat_state", "show_header", "debug"):
        if hasattr(console, name):
            setattr(console, name, lambda *a, **k: None)
    ws = session.scene(load_traits(), store.load_player())
    nightrun.hire_party(ws, 2)
    for m in ws.player.party:
        m["level"] = m["base_level"] = LEVEL - 2                   # hired as fighters of near the player's level
    hurt = ws.player.party[0]
    hurt["hp_frac"], hurt["hp_at"] = 0.05, now                      # the first blow puts them down
    state = store.load_world_state() or pulse.empty_state(now)
    state.setdefault("spawns", []).append({                         # a world event's boss, as engine/events.py add_spawn writes one
        "id": "f495boss", "thread": "f495", "place": PLACE, "creature": BOSS, "boss": True, "level": BOSS_LEVEL, "name": BOSS_NAME,
        "need": 1, "kills": 0, "defeated": False, "from": now - 1440, "until": now + 30 * 1440, "tier": "campaign", "hp_mult": BOSS_HEALTH})
    store.save_world_state(state)
    ws.player.location = PLACE
    store.save_player(ws.player)
    session.close()                                                # the recording starts from the save as a replay opens it: a fresh scene
    session = CampaignSession.open(SAVE)
    store = session.store
    ws = session.scene(load_traits(), store.load_player())
    standing = ws.player.party[1]["name"].split()[0]

    fail = {"title": ""}

    def chat(**k):
        if fail["title"] and k["format"].get("title") == fail["title"]:
            raise Failure("server", "the model server cannot be reached")    # every try of this input fails
        return stub.chat(**k)
    planted = simlib.stand_in(chat=chat)                           # (f518) the stub and its failures, as a source with no embedder
    mode = {"kind": "attack"}

    def choose(u, k):
        f = ws.combat.fight if ws.combat is not None else None
        if mode["kind"] == "talk":
            return {"kind": "talk"}
        if mode["kind"] == "flee":
            return {"kind": "flee"}
        foes = f.enemies() if f is not None else []
        return {"kind": "attack", "target": foes[0].id if foes else ""}
    stub.a_CombatIntent = choose
    stub.a_LootName = lambda u, k: {"name": "Reeve's Spur", "description": "A spur with a notched rowel, taken from the fields."}
    stub.companion = lambda u: {"speech": "A scratch. Keep your eyes on him, not on me.", "gesture": "hefts the shield", "remember": "", "impression": ""}

    def boss_fight(f) -> bool:
        return any(e.rank == "boss" for e in f.fighters if e.side == "enemy")

    st = {"n": 0, "fighting": False, "step": 0, "boss_done": False, "fled": False}

    def ask(*a, **k):
        if not k.get("main", a[0] if a else False):
            return "yes"
        st["n"] += 1
        fail["title"] = ""
        if st["n"] > MOST_LINES or (st["boss_done"] and st["fled"]):
            return "quit"
        fighting = ws.combat is not None and not ws.combat.fight.over
        if fighting and not st["fighting"]:
            st["step"] = 0                                         # a fight just began
        st["fighting"] = fighting
        if fighting:
            f = ws.combat.fight
            if boss_fight(f):
                step = st["step"]
                st["step"] += 1
                if step == 0 and any(m["name"].split()[0] == standing for m in ws.player.party):
                    mode["kind"] = "talk"
                    return f"{standing}, are you hurt?"             # a word to a companion in the fight: no turn spent
                mode["kind"] = "attack"
                if step == 2:
                    fail["title"] = "CombatIntent"                  # the round cannot be read: the line is not taken
                if step == 4:
                    fail["title"] = "Narration"                     # the round cannot be told: the round stands
                if step == 5:
                    return "#useitem healing draught"
                return f"I strike at {BOSS_NAME}."
            mode["kind"] = "flee"
            return "I run for it."
        if st["step"] and not st["boss_done"]:
            st["boss_done"] = True                                 # the boss fight is over (won: the census checks the victory)
        if st["boss_done"] and getattr(ws, "recently_fled", False):
            st["fled"] = True                                      # the fight after the boss's was run from (scenes/combat_scene.py finish)
        if getattr(ws, "wildlife", None):
            creature, foes = ws.wildlife
            if any(e.rank == "boss" for e in foes):
                stub.plan = [{"kind": "attack", "target": foes[0].name, "checks": ["stealth"]}]
                return f"I creep up on {BOSS_NAME} and strike."    # the sneaking start
            if st["boss_done"]:                                    # the fields' own creatures keep their distance: the one to run from
                stub.plan = [{"kind": "attack", "target": foes[0].name}]
                return f"I attack the {creature.name.lower()}."
        if not st["boss_done"]:
            stub.plan = [{"kind": "search", "seek": "bandit"}]
            return "I search the fields for the bandits."
        stub.plan = [{"kind": "search"}]
        return "I beat through the grass for game."
    console.ask = ask
    session.record(folder=folder, rows=True)
    try:
        ws.run()
    finally:
        session.close()
        planted()
        held()
        shutil.rmtree(root / "saves" / SAVE, ignore_errors=True)
    return folder


CENSUS = ("CombatIntent", "Narration", "CompanionReply", "LootName", "LegendaryName", "AccessoryName")


def census(rec: dict) -> list[str]:
    """What the recording must hold: each title above at least once; a combat intent that failed and the same line said again; a round's
    telling that failed; the sneaking start; a hire killed; a draught drunk mid-fight; the victory, a level gained; a fight run from."""
    calls = rec["calls"]
    titles = {c.get("title") for c in calls}
    missing = [t for t in CENSUS if t not in titles]
    for title, what in (("CombatIntent", "a failed CombatIntent"), ("Narration", "a failed Narration")):
        if not any(c.get("title") == title and c.get("error") for c in calls):
            missing.append(what)
    mains = [i for i in rec["inputs"] if i.get("main")]
    texts = [i.get("text", "") for i in mains]
    failed_at = {c["input"] for c in calls if c.get("title") == "CombatIntent" and c.get("error")}
    if not any(i + 1 < len(texts) and texts[i] == texts[i + 1] and mains[i]["i"] in failed_at for i in range(len(texts) - 1)):
        missing.append("the line said again after the failure")
    if not any(t.startswith("I creep up on") for t in texts):
        missing.append("the sneaking start")
    if not any(t.startswith("#useitem") for t in texts):
        missing.append("the draught drunk mid-fight")
    shown = "\n".join(l for t in rec["turns"] for l in t.get("shown_text") or [])
    for mark, what in (("Victory.", "the victory"), ("LEVEL UP!", "the level gained"), ("You got away.", "the fight run from")):
        if mark not in shown:
            missing.append(what)
    if "You have died." in shown:
        missing.append("the player alive throughout (a death and the Threshold are not this recording's)")
    rows = [str(v) for t in rec["turns"] for v in (((t.get("rows") or {}).get("entities") or {}).get("added") or {}).values()]
    if not any('"hire", "dead"' in v for v in rows):                # the hire's entity, dead (core/models.py Entity)
        missing.append("a hire's death")
    return missing
