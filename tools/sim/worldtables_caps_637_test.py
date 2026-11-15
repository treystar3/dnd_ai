"""(f637) The world's tables over a thousand days (docs/design/20_phase3_plan.md; storage/worldtables.py).
A seeded world is played a thousand days, a pulse and a deed a day, once over the row and once over the tables, a process each.
Held here:
- the two hold the same world, with its order, every tenth day, and saved it the same number of times;
- each list that has a number of its own stays within it and reaches it (the deeds, the news, the finished matters), so rows did
  go out; the running matters and the effects have none (they hold what has not ended) and do not grow from the first half to the second;
- a table's rows are the list's, counted by the table and by its status column;
- a save writes the rows that differ: a handful, no more late than early, never a list over again;
- after the thousand days the tables' columns are true to their json.
Run: python tools/sim/worldtables_caps_637_test.py"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
from engine import deeds, pulse
from storage import worldtables

DAYS, SEED, EVERY, WINDOW = 1000, 11, 10, 100
PLACE = "trading_square"
HANDFUL, MOST = 20, 100              # rows a save writes: a window's mean, and any one save (a list written over again is 300)


def play(name: str, kind: str, out: str) -> None:
    """The child: the days over one kind of storage, and what was seen."""
    simlib.quiet_console()
    g = simlib.campaign(name, seed=SEED, location=PLACE)
    ws, store = g.scene, g.store
    config.TURN_LOG_PATH = f"saves/{name}/turns.jsonl"
    if kind == "tables":
        worldtables.adopt(store)
    world = store._world
    ws.enter(PLACE)
    wrote, real = [], world.save

    def save(state):
        before = getattr(world, "written", 0)
        real(state)
        wrote.append(getattr(world, "written", 0) - before)

    world.save = save
    seen, windows, mark = [], [], 0
    for day in range(1, DAYS + 1):
        store.meta.minutes += 1440
        store.save_meta()
        ws.run_pulse()
        deeds.log(store, "found", ws.minutes, PLACE, thread=f"d{day}", by=ws.acting)
        if day % EVERY == 0:
            state = store.load_world_state()
            text = json.dumps(state, ensure_ascii=False)
            at = {"day": day, "digest": hashlib.sha1(text.encode("utf-8")).hexdigest(),
                  "held": {n: len(state.get(n, [])) for n in worldtables.LISTS},
                  "finished": sum(1 for t in state.get("threads", []) if t.get("status") != "active")}
            if kind == "tables":
                at["rows"] = {n: store._db.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in worldtables.LISTS}
                at["rows_finished"] = store._db.execute("SELECT COUNT(*) FROM threads WHERE status != 'active'").fetchone()[0]
            seen.append(at)
        if day % WINDOW == 0:
            part, mark = wrote[mark:], len(wrote)
            windows.append({"day": day, "saves": len(part), "rows": sum(part), "most": max(part, default=0),
                            "row_bytes": len(store._kv_text(world.KEY) or "")})
    end = {"kind": type(world).__name__, "seen": seen, "windows": windows}
    if kind == "tables":
        end["problems"] = worldtables.problems(store)
        end["top"] = {n: store._db.execute(f'SELECT COALESCE(MAX(ord), 0) FROM "{n}"').fetchone()[0] for n in worldtables.LISTS}
    g.session.close()
    Path(out).write_text(json.dumps(end), encoding="utf-8")


if len(sys.argv) > 1 and sys.argv[1] == "--play":
    play(*sys.argv[2:5])
    sys.exit(0)

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def apart(name: str, kind: str) -> dict:
    out = Path("saves") / f"{name}.caps.json"
    done = subprocess.run([sys.executable, __file__, "--play", name, kind, str(out)], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    if done.returncode != 0 or not out.exists():
        raise RuntimeError(f"the {kind} play failed:\n{done.stdout[-1500:]}\n{done.stderr[-3000:]}")
    return json.loads(out.read_text(encoding="utf-8"))


NAMES = {"row": "worldtables_caps_637_row", "tables": "worldtables_caps_637_tab"}       # a save each: two processes never share one
with ThreadPoolExecutor(2) as pool:
    row, tab = pool.map(lambda kind: apart(NAMES[kind], kind), ("row", "tables"))

check("one play was over the row and one over the tables, a thousand days each", (row["kind"], tab["kind"]) == ("RowWorld", "TableWorld")
      and row["seen"][-1]["day"] == tab["seen"][-1]["day"] == DAYS and len(tab["seen"]) == DAYS // EVERY, (row["kind"], tab["kind"]))

# ---- the same world
apart_at = next((a["day"] for a, b in zip(row["seen"], tab["seen"]) if a["digest"] != b["digest"]), None)
check("the two hold the same world, with its order, every tenth day", apart_at is None and len(row["seen"]) == len(tab["seen"]),
      f"they part by day {apart_at}")
check("...and saved it the same number of times", [w["saves"] for w in row["windows"]] == [w["saves"] for w in tab["windows"]]
      and sum(w["saves"] for w in tab["windows"]) > DAYS, ([w["saves"] for w in row["windows"]], [w["saves"] for w in tab["windows"]]))
check("...and the world changed all the way through (the plays are not standing still)", len({a["digest"] for a in tab["seen"]}) == len(tab["seen"]))

# ---- within the caps
seen, end = tab["seen"], tab["seen"][-1]
CAPS = {"deeds": deeds.KEEP, "news": pulse.NEWS_KEEP}
for name, cap in CAPS.items():
    most = max(a["rows"][name] for a in seen)
    check(f"the {name} table never holds more than its {cap}", most <= cap, most)
    check(f"...and holds {cap} at the end, with more than twice that made (rows went out)", end["rows"][name] == cap and tab["top"][name] > 2 * cap,
          (end["rows"][name], tab["top"][name]))
most = max(a["rows_finished"] for a in seen)
check(f"the finished matters kept never pass {pulse.FINISHED_KEPT}, and reach it", most == pulse.FINISHED_KEPT == end["rows_finished"], most)
half = len(seen) // 2
for name, what in (("threads", "matters"), ("effects", "effects")):          # no number of their own: what is running, what has not run out
    early, late = max(a["rows"][name] for a in seen[:half]), max(a["rows"][name] for a in seen[half:])
    check(f"the {what} held do not grow: at most {early} in the first five hundred days, {late} in the second (half as many again would fail)",
          0 < late <= early * 1.5, (early, late))
check("a table's rows are its list's, every tenth day", all(a["rows"] == a["held"] for a in seen),
      next(((a["day"], a["rows"], a["held"]) for a in seen if a["rows"] != a["held"]), None))
check("...and the status column counts the finished as the list does", all(a["rows_finished"] == a["finished"] for a in seen))

# ---- rows written per save stay flat
wins = tab["windows"]
means = [w["rows"] / w["saves"] for w in wins]
print("     rows a save, by hundred days: " + ", ".join(f"{m:.1f}" for m in means) + f"; the most in one save {max(w['most'] for w in wins)}")
print("     the row of the other keys, bytes by hundred days: " + ", ".join(str(w["row_bytes"]) for w in wins))
check("the row's play counts no table rows, and the tables' counts some at every save's worth", all(w["rows"] == 0 for w in row["windows"])
      and all(w["rows"] > 0 for w in wins))
check(f"a save writes a handful of rows in every hundred days (under {HANDFUL} a save)", max(means) < HANDFUL, means)
early, late = sum(w["rows"] for w in wins[:5]) / sum(w["saves"] for w in wins[:5]), sum(w["rows"] for w in wins[5:]) / sum(w["saves"] for w in wins[5:])
check(f"...and does not grow: {early:.1f} a save in the first five hundred days, {late:.1f} in the second (half as many again would fail)",
      late <= early * 1.5, (early, late))
held = sum(end["rows"].values())
check(f"...and no save writes a list over again (the most {max(w['most'] for w in wins)} rows, with {held} held)",
      max(w["most"] for w in wins) < MOST < min(CAPS.values()) and held > 2 * min(CAPS.values()), (max(w["most"] for w in wins), held))
check("the row of the other keys holds none of the four lists (it is a fraction of the row's own)",
      wins[-1]["row_bytes"] * 3 < row["windows"][-1]["row_bytes"], (wins[-1]["row_bytes"], row["windows"][-1]["row_bytes"]))

# ---- still true
check("after the thousand days the tables' columns are true to their json", tab["problems"] == [], tab["problems"][:5])

for name in NAMES.values():
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    Path(f"saves/{name}.caps.json").unlink(missing_ok=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
