"""(f347) Townsfolk have a country and a stance, do not say the same thing twice, and answer a goodbye with two words.
- speech.yaml's cultures reach residents: the town's region and their people decide where they were raised; one feature per reply on the
  culture budget, as for hires.
- the engine rolls a stance per conversation (busy, wary, tired, a grievance, after something, or none) and the prompt states it plainly.
- a reply that means what one of their last replies meant is sent back (the hires' guard, on the record's `said`); a few words are let be,
  and the same question may get much the same answer.
- a line that is nothing but a goodbye never reaches the interpreter: the person answers with one short parting line, no frame."""
import collections, random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
from engine import data_check, partings, voice_profile as vp, voice_rules
from llm.contracts import NPCReply, Parting
from pydantic import ValidationError
stub = simlib.Stub("warrior", 1); simlib.install(stub)      # first: the stand-in model, so nothing here reaches for a real Ollama
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

check("the data checks pass with the regions table and the farewell intercept", data_check.check() == [], data_check.check()[:3])

# ---- a country for residents
c = collections.Counter(vp.resident_culture("human", "wend_vale", random.Random(k)) for k in range(400))
check("a human of the Wend Vale is mostly heartland-raised", c["heartland"] / 400 > 0.65, c)
c = collections.Counter(vp.resident_culture("dwarf", "wend_vale", random.Random(k)) for k in range(400))
check("a dwarf there is more often heartland than Ironvein, but Ironvein stays common", 0.2 < c["ironvein"] / 400 < 0.6 and c["heartland"] > 150, c)
c = collections.Counter(vp.resident_culture("human", "rimelands", random.Random(k)) for k in range(400))
check("a human of the Rimelands is mostly rimelands-raised", c["rimelands"] / 400 > 0.5, c)
c = collections.Counter(vp.resident_culture("dwarf", "nowhere", random.Random(k)) for k in range(400))
check("an unlisted region leaves the people's own weights", c["ironvein"] / 400 > 0.6, c)
npc = types.SimpleNamespace(id="n1", name="Hesk Varley", people="halfling", role="baker", speech={}, said=[], heard=[], trust=50, concern="the oven", motive="", activity="kneading dough")
vp.ensure_npc(npc, random.Random(1), "saltmarches")
check("a resident gets a profile once, from their people and region, with no family trade", npc.speech["culture"] in ("heartland", "saltmarches") and npc.speech["background"] == "" and "tells" in npc.speech)
same = dict(npc.speech)
vp.ensure_npc(npc, random.Random(99), "rimelands")
check("...and keeps it", npc.speech == same)
fact, lines, material = vp.resident_lines(npc, random.Random(2))
check("the reply is told the plain fact of their people, and a few lines on how they talk at most", fact.startswith("A halfling") and len(lines) <= 2, (fact, lines))
runs = [vp.resident_lines(npc, random.Random(k))[1] for k in range(200)]
check("their culture shows in some replies, never all", 0.1 < sum(1 for r in runs if any("way of talking" in l or "comparison" in l or "home shows" in l for l in r)) / 200 < 0.7)

# ---- a stance per conversation
st = collections.Counter(voice_rules.roll_stance(npc, 600, random.Random(k)) for k in range(400))
check("most talks have no stance; busy and a grievance turn up, wary does not at trust 50, nothing after without a motive",
      st[""] / 400 > 0.3 and any("busy" in k for k in st) and any("grievance" in k and "the oven" in k for k in st)
      and not any("wary" in k for k in st) and not any("after something" in k for k in st), st)
npc.trust, npc.motive = 30, "buy the mill"
st = collections.Counter(voice_rules.roll_stance(npc, 600, random.Random(k)) for k in range(400))
check("with low trust and a motive, wary and after turn up", any("wary" in k for k in st) and any("buy the mill" in k for k in st), st)
day = sum(1 for k in range(400) if "tired" in voice_rules.roll_stance(npc, 600, random.Random(k)))
from engine import clock
dark = next(m for m in range(0, 1440, 30) if clock.is_dark(m)); light = next(m for m in range(0, 1440, 30) if not clock.is_dark(m))
day = sum(1 for k in range(400) if "tired" in voice_rules.roll_stance(npc, light, random.Random(k)))
night = sum(1 for k in range(400) if "tired" in voice_rules.roll_stance(npc, dark, random.Random(k)))
check("tired is likelier after dark", night > day, (day, night))

