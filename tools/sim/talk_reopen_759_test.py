"""(f759) Who the acting character was with and speaking to when the game closed is there when the save is opened again, whoever that
is: a resident, someone here on their routine, a bound captive, someone who came looking, a hire. Found by the audit (world_py-2,
trace-replay-3): the saved talk was put back before anyone but the place's own people had joined those present, and the record of it
was dropped whether or not its speaker was found, so a talk with someone here on their routine came back as no talk at all and the
next line wrote the empty talk over the save; someone who came looking was not in the save at all; and the hire who spoke last lived
on the scene alone, so after a reopen an answer to a companion went to the reader as said to no one.

Now the talk is put back once everyone here is present, waits in the save until its speaker is found, gone, or walked away from; the
hire who spoke last is kept in the talk's row while a reply could still go to them, by the hire's id; and who came looking is a row of
its own while they are here, read as the scene is made.

The case that found it: a talk of four lines with someone here on their routine, closed and opened as main.py opens a save
(simlib.Game.reopen). Second cases of the kind: a bound captive; someone who came looking, at a place where no resident is about at
that hour, still here after the open and gone at their hour; a hire's words answered after the open, which go to the hire as they do
in the session played straight; a hire who spoke three lines ago holds no talk row; a speaker not about at the open, waited for in the
save until the character walks on; a speaker gone while the game was closed; and a hire spoken to while a talk waits for its speaker,
whose answer after the next open goes to the hire. (A captive walked along is filed among the place's people, so that case held
before this change too.)
Run: python tools/sim/talk_reopen_759_test.py"""
import contextlib
import io
import re
import shutil
import sys
import tempfile
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
held_stub = simlib.install(stub)
import config

LOGS = tempfile.mkdtemp(prefix="talk_reopen_")
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, f"{LOGS}/{fn}")
SHOWN = simlib.quiet_console()
from engine import mapview, routines
from storage import saves
from ui import console

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


CALLS: list = []                                         # (title, the reading's LAST SPOKE TO line) of every call
real = simlib.below()


def chat(**k):
    text = "\n".join(str(m.get("content", "")) for m in k["messages"])
    m = re.search(r"LAST SPOKE TO: [^\n]*", text)
    CALLS.append((k["format"].get("title"), m.group(0) if m else ""))
    return real.chat(**k)


spy = simlib.stand_in(chat=chat, embed=None)
console.put("status_block", lambda *a, **k: None)


def play(ws, line, plan):
    stub.plan = [dict(p) for p in plan]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ws.play(line)
    finally:
        stub.plan = None


def talk(ws, who, words):
    play(ws, f'I say, "{words}"', [{"kind": "talk", "target": who, "speech": words}])


def reopen(g):
    with contextlib.redirect_stdout(io.StringIO()):
        return g.reopen()                                 # closed, and opened as main.py opens a save: the scene's opening runs


def town_of(ws, pid):
    top = mapview.top_of(ws.world, pid)
    return [p for p, x in ws.world.places.items() if mapview.top_of(ws.world, p) == top and not x.danger]


def talk_kept(ws, who, lines):
    return ws.partner is not None and ws.partner.id == who and [tuple(x) for x in ws.convo] == [tuple(x) for x in lines]


# ---- the case that found it: a talk with someone here on their routine (f352)
NAME = "talk_reopen_routine"
g = simlib.campaign(NAME, seed=4, location="trading_square")
ws, store = g.scene, g.store
town = town_of(ws, "trading_square")
with contextlib.redirect_stdout(io.StringIO()):
    for pid in town:
        ws.enter(pid)
