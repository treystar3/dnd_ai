"""(f696) A narrator is told a foe by its name, never by the game's tag (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). On the King's Road to Willowmead the ambush passage read "a swarm of beetles (elite) surges
forward": the road's happening was handed the fighters' names as the fight keeps them, "(elite)" and all. The fight's own lines
(combat.who) already took the tag off; the road's ambush and a creature sighted at a distance did not.
Held here: combat.plain_name takes the game's tags off a name ("(elite)", "(bounty)", one or several); the road's ambush and a sighting
name their foes plainly; the name the fight keeps (and the game's own notes and panes show) is left as it was.
Run: python tools/sim/plain_foe_696_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from engine import combat, encounters
from llm.gateway import LLMError
import scenes.road_actions as ra

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


check("a tag comes off", combat.plain_name("swarm of beetles (elite)") == "swarm of beetles")
check("...and two", combat.plain_name("pegasus (elite) (bounty)") == "pegasus")
check("...and a plain name stays", combat.plain_name("bandit captain") == "bandit captain")

g = simlib.campaign("plain_foe_696", seed=5, location="greywood")
ws = g.scene
ws.enter("greywood")
world = ws.world
beetle = world.bestiary.get("beetle_swarm") or next(iter(world.bestiary.values()))
elite = [combat.fighter_from_creature(beetle, 2, "elite", "e1", f"{beetle.name.lower()} (elite)")]
real_roll = encounters.roll
encounters.roll = lambda *a, **k: (beetle, [f.model_copy(deep=True) for f in elite])

road = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places and ra.roads.nearby_wilds(world, r.from_, r.to))
prompts = []
real_gen = ra.generate
ra.generate = lambda task, system, user, *a, **k: (prompts.append(user), (_ for _ in ()).throw(LLMError("test")))[1]
saved = {k: ra.R[k] for k in ("hostile", "hostile_max")}
ra.R["hostile"], ra.R["hostile_max"] = 100.0, 1.0
real_temp, real_det = ws.temperament, ws.deterred
ws.temperament, ws.deterred = (lambda c, high=None: "aggressive"), (lambda c, high=None: False)
ws.road_event([road.from_, road.to], road.from_, road.to, 120, 0.5, "I walk on", [])
said = prompts[-1] if prompts else ""
check("the road's ambush names its foes without the game's tag", said and "(elite)" not in said and beetle.name.lower() in said.lower(), said[-600:])

ws.temperament = lambda c, high=None: "passive"
events = []
ws.narrate_with = lambda system, event, *a, **k: events.append(event)
ws.maybe_encounter(1.0, "While searching,")
check("a creature sighted at a distance is named plainly", events and "(elite)" not in events[-1] and beetle.name.lower() in events[-1].lower(), events)
check("...while the name the fight keeps is left as it was", ws.wildlife and ws.wildlife[1][0].name.endswith("(elite)"), ws.wildlife)
from engine import truth
seen = [p for p in truth.scene_of(ws).present_people() if p.id == "wildlife"]
check("...and every later turn's who-is-here names it plainly too", seen and "(elite)" not in seen[0].label and "(elite)" not in seen[0].name,
      [(p.name, p.label) for p in seen])
check("a counter is the game's too: 'wolf 2' is a wolf to a narrator", combat.plain_name("wolf 2") == "wolf" and combat.plain_name("wolf 2 (elite)") == "wolf")
check("...while the fight's own lines keep it as an ordinal", combat.who(combat.fighter_from_creature(beetle, 2, "normal", "e2", "wolf 2")) == "the second wolf")
dead = combat.fighter_from_creature(beetle, 2, "elite", "e1", "giant rat (bounty)")
fight = combat.Combat(fighters=[dead])
combat.raise_thrall(fight, dead)
risen = [f.name for f in fight.fighters if f.side == "ally"]
check("a risen bounty is no '(bounty)'", risen and "(bounty)" not in risen[0] and "giant rat" in risen[0], risen)

ra.generate = real_gen
ra.R.update(saved)
ws.temperament, ws.deterred = real_temp, real_det
encounters.roll = real_roll
g.close()
shutil.rmtree("saves/plain_foe_696", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
