"""(f766) A fighter leaves a fight one way: released first, and never told as gone when it fell (found by the code audit,
trace-fight-7: a wolf engaged with a bow user was tamed through the service's own round, the player kept its id, the battlefield's
check said "engaged with 'e1', who is not standing" and every later shot carried the point-blank step of -15; engine1-3 and
trace-fight-11: a runner cut down by the parting strike of No One Escapes was set fled, told as running after its fall, and the body
was not counted). The kind: every way a living fighter goes out of a fight (it flees, yields, stands down, bolts, is tamed, bound or
freed), and every break that did not happen because the fighter fell or turned first. One engine function, combat.leave, releases
every tie and then sets the fighter fled or yielded or takes it off the field, and refuses one who is down; _break says whether the
foe broke, and its callers tell their line and roll the follow-on morale only when it did. The readers of a tie (the point-blank
step, the pane's where) count only someone standing, a fight row read back lets go of a stale tie and says so in its log, and
tools/purity.py fences writes of .fled and removals from the fighter list outside combat.leave.
The finder's case (taming through the service's round), then the rest of the kind: the seal freeing the Bound Executioner, a foe
persuaded to stand down, a turned foe that flees, a foe that turns its coat when it would have broken, No One Escapes killing the
runner beside two parting strikes that leave it alive and fled, the mend on reading, and the fence. Every case asserts
battlefield.validate == [] on the fight in hand, before any row is written and read back.
Run: python tools/sim/leaves_fight_766_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("ranger", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import battlefield as bf
from engine import battlefield_builder as bb
from engine import behaviors, combat, combat_perks, movement, orenna, parley, streams
from scenes import combat_scene as cs
from services.fight import FightService, FightSpec, RoundIntent
from tools import purity
from ui import console

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def man(i, side="enemy", hp=400, lvl=5, **kw):
    return combat.Fighter(id="player" if side == "player" else f"e{i}", name="you" if side == "player" else f"foe {i}", side=side,
                          level=lvl, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=hp, max_hp=kw.pop("max_hp", hp), stamina=200,
                          max_stamina=200, weapon_damage=8, hold=1, category=kw.pop("category", "hostile people"), **kw)


def field(*fs, serial="lf"):
    f = combat.Combat(fighters=list(fs), record=True, serial=serial)
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    f.opened = True
    return f


def point_blank(att, dfn, f) -> list:
    return [s for s in combat.hit_parts(att, dfn, f)[1] if "point-blank" in s[0]]


class Zero:
    """A die that always rolls lowest: every chance below it comes up (a flight, a morale break)."""
    def random(self):
        return 0.0

    def uniform(self, a, b):
        return a


leave = getattr(combat, "leave", None)

# ---- 1. the finder's case: a wolf engaged with a bow user is tamed through the service's own round
console.put("combat_state", lambda data: False)
console.put("combat_panel", lambda lines: None)
NAME = "leaves_fight_sim"
game = simlib.campaign(NAME, cls="ranger", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")
c = ws.player.character
c.uses_companions = True                                     # a companion class: tame, not bind
svc = cs.service_of(ws)
creature = ws.world.bestiary["wolf"]
foes = []
for i in (1, 2):
    e = combat.fighter_from_creature(creature, 1, "normal", f"e{i}", f"wolf {i}", "near")
    e.behaviors["fearless"] = 1
    foes.append(e)
streams.begin(store.meta.seed, 900, "I attack the wolves.")
from engine import battlefield_builder
ground = battlefield_builder.for_scene(ws, duel=False, big=battlefield_builder.big_kind(foes, [], ""))
with ws.operation("test:begin", "I attack the wolves."):
    fight, _ = svc.begin(FightSpec(creature=creature, enemies=foes, battlefield=ground, place=ws.place.name,
                                   conditions=sorted(ws.conditions()), initiated=True))
p = fight.player
p.hp = p.max_hp = 5000                                       # the player outlives the tries
check("(the player shoots: a ranged physical weapon)", p.reach == "ranged" and p.damage_type == "physical", (p.reach, p.damage_type))
step = 901
for _ in range(8):                                           # the wolves come on
    if "e1" in p.engaged_with:
        break
    streams.begin(store.meta.seed, step, "I hold.")
    step += 1
    with ws.operation("test:round", "I hold."):
        svc.round(fight, RoundIntent(kind="defend", words="I hold."))
check("(the first wolf is engaged with the player before the taming)", "e1" in p.engaged_with, p.engaged_with)
e1, e2 = fight.get("e1"), fight.get("e2")
problems_after_tame = None
tries = 0
while not fight.tamed and tries < 60 and not fight.over:
    e1.hp = min(e1.hp, e1.max_hp * 0.2)                      # worn down, as the tame rule asks
    streams.begin(store.meta.seed, step, "I tame the wolf.")
    step += 1
    with ws.operation("test:round", "I tame the wolf."):
        svc.round(fight, RoundIntent(kind="tame", target="e1", words="I tame the wolf."))
        if fight.tamed:
            problems_after_tame = bf.validate(fight)           # the fight in hand, before its row is written
    tries += 1
check("(the wolf is tamed through the service's round)", bool(fight.tamed), (tries, fight.over))
check("a tamed wolf leaves the fight: off the field, and nobody keeps a tie to it",
      fight.get("e1") is None and not any("e1" in o.engaged_with for o in fight.fighters), [(o.id, o.engaged_with) for o in fight.fighters])
check("...and the battlefield holds together before the fight is saved", problems_after_tame == [], problems_after_tame)
check("(the other wolf still stands for the shot)", e2.alive and not e2.fled, (e2.alive, e2.fled))
if e2.alive and not e2.fled:
    bf.disengage(fight, p, e2)                               # wolf 2 off the player: nobody standing is on them
    check("a shot at the other wolf carries no point-blank step for the tamed one", point_blank(p, e2, fight) == [], point_blank(p, e2, fight))
    scene = cs.CombatScene(ws, fight, "wolf")
    check("the pane does not put the player in the melee with nobody standing on them", scene.spot(p) not in ("in the melee",)
          and not scene.spot(p).startswith("tied up"), scene.spot(p))
    # the readers themselves count only someone standing: a tie to the fallen, staged by hand
    dead = man(7, hp=0, max_hp=10)
    fight.fighters.append(dead)
    p.engaged_with = ["e7"]
    check("the point-blank step counts only a foe standing on the shooter, never a stale tie", point_blank(p, e2, fight) == [],
          point_blank(p, e2, fight))
    check("...and so does the pane's where", not scene.spot(p).startswith("tied up") and scene.spot(p) != "in the melee", scene.spot(p))
    p.engaged_with = []
    fight.fighters.remove(dead)

# ---- 2. the seal frees the Bound Executioner: the same stale tie, a second way of leaving
me = man(0, side="player", reach="ranged", damage_type="physical")
keeper = man(1, hp=10 ** 5, lvl=52)
keeper.boss = {"evidence": 10.0, "seal": True}
ex = man(2, hp=10 ** 5, lvl=52, bound=True)
f = field(me, keeper, ex)
bf.engage(f, me, ex)
freed = False
for rnd in range(1, 40):
    f.round = rnd
    if random.Random(f"{rnd}:{keeper.id}:seal").random() < orenna.seal_chance(10.0):
        freed = orenna.seal_attempt(f, keeper)
        break
check("(the seal frees the Executioner)", freed and f.get("e2") is None, [x.id for x in f.fighters])
check("the seal: the freed Executioner leaves no tie on the player", me.engaged_with == [] and bf.validate(f) == [], (me.engaged_with, bf.validate(f)))
check("...and the next shot at the High Keeper carries no point-blank step", point_blank(me, keeper, f) == [], point_blank(me, keeper, f))

# ---- 3. a foe persuaded to stand down
stood = None
for seed in range(60):
    me = combat.fighter_from_character(c)
    b = combat.fighter_from_creature(ws.world.bestiary["bandit"], 1, "normal", "e1", "bandit 1")
    b.hp = b.max_hp * 0.2                                    # badly hurt: easier to move
    f = field(me, b)
    bf.engage(f, me, b)
    parley.attempt(f, b, "persuade", c, random.Random(seed))
    if b.fled:
        stood = f
        break
check("(a foe is persuaded to stand down)", stood is not None)
if stood is not None:
    check("a foe that stands down leaves no tie behind", stood.player.engaged_with == [] and bf.validate(stood) == [],
          (stood.player.engaged_with, bf.validate(stood)))

# ---- 4. a turned foe that flees once its old side is gone (a dominated foe still tied to the player)
me, t = man(0, side="player"), man(1)
f = field(me, t)
bf.engage(f, me, t)
t.counters["turned"] = 1
combat_perks.turned_turn(f, t, random.Random(1))
check("(a turned foe with nobody left of its side flees)", t.fled)
check("a turned foe that flees leaves no tie on the player", me.engaged_with == [] and bf.validate(f) == [], (me.engaged_with, bf.validate(f)))

# ---- 5. a foe that turns its coat when it would have broken (Dread Regent): no break, no follow-on morale
CALLS = []
_morale = behaviors.morale


def counted(combat_, source, rng):
    CALLS.append(source.id)
    return _morale(combat_, source, rng)


behaviors.morale = counted
me = man(0, side="player", legendary={"dread_regent": 1})
a, b = man(1, family="pack_hunter", behaviors={"flee_low": 0.5}), man(2, lvl=4)
a.hp = 10
f = field(me, a, b)
behaviors.pre_turn(f, a, me, Zero())
check("(the runner turns its coat instead)", bool(a.counters.get("turned")) and not a.fled, (a.counters, a.fled))
check("a foe that turned its coat is not told as breaking and running",
      not any("breaks and runs" in s and combat.who(a) in s.lower() for s in f.story), f.story)
check("...and sets off no follow-on morale: the others do not lose heart at a break that did not happen",
      CALLS == [] and not b.fled and not any("loses heart" in s for s in f.story), (CALLS, b.fled, f.story))
me = man(0, side="player", legendary={"dread_regent": 1})
lead, a, b = man(3, lvl=9, hp=0, max_hp=50, rank="elite"), man(1), man(2)
f = field(me, lead, a, b)
behaviors.morale_on_death(f, lead, Zero())
check("(a leader's death routs the rest, and the first to break turns its coat)", bool(a.counters.get("turned")) and b.fled, (a.counters, b.fled))
check("a rout: the one who turned its coat is not told as breaking at the death; the one who ran is",
      not any(s.lower().startswith(combat.who(a) + " breaks, seeing") for s in f.story)
      and any(s.lower().startswith(combat.who(b) + " breaks, seeing") for s in f.story), f.story)
behaviors.morale = _morale

# ---- 6. No One Escapes: the parting strike that kills the runner, beside two that leave it alive and fled
kills = 0
for s in range(12):
    me, w = man(0, side="player", legendary={"no_one_escapes": 1}), man(1, hp=3, max_hp=400)
    f = field(me, w)
    bf.engage(f, w, me)
    f.round = s + 1
    broke = behaviors._break(f, w, False)
    if w.alive:
        continue
    kills += 1
    if kills > 1:
        continue
    falls = [x for x in f.story if "does not rise" in x]
    check("a runner cut down by the parting strike is dead, never fled", not w.alive and not w.fled and not w.surrendered, (w.alive, w.fled))
    check("...told falling once and never as running", len(falls) == 1 and not any("breaks and runs" in x for x in f.story), f.story)
    check("...the player is not told it fled", not any("flee" in str(t).lower() or "runs" in str(t).lower() for t in f.told), f.told)
    check("...the break did not happen: _break says so", broke is False, broke)
    check("...and its body lies on the field to be counted", w in movement._corpses(f), [x.id for x in movement._corpses(f)])
    check("...and the battlefield holds together", bf.validate(f) == [], bf.validate(f))
check("(the parting strike kills a runner at 3 health in some rounds)", kills >= 3, kills)
# through pre_turn: a kill by the parting strike sets off no follow-on morale (the death's own morale is the blow's)
CALLS.clear()
behaviors.morale = counted
fired = 0
for s in range(12):
    me = man(0, side="player", legendary={"no_one_escapes": 1})
    w = man(1, hp=3, max_hp=400, family="pack_hunter", behaviors={"flee_low": 0.5})
    other = man(2, behaviors={"fearless": 1})
    f = field(me, w, other)
    bf.engage(f, w, me)
    f.round = s + 1
    CALLS.clear()
    behaviors.pre_turn(f, w, me, Zero())
    if not w.alive:
        fired += 1
        check(f"pre_turn, round {s + 1}: a runner cut down rolls no follow-on morale and no one loses heart at it",
              CALLS == [] and not any("loses heart" in x for x in f.story), (CALLS, f.story))
        break
behaviors.morale = _morale
check("(pre_turn reached a runner cut down by the parting strike)", fired == 1)
struck = 0
for hp, rnd in ((10 ** 6, 1), (40, 2)):
    me, w = man(0, side="player", legendary={"no_one_escapes": 1}), man(1, hp=hp, max_hp=10 ** 6 if hp > 400 else 400)
    f = field(me, w)
    bf.engage(f, w, me)
    f.round = rnd
    broke = behaviors._break(f, w, False)
    if not w.alive:
        continue
    struck += 1
    check(f"a parting strike that leaves the runner standing ({hp} health): it is struck, then runs: fled, told running, released",
          broke is True and w.fled and any(h["dfn"] == w.name for h in f.hits) and any("breaks and runs" in x for x in f.story)
          and bool(f.told) and me.engaged_with == [] and bf.validate(f) == [],
          (broke, w.fled, f.story, f.told, me.engaged_with, bf.validate(f)))
check("(both parting strikes left the runner standing)", struck == 2, struck)

# ---- 7. the one way out: down is no way out, and it says so
if leave is not None:
    me, d = man(0, side="player"), man(1, hp=0, max_hp=10)
    f = field(me, d)
    check("leave refuses a fighter who is down, and the fight's log says so", leave(f, d, "fled") is False and not d.fled
          and any("foe 1" in x for x in f.log), (d.fled, f.log))
    me, r = man(0, side="player"), man(1)
    f = field(me, r)
    bf.engage(f, me, r)
    check("leave: a fighter who flees is released first, then fled", leave(f, r, "fled") is True and r.fled and not r.surrendered
          and me.engaged_with == [] and bf.validate(f) == [], (r.fled, me.engaged_with))
    me, r = man(0, side="player"), man(1)
    f = field(me, r)
    bf.engage(f, me, r)
    check("leave: one who yields is released and yielded", leave(f, r, "yielded") is True and r.fled and r.surrendered and me.engaged_with == [])
    check("leave: one already out does not leave again, and the log says so", leave(f, r, "fled") is False and r.surrendered
          and any("already left" in x for x in f.log), f.log)
    me, r = man(0, side="player"), man(1)
    f = field(me, r)
    bf.engage(f, me, r)
    check("leave: one taken off the field is released and gone from the list", leave(f, r, "gone") is True and f.get("e1") is None
          and me.engaged_with == [] and bf.validate(f) == [], ([x.id for x in f.fighters], me.engaged_with))
else:
    check("there is one engine function a fighter leaves the fight by (combat.leave)", False)

# ---- 8. a row saved with a stale tie mends itself when it is read, and says so
me, foe2, foe3 = man(0, side="player"), man(2), man(3)
f = field(me, foe2, foe3)
bf.engage(f, me, foe3)
me.engaged_with = me.engaged_with + ["e9"]                 # a tie to someone no longer on the field (an old writer's leftover)
foe2.hp = 0
me.engaged_with = me.engaged_with + ["e2"]                 # and one to the fallen
raw = FightService.row(f, "bandit")
back, _, why = FightService.resume(raw)
check("(the row reads back)", back is not None, why)
if back is not None:
    mine = back.get("player")
    check("a row saved with a stale tie lets it go when read: only the foe standing is still tied", mine.engaged_with == ["e3"]
          and bf.validate(back) == [], (mine.engaged_with, bf.validate(back)))
    check("...and the fight's log says what was let go, by name where the fighter is known", any("e9" in x for x in back.log)
          and any("foe 2" in x for x in back.log) and len(back.log) == 2, back.log)
clean = field(man(0, side="player"), man(1))
bf.engage(clean, clean.player, clean.get("e1"))
raw = FightService.row(clean, "bandit")
check("a row with no stale tie reads back exactly as it was written", FightService.row(FightService.resume(raw)[0], "bandit") == raw)

# ---- 9. the fence: nothing writes .fled or takes a fighter off the list except combat.leave
writes = getattr(purity, "leave_writes", None)
if writes is not None:
    check("no writer of .fled or remover from the fighter list outside combat.leave", writes() == [], writes())
    planted = ("def go(combat, f, g):\n    f.fled = True\n    combat.fighters.remove(g)\n    combat.fighters = [x for x in combat.fighters if x is not g]\n"
               "    g.hp, g.fled = 0, False\n    combat.fighters.append(g)\n")
    found = purity.leave_writes_in(planted, "engine/somewhere.py")
    check("the fence finds a planted .fled write, a removal and a reassigned list, in a second module; an arrival is no leaving",
          len(found) == 4 and all("engine/somewhere.py" in x for x in found), found)
    check("every exempt site still stands (the list may only shrink)", purity.leave_exempt_missing() == [], purity.leave_exempt_missing())
else:
    check("tools/purity.py fences writes of .fled and the fighter list (leave_writes)", False)

game.close()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
