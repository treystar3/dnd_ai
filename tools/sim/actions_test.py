"""Every kind of action is declared once (engine/actions.py): the contract, the time costs, the audit's targeted kinds and the dispatch
all come from it, and the start-up check catches a kind with no handler, one the interpreter's instructions do not describe, or one
described but not declared."""
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import actions, intent_audit
from scenes import world_prompts as wp
from scenes.world import WorldScene, TIME_COST
from llm.contracts import ActionIntent
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

check("the game's registry agrees with the scene and the interpreter's instructions", actions.problems(WorldScene, wp.INTERPRET_SYSTEM) == [], actions.problems(WorldScene, wp.INTERPRET_SYSTEM))
def _ok(k):
    try:
        ActionIntent(kind=k); return True
    except Exception:
        return False
check("the typed contract accepts every declared kind and nothing else", all(_ok(k) for k in actions.KINDS) and not _ok("fly"))
check("time costs and the audit's targeted kinds come from the registry", TIME_COST is actions.TIME_COST and intent_audit.TARGETED is actions.TARGETED
      and TIME_COST["look"] > 0 and "talk" in actions.TARGETED)
class NoLook:                                            # a scene missing a handler
    pass
for k in actions.KINDS:
    if k != "look":
        setattr(NoLook, f"on_{k}", lambda *a: None)
probs = actions.problems(NoLook, wp.INTERPRET_SYSTEM)
check("a kind with no handler is caught at start-up", any("on_look" in p for p in probs), probs)
probs = actions.problems(WorldScene, wp.INTERPRET_SYSTEM.replace("  move               - they want to go", "  fly                - they want to go"))
check("a kind the instructions describe but nobody declared, and one declared but not described, are both caught",
      any("'fly'" in p for p in probs) and any("'move' is not described" in p for p in probs), probs)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
