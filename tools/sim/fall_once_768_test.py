"""(f768) A death happens once, whatever killed (found by the code audit, engine2-2, trace-fight-4 and trace-fight-5: a Storm Chosen
arc killed a wolf that was not the blow's target and no line of the round told it; a pack leader dead of a torn wound routed nobody and
stayed tied to the player; a foe killed earlier in the foes' phase still reached its turn and fell a second time, paid to the player).
One fall step (engine/damage.py) every damage path ends in, the moment a health stage takes a fighter from standing to zero: a summon
unmade, every tie released, the fall told by its cause with felled_by set, the boss's fall, the rout for a foe on one roll, Avenger for
an ally, and the kill credited by one function to the one who caused it (the owner, 2026-11-19: a death by something laid earlier is
the kill of whoever laid it, with the whole credit a blow gives). The blow's own target is still paid at the blow's tail, through a
record of the blow in progress held on the fight and never in its row.
Every case asserts one fall line, after the line of what killed and before any rout it set off; one rout roll for a foe, none for an
ally; battlefield.validate == [] and nobody tied to the fallen; felled_by; and the credit on the one who caused it, once. The finder's
case (a Storm Chosen arc), then the kind: thorns, a guard's share, a pack leader dead of a torn wound, Retribution, Death's Door, a
Bound summon dead of poison, a bursting summon dead of a torn wound (on the death's keyed die), an ally and the player dead of a tick,
a foe dead of a poison nobody is recorded laying, a foe dead of a curse at its own turn start, Death's Door carried by a curse, a foe
felled earlier reaching its turn, a pack-bond blow that kills, a missed blow whose riposte meets the player's thorns, a kill by a gear
element's damage with Vampiric and Rampage, a family's venom killing a companion, a poison carried on by Plaguebearer, a cause dead
before the death it caused, a companion raised and killed again (and then by no one named), the hires' lines, the player's round and
a Phoenix's saving told as the death came, the stage check and the fence over every stage that writes health, a tick's words from
data, and the blow's record outside the row.
What must not move: an ordinary killing blow draws the blow's die as before, and a foe's tick death routs the same foes as before.
Run: python tools/sim/fall_once_768_test.py"""
import copy
import random
import re
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 1)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import battlefield as bf
from engine import behaviors, combat, combat_perks, data_check, streams, summons
from engine import effects as fx
from engine import spellcraft as SC
from engine.combat import Move

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def fighter(fid, side, hp=10 ** 6, dex=12, dmg=12, level=5, name=None, **kw):
    attrs = {a: 12 for a in combat.ATTRIBUTES}
    attrs["dexterity"] = dex
    return combat.Fighter(id=fid, name=name or fid, side=side, level=level, attrs=attrs, hp=hp, max_hp=kw.pop("max_hp", hp),
                          stamina=10 ** 4, max_stamina=10 ** 4, mana=10 ** 4, max_mana=10 ** 4, weapon_damage=dmg,
                          weapon_attrs=["strength"], hold=2, **kw)


def fight(*fs, **kw):
    f = combat.Combat(fighters=list(fs), record=True, serial=kw.pop("serial", "fo"), **kw)
    combat.ensure_field(f)
    f.opened = True
    return f


# ---- the probes: every rout rolled for a death, and every kill paid (by whom, for whom)
MORALE, PAID, PEEK = [], [], {}
_morale, _on_kill, _after_hit, _on_fall = behaviors.morale_on_death, combat_perks.on_kill, combat_perks.after_hit, summons.on_fall


def morale_on_death(c, fallen, rng):
    MORALE.append(fallen.id)
    return _morale(c, fallen, rng)


def on_kill(c, att, dfn, rng, echo=False):
    PAID.append((att.id if att is not None else None, dfn.id))
    return _on_kill(c, att, dfn, rng, echo=echo)


def after_hit(c, att, dfn, outcome, taken, rng):
    if PEEK.get("on"):                                       # mid-blow: what the fight holds, and what its row would
        PEEK.update(open=list(getattr(c, "_open", None) or []), dump=c.model_dump(), json=c.model_dump_json(), on=False)
    return _after_hit(c, att, dfn, outcome, taken, rng)


def on_fall(c, f, rng):
    PEEK["burst_die"] = rng.getstate()
    return _on_fall(c, f, rng)


behaviors.morale_on_death, combat_perks.on_kill, combat_perks.after_hit, summons.on_fall = morale_on_death, on_kill, after_hit, on_fall


def reset():
    MORALE.clear()
    PAID.clear()
    PEEK.clear()


ROUT = re.compile(r"breaks and runs|throws down .* yields|breaks, (seeing|with so many)|loses heart")


def falls(f, x) -> list[int]:
    """Where the story tells this fighter's fall: its name, then falls, succumbs or collapses (never 'seeing it fall')."""
    w = re.escape(combat.who(x))
    pat = re.compile(rf"(^|, and |\. ){w} (fall|falls|succumbs|collapse|collapses)\b", re.I)
    return [i for i, s in enumerate(f.story) if pat.search(s)]


def payers(x) -> list:
    return [a for a, d in PAID if d == x.id and a is not None]


