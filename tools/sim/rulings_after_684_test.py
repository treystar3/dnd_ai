"""(f684) A situation's ruling never spends the time the player's own line needs (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). `We go to the guild house and I hand the four bear hides to Emlily for the contract.`:
the walk stood, and the give was rolled back, "narrate: the turn's budget is spent (-3 s left)", after four rulings on Parth's
situations, each "0 kept". The owner's word (2026-11-11, f597): the player's line first. A deed done in one of the player's own
operations (a step, a fight's round, its aftermath, a passage) now waits on its situation, and is ruled after the line in an
operation of its own (take_up_rulings), as a deed with no room always was; a deed done elsewhere (the world's own operations, the
tools) is ruled where it is, as before.
Run: python tools/sim/rulings_after_684_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
simlib.quiet_console()
from engine import deeds, events, pulse, retrieval, situation_parts, situations
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


calls = []
answer = stub.a_JudgeVerdict
stub.a_JudgeVerdict = lambda u, k: calls.append(u) or answer(u, k)

g = simlib.campaign("rulings_after_684", seed=7, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
world = ws.world
town = pulse.town_of(world, "trading_square")
folk = retrieval.people_in_town(store, world, town)
by = ws.acting

with ws.operation("test", "a situation with parts"):
    st = store.load_world_state() or {}
    for k_, v_ in pulse.empty_state(ws.minutes).items():
        st.setdefault(k_, v_)
    th = {"id": "th684", "title": "Trouble 684", "tier": "normal", "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
          "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Trouble.", "effects": []}],
          "kind": "politics", "groups": ["everyone"]}
    st["threads"] = [x for x in st.get("threads", []) if x["id"] != "th684"] + [th]
    prop = {"people": [{"who": folk[0].id, "stake": "blocks", "want": "left_alone"}, {"who": folk[1].id, "stake": "harmed", "want": "safety"}]}
    acc, _ = situations.check(SituationParts.model_validate(prop), store, world, "normal", random.Random(7), town=town, ways=False,
                              now=ws.minutes, players=(by,))
    situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
    store.save_world_state(st)


def deed_in(kind_of_op, item):
    with ws.operation(kind_of_op, f"a gift of {item}"):
        events.after_deed(ws, deeds.log(store, "gift", ws.minutes, "trading_square", by=by, npc=folk[1].id, item=item, count=1))


def last_waiting():
    rows = pulse.thread_of(store.load_world_state(), "th684").get("waiting") or []
    return rows[-1].get("item") if rows else None


for kind in ("action:give", "line", "round", "aftermath", "passage", "act:waiting", "command:give", "clarify", "opening"):
    calls.clear()
    deed_in(kind, f"a loaf for {kind}")
    check(f"a deed in the player's own operation ({kind}) asks no ruling and waits on its situation",
          not calls and last_waiting() == f"a loaf for {kind}", (len(calls), last_waiting()))

held = len(pulse.thread_of(store.load_world_state(), "th684").get("waiting") or [])
calls.clear()
ws.take_up_rulings("after the line")
check("after the line, every waiting deed is ruled while the budget has room, none left waiting",
      len(calls) == held and not pulse.thread_of(store.load_world_state(), "th684").get("waiting"), (len(calls), held))

calls.clear()
deed_in("world", "a loaf in the world's own operation")
check("a deed in the world's own operation is ruled where it is, as before", len(calls) == 1, len(calls))
import shutil; shutil.rmtree("saves/rulings_after_684", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
