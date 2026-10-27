"""(f353) Two things the five-hour run showed about the pulse: the re-telling call failed every time (the model left the stage list out), so
its lists are required and the request ends with the exact shape to fill; and the event budget counted the engine's own situations, which
cost no call, so a long absence started at most two things in the whole world. (f354) The engine's own roll keeps a situation or two
within reach of the player. (f355) The world log is saved, the player's meetings with it are marked, and tools/world_report.py reads it."""
import random, re, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
import config
LOGP = "/tmp/claude-0/-home-user-dnd-ai/8b9b3e33-6d8e-58d7-85b0-03b5c8fa35c4/scratchpad/pulse_test.jsonl"
import os
if os.path.exists(LOGP): os.remove(LOGP)
config.PULSE_LOG_PATH = LOGP
from engine import pulse, pulselog, threads
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

# ---- (f354) the engine's own roll: within reach of the player (who must exist, and be somewhere)
import copy
from storage.campaign import PlayerState
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
old = copy.deepcopy(pulse.P)
pulse.P["eventful_chance"] = 0.0                                  # the model-priced roll off: only the engine's own
pulse.P["engine_roll"] = {"chance": 1.0, "bands": {"here": 55, "near": 45}, "quiet_hours": 24, "most_live": 2}
state = pulse.empty_state(start); store.save_world_state(state)
pulse.catch_up(store, world, catalog, start + 5 * 1440)
st = store.load_world_state()
live = pulse.within_reach(store, world, st, start + 5 * 1440)
check("with the engine's roll every tick, live situations within reach of the player sit at the cap, never above", 1 <= len(live) <= 2, (len(live), [t["place"] for t in st["threads"]]))
reach_ids = {x["id"] for x in live}
check("...and every one it started is within reach (the here and near bands)", all(t["id"] in reach_ids or t["status"] != "active" for t in st["threads"])
      and sum(1 for t in st["threads"] if t.get("made_by") == "engine") >= 2, [(t["place"], t["status"]) for t in st["threads"]])
pulse.P["engine_roll"]["chance"] = 0.0                            # no roll at all: only the quiet-day floor
state = pulse.empty_state(start); store.save_world_state(state)
pulse.catch_up(store, world, catalog, start + 2 * 1440 + 60)
st = store.load_world_state()
check("with no roll, a quiet day within reach still starts one (the floor), and only one", len(pulse.within_reach(store, world, st, start + 2 * 1440 + 60)) == 1, len(st["threads"]))
pulse.P.clear(); pulse.P.update(old)

# ---- (f355) the world log
rows = [__import__("json").loads(l) for l in open(LOGP, encoding="utf-8")]
kinds = {r["kind"] for r in rows}
check("every pulse event is a saved row with its kind and its place", "thread" in kinds and all("t" in r and "kind" in r for r in rows) and any(r.get("tier") and r.get("town") and "reach" in r for r in rows if r["kind"] == "thread"), sorted(kinds))
pulselog.mark("stay", "Rain starts.", start + 10, place="parth")
rows = [__import__("json").loads(l) for l in open(LOGP, encoding="utf-8")]
check("what the player meets is marked and saved too", rows[-1]["kind"] == "stay" and rows[-1]["place"] == "parth")
sys.path.insert(0, "tools")
import world_report
text = world_report.summarise(LOGP)
check("the world report reads it per game day: the totals, the table, the situations", text.startswith("## The world") and "| Day |" in text and "situations started" in text and "Situations started:" in text, text[:300])
check("...and says nothing for an empty log", world_report.summarise(LOGP + ".missing") == "")
shutil.rmtree("saves/pulse_budget_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
