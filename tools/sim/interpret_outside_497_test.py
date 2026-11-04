"""(f497) The fight's reading of the line (combat_interpret) is asked outside the round's transaction: the line's operation stands down
at the call, the model is asked with no operation open, and the operation runs again from its start with the answer served, committing
once under the id its first attempt drew (the ops stream restored). The fight's pane (combat_state) and its text panel (combat_panel)
are held with the story and pushed at the commit, never for an attempt that stood down; held, show() takes the same branch as live
(the window's binding says True), so the terminal prints its panel once and the window gets one push; neither is a line of the page
nor of the record's presentation (load re-shows the pane from the row). A reading that fails every try leaves the fight's row and
the save as they were, no round passed, the line not taken (run() tells the player so in failures.yaml's words); the same line again is
taken. The ratchet of tasks still asked inside an operation holds no combat_interpret. And a give-back with the fence armed reads and
never writes: the present are reloaded as the rows hold them, their doings left to the next operation (found by the fight fixtures)."""
import shutil
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import combat, failures, operation
from llm import gateway
from storage import statehash
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "interpret_outside_497"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="parth")
ws, store = game.scene, game.store
ws.enter("parth")

# ---- a give-back reads and never writes (found by the fight fixtures: every round now gives back once, and a period's turn changes
# every doing; assigning them saved the rows past the fence, and the re-run would have met other doings than its first attempt)
from engine import doings
store.meta.minutes = 1440                                        # an hour the townsfolk are about (none are, this seed, before the evening)
store.save_meta()
ws.refresh_present()                                             # outside any line: their doings assigned and saved, as an arrival's are
ids = [n.id for n in ws.present if n.role not in doings.STILL]
rows0 = {i: store.load_npc(i).activity for i in ids}
store.meta.minutes += 6 * 60                                     # another period of the day: every doing is due to change
store.save_meta()
store.arm(True)
try:
    ws.give_back(None, [], None)
    gave = True
except Exception as e:                                           # noqa: BLE001 - the fence's refusal is the finding
    gave = f"{type(e).__name__}: {e}"
store.arm(False)
unwritten = gave is True and all(store.load_npc(i).activity == rows0[i] for i in ids) and all(n.activity == rows0[n.id] for n in ws.present if n.id in rows0)
ws.refresh_present()                                             # and the next assignment (an operation's) does change them: the give-back had something not to write
check("a give-back with the fence armed reads and never writes: the present are reloaded, their doings as the rows hold them, for the next operation to set",
      unwritten and ids and any(n.activity != rows0.get(n.id) for n in ws.present if n.id in rows0), (gave, len(ids)))
store.meta.minutes = 600
store.save_meta()
ws.enter("south_fields")

LOG, FAIL, BEGUN, PRESENTED, LINES = [], {"titles": set()}, [], [], []
real = gateway._client


def chat(**k):
    title = k["format"].get("title")
    LOG.append((title, operation.current().kind if operation.current() else None))
    if title in FAIL["titles"]:
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
real_begin = operation.begin


def begin(*a, **k):
    op = real_begin(*a, **k)
    BEGUN.append((op.kind, op.id))
    return op


operation.begin = begin
real_presentation = operation.Operation.presentation


def presentation(self):
    out = real_presentation(self)
    PRESENTED.append(out)
    LINES.append(list(self.lines))
    return out


operation.Operation.presentation = presentation
STATE, PANEL = [], []
console.combat_state = lambda data: (STATE.append(data), False)[1]       # the terminal's: no pane, so the text panel follows
console.combat_panel = lambda lines: PANEL.append(lines)

