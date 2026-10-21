"""Summons (f222): made things, never companions. Planned forms; sized by the caster; one Bound summon that lasts between fights and
cannot be re-made or switched in a fight; fight-made forms that last a few rounds, two at a time; each form doing its own job.
Companions are living, tamed creatures: the kit gives one in place of a weapon, and only living things can be tamed."""
import random
import sys
import types
from collections import Counter
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("mage", 1))
from engine import battlefield as bf, battlefield_builder as bb, combat, combat_perks as perks, summons
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

S = summons.S


def player(*mechs, hp=400, intel=20, **kw):
    attrs = {a: 10 for a in combat.ATTRIBUTES}
    attrs["intelligence"] = intel
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs=attrs, hp=hp, max_hp=hp, stamina=200, max_stamina=200,
                          mana=10**5, max_mana=10**5, weapon_damage=4, hold=1, armor=10, ward=10,
                          legendary={m: 1 for m in mechs}, mech_names={m: m.title() for m in mechs}, **kw)

def foe(i=1, hp=10**6, **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
                          weapon_damage=8, behaviors={"fearless": 1}, **kw)

def call(form, tier="moderate", mid=None, element=""):
    return Move(id=mid or f"call_{form}", name=f"Call {form}", effect="summon", tier=tier, reach="self", resource="mana",
                attribute="intelligence", summon_form=form, summon_name=f"the {form}", element=element)

def fight(*fs):
    f = combat.Combat(fighters=list(fs), record=False)
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    return f

rng = random.Random(3)

# ---- sized by the caster
p = player(); f = fight(p, foe())
combat.act_ability(f, p, call("striker"), None, rng)
s = summons.made(f)
check("a striker is made", len(s) == 1 and s[0].summon_form == "striker" and s[0].side == "ally", s)
want = 400 * S["health"]["moderate"] / 100 * summons.FORMS["striker"]["health"]
check("its health is a share of the caster's", abs(s[0].max_hp - want) <= 1, (s[0].max_hp, want))
big = player(intel=40); f2 = fight(big, foe())
combat.act_ability(f2, big, call("striker"), None, rng)
check("it strikes with the caster's casting attribute", summons.made(f2)[0].weapon_attrs == ["intelligence"])
check("it is never a companion", not combat.is_companion(s[0]))

# ---- fight-made summons fade, two at a time
p = player(); f = fight(p, foe())
combat.act_ability(f, p, call("striker", "light"), None, rng)
st = summons.made(f)[0]
for r in range(S["rounds"]["light"] + 1):
    f.round += 1
    combat.ally_turn(f, st, rng)
check("a light summon fades after its rounds", not st.alive)
p = player(); f = fight(p, foe())
for form in ("striker", "sentinel", "volatile"):
    combat.act_ability(f, p, call(form), None, rng)
    f.round += 1
    p.cooldowns = {}
forms = sorted(x.summon_form for x in summons.made(f))
check("at most two stand at once; the oldest is let go", forms == ["sentinel", "volatile"], forms)
p = player(); f = fight(p, foe())
combat.act_ability(f, p, call("swarm"), None, rng)
sw = summons.made(f)
check("a swarm is three bodies", len(sw) == 3 and len({x.summon_cast for x in sw}) == 1, len(sw))
combat.act_ability(f, p, call("striker"), None, rng); p.cooldowns = {}
combat.act_ability(f, p, call("decoy", "light"), None, rng)
check("...and the whole swarm counts as one casting", sorted(Counter(x.summon_form for x in summons.made(f)).items()) == [("decoy", 1), ("striker", 1)],
      Counter(x.summon_form for x in summons.made(f)))

# ---- forms do their jobs
hits = 0
for sd in range(200):
    p = player(); e = foe(); f = fight(p, e)
    combat.act_ability(f, p, call("sentinel"), None, rng)
    if summons.redirect(f, e, p, random.Random(sd)).summon_form == "sentinel":
        hits += 1
check("a sentinel takes the blows meant for its caster", hits == 200, hits)
drawn = 0
for sd in range(400):
    p = player(); e = foe(); f = fight(p, e)
    combat.act_ability(f, p, call("decoy", "light"), None, rng)
    if summons.redirect(f, e, p, random.Random(sd)).summon_form == "decoy":
        drawn += 1
check(f"a decoy draws about {summons.FORMS['decoy']['draw']:.0%} of attacks", 0.5 * 400 < drawn < 0.7 * 400, drawn)
p = player(); e = foe(); f = fight(p, e)
combat.act_ability(f, p, call("totem", element="fire"), None, rng)
t = summons.made(f)[0]
h = e.hp
combat.ally_turn(f, t, rng)
check("a fire totem pulses fire into enemies where it stands", e.hp < h and any("pulses fire" in l for l in f.log), f.log[-2:])
check("...and never moves", t.zone_id == p.zone_id and not t.engaged_with)
p = player(); e = foe(); f = fight(p, e)
combat.act_ability(f, p, call("totem"), None, rng)
combat.ally_turn(f, summons.made(f)[0], rng)
check("a totem with no element urges its allies on", "totem_urge" in p.buffs, p.buffs)
p = player(); e = foe(); f = fight(p, e)
combat.act_ability(f, p, call("volatile"), None, rng)
v = summons.made(f)[0]
h = e.hp
combat.take_damage(f, v, v.hp * 10, e, rng)
check("a volatile summon bursts when it falls", e.hp < h and not v.alive, (h, e.hp))

# ---- the Bound summon
p = player(); f = fight(p, foe())
b1, b2 = call("bound", mid="warden"), call("bound", mid="wyrm")
combat.act_ability(f, p, b1, None, rng)
b = summons.bound_of(f)
check("a Bound summon is made in a fight when none stands", b is not None and not b.summon_until)
for _ in range(10):
    f.round += 1
    combat.ally_turn(f, b, rng)
