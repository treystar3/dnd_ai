"""(f769) One turn a fighter a round, and none for a fighter who is out of the fight (found by the code audit, engine2-1, trace-fight-1
and trace-fight-10: four bandits, the first hurt yields on its own turn and the yield spreads, and a bandit that had yielded was handed
its turn and struck the player; routed wolves bit after their leader fell to a riposte or to thorns; a foe Dread Regent turned in the
foes' phase took two turns in the round, its statuses worn down twice). The round's order is made once, but who takes a turn is asked
at the moment of the turn by every way into one (start_turn, enemy_turn, ally_turn: combat.takes_turn), and finish_round keeps the ids
that have had their turn this round, so a foe turned in mid phase acts once.
The kind: every fighter whose state changed after the round's order was made, on each side (a foe, an ally, a turned foe, the player),
each way out of the fight (down, fled, yielded, off the field), and each way into a turn (finish_round's three loops; enemy_turn,
ally_turn and start_turn called alone, as the tests do; simulate, as the tools' bots and the danger estimate do; and the service's
round for the player). The finder's case, then: a riposte fells the wolves' leader and the routed wolves still bite; thorns kill the
leader in the foes' phase; a befuddled ogre fells goblins that have yet to act (and were caught unaware); Dread Regent turns a foe
inside its own turn and inside another's; a foe that yields at its own turn's start (a curse) still strikes; each side and each way
out staged in the middle of each loop; and each way in called alone.
Counted by wrapping enemy_turn, ally_turn, start_turn, apply_damage and turned_turn, never by reading the story: no turn and no blow
from a fighter out of the fight, a turn path handed one tells, logs and changes nothing, at most one start_turn a fighter a round, and
battlefield.validate == [] when the round ends. What must still hold: a foe turned before the round takes its one turn, a stunned foe
and a stunned player are still told they cannot act, and everyone standing acts once.
Run: python tools/sim/turn_once_769_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import battlefield as bf
from engine import battlefield_builder as bb
from engine import combat, combat_perks, streams
from engine import effects as fx
from engine.battlefield import Battlefield, BattleEdge, BattleZone
from scenes import combat_scene as cs
from scenes.combat_scene import CombatScene
from services.fight import RoundIntent
from ui import console

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


game = simlib.campaign("turn_once_769", cls="warrior", seed=7, location="parth")
ws = game.scene
W = ws.world

# ---- the probes: every turn started, every blow struck, every turned turn, and every turn path handed one out of the fight that did
# something (a line, a log line, a blow's record, a change on the fighter)
STARTS, BLOWS, TURNED, LOUD, AFTER = [], [], [], [], {}
_enemy_turn, _ally_turn, _start_turn = combat.enemy_turn, combat.ally_turn, combat.start_turn
_apply_damage, _turned_turn = combat.apply_damage, combat_perks.turned_turn


def out(c, f) -> bool:
    """Out of the fight: down, fled or yielded, or off the field (tamed, bound, freed)."""
    return not f.alive or f.fled or (c is not None and all(x is not f for x in c.fighters))


def seen(c, f):
    return len(c.story), len(c.log), len(c.told), len(c.hits), f.model_dump()


def turn_spy(real):
    def turn(c, f, rng):
        was = seen(c, f) if out(c, f) else None
        try:
            return real(c, f, rng)
        finally:
            if was is not None and seen(c, f) != was:
                LOUD.append(f.id)
            if f.id in AFTER:
                AFTER.pop(f.id)(c)                          # staged: what happens to someone else once this fighter's turn is done
    return turn


def start_turn(f, c=None, rng=None):
    STARTS.append((c.round if c is not None else None, f.id, out(c, f)))
    return _start_turn(f, c, rng)


def apply_damage(c, att, dfn, *a, **k):
    BLOWS.append((att.id, out(c, att)))
    return _apply_damage(c, att, dfn, *a, **k)


def turned_turn(c, e, rng):
    TURNED.append(e.id)
    return _turned_turn(c, e, rng)


combat.enemy_turn, combat.ally_turn = turn_spy(_enemy_turn), turn_spy(_ally_turn)
combat.start_turn, combat.apply_damage, combat_perks.turned_turn = start_turn, apply_damage, turned_turn


def reset():
    for x in (STARTS, BLOWS, TURNED, LOUD):
        x.clear()
    AFTER.clear()


def faults(c) -> list:
    """What every round must hold: nobody out of the fight starts a turn or strikes, a turn path handed one does nothing, nobody starts
    two turns in a round, and the field holds together."""
    got = []
    starts = [(r, i) for r, i, _ in STARTS]
    got += [f"{i} starts {starts.count((r, i))} turns in round {r}" for r, i in sorted(set(starts)) if starts.count((r, i)) > 1]
    got += [f"{i} starts a turn out of the fight" for _, i, o in STARTS if o]
    got += [f"{i} strikes out of the fight" for i, o in BLOWS if o]
    got += [f"{i} is handed a turn out of the fight, and something of it happens" for i in LOUD]
    return got + bf.validate(c)


def left_first(c, stood) -> bool:
    """The case arose: someone standing when the round began was out of the fight before it had a turn of its own."""
    return any(out(c, f) and not any(i == f.id and not o for _, i, o in STARTS) for f in stood)


def rounds(name, n, build, arose=left_first, more=None):
    """finish_round on n seeds of the fight build(seed) makes: every round must hold, and the case must arise in some."""
    hits, broke, shown = 0, 0, None
    for s in range(n):
        reset()
        c = build(s)
        stood = [f for f in c.fighters if f.side != "player" and not out(c, f)]
        combat.finish_round(c, random.Random(s))
        hits += bool(arose(c, stood))
        got = faults(c) + (more(c) if more else [])
        if got:
            broke += 1
            shown = shown or (s, got[:4], c.story[-8:])
    check(f"(the case arises: {name})", hits > 0, hits)
    check(f"{name}: no turn, no blow and no line from a fighter out of the fight, one turn each ({n} seeds)", broke == 0,
          f"{broke} rounds broke; the first: {shown}")
    return hits


# ---- fighters: the bestiary's, on two zones, every foe engaged with the player (as the audit built them)
def foe(cid, lvl, i, rank="normal"):
    return combat.fighter_from_creature(W.bestiary[cid], lvl, rank, f"e{i}", name=f"{cid} {i + 1}")


def me(**k):
    d = dict(id="player", name="you", side="player", level=20, attrs={a: 20 for a in combat.ATTRIBUTES}, hp=400, max_hp=400,
             weapon_damage=5, weapon_name="stick", stamina=500, max_stamina=500, mana=0, max_mana=0, armor=0)
    d.update(k)
    return combat.Fighter(**d)


def arena(*fs):
    c = combat.Combat(fighters=list(fs))
    c.battlefield = Battlefield(zones={"z1": BattleZone(id="z1", name="the ground"), "z2": BattleZone(id="z2", name="the far side")},
                                edges=[BattleEdge(a="z1", b="z2")], start="z1")
    for f in fs:
        f.zone_id, f.row = "z1", ("back" if f.reach == "ranged" else "front")
    for f in fs:
        if f.side == "enemy":
            bf.engage(c, c.player, f)
    c.opened = True
    return c


# bare fighters, on the duel ground (as tools/sim/perks_round2_test.py builds them)
def player(*mechs, hp=5000, **kw):
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: 14 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
                          stamina=200, max_stamina=200, mana=200, max_mana=200, weapon_damage=kw.pop("weapon_damage", 10), hold=1,
                          legendary={m: 1 for m in mechs}, mech_names={m: m.replace("_", " ").title() for m in mechs}, **kw)


def wolf(i, hp=10, max_hp=10, level=3, dex=10, **k):
    d = dict(id=f"e{i}", name=f"wolf {i}", side="enemy", level=level, attrs={"strength": 10, "dexterity": dex}, hp=hp, max_hp=max_hp,
             category="beast", pace="fast", weapon_damage=4, family="pack_hunter", behaviors={"flee_low": 0.25})
    d.update(k)
    return combat.Fighter(**d)


def friend(i, hp=10 ** 5, **k):
    d = dict(id=f"ally_{i}", name=f"friend {i}", side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
             stamina=200, max_stamina=200, weapon_damage=6, hold=2)
    d.update(k)
    return combat.Fighter(**d)


def ground(*fs, rnd=2):
    f = combat.Combat(fighters=list(fs), record=True, serial="to")
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    f.opened = True
    f.round = rnd
    return f


streams.begin(7, 1, "I fight.")

# ---- 1. the finder's case: four bandits, the first hurt; it yields on its own turn and the yield spreads
def bandits(s):
    lead = foe("bandit", 20, 0)
    lead.hp = lead.max_hp * 0.1
    return arena(me(), lead, *[foe("bandit", 5, i + 1) for i in range(3)])


rounds("the finder's case, a yield that spreads among bandits", 400, bandits)


# ---- 2. a riposte fells the wolves' leader on its own turn and the pack breaks: the routed wolves do not bite
def riposte(s):
    alpha = foe("wolf", 8, 0, rank="elite")
    alpha.hp, alpha.attrs["dexterity"] = 1, 30
    p = me(weapon_damage=40)
    p.legendary["riposte"] = 1
    return arena(p, alpha, *[foe("wolf", 3, i + 1) for i in range(3)])


rounds("a riposte fells the leader and the pack breaks", 400, riposte)


# ---- 3. thorns kill the leader in the foes' phase: the routed pack does not bite
def thorns(s):
    alpha = foe("wolf", 8, 0, rank="elite")
    alpha.hp, alpha.attrs["dexterity"] = 1, 30
    p = me()
    p.legendary["thorns"] = 100
    return arena(p, alpha, *[foe("wolf", 3, i + 1) for i in range(3)])


rounds("thorns kill the leader in the foes' phase", 400, thorns)


# ---- 4. a befuddled ogre fells goblins that have yet to act, caught unaware: nothing is told of the dead
def befuddled(s):
    ogre = foe("ogre", 10, 0)
    ogre.attrs["dexterity"] = 30
    gob = [foe("goblin", 3, i + 1) for i in range(2)]
    for g in gob:
        g.hp = 1
        fx.put_status(g, "unaware", 1)
    p = me(hp=1000, max_hp=1000)
    p.hp = 100
    p.legendary["rampage"] = 1
    c = arena(p, ogre, *gob)
    combat.add_status(c, ogre, "befuddled", 2, p)
    return c


rounds("a befuddled ogre fells goblins yet to act", 400, befuddled)


# ---- 5. Dread Regent turns a foe inside its own turn: one turn start, its weakness worn down once
def regent_own(s):
    a = wolf(1, hp=2, dex=18)                                 # hurt below its flee share, and first to act
    big = dict(behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5)
    f = ground(player("dread_regent"), a, wolf(2, dex=8, **big), wolf(3, dex=6, **big))
    fx.put_status(a, "weakened", 6)
    return f


def turned(c, stood):
    return any(f.counters.get("turned") for f in stood)


def worn_once(c):
    a = c.get("e1")
    return [] if not a.counters.get("turned") or a.statuses.get("weakened") == 5 else [f"weakened worn to {a.statuses.get('weakened')}"]


rounds("Dread Regent turns a foe inside its own turn", 400, regent_own, arose=turned, more=worn_once)


# ---- 6. ...and inside another's, before its own: it acts once, as a turned foe
def regent_other(s):
    lead = wolf(1, hp=2, dex=18, level=6, behaviors={"surrender": 0.5}, category="hostile people", name="the captain")
    b = wolf(2, dex=8, behaviors={}, hp=10 ** 5, max_hp=10 ** 5)
    c = wolf(3, dex=6, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5)
    return ground(player("dread_regent"), lead, b, c)


def struck_once(c):
    return [f"{i} takes {TURNED.count(i)} turned turns" for i in set(TURNED) if TURNED.count(i) > 1]


rounds("Dread Regent turns a foe inside another's turn", 600, regent_other, arose=turned, more=struck_once)


# ---- 7. what must still hold: a foe turned before the round takes its one turn, against its old side
ok = 0
for s in range(40):
    reset()
    big = dict(behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5, weapon_damage=0.001)
    f = ground(player("dread_regent"), wolf(1, **big), wolf(2, **big), wolf(3, **big))
    combat_perks.turn_coat(f, f.get("e1"))
    combat.finish_round(f, random.Random(s))
    ok += TURNED == ["e1"] and [i for _, i, _ in STARTS].count("e1") == 1 and not faults(f)
check("a foe turned before the round takes one turn, a turned one, in the turned loop (40 seeds)", ok == 40, ok)

# ---- 8. everyone standing acts once: two allies, three foes, nobody out
reset()
f = ground(player(), friend(1), friend(2), *[wolf(i, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5) for i in (1, 2, 3)])
combat.finish_round(f, random.Random(3))
check("everyone standing takes one turn: two allies, three foes", sorted(i for _, i, _ in STARTS) == ["ally_1", "ally_2", "e1", "e2", "e3"]
      and not faults(f), (STARTS, faults(f)))


# ---- 9. a foe that yields at its own turn's start (a curse) does not strike, and is not told as reeling
def cursed(s):
    e = wolf(1, hp=100, max_hp=100, behaviors={}, family="", yields_at=0.5, yield_text="the first wolf throws itself flat and yields")
    other = wolf(2, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5, family="")
    f = ground(player(), e, other)
    bf.engage(f, e, f.player)
    fx.put_curse(e, dict(by="player", per=10 ** 4, left=2, name="Grave Curse", tier="moderate", element="necrotic", exprs=[]))
    return f


def yielded_at_start(c, stood):
    return c.get("e1").fled and c.get("e1").alive


def not_reeling(c):
    return [s for s in c.story if "unable to act" in s] + [s for s in c.log if "loses its turn" in s]


rounds("a foe that yields at its own turn's start", 20, cursed, arose=yielded_at_start, more=not_reeling)
reset()
f = cursed(0)
fx.put_status(f.get("e1"), "stunned", 2)
combat.enemy_turn(f, f.get("e1"), random.Random(1))
check("...stunned as well: the yield is told, never 'reels, unable to act'", f.get("e1").fled and not not_reeling(f) and not faults(f),
      (f.story, faults(f)))
f = ground(player(), wolf(1, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5))
fx.put_status(f.get("e1"), "stunned", 2)
combat.enemy_turn(f, f.get("e1"), random.Random(1))
check("...while a stunned foe still in the fight is told it reels, once", sum("unable to act" in s for s in f.story) == 1, f.story)


# ---- 10. each side and each way out, staged in the middle of each loop: the one taken out has no turn when its slot comes
def take_out(way, x, by):
    def do(c):
        if way == "down":
            combat.take_damage(c, x, 10 ** 7, by, random.Random(0))
        else:
            combat.leave(c, x, way)
    return do


WAYS = ("down", "fled", "yielded", "gone")
for way in WAYS:
    # the foes' loop: the second wolf, poisoned, is taken out during the first's turn
    reset()
    p = player()
    e1, e2 = wolf(1, dex=30, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5), wolf(2, dex=5, behaviors={"fearless": 1})
    f = ground(p, e1, e2)
    bf.engage(f, e2, p)
    combat.add_status(f, e2, "poisoned", 3, p)
    AFTER["e1"] = take_out(way, e2, p)
    combat.finish_round(f, random.Random(1))
    check(f"the foes' loop: a foe {way} during another's turn has none of its own", out(f, e2) and "e2" not in [i for _, i, _ in STARTS]
          and not faults(f), (STARTS, faults(f)))
    # the allies' loop: the second friend, poisoned, is taken out during the first's turn
    reset()
    p, a1, a2 = player(), friend(1), friend(2)
    e = wolf(1, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5, weapon_damage=0.001)
    f = ground(p, a1, a2, e)
    combat.add_status(f, a2, "poisoned", 3, e)
    AFTER["ally_1"] = take_out(way, a2, e)
    combat.finish_round(f, random.Random(1))
    check(f"the allies' loop: an ally {way} during another's turn has none of its own", out(f, a2)
          and "ally_2" not in [i for _, i, _ in STARTS] and not faults(f), (STARTS, faults(f)))
    # the turned loop: two turned foes, the second taken out during the first's turned turn
    reset()
    big = dict(behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5, weapon_damage=0.001)
    p = player()
    t1, t2, o1, o2 = wolf(1, **big), wolf(2, behaviors={"fearless": 1}), wolf(3, **big), wolf(4, **big)
    f = ground(p, t1, t2, o1, o2)
    for t in (t1, t2):
        t.counters["turned"] = 1
        bf.release(f, t)
    combat.add_status(f, t2, "poisoned", 3, p)
    AFTER["e1"] = take_out(way, t2, o1)
    combat.finish_round(f, random.Random(1))
    check(f"the turned loop: a turned foe {way} during another's turn has none of its own", out(f, t2) and "e2" not in TURNED
          and "e2" not in [i for _, i, _ in STARTS] and not faults(f), (STARTS, TURNED, faults(f)))


# ---- 11. each way in, called alone (as the tests and the tools call them): a fighter out of the fight is handed nothing
def quiet(name, c, x, call, own_start=False):
    """A way into a turn called alone on one out of the fight: nothing told, logged or changed, no blow, and no start_turn but the
    one called (own_start)."""
    reset()
    was = seen(c, x)
    got = call()
    check(name, seen(c, x) == was and not [i for _, i, _ in STARTS if i != x.id or not own_start] and not BLOWS and not TURNED,
          (c.story[was[0]:], c.log[was[1]:], STARTS, BLOWS))
    return got


for way in WAYS:
    for extra in ("", "unaware", "the will lifts", "winding"):
        p = player()
        e, other = wolf(1, behaviors={"fearless": 1}, hp=40, max_hp=40), wolf(2, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5)
        f = ground(p, e, other)
        bf.engage(f, e, p)
        combat.add_status(f, e, "poisoned", 3, p)
        if extra == "unaware":
            fx.put_status(e, "unaware", 1)
        elif extra == "the will lifts":
            e.counters.update(turned=1, turned_until=0)            # a Dominate run out
        elif extra == "winding":
            e.winding = {"target": "player", "round": 1}
        take_out(way, e, p)(f)
        quiet(f"enemy_turn on a foe {way}{', ' + extra if extra else ''}: nothing told, logged, rolled or changed", f, e,
              lambda: combat.enemy_turn(f, e, random.Random(2)))
    p, a = player(), friend(1)
    e = wolf(1, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5)
    f = ground(p, a, e)
    combat.add_status(f, a, "poisoned", 3, e)
    a.cooldowns["guard"] = 2
    take_out(way, a, e)(f)
    quiet(f"ally_turn on an ally {way}: nothing told, logged, rolled or changed", f, a, lambda: combat.ally_turn(f, a, random.Random(2)))
    for side in ("enemy", "ally", "player"):
        if side == "player" and way in ("yielded", "gone"):
            continue                                                # the player neither yields nor leaves the field
        p, a = player(), friend(1)
        e = wolf(1, behaviors={"fearless": 1}, hp=10 ** 5, max_hp=10 ** 5)
        f = ground(p, a, e)
        x = {"enemy": e, "ally": a, "player": p}[side]
        combat.add_status(f, x, "poisoned", 3, e if x is not e else p)
        fx.put_status(x, "weakened", 3)
        x.cooldowns["guard"] = 2
        take_out(way, x, e if x is not e else p)(f)
        got = quiet(f"start_turn on {'the player' if side == 'player' else 'a foe' if side == 'enemy' else 'an ally'} {way}: "
                    "no turn, and nothing ticks, wears down or is told", f, x, lambda: combat.start_turn(x, f, random.Random(2)),
                    own_start=True)
        check(f"...start_turn says so ({side}, {way})", got is False, got)


# ---- 12. simulate, as the tools' bots and the danger estimate play a fight: no round of it breaks the rule
broke, shown = 0, None
for s in range(60):
    reset()
    played = combat.simulate((bandits, riposte, thorns)[s % 3](s), random.Random(s), max_rounds=12)
    if faults(played):
        broke += 1
        shown = shown or (s, faults(played)[:4])
check("simulate: whole fights, no turn and no blow from a fighter out of the fight, one turn each a round (60 fights)", broke == 0,
      (broke, shown))

# ---- 13. the service's round: a player out of the fight is not told 'your body will not answer', and does not strike; a stunned
# player still is told it
console.put("combat_state", lambda data: False)
console.put("combat_panel", lambda lines: None)
ws.enter("parth")
creature = ws.world.bestiary["wolf"]


def service_fight():
    w = combat.fighter_from_creature(creature, 3, "normal", "e1", name="wolf 1")
    w.hp = w.max_hp = 10 ** 6
    w.weapon_damage = 0.001
    w.behaviors["fearless"] = 1
    ws.narrate_with = lambda *a, **k: None
    sc = CombatScene.begin(ws, creature, [w], "It is on you:")
    ws.combat = sc
    return sc.fight, cs.service_of(ws)


f, svc = service_fight()
p = f.player
fx.put_status(p, "stunned", 2)
f.story.clear()
streams.begin(ws.store.meta.seed, 50, "I attack the wolf.")
with ws.operation("test:round", "I attack the wolf."):
    svc.round(f, RoundIntent(kind="attack", target="e1", words="I attack the wolf."))
check("the service's round, a stunned player: told once that the body will not answer",
      sum("will not answer" in s for s in f.story) == 1, f.story)
f, svc = service_fight()
p = f.player
combat.add_status(f, p, "poisoned", 3, f.get("e1"))
fx.put_status(f.get("e1"), "stunned", 2)                     # the wolf loses its own turn: only the player's is measured here
combat.leave(f, p, "fled")
reset()
f.story.clear()
before, hp0 = p.model_dump(), p.hp
streams.begin(ws.store.meta.seed, 51, "I attack the wolf.")
with ws.operation("test:round", "I attack the wolf."):
    svc.round(f, RoundIntent(kind="attack", target="e1", words="I attack the wolf."))
check("the service's round, a player out of the fight: no 'will not answer', no blow, nothing of the turn on them (the poison "
      "does not tick)", not any("will not answer" in s for s in f.story) and not [i for i, _ in BLOWS if i == p.id]
      and p.model_dump() == before, (f.story, BLOWS, p.hp, hp0))
ws.combat = None
game.close()

check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
