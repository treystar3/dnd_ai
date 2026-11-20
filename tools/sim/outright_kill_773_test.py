"""(f773) A kill outright goes down a declared path: the floors hold, and the death sets off what a death sets off (found by the code
audit, engine7-3: Death's Door wrote the health itself, with a floor of its own for the duel and the first hunt and none for the rest;
a foe that yields under its share and above its own yielding point was killed, told falling and counted as a kill, where a blow leaves
it at one and yielding; in a trial the duellist was written to one by the spell's floor and the duel was not decided as a blow decides
it; Lifeline, the Soul Tether, Orenna's Last Breath, Deathless and Deathward were passed).
The owner, 2026-11-19 (GOALS.md's top decision row, docs/design/34_one_fall_step.md question 2): every floor holds a kill outright;
bosses never die this way by the card. The kill outright is a damage path of its own in data/rules/stages.yaml (all the health the
fighter has, past any armour, ward or barrier, then the floors the table gives it, the health, the fall and a yielding foe's break),
one more column of the floors table, held to the table by engine/data_check.py; Death's Door takes it in place of writing the health.
The finder's case (a foe that yields, by both routes), then each of the nine floors against it (a blow that carries it: every floor's
line names "the blow"; the boss's last stand on the path itself, since the card never reaches a boss), a boss struck by the card, a
duellist on either side of a trial, a summon finished by it; then each source that can carry it (a spell, a weapon wreathed in the
element, a technique whose element rides its blow, a curse at its turn's start), each with no floor (told, released, credited to the
caster, the rout held to the end of the action) and with Deathless (its line in the word of what carries it: the blow, or the curse);
the path's own word, for a kill outright with no carrier named; then the table and its check, and the hand-made floor gone.
Run: python tools/sim/outright_kill_773_test.py"""
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
import purity
from engine import battlefield as bf
from engine import behaviors, bosses, combat, combat_perks, damage, data_check, summons
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
    f = combat.Combat(fighters=list(fs), record=True, serial=kw.pop("serial", "ok"), **kw)
    combat.ensure_field(f)
    f.opened = True
    return f


def told(f, pat) -> bool:
    return any(re.search(pat, s, re.I) for s in f.story)


def lines(f, pat) -> list[int]:
    return [i for i, s in enumerate(f.story) if re.search(pat, s, re.I)]


def falls(f, x) -> list[int]:
    w = re.escape(combat.who(x))
    pat = re.compile(rf"(^|, and |\. ){w} (fall|falls|succumbs|collapse|collapses)\b", re.I)
    return [i for i, s in enumerate(f.story) if pat.search(s)]


def landed(f, att, dfn=None):
    rec = next((h for h in reversed(f.hits) if h["att"] == att.name and (dfn is None or h["dfn"] == dfn.name)), None)
    return rec is not None and rec.get("outcome") not in ("miss", "phase", "")


DOOR = {"exprs": ["deaths_door"], "tier": "moderate", "name": "Death's Door", "once": []}
REACHES = r"death reaches for"
CB = yaml.safe_load(open("data/rules/combat.yaml", encoding="utf-8"))
ST = yaml.safe_load(open("data/rules/stages.yaml", encoding="utf-8"))
HARMS = CB.get("harms") or {}
OWN = HARMS.get("outright", "")
OWN = OWN[:1].upper() + OWN[1:]                              # the kill outright's own word, as a line begins with it
kill_outright = getattr(combat, "kill_outright", None)

# ---- the probes: every rout rolled, every break made (inside the action's settling or not), every kill paid, every attack roll
MORALE, PAID, HELD, BROKE, ROLLS = [], [], [], [], []
FORCE, SETTLING = {"on": False}, {"on": False}
_morale, _on_kill, _hold, _break, _settle, _roll = (behaviors.morale_on_death, combat_perks.on_kill, combat.hold_break, behaviors._break,
                                                    combat.settle, combat.roll_attack)


class Breaks(random.Random):
    """A rout's die that breaks every foe it is rolled for."""
    def random(self):
        return 0.0


def morale_on_death(c, fallen, rng):
    MORALE.append(fallen.id)
    return _morale(c, fallen, Breaks(0) if FORCE["on"] else rng)


