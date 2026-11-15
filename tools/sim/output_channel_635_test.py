"""(f635) The whole output seam under the channel (docs/design/20_phase3_plan.md; ui/console.py Channel).
The channel of f580 carried the console's text and nothing else. The line asked for, the side pane's scope, what kind of text a
line is, the status block, the busy light's words, a pane's data, the load bar, the home page, creation and the fight's pane
were functions on the console module that the window swapped for its own, and an operation's hold, the turn log's tap, the
recorder and the question fence swapped them again. So there was one screen for the process, whoever played. Held here:
- no output is set on the console module after import: setting or deleting a name on it raises and says what to call, and its
  names are the same objects after a window came and went, an operation held its lines, a turn was fenced and a tap was put on;
- every name of the seam is the channel's: a channel in use is the one asked, and the terminal's own answers are as they were;
- what stands in for an output (a test's capture, a hold, a fence, the tap) is set on a channel and answers on that channel
  only: `console.put(name, fn)`, `console.now(name)`;
- the window supplies a channel (ui/gui/bridge.py Page): two windows are two pages, and what one is sent the other is not;
- an operation's hold, the question fence and the turn log's tap wrap the channel that is current, and no other;
- the channel in use is this thread's: another thread, and a thread with no actor bound, has the process's;
- no file in the repository assigns to a console attribute, by any name the module was imported under.
What the window is sent is held, unchanged, by tools/sim/output_seam_628_test.py, and the terminal's bytes by
tools/sim/console_bytes_579_test.py.
Run: python tools/sim/output_channel_635_test.py"""
import ast
import contextlib
import io
import shutil
import subprocess
import sys
import threading
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
import ui.console as console
from engine import actor, questions, turnlog
from ui.gui import bridge as bridge_mod

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

SEAM = ("ask", "scope", "kind", "status_block", "busy_text", "panel", "setup_progress", "home", "home_done", "creation", "creation_done",
        "combat_state")
STATUS = ("Day 3, dusk", "light rain", "Trading Square, Parth", "a quiet corner", {"health": (40.4, 52), "mana": (0, 0), "stamina": (11.0, 40)},
          3, 2, 12345)
was_debug, actor.prefs().debug = actor.prefs().debug, False


def module_now() -> dict:
    """The console module's names and what each is bound to, but the one name it writes itself (the process's channel)."""
    return {k: id(v) for k, v in vars(console).items() if k != "_process"}


# ---- no output is set on the module after import
AT_IMPORT = module_now()
raised = {}
for what, write in (("set", lambda: setattr(console, "note", print)), ("set a new name", lambda: setattr(console, "note_635", 1)),
                    ("delete", lambda: delattr(console, "note"))):
    try:
        write()
        raised[what] = ""
    except AttributeError as e:
        raised[what] = str(e)
check("setting or deleting a name on the console module raises, and says what to call", all("console.put" in v for v in raised.values()), raised)
check("...and nothing was written", module_now() == AT_IMPORT)


# ---- every name of the seam is the channel's
class Asked(console.Channel):
    """A channel that keeps what it is asked and what it is written."""
    width, windowed = 61, True

    def __init__(self):
        self.calls, self.text = [], []

    def write(self, text, end="\n"):
        self.text.append(text + end)

    def ask(self, main=False, menu=False):
        self.calls.append(("ask", main, menu))
        return "a line typed"

    @contextlib.contextmanager
    def scope(self, command):
        self.calls.append(("scope", command))
        yield

    @contextlib.contextmanager
    def kind(self, name):
        self.calls.append(("kind", name))
        yield

    def status_block(self, *a, **k):
        self.calls.append(("status_block", a[0]))

    def busy_text(self, message):
        self.calls.append(("busy_text", message))

    def panel(self, name, data):
        self.calls.append(("panel", name))
        return True

    def setup_progress(self, frac, text):
        self.calls.append(("setup_progress", frac))

    def home(self, data):
        self.calls.append(("home",))
        return True

    def home_done(self):
        self.calls.append(("home_done",))

    def creation(self, data):
        self.calls.append(("creation",))
        return True

    def creation_done(self):
        self.calls.append(("creation_done",))

    def combat_state(self, data):
        self.calls.append(("combat_state", data))
        return True


def through(ch=None) -> dict:
    """Every name of the seam, called the way the game calls it; what each answered."""
    got = {}
    got["ask"] = console.ask(main=True) if ch is not None else None          # the terminal's reads the keyboard: not asked here
    with console.scope("#journal"):
        got["panel"] = console.panel("shop", {"wares": []})
    with console.kind("speech"):
        pass
    console.status_block(*STATUS)
    console.busy_text("People go about their day.")
    console.setup_progress(1, "Waking the model")
    got["home"] = console.home({"saves": []})
    console.home_done()
    got["creation"] = console.creation({"step": "name"})
    console.creation_done()
    got["combat_state"] = console.combat_state({"round": 1})
    got["windowed"], got["width"] = console.windowed(), console.width()
    return got


