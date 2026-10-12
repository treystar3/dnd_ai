"""Orenna: trigger, contact, the fixed ruin, the order, the trails, the Executioner, the High Keeper, the blessing."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import config
import ui.console as uc
SAID, NOTES, ANSWERS = [], [], []
uc.say = lambda t, s="": SAID.append((s, t))
uc.narrate = lambda t: SAID.append(("narrate", t))
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.ask = lambda: ANSWERS.pop(0) if ANSWERS else "n"
from engine import combat, orenna, pools, dungeons
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/orenna_chain_test", ignore_errors=True)
store = CampaignStore.open_or_create("orenna_chain_test")
store.meta.seed = 11; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
config.TURN_LOG_PATH = "saves/orenna_chain_test/turns.jsonl"
player = ws.player; c = player.character
ws.narrate = lambda e, t="": None
ws.show_exits = lambda *a, **k: None
ws.resolve = lambda check_name, **k: "strong success"
FIGHTS = []
import scenes.combat_scene as cs
REAL = cs.CombatScene
class FakeScene:
    @classmethod
    def begin(cls, w, creature, enemies, how, **k):
        FIGHTS.append((creature.id, enemies)); return None
cs.CombatScene = FakeScene

# the gate: level 50 and the name said aloud
c.level = 49
ws.orenna_named("Do you know the name Orenna?")
check("below level 50 nothing starts", orenna.stage(player) == "")
c.level = 50
ws.orenna_named("Tell me about the harvest")
check("without the name nothing starts", orenna.stage(player) == "")
ws.orenna_tick()
check("nothing is ever offered unprompted", orenna.stage(player) == "" and not SAID)
ws.orenna_named("Have you ever heard the name Orenna?")
check("saying the name at 50 starts it", orenna.stage(player) == "named")
o = player.orenna
check("four different great cities, never the capital", len({o["meeting"], *o["trails"]}) == 4 and "valecourt" not in {o["meeting"], *o["trails"]}, o)
ws.orenna_tick()
check("the contact does not come at once", orenna.stage(player) == "named" and not SAID)
store.meta.minutes = o["due"] + 1
ANSWERS[:] = ["I heard it in a dream", "y"]
ws.orenna_tick()
check("the contact asks how you know the name and the coin is shown", any("half-circle" in t for s, t in SAID if s == "narrate") and any("how you came by it" in t for s, t in SAID))
check("agreeing takes you to the ruin", orenna.stage(player) == "ruin" and player.location == "dungeon_first_hall", (orenna.stage(player), player.location))
d = next(x for x in store.load_dungeons() if x["id"] == "dungeon_first_hall")
check("the ruin is fixed and has the four floors in story order", d["fixed"] == "orenna" and [f["title"] for f in d["floors"]] == ["The servants", "The gift", "The revolt", "The long forgetting"])
check("it is never remade", dungeons.due_for_respawn(d, d["made"] + 10 ** 7) is False)
check("it is scaled for level 50 and up", all(f["level"] >= 50 for f in d["floors"]))
check("it ends with the Warden as a boss", d["floors"][-1]["chambers"][-1]["boss"] and d["floors"][-1]["chambers"][-1]["creature"] == "forgetting_warden")
ws.ensure_dungeons()
d2 = next(x for x in store.load_dungeons() if x["id"] == "dungeon_first_hall")
check("ensure_dungeons leaves it alone", d2["made"] == d["made"] and d2["fixed"] == "orenna")

# the floors tell the truth in order
SAID.clear()
shown = []
for f, floor in enumerate(d["floors"]):
    last_c = len(floor["chambers"]) - 1
    SAID.clear()
    ws.chamber_cleared(d, f, last_c)
    shown.append(" ".join(t for s, t in SAID if s == "narrate"))
check("floor 1 shows mindless servants", "identical figures" in shown[0] or "rows of identical" in shown[0])
check("floor 2 shows Orenna giving life and will", "Orenna" in shown[1] and "eyes alight" in shown[1])
check("floor 3 shows the revolt and her binding", "turned on the gods" in shown[2] and "bind the woman" in shown[2])
check("floor 4 shows the long forgetting and the door", "cutting her name" in shown[3] and "door" in shown[3])
k = c.knowledge
check("each floor adds its fact to the journal", all(x in k for x in ("orenna_servants", "orenna_gift", "orenna_revolt", "orenna_forgetting")))
check("after the last floor the way out is set", orenna.stage(player) == "leaving")
ws.orenna_tick()
check("Odrin leads you out to the meeting city, and the order meets you", player.location == o["meeting"] and orenna.stage(player) == "trails", (player.location, orenna.stage(player)))
check("you carry the half-circle coin", any(x.id == "order_coin" for x in c.key_items))
check("the order's lore is learned", "orenna_order" in c.knowledge)

# the three trails
SAID.clear()
for i in (0, 1):
    player.location = o["trails"][i]
    ws.orenna_tick()
check("two trails bring the Bound Executioner", o["executioner"] is True and any("I never do" in t for s, t in SAID))
check("he is left alone when not pressed", not FIGHTS)
check("two trails are recorded", o["trails_done"] == [0, 1])
player.location = o["trails"][2]
ws.orenna_tick()
check("the third completes them", orenna.stage(player) == "registry" and o["evidence"] == 3.0, (orenna.stage(player), o.get("evidence")))
check("trail lore is learned", all(x in c.knowledge for x in ("orenna_trail_lecturer", "orenna_trail_letter", "orenna_trail_warning", "orenna_executioner")))
ws.orenna_tick()
check("no step repeats elsewhere", orenna.stage(player) == "registry")

# pressing the Executioner is a real fight
o2_before = list(o["trails_done"])
ws.orenna_executioner_test = None
ANSWERS[:] = ["y"]
ws.orenna_executioner()
check("pressing him starts a fight", FIGHTS and FIGHTS[-1][0] == "bound_executioner")
ws.orenna_fight_over("victory")
check("he escapes in a flash, saying nothing", any("flash of pale light" in t for s, t in SAID if s == "narrate") and not any("Thank you" in t for s, t in SAID))
check("he warns you first", any("I would rather you did not" in t for s, t in SAID))
foe = FIGHTS[-1][1][0]
check("the first fight is not lethal: he yields at a quarter health", foe.yields_at == 0.25 and foe.yield_text)
me2 = combat.fighter_from_character(c)
fx = combat.Combat(fighters=[me2, foe])
combat.take_damage(fx, foe, foe.max_hp * 5, me2, random.Random(3))
check("a huge blow cannot kill him; he breaks off instead", foe.alive and foe.fled and foe.hp >= 1 and not fx.enemies(), (foe.hp, foe.fled))
check("the narrator is told of the flash", any("flash of pale light" in x for x in fx.story))

# the register, then the High Keeper
FIGHTS.clear()
player.location = "valecourt"
ws.orenna_tick()
check("the register leads straight to the confrontation", orenna.stage(player) == "confront" and "orenna_registry" in c.knowledge)
check("the finale is the High Keeper with the Executioner beside him", FIGHTS and FIGHTS[-1][0] == "high_keeper" and len(FIGHTS[-1][1]) == 2)
keeper, bound = FIGHTS[-1][1]
check("the keeper is a boss with the seal", keeper.boss and keeper.boss.get("seal"))
check("the Executioner is bound", bound.bound)
check("strong evidence leaves the keeper with no guards to summon", keeper.boss["guards"] >= 4, keeper.boss)
check("the keeper has the phases of a boss", keeper.boss["tier"] == "leader" and "lines" in keeper.boss)

# wresting the seal
fight = combat.Combat(fighters=[combat.fighter_from_character(c), keeper, bound])
ANSWERS[:] = ["y"]
orenna.O["confront"]["seal"]["ask"]
import random as _r
keeper.boss["evidence"] = 3.0
tries = 0
while any(f.bound for f in fight.fighters) and tries < 40:
    fight.round = tries + 1
    ANSWERS[:] = ["y"]
    orenna.seal_prompt(fight, keeper); tries += 1
check("the seal can be wrested, freeing the Executioner from the fight", not any(f.bound for f in fight.fighters))
fight2 = combat.Combat(fighters=[combat.fighter_from_character(c), keeper, bound]); ANSWERS[:] = ["n"]
orenna.seal_prompt(fight2, keeper)
check("declining leaves him bound", any(f.bound for f in fight2.fighters))

# losing is not the end
ws.orenna_fight_over("defeat")
check("a lost fight keeps the quest at the confrontation", orenna.stage(player) == "confront" and not c.orenna_breath)
ws.orenna_fight = "keeper"
ws.orenna_fight_over("victory")
check("victory gives the blessing and ends the quest", orenna.stage(player) == "done" and c.orenna_breath and "orenna_last_breath" in c.knowledge)
check("she speaks one thin line", any(s == "Orenna" and "I heard" in t for s, t in SAID))
ws.orenna_tick(); ws.orenna_named("Orenna")
check("it never runs twice", orenna.stage(player) == "done")

# Orenna's Last Breath
c.health = pools.maximum(c, "health"); c.mana = pools.maximum(c, "mana")
me = combat.fighter_from_character(c)
check("the blessing enters the fight", me.breath)
foe = combat.fighter_from_creature(world.bestiary["hall_guardian"], 60, "boss", "e1", "guardian", "near")
fight3 = combat.Combat(fighters=[me, foe])
rng = random.Random(1)
me.hp = 5; me.mana = 0
dealt = combat.take_damage(fight3, me, 99999, foe, rng)
check("a killing blow restores health and mana in full", me.hp == me.max_hp and me.mana == me.max_mana and not me.breath, (me.hp, me.max_hp))
combat.take_damage(fight3, me, 99999, foe, rng)
check("the second killing blow kills", me.hp == 0)
scene = REAL.__new__(REAL)
scene.ws, scene.fight = ws, fight3
fight3.fighters[0] = me
REAL.sync_player(scene)
check("the blessing is gone from the character afterwards", c.orenna_breath is False)
other = combat.fighter_from_character(c)
check("a new fight does not carry it", other.breath is False)

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
