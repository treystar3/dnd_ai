"""(f741) A game's folder says it is the player's game (storage/saves.py MARK), and saves/index.json is only a cache of it.
The index alone said which folders were games, so a game deleted and moved back out of saves/_deleted was never listed again
(the Load page tells the player a deleted game is moved aside, "not erased"), an index that was missing or could not be read
listed no game, and the next new game wrote an index holding only itself. Held here, in a saves folder of its own:
- a game deleted and moved back, under its _deleted name or under its own, is listed again with its character;
- with three games on disk, an index that is empty, gone, cut in half or no index at all lists all three, Continue still opens
  the one played last, and the next new game's index holds all four;
- second cases of the kind (a game folder the index does not name): a folder copied in from another install is listed (the
  owner's answer to GOALS.md's open question, (a) of the plan, approved with phase 1); the games an index from before the marks lists, and the
  old single save, are marked the first time they are read and stay listed when that index is lost; a mark that cannot be read
  still marks;
- and what is no game still never shows: a folder with a database and no mark (a tool's, a test's), even when an index this
  build wrote names it, and a mark with no database.
Run: python tools/sim/saves_marked_741_test.py"""
import itertools
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage import campaign, saves
from storage.campaign import CampaignStore, PlayerState

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

BASE = Path(tempfile.mkdtemp(prefix="saves_marked_"))
MARK = saves.MARK
ticks = itertools.count(1)
def clock():
    t = next(ticks)
    return f"2026-11-{10 + t // 1440:02d}T{t // 60 % 24:02d}:{t % 60:02d}:00"
saves._now = clock                                           # played times that always move on, a minute a game

def folder(name):
    root = BASE / name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    campaign.SAVES_DIR = root                                # nothing here can reach the real saves/
    return root

def store(root, name, char_name=""):
    """A save with a character, as a tool or a test makes one: nothing says it is the player's game."""
    st = CampaignStore.open_or_create(name, saves_dir=root)
    c, _ = simlib.make_character("warrior", random.Random(1))
    c.name = char_name or name
    st.save_player(PlayerState(character=c, location="parth"))
    st.close()

def play(root, name, char_name=""):
    """A game the game itself made: its folder, its character, and touch() as main.py calls it."""
    store(root, name, char_name)
    saves.touch(name, root)

def listed(root):
    return sorted(s["name"] for s in saves.list_saves(root))

# ---- 1. the case that found it: a game deleted and moved back
root = folder("moved_back")
play(root, "game_20261101_101010", "Ada Venn"); play(root, "game_20261102_101010", "Bram Holt")
where = saves.delete("game_20261101_101010", root)
check("deleting still moves the game aside and out of the list, though the mark goes with it",
      where is not None and where.parent.name == saves.DELETED and (where / MARK).is_file() and listed(root) == ["game_20261102_101010"],
      (where, listed(root)))
back = root / where.name
shutil.move(str(where), str(back))
got = {s["name"]: s for s in saves.list_saves(root)}
check("a deleted game moved back under its _deleted name is listed again, under that folder name",
      sorted(got) == sorted(["game_20261102_101010", where.name]), sorted(got))
check("...with its character, ready to play", got.get(where.name, {}).get("character") == "Ada Venn" and got.get(where.name, {}).get("ready"), got.get(where.name))
saves.delete(where.name, root)
again = next((root / saves.DELETED).glob(f"{where.name}_*"), None)
check("...and it can be deleted again from there", again is not None and listed(root) == ["game_20261102_101010"], listed(root))
shutil.move(str(again or back), str(root / "game_20261101_101010"))
check("moved back under its own name, it is listed again",
      listed(root) == ["game_20261101_101010", "game_20261102_101010"], listed(root))

# ---- 2. the case that found it: an index that cannot be read hides nothing
root = folder("index_lost")
for n, who in (("game_20261103_101010", "Cass Wen"), ("game_20261104_101010", "Dov Ark"), ("game_20261105_101010", "Edda Lo")):
    play(root, n, who)
