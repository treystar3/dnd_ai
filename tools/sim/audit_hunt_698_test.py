"""(f698) The plan's audit lets an attack at a creature of this place go hunting (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). In the Willowmead wetlands, `I attack the will-o'-wisps.` was refused by the audit ("step
(attack) is aimed at 'will-o'-wisps', who is not here") and the player was asked "Do you mean to strike at the shadows, or something
else?". An attack at a creature of the place's roster goes looking for it (f449, f685): the audit knew only the people here and a
creature already in view.
Held here: the audit's situation knows the creatures this place holds (its roster, read, never written), and an attack or a fighting
ability aimed at one of them is no problem; one aimed at a creature the place does not hold, or at a person who is not here, still is.
Run: python tools/sim/audit_hunt_698_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 6))
simlib.quiet_console()
from engine import encounters, intent_audit as ia
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("audit_hunt_698", seed=5, location="greywood")
ws = g.scene
ws.enter("greywood")
check("(arriving builds no roster: the first attack is the case)", ws.store.load_place("greywood").roster == [], ws.store.load_place("greywood").roster)
roster = encounters.roster_of(ws.store, ws.world, "greywood")
lives = ws.world.bestiary[roster[0]].name.lower()
absent = next(c.name.lower() for k, c in ws.world.bestiary.items() if k not in roster and len(c.name) > 4 and " " not in c.name)
sit = ws.situation()
before = list(ws.store.load_place("greywood").roster)
check("the roster the audit reads is the one the place will keep", encounters.roster_of(ws.store, ws.world, "greywood") == roster)
check(f"an attack at a creature this place holds ('{lives}s') is no problem", ia.problems([A(kind="attack", target=f"{lives}s")], sit) == [],
      ia.problems([A(kind="attack", target=f"{lives}s")], sit))
hit = next(a.id for a in ws.player.character.actives if a.effect.value == "damage")
check("...nor a fighting ability at it", ia.problems([A(kind="ability", ability=hit, target=f"the {lives}")], sit) == [],
      ia.problems([A(kind="ability", ability=hit, target=f"the {lives}")], sit))
check(f"an attack at a creature the place does not hold ('{absent}') still is", ia.problems([A(kind="attack", target=absent)], sit) != [])
check("an attack at a person who is not here still is", ia.problems([A(kind="attack", target="the merchant")], sit) != [])
check("a talk to a creature of the place is still aimed at no one here", ia.problems([A(kind="talk", target=lives)], sit) != [])
check("the roster is read, never written", ws.store.load_place("greywood").roster == before)
check("...and ensure_roster then keeps the very same one", encounters.ensure_roster(ws.store, ws.world, "greywood") == roster
      and ws.store.load_place("greywood").roster == roster)
g.close()
shutil.rmtree("saves/audit_hunt_698", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
