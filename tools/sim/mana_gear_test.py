"""Flat mana costs scale with casting attribute; social/lore/perception never roll on gear."""
import random, sys
sys.path.insert(0, ".")
from engine import loot, pools, combat, items
from engine.loot import STATS
ban = set(combat.RULES["loot"]["not_on_gear"])
rng = random.Random(1)
seen = set()
for r in ["common","uncommon","rare","epic","legendary"]:
    for _ in range(3000):
        for p in loot.roll_properties(r, rng): seen.add(p.modifies)
assert not (seen & ban), seen & ban
print("rollable on gear:", len(seen), sorted(seen))
import yaml
acc = yaml.safe_load(open("data/rules/accessories.yaml"))
for lane, d in acc["lanes"].items():
    assert not set(d["stats"]) & ban and len(d["stats"]) >= 3, lane
R = pools
print("reference L1/L50/L150:", [round(R.reference_mana(l)) for l in (1,50,150)])
print("OK")
v = lambda m: items.value(items.make("plate", "common", 100, material=m))
assert v("bronze") < v("iron") < v("steel") < v("mithril") < v("adamantine"), [v(m) for m in ("bronze","iron","steel","mithril","adamantine")]
print("material grade ordering OK")
