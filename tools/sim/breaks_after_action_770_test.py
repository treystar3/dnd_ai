"""(f770) Who breaks at a death is settled when the action that caused it has finished (found by the code audit, fight-abilities-2:
a blast at five weak foes routed some of them at its first kill, and the rest of the blast struck the ones who had broken; a foe
ended both fled and dead, the player was told it yielded, and it was counted and looted). Since f763 a blow passes a foe who has
left, so the blast's reach hung on the order of its list; the effects that draw their victims first and strike by side damage (a
summon's burst and pulse, Starfall, a relic's nova, Unmaking) still struck the fled. The kind: every action with a blow or a
consequence still to land when a death routs someone, in a player's action and in a foe's or an ally's turn. One scope for an
action (an ability, an attack, a movement, a turn, a turn's start, an improvisation, the mentor's strike), held on the fight and
never in its row:
inside it a break a rout asks for rolls its die where it always did and is held, and the held foe stays a foe; when the outermost
action closes, each held break is settled in the order it was rolled, through the one way out, its line told only if it broke.
The finder's case (a ranked blast, a ranked burst, an area spell, a martial sweep and the Sweeping shape at five weak foes, plain
and able to yield, on the action's own dice), then the kind on a die that breaks every foe it is rolled for: the chain, cleave and
ricochet shapes, Starfall, a relic's nova, Unmaking, a summon's burst and a totem's pulse in its turn, a perk's repeat (Grave
Chorus), Follow Through, an ally's Cleave, a retreat's parting blows when thorns kill the first, the mentor's strike at every foe,
an improvisation; a foe's turn
whose miss meets a riposte that kills it (the break lands when the turn is over); a charged blast released at the turn's start (the
scope inside the turn's start does not settle it); a runner cut down by No One Escapes as its break is settled (one fall, no break
told) and the rout that death sets off, settled too; a failed action leaves nothing held; the fight's row holds nothing of it.
What must not move: a killing blow inside an attack draws the blow's die as one outside any action does, and routs the same foes.
Run: python tools/sim/breaks_after_action_770_test.py"""
import random
import re
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from engine import battlefield as bf
from engine import behaviors, bosses, combat, combat_improv, damage, parley, summons
from engine import effects as fx
from engine.combat import Move

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def player(*mechs, moves=(), hp=10 ** 4, dmg=200, **kw):
    pairs = [x if isinstance(x, tuple) else (x, 1) for x in mechs]
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: 14 for a in combat.ATTRIBUTES}, hp=hp,
                          max_hp=hp, stamina=10 ** 5, max_stamina=10 ** 5, mana=10 ** 5, max_mana=10 ** 5, weapon_damage=dmg,
                          weapon_attrs=["strength"], hold=2, legendary=dict(pairs), mech_names={m: m.replace("_", " ").title() for m, _ in pairs},
                          moves=list(moves), **kw)


WEAK, STOUT = 1, 10 ** 4
FIVE = (WEAK, STOUT, WEAK, STOUT, WEAK)     # the weak fall to anything that lands; the stout stand, and may break


def foe(i, hp, yields=False, **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=kw.pop("level", 5), attrs={a: 10 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=kw.pop("max_hp", STOUT), weapon_damage=kw.pop("dmg", 0.001),
                          category="hostile people" if yields else "beast", behaviors={"surrender": 1.0} if yields else {}, **kw)


def pack(p, hps=FIVE, yields=False, others=(), serial="ba"):
    """The player and a pack in one zone, each foe tied up with the player."""
    foes = [foe(i + 1, hp, yields) for i, hp in enumerate(hps)]
    f = combat.Combat(fighters=[p, *foes, *others], record=True, serial=serial)
    combat.ensure_field(f)
    f.opened = True
    for x in [*foes, *others]:
        if x.zone_id != p.zone_id:
            bf.enter_zone(f, x, p.zone_id)
    for e in foes:
        bf.engage(f, e, p)
    return f, foes


def spell(mid, **kw):
    kw.setdefault("reach", "ranged")
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=kw.pop("effect", "damage"), tier=kw.pop("tier", "heavy"),
                resource="mana", attribute="intelligence", **kw)


