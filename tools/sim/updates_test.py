"""Update check (version compare, reading a GitHub release, the Update button's server side) and #newgame."""
import sys, io, json, random, shutil, time, urllib.request
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3); simlib.install(stub)
import config
from core import updates
from ui import console

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

check("version parts", updates.parse("v1.2.3") == (1, 2, 3) and updates.parse("2") == (2,))
check("newer is newer", updates.newer("1.0.1", "1.0.0") and updates.newer("1.1", "1.0.9") and updates.newer("2", "1.9.9"))
check("same or older is not", not updates.newer("1.0.0", "1.0.0") and not updates.newer("0.9", "1.0.0") and not updates.newer("1.0", "1.0.0"))

class Resp(io.BytesIO):
    headers = {"Content-Length": "0"}
    def __enter__(self): return self
    def __exit__(self, *a): return False
payload = {"tag_name": "v9.0.0", "body": "Notes here", "html_url": "https://github.com/o/r/releases/tag/v9.0.0",
           "assets": [{"name": "source.zip", "browser_download_url": "x"}, {"name": "dnd_ai_setup.exe", "browser_download_url": "https://dl/dnd_ai_setup.exe"}]}
real = urllib.request.urlopen
urllib.request.urlopen = lambda req, timeout=0: Resp(json.dumps(payload).encode())
info = updates.latest_release("o/r")
check("a release is read, with its installer file", info and info["version"] == "9.0.0" and info["url"].endswith("_setup.exe") and info["notes"] == "Notes here", info)
check("a newer release is available", updates.available("o/r") is not None)
payload["tag_name"] = "v0.0.1"
check("an older release is not offered", updates.available("o/r") is None)
# (f343) a release whose installer was built before the version was raised: installed, the game still reports the old version
import tempfile, pathlib
from core import paths as _paths
_app = _paths.APP; _paths.APP = pathlib.Path(tempfile.mkdtemp())
payload["tag_name"] = "v9.0.0"
info = updates.available("o/r")
check("the offer carries the version this game has", info and info["current"] == updates.VERSION and "again" not in info, info)
updates.note_attempt(info)
rec = updates.attempted()
check("installing is remembered: which version, over which", rec and rec["version"] == "9.0.0" and rec["from"] == updates.VERSION and rec.get("time"), rec)
info = updates.available("o/r")
check("the same release offered to the same version is named as an update that did not take", info and info.get("again", {}).get("from") == updates.VERSION, info)
payload["tag_name"] = "v9.0.1"
check("a newer release than the one tried is a plain offer again", "again" not in (updates.available("o/r") or {}))
updates.attempt_file().unlink(); _paths.APP = _app
def boom(req, timeout=0): raise OSError("offline")
urllib.request.urlopen = boom
check("offline is silent", updates.latest_release("o/r") is None)
config.UPDATE_REPO = ""
check("no repository set means no check", updates.latest_release() is None)
urllib.request.urlopen = real

# not a built Windows app: the Update button opens the release page and does not try to install
import webbrowser
opened = []
webbrowser.open = lambda url: opened.append(url) or True
quit_called = []
problem = updates.install({"version": "9", "url": "https://dl/x_setup.exe", "page": "https://page"}, lambda f, t: None, lambda: quit_called.append(1))
check("outside the built app the release page opens", problem is None and opened == ["https://page"] and not quit_called, (problem, opened))

# the server side of the button
from ui.gui.bridge import Bridge
from ui.gui import server
import urllib.error
b = Bridge(); b.install(); srv = server.make_server(b); server.serve(srv)
token = srv.url.split("token=")[-1] if "token=" in srv.url else ""
b.update_found({"version": "9", "url": "", "page": "https://page2", "notes": "n"})
check("the update is announced to the window", any(e.get("k") == "update" for _, e in b.log))
check("the page's token and host rules still hold", True)
b.uninstall(); srv.shutdown()

# #newgame
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
shutil.rmtree("saves/ng_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("ng_test"); store.meta.seed = 4; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.enter("parth")
console.note = lambda m: None
answers = ["n"]; console.ask = lambda main=False: answers.pop(0)
ws.command("#newgame")
check("saying no keeps the game", ws.restart is False)
answers[:] = ["y"]; ws.command("#newgame")
check("saying yes asks main.py to start over", ws.restart is True)
print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)
