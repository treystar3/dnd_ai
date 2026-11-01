"""(f446) The card profile Stage 3's turn budget reads (data/rules/card_profile.yaml), from a 1.5-hour live night recorded on an RTX A4000
and scaled to the RTX 3060 the game is built for (GOALS.md; Runpod rents no 3060): the speeds are there, it says it is an estimate and
from which card, the model and its context fit the card's memory, and the startup check keeps it whole."""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 46))
import yaml
from pathlib import Path
from engine import data_check

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

P = yaml.safe_load(Path("data/rules/card_profile.yaml").read_text(encoding="utf-8"))
check("the profile is for the card the game is built for", P["card"] == "RTX 3060 12GB" and P["model"] == "gemma4:12b", P)
check("...says it is an estimate, and from which card", P["scaled_from"] == "RTX A4000")
check("...says the model and its context fit the card", "(fits)" in P["fits"], P["fits"])
check("...and holds the speeds the turn budget needs", P["prompt_tokens_per_second"] > 0 and P["answer_tokens_per_second"] > 0
      and P["median_turn_seconds"] > 0 and P["turns"] > 100, P)
check("the startup check keeps it whole", not [p for p in data_check.check() if "card_profile.yaml" in p])
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
