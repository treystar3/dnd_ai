"""(f419) Small things the f395 night's fight pages got wrong. A marker the narrator wrapped in a parenthesis ('([h3])', '(#h4)') left '()'
on the screen; every ally struck 'with its sword'; the leech line told '12 health flows back'; a lightning mage's gear 'burns'; a spell
was followed by 'the blow'; enemy rows read 'river pirate 2 cutlasss', 'griffon beaks' and 'claw (fiend form only)s'; 'is not spent' and
'(on the wolf)' reached the page; and the passage after a fight could name someone the player was never told."""
import random, re, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 9))
from engine import combat, names
from scenes import combat_prompts as cp
from scenes.combat_scene import TAG, TAG_N, place_figures, tag_number
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()

# ---- markers in any wrapping are taken whole
for raw in ("The wolf falls ([h3]).", "It bites (#h3) hard.", "It bites (h3).", "It bites [h3]."):
    m = next(TAG_N.finditer(raw), None)
    check(f"the marker in {raw!r} is read whole", m is not None and tag_number(m) == 3 and "(" not in TAG.sub("", raw).replace("(h", ""), TAG.sub("", raw))
out = place_figures("The wolf lunges and falls ([h1]).", [{"id": "x", "tag": "h1", "figure": "(12 damage)"}], False, ["the wolf lunges [h1]"])
check("...and its figure takes its place with no '()' left", out == "The wolf lunges and falls (12 damage).", out)
check("the narrator is shown the plain form, not a wrapped one", "([h2])" not in cp.NARRATE_SYSTEM and "[h2]" in cp.NARRATE_SYSTEM)

# ---- whose weapon
wolf = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "e1", name="wolf 1")
odly = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "ally_h1", name="Odly Garth")
odly.side, odly.ally_role, odly.weapon_name = "ally", "fighter", "longsword"
names.set_cast({"Odly": "she"})
check("a companion strikes with her own weapon, not 'its'", combat.weapon_phrase(odly) == "with her longsword", combat.weapon_phrase(odly))
check("...a beast with its own", combat.weapon_phrase(wolf).startswith("with its "), combat.weapon_phrase(wolf))
bandit = combat.fighter_from_creature(world.bestiary["bandit"], 3, "normal", "e2", name="bandit 1")
check("...and a person whose pronoun the fight does not know, with theirs", combat.weapon_phrase(bandit).startswith("with their "), combat.weapon_phrase(bandit))

# ---- the rows and lines
noted = [c for c in world.bestiary.values() if any("(" in a for a in c.attacks)]
if noted:
    f = combat.fighter_from_creature(noted[0], 3, "normal", "e3")
    check("an attack's stage note is not part of the weapon", "(" not in f.weapon_name, f.weapon_name)
src = open("engine/combat.py", encoding="utf-8").read()
check("enemy rows read 'attacks (bite)', never a noun made a verb", 'f"{e.weapon_name}s"' not in src and src.count('f"attacks ({e.weapon_name})"') == 2)
check("gear damage of any element is never said to burn", "damage burns" not in src and "weapon burns" not in src)
check("the leech line names no figure and no 'health'", "health flows back" not in src)
check("what an ability that was kept is stays in the log, not the story", "is not spent" not in src)

check("gear damage after a spell follows the spell, not 'the blow'", "follows the {'spell' if att.spell_kind == 'spell' else 'blow'}" in src)

# ---- the ground: who is fighting whom
bsrc = open("engine/battlefield.py", encoding="utf-8").read()
check("the ground says '(fighting X)', not '(on X)'", "(fighting {tied[0]})" in bsrc and "(on {tied[0]})" not in bsrc)
csrc = open("scenes/combat_scene.py", encoding="utf-8").read()
check("the passage after a fight hides names the player was never told", "after_text = self.ws.unnamed(aftermath.text)" in csrc)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
