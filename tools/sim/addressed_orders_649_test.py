"""(f649) An order in a fight is given to the one the line speaks to, and the player's own act beside it is kept
(docs/design/21_play_faults_plan.md, B1; found in play: docs/play/2026-11-15_play_findings.md 1.1 to 1.5, 1.9). An order was a
companion's first name anywhere in the line and an order word anywhere in it: "a Twin Hammer Strike ... before it turns on Kennard"
told Kennard to attack, "smash the ogre with Guard Breaker" beside Raerei's name told her to guard, "behind Kennard's shield" told him
to guard, and the player's own strike in each line was dropped; "Kennard, guard Raerei!" could only ever mean guard the player.
Held here, on the journal's lines and a twin of each the journal did not hold:
- an order is given only to one the line addresses: a name at the head of a sentence or of words said ("Kennard, ..." "Kennard
  guard me", "Kennard attacks the wolf"), a name called at its end ("Cover me, Kennard!"), one the player tells, orders or asks
  ("I tell Almund to take wolf 1"), or the whole party ("Everyone, hold back"); a companion named anywhere else is not addressed;
- the names of the player's own abilities and gear are taken out before an order word is looked for;
- a guard order says whom to guard: the companion it names, the one a "him" or "her" points back to, or the player; the order
  keeps it, the line printed says it, and a blow aimed at that one is the one the guard steps in front of;
- the player's own act in the line is kept, whoever it names; a line that is only an order acts on nothing else.
Run: python tools/sim/addressed_orders_649_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import ui.console as uc
NARR = []
uc.put("note", lambda m, *a, **k: None)
uc.put("narrate", lambda t: NARR.append(t))
from engine import addressing, combat, party
from scenes.combat_scene import CombatScene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


world = simlib.campaign("addressed_orders_649", cls="warrior", seed=3).scene.world
ch, _ = simlib.make_character("warrior", random.Random(2))


def fight():
    me = combat.fighter_from_character(ch)
    base = me.moves[0]
    me.moves = me.moves + [base.model_copy(update={"id": "twin", "name": "Twin Hammer Strike"}), base.model_copy(update={"id": "gb", "name": "Guard Breaker"})]
    allies = [party.fighter({"id": hid, "name": name, "role": role, "level": 3})
              for hid, name, role in (("k", "Kennard Holt", "fighter"), ("r", "Raerei Wynn", "priest"), ("a", "Almund Pell", "fighter"))]
    wolves = [combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", f"wolf{i}", f"Wolf {i}", "engaged") for i in range(2)]
    f = combat.Combat(fighters=[me] + allies + wolves, place="x", conditions=[])
    f.round = 1
    return f, allies, wolves


f, (kennard, raerei, almund), (w0, w1) = fight()
sc = CombatScene.__new__(CombatScene)
sc.fight = f


def order(line):
    r = sc.order_of(line)
    return None if r is None else ([a.name.split()[0] for a in r[0]], r[1], r[2])


# ---- the journal's lines
check("1.1: a strike named for its ability, beside a companion named as the one it saves, is no order",
      order("I put everything into a Twin Hammer Strike to kill the owlbear before it turns on Kennard again.") is None)
check("1.2: an ability whose name holds 'Guard', beside a companion stepped in front of, is no order",
      order("I step in front of Raerei and smash the ogre with Guard Breaker.") is None)
check("1.3: 'Kennard, guard Raerei!' tells Kennard to guard Raerei",
      order('"Kennard, guard Raerei!" Twin Hammer Strike on the giant boar.') == (["Kennard"], "guard", raerei.id),
      order('"Kennard, guard Raerei!" Twin Hammer Strike on the giant boar.'))
check("1.4: 'Kennard, cover him!' after Almund is spoken to tells Kennard to guard Almund",
      order('"Almund, get back out of its reach! Kennard, cover him!"') == (["Kennard"], "guard", almund.id), order('"Almund, get back out of its reach! Kennard, cover him!"'))
check("1.5: a companion's shield stood behind is no order",
      order("I stand my ground behind Kennard's shield and wait for the centaur to come to us.") is None)
check("1.9: an order said with a plea in it is the order, to the one it is said to",
      order('"Kennard, I\'m nearly done for, take the other one!" I use Guard Breaker on wolf 1.') == (["Kennard"], "focus", order('"Kennard, I\'m nearly done for, take the other one!" I use Guard Breaker on wolf 1.')[2])
      if order('"Kennard, I\'m nearly done for, take the other one!" I use Guard Breaker on wolf 1.') else False)

# ---- a twin of each the journal did not hold
check("another of the player's abilities with order words in its name, beside a companion named, is no order",
      order("I open with Shield Wall, then Brutal Strike on wolf 1 while Raerei watches.") is None)
check("an ability's name inside an order is not read as the order: 'follow my Guard Breaker with a strike' is an attack",
      order("Kennard, follow my Guard Breaker with a strike on wolf 1") == (["Kennard"], "focus", w1.id), order("Kennard, follow my Guard Breaker with a strike on wolf 1"))
check("a companion ducked behind is no order, though the line holds its ground",
      order("I duck behind Raerei and hold my ground.") is None)
check("a companion shoved aside is no order, though the line takes a wolf", order("I shove Almund aside and take the wolf myself.") is None)
check("an order to guard a third: Raerei told to protect Almund", order("Raerei, protect Almund!") == (["Raerei"], "guard", almund.id), order("Raerei, protect Almund!"))
check("a name called at the end is addressed, and 'me' is the player", order("Cover me, Kennard!") == (["Kennard"], "guard", ""), order("Cover me, Kennard!"))
check("one the player tells is addressed", order("I tell Almund to take wolf 1.") == (["Almund"], "focus", w1.id), order("I tell Almund to take wolf 1."))
check("the whole party is addressed", (order("Everyone, hold back!") or [None, None])[1] == "hold" and len(sc.order_of("Everyone, hold back!")[0]) == 3,
      order("Everyone, hold back!"))
check("a companion at the head of the line doing the deed is told it (f384)", order("Kennard attacks wolf 0") == (["Kennard"], "focus", w0.id), order("Kennard attacks wolf 0"))
check("a name at the head with no comma is addressed", order("Kennard guard me") == (["Kennard"], "guard", ""), order("Kennard guard me"))
check("a 'her' points back to the companion last named", order("Raerei is down. Kennard, protect her!") == (["Kennard"], "guard", raerei.id),
      order("Raerei is down. Kennard, protect her!"))
check("a companion only spoken of is not told anything", order("Raerei is hurt and Kennard is tiring.") is None)
check("...nor one spoken of at the head of the line, though the line takes a wolf", order("Raerei is down, so I take wolf 1 myself.") is None,
      order("Raerei is down, so I take wolf 1 myself."))
check("a question to a companion is no order", order("Kennard, could you take wolf 1?") is None)
check("a companion said to be doing a thing is spoken of, not told it", order("Kennard is guarding Raerei.") is None, order("Kennard is guarding Raerei."))

# ---- the player's own act is kept, whoever it names
told = sc.order_of('"Kennard, guard Raerei!" Twin Hammer Strike on the giant boar.')[0]
check("the player's own strike beside the order is kept", sc.own_part('"Kennard, guard Raerei!" Twin Hammer Strike on the giant boar.', told)
      == "Twin Hammer Strike on the giant boar", sc.own_part('"Kennard, guard Raerei!" Twin Hammer Strike on the giant boar.', told))
told = sc.order_of("Kennard, take wolf 1. I swing Brutal Strike at the wolf beside Kennard.")[0]
check("...even when it names the companion told", sc.own_part("Kennard, take wolf 1. I swing Brutal Strike at the wolf beside Kennard.", told)
      == "I swing Brutal Strike at the wolf beside Kennard", sc.own_part("Kennard, take wolf 1. I swing Brutal Strike at the wolf beside Kennard.", told))
told = sc.order_of('"Kennard, I\'m nearly done for, take the other one!" I use Guard Breaker on wolf 1.')[0]
check("...and an ability named in it is the player's own", sc.own_part('"Kennard, I\'m nearly done for, take the other one!" I use Guard Breaker on wolf 1.', told)
      == "I use Guard Breaker on wolf 1", sc.own_part('"Kennard, I\'m nearly done for, take the other one!" I use Guard Breaker on wolf 1.', told))
check("a line that is only an order acts on nothing else", sc.own_part("Kennard, take wolf 1.", [kennard]) == "")
check("...and what is said to a companion is not the player's own act, though it names the player's ability",
      sc.own_part("Kennard, take wolf 1 after my Brutal Strike!", [kennard]) == "", sc.own_part("Kennard, take wolf 1 after my Brutal Strike!", [kennard]))

# ---- a guard order keeps whom, says it, and guards that one
NARR.clear()
sc.show = lambda: None
sc.to_json = lambda: {}
sc.ws = type("WS", (), {"store": type("S", (), {"save_combat": lambda self, x: None})()})()
sc.give_orders([kennard], "guard", raerei.id)
check("the order keeps whom it guards", kennard.order == "guard" and kennard.order_target == raerei.id, (kennard.order, kennard.order_target))
check("...and the line printed says whom", NARR and NARR[-1] == "You tell Kennard to guard Raerei.", NARR[-1:])
f.round += 1
sc.give_orders([almund], "guard", "")
check("...a guard order with nobody named guards the player, and says so", almund.order_target == "" and NARR[-1] == "You tell Almund to guard you.", (almund.order_target, NARR[-1:]))
check("the guards of each: Kennard is Raerei's, Almund the player's", combat.guards_of(f, raerei) == [kennard] and combat.guards_of(f, f.player) == [almund],
      ([a.name for a in combat.guards_of(f, raerei)], [a.name for a in combat.guards_of(f, f.player)]))
kennard.order_target = w0.id
check("...a guard whose charge is no one on the player's side guards the player", kennard in combat.guards_of(f, f.player))
kennard.order_target = raerei.id
steps = {"raerei": 0, "player": 0}
for i in range(120):
    for x in (f.player, kennard, raerei, almund):
        x.hp = x.max_hp
    f.log = []
    combat.enemy_turn(f, w0, random.Random(i))
    for l in f.log:
        if "Kennard Holt steps in front of Raerei Wynn" in l:
            steps["raerei"] += 1
        if "Kennard Holt steps in front of" in l and f.player.name in l:
            steps["player"] += 1
check("a blow meant for the one guarded is sometimes taken by the guard, and one meant for the player never by her guard",
      steps["raerei"] >= 3 and steps["player"] == 0, steps)

# ---- the reading of who is addressed, on its own
people = {"k": ["kennard holt", "kennard"], "r": ["raerei wynn", "raerei"]}
check("addressing reads the head, the end, a telling and the party, and nothing else",
      [a.who for a in addressing.addressed("Kennard, hold back. I hide behind Raerei. Tell Raerei to heal me. Help me, Kennard! Everyone, run.", people)]
      == [("k",), ("r",), ("k",), ("*",)], addressing.addressed("Kennard, hold back. I hide behind Raerei. Tell Raerei to heal me. Help me, Kennard! Everyone, run.", people))
check("the player's own names are taken out of the line", addressing.without("Kennard, follow my Guard Breaker with a strike", ["Guard Breaker"]).lower().count("guard") == 0)

# ---- (f649's review) the ways an order is said that the first build lost, and the player's part inside the words
f.round += 1
check("a name said alone, then the order: 'Kennard! Fall back!'", order("Kennard! Fall back!") == (["Kennard"], "back", ""), order("Kennard! Fall back!"))
check("...and in quotes, with whom: '\"Kennard! Guard Raerei!\"'", order('"Kennard! Guard Raerei!"') == (["Kennard"], "guard", raerei.id), order('"Kennard! Guard Raerei!"'))
for line in ("Kennard and Raerei, hold back!", "Kennard, Raerei, hold back!", "I tell Kennard and Raerei to hold back.", "Hold back, Kennard and Raerei!"):
    check(f"two companions addressed are both told: {line!r}", order(line) == (["Kennard", "Raerei"], "hold", ""), order(line))
check("two told to guard the player are not told to guard each other", order("Kennard and Raerei, guard me!") == (["Kennard", "Raerei"], "guard", ""),
      order("Kennard and Raerei, guard me!"))
for line, want, mine in (("Kennard, take wolf 1 and I'll take wolf 0", ("focus", w1.id), "I'll take wolf 0"),
                         ("Kennard, cover Raerei while I strike wolf 1", ("guard", raerei.id), "I strike wolf 1"),
                         ("Raerei, heal me while I swing at wolf 1", ("heal", ""), "I swing at wolf 1"),
                         ("Kennard, I'll take wolf 1!", None, "I'll take wolf 1"),
                         ("I take wolf 1, Kennard!", None, "I take wolf 1")):
    got = order(line)
    check(f"the player's own part of the words said to a companion is theirs, not the order: {line!r}",
          (got is None if want is None else got[1:] == want) and sc.own_part(line, [kennard, raerei]) == mine, (got, sc.own_part(line, [kennard, raerei])))
for line in ("Kennard ducks and I strike wolf 1 with Twin Hammer Strike.", "Kennard staggers back, so I strike wolf 1.", "Kennard falls and I take wolf 1 myself."):
    check(f"a companion at the head of what the player does is spoken of, and the strike stays the player's: {line!r}", order(line) is None, order(line))
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(str(m)))
sc.interpret = lambda text: None
sc.act = lambda intent, text: None
sc.ws = type("WS", (), {"store": type("S", (), {"save_combat": lambda self, x: None})(), "combat": None})()
f.round += 1
sc.turn("Kennard, fall back! Raerei, heal Almund!")
check("a second order in a line is said to wait, not dropped unsaid", kennard.order == "back" and any("Raerei will have to wait" in n for n in NOTES), (kennard.order, NOTES))
for line, want in (("I shout for Kennard to fall back", ("back", "")), ("I whisper to Kennard to cover Raerei", ("guard", raerei.id)),
                   ("I nod at Kennard: take wolf 1", ("focus", w1.id)), ('"Cover Raerei," I tell Kennard.', ("guard", raerei.id)),
                   ("Cover Raerei, Kennard, while I take wolf 1.", ("guard", raerei.id)), ("Now everyone, take wolf 0", ("focus", w0.id))):
    got = order(line)
    check(f"an order said in the narration: {line!r}", got is not None and got[1:] == want and (got[0] == ["Kennard"] or line.startswith("Now everyone")), got)
check("a name typed with a curly apostrophe is still the name",
      CombatScene.addressees([party.fighter({"id": "d", "name": "D'arcy Lane", "role": "fighter", "level": 3})])
      and addressing.addressed("D" + chr(0x2019) + "arcy, take wolf 1", {"d": ["d'arcy lane", "d'arcy"]})[0].who == ("d",))

# ---- (f649's second review) a list of names before what is said of one, whom the order is for, the player's part, the next sentence
f.round += 1
for line, want in (("Raerei, Kennard needs healing, heal him!", (["Raerei"], "heal", kennard.id)),
                   ("Kennard, Raerei needs help, guard her!", (["Kennard"], "guard", raerei.id)),
                   ("Raerei, Kennard is down, heal him!", (["Raerei"], "heal", kennard.id)),
                   ("Kennard, Raerei is down, protect her!", (["Kennard"], "guard", raerei.id)),
                   ("Kennard, guard me while Raerei heals.", (["Kennard"], "guard", "")),
                   ("Kennard, cover me so Raerei can get clear.", (["Kennard"], "guard", "")),
                   ("Raerei, heal me before Kennard falls.", (["Raerei"], "heal", "")),
                   ("Kennard, Raerei is down, guard Almund!", (["Kennard"], "guard", almund.id)),
                   ("Kennard, shield me better than Raerei did.", (["Kennard"], "guard", "")),
                   ("Kennard, while I strike wolf 0, take wolf 1.", (["Kennard"], "focus", w1.id)),
                   ("Kennard, as I strike wolf 0, take wolf 1.", (["Kennard"], "focus", w1.id)),
                   ("Kennard, and I mean it, hold back!", (["Kennard"], "hold", "")),
                   ("Kennard, listen. Take wolf 1!", (["Kennard"], "focus", w1.id)),
                   ("Kennard, I'm hurt. Cover me!", (["Kennard"], "guard", "")),
                   ("Kennard, I'm done for. Take wolf 1!", (["Kennard"], "focus", w1.id))):
    check(f"read as said: {line!r}", order(line) == want, order(line))
check("the player's part ends where the words to the companion start again",
      sc.own_part("Kennard, take wolf 1 while I strike wolf 0, then guard Raerei.", [kennard]) == "I strike wolf 0",
      sc.own_part("Kennard, take wolf 1 while I strike wolf 0, then guard Raerei.", [kennard]))
for line in ("I look at Kennard, then take wolf 1", "I turn to Kennard and strike wolf 1", "I call to Kennard and take wolf 1 myself",
             "I tell Kennard that I will hold back."):
    check(f"a companion looked at, turned to or told of what the player does is told nothing: {line!r}", order(line) is None, order(line))
check("...and the player's act is theirs", sc.own_part("I turn to Kennard and strike wolf 1", [kennard]) == "I turn to Kennard and strike wolf 1",
      sc.own_part("I turn to Kennard and strike wolf 1", [kennard]))
check("a name typed with a curly apostrophe beside a pronoun points back right",
      order("Raerei" + chr(0x2019) + "s down. Kennard, protect her!") == (["Kennard"], "guard", raerei.id), order("Raerei" + chr(0x2019) + "s down. Kennard, protect her!"))
NOTES.clear()
sc.ws = type("WS", (), {"store": type("S", (), {"save_combat": lambda self, x: None})(), "combat": None})()
f.round += 1
sc.turn("Kennard, heal me! Raerei, guard me!")
check("a refused order lets the next one be given, and nobody is said to wait",
      raerei.order == "guard" and not any("will have to wait" in n for n in NOTES) and any("no healing" in n for n in NOTES), (raerei.order, NOTES))

# ---- (f649's third review) what the first builds read worse than before them
f.round += 1
for line, want in (("I have Kennard guard me.", (["Kennard"], "guard", "")), ("I have Raerei heal Kennard.", (["Raerei"], "heal", kennard.id)),
                   ("I let Kennard take wolf 1.", (["Kennard"], "focus", w1.id)), ("I turn to Raerei, heal me!", (["Raerei"], "heal", "")),
                   ('"Hold back," I tell Kennard, and I charge wolf 1.', (["Kennard"], "hold", "")),
                   ("Wolf 1 is on me, Kennard, guard me!", (["Kennard"], "guard", "")),
                   ("Kennard and Raerei take wolf 1.", (["Kennard", "Raerei"], "focus", w1.id)),
                   ("I ask Raerei to heal him, Kennard is bleeding.", (["Raerei"], "heal", kennard.id)),
                   ("Raerei, heal him, Kennard is bleeding!", (["Raerei"], "heal", kennard.id))):
    check(f"read as said: {line!r}", order(line) == want, order(line))
check("...and the player's own act after the quote is theirs", sc.own_part('"Hold back," I tell Kennard, and I charge wolf 1.', [kennard]) == "I charge wolf 1",
      sc.own_part('"Hold back," I tell Kennard, and I charge wolf 1.', [kennard]))
check("a name said alone, then the player's own deed, tells the companion nothing", order('"Kennard!" I yell, and charge wolf 1.') is None,
      order('"Kennard!" I yell, and charge wolf 1.'))
check("a him with no one named, before or after, is no order at all: never the player", order("Raerei, heal him!") is None, order("Raerei, heal him!"))
f.round += 1
sc.give_orders([almund], "hold", "")                      # this turn's order, already given
NOTES.clear()
sc.turn("Kennard, take wolf 1! Raerei, heal me!")
check("an order already given this turn is said once, and ends the line's orders",
      sum("already given" in n for n in NOTES) == 1 and not any("will have to wait" in n for n in NOTES), NOTES)
f.round += 1
NOTES.clear()
sc.turn("Kennard, fall back! Kennard, guard me!")
check("a second order to the one already told is said to wait too", kennard.order == "back" and any("Kennard will have to wait" in n for n in NOTES), (kennard.order, NOTES))

# ---- a companion named for its kind, beside foes of that kind
pet = combat.companion_fighter(world.bestiary["wolf"], 3, "comp_w", "Wolf")
pet.side = "ally"
f.fighters.append(pet)
check("a companion called Wolf is not told what 'Wolf 1' does", order("Wolf 1 lunges at me, so I strike it.") is None and order("Wolf 0 attacks Kennard") is None,
      (order("Wolf 1 lunges at me, so I strike it."), order("Wolf 0 attacks Kennard")))
check("...and is told when spoken to", order("Wolf, take wolf 1!") == (["Wolf"], "focus", w1.id), order("Wolf, take wolf 1!"))
f.fighters.remove(pet)

# ---- the gear the player wears is theirs, not an order
gear = type("Item", (), {"name": "Guardian Shield"})()
sc.ws = type("WS", (), {"acting": "p1", "player_of": lambda self, i: type("P", (), {"character": type("C", (), {"equipment": {"off_hand": gear}})()})()})()
from engine import items as _items
real_display = _items.display_name
_items.display_name = lambda i: i.name
check("worn gear named in an order is not read as one: 'Kennard, strike past my Guardian Shield at wolf 1'",
      order("Kennard, strike past my Guardian Shield at wolf 1") == (["Kennard"], "focus", w1.id), order("Kennard, strike past my Guardian Shield at wolf 1"))
_items.display_name = real_display

import shutil
shutil.rmtree("saves/addressed_orders_649", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
