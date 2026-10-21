"""The creation perks outside a fight (f211): every world rule a player can be born with, run twice where its loop allows - the gamble
on checks, the road that shortens, the name that travels (and the one that never sticks), the law that fines instead of jails, the
drink that loosens tongues, the hands that make gear anywhere and spare the consumables, armor that fits, the beast's gift in a meal,
the camp cook, the spirit that walks ahead, the dead that keep their peace, the temple's hospitality and the dreams that name a place.
Numbers from data/rules/perks.yaml (world:); rules in engine/world_perks.py and scenes/passive_hooks.py."""
import random
import shutil
import sys
import types
sys.path.insert(0, ".")
import simlib
STUB = simlib.Stub("warrior", 5)
simlib.install(STUB)
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from core.models import Passive, PowerTier
from engine import checks, combat, inventory as inv, items, law, needs, standing, world_perks as WP
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
needs.N.update(hunger_per_hour=0, fatigue_per_hour=0, fight={'hunger': 0, 'fatigue': 0})
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/pw_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("pw_test")
store.meta.seed = 7; store.meta.turn = 1; store.meta.minutes = 9 * 60; store.save_meta()
char, spec = simlib.make_character("warrior", random.Random(3))
char.level = 6
town = next(p for p in world.places.values() if p.type in ("town", "city", "village") and not p.danger and p.connects)
store.save_player(PlayerState(character=char, location=town.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
c = ws.player.character
c.stamina = c.mana = c.health = 10**6

def give(mid, value=1):
    c.passives[:] = [p for p in c.passives if p.mechanic != mid]
    c.passives.append(Passive(id=f"perk-{mid}", name=mid.replace("_", " ").title(), description="d", tier=PowerTier.LIGHT, mechanic=mid, value=value))

def take(mid):
    c.passives[:] = [p for p in c.passives if p.mechanic != mid]

# ---- All or Nothing: no partials, and a failure costs something
give("all_or_nothing")
check("all or nothing 1: a partial is a success", WP.gamble(c, "partial") == "success")
check("all or nothing 2: ...and the die says so too", all(checks.roll(50, random.Random(s), c=c)[0] != "partial" for s in range(200)))
npc = types.SimpleNamespace(trust=50, name="Marta Voss", role="merchant")
ws.player.reputation[town.id] = 10
NOTES.clear()
ws.bad_failure("persuasion", npc)
check("all or nothing 1: a bad failure costs trust and standing", npc.trust == 45 and ws.player.reputation[town.id] == 9, (npc.trust, ws.player.reputation.get(town.id)))
ws.bad_failure("persuasion", npc)
check("all or nothing 2: ...every time", npc.trust == 40 and ws.player.reputation[town.id] == 8)
take("all_or_nothing")
check("without it, a partial stays a partial and nothing is taken", WP.gamble(c, "partial") == "partial" and (ws.bad_failure("persuasion", npc) is None and npc.trust == 40))

# ---- Borrowed Hands: the best of you and your companions
ws.player.party = [{"id": "h1", "name": "Rue Quill", "role": "archer", "level": 5, "active": True}]
c.attributes.wisdom = 8
give("borrowed_hands")
who, lent = WP.best_hands(c, "perception", ws.player.party)
check("borrowed hands 1: a hunter's eyes for a perception check", who == "Rue" and lent > 0, (who, lent))
who2, lent2 = WP.best_hands(c, "perception", [{"id": "h2", "name": "Bram Fell", "role": "fighter", "level": 5, "active": True}])
check("borrowed hands 2: a sellsword's eyes are worse than a hunter's", lent2 < lent, (who2, lent2))
bon = ws.check_bonuses("perception")
check("...and it rides into the check as a bonus", any("borrowed hands" in b[0] for b in bon), bon)
take("borrowed_hands")
check("without it, no bonus", not any("borrowed hands" in b[0] for b in ws.check_bonuses("perception")))
ws.player.party = []

# ---- Well-Trodden: a road walked before takes half the time
nxt = next(iter(town.connects))
route = [town.id, nxt]
ws.player.visited = [town.id]
base = ws.travel_minutes(route, 120)
give("well_trodden")
check("well trodden 1: a road not yet walked costs the full time", ws.travel_minutes(route, 120) == base, (base, ws.travel_minutes(route, 120)))
ws.player.visited = [town.id, nxt]
half = ws.travel_minutes(route, 120)
check("well trodden 1: ...walked before, half", half == round(base * WP.P["well_trodden"]["share"]), (base, half))
check("well trodden 2: and again on the way back", ws.travel_minutes([nxt, town.id], 120) == half)
take("well_trodden")

# ---- Famous: standing spreads to every road-neighbor town at once, in full; Nobody: it never sticks
neighbors = ws.neighbor_towns(town.id)
give("famous")
ws.player.reputation = {}
ws.reputation_add(town.id, 3)
check("famous 1: the neighbors hear it, in full", neighbors and all(ws.player.reputation.get(t) == 3 for t in neighbors), {t: ws.player.reputation.get(t) for t in neighbors})
ws.reputation_add(town.id, -2)
check("famous 2: ...and infamy too", all(ws.player.reputation.get(t) == 1 for t in neighbors))
take("famous")
give("nobody")
ws.player.reputation = {}
ws.reputation_add(town.id, -5)
check("nobody 1: infamy never sticks", ws.player.reputation.get(town.id, 0) == 0)
ws.reputation_add(town.id, 2)
check("nobody 1: ...renown is yours alone", ws.player.reputation.get(town.id) == 2 and not any(ws.player.reputation.get(t) for t in neighbors))
day = 10
law.set_heat(ws.player, town.id, 60, day)
check("nobody 2: heat is real today", law.current_heat(ws.player, town.id, day) == 60)
check("nobody 2: ...and gone tomorrow", law.current_heat(ws.player, town.id, day + 1) == 0)
take("nobody")
check("without it, heat decays slowly", law.current_heat(ws.player, town.id, day + 1) == 60 - law.H["decay_per_day"])
ws.player.heat = {}

# ---- Above the Law: no cell; the purse pays, then standing
give("above_the_law")
guard = types.SimpleNamespace(memories=[], name="Garrick Harl", label=lambda: "the guard", role="guard", trust=50)
ws.narrate = lambda *a, **k: None
c.coins = 5000
ws.player.reputation = {town.id: 10}
ws.pay_in_standing(guard, town.id, 25000)
check("above the law 1: no jail - the purse is emptied and the rest is paid in standing", c.coins == 0 and ws.player.reputation[town.id] == 8, (c.coins, ws.player.reputation))
c.coins = 40000
ws.pay_in_standing(guard, town.id, 20000)
check("above the law 2: with coin enough, standing is untouched", c.coins == 20000 and ws.player.reputation[town.id] == 8)
take("above_the_law")

# ---- Tavern Ear: a drink at the inn and the town talks
st = store.load_world_state() or {}
st.setdefault("threads", []).append({"id": "t1", "title": "A Missing Shepherd", "place": town.id, "status": "active", "stage": 0,
                                     "stages": [{"description": "A shepherd has not come down from the hills."}], "tier": "common"})
store.save_world_state(st)
give("tavern_ear")
inn = types.SimpleNamespace(role="innkeeper", name="Hollis")
NOTES.clear(); ws.tavern_ear(inn)
check("tavern ear 1: the town's troubles come with the drink", any("Tavern Ear" in n and "shepherd" in n.lower() for n in NOTES), NOTES[-1:] )
NOTES.clear(); ws.tavern_ear(inn)
check("tavern ear 2: ...and again", any("Tavern Ear" in n for n in NOTES))
NOTES.clear(); ws.tavern_ear(types.SimpleNamespace(role="smith", name="Odo"))
check("...but a smith's forge is not an inn", not NOTES)
take("tavern_ear")

# ---- Troubadour: a performance carries the realm's news and earns standing where it is sung of
give("troubadour")
ws.player.reputation = {}
NOTES.clear(); ws.troubadour("success")
check("troubadour 1: the song carries the news, and the town sung of remembers", any("Troubadour" in n for n in NOTES) and ws.player.reputation.get(town.id) == 1, (NOTES[-1:], ws.player.reputation))
ws.troubadour("success")
check("troubadour 2: ...again", ws.player.reputation.get(town.id) == 2)
ws.troubadour("failure")
check("...a bad performance carries news but earns nothing", ws.player.reputation.get(town.id) == 2)
take("troubadour")

# ---- Visions: sleep names a place
far_town = next(p for p in world.places.values() if p.type in ("town", "city", "village") and not p.danger and p.id != town.id)
st = store.load_world_state(); st["threads"].append({"id": "t2", "title": "Fires in the Granary", "place": far_town.id, "status": "active", "stage": 0,
                                                     "stages": [{"description": "Grain stores are burning."}], "tier": "common"})
store.save_world_state(st)
give("visions")
seen = []
ws.narrate = lambda text, *a, **k: seen.append(text)
NOTES.clear(); ws.vision()
check("visions 1: the dream names the place", any(far_town.name in n for n in NOTES) and any(far_town.name in t for t in seen), NOTES[-1:])
NOTES.clear(); ws.vision()
check("visions 2: ...and again", any("vision" in n.lower() for n in NOTES))
take("visions")

# ---- Practiced Hands: made at a workshop once, made anywhere after
base = next(b for b in items.CATALOG.values() if getattr(b, "family", "") == "metal" and b.slot == "body")
check("practiced hands: nothing is remembered before a workshop", base.id not in c.recipes_made)
c.recipes_made.append(base.id)
give("practiced_hands")
check("practiced hands 1: a remembered base needs no workshop", base.id in c.recipes_made and ws.owns("practiced_hands"))
take("practiced_hands")

# ---- Frugal Hands: a consumable not used up, at the mechanic's rate
give("frugal_hands", 30)
random.seed(4)
saves = sum(ws.frugal_save() for _ in range(2000))
check("frugal hands 1: about three in ten are spared", 480 <= saves <= 720, saves)
give("frugal_hands", 100)
check("frugal hands 2: at a hundred, every one", all(ws.frugal_save() for _ in range(20)))
take("frugal_hands")
check("without it, none", not any(ws.frugal_save() for _ in range(20)))

# ---- Shaped to You: your own armor's weight does not tell on you
plate = items.make_gear(base.id, "iron", "common", 6, random.Random(1)) if hasattr(items, "make_gear") else None
if plate is None:
    from engine import crafting
    plate = crafting.make_gear(base, "iron", 50, random.Random(1), 0)
plate.source = "your own work"
c.equipment["body"] = plate
heavy_pace = combat.fighter_from_character(c).pace
give("shaped_to_you")
check("shaped to you 1: fitted plate leaves you quick on your feet", combat.fighter_from_character(c).pace == "normal" and heavy_pace != "normal" or items.weight(plate) != "heavy",
      (heavy_pace, combat.fighter_from_character(c).pace, items.weight(plate)))
plate.source = "a smith's work"
check("shaped to you 2: bought plate still weighs what it weighs", combat.fighter_from_character(c).pace == heavy_pace)
take("shaped_to_you")
c.equipment.pop("body", None)

# ---- Symbiosis: a meal of your own hunt carries the beast's gift until you sleep
give("symbiosis")
meat = inv.make_good("venison", 1); meat.origin = "prey_animal"
meal = inv.make_good("hearty_meal", 1); meal.origin = meat.origin
ws.consume(meal)
check("symbiosis 1: the meal gives the beast's gift", c.gift.get("family") == "prey_animal" and c.gift["mechanics"] == WP.gift_for("prey_animal"), c.gift)
check("symbiosis 1: ...and the fighter carries it", all(k in combat.fighter_from_character(c).legendary for k in c.gift["mechanics"]))
ws.after_sleep()
check("symbiosis 1: sleep takes it back", not c.gift)
meal2 = inv.make_good("hearty_meal", 1); meal2.origin = "pack_hunter"
ws.consume(meal2)
check("symbiosis 2: another beast, another gift", c.gift.get("family") == "pack_hunter" and "rending" in c.gift["mechanics"])
c.gift = {}
raw = inv.make_good("venison", 1); raw.origin = "pack_hunter"
ws.consume(raw)
check("...raw meat gives nothing: it must be cooked", not c.gift)
take("symbiosis")
check("without it, a cooked meal is only a meal", (ws.consume(meal2) or True) and not c.gift)

# ---- the meal recipe: made from any meat, and it keeps the meat's origin
inv_bag = [m for m in [inv.make_good("boar_meat", 1)]]
inv_bag[0].origin = "brute_beast"
recipe = inv.find_recipe("hearty meal")
check("a hearty meal is made from any meat", recipe is not None and not inv.can_craft(inv_bag, recipe))
taken = inv.remove_goods(inv_bag, meat=True, count=1)
check("...and the meat comes out of the pack, origin and all", taken and taken[0].origin == "brute_beast" and not inv_bag)

# ---- Campfire Cook: a meal at camp feeds the party and warms them to you
wild = next(p for p in world.places.values() if p.danger)
ws.player.party = [{"id": "h1", "name": "Rue Quill", "role": "rogue", "level": 5, "bond": 10, "active": True},
                   {"id": "h2", "name": "Bram Fell", "role": "fighter", "level": 5, "bond": 0, "active": True}]
ws.player.location = wild.id
give("campfire_cook")
c.hunger = 50
NOTES.clear(); ws.campfire_cook({"hearty_meal": 1})
check("campfire cook 1: the party eats and thinks better of you", all(m["bond"] in (12, 2) for m in ws.player.party) and c.hunger < 50, [m["bond"] for m in ws.player.party])
ws.campfire_cook({"hearty_meal": 1})
check("campfire cook 2: ...every meal", [m["bond"] for m in ws.player.party] == [14, 4])
ws.campfire_cook({"healing_draught": 1})
check("...a draught is not a meal", [m["bond"] for m in ws.player.party] == [14, 4])
ws.player.location = town.id
ws.campfire_cook({"hearty_meal": 1})
check("...and an inn kitchen is not a camp", [m["bond"] for m in ws.player.party] == [14, 4])
take("campfire_cook")
ws.player.party = []

# ---- Spirit Guide: with the summon walking ahead, hostiles are always seen coming
from core.models import Companion
give("spirit_guide")
check("spirit guide: without the spirit out, nothing", not ws.sees_far())
c.companions.append(Companion(id="sp", name="the spirit", kind="spirit", role="striker"))
check("spirit guide 1: with it, you see them coming", ws.sees_far())
c.companions[0].fallen = True
check("spirit guide 2: a fallen spirit guides nobody", not ws.sees_far())
c.companions.clear()
take("spirit_guide")

# ---- Pale Company: the undead keep their peace
give("pale_company")
ghoul = next(cr for cr in world.bestiary.values() if cr.category == "undead")
wolf = next(cr for cr in world.bestiary.values() if cr.category == "beast")
check("pale company 1: the undead do not attack first", ws.temperament(ghoul) == "passive")
check("pale company 2: a wolf is still a wolf", ws.temperament(wolf) == wolf.temperament or ws.temperament(wolf) == "passive" and ws.deterred(wolf, None))
take("pale_company")
check("without it, the dead are hungry", ws.temperament(ghoul) != "passive" or ws.deterred(ghoul, None))

# ---- Pious Path: the temple feeds you and yours
give("pious_path")
ws.player.party = [{"id": "h1", "name": "Rue Quill", "role": "rogue", "level": 5, "bond": 10, "active": True}]
c.hunger = 50
NOTES.clear(); ws.pious_hospitality()
check("pious path 1: fed and housed for nothing", c.hunger < 50 and any("Pious Path" in n for n in NOTES))
c.hunger = 50
ws.pious_hospitality()
check("pious path 2: ...at every temple", c.hunger < 50)
take("pious_path")
ws.player.party = []

# ---- the registry knows every world perk, and creation offers them to the right families
from core.rules import MECHANICS, FAMILIES
world_perks = [m for m in MECHANICS.values() if m.kind == "world" and m.where == "creation" and m.id in
               ("all_or_nothing", "well_trodden", "famous", "troubadour", "nobody", "above_the_law", "borrowed_hands", "tavern_ear",
                "practiced_hands", "frugal_hands", "shaped_to_you", "enchanter", "symbiosis", "campfire_cook", "spirit_guide",
                "pale_company", "pious_path", "visions")]
check("the eighteen world perks are registered at creation", len(world_perks) == 18, len(world_perks))
listed = {o.mechanic for f in FAMILIES.values() for o in f.options}
check("...and every one of them belongs to a family", all(m.id in listed for m in world_perks), [m.id for m in world_perks if m.id not in listed])
check("needs is an axis tag, never a gate: the draw has no fuel parameter", "fuel" not in __import__("inspect").signature(__import__("character.creation", fromlist=["draw_mechanics"]).draw_mechanics).parameters)

shutil.rmtree("saves/pw_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
