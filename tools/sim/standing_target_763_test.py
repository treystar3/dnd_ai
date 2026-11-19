"""(f763) An ability lands only on a fighter still in the fight, and no blow fells anyone twice (found by the code audit,
fight-abilities-1: with Spell Echo, Triumph and Soul Harvest, a third cast that killed its target was repeated onto the corpse; the
foe fell twice, the kill paid 80 health where one Triumph is 40 and 1000 mana where one harvest is 500, and two other foes stood
untouched). The kind: anything that hands an ability, a blow or an element's effect a target who is down, fled or turned. Three
doors ask one predicate, combat.in_fight: act_ability aims an ability that needs a foe at the nearest foe still standing (a perk's
repeat with nobody left is dropped and not told, one that went is told once and before what it did, a paid cast is refused
before the cost); an element's effect, a rider and a maneuver do nothing to a foe who yielded or fled at this very blow (the
effects that work on a kill keep their work); and a blow handed a defender who is down or gone draws no die and lands nothing.
The finder's case, then the rest of the kind: Grave Chorus (never the fallen; its line counts the repeats that went), a strike, a
volley and a grapple handed a fallen or fled foe, a cast with nobody left, a flurry's and a volley's later hits on a foe that
yielded at the first, Dominate, a mark and Death's Door on a foe that yields at the blow, a grappling rider on one, a table of every
element effect, a blessing named at a stale foe (still its caster's, not refused), a blow straight at the fallen, an area cast
whose kills rout the rest, and what must still pass (No One Escapes, a thrall raised).
Run: python tools/sim/standing_target_763_test.py"""
import random
import re
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from engine import battlefield as bf
from engine import battlefield_builder as bb
from engine import behaviors
from engine import combat
from engine import spellcraft
from engine.combat import Move

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def player(*mechs, moves=(), hp=400, mana=1000, dmg=10, **kw):
    pairs = [x if isinstance(x, tuple) else (x, 1) for x in mechs]
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: 14 for a in combat.ATTRIBUTES}, hp=hp,
                          max_hp=kw.pop("max_hp", hp), stamina=10 ** 4, max_stamina=10 ** 4, mana=mana, max_mana=kw.pop("max_mana", mana),
                          weapon_damage=dmg, hold=2, legendary=dict(pairs), mech_names={m: m.replace("_", " ").title() for m, _ in pairs},
                          moves=list(moves), **kw)


def foe(i, hp=10 ** 6, fearless=True, **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp,
                          max_hp=kw.pop("max_hp", hp), weapon_damage=8, category=kw.pop("category", "hostile people"),
                          behaviors={"fearless": 1} if fearless else {}, **kw)


def fight(*fs):
    f = combat.Combat(fighters=list(fs), record=True, serial="st")
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    f.opened = True
    return f


def spell(mid, **kw):
    kw.setdefault("reach", "ranged")
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=kw.pop("effect", "damage"), tier=kw.pop("tier", "light"),
                resource="mana", attribute="intelligence", **kw)


def skill(mid, **kw):
    kw.setdefault("reach", "melee")
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=kw.pop("effect", "damage"), tier=kw.pop("tier", "moderate"),
                resource="stamina", **kw)


def hits_on(f, who, since=0):
    return [h for h in f.hits[since:] if h["dfn"] == who.name]


ROLLS: list[tuple] = []                  # every attack roll: (attacker, defender, the defender still in the fight when it was rolled)
_roll = combat.roll_attack


def _spy(att, dfn, combat_, rng, trace=None):
    ROLLS.append((att.name, dfn.name, dfn.alive and not dfn.fled))
    return _roll(att, dfn, combat_, rng, trace=trace)


combat.roll_attack = _spy


def on_the_gone(since):
    """The attack rolls since this mark made against a defender who was down or gone when it was rolled."""
    return [r[:2] for r in ROLLS[since:] if not r[2]]


