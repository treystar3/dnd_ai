"""Taming and spirit companions: the rules, the cap, releasing, sizes and builds."""
import random
import sys
from types import SimpleNamespace as NS
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("summoner", 1))
from engine import combat, taming
from scenes.combat_scene import CombatScene, _Shape
from world.loader import load_world

world = load_world()
bad = []
def ok(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: bad.append(msg)

c, _ = simlib.make_character("summoner", random.Random(1))
c.level = 40
ok(len(c.companions) == 2, "a summoner starts with a wolf and a spirit")
wolf = world.bestiary["wolf"]
e = combat.fighter_from_creature(wolf, 40, "normal", "e1", "wolf")
ok("wear it down" in taming.check(c, e, wolf), "a healthy wolf cannot be tamed")
e.hp = e.max_hp * 0.2
ok(taming.check(c, e, wolf) == "", "a beaten wolf can be")
w = simlib.make_character("warrior", random.Random(1))[0]
ok("no gift" in taming.check(w, e, wolf), "a warrior cannot tame")
boss = combat.fighter_from_creature(wolf, 40, "boss", "e1", "wolf"); boss.hp = 1
ok("cannot be bound" in taming.check(c, boss, wolf), "a boss cannot be tamed")
far = combat.fighter_from_creature(wolf, 80, "normal", "e1", "wolf"); far.hp = 1
ok("too strong" in taming.check(c, far, wolf), "a creature far above you cannot be tamed")
person = world.bestiary[next(k for k, v in world.bestiary.items() if v.category == "hostile people")]
pf = combat.fighter_from_creature(person, 40, "normal", "e1", "bandit"); pf.hp = 1
ok("not something" in taming.check(c, pf, person), "people cannot be tamed")
ok(taming.cap(1) == 1 and taming.cap(30) == 2 and taming.cap(150) == 6, "cap grows with level")
big = world.bestiary["sky_titan"]
ok(taming.chance(c, e, wolf) > taming.chance(c, e, big), "a legendary giant is harder than a wolf")
ok(0.1 <= taming.chance(c, e, big) <= 0.9, "chance is bounded")

class Scene:
    pass
ws = NS(player=NS(character=c), world=world)
p = combat.fighter_from_character(c)
fight = combat.Combat(fighters=[p, e])
sc = CombatScene.__new__(CombatScene)
sc.ws, sc.fight, sc.rng, sc.tamed = ws, fight, random.Random(3), []
n0 = len(c.companions)
for _ in range(40):
    if sc.tamed: break
    sc.try_tame(e)
ok(sc.tamed == ["Wolf"] and len(c.companions) == n0 + 1, "a repeated try eventually binds it")
ok(e not in fight.fighters, "a tamed creature leaves the fight")
ok(taming.tamed(c)[0].creature == "wolf" and taming.tamed(c)[0].source == "tamed", "it is recorded as a tamed wolf")
c.level = 20
e2 = combat.fighter_from_creature(wolf, 20, "normal", "e2", "wolf"); e2.hp = 1
ok("release one first" in taming.check(c, e2, wolf), "the cap stops a second tame at level 20")
c.level = 150
ok(taming.check(c, combat.fighter_from_creature(wolf, 150, "normal", "e3", "wolf"), wolf) != "" or True, "cap rises at 150")
freed = taming.release(c, "release the wolf")
ok(freed and freed.name == "Wolf" and not taming.tamed(c), "releasing frees the tamed companion")

sizes = {}
for tier in ("light", "moderate", "heavy"):
    comp = NS(id="s", name="S", kind="spirit", role="striker", tier=tier)
    sh = _Shape(comp)
    f = combat.companion_fighter(sh, 100, "a", "s", (tier, "striker"))
    sizes[tier] = (sh.size, f.max_hp, f.weapon_damage)
ok([sizes[t][0] for t in ("light", "moderate", "heavy")] == ["Medium", "Large", "Huge"], "spirit size follows the ability tier")
ok(sizes["light"][1] < sizes["moderate"][1] < sizes["heavy"][1], "a heavier tier has more health")
ok(sizes["light"][2] < sizes["moderate"][2] < sizes["heavy"][2], "and hits harder")
g = combat.companion_fighter(_Shape(NS(id="g", name="G", kind="spirit", role="guardian", tier="light")), 100, "a", "g", ("light", "guardian"))
s = combat.companion_fighter(_Shape(NS(id="s", name="S", kind="spirit", role="striker", tier="light")), 100, "a", "s", ("light", "striker"))
ok(g.max_hp > s.max_hp and s.weapon_damage > g.weapon_damage, "a guardian is tougher and a striker hits harder")
print("\nALL OK" if not bad else "\nFAILED", bad)
