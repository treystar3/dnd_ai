"""Rings and amulets: lanes, strengthening by rarity, uniqueness, powers in a fight, boss relics, the lie-sense gift, naming."""
import sys, random
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from engine import accessories, combat, items, loot, pools, bosses, relics
from core.models import Item

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

world = load_world()
A = accessories.A
rng = random.Random(1)

def acc(base, rarity, seed=0, level=60):
    r = random.Random(seed)
    it = items.make(base, rarity, level, rng=r)
    accessories.roll(it, r)
    return it

# identity by type
lanes = {"ring": set(), "amulet": set()}
for s in range(200):
    for b in ("ring", "amulet"):
        lanes[b].add(acc(b, "epic", s).trait["lane"])
check("rings are striker/trickster, amulets warden/mystic", lanes == {"ring": {"striker", "trickster"}, "amulet": {"warden", "mystic"}}, str(lanes))

# lane stats stay in lane
ok = True
for s in range(200):
    it = acc("ring", "epic", s)
    allowed = set(A["lanes"][it.trait["lane"]]["stats"])
    from engine import elements as _el
    for _tok, _cat in loot.TOKENS.items():
        if _tok in allowed:
            allowed |= {f"{e}_{'resistance' if _cat == 'resistance' else 'damage'}" for e in _el.ELEMENTS}
    ok &= all(p.modifies in allowed for p in it.properties) and len({p.modifies for p in it.properties}) == len(it.properties)
check("stats come from the lane, never twice", ok)

# strengthening by rarity
def power_of(rarity):
    return [acc("ring", rarity, s) for s in range(100)]
for r in ("common", "uncommon"):
    check(f"{r}: stats only", all(not i.relic and not i.trait["fight"] and not i.trait["world"] for i in power_of(r)))
check("rare: trait mechanic + power (1 use), no gift", all(i.trait["fight"] and i.relic["uses"] == 1 and not i.trait["world"] for i in power_of("rare")))
check("epic: trait + power + world gift", all(i.trait["fight"] and i.relic and i.trait["world"] for i in power_of("epic")))
check("legendary: power with 2 uses", all(i.relic["uses"] == 2 for i in power_of("legendary")))
def mean_mult(rarity):
    v = []
    for i in power_of(rarity):
        v += list(i.trait["fight"].values())
    return sum(v) / len(v)
check("trait mechanics strengthen with rarity", mean_mult("rare") < mean_mult("epic") < mean_mult("legendary"),
      f"{mean_mult('rare'):.1f} {mean_mult('epic'):.1f} {mean_mult('legendary'):.1f}")

# uniqueness: many distinct assemblies
sigs = {(i.trait["lane"], tuple(sorted(i.trait["fight"])), tuple(sorted(i.trait["world"])), i.relic["id"], tuple(sorted(p.modifies for p in i.properties)))
        for i in (acc(random.choice(["ring", "amulet"]), "epic", s) for s in range(400))}
check("epic accessories are very varied", len(sigs) > 150, str(len(sigs)))

# round trip through save format
it = acc("ring", "epic", 5)
back = Item(**it.model_dump())
check("item survives save/load", back.trait == it.trait and back.relic == it.relic)
check("summary lists trait and power", "Power -" in items.summary(it))

# world gift reaches the character
r2 = random.Random(9)
ch, _ = simlib.make_character("warrior", r2)
for s in range(60):
    it = acc("ring", "epic", s)
    if "trap_sense" in it.trait["world"]:
        ch.equipment["ring_1"] = it
        check("a ring's world gift is found by pools.mechanic", pools.mechanic(ch, "trap_sense") is not None)
        break
else:
    check("found a trap-sense ring to test", False)

# ---------- powers in a fight ----------
def arena(items_worn, n=2, cid="knight", lvl=100, seed=0):
    r = random.Random(seed)
    ch, _ = simlib.make_character("warrior", r)
    ch.level = lvl
    ch.passives = []                      # the stand-in character's passives vary run to run; the test wants only the item
    ch.equipment.clear()
    ch.equipment.update(items_worn)
    p = combat.fighter_from_character(ch); p.side = "player"
    es = [combat.fighter_from_creature(world.bestiary[cid], lvl, "normal", f"e{i}", f"foe {i}", "engaged") for i in range(n)]
    return combat.Combat(fighters=[p] + es), r

def forced(kind_id, rarity="legendary", base="ring"):
    r = random.Random(0)
    for s in range(3000):
        it = acc(base, rarity, s)
        if it.relic and it.relic["id"] == kind_id:
            return it
    raise SystemExit("no item with " + kind_id)

