"""(f598) A situation's end, read from the world (engine/situation_parts.py reading; docs/design/16; the owner's answers of 2026-11-11).
Against its heart, never its parts as they come to stand: a condition is resolved when it is no longer in force and nobody able is set
on imposing it again, so the one who imposed it dying leaves the chain across the road a threat until it is lifted. Every threat
resolved: achieved; partly with a stake lost; transformed with one who imposed a condition still free and set against one who acted, its
follow-up started; every stake lost: lost, its fallout landing. At its time limit a touched situation is read by its stakes, an untouched
one keeps the old roll. A contract handed in and a way met feed the reading. Reading writes nothing and reads the same twice. Every
character whose change counted is credited.
Run: python tools/sim/end_reading_598_test.py"""
import json
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
simlib.quiet_console()
from engine import events, pulse, retrieval, situation_parts, situations, threads
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("end_reading_598", seed=7, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
world = ws.world
town = pulse.town_of(world, "trading_square")
folk = retrieval.people_in_town(store, world, town)
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to))
by = ws.acting
n = [0]


def born(guard_stake="gains", victims=1, tier="rare"):
    """A situation: a guard who keeps a chain across the road out of town, and the people it harms."""
    n[0] += 1
    tid = f"th598_{n[0]}"
    with ws.operation("test", "a situation") as op:
        st = store.load_world_state() or {}
        for k_, v_ in pulse.empty_state(ws.minutes).items():
            st.setdefault(k_, v_)
        th = {"id": tid, "title": f"The chain {n[0]}", "tier": tier, "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
              "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Trouble.", "effects": []}],
              "kind": "politics", "groups": ["everyone"], "fallout": {"description": "The road stays shut.", "effects": []}}
        st.setdefault("threads", []).append(th)
        people = [{"who": folk[0].id, "stake": guard_stake, "want": "coin"}] + [{"who": folk[1 + i].id, "stake": "harmed", "want": "safety"}
                                                                               for i in range(victims)]
        prop = {"people": people, "conditions": [{"on": road, "kind": "closed", "label": "a chain across the road", "by": folk[0].id,
                                                  "by_kind": "person"}]}
        acc, dropped = situations.check(SituationParts.model_validate(prop), store, world, tier, random.Random(n[0]), town=town, ways=False,
                                        now=ws.minutes, players=(by,))
        situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
        store.save_world_state(st)
    assert op.state == "committed", op.state
    return tid


def th_of(tid):
    return pulse.thread_of(store.load_world_state(), tid)


def part(th, kind, who=""):
    return next(i + 1 for i, a in enumerate(th["parts"]) if a["kind"] == kind and (not who or a.get("who") == who))


def change(tid, kind, becomes, who="", by_=by, stance=None):
    """A change kept on the situation by its own writer, as a ruling's would be, then the end read."""
    with ws.operation("test", f"{becomes}") as op:
        st = store.load_world_state()
        th = pulse.thread_of(st, tid)
        k = part(th, kind, who)
        situation_parts.keep_changes(ws, st, th, {"kind": "acted", "by": by_, "npc": "", "seq": None},
                                     [{"n": 1, "part": k, "who": 0, "becomes": becomes, "because": "force", "about": 0, "needs": []}])
        if stance:
            th["parts"][part(th, "person", folk[0].id) - 1].setdefault("willing", {})[by_] = stance
        events.read_end(ws, st, th, "by what was done")
        store.save_world_state(st)
    assert op.state == "committed", op.state


def die(who):
    with ws.operation("test", "a death"):
        nn = store.load_npc(who)
        nn.gone = "dead"
        store.save_npc(nn)


def live(who):
    with ws.operation("test", "alive again"):
        nn = store.load_npc(who)
        nn.gone = ""
        store.save_npc(nn)


def read(tid, at_limit=False):
    st = store.load_world_state()
    return situation_parts.reading(store, world, st, pulse.thread_of(st, tid), ws.minutes, at_limit=at_limit)


# ---- the one who imposed it dead, the chain still across the road: not over; lifted: over
tid = born()
die(folk[0].id)
r = read(tid)
check("the one who imposed a condition dead, the condition still in force: not over (the chain stays across the road)",
      not r.over and not r.threats[0][1], r)
text = json.dumps(store.load_world_state(), sort_keys=True)
check("...reading writes nothing, and reads the same twice", json.dumps(store.load_world_state(), sort_keys=True) == text
      and read(tid) == r)
change(tid, "condition", "lifted")
th = th_of(tid)
check("the chain lifted with no one left to put it back: over, achieved, the player's doing", th["status"] == "resolved"
      and th.get("ending_kind") == "achieved" and th.get("result") == "player", (th["status"], th.get("ending_kind")))