def skill(mid, **kw):
    kw.setdefault("reach", "melee")
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=kw.pop("effect", "damage"), tier=kw.pop("tier", "heavy"),
                resource="stamina", **kw)


# ---- the probes: every attack roll and every damage path, with whether each side was still in the fight as it began
ROLLS: list[tuple] = []          # (attacker id, defender id, attacker in the fight, defender in the fight)
STRUCK: list[tuple] = []         # (path, defender id, defender in the fight)
_roll, _resolve = combat.roll_attack, damage.resolve


def roll_attack(att, dfn, combat_, rng, trace=None):
    ROLLS.append((att.id, dfn.id, combat.in_fight(combat_, att), combat.in_fight(combat_, dfn)))
    return _roll(att, dfn, combat_, rng, trace=trace)


def resolve(path, combat_, dfn, *a, **k):
    STRUCK.append((path, dfn.id, combat.in_fight(combat_, dfn)))
    return _resolve(path, combat_, dfn, *a, **k)


combat.roll_attack, damage.resolve = roll_attack, resolve

# a rout's die the case rules: RULE(fallen, foe) says whether that foe breaks when rolled for at that death (None: the action's die)
RULE = {"rule": None}
ASKED: list[tuple] = []          # (fallen id, foe id, attack rolls made so far) for every foe rolled for at a death
PEEK: dict = {}
_morale, _routs, _break, _after_turn = behaviors.morale_on_death, behaviors._routs, behaviors._break, behaviors.after_turn
ORDER: list[tuple] = []


class Ruled(random.Random):
    """A rout's die that breaks the foe it is rolled for when the case's rule says so (the foe is the one _routs was last asked)."""
    def __init__(self, fallen):
        super().__init__(0)
        self.fallen = fallen

    def random(self):
        e = PEEK["rolled"]
        ASKED.append((self.fallen.id, e.id, len(ROLLS)))
        return 0.0 if RULE["rule"](self.fallen, e) else 0.999


def morale_on_death(c, fallen, rng):
    out = _morale(c, fallen, Ruled(fallen) if RULE["rule"] else rng)
    if PEEK.get("row"):
        PEEK.update(dump=c.model_dump(), json=c.model_dump_json(), row=False)
    return out


def routs(e, c):
    PEEK["rolled"] = e
    return _routs(e, c)


def broke(c, f, surrender):
    ORDER.append(("break", f.id))
    return _break(c, f, surrender)


def after_turn(c, e, rng):
    ORDER.append(("turn over", e.id))
    return _after_turn(c, e, rng)


_after_hit = behaviors.after_hit


def after_hit(c, e, target, landed, rng):
    ORDER.append(("turn over", e.id))           # (f772) a foe felled at its own blow ends its turn with that blow's riders
    return _after_hit(c, e, target, landed, rng)


behaviors.morale_on_death, behaviors._routs, behaviors._break, behaviors.after_turn = morale_on_death, routs, broke, after_turn
behaviors.after_hit = after_hit
EVERY = lambda fallen, e: True                     # noqa: E731  every foe breaks at the first death it is rolled for

ROUT = re.compile(r"breaks and runs|throws down .* yields|breaks, (seeing|with so many)|loses heart|turns on its own side")


def falls(f, x, s0=0) -> list[int]:
    w = re.escape(combat.who(x))
    pat = re.compile(rf"(^|, and |\. ){w} (fall|falls|succumbs|collapse|collapses)\b", re.I)
    return [i for i, s in enumerate(f.story[s0:]) if pat.search(s)]


def mark(f):
    return len(f.story), len(f.told), len(ROLLS), len(STRUCK), len(ASKED)


