"""(f741) No test reaches the player's saves folder: a test's saves are a folder of its own outside the repository, one source names
the folder (storage.campaign.SAVES_DIR), and one predicate says whose a folder in it is (storage/saves.py whose).
Since f741 the Load page's reads write (a game's mark, saves/index.json), and every test ran in the player's own saves/: guard_test's
home.page listed it and rewrote its index. Held here by probes, each a test run in a process of its own and watched by an audit hook
that stops any file operation under the repository's saves/ before it happens, so nothing here reaches it:
- the case that found it: a test's home.page, in a test the suite runs and in one run by hand, lists the test's own saves folder,
  outside the repository, and nothing under saves/ is reached;
- second cases of the kind (a test reaching the saves folder by a default): the Load page's other doors (the list, Continue, a game
  touched, a new game's name, discard, delete), a test's own campaign (simlib.campaign, a session, the store), a tool's scratch and
  drop, a tool the test starts in a process of its own, character creation's copy of the character, the update check's record and
  the window's preferences; and a tool that imports simlib and is no test keeps saves/;
- one source: a test that points storage.campaign.SAVES_DIR at a folder finds every reader there (f744's test pointed only
  storage.saves' own, while scratch and drop read the other), no tracked file outside the tests names the folder another way, and
  the tests' own paths named under saves/ by hand may only fall;
- one predicate: every reader asks whose(), so a folder it calls a game is listed and never cleared, and one it calls a tool's is
  cleared and taken, whatever the files in it say.
Run: python tools/sim/own_saves_741_test.py"""
import ast
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)

REAL = ROOT / "saves"                                 # the repository's saves folder: the player's own, in the owner's checkout
HOOK = r'''
import os as _os, sys as _sys
STOPPED = []
class Stopped(BaseException):
    """A file operation on the repository's saves folder, stopped before it happened."""
_REAL = _os.path.normcase(%r)
_WATCHED = {"open", "os.listdir", "os.scandir", "os.mkdir", "os.rmdir", "os.remove", "os.rename", "os.chmod", "os.utime", "os.truncate",
            "shutil.rmtree", "shutil.move", "shutil.copyfile", "shutil.copytree", "sqlite3.connect", "glob.glob", "glob.glob/2"}
def _under(a):
    if not isinstance(a, (str, bytes, _os.PathLike)):
        return False
    s = _os.fsdecode(a)
    s = s[5:].split("?")[0] if s.startswith("file:") else s
    if not s or s == ":memory:":
        return False
    full = _os.path.normcase(_os.path.abspath(s))
    return full == _REAL or full.startswith(_REAL + _os.sep)
def _fence(event, args):
    if event in _WATCHED:
        for a in args[:2]:
            if _under(a):
                STOPPED.append(f"{event} {_os.fsdecode(a)}")
                raise Stopped(f"{event} on {_os.fsdecode(a)}")
_sys.addaudithook(_fence)
''' % str(REAL)
exec(HOOK)                                            # this process is watched too: nothing here may reach the real saves/


def same(a, b) -> bool:
    """Two paths are one, read without touching either (no resolve: a path under the real saves/ is never opened, not even to stat)."""
    return bool(a) and bool(b) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def outside(path) -> bool:
    p, root = os.path.normcase(os.path.abspath(path)), os.path.normcase(str(ROOT))
    return p != root and not p.startswith(root + os.sep)


BASE = Path(tempfile.mkdtemp(prefix="own_saves_")).resolve()
OUT = BASE / "out"
OUT.mkdir()