def one_death(name, f, x, killer, after=None, paid=True):
    """The kind's assertions on one death."""
    got = falls(f, x)
    check(f"{name}: the fall is told once", len(got) == 1, f.story)
    if after is not None:
        cause = [i for i, s in enumerate(f.story) if after(s)]
        check(f"{name}: ...after the line of what killed", bool(got) and bool(cause) and cause[0] < got[0], f.story)
    routs = [i for i, s in enumerate(f.story) if ROUT.search(s)]
    check(f"{name}: ...and before any rout it set off", bool(got) and all(i > got[0] for i in routs), f.story)
    check(f"{name}: one rout roll for a foe, none for an ally", MORALE.count(x.id) == (1 if x.side == "enemy" else 0), MORALE)
    check(f"{name}: nobody is tied to the fallen, and the field holds together",
          not x.engaged_with and not any(x.id in o.engaged_with for o in f.fighters) and bf.validate(f) == [],
          ([(o.id, o.engaged_with) for o in f.fighters], bf.validate(f)))
    if killer is None:
        check(f"{name}: nobody is named, and no kill is paid", x.id not in f.felled_by and payers(x) == [], (f.felled_by, PAID))
        return
    check(f"{name}: felled_by names the one who caused it", f.felled_by.get(x.id) == combat.who(killer), f.felled_by)
    if paid:
        check(f"{name}: the kill is paid to the one who caused it, once", payers(x) == [killer.id], PAID)
    else:
        check(f"{name}: ...who is not paid for it", payers(x) == [], PAID)


streams.begin(7, 1, "I fight.")

# ---- 1. the finder's case: a Storm Chosen arc kills a wolf that was not the blow's target, and the round tells it
found = None
for seed in range(200):
    reset()
    p = fighter("player", "player", dmg=200)
    p.legendary["storm_chosen"] = 1
    w1, w2, w3 = fighter("wolf 1", "enemy", dmg=0.001), fighter("wolf 2", "enemy", hp=3, dmg=0.001), fighter("wolf 3", "enemy", dmg=0.001)
    w2.counters["pyre_by"] = "player"                         # a mark that waits for death
    f = fight(p, w1, w2, w3, conditions=["in_storm"])
    bf.engage(f, p, w1)
    rng = random.Random(seed)
    combat.act_attack(f, p, w1, rng)
    if not w2.alive and w1.alive:
        combat.finish_round(f, rng)
        found = (f, p, w2)
        break
check("(a seed where the arc kills the second wolf)", found is not None)
if found:
    f, p, w2 = found
    one_death("the finder's case, a Storm Chosen arc's kill", f, w2, p, after=lambda s: s.startswith("The storm answers"))
    check("...and the mark that waited for its death did its work (Pyre)", "pyre_by" not in w2.counters
          and "burning_ground" in (f.zone_effects.get(w2.zone_id) or {}), (w2.counters, f.zone_effects))

# ---- 2. thorns kill the wolf that struck
found = None
for seed in range(200):
    reset()
    p = fighter("player", "player", hp=4000, armor=50)
    p.legendary["thorns"] = 100
    wolf, w2 = fighter("wolf 1", "enemy", hp=1, max_hp=40, dmg=10), fighter("wolf 2", "enemy", dmg=0.001)
    f = fight(p, wolf, w2)
    bf.engage(f, wolf, p)
    combat.apply_damage(f, wolf, p, 1.0, "attacks", random.Random(seed))
    if not wolf.alive:
        found = (f, p, wolf)
        break
check("(a seed where the thorns kill the striker)", found is not None)
if found:
    one_death("thorns", found[0], found[2], found[1], after=lambda s: "(Thorns)" in s)

# ---- 3. a guard's share kills the guard
found = None
for seed in range(200):
    reset()
    p = fighter("player", "player", hp=4000)
    p.legendary["guarded"] = 90
    ash, wolf = fighter("ally_ash", "ally", hp=1, max_hp=60, name="Ash"), fighter("wolf 1", "enemy", dmg=40)
    f = fight(p, ash, wolf)
    bf.engage(f, wolf, p)
    combat.apply_damage(f, wolf, p, 1.0, "attacks", random.Random(seed))
    if not ash.alive:
        found = (f, ash, wolf)
        break
check("(a seed where the share kills the guard)", found is not None)
if found:
    f, ash, wolf = found
    one_death("a guard's share", f, ash, wolf, after=lambda s: "throws itself in the way" in s)
    check("...told as harm, never as a blow on the guard", any(s.startswith("Ash falls and does not rise") for s in f.story)
          and not any("Ash falls to" in s for s in f.story), f.story)

# ---- 4. a pack leader dead of a torn wound, the player with a bow
kills = routed = 0
first = None
for seed in range(120):
    reset()
    p = fighter("player", "player", hp=4000, dmg=4, reach="ranged")
    lead = fighter("wolf 1", "enemy", hp=30, max_hp=1000, level=6, rank="elite", dmg=0.001)
    pack = [fighter(f"wolf {i}", "enemy", level=3, dmg=0.001) for i in (2, 3, 4)]
    f = fight(p, lead, *pack)
    bf.engage(f, lead, p)
    combat.add_status(f, lead, "bleeding", 3, p)
    fx.set_strength(lead, "bleeding", 500)                  # the wound, not the shot, is what kills
    combat.apply_damage(f, p, lead, 1.0, "shoots", random.Random(seed), can_cleave=False)
    hit = next((h for h in f.hits if h["dfn"] == lead.name), None)
    if lead.alive or hit is None or hit["final"] >= 30 or not any("wound open again" in s for s in f.story):
        continue
    kills += 1
    routed += sum(1 for w in pack if w.fled)
    if first is None and any(w.alive and not w.fled for w in pack):     # a wolf left standing for the bow's next shot
        first = (f, p, lead, pack, list(MORALE), list(PAID))
