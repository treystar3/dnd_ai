"""(f772) A floor that holds a killing harm holds the whole blow, and the floors are declared once for every damage path (found by the
code audit, trace-fight-2: a bleeding foe with yields_at, struck by the blow that should make him yield, was yielded and dead in 48 of 48
landed blows, the torn wound of that same blow killing him past his floor; by the same code a Lifeline companion and a Deathless player
held at 1 died to the tear, and a poison's or a burn's tick passed every floor but the duel's and the first hunt's).
The owner, 2026-11-19 (GOALS.md's top decision row, question 2): everything a blow carries is the blow (its torn wound, its riders, a
gear element's damage, a Death's Door it sets off), and a floor that holds a blow holds the whole of it; (b) every floor holds every
harm, a tick included, a once-a-fight floor spent by a tick as by a blow. The floors (the duel, the first hunt, Lifeline, Soul Tether, a
boss's last stand, Orenna's Last Breath, Deathless, Deathward, a yielding foe) are one table in data/rules/stages.yaml, which every
damage path (a blow, a tick, a torn wound, a rebound) is held to by engine/data_check.py.
The finder's case, then every floor on every path: a blow and all it carries (its tear, a gear element's damage, Death's Door, the
weapon's statuses, a family's venom), a tick, a tear, a rebound and side harm; the once-a-fight floors spent by a tick; a blow nested in
another (a pack-mate's) still its own; the lines that name the harm; and what f768 to f771 left for this feature (a felled defender's
thorns and Frost Armor, a foe that yielded at its turn's start still harmed, a striker that fell or yielded at its own blow carrying on,
the torn wound deciding a duel, the rebound's duel floor in the table). Then the table and its check.
Run: python tools/sim/floor_holds_772_test.py"""
import copy
import inspect
import random
import re
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 1)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import yaml
from engine import battlefield as bf
from engine import behaviors, bosses, combat, damage, data_check, streams
from engine import effects as fx
from engine import spellcraft as SC

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
    f = combat.Combat(fighters=list(fs), record=True, serial=kw.pop("serial", "fh"), **kw)
    combat.ensure_field(f)
    f.opened = True
    return f


def landed(f, att):
    """Whether the last recorded blow by this striker landed."""
    rec = next((h for h in reversed(f.hits) if h["att"] == att.name), None)
    return rec is not None and rec.get("outcome") not in ("miss", "phase", "")


def told(f, pat) -> bool:
    return any(re.search(pat, s, re.I) for s in f.story)


def falls(f, x) -> list[int]:
    w = re.escape(combat.who(x))
    pat = re.compile(rf"(^|, and |\. ){w} (fall|falls|succumbs|collapse|collapses)\b", re.I)
    return [i for i, s in enumerate(f.story) if pat.search(s)]


def poison(f, x, by=None, dose=500, dot="poisoned"):
    if by is None:
        fx.put_status(x, dot, 3)
    else:
        combat.add_status(f, x, dot, 3, by)
    fx.set_strength(x, dot, [dose] if dot == "poisoned" else dose)


def bleed(f, x, by, size=500):
    combat.add_status(f, x, "bleeding", 3, by)
    fx.set_strength(x, "bleeding", size)


reaches = getattr(combat, "reaches", None)
streams.begin(7, 1, "I fight.")


# ---- 1. the finder's case: a bleeding foe that yields, struck by the blow that should make him yield
def executioner(seed, bleeding=True, hp=30, mult=50.0, wound=5):
    p = fighter("player", "player", hp=500, dmg=10)
    e = fighter("e1", "enemy", hp=hp, max_hp=100, level=3, rank="elite", name="the Bound Executioner", dmg=4,
                category="hostile people", behaviors={"fearless": 1})
    e.yields_at, e.yield_text = 0.25, "he lowers the blade and walks away"
    f = fight(p, e)
    bf.engage(f, p, e)
    if bleeding:
        bleed(f, e, p, wound)
    combat.apply_damage(f, p, e, mult, "strikes", random.Random(seed), reliable=True)
    return f, p, e


for bleeding in (False, True):
    dead = yielded = 0
    for seed in range(40):
        f, p, e = executioner(seed, bleeding)
        dead += not e.alive
        yielded += e.alive and e.fled
    check(f"the finder's case ({'an open wound' if bleeding else 'no wound'}): the blow that makes him yield never kills him (40 blows)",
          dead == 0 and yielded == 40, (dead, yielded))
f, p, e = executioner(1)
check("...his wound is not torn by the blow he yielded at, and no fall is told, named or paid", not told(f, "wound open again")
      and not falls(f, e) and e.id not in f.felled_by and p.kill_round != f.round and e.hp >= 1, (f.story, f.felled_by, e.hp))
combat.finish_round(f, random.Random(1))
check("...and the fight he left is won with him alive, not among the dead", f.over == "victory" and e.alive and e.fled, (f.over, e.alive))
dead = 0
for seed in range(40):                                       # a deep wound and an ordinary blow past his yielding point
    f, p, e = executioner(seed, hp=40, mult=1.0, wound=200)
    dead += not e.alive
check("...nor does an ordinary blow that takes him past his yielding point, on a deep wound (40 blows)", dead == 0, dead)
n = 0
for seed in range(40):                                       # the blow leaves him above it; the wound alone would kill: the floor holds the tear
    f, p, e = executioner(seed, hp=100, mult=0.05, wound=900)
    if e.hp > 1 and not e.fled:
        continue
    n += 1
    check(f"(seed {seed}) the torn wound that would kill him is held at his floor, and he yields", e.alive and e.fled and e.hp >= 1, (e.hp, e.fled))
    break
check("(a seed where the wound alone would have ended him)", n == 1)

# ---- 2. a blow and all it carries: a floor that holds the blow holds its tear, its riders and a Death's Door it sets off
CARRIED = {"its torn wound": "wound open again", "its weapon's fire": "fire damage follows", "a Death's Door it sets off": "death reaches for",
           "its weapon's statuses": ""}