PROBE = HOOK + r'''
import json, random, subprocess
from pathlib import Path
ROOT = %r
_sys.path.insert(0, ROOT)
_sys.path.insert(0, ROOT + "/tools")
done, why, said, made = [], {}, {}, []
def step(name, fn):
    try:
        fn()
        done.append(name)
    except BaseException as e:
        why[name] = f"{type(e).__name__}: {e}"[:300]
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage import campaign, saves
from scenes import home
from world.loader import load_world
world = load_world()
step("simlib.campaign", lambda: simlib.campaign("probe_game").close())
step("saves.touch", lambda: saves.touch("probe_game"))
step("home.page", lambda: said.update(page=[s["name"] for s in home.page(world)["saves"]]))   # the case that found it (guard_test.py)
step("saves.list_saves", lambda: said.update(listed=[s["name"] for s in saves.list_saves()]))
step("saves.last", lambda: said.update(last=(saves.last() or {}).get("name")))
step("saves.load_index", lambda: saves.load_index())
step("saves.new_name", lambda: saves.new_name())
step("saves.adopt_legacy", lambda: saves.adopt_legacy())
def store():
    from storage.campaign import CampaignStore
    CampaignStore.open_or_create("probe_store").close()
step("CampaignStore.open_or_create", store)
def session():
    from engine.session import CampaignSession
    CampaignSession.open("probe_session").close()
step("CampaignSession.open", session)
step("saves.scratch", lambda: saves.scratch("probe_tool"))
step("saves.drop", lambda: saves.drop("probe_tool"))
step("saves.discard", lambda: saves.discard("probe_store"))
step("saves.delete", lambda: saves.delete("probe_game"))
def child():
    got = subprocess.run([_sys.executable, %r], capture_output=True, text=True, timeout=300)
    if got.returncode:
        raise RuntimeError(got.stdout[-300:] + got.stderr[-300:])
    made.append(got.stdout.strip().splitlines()[-1])
step("a tool the test starts", child)
def character():
    from character import creation
    c, _ = simlib.make_character("warrior", random.Random(1))
    made.append(str(creation.save_character(c)))
step("creation.save_character", character)
def update():
    from core import updates
    updates.note_attempt({"version": "9.9.9"})
    if (updates.attempted() or {}).get("version") != "9.9.9":
        raise RuntimeError("the record did not come back")
    made.append(str(updates.attempt_file()))
step("updates.note_attempt", update)
def prefs():
    from ui.gui import server
    made.append(str(server.prefs_path()))
    server.load_prefs()
step("the window's preferences", prefs)
own = _os.path.abspath(campaign.SAVES_DIR)
found = [] if _under(own) else sorted(p.relative_to(own).as_posix() for p in Path(own).rglob("*") if p.is_file())
print("PROBE " + json.dumps({"own": own, "env": _os.environ.get("MERAVIA_SAVES", ""), "done": done, "why": why, "stopped": STOPPED,
                             "said": said, "made": made, "found": found}))
'''
CHILD = HOOK + r'''
_sys.path.insert(0, %r)
from storage import saves
print(saves.scratch("probe_child"))
'''
TOOL = HOOK + r'''
import json
_sys.path.insert(0, %r)
import simlib
from storage import campaign
print("TOOL " + json.dumps({"own": str(campaign.SAVES_DIR), "env": _os.environ.get("MERAVIA_SAVES", "")}))
'''
child_py, probe_py, tool_py = BASE / "probe_child.py", BASE / "probe_test.py", BASE / "probe_tool.py"
child_py.write_text(CHILD % str(ROOT), encoding="utf-8")
probe_py.write_text(PROBE % (str(ROOT), str(child_py)), encoding="utf-8")
tool_py.write_text(TOOL % str(ROOT), encoding="utf-8")
plain = {k: v for k, v in os.environ.items() if k not in ("MERAVIA_SAVES", "MERAVIA_RAN", "MERAVIA_RAN_ROOT")}
plain["PYTHONUTF8"] = "1"
DOORS = ["simlib.campaign", "saves.touch", "saves.list_saves", "saves.last", "saves.load_index", "saves.new_name", "saves.adopt_legacy",
         "CampaignStore.open_or_create", "CampaignSession.open", "saves.scratch", "saves.drop", "saves.discard", "saves.delete",
         "a tool the test starts", "creation.save_character", "updates.note_attempt", "the window's preferences"]


def report(text, head="PROBE "):
    line = next((l for l in text.splitlines() if l.startswith(head)), "")
    return json.loads(line[len(head):]) if line else {"why": {"(the probe)": text[-800:]}}


