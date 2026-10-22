"""A zone's roster is drawn by fit as well as rarity (data/rules/creatures.yaml fit): creatures whose level range sits where the zone's
band sits come before those that merely overlap it, so the high zones hold peers and the low ones vary by seed. Anchors stay."""
import random, sys
sys.path.insert(0, ".")
import yaml
from world.loader import load_world
from engine import encounters
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
R = yaml.safe_load(open("data/rules/creatures.yaml", encoding="utf-8"))
E = encounters.E
wild = [p for p in world.places.values() if p.danger and p.type not in ("dungeon", "road")]

def draw(seed, place, fit):
    found = world.creature_candidates(place.id, R["rarity_weight"], fit)
    rng = random.Random(f"{seed}:roster:{place.id}")
    roster = list(place.anchors)
    pool = [f for f in found if f[0].id not in roster]
    while pool and len(roster) < E["roster_size"]:
        pick = rng.choices(pool, weights=[w for _, w in pool])[0]
        roster.append(pick[0].id)
        pool.remove(pick)
    return roster

def apart(place, roster):
    centre = (place.danger[0] + place.danger[1]) / 2
    return sum(abs((world.bestiary[c].levels[0] + world.bestiary[c].levels[1]) / 2 - centre) for c in roster) / max(1, len(roster))

for seed in (1, 2, 3):
    plain = sum(apart(p, draw(seed, p, None)) for p in wild) / len(wild)
    fitted = sum(apart(p, draw(seed, p, R["fit"])) for p in wild) / len(wild)
    check(f"seed {seed}: rosters drawn by fit sit nearer their zone's band ({fitted:.1f} levels from the centre, was {plain:.1f})", fitted < plain * 0.9, (fitted, plain))
    check(f"seed {seed}: every roster is as full as before", all(len(draw(seed, p, R["fit"])) == len(draw(seed, p, None)) for p in wild))
high = [p for p in wild if p.danger[1] >= 150]
tops = [world.bestiary[c].levels[1] for p in high for c in draw(1, p, R["fit"])]
tops_plain = [world.bestiary[c].levels[1] for p in high for c in draw(1, p, None)]
check("the top zones' rosters reach higher levels than before", sum(tops) / len(tops) > sum(tops_plain) / len(tops_plain), (sum(tops) / len(tops), sum(tops_plain) / len(tops_plain)))
def peers(fit):
    rows = [(p, c) for s in (1, 2, 3) for p in high for c in draw(s, p, fit)]
    return sum(1 for p, c in rows if world.bestiary[c].levels[1] >= (p.danger[0] + p.danger[1]) / 2) / len(rows)
check(f"more of a top zone's roster can reach the band's upper half ({peers(R['fit']):.0%}, was {peers(None):.0%})", peers(R["fit"]) > peers(None) + 0.1)
gw = draw(1, world.places["greywood"], R["fit"])
check("the Greywood keeps its wolf and a full roster", "wolf" in gw and len(gw) == E["roster_size"], gw)
c = world.creature_candidates("greywood", R["rarity_weight"], R["fit"])
w = {cr.id: wt for cr, wt in c}
near = [cr for cr, _ in c if abs((cr.levels[0] + cr.levels[1]) / 2 - 3.5) <= 2 and cr.rarity == "common"]
far = [cr for cr, _ in c if (cr.levels[0] + cr.levels[1]) / 2 >= 12 and cr.rarity == "common"]
check("a common creature of the wood's own level outweighs a common one whose range only brushes it", near and far and min(w[x.id] for x in near) > max(w[x.id] for x in far), ([x.id for x in near][:3], [x.id for x in far][:3]))
check("no candidate weighs nothing", all(wt > 0 for _, wt in c))
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
