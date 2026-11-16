"""(f658) A person here is named by the last word of their trade as by the whole of it: "the clerk" is the guild clerk, "the master"
the caravan master (docs/design/21_play_faults_plan.md, B2; found in play: docs/play/2026-11-15_play_findings.md 4.10, "Both at once"
in answer to the game's own question was read joined to the first line, whose give named "the clerk", and got "There's no one here to
give that to"). Every reader of who a line names here (named_here, those_named) reads it so; two of the same last word name no one.
Run: python tools/sim/trade_named_658_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from npc.models import NPC
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("trade_named_658_test", seed=2, location="trading_square")
ws = g.scene
people = [NPC(id="t658_clerk", name="Odo Venn", role="guild_clerk", people="human", location="trading_square"),
          NPC(id="t658_master", name="Sera Lusk", role="caravan_master", people="human", location="trading_square")]
ws.present[:] = [n for n in ws.present if n.role not in ("guild_clerk", "caravan_master")] + people
check("'the clerk' is the guild clerk", ws.named_here("I hand the clerk the fee") == "t658_clerk", ws.those_named("I hand the clerk the fee"))
check("...'the master' the caravan master", ws.named_here("I ask the master about the road") == "t658_master")
check("...and the whole trade still names them", ws.named_here("I pay the guild clerk") == "t658_clerk")
check("a word of a trade not said as someone is no one: 'a clerk's hand', 'master of none'",
      ws.named_here("I write in a clerk's hand") == "" and ws.named_here("jack of all trades, master of none") == "")
ws.present.append(NPC(id="t658_clerk2", name="Ivo Tam", role="town_clerk", people="human", location="trading_square"))
check("two clerks here: 'the clerk' names neither", ws.named_here("I hand the clerk the fee") == "", ws.those_named("I hand the clerk the fee"))
ws.present.pop()
plan = [A(kind="give", item="coins")]
ws.name_the_target("Do I pay the clerk the fee now or after? - Both at once.", plan)
check("the answer joined to its question: the give is to the clerk the first line named", plan[0].target == "t658_clerk", plan[0])
shutil.rmtree("saves/trade_named_658_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
