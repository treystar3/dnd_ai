"""(f461) Maren's meeting as stages: each of her questions ends the line and the next line answers it, and the whole meeting, played as
typed lines, makes the same model calls, speaks in the same order and leaves the same state as the meeting that read the keyboard inside
one turn (the fixture tools/sim/fixtures/mentor_461.json, recorded from the f460 tree for four answer sets). Also: a hostile answer at the
proof stage is pressed by the stage, not read by the interpreter; a save closed on one of her questions asks it again, in her voice, when
it opens; the fence (engine/questions.py) makes any console.ask inside a turn a fault the turn survives; and the ratchet is zero."""
import json
import re
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
SAID = []
uc.say = lambda t, s="": SAID.append(["say", s, t])
uc.dialogue = lambda b, s, t, a: SAID.append(["dialogue", s, t])
uc.npc_says = lambda s, t, g="": SAID.append(["npc_says", s, t])
uc.narrate = lambda t: SAID.append(["narrate", "", t])
uc.note = lambda m, *a, **k: None
uc.ledger = lambda *a, **k: None


def no_ask(*a, **k):
    raise AssertionError("the world asked in the middle of a turn (f461: a question ends the turn; the next line answers it)")


uc.ask = no_ask
from engine import mentor, questions
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


M = mentor.M
U, N = M["unnamed"], mentor.NAME
FIX = json.loads(Path("tools/sim/fixtures/mentor_461.json").read_text(encoding="utf-8"))
GAMES = []


def fresh(save):
    """The campaign the fixture was recorded on: seed 5, a warrior of the second seed, Parth at the eighteen-hundredth minute, Maren due."""
    g = simlib.campaign(save, cls="warrior", seed=5, minutes=1800, turn=1, location="parth", never_mentor=False, char_seed=2)
    GAMES.append(g)
    st, w = g.store, g.scene
    config.TURN_LOG_PATH = f"saves/{save}/turns.jsonl"
    w.narrate = lambda e, t="": None
    w.narrate_with = lambda *a, **k: None
    w.show_exits = lambda *a, **k: None
    w.mentor_escort = lambda: SAID.append(["escort", "", ""])
    return st, w


def done(save):
    """Close the campaign opened by fresh(save), the way main.py closes one, and remove its folder."""
    g = next((x for x in GAMES if x.name == save), None)
    if g is not None:
        g.close()
        GAMES.remove(g)
    shutil.rmtree(f"saves/{save}", ignore_errors=True)


# ---- the meeting as typed lines, held to the fixture of the meeting that read the keyboard (same order, same stub, same seeds)
stages_seen = {}
for name, fx in FIX.items():
    st, w = fresh(f"stages461_{name}")
    before = dict(stub.calls)
    SAID.clear()
    answers = list(fx["answers"])
    w.mentor_intercept("I look around")
    seen, n = [], 0
    while st.load_question() and n < 30:
        q = st.load_question()
        seen.append((q["kind"], q["data"].get("stage"), q.get("speaker")))
        n += 1
        w.handle(answers.pop(0) if answers else "go on")
    calls = {k: v - before.get(k, 0) for k, v in stub.calls.items() if v - before.get(k, 0)}
    m = w.player.mentor
    state = {"stage": mentor.stage(w.player), "introduced": bool(m.get("introduced")), "skipped": bool(m.get("skipped")),
             "chat": [list(x) for x in m.get("chat", []) if x[0] == "Player"]}
    check(f"{name}: the same model calls, by title", calls == fx["calls"], (calls, fx["calls"]))
    check(f"{name}: the same voices in the same order", [x[:2] for x in SAID] == fx["spoke"], ([x[:2] for x in SAID], fx["spoke"]))
    check(f"{name}: the same state at the end", state == fx["state"], (state, fx["state"]))
    check(f"{name}: the same answers used, the same left over", answers == fx["left_unanswered"], (answers, fx["left_unanswered"]))
    check(f"{name}: each of her questions ended a line, and none stands at the end", n >= 3 and all(k == "mentor" for k, _, _ in seen) and st.load_question() is None, (n, seen))
    stages_seen[name] = [(s, who) for _, s, who in seen]
    done(f"stages461_{name}")

check("the stages of the walkthrough, each under the label she had then", stages_seen["lecture"] == [("first", U), ("proof", U), ("know", N), ("lecture", N), ("waiting", N)], stages_seen["lecture"])
check("two yeses: first, proof, know, sure, and she is gone", stages_seen["skip"] == [("first", U), ("proof", U), ("know", N), ("sure", N)], stages_seen["skip"])
check("a yes then a doubt: the walkthrough after the check", stages_seen["doubt"] == [("first", U), ("proof", U), ("know", N), ("sure", N), ("lecture", N), ("waiting", N)], stages_seen["doubt"])
check("a question back at the proof stage is pressed by the stage, still cold", stages_seen["question_back"][:3] == [("first", U), ("proof", U), ("proof", U)], stages_seen["question_back"])

