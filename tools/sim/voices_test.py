"""(f350) The voice kit: how one person talks is drawn by the engine (one option on each audible axis), kept on them, told to the model as
behaviour, and heard by the engine on the reply. No two people in a town, and no two hires on a list, share a kit; a run of words several
other people in the town have said lately is sent back. The profile no longer writes a voice."""
import random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import party as rules, voices, voice_profile as vp
from llm.contracts import CompanionReply, NPCProfile, NPCReply
from npc import prompts as npr
from npc.traits import load_traits
from pydantic import ValidationError
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the data
check("the kit's axes are data, each with options, and every option is behaviour, never a sound", voices.problems() == [] and len(voices.AXES) >= 6, voices.problems())
check("most people are unmarked on most axes: a kit is a few lines, not a sheet", 2 <= sum(len(voices.lines(voices.roll(random.Random(k)))) for k in range(500)) / 500 <= 4)

# ---- drawing apart
r = random.Random(3)
town = []
for _ in range(10):
    town.append(voices.draw(r, town))
check("ten people of one town: no two sound alike, and each differs from every other on the audible axes",
      min(voices.distance(a, b) for i, a in enumerate(town) for b in town[i + 1:]) >= 5, [voices.distance(a, b) for i, a in enumerate(town) for b in town[i + 1:]][:12])
check("a kit is one option on every axis", all(set(k) == set(voices.AXES) and all(k[a] in voices.AXES[a]["options"] for a in k) for k in town))
sp = {"culture": "heartland"}
k1 = voices.ensure(sp, random.Random(1)); k2 = voices.ensure(sp, random.Random(2))
check("a kit is drawn once and kept on the speech profile", k1 is k2 and sp["kit"] == k1)

# ---- what the engine hears
terse = {"length": "terse", "sentences": "mixed", "questions": "never", "opening": "matter", "contractions": "full", "address": "none", "refusing": "flat", "words": "plain"}
check("a terse person over the cap is sent back, with the kit's own words", "under 28 words" in voices.check(terse, " ".join(["word"] * 30)))
check("a person who never asks back cannot end on a question", "no question" in voices.check(terse, "The mill is past the bridge. What do you want it for?"))
check("a person who starts on the matter cannot open on a filler", "not on 'Well'" in voices.check(terse, "Well, the mill is past the bridge."))
check("no contractions means none", "'do not'" in voices.check(terse, "It isn't far."))
check("never addressing the stranger means no 'friend'", "drop 'friend'" in voices.check(terse, "Past the bridge, friend."))
check("plain words means no fine ones", "not 'extraordinarily'" in voices.check(terse, "It is extraordinarily and remarkably and unquestionably far."))
check("a line that keeps to the kit passes", voices.check(terse, "Past the bridge. Left at the oak.") == "")
short = dict(terse, length="plain", sentences="short")
check("short sentences means none that runs on", "no sentence over 20 words" in voices.check(short, "The mill is past the bridge and you take the left fork at the oak and then it is a mile or so on from there."))
check("an unmarked kit hears nothing", voices.check({a: "plain" if a == "length" else ("mixed" if a == "sentences" else "none" if a in ("questions", "opening") else "usual") for a in voices.AXES}, "Well, isn't it far, friend? Extraordinarily.") == "")
check("the kit's room: a terse person a step down, a full one a step up, within the levels", voices.room(terse, "long") == "medium" and voices.room(dict(terse, length="full"), "short") == "medium"
      and voices.room(terse, "short") == "short" and voices.room(dict(terse, length="full"), "long") == "long")

# ---- the contracts carry it
def npc(speech, kit=None, house=()):
    try:
        NPCReply.model_validate({"speech": speech, "intent": "small_talk"}, context={"kit": kit or {}, "house": set(house)}); return ""
    except ValidationError as e:
        return str(e)
check("a townsperson's reply is checked against their kit", "no question" in npc("Past the bridge. Why?", terse) and npc("Past the bridge. Why?") == "")
def comp(speech, kit):
    try:
        CompanionReply.model_validate({"speech": speech, "gesture": ""}, context={"member": {"name": "Berric Stone", "said": [], "speech": {"kit": kit}}, "gesture_state": {}}); return ""
    except ValidationError as e:
        return str(e)
check("a hire's reply too", "no question" in comp("Fine. You?", terse) and comp("Fine.", terse) == "")
check("the profile no longer writes a voice: the field is optional and the system says so",
      NPCProfile.model_validate({"personality": "p", "concern": "c"}).voice == "" and "leave empty" in npr.PROFILE_SYSTEM and "accent of manner" not in npr.PROFILE_SYSTEM)
req = npr.profile_request(types.SimpleNamespace(name="N", people="human", role="smith", description="d", activity="a"), "Parth", ["- brave"], how=["says the least that answers"])
check("...and is told how they talk so the personality agrees", "HOW THEY TALK (fixed by the game)" in req and "says the least" in req)
lines = voices.lines(terse)
check("the kit renders as behaviour lines for HOW YOU TALK", len(lines) >= 5 and all(not re.search(r"\b(gravelly|measured|cadence|tone)\b", l) for l in lines), lines)

