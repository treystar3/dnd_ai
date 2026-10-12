"""An NPC who promises pay in words gets a real, payable offer; agreeing to the work pays it."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from llm.contracts import ActionIntent
from ui import console

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
shutil.rmtree("saves/work_pay_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("work_pay_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")
c = ws.player.character
npc = ws.present[0]

speech = "If you can move these sacks and help clear the brush by the north fence, I'll give you a fair wage for a day's sweat."
check("a promise of pay for a task is noticed", ws.promises_pay(speech))
check("plain talk is not", not ws.promises_pay("The weather turns cold. Mind the carts.") and not ws.promises_pay("I'll pay you for that herb."))
offer = ws.inferred_offer(npc, speech)
check("an offer is read from the line, falling back to a plain one", bool(offer.task.strip()), offer)
ws.record_work_offer(offer, npc)
check("the offer is stored at an honest wage", npc.work_offer and npc.work_offer["pay"] > 0, npc.work_offer)
before = c.coins
console.note = lambda m: None
ws.on_work(ActionIntent(kind="work", target=npc.id), "I do the work")
check("doing the work pays the wage", c.coins > before and npc.work_offer is None, (before, c.coins))
print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)
