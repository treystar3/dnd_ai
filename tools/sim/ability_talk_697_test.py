"""(f697) An ability named as the line's own deed is that ability, not words to a companion (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). In the Willowmead wetlands, `Twin Flare at the will-o'-wisps.` was read as words said to
Pae ("Telling the group about the plan"), and she answered. use_to_ability already took an ability named as if it were an item.
Held here: a talk whose words open with one of the acting character's prepared abilities, in a line that itself opens with it ("Twin
Flare at the wisps", "I cast Twin Flare at them"), is that ability; a one-word ability counts only when aimed (at, on, against); words
said aloud in any quotes, after a colon or to a companion called first, a talk that only mentions it later, and an ability the
character has not prepared, are left as read; the deed before words said aloud is the deed.
Run: python tools/sim/ability_talk_697_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 6))
simlib.quiet_console()
from engine import loadout
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("ability_talk_697", seed=5, location="greywood")
ws = g.scene
ws.enter("greywood")
ab = next(a for a in loadout.prepared(ws.player.character) if a.context.value == "combat")


def read(text, speech=None):
    plan = [A(kind="talk", target="hire:0-0", speech=speech if speech is not None else text, summary="telling the group")]
    out = ws.repair(text, plan)
    return [(a.kind, a.ability) for a in out]


check(f"'{ab.name} at the wisps.' read as talk is the ability", read(f"{ab.name} at the wisps.") == [("ability", ab.id)], read(f"{ab.name} at the wisps."))
check("...and 'I cast it at them' too", read(f"I cast {ab.name} at them.") == [("ability", ab.id)])
check("...in any case of letters", read(f"{ab.name.lower()} at the wolf") == [("ability", ab.id)])
said = f'"{ab.name} is my best spell," I tell Pae.'
check("words said aloud that name it stay words", read(said, f"{ab.name} is my best spell") == [("talk", "")], read(said, f"{ab.name} is my best spell"))
check("a talk that only mentions it later stays a talk", read(f"Pae, watch how I use {ab.name} later.") == [("talk", "")])
check("an ability the character has not prepared is no ability", read("Meteor Swarm at the wisps.") == [("talk", "")])
check("words after a colon are said: 'I tell Pae: ... is ready.'", read(f"I tell Pae: {ab.name} is ready.", f"{ab.name} is ready") == [("talk", "")])
check("words in single quotes are said too", read(f"'{ab.name} is my best spell,' I tell Pae.", f"{ab.name} is my best spell") == [("talk", "")])
check("a companion called first is given an order, not the player's cast",
      read(f"Pae, {ab.name} at the wolf!", f"{ab.name} at the wolf!") == [("talk", "")])
mixed = ws.repair(f'{ab.name} at the wisps. "Stay back, Pae!"', [A(kind="talk", target="hire:0-0", speech=f"{ab.name} at the wisps."),
                                                               A(kind="talk", target="hire:0-0", speech="Stay back, Pae!")])
check("the deed before words said aloud is the deed, and the words stay words", [(a.kind, a.ability) for a in mixed] == [("ability", ab.id), ("talk", "")],
      [(a.kind, a.ability) for a in mixed])
from engine import loadout as lo
real_prepared = lo.prepared
guard = ab.model_copy(update={"id": "guard", "name": "Guard"})
lo.prepared = lambda c: [guard]
check("a one-word ability that is a common word is the ability only when aimed: 'Guard the camp tonight, Pae.' is words",
      read("Guard the camp tonight, Pae.") == [("talk", "")])
check("...while 'Guard on Pae' is the ability", read("Guard on Pae.") == [("ability", "guard")])
lo.prepared = real_prepared
g.close()
shutil.rmtree("saves/ability_talk_697", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
