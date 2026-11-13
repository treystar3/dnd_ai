"""(f589) The world's state behind one seam (docs/design/05 step 1; docs/design/13, its f582). The store's whole-state load and save go
through storage/worldrow.py; the narrow readers there (and engine/worldstate.py over them) answer what the whole state would, on every
state the seeded world script saves; the four places that priced, endangered and shut a place answer as before; the stale-save detector
notes a copy saved over a newer write, with the function that saved it, and only that; shipped play loads plain dicts as before; the
caps on the world's lists are checked at startup; and the key the row is kept under is named only in storage/.
Run: python tools/sim/worldstate_589_test.py"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
sys.path.insert(0, "tools/sim")
import world_script
from engine import data_check, pulse, worldstate
from storage import worldrow

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


# ---- the readers before the seam, as they were written (engine/pulse.py and engine/deeds.py at f588), to hold the new ones to
def old_effects(state, now, kind, place, good=""):
    return [e for e in state.get("effects", []) if e["kind"] == kind and e["place"] == place and e["until"] > now
            and (not e.get("good") or e["good"] == good)]


def old_since(state, minute, kinds=None):
    return [d for d in state.get("deeds", []) if d["minute"] >= minute and (not kinds or d["kind"] in kinds)]


seen = {"saves": 0, "queries": 0, "differ": []}


def watch(game):
    store, world, real = game.store, game.scene.world, game.store._put

    def put(key, text):                                # under the seam's save, so the detector still names the real caller
        real(key, text)
        if key != "world_state":
            return
        whole = json.loads(text or "{}")
        seen["saves"] += 1
        now = int(store.meta.minutes)
        asks = {(e["kind"], e["place"], e.get("good", "")) for e in whole.get("effects", [])} | {("prices", "nowhere", "")}
        ends = {e["until"] for e in whole.get("effects", [])}
        for kind, place, good in sorted(asks):
            for t in sorted({now, now + 5 * 1440} | ends | {u - 1 for u in ends}):
                got, want = worldstate.effects_at(store, kind, place, t, good), old_effects(whole, t, kind, place, good)
                seen["queries"] += 1
                if got != want:
                    seen["differ"].append(("effects_at", kind, place, t))
        for status in (None, "active", "resolved", "fallen"):
            want = [x for x in whole.get("threads", []) if status is None or x.get("status") == status]
            seen["queries"] += 1
            if worldstate.threads(store, status) != want:
                seen["differ"].append(("threads", status))
        mids = sorted({d["minute"] for d in whole.get("deeds", [])})
        for minute in ([0] + mids[len(mids) // 2:len(mids) // 2 + 1]):
            for kinds in (None, ("found",), ["settled", "kill"]):
                seen["queries"] += 1
                if worldstate.deeds_since(store, minute, kinds) != old_since(whole, minute, kinds):
                    seen["differ"].append(("deeds_since", minute, kinds))
        seen["queries"] += 1
        if worldstate.news(store) != list(whole.get("news", [])):
            seen["differ"].append(("news",))
        for place in {e["place"] for e in whole.get("effects", [])} | {world_script.PLACE}:
            seen["queries"] += 4
            if pulse.price_factor(store, world, place, now) != 1 + sum(e["value"] for e in old_effects(whole, now, "prices", pulse.town_of(world, place))) / 100 \
                    or pulse.danger_factor(store, place, now) != max(0.0, 1 + sum(e["value"] for e in old_effects(whole, now, "danger", place)) / 100):
                seen["differ"].append(("price or danger", place))
            shut = [e for e in old_effects(whole, now, "closed", place) if e.get("cause") != "improvised"]
            if pulse.closed_reason(store, place, now) != (shut[0]["text"] if shut else "") \
                    or pulse.closed_until(store, place, now) != max((e["until"] for e in shut), default=0):
                seen["differ"].append(("closed", place))
    game.store._put = put


run = world_script.play("worldstate_589", stub, prepare=watch)
check("the world script played whole (its coverage met)", all(run.cover.values()), [k for k, v in run.cover.items() if not v])
check("every narrow reader answered what the whole state holds, on every state the script saved", not seen["differ"]
      and seen["saves"] >= 40 and seen["queries"] >= 1000, (seen["differ"][:5], seen["saves"], seen["queries"]))

# ---- the edges the script may not reach: a price on one good, an effect at the very minute it ends
g0 = simlib.campaign("worldstate_589_edges", seed=4)
edge = {"effects": [{"kind": "prices", "place": "parth", "value": 20, "until": 5000, "good": "salt"},
                    {"kind": "prices", "place": "parth", "value": 10, "until": 5000},
                    {"kind": "closed", "place": "gate", "value": 0, "until": 3000, "text": "Shut.", "cause": "flood"},
                    {"kind": "closed", "place": "gate", "value": 0, "until": 4000, "text": "Barred.", "cause": "improvised"}]}
g0.store.save_world_state(edge)
odd = [(k, p, t, good) for k, p, good in (("prices", "parth", ""), ("prices", "parth", "salt"), ("prices", "parth", "bread"), ("closed", "gate", ""))
       for t in (2999, 3000, 3999, 4000, 4999, 5000)
       if worldstate.effects_at(g0.store, k, p, t, good) != old_effects(edge, t, k, p, good)]
check("...and at the edges: a price on one good, and an effect at the minute it ends and the minute before", odd == [], odd)

# ---- the stale-save detector, on the script's own play
RECORDED = set()                                       # (f589) known sites that save a world state over a newer one: only shrinks
found = {s["site"] for s in run.game.store._world.stale}
check("the world script makes no stale save the ratchet does not know of", found <= RECORDED, sorted(found - RECORDED))
check("...and every one the ratchet holds still happens (a fixed one leaves the list)", RECORDED <= found, sorted(RECORDED - found))

# ---- the detector, on saves built to be stale and not
g = simlib.campaign("worldstate_589_b", seed=5)
store = g.store
store.save_world_state({"seq": 1, "deeds": []})
seam = store._world


def held_over():
    a = store.load_world_state()
    b = store.load_world_state()
    b["seq"] = 2
    store.save_world_state(b)
    a["seq"] = 3
    store.save_world_state(a)                          # a's copy is older than what b wrote


held_over()
check("a copy saved over a newer write is noted, with the function that saved it", [s["site"] for s in seam.stale]
      == ["tools.sim.worldstate_589_test:held_over"], seam.stale)
check("...and the save is still made, as today", store.load_world_state()["seq"] == 3)
seam.stale.clear()
s = store.load_world_state()
s["seq"] = 4
store.save_world_state(s)
s["seq"] = 5
store.save_world_state(s)                              # the same copy saved twice: its second save follows its first
store.save_world_state({"seq": 6, "built": True})      # a state a test builds by hand
t = store.load_world_state()
store.save_world_state(t)
check("a copy saved again, a built state and a load saved back are never noted", seam.stale == [] and store.load_world_state()["seq"] == 6,
      seam.stale)
a = store.load_world_state()
try:
    with store.transaction():
        a["seq"] = 7
        store.save_world_state(a)
        raise RuntimeError("the step fails")
except RuntimeError:
    pass
check("a write taken back by its transaction leaves the stored text as it was", store.load_world_state()["seq"] == 6)
b = store.load_world_state()
store.save_world_state(b)
check("...a fresh load after it saves cleanly", seam.stale == [], seam.stale)
store.save_world_state(a)
check("...and the copy that carried the taken-back write is noted when it is saved (the detector reads stored text, not a count)",
      len(seam.stale) == 1, seam.stale)

# ---- shipped play: no detector, plain dicts
worldrow.WATCH_STALE = False
plain = store.load_world_state()
check("with the detector off a load is a plain dict, as before", type(plain) is dict and plain.get("seq") == 7)
seam.stale.clear()
held_over()
check("...and nothing is noted", seam.stale == [])
store.save_world_state({})
check("...an empty row loads as an empty dict", store.load_world_state() == {} and type(store.load_world_state()) is dict)
worldrow.WATCH_STALE = True

# ---- the caps, at startup
E, P = data_check._load("data/rules/events.yaml"), data_check._load("data/rules/pulse.yaml")
check("the caps on the world's lists pass as shipped", data_check.world_caps_problems() == [] and data_check.check() == [])
was = data_check.world_caps_problems
data_check.world_caps_problems = lambda E=None, P=None: ["a cap is wrong"]
check("...and startup runs that check", "a cap is wrong" in data_check.check())
data_check.world_caps_problems = was
for bad_e, bad_p, what in ((dict(E, judge=dict(E["judge"], keep_deeds=0)), P, "keep_deeds 0"),
                           (E, dict(P, history_keep="many"), "history_keep as text"),
                           (E, dict(P, news=dict(P["news"], keep=-1)), "news.keep below 0"),
                           (E, dict(P, news={k: v for k, v in P["news"].items() if k != "keep_days"}), "news.keep_days missing")):
    check(f"...and a cap that would empty or unbound a list fails: {what}", len(data_check.world_caps_problems(bad_e, bad_p)) == 1,
          data_check.world_caps_problems(bad_e, bad_p))
check("a gift or a bribe may be a deed the town answers", '"gift", "bribe"' in Path("engine/data_check.py").read_text(encoding="utf-8"))

# ---- the fence: the row's key is storage's alone
named = []
for d in ("engine", "scenes", "services", "npc", "character", "llm", "ui", "world", "core"):
    for f in Path(d).rglob("*.py"):
        if re.search(r"""["']world_state["']""", f.read_text(encoding="utf-8")):
            named.append(f.as_posix())
for f in ("main.py", "config.py"):
    if Path(f).exists() and re.search(r"""["']world_state["']""", Path(f).read_text(encoding="utf-8")):
        named.append(f)
check("the key the world's row is kept under is named only in storage/", named == [], named)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
