"""(f643) A fight rebuilt from its saved row has one fighter for each person (docs/design/21_play_faults_plan.md, A1; found in play:
docs/play/2026-11-15_play_findings.md 1.7). A field of the fight that holds someone who is also in the fight came back from the row
as a second, separate fighter, so an order given to the mentor in the fight never reached the mentor the script read: she stood
"waiting on you", the troll's blow left her bar full, and a draught healed nobody. Held here:
- every field of a fight that holds a fighter is declared: the fight's own list, one of the fight's, or not yet in it; a new one
  fails until it is declared;
- one of the fight's is, after the row, the very fighter in the list (the mentor, and a second such field made for the test), and
  keeps its own when that person is not in the fight; a row saved with the two apart comes back as the one in the list;
- those not yet in it leave their list as they enter (a wave of foes, a party that held back), so nobody is in both, before the
  row and after;
- the troll's script played with the fight rebuilt from its row after every round: its blow shows on her, health given back to
  her in the fight is on the mentor the script reads, and she strikes on the order;
- in the scene, with each line of the tutorial's fight standing down and running again (the fight resumed from its row, as in
  play): its blow shows on her bar, the draught the player gives her heals her, the order reaches her, and she ends it on the
  player's next line.
Run: python tools/sim/fight_one_fighter_643_test.py"""
import random
import sys
import typing
from typing import ClassVar
sys.path.insert(0, ".")
sys.path.insert(0, "tools/sim")
import simlib
from types import SimpleNamespace as NS
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import battlefield as bf
from engine import combat, mentor
from engine.combat import Combat, Fighter
from llm import gateway
from pydantic import BaseModel
from llm.contracts import DialogueFrame
from services.fight import FightService

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


def rebuilt(fight, cls=None):
    """The fight as play gets it back when an operation does not stand: written to its row and read again."""
    raw = FightService.row(fight, "troll")
    if cls is None:
        got, _, why = FightService.resume(raw)
        assert got is not None, why
        return got
    import json
    return cls(**json.loads(raw)["fight"])


def inside(fight, who):
    return next((f for f in fight.fighters if f.id == who.id), None)


# ---- the fence: every field that holds a fighter says which kind it is
def models_under(cls, found):
    """Every model a fight is made of, the fight's own class first."""
    if cls in found:
        return found
    found.append(cls)
    for f in cls.model_fields.values():
        stack = [f.annotation]
        while stack:
            t = stack.pop()
            stack += list(typing.get_args(t))
            if isinstance(t, type) and issubclass(t, BaseModel):
                models_under(t, found)
    return found


parts = models_under(Combat, [])
check("a fighter is held by the fight alone: no part of a fight (the ground, a fighter, an effect) holds one",
      len(parts) > 10 and not [(m.__name__, n) for m in parts[1:] for n, f in m.model_fields.items() if "Fighter" in str(f.annotation)],
      [(m.__name__, n) for m in parts[1:] for n, f in m.model_fields.items() if "Fighter" in str(f.annotation)])
holds = {name for name, f in Combat.model_fields.items() if "Fighter" in str(f.annotation)}
one_of = set(getattr(Combat, "ONE_OF_THE_FIGHT", ()))
not_yet = set(getattr(Combat, "NOT_YET_IN_IT", ()))
check("every field of a fight that holds a fighter is the fight's list, one of the fight's, or not yet in it",
      holds == {"fighters"} | one_of | not_yet and not one_of & not_yet and "mentor_ally" in one_of and {"reserves", "ally_reserves"} <= not_yet,
      (sorted(holds), sorted(one_of), sorted(not_yet)))

# ---- one of the fight's is the fighter in the list, after the row
c, _ = simlib.make_character("warrior", random.Random(2))


def troll_fight():
    pl = combat.fighter_from_character(c)
    pl.side = "player"
    fg = Combat(fighters=[pl, mentor.troll_fighter("engaged")], record=True)
    m = mentor.maren_fighter()
    fg.mentor_ally = m
    combat.enters(fg, m)
    fg.mentor_in = fg.mentor_troll = fg.mentor = True
    bf.engage(fg, m, fg.enemies()[0])
    fg.enemies()[0].always_miss = True
    return fg