# ---- the fight begins (its own line); then a round, read outside
creature = ws.world.bestiary["awakened_shrub"]                   # fearless (families.yaml plant): it never bolts or yields, so the fight lasts
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "awakened shrub", "near")
foe.hp = foe.max_hp = 600                                        # a weak thing with a long life: never deadly, four rounds are to come
ws.wildlife = (creature, [foe])
stub.plan = [{"kind": "attack", "target": "awakened shrub"}]
ws.turn("I attack the shrub.")
stub.plan = None
check("the fight is on", ws.combat is not None and not ws.combat.fight.over)
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
del LOG[:], BEGUN[:], PRESENTED[:], LINES[:], STATE[:], PANEL[:]
round0 = ws.combat.fight.round
ws.turn("I strike at the shrub.")
reads = [(t, op) for t, op in LOG if t == "CombatIntent"]
check("the round's reading of the line is asked with no operation open", reads and all(op is None for _, op in reads), reads)
lines = [i for k, i in BEGUN if k == "line"]
ops = [o for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps and o["kind"] == "line"]
check("the line's operation ran twice (stood down at the reading, then again with the answer) and committed once, under its first id",
      len(lines) == 2 and lines[0] == lines[1] and len(ops) == 1 and ops[0]["id"] == lines[0], (lines, [o["id"] for o in ops]))
check("...and a round passed", ws.combat is not None and ws.combat.fight.round == round0 + 1, (round0, ws.combat.fight.round if ws.combat else None))
check("the pane was pushed once, at the commit, and the terminal's text panel printed once (none for the attempt that stood down)",
      len(STATE) == 1 and len(PANEL) == 1, (len(STATE), len(PANEL)))
check("...neither is a line of the page", not any("hits" in l or "awakened shrub (lv" in l for ls in LINES for l in ls), LINES[-1][:3] if LINES else LINES)
check("...nor of the record's presentation (load re-shows the pane from the row)",
      PRESENTED and not any(e[0] in ("combat_state", "combat_panel") for p in PRESENTED for e in p), [e[0] for p in PRESENTED for e in p])

# ---- a window: one push, no text panel
console.damage_tags = True
console.combat_state = lambda data: (STATE.append(data), True)[1]
del STATE[:], PANEL[:]
ws.turn("I strike at the shrub.")
check("a window gets one pane push for the round and no text panel", ws.combat is not None and not ws.combat.fight.over and len(STATE) == 1
      and not PANEL, (len(STATE), len(PANEL), ws.combat.fight.over if ws.combat else "over"))
console.damage_tags = False
console.combat_state = lambda data: (STATE.append(data), False)[1]

# ---- a reading that fails every try: nothing moves, the player is told, the same line again is taken
row0, digest0, round0 = store.load_combat(), statehash.digest(store)["all"], ws.combat.fight.round
FAIL["titles"] = {"CombatIntent"}
stood = ws.turn("I strike at the shrub.")
FAIL["titles"] = set()
check("a reading that fails every try leaves the fight's row byte-equal and the save's digest the same, and no round passed",
      store.load_combat() == row0 and statehash.digest(store)["all"] == digest0 and ws.combat is not None and ws.combat.fight.round == round0,
      (store.load_combat() == row0, ws.combat.fight.round if ws.combat else None, round0))
told = ws.failed_line("I strike at the shrub.") if stood is False else None       # what run() shows for a line not taken (world.py run)
check("...the line is not taken, as a model failure (not the game's own fault), and the player is told so in failures.yaml's words",
      stood is False and not ws.last_crash and told in failures.lines(), (stood, ws.last_crash, ws.last_failure, told))
ws.turn("I strike at the shrub.")
check("...the same line typed again is taken: a round passes and a blow is recorded",
      ws.combat is not None and ws.combat.fight.round == round0 + 1 and ws.combat.fight.hits, (ws.combat.fight.round if ws.combat else None, round0))
check("the ratchet holds no combat_interpret: nothing of the fight's reading is asked inside an operation",
      "combat_interpret" not in operation.LEGACY, operation.LEGACY)

operation.begin, operation.Operation.presentation, gateway._client = real_begin, real_presentation, real
game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
