"""(f413) The owner's recorded decisions, kept. The f395 review found the code still breaking five of them: sentence counts in the road
writer's and two narrations' prompts against "no length limits" (f375); a long walk left untold when a road happening was on it or the
place had been seen (f408); dashes in the story the narrator is handed to copy (f403); a companion's errand asked in words straight from
the data, with no accent (f410); Maren's rest habit on a line of its own (f412)."""
import ast, pathlib, random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 6))
import ui.console as uc
NARR, SAID = [], []
uc.narrate = lambda t, *a, **k: NARR.append(str(t))
uc.say = lambda t, speaker="", *a, **k: SAID.append((speaker, str(t)))
uc.dialogue = lambda before, speaker, speech, after="", *a, **k: SAID.append((speaker, str(speech)))
uc.panel = lambda name, data: False
from engine import combat, quirks, road_prompts
from llm.contracts import Narration
from npc.traits import load_traits
from scenes import combat_prompts as cp, party_prompts as pp, voice, world_prompts as wp
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
import npc.prompts as npcp

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- f375: no length on what the narrator or a speaker writes
COUNT = re.compile(r"\b(?:one|two|three|four|five|six)(?: or (?:two|three|four))? sentences\b|\bfour to six\b|\bbriefly\b", re.I)   # a count of sentences, not 'one sentence tells one blow'
prose_prompts = {"DM_VOICE": voice.DM_VOICE, "NARRATOR_SYSTEM": wp.NARRATOR_SYSTEM, "DIALOGUE_SYSTEM": wp.DIALOGUE_SYSTEM,
                 "EXCHANGE_SYSTEM": wp.EXCHANGE_SYSTEM, "NARRATE_SYSTEM": cp.NARRATE_SYSTEM, "AFTERMATH_SYSTEM": cp.AFTERMATH_SYSTEM,
                 "START_SYSTEM": cp.START_SYSTEM, "TALK_SYSTEM": pp.TALK_SYSTEM, "CONVERSATION_SYSTEM": npcp.CONVERSATION_SYSTEM}
road_prose = "\n".join(l for l in road_prompts.SYSTEM.split("\n  ") if l.startswith(("journey:", "scene:")))
prose_prompts["road journey and scene"] = road_prose
found = {k: COUNT.search(v).group(0) for k, v in prose_prompts.items() if COUNT.search(v)}
check("no narrator's or speaker's prompt sets a length (f375)", not found and "journey:" in road_prose, found)
asks = []
for p in list(pathlib.Path("engine").rglob("*.py")) + list(pathlib.Path("scenes").rglob("*.py")):
    for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in ("narrate", "narrate_with", "_narrate_now"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and COUNT.search(sub.value):
                    asks.append(f"{p}:{sub.lineno} {COUNT.search(sub.value).group(0)}")
check("...nor any event the game hands the narrator", not asks, asks)

# ---- a scene to walk and rest in
shutil.rmtree("saves/decisions_413_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("decisions_413_test")
store.meta.seed = 4; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("mage", random.Random(1))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("parth")

# ---- f408: a long walk is always told
road = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places)
asked = []
real_narrate = ws.narrate
ws.narrate = lambda event, text="", *a, **k: asked.append(event)
ws.revisit, ws.first_arrival = True, False
ws.quiet_return = lambda *a, **k: True                     # somewhere seen, with nothing new: before, a long walk ended in a bare line
NARR.clear()
ws.finish_journey([road.from_, road.to], 180, "I walk on", [])
check("a long walk back to a place already seen is still told", asked and "Tell the walk itself" in asked[-1]
      and not any("you are back at" in t.lower() for t in NARR), (asked[-1:], NARR[-2:]))
asked.clear()
ws.finish_journey([road.from_, road.to], 20, "I walk on", [])
check("...a short one back to it is a line, as before", not asked and any("you are back at" in t.lower() for t in NARR), NARR[-2:])
ws.quiet_return = lambda *a, **k: False
asked.clear()
ws.finish_journey([road.from_, road.to], 180, "I walk on", ["The Ford: a ford, swollen."])
check("...and a long walk with a happening on it tells the walk too, but not the happening again", asked and "Tell the walk itself" in asked[-1]
      and "do not tell it again" in asked[-1], asked[-1:])
ws.narrate = real_narrate
ws.enter("parth")

# ---- f403: the story the narrator is handed has no dashes
f = types.SimpleNamespace(story=[])
combat.tell(f, "the blow the troll was winding up never falls - it is left open")
check("a fight's story line reaches the narrator with no dash", f.story and " - " not in f.story[0], f.story)
got = []
import scenes.world as W
real_fresh = W.fresh
W.fresh = lambda task, system, request, *a, **k: (got.append(request), Narration(text="You look around."))[1]
ws._narrate_now("Show the finding as it would be seen, and stop there - no conclusions.")
check("...and so does an event in the world", got and "GAME EVENT:" in got[-1] and " - " not in got[-1].split("GAME EVENT:")[1].split("\n")[0], got[-1][-300:])
check("...and the companions' habits heading carries none", " - " not in wp.HABITS_HEAD)

# ---- f412: Maren's rest habit is in the rest's passage
ws.mentor_with_you = lambda: True
ws._habits_due = {}
for k in range(40):
    store.meta.minutes = 2000 + k * 17
    ws.mentor_rest_habit()
    if ws.__dict__.get("_habits_due", {}).get("rest"):
        break
got.clear(); NARR.clear()
ws._narrate_now("The player rests.")
check("Maren's small attention at a rest goes into the rest's passage", got and wp.HABITS_HEAD in got[-1] and "Maren" in got[-1].split(wp.HABITS_HEAD)[1][:300],
      got[-1][-500:] if got else "")
check("...and is never a line of its own", not any(t.startswith("Maren") for t in NARR), NARR)
W.fresh = real_fresh

# ---- f410: a companion asks their errand in their own voice
hire = {"id": "h1", "name": "Bram Voss", "role": "fighter", "level": 3, "permanent": True, "rank": "F", "bond": 60, "pronoun": "he",
        "motive": "protect", "memories": [], "said": [], "talk": [], "blurb": "a scarred sellsword"}
quirks.roll(hire, random.Random(3))
ws.player.party = [hire]
ws.player.party_mode = "with"
hall = next(p.id for p in world.places.values() if p.type == "guild")
ws.enter(hall)
voiced = []
ws.companion_line = lambda m, now, heard, *a, **k: (voiced.append(now[0]), "There's a courier here, aye. An hour, to send coin home?")[1]
SAID.clear()
ws.errands()
check("an errand is asked through the companion's own voice, with their accent, not read from the data", voiced and "courier" in voiced[-1]
      and any("aye" in t for _, t in SAID), (voiced, SAID))
check("...never word for word from the data", not any(t == quirks.Q["errands"]["protect"]["ask"] for _, t in SAID), SAID)

# ---- (found by the suite) a spell book found after a fight is summed up, not a crash
from engine import items, spells
book = next((b for b in (spells.book_drop(20, "normal", random.Random(s)) for s in range(500)) if b), None)
check("a spell book found after a fight has a summary line", book is not None and items.summary(book).startswith("spell book"),
      items.summary(book) if book else "no book")

store.close()
shutil.rmtree("saves/decisions_413_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
