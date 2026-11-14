"""(f575) tools/prose_measure.py reads a model call log and measures, per task, how much the accepted prose repeats itself: repeated
five-word phrases, repeated sentences, shared openings, worn words and stock phrases. A rejected answer (a row with an error) is not
measured; each task's prose is read from its own field; a kept baseline is compared against."""
import json, sys, tempfile
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

narr = ["The gate stands open and nobody minds it. A dog looks up.",
        "The gate stands open and nobody minds it. Smoke leans east over the roofs.",
        "Rain on the thatch. You wait under the eaves with a weary, unreadable face.",
        "The smith works the bellows with a steady hand, his gaze steady and weary.",
        "A weary horse, a steady rain, an unreadable sky, and the air hangs heavy here.",
        "Dusk. The steady road runs on, weary, unreadable, into the trees."]
lines = [row("narrate", {"text": t}) for t in narr]
lines.append(row("narrate", {"text": "The gate stands open and nobody minds it. Rejected anyway."}, error="stale"))
lines += [row("npc_conversation", {"speech": "Horseshoes. Nails. If you want a sword you want the city.", "reveals": []}),
          row("npc_conversation", {"speech": "Horseshoes and nails, mostly. Ask the city for swords."}),
          row("exchange", {"lines": [{"speaker": "a", "text": "You came back."}, {"speaker": "b", "text": "I said I would."}]}),
          row("dialogue_frame", {"before": "She looks up from the ledger.", "after": "She goes back to it."}),
          row("interpret_action", {"actions": [{"kind": "look"}]}),
          "not json at all"]
log = Path(tempfile.mkdtemp(prefix="prose575_")) / "llm_calls.jsonl"
log.write_text("\n".join(lines) + "\n", encoding="utf-8")

by = pm.load([str(log)])
check("each prose task is read from its own field; interpretation and junk lines are not prose",
      set(by) == {"narrate", "npc_conversation", "exchange", "dialogue_frame"}, set(by))
check("a rejected answer is not measured", len(by["narrate"]) == 6 and not any("Rejected" in p for p in by["narrate"]), by["narrate"])
check("an exchange's lines and a frame's before and after are its prose", by["exchange"] == ["You came back. I said I would."]
      and by["dialogue_frame"] == ["She looks up from the ledger. She goes back to it."], (by["exchange"], by["dialogue_frame"]))

import gzip
gz = log.parent / "kept.jsonl.gz"
gz.write_bytes(gzip.compress(log.read_bytes()))
check("a kept log compressed with gzip reads the same", pm.load([str(gz)]) == by)

m = pm.measure_all(by)["narrate"]
check("a sentence said in two passages is a repeated sentence", m["sentences_per_k"] > 0 and "the gate stands open and nobody minds it" in m["top_sentences"], m)
check("its five-word runs are repeated phrases", "the gate stands open and" in m["top_phrases"], m["top_phrases"])
check("two passages opening on the same three words share an opening (2 of 6)", abs(m["openings_share"] - 2 / 6) < 0.01, m["openings_share"])
check("a word of the wearing kind in four passages is worn (weary); one in three is not yet (steady, unreadable)",
      m["top_worn"] == ["weary"] and m["worn_count"] == 1, m["top_worn"])
check("a stock phrase is counted", m["stock_per_k"] > 0, m["stock_per_k"])
fresh = pm.measure(["Rain on the thatch.", "A dog barks twice and stops.", "The ferry is late again today, they say."])
check("prose that does not repeat itself measures nothing", fresh["phrases_per_k"] == 0 and fresh["sentences_per_k"] == 0
      and fresh["openings_share"] == 0 and fresh["worn_count"] == 0, fresh)

out = log.parent / "base.json"
check("the command line writes the numbers", pm.main([str(log), "--json", str(out), "--samples", "0"]) == 0 and out.exists())
kept = json.loads(out.read_text(encoding="utf-8"))
lines_now = pm.table(pm.measure_all(by), kept["tasks"])
check("...and compares against a kept baseline, a change of nothing showing as +0", any(l.startswith("| narrate |") and "(+0.00)" in l for l in lines_now), lines_now)
check("an empty log says so and fails", pm.main([str(log.parent / "missing.jsonl")]) != 0 if (log.parent / "missing.jsonl").write_text("") is not None else False)

import os, subprocess
probe = "import config; print(config.LOG_MAX_MB)"
plain = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "DND_LOG_MAX_MB"})
raised = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env={**os.environ, "DND_LOG_MAX_MB": "250"})
check("the call log trims at 5 MB, unless a measuring run raises it (DND_LOG_MAX_MB)", plain.stdout.strip() == "5.0" and raised.stdout.strip() == "250.0",
      (plain.stdout, plain.stderr[-200:], raised.stdout))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
