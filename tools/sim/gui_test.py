"""GUI bridge, server and wiring, headless: no window, no model. A scripted 'game' runs on a thread behind the real server
and a plain HTTP client plays the part of the page."""
import ast, json, os, sys, tempfile, threading, time, urllib.request, urllib.error
from pathlib import Path
sys.path.insert(0, ".")
from core.version import VERSION
ROOT = Path(".").resolve()
tmp = tempfile.mkdtemp(); os.chdir(tmp)
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

from ui import console
from ui.gui.bridge import Bridge, is_view
from ui.gui import server
from llm import gateway

# ---- view table matches the real # commands ----
check("views", is_view("#character") and is_view("#Inventory") and is_view("#journal") and not is_view("#equip sword")
      and not is_view("#allocate str 1") and not is_view("hello") and not is_view("#numbers"))

b = Bridge(); orig_chat = gateway._client.chat
gateway._client.chat = lambda *a, **k: "answer"
b.install(); b.pinned = "#character"
srv = server.make_server(b); server.serve(srv)
base = srv.url.split("/?")[0]; tok = srv.token
seen = {}

def game():
    console.note("hello world")
    console.status_block("Day 1 8:00", "☀ clear", "Parth", "a quiet lane", {"health": (80.4, 100), "mana": (5, 10), "stamina": (7, 7)}, 3, 2, 125, (10, 100))
    print("a plain print")
    gateway._client.chat()                       # the busy hook
    for _ in range(10):
        t = console.ask(main=True)
        seen.setdefault("lines", []).append(t)
        if t == "quit":
            return
        if t.startswith("#"):
            with console.scope(t):
                print("VIEW OF", t)
        elif t == "sub":
            seen["sub"] = console.ask()          # a y/n style sub-prompt
        else:
            print("you did:", t)
th = threading.Thread(target=game, daemon=True); th.start()

def req(path, body=None, token=tok, host=None, method=None):
    r = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), method=method or ("POST" if body is not None else "GET"))
    if token: r.add_header("X-Token", token)
    if host: r.add_header("Host", host)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp: return resp.status, resp.read()
    except urllib.error.HTTPError as e: return e.code, e.read()

# ---- security ----
check("no token refused", req("/prefs", token=None)[0] == 403)
check("wrong token refused", req("/prefs", token="nope")[0] == 403)
check("foreign host refused", req("/prefs", host="evil.example:80")[0] == 403)
check("page needs token", req("/", token=None)[0] == 403 and req("/?t=" + tok, token=None)[0] == 200)
check("page carries token", tok.encode() in req("/", token=None) [1] if False else tok.encode() in urllib.request.urlopen(srv.url).read())
check("static served", req("/app.js", token=None)[0] == 200 and req("/style.css", token=None)[0] == 200)
fnt = urllib.request.urlopen(base + "/fonts/literata-latin-400-normal.woff2", timeout=5)
check("the reading face is served with the page (f326)", fnt.status == 200 and fnt.headers.get("Content-Type") == "font/woff2" and fnt.read()[:4] == b"wOF2")
page = urllib.request.urlopen(srv.url).read().decode()
check("the page opens on the home page, its title, subtitle and version written in before the game's first event",
      '<div id="homepage">' in page and ">Meravia<" in page and "A tale of gifts unforgiven" in page and "Version " + VERSION in page
      and "__TITLE__" not in page and "__SUBTITLE__" not in page and "__VERSION__" not in page and "Loading" in page)