check("(seeds where the shot leaves the leader standing and the torn wound kills it)", kills >= 10, kills)
check("the pack routs at a leader dead of a torn wound", routed > 0, (routed, kills))
check("(one of them leaves a wolf standing for the next shot)", first is not None)
if first:
    f, p, lead, pack, MORALE[:], PAID[:] = first
    one_death("a pack leader dead of a torn wound", f, lead, p, after=lambda s: "wound open again" in s)
    standing = next(w for w in pack if w.alive and not w.fled)
    check("...and the bow takes no point-blank step at the next wolf", not [s for s in combat.hit_parts(p, standing, f)[1]
                                                                         if "point-blank" in s[0]], combat.hit_parts(p, standing, f))

# ---- 5. Retribution: the rebound kills the striker
found = None
for seed in range(120):
    reset()
    p = fighter("player", "player", hp=4000)
    p.legendary["retribution"] = 100
    lead = fighter("wolf 1", "enemy", hp=3, max_hp=40, level=6, rank="elite", dmg=40)
    pack = [fighter(f"wolf {i}", "enemy", level=3, dmg=0.001) for i in (2, 3)]
    f = fight(p, lead, *pack)
    bf.engage(f, lead, p)
    combat.apply_damage(f, lead, p, 1.0, "attacks", random.Random(seed))
    if not lead.alive:
        found = (f, p, lead)
        break
check("(a seed where the rebound kills the striker)", found is not None)
if found:
    f, p, lead = found
    one_death("Retribution", f, lead, p, after=lambda s: "rebounds into" in s)
    check("...told as its own undoing", any(s.startswith("The first wolf collapses, undone by its own violence") for s in f.story), f.story)

# ---- 6. Death's Door ends a pack leader
found = None
for seed in range(120):
    reset()
    p = fighter("player", "player", hp=4000, dmg=4)
    lead = fighter("wolf 1", "enemy", hp=100, max_hp=1000, level=6, rank="elite", dmg=0.001)
    pack = [fighter(f"wolf {i}", "enemy", level=3, dmg=0.001) for i in (2, 3)]
    f = fight(p, lead, *pack)
    bf.engage(f, lead, p)
    p.hit_element = p.element = "necrotic"
    p.casting = {"exprs": ["deaths_door"], "tier": "moderate", "name": "Death's Door", "once": []}
    try:
        combat.apply_damage(f, p, lead, 0.5, "strikes", random.Random(seed), can_cleave=False)
    finally:
        SC.end(p)
    if not lead.alive:
        found = (f, p, lead)
        break
check("(a seed where Death's Door ends the leader)", found is not None)
if found:
    one_death("Death's Door", found[0], found[2], found[1], after=lambda s: "death reaches for" in s.lower())

# ---- 7. a Bound summon dead of poison is unmade: it cannot be cast again in this fight
reset()
mv = Move(id="bound_test", name="Bound Thing", effect="summon", tier="moderate", reach="self", resource="mana", attribute="intelligence",
          summon_form="bound")
p, wolf = fighter("player", "player"), fighter("wolf 1", "enemy", dmg=0.001)
f = fight(p, wolf)
f.bound_id = mv.id
s = summons.make(f, p, mv, form="bound")[0]
combat.enters(f, s)
bf.engage(f, wolf, s)
combat.add_status(f, s, "poisoned", 3, wolf)
fx.set_strength(s, "poisoned", [500])
s.hp = 1
combat.ally_turn(f, s, random.Random(1))
check("(the Bound summon dies of the poison at its turn)", not s.alive, s.hp)
one_death("a Bound summon dead of poison", f, s, wolf)
check("...it is unmade, and refused if cast again in this fight", f.bound_fell and bool(summons.refuse(f, p, mv)), (f.bound_fell, summons.refuse(f, p, mv)))

# ---- 8. a bursting summon dead of a torn wound bursts, on the death's own keyed die
mv = Move(id="volatile_test", name="Ember Thing", effect="summon", tier="moderate", reach="self", resource="mana", attribute="intelligence",
          summon_form="volatile")
found = None
for seed in range(60):
    reset()
    p, wolf = fighter("player", "player"), fighter("wolf 1", "enemy", hp=10 ** 5, dmg=2)
    f = fight(p, wolf)
    s = summons.make(f, p, mv, form="volatile")[0]
    combat.enters(f, s)
    wolf.zone_id = s.zone_id
    bf.engage(f, wolf, s)
    s.max_hp, s.hp = 10 ** 4, 520
    combat.add_status(f, s, "bleeding", 3, wolf)
    fx.set_strength(s, "bleeding", 5000)
    combat.apply_damage(f, wolf, s, 1.0, "bites", random.Random(seed))
    if not s.alive and any("wound open again" in x for x in f.story):
        found = (f, s, wolf)
        break
check("(a seed where the bite tears the summon's wound and it dies)", found is not None)
if found:
    f, s, wolf = found
    one_death("a bursting summon dead of a torn wound", f, s, wolf, after=lambda x: "wound open again" in x)
    burst = [i for i, x in enumerate(f.story) if "bursts apart" in x]
    check("...it bursts over the wolf, told after its fall", bool(burst) and s.counters.get("burst") and wolf.hp < 10 ** 5
          and falls(f, s) and falls(f, s)[0] < burst[0], f.story)
    keyed = streams.keyed("morale", s.id, f.serial, f.round).getstate()
    check("...on the death's own keyed die (the torn wound's path has none of its own)", PEEK.get("burst_die") == keyed)

