"""(f378) Two things from a playthrough at the guild hall. The narrator was told each person's look and doing but not their work, so it
took a spectacled quartermaster weighing a sack for the clerk and wrote the real clerk, known by name, as a second man reading at the
board. And a finished contract was paid out the moment the player walked into the hall; it is handed in by speaking to the clerk (or,
for a personal request, to whoever asked), and the clerk's reply knows it happened."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import llm.gateway as gw, types
CALLS = []
_chat = gw._client.chat
def chat(*a, **k):
    CALLS.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
LEDGER = []
for f in ("narrate", "note", "say", "npc_says", "dialogue"):
    setattr(uc, f, lambda *a, **k: None)
uc.ledger = lambda m, *a, **k: LEDGER.append(str(m))
from engine import quests, truth
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

check("work is named unless how the player knows them says it already", truth.their_work("Berram Wickgate", "guild_clerk") == "the guild clerk"
      and truth.their_work("the guild clerk", "guild_clerk") == "" and truth.their_work("the stern keeper", "quartermaster") == "the quartermaster")

world = load_world()
shutil.rmtree("saves/clerk_test", ignore_errors=True)
store = CampaignStore.open_or_create("clerk_test")
store.meta.seed = 3; store.meta.minutes = 120; store.meta.turn = 1; store.save_meta()          # mid-morning: the clerk is at the desk
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="guild_house", guild_rank="F"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("guild_house")
clerk = ws.clerk_here()
check("the hall has its clerk", clerk is not None)
clerk.name_known_to_player = True
seen = {label: desc for label, desc, _ in ws.people_view()}
check("the narrator is told the clerk's work beside their name", seen.get(clerk.label(), "").startswith("the guild clerk. "), seen.get(clerk.label()))
others = [n for n in ws.present if n.id != clerk.id]
if others:
    o = others[0]
    check("...and everyone else's", truth.their_work(o.label(), o.role) == "" or seen.get(o.label(), "").startswith(truth.their_work(o.label(), o.role)), seen.get(o.label()))
check("a frame's list of others names their work too", ws.seen_as(clerk) == f"{clerk.label()}, the guild clerk")

# ---- a finished contract is handed in by speaking to the clerk
q = quests._quest("hunt", "F", "Hunt 3 wolves in the Greywood", ws.minutes, place="greywood", creature="wolf", count=3)
q["progress"] = 3
ws.player.quests = [q]
check("the contract is finished", quests.done(q, ws.pack))
coins = ws.player.character.coins
stub.plan = [{"kind": "look"}]
ws.turn("I look around the hall")
check("walking in or looking around the hall with the clerk there pays nothing", ws.player.quests and ws.player.character.coins == coins
      and not any(l.startswith("Completed") for l in LEDGER), LEDGER)
other = next((n for n in ws.present if n.id != clerk.id), None)
if other:
    stub.plan = [{"kind": "talk", "target": other.id, "speech": "Busy day?"}]
    ws.turn("Busy day?")
    check("...nor does talking to someone else", ws.player.quests and ws.player.character.coins == coins, LEDGER)
CALLS.clear()
stub.plan = [{"kind": "talk", "target": clerk.id, "speech": "The wolves are dead. I'm here for the pay."}]
ws.turn("I hand in my contract to the clerk")
check("speaking to the clerk hands it in and pays", not ws.player.quests and ws.player.character.coins > coins
      and any("Completed: [F] Hunt 3 wolves" in l for l in LEDGER), (LEDGER, ws.player.quests))
said = next((m for t, m in CALLS if t == "NPCReply"), [])
check("...and the clerk's reply is told it happened", said and "handed in the finished contract 'Hunt 3 wolves in the Greywood'" in said[-1]["content"],
      said[-1]["content"][-500:] if said else CALLS)

# ---- handing it over counts too
q2 = quests._quest("hunt", "F", "Hunt 2 boars", ws.minutes, place="greywood", creature="boar", count=2)
q2["progress"] = 2
ws.player.quests = [q2]
LEDGER.clear()
stub.plan = [{"kind": "give", "target": clerk.id, "item": "the contract slip"}]
ws.turn("I hand the slip to the clerk")
check("handing the work to the clerk hands it in", not ws.player.quests and any("Hunt 2 boars" in l for l in LEDGER), LEDGER)
check("the interpreter is told that handing in work is talk to who pays", "turning in finished work" in __import__("scenes.world_prompts", fromlist=["x"]).INTERPRET_SYSTEM)

store.close()
shutil.rmtree("saves/clerk_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
