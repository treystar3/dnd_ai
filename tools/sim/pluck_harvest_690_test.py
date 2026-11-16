"""(f690) A part of a fresh kill, named in an improvised step, is the harvest (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). With a contract for griffon down and a griffon just killed, `I pluck the griffon's down
carefully.` was read once as an improvisation, refused ("it does not make sense here") and narrated beside the wrong carcass.
Held here: a step read as `other`, or a pick-up of nothing lying here, that names what a fresh carcass here yields (its materials
and goods, by the table's own names) is the harvest, once; with no carcass here, or a thing that does lie here, or a part of no
carcass here, the reading stands. Cases other than the one that found it: a boar's meat cut out, a wolf hide taken up.
Run: python tools/sim/pluck_harvest_690_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from engine import inventory as inv, items
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("pluck_harvest_690", seed=5, location="greywood")
ws = g.scene
ws.enter("greywood")
check("(the scene has the repair)", callable(getattr(ws, "carcass_part", None)))


def lay(*creatures, ground=()):
    st = ws.store.load_place(ws.player.location)
    st.carcasses = [{"creature": c, "level": 5, "minute": ws.minutes} for c in creatures]
    st.ground = []
    for gid in ground:
        inv.leave_on_ground(st, items.make_raw(gid), ws.minutes)
    ws.store.save_place(st)


def kinds(text, plan):
    return [a.kind for a in ws.repair(text, plan)]


def drop_of(creature):
    return next((m for m in items.MATERIALS.values() if creature in m.drops_from), None)


lay("griffon")
line = "I pluck the griffon's down carefully."
check("an improvised step naming a part of the fresh griffon is the harvest",
      kinds(line, [A(kind="other", summary="The player plucks the griffon's down carefully.")]) == ["harvest"])
check("...and is recorded under the rule's name", any(r["rule"] == "carcass_part" for r in ws.repairs), ws.repairs)
check("a pick-up of the down, none of it lying here, is the harvest too", kinds("I take the griffon down.", [A(kind="pick_up", item="griffon down")]) == ["harvest"])
check("a harvest already in the plan stays one harvest",
      kinds(line, [A(kind="harvest"), A(kind="other", summary="The player plucks the griffon's down.")]) == ["harvest"])
check("an improvised step beside it that names no part keeps its reading",
      kinds("I pluck the griffon's down and hum a tune.", [A(kind="other", summary="The player plucks the griffon's down."),
                                                           A(kind="other", summary="The player hums a tune.")]) == ["harvest", "other"])

boar = "boar" if "boar" in ws.world.bestiary else None
meat = next((gd for gd in inv.GOODS.values() if boar and boar in gd.drops_from), None)
if meat:
    lay(boar)
    check(f"another kill, another part: cutting the {meat.name} from the boar is the harvest",
          kinds(f"I cut the {meat.name} from the boar.", [A(kind="other", summary=f"The player cuts the {meat.name} from the boar.")]) == ["harvest"], meat.name)
wolf = drop_of("wolf")
if wolf:
    lay("wolf")
    check(f"a {wolf.name} taken up from a wolf just killed is the harvest", kinds(f"I take the {wolf.name}.", [A(kind="pick_up", item=wolf.name)]) == ["harvest"])
    lay("wolf", ground=[wolf.id])
    check(f"...but a {wolf.name} lying here is picked up", kinds(f"I take the {wolf.name}.", [A(kind="pick_up", item=wolf.name)]) == ["pick_up"])

    check("a word of a part's name used as a word of its own names no part: hiding behind the dead wolf",
          kinds("I hide behind the dead wolf.", [A(kind="other", summary="The player hides behind the dead wolf.")]) == ["other"])
    check("a step that says nothing of its own is not given the whole line's words beside another",
          kinds(f"I skin the {wolf.name}, then dance a jig.", [A(kind="harvest"), A(kind="other")]) == ["harvest", "other"])
lay("griffon")
check("...and kneeling down beside the griffon", kinds("I kneel down beside the griffon.", [A(kind="other", summary="The player kneels down beside the griffon.")]) == ["other"])

lay()
check("with no carcass here the improvisation stands", kinds(line, [A(kind="other", summary="The player plucks the griffon's down.")]) == ["other"])
lay("wolf")
check("a part of no carcass here is no harvest", kinds(line, [A(kind="other", summary="The player plucks the griffon's down.")]) == ["other"])
check("an improvised step that names no part stays one", kinds("I sit down by the wolf.", [A(kind="other", summary="The player sits down by the wolf.")]) == ["other"])
st = ws.store.load_place(ws.player.location)
st.carcasses = [{"creature": "griffon", "level": 5, "minute": ws.minutes - 10**6}]
ws.store.save_place(st)
check("a carcass gone stale yields nothing to name", kinds(line, [A(kind="other", summary="The player plucks the griffon's down.")]) == ["other"])

import shutil; shutil.rmtree("saves/pluck_harvest_690", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
