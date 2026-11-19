"""(f742) A game left during creation leaves no dead row, and discard never erases a game that has a character.
New Game made the game's folder and put it in the list (saves.touch, which since f741 also marks the folder the player's game)
before the Threshold, and only Main menu took it back: quitting at the Threshold, closing the window, Ctrl+C, a model failure or a
fault left the folder, its row, Continue pointed at it and the session open, so Load listed one more game that could not be opened.
And discard() erased whatever summary() did not call ready, which is also a save it cannot read and one from a newer build, so a
game with a character could go with rmtree. Held here, through main.play itself, in a saves folder of its own:
- the cases that found it: quitting at the Threshold and closing the window leave no folder, no row, Continue not pointed at it,
  and the session closed;
- second cases of the kind (every way out of creation): Ctrl+C, a model failure (the could-not-wake page's Quit from inside a call,
  and a model error out of creation), a fault; Main menu still discards; a cleanup that fails (the index held) is written down and
  the way out carries on; a game whose character was saved is kept and listed on every way out, and from the moment it is saved;
- the case that found the second: discard() of a played save from a newer build, or with its file cut short, erases nothing: a
  marked game stays where it is, an unmarked one is moved aside as delete() moves it; and the second case, a save whose character's
  row is there but does not read, the same; a marked folder is never erased; a folder with no database, and a new game left with no
  character, are still discarded.
Run: python tools/sim/creation_left_742_test.py"""
import random
import shutil
import sqlite3
import sys
import tempfile
import types
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
from engine import crashlog, data_check
from engine.session import CampaignSession
from llm.errors import LLMError
from scenes import home
from storage import campaign as campaign_store
from storage import migrations, playerstable, saves
from storage.campaign import CampaignStore, PlayerState
from ui import console
from ui.gui.bridge import Closed

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

BASE = Path(tempfile.mkdtemp(prefix="creation_left_"))
config.LOG_PATH = str(BASE / "llm_calls.jsonl")              # what the game writes down stays here, never in the tree
config.CRASH_LOG_PATH = str(BASE / "crash.log")
config.BACKEND = "llama"                                     # main.play's start for a server run by hand: the stub is the one source
config.UPDATE_CHECK = False
data_check.check = lambda: []                                # the data has its own tests; ten seconds a start here
import main as game_main

said: list[str] = []
real = {k: console.now(k) for k in ("ask", "out", "note", "narrate", "say", "status_block")}
for k in ("out", "note", "narrate", "say", "status_block"):
    console.put(k, lambda *a, **kw: said.append(str(a[0]) if a else ""))
real_choose, real_new_name, real_open, real_scene = home.choose, saves.new_name, CampaignSession.open, CampaignSession.scene
real_threshold = game_main.ThresholdScene
opened: list = []
named: list[str] = []
CampaignSession.open = staticmethod(lambda name, saves_dir=None: opened.append(real_open(name, saves_dir)) or opened[-1])
saves.new_name = lambda saves_dir=None: named.append(real_new_name(saves_dir)) or named[-1]


def folder(case: str) -> Path:
    root = BASE / case
    root.mkdir(parents=True)
    saves.SAVES_DIR = root                                   # nothing here can reach the real saves/
    campaign_store.SAVES_DIR = root
    return root


def asks(*answers, then="quit"):
    """The player's lines in order; each may be an exception, raised where the game waits for a line."""
    left = list(answers)
    def ask(main=False, menu=False):
        got = left.pop(0) if left else then
        if isinstance(got, BaseException):
            raise got
        return got
    return ask


def play(ask, threshold=None):
    """main.play as the game runs it: New game on the home page, then its Quit. Returns how play() ended, the game's folder name,
    and whether every session it opened was closed by the time it ended."""
    choices = [("new", ""), ("quit", "")]
    home.choose = lambda world: choices.pop(0) if choices else ("quit", "")
    console.put("ask", ask)
    game_main.ThresholdScene = threshold or real_threshold
    n, m = len(opened), len(named)
    try:
        game_main.play(types.SimpleNamespace(new=False, debug=False, gui=False, terminal=True))
        how = "returned"
    except BaseException as e:                               # what reaches guarded(): the process ends there or after it
        how = type(e).__name__
    finally:
        game_main.ThresholdScene = real_threshold
        home.choose = real_choose
    mine = opened[n:]
    closed = bool(mine) and all(s.closed for s in mine)
    for s in mine:
        s.close()                                            # what the process's end would let go, so the folder can be read
    return how, (named[m:] or [""])[0], closed


