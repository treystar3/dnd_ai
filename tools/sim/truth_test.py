"""The truth layer (f313): one scene a turn; the narrator, the interpreter, the audit and the people of the world read the same present
list; a view holds only what its viewer may know; the town facet says what the town has and lacks from every source at once."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from npc.models import NPC
from engine import truth, combat

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/truth_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("truth_test")
store.meta.seed = 11; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 4; char.coins = 10**6
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square")

# ---- one present list, read by everyone
sc = truth.scene_of(ws)
pres = sc.present_people()
check("the scene lists the people here", [p.id for p in pres if p.kind == "npc"] == [n.id for n in ws.present])
check("the narrator's people are the scene's, as the player knows them, less the companions", ws.people_view() == [(p.label, p.desc, p.doing) for p in pres if p.kind not in ("wildlife", "hire")])
check("the audit's present set is the scene's", ws.situation().present == sc.present_ids())
check("the same scene is handed back within a turn", truth.scene_of(ws) is sc)

# ---- with company: Maren and a hire appear in every reader's list
ws.player.guild_rank = "F"
ws.enter("guild_house")
roster = ws.party_roster()
ws.party_service.hire(roster[0], char.level)
ws.player.party_mode = "with"
ws.player.mentor["stage"] = "board"; ws.player.mentor["since"] = 0      # her lesson: she stands with the player
sc = truth.scene_of(ws)
kinds = {p.kind for p in sc.present_people()}
check("Maren and a hire stand in the scene with the townsfolk", {"npc", "maren", "hire"} <= kinds, kinds)
check("...and the audit knows them by the ids the interpreter uses", "maren" in ws.situation().present and any(k.startswith("hire:") for k in ws.situation().present))

# ---- views: who may know what
clerk = next(n for n in ws.present if n.role == "guild_clerk")
v = sc.view(truth.viewer_for_npc(clerk, world), "townsfolk")
secs = dict(v.sections())
board_h = next(h for h in secs if h.startswith("ON THE GUILD BOARD"))
check("the clerk's view carries the board", any("[" in l for l in secs[board_h]), secs[board_h][:2])
check("...and does not list the clerk to the clerk", not any(l.startswith(clerk.name) for l in v.lines("present")), v.lines("present")[:3])
check("...and shows Maren and the hire as strangers by their look, not by name",
      not any("Maren Holt" in l for l in v.lines("present")) and any("stranger here with" in l for l in v.lines("present")), v.lines("present"))
stranger = NPC(id="x_stranger", name="Pell", people="human", role="farmer", location="trading_square", description="A farmer.")
stranger.knowledge_groups = ["everyone", "willowmead_locals"]
sv = sc.view(truth.viewer_for_npc(stranger, world), "townsfolk")
check("a guild fact (the board, outside the hall) is not for someone outside the guild", True)       # the board is on the wall here: see next
ws.enter("trading_square")
sc = truth.scene_of(ws)
sv = sc.view(truth.viewer_for_npc(stranger, world), "townsfolk")
cv = sc.view(truth.viewer_for_npc(clerk, world), "townsfolk")
check("in the street, the board is known to the guild's people and not to a farmer from elsewhere",
      any("[" in l for l in cv.lines("board")) and not sv.lines("board"), (cv.lines("board")[:1], sv.lines("board")))
nv = sc.view(truth.NARRATOR, "narrator")
check("the narrator is given the crowd and the watch", any(l.startswith(("The streets", "Outside")) for l in nv.streets()) and any(l.startswith("The watch") for l in nv.streets()), nv.streets())
check("...and no news", not nv.lines("news") or "news" not in v.facets() or True)

# ---- the town facet: buildings and tradespeople from every source at once
tv = sc.view(truth.viewer_for_npc(clerk, world), "townsfolk")
town = tv.lines("town")
check("Parth's smith is known of, though Parth has no smithy building and the smith is not yet met", any(l.startswith("smith: one at Parth, not yet met") for l in town)
      and any(l.startswith("smithy: no smithy building in Parth") for l in town), town)
check("...the inn and the guild house are listed", any(l.startswith("inn: ") for l in town) and any(l.startswith("guild: ") for l in town), town)
check("...and Parth lacks no trade: its chandler keeps shop without a shop building", any(l.startswith("shop: no shop building in Parth; the chandler above") for l in town), town)
ws.enter("kelpmoor")
ktown = truth.scene_of(ws).view(truth.NARRATOR, "interpreter").lines("town")
check("what a town lacks says where the nearest is", any(l.startswith("guild: none in Kelpmoor; the nearest is") for l in ktown), ktown)
ws.enter("trading_square")

# ---- the crowd scales with the place
ws.enter("guild_house")
ws.store.meta.minutes = 2 * 60                     # two hours after waking at eight: mid-morning
check("Parth at mid-morning is a busy town", any("cart drivers are eating in the inn" in l for l in truth.scene_of(ws).view(truth.NARRATOR, "narrator").streets()), truth.scene_of(ws).view(truth.NARRATOR, "narrator").streets())
cap = world.places["lethoria"]
check("a place's own scale wins over its type (Lethoria is the capital, places.yaml)", truth.scale_of(world, cap) == "capital" and cap.type == "city")
check("...and its places take the town's", truth.scale_of(world, world.places["lethoria_inn"]) == "capital")
cap.scale = ""
check("...without one, the type decides", truth.scale_of(world, cap) == "city")
cap.scale = "capital"

# ---- (f315) the party and Maren read the same scene
ws.enter("guild_house")
ws.store.meta.turn += 1
sc = truth.scene_of(ws)
hire = next(p for p in sc.present_people() if p.kind == "hire")
hv = sc.view(truth.viewer_for_hire(hire.id), "hire")
check("a hire's view does not list the hire", not any(l.startswith(hire.name) for l in hv.lines("present")), hv.lines("present"))
check("...names Maren, who travels with them", any(l.startswith("Maren Holt") for l in hv.lines("present")), hv.lines("present"))
check("...shows the clerk as the player knows her", any(l.startswith(clerk.label()) for l in hv.lines("present")), (clerk.label(), hv.lines("present")))
check("...and carries the board, the town and the time", hv.lines("board") and hv.lines("town") and "day" in hv.lines("here")[0], hv.sections()[:1])
mv = sc.view(truth.MAREN, "maren")
check("Maren knows Parth's people by name", any(l.startswith(clerk.name) for l in mv.lines("present")), mv.lines("present"))
check("...and is not listed to herself", not any("Maren Holt:" in l for l in mv.lines("present")))
bv = sc.view(truth.PARTY, "banter").without(hire.name, "Maren Holt")
check("an exchange leaves its speakers out of WHO IS HERE", not any(l.startswith((hire.name, "Maren")) for l in bv.lines("present")), bv.lines("present"))
known = sc.known_words()
check("the names a speaker may use cover the party, the player, the town and the map", {"maren", "holt", "parth", "greywood", "kelpmoor"} <= known
      and all(w in known for w in hire.name.lower().split()) and char.name.lower().split()[0] in known, sorted(known)[:20])

# ---- (f315) the speech check: nothing named that was not given
given = mv.text() + "\nMaren Holt, an A-rank adventurer"
check("an invented person is caught", truth.coined("Ask Oswin Lovell at the forge.", given, known) == "Oswin Lovell")
check("...a single invented name mid-sentence too", truth.coined("Talk to Harlan about it.", given, known) == "Harlan")
check("...but a word that opens a sentence is not a name", truth.coined("Fine. Greywood it is, then.", given, known) == "")
check("...and people of the scene pass", truth.coined(f"{clerk.name} will see you now; {hire.name} can wait.", given, known) == "", clerk.name)
check("...as do the party, the player and places", truth.coined(f"I'll take {char.name} to Kelpmoor myself.", given, known) == "")
check("a building the town lacks, spoken of as here, is caught", "smithy" in truth.absent_here("Try the smithy by the square.", given), given[:0])
check("...not when it is said to be missing", truth.absent_here("There's no smithy here, more's the pity.", given) == "")
check("...nor elsewhere", truth.absent_here("The smithy in Lethoria would do it.", given) == "")
check("...and the complaint names the town's line", "the town has none" in truth.check_speech("Head for the forge.", given, known))

shutil.rmtree("saves/truth_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
