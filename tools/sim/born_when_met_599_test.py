"""(f599) Parts for every tier, from the model (the owner, 2026-11-11). A normal or uncommon situation asks the model for its parts once a
character can meet it: in its town or where its trouble is, or once they have heard of it or done something it reached; the nearest
first. One far away never asks, takes no parts, and ends as it always did. A turn with no room in its budget spends none of a birth's
tries; the model failing does, and past its tries the engine's own parts stand. Rare and campaign situations are born as before. New
people stay none for the common tiers.
Run: python tools/sim/born_when_met_599_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 5)
simlib.install(stub)
simlib.quiet_console()
from engine import pulse, situation_parts, situations
from engine.budget import Dropped
from llm.gateway import LLMError

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


pulse.P["eventful_chance"] = 0.0
pulse.P["engine_roll"]["chance"] = 0.0
pulse.P["engine_roll"]["quiet_hours"] = 10 ** 6
for tier in pulse.P["tiers"].values():
    tier["resolved_by_others"] = 0.0

g = simlib.campaign("born_when_met_599", seed=5, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
world = ws.world
town = pulse.town_of(world, "trading_square")
far = next(p for p in sorted(world.places) if world.places[p].type in ("town", "city", "village") and pulse.town_of(world, p) != town)


def start(tier, place, seed):
    with ws.operation("test", "a situation born") as op:
        state = store.load_world_state() or {}
        for k, v in pulse.empty_state(ws.minutes).items():
            state.setdefault(k, v)
        ids = {x["id"] for x in state.get("threads", [])}
        ok = pulse.start_thread(store, world, ws.catalog, state, ws.minutes, random.Random(seed), tier=tier, place_id=place, made_by="model")
        store.save_world_state(state)
    return next((x for x in state["threads"] if x["id"] not in ids), None) if ok and op.state == "committed" else None


def th_of(tid):
    return pulse.thread_of(store.load_world_state(), tid)


calls = []
answer = stub.a_SituationParts
stub.a_SituationParts = lambda u, k: calls.append(u) or answer(u, k)

check("the data: every tier born, the common ones once met, and adopted past their tries",
      situations.S["births"]["tiers"] == ["normal", "uncommon", "rare", "campaign"] and situations.S["births"]["reach_tiers"] == ["normal", "uncommon"]
      and {"normal", "uncommon"} <= set(situations.S["births"]["adopt_tiers"]))

away = start("normal", far, 3)
check("(a normal situation is born far away, with no birth due)", away is not None and "parts_due" not in away)
calls.clear()
ws.turn("I look around.")
check("one far away never asks for its parts, and takes none", not calls and "parts" not in th_of(away["id"]) and not situation_parts.adoptable(store.load_world_state()))

here_a = start("normal", "trading_square", 7)
here_b = start("uncommon", "trading_square", 9)
st = store.load_world_state()
first = situation_parts.due(st, world, ["trading_square"])
check("two met where the character stands: due, the oldest of the nearest first", first is not None and first["id"] == here_a["id"], first and first["id"])
calls.clear()
ws.turn("I look around.")
check("...asked one a line, after the line", len(calls) == 1 and th_of(here_a["id"]).get("parts") and "parts" not in th_of(here_b["id"]))
ws.turn("I look around again.")
check("...and the next on the next line", th_of(here_b["id"]).get("parts"))
check("...each with its heart, written once", th_of(here_a["id"]).get("heart") and th_of(here_b["id"]).get("heart"))
check("new people stay none for the common tiers", all(not a.get("new") and a.get("bind") != "new" for a in th_of(here_a["id"])["parts"]
                                                       if a.get("kind") == "person") and situations.S["caps"]["new_people"]["normal"] == 0)

with ws.operation("test", "heard of it"):
    st = store.load_world_state()
    pulse.thread_of(st, away["id"])["answered"] = True
    store.save_world_state(st)
check("one far away the character has heard of is met: due, from wherever they stand",
      situation_parts.due(store.load_world_state(), world, ["trading_square"]) is not None
      and situation_parts.due(store.load_world_state(), world, ["trading_square"])["id"] == away["id"])

# ---- a turn with no room spends no try; the model failing does; past its tries, the engine's own parts
real_birth = situation_parts.birth
def no_room(ws_, tid):
    raise Dropped("situation_parts", "no room this turn")
situation_parts.birth = no_room
ws.turn("I wait.")
check("a turn with no room for the call spends none of its tries, and nothing is counted as failed", th_of(away["id"]).get("parts_due") == 0
      and "parts" not in [o.kind for o in ws.line_world_failed], (th_of(away["id"]).get("parts_due"), [o.kind for o in ws.line_world_failed]))
with ws.operation("test", "it forgets it heard"):
    st = store.load_world_state()
    pulse.thread_of(st, away["id"])["answered"] = False
    store.save_world_state(st)
check("...and once met it stays due, wherever the character goes", situation_parts.due(store.load_world_state(), world, ["nowhere"]) is not None)
def broken(ws_, tid):
    raise LLMError("the model failed")
situation_parts.birth = broken
spent = []
for i in range(situations.S["births"]["tries"]):
    ws.turn(f"I wait, {i}.")
    spent.append(th_of(away["id"]).get("parts_due", "adopted"))
situation_parts.birth = real_birth
th = th_of(away["id"])
check("the model failing spends one try each time, and past them the engine's own parts stand",
      spent[:-1] == list(range(1, situations.S["births"]["tries"])) and th.get("parts_by") == "engine", (spent, th.get("parts_by")))

rare = start("rare", far, 11)
check("a rare one is born as before: due at once, wherever it is", rare is not None and rare.get("parts_due") == 0)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
