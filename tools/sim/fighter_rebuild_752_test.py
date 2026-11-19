"""(f752) A fighter is rebuilt from the character by one step that keeps what the fight took (engine/combat.py rebuild; the audit's
pane-commands-4). Spending an attribute point in a fight ran services/fight.py refresh, which copied four fields from a fighter built
fresh: an ooze's touch that had worn the armour from 5.0 to 3.893 was put back to 5.0 with the cap's counter left at 24, so only 6 more
could ever be taken; and a gear change followed by a point left the fighter a mix of old and new (the new armour, the old weapon).
Held here:
- the case that found it: three touches of an ooze, then `#attradd constitution` through play(): the armour is the number the fight
  reached, to the last bit (compared with ==), and a fourth touch takes the last 6 of the cap from there;
- second cases of the kind: a quickened pace (Frostborne) through a rebuild, from a pace already fast and from normal, with the
  character slower by then; a point of wisdom raises the ward by its share while the worn armour stays worn; a gear change then a
  point leaves the fighter the character's whole, the weapon too;
- the kind: every field of a fighter is declared the character's or the fight's, so a new field fails until someone says which; a
  fighter rebuilt where nothing wore it equals a fresh one over every field the character gives; over the fight fixtures that lay
  nothing on the fighter by hand (the family, status, hire and rank cases; the mechanics and player_hp cases write legendary,
  mech_names and max_hp on the fighter, which a rebuild rightly undoes), a rebuild after every round with the character unchanged
  leaves the fight's dump the same to the last key;
- control: a fight saved before the steps were kept (the cap's counter and no steps) keeps its armour as the fight left it.
Run: python tools/sim/fighter_rebuild_752_test.py"""
import json
import random
import sys
from types import SimpleNamespace as NS
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/sim")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
stub.bot = NS(combat_choice=lambda: {"kind": "attack", "target": "e1"})
simlib.quiet_console()
from ui import console as _console
for _n in ("out", "status_block", "combat_state", "combat_panel", "show_header", "debug", "show_player_block", "show_inventory"):
    if hasattr(_console, _n):
        _console.put(_n, lambda *a, **k: None)
from core.models import Passive, PowerTier
from engine import behaviors, combat, combat_perks, items, pools
from scenes import combat_scene as cs
from storage import saves

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


GIVEN = set(getattr(combat, "GIVEN", ()))
OWNS = set(getattr(combat, "FIGHT_OWNS", ()))


def flat(f) -> dict:
    """A fighter's dump, flat by field name (the dump is nested by part)."""
    return {k: v for part in f.model_dump(mode="json").values() if isinstance(part, dict) for k, v in part.items()}


NAME = "fighter_rebuild_752"
g = simlib.campaign(NAME, seed=4, location="south_fields")
ws, store = g.scene, g.store
ws.enter("south_fields")
c = ws.player.character
c.level = 6
c.unspent_points = 12
c.equipment["body"] = items.make("chain_shirt", "common", 6)
pools.fill_missing(c)


def me():
    """The character as the scene holds it now (an input may load it again from the save)."""
    return ws.player.character

store.save_player(ws.player)
WOLF = ws.world.bestiary["wolf"]


def begin():
    """A fight with one wolf that will not fall, the row saved: the scene's fight."""
    if ws.combat is not None:
        store.save_combat(None)
        ws.combat = None
    foe = combat.fighter_from_creature(WOLF, 6, "normal", "e1", name="wolf 1")
    foe.max_hp = foe.hp = 5000
    ws.combat = cs.CombatScene.begin(ws, WOLF, [foe], "It is on you:")
    store.save_player(ws.player)
    return ws.combat.fight


def ooze(f):
    """The wolf made an ooze whose touch wears armour 8 at a time (data/world/families.yaml's ooze)."""
    e = f.enemies()[0]
    e.family, e.behaviors = "ooze", {"fearless": 1, "corrode": 8}
    return e


def touch(f, n=1):
    e = ooze(f)
    for _ in range(n):
        behaviors.after_hit(f, e, f.player, True, random.Random(1))
    store.save_combat(ws.combat.to_json())


