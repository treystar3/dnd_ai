"""(f505) The health write-path rule (tools/purity.py hp_writes): the health bar is written by engine/damage.py (the declared paths) and
engine/combat.py restore, and by the named exemptions and nowhere else; the scan over engine/, scenes/, services/ and npc/ finds nothing;
every exemption still names a line that exists (the list may only shrink); a planted write is caught, in the law and in restore it is
not; two reflectors against each other (a Retribution fighter struck by a Spellmirror one, and back) end without recursion, each rebound
written once in the log with the striker it returned to. Nothing stays in the process."""
import random
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import purity
from engine import combat

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

check("no module outside the law writes a health bar", purity.hp_writes() == [], purity.hp_writes())
check("every exemption names a line that still exists (the list may only shrink)", purity.hp_exempt_missing() == [], purity.hp_exempt_missing())
check("the exemptions are the named sites: construction, unmaking, floors, heals outside restore, costs, a trap", len(purity.HP_EXEMPT) == 20
      and {rel for rel, _ in purity.HP_EXEMPT} == {"engine/combat.py", "engine/bosses.py", "engine/events.py", "engine/party.py", "engine/summons.py",
                                                   "engine/combat_perks.py", "scenes/arc_actions.py", "services/fight.py", "engine/spellcraft.py",
                                                   "engine/healing.py", "engine/relics.py", "scenes/field_actions.py"}, sorted(purity.HP_EXEMPT))
planted = "def hurt(f, n):\n    f.hp = max(0, f.hp - n)\n    f.hp -= 1\n    f.max_hp = f.hp = 3\n"
found = purity.hp_writes_in(planted, "engine/planted.py")
check("a planted write is caught, each line", len(found) == 3 and all("engine/planted.py" in x for x in found), found)
check("...not in the law", purity.hp_writes_in(planted, "engine/damage.py") == [])
in_restore = "def other(f):\n    f.hp = 1\n\n\ndef restore(combat, f, amount):\n    f.hp = min(f.max_hp, f.hp + amount)\n    return f.hp\n"
found = purity.hp_writes_in(in_restore, "engine/combat.py")
check("...and restore may write, the function beside it may not", found == ["engine/combat.py:2 writes .hp"], found)
check("an exemption is read as written: the same line in another file is caught", purity.hp_writes_in("x = 1\nf.hp = 0\n", "engine/other.py") == ["engine/other.py:2 writes .hp"])

# ---- two reflectors against each other: Retribution struck by Spellmirror, and back; each rebound once, no recursion
game = simlib.campaign("hp_writes_505", cls="warrior", seed=5, location="south_fields")
world = game.scene.world
char, _ = simlib.make_character("mage", random.Random(2))
me = combat.fighter_from_character(char)
me.legendary["spellmirror"] = 50
me.mech_names["spellmirror"] = "Spellmirror"
foe = combat.fighter_from_creature(world.bestiary["bandit"], 5, "normal", "e1", "bandit")
foe.legendary["retribution"] = 50
foe.mech_names["retribution"] = "Retribution"
f = combat.Combat(fighters=[me, foe], place="the test ground", record=True, serial="t505")
combat.ensure_field(f)
me.hp = me.max_hp = 200.0
foe.hp = foe.max_hp = 200.0
hp0 = (me.hp, foe.hp)
dealt = combat.take_damage(f, foe, 40, me, random.Random(3), "magical")
back = [l for l in f.log if "Retribution returns" in l]
check("a magical blow on a Retribution fighter rebounds once onto the striker, written once", dealt == 40 and len(back) == 1 and me.hp == hp0[0] - 20
      and not any("Spellmirror returns" in l for l in f.log), (dealt, f.log, me.hp))
dealt2 = combat.take_damage(f, me, 40, foe, random.Random(3), "magical")
mirror = [l for l in f.log if "Spellmirror returns" in l]
check("...and a blow back on the Spellmirror fighter rebounds once the other way: no second rebound, no recursion",
      dealt2 == 40 and len(mirror) == 1 and len([l for l in f.log if "Retribution returns" in l]) == 1 and foe.hp == hp0[1] - 40 - 20, (dealt2, f.log, foe.hp))
game.close()
import shutil
shutil.rmtree("saves/hp_writes_505", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