def landed(r, kind):
    """What every probe's run holds: nothing under the real saves/ reached, every door gone through, all of it in the test's own folder."""
    own, found = r.get("own") or str(REAL), set(r.get("found") or [])
    check(f"{kind}: nothing reached the repository's saves/ (the audit hook stopped nothing)", r.get("own") and not r.get("stopped"),
          (r.get("stopped") or [])[:4] or r.get("why"))
    check(f"{kind}: the test's saves folder is its own, outside the repository", outside(own), own)
    check(f"{kind}: the case that found it: home.page lists the game in that folder, and its index is written there",
          r.get("said", {}).get("page") == ["probe_game"] and "index.json" in found, (r.get("why", {}).get("home.page"), r.get("said")))
    missed = [d for d in DOORS if d not in r.get("done", [])]
    check(f"{kind}: every other door to the saves folder goes through, in that folder", not missed, {d: r.get("why", {}).get(d) for d in missed[:5]})
    check(f"{kind}: ...the game touched is listed and is the one Continue opens, then moved to that folder's deleted games",
          r.get("said", {}).get("listed") == ["probe_game"] and r.get("said", {}).get("last") == "probe_game"
          and any(f.startswith("_deleted/probe_game_") and f.endswith("game.json") for f in found), (r.get("said"), sorted(found)[:8]))
    check(f"{kind}: ...a session, a tool's save and a tool the test started all made theirs there, and drop() took the tool's away",
          "probe_session/campaign.db" in found and "probe_child/scratch.json" in found and "probe_tool/scratch.json" not in found,
          sorted(found)[:12])
    check(f"{kind}: ...and character creation's copy, the update record and the window's preferences lie in it too",
          len(r.get("made", [])) == 4 and all(same(os.path.dirname(os.path.abspath(m)), own) for m in r["made"][1:])
          and same(r["made"][0], os.path.join(own, "probe_child")) and {"character.json", "update_attempt.json"} <= found, r.get("made"))
    return own


# ---- 1. the case that found it, and the doors of its kind: a test the suite runs
import run_suite
name, rc, took = run_suite.run_one(probe_py, OUT, 600, ROOT, record=False)
r = report((OUT / f"{probe_py.name}.out").read_text(encoding="utf-8", errors="replace"))
own = landed(r, "run by the suite")
check("run by the suite: the folder is the one the runner made for this run, and every process the test starts is told it",
      same(r.get("env"), own) and outside(own) and str(OUT).casefold() in os.path.abspath(own).casefold(), (r.get("env"), own))
check("...and a passed test's folder goes with its run", rc == 0 and outside(own) and not Path(own).exists(), rc)

# ---- 2. the same test run by hand
got = subprocess.run([sys.executable, str(probe_py)], cwd=ROOT, env=plain, capture_output=True, text=True, encoding="utf-8",
                     errors="replace", timeout=900)
r = report(got.stdout + got.stderr)
own = landed(r, "run by hand")
check("run by hand: simlib gave it a fresh folder outside the repository and told the processes it starts",
      same(r.get("env"), own) and outside(own) and str(OUT).casefold() not in os.path.abspath(own).casefold(), (r.get("env"), own))
check("...and the folder is gone when the test ends", got.returncode == 0 and outside(own) and not Path(own).exists(), got.returncode)

# ---- 3. a tool that imports simlib and is no test keeps the folder it had
got = subprocess.run([sys.executable, str(tool_py)], cwd=ROOT, env=plain, capture_output=True, text=True, encoding="utf-8",
                     errors="replace", timeout=300)
t = report(got.stdout + got.stderr, "TOOL ")
check("a tool that imports simlib (a night run, a replay) is no test: its saves are still saves/", t.get("own") == "saves" and not t.get("env"), t)

