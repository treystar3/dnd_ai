"""(f628) The parts of today's code that phase 3 moves, held to the pins written for them (docs/design/20_phase3_plan.md). The
pins hold behaviour and must pass unchanged while the code moves: tools/sim/turn_fields_628_test.py for a line's fields,
tools/sim/output_seam_628_test.py for what the window is sent. This test is the other half. It reads how the code does it today,
so that until each part moves nothing new can join it without being pinned first:
- every field begin_line resets is one the line pin holds (f631 replaces this check with its declared table);
- every console attribute the window swaps is one the seam pin calls, and the window puts each back (f635 replaces these);
- every place the game's code assigns a console attribute is recorded, and the list only shrinks (f635 brings it to none).
Each feature that moves a part replaces its check here with the fence over what took its place.
Run: python tools/sim/moving_parts_628_test.py"""
import ast
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import ui.console as console
from ui.gui import bridge as bridge_mod

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent


def held_set(test: str, name: str) -> set:
    """The set a pin holds under `name`, read from the pin's own source."""
    tree = ast.parse((HERE / test).read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return set(ast.literal_eval(node.value))


def self_fields(fn) -> set:
    out = set()
    for node in ast.walk(fn):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
        for t in targets:
            out |= {x.attr for x in ast.walk(t) if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == "self"}
    return out


def console_targets(node) -> set:
    """The console attributes a statement assigns: `console.x = ...`, a tuple of them, or setattr(console, name, ...)."""
    out = set()
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
    for t in targets:
        out |= {x.attr for x in ast.walk(t) if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id in ("console", "_c")}
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr" and node.args
            and isinstance(node.args[0], ast.Name) and node.args[0].id in ("console", "_c")):
        out.add("*" if not isinstance(node.args[1], ast.Constant) else str(node.args[1].value))
    return out


def assigned_in(path: Path) -> set:
    return set().union(set(), *(console_targets(n) for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))))


# ---- a line's fields (until f631)
LINE = held_set("turn_fields_628_test.py", "LINE")
tree = ast.parse((ROOT / "scenes" / "world.py").read_text(encoding="utf-8"))
begin = next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == "begin_line")
check("every field a new line resets is one the line pin holds (a field added to begin_line is pinned there first)",
      self_fields(begin) == LINE, sorted(self_fields(begin) ^ LINE))

# ---- the window's swaps (until f635)
SEAM = held_set("output_seam_628_test.py", "SEAM")
tree = ast.parse((ROOT / "ui" / "gui" / "bridge.py").read_text(encoding="utf-8"))
install = next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == "install")
swapped = set().union(*(console_targets(n) for n in ast.walk(install)))
check("every console attribute the window swaps is one the seam pin calls (one added to install is pinned there first)",
      swapped == SEAM, sorted(swapped ^ SEAM))
before = {k: getattr(console, k) for k in SEAM}
b = bridge_mod.Bridge()
b.install()
try:
    up = {k: getattr(console, k) for k in SEAM}
finally:
    b.uninstall()
check("while the window is up each of them is the window's own", all(up[k] is not before[k] for k in SEAM - {"damage_tags", "WIDTH"})
      and up["damage_tags"] is True and up["WIDTH"] == bridge_mod.WRAP_WIDTH, [k for k in SEAM if up[k] is before[k]])
check("when the window goes each is what it was before", all(getattr(console, k) is before[k] or getattr(console, k) == before[k] for k in SEAM),
      [k for k in SEAM if getattr(console, k) is not before[k]])

# ---- every place the game's code assigns a console attribute (until f635): the list only shrinks
RECORDED = {
    "engine/questions.py": {"ask"},                      # the fence round a question asked inside an operation
    "engine/recording.py": {"ask", "*"},                 # the recorder's wrap of the line asked for and of what is told
    "engine/turnlog.py": {"*"},                          # the turn log's tap on what is shown
    "scenes/world.py": {"*"},                            # an operation holding its lines until it stands
    "ui/gui/bridge.py": SEAM,                            # the window
}
found = {}
for folder in ("engine", "scenes", "services", "npc", "storage", "llm", "ui", "core", "world"):
    for path in sorted((ROOT / folder).rglob("*.py")):
        if path == ROOT / "ui" / "console.py":
            continue                                     # the module's own definitions
        if assigned_in(path):
            found[path.relative_to(ROOT).as_posix()] = assigned_in(path)
for path in sorted(ROOT.glob("*.py")):
    if path.name not in ("simlib.py", "simbot.py") and assigned_in(path):    # the harnesses mute or watch the console; they are not the game
        found[path.name] = assigned_in(path)
extra = {f: sorted(n - RECORDED.get(f, set())) for f, n in found.items() if n - RECORDED.get(f, set())}
check("no code assigns a console attribute but the places recorded here (a new one goes through the channel instead)", not extra, extra)
gone = {f: sorted(n - found.get(f, set())) for f, n in RECORDED.items() if n - found.get(f, set())}
check("...and every recorded place still does (one that stopped is taken off the list)", not gone, gone)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
