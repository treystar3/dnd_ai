"""(f743) A tool clears only a save it made itself (storage/saves.py scratch and drop), and says so when the clearing did not happen.
Every tool and harness removed saves/<the name it was handed> before it began, whatever that folder was: `nightrun --save main`, or
the name of any game on the Load page, removed the player's game unasked; `--save ..` named a folder outside saves/; and on Windows
a folder with a file held open was left half removed in silence, after which the tool played on in what was left. Event_trial kept
its reports inside the save its next Trial removes, so with `both` the campaign's report was gone seconds after its path was printed.
Held here, in a saves folder of its own (nothing here reaches the real saves/: every removal is watched, and only the test's own
folders are ever really removed):
- the case that found it: nightrun's start with --save naming a game the Load page lists, and with --save `..` or `../x`, removes
  nothing, opens nothing, and stops with a line naming the folder;
- second cases of the kind: simlib.campaign given the old single save's name `main`, or a game's name copied in from another install
  (`game_<when>`), is refused; a hand-made copy of a game, in no index and with no mark, named on a command line is refused (the
  owner's answer: a typed name is refused unless a tool marked it), while an old tool folder with no mark named in a tool's or a
  test's own code is taken as the tool's own, cleared and marked; a folder that cannot be cleared (a file in it held open) is
  reported, never played on; drop() removes a tool's own save and nothing else, and in a `finally` never hides the run's crash; a
  Trial's report is still there after the next Trial of the same name, and pulse_preview's lies outside its scratch world;
- and a fence over git's list: no tracked file but storage/saves.py calls shutil.rmtree on a path under saves/, and the tests' own
  such calls in tools/sim may only fall.
Run: python tools/sim/scratch_save_743_test.py"""
import ast
import contextlib
import io
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
import storage.campaign as campaign_module
from engine.session import CampaignSession
from storage import saves
from storage.campaign import CampaignStore, PlayerState

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)

BASE = Path(tempfile.mkdtemp(prefix="scratch_save_")).resolve()
SAVES = BASE / "saves"
SAVES.mkdir()
saves.SAVES_DIR = SAVES                                      # nothing here can reach the real saves/
campaign_module.SAVES_DIR = SAVES
SETTINGS = {k: getattr(config, k) for k in dir(config) if k.isupper()}
TOOL_MARK = getattr(saves, "SCRATCH", "scratch.json")


class Stop(Exception):
    """The tool went on to open its save."""


def tool(fn, held=False, stop=True):
    """fn() with every removal watched: what it asked to remove, whether it went on to open a save (stopped there unless stop=False),
    and the line it stopped with. Only folders under BASE are ever really removed; with held=True none is, as Windows leaves a folder
    with a file held open."""
    asked, opened, said, error = [], [], "", ""
    real_rmtree, real_open = shutil.rmtree, CampaignSession.open

    def rmtree(path, *a, **k):
        asked.append(Path(path))
        p = Path(path).resolve()
        if not held and BASE in p.parents:
            return real_rmtree(path, *a, **k)

    def opening(cls, name, *a, **k):
        opened.append(name)
        raise Stop(name)
    shutil.rmtree = rmtree
    if stop:
        CampaignSession.open = classmethod(opening)
    try:
        fn()
    except Stop:
        pass
    except SystemExit as e:
        said = str(e.code)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    finally:
        shutil.rmtree, CampaignSession.open = real_rmtree, real_open
        for k, v in SETTINGS.items():
            setattr(config, k, v)
    return {"asked": asked, "opened": opened, "said": said, "error": error}


def night(*args):
    """nightrun's own start, as `python tools/nightrun.py --stub ...` begins."""
    import nightrun
    sys.argv = ["nightrun.py", "--stub", "--out", str(BASE / "night"), *args]
    nightrun.main()


def game(name, char_name="Ada Venn", touched=True):
    """A game the player made: its database and character, and (touched) the mark and index entry the game gives it."""
    st = CampaignStore.open_or_create(name, saves_dir=SAVES)
    c, _ = simlib.make_character("warrior", random.Random(1))
    c.name = char_name
    st.save_player(PlayerState(character=c, location="parth"))
    st.close()
    if touched:
        saves.touch(name, SAVES)
    return SAVES / name


def whole(folder):
    return (folder / "campaign.db").is_file()


def attempt(fn):
    try:
        return fn(), ""
    except SystemExit as e:
        return None, str(e.code)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


