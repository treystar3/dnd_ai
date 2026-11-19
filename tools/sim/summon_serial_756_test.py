"""(f756) Each summon casting has its own serial, whoever has left the fight since (found by the audit, fight-abilities-10: a striker
was cast, a foe left the fight's list as a tamed one does, and the second casting took the first one's serial, which was the length
of the list; the standing cap counts castings by that serial, so it took the two for one, and a third casting let nothing go: three
castings stood where data/rules/summons.yaml allows two). The fighters' list shrinks three ways (a foe tamed, a beast bound with Bind
a Beast, the Executioner freed by the seal), and after any of them a new casting still gets a serial and ids no earlier casting
holds: the cap lets the oldest go, the bodies of one casting (a swarm) still share theirs, and no two fighters share an id. The same
holds for every casting that makes a summon: a plain one, Blood Summons, and a Bound summon made anew in a fight.
Each casting below is read from the bodies it brought into the list, not from the serial under test."""
import os
import random
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("summoner", 1)
simlib.install(stub)
simlib.quiet_console()
sys.stdout = open(os.devnull, "w", encoding="utf-8")         # the fight's panes; the checks go to the real stdout
from core.models import Ability
from engine import battlefield as bf, battlefield_builder as bb, combat, orenna, summons
from engine.combat import Move
from scenes import combat_scene as cs
from services.fight import FightSpec
from storage import saves

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


ROOM = summons.S["standing"]
rng = random.Random(3)


def call(mid, form="striker"):
    return Move(id=mid, name=mid.replace("_", " ").title(), effect="summon", tier="moderate", reach="self", resource="mana",
                attribute="wisdom", summon_form=form, summon_name=f"the {mid.replace('_', ' ')}")


class Casts:
    """The castings of one fight, each as the bodies it brought into the fighters' list."""

    def __init__(self, f, p):
        self.f, self.p, self.made = f, p, []

    def cast(self, move):
        self.p.mana = self.p.max_mana = 10 ** 5
        self.p.cooldowns = {}
        before = list(self.f.fighters)
        why = combat.act_ability(self.f, self.p, move, None, rng)
        new = [x for x in self.f.fighters if not any(x is b for b in before)]
        if new:
            self.made.append((move.id, new))
        return why

    def standing(self):
        """The castings made in the fight (not the Bound summon) with a body still standing, oldest first."""
        return [mid for mid, bodies in self.made if bodies[0].summon_form != "bound" and any(b.alive for b in bodies)]

    def serials(self):
        return [sorted({b.summon_cast for b in bodies}) for _, bodies in self.made]


def own(label, c):
    """Every casting's bodies share one serial and no two castings share one; no two fighters in the fight share an id."""
    sets = c.serials()
    flat = [s[0] for s in sets if len(s) == 1]
    check(f"{label}: each casting has its own serial, its bodies sharing it", len(flat) == len(sets) and len(set(flat)) == len(flat), sets)
    ids = [x.id for x in c.f.fighters]
    check(f"{label}: no two fighters in the fight share an id", len(set(ids)) == len(ids), sorted({i for i in ids if ids.count(i) > 1}))


def then_two_more(label, c, first="striker_a"):
    """A casting after the foe left, then a third: the second has a serial of its own, and the third lets the oldest go."""
    c.cast(call("striker_b"))
    check(f"{label}: the casting after it has a serial of its own", len(set(map(tuple, c.serials()))) == len(c.made), c.serials())
    c.cast(call("striker_c"))
    check(f"{label}: a third casting lets the oldest go, so {ROOM} castings stand", c.standing() == ["striker_b", "striker_c"],
          (c.standing(), c.serials()))
    check(f"{label}: ...and the oldest is gone whole", not any(b.alive for mid, bodies in c.made if mid == first for b in bodies))
    own(label, c)


def gone(f, e):
    return not any(x is e for x in f.fighters)