# ---- 9. an ally dead of a poison a wolf laid, at the start of its turn
reset()
p, bryn, wolf = fighter("player", "player"), fighter("ally_bryn", "ally", hp=3, max_hp=60, name="Bryn", ally_role="warrior"), \
    fighter("wolf 1", "enemy", dmg=0.001)
f = fight(p, bryn, wolf)
bf.engage(f, wolf, bryn)
combat.add_status(f, bryn, "poisoned", 3, wolf)
fx.set_strength(bryn, "poisoned", [500])
combat.ally_turn(f, bryn, random.Random(1))
check("(Bryn dies of the poison at her turn)", not bryn.alive)
one_death("an ally dead of a tick", f, bryn, wolf)
check("...told as the wolf's poison doing its work", "The first wolf's poison does its work, and Bryn falls and does not rise" in f.story, f.story)
check("...and the fight's log says she succumbs", "Bryn succumbs" in f.log, f.log)

# ---- 10. the player dead of a burn a wolf laid, at the start of their turn
reset()
p, wolf = fighter("player", "player", hp=3, max_hp=400), fighter("wolf 1", "enemy", dmg=0.001)
f = fight(p, wolf)
bf.engage(f, wolf, p)
combat.add_status(f, p, "burning", 3, wolf)
fx.set_strength(p, "burning", 500)
check("(the player's turn does not start: the burn kills them)", combat.start_turn(p, f, random.Random(1)) is False and not p.alive)
one_death("the player dead of a tick", f, p, wolf)
check("...told as the fire the wolf left", "The fire the first wolf left on you burns on. You fall, and the world goes dark" in f.story, f.story)

# ---- 11. a foe dead of a poison nobody is recorded laying: told unnamed, nobody paid, the marks still run
reset()
p, wolf, w2 = fighter("player", "player"), fighter("wolf 1", "enemy", hp=3, max_hp=40), fighter("wolf 2", "enemy", dmg=0.001)
f = fight(p, wolf, w2)
bf.engage(f, wolf, p)
fx.put_status(wolf, "poisoned", 3)
fx.set_strength(wolf, "poisoned", [500])
wolf.counters["pyre_by"] = "player"
f.round = 2
combat.start_turn(wolf, f, random.Random(1))
check("(the wolf dies of the poison at its turn)", not wolf.alive)
one_death("a foe dead of a poison nobody laid", f, wolf, None)
check("...it succumbs", any(x.startswith("The first wolf succumbs to what was done to it") for x in f.story), f.story)
check("...and the mark that waited for its death did its work", "pyre_by" not in wolf.counters, wolf.counters)

# ---- 12. a foe dead of a curse at its own turn start: one rout, the curse's caster paid
found = None
for seed in range(60):
    reset()
    p = fighter("player", "player")
    lead = fighter("wolf 1", "enemy", hp=5, max_hp=40, level=6, rank="elite", dmg=0.001)
    pack = [fighter(f"wolf {i}", "enemy", level=3, dmg=0.001) for i in (2, 3)]
    f = fight(p, lead, *pack, serial=f"s{seed}")
    f.round = 2
    bf.engage(f, lead, p)
    fx.put_curse(lead, dict(by="player", per=500, left=2, name="Withering Curse", tier="moderate", element="", exprs=[]))
    combat.start_turn(lead, f, random.Random(seed))
    if any(w.fled for w in pack):
        found = (f, p, lead)
        break
check("(a seed where the curse's kill routs the pack)", found is not None)
if found:
    one_death("a foe dead of a curse at its own turn start", found[0], found[2], found[1], after=lambda s: "gnaws at" in s)

# ---- 12b. Death's Door carried by a curse ends a foe at its own turn start: the curse's caster is paid, at once
reset()
p = fighter("player", "player")
lead = fighter("wolf 1", "enemy", hp=100, max_hp=1000, level=6, rank="elite", dmg=0.001)
pack = [fighter(f"wolf {i}", "enemy", level=3, dmg=0.001) for i in (2, 3)]
f = fight(p, lead, *pack, serial="dd")
f.round = 2
bf.engage(f, lead, p)
fx.put_curse(lead, dict(by="player", per=10, left=2, name="Grave Curse", tier="moderate", element="necrotic", exprs=["deaths_door"]))
combat.start_turn(lead, f, random.Random(1))
check("(Death's Door, carried by the curse, ends the wolf at its turn's start)", not lead.alive, lead.hp)
one_death("Death's Door from a curse at the turn start", f, lead, p, after=lambda s: "death reaches for" in s.lower())

# ---- 13. a foe felled earlier in the phase reaches its turn: nothing more of it happens
reset()
p = fighter("player", "player", hp=100, max_hp=1000)
p.legendary["rampage"] = 1
e1, e2 = fighter("wolf 1", "enemy", hp=40), fighter("wolf 2", "enemy", dmg=0.001)
f = fight(p, e1, e2)
combat.add_status(f, e1, "poisoned", 3, p)
combat.take_damage(f, e1, 10 ** 7, e2, random.Random(1))         # felled earlier in the phase, by a fellow's blow
reset()
story, dump, hp0, kr = list(f.story), e1.model_dump(), p.hp, p.kill_round
combat.enemy_turn(f, e1, random.Random(2))
check("a fallen foe reaching its turn: no second fall, no rout, nobody paid", f.story == story and MORALE == [] and PAID == [],
      (f.story[len(story):], MORALE, PAID))
