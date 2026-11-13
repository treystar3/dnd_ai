"""(f617) The world's news and history carry no dash. Six sites in the engine wrote lines like "<title> - lost." into them (the audit of
2026-11-13, docs/design/18 part E), and news and history are what the people of the world know and the narrator is told: a dash there
is a dash to copy (f403, f413). The one writer of each (engine/pulse.py add_news, add_history) now takes the dashes out, as every line
the narrator is handed already has them taken out, so no site can put one in.
Run: python tools/sim/news_dash_617_test.py"""
import json
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools/sim")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import pulse

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def dashed(text: str) -> bool:
    return any(d in text for d in ("—", "–", " - ", "--"))


# ---- the two writers, on lines of each shape a site writes and some no site does
LINES = ["The Grain Blight - lost. The fields are bare.", "The Grain Blight - settled by the reeve.",
         "Parth held against The Red Hand - Asha stood at the gate. Two were hurt.", "The mill burned — nobody saw who.",
         "The road is shut -- the bridge is out.", "It lasted 3–5 days."]
state = {}
for x in LINES:
    pulse.add_news(state, x, "parth", 100, ["everyone"])
    pulse.add_history(state, x, "parth", 100)
news, history = [n["text"] for n in state["news"]], [h["text"] for h in state["history"]]
check("a line of news is kept without its dash, whatever dash it was", len(news) == len(LINES) and not any(dashed(x) for x in news), news)
check("...and so is a line of history", len(history) == len(LINES) and not any(dashed(x) for x in history), history)
check("...the words are all still there, the dash a colon or a comma", news[0] == "The Grain Blight: lost. The fields are bare."
      and "Asha stood at the gate" in news[2] and "3 to 5 days" in news[5], (news[0], news[2], news[5]))
pulse.add_news(state, "A half-elf came through with well-made boots.", "parth", 100, ["everyone"])
check("...a hyphen inside a word is no dash", state["news"][-1]["text"] == "A half-elf came through with well-made boots.")
before = len(state["news"])
pulse.add_news(state, LINES[0], "parth", 200, ["everyone"])
check("the same news told again is still one tale told twice", len(state["news"]) == before and state["news"][-1]["times"] == 2
      and state["news"][-1]["text"] == news[0], state["news"][-1])

# ---- the class: every line of news and history the world script's play leaves, on every state it saves
import world_script
run = world_script.play("news_dash_617", stub)
states = [json.loads(text) for _, text in run.steps] + [run.game.store.load_world_state()]
rows = [r["text"] for st in states for r in st.get("news", []) + st.get("history", [])]
check("the world script plays whole, and no line of news or history on any state it saves carries a dash",
      all(run.cover.values()) and len(states) > 10 and len(rows) > 50 and not any(dashed(x) for x in rows),
      (len(states), len(rows), sorted({x for x in rows if dashed(x)})[:3]))
check("...among them the ends of situations, which were the lines that carried one", any(": " in x for x in rows), rows[:6])

# ---- (f617's review) a deed's tale is news too, written by engine/standing.py: the same filter, and no writer besides
from pathlib import Path
from engine import standing
ws = run.game.scene
kind = next(k for k, v in standing.DEEDS.items() if v.get("public") and "{item}" in v["text"] and "{item}" in v["twisted"])
town = next(p for p, v in ws.world.places.items() if not v.danger)
tales = []
for seed in range(12):                                   # some told true, some twisted
    e = standing.report(run.game.store, ws.world, ws.player, kind, town, "Parth - the old town", "Asha", ws.minutes + seed, 1, item="the Sun — Blade", seed=seed)
    tales += [e["text"], e["deed"]["true"]]
check("a deed's tale, told true or twisted, carries no dash whatever its names hold", len(tales) == 24 and len(set(tales)) >= 2
      and not any(dashed(x) for x in tales) and all("Asha" in x for x in tales), sorted(set(tales)))
ROOT = Path(__file__).resolve().parent.parent.parent
import re
adds = re.compile(r"""news(?:"\])?(?:\.append|\.extend|\.insert|\s*\+=)""")      # the list grown, by whatever name it is reached
writers = sorted(f.name for d in ("engine", "scenes") for f in (ROOT / d).glob("*.py") if adds.search(f.read_text(encoding="utf-8")))
check("...and news has the two writers that take the dashes out, no third (a new one is added here with its filter)",
      writers == ["pulse.py", "standing.py"], writers)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