def struck(holder, rider, setup, seeds=120):
    """A wolf's bite that would kill the one a floor holds, carrying one thing more: a wound it tears, its weapon's fire, Death's Door,
    or the statuses its weapon lays (Hex, Rending)."""
    for seed in range(seeds):
        p = fighter("player", "player", hp=10 ** 6)
        wolf = fighter("wolf 1", "enemy", dmg=40)
        x = holder(p)
        f = fight(*([p, x] if x is not p else [p]), wolf, **setup.get("fight", {}))
        bf.engage(f, wolf, x)
        if rider == "its torn wound":
            bleed(f, x, wolf, 900)
        elif rider == "its weapon's fire":
            wolf.bonuses = [combat.Bonus(modifies="fire_damage", trigger="always", magnitude=300, flat=True)]
        elif rider == "a Death's Door it sets off":
            wolf.hit_element = wolf.element = "necrotic"
            wolf.casting = {"exprs": ["deaths_door"], "tier": "moderate", "name": "Death's Door", "once": []}
        else:
            wolf.legendary.update({"rending": 100, "hex": 1})
        try:
            combat.apply_damage(f, wolf, x, 1.0, "bites", random.Random(seed))
        finally:
            SC.end(wolf)
        if landed(f, wolf):
            return f, p, x, wolf
    return None


def held_whole(name, holder, after, line, setup=None):
    for rider, pat in CARRIED.items():
        got = struck(holder, rider, setup or {})
        check(f"(a seed where the wolf's bite lands on {name}, carrying {rider})", got is not None)
        if not got:
            continue
        f, p, x, wolf = got
        check(f"{name}: the floor holds the bite", told(f, line), f.story)
        if pat:
            check(f"{name}: ...and {rider} takes nothing from the held", not told(f, pat), f.story)
        else:
            check(f"{name}: ...and {rider} lay nothing on the held", "hexed" not in x.statuses and "bleeding" not in x.statuses, x.statuses)
        check(f"{name}, {rider}: ...so the held one stands where the floor left it, and no fall is told", x.alive and after(x) and not falls(f, x),
              (x.hp, x.alive, f.story))
        if reaches is not None:
            check(f"{name}, {rider}: the floor's note goes when the blow ends: the next blow reaches it", reaches(f, x))


def lifeline_ash(p):
    p.legendary["lifeline"] = 1
    return fighter("ally_ash", "ally", hp=5, max_hp=100, name="Ash")


def deathless_player(p):
    p.legendary["deathless"] = 1
    p.hp, p.max_hp = 5, 100
    return p


def deathward_player(p):
    p.legendary["deathward"] = 10
    p.hp, p.max_hp = 5, 100
    return p


def tethered(p):
    t = fighter("ally_wisp", "ally", hp=5, max_hp=100, name="Wisp")
    t.tether = 30
    return t


def breathing(p):
    p.breath = True
    p.hp, p.max_hp = 5, 100
    return p


held_whole("a Lifeline companion", lifeline_ash, lambda x: x.hp == 1, r"^The blow should have ended Ash, but the bond with its master will not let it fall \(Lifeline\)$")
held_whole("a Deathless player", deathless_player, lambda x: x.hp == 1, r"held on the threshold")
held_whole("a Deathward wearer", deathward_player, lambda x: x.hp == 11 and x.deathward_used, r"older than death")
held_whole("a Soul Tether", tethered, lambda x: x.hp == 30 and not x.tether, r"draws it back from the brink")
held_whole("Orenna's Last Breath", breathing, lambda x: x.hp == x.max_hp and not x.breath, r"tired warmth")
held_whole("the first hunt", lambda p: setattr(p, "hp", 5) or setattr(p, "max_hp", 100) or p, lambda x: x.hp == 1,
           r"a hand catches you|pulls you aside", {"fight": {"mentor": True}})


def boss_wolf(p):
    b = fighter("boar", "enemy", hp=5, max_hp=100, name="the old boar", category="beast")
    b.boss = bosses.make(bosses.kit_for("beast"), "campaign", "the old boar")
    return b


got = None
for seed in range(120):                                       # the boss is struck: its last stand holds the player's blow and all it carries
    p = fighter("player", "player", dmg=400)
    p.bonuses = [combat.Bonus(modifies="fire_damage", trigger="always", magnitude=3000, flat=True)]
    p.legendary.update({"rending": 100, "hex": 1})
    b = boss_wolf(p)
    f = fight(p, b)
    bf.engage(f, p, b)
    bleed(f, b, p, 900)
    combat.apply_damage(f, p, b, 1.0, "strikes", random.Random(seed))
    if landed(f, p):
        got = (f, p, b)
        break
check("(a seed where the blow on the boss lands)", got is not None)
if got:
    f, p, b = got
    check("a boss's last stand holds the blow", b.boss["stand_used"] and told(f, "BOSS LAST STAND"), f.story)
    check("...and the same blow's tear, its fire and its weapon's statuses take nothing from it: it stands at its last stand",
          b.alive and b.hp == round(b.max_hp * bosses.B["last_stand"]["hp_pct"] / 100) and not told(f, "wound open again")
          and not told(f, "fire damage follows") and not b.statuses, (b.hp, b.statuses, f.story))

# a foe that yields at the blow: what else the blow carries lands on none who has left
got = None
for seed in range(60):
    p = fighter("player", "player", dmg=400)
    p.bonuses = [combat.Bonus(modifies="fire_damage", trigger="always", magnitude=300, flat=True)]
    p.legendary.update({"hex": 1, "rending": 100, "terrify": 100, "frostbite": 100, "curse_of_rust": 10})
    e = fighter("e1", "enemy", hp=30, max_hp=100, name="the bandit", armor=40)
    e.yields_at = 0.25
    f = fight(p, e)
    bf.engage(f, p, e)
    combat.apply_damage(f, p, e, 1.0, "strikes", random.Random(seed))
    if landed(f, p):
        got = (f, p, e)
        break
