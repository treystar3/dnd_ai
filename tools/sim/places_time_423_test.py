"""(f423) Places, time and the world, as the f395 night showed them. A passage wrote 'on day 42' (the day number was in the time line);
'Fog comes in.' was said in the inn's bar; the moment writer was told the weather twice; a road stop near the end of a resumed journey
was 'the way between Hrimgard and Hrimgard', and the old stop and its people were never tidied away; THE WORLD NOW gave raw place ids; the
road writer was asked about 'a traveler'; a revisit line read as the player's own deed; a mourning town mourned no one by name; every
passage was asked to end on a beat inviting the player to act; and 'People go about their day.' was a line of the story."""
import pathlib, random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 13))
import ui.console as uc
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import doings, road_prompts, roads, stay, towns
from npc.traits import load_traits
from scenes import voice
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/places_time_423_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("places_time_423_test")
store.meta.seed = 13; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(13))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("tilted_plough")

check("the time the writers are given has no day number", not re.search(r"\bday \d+", ws.time_label()), ws.time_label())

# ---- weather, inside and out
def turned(place, before, after):
    ws.enter(place)
    ws.__dict__["_stay"] = dict(stay.snapshot(ws), weather=before)
    real = stay.snapshot
    stay.snapshot = lambda w: dict(real(w), weather=after)
    try:
        return stay.tick(ws, narrated=False, rng=random.Random(1))
    finally:
        stay.snapshot = real
inside = turned("tilted_plough", "clear", "fog")
check("fog coming in is not told inside the inn", inside != stay.S["weather"]["fog"], inside)
check("...rain is told as it is heard from indoors", turned("tilted_plough", "clear", "rain") == stay.S["weather_in"]["rain"])
check("...and outside, as before", turned("parth", "clear", "fog") == stay.S["weather"]["fog"])
from engine import moment_prompts
src = pathlib.Path("engine/moment_prompts.py").read_text(encoding="utf-8")
check("the moment writer is told the weather once", src.count("weather") <= 2 and "{ws.time_label()}\\n" in src.replace("\\\\n", "\\n"))

# ---- roads
stop = roads.make_stop(world, "parth", "riverhaven", 0.5, 120, "x", "", "t")
check("a stop is named by the road between two towns", "between" in stop["place"]["name"] and "Parth" in stop["place"]["name"], stop["place"]["name"])
world.places[stop["id"]] = __import__("world.loader", fromlist=["Place"]).Place(**stop["place"])
again = roads.make_stop(world, stop["id"], "parth", 0.9, 30, "y", "", "t2")
name = again["place"]["name"]
check("a stop on a journey resumed from a stop near its end is never 'between X and X'", not re.search(r"between (\w[\w ']*) and \1\b", name), name)
rsrc = pathlib.Path("scenes/road_actions.py").read_text(encoding="utf-8")
check("the stop the player stood at is tidied away before a new one is set", "self.leave_road(stop[\"id\"])" in rsrc)
check("THE WORLD NOW names a matter's place, not its id", "self.where_name(t['place'])" in rsrc)
check("the road writer is asked about the player, never 'a traveler'", "a traveler" not in road_prompts.SYSTEM and "the traveler" not in rsrc)

# ---- the town and its people
n = types.SimpleNamespace(label=lambda: "the innkeeper")
line = doings.changed_lines([(n, "wiping the bar", "stacking chairs")])
check("a revisit line cannot read as the player's own deed", line and "on the player's last visit" in line[0] and "as when the player" not in line[0], line)
cond = towns.Condition("mourning", "Varn Tolley lost lately", "black cloth on the doors", "")
check("a mourning town names whom it mourns", "Varn Tolley" in towns.mourned(cond))
check("...and only a mourning one", towns.mourned(towns.Condition("hungry", "prices up 32%", "bread is dear", "")) == "")
tsrc = pathlib.Path("engine/truth.py").read_text(encoding="utf-8")
check("...to the narrator too", "mourned(cond)" in tsrc)
check("no passage is asked to end on a beat inviting the player to act", "end on a beat" not in voice.DM_VOICE)

# ---- the wait's words
lsrc = pathlib.Path("npc/life.py").read_text(encoding="utf-8")
check("'People go about their day.' is the waiting indicator's words, never a line of the story",
      'console.busy_text("People go about their day.")' in lsrc and 'console.wait("People go about their day.")' not in lsrc)
from ui.gui import bridge
b = bridge.Bridge.__new__(bridge.Bridge)
sent = []
b.emit = lambda **k: sent.append(k)
b.busy_text("People go about their day.")
b.busy(True); b.busy(False); b.busy(True)
check("...the window's indicator shows them for that wait, and then its own words again", sent[0].get("text") == "People go about their day."
      and sent[2].get("text") == "", sent)
js = pathlib.Path("ui/gui/web/app.js").read_text(encoding="utf-8")
check("...and the page sets them", "setBusy(ev.on, ev.text)" in js)

store.close()
shutil.rmtree("saves/places_time_423_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
