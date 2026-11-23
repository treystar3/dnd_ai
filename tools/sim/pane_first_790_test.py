"""(f790) The engine's outcome is shown first: when a fight's round is decided, the window's fight pane shows its new state (health,
statuses, who is down) at once, and the round's telling follows when it is written. Before this, the pane's update was held behind the
round's passage (scenes/world.py release), so nothing on the page moved until the narration came back, 4 to 15 seconds on the
owner's card and longer on the minimum one.
The case that found it: a round struck at a wolf that stands. Second cases of the kind: the round that wins the fight (its last state
first, the pane's close after the telling, so the pane never ends before the blow is told); words spoken in a fight (the talk path,
which tells and shows through its own branch); a line of two actions (the line's one passage, f722); a telling that cannot be
written (its stand-in, the pane still first); and the terminal, whose text panel is a line of the page and keeps its place after
the telling.
Run: python tools/sim/pane_first_790_test.py"""
import io
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 5)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import config
import ui.console as uc
ORDER = []                                                # what reached the page, in order: ("pane", open?) and ("told", text)
uc.channel().windowed = True                              # the window: the pane is drawn from its data, and the text panel is not printed


def pane(data):
    ORDER.append(("pane", data is not None))
    return uc.channel().windowed


uc.put("status_block", lambda *a, **k: None)
uc.put("combat_state", pane)
uc.put("combat_panel", lambda lines: ORDER.append(("panel", True)))
uc.put("narrate", lambda *a, **k: ORDER.append(("told", str(a[0]) if a else "")))
LOGS = simlib.saves_path("pane_first_logs")
LOGS.mkdir(parents=True, exist_ok=True)
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, str(LOGS / fn))
from engine import combat, leveling
from scenes.combat_scene import CombatScene
sys.stdout = io.StringIO()                                # the stand-in's own prints

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NOW = {}
INTENT = {"kind": "attack"}
asked_real = stub.a_Narration
stub.a_Narration = lambda u, k: (ORDER.append(("asked", True)), asked_real(u, k))[1]     # the narrator asked for the telling
stub.a_CombatIntent = lambda u, k: {**INTENT, "target": next((e.id for e in NOW["ws"].combat.fight.enemies()), "")}


def fresh(name: str, seed: int):
    g = simlib.campaign(name, seed=seed, location="greywood", minutes=420)
    ws = g.scene
    leveling.level_up(ws.player.character, 5)
    ws.enter("greywood")
    g.store.save_player(ws.player)
    NOW["ws"] = ws
    return g, ws


def wolves(ws, hp: list[int], kind: str = "wolf") -> None:
    beast = ws.world.bestiary[kind]
    ws.combat = CombatScene.begin(ws, beast, [combat.fighter_from_creature(beast, 2, "normal", f"e{i + 1}", f"{kind} {i + 1}", "near")
                                              for i in range(len(hp))], "In the trees,")
    for i, h in enumerate(hp):
        ws.combat.fight.get(f"e{i + 1}").hp = h
    ws.store.save_combat(ws.combat.to_json())


def played(ws, line: str) -> list:
    ORDER.clear()
    ws.play(line)
    return list(ORDER)


def first(seq, kind, open_=None) -> int:
    return next((i for i, (k, v) in enumerate(seq) if k == kind and (open_ is None or v == open_)), -1)


def last(seq, kind, open_=None) -> int:
    hits = [i for i, (k, v) in enumerate(seq) if k == kind and (open_ is None or v == open_)]
    return hits[-1] if hits else -1


# ---- the case that found it: a round at a wolf that stands
g, ws = fresh("pane_first", 5)
wolves(ws, [400, 400])
seq = played(ws, "I strike at the wolf.")
told = first(seq, "told")
check("a round is told", told >= 0, seq)
check("...and the pane's new state reaches the page before the telling", 0 <= first(seq, "pane", True) < told, seq)
check("...before the narrator is even asked for it: the wait is for the words only", 0 <= first(seq, "pane", True) < first(seq, "asked"), seq)
state = ws.combat.fight.get("e1").hp if ws.combat else None
check("...the round's state, not the one before it (the wolf's health in the pane is the fight's now)",
      state is not None and state < 400, state)

# ---- second case: the round that wins the fight
wolves(ws, [1])
seq = played(ws, "I strike at the wolf.")
told = first(seq, "told")
check("the winning round: its last state first", 0 <= first(seq, "pane", True) < told, seq)
check("...and the pane's close after the blow is told, never before it", last(seq, "pane", False) > told, seq)
check("...the fight is over", ws.combat is None)