def on_kill(c, att, dfn, rng, echo=False):
    PAID.append((att.id if att is not None else None, dfn.id))
    return _on_kill(c, att, dfn, rng, echo=echo)


def hold_break(c, f, surrender, line):
    out = _hold(c, f, surrender, line)
    HELD.append((f.id, out))
    return out


def broke(c, f, surrender):
    BROKE.append((f.id, SETTLING["on"]))
    return _break(c, f, surrender)


def settle(c, act):
    SETTLING["on"] = True
    try:
        return _settle(c, act)
    finally:
        SETTLING["on"] = False


def roll_attack(att, dfn, c, rng, trace=None):
    ROLLS.append((dfn.id, combat.in_fight(dfn), tuple(x.id for x in c.fighters if not x.alive)))
    return _roll(att, dfn, c, rng, trace=trace)


behaviors.morale_on_death, combat_perks.on_kill, combat.hold_break, behaviors._break = morale_on_death, on_kill, hold_break, broke
combat.settle, combat.roll_attack = settle, roll_attack


def reset():
    for x in (MORALE, PAID, HELD, BROKE, ROLLS):
        x.clear()


def payers(x) -> list:
    return [a for a, d in PAID if d == x.id and a is not None]


def carried_strike(f, att, dfn, seed, mult=0.0001):
    """A blow too light to end anyone (it lands one point), carrying Death's Door."""
    att.hit_element = att.element = "necrotic"
    att.casting = dict(DOOR, once=[])
    try:
        combat.apply_damage(f, att, dfn, mult, "strikes", random.Random(seed), can_cleave=False)
    finally:
        SC.end(att)


# ---- 1. the finder's case: a foe that yields, under Death's Door's share and above its own yielding point
got = None
for seed in range(60):
    reset()
    p = fighter("player", "player")
    e = fighter("e1", "enemy", hp=130, max_hp=1000, name="the Bound Executioner", category="hostile people", behaviors={"fearless": 1})
    e.yields_at, e.yield_text = 0.10, "he lowers the blade and walks away"
    f = fight(p, e)
    bf.engage(f, p, e)
    carried_strike(f, p, e, seed)
    if landed(f, p, e):
        got = (f, p, e)
        break
check("(a seed where the light blow carrying Death's Door lands on the Executioner)", got is not None)
if got:
    f, p, e = got
    check("the finder's case: a foe that yields is never killed outright: held one short, it yields", e.alive and e.fled and e.hp >= 1,
          (e.hp, e.fled, f.story))
    check("...told yielding, not falling, and no line of death reaching him", told(f, "lowers the blade") and not falls(f, e)
          and not told(f, REACHES), f.story)
    check("...nobody named his killer, and no kill is paid", e.id not in f.felled_by and payers(e) == [] and p.kill_round != f.round,
          (f.felled_by, PAID))
dead = 0
for seed in range(40):                                        # the other route: the blow makes him yield, and Death's Door finds him gone
    p = fighter("player", "player")
    e = fighter("e1", "enemy", hp=26, max_hp=100, name="the Bound Executioner", category="hostile people", behaviors={"fearless": 1})
    e.yields_at = 0.25
    f = fight(p, e)
    bf.engage(f, p, e)
    carried_strike(f, p, e, seed, mult=50.0)
    dead += not e.alive
check("...nor by the other route: a blow that makes him yield carries no death to him (40 blows)", dead == 0, dead)


# ---- 2. each floor against a kill outright a blow carries: every floor holds it, in its line for the blow
def door_bite(holder, setup=None, seeds=120):
    """A wolf's bite too light to end anyone, carrying Death's Door, on one at a tenth of their health whom a floor may hold."""
    for seed in range(seeds):
        reset()
        p = fighter("player", "player", hp=10 ** 6)
        wolf = fighter("wolf 1", "enemy")
        x = holder(p)
        f = fight(*([p, x] if x is not p else [p]), wolf, **(setup or {}))
        bf.engage(f, wolf, x)
        carried_strike(f, wolf, x, seed)
        if landed(f, wolf, x):
            return f, p, x
    return None


def low(x, hp=100, max_hp=1000):
    x.hp, x.max_hp = hp, max_hp
    return x


def lifeline_ash(p):
    p.legendary["lifeline"] = 1
    return low(fighter("ally_ash", "ally", name="Ash"))


