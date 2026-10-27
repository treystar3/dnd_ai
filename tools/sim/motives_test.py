"""(f360) Known people's lives without a model call: a person the player has met moves their goal a step at a pulse from the table for
the trait it came from; the step is their memory and what is on their mind, gossip for the town, a mood for a while; after steps_most
steps the goal ends as the drift decides, and a new goal starts its steps over."""
import copy, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import drift, motives, pulse
import llm.gateway as gw
from npc.life import populate_place
from npc.traits import load_traits
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

seeds = set(pulse.P["drift"]["motives"]["seeds"])
check("every trait a goal can come from has a table of steps, and the data check reads it", motives.problems(seeds) == [] and motives.M["engine"] is True, motives.problems(seeds))
world = load_world(); catalog = load_traits()
shutil.rmtree("saves/motives_test", ignore_errors=True)
store = CampaignStore.open_or_create("motives_test"); store.meta.seed = 2; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
populate_place(store, world, "parth", catalog)
start = 5 * 1440
state = pulse.empty_state(start)
npc = next(store.load_npc(r.id) for r in store.npc_rows(location="parth") if not r.gone)
npc.tier, npc.traits, npc.motive, npc.met_player = "known", ["ambitious", "calm", "brave"], "to have a say in how Parth is run", True
npc.motive_since = start; npc.concern_from = ""
store.save_npc(npc)
calls = []
real = gw._client
class Spy:
    def chat(self, *a, **k):
        calls.append(1); return real.chat(*a, **k)
gw._client = Spy()
old = copy.deepcopy(pulse.P)
pulse.P["motives"]["step_days"] = 0
ok = pulse.move_motive(store, world, catalog, state, start + 480, random.Random(1))
gw._client = real
n = store.load_npc(npc.id)
check("a step moves without a model call: a first-person memory of it, their concern, a mood, gossip in the news, the step counted",
      ok and not calls and n.memories and n.memories[-1].text.startswith("(my own life) ") and n.concern == n.memories[-1].text[len("(my own life) "):]
      and n.mood and n.motive_step == 1 and state["news"] and n.name in state["news"][-1]["text"], (calls, n.concern, n.mood, n.motive_step, state["news"][-1:]))
check("the step comes from the table for the trait the goal came from", n.memories[-1].text.endswith(motives.M["by_seed"]["ambitious"][0]["line"].format(name=n.name, role=n.role.replace("_", " "), town="Parth", motive="")))
pulse.P["drift"]["motives"]["made_chance"] = 1.0
for i in range(2):
    pulse.move_motive(store, world, catalog, state, start + 480 * (i + 2), random.Random(i + 2))
n = store.load_npc(npc.id)
ps = store.load_place("parth")
check("after steps_most steps the goal ends as the drift decides, the town remembers, and the count starts over",
      n.motive == "" and n.motive_step == 0 and n.motive_done_at > 0 and any(n.name in m["text"] for m in ps.memory), (n.motive, n.motive_step, [m["text"] for m in ps.memory][-2:]))
n.motive_done_at = start; n.motive_step = 2; store.save_npc(n)
state2 = pulse.empty_state(start); state2["drift_cursor"] = 0
pulse.P["drift"]["motives"]["chance"] = 1.0
pulse.P["drift"]["motives"]["cooldown_days"] = 0
drift.people(store, world, state2, start + 2 * 1440, random.Random(3))
n = store.load_npc(npc.id)
check("a new goal from the drift starts its steps over", n.motive and n.motive_step == 0, (n.motive, n.motive_step))
motives.M["engine"] = False
calls.clear(); gw._client = Spy()
pulse.move_motive(store, world, catalog, state, start + 10 * 480, random.Random(9))
gw._client = real
check("with engine off in motives.yaml the step is the model's again", calls, calls)
motives.M["engine"] = True
pulse.P.clear(); pulse.P.update(old)
shutil.rmtree("saves/motives_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
