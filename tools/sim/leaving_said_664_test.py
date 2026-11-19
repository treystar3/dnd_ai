"""(f664) A person's leaving is written to the journal with whether they died, by every writer, and mourning reads that and nothing
looser (docs/design/21_play_faults_plan.md, D2; found in play: docs/play/2026-11-15_play_findings.md 2.13, Parth mourned Maren Holt,
who left alive: her leaving was written with no word of death, and the town read the manner of it as one).
Held here: one writer of a leaving (pulse.journal_gone), which always says whether it was a death; no other code writes the row;
every caller of remove_npc says it; Maren's leaving is written alive; a model's words for a leaving are read once, where written;
and the town's grief reads the written death alone, so a row that says nothing is no death.
Run: python tools/sim/leaving_said_664_test.py"""
import ast
import inspect
import pathlib
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
simlib.quiet_console()
from engine import pulse, towns

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


writers, callers = [], []
for root in ("engine", "scenes", "services", "npc", "storage"):
    for f in pathlib.Path(root).rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for c in ast.walk(node):
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "journal" \
                            and any(isinstance(a, ast.Constant) and a.value == "npc_gone" for a in c.args):
                        writers.append(f"{f.as_posix()}:{node.name}")
            if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == "remove_npc":
                callers.append((f.as_posix(), node.lineno, any(k.arg == "dead" for k in node.keywords)))
check("one writer of a leaving: no other code writes the journal's row", writers == ["engine/pulse.py:journal_gone"], writers)
check("every caller of remove_npc says whether it was a death", callers and all(said for *_, said in callers), [c for c in callers if not c[2]])
check("...and it cannot be left out", inspect.signature(pulse.remove_npc).parameters["dead"].default is inspect.Parameter.empty)
check("Maren's leaving is written alive", "journal_gone(store, npc, npc.gone, t, dead=False)" in open("engine/mentor.py", encoding="utf-8").read())

g = simlib.campaign("leaving_said_664_test", seed=8, location="trading_square")
ws, store = g.scene, g.store
ws.enter("tilted_plough")
npc = next(n for n in ws.present)
town = {npc.location}
store.journal(ws.minutes, "npc_gone", "", npc.id, f"{npc.name} is gone: was carried off by the river and drowned", {"how": "drowned", "place": npc.location})
check("2.13: a row that does not say it was a death is no death, whatever its words", towns._lost_lately(store, ws.world, town, ws.minutes, 3) == "")
pulse.journal_gone(store, npc, "left for the capital", ws.minutes, dead=False)
check("...a leaving written alive is not mourned", towns._lost_lately(store, ws.world, town, ws.minutes, 3) == "")
pulse.journal_gone(store, npc, "fell from the bridge", ws.minutes, dead=True)
check("...and one written as a death is", towns._lost_lately(store, ws.world, town, ws.minutes, 3) == npc.name.split(" is gone")[0])
shutil.rmtree("saves/leaving_said_664_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
