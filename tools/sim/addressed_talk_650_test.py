"""(f650) Out of a fight, a talk goes to the one the line speaks to, read as the fight reads an order (engine/addressing.py)
(docs/design/21_play_faults_plan.md, B1; found by B0's corpus: "I ask my companion what he makes of the guard's story" was said to the
guard). When the line speaks to someone (their trade or their name at its head, called at its end, or the one the player asks or
tells: "I ask the guard who he serves", "I tell the guard that my companion needs rest", "Guard, what did my companion do last
night?"), a talk the reading aimed at a companion is theirs, and of two of one trade, the one already talking; a line that speaks to
the companion keeps the talk with them, whoever else it names. A line that speaks to no one is left to the old rule (a name or trade
it holds), so nothing that rule reached is lost ("I talk to the guard about the road").
Run: python tools/sim/addressed_talk_650_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from engine import addressing
from tools import interp_eval

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


cases = {c["name"]: c for c in interp_eval.load_cases()}
NAMES = ["asking_a_companion_about_the_guard_stays_with_the_companion", "asking_a_friend_about_the_guard_stays_with_the_friend",
         "words_for_the_guard_go_to_the_guard", "words_called_to_the_guard_go_to_the_guard", "telling_the_guard_of_a_companion_goes_to_the_guard",
         "the_cook_asked_what_is_in_the_pot_is_the_cook", "of_two_guards_the_one_already_talking_is_spoken_to",
         "talking_to_the_guard_about_the_road_is_the_guard"]
check("the corpus holds the cases of this class", all(n in cases for n in NAMES), [n for n in NAMES if n not in cases])
out = interp_eval.evaluate([cases[n] for n in NAMES if n in cases], quiet=True, save="addressed_talk_650")
check("a companion asked about the guard keeps the talk; a guard or a cook spoken to gets it; of two guards, the one talking", not out["wrong"] and not out["owed"], out)
check("...and the case B0 owed to B1 is no longer marked owed", not cases["asking_a_companion_about_the_guard_stays_with_the_companion"].get("owed"))
check("to_the_named still acts where the line speaks to someone else", "to_the_named" in out["acted"] and "to_the_named" in out["held_off"], out)

# ---- the reading of who is spoken to, out of a fight
people = {"g1": ["the guard", "guard"], "hire:h0": ["bram voss", "bram", "my companion", "my friend"]}   # as addressees_here gives them, one companion
for line, want in (("I ask the guard who he serves", ("g1",)), ("I tell the guard that my companion needs rest", ("g1",)),
                   ("Guard, what did my companion do last night?", ("g1",)), ("I ask my companion what he makes of the guard's story", ("hire:h0",)),
                   ("I ask Bram about the guard", ("hire:h0",))):
    got = addressing.addressed(line, people)
    check(f"spoken to: {line!r}", bool(got) and got[0].who == want, got)
check("someone only spoken of is not spoken to", addressing.addressed("I wonder aloud whether the guard saw anything", people) == [])
check("a line that speaks to no one is left to the reading's own rule (a name or trade it holds), as before",
      addressing.addressed("I talk to the guard about the road", people) == [])
check("words asked or told of someone are no order: 'I tell Kennard that I will hold back' asks him nothing",
      [a.said for a in addressing.addressed("I tell Kennard that I will hold back.", {"k": ["kennard"]})] == [""])
check("...nor 'I ask Kennard if he can take wolf 1'", [a.said for a in addressing.addressed("I ask Kennard if he can take wolf 1", {"k": ["kennard"]})] == [""],
      addressing.addressed("I ask Kennard if he can take wolf 1", {"k": ["kennard"]}))

# ---- (f650's second review) the repair itself: two spoken to, a trade used as a verb, the player's act after an ask in a fight
from llm.contracts import ActionIntent as A
from npc.models import NPC
g = simlib.campaign("addressed_talk_650_scene", cls="warrior", seed=3, location="trading_square")
ws = g.scene
guard = NPC(id="g1", name="Garran Holt", people="human", role="guard", location="trading_square", traits=[])
ws.present = [guard]
ws.player.party = [{"id": "h0", "name": "Bram Voss", "role": "fighter", "level": 3, "permanent": True}]
ws.partner, ws.last_spoken = None, None


def turned(line, targets):
    plan = [A(kind="talk", target=t, speech="x") for t in targets]
    ws.to_the_named(line, plan)
    return [a.target for a in plan]


for line, before, after in (("I ask the guard who he serves. I ask Bram what he thinks.", ["g1", "hire:h0"], ["g1", "hire:h0"]),
                            ("I ask the guard who he serves, then I ask Bram what he thinks", ["g1", "hire:h0"], ["g1", "hire:h0"]),
                            ("I ask the guard who he serves. Bram, keep watch.", ["g1", "hire:h0"], ["g1", "hire:h0"]),
                            ("Guard the gate while I sleep, I tell Bram", ["hire:h0"], ["hire:h0"]),
                            ("Guard, who do you serve?", ["hire:h0"], ["g1"]),
                            ("Guard, has Bram been here before?", ["hire:h0"], ["g1"]),
                            ("I ask my companion what he makes of the guard's story", ["hire:h0"], ["hire:h0"]),
                            ("I talk to the guard about the road", ["hire:h0"], ["g1"])):
    check(f"each talk goes to the one it is said to: {line!r}", turned(line, before) == after, turned(line, before))
import types
from scenes.combat_scene import CombatScene
sc = CombatScene.__new__(CombatScene)
k = types.SimpleNamespace(id="k", name="Kennard Holt", alive=True, ally_role="fighter")
r = types.SimpleNamespace(id="r", name="Raerei Wynn", alive=True, ally_role="priest")
strike = types.SimpleNamespace(name="Brutal Strike")
sc.fight = types.SimpleNamespace(allies=lambda: [k, r], enemies=lambda: [], player=types.SimpleNamespace(moves=[strike]))
for line, mine in (("Kennard, guard me. I ask Raerei if she is hurt, then Brutal Strike wolf 1.", "Brutal Strike wolf 1"),
                   ("Kennard, guard me. I tell Raerei about the trap and Brutal Strike wolf 1.", "Brutal Strike wolf 1"),
                   ("Kennard, guard me. I tell Raerei what I'm doing: I charge wolf 1.", "I charge wolf 1"),
                   ("Kennard, guard me. I ask Raerei if she can heal Kennard and Almund.", "")):
    check(f"the player's own act after what a companion is asked, and nothing that is not one: {line!r}", sc.own_part(line, [k]) == mine, sc.own_part(line, [k]))
g.close()
shutil.rmtree("saves/addressed_talk_650_scene", ignore_errors=True)
shutil.rmtree("saves/addressed_talk_650", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
