"""Update check (version compare, reading a GitHub release, the Update button's server side).
(f780) The update switch is asked in one place, updates.enabled() (UPDATE_REPO set and UPDATE_CHECK on), and every path obeys it:
the window's check (ui.gui.launch), the terminal's (main.play), the game's own question, install() itself, and the Update button
(POST /update, over an offer already on the bridge). The game asks only of the repository config names, so the tests name theirs
there. A source rule fences the kind: outside core/updates nothing reads the switch, asks the releases API some other way, or
installs in a function that does not ask enabled()."""
import sys, io, json, urllib.request
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

held_config = {k: getattr(config, k) for k in ("UPDATE_REPO", "UPDATE_CHECK", "BACKEND", "LOG_PATH", "CRASH_LOG_PATH")}
config.UPDATE_REPO, config.UPDATE_CHECK = "o/r", True          # (f780) the one repository the game asks of, the switch on

check("version parts", updates.parse("v1.2.3") == (1, 2, 3) and updates.parse("2") == (2,))
check("newer is newer", updates.newer("1.0.1", "1.0.0") and updates.newer("1.1", "1.0.9") and updates.newer("2", "1.9.9"))
check("same or older is not", not updates.newer("1.0.0", "1.0.0") and not updates.newer("0.9", "1.0.0") and not updates.newer("1.0", "1.0.0"))

class Resp(io.BytesIO):
    headers = {"Content-Length": "0"}
    def __enter__(self): return self
    def __exit__(self, *a): return False
payload = {"tag_name": "v9.0.0", "body": "Notes here", "html_url": "https://github.com/o/r/releases/tag/v9.0.0",
           "assets": [{"name": "source.zip", "browser_download_url": "x"}, {"name": "Meravia_0.0.6_setup.exe", "browser_download_url": "https://dl/Meravia_0.0.6_setup.exe"}]}
real = urllib.request.urlopen
urllib.request.urlopen = lambda req, timeout=0: Resp(json.dumps(payload).encode())
info = updates.latest_release()
check("a release is read, with its installer file", info and info["version"] == "9.0.0" and info["url"].endswith("_setup.exe") and info["notes"] == "Notes here", info)
check("a newer release is available", updates.available() is not None)
payload["tag_name"] = "v0.0.1"
check("an older release is not offered", updates.available() is None)
# (f343) a release whose installer was built before the version was raised: installed, the game still reports the old version
import tempfile, pathlib
from storage import campaign as _campaign
_saves = _campaign.SAVES_DIR; _campaign.SAVES_DIR = pathlib.Path(tempfile.mkdtemp())
payload["tag_name"] = "v9.0.0"
info = updates.available()
check("the offer carries the version this game has", info and info["current"] == updates.VERSION and "again" not in info, info)
updates.note_attempt(info)
rec = updates.attempted()
check("installing is remembered: which version, over which", rec and rec["version"] == "9.0.0" and rec["from"] == updates.VERSION and rec.get("time"), rec)
info = updates.available()
check("the same release offered to the same version is named as an update that did not take", info and info.get("again", {}).get("from") == updates.VERSION, info)
payload["tag_name"] = "v9.0.1"
check("a newer release than the one tried is a plain offer again", "again" not in (updates.available() or {}))
updates.attempt_file().unlink(); _campaign.SAVES_DIR = _saves
def boom(req, timeout=0): raise OSError("offline")
urllib.request.urlopen = boom
check("offline is silent", updates.latest_release() is None)
config.UPDATE_REPO = ""
check("no repository set means no check", updates.latest_release() is None)
config.UPDATE_REPO = "o/r"
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

# ---- (f780) one switch: updates.enabled() is asked in one place, and every path that looks for, offers or installs a release obeys it
import ast, threading, time, types
from pathlib import Path
from engine import data_check
from scenes import home
from ui import gui
import main as game_main

