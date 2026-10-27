"""(f345) Saves and the home page. Every game is a folder of its own, listed in saves/index.json with when it was last played; the
old single save and New game's old backups are adopted; Continue opens the game played last; New game makes a new folder and leaves
every other game alone; Delete moves a game aside, not away. The home page's choices mean the same typed in the terminal or sent by
the window, and the main menu and New game in the game leave the save as it was."""
import json, random, shutil, sqlite3, sys, tempfile, time, types
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage import saves, migrations
from storage.campaign import CampaignStore, PlayerState
from scenes import home
from ui import console
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
root = Path(tempfile.mkdtemp())
saves.SAVES_DIR = root

def make(name, char_name, level=3, location="parth", minutes=1440 * 40, player=True):
    st = CampaignStore.open_or_create(name, saves_dir=root)
    st.meta.seed = 1; st.meta.minutes = minutes; st.save_meta()
    if player:
        c, _ = simlib.make_character("warrior", random.Random(1))
        c.name, c.level = char_name, level
        st.save_player(PlayerState(character=c, location=location))
    st.close()

# ---- 1. the old saves are adopted; Continue is the one played last
make("main", "Horseguy55", 4)
time.sleep(1.1)
make("main_backup_20261020_101010", "Old Wren", 12, "trading_square")
make("some_tool_save", "Not Mine")                                   # what tools and tests make is never listed
listed = saves.list_saves()
check("the old single save and New game's old backup are listed; a tool's save is not",
      {s["name"] for s in listed} == {"main", "main_backup_20261020_101010"}, [s["name"] for s in listed])
check("...each with its character, class and level read from inside", any(s["character"] == "Horseguy55" and s["level"] == 4 and s["ready"] for s in listed), listed)
check("the old single save is what Continue opens until something else is played", saves.last()["name"] == "main")
saves.touch("main_backup_20261020_101010")
check("playing a game makes it the one Continue opens, and first in the list",
      saves.last()["name"] == "main_backup_20261020_101010" and saves.list_saves()[0]["name"] == "main_backup_20261020_101010")

# ---- 2. a new game is a folder of its own
name = saves.new_name()
check("a new game gets a fresh folder name that is not taken", name.startswith("game_") and not (root / name).exists(), name)
make(name, "Ada Venn", 1, minutes=0); saves.touch(name)
check("...and is listed beside the others, the others untouched", len(saves.list_saves()) == 3 and (root / "main" / "campaign.db").exists())

# ---- 3. what cannot be played says why
make("game_unfinished", "", player=False); saves.touch("game_unfinished")
s = next(x for x in saves.list_saves() if x["name"] == "game_unfinished")
check("a game whose creation was not finished is listed, not ready, with the reason", not s["ready"] and "not finished" in s["why"], s)
check("...and Continue skips it", saves.last()["name"] != "game_unfinished")
make("game_future", "Tomorrow"); saves.touch("game_future")
db = sqlite3.connect(root / "game_future" / "campaign.db"); db.execute(f"PRAGMA user_version = {migrations.CURRENT + 1}"); db.commit(); db.close()
s = next(x for x in saves.list_saves() if x["name"] == "game_future")
check("a save from a newer build is listed as needing an update", not s["ready"] and "newer version" in s["why"], s)

# ---- 4. delete moves a game aside, and Continue moves on
where = saves.delete("game_future")
check("deleting moves the folder into the deleted folder, not away", where is not None and where.exists() and where.parent.name == saves.DELETED and not (root / "game_future").exists(), where)
check("...and it leaves the list", all(x["name"] != "game_future" for x in saves.list_saves()))
saves.touch("main")
saves.delete("main")
check("deleting the game Continue would open lets Continue pick the next one played", saves.last() and saves.last()["name"] != "main", saves.last())
check("a folder that disappears is dropped from the index", (shutil.rmtree(root / "game_unfinished"), saves.summary("game_unfinished"))[1] is None
      and "game_unfinished" not in saves.load_index()["saves"] or all(x["name"] != "game_unfinished" for x in saves.list_saves()))

# ---- 5. the home page: what it shows, and what each choice means, typed or clicked
data = home.page(world)
check("the page names the game, its version, the game to continue and every save", data["title"] and data["version"] and data["continue"] and len(data["saves"]) >= 2, data)
c = data["continue"]
check("the continue card says who, where and when", c["line"].startswith(c["character"]) and c["where"] and c["when"].startswith("day "), c)
other = next(x for x in data["saves"] if x["name"] != c["name"])
for typed, want in (("", ("load", c["name"])), ("home:continue", ("load", c["name"])), ("n", ("new", "")), ("home:new", ("new", "")),
                    ("q", ("ask_quit", "")), ("home:quit", ("quit", "")), ("l", ("list", "")), ("2", ("load", data["saves"][1]["name"])),
                    (f"home:load:{other['name']}", ("load", other["name"])), ("d2", ("ask_delete", data["saves"][1]["name"])),
                    (f"home:delete:{other['name']}", ("delete", other["name"])), ("home:load:no_such_game", ("bad", "")), ("dance", ("bad", "")), ("9", ("bad", ""))):
    got = home.parse(typed, data)
    check(f"'{typed}' means {want[0]}", got == want, got)

