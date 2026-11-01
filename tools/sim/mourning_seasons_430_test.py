"""(f430) What the f425 night showed of the world's facts: three towns hung black cloth for bandit captives who had slipped their bonds
("the town's collective mourning for Brannoc"; "Dorn's passing"; "Teague's passing"), because whether someone's leaving was a death was
read from the meaning of the words, and 'got away' passed; and summer nights were 'freezing' (244 frosts on one run), because the
weather never reckoned the season. Now the game says whether a removal is a death, a captive outlaw is no town's to grieve, and the
season moves the temperature."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 30))
from engine import clock, pulse, towns, weather
from storage.campaign import CampaignStore
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/mourning_430_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("mourning_430_test")
store.meta.seed = 30; store.meta.minutes = 600; store.save_meta()
from npc.models import NPC
def person(pid, name, role="farmer", place="parth"):
    n = NPC(id=pid, name=name, people="human", role=role, location=place)
    store.save_npc(n)
    return n
places = towns.town_places(world, "parth")
now = 2000
pulse.remove_npc(store, world, person("brannoc", "Brannoc"), "slipped their bonds and got away", 1900, dead=False, mourned=False)
check("a captive who got away is no one's grief", towns._lost_lately(store, world, places, now, 7) == "")
pulse.remove_npc(store, world, person("dorn", "Dorn"), "put to the sword by the stranger", 1950, dead=True, mourned=False)
check("...nor an outlaw captive put to the sword", towns._lost_lately(store, world, places, now, 7) == "")
pulse.remove_npc(store, world, person("varn", "Varn Tolley"), "moved on along the road", 1960, dead=False)
check("someone who moved on is not mourned", towns._lost_lately(store, world, places, now, 7) == "")
pulse.remove_npc(store, world, person("ella", "Ella Marsh"), "killed defending Parth against the raiders", 1970, dead=True)
check("one of the town killed is mourned, by name", towns._lost_lately(store, world, places, now, 7) == "Ella Marsh",
      towns._lost_lately(store, world, places, now, 7))
row = store.journal_tail(1, kind="npc_gone")[-1]
check("...and the journal row says it was a death", (row.get("data") or {}).get("dead") is True, row)
from pathlib import Path
src = Path("scenes/arc_actions.py").read_text(encoding="utf-8")
check("a captive dropped from the player's hands is never the town's grief", 'mourned=False' in src[src.index("def drop_prisoner("):src.index("def drop_prisoner(") + 1200])

# ---- the season moves the temperature
temps = weather.RULES["temperatures"]
def season_start(name):
    order = __import__("engine.pulse", fromlist=["P"]).P["seasons"]["order"]
    return (order.index(name) * pulse.P["seasons"]["days_each"]) * 1440
summer, winter = season_start("summer"), season_start("winter")
check("the season is known where the weather is", clock.season(summer + 600) == "summer" and clock.season(winter + 600) == "winter")
summer_nights = {weather.temperature(30, summer + d * 1440 + 3 * 60) for d in range(30)}
winter_noons = {weather.temperature(30, winter + d * 1440 + 14 * 60) for d in range(30)}
check("a summer night is never freezing", "freezing" not in summer_nights, summer_nights)
check("a winter afternoon is never warm or hot", not ({"warm", "hot"} & winter_noons), winter_noons)
check("...and summer is warmer than winter at the same hour", max(temps.index(t) for t in summer_nights) > min(temps.index(t) for t in
      {weather.temperature(30, winter + d * 1440 + 3 * 60) for d in range(30)}))

store.close()
shutil.rmtree("saves/mourning_430_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