settled = [d for d in store.load_world_state()["deeds"] if d["kind"] == "settled" and d.get("thread") == tid]
check("...a settled deed for the one whose change counted, with how it ended", [(d["by"], d.get("ending")) for d in settled] == [(by, "achieved")], settled)
live(folk[0].id)

# ---- lifted while its keeper is still set on it: not over
tid = born()
change(tid, "condition", "lifted")
check("lifted while the one who imposed it is still free and able: not over (nobody has stopped them putting it back)",
      th_of(tid)["status"] == "active", th_of(tid)["status"])

# ---- won over, then lifted: over; one harmed dead on the way: partly
tid = born(victims=2)
die(folk[1].id)
change(tid, "person", "open", who=folk[0].id)
change(tid, "condition", "lifted")
th = th_of(tid)
check("its keeper won over and the chain lifted, but one of those it harmed dead: partly achieved", th["status"] == "resolved"
      and th.get("ending_kind") == "partly", (th["status"], th.get("ending_kind")))
live(folk[1].id)

# ---- every stake lost: lost, its fallout landing, nobody credited
tid = born()
change(tid, "person", "colder", who=folk[0].id)                     # something done, so it was touched
die(folk[1].id)
with ws.operation("test", "read"):
    st = store.load_world_state()
    events.read_end(ws, st, pulse.thread_of(st, tid))
    store.save_world_state(st)
th = th_of(tid)
check("everyone it put at stake lost: over, lost, its fallout landing, no settled deed", th["status"] == "ended" and th.get("ending_kind") == "lost"
      and not [d for d in store.load_world_state()["deeds"] if d["kind"] == "settled" and d.get("thread") == tid], (th["status"], th.get("ending_kind")))
live(folk[1].id)

# ---- transformed: the chain lifted, its keeper fled with a grudge: free, and set against the character
followed = []
real_follow = threads.follow_up
threads.follow_up = lambda state, th_, how, rng, t, always=False: followed.append((th_["id"], how, always)) or real_follow(state, th_, how, rng, t, always)
tid = born()
with ws.operation("test", "the keeper flees, set against the player"):
    st = store.load_world_state()
    th = pulse.thread_of(st, tid)
    k = part(th, "person", folk[0].id) - 1
    th["parts"][k]["now"] = "fled"
    th["parts"][k].setdefault("willing", {})[by] = "committed"
    store.save_world_state(st)
check("the keeper fled, the chain still across the road: not over (it is still in force)", not read(tid).over)
change(tid, "condition", "lifted")
threads.follow_up = real_follow
th = th_of(tid)
check("the chain lifted with its keeper fled but free and set against the character: transformed, its follow-up always started",
      th.get("ending_kind") == "transformed" and (tid, "settled", True) in followed, (th.get("ending_kind"), followed))
settled = [d for d in store.load_world_state()["deeds"] if d["kind"] == "settled" and d.get("thread") == tid]
check("...still the character's doing, credited as transformed", [d.get("ending") for d in settled] == ["transformed"], settled)

# ---- the time limit: touched, read by its stakes; untouched, the old roll
tid = born()
change(tid, "person", "colder", who=folk[0].id)
tid2 = born()
with ws.operation("test", "time passes"):
    store.meta.minutes = th_of(tid)["times"][-1] + 60
    store.save_meta()
    st = store.load_world_state()
    pulse.tick_threads(store, world, ws.catalog, st, store.meta.minutes, random.Random(1))
    store.save_world_state(st)
check("at its time limit a touched situation waits to be read, never rolled", th_of(tid)["status"] == "active" and th_of(tid).get("read_due"))
check("...an untouched one keeps the old roll (settled by others, or its fallout)", th_of(tid2)["status"] != "active")
with ws.operation("test", "after the pulse"):
    events.read_ends(ws)
th = th_of(tid)
check("...read after the pulse by its stakes: nothing secured and no threat resolved, lost", th["status"] == "ended" and th.get("ending_kind") == "lost",
      (th["status"], th.get("ending_kind")))

# ---- two characters, each credited
tid = born()
die(folk[0].id)
change(tid, "person", "warmer", who=folk[1].id, by_="another_character")
change(tid, "condition", "lifted")
settled = sorted(d["by"] for d in store.load_world_state()["deeds"] if d["kind"] == "settled" and d.get("thread") == tid)
check("every character whose change counted is credited, a deed each", settled == sorted([by, "another_character"]), settled)
live(folk[0].id)

