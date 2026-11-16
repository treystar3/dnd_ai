"""(f661) What the engine decides against or beside what the player asked is said to the player, in the game's own voice, whether
or not the passage says it (docs/design/21_play_faults_plan.md, group C; found in play: docs/play/2026-11-15_play_findings.md 4.4,
4.5, 4.11, 6.4). An attack on a foe out of reach became a walk with no word why; three hours of searching found nothing and only the
passage said so; a flight was one hidden roll; a night with no room was not a full rest and nothing said why.
Held here: one mechanism (engine/told.py, the lines in data/rules/told.yaml, several a kind, checked at start-up) and each of those
sites raising its line: the approach (a plain attack and an ability), the search that found nothing, the flight with its chance in
words (never a figure), the rest with no bed; and the lines not raised where the engine did what was asked.
Run: python tools/sim/told_661_test.py"""
import re
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import ui.console as uc
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(m))
for fn in ("narrate", "ledger"):
    uc.put(fn, lambda *a, **k: None)
from engine import battlefield, combat, data_check, told
from llm.contracts import ActionIntent
from services.fight import RoundIntent
from scenes import combat_scene as cs

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


def of(kind, said) -> bool:
    """Is one of this kind's lines in what was said (its facts aside)?"""
    pats = [re.escape(l).replace(r"\{", "{").replace(r"\}", "}") for l in told.T[kind]]
    pats = [re.sub(r"\{\w+\}", ".+?", p) for p in pats]
    return any(re.search(p, s, re.I) for p in pats for s in said)


check("the lines are checked at start-up, and none is wrong", told.problems() == [] and "told.problems()" in open("engine/data_check.py").read())
check("...a kind with no lines is caught", told.problems({"approach": []}) != [])
check("...a dash in a line is caught", told.problems({"approach": ["a" + chr(0x2014) + "b"]}) != [])
check("each kind has several lines", all(len(v) >= 3 for k, v in told.T.items() if k not in told.WORDS))
check("a chance is said in words, never a figure", told.odds(10) == "a long chance" and told.odds(90) == "all but sure"
      and not re.search(r"\d", told.say("flight_odds", 0, odds=told.odds(40))))

g = simlib.campaign("told_661_test", seed=5, location="greywood")
ws, world = g.scene, g.scene.world


def scene(far=False):
    me = combat.fighter_from_character(ws.player.character)
    wolf = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "e0", "wolf 1")
    fight = combat.Combat(fighters=[me, wolf], place="greywood")
    if far:
        import random
        from engine import battlefield_builder as bb
        fight.battlefield = bb.build("forest", random.Random(4))
        while len(fight.battlefield.zones) < 3:
            fight.battlefield = bb.build("forest", random.Random(random.randrange(999)))
        battlefield.place_fighters(fight)
        battlefield.enter_zone(fight, wolf, max(fight.battlefield.zones, key=lambda z: fight.battlefield.steps(me.zone_id, z)))
    else:
        battlefield.engage(fight, wolf, fight.player)
    fight.round = 1
    sc = cs.CombatScene(ws, fight, "wolf")
    ws.combat = sc
    return sc, fight, wolf


sc, f, wolf = scene(far=True)
zones = {getattr(x, "zone_id", "") for x in f.fighters}
out = sc.service.round(f, RoundIntent(kind="attack", target="e0"))
check("4.4: an attack on a foe out of reach is said to be spent closing on them", of("approach", out.notes) and "wolf 1" in " ".join(out.notes).lower(),
      (out.notes, zones, [x.zone_id for x in f.fighters]))
sc, f, wolf = scene()
out = sc.service.round(f, RoundIntent(kind="attack", target="e0"))
check("...and not when the foe is in reach", not of("approach", out.notes), out.notes)
sc, f, wolf = scene()
out = sc.service.round(f, RoundIntent(kind="flee"))
check("4.11: a flight says how likely it was, in words", of("flight_odds", out.notes) and not re.search(r"\d+\s*%", " ".join(out.notes)), out.notes)
ws.combat = None

ws.enter("trading_square")
NOTES.clear()
ws.player.room, ws.player.room_until = "", 0
ws.on_wait(ActionIntent(kind="wait", wait_minutes=8 * 60), "I sleep under the pines")
check("6.4: a night's sleep with no bed says why it was not a full rest", of("rest_no_bed", NOTES), NOTES)
NOTES.clear()
ws.on_wait(ActionIntent(kind="wait", wait_minutes=60), "I rest a while")
check("...and a short rest, which is no night, says nothing of it", not of("rest_no_bed", NOTES), NOTES)

wild = next(p.id for p in world.places.values() if p.type not in ("road", "dungeon", "city", "town", "village") and not p.parent and p.danger)
ws.enter(wild)
NOTES.clear()
ws.rng.random = lambda: 0.999
ws.on_explore(ActionIntent(kind="explore", seek="the lost tomb of Kael Varos"), "I search far and wide for the lost tomb of Kael Varos")
check("4.5: a search that finds nothing says so, with the time it took", of("search_failed", NOTES) and "kael varos" in " ".join(NOTES).lower(), NOTES)
shutil.rmtree("saves/told_661_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
