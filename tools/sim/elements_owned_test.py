"""Elements are the engine's (f220): every elemental ability's element is planned with the slot - from the class's named palette, or its
families' lean - and carried as Ability.element into combat. The model is told the element and only narrates it; a name or description
that reads as another element is turned back. A fire mage is offered fire and nothing else."""
import random
import sys
import types
from collections import Counter
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("mage", 1))
from engine import ability_slots as AS, ability_traits, elements as EL, lessons
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def interp(palette, fams=("mage",), cls="Mage"):
    return types.SimpleNamespace(archetype=types.SimpleNamespace(value="mage"), families=list(fams), focus="balanced", uses_companions=False,
                                 custom_class=cls, combat_identity="", summary="", themes=[], primary_attributes=["intelligence"],
                                 casting_attribute="intelligence", elements=list(palette), constraints=[])

def plans(i, n=40):
    out = []
    for s in range(n):
        out += AS.plan(i, ability_traits.draw_offers(i, random.Random(s), min_functions=5), 5, random.Random(s))
    return out

# ---- a fire mage: fire, only fire
fire = plans(interp(["fire"], cls="Fire Mage"))
el = [s for s in fire if AS.elemental(s)]
check("a fire mage has elemental abilities to plan", len(el) >= 40, len(el))
check("...and every one of them is fire", all(s["element"] == "fire" for s in el), Counter(s["element"] for s in el))
check("non-elemental abilities carry no element", all(s["element"] == "" for s in fire if not AS.elemental(s)))

# ---- a two-element palette: both, nothing else
duo = [s for s in plans(interp(["lightning", "cold"], cls="Storm Witch")) if AS.elemental(s)]
seen = Counter(s["element"] for s in duo)
check("a storm-and-frost witch gets both her elements and only those", set(seen) == {"lightning", "cold"}, seen)

# ---- an open palette: the family's lean, with some unaligned
open_ = [s for s in plans(interp([])) if AS.elemental(s)]
seen = Counter(s["element"] for s in open_)
lean = set(EL.R["family_lean"]["mage"])
check("an open mage spreads across its family's elements", len(set(seen) - {""}) >= 3 and set(seen) - {""} <= lean, seen)
check("...and some of its magic carries no element", 0 < seen[""] < len(open_) * 0.5, seen)
pal = [s for s in plans(interp([], fams=("paladin",), cls="Paladin")) if AS.elemental(s)]
check("a paladin's magic leans radiant and fire", set(s["element"] for s in pal) - {""} <= {"radiant", "fire"}, Counter(s["element"] for s in pal))

# ---- elemental weapons always have an element
wep = [s for s in plans(interp([]), 80) if s["effect"] == "buff" and s.get("buff") == "elemental"]
check("an elemental weapon is never unaligned", all(s["element"] for s in wep), [s["element"] for s in wep])

# ---- the model is told; a contradiction is turned back
s = next(s for s in fire if AS.elemental(s))
check("the model is told the element", "it is fire" in AS.mechanic_text(s))
check("a fire name passes", AS.text_problem(s, "Searing Flame", "a gout of fire") in (None, "") or "reads as" not in (AS.text_problem(s, "Searing Flame", "a gout of fire") or ""))
p = AS.text_problem(s, "Frost Lance", "a spear of ice")
check("a frost name on a fire slot is turned back", bool(p) and "reads as cold" in p, p)
u = dict(s, element="")
check("an unaligned slot is told to stay unaligned", "carries no element" in AS.mechanic_text(u))
p = AS.text_problem(u, "Fire Bolt", "a bolt of flame")
check("...and an elemental name on it is turned back", bool(p) and "not elemental" in p, p)
check("a name with no element words is fine either way", "reads as" not in (AS.text_problem(s, "Arcane Spear", "a lance of force") or ""))

# ---- carried through to the ability and into combat
from core.models import Ability
check("Ability carries an element field", "element" in Ability.model_fields)
from engine import combat
import inspect
check("combat reads the planned element, not the words", "element=a.element" in inspect.getsource(combat))

# ---- lessons: the class palette, and an element named in the request
c = types.SimpleNamespace(custom_class="Fire Mage", class_summary="", archetype=types.SimpleNamespace(value="mage"), uses_companions=False,
                          primary_attributes=["intelligence"], casting_attribute="intelligence", elements=["fire"], actives=[], level=3,
                          passives=[], legendary={}, recipes_made=[], attributes={})
got = []
for sd in range(30):
    try:
        got += [s for s in lessons.plan(c, lessons.Want("active", "damage", "", "teach me a spell"), random.Random(sd), can_passive=False)
                if AS.elemental(s)]
    except Exception as ex:
        check("lessons plan for a fire mage", False, repr(ex)); break
check("a fire mage's lessons are fire", got and all(s["element"] == "fire" for s in got), Counter(s["element"] for s in got))
w = lessons.from_words("teach me a frost spell")
check("a request that names frost is read as cold", w.element == "cold", w)
got = []
for sd in range(30):
    got += [s for s in lessons.plan(c, lessons.Want("active", "damage", "", "frost spell", "cold"), random.Random(sd), can_passive=False)
            if AS.elemental(s) and s["biased"]]
check("...and the lessons answering it carry cold", got and all(s["element"] == "cold" for s in got), Counter(s["element"] for s in got))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
