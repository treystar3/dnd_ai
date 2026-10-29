"""(f368) The night bot plays with goals: a contract is taken to its place, hunted, carried back and reported; a situation the world brought
to the player is followed to one of its paths; the level band is judged by the roads' wilds as the game rolls them; a death sends it home
and keeps it away; personas weight what it cares about; its words pick up the passage before; the summary measures all of it."""
import json, random, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 1)
simlib.install(stub)
sys.path.insert(0, "tools")
import nightbot
from nightbot import PERSONAS, ROTATION, Bot, notable, refers_to
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- personas
check("every persona in the rotation exists, with its band, its talk turns and its weights", set(ROTATION) <= set(PERSONAS)
      and all({"text", "band", "talk", "job", "doors", "hunt", "roam", "trade", "chat", "improv", "indoors"} <= set(v) for v in PERSONAS.values())
      and PERSONAS["hunter"]["band"] > PERSONAS["steady"]["band"] > PERSONAS["careful"]["band"], PERSONAS.keys())
check("a seed picks a persona, in turn", [nightbot.persona_for(s) for s in (1, 2, 6)] == [ROTATION[0], ROTATION[1], ROTATION[0]])

# ---- the words: what a passage gives a player to pick up
passage = "The smith, Bram Hollis, wipes his hands. \"The mill's been quiet since Tam left for Willowmead,\" he says. You wait."
check("the notable words of a passage are its names, not its sentence openers", {"bram", "hollis", "tam", "willowmead"} <= notable(passage)
      and not ({"the", "you"} & notable(passage)), notable(passage))
check("a line that picks up a name refers to the passage; a stock line does not", refers_to("I ask Bram where Tam went.", passage, [])
      and refers_to("I go over to the smith.", passage, ["the soot-stained smith"]) and not refers_to("I look around.", passage, []))

from llm.contracts import PlayerLine
ok = PlayerLine.model_validate({"line": "  I head   to Parth. "}, context={"must_name": ["Parth"]})
check("the player's line is tidied and must carry the names the goal turns on", ok.line == "I head to Parth.")
for text, why in (("I head to Willowmead.", "must name Parth"), ("The player walks to Parth.", "third person"), ("", "empty"), ("I " + "walk " * 50 + "to Parth.", "too long")):
    try:
        PlayerLine.model_validate({"line": text}, context={"must_name": ["Parth"]})
        check(f"a line is refused: {why}", False)
    except Exception:
        check(f"a line is refused: {why}", True)

# ---- a scene to play in
from engine import pulse
from npc.traits import load_traits
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from world.loader import load_world
world = load_world(); catalog = load_traits()
shutil.rmtree("saves/nightbot_test", ignore_errors=True)
store = CampaignStore.open_or_create("nightbot_test"); store.meta.seed = 11; store.meta.minutes = 10 * 60; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
from engine import leveling
leveling.level_up(char, 12)
player = PlayerState(character=char, location="parth", guild_rank="E")
store.save_player(player)
ws = WorldScene(store, world, catalog, store.load_player())
ws.player.mentor["never"] = True
stub.plan = [{"kind": "look"}]
ws.turn("I look around.")                                   # the scene is entered: people are here
bot = Bot(ws, world, random.Random(5), stub, persona="steady")
stub.bot = bot

# ---- the band, judged by the roads' wilds
check("a wild place fits when its creatures top out near the level; one far above does not", bot.fits("greywood") and bot.fits("south_fields")
      and not bot.fits("hollow_barrows") and bot.fits("parth"), (bot.c.level, bot.P["band"]))
check("a road is judged by the wild places its trouble comes from: Parth to Willowmead yes, Riverhaven to Lethoria no, at level 13",
      bot.leg_ok("parth", "willowmead") and not bot.leg_ok("riverhaven", "lethoria"))
check("a route to a far town is refused when a road on the way is above the band; a near one is given",
      bot.route("frostholm") is None and bot.route("willowmead") == ["willowmead"] and bot.route("parth") == [], (bot.route("frostholm"), bot.route("willowmead")))
bot.avoid["greywood"] = ws.minutes + 1440
check("a place kept away from does not fit, until the time passes", not bot.fits("greywood"))
bot.avoid.clear()

# ---- a contract, from the posting to the pay
from engine import encounters, quests
roster = encounters.ensure_roster(store, world, "greywood")
creature = world.bestiary[roster[0]]
q = {"id": "q_test", "title": f"Hunt 2 {quests.plural(creature.name)} in the Greywood", "kind": "hunt", "letter": "F", "guild": True, "issuer": "guild",
     "issuer_name": "the guild", "count": 2, "progress": 0, "coins": 100, "xp": 10, "deadline": ws.minutes + 20 * 1440, "posted": ws.minutes,
     "place": "greywood", "creature": creature.id}
