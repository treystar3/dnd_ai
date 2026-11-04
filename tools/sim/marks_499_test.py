"""(f499) What a fight remembers of itself is on the saved fight (engine/effects.py; engine/combat.py Combat effects, shown, tamed; Fighter
casting): a hunter's quarry mark is in the saved row and survives a reopen mid-fight; a rolled-back round's marks go with the row and the
committed rounds' stand; a fight's end drops the row and nothing of it stays in the process (the session owns no mark table); a mid-fight
save reopened carries what the player has read of the fight and the next telling is told so; a fight with 300 expired rows holds
effects_keep; the casting context lives on the fighter and the purity fence finds no id() in spellcraft; nothing stays in the process."""
import json
import shutil
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import purity
from engine import combat, combat_perks, effects, session
from llm import gateway
from llm.gateway import LLMError
from scenes import combat_scene as cs
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "marks_499"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")
console.combat_state = lambda data: False
console.combat_panel = lambda lines: None
REQ = []
real = gateway._client


def chat(**k):
    if k["format"].get("title") == "Narration":
        REQ.append(k["messages"][1]["content"])
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)


def row():
    raw = store.load_combat()
    return json.loads(raw)["fight"] if raw else None


# ---- a hunter with quarry: the mark is in the saved row
creature = ws.world.bestiary["awakened_shrub"]                   # fearless: it never bolts or yields, so the fight lasts
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "awakened shrub", "near")
foe.hp = foe.max_hp = 600
ws.wildlife = (creature, [foe])
stub.plan = [{"kind": "attack", "target": "awakened shrub"}]
ws.turn("I attack the shrub.")
stub.plan = None
check("the fight is on, its row saved with an empty list of what it remembers", ws.combat is not None and row() is not None and row().get("effects") == []
      and "shown" in row() and "tamed" in row(), (row() or {}).keys() if row() else row())
me = ws.combat.fight.player
me.legendary["quarry"] = 1                                       # the hunter's mark, given for the test
me.mech_names.setdefault("quarry", "Quarry")
store.save_combat(ws.combat.to_json())                           # the row the next round resumes from
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
stood = ws.turn("I strike at the shrub.")
q = effects.get(ws.combat.fight, "quarry") if ws.combat else None
check("a blow marks the quarry, on the fight's own row (kind quarry, the foe its target)", stood is True and q is not None and q.target == "e1"
      and combat_perks.quarry_of(ws.combat.fight) is ws.combat.fight.get("e1")
      and any(r["kind"] == "quarry" and r["target"] == "e1" for r in row()["effects"]), (stood, row() and row()["effects"]))
shown0 = list(ws.combat.fight.shown)
check("...and what the player has read of the fight is in the row too", shown0 and row()["shown"] == shown0, (shown0, row() and row()["shown"]))

# ---- a reopen mid-fight: the quarry and what was read survive, and the next telling is told what was shown
game.close()
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields", fresh=False)
ws, store = game.scene, game.store
ws.enter(ws.player.location)
console.combat_state = lambda data: False
console.combat_panel = lambda lines: None
ws.combat = cs.CombatScene.resume(ws, store.load_combat())      # as run() resumes a saved fight when the game opens (scenes/world.py)
check("reopened mid-fight, the fight is on with its quarry and what was read of it", ws.combat is not None and effects.get(ws.combat.fight, "quarry") is not None
      and effects.get(ws.combat.fight, "quarry").target == "e1" and list(ws.combat.fight.shown) == shown0, (ws.combat is not None, shown0))
REQ.clear()
stood = ws.turn("I strike at the shrub.")
told = next((r for r in REQ if "ALREADY SHOWN IN THIS FIGHT" in r), "")
check("...and the round's telling after the reopen is told what was already shown: the fight tells as one unbroken run",
      stood is True and told and all(line in told for line in shown0), (stood, REQ[-1][-400:] if REQ else REQ))

# ---- a rolled-back round's marks go with the row; the committed rounds' stand
effects.drop(ws.combat.fight, "quarry")                          # the mark let go between rounds (as a quarry's fall lets it go): the next blow marks again
store.save_combat(ws.combat.to_json())
last0 = effects.get(ws.combat.fight, "last_heal")
real_narrate = cs.CombatScene.narrate_round


def narrate_round(self, text):
    assert effects.get(self.fight, "quarry") is not None and effects.get(self.fight, "quarry").target == "e1"      # the round marked it before failing
    raise LLMError("the model failed")                           # inside the round's operation: the round rolls back


cs.CombatScene.narrate_round = narrate_round
stood = ws.turn("I strike at the shrub.")
cs.CombatScene.narrate_round = real_narrate
check("a round that rolls back takes its mark with its row: no quarry, as the committed round left it", stood is False and ws.combat is not None
      and effects.get(ws.combat.fight, "quarry") is None and not any(r["kind"] == "quarry" for r in row()["effects"]),
      (stood, [r.model_dump() for r in ws.combat.fight.effects] if ws.combat else None, row() and row()["effects"]))
stood = ws.turn("I strike at the shrub.")
q = effects.get(ws.combat.fight, "quarry") if ws.combat else None
check("...and the same round taken again marks it, in the row", stood is True and q is not None and q.target == "e1"
      and any(r["kind"] == "quarry" and r["target"] == "e1" for r in row()["effects"]), (stood, q and q.model_dump()))

# ---- the casting context is the fighter's, and never in a saved row mid-cast
check("no fighter in the saved row holds a casting context: it is set as an ability is used and ended with it",
      all(not f.get("casting") for f in row()["fighters"]) and all(not f.casting for f in ws.combat.fight.fighters))
check("the purity fence finds no id() in spellcraft", not any("id()" in p for p in purity.problems("engine/spellcraft.py")), purity.problems("engine/spellcraft.py"))

# ---- the fight's end: the row goes, and nothing of it stays in the process
for f in ws.combat.fight.fighters:
    if f.side == "enemy":
        f.hp = 1
store.save_combat(ws.combat.to_json())
for _ in range(6):
    stood = ws.turn("I strike at the shrub.")
    if ws.combat is None or stood is not True:
        break
owned = [n for n, *_ in session._owned()]
check("the fight won, its row is gone, and the session owns no table of its marks", stood is True and ws.combat is None and store.load_combat() is None
      and not any(x in owned for x in ("combat_perks.QUARRY", "combat_perks.WITHER", "healing.LAST", "spellcraft._CAST")), (stood, ws.combat, owned))

# ---- the cap: a fight with 300 expired rows holds effects_keep
f = combat.Combat(fighters=[], round=9)
for i in range(300):
    effects.put(f, effects.ActiveEffect(id=f"x{i}", kind="test", until=1))
check("a fight with 300 expired rows holds effects_keep (combat.yaml)", len(f.effects) == combat.RULES["effects_keep"] == 64 and f.effects[-1].id == "x299", len(f.effects))
effects.put(f, effects.ActiveEffect(id="live", kind="test", until=0))
for i in range(70):
    effects.put(f, effects.ActiveEffect(id=f"y{i}", kind="test", until=1))
check("...the oldest expired go first: a row that still holds stays", any(r.id == "live" for r in f.effects) and len(f.effects) == 64)

gateway._client = real
game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
