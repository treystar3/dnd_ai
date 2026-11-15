"""(f637) The world's tables, built and proven, not yet used (docs/design/20_phase3_plan.md; docs/design/13; storage/worldtables.py).
The world's state is one JSON row, read and written whole. TableWorld answers the same seam (storage/worldrow.py) with the
matters, the deeds, the news and the effects each kept as the rows of a table, and every other key left in the row. Held here:
- nothing uses it yet: a save is version 16, its world is the row's, and a new save has none of the four tables;
- what is loaded is what the row would load, whatever was saved: keys in their order, a list that is absent, empty or not a
  list, no row at all;
- a row's json is the list's item as the row kept it, and its columns are read from it; an old item without a field gets the
  column's default and keeps its json, and a deed that names nobody is the save's first character's;
- a save writes the rows that differ and no others, and always the row of the other keys;
- any run of edits to the four lists (a seeded thousand) loads as the row's does, with the tables' columns true to their json;
- a transaction that wrote all four lists and failed leaves every table and the row as they were, byte for byte;
- the stale-save detector notes what it noted over the row;
- the campaign's check names a column that is not what its json says;
- the seeded world script played over the row and over the tables, a process each, holds the same world after every step, the
  same other tables, the same lines shown, operations and model calls, and wrote at the same steps;
- the saves kept for the migration to be tested on (data/replay/saves_v16) are version 16 and load the same from the tables.
tools/sim/worldtables_caps_637_test.py holds the caps over a thousand days.
Run: python tools/sim/worldtables_637_test.py"""
import json
import random
import shutil
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
sys.path.insert(0, "tools/sim")
import world_script
import rows_v16
from core.models import Character
from storage import invariants, migrations, worldrow, worldtables
from storage.campaign import DB_NAME, CampaignStore

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

KEY = worldrow.RowWorld.KEY
LISTS = worldtables.LISTS
MADE = []


def scratch(name: str) -> CampaignStore:
    """(f640) A new save put back as version 16 kept it: the row's side of every comparison here, and what `adopt` is tried on."""
    MADE.append(name)
    return rows_v16.opened(name)


