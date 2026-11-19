"""(f722) One ordered page. What a line shows came by two roads: an operation's lines were shown when it committed, and the one
passage of a line of several actions was written after all its steps. So a later step's line was read above the passage that told
an earlier step: on 16 November "You find a level patch of ground and make camp there." stood above the passage that walked to
the rise. Held here: the line's one passage has a place on the page, where its first event was asked for, as a single action's
passage has (f464); what is said after that place, by that step or a later one, waits behind it and is shown after it, in the
order it was said; the stand-in for a lost passage takes the passage's place; a passage told early by a later step (a talk tells
what came before it) keeps the same order; a step that told it and then failed leaves the page as if it never ran; what waits is
still owed by its operation until it is shown (f467). A line of one action reads as it did.
Run: python tools/sim/page_order_722_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import encounters
from llm.gateway import LLMError
from ui import console

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


shown = simlib.quiet_console()
g = simlib.campaign("page_722", seed=4, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
real_look, real_wait, real_narration = ws.on_look, ws.on_wait, stub.a_Narration
MARKS = ("A1", "A2", "B1", "B2", "R1", "N")
seen = {}


def page() -> list:
    """What the line showed of the marks, in order, a passage as P."""
    return ["P" if k == "narrate" and t != "N" else t for k, t in shown if k == "narrate" or t in MARKS]


def play(text, plan, look, wait):
    stub.plan = plan
    ws.on_look, ws.on_wait = look, wait
    del shown[:]
    try:
        return ws.turn(text)
    finally:
        ws.on_look, ws.on_wait = real_look, real_wait
        stub.plan = None


def step_a(intent, text):
    console.note("A1")
    ws.narrate("The player looks the square over.")
    console.note("A2")


def step_b(intent, text):
    seen["owed"] = set(store.unshown())
    console.note("B1")
    ws.narrate("The player waits by the well.")
    console.note("B2")


TWO = [{"kind": "look"}, {"kind": "wait"}]

# ---- a line of one action reads as it did
out = play("I look the square over.", [{"kind": "look"}], step_a, step_b)
check("a line of one action reads in the order it was said: its line, its passage, its line", out is True and page()[:3] == ["A1", "P", "A2"], page())

# ---- a line of two actions: the one passage has its place, and what was said after it waits behind it
out = play("I look the square over and wait by the well.", TWO, step_a, step_b)
check("a line of two actions reads what came before its passage, the passage, then each step's lines in order",
      out is True and page()[:5] == ["A1", "P", "A2", "B1", "B2"], page())
check("...each line shown once", all(page().count(m) == 1 for m in ("A1", "A2", "B1", "B2")), page())
check("...the first step's operation still owed its lines while they waited (f467), and nothing is owed once the line is read",
      len(seen.get("owed", ())) == 1 and not store.unshown() and not getattr(ws, "waiting", None), (seen.get("owed"), store.unshown()))

# ---- the stand-in for a lost passage takes the passage's place
def lost(u, k):
    if "THEN:" in u:
        raise RuntimeError("the passage could not be written")
    return real_narration(u, k)


stub.a_Narration = lost
out = play("I look the square over and wait by the well.", TWO, step_a, step_b)
stub.a_Narration = real_narration
p = page()
check("a line's passage that could not be written is stood in for at its place: what waited comes after the stand-in",
      ws.line_untold and p[0] == "A1" and p[1] == "P" and [m for m in p if m != "P"][:4] == ["A1", "A2", "B1", "B2"]
      and p.index("A2") > 1, (p, len(ws.line_untold)))
check("...and nothing is left owed or waiting", not store.unshown() and not getattr(ws, "waiting", None), store.unshown())

# ---- a later step that tells what came before it (as a talk does) keeps the order
def tells_first(intent, text):
    console.note("B1")
    ws.flush(text)
    console.note("B2")


out = play("I look the square over and wait by the well.", TWO, step_a, tells_first)
check("a later step that tells the earlier ones first reads the same way: the passage, the earlier step's lines, then its own",
      out is True and page()[:5] == ["A1", "P", "A2", "B1", "B2"] and not store.unshown(), page())

# ---- a step that told the passage and then failed leaves the page as if it never ran
def tells_then_fails(intent, text):
    console.note("B1")
    ws.flush(text)
    raise LLMError("the model failed")


out = play("I look the square over and wait by the well.", TWO, step_a, tells_then_fails)
p = page()
check("a step that told the passage and then did not stand shows nothing of itself: the passage is told once, after it the first step's line",
      out == "part" and p[:3] == ["A1", "P", "A2"] and "B1" not in p and p.count("A2") == 1 and not store.unshown() and not getattr(ws, "waiting", None), (out, p))

# ---- a refusal comes before anything it stops; one in a later step comes after what was done before it
def refuses(intent, text):
    console.note("R1")


out = play("I look the square over and wait by the well.", TWO, refuses, step_b)
check("a first step that only refuses is read at once, before the rest", page()[:4] == ["R1", "B1", "P", "B2"], page())
out = play("I look the square over and wait by the well.", TWO, step_a, refuses)
check("a later step that only refuses (or asks) is read after what was done before it: last", page()[:4] == ["A1", "P", "A2", "R1"], page())

# ---- a passage of its own asked for by a later step (the goddess's words) waits its turn too
def own_passage(intent, text):
    console.note("B1")
    ws.mark_passage("goddess", lambda: console.narrate("N"), None)
    console.note("B2")
    ws.time_note("T")


out = play("I look the square over and wait by the well.", TWO, step_a, own_passage)
texts = [t for k, t in shown]
check("a later step's own passage is told after the line's, at its place among that step's lines",
      out is True and [m for i, m in enumerate(page()) if m != "P" or i == page().index("P")][:6] == ["A1", "P", "A2", "B1", "N", "B2"]
      and not store.unshown() and not ws.passages, page())
check("...with nothing of the world's read between that step's lines and its passage (review Q36: the world's notes come after)",
      texts[texts.index("B1"):texts.index("B2") + 1] == ["B1", "N", "B2"] and "T" in texts[texts.index("B2"):], texts[texts.index("A2"):][:8])

# ---- the game closed between a step's commit and the passage: the next load tells what the step said (f467)
from core.interrupts import Interrupt
ws.crash_after_commit = "action:look"
try:
    play("I look the square over and wait by the well.", TWO, step_a, step_b)
    died = False
except Interrupt:
    died = True
owed = len(store.unshown())
del shown[:]
told = ws.recover_unshown()
check("a game closed after a step's commit and before the line's passage tells that step's lines at the next load, once",
      died and owed == 1 and told and [m for m in page() if m in ("A1", "A2")] == ["A1", "A2"] and not store.unshown(), (died, owed, page()))

# ---- the game closed after the passage stood and before it was read: each deed is told once, by the passage
from engine import ledger


def with_row(intent, text):
    ledger.add("arrived", facts={"who": "Marta", "what": "a tinker"}, say="Marta, a tinker, has come looking for the player.")
    step_a(intent, text)


ws.crash_after_commit = "passage"
try:
    play("I look the square over and wait by the well.", TWO, with_row, step_b)
    died = False
except Interrupt:
    died = True
owed = len(store.unshown())
del shown[:]
ws.recover_unshown()
texts = [t for k, t in shown]
check("a game closed after the line's passage stood, before it was read, tells each step's lines and the passage once at the next load,"
      " and stands in for no deed the passage tells", died and owed == 3 and all(texts.count(m) == 1 for m in ("A1", "A2", "B1", "B2"))
      and not any("Marta" in t for t in texts) and not store.unshown(), (died, owed, texts))
ws.crash_after_commit = "action:look"
try:
    play("I look the square over and wait by the well.", TWO, with_row, step_b)
except Interrupt:
    pass
del shown[:]
ws.recover_unshown()
check("...and one closed before the passage was written still reads the deed plainly, from its row", any("Marta" in t for k, t in shown) and not store.unshown(),
      [t for k, t in shown])

# ---- a line of several actions that was not taken leaves nothing set for the next input
def fails(intent, text):
    raise LLMError("the model failed")


out = play("I look the square over and wait by the well.", TWO, fails, step_b)
real_take = ws.take_line
ws.take_line = lambda text: (step_a(None, text), True)[1]
del shown[:]
taken = ws.turn("yes")
ws.take_line = real_take
check("after a line of several actions that was not taken, a line taken whole is told as any line of one action: its line, its passage, its line",
      out is False and taken is True and page()[:3] == ["A1", "P", "A2"] and ws.pending == [] and not any("Nothing comes of that" in t for k, t in shown),
      (out, taken, page(), ws.pending))
g.close()
shutil.rmtree("saves/page_722", ignore_errors=True)

# ---- the case that found it: a look and a night's camp in the wilds, in one line
shown = simlib.quiet_console()
g = simlib.campaign("page_722_camp", seed=4, location="parth")
ws, store = g.scene, g.store
wild = next(pid for pid, p in ws.world.places.items() if p.danger and p.type not in ("dungeon", "road") and not p.parent)
ws.enter(wild)
real_roll = encounters.roll
encounters.roll = lambda *a, **k: None
ws.player.character.health = 1
stub.plan = [{"kind": "look"}, {"kind": "wait", "wait_until": "morning", "summary": "sleep"}]
del shown[:]
out = ws.turn("We look the place over, make camp here and sleep until morning.")
encounters.roll = real_roll
stub.plan = None
kinds = [k for k, t in shown]
camp = next((i for i, (k, t) in enumerate(shown) if k == "note" and "camp" in t.lower()), None)
check("a look and a night's camp in one line: the camp is made after the passage that tells the look, not above it",
      out is True and camp is not None and "narrate" in kinds and kinds.index("narrate") < camp, (out, camp, [(k, t[:50]) for k, t in shown][:6]))
g.close()
shutil.rmtree("saves/page_722_camp", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
