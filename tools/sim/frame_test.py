"""(f347) The frame is the exception: the engine decides when a line of speech gets the narrator's frame (the first words this visit, trust
moved, a reveal, a refusal, a gift, a leaving), and every other line is the words with a short gesture. The narrator and the frames are
told what the player has already read about the place this visit; lengths are room in words, not sentence counts; the voice is shown."""
import random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
from npc.traits import load_traits
from scenes.world import WorldScene
from scenes import voice, world_prompts as wp
from engine import voice_rules, truth
from llm.contracts import DialogueFrame
from ui import console
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the rules as data
V = voice_rules.V
check("(f375) no length is set: the voice rules hold no room for the narrator or for what people say", "narration" not in V and "npc" not in V and "points" not in V)
check("the reasons a line gets a frame are declared", {"first", "trust", "reveal", "refuse", "gift", "leave"} <= set(V["frame_when"]))
ex = V["exemplars"]
check("exemplars: a few passages and a few replies", len(ex["passages"]) >= 4 and len(ex["speech"]) >= 6)
check("exemplars name no one and nowhere and carry no numbers", all(not truth.coined(t, "", frozenset()) and not re.search(r"\d", t) for t in ex["passages"] + ex["speech"]),
      [truth.coined(t, "", frozenset()) for t in ex["passages"] + ex["speech"]])
check("the narrator, the frames and the fight see the passages; townsfolk and hires see the replies",
      "HOW NARRATION SOUNDS HERE" in wp.NARRATOR_SYSTEM and "HOW NARRATION SOUNDS HERE" in wp.DIALOGUE_SYSTEM
      and "HOW PEOPLE SOUND HERE" in __import__("npc.prompts", fromlist=["CONVERSATION_SYSTEM"]).CONVERSATION_SYSTEM
      and "HOW PEOPLE SOUND HERE" in __import__("scenes.party_prompts", fromlist=["TALK_SYSTEM"]).TALK_SYSTEM)
check("the DM voice asks for sentence music as craft, not a quota", "a short one lands a blow" in voice.DM_VOICE and "under eight words" not in voice.DM_VOICE
      and "two before a noun" in voice.DM_VOICE and "trailing participle" in voice.DM_VOICE)
check("the narrator is told to say what is new, and to give an arrival as the place and one person, with no length", "ALREADY SHOWN THIS VISIT" in wp.NARRATOR_SYSTEM
      and "one person doing one thing" in wp.NARRATOR_SYSTEM and "LENGTH" not in wp.NARRATOR_SYSTEM and "sentence or two" not in wp.NARRATOR_SYSTEM
      and "say less" not in wp.NARRATOR_SYSTEM + voice.DM_VOICE and "economical" not in voice.DM_VOICE)
check("the frame never shows the character going back to work, never ends on the room", "going back to what they were doing" in wp.DIALOGUE_SYSTEM
      and "closing shot" in wp.DIALOGUE_SYSTEM and "WHY THIS LINE GETS A FRAME" in wp.DIALOGUE_SYSTEM)
req = wp.narration_request("day 1, morning", types.SimpleNamespace(name="Parth", type="town", visible=["a well"]), [], "x", already=["the place itself", "the weather"])
check("the narrator's request lists what was shown", "ALREADY SHOWN THIS VISIT" in req and "- the weather" in req, req)
check("...and not when nothing was", "ALREADY SHOWN" not in wp.narration_request("t", types.SimpleNamespace(name="P", type="town", visible=[]), [], "x"))
check("(f375) the narrator's request and a frame's carry no length", "LENGTH" not in req and "LENGTH" not in wp.DIALOGUE_SYSTEM + wp.EXCHANGE_SYSTEM
      and "LENGTH" not in wp.dialogue_request("t", types.SimpleNamespace(name="P", visible=[]), [], "x", "l", "d", "m", False, "hi", "yes", "", False, []))

# ---- short gestures
sg = voice_rules.short_gesture
check("a short gesture is kept", sg("wipes her hands on her apron.") == "wipes her hands on her apron")
check("(f375) a long one is kept whole, never cut at a clause", sg("glances at the door, then back to the ledger with a sigh") == "glances at the door, then back to the ledger with a sigh"
      and sg("turns the whetstone slowly in her scarred hands without looking up") == "turns the whetstone slowly in her scarred hands without looking up")