def placed(f, h0, pick):
    """Where the story lines that pick takes stand, and where each blow recorded since h0 was told (-1 when it was not)."""
    lines = [i for i, s in enumerate(f.story) if pick(s)]
    blows = [next((i for i, s in enumerate(f.story) if f"[{h['tag']}]" in s), -1) for h in f.hits[h0:]]
    return lines, blows


CHORUS = re.compile(r"(\d+) spectral echo(?:es)? repeats? the working")


def chorus_told(f, h0):
    """None when the Grave Chorus line is told once, its number the repeats that went (the blows after the working's own), after
    the working's blow and before the first repeat's; else what was seen."""
    lines, blows = placed(f, h0, lambda s: CHORUS.match(s) is not None)
    ok = len(lines) == 1 and len(blows) >= 2 and -1 < blows[0] < lines[0] < blows[1] \
        and int(CHORUS.match(f.story[lines[0]]).group(1)) == len(blows) - 1
    return None if ok else (lines, blows, f.story[-8:])


fire = spell("firebolt", element="fire")

# ---- 1. the finder's case: Spell Echo's repeat of a third cast that killed its target (fight-abilities-1)
killed = twice = paid_wrong = idle = repeated = misplaced = 0
seen = where = None
for sd in range(1, 41):
    p = player("spell_echo", ("triumph", 10), ("soul_harvest", 10), moves=[fire], max_mana=5000)
    p.hp = 100
    f = fight(p, foe(1), foe(2, hp=5), foe(3))
    rng = random.Random(sd)
    e1, e2, e3 = f.get("e1"), f.get("e2"), f.get("e3")
    combat.act_ability(f, p, fire, e1, rng)
    combat.act_ability(f, p, fire, e1, rng)
    log0, r0, hp0, mana0, h0 = len(f.log), len(ROLLS), p.hp, p.mana, len(f.hits)
    cost = combat.cost_of(p, fire, f)
    combat.act_ability(f, p, fire, e2, rng)
    rolls = ROLLS[r0:]
    if len(rolls) == 2 and rolls[1][2]:                   # the repeat went, at a foe still standing: told once, between the blows
        repeated += 1
        lines, blows = placed(f, h0, lambda s: "three times running" in s)
        if len(lines) != 1 or len(blows) != 2 or not -1 < blows[0] < lines[0] < blows[1]:
            misplaced += 1
            where = where or (lines, blows, f.story[-8:])
    if e2.alive:
        continue
    killed += 1
    falls = f.log[log0:].count("foe 2 falls")
    twice += falls >= 2
    paid_wrong += (p.hp - hp0, round(p.mana - mana0 + cost)) != (40, 500)
    idle += len(ROLLS) - r0 != 2 or bool(on_the_gone(r0))
    seen = seen or (falls, p.hp - hp0, round(p.mana - mana0 + cost), ROLLS[r0:])
check("(the third cast kills its target in most seeds)", killed >= 30, killed)
check("Spell Echo: the foe the third cast killed falls once, never twice", twice == 0, f"twice in {twice} of {killed}; first: {seen}")
check("Spell Echo: one death pays one Triumph (40) and one Soul Harvest (500)", paid_wrong == 0, f"{paid_wrong} of {killed}; first: {seen}")
check("Spell Echo: the repeat goes at a foe still in the fight, never the fallen", idle == 0,
      f"{idle} of {killed}; first (falls, health, mana, rolls): {seen}")
check("(the repeat goes at a foe still standing in most seeds)", repeated >= 30, repeated)
check("Spell Echo: a repeat that went is told once, after the third cast's blow and before its own", misplaced == 0,
      f"{misplaced} of {repeated}; first (lines, blows, story): {where}")

