"""Creation perks, round two (f217): each rule run through its loop twice where it has one - the plate that cannot be moved, the
headsman's chain, blood that makes the heavy sure, judgement for a wounded ally, the press of many, the step into shadow, the venom
that waits, the quarry, stillness for the archer and the caster, the hunter's high ground, rust, the attuned weapon, withering, the
blood-called spirit, the familiar's eyes, feral form, arcane precision, frost that runs backward, frozen ground, triage, the
coordinated strike, the rhythm of mending, the sanctuary, the twin blessing, the selfless one, shared strength and the turncoat;
and single-target blessings. Numbers from data/rules/perks.yaml."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import battlefield as bf, battlefield_builder as bb, behaviors, combat, combat_perks as perks
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

P = perks.P


def player(*mechs, moves=(), hp=400, stam=200, mana=200, attrs=14, dmg=10, **kw):
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: attrs for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, stamina=stam, max_stamina=stam, mana=mana, max_mana=mana, weapon_damage=dmg, hold=1,
                          legendary={m: v for m, v in (x if isinstance(x, tuple) else (x, 1) for x in mechs)},
                          mech_names={(x[0] if isinstance(x, tuple) else x): (x[0] if isinstance(x, tuple) else x).replace("_", " ").title() for x in mechs},
                          moves=list(moves), **kw)

def foe(i, hp=10**6, category="hostile people", level=5, dmg=8, **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=level, attrs={a: 10 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, weapon_damage=dmg, category=category, behaviors={"fearless": 1}, **kw)

def ally(hp=200, fid="ally_h", name="Tam"):
    return combat.Fighter(id=fid, name=name, side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, weapon_damage=8, ally_role="fighter", hold=1)

def spirit(hp=100):
    """The player's Bound summon (f222: summons are made, never companions)."""
    f = combat.Fighter(id="ally_spirit", name="the spirit", side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                       hp=hp, max_hp=hp, weapon_damage=8, hold=1)
    f.summon_form, f.summon_owner, f.summon_tier = "bound", "player", "light"
    return f

def fight(*fs, field=None):
    f = combat.Combat(fighters=list(fs), record=False)
    f.battlefield = field or bb.duel_ground()
    bf.place_fighters(f)
    return f

def spell(mid, element="", tier="light", effect="damage", reach="ranged", **kw):
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=effect, tier=tier, reach=reach, resource="mana",
                attribute="intelligence", element=element, **kw)

def skill(mid, tier="light", effect="damage", reach="melee", **kw):
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=effect, tier=tier, reach=reach, resource="stamina", **kw)

def outcomes(f, att, dfn, n=400, seed=0, **counters):
    """Run on_outcome over real rolls, forcing the counters the perk reads; returns the outcome counts."""
    out = {"miss": 0, "graze": 0, "hit": 0, "crit": 0}
    for s in range(n):
        for k, v in counters.items():
            att.counters[k] = v
        o, _ = combat.roll_attack(att, dfn, f, random.Random(seed + s))
        out[perks.on_outcome(f, att, dfn, o, None)] += 1
    return out

rng = random.Random(7)

# ---- Juggernaut: plate that cannot be moved, and that holds what it is engaged with
for n in (1, 2):
    p = player("juggernaut", armor_weight="heavy")
    f = fight(p, foe(1))
    e = f.get("e1")
    took = combat.add_status(f, p, ("prone", "grappled")[n - 1], 1, e)
    check(f"juggernaut {n}: {('prone', 'grappled')[n - 1]} does not take", not took and ("prone", "grappled")[n - 1] not in p.statuses)
    bf.engage(f, p, e)
    check(f"juggernaut {n}: what it is engaged with cannot step away", perks.held_fast(f, e))
p = player("juggernaut", armor_weight="medium")
f = fight(p, foe(1))
check("juggernaut: without heavy armor, no", combat.add_status(f, p, "prone", 1, f.get("e1")))

# ---- Headsman: a heavy that kills makes the next heavy free
cleaver = skill("cleaver", tier="heavy")
for n in (1, 2):
    p = player("headsman", moves=[cleaver], dmg=10**5)
    f = fight(p, foe(1, hp=1), foe(2, hp=10**6))
    before = p.stamina
    while f.get("e1").alive:
        combat.act_ability(f, p, cleaver, f.get("e1"), random.Random(n * 100 + p.stamina))
    first = before - p.stamina
    mid = p.stamina
    combat.act_ability(f, p, cleaver, f.get("e2"), rng)
    check(f"headsman {n}: the kill paid for the next heavy", first > 0 and p.stamina >= mid, (first, mid, p.stamina))