def faults(f, foes, m, drawn=(), noe=False) -> dict[str, str]:
    """What one action left wrong, by kind of fault: empty when it is all as it should be."""
    s0, t0, r0, i0, _ = m
    out = {}
    both = [e.id for e in foes if e.fled and not e.alive]
    if both:
        out["fled and dead"] = both
    gone = [x for x in ROLLS[r0:] if not x[3]] + [x for x in STRUCK[i0:] if not x[2] and x[0] == "blow"]
    if gone:
        out["struck after it left"] = gone
    from_gone = [x for x in ROLLS[r0:] if not x[2]]
    if from_gone:
        out["a blow from one who had left"] = from_gone
    reached = {x[1] for x in ROLLS[r0:]} | {x[1] for x in STRUCK[i0:]}
    passed = [e.id for e in drawn if e.id not in reached]
    if passed:
        out["a foe it caught passed by"] = passed
    story = f.story[s0:]
    routs_at = [i for i, s in enumerate(story) if ROUT.search(s)]
    if routs_at and not noe and not all(ROUT.search(s) for s in story[routs_at[0]:]):
        out["a rout told before the action was done"] = story[routs_at[0]:][:6]
    for e in foes:
        if e.alive:
            continue
        w = combat.who(e).lower()
        if any(ROUT.search(s) and s.lower().startswith(w + " ") for s in story):
            out[f"{e.id} told breaking, and dead"] = [s for s in story if s.lower().startswith(w + " ")]
        if any(re.search(rf"\b{re.escape(e.name)}\b", str(t)) for t in f.told[t0:]):
            out[f"{e.id} told to the player as leaving, and dead"] = f.told[t0:]
        if len(falls(f, e, s0)) != 1:
            out[f"{e.id} told falling {len(falls(f, e, s0))} times"] = story
    if bf.validate(f):
        out["the field"] = bf.validate(f)
    return out


def tally(rows: list[dict]) -> dict[str, list]:
    """Each kind of fault, with the seeds that showed it and the first seen."""
    out: dict[str, list] = {}
    for sd, got in rows:
        for k, v in got.items():
            kind = re.sub(r"^e\d+ ", "a foe ", k)
            out.setdefault(kind, [0, (sd, v)])[0] += 1
    return out


KINDS = ("fled and dead", "struck after it left", "a blow from one who had left", "a foe it caught passed by",
         "a rout told before the action was done", "a foe told breaking, and dead", "a foe told to the player as leaving, and dead",
         "a foe told falling", "the field", "a foe rolled for again")


def judge(label, rows, n):
    seen = tally(rows)
    for kind in KINDS:
        hits = {k: v for k, v in seen.items() if k.startswith(kind)}
        count = sum(v[0] for v in hits.values())
        first = next(iter(hits.values()), [0, None])[1]
        check(f"{label}: {kind.replace('a foe told falling', 'a foe it killed told falling more or less than once')}: never",
              count == 0, f"{count} of {n}; first: {first}")
    other = [k for k in seen if not any(k.startswith(kind) for kind in KINDS)]
    check(f"{label}: no other fault", not other, other)


# ---- 1. the finder's case: an area cast, a sweep and the Sweeping shape at five weak foes, on the action's own dice
FINDERS = {
    "a ranked blast": spell("fire_burst", element="fire", spell_form="blast", rank=1),
    "a ranked burst": spell("nova_ring", element="fire", spell_form="burst", rank=1),
    "an area spell": spell("firestorm", element="fire", reach="area"),
    "a martial sweep": skill("reaping_sweep", martial_form="sweep"),
    "the Sweeping shape": skill("wide_cut", shape="sweeping"),
}
for label, mv in FINDERS.items():
    for yields in (False, True):
        kind = "foes able to yield" if yields else "plain foes"
        rows, routed, refused = [], 0, None
        for sd in range(1, 41):
            p = player(moves=[mv])
            f, foes = pack(p, yields=yields)
            m = mark(f)
            res = combat.act_ability(f, p, mv, foes[0], random.Random(sd))
            if res:
                refused = res
                break
            rows.append((sd, faults(f, foes, m, drawn=foes)))
            routed += any(e.fled for e in foes)
        check(f"({label} at {kind}: cast, never refused)", refused is None, refused)
        check(f"({label} at {kind}: casts where part of the pack broke)", routed >= 5, routed)
        judge(f"{label} at five weak {kind}", rows, len(rows))

# ---- 2. the kind, on a die that breaks every foe at the first death it is rolled for
RULE["rule"] = EVERY