def nothing_left(root: Path, name: str) -> dict:
    index = saves.load_index(root)
    return {"folder": (root / name).exists(), "row": name in index["saves"], "last": index["last"] == name,
            "listed": any(s["name"] == name for s in saves.list_saves(root))}


NONE = {"folder": False, "row": False, "last": False, "listed": False}

# ---- 1. the cases that found it: quit typed at the Threshold, and the window closed
for label, ask, raised in (("quit typed at the Threshold", asks("quit"), "SystemExit"),
                           ("the window closed at the Threshold", asks(Closed()), "Closed")):
    root = folder(label.split()[0] + "_" + label.split()[2])
    how, name, closed = play(ask)
    left = nothing_left(root, name)
    check(f"{label}: play() ends as it did ({raised}), and the game begun leaves no folder, no row, and Continue not pointed at it",
          how == raised and name and left == NONE, (how, name, left))
    check(f"...and its session was closed on the way out", closed, closed)
check("...and the player was told no character was saved, which is now so", any("No character was saved" in s for s in said), said[-3:])

# ---- 2. second cases of the kind: every other way out of creation
calls = []
def could_not_wake(**k):
    calls.append(k)
    raise SystemExit(0)                                      # llm/launch.py Screen.recover: the page's Quit, from inside creation's call


for label, ask, raised, below in (("Ctrl+C", asks("", KeyboardInterrupt()), "KeyboardInterrupt", None),
                                  ("a model failure: the could-not-wake page's Quit", asks("", "Ada Venn", then=AssertionError("asked again")),
                                   "SystemExit", could_not_wake),
                                  ("a model failure out of creation", asks("", LLMError("no usable answer")), "LLMError", None),
                                  ("a fault in creation", asks("", RuntimeError("a fault")), "RuntimeError", None)):
    root = folder(label.split(":")[0].replace(" ", "_").replace("+", ""))
    held = simlib.stand_in(chat=below, name="could_not_wake") if below else None
    try:
        how, name, closed = play(ask)
    finally:
        if held is not None:
            held()
    left = nothing_left(root, name)
    check(f"{label}: no folder, no row, the session closed", how == raised and name and left == NONE and closed, (how, name, left, closed))
check("...the could-not-wake page's Quit came from inside creation's call to the model", len(calls) == 1, len(calls))

root = folder("main_menu")
how, name, closed = play(asks("#menu"))
check("Main menu during creation still discards the game begun, and play goes back to the home page",
      how == "returned" and name and nothing_left(root, name) == NONE and closed, (how, name, nothing_left(root, name), closed))


def held_index(name, saves_dir=None):
    raise PermissionError("index.json is held")               # _write_index's replace on Windows, while another reader holds it


real_discard = saves.discard
for label, ask, raised in (("quit typed at the Threshold", asks("quit"), "SystemExit"), ("Main menu", asks("#menu"), "returned")):
    root = folder("cleanup_fails_" + label.split()[0].lower())
    n = len(crashlog.SESSION)
    saves.discard = held_index
    try:
        how, name, closed = play(ask)
    finally:
        saves.discard = real_discard
    logged = [e for e in crashlog.SESSION[n:] if e["where"] == "leaving character creation" and "PermissionError" in e["error"]]
    check(f"a cleanup that fails after {label} is written down, and the way out carries on in its place ({raised})",
          how == raised and closed and len(logged) == 1, (how, closed, crashlog.SESSION[n:]))


class Made:
    """Creation that finishes: the character it hands back, as ThresholdScene.run hands one back."""
    def __init__(self, session=None):
        pass

    def run(self):
        c, _ = simlib.make_character("warrior", random.Random(5))
        c.name = "Wren Ash"
        return c


def kept(root: Path, name: str):
    s = next((s for s in saves.list_saves(root) if s["name"] == name), None)
    return bool(s and s["ready"] and s["character"] == "Wren Ash" and (root / name / saves.MARK).is_file()
                and saves.load_index(root)["last"] == name), s