check("(a seed where the blow that makes the bandit yield lands)", got is not None)
if got:
    f, p, e = got
    check("a foe that yields at the blow takes none of the rest of it: no fire, no status, no rust, no line of one",
          e.alive and e.fled and not e.statuses and not told(f, "fire damage follows") and not told(f, "curse settles")
          and not told(f, "flakes away") and e.armor == 40 and "rust" not in e.counters, (e.statuses, e.armor, f.story))

# a family's venom rides its bite: a floor that holds the bite holds the venom
got = None
for seed in range(120):
    p = fighter("player", "player")
    p.legendary["lifeline"] = 1
    ash = fighter("ally_ash", "ally", hp=5, max_hp=100, name="Ash")
    spider = fighter("spider 1", "enemy", family="venomous", behaviors={"venom": 100, "surge": 1.0, "surge_every": 1}, dmg=40)
    f = fight(p, ash, spider)
    bf.engage(f, spider, ash)
    behaviors.pre_turn(f, spider, ash, random.Random(seed))
    if landed(f, spider):
        got = (f, ash)
        break
check("(a seed where the spider's surge lands on Ash)", got is not None)
if got:
    f, ash = got
    check("a family's venom rides the bite a floor held: Lifeline holds Ash, and no venom is laid", ash.alive and ash.hp == 1
          and "poisoned" not in ash.statuses, (ash.hp, ash.statuses))

# ---- 3. another blow is its own: a pack-mate's blow nested in the player's, and the next wolf's bite
got = None
for seed in range(200):
    p = fighter("player", "player", dmg=400)
    p.legendary["packbond"] = 100
    pet = fighter("ally_pet", "ally", dmg=10 ** 4, name="Grip")
    e = fighter("e1", "enemy", hp=20, max_hp=100, name="the bandit")
    e.legendary["deathward"] = 10
    f = fight(p, pet, e)
    bf.engage(f, p, e)
    combat.act_attack(f, p, e, random.Random(seed))
    if e.deathward_used and told(f, r"\(Packbond\)"):
        got = (f, pet, e)
        break
check("(a seed where Deathward holds the player's blow and the bond answers it)", got is not None)
if got:
    f, pet, e = got
    check("a pack-mate's blow nested in the player's is its own blow: Deathward is spent, and it may kill",
          not e.alive and f.felled_by.get(e.id) == combat.who(pet), (e.hp, f.felled_by))
got = None
for seed in range(200):
    p = fighter("player", "player")
    p.legendary["lifeline"] = 1
    ash = fighter("ally_ash", "ally", hp=5, max_hp=100, name="Ash")
    w1, w2 = fighter("wolf 1", "enemy", dmg=40), fighter("wolf 2", "enemy", dmg=40)
    f = fight(p, ash, w1, w2)
    bf.engage(f, w1, ash)
    combat.apply_damage(f, w1, ash, 1.0, "bites", random.Random(seed))
    if ash.counters.get("lifeline"):
        for s2 in range(60):
            combat.apply_damage(f, w2, ash, 1.0, "bites", random.Random(1000 + s2))
            if not ash.alive:
                break
        got = (f, ash)
        break
check("the next wolf's bite on a companion Lifeline has held is its own blow, and kills", got is not None and not got[1].alive)

# ---- 3b. one striker's strikes on one target in one attack are one blow: a floor that held the first holds the rest
from engine import martial
from engine.combat import Move
got = flurried = 0
for seed in range(240):                                       # a wolf's Flurry (the perk) after Lifeline held its bite
    p = fighter("player", "player")
    p.legendary["lifeline"] = 1
    ash = fighter("ally_ash", "ally", hp=5, max_hp=100, name="Ash")
    wolf = fighter("wolf 1", "enemy", dmg=40)
    wolf.legendary["flurry"] = 100
    f = fight(p, ash, wolf)
    bf.engage(f, wolf, ash)
    combat.apply_damage(f, wolf, ash, 1.0, "bites", random.Random(seed))
    if ash.counters.get("lifeline"):
        got += 1
        flurried += (not ash.alive) or told(f, r"\(Flurry\)")
check("a foe's Flurry after Lifeline held its bite: no follow-up strike, Ash stands at 1 (every seed Lifeline held)",
      got >= 20 and flurried == 0, (flurried, got))


def boss_struck(run, seeds=200):
    """The player strikes a boss at 5 health with something of several strikes; its last stand holds the first. Returns how often the
    stand held, how often the boss then fell in the same attack, and how often its health stood where the stand left it."""
    held = fell = stood = 0
    for seed in range(seeds):
        p = fighter("player", "player", dmg=400)
        b = boss_wolf(p)
        f = fight(p, b)
        bf.engage(f, p, b)
        run(f, p, b, random.Random(seed))
        if b.boss["stand_used"]:
            held += 1
            fell += not b.alive
            stood += b.alive and b.hp == round(b.max_hp * bosses.B["last_stand"]["hp_pct"] / 100)
    return held, fell, stood


def perk_flurry(f, p, b, rng):
    p.legendary["flurry"] = 100
    combat.act_attack(f, p, b, rng)


for name, run in (
        ("the player's Flurry (the perk)", perk_flurry),
        ("a martial flurry of three strikes", lambda f, p, b, rng: combat.act_ability(
            f, p, Move(id="t_flurry", name="Hammering Flurry", effect="damage", tier="moderate", reach="melee", resource="stamina",
                       attribute="strength", martial_form="flurry", hits=3), b, rng)),
        ("a volley (a shape of three parts)", lambda f, p, b, rng: combat.act_ability(
            f, p, Move(id="t_volley", name="Arrow Volley", effect="damage", tier="moderate", reach="melee", resource="stamina",
                       attribute="strength", shape="volley"), b, rng)),
        ("a double strike (a shape of two parts)", lambda f, p, b, rng: combat.act_ability(
            f, p, Move(id="t_double", name="Twin Cut", effect="damage", tier="moderate", reach="melee", resource="stamina",
                       attribute="strength", shape="double"), b, rng))):
    held, fell, stood = boss_struck(run)
    check(f"{name} at a boss: its last stand holds the first strike, and the rest of the attack takes nothing ({held} held)",
          held >= 10 and fell == 0 and stood == held, (held, fell, stood))
