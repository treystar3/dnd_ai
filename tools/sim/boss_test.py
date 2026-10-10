"""Set-piece bosses: legendary actions, legendary resistance, bloodied phase, last stand, guards, voice, human war captains."""
import sys, random
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from engine import combat, bosses, events

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

world = load_world()
LV = 100

def fight(cid, tier, seed, lines=None, hp=4.0, allies=0, lvl=LV, name="the thing"):
    rng = random.Random(seed)
    ch, _ = simlib.make_character("warrior", rng)
    ch.level = lvl
    p = combat.fighter_from_character(ch); p.side = "player"
    c = world.bestiary[cid]
    e = combat.fighter_from_creature(c, lvl + 3, "boss", "e1", name, "near")
    e.max_hp = e.hp = round(e.max_hp * hp / combat.RULES["creatures"]["rank"]["boss"]["health"])
    e.boss = bosses.make(bosses.kit_for(c.category), tier, name, lines)
    return combat.Combat(fighters=[p, e]), rng

# legendary actions are taken between turns, capped per round
cmb, rng = fight("knight", "cataclysm", 1)
combat.opening(cmb, rng)
combat.finish_round(cmb, rng)
acts = [l for l in cmb.log if l.startswith("the thing:") or l.startswith("The thing:")]
check("a cataclysm boss uses legendary actions", len(acts) >= 1, str(acts))
check("at most 3 + signature per round", len(acts) <= 4, str(len(acts)))

# resistance
cmb, rng = fight("knight", "cataclysm", 2)
e = cmb.enemies()[0]
res = [combat.add_status(cmb, e, "stunned", 2) for _ in range(5)]
check("legendary resistance blocks 3 stuns then fails", res == [False, False, False, True, True], str(res))
cmb, rng = fight("knight", "campaign", 2)
e = cmb.enemies()[0]
check("campaign boss resists twice", [combat.add_status(cmb, e, "frightened", 2) for _ in range(3)] == [False, False, True])
cmb, rng = fight("knight", "captain", 2)
e = cmb.enemies()[0]
check("captain resists once", [combat.add_status(cmb, e, "stunned", 2) for _ in range(2)] == [False, True])

# bloodied + last stand + fall lines
L = {"intro": "I am {name}. Kneel.", "bloodied": "Bleeding? Me?", "last_stand": "Not yet!", "fall": "Remember me."}
cmb, rng = fight("archmage", "leader", 3, L, name="Warden Vael")
e = cmb.enemies()[0]
combat.opening(cmb, rng)
check("intro spoken with name", any("I am Warden Vael" in s for s in cmb.story), str(cmb.story[-2:]))
combat.take_damage(cmb, e, e.max_hp * 0.55, cmb.player, rng)
check("bloodied phase", e.boss["phase"] == 1 and any("Bleeding" in s for s in cmb.story))
combat.take_damage(cmb, e, e.max_hp * 5, cmb.player, rng)
check("last stand: a killing blow leaves it standing", e.alive and e.boss["stand_used"] and any("Not yet" in s for s in cmb.story))
combat.take_damage(cmb, e, e.max_hp * 5, cmb.player, rng)
check("second killing blow kills, last words said", not e.alive and any("Remember me" in s for s in cmb.story))
cmb, rng = fight("knight", "captain", 3)
e = cmb.enemies()[0]
combat.take_damage(cmb, e, e.max_hp * 5, cmb.player, rng)
check("captain has no last stand", not e.alive)

# guards capped
cmb, rng = fight("mage", "cataclysm", 4)
e = cmb.enemies()[0]
for _ in range(6): bosses._guards(cmb, e, 2)
check("guards capped", len([f for f in cmb.fighters if "guard" in f.id]) == bosses.B["max_guards"])

# every kit runs a whole fight without error, and kits differ
seen = set()
for cid in ["knight", "mage", "ashen_champion", "bandit_captain"] + [c.id for c in world.bestiary.values() if c.roster and not c.unique][::25]:
    cmb, rng = fight(cid, "cataclysm", 5)
    seen.add(cmb.enemies()[0].boss["kit"])
    r = combat.simulate(cmb, rng)
    assert r.over, cid
check("kits exercised", len(seen) >= 3, str(seen))

# human war captains and leaders: pools are people
ev = events.E if hasattr(events, "E") else None
war = events.C["kinds"]["war"] if "kinds" in events.C else None
pool = (war["captain_pool"] + war["leader_pool"]) if war else []
check("war pools are person creatures", pool and all(world.bestiary[i].category in ("person template", "hostile people") and world.bestiary[i].group[0] < 2 for i in pool), str(pool))
print("ALL PASS" if not bad else f"FAILED {bad}")
