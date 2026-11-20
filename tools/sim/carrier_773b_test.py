"""(f773, a follow-up) A floor that holds a harm holds all it carries, whatever carries it: one record of the harm in progress for a blow
and for a curse's turn alike, one finder for it, and nothing landing on the dead (found by the review of f768 to f774).
f772 kept a floor's hold on the blow in progress, and f773 named a curse as the carrier of a kill outright through the caster's casting
context; but a curse opened no record, so a floor that held a curse's gnaw at the cursed one's turn start held nothing more of it, and
the same curse's Death's Door then reached the one just held: Deathward told its line and the warden fell to "Death reaches for the
warden"; Deathless told its line twice; a trial was "called before the curse" twice, three times with a second curse. And the floors'
gates refused harm only to the living out of reach: side harm handed to a dead Lifeline companion raised it to 1 with Lifeline's line.
Each floor against a curse carrying Death's Door; the trial on either side, told once by the harm that decides it (a second curse, a
tick after it, held silently); a curse's hold lasting its own record alone (a curse is no strike: the caster's next curse and the
caster's counter and riposte later in the turn are their own); a counter or riposte at one out of reach neither told nor spent, by a
blow's hold or a fall; a lethal blow carrying Death's Door still held once; a curse with no floor paid to its caster at once; the one
record kind and its one finder; the dead refused at each of the three gates, with Pyre's door for the dead still open; and the data
check's rule for the placeholders in an expression's words, with a dash left to f621's one rule.
Run: python tools/sim/carrier_773b_test.py"""
import copy
import inspect
import pathlib
import random
import re
import shutil
import sys
import tempfile
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 1)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import battlefield as bf
from engine import bosses, combat, combat_perks, damage, data_check, martial
from engine import effects as fx
from engine import spellcraft as SC

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def fighter(fid, side, hp=10 ** 6, dmg=12, level=5, name=None, **kw):
    attrs = {a: 12 for a in combat.ATTRIBUTES}
    return combat.Fighter(id=fid, name=name or fid, side=side, level=level, attrs=attrs, hp=hp, max_hp=kw.pop("max_hp", hp),
                          stamina=10 ** 4, max_stamina=10 ** 4, mana=10 ** 4, max_mana=10 ** 4, weapon_damage=dmg,
                          weapon_attrs=["strength"], hold=2, **kw)


def fight(*fs, **kw):
    f = combat.Combat(fighters=list(fs), record=True, serial=kw.pop("serial", "cr"), **kw)
    combat.ensure_field(f)
    f.opened = True
    return f


def lines(f, pat) -> list[int]:
    return [i for i, s in enumerate(f.story) if re.search(pat, s, re.I)]


def falls(f, x) -> list[int]:
    w = re.escape(combat.who(x))
    pat = re.compile(rf"(^|, and |\. ){w} (fall|falls|succumbs|collapse|collapses)\b", re.I)
    return [i for i, s in enumerate(f.story) if pat.search(s)]


REACHES = r"death reaches for"
PAID = []
_on_kill = combat_perks.on_kill


def on_kill(c, att, dfn, rng, echo=False):
    PAID.append((att.id if att is not None else None, dfn.id))
    return _on_kill(c, att, dfn, rng, echo=echo)


combat_perks.on_kill = on_kill


def curse(x, by, per=10, name="Grave Curse", exprs=("deaths_door",)):
    """A curse on x by `by`: per a turn, carrying what its exprs name (Death's Door by default)."""
    fx.put_curse(x, dict(by=by.id, per=per, left=3, name=name, tier="moderate", element="necrotic", exprs=list(exprs)))


def turn_start(f, x, seed=1):
    f.round = 2
    PAID.clear()
    combat.start_turn(x, f, random.Random(seed))


# ---- 1. a curse carrying Death's Door against each floor: its gnaw would end the cursed one, the floor holds it, and holds all of it
def ally_case(make):
    def run():
        p, wolf = fighter("player", "player"), fighter("wolf 1", "enemy")
        x = make(p)
        f = fight(p, x, wolf)
        curse(x, wolf)
        return f, x
    return run