# ---- second case: words spoken in a fight (the talk path), to someone who can be spoken to
wolves(ws, [400], "thug")
INTENT.clear(); INTENT.update(kind="talk", approach="intimidate")
seq = played(ws, '"Back off, or I\'ll gut you."')
if first(seq, "told") >= 0 and first(seq, "pane", True) >= 0:
    check("words in a fight: the pane first, then the telling", first(seq, "pane", True) < first(seq, "told"), seq)
else:
    check("words in a fight are told and the pane shown", False, (seq, SHOWN[-4:]))
INTENT.clear(); INTENT.update(kind="attack")
wolves(ws, [400, 400])

# ---- second case: two verbs in a fight's line (read as one round)
seq = played(ws, "I shout at it and strike at the wolf.")
told = first(seq, "told")
check("two verbs in a fight's line: the pane before the round's telling", 0 <= first(seq, "pane", True) < told, seq)

# ---- second case: a line of several actions (its one passage, f722), at release itself: each operation of the line
from scenes.world import WorldScene
import types


def line_scene():
    out = []
    sc = types.SimpleNamespace(waiting=[], passages=[], FIRST=WorldScene.FIRST, REVEAL=WorldScene.REVEAL,
                               show=lambda calls: out.extend(n for n, a, k in calls))
    return sc, out


def op_of(*held):
    return types.SimpleNamespace(held=[("marker", (["line", None, None, [], 1],), {})] + list(held))


sc, out = line_scene()
WorldScene.release(sc, op_of(("note", ("a line",), {}), ("combat_state", ({"round": 1},), {})))
check("a line of several actions: a pane state behind the line's passage is shown at the commit, the note waits",
      out == ["combat_state"] and [n for n, a, k in sc.waiting[0][3]] == ["note"], (out, sc.waiting))
sc, out = line_scene()
WorldScene.release(sc, op_of(("combat_state", ({"round": 3},), {}), ("combat_state", (None,), {})))     # the first action wins a fight
WorldScene.release(sc, op_of(("combat_state", ({"round": 1},), {})))                                    # a later one starts another
check("...a fight won by one action and another begun by a later one: the new pane waits behind the old one's close, "
      "so the close never ends the new fight's pane", out == ["combat_state"]
      and [n for e in sc.waiting for n, a, k in e[3]] == ["combat_state", "combat_state"], (out, sc.waiting))

# ---- second case: a telling that cannot be written (its stand-in), the pane still first
real = stub.a_Narration
stub.a_Narration = lambda u, k: (_ for _ in ()).throw(RuntimeError("the narrator is down"))
seq = played(ws, "I strike at the wolf.")
stub.a_Narration = real
told = first(seq, "told")
check("a telling that cannot be written: the stand-in is told", told >= 0, seq)
check("...and the pane came first all the same", 0 <= first(seq, "pane", True) < told, seq)

# ---- the terminal: its text panel is a line of the page and keeps its place after the telling
uc.channel().windowed = False
if ws.combat is None:
    wolves(ws, [400])
seq = played(ws, "I strike at the wolf.")
told = first(seq, "told")
check("the terminal: the text panel follows the telling, as before", 0 <= told < first(seq, "panel"), seq)

# ---- the owner's reveal (2026-11-21, "Yes, keep the reveal"): a fight's opening is told before its pane shows the foes
def marked(kind, *held):
    return types.SimpleNamespace(held=[("marker", ([kind, None, None, [], 1],), {})] + list(held))


sc, out = line_scene()
WorldScene.release(sc, types.SimpleNamespace(held=[("marker", (["opening", None, None, [], 1],), {}), ("combat_state", ({"round": 0},), {}),
                                                    ("marker", (["round", None, None, [], 1],), {}), ("combat_state", ({"round": 1},), {})]))
check("a fight's opening: its first pane waits behind the opening's telling, and a round's pane after it waits with it", out == [], out)
sc, out = line_scene()
WorldScene.release(sc, marked("round", ("combat_state", ({"round": 2},), {})))
check("...while a round's pane behind a round's telling goes first", out == ["combat_state"], out)
sc, out = line_scene()
WorldScene.release(sc, marked("line", ("note", ("x",), {})))
sc.waiting[0][3].append(("combat_state", ({"round": 0},), {}))                 # a pane already waiting behind the line's passage
WorldScene.release(sc, marked("line", ("combat_state", ({"round": 1},), {})))
check("...and a later operation's pane waits behind one already waiting, so the page keeps their order", out == [], out)

g.close() if hasattr(g, "close") else None
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