check("...Rampage silent, and the fallen untouched", p.hp == hp0 and p.kill_round == kr and e1.model_dump() == dump, (p.hp, hp0))

# ---- 14. a pack-bond blow inside the player's that kills: told once, paid once, to the one whose blow it was
found = None
for seed in range(200):
    reset()
    p = fighter("player", "player", dmg=0.001)
    p.legendary["packbond"] = 100
    pet, e = fighter("ally_ash", "ally", dmg=10 ** 4, name="Ash"), fighter("wolf 1", "enemy", hp=60, max_hp=60, dmg=0.001)
    f = fight(p, pet, e)
    bf.engage(f, p, e)
    combat.act_attack(f, p, e, random.Random(seed))
    if not e.alive and any("(Packbond)" in s for s in f.story):
        found = (f, pet, e, p)
        break
check("(a seed where the bond's blow kills)", found is not None)
if found:
    f, pet, e, p = found
    one_death("a pack-bond blow that kills", f, e, pet, after=lambda s: "(Packbond)" in s)
    check("...and the player's own blow, which did not kill, is not paid", p.kill_round == -9, p.kill_round)

# ---- 15. a missed blow whose riposte meets the player's thorns: the riposter dies, paid once, to the player
found = None
for seed in range(300):
    reset()
    p = fighter("player", "player", hp=4000, armor=50, always_miss=True)
    p.legendary["thorns"] = 100
    e = fighter("wolf 1", "enemy", hp=1, max_hp=50, dmg=10)
    e.legendary["riposte"] = 1
    f = fight(p, e)
    bf.engage(f, p, e)
    combat.apply_damage(f, p, e, 1.0, "attacks", random.Random(seed))
    if not e.alive:
        found = (f, p, e)
        break
check("(a seed where the riposte lands on the thorns and the riposter dies)", found is not None)
if found:
    one_death("a missed blow's riposte that met the thorns", found[0], found[2], found[1], after=lambda s: "(Thorns)" in s)


# ---- 16. a kill by a gear element's damage, with Vampiric and Rampage: the heals come in today's order, once each
def gear(seed, hp):
    p = fighter("player", "player", hp=1, max_hp=10 ** 4, dmg=20)
    p.bonuses = [combat.Bonus(modifies="fire_damage", trigger="always", magnitude=300, flat=True)]
    p.legendary.update({"vampiric": 10, "rampage": 1})
    e = fighter("wolf 1", "enemy", hp=hp, max_hp=10 ** 6, dmg=0.001)
    f = fight(p, e)
    bf.engage(f, p, e)
    combat.apply_damage(f, p, e, 1.0, "attacks", random.Random(seed))
    return f, p, e


found = None
for seed in range(100):
    reset()
    f, p, e = gear(seed, 10 ** 6)
    rec = next(iter(f.hits), None)
    if rec is None or rec.get("outcome") == "miss" or not rec.get("final") or not any("Fire damage from gear" in x[0] for x in rec["extras"]):
        continue
    reset()
    f, p, e = gear(seed, rec["final"] + 1)                    # the same blow; the fire after it is what kills
    if not e.alive:
        found = (f, p, e)
        break
check("(a seed where the gear's fire finishes what the blow began)", found is not None)
if found:
    f, p, e = found
    one_death("a kill by a gear element's damage", f, e, p, after=lambda s: "fire damage follows" in s.lower())
    vamp = [i for i, l in enumerate(f.log) if "(Vampiric)" in l]
    ramp = [i for i, l in enumerate(f.log) if "(Rampage)" in l]
    check("...the weapon drinks first, then the kill restores (Rampage), once each, as before", len(vamp) == 1 and len(ramp) == 1
          and vamp[0] < ramp[0], f.log)

# ---- 17. a family's venom kills a companion: the spider named, the dose the same as one laid with no maker
reset()
p = fighter("player", "player")
spider = fighter("spider 1", "enemy", family="venomous", behaviors={"venom": 100}, dmg=0.001)
ash, twin = fighter("ally_ash", "ally", hp=200, name="Ash"), fighter("ally_twin", "ally", hp=200, name="Twin")
f = fight(p, ash, twin, spider)
behaviors.after_hit(f, spider, ash, True, random.Random(1))
combat.add_status(f, twin, "poisoned", 3)
check("a family's venom records the one who laid it", ash.status_from.get("poisoned") == spider.id, ash.status_from)
check("...and is dosed as before: the same stack as one laid with no maker", ash.poison == twin.poison and bool(ash.poison), (ash.poison, twin.poison))
ash.hp = 1
combat.ally_turn(f, ash, random.Random(2))
check("(the venom kills Ash at her turn)", not ash.alive)
one_death("a family's venom", f, ash, spider)

# ---- 18. a poison carried on by Plaguebearer is the player's: the next foe dead of it is the player's kill
reset()
p = fighter("player", "player", dmg=10 ** 5)
p.legendary["plaguebearer"] = 1
e1, e2 = fighter("wolf 1", "enemy", hp=50, max_hp=50), fighter("wolf 2", "enemy", behaviors={"fearless": 1}, dmg=0.001)
f = fight(p, e1, e2)
bf.engage(f, p, e1)
combat.add_status(f, e1, "poisoned", 3, p)
for seed in range(40):
    if not e1.alive:
        break
    combat.apply_damage(f, p, e1, 1.0, "attacks", random.Random(seed))
