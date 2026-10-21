"""Creature families: every creature has one, and the families really change how a fight goes. (Ported to the battlefield in f223: a
fighter "engaged" is tied up with the player, "near" stands in the same ground untied, "far" across the field.)"""
import random, sys, statistics
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from engine import combat as C, behaviors as B, battlefield as bfm
from engine.battlefield import Battlefield, BattleZone, BattleEdge
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

w = load_world()
fams = B.FAMILIES
check("every creature names a family that exists", all(c.family in fams for c in w.bestiary.values()), [c.id for c in w.bestiary.values() if c.family not in fams][:5])
check("no family goes unused", set(fams) <= {c.family for c in w.bestiary.values()}, set(fams) - {c.family for c in w.bestiary.values()})
KNOWN = {"flank", "pounce", "charge", "dive", "hover", "breath", "breath_every", "slam", "slam_every", "sweep", "surge", "surge_every", "venom", "grapple",
         "befuddle", "frenzy", "rage", "corrode", "drain", "keep_range", "defend_low", "use_item", "flee_low", "surrender", "fearless",
         "stalk", "relentless"}
check("families use only behaviours the engine knows", all(set(f.get("behaviors", {})) <= KNOWN for f in fams.values()), {k: set(f.get("behaviors", {})) - KNOWN for k, f in fams.items() if set(f.get("behaviors", {})) - KNOWN})
from core.rules import MECHANICS
check("families use only mechanics that exist", all(m in MECHANICS for f in fams.values() for m in f.get("legendary", {})), [m for f in fams.values() for m in f.get("legendary", {}) if m not in MECHANICS])
check("every family says how it fights", all(f.get("text") for f in fams.values()))
for cid, fam in (("wolf", "pack_hunter"), ("wyvern", "winged_drake"), ("bandit", "outlaw"), ("skeleton", "undead_shambler"), ("troll", "troll"), ("swarm_of_rats", "swarm"),
                 ("goblin", "raider"), ("red_dragon_wyrmling", "drake"), ("treant", "plant_titan"), ("gelatinous_cube", "ooze")):
    check(f"{cid} is a {fam}", w.bestiary[cid].family == fam, w.bestiary[cid].family)

def foe(cid, lvl=20, i=0, rank="normal"):
    return C.fighter_from_creature(w.bestiary[cid], lvl, rank, f"e{i}", name=f"{cid} {i}")
def me(**k):
    d = dict(id="p", name="you", side="player", level=20, attrs={a: 20 for a in C.ATTRIBUTES}, hp=10 ** 6, max_hp=10 ** 6, weapon_damage=0.1, weapon_name="stick",
             stamina=500, max_stamina=500, mana=0, max_mana=0, armor=50)
    d.update(k); return C.Fighter(**d)
WANT, CURRENT = {}, [None]
def arena(fighters):
    cmb = C.Combat(fighters=fighters)
    cmb.battlefield = Battlefield(zones={"z1": BattleZone(id="z1", name="the ground"), "z2": BattleZone(id="z2", name="the far side")},
                                  edges=[BattleEdge(a="z1", b="z2")], start="z1")
    for f in fighters:
        f.zone_id, f.row = "z1", ("back" if f.reach == "ranged" else "front")
    CURRENT[0] = cmb
    for f in fighters:
        if id(f) in WANT:
            want(f, WANT[id(f)])
    return cmb
def want(f, state):
    """Put a fighter where the old range bands said: engaged with the player, near (same ground, untied) or far."""
    WANT[id(f)] = state
    cmb = CURRENT[0]
    if cmb is None or f not in cmb.fighters or f.side == "player":
        return
    p = cmb.player
    if state == "engaged":
        if f.zone_id != p.zone_id:
            bfm.enter_zone(cmb, f, p.zone_id)
        bfm.engage(cmb, p, f)
    elif state == "near":
        bfm.release(cmb, f)
    else:
        bfm.enter_zone(cmb, f, "z2")
