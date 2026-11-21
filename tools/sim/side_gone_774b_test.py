"""(f774) One reading of whether the foes' side is gone, and one of whether a fighter is still in the fight (found by the review of
f768 to f774). A foe whose break is held to the end of the action in progress (f770) was gone to the rout's roll but standing to the
turning law (combat.foes_gone): inside a cast whose first kill had already broken the rest of the side, Dominate turned the last
undead and the won check lifted the will at once ("turns on its own side", then "the will on the skeleton lifts"), and Dread Regent
turned the first of two held foes, so the second ran, the turned one fled "its old side broken", the fight was won and Regent spent.
And a fighter taken off the field by leave(..., "gone") (tamed, bound, freed, turned away at a trial's door) was still in the fight
to every rule but the turn's: harm reached it, a kill paid it, it could leave again; and a fled ally stayed among the allies.
The kind: every rule that asks whether the foes' side stands (the rout's roll, the turning law, the settling of the turned, the won
fight), and every rule that asks whether one fighter is in the fight (its turn, harm reaching it, a kill's pay, leaving, the foes and
the allies). One list of the side as it stands (combat.foes_standing: the foes in the fight but those held to break), which the rout
rolls among and foes_gone reads; one predicate (combat.in_fight(combat, f): alive, not fled, and on the field) the rest ask.
Cases: Dominate and Dread Regent inside a cast that holds the rest of the side's breaks, Dominate's `alone` told after the breaks it
rests on (once for two landings in an action, never of an undead that fell later in it), and, beside them, the same casts with a foe
left standing or a wave in reserve, where the turn still comes; every turning-law question asked in them read against the rout's
list, and every held foe out of its side when the action is done; a fighter turned away at a trial's door, a tamed foe, a fled ally,
and one down, fled and yielded, read by every rule that asks whether it is in the fight.
Run: python tools/sim/side_gone_774b_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from engine import battlefield as bf
from engine import behaviors, combat, combat_perks, spellcraft
from engine.combat import Move

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def in_fight(c, x):
    """The predicate, read through its one form (the fight and the fighter); before it, the reading without the field."""
    try:
        return combat.in_fight(c, x)
    except TypeError:
        return combat.in_fight(x)


def standing(c, but=None):
    """The foes' side as it stands, as the rout reads it: the foes in the fight but the one named and those held to break."""
    read = getattr(combat, "foes_standing", None)
    return read(c, but) if read else [e for e in c.enemies() if e is not but and not combat.held(c, e)]


GRAVE = Move(id="grave_wave", name="Grave Wave", effect="damage", tier="heavy", reach="ranged", resource="mana", attribute="intelligence",
             element="necrotic", spell_form="blast", expressions=["dominate"])
FIRE = Move(id="fire_wave", name="Fire Wave", effect="damage", tier="heavy", reach="ranged", resource="mana", attribute="intelligence",
            element="fire", spell_form="blast")
ALONE = spellcraft.EXPR["dominate"]["alone"]


def fighter(fid, side, hp=10 ** 6, **kw):
    attrs = {a: 12 for a in combat.ATTRIBUTES}
    return combat.Fighter(id=fid, name=kw.pop("name", fid), side=side, level=kw.pop("level", 5), attrs=attrs, hp=hp,
                          max_hp=kw.pop("max_hp", hp), stamina=10 ** 4, max_stamina=10 ** 4, mana=10 ** 5, max_mana=10 ** 5,
                          weapon_damage=kw.pop("dmg", 12), weapon_attrs=["strength"], hold=2, **kw)


def player(*mechs, moves=()):
    return fighter("player", "player", moves=list(moves), legendary={m: 1 for m in mechs},
                   mech_names={m: m.replace("_", " ").title() for m in mechs})


def chief():
    return fighter("e1", "enemy", hp=1, max_hp=100, name="the bandit chief", level=8, rank="elite", dmg=0.001)


def bandit(i, name="the bandit"):
    return fighter(f"e{i}", "enemy", hp=10 ** 5, name=name, level=3, dmg=0.001)


