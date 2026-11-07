"""(f539) The model's load shows in the window. While Continue waits for the model, the page shows a card with the loading line and a bar
that only rises (llm/launch.py Screen, through console.setup_progress), from 0 at once; the card goes at ready, or as soon as the game
next speaks, asks or opens a page. The could-not-wake page is told in the story, so nothing may cover it: Continue takes the home page
away before it waits (main.py), and a call that finds the load failed during creation takes the creation page away first (the Screen's
uncover). Before, the page stood under the home page or the creation page with every button there disabled, and the player was stuck.
The bridge hands a page the events after the last it read by id: a replaced progress event leaves a gap in the ids, and by position the
page was handed nothing more (the bar stopped, and the lines and the prompt after it were lost). The real Screen with a scripted load,
the real page in a headless browser behind the real server; skipped where no browser is installed; the source checks run everywhere."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, threading
sys.path.insert(0, os.path.abspath("."))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

ROOT = os.path.abspath(".")
js = pathlib.Path("ui/gui/web/app.js").read_text(encoding="utf-8")
fn = js[js.index("function setupProgress("):][:700]
check("the card shows while the load rises and goes at ready", '$("setup").hidden = false' in fn and "frac >= 1" in fn, fn)
ends = js[js.index("const ENDS_LOAD"):][:200] if "const ENDS_LOAD" in js else ""
check("...and goes as soon as the game next speaks, asks or opens a page", all(f'"{k}"' in ends for k in ("text", "prompt", "home", "creation",
      "fatal", "ended")), ends)
main_src = pathlib.Path("main.py").read_text(encoding="utf-8")
loop = main_src[main_src.index('if kind == "new":'):main_src.index("CampaignSession.open(name)")]
check("Continue takes the home page away before it waits for the load", "console.home_done()" in loop and "screen.wait()" in loop
      and loop.index("console.home_done()") < loop.index("screen.wait()"), loop)
check("...and the Screen is given creation's page to take away", "uncover=lambda: console.creation_done()" in main_src)
at_edge = main_src[main_src.index("saves.touch(name)"):main_src.index("store, world = session.store")]
check("what the load says is said after the home page has gone (its going clears the story)", "screen.flush()" in at_edge
      and at_edge.index("console.home_done()") < at_edge.index("screen.flush()") and main_src.count("screen.flush()") == 2, at_edge)
# the bridge serves a page the events after the last it read, by id: a replaced progress event leaves a gap in the ids
from ui.gui.bridge import Bridge as _B
_b = _B()
_b.emit(k="text", text="a"); _b.setup_progress(0.3, "x")
seen = [i for i, _ in _b.since(-1, timeout=0)]
_b.setup_progress(0.6, "x"); _b.emit(k="text", text="b"); _b.emit(k="prompt")
after = _b.since(seen[-1], timeout=0)
check("a page that read a progress figure is handed the next one and all after it, though the first was replaced in the log",
      [e.get("frac") or e.get("k") for _, e in after] == [0.6, "text", "prompt"] and all(i > seen[-1] for i, _ in after), (seen, after))
check("...and a page that read nothing is handed the log as it is", [e.get("k") for _, e in _b.since(-1, timeout=0)] == ["text", "setup_progress",
      "text", "prompt"])
html = pathlib.Path("ui/gui/web/index.html").read_text(encoding="utf-8")
check("the page has the card, its bar and its line", all(s in html for s in ('id="setup"', 'id="setupbar"', 'id="setupfill"', 'id="setuptext"')))

NODE = shutil.which("node")
if not NODE or subprocess.run([NODE, "-e", "require('playwright')"], capture_output=True, cwd=".").returncode != 0:
    print("ok   (skipped: no node with playwright here)", file=sys.__stdout__)
    print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
    sys.exit(1 if bad else 0)

tmp = tempfile.mkdtemp(); os.chdir(tmp)
import config
config.CRASH_LOG_PATH = os.path.join(tmp, "crash.log")          # the could-not-wake page writes its reason down: here, not in the tree
from ui import console
from ui.gui.bridge import Bridge
from ui.gui import server
from llm import launch
from llm.errors import Failure
import simlib, types

b = Bridge()
quiet = simlib.stand_in(chat=lambda **k: types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content="answer")),
                        embed=None, name="load_bar")              # a stand-in source: nothing here can reach a real model
b.install()
srv = server.make_server(b); server.serve(srv)
STEP = threading.Event()
LOADING = launch.line("loading") or ""
FAILED = launch.line("could_not_wake") or ""


def step():
    STEP.wait(15); STEP.clear()


class Load:
    """The runtime's load, scripted: the first rises to 60% and fails; Try again rises from 50% to ready; the third fails at once."""
    def __init__(self):
        self.state, self.cfg, self.facts_, self.build, self.n = "loading", {}, {}, "cuda", 0
        self.runtime = pathlib.Path(tmp) / "runtime"               # no processor build here: the page offers Try again and Quit
        self.closed = False

    def load(self, tell):
        self.n += 1
        if self.n == 1:
            step(); tell(0.3); step(); tell(0.6); step()
        elif self.n == 2:
            tell(0.5); step(); tell(1.0); self.state = "ready"; return
        self.state = "failed"
        raise Failure("unreachable", "the scripted load failed")

    def close(self):
        self.closed = True


