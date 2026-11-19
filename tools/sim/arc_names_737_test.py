"""(f737) The plain arc story names its people from the name builder, apart from every name in the save, so taking an arc never
fails for want of a name (found by the audit, scenes1-3 and aged-save-6: the plain story drew its people's names from the sixteen
captive names of data/rules/arcs.yaml less those already in the save, and a long save that held all sixteen divided by zero, so a
missing-person contract could not be taken on any turn its story call was deferred, dropped or failed its check, and redress_arc
raised the same way). Each person step of a plain story is named by npc/names.pick for the step's own people, apart from the save's
names and from each other, on the arc's own dice; a site step keeps no name; the save's names are read once. Cases: the save holding
all sixteen names (the accept with the story deferred, typed as a line too, and redress_arc's tail); the model's story failing its
check; a save with twenty captives taken over twenty fights; steps of other peoples; the same arc named the same.
Run: python tools/sim/arc_names_737_test.py"""
import shutil
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import config
from engine import arcs, budget, clock, failures, quests, streams
from engine.arcs import A
from llm.contracts import ActionIntent
from npc import names
from npc.models import NPC
from scenes import combat_scene

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


LIST = ["Dorn", "Kell", "Marek", "Sorin", "Vask", "Tobren", "Hale", "Garrick", "Brannoc", "Ferrow", "Jessk", "Orlen", "Ruddick", "Skarn",
        "Teague", "Wynn"]                                         # (f746) the old captive list, gone from arcs.yaml
_roll_scale = arcs.roll_scale
arcs.roll_scale = lambda *a, **k: ("arc", "forced")            # the longest trail: contacts, a lair or site, the boss
TID = next(t for t, tpl in arcs.TEMPLATES.items() if tpl["subject_kind"] == "person")


def working_hours(ws):
    while not all(clock.in_hours(ws.store.meta.minutes + h, (9, 18)) for h in (0, 120, 240)):
        ws.store.meta.minutes += 30


def full_budget():
    """A turn's budget with no room left for an optional call: the arc's story is deferred, as on the minimum card's priced turn."""
    return budget.open(limit=0, margin=0, floor=0, reserve=0)


def post(ws):
    """A missing-person contract alone on the hall's board; the character there in working hours, holding no contract and no arc."""
    c = ws.player.character
    c.level, ws.combat, ws.player.guild_rank = 20, None, "D"
    ws.store.save_arcs({"arcs": [], "last_end": -10 ** 9})
    ws.player.quests = []
    ws.store.meta.minutes += 1440
    working_hours(ws)
    ws.enter("guild_house")
    ws.ensure_board()
    tpl = arcs.TEMPLATES[TID]
    q = quests._quest("missing", "D", tpl["board"].format(subject=tpl["victims"][0], place="X"), ws.minutes, victim=tpl["victims"][0],
                      hall="guild_house", count=1)
    q["template"] = TID
    gs = ws.store.load_place("guild_house")
    gs.board = [q]
    ws.store.save_place(gs)


def accept(ws):
    """Take a missing-person contract from the hall's board with the story call deferred: (the arc the save holds, the error raised)."""
    post(ws)
    err = None
    full_budget()
    try:
        ws.on_accept_quest(ActionIntent(kind="accept_quest", item="1"), "take 1")
    except Exception as e:
        err = e
    finally:
        budget.close()
    data, arc = ws.my_arc()
    return arc, err


def typed(ws, text):
    """The same contract taken by a line the player types: the turn's own operation and budget, the story call priced past that budget
    so it is deferred. (how the line stood, the lines it closed on)"""
    post(ws)
    ws.store.save_meta()
    ws.store.save_player(ws.player)
    ws.interpret = lambda t, hint="": [ActionIntent(kind="accept_quest", item="1")]
    ws.audit_plan = lambda t, plan, raw=None: plan
    task = budget.TASKS["arc_story"]
    was = dict(task)
    task["answer_tokens"] = 10 ** 7
    n = len(SHOWN)
    try:
        stood = ws.turn(text)
    finally:
        task.clear()
        task.update(was)
        del ws.interpret, ws.audit_plan
    return stood, [t for k, t in SHOWN[n:] if k == "note"]


def people_named(arc):
    """The plain story's names, by step: [(kind, people, name)]."""
    by = {n["id"]: n for n in (arc.get("story") or {}).get("nodes", [])}
    return [(n["kind"], n["people"], by.get(n["id"], {}).get("npc_name", "")) for n in arc["nodes"]]