def ability_row(mv, *mechs, target=1, hps=FIVE, drawn=True, before=None):
    """An ability the player uses at the pack: (fight, foes, run, drawn)."""
    def setup(sd):
        p = player(*mechs, moves=[mv])
        f, foes = pack(p, hps=hps, serial=f"ab{sd}")
        if before:
            before(f, p, foes)
        return f, foes, (lambda: combat.act_ability(f, p, mv, foes[target - 1], random.Random(sd))), (foes if drawn else ())
    return setup


def starfall_before(f, p, foes):
    p.spells_cast = 3                                  # the bolt is the fourth spell: the stars fall on all five


def unmaking_before(f, p, foes):
    s = summons.make(f, p, CALL, form="striker")[0]
    combat.enters(f, s)
    if s.zone_id != p.zone_id:
        bf.enter_zone(f, s, p.zone_id)


def summon_row(form, element=""):
    """A summon of the player's whose own turn strikes every foe where it stands: (fight, foes, run, drawn)."""
    mv = Move(id=f"{form}_call", name=f"{form.title()} Thing", effect="summon", tier="moderate", reach="self", resource="mana",
              attribute="intelligence", summon_form=form, element=element)

    def setup(sd):
        p = player()
        f, foes = pack(p, serial=f"sm{sd}")
        s = summons.make(f, p, mv, form=form)[0]
        combat.enters(f, s)
        if s.zone_id != p.zone_id:
            bf.enter_zone(f, s, p.zone_id)
        if form == "volatile":
            s.summon_until = f.round                    # its time is up: it bursts over everyone where it stands
        return f, foes, (lambda: combat.ally_turn(f, s, random.Random(sd))), foes
    return setup


def chorus_row(sd):
    fire = spell("firebolt", element="fire", tier="light")
    p = player("grave_chorus", moves=[fire])
    f, foes = pack(p, serial=f"gc{sd}")
    p.counters["echoes"] = 2
    return f, foes, (lambda: combat.act_ability(f, p, fire, foes[0], random.Random(sd))), ()


def attack_row(*mechs):
    def setup(sd):
        p = player(*mechs)
        f, foes = pack(p, serial=f"at{sd}")
        return f, foes, (lambda: combat.act_attack(f, p, foes[0], random.Random(sd))), ()
    return setup


def ally_cleave_row(sd):
    p = player()
    ash = combat.Fighter(id="ally_ash", name="Ash", side="ally", level=5, attrs={a: 14 for a in combat.ATTRIBUTES}, hp=10 ** 4,
                         max_hp=10 ** 4, weapon_damage=200, weapon_attrs=["strength"], hold=2, legendary={"cleave": 100})
    f, foes = pack(p, others=(ash,), serial=f"cl{sd}")
    for e in foes:
        bf.engage(f, e, ash)
    return f, foes, (lambda: combat.ally_turn(f, ash, random.Random(sd))), ()


def retreat_row(by_step=False):
    """A retreat whose first parting blow meets thorns: through the movement action, or by itself, as the service's step takes it."""
    def setup(sd):
        p = player("thorns", hp=4000, armor=50)
        p.legendary["thorns"] = 100
        f, foes = pack(p, hps=(WEAK, STOUT), serial=f"rt{sd}")
        foes[0].weapon_damage, foes[0].max_hp = 10, 40     # its bite lands, and the thorns kill it
        foes[1].pace = "fast"                              # it follows a retreat step for step
        if by_step:
            return f, foes, (lambda: combat.retreat(f, p, random.Random(sd)) and None), ()
        return f, foes, (lambda: combat.act_move(f, p, "back", None)), ()
    return setup


def legendary_row(sd):
    """A boss's legendary action fells the player's volatile summon, whose burst over the pack kills and routs."""
    p = player()
    fx.put_status(p, "frightened", 3)                  # its kit's cow is little worth: the smite and the strike are its likely choices
    boss = foe(9, STOUT, dmg=60)
    boss.boss, boss.shield = bosses.make("person", "captain", "foe 9"), 10.0
    f, foes = pack(p, others=(boss,), serial=f"lg{sd}")
    s = summons.make(f, p, BURSTING, form="volatile")[0]
    combat.enters(f, s)
    if s.zone_id != p.zone_id:
        bf.enter_zone(f, s, p.zone_id)
    s.hp = 1.0                                         # the weakest of the player's side: what the smite goes for
    return f, foes, (lambda: combat._legendary(f, random.Random(sd))), (lambda: () if s.alive else foes)


