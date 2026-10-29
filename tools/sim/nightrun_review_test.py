"""(f386) What a blank-slate read of a night's seven runs found (f375 build), and what still held on f385.
- Words to the whole party swallowed the move they asked for: "We need to head toward the Ironcrown Peaks" became a talk to each of
  three hires, which filled the three-actions limit and pushed the move off the end; "Let's keep moving toward Parth" went to the hire
  who spoke last as chat; "head back to the adventurers' guild house" was read as party business ("your party moves beside you"); and
  "may I search the tidepools for the crabs now?" was answered "go ahead" twenty-two times. 55% of the bot's travel lines went nowhere.
- Targets the scene showed were ruled 'not here': 'wildlife:hippogriff (elite)', 'wildlife: raven', a misspelt id, a prisoner at the
  player's side in another place.
- Gestures were rolled as gambles that changed the world: leaning on a wall barred the guild house to the player for twenty turns,
  pulling a cloak tight was a block, sleeping was hiding, spitting was a signal the town talked of.
- Nobody knew whether the player was a man or a woman: sir, madam, lad and lass, two in one turn.
- Companions flooded turns (14 lines in one), told what they were holding turn after turn, showed one habit twenty times, and asked
  one errand six times after it was agreed to."""
import random, re, shutil, sys, types
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
from engine import combat, party, pulse, quirks, truth, world_improv
from llm.contracts import ActionIntent, ActionPlan, CompanionReply, Exchange
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/nightrun_review_test", ignore_errors=True)
store = CampaignStore.open_or_create("nightrun_review_test")
store.meta.seed = 3; store.meta.minutes = 600; store.meta.turn = 1; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.concept, char.class_summary = "", ""
store.save_player(PlayerState(character=char, location="trading_square", guild_rank="E"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("trading_square")
offers = party.roster(3, "guild_house", 0, 5, 100, [])[:3]
ws.player.party = [party.new_hire(o, 5, 0) for o in offers]
ws.player.party_mode = "with"
hids = [f"hire:{m['id']}" for m in ws.player.party]

# ---- 1. words to the party
said = "We need to head toward the Ironcrown Peaks."
read = ActionPlan.model_validate({"actions": [{"kind": "talk", "target": h, "speech": said} for h in hids] +
                                            [{"kind": "move", "destination": "ironcrown_peaks"}]})
check("the same words to each of the party are one talk: the move they asked for is not pushed off the end",
      [a.kind for a in read.actions] == ["talk", "move"] and not read.dropped, [a.kind for a in read.actions])
plan = ws.party_word(said, [ActionIntent(kind="talk", target=hids[0], speech=said)])
check("a proposal to go somewhere, read as talk to them, is the move to the place it names", [(a.kind, a.destination) for a in plan] == [("move", "ironcrown_peaks")],
      [a.model_dump(exclude_defaults=True) for a in plan])
plan = ws.party_word("May I begin searching the tidepools for the Giant Crabs now?", [ActionIntent(kind="talk", target=hids[1], speech="May I begin?")])
check("...asking leave to search is searching, for what it names", [(a.kind, a.seek) for a in plan] == [("search", "Giant Crabs")], [a.model_dump(exclude_defaults=True) for a in plan])
plan = ws.party_word("Should we go to Parth or Redstone?", [ActionIntent(kind="talk", target=hids[0], speech="Should we go to Parth or Redstone?")])
check("...while asking them to choose stays a question for them", [a.kind for a in plan] == ["talk"])
check("'Let's keep moving toward Parth' goes to Parth", ws.place_in_words("keep moving toward Parth") == "parth")
for line in ("We need to push ahead toward the Ironcrown Peaks.", "Let's keep moving toward the Ironcrown Peaks.", "We should start heading toward the Ironcrown Peaks now.",
             "Let's move out toward the Ironcrown Peaks.", "Let’s keep moving forward toward Parth.", "May I begin searching the tidepools for the Giant Crabs now?"):
    ws._hire_last = (ws.player.party[0]["name"], store.meta.turn - 1)
    check(f"not chat for the hire who spoke last: {line!r}", ws.hire_followup(line) is None)
for line in ("tell me more", "No, where are you from?", "fair enough", "go on"):
    ws._hire_last = (ws.player.party[0]["name"], store.meta.turn - 1)
    check(f"...still for them: {line!r}", ws.hire_followup(line) is not None)
real_read = ws.party_read
ws.party_read = lambda text, offered: types.SimpleNamespace(kind="with", target="")
NOTES.clear()
check("'head back to the adventurers' guild house' is not party business", ws.party_turn("head back to the adventurers' guild house") is False and not NOTES, NOTES)
check("...and 'the party comes with me' when they already are is not either", ws.party_turn("my party and I head to the inn") is False and not NOTES, NOTES)
ws.party_read = real_read
from scenes import world_prompts as wp
check("the interpreter is told a proposal is the player doing it", "is the player doing it" in wp.INTERPRET_SYSTEM and "ONE talk, to one of them" in wp.INTERPRET_SYSTEM)

# ---- 2. targets
ws.enter("guild_house"); ws.apply_backfill()
first = ws.clerk_here() or ws.present[0]
typo = first.id[:3] + first.id[3:].replace(first.id[4], first.id[4] + "x", 1)            # 'bixdie_wigglewick' for 'bixie_wigglewick'
check("a target near enough to someone here is them: a slip of the pen", ws.settle_target(typo) == first.id, (typo, first.id))
check("...their name or how the player knows them", ws.settle_target(first.label()) == first.id and ws.settle_target(f"the {first.label()}") == first.id)
wolf = world.bestiary["wolf"]
ws.wildlife = (wolf, [combat.fighter_from_creature(wolf, 3, "elite", "e1", "hippogriff (elite)", "far")])
check("'wildlife:hippogriff (elite)' and 'wildlife: raven' are the creature that is about", ws.settle_target("wildlife:hippogriff (elite)") == "wildlife"
      and ws.settle_target("wildlife: raven") == "wildlife")
plan = ws.repair("attack the hippogriff", [ActionIntent(kind="attack", target="wildlife:hippogriff (elite)")])
check("...as a repair, before the audit sees it", [a.target for a in plan] == ["wildlife"], [a.model_dump(exclude_defaults=True) for a in plan])
check("...and someone not here is still as written", ws.settle_target("no_such_person_at_all") == "no_such_person_at_all")
ws.wildlife = None
npc = ws.make_prisoner("Hob", "", tip=False, named=False, kind="bandit")
store.save_npc(npc)
ws.player.prisoners[npc.id]["escort"] = True
ws.enter("greywood")
check("a prisoner the player walked elsewhere is still at their side", any(n.id == npc.id for n in ws.present))
ws.player.prisoners.pop(npc.id, None)
ws.enter("trading_square")


# ---- 3. gestures
for line in ("I lean against the wall and just watch the shadows.", "Pulling my cloak tight against the wind", "I stand up and wipe my hands",
             "I spit on the floor", "I tighten my grip on my blade"):
    check(f"a gesture is shown, not rolled: {line!r}", world_improv.read_effect(line) == "pose", world_improv.read_effect(line))
check("...while barring a door is still a block, and hiding a thing still hiding", world_improv.read_effect("I bar the gate behind us") == "block"
      and world_improv.read_effect("I hide the letter under the floorboard") == "hide")
marks = list(store.load_place("trading_square").marks)
NOTES.clear(); ws.ran = []
stub.plan = [{"kind": "other", "summary": "leaning against the wall and watching the shadows"}]
ws.turn("I lean against the wall and just watch the shadows.")
check("...and leaves nothing behind: no mark, nothing barred", store.load_place("trading_square").marks == marks
      and not pulse.closed_reason(store, "trading_square", ws.minutes + 1), store.load_place("trading_square").marks[-2:])
real = world_improv.read_effect
from engine import checks
real_roll = checks.roll
world_improv.read_effect = lambda w: "block"
checks.roll = lambda odds, *a, **k: ("success", 1)
world_improv.resolve(ws, "bar the gate with the cart", "I bar the gate with the cart")
world_improv.read_effect, checks.roll = real, real_roll
check("a way the player barred themselves never bars them", pulse.closed_reason(store, "trading_square", ws.minutes + 1) == "")
check("...and the world tells it as theirs", any("barred the way here themselves" in h for h in pulse.happenings_at(store, world, "trading_square", ws.minutes + 1)))
before = ws.minutes
stub.plan = [{"kind": "other", "summary": "going to sleep"}]
ws.turn("I go to sleep")
check("going to sleep is a rest, not a gamble rolled as hiding", ws.minutes - before >= 50 and not any("hidden here" in m for m in store.load_place("trading_square").marks),
      ws.minutes - before)

# ---- 4. the player as the world sees them
c = ws.player.character
for words, want in (("a mountain of a man who beats drums", "he"), ("She is a wandering healer with her own herbs", "she"), ("a drifting spearman hunter", "they")):
    c.pronoun, c.concept, c.class_summary = "", words, ""
    check(f"read from their own words: {words!r} -> {want}", truth.player_pronoun(c) == want, c.pronoun)
c.pronoun, c.concept = "", "a mountain of a man"
seen = truth.scene_of(ws).view(truth.viewer_for_hire(hids[0]), "hire").text()
check("a hire sees whether the player is a man or a woman", "is a man" in seen, seen[-300:])
check("...and so do the townsfolk, Maren and the party among themselves", all("player" in truth.T["profiles"][k] for k in ("townsfolk", "maren", "banter", "hire")))
ws.command("#pronoun they")
check("'#pronoun they' sets it, and they are then called nothing that says", c.pronoun == "they"
      and "no sir, madam, lad or lass" in truth.scene_of(ws).view(truth.viewer_for_hire(hids[0]), "hire").text())
ws.command("#pronoun she")
check("...and '#pronoun she' too", c.pronoun == "she")

# ---- 5. the party's talk
def reply(speech, said=""):
    try:
        CompanionReply.model_validate({"speech": speech, "gesture": ""}, context={"said": said}); return ""
    except ValidationError as e:
        return str(e)
check("a companion who tells what they are holding is sent back", "nobody asked" in reply("I have my staff gripped tight, ready for anything."))
check("...unless the player asked about it", reply("I have my staff, yes.", "do you have your staff?") == "")
def ex_err(lines):
    try:
        Exchange.model_validate({"lines": [{"speaker": a, "text": b} for a, b in lines]}, context={"speakers": ["A B", "C D"], "lines": (2, 4), "material": []}); return ""
    except ValidationError as e:
        return str(e)
check("...and in talk among them", "tells what they are holding" in ex_err([("A B", "I am holding this shield tight."), ("C D", "Good, keep it up.")]))
m = ws.player.party[0]
m.setdefault("quirks", {})["habit"] = next(iter(quirks.Q["habits"]))
shown = 0
for day in range(60):
    m["quirks"]["habit_day"] = -1
    shown += bool(quirks.habit_line(m, quirks.Q["habits"][m["quirks"]["habit"]]["when"], random.Random(day), day=day, place_type="town", danger=True))
check("a habit seen often is seen less (not twenty times in a night)", 3 <= shown <= 20, shown)
SAID = []
ws.party_banter = lambda crew, kind="travel": SAID.append(kind) or True
ws._banter_due = ""; ws._banter_loc = "parth"; ws._banter_last = -10 ** 9
ws.note_party_said(3)
ws.player.location = "greywood"
ws.banter_tick(); ws.player.location = "trading_square"
check("after a turn that already showed several companion lines, no more talk among them", SAID == [], SAID)
q = m["quirks"]
q.pop("errand", None); q["target"] = "Ferris Vane"; q.pop("errand_ignored", None)
E = {"ask": "x", "yes_line": "Fine.", "no_line": "No.", "memory_yes": "yes", "memory_no": "no", "where": "town"}
ws._errand = (m, E)
ws.errand_intercept("Sure, Fenna, let's go ask about Ferris Vane")
check("a yes that goes on about the errand itself is that yes", q.get("errand") == "yes", q.get("errand"))
q.pop("errand", None)
for _ in range(2):
    ws._errand = (m, E)
    ws.errand_intercept("Okay, let's head to the inn first")
check("an ask left unanswered twice is let go for good", q.get("errand") == "let go" and quirks.errand(m) is None, q.get("errand"))

store.close()
shutil.rmtree("saves/nightrun_review_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
