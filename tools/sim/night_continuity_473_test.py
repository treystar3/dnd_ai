"""(f473) The night bot's continuity steps: what a player does that the world then has to remember. Off unless asked for, and on a
stream of their own, so the golden's session and every test that drives the bot are unmoved; on, the bot makes a promise in words,
tells one false name a run and later sets it straight to the one told, goes back to people a game day or more after the last talk,
takes up work and requests offered, gives a contract up out loud, and visits the one who posted a contract when it is over. The
night's per-turn state carries the truth the continuity counts read: who is here and what each knows of the player, what is owed,
the turn's deeds and who saw them."""
import random
import shutil
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
import ui.console as uc
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from pathlib import Path
import nightbot
import nightrun

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


NAME = "night_continuity_473"
g = simlib.campaign(NAME, cls="warrior", seed=7, location="tilted_plough")
ws, store, world = g.scene, g.store, g.world
ws.enter("tilted_plough")   # the inn: people to talk to
c = ws.player.character
c.hunger, c.fatigue = 0, 0
people = [n for n in ws.present]
check("the scene has people to talk to", len(people) >= 2, len(people))
a, b = people[0], people[1]

# ---- off by default, and no draw taken from the bot's own stream
r = random.Random(5)
before = r.getstate()
off = nightbot.Bot(ws, world, r, stub=stub, persona="talker")
check("off unless asked for, and building the bot takes no draw from its stream", not off.cont and r.getstate() == before)
check("...and with it off the bot's report carries no continuity", "continuity" not in off.report())
check("the night turns it on (--no-continuity turns it off) and passes the choice to each run it starts",
      "continuity=not args.no_continuity" in Path("tools/nightrun.py").read_text(encoding="utf-8")
      and 'cmd += ["--no-continuity"] if args.no_continuity else []' in Path("tools/nightrun.py").read_text(encoding="utf-8"))

bot = nightbot.Bot(ws, world, random.Random(5), stub=stub, persona="talker", continuity=True)
ALL = {k: 100.0 for k in nightbot.CONTINUITY["talker"]}
NONE = {k: 0.0 for k in nightbot.CONTINUITY["talker"]}

# ---- in a conversation: nothing when the weights say nothing; then the lie (once a run), a promise, an offer taken up
ws.partner = a
bot.CW = dict(NONE)
check("with every weight at nothing, a conversation is left to its questions", bot._cont_talk(a) is None)
bot.CW = dict(ALL)
text, intent, kind = bot._cont_talk(a)
plant = bot.clog["plants"][0] if bot.clog["plants"] else {}
check("the run's one lie: a false name no table in data holds, told to this person and logged", kind == "talk" and plant.get("token") in text
      and plant.get("npc") == a.id and plant["token"] in nightbot.FALSE_NAMES, (text, plant))
text, intent, kind = bot._cont_talk(a)
check("...told once a run: the next turn makes a promise instead, logged to whom", kind == "talk" and len(bot.clog["plants"]) == 1
      and bot.clog["promises"] and bot.clog["promises"][0]["npc"] == a.id and bot.clog["promises"][0]["text"] in text, (text, bot.clog["promises"]))
check("...and a promise to the same person is made once", bot._cont_talk(a) is None)
simlib.offer(store, a.id, "work", {"task": "carry sacks to the mill", "pay": 30, "minutes": 60})   # (f481) an offer in the registry
text, intent, kind = bot._cont_talk(a)
check("work this person offered is taken up, by its own action", kind == "work" and intent.get("kind") == "work" and intent.get("target") == a.id
      and bot.clog["accepted"][-1] == {**bot.clog["accepted"][-1], "npc": a.id, "kind": "work"}, (text, intent))
simlib.end_offer(store, a.id, "work")
simlib.offer(store, a.id, "request", {"title": "Find my lost goat", "what": "a goat"})
text, intent, kind = bot._cont_talk(a)
check("...and a personal request is accepted", intent.get("kind") == "accept_quest" and bot.clog["accepted"][-1]["kind"] == "request", (text, intent))
simlib.end_offer(store, a.id, "request")
check("the turn's step goes on the night's row", bot.__dict__.get("_cont_now", {}).get("step") == "accepted", bot.__dict__.get("_cont_now"))
ws.partner = None

# ---- people gone back to: not before a game day has passed, then a revisit with how long it has been
bot._note_met(b)
bot.goals.clear()
bot.continuity_goals()
check("someone talked to just now is not gone back to yet", not any(x.get("npc") == b.id for x in bot.goals), bot.goals)
store.meta.minutes += nightbot.REVISIT_AFTER + 60
bot.clog["plants"][0]["turn"] = store.meta.turn                       # the lie is fresh: the revisit below is the ordinary kind
bot.continuity_goals()
rv = next((x for x in bot.goals if x.get("kind") == "revisit"), None)
check("a game day later they are due: a revisit goal to where they were", rv is not None and rv["place"] == ws.player.location
      and rv["why"] == "return", bot.goals)
if rv:
    bot.goals = [rv]
    text, intent, kind = bot.goal_revisit(rv)
    check("...walked to them: a talk that says it has been a while, with the gap logged", kind == "talk" and intent.get("target") == rv["npc"]
          and any(line in text for line in (nightbot.PROMISED_RETURN_LINES if bot.clog["revisits"][-1].get("promised") else nightbot.REVISIT_LINES))   # (f493)
      and bot.clog["revisits"][-1]["gap"] >= nightbot.REVISIT_AFTER, (text, bot.clog["revisits"]))
    check("...and the goal is done", rv not in bot.goals)

