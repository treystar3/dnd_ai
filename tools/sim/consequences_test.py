"""(f359) The player as a cause: runs of deeds in the ledger start a situation at the player's town from an answering shape, through the
door the rule names, with a cooldown; the answering shapes are never drawn by chance."""
import copy, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import consequences, deeds, matters, pulse, threads
from npc.life import populate_place
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

check("the rules name answering templates, marked so chance never draws them", consequences.problems(threads.T["templates"], ("kill", "offense", "quest_done")) == []
      and all("social_hunters" not in threads.shapes(k) and "social_watch" not in threads.shapes(k) for k in threads.T["kind_weights"]), consequences.problems(threads.T["templates"]))
world = load_world(); catalog = load_traits()
shutil.rmtree("saves/consequences_test", ignore_errors=True)
store = CampaignStore.open_or_create("consequences_test"); store.meta.seed = 4; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
populate_place(store, world, "parth", catalog)
start = 5 * 1440
state = pulse.empty_state(start)
for i in range(6):
    state["deeds"].append({"kind": "kill", "minute": start - i * 300, "place": "greywood", "creature": "wolf", "level": 3, "rank": "normal", "spawn": ""})
store.save_world_state(state)
hits = consequences.met(state, world, "parth", start)
check("six wolves killed in the region within a week meets the hunters' rule, with the creature as its word", [h[0]["id"] for h in hits] == ["hunters_want_you"] and hits[0][1] == {"creature": "wolf"}, hits)
ok = consequences.tick(store, world, catalog, state, start, random.Random(1))
th = state["threads"][-1] if state["threads"] else None
check("...and the town answers: a situation from the hunters' shape at Parth, about wolves, through a summons that needs no reputation",
      ok and th and th["template"] == "social_hunters" and th["place"] == "parth" and th["words"].get("creature") == "wolf" and th["door"] == "summons" and th.get("summons_force")
      and th.get("consequence") == "hunters_want_you", th and {k: th.get(k) for k in ("template", "place", "door", "consequence")})
check("the contract it carries hunts the same creature", th and th.get("contract") and th["contract"]["what"] == "wolf", th and th.get("contract"))
check("the same answer does not come twice while the cooldown runs", not consequences.met(state, world, "parth", start + 60))
for i in range(2):
    state["deeds"].append({"kind": "offense", "minute": start - i * 300, "place": "parth", "offense": "theft", "witnesses": ["x"]})
hits = consequences.met(state, world, "parth", start)
check("two offenses seen in the town meet the watch's rule", [h[0]["id"] for h in hits] == ["watch_asking"])
ok = consequences.tick(store, world, catalog, state, start, random.Random(2))
th2 = state["threads"][-1]
check("...and the watch starts asking, by word of mouth", ok and th2["template"] == "social_watch" and th2["door"] == "word" and not th2.get("summons_force"), (th2["template"], th2["door"]))
store.save_world_state(state)
console.narrate = lambda text: None
console.note = lambda text: None
console.ledger = lambda text: None
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.player.mentor["never"] = True
ws.enter("parth")
state = store.load_world_state()
th = next(x for x in state["threads"] if x.get("consequence") == "hunters_want_you")
sent = matters._send_someone(ws, state, th)
check("someone comes to find the stranger about the wolves though the town thinks nothing of them yet", sent and th["summons"] == "met" and th.get("sender"), (sent, th.get("sender")))
from engine import domain_events as de
check("every finished contract is a deed the town may answer, not only a situation's", de.ContractDone(minute=0, quest="q", title="t").ledger_row() is not None)
shutil.rmtree("saves/consequences_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
