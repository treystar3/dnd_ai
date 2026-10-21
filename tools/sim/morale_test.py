"""Morale and the enemy archetypes (B5): a fight has a second way to end. Kill the pack's leader, or drop half of them, and the rest
may break and run; the mindless and the sworn never do. Relentless brutes wind up every blow; stalkers open from concealment."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import battlefield as bf, battlefield_builder as bb, behaviors, combat
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def wolf(i, level=3, rank="normal", category="beast", fearless=False):
    f = combat.Fighter(id=f"e{i}", name=f"wolf {i}", side="enemy", level=level, attrs={"strength": 10},
                       hp=10, max_hp=10, rank=rank, category=category, pace="fast", weapon_damage=4, family="pack_hunter")
    f.behaviors = {"fearless": 1} if fearless else {"flee_low": 0.25}
    return f

def fight(*fs):
    p = combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                       hp=500, max_hp=500, weapon_damage=10, hold=1)
    f = combat.Combat(fighters=[p] + list(fs))
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    return f

# ---- the alpha falls and the pack may break
routed = 0
for seed in range(30):
    alpha = wolf(0, level=6, rank="elite")
    pack = [wolf(i) for i in (1, 2, 3)]
    f = fight(alpha, *pack)
    alpha.hp = 1
    combat.take_damage(f, alpha, 5, f.player, random.Random(seed))
    routed += sum(1 for w in pack if w.fled)
check("kill the alpha and the pack often scatters", 20 <= routed <= 85, routed)

# ---- half down may break the rest; the fearless and the mindless never rout
routed = skeletons = 0
for seed in range(30):
    a, b, c, d = wolf(0), wolf(1), wolf(2), wolf(3)
    f = fight(a, b, c, d)
    a.hp = c.hp = 1
    combat.take_damage(f, a, 5, f.player, random.Random(seed))
    combat.take_damage(f, c, 5, f.player, random.Random(seed + 100))
    routed += sum(1 for w in (b, d) if w.fled)
    s1, s2, s3 = (wolf(i, category="undead") for i in (5, 6, 7))
    s2.rank = "elite"; s2.level = 6
    g = fight(s1, s2, s3)
    s2.hp = 1
    combat.take_damage(g, s2, 5, g.player, random.Random(seed))
    skeletons += sum(1 for w in (s1, s3) if w.fled)
    br = wolf(8, fearless=True)
    al = wolf(9, rank="elite", level=6)
    h = fight(al, br)
    al.hp = 1
    combat.take_damage(h, al, 5, h.player, random.Random(seed))
    skeletons += (1 if br.fled else 0)
check("half the pack down and the rest may run", routed >= 8, routed)
check("the undead and the fearless never rout", skeletons == 0, skeletons)

# ---- a routed fight is a won fight, with everyone released
a, b = wolf(0, rank="elite", level=6), wolf(1)
f = fight(a, b)
bf.engage(f, b, f.player)
for seed in range(60):
    b.fled = False
    a.hp = 1
    combat.take_damage(f, a, 5, f.player, random.Random(seed))
    if b.fled:
        break
check("a routed wolf is out of the fight and out of everyone's grasp", b.fled and not f.enemies() and b.id not in f.player.engaged_with)

# ---- relentless brutes wind up every blow they can
import types
troll = combat.Fighter(id="t", name="the troll", side="enemy", level=6, attrs={"strength": 16}, hp=300, max_hp=300,
                       rank="elite", size="Huge", weapon_damage=12, pace="slow", family="troll", behaviors={"relentless": 1})
p = combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                   hp=5000, max_hp=5000, weapon_damage=10, hold=1)
f = combat.Combat(fighters=[p, troll]); f.battlefield = bb.duel_ground(); bf.place_fighters(f)
combat.enemy_turn(f, troll, random.Random(1))
check("a relentless brute's first act is the wind-up, named at its target", troll.winding.get("target") == "player", troll.winding)

# ---- stalkers open from concealment when the ground offers it
field = bb.Battlefield(zones={"z1": bb.BattleZone(id="z1", name="the trail", tags=["open"]),
                              "z2": bb.BattleZone(id="z2", name="dense brush", tags=["concealed"])},
                       edges=[bb.BattleEdge(a="z1", b="z2")], start="z1")
cat = combat.Fighter(id="c", name="the panther", side="enemy", level=4, attrs={"strength": 12}, hp=40, max_hp=40,
                     weapon_damage=8, pace="fast", family="predator", behaviors={"stalk": 1, "pounce": 40})
f = combat.Combat(fighters=[p.model_copy(deep=True), cat]); f.battlefield = field
bf.place_fighters(f)
check("the stalker begins in the brush, concealed", cat.zone_id == "z2" and "concealed" in cat.position_tags, (cat.zone_id, cat.position_tags))
check("...where arrows cannot find it", not bf.attack_access(f, f.player, cat, "ranged").ok)
bf.enter_zone(f, cat, "z1")
check("...and loses the concealment when it comes out", "concealed" not in cat.position_tags)

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
