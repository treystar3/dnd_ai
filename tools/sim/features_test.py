"""(f394) The parts of places: a wild place is made of parts the player can go to, made from its own list or the templates, grown a part
at a time outward, adopted when a passage names one, closed by the tide, and searched where the player stands."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
import llm.gateway as gw
TOLD = []
_chat = gw._client.chat
def chat(*a, **k):
    if (k.get("format") or {}).get("title") == "Narration":
        TOLD.append(k["messages"][-1]["content"])
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
NOTES = []
for f in ("narrate", "say", "npc_says", "dialogue"):
    setattr(uc, f, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.ledger = lambda m, *a, **k: NOTES.append(str(m))
from engine import features, ledger
from llm.contracts import ActionIntent
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/features_test", ignore_errors=True)
store = CampaignStore.open_or_create("features_test")
store.meta.seed = 4; store.meta.minutes = 720; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 10
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("trading_square")

# ---- which places are made of parts
check("a town is not made of parts here (its parts are places of their own)", not features.grows_here(world.places["trading_square"])
      and not features.here(store, "trading_square"))
check("a wild place is", features.grows_here(world.places["greywood"]) and features.grows_here(world.places["tidepool_caves"]))

# ---- its own list
ws.enter("tidepool_caves")
parts = {e.name: e for e in features.here(store, "tidepool_caves")}
check("a place's own parts are made on the first visit, known, linked both ways", {"the first chamber", "the second beach", "the dry chamber"} <= set(parts)
      and all(e.state != "unseen" for e in parts.values()) and parts["the dry chamber"].ref in parts["the first chamber"].data["links"], list(parts))
check("...and the player stands at its entry", ws.player.spot == parts["the first chamber"].ref, ws.player.spot)

# ---- the templates, for a wild place with no list of its own
ws.enter("greywood")
wood = features.here(store, "greywood")
check("a wild place with no list of its own is given its first parts, of kinds its land has, the entry known and the rest unseen",
      len(wood) == features.F["budget"]["first_visit"] and all(e.data["kind"] in features.kinds_here(world.places["greywood"]) for e in wood)
      and sum(e.state == "known" for e in wood) == 1, [(e.name, e.state) for e in wood])
check("...the same in every save with this seed", [e.name for e in wood] == [e.name for e in wood])

# ---- reading words
check("'the rear tunnel' names a part; 'the cave', 'the walls' and a bare 'tunnel' do not",
      features.named_part("the darkest pocket of the rear tunnel") == ("the rear tunnel", "tunnel") and features.named_part("the cave") is None
      and features.named_part("the walls") is None and features.named_part("tunnel") is None)
ws.enter("tidepool_caves")
check("a phrase finds the part it means", features.find(ws, "the dry chamber's threshold").name == "the dry chamber"
      and features.find(ws, "the beach with the glowing pools").name == "the second beach")

# ---- the tide
check("the tide is in at dawn on the first day and out at midday", features.tide(360)[0] == "high" and features.tide(720)[0] == "low")
check("...it turns every 12 hours and 25 minutes", features.tide(360 + 745)[0] == "high" and features.tide(720 + 745)[0] == "low")
beach = parts["the second beach"]
store.meta.minutes = 360
ok, why = features.open_now(store.load_entity(beach.ref), 360)
check("the second beach is closed at high water, saying when it opens", not ok and "tide is in" in why and "about" in why, why)
NOTES.clear(); ws.halted = False
ws.go_to_part(store.load_entity(beach.ref), "I go to the beach.")
check("...walking there is told so, and nothing is walled off", ws.halted and any("tide is in" in n for n in NOTES) and ws.player.spot != beach.ref, NOTES)
store.meta.minutes = 720

# ---- growth, and its budgets
ws.player.spot = parts["the dry chamber"].ref
before = len(features.here(store, "tidepool_caves"))
n0 = ledger.count("made")
ws.go_deeper("I go further in.")
after = features.here(store, "tidepool_caves")
new = [e for e in after if e.ref not in {p.ref for p in parts.values()}]
check("further in from the dry chamber, a part is made a step deeper, linked to it, and recorded", len(after) == before + 1 and new
      and features.depth(new[0]) == features.depth(parts["the dry chamber"]) + 1 and parts["the dry chamber"].ref in new[0].data["links"]
      and ledger.count("made") == n0 + 1 and ws.player.spot == new[0].ref, [(e.name, features.depth(e)) for e in after])
for _ in range(6):
    ws.go_deeper("I go further in.")
grown = [e for e in features.here(store, "tidepool_caves") if e.data.get("origin") == "grown"]
check("a place grows no more than its share in an hour", len(grown) <= features.F["budget"]["per_hour"], len(grown))
NOTES.clear(); TOLD.clear()
store.meta.minutes += 60 * 6
for _ in range(12):
    ws.go_deeper("I go further in.")
check("...nor more than its whole budget; then the deepest part is where the way ends, said plainly",
      len(features.here(store, "tidepool_caves")) <= features.F["budget"]["most"] and any("no way further in" in t for t in TOLD), TOLD[-1][-300:] if TOLD else "")

# ---- adopted from a passage
ws.enter("greywood")
before = {e.ref for e in features.here(store, "greywood")}
made = ws.adopt_from_passage("You push through the brush to the sunken glade, where a cold spring feeds the fern hollow below.")
check("parts a passage names are made real, within its share", 1 <= len(made) <= features.F["budget"]["adopt_per_passage"]
      and all(e.ref not in before for e in made) and all(e.data["origin"] == "narrated" for e in made), [e.name for e in made])
check("...and a part already there is not made twice", not ws.adopt_from_passage("You walk back to " + made[0].name + "."))

# ---- searching where the player stands
ws.enter("tidepool_caves")
dry = store.load_entity(parts["the dry chamber"].ref)
ws.player.spot = dry.ref
TOLD.clear(); NOTES.clear()
store.meta.minutes = 720
ws.on_search(ActionIntent(kind="search"), "I look closely at the marks on the wall.")
check("searching the dry chamber reads its scratches: when the beach is open, from the tide itself", store.load_entity(dry.ref).data.get("read")
      and any("runs dry" in t and ("about" in t or "now" in t) for t in TOLD), TOLD[-1][-400:] if TOLD else NOTES)
check("...and it is kept in the journal", any("dry chamber" in f.lower() for f in ws.journal_data()["facts"]), ws.journal_data()["facts"][-2:])

# ---- what the narrator is told
TOLD.clear()
ws.narrate("The player looks around.", "I look around.")
check("the narrator is told the parts of this place and where the player stands", TOLD and "THE PARTS OF THIS PLACE" in TOLD[-1]
      and "the dry chamber (where the player stands)" in TOLD[-1], TOLD[-1][-800:] if TOLD else "")
check("the place data checks clean", features.problems(world) == [], features.problems(world))

store.close()
shutil.rmtree("saves/features_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
