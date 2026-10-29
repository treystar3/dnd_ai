"""(f381) From a playthrough at the Tidepool Caves: a search turned up sahuagin signs leading "toward the dry chamber's threshold", and
"go to the dry chamber's threshold" was read as setting out to find somewhere off the map - hours gone, the model asked three times to
invent a place the caves already hold, and nothing found. A spot inside where the player is (named by the place's own description or the
passage they just read) is a short walk; fresh signs can be followed, and following them hunts that creature with better odds. And
"search for silverleaf" was a hunt for tracks: looking for a plant is foraging for it."""
import random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import llm.gateway as gw
CALLS = []
_chat = gw._client.chat
def chat(*a, **k):
    CALLS.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
for f in ("narrate", "note", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f, lambda *a, **k: None)
from engine import encounters
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/within_place_test", ignore_errors=True)
store = CampaignStore.open_or_create("within_place_test")
store.meta.seed = 5; store.meta.minutes = 720; store.meta.turn = 1; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 10
store.save_player(PlayerState(character=char, location="tidepool_caves", guild_rank="E"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("tidepool_caves")
roster = encounters.ensure_roster(store, world, "tidepool_caves")
quarry = world.bestiary[roster[0]]

TRIED = []
def no_encounter(chance, how, seek=""):
    TRIED.append((round(chance, 2), seek))
    return False
ws.maybe_encounter = no_encounter
def narrated():
    return [m[-1]["content"] for t, m in CALLS if t == "Narration"]

# ---- the search that found signs
stub.plan = [{"kind": "search", "seek": quarry.name}]
ws.turn(f"look for {quarry.name}")
check("a search that finds no creature leaves its signs to follow", (ws.fresh_trail() or {}).get("creature") == quarry.id, ws.__dict__.get("_trail"))
first_chance = TRIED[-1][0] if TRIED else None
ws.recent_narration.append(f"Three claw gouges tear the mud, each furrow pulling toward the dry chamber's threshold.")

# ---- going where they led
CALLS.clear(); TRIED.clear()
before = ws.minutes
stub.plan = [{"kind": "move", "destination": "dry chamber's threshold"}]
ws.turn("go to the dry chamber's threshold")
check("going where the signs led follows them: a hunt for that creature, not a search for somewhere new",
      TRIED and TRIED[-1][1] == quarry.name and not any(t == "DiscoveryProposal" for t, _ in CALLS), (TRIED, [t for t, _ in CALLS]))
check("...with better odds than the search that found them", TRIED and first_chance is not None and TRIED[-1][0] > first_chance, (first_chance, TRIED))
check("...and it takes a search's time, not an expedition's", ws.minutes - before < 60, ws.minutes - before)
CALLS.clear(); TRIED.clear()
stub.plan = [{"kind": "search", "seek": "the tracks"}]
ws.turn("I follow the tracks")
check("'follow the tracks' hunts what made them", TRIED and TRIED[-1][1] == quarry.name, TRIED)

# ---- a spot inside the caves, with no trail
ws._trail = None
CALLS.clear(); TRIED.clear()
before = ws.minutes
stub.plan = [{"kind": "move", "destination": "the dry chamber"}]
ws.turn("I walk over to the dry chamber")
asked = narrated()
check("a spot the place's own description names is a short walk inside it", ws.minutes - before <= 10
      and not any(t == "DiscoveryProposal" for t, _ in CALLS) and asked and "within the Tidepool Caves" in asked[-1],
      (ws.minutes - before, [t for t, _ in CALLS]))
check("...and nobody is hunted for it", not TRIED, TRIED)

# ---- somewhere nothing here names is still exploring
before = ws.minutes
stub.plan = [{"kind": "move", "destination": "a hidden grotto"}]
ws.turn("I go looking for a hidden grotto beyond the caves")
check("somewhere neither the place nor the last passage names is still set out for, hours and all", ws.minutes - before >= 120,
      ws.minutes - before)

# ---- a plant is foraged for
FORAGED = []
real_forage = ws.on_forage
def forage(intent, text):
    FORAGED.append(intent.seek)
    real_forage(intent, text)
ws.on_forage = forage
CALLS.clear(); TRIED.clear()
stub.plan = [{"kind": "search", "seek": "silverleaf"}]
ws.turn("i search for silverleaf")
asked = narrated()
check("'search for silverleaf' forages for it", FORAGED == ["silverleaf"] and not any(s == "silverleaf" for _, s in TRIED), (FORAGED, TRIED))
check("...and where it does not grow, says so", asked and "does not grow in this kind of country" in asked[-1], asked[-1:] if asked else CALLS)
ws.enter("greywood")
ws.maybe_encounter = no_encounter
got = 0
for i in range(8):
    stub.plan = [{"kind": "search", "seek": "silverleaf"}]
    ws.turn("i search for silverleaf")
got = sum(i.quantity for i in ws.player.character.inventory if "silverleaf" in (getattr(i, "name", "") or "").lower()) if hasattr(ws.player.character, "inventory") else 0
check("in the Greywood, where it grows, searching for it turns some up", got > 0 or any("silverleaf" in str(x).lower() for x in ws.pack), (got, ws.pack[:5] if hasattr(ws, "pack") else None))

# ---- the place no longer promises a hermit who lives nowhere
check("the Tidepool Caves promise no one who is not there", not any("hermit" in v.lower() for v in world.places["tidepool_caves"].visible))

store.close()
shutil.rmtree("saves/within_place_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
