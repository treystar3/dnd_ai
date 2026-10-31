"""(f421) Improvisation and rulings, as the f395 night showed them. A plain yes that changed nothing was told to show 'what is different
now', and the narrator made a change up; a place part became 'the a secluded nook'; the ruling was taught that a character with no torch
simply lights one; word of recall did not grant teleport, nor revivify raising the dead; a check named where a capability goes sent the
whole ruling back; and a no's answer was held to 'one or two sentences' (the owner: no length limits)."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 11))
import ui.console as uc
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import checks, ruling, world_improv
from llm.contracts import Ruling
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/rulings_421_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("rulings_421_test")
store.meta.seed = 11; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("mage", random.Random(11))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("parth")

# ---- a yes that changes nothing says so
told = []
ws.narrate = lambda event, text="", *a, **k: told.append(event)
world_improv.resolve(ws, "hums a tune", "I hum a tune", {"sense": "yes", "why": "anyone can"})
check("a plain yes that changes nothing is told that nothing lasting is different", told and "Nothing lasting is different" in told[-1]
      and "what is different now" not in told[-1], told[-1:])

# ---- names, the yes taught, the capabilities
check("a part's name takes 'the' once, whatever article it came with", ruling.the_name("a secluded nook") == "the secluded nook"
      and ruling.the_name("The high ledge") == "the high ledge" and ruling.the_name("an old well") == "the old well")
check("the ruling is not taught that lighting a torch one lacks is a plain yes", "light a torch" not in ruling.SYSTEM)
recall = next(iter(ws.player.character.actives), None)
if recall is not None:
    was = recall.field_use
    recall.field_use = "word_of_recall"
    check("word of recall grants teleport", "teleport" in ruling.means_of(ws))
    recall.field_use = "revivify"
    check("...and revivify raising the dead", "raise_dead" in ruling.means_of(ws))
    recall.field_use = was
else:
    check("word of recall grants teleport (an ability to try it on)", False)

# ---- the ruling's contract
ctx = {"capabilities": list(ruling.C), "checks": sorted(checks.CHECKS) + list(ruling.ATTRS)}          # as engine/ruling.ask gives it
r = Ruling.model_validate({"sense": "cost", "requires": ["stealth"]}, context=ctx)
check("a check named where a capability goes is moved to the check, not sent back", r.stakes.check == "stealth" and r.requires == [], r)
try:
    Ruling.model_validate({"sense": "cost", "requires": ["dragonform"]}, context=ctx)
    check("...while a name that is neither is still sent back", False)
except Exception as e:
    check("...while a name that is neither is still sent back", "CAPABILITIES" in str(e), str(e))
try:
    Ruling.model_validate({"sense": "no"}, context=ctx)
    check("a no still needs its answer", False)
except Exception as e:
    check("a no still needs its answer, with no length set on it", "answer" in str(e) and "sentence" not in str(e), str(e))
check("...nor in what the ruling is asked", "one or two sentences of the world" not in ruling.SYSTEM)

store.close()
shutil.rmtree("saves/rulings_421_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
