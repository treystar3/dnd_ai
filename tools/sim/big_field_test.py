"""Big fights (f224): camp and hideout assaults, boss fights and fights of 6+ enemies are fought on a larger, chained field (camp, lair
or wild layout); ordinary encounters and duels keep their small ground. Everyone begins where their role puts them: you at the edge,
their fighters in the middle, archers on high or covered ground, the leader or boss at the back, reinforcements walking in."""
import random
import sys
import types
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import battlefield as bf, battlefield_builder as bb, combat
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def F(fid, side, reach="melee", rank="normal", **kw):
    return combat.Fighter(id=fid, name=fid, side=side, level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=200, max_hp=200,
                          weapon_damage=8, reach=reach, rank=rank, hold=1, behaviors={"fearless": 1}, **kw)

def fight_on(field, enemies, reserves=()):
    p = F("player", "player")
    f = combat.Combat(fighters=[p] + list(enemies), record=False)
    f.reserves = list(reserves)
    f.battlefield = field
    bf.place_fighters(f)
    return f, p

# ---- which fights are big
grunts = [F(f"e{i}", "enemy") for i in range(3)]
check("an ordinary encounter stays small", bb.big_kind(grunts, []) == "")
check("six enemies make a big fight", bb.big_kind([F(f"e{i}", "enemy") for i in range(6)], []) == "wild")
check("...reserves counted", bb.big_kind(grunts, [F("r1", "enemy"), F("r2", "enemy"), F("r3", "enemy")]) == "wild")
check("a boss makes a big fight", bb.big_kind([F("b", "enemy", rank="boss")], []) == "wild")
check("a camp or lair asked for is kept", bb.big_kind(grunts, [], "camp") == "camp" and bb.big_kind(grunts, [], "lair") == "lair")

# ---- the wild layout: 4-6 zones, chained, the far end 3 steps from where you begin
sizes, reach = set(), set()
for sd in range(60):
    for fam in bb.FAMILIES:
        field = bb.build_big(fam, "wild", random.Random(sd))
        sizes.add(len(field.zones))
        reach.add(field.steps(field.player_start, field.back))
        f, _ = fight_on(field, [])
        if bf.validate(f):
            check(f"wild field {fam}/{sd} is sound", False, bf.validate(f))
check("big wild fields have 4 to 6 zones", sizes <= {4, 5, 6} and len(sizes) >= 2, sizes)
check("...and the far end is 3 steps from where you begin", reach == {3}, reach)
small = {len(bb.build(fam, random.Random(sd)).zones) for sd in range(40) for fam in bb.FAMILIES}
check("ordinary fields are unchanged: 1 to 3 zones", small <= {1, 2, 3}, small)

# ---- the camp: you at the approach, fighters among the tents, archers on the platform, the leader at the back
leader, a, b, archer = F("chief", "enemy"), F("e1", "enemy"), F("e2", "enemy"), F("bow", "enemy", reach="ranged")
reserves = [F("r1", "enemy"), F("r2", "enemy")]
field = bb.build_big("forest", "camp", random.Random(1))
f, p = fight_on(field, [leader, a, b, archer], reserves)
Z = field.zones
check("the camp is sound", not bf.validate(f), bf.validate(f))
check("you begin at the approach", Z[p.zone_id].name == "the approach to the camp")
check("its fighters begin among the tents", Z[a.zone_id].name == "between the tents" and a.zone_id == b.zone_id)
check("its archer takes the watch platform, on high ground", Z[archer.zone_id].name == "the watch platform" and "elevated" in archer.position_tags)
check("its leader waits in the tent at the back", Z[leader.zone_id].name == "the leader's tent")
check("the leader is three steps from you, through the gate", field.steps(p.zone_id, leader.zone_id) == 3)
check("the platform is a climb from the tents", field.hard(a.zone_id, archer.zone_id))
combat.muster(f)
r = f.get("r1")
check("reinforcements walk in from the back of the camp", r is not None and Z[r.zone_id].name == "the leader's tent", r and r.zone_id)
s = F("summon_x", "ally")
combat.enters(f, s)
check("an ally joining mid-fight stands with you, not with them", s.zone_id == p.zone_id)

# ---- the lair: the boss on the dais, its brood out of the alcove
boss, minion = F("boss", "enemy", rank="boss"), F("m1", "enemy")
field = bb.build_big("underground", "lair", random.Random(2))
f, p = fight_on(field, [boss, minion], [F("r1", "enemy")])
Z = field.zones
check("the lair is sound", not bf.validate(f), bf.validate(f))
check("you begin at the entrance, the boss on its dais", Z[p.zone_id].name == "the entrance" and Z[boss.zone_id].name == "the dais"
      and "elevated" in boss.position_tags)
check("its minions on the chamber floor", Z[minion.zone_id].name == "the chamber floor")
combat.muster(f)
check("what it calls comes out of the alcove", Z[f.get("r1").zone_id].name == "a dark alcove")

# ---- a wild big fight: you at an edge, they in the middle, a boss at the far end
boss, a = F("boss", "enemy", rank="boss"), F("e1", "enemy")
field = bb.build_big("forest", "wild", random.Random(3))
f, p = fight_on(field, [boss, a])
check("in a big wild fight you come in from a side, they hold the middle", p.zone_id == field.player_start and a.zone_id == "z1")
check("...and the boss begins at the far end", boss.zone_id == field.back and field.steps(p.zone_id, boss.zone_id) == 3)

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