check("nothing stays nothing", sg("") == "" and sg("  ") == "")
from engine import voice_rules as _vr
check("the words decide a refusal, not the model's intent", _vr.refuses("No. Not for you, and not today.") and _vr.refuses("Mind your own business, stranger.") and not _vr.refuses("The mill is past the bridge, on the left."))
check("...and a long gesture with a comma is kept too", sg("gives a slow, deliberate nod toward the door of the inn") == "gives a slow, deliberate nod toward the door of the inn")

# ---- the frame contract holds what the instruction alone could not
from pydantic import ValidationError
def frame(before, after, speaker=("Mabry Wilins",), others=("Tuckwin Fosell", "Heth Bradton", "the stout watchman")):
    try:
        DialogueFrame.model_validate({"before": before, "after": after}, context={"speaker": list(speaker), "others": list(others)})
        return ""
    except ValidationError as e:
        return str(e)
check("a frame that sends them back to their work is sent back", "going back to what they were doing" in frame("", "He returns to his whetstone with a slow nod, the rhythmic scrape resuming.")
      and frame("", "She turns back to the stove.") and frame("", "He lets his shoulders drop, the steady slide of stone over metal resuming its pace."))
check("a frame that ends on what the words changed passes", frame("", "His shoulders drop an inch.") == "" and frame("He looks up.", "") == "")
check("a frame that opens on another person's name is sent back", "opens on Tuckwin Fosell" in frame("Tuckwin leans into the warmth of the stove.", "")
      and "Heth Bradton" in frame("", "Heth stops the whetstone mid-stroke."))
check("...but one about the speaker, by name, a pronoun or how they are known, passes", frame("Mabry leans into the stove.", "") == "" and frame("She looks away.", "") == ""
      and frame("The watchman sets the rag aside.", "", speaker=("the stout watchman",), others=("Tuckwin Fosell",)) == "")