def player_case(setup=None, **kw):
    def run():
        p, wolf = fighter("player", "player", hp=5, max_hp=1000), fighter("wolf 1", "enemy")
        if setup:
            setup(p)
        f = fight(p, wolf, **kw)
        curse(p, wolf)
        return f, p
    return run


def foe_case(setup):
    def run():
        p = fighter("player", "player")
        e = fighter("e1", "enemy", hp=5, max_hp=10 ** 4, name="the warden", behaviors={"fearless": 1})
        setup(e)
        f = fight(p, e)
        bf.engage(f, p, e)
        curse(e, p)
        return f, e
    return run


def lifeline_ash(p):
    p.legendary["lifeline"] = 1
    return fighter("ally_ash", "ally", hp=5, max_hp=1000, name="Ash")


def tethered(p):
    w = fighter("ally_wisp", "ally", hp=5, max_hp=1000, name="Wisp")
    w.tether = 10                                              # held at a tenth: under Death's Door's share, so the door would open
    return w


def boss(e):
    e.boss = bosses.make(bosses.kit_for("beast"), "campaign", "the warden")


def yielding(e):
    e.yields_at, e.yield_text = 0.10, "the warden lowers his blade and walks away"


FLOORS = [
    ("Lifeline", ally_case(lifeline_ash), lambda x, f: x.hp == 1 and x.counters.get("lifeline"),
     r"^The curse should have ended Ash, but the bond with its master will not let it fall \(Lifeline\)$"),
    ("the Soul Tether", ally_case(tethered), lambda x, f: x.hp == 100 and not x.tether,
     r"^The curse should have ended Wisp, but a thread of the master's will draws it back from the brink \(Soul Tether\)$"),
    ("Orenna's Last Breath", player_case(lambda p: setattr(p, "breath", True)), lambda x, f: x.hp == x.max_hp and not x.breath,
     r"^The curse should have killed you, but a thin, tired warmth catches you, and you rise whole \(Orenna's Last Breath, now spent\)$"),
    ("the first hunt", player_case(mentor=True), lambda x, f: x.hp == 1 and f.mentor_saved == 1,
     r"^The curse should have ended you, but a hand catches you before you fall$"),
    ("Deathless", foe_case(lambda e: e.legendary.__setitem__("deathless", 1)), lambda x, f: x.hp == 1,
     r"^The curse should have ended the warden, but it is held on the threshold and will not fall$"),
    ("Deathward", foe_case(lambda e: e.legendary.__setitem__("deathward", 10)), lambda x, f: x.hp == 1001 and x.deathward_used,
     r"^The curse should have killed the warden, but a power older than death refuses to let go \(Deathward\)$"),
    ("a boss's last stand", foe_case(boss), lambda x, f: x.boss["stand_used"], r"BOSS LAST STAND"),
    ("a yielding foe", foe_case(yielding), lambda x, f: x.fled and x.hp >= 1, r"lowers his blade and walks away"),
]
for name, make, after, line in FLOORS:
    f, x = make()
    turn_start(f, x)
    check(f"{name} holds a curse's gnaw that would end them, and stands where the floor leaves them", x.alive and after(x, f),
          (x.hp, x.counters, f.mentor_saved, f.story))
    check(f"{name}: ...told once, in the floor's own line for the curse", len(lines(f, line)) == 1, f.story)
    check(f"{name}: ...and the same curse's Death's Door takes nothing: no line of death, no fall, nobody named or paid",
          not lines(f, REACHES) and not falls(f, x) and x.id not in f.felled_by and PAID == [], (f.story, f.felled_by, PAID))

