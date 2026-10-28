"""(f349) What the five-hour run asked for: companions out of the narrator's scenery, no narrator call on a quiet return, a pause shown
once per person, a local's distances in walks and days, the fight narrator with room in words and a memory of what it has shown, the
worn-word watch (found, never banned), speech without tics, the goddess remembering her earlier words, and a rewrite when a draft ends
sentence after sentence on a trailing participle."""
import random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import clock, combat, truth, voice_rules, worn
from llm.contracts import CompanionReply, GoddessLine, NPCReply, Narration, opener_of
from npc import land
from npc.traits import load_traits
from pydantic import ValidationError
from scenes import combat_prompts as cp, voice, world_prompts as wp
from scenes.combat_scene import CombatScene
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the worn-word watch
w = worn.Watch()
for i in range(30):
    w.add(f"Passage {i}. " + ("His expression is unreadable, a mask of weary patience. " if i % 3 == 0 else "The gate stands open. ")
          + ("Berric leans on the post, steadily. " if i % 2 == 0 else "The dog sleeps. "))
got = w.worn(keep=["Parth", "the stout gatekeeper"])
check("the words the passages leaned on are found: the manner words and the -ly", {"unreadable", "expression", "weary", "steady"} <= set(got), got)
check("a name is never worn, however often it comes up", "berric" not in got, got)
check("the nouns of the scene are not candidates", "gate" not in got and "post" not in got and "dog" not in got, got)
check("nothing is worn until there is a history", worn.Watch().worn() == [])
check("a draft leaning on them is seen, in any form", worn.leaned_on("Her expression was unreadable; he moved wearily.", ["expression", "unreadable", "weary", "steady"]) == ["expression", "unreadable", "weary"])
check("the watch is rules, not code: seed, suffixes, how many kept", {"seed", "suffixes", "keep", "least", "top"} <= set(voice_rules.V["worn"]) and "unreadable" in voice_rules.V["worn"]["seed"])

# ---- participle tails, and the one rewrite
t = voice.participle_tails("He nods. She sets the cup down, her eyes returning to the fire. The dog stirs, its tail thumping the boards. It is morning.")
check("sentences ending on a trailing participle are found, and the morning is not one", len(t) == 2 and "returning" in t[0] and "thumping" in t[1], t)
check("a sentence that ends on its verb or its noun is not", voice.participle_tails("The hammer rang. He put it down, and that was the end of the thing.") == [])
calls = []
def fake(task, system, request, schema, **kw):
    calls.append(request)
    return Narration(text="His expression is unreadable, weary. The rain goes on, the light failing, the yard emptying." if len(calls) == 1 else "Clean.")
voice.generate = fake
r = voice.fresh("narrate", "sys", "req", Narration, [], worn=["expression", "unreadable", "weary"])
check("a draft that leans on worn words is rewritten once, told which", len(calls) == 2 and "WORN OUT: expression, unreadable, weary" in calls[1] and r.text == "Clean.", calls[-1][-300:])
calls.clear()
def fake2(task, system, request, schema, **kw):
    calls.append(request)
    return Narration(text="He nods, his hand resting on the hilt. She turns away, her shoulders dropping. The door shuts." if len(calls) == 1 else "Clean.")
voice.generate = fake2
r = voice.fresh("narrate", "sys", "req", Narration, [])
check("a draft ending two sentences on a trailing participle is rewritten once, shown them", len(calls) == 2 and "TRAILING PARTICIPLE" in calls[1] and "resting on the hilt" in calls[1], calls[-1][-300:])
calls.clear()
voice.generate = lambda *a, **k: (calls.append(a[2]) or Narration(text="He nods, his hand resting on the hilt. The door shuts."))
voice.fresh("narrate", "sys", "req", Narration, [])
check("one such sentence is let be", len(calls) == 1)

# ---- speech without tics
def npc(speech, last=""):
    try:
        NPCReply.model_validate({"speech": speech, "intent": "small_talk"}, context={"last": last}); return ""
    except ValidationError as e:
        return str(e)
check("the same stock opener twice running is sent back", "opened your last line on 'Well'" in npc("Well, the mill's past the bridge.", "Well now, that depends on who's asking."), npc("Well, the mill's past the bridge.", "Well now, that depends."))
check("a different opener, or none, passes", npc("Aye, past the bridge.", "Well, that depends.") == "" and npc("The mill is past the bridge.", "The mill? Past the bridge, same as ever.") == "")
check("two trailing-offs in one reply are sent back", "trailing-off" in npc("I don't know... maybe... ask her."))
check("the opener is read past quotes, and a word that only starts like one is not one", opener_of('"Well now, friend."') == "well" and opener_of("Welling up, she said nothing.") == "" and opener_of("Oh. That.") == "oh" and opener_of("No. Not today.") == "")
def comp(speech, last):
    try:
        CompanionReply.model_validate({"speech": speech, "gesture": ""}, context={"member": {"name": "Berric Stone", "said": [last]}, "gesture_state": {}}); return ""
    except ValidationError as e:
        return str(e)