def band(f):
    cmb = CURRENT[0]
    if f.engaged_with:
        return "engaged"
    return "near" if f.zone_id == cmb.player.zone_id else "far"
def fight(foes, **k):
    p = me(**k)
    for f in foes:
        WANT.setdefault(id(f), "engaged")
    return arena([p] + foes), p

wolf = foe("wolf")
check("a creature gets its family's traits", wolf.family == "pack_hunter" and wolf.behaviors["flank"] == B.FAMILIES["pack_hunter"]["behaviors"]["flank"] and wolf.legendary["rending"] == B.FAMILIES["pack_hunter"]["legendary"]["rending"])
boss = foe("wolf"); boss.boss = {"kit": "beast"}
cmb, p = fight([boss]); want(p, "engaged"); want(boss, "engaged"); cmb.round = 3
check("a boss never uses family behaviours", not B.pre_turn(cmb, boss, p, random.Random(1)) and B.attack_mult(cmb, boss, p) == (1.0, []))
comp = C.companion_fighter(w.bestiary["wolf"], 20, "c", "pet")
check("a companion wolf has no family traits", comp.family == "" and not comp.behaviors and "rending" not in comp.legendary)

def dmg_of(f, first_n=1, others=0, tgt_hp=None, seed=1):
    es = [f] + [foe(f.creature, 20, i + 1) for i in range(others)]
    cmb, p = fight(es)
    if tgt_hp: p.hp = tgt_hp
    want(p, "engaged"); [want(e, "engaged") for e in es]
    out = []
    for n in range(first_n):
        h = p.hp
        C.enemy_turn(cmb, f, random.Random(seed + n))
        out.append(h - p.hp)
    return out, cmb, p

def avg_first(cid, n=200, **kw):
    r = []
    for s in range(n):
        f = foe(cid); want(f, "engaged")
        out, *_ = dmg_of(f, 1, seed=s, **kw); r.append(out[0])
    return statistics.mean(r)
base = foe("wolf"); base.behaviors = {}; base.legendary = {}; base.family = ""
def avg_plain(n=200, others=0):
    r = []
    for s in range(n):
        f = foe("wolf"); f.behaviors = {}; f.legendary = {}; f.family = ""; want(f, "engaged")
        es = [f] + [foe("wolf", 20, i + 1) for i in range(others)]
        for e in es: want(e, "engaged"); e.behaviors = {}; e.legendary = {}; e.family = ""
        cmb, p = fight(es); want(p, "engaged"); h = p.hp
        C.enemy_turn(cmb, f, random.Random(s)); r.append(h - p.hp)
    return statistics.mean(r)
def avg_pack(n=200, others=1):
    r = []
    for s in range(n):
        f = foe("wolf"); want(f, "engaged")
        es = [f] + [foe("wolf", 20, i + 1) for i in range(others)]
        for e in es: want(e, "engaged")
        cmb, p = fight(es); want(p, "engaged"); h = p.hp
        C.enemy_turn(cmb, f, random.Random(s)); r.append(h - p.hp)
    return statistics.mean(r)
check("a wolf with packmates hits harder than a lone wolf (flank)", avg_pack(others=1) > avg_pack(others=0) * 1.1, (avg_pack(others=0), avg_pack(others=1)))

# pounce: first blow only
tiger = foe("tiger"); want(tiger, "engaged")
cmb, p = fight([tiger]); want(p, "engaged")
C.enemy_turn(cmb, tiger, random.Random(3))
check("a predator's first strike is an ambush, and later ones are not", tiger.counters.get("struck") == 1 and B.attack_mult(cmb, tiger, p)[0] == 1.0, B.attack_mult(cmb, tiger, p))
tiger2 = foe("tiger"); cmb2, p2 = fight([tiger2])
check("the first blow's multiplier shows the pounce", abs(B.attack_mult(cmb2, tiger2, p2)[0] - (1 + B.FAMILIES["predator"]["behaviors"]["pounce"] / 100)) < 1e-9)

