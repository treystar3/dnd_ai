"""An NPC only counts as leaving if the speech itself says goodbye or dismisses the player."""
import sys
sys.path.insert(0, ".")
from npc.life import has_parting
bad = []
def check(n, ok):
    print(("ok   " if ok else "FAIL ") + n)
    if not ok: bad.append(n)
for s in ["Aye. You're a long way from the main road, aren't you? Best stay on the path if you're just passing through.",
          "Names are a fickle thing to catch in the wind. You'll have to ask her yourself if you're looking to know.",
          "Orenna? No, I ain't never heard of a goddess by that name. We mostly look to the Sun Warden 'round these parts."]:
    check("not a goodbye: " + s[:30], not has_parting(s))
for s in ["I've work to do. Good day.", "Now leave me be.", "Farewell, traveller.", "Safe travels, friend.", "Enough of this talk.",
          "If you'll excuse me, the seed won't sow itself.", "Get out of my sight.", "I must be going."]:
    check("goodbye: " + s[:30], has_parting(s))
print("FAILED: " + ", ".join(bad) if bad else "all ok"); sys.exit(1 if bad else 0)
