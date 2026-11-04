"""(f465) Scene state restored per operation: every attribute WorldScene.ROLLED declares, set inside an operation that then fails, is back
to what it was before it; a person the scene held and wrote inside a failed operation carries no memory id of a row that no longer
exists; the marks the fight's perks and heals keep are as they were before a rolled-back operation and gone at a fight's end; and the
session owns them with the live check's lists, so nothing of a campaign stays in the process once it closes."""
import copy
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from engine import canon, combat, combat_perks, healing, severity
from llm.gateway import LLMError
from npc.models import NPC, Memory
from scenes import combat_scene as cs
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


g = simlib.campaign("scene_465", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/scene_465/turns.jsonl"
simlib.quiet_console()
ws.enter("parth")
MISSING = object()

# ---- every declared attribute set inside a failing operation is back to what it was
check("the declared state names what a line writes outside the save", len(ws.ROLLED) >= 20 and "recent_narration" in ws.ROLLED and "last_plan" in ws.ROLLED)
ws.recent_narration = ["what was told before"]
ws.last_spoken = "someone"
before = {k: (copy.deepcopy(ws.__dict__[k]) if k in ws.__dict__ else MISSING) for k in ws.ROLLED}
with ws.operation("test", "a failing step") as op:
    for k in ws.ROLLED:
        setattr(ws, k, f"sentinel:{k}")
    raise LLMError("the model failed")
after = {k: ws.__dict__.get(k, MISSING) for k in ws.ROLLED}
moved = [k for k in ws.ROLLED if k != "step" and ((after[k] is MISSING) != (before[k] is MISSING) or (after[k] is not MISSING and after[k] != before[k]))]
check("every declared attribute is as it was before the operation, and one it set anew is unset", op.state == "rolled_back" and not moved, moved)
check("...and the step being done is none (the operation's abandon says so)", ws.step is None)
check("...the narrator's memory and the last one spoken to among them", ws.recent_narration == ["what was told before"] and ws.last_spoken == "someone")

# ---- a person the scene held and wrote inside a failed operation keeps no memory of a row that is gone
npc = NPC(id="n465", name="Ost Vell", people="human", role="farmer", location="parth", traits=[], trust=50)
store.save_npc(npc)
ws.present, ws.residents = [npc], [npc]
with ws.operation("test", "a word to Ost") as op:
    held = ws.npc_by_id("n465")
    held.memories.append(Memory(importance=1, day=1, turn=1, text="a memory that will not be"))
    store.save_npc(held)
    raise LLMError("the model failed")
rows = {r[0] for r in store._db.execute("SELECT id FROM npc_memory WHERE npc_id = 'n465'")}
again = ws.npc_by_id("n465")
check("no one the scene holds carries a memory of a row that was rolled back", op.state == "rolled_back" and again is not None
      and all(m.id is None or m.id in rows for m in again.memories) and not any(m.text == "a memory that will not be" for m in again.memories),
      [(m.id, m.text) for m in again.memories] if again else None)

# ---- the fight's marks: as they were before a rolled-back operation, gone at the fight's end
combat_perks.QUARRY["fight_a"] = "e1"
healing.LAST["fight_a"] = ("p", 3.0)
with ws.operation("test", "a round that fails") as op:
    combat_perks.QUARRY["fight_b"] = "e2"
    combat_perks.WITHER[("fight_b", "e2")] = "p"
    healing.LAST["fight_b"] = ("p", 5.0)
    raise LLMError("the model failed")
check("marks made inside a rolled-back operation are gone, the earlier ones stand", "fight_b" not in combat_perks.QUARRY and ("fight_b", "e2") not in combat_perks.WITHER
      and "fight_b" not in healing.LAST and combat_perks.QUARRY.get("fight_a") == "e1" and healing.LAST.get("fight_a") == ("p", 3.0),
      (dict(combat_perks.QUARRY), dict(combat_perks.WITHER), dict(healing.LAST)))
combat_perks.QUARRY.clear()
healing.LAST.clear()
ws.narrate_with = lambda *a, **k: None
creature = ws.world.bestiary["bandit"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", name="bandit 1")
foe.hp = foe.max_hp = 1
sc = cs.CombatScene.begin(ws, creature, [foe], "It is on you:")
ws.combat = sc
key = combat.fight_key(sc.fight)
store.save_combat(sc.to_json())          # (f497) the row carries the mark too: the round's line stands down at its reading, and the fight is resumed from the row
combat_perks.QUARRY[key] = "e1"
combat_perks.WITHER[(key, "e1")] = "p"
healing.LAST[key] = ("p", 2.0)
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
stood = ws.turn("I attack the bandit")
check("at a fight's end what the perks and heals remembered of it goes", stood is True and ws.combat is None and key not in combat_perks.QUARRY
      and not any(k[0] == key for k in combat_perks.WITHER) and key not in healing.LAST, (stood, dict(combat_perks.QUARRY), dict(healing.LAST)))

# ---- the session owns the marks and the live check's lists
from engine import session
owned = [n for n, *_ in session._owned()]
check("the session owns the fight marks, the heal memory and the live check's lists", all(x in owned for x in ("combat_perks.QUARRY", "combat_perks.WITHER", "healing.LAST", "canon.EVENTS", "canon._SINK", "severity.REACTIONS")), owned)
combat_perks.QUARRY["left"] = "x"
canon.EVENTS.append({"claim": "left over"})
severity.REACTIONS.append(("sobered", False))
g.close()
check("nothing of it stays in the process once the campaign closes", simlib.residue() == {} and not canon.EVENTS and not combat_perks.QUARRY, simlib.residue())
import shutil
shutil.rmtree("saves/scene_465", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