# ---- 2. the trial, on either side: the curse's gnaw that would end a duellist decides it, told once
for side in ("the examiner", "the player"):
    p = fighter("player", "player", hp=10 ** 6)
    ex = fighter("e1", "enemy", hp=10 ** 6, name="the examiner")
    f = fight(p, ex, players=["player"], duel=True, no_rewards=True)
    bf.engage(f, p, ex)
    target, caster = (ex, p) if side == "the examiner" else (p, ex)
    target.hp, target.max_hp = 5, 10 ** 4
    curse(target, caster)
    turn_start(f, target)
    want = "victory" if target is ex else "defeat"
    check(f"a trial: a curse carrying Death's Door on {side}, its gnaw lethal: held at one and the duel decided",
          target.alive and target.hp == 1 and f.over == want, (target.hp, f.over))
    who = re.escape(combat.who(target))
    check(f"...the trial's line for the curse told once on {side}, and no line of death",
          len(lines(f, rf"^The trial is called before the curse can end {who}, and the duel is decided$")) == 1 and not lines(f, REACHES),
          f.story)

# ---- 3. a curse is no strike: its hold lasts its own record. The caster's next curse is its own harm, as a tick is; and a trial is
#         told once, by the harm that decides it, every harm after it held silently
def trial(more):
    p = fighter("player", "player", hp=10 ** 6)
    ex = fighter("e1", "enemy", hp=5, max_hp=10 ** 4, name="the examiner")
    f = fight(p, ex, players=["player"], duel=True, no_rewards=True)
    bf.engage(f, p, ex)
    curse(ex, p)
    more(f, p, ex)
    turn_start(f, ex)
    return f, ex


f, ex = trial(lambda f, p, ex: curse(ex, p, name="Second Curse", exprs=()))
check("two curses from one caster in a trial: the second is its own harm, told, and held at one silently; the trial called once",
      ex.alive and ex.hp == 1 and f.over == "victory" and len(lines(f, r"^Second Curse gnaws")) == 1
      and len(lines(f, r"the duel is decided")) == 1, (ex.hp, f.over, f.story))
LAID = {}


def poisoned(f, p, ex):
    LAID["poison"] = combat.add_status(f, ex, "poisoned", 3, p)
    fx.set_strength(ex, "poisoned", [50])


f, ex = trial(poisoned)
check("(the examiner carries a lethal poison into the turn)", LAID.get("poison") and "poisoned" in ex.statuses, LAID)
check("a lethal tick after the curse that decided a trial: held at one silently; the trial called once",
      ex.alive and ex.hp == 1 and len(lines(f, r"the duel is decided")) == 1 and not lines(f, r"before the poison"), (ex.hp, f.story))
for second_by in ("the player", "the archer"):
    p = fighter("player", "player")
    archer = fighter("ally_archer", "ally", name="Tam")
    e = fighter("e1", "enemy", hp=5, max_hp=10 ** 4, name="the warden", behaviors={"fearless": 1})
    e.legendary["deathward"] = 10
    f = fight(p, archer, e)
    bf.engage(f, p, e)
    curse(e, p)
    caster = p if second_by == "the player" else archer
    curse(e, caster, per=5000, name="Second Curse", exprs=())
    turn_start(f, e)
    check(f"two curses on a Deathward foe, the second by {second_by}: Deathward holds the first, once; the second is its own harm and "
          "ends the warden, told once and paid to its caster",
          not e.alive and len(lines(f, r"\(Deathward\)$")) == 1 and len(lines(f, r"^Second Curse gnaws")) == 1 and len(falls(f, e)) == 1
          and PAID == [(caster.id, e.id)], (e.hp, f.story, PAID))

# ---- 4. a readied counter and a riposte answer only a blow they may: never told or spent at one out of reach, whatever put it there
COUNTER = combat.Move(id="riposte_form", name="Riposte Form", effect="damage", tier="moderate", reach="melee", resource="stamina",
                      martial_form="counter")
MET = r"^You meet it with Riposte Form$"


def ready(p, kind):
    if kind == "counter":
        p.counter_move = COUNTER.model_dump()
    else:
        fx.put_buff(p, "guard", {"rounds": 5, "mech": {"stance": 1, "riposte": 1}, "drain": 0, "collapse": "", "name": "Guard",
                                 "kind": "stance"})


