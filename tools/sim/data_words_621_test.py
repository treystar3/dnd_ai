"""(f621) The words that stand in data/ carry no dash. f620 took the dashes out of the lines the engine keeps; the larger share of what a
model is handed with a dash was never the engine's: it stood in data/ (a place's lines, lore, a road, a role). 240 strings there held
one (docs/design/18 part G): 138 told as true, the rest labels of the game's own panes, rules for a model, marks the engine reads and
notes. Now every string in data/ is told unless data/rules/hygiene.yaml data_words names its file and key as one of those four, and
engine/data_check.py refuses a dash in a told one at startup: a new file or key is checked without being added anywhere. The 138 were
reworded once, the words kept; a pressure's description, which the engine cuts at its head and three prompts are handed whole, now
ends its head at a colon.
Run: python tools/sim/data_words_621_test.py"""
import json
import random
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools/sim")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import data_check, hygiene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


# ---- the rule, on trees it is handed: shapes the game's own files do not hold
tmp = Path("saves/data_words_621")
shutil.rmtree(tmp, ignore_errors=True)
(tmp / "world").mkdir(parents=True)
(tmp / "rules").mkdir()
(tmp / "measured").mkdir()


def tree(files: dict) -> None:
    for rel, text in files.items():
        (tmp / rel).write_text(text, encoding="utf-8", newline="\n")


def found(table: dict) -> list[str]:
    return data_check.data_words_problems(root=tmp, table={"skip": ["measured", "replay"], "not_told": table})


tree({"world/inns.yaml": "- {id: plough, sign: A plough - tilted, rooms: 4}\n- id: stag\n  sign: The white stag\n  told:\n    - Its ale is thin — its beds are not.\n"
                         "    - The cellar floods 2–3 times a year.\n  cook: {says: 'Stew -- or nothing.'}\n",
      "world/ferries.json": json.dumps({"ferries": [{"name": "the Wend ferry", "line": "It runs at dawn - and never after dark."}]}),
      "rules/odd.yaml": "names:\n  half - way: a key with a dash in it\nfine: A half-elf with well-made boots, a so-called lord.\nlist: |\n  What it holds:\n  - a first thing\n  - a second thing\n"
                        "blurb: quicken your step - your next journey takes less time\n",
      "measured/numbers.yaml": "note: measured - by a tool\n"})
got = found({})
check("a dash in a string nobody declared is refused: in a table on one line, a list, a nested table, a JSON file",
      sum("world/inns.yaml" in x for x in got) == 4 and sum("world/ferries.json" in x for x in got) == 1, got)
check("...of every kind of dash, each named with its file, its key and its words", any("sign" in x and "A plough - tilted" in x for x in got)
      and any("—" in x for x in got) and any("2–3" in x for x in got) and any("says" in x and "Stew -- or nothing." in x for x in got), got)
check("...a key with a dash in it too", any("rules/odd.yaml" in x and "half - way" in x for x in got), got)
check("...a hyphen inside a word, and a list's marks inside a string, are no dash", not any("fine" in x or "a first thing" in x for x in got), got)
check("...what a tool measured is not read", not any("measured" in x for x in got), got)
check("...a label nobody declared is refused like the rest: told is the default", any("blurb" in x for x in got) and len(got) == 7, got)
got = found({"rules/odd.yaml": {"blurb": "label", "names": "structure"}, "world/inns.yaml": {"cook.says": "rule", "told": "note"}})
check("a declared key is let through, whatever it is declared as, by its name or by its path",
      not any("rules/odd.yaml" in x for x in got) and sum("world/inns.yaml" in x for x in got) == 1 and any("sign" in x for x in got), got)
got = found({"rules/odd.yaml": {"blurb": "label", "names": "structure", "nothing": "label"}, "world/gone.yaml": {"text": "rule"},
             "world/inns.yaml": {"sign": "story"}})
check("the table itself is held: a file that is not there, a key that is not there, a kind that is none of the four",
      any("world/gone.yaml" in x for x in got) and any("nothing" in x for x in got) and any("story" in x for x in got), got)
tree({"world/new_this_year.yaml": "towers:\n  - {name: the Salt Tower, seen: Grey stone - streaked white by the gulls.}\n"})
got = found({"rules/odd.yaml": {"blurb": "label", "names": "structure"}})
check("a new file is checked without being added anywhere", any("world/new_this_year.yaml" in x and "seen" in x for x in got), got)
shutil.rmtree(tmp, ignore_errors=True)