def tethered(p):
    t = low(fighter("ally_wisp", "ally", name="Wisp"))
    t.tether = 30
    return t


def breathing(p):
    p.breath = True
    return low(p)


def deathless(p):
    p.legendary["deathless"] = 1
    return low(p)


def deathward(p):
    p.legendary["deathward"] = 10
    return low(p)


FLOOR_CASES = [
    ("Lifeline", lifeline_ash, None, lambda x, f: x.hp == 1 and x.counters.get("lifeline"),
     r"^The blow should have ended Ash, but the bond with its master will not let it fall \(Lifeline\)$"),
    ("the Soul Tether", tethered, None, lambda x, f: x.hp == 300 and not x.tether,
     r"^The blow should have ended Wisp, but a thread of the master's will draws it back from the brink \(Soul Tether\)$"),
    ("Orenna's Last Breath", breathing, None, lambda x, f: x.hp == x.max_hp and not x.breath,
     r"^The blow should have killed you, but a thin, tired warmth catches you, and you rise whole \(Orenna's Last Breath, now spent\)$"),
    ("the first hunt", low, {"mentor": True}, lambda x, f: x.hp == 1 and f.mentor_saved == 1,
     r"^The blow should have ended you, but a hand catches you before you fall$"),
    ("Deathless", deathless, None, lambda x, f: x.hp == 1,
     r"^The blow should have ended you, but you are held on the threshold and will not fall$"),
    ("Deathward", deathward, None, lambda x, f: x.hp == 101 and x.deathward_used,
     r"^The blow should have killed you, but a power older than death refuses to let go \(Deathward\)$"),
]
for name, holder, setup, after, line in FLOOR_CASES:
    got = door_bite(holder, setup)
    check(f"(a seed where the wolf's bite carrying Death's Door lands, for {name})", got is not None)
    if not got:
        continue
    f, p, x = got
    check(f"{name} holds a kill outright: the one it holds stands where the floor leaves it", x.alive and after(x, f),
          (x.hp, x.max_hp, x.counters, f.mentor_saved))
    check(f"{name}: ...told in its own line, naming the harm by its word (the blow carried it)", told(f, line), f.story)
    check(f"{name}: ...no line of death reaching them, no fall told, nobody named", not told(f, REACHES) and not falls(f, x)
          and x.id not in f.felled_by, f.story)
    check(f"{name}: ...and once the blow is over, the next blow reaches them", combat.reaches(f, x))

# the duel's floor, on either side: the duellist is held at one and the trial decided, as a blow decides it
for side in ("the examiner", "the player"):
    got = None
    for seed in range(120):
        reset()
        p = fighter("player", "player", hp=10 ** 6)
        ex = fighter("e1", "enemy", hp=10 ** 6, name="the examiner")
        target, striker = (ex, p) if side == "the examiner" else (p, ex)
        low(target)
        f = fight(p, ex, players=["player"], duel=True, no_rewards=True)
        bf.engage(f, p, ex)
        carried_strike(f, striker, target, seed)
        if landed(f, striker, target):
            got = (f, target)
            break
    check(f"(a seed where a blow carrying Death's Door lands on {side} in a trial)", got is not None)
    if got:
        f, target = got
        want = "victory" if target.side == "enemy" else "defeat"
        check(f"a trial: Death's Door on {side} is held at one by the duel's floor, and the duel is decided",
              target.alive and target.hp == 1 and f.over == want, (target.hp, f.over))
        check(f"...told by the duel's line for the blow, and no line of death reaching {side}",
              told(f, rf"^The blow that would have ended {re.escape(combat.who(target))} is pulled short, and the duel is decided$")
              and not told(f, REACHES), f.story)

# a yielding foe's floor is the finder's case (1); a boss's last stand: the card never reaches a boss, the path holds one
got = None
for seed in range(120):
    reset()
    p = fighter("player", "player")
    b = fighter("boar", "enemy", hp=50, max_hp=1000, name="the old boar", category="beast")
    b.boss = bosses.make(bosses.kit_for("beast"), "campaign", "the old boar")
    f = fight(p, b)
    bf.engage(f, p, b)
    carried_strike(f, p, b, seed)
    if landed(f, p, b):
        got = (f, b)
        break