got = None
for seed in range(200):                                       # a boss's follow-through after Deathward held its blow, in its own turn
    p = fighter("player", "player", hp=5, max_hp=100)
    p.legendary["deathward"] = 10
    boss = fighter("boss", "enemy", name="the captain", category="hostile people", dmg=400)
    boss.boss = bosses.make(bosses.kit_for("hostile people"), "captain", "the captain")
    f = fight(p, boss)
    bf.engage(f, boss, p)
    BLOWS = []
    _apply0 = combat.apply_damage

    def counting(c, att, dfn, *a, **k):
        BLOWS.append(len(c.hits))
        return _apply0(c, att, dfn, *a, **k)
    combat.apply_damage = counting
    try:
        combat.enemy_turn(f, boss, random.Random(seed))
    finally:
        combat.apply_damage = _apply0
    if p.deathward_used:
        got = (f, p, len(BLOWS), len(f.hits))
        break
check("(a seed where Deathward holds the boss's blow)", got is not None)
if got:
    f, p, asked, recorded = got
    check("a boss's follow-through in the same turn takes nothing from the one Deathward held: no roll, no line, no harm",
          p.alive and p.hp == 11 and asked == 2 and recorded == 1, (p.hp, asked, recorded, f.story))
p = fighter("player", "player")
b, other = fighter("e1", "enemy", name="the bandit"), fighter("e2", "enemy", name="the archer")
f = fight(p, b, other)
spark = Move(id="t_bolt", name="Spark", effect="damage", tier="moderate", reach="ranged", resource="mana", attribute="intelligence")
act = combat.OpenAction()
with combat.in_progress(f, act):
    act.floored.append((p, b))
    check("a perk's repeat (Spell Echo, Grave Chorus) goes at no foe its striker's floor-held strike reached in the action: the nearest other",
          combat.aim(f, p, spark, b) is other, combat.aim(f, p, spark, b))
    third = fighter("ally_ash", "ally", name="Ash")
    check("...while another striker's strike still reaches it", combat.reaches(f, b, by=third) and not combat.reaches(f, b, by=p))
    other.hp = 0
    check("...and with no other, at no one: the repeat is dropped", combat.aim(f, p, spark, b) is None)
check("...and once the action is over, the note is gone", combat.aim(f, p, spark, b) is b)

# ---- 4. a tick against every floor: each holds it, in a line that names the harm; a once-a-fight floor is spent by it
TICK = {}


def tick(name, make, dot="poisoned", setup=None, by=True):
    """A lethal tick at the start of x's turn: the fight, x, and what start_turn said."""
    p = fighter("player", "player", hp=10 ** 6)
    wolf = fighter("wolf 1", "enemy", dmg=0.001)
    x = make(p)
    f = fight(*([p, x] if x is not p else [p]), wolf, **(setup or {}))
    bf.engage(f, wolf, x)
    poison(f, x, wolf if by else None, 5000, dot)
    went = combat.start_turn(x, f, random.Random(3))
    TICK[name] = (f, x, went)
    return f, x, went


f, x, _ = tick("Lifeline", lifeline_ash)
check("a tick: Lifeline holds a companion the poison would end", x.alive and x.hp == 1 and x.counters.get("lifeline"), (x.hp, f.story))
check("...told with the harm named", "The poison should have ended Ash, but the bond with its master will not let it fall (Lifeline)" in f.story, f.story)
wolf = f.get("wolf 1")
wolf.weapon_damage = 40
for s in range(60):
    combat.apply_damage(f, wolf, x, 1.0, "bites", random.Random(s))
    if not x.alive:
        break
check("...and Lifeline, once a fight, is spent by the tick: the next killing blow ends Ash", not x.alive)

f, x, _ = tick("Soul Tether", tethered)
check("a tick: the Soul Tether holds, and is spent", x.alive and x.hp == 30 and x.tether == 0
      and "The poison should have ended Wisp, but a thread of the master's will draws it back from the brink (Soul Tether)" in f.story, (x.hp, f.story))

f, x, went = tick("Orenna's Last Breath", breathing, dot="burning")
check("a tick: Orenna's Last Breath holds a burn, and is spent", x.alive and x.hp == x.max_hp and not x.breath, (x.hp, x.breath))
check("...told in the owner's words", "The fire should have killed you, but a thin, tired warmth catches you, and you rise whole (Orenna's Last Breath, now spent)"
      in f.story, f.story)

f, x, _ = tick("Deathless", deathless_player, dot="burning")
check("a tick: Deathless holds a burn", x.alive and x.hp == 1
      and "The fire should have ended you, but you are held on the threshold and will not fall" in f.story, (x.hp, f.story))
poison(f, x, None, 5000, "burning")
f.round += 1
combat.start_turn(x, f, random.Random(4))
check("...every time", x.alive and x.hp == 1, x.hp)

f, x, _ = tick("Deathward", deathward_player)
check("a tick: Deathward holds a poison, and is spent", x.alive and x.hp == 11 and x.deathward_used
      and "The poison should have killed you, but a power older than death refuses to let go (Deathward)" in f.story, (x.hp, f.story))
wolf = f.get("wolf 1")
wolf.weapon_damage = 400
for s in range(60):
    combat.apply_damage(f, wolf, x, 1.0, "bites", random.Random(s))
    if not x.alive:
        break
check("...the next killing blow ends the wearer: Deathward was spent by the tick", not x.alive)


def boss_alone(p):
    b = boss_wolf(p)
    b.hp = 5
    return b


