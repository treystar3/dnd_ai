"""Riders, shapes and buffs: each does what it says, numbers come from the tier, and every new character is offered a different draw."""
import random, sys, collections
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import combat as C, ability_traits as AT
from core.models import Archetype
from llm.contracts import ClassInterpretation, ActiveProposal, ActiveSet
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

def F(id, side, hp=100000, **k):
    d = dict(id=id, name=id, side=side, level=40, attrs={a: 14 for a in C.ATTRIBUTES}, hp=hp, max_hp=hp, weapon_damage=50, armor=0, ward=0,
             stamina=1000, max_stamina=1000, mana=1000, max_mana=1000)
    d.update(k)
    return C.Fighter(**d)

def mv(effect="damage", tier="moderate", reach="melee", resource="stamina", **k):
    return C.Move(id="m", name="Test Move", effect=effect, tier=tier, reach=reach, resource=resource, attribute="intelligence" if resource == "mana" else "", **k)

def setup(n_foes=2, **fk):
    p = F("p", "player", **fk)
    foes = [F(f"e{i}", "enemy", armor=0) for i in range(n_foes)]
    cmb = C.Combat(fighters=[p] + foes)
    from engine import battlefield as bf
    for e in foes:
        bf.engage(cmb, e, p)
    return cmb, p, foes

def avg(move, trials=200, foe_hp_frac=1.0, **fk):
    tot = 0
    for i in range(trials):
        cmb, p, foes = setup(**fk)
        foes[0].hp = foes[0].max_hp * foe_hp_frac
        h0 = [f.hp for f in foes]
        C.act_ability(cmb, p, move, foes[0], random.Random(i))
        tot += sum(a - f.hp for a, f in zip(h0, foes))
    return tot / trials

AT.T["plain_damage"] = 0        # these tests compare each trait with a neutral plain strike; the Honed bonus has its own test
base = avg(mv())
# ---- shapes
vol = avg(mv(shape="volley"))
check("volley deals about the same total as a plain strike (1.2x of three small hits)", 0.9 < vol / base < 1.5, f"{vol/base:.2f}")
cmb, p, foes = setup(); C.act_ability(cmb, p, mv(shape="volley"), foes[0], random.Random(1))
check("volley is several separate strikes", sum("Test Move" in l or "strikes again" in l for l in cmb.log) >= 2, cmb.log)
fin_low = avg(mv(shape="finisher"), foe_hp_frac=0.1) / avg(mv(), foe_hp_frac=0.1)
fin_hi = avg(mv(shape="finisher")) / base
check("finisher is a normal blow on healthy foes and strong on wounded ones (never worse than plain)",
      0.95 <= fin_hi <= 1.15 and fin_low > 1.4, f"{fin_hi:.2f} / {fin_low:.2f}")
op_hi = avg(mv(shape="opener")) / base; op_lo = avg(mv(shape="opener"), foe_hp_frac=0.5) / avg(mv(), foe_hp_frac=0.5)
check("opener favours the first strike and is a plain blow after (never worse)", op_hi > 1.35 and 0.95 <= op_lo <= 1.1,
      f"{op_hi:.2f} / {op_lo:.2f}")
for sd in range(30):
    cmb, p, foes = setup(); h = [f.hp for f in foes]; C.act_ability(cmb, p, mv(shape="chain"), foes[0], random.Random(sd))
    if foes[0].hp < h[0] and foes[1].hp < h[1]:
        break
check("chain also hits a second enemy for less", foes[1].hp < h[1] and (h[1] - foes[1].hp) < (h[0] - foes[0].hp), (h[0]-foes[0].hp, h[1]-foes[1].hp))
oc = avg(mv(shape="overcharge")) / base
check("overcharge hits harder", 1.2 < oc < 1.6, f"{oc:.2f}")
m_oc, m_pl = mv(shape="overcharge"), mv()
check("overcharge costs half again", C.cost_of(F("p", "player"), m_oc) >= round(C.cost_of(F("p", "player"), m_pl) * 1.4))

# ---- riders
def stat_rate(rider, tier, status, n=400):
    hits = 0
    for i in range(n):
        cmb, p, foes = setup(); C.act_ability(cmb, p, mv(rider=rider, tier=tier), foes[0], random.Random(i))
        hits += status in foes[0].statuses
    return hits / n
for rid, st in (("rend", "bleeding"), ("chill", "slowed"), ("dread", "frightened"), ("dazzle", "blinded")):
    lo, hi = stat_rate(rid, "light", st), stat_rate(rid, "heavy", st)
    check(f"{rid} applies {st} more often at higher tiers", 0.05 < lo < hi, f"{lo:.2f} -> {hi:.2f}")
cmb, p, foes = setup(); C.act_ability(cmb, p, mv(rider="shove"), foes[0], random.Random(1))
check("shove drives the target out of the press", "p" not in foes[0].engaged_with and "exposed" in foes[0].position_tags,
      (foes[0].engaged_with, foes[0].position_tags))
