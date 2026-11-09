"""(f465) Scene state restored per operation: every attribute WorldScene.ROLLED declares, set inside an operation that then fails, is back
to what it was before it; a person the scene held and wrote inside a failed operation carries no memory id of a row that no longer
exists; (f499) the marks the fight's perks and heals keep are its row's: back with the row on a rollback, gone with it at the fight's end; and the
session owns them with the live check's lists, so nothing of a campaign stays in the process once it closes."""
import copy
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from engine import canon, combat, severity
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

# ---- (f499) the fight's marks are its row's: back with the row on a rollback, gone with the row at the fight's end
from engine import effects
shrub = ws.world.bestiary["awakened_shrub"]                        # fearless: it never yields, so the fight ends when it falls
foe = combat.fighter_from_creature(shrub, 1, "normal", "e1", name="awakened shrub")
foe.hp = foe.max_hp = 1
sc = cs.CombatScene.begin(ws, shrub, [foe], "It is on you:")
ws.combat = sc
effects.put(sc.fight, effects.ActiveEffect(id="quarry", kind="quarry", family="mark", source="p", target="e1"))
effects.put(sc.fight, effects.ActiveEffect(id="last_heal", kind="last_heal", family="heal", source="p", target="p", value=2.0))
store.save_combat(sc.to_json())                                    # the committed fight: its marks in its row
with ws.operation("test", "a round that fails") as op:
    effects.put(ws.combat.fight, effects.ActiveEffect(id="withering:e1", kind="withering", family="affliction", source="p", target="e1"))
    store.save_combat(ws.combat.to_json())
    raise LLMError("the model failed")
rows = {r.kind: r for r in ws.combat.fight.effects} if ws.combat else {}
check("a mark made inside a rolled-back operation goes with the row; the committed ones stand (the fight resumed from its row)",
      op.state == "rolled_back" and ws.combat is not None and "withering" not in rows and rows.get("quarry") and rows["quarry"].target == "e1"
      and rows.get("last_heal") and rows["last_heal"].value == 2.0, (op.state, {k: r.model_dump() for k, r in rows.items()}))
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
for _ in range(4):                                                 # a blow may miss: a few rounds at most
    stood = ws.turn("I attack the shrub")
    if ws.combat is None or stood is not True:
        break
check("at a fight's end what it remembered of itself goes with its row", stood is True and ws.combat is None and store.load_combat() is None, (stood, ws.combat))

# ---- the session owns the live check's lists, and no mark table
from engine import session
owned = [n for n, *_ in session._owned()]
check("the session owns the live check's lists, and no table of the fight's marks (f499: the row carries them)",
      all(x in owned for x in ("canon.EVENTS", "canon._SINK", "severity.REACTIONS"))
      and not any(x in owned for x in ("combat_perks.QUARRY", "combat_perks.WITHER", "healing.LAST", "spellcraft._CAST")), owned)
canon.EVENTS.append({"claim": "left over"})
severity.REACTIONS.append(("sobered", False))
g.close()
check("nothing of it stays in the process once the campaign closes", simlib.residue() == {} and not canon.EVENTS, simlib.residue())
import shutil
shutil.rmtree("saves/scene_465", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