screen = launch.Screen(say=console.out, ask=console.ask, progress=lambda f: console.setup_progress(f, LOADING),
                       uncover=lambda: console.creation_done())     # as main.py makes it
screen.rt = Load()
OUT = {}


def game():
    screen._load()                                        # the load runs behind the home page, as begin() starts it
    console.home({"title": "Meravia", "subtitle": "a test", "version": "0", "credits": "",
                  "saves": [{"name": "a", "where": "Ashford", "when": "today"}],
                  "continue": {"name": "a", "line": "Tester, the Vanguard", "where": "Ashford", "when": "today"}})
    OUT["choice"] = console.ask()                         # the page's Continue
    console.home_done()                                   # main.py: the home page goes, then Continue waits for the load
    OUT["first_wait"] = screen.wait()                     # could not wake, Try again, ready
    console.creation({"step": "name", "tabs": [["who", "Who you were"], ["name", "Your name"]], "tab": "name",
                      "wait": "The goddess is thinking."})  # New Game's pages, while the model is asked
    step()
    screen._load()                                        # the load (or its restart) fails under creation's page...
    screen.done.wait(10)
    try:
        screen.recover()                                  # ...and the call that finds it shows the page (llm/runtime.py chat_call)
        OUT["recovered"] = True
    except SystemExit:
        OUT["quit"] = True                                # Quit on the could-not-wake page ends the game
def run_game():
    try:
        game()
    except BaseException as e:                            # a fault in the scripted game is the test's, and is shown
        import traceback
        OUT["fault"] = traceback.format_exc()[-800:]
threading.Thread(target=run_game, daemon=True).start()