out = io.StringIO()
mine = Asked()
with contextlib.redirect_stdout(out), console.use(mine):
    answered = through(mine)
check("a channel in use is asked for every name of the seam", {c[0] for c in mine.calls} == set(SEAM), sorted(set(SEAM) ^ {c[0] for c in mine.calls}))
check("...and the game is answered by it: the line, the panes drawn, whether a window draws, the width to wrap to",
      answered == {"ask": "a line typed", "panel": True, "home": True, "creation": True, "combat_state": True, "windowed": True, "width": 61}, answered)
check("...and the process's channel is sent nothing meanwhile", out.getvalue() == "", out.getvalue()[:80])
out = io.StringIO()
with contextlib.redirect_stdout(out):
    plain = through()
check("the terminal answers as it did: no pane is drawn, nothing is a window, lines wrap at 92",
      plain == {"ask": None, "panel": False, "home": False, "creation": False, "combat_state": False, "windowed": False, "width": 92}, plain)
check("...and its status block and load bar are text", "HP " in out.getvalue() and "Waking the model  100%" in out.getvalue(), out.getvalue()[:200])
check("the seam's names are still called on the console, each a function there", all(callable(getattr(console, n)) for n in SEAM))

# ---- what stands in for an output is the channel's
notes = []
plain_note = console.now("note")
console.put("note", lambda m: notes.append(m))
console.note("kept by the stand-in")
other = Asked()
with console.use(other):
    console.note("written to the other channel")
console.note("kept again")
check("a stand-in put on the channel answers there", notes == ["kept by the stand-in", "kept again"], notes)
check("...and on that channel only: another in use writes the line itself", "".join(other.text).strip() == "[written to the other channel]", other.text)
console.put("note", plain_note)
out = io.StringIO()
with contextlib.redirect_stdout(out):
    console.note("as before")
check("...and what was read before it is put back the same way", out.getvalue().strip() == "[as before]" and len(notes) == 2, out.getvalue())
try:
    console.put("note", console.note)
    refused = ""
except TypeError as e:
    refused = str(e)
check("the console's own function is refused as a stand-in (it would only call itself): console.now reads what answers", "console.now" in refused, refused)


class Quiet(console.Channel):
    def __init__(self):
        self.said = []

    def write(self, text, end="\n"):
        pass

    def note(self, message):
        self.said.append(message)


quiet = Quiet()
with console.use(quiet):
    console.note("to its own method")
check("a channel that has an output of its own answers with it", quiet.said == ["to its own method"], quiet.said)


class Titled(console.Channel):
    header = "a field, not an output"

    def __init__(self):
        self.text = []

    def write(self, text, end="\n"):
        self.text.append(text)


titled = Titled()
with console.use(titled):
    try:
        console.header("A heading")
        drew = "".join(titled.text)
    except TypeError as e:
        drew = f"raised: {e}"
check("...and a field of a channel that only shares an output's name is not taken for its answer", "A heading" in drew, drew)
check("...and none of that wrote to the module", module_now() == AT_IMPORT)

# ---- the window supplies a channel
before = console.channel()
b1, b2 = bridge_mod.Bridge(), bridge_mod.Bridge()
up = {}
b1.install()                                               # stdout is the window's while it is up: what is found is checked after
try:
    page = console.channel()
    up["page"] = page is b1.page and isinstance(page, console.Channel) and page is not before
    up["seam"] = [n for n in SEAM if console.now(n) != getattr(b1, n)]
    up["draws"] = (console.windowed(), console.width())
    up["module"] = [k for k, v in module_now().items() if AT_IMPORT.get(k) != v]
    with console.scope("#journal"):
        console.panel("shop", {"wares": [{"name": "a coil of rope", "price": 12}]})
    with console.use(b2.page):
        with console.scope("#journal"):
            console.panel("shop", {"wares": []})
        console.busy_text("Only the second window waits.")
    b2.busy(True)
finally:
    b1.uninstall()
kinds = lambda b: [ev["k"] for _, ev in b.log]
check("a window up: the process's channel is its page", up.get("page"))
check("...which answers every name of the seam with the window's own", up.get("seam") == [], up.get("seam"))
check("...draws for itself and does its own wrapping", up.get("draws") == (True, bridge_mod.WRAP_WIDTH), up.get("draws"))
check("...and the console module is as it was at import", up.get("module") == [], up.get("module"))
check("two windows are two pages: what one is sent the other is not", kinds(b1).count("panel") == 1 and kinds(b2).count("panel") == 1
      and [ev["text"] for _, ev in b2.log if ev["k"] == "busy"] == ["Only the second window waits."] and "busy" not in kinds(b1), (kinds(b1), kinds(b2)))
