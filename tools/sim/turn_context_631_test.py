"""(f631) The turn's context (engine/actor.py; docs/design/20_phase3_plan.md). The fields a line and its operations keep are on
an object of their own, declared in one table, and the scene reads each through a descriptor of the same name. What they do is
held by the pins written before they moved, which pass unchanged: tools/sim/turn_fields_628_test.py, rollback_fields_579_test.py,
scene_rollback_465_test.py and the three recordings. This holds the rest:
- the table: every field says whether a new line resets it, whether a failed operation puts it back, or that it is kept; every
  name a failed operation puts back has a home declared for the day a scene is split for several characters;
- the home: each field lives on the context and nowhere else, through a played line, a failed operation and the reload that
  follows it; the scene has a descriptor for each field and for nothing else; no class the scene is built from keeps a class
  attribute of a field's name; nothing in the game's code, its tools or its harnesses names a field as a key of an object's
  own dictionary;
- the defaults: a scene that has played nothing reads each field as its constructor and the table leave it;
- the snapshot an operation may have to give back is the context's, one for each scene.
Run: python tools/sim/turn_context_631_test.py"""
import ast
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from engine import actor
from llm.gateway import LLMError
from scenes.world import WorldScene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

MISSING = object()
F = actor.FIELDS
line = {k for k, f in F.items() if actor.LINE in f.marks}
rolled = {k for k, f in F.items() if actor.ROLLED in f.marks}
kept = {k for k, f in F.items() if actor.KEPT in f.marks}

# ---- the table
check("every field is reset by a new line, put back by a failed operation, both, or kept: one of those, and kept is neither of the others",
      all(f.marks and f.marks <= {actor.LINE, actor.ROLLED, actor.KEPT} and (f.marks == {actor.KEPT} or actor.KEPT not in f.marks) for f in F.values()),
      {k: sorted(f.marks) for k, f in F.items()})
check("the turn's fields are the thirteen of a line (f715: its plan and its own passages), the step's five, and the four kept across lines",
      len(line) == 13 and len(rolled - line) == 5 and len(kept) == 4 and len(F) == 22, (len(line), len(rolled - line), len(kept), len(F)))
check("only a field a new line resets has a fresh value, and only two are given by the scene (where the line began)",
      all(f.fresh is None for k, f in F.items() if k not in line) and {k for k in line if F[k].fresh is None} == {"line_from", "line_log"})
check("every name a failed operation puts back has a home declared: the turn's, one character's view, or the scene's",
      set(actor.HOMES) == set(WorldScene.ROLLED) and set(actor.HOMES.values()) == {actor.TURN, actor.VIEW, actor.SCENE},
      sorted(set(actor.HOMES) ^ set(WorldScene.ROLLED)))
check("...the turn's are the fields the table says a failure puts back, and the scene's list still names each of them",
      {k for k, h in actor.HOMES.items() if h == actor.TURN} == rolled and rolled <= set(WorldScene.ROLLED))
check("the four scene fields no list held are declared too, apart from the ones a failure puts back",
      set(actor.UNLISTED) == {"broken", "last_text", "crash_after_commit", "recovered_at_load"} and not set(actor.UNLISTED) & set(WorldScene.ROLLED)
      and not set(actor.UNLISTED) & set(F))

# ---- the descriptors
fields_on_scene = {k for k in dir(WorldScene) if isinstance(getattr(WorldScene, k, None), actor.TurnField)}
check("the scene has a descriptor for every field of the turn, and for nothing else", fields_on_scene == set(F), sorted(fields_on_scene ^ set(F)))
ROOT = Path(__file__).resolve().parent.parent.parent
shadow = [f"{c.__name__}.{k}" for c in WorldScene.__mro__ for k in F if k in c.__dict__ and not isinstance(c.__dict__[k], actor.TurnField)]
reach = []
CODE = [p for folder in ("scenes", "engine", "services", "npc", "storage", "llm", "ui", "tools") for p in (ROOT / folder).rglob("*.py")] \
    + list(ROOT.glob("*.py")) + list((ROOT / "data" / "replay" / "scripts").glob("*.py"))
for path in sorted(CODE):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    name = path.relative_to(ROOT).as_posix()
    if name == "scenes/world.py":                         # a class default written in the scene's own body: install would replace it unseen
        body = next(c for c in ast.walk(tree) if isinstance(c, ast.ClassDef) and c.name == "WorldScene").body
        for node in body:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
            shadow += [f"{name}:{node.lineno} {t.id}" for t in targets if isinstance(t, ast.Name) and t.id in F]
    for node in ast.walk(tree):                           # x.__dict__["ran"], x.__dict__.get("ran"), .setdefault, .pop
        d = node.value if isinstance(node, ast.Subscript) else node.func.value if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) else None
        if not (isinstance(d, ast.Attribute) and d.attr == "__dict__"):
            continue
        key = node.slice if isinstance(node, ast.Subscript) else (node.args[0] if node.args else None)
        if isinstance(key, ast.Constant) and key.value in F and name != "engine/actor.py":
            reach.append(f"{name}:{node.lineno} {key.value}")
