"""(f458) The window forgets the campaign it left. Going to the main menu and opening another game cleared the story column, but the page
kept the rest of the game it had left: the block the next line was appended to (so "Continuing as ..." could land inside a detached
block and never show), the fight's pane state and hit map, the gear tips, the map's pan and zoom, the journal's open entries and search,
the typed-line history, and the creation page's remembered start (so a second New game did not start from chance). Now hideHome, the
page's one campaign-closed reset, forgets all of it. The real page in a headless browser, behind the real server, with a scripted game;
skipped where no browser is installed; the source checks run everywhere."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, threading
sys.path.insert(0, os.path.abspath("."))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

ROOT = os.path.abspath(".")
js_src = pathlib.Path("ui/gui/web/app.js").read_text(encoding="utf-8")
hide = js_src[js_src.index("function hideHome()"):js_src.index("function forgetCampaign()")]
forget = js_src[js_src.index("function forgetCampaign()"):][:900]
check("hideHome drops the block the next line would be appended to, and forgets the campaign", "cur = null; lastBlank = true;" in hide and "forgetCampaign();" in hide)
check("...the fight, its hits, the gear tips, the map view, the journal, the typed lines and the creation page's start", all(s in forget for s in
      ("Object.assign(combat, { active: false", "hitsMap, tipMap", "mapView = null", "journalQuery = \"\"; journalOpen.clear()", "history.length = 0; hpos = 0", "cr.who = null")), forget)

NODE = shutil.which("node")
if not NODE or subprocess.run([NODE, "-e", "require('playwright')"], capture_output=True, cwd=".").returncode != 0:
    print("ok   (skipped: no node with playwright here)", file=sys.__stdout__)
    print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
    sys.exit(1 if bad else 0)

tmp = tempfile.mkdtemp(); os.chdir(tmp)
from ui import console
from ui.gui.bridge import Bridge
from ui.gui import server
from llm import gateway

b = Bridge()
gateway._client.chat = lambda *a, **k: "answer"
b.install()
srv = server.make_server(b); server.serve(srv)

SEEN = []
def game():
    console.narrate("The old story, long since told.")
    while True:
        t = console.ask(main=True)
        SEEN.append(t)
        if t == "quit":
            return
        if t == "#menu":                                   # the main menu, as main.py shows it between campaigns, then another game opens
            console.home({"title": "Meravia", "subtitle": "a test", "version": "0", "saves": [], "continue": None, "credits": ""})
            console.ask()                                  # the page answers with a button
            console.home_done()
            console.note("Continuing as Tester, the Vanguard.")
        elif t.startswith("#"):                            # the pinned view the bridge asks for at a prompt, run as the game runs it
            with console.scope(t):
                print("VIEW OF", t)
        else:
            console.narrate("A short line.")
threading.Thread(target=game, daemon=True).start()

JS = r"""
const { chromium } = require('playwright');
(async () => {
  const out = {};
  let br;
  try { br = await chromium.launch(); } catch (e) { console.log(JSON.stringify({ skip: String(e).slice(0, 80) })); return; }
  const page = await br.newPage({ viewport: { width: 1100, height: 700 } });
  await page.goto(process.argv[2]);
  await page.waitForFunction(() => document.getElementById('input') !== null);
  await page.evaluate(() => { document.getElementById('homepage').hidden = true; });
  await page.waitForFunction(() => !document.getElementById('input').disabled, null, { timeout: 10000 });
  const say = async (t) => { await page.fill('#input', t); await page.press('#input', 'Enter'); };
  await say('hello');
  await page.waitForFunction(() => document.getElementById('log').innerText.includes('A short line'), null, { timeout: 10000 });
  await page.evaluate(() => { history.push('x'); hpos = 1; mapView = { here: 'p', box: {} }; journalOpen.add('z'); journalQuery = 'q'; cr.who = { x: 1 };
    hitsMap.k = 1; tipMap.k = 1; combat.active = true; combat.rows.push(1); combat.seen.add('s'); combat.mode = 'fight'; });
  out.before = await page.evaluate(() => document.getElementById('log').children.length);
  await say('#menu');
  await page.waitForFunction(() => !document.getElementById('homepage').hidden, null, { timeout: 10000 });
  out.home_shown = true;
  await page.evaluate(() => homeSend('home:new'));
  await page.waitForFunction(() => document.getElementById('log').innerText.includes('Continuing as'), null, { timeout: 10000 });
  await page.waitForTimeout(300);
  out.after = await page.evaluate(() => { const l = document.getElementById('log'); return { blocks: l.children.length, text: l.innerText.trim(),
    first_class: l.children[0] ? l.children[0].className : '' }; });
  out.state = await page.evaluate(() => ({ history: history.length, hpos, mapView, journalOpen: journalOpen.size, journalQuery, who: cr.who,
    hits: Object.keys(hitsMap).length, tips: Object.keys(tipMap).length, combat: { active: combat.active, rows: combat.rows.length, seen: combat.seen.size, mode: combat.mode } }));
  out.homepage_hidden = await page.evaluate(() => document.getElementById('homepage').hidden);
  await say('quit');
  await br.close();
  console.log(JSON.stringify(out));
})();
"""
script = os.path.join(tmp, "reset.js")
open(script, "w").write(JS)
r = subprocess.run([NODE, script, srv.url], capture_output=True, text=True, timeout=120, cwd=ROOT)
try:
    out = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except ValueError:
    out = {}
if out.get("skip"):
    print(f"ok   (skipped: no browser to run: {out['skip']})", file=sys.__stdout__)
else:
    check("the page ran, with a story and a campaign's state on it", bool(out) and (out.get("before") or 0) >= 1, (out, r.stdout[-300:], r.stderr[-600:]))
    check("the main menu was shown, and another game opened from it", out.get("home_shown") and out.get("homepage_hidden") is True, out)
    after, st = out.get("after") or {}, out.get("state") or {}
    check("the story column holds only the new game's first line, in a block of its own", after.get("blocks") == 1 and "Continuing as Tester" in after.get("text", "")
          and "old story" not in after.get("text", "") and "k-note" in after.get("first_class", ""), (after, SEEN, [e.get("k") for _, e in b.log][-12:]))
    check("the window forgot the fight it left", st.get("combat") == {"active": False, "rows": 0, "seen": 0, "mode": "view"} and st.get("hits") == 0, st)
    check("...the gear tips, the map view, the journal's search and open entries", st.get("tips") == 0 and st.get("mapView") is None and st.get("journalQuery") == ""
          and st.get("journalOpen") == 0, st)
    check("...the typed lines, and the creation page's remembered start", st.get("history") == 0 and st.get("hpos") == 0 and st.get("who") is None, st)

srv.shutdown()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
