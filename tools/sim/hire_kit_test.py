"""(f396) What a hire can do besides a plain blow (party.yaml kits; engine/techniques.py), and a priest's care outside a fight: a priest
heals when it matters, blesses the party at the start, and tends wounds after a fight and when asked; a fighter shields the player; an
archer pins a foe; a rogue strikes a foe busy with someone else; a mage hits every foe bunched together."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
for f_ in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f_, lambda *a, **k: None)
from engine import combat, party, pools, techniques
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
ch, _ = simlib.make_character("warrior", random.Random(2))
ch.level = 5

def fight(roles, foes=2, foe="wolf"):
    me = combat.fighter_from_character(ch)
    allies = [party.fighter({"id": f"t{i}", "name": f"{r.title()} Voss", "role": r, "level": 5}) for i, r in enumerate(roles)]
    enemies = [combat.fighter_from_creature(world.bestiary[foe], 5, "normal", f"foe{i}", f"Wolf {i}", "engaged") for i in range(foes)]
    f = combat.Combat(fighters=[me] + allies + enemies, place="x", conditions=[], record=True)
    f.round = 1
    return f, allies, enemies

check("every role has techniques, and the data checks clean", techniques.problems() == [], techniques.problems())

# ---- the priest
f, (priest,), wolves = fight(["priest"])
combat.ally_turn(f, priest, random.Random(1))
check("a priest blesses the party at the start of a fight", f.player.counters.get("blessed") and priest.counters.get("blessed")
      and techniques.blessed(f.player, f) > 1.0, f.player.counters)
f.round = 6
check("...and the blessing wears off", techniques.blessed(f.player, f) == 1.0)
f.round = 2
f.player.hp = f.player.max_hp * 0.6
before = f.player.hp
combat.ally_turn(f, priest, random.Random(2))
spec = techniques.healing("priest")
check("a priest heals the player once they are hurt, by a share worth having", f.player.hp >= before + f.player.max_hp * spec["pct"] / 100 * 0.9,
      (before, f.player.hp, f.player.max_hp))
check("...shown in the fight's record by name", any(h.get("outcome") == "heal" and spec["name"] in h.get("label", "") and h.get("att") == priest.name
                                                   for h in f.hits), f.hits[-1:])
f.round = 3
f.player.hp = f.player.max_hp * 0.5
mid = f.player.hp
w_hp = sum(w.hp for w in wolves)
combat.ally_turn(f, priest, random.Random(3))
check("...not again until the heal is ready: the round between, they fight", f.player.hp == mid and sum(w.hp for w in wolves) <= w_hp)
f.round = 4
combat.ally_turn(f, priest, random.Random(4))
check("...and then again", f.player.hp > mid)
f.round = 5
f.player.hp = f.player.max_hp
priest.cooldowns.clear()
w_hp = sum(w.hp for w in wolves)
combat.ally_turn(f, priest, random.Random(5))
check("a priest with nobody hurt fights", sum(w.hp for w in wolves) <= w_hp and f.player.hp == f.player.max_hp)
f.round = 6
f.player.hp = 5
check("a priest told to heal heals every turn they are told", combat.give_order(f, priest, "heal") == "")
combat.ally_turn(f, priest, random.Random(6))
f.round = 7; combat.give_order(f, priest, "heal")
h1 = f.player.hp
combat.ally_turn(f, priest, random.Random(7))
check("...", f.player.hp > h1 > 5, (h1, f.player.hp))

# ---- the fighter
f, (fighter,), wolves = fight(["fighter"])
f.round = 2
f.player.hp = f.player.max_hp * 0.4
combat.ally_turn(f, fighter, random.Random(1))
check("a fighter shields a hurt player: blows meant for them land on the fighter", fighter.covering == f.player.id)
f.player.hp = f.player.max_hp
fighter.covering = ""
hits = 0
for i in range(30):
    fighter.cooldowns.clear(); fighter.counters.clear()
    w = wolves[0]; w.hp = w.max_hp
    before = w.hp
    combat.ally_turn(f, fighter, random.Random(100 + i))
    hits += any("Crushing Blow" in l for l in f.log[-2:])
check("a fighter with the player well puts their weight into a Crushing Blow", hits >= 10, hits)

# ---- the archer
f, (archer,), wolves = fight(["archer"])
f.round = 2
for i in range(10):
    archer.cooldowns.clear()
    combat.ally_turn(f, archer, random.Random(i))
    if any("slowed" in w.statuses for w in wolves):
        break
check("an archer pins a foe with a shot: it is slowed", any("slowed" in w.statuses for w in wolves), [w.statuses for w in wolves])

# ---- the rogue
f, (rogue,), wolves = fight(["rogue"])
f.round = 2
from engine import battlefield as bf
w = wolves[0]
combat.ally_turn(f, rogue, random.Random(1))
first = list(f.log)
check("a rogue's Backstab waits for a foe busy with someone else", not any("Backstab" in l for l in first) or f.player.id in w.engaged_with, first)
rogue.cooldowns.clear()
bf.engage(f, f.player, w)
f.focus = w.id
labels = []
for i in range(20):
    rogue.cooldowns.clear()
    w.hp = w.max_hp
    combat.ally_turn(f, rogue, random.Random(200 + i))
    labels += f.log[-2:]
check("...and strikes one that is", any("Backstab" in l for l in labels), labels[-4:])

# ---- the mage
f, (mage,), wolves = fight(["mage"], foes=3)
f.round = 2
hp0 = [w.hp for w in wolves]
combat.ally_turn(f, mage, random.Random(1))
check("a mage looses a burst at every foe bunched together", sum(1 for l in f.log if "Arcane Burst on" in l) == 3, f.log[-4:])

# ---- a priest's care outside a fight
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
shutil.rmtree("saves/hire_kit_test", ignore_errors=True)
store = CampaignStore.open_or_create("hire_kit_test")
store.meta.seed = 4; store.meta.minutes = 720; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(3))
char.level = 6
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
priest_m = {"id": "h1", "name": "Aldo Venn", "role": "priest", "level": 6, "permanent": True, "rank": "E", "kind": "adventurer"}
hurt_m = {"id": "h2", "name": "Bryn Tor", "role": "fighter", "level": 6, "permanent": True, "rank": "E", "kind": "adventurer",
          "hp_frac": 0.4, "hp_at": ws.minutes}
ws.player.party = [priest_m, hurt_m]
ws.player.party_mode = "with"
c = ws.player.character
top = pools.maximum(c, "health")
c.health = top * 0.3
NOTES.clear()
check("after a fight, a priest on their feet sees to the wounds", ws.tend_after_fight() and pools.current(c, "health") > top * 0.3
      and any("Aldo sees to the wounds" in n for n in NOTES), NOTES)
check("...and to the hurt hires'", party.health_now(hurt_m, ws.minutes) > 0.6, party.health_now(hurt_m, ws.minutes))
c.health = top * 0.3
NOTES.clear()
before_min = ws.minutes
check("asked to see to the player's wounds, a priest does", ws.tend_when_asked(priest_m, "Aldo, can you see to my wounds?")
      and pools.current(c, "health") > top * 0.3 and ws.minutes > before_min, NOTES)
h = pools.current(c, "health")
check("...not again straight away", ws.tend_when_asked(priest_m, "Aldo, heal me again.") and pools.current(c, "health") == h
      and any("rest and time" in n for n in NOTES), NOTES)
check("a line that asks nothing of the kind is only talk", not ws.tend_when_asked(priest_m, "Aldo, where did you learn your prayers?"))
check("a fighter asked to heal has no healing to give: it is only talk", not ws.tend_when_asked(hurt_m, "Bryn, heal me."))
store.close()
shutil.rmtree("saves/hire_kit_test", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
