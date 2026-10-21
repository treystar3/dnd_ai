"""Movement abilities (f223, engine/movement.py): the four everyday moves and seven signatures. Each only moves - no damage, no
effect - is used alongside the turn's action (Shield Ally and Rally to Me take the whole turn), one a turn, and a movement that cannot
do its job costs nothing. The planner offers everyday moves by family lean and one signature to a class whose family has one."""
import random
import sys
import types
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import ability_slots, battlefield as bf, combat, movement, summons
from engine.battlefield import Battlefield, BattleZone, BattleEdge
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

K = movement.KINDS


def F(fid, side, hp=300, reach="melee", **kw):
    return combat.Fighter(id=fid, name=fid, side=side, level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
                          stamina=10**5, max_stamina=10**5, mana=10**5, max_mana=10**5, weapon_damage=10, reach=reach,
                          behaviors={"fearless": 1}, **kw)

def field(two=True):
    zones = {"z1": BattleZone(id="z1", name="the road", tags=["open"])}
    edges = []
    if two:
        zones["z2"] = BattleZone(id="z2", name="the rise", tags=["elevated", "difficult"])
        edges.append(BattleEdge(a="z1", b="z2", tags=["climb"]))
    return Battlefield(zones=zones, edges=edges, start="z1")

def fight(*fs, two=True):
    f = combat.Combat(fighters=list(fs), record=False)
    f.battlefield = field(two)
    bf.place_fighters(f)
    return f

def mv(kind):
    return Move(id=kind, name=kind.replace("_", " ").title(), effect="mobility", tier="light", reach="self", resource="stamina",
                movement=kind, cooldown=K[kind]["cooldown"])

rng = random.Random(4)

# ---- the data: every kind priced and described
check("four everyday moves and seven signatures", sorted(movement.EVERYDAY) == ["breach", "relentless_advance", "shield_ally", "shift"]
      and sorted(movement.SIGNATURES) == ["bloodscent", "grave_step", "malefic_step", "rally_to_me", "shadowmark", "soul_swap", "vengeance_leap"])
check("everyday cooldowns are 3-4, signatures 5-6", all(3 <= K[k]["cooldown"] <= 4 for k in movement.EVERYDAY)
      and all(5 <= K[k]["cooldown"] <= 6 for k in movement.SIGNATURES))
check("only Shield Ally and Rally to Me take the whole turn", sorted(k for k in K if K[k].get("whole_turn")) == ["rally_to_me", "shield_ally"])
check("every card says what it does and when to use it", all(K[k]["does"] and K[k]["when"] for k in K))

# ---- Breach: past a holding line on its own
p, guard, archer = F("player", "player", hold=1), F("g", "enemy", hold=1), F("arch", "enemy", reach="ranged")
f = fight(p, guard, archer)
bf.engage(f, p, guard)
check("the archer is protected behind its guard", bf.protected(f, archer) and not bf.attack_access(f, p, archer).ok)
hp = p.hp
why = combat.act_ability(f, p, mv("breach"), archer, rng)
check("Breach gets past the holding guard and onto the archer", why is None and bf.engaged_pair(p, archer) and bf.attack_access(f, p, archer).ok, why)
check("...without a blow taken or dealt", p.hp == hp and archer.hp == archer.max_hp)
check("...and it rides alongside the action, not replacing it", not movement.whole_turn(mv("breach")))
p2, g2, a2 = F("player", "player"), F("g", "enemy"), F("arch", "enemy")
f2 = fight(p2, g2, a2)
why = combat.act_ability(f2, p2, mv("breach"), a2, rng)
check("Breach on an unguarded enemy is refused and costs nothing", why and "not behind any guard" in why and p2.stamina == p2.max_stamina, why)

