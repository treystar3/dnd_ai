"""(f735) The towns a character has stood in hold only places that count as settled, so Word of Recall finds the town behind (the
audit's aged-save-2). Every arrival wrote the place's town into the character's list of towns stood in, passing over dangerous
places only, and a road stop or a dungeon's mouth is no town's part: each was written as a town of its own. A walk from Parth to
Willowmead stopped once on the road left [parth, road_x, willowmead], the stop tidied off the map as soon as the walk went on, and
Word of Recall in Willowmead answered "There's no town behind you to return to yet." with Parth behind; the journal's "last
visited" town was the stop. GOALS.md (review Q15) says neither a road stop nor a dungeon's mouth counts as settled.
Now one predicate (engine/pulse.py settled) says what counts, the list takes only those, and one reader (the town behind: the
newest entry on the map, settled and not where the character stands) serves Word of Recall and the journal, so a save that already
holds a stop or a dungeon's mouth reads right as it is.
The case that found it: Parth, a stop, Willowmead. Second case of the kind: Parth, the Cracked Plains' dungeon mouth, Parth, where
the ability took the character down to the mouth. Also: two stops in a row; a save holding a gone stop and a dungeon's mouth,
opened again; the journal's last town; the ability used at a stop; a second character's own list.
Run: python tools/sim/town_behind_735_test.py"""
import os
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
import config
import ui.console as uc

NAME, LOGS = "town_behind", "saves/town_behind_logs"
os.makedirs(LOGS, exist_ok=True)
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, f"{LOGS}/{fn}")
SHOWN = simlib.quiet_console()
uc.put("status_block", lambda *a, **k: None)
uc.put("combat_state", lambda *a, **k: False)
from engine import abilities, loadout, pulse, roads
from llm.contracts import ActionIntent, ActiveProposal

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


R = roads.R
KEEP = {k: R[k] for k in ("chance_per_leg", "hostile", "kinds", "max_per_trip")}
NO_TOWN = "There's no town behind you to return to yet."
loadout.L["start"] = loadout.L["max"] = 99           # room to bring the ability the test gives


def fresh(at: str = "parth", seed: int = 5):
    g = simlib.campaign(NAME, seed=seed, location=at, minutes=420)
    ws = g.scene
    ws.enter(at)
    g.store.save_player(ws.player)
    return g, ws


def play(ws, text, plan) -> list:
    """One typed line through the game's one input path: the operations of it that failed."""
    stub.plan = [dict(p) for p in plan]
    ws.play(text)
    return [f"{o.kind}: {o.failure}" for o in ws.line_failed]


def recall(ws) -> tuple:
    """Word of Recall spoken where the character stands, as the game dispatches an ability: (where they stand after, the notes)."""
    c = ws.player.character
    ab = next((a for a in c.actives if a.field_use == "word_of_recall"), None)
    if ab is None:
        ab = abilities.materialize_active(ActiveProposal(name="Waystone Word", description="speaks the word that folds the road home",
                                                         effect="utility", tier="moderate", reach="self", resource="mana",
                                                         context="out_of_combat", field_use="word_of_recall"))
        c.actives.append(ab)
    ws.fld.get("cd", {}).pop(ab.id, None)
    c.mana = c.stamina = 10 ** 6
    ws.halted = False
    del SHOWN[:]
    ws.on_ability(ActionIntent(kind="ability", ability=ab.id), f"I speak the {ab.name}.")
    return ws.player.location, [t for k, t in SHOWN if k == "note"]


def towns(ws) -> list:
    return list(ws.fld.get("towns", []))