# ---- the bare engine, as the audit found it: a foe taken out of the list by hand
def player(*mechs):
    attrs = {a: 10 for a in combat.ATTRIBUTES}
    attrs["wisdom"] = 20
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs=attrs, hp=400, max_hp=400, stamina=200, max_stamina=200,
                          mana=10 ** 5, max_mana=10 ** 5, weapon_damage=4, hold=1, armor=10, ward=10,
                          legendary={m: 1 for m in mechs}, mech_names={m: m.title() for m in mechs})


def bare(*mechs):
    p = player(*mechs)
    foes = [combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=10 ** 6,
                           max_hp=10 ** 6, weapon_damage=8, behaviors={"fearless": 1}) for i in range(1, 5)]
    f = combat.Combat(fighters=[p] + foes, record=False)
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    return f, p, foes, Casts(f, p)


f, p, foes, c = bare()
c.cast(call("striker_a"))
f.fighters.remove(foes[3])                                   # as services/fight.py try_tame does
then_two_more("the case that found it (a foe taken out of the list between two castings)", c)

# the seal frees the Bound Executioner (engine/orenna.py seal_attempt): the third way out of the list
f, p, foes, c = bare()
foes[3].bound = True
c.cast(call("striker_a"))
keeper = types.SimpleNamespace(id="keeper", boss={"evidence": 10.0})
freed = False
for _ in range(20):
    if orenna.seal_attempt(f, keeper):
        freed = True
        break
    f.round += 1
check("(the seal is wrested and the Executioner leaves the fight)", freed and gone(f, foes[3]), freed)
then_two_more("the seal frees the Executioner between two castings", c)

# Blood Summons: the blood-spirit is a casting too (engine/combat_perks.py blood_summon makes it through the same line)
f, p, foes, c = bare("blood_summons")
c.cast(call("striker_a"))
check("(Blood Summons: the first casting is a blood-spirit)", [b.name for b in c.made[0][1]] == ["the blood-spirit"], c.made)
f.fighters.remove(foes[3])
then_two_more("Blood Summons, a foe gone before the next casting", c)

# the same spell twice in one round, a foe gone between: two bodies, two ids
f, p, foes, c = bare()
c.cast(call("striker_a"))
f.fighters.remove(foes[3])
c.cast(call("striker_a"))
ids = [b.id for _, bodies in c.made for b in bodies]
check("the same spell cast twice in one round with a foe gone between: each body has its own id", len(ids) == 2 and len(set(ids)) == 2, ids)
check("...and the fight finds each by its id", all(f.get(b.id) is b for _, bodies in c.made for b in bodies))
own("the same spell twice in one round", c)

# nobody leaves: the serial and the id are what they were (the length of the list), so no recorded fight moves
f, p, foes, c = bare()
for mid in ("striker_a", "striker_b", "striker_c", "striker_d"):
    n = len(f.fighters)
    c.cast(call(mid))
    body = c.made[-1][1][0]
    check(f"nobody has left: {mid}'s serial and id are taken from the list's length, as before",
          body.summon_cast == n and body.id == f"summon_{mid}_{f.round}_0_{n}", (body.summon_cast, body.id, n))
check(f"nobody has left: never more than {ROOM} castings stand", c.standing() == ["striker_c", "striker_d"], c.standing())

# ---- through the fight service: the taming and the binding done by services/fight.py try_tame and try_bind themselves
NAME = "summon_serial"
g = simlib.campaign(NAME, cls="summoner", seed=7, location="parth")
ws = g.scene
ws.enter("parth")
ch = ws.player.character
WARDEN = ch.bound_summon
check("(the stand-in summoner is bound to its Warden, and both tames and summons)", WARDEN and ch.uses_companions, (WARDEN, ch.uses_companions))
dart = next(a for a in ch.actives if a.effect == "damage")
BIND = Ability.model_validate({**dart.model_dump(), "id": "bind", "name": "Beast Bond", "effect": "control", "context": "both",
                               "field_use": "bind_beast", "resource": "mana", "tier": "moderate", "reach": "ranged"})
