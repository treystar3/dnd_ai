"""The element wheel (f266): ignite and poison as one law for every source, element expressions on hits and as no-damage control spells,
spell forms (bolt, blast, burst, curse, charged), area spells striking one area only, category resistances, and the planner."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import ability_slots as AS, afflictions, battlefield as bf, combat, spellcraft as SC
from engine.battlefield import Battlefield, BattleZone, BattleEdge
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def player(hp=10**5, intel=16, **kw):
    attrs = {a: 10 for a in combat.ATTRIBUTES}
    attrs["intelligence"] = intel
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs=attrs, hp=hp, max_hp=hp, stamina=10**4,
                          max_stamina=10**4, mana=10**5, max_mana=10**5, weapon_damage=12, hold=3, accuracy=200, **kw)

def foe(i=1, hp=10**6, zone="a", **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp,
                          max_hp=hp, weapon_damage=8, behaviors={"fearless": 1}, zone_id=zone, **kw)

def field():
    return Battlefield(zones={z: BattleZone(id=z, name=f"zone {z}") for z in ("a", "b", "c")},
                       edges=[BattleEdge(a="a", b="b"), BattleEdge(a="b", b="c")], start="a")

def fight(*fs):
    f = combat.Combat(fighters=list(fs), record=False)
    f.battlefield = field()
    for x in fs:
        x.zone_id = x.zone_id or "a"
    return f

def spell(name="Bolt", tier="moderate", effect="damage", reach="ranged", element="", expression="", form="", expressions=None, **kw):
    return Move(id=name.lower().replace(" ", "_"), name=name, effect=effect, tier=tier, reach=reach, resource="mana",
                attribute="intelligence", element=element, expressions=expressions or ([expression] if expression else []), spell_form=form, **kw)

rng = random.Random(3)

# ---- ignite: a share of the hit, the strongest wins
p = player(); e = foe(); f = fight(p, e)
p.counters["last_hit"] = 100
combat.add_status(f, e, "burning", 2, p)
check("ignite: half the hit over two rounds", abs(e.ignite - 25) < 0.01, e.ignite)
p.counters["last_hit"] = 40
combat.add_status(f, e, "burning", 2, p)
check("...a smaller ignite changes nothing", abs(e.ignite - 25) < 0.01, e.ignite)
p.counters["last_hit"] = 200
combat.add_status(f, e, "burning", 2, p)
check("...a bigger one replaces it", abs(e.ignite - 50) < 0.01, e.ignite)

# ---- poison: flat stacks of offensive power, no cap, refreshed
p = player(); e = foe(); f = fight(p, e)
power = afflictions.offensive_power(p)
for _ in range(5):
    combat.add_status(f, e, "poisoned", 3, p)
check("poison: five stacks, each 8% of offensive power", len(e.poison) == 5 and abs(e.poison[0] - power * 0.08) < 0.01, e.poison)
check("...it lasts three rounds, refreshed", e.statuses["poisoned"] == 3)
h = e.hp; combat.start_turn(e, f)
check("...and ticks for the sum of the stacks", abs((h - e.hp) - round(sum(e.poison) if e.poison else power * 0.4)) <= 1, h - e.hp)

# ---- melee: a weapon's venom follows the same law
p = player(); e = foe(); f = fight(p, e)
p.spell_kind = ""
combat.add_status(f, e, "poisoned", 3, p)
check("melee poison uses weapon power", abs(e.poison[0] - afflictions.offensive_power(p) * 0.08) < 0.01)

# ---- damage expressions
def cast(move, *foes_, target=None, **pk):
    """Cast until the blow lands (the roll is not what is being tested)."""
    import copy
    keep = [copy.deepcopy(x) for x in foes_]
    for seed in range(30):
        fresh = [copy.deepcopy(x) for x in keep]
        p = player(**pk)
        f = fight(p, *fresh)
        combat.act_ability(f, p, move, fresh[foes_.index(target)] if target is not None else fresh[0], random.Random(seed))
        if move.effect != "damage" or move.spell_form in ("curse", "charged") or not any("graze" in l or "miss" in l for l in f.log):
            break
    for orig, new in zip(foes_, fresh):
        orig.__dict__.update(new.__dict__)
    for x in f.fighters:
        if x.side == "enemy":
            x.__dict__ = next(o for o in foes_ if o.id == x.id).__dict__
    return f, p


def control(expr, element, *foes_, target=None, **pk):
    return cast(spell(expr.title(), effect="control", element=element, expression=expr), *foes_, target=target, **pk)

from engine import elements as EL
check("eight elements on the wheel, nature among them", len(EL.WHEEL) == 8 and set(EL.WHEEL) == set(EL.ELEMENTS) and "nature" in EL.ELEMENTS, EL.WHEEL)
check("neighbors close the ring", EL.neighbors("fire") == ["lightning", "radiant"] and EL.neighbors("radiant") == ["fire", "nature"], EL.neighbors("fire"))
for el in EL.WHEEL:
    check(f"{el} has at least 2 damage effects and 1 control spell", len(SC.of_element(el, "damage")) >= 2 and len(SC.of_element(el, "control")) >= 1)

# ---- necrotic
e = foe(hp=1000); f, p = cast(spell("Rot", element="necrotic", expression="rot"), e)
check("rot: maximum health is lost for the fight", e.max_hp < 1000 and e.hp <= e.max_hp, (e.max_hp, e.hp))
e = foe(hp=1000); f, p = cast(spell("Reap", element="necrotic", expression="reap"), e)
check("reap marks the target", e.counters.get("reaped_by") == "player", e.counters)
e.hp = 1
for sd in range(30):
    if e.alive: combat.apply_damage(f, p, e, 5.0, "hits", random.Random(sd))
check("...and if it dies in time it rises for you", any(x.side == "ally" and x.id.startswith("thrall") for x in f.fighters), [x.id for x in f.fighters])
e = foe(); f, p = control("grasping_dead", "necrotic", e)
f.round += 1; combat.start_turn(e, f)
check("grasping dead holds whoever starts there", "grappled" in e.statuses, e.statuses)

# ---- fire
e = foe(ward=500); plain = foe(i=2, ward=500)
f1, _ = cast(spell("Scorch", element="fire", expression="scorch"), e)
f2, _ = cast(spell("Bolt", element="fire", expression="ignite"), plain)
check("scorch ignores ward", (e.max_hp - e.hp) > (plain.max_hp - plain.hp) * 1.2, (e.max_hp - e.hp, plain.max_hp - plain.hp))
e = foe(); f, p = control("smoke", "fire", e)
shooter = foe(i=4, zone="b"); f.fighters.append(shooter)
check("smoke: attacks into it are harder", any(s[0] == "through smoke" for s in bf.hit_modifiers(f, shooter, e)), bf.hit_modifiers(f, shooter, e))

# ---- cold
slow, fresh = foe(1), foe(2)
slow.statuses["slowed"] = 3
r1 = {"steps": []}; r2 = {"steps": []}
SC._CAST[id(p)] = {"exprs": ["shatter"], "tier": "moderate", "name": "Shatter", "once": set()}
check("shatter hits a slowed target harder", SC.hit_mult(f, p, slow, 1.0, r1) == 1.5 and SC.hit_mult(f, p, fresh, 1.0, r2) == 1.0)
SC._CAST.pop(id(p))

# ---- lightning
e = foe(); mv = spell("Overload", element="lightning", expression="overload")
f, p = cast(mv, e)
SC.begin(p, mv); SC.on_hit(f, p, e, 10, random.Random(1)); SC.end(p)
check("overload: two hits in a row stun", "stunned" in e.statuses, (e.statuses, e.counters))
e1, e2 = foe(1), foe(2); e1.winding = {"x": 1}
f, p = control("thunderclap", "lightning", e1, e2)
check("thunderclap breaks wind-ups across the area", not e1.winding)

# ---- poison
e = foe(); f, p = cast(spell("Sicken", element="poison", expression="sickening"), e)
check("sickening weakens", "weakened" in e.statuses)
e = foe(); e.poison = [1, 1, 1]; e.statuses["poisoned"] = 3
f, p = cast(spell("Paralyse", element="poison", expression="paralytic"), e)
check("paralytic slows a well-poisoned target", "slowed" in e.statuses)

# ---- acid
e1, e2 = foe(1), foe(2); f, p = cast(spell("Splash", element="acid", expression="splash"), e1, e2)
check("splash hurts the others in the area", e2.hp < e2.max_hp)
c = foe(1); c.corroded = 50
SC._CAST[id(p)] = {"exprs": ["blister"], "tier": "moderate", "name": "Blister", "once": set()}
check("blister: more damage for armor already eaten", SC.hit_mult(f, p, c, 1.0, {"steps": []}) == 1.5)
SC._CAST.pop(id(p))
e = foe(); f, p = control("caustic_pool", "acid", e)
f.round += 1; combat.start_turn(e, f)
check("caustic pool eats armor of whoever starts there", e.corroded > 0)

# ---- radiant
u = foe(category="undead"); SC._CAST[id(p)] = {"exprs": ["smite"], "tier": "moderate", "name": "Smite", "once": set()}
check("smite hits the undead harder", SC.hit_mult(f, p, u, 1.0, {"steps": []}) == 1.5)
SC._CAST.pop(id(p))
e1, e2 = foe(1), foe(2); f, p = control("flare", "radiant", e1, e2)
check("flare blinds the area", "blinded" in e1.statuses and "blinded" in e2.statuses)

# ---- nature
e = foe(hp=10**6); f, p = cast(spell("Graft", element="nature", expression="barkskin_graft"), e)
check("barkskin graft gives you a barrier", p.shield > 0, p.shield)
e = foe(zone="b"); f, p = cast(spell("Lash", element="nature", expression="vine_lash"), e)
check("vine lash drags the target into melee", e.zone_id == "a" and bf.engaged_pair(p, e), (e.zone_id, e.engaged_with))
e = foe(); f, p = cast(spell("Thorns", element="nature", expression="thornburst"), e)
check("thornburst makes it bleed", "bleeding" in e.statuses)
e = foe(); f, p = control("petrify", "nature", e)
check("petrify turns it to stone", "petrified" in e.statuses, e.statuses)
check("...it cannot be damaged", combat.take_damage(f, e, 100, p, random.Random(1)) == 0)
check("...and loses its turn", not combat.start_turn(e, f))
b = foe(); b.rank = "boss"; f, p = control("petrify", "nature", b)
check("...a boss cannot be petrified", "petrified" not in b.statuses)
e1, e2 = foe(1), foe(2); f, p = control("earthquake", "nature", e1, e2)
check("earthquake knocks the area down", "prone" in e1.statuses and "prone" in e2.statuses)
e = foe(zone="b"); f, p = control("overgrowth", "nature", e)
check("overgrowth hides the area from range", SC.zone_hidden(f, "b"))
e = foe(zone="b"); f, p = control("earthen_barricade", "nature", e)
check("earthen barricade: your area is cover, and getting in is a climb", SC.zone_covered(f, "a") and f.battlefield.hard("b", "a"))

# ---- borrowing at creation
import collections
from core.models import Archetype
from llm.contracts import ClassInterpretation
from engine import ability_traits as AT
ic = ClassInterpretation(archetype=Archetype("mage"), custom_class="X", combat_identity="x", themes=["x"], summary="x",
                         families=["necromancer"], focus="balanced", elements=["necrotic"])
seen, own, far = collections.Counter(), 0, 0
for sd in range(150):
    r = random.Random(sd)
    for s in AS.plan(ic, AT.draw_offers(ic, r, min_functions=5), 5, r):
        for x in s.get("expressions") or []:
            src = SC.EXPR[x]["element"]
            seen[src] += 1
            own += src == "necrotic"
            far += src not in ["necrotic"] + EL.neighbors("necrotic")
tot = sum(seen.values())
check("a necrotic caster mostly uses necrotic effects", own / tot > 0.6, dict(seen))
check("...sometimes borrows from its neighbors (acid, cold)", seen["acid"] + seen["cold"] > 0, dict(seen))
check("...and never from further round the wheel", far == 0, dict(seen))

print("\nFAILED:", bad if bad else "none")
sys.exit(1 if bad else 0)
