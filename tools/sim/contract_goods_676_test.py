"""(f676) Goods a held contract asks for are handed in when given to the one who pays for it, and asked about before they go to anyone
else (found in the second blind play: docs/play/2026-11-16_blind_play_journal.md, the bear hides). `I hand in the bear hide contract to
Emlily.` gave the four hides to the clerk as a gift, though the contract was the smith's: gone, unpaid, and nothing said whose it was.
And a give to the one who pays did the same: the giving took the goods as a gift first, and the hand-in that runs after the step found
nothing left to hand in.
Held here: given to the payer, the goods hand the contract in (paid, the contract gone, the goods with it); given to anyone else, the
game asks first and gives nothing yet; no keeps them, yes gives them; goods no contract asks for are given at once, as before.
Run: python tools/sim/contract_goods_676_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 5)
simlib.install(stub)
simlib.quiet_console()
from engine import inventory as inv, quests

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


from npc.models import NPC
g = simlib.campaign("contract_goods_676_test", seed=5, minutes=900)
ws, store = g.scene, g.store
ws.enter(ws.player.location)
store.save_npc(NPC(id="c1", name="Ulard Heygate", people="human", role="farmer", location=ws.player.location))
store.save_npc(NPC(id="c2", name="Bors Hale", people="human", role="farmer", location=ws.player.location))
payer, other = store.load_npc("c1"), store.load_npc("c2")
ws.present = [payer, other] + [p for p in ws.present if p.id not in ("c1", "c2")]
leaves = "silverleaf" if "silverleaf" in inv.GOODS else next(iter(inv.GOODS))
name = inv.GOODS[leaves].name


def contract():
    q = quests._quest("gather", "F", "Bring 3 leaves", ws.minutes, good=leaves, count=3)
    q.update(guild=False, issuer=payer.id, issuer_name=payer.name)
    ws.player.quests = [q]
    ws.player.character.inventory[:] = [i for i in ws.player.character.inventory if i.good != leaves] + [inv.make_good(leaves, 3)]
    return q


def give(to):
    ws.present = [store.load_npc("c1"), store.load_npc("c2")] + [p for p in ws.present if p.id not in ("c1", "c2")]
    stub.plan = [{"kind": "give", "target": to.id, "item": name, "count": 3}]
    ws.turn(f"I give the {name} to {to.name}.")


def held():
    return inv.count_of(ws.pack, leaves)


contract()
give(other)
asked = store.load_question()
check("given to one who does not pay for it, the game asks first", (asked or {}).get("kind") == "give_wanted", asked)
check("...and nothing is given yet", held() == 3, held())
check("...the question names whose contract it is", payer.name in (asked or {}).get("question", ""), asked)
ws.turn("no")
check("no: the goods are kept, the contract still held", held() == 3 and ws.player.quests and store.load_question() is None,
      (held(), store.load_question()))

coins = ws.player.character.coins
give(payer)
check("given to the one who pays, the contract is handed in and paid", not ws.player.quests and ws.player.character.coins > coins,
      (ws.player.quests, coins, ws.player.character.coins))
check("...the goods go with it, and nothing is asked", held() == 0 and store.load_question() is None, (held(), store.load_question()))

contract()
give(other)
ws.present = [store.load_npc("c1"), store.load_npc("c2")] + [p for p in ws.present if p.id not in ("c1", "c2")]
ws.turn("yes")
check("yes: the goods are given to them all the same, and the contract stays held", held() == 0 and ws.player.quests, held())

contract()
inv.remove_goods(ws.pack, leaves, "", 1)
give(payer)
asked = store.load_question() or {}
check("too few given to the one who pays: asked first, the question says how many of how many", held() == 2 and
      asked.get("kind") == "give_wanted" and "2" in asked.get("question", "") and "3" in asked.get("question", ""), (held(), asked))
ws.present = [store.load_npc("c1"), store.load_npc("c2")] + [p for p in ws.present if p.id not in ("c1", "c2")]
ws.turn("no")

contract()
hire = {"id": "pae", "name": "Pae Tamalaga", "role": "fighter", "level": 3, "permanent": True, "joined": 0, "fee": 500, "rank": "F", "bond": 10}
ws.player.party.append(hire)
ws.player.party_mode = "with"
stub.plan = [{"kind": "give", "target": "hire:pae", "item": name, "count": 3}]
ws.turn(f"I give the {name} to Pae.")
asked = store.load_question() or {}
check("a companion is anyone else too: asked first, nothing given", asked.get("kind") == "give_wanted" and held() == 3, (asked, held()))
ws.turn("yes")
check("...and yes gives it to them", held() < 3 and "given" in hire, (held(), hire.get("given")))
ws.player.party.remove(hire)

clerk = NPC(id="c3", name="Emlily Wickley", people="human", role="farmer", location=ws.player.location)
store.save_npc(clerk)
q = contract()
q["guild"] = True                                       # a guild contract with an issuer of its own (engine/stakes.py): the clerk pays it
ws.clerk_here = lambda: store.load_npc("c3")
ws.present = [store.load_npc("c3")] + ws.present
stub.plan = [{"kind": "give", "target": "c3", "item": name, "count": 3}]
ws.turn(f"I give the {name} to Emlily.")
check("a guild contract given to the clerk is handed in, though another asked for it", not ws.player.quests and held() == 0, ws.player.quests)

ws.player.quests = []
ws.player.character.inventory[:] = [i for i in ws.player.character.inventory if i.good != leaves] + [inv.make_good(leaves, 3)]
give(other)
check("goods no contract asks for are given at once, as before", held() == 0 and store.load_question() is None, held())
shutil.rmtree("saves/contract_goods_676_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
