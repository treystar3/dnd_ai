"""Audiences (f320): the crown is behind a door the chamberlain keeps; the door opens on the town's regard, the nobility's word, or a
summons; the keeper voices the game's decision; behind the door, the monarch is met like anyone else, for a while."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import court, matters, truth, pulse
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/court_test", ignore_errors=True)
world = load_world()
check("the palace keeps the crown behind a door the chamberlain holds", world.places["lethoria_palace"].audience == {"keeper": "chamberlain", "sees": ["monarch"]})
store = CampaignStore.open_or_create("court_test")
store.meta.seed = 9; store.meta.minutes = 2 * 60; store.save_meta()          # mid-morning: the court is up
char, _ = simlib.make_character("warrior", random.Random(4))
char.level = 20
store.save_player(PlayerState(character=char, location="lethoria"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("lethoria")
ws.enter("lethoria_palace")
if not store.load_world_state():
    store.save_world_state(pulse.empty_state(ws.minutes))
narrated = []
ws._narrate_now = lambda event, player_text="": narrated.append(event)

monarch = next(n for n in ws.residents if n.role == "monarch")
keeper = next(n for n in ws.residents if n.role == "chamberlain")
check("without a profile for the capital yet, the monarch is an ordinary resident of the palace", not monarch.anchor and monarch.location == "lethoria_palace")
monarch.anchor = "rules the kingdom from here"; monarch.protected = True; store.save_npc(monarch)      # as the capital's profile will make them
check("the monarch is not met in the hall; the chamberlain is", monarch.id not in {n.id for n in ws.present} and keeper.id in {n.id for n in ws.present})
check("...and the truth layer does not list them either", monarch.id not in truth.scene_of(ws).present_ids())
notes = []
_note = console.note
console.note = lambda t, *a, **k: notes.append(t)
from llm.contracts import ActionIntent
ws.on_talk(ActionIntent(kind="talk", target=monarch.id, speech="your majesty, a word"), "your majesty, a word")
console.note = _note
check("speaking to the crown uninvited gets the door, not the crown", any("keeps the door" in n for n in notes), notes)

# ---- the keeper decides nothing: the game does
ok, why = court.decide(ws, "lethoria_palace")
check("a stranger is refused, and told why in the keeper's terms", not ok and "nobody the city has heard of" in why, why)
lines = court.keeper_lines(ws, keeper, "I ask to see the king")
check("the keeper's prompt says they keep the door and carries the refusal", any("YOU KEEP THE DOOR" in l for l in lines) and any("THE ANSWER IS NO" in l for l in lines), lines)
check("...nothing opened", not court.admitted(ws, "lethoria_palace"))
check("small talk with the keeper asks for nothing", len(court.keeper_lines(ws, keeper, "fine weather for the season")) == 1)
ws.player.reputation["lethoria"] = 30
lines = court.keeper_lines(ws, keeper, "I would like an audience with the queen")
check("once the town knows the player's name, the answer is yes and the door opens", any("THE ANSWER IS YES" in l for l in lines) and court.admitted(ws, "lethoria_palace"), lines)
ws.store.meta.turn += 1
check("...and the crown stands in the scene, for the truth layer too", monarch.id in {n.id for n in ws.present} and monarch.id in truth.scene_of(ws).present_ids())
gl = court.gated_lines(ws, monarch)
check("the monarch's prompt carries the terms of the audience", gl and "AUDIENCE" in gl[0] and "minutes" in gl[0], gl)
ws.player.audiences["lethoria_palace"] = ws.minutes - 1
ws.refresh_present()
check("when the time is up, the door is shut again", monarch.id not in {n.id for n in ws.present})
ws.player.reputation["lethoria"] = -20
ok, why = court.decide(ws, "lethoria_palace")
check("a town that thinks ill of the player says so at the door", not ok and "thinks ill" in why, why)

# ---- the crown sends for the player (door six, through a door)
ws.player.reputation["lethoria"] = 30
for n in ws.residents:
    n.met_player = False; store.save_npc(n)
ws.enter("lethoria")
state = store.load_world_state()
th = {"id": "c1", "title": "The silver-wire shortage", "tier": "uncommon", "place": "lethoria", "pressure": "", "stage": 0, "status": "active",
      "stages": [{"description": "The court's enchanters have no silver wire.", "effects": []}], "fallout": {"description": "", "effects": []},
      "times": [ws.minutes, ws.minutes + 2880], "made": ws.minutes, "groups": ["everyone"], "paths": [], "contract": None,
      "clues": [{"text": "The wire came up the Valley Road and stopped coming three weeks back.", "holder": "", "npc": "", "found": False}],
      "door": "summons", "summons": "pending", "moment": "", "sender": "", "touched": False, "answered": False, "opened": ws.minutes, "hidden": False, "revealed": False, "reveal": "", "truth": ""}
state["threads"].append(th); state["door_log"] = {}; store.save_world_state(state)
narrated.clear()
ws._door_loc = "elsewhere"
ws.halted = False
matters.on_arrival(ws)
th = next(t for t in store.load_world_state()["threads"] if t["id"] == "c1")
check("an anchor behind a door sends a messenger instead of coming", th["summons"] == "met" and th["sender"] == monarch.id
      and any("messenger" in e and "will see them" in e for e in narrated), (th["summons"], th["sender"] == monarch.id, narrated[-1:][0][:100] if narrated else ""))
check("...and the door is open to the player for the day", court.admitted(ws, "lethoria_palace") and ws.player.audiences["lethoria_palace"] - ws.minutes >= 1000)
ws.enter("lethoria_palace")
check("...so the crown is there when they come", monarch.id in {n.id for n in ws.present})
tl = matters.talk_lines(ws, monarch)
check("...with why they were sent for, and that the crown knows them by repute", any("CAME LOOKING" in l for l in tl) and any("never spoken" in l for l in tl), tl)

shutil.rmtree("saves/court_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
