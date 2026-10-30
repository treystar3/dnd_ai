"""(f396) The story column never pulls a reader down: the real page in a headless browser, behind the real server, with a scripted game.
A long passage is shown from its top, not landed on at its end; a reader who has scrolled up stays where they are while new text comes,
and a button says there is more below; the player's own line always brings the log to it. Skipped where no browser is installed."""
import json, os, shutil, subprocess, sys, tempfile, threading, time
sys.path.insert(0, os.path.abspath("."))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NODE = shutil.which("node")
if not NODE or subprocess.run([NODE, "-e", "require('playwright')"], capture_output=True, cwd=".").returncode != 0:
    print("ok   (skipped: no node with playwright here)")
    print("\nALL PASS")
    sys.exit(0)

ROOT = os.path.abspath(".")
tmp = tempfile.mkdtemp(); os.chdir(tmp)
from ui import console
from ui.gui.bridge import Bridge
from ui.gui import server
from llm import gateway

b = Bridge()
gateway._client.chat = lambda *a, **k: "answer"
b.install()
srv = server.make_server(b); server.serve(srv)
LONG = "\n".join(f"Line {i} of a long passage: the tide draws back over the stones and the cave breathes cold air." for i in range(90))

def game():
    while True:
        t = console.ask(main=True)
        if t == "quit":
            return
        if t == "long":
            console.narrate(LONG)
        elif t == "think":                                 # (f402) a turn of several calls to the model: the thinking line comes and goes
            for _ in range(4):
                b.busy(True); time.sleep(0.3); b.busy(False); time.sleep(0.12)
            console.narrate("The answer, after some thought.")
        elif t == "later":
            console.narrate("A short answer.")
            time.sleep(2.0)
            console.narrate("Something more, a little later.")
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
  const log = (f) => page.evaluate(f);
  const wait = (ms) => page.waitForTimeout(ms);
  const atBottom = () => log(() => { const l = document.getElementById('log'); return l.scrollHeight - l.scrollTop - l.clientHeight < 24; });
  const more = () => page.isVisible('#more');

  await say('long');
  await page.waitForFunction(() => document.getElementById('log').innerText.includes('Line 89'), null, { timeout: 10000 });
  await wait(400);
  out.echo_in_view = await log(() => { const l = document.getElementById('log'); const e = [...l.querySelectorAll('.echo')].pop();
    const r = e.getBoundingClientRect(), L = l.getBoundingClientRect(); return r.top >= L.top - 1 && r.bottom <= L.bottom + 1; });
  out.long_at_bottom = await atBottom();
  out.long_more = await more();
  await page.click('#more');
  await wait(400);
  out.after_more = await log(() => document.getElementById('log').scrollTop);
  await log(() => { const l = document.getElementById('log'); l.scrollTop = l.scrollHeight; });
  await wait(400);
  out.more_gone = !(await more());

  await say('later');
  await page.waitForFunction(() => document.getElementById('log').innerText.includes('A short answer'), null, { timeout: 10000 });
  await wait(200);
  out.short_follows = await atBottom();
  await log(() => { const l = document.getElementById('log'); l.scrollTop = l.scrollTop - 30; });
  await wait(200);
  out.held = await log(() => document.getElementById('log').scrollTop);
  await page.waitForFunction(() => document.getElementById('log').innerText.includes('Something more'), null, { timeout: 10000 });
  await wait(400);
  out.after_later = await log(() => document.getElementById('log').scrollTop);
  out.later_more = await more();

  await say('short');
  await page.waitForFunction(() => document.querySelectorAll('#log .echo').length >= 3, null, { timeout: 10000 });
  await wait(400);
  await say('think');
  await page.waitForFunction(() => document.querySelectorAll('#log .echo').length >= 4, null, { timeout: 10000 });
  await wait(150);
  const samples = [];
  while (!(await log(() => document.getElementById('log').innerText.includes('after some thought')))) {
    samples.push(await log(() => { const l = document.getElementById('log'); const b = document.getElementById('busy');
      return [l.clientHeight, l.scrollTop, !b.hidden]; }));
    await wait(40);
    if (samples.length > 200) break;
  }
  out.think_heights = [...new Set(samples.map((s) => s[0]))];
  out.think_tops = [...new Set(samples.map((s) => s[1]))];
  out.think_busy_seen = samples.filter((s) => s[2]).length;
  out.think_busy_gaps = samples.slice(samples.findIndex((s) => s[2])).filter((s) => !s[2]).length;
  await say('short');
  await page.waitForFunction(() => document.querySelectorAll('#log .echo').length >= 5, null, { timeout: 10000 });
  await wait(400);
  out.own_line_bottom = await atBottom();
  out.own_line_more = await more();
  await say('quit');
  await br.close();
  console.log(JSON.stringify(out));
})();
"""
script = os.path.join(tmp, "follow.js")
open(script, "w").write(JS)
r = subprocess.run([NODE, script, srv.url], capture_output=True, text=True, timeout=120, cwd=ROOT)
try:
    out = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except ValueError:
    out = {}
if out.get("skip"):
    print(f"ok   (skipped: no browser to run: {out['skip']})", file=sys.__stdout__)
else:
    check("the page ran", bool(out), (r.stdout[-400:], r.stderr[-800:]))
    check("a long passage is shown from its top: the player's line stays in view, the log is not landed at the passage's end",
          out.get("echo_in_view") and not out.get("long_at_bottom"), out)
    check("...and a button says there is more below", out.get("long_more"), out)
    check("the button brings the reader on, and at the bottom it goes away", (out.get("after_more") or 0) > 0 and out.get("more_gone"), out)
    check("a short answer, the reader at the bottom: the log follows it", out.get("short_follows"), out)
    check("a reader who has scrolled up, even a little, is not pulled down by new text", abs((out.get("after_later") or 0) - (out.get("held") or -99)) <= 2, out)
    check("...and is told there is more below", out.get("later_more"), out)
    check("the player's own line brings the log down to it", out.get("own_line_bottom") and not out.get("own_line_more"), out)
    check("(f402) while the world thinks, the story never moves: its height and place stay put as the thinking line comes and goes",
          len(out.get("think_heights") or []) == 1 and len(out.get("think_tops") or []) == 1, out)
    check("...the thinking line shows, and stays up through the gaps between one turn's calls", (out.get("think_busy_seen") or 0) > 5
          and out.get("think_busy_gaps") == 0, out)

srv.shutdown()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
