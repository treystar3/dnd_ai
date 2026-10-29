"""(f375) What people are doing and what the streets look like are plain facts the narrator is given, not material for everyone who
speaks; and nobody is given a length. The playthrough after the voice work had a woman 'binding a goose feather to a shaft between her
teeth', a smith holding 'a restless horse steady against an anvil' and 'drivers gathered outside the inn': engine-written fragments,
handed to every speaker as facts, reworded and scrambled."""
import random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import ui.console as uc
for f in ("narrate", "note", "say", "npc_says", "dialogue"):
    setattr(uc, f, lambda *a, **k: None)
import config
from engine import doings, truth, voice_rules
from npc import prompts as npr
from npc.traits import load_traits
from scenes import combat_prompts as cp, party_prompts as pp, world_prompts as wp
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the doings are plain facts
lines = list(doings.D["anyone"]) + [e["text"] for r in doings.D["by_role"] for e in doings.entries(r)]
check("every doing is two to five words, with no second clause, no figure and no pronoun",
      all(2 <= len(t.split()) <= 5 and "," not in t and not re.search(r"\b(as if|like a|his|her|him|she|he|their|them)\b", t) for t in lines))
check("the hunter fletches arrows and the smith shoes a horse, and nothing more is said of it",
      "fletching arrows" in [e["text"] for e in doings.entries("hunter")] and "shoeing a horse" in [e["text"] for e in doings.entries("smith")])
busy = voice_rules.V["stances"]["busy"]["text"]
check("a busy person's stance does not quote their chore back to them", "{activity}" not in busy)

# ---- a scene in Parth's guild hall at mid-morning
world = load_world()
shutil.rmtree("saves/plain_world_test", ignore_errors=True)
store = CampaignStore.open_or_create("plain_world_test")
store.meta.seed = 3; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("guild_house")
people = [n for n in ws.present]
check("people are present, each doing something", len(people) >= 2 and all(n.activity for n in people), [(n.label(), n.activity) for n in people])
a, b = people[0], people[1]
sc = truth.scene_of(ws)
theirs = sc.view(truth.viewer_for_npc(a, world), "townsfolk")
check("a townsperson is not told what the others here are doing", b.activity not in theirs.text() and any(b.name in l or b.label() in l for l in theirs.lines("present")),
      theirs.lines("present"))
check("...nor is Maren or a hire", b.activity not in sc.view(truth.MAREN, "maren").text() and b.activity not in sc.view(truth.viewer_for_hire("hire:x"), "hire").text())
check("the narrator is", any(b.activity in l for l in sc.view(truth.NARRATOR, "narrator").present_lines()))
check("...and so is the reader of the player's words, so 'the one shoeing the horse' finds them",
      any(b.activity in l for l in sc.view(truth.INTERPRETER, "narrator").present_lines()))
p = npr.conversation_prompt(a, world.places["guild_house"], [], [], [], "hello", [], [], [], truth_text=theirs.text()).render()
check("the person's own doing is theirs, as RIGHT NOW", f"RIGHT NOW: {a.activity}" in p)

# ---- the streets: the narrator's, and a speaker's only when asked
streets = sc.view(truth.NARRATOR, "narrator").streets()
crowd = next((l for l in streets if l.startswith("Outside: ")), "")[len("Outside: "):]
check("the narrator has Parth's own street line, as a plain sentence", crowd and crowd in (world.places["parth"].crowd or {}).values(), (streets, world.places["parth"].crowd))
check("...and Parth's busy hours say cart drivers, not drivers", "cart drivers are eating in the inn" in world.places["parth"].crowd["market"])
quiet = sc.view(truth.viewer_for_npc(a, world), "townsfolk")
check("a townsperson asked an ordinary thing is not told the street scene", crowd not in quiet.text())
asked = sc.view(truth.viewer_for_npc(a, world), "townsfolk").asking("what's going on in town today?")
check("...asked about the town, they are", crowd in asked.text())
check("...and so are Maren and a hire, when asked", crowd in sc.view(truth.MAREN, "maren").asking("busy out there?").text()
      and crowd not in sc.view(truth.MAREN, "maren").asking("how did you learn to fight?").text()
      and crowd in sc.view(truth.viewer_for_hire("hire:x"), "hire").asking("is the square crowded?").text())
check("what counts as asking about the streets", truth.streets_asked("Is the market busy?") and truth.streets_asked("what's going on outside")
      and not truth.streets_asked("who taught you the sword?"))
check("no crowd line anywhere runs as a compressed phrase", all(v.endswith(".") and v[0].isupper() for s in truth.T["crowd"].values() for v in s.values()))

# ---- nobody is given a length
req = wp.narration_request("t", world.places["guild_house"], ws.people_view(), "x", "y")
frame = wp.dialogue_request("t", world.places["guild_house"], [], "x", "l", "d", "m", False, "hi", "yes", "", False, [])
fight = cp.narrate_request("P", "t", "swing", ["x [h1]"], "sword", "fine", ["a wolf"], 2)
check("no request to the narrator, a frame or the fight carries a length", not any("LENGTH" in r for r in (req, frame, fight)))
check("no system prompt for the narrator, frames, fights, townsfolk or hires names a length",
      not any(re.search(r"LENGTH|\bwords?\b.*\bat most\b|one to (three|four) short sentences|in a sentence or two|say less", s)
              for s in (wp.NARRATOR_SYSTEM, wp.DIALOGUE_SYSTEM, wp.EXCHANGE_SYSTEM, cp.NARRATE_SYSTEM, cp.AFTERMATH_SYSTEM, cp.START_SYSTEM,
                        npr.CONVERSATION_SYSTEM, pp.TALK_SYSTEM)))
check("the length tables are gone and one ceiling stops a runaway", "narration" not in voice_rules.V and "npc" not in voice_rules.V
      and config.PROSE_MAX_TOKENS >= 2048 and not hasattr(voice_rules, "npc_level"))
from llm.contracts import CompanionReply, Parting
check("a long reply from a hire and a long parting are accepted", bool(Parting.model_validate({"speech": "word " * 40}))
      and bool(CompanionReply.model_validate({"speech": "A long answer. " * 80, "gesture": ""}, context={"member": {"name": "Bram", "said": []}, "gesture_state": {}})))

store.close()
shutil.rmtree("saves/plain_world_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
