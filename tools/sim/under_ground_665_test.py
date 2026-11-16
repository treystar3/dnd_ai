"""(f665) Under the ground: a dungeon's fights take the underground ground, and the hour told to the narrator gives the weather only
under open sky (docs/design/21_play_faults_plan.md, D3; found in play: docs/play/2026-11-15_play_findings.md 2.14, dungeon rooms told
with canopy, rain, creek beds and wind: a dungeon took the biome of the land above, and the time label always added the weather;
the owner's decision Q14 is that weather is for open sky).
Held here: every dungeon of the world, whatever its land, takes the underground family; a place above keeps its own; the hour in a
dungeon says it is under the ground and names no weather, and above it still does.
Run: python tools/sim/under_ground_665_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
simlib.quiet_console()
from engine import battlefield_builder as bb

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("under_ground_665_test", seed=2, location="trading_square")
ws, world = g.scene, g.scene.world
from engine import dungeons as dg
lands = [p for p in world.places.values() if not p.parent and p.biome and p.type not in ("city", "town", "village")]
dungeons = [dg.entrance_place({"place": p.id, "entrance": f"t665_{p.id}", "name": "The Test Warren", "theme": "cave"}, world) for p in lands]
check("(a dungeon beneath every kind of land)", len({p.biome for p in dungeons}) >= 4, sorted({p.biome for p in dungeons}))
families = {p.id: bb.family_of(p, world) for p in dungeons}
check("2.14: every dungeon, whatever the land above it, fights on underground ground", all(v == "underground" for v in families.values()),
      {k: v for k, v in families.items() if v != "underground"})
above = [p for p in world.places.values() if p.type in ("forest", "hills", "fields") and not p.parent]
check("...while a place above keeps its own", above and all(bb.family_of(p, world) != "underground" for p in above),
      [(p.id, bb.family_of(p, world)) for p in above if bb.family_of(p, world) == "underground"])
label = ws.time_label()
check("the hour above names the weather", "weather:" in label, label)
world.add_place(dungeons[0])
ws.player.location = dungeons[0].id
label = ws.time_label()
check("...and in a dungeon it says under the ground and names no weather", "weather" not in label and "under the ground" in label, label)
shutil.rmtree("saves/under_ground_665_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
