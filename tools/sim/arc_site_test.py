"""Missing-person arcs: a site node is searched with the best fitting skill and a confrontation finale is settled by evidence, both rolled with
the character's own perks in play (the roll used to name a character variable nobody had bound, and crashed every site search). The arc is
forced through the board the way the game does it; the model is the stand-in."""
import os
import random
import sys
sys.path.insert(0, ".")
sys.argv = ["x", "warrior", "2", "1", "1", "1"]
_out = sys.stdout                                        # the bot takes stdout for its own log: the checks print to the real one
import simbot
from llm.contracts import ActionIntent
from engine import arcs, checks, clock, quests
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=_out)
    if not ok: bad.append(n)

b = simbot.Bot(); ws = b.ws; c = ws.player.character
c.level = 20; c.coins = 100000; ws.player.guild_rank = "D"
ws.player.mentor["never"] = True
notes, narrated = [], []
console.note = lambda t, *a, **k: notes.append(t)
ws._narrate_now = lambda event, player_text="": narrated.append(event)
arcs.roll_scale = lambda *a, **k: ("arc", "forced")
_roll = checks.roll

def working_hours():
    while not all(clock.in_hours(ws.store.meta.minutes + h, (9, 18)) for h in (0, 120, 240)):
        ws.store.meta.minutes += 30

def start(tid: str):
    """Take a forced arc of this template from the board; the arc as the store holds it."""
    c.level = 20; ws.combat = None; ws.player.guild_rank = "D"
    ws.store.save_arcs({"arcs": [], "last_end": -10 ** 9}); ws.player.quests = []
    ws.store.meta.minutes += 1440 * 25
    working_hours()
    ws.enter("guild_house"); ws.ensure_board()
    tpl = arcs.TEMPLATES[tid]
    q = quests._quest("missing", "D", tpl["board"].format(subject=tpl["victims"][0], place="X"), ws.minutes, victim=tpl["victims"][0], hall="guild_house", count=1)
    q["template"] = tid
    gs = ws.store.load_place("guild_house"); gs.board = [q]; ws.store.save_place(gs)
    ws.on_accept_quest(ActionIntent(kind="accept_quest", item="1"), "take 1")
    data, arc = ws.my_arc()
    return data, arc, tpl

def walk_to(data, arc, kind: str):
    """Complete the arc's steps until one of this kind is current, and stand at its place."""
    while True:
        n = arcs.current(arc)
        if n is None or n["kind"] == kind:
            break
        arcs.complete_node(arc, n["id"])
    ws.store.save_arcs(data)
    if n:
        ws.combat = None
        ws.enter(n["place"])
    return n

def start_with(tid: str, kind: str):
    """An arc of this template whose trail has a step of this kind: the layout is rolled, so a few tries may be needed."""
    for _ in range(8):
        data, arc, tpl = start(tid)
        if arc and any(n["kind"] == kind for n in arc["nodes"]):
            return data, arc, tpl
    return data, arc, tpl

# ---- a site is searched
site_tpl = next(t for t, tpl in arcs.TEMPLATES.items() if (tpl.get("mix") or {}).get("site"))
data, arc, tpl = start_with(site_tpl, "site")
check("a forced arc is taken from the board", arc is not None and arc["template"] == site_tpl, (site_tpl, arc and arc["template"]))
n = walk_to(data, arc, "site")
check("...and has a site to search", n is not None and n["kind"] == "site" and ws.player.location == n["place"], n and (n["kind"], n["place"], ws.player.location))
checks.roll = lambda odds, rng=None, c=None: ("success", 1)
narrated.clear()
data, arc = ws.my_arc(); n = arcs.current(arc)
if n and n["kind"] == "site" and n["status"] != "done":
    ws.work_site(data, arc, n, tpl)
data, arc = ws.my_arc(); done = next((x for x in arc["nodes"] if x["kind"] == "site"), None)
check("searching the site with a good roll finds what it hides and the arc moves on", done is not None and done["clue_given"] and done["status"] == "done"
      and any("searches at" in e for e in narrated), (done and (done["clue_given"], done["status"]), narrated[-1:][0][:80] if narrated else ""))

# ---- a search that keeps failing costs time, and three tries find the thread another way
data, arc, tpl = start_with(site_tpl, "site")
n = walk_to(data, arc, "site")
checks.roll = lambda odds, rng=None, c=None: ("failure", 99)
t0 = ws.minutes
data, arc = ws.my_arc(); n = arcs.current(arc)
if n and n["kind"] == "site" and n["status"] != "done":
    ws.work_site(data, arc, n, tpl)
data, arc = ws.my_arc(); done = next((x for x in arc["nodes"] if x["kind"] == "site"), None)
check("three failed searches cost hours and the thread turns up another way, at a cost", done is not None and done["attempts"] == arcs.A["max_attempts"] and done["partial"]
      and ws.minutes - t0 >= (arcs.A["max_attempts"] - 1) * arcs.A["site"]["hours_per_try"] * 60, (done and (done["attempts"], done["partial"]), ws.minutes - t0))

# ---- a confrontation finale is settled by evidence
conf_tpl = next(t for t, tpl in arcs.TEMPLATES.items() if tpl.get("finale") == "confront")
data, arc, tpl = start(conf_tpl)
n = walk_to(data, arc, "boss")
check("a confrontation template ends at a reckoning", n is not None and n["kind"] == "boss" and tpl["finale"] == "confront", n and n["kind"])
checks.roll = lambda odds, rng=None, c=None: ("strong success", 1)
narrated.clear(); notes.clear()
data, arc = ws.my_arc(); n = arcs.current(arc)
settled = ws.confront(data, arc, n, tpl) if n and n["kind"] == "boss" else None
check("with the proof too strong, the one behind it gives way without a fight", settled is True and any("gives way" in x for x in notes), (settled, notes[-2:]))
data, arc, tpl = start(conf_tpl)
n = walk_to(data, arc, "boss")
checks.roll = lambda odds, rng=None, c=None: ("failure", 99)
notes.clear()
data, arc = ws.my_arc(); n = arcs.current(arc)
settled = ws.confront(data, arc, n, tpl) if n and n["kind"] == "boss" else None
check("...and when it is not enough, it comes to blades", settled is False and any("comes to blades" in x for x in notes), (settled, notes[-2:]))
checks.roll = _roll

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "", file=_out)
sys.exit(1 if bad else 0)
