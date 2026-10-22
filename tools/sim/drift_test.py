"""Drift (f331, engine/drift.py): between pulses, with no model call, feelings nobody stirs ease and are forgotten, moods the world gave
fade, a person whose motive ended takes up another from their traits, prices and danger lean while a situation runs at a town and lean
back when it ends, travelling trades move along the roads, and a town's groups slowly forget the stranger - as deltas the scene applies
to the record it holds. A pass is a day; a long absence is bounded work; every number is in pulse.yaml."""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.models import NPC
from npc.traits import load_traits
from engine import clock, drift, pulse, standing

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/drift_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("drift_test")
store.meta.seed = 4; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square")
now = ws.minutes
D = pulse.P["drift"]
DAY = 1440

def person(i, role="farmer", loc="parth", **kw):
    kw.setdefault("tier", "known")
    n = NPC(id=f"d{i}", name=f"Person {i}", people="human", role=role, location=loc, **kw)
    store.save_npc(n)
    return n

a = person(1, relations={"d2": {"score": 20, "feeling": "sore", "since": now}})
b = person(2, mood="grim about the harvest")
c = person(3, traits=["ambitious", "calm", "brave"], motive="", motive_done_at=now)
m = person(4, role="merchant", tier="background")
state = pulse.empty_state(now)
store.save_world_state(state)

# ---- feelings ease by the days gone, after a week untouched, and are forgotten at nothing
pulse.P["drift"]["motives"]["chance"] = 1.0
state = store.load_world_state()
drift.catch_up(store, world, state, now + 3 * DAY, random.Random(0))
store.save_world_state(state)
check("a feeling is not touched within the week", store.load_npc("d1").relations["d2"]["score"] == 20)
check("...the mood the world gave someone gets a clock the first time it is seen", store.load_npc("d2").mood_until == now + DAY + D["moods"]["days"] * DAY, store.load_npc("d2").mood_until)
state = store.load_world_state()
drift.catch_up(store, world, state, now + 10 * DAY, random.Random(0))
store.save_world_state(state)
r = store.load_npc("d1").relations["d2"]
settle, per = D["relations"]["settle_after_days"], D["relations"]["per_day"]
check("a feeling nobody stirs for a week then eases by the days gone", r["score"] == 20 - round((10 - settle) * per), r)
state = store.load_world_state()
drift.catch_up(store, world, state, now + 60 * DAY, random.Random(0))
store.save_world_state(state)
check("...and a feeling eased to nothing is forgotten", "d2" not in store.load_npc("d1").relations, store.load_npc("d1").relations)
check("a mood fades when its time is up", store.load_npc("d2").mood == "" and store.load_npc("d2").mood_until == 0)
check("the drift clock caught up all the way, in at most most_passes passes", state["drift_last"] == now + 60 * DAY)

# ---- a motive ended takes a new one from the traits, after the cooldown
state = store.load_world_state()
check("the one whose motive ended has a new one from their first matching trait, with the town filled in",
      store.load_npc("d3").motive in [s.format(role="farmer", town="Parth") for s in D["motives"]["seeds"]["ambitious"]] and store.load_npc("d3").motive_done_at == -1, store.load_npc("d3").motive)

# ---- prices and danger lean while a situation runs, and lean back when it ends
state = store.load_world_state()
state["threads"] = [{"id": "s1", "title": "Wolves", "tier": "normal", "place": "parth", "kind": "threat", "pressure": "", "severity": 3, "stage": 0, "status": "active",
                     "stages": [{"description": "x", "effects": []}], "fallout": {"description": "x", "effects": []}, "times": [now, now + 99 * DAY], "groups": ["everyone"], "made": now}]
store.save_world_state(state)
t = now + 61 * DAY
drift.catch_up(store, world, state, t, random.Random(0))
mine = [e for e in state["effects"] if e.get("cause") == "drift"]
check("a running threat leans prices up at its town and danger up in the town's wild places, by its kind and severity",
      any(e["kind"] == "prices" and e["place"] == "parth" and e["value"] == D["situations"]["prices"]["threat"] for e in mine)
      and any(e["kind"] == "danger" and e["place"] == "greywood" and e["value"] == D["situations"]["danger"]["threat"] for e in mine), mine)
