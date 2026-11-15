"""(f628) The parts of today's code that phase 3 moves, held to the pins written for them (docs/design/20_phase3_plan.md). The
pins hold behaviour and must pass unchanged while the code moves: tools/sim/turn_fields_628_test.py for a line's fields,
tools/sim/output_seam_628_test.py for what the window is sent. This test is the other half. It reads how the code does it today,
so that until each part moves nothing new can join it without being pinned first:
- every field the turn's table says a new line resets is one the line pin holds (engine/actor.py FIELDS);
- (f635) every name the seam pin calls is one the channel answers (ui/console.py SEAM, and a channel's `windowed` and `width`
  for the two the window used to set), and a window's page answers each with the window's own. That nothing assigns a console
  attribute any more is held by tools/sim/output_channel_635_test.py, over every file.
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


# ---- a line's fields: the turn's table (f631) names the ones a new line resets, and the scene's begin_line sets none by hand
LINE = held_set("turn_fields_628_test.py", "LINE")
from engine import actor
declared = {k for k, f in actor.FIELDS.items() if actor.LINE in f.marks}
tree = ast.parse((ROOT / "scenes" / "world.py").read_text(encoding="utf-8"))
begin = next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == "begin_line")
check("every field a new line resets is one the line pin holds (a field marked LINE in the turn's table is pinned there first)",
      declared == LINE and not self_fields(begin), (sorted(declared ^ LINE), sorted(self_fields(begin))))

# ---- the seam is the channel's (f635)
SEAM = held_set("output_seam_628_test.py", "SEAM")
FIELDS = {"damage_tags": "windowed", "WIDTH": "width"}                   # the two the window set by hand: a channel's own fields
check("every name the seam pin calls is one the channel answers (one added to the seam is pinned there first)",
      SEAM == set(console.SEAM) | set(FIELDS) and all(callable(getattr(console.Channel, n)) for n in console.SEAM)
      and all(hasattr(console.Channel, f) for f in FIELDS.values()), sorted(SEAM ^ (set(console.SEAM) | set(FIELDS))))
before = {k: console.now(k) for k in console.SEAM}
b = bridge_mod.Bridge()
b.install()
try:
    up = {k: console.now(k) for k in console.SEAM}
    flags = (console.damage_tags, console.WIDTH)
finally:
    b.uninstall()
check("while the window is up each of them is the window's own", all(up[k] == getattr(b, k) and up[k] != before[k] for k in console.SEAM)
      and flags == (True, bridge_mod.WRAP_WIDTH), ([k for k in console.SEAM if up[k] != getattr(b, k)], flags))
check("when the window goes each is what it was before", all(console.now(k) == before[k] for k in console.SEAM)
      and (console.damage_tags, console.WIDTH) == (False, 92), [k for k in console.SEAM if console.now(k) != before[k]])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