check("the window gone: the channel is the one before it, and the terminal answers again", console.channel() is before and not console.windowed()
      and console.width() == 92 and console.panel("shop", {}) is False)
check("...and the module was not written", module_now() == AT_IMPORT)

# ---- an operation's hold, the question fence and the tap wrap the channel that is current
BASE = Path("saves/output_channel_635")
shutil.rmtree(BASE, ignore_errors=True)
g = simlib.campaign("output_channel_635", cls="warrior", seed=3, location="parth")
ws = g.scene
config.TURN_LOG_PATH = str(BASE / "turns.jsonl")
ws.enter("parth")
check("a scene built: the module is still as it was at import (the tap is on the channel)", module_now() == AT_IMPORT)
shown = []
console.put("note", lambda m: shown.append(m))
apart = Asked()
with ws.operation("test", "a step that stands") as op:
    console.note("held until it stands")
    inside = list(shown)
    with console.use(apart):
        console.note("another channel's line")
    check("an operation holds its channel's lines until it stands", inside == [] and any(h[0] == "note" for h in op.held), (inside, op.held))
    check("...and not another channel's: its line is written at once", "".join(apart.text).strip() == "[another channel's line]"
          and len([h for h in op.held if h[0] == "note"]) == 1, (apart.text, op.held))
    check("...without writing to the module", module_now() == AT_IMPORT)
check("...and when it stands its channel is told, through what answered before the hold", shown == ["held until it stands"], shown)
console.put("note", plain_note)
own = Asked()
with console.use(own):
    with ws.operation("test", "a step that stands on another channel") as op:
        console.note("held on the channel in use")
        waiting = (list(own.text), [h[0] for h in op.held])
check("an operation played on another channel holds that channel's lines, and tells it when it stands", waiting == ([], ["note"])
      and "".join(own.text).strip() == "[held on the channel in use]", (waiting, own.text))

answers = iter(["yes"])
real_ask = console.now("ask")
console.put("ask", lambda main=False, menu=False: next(answers))
fenced = {}
with questions.fence():
    try:
        console.ask()
        fenced["this"] = "answered"
    except questions.AskedInsideTurn:
        fenced["this"] = "refused"
    with console.use(apart):
        fenced["other"] = console.ask()
    fenced["module"] = module_now() == AT_IMPORT
fenced["after"] = console.ask()
console.put("ask", real_ask)
check("the question fence is put on the channel that is current, and taken off after the turn", fenced == {"this": "refused", "other": "a line typed",
      "module": True, "after": "yes"}, fenced)
with console.use(own):
    with questions.fence():
        try:
            fenced["own"] = console.ask()
        except questions.AskedInsideTurn:
            fenced["own"] = "refused"
    fenced["own after"] = console.ask()
check("...a turn played on another channel fences that one", (fenced["own"], fenced["own after"]) == ("refused", "a line typed"), fenced)

tapped = Asked()
with console.use(tapped):
    count = turnlog.shown_count()
    console.note("before the tap")
    untapped = turnlog.shown_count() - count
    turnlog.tap()
    turnlog.tap()
    console.note("after the tap")
    once = turnlog.shown_count() - count - untapped
check("the turn log's tap is put on the channel that is current, once: a line there is counted once, and a channel not tapped is not counted",
      (untapped, once) == (0, 1), (untapped, once))
g.close()

# ---- the channel in use is this thread's
seen = {}
elsewhere = Asked()


def other_thread():
    seen["channel"] = console.channel()
    with console.use(elsewhere):
        seen["inside"] = console.channel()
        ready.set()
        go.wait(5)


ready, go = threading.Event(), threading.Event()
with console.use(mine):
    t = threading.Thread(target=other_thread)
    t.start()
    ready.wait(5)
    here = console.channel()
    go.set()
    t.join()
check("a channel in use is this thread's: another thread has the process's, and its own does not reach here",
      seen.get("channel") is before and seen.get("inside") is elsewhere and here is mine, (seen, here))
player = actor.ActorContext(out=apart)
with actor.bind(player):
    bound = console.channel()
    t = threading.Thread(target=lambda: seen.update(unbound=console.channel()))
    t.start()
    t.join()
check("an actor's own channel is the console's while it is bound, on its thread only", bound is apart and seen.get("unbound") is before
      and console.channel() is before, (bound, seen.get("unbound")))