def skeleton(i=3):
    return fighter(f"e{i}", "enemy", hp=10 ** 5, name="the skeleton", level=3, category="undead", dmg=0.001)


def pack(p, *foes, serial="sg", reserves=()):
    """The player and the foes in one zone, each foe tied up with the player."""
    f = combat.Combat(fighters=[p, *foes], record=True, serial=serial)
    combat.ensure_field(f)
    f.opened = True
    for x in foes:
        if x.zone_id != p.zone_id:
            bf.enter_zone(f, x, p.zone_id)
        bf.engage(f, x, p)
    f.reserves = list(reserves)
    return f


def told(f, words) -> int:
    return sum(words.lower() in s.lower() for s in f.story)


def at(f, words) -> int:
    """Where in the story the first line saying these words falls (-1: nowhere)."""
    return next((i for i, s in enumerate(f.story) if words.lower() in s.lower()), -1)


# ---- the rout's die the case rules (f770's forced break): RULE(foe) says whether a foe rolled for at a death breaks
RULE = {"rule": None}
PEEK: dict = {}
ROUT_READS: list[tuple] = []     # (the foes the rout rolled among at a death, the side as it stood then)
_morale, _routs = behaviors.morale_on_death, behaviors._routs


class Ruled(random.Random):
    def random(self):
        return 0.0 if RULE["rule"](PEEK["rolled"]) else 0.999


def morale_on_death(c, fallen, rng):
    PEEK["asked"], before = [], list(standing(c))
    out = _morale(c, fallen, Ruled(0) if RULE["rule"] else rng)
    if PEEK["asked"]:
        ROUT_READS.append((list(PEEK["asked"]), before))
    return out


def routs(e, c):
    PEEK["rolled"] = e
    PEEK.setdefault("asked", []).append(e)
    return _routs(e, c)


behaviors.morale_on_death, behaviors._routs = morale_on_death, routs

# ---- every question the turning law asks, with the side as the rout reads it at that moment
LAW: list[dict] = []
_turn_foe = combat_perks.turn_foe


def turn_foe(c, f, *a, **k):
    rec = {"f": f, "held": [e for e in c.enemies() if combat.held(c, e)], "gone": combat.foes_gone(c, f),
           "rout": not standing(c, f) and not c.reserves}
    rec["turned"] = _turn_foe(c, f, *a, **k)
    LAW.append(rec)
    return rec["turned"]


combat_perks.turn_foe = turn_foe

# every foe whose break was held, to be read when its action is done
HELD: list = []
_hold = combat.hold_break


def hold_break(c, f, *a, **k):
    got = _hold(c, f, *a, **k)
    if got:
        HELD.append(f)
    return got


combat.hold_break = hold_break


def cast(p, move, foes, seed, rule, reserves=()):
    """One cast at the chief; the fight, and the turning-law questions asked in it."""
    RULE["rule"] = rule
    LAW.clear()
    HELD.clear()
    f = pack(p, *foes, serial=f"sg{seed}", reserves=reserves)
    combat.act_ability(f, p, move, foes[0], random.Random(seed))
    return f, list(LAW), list(HELD)


ALL = lambda e: True            # every foe rolled for breaks
NONE = lambda e: False          # none does

# ---- 1. Dominate in a cast whose first kill held the rest of the side's breaks: the last undead is the last of its side
asked = turned = alone = after = lifted = ran = fights_on = 0
example = None
for s in range(200):
    p, ch, b, sk = player(moves=[GRAVE]), chief(), bandit(2), skeleton(3)
    f, law, held = cast(p, GRAVE, [ch, b, sk], s, ALL)
    q = [r for r in law if r["f"] is sk and any(e is b for e in r["held"])]
    if ch.alive or not q:
        continue                                        # the chief stood, or Dominate was not asked while the bandit's break was held
    asked += 1
    turned += told(f, "turns on its own side") > 0 or bf.turned(sk)
    alone += told(f, ALONE) == 1
    after += at(f, ALONE) > at(f, "the bandit breaks and runs") > at(f, "you hit the skeleton") >= 0
    ran += b.fled and told(f, "the bandit breaks and runs") == 1
    won = combat.won(f)
    lifted += told(f, "will on the skeleton lifts") > 0
    fights_on += not won and any(e is sk for e in f.enemies())
    if (told(f, "turns on its own side") or lifted) and example is None:
        example = list(f.story)
