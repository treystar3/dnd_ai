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

# ---- (f457) a reopen is a new session over the same save: what the scene added is read back from the store, never carried across
import simlib
from world.loader import authored
t = scenes.Table(due[0])
first = t.session
here = t.ws.player.location
data = t.store.load_discoveries()
data["places"].append({"place": {"id": "x_reopen_probe", "name": "the Reopen Probe", "type": "wild", "region": authored().places[here].region,
                                 "visible": ["A probe."]}, "anchor": here, "minutes": 30})
t.store.save_discoveries(data)
t.ws.ensure_discoveries()
check("a place the scene added is on its session's map", "x_reopen_probe" in t.ws.world.added()["places"])
from world.loader import Place
old_map = t.ws.world
old_map.add_place(Place(id="x_unsaved_probe", name="the Unsaved Probe", type="wild", region=authored().places[here].region, visible=["A probe."]))
t.reopen()
check("a reopen is a new session over the same save, the old one closed, the scene's its own", t.session is not first and first.closed and t.ws.session is t.session)
# (f733) the new scene is made over the save's map: the saved find is back with no run() and no ensure, the unsaved place is not
check("...its map is read from the store: the saved find is back on a map of its own, the place never saved is not", t.ws.world is not old_map
      and "x_reopen_probe" in t.ws.world.added()["places"] and "x_unsaved_probe" not in t.ws.world.places, t.ws.world.added()["places"])
t.close()
check("...and closing the table leaves nothing of it in the process", simlib.residue() == {}, simlib.residue())

cases = yaml.safe_load(open("data/replay/ruling_cases.yaml", encoding="utf-8"))
check("the ruling's test set: every case has a line, a place, and yes, cost or no",
      all(c.get("line") and c.get("at") and c.get("expect") in ("yes", "cost", "no") for c in cases), [c for c in cases if c.get("expect") not in ("yes", "cost", "no")][:3])
check("...with sensible, nonsensical and means-dependent lines", sum(c["expect"] == "no" for c in cases) >= 15 and sum(c["expect"] != "no" for c in cases) >= 15
      and sum(1 for c in cases if "means" in c) >= 6)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
