"""(f510) Closing Bundle E. The gate (tools/latency.py --gate) prices the three goldens at expected answers on the card's profile: no
input with a speech or a fight call dearer than before Bundle D, every input under budget.yaml limit_seconds apart from those the
pre-D baseline already priced over it (Bundle D's own debt, named), and every fight input under it. --fights writes the fight measures
to data/measured/bundle_e_fights.yaml (the required path's estimate, the fight calls by task, the operations and the re-runs, the odds'
simulations, per fight input), a measurement outside the data hash whose shape engine/data_check.py holds (fight tasks budget.yaml
knows, numbers where numbers are due). tools/purity.py PURE holds the fight's rule modules. A night summary built from the stub_fight
recording reports the fights (calls a round, p95 a task, fights let go at a load, re-runs a round). prepared_470's ratchet holds none of
the fight's tasks. Nothing stays in the process."""
import gzip
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import yaml
import card_profile
import latency
import purity
from engine import data_check

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- the gate
held = latency.gate()
check("the gate prices the three goldens: no input with a speech or a fight call dearer than before Bundle D", set(held) == {"stub_short", "stub_party", "stub_fight"}
      and all(held[g] == [] for g in held), held)
base = latency._yaml(latency.BASELINE)
over = latency.over_limit(base=base)
over_all = latency.over_limit()
limit = card_profile.budget_limit()
debt = {g: [(int(i), float(s)) for i, s in (base["estimates"].get(g) or {}).items() if float(s) > limit] for g in held}
check("every input is under the limit, apart from those the pre-D baseline already priced over it (Bundle D's own debt, named)", all(over[g] == [] for g in over)
      and all(i in {j for j, _ in debt[g]} for g in over_all for i, _ in over_all[g]) and limit == 60, (over, over_all, debt))
fights = {g: latency.fight_inputs(latency.GOLDENS / g) for g in held}
check("...and every fight input fits the minute: stub_fight's twenty, stub_short's nineteen, stub_party has none", not any(i in fights[g] for g in over_all for i, _ in over_all[g])
      and len(fights["stub_fight"]) == 20 and len(fights["stub_short"]) == 19 and fights["stub_party"] == set(), {g: len(v) for g, v in fights.items()})
check("a fight input the baseline priced over the limit would still fail the gate",
      3 in {i for i, _ in latency.over_limit(base={"estimates": {"stub_fight": {3: 99.0}}}, limit=10.0)["stub_fight"]})
check("...while a plain input the baseline priced over it is left to Bundle D", latency.over_limit(base={"estimates": {"stub_short": {1: 99.0}}}, limit=60.0)["stub_short"] == [(36, 69.3)])

# ---- the fight measures
kept = yaml.safe_load(Path("data/measured/bundle_e_fights.yaml").read_text(encoding="utf-8"))
now = latency.fights_report()
check("the fight measures are kept, outside the data hash, and read the same from the goldens today", kept["goldens"] == now and kept["fight_tasks"] == list(latency.FIGHT_TASKS)
      and kept["limit_seconds"] == limit and Path("data/measured/bundle_e_fights.yaml").parent.name == "measured", {g: [i for i in now[g] if now[g][i] != (kept["goldens"].get(g) or {}).get(i)][:3] for g in now})
known = set(yaml.safe_load(Path("data/rules/budget.yaml").read_text(encoding="utf-8"))["tasks"])
check("the measured file names only fight tasks budget.yaml knows, and its rows count only those", set(kept["fight_tasks"]) <= known
      and all(set(r["calls"]) <= set(kept["fight_tasks"]) for rows in kept["goldens"].values() for r in rows.values()) and data_check.fights_problems() == [], data_check.fights_problems())
row = kept["goldens"]["stub_fight"][3]
check("a fight's first input: the opening's call, the odds' eighty simulations, its operations, no re-run", row["calls"] == {"combat_opening": 1} and row["simulations"] == 80 and row["operations"] >= 1 and row["reruns"] == 0, row)
check("...and the measures are numbers where numbers are due: a stray task or a word is named", any("moon" in m for m in data_check.fights_problems({**kept, "fight_tasks": kept["fight_tasks"] + ["moon_call"]}))
      and any("estimate" in m for m in data_check.fights_problems({**kept, "goldens": {"stub_fight": {3: {**row, "estimate": "slow"}}}}))
      and any("counts a call" in m for m in data_check.fights_problems({**kept, "goldens": {"stub_fight": {3: {**row, "calls": {"narrate": 1}}}}}))
      and any("no such recording" in m for m in data_check.fights_problems({**kept, "goldens": {"stub_moon": {}}})))
check("the check runs at startup with the rest", "bad += fights_problems()" in Path("engine/data_check.py").read_text(encoding="utf-8") and data_check.check() == [])

# ---- purity
check("tools/purity.py PURE holds the fight's rule modules, and all of them pass", {"engine/damage.py", "engine/effects.py", "engine/stacking.py", "engine/afflictions.py",
      "engine/healing.py", "engine/relics.py", "engine/bosses.py", "engine/behaviors.py"} <= set(purity.PURE) and purity.check_all() == [], purity.check_all())

# ---- a night summary from the stub_fight recording
folder = latency.GOLDENS / "stub_fight"
calls = [{"task": c.get("task"), "turn": int(c.get("input", 0)), "seconds": float(c.get("seconds") or 0), "error": None}
         for c in card_profile.calls_of(folder) if c.get("kind") != "embed"]
turns = [{"turn": int(t["i"]), "ops": [{"id": o.get("id"), "kind": o.get("kind"), "state": "stood"} for o in t.get("operations") or []]} for t in latency.load(folder / "turns.jsonl")]
table = latency.fight_table(calls, turns, [{"where": "fight row"}])
text = "\n".join(table)
check("the night's fight measures: rounds with a fight call, calls a round, re-runs a round, fights let go, and p95 a fight task", "rounds with a fight call" in text
      and "fight calls a round" in text and "1 fights let go at a load" in text and "| combat_interpret |" in text and "| combat_narrate |" in text and "| combat_opening |" in text, table[:6])
check("...and a night with no fight says so", latency.fight_table([{"task": "narrate", "turn": 1, "seconds": 1.0}], []) == ["No fight calls."])
src = Path("tools/latency.py").read_text(encoding="utf-8")
check("summarise writes the Fights section when a run made a fight call", '"## Fights"' in src and "fight_table(calls, turns" in src)

# ---- prepared_470's ratchet holds none of the fight's tasks
ratchet = Path("tools/sim/prepared_470_test.py").read_text(encoding="utf-8")
block = ratchet[ratchet.index("RECORDED = frozenset({"):ratchet.index("})", ratchet.index("RECORDED = frozenset({"))]
names = set(re.findall(r'"([a-z_]+)"', block))
check("prepared_470 RECORDED holds none of the fight's tasks", not (names & set(latency.FIGHT_TASKS)), sorted(names & set(latency.FIGHT_TASKS)))
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