# ---- a hostile answer at the proof stage is pressed by the stage, not read by the interpreter
st, w = fresh("stages461_hostile")
SAID.clear()
w.mentor_intercept("I look around")
w.handle("work")
interp_before = dict(stub.calls)
w.handle("I'm a bandit and I'll rob you")
q = st.load_question()
check("a hostile answer is pressed once more, by the stage", q and q["data"]["stage"] == "proof" and q["data"]["pressed"] == 1 and q["speaker"] == U, q)
check("...and the interpreter never saw the line", not any(k in stub.calls and stub.calls[k] != interp_before.get(k, 0) for k in stub.calls if "Plan" in k or "Intent" in k), {k: v for k, v in stub.calls.items() if v != interp_before.get(k, 0)})
w.handle("fine, I'm new, I came for the guild work")
q = st.load_question()
check("a straight answer settles her, and she asks how new they are, under her name", q and q["data"]["stage"] == "know" and q["speaker"] == N and w.player.mentor.get("introduced"), q)
done("stages461_hostile")

# ---- a save closed on one of her questions asks it again, in her voice, when it opens; the answer carries the meeting on
g = simlib.campaign("stages461_reopen", location="parth", never_mentor=False, seed=5, minutes=1800)
w = g.scene
w.narrate = lambda e, t="": None
w.narrate_with = lambda *a, **k: None
w.show_exits = lambda *a, **k: None
SAID.clear()
w.mentor_intercept("I look around")
q = g.store.load_question()
check("her first question stands in the save, under what you can see of her", q and q["kind"] == "mentor" and q["data"]["stage"] == "first"
      and q["speaker"] == U and q["question"] == M["approach"]["ask_first"], q)
g.close()
g2 = simlib.campaign("stages461_reopen", fresh=False)
w2 = g2.scene
w2.narrate = lambda e, t="": None
w2.narrate_with = lambda *a, **k: None
w2.show_exits = lambda *a, **k: None
w2.mentor_escort = lambda: None
SAID.clear()
marks = []
script = ["I came for work", "quit"]


def scripted(*a, **k):
    marks.append(len(SAID))                                  # how much had been shown when the loop first asked for a line
    return script.pop(0) if script else "quit"


uc.ask = scripted
w2.run()
uc.ask = no_ask
shown_first = SAID[:marks[0]] if marks else []
check("a save opened on her question asks it again, once, in her voice, before the first line is taken",
      sum(1 for x in shown_first if x[:2] == ["say", U] and x[2] == M["approach"]["ask_first"]) == 1, shown_first)
q = g2.store.load_question()
check("...and the answer carries the meeting to her pointed question", q and q["data"]["stage"] == "proof", q)
g2.close()

# ---- the fence: a question read inside a turn is a fault the turn survives
uc.ask = lambda *a, **k: "typed"
with questions.fence():
    passes = uc.ask(main=True) == "typed"
    try:
        uc.ask()
        raised = False
    except questions.AskedInsideTurn:
        raised = True
check("inside the fence the loop's own ask passes and any other raises", passes and raised)
check("the fence is lifted after", uc.ask() == "typed")
st, w = fresh("stages461_fence")
w.mentor_intercept = lambda t: (uc.ask(), True)[1]          # a site slipping back to reading an answer inside the turn
stood = w.turn("I look around")
check("a turn that reads an answer inside itself is not taken, and says why in the log", stood is False and w.last_crash and "AskedInsideTurn" in w.last_failure, (stood, w.last_failure))
check("...and console.ask is put back afterwards", uc.ask() == "typed")
uc.ask = no_ask
done("stages461_fence")
src = Path("scenes/world.py").read_text(encoding="utf-8")
check("the fence stands over every turn, every #command, the arrival after one (f463) and the game's opening (f466)", src.count("questions.fence()") == 4, src.count("questions.fence()"))

# ---- the ratchet: no console.ask() inside a turn anywhere under scenes/ or engine/
left = {}
for f in sorted(list(Path("scenes").glob("*.py")) + list(Path("engine").glob("*.py"))):
    if f.name == "home.py":                                  # the save menu: a menu, not a turn
        continue
    n = len(re.findall(r"console\.ask\(\s*\)", f.read_text(encoding="utf-8")))
    if n:
        left[f.as_posix()] = n
check("no question is read inside a turn anywhere: the ratchet is zero", left == {}, left)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
