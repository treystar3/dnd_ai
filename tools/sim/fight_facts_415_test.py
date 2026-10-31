"""(f415) The fight's writers are told what the engine knows of who stands: a foe who yielded or fled is out of the fight, not a wounded
foe still in it; a foe turned by the player's magic fights for them; each companion's line says how hurt they are now; and the passage
after the fight is told who is still on their feet, and how hurt. Before, all of it was left for the narrator to guess."""
import random, re, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import ui.console as uc
for fn in ("narrate", "say", "npc_says", "dialogue", "ledger", "note"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import combat, quirks
from npc.traits import load_traits
from scenes import combat_scene as cs
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/fight_facts_415_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("fight_facts_415_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 900; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(5))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
odly = {"id": "h1", "name": "Odly Garth", "role": "fighter", "level": 2, "permanent": True, "rank": "F", "bond": 12, "pronoun": "she",
        "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "a sellsword with a dented shield"}
quirks.roll(odly, random.Random(1))
ws.player.party = [odly]
ws.player.party_mode = "with"
ws.enter("parth")

asked = []
real_fresh = cs.fresh
cs.fresh = lambda task, system, request, *a, **k: (asked.append((task, request)), real_fresh(task, system, request, *a, **k))[1]

creature = world.bestiary["bandit"]
foes = [combat.fighter_from_creature(creature, 3, "normal", f"e{i}", name=f"bandit {i + 1}") for i in range(4)]
for e in foes:
    e.hp = e.max_hp = 10 ** 5
ws.narrate_with = lambda *a, **k: None
sc = cs.CombatScene.begin(ws, creature, foes, "It is on you:")
ws.combat = sc
f = sc.fight
yielded, fled, turned, fighting = foes
yielded.fled = yielded.surrendered = True
fled.fled = True
turned.counters["turned"] = 1
ally = next(a for a in f.fighters if a.side == "ally" and a.name == "Odly Garth")
ally.hp = ally.max_hp * 0.2

# ---- each round's request
asked.clear()
f.story = ["you strike the fourth bandit"]
sc.narrate_round("I swing at the last of them")
req = next((r for t, r in asked if t == "combat_narrate"), "")
foes_line = re.search(r"FOES NOW: (.*)", req).group(1) if "FOES NOW" in req else ""
out_line = re.search(r"OUT OF THE FIGHT[^:]*: (.*)", req).group(1) if "OUT OF THE FIGHT" in req else ""
check("a foe who yielded is not among the foes still fighting", combat.who(yielded) not in foes_line and combat.who(fighting) in foes_line, foes_line)
check("...nor one who fled", combat.who(fled) not in foes_line, foes_line)
check("...both are out of the fight, the one yielded and the other gone", "has yielded" in out_line and combat.who(yielded) in out_line
      and "has fled" in out_line and combat.who(fled) in out_line, out_line)
check("a foe the player turned is told as fighting for the player", re.search(re.escape(combat.who(turned)) + r"[^;]*fights for the player", foes_line),
      foes_line)
odly_line = next((l for l in req.split("\n") if "Odly Garth" in l and "fights with" in l), "")
check("each companion's line says how hurt they are now", odly_line.endswith("NOW: barely standing"), odly_line)
ally.hp = 0
asked.clear()
sc.narrate_round("I swing again")
req = next((r for t, r in asked if t == "combat_narrate"), "")
check("...and when one falls, that they are down and out of it", any(l.endswith("NOW: down, out of the fight") for l in req.split("\n")
                                                                       if "Odly Garth" in l), req[-600:])
fighting.fled = turned.fled = True
asked.clear()
sc.narrate_round("I look round")
req = next((r for t, r in asked if t == "combat_narrate"), "")
check("with no foe fighting, none are left standing", "FOES NOW: none left standing" in req, re.search(r"FOES NOW: .*", req))

# ---- the passage after the fight
ally.hp = ally.max_hp * 0.4
for e in foes:
    e.fled = False
    e.counters.pop("turned", None)
    e.hp = 0
f.over = "victory"
asked.clear()
sc.victory()
after = next((r for t, r in asked if t == "combat_aftermath"), "")
feet = re.search(r"ON THEIR FEET \([^)]*\): (.*)", after).group(1) if "ON THEIR FEET" in after else ""
check("the passage after the fight is told who is still on their feet, and how hurt", feet == "Odly Garth, badly wounded", feet or after[:400])
check("...told as a fact, not a pose each", "not a pose each" in after)

ws.combat = None
cs.fresh = real_fresh
store.close()
shutil.rmtree("saves/fight_facts_415_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
