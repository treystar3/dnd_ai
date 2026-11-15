"""(f641) The narrow reads read one table (docs/design/20_phase3_plan.md; storage/worldtables.py; engine/worldstate.py).
The four readers on the world's seam (the effects at a place, the matters by status, the deeds since a minute, the news) were
filters over the whole world, loaded for each question. Each is now one query on its own table. Held here:
- a reader loads no whole world: with the whole load made to fail, each of the four still answers;
- each asks one statement of one table, and the three that ask by something find it by that table's index;
- each answers what the filter over the whole world answers, on a world with every list in use and on the edges: an effect at the
  minute it ends and the minute before, a price on one good, a minute that is not whole, a matter with no status, a list that
  is absent or empty, a world saved again with fewer, and a world with no row at all;
- a reader sees what its own transaction has written, and what a transaction took back is gone from it;
- the four places in the game that ask (a price, a danger, a place shut and until when) load no whole world;
- a save still on its rows (an older one, while its steps run) is answered by the filter, as before;
- over the three kept recordings, replayed whole both ways, a process each: no input loads the whole world more often than it
  did with the readers as filters, and the play as a whole loads it less often.
Run: python tools/sim/narrow_reads_641_test.py"""
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools/sim")
sys.path.insert(0, "tools")
from storage import worldrow, worldtables
from storage.worldrow import deeds_matching, effects_matching, news_matching, threads_matching

GOLDENS = ("stub_short", "stub_party", "stub_fight")


def as_filters() -> None:
    """The readers as they were until f641: each a filter over the whole world, loaded for the question."""
    T = worldtables.TableWorld
    T.effects_at = lambda self, kind, place, now, good="": effects_matching(self.load(), now, kind, place, good)
    T.threads = lambda self, status=None: threads_matching(self.load(), status)
    T.deeds_since = lambda self, minute, kinds=None: deeds_matching(self.load(), minute, kinds)
    T.news = lambda self: news_matching(self.load())


def count(how: str, out: str) -> None:
    """The child: the three kept recordings replayed, the whole-world loads counted by the input they fell in."""
    import rerun
    if how == "filters":
        as_filters()
    real = worldtables.TableWorld._held
    seen = {}

    def held(self):
        steps = int(getattr(self._store.meta, "steps", 0) or 0)
        seen[steps] = seen.get(steps, 0) + 1
        return real(self)
    worldtables.TableWorld._held = held
    result = {}
    for name in GOLDENS:
        seen.clear()
        played = rerun.replay(rerun.golden(name))
        result[name] = {"matched": played["matched"], "of": played["of"], "parted": played["parted"], "loads": dict(sorted(seen.items()))}
    Path(out).write_text(json.dumps(result), encoding="utf-8")


if len(sys.argv) > 1 and sys.argv[1] == "--count":       # before the stand-in model is put in: a replay brings its own
    count(*sys.argv[2:4])
    sys.exit(0)

import simlib
simlib.install(simlib.Stub("warrior", 3))

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


from engine import pulse, worldstate

g = simlib.campaign("narrow_641", seed=3, location="trading_square")
store = g.store
seam = store._world
NOW = 1000
WORLD = {
    "seq": 9, "last": NOW,
    "threads": [{"id": "t1", "title": "A quarrel over a well", "status": "active", "place": "parth"},
                {"id": "t2", "title": "The mill wheel", "status": "resolved", "place": "parth"},
                {"id": "t3", "title": "No status at all", "place": "amaranth"},
                {"id": "t4", "title": "An empty status", "status": "", "place": "parth"},
                {"id": "t5", "title": "Wolves on the road", "status": "active", "place": "kings_pass"}],
    "deeds": [{"seq": 1, "minute": 10, "kind": "found", "place": "parth", "by": "player"},
              {"seq": 2, "minute": 500, "kind": "kill", "place": "kings_pass", "by": "second"},
              {"seq": 3, "minute": 500.5, "kind": "settled", "place": "parth", "by": "player"},
              {"seq": 4, "minute": 999, "kind": "found", "place": "parth"},
              {"seq": 5, "minute": 1000, "kind": "gift", "place": "parth", "by": "player"}],
    "news": [{"text": "Élan the miller is ill.", "place": "parth", "minute": 3}, {"text": "The pass is open.", "place": "kings_pass", "minute": 700, "origin": "pulse"}],
    "effects": [{"kind": "prices", "place": "parth", "value": 20, "until": 5000, "good": "salt"},
                {"kind": "prices", "place": "parth", "value": 10, "until": 5000},
                {"kind": "prices", "place": "parth", "value": 5, "until": 1000},
                {"kind": "prices", "place": "parth", "value": 7, "until": 1000.5},
                {"kind": "danger", "place": "kings_pass", "value": 25, "until": 3000, "thread": "t5"},
                {"kind": "closed", "place": "guild_house", "value": 0, "until": 3000, "text": "Shut for the count.", "cause": "flood"},
                {"kind": "closed", "place": "guild_house", "value": 0, "until": 4000, "text": "Barred.", "cause": "improvised"}],
    "history": [{"text": "It began.", "minute": 1}], "spawns": []}