# ---- the prompt
from npc import prompts
place = types.SimpleNamespace(name="Parth", visible=["a well"])
full = types.SimpleNamespace(id="n1", name="Hesk Varley", people="halfling", role="baker", location="parth", description="d", personality="p", voice="v", concern="the oven",
                             activity="kneading", met_player=False, knows_player_as="", trust=50, memories=[], work_offer=None, stock=[], speech=npc.speech, said=["Bread's two copper."], heard=["how much?"])
p = prompts.conversation_prompt(full, place, ["- wary"], [], [], "what's good today?", [], [], [], stance="busy: kneading. The work comes first",
                                voice_fact="A halfling.", voice_lines=["Keeps things short and practical, and laughs easily."], material=["a saying from home: 'Mend the net before you need it.'"],
                                unsaid="SAID LATELY BY YOU (say something new):\n  - Bread's two copper.")
text = p.render()
check("the prompt carries the stance, the people, how they talk, the material and what was said lately, and ends on the line and its room",
      "RIGHT NOW YOU ARE: busy" in text and "YOUR PEOPLE: A halfling." in text and "HOW YOU TALK:" in text and "WORDS YOU MAY USE" in text
      and "SAID LATELY BY YOU" in text and text.rstrip().endswith("LENGTH: a line or two, up to about 35 words") and "THIS CONVERSATION SO FAR" in text, text[-600:])
check("how they talk and the stance are instructions; the saying is material; the rest is fact", "Keeps things short" in "\n".join(p.texts("instruction"))
      and "busy: kneading" in "\n".join(p.texts("instruction")) and "Mend the net" in "\n".join(p.texts("material")) and "YOU ARE: Hesk" in "\n".join(p.texts("fact")))
check("the plain request is the same text", prompts.conversation_request(full, place, ["- wary"], [], [], "hi", [], [], []) == prompts.conversation_prompt(full, place, ["- wary"], [], [], "hi", [], [], []).render())
check("the system prompt gives the stance rule", "Answer the part you care about" in prompts.CONVERSATION_SYSTEM and "nobody drops everything for a stranger" in prompts.CONVERSATION_SYSTEM)

# ---- the repeat guard
recent = ["The roads are just as they always are, muddy enough to swallow a boot, and the carts hate them."]
try:
    NPCReply.model_validate({"speech": "The roads are just as they always are, muddy enough to swallow a boot.", "intent": "small_talk"}, context={"recent": recent})
    check("a reply said again is sent back", False)
except ValidationError as e:
    check("a reply said again is sent back", "said something very like" in str(e), str(e)[:200])
ok = NPCReply.model_validate({"speech": "Aye.", "intent": "small_talk"}, context={"recent": ["Aye."]})
check("a word or two is let be", ok.speech == "Aye.")
ok = NPCReply.model_validate({"speech": "Horseshoes and nails, mostly, and the odd hinge when the carpenter asks.", "intent": "small_talk"}, context={"recent": recent})
check("something new passes", bool(ok.speech))
ok = NPCReply.model_validate({"speech": "The roads are just as they always are, muddy enough to swallow a boot.", "intent": "small_talk"}, context={})
check("no record, no guard", bool(ok.speech))

# ---- the parting line
try:
    Parting.model_validate({"speech": " ".join(["word"] * 30)})
    check("a parting is a few words, not a speech", False)
except ValidationError as e:
    check("a parting is a few words, not a speech", "not a speech" in str(e))