def mentor_row(sd):
    p = player()
    m = combat.Fighter(id="ally_mentor", name="Maren", side="ally", level=5, attrs={a: 14 for a in combat.ATTRIBUTES}, hp=10 ** 4,
                       max_hp=10 ** 4, weapon_damage=200, weapon_attrs=["strength"], ally_role="mentor")
    f, foes = pack(p, others=(m,), serial=f"mt{sd}")
    f.mentor_ally, f.mentor_phase, m.order = m, 2, "focus"            # told to strike: her blows go at every foe in turn
    return f, foes, (lambda: combat.mentor_strikes(f, random.Random(sd))), foes


def improv_row(sd):
    p = player()
    f, foes = pack(p, serial=f"im{sd}")
    return f, foes, (lambda: combat_improv.resolve(f, p, foes[0], "I bring the shelf down on them", random.Random(sd), "damage")), ()


CALL = Move(id="call_spirit", name="Call Spirit", effect="summon", tier="moderate", reach="self", resource="mana", attribute="intelligence",
            summon_form="striker")
BURSTING = Move(id="ember_thing", name="Ember Thing", effect="summon", tier="moderate", reach="self", resource="mana",
                attribute="intelligence", summon_form="volatile")
NOVA = Move(id="nova_stone", name="Nova Stone", effect="relic", tier="light", reach="ranged", resource="mana", uses=3,
            relic={"kind": "nova", "name": "Nova Stone", "params": {"mult": 300}})
KIND = {
    "a ranked blast": ability_row(FINDERS["a ranked blast"]),
    "a ranked burst": ability_row(FINDERS["a ranked burst"]),
    "an area spell": ability_row(FINDERS["an area spell"]),
    "a martial sweep": ability_row(FINDERS["a martial sweep"]),
    "the Sweeping shape": ability_row(FINDERS["the Sweeping shape"]),
    "the chain shape": ability_row(skill("lashing_arc", shape="chain"), drawn=False),
    "the cleave shape": ability_row(skill("splitting_cut", shape="cleave"), drawn=False),
    "the ricochet shape": ability_row(skill("skipping_stone", shape="ricochet", reach="ranged"), drawn=False),
    "Starfall": ability_row(spell("firebolt", element="fire", tier="light"), ("starfall", 300), target=2, before=starfall_before),
    "a relic's nova": ability_row(NOVA),
    "Unmaking": ability_row(CALL, "unmaking", before=unmaking_before),
    "a summon's burst, in its turn": summon_row("volatile"),
    "a totem's pulse, in its turn": summon_row("totem", element="fire"),
    "a perk's repeat (Grave Chorus)": chorus_row,
    "Follow Through": attack_row(("follow_through", 100)),
    "an ally's Cleave, in its turn": ally_cleave_row,
    "a retreat's parting blows, thorns killing the first": retreat_row(),
    "a retreat taken as a step, by itself": retreat_row(by_step=True),
    "a boss's legendary action fells a summon whose burst kills": legendary_row,
    "the mentor's strike at every foe": mentor_row,
    "an improvisation that brings the surroundings down": improv_row,
}
CARRY = ("a ranked blast", "a martial sweep", "the Sweeping shape", "the chain shape", "the cleave shape", "the ricochet shape",
         "a perk's repeat (Grave Chorus)", "Follow Through", "an ally's Cleave, in its turn")
