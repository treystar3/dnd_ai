"""(f362) Trust that moves: the engine moves a townsperson's trust from what happened in a conversation (the first talk of a day, how they
chose to answer, the model's say within its limit), up to a cap that talk alone cannot pass; deeds move it through the reactions bus."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 1); simlib.install(stub)
from engine import clock, trust
from llm.contracts import ActionIntent
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the rule, on its own
check("the rules are sound", trust.problems({"small_talk", "share", "withhold", "lie", "bargain", "help", "refuse", "threaten", "leave"}) == [], trust.problems())
R = lambda intent="small_talk", change=0: types.SimpleNamespace(intent=intent, trust_change=change)
n = types.SimpleNamespace(trust=50, last_talk_day=-1)
check("the first talk of a day moves trust one step", trust.after_talk(n, R(), 3) == 1 and n.trust == 51 and n.last_talk_day == 3)
check("a second talk the same day does not", trust.after_talk(n, R(), 3) == 0 and n.trust == 51)
check("the next day does", trust.after_talk(n, R(), 4) == 1 and n.trust == 52)
check("helping or sharing is a step toward the player; refusing a step away; a threat three", trust.after_talk(n, R("help"), 4) == 1 and trust.after_talk(n, R("refuse"), 4) == -1
      and trust.after_talk(n, R("threaten"), 4) == -3 and n.trust == 49)
n.trust = 60
check("talk alone takes trust no further than the cap", trust.after_talk(n, R(), 5) == 0 and n.trust == 60)
check("...but a deed's worth of help still does, and the model's own say counts within its limit", trust.after_talk(n, R("help", 9), 6) == 6 and n.trust == 66)
n.trust = 1
check("nothing goes below nothing", trust.after_talk(n, R("threaten"), 7) == -1 and n.trust == 0)

# ---- in a scene, through a conversation
shutil.rmtree("saves/trust_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("trust_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
console.npc_says = lambda *a, **k: None; console.dialogue = lambda *a, **k: None; console.note = lambda *a, **k: None; console.narrate = lambda t: None
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.player.mentor["never"] = True
ws.enter("parth")
who = ws.present[0]
before = who.trust
stub.plan = [{"kind": "talk", "target": who.id, "speech": "What do you make?"}]
ws.turn("I ask what they make")
after1 = store.load_npc(who.id).trust
check("the first conversation of the day moves their trust one step, with the model saying nothing", after1 == before + 1, (before, after1))
ws.turn("I ask what they make")
check("...and the second that day moves nothing", store.load_npc(who.id).trust == after1)
store.meta.minutes += 1440
ws.turn("I ask what they make")
check("the next day moves it again", store.load_npc(who.id).trust == after1 + 1, store.load_npc(who.id).trust)
stub.a_NPCReply = lambda u, k: {"speech": "No. Be off.", "intent": "refuse"}
t0 = store.load_npc(who.id).trust
ws.turn("I ask what they make")
check("a refusal is a step away", store.load_npc(who.id).trust == t0 - 1, (t0, store.load_npc(who.id).trust))
stub.a_NPCReply = None
shutil.rmtree("saves/trust_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
