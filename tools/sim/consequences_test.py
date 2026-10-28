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

check("the rules name answering templates, marked so chance never draws them", consequences.problems(threads.T["templates"], ("kill", "offense", "quest_done", "settled")) == []
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

# ---- (f363) a campaign earned by play: two matters settled in the region, and someone with a bigger one comes looking
state = store.load_world_state()
check("the campaign rule is data, with no template of its own", consequences.problems(threads.T["templates"], ("kill", "offense", "quest_done", "settled")) == []
      and any(r.get("tier") == "campaign" for r in consequences.C["rules"]))
later = start + 3 * 1440
state["deeds"].append({"kind": "settled", "minute": later - 1440, "place": "greywood", "thread": "a", "title": "Wolves", "tier": "normal", "how": "by way of a hunt"})
check("one matter settled is not yet renown", not any(r["id"] == "renown_campaign" for r, _ in consequences.met(state, world, "parth", later)))
state["deeds"].append({"kind": "settled", "minute": later - 600, "place": "parth", "thread": "b", "title": "Two doors", "tier": "normal", "how": "by persuasion"})
check("two in the region within six weeks are", any(r["id"] == "renown_campaign" for r, _ in consequences.met(state, world, "parth", later)))
check("...and the deed reads plainly for the judge", deeds.describe(state["deeds"][-1]).startswith("settled 'Two doors' at parth"))
import httpx
from llm import gateway
class Broken:
    def chat(self, **kw):
        raise httpx.TimeoutException("no model")
_client = gateway._client
gateway._client = Broken()
state["campaign"] = ""
ok = consequences.tick(store, world, catalog, state, later, random.Random(3))
check("when the model gives nothing, no campaign starts and the rule waits only a day, not its cooldown",
      not ok and not state.get("campaign") and not any(r["id"] == "renown_campaign" for r, _ in consequences.met(state, world, "parth", later + 600))
      and any(r["id"] == "renown_campaign" for r, _ in consequences.met(state, world, "parth", later + 2 * 1440)), state.get("consequence_last"))
gateway._client = _client
ok = consequences.tick(store, world, catalog, state, later + 2 * 1440, random.Random(3))
th = state["threads"][-1] if state["threads"] else {}
check("with the model answering, a campaign starts near the player, marked as earned, through the door the rule names",
      ok and state.get("campaign") == th.get("id") and th.get("tier") == "campaign" and th.get("earned") and th.get("consequence") == "renown_campaign" and th.get("door") == "summons",
      {k: th.get(k) for k in ("tier", "earned", "consequence", "door", "place")})
check("...and a second cannot start while it runs", not any(r["id"] == "renown_campaign" for r, _ in consequences.met(state, world, "parth", later + 2 * 1440 + 10))
      or not consequences.tick(store, world, catalog, state, later + 2 * 1440 + 10, random.Random(4)) or state["threads"][-1] is th)
shutil.rmtree("saves/consequences_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