fg = troll_fight()
check("as made, the mentor the script reads is the mentor in the fight", fg.mentor_ally is inside(fg, fg.mentor_ally))
back = rebuilt(fg)
check("after the row she is still that one fighter, not a second", back.mentor_ally is not None and back.mentor_ally is inside(back, back.mentor_ally),
      (id(back.mentor_ally), id(inside(back, back.mentor_ally))))
check("...and the row read twice over holds the same fight", FightService.row(rebuilt(back), "troll") == FightService.row(back, "troll"))

import json
old = json.loads(FightService.row(troll_fight(), "troll"))
old["fight"]["mentor_ally"]["resources"]["hp"] = 700.0
mid = next(f for f in old["fight"]["fighters"] if f["identity"]["id"] == old["fight"]["mentor_ally"]["identity"]["id"])
mid["resources"]["hp"] = 1200.0
back, _, why = FightService.resume(json.dumps(old))
check("a row saved with the two apart (a fight under way in an older save) comes back as the one in the fight, the one the bars showed",
      back is not None and back.mentor_ally is inside(back, back.mentor_ally) and back.mentor_ally.hp == 1200.0, (why, back and back.mentor_ally.hp))

apart = troll_fight()
apart.fighters = [f for f in apart.fighters if f.id != apart.mentor_ally.id]
back = rebuilt(apart)
check("a mentor who is not in the fight keeps her own record", back.mentor_ally is not None and inside(back, back.mentor_ally) is None
      and back.mentor_ally.name == mentor.NAME)


class Two(Combat):
    """A fight with a second field that holds one of its fighters, made for the test: the rule is the class's, not the mentor's."""
    champion: Fighter | None = None
    ONE_OF_THE_FIGHT: ClassVar[tuple] = tuple(getattr(Combat, "ONE_OF_THE_FIGHT", ())) + ("champion",)


two = Two(**troll_fight().model_dump(mode="json"))
two.champion = two.enemies()[0]
back = rebuilt(two, Two)
check("a second such field is held the same way: it and the mentor are each the one in the list",
      back.champion is inside(back, back.champion) and back.mentor_ally is inside(back, back.mentor_ally) and back.champion is not back.mentor_ally)
back.champion.hp -= 5
check("...so a wound on one shows on the other", inside(back, back.champion).hp == back.champion.hp == back.enemies()[0].hp)

# ---- not yet in it: they leave their list as they enter
pl = combat.fighter_from_character(c)
pl.side = "player"
wolf = lambda i: combat.fighter_from_creature(mentor._world().bestiary["wolf"], 1, "normal", f"e{i}", f"wolf {i}", "near")
hire = combat.fighter_from_character(c, "a1")
held = Combat(fighters=[pl, wolf(1)], reserves=[wolf(2), wolf(3)], ally_reserves=[hire], ally_arrive=1, reinforce_from=1, reinforce_every=1, reinforce_count=2)
held = rebuilt(held)
for _ in range(3):
    combat.finish_round(held, random.Random(4))
    held = rebuilt(held)
ids = [f.id for f in held.fighters]
check("those held back are in the fight once they arrive (the party, and the wave of foes), and in no list twice, before the row and after",
      len(ids) == len(set(ids)) and {"a1", "e2", "e3"} <= set(ids) and not held.ally_reserves and not held.reserves, (ids, [f.id for f in held.reserves]))

# ---- the troll's script, the fight rebuilt from its row after every round
fg = troll_fight()
rng = random.Random(7)
fg = rebuilt(fg)
combat.finish_round(fg, rng)
fg = rebuilt(fg)
her = inside(fg, fg.mentor_ally)
check("the troll's blow shows on her in the fight: her health is down by about two fifths", 0.5 * her.max_hp < her.hp < 0.7 * her.max_hp, (her.hp, her.max_hp))
hurt = her.hp
her.hp = min(her.max_hp, her.hp + 50)
fg = rebuilt(fg)
check("health given back to her in the fight is on the mentor the script reads", fg.mentor_ally.hp == hurt + 50, (fg.mentor_ally.hp, hurt))
combat.finish_round(fg, rng)
fg = rebuilt(fg)
combat.finish_round(fg, rng)
fg = rebuilt(fg)
check("she guards, then waits for the word: not struck yet", fg.mentor_phase == 2 and not fg.mentor_struck and not fg.over, (fg.mentor_phase, fg.mentor_struck))
problem = combat.give_order(fg, inside(fg, fg.mentor_ally), "focus", fg.enemies()[0].id)
fg = rebuilt(fg)
combat.mentor_strikes(fg, rng)
check("the order given to her in the fight is the order the script reads: she strikes on it, the first round asked",
      not problem and fg.mentor_struck and fg.mentor_stalls < 3 and not fg.enemies(), (problem, fg.mentor_struck, fg.mentor_stalls))