store.save_world_state(json.loads(json.dumps(WORLD)))

EFFECT_ASKS = [(k, p, t, good) for k, p, good in (("prices", "parth", ""), ("prices", "parth", "salt"), ("prices", "parth", "bread"),
                                                  ("danger", "kings_pass", ""), ("closed", "guild_house", ""), ("prices", "nowhere", ""),
                                                  ("nothing", "parth", ""))
               for t in (0, 999, 1000, 1000.2, 1001, 2999, 3000, 3999, 4000, 4999, 5000, 9999)]
THREAD_ASKS = [None, "active", "resolved", "fallen", ""]
DEED_ASKS = [(m, k) for m in (0, 10, 11, 500, 500.2, 500.5, 501, 999, 1000, 1001) for k in (None, ("found",), ["settled", "kill"], ())]


def answers(world) -> dict:
    return {"effects": [world.effects_at(k, p, t, good) for k, p, t, good in EFFECT_ASKS], "threads": [world.threads(s) for s in THREAD_ASKS],
            "deeds": [world.deeds_since(m, k) for m, k in DEED_ASKS], "news": world.news()}


def filtered(state) -> dict:
    return {"effects": [effects_matching(state, t, k, p, good) for k, p, t, good in EFFECT_ASKS], "threads": [threads_matching(state, s) for s in THREAD_ASKS],
            "deeds": [deeds_matching(state, m, k) for m, k in DEED_ASKS], "news": news_matching(state)}


# ---- no whole world is loaded
class Loaded(Exception):
    pass


def no_load(self, *a, **k):
    raise Loaded("the whole world was loaded")


real = {name: getattr(worldtables.TableWorld, name) for name in ("load", "_state", "_held")}


def fenced(fn):
    """What fn returns with every way to the whole world shut, or the error."""
    for name in real:
        setattr(worldtables.TableWorld, name, no_load)
    try:
        return fn()
    except Loaded as e:
        return e
    finally:
        for name, was in real.items():
            setattr(worldtables.TableWorld, name, was)


want = filtered(WORLD)
got = fenced(lambda: answers(seam))
check("the four readers answer with the whole load shut", isinstance(got, dict), got)
got = got if isinstance(got, dict) else answers(seam)
check("...the effects at a place, as the filter over the whole world answers, the edges with them",
      got["effects"] == want["effects"] and sum(1 for x in want["effects"] if x) >= 20,
      next(((a, x, y) for a, x, y in zip(EFFECT_ASKS, got["effects"], want["effects"]) if x != y), None))
check("...the matters by status, and all of them in their order", got["threads"] == want["threads"] and [len(x) for x in want["threads"]] == [5, 2, 1, 0, 1],
      [len(x) for x in got["threads"]])
check("...the deeds since a minute, a minute that is not whole among them", got["deeds"] == want["deeds"] and sum(1 for x in want["deeds"] if x) >= 20,
      next(((a, x, y) for a, x, y in zip(DEED_ASKS, got["deeds"], want["deeds"]) if x != y), None))
check("...and the news, oldest first", got["news"] == want["news"] == WORLD["news"])
check("the game's way to them answers the same (engine/worldstate.py)", worldstate.effects_at(store, "prices", "parth", 999, "salt") == want["effects"][EFFECT_ASKS.index(("prices", "parth", 999, "salt"))]
      and worldstate.threads(store, "active") == want["threads"][1] and worldstate.deeds_since(store, 500, ("kill",)) == [WORLD["deeds"][1]]
      and worldstate.news(store) == WORLD["news"])

# ---- one statement, one table, by its index
asked = []
store._db.set_trace_callback(asked.append)
runs = {}
for label, fn in (("effects", lambda: seam.effects_at("prices", "parth", 999, "salt")), ("threads", lambda: seam.threads("active")),
                  ("every thread", lambda: seam.threads()), ("deeds", lambda: seam.deeds_since(500)), ("news", lambda: seam.news())):
    del asked[:]
    fn()
    runs[label] = list(asked)
store._db.set_trace_callback(None)
TABLE = {"effects": "effects", "threads": "threads", "every thread": "threads", "deeds": "deeds", "news": "news"}
check("each reader asks one statement, of its own table and no other",
      all(len(v) == 1 and f'"{TABLE[k]}"' in v[0] and "kv" not in v[0] and sum(f'"{t}"' in v[0] for t in worldtables.LISTS) == 1 for k, v in runs.items()), runs)


def plan(sql: str) -> str:
    return " | ".join(str(r[-1]) for r in store._db.execute("EXPLAIN QUERY PLAN " + sql.replace("?", "0")))


