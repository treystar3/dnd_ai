"""(f432) The night bot, as the f425 night showed it playing: the mage noticed its bear contract only once in the Greywood, recorded the
Greywood as the place to report it, and waited there for 700 turns at level 23 ("go and report" was "stay where you are"); "I walk over
to Parth" made the model player take the town for a person ("Excuse me, Parth, are you available?"); and a part of a place was read out
of the whole last passage, "I go to the you stand." Now a contract keeps the hall it was taken at, and the bot reports there; a town is
set out for; and a part named in a passage comes from a phrase of it."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("mage", 32)
simlib.install(stub)
import ui.console as uc
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from tools import nightbot
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/night_bot_432_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("night_bot_432_test")
store.meta.seed = 32; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("mage", random.Random(32))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("guild_house")
bot = nightbot.Bot(ws, world, random.Random(32), stub=stub, persona="talker")
bot.watch()

# ---- a contract keeps its hall, and the bot reports there
from pathlib import Path
src = Path("scenes/guild_actions.py").read_text(encoding="utf-8")
take = src[src.index("    def on_accept_quest("):]
check("a contract taken at the board keeps the hall it was taken at", 'q["hall"] = gid' in take[:take.index("self.player.quests.append(q)")])
ws.enter("greywood")                                     # the bot first sees the contract out in the wild, as the mage did
ws.player.quests.append({"id": "q_bears", "title": "Hunt 4 black bears in the Greywood", "kind": "hunt", "guild": True, "hall": "guild_house",
                         "letter": "F", "creature": "black_bear", "count": 4, "place": "greywood"})
bot.watch()
check("...and the bot records that hall, never the place it stood when it noticed", bot.hall_of.get("q_bears") == "guild_house", bot.hall_of)
ws.player.quests.append({"id": "q_old", "title": "An old contract", "kind": "hunt", "guild": True, "letter": "F", "creature": "wolf",
                         "count": 1, "place": "greywood"})
bot.watch()
check("...an old contract with no hall kept is reported at the nearest hall", world.places[bot.hall_of.get("q_old", "greywood")].type == "guild",
      bot.hall_of.get("q_old"))
step = bot.goal_report({"kind": "report", "place": bot.hall_of["q_bears"], "title": "Hunt 4 black bears", "tries": 0})
check("reporting from the Greywood is a walk to the hall, not a wait", step and step[1]["kind"] == "move" and step[1].get("destination") == "guild_house", step)

# ---- a town is set out for, never walked over to
lines = set()
for _ in range(20):
    out = bot.go_step({"kind": "go", "tries": 0}, "parth")
    if out:
        lines.add(out[0].split(" Parth")[0])
check("a town is set out for, never 'walked over to'", lines and not any(l.startswith("I walk over to") for l in lines), lines)

# ---- a part named in the last passage is a phrase of it
bot.passage = lambda: "In the thorn grove where you stand now, branches twist overhead. A heron stands motionless past the thorns."
named = []
for _ in range(30):
    text, intent, _ = bot.parts_line()
    if text.startswith("I go to "):
        named.append(text)
check("a part the passage named is a phrase of it, never 'the you stand'", named and all("you stand" not in t for t in named)
      and any("thorn grove" in t for t in named), named[:3])

store.close()
shutil.rmtree("saves/night_bot_432_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
