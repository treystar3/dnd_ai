"""(f711) What the world does after a long walk is told, or waits until it can be (the owner, 2026-11-16:
docs/design/23_untold_after_walks.md; found in the third blind play: docs/play/2026-11-16_blind_play_journal.md). A 288 minute walk
to Ironvein spent the turn; a matter then sent Norvald Balarakk to find the player anyway, his passage was refused for the budget, and
the player read "The thing is settled. No passage came, and none is needed for it to be so." The summons was spent ("met") and nobody
was ever seen to come.
Held here: a summons or a moment on a turn that cannot pay for its passage does not happen yet (still pending, nobody placed) and
happens on a later turn in that town; a summons keeps a plain fact (who came, by name and trade) told if its passage is lost, a moment
a plain line that something happened here; the stand-in lines never speak of the telling, the words or the story, nor promise more;
after a won road fight on a spent turn the walk waits at the stop with the way on named, and with the turn's budget left it walks on.
Run: python tools/sim/untold_moment_711_test.py"""
import re
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
import ui.console as uc
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(str(m)))
from engine import budget, failures, ledger, matters, pulse, retrieval

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("untold_711", seed=5, location="trading_square")
ws, store, world = g.scene, g.store, g.scene.world
for p in ("trading_square", "watch_tower", "guild_house", "tilted_plough", "trading_square"):
    ws.enter(p)
if not store.load_world_state():
    store.save_world_state(pulse.empty_state(ws.minutes))
told = []
ws._narrate_now = lambda event, player_text="": told.append(event)
ws.player.reputation["parth"] = 40


def matter(tid, **kw):
    th = {"id": tid, "title": "The market at Parth", "tier": "uncommon", "place": "parth", "status": "active", "stage": 0,
          "stages": [{"description": "Stalls stand empty and prices climb.", "effects": []}], "times": [ws.minutes, ws.minutes + 9000],
          "groups": ["everyone"], "paths": [], "door": "summons", "summons": "", "moment": "", "summons_force": True, "sender": "",
          "clues": [{"text": "The grain carts were turned back at the gate.", "holder": "", "npc": "", "found": False}], **kw}
    state = store.load_world_state()
    state["threads"] = [t for t in state.get("threads", []) if t["id"] != tid] + [th]
    state["door_log"] = {}
    store.save_world_state(state)


def th_of(tid):
    return next(t for t in store.load_world_state()["threads"] if t["id"] == tid)


def turn(spent: bool):
    b = budget.open()
    if spent:
        b.spent = b.limit
    ws._door_loc = ws.player.location
    told.clear()
    ws.arrival()
    budget.close()


matter("m1", summons="pending")
turn(spent=True)
t = th_of("m1")
check("a summons on a turn that cannot pay for its passage does not happen yet: still pending, nobody sent, nothing told",
      t["summons"] == "pending" and not t.get("sender") and not told, (t["summons"], t.get("sender"), told[:1]))
turn(spent=False)
t = th_of("m1")
sender = store.load_npc(t["sender"]) if t.get("sender") else None
check("...and on a later turn in that town it happens, told, with the one sent here", t["summons"] == "met" and sender is not None
      and told and any(n.id == sender.id for n in ws.present), (t["summons"], told[:1]))
rows = [r for r in ledger.this_turn() if r["kind"] == "arrived"]
known = sender.label(ws.acting) if sender else ""
check("...keeping a plain fact of who came, as the player knows them (a name not yet learned stays unsaid), the trade only beside a name",
      rows and rows[-1]["facts"].get("who") == known and ("what" in rows[-1]["facts"]) == (known == sender.name)
      and (sender.name == known or sender.name not in str(rows[-1]["facts"])), rows[-1:] if rows else rows)
line = failures.stood_lines(rows[-1:])[0] if rows else ""
check("...which, its passage lost, is what the player reads: who came, never a deed line", known and known in line
      and line not in failures.F["stood_any"] and not line[:1].islower(), line)
check("every line for someone come looking reads whole with only who they are, or with who and trade",
      all(failures._placeholders(l) in ({"who"}, {"who", "what"}) for l in failures.F["stood"]["arrived"])
      and sum(failures._placeholders(l) == {"who"} for l in failures.F["stood"]["arrived"]) >= 3)

said = ledger.told()
check("...a fact the passage is given, and once told it is no stand-in of a later lost passage",
      any(sender.label(ws.acting) in x for x in said) and not [r for r in ledger.this_turn() if r["kind"] == "arrived" and not r.get("told")], said)

matter("m2", door="scene", moment="pending", summons="")
turn(spent=True)
check("a moment on a spent turn waits the same way", th_of("m2")["moment"] == "pending" and not told, (th_of("m2")["moment"], told[:1]))
turn(spent=False)
check("...and plays on a later turn there", th_of("m2")["moment"] == "shown", th_of("m2")["moment"])
rows = [r for r in ledger.this_turn() if r["kind"] == "happened"]
line = failures.stood_lines(rows[-1:])[0] if rows else ""
check("...keeping a plain line that something happened here, told if its passage is lost", rows and line in failures.F["stood"]["happened"], (rows[-1:], line))

STORY = re.compile(r"\b(telling|told|words|story|untold|unsaid|passage|wait for|settled|remembers)\b", re.I)
for key in ("stood_any",):
    off = [l for l in failures.F[key] if STORY.search(l)]
    check(f"no {key} line speaks of the telling, the words or the story, or claims what it cannot know", not off, off)
for kind in ("arrived", "happened"):
    off = [l for l in failures.F["stood"][kind] if STORY.search(l)]
    check(f"...nor any stood.{kind} line", not off, off)

WON = {"resume": "ironvein", "text": "We walk on.", "won": True}        # (f758) the saved road: where a won fight's walk goes on to
ws.player.road = dict(WON)
moved = []
real_move = ws.on_move
ws.on_move = lambda intent, text: moved.append(intent.destination)
b = budget.open(); b.spent = b.limit
NOTES.clear()
ws.resume_road()
budget.close()
check("after a won road fight on a spent turn the walk waits, the way on named, and nothing is pending",
      not moved and not ws.walk_due() and any(world.places["ironvein"].name in n for n in NOTES), (moved, NOTES))
ws.player.road = dict(WON)
b = budget.open()
ws.resume_road()
budget.close()
check("...and with the turn's budget left it walks on, as before", moved == ["ironvein"], moved)
ws.on_move = real_move
ws.player.road = None
g.close()
shutil.rmtree("saves/untold_711", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
