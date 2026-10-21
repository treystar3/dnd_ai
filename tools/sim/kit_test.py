"""Starting kits: a class carries a weapon - or, if it keeps companions, a companion in its place (f222). A summoner's Bound summon is
made by its ability, not given in the kit, and the narrator hears of it."""
import sys, random, re
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
def a_StartingKit(u, k):
    weapon = re.search(r"WEAPON OPTIONS:\n\s+(\S+):", u).group(1) if "WEAPON OPTIONS" in u else ""
    comp = re.search(r"COMPANION OPTIONS:\n\s+(\S+):", u)
    return {"weapon": weapon, "companion": comp.group(1) if comp else "", "companion_name": "Rook" if comp else ""}
stub.a_StartingKit = a_StartingKit
simlib.install(stub)
from character import kit as K
from world.loader import load_world
from llm.contracts import StartingKit
from pydantic import ValidationError
from engine import items

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
world = load_world()

c, _ = simlib.make_character("warrior", random.Random(1))
c.equipment = {}; c.companions = []; c.kit_given = False; c.coins = 0
txt = K.give_starting_kit(c, "warrior", False, world)
check("an ordinary class gets a weapon", "main_hand" in c.equipment or any(items.base_of(i).is_weapon for i in c.equipment.values()), list(c.equipment))
check("...and no companion", not c.companions)

c, _ = simlib.make_character("warrior", random.Random(1))
c.equipment = {}; c.companions = []; c.kit_given = False; c.coins = 0; c.actives = [a for a in c.actives if a.effect.value != "summon"]
txt = K.give_starting_kit(c, "beast handler", True, world)
check("a companion class gets its companion", len(c.companions) == 1, txt)
check("...in place of a weapon", not any(items.base_of(i).is_weapon for i in c.equipment.values()), list(c.equipment))
check("...and the narrator is told so", "named Rook" in txt and "in place of any weapon" in txt, txt)

stub.cls = "summoner"
c, _ = simlib.make_character("summoner", random.Random(1))
stub.cls = "warrior"
c.equipment = {}; c.companions = []; c.kit_given = False; c.coins = 0
bound = c.bound_summon
txt = K.give_starting_kit(c, "summoner", False, world)
check("a summoner who keeps no companions carries a weapon", any(items.base_of(i).is_weapon for i in c.equipment.values()) and not c.companions, list(c.equipment))
check("...and the narrator hears of its Bound summon", bound and "the summon they made" in txt, txt)

ctx = {"needs_companion": True, "weapons": ["dagger"], "companions": ["wolf"]}
try:
    StartingKit.model_validate({"weapon": "", "companion": "wolf", "companion_name": "Rook"}, context=ctx)
    check("a companion kit with no weapon is refused", False)
except ValidationError:
    check("a companion kit with no weapon is refused", True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