check("a hire keeps the same rule", "opened your last line" in comp("Aye, and the road's no better.", "Aye, that it is.") and comp("The road's no better.", "Aye, that it is.") == "")
from npc import prompts as npr
check("the townsfolk are told to open on the matter and to trail off at most once", "never two lines running" in npr.CONVERSATION_SYSTEM and "Trailing dots at most once" in npr.CONVERSATION_SYSTEM)

# ---- the goddess remembers
def god(speech, said):
    try:
        GoddessLine.model_validate({"speech": speech}, context={"said": said}); return ""
    except ValidationError as e:
        return str(e)
check("she never opens a return the way she opened an earlier one", "earlier return" in god("Again, so soon. The water is cold.", ["Again. So soon, my child.", "You came back to me."])
      and "earlier return" in god("Again... the cold.", ["Again, so soon."]) and god("The water is colder this time. Breathe.", ["Again, so soon."]) == "" and god("Again.", []) == "")
check("her earlier words are kept on the player", "goddess_said" in PlayerState.model_fields)

# ---- a local's distances
check("a local says a distance in walks and days, never minutes", clock.walk_words(10) == "a few minutes' walk" and clock.walk_words(70) == "an hour's walk"
      and clock.walk_words(400) == "half a day on foot" and clock.walk_words(1300) == "two days on the road" and not any(re.search(r"\d", clock.walk_words(m)) for m in (0, 55, 200, 700, 2000, 9000)))
check("the player's own map keeps its figures", clock.describe_duration(70) == "1 hour 10 minutes")

# ---- the fight narrator joins the rest
check("the fight narrator has room in words, no sentence count, one blow a sentence and its own exemplars",
      "Three to six" not in cp.NARRATE_SYSTEM and "LENGTH" in cp.NARRATE_SYSTEM and "HOW A FIGHT SOUNDS HERE" in cp.NARRATE_SYSTEM
      and "last thing in the sentence" in cp.NARRATE_SYSTEM and "up to eight sentences" not in cp.NARRATE_SYSTEM and "One sentence tells one blow" in cp.NARRATE_SYSTEM)
req = cp.narrate_request("P", "t", "swing", ["x [h1]"], "sword", "fine", ["a wolf, unhurt"], 2, length="up to about 90 words", shown=["the look of the wolf"], worn=["steady"])
check("its request carries the room, what the fight has shown and the worn words", "LENGTH: up to about 90 words" in req and "ALREADY SHOWN IN THIS FIGHT" in req and "the look of the wolf" in req and "WORN OUT (find other words): steady" in req)
check("a fight and a boss beat have their room in the rules", "words" in voice_rules.V["narration"]["fight"]["length"] and "words" in voice_rules.V["narration"]["fight_boss"]["length"] and len(voice_rules.V["exemplars"]["fight"]) >= 3)
check("an element on the blade is told to the narrator once a fight", combat.Combat(fighters=[]).burn_told is False and "combat.burn_told = True" in open("engine/combat.py").read())