def apart(arc, before):
    """Every person step named, a site step not; no name already in the save, no first name already in the save, none twice."""
    rows = people_named(arc)
    given = [nm for k, _, nm in rows if k != "site"]
    low = {x.strip().lower() for x in before}
    firsts = {names.first_of(x) for x in before}
    return (all(nm.strip() for nm in given) and all(not nm for k, _, nm in rows if k == "site")
            and not any(nm.strip().lower() in low for nm in given) and not any(names.first_of(nm) in firsts for nm in given)
            and len({names.first_of(nm) for nm in given}) == len(given)), rows


def crashed(err):
    return f"{type(err).__name__}: {err}" if err else ""


# ---- the case that found it: a save that holds all sixteen names
NAME = "arc_names_737"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store

arc1, err = accept(ws)                                              # before the names run out: the story stands plain, to redress later
check("(an arc is taken with its story deferred while names are free)", arc1 is not None and not err and (arc1.get("story") or {}).get("plain"),
      crashed(err))
for i, nm in enumerate(LIST):
    if nm not in store.npc_names():
        store.save_npc(NPC(id=f"listed_{i}", name=nm, people="human", role="farmer", location="parth"))
check("(the save holds every name of the captive list)", set(LIST) <= set(store.npc_names()))

err = None
story_was = dict(arc1["story"]) if arc1 else {}
full_budget()
try:
    ws.redress_arc(arc1["id"])
except Exception as e:
    err = e
finally:
    budget.close()
data, arc = ws.my_arc()
check("redress_arc's tail with the story deferred again raises nothing on a save holding all sixteen names", err is None, crashed(err))
check("...and the plain story it had stands, its names as they were", arc is not None and arc["story"] == story_was)

before = store.npc_names()
arc2, err = accept(ws)
check("a missing-person contract is taken with its story deferred on a save holding all sixteen names", err is None and arc2 is not None,
      crashed(err))
check("...the contract is held, and the board no longer posts it", any(q.get("kind") == "missing" for q in ws.player.quests)
      and not store.load_place("guild_house").board)
ok, rows = apart(arc2, before) if arc2 else (False, [])
check("...every person step of its plain story is named, apart from every name in the save and from each other; a site step keeps none",
      ok, rows)
check("...and none of them is a name off the captive list", rows and not any(nm in LIST for _, _, nm in rows), rows)
check("...the story waits for a later turn to dress it", any(r.get("kind") == "arc" and (r.get("data") or {}).get("arc") == (arc2 or {}).get("id")
                                                              for r in store.load_deferred()), store.load_deferred())

# ---- the dressing itself, on the arc just taken (or, if the take failed, one built as start_arc builds it)
if arc2 is not None:
    q2 = next((q for q in ws.player.quests if q.get("arc") == arc2["id"]), {})
else:
    q2 = quests._quest("missing", "D", "Find someone", ws.minutes, victim=arcs.TEMPLATES[TID]["victims"][0], hall="guild_house", count=1)
    q2["template"] = TID
    arc2 = arcs.build(ws.world, store, q2, "guild_house", 20, "arc", "forced", ws.minutes, store.meta.seed)


def dress(arc, q, deferred=True):
    """dress_arc with the story call deferred (or made, and failing): (the story, the error raised)."""
    if deferred:
        full_budget()
    try:
        return ws.dress_arc(arc, q), None
    except Exception as e:
        return {}, e
    finally:
        if deferred:
            budget.close()


real = store.npc_names
reads = [0]


def counted():
    reads[0] += 1
    return real()


store.npc_names = counted
out, err = dress(arc2, q2)
store.npc_names = real
check("one plain dressing reads the save's names once", err is None and reads[0] == 1, (reads[0], crashed(err)))

# ---- the model's story fails its check (not deferred): the plain story is named the same way
was = stub.a_ArcStory
stub.a_ArcStory = lambda u, k: {"hook_title": "x", "title": "x", "victim_name": "x", "premise": "x", "nodes": [{"id": "nope"}]}
out, err = dress(arc2, q2, deferred=False)
stub.a_ArcStory = was
check("the model's story failing its check falls to a plain story that raises nothing", err is None and bool(out.get("nodes")), crashed(err))
ok, rows = apart({**arc2, "story": out}, store.npc_names()) if out else (False, [])
check("...its people named apart from the save and from each other", ok, rows)