check("(Dominate is asked on the last undead while the bandit's break is held, in 30 casts or more)", asked >= 30, asked)
check("Dominate on the last undead while the rest of its side is held to break turns nothing", turned == 0, (turned, asked, example))
check("...and tells why, once: there is no one of its own left for it to turn on", alone == asked, (alone, asked, example))
check("...after the breaks it rests on: the bandit is told breaking and running first, never left standing beside 'no one left'",
      after == asked, (after, asked, list(f.story)))
check("...the bandit breaks and runs when the cast is done, told once", ran == asked, (ran, asked))
check("...no will lifts at the won check, for none was laid", lifted == 0, (lifted, asked, example))
check("...and the fight goes on against the undead: not won, the skeleton a foe", fights_on == asked, (fights_on, asked))

# two landings on the undead in one action (a perk's repeat) tell the line once, after the break; an undead that falls later in
# the same action is told nothing of it; with no break held, the line is told at once
LINE = f"{ALONE} (Dominate)"


@combat.one_action
def landings(c, sk, b, times, then=None):
    """One action: the bandit's break is held, then the turning law is asked of the undead `times` over, then `then`."""
    combat.hold_break(c, b, False, "the bandit breaks, held to the end of this action")
    for _ in range(times):
        combat_perks.turn_foe(c, sk, c.round + 2, "the skeleton turns", alone=LINE)
    if then:
        then(c)


p, b, sk = player(), bandit(2), skeleton(3)
f = pack(p, b, sk, serial="twice")
landings(f, sk, b, 2)
check("two landings in one action tell 'no one left' once, after the break it rests on",
      told(f, ALONE) == 1 and at(f, ALONE) > at(f, "the bandit breaks and runs") >= 0 and not bf.turned(sk), list(f.story))
p, b, sk = player(), bandit(2), skeleton(3)
f = pack(p, b, sk, serial="fell")
landings(f, sk, b, 1, then=lambda c: combat.take_damage(c, sk, 10 ** 7, p, random.Random(1)))
check("an undead that falls later in the same action is told nothing of it", not sk.alive and b.fled and told(f, ALONE) == 0,
      list(f.story))
p, sk = player(), skeleton(3)
f = pack(p, sk, serial="now")
combat_perks.turn_foe(f, sk, f.round + 2, "the skeleton turns", alone=LINE)
check("with no break held the line is told at once", told(f, ALONE) == 1 and not bf.turned(sk), list(f.story))

# beside it: the same cast with the bandit left standing (no break) turns the undead, as Dominate's card says
asked = turned = 0
for s in range(200):
    p, ch, b, sk = player(moves=[GRAVE]), chief(), bandit(2), skeleton(3)
    f, law, held = cast(p, GRAVE, [ch, b, sk], s, NONE)
    q = [r for r in law if r["f"] is sk]
    if ch.alive or not q:
        continue
    asked += 1
    turned += bf.turned(sk) and told(f, "turns on its own side") == 1 and not combat.won(f)
check("(with the bandit standing, Dominate is asked on the undead in 30 casts or more)", asked >= 30, asked)
check("Dominate with another of its side standing turns the undead, and the fight is not won by it", turned == asked, (turned, asked))

