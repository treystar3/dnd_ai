"""(f342) A town's tradespeople are found wherever in town they work. Parth has a smith in its streets and no smithy: 'go to the smithy'
and 'go to the blacksmith' from the square walk the player to her instead of pointing at a smithy three towns away; a talk aimed at
someone who works across town walks there first; the interpreter is offered the townsfolk the words name, met or not. Two plan repairs
from the same tester's run: a move to a place the player names stands even when the talk after it is to someone here, and a piece of
stock the line never named, bought beside the asking for something else, goes."""
import random
import shutil
import sys
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
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

notes = []
_note = console.note
console.note = lambda text, *a, **k: (notes.append(str(text)), _note(text, *a, **k))[1]

shutil.rmtree("saves/town_person_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("town_person_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 3
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")                                   # the streets: the smith lives here
smith = next((n for n in ws.residents if n.role == "smith"), None)
check("Parth's streets have a smith and Parth has no smithy", smith is not None and not any(p.parent == "parth" and p.type == "smithy" for p in world.places.values()), [n.role for n in ws.residents])
ws.enter("trading_square")
check("...who is not in the square", smith and all(n.id != smith.id for n in ws.present))

# ---- 1. 'the smithy', read as a far smithy, walks to the town's own smith
notes.clear()
ws.on_move(ActionIntent(kind="move", destination="kelpmoor_smithy", summary="I prance over to the smithy"), "i prance over to the smithy")
about = any(n.id == smith.id for n in ws.present)
check("a move to a far smithy from the square walks to where Parth's smith works", ws.player.location == "parth", (ws.player.location, notes))
check("...and over to her when she is about, or says she is not about at this hour",
      (about and ws.last_spoken == smith.id) or (not about and any("not about at this hour" in n for n in notes)), (about, ws.last_spoken, notes))
check("...never 'there is no smithy in Parth'", not any("There is no smithy" in n for n in notes), notes)

# ---- 2. 'the blacksmith' as a destination
ws.enter("trading_square"); notes.clear()
ws.on_move(ActionIntent(kind="move", destination="the blacksmith", summary="I go to the blacksmith"), "i go to the blacksmith")
check("a trade word as the destination finds them across town", ws.player.location == "parth" and not any("no such place" in n.lower() for n in notes), (ws.player.location, notes))

# ---- 3. the interpreter is offered the townsfolk the words name, met or not
ws.enter("trading_square")
named = ws.town_people_named("i go to the soot stained smith in the center of town", {n.id for n in ws.present})
check("'the smith' from the square names Parth's smith for the interpreter though they never met", any(r.id == smith.id for r in named), [r.id for r in named])
check("...and a line about bread names nobody across town", not ws.town_people_named("i buy a loaf of bread", {n.id for n in ws.present}))
check("'blacksmith' and 'smithy' both mean the smith", ws.names_person("the blacksmith", smith) and ws.names_person("over to the smithy", smith) and not ws.names_person("a smith", type("R", (), {"role": "baker", "name": "Rufus Yeoman", "epithet": "the flour-dusted baker", "id": "r1"})()))

# ---- 4. a talk aimed at someone who works across town walks there first
ws.enter("trading_square"); notes.clear()
before = stub.calls.get("NPCReply", 0)
ws.on_talk(ActionIntent(kind="talk", target=smith.id, speech="Do you have arrows?", summary="asking the smith for arrows"), "I ask the smith if she has arrows")
walked = ws.player.location == "parth"
check("a talk to the smith from the square walks to the streets", walked, (ws.player.location, notes))
check("...and the talk happens there when she is about, else the world says she is not about",
      (ws.partner is not None and ws.partner.id == smith.id and stub.calls.get("NPCReply", 0) > before) or any("not about at this hour" in n for n in notes), (ws.partner and ws.partner.id, notes))
check("...and nobody is told 'you last saw them'", not any("last saw them" in n for n in notes), notes)

# ---- 5. the repairs
ws.enter("guild_house")
here = ws.present[0]
plan = [ActionIntent(kind="move", destination="trading_square", summary="out to the square"), ActionIntent(kind="talk", target=here.id, speech="do you have arrows for sale?", summary="asking")]
kept = ws.move_to_present("i walk out of the building to the trading square and approach the chandler", list(plan))
check("a move to a place the line names stands, though the talk after it is to someone here", [a.kind for a in kept] == ["move", "talk"], [a.kind for a in kept])
kept = ws.move_to_present("i ask the clerk about arrows", list(plan))
check("...while a move the line never named, before a word with someone here, goes as before", [a.kind for a in kept] == ["talk"], [a.kind for a in kept])
plan = [ActionIntent(kind="talk", target="t1", speech="I approach the tinker and ask to buy arrows", summary="asking"), ActionIntent(kind="buy", target="t1", ware="crude ash shortbow", summary="buying")]
out = ws.buy_what_was_named("i approach the tinker and ask to buy arrows", list(plan))
check("asking to buy arrows does not buy the shortbow the model reached for", out is not None and [a.kind for a in out] == ["talk"], out and [a.kind for a in out])
check("...while the shortbow asked for by name is bought", ws.buy_what_was_named("i ask the tinker for the crude shortbow and buy it", list(plan)) is None)
check("...and a good nobody names ('something to eat') is still bought",
      ws.buy_what_was_named("I ask for something to eat", [plan[0], ActionIntent(kind="buy", target="t1", ware="trail_ration", summary="food")]) is None)
check("...and a lone buy with no asking beside it is left to the shop", ws.buy_what_was_named("i buy arrows", [plan[1]]) is None)

shutil.rmtree("saves/town_person_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