# dive and hover
wy = foe("wyvern"); want(wy, "engaged")
cmb, p = fight([wy]); want(p, "engaged")
bands = []
for r in range(7):
    cmb.round = r + 1
    C.enemy_turn(cmb, wy, random.Random(r)); bands.append(band(wy))
check("a wyvern wheels out of reach every few rounds and dives back in", "near" in bands and "engaged" in bands, bands)
wy2 = foe("wyvern"); want(wy2, "far")
cmb, p = fight([wy2]); want(p, "engaged"); h = p.hp
C.enemy_turn(cmb, wy2, random.Random(1))
check("a flyer closing in strikes in the same turn (dive)", band(wy2) == "engaged" and p.hp < h or any("swoops" in s for s in cmb.story), (band(wy2), cmb.story))
# charge
boar = foe("boar", 10); want(boar, "far")
cmb, p = fight([boar]); want(p, "engaged"); h = p.hp
C.enemy_turn(cmb, boar, random.Random(2))
check("a charger closes and strikes at once", band(boar) == "engaged" and any("arrives" in s for s in cmb.story), cmb.story)
plain = foe("wolf"); want(plain, "far"); plain.behaviors = {}; plain.family = ""
cmb, p = fight([plain]); C.enemy_turn(cmb, plain, random.Random(2))
check("an ordinary creature closes in without a charge", band(plain) == "engaged" and not any("arrives" in s for s in cmb.story), cmb.story)

# breath
dr = foe("young_red_dragon", 40); want(dr, "near")
ally = me(id="a", name="ally", side="ally"); cmb = arena([me(), ally, dr])
pl = cmb.player; h0, h1 = pl.hp, ally.hp
cmb.round = 3
C.enemy_turn(cmb, dr, random.Random(1))
check("a dragon's breath hits everyone against it on its round", pl.hp < h0 and ally.hp < h1, (pl.hp, ally.hp))
cmb.story = []; cmb.round = 2; want(dr, "engaged"); want(pl, "engaged")
C.enemy_turn(cmb, dr, random.Random(1))
check("...and not on the other rounds", not any("breath" in s for s in cmb.story), cmb.story)
# slam
og = foe("ogre", 30); want(og, "engaged")
cmb, p = fight([og]); want(p, "engaged"); cmb.round = 4
C.enemy_turn(cmb, og, random.Random(5))
check("a giant slams on its round", any("crushing blow" in s for s in cmb.story), cmb.story)
# sweep
sw = foe("swarm_of_rats", 5); want(sw, "engaged")
ally = me(id="a", name="ally", side="ally"); cmb = arena([me(), ally, sw]); bfm.engage(cmb, cmb.player, sw); bfm.engage(cmb, ally, sw)
hp0 = (cmb.player.hp, ally.hp)
C.enemy_turn(cmb, sw, random.Random(2))
check("a swarm strikes everyone at once", (cmb.player.hp, ally.hp) != hp0 and any("everyone in reach" in s for s in cmb.story), cmb.story)

# on-hit effects
def many(cid, status, n=300, lvl=20):
    got = 0
    for s in range(n):
        f = foe(cid, lvl); want(f, "engaged")
        cmb, p = fight([f]); want(p, "engaged")
        B.after_hit(cmb, f, p, True, random.Random(s)); got += status in p.statuses
    return got / n
