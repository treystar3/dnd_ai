"""(f496) What a re-run forgets, fixed where it costs no digest. An operation that stands down to ask the model outside runs again from
its start (f485), and must find what its first attempt found: the creeping up (ws.sneaking), the buffs readied by name, the line's
words and the captive taken go back with the scene's declared state (WorldScene.ROLLED), so the stealth roll is made on the re-run;
and the fight's scene, resumed from the row, is given back what the player has read of this fight (fight_shown) and who was tamed, as
the operation found them, so the round's telling after a stood-down line is told not to describe the ground and the light again. The
serial decides it is the same fight. Nothing of the save moves: shown-memory, not state. And nothing stays in the process."""
import shutil
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import combat
from llm import gateway
from llm.contracts import ActionIntent, DialogueFrame
import nightrun

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "fight_rerun_496"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")
check("the declared state names the creeping up, the readied buffs, the line's words and the captive taken",
      {"sneaking", "queued_buffs", "fight_text", "surrender_took"} <= set(ws.ROLLED))

# ---- a fight begun by creeping up, whose operation stands down once: the re-run creeps up again
creature = ws.world.bestiary["mastiff"]
ws.wildlife = (creature, [combat.fighter_from_creature(creature, 2, "normal", "e1", "mastiff", "near")])
ws.sneaking, ws.queued_buffs, ws.fight_text = True, ["iron_skin"], "I creep up on the mastiff and strike."
resolved, seen = [], []
real_resolve = ws.resolve


def resolve(check_name, *a, **k):
    resolved.append((len(seen), check_name))
    return real_resolve(check_name, *a, **k)


ws.resolve = resolve


def body(op):
    seen.append((ws.sneaking, list(ws.queued_buffs), ws.fight_text))
    ws.on_attack(ActionIntent(kind="attack", target="mastiff"), "I creep up on the mastiff and strike.")
    if len(seen) == 1:
        gateway.generate("dialogue_frame", "You frame a line.", "The line.", DialogueFrame)     # asked outside: the operation stands down once


op, _ = ws.asked_operation("action:attack", "I creep up on the mastiff and strike.", body)
ws.resolve = real_resolve
check("the operation ran twice and stands", len(seen) >= 2 and op.state == "committed" and ws.combat is not None, (len(seen), op.state))
check("...every attempt found the creeping up, the readied buff and the line's words as the first did",
      all(s == (True, ["iron_skin"], "I creep up on the mastiff and strike.") for s in seen), seen)
check("...and the stealth roll was made on the re-run as on the first attempt (the first spent the creeping up; the re-run found it again)",
      [n for n, c in resolved if c == "stealth"] == list(range(1, len(seen) + 1)), (resolved, len(seen)))
check("...the creeping up is spent once the fight has begun", ws.sneaking is False)
opening = list(ws.combat.fight_shown)
check("the opening passage left what the player has read of the fight on its scene", bool(opening), opening)

# ---- a word to a companion mid-fight stands the line down; the round after it is told what was already shown
nightrun.hire_party(ws, 1)                                     # hired now, so nothing of theirs asked outside during the opening above
first = ws.player.party[0]["name"].split()[0]
REQ = []
real = gateway._client


def chat(**k):
    if k["format"].get("title") == "Narration":
        REQ.append(k["messages"][1]["content"])
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
stub.a_CombatIntent = lambda u, k: {"kind": "talk"}
calls0 = dict(stub.calls)
ws.turn(f"{first}, are you hurt?")
check("the word to the companion was answered (hire_chat, asked outside: the line stood down and ran again)",
      stub.calls.get("CompanionReply", 0) > calls0.get("CompanionReply", 0), stub.calls)
check("...and the resumed fight still holds what the player has read of it", ws.combat is not None and list(ws.combat.fight_shown) == opening,
      (opening, ws.combat.fight_shown if ws.combat else None))
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
REQ.clear()
ws.turn("I strike at the mastiff.")
told = next((r for r in REQ if "ALREADY SHOWN IN THIS FIGHT" in r), "")
check("the round's telling after the stood-down line is told not to describe the ground and the light again",
      told and all(line in told for line in opening), (REQ[-1][-600:] if REQ else REQ))
gateway._client = real

# ---- the same fight, by its serial: a different fight's memory is not given
fight0 = ws.fight_memory()
check("the fight's memory names what was read, who was tamed and which fight it is", fight0 is not None and fight0[0] == list(ws.combat.fight_shown)
      and fight0[2] == ws.combat.fight.serial, fight0)
ws.combat.fight_shown.append("a test line")
ws.give_back(None, [], (["from another fight"], ["a tamed wolf"], "other"))
check("...a resumed fight with another serial keeps its own", ws.combat is not None and "from another fight" not in ws.combat.fight_shown
      and not ws.combat.tamed, (ws.combat.fight_shown if ws.combat else None))
ws.give_back(None, [], fight0)
check("...the same fight is given back what the operation found", ws.combat is not None and list(ws.combat.fight_shown) == fight0[0]
      and "a test line" not in ws.combat.fight_shown)
game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
