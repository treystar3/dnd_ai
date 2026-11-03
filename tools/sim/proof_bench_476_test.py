"""(f476) The proof bench Bundle D is checked with. The store-reading helpers (simlib.remembered, obligation, reset_person, heard_by) find
what a person remembers and owes by what it is, through every row, not only the window their record carries; the stand-in embedder is
the same in every process; and the embedding cache is the campaign's, so nothing of it outlives a closed campaign."""
import subprocess
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
from engine import clock
from llm import embed
from npc.models import NPC, Memory

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("proof_bench_476")
store = game.session.store
far = NPC(id="pb1", name="Hob Marl", people="human", role="farmer", location="parth", traits=[], trust=50)
far.memories.append(Memory(day=1, turn=1, text="Saw the stranger took a torch from the merchant.", importance=2))
far.memories.append(Memory(day=1, turn=2, text="The stranger bought a sack of seed from me.", importance=1))
store.save_npc(far)
for i in range(30):                                                       # thirty defining rows push the first out of the window
    far = store.load_npc("pb1")
    far.memories.append(Memory(day=2 + i, turn=3 + i, text=f"A hard winter's night, the {i}th.", importance=3))
    store.save_npc(far)
window = [m.text for m in store.load_npc("pb1").memories]
check("the torch is out of the farmer's window, behind thirty defining rows", not any("torch" in t for t in window), len(window))
seen = simlib.remembered(store, "pb1", kind="witnessed", about="torch")
check("...and remembered() still finds it, by kind, through the store", len(seen) == 1 and seen[0]["subject"] == "player", seen)
check("...an ordinary dealing is experienced", simlib.remembered(store, "pb1", kind="experienced", about="seed"), simlib.remembered(store, "pb1")[:2])
own = NPC(id="pb2", name="Ma Tull", people="human", role="innkeeper", location="parth", traits=[], trust=50)
own.memories.append(Memory(day=1, turn=-1, text="(my own life) Buried my brother in the spring.", importance=2))
own.memories.append(Memory(day=2, turn=-1, text="I dealt with the bridge quarrel myself, in the end.", importance=2))
own.memories.append(Memory(day=3, turn=4, text="Hob Marl settled the bridge quarrel.", importance=2))
store.save_npc(own)
check("a person's own life is own_life, an anchor's settling too, and a matter's end is heard",
      len(simlib.remembered(store, "pb2", kind="own_life")) == 2 and simlib.remembered(store, "pb2", kind="heard", about="bridge"),
      simlib.remembered(store, "pb2"))
check("heard_by names who heard of a thing they did not see", simlib.heard_by(store, "bridge quarrel") == ["pb2"], simlib.heard_by(store, "bridge quarrel"))
try:
    simlib.remembered(store, "pb1", source="town")
    refused = False
except ValueError:
    refused = True
check("asking by what the save does not record yet (a source) is refused, never a quiet pass", refused)
simlib.reset_person(store, "pb1")
check("reset_person leaves no row and an empty window", simlib.remembered(store, "pb1") == [] and store.load_npc("pb1").memories == [])

far = store.load_npc("pb1")
far.work_offer = {"task": "Mend the fence by the barn", "pay": 5, "minutes": 120, "until": store.meta.minutes + 600}
far.quest_offer = {"id": "rq1", "title": "Wolves at the fold", "letter": "F"}
store.save_npc(far)
p = store.load_player()
p.quests.append({"id": "qq1", "title": "Clear the cellar rats", "kind": "hunt", "issuer": "pb1", "letter": "F", "guild": False, "count": 1, "progress": 0})
store.save_player(p)
ob = simlib.obligation(store, "pb1")
check("obligation() reads what a person offers and is owed in one shape",
      {(o["id"], o["state"]) for o in ob} == {("work:pb1", "open"), ("request:pb1", "offered"), ("qq1", "taken")}, ob)
check("...and by words in its title", [o["id"] for o in simlib.obligation(store, "pb1", about="cellar")] == ["qq1"])

fake = simlib.FakeEmbedder()
v = fake.embed(input=["the wolves at the fold"])["embeddings"][0]
code = ("import sys; sys.path.insert(0, '.'); import simlib; print(simlib.FakeEmbedder().embed(input=['the wolves at the fold'])['embeddings'][0])")
outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={"PYTHONHASHSEED": s, "PATH": "/usr/bin:/bin"}).stdout.strip() for s in ("1", "2")}
check("the stand-in embedder gives the same vectors in every process", len(outs) == 1 and outs == {str(v)}, outs)
one, two = simlib.two_characters(game.scene)
check("two_characters gives the player's character and another", one is game.scene.player.character and two.name and two.name != one.name, (one.name, two.name))

embed._cache["a line"] = [1.0]
check("a warm embedding cache is the campaign's: residue names it while it is open", "embed._cache" in simlib.residue(), simlib.residue())
game.close()
check("...and closing the campaign leaves nothing of it in the process", simlib.residue() == {} and not embed._cache, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
