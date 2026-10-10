"""Guild contracts follow the place they send you to, not your rank: a high-rank member at an early hall sees little worth doing,
and better work means travelling to a better hall."""
import random, sys, re, types
sys.path.insert(0, ".")
from world.loader import load_world
from engine import quests, encounters
from engine.quests import G

world = load_world()
class Store:
    def __init__(self): self.meta = types.SimpleNamespace(seed="t", minutes=0); self.p = {}
    def load_place(self, pid): return self.p.setdefault(pid, types.SimpleNamespace(id=pid, roster=[], populated=False))
    def save_place(self, s): pass
    def load_dungeons(self): return []
    def load_arcs(self): return {"arcs": []}
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)
check("place_levels is on", G.get("place_levels") is True)
halls = [h for h in world.places if h.endswith("_guild")]
for rank in ("F", "B"):
    print(f"-- rank {rank}")
    for h in halls:
        st = Store(); rng = random.Random(h + rank)
        hunts = []
        for _ in range(40):
            for q in quests.post_board(world, st, 0, 6, rng, rank, h):
                if q["kind"] in ("hunt", "bounty"):
                    hunts.append(q)
        check_scale = all("scale" not in q for q in hunts)
        letters = sorted({q["letter"] for q in hunts})
        print(f"   {h:18} tier {quests.hall_tier(world, h)['tier']}  hunt/bounty letters {letters}")
        if not check_scale: bad.append(f"{h} scaled")
def low_share(rank, hall="eldervale_guild"):
    st = Store(); rng = random.Random(5); low = tot = 0
    for _ in range(200):
        for q in quests.post_board(world, st, 0, 6, rng, rank, hall):
            if q["kind"] in ("hunt", "bounty"):
                tot += 1; low += world.places[q["place"]].danger[1] < 30
    return low / max(1, tot), tot
f, fn = low_share("F"); b, bn = low_share("B")
print(f"   hunts in zones topping out under 30: rank F {f:.0%} of {fn}, rank B {b:.0%} of {bn}")
check("a rank-B member is mostly not offered starter-zone hunts", b < 0.35 and b < f, f"{b:.0%} vs {f:.0%}")
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)