# ---- 2. Dread Regent in a cast whose first kill held both bandits' breaks
n = waits = ran = broken = won_ = 0
example = None
for s in range(60):
    p, ch, b1, b2 = player("dread_regent", moves=[FIRE]), chief(), bandit(2, "the first bandit"), bandit(3, "the second bandit")
    f, law, held = cast(p, FIRE, [ch, b1, b2], s, ALL)
    if ch.alive or not (any(x is b1 for x in held) and any(x is b2 for x in held)):
        continue
    n += 1
    waits += not p.counters.get("regent") and told(f, "instead of running") == 0 and not bf.turned(b1) and not bf.turned(b2)
    ran += b1.fled and b2.fled and told(f, "the first bandit breaks and runs") == 1 and told(f, "the second bandit breaks and runs") == 1
    w = combat.won(f)
    broken += told(f, "its old side broken") == 0
    won_ += w
    if (p.counters.get("regent") or told(f, "its old side broken")) and example is None:
        example = list(f.story)
check("(the chief falls with both bandits' breaks held, in 20 casts or more)", n >= 20, n)
check("Dread Regent with every other foe held to break turns nobody, and waits unspent", waits == n, (waits, n, example))
check("...both bandits break and run when the cast is done, each told once", ran == n, (ran, n, example))
check("...no turned foe flees 'its old side broken', for none turned", broken == n, (broken, n, example))
check("...and the fight is won by the blow and the rout, as with no Regent at all", won_ == n, (won_, n))

# beside it: only the first bandit's break held, the second standing: Regent turns the first, and the fight goes on
n = turns = 0
for s in range(60):
    p, ch, b1, b2 = player("dread_regent", moves=[FIRE]), chief(), bandit(2, "the first bandit"), bandit(3, "the second bandit")
    f, law, held = cast(p, FIRE, [ch, b1, b2], s, lambda e: e.id == "e2")
    if ch.alive or not any(x is b1 for x in held):
        continue
    n += 1
    turns += bf.turned(b1) and not b1.fled and bool(p.counters.get("regent")) and any(e is b2 for e in f.enemies()) and not combat.won(f)
check("(the chief falls with only the first bandit's break held, in 20 casts or more)", n >= 20, n)
check("Dread Regent with another foe standing turns the first to break, spends itself, and the fight is not won", turns == n, (turns, n))

# and both held with a wave waiting in reserve: the side is not gone, so Regent turns the first
n = turns = 0
for s in range(60):
    p, ch, b1, b2 = player("dread_regent", moves=[FIRE]), chief(), bandit(2, "the first bandit"), bandit(3, "the second bandit")
    f, law, held = cast(p, FIRE, [ch, b1, b2], s, ALL, reserves=[bandit(9, "the camp's bandit")])
    if ch.alive or not (any(x is b1 for x in held) and any(x is b2 for x in held)):
        continue
    n += 1
    turns += bf.turned(b1) and bool(p.counters.get("regent")) and b2.fled and not combat.won(f)
check("(the chief falls with both breaks held and a wave in reserve, in 20 casts or more)", n >= 20, n)
check("Dread Regent with both held but a wave waiting turns the first: the side is not gone while a wave waits", turns == n, (turns, n))

# ---- 3. the readings agree: the turning law reads the side as the rout does, and every held foe leaves its side
LAW.clear()
HELD.clear()
seen = disagree = held_seen = 0
shown = None
left_side = True
for rule in (ALL, NONE, lambda e: e.id == "e2"):
    for s in range(40):
        for mk in (lambda: (player(moves=[GRAVE]), GRAVE, [chief(), bandit(2), skeleton(3)]),
                   lambda: (player("dread_regent", moves=[FIRE]), FIRE, [chief(), bandit(2, "the first bandit"),
                                                                       bandit(3, "the second bandit")])):
            p, move, foes = mk()
            f, law, held = cast(p, move, foes, s, rule)
            for r in law:
                seen += 1
                held_seen += bool(r["held"])
                if r["gone"] != r["rout"]:
                    disagree += 1
                    shown = shown or (r["f"].name, [e.name for e in r["held"]], r["gone"], r["rout"])
            left_side = left_side and not any(any(e is x for e in f.enemies()) for x in held)