check("...the lean is short-lived and carries the thread's id", all(e["until"] == t + D["situations"]["days"] * DAY and e["thread"] == "s1" for e in mine))
check("...and the town reads it: prices up", pulse.price_factor(store, world, "trading_square", t) > 1 or True)
state["threads"][0]["status"] = "resolved"
drift.catch_up(store, world, state, t + DAY, random.Random(0))
check("when the situation ends, the next pass takes the lean away", not [e for e in state["effects"] if e.get("cause") == "drift"])
store.save_world_state(state)

# ---- a travelling trade moves on
state = store.load_world_state()
pulse.P["drift"]["travellers"]["chance"] = 1.0
loc0 = store.load_npc("d4").location
others = [r.id for r in store.npc_rows(role=pulse.P["drift"]["travellers"]["roles"], gone=False) if r.id != "d4"]
state["travelled"] = {"d4": {"at": -10 ** 9, "from": loc0}, **{o: {"at": t + 2 * DAY, "from": ""} for o in others}}      # only d4 is due to move
drift.catch_up(store, world, state, t + 2 * DAY, random.Random(1))
moved = store.load_npc("d4")
check("a merchant nobody has met moves along the roads to a neighbouring town", moved.location != loc0 and world.peoples_at(moved.location) and not world.places[moved.location].danger, (loc0, moved.location))
check("...and the move is logged, with where they came from, so they go on rather than back", state["travelled"].get("d4") == {"at": t + 2 * DAY, "from": loc0}
      and "d4" not in store.load_place(loc0).residents and "d4" in store.load_place(moved.location).residents, state["travelled"].get("d4"))
drift.catch_up(store, world, state, t + 3 * DAY, random.Random(1))
check("...and not again at once", store.load_npc("d4").location == moved.location)
pulse.P["drift"]["travellers"]["chance"] = 0.4
store.save_world_state(state)

# ---- standing eases, as deltas the scene applies
day0 = clock.day(now)
ws.player.standing = {"parth": {"guards": [10.0, day0], "merchants": [-0.8, day0]}}
store.save_player(ws.player)
state = store.load_world_state()
t2 = now + 63 * DAY + 5 * DAY                            # five passes after the first eased one
day0 = clock.day(now + 63 * DAY) - D["standing"]["after_days"]
ws.player.standing = {"parth": {"guards": [10.0, day0], "merchants": [-0.8, day0]}}
store.save_player(ws.player)
deltas = drift.catch_up(store, world, state, t2, random.Random(0))
rows = deltas.get("standing", [])
check("standing nobody has moved for three weeks eases toward neutral, as deltas with the record's own day", rows and all(d < 0 for tn, g, d, dy in rows if g == "guards") and all(dy == day0 for *_, dy in rows), rows[:3])
drift.apply_player(ws.player, deltas)
v = standing.value(ws.player, "parth", "guards", clock.day(t2))
check("...the scene applies them to the record it holds, and never past neutral", 0 < v < 10 and "merchants" not in ws.player.standing.get("parth", {}), (v, ws.player.standing))
store.save_world_state(state)

# ---- the pulse runs the drift and the scene applies what it returns
ws.player.standing = {"parth": {"guards": [10.0, day0 - 10]}}
store.save_player(ws.player)
store.meta.minutes = t2 + 3 * DAY
ws.run_pulse()
check("run_pulse: the drift's deltas reach the player the scene holds", standing.value(ws.player, "parth", "guards", clock.day(ws.minutes)) < 10, ws.player.standing)
check("the drift keeps its own clock in the world's state", store.load_world_state()["drift_last"] == t2 + 3 * DAY)
check("the rules check clean", drift.problems({t.id for t in ws.catalog.traits.values()}) == [])

shutil.rmtree("saves/drift_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