ws.player.quests.append(q)
bot.hall_of["q_test"] = "guild_house"
text, kind = bot.decide()
check("a held contract becomes the goal: the bot sets out for the place on the posting", kind == "move" and "Greywood" in text and bot.meta["goal"] == "contract:hunt"
      and stub.plan[0] == {"kind": "move", "destination": "greywood"}, (text, bot.meta, stub.plan))
check("the row carries the goal, the persona, where the line came from and whether it picked up the passage",
      {"goal", "persona", "source", "refers", "band", "bot_seconds"} <= set(bot.meta) and bot.meta["source"] == "template" and bot.meta["persona"] == "steady", bot.meta)
ws.player.location = "greywood"
text, kind = bot.decide()
check("at the place it hunts: a search for the creature on the posting", kind == "search" and quests.plural(creature.name).lower() in text.lower()
      and stub.plan[0].get("seek") == creature.name, (text, stub.plan))
q["progress"] = 2
text, kind = bot.decide()
check("the contract done, it carries it back to the hall it was taken from", kind == "move" and stub.plan[0].get("destination") == "guild_house"
      and bot.meta["goal"] == "report" and bot.stats["goals_done"]["contract"] == 1, (text, bot.meta, bot.goals))
ws.player.location = "guild_house"
ws.enter("guild_house")
clerk = ws.clerk_here()
if clerk is None:                                           # after hours: the bot waits for the clerk; bring one in to see the report
    from npc.life import populate_place
    clerk = next((n for n in populate_place(store, world, "guild_house", catalog, first_batch=None) if n.role == "guild_clerk"), None)
    if clerk is not None:
        ws.present = list(ws.present) + [clerk]
text, kind = bot.decide()
check("at the hall it reports to the clerk, who pays (the game's turn-in runs on the line)", clerk is not None and kind == "talk" and stub.plan[0].get("target") == clerk.id
      and "done" in text, (text, stub.plan, [n.role for n in ws.present]))

# ---- a situation the world brought to the player: a path to persuade someone here
ws.player.quests.clear()                                    # the test contract is over with; a new bot would otherwise go and report it
ws.player.location = "parth"
ws.enter("parth")
from npc.life import populate_place
folk = populate_place(store, world, "parth", catalog, first_batch=None)
npc = next((n for n in folk if n.role != "guild_clerk"), folk[0])
ws.present = [npc] + [n for n in ws.present if n.id != npc.id]
state = store.load_world_state() or pulse.empty_state(ws.minutes)
th = {"id": "th_test", "title": "The Quiet Mill", "tier": "uncommon", "place": "parth", "status": "active", "touched": True, "made": ws.minutes - 1440,
      "stage": 0, "stages": [{"name": "Silence", "description": "The mill wheel has stopped."}], "times": [ws.minutes - 1440], "told": True,
      "paths": [{"id": "talk_" + npc.id, "name": "Talk them round", "how": f"Ask {npc.label()} to open the mill again", "kind": "persuade", "target": npc.id, "spawn": "", "done": False}]}
state.setdefault("threads", []).append(th)
store.save_world_state(state)
talker = Bot(ws, world, random.Random(9), stub, persona="talker")
talker.here_for = 3                                         # been here a while: a bot just arrived may ask around first
stub.bot = talker
text, kind = talker.decide()
check("a situation the player has met is followed: the persuade path becomes a talk with a persuasion check on the one named",
      kind == "talk" and stub.plan[0].get("target") == npc.id and stub.plan[0].get("checks") == ["persuasion"] and talker.meta["goal"] == "follow:persuade"
      and talker.stats["doors_seen"] == 1 and talker.stats["doors_followed"] == 1, (text, stub.plan, talker.meta, talker.goals))
state = store.load_world_state()
state.setdefault("deeds", []).append({"kind": "persuade", "minute": ws.minutes, "place": "parth", "npc": npc.id, "degree": "strong success"})
store.save_world_state(state)
ws.partner = None
text, kind = talker.decide()
check("once the path is met the goal is done and the bot moves on", talker.stats["goals_done"].get("persuade") == 1 and not any(g["kind"] == "persuade" for g in talker.goals), (talker.goals, talker.stats["goals_done"]))