# ---- Blood for Blood: bleeding, the heavy cannot miss
for n in (1, 2):
    p = player("blood_for_blood", attrs=1)
    f = fight(p, foe(1, level=30))
    p.statuses["bleeding"] = 3
    res = outcomes(f, p, f.get("e1"), seed=n * 1000, tier_now=3)
    check(f"blood for blood {n}: bleeding, a heavy never misses", res["miss"] == 0, res)
p = player("blood_for_blood", attrs=1)
f = fight(p, foe(1, level=30))
check("blood for blood: not bleeding, it can", outcomes(f, p, f.get("e1"), tier_now=3)["miss"] > 0)

# ---- Judgement: an enemy that hurt an ally last round cannot be missed
for n in (1, 2):
    p = player("judgement", attrs=1)
    t = ally()
    f = fight(p, t, foe(1, level=30))
    e = f.get("e1")
    f.round = 4
    combat.take_damage(f, t, 5, e, rng)
    f.round = 4 + (n - 1)
    check(f"judgement {n}: it hurt Tam, and the blow cannot miss", outcomes(f, p, e, seed=n * 50)["miss"] == 0)
f.round = 7
check("judgement: two rounds on, the anger has cooled", outcomes(f, p, e, seed=99)["miss"] > 0)

# ---- Thick of It: heavier with each enemy pressing in
for n, k in ((1, 2), (2, 3)):
    p = player(("thick_of_it", 15))
    foes = [foe(i) for i in range(1, k + 1)]
    f = fight(p, *foes)
    for e in foes:
        bf.engage(f, p, e)
    m = perks.damage_mult(f, p, foes[0], 1.0, None)
    check(f"thick of it {n}: {k} on you, {1 + 0.15 * (k - 1):.2f}x", abs(m - (1 + 0.15 * (k - 1))) < 1e-6, m)

# ---- Shadowstep: a kill slips you into cover, only where there is cover
brush = bb.Battlefield(zones={"z1": bb.BattleZone(id="z1", name="the thicket", tags=["concealed"])}, start="z1")
for n in (1, 2):
    p = player("shadowstep", dmg=10**5)
    f = fight(p, foe(1, hp=1), foe(2), field=brush.model_copy(deep=True))
    p.position_tags = []
    while f.get("e1").alive:
        combat.act_attack(f, p, f.get("e1"), random.Random(n * 7 + len(f.log)))
    check(f"shadowstep {n}: the kill and the vanishing", "concealed" in p.position_tags)
p = player("shadowstep", dmg=10**5)
f = fight(p, foe(1, hp=1), foe(2))
while f.get("e1").alive:
    combat.act_attack(f, p, f.get("e1"), random.Random(len(f.log)))
check("shadowstep: on open ground, nowhere to go", "concealed" not in p.position_tags)

# ---- Dormant Venom: the poison gathers, and a crit spends it
for n in (1, 2):
    p = player("dormant_venom")
    f = fight(p, foe(1, hp=10000))
    e = f.get("e1")
    combat.add_status(f, e, "poisoned", 3, p)
    hp0 = e.hp
    combat.start_turn(e, f)
    combat.start_turn(e, f)
    check(f"dormant venom {n}: no ticks, but it builds", e.hp == hp0 and e.counters.get("venom_store", 0) > 0, (e.hp, e.counters))
    store = e.counters["venom_store"]
    perks.after_hit(f, p, e, "crit", 10, rng)
    check(f"dormant venom {n}: the crit spends it all", e.hp < hp0 and not e.counters.get("venom_store") and "poisoned" not in e.statuses)

# ---- Quarry: the first enemy struck cannot hide, cannot slip away, and is never grazed; the mark moves on
for n in (1, 2):
    p = player("quarry", attrs=1)
    f = fight(p, foe(1, level=12), foe(2, level=12))
    e1, e2 = f.get("e1"), f.get("e2")
    res = outcomes(f, p, e1, seed=n * 300)
    check(f"quarry {n}: never grazed", res["graze"] == 0 and res["hit"] > 0, res)
    check(f"quarry {n}: it cannot slip away", perks.held_fast(f, e1) and not perks.held_fast(f, e2))
    e1.position_tags = ["concealed"]
    perks.on_turn_start(f, p)
    check(f"quarry {n}: and cannot hide", "concealed" not in e1.position_tags)
    e1.hp = 0
    perks.on_outcome(f, p, e2, "hit", None)
    check(f"quarry {n}: when it falls, the next one struck is the quarry", perks.QUARRY.get(id(f)) == "e2")