check("no class the scene is built from keeps a class attribute of a field's name (the table holds a field's default)", not shadow, shadow)
check("nothing names a field as a key of an object's own dictionary, round the descriptor", not reach, reach)

# ---- a scene that has played nothing
g = simlib.campaign("turn_context_631", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/turn_context_631/turns.jsonl"
simlib.quiet_console()
turn = actor.turn_of(ws)
check("the scene's context is one object, the same each time it is asked for", turn is actor.turn_of(ws) and isinstance(turn, actor.TurnContext))
check("it is the scene's actor's (f632), under no name the session sweeps or rolls back", turn is ws.actor.turn and "actor" not in WorldScene.ROLLED
      and not any(v is turn or v is ws.actor for k, v in ws.__dict__.items() if k.startswith("_")))
check("before anything has run the step reads as none and the kept fields as the scene set them", ws.step is None and ws.pending == []
      and ws.halted is False and ws.last_failure == "" and ws.last_budget == {}, (ws.pending, ws.halted, ws.last_failure, ws.last_budget))
made = {k: getattr(ws, k, MISSING) for k in line | {"buffering"}}
check("...and the line's fields and the one-passage flag as its constructor leaves them: empty, false, and no line begun",
      all(made[k] == F[k].fresh() for k in line - {"line_from", "line_log", "line_losses"}) and made["buffering"] is False
      and all(made[k] is MISSING for k in ("line_from", "line_log", "line_losses")), made)
check("...a field nothing has set is not there, and a default asked for is given", getattr(ws, "ran", MISSING) is MISSING
      and getattr(ws, "ran", []) == [] and not hasattr(ws, "interpret_calls"))
ws.halted = True
ws.ran = ["look"]
check("a field set on the scene is set on the context", turn.values["halted"] is True and turn.values["ran"] == ["look"] and ws.ran is turn.values["ran"])
del ws.ran
ws.halted = False
try:
    del ws.ran
    twice = True
except AttributeError:
    twice = False
check("...and one deleted is gone from it, and cannot be deleted twice", "ran" not in turn.values and not twice)
check("no field of the turn is in the scene's own dictionary", not set(F) & set(ws.__dict__), sorted(set(F) & set(ws.__dict__)))

# ---- a line played, an operation failed, the save reloaded: still the context's alone
ws.enter("parth")
stub.plan = [{"kind": "look"}]
ws.turn("I look around.")
check("after a played line the line's fields are the context's, and none is on the scene", ws.line_ops and line <= set(turn.values)
      and not set(F) & set(ws.__dict__), (sorted(line - set(turn.values)), sorted(set(F) & set(ws.__dict__))))
check("...the kinds of action it ran and the interpreter's calls among them", ws.ran == ["look"] and len(ws.interpret_calls) == 1
      and turn.values["ran"] is ws.ran, (getattr(ws, "ran", None), len(getattr(ws, "interpret_calls", []))))
ws.begin_line()
store.arm(False)
check("a new line starts every field the table says it resets as the table says, each list its own",
      all(getattr(ws, k) == F[k].fresh() for k in line if F[k].fresh) and ws.line_from == ws.player.location and isinstance(ws.line_log, int)
      and len({id(turn.values[k]) for k in line if isinstance(turn.values[k], list)}) == 6, {k: turn.values.get(k) for k in line})
check("...and leaves the others as they stood", ws.ran == ["look"] and len(ws.interpret_calls) == 1)
inside = {}
with ws.operation("test", "a failing step") as op:
    inside["snapshot"] = turn.snapshot is not None
    ws.ran = ws.ran + ["made inside"]
    ws.interpret_calls.append("made inside")
    ws.buffering = True
    raise LLMError("the model failed")
check("the snapshot an open operation may have to give back is the context's, and the session holds none of its own",
      inside["snapshot"] and turn.snapshot is None and not hasattr(g.session, "_turn"))
check("a failed operation puts the turn's rolled fields back on the context", op.state == "rolled_back" and ws.ran == ["look"] and len(ws.interpret_calls) == 1
      and ws.buffering is False and not set(F) & set(ws.__dict__), (ws.ran, ws.interpret_calls, ws.buffering, sorted(set(F) & set(ws.__dict__))))
check("the context is the one the scene had before the failure and its reload", actor.turn_of(ws) is turn)

# ---- two scenes
g2 = simlib.campaign("turn_context_631b", cls="warrior", seed=4, location="parth")
ws2 = g2.scene
ws2.enter("parth")
check("a second scene has a context of its own", actor.turn_of(ws2) is not turn and actor.turn_of(ws2).values is not turn.values)
ws.ran, ws2.ran = ["first"], ["second"]
with ws2.operation("test", "the second fails") as op2:
    ws2.ran = ["changed"]
    raise LLMError("the model failed")
check("a failure in one puts its own fields back and leaves the other's", op2.state == "rolled_back" and ws2.ran == ["second"] and ws.ran == ["first"])

g2.session.close()
g.session.close()
for name in ("turn_context_631", "turn_context_631b"):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
