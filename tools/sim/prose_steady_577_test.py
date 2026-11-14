"""(f577) tools/prose_measure.py also measures each task over draws of a fixed size, so two runs of different lengths compare and each
number carries a band: fights are drawn whole (opening, rounds and aftermath split at each opening), other tasks by the passage. A change
is better than its baselines only when it sits below every baseline's band, worse above, and otherwise holds."""
import json, random, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 75))
sys.path.insert(0, "tools")
import prose_measure as pm

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def row(task, answer, error=""):
    return json.dumps({"task": task, "attempt": 0, "raw": json.dumps(answer), "messages": [], "error": error})

VOCAB = ("river stone lantern hollow barrow fence ledger kettle orchard rope gutter chapel wagon cellar thistle market bell "
         "copper ferry hedge mill ash willow anvil loft cart brook shutter").split()
_pool = random.Random(0)
STOCK = [" ".join(_pool.choice(VOCAB) + "s" * k for k in range(5)) for _ in range(200)]
def corpus(n, seed):
    """n passages of fresh words, each carrying two runs from one pool of stock runs: the same habit of repeating at any length."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        words = [rng.choice(VOCAB) + str(rng.randrange(10000)) for _ in range(30)]
        words[10:10] = rng.choice(STOCK).split()
        words[25:25] = rng.choice(STOCK).split()
        out.append(" ".join(words) + ".")
    return out

def avg(xs): return sum(xs) / len(xs)
shorts, longs = [corpus(40, s) for s in range(1, 7)], [corpus(160, s) for s in range(11, 17)]
whole_s, whole_l = avg([pm.measure(c)["phrases_per_k"] for c in shorts]), avg([pm.measure(c)["phrases_per_k"] for c in longs])
held_s = avg([pm.steady({"narrate": c}, [], sizes={"narrate": 30}, draws=40)["narrate"]["phrases_per_k"]["mean"] for c in shorts])
held_l = avg([pm.steady({"narrate": c}, [], sizes={"narrate": 30}, draws=40)["narrate"]["phrases_per_k"]["mean"] for c in longs])
check("measured whole, longer runs of the same writing score worse (the size effect)", whole_l > whole_s * 1.5, (whole_s, whole_l))
check("...measured over draws of a fixed size, they agree", abs(held_s - held_l) < 0.2 * held_s, (held_s, held_l))
long_run = longs[0]
lt = pm.steady({"narrate": long_run}, [], sizes={"narrate": 30})["narrate"]
short_run = shorts[0]
check("each number carries a band around its mean", lt["phrases_per_k"]["low"] <= lt["phrases_per_k"]["mean"] <= lt["phrases_per_k"]["high"]
      and lt["phrases_per_k"]["low"] < lt["phrases_per_k"]["high"], lt["phrases_per_k"])
check("the draw size and unit are kept with the numbers", lt["size"] == 30 and lt["unit"] == "passages" and not lt["short"], lt)
check("the same seed draws the same", pm.steady({"narrate": long_run}, [], sizes={"narrate": 30}) == {"narrate": lt})
few = pm.steady({"narrate": short_run[:10]}, [], sizes={"narrate": 30})["narrate"]
check("a task with fewer passages than the size is measured whole and marked short",
      few["short"] and few["phrases_per_k"]["low"] == few["phrases_per_k"]["high"] == pm.measure(short_run[:10])["phrases_per_k"], few)

d = Path(tempfile.mkdtemp(prefix="prose577_"))
def fight(i, rounds):
    return ([row("combat_opening", {"text": f"Fight {i} opens on the bridge."})] + [row("combat_narrate", {"text": f"Round {r} of fight {i}."})
            for r in range(rounds)] + [row("combat_aftermath", {"text": f"Fight {i} is over."})])
a = [row("combat_narrate", {"text": "A round from before any opening was logged."})] + fight(1, 2) + [row("narrate", {"text": "The road."})] + fight(2, 3)
b = fight(3, 1) + [row("combat_narrate", {"text": "Rejected round."}, error="stale")]
(d / "a.jsonl").write_text("\n".join(a) + "\n", encoding="utf-8")
(d / "b.jsonl").write_text("\n".join(b) + "\n", encoding="utf-8")
fs = pm.load_fights([str(d / "a.jsonl"), str(d / "b.jsonl")])
check("fights are split at each opening, log by log; a round before any opening is no fight's, a rejected round is not kept",
      [len(f["combat_narrate"]) for f in fs] == [2, 3, 1] and all(len(f["combat_opening"]) == 1 and len(f["combat_aftermath"]) == 1 for f in fs), fs)
by = pm.load([str(d / "a.jsonl"), str(d / "b.jsonl")])
fsteady = pm.steady(by, fs, sizes={"fights": 2})
check("fight tasks are drawn by the fight, so a draw holds a whole fight's rounds", fsteady["combat_narrate"]["unit"] == "fights"
      and fsteady["combat_narrate"]["size"] == 2 and fsteady["narrate"]["unit"] == "passages", fsteady)

def band(lo, mean, hi, size=40, short=False):
    return {"phrases_per_k": {"low": lo, "mean": mean, "high": hi}, "size": size, "unit": "passages", "short": short}
b1, b2 = band(2.0, 3.0, 4.0), band(5.0, 6.0, 8.0)
check("a change below every baseline's band is better", pm.verdict(band(1.0, 1.5, 2.5), [b1, b2], "phrases_per_k") == "better")
check("...above every one is worse", pm.verdict(band(8.0, 9.0, 10.0), [b1, b2], "phrases_per_k") == "worse")
check("...and anywhere the baselines span, it holds", pm.verdict(band(4.0, 4.5, 5.0), [b1, b2], "phrases_per_k") == "holds")
check("a short side, or one drawn at another size, gets no verdict (the size effect again)",
      pm.verdict(band(1.0, 1.0, 1.0, short=True), [b1, b2], "phrases_per_k") == "-"
      and pm.verdict(band(1.0, 1.5, 2.5), [b1, band(5.0, 6.0, 8.0, short=True)], "phrases_per_k") == "-"
      and pm.verdict(band(1.0, 1.5, 2.5, size=30), [b1, b2], "phrases_per_k") == "-")

runs = []
for k in range(3):
    f = d / f"run{k}.jsonl"
    f.write_text("\n".join(row("narrate", {"text": t}) for t in corpus(60, 100 + k)) + "\n", encoding="utf-8")
    runs.append(f)
j1, j2 = d / "one.json", d / "two.json"
check("the kept numbers carry the steady measure", pm.main([str(runs[0]), "--json", str(j1), "--samples", "0"]) == 0
      and json.loads(j1.read_text(encoding="utf-8"))["steady"]["narrate"]["size"] == pm.SIZE["narrate"], j1.read_text(encoding="utf-8")[:300])
pm.main([str(runs[1]), "--json", str(j2), "--samples", "0"])
import io, contextlib
def steady_rows(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        pm.main(args)
    part = buf.getvalue().split("fixed size")[-1].split("## First tries")[0]
    return [l for l in part.splitlines() if l.startswith("| narrate |")]
two = steady_rows([str(runs[2]), "--against", str(j1), str(j2), "--samples", "0"])
check("a run compared against two kept baselines gets a verdict on every measure",
      len(two) == 1 and sum(two[0].count(w) for w in ("holds", "better", "worse")) == len(pm.STEADY), two)
one = steady_rows([str(runs[2]), "--against", str(j1), "--samples", "0"])
check("...but against one baseline, none: one run's band is narrower than two runs differ",
      len(one) == 1 and not any(w in one[0] for w in ("holds", "better", "worse")), one)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
