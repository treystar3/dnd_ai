"""(f694) Work handed in where nobody pays for it is told so (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). At Ironvein at seven in the evening, "I hand in both bounties." went to a guild contractor
in the hall, who said "You got your hands on both of 'em, did ya? Toss 'em over here." Nothing was handed in or paid: the clerk keeps
the desk by day, and the player was never told. Words with no deed.
Held here: a talk whose words hand in finished work this listener does not take tells the player who pays, and whether they are
here (told.yaml handin_away, handin_other), and the listener is told nothing was handed in or paid: the payer away, the payer here
but not spoken to (a named listener), and the rest of a mixed hand-in; two titles for one payer are one line; a hand-in to the one
who pays says nothing of the kind; a talk that hands nothing in, or with nothing finished, says nothing of it either.
Run: python tools/sim/handin_away_694_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
import ui.console as uc
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(str(m)))
from engine import quests
import scenes.world as W
from npc.models import NPC

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


NAME = "handin_away_694"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="guild_house")
ws, store = g.scene, g.store
ws.enter("guild_house")
ws.player.mentor["never"] = True
store.save_npc(NPC(id="n694", name="Norvald Balarakk", people="dwarf", role="guild_contractor", location="guild_house"))
store.save_npc(NPC(id="c694", name="Bimnob Zump", people="gnome", role="guild_clerk", location="guild_house"))
nor, clerk = store.load_npc("n694"), store.load_npc("c694")
M0 = store.meta.minutes
HEARD = []
real_converse = W.converse
W.converse = lambda npc, store_, world, catalog, convo, speech, ctx, **k: (HEARD.append(speech), real_converse(npc, store_, world, catalog, convo, speech, ctx, **k))[1]


def ready():
    q = quests._quest("bounty", "E", "Bounty: the pegasus of the Grey Mountains", ws.minutes, creature="pegasus", place="grey_mountains")
    q["progress"] = 1
    ws.player.quests = [q]
    store.save_player(ws.player)


def talk(words, to, here):
    store.meta.minutes = M0                               # the hall's day held: nobody heads home between the cases
    ws.present =[n for n in ws.present if n.role not in ("guild_clerk", "guild_contractor")] + here
    NOTES.clear(); HEARD.clear()
    stub.plan = [{"kind": "talk", "target": to, "speech": words}]
    try:
        ws.turn(f'I say, "{words}"')
    finally:
        stub.plan = None
    return " ".join(NOTES), " ".join(HEARD)


ready()
notes, heard = talk("I hand in the pegasus bounty.", "n694", [nor])
check("with the clerk away, the player is told who pays and that they are not here", "clerk" in notes.lower() and "pegasus" in notes.lower(), notes)
check("...the listener is told nothing was handed in or paid", "nothing is handed in" in heard, heard[-300:])
check("...and the contract is still held", len(ws.player.quests) == 1)
notes, heard = talk("How are the mines?", "n694", [nor])
check("a talk that hands nothing in says nothing of it", "clerk" not in notes.lower() and "nothing is handed in" not in heard, (notes, heard[-200:]))
ws.player.quests = []
store.save_player(ws.player)
notes, heard = talk("I hand in the pegasus bounty.", "n694", [nor])
check("with nothing finished, nothing is said of a payer", "clerk" not in notes.lower() and "nothing is handed in" not in heard, (notes, heard[-200:]))
ready()
notes, heard = talk("I hand in the pegasus bounty.", "c694", [nor, clerk])
check("handed to the clerk at the desk, it is handed in and nothing is said of anyone away",
      not ws.player.quests and "nothing is handed in" not in heard and "not here" not in notes, (notes, ws.player.quests))

def request(title, issuer, name):
    q = quests._quest("gather", "F", title, ws.minutes, guild=False, issuer=issuer, issuer_name=name, good="herbs", count=0)
    q["progress"] = 1
    return q


store.save_npc(NPC(id="m694", name="Mara Voss", people="human", role="farmer", location="ironvein"))
ready()
ws.player.quests.append(request("Bring the herbs", "m694", "Mara Voss"))
store.save_player(ws.player)
notes, heard = talk("I hand in my work.", "c694", [nor, clerk])
check("a mixed hand-in: the bounty is paid, and the request whose asker is away is told so (as this character knows her)",
      len(ws.player.quests) == 1 and "Bring the herbs" in notes and "farmer" in notes, (notes, [q["title"] for q in ws.player.quests]))
ready()
q2 = dict(ws.player.quests[0], id="q2b", title="Bounty: the gargoyle of the Ironcrown Peaks")
ws.player.quests.append(q2)
store.save_player(ws.player)
notes, heard = talk("I hand in both bounties.", "n694", [nor])
check("two titles for the one payer away are told in one line", notes.count("not here") == 1 and "pegasus" in notes and "gargoyle" in notes, notes)
ws.player.quests = ws.player.quests[:1]
store.save_player(ws.player)
notes, heard = talk("Norvald, I hand in the pegasus bounty.", "n694", [nor, clerk])
check("the payer here but not spoken to (a named listener keeps the talk): the player is told who pays",
      len(ws.player.quests) == 1 and "pegasus" in notes.lower() and "clerk" in notes.lower(), notes)
check("...and the listener that nothing was handed in", "nothing is handed in" in heard, heard[-300:])

W.converse = real_converse
g.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
