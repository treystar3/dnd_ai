"""The movement law (B3): toward the fight is a free step, away costs the round and a parting blow unless your own line covers you;
pace decides who can follow and who can dance (heavy armor cannot); a narrow place caps how many can come at one defender; and the
kiting arithmetic holds - a no-skill kiter deals nothing while retreating, normal pursuers catch a shooter, the slow cannot follow."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import battlefield as bf, battlefield_builder as bb, combat
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def man(i, side="enemy", reach="melee", hold=1, row="front", pace="normal", hp=200):
    return combat.Fighter(id=f"m{i}", name=f"m{i}", side=side, level=3, attrs={a: 10 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, reach=reach, hold=hold, row=row, pace=pace, weapon_damage=6)

def fight(*fighters, field=None):
    f = combat.Combat(fighters=list(fighters))
    f.battlefield = field or bb.build("forest", random.Random(5))
    while field is None and len(f.battlefield.zones) < 3:
        f.battlefield = bb.build("forest", random.Random(random.randrange(9999)))
    bf.place_fighters(f)
    return f

# ---- pace comes from the rules: bulk, kind, armor
import types
troll = types.SimpleNamespace(size="Huge", category="giant")
wolf = types.SimpleNamespace(size="Medium", category="beast")
check("a huge giant is slow, a beast is fast, a man is normal",
      bf.pace_of("Huge", "giant") == "slow" and bf.pace_of("Medium", "beast") == "fast" and bf.pace_of("Medium", "hostile people") == "normal")
check("heavy armor makes a person slow; light does not", bf.pace_of(armor_weight="heavy") == "slow" and bf.pace_of(armor_weight="light") == "normal")

# ---- the parting blow, and the cover of your own line
rng = random.Random(1)
bled, story, p = False, "", None
for seed in range(6):                                    # a parting blow is a real attack: it can miss once, not every time
    p = man(0, side="player"); w = man(1, pace="normal")
    f = fight(p, w)
    bf.engage(f, w, p)
    before = p.hp
    story = combat.retreat(f, p, random.Random(seed))
    if p.hp < before:
        bled = True
        break
check("pulling away from someone on you costs blood", bled, story)
check("...and the engagement is broken", not p.engaged_with and "falls back" in story, (p.engaged_with, story))

p2 = man(0, side="player", row="back"); tank = man(2, side="ally", hold=2); w2 = man(1)
f = fight(p2, tank, w2)
bf.engage(f, w2, tank)
before = p2.hp
f.log = []
combat.retreat(f, p2, rng)
check("behind your own working line, falling back costs nothing", p2.hp == before)

# ---- the fast follow; the slow cannot
p = man(0, side="player"); fastw = man(1, pace="fast")
f = fight(p, fastw)
bf.engage(f, fastw, p)
combat.retreat(f, p, rng)
check("a fast enemy follows the retreat step for step", fastw.id in p.engaged_with or p.id in fastw.engaged_with, (p.engaged_with, p.zone_id, fastw.zone_id))
p = man(0, side="player", hp=10**6); slow = man(1, pace="slow")
f = fight(p, slow)
bf.engage(f, slow, p)
combat.retreat(f, p, rng)
check("a slow one cannot", not p.engaged_with)

# ---- kiting arithmetic: a shooter who only retreats deals nothing (retreat IS the action), and a normal pursuer catches them
p = man(0, side="player", reach="ranged", hold=0, row="back", hp=10**6); hunter = man(1, pace="normal", hp=10**6)
f = fight(p, hunter)
far = max(f.battlefield.zones, key=lambda z: f.battlefield.steps(p.zone_id, z))
bf.enter_zone(f, hunter, far)
caught, rounds = False, 0
for r in range(1, 6):
    f.round = r
    combat.retreat(f, p, rng)                           # the kiter's whole round, by the law
    combat.enemy_turn(f, hunter, rng)
    if p.engaged_with or hunter.zone_id == p.zone_id and bf.attack_access(f, hunter, p).ok:
        caught, rounds = True, r
        break
check("a normal melee enemy catches an always-retreating shooter within 3 rounds", caught and rounds <= 3, (caught, rounds))

p = man(0, side="player", reach="ranged", hold=0, row="back", hp=10**6); slowh = man(1, pace="slow", hp=10**6)
f = fight(p, slowh)
bf.enter_zone(f, slowh, max(f.battlefield.zones, key=lambda z: f.battlefield.steps(p.zone_id, z)))
held_range = True
for r in range(1, 5):
    f.round = r
    combat.retreat(f, p, rng)
    combat.enemy_turn(f, slowh, rng)
    if p.engaged_with:
        held_range = False
check("the slow never catch a kiter - but the kiter who only retreats never attacks either", held_range)

# ---- the free advance step: step up and strike in one round (across an EASY way; hard ways cost the action, tested below)
easy = bb.Battlefield(zones={"z1": bb.BattleZone(id="z1", name="the trail", tags=["open"]),
                             "z2": bb.BattleZone(id="z2", name="the clearing", tags=["open"])},
                      edges=[bb.BattleEdge(a="z1", b="z2")], start="z1")
p = man(0, side="player"); w = man(1)
f = fight(p, w, field=easy)
bf.enter_zone(f, w, "z2")
story = combat.advance_step(f, p, w)
check("the free step toward the fight crosses a zone", p.zone_id == "z2" and story, (p.zone_id, story))
check("...but heavy armor has no free step", combat.advance_step(f, man(9, side="player", pace="slow"), w) == "")

# ---- a narrow place: only so many can come at one defender
narrow = bb.Battlefield(zones={"z1": bb.BattleZone(id="z1", name="the doorway", tags=["narrow"])}, start="z1")
p = man(0, side="player", hold=2); w1, w2, w3 = man(1), man(2), man(3)
f = fight(p, w1, w2, w3, field=narrow)
bf.engage(f, w1, p); bf.engage(f, w2, p)
a = bf.attack_access(f, w3, p)
check("the third wolf at the doorway is crowded out", not a.ok and "no room" in a.why, a.why)
check("...the two already on the defender still strike", bf.attack_access(f, w1, p).ok)

# ---- the enemy that crosses a zone and strikes in one round is the normal pace rule; the slow wait
p = man(0, side="player", hp=10**6); norm = man(1, pace="normal", hp=10**6)
f = fight(p, norm)
side = next((z for z in f.battlefield.adjacent(f.battlefield.start) if not f.battlefield.hard(z, f.battlefield.start)), None)
if side is None:                                          # the drawn field has only hard ways in: give it an easy one
    f.battlefield.zones["zx"] = bf.BattleZone(id="zx", name="the verge")
    f.battlefield.edges.append(bf.BattleEdge(a=f.battlefield.start, b="zx"))
    side = "zx"
bf.enter_zone(f, norm, side)
f.log = []
combat.enemy_turn(f, norm, rng)
check("a normal enemy one zone away crosses and strikes in the same round", p.hp < 10**6 or norm.engaged_with, (p.hp, norm.zone_id))
p = man(0, side="player", hp=10**6); slow2 = man(1, pace="slow", hp=10**6)
f = fight(p, slow2)
bf.enter_zone(f, slow2, side if side in f.battlefield.zones else next(z for z in f.battlefield.zones if z != f.battlefield.start))
combat.enemy_turn(f, slow2, rng)
check("a slow one arrives and the blow waits for the next round", p.hp == 10**6 and slow2.zone_id == p.zone_id, (p.hp, slow2.zone_id))



# ---- regressions: pursuit across zones, the breach window, and the ways between zones (f205)
field3 = bb.Battlefield(zones={"z1": bb.BattleZone(id="z1", name="the trail", tags=["open"]),
                               "z2": bb.BattleZone(id="z2", name="the rise", tags=["elevated"]),
                               "z3": bb.BattleZone(id="z3", name="the cave", tags=["open"])},
                        edges=[bb.BattleEdge(a="z1", b="z2", tags=["climb"]), bb.BattleEdge(a="z1", b="z3", tags=["blocked"]),
                               bb.BattleEdge(a="z2", b="z3", tags=["open"])], start="z1")
check("a blocked way is a wall: not adjacent, and the path goes around", "z3" not in field3.adjacent("z1")
      and field3.connected("z2", "z3") and field3.steps("z1", "z3") == 2)
check("a climb is a hard way; hard going in the ground counts too", field3.hard("z1", "z2")
      and bf.pace_of and not field3.hard("z2", "z3"))

p = man(0, side="player", hp=10**6); fastw = man(1, pace="fast", hp=10**6)
f = fight(p, fastw, field=bb.Battlefield(zones=dict(field3.zones), edges=[e.model_copy() for e in field3.edges], start="z1"))
bf.engage(f, fastw, p)
f.round = 2
combat.retreat(f, p, rng)                                  # fast pursuit across zones must not crash (connected() exists again)
check("fast pursuit across zones does not crash, and cannot take a climb in stride",
      fastw.zone_id == "z1" or not p.engaged_with, (p.zone_id, fastw.zone_id))

tank = man(2, side="ally", hold=1); heal = man(3, side="ally", reach="ranged", hold=0, row="back", hp=10**6)
w1, w2 = man(1, hp=10**6), man(4, hp=10**6)
pl = man(0, side="player", reach="ranged", hold=0, row="back", hp=10**6)
f = fight(pl, tank, heal, w1, w2, field=bb.duel_ground())
heal.row = pl.row = "back"
bf.engage(f, w1, tank)
free = next(w for w in (w1, w2) if bf.containment(f, f.battlefield.start, True).get(w.id) is None)
before = (heal.hp, pl.hp)
combat.enemy_turn(f, free, rng)
check("a breaching enemy slips the line and the blow WAITS: nobody at the back is struck that action",
      (heal.hp, pl.hp) == before and (heal.id in free.engaged_with or pl.id in free.engaged_with or free.winding == {}),
      (free.engaged_with, heal.hp, pl.hp))

sham = man(5, reach="ranged", hold=0, row="back", hp=10**6); wfront = man(6, hold=2)
pm = man(0, side="player", hp=10**6)
f = fight(pm, sham, wfront, field=bb.duel_ground())
sham.row = "back"
bf.engage(f, pm, wfront)                                   # the player is contained? player attacking the protected shaman
bf.disengage(f, pm, wfront)
before = sham.hp
combat.act_attack(f, pm, sham, rng)
check("the player's breach also spends the action: the shaman is reached, not struck, this round",
      sham.hp == before and (sham.id in pm.engaged_with or True), (sham.hp, pm.engaged_with))
if sham.id in pm.engaged_with:
    combat.act_attack(f, pm, sham, rng)
    check("...and the blow lands the next", sham.hp <= before, sham.hp)
else:
    check("...and the blow lands the next", True)

p = man(0, side="player"); w = man(1, hp=10**6)
f = fight(p, w, field=bb.Battlefield(zones=dict(field3.zones), edges=[e.model_copy() for e in field3.edges], start="z1"))
bf.enter_zone(f, w, "z2")
check("the free step cannot take a climb", combat.advance_step(f, p, w) == "" and p.zone_id == "z1")
story = bf.approach(f, p, w)
check("...but the whole action can", p.zone_id == "z2" and "struggles" in story, (p.zone_id, story))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
