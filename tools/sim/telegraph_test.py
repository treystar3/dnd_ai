"""Telegraphs, openings, stances, interpose and graded control (B4): a heavy hitter winds up a named blow a round early, and every
defensive tool is an answer - stance through it, interpose for the target, stun the brute (interrupt), or step out and strike the
opening; heavy armor cannot dance. Defense abilities are stances that persist with upkeep; control is graded with diminishing returns
and bosses are controllable but worn down fast."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import battlefield as bf, battlefield_builder as bb, combat
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def man(i, side="enemy", reach="melee", hold=1, pace="normal", hp=400, rank="normal", size="Medium", stam=100):
    return combat.Fighter(id=f"m{i}", name=f"m{i}", side=side, level=5, attrs={a: 10 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, stamina=stam, max_stamina=stam, reach=reach, hold=hold, pace=pace,
                          rank=rank, size=size, weapon_damage=8)

def fight(*fighters):
    f = combat.Combat(fighters=list(fighters))
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    return f

rng = random.Random(3)

# ---- who telegraphs
check("elites and the Huge wind up; trash and set-piece bosses do not",
      combat.telegraphs(man(1, rank="elite")) and combat.telegraphs(man(1, size="Huge"))
      and not combat.telegraphs(man(1)) and not (lambda b: (setattr(b, "boss", {"x": 1}) or combat.telegraphs(b)))(man(1, rank="boss")))

# ---- the wind-up lands with weight when unanswered
p = man(0, side="player", hp=4000); troll = man(1, rank="elite", pace="slow", hp=4000)
f = fight(p, troll)
troll.winding = {"target": p.id, "round": 1}
before = p.hp
combat.resolve_telegraph(f, troll, random.Random(0))
check("unanswered, the great blow lands", p.hp < before, (before, p.hp))

# ---- stepping out makes it whiff and leaves the brute open; plate cannot
p = man(0, side="player", hp=4000); troll = man(1, rank="elite", pace="slow", hp=4000)
f = fight(p, troll)
troll.winding = {"target": p.id, "round": 1}
f.round = 2
p.move_round = 1
bf.disengage(f, troll, p)
combat.resolve_telegraph(f, troll, random.Random(0))
check("step out on the wind-up and the blow finds air", p.hp == 4000)
check("...and the brute is open: easier to hit and to crit", combat.is_open(troll, f.round))
tr = {}
combat.roll_attack(p, troll, f, random.Random(1), tr)
check("...the opening shows in the roll", any("open" in s[0] for s in tr.get("hit_steps", [])), tr.get("hit_steps"))
p2 = man(2, side="player", pace="slow", hp=4000)
f2 = fight(p2, man(3, rank="elite", hp=4000))
e2 = f2.get("m3"); e2.winding = {"target": p2.id, "round": 1}
f2.round = 2
p2.move_round = 1
before = p2.hp
combat.resolve_telegraph(f2, e2, random.Random(0))
check("in heavy armor there is no dancing: the blow still lands", p2.hp < before)

# ---- a stun interrupts the wind-up
troll = man(1, rank="elite", hp=4000); p = man(0, side="player", hp=4000)
f = fight(p, troll)
troll.winding = {"target": p.id, "round": 1}
combat.add_status(f, troll, "stunned", 1)
check("a stun interrupts the wound-up blow and leaves them open", not troll.winding and combat.is_open(troll, f.round + 1))

# ---- interpose: the blow meant for the healer lands on you, through your stance
p = man(0, side="player", hp=4000); heal = man(2, side="ally", reach="ranged", hold=0, hp=400); troll = man(1, rank="elite", hp=4000)
f = fight(p, heal, troll)
stance = Move(id="wall", name="Shield Wall", effect="defense", tier="heavy", reach="self", resource="stamina")
combat.act_ability(f, p, stance, None, rng)
check("a defense ability is a stance: it persists and you keep acting",
      any(b.get("kind") == "stance" for b in p.buffs.values()) and p.buffs["wall"]["rounds"] == 4, p.buffs)
combat.act_interpose(f, p, heal)
troll.winding = {"target": heal.id, "round": 1}
before_p, before_h = p.hp, heal.hp
combat.resolve_telegraph(f, troll, random.Random(0))
check("the interposer takes the blow meant for the healer", heal.hp == before_h and p.hp < before_p, (p.hp, heal.hp))
taken = before_p - p.hp
p3 = man(9, side="player", hp=4000)
f3 = fight(p3, man(8, rank="elite", hp=4000))
e3 = f3.get("m8"); e3.winding = {"target": p3.id, "round": 1}
combat.resolve_telegraph(f3, e3, random.Random(0))
check("...and the stance blunts it against a bare target's wound", taken < (4000 - p3.hp), (taken, 4000 - p3.hp))

# ---- stance upkeep: no stamina, no stance
p = man(0, side="player", stam=100)
f = fight(p, man(1))
combat.act_ability(f, p, stance, None, rng)
p.stamina = 0
f.round = 2
combat.start_turn(p, f)
check("a stance falters when there is nothing left to hold it with", not any(b.get("kind") == "stance" for b in p.buffs.values()))

# ---- graded control with diminishing returns; bosses controllable but worn
grades = [combat.contest(man(0, side="player"), man(1), ["strength"], random.Random(s)) for s in range(60)]
check("the contest grades: full, partial and none all occur", {"full", "partial", "none"} <= set(grades), set(grades))
t = man(1)
t.counters["controlled"] = 2
check("twice-controlled, a full result is worn to nothing", combat.contest(man(0, side="player"), t, ["strength"], random.Random(1)) == "none")
b = man(1, rank="boss"); b.boss = {"legendary": 0}
got = {combat.contest(man(0, side="player"), b, ["strength"], random.Random(s)) for s in range(60)}
check("a boss can be controlled, but never fully", "partial" in got and "full" not in got, got)

# ---- a stunned holder's line breaks (control releases the hold, derived)
tank = man(2, side="ally", hold=2); back = man(3, side="ally", reach="ranged", hold=0)
w = man(1)
f = fight(tank, back, man(0, side="player"), w)
back.row = "back"
check("the healer is protected while the tank stands", bf.protected(f, back))
combat.add_status(f, tank, "stunned", 1)
check("...stun the tank and the protection is gone with his holds", not bf.protected(f, back) or bf.can_hold(f.player))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
