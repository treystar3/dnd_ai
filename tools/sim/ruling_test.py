"""(f395) The dungeon master's ruling (engine/ruling.py): the model rules on sense, and the engine refuses a yes on its four grounds only:
means, consistency, kind and budget. Also the grounded listening repairs (scenes/listening.py), the fork read from the line itself, and
offers of work that lapse."""
import random, shutil, subprocess, sys, types
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
import config
import ui.console as uc
NOTES = []
for f in ("narrate", "say", "npc_says", "dialogue"):
    setattr(uc, f, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.ledger = lambda m, *a, **k: NOTES.append(str(m))
config.REFUSALS_LOG = False
from engine import exits, features, ledger, refusals, ruling
from llm.contracts import ActionIntent, Ruling
from npc.traits import load_traits
from scenes.listening import said
from scenes.work_actions import offer_open
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def rule(**k):
    return Ruling.model_validate({"answer": "", **k}, context={"capabilities": list(ruling.C), "becomes": list(features.F["becomes"])})

world = load_world()
shutil.rmtree("saves/ruling_test", ignore_errors=True)
store = CampaignStore.open_or_create("ruling_test")
store.meta.seed = 4; store.meta.minutes = 720; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 10
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("tidepool_caves")

# ---- the test set, offline: every case that carries the model's ruling is judged by the engine as a good dungeon master would
out = subprocess.run([sys.executable, "tools/ruling_eval.py"], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
check("the ruling test set: the engine's own grounds are right on every case it can judge offline", out.returncode == 0 and " right" in out.stdout,
      out.stdout[-800:] + out.stderr[-800:])

# ---- means
c = ws.player.character
c.capabilities = []
check("a warrior with nothing that grants it cannot fly", "flight" not in ruling.means_of(ws))
c.capabilities = ["flight"]
check("...something that grants flight (the story, an item) is a means", "flight" in ruling.means_of(ws))
c.capabilities = []
old_people = c.people
c.people = "dwarf"
check("a dwarf sees in the dark", "darkvision" in ruling.means_of(ws))
c.people = old_people
v = ruling.verdict(ws, rule(sense="yes", why="", requires=["flight"]))
check("a yes that needs flight the character lacks is a no, in the world's words", not v["ok"] and v["answer"] == ruling.C["flight"]["lacking"], v)
c.capabilities = ["flight"]
check("...and stands with the means", ruling.verdict(ws, rule(sense="yes", why="", requires=["flight"]))["ok"])
c.capabilities = []
check("the model's no stands, whatever the character can do", not ruling.verdict(ws, rule(sense="no", why="impossible", answer="Nothing happens."))["ok"])
try:
    rule(sense="yes", requires=["wings_of_gold"])
    sent_back = False
except ValueError:
    sent_back = True
check("a capability not in the list is sent back to the model, not trusted", sent_back)

# ---- kind and budget: a part is made to a template and within the place's share
ledger.begin()
r = rule(sense="cost", why="a cave goes on", needs=[{"kind": "feature", "name": "the high ledge", "what": "a shelf of rock above the pools",
                                                     "where": "above"}], stakes={"check": "athletics", "hard": "fair"})
check("a yes for a part this place does not hold yet stands", ruling.verdict(ws, r)["ok"])
made = ruling.make_room(ws, r)
ledge = features.find(ws, "the high ledge")
check("...the part is made real, kept, with what the ruling said it is, and recorded", ledge is not None and ledge.data.get("what") == "a shelf of rock above the pools"
      and made and ledger.count("made") >= 1, (made, ledge))
check("...and asking again makes nothing twice", ruling.make_room(ws, r) == [] or features.find(ws, "the high ledge").ref == ledge.ref)
room = features.room
features.room = lambda ws_, pid: False
v = ruling.verdict(ws, rule(sense="yes", needs=[{"kind": "feature", "name": "the sunken vault", "what": "a vault"}]))
check("when the place holds all it can, a new part is refused plainly", not v["ok"] and "nowhere it could be" in v["answer"], v)
features.room = room
ledge.state = "gone"; store.save_entity(ledge)
v = ruling.verdict(ws, rule(sense="yes", needs=[{"kind": "feature", "name": "the high ledge", "what": "a ledge"}]))
check("consistency: a part that is gone cannot be called back", not v["ok"] and "gone" in v["answer"], v)

# ---- people: made by the engine, counted per place and day; the dead stay dead
hermit = rule(sense="yes", needs=[{"kind": "person", "name": "the hermit", "what": "an old recluse of the dry chamber", "role": "hermit"}])
check("someone the attempt calls for may appear", ruling.verdict(ws, hermit)["ok"])
made = ruling.make_room(ws, hermit)
h = next((n for n in ws.present if n.role == "hermit"), None)
check("...a real person of this place: named by the engine, kept, present, a resident, and recorded", h is not None and h.name and store.npc_exists(h.id)
      and h.id in store.load_place("tidepool_caves").residents and "the hermit" in h.label() and made, (made, [n.label() for n in ws.present]))
check("...of the role the ruling named, described in its words", h is not None and h.role == "hermit" and "recluse" in h.description)
wanderer = ruling.appear(ws, Ruling.model_validate({"answer": "", "sense": "yes", "needs": [{"kind": "person", "name": "a stranger", "what": "a traveller"}]},
                                                   context={"capabilities": []}).needs[0])
check("a person with no role that fits is a wanderer", wanderer.role == "wanderer", wanderer.role)
check("two have appeared here today", ruling.appeared_today(ws) == 2)
v = ruling.verdict(ws, hermit)
check("...and a third is refused: a place does not fill with whoever is called for", not v["ok"] and v["answer"] == "Nobody comes.", v)
store.meta.minutes += 24 * 60
check("...the next day the count starts again", ruling.appeared_today(ws) == 0)
h.gone = "dead"; store.save_npc(h)
v = ruling.verdict(ws, rule(sense="yes", needs=[{"kind": "person", "name": h.name, "what": "the hermit again"}]))
check("consistency: a person who is gone does not come back when called", not v["ok"] and "gone from the world" in v["answer"], v)

# ---- saying no: nothing made, nothing broken, a moment spent, logged as a refusal
NOTED = []
_note = refusals.note
refusals.note = lambda kind, *a, **k: NOTED.append(kind)
stub.ruling = {"sense": "yes", "why": "they want to", "needs": [{"kind": "feature", "name": "the sky road", "what": "a road in the air"}], "requires": ["flight"]}
before_parts = len(features.here(store, "tidepool_caves"))
before_min = ws.minutes
m0, r0 = ledger.count("made"), ledger.count("refused")
ledger.begin(); TOLD.clear()
ruling.run(ws, "grows wings and flies away", "I grow wings and fly away.")
check("a refusal makes nothing", len(features.here(store, "tidepool_caves")) == before_parts and ledger.count("made") == m0, ledger.this_turn())
check("...spends a moment, and is recorded as refused on the turn and in the refusals log", ws.minutes == before_min + 1 and ledger.count("refused") == r0 + 1
      and NOTED == ["refused"], (ws.minutes - before_min, NOTED))
check("...and is told as the world, with what it does not do", TOLD and "does not happen" in TOLD[-1] and ruling.C["flight"]["lacking"] in TOLD[-1], TOLD[-1][-500:] if TOLD else "")
refusals.note = _note

# ---- a plain yes is done without a roll; a cost is rolled on the ruling's check
stub.ruling = {"sense": "yes", "why": "anyone can", "needs": [], "requires": []}
TOLD.clear()
ruling.run(ws, "lights a torch", "I light a torch.")
check("a plain yes simply happens", TOLD and "WORKS" in TOLD[-1], TOLD[-1][-400:] if TOLD else "")
ruled = {"sense": "cost", "check": "athletics", "hard": "easy"}
easy = ruling.odds(ws, "climb", ruled)
hard = ruling.odds(ws, "climb", {**ruled, "hard": "hard"})
check("how hard the ruling says it is moves the odds", easy > hard, (easy, hard))
check("an attribute is a check too", 0 < ruling.odds(ws, "climb", {"sense": "cost", "check": "strength", "hard": "fair"}) <= 100)
stub.ruling = None

check("the capabilities check clean", ruling.problems() == [], ruling.problems())

# ---- a part made different: kept on the part, told, and the way shut while it lasts
ws.enter("tidepool_caves")
dry = features.find(ws, "the dry chamber")
stub.ruling = {"sense": "yes", "why": "driftwood is to hand", "needs": [], "requires": [], "changes": [{"part": "the dry chamber", "becomes": "blocked"}]}
TOLD.clear(); NOTES.clear()
ruling.run(ws, "wedges driftwood across the way into the dry chamber", "I wedge driftwood across the way into the dry chamber.")
dry = features.find(ws, "the dry chamber")
check("blocking a way works and is kept on the part", "blocked" in features.now_of(dry, ws.minutes) and TOLD and "blocked" in TOLD[-1], (dry.data.get("now"), TOLD[-1][-300:] if TOLD else ""))
check("...the way there is shut, saying when it should be passable", not features.open_now(dry, ws.minutes)[0] and "passable again" in features.open_now(dry, ws.minutes)[1])
ws.halted = False
ws.go_to_part(dry, "I go to the dry chamber.")
check("...walking there is told so", ws.halted and any("blocked" in n for n in NOTES) and ws.player.spot != dry.ref, NOTES)
check("...and in a day it has worked loose", features.open_now(dry, ws.minutes + 25 * 60)[0])
stub.ruling = {"sense": "yes", "why": "", "needs": [], "requires": [], "changes": [{"part": "the dry chamber", "becomes": "cleared"}]}
ruling.run(ws, "pulls the driftwood away", "I pull the driftwood away.")
check("clearing it opens the way at once", features.open_now(features.find(ws, "the dry chamber"), ws.minutes)[0])
stub.ruling = {"sense": "yes", "why": "", "needs": [], "requires": [], "changes": [{"part": "", "becomes": "lit"}]}
ruling.run(ws, "lights a torch and wedges it in the rock", "I light a torch and wedge it in the rock.")
at = features.spot_of(ws)
check("a change with no part named is to where the player stands, and is told beside it", at is not None and "lit" in features.now_of(at, ws.minutes)
      and any("Now lit" in l for l in features.lines(ws)), features.lines(ws))
stub.ruling = {"sense": "yes", "why": "", "needs": [], "requires": [], "changes": [{"part": "the crystal throne room", "becomes": "lit"}]}
n_parts = len(features.here(store, "tidepool_caves"))
ruling.run(ws, "lights the crystal throne room", "I light the crystal throne room.")
check("a change to a part the place does not have changes nothing and makes nothing", len(features.here(store, "tidepool_caves")) == n_parts
      and not any("throne" in e.name for e in features.here(store, "tidepool_caves")))
try:
    rule(sense="yes", changes=[{"part": "", "becomes": "turned to gold"}])
    sent_back = False
except ValueError:
    sent_back = True
check("a change that is not one of the kinds is sent back to the model", sent_back)
stub.ruling = None

# ---- listening: what the words are about is what the game acts on
check("'sword' names a longsword", said("longsword", "i sell my sword"))
check("'silver coins' names no silverleaf", not said("silverleaf", "i hand over five silver coins"))
ws.enter("trading_square")
from engine import inventory
ws.to_pack(inventory.make_good("silverleaf", 1))
plan = [ActionIntent(kind="give", item="silverleaf", target="m1")]
ws.grounded_item("I hand over five silver coins to the merchant.", plan)
check("coins handed over are coins, not the silverleaf whose name holds 'silver'", plan[0].item == "coins", plan[0].item)
plan = [ActionIntent(kind="give", item="silverleaf", target="m1")]
ws.grounded_item("I give the merchant my silverleaf.", plan)
check("...and the silverleaf named is the silverleaf", plan[0].item == "silverleaf", plan[0].item)
plan = [ActionIntent(kind="talk", target="m1", speech="")]
ws.gesture_only("I nod at him.", plan)
check("a nod is a gesture, not speech", plan[0].kind == "other", plan[0].kind)
plan = [ActionIntent(kind="talk", target="m1", speech="Thank you.")]
ws.gesture_only("I nod and say \"Thank you.\"", plan)
check("...a nod with words is still talk", plan[0].kind == "talk")
ws.hire_by_id = lambda hid: {"name": "Bram Tull"}
ws.named_here = lambda text: "hermit_1" if "hermit" in text.lower() else ""
plan = [ActionIntent(kind="talk", target="hire:h1", speech="Who are you?")]
ws.to_the_named("I ask the hermit who he is.", plan)
check("words to the person the line names go to them, not to the companion who spoke last", plan[0].target == "hermit_1", plan[0].target)
plan = [ActionIntent(kind="talk", target="hire:h1", speech="Who is he?")]
ws.to_the_named("Bram, who is the hermit?", plan)
check("...words to the companion by name stay with them", plan[0].target == "hire:h1", plan[0].target)
del ws.hire_by_id, ws.named_here

# ---- a fork: the road the line already named
fork = {"members": [{"name": "", "side": "left fork", "to": "a"}, {"name": "", "side": "right fork", "to": "b"},
                    {"name": "", "side": "far right fork", "to": "c"}]}
check("'the far right road' is the far right fork", (exits.pick(fork, "I take the far right road.") or {}).get("to") == "c")
check("'the right fork' is the right fork", (exits.pick(fork, "I take the right fork.") or {}).get("to") == "b")

# ---- offers of work lapse
n = types.SimpleNamespace(work_offer={"task": "haul nets", "pay": 5, "minutes": 60, "until": 1000})
check("an offer of work stands until its hour", offer_open(n, 900) and not offer_open(n, 1001))
check("...an older offer with no hour stands", offer_open(types.SimpleNamespace(work_offer={"task": "x", "pay": 1, "minutes": 30}), 10 ** 9))

store.close()
shutil.rmtree("saves/ruling_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
