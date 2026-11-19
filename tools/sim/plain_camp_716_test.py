"""(f716) A camp anyone can make (the owner, 2026-11-16: option A of docs/design/25_speech_parts_camp.md, "Yes, build all three"). In the
third blind play "We make camp by the pool and sleep until morning" made no camp: a camp was only an ability's shelter, and the rest
line offered every player one. Sleeping in the open on the Ironcrown Peaks drew three attacks in three hours.
Held here: a sleep in the wilds whose line asks to make camp makes a plain camp first (field.yaml plain_camp: its minutes), told so,
and the night is the full rest it promises; while asleep in a plain camp the chance of being found is the share field.yaml gives;
an ability's shelter camp is still the better one (nothing finds it); a line that asks for no camp sleeps rough as before; a town
makes no camp.
Run: python tools/sim/plain_camp_716_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
import ui.console as uc
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(str(m)))
from llm.contracts import ActionIntent as A
from engine import encounters, pools
import scenes.world as W

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("camp_716", seed=4, location="parth")
ws = g.scene
wild = next(pid for pid, p in ws.world.places.items() if p.danger and p.type not in ("dungeon", "road") and not p.parent)
ws.enter(wild)
F = W.field_rules() if hasattr(W, "field_rules") else None
asked = []
real_roll = encounters.roll
encounters.roll = lambda store, world, loc, chance, rng, **k: (asked.append(chance), None)[1]


def night(text, camp=None):
    ws.fld.pop("camp", None)
    if camp:
        ws.fld["camp"] = camp
    c = ws.player.character
    c.health = 1
    asked.clear(); NOTES.clear()
    m0 = ws.minutes
    ws.on_wait(A(kind="wait", wait_until="morning", summary="sleep"), text)
    return m0, c


base = encounters.E["chance_per_hour"]
m0, c = night("We make camp here and sleep until morning.")
woke = ws.minutes
camp = ws.fld.get("camp") or {}
check("a sleep in the wilds that asks to make camp makes a plain camp first, told so", camp.get("plain") and any("camp" in n.lower() for n in NOTES[:2]),
      (camp, NOTES[:2]))
check("...and the night is the full rest it promises", c.health == pools.maximum(c, "health") and not any("only a rest" in n or "rest, not" in n for n in NOTES), NOTES)
check("...while asleep in it the chance of being found is the share field.yaml gives", asked and all(abs(a - base * ws.plain_camp()["share"]) < 1e-9 for a in asked),
      (asked[:3], base))
m2, c = night("We sleep until morning.")
check("a sleep in the wilds that asks for no camp sleeps rough, at the full chance, told why it was not a full night",
      not (ws.fld.get("camp") or {}).get("plain") and asked and all(abs(a - base) < 1e-9 for a in asked)
      and any("make camp" in n for n in NOTES), (asked[:3], NOTES[-2:]))
m3, c = night("We sleep until morning.", camp={"loc": ws.player.location, "pos": ws.camp_pos(), "until": ws.minutes + 2000})
check("an ability's shelter camp is still the better one: nothing finds it", not asked and c.health == pools.maximum(c, "health"), asked)
check("making the camp takes its time, and it comes out of the night: the sleep still ends in the morning",
      camp.get("until", 0) - ws.plain_camp()["lasts_minutes"] - m0 == ws.plain_camp()["minutes"]
      and __import__("engine.clock", fromlist=["period"]).period(woke) in ("morning", "dawn"), (camp, m0, woke))
from engine import world_improv
for line in ("We sleep near the bandit camp in the hills.", "We don't make camp, just sleep on the ground.", "We strike camp and sleep.",
             "We bed down by the fire.", "Where can we camp?", "We sleep with no camp."):
    check(f"no camp is made for a line that does not ask for one: {line!r}", not world_improv.asks_camp(line))
for line in ("We pitch our tent and sleep.", "We camp for the night.", "We make camp by the pool and sleep until morning.", "We'll camp here.",
             "I'll camp by the stream.", "Camp here for the night.", "We set camp by the pool.", "No one sees us as we make camp."):
    check(f"...and one is for a line that does: {line!r}", world_improv.asks_camp(line))
ws.fld.pop("camp", None)
NOTES.clear()
ws.on_other(A(kind="other", summary="make camp"), "We make camp.")
check("'We make camp.' alone, read as an act of its own, makes the camp: never a gamble, told", (ws.fld.get("camp") or {}).get("plain")
      and any("camp" in n.lower() for n in NOTES), (ws.fld.get("camp"), NOTES))
ws.fld.pop("camp", None)
c = ws.player.character
c.health = 1
NOTES.clear()
asked.clear()
m4 = ws.minutes
ws.on_other(A(kind="other", summary="make camp and sleep"), "We make camp by the pool and sleep until morning.")
check("'We make camp and sleep.', read as an act, makes the camp and sleeps the night in it: the full rest",
      (ws.fld.get("camp") or {}).get("plain") and c.health == pools.maximum(c, "health") and ws.minutes - m4 >= 360, (ws.minutes - m4, c.health, NOTES))
ws.enter("parth")
NOTES.clear()
night("We make camp here and sleep until morning.")
check("a town makes no camp", not (ws.fld.get("camp") or {}).get("plain"), ws.fld.get("camp"))
encounters.roll = real_roll
g.close()
shutil.rmtree("saves/camp_716", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