# ---- in a scene
shutil.rmtree("saves/prose3_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("prose3_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
printed, narrated = [], []
console.narrate = lambda text: printed.append(text)
console.note = lambda text: None
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.player.mentor["never"] = True
ws.enter("parth")
check("a first arrival is never a quiet return", not ws.quiet_return())
def all_seen():
    here = truth.scene_of(ws).view(truth.NARRATOR, "narrator")
    ws.__dict__["_happenings_seen"] = {(ws.player.location, h) for h in here.lines("happenings")}
    ws.__dict__["_news_seen"] = set(here.lines("news")[:3])
ws.enter("parth"); ws._arrival_lines = []; all_seen()
check("back somewhere seen with nothing new: a quiet return", ws.quiet_return())
ws._arrival_lines = ["The smith has moved on to shoeing a horse."]
check("...not when someone has moved on to something else", not ws.quiet_return())
ws._arrival_lines = []
check("...nor when something was met on the way, or the player asked something", not ws.quiet_return(log=["a cart in the ditch"]) and not ws.quiet_return(text="I head back. Is the smith in?"))
ws.narrate = lambda event, player_text="": narrated.append(event)
ws.finish_journey(["tilted_plough", "parth"], 5, "I go back to the square.", [])
check("the engine says so in a line, and the narrator is not called", printed and printed[-1] == "You are back at Parth." and not narrated and ws.weight_hint is None, (printed[-1:], narrated))
check("...and the line is remembered like any passage", ws.recent_narration and ws.recent_narration[-1] == "You are back at Parth.")
ws.finish_journey(["tilted_plough", "parth"], 75, "I go back to the square.", [])
check("a longer way back says how long, as a walk", printed[-1] == "After an hour's walk, you are back at Parth.", printed[-1])
ws._arrival_lines = ["The smith has moved on to shoeing a horse."]
ws.finish_journey(["tilted_plough", "parth"], 5, "I go back.", [])
check("with something changed, the narrator is called as before", narrated and "arrives at Parth" in narrated[-1], narrated[-1:])

ws.player.party.append({"id": "h1", "name": "Berric Stone", "role": "warrior", "level": 3, "permanent": True, "rank": "F", "temper": ["dry"], "blurb": "A big quiet man."})
ws.player.party_mode = "with"
check("the narrator hears of a companion only when the event has them act", ws.companions_in("Berric takes the first watch without being asked.") == ["Berric Stone"] and ws.companions_in("The player waits an hour.") == [])
check("a hire is not among the narrator's people, and still in the scene for the interpreter",
      not any(v[0] == "Berric Stone" for v in ws.people_view()) and any(p.kind == "hire" and p.name == "Berric Stone" for p in truth._present_people(ws)))
req = wp.narration_request("t", types.SimpleNamespace(name="P", type="town", visible=[]), [], "x", companions=["Berric Stone"], worn=["steady"])
check("the narrator's request names a companion the event has act, and the worn words", "WITH THE PLAYER" in req and "Berric Stone" in req and "WORN OUT" in req and "steady" in req)
check("the narrator is told companions are not scenery, and that manner is what the body does", "not scenery" in wp.NARRATOR_SYSTEM and "never name an expression" in wp.NARRATOR_SYSTEM
      and "never name an expression" in wp.DIALOGUE_SYSTEM.lower() and "never name an expression" in wp.dialogue_request("t", types.SimpleNamespace(name="P", visible=[]), [], "w", "l", "d", "m", True, "p", "s", "", False, []))
check("the frame is told a pause is shown once a visit", "shown once for a person in a visit" in wp.DIALOGUE_SYSTEM)

ws.enter("parth"); npc = ws.present[0]; ws.present = [npc] + [n for n in ws.present if n.id != npc.id]
label = npc.label()
ws.note_shown(f"{label[0].upper() + label[1:]} looks up from the ledger and waits.")
check("a person pausing their work on the page is on the list, as shown once", any("pausing their work" in l and label in l for l in ws.shown_lines()), ws.shown_lines())
ws.enter("parth"); ws.present = [npc] + [n for n in ws.present if n.id != npc.id]
ws.note_shown(f"{label[0].upper() + label[1:]} works on without looking up.")
check("...and a passage in which nobody stops does not say so", not any("pausing" in l for l in ws.shown_lines()), ws.shown_lines())

# the watches on the scene, fed by what is remembered
for i in range(12):
    ws.remember_narration(f"Passage {i}: his expression is unreadable, a mask." if i % 2 else f"Passage {i}: the yard.")
    ws.remember_narration(f'{label}: "Folk round here keep to themselves, friend."', {"type": "says", "speaker": label, "speech": "Folk round here keep to themselves, friend.", "gesture": ""})
check("the scene's prose watch learns what the passages leaned on, and its speech watch what mouths did",
      {"expression", "unreadable"} <= set(ws.worn_words("prose")) and {"folk", "friend"} <= set(ws.worn_words("speech")) and "folk" not in ws.worn_words("prose"), (ws.worn_words("prose"), ws.worn_words("speech")))
a_local = next(n for n in ws.residents)
check("a local tells the way in walks, not minutes", not re.search(r"\d+ (minutes|hours?)", " ".join(ws.local_knowledge(a_local)) + " ".join(land.land_lines(world, "parth"))), ws.local_knowledge(a_local))

# the fight's memory of what it has shown
wolf = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "w0", "wolf", "near")
cs = CombatScene(ws, combat.Combat(fighters=[combat.fighter_from_character(ws.player.character), wolf]), "wolf")
cs.note_fight_shown("Dusk. The wolf comes out of the bracken, lean and grey, and the light catches your blade.")
check("after a passage the fight knows the ground, the light, the gleam and the foe's look are given",
      any("ground" in s for s in cs.fight_shown) and any("light" in s for s in cs.fight_shown) and any("gleam" in s for s in cs.fight_shown) and any("look of the wolf" in s for s in cs.fight_shown), cs.fight_shown)
