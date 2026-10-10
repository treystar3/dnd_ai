"""Far lands: every new zone rolls creatures, builds fighters, makes a dungeon; every hall posts a board; relic shelves cover the new cities."""
import random, sys, tempfile
sys.path.insert(0, ".")
from world.loader import load_world
from engine import encounters, combat, dungeons, quests, property as P
import yaml

world = load_world()
bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

FAR = ["ash_wastes", "cinder_caldera", "stormcrown_heights", "thunder_spires", "deep_roads_tunnels", "lightless_deep",
       "drowned_shore", "jade_maw_jungle", "sepulchre_fields"]
R = yaml.safe_load(open("data/rules/creatures.yaml"))["rarity_weight"]
for z in FAR:
    pl = world.places[z]
    c = world.creature_candidates(z, R)
    check(f"{z} has creatures", len(c) >= 20, str(len(c)))
    rng = random.Random(z)
    lvls = []
    for cr, _ in c:
        lo, hi = max(pl.danger[0], cr.levels[0]), min(pl.danger[1], cr.levels[1])
        f = combat.fighter_from_creature(cr, rng.randint(lo, hi), "normal", "e1", cr.name.lower(), "near")
        assert f.hp > 0 and f.max_hp > 0
        lvls.append(f.level if hasattr(f, "level") else 0)
    d = dungeons.generate(pl, world, f"t:{z}", 0)
    check(f"{z} dungeon", d is not None and len(d["floors"]) >= 3, (d or {}).get("theme", "none"))

check("towns reachable", all(world.path("parth", t) for t in ["cinderhold", "hrimgard", "dunmarrow", "brinewatch", "amaranth"]))
for t in ["cinderhold", "hrimgard", "dunmarrow", "brinewatch", "amaranth"]:
    r = world.path("parth", t)
    print("   parth ->", t, r[1], "min,", round(r[1] / 1440, 1), "days")
for h in ["cinderhold_guild", "hrimgard_guild", "dunmarrow_guild"]:
    t = quests.hall_tier(world, h)
    check(f"{h} is a top-tier hall", t["tier"] >= 3 and t["reward_mult"] > 1.5, str(t["reward_mult"]))
check("old halls unchanged", [quests.hall_tier(world, h)["tier"] for h in
      ["ironvein_guild", "frostholm_guild", "sunspire_guild", "valecourt_guild", "eldervale_guild", "riverhaven_guild"]] == [1, 2, 2, 1, 0, 0])
check("dealer per city", len(P.dealer_towns(world)) == 11, str(len(P.dealer_towns(world))))
check("relic shelves filled", len(set(P.stock(world, 7).values())) == 11)
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)
