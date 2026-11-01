"""(f447) What the A4000 timing night showed on one walk: two road events, each written three times and thrown away. A hazard had to
name the check that gets the player past it from a list of skills with nothing physical in it, and a crack across the road fits none,
so it never could; a find was refused for "I" inside a note written on the page in single quotes. Now (the owner: "let's have the model
stop naming checks", for road hazards) a hazard is what it is and how hard, and pressing straight on past it is ruled in the moment like
any attempt; a single-quoted line counts as quoted; and the same complaint twice running ends the tries."""
import json, random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 47)
simlib.install(stub)
import ui.console as uc
SHOWN = []
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: SHOWN.append((_fn, str(a[0]) if a else "")))
uc.panel = lambda name, data: False
from pydantic import BaseModel, field_validator, ValidationError
from engine import hygiene, road_prompts
from llm import gateway
from llm.contracts import RoadEvent
from llm.gateway import LLMError
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import campaign_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- a hazard names no way past it
check("a road event has no check to name", "check" not in RoadEvent.model_fields)
ev = RoadEvent.model_validate_json(json.dumps({"title": "The Mud-Slicked Rut", "journey": "The road climbs into the hills.",
                                               "scene": "A fissure has opened across the road.", "kind": "hazard"}),
                                   context={"kind": "hazard", "want_journey": True, "stops": True})
check("...and a hazard stands without one", ev.kind == "hazard")
check("...nor is the writer told of checks", "CHECKS" not in road_prompts.user("r", "normal", "spring", "day", "clear", "", "", "", ["merchant"],
                                                                                 "", True) and "check says" not in road_prompts.SYSTEM)

# ---- pressing on is ruled as it is tried
shutil.rmtree("saves/hazard_ruled_447_test", ignore_errors=True)
store = CampaignStore.open_or_create("hazard_ruled_447_test")
store.meta.seed = 47; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(47))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, campaign_world(), load_traits(), store.load_player())
ws.player.mentor["never"] = True
hz = {"tier": "normal", "what": "A fissure has opened across the road.", "behind": "parth"}
asked = []
real = gateway._client
def chat(**k):
    if k["format"].get("title") == "Ruling":
        asked.append(k["messages"][-1]["content"])
    return real.chat(**k)
gateway._client = types.SimpleNamespace(chat=chat)
stub.ruling = {"sense": "cost", "why": "", "stakes": {"check": "dexterity", "hard": "hard"}}
SHOWN.clear()
ws.get_past(dict(hz), "I keep going")
check("pressing on past a hazard asks for a ruling, as any attempt does", asked and "pressing straight on past" in asked[-1], asked[-1:])
check("...and rolls what the ruling says it takes", any(k == "note" and t.startswith("Dexterity") for k, t in SHOWN), SHOWN)
stub.ruling = {"sense": "no", "why": "", "answer": "There is no crossing it here."}
SHOWN.clear(); m0 = ws.minutes
ws.get_past(dict(hz), "I keep going")
check("a ruling that there is no pushing through sends them the long way round", ws.minutes > m0
      and any("no pushing straight through" in t for _, t in SHOWN), SHOWN)
n = len(asked); SHOWN.clear(); m0 = ws.minutes
ws.get_past(dict(hz), "we go around it by the long way")
check("going around asks for no ruling, and costs time", len(asked) == n and ws.minutes > m0, SHOWN)
store.close()
shutil.rmtree("saves/hazard_ruled_447_test", ignore_errors=True)
gateway._client = real

# ---- a line written in single quotes is quoted
note = "On the page a hand has scrawled: 'I saw it, a light that didn't move, and I'm done walking those paths.' The wind turns it."
check("'I' inside a single-quoted note is quoted, not the narrator", hygiene.problem("narrate", {"text": note})[0] != "first_person")
check("...while the narrator saying 'I' is still sent back", hygiene.problem("narrate", {"text": "I walk on."})[0] == "first_person")
check("...and an apostrophe opens no quote", hygiene.problem("narrate", {"text": "The wolves' den is near; I think it is empty."})[0]
      == "first_person")

# ---- the same complaint twice running ends the tries
class Always(BaseModel):
    text: str
    @field_validator("text")
    @classmethod
    def no(cls, v):
        raise ValueError("this is never right")
class Changing(BaseModel):
    text: str
    @field_validator("text")
    @classmethod
    def no(cls, v):
        raise ValueError(f"not '{v}'")
tries = {"n": 0}
def answer(**k):
    tries["n"] += 1
    return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=json.dumps({"text": f"draft {tries['n']}"})))
gateway._client = types.SimpleNamespace(chat=answer)
def attempts(schema):
    tries["n"] = 0
    try:
        gateway.generate("test_task", "s", "u", schema, retries=2, _quiet=True)
    except LLMError:
        pass
    return tries["n"]
check("told the same thing twice and answered the same way, it stops: no third try", attempts(Always) == 2, tries)
check("...while a draft that changes, and is told something new, gets its tries", attempts(Changing) == 3, tries)
gateway._client = real

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
