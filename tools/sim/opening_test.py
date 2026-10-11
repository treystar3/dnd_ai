"""The fixed opening, and that creation ends after the stats are confirmed (no set goal is asked for)."""
import sys, json, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import ui.console as uc
SAID = []
uc.say = lambda t, s="": SAID.append(("say", t))
uc.narrate = lambda t: SAID.append(("narrate", t))
uc.note = lambda *a, **k: None
from scenes.goddess import ThresholdScene, Step
from llm.contracts import PlayerTurn
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)
s = ThresholdScene()
s.opening()
beats = json.load(open("data/opening.json"))
check("every beat is printed, the goddess's in her voice", len(SAID) == len(beats) and [k for k, _ in SAID].count("say") == sum(b["who"] == "goddess" for b in beats))
text = " ".join(t for _, t in SAID).lower()
check("it says you died, not your time, the second life, and asks the name", all(w in text for w in ("dead", "not your time", "second life", "your name")))
check("no cause of death is given", all(w not in text for w in ("killed", "sword", "poison", "murder")))
check("her lines are in the transcript", len(s.transcript) == sum(b["who"] == "goddess" for b in beats))
check("there is no aspiration step any more", "ASPIRATION" not in Step.__members__)
# confirming the stats finishes creation
import character.creation as cr
done = []
s.speak = lambda event: done.append(event)
s.finish = lambda: done.append("finished")
s.step = Step.CONFIRM_STATS
s.on_confirm_stats(PlayerTurn(kind="confirm"))
check("confirming the stats ends creation", done == ["finished"], done)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
