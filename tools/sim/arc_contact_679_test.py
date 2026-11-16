"""(f679) An arc's contact is pointed to and is there while their step is open (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md, "Discrepancy in the Chronicles"). The Story pane said "the first sign of it is at
Kelpmoor. Ask there. Next: Kelpmoor." and nothing named whom to ask; the contact, a real person made on arrival, kept their trade's
hours (the player came in at 1 AM) and could be out at a routine, so asking the town's other folk gave nothing.
Held here: arriving at a contact's place says who there should know more, by their trade (never their secret, f486); the arc's
"Next:" line says it too; the contact is among those present at any hour while their step is open, and keeps their hours again
once the clue is given. Every template with a contact step is tried.
Run: python tools/sim/arc_contact_679_test.py"""
import sys
sys.path.insert(0, ".")
sys.argv = ["x", "warrior", "2", "1", "1", "1"]
import simbot
from llm.contracts import ActionIntent
from engine import arcs, clock, quests
from ui import console

bad = []
def check(n, ok, x=""):
    sys.__stderr__.write(("ok   " if ok else "FAIL ") + n + ("" if ok else f" {x}") + "\n")
    if not ok: bad.append(n)

b = simbot.Bot(); ws = b.ws; c = ws.player.character
ws.player.mentor["never"] = True
notes = []
console.put("note", lambda t, *a, **k: notes.append(t))
ws._narrate_now = lambda event, player_text="": None
arcs.roll_scale = lambda *a, **k: ("arc", "forced")


def at_hour(h):
    ws.store.meta.minutes += (h * 60 - ws.store.meta.minutes % 1440) % 1440


def start(tid):
    c.level = 20; ws.combat = None; ws.player.guild_rank = "D"
    ws.store.save_arcs({"arcs": [], "last_end": -10 ** 9}); ws.player.quests = []
    ws.store.meta.minutes += 1440 * 25
    while not all(clock.in_hours(ws.store.meta.minutes + h, (9, 18)) for h in (0, 120, 240)):
        ws.store.meta.minutes += 30
    ws.enter("guild_house"); ws.ensure_board()
    tpl = arcs.TEMPLATES[tid]
    q = quests._quest("missing", "D", tpl["board"].format(subject=tpl["victims"][0], place="X"), ws.minutes, victim=tpl["victims"][0], hall="guild_house", count=1)
    q["template"] = tid
    gs = ws.store.load_place("guild_house"); gs.board = [q]; ws.store.save_place(gs)
    ws.on_accept_quest(ActionIntent(kind="accept_quest", item="1"), "take 1")
    return ws.my_arc()


tried = 0
for tid in arcs.TEMPLATES:
    data, arc = start(tid)
    if not arc:
        continue
    n = next((x for x in arc["nodes"] if x["kind"] == "contact"), None)
    if n is None:
        continue
    while arcs.current(arc) is not n:
        arcs.complete_node(arc, arcs.current(arc)["id"])
    ws.store.save_arcs(data)
    hours = ws.world.roles[n["role"]].hours
    night = next((h for h in range(24) if not clock.in_hours(h * 60, hours)), None)
    at_hour(night if night is not None else 2)
    notes.clear()
    ws.combat = None
    ws.enter(n["place"])
    data, arc = ws.my_arc()
    n = arcs.node(arc, n["id"])
    role = n["role"].replace("_", " ")
    tried += 1
    check(f"{tid}: arriving says who there should know more, by their trade", any(role in t for t in notes), (role, notes[-3:]))
    check(f"{tid}: the contact is here at {night if night is not None else 2}:00, outside their trade's hours",
          any(p.id == n.get("npc") for p in ws.present), (n.get("npc"), [p.id for p in ws.present]))
    notes.clear()
    ws.show_arc()
    check(f"{tid}: the arc's Next line names the trade too", any(t.startswith("Next:") and role in t for t in notes), notes)
    n["clue_given"] = True
    ws.store.save_arcs(data)
    ws.refresh_present()
    if night is not None:
        check(f"{tid}: once the clue is given, the contact keeps their hours again", all(p.id != n.get("npc") for p in ws.present),
              [p.id for p in ws.present])
check("(some template has a contact step)", tried > 0, tried)
sys.__stderr__.write("\nALL PASS\n" if not bad else "\nFAILED: " + ", ".join(bad) + "\n")     # simbot keeps stdout for its own log
sys.exit(1 if bad else 0)
