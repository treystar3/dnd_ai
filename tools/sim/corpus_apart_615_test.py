"""(f615) The prompt and the corpus are kept apart. A corpus line that shares two or more content words with one phrase of a ruling's
prompt is a line the prompt teaches, and its score says nothing of the model's judgement: the act's prompt gave "summoning a dragon
from nothing, conjuring gold, making the sun set" as its examples of a no while the corpus asked "I summon a dragon to burn the
market", "I conjure a thousand gold coins" and "I make the sun go down now" (the audit of 2026-11-13, docs/design/18 A1). The measuring
tool now refuses such a line, naming the phrase, for every phrase of both prompts and every line of every corpus file.
Run: python tools/sim/corpus_apart_615_test.py"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


from tools import ruling_eval as R

P = {"a prompt": "Rule with:\n  sense: \"no\" - impossible for anyone (summoning a dragon from\n      nothing, conjuring gold), or what they have "
                 "does not reach.\n  uses: the rope to climb, the person spoken to."}
def taught(line):
    return R.taught([{"line": line}], P)


check("a line sharing two content words with one phrase of a prompt is taught, and named with the phrase, however the words are bent",
      [(l, p) for l, _, p in taught("I summon a dragon to burn the market.")] == [("I summon a dragon to burn the market.", "summoning a dragon from nothing")]
      and taught("I conjure a thousand gold coins.") and taught("I climb the rope down into the dry well."), taught("I summon a dragon to burn the market."))
check("...a phrase broken over two lines of the prompt is still one phrase", taught("Nothing but a dragon would do."))
check("...one shared word is not enough, nor are two words from two different phrases", not taught("I buy a rope.") and not taught("I ride a dragon made of gold."),
      (taught("I buy a rope."), taught("I ride a dragon made of gold.")))
check("...and the small words of the language never count", not taught("I ask what they have for sale."), taught("I ask what they have for sale."))

prompts = R.prompts()
check("the prompts read are the act's ruling's and the road's", len(prompts) == 2 and all(len(R.phrases(p)) > 20 for p in prompts.values()),
      {k: len(R.phrases(p)) for k, p in prompts.items()})
missed = [(name, ph) for name, p in prompts.items() for ph in R.phrases(p) if len(R.stems(ph)) >= 2
          and not R.taught([{"line": "I try " + ph + "."}], {name: p})]
check("every phrase of either prompt with two content words is caught when a line repeats it", not missed, missed[:3])

files = sorted((ROOT / "data" / "replay").glob("ruling_cases*.yaml"))
found = {f.name: R.taught(R.load(f)) for f in files}
check("no line of any corpus file is taught by either prompt", len(files) >= 3 and not any(found.values()), found)
lines = [c["line"] for f in files for c in R.load(f)]
check("...the three lines the prompt taught are gone from the corpus, one of each kind in their place",
      not any(x in lines for x in ("I summon a dragon to burn the market.", "I conjure a thousand gold coins.", "I make the sun go down now."))
      and len(R.load(R.CASES)) == 50 and sum(c["expect"] == "no" for c in R.load(R.CASES)) == 22)

folder = Path(tempfile.mkdtemp(prefix="corpus_apart_615_"))
path = folder / "cases.yaml"
path.write_text(yaml.safe_dump([{"line": "I sit by the fire.", "at": "trading_square", "expect": "yes", "model": {"sense": "yes"}},
                                {"line": "I conjure a heap of gold.", "at": "trading_square", "expect": "no", "model": {"sense": "no", "answer": "x"}}],
                               sort_keys=False), encoding="utf-8")
r = subprocess.run([sys.executable, "tools/ruling_eval.py", "--cases", str(path)], cwd=ROOT, env=dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONUTF8="1"),
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
shutil.rmtree(folder, ignore_errors=True)
check("the tool refuses a case file with a taught line, naming the line and the phrase, and scores nothing",
      r.returncode == 2 and "I conjure a heap of gold." in r.stderr and "conjuring gold" in r.stderr and "right" not in r.stdout,
      (r.returncode, r.stdout[-200:], r.stderr[-300:]))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