# ---- 1. the case that found it: nightrun --save names a game the Load page lists, or a folder outside saves/
listed = game("game_20261101_101010")
check("(the game is on the Load page)", [s["name"] for s in saves.list_saves(SAVES)] == ["game_20261101_101010"], saves.list_saves(SAVES))
r = tool(lambda: night("--save", "game_20261101_101010"))
check("nightrun --save <a game the Load page lists> removes nothing of it", not r["asked"], r)
check("...does not open it to play its own character in", not r["opened"], r)
check("...and stops with a line naming the folder", "game_20261101_101010" in r["said"], r)
check("...the game is whole and still listed", whole(listed) and [s["name"] for s in saves.list_saves(SAVES)] == ["game_20261101_101010"])
for name in ("..", "../x", "..\\x", "_deleted"):
    r = tool(lambda: night("--save", name))
    check(f"nightrun --save {name!r} names nothing outside the tools' saves: nothing removed, nothing opened",
          not r["asked"] and not r["opened"], r)
    check(f"...and it says why ({name!r})", r["said"] and name in r["said"], r)

# ---- 2. second cases of the kind
old_main = game("main", "Bram Holt", touched=False)          # the old single save, from before the marks
r = tool(lambda: simlib.campaign("main"))
check("simlib.campaign('main'), the old single save's name, is refused: nothing removed, nothing opened",
      not r["asked"] and not r["opened"] and "main" in r["said"], r)
check("...and the old save is whole", whole(old_main))
copied = game("game_20250601_090000", "Cora Lind", touched=False)   # a game copied in from another install: no mark yet, no index
r = tool(lambda: simlib.campaign("game_20250601_090000"))
check("a game's name copied in from another install (game_<when>) is refused, though no mark or index names it yet",
      not r["asked"] and not r["opened"] and "game_20250601_090000" in r["said"], r)
check("...and that game is whole", whole(copied))

hand = game("my_copy", "Dara Venn", touched=False)            # a copy of a game made by hand: no index, no mark of any kind
r = tool(lambda: night("--save", "my_copy"))
check("a hand-made copy with no mark, named on a command line, is refused: nothing removed, nothing opened",
      not r["asked"] and not r["opened"] and "my_copy" in r["said"], r)
check("...and the copy is whole", whole(hand))

old_tool = game("old_tool_save", "Eli Moss", touched=False)   # a tool's or a test's save from before the tools' mark
r = tool(lambda: simlib.campaign("old_tool_save"))
check("an unmarked old tool save named in a test's own code is taken as the tool's own: cleared, marked, then opened",
      r["opened"] == ["old_tool_save"] and not r["said"] and not r["error"] and not whole(old_tool)
      and (old_tool / TOOL_MARK).is_file(), r)
r = tool(lambda: night("--save", "old_tool_save"))
check("...and once marked, a typed --save of that name clears it and plays on in it",
      r["opened"] == ["old_tool_save"] and not r["said"] and not r["error"] and (old_tool / TOOL_MARK).is_file(), r)

made = game("held_tool", "Fen Ash", touched=False)
r = tool(lambda: simlib.campaign("held_tool"), held=True)
check("a folder that could not be cleared (a file in it held open) is reported, never played on in silence",
      not r["opened"] and "held_tool" in r["said"], r)
check("...and it keeps the tools' mark, so the next run can clear it", (made / TOOL_MARK).is_file(), sorted(p.name for p in made.iterdir()))
if os.name == "nt":                                           # the real thing: Windows will not remove a database another connection holds
    holder = sqlite3.connect(made / "campaign.db")
    holder.execute("SELECT 1").fetchall()
    r = tool(lambda: simlib.campaign("held_tool"))
    check("(Windows) a database held open by another connection: the clearing is reported", not r["opened"] and "held_tool" in r["said"], r)
    holder.close()
r = tool(lambda: simlib.campaign("held_tool"))
check("...and once let go, the same name clears and opens", r["opened"] == ["held_tool"] and not r["said"] and not r["error"], r)

ours, why = attempt(lambda: saves.drop("my_copy"))
check("drop() on a folder with no tools' mark removes nothing", ours is False and whole(hand), (ours, why))
ours, why = attempt(lambda: saves.drop("game_20261101_101010"))
check("drop() on a game removes nothing", ours is False and whole(listed), (ours, why))
ours, why = attempt(lambda: saves.drop(".."))
check("drop() of a name outside saves/ removes nothing", ours is False and SAVES.is_dir(), (ours, why))
ours, why = attempt(lambda: saves.drop("held_tool"))
check("drop() removes a tool's own save", ours is True and not made.exists(), (ours, why))
ours, why = attempt(lambda: saves.drop("held_tool"))
check("...and of one no longer there says nothing was removed", ours is False, (ours, why))
gone = SAVES / "drop_held"
ours, why = attempt(lambda: saves.scratch("drop_held"))
r = tool(lambda: saves.drop("drop_held"), held=True)
check("drop() that could not clear the folder says so", "drop_held" in r["said"] and gone.is_dir(), r)


caught = []


def crash_then_drop():
    try:
        try:
            raise ValueError("the run's own crash")
        finally:
            saves.drop("drop_held")
    except ValueError as e:
        caught.append(e)


