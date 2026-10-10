"""A companion who goes down sits out; beasts may die, spirits disperse and come back."""
import random, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from core.models import Companion
from scenes.combat_scene import CombatScene
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

def rig(comps, minutes=1000, seed=1):
    saved = []
    char = types.SimpleNamespace(companions=comps)
    ws = types.SimpleNamespace(player=types.SimpleNamespace(character=char), minutes=minutes,
                               world=types.SimpleNamespace(bestiary={"wolf": object()}),
                               store=types.SimpleNamespace(save_player=lambda p: saved.append(1)))
    sc = CombatScene.__new__(CombatScene)
    sc.ws, sc.rng = ws, random.Random(seed)
    return sc, ws

spirit = Companion(id="s1", name="Bone Warden", kind="undead", role="guardian", source="Skeletal Sentry")
wolf = Companion(id="w1", name="Grey", creature="wolf", kind="beast", role="striker")
sc, ws = rig([spirit, wolf])
check("fresh companions are active", spirit.active and wolf.active)
sc.companions_after_fight({"ally_s1"})
check("a downed spirit is fallen, never dead", spirit.fallen and not spirit.dead and spirit.recover_at == 1000 + 24 * 60)
check("the other companion is untouched", wolf.active)
deaths = 0
for seed in range(200):
    w = Companion(id="w", name="Grey", creature="wolf", kind="beast", role="striker")
    sc, ws = rig([w], seed=seed)
    sc.companions_after_fight({"ally_w"})
    deaths += w.dead
    assert w.fallen
check("about half of downed beasts die", 70 <= deaths <= 130, str(deaths))
w = Companion(id="w", name="Grey", creature="wolf", kind="beast", role="striker", fallen=True, dead=True)
sc, ws = rig([w]); sc.companions_after_fight({"ally_w"})
check("a dead companion is not processed again", w.dead and w.recover_at == 0)
print("ALL PASS" if not bad else f"FAILED: {bad}")
sys.exit(1 if bad else 0)
