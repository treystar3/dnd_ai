"""(f393) The acceptance scenes (tools/acceptance.py, data/replay/scenes.yaml): every scene of a slice built so far plays as the goal says;
the rest are reported. Also: the ruling's test set is well formed."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import yaml
import acceptance as scenes
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

all_ = scenes.load()
check("every scene has a name, a slice, a start and steps", all(s.get("name") and isinstance(s.get("slice"), int) and s.get("start") and s.get("steps") for s in all_))
check("scene names are unique", len({s["name"] for s in all_}) == len(all_))
due = [s for s in all_ if s["slice"] <= scenes.BUILT]
check("there is a scene for each slice up to the third", {1, 2, 3} <= {s["slice"] for s in all_})
for sc in due:
    short = scenes.play(sc)
    check(f"[{sc['slice']}] {sc['name']}: {sc.get('about', '')}", not short, short)
ahead = [s["name"] for s in all_ if s["slice"] > scenes.BUILT]
print(f"     ({len(ahead)} scene(s) for slices not built yet: {', '.join(ahead)})")

cases = yaml.safe_load(open("data/replay/ruling_cases.yaml", encoding="utf-8"))
check("the ruling's test set: every case has a line, a place, and yes, cost or no",
      all(c.get("line") and c.get("at") and c.get("expect") in ("yes", "cost", "no") for c in cases), [c for c in cases if c.get("expect") not in ("yes", "cost", "no")][:3])
check("...with sensible, nonsensical and means-dependent lines", sum(c["expect"] == "no" for c in cases) >= 15 and sum(c["expect"] != "no" for c in cases) >= 15
      and sum(1 for c in cases if "means" in c) >= 6)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