r = tool(crash_then_drop, held=True)
shown = "".join(traceback.format_exception(caught[0])) if caught else ""
check("drop() in a finally while the run crashes: the crash goes on with its own traceback, and that traceback names the folder",
      len(caught) == 1 and not r["said"] and not r["error"] and "the run's own crash" in shown and "drop_held could not be cleared" in shown
      and gone.is_dir(), (r, shown[-400:]))

# the reports: a Trial's report is still there after the next Trial of the same save
from tools import event_trial
event_trial.ROOT = BASE                                       # the tool's own root: its saves are the test's
config.LOG_PATH = str(BASE / "logs" / "llm_calls.jsonl")     # the folder a run's logs go to (SUITE-2's, when one is set)
printed = io.StringIO()
sys.argv = ["event_trial.py", "both", "--days", "3", "--ignore"]
with contextlib.redirect_stdout(printed):
    r = tool(lambda: event_trial.main(), stop=False)
reports = [Path(m) if Path(m).is_absolute() else BASE / m for m in re.findall(r"report: (.+)", printed.getvalue())]
check("(event_trial both wrote two reports)", len(reports) == 2 and not r["error"], (r, printed.getvalue()[-600:]))
check("the campaign's report is still there once the cataclysm's Trial, on the same save, has begun and ended",
      len(reports) == 2 and all(p.is_file() for p in reports), [(str(p), p.exists()) for p in reports])
check("...and the reports lie outside every save", reports and not any(SAVES in p.parents for p in reports), reports)
check("...in the run's log folder", reports and all((BASE / "logs") in p.parents for p in reports), reports)
from tools import pulse_preview                              # a second tool's report: never inside the scratch world --fresh clears
config.LOG_PATH = str(BASE / "logs" / "llm_calls.jsonl")
printed = io.StringIO()
sys.argv = ["pulse_preview.py", "--stub", "--tier", "normal", "--fresh", "--seed", "1"]
with contextlib.redirect_stdout(printed):
    r = tool(lambda: pulse_preview.main(), stop=False)
saved = [Path(m) for m in re.findall(r"\(saved to (.+)\)", printed.getvalue())]
check("pulse_preview --stub --fresh: its report is written outside every save, in the run's log folder",
      len(saved) == 1 and saved[0].is_file() and SAVES not in saved[0].parents and (BASE / "logs") in saved[0].parents
      and not r["error"] and not r["said"], (r, saved, printed.getvalue()[-600:]))
for k, v in SETTINGS.items():
    setattr(config, k, v)

# ---- 3. the fence: no file removes a save by hand but storage/saves.py
SAVE_TEXT = re.compile(r"""["']saves[/"'\\]|SAVES_DIR\b""")
TESTS_MOST = 529                                             # (f743) the tests' own removals of a save: this may only fall


def removals_of_saves(text):
    """The lines where shutil.rmtree is called on a path under saves/: its argument names saves, or a name in it was given a value that does."""
    tree = ast.parse(text)
    given = {}
    for node in ast.walk(tree):
        pairs = []
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            pairs = [(t, node.value) for t in (node.targets if isinstance(node, ast.Assign) else [node.target])]
        elif isinstance(node, (ast.For, ast.comprehension)):
            pairs = [(node.target, node.iter)]
        for target, value in pairs:
            given.setdefault(ast.unparse(target), []).append(ast.unparse(value))

    def names_saves(src, depth=0):
        if SAVE_TEXT.search(src):
            return True
        if depth > 3:
            return False
        try:
            parts = {ast.unparse(n) for n in ast.walk(ast.parse(src, mode="eval")) if isinstance(n, (ast.Name, ast.Attribute))}
        except SyntaxError:
            return False
        return any(names_saves(v, depth + 1) for p in parts for v in given.get(p, []) if v != src)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and ast.unparse(node.func) in ("shutil.rmtree", "rmtree") and node.args:
            if names_saves(ast.unparse(node.args[0])):
                out.append(node.lineno)
    return out


files = subprocess.run(["git", "ls-files", "--cached", "*.py"], cwd=ROOT, capture_output=True, text=True).stdout.split()
outside, in_tests = {}, 0
for f in files:
    if not (ROOT / f).is_file():
        continue
    lines = removals_of_saves((ROOT / f).read_text(encoding="utf-8"))
    if f.startswith("tools/sim/"):
        in_tests += len(lines)
    elif lines and f != "storage/saves.py":
        outside[f] = lines
check("(the fence reads: storage/saves.py is seen)", "storage/saves.py" in files)
check("no file but storage/saves.py removes a save by hand: every tool and harness goes through scratch() and drop()", not outside,
      sorted(outside.items()))
check(f"the tests' own removals of a save do not grow ({in_tests} of at most {TESTS_MOST})", in_tests <= TESTS_MOST, in_tests)

shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}", file=sys.__stdout__)
sys.exit(1 if bad else 0)