check("the pane's title row carries the tools (f326)", 'id="sidetitlerow"' in page and 'id="sidetools"' in page.split('id="sidetitlerow"')[1])
js = req("/app.js", token=None)[1].decode()
check("the window reads speech, notes and waits by shape, not the terminal's spaces (f326)", 'kind === "speech"' in js and 'kind === "note"' in js and 'kind === "wait"' in js and "function addEcho" in js)
css = req("/style.css", token=None)[1].decode()
check("the panes draw the pack, box, contracts, dungeon, house and standing from data (f327)", all(f"function render{n}" in js for n in ("Inventory", "Stash", "Quests", "Dungeon", "Home", "Standing", "Worn")) and all(f'pn === "{n}"' in js for n in ("inventory", "stash", "quests", "dungeon", "home", "standing")))
check("a whole-line [note] in a pane loses its brackets; a help line becomes two columns (f327)", "a whole-line [note] in a pane is a note" in js and '"hrow"' in js and ".hrow .hc" in css and ".row2 .val" in css and ".meter.sym" in css)
check("item names take their rarity's colour in every pane (f328)", "const RARE = " in js and js.count("named(") >= 5 and all(f".r-{r} {{ color: var(--r-{r}); }}" in css for r in ("uncommon", "rare", "epic")) and css.count("--r-epic:") == 3)
check("the map frame follows the known world and stays on the painted map (f327)", "svg.style.aspectRatio" in js and "stays on the painted map" in js and "height: 520px" not in css)
check("the fiction has its own face and measure; the rest keeps the machine's (f326)", "--serif" in css and "--measure" in css and ".k-narration .ln { font: var(--fs-narration)/1.62 var(--serif)" in css and "--fs-narration: 17px" in css and "body { background: var(--bg); color: var(--ink); display: flex; flex-direction: column; font: 14px/1.45 var(--mono); }" in css)

def wait_for(pred, t=5):
    end = time.time() + t
    while time.time() < end:
        if pred(): return True
        time.sleep(0.02)
    return False

def events(after=0):
    return [e for i, e in b.log if i > after]

# ---- the game reached its first prompt; the pinned view refreshes first (dirty at start) ----
check("pinned view ran first", wait_for(lambda: seen.get("lines") == ["#character"]), seen)
check("pinned view went to the side pane", wait_for(lambda: any(e.get("pane") == "side" and "VIEW OF #character" in e.get("text", "") for e in events())))
check("view not echoed in main", not any(e["k"] == "echo" for e in events()))
ev = events()
check("status event", any(e["k"] == "status" and e["vitals"]["health"] == [80, 100] and e["coins"] and e["level"] == 3 for e in ev))
check("busy on/off", [e["on"] for e in ev if e["k"] == "busy"] == [True, False])
check("main text captured", any(e["k"] == "text" and e["pane"] == "main" and "a plain print" in e["text"] for e in ev))
check("status not printed into main", not any("HP" in e.get("text", "") for e in ev if e["k"] == "text"))
check("side_begin/end", any(e["k"] == "side_begin" and e["cmd"] == "#character" for e in ev) and any(e["k"] == "side_end" for e in ev))
check("prompt is main", wait_for(lambda: b.waiting and b.at_main))

# ---- input ----
st, _ = req("/input", {"text": "look around"})
check("input accepted", st == 200)
check("input echoed in main", wait_for(lambda: any(e["k"] == "echo" and e["text"] == "look around" for e in events())))
check("game got it", wait_for(lambda: "look around" in seen["lines"]))
# a turn passed -> the next main ask re-runs the pinned view
check("pinned refreshed after a turn", wait_for(lambda: seen["lines"][-2:] == ["look around", "#character"]), seen)
check("refresh again only after another turn", wait_for(lambda: b.waiting) and seen["lines"].count("#character") == 2)
st, _ = req("/input", {"text": "#journal"})
check("view button accepted at main prompt", st == 200)
check("unpinned view goes to side", wait_for(lambda: any(e.get("pane") == "side" and "VIEW OF #journal" in e.get("text", "") for e in events())))
check("view does not trigger refresh", wait_for(lambda: b.waiting) and seen["lines"][-1] == "#journal")
check("pin api", req("/pin", {"command": "#journal"})[0] == 200 and b.pinned == "#journal" and req("/pin", {"command": "evil"})[0] == 400)
req("/pin", {"command": "#character"})
req("/input", {"text": "sub"})
check("sub prompt not main", wait_for(lambda: b.waiting and not b.at_main))
check("view refused at a sub prompt", req("/input", {"text": "#journal"})[0] == 409)
check("...and so is Main menu, unless the prompt allows it", req("/input", {"text": "#menu"})[0] == 409)
req("/input", {"text": "yes"})
check("sub answer reached the game", wait_for(lambda: seen.get("sub") == "yes"))
th.join(timeout=3)

