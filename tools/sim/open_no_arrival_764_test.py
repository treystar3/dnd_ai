"""(f764) Opening a save puts the scene back and rolls nothing: an opening is not an arrival. Found by the audit (trace-replay-4):
the game's opening entered the place the character already stood in as if they had just walked in, so it did again what only an
arrival does. A period's moment was rolled at the open (data/rules/moments.yaml: the roll is made on arriving): a character who waited
in a town from one period into the next met no roll, while the same save closed and opened rolled the new period, and on a hit made
a model call and began a moment before a line was typed. The same entry picked a home's garden and served its hearth on a new day,
and the next line's door (engine/matters.py on_arrival) read the open as an arrival, so a situation's moment waiting in the town was
held back by the arrival's chance where a session played straight would have shown it.

Now the opening puts the scene back where the character has stood before (WorldScene.restore: the people from their rows, who is
present, a moment still on carried on and one that ended closed, the place's parts and the spot, the visit's marks fresh, and the door
told they are not arriving), and arrives only where they never have: a new game's first waking, a save set down where it was never
entered.

The case that found it: Parth (seed 4), waited in from the evening into the morning, closed and opened: no roll and no model call at
the open, as straight. Second cases of the kind: an inn whose roll would hit at the open; a moment on at the close carried on with its
visitor, and one that ended while the game was closed is closed with nothing rolled; one's own house, closed one day and opened the
next, picks no herbs and serves no meal; a guild hall's trial notice is not told again at an open on a new day; a situation's moment
waiting in the town is shown on the first line after the open as on the line straight; and two that still arrive: a new game's first
open, and a save set down where the character never entered.
Run: python tools/sim/open_no_arrival_764_test.py"""
import contextlib
import io
import random
import shutil
import sys
import tempfile
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
held_stub = simlib.install(stub)
import config

LOGS = tempfile.mkdtemp(prefix="open_no_arrival_")
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, f"{LOGS}/{fn}")
SHOWN = simlib.quiet_console()
from engine import clock, mapview, matters, moments, pulse
from storage import saves
from ui import console

console.put("status_block", lambda *a, **k: None)
console.put("combat_state", lambda *a, **k: False)
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def play(ws, line, plan):
    stub.plan = [dict(p) for p in plan]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ws.play(line)
    finally:
        stub.plan = None


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a)


def calls_since(before: dict) -> dict:
    return {t: n - before.get(t, 0) for t, n in stub.calls.items() if n - before.get(t, 0)}


def reopen(g):
    """Closed, and opened as main.py opens a save (the scene's opening run): the scene, the model calls and the lines it made."""
    before, shown = dict(stub.calls), len(SHOWN)
    ws = quiet(g.reopen)
    return ws, calls_since(before), [t for _, t in SHOWN[shown:]]


def key(ws) -> str:
    return f"{clock.day(ws.minutes)}:{clock.period(ws.minutes)}"


WAIT_MORNING = [{"kind": "wait", "wait_until": "morning"}]
LOOK = [{"kind": "look"}]


# ---- the case that found it: Parth, waited in from the evening into the morning
def parth(reopened: bool) -> dict:
    name = f"open_no_arrival_parth_{int(reopened)}"
    g = simlib.campaign(name, seed=4, location="parth")                   # day 1, the evening
    ws = g.scene
    quiet(ws.enter, "parth")                                              # the arrival: the evening's roll
    g.store.save_player(ws.player)
    out = {"arrived": g.store.load_place("parth").moment_roll}
    play(ws, "I wait until morning.", WAIT_MORNING)
    out["waited"], out["key"] = g.store.load_place("parth").moment_roll, key(ws)
    out["opened"] = {}
    if reopened:
        ws, out["opened"], _ = reopen(g)
    st = g.store.load_place("parth")
    out["at_open"], out["moment_at_open"] = st.moment_roll, dict(st.moment or {})
    before = dict(stub.calls)
    for _ in range(2):
        play(ws, "I look around.", LOOK)
    st = g.store.load_place("parth")
    out["after"], out["moment"], out["looked"] = st.moment_roll, dict(st.moment or {}), calls_since(before)
    g.close()
    saves.drop(name)
    return out


a, b = parth(False), parth(True)
check("(the arrival in Parth rolled the evening, and the wait ran into the next period)",
      a["arrived"] and a["arrived"].endswith(":evening") and a["key"] != a["arrived"], (a["arrived"], a["key"]))
check("played straight, waiting into the morning and looking around rolls nothing: the roll is the evening's, no moment is asked for",
      a["after"] == a["arrived"] and not a["moment"] and not a["looked"].get("MomentProposal"), (a["after"], a["moment"].get("id"), a["looked"]))
check("closed and opened in the morning, the opening rolls nothing: the save's roll is still the evening's",
      b["at_open"] == b["arrived"] == a["arrived"], (b["arrived"], b["at_open"]))