check("in Load's list, Enter goes back to the menu instead of continuing", home.parse("", data, "list") == ("menu", "")
      and home.parse("2", data, "list") == ("load", data["saves"][1]["name"]) and home.parse("n", data, "list") == ("bad", ""))
empty = {"saves": [], "continue": None}
check("with nothing to continue, Enter begins a new game, and with nothing saved there is nothing to load",
      home.parse("", empty) == ("new", "") and home.parse("c", empty) == ("bad", "") and home.parse("l", empty) == ("bad", ""))

# choose(): a delete asked in the terminal, refused, then accepted, then a load
answers = ["l", "d1", "n", "d1", "y", "1"]
notes, menus = [], []
real_ask, real_note, real_out = console.ask, console.note, console.out
console.ask = lambda main=False: answers.pop(0)
console.note = lambda m, *a, **k: notes.append(str(m))
console.out = lambda t="": menus.append(str(t))
first = home.page(world)["saves"][0]["name"]
kind, name_ = home.choose(world)
console.ask, console.note, console.out = real_ask, real_note, real_out
check("in the terminal, a delete is asked first and 'n' keeps the game", any("Delete" in n for n in notes) and not answers, notes)
check("...'y' moves it aside, and the page comes back", not (root / first).exists() and any("Deleted" in n for n in notes), notes)
check("...and a number loads a game", kind == "load" and name_ != first, (kind, name_))
check("the terminal menu offers continue, load, new and quit, and Load lists the games to load or delete",
      any("Continue as" in m for m in menus) and any("[l] Load" in m for m in menus) and any("[n] New game" in m for m in menus)
      and any("[q] Quit" in m for m in menus) and any("d and a number" in m for m in menus), menus[:8])
shown = []
console.out = lambda t="": shown.append(str(t))
home._terminal_menu(data)
lines = [m for m in shown if "[n]" in m or "[l]" in m]
check("New game comes before Load", [("[n]" in m) for m in lines] == [True, False], lines)
shown.clear()
home._terminal_menu({"title": "t", "subtitle": "", "continue": None, "saves": []})
check("with nothing saved there is no Load at all, and Enter is New game", not any("Load" in m for m in shown) and any("[Enter] New game" in m for m in shown), shown)
console.out = real_out
answers = ["q", "n", "q", "y"]
notes.clear()
console.ask = lambda main=False: answers.pop(0)
console.note = lambda m, *a, **k: notes.append(str(m))
console.out = lambda t="": None
got = home.choose(world)
console.ask, console.note, console.out = real_ask, real_note, real_out
check("Quit is asked first: 'n' stays, 'y' quits", got == ("quit", "") and not answers and sum("Quit the game?" in n for n in notes) == 2, (got, notes))

# ---- 6. the window draws the page itself and never echoes the choice
from ui.gui.bridge import Bridge, HIDDEN
b = Bridge(); b.install()
drawn = console.home(home.page(world))
console.home_done()
evs = [e for _, e in b.log]
b.uninstall()
check("the window draws the home page (and the terminal menu is not printed)", drawn is True and any(e.get("k") == "home" for e in evs))
check("opening a game hides it and has the pinned view run again", any(e.get("k") == "home_end" for e in evs) and b.dirty)
check("a home page choice is never echoed into the story", "home:".startswith(HIDDEN) or any("home:load:x".startswith(h) for h in HIDDEN))
check("the terminal's hooks are back once the window closes", console.home(home.page(world)) is False)

# ---- 7. in the game: the main menu and New game leave the save as it is
from scenes.world import WorldScene
from npc.traits import load_traits
make("game_play", "Mira Holt", 5); saves.touch("game_play")
st = CampaignStore.open_or_create("game_play", saves_dir=root)
ws = WorldScene(st, world, load_traits(), st.load_player()); ws.enter("parth")
said = []
console.note = lambda m, *a, **k: said.append(str(m))
ws.command("#menu")
check("#menu saves and asks main.py for the home page", ws.to_menu)
ws.to_menu = False
ws.combat = types.SimpleNamespace(show=lambda: None)
ws.command("#menu")
check("...but not in the middle of a fight", not ws.to_menu and any("fight" in s for s in said), said[-1:])
ws.combat = None
ws.command("#newgame")
console.ask, console.note = real_ask, real_note
check("New game is on the main menu only: in the game #newgame is no command", not ws.to_menu and "Unknown command" in said[-1], said[-1:])
st.close()
check("...and the game's folder is still there for the main menu", (root / "game_play" / "campaign.db").exists() and any(x["name"] == "game_play" for x in saves.list_saves()))

shutil.rmtree(root, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