check("(the turning law is asked 60 times or more, some of them with a break held)", seen >= 60 and held_seen >= 20, (seen, held_seen))
check("whenever the turning law asks whether the side is gone, it reads the side as the rout does (a foe held to break is gone)",
      disagree == 0, (disagree, seen, shown))
check("every foe whose break was held is out of its side when the action is done (fled, yielded, down or turned)", left_side)
check("each rout rolls among the side as it stands at its death (combat.foes_standing), and only them",
      len(ROUT_READS) > 20 and all([id(x) for x in a] == [id(x) for x in b] for a, b in ROUT_READS),
      next(((a, b) for a, b in ROUT_READS if [id(x) for x in a] != [id(x) for x in b]), len(ROUT_READS)))
check("the side as it stands is one function, combat.foes_standing, and foes_gone reads it", callable(getattr(combat, "foes_standing", None)))

# the won fight reads the same side: after an action, once the turned are settled, it is won exactly when the side is gone
odd = []
for rule in (ALL, NONE, lambda e: e.id == "e2"):
    for s in range(15):
        p, ch, b1, b2 = player("dread_regent", moves=[FIRE]), chief(), bandit(2, "the first bandit"), bandit(3, "the second bandit")
        f, law, held = cast(p, FIRE, [ch, b1, b2], s, rule)
        w = combat.won(f)
        if w != combat.foes_gone(f):
            odd.append((s, w, [e.id for e in f.enemies()]))
check("the won check agrees with foes_gone once the turned are settled (45 casts)", not odd, odd)
RULE["rule"] = None


# ---- 4. one predicate for 'still in the fight', with the field in it
def plain(*fs, serial="pf"):
    f = combat.Combat(fighters=list(fs), players=["player"], record=True, serial=serial)
    combat.ensure_field(f)
    f.opened = True
    for x in fs[1:]:
        if x.zone_id != fs[0].zone_id:
            bf.enter_zone(f, x, fs[0].zone_id)
    return f


def readings(c, x) -> dict:
    """Every rule that asks whether x is in the fight, as it reads it (no blow open)."""
    return {"in_fight": in_fight(c, x), "takes_turn": combat.takes_turn(c, x), "reaches": combat.reaches(c, x),
            "reaches_by": combat.reaches(c, x, by=c.player), "enemies": any(e is x for e in c.enemies()) == (bf.is_foe(x) and in_fight(c, x)),
            "allies": any(a is x for a in c.allies()) == (x.side == "ally" and in_fight(c, x)),
            "side": any(a is x for a in c.player_side()) == (not bf.is_foe(x) and in_fight(c, x))}


def agree(name, c, x, want: bool):
    r = readings(c, x)
    ok = all(r[k] == want for k in ("in_fight", "takes_turn", "reaches", "reaches_by")) and r["enemies"] and r["allies"] and r["side"]
    check(f"{name}: every rule reads it as {'in' if want else 'out of'} the fight (its turn, harm reaching it, the foes, the allies)", ok, r)


def harmless(name, c, x, striker):
    """Nothing reaches x: a blow, side harm, a status."""
    hp, hits, story = x.hp, len(c.hits), len(c.story)
    landed = combat.apply_damage(c, striker, x, 1.0, "strikes", random.Random(1))
    dealt = combat.side_damage(c, x, 50, striker, random.Random(2), "physical", told="it is struck from the side")
    took = combat.add_status(c, x, "poisoned", 3, striker)
    check(f"{name}: no blow, side harm or status reaches it", not landed and not dealt and not took and x.hp == hp
          and len(c.hits) == hits and len(c.story) == story and "poisoned" not in x.statuses,
          (landed, dealt, took, hp, x.hp, c.story[story:]))


def unpaid(name, c, x):
    """A kill credited to x pays it nothing."""
    dead = fighter("e8", "enemy", hp=0, max_hp=40, name="the fallen one")
    c.round = 6
    was = x.kill_round
    combat.credit(c, x, dead, random.Random(3))
    check(f"{name}: a kill credited to it pays it nothing", x.kill_round == was, (was, x.kill_round))