check("venomous creatures poison (about 30%)", 0.2 < many("giant_spider", "poisoned") < 0.4, many("giant_spider", "poisoned"))
check("serpents seize", many("constrictor_snake", "grappled", ) > 0.1)
check("fey scatter the mind", many("sprite", "befuddled") > 0.15, many("sprite", "befuddled"))
f = foe("gelatinous_cube"); cmb, p = fight([f]); a0 = p.armor
for s in range(10): B.after_hit(cmb, f, p, True, random.Random(s))
check("an ooze eats armor, but only so far", p.armor < a0 and p.armor >= a0 * 0.7 - 0.01, (a0, p.armor))
f = foe("wraith"); cmb, p = fight([f]); s0 = p.stamina
B.after_hit(cmb, f, p, True, random.Random(1))
check("a wraith drains stamina", p.stamina < s0)
f = foe("troll"); f.hp = f.max_hp * 0.4; h = f.hp; C.start_turn(f, cmb)
check("a troll regenerates each turn", f.hp > h)
f = foe("mage"); want(f, "engaged"); cmb, p = fight([f]); want(p, "engaged")
seen = []
for r in range(B.KEEP_RANGE_EVERY * 2):
    C.enemy_turn(cmb, f, random.Random(r)); seen.append(band(f))
    if band(f) == "near": break
check("a caster gives ground only every few blows, so you can still catch it", "near" in seen and seen[0] == "engaged", seen)

# yield / flee / fearless / items / guard
def low(cid, share, lvl=20, others=0):
    f = foe(cid, lvl); f.hp = f.max_hp * share
    es = [f] + [foe(cid, lvl, i + 1) for i in range(others)]
    cmb, p = fight(es); [want(e, "engaged") for e in es]; want(p, "engaged"); return f, es, cmb, p
res = []
for s in range(60):
    f, es, cmb, p = low("bandit", 0.2); C.enemy_turn(cmb, f, random.Random(s)); res.append((f.fled, f.surrendered, f.counters.get("drank", 0), f.defending))
check("a beaten bandit sometimes yields, sometimes drinks, sometimes guards", any(r[1] for r in res) and any(r[2] for r in res) and any(r[3] for r in res), [sum(r[i] for r in res) for i in (0, 1, 2, 3)])
f, es, cmb, p = low("bandit", 0.9); C.enemy_turn(cmb, f, random.Random(1))
check("a healthy bandit fights on", not f.fled and not f.surrendered)
fl = 0
for s in range(60):
    f, es, cmb, p = low("deer", 0.3, 5); C.enemy_turn(cmb, f, random.Random(s)); fl += f.fled and not f.surrendered
check("a hurt deer bolts (it does not yield)", fl > 10, fl)
for cid in ("skeleton", "cultist", "ghost"):
    ok = True
    for s in range(60):
        f, es, cmb, p = low(cid, 0.05); C.enemy_turn(cmb, f, random.Random(s)); ok = ok and not f.fled
    check(f"a {cid} never breaks", ok)
# morale
br = 0
for s in range(80):
    f, es, cmb, p = low("bandit", 0.1, 20, others=3)
    for e in es[1:]: e.level = 5
    f.counters.clear(); C.enemy_turn(cmb, f, random.Random(s))
    if f.fled: br += sum(1 for e in es[1:] if e.fled)
check("when the strongest breaks, others may break with it", br > 0, br)
f, es, cmb, p = low("bandit", 0.1, 20, others=1); es[1].level = 30
B.morale(cmb, f, random.Random(1))
check("a weaker one breaking does not move the stronger", not es[1].fled)
# families change a fight
def avg_fight(cid, n=40):
    out = []
    for s in range(n):
        f = [foe(cid, 20, i) for i in range(2)]
        cmb, p = fight(f, weapon_damage=0.1)
        for e in f: want(e, "engaged")
        want(p, "engaged"); rng = random.Random(s)
        for r in range(6):
            cmb.round = r + 1
            for e in cmb.enemies(): C.enemy_turn(cmb, e, rng)
        out.append(p.max_hp - p.hp)
    return statistics.mean(out)
print("   damage over 6 rounds, two foes:", {c: round(avg_fight(c)) for c in ("wolf", "wyvern", "bandit", "skeleton", "ogre", "goblin")})
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS []")
sys.exit(1 if bad else 0)
