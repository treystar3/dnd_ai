"""(f703) An improvised act always ends in an outcome the player can read (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). "I press a page of my journal against the carvings and rub charcoal over it to copy the
markings." was ruled a plain yes: no roll, nothing changed, so no outcome line was shown (the "Attempt:" line is only for a roll or a
change), and the passage stopped on "as you try to capture the depth of those grooves": the player could not tell whether it worked.
Held here: an act that works with no roll and nothing changed is told to the player in the game's own line (told.yaml act_done) by
what the ruling says it comes to (f609's `works`, never what the line claims), in long words or short, a pose too; a rolled act keeps
its own line ("Attempt: ..."), and a failure is never told as working.
Run: python tools/sim/act_done_703_test.py"""
import shutil
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
import ui.console as uc
LINES = []
uc.put("note", lambda m, *a, **k: LINES.append(("note", str(m))))
uc.put("ledger", lambda m, *a, **k: LINES.append(("ledger", str(m))))
from engine import checks, pulse

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("act_done_703", seed=3, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})
ws.narrate = lambda event, text="": None


def attempt(text, ruled, roll="success"):
    stub.act_ruling = ruled
    real_roll = checks.roll
    checks.roll = lambda odds, rng=None, c=None: (roll, 1)
    LINES.clear()
    try:
        with ws.operation("action:other", text):
            ws.on_other(types.SimpleNamespace(kind="other", summary=text.rstrip(".")), text)
    finally:
        checks.roll = real_roll
    return " | ".join(t for _, t in LINES)


YES = {"sense": "yes", "why": "anyone with paper can", "uses": [], "requires": [], "changes": [], "fail": "noticed",
       "works": "A smudged copy of the grooves on the page."}
said = attempt("I press a page of my journal against the carvings and rub charcoal over it to copy the markings.", YES)
check("a plain yes that changes nothing is told by what the ruling says it comes to, in the game's own line",
      "smudged copy of the grooves on the page" in said and "journal" not in said, said)
said = attempt("I rub charcoal over the carving.", YES)
check("...the same act in fewer words too", "smudged copy" in said, said)
said = attempt("I whistle a tune while I wait.", {**YES, "works": "A tune carries across the square."})
check("...and another act, not the one that found it", "tune carries across the square" in said, said)
said = attempt("I lean against the wall.", {**YES, "works": "You lean there, the stone cool at your back."})
check("a pose is told by what it comes to as well: no act ends without one", "lean there" in said, said)
COST = {"sense": "cost", "why": "a hard climb", "uses": [], "requires": [], "stakes": {"check": "strength", "hard": "hard"}, "changes": [],
        "fail": "noticed", "works": "You reach the top of the wall."}
said = attempt("I climb the wall of the fountain.", COST, "failure")
check("a failure is never told as working, and keeps its own line", "It works" not in said and "reach the top" not in said and "Attempt" in said, said)
said = attempt("I climb the wall of the fountain again.", COST, "success")
check("a rolled success keeps its own line, once", "Attempt" in said and "It works" not in said, said)
g.close()
shutil.rmtree("saves/act_done_703", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