check("(a seed where the blow carrying Death's Door lands on a boss at a twentieth of its health)", got is not None)
if got:
    f, b = got
    check("a boss never dies to Death's Door, by the card: it stands, no line of death reaching it, its last stand unspent",
          b.alive and not told(f, REACHES) and not b.boss["stand_used"], (b.hp, b.boss.get("stand_used"), f.story))
p = fighter("player", "player")
b = fighter("boar", "enemy", hp=50, max_hp=1000, name="the old boar", category="beast")
b.boss = bosses.make(bosses.kit_for("beast"), "campaign", "the old boar")
f = fight(p, b)
check("the kill outright's path is one the fight can take (engine/combat.py kill_outright)", kill_outright is not None)
if kill_outright is not None:
    ended = kill_outright(f, b, p, random.Random(1), "death reaches for the old boar")
    check("...and a boss's last stand holds it there: the boss stands at its last stand, and the caller's line is not told",
          not ended and b.alive and b.boss["stand_used"] and told(f, "BOSS LAST STAND") and not told(f, REACHES), (b.hp, f.story))

# a summon finished this way is unmade, as by a blow
mv = Move(id="bound_test", name="Bound Thing", effect="summon", tier="moderate", reach="self", resource="mana", attribute="intelligence",
          summon_form="bound")
got = None
for seed in range(120):
    reset()
    p, wolf = fighter("player", "player"), fighter("wolf 1", "enemy")
    f = fight(p, wolf)
    f.bound_id = mv.id
    s = summons.make(f, p, mv, form="bound")[0]
    combat.enters(f, s)
    low(s)
    bf.engage(f, wolf, s)
    carried_strike(f, wolf, s, seed)
    if landed(f, wolf, s):
        got = (f, s, wolf)
        break
check("(a seed where the wolf's bite carrying Death's Door lands on the Bound summon)", got is not None)
if got:
    f, s, wolf = got
    check("a summon finished by a kill outright is unmade as by a blow: told once, its spell refused for the fight, the kill the wolf's",
          not s.alive and s.counters.get("dead") and f.bound_fell and len(falls(f, s)) == 1 and payers(s) == [wolf.id],
          (s.hp, s.counters, f.bound_fell, f.story, PAID))


# ---- 3. each source that can carry it, with no floor and with one
def spell(mid, **kw):
    kw.setdefault("reach", "ranged")
    return Move(id=mid, name=mid.replace("_", " ").title(), effect="damage", tier="light", resource="mana", attribute="intelligence",
                element="necrotic", expressions=["deaths_door"], **kw)


BLAST = spell("grave_blast", spell_form="blast")
TOUCH = spell("grave_touch")
CUT = Move(id="grave_cut", name="Grave Cut", effect="damage", tier="light", reach="melee", resource="stamina", element="necrotic",
           expressions=["deaths_door"])
EDGE = Move(id="grave_edge", name="Grave Edge", effect="buff", tier="light", reach="self", resource="mana", buff="imbue",
            element="necrotic", expressions=["deaths_door"])


def pack_fight(seed, floor=False):
    """The player against a pack: its leader at a tenth of its health (under Death's Door's share, above any blow's reach), two
    stout pack-mates beside it, all tied up with the player."""
    p = fighter("player", "player", dmg=12, moves=[BLAST, TOUCH, CUT, EDGE])
    lead = fighter("wolf 1", "enemy", hp=1000, max_hp=10 ** 4, level=6, rank="elite", dmg=0.001)
    if floor:
        lead.legendary["deathless"] = 1
    mates = [fighter(f"wolf {i}", "enemy", hp=10 ** 5, max_hp=10 ** 5, level=3, dmg=0.001) for i in (2, 3)]
    f = fight(p, lead, *mates, serial=f"pk{seed}")
    for x in (lead, *mates):
        if x.zone_id != p.zone_id:
            bf.enter_zone(f, x, p.zone_id)
        bf.engage(f, x, p)
    return f, p, lead, mates


def by_spell(f, p, lead, seed, mv=BLAST):
    combat.act_ability(f, p, mv, lead, random.Random(seed))
    return landed(f, p, lead)