check("(the first wolf falls and its poison crawls on)", not e1.alive and "poisoned" in e2.statuses, e2.statuses)
check("a poison carried on by Plaguebearer names its layer", e2.status_from.get("poisoned") == p.id, e2.status_from)
reset()
e2.hp = 1
f.round += 1
combat.start_turn(e2, f, random.Random(3))
check("(the carried poison kills the second wolf)", not e2.alive)
one_death("a poison carried on by Plaguebearer", f, e2, p)

# ---- 19. a cause dead before the death it caused: named, not paid
reset()
p, bryn, wolf = fighter("player", "player"), fighter("ally_bryn", "ally", hp=3, max_hp=60, name="Bryn", ally_role="warrior"), \
    fighter("wolf 1", "enemy", hp=40, dmg=0.001)
f = fight(p, bryn, wolf)
combat.add_status(f, bryn, "poisoned", 3, wolf)
fx.set_strength(bryn, "poisoned", [500])
combat.take_damage(f, wolf, 10 ** 7, p, random.Random(1))
reset()
kr = wolf.kill_round
combat.ally_turn(f, bryn, random.Random(2))
check("(Bryn dies of a dead wolf's poison)", not bryn.alive and not wolf.alive)
one_death("a cause dead before the death it caused", f, bryn, wolf, paid=False)
check("...the dead wolf's kill round untouched", wolf.kill_round == kr, wolf.kill_round)

# ---- 20. a companion raised and killed again falls twice
reset()
p, ash, wolf = fighter("player", "player"), fighter("ally_ash", "ally", hp=1, max_hp=60, name="Ash"), fighter("wolf 1", "enemy", dmg=40)
f = fight(p, ash, wolf)
told = []
for round_ in (1, 2):
    bf.engage(f, wolf, ash)
    for seed in range(80):
        combat.apply_damage(f, wolf, ash, 1.0, "bites", random.Random(100 * round_ + seed))
        if not ash.alive:
            break
    told.append(len(falls(f, ash)))
    check(f"(Ash is struck down, time {round_})", not ash.alive)
    check(f"...released, the field whole, time {round_}", not ash.engaged_with and bf.validate(f) == [], (ash.engaged_with, bf.validate(f)))
    ash.hp = 30                                               # raised (a Rescue, by hand)
check("a companion raised and killed again falls twice, once each time", told == [1, 2], told)
check("...each time to the wolf's blow", sum(1 for s in f.story if s.startswith("Ash falls to the first wolf's blow")) == 2, f.story)
check("(the wolf is named as the one who felled her)", f.felled_by.get(ash.id) == "the first wolf", f.felled_by)
fx.put_status(ash, "poisoned", 3)                             # raised again, then felled by a poison no one is recorded laying
fx.set_strength(ash, "poisoned", [500])
combat.ally_turn(f, ash, random.Random(7))
check("(Ash falls a third time, to the poison)", not ash.alive and len(falls(f, ash)) == 3, f.story[-3:])
check("...and the wolf is no longer named for a death that was not its doing", ash.id not in f.felled_by, f.felled_by)

# ---- 21. the stage check: a path that writes health names the fall straight after it, and no other stage writes health unfallen
import pathlib
import yaml
import purity
from engine import damage as DMG
ST = yaml.safe_load(open("data/rules/stages.yaml", encoding="utf-8"))
check("the declared paths pass the stage check", data_check.tables_problems() == [], data_check.tables_problems())
for path in ("blow", "dot_tick", "tear"):
    gone = copy.deepcopy(ST)
    gone["damage"][path] = [s for s in gone["damage"][path] if s != "fall"]
    probs = data_check.tables_problems(ST=gone)
    check(f"...and refuse a {path} path whose health stage is not followed by the fall", any("fall" in x and f"damage.{path}" in x for x in probs), probs)
fence = getattr(purity, "unfallen_hp_writes_in", None)
src = pathlib.Path("engine/damage.py").read_text(encoding="utf-8")
HEALTH, FLOORS = getattr(DMG, "HEALTH", ()), getattr(DMG, "FLOORS", ())
check("every stage that writes health is a health stage, a floor that leaves one standing, or calls the fall step",
      fence is not None and fence(src, DMG.STAGES, HEALTH, FLOORS) == [], fence(src, DMG.STAGES, HEALTH, FLOORS) if fence else "no fence")
check("...the health stages and floors it names are stages", bool(HEALTH) and set(HEALTH) | set(FLOORS) <= set(DMG.STAGES), (HEALTH, FLOORS))
if fence:
    planted = ("def outright(b):\n    b.dfn.hp = 0\n    return True\n\n\ndef held(b):\n    b.dfn.hp = 0\n    return False\n\n\n"
               "def ended(b):\n    b.dfn.hp = 0\n    fall_step(b.combat, b.dfn, b.source)\n    return True\n\n\n"
               "def wide(b):\n    b.dfn.hp, b.dfn.mana = b.dfn.max_hp, 0\n    return False\n")
    check("...a planted stage that writes health with no fall is caught, and a floor that writes zero; the rest pass",
          fence(planted, {"outright", "held", "ended", "wide"}, (), ("held", "wide"))
          == ["outright writes .hp with no fall", "held, a floor, may write .hp to zero"],
          fence(planted, {"outright", "held", "ended", "wide"}, (), ("held", "wide")))

