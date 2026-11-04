"""(f502) The naming of a win's finds is an operation after the win commits. Every drop is committed under the engine's own name; the
naming operation (kind naming, its tasks asked outside it) gives the rare and better pieces the model's names, the taken-names list and
the turn's record follow the name the item bears, and the Found lines are the naming's own, shown at its commit, before the aftermath;
the aftermath's THE PLAYER FINDS names the final names. The pack holds both finds before the naming runs (the game dead right after the
win's commit, then reopened). A naming whose call fails every try leaves the engine's name and the item kept, its Found line showing
that name. The ratchet holds none of the five naming tasks. Nothing stays in the process."""
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
from core.interrupts import Interrupt
from engine import combat, ledger, loot, operation
from scenes import combat_scene as cs
from llm import gateway
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "naming_502"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")
console.combat_state = lambda data: (SHOWN.append(("pane", "")), False)[1]
console.combat_panel = lambda lines: None
console.legendary_reveal = lambda item: SHOWN.append(("reveal", item.name))
LOG, FAIL, REQ = [], {"titles": set()}, []
real = gateway._client


def chat(**k):
    title = k["format"].get("title")
    op = operation.current()
    LOG.append((title, op.kind if op else None))
    if title == "Narration":
        REQ.append(k["messages"][1]["content"])
    if title in FAIL["titles"]:
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
real_commit = store.commit_operation
store.commit_operation = lambda op, *a, **k: (SHOWN.append(("commit", op.kind)), real_commit(op, *a, **k))[1]
real_drops = loot.boss_drops


def boss_drops(enemy, rng, companions=False):
    """(the design's patch) a rare and a legendary: the boss's two prizes."""
    return 50, [loot.make_drop(enemy.level, "rare", rng, companions), loot.make_drop(enemy.level, "legendary", rng, companions)]


loot.boss_drops = boss_drops


def ops_of_input():
    return [o["kind"] for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps]


def start_fight():
    creature = ws.world.bestiary["awakened_shrub"]                   # fearless: it never yields, so the fight ends when it falls
    foe = combat.fighter_from_creature(creature, 1, "boss", "e1", "awakened shrub", "near")     # a boss's prizes: two pieces, named
    foe.hp = foe.max_hp = 1
    ws.wildlife = (creature, [foe])
    stub.plan = [{"kind": "attack", "target": "awakened shrub"}]
    ws.turn("I attack the shrub.")
    stub.plan = None
    store.save_combat(ws.combat.to_json())
    stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}


def win():
    for _ in range(6):
        stood = ws.turn("I strike at the shrub.")
        if ws.combat is None or stood is not True:
            return stood
    return stood


# ---- the win: the finds committed, named after, the names followed everywhere
start_fight()
del SHOWN[:], LOG[:], REQ[:]
pack0 = {i.uid: i.name for i in ws.pack}
stood = win()
kinds = ops_of_input()
new = [i for i in ws.pack if i.uid not in pack0]
rare = next((i for i in new if i.rarity == "rare"), None)
legend = next((i for i in new if i.rarity == "legendary"), None)
check("the win's input: the round commits, its telling, then the naming as an operation of its own, then the aftermath, then the tail",
      stood is True and ws.combat is None and kinds == ["line", "round", "naming", "aftermath", "tail"], (stood, kinds))
check("...a rare and a legendary are in the pack, the model's names on them (not the engine's), the legendary's title too",
      rare is not None and legend is not None and not rare.name.startswith("Rare ") and legend.title and "of awakened shrub" not in legend.title
      and legend.name in store.legendary_names(), (rare and rare.name, legend and (legend.name, legend.title), store.legendary_names()))
legends = [i for i in new if i.rarity == "legendary"]
check("...the taken-names list holds the legendaries' names (the pack's), not the engine's", legends and sorted(store.legendary_names()) == sorted(i.name for i in legends)
      and not any(t.startswith("the ") and "of awakened shrub" in t for i in legends for t in [i.title]), (store.legendary_names(), [(i.name, i.title) for i in legends]))