p = fighter("player", "player")
b = boss_alone(p)
f = fight(p, b)
poison(f, b, p, 5000)
combat.start_turn(b, f, random.Random(2))
check("a tick: a boss's last stand holds a poison (its statuses cleared, the poison with them)", b.alive and b.boss["stand_used"]
      and b.hp == round(b.max_hp * bosses.B["last_stand"]["hp_pct"] / 100) and "poisoned" not in b.statuses and told(f, "BOSS LAST STAND"), (b.hp, f.story))
poison(f, b, p, 5000)
f.round += 1
combat.start_turn(b, f, random.Random(3))
check("...and it is spent: the next tick ends the boss, with its fall", not b.alive and told(f, "BOSS FALLS"), f.story)

p = fighter("player", "player")
e = fighter("e1", "enemy", hp=5, max_hp=100, name="the bandit")
e.yields_at = 0.25
f = fight(p, e)
poison(f, e, p, 5000)
went = combat.start_turn(e, f, random.Random(2))
check("a tick: a yielding foe is held at its floor and yields, its turn gone", e.alive and e.hp >= 1 and e.fled and went is False
      and not falls(f, e), (e.hp, e.fled, went, f.story))

f, x, went = tick("the duel", lambda p: (setattr(p, "hp", 5), p)[1], setup={"duel": True})
check("a tick: the duel holds a duellist the poison would end, and decides the trial", x.alive and x.hp == 1 and f.over == "defeat", (x.hp, f.over))
check("...told as the duel's floor, the harm named", "The trial is called before the poison can end you, and the duel is decided" in f.story, f.story)
f, x, went = tick("the first hunt", lambda p: (setattr(p, "hp", 5), p)[1], setup={"mentor": True})
check("a tick: the first hunt holds the player, and counts the save", x.alive and x.hp == 1 and f.mentor_saved == 1
      and "The poison should have ended you, but a hand catches you before you fall" in f.story, (x.hp, f.mentor_saved, f.story))

# ---- 5. a torn wound against every floor, the blow itself short of killing: the tear is the blow's, and the floor holds it


def torn(make, setup=None, seeds=120):
    for seed in range(seeds):
        p = fighter("player", "player", hp=10 ** 6)
        wolf = fighter("wolf 1", "enemy", dmg=1)
        x = make(p)
        f = fight(*([p, x] if x is not p else [p]), wolf, **(setup or {}))
        bf.engage(f, wolf, x)
        hp0 = x.hp = 80
        x.max_hp = 100
        bleed(f, x, wolf, 5000)
        combat.apply_damage(f, wolf, x, 0.05, "bites", random.Random(seed))
        if landed(f, wolf):
            return f, x, hp0
    return None


for name, make, setup, after in (("Lifeline", lifeline_ash, None, lambda x: x.hp == 1),
                                 ("Deathless", deathless_player, None, lambda x: x.hp == 1),
                                 ("Deathward", deathward_player, None, lambda x: x.hp == 11 and x.deathward_used),
                                 ("the Soul Tether", tethered, None, lambda x: x.hp == 30),
                                 ("Orenna's Last Breath", breathing, None, lambda x: x.hp == x.max_hp and not x.breath),
                                 ("the first hunt", lambda p: p, {"mentor": True}, lambda x: x.hp == 1)):
    got = torn(make, setup)
    check(f"a torn wound: {name} holds it", got is not None and got[1].alive and after(got[1]), (got[1].hp, got[0].story) if got else None)
got = torn(lambda p: p, {"duel": True})
check("a torn wound: the duel holds it, and the tear decides the trial (not the next blow)", got is not None and got[1].hp == 1
      and got[0].over == "defeat", (got[1].hp, got[0].over) if got else None)

# ---- 6. a rebound against every floor: the striker's own force, turned back by Retribution


def rebounded(make, setup=None, seeds=120, wearer_side="player"):
    """x strikes someone wearing Retribution; what came back would end x."""
    for seed in range(seeds):
        p = fighter("player", "player", hp=10 ** 6)
        x = make(p)
        if x.side == "enemy":
            p.legendary["retribution"] = 100
            wearer, others = p, [x]
        else:
            wearer = fighter("e1", "enemy", hp=10 ** 6, name="the knight")
            wearer.legendary["retribution"] = 100
            others = [x, wearer] if x is not p else [wearer]
        f = fight(p, *others, **(setup or {}))
        bf.engage(f, x, wearer)
        x.weapon_damage = 40
        combat.apply_damage(f, x, wearer, 1.0, "strikes", random.Random(seed))
        if landed(f, x):
            return f, x
    return None


def deathless_wolf(p):
    w = fighter("wolf 1", "enemy", hp=5, max_hp=100)
    w.legendary["deathless"] = 1
    return w


def deathward_wolf(p):
    w = fighter("wolf 1", "enemy", hp=5, max_hp=100)
    w.legendary["deathward"] = 10
    return w


def yielding_wolf(p):
    w = fighter("wolf 1", "enemy", hp=5, max_hp=100)
    w.yields_at = 0.25
    return w


for name, make, setup, after, line in (
        ("Deathless", deathless_wolf, None, lambda x: x.hp == 1, "The force should have ended the first wolf, but it is held on the threshold and will not fall"),
        ("Deathward", deathward_wolf, None, lambda x: x.hp == 11 and x.deathward_used, "older than death"),
        ("a yielding foe", yielding_wolf, None, lambda x: x.fled, ""),
        ("a boss's last stand", boss_alone, None, lambda x: x.boss["stand_used"], "BOSS LAST STAND"),
        ("Lifeline", lambda p: (p.legendary.__setitem__("lifeline", 1), fighter("ally_ash", "ally", hp=5, max_hp=100, name="Ash"))[1], None,
         lambda x: x.hp == 1, "The force should have ended Ash, but the bond with its master will not let it fall (Lifeline)"),
        ("the Soul Tether", tethered, None, lambda x: x.hp == 30, "draws it back from the brink"),
        ("Orenna's Last Breath", breathing, None, lambda x: x.hp == x.max_hp, "tired warmth"),
        ("the first hunt", lambda p: (setattr(p, "hp", 5), p)[1], {"mentor": True}, lambda x: x.hp == 1, "a hand catches you before you fall"),
        ("the duel", lambda p: (setattr(p, "hp", 5), p)[1], {"duel": True}, lambda x: x.hp == 1,
         "The trial is called before the force can end you, and the duel is decided")):
    got = rebounded(make, setup)
    check(f"a rebound: {name} holds the striker's own force", got is not None and got[1].alive and after(got[1])
          and (not line or told(got[0], re.escape(line))) and not told(got[0], "undone by"), (got[1].hp, got[0].story) if got else None)

