"""(f493) The night bot's continuity steps, as the baseline night's blind readers found them: the lie's line went to the model to be
reworded and lost its false name, so the bot later "set straight" a name the page never saw ("it isn't Odessa Thrimble"); and a return
line said "I'm back, as I said I'd be" to people it had promised nothing. Now a continuity step's line is typed as written, a step whose
turn the game rolled back is taken back, and the promised return is said only where a promise was made."""
import random
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
shown = simlib.quiet_console()
import nightbot
from engine import failures

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

g = simlib.campaign("night_bot_493", cls="warrior", seed=7, location="tilted_plough")
ws, world = g.scene, g.world
ws.enter("tilted_plough")
people = list(ws.present)
check("the scene has people to talk to", len(people) >= 2, len(people))
a, b = people[0], people[1]
ALL = {k: 100.0 for k in nightbot.CONTINUITY["talker"]}
NONE = {k: 0.0 for k in nightbot.CONTINUITY["talker"]}

# ---- a continuity line is typed as written: the model that words the bot's other lines never sees it
bot = nightbot.Bot(ws, world, random.Random(5), stub=stub, persona="talker", continuity=True)
bot.stub, bot.run = None, type("Run", (), {"passage": [], "current": None})()      # as on a real night: the model words the lines
reworded = []
bot.model_line = lambda text, intent, kind, passage: (reworded.append(text), "I tell them a little about myself.")[1]
ws.partner = a
bot.CW = dict(ALL)
bot.choose = lambda: bot._cont_talk(a)
text, kind = bot.decide()
plant = bot.clog["plants"][0] if bot.clog["plants"] else {}
check("the lie's line is typed as written, false name and all, never reworded", plant and plant["token"] in text and not reworded, (text, reworded))
bot.CW = dict(NONE)
bot.choose = lambda: ("I ask about the weather.", bot.intend("talk", target=a.id, speech="Weather?"), "talk")
text, kind = bot.decide()
check("...while an ordinary line is still worded by the model", reworded and text == "I tell them a little about myself.", (text, reworded))

# ---- a step whose turn the game rolled back is taken back: no correction of a name the page never saw
bot2 = nightbot.Bot(ws, world, random.Random(6), stub=stub, persona="talker", continuity=True)
bot2.stub, bot2.run = None, type("Run", (), {"passage": [], "current": None})()
bot2.model_line = lambda *x: ""
bot2.CW = dict(ALL)
bot2.choose = lambda: bot2._cont_talk(b)
bot2.decide()
check("the lie is logged when told", len(bot2.clog["plants"]) == 1)
bot2.run.passage = [failures.lines()[0]]                                  # the game answered it with a failure line: the turn rolled back
bot2.CW = dict(NONE)
bot2.choose = lambda: ("I look around.", bot2.intend("look"), "look")
bot2.decide()
check("...and taken back when its turn rolled back, so nothing is ever set straight that was never said",
      bot2.clog["plants"] == [] and bot2.stats.get("cont_taken_back") == 1, (bot2.clog["plants"], bot2.stats.get("cont_taken_back")))

# ---- "as I said I'd be" only to someone promised
check("the plain return lines promise nothing", not any("said I'd" in l or "promised" in l.lower() for l in nightbot.REVISIT_LINES))
bot3 = nightbot.Bot(ws, world, random.Random(8), stub=stub, persona="talker", continuity=True)
for who, promised in ((a, False), (b, True)):
    if promised:
        bot3.clog["promises"].append({"npc": who.id, "turn": 0, "text": "I'll be back."})
    bot3._note_met(who)
    ws.store.meta.minutes += nightbot.REVISIT_AFTER + 60
    g_ = {"kind": "revisit", "npc": who.id, "place": ws.player.location, "name": who.label(ws.acting), "why": "return", "tries": 0}
    bot3.goals.append(g_)
    text, intent, kind = bot3.goal_revisit(g_)
    pool = nightbot.PROMISED_RETURN_LINES if promised else nightbot.REVISIT_LINES
    check(f"a return to someone {'promised' if promised else 'promised nothing'} says {'the promised return' if promised else 'a plain return'}",
          any(l in text for l in pool) and bot3.clog["revisits"][-1]["promised"] is promised, text)
g.close()
import shutil
shutil.rmtree("saves/night_bot_493", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