# the third cast kills the last foe at its first resolution: the repeat is dropped, and not told as happening
first_kills = wrong = 0
shown = None
for sd in range(1, 41):
    p = player("spell_echo", ("triumph", 10), moves=[fire])
    f = fight(p, foe(1))
    e1 = f.get("e1")
    rng = random.Random(sd)
    combat.act_ability(f, p, fire, e1, rng)
    combat.act_ability(f, p, fire, e1, rng)
    e1.hp = 5
    s0, r0 = len(f.story), len(ROLLS)
    combat.act_ability(f, p, fire, e1, rng)
    rolls = ROLLS[r0:]
    if e1.alive or (len(rolls) > 1 and rolls[1][2]):
        continue                                          # the first resolution missed: the repeat rightly went at it
    first_kills += 1
    told = [s for s in f.story[s0:] if "three times running" in s]
    falls = sum(1 for s in f.story[s0:] if "does not rise" in s)
    if len(rolls) != 1 or told or falls != 1:
        wrong += 1
        shown = shown or (rolls, f.story[s0:])
check("(the third cast kills the last foe at its first resolution in some seeds)", first_kills >= 10, first_kills)
check("Spell Echo on the last foe: it falls once, no repeat is struck and none is told", wrong == 0, f"{wrong} of {first_kills}; first: {shown}")

# ---- 2. Grave Chorus: the repeat never strikes the fallen (which standing foe it strikes is not held)
fell_again = chorus = chorus_wrong = 0
chorus_seen = None
for sd in range(1, 21):
    p = player("grave_chorus", moves=[fire], dmg=10 ** 5)
    f = fight(p, foe(1, hp=10), foe(2, hp=5), foe(3))
    rng = random.Random(sd)
    combat.act_attack(f, p, f.get("e1"), rng)
    if p.counters.get("echoes") != 1:
        continue
    e2 = f.get("e2")
    r0, log0, h0 = len(ROLLS), len(f.log), len(f.hits)
    combat.act_ability(f, p, fire, e2, rng)
    if not e2.alive and (on_the_gone(r0) or f.log[log0:].count("foe 2 falls") != 1 or len(ROLLS) - r0 < 2):
        fell_again += 1
    chorus += 1                                           # a foe stands for every repeat here: each goes, and the line is told
    told = chorus_told(f, h0)
    chorus_wrong += told is not None
    chorus_seen = chorus_seen or told
check("Grave Chorus: the repeat of a working that killed goes at a foe still standing, never the fallen", fell_again == 0, fell_again)
check("(Grave Chorus: seeds where the repeat goes)", chorus >= 10, chorus)
check("Grave Chorus: the repeats that went are told once, their number right, after the working's blow and before theirs",
      chorus_wrong == 0, f"{chorus_wrong} of {chorus}; first (lines, blows, story): {chorus_seen}")

# more echoes wait than there are foes left to take them: the line counts the repeats that went, not the echoes
fewer = off = 0
off_seen = None
for sd in range(1, 41):
    p = player("grave_chorus", moves=[fire])
    f = fight(p, foe(1, hp=5), foe(2, hp=5))
    p.counters["echoes"] = 2
    h0 = len(f.hits)
    combat.act_ability(f, p, fire, f.get("e1"), random.Random(sd))
    fewer += len(f.hits) - h0 - 1 < 2
    told = chorus_told(f, h0)
    off += told is not None
    off_seen = off_seen or told
check("(Grave Chorus: seeds where fewer repeats go than echoes wait)", fewer >= 5, fewer)
check("Grave Chorus with more echoes than foes left: the line counts the repeats that went, told before the first",
      off == 0, f"{off} of 40; first (lines, blows, story): {off_seen}")

# the working kills the last foe: no repeat is struck, and none is told
last_kills = told_idle = 0
for sd in range(1, 21):
    p = player("grave_chorus", moves=[fire])
    f = fight(p, foe(1, hp=5))
    p.counters["echoes"] = 1
    s0, r0 = len(f.story), len(ROLLS)
    combat.act_ability(f, p, fire, f.get("e1"), random.Random(sd))
    if f.get("e1").alive or (len(ROLLS) - r0 > 1 and ROLLS[r0 + 1][2]):
        continue                                          # the working missed: the repeat rightly went at the foe
    last_kills += 1
    told_idle += len(ROLLS) - r0 != 1 or any("repeat" in s and "the working" in s for s in f.story[s0:])
