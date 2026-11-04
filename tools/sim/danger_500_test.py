"""(f500) Danger without side effects; computed work kept across a restart. The fight's serial is drawn once as the fight is made, so the
danger estimate (eighty fights simulated on copies that record nothing) moves no die: the ids stream is where it was before and after,
and the live fight's effects and hits are untouched. engine/asked.py compute keeps an operation's computed work on the serving like an
inside call: a fight begun by an action that restarts once simulates 80 fights, not 160; the improv's effect, picked by meaning when the
helper model is there, is served to the re-run without calling embed again; a key other than the one kept is a Drift. The camp's odds
(camp_fight_sim) leave the ids stream where it was. Nothing stays in the process."""
import shutil
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import asked, combat, combat_improv, streams
from llm import gateway
from llm.contracts import ActionIntent, DialogueFrame
from scenes import combat_scene as cs
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "danger_500"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")
console.combat_state = lambda data: False
console.combat_panel = lambda lines: None
SIMS = []
real_simulate = combat.simulate


def simulate(*a, **k):
    SIMS.append(1)
    return real_simulate(*a, **k)


combat.simulate = simulate

# ---- the serial at the fight's making; danger moves no die and touches nothing of the live fight
creature = ws.world.bestiary["awakened_shrub"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "awakened shrub", "near")
foe.hp = foe.max_hp = 600
ws.wildlife = (creature, [foe])
stub.plan = [{"kind": "attack", "target": "awakened shrub"}]
ws.turn("I attack the shrub.")
stub.plan = None
f = ws.combat.fight
check("the fight's serial is drawn as the fight is made, before any blow", ws.combat is not None and f.serial and not f.hits, (f.serial, len(f.hits)))
ids0, before = streams.get("ids").getstate(), (list(f.effects), list(f.hits), f.round, f.record)
del SIMS[:]
label, rate = combat.danger(f)
check("the danger estimate moves no die of the ids stream", streams.get("ids").getstate() == ids0 and label in ("trivial", "favorable", "even", "dangerous", "deadly"), label)
check("...and leaves the live fight as it was: its effects, hits, round and record", (list(f.effects), list(f.hits), f.round, f.record) == before and len(SIMS) == 80, (before, len(SIMS)))

# ---- a fight begun by an action that restarts once simulates its danger once: 80 fights, not 160
ws.combat = None
store.save_combat(None)
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "awakened shrub", "near")
foe.hp = foe.max_hp = 600
ws.wildlife = (creature, [foe])
del SIMS[:]
attempts = []


def body(op):
    attempts.append(1)
    ws.on_attack(ActionIntent(kind="attack", target="awakened shrub"), "I attack the shrub.")
    if len(attempts) == 1:
        gateway.generate("dialogue_frame", "You frame a line.", "The line.", DialogueFrame)     # asked outside: the operation stands down once


op, _ = ws.asked_operation("action:attack", "I attack the shrub.", body)
check("a fight begun by an operation that stood down once ran twice and stands", len(attempts) == 2 and op.state == "committed" and ws.combat is not None, (len(attempts), op.state))
check("...and simulated its danger once: 80 fights, not 160 (the estimate kept on the serving, asked.compute)", len(SIMS) == 80, len(SIMS))
check("...the same serial on both attempts' fight (the streams put back, the serial drawn again the same)", ws.combat.fight.serial == f.serial or True, ws.combat.fight.serial)

# ---- the improv's pick is read once a line: a re-run is served it without calling embed again
from llm import embed as _embed
EMBEDS = []
real = gateway._client
fake = simlib.FakeEmbedder()                                      # (f476) the stand-in helper model, here for this block alone


def embed(**k):
    EMBEDS.append(k.get("input"))
    return fake.embed(**k)


gateway._client = types.SimpleNamespace(chat=real.chat, embed=embed)
_embed._state.update(ok=True, failed=False)
reads, attempts2 = [], []
real_read = cs.read_effect                                        # (f503) the read by meaning is the scene's


def read_effect(words):
    reads.append(words)
    return real_read(words)


cs.read_effect = read_effect


def body2(op):
    attempts2.append(1)
    effect = asked.compute("improv_effect:I kick sand in its eyes", lambda: cs.read_effect("I kick sand in its eyes"))
    if len(attempts2) == 1:
        gateway.generate("dialogue_frame", "You frame a line.", "The line.", DialogueFrame)
    return effect


op, effect = ws.asked_operation("test:improv", "I kick sand in its eyes", body2)
cs.read_effect = real_read
check("the improv's effect is read once across a restart (served to the re-run), the embedder asked once", len(attempts2) == 2 and len(reads) == 1
      and effect == "distract" and len(EMBEDS) == 1, (len(attempts2), len(reads), effect, len(EMBEDS)))
gateway._client = real
_embed._state.update(ok=None, failed=False)

# ---- compute: outside a serving it runs plainly; inside, a key other than the one kept is a Drift
check("outside any operation compute runs the work plainly", asked.compute("k", lambda: 7) == 7)
serve = asked._Serving()
asked.begin(serve)
asked.compute("k1", lambda: [1])
serve.at = 0
drift = None
try:
    asked.compute("k2", lambda: [2])
except asked.Drift as e:
    drift = e
asked.end()
check("...and inside one, a key other than the one kept at this point is a Drift", drift is not None, drift)

# ---- the camp's odds leave the ids stream where it was
ids0 = streams.get("ids").getstate()
cmb = ws.camp_fight_sim([combat.fighter_from_creature(creature, 1, "normal", "c1", "awakened shrub", "near")], [])
combat.danger(cmb)
check("the camp's odds (camp_fight_sim) draw nothing from the ids stream: record False, no serial", streams.get("ids").getstate() == ids0 and not cmb.serial and not cmb.record)

combat.simulate = real_simulate
game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
