"""The f268 batch: eighty more element effects, each run through the engine once."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import afflictions, battlefield as bf, combat, combat_perks, spellcraft as SC
from engine.battlefield import Battlefield, BattleZone, BattleEdge
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def player(hp=10**5, **kw):
    attrs = {a: 10 for a in combat.ATTRIBUTES}; attrs["intelligence"] = 16
    d = dict(id="player", name="you", side="player", level=5, attrs=attrs, hp=hp, max_hp=hp, stamina=10**4, max_stamina=10**4,
             mana=10**5, max_mana=10**5, weapon_damage=12, hold=3, accuracy=200)
    d.update(kw); return combat.Fighter(**d)

def foe(i=1, hp=10**6, zone="a", side="enemy", **kw):
    d = dict(id=f"e{i}", name=f"foe {i}", side=side, level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
             weapon_damage=8, behaviors={"fearless": 1}, zone_id=zone)
    d.update(kw); return combat.Fighter(**d)

def ally(i=1, **kw):
    return foe(i, side="ally", **kw)

def field():
    return Battlefield(zones={z: BattleZone(id=z, name=f"zone {z}") for z in ("a", "b", "c")},
                       edges=[BattleEdge(a="a", b="b"), BattleEdge(a="b", b="c")], start="a")

def fight(*fs, conditions=None):
    f = combat.Combat(fighters=list(fs), record=False, conditions=conditions or [])
    f.battlefield = field()
    for x in fs:
        x.zone_id = x.zone_id or "a"
    for x in fs:
        if x.side == "ally":
            x.id = x.id if x.id.startswith("ally") else "ally_" + x.id
    return f

def spell(name, element, expression, tier="moderate", reach="ranged", **kw):
    return Move(id=name.lower().replace(" ", "_"), name=name, effect="damage", tier=tier, reach=reach, resource="mana",
                attribute="intelligence", element=element, expressions=[expression], **kw)

rng = random.Random(7)

def land(eid, element, *foes_, taken=100, crit=False, p=None, tier="moderate", f=None):
    """A hit with this expression has just landed for `taken`: run what it does."""
    p = p or player()
    f = f or fight(p, *foes_)
    p.hit_element, p.element = element, element
    p.counters["last_outcome"] = "crit" if crit else "hit"
    p.counters["last_hit"] = taken
    SC._CAST[id(p)] = {"exprs": [eid], "tier": tier, "name": eid, "once": set()}
    try:
        SC.on_hit(f, p, foes_[0], taken, rng)
    finally:
        SC.end(p)
    return f, p

def mult_for(eid, p, e, f, tier="moderate"):
    SC._CAST[id(p)] = {"exprs": [eid], "tier": tier, "name": eid, "once": set()}
    try:
        return SC.hit_mult(f, p, e, 1.0, {"steps": []})
    finally:
        SC.end(p)

# =============================================================== fire
e = foe(); e.statuses["burning"] = 2; e.ignite = 50
f, p = land("flashfire", "fire", e)
check("flashfire: the burn goes off at once and ends", "burning" not in e.statuses and e.hp == e.max_hp - 100, (e.statuses, e.max_hp - e.hp))

e = foe(hp=50); f, p = land("pyre", "fire", e, taken=100)
e.hp = 0; SC.on_death(f, e, p)
check("pyre: the body burns where it fell", "burning_ground" in f.zone_effects.get("a", {}), f.zone_effects)
e = foe(); f, p = land("pyre", "fire", e)
check("...a living target is marked for it", e.counters.get("pyre_by") == "player")

p = player(); e = foe(); f = fight(p, e); bf.engage(f, p, e)
land("blowback", "fire", e, p=p, f=f)
check("blowback: knocked out of melee", not bf.engaged_pair(p, e))

e = foe(); f, p = land("smolder", "fire", e)
check("smolder: a long, low burn", e.statuses.get("burning") == 4 and 0 < e.ignite < 100 * 0.5 / 2 + 1, (e.statuses, e.ignite))

e = foe(); f, p = land("flare_up", "fire", e, crit=True)
e2 = foe(2); land("flare_up", "fire", e2, crit=False)
check("flare-up: a critical hit doubles the burn", abs(e.ignite - 2 * e2.ignite) < 0.01, (e.ignite, e2.ignite))

p = player(); e = foe(); f = fight(p, e)
for _ in range(3):
    land("stoke", "fire", e, p=p, f=f)
combat.add_status(f, e, "burning", 2, p)
plain = foe(2); q = player(); fq = fight(q, plain); q.counters["last_hit"] = 100; combat.add_status(fq, plain, "burning", 2, q)
check("stoke: three hits in a row make the next burn 75% bigger", abs(e.ignite / plain.ignite - 1.75) < 0.01, (e.ignite, plain.ignite))
combat.apply_damage(f, p, e, 1.0, "hits", random.Random(1))
p.counters["stoke"] = 3; p.always_miss = True; combat.apply_damage(f, p, e, 1.0, "hits", random.Random(1)); p.always_miss = False
check("...and a miss resets it", "stoke" not in p.counters, p.counters.get("stoke"))

b = foe(); b.statuses["burning"] = 2; c = foe(2); f = fight(player(), b, c)
check("fan the flames: more against a burning target", mult_for("fan_the_flames", f.player, b, f) == 1.3 and mult_for("fan_the_flames", f.player, c, f) == 1.0)

e = foe(); e.statuses["burning"] = 1; e.ignite = 10; land("last_ember", "fire", e)
check("last ember: the burn lasts a round longer", e.statuses["burning"] == 2)

e = foe(hp=10); p = player(); f = fight(p, e); e.hp = 0
land("phoenix_spark", "fire", e, p=p, f=f)
fire = spell("Blaze", "fire", "ignite")
check("phoenix spark: a kill makes the next fire ability free", p.counters.get("free_fire") == 1 and combat.cost_of(p, fire, f) == 0)
combat.act_ability(f, p, fire, foe(2), random.Random(1))
check("...and it is spent on the cast", not p.counters.get("free_fire") and combat.cost_of(p, fire, f) > 0)

e = foe(); e.statuses["burning"] = 2; e.ignite = 5; e.position_tags = ["concealed"]
land("afterglow", "fire", e)
check("afterglow: a burning target cannot hide", "illuminated" in e.statuses and "concealed" not in e.position_tags)

# =============================================================== cold
e1, e2, e3 = foe(1), foe(2), foe(3, zone="b"); land("cold_snap", "cold", e1, e2, e3)
check("cold snap: everyone in the area is slowed, no one beyond it", "slowed" in e1.statuses and "slowed" in e2.statuses and "slowed" not in e3.statuses)

e = foe(); e.shield = 500; p = player(); f = fight(p, e)
mult_for("shatter_ward", p, e, f)
check("shatter ward: the barrier is cracked before the blow", e.shield == 0)

e = foe(); p = player(); f = fight(p, e)
land("brittle", "cold", e, p=p, f=f)
t = {}; combat.roll_attack(p, e, f, random.Random(1), trace=t); plain = {}; combat.roll_attack(p, foe(2), f, random.Random(1), trace=plain)
check("brittle: crits twice as likely", "brittle" in e.statuses and abs(t["crit"] - 2 * plain["crit"]) < 0.01, (t["crit"], plain["crit"]))

e = foe(); e.statuses["slowed"] = 3; f, p = land("frostbite", "cold", e, taken=100)
h = e.hp; combat.start_turn(e, f)
check("frostbite: 10% of the hit again each turn while slowed", h - e.hp == 10, h - e.hp)
e.statuses.pop("slowed"); h = e.hp; combat.start_turn(e, f)
check("...and stops once the slow is gone", h == e.hp and "frostbite" not in e.counters)

e = foe(); p = player(); f = fight(p, e); land("frostweld", "cold", e, p=p, f=f)
bf.enter_zone(f, e, "b")
check("frostweld: it cannot leave its area", e.zone_id == "a" and "frostwelded" in e.statuses)
check("...or step away from melee", combat_perks.held_fast(f, e))

e = foe(zone="b"); p = player(); f = fight(p, e); land("avalanche", "cold", e, p=p, f=f)
check("avalanche: driven into the next area over", e.zone_id == "c", e.zone_id)

e = foe(); e.statuses["slowed"] = 2; land("hypothermia", "cold", e)
check("hypothermia: a slowed target stays slowed a round longer", e.statuses["slowed"] == 3)

e1, e2 = foe(1), foe(2); f, p = land("superconductor", "cold", e1, e2)
p.hit_element = "lightning"; h = e2.hp
SC.on_any_hit(f, p, e1, 100, rng)
check("superconductor: lightning on it arcs to the others for 30%", "superconductive" in e1.statuses and e2.max_hp - e2.hp == 30, e2.max_hp - e2.hp)

e = foe(reach="ranged"); p = player(); f = fight(p, e); land("numb_hands", "cold", e, p=p, f=f)
check("numb hands: no ranged attacks", "numb_hands" in e.statuses and bool(SC.blocked_attack(e, "ranged")) and not SC.blocked_attack(e, "melee"))
h = p.hp; combat.enemy_turn(f, e, random.Random(1))
check("...a ranged enemy comes in swinging instead", e.reach == "ranged" and (p.hp < h or bf.engaged_pair(e, p)), (p.hp, h, e.engaged_with))

e = foe(zone="b"); f, p = land("snowdrift", "cold", e)
check("snowdrift: moving into or out of the area is hard going", f.battlefield.hard("a", "b") and f.battlefield.hard("b", "c"))

# =============================================================== lightning
m = foe(wears_metal=True); s = foe(2); land("galvanize", "lightning", m); land("galvanize", "lightning", s)
check("galvanize: a target in metal is stunned", "stunned" in m.statuses and "stunned" not in s.statuses)

e = foe(); e.winding = {"target": "player", "round": 1}; f, p = land("spasm", "lightning", e)
check("spasm: the wind-up is broken and it is left open", not e.winding and combat.is_open(e, f.round))

p = player(pace="normal"); e = foe(); f = fight(p, e); land("charged_step", "lightning", e, p=p, f=f)
check("charged step: fast until your next turn", p.pace == "fast" and p.counters.get("quick_until") == f.round + 1)

e1, e2 = foe(1, hp=10), foe(2); p = player(); f = fight(p, e1, e2); e1.hp = 0
land("jumping_spark", "lightning", e1, e2, p=p, f=f, taken=100)
check("jumping spark: a kill jumps on for the full damage", e2.max_hp - e2.hp == 100, e2.max_hp - e2.hp)

p = player(); p.cooldowns = {"x": 3, "y": 1}; e = foe(); f = fight(p, e); land("recharge", "lightning", e, p=p, f=f)
check("recharge: every cooldown a round sooner", p.cooldowns == {"x": 2})

p = player(); e = foe(zone="c"); f = fight(p, e)
combat.act_ability(f, p, spell("Flash Step", "lightning", "lightning_step", reach="melee"), e, random.Random(1))
check("lightning step: across the field and the blow is thrown", p.zone_id == "c" and bf.engaged_pair(p, e) and any("uses Flash Step" in l for l in f.log), (p.zone_id, f.log))

e = foe(); f, p = land("conductor", "lightning", e)
check("conductor: 25% more lightning gets through", "conductive" in e.statuses and abs(combat.element_factor(e, "lightning") - 1.25) < 0.01 and combat.element_factor(e, "fire") == 1.0)

p = player(); e = foe(); f = fight(p, e); p.move_round = f.round
check("storm charge: more damage after moving", mult_for("storm_charge", p, e, f) == 1.4)
p.move_round = -1
check("...and not when standing still", mult_for("storm_charge", p, e, f) == 1.0)

e = foe(); land("jittered", "lightning", e)
check("jittered: it dodges less", "jittered" in e.statuses and combat.status_mod(e, "evasion") == -20)

e1, e2 = foe(1), foe(2); f, p = land("ball_lightning", "lightning", e1, e2, taken=100)
f.round += 1; combat.start_turn(e2, f)
check("ball lightning: next round, it bursts on whoever starts their turn there", e2.max_hp - e2.hp == 30, e2.max_hp - e2.hp)

# =============================================================== poison
e = foe(); land("virulent", "poison", e)
check("virulent: two stacks at once", len(e.poison) == 2)
e = foe(); e.statuses["poisoned"] = 3; e.poison = [1]; land("festering", "poison", e)
check("festering: the poison lasts 2 rounds longer", e.statuses["poisoned"] == 5)
e = foe(); land("nerve_toxin", "poison", e)
check("nerve toxin: shaky aim", "shaky" in e.statuses and combat.status_mod(e, "accuracy") == -20)
e1, e2 = foe(1), foe(2); f, p = land("contagion", "poison", e1, e2)
combat.add_status(f, e1, "poisoned", 3, p); e1.hp = 0; SC.on_death(f, e1, p)
check("contagion: the poison passes on when it dies", "poisoned" in e2.statuses and len(e2.poison) == 1)
e1, e2, e3 = foe(1), foe(2), foe(3, zone="b"); land("venom_spray", "poison", e1, e2, e3)
check("venom spray: a stack for everyone in the area", len(e1.poison) == 1 and len(e2.poison) == 1 and not e3.poison)
e = foe(); f, p = land("wasting", "poison", e, p=player(weapon_damage=1000)); combat.add_status(f, e, "poisoned", 3, p)
w = foe(2); fw = fight(player(weapon_damage=1000), w); combat.add_status(fw, w, "poisoned", 3, fw.player)
h1, h2 = e.hp, w.hp; combat.start_turn(e, f); combat.start_turn(w, fw)
check("wasting: poison hurts half again as much", abs((h1 - e.hp) / max(1, h2 - w.hp) - 1.5) < 0.1, (h1 - e.hp, h2 - w.hp))
e = foe(); e.poison = [1, 1, 1]; e.statuses["poisoned"] = 3; f = fight(player(), e)
check("lethal dose: more against a well-poisoned target", mult_for("lethal_dose", f.player, e, f) == 1.4 and mult_for("lethal_dose", f.player, foe(2), f) == 1.0)
e = foe(); f, p = land("persistent_toxin", "poison", e)
check("persistent toxin: the stack is set aside as one that will not fade", len(e.poison_fixed) == 1 and not e.poison)
e.statuses["poisoned"] = 1; combat.start_turn(e, f)
check("...and the poison never wears off", "poisoned" in e.statuses and e.poison_fixed, e.statuses)
e = foe(); e.statuses["bleeding"] = 3; e.bleed = 20; land("anticoagulant", "poison", e)
check("anticoagulant: the wound doubles", e.bleed == 40)
u = foe(category="undead"); f, p = land("refined_venom", "poison", u, p=player(weapon_damage=1000))
plain = foe(2, category="undead"); fp = fight(player(weapon_damage=1000), plain); combat.add_status(fp, plain, "poisoned", 3, fp.player)
check("refined venom: the undead's resistance to poison does not count", afflictions.tick(u, "poisoned") > afflictions.tick(plain, "poisoned") * 1.5, (afflictions.tick(u, "poisoned"), afflictions.tick(plain, "poisoned")))

# =============================================================== acid
p = player(); e = foe(ward=30); f = fight(p, e)
SC._CAST[id(p)] = {"exprs": ["etch"], "tier": "moderate", "name": "Etch", "once": set()}
etched, _ = combat.mitigate(e, 100, "magical", 5, f, p); SC.end(p)
plain, _ = combat.mitigate(e, 100, "magical", 5, f, p)
check("etch: half the ward eaten through", etched > plain, (etched, plain))
e = foe(); f, p = land("lingering_acid", "acid", e, taken=100)
h = e.hp; combat.start_turn(e, f); combat.start_turn(e, f)
check("lingering acid: 30% more over two turns", h - e.hp == 30 and not e.curses, (h - e.hp, e.curses))
p = player(); e = foe(); e.shield = 500; f = fight(p, e)
SC._CAST[id(p)] = {"exprs": ["seep"], "tier": "moderate", "name": "Seep", "once": set()}
dealt = combat.take_damage(f, e, 100, p, rng, "magical"); SC.end(p)
check("seep: under the barrier to the health", dealt == 100 and e.shield == 500 and e.hp == e.max_hp - 100)
e = foe(); land("strip", "acid", e)
check("strip: exposed", e.statuses.get("exposed") == 2)
p = player(); e = foe(); e.defending = 50; f = fight(p, e)
SC._CAST[id(p)] = {"exprs": ["burn_through"], "tier": "moderate", "name": "Burn Through", "once": set()}
through, _ = combat.mitigate(e, 100, "magical", 5, f, p); SC.end(p)
guarded, _ = combat.mitigate(e, 100, "magical", 5, f, p)
check("burn through: a defending target still takes full damage", abs(through - 2 * guarded) < 0.5, (through, guarded))
p = player(); p.statuses["grappled"] = 2; e = foe(); f = fight(p, e); land("corrode_the_hold", "acid", e, p=p, f=f)
check("corrode the hold: you break free", "grappled" not in p.statuses)
e = foe(); p = player(); f = fight(p, e); land("caustic_drip", "acid", e, p=p, f=f, taken=100)
h = e.hp; combat.apply_damage(f, e, p, 1.0, "hits", random.Random(1))
check("caustic drip: it is hurt whenever it attacks", h - e.hp == 10, h - e.hp)
e = foe(); f, p = land("creeping_corrosion", "acid", e)
for _ in range(3): combat.start_turn(e, f)
combat.start_turn(e, f)
check("creeping corrosion: 5% a round for three rounds", e.corroded == 15, e.corroded)
e = foe(); p = player(); f = fight(p, e); land("tarnish", "acid", e, p=p, f=f)
t = {}; combat.roll_attack(e, p, f, random.Random(1), trace=t)
check("tarnish: its next hits cannot crit", e.counters.get("tarnished") == 2 and t["crit"] == 0)
e = foe(); f, p = land("caustic_venom", "acid", e); combat.add_status(f, e, "poisoned", 3, p); combat.start_turn(e, f)
check("caustic venom: each poison tick eats armor", e.corroded == 2, e.corroded)

# =============================================================== necrotic
e = foe(); land("dread", "necrotic", e); check("dread: frightened", e.statuses.get("frightened") == 2)
e = foe(); land("marked_for_death", "necrotic", e); check("marked for death", e.statuses.get("marked") == 3)
p = player(); pet = ally(1, hp=1000, summon_form="striker"); pet.hp = 100; e = foe(); f = fight(p, pet, e)
land("soul_leech", "necrotic", e, p=p, f=f, taken=100)
check("soul leech: the summon heals for 30%", pet.hp == 130, pet.hp)
p = player(hp=1000); p.hp = 500; e = foe(hp=10); f = fight(p, e); e.hp = 0; land("death_feeds", "necrotic", e, p=p, f=f)
check("death feeds: a kill heals you 15%", p.hp == 650, p.hp)
e = foe(); e.buffs = {"b": {"rounds": 1, "mech": {}, "name": "Ward", "kind": "arcaneward"}, "c": {"rounds": 3, "mech": {}, "name": "Haste", "kind": "x"}}
land("entropy", "necrotic", e)
check("entropy: every buff loses a round, and the last one goes", "b" not in e.buffs and e.buffs["c"]["rounds"] == 2)
p = player(hp=1000); e = foe(); f = fight(p, e)
check("blood price: 40% more", mult_for("blood_price", p, e, f) == 1.4)
land("blood_price", "necrotic", e, p=p, f=f, taken=100)
check("...for 10% of the damage in your own blood", p.hp == 990, p.hp)
u = foe(category="undead"); f, p = land("dominate", "necrotic", u)
check("dominate: an undead target turns for 2 rounds", u.counters.get("turned") == 1 and u.counters.get("turned_until") == f.round + 2)
f.round += 3; combat.enemy_turn(f, u, random.Random(1))
check("...and comes back to its side after", not u.counters.get("turned"))
p = player(); e = foe(); f = fight(p, e); f.battlefield.zones["a"].tags = ["concealed"]
land("shadowcloak", "necrotic", e, p=p, f=f)
check("shadowcloak: hidden again after the blow", "concealed" in p.position_tags)
e = foe(hp=1000); e.hp = 100; f, p = land("deaths_door", "necrotic", e)
b = foe(2, hp=1000, rank="boss"); b.hp = 100; land("deaths_door", "necrotic", b)
check("death's door: below 15% it dies; a boss does not", not e.alive and b.alive)
e = foe(hp=1000); e.hp = 500; p = player(hp=1000); p.hp = 500; f = fight(p, e); land("life_theft", "necrotic", e, p=p, f=f)
combat.restore(f, e, 100)
check("life theft: its next healing comes to you", e.hp == 500 and p.hp == 600, (e.hp, p.hp))

# =============================================================== radiant
e = foe(); e.buffs = {"b": {"rounds": 3, "mech": {}, "name": "Ward", "kind": "arcaneward"}}; land("purge", "radiant", e)
check("purge: a buff stripped", not e.buffs)
p = player(); p.statuses["slowed"] = 2; e = foe(); f = fight(p, e); land("cleanse", "radiant", e, p=p, f=f)
check("cleanse: an affliction lifted from you", "slowed" not in p.statuses)
p = player(); a = ally(1, hp=1000); e = foe(); f = fight(p, a, e); land("shield_of_faith", "radiant", e, p=p, f=f, taken=100)
check("shield of faith: allies in your area gain a barrier", a.shield == 10, a.shield)
p = player(); a = ally(1); e = foe(); f = fight(p, a, e); land("censure", "radiant", e, p=p, f=f)
check("censure: its next action is aimed at you", combat_perks.pick_target(f, e, [p, a], random.Random(1)) is p)
p = player(); e = foe(); f = fight(p, e); e.counters["hurt_ally"] = f.round
check("judgement: more against one that hurt an ally", mult_for("judgement", p, e, f) == 1.3)
p = player(); a = ally(1); e = foe(); f = fight(p, a, e); land("guiding_light", "radiant", e, p=p, f=f)
_roll = combat.roll_attack
combat.roll_attack = lambda *a, **k: ("miss", 0.0)
try:
    landed = combat.apply_damage(f, a, e, 1.0, "hits", random.Random(1))
finally:
    combat.roll_attack = _roll
check("guiding light: an ally's next hit cannot miss", landed and "guided" not in e.counters)
e = foe(zone="b"); f, p = land("daybreak", "radiant", e)
f.zone_effects["b"] = {"smoke": {"until": 9}, "overgrowth": {"until": 9}}
land("daybreak", "radiant", e, p=p, f=f)
check("daybreak: smoke and undergrowth cleared", not f.zone_effects.get("b"))
p = player(); a = ally(1); e = foe(); f = fight(p, a, e); land("rallying_light", "radiant", e, p=p, f=f, crit=True)
check("rallying light: a crit rallies the allies", a.counters.get("rallied") == 30)
e = foe(); p = player(); f = fight(p, e); land("humbled", "radiant", e, p=p, f=f)
t = {}; combat.roll_attack(e, p, f, random.Random(1), trace=t)
check("humbled: no critical hits", t["crit"] == 0)
u = foe(category="undead"); p = player(); f = fight(p, u); land("sunfire", "radiant", u, p=p, f=f)
plain = foe(2); fp = fight(player(), plain); fp.player.counters["last_hit"] = 100; combat.add_status(fp, plain, "burning", 2, fp.player)
check("sunfire: holy fire burns the undead half again as hot, and cannot be cleansed", abs(u.ignite / plain.ignite - 1.5) < 0.01 and u.counters.get("holy_burn"))
u.statuses["slowed"] = 1
land("cleanse", "radiant", foe(3), p=u, f=f)
check("...cleanse lifts something else instead", "burning" in u.statuses and "slowed" not in u.statuses)

# =============================================================== nature
e = foe(); land("entangle", "nature", e); check("entangle: held through its next turn", e.statuses.get("grappled", 0) >= 2, e.statuses)
e = foe(); land("spore_burst", "nature", e); check("spore burst: befuddled", "befuddled" in e.statuses)
p = player(); a = ally(1, hp=1000); a.hp = 500; e = foe(); f = fight(p, a, e); land("lifebloom", "nature", e, p=p, f=f, taken=100)
check("lifebloom: allies in your area heal 15%", a.hp == 515, a.hp)
e = foe(); land("quake_strike", "nature", e); big = foe(2, size="Gargantuan"); land("quake_strike", "nature", big)
check("quake strike: knocked down, unless far bigger", "prone" in e.statuses and "prone" not in big.statuses)
e = foe(); e.statuses["prone"] = 1; f = fight(player(), e)
check("crushing roots: more against the held or downed", mult_for("crushing_roots", f.player, e, f) == 1.5)
e = foe(); f, p = land("seedburst", "nature", e, taken=100)
combat.start_turn(e, f); h = e.hp; f.round += 2; combat.start_turn(e, f)
check("seedburst: bursts two rounds later for 60%", h - e.hp == 60, h - e.hp)
p = player(); pet = ally(1, summon_form="striker"); e = foe(); f = fight(p, pet, e); land("pack_scent", "nature", e, p=p, f=f)
check("pack scent: companions and summons hit it harder", "scented" in e.statuses)
p = player(); e = foe(); f = fight(p, e, conditions=["in_daylight", "in_wilderness"])
check("sunlit growth: more in daylight under open sky", mult_for("sunlit_growth", p, e, f) == 1.3)
f2 = fight(player(), foe(), conditions=["in_daylight", "underground"])
check("...not underground", mult_for("sunlit_growth", f2.player, f2.fighters[1], f2) == 1.0)
e = foe(); f, p = land("bramble_wrap", "nature", e, taken=100)
h = e.hp; bf.enter_zone(f, e, "b")
check("bramble wrap: it is hurt when it moves", h - e.hp == 10, h - e.hp)
e = foe(); p = player(); f = fight(p, e); land("tangled_arms", "nature", e, p=p, f=f)
h = p.hp; combat.enemy_turn(f, e, random.Random(1))
check("tangled arms: no melee attacks, it guards instead", p.hp == h and e.defending > 0, (p.hp, h, e.defending))

# =============================================================== the cards
from engine import ability_traits as AT
from core.models import Ability
for eid in SC.EXPR:
    a = Ability(id="x", name="X", description="d", effect="damage", tier="moderate", reach="ranged", resource="mana", context="combat",
                cost=0, cooldown=0, element=SC.EXPR[eid]["element"], expressions=[eid])
    line = dict(AT.parts(a)).get(SC.EXPR[eid]["label"], "")
    if SC.EXPR[eid]["kind"] == "damage" and ("{" in line or not line or "}" in line):
        check(f"card text for {eid}", False, line)
check("every effect has a readable card line", True)

print("\nFAILED:", bad if bad else "none")
sys.exit(1 if bad else 0)
