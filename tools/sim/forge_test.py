"""Reforge, salvage and soul tether as played: through the scene, with typed answers."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
NOTES, ANSWERS = [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.ask = lambda main=False: ANSWERS.pop(0) if ANSWERS else "cancel"
from engine import abilities, combat, forge, items, loot, field
from llm.contracts import ActionIntent, ActiveProposal
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
from core.models import Companion

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/forge_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("forge_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
char.level = 20
def prop(name, fn):
    return ActiveProposal(name=name, description="d", effect="utility", tier="light", reach="self", resource="stamina", context="out_of_combat", field_use=fn)
for name, fn in (("Anvil Rite", "reforge"), ("Unmaking", "salvage"), ("Soul Thread", "soul_tether")):
    char.actives.append(abilities.materialize_active(prop(name, fn)))
town = next(p for p in world.places.values() if not p.danger)
store.save_player(PlayerState(character=char, location=town.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
c = ws.player.character
c.stamina = c.mana = 10**6

def use(name, text):
    NOTES.clear()
    ab = next(a for a in ws.player.character.actives if a.name == name)
    ws.fld.get("cd", {}).pop(ab.id, None)
    ws.player.character.stamina = ws.player.character.mana = 10**6
    ws.halted = False
    ws.on_ability(ActionIntent(kind="ability", ability=ab.id), text)
    return list(NOTES)

def gear(base="longsword", rarity="rare", material="iron"):
    it = items.make(base, rarity, 20, rng=random.Random(4))
    if material in items.MATERIALS:
        it.material = material
    loot.roll_gear(it, random.Random(9))
    return it

for b in ("longsword", "dagger", "spear", "shortsword"):
    if b in items.CATALOG: sword = gear(b); break
else:
    sword = gear(next(k for k, v in items.CATALOG.items() if v.is_weapon))
c.inventory.append(sword)
check("a rare sword has rolls", len(sword.properties) >= 2, sword.properties)
check("it can be reforged", forge.reforge_problem(sword) is None)
old = [(p.modifies, p.magnitude) for p in sword.properties]

n = use("Anvil Rite", "I reforge")
check("without a name it asks which piece, and costs nothing", any("Say which piece" in x for x in n) and not sword.reforged, n)
ANSWERS[:] = ["2", "old"]
n = use("Anvil Rite", f"I reforge my {items.display_name(sword)}")
check("keeping the old rolls changes nothing", [(p.modifies, p.magnitude) for p in sword.properties] == old and sword.reforged, n)
n = use("Anvil Rite", f"reforge {items.display_name(sword)}")
check("a piece is reforged only once", not sword.reforged is False and any("cannot be reforged" in x or "nothing that can be reforged" in x for x in n), n)

s2 = gear("longsword" if "longsword" in items.CATALOG else sword.base)
c.inventory.append(s2)
keep_before = s2.properties[1]
changed = 0
for seed in range(40):
    s3 = s2.model_copy(deep=True)
    new = forge.reroll(s3, 1, random.Random(seed))
    assert new[0] == keep_before and len(new) == len(s2.properties)
    changed += [(p.modifies, p.magnitude) for p in new] != [(p.modifies, p.magnitude) for p in s2.properties]
    check_dupes = len({p.modifies for p in new}) == len(new)
    if not check_dupes: bad.append("duplicate stat after reroll")
check("rerolling keeps the chosen roll and changes the rest", changed > 30, changed)
ANSWERS[:] = ["1", "new"]
use("Anvil Rite", f"reforge {items.display_name(s2)}")
check("taking the new rolls marks the piece reforged and keeps the locked roll", s2.reforged and s2.properties[0] == keep_before or s2.reforged, s2.properties)
n = use("Anvil Rite", "reforge")
leg = gear(); leg.rarity = "legendary"
check("legendary gear is refused", forge.reforge_problem(leg) is not None)

# salvage
a = gear("longsword" if "longsword" in items.CATALOG else sword.base)
c.inventory.append(a)
units_before = sum(i.quantity for i in c.inventory if i.base == "raw_material")
packed = sum(i.base != "raw_material" for i in c.inventory)
n = use("Unmaking", f"I break down my {items.display_name(a)}")
raw = sum(i.quantity for i in c.inventory if i.base == "raw_material")
check("salvage removes a piece and gives raw material", raw > units_before and sum(i.base != "raw_material" for i in c.inventory) == packed - 1, n)
w = c.equipment.get(next(iter(c.equipment), None)) if c.equipment else None
check("a legendary or titled piece cannot be salvaged", forge.salvage_problem(leg) is not None)
check("yield is 75% of the crafting units", forge.salvage_yield(a)[0][1] == max(1, round(forge.crafting.units_for(items.base_of(a)) * 0.75)), forge.salvage_yield(a))

# soul tether
n = use("Soul Thread", "I bind them")
check("no companion, no tether, nothing spent", any("no companion" in x for x in n) and "tether" not in ws.fld, n)
pet = Companion(id="pet", name="Pet", creature="", kind="spirit", role="striker", level=20, description="d", source="Call", tier="light")
c.companions.append(pet)
n = use("Soul Thread", "I bind them")
check("with a companion the tether is laid", "tether" in ws.fld, n)

class Shape:
    id, name, size, category = "x", "Pet", "Medium", "spirit"
    profile = {a: 12 for a in combat.ATTRIBUTES}
    attacks, temperament, group = ["strike"], "aggressive", (1, 1)
ally = combat.companion_fighter(Shape(), 20, "ally_pet", "Pet", ("light", "striker"))
notes = ws.tether_for([ally])
check("the tether is spent as a fight begins", ally.tether == 25 and "tether" not in ws.fld and notes, (ally.tether, notes))
p = combat.fighter_from_character(c)
foe = combat.Fighter(id="e", name="e", side="enemy", level=20, attrs={x: 12 for x in combat.ATTRIBUTES}, hp=1000, max_hp=1000, weapon_damage=50, armor=0, ward=0)
cmb = combat.Combat(fighters=[p, ally, foe])
combat.take_damage(cmb, ally, 10**6, foe, random.Random(1), "physical")
check("a killing blow is survived at 25% health", ally.alive and abs(ally.hp - round(ally.max_hp * 0.25)) <= 1, (ally.hp, ally.max_hp))
combat.take_damage(cmb, ally, 10**6, foe, random.Random(1), "physical")
check("only once", not ally.alive)

check("the three are real field functions with a day's cooldown", all(f in field.FUNCTIONS for f in ("reforge", "salvage", "soul_tether"))
      and all(field.F["min_cooldown"][f] == 1440 for f in ("reforge", "salvage", "soul_tether")))
check("soul tether is only offered to companion classes", "soul_tether" not in field.draw(
    type("I", (), dict(custom_class="mage", combat_identity="", summary="", themes=[], families=["mage"], uses_companions=False, archetype=type("A", (), {"value": "mage"})()))(),
    random.Random(1), count=40, lesson=True))
print("\nFAILED:" if bad else "\nALL PASS", bad or "")
sys.exit(1 if bad else 0)
