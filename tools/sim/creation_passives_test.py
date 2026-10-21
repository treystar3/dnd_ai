"""Creation passives are mechanics only (B8): fifteen offers, each one a mechanic that changes how a fight or a day plays, never a bare
always-on number; flat stat passives remain at the trainers. The four battlefield hooks do what their lines say."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from character import creation
from core.rules import MECHANICS
from engine import battlefield as bf, battlefield_builder as bb, combat
from llm.contracts import ClassInterpretation
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

interp = ClassInterpretation(archetype="warrior", custom_class="Shieldmaiden", summary="s", families=["warrior", "guardian"],
                             primary_attributes=["strength"], focus="balanced", uses_companions=False,
                             combat_identity="a wall of iron", themes=["guardian", "shield"])
ps = creation.generate_passives(interp, [])
check("fifteen offers, all of them mechanics, none a bare stat", len(ps) == 15 and all(p.mechanic for p in ps),
      [(p.name, p.mechanic) for p in ps[:4]])
check("world mechanics are among them (the day outside the fight is a real offer)",
      sum(MECHANICS[p.mechanic].kind == "world" for p in ps) >= 2)
drawn = set()
for seed in range(12):
    drawn |= {o.mechanic for o in creation.draw_mechanics(interp, random.Random(seed)).values()}
check("the battlefield enablers are no longer born with: creation draws only rules",
      not ({"shield_bearer", "stancework", "sure_footed", "press_the_opening"} & drawn), sorted(drawn))
taught_draw = set()
for seed in range(12):
    taught_draw |= {o.mechanic for o in creation.draw_mechanics(interp, random.Random(seed), where="taught").values()}
check("...a guardian learns them from instructors instead",
      {"shield_bearer", "stancework", "sure_footed", "press_the_opening"} & taught_draw != set(), sorted(taught_draw))

# ---- the four hooks do what they say
def man(i, side="enemy", hp=300):
    return combat.Fighter(id=f"m{i}", name=f"m{i}", side=side, level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, stamina=100, max_stamina=100, weapon_damage=8, hold=1)
p = man(0, side="player"); w = man(1)
f = combat.Combat(fighters=[p, w]); f.battlefield = bb.duel_ground(); bf.place_fighters(f)
p.legendary["stancework"] = 1
from engine.combat import Move
combat.act_ability(f, p, Move(id="s", name="Iron Wall", effect="defense", tier="light", reach="self", resource="stamina"), None, random.Random(1))
st = p.stamina
f.round = 2
combat.start_turn(p, f)
check("stancework: holding a stance costs nothing", any(b.get("kind") == "stance" for b in p.buffs.values()) and p.stamina >= st)

p = man(0, side="player"); w = man(1)
f = combat.Combat(fighters=[p, w]); f.battlefield = bb.duel_ground(); bf.place_fighters(f)
bf.engage(f, w, p)
p.legendary["sure_footed"] = 1
before = p.hp
for seed in range(5):
    combat.retreat(f, p, random.Random(seed))
check("sure-footed: pulling away never costs a parting blow", p.hp == before)

p = man(0, side="player"); w = man(1)
f = combat.Combat(fighters=[p, w]); f.battlefield = bb.duel_ground(); bf.place_fighters(f)
def dealt(mech, open_, seeds=40):
    tot = 0.0
    for s in range(seeds):
        pp = man(0, side="player"); ww = man(1, hp=10**6)
        g = combat.Combat(fighters=[pp, ww]); g.battlefield = bb.duel_ground(); bf.place_fighters(g)
        if mech:
            pp.legendary["press_the_opening"] = 25
        if open_:
            combat.leave_open(g, ww)
        combat.apply_damage(g, pp, ww, 1.0, "strikes", random.Random(s))
        tot += 10**6 - ww.hp
    return tot / seeds
check("press the opening: more damage into an open enemy", dealt(True, True) > dealt(False, True) * 1.1,
      (dealt(True, True), dealt(False, True)))

ch, _ = simlib.make_character("warrior", random.Random(2))
base = combat.fighter_from_character(ch).hold
from core.models import Passive, PowerTier
ch.passives.append(Passive(id="sb", name="Line Holder", description="d", tier=PowerTier.LIGHT, mechanic="shield_bearer", value=1))
check("shield-bearer: the line is one wider", combat.fighter_from_character(ch).hold == base + 1,
      (base, combat.fighter_from_character(ch).hold))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