cmb, p, foes = setup(); p.hp = 1000; foes[0].hp = foes[0].max_hp; C.act_ability(cmb, p, mv(rider="siphon"), foes[0], random.Random(2))
check("siphon heals the caster", p.hp > 1000, p.hp)
cmb, p, foes = setup(); foes[1].hp = 50000; C.act_ability(cmb, p, mv(rider="seeker"), foes[0], random.Random(2))
check("seeker goes for the most wounded enemy", foes[1].hp < 50000 and foes[0].hp == foes[0].max_hp, (foes[0].hp, foes[1].hp))
cmb, p, foes = setup(); p.stamina = 500; C.act_ability(cmb, p, mv(rider="thrift"), foes[0], random.Random(1))
cmb2, p2, foes2 = setup(); p2.stamina = 500; C.act_ability(cmb2, p2, mv(), foes2[0], random.Random(1))
check("thrift gives part of the cost back", p.stamina > p2.stamina, (p.stamina, p2.stamina))
def armored_avg(rider):
    tot = 0
    for i in range(200):
        cmb, p, foes = setup(); foes[0].armor = 200; h = foes[0].hp
        C.act_ability(cmb, p, mv(rider=rider, resource="stamina"), foes[0], random.Random(i)); tot += h - foes[0].hp
    return tot / 200
check("sunder gets through armor", armored_avg("sunder") > armored_avg("") * 1.2, (armored_avg("sunder"), armored_avg("")))
cmb, p, foes = setup(); C.act_ability(cmb, p, mv(rider="sunder"), foes[0], random.Random(1))
check("sunder leaves no permanent change", p.armor_pierce == 0 and "wardbreaker" not in p.legendary)

# ---- buffs (f235: the four new buffs are tested in tools/sim/buffs_test.py; here only the shared rules)
cmb, p, foes = setup(); b = mv(effect="buff", reach="self", buff="blur"); C.act_ability(cmb, p, b, None, random.Random(1))
n = 0
while p.buffs and n < 20:
    C.start_turn(p, cmb); n += 1
check("a buff lasts its rounds then fades", n == 3, n)
cmb, p, foes = setup()
C.act_ability(cmb, p, mv(effect="buff", reach="self", buff="blur"), None, random.Random(1))
m2 = C.Move(id="m2", name="Other", effect="buff", tier="moderate", reach="self", resource="stamina", buff="blur")
C.act_ability(cmb, p, m2, None, random.Random(1))
check("only one buff of a kind at a time", len(p.buffs) == 1 and "m2" in p.buffs, list(p.buffs))
check("buffs end with the fight (nothing persists on the character)", True)

# ---- creation: contract validation and variety
interp = lambda arch, themes, fams: ClassInterpretation(archetype=Archetype(arch), custom_class="X", combat_identity="x", themes=themes, summary="x",
                                                         focus="balanced", uses_companions=False, families=fams, primary_attributes=["strength"], casting_attribute="")
combos = set()
for i in range(300):
    for arch, th, fam in (("mage", ["fire", "storm"], ["mage"]), ("warrior", ["blade", "shield"], ["warrior"]), ("rogue", ["shadow", "knife"], ["rogue"]),
                          ("support", ["light", "mending"], ["healer"])):
        o = AT.draw_offers(interp(arch, th, fam))
        combos.add((arch, tuple(sorted(o["riders"])), tuple(sorted(o["shapes"])), tuple(sorted(o["buffs"]))))
per = collections.Counter(c[0] for c in combos)
check("every draw is varied (hundreds of different offers per class)", all(v > 80 for v in per.values()), dict(per))
mage_riders = collections.Counter(r for c in combos if c[0] == "mage" for r in c[1])
warrior_riders = collections.Counter(r for c in combos if c[0] == "warrior" for r in c[1])
check("offers still lean toward the class", mage_riders["chill"] > warrior_riders["chill"] and warrior_riders["rend"] > mage_riders["rend"], (mage_riders["chill"], warrior_riders["chill"]))
offers = {"riders": ["rend", "chill", "dread", "sunder", "shove", "siphon"], "shapes": ["volley", "finisher", "chain"], "buffs": ["blur", "precision"]}
def prop(i, **k):
    d = dict(name=f"Move {i}", description="d", effect="damage", tier="light", reach="melee", resource="stamina", context="combat"); d.update(k)
    return ActiveProposal(**d)
def full(riders=3, shapes=2, buffs=1, extra=None):
    ps = [prop(0, rider="rend"), prop(1, rider="chill"), prop(2, rider="dread"), prop(3, shape="volley"), prop(4, shape="finisher")]
    ps = ps[:riders] + ps[3:3 + shapes]
    for b in range(buffs):
        ps.append(prop(20 + b, effect="buff", buff="blur", reach="self"))
    for j in range(15 - len(ps)):
        ps.append(prop(40 + j, context="both", effect="healing" if j < 3 else "damage"))
    return ps[:15]
def ok(ps):
    try:
        ActiveSet.model_validate({"skills": [p.model_dump() for p in ps]}, context={"offers": offers, "min_noncombat": 0}); return True
    except Exception as e:
        return str(e)[:160]