def tables(store) -> set:
    return {r[0] for r in store._db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def rows(store, name: str) -> list[tuple]:
    """A table as it is held: every column of every row, in the order of the list."""
    return [tuple(r) for r in store._db.execute(f'SELECT * FROM "{name}" ORDER BY ord')]


def raw(store) -> dict:
    return {**{name: rows(store, name) for name in LISTS}, "row": store._kv_text(KEY)}


def texts(store, name: str) -> list[str]:
    return [r[-1] for r in rows(store, name)]


# ---- (f640) in use: a save has the tables, and one put back is the row
plain = scratch("worldtables_637_plain")
shutil.rmtree("saves/worldtables_637_live", ignore_errors=True)
MADE.append("worldtables_637_live")
live = CampaignStore.open_or_create("worldtables_637_live")
check("a save is version 17 and its world is the tables'; one put back is version 16, its world the one row, with none of the four",
      migrations.CURRENT == 17 and live.version == 17 and type(live._world) is worldtables.TableWorld and set(LISTS) <= tables(live)
      and plain.version == 16 and type(plain._world) is worldrow.RowWorld and not tables(plain) & set(LISTS),
      (migrations.CURRENT, type(live._world).__name__, type(plain._world).__name__, tables(plain)))
live.close()
check("the four lists are the matters, the deeds, the news and the effects", LISTS == ("threads", "deeds", "news", "effects"), LISTS)

# ---- the tables put under a store
row, tab = scratch("worldtables_637_row"), scratch("worldtables_637_tab")
early = {"last": 7, "news": [{"text": "old news", "origin": "parth", "minute": 5}], "threads": [], "seq": 2}
for s in (row, tab):
    s.save_world_state(json.loads(json.dumps(early)))
world = worldtables.adopt(tab)
check("adopting a save makes the four tables and puts its world on them", set(LISTS) <= tables(tab) and tab._world is world
      and type(world) is worldtables.TableWorld, (tables(tab), type(tab._world).__name__))
check("...with the lists the row held moved into them, and the same world loaded", texts(tab, "news") == [json.dumps(early["news"][0])]
      and json.dumps(tab.load_world_state()) == json.dumps(row.load_world_state()) == json.dumps(early), (raw(tab), tab.load_world_state()))
check("...and adopting it again changes nothing", (raw(tab), worldtables.adopt(tab) is not None)[0] == raw(tab))


def both(state) -> tuple[str, str]:
    """This state saved in both stores, and what each loads, as text."""
    for s in (row, tab):
        s.save_world_state(json.loads(json.dumps(state)))
    return json.dumps(row.load_world_state()), json.dumps(tab.load_world_state())


def agree(state) -> bool:
    a, b = both(state)
    return a == b == json.dumps(state)


THREAD = {"id": "th1", "title": "Cut off at Amaranth", "tier": "normal", "place": "amaranth", "status": "active", "made": 400,
          "stages": [{"description": "The summer shut the Jade Way.", "effects": [{"kind": "closed", "place": "amaranth"}]}]}
DEED = {"kind": "found", "minute": 420, "place": "trading_square", "thread": "th1", "by": "second", "seq": 9}
NEWS = {"text": "The Jade Way is shut, they say: “no carts”.", "origin": "tilted_plough", "minute": 430, "groups": ["parth_locals"],
        "certainty": "they say", "thread": "th1"}
EFFECT = {"kind": "danger", "place": "kings_pass", "value": 25, "until": 9000, "cause": "Parth: the watch and the guild", "thread": "th1"}
FULL = {"last": 440, "threads": [THREAD], "news": [NEWS], "history": [{"text": "Something happened.", "place": "parth", "minute": 3}],
        "effects": [EFFECT], "cooldowns": {"parth": 9}, "campaign": "", "deeds": [DEED], "spawns": [], "seq": 9}

# ---- what is loaded is what the row would load
check("a world with all four lists loads as the row's does, keys in their order", agree(FULL), both(FULL))
held = json.loads(tab._kv_text(KEY))
check("...the row keeps every other key, and a marker where each list stood", list(held) == list(FULL)
      and all(held[k] == FULL[k] for k in FULL if k not in LISTS) and all(held[k] == worldtables.marker(k) for k in LISTS)
      and "Jade Way" not in tab._kv_text(KEY).replace(FULL["history"][0]["text"], ""), held)
check("the lists in another order, among other keys", agree({"seq": 1, "effects": [EFFECT], "x": {"deeds": [1]}, "deeds": [DEED], "news": [NEWS, NEWS],
                                                          "threads": [THREAD], "last": 2}))
check("a list that is absent has no marker and no rows, and is absent when loaded", agree({"last": 3, "threads": [THREAD]})
      and list(json.loads(tab._kv_text(KEY))) == ["last", "threads"] and [len(rows(tab, n)) for n in LISTS] == [1, 0, 0, 0], raw(tab))
check("a list that is empty is loaded empty", agree({"deeds": [], "news": [], "threads": [], "effects": [], "last": 4})
      and tab.load_world_state()["news"] == [] and [len(rows(tab, n)) for n in LISTS] == [0, 0, 0, 0])
check("something that is not a list under a list's key stays in the row as it is", agree({"news": None, "deeds": {"a": 1}, "threads": "none", "effects": 0})
      and [len(rows(tab, n)) for n in LISTS] == [0, 0, 0, 0], raw(tab))
check("items that are not records are kept as they are", agree({"news": ["a line", 3, None, [1, 2], {"text": "x"}], "deeds": [[], {}]}))
check("an empty world is an empty world", agree({}) and not tab.load_world_state())
bare = scratch("worldtables_637_bare")
worldtables.adopt(bare)
check("a save with no world row loads an empty world, and adopting it writes none", bare.load_world_state() == {} and not bare.load_world_state()
      and bare._kv_text(KEY) is None, bare._kv_text(KEY))

# ---- a row's json is the item as the row kept it; its columns are read from it
agree(FULL)
check("a row's json is the list's item as the row would have written it", all(texts(tab, n) == [json.dumps(x) for x in FULL[n]] for n in LISTS), raw(tab))
check("a matter's columns: its id, its status, its place", [r[1:-1] for r in rows(tab, "threads")] == [("th1", "active", "amaranth")], rows(tab, "threads"))
check("a deed's: its number, its minute, its kind, who did it, where", [r[1:-1] for r in rows(tab, "deeds")] == [(9, 420, "found", "second", "trading_square")],
      rows(tab, "deeds"))
check("a piece of news': its minute, where it began, its matter", [r[1:-1] for r in rows(tab, "news")] == [(430, "tilted_plough", "th1")], rows(tab, "news"))
check("an effect's: its kind, its place, when it ends, its matter", [r[1:-1] for r in rows(tab, "effects")] == [("danger", "kings_pass", 9000, "th1")],
      rows(tab, "effects"))
FIRST = Character.model_fields["id"].default
OLD = {"threads": [{"id": "t0", "title": "An old matter"}], "deeds": [{"kind": "start", "minute": 0, "place": "parth"}, {"kind": "slew", "minute": 5.0, "seq": 2}],
       "news": [{"text": "old news"}], "effects": [{"kind": "prices", "place": "parth", "value": 2, "until": 50, "cause": "A poor harvest"}]}
check("items from older saves, without a field a column reads, load as the row's do", agree(OLD), both(OLD))
check("...each keeps its json, and its column has the default: no place or status, no number, no matter",
      all(texts(tab, n) == [json.dumps(x) for x in OLD[n]] for n in LISTS) and [r[1:-1] for r in rows(tab, "threads")] == [("t0", "", "")]
      and [r[1:-1] for r in rows(tab, "news")] == [(0, "", "")] and [r[1:-1] for r in rows(tab, "effects")] == [("prices", "parth", 50, "")], raw(tab))
check("...and a deed that names nobody is the save's first character's", [r[1:-1] for r in rows(tab, "deeds")] == [(0, 0, "start", FIRST, "parth"),
                                                                                                                   (2, 5, "slew", FIRST, "")]
      and worldtables.FIRST == FIRST == "player", rows(tab, "deeds"))
check("the columns are what derive() reads, for every table", all(r[1:-1] == worldtables.derive(n, json.loads(r[-1])) for n in LISTS for r in rows(tab, n)))
ODD = {"deeds": [{"kind": "k", "minute": True, "seq": 3.9}, {"kind": "k", "minute": "7", "seq": float("nan")}, {"kind": 5, "by": ["a"], "place": None}]}
check("a field of the wrong kind keeps its json and gives the column's default: a yes for a number, a number as text, a list for a name",
      agree(ODD) and [r[1:-1] for r in rows(tab, "deeds")] == [(3, 0, "k", FIRST, ""), (0, 0, "k", FIRST, ""), (0, 0, "", FIRST, "")], rows(tab, "deeds"))


def plan(store, sql: str) -> str:
    return " | ".join(str(r[-1]) for r in store._db.execute("EXPLAIN QUERY PLAN " + sql, (1,) * sql.count("?")))


ASKED = {"threads_status": "SELECT json FROM threads WHERE status = ?", "deeds_minute": "SELECT json FROM deeds WHERE minute >= ?",
         "effects_where": "SELECT json FROM effects WHERE kind = ? AND place = ? AND until > ?"}
check("what a narrow reader asks by is found by an index: a matter's status, a deed's minute, an effect's kind and place while it lasts",
      all(name in plan(tab, sql) for name, sql in ASKED.items()) and set(ASKED) == set(worldtables.INDEXES), {n: plan(tab, s) for n, s in ASKED.items()})


# ---- a save writes the rows that differ, and always the row
def written(state) -> tuple[int, int]:
    """Rows of the four tables written by this save, and statements the store counted."""
    w0, s0 = world.written, tab._writes
    tab.save_world_state(state)
    return world.written - w0, tab._writes - s0


def news(n: int, start: int = 0) -> list[dict]:
    return [{"text": f"news {i}", "origin": "parth", "minute": i} for i in range(start, start + n)]


base = {"last": 1, "news": news(50), "deeds": [dict(DEED, seq=i) for i in range(40)], "threads": [dict(THREAD, id=f"t{i}") for i in range(12)],
        "effects": [dict(EFFECT, until=100 + i) for i in range(6)]}
tab.save_world_state(base)
same = written(json.loads(json.dumps(base)))
check("a world saved as it stands writes no row of any table, and still the row of the other keys (an operation that saved the world has written)",
      same[0] == 0 and same[1] >= 1, same)
cases = {}
st = json.loads(json.dumps(base)); st["news"].append({"text": "one more", "origin": "parth", "minute": 99})
cases["one more at the end"] = (written(st)[0], 1)
st["threads"][3]["status"] = "resolved"
cases["one changed where it stands"] = (written(st)[0], 1)
del st["deeds"][:3]; st["deeds"].append(dict(DEED, seq=77))
cases["three dropped from the head and one added"] = (written(st)[0], 4)
st["news"].append(st["news"].pop(20))
cases["one moved from the middle to the end"] = (written(st)[0], 2)
del st["news"][10]
cases["one taken from the middle"] = (written(st)[0], 1)
del st["effects"][2]; st["effects"][0]["until"] = 5; st["effects"].append(dict(EFFECT, until=999))
cases["one lifted, one dropped, one laid"] = (written(st)[0], 3)
check("a save writes the rows that differ and no others", all(got == want for got, want in cases.values()), cases)
check("...and the world still loads as saved, the tables in the lists' order", json.dumps(tab.load_world_state()) == json.dumps(st)
      and all(texts(tab, n) == [json.dumps(x) for x in st[n]] for n in LISTS))
st["news"].insert(5, {"text": "put in the middle", "origin": "parth", "minute": 1})
w = written(st)[0]
check("an item put in before others is written with those after it, and loads in its place", 1 <= w <= len(st["news"]) - 5
      and json.dumps(tab.load_world_state()) == json.dumps(st), w)
st["news"] = news(30, start=500)
check("a list replaced whole is written whole", written(st)[0] >= 30 and json.dumps(tab.load_world_state()) == json.dumps(st))
alike = ["a line", "another"] * 150                      # a long list of items that are many times the same
st["news"] = [{"text": "the first"}] + alike
tab.save_world_state(st)
st["news"] = alike + [{"text": "the last"}]
w = written(st)[0]
check("in a long list of items many times the same, the head dropped and one added is still two rows", w == 2
      and json.dumps(tab.load_world_state()) == json.dumps(st), w)
was = {r[-1]: r[0] for r in rows(tab, "deeds")}
del st["deeds"][:2]; st["deeds"].append(dict(DEED, seq=78))
tab.save_world_state(st)
now = {r[-1]: r[0] for r in rows(tab, "deeds")}
check("a row that stands keeps its number, and a new one's is above them all", len(now) == len(was) - 1 and max(now.values()) > max(was.values())
      and all(now[t] == was[t] for t in now if t in was) and len([t for t in now if t not in was]) == 1, (sorted(was.values())[-3:], sorted(now.values())[-3:]))

# ---- any run of edits loads as the row's does
rng = random.Random(637)
state = json.loads(json.dumps(base))
both(state)
ITEM = {"threads": lambda i: dict(THREAD, id=f"r{i}", status=rng.choice(("active", "resolved", "fallen")), place=rng.choice(("parth", "amaranth"))),
        "deeds": lambda i: dict(DEED, seq=i, minute=rng.randrange(5000), kind=rng.choice(("found", "slew", "gave"))),
        "news": lambda i: {"text": f"news {i} “ü”", "origin": rng.choice(("parth", "")), "minute": rng.randrange(5000), **({"thread": f"r{i}"} if i % 3 else {})},
        "effects": lambda i: dict(EFFECT, until=rng.randrange(9000), kind=rng.choice(("danger", "prices", "closed")), place=rng.choice(("parth", "kings_pass")))}
OTHER = worldrow.effects_matching, worldrow.threads_matching, worldrow.deeds_matching, worldrow.news_matching
wrong, kinds = [], set()
for step in range(1000):
    name = rng.choice(LISTS)
    cur = state.get(name)
    edit = rng.choice(("append", "append", "append", "head", "middle", "change", "insert", "move", "swap", "clear", "absent", "all", "other", "same"))
    if not isinstance(cur, list):
        edit = "all"
    if edit == "append":
        cur.append(ITEM[name](step))
    elif edit == "head":
        del cur[:rng.randrange(4)]
    elif edit == "middle" and cur:
        del cur[rng.randrange(len(cur))]
    elif edit == "change" and cur:
        cur[rng.randrange(len(cur))] = dict(cur[rng.randrange(len(cur))], changed=step)
    elif edit == "insert":
        cur.insert(rng.randrange(len(cur) + 1), ITEM[name](step))
    elif edit == "move" and cur:
        cur.append(cur.pop(rng.randrange(len(cur))))
    elif edit == "swap" and len(cur) > 1:
        i, j = rng.randrange(len(cur)), rng.randrange(len(cur))
        cur[i], cur[j] = cur[j], cur[i]
    elif edit == "clear":
        cur.clear()
    elif edit == "absent" and step % 7 == 0:
        state.pop(name)
    elif edit == "all":
        state[name] = [ITEM[name](step * 100 + k) for k in range(rng.randrange(60))]
    elif edit == "other":
        state["last"] = step
        state[f"k{step % 5}"] = {"n": step}
    kinds.add(edit)
    a, b = both(state)
    now = rng.randrange(9000)
    readers = (world.effects_at("danger", "parth", now) == OTHER[0](state, now, "danger", "parth") and world.threads("active") == OTHER[1](state, "active")
               and world.threads() == OTHER[1](state) and world.deeds_since(now, ("found",)) == OTHER[2](state, now, ("found",)) and world.news() == OTHER[3](state))
    tabled = all(texts(tab, n) == [json.dumps(x) for x in (state.get(n) if isinstance(state.get(n), list) else [])] for n in LISTS)
    if not (a == b == json.dumps(state) and readers and tabled) or (step % 50 == 0 and worldtables.problems(tab)):
        wrong.append((step, name, edit, a == b, readers, tabled, worldtables.problems(tab)[:2]))
        break
check("a thousand seeded edits of the four lists: each loads as the row's does, the tables hold the lists, the narrow readers answer as the filters do",
      not wrong and len(kinds) == 12 and worldtables.problems(tab) == [], (wrong, sorted(kinds)))

# ---- a failed transaction leaves all of it as it was
both(FULL)
before = raw(tab)
try:
    with tab.transaction():
        tab.save_world_state({"last": 999, "threads": [THREAD, dict(THREAD, id="never")], "deeds": [], "news": news(9), "effects": [EFFECT, EFFECT], "more": 1})
        inside = raw(tab)
        raise RuntimeError("the operation did not stand")
except RuntimeError:
    pass
check("a transaction that wrote all four lists and failed leaves every table and the row byte for byte as they were", inside != before and raw(tab) == before
      and all(inside[n] != before[n] for n in LISTS), [n for n in before if raw(tab)[n] != before[n]])
def no_disk(key, text):
    raise OSError("the row could not be written")


tab._put = no_disk                                       # the tables' rows are written, and then the row is not
try:
    tab.save_world_state({"last": 1000, "threads": [dict(THREAD, id="half")], "deeds": [DEED, DEED], "news": [], "effects": [EFFECT, EFFECT]})
    failed = False
except OSError:
    failed = True
del tab._put
check("a save that fails part way, with no transaction open around it, leaves every table and the row as they were", failed and raw(tab) == before,
      [n for n in before if raw(tab)[n] != before[n]])


def caught_inside(store) -> tuple[str, int]:
    """A save that cannot be written, of a copy held across another's write, caught by its caller inside a transaction that stands."""
    store.save_world_state(json.loads(json.dumps(FULL)))
    del store._world.stale[:]
    held, other = store.load_world_state(), store.load_world_state()
    other["last"] = 31
    store.save_world_state(other)
    held["threads"] = [dict(THREAD, id="half")]
    held["effects"] = [{"kind": "k", "until": object()}]
    with store.transaction():
        try:
            store.save_world_state(held)
        except TypeError:
            pass
    return json.dumps(store.load_world_state()), len(store._world.stale)


check("a save that cannot be written, caught inside a transaction that then stands, wrote nothing and noted nothing, as over the row",
      caught_inside(tab) == caught_inside(row) == (json.dumps(dict(FULL, last=31)), 0), (caught_inside(tab), caught_inside(row)))


# ---- the stale-save detector notes what it noted over the row
def held_across(store) -> list[str]:
    del store._world.stale[:]
    first = store.load_world_state()
    second = store.load_world_state()
    second["last"] = 12345
    store.save_world_state(second)
    fresh = store.load_world_state()
    fresh["last"] = 5
    store.save_world_state(fresh)                         # loaded after the write: nothing to note
    store.save_world_state(first)                         # a copy held across another's write, saved over it
    return [s["site"] for s in store._world.stale]


check("a copy held across another write and saved over it is noted, with the function that saved it, over the tables as over the row",
      held_across(tab) == held_across(row) == ["tools.sim.worldtables_637_test:held_across"], (held_across(tab), held_across(row)))


def own_then_a_list(store) -> list:
    del store._world.stale[:]
    mine = store.load_world_state()
    mine["last"] = 77
    store.save_world_state(mine)
    mine["deeds"] = mine["deeds"] + [dict(DEED, seq=77)]
    store.save_world_state(mine)                          # its own copy, saved twice running: nothing to note
    quiet = len(store._world.stale)
    first = store.load_world_state()
    other = store.load_world_state()
    other["deeds"][0] = dict(other["deeds"][0], minute=1)     # another's write that changes one item of one list and no other key
    store.save_world_state(other)
    store.save_world_state(first)
    return [quiet] + [s["site"] for s in store._world.stale]


check("...a copy saved twice running is its own and is not noted; one held across a write to a single list's item is",
      own_then_a_list(tab) == own_then_a_list(row) == [0, "tools.sim.worldtables_637_test:own_then_a_list"], (own_then_a_list(tab), own_then_a_list(row)))
worldrow.WATCH_STALE = False
check("...and in shipped play, where nothing watches, a plain dict is loaded", type(tab.load_world_state()) is dict and type(bare.load_world_state()) is dict)
worldrow.WATCH_STALE = True

# ---- the campaign's check
both(FULL)
check("the campaign's check finds nothing wrong with a world in its tables, nor with one in its row", worldtables.problems(tab) == []
      and worldtables.problems(plain) == [] and not [p for p in invariants.validate_campaign(tab) if "table" in str(p)], worldtables.problems(tab))
tab._db.execute("UPDATE deeds SET kind = 'slew' WHERE ord = (SELECT MIN(ord) FROM deeds)")
found = worldtables.problems(tab)
check("a column that is not what its json says is named", len(found) == 1 and "deeds" in found[0] and "kind" in found[0]
      and any(found[0] in str(p) for p in invariants.validate_campaign(tab)), found)
both(dict(FULL, deeds=[dict(DEED, seq=10)]))
tab._db.execute("INSERT INTO effects (ord, kind, place, until, thread, json) VALUES (999, 'x', 'y', 1, '', 'not json')")
tab._put(KEY, json.dumps({k: v for k, v in json.loads(tab._kv_text(KEY)).items() if k != "news"}))
found = worldtables.problems(tab)
check("...and so is a row whose json cannot be read, and rows of a list the world does not hold", len(found) == 2
      and any("effects" in p for p in found) and any("news" in p for p in found), found)
both(FULL)
check("(a save puts it right)", worldtables.problems(tab) == [], worldtables.problems(tab))
good = tab._kv_text(KEY)
tab._put(KEY, "{not a world")
found = worldtables.problems(tab)
check("a world's row that cannot be read is named, not raised", len(found) == 1 and "row" in found[0], found)
tab._put(KEY, good)

# ---- the seeded world script, over the row and over the tables
with ThreadPoolExecutor(2) as pool:                      # each play in a process of its own (the stand-in model counts what it invents)
    a, b = pool.map(lambda args: world_script.run_apart(*args), (("worldtables_637_play_row", world_script.SEED, ("--world", "row")),
                                                                 ("worldtables_637_play_tab", world_script.SEED, ())))
MADE.extend(("worldtables_637_play_row", "worldtables_637_play_tab"))
check("the script was played over the row, and over the tables", (a["world"], b["world"]) == ("RowWorld", "TableWorld"), (a.get("world"), b.get("world")))
check("...the same steps, and every part of the script's coverage met over each", len(a["steps"]) > 20 and [s[0] for s in a["steps"]] == [s[0] for s in b["steps"]]
      and all(a["cover"].values()) and a["cover"] == b["cover"] and len(a["cover"]) >= 15, {k: (v, b["cover"].get(k)) for k, v in a["cover"].items() if not (v and b["cover"].get(k))})
part = next((i for i, (x, y) in enumerate(zip(a["steps"], b["steps"])) if x[1] != y[1]), None)
check("after every step the loaded world is the same, as text, keys and lists in their order", part is None,
      part is not None and (a["steps"][part][0], world_script.first_difference(a["steps"][part][1], b["steps"][part][1])))
check("every other table of the save holds the same", all(a["other"][t] == b["other"][t] for t in a["other"] if t not in ("kv", "all", *LISTS)) and len(a["other"]) >= 7,
      [t for t in a["other"] if a["other"][t] != b["other"][t]])
check("...and so does every other row of the small ones", a["rest"] == b["rest"])
check("...the player's record among them, the same text at the end", a["player"] == b["player"] and len(a["player"] or "") > 1000,
      world_script.first_difference(a["player"] or "{}", b["player"] or "{}"))
check("the same lines were shown", a["shown"] == b["shown"] and len(a["shown"]) > 5,
      next(((x, y) for x, y in zip(a["shown"], b["shown"]) if x != y), (len(a["shown"]), len(b["shown"]))))
check("the same operations stood, with the same outcomes", a["ops"] == b["ops"] and len(a["ops"]) > 3, (len(a["ops"]), len(b["ops"])))
check("the store was written at every step in both (the script has no step that leaves it alone)", a["wrote"] == b["wrote"] and all(a["wrote"])
      and len(a["wrote"]) == len(a["steps"]), [s[0] for s, x, y in zip(a["steps"], a["wrote"], b["wrote"]) if x != y])
check("neither play noted a stale save, and the model was asked the same", a["stale"] == b["stale"] == [] and a["calls"] == b["calls"], (a["stale"], b["stale"]))

# ---- the saves kept for the migration to be tested on
KEPT = Path("data/replay/saves_v16")
GOLDENS = ("stub_short", "stub_party", "stub_fight")
want = {f"{g}.db" for g in GOLDENS} | {"world_script.db"}
check("the saves kept at version 16: the three goldens' starts and the world script's end", {p.name for p in KEPT.glob("*.db")} == want,
      sorted(p.name for p in KEPT.glob("*")))
def version_of(path) -> int:
    db = sqlite3.connect(f"file:{Path(path).as_posix()}?immutable=1", uri=True)       # read where it lies: no file is made beside a kept save
    try:
        return db.execute("PRAGMA user_version").fetchone()[0]
    finally:
        db.close()


starts = {g: Path(f"data/replay/sessions/{g}/start.db") for g in GOLDENS}
still = [g for g in GOLDENS if version_of(starts[g]) == 16]         # a recording made again at a later version is no longer the kept one
check("...the goldens' are their recordings' own, byte for byte, while a recording's start is version 16",
      all((KEPT / f"{g}.db").read_bytes() == starts[g].read_bytes() for g in still if (KEPT / f"{g}.db").exists())
      and (still or migrations.CURRENT > 16), still)
lists_held = {}
for name in sorted(want):
    if not (KEPT / name).exists():
        continue
    version = version_of(KEPT / name)
    folder = Path("saves") / f"worldtables_637_kept_{Path(name).stem}"
    MADE.append(folder.name)
    kept = rows_v16.opened(folder.name, name)             # (f640) as version 16 read it: no later step run
    was = json.dumps(kept.load_world_state())
    worldtables.adopt(kept)
    lists_held[name] = [len(rows(kept, n)) for n in LISTS]
    check(f"{name} is a version 16 save, and its world loads the same from the tables", version == 16 and kept.version == 16
          and json.dumps(kept.load_world_state()) == was and worldtables.problems(kept) == [], (version, worldtables.problems(kept)))
    kept.close()
check("...the world script's end has all four lists in use", all(lists_held.get("world_script.db", [0])), lists_held)

for s in (plain, row, tab, bare):
    s.close()
for name in MADE:
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    Path(f"saves/{name}.world_script.json").unlink(missing_ok=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