# ---- Steady Aim: a round without moving, and the next ranged blow cannot miss; then it must steady again
for n in (1, 2):
    p = player("steady_aim", attrs=1, reach="ranged")
    f = fight(p, foe(1, level=30))
    f.round, p.move_round = 5, 3
    e = f.get("e1")
    o, _ = combat.roll_attack(p, e, f, random.Random(1))
    misses = 0
    for s in range(200):
        p.counters.pop("steady_round", None)
        if perks.on_outcome(f, p, e, "miss", None) == "miss":
            misses += 1
    check(f"steady aim {n}: steadied, the shot is true", misses == 0)
    first = perks.on_outcome(f, p, e, "miss", None)
    check(f"steady aim {n}: spent, it must steady again", first == "miss")
p = player("steady_aim", reach="ranged")
f = fight(p, foe(1))
f.round, p.move_round = 5, 5
check("steady aim: having moved, nothing", perks.on_outcome(f, p, f.get("e1"), "miss", None) == "miss")

# ---- High Ground Hunter: from high ground, cover does not count, and the target is pinned
cover_field = bb.Battlefield(zones={"z1": bb.BattleZone(id="z1", name="the ridge", tags=["elevated"]),
                                    "z2": bb.BattleZone(id="z2", name="the wall", tags=["cover"])},
                             edges=[bb.BattleEdge(a="z1", b="z2")], start="z1")
for n in (1, 2):
    p = player("high_ground_hunter", reach="ranged")
    f = fight(p, foe(1), field=cover_field.model_copy(deep=True))
    e = f.get("e1")
    bf.enter_zone(f, e, "z2")
    steps = bf.hit_modifiers(f, p, e)
    check(f"high ground hunter {n}: cover does not count", not any("cover" in s[0] for s in steps), steps)
    f.round = 3
    perks.after_hit(f, p, e, "hit", 10, rng)
    f.round = 4
    check(f"high ground hunter {n}: the target is pinned next round", perks.pinned(f, e) and combat.advance_step(f, e, p) == "")
q = player(reach="ranged")
f = fight(q, foe(1), field=cover_field.model_copy(deep=True))
bf.enter_zone(f, f.get("e1"), "z2")
check("without it, the cover counts", any("cover" in s[0] for s in bf.hit_modifiers(f, q, f.get("e1"))))

# ---- Curse of Rust: no metal on you, armor flakes off them, to the cap
for n in (1, 2):
    p = player(("curse_of_rust", 20))
    f = fight(p, foe(1, armor=100.0))
    e = f.get("e1")
    for _ in range(6):
        perks.rust(f, p, e, 5)
    check(f"curse of rust {n}: five stacks strip it all, and no further", e.counters.get("rust") == 5 and abs(e.armor) < 0.01, (e.counters.get("rust"), e.armor))
p = player(("curse_of_rust", 20), wears_metal=True)
f = fight(p, foe(1, armor=100.0))
perks.rust(f, p, f.get("e1"), 5)
check("curse of rust: in metal, nothing", f.get("e1").armor == 100)