# ---- the case that found it: an ooze's wear through an attribute click
f = begin()
ws.play("I attack the wolf.")
f = ws.combat.fight
p = f.player
whole = p.armor
touch(f, 3)
worn = p.armor
check("(three touches of an ooze wear the armour from 5.0 to 3.8934400000000013, the cap's counter at 24)",
      whole == 5.0 and worn == 3.8934400000000013 and p.counters.get("corroded") == 24, (whole, worn, p.counters.get("corroded")))
before = flat(p)
con0, top0 = me().attributes.constitution, p.max_hp
ws.play("#attradd constitution")
f = ws.combat.fight
p = f.player
check("(the point is spent: constitution and the fighter's most health rise)", me().attributes.constitution == con0 + 1 and p.max_hp > top0,
      (me().attributes.constitution, p.max_hp, top0))
check("an attribute click leaves the worn armour the number the fight reached, to the last bit", p.armor == worn, (p.armor, worn))
after = flat(p)
kept = sorted(k for k in OWNS - {"hp", "stamina", "mana"} if before.get(k) != after.get(k))
check("...and every field the fight owns as the fight left it", bool(OWNS) and not kept, kept or "no field is declared the fight's")
touch(f, 1)
check("a fourth touch after the click takes the last 6 of the cap from there, the counter at 30",
      p.armor == worn * (1 - 6 / 100) and p.counters.get("corroded") == 30, (p.armor, worn * (1 - 6 / 100), p.counters.get("corroded")))
last = p.armor
touch(f, 2)
check("...and no touch past the cap wears it more", p.armor == last and p.counters.get("corroded") == 30, (p.armor, last))
check("the steps the fight took are kept in order, the cap bounding them (four at the ooze's 8 under 30)",
      p.counters.get("armor_steps") == [8, 8, 8, 6], p.counters.get("armor_steps"))
ws.play("#attradd constitution")
p = ws.combat.fight.player
check("a second click keeps the armour worn to the cap", p.armor == last, (p.armor, last))
raw = json.loads(store.load_combat())
row_p = next(x for x in cs.FightService.resume(json.dumps(raw))[0].fighters if x.id == "player")
check("the row holds the steps, so a reopened fight keeps the wear", row_p.counters.get("armor_steps") == [8, 8, 8, 6],
      row_p.counters.get("armor_steps"))

# ---- second case: a point of wisdom raises the ward by its share while the worn armour stays worn
f = begin()
p = f.player
touch(f, 2)
worn, ward0, wis0 = p.armor, p.ward, p.attrs["wisdom"]
ws.play("#attradd wisdom")
p = ws.combat.fight.player
share = combat.RULES["mitigation"]["wisdom_ward"]
check("a point of wisdom raises the fighter's ward by its share", p.attrs["wisdom"] == wis0 + 1 and abs(p.ward - (ward0 + share)) < 1e-9,
      (p.attrs["wisdom"], wis0, p.ward, ward0, share))
check("...while the worn armour stays worn", p.armor == worn, (p.armor, worn))

# ---- second case: a quickened pace through a rebuild
me().passives.append(Passive(id="fb", name="Frostborne", description="d", tier=PowerTier.LIGHT, mechanic="frostborne", value=1))
me().equipment["body"] = items.make("padded", "common", 6)
store.save_player(ws.player)
light = combat.RULES["pace"]["armor"]["light"]


def quicken(f):
    p = f.player
    combat.add_status(f, p, "slowed", 2, f.enemies()[0])
    return p


def ends(f, p):
    f.round = p.counters.get("quick_until", f.round) + 1
    combat_perks.on_turn_start(f, p)


combat.RULES["pace"]["armor"]["light"] = "fast"         # a character whose own armour lets them move fast
try:
    f = begin()
    p = quicken(f)
    check("(a fighter fast of their own is quickened by Frostborne, and no pace_was is kept)",
          p.pace == "fast" and "quick_until" in p.counters and "pace_was" not in p.counters, (p.pace, p.counters))
    me().equipment["body"] = items.make("chainmail", "common", 6)      # heavy and not fitted: the character is slow now
    ws.combat.service.refresh(f)
    check("quickened when already fast, the character slower by the rebuild: still fast while the quickening stands", p.pace == "fast",
          p.pace)
    ends(f, p)
    check("...and the character's slower pace once it ends", p.pace == "slow", p.pace)
finally:
    combat.RULES["pace"]["armor"]["light"] = light
