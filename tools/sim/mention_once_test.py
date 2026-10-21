"""A waking scene mentions the gasp once: later sentences about the same breath are dropped."""
import sys
sys.path.insert(0, ".")
from engine.voice_rules import mention_once
bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
W = ("gasp", "gasped", "gasping")
t = ("You wake with a sharp, ragged gasp. A sharp, jagged gasp of air tears through your lungs. You lie flat against the soil. "
     "To your side, the Shadow Wolf sits in silent vigil.")
out = mention_once(t, W)
check("the second gasp sentence is dropped", out.lower().count("gasp") == 1 and "tears through" not in out, out)
check("everything else stays", "lie flat against the soil" in out and "Shadow Wolf" in out)
check("a text with one gasp is untouched", mention_once("You gasp. The air is cold.", W) == "You gasp. The air is cold.")
check("a text with none is untouched", mention_once("The light is grey.", W) == "The light is grey.")
check("an empty result falls back to the text", mention_once("", W) == "")
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
