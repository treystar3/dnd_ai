"""(f580) The console writes to a channel. Every line the game shows goes out through one place in ui/console.py: the current channel,
which by default writes to whatever sys.stdout is at that moment, in the same pieces the built-in print wrote (so the window, which takes
stdout, and every tool that captures it see what they saw). Another channel put in its place gets every function's text and stdout gets
none: the seam a second player's page hangs on (multiplayer, GOALS.md checklist 8). Nothing else moved: the functions are still found on
the module by name, the output gate still mends the story's lines, and no game code prints for itself.
Run: python tools/sim/channel_580_test.py"""
import ast
import builtins
import contextlib
import io
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import ui.console as console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

LONG = ("The ferry is late again and nobody on the landing is surprised; the ferryman's boy sits on a coil of rope, counting gulls, while "
        "two carters argue over whose turn it was to bring the lantern down from the toll house.")
CALLS = {
    "say": lambda: console.say("Horseshoes. Nails.\n(She wipes her hands on her apron.)\n" + LONG, "Brannoch"),
    "narrate": lambda: console.narrate("Rain on the thatch.\n\n" + LONG),
    "npc_says": lambda: console.npc_says("Ost the smith", LONG, "sets the tongs down"),
    "dialogue": lambda: console.dialogue("She looks up from the ledger.", "Maren", LONG, "She goes back to it."),
    "out": lambda: console.out("Saved. Until next time."),
    "out, nothing": lambda: console.out(),
    "setup_progress": lambda: console.setup_progress(0.5, "Waking the model"),
    "wait": lambda: console.wait("the world turns"),
    "note": lambda: console.note("You are carrying too much to run."),
    "ledger": lambda: console.ledger("12 silver paid"),
    "header": lambda: console.header("The Trading Square"),
    "show_journal": lambda: console.show_journal([LONG], ["Ost, the smith at the square"], ["a letter, delivered"]),
    "show_help": lambda: console.show_help(),
    "combat_panel": lambda: console.combat_panel(["You        HP 40/52", "Grey wolf  HP 9/30"]),
    "combat_numbers": lambda: console.combat_numbers(["12 slashing to the wolf", "the wolf misses"] * 4),
    "status_block": lambda: console.status_block("Day 3, dusk", "light rain", "Trading Square, Parth", "a quiet corner by the well",
                                                 {"health": (40.4, 52), "mana": (0, 0), "stamina": (11.0, 40)}, 3, 2, 12345, (120, 400)),
}


def to_stdout(fn) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue()


class Collect(console.Channel):
    """A channel that keeps what it is sent."""
    def __init__(self):
        self.text = ""

    def write(self, text: str, end: str = "\n") -> None:
        self.text += text + end


class Pieces:
    """A stdout that keeps each write and each flush as it comes, as the window's does."""
    def __init__(self):
        self.calls = []

    def write(self, s):
        self.calls.append(("write", s))
        return len(s)

    def flush(self):
        self.calls.append(("flush",))


def pieces(fn) -> list:
    out, was = Pieces(), sys.stdout
    sys.stdout = out
    try:
        fn()
    finally:
        sys.stdout = was
    return out.calls


# ---- the default channel is stdout, as it is at the moment of the call
check("there is a current channel, and by default it is the one that writes to stdout", isinstance(console.channel(), console.Channel)
      and console.channel() is console.STDOUT)
check("a stdout swapped in after the console loaded is the one written to (the window's way)", to_stdout(CALLS["narrate"]).count("Rain on the thatch.") == 1)
check("...in the pieces the built-in print wrote: the text, then the line's end",
      pieces(lambda: console.out("x")) == pieces(lambda: builtins.print("x")) and pieces(lambda: console.note("y")) == pieces(lambda: builtins.print("\n[y]")))
check("...a bare line as the line's end alone", pieces(lambda: console.combat_panel([])) == pieces(lambda: builtins.print()))
check("...and the load bar's unfinished line with its flush",
      pieces(lambda: console.setup_progress(0.5, "W")) == pieces(lambda: builtins.print("\r  W   50%   ", end="", flush=True)))

# ---- another channel gets every function's text, and stdout none
want = {k: to_stdout(f) for k, f in CALLS.items()}
got, leaked = {}, {}
for k, f in CALLS.items():
    c = Collect()
    with console.use(c):
        inside = console.channel() is c
        leaked[k] = to_stdout(f)
    got[k] = c.text
check("(a channel in use is the current one, and the one before it is back after)", inside and console.channel() is console.STDOUT)
check("a channel in use gets each function's text, the same text stdout got", got == want, [k for k in want if got[k] != want[k]])
check("...and stdout gets none of it", not any(leaked.values()), [k for k, v in leaked.items() if v])
outer, inner = Collect(), Collect()
with console.use(outer):
    console.out("one")
    with console.use(inner):
        console.out("two")
    console.out("three")
check("channels nest: the one before is back when the inner one is done, even after a fault", outer.text == "one\nthree\n" and inner.text == "two\n",
      (outer.text, inner.text))
try:
    with console.use(inner):
        raise RuntimeError("a fault inside")
except RuntimeError:
    pass
check("...even after a fault inside", console.channel() is console.STDOUT)

# ---- nothing else moved
check("the story's functions are still the gated ones, found on the module by name", all(getattr(getattr(console, n), "gated", False) for n in console.STORY))
c = Collect()
with console.use(c):
    console.narrate("The road runs on — into the trees.")
check("...and the gate still mends a story line on its way to a channel (no dash reaches it)", "—" not in c.text and "The road runs on" in c.text, c.text)
saved = {n: getattr(console, n) for n in ("narrate", "say", "note", "ledger", "panel")}
shown = simlib.quiet_console()
console.narrate("muted")
check("a function replaced on the module (a test's mute, the night's harness) is the one called", shown == [("narrate", "muted")], shown)
for n, f in saved.items():
    setattr(console, n, f)

# ---- one way out
tree = ast.parse(Path(console.__file__).read_text(encoding="utf-8"))
real = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "print"
        and isinstance(n.value, ast.Name) and n.value.id == "builtins"]
names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
check("the console has a print of its own, and reaches the built-in one in one place only (the stdout channel)", "print" in names and len(real) == 1, real)
loose = []
for d in ("engine", "scenes", "services", "npc", "world", "storage", "character", "core", "llm"):
    for path in sorted(Path(d).rglob("*.py")):
        for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print":
                loose.append(f"{path}:{n.lineno}")
check("no game code prints for itself: the console is the one way to the page", not loose, loose[:8])

# ---- a line that fails still tells its failure, through the channel
g = simlib.campaign("channel_580", seed=5, location="trading_square")
ws = g.scene
ws.enter("trading_square")


def no_reading(u, k):
    raise RuntimeError("the model could not read the line")


stub.a_ActionPlan = no_reading
stood = []
during, after = Collect(), Collect()
with console.use(during):
    leaked_line = to_stdout(lambda: stood.append(ws.turn("juggle three lanterns")))
with console.use(after):                                  # the game's loop tells a line it could not take (scenes/world.py run)
    leaked_line += to_stdout(lambda: console.narrate(ws.failed_line("juggle three lanterns")))
check("a line whose reading fails every try shows nothing of itself: no held line reaches the channel", stood == [False] and during.text == ""
      and bool(getattr(ws, "last_failure", "")), (stood, during.text[:200], getattr(ws, "last_failure", "")))
check("...the player is told so, on the channel", bool(after.text.strip()), after.text[:200])
check("...and nothing of it goes round the channel to stdout", leaked_line == "", leaked_line[:200])

g.session.close()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