# ---- 4. one source: a test that points storage.campaign.SAVES_DIR at a folder finds every reader there
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage import campaign, saves
from storage.campaign import CampaignStore, PlayerState
from engine.session import CampaignSession
SAVES = BASE / "one_source"
SAVES.mkdir()
campaign.SAVES_DIR = SAVES
check("storage.saves keeps no saves folder of its own: storage.campaign.SAVES_DIR is the one", not hasattr(saves, "SAVES_DIR"),
      getattr(saves, "SAVES_DIR", None))


def attempt(fn):
    try:
        return fn(), ""
    except BaseException as e:
        return None, f"{type(e).__name__}: {e}"[:200]


attempt(lambda: CampaignStore.open_or_create("one_game").close())
attempt(lambda: saves.touch("one_game"))
listed, why = attempt(lambda: [s["name"] for s in saves.list_saves()])
check("f744's case: a test that points the one source finds the game it opened listed there", listed == ["one_game"]
      and (SAVES / "one_game" / "game.json").is_file() and (SAVES / "index.json").is_file(), (listed, why, STOPPED[-3:]))
folder, why = attempt(lambda: saves.scratch("one_tool"))
check("...a tool's scratch save lies in the same folder", folder == SAVES / "one_tool" and (SAVES / "one_tool").is_dir(), (folder, why))
gone, why = attempt(lambda: saves.drop("one_tool"))
check("...and drop() removes it there", gone is True and not (SAVES / "one_tool").exists(), (gone, why))
s, why = attempt(lambda: CampaignSession.open("one_session"))
if s is not None:
    s.close()
check("...a session opens its save there", (SAVES / "one_session" / "campaign.db").is_file(), why)
moved, why = attempt(lambda: saves.delete("one_game"))
check("...and delete() moves a game to that folder's deleted games", moved is not None and SAVES / "_deleted" in Path(moved).parents,
      (moved, why))
check("(nothing here reached the repository's saves/)", not STOPPED, STOPPED[:4])

# ---- 5. one source: no tracked file outside the tests names the saves folder another way
LITERAL = re.compile(r"""Path\(\s*f?["']saves\b|/\s*["']saves["']|f?["']saves[/\\]""")
OWN_FILES = {"tools/run_suite.py": "the runner's lock, and the folders it never walks", "tools/model_fence.py": "the folders it never reads"}
TESTS_LITERAL = re.compile(r"""["']saves[/\\"']""")
TESTS_LITERAL_MOST = 558                     # (f741) a test's path named under saves/ by hand lies apart from its save: this may only fall
files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], cwd=ROOT, capture_output=True,
                       text=True).stdout.split()
other, copied, tests_old, tests_literal = {}, {}, [], 0
for f in files:
    if not (ROOT / f).is_file():
        continue
    text = (ROOT / f).read_text(encoding="utf-8", errors="replace")
    if f.startswith("tools/sim/"):
        if re.search(r"\bsaves\.SAVES_DIR\b", text) and not f.startswith("tools/sim/own_saves_"):
            tests_old.append(f)
        tests_literal += sum(1 for line in text.splitlines() if TESTS_LITERAL.search(line))
        continue
    if f.startswith("docs/"):
        continue
    lines = [i for i, line in enumerate(text.splitlines(), 1) if LITERAL.search(line.split("#")[0])]
    if lines and f not in OWN_FILES:
        other[f] = lines
    try:
        tree = ast.parse(text)
    except SyntaxError:
        continue
    top = [n.lineno for n in tree.body if isinstance(n, ast.ImportFrom) and any(a.name == "SAVES_DIR" for a in n.names)]
    bound = [n.lineno for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             for d in n.args.defaults + n.args.kw_defaults if d is not None and "SAVES_DIR" in ast.unparse(d)]
    if top or bound:
        copied[f] = top + bound
check("(the fence reads: storage/saves.py and scenes/home.py are seen)", "storage/saves.py" in files and "scenes/home.py" in files)
check("no tracked file outside the tests builds a path to the saves folder from its name: each reads the one source",
      not other, sorted(other.items()))
check("...nor keeps a copy of it made at import or bound as a default, which a test pointing the source elsewhere would not move",
      not copied, sorted(copied.items()))
