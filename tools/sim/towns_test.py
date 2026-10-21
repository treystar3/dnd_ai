"""Towns with identity (f316): a profile is loaded and checked against the map; the condition is read off the world's state - situations,
effects, losses, holidays - in a fixed order; the truth layer hands the character, the condition and the landmarks to every reader; the
people made in a town are told what it is like."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world, Town, WorldError, _check_towns
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import truth, towns, pulse, clock
from npc import prompts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/towns_test", ignore_errors=True)
world = load_world()
prof = world.towns["parth"]
check("Parth has a profile, and its places find it", prof.id == "parth" and world.town("trading_square") is prof and world.town("greywood") is None)
check("...the profile's scale, crowd, guard and districts are written onto the place", world.places["parth"].districts == prof.districts
      and world.places["parth"].crowd["market"] == prof.crowd["market"] and world.places["parth"].guard == "light")

# ---- checking a profile against the map
def problems_of(**changes):
    raw = prof.model_dump(); raw.update(changes)
    w = {"towns": {"parth": Town(**raw)}, "places": world.places, "roles": world.roles}
    out = []
    _check_towns(w, out)
    return out
check("a landmark must stand at one of the town's places", any("landmark" in p for p in problems_of(landmarks=[{"name": "x", "where": "greywood"}])))
check("an anchor must be a role the town has", any("anchor role" in p for p in problems_of(anchors=[{"role": "miner"}])))
check("a festival must be on the calendar", any("festival" in p for p in problems_of(festivals=[{"name": "x", "season": "monsoon", "day": 1}])))
check("a scale and a guard word must be ones the truth layer knows", any("scale" in p for p in problems_of(scale="megalopolis")) and any("guard" in p for p in problems_of(guard="army")))
check("...and a good profile passes", not problems_of())

# ---- the condition, from the world's state
store = CampaignStore.open_or_create("towns_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(3))
char.level = 3
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square")
now = ws.minutes
state = store.load_world_state()
state["effects"] = []; state["threads"] = []
store.save_world_state(state)
check("a town with nothing going on is calm", towns.condition(store, world, "trading_square", now).name == "calm")

def with_effect(kind, value, place="parth", days=3):
    st = store.load_world_state()
    st["effects"] = [e for e in st["effects"] if e["kind"] != kind] + [{"kind": kind, "place": place, "value": value, "until": now + days * 1440, "cause": "test"}]
    store.save_world_state(st)
with_effect("danger", 30, place="south_fields")
c = towns.condition(store, world, "trading_square", now)
check("danger up a little makes the town uneasy, from any of its places", c.name == "uneasy" and "30%" in c.why, (c.name, c.why))
with_effect("danger", 70, place="south_fields")
c = towns.condition(store, world, "trading_square", now)
check("danger up a lot makes it besieged, and the streets empty", c.name == "besieged" and c.crowd, (c.name, c.crowd))
with_effect("danger", 0)
with_effect("prices", 30)
check("prices up makes it hungry", towns.condition(store, world, "trading_square", now).name == "hungry")
with_effect("prices", -15)
check("prices down makes it prospering", towns.condition(store, world, "trading_square", now).name == "prospering")
with_effect("prices", 0)

st = store.load_world_state()
st["threads"] = [{"id": "t1", "title": "Wolves at the sheep hill", "tier": "normal", "place": "parth", "pressure": "wolves_in_greywood", "stage": 0, "status": "active",
                  "stages": [{"description": "Sheep are going missing at night.", "effects": []}], "times": [now, now + 1440], "groups": ["everyone"]}]
store.save_world_state(st)
pk = world.pressures.get("wolves_in_greywood")
if pk is None:                                                   # the pressure id is whatever Parth's threat is called
    pk = next(p for p in world.pressures.values() if p.place in ("parth", "greywood") and p.kind == "threat")
    st["threads"][0]["pressure"] = pk.id; store.save_world_state(st)
c = towns.condition(store, world, "guild_house", now)
check("a threat running at the town makes it uneasy, and says which", c.name == "uneasy" and c.why == "Wolves at the sheep hill", (c.name, c.why, pk.id))
st["threads"][0]["tier"] = "campaign"; store.save_world_state(st)
check("...a campaign-sized threat besieges it", towns.condition(store, world, "guild_house", now).name == "besieged")
st["threads"] = []; store.save_world_state(st)

store.journal(now - 1440, "npc_gone", "", "x1", "Old Tam is gone: killed by wolves on the sheep hill", {"how": "killed by wolves on the sheep hill", "place": "parth"})
c = towns.condition(store, world, "trading_square", now)
check("someone of the town killed lately puts it in mourning", c.name == "mourning" and "Old Tam" in c.why, (c.name, c.why))
store.journal(now - 600, "npc_gone", "", "x2", "Pell is gone: moved to the capital for work", {"how": "moved to the capital for work", "place": "kelpmoor"})
check("...a loss elsewhere, or a leaving, does not", towns.condition(store, world, "kelpmoor", now).name == "calm")
with_effect("danger", 70, place="parth")
check("a siege outranks mourning", towns.condition(store, world, "trading_square", now).name == "besieged")
with_effect("danger", 0)

# ---- the calendar
f = prof.festivals[0]
season_i = pulse.P["seasons"]["order"].index(f.season)
fair_day = season_i * pulse.P["seasons"]["days_each"] + f.day
fair_minute = (fair_day - 1) * 1440 + 120                       # day fair_day, two hours after waking
check("the town's own holiday is read off the calendar", towns.festival_today(world, "trading_square", fair_minute) == f.name
      and towns.festival_today(world, "trading_square", fair_minute + f.days * 1440) == "", (clock.day(fair_minute), fair_day))
c = towns.condition(store, world, "trading_square", fair_minute)
check("...and the town is festive, with full streets", c.name == "festive" and "throng" in c.crowd and c.why == f.name, (c.name, c.why))
store.journal(fair_minute - 1440, "npc_gone", "", "x3", "Hob is gone: died of a fever", {"how": "died of a fever", "place": "parth"})
check("...mourning outranks a holiday", towns.condition(store, world, "trading_square", fair_minute).name == "mourning")

# ---- through the truth layer
ws.enter("trading_square")
ws.store.meta.turn += 1
sc = truth.scene_of(ws)
nv = sc.view(truth.NARRATOR, "narrator")
check("the narrator is given the town's condition and the landmarks here", any(l.startswith("The town right now (mourning)") for l in nv.streets())
      and any("the well" in l for l in nv.streets()), nv.streets())
tv = sc.view(truth.INTERPRETER, "interpreter").lines("town")
check("the town facet opens with the character and the condition", tv[0].startswith("Parth: A river-crossing market town") and tv[1].startswith("the town is mourning"), tv[:2])
check("the town's named things are names a speaker may use", {"wend", "bridge", "granary", "sunburst", "sheep", "hill", "harvest", "fair"} <= sc.known_words())
check("the crowd line is the condition's while it holds", any("keep to their own" in l for l in nv.streets()), nv.streets())

# ---- the people made here are told about the town
lines = towns.resident_lines(world, "trading_square", towns.condition(store, world, "trading_square", now))
check("residents are told the character, the condition and the trouble", len(lines) == 3 and lines[0].startswith("THE TOWN:") and "mourning" in lines[1] and "UNDERNEATH" in lines[2], lines)
req = prompts.residents_request(world.places["trading_square"], world.summary, [("baker", "bakes", "human", "Ada", "woman")], lines)
check("...and the request carries them", "THE TOWN:" in req and "RIGHT NOW IN TOWN" in req)
check("a place without a profile says nothing of the kind", towns.resident_lines(world, "kelpmoor", None) == [] and towns.thread_lines(world, "kelpmoor") == [])
tl = towns.thread_lines(world, "parth", big=True)
check("the situation writer is told the trouble, and the secret only for a big one", any(l.startswith("WHAT IS WRONG") for l in tl) and any("SECRET" in l for l in tl)
      and not any("SECRET" in l for l in towns.thread_lines(world, "parth")))

shutil.rmtree("saves/towns_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