SCRATCH = Path(tempfile.mkdtemp(prefix="updates_780_")).resolve()
config.LOG_PATH, config.CRASH_LOG_PATH = str(SCRATCH / "llm_calls.jsonl"), str(SCRATCH / "crash.log")
payload["tag_name"] = "v9.0.0"
asked: list[str] = []


def recorder(req, timeout=0):
    """urlopen as a recorder: what was asked is written down and a newer release answered; nothing leaves the machine."""
    asked.append(getattr(req, "full_url", str(req)))
    return Resp(json.dumps(payload).encode())


def window_path():
    """ui.gui.launch as the window opens (the window itself a stand-in that waits for the release check): the bridge the page reads."""
    seen = []

    def stand_in(bridge, url, title, game_thread):
        seen.append(bridge)
        game_thread.join(5)
        for t in threading.enumerate():
            if t.name == "update-check":
                t.join(5)
    real_window, gui._window = gui._window, stand_in
    try:
        gui.launch(lambda bridge: None, title="f780")
    finally:
        gui._window = real_window
    return seen[0]


def terminal_path() -> list[str]:
    """main.play as the terminal game starts (a server run by hand, the stub its source) up to the home page, whose Quit ends it: what
    the story was told."""
    told: list[str] = []
    held = {k: console.now(k) for k in ("note", "out")}
    for k in held:
        console.put(k, lambda t="", *a, **kw: told.append(str(t)))
    real_choose, real_check = home.choose, data_check.check
    home.choose, data_check.check = (lambda written: ("quit", "")), (lambda: [])      # the data has its own tests
    config.BACKEND = "llama"
    try:
        game_main.play(types.SimpleNamespace(new=False, debug=False, gui=False, terminal=True))
    finally:
        home.choose, data_check.check = real_choose, real_check
        config.BACKEND = held_config["BACKEND"]
        for k, f in held.items():
            console.put(k, f)
    return told


def offered(bridge) -> bool:
    return any(e.get("k") == "update" for _, e in bridge.log)


urllib.request.urlopen = recorder
try:
    switch = {}
    for label, repo, on in (("off", "o/r", False), ("no repository", "", True), ("on", "o/r", True)):
        config.UPDATE_REPO, config.UPDATE_CHECK = repo, on
        asked.clear()
        enabled = updates.enabled() if hasattr(updates, "enabled") else None
        b = window_path()
        window = (list(asked), offered(b), b.update_info is not None)
        asked.clear()
        told = terminal_path()
        terminal = (list(asked), any("A newer version (9.0.0)" in t for t in told))
        asked.clear()
        bare = (updates.latest_release(), updates.available(), list(asked))
        switch[label] = {"enabled": enabled, "window": window, "terminal": terminal, "bare": bare}
finally:
    urllib.request.urlopen = real
off = switch["off"]
check("(f780) with UPDATE_CHECK off, the window's check asks nothing and no update reaches the page (no event, no offer kept)",
      off["window"] == ([], False, False), off["window"])
check("...and the terminal's check, as main.play runs it, asks nothing and tells nothing", off["terminal"] == ([], False), off["terminal"])
check("...and the game's own question answers None unasked; enabled() says it is off",
      off["bare"] == (None, None, []) and off["enabled"] is False, (off["bare"], off["enabled"]))
gone = switch["no repository"]
check("...the same with no repository named and the switch on (the switch's other half)", gone["window"] == ([], False, False)
      and gone["terminal"] == ([], False) and gone["bare"] == (None, None, []) and gone["enabled"] is False, gone)
on = switch["on"]
LATEST = "https://api.github.com/repos/o/r/releases/latest"
check("...and with it on, both paths ask the release page and offer the update", on["enabled"] is True
      and on["window"] == ([LATEST], True, True) and on["terminal"] == ([LATEST], True), on)