check("no test points storage.saves' own folder, which is no more: the one source is storage.campaign.SAVES_DIR", not tests_old, tests_old)
check(f"the tests' own paths named under saves/ by hand do not grow ({tests_literal} lines of at most {TESTS_LITERAL_MOST}): a new one "
      "takes simlib.saves_path(), in the folder the test's campaign opens", tests_literal <= TESTS_LITERAL_MOST, tests_literal)

# ---- 6. one predicate: every reader asks whose(), whatever the files in the folder say
P = BASE / "predicate"
P.mkdir()
campaign.SAVES_DIR = P


def folder_with(name, *marks, db=True, character=True):
    f = P / name
    f.mkdir()
    if db:
        st = CampaignStore.open_or_create(name, saves_dir=P)
        if character:
            c, _ = simlib.make_character("warrior", random.Random(1))
            c.name = name
            st.save_player(PlayerState(character=c, location="parth"))
        st.close()
    for m in marks:
        (f / m).write_text("{}", encoding="utf-8")
    return f


whose = getattr(saves, "whose", None)
check("storage/saves.py has the one predicate, whose()", callable(whose))
if callable(whose):
    unread = folder_with("unread_mark")
    (unread / "game.json").mkdir()                                # a mark that cannot be read still marks (f741)
    table = {"game": folder_with("a_game", "game.json"), "no_db": folder_with("no_db", "game.json", db=False), "unread": unread,
             "both": folder_with("both_marks", "game.json", "scratch.json"), "tool": folder_with("a_tool", "scratch.json"),
             "none": folder_with("no_mark")}
    want = {"game": saves.GAME, "no_db": saves.GAME, "unread": saves.GAME, "both": saves.GAME, "tool": saves.TOOL, "none": ""}
    got = {k: whose(f) for k, f in table.items()}
    check("whose(): the game's mark makes a game (with a database or not, readable or not, a tool's mark beside it or not); the tools' "
          "mark alone a tool's; neither, no one's", got == want, got)
    for f in table.values():
        shutil.rmtree(f, ignore_errors=True)

# the readers ask it: folders it calls a game with no mark on disk, and one it calls a tool's with no mark
GAME, TOOL = getattr(saves, "GAME", "game"), getattr(saves, "TOOL", "tool")
called = {"called_game": GAME, "called_new": GAME, "main": GAME, "called_tool": TOOL}
saves.whose = lambda folder: called.get(Path(folder).name) or (whose(folder) if callable(whose) else "")
called_game, called_new, legacy, called_tool = (folder_with("called_game"), folder_with("called_new", character=False),
                                                folder_with("main"), folder_with("called_tool"))
listed, why = attempt(lambda: [s["name"] for s in saves.list_saves()])
check("the Load page lists a folder whose() calls a game, with no mark on disk", listed is not None and "called_game" in listed, (listed, why))
check("...and the old single save it calls a game already is not marked again", not (legacy / "game.json").exists())
_, why = attempt(lambda: saves.scratch("called_game"))
check("...a tool never clears a folder whose() calls a game", why and (called_game / "campaign.db").is_file(), why)
gone, why = attempt(lambda: saves.discard("called_new"))
check("...and discard() never touches one, though it has no character yet", gone is False and (called_new / "campaign.db").is_file(),
      (gone, why))
taken, why = attempt(lambda: saves.scratch("called_tool", typed=True))
check("a folder whose() calls a tool's, typed on a command line, is taken as the tool's own: cleared and made anew",
      taken == P / "called_tool" and not (called_tool / "campaign.db").exists(), (taken, why))
(called_tool / "campaign.db").write_text("", encoding="utf-8")
(called_tool / "scratch.json").unlink(missing_ok=True)
gone, why = attempt(lambda: saves.drop("called_tool"))
check("...and drop() removes it, with no mark on disk", gone is True and not called_tool.exists(), (gone, why))
if callable(whose):
    saves.whose = whose
check("(nothing here reached the repository's saves/)", not STOPPED, STOPPED[:4])

shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)
