"""(f351) The room changes while the player is in it: one line a turn for the one change worth telling, when the narrator did not write."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import clock, stay, weather
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
wx = {c["id"] for c in weather.RULES["conditions"]}
check("the lines are data, one per weather and per period", stay.problems(wx, set(clock.PERIOD_NAMES)) == [] and set(stay.S["weather"]) == wx, stay.problems(wx, set(clock.PERIOD_NAMES)))
shutil.rmtree("saves/stay_test", ignore_errors=True)
store = CampaignStore.open_or_create("stay_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
told = []
console.narrate = lambda text: told.append(text)
console.note = lambda text: None
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.player.mentor["never"] = True
ws.enter("tilted_plough")
rng = random.Random(1)
check("arriving starts the stay: nothing to tell yet", stay.tick(ws, rng=rng) == "")
# someone comes in
guest = next(n for n in store.load_npc(i) for i in [] ) if False else None
other = [n for n in ws.residents if n not in ws.present] or [n for n in ws.residents]
newcomer = next((n for n in store.npc_rows(location="parth") if n.id not in {p.id for p in ws.present}), None)
if newcomer:
    v = store.load_npc(newcomer.id); v.activity = "warming his hands"
    ws.present.append(v)
    ws.store.meta.turn += 1
    line = stay.tick(ws, rng=rng)
    check("someone coming in gets a line, with them as the player knows them", v.label() in line.lower() or v.label()[0].upper() + v.label()[1:] in line, line)
    ws.store.meta.turn += 1
    ws.present.remove(v)
    check("...and the next change about people waits the gap", stay.tick(ws, rng=rng) == "")
    ws.store.meta.turn += 3
    v2 = store.load_npc(newcomer.id); ws.present.append(v2)
    ws.present.remove(v2)
    # a departure of someone who was there
    gone = ws.present[0]
    ws.present.remove(gone)
    line = stay.tick(ws, rng=rng)
    check("after the gap, someone going out gets a line", "gone" in line or "goes out" in line, line)
    ws.present.insert(0, gone)
# the weather turns
m0 = ws.minutes
turn_at = next(m for m in range(m0, m0 + 1440 * 4, 15) if weather.condition(3, m)["id"] != weather.condition(3, m0)["id"])
stay.reset(ws)
store.meta.minutes = turn_at; ws.store.meta.turn += 1
line = stay.tick(ws, rng=rng)
inside = ws.place.type in stay.S.get("indoors", [])                     # (f423) told as it is heard from indoors, when there is such a line
want = stay.S["weather_in" if inside and weather.condition(3, turn_at)["id"] in stay.S.get("weather_in", {}) else "weather"].get(weather.condition(3, turn_at)["id"], "")
check("the weather turning is told, in the line for what it turns to", line == want or (inside and not want), line)
# the hour turns
stay.reset(ws)
m1 = ws.minutes
nxt = next(m for m in range(m1, m1 + 600, 15) if clock.period(m) != clock.period(m1) and weather.condition(3, m)["id"] == weather.condition(3, m1)["id"])
store.meta.minutes = nxt; ws.store.meta.turn += 1
line = stay.tick(ws, rng=rng)
check("the hour turning is told", line == stay.S["periods"][clock.period(nxt)], line)
# the narrator wrote this turn: nothing
stay.reset(ws)
store.meta.minutes = next(m for m in range(nxt, nxt + 600, 15) if clock.period(m) != clock.period(nxt)); ws.store.meta.turn += 1
check("when the narrator wrote this turn, its passage is the update: no line", stay.tick(ws, narrated=True, rng=rng) == "")
# ...and the scene knows the narrator wrote by a flag the turn resets, not by a turn number (handle() moves the counter at its end: the
# 1720 run printed 'The door goes, and it is the broker' under a passage that had already sat him at his table)
import inspect
src = inspect.getsource(WorldScene.turn)
check("the turn clears the narrator's mark before handling the line", "self._wrote_turn = False" in src and src.index("_wrote_turn = False") < src.index("self.handle(text)"))
stay.reset(ws)
told.clear()
store.meta.minutes = next(m for m in range(ws.minutes, ws.minutes + 600, 15) if clock.period(m) != clock.period(ws.minutes)); ws.store.meta.turn += 1
ws._wrote_turn = True
ws.stay_tick()
check("the scene's own tick: nothing when the narrator wrote this turn, whatever the turn counter says", told == [], told)
ws._wrote_turn = False                                                     # the snapshot moved on with that tick: the next change is the next hour
store.meta.minutes = next(m for m in range(ws.minutes, ws.minutes + 600, 15) if clock.period(m) != clock.period(ws.minutes)); ws.store.meta.turn += 1
ws.stay_tick()
check("...and the line when the narrator did not", len(told) == 1 and told[0] == stay.S["periods"][clock.period(ws.minutes)], told)
# a moment ending
stay.reset(ws)
st = store.load_place(ws.player.location)
st.moment = {"id": "game", "title": "the dice by the hearth", "until": ws.minutes + 60, "line": "x", "doings": {}}
store.save_place(st)
stay.reset(ws)
st.moment = {}; store.save_place(st); ws.store.meta.turn += 1
line = stay.tick(ws, rng=rng)
check("a moment ending is told in its shape's own words", "game breaks up" in line, line)
check("every moment shape says how it ends", all(sh.get("ends") for sh in __import__("engine.moments", fromlist=["M"]).M["shapes"]))
# the player's own prisoner is not the room's: bound at their side, never "gone out" (27 of 46 room lines in one run were a captured
# bandit the player was escorting), and present whatever the hour or the door
cap = ws.residents[0]
ws.player.prisoners[cap.id] = {"escort": True, "deal": False, "asked": 0}
from engine import entities as _entities                                  # (f392) a captive is one in the registry, escorted
_entities.begin(ws.store, "captive", f"captive:{cap.id}", cap.name, ws.minutes, owner="player", links={"npc": cap.id})
if cap not in ws.present:
    ws.present.append(cap)
stay.reset(ws)
ws.present.remove(cap)
ws.store.meta.turn += 5
told.clear(); ws._wrote_turn = False
check("a prisoner the player escorts leaving the room is no line", stay.tick(ws, rng=rng) == "" and cap.id not in stay.snapshot(ws)["present"])
cap.away_until = ws.minutes + 1000
ws.refresh_present()
check("...and they are present whatever the filters say, while the player holds them", any(p.id == cap.id for p in ws.present))
del ws.player.prisoners[cap.id]; cap.away_until = 0
# moving places starts over
stay.reset(ws); ws.enter("parth"); ws.store.meta.turn += 1
check("a new place starts the stay over: nothing to tell", stay.tick(ws, rng=rng) == "")
# through a whole turn
told.clear()
ws.enter("tilted_plough")
nb = next((n for n in store.npc_rows(location="parth") if n.id not in {p.id for p in ws.present}), None)
if nb:
    ws.store.meta.turn += 4
    ws.present.append(store.load_npc(nb.id))
    ws.stay_tick()
    check("the scene prints the line and remembers it", told and told[-1] == ws.recent_narration[-1] and nb.label().split()[-1] in told[-1].lower(), told[-1:])
shutil.rmtree("saves/stay_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