check("(the working kills the last foe in some seeds)", last_kills >= 5, last_kills)
check("Grave Chorus with nobody left: no repeat is struck and none is told", told_idle == 0, f"{told_idle} of {last_kills}")

# ---- 3. a strike, a volley and a grapple handed a fallen or fled foe straight at the engine: re-aimed, nothing lands on it
strike = skill("strike")
volley = skill("volley_shot", shape="volley")
grab = skill("grab", rider="grapple", tier="heavy")
for mv in (strike, volley, grab):
    for state in ("fallen", "fled"):
        p = player(moves=[mv])
        gone, other = foe(1, hp=100), foe(2)
        f = fight(p, gone, other)
        bf.engage(f, p, gone)
        bf.engage(f, p, other)
        if state == "fallen":
            gone.hp = 0.0
        else:
            gone.fled = True
        bf.release(f, gone)
        hp0, r0 = gone.hp, len(ROLLS)
        res = combat.act_ability(f, p, mv, gone, random.Random(7))
        check(f"{mv.name} handed a {state} foe: nothing lands on it and nobody is left grappled",
              res is None and not on_the_gone(r0) and gone.hp == hp0 and "grappled" not in gone.statuses and bf.validate(f) == [],
              (res, ROLLS[r0:], dict(gone.statuses), bf.validate(f)))
        check(f"{mv.name} handed a {state} foe: it goes at the foe still standing", bool(hits_on(f, other)), [h["dfn"] for h in f.hits])

# with nobody left to aim at: a paid cast is refused before the cost
for mv in (fire, strike):
    p = player(moves=[mv])
    gone = foe(1, hp=100)
    f = fight(p, gone)
    gone.hp = 0.0
    pools = (p.mana, p.stamina, dict(p.cooldowns), p.spells_cast)
    res = combat.act_ability(f, p, mv, gone, random.Random(7))
    check(f"{mv.name} named at the fallen with nobody standing: refused, and nothing is paid",
          isinstance(res, str) and res and (p.mana, p.stamina, dict(p.cooldowns), p.spells_cast) == pools and not f.hits,
          (res, pools, (p.mana, p.stamina, dict(p.cooldowns), p.spells_cast)))
    check(f"{mv.name}: the refusal has no dash", isinstance(res, str) and "-" not in res and "\u2014" not in res, res)


# ---- 4. a later hit on a foe that yielded at the first
def yielded_after(mv, seeds=40):
    """Over seeds where a hit makes the foe yield: in how many a later hit was rolled at it after it left, and the first case."""
    n = after = 0
    first = None
    for sd in range(1, seeds + 1):
        p = player(moves=[mv], dmg=14)
        y = foe(1, hp=200, yields_at=0.97)
        f = fight(p, y, foe(2))
        bf.engage(f, p, y)
        r0 = len(ROLLS)
        combat.act_ability(f, p, mv, y, random.Random(sd))
        if not y.fled:
            continue
        n += 1
        late = on_the_gone(r0)
        after += bool(late)
        first = first or (late, ROLLS[r0:])
    return n, after, first


for mv in (skill("flurry_of_blows", martial_form="flurry", hits=3), skill("volley_of_cuts", shape="volley")):
    n, after, first = yielded_after(mv)
    check(f"({mv.name}: seeds where the first hit makes the foe yield)", n >= 10, n)
    check(f"{mv.name}: no later hit lands on a foe that yielded at the first", after == 0, f"{after} of {n}; first: {first}")


# ---- 5. an element's effect, a rider and a maneuver on a foe that yields at this very blow
def yielding_cast(mv, category="hostile people", seeds=40, hp=200, max_hp=200, everyone=False):
    """The cases where the blow made the foe yield: (the foe, the fight) for each; with everyone, also those where it did not
    survive, so a kill after the yield is counted."""
    out = []
    for sd in range(1, seeds + 1):
        p = player(moves=[mv], dmg=14)
        y = foe(1, hp=hp, max_hp=max_hp, yields_at=0.97, category=category)
        f = fight(p, y, foe(2), foe(3))
        bf.engage(f, p, y)
        combat.act_ability(f, p, mv, y, random.Random(sd))
        if y.fled and (y.alive or everyone):
            out.append((y, f))
    return out