check("...makes no model call for a moment and begins none before a line is typed",
      not b["opened"].get("MomentProposal") and not b["moment_at_open"], (b["opened"], b["moment_at_open"].get("id")))
check("...and after the same two lines the place is as the session played straight left it",
      (b["after"], b["moment"]) == (a["after"], a["moment"]), ((b["after"], b["moment"].get("id")), (a["after"], a["moment"].get("id"))))


# ---- an inn whose roll would hit at the open
def inn_of(world, town="parth") -> str:
    return next(pid for pid, p in sorted(world.places.items()) if p.type == "inn" and mapview.top_of(world, pid) == town)


chance = dict(moments.M["chance"])
NAME = "open_no_arrival_inn"
g = simlib.campaign(NAME, seed=7, location="parth", minutes=360)          # day 1, the afternoon
ws = g.scene
inn = inn_of(ws.world)
moments.M["chance"]["inn"] = 0.0
quiet(ws.enter, "parth")
quiet(ws.enter, inn)                                                      # the afternoon's roll, a miss
g.store.save_player(ws.player)
moments.M["chance"]["inn"] = 1.0                                          # from here every roll made at the inn hits
rolled = g.store.load_place(inn).moment_roll
play(ws, "I wait a while.", [{"kind": "wait", "wait_minutes": 240}])
check("(at the inn, rolled in the afternoon, waited into the evening with people about)",
      rolled.endswith(":afternoon") and key(ws).endswith(":evening") and len(ws.present) >= 2, (rolled, key(ws), len(ws.present)))
check("...where staying put rolls nothing", g.store.load_place(inn).moment_roll == rolled and not g.store.load_place(inn).moment,
      g.store.load_place(inn).moment_roll)
ws, opened, _ = reopen(g)
st = g.store.load_place(inn)
check("an inn closed and opened in the next period: nothing rolled, no moment asked for and none begun, though any roll would hit",
      st.moment_roll == rolled and not st.moment and not opened.get("MomentProposal"), (st.moment_roll, (st.moment or {}).get("id"), opened))

# ---- a moment on at the close carries on, with its visitor in the room; one that ended while the game was closed is closed
spec = next(s for s in moments.M["shapes"] if s["id"] == "performer")
m = quiet(moments.start, ws, spec, random.Random(1))
g.store.save_player(ws.player)
check("(a performer is on at the inn, with a visitor from the road)", m.get("visitor") and any(n.id == m["visitor"] for n in ws.present), m)
g.store.arm(False)
row = g.store.load_place(inn)
row.residents = [i for i in row.residents if i != m["visitor"]]          # the visitor comes back by the moment carried on, not by the row
g.store.save_place(row)
ws, opened, _ = reopen(g)
st = g.store.load_place(inn)
check("a moment on at the close is still on after the open, the same one, its visitor in the room, nothing asked for",
      (st.moment or {}).get("since") == m["since"] and any(n.id == m["visitor"] for n in ws.present) and not opened.get("MomentProposal")
      and st.moment_roll == rolled, ((st.moment or {}).get("since"), [n.id for n in ws.present], opened, st.moment_roll))
g.store.arm(False)
g.store.meta.minutes = m["until"] + 30                                   # between the two sessions: its minutes run out
g.store.save_meta()
ws, opened, _ = reopen(g)
st = g.store.load_place(inn)
check("one that ended while the game was closed is closed at the open, its visitor gone from the room",
      not st.moment and not any(n.id == m["visitor"] for n in ws.present), ((st.moment or {}).get("id"), [n.id for n in ws.present]))
check("...and nothing is rolled for the new period", st.moment_roll == rolled and not opened.get("MomentProposal"), (st.moment_roll, key(ws), opened))
g.close()
saves.drop(NAME)
moments.M["chance"].update(chance)

# ---- one's own house, closed one day and opened the next
NAME = "open_no_arrival_home"
g = simlib.campaign(NAME, seed=3, location="parth")
ws = g.scene
ws.player.homes["parth"] = {"day": 1, "upgrades": ["garden", "hearth"], "last_garden": -1, "last_hearth": -1}
ws.ensure_homes()
quiet(ws.enter, "parth")
del SHOWN[:]
quiet(ws.enter, "home_parth")                                             # the arrival: the garden and the hearth of day 1
g.store.save_player(ws.player)
h = ws.player.homes["parth"]
check("(walking into the house on day 1 picks the garden and serves the hearth)",
      h["last_garden"] == h["last_hearth"] == clock.day(ws.minutes) and any(t.startswith("From the garden") for _, t in SHOWN), (h, SHOWN[-3:]))
