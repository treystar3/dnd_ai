"""(f692) A quiet line is no answer to what the player typed (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). At Ironvein, `I take the pegasus bounty and the gargoyle bounty.` took both contracts
and showed only "Heard of: the Ironcrown Peaks (on your map)": the quiet map line counted as the turn's answer, so the deed itself
(f416: a contract taken with no words from the clerk is told in the world) was never told. Any line of the turn's tail does the same
(a change in the room, a companion's aside, the mentor).
Held here: a deed whose only telling is a passage (a ledger row added passage_only: a contract taken at the board) and that no passage told is told
at the turn's end whatever quiet lines showed; the heard-of line still shows; a turn that did nothing and only heard of a place still
says nothing came of it; a deed already told is not told again, and a refusal, which shows its own reason, is not narrated for it.
Run: python tools/sim/heard_not_answer_692_test.py"""
import shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 6))
simlib.quiet_console()
import ui.console as uc
NOTES, LEDGER = [], []
uc.put("note", lambda m, *a, **k: NOTES.append(str(m)))
uc.put("ledger", lambda m, *a, **k: LEDGER.append(str(m)))
from engine import ledger
from llm.contracts import ActionIntent as A, Narration
import scenes.world as W

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


NAME = "heard_not_answer_692"
g = simlib.campaign(NAME, seed=6, location="parth")
ws = g.scene
ws.player.mentor["never"] = True
ws.enter("parth")
asked = []
real_fresh = W.fresh
W.fresh = lambda task, system, request, *a, **k: (asked.append((task, request)), Narration(text="The clerk writes your name down.")
                                                   if task == "narrate" else real_fresh(task, system, request, *a, **k))[1]
ws.audit_plan = lambda text, plan, raw=None: plan
PLAN = []
ws.interpret = lambda text, hint="": [a.model_copy(deep=True) for a in PLAN]
far = next(p for p in ws.world.places.values() if not p.parent and p.id != "parth")
real_stay = ws.stay_tick


def taking(intent, text):                                  # a contract taken whose posting names a place not yet heard of
    ledger.add("took", passage_only=True, say="The player has taken the contract 'Bounty: the gargoyle' at the board; the clerk records it.")
    ws.__dict__.setdefault("_heard_now", []).append(far.name)


def board_only(intent, text):                              # a contract taken, the room changing as it is
    ledger.add("took", passage_only=True, say="The player has taken the contract 'Wolves at the mill' at the board; the clerk records it.")


def request(intent, text):                                 # a person's request taken: its own line shows it (guild_actions)
    ledger.add("took", say="The player has taken on Colmer's request, 'Wolves at the mill'. It is theirs now.")
    uc.ledger("Request taken: [F] Wolves at the mill (for Colmer).")


def hearing_only(intent, text):
    ws.__dict__.setdefault("_heard_now", []).append(far.name)


def refused(intent, text):
    ws.refuse("That posting is not on this board.")
    ws.__dict__.setdefault("_heard_now", []).append(far.name)


def turn(text, handler, stay=None):
    ws.on_accept_quest = handler
    ws.stay_tick = stay or real_stay
    PLAN[:] = [A(kind="accept_quest", item="the bounty")]
    asked.clear(); NOTES.clear(); LEDGER.clear()
    ws.turn(text)
    return [r for t, r in asked if t == "narrate"]


told = turn("I take the gargoyle bounty.", taking)
check("a contract taken while a place is first heard of is told, in the world", len(told) == 1 and "gargoyle" in told[0], (told, NOTES, LEDGER))
check("...and the place heard of still shows", any(far.name in l and "Heard of" in l for l in LEDGER), LEDGER)
check("...with no 'Nothing comes of that'", not any("Nothing comes of that" in n for n in NOTES), NOTES)
told = turn("I take the mill contract.", board_only, stay=lambda: uc.note("A cart rattles past the window."))
check("another quiet line, a change in the room, hides no contract taken either", len(told) == 1 and "Wolves at the mill" in told[0], (told, NOTES))
told = turn("I'll take on your request, Colmer.", request, stay=lambda: uc.note("A cart rattles past the window."))
check("a request taken shows its own line, and no passage is added for it", not told, told)
told = turn("I take the gargoyle bounty.", hearing_only)
check("a turn that only heard of a place still says nothing came of it", not told and any("Nothing comes of that" in n for n in NOTES), (told, NOTES))
check("...and shows the place heard of", any(far.name in l for l in LEDGER), LEDGER)
told = turn("I take the wyvern bounty.", refused)
check("a refusal shows its own reason and is not narrated for it", not told and any("not on this board" in n for n in NOTES), (told, NOTES))


def told_already(intent, text):
    ledger.add("took", passage_only=True, say="The player has taken the contract 'Bounty: the gargoyle'.")
    ws.narrate("The player takes the gargoyle bounty.", text)


told = turn("I take the gargoyle bounty.", told_already)
check("a deed a passage already told is not told again", len(told) == 1, told)

ws.stay_tick = real_stay
g.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
