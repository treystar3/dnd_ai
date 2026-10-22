"""How differently the world moves on two seeds (f331): the same town, the same days, no player action - what situations start, what
they do, and how much of it the two campaigns share. A yardstick for "no two runs the same", run without a model (the stand-in answers
the few calls the rare tiers make; the ordinary tiers are the engine's own).

  python tools/world_divergence.py                 seeds 1 and 2, 60 days from Parth
  python tools/world_divergence.py --seeds 3 7 --days 120 --town greyhollow
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import simlib  # noqa: E402
from engine import clock, pulse  # noqa: E402
from npc.life import populate_place  # noqa: E402
from npc.traits import load_traits  # noqa: E402
from storage.campaign import SAVES_DIR, CampaignStore  # noqa: E402
from world.loader import load_world  # noqa: E402


def run(world, catalog, seed: int, town: str, days: int) -> dict:
    name = f"divergence_{seed}"
    shutil.rmtree(SAVES_DIR / name, ignore_errors=True)
    store = CampaignStore.open_or_create(name)
    store.meta.seed = seed
    store.save_meta()
    simlib.install(simlib.Stub("warrior", seed))
    populate_place(store, world, town, catalog)
    start = 5 * 1440
    store.save_world_state(pulse.empty_state(start))
    pulse.P["max_new_events_per_action"] = 10 ** 6                    # nothing is compressed: every pulse of every day runs
    for d in range(1, days + 1):
        pulse.catch_up(store, world, catalog, start + d * 1440)
    st = store.load_world_state()
    out = {"threads": [(t["title"], t["place"], t["tier"], t.get("made_by", "model"), t["status"]) for t in st["threads"]],
           "effects": sorted((e["kind"], e["place"], e["value"]) for e in st["effects"]),
           "news": len(st["news"]), "history": len(st["history"]),
           "moods": sorted((r.id, r.mood) for r in store.npc_rows(gone=False) if r.mood),
           "moved": sorted(r.id for r in store.npc_rows(gone=False) if r.location != town and r.location not in
                           {p for p in world.places if pulse.town_of(world, p) == town})}
    shutil.rmtree(SAVES_DIR / name, ignore_errors=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", nargs=2, type=int, default=[1, 2])
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--town", default="parth")
    a = ap.parse_args()
    world = load_world()
    catalog = load_traits()
    runs = [run(world, catalog, s, a.town, a.days) for s in a.seeds]
    for s, r in zip(a.seeds, runs):
        made = sum(1 for t in r["threads"] if t[3] == "engine")
        print(f"\n== seed {s}: {len(r['threads'])} situations over {a.days} days ({made} engine-built), {r['news']} pieces of news, "
              f"{len(r['effects'])} effects live, {len(r['moods'])} moods, {len(r['moved'])} people moved")
        for title, place, tier, by, status in r["threads"][-12:]:
            print(f"   [{tier}{'/engine' if by == 'engine' else ''}] {title} at {world.places[place].name if place in world.places else place} - {status}")
    a_, b_ = runs
    shared_titles = {t[0] for t in a_["threads"]} & {t[0] for t in b_["threads"]}
    shared_fx = set(a_["effects"]) & set(b_["effects"])
    total = max(1, len(a_["threads"]) + len(b_["threads"]))
    print(f"\nshared between the two seeds: {len(shared_titles)} situation titles of {len({t[0] for t in a_['threads']} | {t[0] for t in b_['threads']})}, "
          f"{len(shared_fx)} live effects of {len(set(a_['effects']) | set(b_['effects']))}; "
          f"divergence {100 - round(200 * len(shared_titles) / total)}% by situation")


if __name__ == "__main__":
    main()
