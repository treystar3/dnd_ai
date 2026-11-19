"""(f706) What an act uses comes from somewhere: a catalogued good is carried, a trifle is found here (found in the second blind
play: docs/play/2026-11-16_blind_play_journal.md). "I ... rub charcoal over it to copy the markings." was ruled a plain yes with no
charcoal anywhere: it simply appeared. The owner kept decision Q34 ("catalogued goods must be carried and trifles can be supplied by
the place", 2026-11-16) and asked that what is supplied come from somewhere real.
Held here: a need the ruling names that is one of the catalogued goods (data/world/goods.yaml: rope, a torch) is refused when the
character carries none and none lies here, never conjured (told.yaml lacks_good); held, the act goes on and nothing is made; a trifle
the ruling names is made real lying here, and the passage is told where it came from; the ruling is asked to name such trifles, with
where they come from, and never a catalogued good.
Run: python tools/sim/carried_706_test.py"""
import shutil
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
import ui.console as uc
LINES = []
uc.put("note", lambda m, *a, **k: LINES.append(str(m)))
from engine import act, inventory as inv, objects, pulse

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("carried_706", seed=3, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})
TOLD = []
ws.narrate = lambda event, text="": TOLD.append(event)
c = ws.player.character
c.inventory = [i for i in c.inventory if i.good not in ("rope", "torch")]


def attempt(text, needs):
    stub.act_ruling = {"sense": "yes", "why": "simple", "uses": [], "requires": [], "changes": [], "fail": "noticed",
                       "works": "It is done.", "needs": needs}
    LINES.clear(); TOLD.clear()
    with ws.operation("action:other", text):
        ws.on_other(types.SimpleNamespace(kind="other", summary=text.rstrip(".")), text)
    return " | ".join(LINES), " ".join(TOLD)


ROPE = [{"kind": "thing", "name": "rope", "what": "a coil of rope", "where": "in your hands"}]
said, told = attempt("I lash the crates together and haul them up the wall.", ROPE)
here = [o.name for o in objects.here(store, ws.player.location, ws.minutes)]
check("a catalogued good the character does not carry is refused, never conjured", "rope" in said.lower() and not any("rope" in n for n in here), (said, here))
c.inventory.append(inv.make_good("rope", 1))
said, told = attempt("I lash the barrels together and haul them up the steps.", ROPE)
here = [o.name for o in objects.here(store, ws.player.location, ws.minutes)]
check("...carried, the act goes on and no second rope is made", "no rope" not in said.lower() and not any("rope" in n for n in here) and told, (said, here))
COAL = [{"kind": "thing", "name": "charcoal", "what": "a charred stick", "where": "from the cold brazier by the well"}]
said, told = attempt("I rub charcoal over the carving to copy the markings.", COAL)
here = [o.name for o in objects.here(store, ws.player.location, ws.minutes)]
check("a trifle the ruling names is made real lying here", any("charcoal" in n for n in here), here)
check("...and the passage is told where it came from", "cold brazier by the well" in told, told[-400:])
CLOTH = [{"kind": "thing", "name": "a scrap of cloth", "what": "a torn strip", "where": "from your sleeve"}]
said, told = attempt("I bind the cut with a scrap of cloth.", CLOTH)
check("a trade good's name in a trifle ('a scrap of cloth') refuses nothing: only the carried kit (act.yaml carried_goods) must be held",
      "no cloth" not in said.lower() and "carry none" not in said.lower() and told, said)
c.inventory = [i for i in c.inventory if i.good != "rope"]
BELL = [{"kind": "thing", "name": "the bell rope", "what": "the bell's pull rope", "where": "hanging from the belfry"}]
said, told = attempt("I haul on the bell rope to ring the alarm.", BELL)
check("a thing of the place that only shares a good's word ('the bell rope') is no rope from the pack: nothing refused",
      "no rope" not in said.lower() and "carry none" not in said.lower() and told, said)
SPARE = [{"kind": "thing", "name": "a coil of rope", "what": "rope", "where": "in your pack"}]
said, told = attempt("I tie a coil of rope to the railing and climb down.", SPARE)
check("...while 'a coil of rope' is the rope the pack does not hold: refused", "rope" in said.lower() and not told, said)
check("the act's data checks clean", act.problems() == [], act.problems())
check("the ruling is asked to name a trifle the act uses, with where it comes from, and never a catalogued good",
      "KIT (rope, torch" in act.SYSTEM and "where it comes from" in act.SYSTEM and "<KIT>" not in act.SYSTEM,
      act.SYSTEM[act.SYSTEM.find("needs:"):][:600])
g.close()
shutil.rmtree("saves/carried_706", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