# ---- 21b. a ticking status is told in its own words, from data, and the check refuses one without them
CB = yaml.safe_load(open("data/rules/combat.yaml", encoding="utf-8"))
TICKS = CB.get("ticks") or {}
check("every status that ticks has the words a death by it is told in", sorted(TICKS) == ["burning", "poisoned"]
      and all(r.get("laid") and r.get("nobody") for r in TICKS.values()), TICKS)
bare = copy.deepcopy(CB)
bare.setdefault("ticks", {})["poisoned"] = {"laid": "{whose} poison - does its work"}
probs = data_check.tables_problems(CB=bare)
check("...and the check refuses a ticking status with a word missing, or a dash", any("ticks.poisoned.nobody" in x for x in probs)
      and any("ticks.poisoned.laid" in x and "dash" in x for x in probs), probs)
bare["ticks"]["festering"] = {"laid": "{whose} rot does its work", "nobody": "the rot does its work"}
check("...or one that is no status with a tick of its own", any("ticks.festering" in x for x in data_check.tables_problems(CB=bare)),
      data_check.tables_problems(CB=bare))
try:
    getattr(DMG, "fall_line")(fighter("ally_x", "ally", name="X"), None, "tick", "festering")
    loud = False
except KeyError:
    loud = True
except AttributeError:
    loud = False
check("...and a tick the data does not know is refused out loud, never told as a poison", loud)

# ---- 22. the blow in progress is held on the fight, never in its row
reset()
p, e = fighter("player", "player", dmg=10 ** 5), fighter("wolf 1", "enemy", hp=30)
f = fight(p, e)
bf.engage(f, p, e)
PEEK["on"] = True
for seed in range(40):
    if not e.alive:
        break
    PEEK["on"] = True
    combat.apply_damage(f, p, e, 1.0, "attacks", random.Random(seed))
held = PEEK.get("open") or []
check("mid-blow, the fight holds the blow in progress: its striker and its target", len(held) == 1 and held[0].att is p and held[0].dfn is e,
      held)
check("...and its row does not", "_open" not in (PEEK.get("dump") or {"_open": 1}) and "_open" not in (PEEK.get("json") or "_open")
      and getattr(combat.Combat.model_validate(PEEK["dump"]), "_open", None) == [] if PEEK.get("dump") else False)
check("...and nothing is held once the blow is done", getattr(f, "_open", None) == [], getattr(f, "_open", None))

# ---- 23. what must not move: an ordinary killing blow draws the blow's die as before, and a tick death routs as before
class Counted(random.Random):
    """A die that counts its draws."""
    def __init__(self, seed):
        self.n = 0
        super().__init__(seed)

    def random(self):
        self.n += 1
        return super().random()

    def getrandbits(self, k):
        self.n += 1
        return super().getrandbits(k)


draws, broke = [], []
for seed in range(30):
    reset()
    p = fighter("player", "player", dmg=10 ** 5)
    chief = fighter("chief", "enemy", hp=50, level=8, dmg=0.001)
    gobs = [fighter(f"goblin {i}", "enemy", level=2, dmg=0.001) for i in (1, 2, 3)]
    f = fight(p, chief, *gobs)
    bf.engage(f, p, chief)
    rng = Counted(seed)
    rng.n = 0
    combat.apply_damage(f, p, chief, 1.0, "attacks", rng, can_cleave=False)
    draws.append(rng.n)
    broke.append("".join("1" if g.fled else "0" for g in gobs))
DRAWS = [5, 1, 5, 1, 1, 5, 5, 5, 1, 5, 5, 5, 5, 5, 1, 5, 5, 5, 1, 5, 5, 1, 5, 5, 5, 5, 5, 5, 1, 5]     # (f768) measured before the fall step
BROKE = ["110", "000", "110", "000", "000", "000", "111", "010", "000", "101", "010", "010", "011", "001", "000", "010", "111", "010",
         "000", "001", "001", "000", "101", "010", "101", "010", "101", "011", "000", "010"]
check("an ordinary killing blow draws the blow's die as before, draw for draw", draws == DRAWS, draws)
check("...and routs the same goblins", broke == BROKE, broke)

routs = []
for seed in range(30):
    reset()
    p = fighter("player", "player")
    lead = fighter("wolf 1", "enemy", hp=5, max_hp=40, level=6, rank="elite", dmg=0.001)
    pack = [fighter(f"wolf {i}", "enemy", level=3, dmg=0.001) for i in (2, 3, 4)]
    f = fight(p, lead, *pack, serial=f"t{seed}")
    f.round = 2
    combat.add_status(f, lead, "poisoned", 3, p)
    fx.set_strength(lead, "poisoned", [500])
    combat.start_turn(lead, f, random.Random(seed))
    routs.append("".join("1" if w.fled else "0" for w in pack))
ROUTS = ["111", "001", "011", "100", "110", "101", "101", "100", "001", "100", "101", "010", "000", "110", "111", "010", "010", "100",
         "101", "101", "011", "100", "111", "101", "100", "101", "000", "010", "101", "001"]     # (f768) measured before the fall step
check("a foe's tick death routs the same foes as before (its keyed die)", routs == ROUTS, routs)

behaviors.morale_on_death, combat_perks.on_kill, combat_perks.after_hit, summons.on_fall = _morale, _on_kill, _after_hit, _on_fall