base = (store.meta.minutes // 1440) * 1440
pid, minute = next(((p, base + 1440 + h * 60) for h in range(24) for p in town
                    if routines.visitor_ids(store, ws.world, store.meta.seed, p, base + 1440 + h * 60, {})), (None, None))
store.meta.minutes = minute
store.save_meta()
ws.__dict__.pop("_routine_cache", None)
with contextlib.redirect_stdout(io.StringIO()):
    ws.enter(pid)
who = next((n.id for n in ws.present if n.id in ws._routine_here), None)
check("(someone is here on their routine, and the place's own people are about)", who and any(n.id not in ws._routine_here for n in ws.present),
      (pid, minute, [n.id for n in ws.present]))
talk(ws, who, "Good day to you.")
talk(ws, who, "What brings you here?")
lines, stance = list(ws.convo), getattr(ws, "stance", "")
check("(a talk of four lines with them, kept in the save)", len(lines) == 4 and (store.load_talk() or {}).get("speaker") == who, (len(lines), store.load_talk()))
ws = reopen(g)
store = g.store
check("opened again, the talk with someone here on their routine is as it was: who, its lines and their manner",
      talk_kept(ws, who, lines) and getattr(ws, "stance", "") == stance, (ws.partner and ws.partner.id, len(ws.convo), any(n.id == who for n in ws.present)))
play(ws, "I look around.", [{"kind": "look"}])
rec = store.load_talk() or {}
check("...and the next line keeps it in the save, never writes an empty talk over it",
      rec.get("speaker") == who and len(rec.get("lines") or []) == 4 and talk_kept(ws, who, lines), rec)
talk(ws, who, "And the roads?")
check("(the talk goes on, kept in the save)", (store.load_talk() or {}).get("speaker") == who, store.load_talk())
lines = [list(x) for x in ws.convo]

# ---- a speaker not about at the open: the talk waits for them, in the save too
store.arm(False)
away = store.load_npc(who)
away.away_until = ws.minutes + 60                         # between the two sessions: they have stepped off for a while
store.save_npc(away)
ws = reopen(g)
store = g.store
check("a speaker not about at the open: the talk waits for them, and is no talk with anyone else",
      ws.partner is None and not ws.convo and (ws.__dict__.get("_talk_saved") or {}).get("speaker") == who, (ws.partner, ws.__dict__.get("_talk_saved")))
play(ws, "I look around.", [{"kind": "look"}])
rec = store.load_talk() or {}
check("...and the save keeps it whole through the next line", rec.get("speaker") == who and rec.get("lines") == lines, rec)
on = next(p for p in town if p != ws.player.location)
play(ws, "I walk on.", [{"kind": "move", "destination": on}])
check("...until the character walks on: then nothing waits, and the save holds no talk with them",
      ws.player.location == on and not ws.__dict__.get("_talk_saved") and not (store.load_talk() or {}).get("speaker"),
      (ws.player.location, ws.__dict__.get("_talk_saved"), store.load_talk()))

# ---- a speaker gone while the game was closed: nothing waits for them, and the save holds no talk of them after the next line
who = sorted(n.id for n in ws.present)[0] if ws.present else None
talk(ws, who, "Good day to you.")
check("(a talk under way with someone else, kept in the save)", (store.load_talk() or {}).get("speaker") == who, store.load_talk())
store.arm(False)
gone = store.load_npc(who)
gone.gone = "left for the coast"                          # between the two sessions: as the save holds it at the next open
store.save_npc(gone)
ws = reopen(g)
store = g.store
play(ws, "I look around.", [{"kind": "look"}])
check("a speaker gone while the game was closed: no talk is put back, none waits, and the save holds none of them",
      ws.partner is None and not ws.__dict__.get("_talk_saved") and (store.load_talk() or {}).get("speaker", "") == "",
      (ws.partner, ws.__dict__.get("_talk_saved"), store.load_talk()))
g.close()
saves.drop(NAME)

# ---- a bound captive walked along
NAME = "talk_reopen_captive"
g = simlib.campaign(NAME, seed=3, location="guild_house")
ws, store = g.scene, g.store
with contextlib.redirect_stdout(io.StringIO()):
    ws.enter("guild_house")
    cap = ws.make_prisoner("Garrick Fell", "", tip=False, named=False, kind="bandit")
store.save_player(ws.player)
talk(ws, cap.id, "Who sent you?")
talk(ws, cap.id, "Answer me.")
lines = list(ws.convo)
ws = reopen(g)
check("a talk with a captive walking bound at the character's side is there again after the open", talk_kept(ws, cap.id, lines),
      (ws.partner and ws.partner.id, len(ws.convo)))
g.close()
saves.drop(NAME)

# ---- someone who came looking, where no resident is about at that hour
NAME = "talk_reopen_visitor"
g = simlib.campaign(NAME, seed=3, location="trading_square")
ws, store = g.scene, g.store
town = town_of(ws, "trading_square")
with contextlib.redirect_stdout(io.StringIO()):
    for p in town:
        ws.enter(p)
caller = next(n for n in ws.store.load_npcs(list(store.load_place("trading_square").residents)) if not n.gone)
base = (store.meta.minutes // 1440) * 1440
spot = None
for h in range(24):
    store.meta.minutes = base + 1440 + h * 60
    store.save_meta()
    for p in town:
        if p == caller.location:
            continue
        ws.__dict__.pop("_routine_cache", None)
        with contextlib.redirect_stdout(io.StringIO()):
            ws.enter(p)
        if not ws.present:
            spot = (p, store.meta.minutes)
            break
    if spot:
        break
check("(a place in town where no one is about at that hour)", spot is not None and not ws.present, spot)
ws.begin_line()
with ws.operation("world", "someone comes looking", world=True) as op:
    ws.visit(caller, ws.minutes + 120)
store.arm(False)
check("(they came looking, inside an operation that stood)", op.state == "committed" and any(n.id == caller.id for n in ws.present), op.state)
talk(ws, caller.id, "You were looking for me?")
talk(ws, caller.id, "Go on, then.")
lines = list(ws.convo)
ws = reopen(g)
store = g.store
check("someone who came looking is still here after the open", any(n.id == caller.id for n in ws.present), [n.id for n in ws.present])
check("...and the talk with them, where no resident is about, is as it was", talk_kept(ws, caller.id, lines), (ws.partner and ws.partner.id, len(ws.convo)))
play(ws, "I wait a while.", [{"kind": "wait", "wait_minutes": 150}])
check("...and they leave at their hour, and the talk with them ends",
      not any(n.id == caller.id for n in ws.present) and ws.partner is None, ([n.id for n in ws.present], ws.partner and ws.partner.id))
check("...and the save holds no one come looking once they have gone", not store._kv("visitors"), store._kv("visitors"))
g.close()
saves.drop(NAME)


# ---- a hire's words answered: straight, and with the game closed and opened between
def hired(name):
    g = simlib.campaign(name, seed=7, minutes=8 * 60 + 600 * 1440, turn=1, location="parth")
    ws = g.scene
    hall, was = ws.guild_place_id(), ws.player.location
    ws.player.location = hall
    try:
        pick = ws.party_roster()[0]
    finally:
        ws.player.location = was
    ws.player.character.coins += pick["fee"]
    with ws.store.transaction():
        ws.party_service.hire(pick, ws.player.character.level)
    with contextlib.redirect_stdout(io.StringIO()):
        ws.enter(ws.player.location)
    g.store.save_player(ws.player)
    return g, ws, next(m for m in ws.player.party if m.get("permanent"))


SAID = {"kind": "other", "summary": "says something to no one in particular"}
FOLLOW = "No, where are you from?"


def answered(reopened: bool):
    name = f"talk_reopen_hire_{int(reopened)}"
    g, ws, m = hired(name)
    play(ws, f"{m['name'].split()[0]}, how are your feet holding up?", [SAID])
    row = g.store.load_talk() or {}
    if reopened:
        ws = reopen(g)
    else:
        g.forget(owed=True)                               # (f751) straight: what an opening forgets, and what it still owes another feature
    CALLS.clear()
    play(ws, FOLLOW, [SAID])
    titles = list(CALLS)
    g.close()
    saves.drop(name)
    return m, row, titles


m, row, straight = answered(False)
check("played straight, an answer to the hire who spoke goes to them: the companion answers, nothing reads it as said to no one",
      any(t == "CompanionReply" for t, _ in straight) and not any(t == "ActionPlan" for t, _ in straight), straight)
check("the hire who spoke last is in the save's talk, by the hire's id, while a reply could still go to them",
      (row.get("hire") or {}).get("id") == str(m["id"]), row)
_, _, reopened = answered(True)
check("closed and opened between, the answer goes to the hire as it does straight", reopened == straight, (reopened, straight))
check("...never read as said to no one", not any(l == "LAST SPOKE TO: no one" for _, l in reopened), reopened)

# ---- a hire who spoke three lines ago holds no talk row
NAME = "talk_reopen_hire_old"
g, ws, m = hired(NAME)
rows = []
for line, plan in [(f"{m['name'].split()[0]}, how are your feet holding up?", [SAID])] + [("I look around.", [{"kind": "look"}])] * 3:
    play(ws, line, plan)
    rows.append(((g.store.load_talk() or {}).get("hire"), (ws.__dict__.get("_hire_last") or (None, -9))[1], g.store.meta.turn))
check("the hire is kept only while a reply could still go to them: a hire who spoke three lines ago holds no talk row",
      rows[0][0] and all(bool(h) == (t >= turn - 1) for h, t, turn in rows) and rows[-1][0] is None and g.store.load_talk() is None,
      (rows, g.store.load_talk()))
g.close()
saves.drop(NAME)

# ---- a hire spoken to while a talk waits for its speaker: the save keeps the hire beside the waiting talk
NAME = "talk_reopen_hire_wait"
g, ws, m = hired(NAME)
who = next((n.id for n in ws.present), None)
check("(someone here to talk with, beside the hire)", who is not None, [n.id for n in ws.present])
talk(ws, who, "Good day to you.")
g.store.arm(False)
away = g.store.load_npc(who)
away.away_until = ws.minutes + 120                        # between the two sessions: they have stepped off for a while
g.store.save_npc(away)
ws = reopen(g)
play(ws, f"{m['name'].split()[0]}, how are your feet holding up?", [SAID])
row = g.store.load_talk() or {}
check("a hire spoken to while a talk waits for its speaker: the save keeps the waiting talk and the hire both",
      bool(ws.__dict__.get("_talk_saved")) and row.get("speaker") == who and bool(row.get("lines")) and (row.get("hire") or {}).get("id") == str(m["id"]),
      (ws.__dict__.get("_talk_saved"), row))
ws = reopen(g)
CALLS.clear()
play(ws, FOLLOW, [SAID])
check("...and closed and opened between, the answer goes to the hire, never read as said to no one",
      any(t == "CompanionReply" for t, _ in CALLS) and not any(t == "ActionPlan" for t, _ in CALLS), list(CALLS))
g.close()
saves.drop(NAME)

spy()
held_stub()
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
shutil.rmtree(LOGS, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