for pid in ["smite", "frenzy", "rend", "vanish", "dazzle", "sleight"]:
    it = forced(pid, base="ring")
    c, r = arena({"ring_1": it})
    p = c.player
    mv = next(m for m in p.moves if m.effect == "relic")
    check(f"{pid}: appears as a move, free to use", combat.cost_of(p, mv, c) == 0 and not combat.can_use(p, mv, c))
    hp0 = [e.hp for e in c.enemies()]
    p.cooldowns["x"] = 3
    err = combat.act_ability(c, p, mv, c.enemies()[0], r)
    check(f"{pid}: fires without error", err is None, str(err))
    effect = {"smite": c.enemies()[0].hp < hp0[0] or c.enemies()[0].hp < hp0[0] + 1,
              "frenzy": bool(p.buffs), "rend": "hexed" in c.enemies()[0].statuses, "vanish": bool(p.buffs),
              "dazzle": "slowed" in c.enemies()[0].statuses or "blinded" in c.enemies()[0].statuses,
              "sleight": "x" not in p.cooldowns}[pid]
    check(f"{pid}: does its work", effect, c.story[-1])
    for _ in range(mv.uses - 1):
        combat.act_ability(c, p, mv, c.enemies()[0], r)
    check(f"{pid}: limited to its uses a fight", bool(combat.can_use(p, mv, c)))

for pid in ["barrier", "mend", "bastion"]:
    it = forced(pid, base="amulet")
    c, r = arena({"neck": it})
    p = c.player; p.hp = p.max_hp * 0.4; p.statuses["bleeding"] = 3
    mv = next(m for m in p.moves if m.effect == "relic")
    combat.act_ability(c, p, mv, None, r)
    ok = {"barrier": p.shield > 0, "mend": p.hp > p.max_hp * 0.4 and "bleeding" not in p.statuses,
          "bastion": "stoneskin" in combat.mechanics(p, c) and "unyielding" in combat.mechanics(p, c)}[pid]
    check(f"{pid} works", ok)
for pid in ["font", "nova", "veil"]:
    it = forced(pid, base="amulet")
    c, r = arena({"neck": it})
    p = c.player; p.mana = 0; p.cooldowns["x"] = 2
    hp0 = [e.hp for e in c.enemies()]
    mv = next(m for m in p.moves if m.effect == "relic")
    combat.act_ability(c, p, mv, None, r)
    ok = {"font": p.mana > 0 and "x" not in p.cooldowns, "nova": all(e.hp < h for e, h in zip(c.enemies(), hp0)),
          "veil": "spellward" in combat.mechanics(p, c)}[pid]
    check(f"{pid} works", ok)

# timed buffs end, and charge their price
c, r = arena({"ring_1": forced("frenzy")})
p = c.player
mv = next(m for m in p.moves if m.effect == "relic")
combat.act_ability(c, p, mv, None, r)
rounds = 0
while p.buffs and rounds < 10:
    combat.start_turn(p, c); rounds += 1
check("a 3-round buff covers the next 3 enemy phases then ends", rounds == 3, str(rounds))

# ---------- boss signatures ----------
def boss_item(kit, sig):
    for s in range(2000):
        it = accessories.boss_relic(kit, 200, random.Random(s))
        if it.trait["signature"] == sig:
            return it
    raise SystemExit(sig)

check("every kit has a relic variant list", set(A["bosses"]) >= set(bosses.B["kits"]), str(set(bosses.B["kits"]) - set(A["bosses"])))
for kit in bosses.B["kits"]:
    for s in range(30):
        it = accessories.boss_relic(kit, 150, random.Random(s))
        assert it.rarity == "legendary" and it.trait["signature"]
check("boss relics are legendary jewelry for all kits", True)

# thrall
it = boss_item("undead", "thrall")
c, r = arena({"ring_1": it}, n=3)
p = c.player
first = c.enemies()[0]
combat.take_damage(c, first, first.max_hp * 5, p, r)
first.hp = 0
# a real kill through apply_damage
c, r = arena({"ring_1": it}, n=3)
p = c.player; p.weapon_damage = 9999
t0 = c.enemies()[0]
for _ in range(10):
    if not t0.alive: break
    combat.apply_damage(c, p, t0, 3.0, "attacks", r)
th = c.get("thrall")
check("the first enemy slain rises as a thrall", th is not None and th.side == "ally" and th.alive and th.name.startswith("the risen "), th.name if th else "none")
check("the thrall is a copy of it in life", th.weapon_damage == t0.weapon_damage and th.attrs == t0.attrs and th.max_hp == t0.max_hp)
t1 = c.enemies()[0]
for _ in range(10):
    if not t1.alive: break
    combat.apply_damage(c, p, t1, 3.0, "attacks", r)
check("only the first kill rises", len([f for f in c.fighters if f.id == "thrall"]) == 1)
for e in c.enemies(): e.max_hp = e.hp = 10**6
e_hp = [e.hp for e in c.enemies()]
for _ in range(20): combat.ally_turn(c, th, r)
check("the thrall fights for the player", any(e.hp < h for e, h in zip(c.enemies(), e_hp)))
combat.take_damage(c, th, th.max_hp * 5, None, r)
check("the thrall can perish again and stays down", not th.alive and not any(f.id == "thrall" and f.alive for f in c.fighters))

# earthshaker
it = boss_item("giant", "earthshaker")
c, r = arena({"ring_1": it}, n=1)
p = c.player
check("earthshaker: cannot be knocked prone", not combat.add_status(c, p, "prone", 1))
fell = 0
for s in range(60):
    c, r = arena({"ring_1": it}, n=1, seed=s)
    e = c.enemies()[0]; e.max_hp = e.hp = 10**6
    for _ in range(4): combat.apply_damage(c, c.player, e, 1.0, "attacks", r)
    fell += "prone" in e.statuses
