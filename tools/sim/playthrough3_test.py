"""(f384) What the third logged playthrough showed (Tidepool Caves, a fist-fighting warrior with a worg called Fenris).
- "head straight into the guild hall and hand that contract in to the clerk" was asked back ("do you mean now?"): the audit read the
  clerk as 'not here', though the plan's first step walked to where he works.
- "go to smith" lost its walk: the line was put in the clerk's mouth and the walk dropped as a move to someone already here.
- "*snatch the paper and ink and force my name in the register without paying*" became a paid joining.
- Nine lines after a hire spoke went to that hire as speech: "*execute the remaining sahuagin*", "follow sea hag", "turn in all quests".
- "pick up coins" after a fight: the coins were already in the purse, the narrator had shown them lying in the mud, and called them
  worthless when they could not be found.
- "Fenris, attack the troll", "Merris Oxwick, fire a bolt at the reef shark", "hold down the shark" were the player's own punches.
- A rewrite printed every blow's figure after the passage; a passage put words in two woodcutters' mouths; a frame printed
  'ALREADY SHOWN THIS VISIT'; the interpreter did not know Fenris; two finished jobs took two passages, each told 'a sentence or two'."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import llm.gateway as gw
CALLS = []
_chat = gw._client.chat
def chat(*a, **k):
    CALLS.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
NOTES = []
for f in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from pydantic import ValidationError
from core.models import Companion
from engine import combat, intent_audit as ia, party, quests
from llm.contracts import ActionIntent, DialogueFrame, Narration
from npc.traits import load_traits
from scenes import combat_prompts as cp, voice
from scenes.combat_scene import CombatScene
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/playthrough3_test", ignore_errors=True)
store = CampaignStore.open_or_create("playthrough3_test")
store.meta.seed = 3; store.meta.minutes = 120; store.meta.turn = 1; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.companions = [Companion(id="c1", name="Fenris", creature="worg" if "worg" in world.bestiary else "wolf", kind="beast", role="striker", level=3)]
store.save_player(PlayerState(character=char, location="guild_house", guild_rank="F"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("guild_house")
clerk = ws.clerk_here()
ws.enter("trading_square")

# ---- a talk at the place the plan walks to
plan = [ActionIntent(kind="move", destination="guild_house", summary="go"), ActionIntent(kind="talk", target=clerk.id, speech="Here's the contract.", summary="hand it in")]
check("talking to the clerk after walking to the hall is no 'who is not here'", ia.problems(plan, ws.situation()) == [], ia.problems(plan, ws.situation()))
plan[1].target = "clerk"
check("...by his work as well as his name", ia.problems(plan, ws.situation()) == [], ia.problems(plan, ws.situation()))
plan[1].target = "no_such_person"
check("...while someone found nowhere on the way is still flagged", ia.problems(plan, ws.situation()) != [])

# ---- "go to smith" keeps its walk
plan = [ActionIntent(kind="move", destination="parth", summary="go"), ActionIntent(kind="talk", target=ws.present[0].id if ws.present else "x", speech="go to smith", summary="x")]
kept = ws.move_to_present("go to smith", plan)
check("'go to smith' is a journey: the walk stays and the line put in someone's mouth goes", [a.kind for a in kept] == ["move"], [a.kind for a in kept])

# ---- refusing to pay is not joining
ws.enter("guild_house")
plan = [ActionIntent(kind="talk", target=clerk.id, speech="", summary="snatching the paper and ink to forge a name in the register")]
check("forcing a name into the register without paying is not a paid joining",
      ws.join_guild_rewrite("*snatch the paper and the ink and force my name in the register without paying*", plan) is None)

# ---- lines that are not for the hire who spoke last
ws.player.party = [{"id": "h1", "name": "Merris Oxwick", "role": "archer", "level": 3, "permanent": True, "temper": ["dry"], "blurb": "an archer"}]
ws.player.party_mode = "with"
def after_merris(line):
    ws._hire_last = ("Merris Oxwick", store.meta.turn - 1)
    return ws.hire_followup(line)
for line in ("*execute the remaining sahuagin slumped against a rock*", "follow sea hag", "turn in all quests", "ask the hermit who he is",
             "*pee on the largest of their kind*", "slap the both of them"):
    check(f"not for the last hire: {line!r}", after_merris(line) is None)
for line in ("tell me more", "No, where are you from?", "*nods at Merris*", "fair enough", "go on"):
    check(f"...still for them: {line!r}", after_merris(line) is not None)

# ---- coins from a fight are already taken
NOTES.clear(); CALLS.clear()
stub.plan = [{"kind": "pick_up", "item": "coins"}]
ws.turn("pick up coins")
check("'pick up coins' with none on the ground says they are in the purse, and no passage is written", NOTES and "already in your purse" in NOTES[-1]
      and not any(t == "Narration" for t, _ in CALLS), (NOTES[-1:], [t for t, _ in CALLS]))
check("the narrator is told what a fight leaves is taken, not left lying", "never left lying" in cp.AFTERMATH_SYSTEM)

# ---- fight orders reach the companion and the ways an order is said
me = combat.fighter_from_character(char)
fen = combat.companion_fighter(world.bestiary["wolf"], 3, "comp_c1", "Fenris")
fen.side = "ally"
merris = party.fighter({"id": "h1", "name": "Merris Oxwick", "role": "archer", "level": 3})
shark = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "e1", "reef shark", "engaged")
f = combat.Combat(fighters=[me, fen, merris, shark], place="x", conditions=[]); f.round = 1
sc = CombatScene.__new__(CombatScene); sc.fight = f
for line, who, kind in (("Fenris, attack the troll", "Fenris", "focus"), ("Fenris attacks the reef shark", "Fenris", "focus"),
                        ("Merris Oxwick, fire a bolt at the reef shark", "Merris Oxwick", "focus"),
                        ("Merris Oxwick, hold down the shark so it does not move", "Merris Oxwick", "focus"),
                        ("Fenris, bite the reef shark and hold it steady", "Fenris", "focus"), ("everyone hold back", None, "hold")):
    r = sc.order_of(line)
    check(f"order: {line!r}", r and r[1] == kind and (who is None or [a.name for a in r[0]] == [who]), r and ([a.name for a in r[0]], r[1]))

# ---- rewrites, invented speech, frames
calls = []
def gen(*a, **k):
    calls.append(a[2])
    return Narration(text="You strike [h1]. The wolf bites [h2]. It is the same old story, again and again, a sense of doom." if len(calls) == 1
                     else "You strike. The wolf bites. [h1] [h2]" if "STALE" in a[2] else "x")
_g = voice.generate
voice.generate = gen
r = voice.fresh("combat_narrate", "sys", "req", Narration, [])
check("a rewrite that loses a blow's marker the draft kept is thrown away: the draft stands", len(calls) == 2 and r.text.startswith("You strike [h1]"), r.text)
calls.clear()
voice.generate = lambda *a, **k: (calls.append(a[2]), Narration(text='The woodcutter looks up. "The wolves took three sheep last week," he says.' if len(calls) == 1 else "He looks up and points north."))[1]
r = voice.fresh("narrate", "sys", "req", Narration, [], said="find the woodcutters and ask about the wolves")
check("a passage that puts words in someone's mouth is written again", len(calls) == 2 and "PUT WORDS IN SOMEONE'S MOUTH" in calls[1] and '"' not in r.text, calls[-1][-200:])
calls.clear()
voice.generate = lambda *a, **k: (calls.append(a[2]), Narration(text='You call out "thank you, Maren" across the square.'))[1]
voice.fresh("narrate", "sys", "req", Narration, [], said="i yell thank you to Maren")
check("...but the player's own words, quoted, are theirs", len(calls) == 1, calls)
voice.generate = _g
try:
    DialogueFrame.model_validate({"before": "ALREADY SHOWN THIS VISIT", "after": "He taps the page."}); framed = ""
except ValidationError as e:
    framed = str(e)
check("a frame that prints a heading of the request is sent back", "heading of the request" in framed, framed[:200])

# ---- Fenris is in the scene, for the interpreter
from engine import truth
kinds = {p.kind: p for p in truth.scene_of(ws).present_people()}
check("the animal companion is in the scene, by name, as the player's own", "companion" in kinds and kinds["companion"].name == "Fenris"
      and "search" in kinds["companion"].note)
check("...not scenery for the narrator", all(l != "Fenris" for l, _, _ in ws.people_view()))
CALLS.clear()
stub.plan = [{"kind": "search", "seek": "sahuagin"}]
ws.turn("have ferris sniff out sahuagin")
asked = next((m[-1]["content"] for t, m in CALLS if t == "ActionPlan"), "")
check("...and the interpreter is shown it, with what telling it to track means", "Fenris" in asked and "sniff out" in asked, asked[-800:])

# ---- two jobs done, one passage, no length
for q in list(ws.player.quests):
    ws.player.quests.remove(q)
for title, cr in (("Hunt 2 boars", "boar"), ("Hunt 2 wolves", "wolf")):
    q = quests._quest("hunt", "F", title, ws.minutes, place="greywood", creature=cr, count=2)
    q["progress"] = 2; q["result"] = f"the {cr}s are gone from the Greywood"
    ws.player.quests.append(q)
ws.player.party = []
CALLS.clear()
stub.plan = [{"kind": "talk", "target": clerk.id, "speech": "Both done."}]
ws.turn("I hand in both contracts")
narr = [m[-1]["content"] for t, m in CALLS if t == "Narration"]
check("two jobs handed in together are told in one passage", len([n for n in narr if "THE JOB IS DONE" in n]) == 1, len(narr))
check("...with no length asked of it", narr and "sentence or two" not in " ".join(narr))

store.close()
shutil.rmtree("saves/playthrough3_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
