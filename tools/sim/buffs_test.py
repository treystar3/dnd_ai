"""Buffs, rebuilt (f235): Imbue, Precision, Blur and Mana Shield - one strength each, no tiers; Imbue, Precision and Blur can be
given to one ally, Mana Shield is your own; the planner gives buffs one strength and the right resource."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import ability_slots as AS, ability_traits as AT, combat
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def fighter(fid="player", side="player", **kw):
    return combat.Fighter(id=fid, name=fid, side=side, level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=10**6, max_hp=10**6,
                          stamina=10**4, max_stamina=10**4, mana=10**4, max_mana=10**4, weapon_damage=12, weapon_attrs=["strength"], hold=2, **kw)

def fight(*fs):
    return combat.Combat(fighters=list(fs), record=False)

def buff(kind, tier="light", **k):
    return Move(id="b_" + kind, name="Test " + kind, effect="buff", tier=tier, reach="self", resource="mana", buff=kind, **k)

check("thirteen buffs", sorted(AT.BUFFS) == ["acidcoat", "arcaneward", "attunement", "bladeward", "blur", "enlarge", "envenom", "frostarmor", "imbue", "manashield", "precision", "stoneform", "thorns"], sorted(AT.BUFFS))
p = fighter(); f = fight(p, fighter("e", "enemy"))
for tier in ("light", "heavy"):
    p.buffs.clear(); combat.act_ability(f, p, buff("precision", tier), None, random.Random(1))
check("a buff has one strength, whatever its tier", list(p.buffs.values())[0]["mech"] == {"precision": 15}, p.buffs)

# ---- Precision: no glancing blows, more crits
def outcomes(buffed, n=400):
    tally = {"graze": 0, "crit": 0}
    for i in range(n):
        a, d = fighter(), fighter("e", "enemy")
        f = fight(a, d)
        if buffed:
            combat.act_ability(f, a, buff("precision"), None, random.Random(1))
        combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i))
        last = f.log[-1]
        tally["graze"] += "(graze)" in last
        tally["crit"] += "(critical)" in last
    return tally
plain, sharp = outcomes(False), outcomes(True)
check("precision: no glancing blows", plain["graze"] > 0 and sharp["graze"] == 0, (plain, sharp))
check("...and more critical hits", sharp["crit"] > plain["crit"] * 1.3, (plain, sharp))

# ---- Blur: attacks miss more
def hits_taken(buffed, n=400):
    landed = 0
    for i in range(n):
        a, d = fighter("e", "enemy"), fighter()
        f = fight(d, a)
        if buffed:
            combat.act_ability(f, d, buff("blur"), None, random.Random(1))
        landed += combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i))
    return landed
check("blur: attacks against you land less often (rolled twice, the worse kept)", hits_taken(True) < hits_taken(False) * 0.85, (hits_taken(False), hits_taken(True)))

# ---- Mana Shield: point for point, breaks when the mana runs out
p, e = fighter(), fighter("e", "enemy"); f = fight(p, e)
combat.act_ability(f, p, buff("manashield"), None, random.Random(1))
p.mana = 10**4; h, m = p.hp, p.mana
dealt = combat.take_damage(f, p, 100, e, random.Random(1), "physical")
check("mana shield: 60% of the blow comes out of mana, point for point", dealt == 40 and m - p.mana == 60, (dealt, m - p.mana))
p.mana = 30
combat.take_damage(f, p, 100, e, random.Random(1), "physical")
check("...and breaks when the mana runs out", p.mana <= 0 and not any(b.get("kind") == "manashield" for b in p.buffs.values()))
p, t = fighter(), fighter("ally_t", "ally"); f = fight(p, t, fighter("e", "enemy"))
combat.act_ability(f, p, buff("manashield"), None, random.Random(1), give=[t])
check("...and stays on the caster", any(b.get("kind") == "manashield" for b in p.buffs.values()) and not t.buffs)

# ---- Imbue: the element and its effect on weapon hits
p, e = fighter(), fighter("e", "enemy"); f = fight(p, e)
m = buff("imbue", element="fire", expressions=["ignite"])
combat.act_ability(f, p, m, None, random.Random(1))
for i in range(20):
    if combat.apply_damage(f, p, e, 1.0, "hits", random.Random(i)):
        break
check("imbue: weapon hits carry the element", any("fire flares" in l.lower() for l in f.story), f.story[-3:])
check("...and the element does what it does", "burning" in e.statuses, e.statuses)
p, e = fighter(), fighter("e", "enemy"); f = fight(p, e)
combat.act_ability(f, p, buff("imbue", element="fire", expressions=["ignite"]), None, random.Random(1))
bolt = Move(id="bolt", name="Bolt", effect="damage", tier="light", reach="ranged", resource="mana", attribute="intelligence")
for i in range(10):
    combat.act_ability(f, p, bolt, e, random.Random(i))
check("...but never on spells", not any("flares" in l for l in f.story), [l for l in f.story if "flares" in l][:1])
p, t = fighter(), fighter("ally_t", "ally"); f = fight(p, t, fighter("e", "enemy"))
combat.act_ability(f, p, buff("imbue", element="cold"), None, random.Random(1), give=[t])
check("imbue, precision and blur can be given to an ally", t.buffs and not p.buffs)

# ---- Enlarge: a size larger, holds two more, harder melee blows - and nothing aimed at you misses
from engine import battlefield as bf, martial as MA
p, e = fighter(), fighter("e", "enemy", size="Large"); f = fight(p, e)
check("before Enlarge you cannot pin something larger", not MA.fits(p, e, "pin"))
combat.act_ability(f, p, buff("enlarge"), None, random.Random(1))
check("Enlarged you can", MA.fits(p, e, "pin"))
check("...and you hold two more at the line", bf.hold_of(p) == p.hold + 2, (bf.hold_of(p), p.hold))
def melee(buffed, n=200):
    t = 0
    for i in range(n):
        a, d = fighter(), fighter("e", "enemy")
        a.reach = "melee"; f = fight(a, d)
        if buffed:
            combat.act_ability(f, a, buff("enlarge"), None, random.Random(1))
        h = d.hp; combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i)); t += h - d.hp
    return t / n
r = melee(True) / melee(False)
check("...your melee blows hit 10% harder", 1.05 < r < 1.15, round(r, 2))
missed = 0
for i in range(200):
    d, a = fighter(), fighter("e", "enemy", accuracy=-500); f = fight(d, a)
    combat.act_ability(f, d, buff("enlarge"), None, random.Random(1))
    missed += not combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i))
check("...but nothing aimed at you can miss", missed == 0, missed)
n = 0
p = fighter(); f = fight(p, fighter("e", "enemy")); combat.act_ability(f, p, buff("enlarge"), None, random.Random(1))
while p.buffs and n < 10:
    combat.start_turn(p, f); n += 1
check("...for three rounds, then you shrink back", n == 3 and MA._size(p) == 2, (n, MA._size(p)))

# ---- Frost Armor: +20% armor, and melee attackers who strike you are slowed
def taken(buffed, n=200):
    t = 0
    for i in range(n):
        d, a = fighter(armor=40), fighter("e", "enemy"); f = fight(d, a)
        if buffed:
            combat.act_ability(f, d, buff("frostarmor"), None, random.Random(1))
        x, _ = combat.mitigate(d, 1000, "physical", 5, f, a); t += x
    return t / n
check("frost armor: physical blows land softer", taken(True) < taken(False) * 0.97, (taken(False), taken(True)))
d, a = fighter(), fighter("e", "enemy"); a.reach = "melee"; f = fight(d, a)
combat.act_ability(f, d, buff("frostarmor"), None, random.Random(1))
for i in range(30):
    if combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i)):
        break
check("...and a melee attacker who strikes you is slowed", "slowed" in a.statuses and a.statuses["slowed"] == 2, a.statuses)
combat.start_turn(a, f)
check("...through its next turn", "slowed" in a.statuses)
d, a = fighter(), fighter("e", "enemy"); a.reach = "ranged"; f = fight(d, a)
combat.act_ability(f, d, buff("frostarmor"), None, random.Random(1))
for i in range(30):
    combat.apply_damage(f, a, d, 1.0, "shoots", random.Random(i))
check("...but an archer is not", "slowed" not in a.statuses)

# ---- Stoneform: 25% less physical damage, unshakable - but slowed and no movement abilities
p, e = fighter(), fighter("e", "enemy"); f = fight(p, e)
combat.act_ability(f, p, buff("stoneform"), None, random.Random(1))
check("stoneform: physical blows lose a quarter", combat.take_damage(f, p, 100, e, random.Random(1), "physical") == 75)
check("...magic does not", combat.take_damage(f, p, 100, e, random.Random(1), "magical") == 100)
check("...nothing knocks you down, stuns you or pins you", not any(combat.add_status(f, p, s_, 2, e) for s_ in ("prone", "stunned", "grappled")))
check("...nor moves you", not MA.maneuver(f, e, p, Move(id="x", name="Shove", effect="damage", tier="light", reach="melee", resource="stamina", maneuver="shove"), random.Random(1)))
check("...but you are slowed", "slowed" in p.statuses)
mv = Move(id="m", name="Dash", effect="mobility", tier="light", reach="self", resource="stamina", movement="shift")
from engine import movement
check("...and cannot use a movement ability", "stone" in (movement.refuse(f, p, mv, e) or ""), movement.refuse(f, p, mv, e))

# ---- Thorns: melee attackers take a share of your armor
d, a = fighter(armor=100), fighter("e", "enemy"); a.reach = "melee"; f = fight(d, a)
combat.act_ability(f, d, buff("thorns"), None, random.Random(1))
h = a.hp
for i in range(30):
    if combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i)):
        break
check("thorns: a melee attacker that hits you is hurt", a.hp < h, h - a.hp)
d, a = fighter(armor=100), fighter("e", "enemy"); a.reach = "ranged"; f = fight(d, a)
combat.act_ability(f, d, buff("thorns"), None, random.Random(1))
h = a.hp
for i in range(30):
    combat.apply_damage(f, a, d, 1.0, "shoots", random.Random(i))
check("...an archer is not", a.hp == h)
from engine import relics
for arm, want in ((0, 5), (100, 55)):
    d = fighter(armor=arm); f = fight(d, fighter("e", "enemy"))
    combat.act_ability(f, d, buff("thorns"), None, random.Random(1))
    m = combat.mechanics(d, f)
    got = m.get("thorn_flat", 0) + d.armor * m.get("thorn_pct", 0) / 100
    check(f"thorns at {arm} armor: 5 + 50% of armor = {want}", got == want, got)

# ---- Envenom Weapon: every weapon hit adds a poison stack, and no extra damage
def plain_hit(buffed, n=150):
    t = 0
    for i in range(n):
        a, d = fighter(), fighter("e", "enemy"); f = fight(a, d)
        if buffed:
            combat.act_ability(f, a, buff("envenom"), None, random.Random(1))
        h = d.hp; combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i)); t += h - d.hp
    return t / n
check("envenom weapon: the hit itself is no stronger", abs(plain_hit(True) - plain_hit(False)) < 0.01)
a, d = fighter(), fighter("e", "enemy"); f = fight(a, d)
combat.act_ability(f, a, buff("envenom"), None, random.Random(1))
landed = sum(combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i)) for i in range(4))
check("...every hit adds a poison stack", len(d.poison) == landed and landed > 0, (len(d.poison), landed))
slots = [dict(AS._base(), effect="buff", buff="imbue", element="poison", resource="mana")]
AS.split_poison_imbue(slots)
check("an Imbue planned with poison becomes Envenom Weapon", slots[0]["buff"] == "envenom" and slots[0]["element"] == "")
slots = [dict(AS._base(), effect="buff", buff="envenom"), dict(AS._base(), effect="buff", buff="imbue", element="poison")]
AS.split_poison_imbue(slots)
check("...unless the class already has one, then it takes fire", slots[1]["buff"] == "imbue" and slots[1]["element"] == "fire")

# ---- Acid Coating: every weapon hit eats armor, and no extra damage
a, d = fighter(), fighter("e", "enemy", armor=100); f = fight(a, d)
combat.act_ability(f, a, buff("acidcoat"), None, random.Random(1))
landed = sum(combat.apply_damage(f, a, d, 0.01, "hits", random.Random(i)) for i in range(3))
check("acid coating: each weapon hit eats 10% of armor and ward", d.corroded == min(75, 10 * landed) and landed > 0, (d.corroded, landed))
slots = [dict(AS._base(), effect="buff", buff="imbue", element="acid", resource="mana")]
offers = {"buffs": ["imbue"]}
AS.split_poison_imbue(slots, offers)
check("an Imbue planned with acid becomes Acid Coating, and the offer says so", slots[0]["buff"] == "acidcoat" and "acidcoat" in offers["buffs"])

# ---- Arcane Ward, Wind Ward, Bladeward (f244)
def taken_m(buffed, n=100):
    t = 0
    for i in range(n):
        d, a = fighter(ward=40), fighter("e", "enemy"); f = fight(d, a)
        if buffed:
            combat.act_ability(f, d, buff("arcaneward"), None, random.Random(1))
        x, _ = combat.mitigate(d, 1000, "magical", 5, f, a); t += x
    return t / n
check("arcane ward: magic lands softer", taken_m(True) < taken_m(False) * 0.97, (taken_m(False), taken_m(True)))
def landed(kind, reach, n=400):
    got = 0
    for i in range(n):
        d, a = fighter(), fighter("e", "enemy"); a.reach = reach; f = fight(d, a)
        if kind:
            combat.act_ability(f, d, buff(kind), None, random.Random(1))
        got += combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i))
    return got
# Attunement: an archon of one element
d, src = fighter(), fighter("e", "enemy"); f = fight(d, src)
combat.act_ability(f, d, buff("attunement", element="fire"), None, random.Random(1))
check("attunement: its element is resisted by half", abs(combat.element_factor(d, "fire") - 0.5) < 0.01 and combat.element_factor(d, "cold") == 1.0)
src.counters["last_hit"] = 100
check("...its effects cannot take hold", not combat.add_status(f, d, "burning", 2, src) and "burning" not in d.statuses)
check("...but other elements' can", combat.add_status(f, d, "poisoned", 3, src))
d, src = fighter(), fighter("e", "enemy"); f = fight(d, src)
combat.act_ability(f, d, buff("attunement", element="cold"), None, random.Random(1))
src.hit_element = "cold"
check("a cold archon is not chilled by cold", not combat.add_status(f, d, "slowed", 2, src))
src.hit_element = ""
check("...but can still be hamstrung", combat.add_status(f, d, "slowed", 2, src))
# mastery
a, t = fighter(), fighter("e", "enemy"); f = fight(a, t)
a.counters["last_hit"] = 100; combat.add_status(f, t, "burning", 2, a); plain = t.ignite
a2, t2 = fighter(), fighter("e", "enemy"); f2 = fight(a2, t2)
combat.act_ability(f2, a2, buff("attunement", element="fire"), None, random.Random(1))
a2.counters["last_hit"] = 100; combat.add_status(f2, t2, "burning", 2, a2)
check("an archon of fire sets bigger burns", abs(t2.ignite - plain * 1.5) < 0.01, (plain, t2.ignite))
a, t = fighter(), fighter("e", "enemy"); f = fight(a, t)
combat.act_ability(f, a, buff("attunement", element="poison"), None, random.Random(1))
combat.add_status(f, t, "poisoned", 3, a)
check("an archon of poison adds two stacks a dose", len(t.poison) == 2, len(t.poison))
a, t = fighter(), fighter("e", "enemy"); f = fight(a, t)
combat.act_ability(f, a, buff("attunement", element="cold"), None, random.Random(1))
a.hit_element = "cold"; combat.add_status(f, t, "slowed", 2, a); a.hit_element = ""
check("an archon of cold chills a round longer", t.statuses.get("slowed") == 3, t.statuses)
slots = [dict(AS._base(), effect="buff", buff="attunement", resource="mana")]
AS.assign_elements(slots, [], ["paladin"], random.Random(1))
check("the planner gives an attunement its element", slots[0]["element"] != "", slots)

d, a = fighter(), fighter("e", "enemy"); a.reach = "melee"; f = fight(d, a)
combat.act_ability(f, d, buff("bladeward"), None, random.Random(1))
for i in range(30):
    if combat.apply_damage(f, a, d, 1.0, "hits", random.Random(i)):
        break
check("bladeward: the first melee blow each round is turned", any("Bladeward" in l for l in f.story))
n_turned = sum(1 for l in f.story if "Bladeward" in l)
for i in range(5):
    combat.apply_damage(f, a, d, 1.0, "hits", random.Random(100 + i))
check("...only the first each round", sum(1 for l in f.story if "Bladeward" in l) == n_turned)
cut = Move(id="cut", name="Cut", effect="damage", tier="light", reach="melee", resource="stamina")
check("...and you cannot strike in melee yourself", "Bladeward" in (combat.can_use(d, cut, f) or ""))
d2 = fighter(); f2 = fight(d2, fighter("e", "enemy")); combat.act_ability(f2, d2, buff("bladeward"), None, random.Random(1))
combat.act_attack(f2, d2, f2.fighters[1], random.Random(1))
check("...not even a plain blow", any("cannot strike in melee" in l for l in f2.log), f2.log[-1:])

# ---- f247: cooldown longer than the buff; buffs cast before a fight you start
from engine import abilities
from llm.contracts import ActiveProposal as AP
ab = abilities.materialize_active(AP(name="Hide of Stone", description="d", effect="buff", tier="light", reach="self", resource="mana", context="combat", buff="stoneform"))
check("a buff's cooldown is longer than it lasts", ab.cooldown == AT.buff_rounds("stoneform") + 3, ab.cooldown)
p, e = fighter(), fighter("e", "enemy")
m = buff("stoneform"); m.cooldown = 6; p.moves = [m]
f = fight(p, e)
notes = combat.prebuff(f, ["b_stoneform"], random.Random(1))
check("a pre-fight buff is up before the first blow, a round shorter", "b_stoneform" in p.buffs and p.buffs["b_stoneform"]["rounds"] == AT.buff_rounds("stoneform") - 1, (p.buffs, notes))
check("...and paid for, and on cooldown", p.mana < 10**4 and p.cooldowns.get("b_stoneform", 0) > 0)
p.mana = 0; p.buffs.clear(); p.cooldowns.clear()
notes = combat.prebuff(f, ["b_stoneform"], random.Random(1))
check("...but not without the mana", not p.buffs and notes and "No time" in notes[0], notes)
from engine import field
check("pass without trace is a taught exploration buff", "pass_without_trace" in field.FUNCTIONS and field.F["functions"]["pass_without_trace"].get("taught_only"))

# ---- the planner
class I:
    families = ["mage"]; elements = []; archetype = type("A", (), {"value": "mage"})()
for seed in range(30):
    r = random.Random(seed)
    slots = [dict(AS._base(), effect="buff", tier="light", buff=b, resource="stamina") for b in AT.BUFFS]
    AS.buff_resources(slots)
    if any(s["tier"] != "moderate" for s in slots) or any(s["resource"] != "mana" for s in slots):
        bad.append("planner buff resources/tier")
        break
check("the planner gives buffs one strength, and every buff costs mana", "planner buff resources/tier" not in bad)
check("cards describe the new buffs", "never graze" in AT.describe(buff("precision")) and "point for point" in AT.describe(buff("manashield")),
      AT.describe(buff("precision")))

from llm.contracts import ActiveProposal
pp = ActiveProposal(name="X", description="d", effect="buff", tier="light", reach="self", resource="stamina", context="combat", buff="blur")
check("a buff proposed with stamina costs mana anyway (every buff is magic, f238)", pp.resource == "mana")
from engine import loadout as LO
check("...so it sits among your spells", LO.pool_of(pp) == "spells")

# ---- Imbue's card names its own element and what that element does (f250)
from core.models import Ability
ib = Ability(id="ib", name="Ignite Blade", description="x", effect="buff", tier="moderate", reach="self", resource="mana", context="combat",
             cost=0, cooldown=0, buff="imbue", element="fire", expressions=["ignite"])
lines = dict(AT.parts(ib))
check("imbue's card says fire and that it burns, in one line", "as fire" in lines.get("Imbue", "") and "burning" in lines["Imbue"]
      and "named in the ability" not in lines["Imbue"] and len(lines) == 1, lines)

at = Ability(id="at", name="Archon of Rot", description="x", effect="buff", tier="moderate", reach="self", resource="mana", context="combat",
             cost=0, cooldown=0, buff="attunement", element="necrotic")
line = dict(AT.parts(at)).get("Attunement", "")
check("Attunement's card names its element and what it does (f261)", "archon of necrotic" in line and "withering" in line and "the ability's element" not in line, line)
check("a buff that can go on an ally says so, not 'you'", "the one it is cast on" in AT.buff_text("enlarge") and " you " not in f" {AT.buff_text('enlarge')} ")

print("\nFAILED:", bad if bad else "none")
sys.exit(1 if bad else 0)
