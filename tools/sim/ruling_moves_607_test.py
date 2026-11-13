"""(f607) The act corpus measures a fair ruling as fair (docs/measure/2026-11-12_phase2_pod.md: of five act cases counted wrong, one
was a fair "surrenders" where the case allowed only "terrified", and one a fair "warmer" where the case asked the guard untouched).
A case's `moves` for a target is one word (exactly that), a list (one or more of these, nothing else), {not: [words]} (anything
but these: the change that matters is forbidden, a feeling beside it is not), or false (untouched). The two cases now say what a good
dungeon master would accept.
Run: python tools/sim/ruling_moves_607_test.py"""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from tools import ruling_eval as R

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


class FakeT:
    def get(self, code):
        return NS(code=code)


fake = NS(resolve=lambda name, T: name, follows=lambda T, v: dict(after))   # (f619) what follows from the kept changes, by target
after = {}
moved = lambda moves, *words: R.Bench.moved(fake, {"moves": {"s1.1": moves}}, FakeT(),
                                            NS(ok=True, ruling=NS(changes=[NS(target="s1.1", becomes=w) for w in words])))
check("one word: exactly that change", moved("terrified", "terrified") and not moved("terrified", "terrified", "warmer")
      and not moved("terrified"))
check("a list: one or more of them and nothing else", moved(["terrified", "surrenders"], "surrenders")
      and moved(["terrified", "surrenders"], "terrified", "surrenders") and not moved(["terrified", "surrenders"])
      and not moved(["terrified", "surrenders"], "committed"))
check("not: anything but these, untouched included", moved({"not": ["open"]}, "warmer") and moved({"not": ["open"]})
      and not moved({"not": ["open"]}, "warmer", "open"))
check("false: untouched", moved(False) and not moved(False, "warmer"))
after["s1.1"] = {"safe"}
check("(f619) what follows from a kept change counts with it, on the target it lands on", moved(["lifted", "safe"], "lifted")
      and not moved("lifted", "lifted") and not moved("safe"))
after.clear()
try:
    moved({"only": ["open"]}, "warmer")
    loud = False
except ValueError:
    loud = True
check("a moves misspelt is refused aloud, never read as anything passes", loud)

cases = R.load(ROOT / "data/replay/ruling_cases_act.yaml")
wrestle = next(c for c in cases if "wrestle" in c["line"])
plead = next(c for c in cases if "plead" in c["line"])
check("the wrestled guard may be terrified or surrender", sorted(wrestle["moves"]["@person:1"]) == ["surrenders", "terrified"],
      wrestle["moves"])
check("the pleaded-with guard may warm to the player, never change their stance or act on words alone",
      {"open", "committed", "warns", "surrenders"} <= set(plead["moves"]["@person:1"]["not"])
      and "warmer" not in plead["moves"]["@person:1"]["not"], plead["moves"])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
