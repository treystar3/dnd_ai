"""(f659) Every part of a fight line is acted on, and the foe the player names is the one struck, or the player is told why not
(docs/design/21_play_faults_plan.md, B3; found in play: docs/play/2026-11-15_play_findings.md 1.8 and 1.9). "I drink the healing
draught, then use Twin Hammer Strike on wolf 1." drank and never struck: the fight's reading returns one intent, and a draught is a
free act that ended the turn's reading. "... I use Guard Breaker on wolf 2." struck wolf 3: the target came from the model, or from
the service turning on the closest foe when the one named was down, and nothing said so.
Held here: a free act (a draught) and an act in one line are both done, in either order of words; a line of only the draught is only
the draught; the foe the player's own words name is the target whatever the reading said; a named foe already down is said to be
down, and the player is told whom they turn on instead.
Run: python tools/sim/fight_line_parts_659_test.py"""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import ui.console as uc
NOTES, NARR = [], []
uc.put("note", lambda m, *a, **k: NOTES.append(m))
uc.put("narrate", lambda t, *a, **k: NARR.append(t))
from engine import battlefield, combat, inventory
from llm.contracts import CombatIntent
from scenes import combat_scene as cs

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("fight_line_parts_659_test", seed=5, location="greywood")
ws, world = g.scene, g.scene.world
ROUNDS = []


def scene(n=3):
    me = combat.fighter_from_character(ws.player.character)
    wolves = [combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", f"e{i}", f"wolf {i + 1}") for i in range(n)]
    fight = combat.Combat(fighters=[me] + wolves, place="greywood")
    for w in wolves:
        battlefield.engage(fight, w, fight.player)
    fight.round = 1
    sc = cs.CombatScene(ws, fight, "wolf")
    ws.combat = sc
    return sc, fight, wolves


from services.fight import FightService
_real_round = FightService.round
FightService.round = lambda self, f, intent: (ROUNDS.append(intent), _real_round(self, f, intent))[1]


def draught():
    ws.player.character.inventory = [i for i in ws.player.character.inventory if i.good != "healing_draught"] + [inventory.make_good("healing_draught", 3)]


def drafts() -> int:
    return sum(i.quantity for i in ws.player.character.inventory if i.good == "healing_draught")


strike = None


def reading(sc, target_id):
    """The model's reading: the draught when the line is only the draught, else the strike, aimed where the test says."""
    def interpret(text):
        low = text.lower()
        if "draught" in low and not any(w in low for w in ("strike", "use brutal", "attack", "swing")):
            return CombatIntent(kind="item", item="healing draught")
        if "draught" in low:
            return CombatIntent(kind="item", item="healing draught")        # the one intent the reading gives for both
        return CombatIntent(kind="ability", ability=strike, target=target_id)
    sc.interpret = interpret


sc, f, wolves = scene()
strike = next(m.id for m in f.player.moves if m.name == "Brutal Strike")
for line in ("I drink the healing draught, then use Brutal Strike on wolf 1.", "I use Brutal Strike on wolf 1 and drink a healing draught.",
             "I drink a healing draught and I attack wolf 1"):
    sc, f, wolves = scene()
    reading(sc, "e0")
    draught()
    ws.player.character.health = 5
    ROUNDS.clear()
    before = drafts()
    sc.turn(line)
    check(f"1.8: the draught drunk and the strike struck: {line!r}",
          drafts() == before - 1 and len(ROUNDS) == 1 and ROUNDS[0].kind == "ability", (before, drafts(), [r.kind for r in ROUNDS]))
sc, f, wolves = scene()
reading(sc, "e0")
draught()
ROUNDS.clear()
before = drafts()
sc.turn("I drink a healing draught.")
check("a line of only the draught is only the draught: no round is fought", drafts() == before - 1 and not ROUNDS, (drafts(), ROUNDS))
sc, f, wolves = scene()
reading(sc, "e0")
ws.player.character.inventory = [i for i in ws.player.character.inventory if i.good != "healing_draught"] + [inventory.make_good("healing_draught", 1)]
READS = []
real_read = sc.interpret
sc.interpret = lambda text: (READS.append(text), real_read(text))[1]
ROUNDS.clear()
sc.turn("I drink a healing draught.")
check("...even the last one: the line is read once, and the draught is not read again as another act", drafts() == 0 and len(READS) == 1
      and not ROUNDS, (drafts(), READS, ROUNDS))

for line, wrong, named in (("I use Brutal Strike on wolf 2.", "e2", "e1"), ('"Kennard, take the other one!" I use Brutal Strike on wolf 3.', "e0", "e2"),
                           ("Brutal Strike on Wolf 2, now!", "e0", "e1")):
    sc, f, wolves = scene()
    reading(sc, wrong)
    ROUNDS.clear()
    sc.turn(line)
    check(f"1.9: the foe the player names is the one struck, whatever the reading said: {line!r}", ROUNDS and ROUNDS[0].target == named,
          [r.target for r in ROUNDS])
sc, f, wolves = scene()
reading(sc, "e1")
ROUNDS.clear()
sc.turn("I use Brutal Strike on it.")
check("a line that names no foe keeps the reading's target", ROUNDS and ROUNDS[0].target == "e1", [r.target for r in ROUNDS])
sc, f, wolves = scene()
reading(sc, "e2")
ROUNDS.clear()
sc.turn("I strike wolf 1, then wolf 3 if it still stands.")
check("...and so does a line that names two", ROUNDS and ROUNDS[0].target == "e2", [r.target for r in ROUNDS])

sc, f, wolves = scene()
ward = next((m for m in f.player.moves if str(getattr(m.effect, "value", m.effect)) == "defense"), None)
check("(the warrior holds a ward)", ward is not None, [(m.name, m.effect) for m in f.player.moves])
if ward:
    sc.interpret = lambda text: CombatIntent(kind="ability", ability=ward.id)
    ROUNDS.clear()
    sc.turn(f"I raise {ward.name} as wolf 2 closes in.")
    check("a ward the player raises is not turned on the foe the line names", ROUNDS and ROUNDS[0].target == "", [r.target for r in ROUNDS])
sc, f, wolves = scene()
wolves[1].hp = 0
reading(sc, "e1")
ROUNDS.clear()
NOTES.clear()
sc.turn("I use Brutal Strike on wolf 2.")
said = " ".join(NOTES)
check("a named foe already down: the player is told so, and whom they turn on instead",
      ROUNDS and ROUNDS[0].target in ("e0", "e2") and "wolf 2" in said.lower() and "down" in said.lower()
      and any(w.name in said for w in wolves if w.id == ROUNDS[0].target), (said, [r.target for r in ROUNDS]))
shutil.rmtree("saves/fight_line_parts_659_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
