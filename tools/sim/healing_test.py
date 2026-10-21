"""Healing (f219): single-target heals in six forms, sized by the target and the caster's power, drawing the eye, soured by necrotic
harm; the planner gives every healing slot a form; and the support perks finally reach allies. Numbers from data/rules/healing.yaml."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import battlefield as bf, battlefield_builder as bb, combat, combat_perks as perks, healing
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

H = healing.H


def player(*mechs, hp=400, wis=14, mana=10**4, **kw):
    attrs = {a: 10 for a in combat.ATTRIBUTES}
    attrs["wisdom"] = wis
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs=attrs, hp=hp, max_hp=hp, stamina=200, max_stamina=200,
                          mana=mana, max_mana=mana, weapon_damage=10, hold=1,
                          legendary={m: 1 for m in mechs}, mech_names={m: m.title() for m in mechs}, **kw)

def ally(fid="ally_h", name="Tam", hp=200):
    return combat.Fighter(id=fid, name=name, side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
                          weapon_damage=8, ally_role="fighter", hold=1)

def foe(i=1, hp=10**6, **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
                          weapon_damage=8, behaviors={"fearless": 1}, **kw)

def heal(form, tier="moderate", attribute="wisdom"):
    return Move(id=f"h_{form}", name=f"{form.title()} Prayer", effect="healing", tier=tier, reach="extended", resource="mana",
                attribute=attribute, heal_form=form)

def fight(*fs):
    f = combat.Combat(fighters=list(fs), record=False)
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    return f

rng = random.Random(5)

# ---- size: a share of the TARGET's health, times the caster's power
p, t = player(wis=10), ally(hp=200)
f = fight(p, t, foe())
mend = heal("mend")
check("a heal is a share of the target's health at plain power", abs(healing.base(p, mend, t) - 200 * H["percent"]["moderate"] / 100) < 0.01)
strong = player(wis=20)
check("...and a stronger caster heals more", healing.base(strong, mend, t) > healing.base(p, mend, t))
weak = player(wis=0)
check("...never below the floor", abs(healing.base(weak, mend, t) / healing.base(p, mend, t) - 0.6) < 0.01)

# ---- single target: an ally, not the caster
for n in (1, 2):
    p, t = player(), ally()
    f = fight(p, t, foe())
    p.hp, t.hp = 100, 50
    combat.act_ability(f, p, mend, None, rng, give=[t])
    check(f"mend {n}: the ally is healed, not the caster", t.hp > 50 and p.hp == 100, (t.hp, p.hp))
    combat.act_ability(f, p, mend, None, rng)
    check(f"mend {n}: with no one named, it heals the caster", p.hp > 100)

# ---- renew: spread over the target's turns
for n in (1, 2):
    p, t = player(), ally()
    f = fight(p, t, foe())
    t.hp = 20
    combat.act_ability(f, p, heal("renew"), None, rng, give=[t])
    check(f"renew {n}: nothing at once", t.hp == 20)
    for _ in range(4):
        combat.start_turn(t, f)
    total = healing.base(p, heal("renew"), t) * H["forms"]["renew"]["share"]
    check(f"renew {n}: heals over three turns, about {total:.0f} in all", abs((t.hp - 20) - total) <= 3, (t.hp - 20, total))

# ---- ward: a barrier, capped
for n in (1, 2):
    p, t = player(wis=30), ally()
    f = fight(p, t, foe())
    for _ in range(4):
        combat.act_ability(f, p, heal("ward", "heavy"), None, rng, give=[t])
    check(f"ward {n}: a barrier that never passes half their life", 0 < t.shield <= t.max_hp * H["forms"]["ward"]["cap"] + 0.01, t.shield)

# ---- cleanse: afflictions lifted
for n in (1, 2):
    p, t = player(), ally()
    f = fight(p, t, foe())
    t.statuses.update(poisoned=3, frightened=2, slowed=2)
    combat.act_ability(f, p, heal("cleanse", "light"), None, rng, give=[t])
    check(f"cleanse {n}: two afflictions lifted", sum(s in t.statuses for s in ("poisoned", "frightened", "slowed")) == 1, t.statuses)

# ---- transfer: the caster pays, the ally gets double
for n in (1, 2):
    p, t = player(), ally()
    f = fight(p, t, foe())
    t.hp = 20
    combat.act_ability(f, p, heal("transfer"), None, rng, give=[t])
    check(f"transfer {n}: the caster pays in health and the ally heals twice over", p.hp < 400 and t.hp - 20 > 400 - p.hp, (p.hp, t.hp))

# ---- rescue: a fallen ally rises, once; the truly dead do not
for n in (1, 2):
    p, t = player(), ally()
    f = fight(p, t, foe())
    t.hp = 0
    combat.act_ability(f, p, heal("rescue", "heavy"), None, rng, give=[t])
    check(f"rescue {n}: the fallen ally rises", t.alive and abs(t.hp - t.max_hp * H["forms"]["rescue"]["revive"]) < 1, t.hp)
    t.hp = 0
    combat.act_ability(f, p, heal("rescue", "heavy"), None, rng, give=[t])
    check(f"rescue {n}: but only once a fight - the second turns back to the caster", not t.alive)
p, t = player(), ally()
f = fight(p, t, foe())
t.hp, t.counters["dead"] = 0, 1
combat.act_ability(f, p, heal("rescue", "heavy"), None, rng, give=[t])
check("rescue: the dead stay dead", not t.alive)
p, t = player(), ally()
f = fight(p, t, foe())
t.hp = 0
combat.act_ability(f, p, mend, None, rng, give=[t])
check("only a rescue reaches the fallen", not t.alive)

# ---- withered: necrotic harm halves healing and regeneration
for n in (1, 2):
    p, t = player(), ally()
    e = foe(element="necrotic")
    f = fight(p, t, e)
    combat.take_damage(f, t, 5, e, rng)
    check(f"withered {n}: necrotic harm withers", "withered" in t.statuses)
    t.hp = 20
    healed, _ = perks.mend(f, p, t, 40)
    check(f"withered {n}: the heal is halved", healed == 20, healed)
troll = foe(2, hp=1000, legendary={"regeneration": 5})
f = fight(player(), troll)
troll.hp = 500
combat.start_turn(troll, f)
plain = troll.hp - 500
troll.hp, troll.statuses["withered"] = 500, 2
combat.start_turn(troll, f)
check("withered: regeneration halves too", troll.hp - 500 == round(plain / 2), (plain, troll.hp - 500))

# ---- attention: an enemy that saw a heal goes for the healer
hits = 0
for s in range(200):
    p, t = player(), ally()
    e = foe()
    f = fight(p, t, e)
    f.round = 3
    p.counters["healed_round"] = 3
    if healing.attention_target(f, e, random.Random(s)) is p:
        hits += 1
check("healing draws the eye about half the time", 70 <= hits <= 130, hits)
p, t = player(), ally()
e = foe()
f = fight(p, t, e)
f.round = 5
p.counters["healed_round"] = 2
check("...and only while the heal is fresh", healing.attention_target(f, e, random.Random(1)) is None)

# ---- the support perks reach allies now
p, t = player("triage"), ally()
f = fight(p, t, foe())
t.hp = 20
before = t.hp
combat.act_ability(f, p, mend, None, rng, give=[t])
check("triage reaches an ally through a real heal", t.hp - before >= 2 * healing.base(p, mend, t) * 0.99 or t.hp == t.max_hp, (t.hp, healing.base(p, mend, t)))

# ---- hired healers go through the same path (withering applies)
priest = combat.Fighter(id="ally_p", name="Brother Odo", side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=200, max_hp=200,
                        weapon_damage=5, ally_role="priest", hold=0, reach="ranged")
p = player()
f = fight(p, priest, foe())
p.hp, p.statuses["withered"] = 100, 2
combat.ally_turn(f, priest, rng)
gain = p.hp - 100
priest2 = combat.Fighter(id="ally_p", name="Brother Odo", side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=200, max_hp=200,
                         weapon_damage=5, ally_role="priest", hold=0, reach="ranged")
q = player(); f2 = fight(q, priest2, foe()); q.hp = 100
combat.ally_turn(f2, priest2, rng)
check("a hired priest's heal is withered too", 0 < gain < q.hp - 100, (gain, q.hp - 100))

# ---- the planner gives every healing slot a form, and tells the model what it is
from engine import ability_slots, ability_traits
import types
interp = types.SimpleNamespace(archetype=types.SimpleNamespace(value="support"), families=["healer"], focus="balanced", uses_companions=False,
                               custom_class="Cleric", combat_identity="", summary="", themes=["healer"], primary_attributes=["wisdom"],
                               casting_attribute="wisdom")
forms = set()
for s in range(30):
    try:
        slots = ability_slots.plan(interp, ability_traits.draw_offers(interp, random.Random(s), min_functions=5), 5, random.Random(s))
    except Exception as ex:
        check("the planner runs for a healer", False, repr(ex))
        break
    for sl in slots:
        if sl["effect"] == "healing":
            forms.add(sl["heal_form"])
            if s == 0:
                check("the model is told the form", sl["heal_form"] and H["forms"][sl["heal_form"]]["depict"] in ability_slots.mechanic_text(sl))
check("healers are offered a spread of forms", len(forms) >= 4, forms)

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
