"""(f615) The prompt's examples of a verdict and the corpus are kept apart. The act's prompt and the road's gave "summoning a dragon
from nothing, conjuring gold, making the sun set" as their examples of a no while the corpus asked "I summon a dragon to burn the
market", "I conjure a thousand gold coins" and "I make the sun go down now": three lines that scored the prompt (the audit of
2026-11-13, docs/design/18 A1). The measuring tool refuses a case file with a line that repeats an example either prompt gives of a
verdict (its `sense` lines), two or more content words shared however they are bent, naming the line and the example. An example of
one word names a kind of act and the corpus may hold it; the prompt's other text is not an example of a verdict.
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

P = {"a prompt": "Rule with:\n  sense:    \"yes\"  - they can simply do it (walk on, sit down, look closely).\n"
                 "            \"cost\" - it takes effort (climbing, digging a pit, barring the door).\n"
                 "            \"no\"   - impossible for anyone (calling a storm out of a clear\n                     sky, a rope broken by a word).\n"
                 "  why:      one short line.\n  uses:     the rope to climb, the person spoken to.\n  stakes:   Leave empty for a plain yes."}
def taught(line):
    return [(l, ex) for l, _, ex in R.taught([{"line": line}], P)]


check("the examples of a verdict are read from the prompt's sense lines, each item of each list, across a line break",
      R.examples(P["a prompt"]) == ["walk on", "sit down", "look closely", "climbing", "digging a pit", "barring the door",
                                    "calling a storm out of a clear sky", "a rope broken by a word"], R.examples(P["a prompt"]))
check("a line that shares two content words with one example repeats it, and is named with the example",
      taught("I call a storm down on the harbour.") == [("I call a storm down on the harbour.", "calling a storm out of a clear sky")],
      taught("I call a storm down on the harbour."))
check("...however the words are bent: a doubled letter (dig, digging; bar, barred), a past that is another word (dug; break, broken)",
      all(taught(x) for x in ("I dig a pit by the wall.", "I dug a deep pit.", "The pit is dug.", "I bar the door.", "The door stays barred.",
                              "I break the rope with a word.", "The rope broke at my word.", "I looked closely at it.")),
      [x for x in ("I dig a pit by the wall.", "I dug a deep pit.", "The pit is dug.", "I bar the door.", "The door stays barred.",
                   "I break the rope with a word.", "The rope broke at my word.", "I looked closely at it.") if not taught(x)])
check("...one shared word is not enough, nor two words from two different examples",
      not taught("I buy a rope.") and not taught("I dig by the door."), (taught("I buy a rope."), taught("I dig by the door.")))
check("...an example of one word is a kind of act, which a line may hold", not taught("I climb up to the ledge above the waterline."))
check("...the small words of the language never count", not taught("I sit down with what they have."), taught("I sit down with what they have."))
check("...and the prompt's other text is no example of a verdict: how to name a thing, an instruction",
      not taught("I climb the rope down into the dry well.") and not taught("I give them a plain yes and leave it empty."),
      (taught("I climb the rope down into the dry well."), taught("I give them a plain yes and leave it empty.")))

prompts = R.prompts()
found_ex = {name: R.examples(p) for name, p in prompts.items()}
check("the real prompts are the act's ruling's and the road's, each read to its eleven examples of a verdict",
      len(prompts) == 2 and all(len(x) == 11 and "conjuring gold" in x and "sit down" in x for x in found_ex.values()), found_ex)
OLD = ("I summon a dragon to burn the market.", "I conjure a thousand gold coins.", "I make the sun go down now.")
BENT = ("A dragon is summoned out of nothing.", "Gold, conjured by the handful.", "I made the sun set early.", "I sat down and looked closely.")
check("...under them the three old lines are refused, and so are the same examples bent another way",
      all(R.taught([{"line": x}]) for x in OLD + BENT), [x for x in OLD + BENT if not R.taught([{"line": x}])])

files = sorted((ROOT / "data" / "replay").glob("ruling_cases*.yaml"))
found = {f.name: R.taught(R.load(f)) for f in files}
check("no line of any corpus file repeats an example of either prompt", len(files) >= 3 and not any(found.values()), found)
lines = [c["line"] for f in files for c in R.load(f)]
check("...the three are gone from the corpus, one of each kind in their place, and no other line was changed for the check",
      not any(x in lines for x in OLD) and len(R.load(R.CASES)) == 50 and all(any(c["line"] == x and c["expect"] == "no" for c in R.load(R.CASES))
      for x in ("I call a giant up out of the earth to flatten the market.", "I wish a chest of silver into my hands.", "I tell the moon to rise at noon."))
      and "I climb the rope down into the dry well." in lines)

folder = Path(tempfile.mkdtemp(prefix="corpus_apart_615_"))
path = folder / "cases.yaml"
path.write_text(yaml.safe_dump([{"line": "I sit by the fire.", "at": "trading_square", "expect": "yes", "model": {"sense": "yes"}},
                                {"line": "I conjure a heap of gold.", "at": "trading_square", "expect": "no", "model": {"sense": "no", "answer": "x"}}],
                               sort_keys=False), encoding="utf-8")
r = subprocess.run([sys.executable, "tools/ruling_eval.py", "--cases", str(path)], cwd=ROOT, env=dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONUTF8="1"),
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
shutil.rmtree(folder, ignore_errors=True)
check("the tool refuses a case file with such a line, naming the line and the example, and scores nothing",
      r.returncode == 2 and "I conjure a heap of gold." in r.stderr and "conjuring gold" in r.stderr and "right" not in r.stdout,
      (r.returncode, r.stdout[-200:], r.stderr[-300:]))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