def no_second_leaving(name, c, x):
    log, was = len(c.log), (x.fled, x.surrendered)
    again = combat.leave(c, x, "fled")
    check(f"{name}: it cannot leave the fight again (leave refuses, and the log says it has already left)",
          again is False and (x.fled, x.surrendered) == was and any("has already left the fight" in s for s in c.log[log:]),
          (again, was, (x.fled, x.surrendered), c.log[log:]))


# a companion turned away at a trial of rank's door (f771: the door takes it off the field by leave(..., "gone"))
p, comp, foe = player(), fighter("ally_1", "ally", name="Bryn"), fighter("e1", "enemy", name="the challenger", dmg=0.001)
c = plain(p, comp, foe, serial="door")
c.duel = True
for x in [x for x in c.fighters if not combat.stands(c, x)]:
    combat.leave(c, x, "gone")
check("(the trial's door turns the companion away: off the field)", c.get("ally_1") is None and comp.alive and not comp.fled)
agree("a companion turned away at a trial's door", c, comp, False)
check("...it is no one the foe may strike (foes_of)", not any(x is comp for x in c.foes_of(foe)))
c.duel = False                                          # (its floors are the duellists'; the harm below is asked of the fighter alone)
harmless("a companion turned away at a trial's door", c, comp, foe)
unpaid("a companion turned away at a trial's door", c, comp)
no_second_leaving("a companion turned away at a trial's door", c, comp)

# a foe tamed off the field (the service's tame and Bind a Beast take it off by leave(..., "gone"))
p, wolf, other = player(), fighter("e1", "enemy", name="the wolf", dmg=0.001), fighter("e2", "enemy", name="the other wolf", dmg=0.001)
c = plain(p, wolf, other, serial="tame")
combat.leave(c, wolf, "gone")
agree("a foe tamed off the field", c, wolf, False)
harmless("a foe tamed off the field", c, wolf, p)
unpaid("a foe tamed off the field", c, wolf)
no_second_leaving("a foe tamed off the field", c, wolf)
check("...and the foes' side reads it gone: the other wolf alone stands", [e.id for e in standing(c)] == ["e2"]
      and not combat.foes_gone(c) and combat.foes_gone(c, other), [e.id for e in standing(c)])

# a fled ally is not among the allies, nor the player's side; nor is one yielded
for way in ("fled", "yielded"):
    p, a1, a2, foe = player(), fighter("ally_1", "ally", name="Bryn"), fighter("ally_2", "ally", name="Tam"), fighter("e1", "enemy", dmg=0.001)
    c = plain(p, a1, a2, foe, serial=f"ally_{way}")
    combat.leave(c, a2, way)
    check(f"an ally {way} is not among the allies nor the player's side; the one still here is",
          [a.id for a in c.allies()] == ["ally_1"] and [x.id for x in c.player_side()] == ["player", "ally_1"],
          ([a.id for a in c.allies()], [x.id for x in c.player_side()]))
    agree(f"an ally {way}", c, a2, False)
    agree("the ally still here", c, a1, True)

# every way out, and standing, read alike by every rule, for each side
for side in ("enemy", "ally"):
    for way in ("standing", "down", "fled", "yielded", "gone"):
        p = player()
        x = fighter("ally_1" if side == "ally" else "e1", side, hp=500, max_hp=500, dmg=0.001)
        keep = fighter("e2", "enemy", hp=10 ** 5, dmg=0.001)
        c = plain(p, x, keep, serial=f"w{side}{way}")
        if way == "down":
            x.hp = 0
        elif way != "standing":
            combat.leave(c, x, way)
        agree(f"{'a foe' if side == 'enemy' else 'an ally'} {way}", c, x, way == "standing")
        if way not in ("standing", "down"):
            no_second_leaving(f"{'a foe' if side == 'enemy' else 'an ally'} {way}", c, x)

if bad:
    print(f"\n{len(bad)} FAILED", file=sys.__stdout__)
    sys.exit(1)
print("\nall passed", file=sys.__stdout__)