# ---- a death sends it home and keeps it away
bot2 = Bot(ws, world, random.Random(3), stub, persona="hunter")
stub.bot = bot2
bot2.goals.append({"kind": "hunt", "place": "hollow_barrows", "tries": 0})
bot2.last_loc = "hollow_barrows"
ws.player.location = "greywood"
ws.player.character.deaths += 1
text, kind = bot2.decide()
check("a death: the hunt is dropped, the place is kept away from, and the bot heads home", bot2.stats["deaths"] == 1 and bot2.stats["deaths_above_band"] == 1
      and "hollow_barrows" in bot2.avoid and bot2.stats["goals_dropped"]["hunt"] == 1 and bot2.meta["goal"] == "retreat" and stub.plan[0].get("destination") == "parth",
      (text, bot2.meta, bot2.goals, bot2.avoid))

# ---- the summary's measures of play
tmp = Path(tempfile.mkdtemp())
rows = [{"n": 1, "kind": "talk", "text": "I ask Bram about the mill.", "where": "Parth", "goal": "follow:persuade", "source": "model", "refers": True, "level": 13, "deaths": 0},
        {"n": 2, "kind": "talk", "text": "\"Who runs things here?\"", "where": "Parth", "goal": "idle:talk", "source": "template", "refers": False, "level": 13, "deaths": 0},
        {"n": 3, "kind": "wait", "text": "I wait an hour.", "where": "Parth", "goal": "idle:wait", "source": "template", "refers": False, "level": 13, "deaths": 0},
        {"n": 4, "kind": "wait", "text": "I wait an hour.", "where": "Parth", "goal": "idle:wait", "source": "template", "refers": False, "level": 13, "deaths": 1}]
(tmp / "turns.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
(tmp / "pulse.jsonl").write_text(json.dumps({"kind": "end", "how": "player", "t": 1}) + "\n" + json.dumps({"kind": "end", "how": "settled", "t": 2}) + "\n", encoding="utf-8")
(tmp / "run.json").write_text(json.dumps({"character": "Tam", "class": "warrior", "level": 13, "deaths": 1, "turns": 4, "hours": 0.1, "reason": "turn limit (4)", "start": "green",
                                           "persona": "talker", "bot": {"contracts_taken": 2, "contracts_done": 1, "doors_seen": 3, "doors_followed": 2, "deaths_above_band": 1,
                                                                        "goals_done": {"contract": 1}, "goals_dropped": {"go": 2}, "places": 5, "fights": 1, "model_failed": 0, "model_seconds": 3.2}}), encoding="utf-8")
import latency
text = latency.summarise(tmp)
check("summary.md measures the play: distinct lines, lines picking up the passage, contracts, situations, goals, deaths above the band, waits",
      "## Play" in text and "| Distinct lines | 3 of 4 (75%) |" in text and "| Lines the model wrote | 1 (template 3" in text
      and "1 of 4 (25%); in talk 1 of 2 (50%)" in text and "| Contracts taken / finished | 2 / 1 |" in text
      and "| Situations met / followed / ended by the player | 3 / 2 / 1 |" in text and "| Goals finished / given up | 1 / 2 (contract 1/0, go 0/2) |" in text
      and "| Deaths (above the level band) | 1 (1) |" in text and "| Waits | 2 of 4 (50%) |" in text and "playing as talker" in text
      and "Turns by goal: idle 3, follow 1" in text, text)
# ---- (f391) a refusal said twice gives the goal up; a person is never asked the same thing twice
import types
b3 = Bot(ws, world, random.Random(4), stub, persona="steady")
b3.goals = [{"kind": "go", "place": "parth", "tries": 0}]
b3.run = types.SimpleNamespace(turn_notes=["The way through the Cracked Plains is closed: The Weeping Standing Stone."])
b3.read_refusals()
check("one refusal is not yet a reason to give up", len(b3.goals) == 1)
b3.read_refusals()
check("the same refusal twice running gives the goal up and keeps away from its place for a day",
      not b3.goals and b3.stats["blocked"] == 1 and b3.avoid.get("parth", 0) > ws.minutes, (b3.goals, b3.stats["blocked"]))
was = ws.partner
ws.partner = types.SimpleNamespace(id="someone")
qs = [b3.question_for({}) for _ in range(len(Bot.QUESTIONS) + 2)]
asked = [q for q in qs if q]
check("a person is never asked the same question twice; once all are asked there is nothing left to ask", len(set(asked)) == len(asked) == len(Bot.QUESTIONS) and qs[-1] == "", qs)
ws.partner = was

shutil.rmtree(tmp, ignore_errors=True)
store.close()
shutil.rmtree("saves/nightbot_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
