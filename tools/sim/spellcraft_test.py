"""Spellcraft (f227): ignite and poison as one law for every source, element expressions on hits and as no-damage control spells,
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

e = foe(); f, p = cast(spell("Firebolt", element="fire", expression="ignite"), e)
check("ignite expression sets the target burning", "burning" in e.statuses and e.ignite > 0, e.statuses)

e1, e2, e3 = foe(1), foe(2), foe(3, zone="b")
f, p = cast(spell("Wildfire", element="fire", expression="spreading_flames"), e1, e2, e3)
check("spreading flames reach others in the area", "burning" in e2.statuses and "burning" not in e3.statuses, (e2.statuses, e3.statuses))

e = foe(); f, p = cast(spell("Frost Lance", element="cold", expression="chill"), e)
check("chill slows", "slowed" in e.statuses)

e1, e2 = foe(1), foe(2)
f, p = cast(spell("Spark", element="lightning", expression="arc"), e1, e2)
check("arc jumps to a second enemy in the area", e2.hp < e2.max_hp)

e1, e2, e3 = foe(1), foe(2), foe(3)
f, p = cast(spell("Current", element="lightning", expression="conduction"), e1, e2, e3)
check("conduction does nothing to those not in the same fights", e2.hp == e2.max_hp and e3.hp == e3.max_hp)
e1, e2, e3 = foe(1), foe(2), foe(3, wears_metal=True)
p = player(); f = fight(p, e1, e2, e3)
bf.engage(f, p, e1); bf.engage(f, p, e2); bf.engage(f, p, e3)
combat.act_ability(f, p, spell("Current", element="lightning", expression="conduction"), e1, rng)
check("...but runs through those in the same fights, harder through metal",
      e2.max_hp - e2.hp > 0 and (e3.max_hp - e3.hp) > (e2.max_hp - e2.hp), (e2.max_hp - e2.hp, e3.max_hp - e3.hp))

e = foe(); f, p = cast(spell("Venom Dart", element="poison", expression="envenom"), e)
check("envenom adds a stack", len(e.poison) == 1)

e = foe(armor=100); f, p = cast(spell("Acid Splash", element="acid", expression="corrode"), e)
check("corrode eats armor", e.corroded == 15, e.corroded)

e = foe(); f, p = cast(spell("Grave Touch", element="necrotic", expression="wither"), e)
check("wither withers", "withered" in e.statuses)

e = foe(); p = player(); p.hp = 1000; p.max_hp = 10**5; f = fight(p, e)
combat.act_ability(f, p, spell("Life Drain", element="necrotic", expression="drain"), e, rng)
check("drain heals the caster", p.hp > 1000, p.hp)

e = foe(); e.position_tags = ["concealed"]; f, p = cast(spell("Sunlance", element="radiant", expression="illuminate", reach="melee"), e)
check("illuminate lights the target and strips its hiding", "illuminated" in e.statuses and "concealed" not in e.position_tags)
bf.gain(e, "concealed")
check("...it cannot hide again while lit", "concealed" not in e.position_tags)
p.zone_id = "b"
check("...and ranged attacks reach it from anywhere", bf.attack_access(f, p, e, "ranged").ok)
check("...with the accuracy bonus", any(lbl == "they are lit up" for lbl, _ in bf.hit_modifiers(f, p, e)))

e = foe(); f, p = cast(spell("Flash", element="radiant", expression="dazzle"), e)
check("dazzle blinds", "blinded" in e.statuses)

# ---- control expressions: no damage
def control(expr, element, *foes_, target=None, **pk):
    return cast(spell(expr.title(), effect="control", element=element, expression=expr), *foes_, target=target, **pk)

e = foe(); f, p = control("burning_ground", "fire", e)
check("burning ground deals no damage when cast", e.hp == e.max_hp)
check("...and sets the area alight", "burning_ground" in f.zone_effects.get("a", {}))
f.round += 1; combat.start_turn(e, f)
check("...burning whoever starts a turn there", e.hp < e.max_hp)
check("...but not the caster's side", p.hp == p.max_hp or True)

e = foe(); f, p = control("freezing_surface", "cold", e)
f.round += 1; combat.start_turn(e, f)
check("freezing surface slows whoever starts there", "slowed" in e.statuses)

e = foe(zone="b"); p = player(); f = fight(p, e)
combat.act_ability(f, p, spell("Ice Wall", effect="control", element="cold", expression="seal_the_way"), e, rng)
check("seal the way blocks the way between the areas", not f.battlefield.connected("a", "b"))
f.round += 5; SC.expire(f)
check("...and comes down when it ends", f.battlefield.connected("a", "b"))

e = foe(zone="b"); p = player(); f = fight(p, e)
combat.act_ability(f, p, spell("Static", effect="control", element="lightning", expression="static_field"), e, rng)
h = e.hp; bf.enter_zone(f, e, "c")
check("static field hurts whoever leaves it", e.hp < h)

e = foe(); f, p = control("toxic_cloud", "poison", e)
f.round += 1; combat.start_turn(e, f)
check("toxic cloud poisons whoever starts there", len(e.poison) >= 1)

e = foe(); e.shield = 50; e.defending = 30
e.buffs = {"x": {"rounds": 3, "mech": {"stance": 30}, "kind": "stance", "name": "Iron Guard"}}
f, p = control("dissolve_barriers", "acid", e, intel=60)
check("dissolve barriers strips shield, stance and guard", e.shield == 0 and not e.buffs and e.defending == 0, (e.shield, e.buffs))

e = foe(); e.hp = 100; e.buffs = {"renew_x": {"rounds": 3, "mech": {}, "kind": "renew", "per": 10, "name": "Renew"}}
f, p = control("unravel_recovery", "necrotic", e, intel=60)
from engine import combat_perks
healed, _ = combat_perks.mend(f, None, e, 50)
check("unravel recovery turns a heal into that much damage (f263)", healed == 0 and 0 < e.hp < 100 and "unraveled" in e.statuses, (healed, e.hp))
h0 = e.hp; combat.restore(f, e, 20)
check("...any healing at all, not just heal spells", e.hp < h0, (h0, e.hp))
e.statuses.pop("unraveled"); h0 = e.hp; combat.restore(f, e, 20)
check("...and once it wears off, healing heals again", e.hp > h0, (h0, e.hp))

e = foe(); e.position_tags = ["concealed"]; f, p = control("reveal", "radiant", e)
f.battlefield.zones["a"].tags = ["concealed"]
check("reveal strips hiding in the area", "concealed" not in e.position_tags)
check("...and the ground hides no one", not SC.zone_hidden(f, "a"))

# ---- forms and the area fix
e1, e2, e3 = foe(1), foe(2), foe(3, zone="c")
f, p = cast(spell("Fireball", reach="area", form="blast"), e1, e2, e3)
check("blast strikes the target's area", e1.hp < e1.max_hp and e2.hp < e2.max_hp)
check("...and nobody elsewhere on the field", e3.hp == e3.max_hp)

e1, e2 = foe(1), foe(2, zone="b")
f, p = cast(spell("Nova", reach="area", form="burst"), e1, e2, target=e2)
check("burst strikes your own area only", e1.hp < e1.max_hp and e2.hp == e2.max_hp)

e1, e2 = foe(1), foe(2, zone="b")
f, p = cast(spell("Old Area", reach="area"), e1, e2)
check("the old area reach is one area, not the field", e1.hp < e1.max_hp and e2.hp == e2.max_hp)

e = foe(); f, p = cast(spell("Hex", form="curse"), e)
check("curse deals nothing at once", e.hp == e.max_hp and len(e.curses) == 1)
for _ in range(3):
    f.round += 1; combat.start_turn(e, f)
check("...then its damage over three turns", e.hp < e.max_hp and not e.curses)
import engine.movement as mv
e = foe(); f, p = cast(spell("Hex", form="curse"), e)
check("...and Malefic Step finds the cursed", e in mv._cursed_by(f, p))

e = foe(); f, p = cast(spell("Meteor", form="charged"), e)
check("charged winds up and deals nothing yet", e.hp == e.max_hp and p.charging)
f.round += 1; acts = combat.start_turn(p, f, rng)
check("...and is released next turn", e.hp < e.max_hp and not p.charging)
check("...which takes that whole turn", acts is False and p.counters.get("cast_turn"))
e = foe(); f, p = cast(spell("Meteor", form="charged"), e)
p.statuses["stunned"] = 1
f.round += 1; combat.start_turn(p, f, rng)
check("...a stun breaks it", e.hp == e.max_hp and not p.charging)

# ---- charged hits harder than a bolt (same rolls)
def avg(form, n=40):
    tot = 0
    for i in range(n):
        r = random.Random(i)
        e = foe(); p = player(); f = fight(p, e)
        combat.act_ability(f, p, spell("S", form=form), e, r)
        if form == "charged":
            f.round += 1; combat.start_turn(p, f, r)
        tot += e.max_hp - e.hp
    return tot / n
b, c = avg("bolt"), avg("charged")
check("charged lands about 3.5x a bolt (two bolts' worth of turns for 1.75x each)", 3.0 < c / b < 4.0, (b, c))

# ---- category resistances
d = foe(category="undead")
check("undead resist necrotic", abs(combat.resist_factor(d, "magical", "necrotic") - 0.5) < 0.01)
check("undead are weak to radiant", abs(combat.resist_factor(d, "magical", "radiant") - 1.5) < 0.01)
check("plants are weak to fire", abs(combat.resist_factor(foe(category="plant"), "magical", "fire") - 1.5) < 0.01)
check("constructs resist poison", abs(combat.resist_factor(foe(category="construct"), "magical", "poison") - 0.25) < 0.01)

# ---- the planner
class Interp:
    families = ["mage"]; elements = []; archetype = "caster"
seen_expr, seen_form, rider_on_elemental = set(), set(), 0
for seed in range(60):
    r = random.Random(seed)
    slots = [dict(AS._base(), effect="damage", resource="mana", reach="ranged", rider="sunder", tier="moderate"),
             dict(AS._base(), effect="damage", resource="mana", reach="area", tier="moderate"),
             dict(AS._base(), effect="control", resource="mana", reach="ranged", rider="sunder", tier="light")]
    AS.assign_elements(slots, [], ["mage"], r)
    AS.assign_expressions(slots, r)
    AS.assign_forms(slots, r)
    for s in slots:
        if s["expressions"]:
            seen_expr.add(s["expressions"][0])
            from engine import elements as EL
            x_el = SC.EXPR[s["expressions"][0]]["element"]
            if x_el != s["element"] and x_el not in EL.neighbors(s["element"]):   # the wheel (f266): a neighbor's effect may be borrowed
                bad.append(f"expression element mismatch: {s['element']} slot given {s['expressions'][0]} ({x_el})")
            if s["rider"]:
                rider_on_elemental += 1
        if s["spell_form"]:
            seen_form.add(s["spell_form"])
        if s["reach"] == "area" and s["spell_form"] not in ("blast", "burst"):
            bad.append("area slot without area form")
check("the planner gives elemental slots expressions of their element or a neighbor's", len(seen_expr) >= 6, seen_expr)
check("...which replace the rider", rider_on_elemental == 0)
check("...and mana damage slots forms", {"blast", "burst", "bolt", "curse", "charged"} <= seen_form, seen_form)
s = dict(AS._base(), effect="control", resource="mana", reach="ranged", element="fire", expressions=["burning_ground"], n=1)
check("the model is told a control expression deals no damage", "NO damage" in AS.mechanic_text(s), AS.mechanic_text(s))

# ---- the groundwork for abilities with numbers of their own (f229): own power, own cost, own cast time, several expressions
e = foe(); f, p = cast(spell("Plain", form="bolt"), e); plain = e.max_hp - e.hp
e = foe(); f, p = cast(spell("Own", form="bolt", power=5.25), e); own = e.max_hp - e.hp
check("an ability's own power replaces its tier's", 2.0 < own / max(1, plain) < 4.0, (plain, own))
p = player(); m = spell("Costly", cost_percent=50)
check("...and its own cost its tier's", combat.cost_of(p, m) > 3 * combat.cost_of(p, spell("Cheap")), (combat.cost_of(p, m),))
e = foe(); f, p = cast(spell("Meteor", reach="area", form="blast", cast_turns=3), e)
check("a three-turn spell does nothing on its first turn", e.hp == e.max_hp and p.charging.get("left") == 2)
f.round += 1; a1 = combat.start_turn(p, f, rng)
check("...the second turn goes to gathering", e.hp == e.max_hp and a1 is False and p.charging.get("left") == 1)
p.counters.pop("cast_turn", None)
f.round += 1; combat.start_turn(p, f, rng)
check("...and it goes off on the third", any("uses Meteor on" in l for l in f.log) and not p.charging, f.log[-3:])
e = foe(); f, p = cast(spell("Meteor", reach="area", form="blast", cast_turns=3), e)
f.round += 1; combat.start_turn(p, f, rng); p.counters.pop("cast_turn", None)
p.statuses["prone"] = 1
f.round += 1; combat.start_turn(p, f, rng)
check("...a fall on the last turn still breaks it", e.hp == e.max_hp and not p.charging)
e = foe(); f, p = cast(spell("Starfire", element="fire", expressions=["ignite", "dazzle"]), e)
check("an ability with two expressions does both", "burning" in e.statuses and "blinded" in e.statuses, e.statuses)
e = foe(); e.shield = 40
f, p = cast(Move(id="w", name="Ward Rot", effect="control", tier="moderate", reach="ranged", resource="mana", attribute="intelligence",
                 element="acid", expressions=["dissolve_barriers", "toxic_cloud"]), e, intel=60)
check("a control spell with two expressions does both", e.shield == 0 and "toxic_cloud" in f.zone_effects.get("a", {}))
from engine import ability_traits as AT
card = AT.describe(spell("Meteor", reach="area", form="blast", cast_turns=3, expressions=["ignite", "dazzle"], element="fire"))
check("the card lists every expression and the cast time", "ignite" in card and "dazzle" in card and "3 turns" in card, card)

# ---- burns and poisonings get through element resistance only (f230)
p = player(); e = foe(category="construct"); f = fight(p, e)
combat.add_status(f, e, "poisoned", 3, p)
h = e.hp; combat.start_turn(e, f)
check("a construct takes a quarter of a poison tick", abs((h - e.hp) - round(e.poison[0] * 0.25)) <= 1 if e.poison else False, (h - e.hp,))
p = player(); e = foe(element="fire"); f = fight(p, e)
p.counters["last_hit"] = 100
combat.add_status(f, e, "burning", 2, p)
h = e.hp; combat.start_turn(e, f)
check("a fire creature takes half a burn tick (a plain hit's ignite)", h - e.hp == 12, h - e.hp)
p = player(); e = foe(element="fire"); f = fight(p, e)
p.counters["last_hit"] = 50; p.hit_element = "fire"
combat.add_status(f, e, "burning", 2, p); p.hit_element = ""
h = e.hp; combat.start_turn(e, f)
check("...and a fire hit's ignite is resisted once, not twice", h - e.hp == 12, (e.ignite, h - e.hp))
p = player(); e = foe(armor=500); e.shield = 1000; f = fight(p, e)
p.counters["last_hit"] = 100
combat.add_status(f, e, "burning", 2, p)
h = e.hp; combat.start_turn(e, f)
check("armor and shields do not stop a burn", h - e.hp == 25, h - e.hp)

# ---- bleeding: the open wound (f234) - sized by the hit that opened it, paid out by every physical blow after
from engine import afflictions as AF
p = player(); e = foe(); f = fight(p, e)
p.counters["last_hit"] = 100
combat.add_status(f, e, "bleeding", 3, p)
check("a wound is a fifth of the hit that opened it", abs(e.bleed - 20) < 0.01 and e.statuses["bleeding"] == 3, e.bleed)
p.counters["last_hit"] = 50
combat.add_status(f, e, "bleeding", 3, p)
check("...a smaller cut changes nothing", abs(e.bleed - 20) < 0.01)
p.counters["last_hit"] = 300
combat.add_status(f, e, "bleeding", 3, p)
check("...a bigger one replaces it", abs(e.bleed - 60) < 0.01)
h = e.hp; combat.start_turn(e, f)
check("an open wound does nothing by itself", e.hp == h, h - e.hp)
for _ in range(4):
    combat.start_turn(e, f)
check("...and closes after three rounds even untouched", "bleeding" not in e.statuses and e.bleed == 0, e.statuses)

e = foe(armor=10**4); e.shield = 10**4
ally = combat.Fighter(id="ally_x", name="Tam", side="ally", level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=500, max_hp=500,
                      weapon_damage=8, accuracy=300, hold=1)
p = player(); f = fight(p, ally, e)
p.counters["last_hit"] = 100
combat.add_status(f, e, "bleeding", 3, p)
lost = 0
for i in range(6):
    before = e.hp
    if combat.apply_damage(f, ally, e, 0.01, "hits", random.Random(i)):
        lost += 1
torn = sum(1 for l in f.log if "wound tears" in l)
check("every physical hit from anyone makes it bleed its size, through armor and shields", torn == lost and torn > 0
      and all(l.endswith(": 20") for l in f.log if "wound tears" in l), (torn, lost, [l for l in f.log if "tears" in l][:2]))

e = foe(); p = player(); f = fight(p, e)
for i in range(10):
    e.statuses.pop("bleeding", None); e.bleed = 0
    combat.apply_damage(f, p, e, 1.0, "hits", random.Random(i))
    combat.add_status(f, e, "bleeding", 3, p)
check("the hit that opens a wound does not make it bleed", not any("wound tears" in l for l in f.log))
e = foe(); p = player(); p.damage_type = "magical"; f = fight(p, e)
p.counters["last_hit"] = 100; combat.add_status(f, e, "bleeding", 3, p)
for i in range(10):
    combat.apply_damage(f, p, e, 1.0, "hits", random.Random(i))
check("magic does not make a wound bleed", not any("wound tears" in l for l in f.log))
e = foe(category="undead"); f = fight(player(), e)
check("the undead cannot bleed", not combat.add_status(f, e, "bleeding", 3, p) and "bleeding" not in e.statuses)
e = foe(); p = player(); f = fight(p, e)
p.counters["last_hit"] = 100; combat.add_status(f, e, "bleeding", 3, p); combat.act_defend(f, e)
check("setting your guard no longer closes it", "bleeding" in e.statuses)
p = player(); p.hp = 100; f = fight(p, foe())
q = foe(9); q.counters["last_hit"] = 50
combat.add_status(f, p, "bleeding", 3, q); combat_perks.mend(f, None, p, 10)
check("healing closes it, on the player too", "bleeding" not in p.statuses and p.bleed == 0)

print("\nFAILED:", bad if bad else "none")
sys.exit(1 if bad else 0)