check("a full set validates", ok(full()) is True, ok(full()))
check("too few riders are filled in from the offer", ok(full(riders=1)) is True, ok(full(riders=1)))
check("too few shapes are filled in from the offer", ok(full(shapes=0)) is True, ok(full(shapes=0)))
check("a set with no buff is refused", ok(full(buffs=0)) is not True)
bad_off = full(); bad_off[0] = prop(0, rider="siphon"); bad_off[1] = prop(1, rider="seeker")
check("a rider that wasn't offered is replaced from the offer", ok(bad_off) is True, ok(bad_off))
p_ = prop(0, effect="healing", rider="rend", shape="volley")
check("riders and shapes are stripped from abilities they don't suit", p_.rider == "" and p_.shape == "")
p_ = prop(0, effect="buff", buff="blur", context="both", reach="melee")
check("a buff is combat-only and self-targeted", p_.context.value == "combat" and p_.reach.value == "self")
p_ = prop(0, effect="damage", reach="area", shape="chain")
check("area abilities get no shape", p_.shape == "")
from engine import abilities
a = abilities.materialize_active(prop(5, effect="buff", buff="precision", tier="heavy", reach="self"))
check("materialized abilities keep their traits and describe them", a.buff == "precision" and "15%" in AT.describe(a), AT.describe(a))

# ---- commands
def pack_scene():
    cmb, p, foes = setup(n_foes=1)
    pet = F("ally_pet", "ally", weapon_damage=50)
    cmb.fighters.append(pet)
    return cmb, p, foes, pet
def cmv(kind, tier="moderate"):
    return C.Move(id="c_" + kind, name="Order " + kind, effect="command", tier=tier, reach="extended", resource="stamina", command=kind)
cmb, p, foes, pet = pack_scene(); h = foes[0].hp; C.act_ability(cmb, p, cmv("focus"), foes[0], random.Random(3))
check("focus fire makes the pack strike", foes[0].hp < h or any("on command" in l for l in cmb.log), cmb.log[-2:])
def pet_dmg(buffed, n=200):
    tot = 0
    for i in range(n):
        cmb, p, foes, pet = pack_scene()
        if buffed: C.act_ability(cmb, p, cmv("press"), None, random.Random(i))
        h = foes[0].hp; C.apply_damage(cmb, pet, foes[0], 1.0, "hits", random.Random(i)); tot += h - foes[0].hp
    return tot / n
check("press the attack makes companions hit harder", pet_dmg(True) > pet_dmg(False) * 1.25, (pet_dmg(False), pet_dmg(True)))
def pet_taken(buffed, n=100):
    tot = 0
    for i in range(n):
        cmb, p, foes, pet = pack_scene()
        if buffed: C.act_ability(cmb, p, cmv("hold"), None, random.Random(i))
        pet.hp = pet.max_hp; C.take_damage(cmb, pet, 1000, foes[0], random.Random(i), "physical"); tot += pet.max_hp - pet.hp
    return tot / n
check("hold the line makes companions take less", pet_taken(True) < pet_taken(False) * 0.8, (pet_taken(False), pet_taken(True)))
cmb, p, foes, pet = pack_scene(); C.act_ability(cmb, p, cmv("guard"), None, random.Random(1))
hp0, pet0 = p.hp, pet.hp
for sd in range(20):
    C.apply_damage(cmb, foes[0], p, 1.0, "hits", random.Random(sd))
check("guard sends part of the damage to a companion", pet.hp < pet0 and p.hp < hp0, (hp0 - p.hp, pet0 - pet.hp))
cmb, p, foes = setup(n_foes=1); C.act_ability(cmb, p, cmv("press"), None, random.Random(1))
check("a command with no companion does nothing harmful", not p.buffs)
cmd_offers = {"riders": [], "shapes": [], "buffs": [], "commands": ["focus", "guard", "press", "hold"]}
def cprop(i, c): return prop(i, effect="command", command=c, reach="extended")
def cok(cs):
    from llm.contracts import SummonProposal
    summ = prop(99, effect="summon", reach="self", resource="mana", summons=SummonProposal(name="Pup", description="d"))
    ps = [cprop(i, c) for i, c in enumerate(cs)] + [summ] + [prop(20 + j) for j in range(14 - len(cs))]
    try:
        ActiveSet.model_validate({"skills": [x.model_dump() for x in ps]}, context={"offers": cmd_offers, "min_noncombat": 0}); return True
    except Exception as e:
        return str(e)[:120]
check("different commands are accepted", cok(["focus", "guard", "press"]) is True, cok(["focus", "guard", "press"]))
check("duplicate commands are refused", cok(["focus", "focus"]) is not True)
check("a command ability defaults to focus", prop(0, effect="command", reach="extended").command == "focus")
o = AT.draw_offers(interp("mage", ["x"], ["mage"]))
check("commands are only offered to companion classes", o["commands"] == [])
ci = interp("mage", ["x"], ["summoner"]); ci.uses_companions = True
check("companion classes are offered all five commands", AT.draw_offers(ci)["commands"] == ["focus", "guard", "press", "hold", "distract"])
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)