def answers(f, kind, at=0):
    return [h for h in f.hits[at:] if h["label"] == ("answers with" if kind == "counter" else "ripostes against")]


def spent(p, f, kind):
    return not p.counter_move if kind == "counter" else p.counters.get("riposte_round") == f.round


def meets(att, dfn, c) -> bool:
    """Whether dfn's readied counter meets att's blow now (martial.countering, asked with the fight it is in)."""
    try:
        return martial.countering(att, dfn, c)
    except TypeError:                                         # its form before this change asked no fight
        return martial.countering(att, dfn)


def warden(hp=5):
    e = fighter("e1", "enemy", hp=hp, max_hp=10 ** 4, name="the warden", behaviors={"fearless": 1})
    e.legendary["deathward"] = 10
    return e


for kind in ("counter", "riposte"):                            # the curse's hold is over with its record: the turn's answers land
    p, e = fighter("player", "player", dmg=10 ** 5), warden()
    f = fight(p, e)
    bf.engage(f, p, e)
    curse(e, p)
    ready(p, kind)
    e.always_miss = kind == "riposte"                       # a riposte answers a miss
    f.round = 2
    with combat.in_progress(f, combat.OpenAction()):            # the warden's turn: its start, then its blow at the player
        combat.start_turn(e, f, random.Random(1))
        held = e.alive and e.deathward_used
        combat.apply_damage(f, e, p, 1.0, "bites", random.Random(3), can_cleave=False)
    check(f"the player's curse held by Deathward at the warden's turn start; the player's {kind} later in that turn lands: told, struck, "
          "spent", held and len(answers(f, kind)) == 1 and spent(p, f, kind) and (kind == "riposte" or len(lines(f, MET)) == 1),
          (held, [h["label"] for h in f.hits], f.story))
for kind in ("counter", "riposte"):                            # a blow's hold (f772): the held foe's later blow in the same action
    got = None
    for seed in range(80):
        p, e = fighter("player", "player", dmg=10 ** 5), warden()
        f = fight(p, e)
        bf.engage(f, p, e)
        f.round = 2
        with combat.in_progress(f, combat.OpenAction()):        # one action: the player's strike held by Deathward, then the warden's blow
            combat.apply_damage(f, p, e, 1.0, "strikes", random.Random(seed), can_cleave=False)
            if not e.deathward_used:
                continue
            ready(p, kind)
            e.always_miss = kind == "riposte"
            met_in = meets(e, p, f)
            hits_at, story_at = len(f.hits), len(f.story)
            combat.apply_damage(f, e, p, 1.0, "bites", random.Random(seed + 100), can_cleave=False)
            inside = (len(answers(f, kind, hits_at)), spent(p, f, kind), f.story[story_at:])
        hits_at, story_at = len(f.hits), len(f.story)
        with combat.in_progress(f, combat.OpenAction()):        # the next action: its blow again
            met_after = meets(e, p, f)
            combat.apply_damage(f, e, p, 1.0, "bites", random.Random(seed + 200), can_cleave=False)
        got = (inside, len(answers(f, kind, hits_at)), spent(p, f, kind), f.story[story_at:])
        break
    check(f"(a seed where Deathward holds the player's strike, before the warden's blow, for the {kind})", got is not None)
    if got:
        (n_in, spent_in, story_in), n_after, spent_after, story_after = got
        check(f"the {kind} at a foe a floor held in the player's strike this action: neither told nor spent", n_in == 0 and not spent_in
              and not any(re.search(MET, s) for s in story_in) and not any("riposte" in s for s in story_in), (n_in, spent_in, story_in))
        if kind == "counter":
            check("...nor does the counter meet (weaken) a blow it may not answer, and it meets the one it may",
                  not met_in and met_after, (met_in, met_after))
        check(f"...and kept: the foe's blow in the next action meets it, told and spent", n_after == 1 and spent_after
              and (kind == "riposte" or any(re.search(MET, s) for s in story_after)), (n_after, spent_after, story_after))
