"""(f633) The turn's registers, with one owner (docs/design/20_phase3_plan.md; engine/actor.py Registers).
What a turn keeps while it is played was held by five modules under names of their own (the operation open now, what was
presented, the calls made inside a transaction; the ledger's rows, the last turn's and the totals; the budget and the last
one's summary; the turn log's open turn and its count of things shown; the serving), and three of them each had their own way
of saying which thread the turn belonged to. Held here:
- every register written through its module's functions is named by the session's residue and gone after its reset;
- the old names are gone: reading one or setting one raises and says what to call, and no file in the repository (the game,
  the tools the suite never runs, the tests) loads or stores one, under any name the module was imported by. (f634) The same
  for the names the actor's caches were held under;
- one field says whose the turn is: the first of a budget, an operation or a serving to open takes it for its thread, the last
  to close gives it up, an open operation or serving keeps it, and a budget a thread left open does not;
- off that thread there is no turn: a call there is not charged, not filed under the operation and not served an answer;
- a scene built on one thread and played on another owns its line where it is played;
- two actors given registers of their own keep their operations, ledgers, budgets and counts apart;
- a turn that showed nothing is still told so, and a failed operation takes back its ledger rows and their totals.
tools/sim/owned_state_633_test.py holds the table every piece of module state is declared in.
Run: python tools/sim/registers_633_test.py"""
import ast
import importlib
import shutil
import subprocess
import sys
import threading
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
restore = simlib.install(stub)
from engine import actor, asked, budget, ledger, operation, session, turnlog
from llm.errors import LLMError

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

simlib.quiet_console()
ME = threading.get_ident()
REQUIRED = next(t for t in budget.TASKS if budget.need(t) == "required")


def held():
    """The registers the session's residue names."""
    return sorted(k for k in session.residue() if k.startswith("registers."))


def on_thread(fn):
    out = {}

    def run():
        try:
            out["got"] = fn()
        except BaseException as e:
            out["error"] = e
    t = threading.Thread(target=run)
    t.start()
    t.join(60)
    return out


# ---- one object, the process's while no actor has its own
R = actor.registers()
session.reset()
check("with no actor bound the turn's registers are the process's one, and a scene's actor shares it", R is actor.SHARED
      and actor.PROCESS.registers is R and actor.ActorContext().registers is R)
check("a set just put back holds nothing", R.held() == {} and held() == [], (R.held(), held()))

# ---- every register, written through its module's functions, is the session's to put back
WRITERS = {
    "operation": lambda: operation.begin("test", 1, 0, 0),
    "presented": lambda: operation.present("o1", "shown"),
    "legacy": lambda: (operation.begin("line", 1, 0, 0), operation.note_legacy("narrate")),
    "rows": lambda: ledger.add("made", say="a thing made"),
    "last": lambda: (ledger.add("made", say="a thing made"), ledger.end()),
    "totals": lambda: (ledger.add("made", say="a thing made"), ledger.end()),
    "budget": lambda: budget.open(),
    "budget_last": lambda: (budget.open(), budget.close()),
    "open_turn": lambda: turnlog.begin(),
    "shown": lambda: turnlog.shown("note", "a line the player read"),
    "serving": lambda: asked.begin(asked._Serving()),
    "owner": lambda: budget.open(),
}
check("every register has a writer here", set(WRITERS) == set(actor.Registers.FRESH), set(WRITERS) ^ set(actor.Registers.FRESH))
for name, write in WRITERS.items():
    session.reset()
    try:
        write()
        named = held()
    except Exception as e:
        named = [repr(e)]
    session.reset()
    check(f"{name}: written through its module it is named by the session's residue, and gone after the reset",
          f"registers.{name}" in named and held() == [] and R.held() == {}, (named, held()))

session.reset()
op = operation.begin("line", 1, 0, 0, "a line")
operation.present(op.id, "shown")
operation.note_legacy("narrate")
ledger.add("made", say="a thing made")
b = budget.open()
turnlog.shown("note", "a line the player read")
check("each is read through its module: the open operation, what was presented, the calls inside a transaction",
      operation.opened() is op and operation.presented() == [{"op": op.id, "how": "shown"}] and operation.legacy() == ["narrate"],
      (operation.opened(), operation.presented(), operation.legacy()))