held_then_killed = 0
for label, setup in KIND.items():
    rows, deaths, broken, struck_held = [], 0, 0, 0
    for sd in range(1, 31):
        f, foes, run, drawn = setup(sd)
        m = mark(f)
        res = run()
        if isinstance(res, str):
            rows.append((sd, {"refused": res}))
            continue
        drawn = drawn() if callable(drawn) else drawn
        got = faults(f, foes, m, drawn=drawn)
        rows.append((sd, got))
        rolled = ASKED[m[4]:]
        asked = {e: at for fallen, e, at in rolled if fallen == rolled[0][0]} if rolled else {}     # asked at the first death, and when
        twice = sorted({e for _, e, _ in rolled if sum(1 for _, x, _ in rolled if x == e) > 1})
        if twice:
            got["a foe rolled for again, at a later death of the same action"] = twice
        deaths += bool(rolled)
        broken += any(e.fled for e in foes)
        held_then_killed += sum(1 for e in foes if e.id in asked and not e.alive)
        struck_held += any(x[1] in asked and k >= asked[x[1]] and x[3] for k, x in enumerate(ROLLS[m[2]:], start=m[2]))
    check(f"({label}: actions where a death routed the rest)", deaths >= 5 and broken >= 1, (deaths, broken))
    judge(label, rows, len(rows))
    if label in CARRY:
        check(f"{label}: a foe asked to break at the kill is still a foe until the action is done, and what carries on may strike it",
              struck_held >= 3, f"in {struck_held} of {len(rows)}")
check("(a foe asked to break at a kill was then killed by the rest of the same action, in some actions)", held_then_killed >= 10,
      held_then_killed)

# ---- 3. a foe's turn: its miss meets a riposte that kills it, and a slower foe breaks when the turn is over
seen = wrong = 0
first = None
for sd in range(1, 61):
    p = player("riposte")
    f, foes = pack(p, hps=(WEAK, STOUT), serial=f"rp{sd}")
    a, b = foes
    a.always_miss = True
    ORDER.clear()
    m = mark(f)
    combat.enemy_turn(f, a, random.Random(sd))
    if a.alive:
        continue
    seen += 1
    over = max((i for i, x in enumerate(ORDER) if x == ("turn over", a.id)), default=-1)     # (f772) the turn's last step
    breaks = [i for i, x in enumerate(ORDER) if x == ("break", b.id)]
    story = f.story[m[0]:]
    if not (b.fled and breaks and over > -1 and breaks[0] > over and ROUT.search(story[-1]) and not faults(f, foes, m)):
        wrong += 1
        first = first or (ORDER[:], story, faults(f, foes, m))
check("(a foe's miss meets a riposte that kills it, in some seeds)", seen >= 10, seen)
check("a foe's turn: a slower foe breaks at its death when the turn is over, after the turn's last step, and its break is told last",
      wrong == 0, f"{wrong} of {seen}; first (order, story, faults): {first}")

# ---- 4. a charged blast released at the turn's start: the scope inside the turn's start settles nothing; the start's own does, at its end
GATHERED = spell("gathered_burst", element="fire", spell_form="blast", rank=1, cast_turns=2)
seen = wrong = 0
first = None
for sd in range(1, 31):
    p = player(moves=[GATHERED])
    f, foes = pack(p, serial=f"gb{sd}")
    p.charging = {"move": GATHERED.model_dump(), "target": "e1", "round": f.round, "left": 1, "give": [], "archmage": 0,
                  "blood_cast": False, "weave_crit": False, "echo_now": False}
    fx.put_status(p, "slowed", 3)
    p.counters["frostbite"] = ["e2", 3]                 # told at the turn's start, after the gathered blast goes off
    m = mark(f)
    combat.start_turn(p, f, random.Random(sd))
    story = f.story[m[0]:]
    bite = [i for i, s in enumerate(story) if "frostbite eats" in s]
    rout = [i for i, s in enumerate(story) if ROUT.search(s)]
    if not rout:
        continue
    seen += 1
    if not (bite and bite[0] < rout[0] and all(ROUT.search(s) for s in story[rout[0]:]) and not faults(f, foes, m, drawn=foes)):
        wrong += 1
        first = first or (story, faults(f, foes, m, drawn=foes))
check("(the released blast routs part of the pack, in some seeds)", seen >= 10, seen)
check("a blast released at the turn's start: the rout is told when the whole turn's start is done, after the frostbite that follows it",
      wrong == 0, f"{wrong} of {seen}; first (story, faults): {first}")