named = [(t, o) for t, o in LOG if t in ("LootName", "LegendaryName")]
check("...the naming calls were made with no operation open", len(named) == 2 and all(o is None for t, o in named), named)
order = [(k, t[:40]) for k, t in SHOWN if k in ("commit", "ledger", "narrate", "reveal")]
i_naming = next((i for i, (k, t) in enumerate(SHOWN) if k == "commit" and t == "naming"), None)
i_found = next((i for i, (k, t) in enumerate(SHOWN) if k == "ledger" and t.startswith("Found:")), None)
i_reveal = next((i for i, (k, t) in enumerate(SHOWN) if k == "reveal"), None)
i_after = next((i for i, (k, t) in enumerate(SHOWN) if k == "commit" and t == "aftermath"), None)
i_victory = next((i for i, (k, t) in enumerate(SHOWN) if k == "ledger" and t.startswith("Victory.")), None)
check("...the page: the finds (the Found line and the legendary's reveal) after the naming's commit and before the aftermath, Victory after it",
      None not in (i_naming, i_found, i_reveal, i_after, i_victory) and i_naming < i_found < i_after and i_naming < i_reveal < i_after and i_after < i_victory, order)
found_line = next((t for k, t in SHOWN if k == "ledger" and t.startswith("Found:")), "")
check("...the Found line bears the model's name", rare is not None and rare.name in found_line, found_line)
told = next((r for r in REQ if "THE PLAYER FINDS" in r), "")
check("...and the aftermath's THE PLAYER FINDS names the final names", told and rare.name in told and legend.name in told
      and "Rare " not in told.split("THE PLAYER FINDS:")[1].split("\n")[0], told.split("THE PLAYER FINDS:")[1].split("\n")[0] if told else told)
gained = [r for r in ledger.LAST if r.get("kind") == "gained"]
check("...the turn's record (the ledger the narrator and the turn log read) names them as the pack does",
      gained and all(any(i.name in (r.get("say") or "") for i in new) for r in gained), [r.get("say") for r in gained])

# ---- the game dead right after the win's commit: the pack holds both finds under the engine's names; reopened, they stay so
start_fight()
real_victory = cs.CombatScene.victory


def victory(self):                                               # the crash armed from inside the win: the winning line's commit, and nothing after
    self.ws.crash_after_commit = "line"
    return real_victory(self)


cs.CombatScene.victory = victory
pack0 = {i.uid for i in ws.pack}
del SHOWN[:], LOG[:]
try:
    win()
    stopped = False
except Interrupt:
    stopped = True
cs.CombatScene.victory = real_victory
check("the game stopped right after the win's commit, before the naming ran", stopped and not any(t in ("LootName", "LegendaryName") for t, o in LOG), (stopped, LOG))
game.close()
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields", fresh=False)
ws, store = game.scene, game.store
ws.enter(ws.player.location)
new = [i for i in ws.pack if i.uid not in pack0]
check("...reopened, the pack holds both finds under the engine's own names, the legendary's name in the taken list",
      len(new) >= 2 and any(i.name.startswith("Rare ") for i in new) and any(i.rarity == "legendary" and i.title.startswith("the ") and "of awakened shrub" in i.title for i in new)
      and all(i.name in store.legendary_names() for i in new if i.rarity == "legendary"), [(i.rarity, i.name, i.title) for i in new])
console.combat_state = lambda data: (SHOWN.append(("pane", "")), False)[1]
console.combat_panel = lambda lines: None
console.legendary_reveal = lambda item: SHOWN.append(("reveal", item.name))
store.commit_operation = lambda op, *a, **k: (SHOWN.append(("commit", op.kind)), store.__class__.commit_operation(store, op, *a, **k))[1]

# ---- a naming whose call fails every try leaves the engine's name and the item kept, its Found line showing that name
start_fight()
FAIL["titles"] = {"LootName", "LegendaryName"}
pack0 = {i.uid for i in ws.pack}
del SHOWN[:], LOG[:]
stood = win()
FAIL["titles"] = set()
new = [i for i in ws.pack if i.uid not in pack0]
rare = next((i for i in new if i.rarity == "rare"), None)
found_line = next((t for k, t in SHOWN if k == "ledger" and t.startswith("Found:")), "")
check("a naming whose call fails every try leaves the engine's name, the item kept, the Found line showing that name, the win standing",
      stood is True and rare is not None and rare.name.startswith("Rare ") and rare.name in found_line and "naming" in ops_of_input(), (stood, rare and rare.name, found_line, ops_of_input()))

check("the ratchet holds none of the five naming tasks", not ({"loot_name", "legendary_name", "accessory_name", "named_spell", "spell_rank"} & set(operation.LEGACY)), operation.LEGACY)

loot.boss_drops = real_drops
gateway._client = real
game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