def walk(ws, dest: str, stops: int) -> list:
    """Walk to `dest`, the walk stopped `stops` times on the road by someone in need: the ids of the stops stood at, in the order
    met (an id not a stop when stood at is kept as "not a stop: <id>", so the caller's check says so)."""
    there = ws.world.places[dest].name
    made = []
    R.update(chance_per_leg=1.0, hostile=0.0, kinds={"aid": 1}, max_per_trip=9)
    for i in range(stops):
        play(ws, f"I set out for {there}." if i == 0 else f"I walk on toward {there}.", [{"kind": "move", "destination": dest}])
        at = ws.player.location
        made.append(at if roads.is_stop(ws.world, at) else f"not a stop: {at}")
    R.update(chance_per_leg=0.0)
    play(ws, f"I walk on toward {there}." if stops else f"I set out for {there}.", [{"kind": "move", "destination": dest}])
    R.update(KEEP)
    return made


def settled(world, pid):
    """The predicate under test, or None before it is built."""
    f = getattr(pulse, "settled", None)
    return f(world, pid) if f else None


def behind(ws, cid):
    """The reader under test, or None before it is built."""
    f = getattr(ws, "town_behind", None)
    return f(cid) if f else None


def all_settled(ws) -> bool:
    """Every entry a top-level place on the map that GOALS.md (review Q15) counts as settled, each once: the rule read here by hand."""
    world, got = ws.world, towns(ws)
    return all(t in world.places and not world.places[t].parent and not roads.is_stop(world, t) and world.places[t].type != "dungeon"
               and not world.places[t].danger for t in got) and len(set(got)) == len(got)


