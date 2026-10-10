"""Check the authored world files and try out NPC traits.

Usage:
    python world_check.py            validate the world, show a summary, meet a test NPC
    python world_check.py --change   also change one of the test NPC's traits (with a cause)

Run it twice: the test NPC keeps the same traits, because they are rolled once and saved.
Delete saves/world_check/ to meet a fresh NPC.
"""

import sys

from npc.models import NPC
from npc.traits import assign_traits, change_trait, load_traits, npc_rng
from storage.campaign import CampaignStore
from world.loader import WorldError, load_world


def main():
    try:
        world = load_world()
    except WorldError as e:
        print(e)
        sys.exit(1)
    catalog = load_traits()

    print(f"World: {world.name}  (start: {world.places[world.start_location].name})")
    print(f"  {len(world.regions)} regions, {len(world.places)} places, {len(world.peoples)} peoples, "
          f"{len(world.lore)} facts, {len(world.pressures)} pressures, {len(catalog.traits)} traits")

    print("\nA shepherd from Parth would know:")
    for fact in world.facts_known_by({"everyone", "parth_locals", "shepherds"}):
        print(f"  - {fact.text.strip()}")

    print("\nVisible in the trading square:")
    for line in world.places["trading_square"].visible:
        print(f"  - {line}")

    store = CampaignStore.open_or_create("world_check")
    npc_id = "test_innkeeper"
    if store.npc_exists(npc_id):
        npc = store.load_npc(npc_id)
        print(f"\nMet {npc.name} before. Traits are unchanged:")
    else:
        npc = NPC(id=npc_id, name="the innkeeper", people="human", role="innkeeper",
                  location="tilted_plough", tier="known")
        assign_traits(npc, catalog, npc_rng(store.meta.seed, npc.id))
        store.save_npc(npc)
        print(f"\nMeeting {npc.name} for the first time. Rolled traits:")
    for line in catalog.describe(npc.traits):
        print(f"  - {line}")

    if "--change" in sys.argv:
        old = npc.traits[0]
        replacement = next(t for t in catalog.traits if catalog.fits(t, npc.traits[1:]) and t != old)
        change_trait(npc, catalog, old, replacement, "Test: a hard winter changed them.", store.meta.day)
        store.save_npc(npc)
        print(f"\nChanged '{old}' to '{replacement}'. History:")
        for h in npc.trait_history:
            print(f"  - day {h.day}: {h.removed} -> {h.added} ({h.cause})")


if __name__ == "__main__":
    main()