got = None
for seed in range(80):                                        # one fallen at its own blow (the thorns): the counter is not told or spent
    p = fighter("player", "player")
    e = fighter("e1", "enemy", hp=50, max_hp=50, name="the warden", behaviors={"fearless": 1})
    f = fight(p, e)
    bf.engage(f, p, e)
    ready(p, "counter")
    fx.put_buff(p, "thorny", {"rounds": 5, "mech": {"thorn_pct": 100, "thorn_flat": 10 ** 5}, "drain": 0, "collapse": "",
                              "name": "Thorny", "kind": "buff"})
    combat.apply_damage(f, e, p, 1.0, "bites", random.Random(seed), can_cleave=False)
    if not e.alive:
        got = f, p, e
        break
check("(a seed where the warden's bite lands and the player's thorns end it)", got is not None)
if got:
    f, p, e = got
    check("a readied counter at a foe its own blow's thorns felled: not told, no strike, and kept for the next",
          not lines(f, MET) and not answers(f, "counter") and bool(p.counter_move), (f.story, p.counter_move))

# ---- 5. the control: a lethal blow carrying Death's Door is still held once
for name, setup, hp in (("Deathless", lambda e: e.legendary.__setitem__("deathless", 1), 1),
                        ("Deathward", lambda e: e.legendary.__setitem__("deathward", 10), 1001)):
    got = None
    for seed in range(60):
        p = fighter("player", "player")
        e = fighter("e1", "enemy", hp=5, max_hp=10 ** 4, name="the warden", behaviors={"fearless": 1})
        setup(e)
        f = fight(p, e)
        bf.engage(f, p, e)
        p.hit_element = p.element = "necrotic"
        p.casting = {"exprs": ["deaths_door"], "tier": "moderate", "name": "Death's Door", "once": []}
        try:
            combat.apply_damage(f, p, e, 5.0, "strikes", random.Random(seed), can_cleave=False)
        finally:
            SC.end(p)
        if any(h["outcome"] not in ("miss", "") for h in f.hits):
            got = (f, e)
            break
    check(f"(a seed where a lethal blow carrying Death's Door lands on a {name} foe)", got is not None)
    if got:
        f, e = got
        check(f"a lethal blow carrying Death's Door on {name}: held once, in the blow's word, and no line of death",
              e.alive and e.hp == hp and len(lines(f, r"^The blow should have")) == 1 and not lines(f, REACHES), (e.hp, f.story))

# ---- 6. a curse with no floor: its death is paid to its caster at once, as before (no tail is to come)
p = fighter("player", "player")
e = fighter("e1", "enemy", hp=5, max_hp=10 ** 4, name="the warden", behaviors={"fearless": 1})
f = fight(p, e)
bf.engage(f, p, e)
curse(e, p)
turn_start(f, e)
check("a curse that ends the warden with no floor: one fall, after the gnaw, the caster named and paid once, at once",
      not e.alive and len(falls(f, e)) == 1 and lines(f, r"^Grave Curse gnaws")[0] < falls(f, e)[0] and f.felled_by.get(e.id) == "you"
      and PAID == [(p.id, e.id)], (f.story, PAID))

# ---- 7. one record of the harm in progress, whatever carries it, and one finder
PEEK = {}
_side, _on_hit, _after_hit = combat.side_damage, SC.on_hit, combat_perks.after_hit


def side_damage(c, dfn, *a, **k):
    PEEK.setdefault("gnaw", list(getattr(c, "_open", None) or []))
    return _side(c, dfn, *a, **k)


def on_hit(c, att, dfn, *a, **k):
    PEEK.setdefault("hit", list(getattr(c, "_open", None) or []))
    PEEK.setdefault("casting", dict(att.casting or {}))
    return _on_hit(c, att, dfn, *a, **k)