def by_weapon(f, p, lead, seed):
    combat.act_ability(f, p, EDGE, None, random.Random(seed))
    combat.act_attack(f, p, lead, random.Random(seed))
    return landed(f, p, lead)


def by_technique(f, p, lead, seed):
    combat.act_ability(f, p, CUT, lead, random.Random(seed))
    return landed(f, p, lead)


def by_curse(f, p, lead, seed):
    f.round = 2
    fx.put_curse(lead, dict(by="player", per=10, left=2, name="Grave Curse", tier="moderate", element="necrotic", exprs=["deaths_door"]))
    combat.start_turn(lead, f, random.Random(seed))
    return True


SOURCES = [("a spell (an area spell, the pack-mates struck after the leader)", by_spell, "blow"),     # the harm, by what carries it
           ("a weapon wreathed in the element (Imbue)", by_weapon, "blow"),
           ("a technique whose element rides its blow", by_technique, "blow"),
           ("a curse at its turn's start", by_curse, "curse")]
for name, run, harm in SOURCES:
    got = None
    for seed in range(120):
        reset()
        FORCE["on"] = True
        try:
            f, p, lead, mates = pack_fight(seed)
            ok = run(f, p, lead, seed)
        finally:
            FORCE["on"] = False
        if ok and not lead.alive:
            got = (f, p, lead, mates)
            break
    check(f"(a seed where Death's Door, carried by {name}, ends the pack's leader)", got is not None)
    if got:
        f, p, lead, mates = got
        door, fell = lines(f, rf"^Death reaches for {re.escape(combat.who(lead))} and does not let go"), falls(f, lead)
        check(f"{name}: the kill outright is told once, then the fall once, after it", len(door) == 1 and len(fell) == 1 and door[0] < fell[0],
              f.story)
        check(f"{name}: ...released (nobody tied to the fallen, the field whole) and one rout rolled for it",
              not lead.engaged_with and not any(lead.id in o.engaged_with for o in f.fighters) and bf.validate(f) == []
              and MORALE.count(lead.id) == 1, ([(o.id, o.engaged_with) for o in f.fighters], bf.validate(f), MORALE))
        check(f"{name}: ...credited to the caster, once, and named as theirs", payers(lead) == [p.id] and f.felled_by.get(lead.id) == "you",
              (PAID, f.felled_by))
        mine = [m.id for m in mates]
        check(f"{name}: ...the rout it set off is held to the end of the action: each break held, and made only as the action settles",
              sorted(i for i, held_ in HELD if held_) == sorted(mine) and BROKE and all(on for i, on in BROKE if i in mine)
              and all(m.fled and m.alive for m in mates), (HELD, BROKE, [(m.id, m.fled, m.alive) for m in mates]))
        routs = lines(f, r"breaks, seeing")
        check(f"{name}: ...and told after the fall", len(routs) == 2 and all(i > fell[0] for i in routs), f.story)
        if run is by_spell:
            after = [(d, up) for d, up, gone in ROLLS if d in mine and lead.id in gone]
            check(f"{name}: ...the rest of the cast strikes the pack-mates after the leader's fall, each still in the fight",
                  sorted({d for d, up in after}) == sorted(mine) and all(up for d, up in after), ROLLS)
    got = None
    for seed in range(120):
        reset()
        f, p, lead, mates = pack_fight(seed, floor=True)
        if run(f, p, lead, seed) and lead.hp == 1:
            got = (f, p, lead)
            break
    check(f"(a seed where Death's Door, carried by {name}, reaches a Deathless leader)", got is not None)
    if got:
        f, p, lead = got
        word = HARMS.get(harm, "?")
        word = word[:1].upper() + word[1:]
        check(f"{name}: Deathless holds the kill outright: it stands at one, no fall, no rout, no kill paid",
              lead.alive and lead.hp == 1 and not falls(f, lead) and lead.id not in MORALE and payers(lead) == [], (lead.hp, f.story, PAID))
        check(f"{name}: ...told by Deathless in the word of what carries it ({word!r}), with no line of death reaching it",
              told(f, rf"^{re.escape(word)} should have ended {re.escape(combat.who(lead))}, but it is held on the threshold "
                      r"and will not fall$") and not told(f, REACHES), f.story)