# ---- the engine's decision, in a scene
shutil.rmtree("saves/frame_test", ignore_errors=True)
simlib.install(simlib.Stub("warrior", 1))
world = load_world(); store = CampaignStore.open_or_create("frame_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
asked, printed = [], []
def fake(task, system, request, schema, **kw):
    asked.append(request)
    return DialogueFrame(before="A look.", after="")
voice.generate = fake
console.npc_says = lambda label, speech, gesture="": printed.append(("says", label, speech, gesture))
console.dialogue = lambda before, who, speech, after="": printed.append(("frame", who, speech, before))
console.narrate = lambda text: None
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.enter("parth")
npc = next(n for n in ws.residents if n.role == "smith")
ws.present = [npc] + [n for n in ws.present if n.id != npc.id]
reply = types.SimpleNamespace(speech="Horseshoes, a copper apiece.", gesture="wipes her hands on her apron, leaving a dark smear across the leather", intent="small_talk", trust_change=0, gives=None)
ws.narrate_dialogue(npc, npc.label(), npc.label(), "i ask what she makes", reply, False)
check("the first words with someone this visit are framed, and the frame is told why", printed[-1][0] == "frame" and "WHY THIS LINE GETS A FRAME: the first words" in asked[-1], (printed[-1], asked[-1][:300]))
n = len(asked)
ws.narrate_dialogue(npc, npc.label(), npc.label(), "and nails?", reply, False)
check("an ordinary second line is the words alone: no frame call, and the gesture whole (f375)",
      len(asked) == n and printed[-1] == ("says", npc.label(), "Horseshoes, a copper apiece.", "wipes her hands on her apron, leaving a dark smear across the leather"), printed[-1])
nudged = types.SimpleNamespace(speech="Aye, a copper.", gesture="", intent="small_talk", trust_change=1, gives=None)
check("trust nudged by one is not a moment", ws.frame_reasons(npc, nudged) == [], ws.frame_reasons(npc, nudged))
moved = types.SimpleNamespace(speech="Fine. Two copper, and that's a favour.", gesture="", intent="bargain", trust_change=2, gives=None)
ws.narrate_dialogue(npc, npc.label(), npc.label(), "i haggle", moved, False, reasons=ws.frame_reasons(npc, moved))
check("trust that moved earns a frame", printed[-1][0] == "frame" and "trust in the player has just moved" in asked[-1])
check("an intent of 'refuse' on an ordinary answer is not a moment", ws.frame_reasons(npc, types.SimpleNamespace(intent="refuse", speech="The mill is past the bridge.", trust_change=0, gives=None)) == [])
check("a refusal, a gift, a leaving and a judged attempt do too", voice_rules.V["frame_when"]["refuse"] in ws.frame_reasons(npc, types.SimpleNamespace(intent="refuse", speech="No. Not for you.", trust_change=0, gives=None))
      and voice_rules.V["frame_when"]["gift"] in ws.frame_reasons(npc, types.SimpleNamespace(intent="help", trust_change=0, gives=types.SimpleNamespace(name="a pendant")))
      and voice_rules.V["frame_when"]["leave"] in ws.frame_reasons(npc, types.SimpleNamespace(intent="leave", trust_change=0, gives=None))
      and voice_rules.V["frame_when"]["decided"] in ws.frame_reasons(npc, reply, [], "[THE GAME HAS DECIDED: it worked]")
      and voice_rules.V["frame_when"]["reveal"] in ws.frame_reasons(npc, reply, ["clue:thread1:0"]))
check("an ordinary fact of the town conveyed is not a moment; a clue is", ws.frame_reasons(npc, reply, ["lore_parth_river"]) == [])
check("an ordinary line has no reason", ws.frame_reasons(npc, reply) == [])
ws.enter("parth")
check("a new visit starts the count over", voice_rules.V["frame_when"]["first"] in ws.frame_reasons(npc, reply))
ws._framed_hires = {"Tuckwin Fosell"}
ws.enter("guild_house")
check("a hire's frame count holds across the buildings of one town", ws._framed_hires == {"Tuckwin Fosell"})
ws.enter(next(p.id for p in world.places.values() if p.type == "town" and p.id != "parth"))
check("...and starts over in a new town", ws._framed_hires == set())
check("no stance text is a line to quote back", not any(w in t["text"] for t in voice_rules.V["stances"].values() for w in ("long day", "I am busy", "I'm busy")))

# ---- what was shown this visit
ws.enter("parth"); ws.present = [npc] + [n for n in ws.present if n.id != npc.id]
check("nothing shown yet on arrival", ws.shown_lines() == [])
label = npc.label()
ws.note_shown(f"Rain. {label[0].upper() + label[1:]} works the bellows while the square empties.")
lines = ws.shown_lines()
check("after a passage: the place, the weather and the person it described are on the list",
      any("place itself" in l for l in lines) and any("weather" in l for l in lines) and any(label in l for l in lines), lines)
others = [n for n in ws.present if n.id != npc.id]
check("a person the passage did not describe is not", not others or not any(others[0].label() in l for l in lines), lines)
ws.enter("parth"); ws.present = [npc] + [n for n in ws.present if n.id != npc.id]
head = npc.label().split()[-1]
ws.note_shown(f"A muscular {head} strikes a glowing rod of iron.")
check("a person described by a paraphrase of their epithet counts as shown", any(npc.label() in l for l in ws.shown_lines()), (npc.label(), ws.shown_lines()))
check("the revisit line never invents a change", "never invent a change" in ws.brevity() or not ws.revisit)
ws.narrate_dialogue(npc, label, label, "hello", reply, False, reasons=["test"])
check("a frame is told the list", "ALREADY SHOWN THIS VISIT" in asked[-1] and label in asked[-1], asked[-1][:400])

# ---- the weight of an arrival
ws.weight_hint = None
ws.enter("tilted_plough")
check("a first visit to a building inside a town is not a first sight: no extra room", ws.weight_hint is None, ws.weight_hint)
fresh_town = next(p for p in world.places.values() if p.type == "town" and p.id not in ws.player.visited)
ws.enter(fresh_town.id)
check("a first arrival in a town earns a rich passage", ws.weight_hint == "rich", ws.weight_hint)
ws.weight_hint = None
ws.enter("parth")
check("a return to a place already peopled is brief", ws.weight_hint == "brief", ws.weight_hint)
check("the revisit note says what has changed, in a sentence or two, and never invents it", "has changed since" in ws.brevity() and "never invent" in ws.brevity())

shutil.rmtree("saves/frame_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