# ---- 5. No One Escapes as a held break is settled: the runner cut down falls once and is never told breaking
RULE["rule"] = lambda fallen, e: fallen.id == "e1" and e.id == "e2" or fallen.id == "e2" and e.id == "e3"
cut = 0
first = None
rows = []
for sd in range(1, 61):
    p = player("no_one_escapes")
    lead = foe(1, WEAK, level=8, rank="elite")
    runner, third = foe(2, WEAK), foe(3, STOUT)
    f = combat.Combat(fighters=[p, lead, runner, third], record=True, serial=f"noe{sd}")
    combat.ensure_field(f)
    f.opened = True
    f.round = sd
    for x in (lead, runner, third):
        if x.zone_id != p.zone_id:
            bf.enter_zone(f, x, p.zone_id)
    bf.engage(f, lead, p)
    bf.engage(f, runner, p)
    m = mark(f)
    combat.act_attack(f, p, lead, random.Random(sd))
    if lead.alive or runner.alive:
        continue
    cut += 1
    got = faults(f, [lead, runner, third], m, noe=True)
    story = f.story[m[0]:]
    rf = falls(f, runner, m[0])
    rb = [i for i, s in enumerate(story) if ROUT.search(s) and s.lower().startswith(combat.who(third))]
    ok = not got and not runner.fled and third.fled and third.alive and bool(rf) and bool(rb) and rb[0] > rf[0] \
        and any("parting strike" in s for s in story)
    rows.append(ok)
    if not ok:
        first = first or (story, got, runner.fled, third.fled)
check("(the parting strike cuts down a runner as its break is settled, in some seeds)", cut >= 5, cut)
check("No One Escapes as a break is settled: the runner falls once, is never told breaking or leaving, and the rout its death sets "
      "off is settled too (the third foe breaks after the runner's fall)", all(rows), f"{rows.count(False)} of {len(rows)}; first: {first}")


# ---- 5b. a talk's threat breaks the strongest, the rest lose heart, and No One Escapes cuts a runner down: each foe asked once
class Breaks(random.Random):
    """A die for morale(): every foe it is rolled for loses heart."""
    def random(self):
        return 0.0


_lose_heart = behaviors.morale
behaviors.morale = lambda c, source, rng: _lose_heart(c, source, Breaks() if RULE["rule"] else rng)
RULE["rule"] = EVERY
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 10
for a in ("charisma", "strength", "wisdom", "dexterity", "intelligence"):
    setattr(char.attributes, a, 20)
talks = 0
first = None
rows = []
for sd in range(1, 81):
    p = player("no_one_escapes")
    chief = foe(1, STOUT, yields=True, level=6)
    chief.hp = chief.max_hp * 0.2                      # badly hurt: a threat lands
    runner, third = foe(2, WEAK), foe(3, STOUT)
    f = combat.Combat(fighters=[p, chief, runner, third], record=True, serial=f"talk{sd}")
    combat.ensure_field(f)
    f.opened = True
    f.round = sd
    for x in (chief, runner, third):
        if x.zone_id != p.zone_id:
            bf.enter_zone(f, x, p.zone_id)
    bf.engage(f, runner, p)
    ORDER.clear()
    m = mark(f)
    parley.attempt(f, chief, "intimidate", char, random.Random(sd))
    if not chief.fled or runner.alive:
        continue
    talks += 1
    story = f.story[m[0]:]
    asked = [x for x in ORDER if x == ("break", third.id)]
    rf = falls(f, runner, m[0])
    ok = not runner.fled and len(rf) == 1 and third.fled and third.alive and len(asked) == 1 \
        and not any(ROUT.search(s) and s.lower().startswith(combat.who(runner)) for s in story) and bf.validate(f) == []
    rows.append(ok)
    if not ok:
        first = first or (ORDER[:], story, runner.fled, third.fled)
behaviors.morale = _lose_heart
check("(a threat breaks the chief, the rest lose heart, and the parting strike cuts the runner down, in some seeds)", talks >= 5, talks)
check("a talk's threat is one action: the runner cut down falls once and is never told breaking, and the third foe is asked to break "
      "once, never again at the runner's death", all(rows), f"{rows.count(False)} of {len(rows)}; first: {first}")

# ---- 6. a failed action leaves nothing held: the next action on the same fight settles its own breaks
RULE["rule"] = EVERY
_credit = combat.credit
fails = {"n": 0}