ch.actives.append(BIND)
ch.prepared = list(ch.prepared) + [BIND.id]
ch.level = 30                                                # room for two tamed creatures (data/rules/taming.yaml cap)
KEPT = list(ch.companions)
svc = cs.service_of(ws, random.Random(11))
WOLF = ws.world.bestiary["wolf"]


class Sure(random.Random):
    """Dice that never miss: the taming and the binding take."""

    def random(self):
        return 0.0


def begin(broken=False):
    ch.bound_broken = broken
    ch.companions[:] = KEPT
    ws.player.field = {}
    wolves = []
    for i in range(1, 5):
        e = combat.fighter_from_creature(WOLF, ch.level, "normal", f"e{i}", "wolf", "near")
        e.behaviors["fearless"] = 1
        wolves.append(e)
    f, _ = svc.begin(FightSpec(creature=WOLF, enemies=wolves, battlefield=bb.duel_ground(), place="the test ground"))
    c = Casts(f, f.player)
    warden = summons.bound_of(f, f.player)
    if warden is not None:
        c.made.append((WARDEN, [warden]))
    return f, c, [f.get(f"e{i}") for i in range(1, 5)]


def tame(f, e):
    e.hp = 1.0
    held, svc.dice = svc.dice, Sure(1)
    notes = []
    svc.try_tame(f, e, notes)
    svc.dice = held
    return gone(f, e)


def bind(f, e):
    move = next(m for m in f.player.moves if m.id == BIND.id)
    f.player.mana = 10 ** 5
    held, svc.dice = svc.dice, Sure(1)
    notes = []
    svc.try_bind(f, move, BIND, e, notes)
    svc.dice = held
    return gone(f, e)


f, c, wolves = begin()
check("(the Warden walks in with the summoner)", len(c.made) == 1, c.made)
c.cast(call("striker_a"))
check("(a wolf is tamed through the fight service and leaves the fight)", tame(f, wolves[0]))
then_two_more("a wolf tamed (services/fight.py try_tame) between two castings", c)

f, c, wolves = begin()
c.cast(call("striker_a"))
check("(a wolf is bound with Bind a Beast through the fight service and leaves the fight)", bind(f, wolves[0]))
then_two_more("a wolf bound (services/fight.py try_bind) between two castings", c)

# a swarm first: its bodies share one serial, and the next casting gets another, even with three gone from the list since
f, c, wolves = begin()
pack = next(m for m in f.player.moves if m.summon_form == "swarm")
c.cast(pack)
check("(the swarm is three bodies)", len(c.made[-1][1]) == 3, c.made[-1])
wolves[2].bound = True
left = [tame(f, wolves[0]), bind(f, wolves[1]), orenna.seal_attempt(f, types.SimpleNamespace(id="keeper", boss={"evidence": 10.0}))
        or orenna.seal_attempt(f, types.SimpleNamespace(id="keeper2", boss={"evidence": 10.0}))]
check("(three leave the list after the swarm: tamed, bound, freed by the seal)", all(left) and gone(f, wolves[2]), left)
then_two_more("a swarm, then a wolf tamed, one bound and one freed by the seal", c, first=pack.id)

# a Bound summon made anew in the fight (f749) is a casting like any other: a serial no earlier casting holds
f, c, wolves = begin(broken=True)
check("(broken, the Warden does not walk in)", not c.made, c.made)
c.cast(call("striker_a"))
tame(f, wolves[0])
why = c.cast(next(m for m in f.player.moves if m.id == WARDEN))
check("(the Warden is made anew in the fight)", why is None and summons.bound_of(f, f.player) is not None, why)
own("the Warden made anew after a wolf was tamed", c)

ws.store.save_combat(None)
g.close()
saves.drop(NAME)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
