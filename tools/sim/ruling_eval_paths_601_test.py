"""(f601) Both ruling paths on the corpus (docs/design/14_phase2_plan.md, the measurement before the switch). tools/ruling_eval.py --path
old|new|both rules every case by the old ruling (engine/ruling.py) or the act's (engine/act.py), and counts false acceptances and false
rejections for each, side by side. A case carries what it needs in the world (things lying here, things in hand, a situation with its
parts), and no case sees another's. The act corpus (data/replay/ruling_cases_act.yaml) holds acts on things and on a situation's parts,
offline where a model ruling is given; the old path's output stays as tools/think_ab.py and the suite read it.
Run: python tools/sim/ruling_eval_paths_601_test.py"""
import os
import subprocess
import sys
sys.path.insert(0, ".")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


ENV = dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONUTF8="1")
def run(*args):
    return subprocess.run([sys.executable, "tools/ruling_eval.py", *args], cwd=ROOT, env=ENV, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=600)


r = run("--path", "both", "--cases", "data/replay/ruling_cases_act.yaml")
tail = r.stdout.strip().splitlines()[-2:]
check("the act corpus on both paths, offline: every case the engine can judge is right on each, false acceptances and rejections counted",
      r.returncode == 0 and len(tail) == 2 and tail[0].startswith("old: ") and tail[1].startswith("new: ")
      and all("false acceptances 0, false rejections 0" in t for t in tail), (r.returncode, r.stdout[-600:], r.stderr[-600:]))
check("...each path scored on its sense alike, the act's changes on each target apart (never by the ruling's own numbering)",
      "new: 17 of 17 right" in r.stdout and "changes wrong 0" in tail[1] and "old: 18 of 18 right" in tail[0]
      and "| new ok  yes, moves ok" in r.stdout and "{person:" not in r.stdout, r.stdout[-1500:])

check("...and where the engine is not yet what the owner decided, the case is shown apart, by name, never counted right",
      "1 known, awaiting their feature" in tail[1] and "new KNW" in r.stdout and "known: a hand's work" in r.stdout, r.stdout[-800:])

r = run()
check("the old path's own output is unchanged: the suite and tools/think_ab.py read it", r.returncode == 0
      and r.stdout.strip().splitlines()[-1].endswith("need the model (--live)") and " of " in r.stdout.strip().splitlines()[-1], r.stdout[-300:])
r = run("--path", "both")
check("...and the first corpus runs on both paths side by side", r.returncode == 0 and "old: 19 of 19 right" in r.stdout
      and "new: 19 of 19 right" in r.stdout, r.stdout[-400:])

# ---- the bench, in this process
sys.path.insert(0, str(ROOT))
from tools import ruling_eval as R
from engine import objects, pulse

t = R.Tally()
seen = [t.add("no", "yes"), t.add("yes", "no"), t.add("yes", "yes"), t.add("no", "no"), t.add("yes", None), t.add("yes", "yes", moves_ok=False),
        t.add("yes", "yes", needs_ok=False)]
k = R.Tally()
k.add("yes", "yes", moves_ok=False, known=True)
k.add("yes", "no", moves_ok=False, known=True)
k.add("yes", "yes", moves_ok=True, known=True)
check("a known label covers the decided gap alone: a refusal under it is a false rejection, and one now right asks for it to go",
      (k.known, k.rejected, k.retire, k.wrong) == (1, 1, 1, 2), vars(k))
check("a no taken for a yes is a false acceptance, a yes refused a false rejection; the changes and the needs counted apart",
      (t.right, t.accepted, t.rejected, t.none, t.changes_wrong, t.needs_missed) == (4, 1, 1, 1, 1, 1)
      and seen == [False, False, True, True, False, False, False], (vars(t), seen))

act_cases = R.load(ROOT / "data/replay/ruling_cases_act.yaml")
complex_cases = R.load(ROOT / "data/replay/ruling_cases_complex.yaml")
b = R.Bench(save="ruling_eval_601")
try:
    barrel = next(c for c in act_cases if c.get("objects") == ["a barrel"] and "moves" in c and c["moves"]["@object:barrel"])
    loot = next(c for c in act_cases if (c.get("situation") or {}).get("title") == "Looting" and (c.get("moves") or {}).get("@person:1"))
    plain = {"line": "I look around.", "at": "trading_square", "expect": "yes"}
    b.put(barrel)
    T = b.targets()
    check("a case's thing lies where it is, among the act's targets", any(x.kind == "object" and "barrel" in x.line for x in T.rows))
    b.put(loot)
    T = b.targets()
    check("...and is gone for the next case, whose situation stands with its parts", not any(x.kind == "object" and "barrel" in x.line
          for x in T.rows) and any(x.kind == "condition" for x in T.rows) and any(x.kind == "person" for x in T.rows))
    sit = b.sit
    b.put(plain)
    state = b.store.load_world_state()
    check("...and a case with nothing of its own sees no situation of another's, nor what it laid on the world",
          pulse.thread_of(state, sit)["status"] != "active" and not any(x.kind == "condition" for x in b.targets().rows)
          and not any(e.get("thread") == sit and e["until"] > b.ws.minutes for e in state.get("effects", [])))
    named = next(c for c in act_cases if "{person:1}" in c["line"])
    b.put(named)
    check("a case names the situation's people as the player would: by name", "{person:" not in b.line(named)
          and b.store.load_npc(pulse.thread_of(b.store.load_world_state(), b.sit)["parts"][0]["who"]).name in b.line(named), b.line(named))
    packed = [c for c in complex_cases if c.get("pack")]
    held = []
    for c in packed:
        b.put(c)
        held.append(sorted(i.good for i in b.ws.player.character.inventory if i.good in c["pack"]) == sorted(c["pack"]))
    b.put(plain)
    check("the complex cases that rely on goods have them in the pack, as both rulings see a pack, and only for that case",
          len(packed) >= 4 and all(held) and not any(i.good in {"rope", "lamp_oil", "dried_fish"} for i in b.ws.player.character.inventory),
          (len(packed), held))

    b.put(loot)
    T = b.targets()
    b.stub.act_ruling = {"sense": "cost", "stakes": {"check": "intimidation", "hard": "fair"},
                         "changes": [{"n": 5, "target": b.resolve("@condition", T), "becomes": "lifted", "because": "force"},
                                     {"n": 7, "target": b.resolve("@person:1", T), "becomes": "safe", "because": "earlier", "needs": [5]}]}
    tl = R.Tally()
    shown = R.side(b, dict(loot), "new", True, tl)
    check("the live new path asks the act's ruling and measures its changes by target, whatever it numbers them",
          tl.right == 1 and tl.changes_wrong == 0 and "moves ok" in shown, (vars(tl), shown))
    b.stub.act_ruling = {"sense": "cost", "stakes": {"check": "performance", "hard": "fair"},
                         "changes": [{"n": 1, "target": "s1.2", "becomes": "lifted", "because": "force"}]}
    shown = R.side(b, dict(loot), "new", True, tl)
    check("...a live ruling whose changes do not do what the case says is counted so", tl.changes_wrong == 1 and "moves WRONG" in shown, shown)
    real = b.stub.a_ActRuling
    try:
        from llm.gateway import LLMError
        b.stub.a_ActRuling = lambda u, k: (_ for _ in ()).throw(LLMError("the model failed"))
        shown = R.side(b, dict(loot), "new", True, tl)
        check("...and a model that gives none is counted apart, never as right or wrong", tl.none == 1 and tl.right == 2, (vars(tl), shown))
    finally:
        b.stub.a_ActRuling = real
finally:
    b.clear()
    b.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
