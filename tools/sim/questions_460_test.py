"""(f460) A question the world asks in the middle of a turn ends the turn, and the answer is the next line typed: the words that count
as yes and as no; a line that is not an answer lets the question go, says so and is read as new; a question is kept in the save (a
#command typed meanwhile leaves it standing, quitting keeps it, a save opened on one asks it again) and goes back with a rolled-back turn;
the clarify question of f321 rides the same row; data/rules/questions.yaml is checked at startup; and the ratchet: the only console.ask()
calls left inside a turn are Maren's seven (f461 takes them)."""
import random
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
from ui import console
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


from engine import questions
Q = questions.Q

# ---- the words
yes = ("y", "Yes.", "yes, go on", "Sure", "I do", "ok then", "Aye", "all right, let us")
check("the words for yes", all(questions.yes_no(t) is True for t in yes), [t for t in yes if questions.yes_no(t) is not True])
no = ("n", "No", "no, I keep it", "never mind", "I do not", "cancel", "Not now.", "I don't think so")
check("the words for no", all(questions.yes_no(t) is False for t in no), [t for t in no if questions.yes_no(t) is not False])
other = ("I go to the inn", "", "nothing for me", "yesterday I saw him", "I ask about the road", "Which way is the ruin?")
check("anything else is not an answer", all(questions.yes_no(t) is None for t in other), [t for t in other if questions.yes_no(t) is not None])
rng = random.Random(7)
runs = [questions.dropped(rng) for _ in range(30)]
check("the line that lets a question go is one of the data's, never the same twice running",
      all(l in Q["dropped"] for l in runs) and all(a != b for a, b in zip(runs, runs[1:])) and len(set(runs)) >= 3)
check("the data is checked, and clean", questions.problems() == [], questions.problems())
broken = {"tries": 0, "yes": ["y", "yes", "ok"], "no": ["n", "no", "ok"], "dropped": Q["dropped"][:5] + ["The model dropped it - say it again?"]}
p = questions.problems(broken)
check("...and a broken copy is named for each fault", any("tries" in x for x in p) and any("both yes and no" in x for x in p)
      and any("machinery" in x for x in p) and any("dash" in x for x in p) and any("asks something" in x for x in p), p)
check("the startup check runs it", "_questions.problems()" in Path("engine/data_check.py").read_text(encoding="utf-8"))

# ---- the scene: a question ends the turn; the next line answers it
from core.models import KeyItem
from llm.contracts import ActionIntent
g = simlib.campaign("questions_460", cls="warrior", seed=3)
ws, store = g.scene, g.store
shown = simlib.quiet_console()
c = ws.player.character
c.key_items.append(KeyItem(id="letter", name="a sealed letter", kind="quest", for_whom="the watch captain", day=1))
store.save_player(ws.player)
ws.halted = False
ws.on_discard(ActionIntent(kind="discard", item="sealed letter"), "I throw the letter away")
asked = store.load_question()
check("the question is asked and ends the line", bool(asked) and asked["kind"] == "discard" and ws.halted
      and any("Discard it for good" in t for k, t in shown), (asked, shown[-2:]))
check("...and nothing has happened yet", any(k.name == "a sealed letter" for k in c.key_items))
shown.clear()
ws.handle("I look around")
texts = [t for k, t in shown]
check("a line that is not an answer lets the question go, says so in the narrator's words, and is read as new",
      store.load_question() is None and any(t in Q["dropped"] for t in texts) and any(k.name == "a sealed letter" for k in c.key_items)
      and any(t not in Q["dropped"] for t in texts), texts[:4])
ws.on_discard(ActionIntent(kind="discard", item="sealed letter"), "I throw the letter away")
shown.clear()
ws.handle("no")
check("no keeps it, and the question is spent", store.load_question() is None and any("Kept" in t for k, t in shown)
      and any(k.name == "a sealed letter" for k in c.key_items), shown[:3])
ws.on_discard(ActionIntent(kind="discard", item="sealed letter"), "I throw the letter away")
shown.clear()
turn0 = store.meta.turn
ws.handle("yes")
check("yes does it, and the answer is a turn of its own", not any(k.name == "a sealed letter" for k in c.key_items)
      and any("Discarded" in t for k, t in shown) and store.meta.turn == turn0 + 1 and store.load_question() is None, shown[:3])

# ---- the question lives in the save
ws.ask_next("discard", "Discard it?", item="x", text="t")
try:
    with store.transaction():
        store.clear_question()
        raise RuntimeError("the answering turn fell over")
except RuntimeError:
    pass
check("a question stands again when the turn that would have answered it rolled back", store.load_question() is not None)
try:
    with store.transaction():
        ws.ask_next("fork", "Which way?", top="parth", dir="north", text="t", events=0, tries=0)
        raise RuntimeError("the asking turn fell over")
except RuntimeError:
    pass
check("...and a question asked by a turn that rolled back is gone with it", (store.load_question() or {}).get("kind") == "discard")
store.clear_question()
ws.handle("I look around")
check("with no question standing a line is read as it always was", store.load_question() is None)

# ---- the clarify question of f321 rides the same row
ws.pending_clarify = {"text": "go there", "question": "Where is there?", "place": "greyhollow"}
asked = store.load_question()
check("the clarify question is kept with the others", bool(asked) and asked["kind"] == "clarify" and ws.pending_clarify["text"] == "go there"
      and ws.pending_clarify.get("place") == "greyhollow", asked)
ws.pending_clarify = None
check("...and is cleared the same way", store.load_question() is None and ws.pending_clarify is None)

# ---- the whole loop: a save opened on a question asks it again; a #command leaves it standing; the next line answers it
c.key_items.append(KeyItem(id="map", name="a torn map", kind="key", day=1))
ws.halted = False
ws.on_discard(ActionIntent(kind="discard", item="torn map"), "I throw the map away")
store.save_player(ws.player)
g.close()
g2 = simlib.campaign("questions_460", fresh=False)
ws2 = g2.scene
shown = simlib.quiet_console()
script = ["#inventory", "y", "quit"]
console.ask = lambda *a, **k: script.pop(0) if script else "quit"
ws2.run()
texts = [t for k, t in shown]
i_q = next((i for i, t in enumerate(texts) if "Discard it for good" in t), None)
i_d = next((i for i, t in enumerate(texts) if "Discarded" in t), None)
check("a save opened on a question asks it again, once, before the first line", i_q is not None
      and sum(1 for t in texts if "Discard it for good" in t) == 1, texts[:8])
check("a #command typed meanwhile leaves the question standing, and the next line answers it", i_d is not None and i_q is not None
      and i_d > i_q and not any(k.name == "a torn map" for k in ws2.player.character.key_items), texts)
check("the save holds no question once it is answered", g2.store.load_question() is None)
g2.close()

# ---- the ratchet: console.ask() inside a turn is gone from every site but Maren's tutorial (f461 takes those)
left = {}
for f in sorted(list(Path("scenes").glob("*.py")) + list(Path("engine").glob("*.py")) + list(Path("services").glob("*.py"))):   # (f503) services too
    if f.name == "home.py":                                      # the save menu: a menu, not a turn
        continue
    n = len(re.findall(r"console\.ask\(\s*\)", f.read_text(encoding="utf-8")))
    if n:
        left[f.as_posix()] = n
check("no question is asked inside a turn anywhere (f461 took Maren's seven)", left == {}, left)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