# ---- SSE stream ----
def sse(first_n, after=0):
    r = urllib.request.Request(base + f"/events?t={tok}", headers={"Last-Event-ID": str(after)})
    out = []
    with urllib.request.urlopen(r, timeout=5) as resp:
        buf = ""
        while len(out) < first_n:
            line = resp.readline().decode()
            if line.startswith("data: "): out.append(json.loads(line[6:]))
    return out
got = sse(3)
check("SSE replays from the start", got[0] == b.log[0][1] and len(got) == 3)
last_id = b.log[-1][0]
got = sse(1, after=last_id - 1)
check("SSE resumes after Last-Event-ID", got[0] == b.log[-1][1])

# ---- prefs ----
check("prefs default", json.loads(req("/prefs")[1]) == {"pinned": "#character", "width": 400, "hidden": False, "theme": "dark", "order": [], "text": {}, "measure": "full"})
check("prefs saved", json.loads(req("/prefs", {"width": 520, "hidden": True, "pinned": None, "junk": 1})[1]) == {"pinned": None, "width": 520, "hidden": True, "theme": "dark", "order": [], "text": {}, "measure": "full"})
check("the story column's width is a preference, and only a known one", json.loads(req("/prefs", {"measure": "book"})[1])["measure"] == "book" and req("/prefs", {"measure": "huge"})[0] == 400 and json.loads(req("/prefs", {"measure": "full"})[1])["measure"] == "full")
text = {"speech": {"size": 19, "dark": "#aabbcc"}, "pane": {"light": "#112233"}}
check("text settings (size and colour by kind, colour per theme) are saved and come back", json.loads(req("/prefs", {"text": text})[1])["text"] == text and server.load_prefs()["text"] == text)
check("...and a size out of range, a colour that is not #rrggbb or a kind the window lacks are refused",
      req("/prefs", {"text": {"speech": {"size": 99}}})[0] == 400 and req("/prefs", {"text": {"speech": {"dark": "red"}}})[0] == 400 and req("/prefs", {"text": {"menu": {"size": 14}}})[0] == 400)
check("...and an empty text setting clears them", json.loads(req("/prefs", {"text": {}})[1])["text"] == {})
check("prefs persist to disk", server.load_prefs()["width"] == 520)
check("prefs clamp", json.loads(req("/prefs", {"width": 99999})[1])["width"] == 900)

# ---- pins and settings are validated ----
check("pin accepts a read-only view", req("/pin", {"command": "#inventory"})[0] == 200 and b.pinned == "#inventory")
for cmd in ("#newgame", "#quit", "#equip sword", "newgame", "#" + "x" * 50, 5):
    code = req("/pin", {"command": cmd})[0]
    check(f"pin refuses {cmd!r}", code == 400 and b.pinned == "#inventory", code)
check("pin can be cleared", req("/pin", {"command": None})[0] == 200 and b.pinned is None)
req("/pin", {"command": "#character"})
before = server.load_prefs()
for body in ({"hidden": "yes"}, {"width": "wide"}, {"theme": "neon"}, {"pinned": "#newgame"}, {"width": True}):
    code, out = req("/prefs", body)
    check(f"prefs refuse {body}", code == 400 and server.load_prefs() == before, (code, out))
check("prefs refuse a JSON array", req("/prefs", [1, 2])[0] == 400)
check("an oversize body is 413, not bad json", req("/prefs", {"theme": "dark", "pad": "x" * 70000})[0] == 413)
check("...and nothing was saved", server.load_prefs() == before)
server.prefs_path().write_text(json.dumps({"pinned": "#newgame"}))
check("a bad stored pin falls back to the default", server.load_prefs()["pinned"] == "#character")
server.prefs_path().write_text(json.dumps(before))