check("...the turn's rows and the totals, the open budget, the count of things shown", [r["say"] for r in ledger.this_turn()] == ["a thing made"]
      and ledger.totals() == {"made": 1} and budget.opened() is b and turnlog.shown_count() == 1,
      (ledger.this_turn(), ledger.totals(), budget.opened(), turnlog.shown_count()))
took = operation.take_presented()
rows = ledger.end()
check("taking what was presented leaves none, and the turn's rows become the last turn's as it ends", took == [{"op": op.id, "how": "shown"}]
      and operation.presented() == [] and ledger.last() is rows and ledger.this_turn() == [] and ledger.totals() == {"made": 1},
      (took, operation.presented(), ledger.last(), ledger.this_turn()))
operation.end("committed")
summary = budget.close(stand_ins=["passage"])
check("...and the closed budget's summary is the last one's", budget.opened() is None and budget.last() == summary and summary["stand_ins"] == ["passage"],
      (budget.opened(), budget.last()))
check("a budget held after it closed still answers whoever holds it", b.charge(REQUIRED, 4000, 800) > 0 and len(b.charges) == 1, b.charges)
session.reset()

# ---- the old names are gone, for a reader and for a writer
MOVED = {"engine.operation": ("CURRENT", "PRESENTED", "LEGACY"), "engine.ledger": ("ROWS", "LAST", "TOTALS"), "engine.budget": ("CURRENT", "LAST"),
         "engine.turnlog": ("_open", "SHOWN"), "engine.asked": ("_LOCAL",)}
REGISTERS = tuple(MOVED)
MOVED.update({"engine.canon": ("JOURNAL", "IDS", "EVENTS", "_SINK"), "engine.names": ("CAST",), "engine.failures": ("_last",),        # (f634) the
              "engine.questions": ("_last",), "engine.enchanting": ("DISCOUNT",)})                    # actor's caches (actor_caches_634_test.py)
for mod_name, names in MOVED.items():
    mod = importlib.import_module(mod_name)
    for name in names:
        said = []
        for act in (lambda: getattr(mod, name), lambda: setattr(mod, name, None)):
            try:
                act()
                said.append("")
                break                                      # the name is there: setting it would only break the module for the rest
            except AttributeError as e:
                said.append(str(e))
        check(f"{mod_name}.{name} is gone: reading it raises and says what to call, and so does setting it",
              len(said) == 2 and all(f"{mod_name}.{name}" in s and "use " in s for s in said) and name not in vars(mod), said)
check("...and a name the module never had is refused as any missing name is", not hasattr(ledger, "NO_SUCH_NAME"))

# ---- the fence: no file loads or stores one, whatever the module was imported as
SHORT = {m.split(".")[1]: set(names) for m, names in MOVED.items()}


def uses(source: str) -> list[str]:
    """Every load or store of a moved name in this source: an attribute of the module under any name it was imported by, the
    name imported itself, or the name handed to getattr, setattr, hasattr or delattr."""
    tree = ast.parse(source)
    alias = {}                                             # the name in this file -> which of the five modules
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module == "engine":
            for a in n.names:
                if a.name in SHORT:
                    alias[a.asname or a.name] = a.name
        elif isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("engine.") and n.module[7:] in SHORT:
            out += [f"line {n.lineno}: from {n.module} import {a.name}" for a in n.names if a.name in SHORT[n.module[7:]] or a.name == "*"]
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.asname and a.name.startswith("engine.") and a.name[7:] in SHORT:
                    alias[a.asname] = a.name[7:]
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute):
            v = n.value
            mod = alias.get(v.id) if isinstance(v, ast.Name) else \
                v.attr if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == "engine" and v.attr in SHORT else None
            if mod and n.attr in SHORT[mod]:
                out.append(f"line {n.lineno}: {mod}.{n.attr} ({type(n.ctx).__name__.lower()})")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("getattr", "setattr", "hasattr", "delattr") and len(n.args) >= 2 \
                and isinstance(n.args[0], ast.Name) and isinstance(n.args[1], ast.Constant) and n.args[1].value in SHORT.get(alias.get(n.args[0].id), ()):
            out.append(f"line {n.lineno}: {n.func.id}({n.args[0].id}, {n.args[1].value!r})")
    return out