def after_hit(c, *a, **k):
    PEEK.setdefault("blow", list(getattr(c, "_open", None) or []))
    return _after_hit(c, *a, **k)


combat.side_damage, SC.on_hit, combat_perks.after_hit = side_damage, on_hit, after_hit
try:
    p = fighter("player", "player")
    e = fighter("e1", "enemy", hp=10 ** 5, name="the warden", behaviors={"fearless": 1})
    f = fight(p, e)
    bf.engage(f, p, e)
    curse(e, p)
    turn_start(f, e)
    for seed in range(40):
        if "blow" in PEEK:
            break
        combat.apply_damage(f, p, e, 1.0, "strikes", random.Random(seed), can_cleave=False)
finally:
    combat.side_damage, SC.on_hit, combat_perks.after_hit = _side, _on_hit, _after_hit
mine = [o for o in PEEK.get("gnaw", []) if not isinstance(o, combat.OpenAction)]
hit = [o for o in PEEK.get("hit", []) if not isinstance(o, combat.OpenAction)]
blow = [o for o in PEEK.get("blow", []) if not isinstance(o, combat.OpenAction)]
check("a curse's turn opens a record of the harm in progress around its gnaw and what it carries: its caster, its target, its word",
      len(mine) == 1 and mine[0].att is p and mine[0].dfn is e and getattr(mine[0], "harm", None) == "curse" and hit == mine,
      (PEEK.get("gnaw"), PEEK.get("hit")))
check("...the same kind of record a blow opens (one record kind, whatever carries the harm)", len(blow) == 1 and bool(mine)
      and type(blow[0]) is type(mine[0]) and getattr(blow[0], "harm", None) == "blow", (blow, mine))
check("...and the casting context it builds names no carrier: the record does", "harm" not in PEEK.get("casting", {"harm": 1}),
      PEEK.get("casting"))
kind = type(mine[0]) if mine else None
finders = sorted(n for n, fn in inspect.getmembers(combat, inspect.isfunction) if fn.__module__ == combat.__name__ and kind is not None
                 and f"isinstance(o, {kind.__name__})" in inspect.getsource(fn))
check("one finder of the harm in progress (engine/combat.py)", len(finders) == 1, finders)
check("...and no stale record or finder is left beside it", not hasattr(combat, "OpenBlow") and not hasattr(combat, "blow_now")
      and not hasattr(combat, "open_blow"), [n for n in ("OpenBlow", "blow_now", "open_blow") if hasattr(combat, n)])
check("...and nothing is held once the turn and the blows are done", getattr(f, "_open", None) == [], getattr(f, "_open", None))

# ---- 8. nothing lands on the dead: each of the three gates refuses one who has left the fight, alive or not
p = fighter("player", "player")
p.legendary["lifeline"] = 1
ash = fighter("ally_ash", "ally", hp=0, max_hp=100, name="Ash")
wolf = fighter("wolf 1", "enemy")
f = fight(p, ash, wolf)
dealt = combat.side_damage(f, ash, 5, wolf, random.Random(1), "physical", told="the splash catches them")
check("side harm handed to a dead Lifeline companion lands nothing: it stays dead, nothing told, nothing dealt",
      not ash.alive and ash.hp == 0 and dealt == 0 and f.story == [], (ash.hp, dealt, f.story))
p = fighter("player", "player", hp=0, max_hp=100)
p.legendary["deathless"] = 1
wolf = fighter("wolf 1", "enemy")
f = fight(p, wolf)
dealt = combat.take_damage(f, p, 5, wolf, random.Random(1))
check("a damage path handed a dead Deathless player runs no floor: it stays dead, nothing told, nothing dealt",
      not p.alive and p.hp == 0 and dealt == 0 and f.story == [], (p.hp, dealt, f.story))
