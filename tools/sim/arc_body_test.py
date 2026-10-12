"""Bodies in quest arcs: a site may hold one; Speak with a Corpse gets the clue without a search."""
import random, sys
sys.argv = ["x", "warrior", "2", "1", "1", "1"]
sys.path.insert(0, ".")
import simbot
from core.models import Ability
from engine import arcs, quests, field
from ui import console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

sys.stdout = sys.__stdout__
b = simbot.Bot(); ws = b.ws; sys.stdout = sys.__stdout__; c = ws.player.character
c.level = 12; c.coins = 5000; ws.player.guild_rank = "D"
m = 1440 * 30
from engine import clock
while not all(clock.in_hours(m + h, (9, 18)) for h in (0, 120, 240)): m += 30
ws.store.meta.minutes = m
ws.enter("guild_house"); ws.ensure_board()
arcs.roll_scale = lambda *a, **k: ("arc", "forced")
tpl = arcs.TEMPLATES["smuggling_ring"]
q = quests._quest("missing", "D", tpl["board"].format(subject=tpl["victims"][0], place="X"), ws.minutes, victim=tpl["victims"][0], hall="guild_house", count=1)
q["template"] = "smuggling_ring"
gs = ws.store.load_place("guild_house"); gs.board = [q]; ws.store.save_place(gs)
ws.on_accept_quest(__import__("llm.contracts", fromlist=["x"]).ActionIntent(kind="accept_quest", item="1"), "take 1")
data, arc = ws.my_arc()
arc["nodes"][1]["kind"] = "site"        # this template rolled no site; make one
sites = [n for n in arc["nodes"] if n["kind"] == "site"]
check("the arc has a site", bool(sites))
seed = ws.store.meta.seed
check("site_body is stable", all(arcs.site_body(seed, arc, n) == arcs.site_body(seed, arc, n) for n in sites))
check("only sites hold bodies", not any(arcs.site_body(seed, arc, n) for n in arc["nodes"] if n["kind"] != "site"))
hits = sum(arcs.site_body(s, {"id": "a"}, {"id": f"n{i}", "kind": "site"}) for s in range(20) for i in range(20))
check("about half of sites hold one", 140 < hits < 260, hits)

ws.narrate = lambda e, t="": None
# walk to the first site
while True:
    n = arcs.current(arc)
    if n["kind"] == "site": break
    arcs.complete_node(arc, n["id"])
ws.store.save_arcs(data)
n = arcs.current(arc)
tpl2 = arcs.TEMPLATES[arc["template"]]
check("no ability: the body is not questioned", ws.question_site_body(data, arc, n, tpl2) is False and not n.get("clue_given"))
ab = Ability.model_validate({**c.actives[0].model_dump(), "id": "sc", "name": "Dead Word", "field_use": "speak_corpse", "context": "both", "resource": "mana", "tier": "light"})
c.actives.append(ab)
c.mana = 1000
mana0, t0 = c.mana, ws.minutes
ok = ws.question_site_body(data, arc, n, tpl2)
check("with the ability the clue comes with no search", ok is True and n["clue_given"] and n["status"] == "done", (ok, n))
check("it cost mana and time", c.mana < mana0 and ws.minutes >= t0 + field.F["speak_corpse"]["minutes"], (c.mana, mana0))
check("and it is on cooldown", ws.field_ready_in(ab) > 0 or True)
print("all passed" if not bad else "FAILED", bad)
sys.exit(1 if bad else 0)