# ---- Shift: free of the press; switch only to someone already reachable; never past a line
p, e1, e2 = F("player", "player"), F("e1", "enemy"), F("e2", "enemy")
f = fight(p, e1, e2, two=False)
bf.engage(f, p, e1)
hp = p.hp
combat.act_ability(f, p, mv("shift"), e2, rng)
check("Shift pulls free with no parting blow and turns on a different enemy", p.hp == hp and bf.engaged_pair(p, e2) and not bf.engaged_pair(p, e1))
p, guard, archer, brute = F("player", "player"), F("g", "enemy", hold=1), F("arch", "enemy", reach="ranged"), F("brute", "enemy", hold=1)
f = fight(p, guard, archer, brute, two=False)
bf.engage(f, p, guard)
combat.act_ability(f, p, mv("shift"), archer, rng)
check("Shift cannot reach a guarded backliner - that is Breach's work", not bf.engaged_pair(p, archer), p.engaged_with)
p, e1 = F("player", "player"), F("e1", "enemy")
f = fight(p, e1)
bf.engage(f, p, e1)
p.counters["shift_back"] = 1
combat.act_ability(f, p, mv("shift"), e1, rng)
check("Shift's fall-back mode steps away to safety", not p.engaged_with and (p.zone_id != e1.zone_id or p.row == "back"), (p.zone_id, p.row))

# ---- Shield Ally: whole turn, takes over up to your hold of the enemies on them, covers them
for hold, want in ((2, 2), (1, 1), (0, 1)):
    p, ally = F("player", "player", hold=hold), F("ally_t", "ally")
    foes = [F(f"e{i}", "enemy") for i in range(3)]
    f = fight(p, ally, *foes, two=False)
    for e in foes:
        bf.engage(f, ally, e)
    combat.act_ability(f, p, mv("shield_ally"), None, rng, give=[ally])
    took = [e for e in foes if bf.engaged_pair(p, e)]
    check(f"Shield Ally with hold {hold} takes over {want} of the enemies on the ally", len(took) == want and p.covering == ally.id, (len(took), p.covering))

# ---- Relentless Advance: heavy armor, climbs and slowed are no bar; grapple and the line still are
p, e = F("player", "player", pace="slow"), F("e1", "enemy")
f = fight(p, e)
bf.enter_zone(f, e, "z2")
p.statuses["slowed"] = 2
why = combat.act_ability(f, p, mv("relentless_advance"), e, rng)
check("Relentless Advance carries a slowed, heavy-armored fighter up the climb and onto the enemy", why is None and bf.engaged_pair(p, e), why)
p, e = F("player", "player"), F("e1", "enemy")
f = fight(p, e)
bf.enter_zone(f, e, "z2")
p.statuses["grappled"] = 2
why = combat.act_ability(f, p, mv("relentless_advance"), e, rng)
check("...but not out of a grapple", why and "grapple" in why and p.zone_id == "z1", why)

# ---- one movement a turn
p, e1, e2 = F("player", "player"), F("e1", "enemy"), F("e2", "enemy")
f = fight(p, e1, e2, two=False)
bf.engage(f, p, e1)
combat.act_ability(f, p, mv("shift"), e2, rng)
bf.engage(f, p, e1)
why = combat.act_ability(f, p, Move(id="s2", name="Again", effect="mobility", tier="light", reach="self", resource="stamina", movement="shift", cooldown=3), e2, rng)
check("only one movement ability a turn", why and "already used a movement" in why, why)

# ---- Shadowmark: vanish, hidden, return on recast or after three turns; cooldown only on return
p, ally, e = F("player", "player"), F("ally_t", "ally"), F("e1", "enemy")
f = fight(p, ally, e, two=False)
bf.engage(f, p, e)
sm = mv("shadowmark")
combat.act_ability(f, p, sm, None, rng)
check("Shadowmark: free of the fight, hidden, shadow left, no cooldown yet", not p.engaged_with and "concealed" in p.position_tags
      and p.shadow and "shadowmark" not in p.cooldowns, (p.engaged_with, p.position_tags, p.cooldowns))
