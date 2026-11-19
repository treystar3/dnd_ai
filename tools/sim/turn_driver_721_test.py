"""(f721) One turn driver. An input of the game's loop, a typed line or a pane's command, is played by one path (WorldScene.play):
opened and closed in one place (the line's fields, the fence, the dice, the budget: WorldScene.input), and its row and the header
written once (close_input). Where the input closes is the only place that says its last line, and it says one: the turn was not
taken, it stood in part, it was silent, or nothing. So a turn played without the loop (the suite, the acceptance tool) reads the
same last line. On 17 November a turn that stood in part read "Nothing comes of that here" and then the part line: the tail
printed the first and the loop the second.

What the world owes the save as the game opens is opened by the same place; nothing was typed, so it is counted as no input,
has no budget and writes no row, and it leaves nothing open."""
import ast
import inspect
import json
import shutil
import sys
import textwrap
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from engine import actor, budget, failures
from engine.operation import Operation
from llm.gateway import LLMError
from scenes.world import WorldScene
from ui import console

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


# ---- one path
tree = ast.parse(textwrap.dedent(inspect.getsource(WorldScene)))
calls: dict[str, list[str]] = {}
for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            calls.setdefault(f"{node.func.value.id}.{node.func.attr}", []).append(fn.name)
src_open = inspect.getsource(WorldScene.open_world)
check("the world's opening is opened by the same place as a typed input", 'self.input("#start", "opening")' in src_open and "arm(" not in src_open)
check("the scene has one driver for an input, one opening of it and one close", all(callable(getattr(WorldScene, k, None)) for k in ("play", "input", "close_input", "closing_line")))
check("a line's fields, its dice and its budget are opened in one place, and the budget closed there",
      calls.get("self.begin_line") == ["input"] and calls.get("self.new_input") == ["input"] and calls.get("budget.close") == ["input"],
      (calls.get("self.begin_line"), calls.get("self.new_input"), calls.get("budget.close")))
check("the log's row is opened by the driver and written by the close, once each", calls.get("turnlog.begin") == ["play"] and calls.get("turnlog.end") == ["close_input"],
      (calls.get("turnlog.begin"), calls.get("turnlog.end")))
check("the line that says a turn was not taken, and the one for a part, are chosen in one place",
      calls.get("self.failed_line") == ["closing_line"] and calls.get("self.part_line") == ["closing_line"], (calls.get("self.failed_line"), calls.get("self.part_line")))
silent_said = [fn.name for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
               and any(isinstance(n, ast.Attribute) and n.attr == "SILENT" for n in ast.walk(fn))]
check("...and so is the line for a silent turn; the one line chosen is said where the input closes, and nowhere else",
      silent_said == ["closing_line"] and calls.get("self.closing_line") == ["input"], (silent_said, calls.get("self.closing_line")))
check("the game's loop plays each input through the driver", "play" in {n.func.attr for n in ast.walk(next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == "run"))
                                                                       if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)})

