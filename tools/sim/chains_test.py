"""(f358) Consequence chains: a situation that ends queues what may come of it at the same place (threads.yaml `then`), its pressure
heats when ignored and cools when settled, and the follow-on starts after its delay with the heat added to its severity."""
import copy, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import pulse, threads
from npc.life import populate_place
from npc.traits import load_traits
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

check("every base template says what follows it, and the data check reads it", threads.problems() == [] and all(threads.T["templates"][k].get("then") for k in threads.T["kind_weights"]), threads.problems()[:3])
world = load_world(); catalog = load_traits()
shutil.rmtree("saves/chains_test", ignore_errors=True)
store = CampaignStore.open_or_create("chains_test"); store.meta.seed = 9; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
populate_place(store, world, "parth", catalog)
start = 5 * 1440
old = copy.deepcopy(pulse.P)
pulse.P["eventful_chance"] = 0.0
pulse.P["engine_roll"]["chance"] = 0.0
pulse.P["engine_roll"]["quiet_hours"] = 10 ** 6
pulse.P["chains"] = {"ignored": 1.0, "settled": 1.0, "delay_days": [1, 1], "heat_max": 3}
pulse.P["tiers"]["normal"]["resolved_by_others"] = 0.0
world.pressures["greywood_predators"].template = "threat"
state = pulse.empty_state(start)
ok = pulse.start_thread(store, world, catalog, state, start, random.Random(1), tier="normal", pressure_id="greywood_predators", made_by="engine")
th = state["threads"][-1]
sev0 = th["severity"]
th["times"] = [start, start + 60]                                   # it ends at the next tick
store.save_world_state(state)
pulse.catch_up(store, world, catalog, start + 8 * 60)
st = store.load_world_state()
th = next(x for x in st["threads"] if x["id"] == th["id"])
q = st.get("queued") or []
check("left to its fallout, the wolves' situation ends ignored and queues what follows at the same place, from the template's `then`",
      th["status"] == "ended" and len(q) == 1 and q[0]["template"] in ("threat_tribute", "threat", "nature") and q[0]["place"] == th["place"] and q[0]["from"] == th["title"], (th["status"], q))
check("...and its pressure heats by one", st.get("pressure_heat", {}).get("greywood_predators") == 1, st.get("pressure_heat"))
pulse.catch_up(store, world, catalog, q[0]["after"] + 1)             # to the tick the follow-on is due, and no further
st = store.load_world_state()
new = [x for x in st["threads"] if x.get("follows")]
check("after its delay the follow-on starts, says what it follows from, and is worse by its shift and the heat",
      len(new) == 1 and new[0]["follows"] == th["title"] and new[0]["template"] == q[0]["template"] and new[0]["severity"] >= min(5, sev0 + q[0]["severity"] + 1) and not st.get("queued"),
      [(x.get("template"), x.get("severity"), x.get("follows")) for x in st["threads"]])
# settled: the heat cools, and an aftermath may follow
th2 = new[0]
th2["times"] = [st["last"], st["last"] + 60]
pulse.P["tiers"][th2["tier"]]["resolved_by_others"] = 1.0
store.save_world_state(st)
pulse.catch_up(store, world, catalog, st["last"] + 8 * 60)
st = store.load_world_state()
check("settled by the town's own people, the heat cools and an aftermath is queued", st["pressure_heat"]["greywood_predators"] == 0 and any(x["from"] == th2["title"] for x in st.get("queued", [])),
      (st.get("pressure_heat"), st.get("queued")))
# the player's own ending follows up as settled
rng = random.Random(4)
state2 = pulse.empty_state(start); state2["pressure_heat"] = {"greywood_predators": 2}
pulse.start_thread(store, world, catalog, state2, start, rng, tier="normal", pressure_id="greywood_predators", made_by="engine")
th3 = state2["threads"][-1]
check("the heat is added to a new situation's severity", th3["severity"] >= 2, th3["severity"])
row = threads.follow_up(state2, th3, "settled", random.Random(1), start)
check("a settled ending (the player's too) cools the heat and may queue an aftermath", state2["pressure_heat"]["greywood_predators"] == 1 and (row is None or row["template"] in ("fortune", "social")), (state2["pressure_heat"], row))
pulse.P.clear(); pulse.P.update(old)
shutil.rmtree("saves/chains_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
