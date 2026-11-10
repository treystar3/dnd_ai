"""(f558) Faster loading changes nothing the game reads: core/yamlio gives the same documents as PyYAML's SafeLoader for every data
file, the map's layout is the same whether it is computed or served from the memo, every world gets its own copy, and the memo keeps
at most LAYOUT_MEMO_MAX maps, dropping the least recently used."""
import pathlib, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 58))
import yaml
from core import yamlio
from engine import mapview
from world.campaign import CampaignWorld
from world.loader import authored

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the loaders agree on every data file
files = sorted(p for p in pathlib.Path("data").rglob("*") if p.suffix in (".yaml", ".yml") and p.is_file())
differ = [p.as_posix() for p in files
          if yaml.load(p.read_text(encoding="utf-8"), Loader=yaml.SafeLoader) != yamlio.safe_load(p.read_text(encoding="utf-8"))]
print(f"     loader: {yamlio._Loader.__name__}, {len(files)} files")
check("yamlio reads every data file to the same documents as SafeLoader", len(files) > 100 and not differ, differ[:5])
check("...and it is a safe loader", yamlio._Loader in (getattr(yaml, "CSafeLoader", None), yaml.SafeLoader))

# ---- the layout is the same computed or from the memo, and each world has its own
written = authored()
mapview._LAYOUT_MEMO.clear()
w1 = CampaignWorld(written)
computed = mapview.layout(w1)
check("a computed layout is remembered", len(mapview._LAYOUT_MEMO) == 1)
w2 = CampaignWorld(written)
served = mapview.layout(w2)
keep, mapview.LAYOUT_MEMO_MAX = mapview.LAYOUT_MEMO_MAX, 0
mapview._LAYOUT_MEMO.clear()
w3 = CampaignWorld(written)
fresh = mapview.layout(w3)
mapview.LAYOUT_MEMO_MAX = keep
check("the layout is the same computed, served from the memo, and with no memo at all", computed == served == fresh and len(computed) > 10,
      (len(computed), len(served), len(fresh)))
check("...with nothing kept when the memo holds nothing", not mapview._LAYOUT_MEMO)
check("every world has its own dict", computed is not served and served is not fresh and computed is not fresh)
some = next(iter(served))
served[some] = (-1.0, -1.0)
check("...so changing one world's layout changes no other's", computed[some] != (-1.0, -1.0) and fresh[some] != (-1.0, -1.0))

# ---- the cap holds, and a map in use is the last dropped
mapview._LAYOUT_MEMO.clear()
mapview.layout(CampaignWorld(written))
real = next(iter(mapview._LAYOUT_MEMO))
for n in range(mapview.LAYOUT_MEMO_MAX - 1):
    mapview._remember(("fake", n), {"x": (0.0, 0.0)})
check("the memo fills to its cap", len(mapview._LAYOUT_MEMO) == mapview.LAYOUT_MEMO_MAX == 8, len(mapview._LAYOUT_MEMO))
mapview.layout(CampaignWorld(written))                                # a hit: the real map becomes the most recent
mapview._remember(("fake", "one more"), {"x": (0.0, 0.0)})
check("past the cap the least recently used is dropped, not the map just used",
      len(mapview._LAYOUT_MEMO) == 8 and real in mapview._LAYOUT_MEMO and ("fake", 0) not in mapview._LAYOUT_MEMO, list(mapview._LAYOUT_MEMO)[:3])
for n in range(30):
    mapview._remember(("more", n), {"x": (0.0, 0.0)})
check("...and it never grows past the cap", len(mapview._LAYOUT_MEMO) == 8 and ("more", 29) in mapview._LAYOUT_MEMO, len(mapview._LAYOUT_MEMO))
mapview._LAYOUT_MEMO.clear()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
