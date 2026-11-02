"""(f464) The passage is an operation after the commit: a buy whose telling fails every try keeps its coins and item in the save and the
record and shows a plain line of what stood, filled from the row's facts, never machinery, with no story written for the line; the
passage runs after the action's commit, and a line of several actions is told before the world's pulse; a fight won whose telling and
aftermath fail stays won, with the Victory line and the stand-ins in their place and the fight closed; a death whose goddess line fails is
still a death, told by her own silence; the operations of the line are recorded as what they were."""
import json
import pathlib
import shutil
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
from engine import combat, failures, ledger
from llm import gateway
from scenes import combat_scene as cs
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


g = simlib.campaign("passage_464", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/passage_464/turns.jsonl"
SHOWN = simlib.quiet_console()
real = gateway._client
LOG = []                                        # the order of things: ("call", title), ("commit", kind), ("pulse",)
FAIL = {"titles": set()}


def chat(**k):
    title = k["format"].get("title")
    LOG.append(("call", title))
    if title in FAIL["titles"]:
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
real_commit = store.commit_operation
store.commit_operation = lambda op, *a, **k: (LOG.append(("commit", op.kind)), real_commit(op, *a, **k))[1]
real_pulse = ws.run_pulse
ws.run_pulse = lambda *a, **k: (LOG.append(("pulse",)), real_pulse(*a, **k))[1]


def narrated():
    return [t for k, t in SHOWN if k == "narrate"]


def ops_of_input():
    return [o["kind"] for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps]


# ---- a buy whose telling fails every try
from npc.models import NPC
herb = NPC(id="herb1", name="Tam Reed", people="human", role="herbalist", location="parth", traits=[], trust=50)   # a seller at hand, as the law test does
store.save_npc(herb)
ws.enter("parth")
ws.present, ws.residents = [herb], [herb]
c = ws.player.character
c.coins = 100000
store.save_player(ws.player)
coins0 = c.coins
story0 = store._kv("story")
stub.plan = [{"kind": "buy", "ware": "healing draught", "target": herb.id}]
FAIL["titles"] = {"Narration"}
SHOWN.clear(); LOG.clear()
stood = ws.turn("I buy a healing draught from the herbalist.")
paid = [r for r in ledger.LAST if r["kind"] == "paid"]
check("the buy stands though its telling failed: coins spent and the draught in the pack, in the save", stood is True and store.load_player().character.coins < coins0
      and any(i.good == "healing_draught" for i in store.load_player().character.inventory), (stood, store.load_player().character.coins, coins0))
check("...its row is on the record with the facts a stand-in is filled from", paid and paid[0].get("facts", {}).get("who") == herb.label() and paid[0]["op"] in [o["id"] for o in store.load_operations()["ops"]], paid)
lines = narrated()
check("...the player reads a plain line that it stood, filled from those facts, never machinery",
      any((herb.label() in t or paid[0]["facts"]["amount"] in t) and not failures.MACHINERY.search(t) for t in lines), lines)
check("...the passage was an operation of its own, told by a stand-in, and the line is whole", [o.kind for o in ws.line_untold] == ["passage"] and not ws.line_failed
      and ops_of_input() == ["action:buy", "world", "arrival", "law", "tail"], (ws.line_untold, ws.line_failed, ops_of_input()))
check("...and no story was written for the line", store._kv("story") == story0)
check("the passage ran after the action's commit", LOG.index(("commit", "action:buy")) < LOG.index(("call", "Narration")), LOG)

# ---- the same buy, its telling written: the passage is still an operation of its own, after the commit, and shows at its place
FAIL["titles"] = set()
ws.present, ws.residents = [herb], [herb]                 # a rollback refreshes who is present; the seller is at hand again
SHOWN.clear(); LOG.clear()
stood = ws.turn("I buy a healing draught from the herbalist.")
check("told, the passage is an operation after the action's commit", stood is True and ops_of_input() == ["action:buy", "passage", "world", "arrival", "law", "tail"]
      and LOG.index(("commit", "action:buy")) < LOG.index(("call", "Narration")) < LOG.index(("commit", "passage")), (ops_of_input(), LOG))
texts = [t for k, t in SHOWN]
check("...and the page reads as it did: the purse line, then the passage", any("Paid" in t for t in texts) and any(k == "narrate" for k, t in SHOWN)
      and [k for k, t in SHOWN if "Paid" in t or k == "narrate"][:2] == ["note", "narrate"] or [k for k, t in SHOWN if "Paid" in t or k == "narrate"][:2] == ["ledger", "narrate"], [(k, t[:40]) for k, t in SHOWN][:8])

# ---- a line of several actions is told before the world's pulse
stub.plan = [{"kind": "look"}, {"kind": "wait"}]
SHOWN.clear(); LOG.clear()
stood = ws.turn("I look around, then wait a while.")
check("a line of several actions: its one passage before the pulse, both operations of their own", stood is True
      and ops_of_input() == ["action:look", "action:wait", "passage", "world", "arrival", "law", "tail"] and LOG.index(("call", "Narration")) < LOG.index(("pulse",)), (ops_of_input(), LOG))

# ---- a fight won whose telling and aftermath fail: the win stands, the stand-ins in their place, the fight closed
ws.narrate_with = lambda *a, **k: None
creature = ws.world.bestiary["bandit"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", name="bandit 1")
foe.hp = foe.max_hp = 1
sc = cs.CombatScene.begin(ws, creature, [foe], "It is on you:")
ws.combat = sc
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}      # the player's move each round, decided for the stub
xp0 = store.load_player().character.xp
FAIL["titles"] = {"Narration"}
SHOWN.clear(); LOG.clear()
stood = ws.turn("I attack the bandit")
lines = narrated()
texts = [t for k, t in SHOWN]
check("the fight is won and over, and the win is in the save", stood is True and ws.combat is None and store.load_player().character.xp > xp0, (stood, ws.combat, store.load_player().character.xp, xp0))
check("...the round's telling and the aftermath were operations of their own, told by stand-ins", [o.kind for o in ws.line_untold] == ["round", "aftermath"], [o.kind for o in ws.line_untold])
check("...the Victory line is shown, after the stand-in for the aftermath", any(t.startswith("Victory.") for t in texts)
      and texts.index(next(t for t in texts if t.startswith("Victory."))) > max(i for i, t in enumerate(texts) if t in lines), texts)
check("...and the stand-ins are the fight's, in the narrator's words", any(t in failures.F["round_stood"] for t in lines)
      and any("experience" in t or t in failures.F["victory_stood"] for t in lines) and not any(failures.MACHINERY.search(t) for t in lines), lines)
FAIL["titles"] = set()

# ---- a death whose goddess line fails is still a death, told by her silence
c = ws.player.character
c.health = 1
deaths0, coins0 = c.deaths, c.coins
strong = combat.fighter_from_creature(creature, 40, "elite", "e2", name="bandit captain")
strong.hp = strong.max_hp = 10 ** 6
strong.weapon_damage = 10 ** 4
sc = cs.CombatScene.begin(ws, creature, [strong], "It is on you:")
ws.combat = sc
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e2"}
FAIL["titles"] = {"GoddessLine"}
SHOWN.clear()
for _ in range(6):                                                   # the captain winds up, may miss, then lands: a few rounds
    stood = ws.turn("I attack the bandit captain")
    if ws.combat is None or stood is not True:
        break
c2 = store.load_player().character
lines = narrated()
check("the death stands: counted, the purse lighter, the player awake elsewhere", stood is True and c2.deaths == deaths0 + 1 and c2.coins < coins0 and ws.combat is None, (stood, c2.deaths, c2.coins, coins0))
check("...her words could not be written: her own silence in their place, and the loss told after it", "goddess" in [o.kind for o in ws.line_untold]
      and any(t in failures.F["goddess_silent"] for t in lines) and any(t.startswith("Lost:") for k, t in SHOWN), ([o.kind for o in ws.line_untold], lines[:3]))
FAIL["titles"] = set()

gateway._client = real
g.close()
shutil.rmtree("saves/passage_464", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
