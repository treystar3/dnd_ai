"""(f417) What the turn gives and leaves, told as it is. A night's after-fight passage slid an amulet into a pocket a line after the game had
left it on the ground for want of room, and a bought tonic left on the ground was narrated as handed over; a road find was 'taken' with
the pack full; a smith said he did not deal in cloth and then bought the hood, because his answer was written before the sale; and a won
road fight walked on before the player had said what becomes of the one who yielded, while the arrival never heard of the fight."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 7))
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
for fn in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import combat, inventory as inv, ledger, spells
from llm.contracts import ActionIntent as A
from llm.gateway import LLMError
from npc.traits import load_traits
from scenes import combat_scene as cs, road_actions as ra
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/left_lying_417_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("left_lying_417_test")
store.meta.seed = 7; store.meta.turn = 1; store.meta.minutes = 900; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(7))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("parth")

def fill_pack():
    while len(ws.pack) < ws.pack_slots():
        ws.pack.append(inv.make_good("trail_ration", inv.stack_size(inv.make_good("trail_ration", 1))).model_copy(update={"uid": f"x{len(ws.pack)}"}))

# ---- to_pack says what it kept and what it left, and the turn keeps both
ledger.begin()
ws.pack.clear()
st = ws.to_pack(inv.make_good("healing_draught", 1))
check("a thing that fits is kept, and nothing is left", st.kept is not None and st.left is None
      and any(r["kind"] == "gained" for r in ledger.ROWS), (st, ledger.ROWS))
ws.pack.clear()
fill_pack()
ledger.begin()
st = ws.to_pack(inv.make_good("healing_draught", 1))
on_ground = [inv.label(i) for i in ws.ground_here()]
check("with the pack full, it is left on the ground, and said so", st.kept is None and st.left is not None
      and any("draught" in g.lower() for g in on_ground), (st, on_ground))
check("...and the turn's record says it lies here, never to be shown taken", any(r["kind"] == "left" and "Never show it taken" in r["say"]
                                                                                  for r in ledger.ROWS), ledger.ROWS)
check("whether a thing will fit can be asked without putting it there", not inv.fits(ws.pack, inv.make_good("healing_draught", 1), ws.pack_slots())
      and inv.fits([], inv.make_good("healing_draught", 1), ws.pack_slots()))

# ---- the passage after a fight: what was left is LEFT LYING HERE, not found and pocketed
book = next((b for b in (spells.book_drop(20, "normal", random.Random(s)) for s in range(500)) if b), None)
real_drop = spells.book_drop
spells.book_drop = lambda level, rank, rng: book.model_copy(update={"uid": f"book{rng.random()}"})
asked = []
real_fresh = cs.fresh
cs.fresh = lambda task, system, request, *a, **k: (asked.append((task, request)), real_fresh(task, system, request, *a, **k))[1]
creature = world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 3, "normal", "e1", name="wolf 1")
ws.narrate_with = lambda *a, **k: None
sc = cs.CombatScene.begin(ws, creature, [foe], "It is on you:")
ws.combat = sc
foe.hp = 0
sc.fight.over = "victory"
ledger.begin()
sc.victory()
ws.combat = None
spells.book_drop, cs.fresh = real_drop, real_fresh
after = next((r for t, r in asked if t == "combat_aftermath"), "")
finds = next((l for l in after.split("\n") if l.startswith("THE PLAYER FINDS")), "")
lying = next((l for l in after.split("\n") if l.startswith("LEFT LYING HERE")), "")
name = inv.label(book).lower() if book else "?"
check("a full pack after a fight: the find is LEFT LYING HERE", book is not None and name in lying.lower(), (name, lying, finds))
check("...and not among what the player finds and takes up", name not in finds.lower(), finds)
check("...told once, under its own head, not again among what the game did", after.count("LEFT LYING here") == 0, after[-800:])

# ---- a road find with the pack full is told as left, before the scene is written
road = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places and ra.roads.nearby_wilds(world, r.from_, r.to))
prompts = []
real_gen = ra.generate
ra.generate = lambda task, system, user, *a, **k: (prompts.append(user), (_ for _ in ()).throw(LLMError("test")))[1]
saved = {k: ra.R[k] for k in ("hostile", "kinds")}
ra.R["hostile"], ra.R["kinds"] = 0.0, {"find": 1}
ws.road_event([road.from_, road.to], road.from_, road.to, 120, 0.5, "I walk on", [])
ra.R.update(saved)
ra.generate = real_gen
check("(f427) a find on the road, the pack full or not: the scene is told it lies there untouched, the player's to take", prompts
      and "untouched" in prompts[-1] and "finds and takes" not in prompts[-1], prompts[-1][-500:] if prompts else "no prompt")

# ---- a deal settled is a row a person's answer reads
ws.pack.clear()
ws.enter("tilted_plough")
smith = next((n for n in ws.present if ws.world.roles[n.role].buys), None) or next(iter(ws.present), None)
ledger.begin()
if smith is not None:
    hide = inv.make_good("healing_draught", 1)
    ws.finish_sale(hide, smith, "I sell it", quiet=True)
check("a sale settled is on the turn's record, for the buyer's answer", smith is not None and any(r["kind"] == "received" and "settled" in r["say"]
                                                                                             for r in ledger.ROWS), ledger.ROWS)
check("...and a word with someone before a deal with them waits for the deal (the plan repair is declared)",
      any(r.name == "deal_then_word" for r in ws.REPAIR_TABLE))

# ---- a won road fight: the arrival hears of it, and the walk waits on a yield
ws.player.road = {"id": "road_x", "from": road.from_, "to": road.to, "title": "Wolves on the ford", "log": ["Wolves on the ford: they come."],
                  "resume": road.to, "text": "I walk on"}
ws.road_fight_over("victory")
check("a won road fight is kept to tell at the arrival", any("fought it out there, won" in l for l in ws.player.road["log"]), ws.player.road["log"])
resumed = []
ws.resume_road = lambda: (resumed.append(1), setattr(ws, "resume_pending", None))
ws.held_yield = [types.SimpleNamespace(name="bandit 1", side="enemy")]
ws.handle = lambda text: None
ws.turn("I look at the bandit")
check("...and the walk does not go on while the one who yielded waits on the player's word", not resumed and ws.resume_pending)
ws.held_yield = None
ws.turn("I spare him")
check("...and goes on once that is settled", resumed)
told = []
ws.narrate = lambda event, text="", *a, **k: told.append(event)
ws.finish_journey([road.from_, road.to], 180, "I walk on", ws.player.road["log"])
check("the arrival is told the fight happened, as something already read", told and "fought it out there" in told[-1]
      and "do not tell it again" in told[-1], told[-1:])

store.close()
shutil.rmtree("saves/left_lying_417_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