# ---- no file in the repository assigns to a console attribute
def assigned(source: str) -> list:
    """The console attributes a file sets or deletes: by assignment, by setattr or delattr, through the module's dict, under any
    name the module was imported by."""
    tree = ast.parse(source)
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module == "ui":
            names |= {a.asname or a.name for a in n.names if a.name == "console"}
        if isinstance(n, ast.Import):
            names |= {a.asname for a in n.names if a.name == "ui.console" and a.asname}

    def is_console(x) -> bool:
        if isinstance(x, ast.Name):
            return x.id in names
        if isinstance(x, ast.Attribute) and x.attr == "console" and isinstance(x.value, ast.Name) and x.value.id == "ui":
            return True
        if isinstance(x, ast.Subscript) and "sys.modules" in ast.unparse(x.value) and "ui.console" in ast.unparse(x.slice):
            return True
        if isinstance(x, ast.Call) and ast.unparse(x.func) == "vars" and x.args and is_console(x.args[0]):
            return True
        return isinstance(x, ast.Attribute) and x.attr == "__dict__" and is_console(x.value)

    found = []
    for n in ast.walk(tree):
        targets = []
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Delete)):
            for t in (n.targets if isinstance(n, (ast.Assign, ast.Delete)) else [n.target]):
                targets += [x for x in ast.walk(t) if isinstance(x, (ast.Attribute, ast.Subscript)) and isinstance(x.ctx, (ast.Store, ast.Del))]
        for t in targets:
            if is_console(t.value):
                found.append((n.lineno, ast.unparse(t)))
        if isinstance(n, ast.Call) and ast.unparse(n.func) in ("setattr", "delattr") and n.args and is_console(n.args[0]):
            found.append((n.lineno, ast.unparse(n)[:60]))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("update", "pop", "setdefault", "__setitem__", "clear") \
                and is_console(n.func.value):
            found.append((n.lineno, ast.unparse(n)[:60]))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("__setattr__", "__delattr__") \
                and (is_console(n.func.value) or (n.args and is_console(n.args[0]))):
            found.append((n.lineno, ast.unparse(n)[:60]))
    return found


CAUGHT = {
    "an output replaced": "from ui import console\nconsole.note = lambda m: None\n",
    "two in one statement": "from ui import console\nconsole.ask, console.note = a, b\n",
    "one among other targets": "from ui import console\nreal, console.ask = console.ask, fake\n",
    "under another name": "import ui.console as c\nc.panel = draw\n",
    "by its whole name": "import ui.console\nui.console.say = f\n",
    "by setattr": "from ui import console\nsetattr(console, name, fn)\n",
    "by delattr": "from ui import console\ndelattr(console, 'note')\n",
    "deleted": "from ui import console\ndel console.note\n",
    "added to": "from ui import console\nconsole.WIDTH += 8\n",
    "through its dict": "from ui import console\nvars(console)['note'] = f\n",
    "through its dict, updated": "from ui import console\nconsole.__dict__.update(note=f)\n",
    "through sys.modules": "import sys\nsys.modules['ui.console'].note = f\n",
    "inside a function": "def quiet():\n    from ui import console as _c\n    _c.narrate = lambda t: None\n",
    "the window's flag": "from ui import console\nconsole.damage_tags = True\n",
    "past the module's refusal": "import types\nfrom ui import console\ntypes.ModuleType.__setattr__(console, 'note', f)\n",
    "by its own __delattr__": "from ui import console\nconsole.__delattr__('note')\n",
}
PASSED = {
    "a stand-in put on the channel": "from ui import console\nconsole.put('note', lambda m: None)\n",
    "a channel's own field": "from ui import console\nconsole.channel().windowed = True\n",
    "a call": "from ui import console\nconsole.note('x')\n",
    "a read": "from ui import console\nreal = console.now('ask')\nw = console.WIDTH\n",
    "another object called console": "console = Thing()\nconsole.note = f\n",
    "another module's attribute": "from ui import console\nimport config\nconfig.MAX_TOKENS = console.width()\n",
}
check("the search catches every way a console attribute is written", all(assigned(s) for s in CAUGHT.values()), [k for k, s in CAUGHT.items() if not assigned(s)])
check("...and passes what is not one", not any(assigned(s) for s in PASSED.values()), [k for k, s in PASSED.items() if assigned(s)])
files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True, text=True).stdout.split()
ME = Path(__file__).name
writers, unread = {}, []
for f in files:
    if Path(f).name == ME or not Path(f).exists():
        continue
    try:
        got = assigned(Path(f).read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        unread.append(f)
        continue
    if got:
        writers[f] = got
check("every one of them was read", not unread, unread)
check(f"no file in the repository assigns to a console attribute ({len(files)} files: the game, the tools, the tests)", not writers and len(files) > 700,
      (len(writers), sum(len(v) for v in writers.values()), sorted(writers.items())[:6]))

actor.prefs().debug = was_debug
shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