# install() itself: refused while the switch is off, whoever calls it
config.UPDATE_REPO, config.UPDATE_CHECK = "o/r", False
opened.clear(); quit_called.clear()
problem = updates.install({"version": "9", "url": "https://dl/x_setup.exe", "page": "https://page"}, lambda f, t: None, lambda: quit_called.append(1))
check("(f780) with the switch off, install() itself refuses: a plain line back, no page opened, the game not told to quit",
      isinstance(problem, str) and problem and not any(c in problem for c in "-\u2013\u2014") and not opened and not quit_called,
      (problem, opened, quit_called))

# the Update button: an offer already on the bridge (without one the route answers 409 whatever the switch says)
installs = []
real_install = updates.install
updates.install = lambda info, progress, quit_game: installs.append(info) or None
b = Bridge(); srv = server.make_server(b); server.serve(srv)


def press_update() -> int:
    req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/update", data=b"{}", method="POST",
                                 headers={"X-Token": srv.token, "Content-Type": "application/json"})
    try:
        with real(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def pressed() -> tuple[int, list]:
    """POST /update once: its answer and the installs that press started (waited for a moment, as the route starts one off its thread)."""
    before = len(installs)
    code = press_update()
    for _ in range(100):
        if len(installs) > before:
            break
        time.sleep(0.02)
    return code, installs[before:]


try:
    b.update_info = {"version": "9.0.0", "url": "https://dl/x_setup.exe", "page": "https://page", "notes": "n"}
    config.UPDATE_REPO, config.UPDATE_CHECK = "o/r", False
    code_off, started_off = pressed()
    progress_off = any(e.get("k") == "update_progress" for _, e in b.log)
    config.UPDATE_CHECK = True
    code_on, started_on = pressed()
finally:
    updates.install = real_install
    srv.shutdown()
check("(f780) with the switch off, POST /update answers 409 over an offer already on the bridge, and starts nothing",
      code_off == 409 and started_off == [] and not progress_off, (code_off, started_off, progress_off))
check("...and with it on, that press installs the offer, once", code_on == 200 and [i["version"] for i in started_on] == ["9.0.0"],
      (code_on, started_on))

# the fence: the switch is read in core/updates alone, and no path around it is written elsewhere
SWITCHES = {"UPDATE_REPO", "UPDATE_CHECK"}


def dotted(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = dotted(node.value)
        return None if head is None else f"{head}.{node.attr}"
    return None


def own_nodes(scope):
    """Every node of a function (or a module) but those of the functions, lambdas and classes inside it."""
    todo = list(ast.iter_child_nodes(scope))
    while todo:
        n = todo.pop()
        yield n
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            todo.extend(ast.iter_child_nodes(n))


def strays(text) -> list[tuple[int, str]]:
    """Each place in a module (not core/updates) that goes around the one switch, with its form: the switch read here, the releases API
    asked some other way, or an install in no function that asks enabled() (the function itself, one it is nested in, or the module)."""
    tree = text if isinstance(text, ast.AST) else ast.parse(text)
    cfg, mod, fns = set(), set(), {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "config":
                    cfg.add(a.asname or "config")
                elif a.name == "core.updates":
                    mod.add(a.asname or "core.updates")
        elif isinstance(n, ast.ImportFrom) and n.module == "core" and not n.level:
            mod |= {a.asname or a.name for a in n.names if a.name == "updates"}
        elif isinstance(n, ast.ImportFrom) and n.module == "core.updates" and not n.level:
            fns.update({a.asname or a.name: a.name for a in n.names})

    def target(call) -> str | None:
        if isinstance(call.func, ast.Name):
            return fns.get(call.func.id)
        if isinstance(call.func, ast.Attribute) and dotted(call.func.value) in mod:
            return call.func.attr
        return None
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load) and n.attr in SWITCHES and dotted(n.value) in cfg:
            out.append((n.lineno, "reads the switch"))
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("getattr", "hasattr") and len(n.args) >= 2
              and dotted(n.args[0]) in cfg and isinstance(n.args[1], ast.Constant) and n.args[1].value in SWITCHES):
            out.append((n.lineno, "reads the switch"))
        elif isinstance(n, ast.ImportFrom) and n.module == "config" and any(a.name in SWITCHES | {"*"} for a in n.names):
            out.append((n.lineno, "reads the switch"))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and "api.github.com" in n.value:
            out.append((n.lineno, "asks the releases some other way"))

    def walk(scope, asking: bool) -> None:
        asking = asking or any(isinstance(x, ast.Call) and target(x) == "enabled" for x in own_nodes(scope))
        for x in own_nodes(scope):
            if isinstance(x, ast.Call) and target(x) == "install" and not asking:
                out.append((x.lineno, "installs without asking"))
            if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                walk(x, asking)
    walk(tree, False)
    return out


MAIN_AS_IT_WAS = ("import config\nfrom core import updates\n"                                  # main.py's own gate before f780
                  "info = updates.available(timeout=3.0) if config.UPDATE_REPO and getattr(config, \"UPDATE_CHECK\", True) else None\n")
ROUTE_AS_IT_WAS = ("from core import updates\ndef do_POST(bridge):\n    info = bridge.update_info\n    if not info:\n        return 409\n"
                   "    def work():\n        updates.install(info, None, bridge.close)\n    work()\n")          # the /update route before f780
planted = {
    MAIN_AS_IT_WAS: True,
    ROUTE_AS_IT_WAS: True,
    "import config as c\nif c.UPDATE_CHECK:\n    pass\n": True,
    "from config import UPDATE_REPO\n": True,
    "import config\nok = hasattr(config, 'UPDATE_CHECK')\n": True,
    "import config\nfrom core import updates\ninfo = updates.available(config.UPDATE_REPO)\n": True,
    "import urllib.request\nR = 'o/r'\nurllib.request.urlopen(f'https://api.github.com/repos/{R}/releases/latest')\n": True,
    "from core.updates import install\ndef route(info):\n    def work():\n        install(info, None, None)\n    work()\n": True,
    "from core import updates\ndef check():\n    return updates.enabled()\ndef route(info):\n    updates.install(info, None, None)\n": True,
    "import config\nfrom core import updates\ninfo = updates.available(timeout=3.0)\nupdates.check_in_background(print)\nconfig.UPDATE_CHECK = False\n": False,
    "from core import updates\ndef route(info):\n    if not updates.enabled():\n        return 409\n    def work():\n"
    "        updates.install(info, None, None)\n    work()\n": False,
    "from llm import embed\nembed.available()\nclass B:\n    def install(self):\n        pass\nB().install()\ncfg = {}\ncfg.get('UPDATE_REPO')\n": False,
}
caught = {src: bool(strays(src)) == want for src, want in planted.items()}
check("(f780) the fence catches each way around the switch, planted (the switch read outside core/updates, by any name or import;"
      " the releases API asked some other way; an install in no function that asks enabled()), and passes the game's own question,"
      " an install under the ask, the switch set, and names that are not the updates'", all(caught.values()), [s for s, ok in caught.items() if not ok])
check("...and finds the finding's own: main.py's gate of its own, and the Update button's route that never asked",
      [w for _, w in strays(MAIN_AS_IT_WAS)] == ["reads the switch", "reads the switch"]
      and [w for _, w in strays(ROUTE_AS_IT_WAS)] == ["installs without asking"], (strays(MAIN_AS_IT_WAS), strays(ROUTE_AS_IT_WAS)))
from game_files import game_files                                   # (f788) the game's own code and, by name, the tools beside it
files = [p.as_posix() for p in game_files(with_tools=True) if p.as_posix() != "core/updates.py"]
around = [f"{f}:{line} ({how})" for f in files for line, how in strays(Path(f).read_text(encoding="utf-8"))]
check("in every .py git lists outside docs/, .claude/, data/, tools/sim/ and core/updates.py, nothing goes around the switch",
      not around and len(files) > 200 and "main.py" in files and "ui/gui/server.py" in files, around)

for k, v in held_config.items():
    setattr(config, k, v)
import shutil
shutil.rmtree(SCRATCH, ignore_errors=True)

print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)
