"""(f662) A refused pick-up does not stop a walk on, and the end of a matter of the world is told only to a player who met it, in
words whose verb fits any title (docs/design/21_play_faults_plan.md, group C; found in play: docs/play/2026-11-15_play_findings.md
4.6 and 3.6). "I pocket the coins and we go on to the next chamber" refused the coins and dropped the walk; "The tinker's losses is
lost, for all that was done." and two like it were told at the end of a journey of matters the player had never heard of.
Held here: after a refused pick-up the steps that only go on (a walk, a delve, a way out, a look, a wait) are done, while a step that
may need the thing (an unlock) is not; a matter the player never met ends unsaid, one they met ends told, "the matter of" a title of
any number, for every way a matter ends.
Run: python tools/sim/walk_on_matter_662_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import ui.console as uc
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(m))
for fn in ("narrate", "ledger"):
    uc.put(fn, lambda *a, **k: None)
from engine import events, matters
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("walk_on_matter_662_test", seed=2, location="trading_square")
ws = g.scene


def refused_then(*rest):
    take = A(kind="pick_up", item="the coins")
    ws.plan_now = [take, *rest]
    ws.step, ws.halted = take, False
    ws.refuse("Any coin worth taking is already in your purse.")
    return ws.halted


check("4.6: a pick-up refused does not stop the walk on to the next chamber", refused_then(A(kind="move", destination="the next chamber")) is False)
check("...nor a delve, a way out, a look or a wait", all(refused_then(A(kind=k)) is False for k in ("delve", "leave_dungeon", "look", "wait")))
check("...but a step that may need the thing is not done", refused_then(A(kind="unlock", target="the door")) is True)
check("...and a walk after such a step is not either", refused_then(A(kind="unlock", target="the door"), A(kind="move", destination="x")) is True)
take = A(kind="give", item="x")
ws.plan_now, ws.step, ws.halted = [take, A(kind="move", destination="x")], take, False
ws.refuse("No.")
check("...and any other refusal holds as before", ws.halted is True)

unmet = {"id": "th1", "title": "The tinker's losses", "touched": False, "moment": "", "answered": False, "revealed": False}
met = dict(unmet, id="th2", moment="shown")
held = dict(unmet, id="th3")
ws.player.quests = [{"id": "q1", "thread": "th3"}]
for kind in ("achieved", "partly", "transformed", "lost"):
    check(f"3.6: a matter never met ends unsaid ({kind})", matters.ended_line(unmet, kind, ws.player) == "")
    line = matters.ended_line(met, kind, ws.player)
    check(f"...one met is told, its verb fitting a plural title ({kind}): {line!r}", line.startswith("The matter of the tinker's losses ") and " are " not in line)        # (f712) "is settled", "ends badly"
check("...as is one the player holds a contract of", matters.ended_line(held, "lost", ws.player) != "")
check("...and a title with no article is kept as it is", "of Bram's debt " in matters.ended_line(dict(met, title="Bram's debt"), "lost", ws.player))
check("the loss reads the matter before marking it touched", "line = matters_line(th, \"lost\", ws.player_of(ws.acting))" in open("engine/events.py").read()
      and open("engine/events.py").read().index("line = matters_line(th") < open("engine/events.py").read().index('th["result"], th["ending_kind"], th["touched"] = "lost"'))
shutil.rmtree("saves/walk_on_matter_662_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