CAUGHT = {
    "a read": "from engine import ledger\nx = ledger.ROWS\n",
    "a store": "from engine import ledger\nledger.LAST = []\n",
    "a change in place under another name": "from engine import operation as _op\n_op.LEGACY.append('t')\n",
    "a slice store": "from engine import operation\noperation.PRESENTED[:] = []\n",
    "the module imported by its path": "import engine.turnlog as t\nn = t.SHOWN\n",
    "the path spelled whole": "import engine.budget\nb = engine.budget.CURRENT\n",
    "the name imported": "from engine.ledger import TOTALS\n",
    "the name handed to setattr": "from engine import budget\nsetattr(budget, 'CURRENT', None)\n",
    "an import inside a function": "def f():\n    from engine import asked as a\n    return a._LOCAL\n",
    "(f634) a name map put in whole": "from engine import canon\ncanon.IDS = {'Bram': 'h1'}\n",
    "(f634) a key set in it": "from engine import canon\ncanon.IDS['Bram'] = 'h1'\n",
    "(f634) the discount's key set": "from engine import enchanting\nenchanting.DISCOUNT['percent'] = 10\n",
    "(f634) a private name read": "from engine import failures, questions\nx = failures._last, questions._last\n",
}
PASSED = {
    "another module's name": "from storage import migrations\nfrom engine import pulse\nv = migrations.CURRENT\nw = pulse.LAST\n",
    "the module's functions": "from engine import ledger, budget\nledger.this_turn()\nbudget.last()\nledger.KINDS\n",
    "a word in a docstring": '"""ledger.ROWS was the turn\'s rows"""\n',
}
check("the fence catches every way a moved name is loaded or stored", all(uses(src) for src in CAUGHT.values()), [k for k, s in CAUGHT.items() if not uses(s)])
check("...and passes what is not one", not any(uses(src) for src in PASSED.values()), {k: uses(s) for k, s in PASSED.items() if uses(s)})
FILES = [Path(p) for p in subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True, text=True,
                                         check=True).stdout.split()]
found = {str(p): uses(p.read_text(encoding="utf-8")) for p in FILES if p.exists()}
found = {p: u for p, u in found.items() if u}
check("no file in the repository loads or stores a moved name: the game, the tools the suite never runs, the tests",
      len(FILES) > 600 and all(Path(p) in FILES for p in ("tools/rerun.py", "tools/nightrun.py", "tools/live_check.py", "simbot.py")) and not found,
      {p: u[:3] for p, u in list(found.items())[:12]})

# ---- one field says whose the turn is
sources = {m: Path(m.replace(".", "/") + ".py").read_text(encoding="utf-8") for m in REGISTERS}
check("the three ways a thread owned a turn are one field: no thread id and no thread-local in the five modules",
      "thread" not in operation.Operation.__dataclass_fields__ and "owner" not in vars(budget.Budget())
      and not any("get_ident" in s or "threading.local" in s for s in sources.values()),
      [m for m, s in sources.items() if "get_ident" in s or "threading.local" in s])
check("between turns the turn is nobody's", R.owner is None and not R.mine())
OPENERS = {
    "a budget": (lambda: budget.open(), lambda: budget.close()),
    "an operation": (lambda: operation.begin("line", 1, 0, 0), lambda: operation.end("committed")),
    "a serving": (lambda: asked.begin(asked._Serving()), lambda: asked.end()),
}
for what, (opens, closes) in OPENERS.items():
    opens()
    took = (R.owner, R.mine())
    closes()
    check(f"{what} opening takes the turn for its thread, and closing alone gives it up", took == (ME, True) and R.owner is None, (took, R.owner))
b = budget.open()
asked.begin(asked._Serving())
op = operation.begin("line", 1, 0, 0, "a line")
steps = [R.owner]
operation.end("committed")
steps.append(R.owner)
budget.close()
steps.append(R.owner)
asked.end()
steps.append(R.owner)
check("with all three open the turn is given up only as the last closes", steps == [ME, ME, ME, None], steps)

