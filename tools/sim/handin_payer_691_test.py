"""(f691) Work handed in to someone who pays for none of it goes to the one who does (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). At Ironvein, "I go to the guild hall and hand in the griffon contracts." was read as a
walk and a talk to a contractor standing in the hall; he answered "Let me see those papers then" and nothing was handed in, though
the clerk sat at the counter. A hand-in is made by speaking to who pays (f378); the reading picked the wrong listener.
Held here: a talk whose words hand work in, aimed at someone who pays for nothing finished, is for the one here who does: the clerk
for a guild contract, the asker for a personal request; a listener the line names keeps it, as does a talk that hands nothing in, and
so does a hand-in when nobody here pays or more than one would.
Run: python tools/sim/handin_payer_691_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import quests
from llm.contracts import ActionIntent as A
from npc.models import NPC

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


NAME = "handin_payer_691"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="guild_house")
ws, store = g.scene, g.store
ws.enter("guild_house")
store.save_npc(NPC(id="c691", name="Bimnob Zump", people="gnome", role="guild_clerk", location="guild_house"))
store.save_npc(NPC(id="n691", name="Norvald Balarakk", people="dwarf", role="guild_contractor", location="guild_house"))
store.save_npc(NPC(id="a691", name="Colmer Moorwell", people="human", role="farmer", location="guild_house"))
norvald, asker = store.load_npc("n691"), store.load_npc("a691")
ws.present = [norvald, asker, store.load_npc("c691")] + [n for n in ws.present if n.role != "guild_clerk"]
clerk = ws.clerk_here()
check("(the hall has its clerk)", clerk is not None and clerk.id == "c691", [(n.id, n.role) for n in ws.present])
ws.turn_in = lambda to=None: []                     # what is handed in is f378's; the listener is what is held here


def ready(guild=True, issuer="guild"):
    q = quests._quest("hunt", "F", "Hunt 2 wolves", ws.minutes, guild=guild, creature="wolf", count=2, place="greywood",
                      issuer=issuer, issuer_name="Colmer Moorwell" if not guild else "the guild")
    q["progress"] = 2
    ws.player.quests = [q]


def heard(words, target="n691", line=None):
    i = A(kind="talk", target=target, speech=words, summary=words)
    ws.prepare_talk(i, line or f'I say, "{words}"')
    return i.target


ready()
check("a hand-in said to one who pays for nothing goes to the clerk, for a guild contract",
      heard("I'm here to hand in the wolf contracts.", line="I go to the guild hall and hand in the wolf contracts.") == clerk.id)
check("...'turn in' too", heard("I want to turn these in.") == clerk.id)
check("a listener the line names keeps it", heard("Norvald, I'll hand these in shortly.", line='I tell Norvald, "I\'ll hand these in shortly."') == "n691")
check("a talk that hands nothing in keeps its listener", heard("How are the mines?") == "n691")
for bed in ("Well, I am turning in. Goodnight.", "I think I will turn in now.", "I'll report back once the wolves are dead."):
    check(f"going to bed, or a promise to come back, hands nothing in: '{bed}'", heard(bed) == "n691")
check("a hand-in with no listener read goes to the one who pays", heard("I'm here to hand in the wolf contracts.", target="") == clerk.id)
store.save_npc(NPC(id="w691", name="Wenna Hale", people="human", role="farmer", location="ironvein"))
check("a listener of this town who is elsewhere keeps it: the walk to them is theirs", heard("I'm here to hand in the job.", target="w691") == "w691")
check("a hand-in already said to the clerk stays with the clerk", heard("I'm here to hand in the wolf contracts.", target=clerk.id) == clerk.id)
ready(guild=False, issuer="a691")
check("a personal request goes to the one who asked", heard("The job is done; I'm here to hand it in.") == "a691")
ws.present = [n for n in ws.present if n.id != "a691"]
check("with nobody here who pays, the listener stays", heard("I'm here to hand it in.") == "n691")
ws.player.quests = []
check("with nothing finished, the listener stays", heard("I'm here to hand in the contracts.") == "n691")
ready()
q2 = dict(ws.player.quests[0], id="q2", guild=False, issuer="a691", issuer_name="Colmer Moorwell")
ws.present.append(asker)
ws.player.quests.append(q2)
check("two who would pay, and the words name neither: the listener stays", heard("I'm here to hand in my work.") == "n691")

del ws.turn_in
g.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