# ---- a typed line, a pane's command: the same things closed
shown = simlib.quiet_console()
g = simlib.campaign("driver_721", seed=4, location="trading_square")
ws, store = g.scene, g.store
log = Path("saves/driver_721/turns.jsonl")
config.TURN_LOG_PATH = str(log)
ws.enter("trading_square")
rows = lambda: [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
closed = lambda: (store._armed, budget.opened() is None, ws.collecting, actor.registers().open_turn is None)
CLOSED = (False, True, False, True)
play = getattr(ws, "play", lambda text: None)

n0, steps0 = len(rows()), store.meta.steps
went_on = play("I look around.")
check("a typed line is played, and the loop goes on", went_on is True and store.meta.steps == steps0 + 1, (went_on, store.meta.steps - steps0))
check("...it leaves no fence armed, no budget open, nothing collecting, and one row in the log", closed() == CLOSED and len(rows()) == n0 + 1 and rows()[-1].get("text") == "I look around.",
      (closed(), len(rows()) - n0))
n0, steps0 = len(rows()), store.meta.steps
went_on = play("#pronoun she")
check("a pane's command is played by the same path: an input counted, the same things closed", went_on is True and store.meta.steps == steps0 + 1 and closed() == CLOSED,
      (went_on, store.meta.steps - steps0, closed()))
check("...and leaves its row", len(rows()) == n0 + 1 and rows()[-1].get("handled_by") == "command", (len(rows()) - n0, rows()[-1].get("handled_by") if rows() else None))

# ---- a failed command reads as a failed line does
NOT_TAKEN = set(failures.F["turn_not_taken"]) | set(failures.F.get("turn_not_possible") or [])
real_command, real_take = ws.command, ws.take_line


def lost(*a, **k):
    raise LLMError("the model failed")


del shown[:]
ws.command = lost
play("#pronoun she")
ws.command = real_command
by_command = [t for k, t in shown if k == "note"]
del shown[:]
ws.take_line = lost
play("I sit down.")
ws.take_line = real_take
by_line = [t for k, t in shown if k == "note"]
check("a pane's command that could not be taken says so in the narrator's words, once", len(by_command) == 1 and by_command[0] in NOT_TAKEN, by_command)
check("...as a typed line does", len(by_line) == 1 and by_line[0] in NOT_TAKEN, by_line)
check("...and both leave the same things closed", closed() == CLOSED, closed())

# ---- the one closing line
SILENT = "Nothing comes of that here"
went = Operation(id="w", kind="action:go", steps=1, index=0, revision_seen=0, did=["walked to the guild hall"])
missed = Operation(id="x", kind="action:talk", steps=1, index=1, revision_seen=0, aim="speak with the clerk")
closing = getattr(ws, "closing_line", lambda text: "")
ws.begin_line()
store.arm(False)
del shown[:]
ws.said_nothing("I hum a tune.")
check("a turn that showed nothing is marked silent by the tail, which prints no line of its own", getattr(ws, "silent", None) is True and not [t for k, t in shown if SILENT in t], shown)
ws.stood = True
check("...and the close says so, when the turn stood whole", SILENT in (closing("I hum a tune.") or ""), closing("I hum a tune."))
ws.line_ops, ws.line_failed, ws.stood = [went], [missed], "part"
part = closing("I go to the guild hall and speak with the clerk.") or ""
check("a turn that stood in part reads the part line and no silent line beside it", part.startswith("You walked to the guild hall") and SILENT not in part, part)
ws.stood = False
check("...a turn not taken reads that it was not, and nothing else", closing("I hum a tune.") in NOT_TAKEN, closing("I hum a tune."))
ws.begin_line()
store.arm(False)
check("...and a new line has no closing line: it is silent no longer, and how it stood is not yet settled", closing("I look around.") is None and ws.silent is False
      and ws.stood is None, (closing("I look around."), getattr(ws, "silent", None), getattr(ws, "stood", 0)))

# ---- real turns: silent, and in part, with the loop and without it
real_look, real_step = ws.on_look, ws.run_step
ws.on_look = lambda intent, text: None


def notes_of(fn, text, plan):
    stub.plan = plan
    del shown[:]
    out = fn(text)
    return out, [t for k, t in shown if k == "note"], [k for k, t in shown]


out, notes, kinds = notes_of(ws.turn, "I gaze at nothing in particular.", [{"kind": "look"}])
check("a turn that shows nothing, played without the loop, says so in one line, the last thing shown",
      out is True and len([n for n in notes if SILENT in n]) == 1 and SILENT in notes[-1] and kinds[-1] == "note", (out, notes, kinds[-3:]))
n0 = len(rows())
out, notes, kinds = notes_of(play, "I gaze at nothing in particular.", [{"kind": "look"}])
check("...and played by the loop it says so once, and its row says it stood", out is True and len([n for n in notes if SILENT in n]) == 1
      and len(rows()) == n0 + 1 and rows()[-1].get("stood") == "all", (out, notes, rows()[-1].get("stood") if rows() else None))


def second_fails(i, plan, text):
    if i == 1:
        raise LLMError("the model failed")
    return real_step(i, plan, text)


ws.run_step = second_fails
TWO = [{"kind": "look"}, {"kind": "wait"}]
out, notes, kinds = notes_of(ws.turn, "I gaze at nothing and then wait a while.", TWO)
closers = [n for n in notes if SILENT in n or n in NOT_TAKEN or n.startswith("You ")]
check("a turn that showed nothing and stood in part (the fault of 17 November) reads one closing line, the part line, and no silent line",
      out == "part" and ws.silent is True and not [n for n in notes if SILENT in n] and len(closers) == 1, (out, getattr(ws, "silent", None), notes))
n0 = len(rows())
out2, notes2, kinds = notes_of(play, "I gaze at nothing and then wait a while.", TWO)
check("...the same by the loop, and its row says it stood in part", out2 is True and len(notes2) == 1 and notes2[0].startswith("You ") and SILENT not in notes2[0] and len(rows()) == n0 + 1 and rows()[-1].get("stood") == "part",
      (out2, notes2, rows()[-1].get("stood") if rows() else None))
ws.on_look, ws.run_step = real_look, real_step
stub.plan = None

# ---- a turn stopped on purpose says no closing line
from core.interrupts import Interrupt


def stopped(text):
    raise Interrupt("stopped")


ws.take_line = stopped
del shown[:]
try:
    ws.turn("I sit down.")
    raised = False
except Interrupt:
    raised = True
ws.take_line = real_take
check("a turn stopped on purpose passes through its close with no closing line, and nothing left open", raised and not [t for k, t in shown if k == "note"]
      and closed() == CLOSED, (raised, shown, closed()))

# ---- the menu ends the loop
n0 = len(rows())
check("a pane's command for the menu ends the loop", play("#menu") is False and ws.to_menu is True and closed() == CLOSED, closed())
g.close()
shutil.rmtree("saves/driver_721", ignore_errors=True)

# ---- the opening is no input, and leaves nothing open
shown = simlib.quiet_console()
g = simlib.campaign("driver_721_open", seed=4, location="trading_square")
ws, store = g.scene, g.store
log = Path("saves/driver_721_open/turns.jsonl")
config.TURN_LOG_PATH = str(log)
steps0 = store.meta.steps
typed = iter(["I look around.", "quit"])
console.put("ask", lambda *a, **k: next(typed) if k.get("main", a[0] if a else False) else "yes")
ws.run()
check("the opening counts no input and writes no row; the line typed after it is the first of both",
      store.meta.steps == steps0 + 1 and len(rows()) == 1 and rows()[0].get("text") == "I look around.", (store.meta.steps - steps0, [r.get("text") for r in rows()]))
check("...and the loop's end leaves nothing armed or open", (store._armed, budget.opened() is None, actor.registers().open_turn is None) == (False, True, True))
g.close()
shutil.rmtree("saves/driver_721_open", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
