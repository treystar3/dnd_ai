"""(f392) What becomes of people, kept: a companion who falls is remembered by every writer and survivor; what the game believes about
where the player is ends when they leave; what is someone's in a save is nobody else's.
Two nights: two companions died and were never spoken of again (the party row was deleted as they fell); a delve left set after walking
out silenced every companion for half a run and refused 'move out' 46 times; a party held back at a camp never fell in again; two hires
owed the same widow her revenge, word for word."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import llm.gateway as gw
SENT = []
_chat = gw._client.chat
def chat(*a, **k):
    SENT.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
NOTES = []
for f in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import entities, party, quirks, truth
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/lifecycle_test", ignore_errors=True)
store = CampaignStore.open_or_create("lifecycle_test")
store.meta.seed = 3; store.meta.minutes = 600; store.meta.turn = 1; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="trading_square", guild_rank="E"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("trading_square")
offers = party.roster(3, "guild_house", 0, 5, 100, [])[:3]
ws.player.party = [party.new_hire(o, 5, 0) for o in offers]
ws.player.party_mode = "with"
gone = ws.player.party[0]

# ---- a companion who falls is kept, and remembered
ws.party_service.kill(gone, "fight", in_fight=True)
e = store.load_entity(f"hire:{gone['id']}")
check("a companion who dies leaves the party, but the registry keeps who they were and how they fell",
      gone not in ws.player.party and e is not None and e.state == "dead" and e.pronoun == gone["pronoun"] and e.data.get("place_name"), e)
who = entities.identity(ws, f"hire:{gone['id']}")
check("...so who they were is still known, by the one identity every writer reads", who is not None and who.name == gone["name"]
      and who.pronoun == gone["pronoun"], who)
fallen = truth.scene_of(ws).view(truth.NARRATOR, "narrator").lines("fallen")
check("the narrator is told of the fallen, never to be seen alive again", any(gone["name"] in l and "died today" in l for l in fallen), fallen)
SENT.clear()
ws.narrate("The player looks around the square.", "I look around.")
narr = [m for t, m in SENT if t == "Narration"]
check("...in the narrator's own request", narr and truth.T["headers"]["fallen"] in narr[-1][-1]["content"] and gone["name"] in narr[-1][-1]["content"],
      narr[-1][-1]["content"][-700:] if narr else "no call")
hire_view = truth.scene_of(ws).view(truth.viewer_for_hire(f"hire:{ws.player.party[0]['id']}"), "hire").text()
check("...and so are the survivors, when they speak", gone["name"] in hire_view, hire_view[-500:])
ws.player.party_last_fight = {"minute": ws.minutes, "won": True, "fallen": [gone["name"], "Ilse Varr"], "fallen_ids": [gone["id"], "x"]}
kind, hook, _ = ws.banter_hook(ws.player.party, "fight", random.Random(1))
check("talk after a fight with two dead speaks of both, not the first alone", kind == "fallen" and gone["name"] in hook and "Ilse Varr" in hook, hook)

# ---- what the game believes about where the player is ends when they leave it
ws.ensure_dungeons()
d = store.load_dungeons()[0]
ws.player.location = d["entrance"]
ws.player.delve = {"dungeon": d["id"], "floor": 0, "chamber": 0, "rest": False}
ws.enter("trading_square")
check("walking out of a dungeon ends the delve", ws.player.delve is None)
ws.party_hold("", "Wait here.", [])
check("the party holds back here", ws.player.party_mode == "hold" and ws.player.party_hold_at == "trading_square")
NOTES.clear()
dest = next(p for p in world.places if p != "trading_square" and world.places[p].type in ("town", "city", "village"))
ws.enter(dest)
check("...and falls in again when the player leaves, told", ws.player.party_mode == "with" and any("falls in beside you" in n for n in NOTES), NOTES)

# ---- what is someone's in a save is nobody else's
owned = {}
targets, habits = [], []
for i in range(5):
    m = {"id": f"t{i}", "name": f"Hire {i}", "motive": "revenge"}
    quirks.roll(m, random.Random(7), owned)            # the same seed each time: only ownership keeps them apart
    targets.append(m["quirks"].get("target")); habits.append(m["quirks"]["habit"])
E = quirks.Q["errands"]["revenge"]["targets"]
check("an errand's target is one person's in a save: five hires with the same seed and motive owe five different people",
      len(set(targets)) == min(5, len(E)), targets)
check("...and no two share a habit", len(set(habits)) == 5, habits)
check("...and what is owned is kept, the dead's with it", set(targets) <= set(owned["target"]) and set(habits) <= set(owned["habit"]))

store.close()
shutil.rmtree("saves/lifecycle_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