# a kill outright with no carrier named (no blow in progress, none named by its caller) is told in the path's own word
p = fighter("player", "player")
x = low(fighter("e1", "enemy", name="the bandit"))
x.legendary["deathless"] = 1
f = fight(p, x)
if kill_outright is not None:
    reset()
    kill_outright(f, x, p, random.Random(1), "death reaches for the bandit")
check("a kill outright with no carrier named: Deathless holds it, told in the path's own word (combat.yaml harms.outright)",
      bool(OWN.strip()) and x.alive and x.hp == 1 and told(f, rf"^{re.escape(OWN)} should have ended the bandit, but it is held on the "
                                                            r"threshold and will not fall$") and not told(f, REACHES), f.story)

# ---- 4. the path, declared once: a column of the floors table, every floor holding it, and the check both ways
PATHS, TABLE = ST["damage"], ST.get("floors") or {}
OWNER = ["duel_floor", "lifeline", "tether", "boss_last_stand", "breath", "mentor_floor", "deathless", "deathward", "yields_floor"]
check("stages.yaml declares the kill outright as a damage path of its own", "outright" in PATHS, sorted(PATHS))
out = PATHS.get("outright") or []
check("...all the health the fighter has, then every floor in the table's order, then the health, the fall and a yielding foe's break",
      out[:1] == ["whole_health"] and "whole_health" in damage.STAGES and [s for s in out if s in TABLE] == OWNER
      and out[len(OWNER) + 1:] == ["health", "fall", "yields_break"], out)
check("...nothing before the floors cuts it: no armour, ward or barrier stage on the path", not ({"resistance", "barrier", "rounded",
      "mana_shield", "stoneskin", "plating", "spellward"} & set(out)), out)
check("every floor of the table holds the kill outright, by the owner's answer (one more column, nothing reshaped)",
      list(TABLE) == OWNER and all(r[:4] == ["blow", "dot_tick", "tear", "rebound"] and "outright" in r for r in TABLE.values()), TABLE)
check("the kill outright's harm has its word in combat.yaml harms (engine/damage.py keeps the key)",
      damage.PATH_HARM.get("outright") in HARMS and bool(OWN.strip()), (getattr(damage, "PATH_HARM", None), HARMS.get("outright")))
check("the tree passes the check", data_check.tables_problems() == [], data_check.tables_problems())
gone = copy.deepcopy(ST)
if gone.get("floors", {}).get("deathward"):
    gone["floors"]["deathward"] = [x for x in gone["floors"]["deathward"] if x != "outright"]
probs = data_check.tables_problems(ST=gone)
check("...and refuses a floor that leaves the kill outright out of its row", any("deathward" in x and "outright" in x for x in probs), probs)
gone = copy.deepcopy(ST)
if "outright" in gone["damage"]:
    gone["damage"]["outright"] = [s for s in gone["damage"]["outright"] if s != "lifeline"]
probs = data_check.tables_problems(ST=gone)
check("...and the path when it leaves out a floor whose row names it", any("lifeline" in x and "outright" in x for x in probs), probs)
bare = copy.deepcopy(CB)
bare["harms"].pop("outright", None)
probs = data_check.tables_problems(CB=bare)
check("...and a table with no word for the kill outright", any("outright" in x and "harms" in x for x in probs), probs)

# ---- 5. no floor by hand: Death's Door takes the path
src = inspect.getsource(SC._express_more)
door_src = src[src.index('eid == "deaths_door"'):]
door_src = door_src[:door_src.index("\n    elif ")]
check("Death's Door writes no health and holds no floor of its own: it takes the kill outright's path",
      ".hp =" not in door_src and "duel_holds" not in door_src and "mentor" not in door_src and "kill_outright" in door_src, door_src)
check("...so the health bar's exemptions no longer list its write (the list only shrinks), and nothing writes outside the law",
      ("engine/spellcraft.py", "dfn.hp = float(floor)") not in purity.HP_EXEMPT and purity.hp_writes() == [] and purity.hp_exempt_missing() == [],
      (purity.hp_writes(), purity.hp_exempt_missing()))

behaviors.morale_on_death, combat_perks.on_kill, combat.hold_break, behaviors._break = _morale, _on_kill, _hold, _break
combat.settle, combat.roll_attack = _settle, _roll
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
