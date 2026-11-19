"""(f670) The smaller of D8 (docs/design/21_play_faults_plan.md; found in play: docs/play/2026-11-15_play_findings.md 2.12, 2.15, 2.17,
4.4): a nickname comes with its reason, so a hire asked why does not invent "you named yourself"; a found cache is told as taken, so a
later "take the pouch" is not told it proved empty; a fixed line that named the hour ("The sun is low", at 10:43 AM) names none; and a
slow fighter already within reach does not spend the round advancing. Left for the balance pass, by the owner's word: a hire's health
falling at a level (5.8).
Run: python tools/sim/small_ones_670_test.py"""
import random
import re
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
simlib.quiet_console()
from engine import battlefield, combat, quirks
from services.fight import RoundIntent

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


nicks = quirks.Q["voices"]["nickname"]["nicks"]
reasons = quirks.Q.get("nick_reasons") or {}
check("2.12: every nickname has its reason", all(reasons.get(n) for n in nicks), [n for n in nicks if not reasons.get(n)])
member = {"name": "Odly", "quirks": {"voice": "nickname", "nick": "Sparrow"}}
lines = quirks.material(member, random.Random(1), []) if hasattr(quirks, "material") else []
src = open("engine/quirks.py", encoding="utf-8").read()
check("...and the speaker is given it with the name", "nick_reasons" in src and "asked why, that is the reason" in src)
said = " ".join(lines) if lines else ""
if lines:
    check("...in what the speaker is offered", "Sparrow" in said and reasons["Sparrow"] in said, lines)
check("2.15: a cache is told as taken, nothing of it left lying there",
      "nothing of it left lying there" in open("scenes/dungeon_actions.py", encoding="utf-8").read())
mentor_text = open("data/world/mentor.yaml", encoding="utf-8").read()
ret = mentor_text.split("\nreturn:", 1)[1].split("\n  info:", 1)[0]
check("2.17: the walk back to Parth names no hour", not re.search(r"\b(sun is low|dusk|dawn|noon|evening|midday)\b", ret, re.I), ret)

first = simlib.campaign("small_ones_670_test", seed=5, location="greywood")
world = first.scene.world
ch, _ = simlib.make_character("warrior", random.Random(2))
me = combat.fighter_from_character(ch)
me.pace = "slow"
wolf = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "e0", "wolf 1")
f = combat.Combat(fighters=[me, wolf], place="x")
battlefield.engage(f, wolf, f.player)
from scenes.combat_scene import service_of
first.close()                                                # (f743) the campaign below clears this save: it is let go first
svc = service_of(simlib.campaign("small_ones_670_test", seed=5, location="greywood").scene)
check("4.4: a slow fighter already in reach does not spend the round advancing",
      svc.apply_step(f, me, RoundIntent(kind="attack", target="e0", step="advance"), wolf) is False)
import shutil
shutil.rmtree("saves/small_ones_670_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