# ---- 24. the hires' lines, and the player's own round, for a death that was no blow on them
from engine import quirks
from scenes import combat_scene as cs
from scenes.combat_scene import CombatScene
from services.fight import RoundIntent
from ui import console
console.put("combat_state", lambda data: False)
console.put("combat_panel", lambda lines: None)
NAME = "fall_once_768"
game = simlib.campaign(NAME, cls="warrior", seed=7, location="parth")
ws = game.scene
odly = {"id": "h1", "name": "Odly Garth", "role": "fighter", "level": 2, "permanent": True, "rank": "F", "bond": 12, "pronoun": "she",
        "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "a sellsword with a dented shield"}
thav = {"id": "h2", "name": "Thavathiel Liaralor", "role": "mage", "level": 2, "permanent": True, "rank": "F", "bond": 12, "pronoun": "he",
        "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "an elf who talks of ley lines"}
for i, m in enumerate((odly, thav)):
    quirks.roll(m, random.Random(i))
ws.player.party = [odly, thav]
ws.player.party_mode = "with"
ws.enter("parth")
creature = ws.world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 3, "normal", "e1", name="wolf 1")
foe.hp = foe.max_hp = 10 ** 6
foe.behaviors["fearless"] = 1
ws.narrate_with = lambda *a, **k: None
sc = CombatScene.begin(ws, creature, [foe], "It is on you:")
ws.combat = sc
f = sc.fight
f.story.clear()
for m in (odly, thav):
    a = f.get(f"ally_{m['id']}")
    combat.add_status(f, a, "poisoned", 3, foe)
    fx.set_strength(a, "poisoned", [10 ** 4])
    a.hp = 1
    combat.start_turn(a, f, random.Random(5))
check("(both hires die of the wolf's poison at their turn)", not f.get("ally_h1").alive and not f.get("ally_h2").alive)
svc_cls = type(ws.party_service)
real_decide = svc_cls.decide_down
fate = {"h1": "carried", "h2": "dead"}
svc_cls.decide_down = lambda self, m, rng, in_fight=True: (m.__setitem__("down_fate", fate[m["id"]]), fate[m["id"]])[1]
f.story.clear()
try:
    sc.hires_down()
finally:
    svc_cls.decide_down = real_decide
dead = [s for s in f.story if s.startswith("Thavathiel Liaralor")]
down = [s for s in f.story if s.startswith("Odly Garth")]
check("a hire dead of poison: told dead, by the wolf, and never by a blow",
      dead == ["Thavathiel Liaralor does not get up again: Thavathiel Liaralor is dead (killed by the first wolf, not by you)"], dead)
check("...and one down alive from it: told down, never 'hard', never by a blow",
      down == ["Odly Garth goes down and lies still: alive, but out of the fight, and she will have to be carried"], down)

p = f.player
p.hp = 1
combat.add_status(f, p, "poisoned", 3, foe)
fx.set_strength(p, "poisoned", [10 ** 4])
f.story.clear()
svc = cs.service_of(ws)
streams.begin(ws.store.meta.seed, 50, "I attack the wolf.")
with ws.operation("test:round", "I attack the wolf."):
    svc.round(f, RoundIntent(kind="attack", target="e1", words="I attack the wolf."))
check("the player dead of a tick at their turn: told once, as the wolf's poison", not p.alive and len(falls(f, p)) == 1
      and "The first wolf's poison does its work. You fall, and the world goes dark" in f.story, f.story)
check("...never 'your body will not answer', which is for the living", not any("will not answer" in s for s in f.story), f.story)
check("...and the fight is lost", f.over == "defeat", f.over)

# ---- 25. a Phoenix that turns the death aside tells it as it came: no blow for a poison, the blow for a blow
from engine import items
c = ws.player.character
ph = items.make("amulet", "legendary", 40, rng=random.Random(2))
ph.legendary_effect = "phoenix"
c.equipment["neck"] = ph
NARR = []
ws.narrate = lambda t, *a, **k: NARR.append(t)


def phoenix_told() -> tuple[list, list]:
    """What the Phoenix's saving tells the player and the narrator, a fresh use each time."""
    c.phoenix_day = -10 ** 6
    SHOWN.clear()
    NARR.clear()
    saved = sc.phoenix()
    return ([t for k, t in SHOWN if k == "note"] if saved else None), list(NARR)


notes, passages = phoenix_told()
check("a Phoenix turning aside the player's death by poison speaks of no blow",
      notes == ["The last of your strength gives out, and " + items.display_name(ph) + " burns white. You rise from the ashes at half "
                "strength, and the fight is over. (It can't do this again for " + f"{items.LEGENDARY['phoenix'].value:g}" + " days.)"]
      and passages == ["The last of the player's strength gives out, but their Phoenix relic flares and refuses the death. They "
                       "stagger up, alive, the enemies recoiling or gone."], (notes, passages))
p.hp = 10                                                       # raised, then struck down by the wolf's bite
for seed in range(80):
    combat.apply_damage(f, foe, p, 1.0, "bites", random.Random(seed))
    if not p.alive:
        break
check("(the player falls to the wolf's bite)", not p.alive and "fell_to" not in p.counters, p.counters.get("fell_to"))
notes, passages = phoenix_told()
check("...and one turning aside a killing blow keeps the blow", bool(notes) and notes[0].startswith("The killing blow lands, and ")
      and passages and passages[0].startswith("A killing blow falls on the player"), (notes, passages))
ws.combat = None
game.close()

check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
