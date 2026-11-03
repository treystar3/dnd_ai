"""(f483, Bundle D G5) Who someone is changes in one place. revise() is the only way a trait changes (and the way a profile or a hire's
identity will): it keeps how they first looked (first_description), records the change in trait_history (capped in data) and leaves them
a revision row, a line of how they changed and why, so a person who is braver than they were knows what made them so."""
from __future__ import annotations


def _cap() -> int:
    from engine import memory
    return int(((memory.caps().get("identity") or {}).get("trait_history")) or 8)


def revise(npc, catalog, remove: str, add: str, cause: str, t: int) -> None:
    """One trait for another, for a cause (npc/traits.py change_trait's checks), kept as a revision of who they are."""
    from engine import clock, memory
    from npc.traits import change_trait
    if not npc.first_description and npc.description:
        npc.first_description = npc.description
    change_trait(npc, catalog, remove, add, cause, clock.day(t))
    npc.trait_history = npc.trait_history[-_cap():]
    said = lambda tid: catalog.traits[tid].said if tid in catalog.traits else tid.replace("_", " ")     # in their words, not the id
    memory.keep(npc, f"I am less {said(remove)} than I was, and more {said(add)}: {cause.strip().rstrip('.')}.", day=clock.day(t), turn=-1,
                kind="revision", subject="", importance=2, about=f"trait:{remove}>{add}", minute=int(t))
