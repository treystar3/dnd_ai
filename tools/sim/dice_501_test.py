"""(f501) The dice outside the streams onto keyed and fixed dice; the DICE fence. Nothing in play is seeded by what was logged (decision
5): the retreat die, the morale die and the parting strike of No One Escapes draw their own keyed dice (streams.keyed by the fighter, the
fight's serial and the round), so the same fight run twice, one with an extra line in its log before the roll, gives the same retreat
story, the same morale outcome and the same parting blow; a hall's roster for one week is the same list across two inputs and is
today's (streams.fixed builds today's seed string exactly), as is a companion's pronoun; the DICE fence (tools/purity.py check_dice)
finds nothing in the fight modules, catches a die seeded by the log or a bare random roll, and lets the streams and the two named
constants through. Nothing stays in the process."""
import copy
import random
import shutil
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import purity
from engine import behaviors, combat, combat_perks, party, streams

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "dice_501"
game = simlib.campaign(NAME, cls="warrior", seed=7, location="south_fields")
ws = game.scene
bestiary = ws.world.bestiary


def bare_fight() -> combat.Combat:
    """A pack fight built bare: the player and three bandits, on plain ground, with a serial as a scene's fight has."""
    p = combat.fighter_from_character(ws.player.character)
    foes = [combat.fighter_from_creature(bestiary["bandit"], 1, "normal", f"e{i}", f"bandit {i}") for i in (1, 2, 3)]
    c = combat.Combat(fighters=[p] + foes, record=False, serial="ab12")
    combat.ensure_field(c)
    for e in foes:
        e.zone_id = p.zone_id
    return c


def twice(run):
    """The same fight twice, the second with an extra line in its log before the roll: what each run shows."""
    out = []
    for extra in (False, True):
        streams.begin(7, 3, "I fight on")
        c = bare_fight()
        if extra:
            c.log.append("an extra line, logged before the roll")
        out.append(run(c))
    return out


# ---- morale: a death that may rout the rest draws its own die
def morale(c):
    fallen = c.get("e1")
    fallen.hp = 0
    combat_perks.on_dot_death(c, fallen)
    return [(e.id, e.fled, e.surrendered, round(e.hp, 2)) for e in c.fighters if e.side == "enemy"]


a, b = twice(morale)
check("the morale outcome after a death is the same whatever was logged before the roll (its own keyed die)", a == b, (a, b))

# ---- the retreat: the parting blows of a foe backing away draw their own die
def retreat(c):
    p, e = c.player, c.get("e2")
    e.engaged_with, p.engaged_with = [p.id], [e.id]
    combat.act_move(c, e, "back", None)
    return (round(e.hp, 2), round(p.hp, 2), c.story[-1] if c.story else "", c.log[-1] if c.log else "")


a, b = twice(retreat)
check("a foe backing away: the same parting blows and the same story whatever was logged before the roll", a == b, (a, b))

# ---- No One Escapes: the parting strike owed a fleeing foe draws its own die
def escape(c):
    p, e = c.player, c.get("e3")
    p.legendary["no_one_escapes"] = 1
    p.mech_names.setdefault("no_one_escapes", "No One Escapes")
    e.engaged_with, p.engaged_with = [p.id], [e.id]
    behaviors._break(c, e, False)
    return (round(e.hp, 2), e.fled, [l for l in c.log if "fleeing" in l or "flees" in l or "runs" in l][-1:] )


a, b = twice(escape)
check("the parting strike on a fleeing foe (No One Escapes) is the same whatever was logged before the roll", a == b and a[1] is True, (a, b))

# ---- the DICE fence
check("the DICE fence finds no die outside the streams in the fight modules", purity.check_dice() == [], purity.check_dice())
planted = '''
import random
from engine import streams
def act(combat, f):
    story = retreat(combat, f, random.Random(combat.round * 7919 + len(combat.log)))
    if random.random() < 0.5:
        pass
    ok = streams.keyed("retreat", f.id, combat.serial, combat.round)
    ok2 = streams.fixed(1, "party", "hall", 2)
    ok3 = streams.get("combat")
    ok4 = streams.new_id(4)
'''
found = purity.dice_problems_in(planted, "engine/planted.py")
check("...it catches a die seeded by the log and a bare random roll", len(found) == 2 and any("makes its own Random" in f for f in found)
      and any("rolls random.random" in f for f in found), found)
constants = "def danger(seed):\n    rng = random.Random(seed)\n    probe = f(random.Random(0))\n"
check("...and lets the streams and the two named constants through", purity.dice_problems_in(constants, "engine/combat.py") == []
      and len(purity.dice_problems_in(constants, "engine/other.py")) == 2, purity.dice_problems_in(constants, "engine/combat.py"))
check("every fight module the fence names exists, or is the one f503 will write", all((purity.ROOT / m).exists() or m == "services/fight.py" for m in purity.DICE), purity.DICE)

# ---- a hall's roster for the week is the same list across two inputs, and today's
streams.begin(7, 1, "I look at the roster")
r1 = party.roster(7, "guild_house", 10, 1, 0, [])
streams.begin(7, 2, "I look again")
r2 = party.roster(7, "guild_house", 10, 1, 0, [])
week = 10 // party.P["roster_days"]
check("a hall's roster for one week is the same list across two inputs", r1 == r2 and len(r1) == party.P["roster_size"], (len(r1), len(r2)))
check("...and today's: the fixed die is seeded by today's string exactly", streams.fixed(7, "party", "guild_house", week).random() == random.Random(f"7:party:guild_house:{week}").random())
check("a companion's pronoun fallback is today's too", streams.fixed("h1", "Dade Bromwood").choice(["she", "he"]) == random.Random("h1:Dade Bromwood").choice(["she", "he"])
      and streams.fixed("h1", "Dade Bromwood").random() == streams.fixed("h1", "Dade Bromwood").random())

game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
