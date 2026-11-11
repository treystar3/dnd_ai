"""(f578) A situation the player ends leaves its 'settled' deed in the world's ledger. events.finish logged it through deeds.log, which
loaded and saved its own copy of the world row; both of finish's callers then returned into after_deed, which saved its older copy over
it, so the deed and its count were lost in play and the rule that counts them (consequences.yaml renown_campaign) could never be met by
the player's own endings. finish now adds the deed to the state it was handed, so the one save keeps it, and the deed names who did it.
Run: python tools/sim/settled_deed_578_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import consequences, deeds, events, pulse
from engine.domain_events import CreatureKilled

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("settled_578", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
n = [0]


def born(tier="normal", paths=(), stage=0):
    """An active matter at the square; its id."""
    n[0] += 1
    tid = f"ths{n[0]}"
    t = ws.minutes
    st = store.load_world_state()
    st.setdefault("threads", []).append({"id": tid, "title": f"Trouble {n[0]}", "tier": tier, "place": "trading_square",
                                         "times": [t, t + 6 * 1440, t + 12 * 1440], "status": "active", "made": t, "clues": [],
                                         "paths": [dict(p) for p in paths], "stage": stage,
                                         "stages": [{"description": "Trouble.", "effects": []}, {"description": "Worse.", "effects": []}],
                                         "kind": "trouble", "groups": ["everyone"], "fallout": {"description": "", "effects": []},
                                         "resolution": "", "triumph": None})
    store.save_world_state(st)
    return tid


def thread(tid):
    return next(x for x in store.load_world_state()["threads"] if x["id"] == tid)


def kill(creature):
    """A kill the world notices, by the real path: the reaction logs the deed, then asks what it ended (engine/reactions.py ledger)."""
    ws.notice(CreatureKilled(minute=ws.minutes, place="trading_square", witnesses=(), creature=creature, level=1))


def settled(tid=None):
    return [d for d in store.load_world_state().get("deeds", []) if d["kind"] == "settled" and (tid is None or d.get("thread") == tid)]


# ---- ended by one of its ways
WAY = {"kind": "kill", "target": "wolf", "name": "kill the wolves", "how": "the wolves are killed", "done": False}
tid = born(paths=[WAY])
kill("wolf")
st = store.load_world_state()
check("(the kill met the matter's way and ended it as the player's doing)", thread(tid)["status"] == "resolved"
      and thread(tid).get("result") == "player", (thread(tid)["status"], thread(tid).get("result")))
mine = settled(tid)
check("a matter ended by one of its ways leaves one 'settled' deed in the saved world", len(mine) == 1, st.get("deeds"))
kills = [d for d in st.get("deeds", []) if d["kind"] == "kill"]
check("...numbered after the deed that ended it, and the world's count stands at the last deed", bool(mine) and bool(kills)
      and mine[0].get("seq", 0) > kills[-1]["seq"] and st.get("seq") == max(d.get("seq", 0) for d in st["deeds"]),
      (st.get("seq"), [(d["kind"], d.get("seq")) for d in st.get("deeds", [])]))
check("...and it names who did it, the matter and how", bool(mine) and mine[0].get("by") == ws.acting and mine[0].get("title") == "Trouble 1"
      and mine[0].get("tier") == "normal" and "kill the wolves" in mine[0].get("how", ""), mine)

# ---- ended by the judge's word
tid2 = born(tier="rare", stage=1)
stub.verdict = "resolved"
kill("bandit")
stub.verdict = "no"
check("(the judge ruled the rare matter ended)", thread(tid2)["status"] == "resolved" and thread(tid2).get("result") == "player",
      (thread(tid2)["status"], thread(tid2).get("judge_calls")))
check("a matter the judge rules ended leaves its 'settled' deed too", len(settled(tid2)) == 1 and settled(tid2)[0].get("by") == ws.acting,
      store.load_world_state().get("deeds"))

# ---- what counts them
st = store.load_world_state()
rules = [r["id"] for r, _ in consequences.met(st, world, town, ws.minutes)]
check("two matters settled in the region within six weeks meet the rule that counts them (renown_campaign)", "renown_campaign" in rules,
      (rules, [(d["kind"], d.get("place")) for d in st.get("deeds", [])]))

# ---- an ending that does not stand takes its deed back
from llm.gateway import LLMError
tid3 = born(paths=[dict(WAY, target="boar")])
before = store.load_world_state()
with ws.operation("test", "an ending that fails after it") as op:
    kill("boar")
    inside = settled(tid3)
    raise LLMError("the model failed")
check("an ending inside an operation that fails is taken back whole, its deed and the world's count with it", len(inside) == 1
      and op.state == "rolled_back" and store.load_world_state() == before and thread(tid3)["status"] == "active",
      (len(inside), op.state, store.load_world_state().get("seq"), before.get("seq")))
kill("boar")
check("...and the same deed done again, standing, is kept once", len(settled(tid3)) == 1 and thread(tid3)["status"] == "resolved", settled(tid3))

# ---- the plain ledger call is as it was
g2 = simlib.campaign("settled_578_empty", seed=8)
empty = g2.store
before = empty.load_world_state()
d = deeds.log(empty, "kill", 600, "trading_square", creature="wolf")
check("a deed logged where no world row stands writes nothing and is still handed back", not before and not empty.load_world_state()
      and d["kind"] == "kill" and "seq" not in d, (before, empty.load_world_state(), d))
st3 = {"seq": 4, "deeds": [{"kind": "kill", "minute": 1, "place": "", "seq": 4}]}
d3 = deeds.add(st3, "found", 9, "trading_square", thread="x")
check("deeds.add numbers the deed on the state it is handed, appends it and saves nothing", d3["seq"] == 5 and st3["seq"] == 5
      and st3["deeds"][-1] is d3 and d3["thread"] == "x", st3)
many = {"deeds": [{"kind": "kill", "minute": i, "place": ""} for i in range(deeds.KEEP)]}
deeds.add(many, "kill", 10 ** 6, "")
check("...and keeps the ledger at its cap", len(many["deeds"]) == deeds.KEEP and many["deeds"][-1]["minute"] == 10 ** 6, len(many["deeds"]))

g.session.close()
g2.session.close()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