# ---- the same arc and save give the same names, and no die of the scene's moves
snap = streams.snapshot()
a, err = dress(arc2, q2)
b, err2 = dress(arc2, q2)
same = [n["npc_name"] for n in a.get("nodes", [])], [n["npc_name"] for n in b.get("nodes", [])]
check("the same arc on the same save is named the same, every time", not err and not err2 and same[0] and same[0] == same[1], (same, crashed(err)))
check("...on the arc's own dice: no draw of the scene's streams moves", streams.snapshot() == snap)

# ---- steps of other peoples: each named as its own people
odd = {**arc2, "nodes": [dict(n) for n in arc2["nodes"]]}
peoples = ["dwarf", "elf", "orc", "halfling"]
for i, n in enumerate(odd["nodes"]):
    n["people"] = peoples[i % len(peoples)]
odd["nodes"][-2]["kind"] = "site"                                  # a place searched, with nobody in it
out, err = dress(odd, q2)
ok, rows = apart({**odd, "story": out}, store.npc_names()) if out else (False, [])
check("an arc whose steps are of four peoples is named apart, each step its own name, its site none", ok and any(k == "site" for k, _, _ in rows),
      (rows, crashed(err)))
room = {}


def of_people(people, full):
    """Whether a full name is one the people's sounds build: a male or female first name and a family name of theirs."""
    if people not in room:                                  # possible() follows a people's family_from, as build() does
        room[people] = (names.possible(people, "male") | names.possible(people, "female"), names.possible(people, "family"))
    first, _, family = full.partition(" ")
    return first in room[people][0] and family in room[people][1]


wrong = [(p, nm) for k, p, nm in rows if k != "site" and not of_people(p, nm)]
check("...and each person is named as their own people (a dwarf a dwarf's name, an elf an elf's)", bool(rows) and not wrong, wrong)

# ---- the same contract taken by a typed line, on the same save: what the player sees of it
config.CRASH_LOG_PATH, config.TURN_LOG_PATH = f"saves/{NAME}/crash.log", f"saves/{NAME}/turns.jsonl"     # a fault here is the save's
before = store.npc_names()
stood, closers = typed(ws, "I take the missing person contract.")
data, arc4 = ws.my_arc()
not_taken = set(failures.F["turn_not_taken"]) | set(failures.F.get("turn_not_possible") or [])
check("typed as a line on that save, the contract is taken: the line stands, and the player reads no line saying it did not happen",
      stood is True and not set(closers) & not_taken, (stood, closers, getattr(ws, "last_failure", None)))
check("...the contract is held in the save, and the board no longer posts it",
      any(q.get("kind") == "missing" for q in store.load_player().quests) and not store.load_place("guild_house").board)
ok, rows = apart(arc4, before) if arc4 else (False, [])
check("...its story stands plain, its people named apart from the save", ok and bool((arc4 or {}).get("story", {}).get("plain")), rows)

store.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)

# ---- a second save: twenty captives taken over twenty fights, each let go (their rows stay)
NAME2 = "arc_names_737_b"
g2 = simlib.campaign(NAME2, cls="warrior", seed=5, location="parth")
ws2, store2 = g2.scene, g2.store
svc = combat_scene.service_of(ws2)
taken_names = []
for i in range(20):
    foe = types.SimpleNamespace(category=A["people_categories"][0], name=f"Bandit {i + 1}", level=3, creature="bandit", id=f"e{i}")
    for cap in svc.captives(types.SimpleNamespace(serial=500 + i), [foe], ws2.player_of(ws2.acting).location):
        npc = ws2.make_prisoner(cap.name, "", tip=cap.tip, named=False, kind=cap.kind, fighter=cap)
        taken_names.append(npc.name)
        ws2.settle_prisoner(npc, "release", "I let them go.")
check("(twenty captives taken, one a fight, and let go)", len(taken_names) == 20, taken_names)
check("(...their names are in the save)", set(taken_names) <= set(store2.npc_names()), sorted(set(taken_names)))
before = store2.npc_names()
arc3, err = accept(ws2)
check("on a save with twenty captives taken, a missing-person contract is taken with its story deferred", err is None and arc3 is not None,
      crashed(err))
ok, rows = apart(arc3, before) if arc3 else (False, [])
check("...its people named apart from every captive's name and from each other", ok, rows)
store2.close()
shutil.rmtree(f"saves/{NAME2}", ignore_errors=True)

arcs.roll_scale = _roll_scale
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