# ---- one nobody touched is never ended by the reading, nor anyone credited
tid = born()
with ws.operation("test", "the chain lifted off-screen"):
    st = store.load_world_state()
    th = pulse.thread_of(st, tid)
    th["parts"][part(th, "condition") - 1]["now"] = "lifted"
    store.save_world_state(st)
die(folk[0].id)
with ws.operation("test", "after the pulse"):
    events.read_ends(ws)
th = th_of(tid)
check("one nobody touched is never ended by the reading, whatever befalls it off-screen; it keeps the old roll", th["status"] == "active"
      and not [d for d in store.load_world_state()["deeds"] if d["kind"] == "settled" and d.get("thread") == tid])
live(folk[0].id)

# ---- what a creature imposes goes with the creature
tid = born()
with ws.operation("test", "a beast keeps the road"):
    st = store.load_world_state()
    th = pulse.thread_of(st, tid)
    th["heart"]["threats"] = [dict(x, by="the wolves", by_kind="creature") for x in th["heart"]["threats"]]
    st.setdefault("spawns", []).append({"id": "sp598", "thread": tid, "name": "the wolves", "defeated": False, "from": 0,
                                        "until": ws.minutes + 9 * 1440, "boss": False, "kills": 0, "need": 3})
    store.save_world_state(st)
check("a condition a creature imposes holds while the creature is abroad", not read(tid).threats[0][1])
with ws.operation("test", "the wolves beaten"):
    st = store.load_world_state()
    next(s_ for s_ in st["spawns"] if s_["id"] == "sp598")["defeated"] = True
    store.save_world_state(st)
check("...and is resolved once it is beaten back, though nobody lifted it by hand", read(tid).threats[0][1])

# ---- a situation's own request handed in secures its stake
tid = born()
with ws.operation("test", "a load to move") as op:
    st = store.load_world_state()
    th = pulse.thread_of(st, tid)
    th["parts"].append({"kind": "resource", "good": "salt", "state": "stranded", "holder": folk[1].id})
    th["heart"]["stakes"].append({"part": len(th["parts"]) - 1, "kind": "resource", "good": "salt", "state": "stranded"})
    store.save_world_state(st)
check("a load at stake is at risk until it is moved", [s_ for x, s_ in read(tid).stakes if x["kind"] == "resource"] == ["at_risk"])
with ws.operation("test", "the request handed in"):
    st = store.load_world_state()
    pulse.thread_of(st, tid)["parts"][-1]["done"] = True
    store.save_world_state(st)
check("...and secured once its request is handed in", [s_ for x, s_ in read(tid).stakes if x["kind"] == "resource"] == ["secured"])
check("at its limit, read by its stakes: something secured, partly", read(tid, at_limit=True).ending == "partly")
tid = born()
with ws.operation("test", "won over only"):
    st = store.load_world_state()
    th = pulse.thread_of(st, tid)
    th["parts"][part(th, "person", folk[0].id) - 1].setdefault("willing", {})[by] = "open"
    store.save_world_state(st)
check("...nothing secured, though its keeper was won over: lost (the stakes decide, not a threat half-met)", read(tid, at_limit=True).ending == "lost")

# ---- meeting a fixer's condition makes them willing, and nothing more (the owner, 2026-11-11)
from engine import situation_parts as sp
tid = born(guard_stake="can_fix")
with ws.operation("test", "the fixer paid"):
    st = store.load_world_state()
    th = pulse.thread_of(st, tid)
    sp.met_way(ws, st, th, {"kind": "part", "target": folk[0].id, "need": "paid"}, by)
    store.save_world_state(st)
th = th_of(tid)
check("meeting the condition of one who could set it right makes them willing and secures nothing by itself", th["status"] == "active"
      and th["parts"][part(th, "person", folk[0].id) - 1]["willing"][by] == "open"
      and th["parts"][part(th, "condition") - 1].get("now") != "lifted" and all(s_ != "secured" for _, s_ in read(tid).stakes))
check("...and a change that moved nothing toward its end (colder) counts no one as a contributor", sp.contributors(
    {"heart": th["heart"], "changes": [{"by": "x", "becomes": "colder", "part": 1}]}) == [])

# ---- a contract handed in: paid, and the world decides
tid = born(tier="normal")
with ws.operation("test", "a hand-in"):
    from engine import deeds
    events.after_deed(ws, deeds.log(store, "quest_done", ws.minutes, "trading_square", thread=tid, title="the guild job", by=by))
check("a contract handed in on a situation with parts ends nothing by itself", th_of(tid)["status"] == "active")

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