for label, ask, raised in (("quit typed in the world", asks("quit"), "returned"), ("the window closed in the world", asks(Closed()), "Closed"),
                           ("Ctrl+C in the world", asks(KeyboardInterrupt()), "KeyboardInterrupt")):
    root = folder(label.replace(" ", "_").replace("+", ""))
    how, name, closed = play(ask, Made)
    ok, s = kept(root, name)
    check(f"a game whose character was saved is kept and listed, with its character, after {label}", how == raised and ok and closed,
          (how, s, closed))


def faulty_scene(self, catalog, player):
    raise RuntimeError("a fault before the first line")


root = folder("fault_after_save")
CampaignSession.scene = faulty_scene
try:
    how, name, closed = play(asks("quit"), Made)
finally:
    CampaignSession.scene = real_scene
ok, s = kept(root, name)
check("...and from the moment it is saved: a fault before its first line leaves it listed", how == "RuntimeError" and ok, (how, s))

# ---- 3. discard() erases only a game with no character
root = folder("discard")


def played(name: str, mark: bool = True) -> Path:
    st = CampaignStore.open_or_create(name, saves_dir=root)
    c, _ = simlib.make_character("warrior", random.Random(1))
    c.name = "Ada Venn"
    st.save_player(PlayerState(character=c, location="parth"))
    st.close()
    if mark:
        saves.touch(name, root)
    return root / name / "campaign.db"


def newer(db: Path) -> None:
    con = sqlite3.connect(db)
    con.execute(f"PRAGMA user_version = {migrations.CURRENT + 1}")
    con.commit()
    con.close()


def cut(db: Path) -> None:
    whole = db.read_bytes()
    for extra in ("campaign.db-wal", "campaign.db-shm"):
        (db.parent / extra).unlink(missing_ok=True)
    db.write_bytes(whole[:4096])                             # a save cut short: a disk fault, a copy broken off


def damaged(db: Path) -> None:
    con = sqlite3.connect(db)                                # the character's row there, but not readable
    con.execute("UPDATE kv SET json = '{cut' WHERE key = 'player'")
    if con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (playerstable.TABLE,)).fetchone():
        con.execute(f'UPDATE "{playerstable.TABLE}" SET json = ?', ("{cut",))
    con.commit()
    con.close()


def aside(name: str) -> list[Path]:
    return [p for p in (root / saves.DELETED).glob(f"{name}_*") if (p / "campaign.db").is_file()] if (root / saves.DELETED).is_dir() else []


for how, spoil in (("from a newer build", newer), ("with its file cut short", cut), ("with its character's row damaged", damaged)):
    tag = how.split()[-1]
    marked = f"game_marked_{tag}"
    spoil(played(marked))
    went = saves.discard(marked, root)
    check(f"discard() of a played game {how} erases nothing: it says so, and the game stays where it is, still listed",
          went is False and (root / marked / "campaign.db").is_file() and any(s["name"] == marked for s in saves.list_saves(root)),
          (went, (root / marked).exists(), saves.summary(marked, root)))
    loose = f"game_unmarked_{tag}"
    spoil(played(loose, mark=False))
    went = saves.discard(loose, root)
    check(f"...and one with no mark is moved aside as delete() moves it, its database whole, never erased",
          went is False and not (root / loose).exists() and len(aside(loose)) == 1, (went, (root / loose).exists(), aside(loose)))

played("game_unmarked_whole", mark=False)
check("a game with a character that reads is left where it is", saves.discard("game_unmarked_whole", root) is False
      and (root / "game_unmarked_whole" / "campaign.db").is_file() and not aside("game_unmarked_whole"))
st = CampaignStore.open_or_create("game_marked_empty", saves_dir=root)
st.close()
saves.touch("game_marked_empty", root)                        # a game's folder whose character the save does not hold
check("a folder marked as the player's game is never erased, character or not",
      saves.discard("game_marked_empty", root) is False and (root / "game_marked_empty" / "campaign.db").is_file())
(root / "half_made").mkdir()
(root / "half_made" / "notes.txt").write_text("x", encoding="utf-8")
check("a folder with no database is still discarded", saves.discard("half_made", root) is True and not (root / "half_made").exists())
fresh = saves.new_name(root)
CampaignStore.open_or_create(fresh, saves_dir=root).close()
check("a new game left with no character is still discarded, folder and row", saves.discard(fresh, root) is True
      and not (root / fresh).exists() and fresh not in saves.load_index(root)["saves"] and not aside(fresh))

for k, v in real.items():
    console.put(k, v)
CampaignSession.open, saves.new_name = real_open, real_new_name
shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
