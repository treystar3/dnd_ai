"""(f597) The gate: which deeds reach a situation's ruling (the owner, 2026-11-11: the judge's tier filter, its one call a game day and
its 8 in all go; the reuse rule and the turn's budget hold instead). A situation with parts, at any tier, is ruled on for a deed that
touches it by id: done to one of its people, carrying its id, killing a threat it names, or done where its trouble is; a gift, a bribe,
an offence and an act of the one ruling among them. Deeds that touch nothing make no call. The same deed with nothing changed is ruled
no more; a different one the same day is. An act whose own ruling already weighed the situation is never ruled again for it. A ruling
the turn's budget has no room for leaves the deed waiting on the situation, ruled after the next line (as a birth is), never lost
to a limit: past the waiting cap the oldest is let go and counted. A situation without
parts is ruled on not at all (the owner, 2026-11-11: the old judge retired), at any tier. The ruling is asked outside the transaction,
and the turn's budget is asked before any line stands down for it.
Run: python tools/sim/gate_597_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
simlib.quiet_console()
from core import yamlio
from engine import deeds, events, pulse, retrieval, roads, situation_parts, situations
from engine.budget import Dropped
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


calls = []
answer = stub.a_JudgeVerdict
stub.a_JudgeVerdict = lambda u, k: calls.append(u) or answer(u, k)

g = simlib.campaign("gate_597", seed=7, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
world = ws.world
town = pulse.town_of(world, "trading_square")
folk = retrieval.people_in_town(store, world, town)
by = ws.acting


def situation(tid, tier, parts=True, place="trading_square"):
    st = store.load_world_state() or {}
    for k_, v_ in pulse.empty_state(ws.minutes).items():
        st.setdefault(k_, v_)
    st["threads"] = [x for x in st.get("threads", []) if x["id"] != tid]
    th = {"id": tid, "title": f"Trouble {tid}", "tier": tier, "place": place, "times": [ws.minutes, ws.minutes + 9 * 1440],
          "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Trouble.", "effects": []}],
          "kind": "politics", "groups": ["everyone"]}
    st["threads"].append(th)
    if parts:
        prop = {"people": [{"who": folk[0].id, "stake": "blocks", "want": "left_alone"}, {"who": folk[1].id, "stake": "harmed", "want": "safety"}]}
        acc, _ = situations.check(SituationParts.model_validate(prop), store, world, tier, random.Random(7), town=town, ways=False,
                                  now=ws.minutes, players=(by,))
        situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
    store.save_world_state(st)
    return th


with ws.operation("test", "a common situation with parts") as op:
    situation("th597", "normal")
check("a common situation is set, with parts", op.state == "committed" and pulse.thread_of(store.load_world_state(), "th597").get("parts"))


def deed(kind, place="trading_square", **data):
    with ws.operation("test", f"a {kind}"):
        events.after_deed(ws, deeds.log(store, kind, ws.minutes, place, by=by, **data))


calls.clear()
deed("gift", npc=folk[1].id, item="a loaf", count=1)
check("a gift to a common situation's person is ruled on (no tier filter)", len(calls) == 1, len(calls))
deed("gift", npc=folk[1].id, item="a loaf", count=1)
check("...the same gift again, with nothing it could change changed, is ruled no more", len(calls) == 1, len(calls))
deed("bribe", npc=folk[0].id, coin=50)
check("...a different deed the same day is ruled (no daily limit, no count)", len(calls) == 2, len(calls))
far = next(p for p in sorted(world.places) if world.places[p].type not in ("road",) and pulse.town_of(world, p) != town
           and p not in situation_parts.trouble_near(world, pulse.thread_of(store.load_world_state(), "th597"), [])[0])
for i in range(10):
    deed("kill", place=far, creature=f"wolf {i}", level=1, rank="normal")
check("ten kills that touch nothing of it make no call", len(calls) == 2, len(calls))
deed("offense", offense="assault", target=folk[0].id, witnesses=[])
check("an offence against one of its people is ruled on", len(calls) == 3, len(calls))
deed("acted", what="kick the barrel", degree="success", changes=[], considered=["th597"])
check("an act whose own ruling already weighed the situation is never ruled again for it", len(calls) == 3, len(calls))
deed("acted", what="kick the barrel over", degree="success", changes=[], considered=[])
check("...one done where the trouble is, its ruling never having weighed it, is", len(calls) == 4, len(calls))

# ---- the reuse rule's edges: a different amount is a different deed; a call that gave no ruling is no ruling
deed("bribe", npc=folk[0].id, coin=5)
n0 = len(calls)
deed("bribe", npc=folk[0].id, coin=5000)
check("a bribe of 5 then of 5000 are two deeds, each ruled on", len(calls) == n0 + 1, (n0, len(calls)))
from llm.gateway import LLMError
was = stub.a_JudgeVerdict
def down(u, k):
    raise LLMError("the model is down")
stub.a_JudgeVerdict = down
deed("gift", npc=folk[0].id, item="a pear", count=1)
stub.a_JudgeVerdict = was
n1 = len(calls)
deed("gift", npc=folk[0].id, item="a pear", count=1)
check("a call that gave no ruling is never kept as one: the same deed is ruled on when the model answers", len(calls) == n1 + 1)

# ---- no room in the turn's budget: it waits, and is ruled at the next input
real_rule = situation_parts.rule
def no_room(*a, **k):
    raise Dropped("event_judge", "no room this turn")
situation_parts.rule = no_room
deed("gift", npc=folk[0].id, item="a jug of ale", count=1)
situation_parts.rule = real_rule
th = pulse.thread_of(store.load_world_state(), "th597")
check("a ruling the budget has no room for leaves the deed waiting on the situation, with who saw it",
      [d.get("item") for d in th.get("waiting") or []] == ["a jug of ale"] and "witnesses_at" in th["waiting"][0])
calls.clear()
ws.turn("I look around.")
th = pulse.thread_of(store.load_world_state(), "th597")
check("...ruled after the next line, as a birth is, and no longer waiting: nothing lost", len(calls) >= 1 and not th.get("waiting")
      and any("ale" in c for c in calls), len(calls))

# ---- the budget asked first: one operation with no room stands down for none of its rulings, and all of them wait
from engine import budget, refusals
asked_budget, noted = [], []
real_allow = budget.allow
def full(task, chars):
    asked_budget.append(task)
    raise Dropped(task, "no room")
budget.allow = full
refusals_note = refusals.note
refusals.note = lambda kind, text, why="", place="", turn=-1, asked="": noted.append((kind, why))
with ws.operation("test", "a busy line") as op:
    for i in range(situation_parts.S["rulings"]["waiting"] + 2):
        events.after_deed(ws, deeds.log(store, "gift", ws.minutes, "trading_square", by=by, npc=folk[1].id, item=f"an apple {i}", count=1))
budget.allow, refusals.note = real_allow, refusals_note
th = pulse.thread_of(store.load_world_state(), "th597")
check("the budget is asked before a line stands down for a ruling, once an operation: the rest wait without asking", op.state == "committed"
      and asked_budget == ["event_judge"], asked_budget)
check("...past the waiting cap the oldest is let go, counted as a ruling that failed", len(th["waiting"]) == situation_parts.S["rulings"]["waiting"]
      and len([n for n in noted if n[0] == "ruling_failed"]) == 2, (len(th["waiting"]), noted))
with ws.operation("test", "clear the queue"):
    st = store.load_world_state()
    pulse.thread_of(st, "th597")["waiting"] = []
    store.save_world_state(st)

# ---- without parts: ruled on not at all
with ws.operation("test", "no parts") as op:
    situation("th597n", "normal", parts=False)
    situation("th597r", "rare", parts=False)
    st = store.load_world_state()
    for x in st["threads"]:
        if x["id"] in ("th597n", "th597r"):
            x["stage"] = 1
    store.save_world_state(st)
st = store.load_world_state()
d = deeds.log(store, "kill", ws.minutes, "trading_square", creature="rat", level=1, rank="normal", by=by)
check("a situation without parts, common or rare, is ruled on not at all (the old judge is retired)",
      not events.judge_ok(world, st, pulse.thread_of(st, "th597n"), d, ws.minutes)
      and not events.judge_ok(world, st, pulse.thread_of(st, "th597r"), d, ws.minutes))

E = yamlio.safe_load(open("data/rules/events.yaml", encoding="utf-8").read())
B = yamlio.safe_load(open("data/rules/budget.yaml", encoding="utf-8").read())
check("the daily limit, the count and the old judge's tiers are gone from the data, the new deeds in",
      not ({"tiers", "per_day", "max_calls", "no_parts_tiers", "min_stage"} & set(E["judge"]))
      and {"gift", "bribe", "offense", "found", "acted"} <= set(E["judge"]["relevant_deeds"]))
check("the ruling is asked outside the transaction", "event_judge" in B["asked_outside"])

# ---- the world script's calls, counted: a later change that multiplies them fails here
sys.path.insert(0, "tools/sim")
import world_script
calls.clear()
run = world_script.play("gate_597_ws", stub)
CEILING = 2                                            # (f598) the seeded world script's rulings: a gift moving a rare matter, one ending it
check("the seeded world script plays whole", all(run.cover.values()), [k for k, v in run.cover.items() if not v])
check(f"...and asks for no more rulings than it does today ({CEILING})", len(calls) <= CEILING, len(calls))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