dom = spell("command_the_dead", element="necrotic", expressions=["dominate"])
cases = yielding_cast(dom, category="undead")
check("(Dominate: seeds where the blow makes the foe yield)", len(cases) >= 10, len(cases))
check("Dominate on a foe that yields at the blow: nothing turns and no turning is told",
      all(not y.counters.get("turned") and not any("turns on its own side" in s for s in f.story) for y, f in cases),
      [(y.counters, f.story[-3:]) for y, f in cases if y.counters.get("turned")][:1])
mark = spell("doom_mark", element="necrotic", expressions=["marked_for_death"])
cases = yielding_cast(mark)
check("(a mark: seeds where the blow makes the foe yield)", len(cases) >= 10, len(cases))
check("a mark on a foe that yields at the blow: it is not marked", all("marked" not in y.statuses for y, f in cases),
      [dict(y.statuses) for y, f in cases if "marked" in y.statuses][:1])
door = spell("deaths_grip", element="necrotic", expressions=["deaths_door"])
cases = yielding_cast(door, hp=25, max_hp=200, everyone=True)                 # under Death's Door's 15% when the blow lands
check("(Death's Door: seeds where the blow takes the foe under 15% and it yields)", len(cases) >= 10, len(cases))
check("Death's Door on a foe that yields at the blow: it is not killed", all(y.alive for y, f in cases),
      [(y.hp, f.story[-3:]) for y, f in cases if not y.alive][:1])
grab_cases = yielding_cast(skill("seize", rider="grapple", tier="heavy"))
check("(a grappling rider: seeds where the blow makes the foe yield)", len(grab_cases) >= 10, len(grab_cases))
check("a grappling rider on a foe that yields at the blow: it is not held, nor tied to the striker",
      all("grappled" not in y.statuses and bf.validate(f) == [] for y, f in grab_cases),
      [(dict(y.statuses), bf.validate(f)) for y, f in grab_cases if "grappled" in y.statuses or bf.validate(f)][:1])
pin_cases = yielding_cast(skill("pin_down", maneuver="pin", tier="heavy"))
check("(a pinning maneuver: seeds where the blow makes the foe yield)", len(pin_cases) >= 10, len(pin_cases))
check("a pinning maneuver on a foe that yields at the blow: it is not held, nor tied to the striker",
      all("grappled" not in y.statuses and bf.validate(f) == [] for y, f in pin_cases),
      [(dict(y.statuses), bf.validate(f)) for y, f in pin_cases if "grappled" in y.statuses or bf.validate(f)][:1])

# the table: every element effect, on a foe in the fight, one that yielded at the blow and one the blow killed
ran: list[str] = []
real = spellcraft._express
spellcraft._express = lambda combat_, att, dfn, taken, rng, ctx, eid: ran.append(eid)
try:
    every = [e for e in spellcraft.EXPR if not spellcraft.is_control(e)]
    rows = {}
    for state in ("standing", "yielded", "fallen"):
        p = player()
        t = foe(1, hp=100)
        f = fight(p, t)
        if state == "yielded":
            t.fled, t.surrendered = True, True
        elif state == "fallen":
            t.hp = 0.0
        p.casting = {"exprs": every, "tier": "light", "name": "Test", "once": []}
        ran.clear()
        spellcraft.on_hit(f, p, t, 10.0, random.Random(1))
        rows[state] = set(ran)
finally:
    spellcraft._express = real
    p.casting = {}
check("the table: every element effect does its work on a foe still in the fight", rows["standing"] == set(every),
      sorted(set(every) - rows["standing"]))
check("the table: on a foe that yielded at the blow, only the effects that work on a kill do their work",
      rows["yielded"] == set(every) & spellcraft.DEAD_OK, sorted(rows["yielded"] ^ (set(every) & spellcraft.DEAD_OK)))