n = len(cs.fight_shown)
cs.note_fight_shown("It lunges. You step aside.")
check("...and does not list a thing twice", len(cs.fight_shown) == n)

# places heard of: one quiet line a turn, not a note per place
notes, ledgers = [], []
console.note = lambda text: notes.append(text)
console.ledger = lambda text: ledgers.append(text)
new = [p.id for p in world.places.values() if not p.parent and p.id not in ws.known_places()][:3]
for pid in new:
    ws.hear(pid)
check("hearing of a place prints nothing by itself", not notes and not ledgers and all(pid in ws.player.heard for pid in new))
ws.heard_flush()
check("...the turn's end tells them once, together, as a ledger line and not a note",
      not notes and len(ledgers) == 1 and ledgers[0].startswith("Heard of: ") and all(world.places[pid].name in ledgers[0] for pid in new) and " and " in ledgers[0], ledgers)
ws.heard_flush()
check("...and nothing when nothing new was heard", len(ledgers) == 1)

# ---- what the 20261027_1334 run showed
# a long draft whose last sentence trails off is rewritten, even when it is the only such sentence
calls.clear()
def fake3(task, system, request, schema, **kw):
    calls.append(request)
    return Narration(text="The gate is open and the yard beyond it is quiet, the carts drawn up along the wall and the dogs asleep under them. "
                          "Berric sets his pack down by the well. He looks back the way you came, his hand resting on the hilt." if len(calls) == 1 else "Clean.")
voice.generate = fake3
r = voice.fresh("narrate", "sys", "req", Narration, [])
check("a passage that ends on a trailing participle is rewritten, told it was the last sentence", len(calls) == 2 and "ITS LAST SENTENCE" in calls[1] and r.text == "Clean.", calls[-1][-200:])
calls.clear()
voice.generate = lambda *a, **k: (calls.append(a[2]) or Narration(text="He looks back, his hand resting on the hilt. The gate is open."))
voice.fresh("narrate", "sys", "req", Narration, [])
check("...a short passage with one such sentence in the middle is let be", len(calls) == 1)

# the worn words are heard in speech too: a reply leaning on two of them is sent back
def npcw(speech, worn):
    try:
        NPCReply.model_validate({"speech": speech, "intent": "small_talk"}, context={"worn": worn}); return ""
    except ValidationError as e:
        return str(e)
check("a townsperson's reply that leans on two worn words is sent back, naming them",
      "'steady' and 'weary' are words everyone here has worn out" in npcw("The road is steady enough past the bridge, though you look weary to me, and the mill is not far.", ["steady", "weary", "glance"]))
check("...one worn word, or a short line, passes", npcw("The road is steady enough past the bridge, though the mill is not far from it.", ["steady", "weary"]) == ""
      and npcw("Steady on, weary one.", ["steady", "weary"]) == "")

# a hire is told of a loss, not asked how they are: 'how are you holding up?' is not a loss confided
hire = {"id": "h2", "name": "Tam Reed", "role": "scout", "level": 3, "permanent": True, "rank": "F", "temper": ["dry"], "blurb": "Quiet.", "trust": 40}
check("a loss confided is heard", ws.hire_feeling(hire, "My brother was killed by bandits last winter.") == "painful_told")
check("a question about their own hurt is not one", ws.hire_feeling(hire, "Are you all right after the wolf nearly killed you?") != "painful_told"
      and ws.hire_feeling(hire, "How are you holding up?") != "painful_told" and ws.hire_feeling(hire, "Someone died.") != "painful_told")

# the model server failing (Ollama's 500 on its own repeat limit) is one failed attempt, not a crash
import ollama
from llm import gateway
from llm.gateway import LLMError
class Broken:
    def chat(self, **kw):
        raise ollama.ResponseError("token repeat limit reached", 500)
_client = gateway._client
gateway._client = Broken()
try:
    gateway.generate("narrate", "sys", "req", Narration, retries=1, _quiet=True)
    got = None
except LLMError as e:
    got = e
except Exception as e:
    got = e
gateway._client = _client
check("a server error from the model becomes the gateway's own error, after every try, with the cause kept",
      isinstance(got, LLMError) and isinstance(got.__cause__, ollama.ResponseError) and gateway.OUTCOMES[-1] == ("narrate", False, 2), repr(got))

# the night-run bot
src = open("tools/nightrun.py").read()
check("the bot asks a companion how they are at most once a game day", "asked_hires" in src and "unasked" in src)

shutil.rmtree("saves/prose3_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
