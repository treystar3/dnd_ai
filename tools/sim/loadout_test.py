"""The loadout (f232): every ability stays in the book, but only 5 spells and 5 techniques are brought at first (10 each by level 100);
everything counts; changed out of combat, once a day, the first change free; a newly learned ability comes along when there is room;
only what is brought reaches a fight or the world."""
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from core.models import Character, Ability
from engine import loadout as LO, combat
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def ab(i, effect="damage", resource="mana", tier="light", context="combat", field_use=""):
    return Ability(id=f"a{i}", name=f"Ability {i}", description="d", effect=effect, tier=tier, reach="ranged" if effect != "defense" else "self",
                   resource=resource, context=context, cost=5, cooldown=0, field_use=field_use)

def char(actives, level=1):
    return Character(name="T", archetype="mage", custom_class="X", level=level, actives=actives)

check("room is 5 at level 1", LO.room(1) == 5)
check("...6 at 20, 8 at 60", LO.room(20) == 6 and LO.room(60) == 8)
check("...and 10 at level 100, no more after", LO.room(100) == 10 and LO.room(300) == 10)

spells = [ab(i) for i in range(8)] + [ab(8, "control"), ab(9, "healing"), ab(10, "mobility")]
techs = [ab(20 + i, resource="stamina") for i in range(7)] + [ab(30, "utility", "stamina", context="out_of_combat", field_use="picklock")]
c = char(spells + techs)
brought = LO.prepared(c)
s_ = [a for a in brought if LO.pool_of(a) == "spells"]; t_ = [a for a in brought if LO.pool_of(a) == "techniques"]
check("the first pick brings 5 of each", len(s_) == 5 and len(t_) == 5, (len(s_), len(t_)))
check("...spreading over kinds before doubling up", {a.effect.value for a in s_} >= {"damage", "control", "healing", "mobility"}, [a.effect.value for a in s_])
check("...and the rest stays in the book", len(LO.book(c)) == len(c.actives) - 10)

f = combat.fighter_from_character(c)
check("only what is brought reaches a fight", {m.id for m in f.moves if not m.id.startswith("relic")} == {a.id for a in brought},
      ({m.id for m in f.moves}, {a.id for a in brought}))

msg = LO.change(c, ["a0", "a1", "a2"], day=3, in_combat=True)
check("no change in a fight", "fight" in msg and c.loadout_free)
msg = LO.change(c, ["a0", "a1", "a2", "a3", "a4", "a5"], day=3, in_combat=False)
check("no more than the room", "at most 5" in msg)
msg = LO.change(c, ["a5", "a6", "a7"], day=3, in_combat=False)
s_ = [a.id for a in LO.prepared(c) if LO.pool_of(a) == "spells"]
check("the first change is free and sets that pool", sorted(s_) == ["a5", "a6", "a7"] and not c.loadout_free, (s_, msg))
check("...leaving the other pool alone", len([a for a in LO.prepared(c) if LO.pool_of(a) == "techniques"]) == 5)
msg = LO.change(c, ["a0"], day=3, in_combat=False)
check("a second change the same day is refused", "tomorrow" in msg and "a0" not in c.prepared, msg)
msg = LO.change(c, ["a0", "a30"], day=4, in_combat=False)
check("the next day it can change again, both pools at once", "a0" in c.prepared and "a30" in c.prepared, msg)

c.actives.append(ab(40))
LO.prepared(c)
check("a newly learned spell comes along when there is room", "a40" in c.prepared)
c2 = char([ab(i) for i in range(5)])
LO.prepared(c2)
c2.actives.append(ab(99))
LO.prepared(c2)
check("...and waits in the book when there is none", "a99" not in c2.prepared)
c2.level = 20
LO.prepared(c2)
check("...until a level brings more room, which the book fills", "a99" in c2.prepared)

c3 = char([ab(1), ab(30, "utility", "stamina", context="out_of_combat", field_use="bind_beast")])
LO.prepared(c3)
from engine import taming
check("an out-of-combat ability that is brought can be used", taming.binder(c3) is not None)
LO.change(c3, ["a1", "a2"] if False else ["a1"], day=1, in_combat=False)
c3.prepared = ["a1"]
check("...and one left in the book cannot", taming.binder(c3) is None)

lines = "\n".join(LO.lines(c, day=4, in_combat=False))
check("the book shows the room and what is brought", "SPELLS - bringing" in lines and "TECHNIQUES - bringing" in lines and "*" in lines, lines)
check("...and numbers turn into abilities", LO.by_number(c, ["1", "Ability 3"])[0] == next(a.id for a in c.actives if LO.pool_of(a) == "spells"))

print("\nFAILED:", bad if bad else "none")
sys.exit(1 if bad else 0)
