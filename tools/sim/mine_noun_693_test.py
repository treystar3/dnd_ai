"""(f693) The gate's first-person words have senses that are not the first person (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). Travelling to the Ironcrown Peaks, the passage was refused twice ("the narrator speaks
to the player as 'you'; 'I', 'me' and 'my' belong only inside someone's quoted speech (not 'mine')") and the player read only "the
telling of it slipped away": the mountains are mining country, and a pit dug for ore was read as the first person.
Held here: "mine" is the narrator's own only in a possessive frame (hygiene.yaml first_person_senses: after is, of, like, in, meet
and their kind; "'s mine" closing a clause; "Mine is" opening a sentence), so the place and the verb pass ("an old mine", "Mine carts",
"the Deepdelve Mine", "Ironcrown's mine lies cold", "Dwarves mine the veins"); a king's numeral is no "I" ("King Harald I"); every
possessive "mine", and I, me, my and myself anywhere, are still sent back; inside quoted speech any of them passes.
Run: python tools/sim/mine_noun_693_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from engine import hygiene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


def flagged(text):
    return hygiene.problem("narrate", {"text": text})[0] == "first_person"


check("(the gate's check is reachable)", flagged("You walk on.") is False and flagged("I walk on.") is True)
for ok in ("You pass the mouth of an old mine cut into the slope.", "Smoke rises from the mine below.", "Mine carts rust beside the track.",
           "The road bends toward the Deepdelve Mine.", "A mine shaft yawns in the rock.", "Every abandoned dwarven mine in these peaks has its ghosts.",
           "Ironcrown's mine lies cold.", "Dwarves mine the deep veins for silver.", "They mine iron here.", "Silver mine country stretches east.",
           "King Harald I rules these peaks.", 'The foreman shouts, "That claim is mine!"', "You step into the mine."):
    check(f"passes: '{ok}'", flagged(ok) is False, ok)
for no in ("The choice is mine to make.", "A friend of mine waits by the gate.", "Mine is the only lantern lit.", "His eyes meet mine.",
           "Her hand in mine, we walk.", "A heart like mine knows.", "This one's mine.", "The pleasure's all mine.", "The gold is mine.",
           "Each day I mine the hill.", "The ore I mine is yours.", "I see the peaks ahead.", "My boots slip on the scree.",
           "The wind bites at me.", "Then I walk on.", "The Peaks\nMine is the lantern."):
    check(f"sent back: '{no}'", flagged(no) is True, no)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