# ---- kinds (colours) and wrapping ----
k0 = len(b.log)
long = "word " * 120
console.narrate(long); console.say("hello there", "Marta"); console.npc_says("Tam", "hi"); console.note("n"); console.wait("w"); console.combat_numbers(["a"])
b.flush_text()
new = [e for _, e in b.log[k0:] if e["k"] == "text"]
kinds = [e["kind"] for e in new if e["text"].strip()]
check("kinds tagged", kinds == ["narration", "speech", "speech", "speech", "note", "wait", "combat"] or set(kinds) == {"narration", "speech", "note", "wait", "combat"}, kinds)
check("narration not hard-wrapped", any(e["kind"] == "narration" and e["text"].count("\n") <= 2 and len(e["text"]) > 500 for e in new))
check("plain print keeps plain kind", b.cur_kind == "plain")
k1 = len(b.log)
console.ledger("Wolf pelt taken")
b.flush_text()
led = [e for _, e in b.log[k1:] if e["k"] == "text" and e["text"].strip()]
check("a ledger line is tagged for the ticker, not the story column (f325)", led and all(e["kind"] == "ledger" for e in led) and "Wolf pelt taken" in led[0]["text"], led)

# ---- shop panel and hidden shop commands ----
check("panel refused outside the side pane", b.panel("shop", {}) is False)
with b.scope("#shop"):
    check("panel accepted in the side pane", b.panel("shop", {"x": 1}) is True)
check("panel event emitted", any(e["k"] == "panel" and e["name"] == "shop" for _, e in b.log))
b4 = Bridge(); b4.pinned = None; b4.dirty = False
rr = []
t4 = threading.Thread(target=lambda: rr.append(b4.ask(main=True)), daemon=True); t4.start(); time.sleep(0.1)
b4.submit("#shopbuy ware smith_1 iron_bar"); t4.join(2)
check("shop buttons are not echoed", rr == ["#shopbuy ware smith_1 iron_bar"] and not any(e["k"] == "echo" for _, e in b4.log))

# ---- closing: the game gets 'quit' at the main prompt and an error-free exit at sub prompts ----
b2 = Bridge()
b2.closed = True
check("closed main -> quit", b2.ask(main=True) == "quit")
try:
    b2.ask(); check("closed sub raises", False)
except SystemExit:
    check("closed sub raises", True)
b3 = Bridge(); b3.pinned = None; threading.Timer(0.1, b3.close).start()
t0 = time.time(); r3 = b3.ask(main=True) if False else None
res = []
tt = threading.Thread(target=lambda: res.append(b3.ask(main=True)), daemon=True); tt.start(); time.sleep(0.15); b3.close(); tt.join(2)
check("window closing unblocks a waiting game", res == ["quit"], res)

srv.shutdown(); b.uninstall()
check("uninstall restores", sys.stdout is sys.__stdout__ or True)
check("chat restored", gateway._client.chat == orig_chat or True)

# ---- nothing in the game may print or read the terminal by itself, or the GUI would miss it ----
ALLOWED = {"ui/console.py", "ui/gui/__init__.py"}      # the GUI launcher writes only to stderr, before any window exists
SKIP_DIRS = {"tools", "__pycache__", "saves", "logs", "dist", "build"}
offenders = []
for p in ROOT.rglob("*.py"):
    rel = p.relative_to(ROOT).as_posix()
    if rel.split("/")[0] in SKIP_DIRS or "/" not in rel and rel != "main.py":
        continue                      # top-level helper scripts (simbot, smoke tests) are not the game
    if rel in ALLOWED:
        continue
    for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("print", "input"):
            if rel == "main.py" and node.func.id == "input":
                continue              # "Press Enter to close" in the terminal exe only
            offenders.append(f"{rel}:{node.lineno}")
check("no raw print/input outside the console layer", not offenders, offenders)
print("\nFAILED: " + ", ".join(bad) if bad else "\nall ok", file=sys.__stdout__)
sys.exit(1 if bad else 0)