me().equipment["body"] = items.make("padded", "common", 6)
f = begin()
p = quicken(f)
check("(quickened from normal: fast, the normal pace kept)", p.pace == "fast" and p.counters.get("pace_was") == 1, (p.pace, p.counters))
ws.combat.service.refresh(f)
check("quickened from normal, the character unchanged: still quick after a rebuild", p.pace == "fast", p.pace)
ends(f, p)
check("...and normal once the quickening ends", p.pace == "normal", p.pace)
f = begin()
p = quicken(f)
me().equipment["body"] = items.make("chainmail", "common", 6)
ws.combat.service.refresh(f)
check("quickened from normal, the character slower by the rebuild: still quick", p.pace == "fast", p.pace)
ends(f, p)
check("...and the character's slower pace once it ends", p.pace == "slow", p.pace)
me().passives = [x for x in me().passives if x.id != "fb"]

# ---- second case: a gear change, then a point: the fighter is the character's whole (the finding's gear_in_fight.py)
me().equipment["body"] = items.make("chain_shirt", "common", 6)
me().equipment["main_hand"] = items.make("longsword", "common", 6)
store.save_player(ws.player)
f = begin()
p = f.player
check("(the fighter holds the sword)", p.weapon_name == me().equipment["main_hand"].name, (p.weapon_name, me().equipment["main_hand"].name))
del me().equipment["main_hand"]
me().equipment["body"] = items.make("padded", "common", 6)
store.save_player(ws.player)
ws.play("#attradd strength")
p = ws.combat.fight.player
fresh = combat.fighter_from_character(me(), p.id)
check("a gear change then a point: the weapon follows the character as the armour does",
      (p.weapon_name, p.weapon_damage, p.armor) == (fresh.weapon_name, fresh.weapon_damage, fresh.armor),
      ((p.weapon_name, p.weapon_damage, p.armor), (fresh.weapon_name, fresh.weapon_damage, fresh.armor)))

# ---- the kind: the declaration
def undeclared(names, given, owns) -> list:
    """Every field of a fighter declared neither the character's nor the fight's, or declared both."""
    return sorted((set(names) - given - owns) | (given & owns) | ((given | owns) - set(names)))


check("every field of a fighter is declared once, the character's or the fight's", bool(GIVEN) and not undeclared(combat.FLAT, GIVEN, OWNS),
      undeclared(combat.FLAT, GIVEN, OWNS) if GIVEN else "no declaration (combat.GIVEN, combat.FIGHT_OWNS)")
check("...so a field added to a fighter and declared neither is named", "a_new_field" in undeclared(set(combat.FLAT) | {"a_new_field"}, GIVEN, OWNS))
built = set().union(*(getattr(combat.fighter_from_character(me()), part).model_fields_set for part in combat.PARTS))
check("every field the character gives is one the Character to Fighter step sets (none is taken as a bare default)",
      bool(GIVEN) and GIVEN <= built, sorted(GIVEN - built))
SEEDS = {"id", "side", "hp", "stamina", "mana", "breath"}   # the fight's own that the step only seeds when the fight begins
check("...and every field that step sets is the character's or one of the fight's seeds, so none is declared the fight's by mistake",
      bool(GIVEN) and built - GIVEN <= SEEDS <= OWNS, sorted(built - GIVEN - SEEDS) or sorted(SEEDS - OWNS))

# ---- the kind: a fighter rebuilt where nothing wore it equals a fresh one over every field the character gives
f = begin()
ws.play("I attack the wolf.")
f = ws.combat.fight
me().equipment["main_hand"] = items.make("longsword", "common", 6)
me().equipment["body"] = items.make("chainmail", "common", 6)
me().passives.append(Passive(id="sb", name="Line Holder", description="d", tier=PowerTier.LIGHT, mechanic="shield_bearer", value=1))
store.save_player(ws.player)
ws.play("#attradd dexterity")
p = ws.combat.fight.player
mine, fresh = flat(p), flat(combat.fighter_from_character(me(), p.id))
apart = sorted(k for k in GIVEN if mine.get(k) != fresh.get(k))
check("a fighter rebuilt where nothing wore it equals a fresh one over every field the character gives (gear, a passive, a point)",
      bool(GIVEN) and not apart, apart or "no field is declared the character's")