# ---- the game's own data
T = hygiene.H.get("data_words") or {}
got = data_check.data_words_problems()
check("no told string in data/ holds a dash", not got, (len(got), got[:4]))
check("...and the game's startup check holds it", "data_words_problems()" in Path(data_check.__file__).read_text(encoding="utf-8").split("def check()")[1].split("\ndef ")[0])
rows = list(data_check.data_strings(data_check.ROOT / "data", tuple(T.get("skip") or ())))
dashed = [(rel, path, s) for rel, path, s in rows if data_check.DASHED.search(s)]
kinds = {}
for rel, path, s in dashed:
    kinds.setdefault(data_check.not_told(T.get("not_told") or {}, rel, path), []).append((rel, ".".join(path)))
other = [f.as_posix() for f in (data_check.ROOT / "data").rglob("*") if f.is_file() and f.suffix not in data_check.DATA_KINDS
         and f.relative_to(data_check.ROOT / "data").parts[0] not in (T.get("skip") or ())]
check("every file in data/ is of a kind the rule reads", not other, other)
check("the data is read whole: thousands of strings in a hundred files", len(rows) > 5000 and len({r for r, _, _ in rows}) > 100, (len(rows), len({r for r, _, _ in rows})))
check("...the dashes left are all of the four declared kinds", set(kinds) == set(data_check.NOT_TOLD) and "" not in kinds, {k: len(v) for k, v in kinds.items()})
stale = [(rel, key) for rel, keys in (T.get("not_told") or {}).items() for key in keys
         if not any(r == rel and data_check.not_told({rel: {key: keys[key]}}, r, p) for r, p, _ in dashed)]
check("...and the table declares nothing that holds no dash (an entry gone is taken off it)", not stale, stale)

# ---- structure the engine reads still reads
from engine import threads
from world.loader import authored
world = authored()
pressures = list(world.pressures.values())
headed = [p for p in pressures if ": " in p.description]
got = {p.id: {threads.clause(p.description, random.Random(seed)) for seed in range(30)} for p in pressures}
check("a pressure's description holds no dash, and most end their head at a colon", len(headed) > 40
      and not any(data_check.DASHED.search(p.description) for p in pressures), [p.description for p in pressures if data_check.DASHED.search(p.description)][:3])
check("...its clause is still one thing that may happen, never its head, whichever is drawn",
      all(c and not data_check.DASHED.search(c) and ": " not in c for cs in got.values() for c in cs)
      and not any(p.description.split(": ")[0].lower() in {c.lower() for c in got[p.id]} for p in headed),
      [(p.id, sorted(got[p.id])) for p in headed if p.description.split(": ")[0].lower() in {c.lower() for c in got[p.id]}][:2])
check("...a line that was an aside between two dashes gives its things, not a broken half",
      got["rimewind_march"] == {"frost-giants", "a winter hag or a frozen host"} if "rimewind_march" in got else False, sorted(got.get("rimewind_march", [])))
check("...and a clause handed on is drawn from every part: a line of two halves gives either",
      got["willowmead_floods"] == {"the Great River's waters rise into the fields and orchards", "a good season brings a fine harvest and a market fair"}
      if "willowmead_floods" in got else False, sorted(got.get("willowmead_floods", [])))
from core import yamlio
ends = yamlio.safe_load((data_check.ROOT / "data" / "rules" / "brief.yaml").read_text(encoding="utf-8"))["townsfolk"]["promise"]["clause_ends"]
check("the brief's clause ends still hold the dashes it looks for", any("—" in e for e in ends) and any("–" in e for e in ends), ends)

# ---- what was reworded is told as it now stands
visible = [v for p in world.places.values() for v in p.visible]
check("a place's lines, lore, a role and a road reach the game without a dash, their words whole",
      any(v.startswith("Roads leave in every direction: the Old Quarry Road north") for v in visible)
      and not any(data_check.DASHED.search(v) for v in visible)
      and not any(data_check.DASHED.search(f.text) for f in world.lore.values())
      and not any(data_check.DASHED.search(r.description) for r in world.roles.values())
      and not any(data_check.DASHED.search(r.description or "") for r in world.roads.values()),
      [v for v in visible if data_check.DASHED.search(v)][:3])
hollow = next(f.text for f in world.lore.values() if "the Hollow, somewhere beyond" in f.text)
check("...and a line the mender would have broken off like speech is whole", "looks like one: no two tellings agree" in hollow, hollow)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
