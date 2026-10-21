"""Is the campaign consistent as a game world, not only as a database? SQLite keeps rows whole; it does not know that a place's resident
must be a real person, that the player must stand somewhere that exists, or that a hire's opinions must be of someone. validate_campaign()
lists every such problem it can find and repairs nothing: detection is the point, and an ambiguous repair would hide the bug that caused it.

Used by the tests, the long-campaign fixture, after a migration, and the #check command."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Problem:
    where: str        # the record it is in: "place parth", "npc n12", "player", "world"
    what: str

    def __str__(self) -> str:
        return f"{self.where}: {self.what}"


def validate_campaign(store, world=None) -> list[Problem]:
    out: list[Problem] = []
    rows = store.npc_rows()
    ids = {r.id for r in rows}
    by_id = {r.id: r for r in rows}
    places = set(world.places) if world is not None else None
    place_ids = store.list_places()

    # ---- people
    seen_names = {}
    for r in rows:
        if not r.id or not r.id.strip():
            out.append(Problem("npc ?", "a person with no id"))
        if not r.name.strip() and not r.gone:
            out.append(Problem(f"npc {r.id}", "a person with no name"))
        if places is not None and r.location and r.location not in places and not r.gone:
            out.append(Problem(f"npc {r.id}", f"stands in '{r.location}', which is not a place of the world"))
        if r.name and not r.gone:
            seen_names.setdefault(r.name, []).append(r.id)
    # the same name on two living people is allowed (people share names); it is only noted when both are in the same place
    for name, who in seen_names.items():
        if len(who) > 1:
            spots = {by_id[i].location for i in who}
            if len(spots) < len(who):
                out.append(Problem("npcs " + ", ".join(who), f"two living people named '{name}' in the same place"))

    # ---- places
    for pid in place_ids:
        ps = store.load_place(pid)
        if places is not None and pid not in places:
            out.append(Problem(f"place {pid}", "a saved place that is not in the world"))
        for rid in ps.residents:
            if rid not in ids:
                out.append(Problem(f"place {pid}", f"resident '{rid}' is not a person in the save"))
            elif by_id[rid].location != pid and not by_id[rid].gone:
                out.append(Problem(f"place {pid}", f"lists {by_id[rid].name} ({rid}) as resident, but they stand in '{by_id[rid].location}'"))
        for rid in ps.roster:
            if rid not in ids:
                out.append(Problem(f"place {pid}", f"roster entry '{rid}' is not a person in the save"))

    # ---- the player
    if not store.player_exists():
        return out
    p = store.load_player()
    if places is not None and p.location not in places:
        out.append(Problem("player", f"stands in '{p.location}', which is not a place of the world"))
    member_ids = set()
    for m in p.party:
        mid = m.get("id")
        if not mid:
            out.append(Problem("player.party", f"a member with no id: {m.get('name', '?')}"))
            continue
        if mid in member_ids:
            out.append(Problem("player.party", f"member id '{mid}' appears twice"))
        member_ids.add(mid)
        if m.get("npc") and m["npc"] not in ids:
            out.append(Problem(f"party {mid}", f"stands in for npc '{m['npc']}', who is not in the save"))
        for x in m.get("opinions", []):
            aid = x.get("about_id", x.get("about", ""))
            if not aid:
                out.append(Problem(f"party {mid}", f"an opinion of nobody: '{x.get('text', '')[:60]}'"))
            elif aid not in ("player", "maren") and aid not in member_ids | ids and aid == x.get("about"):
                pass                                      # someone the game knows only by name (outside the party): allowed
    for key in p.party_relations:
        if "|" in key:
            a, b_ = key.split("|", 1)
            for x in (a, b_):
                if x not in member_ids and x not in p.party_used:
                    out.append(Problem("player.party_relations", f"'{key}' names '{x}', who is neither in the party nor among those who left"))
    if p.mount and p.mount not in {m.get("id") for m in p.mounts}:
        out.append(Problem("player", f"rides mount '{p.mount}', which they do not own"))
    for q in p.quests:
        if places is not None and q.get("place") and q["place"] not in places:
            out.append(Problem("player.quests", f"'{q.get('title', '?')}' points at place '{q['place']}', which is not in the world"))
        if q.get("npc") and q["npc"] not in ids:
            out.append(Problem("player.quests", f"'{q.get('title', '?')}' points at npc '{q['npc']}', who is not in the save"))
    for nid in p.prisoners:
        if nid not in ids:
            out.append(Problem("player.prisoners", f"captive '{nid}' is not a person in the save"))

    # ---- the world's own state
    st = store.load_world_state() or {}
    thread_ids = {t.get("id") for t in st.get("threads", [])}
    for s in st.get("spawns", []):
        if s.get("thread") and s["thread"] not in thread_ids:
            out.append(Problem("world.spawns", f"spawn '{s.get('id', '?')}' belongs to thread '{s['thread']}', which is gone"))
    if st.get("campaign") and st["campaign"] not in thread_ids:
        out.append(Problem("world", f"the running campaign '{st['campaign']}' is not among the threads"))
    for t in st.get("threads", []):
        if places is not None and t.get("place") not in places:
            out.append(Problem("world.threads", f"'{t.get('title', '?')}' is set in '{t.get('place')}', which is not a place of the world"))
    return out
