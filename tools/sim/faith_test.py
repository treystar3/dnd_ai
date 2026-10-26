"""Which god each place follows, and the faith line in NPC prompts."""
import sys
sys.path.insert(0, ".")
from world.loader import load_world
from engine import faith
from types import SimpleNamespace as NS
w = load_world()
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)
S = faith.seat
for place, god in [("parth","lethoria"),("willowmead","lethoria"),("greyhollow","lethoria"),("redstone","lethoria"),
                   ("lethoria","lethoria"),("riverhaven","riverhaven"),("eldervale","eldervale"),("dunmarrow","dunmarrow"),
                   ("parth_temple","lethoria"),("riverhaven_temple","riverhaven"),("sunspire","sunspire"),("amaranth","amaranth")]:
    check(f"{place} follows {god}", S(w, place) == god, S(w, place))
for city in ("eldervale","ironvein","frostholm","riverhaven","sunspire","lethoria","cinderhold","hrimgard","dunmarrow","brinewatch","amaranth"):
    check("god for "+city, city in faith.GODS)
check("Morrowen is a cult, not a seat", "morrowen" in faith.GODS and "morrowen" not in [p.id for p in w.places.values()])
# no-ruler region falls back to nearest city
for pid, p in w.places.items():
    if not p.parent and p.type != "road":
        check("every top place has a god: "+pid, S(w, pid) in faith.GODS, S(w, pid)) if not S(w, pid) in faith.GODS else None
n = lambda role, loc: NS(role=role, location=loc)
pr = faith.line(w, n("priest", "parth_temple")); fm = faith.line(w, n("farmer", "parth")); gd = faith.line(w, n("guard", "lethoria"))
check("line names the god", "Aurelan" in pr and "Aurelan" in fm)
check("voice varies by role", pr != fm != gd and "devout" in pr and "brief" in gd and "ordinary talk" in fm)
check("tone notes are marked as not to be quoted", "not lines to quote" in fm)
check("river guard follows Teluun", "Teluun" in faith.line(w, n("guard", "riverhaven")))
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