check("...and it does not fade", b.alive)
why = combat.act_ability(f, p, b2, None, rng)
check("another Bound spell cannot switch it mid-fight", bool(why) and "cannot be changed" in why, why)
b.hp = b.max_hp / 4
p.cooldowns = {}
combat.act_ability(f, p, b1, None, rng)
check("its own spell restores it", b.hp > b.max_hp / 4, b.hp)
combat.take_damage(f, b, b.hp * 10, None, rng)
p.cooldowns = {}
why = combat.act_ability(f, p, b1, None, rng)
check("destroyed, it cannot be re-made until the fight is over", bool(why) and "until the fight is over" in why and summons.bound_of(f) is None, why)
check("...nor raised by a rescue", b.counters.get("dead"))

# ---- around the fight: joins whole, stays broken after a loss, re-made outside, switched outside
from core.models import Ability, Summoned
def ab(aid, form="bound"):
    return Ability(id=aid, name=aid.title(), description="d", effect="summon", tier="moderate", reach="self", resource="mana",
                   context="both", cost=10, cooldown=1, summon_form=form, summoned=Summoned(name=f"the {aid}"))
ch = types.SimpleNamespace(bound_summon="warden", bound_broken=False, actives=[ab("warden"), ab("wyrm")])
p = player(); p.moves = [call("bound", mid="warden")]
f = combat.Combat(fighters=[p, foe()], record=False)
summons.join_bound(f, ch)
check("the Bound summon walks into a fight with its maker", summons.bound_of(f) is not None and f.bound_id == "warden")
f.bound_fell = True
note = summons.after_fight(ch, f)
check("unmade in a fight, it stays unmade afterwards", ch.bound_broken and note)
p = player(); p.moves = [call("bound", mid="warden")]
f = combat.Combat(fighters=[p, foe()], record=False)
summons.join_bound(f, ch)
check("...and does not walk into the next fight", summons.bound_of(f) is None)
msg = summons.form_outside(ch, ch.actives[0])
check("casting it outside a fight makes it anew", not ch.bound_broken and "again" in msg, msg)
msg = summons.form_outside(ch, ch.actives[1])
check("another Bound spell outside a fight switches the bond", ch.bound_summon == "wyrm" and "takes its place" in msg, msg)

# ---- perks find 'your summon': the Bound one first
p = player("shared_skin"); f = fight(p, foe())
combat.act_ability(f, p, call("striker"), None, rng); p.cooldowns = {}
combat.act_ability(f, p, call("bound", mid="warden"), None, rng)
check("'your summon' is the Bound summon first", perks.summon_of(f).summon_form == "bound")
p = player("unmaking"); e = foe(); f = fight(p, e)
combat.act_ability(f, p, call("bound", mid="warden"), None, rng); p.cooldowns = {}
combat.act_ability(f, p, call("striker"), None, rng); p.cooldowns = {}
h = e.hp
combat.act_ability(f, p, call("striker"), None, rng)
check("Unmaking bursts a made summon recast while it stands", e.hp < h and not summons.made(f), e.hp)
check("...and never the Bound one", summons.bound_of(f) is not None)
p = player("blood_summons"); f = fight(p, foe())
combat.act_ability(f, p, call("decoy", "light"), None, rng)
bs = summons.made(f)
check("Blood Summons makes a striker a tier up, for the whole fight", len(bs) == 1 and bs[0].summon_form == "striker"
      and bs[0].summon_tier == "moderate" and bs[0].summon_until == 0, [(x.summon_form, x.summon_tier) for x in bs])

# ---- the planner: a summoner gets one Bound and one or two made; a tamer gets none
from engine import ability_slots, ability_traits
def interp(summoner=False, tamer=False):
    return types.SimpleNamespace(archetype=types.SimpleNamespace(value="support"), families=["summoner"], focus="balanced",
                                 uses_companions=tamer, summoner=summoner, custom_class="Binder", combat_identity="", summary="", themes=[],
                                 primary_attributes=["intelligence"], casting_attribute="intelligence", elements=[], constraints=[])
ok, ranges, made_forms = True, set(), Counter()
for sd in range(40):
    i = interp(summoner=True)
    sl = ability_slots.plan(i, ability_traits.draw_offers(i, random.Random(sd), min_functions=5), 5, random.Random(sd))
    sm = [s for s in sl if s["effect"] == "summon"]
    ok &= sum(s["summon_form"] == "bound" for s in sm) == 1 and all(s["resource"] == "mana" for s in sm)
    ranges.add(len(sm))
    made_forms.update(s["summon_form"] for s in sm if s["summon_form"] != "bound")
    if sd == 0:
        s0 = next(s for s in sm if s["summon_form"] == "bound")
        check("the model is told the form", summons.FORMS["bound"]["depict"] in ability_slots.mechanic_text(s0))
check("a summoner always gets exactly one Bound summon, all paid in mana", ok)
check("...and one or two made in the fight", ranges <= {2, 3} and len(ranges) == 2, ranges)
check("...in a spread of forms", len(made_forms) >= 5, made_forms)
i = interp(tamer=True)
sl = ability_slots.plan(i, ability_traits.draw_offers(i, random.Random(1), min_functions=5), 5, random.Random(1))
check("a tamer gets commands and no summons", not [s for s in sl if s["effect"] == "summon"] and [s for s in sl if s["effect"] == "command"])

# ---- companions are living things
from engine import taming
from character import kit
check("only living things can be tamed", set(taming.T["categories"]) <= {"beast", "monstrosity", "dragon", "fey", "plant"})
check("the kit's companions are living things", kit.COMPANION_CATEGORIES <= {"beast", "monstrosity", "dragon", "fey", "plant"})

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