# ---- 7. side harm meets every floor as it always has: a guard's share, thorns, a curse at the turn's start
got = None
for seed in range(120):
    p = fighter("player", "player", hp=10 ** 6)
    p.legendary.update({"guarded": 90, "lifeline": 1})
    ash, wolf = fighter("ally_ash", "ally", hp=1, max_hp=60, name="Ash"), fighter("wolf 1", "enemy", dmg=40)
    f = fight(p, ash, wolf)
    bf.engage(f, wolf, p)
    combat.apply_damage(f, wolf, p, 1.0, "attacks", random.Random(seed))
    if ash.counters.get("lifeline"):
        got = ash
        break
check("side harm: Lifeline holds a guard the share would end, and calls it the blow it took for the player", got is not None and got.alive
      and got.hp == 1 and told(f, r"^The blow should have ended Ash, but the bond"), f.story)
got = None
for seed in range(120):
    p = fighter("player", "player", hp=10 ** 6, armor=200)
    p.legendary["thorns"] = 100
    w = deathward_wolf(p)
    w.weapon_damage = 10
    f = fight(p, w)
    bf.engage(f, w, p)
    combat.apply_damage(f, w, p, 1.0, "attacks", random.Random(seed))
    if w.deathward_used:
        got = w
        break
check("side harm: Deathward holds the striker its thorns would end, told as the thorns", got is not None and got.alive and got.hp == 11
      and told(f, r"^The thorns should have killed the first wolf, but a power older than death"), f.story)
p, w = fighter("player", "player"), deathless_wolf(None)
f = fight(p, w)
f.round = 2
fx.put_curse(w, dict(by="player", per=500, left=2, name="Withering Curse", tier="moderate", element="", exprs=[]))
combat.start_turn(w, f, random.Random(1))
check("side harm: Deathless holds a curse at the turn's start, told as the curse after the curse's own line", w.alive and w.hp == 1
      and "The curse should have ended the first wolf, but it is held on the threshold and will not fall" in f.story
      and not told(f, r"^The blow should have"), f.story)
i = next((k for k, s in enumerate(f.story) if s.startswith("The curse should have")), -1)
check("...the curse's own line just before it", i > 0 and f.story[i - 1].startswith("Withering Curse gnaws at the first wolf"), f.story)
p, w = fighter("player", "player"), deathless_wolf(None)
f = fight(p, w)
combat.side_damage(f, w, 500, p, random.Random(1), "magical", told="the sky falls on the first wolf")
check("side harm with no word of its own: the floor says 'that', after the harm's own line",
      f.story[-2:] == ["The sky falls on the first wolf", "That should have ended the first wolf, but it is held on the threshold and will not fall"],
      f.story)
p = fighter("player", "player")
e = fighter("e1", "enemy", name="the examiner")
f = fight(p, e, duel=True)
combat.side_damage(f, e, 10 ** 6, p, random.Random(1), "magical", told="the sky falls on the examiner")
check("...and the duel's floor, with no word for the harm", "The trial is called before the examiner can fall, and the duel is decided"
      in f.story and f.over == "victory", (f.story, f.over))

# ---- 8. what the earlier builders left for this one
got = None                                                    # (f768) a felled defender's thorns and Frost Armor answer nothing
for seed in range(120):
    p = fighter("player", "player")
    ash = fighter("ally_ash", "ally", hp=1, max_hp=60, name="Ash", armor=200)
    ash.legendary.update({"thorns": 100, "frost_armor": 1})
    wolf = fighter("wolf 1", "enemy", hp=1000, dmg=40)
    f = fight(p, ash, wolf)
    bf.engage(f, wolf, ash)
    combat.apply_damage(f, wolf, ash, 1.0, "bites", random.Random(seed))
    if not ash.alive:
        got = (f, wolf)
        break
check("(a seed where the bite fells Ash)", got is not None)
if got:
    f, wolf = got
    check("a defender the blow felled answers nothing: no thorns, no Frost Armor on the wolf", wolf.hp == 1000 and "slowed" not in wolf.statuses
          and not told(f, r"\(Thorns\)|\(Frost Armor\)"), (wolf.hp, wolf.statuses, f.story))

# (f769) a foe that yields at its own turn's start takes nothing more of it: no frostbite, no seed, no corrosion, no tick
p = fighter("player", "player")
e = fighter("e1", "enemy", hp=55, max_hp=100, name="the bandit")
e.yields_at = 0.5
f = fight(p, e)
f.round = 2
fx.put_curse(e, dict(by="player", per=10, left=2, name="Withering Curse", tier="moderate", element="", exprs=[]))
poison(f, e, p, 5000)
fx.put_status(e, "slowed", 3)
e.counters.update({"frostbite": ["player", 50], "seed": ["player", 1, 500, "Seedburst"], "creeping": [3, 10]})
went = combat.start_turn(e, f, random.Random(1))
check("a foe that yields at its turn's start (the curse) takes nothing more of that start: no tick, no frostbite, no seed, no corrosion",
      went is False and e.alive and e.fled and e.hp > 1 and not e.corroded and "seed" in e.counters
      and not told(f, r"Frostbite|Seedburst|Creeping Corrosion") and not falls(f, e), (e.hp, e.corroded, e.counters, f.story))

