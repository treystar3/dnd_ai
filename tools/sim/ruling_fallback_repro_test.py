"""REPRO (advisor review): an impossible act must never be granted because the ruling call failed.

engine/ruling.run(): when ruling.ask() returns None (the model's call failed: an LLMError, a timeout, a budget deferral), the act falls
through to world_improv.resolve() with no ruling at all: no capability check, no "no". "I grow wings and fly away" is then sorted into
the improvisation vocabulary and rolled like any climb; on a success the narrator is told it WORKS. GOALS.md pillar 2: "Impossible
actions are refused, and never granted and then forgotten." Expected to FAIL on 06b393c."""
import shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from llm.contracts import ActionIntent
from engine import refusals, ruling
import engine.checks as checks
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("ruling_fallback_repro", seed=2, char_seed=1, location="trading_square")   # (f559) the one constructor (f450)
ws = g.scene
ws.enter("trading_square")
narrated = []
ws._narrate_now = lambda event, player_text="": narrated.append(event)
console.note = lambda *a, **k: None

ruling.ask = lambda ws_, words, text: None                       # the ruling call failed
checks.roll = lambda odds, rng=None, c=None: ("success", 1)      # and the die is kind

line = "I grow wings and fly away over the rooftops"
ws.on_other(ActionIntent(kind="other", summary="grow wings and fly away over the rooftops"), line)
told = narrated[-1] if narrated else ""
check("with no ruling, an impossible act is not told as working", "WORKS" not in told, told[:240])
asked = [r for r in refusals.SESSION if r["kind"] == "ruling_failed"]
check("...it is asked back instead, and logged as a ruling_failed refusal with the player's words", len(asked) == 1 and asked[0]["text"] == line,
      refusals.SESSION[-3:])
check("...and a question waits for the player's next line", bool(getattr(ws, "pending_clarify", None)), getattr(ws, "pending_clarify", None))
g.close()
shutil.rmtree("saves/ruling_fallback_repro", ignore_errors=True)
print("FAILED:" if bad else "all ok", ", ".join(bad))
sys.exit(1 if bad else 0)