saves.touch("game_20261104_101010", root)                    # the one played last, though not the one made last
good = (root / saves.INDEX).read_text(encoding="utf-8")
three = ["game_20261103_101010", "game_20261104_101010", "game_20261105_101010"]
for how, spoil in (("empty", lambda p: p.write_text("", encoding="utf-8")),
                   ("gone", lambda p: p.unlink()),
                   ("cut in half", lambda p: p.write_text(good[:len(good) // 2], encoding="utf-8")),
                   ("not an index at all", lambda p: p.write_text('["game_20261103_101010"]', encoding="utf-8"))):
    spoil(root / saves.INDEX)
    check(f"with the index {how}, all three games are listed", listed(root) == three, listed(root))
    cont = saves.last(root)
    check(f"...and Continue opens the one played last", cont is not None and cont["name"] == "game_20261104_101010", cont and cont["name"])
(root / saves.INDEX).write_text("", encoding="utf-8")
play(root, "game_20261106_101010", "Fen Moor")
check("after the index is lost, the next new game's index holds every game, not only itself",
      sorted(saves.load_index(root)["saves"]) == three + ["game_20261106_101010"] and saves.load_index(root)["last"] == "game_20261106_101010",
      saves.load_index(root))

# ---- 3. second case: a game folder from another install, which this index never named
root = folder("copied_in")
other = folder("other_install")
play(other, "game_20260901_090909", "Gil Arn")
campaign.SAVES_DIR = root
play(root, "game_20261107_101010", "Hale Dun")
shutil.copytree(other / "game_20260901_090909", root / "game_20260901_090909")
got = {s["name"]: s for s in saves.list_saves(root)}
check("a game folder copied in from another install is listed, with its character",
      got.get("game_20260901_090909", {}).get("character") == "Gil Arn", sorted(got))
check("...and its own played time comes with it, so the game played here is still first",
      saves.list_saves(root)[0]["name"] == "game_20261107_101010" and saves.last(root)["name"] == "game_20261107_101010", listed(root))

# ---- 4. second case: games from before the marks are marked the first time they are read
root = folder("before_marks")
for n in ("main", "game_20261008_101010", "game_20261009_101010"):
    store(root, n, n.title())
old_index = {"last": "game_20261009_101010", "saves": {"game_20261008_101010": {"created": "2026-10-08T10:10:10", "played": "2026-10-08T11:00:00"},
                                                        "game_20261009_101010": {"created": "2026-10-09T10:10:10", "played": "2026-10-09T11:00:00"}}}
(root / saves.INDEX).write_text(json.dumps(old_index), encoding="utf-8")         # an index as a build before the marks wrote it
check("the games an older index lists, and the old single save, are all listed",
      listed(root) == ["game_20261008_101010", "game_20261009_101010", "main"], listed(root))
check("...Continue is still the one that index played last", saves.last(root)["name"] == "game_20261009_101010", saves.last(root))
check("...and each now carries its mark", all((root / n / MARK).is_file() for n in ("main", "game_20261008_101010", "game_20261009_101010")))
(root / saves.INDEX).unlink()
check("so when that index is lost they are all still listed, with their played times",
      listed(root) == ["game_20261008_101010", "game_20261009_101010", "main"]
      and saves.load_index(root)["saves"].get("game_20261009_101010", {}).get("played") == "2026-10-09T11:00:00", saves.load_index(root))

# ---- 5. second case: a mark that cannot be read still says the folder is a game
root = folder("mark_unread")
play(root, "game_20261110_101010", "Ida Fell")
(root / "game_20261110_101010" / MARK).write_text("", encoding="utf-8")
(root / saves.INDEX).unlink()
check("a game whose mark cannot be read is still listed", listed(root) == ["game_20261110_101010"], listed(root))

# ---- 6. what is no game still never shows
root = folder("no_game")
play(root, "game_20261111_101010", "Jory Pell")
store(root, "some_tool_save", "Not Mine")                    # what a tool or a test makes: a database, no mark
check("a folder with a database and no mark is not listed", listed(root) == ["game_20261111_101010"], listed(root))
(root / saves.INDEX).unlink()
check("...nor when the index is lost", listed(root) == ["game_20261111_101010"], listed(root))
ix = json.loads((root / saves.INDEX).read_text(encoding="utf-8")) if (root / saves.INDEX).exists() else {"last": "", "saves": {}}
ix["saves"]["some_tool_save"] = {"created": "2026-11-11T10:00:00", "played": "2026-11-11T10:00:00"}
(root / saves.INDEX).write_text(json.dumps(ix), encoding="utf-8")
check("...nor when an index this build wrote names it: the index says nothing of what is a game",
      listed(root) == ["game_20261111_101010"] and not (root / "some_tool_save" / MARK).exists(), listed(root))
(root / "half_made").mkdir()
(root / "half_made" / MARK).write_text(json.dumps({"created": "2026-11-11T10:00:00"}), encoding="utf-8")
check("a mark with no database is not listed", listed(root) == ["game_20261111_101010"], listed(root))

shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