check("a parting may be a word and a gesture", Parting.model_validate({"speech": "Aye.", "gesture": "nods"}).gesture == "nods")
w = types.SimpleNamespace(trust=80); c = types.SimpleNamespace(trust=20)
check("the written parting follows how they are with the player", voice_rules.written_parting(w, random.Random(1)) in voice_rules.V["partings"]["warm"]
      and voice_rules.written_parting(c, random.Random(1)) in voice_rules.V["partings"]["wary"])
check("...and is never one they said lately", voice_rules.written_parting(c, random.Random(1), said=["Hm.", "Go on, then."]) == "Mind yourself.")

# ---- what counts as a goodbye
yes = ["Thanks, that's all. Goodbye.", "Thanks, I'll let you get on.", "That's all I wanted to know. Good day.", "I'd best be moving on.", "Goodbye", "bye!",
       "Farewell, Osric.", "Good day to you, then.", "Thank you for your help. I'll be on my way.", "Right. Thanks. See you around.", "I say goodbye and thank him for his time",
       "Safe travels", "Take care, friend.", "Nothing else, thanks.", "I won't keep you any longer. Good day.", "Alright then, I must be going.", "Okay thanks bye", "\"Goodbye, woodsman.\""]
no = ["Goodbye, but first: where is the mill?", "Thanks. What do you know about the north?", "I'll let you get on. Can I buy a loaf first?", "I leave", "I turn away and say nothing",
      "Tell me about the road before I go", "goodbye to all that nonsense, tell me the price", "I head to the inn", "Thanks, I will take the job.", "Good day. Is the smith open?",
      "I nod and walk to the market", "thanks for the warning, I'll take the north road then"]
names = ("Osric Vane", "the scarred woodsman")
check("a plain goodbye, with its thanks and filler, is a goodbye", all(partings.is_goodbye(t, names) for t in yes), [t for t in yes if not partings.is_goodbye(t, names)])
check("a goodbye that carries a question, an action or anything more is not", not any(partings.is_goodbye(t, names) for t in no), [t for t in no if partings.is_goodbye(t, names)])

# ---- in a scene: the intercept, the parting, no interpreter
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
from npc.traits import load_traits
from scenes.world import WorldScene
from ui import console
shutil.rmtree("saves/townsfolk_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("townsfolk_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
printed = []
console.npc_says = lambda label, speech, gesture="": printed.append(("says", label, speech, gesture))
console.dialogue = lambda before, who, speech, after="": printed.append(("frame", who, speech, before))
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.enter("parth")
ws.player.mentor["never"] = True                    # Maren does not step in: this is about the townsfolk
smith = next(n for n in ws.residents if n.role == "smith")
ws.present = [smith] + [n for n in ws.present if n.id != smith.id]
stub.plan = [{"kind": "talk", "target": smith.id, "speech": "What do you make?"}]
ws.turn("I ask the smith what she makes")
check("a talk begins with a partner and a stance rolled for it (possibly none)", ws.partner and ws.partner.id == smith.id and hasattr(ws, "stance"), (getattr(ws.partner, "id", None), getattr(ws, "stance", None)))
check("the record keeps what they said and heard, and a speech profile", smith.said and smith.heard and smith.speech.get("culture"), (smith.said, smith.heard, smith.speech.get("culture")))
plans = stub.calls.get("ActionPlan", 0)
ws.turn("Thanks, that's all. Goodbye.")
check("a goodbye never reaches the interpreter", stub.calls.get("ActionPlan", 0) == plans, (plans, stub.calls.get("ActionPlan")))
check("the person answers with one bare line, and the talk ends", printed and printed[-1][0] == "says" and printed[-1][1] == smith.label() and ws.partner is None, printed[-1:])
check("the parting is on their record", len(store.load_npc(smith.id).said) == 2, store.load_npc(smith.id).said)
ws.turn("I ask the smith what she makes")
stub.plan = [{"kind": "leave_conversation", "target": smith.id, "speech": "Good day to you."}]
n = len(printed)
ws.turn("I say good day to the smith")
check("a goodbye the interpreter read as leaving is answered the same way", len(printed) == n + 1 and printed[-1][0] == "says" and ws.partner is None, printed[-1:])
shutil.rmtree("saves/townsfolk_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