INDEX = {"effects": "effects_where", "threads": "threads_status", "deeds": "deeds_minute"}
plans = {k: plan(runs[k][0]) for k in INDEX if len(runs.get(k, [])) == 1}
check("the three that ask by something find it by their table's index", len(plans) == 3 and all(INDEX[k] in plans[k] for k in plans), plans)

# ---- a list that is absent, empty or not a list; no world at all
for label, state in (("a world with none of the lists", {"seq": 1, "history": []}),
                     ("a world whose lists are empty", {"threads": [], "deeds": [], "news": [], "effects": []}),
                     ("a world saved after a full one, with fewer", {"threads": WORLD["threads"][:1], "news": WORLD["news"][1:], "effects": WORLD["effects"][4:], "deeds": []})):
    store.save_world_state(json.loads(json.dumps(WORLD)))
    store.save_world_state(json.loads(json.dumps(state)))
    got = fenced(lambda: answers(seam))
    check(f"{label}: the readers answer what the filter does", got == filtered(state), got if not isinstance(got, dict) else "they differ")
bare = simlib.campaign("narrow_641_bare", seed=4)
got = fenced(lambda: answers(bare.store._world))
check("a save with no world answers nothing, and loads none", got == filtered({}) and bare.store._kv_text(worldtables.KEY) is None, got)

# ---- inside a transaction, and after one is taken back
store.save_world_state(json.loads(json.dumps(WORLD)))
more = json.loads(json.dumps(WORLD))
more["effects"].append({"kind": "danger", "place": "parth", "value": 40, "until": 9000})
more["news"].append({"text": "Never happened.", "place": "parth", "minute": 999})
try:
    with store.transaction():
        store.save_world_state(more)
        inside = (seam.effects_at("danger", "parth", NOW), len(seam.news()))
        raise RuntimeError("the step did not stand")
except RuntimeError:
    pass
check("a reader sees what its own transaction wrote, and none of it once the transaction is taken back",
      inside == ([more["effects"][-1]], 3) and seam.effects_at("danger", "parth", NOW) == [] and len(seam.news()) == 2, inside)

# ---- the game's four askers
world = g.session.world
town = pulse.town_of(world, "trading_square")
shop = json.loads(json.dumps(WORLD))
shop["effects"].append({"kind": "prices", "place": town, "value": 30, "until": 9000})
store.save_world_state(shop)
got = fenced(lambda: (pulse.price_factor(store, world, "trading_square", NOW), pulse.danger_factor(store, "kings_pass", NOW),
                      pulse.closed_reason(store, "guild_house", NOW), pulse.closed_until(store, "guild_house", NOW)))
want_price = 1 + sum(e["value"] for e in effects_matching(shop, NOW, "prices", town)) / 100
check("a price, a danger, a place shut and until when are asked with no whole world loaded", got == (want_price, 1.25, "Shut for the count.", 3000) and want_price > 1,
      (got, want_price))

# ---- a save still on its rows
import rows_v16
old = rows_v16.opened("narrow_641_row")
old.save_world_state(json.loads(json.dumps(WORLD)))
check("a save on its rows is answered by the filter over its one row, as before", type(old._world) is worldrow.RowWorld and answers(old._world) == filtered(WORLD))
old.close()

# ---- the kept recordings: the whole world is loaded no more often on any input, and less often over the play
def apart(how: str) -> dict:
    out = Path("saves") / f"narrow_641_{how}.json"
    done = subprocess.run([sys.executable, __file__, "--count", how, str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env={**os.environ, "PYTHONUTF8": "1"})
    if done.returncode != 0 or not out.exists():
        raise RuntimeError(f"the {how} count failed:\n{done.stdout[-1500:]}\n{done.stderr[-3000:]}")
    got = json.loads(out.read_text(encoding="utf-8"))
    out.unlink(missing_ok=True)
    return got


with ThreadPoolExecutor(2) as pool:
    before, after = pool.map(apart, ("filters", "tables"))
for name in GOLDENS:
    b, a = before[name], after[name]
    check(f"{name} replays whole both ways", a["parted"] is None and b["parted"] is None and a["matched"] == a["of"] == b["matched"] > 0, (a["parted"], b["parted"]))
    rose = {k: (b["loads"].get(k, 0), v) for k, v in a["loads"].items() if v > b["loads"].get(k, 0)}
    tb, ta = sum(b["loads"].values()), sum(a["loads"].values())
    fell = sum(1 for k, v in b["loads"].items() if a["loads"].get(k, 0) < v)
    print(f"     {name}: the whole world loaded {tb} times with the readers as filters, {ta} now; fewer on {fell} of its {a['of']} inputs")
    check(f"{name}: no input loads the whole world more often than it did", not rose and ta <= tb, rose)
total = [sum(sum(x[name]["loads"].values()) for name in GOLDENS) for x in (before, after)]
check(f"over the three the whole world is loaded less often ({total[0]} times before, {total[1]} now)", total[1] < total[0], total)

g.session.close()
bare.session.close()
for name in ("narrow_641", "narrow_641_bare", "narrow_641_row"):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