def credit(c, killer, fallen, rng, A=None):
    if fails["n"] == 0:
        fails["n"] = 1
        raise RuntimeError("a failure in the middle of the action")
    return _credit(c, killer, fallen, rng, A)


combat.credit = credit
raised = False
p = player(moves=[FINDERS["a ranked blast"]])
f, foes = pack(p, serial="fail")
for sd in range(1, 30):
    if fails["n"]:
        break
    try:
        combat.act_ability(f, p, FINDERS["a ranked blast"], foes[0], random.Random(sd))
    except RuntimeError:
        raised = True
combat.credit = _credit
check("(the action failed in its middle, after a kill had asked for a rout)", raised and any(not e.alive for e in foes))
check("a failed action leaves nothing in progress on the fight", getattr(f, "_open", None) == [], getattr(f, "_open", None))
after = None
for sd in range(1, 30):
    weak = next((e for e in foes if e.alive and e.hp <= WEAK), None)
    if weak is None or any(e.fled for e in foes):
        break
    combat.act_attack(f, p, weak, random.Random(sd))
    after = [(e.id, e.alive, e.fled) for e in foes]
check("...and the next action on the same fight settles its own breaks when it is done",
      any(e.fled and e.alive for e in foes), after)

# ---- 7. the fight's row holds nothing of an action in progress
PEEK["row"] = True
p = player(moves=[FINDERS["a ranked blast"]])
f, foes = pack(p, serial="row")
for sd in range(1, 30):
    if "dump" in PEEK:
        break
    PEEK["row"] = True
    combat.act_ability(f, p, FINDERS["a ranked blast"], next(e for e in foes if e.alive), random.Random(sd))
check("(the fight was read mid-action, as a rout was rolled)", "dump" in PEEK)
check("...and its row holds only the fight's own fields, and a fight read from it has nothing in progress",
      set(PEEK.get("dump") or {"x": 1}) == set(combat.Combat.model_fields) and "_open" not in (PEEK.get("json") or "_open")
      and getattr(combat.Combat.model_validate(PEEK["dump"]), "_open", None) == [] if PEEK.get("dump") else False,
      sorted(set(PEEK.get("dump") or {}) ^ set(combat.Combat.model_fields)))
RULE["rule"] = None


# ---- 8. what must not move: a killing blow inside an attack draws the blow's die as one outside any action, and routs the same foes
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


def chief_fight(seed):
    p = player(dmg=10 ** 5)
    chief = foe(9, 50, level=8, max_hp=50)
    gobs = [foe(i, STOUT, level=2) for i in (1, 2, 3)]
    f = combat.Combat(fighters=[p, chief, *gobs], record=True, serial=f"mv{seed}")
    combat.ensure_field(f)
    f.opened = True
    for x in (chief, *gobs):
        if x.zone_id != p.zone_id:
            bf.enter_zone(f, x, p.zone_id)
    bf.engage(f, p, chief)
    return f, p, chief, gobs


routed, differ = 0, []
for seed in range(30):
    runs = []
    for inside in (False, True):
        f, p, chief, gobs = chief_fight(seed)
        rng = Counted(seed)
        if inside:
            combat.act_attack(f, p, chief, rng)
        else:
            combat.apply_damage(f, p, chief, combat.RULES["damage"]["multiplier"]["basic"], f"attacks ({p.weapon_name})", rng)
        runs.append((rng.n, "".join("1" if g.fled else "0" for g in gobs), chief.alive))
    routed += not runs[1][2] and "1" in runs[1][1]
    if runs[0] != runs[1]:
        differ.append((seed, runs))
check("(the chief falls and goblins rout, in some seeds)", routed >= 5, routed)
check("a killing blow inside an attack draws the blow's die as one outside any action, draw for draw, and routs the same foes",
      not differ, differ[:3])

behaviors.morale_on_death, behaviors._routs, behaviors._break, behaviors.after_turn = _morale, _routs, _break, _after_turn
behaviors.after_hit = _after_hit
combat.roll_attack, damage.resolve = _roll, _resolve
print("all ok" if not bad else f"FAILED: {len(bad)}", file=sys.__stdout__)
sys.exit(1 if bad else 0)
