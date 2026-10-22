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
check("every kind carries the words the interpreter is told about it", all(a.prompt.strip() for a in actions.ACTIONS))
check("the kinds block of the instructions is written from the table", actions.prompt_block() in wp.INTERPRET_SYSTEM and actions.prompt_block().splitlines()[0].startswith("  move               - they want to go"))
check("a kind added to the table is described without a hand edit", "  other              - anything else" in actions.prompt_block())
from scenes import intercepts
check("the intercepts the mixins declare make a consistent table", intercepts.problems(WorldScene) == [], intercepts.problems(WorldScene))
check("they run in their declared order, the errand first and the way out of town last", [i.name for i in WorldScene.INTERCEPT_TABLE][:2] == ["errand", "mentor_intercept"] and WorldScene.INTERCEPT_TABLE[-1].name == "exit", [i.name for i in WorldScene.INTERCEPT_TABLE])
from scenes import plan_repairs
check("the plan repairs the mixins declare make a consistent table", plan_repairs.problems(WorldScene) == [], plan_repairs.problems(WorldScene))
check("they run in their declared order, markup first and the harvest rule last", WorldScene.REPAIR_TABLE[0].name == "scrub_markup" and WorldScene.REPAIR_TABLE[-1].name == "one_harvest", [r.name for r in WorldScene.REPAIR_TABLE])
class Ghost(WorldScene):
    REPAIRS = (plan_repairs.Repair("tidy_fields", 60, "tidy_fields"), plan_repairs.Repair("ghost", 61, "no_such_repair"))
probs = plan_repairs.problems(Ghost)
check("a repair declared twice, and one naming a method the scene lacks, are caught at start-up", any("declared twice" in p for p in probs) and any("no_such_repair" in p for p in probs), probs)
class Twice(WorldScene):
    INTERCEPTS = (intercepts.Intercept("errand", 10, "errand_intercept"), intercepts.Intercept("ghost", 11, "no_such_method"))
probs = intercepts.problems(Twice)
check("a name or an order declared twice, and a method the scene lacks, are caught at start-up", any("declared twice" in p for p in probs) and any("order 10" in p for p in probs) and any("no_such_method" in p for p in probs), probs)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