# ---- Ley Tether: stillness halves the next spell, then must be earned again
bolt = spell("bolt", element="fire")
for n in (1, 2):
    p = player(("ley_tether", 50), moves=[bolt])
    f = fight(p, foe(1))
    f.round, p.move_round = 6, 2
    base = combat.cost_of(player(moves=[bolt]), bolt, f)
    half = combat.cost_of(p, bolt, f)
    check(f"ley tether {n}: standing fast, the spell costs half", half == max(1, round(base * 0.5)) or half == max(1, -(-base // 2)), (base, half))
    perks.on_cast(f, p, bolt, False, half)
    check(f"ley tether {n}: spent, it costs full again", combat.cost_of(p, bolt, f) == base)

# ---- Attuned Edge: the weapon strikes as the last spell's element
for n, el in ((1, "fire"), (2, "cold")):
    p = player("attuned_edge", moves=[spell("s", element=el)])
    f = fight(p, foe(1))
    perks.on_cast(f, p, p.moves[0], False, 5)
    check(f"attuned edge {n}: the blade takes the {el}", p.attuned == el)
    seen = []
    orig = combat.apply_damage
    combat.apply_damage = lambda c, a, d, *x, **k: seen.append(a.hit_element) or True
    bf.engage(f, p, f.get("e1"))
    combat.act_attack(f, p, f.get("e1"), rng)
    combat.apply_damage = orig
    check(f"attuned edge {n}: and the blow carries it", seen == [el] and p.hit_element == "", (seen, p.hit_element))

# ---- Withering: afflictions hold while you share their ground
for n in (1, 2):
    p = player("withering")
    f = fight(p, foe(1))
    e = f.get("e1")
    combat.add_status(f, e, ("slowed", "frightened")[n - 1], 2, p)
    for _ in range(4):
        combat.start_turn(e, f)
    check(f"withering {n}: it does not wear off beside you", ("slowed", "frightened")[n - 1] in e.statuses, e.statuses)
far = bb.Battlefield(zones={"z1": bb.BattleZone(id="z1", name="a", tags=["open"]), "z2": bb.BattleZone(id="z2", name="b", tags=["open"])},
                     edges=[bb.BattleEdge(a="z1", b="z2")], start="z1")
p = player("withering")
f = fight(p, foe(1), field=far)
e = f.get("e1")
bf.enter_zone(f, e, "z2")
combat.add_status(f, e, "slowed", 2, p)
for _ in range(4):
    combat.start_turn(e, f)
check("withering: apart from you, it fades", "slowed" not in e.statuses)

# ---- Blood Summons: no summon standing, one comes in blood - stronger, for this fight
call = spell("call", effect="summon", tier="light", reach="self", summon_form="decoy")
for n in (1, 2):
    p = player("blood_summons", moves=[call], hp=1000)
    f = fight(p, foe(1))
    hp0, mana0 = p.hp, p.mana
    combat.act_ability(f, p, call, None, rng)
    s_ = next((a for a in f.allies() if a.summon_form), None)
    check(f"blood summons {n}: a striker stands, a tier stronger, paid in blood",
          s_ is not None and p.hp < hp0 and s_.summon_tier == "moderate" and s_.summon_form == "striker", (s_ and s_.summon_form, p.hp, hp0))
    check(f"blood summons {n}: it lasts the fight and is never a companion", s_ is not None and s_.summon_until == 0 and not combat.is_companion(s_))
p = player(moves=[call])
f = fight(p, foe(1))
combat.act_ability(f, p, call, None, rng)
check("blood summons: without it, the spell makes its own summon", [a.summon_form for a in f.allies()] == ["decoy"])

# ---- Feral Form: a blessing on yourself puts spell power into the blow
wardbuff = spell("bark", effect="buff", buff="blur", tier="light")
for n in (1, 2):
    p = player("feral_form", moves=[wardbuff])
    f = fight(p, foe(1))
    check(f"feral form {n}: no blessing, no power", perks.feral(p, f) == 0)
    combat.act_ability(f, p, wardbuff, None, rng)
    check(f"feral form {n}: blessed, the blow carries spell power", perks.feral(p, f) > 0)

# ---- Arcane Precision: once a spell has found it, cover stops counting against your spells
for n in (1, 2):
    p = player("arcane_precision", reach="ranged")
    f = fight(p, foe(1), field=cover_field.model_copy(deep=True))
    e = f.get("e1")
    bf.enter_zone(f, e, "z2")
    p.position_tags = []
    p.spell_kind = "spell"
    before = any("cover" in s[0] for s in bf.hit_modifiers(f, p, e))
    perks.after_hit(f, p, e, "hit", 10, rng)
    after = any("cover" in s[0] for s in bf.hit_modifiers(f, p, e))
    check(f"arcane precision {n}: cover counted, then stops", before and not after, (before, after))

# ---- Frostborne: slowed quickens you, and cold mends
for n in (1, 2):
    p = player("frostborne", hp=400)
    f = fight(p, foe(1, element="cold"))
    took = combat.add_status(f, p, "slowed", 2, f.get("e1"))
    check(f"frostborne {n}: slowed becomes quick", not took and p.pace == "fast")
    p.hp = 300
    f.get("e1").hit_element = "cold"
    combat.take_damage(f, p, 50, f.get("e1"), rng, "magical")
    check(f"frostborne {n}: cold still wounds", p.hp < 300, p.hp)
    f.round += 4
    perks.on_turn_start(f, p)
    check(f"frostborne {n}: and the quickening passes", p.pace == "normal")

# ---- Frozen Ground: a cold kill freezes the ground, and whoever stands there is chilled
for n in (1, 2):
    p = player(("frozen_ground", 2), dmg=10**5)
    p.hit_element = "cold"
    f = fight(p, foe(1, hp=1), foe(2))
    e2 = f.get("e2")
    perks.on_kill(f, p, f.get("e1"), rng)
    check(f"frozen ground {n}: the ground freezes", f.zone_effects.get(f.get("e1").zone_id, {}).get("frozen_until") == f.round + 2)
    perks.on_turn_start(f, e2)
    check(f"frozen ground {n}: whoever stands there is chilled", "slowed" in e2.statuses)

# ---- Triage: the near-dead are healed double, and an affliction lifted
for n in (1, 2):
    p = player("triage", hp=400)
    t = ally(hp=200)
    f = fight(p, t, foe(1))
    t.hp = 20
    t.statuses["bleeding"] = 2
    healed, _ = perks.mend(f, p, t, 30)
    check(f"triage {n}: double the healing, and the bleeding stops", healed == 60 and "bleeding" not in t.statuses, (healed, t.statuses))
    t.hp = 150
    healed, _ = perks.mend(f, p, t, 30)
    check(f"triage {n}: above a quarter, plain healing", healed == 30)

# ---- Coordinated Strike: the second blow of a pair is critical
for n in (1, 2):
    p = player("coordinated_strike")
    t = ally()
    f = fight(p, t, foe(1))
    e = f.get("e1")
    f.round = 3 + n
    perks.after_hit(f, t, e, "hit", 10, rng)
    check(f"coordinated strike {n}: the companion struck, your blow crits", perks.on_outcome(f, p, e, "hit", None) == "crit")
    check(f"coordinated strike {n}: once a round", perks.on_outcome(f, p, e, "hit", None) == "hit")

# ---- Mending Rhythm: every third heal reaches the whole party
mendmove = spell("mend", effect="healing", tier="light", reach="self")
for n in (1, 2):
    p = player("mending_rhythm", moves=[mendmove], mana=10**4)
    t1, t2 = ally(fid="a1", name="Tam"), ally(fid="a2", name="Rue")
    f = fight(p, t1, t2, foe(1))
    t1.hp = t2.hp = 50
    for k in range(3):
        combat.act_ability(f, p, mendmove, None, rng)
        if k < 2:
            check(f"mending rhythm {n}: heal {k + 1} stays with you", t1.hp == 50 and t2.hp == 50)
    check(f"mending rhythm {n}: the third reaches everyone", t1.hp > 50 and t2.hp > 50, (t1.hp, t2.hp))

# ---- Sanctuary Circle: in your stance, no blow on an ally beside you lands critical
stance = Move(id="wall", name="Shield Wall", effect="defense", tier="moderate", reach="self", resource="stamina")
for n in (1, 2):
    p = player("sanctuary_circle", moves=[stance])
    t = ally()
    f = fight(p, t, foe(1))
    combat.act_ability(f, p, stance, None, rng)
    check(f"sanctuary circle {n}: a crit on Tam is only a hit", perks.on_outcome(f, f.get("e1"), t, "crit", None) == "hit")
    p.buffs.clear()
    check(f"sanctuary circle {n}: out of the stance, it crits", perks.on_outcome(f, f.get("e1"), t, "crit", None) == "crit")

# ---- Single-target blessings; Twin Benediction; Selfless; Shared Strength
emp = spell("might", effect="buff", buff="precision", tier="light")
p = player(moves=[emp])
t1, t2 = ally(fid="a1", name="Tam"), ally(fid="a2", name="Rue")
f = fight(p, t1, t2, foe(1))
combat.act_ability(f, p, emp, None, rng, give=[t1, t2])
check("a blessing falls on one at a time", "might" in t1.buffs and "might" not in t2.buffs and "might" not in p.buffs)
for n in (1, 2):
    p = player("twin_benediction", moves=[emp])
    t = ally()
    f = fight(p, t, foe(1))
    combat.act_ability(f, p, emp, None, rng, give=[t])
    check(f"twin benediction {n}: the ally's blessing falls on you too", "might" in t.buffs and "might" in p.buffs)
for n in (1, 2):
    p = player("selfless", moves=[emp])
    t = ally()
    f = fight(p, t, foe(1))
    refused = combat.act_ability(f, p, emp, None, rng)
    check(f"selfless {n}: you cannot bless yourself", refused is not None and "might" not in p.buffs)
    combat.act_ability(f, p, emp, None, rng, give=[t])
    plain = player(moves=[emp]); pt = ally(); pf = fight(plain, pt, foe(1))
    combat.act_ability(pf, plain, emp, None, rng, give=[pt])
    check(f"selfless {n}: what you give lasts two rounds longer", t.buffs["might"]["rounds"] == pt.buffs["might"]["rounds"] + 2, (t.buffs["might"]["rounds"], pt.buffs["might"]["rounds"]))
for n in (1, 2):
    p = player(("shared_strength", 3), moves=[emp], mana=200)
    t = ally()
    f = fight(p, t, foe(1))
    combat.act_ability(f, p, emp, None, rng, give=[t])
    p.mana = 100
    perks.after_hit(f, t, f.get("e1"), "hit", 10, rng)
    check(f"shared strength {n}: the blessed ally's hit returns mana", abs(p.mana - 106) < 0.01, p.mana)

# ---- Dread Regent: the first to break turns on its own side
for n in (1, 2):
    p = player("dread_regent")
    a, b, c = foe(1), foe(2), foe(3)
    for x in (a, b, c):
        x.behaviors = {}
    f = fight(p, a, b, c)
    behaviors._break(f, a, False)
    check(f"dread regent {n}: the first to run turns instead", a.counters.get("turned") and not a.fled and a not in f.enemies())
    hp_b, hp_c = b.hp, c.hp
    for _ in range(6):
        combat.enemy_turn(f, a, random.Random(n + _))
    check(f"dread regent {n}: and fights its old side", b.hp < hp_b or c.hp < hp_c, (b.hp, c.hp))
    behaviors._break(f, b, False)
    check(f"dread regent {n}: only the first", b.fled and not b.counters.get("turned"))

# ---- Familiar's Eyes: a spell cast from where the summon stands
melee_spell = spell("touch", reach="melee")
for n in (1, 2):
    p = player("familiars_eyes", moves=[melee_spell], mana=10**4)
    sp = spirit()
    f = fight(p, sp, foe(1, hp=10**6), field=far.model_copy(deep=True))
    e = f.get("e1")
    bf.enter_zone(f, e, "z2"); bf.enter_zone(f, sp, "z2"); bf.engage(f, sp, e)
    hp0 = e.hp
    for k in range(6):
        combat.act_ability(f, p, melee_spell, e, random.Random(n * 10 + k))
    check(f"familiar's eyes {n}: a touch spell lands from across the field", e.hp < hp0 and p.zone_id == "z1", (e.hp, p.zone_id))
q = player(moves=[melee_spell], mana=10**4)
f = fight(q, spirit(), foe(1), field=far.model_copy(deep=True))
bf.enter_zone(f, f.get("e1"), "z2")
combat.act_ability(f, q, melee_spell, f.get("e1"), rng)
check("familiar's eyes: without it, you must walk there", q.zone_id == "z2" or f.get("e1").hp == f.get("e1").max_hp)

from core.rules import MECHANICS
check("every round-two perk is registered at creation", all(MECHANICS[m].where == "creation" for m in
      ("juggernaut", "headsman", "blood_for_blood", "judgement", "thick_of_it", "siege_breaker", "shadowstep", "dormant_venom", "quarry",
       "steady_aim", "high_ground_hunter", "scout_ahead", "curse_of_rust", "ley_tether", "attuned_edge", "withering", "blood_summons",
       "familiars_eyes", "feral_form", "arcane_precision", "frostborne", "frozen_ground", "triage", "coordinated_strike",
       "mending_rhythm", "sanctuary_circle", "twin_benediction", "selfless", "shared_strength", "dread_regent")))
from core.rules import FAMILIES as _F
check("reverse engineer is disabled: no family offers it", not any(o.mechanic == "reverse_engineer" for f_ in _F.values() for o in f_.options))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