e = fighter("e1", "enemy", hp=0, max_hp=100, name="the warden")
e.legendary["deathward"] = 10
f = fight(fighter("player", "player"), e)
damage.resolve("dot_tick", f, e, 5, None, random.Random(1), dot="poisoned")
check("...nor a tick on a dead Deathward foe", not e.alive and not e.deathward_used and f.story == [], (e.hp, f.story))
check("a status handed to the dead does not land (the `reached` stage)",
      not combat.add_status(f, e, "burning", 3, f.fighters[0]) and "burning" not in e.statuses, e.statuses)
got = None
for seed in range(60):                                        # Pyre's door for the dead stays open: a body burns where it fell
    p = fighter("player", "player", dmg=10 ** 5)
    w = fighter("wolf 1", "enemy", hp=20, max_hp=20)
    f = fight(p, w)
    bf.engage(f, p, w)
    p.hit_element = p.element = "fire"
    p.casting = {"exprs": ["pyre"], "tier": "moderate", "name": "Pyre", "once": []}
    try:
        combat.apply_damage(f, p, w, 1.0, "strikes", random.Random(seed), can_cleave=False)
    finally:
        SC.end(p)
    if not w.alive:
        got = f
        break
check("...while what still works on a kill (Pyre, spellcraft's DEAD_OK) does: the body goes up where it fell",
      got is not None and bool(lines(got, r"body goes up in flames where it fell")), got.story if got else None)

# ---- 9. the data check: the placeholders in an expression's words (its card's are its numbers; every other line is told as it
#         stands, so has none), Dominate's `alone` among them and the line there; a dash in any of them is f621's one rule
check("the tree passes the expressions' check", data_check.allowlist_problems() == [], data_check.allowlist_problems())
EX = copy.deepcopy(SC.EXPR)
EX["dominate"]["alone"] = "there is no one of {whose} own left"
probs = data_check.allowlist_problems(tables={"expressions": EX})
check("an unknown placeholder in Dominate's `alone` is refused (the line is told as it stands)",
      any("dominate.alone" in x and "placeholder" in x for x in probs), probs)
EX["dominate"].pop("alone")
probs = data_check.allowlist_problems(tables={"expressions": EX})
check("...and the line missing", any("dominate" in x and "alone" in x for x in probs), probs)
EX = copy.deepcopy(SC.EXPR)
EX["chill"]["depict"] = "cold sinking into {target}'s limbs"
EX["brittle"]["label"] = "Brittle {tier}"
EX["arc"]["text"] = EX["arc"]["text"] + " ({nowhere})"
probs = data_check.allowlist_problems(tables={"expressions": EX})
check("...by one rule for every expression: a placeholder in another's told words and in its label, and one its card's numbers do not fill",
      any("chill.depict" in x and "placeholder" in x for x in probs) and any("brittle.label" in x and "placeholder" in x for x in probs)
      and any("arc.text" in x and "nowhere" in x for x in probs), probs)
DASHED_ALONE = "there is no one of its own left - the will slides off the dead thing"
EX = copy.deepcopy(SC.EXPR)
EX["dominate"]["alone"] = DASHED_ALONE
probs = data_check.allowlist_problems(tables={"expressions": EX})
check("a dash in Dominate's `alone` is not refused a second time by the expressions' check", not any("dash" in x for x in probs), probs)
tmp = pathlib.Path(tempfile.mkdtemp())
try:
    (tmp / "rules").mkdir()
    text = pathlib.Path("data/rules/spellcraft.yaml").read_text(encoding="utf-8")
    planted = text.replace(SC.EXPR["dominate"]["alone"], DASHED_ALONE)
    (tmp / "rules" / "spellcraft.yaml").write_text(planted, encoding="utf-8")
    probs = data_check.data_words_problems(root=tmp, table={"skip": [], "not_told": {"rules/spellcraft.yaml": {"text": "label"}}})
finally:
    shutil.rmtree(tmp, ignore_errors=True)
check("...it is f621's one rule for every word data/ tells that refuses it, once",
      planted != text and sum("expressions.dominate.alone" in x and "dash" in x for x in probs) == 1 and len(probs) == 1, probs)

combat_perks.on_kill = _on_kill
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