check("the table: on a foe the blow killed, the same, as before", rows["fallen"] == set(every) & spellcraft.DEAD_OK,
      sorted(rows["fallen"] ^ (set(every) & spellcraft.DEAD_OK)))

# ---- 6. a blessing handed a stale foe as its target: still its caster's, not refused
bless = spell("stone_skin", effect="buff", buff="bulwark", reach="self")
p = player(moves=[bless])
gone = foe(1, hp=100)
f = fight(p, gone, foe(2))
gone.hp = 0.0
res = combat.act_ability(f, p, bless, gone, random.Random(2))
check("a blessing handed a fallen foe as its target: it lands on its caster and is not refused",
      res is None and bless.id in p.buffs and not gone.buffs, (res, list(p.buffs), list(gone.buffs)))

# ---- 7. the second line: a blow handed straight to a defender who is down or gone draws no die and lands nothing
for state in ("fallen", "fled"):
    p = player(("flurry", 100), ("triumph", 10))
    gone = foe(1, hp=100)
    f = fight(p, gone)
    bf.engage(f, p, gone)
    if state == "fallen":
        gone.hp = 0.0
    else:
        gone.fled = True
    rng = random.Random(3)
    before = rng.getstate()
    hp0, log0, s0 = gone.hp, len(f.log), len(f.story)
    landed = combat.apply_damage(f, p, gone, 1.0, "attacks", rng)
    check(f"a blow straight at a {state} foe: it lands nothing, records nothing, tells nothing and draws no die",
          landed is False and gone.hp == hp0 and not f.hits and len(f.log) == log0 and len(f.story) == s0 and rng.getstate() == before,
          (landed, gone.hp, f.hits, f.log[log0:], f.story[s0:]))

# an area cast whose kills rout the rest: the rest of the cast passes a foe that broke, so none ends both fled and dead
blast = spell("fire_burst", element="fire", tier="heavy", spell_form="blast")
both = casts = routed = struck_gone = 0
for sd in range(1, 41):
    p = player(moves=[blast], mana=10 ** 5, dmg=30)
    pack = [foe(i, hp=30, fearless=False, category="beast") for i in range(1, 6)]
    f = fight(p, *pack)
    for e in pack:
        e.zone_id = pack[0].zone_id
        bf.engage(f, p, e)
    r0 = len(ROLLS)
    combat.act_ability(f, p, blast, pack[0], random.Random(sd))
    casts += 1
    struck_gone += bool(on_the_gone(r0))
    routed += any(e.fled for e in pack)
    both += any(e.fled and not e.alive for e in pack)
check("(an area cast routs part of the pack in some seeds)", routed >= 5, routed)
check("an area cast: the rest of it passes a foe that broke at an earlier kill", struck_gone == 0, f"{struck_gone} of {casts}")
check("an area cast: no foe ends both fled and dead", both == 0, f"{both} of {casts}")

# ---- 8. what must still pass: No One Escapes strikes the runner before it is gone; a thrall still rises from the fallen
p = player(("no_one_escapes", 1), dmg=12)
runner = foe(1, hp=200)
f = fight(p, runner)
bf.engage(f, p, runner)
behaviors._break(f, runner, False)
check("No One Escapes: the parting strike still lands on the runner", runner.fled and bool(hits_on(f, runner)), [h["dfn"] for h in f.hits])
p = player(("thrall", 1), dmg=10 ** 5)
dead = foe(1, hp=10)
f = fight(p, dead, foe(2))
bf.engage(f, p, dead)
rng = random.Random(1)
for _ in range(10):
    if not dead.alive:
        break
    combat.apply_damage(f, p, dead, 3.0, "attacks", rng)
risen = f.get("thrall")
check("a thrall still rises from the one the blow killed", not dead.alive and risen is not None and risen.alive and not risen.fled,
      [x.id for x in f.fighters])

print("all ok" if not bad else f"FAILED: {len(bad)}", file=sys.__stdout__)
sys.exit(1 if bad else 0)