p = fighter("player", "player")                               # ...driven off by the frostbite: no creeping corrosion after it
e = fighter("e1", "enemy", hp=55, max_hp=100, name="the bandit")
e.yields_at = 0.5
f = fight(p, e)
f.round = 2
fx.put_status(e, "slowed", 3)
e.counters.update({"frostbite": ["player", 10], "creeping": [3, 10]})
went = combat.start_turn(e, f, random.Random(1))
check("a foe the frostbite drives off at its turn's start is not corroded after it", went is False and e.fled and not e.corroded
      and not told(f, "Creeping Corrosion"), (e.corroded, f.story))
p = fighter("player", "player")                               # ...driven off by burning ground: no caustic pool after it
e = fighter("e1", "enemy", hp=55, max_hp=100, name="the bandit")
e.yields_at = 0.5
f = fight(p, e)
f.round = 2
fx.put_ground(f, e.zone_id, "burning_ground", {"until": 9, "by": "player", "power": 100, "pct": 10, "name": "Wildfire"})
fx.put_ground(f, e.zone_id, "caustic_pool", {"until": 9, "by": "player", "pct": 20, "name": "Acid Pool"})
went = combat.start_turn(e, f, random.Random(1))
check("a foe burning ground drives off at its turn's start is not corroded by the pool after it", went is False and e.fled
      and not e.corroded and not told(f, "Acid Pool"), (e.corroded, f.story))

# (f769) a striker that falls or yields at its own blow carries nothing on: no venom from a dead spider, no boss's follow-through
got = None
for seed in range(120):
    p = fighter("player", "player", hp=10 ** 6, armor=200)
    p.legendary["thorns"] = 100
    spider = fighter("spider 1", "enemy", hp=1, max_hp=40, family="venomous", behaviors={"venom": 100}, dmg=5)
    f = fight(p, spider)
    bf.engage(f, spider, p)
    combat.enemy_turn(f, spider, random.Random(seed))
    if not spider.alive and landed(f, spider):
        got = (f, p)
        break
check("(a seed where the spider's bite lands and the thorns kill it)", got is not None)
if got:
    check("a spider felled by the thorns its own bite met lays no venom", "poisoned" not in got[1].statuses, got[1].statuses)
got = None
for seed in range(120):
    p = fighter("player", "player", hp=10 ** 6, armor=200)
    p.legendary["thorns"] = 100
    spider = fighter("spider 1", "enemy", hp=60, max_hp=100, family="venomous", behaviors={"venom": 100}, dmg=5)
    spider.yields_at = 0.5
    f = fight(p, spider)
    bf.engage(f, spider, p)
    combat.enemy_turn(f, spider, random.Random(seed))
    if spider.fled and landed(f, spider):
        got = (f, p)
        break
check("(a seed where the thorns its own bite met make the spider yield)", got is not None)
if got:
    check("a spider that yields at its own bite lays no venom", "poisoned" not in got[1].statuses, got[1].statuses)

BLOWS = []
_apply = combat.apply_damage


def counted(c, att, dfn, *a, **k):
    BLOWS.append((att.id, att.alive and not att.fled))
    return _apply(c, att, dfn, *a, **k)


got = None
for seed in range(120):
    p = fighter("player", "player", hp=10 ** 6, armor=200)
    p.legendary["thorns"] = 100
    boss = fighter("boss", "enemy", hp=60, max_hp=100, name="the captain", category="hostile people", dmg=5)
    boss.boss = bosses.make(bosses.kit_for("hostile people"), "captain", "the captain")
    boss.yields_at = 0.5
    f = fight(p, boss)
    bf.engage(f, boss, p)
    BLOWS.clear()
    combat.apply_damage = counted
    try:
        combat.enemy_turn(f, boss, random.Random(seed))
    finally:
        combat.apply_damage = _apply
    if boss.fled:
        got = BLOWS[:]
        break
check("(a seed where the boss yields to the thorns its own blow met)", got is not None)
if got:
    check("...and takes no follow-through and no signature after it", len([b for b in got if b[0] == "boss"]) == 1, got)

# (f770) a striker felled by its own blow stops striking: a boss's sweep, a swarm's, a breath
for name, run in (
        ("a boss's legendary sweep", lambda f, e, rng: bosses._do(f, e, {"kind": "sweep", "name": "Sweep", "text": "{name} sweeps"}, rng, 1.0)),
        ("a swarm's sweep", lambda f, e, rng: behaviors.sweeps(f, e, rng)),
        ("a breath", lambda f, e, rng: behaviors._area(f, e, rng, 1.0, "breath", "it breathes"))):
    got = None
    for seed in range(120):
        p = fighter("player", "player", hp=10 ** 6, armor=200)
        p.legendary["thorns"] = 100
        allies = [fighter(f"ally_{i}", "ally", hp=10 ** 6, name=n) for i, n in enumerate(("Ash", "Bryn", "Cole"))]
        e = fighter("e1", "enemy", hp=1, max_hp=40, family="swarm", behaviors={"sweep": 1.0}, dmg=10, reach="melee")
        e.boss = bosses.make("default", "captain", "the swarm") if "boss" in name else {}
        f = fight(p, *allies, e)
        for a in [p] + allies:
            bf.engage(f, e, a)
        BLOWS.clear()
        combat.apply_damage = counted
        try:
            run(f, e, random.Random(seed))
        finally:
            combat.apply_damage = _apply
        if not e.alive:
            got = BLOWS[:]
            break
    check(f"(a seed where the thorns fell the striker in {name})", got is not None)
    if got:
        check(f"{name}: no blow comes from the striker after it fell", all(up for who_, up in got if who_ == "e1"), got)

# ---- 9. the floors declared once: the table, every path held to it both ways, and the stages that read it
ST = yaml.safe_load(open("data/rules/stages.yaml", encoding="utf-8"))
CB = yaml.safe_load(open("data/rules/combat.yaml", encoding="utf-8"))
TABLE = ST.get("floors") or {}
PATHS = ST["damage"]
OWNER = ["duel_floor", "lifeline", "tether", "boss_last_stand", "breath", "mentor_floor", "deathless", "deathward", "yields_floor"]
check("stages.yaml declares the floors once, in a table beside the paths, in the order a path meets them", list(TABLE) == OWNER, list(TABLE))
check("...the rebound is a path of its own, the force turned back: its floors, its health, the fall", "rebound" in PATHS
      and "rebound" not in PATHS.get("rebound", []), PATHS.get("rebound"))