# ---- off the owner's thread there is no turn
session.reset()
b = budget.open()
serve = asked._Serving()
asked.begin(serve)
op = operation.begin("line", 1, 0, 0, "a line")
mine = dict(op=operation.current() is op, served=asked.wanted(REQUIRED), charged=budget.charge(REQUIRED, 4000, 800), deadline=budget.deadline(),
            row=ledger.add("made", say="made by the line"))


def background():
    got = dict(mine=actor.registers().mine(), same=actor.registers() is R, op=operation.current(), served=asked.wanted(REQUIRED), serving=asked.serving(),
               charged=budget.charge(REQUIRED, 4000, 800), embedded=budget.embed(3), deadline=budget.deadline(),
               row=ledger.add("made", say="made behind the scenes"))
    operation.note_legacy("populate_place")
    b.spent = b.limit                                      # nothing left: a required call of the turn's would be refused
    try:
        budget.allow(REQUIRED, 4000)
        got["refused"] = False
    except budget.BudgetError:
        got["refused"] = True
    b.spent = 0.0
    return got


other = on_thread(background).get("got") or {}
check("on the thread that plays the turn a call is the operation's, served and charged", mine["op"] and mine["served"] and mine["charged"] > 0
      and mine["deadline"] is not None and mine["row"].get("op") == op.id, mine)
check("a call on another thread at the same moment reads the same registers and finds no turn there", other.get("same") and other.get("mine") is False
      and other.get("op") is None, other)
check("...it is not charged or refused, and has no deadline of the turn's", other.get("charged") == 0.0 and other.get("embedded") == 0.0
      and other.get("refused") is False and other.get("deadline") is None and len(b.charges) == 1, (other, b.charges))
check("...not filed under the operation or counted as waiting inside its transaction", "op" not in other.get("row", {"op": 1}) and operation.legacy() == []
      and op.rows == [mine["row"]], (other.get("row"), operation.legacy(), op.rows))
check("...and not served an answer", other.get("served") is False and other.get("serving") is None and asked.serving() is serve, other)
taken = on_thread(lambda: (budget.open(), R.owner))                    # an opener on another thread, while the operation is open
check("an open operation keeps the turn for its thread, whoever opens a budget meanwhile", R.owner == ME and operation.current() is op, (taken, R.owner))
operation.end("committed")
taken = on_thread(lambda: (budget.open(), R.owner))                    # ...and between two attempts, with the serving alone open
check("...and so does an open serving, between two attempts of its operation", R.owner == ME and asked.serving() is serve, (taken, R.owner))
op = operation.begin("line", 1, 0, 0, "the attempt after")
second = on_thread(lambda: operation.begin("line", 1, 1, 0))
check("...and a second operation cannot be opened over it, from any thread", isinstance(second.get("error"), RuntimeError) and operation.opened() is op, second)
session.reset()
left = on_thread(lambda: (budget.open(), threading.get_ident())[1])["got"]       # a budget a thread opened and never closed
stale = (R.owner == left, budget.charge(REQUIRED, 4000, 800))
fresh = budget.open()                                      # the next input, on this thread
check("a budget a thread left open does not keep the turn from the thread that opens the next", stale == (True, 0.0) and R.owner == ME
      and budget.charge(REQUIRED, 4000, 800) > 0 and len(fresh.charges) == 1, (stale, R.owner, fresh.charges))
session.reset()
left = on_thread(lambda: (budget.open(), threading.get_ident())[1])["got"]
stale = (R.owner == left, budget.charge(REQUIRED, 4000, 800))
op = operation.begin("line", 1, 0, 0, "the next line, on this thread")
check("...nor from the thread that opens an operation next, whose calls the budget then charges", stale == (True, 0.0) and R.owner == ME
      and operation.current() is op and budget.charge(REQUIRED, 4000, 800) > 0, (stale, R.owner))
session.reset()

