"""(f353) Two things the five-hour run showed about the pulse: the re-telling call failed every time (the model left the stage list out), so
its lists are required and the request ends with the exact shape to fill; and the event budget counted the engine's own situations, which
cost no call, so a long absence started at most two things in the whole world."""
import random, re, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import pulse, threads
from llm.contracts import ThreadTelling
from npc.life import populate_place
from npc.traits import load_traits
from pydantic import ValidationError
from storage.campaign import CampaignStore
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def telling(payload, stages=1, clues=1):
    try:
        ThreadTelling.model_validate(payload, context={"stages": stages, "clues": clues, "known": frozenset()}); return ""
    except ValidationError as e:
        return str(e)
check("a re-telling without its lists is refused by the schema itself, not only by the count", "stages" in telling({"reveal": "x", "resolution": "y"}) and "required" in telling({"reveal": "x"}).lower())
check("...one with the lists, counted right, passes", telling({"stages": ["a"], "clues": ["b"], "fallout": "", "truth": "", "reveal": "", "resolution": ""}) == "")
check("...and the wrong count is still sent back with the instruction", "write exactly 2 stages" in telling({"stages": ["a"], "clues": ["b"]}, stages=2))

world = load_world(); catalog = load_traits()
shutil.rmtree("saves/pulse_budget_test", ignore_errors=True)
store = CampaignStore.open_or_create("pulse_budget_test"); store.meta.seed = 5; store.save_meta()
populate_place(store, world, "parth", catalog)
start = 5 * 1440
store.save_world_state(pulse.empty_state(start))
th = {"id": "t1", "title": "Wolves out of the Greywood", "place": "parth", "tier": "normal", "kind": "threat", "stage": 0, "status": "active",
      "stages": [{"description": "Wolves at the pens.", "effects": []}], "fallout": {"description": "The wolves had their fill.", "effects": []},
      "resolution": "Thin the wolves.", "truth": "Something pushed them out.", "clues": [{"text": "Count the tracks.", "holder": "farmer", "npc": "", "found": False}],
      "reveal": "", "door": "board", "made_by": "engine", "told": False, "words": {"town": "Parth", "wild": "the Greywood"}, "times": [start, start + 1440], "groups": ["everyone"]}
state = store.load_world_state(); state["threads"].append(th)
asked = []
import llm.gateway as gw
real = gw._client
class Spy:
    def chat(self, *a, **k):
        asked.append(k.get("messages") or (a[1] if len(a) > 1 else None))
        return real.chat(*a, **k)
gw._client = Spy()
ok = threads.tell(store, world, state, th, start + 60)
gw._client = real
req = next((m["content"] for m in (asked[-1] or []) if m.get("role") == "user"), "") if asked else ""
check("the request ends with the exact shape to fill: one slot per stage and per clue", '"stages": ["<STAGE 1 re-told>"]' in req and '"clues": ["<CLUE 1 re-told>"]' in req, req[-400:])
check("...and the stand-in re-tells it", ok and th["told"] and th["stages"][0]["description"].startswith("(retold)"))

# the budget
old = dict(pulse.P)
pulse.P["eventful_chance"] = 1.0
pulse.P["kinds"] = {"thread": 1}
state = pulse.empty_state(start); store.save_world_state(state)
pulse.catch_up(store, world, catalog, start + 10 * 1440)          # ten days away in one action
st = store.load_world_state()
mine = [t for t in st["threads"] if t.get("made_by") == "engine"]
check("ten days away: the engine's own situations are not held to the two-call budget", len(mine) > 2 and len(mine) <= pulse.P.get("max_engine_events_per_action", 8), len(mine))
pulse.P.clear(); pulse.P.update(old)
shutil.rmtree("saves/pulse_budget_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