me().passives = [x for x in me().passives if x.id != "sb"]

# ---- control: a fight saved before the steps were kept keeps its armour as the fight left it
me().equipment["body"] = items.make("chain_shirt", "common", 6)
store.save_player(ws.player)
for counter, steps, why in ((16, None, "the cap's counter and no steps"), (24, [8], "steps begun only after the counter")):
    f = begin()
    p = f.player
    p.armor = 5.0 * (1 - 8 / 100) * (1 - 8 / 100) * ((1 - 8 / 100) if counter == 24 else 1)
    p.counters["corroded"] = counter
    if steps is not None:
        p.counters["armor_steps"] = list(steps)
    old = p.armor
    store.save_combat(ws.combat.to_json())
    ws.combat = cs.CombatScene.resume(ws, store.load_combat())
    ws.play("#attradd constitution")
    p = ws.combat.fight.player
    check(f"a fight saved before the steps were kept ({why}) keeps its armour as the fight left it", p.armor == old, (p.armor, old))

# ---- the kind: a rebuild after every round, the character unchanged, leaves the fight's dump the same to the last key
import fight_fixtures as ff
from scenes.world import WorldScene
CASES = ff.cases()
MOVED, FAULTS, RAN = [], [], {"rounds": 0, "worn": 0, "label": ""}
real_turn, real_danger = WorldScene.turn, combat.danger


def turn(self, text):
    out = real_turn(self, text)
    if self.combat is not None:
        fight = self.combat.fight
        was = fight.model_dump(mode="json")
        self.combat.service.refresh(fight)
        d = ff.first_difference(was, fight.model_dump(mode="json"))
        RAN["rounds"] += 1
        RAN["worn"] += any(x.counters.get("armor_steps") for x in fight.player_fighters())
        if d:
            MOVED.append(f"{RAN['label'] or CASES[(self.store.meta.turn - 1) // 100]['id']} round {fight.round}: {d}")
    return out


WorldScene.turn = turn
try:                                                     # an ooze fight against a chain shirt: the fixtures' ooze ranger wears none
    me().equipment["body"] = items.make("chain_shirt", "common", 6)
    store.save_player(ws.player)
    store.save_combat(None)
    cube = ws.world.bestiary["gelatinous_cube"]
    foe = combat.fighter_from_creature(cube, 6, "normal", "e1", name="gelatinous cube")
    foe.max_hp = foe.hp = 5000
    ws.combat = cs.CombatScene.begin(ws, cube, [foe], "It is on you:")
    store.save_player(ws.player)
    RAN["label"] = "a played ooze fight"
    for _ in range(10):
        if ws.combat is None:
            break
        ws.play("I attack the cube.")
    played = dict(RAN)
finally:
    WorldScene.turn = real_turn
p = ws.combat.fight.player if ws.combat is not None else None
check(f"an ooze fight played {played['rounds']} rounds, rebuilt after each: the dump the same, with the armour worn {played['worn']} of them",
      played["rounds"] > 0 and played["worn"] > 0 and not MOVED, (MOVED[:4], p.counters.get("armor_steps") if p else None))
store.save_combat(None)
ws.combat = None
g.close()
saves.drop(NAME)

CHOSEN = [x for x in CASES if x["id"].split(":")[0] in ("family", "statuses", "hires", "rank")]
RAN.update(rounds=0, worn=0, label="")
MOVED.clear()
WorldScene.turn = turn
combat.danger = lambda fight, runs=80, seed=0: ("even", 0.5)      # the odds are not what is held here, and are the slow part
try:
    for s in range(ff.SHARDS):
        ff.play(s, only={x["id"] for x in CHOSEN if ff.shard_of(x) == s})
        FAULTS += ff.fault_lines()
finally:
    WorldScene.turn, combat.danger = real_turn, real_danger
check(f"over {len(CHOSEN)} fixture fights that lay nothing on the fighter by hand ({RAN['rounds']} rounds), the same", RAN["rounds"] > 0
      and not MOVED, MOVED[:4])
check("...the ooze family among them", any(x["id"] == "family:ooze" for x in CHOSEN), [x["id"] for x in CHOSEN if "ooze" in x["id"]])
check("...and no turn of them was rolled back by a fault", not FAULTS, FAULTS[:4])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