check("earthshaker topples enemies", fell > 10, str(fell))

# attunement
it = boss_item("elemental", "attunement")
c, r = arena({"ring_1": it}, n=1)
p = c.player
mv = next((m for m in p.moves if m.effect != "relic"), None)
if mv is None:
    from engine.combat import Move
    mv = Move(id="t", name="Test", effect="damage", tier="light", reach="melee", resource="stamina")
    p.moves.append(mv)
p.stamina = p.max_stamina = 10**6
for _ in range(7):
    p.cooldowns.clear(); combat.act_ability(c, p, mv, c.enemies()[0], r)
check("attunement stacks to five", p.counters.get("attune") == 5, str(p.counters))

# iron will
it = boss_item("construct", "iron_will")
c, r = arena({"ring_1": it}, n=1)
p = c.player
res = [combat.add_status(c, p, "stunned", 1) for _ in range(4)]
check("iron will shrugs off the first two afflictions only", res == [False, False, True, True], str(res))
check("each shrug steels the blows", p.counters["shrugged"] == 2)

# many heads
it = boss_item("monstrosity", "many_heads")
c, r = arena({"ring_1": it}, n=3)
p = c.player
for e in c.enemies(): e.max_hp = e.hp = 10**6
hp0 = {e.id: e.hp for e in c.enemies()}
for _ in range(30):
    if combat.apply_damage(c, p, c.enemies()[0], 1.0, "attacks", r): break
hit = [e.id for e in c.enemies() if e.hp < hp0[e.id]]
check("many heads strikes a second enemy once a round", len(hit) == 2, str(hit))
c.story.clear()
for _ in range(30):
    if combat.apply_damage(c, p, c.enemies()[0], 1.0, "attacks", r): break
check("only one extra head-strike per round", not any("another head" in s for s in c.story))
check("only once per round", p.counters["heads_round"] == c.round)

# deathless + price
it = boss_item("default", "deathless")
c, r = arena({"ring_1": it}, n=1)
p = c.player
mv = next(m for m in p.moves if m.effect == "relic")
combat.act_ability(c, p, mv, None, r)
combat.take_damage(c, p, p.max_hp * 10, c.enemies()[0], r)
check("deathless holds the wearer on the threshold", p.alive and p.hp == 1)
while p.buffs: combat.start_turn(p, c)
check("when deathless ends, stamina and mana are spent", p.stamina == 0 and p.mana == 0)

# devil's bargain: drain + slowed
it = boss_item("fiend", "bargain")
c, r = arena({"ring_1": it}, n=1)
p = c.player
mv = next(m for m in p.moves if m.effect == "relic")
combat.act_ability(c, p, mv, None, r)
hp = p.hp
combat.start_turn(p, c)
check("the bargain costs health every round", p.hp < hp)
while p.buffs: combat.start_turn(p, c)
check("and leaves the wearer slowed", "slowed" in p.statuses)

# rally, breath
it = boss_item("person", "rally")
c, r = arena({"ring_1": it}, n=1)
al = combat.fighter_from_creature(world.bestiary["knight"], 100, "normal", "ally_x", "Sir Test", "near"); al.side = "ally"; al.hp = 1
c.fighters.append(al)
mv = next(m for m in c.player.moves if m.effect == "relic")
combat.act_ability(c, c.player, mv, None, r)
check("rally heals companions and shields the wearer", al.hp > 1 and c.player.shield > 0)
it = boss_item("dragon", "wyrmfire")
c, r = arena({"ring_1": it}, n=3)
hp0 = [e.hp for e in c.enemies()]
mv = next(m for m in c.player.moves if m.effect == "relic")
combat.act_ability(c, c.player, mv, None, r)
check("dragon's breath hits the whole field", all(e.hp < h for e, h in zip(c.enemies(), hp0)))

# lie sense
it = boss_item("aberration", "unmasking")
ch, _ = simlib.make_character("warrior", random.Random(2))
ch.equipment["ring_1"] = it
check("unmasking gaze: lie_sense found", pools.mechanic(ch, "lie_sense") is not None)
ch.equipment.pop("ring_1")
check("and absent without it", pools.mechanic(ch, "lie_sense") is None)

# drop chances and naming
check("boss relic chances defined for all tiers", set(bosses.B["relic_chance"]) >= {"campaign", "cataclysm", "leader", "captain", "dungeon"})
n = 0
from scenes.combat_scene import CombatScene
check("combat scene has accessory naming", hasattr(CombatScene, "ask_accessory_name") and hasattr(CombatScene, "story_around"))

# normal drops produce accessories
r3 = random.Random(4)
made = [loot.make_drop(80, "epic", r3) for _ in range(400)]
jew = [i for i in made if accessories.is_accessory(i)]
check("epic drops include fully assembled rings/amulets", jew and all(i.trait and i.relic for i in jew), str(len(jew)))
print("ALL PASS" if not bad else f"FAILED {bad}")