# ---- a scene built on one thread and played on another
BASE = Path("saves/registers_633")
shutil.rmtree(BASE, ignore_errors=True)
g = simlib.campaign("registers_633", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
ws.enter("parth")
budget.open()                                              # left open by the thread that built it
seen = {}
stub.plan = [{"kind": "look"}]
real_step = ws.run_step


def step(i, plan, text):
    seen.update(op=operation.current(), mine=actor.registers().mine(), thread=threading.get_ident(), budget=budget.opened())
    return real_step(i, plan, text)


ws.run_step = step
played = on_thread(lambda: ws.turn("I look around."))
del ws.run_step
check("a scene built on one thread and played on another owns its line where it is played", played.get("got") is True and seen.get("op") is not None
      and seen.get("mine") is True and seen.get("thread") not in (None, ME), (played, seen))
check("...its calls charged to the budget of that line", ws.last_budget.get("calls", 0) >= 1 and budget.last() == ws.last_budget, ws.last_budget)
check("...and the turn is nobody's once the line is done", R.owner is None and budget.opened() is None and operation.opened() is None, R.held())

# ---- a turn that showed nothing is still told so
import ui.console as console
said, moved = [], {}
ws.said_nothing = lambda text: said.append(text)
before = turnlog.shown_count()
turnlog.tap()
console.note("")                                           # nothing: it does not count
empty = turnlog.shown_count() - before
console.note("A gull wheels over the quay.")
check("the count of things shown moves with what the player was shown, and not with an empty line", (empty, turnlog.shown_count() - before) == (0, 1),
      (empty, turnlog.shown_count() - before))
TICKS = ("release_time_notes", "hire_said_marks", "sync_heard", "orenna_tick", "mentor_tick", "quirk_tick", "run_deferred", "banter_tick", "note_hire_spoke",
         "collapse_check", "stay_tick", "heard_flush")
for name in TICKS:
    setattr(ws, name, lambda *a, **k: None)
with actor.bind(ws.actor):
    ws.turn_ticks("I stand still.", turnlog.shown_count())
    quiet = list(said)
    start = turnlog.shown_count()
    console.note("The bell rings noon.")
    ws.turn_ticks("I listen.", start)
for name in TICKS + ("said_nothing",):
    delattr(ws, name)
check("a line that showed the player nothing is told so, and one that showed something is not", quiet == ["I stand still."] and said == quiet, (quiet, said))

# ---- a failed operation takes back its ledger rows and their totals
session_rows = ledger.count("gained")
with actor.bind(ws.actor):
    ledger.begin()
    kept = ledger.add("made", say="a thing made before the step")
    with ws.operation("test", "a step that fails") as failed:
        ledger.add("gained", say="a thing that will not stand")
        inside = (ledger.count("gained") - session_rows, len(ledger.this_turn()))
        raise LLMError("the model failed")
check("an operation that fails takes back its own ledger rows and their totals, and leaves the rest of the turn's", failed.state == "rolled_back"
      and inside == (1, 2) and ledger.this_turn() == [kept] and ledger.count("gained") == session_rows, (failed.state, inside, ledger.this_turn()))
g.close()
check("closing the campaign leaves nothing in the registers", R.held() == {} and simlib.residue() == {}, (R.held(), simlib.residue()))

# ---- two actors with registers of their own
one, two = actor.ActorContext(registers=actor.Registers()), actor.ActorContext(registers=actor.Registers())
with actor.bind(one):
    op_one = operation.begin("line", 1, 0, 0, "one's line")
    ledger.add("made", say="one's")
    turnlog.shown("note", "one's line")
    budget.open()
    with actor.bind(two):
        apart = dict(op=operation.current(), rows=ledger.this_turn(), shown=turnlog.shown_count(), budget=budget.opened(), owner=actor.registers().owner)
        op_two = operation.begin("line", 1, 0, 0, "two's line")           # two lines open at once, one each
        ledger.add("gained", say="two's")
        theirs = (operation.current() is op_two, [r["say"] for r in ledger.this_turn()], ledger.totals())
        operation.end("committed")
    back = (operation.current() is op_one, [r["say"] for r in ledger.this_turn()], ledger.totals(), turnlog.shown_count())
    operation.end("committed")
    budget.close()
check("two actors given registers of their own: the second finds no operation, no rows, nothing shown and no budget of the first's",
      apart == dict(op=None, rows=[], shown=0, budget=None, owner=None), apart)
check("...each opens a line of its own at the same moment, with its own ledger", theirs == (True, ["two's"], {"gained": 1})
      and back == (True, ["one's"], {"made": 1}, 1), (theirs, back))
check("...and neither wrote the process's", R.held() == {}, R.held())

restore()
shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
