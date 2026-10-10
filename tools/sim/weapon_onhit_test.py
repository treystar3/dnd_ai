"""Weapons can roll on-hit properties: vampiric, envenom, ignite, jolt, siphon mana, siphon stamina."""
import random, sys, collections
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import items, loot, combat as C
from engine.combat import Bonus
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)
NEW = ["vampiric", "envenom_chance", "ignite_chance", "jolt_chance", "siphon_mana", "siphon_stamina"]
rng = random.Random(4)
seen, armor_leak, ranges = collections.defaultdict(set), set(), collections.defaultdict(lambda: [10**9, 0])
for b in items.CATALOG.values():
    if b.slot in ("none", "neck", "ring"):
        continue
    for r in ("uncommon", "rare", "epic", "legendary"):
        for _ in range(120):
            it = items.make(b.id, r, rng.randint(5, 300), rng=rng); loot.roll_gear(it, rng)
            for p in it.properties:
                if p.modifies in NEW:
                    if b.is_weapon:
                        seen[loot.gear_kind(b)].add(p.modifies)
                        lo, hi = ranges[(p.modifies, r)]; ranges[(p.modifies, r)] = [min(lo, p.magnitude), max(hi, p.magnitude)]
                    else:
                        armor_leak.add(b.id)
for kind in ("weapon.melee", "weapon.finesse", "weapon.ranged", "weapon.focus"):
    check(f"{kind} weapons can roll all six on-hit properties", seen[kind] == set(NEW), sorted(set(NEW) - seen[kind]))
check("armor never rolls them", not armor_leak, sorted(armor_leak)[:3])
L = C.RULES["loot"]["onhit_magnitude"]
check("magnitudes stay in their rarity ranges", all(L[s][r][0] <= v[0] and v[1] <= L[s][r][1] for (s, r), v in ranges.items()), dict(list(ranges.items())[:3]))
text = [items._describe_effect(items.Effect(modifies=m, trigger="always", magnitude=5)) for m in NEW]
check("each has readable card text", all("{" not in t and "_" not in t for t in text), text)

def F(id, side, **k):
    d = dict(id=id, name=id, side=side, level=40, attrs={a: 14 for a in C.ATTRIBUTES}, hp=100000, max_hp=100000, weapon_damage=50, armor=0, ward=0,
             stamina=500, max_stamina=1000, mana=500, max_mana=1000)
    d.update(k); return C.Fighter(**d)
def fight(stat, mag, n=300):
    out = collections.Counter(); heal = mana = stam = 0
    for i in range(n):
        p = F("p", "player", bonuses=[Bonus(modifies=stat, trigger="always", magnitude=mag)]); p.hp = 50000
        e = F("e", "enemy", band="engaged")
        cmb = C.Combat(fighters=[p, e]); h = e.hp
        C.apply_damage(cmb, p, e, 1.0, "hits", random.Random(i))
        if e.hp < h:
            out["hit"] += 1
            out.update(set(e.statuses))
            heal += p.hp - 50000; mana += p.mana - 500; stam += p.stamina - 500
    return out, heal, mana, stam
o, heal, mana, stam = fight("vampiric", 10)
check("vampiric heals you from damage you deal", heal > 0 and mana == 0 and stam == 0, heal)
for stat, st in (("envenom_chance", "poisoned"), ("ignite_chance", "burning"), ("jolt_chance", "stunned")):
    o, *_ = fight(stat, 50)
    check(f"{stat} puts {st} on about half of hits", o["hit"] > 100 and 0.3 < o[st] / o["hit"] < 0.7, (o[st], o["hit"]))
    o0, *_ = fight(stat, 0)
    check(f"no {stat}, no {st}", o0[st] == 0)
o, heal, mana, stam = fight("siphon_mana", 3)
check("siphon mana restores mana per hit", mana > 0 and stam == 0 and heal == 0, mana)
o, heal, mana, stam = fight("siphon_stamina", 3)
check("siphon stamina restores stamina per hit", stam > 0 and mana == 0, stam)
# a rolled property on the equipped weapon reaches the fighter
from core.models import ItemProperty
ch, _ = simlib.make_character("warrior", random.Random(2))
w = next(b for b in items.CATALOG.values() if b.is_weapon and b.slot == "main_hand")
it = items.make(w.id, "rare", 3, rng=random.Random(1)); it.properties = [ItemProperty(modifies="ignite_chance", trigger="always", magnitude=9)]
try:
    ch.equipment["main_hand"] = it
    f = C.fighter_from_character(ch)
    check("the weapon's property reaches the fighter", any(b.modifies == "ignite_chance" and b.magnitude == 9 for b in f.bonuses), [b.modifies for b in f.bonuses][:6])
except Exception as e:
    check("the weapon's property reaches the fighter", False, repr(e)[:150])
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)