g = None
try:
    # ---- the predicate: what counts as settled
    g, ws = fresh()
    world = ws.world
    ws.ensure_dungeons()
    mouth = ws.store.load_dungeons()[0]["entrance"]
    wild = next(p.id for p in world.places.values() if p.danger and not p.parent and p.type != "dungeon")
    stop = roads.make_stop(world, "parth", "willowmead", 0.5, 480, "A quiet bend.", "", "A bend")
    from world.loader import Place
    world.add_place(Place(**stop["place"]))
    check("a town, a village and a shop inside a town count as settled; a road stop, a dungeon's mouth, a dangerous wild and a place "
          "off the map do not", [settled(world, x) for x in ("parth", "willowmead", "tilted_plough", stop["id"], mouth, wild, "road_gone")]
          == [True, True, True, False, False, False, False],
          [(x, settled(world, x)) for x in ("parth", "willowmead", "tilted_plough", stop["id"], mouth, wild, "road_gone")])
    world.remove_place(stop["id"])
    g.close()

    # ---- the case that found it: Parth, a stop, Willowmead; the journal's last town on the way
    g, ws = fresh()
    world, store = ws.world, ws.store
    for n in ws.present:
        simlib.view(n).met = True
        simlib.view(n).name_known = True
        store.save_npc(n)
    made = walk(ws, "willowmead", 1)
    check("(the walk to Willowmead was stopped once at a stop on the road, and went on to Willowmead)",
          len(made) == 1 and made[0].startswith("road_") and ws.player.location == "willowmead", (made, ws.player.location))
    check("Parth, a stop, Willowmead: the towns stood in are Parth and Willowmead, and the stop is not among them",
          towns(ws)[-2:] == ["parth", "willowmead"] and not set(made) & set(towns(ws)), (towns(ws), made))
    check("...every entry counts as settled and is a top-level place, each once", all_settled(ws), towns(ws))
    groups = [(gr["town"], gr["tag"]) for gr in ws.journal_data()["groups"]]
    check("the journal puts Parth after Willowmead as the last town visited", ("Parth", "last visited") in groups, groups)
    where, notes = recall(ws)
    check("Word of Recall in Willowmead takes the character back to Parth", where == "parth" and any("you stand in Parth" in n for n in notes),
          (where, notes))
    g.close()

    # ---- two stops in a row, on the longer road to Eldervale
    g, ws = fresh()
    made = walk(ws, "eldervale", 2)
    check("(the walk to Eldervale was stopped twice, at two different stops, and went on to Eldervale)",
          len(set(made)) == 2 and all(m.startswith("road_") for m in made) and ws.player.location == "eldervale", (made, ws.player.location))
    check("two stops in a row: neither is among the towns stood in", towns(ws)[-2:] == ["parth", "eldervale"] and not set(made) & set(towns(ws))
          and all_settled(ws), (towns(ws), made))
    where, notes = recall(ws)
    check("...and Word of Recall in Eldervale takes the character back to Parth", where == "parth", (where, notes))
    g.close()

    # ---- the ability used at a stop: back to the town left
    g, ws = fresh()
    R.update(chance_per_leg=1.0, hostile=0.0, kinds={"aid": 1}, max_per_trip=9)
    play(ws, "I set out for Willowmead.", [{"kind": "move", "destination": "willowmead"}])
    R.update(KEEP)
    at = ws.player.location
    check("(the walk was stopped at a stop on the road)", roads.is_stop(ws.world, at), at)
    check("standing at the stop, it is not among the towns stood in", at not in towns(ws) and all_settled(ws), (at, towns(ws)))
    where, notes = recall(ws)
    check("Word of Recall at a stop takes the character back to the town left, and the stop is tidied away",
          where == "parth" and at not in ws.world.places, (where, notes))
    g.close()

    # ---- second case of the kind: a dungeon's mouth
    g, ws = fresh()
    ws.ensure_dungeons()
    d = next(x for x in ws.store.load_dungeons() if x["entrance"] == "dungeon_cracked_plains")
    for pid in (d["place"], d["entrance"], "parth"):
        ws.enter(pid)
    check("Parth, the Cracked Plains' dungeon mouth, Parth: the mouth is not among the towns stood in", towns(ws) == ["parth"], towns(ws))
    where, notes = recall(ws)
    check("...and Word of Recall in Parth finds no town behind and leaves the character in Parth, not at the mouth",
          where == "parth" and NO_TOWN in notes, (where, notes))
    for pid in ("willowmead", "parth", d["place"], d["entrance"], "parth"):
        ws.enter(pid)
    check("Willowmead, Parth, the mouth, Parth: the towns stood in are Willowmead and Parth", towns(ws) == ["willowmead", "parth"], towns(ws))
    where, notes = recall(ws)
    check("...and Word of Recall in Parth takes the character to Willowmead, not to the mouth", where == "willowmead", (where, notes))
    g.close()

    # ---- a save that already holds a stop gone from the map and a dungeon's mouth, opened again
    g, ws = fresh()
    ws.ensure_dungeons()
    mouth = ws.store.load_dungeons()[0]["entrance"]
    ws.enter("willowmead")
    ws.enter("parth")
    ws.fld["towns"] = ["willowmead", "road_0f3254ad", mouth, "parth"]
    ws.store.save_player(ws.player)
    g.close()
    g = simlib.campaign(NAME, fresh=False)
    ws = g.scene
    check("(the save opened again in Parth holds the gone stop and the mouth among its towns)",
          ws.player.location == "parth" and "road_0f3254ad" in towns(ws) and mouth in towns(ws), (ws.player.location, towns(ws)))
    check("an older save reads right as it is: the town behind is Willowmead", behind(ws, ws.acting) == "willowmead", behind(ws, ws.acting))
    where, notes = recall(ws)
    check("...and Word of Recall takes the character there, past the stop and the mouth", where == "willowmead", (where, notes))
    g.close()

    # ---- a second character's own list (checklist 8)
    g, ws = fresh()
    other = simlib.stood_beside(ws, "second", location="willowmead")
    other.field = {"towns": ["eldervale", "road_0f3254ad", "parth", "willowmead"]}
    ws.fld["towns"] = ["willowmead", "parth"]
    check("the town behind is read from the character named: Parth for the second, Willowmead for the player",
          behind(ws, "second") == "parth" and behind(ws, ws.acting) == "willowmead", (behind(ws, "second"), behind(ws, ws.acting)))
    del ws.player_of
    g.close()
    g = None
finally:
    R.update(KEEP)
    if g is not None:
        g.close()
    shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
    shutil.rmtree(LOGS, ignore_errors=True)

print(f"\n{len(bad)} failed" if bad else "\nall passed", file=sys.__stdout__)
sys.exit(1 if bad else 0)