# ---- in the scene: a line of the tutorial's fight that stands down and runs again
stub.a_Narration = lambda u, k: {"text": "The fight rages on."}
stub.a_MentorReply = lambda u, k: {"speech": "Mind your feet."}
CHOICE = [{"kind": "attack", "target": "e1"}]
stub.bot = NS(combat_choice=lambda: dict(CHOICE[0]))
stub.a_CombatIntent = lambda u, k: dict(CHOICE[0])
game = simlib.campaign("one_fighter_643", cls="warrior", seed=5, location=mentor.M["hunt"]["place"], never_mentor=False)
ws = game.scene
ws.enter(mentor.M["hunt"]["place"])
ws.asked_operation("action:other", "the troll comes", lambda op: ws.mentor_troll())
check("the troll's fight is on, the mentor in it", ws.combat is not None and ws.combat.fight.mentor_troll and inside(ws.combat.fight, ws.combat.fight.mentor_ally) is not None)
runs = []


def line(text, stand_down=True):
    """One typed line of the fight as its own operation; it stands down to ask outside (once here, and once for each thing the
    line itself asks), so the fight is resumed from its row."""
    del runs[:]

    def body(op):
        runs.append(ws.combat)
        ws.combat.turn(text)
        if stand_down and len(runs) == 1:
            gateway.generate("dialogue_frame", "You frame a line.", "The line.", DialogueFrame)
    return ws.asked_operation("action:attack", text, body)[0]


for text in ("I strike at the troll.", "I strike at the troll again.", "I hold my ground."):
    op = line(text)
    if ws.combat is None or ws.combat.fight.over:
        break
f = ws.combat.fight if ws.combat else None
check("three lines in, each stood down and stands: the fight was resumed from its row, and she waits for the word",
      f is not None and len(runs) >= 2 and runs[0] is not runs[-1] and op.state == "committed" and f.mentor_phase == 2 and not f.mentor_struck,
      (len(runs), getattr(op, "state", None), f and (f.mentor_phase, f.mentor_struck, f.over)))
check("...the mentor the script reads is the mentor in the fight", f is not None and f.mentor_ally is inside(f, f.mentor_ally))
her = inside(f, f.mentor_ally)
check("...and the troll's blow shows on her bar", her.hp < her.max_hp, (her.hp, her.max_hp))
potion = mentor.M["hunt"]["potion"]
hurt, carried = her.hp, sum(1 for i in ws.player.character.inventory if i.good == potion)
CHOICE[0] = {"kind": "item", "item": "healing draught"}
line("I give Maren a healing draught.")
CHOICE[0] = {"kind": "attack", "target": "e1"}
f = ws.combat.fight
her = inside(f, f.mentor_ally)
check("...the draught the tutorial hands the player, given to her, heals her: her health is up, on the mentor the script reads too, and the draught is spent",
      carried >= 1 and her.hp > hurt and f.mentor_ally.hp == her.hp and sum(1 for i in ws.player.character.inventory if i.good == potion) == carried - 1,
      (carried, hurt, her.hp, f.mentor_ally.hp))
stalls = f.mentor_stalls
op = line("Maren, attack the troll!")
f = ws.combat.fight if ws.combat else None
check("told to attack, the order is on the mentor the script reads (an order does not use the turn: the round is the same one)",
      f is not None and f.mentor_ally.order == "focus" and f.order_round == f.round and f.mentor_stalls == stalls and stalls < 2,
      f and (f.mentor_ally.order, f.order_round, f.round, f.mentor_stalls, stalls))
told = len(SHOWN)
line("I strike at the troll.")
f = ws.combat.fight if ws.combat else None
after = " ".join(str(s) for s in SHOWN[told:])
check("...and on the player's next line she ends it, with no waiting out three rounds",
      (ws.combat is None or f.mentor_struck or f.over == "victory") and (f is None or f.mentor_stalls <= stalls + 1) and "waiting on your word" not in after,
      (f and (f.mentor_struck, f.over, f.mentor_stalls), stalls, after[-300:]))

game.session.close()
import shutil
shutil.rmtree("saves/one_fighter_643", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