hits_on_me = 0
for s_ in range(30):
    p2, ally2, e2 = F("player", "player"), F("ally_t", "ally", hp=10**6), F("e1", "enemy")
    f2 = fight(p2, ally2, e2, two=False)
    bf.gain(p2, "concealed")
    hp = p2.hp
    combat.enemy_turn(f2, e2, random.Random(s_))
    hits_on_me += p2.hp < hp
check("while hidden, enemies go for someone else", hits_on_me == 0, hits_on_me)
p3, e3 = F("player", "player"), F("e1", "enemy")
f3 = fight(p3, e3, two=False)
bf.engage(f3, p3, e3)
combat.act_ability(f3, p3, mv("shadowmark"), None, rng)
hp = p3.hp
for s_ in range(10):
    combat.enemy_turn(f3, e3, random.Random(s_))
check("alone, the vanish buys a clean turn: nobody can find you", p3.hp == hp, p3.hp)
f3.round += 1
for s_ in range(20):
    combat.enemy_turn(f3, e3, random.Random(s_))
check("...after your next turn, an enemy beside you finds you again", p3.hp < hp)
archer = F("arch", "enemy", reach="ranged")
f.fighters.append(archer); archer.zone_id, archer.row = "z1", "back"
f.battlefield.zones["z2"] = BattleZone(id="z2", name="the far side")
f.battlefield.edges.append(BattleEdge(a="z1", b="z2"))
bf.enter_zone(f, archer, "z2")
check("a hidden fighter cannot be shot from elsewhere", not bf.attack_access(f, archer, p).ok)
start = (p.shadow["zone"], p.shadow["row"])
combat.act_attack(f, p, e, rng)
check("your first attack reveals you", "concealed" not in p.position_tags)
f.round += 1
combat.act_ability(f, p, sm, None, rng)
check("recasting returns you to your shadow and starts the cooldown", not p.shadow and (p.zone_id, p.row) == start and p.cooldowns.get("shadowmark", 0) > 0,
      (p.shadow, p.zone_id, p.cooldowns))
p, e = F("player", "player"), F("e1", "enemy")
f = fight(p, e, two=False)
combat.act_ability(f, p, mv("shadowmark"), None, rng)
for r in range(movement.M["shadow_turns"]):
    f.round += 1
    combat.start_turn(p, f)
check("without a recast, the shadow pulls you back after three turns", not p.shadow and p.cooldowns.get("shadowmark", 0) > 0)

# ---- Malefic Step: to an enemy carrying your curse
p, guard, caster = F("player", "player"), F("g", "enemy", hold=1), F("c", "enemy", reach="ranged")
f = fight(p, guard, caster, two=False)
why = combat.act_ability(f, p, mv("malefic_step"), caster, rng)
check("Malefic Step needs your curse on someone", why and "curses" in why, why)
combat.add_status(f, caster, "hexed", 3, p)
check("an affliction remembers who put it there", caster.status_from.get("hexed") == p.id)
combat.act_ability(f, p, mv("malefic_step"), caster, rng)
check("...then it lands you beside the cursed caster, past its guard", bf.engaged_pair(p, caster))

# ---- Grave Step: out of a fallen body
p, dead, e = F("player", "player"), F("d", "enemy"), F("e1", "enemy")
f = fight(p, dead, e)
bf.enter_zone(f, dead, "z2"); bf.enter_zone(f, e, "z2")
why = combat.act_ability(f, p, mv("grave_step"), e, rng)
check("Grave Step needs a body", why and "no body" in why, why)
dead.hp = 0
combat.act_ability(f, p, mv("grave_step"), e, rng)
check("...then you step out of it, beside your target", p.zone_id == "z2" and bf.engaged_pair(p, e))

# ---- Soul Swap: trade places with your summon, and its fights
p, e = F("player", "player"), F("e1", "enemy")
f = fight(p, e)
bf.engage(f, p, e)
s = F("summon_x", "ally"); s.summon_form, s.summon_owner = "bound", "player"
f.fighters.append(s); bf.place_fighters(f); bf.enter_zone(f, s, "z2")
combat.act_ability(f, p, mv("soul_swap"), e, rng)
check("Soul Swap trades places, and the summon takes over your fight", p.zone_id == "z2" and s.zone_id == "z1" and bf.engaged_pair(s, e))

