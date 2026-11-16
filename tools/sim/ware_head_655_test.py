"""(f655) A ware asked for is named by the head of what is asked, never by a word of a phrase after it that says for whom, for how
long or why (docs/design/21_play_faults_plan.md, B2; found in play: docs/play/2026-11-15_play_findings.md 4.8, "I buy a room for the
night" printed the price list). The same reading for the ware's own name: "a room for the night" is a room, not a night.
Run: python tools/sim/ware_head_655_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 8))
simlib.quiet_console()
from engine import inventory as inv
from npc.models import NPC

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("ware_head_655_test", seed=8, location="trading_square")
ws = g.scene
people = {r: NPC(id=f"t655_{r}", name=f"Tess {r}", role=r, people="human", location="trading_square")
          for r in ("innkeeper", "merchant", "chandler", "fisher")}
asked = lambda role, what: getattr(ws.ware_asked(ws.wares_of(people[role]), what), "id", "")

check("the head of what is asked: a room for tonight, until morning, for me and my friend",
      [asked("innkeeper", w) for w in ("room for tonight", "a room until morning", "a room for me and my friend", "a room, please")]
      == ["room", "room", "room", "room"], [asked("innkeeper", w) for w in ("room for tonight", "a room until morning", "a room for me and my friend", "a room, please")])
check("...a meal for two, a hot meal with bread, a mug of ale for the road",
      [asked("innkeeper", w) for w in ("a meal for two", "a hot meal with bread", "a mug of ale for the road")] == ["meal", "meal", "ale"],
      [asked("innkeeper", w) for w in ("a meal for two", "a hot meal with bread", "a mug of ale for the road")])
check("...some rope to climb with, a sack of salt for the winter, candles for the shrine",
      asked("merchant", "some rope to climb with") == "rope" and asked("merchant", "a sack of salt for the winter") == "salt"
      and asked("chandler", "candles for the shrine") == "candles",
      (asked("merchant", "some rope to climb with"), asked("merchant", "a sack of salt for the winter"), asked("chandler", "candles for the shrine")))
check("a word only in the phrase after the head names nothing: a lamp for the room is no room, a hook for the rope no rope",
      asked("innkeeper", "a lamp for the room") == "" and asked("merchant", "a hook for the rope") == "",
      (asked("innkeeper", "a lamp for the room"), asked("merchant", "a hook for the rope")))
check("what was right stays right: some rope, a sack of salt, a room, and no rope ladder, salted pork or grain alcohol",
      [asked("merchant", w) for w in ("some rope", "a sack of salt", "a rope ladder", "salted pork", "grain alcohol")] == ["rope", "salt", "", "", ""]
      and asked("innkeeper", "room") == "room" and asked("innkeeper", "a room for the night") == "room" and asked("fisher", "room") == "")
check("the head of a name: a room for the night is a room, a sack of salt is salt, rope to climb with is rope",
      [inv.asked_head(t) for t in ("a room for the night", "a sack of salt", "rope to climb with", "")] == ["room", "salt", "rope", ""],
      [inv.asked_head(t) for t in ("a room for the night", "a sack of salt", "rope to climb with", "")])
shutil.rmtree("saves/ware_head_655_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