check("...and by the owner's answer every floor holds every harm: each row names every path", bool(TABLE)
      and all(sorted(r) == sorted(PATHS) for r in TABLE.values()), TABLE)
check("...each path names exactly the floors its rows give it, in the table's order", bool(TABLE)
      and all([s for s in ids if s in TABLE] == [fl for fl in TABLE if p_ in TABLE[fl]] for p_, ids in PATHS.items()), PATHS)
check("the tree passes the check", data_check.tables_problems() == [], data_check.tables_problems())
for p_, fl in (("dot_tick", "lifeline"), ("tear", "deathward"), ("rebound", "duel_floor")):
    gone = copy.deepcopy(ST)
    gone["damage"][p_] = [s for s in gone["damage"].get(p_, []) if s != fl]
    probs = data_check.tables_problems(ST=gone)
    check(f"...and refuses a {p_} path missing the floor {fl} its row gives it", any(fl in x and p_ in x for x in probs), probs)
    gone = copy.deepcopy(ST)
    if gone.get("floors"):
        gone["floors"][fl] = [x for x in gone["floors"][fl] if x != p_]
    probs = data_check.tables_problems(ST=gone)
    check(f"...and a {p_} path naming {fl} that its row does not give it", any(fl in x and p_ in x for x in probs), probs)
gone = copy.deepcopy(ST)
ids = gone["damage"]["blow"]
i, j = ids.index("lifeline"), ids.index("deathless")
ids[i], ids[j] = ids[j], ids[i]
probs = data_check.tables_problems(ST=gone)
check("...a floor out of the table's order", any("order" in x and "damage.blow" in x for x in probs), probs)
gone = copy.deepcopy(ST)
gone.setdefault("floors", {})["moon_ward"] = list(PATHS)
gone["floors"]["lifeline"] = list(gone["floors"].get("lifeline", [])) + ["drowning"]
probs = data_check.tables_problems(ST=gone)
check("...a floor no stage runs, and a harm no path is", any("moon_ward" in x for x in probs) and any("drowning" in x for x in probs), probs)
check("the code's floors are the table's (what the fall's fence reads)", tuple(getattr(damage, "FLOORS", ())) == tuple(TABLE), getattr(damage, "FLOORS", ()))
check("the bypasses' second floor is gone: no tick_floor, no tick_duel_end", "tick_floor" not in damage.STAGES and "tick_duel_end" not in damage.STAGES)
check("the rebound stage writes no health of its own and holds no floor by hand", ".hp" not in inspect.getsource(damage.rebound)
      and "duel_holds" not in inspect.getsource(damage.rebound))
check("every floor reads what is about to land through the one accessor", all("landing" in inspect.getsource(damage.STAGES[s]) for s in OWNER if s in damage.STAGES))
TICKS, HARMS = CB.get("ticks") or {}, CB.get("harms") or {}
check("every word a floor's line calls a harm by is in one table (combat.yaml harms): the blow, the force, each tick's, 'that'",
      HARMS.get("blow") == "the blow" and HARMS.get("rebound") == "the force" and HARMS.get("poisoned") == "the poison"
      and HARMS.get("burning") == "the fire" and HARMS.get("unnamed") == "that" and all(t in HARMS for t in TICKS), HARMS)
check("...and engine/damage.py keeps keys, not words: each path's harm is a key of the table", not hasattr(damage, "HARM")
      and set(getattr(damage, "PATH_HARM", {"x": "x"}).values()) <= set(HARMS), getattr(damage, "PATH_HARM", None))
bare = copy.deepcopy(CB)
bare["harms"].pop("poisoned")
bare["harms"]["thorns"] = "the thorns - sharp"
probs = data_check.tables_problems(CB=bare)
check("...and the check refuses a ticking status with no word, and a dash", any("harms.poisoned" in x for x in probs)
      and any("harms.thorns" in x and "dash" in x for x in probs), probs)
import pathlib
named = set()
for rel in ("engine/combat.py", "engine/spellcraft.py", "engine/combat_perks.py", "engine/summons.py", "engine/relics.py"):
    named |= set(re.findall(r"\bharm=\"(\w+)\"", pathlib.Path(rel).read_text(encoding="utf-8")))
named |= {"burning_ground", "static_field"}                    # zone_turn names its ground by the ground's own id
check("every side harm a caller names has its word in the table", bool(named) and named <= set(HARMS), sorted(named - set(HARMS)))

# ---- 10. the blow's note is held on the fight, never in its row
PEEK = {}
from engine import combat_perks
_after_hit = combat_perks.after_hit


def peek(c, *a, **k):
    PEEK.update(json=c.model_dump_json(), open=list(getattr(c, "_open", None) or []))
    return _after_hit(c, *a, **k)


p = fighter("player", "player")
p.legendary["lifeline"] = 1
ash = fighter("ally_ash", "ally", hp=5, max_hp=100, name="Ash")
wolf = fighter("wolf 1", "enemy", dmg=40)
f = fight(p, ash, wolf)
bf.engage(f, wolf, ash)
for seed in range(60):
    combat_perks.after_hit = peek
    try:
        combat.apply_damage(f, wolf, ash, 1.0, "bites", random.Random(seed))
    finally:
        combat_perks.after_hit = _after_hit
    if ash.counters.get("lifeline"):
        break
held = [o for o in PEEK.get("open", []) if hasattr(o, "floored")]
check("the floor's note is on the blow in progress, mid-blow", bool(held) and any(x is ash for o in held for x in o.floored), PEEK.get("open"))
check("...and never in the fight's row", "floored" not in PEEK.get("json", "floored"))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