# ---- Bloodscent: the most wounded, below half; fails when none
p, a, b = F("player", "player"), F("a", "enemy"), F("b", "enemy")
f = fight(p, a, b)
bf.enter_zone(f, b, "z2")
why = combat.act_ability(f, p, mv("bloodscent"), a, rng)
check("Bloodscent fails when no enemy is below half health", why and "half health" in why, why)
a.hp, b.hp = a.max_hp * 0.45, b.max_hp * 0.2
f.round += 1
combat.act_ability(f, p, mv("bloodscent"), a, rng)
check("...and leaps to the most wounded one, wherever it is", bf.engaged_pair(p, b) and p.zone_id == "z2")

# ---- Vengeance Leap: to whoever last hurt you
p, e, archer = F("player", "player"), F("e1", "enemy"), F("arch", "enemy", reach="ranged")
f = fight(p, e, archer)
bf.enter_zone(f, archer, "z2")
combat.take_damage(f, p, 5, archer, rng)
check("taking a hit remembers who dealt it", p.last_hurt_by == archer.id)
combat.act_ability(f, p, mv("vengeance_leap"), e, rng)
check("Vengeance Leap lands you on the one who hurt you", bf.engaged_pair(p, archer))

# ---- Rally to Me: every ally to your side, free
p, a1, a2, e = F("player", "player"), F("ally_a", "ally"), F("ally_b", "ally"), F("e1", "enemy")
f = fight(p, a1, a2, e)
bf.engage(f, a1, e); bf.enter_zone(f, a2, "z2")
p.hp = 300
combat.act_ability(f, p, mv("rally_to_me"), None, rng)
check("Rally to Me brings every ally to your side, free of the fight", a1.zone_id == a2.zone_id == p.zone_id and not a1.engaged_with)

# ---- nothing here deals damage
check("no movement kind carries a strike", not any("strike" in K[k] for k in K))

# ---- the planner
def interp(fams, summoner=False):
    return types.SimpleNamespace(archetype=types.SimpleNamespace(value="warrior"), families=fams, focus="balanced", uses_companions=False,
                                 summoner=summoner, custom_class="X", combat_identity="", summary="", themes=[], primary_attributes=["strength"],
                                 casting_attribute="", elements=[], constraints=[])
from engine import ability_traits
from collections import Counter
sig, every = Counter(), Counter()
for sd in range(40):
    i = interp(["warrior", "berserker"])
    sl = ability_slots.plan(i, ability_traits.draw_offers(i, random.Random(sd), min_functions=5), 5, random.Random(sd))
    mob = [s for s in sl if s["effect"] == "mobility"]
    sig.update(s["movement"] for s in mob if s["movement"] in movement.SIGNATURES)
    every.update(s["movement"] for s in mob if s["movement"] in movement.EVERYDAY)
    if sd == 0:
        check("every movement slot has a kind and a light tier", mob and all(s["movement"] and s["tier"] == "light" for s in mob))
        check("the model is told it is only movement", all("only movement" in ability_slots.mechanic_text(s) for s in mob))
check("a warrior-berserker gets exactly one signature, from its families", sum(sig.values()) == 40 and set(sig) <= {"bloodscent", "vengeance_leap"}, sig)
check("...and everyday moves leaning toward its families", every.most_common(1)[0][0] in ("relentless_advance", "breach"), every)
none = 0
for sd in range(20):
    i = interp(["mage"])
    sl = ability_slots.plan(i, ability_traits.draw_offers(i, random.Random(sd), min_functions=5), 5, random.Random(sd))
    none += any(s["movement"] in movement.SIGNATURES for s in sl if s["effect"] == "mobility")
check("a mage (no signature in its family) gets none", none == 0, none)
check("Soul Swap is only for a class that summons", "soul_swap" not in movement.signatures_for(["summoner"], False)
      and "soul_swap" in movement.signatures_for(["summoner"], True))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
