"""Blessings cast on allies, and on summons (f222). The old spirit roles (rogue, healer, support) are gone: summons have forms now, and
those are tested in summons_test.py."""
import random, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import combat as C, summons, battlefield as bf, battlefield_builder as bb
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

def F(id, side, hp=100000, **k):
    d = dict(id=id, name=id, side=side, level=40, attrs={a: 14 for a in C.ATTRIBUTES}, hp=hp, max_hp=hp, weapon_damage=50, armor=0, ward=0,
             stamina=1000, max_stamina=1000, mana=1000, max_mana=1000)
    d.update(k)
    return C.Fighter(**d)

def fight(*fs):
    f = C.Combat(fighters=list(fs))
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    return f

def buff(kind="precision", resource="mana", **k):
    return C.Move(id="b", name="Test Buff", effect="buff", tier="light", reach="self", resource=resource,
                  attribute="intelligence" if resource == "mana" else "", buff=kind, **k)

p, foe = F("p", "player"), F("e", "enemy")
cmb = fight(p, foe)
call = C.Move(id="s", name="Call", effect="summon", tier="moderate", reach="self", resource="mana", attribute="intelligence", summon_form="striker")
C.act_ability(cmb, p, call, None, random.Random(1))
s = summons.made(cmb)[0]
mv = buff(); one = C.cost_of(p, mv, cmb)
m0 = p.mana
check("a blessing falls on the caster by default", C.act_ability(cmb, p, mv, foe, random.Random(1)) is None and "b" in p.buffs and "b" not in s.buffs)
p.buffs.clear(); m0 = p.mana
C.act_ability(cmb, p, mv, foe, random.Random(1), give=[s])
check("a blessing can fall on a summon, at the normal price", "b" in s.buffs and "b" not in p.buffs and m0 - p.mana == one, (m0 - p.mana, one))
check("...and works on it", C.mechanics(s, cmb).get("precision", 0) > 0)
C.act_ability(cmb, p, buff("manashield"), foe, random.Random(1), give=[s])
check("a mana shield stays on the caster", "b" in p.buffs and not [k for k, v in s.buffs.items() if v.get("kind") == "manashield"])
elem = buff("imbue", element="fire")
s.buffs.clear(); C.act_ability(cmb, p, elem, foe, random.Random(1), give=[s])
for i in range(20):
    if C.apply_damage(cmb, s, foe, 1.0, "attacks", random.Random(i)):
        break
check("a summon given Imbue adds fire to its blows", any("flares" in x for x in cmb.story), cmb.story[-3:])
print("\nFAILED:" if bad else "\nALL PASS", bad or "")
sys.exit(1 if bad else 0)
