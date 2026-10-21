"""#shop shows wares only inside a place of business, and only from people you have met."""
import sys
sys.path.insert(0, ".")
from types import SimpleNamespace as NS
from world.loader import load_world
from scenes import inventory_actions as ia
from ui import console
w = load_world()
cls = next(c for n, c in vars(ia).items() if isinstance(c, type) and hasattr(c, "show_shop"))
bad = []
def check(n, ok):
    print(("ok   " if ok else "FAIL ") + n)
    if not ok: bad.append(n)
lines = []
console.note = lambda m: lines.append(m)
def scene(ptype, npcs):
    met = [n for n in npcs if n.met_player]      # shop_data lists only people you have met
    s = NS(place=NS(type=ptype), present=npcs, world=w, BUSINESS_PLACES=cls.BUSINESS_PLACES,
           shop_data=lambda: {"sellers": [{"name": n.label(), "wares": [], "buys": []} for n in met], "sell": [], "purse": ""},
           stable_stock=lambda: [], show_stable=lambda: lines.append("STABLE"),
           trades_here=lambda: ", ".join(f"{n.label()} (wares)" for n in npcs if not n.met_player))      # (f328) who sells here, unmet
    return s
merchant = NS(role="merchant", met_player=False, label=lambda: "Stranger")
lines.clear(); cls.show_shop(scene("temple", [merchant])); check("not in a business: nothing sold", len(lines) == 1 and "Nothing is sold" in lines[0])
lines.clear(); cls.show_shop(scene("town", [merchant])); check("town counts, unmet seller hidden but named", len(lines) == 1 and "Trading here: Stranger (wares)" in lines[0] and "Speak to them first" in lines[0])
lines.clear(); cls.show_shop(scene("shop", [merchant])); check("unmet seller hidden but named", len(lines) == 1 and "Trading here: Stranger (wares)" in lines[0])
for t in ("city", "guild", "temple"):
    lines.clear(); cls.show_shop(scene(t, [NS(role="merchant", met_player=True, label=lambda: "X")])); check(f"{t} is not a business", "Nothing is sold" in lines[0])
print("FAILED: " + ", ".join(bad) if bad else "all ok")
sys.exit(1 if bad else 0)
