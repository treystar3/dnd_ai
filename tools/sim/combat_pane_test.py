"""(f405) The fight pane after a fight, and an ability's card in it: the real page in a headless browser, behind the real server. While
the fight goes on, hovering an ability shows its full card, as the character pane does. When it ends the pane stays, titled the last
fight, with how it ended and every line of its log, and a button brings it back until the next fight replaces it. Skipped where no
browser is installed."""
import json, os, random, shutil, subprocess, sys, tempfile, threading, time, types
sys.path.insert(0, os.path.abspath("."))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- the card each ability carries to the pane
import simlib
simlib.install(simlib.Stub("mage", 3))
from engine import combat
from scenes.combat_scene import CombatScene
char, _ = simlib.make_character("mage", random.Random(2))
sc = CombatScene.__new__(CombatScene)
sc.ws = types.SimpleNamespace(player=types.SimpleNamespace(character=char))
me = combat.fighter_from_character(char)
mv = me.moves[0]
tip = sc.move_tip(mv)
check("an ability in the fight pane carries its full card, as the character pane shows it", tip and tip[0] == ["h", mv.name] and len(tip) >= 3, tip)
relic = combat.Move(id="relic_x", name="Ember Ring", effect="relic", tier="light", reach="self", resource="mana", text="burns a foe once a fight")
check("...a relic's power, by what it does", sc.move_tip(relic) == [["h", "Ember Ring"], ["", "burns a foe once a fight"]])

NODE = shutil.which("node")
if not NODE or subprocess.run([NODE, "-e", "require('playwright')"], capture_output=True, cwd=".").returncode != 0:
    print("ok   (skipped the page: no node with playwright here)", file=sys.__stdout__)
    print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
    sys.exit(1 if bad else 0)

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


def pane(round_, hits, over=""):
    you = {"id": "p", "name": "You", "level": 1, "hp": 40, "max_hp": 60, "where": "", "zone": "", "row": "front", "engaged": [], "statuses": [],
           "elevated": False, "stamina": 30, "max_stamina": 45, "mana": 80, "max_mana": 105, "buffs": []}
    wolf = {"id": "e1", "name": "wolf 1", "level": 1, "hp": 0 if over else 12, "max_hp": 28, "where": "at the front", "zone": "", "row": "front",
            "engaged": [], "statuses": [], "elevated": False, "stamina": 0, "max_stamina": 0, "mana": 0, "max_mana": 0}
    return {"round": round_, "danger": "TRIVIAL", "enemies": [] if over else [wolf], "reserves": 0, "allies": [], "you": you,
            "moves": [{"id": "inferno", "name": "Inferno Release", "resource": "mana", "cost": 22, "stamina_cost": 0, "effect": "damage",
                       "tier": "light", "cooldown": 3, "left": 0, "ready": True, "reason": "",
                       "tip": [["h", "Inferno Release"], ["dim", "Spell · Ranged reach · 22 mana"], ["", "You gather raw fire and release it."]]}],
            "items": [], "hits": hits, "over": over}


HIT1 = {"id": "h-1", "round": 1, "att": "You", "att_side": "player", "label": "use Inferno Release on", "dfn": "wolf 1", "figure": "(16 damage)", "outcome": "hit"}
HIT2 = {"id": "h-2", "round": 2, "att": "You", "att_side": "player", "label": "use Inferno Release on", "dfn": "wolf 1", "figure": "(14 damage)", "outcome": "kill"}


def game():
    while True:
        t = console.ask(main=True)
        if t == "quit":
            return
        if t == "fight":
            console.combat_state(pane(1, [HIT1]))
            console.narrate("The wolf comes on.")
        elif t == "win":
            console.combat_state(pane(2, [HIT1, HIT2], over="victory"))
            console.combat_state(None)
            console.narrate("The wolf is down.")
        else:
            console.narrate("A short line.")
threading.Thread(target=game, daemon=True).start()

JS = r"""
const { chromium } = require('playwright');
(async () => {
  const out = {};
  let br;
  try { br = await chromium.launch(); } catch (e) { console.log(JSON.stringify({ skip: String(e).slice(0, 80) })); return; }
  const page = await br.newPage({ viewport: { width: 1100, height: 760 } });
  await page.goto(process.argv[2]);
  await page.waitForFunction(() => document.getElementById('input') !== null);
  await page.evaluate(() => { document.getElementById('homepage').hidden = true; });
  await page.waitForFunction(() => !document.getElementById('input').disabled, null, { timeout: 10000 });
  const say = async (t) => { await page.fill('#input', t); await page.press('#input', 'Enter'); };
  await say('fight');
  await page.waitForFunction(() => document.getElementById('log').innerText.includes('comes on'), null, { timeout: 10000 });
  await page.waitForTimeout(300);
  out.during_title = await page.textContent('#sidetitle');
  await page.hover('#sidebody .mv.hoverrow');
  await page.waitForTimeout(200);
  out.tip = await page.evaluate(() => { const t = [...document.querySelectorAll('body > div.tip')].pop(); return t && !t.hidden ? t.innerText : ''; });
  await say('win');
  await page.waitForFunction(() => document.getElementById('log').innerText.includes('is down'), null, { timeout: 10000 });
  await page.waitForTimeout(300);
  out.after_title = await page.textContent('#sidetitle');
  out.after_body = await page.textContent('#sidebody');
  out.log_rows = await page.evaluate(() => document.querySelectorAll('#sidebody .clog .cl').length);
  out.button = await page.evaluate(() => [...document.querySelectorAll('#buttons button')].map((b) => b.textContent).filter((t) => t.includes('⚔')));
  out.abilities_after = await page.evaluate(() => document.querySelectorAll('#sidebody .mv').length);
  await say('quit');
  await br.close();
  console.log(JSON.stringify(out));
})();
"""
script = os.path.join(tmp, "pane.js")
open(script, "w").write(JS)
r = subprocess.run([NODE, script, srv.url], capture_output=True, text=True, timeout=120, cwd=ROOT)
try:
    out = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except ValueError:
    out = {}
if out.get("skip"):
    print(f"ok   (skipped the page: no browser to run: {out['skip']})", file=sys.__stdout__)
else:
    check("the page ran", bool(out), (r.stdout[-400:], r.stderr[-800:]))
    check("in a fight, hovering an ability shows its full card", "Inferno Release" in (out.get("tip") or "") and "gather raw fire" in (out.get("tip") or ""), out)
    check("when the fight ends the pane stays, as the last fight", "Last fight" in (out.get("after_title") or "") and "Won, in 2 rounds" in (out.get("after_body") or ""), out)
    check("...with every line of its log, the killing blow too", out.get("log_rows") == 2, out)
    check("...a button brings it back until the next fight", out.get("button") == ["⚔ Last fight"], out)
    check("...and no abilities to use in a fight that is over", out.get("abilities_after") == 0, out)

srv.shutdown()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