# ---- the lie set straight, to the one it was told to, once enough turns have passed
bot.goals.clear()
bot.clog["plants"][0]["turn"] = store.meta.turn - nightbot.CORRECT_AFTER
bot.met[a.id]["place"] = ws.player.location
bot.CW = dict(NONE)                                                  # the correction comes first, whatever the weights
bot.continuity_goals()
cg = next((x for x in bot.goals if x.get("why") == "correct"), None)
check("the correction is due: a revisit to the one told", cg is not None and cg["npc"] == a.id, bot.goals)
if cg:
    text, intent, kind = bot.goal_revisit(cg)
    tok = bot.clog["plants"][0]["token"]
    check("...the false name owned to and the real one given, logged", tok in text and c.name in text and bot.clog["plants"][0].get("corrected")
          and bot.clog["corrections"] and bot.clog["corrections"][0]["token"] == tok, (text, bot.clog["corrections"]))
bot.goals.clear()
bot.continuity_goals()
check("...set straight once", not any(x.get("why") == "correct" for x in bot.goals), bot.goals)

# ---- someone not there is waited for twice, then let go
gone = {"kind": "revisit", "npc": "nobody_here", "place": ws.player.location, "name": "Nobody", "why": "return", "tries": 0}
bot.goals = [gone]
w1 = bot.goal_revisit(gone)
w2 = bot.goal_revisit(gone)
w3 = bot.goal_revisit(gone)
check("a person not there: waited for twice, then the goal is dropped", w1[2] == "wait" and w2[2] == "wait" and w3 is None and gone not in bot.goals)

# ---- a contract given up out loud, and the one who posted it told
store.save_npc(b)
q = {"id": "q_473", "title": "Hunt 3 wolves near Parth", "kind": "hunt", "guild": False, "issuer": b.id, "issuer_name": b.label("player"),
     "letter": "F", "creature": "wolf", "count": 3, "place": "tilted_plough", "progress": 0}
ws.player.quests.append(q)
gc = {"kind": "contract", "quest": "q_473", "tries": 30}
bot.goals = [gc]
bot.CW = dict(ALL)
out = bot.goal_contract(gc)
check("a contract the bot cannot finish is given up out loud, by its own action, and logged", out and out[1].get("kind") == "abandon_quest"
      and bot.clog["abandoned"][-1]["quest"] == "q_473", out)
iv = next((x for x in bot.goals if x.get("why") == "issuer"), None)
check("...and a visit to the one who posted it is planned, saying how it ended", iv is not None and iv["npc"] == b.id and iv["outcome"] == "abandoned", bot.goals)
if iv:
    text, intent, kind = bot.goal_revisit(iv)
    check("...where the bot owns that it could not see it through", "couldn't see the work you posted through" in text
          and bot.clog["issuer_visits"][-1]["outcome"] == "abandoned", text)
ws.player.quests.remove(q)
bot._issuer_goal({"issuer": b.id, "issuer_name": b.label("player"), "title": "Hunt 3 wolves"}, "done")
done_visit = next((x for x in bot.goals if x.get("why") == "issuer"), None)
check("a contract reported done plans the same visit, with 'done'", done_visit is not None and done_visit["outcome"] == "done", bot.goals)
bot._issuer_goal({"issuer": "guild", "title": "A guild job"}, "done")
check("...but never for the guild, which is not a person", sum(1 for x in bot.goals if x.get("why") == "issuer") == 1)
bot.goals.clear()

# ---- the bot's report carries the log the counts compare the page against
rep = bot.report()
check("the report counts each kind of step and keeps the log", rep["continuity"]["plants"] == 1 and rep["continuity"]["corrections"] == 1
      and rep["continuity"]["revisits"] >= 1 and rep["continuity_log"]["plants"][0]["npc"] == a.id, rep.get("continuity"))

# ---- the night's per-turn state: who is here and what each knows, what is owed, the turn's deeds and who saw them
run = types.SimpleNamespace()
ws.player.quests.append(dict(q))
simlib.offer(store, b.id, "work", {"task": "mend a fence", "pay": 20, "minutes": 60})
s1 = nightrun.Run.continuity_state(run, ws)
check("the state names who is here, with what each knows of the player", b.id in s1["talk"] and {"label", "met", "last_talk_at", "known_as", "trust"}
      <= set(s1["talk"][b.id]), s1.get("talk", {}).get(b.id))
check("...what is owed: the contract held (by its issuer) and the work offered (open)", any(o["id"] == "q_473" and o["holder"] == b.id for o in s1["owed"])
      and any(o["id"] == f"work:{b.id}" and o["state"] == "open" for o in s1["owed"]), s1["owed"])
check("...and no deeds on the first turn read (what came before the night is not the night's)", s1["deeds"] == [], s1["deeds"])
with store.transaction():
    store.journal(ws.minutes, "Theft", actor="player", target=b.id, text="took a purse", data={"witnesses": [b.id], "place": "parth"})
store.meta.minutes += 400
s2 = nightrun.Run.continuity_state(run, ws)
check("a deed recorded since: in the state with who saw it", len(s2["deeds"]) == 1 and s2["deeds"][0]["witnesses"] == [b.id], s2["deeds"])
check("...the offer, past the hours it used to last, still stands (nothing ends by age, f481)",
      any(o["id"] == f"work:{b.id}" and o["state"] == "open" for o in s2["owed"]), s2["owed"])
simlib.end_offer(store, b.id, "work")
s3 = nightrun.Run.continuity_state(run, ws)
check("...and a deed is counted once", s3["deeds"] == [])
check("...an offer that ends is in the state's closed, with its reason (f481)", any(c["id"] == f"work:{b.id}" and c["state"] == "withdrawn" and c["reason"]
      for c in s3["closed"]), s3.get("closed"))
ws.player.quests.clear()

g.close()
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