play(ws, "I sleep until morning.", WAIT_MORNING)
h = g.store.load_player().homes["parth"]
check("(slept there into day 2, where staying picks nothing)", clock.day(ws.minutes) == 2 and h["last_garden"] == h["last_hearth"] == 1, h)
ws, opened, said = reopen(g)
h = g.store.load_player().homes["parth"]
check("closed on day 1 and opened on day 2 in one's own house: no herbs picked and no meal served at the open",
      h["last_garden"] == h["last_hearth"] == 1 and not [t for t in said if t.startswith(("From the garden", "A hot meal"))],
      (h, [t for t in said if t.startswith(("From the garden", "A hot meal"))]))
g.close()
saves.drop(NAME)

# ---- the guild hall, a rank earned on paper: its trial is told on walking in, once a day, and an open on a new day tells it no more
NAME = "open_no_arrival_hall"
TRIAL = "To hold it you must win a trial"
g = simlib.campaign(NAME, seed=3, location="parth")
ws = g.scene
hall = next(pid for pid, p in sorted(ws.world.places.items()) if p.type == "guild" and mapview.top_of(ws.world, pid) == "parth")
ws.player.guild_rank, ws.player.guild_done, ws.player.character.level = "F", {"F": 5}, 10
quiet(ws.enter, "parth")
del SHOWN[:]
quiet(ws.enter, hall)                                                     # the arrival: the trial told on day 1
g.store.save_player(ws.player)
check("(walking into the guild hall with a rank earned on paper tells the trial)", any(TRIAL in t for _, t in SHOWN), SHOWN[-3:])
play(ws, "I wait until morning.", WAIT_MORNING)
ws, opened, said = reopen(g)
check("closed on day 1 and opened in the hall on day 2: the trial is not told again at the open",
      clock.day(ws.minutes) == 2 and not [t for t in said if TRIAL in t], (clock.day(ws.minutes), [t for t in said if TRIAL in t]))
g.close()
saves.drop(NAME)


# ---- a situation's moment waiting in the town: the next line's door reads no arrival after the open, as straight
def door(reopened: bool) -> str:
    name = f"open_no_arrival_door_{int(reopened)}"
    g = simlib.campaign(name, seed=3, location="trading_square")
    ws, store = g.scene, g.store
    quiet(ws.enter, "trading_square")
    store.save_player(ws.player)
    play(ws, "I look around.", LOOK)
    store.arm(False)
    state = store.load_world_state() or pulse.empty_state(ws.minutes)
    th = {"id": "m_door", "title": "The market at Parth", "tier": "uncommon", "place": "parth", "status": "active", "stage": 0,
          "stages": [{"description": "Stalls stand empty and prices climb.", "effects": []}], "times": [ws.minutes, ws.minutes + 9000],
          "groups": ["everyone"], "paths": [], "door": "scene", "summons": "", "moment": "pending", "sender": "",
          "clues": [{"text": "The grain carts were turned back at the gate.", "holder": "", "npc": "", "found": False}]}
    state["threads"] = [t for t in state.get("threads", []) if t["id"] != th["id"]] + [th]
    state["door_log"] = {}
    store.save_world_state(state)
    if reopened:
        ws, _, _ = reopen(g)
        store = g.store
    play(ws, "I look around.", LOOK)
    out = next(t for t in store.load_world_state()["threads"] if t["id"] == "m_door").get("moment")
    g.close()
    saves.drop(name)
    return out


once = dict(matters.D["scene"])
matters.D["scene"]["on_enter_chance"] = 0.0                               # an arrival never meets it: only a line where they stand
straight, opened_door = door(False), door(True)
matters.D["scene"].update(once)
check("(played straight, a situation's moment waiting in the town is shown on the next line where they stand)", straight == "shown", straight)
check("closed and opened, the first line after the open is no arrival either: the moment is shown as straight", opened_door == straight,
      (opened_door, straight))

# ---- two that still arrive: a new game's first open, and a save set down where the character never entered
NAME = "open_no_arrival_new"
g = simlib.campaign(NAME, seed=4, location="parth", turn=0)              # a new game: placed at its waking, never entered
ws, opened, _ = reopen(g)
check("a new game's first open still arrives: the place is entered, its period rolled, the first sight told",
      "parth" in ws.player.visited and g.store.load_place("parth").moment_roll == key(ws) and opened.get("Narration"),
      (ws.player.visited, g.store.load_place("parth").moment_roll, key(ws), opened))
g.close()
saves.drop(NAME)

NAME = "open_no_arrival_set_down"
g = simlib.campaign(NAME, seed=4, location="parth", turn=5)               # a recording script's save: placed, never entered
ws, opened, _ = reopen(g)
check("a save set down where the character never entered still arrives: entered, its period rolled",
      "parth" in ws.player.visited and g.store.load_place("parth").moment_roll == key(ws),
      (ws.player.visited, g.store.load_place("parth").moment_roll, key(ws)))
g.close()
saves.drop(NAME)

held_stub()
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
shutil.rmtree(LOGS, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
