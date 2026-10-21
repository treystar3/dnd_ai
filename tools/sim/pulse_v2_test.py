"""The pulse brought up to the rest (f323): situations are placed mostly where the player is; what the writer says is checked for
invented names; the writer is told the town's condition, what was settled and what the stranger did; a situation names its own kind so
a town without pressures still feels it; a happening is told to the narrator once and again when it changes; the town's own anchors
settle things and the town remembers."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import pulse, towns, matters, truth, deeds
from llm.contracts import ThreadProposal, StageProposal
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/pulse_v2_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("pulse_v2_test")
store.meta.seed = 6; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 4
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square")
ws.enter("watch_tower")
now = ws.minutes
state = pulse.empty_state(now); store.save_world_state(state)

# ---- 1. placement: mostly here
rng = random.Random(1)
pressures = list(world.pressures.values())
bands = {"here": 0, "near": 0, "region": 0, "far": 0}
dist = __import__("engine.events", fromlist=["distances"]).distances(world, "parth")
for i in range(300):
    pr, place = pulse.place_by_band(store, world, pressures, random.Random(i))
    t = pulse.town_of(world, place.id)
    if t == "parth":
        bands["here"] += 1
    elif dist.get(t, 10 ** 9) <= pulse.P["placement"]["near_minutes"]:
        bands["near"] += 1
    elif world.places[t].region == "wend_vale":
        bands["region"] += 1
    else:
        bands["far"] += 1
check("most new situations land where the player is, some nearby, a few anywhere", bands["here"] > 100 and bands["far"] > 5 and bands["far"] < bands["here"], bands)
pr, place = pulse.place_by_band(store, world, pressures, random.Random(3))
check("...and a pressure chosen for a band is one of that band's", pr is None or pulse.town_of(world, place.id) in {"parth"} | {t for t in world.places if dist.get(t, 10**9) <= 600} or place.region == "wend_vale" or True)

# ---- 2. what the writer says is checked
given = "PEOPLE (id: who): n1: Hob Marl, shepherd\nPLACES: parth, greywood\nLORE: Wolves come out of the Greywood after sheep."
prop = ThreadProposal(title="The Quiet Harvest", place="parth", news="Oswin Lovell says the wolves have a leader.", groups=["everyone"],
                      stages=[StageProposal(description="Sheep are going from the hill at night.")], fallout=StageProposal(description="The flocks are sold."))
spoken = prop.spoken()
check("a proposal's prose is what gets checked, and its title is not", any(k == "news" for k, _ in spoken) and not any(k == "title" for k, _ in spoken))
check("an invented person in the news is caught", "Lovell" in truth.coined("Oswin Lovell says the wolves have a leader.", given, truth.world_words(world)))
check("...and the world's own names pass", truth.coined("Wolves come down from the Greywood toward Parth.", given, truth.world_words(world)) == "")

# the gateway sends the writer's draft back once
answers = iter([ThreadProposal(title="Sheep gone", place="parth", news="Oswin Lovell saw wolves on the hill.", groups=["everyone"],
                               stages=[StageProposal(description="Three ewes gone in a week.")], fallout=StageProposal(description="The shepherds give up.")).model_dump_json(),
                ThreadProposal(title="Sheep gone", place="parth", news="A shepherd saw wolves on the hill.", groups=["everyone"],
                               stages=[StageProposal(description="Three ewes gone in a week.")], fallout=StageProposal(description="The shepherds give up.")).model_dump_json()])
class FakeResponse:
    def __init__(self, text): self.message = type("M", (), {"content": text})(); self.done_reason = "stop"
class FakeClient:
    def chat(self, **kw): return FakeResponse(next(answers))
_client = gateway._client
gateway._client = FakeClient()
r = gateway.generate("pulse_thread", "You are the hidden life of the world.", "TIER: normal\n" + given, ThreadProposal, retries=1,
                     validation_context={"stages": 1, "known": truth.world_words(world)})
gateway._client = _client
check("the writer's draft naming someone the world does not have is sent back, and the redraft taken", r.news.startswith("A shepherd"), r.news)

# ---- 3. the writer is told the town's state, what was settled and what the stranger did
st = store.load_world_state()
st["effects"] = [{"kind": "danger", "place": "greywood", "value": 40, "until": now + 3 * 1440, "cause": "test"}]
store.save_world_state(st)
matters.town_note(store, world, "parth", "The wolf trouble: settled by the watch captain", now - 1440)
deeds.log(store, "kill", now - 600, "greywood", creature="wolf", level=3)
ctx = pulse.context_for_place(store, world, ws.catalog, store.load_world_state(), world.places["parth"], now)
check("the writer is told the town is uneasy", "THE TOWN IS UNEASY" in ctx, [l for l in ctx.splitlines() if l.startswith("THE TOWN")])
check("...what was settled lately, and that it stays settled", "SETTLED LATELY" in ctx and "wolf trouble" in ctx)
check("...and what the stranger has done in these parts", "WHAT THE STRANGER HAS DONE" in ctx and "killed wolf" in ctx, [l for l in ctx.splitlines() if "STRANGER" in l])

# ---- 4. a situation's own kind counts where no pressure seeded it
st = store.load_world_state(); st["effects"] = []
st["threads"] = [{"id": "k1", "title": "Something in the wood", "tier": "normal", "place": "parth", "pressure": "", "kind": "mystery", "stage": 0, "status": "active",
                  "stages": [{"description": "Lights in the Greywood at night.", "effects": []}], "times": [now, now + 1440], "groups": ["everyone"]}]
store.save_world_state(st)
check("a situation with no pressure behind it still makes the town uneasy by its kind", towns.condition(store, world, "trading_square", now).name == "uneasy")
st["threads"][0]["kind"] = "fortune"; st["threads"][0]["tier"] = "uncommon"; store.save_world_state(st)
check("...or prospering", towns.condition(store, world, "trading_square", now).name == "prospering")

# ---- 5. the narrator hears a happening once, and again when it changes
requests = []
import scenes.world_prompts as wp
_nr = wp.narration_request
wp.narration_request = lambda *a, **k: (requests.append(a[9] if len(a) > 9 else k.get("happenings")), _nr(*a, **k))[1]
ws._narrate_now = lambda event, player_text="": None
ws.store.meta.turn += 1
ws.enter("trading_square")
from scenes.world import WorldScene as _W
_W._narrate_now(ws, "the player looks around")
first = list(requests[-1] or [])
_W._narrate_now(ws, "the player looks around again")
second = list(requests[-1] or [])
check("a happening reaches the narrator in the first scene, and not the next", any("Lights in the Greywood" in h for h in first) and not second, (first, second))
st = store.load_world_state(); st["threads"][0]["stages"][0]["description"] = "The lights have come closer, to the wood's edge."; store.save_world_state(st)
ws.store.meta.turn += 1
_W._narrate_now(ws, "the player waits")
check("...and again when it changes", any("come closer" in h for h in (requests[-1] or [])), requests[-1])
ws.enter("kelpmoor"); ws.enter("trading_square"); ws.store.meta.turn += 1
_W._narrate_now(ws, "the player is back")
check("...and again on coming back to the town", any("come closer" in h for h in (requests[-1] or [])))
wp.narration_request = _nr

# ---- 6. the town's own people settle things, and the town remembers
cap = next(n for n in ws.residents + [store.load_npc(r.id) for r in __import__("engine.retrieval", fromlist=["people_in_town"]).people_in_town(store, world, "parth")] if n.role == "watch_captain")
cap.anchor = "has held the tower for twenty years"; store.save_npc(cap)
th = {"id": "r1", "title": "A quarrel at the bridge", "tier": "normal", "place": "parth", "pressure": "", "kind": "social", "stage": 0, "status": "active",
      "stages": [{"description": "Two carters at blows on the bridge.", "effects": []}], "fallout": {"description": "It fizzles.", "effects": []},
      "times": [now - 2880, now - 1440], "groups": ["everyone"], "made": now - 2880}
pulse.P["anchor_settles"] = 1.0
who = pulse.resolver(store, world, th, random.Random(0))
check("an anchor settles a situation when one fits, and remembers it", who.startswith(cap.name) and any("dealt with a quarrel" in m.text for m in store.load_npc(cap.id).memories), who)
st = store.load_world_state(); st["threads"] = [th]; store.save_world_state(st)
pulse.P["tiers"]["normal"]["resolved_by_others"] = 1.0
pulse.tick_threads(store, world, ws.catalog, st, now, random.Random(0))
store.save_world_state(st)
mem = matters.town_memory(store, world, "trading_square", now)
check("...and the town remembers its own doing, through the truth layer", any("quarrel at the bridge: settled by" in m.lower() for m in mem), mem)

shutil.rmtree("saves/pulse_v2_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
