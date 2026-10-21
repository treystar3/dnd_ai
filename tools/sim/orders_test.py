"""Orders to allies in a fight: one free order a turn (focus, guard, hold, heal); an order is a plain pattern, never a question; a guarding
ally takes blows meant for the player; a held ally does nothing; only healers can heal; the mentor will not stand back."""
import sys, random
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import ui.console as uc
NOTES, NARR = [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.narrate = lambda t: NARR.append(t)
uc.say = lambda t, s="": None
from engine import combat, party
from world.loader import load_world
from scenes.combat_scene import CombatScene
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
ch, _ = simlib.make_character("warrior", random.Random(2))

def fight(roles=("fighter", "priest")):
    me = combat.fighter_from_character(ch)
    allies = [party.fighter({"id": f"t{i}", "name": ("Ayla" if r == "fighter" else "Bram") + " Voss", "role": r, "level": 3}) for i, r in enumerate(roles)]
    wolves = [combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", f"wolf{i}", f"Wolf {i}", "engaged") for i in range(2)]
    f = combat.Combat(fighters=[me] + allies + wolves, place="x", conditions=[])
    f.round = 1
    return f, allies, wolves

f, (fighter, priest), (w0, w1) = fight()
check("a focus order sets the ally's target", combat.give_order(f, fighter, "focus", w1.id) == "" and fighter.order == "focus" and fighter.order_target == w1.id)
check("only one order a turn", "already given" in combat.give_order(f, priest, "guard"))
f.round = 2
check("...and a new turn allows another", combat.give_order(f, priest, "guard") == "")
f.round = 3
check("a non-healer cannot be told to heal", "no healing" in combat.give_order(f, fighter, "heal"))
f.round = 4
check("a priest can be told to heal", combat.give_order(f, priest, "heal") == "")
f.player.hp = 5
rng = random.Random(1)
combat.ally_turn(f, priest, rng)
check("a healing order tends the player", f.player.hp > 5, f.player.hp)
f.round = 5
fighter.order = "focus"; fighter.order_target = w1.id
hp0, hp1 = w0.hp, w1.hp
for _ in range(6):
    combat.ally_turn(f, fighter, random.Random(_))
check("a focused ally goes for the named enemy", w1.hp < hp1 and w0.hp == hp0, (w0.hp, w1.hp))
f.round = 6
check("a hold order is accepted", combat.give_order(f, fighter, "hold") == "")
hp1 = w1.hp
combat.ally_turn(f, fighter, random.Random(3))
check("a held ally does nothing", w1.hp == hp1 and w0.hp == hp0)
f2, (g, p2), (a0, a1) = fight()
g.order = "guard"
hits = {"player": 0, "guard": 0}
for i in range(80):
    f2.player.hp = f2.player.max_hp; g.hp = g.max_hp; p2.hp = p2.max_hp
    f2.log = []
    combat.enemy_turn(f2, a0, random.Random(i))
    hits["guard"] += any(g.name in l and "steps in front" in l for l in f2.log)
    hits["player"] += f2.player.hp < f2.player.max_hp
check("a guard takes some of the blows meant for the player", hits["guard"] >= 8, hits)
mentor = party.fighter({"id": "m", "name": "Maren Holt", "role": "fighter", "level": 5}); mentor.ally_role = "mentor"
f3 = combat.Combat(fighters=[f2.player, mentor, a0], place="x", conditions=[]); f3.round = 2
check("the mentor will not stand back", "not about to stand back" in combat.give_order(f3, mentor, "hold"))

# the scene's reading of the line
class W: pass
sc = CombatScene.__new__(CombatScene)
f4, (fa, pa), (b0, b1) = fight()
sc.fight = f4
r = sc.order_of("Ayla, take Wolf 1")
check("'<name>, take <enemy>' is a focus order on that enemy", r and r[1] == "focus" and r[2] == b1.id, r)
r = sc.order_of("everyone hold back")
check("'everyone hold back' is a hold order for all", r and r[1] == "hold" and len(r[0]) == 2, r)
r = sc.order_of("Bram, tend my wounds")
check("tending is a heal order", r and r[1] == "heal", r)
r = sc.order_of("Ayla guard me")
check("guard me is a guard order", r and r[1] == "guard", r)
check("a question is not an order", sc.order_of("Ayla, how do I get my hit chance up?") is None)
check("an order to nobody is not an order", sc.order_of("I attack the wolf") is None)

# the damage breakdown names the passive that reduced a hit
f5, (fa5, pa5), (c0, c1) = fight()
f5.record = True
f5.player.legendary["aegis"] = 20
f5.player.mech_names = {"aegis": "Bulwark Reflexes"}
hits = []
for i in range(40):
    f5.hits = []; f5.player.aegis_round = -1; f5.player.hp = f5.player.max_hp
    combat.apply_damage(f5, c0, f5.player, 1.0, "bites", random.Random(i))
    hits += [h for h in f5.hits[:1] if h.get("outcome") == "hit" and h.get("final", 0) >= 5]       # the first blow of the round: Aegis only turns the first
named = [h for h in hits if any(e[0] == "Bulwark Reflexes" for e in h["extras"])]
check("a hit reduced by a passive names it in the breakdown", hits and len(named) == len(hits), (len(named), len(hits)))
check("...with the amount taken off", all(e[1].startswith("-") for h in named for e in h["extras"] if e[0] == "Bulwark Reflexes"))
check("...and no unexplained 'last-moment' line when the name covers it", not any(e[0].startswith("Other") for h in hits for e in h["extras"]), [h["extras"] for h in hits][:2])

# the defence line explains where the percentage comes from
f6, (fa6, pa6), (d0, d1) = fight()
taken, soaked = combat.mitigate(d0, 40.0, "physical", 3, f6, f6.player, trace=(tr := {}))
check("the defence trace names whose armour, its value, and the working", tr["who"] == d0.name and tr["base_protection"] == round(d0.armor, 1) and tr["k"] > 0
      and abs(tr["raw_reduction"] - 100 * tr["protection"] / (tr["protection"] + tr["k"])) < 0.6 and tr["reduction"] <= tr["raw_reduction"], tr)
f6.player.armor_pierce = 55
taken2, _ = combat.mitigate(d0, 40.0, "physical", 3, f6, f6.player, trace=(tr2 := {}))
check("a sundering strike shows the cut to the armour", any(n.startswith("Piercing") and v == "-55%" for n, v in tr2["prot_steps"]) and tr2["protection"] < tr2["base_protection"], tr2)

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
