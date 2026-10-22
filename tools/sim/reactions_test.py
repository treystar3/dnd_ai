"""The world-reaction bus (engine/domain_events.py Deed family, engine/reactions.py, data/rules/reactions.yaml): a deed published once
reaches every store that should notice it - who remembers and trusts less, standing, reputation, heat, the companions, the deeds ledger,
the journal - through the scene's own copies of the people here; nothing is recorded twice; an unknown kind or a lawless place is
skipped, not raised. And a turn that fails is taken back whole: the clock too."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
STUB = simlib.Stub("warrior", 5)
simlib.install(STUB)
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import clock, domain_events as de, law, reactions, standing
from engine.domain_events import (Bribe, ContractDone, Deed, Persuaded, Rested, Theft, publish)
from llm.contracts import ActionIntent as A
from llm.gateway import LLMError
from npc.models import NPC
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
from dataclasses import dataclass, field
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/reactions_test", ignore_errors=True)
store = CampaignStore.open_or_create("reactions_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 120; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
config.TURN_LOG_PATH = "saves/reactions_test/turns.jsonl"
config.AUDIT_ENABLED = False
mer = NPC(id="m1", name="Osric Vane", people="human", role="merchant", location="trading_square", traits=[], trust=50); store.save_npc(mer)
frm = NPC(id="f1", name="Tilda Rook", people="human", role="farmer", location="trading_square", traits=[], trust=50); store.save_npc(frm)
grd = NPC(id="g1", name="Garran Holt", people="human", role="guard", location="trading_square", traits=[], trust=50); store.save_npc(grd)
ws.residents = ws.present = [mer, frm, grd]
from engine import money, pulse
store.save_world_state(pulse.empty_state(ws.minutes))      # the world has begun: the ledger lives in its state
DEEDS = []
ws.deed = lambda d: DEEDS.append(d)
day = clock.day(ws.minutes)

check("people here come back as the scene's own copies", ws.npc_by_id("m1") is mer and ws.npc_by_id("nobody") is None)
far = NPC(id="x1", name="Far Away", people="human", role="miller", location="willowmead", traits=[], trust=50); store.save_npc(far)
check("anyone else is loaded from the store", ws.npc_by_id("x1") is not None and ws.npc_by_id("x1") is not far)

# ---- a theft, seen by the victim and a bystander
with store.transaction():
    publish(Theft(minute=ws.minutes, place="trading_square", witnesses=("m1", "f1"), npc="m1", name=mer.label(), item="a silver cup", took=True, story=False, value=5000))
check("the victim remembers being caught, and trusts less", any(m.text == "Caught the stranger taking a silver cup from me." and m.importance == 3 for m in mer.memories) and mer.trust == 35, ([m.text for m in mer.memories], mer.trust))
check("the bystander remembers seeing it", any(m.text == f"Saw the stranger took a silver cup from {mer.label()}." for m in frm.memories) and frm.trust == 45, [m.text for m in frm.memories])
check("the guard, who saw nothing, remembers nothing", not grd.memories)
check("standing moves in the town at once", standing.value(ws.player, "parth", "merchants", day) == -5 and standing.value(ws.player, "parth", "outlaws", day) == 3, ws.player.standing)
check("the watch hears of it", law.current_heat(ws.player, "parth", day) > 0, ws.player.heat)
deeds = store.load_world_state().get("deeds", []) if store.load_world_state() else []
check("the ledger has the offense, with the keys the paths read", any(d["kind"] == "offense" and d["offense"] == "theft" and d["witnesses"] == ["m1", "f1"] for d in deeds), deeds)
rows = store.journal_tail(5, kind="theft")
check("the journal has the deed, by the player, against the victim", rows and rows[-1]["actor"] == "player" and rows[-1]["target"] == "m1", rows)
check("it was written to the store through the held copy", any("silver cup" in m.text for m in store.load_npc("m1").memories))

# ---- a theft nobody saw
heat0 = law.current_heat(ws.player, "parth", day); st0 = dict(ws.player.standing.get("parth", {}))
with store.transaction():
    publish(Theft(minute=ws.minutes, place="trading_square", witnesses=(), npc="m1", name=mer.label(), item="a loaf", took=True))
check("an unseen theft leaves the owner a memory that something is gone", any("Loaf" in m.text or "loaf" in m.text and "gone missing" in m.text for m in mer.memories), [m.text for m in mer.memories][-1:])
check("but no tale, no heat and no ledger row", law.current_heat(ws.player, "parth", day) == heat0 and dict(ws.player.standing.get("parth", {})) == st0 and len(store.load_world_state().get("deeds", [])) == 1)

# ---- a lawless place: people still remember, the town has no law and no standing to move
heat0 = law.current_heat(ws.player, "parth", day); st0 = dict(ws.player.standing.get("parth", {})); n0 = len(mer.memories)
with store.transaction():
    publish(Theft(minute=ws.minutes, place="south_fields", witnesses=("m1",), npc="m1", name=mer.label(), item="a hat", took=False))
check("in the wild the victim remembers but nothing else moves", len(mer.memories) == n0 + 1 and law.current_heat(ws.player, "parth", day) == heat0 and dict(ws.player.standing.get("parth", {})) == st0)

# ---- a bribe to the watch, in a confrontation: the tale is about the watch, and the companions see it
with store.transaction():
    publish(Bribe(minute=ws.minutes, place="trading_square", witnesses=("g1",), npc="g1", name=grd.label(), amount=300, worked=True, degree="success", favor="forget what they knew", confrontation=True, guard=True))
check("the guard remembers taking it", any(m.text == f"Took {money.words(300)} from the stranger to forget what I knew." for m in grd.memories), [m.text for m in grd.memories])
check("the watch's standing drops and the outlaws warm", standing.value(ws.player, "parth", "guards", day) < -3 and standing.value(ws.player, "parth", "outlaws", day) > 3, ws.player.standing)
check("the companions get their say on it", DEEDS == ["bribe"], DEEDS)
with store.transaction():
    publish(Bribe(minute=ws.minutes, place="trading_square", witnesses=("m1",), npc="m1", name=mer.label(), amount=100, worked=False, degree="failure", favor="look the other way at the gate", confrontation=False, guard=False))
check("a refused bribe in talk is remembered with what it was for, and starts no tale about the watch",
      any(f"tried to bribe me with {money.words(100)} (look the other way at the gate). I refused" in m.text for m in mer.memories) and standing.value(ws.player, "parth", "guards", day) == standing.value(ws.player, "parth", "guards", day), [m.text for m in mer.memories][-1:])

# ---- a finished guild contract: the clerk remembers, the guild thinks more of you, the town does too
rep0 = ws.player.reputation.get("parth", 0)
with store.transaction():
    publish(ContractDone(minute=ws.minutes, place="trading_square", witnesses=("g1",), npc="g1", name=grd.label(), quest="q1", title="Wolves at the fold", guild=True, coins=1200, letter="F"))
check("the payer remembers paying", any("finished wolves at the fold; I paid" in m.text for m in grd.memories), [m.text for m in grd.memories][-1:])
check("the guild and the town think more of you", standing.value(ws.player, "parth", "guild", day) == 4 and ws.player.reputation.get("parth", 0) == rep0 + 4, (ws.player.standing, ws.player.reputation))

# ---- flags pick the companions' deeds and the reputation key
DEEDS.clear()
with store.transaction():
    publish(Rested(minute=ws.minutes, place="tilted_plough", inn=True, late=True, slept=True))
check("a late sleep at an inn is two things the companions may mind", sorted(DEEDS) == ["inn", "sleep_late"], DEEDS)
rep0 = ws.player.reputation.get("parth", 0)
with store.transaction():
    publish(Persuaded(minute=ws.minutes, place="trading_square", witnesses=("m1",), npc="m1", name=mer.label(), how="intimidation", degree="success"))
check("an intimidation is a threat the town notes, and a deed the ledger keeps", ws.player.reputation.get("parth", 0) == rep0 - 2 and any(d["kind"] == "persuade" and d["degree"] == "success" for d in store.load_world_state()["deeds"]))

# ---- a kind the table does not know is skipped; registering again does not double anything
@dataclass(frozen=True)
class Odd(Deed):
    kind: str = field(init=False, default="odd_thing")
n0 = len(mer.memories)
with store.transaction():
    publish(Odd(minute=ws.minutes, witnesses=("m1",), npc="m1"))
check("an unknown kind of deed is nothing to the world (and not an error)", len(mer.memories) == n0)
reactions.register(ws); reactions.register(ws)
with store.transaction():
    publish(Theft(minute=ws.minutes, place="trading_square", witnesses=("f1",), npc="f1", name=frm.label(), item="an apple", took=True))
check("registered three times, a deed is still remembered once", sum("apple" in m.text for m in frm.memories) == 1, [m.text for m in frm.memories])

# ---- what the town can be told of it: the "lately" facet, by who saw what
from engine import truth
sc = truth.Scene(ws)
facts = sc.facts("lately")
cup = next((f for f in facts if "silver cup" in f.text), None)
job = next((f for f in facts if "Wolves at the fold" in f.text), None)
check("a seen deed is a fact here, tagged for those who saw it and the narrator", cup is not None and {"npc:m1", "npc:f1", "narrator"} <= cup.known and "all" not in cup.known, cup)
check("a public deed is known to everyone", job is not None and "all" in job.known, job)
check("the unseen theft is no fact at all", not any("loaf" in f.text for f in facts), [f.text for f in facts])
bystander, guard_v, narrator = truth.Viewer(id="f1", kind="npc"), truth.Viewer(id="g1", kind="npc"), truth.Viewer(kind="narrator")
check("the bystander knows of the theft, the guard who was elsewhere does not, the narrator does", bystander.sees(cup) and not guard_v.sees(cup) and narrator.sees(cup))
check("the facet is in the townsfolk's and the narrator's views", "lately" in truth.T["profiles"]["townsfolk"] and "lately" in truth.T["profiles"]["narrator"] and truth.T["headers"].get("lately"))

# ---- a dropped guild contract is a mark against them with the guild, even with nobody to tell
from engine.domain_events import ContractDropped
g0 = standing.value(ws.player, "parth", "guild", day)
with store.transaction():
    publish(ContractDropped(minute=ws.minutes, place="trading_square", quest="q2", title="Rats in the granary", how="abandoned", guild=True))
check("a guild contract dropped costs standing with the guild", standing.value(ws.player, "parth", "guild", day) == g0 - 2, (g0, standing.value(ws.player, "parth", "guild", day)))

# ---- the news list keeps the tales that move standing; the journal does not grow without bound
news = [{"text": f"gossip {i}", "origin": "parth", "minute": i, "groups": ["everyone"]} for i in range(305)]
news[0]["deed"] = {"id": "d0"}; news[1]["deed"] = {"id": "d1"}
kept = pulse.cap_news(news)
check("past the cap the oldest gossip goes first and the tales stay", len(kept) == pulse.NEWS_KEEP and kept[0].get("deed") and kept[1].get("deed") and kept[2]["text"] == "gossip 7", (len(kept), kept[:3]))
n_before = len(store.journal_tail(10000))
for i in range(12):
    store.journal(ws.minutes, "test_row", "player", "", f"row {i}")
gone = store.journal_trim(keep=5)
check("the journal is trimmed to what is kept, oldest first", len(store.journal_tail(10000)) == 5 and gone == n_before + 12 - 5 and store.journal_tail(1)[-1]["text"] == "row 11", (gone, len(store.journal_tail(10000))))

# ---- a turn that fails is taken back whole, the clock included
for k in ("on_look",):
    def boom(intent, text):
        ws.advance(30)
        raise LLMError("the model is away")
    setattr(ws, k, boom)
ws.run_checks = lambda intent, text: False
ws.interpret = lambda text, hint="": [A(kind="look")]
minutes0, turn0 = store.meta.minutes, store.meta.turn
ok = ws.turn("I look around")
check("the failed turn is rolled back and the clock goes back with it", ok is False and store.meta.minutes == minutes0 and store.meta.turn == turn0, (store.meta.minutes, minutes0))

print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)