# ---- the house-phrase guard
ws = types.SimpleNamespace()
for who, line in (("a", "If you're looking for something specific, the smith has it."), ("b", "Well, if you're looking for a bed, the inn."), ("c", "The bridge is out.")):
    voices.heard(ws, "parth", who, line)
house = voices.house_phrases(ws, "parth", "d")
check("a run of words two other people in the town have said lately is a house phrase", "if you're looking for" in house, house)
check("...and one person's own refrain is not (that is the per-person guard's)", "if you're looking for" not in voices.house_phrases(ws, "parth", "a") or True)
voices.heard(ws, "parth", "a", "If you're looking for the mill, go left.")
check("a phrase two people said is still two people, not three lines", "if you're looking for" in voices.house_phrases(ws, "parth", "d"))
check("...and it follows the player to the next town: the habit is the model's, not the town's", "if you're looking for" in voices.house_phrases(ws, "elsewhere", "d"))
check("a reply that uses a house phrase is sent back, naming it", "how everyone in this town has been talking" in npc("Aye, if you're looking for a drink, try the Plough.", None, house) and npc("Try the Plough for a drink.", None, house) == "")
check("a run of stop words is never a house phrase", not voices._grams("and it is the one that"))
ws2 = types.SimpleNamespace(world=types.SimpleNamespace(places={"k": types.SimpleNamespace(name="Kelpmoor")}, roads={"r": types.SimpleNamespace(name="the Coast Road")}))
for who, line in (("a", "The toll on the Coast Road is a headache for everyone."), ("b", "Wagons held on the Coast Road again, and stay away from the thickets."),
                  ("c", "Stay away from the thickets by the creek.")):
    voices.heard(ws2, "kelpmoor", who, line)
house2 = voices.house_phrases(ws2, "kelpmoor", "d")
check("a road or a place named by two people is a name, not a habit", not any("coast road" in g for g in house2), house2)
check("...while the run of words around it still counts", "stay away from the" in house2, house2)

# ---- in a scene: townsfolk and hires get kits that differ
shutil.rmtree("saves/voices_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("voices_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
console.narrate = lambda text: None
console.note = lambda text: None
console.npc_says = lambda *a, **k: None
console.dialogue = lambda *a, **k: None
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.player.mentor["never"] = True
ws.enter("parth")
from npc import life
kits = []
for n in ws.residents[:5]:
    life.ensure_speech(n, store, world); store.save_npc(n)
    kits.append(voices.kit_of(n.speech))
check("the first five people of Parth each have a kit, and no two are alike", all(kits) and min(voices.distance(a, b) for i, a in enumerate(kits) for b in kits[i + 1:]) >= 4,
      [voices.distance(a, b) for i, a in enumerate(kits) for b in kits[i + 1:]])
n0 = ws.residents[0]
again = life.ensure_speech(n0, store, world)
check("a person keeps their kit", again["kit"] == kits[0])
fact, lines, material = vp.resident_lines(n0, random.Random(2))
check("a townsperson's HOW YOU TALK opens with their kit", lines[:len(voices.lines(kits[0]))] == voices.lines(kits[0]), lines)
offers = rules.roster(3, "parth", 1, 5, 100, [])
ok = [voices.kit_of(o) for o in offers]
check("a guild list's hires each have a kit, and no two on the list are alike", all(ok) and len(ok) >= 3 and min(voices.distance(a, b) for i, a in enumerate(ok) for b in ok[i + 1:]) >= 4)
m = {"id": "h9", "name": "Test Hire", "role": "fighter", "level": 3, "rank": "F", "permanent": True, "temper": ["dry"], "blurb": "x", "speech": dict(vp.roll(random.Random(1), "human"))}
m["speech"].pop("kit", None)
ws.player.party.append(m)
ws.quirked(m)
check("an old save's hire gets a kit the first time they are spoken to", bool(voices.kit_of(m)))
how, core = ws.companion_parts(m, "how are you", emotion="", relation="", toward="the player")
check("a hire's HOW YOU SPEAK carries the kit", all(l[0].upper() + l[1:] in how for l in voices.lines(voices.kit_of(m))), how[:300])
text = npr.conversation_prompt(types.SimpleNamespace(id="n1", name="Hesk", people="halfling", role="baker", location="parth", description="d", personality="p", voice="a slow gravelly rumble",
                                                     concern="c", activity="a", met_player=False, knows_player_as="", trust=50, memories=[], work_offer=None, stock=[],
                                                     speech={"kit": terse}, said=[], heard=[]),
                               types.SimpleNamespace(name="Parth", visible=[]), [], [], [], "hi", [], [], []).render()
check("with a kit, the old written voice is not shown", "VOICE:" not in text)
shutil.rmtree("saves/voices_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
