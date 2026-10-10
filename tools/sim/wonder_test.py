"""Wonders: legendary effects that give world-side powers, the Phoenix save, and per-run relic shelves."""
import sys, random, types
sys.path.insert(0, ".")
from engine import items, loot, pools, property as P
from world.loader import load_world
import simlib

simlib.install(simlib.Stub("warrior", 1))
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
import shutil
shutil.rmtree("saves/wonder_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("wonder_test")
store.meta.seed = 11; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
store.save_player(PlayerState(character=char, location=world.start_location))
ws = WorldScene(store, world, load_traits(), store.load_player())
c = ws.player.character
fails = []
def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

# every wonder reaches its world hook through has()/owns()
for eid, le in items.LEGENDARY.items():
    if not le.world: continue
    base = items.CATALOG[{"jewelry": "amulet", "weapon": "longsword", "armor": "plate"}[le.applies]]
    it = items.make(base.id, "legendary", 40, rng=random.Random(1)); it.legendary_effect = eid
    c.equipment.clear(); c.equipment[base.slot] = it
    had = pools.mechanic(c, le.world) is not None and any(p.mechanic == le.world for p in c.passives)
    check(f"{eid} grants {le.world}", ws.owns(le.world))
    c.equipment.clear()
    check(f"{eid} gone when unequipped", had or not ws.owns(le.world))

# the two shelves differ between campaigns, and every dealer town stocks exactly one relic
a, b = P.stock(world, 1), P.stock(world, 2)
check("shelves differ per seed", a != b)
towns = P.dealer_towns(world)
check("every dealer town has a relic", set(a.values()) == set(towns))
check("far-lands relics stay home", all(P.RELICS[r].get("home") is None or t in P.RELICS[r]["home"] for r, t in a.items()))
check("same seed, same shelves", P.stock(world, 1) == a)
town = next(iter(a.values()))
here = [k for k, v in a.items() if v == town]
check("dealer lists its relics", len(P.relics_in(world, 1, town, [])) == len(here) and len(P.relics_in(world, 1, town, [here[0]])) == len(here) - 1)

# phoenix: saves the wearer once, then waits out its cooldown
from scenes.combat_scene import CombatScene
cs = CombatScene.__new__(CombatScene); cs.ws = ws
ph = items.make("amulet", "legendary", 40, rng=random.Random(2)); ph.legendary_effect = "phoenix"
c.equipment["neck"] = ph
c.health = 0.0
check("phoenix saves", cs.phoenix())
check("phoenix restores half health", abs(c.health - pools.maximum(c, "health") * 0.5) < 1)
check("phoenix waits", not cs.phoenix())
ws.advance_quiet(8 * 1440)
check("phoenix returns after its cooldown", cs.phoenix())
c.equipment.clear()
check("no phoenix, no save", not cs.phoenix())

# slot discipline: weapons only roll combat strikes, armor only defences, jewelry only wonders
for slot_base, kind in (("longsword", "weapon"), ("plate", "armor"), ("amulet", "jewelry"), ("ring", "jewelry")):
    opts = items.legendary_options(items.CATALOG[slot_base])
    check(f"{slot_base} options are all {kind}", opts and all(o.applies == kind for o in opts))
check("every jewelry effect is a wonder", all(o.world or o.id in ("phoenix", "lightfoot", "shadowmantle") for o in items.legendary_options(items.CATALOG["ring"])))
check("no world wonders on weapons or armor", not any(o.world for o in items.legendary_options(items.CATALOG["plate"]) + items.legendary_options(items.CATALOG["longsword"])))
check("legendary drops include rings and amulets", sum(items.CATALOG[loot.make_drop(40, "legendary", random.Random(i)).base].slot in ("neck", "ring") for i in range(400)) > 60)

# armor reduction effects bite
from engine import combat, party
def hit(effect, value, dtype, amount=100):
    d = party.fighter({"id": "t", "name": "T", "role": "fighter", "level": 40})
    d.side = "enemy"; d.legendary = {effect: value}; d.hp = d.max_hp = 1000
    cmb = combat.Combat(fighters=[d])
    return combat.take_damage(cmb, d, amount, None, random.Random(1), dtype)
check("stoneskin cuts 12%", hit("stoneskin", 12, "physical") == 88)
check("plating cuts physical 25%", hit("plating", 25, "physical") == 75)
check("plating ignores magic", hit("plating", 25, "magical") == 100)
check("spellward cuts magic 25%", hit("spellward", 25, "magical") == 75)
check("spellward ignores physical", hit("spellward", 25, "physical") == 100)
check("unbroken caps one blow", hit("unbroken", 25, "physical", amount=900) == 250)

# the casters' effects
def duel(**legendary):
    p = party.fighter({"id": "p", "name": "Mage", "role": "mage", "level": 40}); p.side = "player"
    e = party.fighter({"id": "e", "name": "Foe", "role": "fighter", "level": 40}); e.side = "enemy"; e.hp = e.max_hp = 100000
    p.legendary = dict(legendary); p.max_mana = 3000; p.mana = 3000; p.hp = p.max_hp = 1000
    p.moves = [combat.Move(id="bolt", name="Bolt", effect="damage", tier="light", reach="ranged", resource="mana", cooldown=0, attribute="intelligence"),
               combat.Move(id="nova", name="Nova", effect="damage", tier="heavy", reach="ranged", resource="mana", cooldown=3, attribute="intelligence")]
    cmb = combat.Combat(fighters=[p, e]); return cmb, p, e, p.moves[0]
rng = random.Random(3)
cmb, p, e, bolt = duel(archmage=50)
p.mana = 0
check("archmage: first spell needs no mana", combat.can_use(p, bolt, cmb) is None)
combat.act_ability(cmb, p, bolt, e, rng)
check("archmage: only the first", combat.can_use(p, bolt, cmb) is not None)
cmb, p, e, bolt = duel()
p.mana = 0
check("no archmage: cannot cast on empty", combat.can_use(p, bolt, cmb) is not None)
cmb, p, e, bolt = duel(overchannel=2)
p.mana = 0
check("overchannel: can cast on empty", combat.can_use(p, bolt, cmb) is None)
combat.act_ability(cmb, p, bolt, e, rng)
check("overchannel: paid in health", p.hp < 1000 and p.mana == 0)
for _ in range(60):
    if combat.can_use(p, bolt, cmb) is None: combat.act_ability(cmb, p, bolt, e, rng)
check("overchannel never kills", p.hp >= p.max_hp * 0.1 - 1)
cmb, p, e, bolt = duel(arcane_recall=1)
p.cooldowns["other"] = 3
combat.act_ability(cmb, p, bolt, e, rng)
check("arcane recall shortens other cooldowns", p.cooldowns["other"] == 2)
cmb, p, e, bolt = duel(starfall=60)
for i in range(4):
    cmb.log.clear(); p.cooldowns.clear(); combat.act_ability(cmb, p, bolt, e, rng)
check("starfall on the fourth spell", any("starfall" in l for l in cmb.log))
cmb, p, e, bolt = duel(starfall=60)
for i in range(3):
    cmb.log.clear(); p.cooldowns.clear(); combat.act_ability(cmb, p, bolt, e, rng)
check("no starfall before the fourth", not any("starfall" in l for l in cmb.log))
cmb, p, e, bolt = duel(ward_conversion=40)
p.mana = 10
combat.take_damage(cmb, p, 100, e, rng, "magical")
check("ward conversion restores mana from magic", p.mana > 10)
p.mana = 10
combat.take_damage(cmb, p, 100, e, rng, "physical")
check("ward conversion ignores physical", p.mana == 10)
check("caster effects only on focus weapons", all("archmage" not in [o.id for o in items.legendary_options(items.CATALOG[b])] for b in ("longsword", "plate", "robe")))
print("FAILED" if fails else "ALL OK", fails)
sys.exit(1 if fails else 0)