JS = r"""
const { chromium } = require('playwright');
const http = require('http');
const step = (url) => new Promise((res) => http.get(url, (r) => { r.resume(); r.on('end', res); }));
(async () => {
  const out = {};
  let br;
  try { br = await chromium.launch(); } catch (e) { console.log(JSON.stringify({ skip: String(e).slice(0, 80) })); return; }
  const page = await br.newPage({ viewport: { width: 1000, height: 700 } });
  out.errors = [];
  page.on('pageerror', (e) => out.errors.push(String(e).slice(0, 200)));
  const card = () => page.evaluate(() => ({ hidden: document.getElementById('setup').hidden, bar: document.getElementById('setupbar').hidden,
    width: document.getElementById('setupfill').style.width, text: document.getElementById('setuptext').textContent,
    home: document.getElementById('homepage').hidden, creation: document.getElementById('creation').hidden }));
  const page_told = (text) => page.evaluate((text) => {          // the could-not-wake page: told, answerable, and nothing over it
    const box = document.getElementById('input'), r = box.getBoundingClientRect();
    const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    const log = document.getElementById('log'), lr = log.getBoundingClientRect();
    const over = document.elementFromPoint(lr.left + lr.width / 2, Math.min(lr.bottom, window.innerHeight) - 30);
    return { told: log.innerText.includes(text), choices: log.innerText.includes('Try again') && log.innerText.includes('Quit'),
      input_free: !box.disabled && (top === box || box.contains(top)), log_seen: !!over && log.contains(over),
      home: document.getElementById('homepage').hidden, creation: document.getElementById('creation').hidden,
      card: document.getElementById('setup').hidden };
  }, text);
  try {
  await page.goto(process.argv[2]);
  await page.waitForFunction(() => document.querySelector('.home-continue') !== null, null, { timeout: 10000 });
  out.before = await card();
  await page.click('.home-continue');
  await page.waitForFunction(() => !document.getElementById('setup').hidden, null, { timeout: 10000 });
  out.at_once = await card();
  await step(process.argv[3]);
  await page.waitForFunction(() => document.getElementById('setupfill').style.width === '30%', null, { timeout: 10000 });
  out.first = await card();
  await step(process.argv[3]);
  await page.waitForFunction(() => document.getElementById('setupfill').style.width === '60%', null, { timeout: 10000 });
  out.second = await card();
  await step(process.argv[3]);
  const told = (n) => page.waitForFunction(([text, n]) => document.getElementById('log').innerText.split(text).length > n
    && document.getElementById('log').innerText.trim().endsWith('Quit') && !document.getElementById('input').disabled, [process.argv[4], n],
    { timeout: 10000 });
  await told(1);
  out.failed = await page_told(process.argv[4]);
  await page.fill('#input', '1'); await page.press('#input', 'Enter');          // Try again
  await page.waitForFunction(() => !document.getElementById('setup').hidden && document.getElementById('setupfill').style.width === '50%',
    null, { timeout: 10000 });
  out.again = await card();
  await step(process.argv[3]);
  await page.waitForFunction(() => !document.getElementById('creation').hidden, null, { timeout: 10000 });
  out.ready = await card();
  await step(process.argv[3]);
  await told(2);
  out.in_creation = await page_told(process.argv[4]);
  await page.fill('#input', '2'); await page.press('#input', 'Enter');          // Quit
  } catch (e) { out.error = String(e).slice(0, 300); out.at_error = await card().catch(() => null); }
  await br.close();
  console.log(JSON.stringify(out));
})();
"""
import http.server
class Step(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        STEP.set(); self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a):
        pass
st = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Step)
threading.Thread(target=st.serve_forever, daemon=True).start()
script = os.path.join(tmp, "bar.js")
open(script, "w").write(JS)
try:
    r = subprocess.run([NODE, script, srv.url, f"http://127.0.0.1:{st.server_address[1]}/", FAILED], capture_output=True, text=True,
                       timeout=120, cwd=ROOT)
    try:
        out = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
    except ValueError:
        out = {}
    if out.get("skip"):
        print(f"ok   (skipped: no browser to run: {out['skip']})", file=sys.__stdout__)
    else:
        bf, a0, f, s = (out.get(k) or {} for k in ("before", "at_once", "first", "second"))
        check("the page ran; the home page is up and no card is shown before Continue", bf.get("hidden") is True and bf.get("home") is False
              and not out.get("errors") and not out.get("error"), (out, r.stdout[-300:], r.stderr[-600:]))
        check("Continue: the home page goes and the card shows the loading line at once, at 0", a0.get("hidden") is False and a0.get("home") is True
              and a0.get("bar") is False and a0.get("width") == "0%" and a0.get("text") == LOADING, a0)
        check("...the bar rises as the load does", f.get("width") == "30%" and s.get("width") == "60%" and s.get("hidden") is False, (f, s))
        fl = out.get("failed") or {}
        check("a load that could not wake: its page is told in the story, nothing over it, and answerable", fl.get("told") and fl.get("choices")
              and fl.get("input_free") and fl.get("log_seen") and fl.get("home") is True and fl.get("card") is True, fl)
        check("Try again shows the card again, and it goes at ready", (out.get("again") or {}).get("hidden") is False
              and (out.get("ready") or {}).get("hidden") is True and OUT.get("choice") == "home:continue" and OUT.get("first_wait") is True,
              (out.get("again"), out.get("ready"), OUT))
        ic = out.get("in_creation") or {}
        check("a load found failed during creation: creation's page goes, and the page is told and answerable", ic.get("told")
              and ic.get("choices") and ic.get("input_free") and ic.get("log_seen") and ic.get("creation") is True, ic)
        threading.Event().wait(1.0) if "quit" not in OUT else None
        check("...and its Quit ends the game", OUT.get("quit") is True and screen.rt.closed, OUT)
    check("...and the scripted game behind the page asked the model nothing", quiet.live() and not quiet.src.calls, dict(quiet.src.calls))
finally:
    quiet()
    srv.shutdown(); st.shutdown()
    os.chdir(ROOT)
    shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
