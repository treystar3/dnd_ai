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

def rerun_census() -> list:
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("stub_party_script", Path("data/replay/scripts/stub_party.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import rerun
    return mod.census(rerun.load(rerun.golden("stub_party")))


bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("proof_bench_476")
store = game.session.store
far = NPC(id="pb1", name="Hob Marl", people="human", role="farmer", location="parth", traits=[], trust=50)
far.memories.append(Memory(day=1, turn=1, text="Saw {them} took a torch from the merchant.", importance=2, kind="witnessed"))
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
own.memories.append(Memory(day=1, turn=-1, text="Buried my brother in the spring.", importance=2, kind="own_life", subject=""))
own.memories.append(Memory(day=2, turn=-1, text="I dealt with the bridge quarrel myself, in the end.", importance=2, kind="own_life", subject=""))
own.memories.append(Memory(day=3, turn=4, text="Hob Marl settled the bridge quarrel.", importance=2, kind="heard", subject="", source="town"))
store.save_npc(own)
check("a person's own life is own_life, an anchor's settling too, and a matter's end is heard",
      len(simlib.remembered(store, "pb2", kind="own_life")) == 2 and simlib.remembered(store, "pb2", kind="heard", about="bridge"),
      simlib.remembered(store, "pb2"))
check("heard_by names who heard of a thing they did not see", simlib.heard_by(store, "bridge quarrel") == ["pb2"], simlib.heard_by(store, "bridge quarrel"))
check("since f478 a memory's source is recorded and can be asked by", [r["text"] for r in simlib.remembered(store, "pb2", source="town")]
      == ["Hob Marl settled the bridge quarrel."], simlib.remembered(store, "pb2"))
simlib.reset_person(store, "pb1")
check("reset_person leaves no row and an empty window", simlib.remembered(store, "pb1") == [] and store.load_npc("pb1").memories == [])

simlib.offer(store, "pb1", "work", {"task": "Mend the fence by the barn", "pay": 5, "minutes": 120})     # (f481) offers in the registry
simlib.offer(store, "pb1", "request", {"id": "rq1", "title": "Wolves at the fold", "letter": "F"})
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

# ---- what an input changed, by row, and the re-bless report that names every key
import io, contextlib
import rerun
from storage import statehash
before = {"npc_memory": [[1, "f1", 1, 1, "event", 1, "Sold the stranger seed.", 0]], "npcs": [["f1", {"trust": 50, "met_player": False}]],
          "kv": [], "places": [], "event_log": [], "entities": []}
after = {"npc_memory": [[1, "f1", 1, 1, "experienced", 1, "Sold {them} seed.", 0], [2, "f1", 1, 2, "event", 1, "Talked.", 0]],
         "npcs": [["f1", {"trust": 52, "met_player": True}]], "kv": [], "places": [], "event_log": [], "entities": []}
ch = statehash.changes(before, after)
check("changes() names a row added, a column changed and a JSON key moved (keyed as a recording's JSON keeps them)",
      "2" in ch["npc_memory"]["added"] and ch["npc_memory"]["changed"]["1"] == {"4": "experienced", "6": "Sold {them} seed."}
      and ch["npcs"]["changed"]["f1"] == {"1.met_player": "true", "1.trust": "52"}, ch)
old_t = [{"i": 7, "state": {"all": "a", "npc_memory": "x"}, "rows": {"npc_memory": {"changed": {1: {"4": "event"}}}}}]
new_t = [{"i": 7, "state": {"all": "b", "npc_memory": "y"}, "rows": {"npc_memory": {"changed": {1: {"4": "experienced", "8": "player"}}}}}]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rerun.report_rows({"turns": old_t}, {"turns": new_t}, list(zip(old_t, new_t)))
said = buf.getvalue()
check("the re-bless report names every key that moved in each recording, with both values",
      "npc_memory 1 changed" in said and "4 'event' -> 'experienced'" in said and "8 '(unchanged)' -> 'player'" in said, said)
rec_new = rerun.load(rerun.golden("stub_party"))
place = rerun.placement(rec_new)
check("calls are placed by the kind of operation they were made in: the townsfolk's replies inside the talk, the party's outside any",
      "action:talk" in place.get("npc_conversation", {}) and "action:talk" not in place.get("hire_chat", {}), place)
check("stub_party holds a reply that failed every try and the same line said again, and its census is whole",
      any(c.get("title") == "NPCReply" and c.get("error") for c in rec_new["calls"]) and not rerun_census(), rerun_census())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
