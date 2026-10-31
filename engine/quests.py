"""Guild contracts and personal requests. The engine owns every quest: what it asks, its letter, its reward.

A quest is a plain dict so it saves simply:
  id, title, kind (hunt|bounty|gather|materials|deliver), letter, guild (bool), issuer, issuer_name,
  place, creature, good, material, count, progress, to_role, to_name, item, deadline, coins, xp, posted
"""

import random
import uuid
from pathlib import Path

import yaml

from engine import encounters, inventory as inv, items

ROOT = Path(__file__).resolve().parent.parent
G = yaml.safe_load((ROOT / "data" / "rules" / "guild.yaml").read_text(encoding="utf-8"))
LETTERS = list(G["ranks"])


def letter_for_level(level: int) -> str:
    for letter in LETTERS:
        lo, hi = G["ranks"][letter]["levels"]
        if level < hi or letter == LETTERS[-1]:
            return letter
    return LETTERS[-1]


def at_or_below(letter: str, rank: str) -> bool:
    return LETTERS.index(letter) <= LETTERS.index(rank)


def perks(rank: str) -> dict:
    """Every perk from F up to this rank, added together."""
    total = {"board": 0, "active": 0, "room_discount": 0, "shop_discount": 0, "reward_bonus": 0, "storage": False}
    if not rank:
        return total
    for letter in LETTERS[:LETTERS.index(rank) + 1]:
        for k, v in G["ranks"][letter]["perks"].items():
            total[k] = (total[k] or v) if isinstance(v, bool) else total[k] + v
    return total


def describe_perks(letter: str) -> str:
    names = {"board": "+{} board postings", "active": "+{} contract at once", "room_discount": "{}% off inn rooms",
             "shop_discount": "{}% off at shops", "reward_bonus": "{}% bigger contract rewards",
             "storage": "your item box at guild houses"}
    return ", ".join(names[k].format(v) for k, v in G["ranks"][letter]["perks"].items()) or "none"


def next_rank(rank: str) -> str | None:
    i = LETTERS.index(rank)
    return LETTERS[i + 1] if i + 1 < len(LETTERS) else None


def promotion_due(rank: str, level: int, done: dict[str, int], discount: int = 0) -> str | None:
    """The rank this member has earned, if they qualify for the next one."""
    nxt = next_rank(rank)
    if not nxt:
        return None
    need = G["ranks"][nxt]["requires"]
    counted = sum(n for letter, n in done.items() if LETTERS.index(letter) >= LETTERS.index(rank))
    return nxt if level >= need["level"] and counted >= need["completed"] - discount else None


def reward(letter: str, guild: bool, bonus: float = 0) -> tuple[int, int]:
    r = G["ranks"][letter]["reward"]
    share = 1.0 if guild else G["personal_share"]
    return round(r["coins"] * share * (1 + bonus / 100)), round(r["xp"] * share * (1 + bonus / 100))


def plural(name: str) -> str:
    n = name.lower()
    if n.endswith("f"):
        return n[:-1] + "ves"
    if n.endswith("fe"):
        return n[:-2] + "ves"
    if n.endswith("y") and n[-2:-1] not in "aeiou":
        return n[:-1] + "ies"
    if n.endswith(("s", "sh", "ch", "x")):
        return n + "es" if not n.endswith("s") else n
    return n + "s"


def _quest(kind: str, letter: str, title: str, now: int, guild: bool = True, **fields) -> dict:
    coins, xp = reward(letter, guild)
    q = {"id": uuid.uuid4().hex[:8], "title": title, "kind": kind, "letter": letter, "guild": guild,
         "issuer": "guild", "issuer_name": "the guild", "count": 1, "progress": 0, "coins": coins, "xp": xp,
         "deadline": now + G["ranks"][letter]["deadline_days"] * 1440, "posted": now}
    if kind == "missing":
        q["deadline"] = None             # a search has no clock; it may grow into a story, and stories wait
    q.update(fields)
    return q


def _overlap(creature, place) -> tuple[int, int]:
    lo, hi = max(place.danger[0], creature.levels[0]), min(place.danger[1], creature.levels[1])
    return (lo, hi) if lo <= hi else (creature.levels[0], creature.levels[0])


def hall_wilds(world, hall: str | None) -> list:
    """Wild places a guild hall posts work for: those within a day's walk, or failing that the nearest few."""
    wild = [p for p in world.places.values() if p.danger and p.type != "road"]
    if not hall or hall not in world.places:
        return wild
    reach = G.get("hall_reach_minutes", 1440)
    far_lands = set(G.get("far_lands", []))
    if far_lands and world.places[hall].region not in far_lands:
        wild = [p for p in wild if p.region not in far_lands]   # a home-lands hall never counts the far lands as its own country
    timed = []
    for p in wild:
        r = world.path(hall, p.id)
        if r:
            timed.append((r[1], p))
    timed.sort(key=lambda t: t[0])
    near = [p for m, p in timed if m <= reach]
    return near if len(near) >= 3 else [p for _, p in timed[:max(3, len(near))]]


def hall_tier(world, hall: str | None) -> dict:
    """The great-hall bonuses a hall has earned (size, reward_mult, kinds, far reach), or the plain defaults."""
    plain = {"tier": 0, "size": 0, "reward_mult": 1.0, "kinds": None, "far_reach_minutes": 0}
    if not hall or hall not in world.places:
        return plain
    town = world.places[_town(world, hall)]
    ignore = set(G.get("tier_ignore", []))
    danger = max([p.danger[1] for p in hall_wilds(world, hall) if p.id not in ignore] + [town.trade_level[1]])
    best = plain
    for i, t in enumerate(G.get("hall_tiers", []), 1):
        if danger >= t["min_danger"]:
            best = {**plain, **t, "tier": i}
    return best


def post_board(world, store, now: int, size: int, rng: random.Random, rank: str = "F", hall: str | None = None,
               existing: list | None = None) -> list[dict]:
    """Postings mostly at or near the member's rank; now and then one far above, as a glimpse of what's out there.
    Work is posted for the places around the hall that holds the board."""
    wild = hall_wilds(world, hall)
    tier = hall_tier(world, hall)
    near_ids = {p.id for p in wild}
    far = {}
    if tier["far_reach_minutes"]:
        for p in world.places.values():
            if p.danger and p.type != "road" and p.id not in near_ids and p.danger[1] >= tier["far_min_danger"]:
                r = world.path(hall, p.id)
                if r and r[1] <= tier["far_reach_minutes"]:
                    far[p.id] = -(-r[1] // 1440)
        wild = wild + [world.places[i] for i in far]
    wild_ids = {p.id for p in wild}
    kinds = tier["kinds"] or G["kinds"]
    town = _town(world, hall) if hall else None
    makers = {"hunt": _hunt, "bounty": _bounty, "gather": _gather, "materials": _materials, "deliver": _deliver,
              "delve": _delve, "dungeon_boss": _dungeon_boss, "missing": _missing}
    reach = LETTERS.index(rank or "F") + 1
    board, tries, glimpse = list(existing or []), 0, 0
    while len(board) < size and tries < size * 15:
        tries += 1
        kind = rng.choices(list(kinds), weights=list(kinds.values()))[0]
        if kind in ("deliver", "delve", "dungeon_boss", "missing"):
            q = makers[kind](world, store, wild, now, rng, hall)
        elif kind in ("hunt", "bounty"):
            q = makers[kind](world, store, wild, now, rng, None if G.get("place_levels") else (rank or "F"))
        else:
            q = makers[kind](world, store, wild, now, rng)
        if not q:
            continue
        d = None
        if kind in ("delve", "dungeon_boss"):
            d = next((x for x in store.load_dungeons() if x["id"] == q.get("dungeon")), None)
            if hall and (not d or d["place"] not in wild_ids):
                continue
        key = (q["kind"], q.get("creature"), q.get("good"), q.get("material"), q.get("item"))
        if any((b["kind"], b.get("creature"), b.get("good"), b.get("material"), b.get("item")) == key for b in board):
            continue
        li = LETTERS.index(q["letter"])
        if li > reach:
            if glimpse or rng.random() > 0.15:
                continue
            glimpse += 1
        elif li > reach - 1 and sum(reach - 1 < LETTERS.index(b["letter"]) <= reach for b in board) >= G.get("above_max", size):
            continue                                          # (f292) work a rank above yours is a couple of postings, not half the board
        elif li < LETTERS.index(rank or "F") - G["rank_focus"]["below"] and rng.random() > G["rank_focus"]["keep"]:
            continue
        spot = q.get("place") or (d["place"] if kind in ("delve", "dungeon_boss") and d else None)
        if spot in far:
            q["extra_days"] = far[spot]
            q["title"] += f" (expedition, {far[spot]} days out)"
        if tier["reward_mult"] != 1.0:
            q["multiplier"] = round(q.get("multiplier", 1) * tier["reward_mult"], 3)
            q["hall"] = hall
        board.append(q)
    return sorted(board, key=lambda q: LETTERS.index(q["letter"]))


def scaled_work(rank: str, rng: random.Random) -> tuple[str, int]:
    """The letter and creature level of a hunt or bounty posted for a member of this rank: mostly their own rank, now and then
    one above or below. The fight itself is raised to that level when the member goes after it (encounters.roll)."""
    S = G["scaled"]
    i = LETTERS.index(rank or "F")
    r = rng.random()
    if r < S["above"] and i + 1 < len(LETTERS):
        i += 1
    elif r < S["above"] + S["below"] and i > 0:
        i -= 1
    letter = LETTERS[i]
    lo, hi = G["ranks"][letter]["levels"]
    hi = min(hi, lo + S["top_span"])
    return letter, max(1, round(lo + (hi - lo) * rng.uniform(*S["level_span"])))


def _hunt(world, store, wild, now, rng, rank=None):
    place = rng.choice(wild)
    roster = encounters.ensure_roster(store, world, place.id)
    hostile = [world.bestiary[r] for r in roster if world.bestiary[r].temperament != "passive"]
    if not hostile:
        return None
    c = rng.choice(hostile)
    if rank:
        letter, level = scaled_work(rank, rng)
        n = rng.randint(*G["hunt_count"][letter])
        return _quest("hunt", letter, f"Hunt {n} {plural(c.name)} in {place.name} (about level {level})", now,
                      place=place.id, creature=c.id, count=n, scale=level)
    lo, hi = _overlap(c, place)
    letter = letter_for_level((lo + hi) // 2)
    n = rng.randint(*G["hunt_count"][letter])
    return _quest("hunt", letter, f"Hunt {n} {plural(c.name)} in {place.name}", now, place=place.id, creature=c.id, count=n)


def _bounty(world, store, wild, now, rng, rank=None):
    place = rng.choice(wild)
    roster = encounters.ensure_roster(store, world, place.id)
    if not roster:
        return None
    c = max((world.bestiary[r] for r in roster), key=lambda b: _overlap(b, place)[1])
    if rank:
        letter, level = scaled_work(rank, rng)
        return _quest("bounty", letter, f"Bounty: the {c.name.lower()} of {place.name} (about level {level})", now,
                      place=place.id, creature=c.id, count=1, scale=level)
    letter = letter_for_level(_overlap(c, place)[1])
    return _quest("bounty", letter, f"Bounty: the {c.name.lower()} of {place.name}", now, place=place.id,
                  creature=c.id, count=1)


def _gather(world, store, wild, now, rng):
    biomes = {p.biome for p in (wild or world.places.values()) if p.biome}
    herbs = [g for g in inv.GOODS.values() if g.kind == "herb" and set(g.grows_in) & biomes]
    if not herbs:
        return None
    g = rng.choice(herbs)
    n = rng.randint(*G["gather_count"])
    return _quest("gather", "F", f"Gather {n} {g.name}", now, good=g.id, count=n)


def _materials(world, store, wild, now, rng):
    place = rng.choice(wild)
    roster = encounters.ensure_roster(store, world, place.id)
    mats = [(m, world.bestiary[r], place) for r in roster for m in items.MATERIALS.values() if r in m.drops_from]
    if not mats:
        return None
    m, c, place = rng.choice(mats)
    letter = letter_for_level(sum(_overlap(c, place)) // 2)
    n = rng.randint(*G["materials_count"])
    return _quest("materials", letter, f"Bring {n} {m.name}", now, material=m.id, count=n)


def _town(world, place_id: str) -> str:
    p = world.places.get(place_id)
    while p and p.parent and p.parent in world.places:
        p = world.places[p.parent]
    return p.id if p else place_id


def _deliver(world, store, wild, now, rng, hall=None):
    d = rng.choice(G["deliveries"])
    if d["place"] not in world.places:
        return None
    if hall and _town(world, d["place"]) != _town(world, hall):
        return None
    to = d["to_role"].replace("_", " ")
    return _quest("deliver", "F", f"Deliver the {d['item']} to the {to} at {world.places[d['place']].name}", now,
                  to_role=d["to_role"], place=d["place"], item=d["item"], item_description=d["description"])


def _missing(world, store, wild, now, rng, hall=None):
    """A person is missing. Whether this is a short job, a chain or a whole story is decided when the contract is TAKEN."""
    from engine import arcs
    if arcs.active(store.load_arcs()) or not wild:
        return None
    place = rng.choice(wild)
    tpl = rng.choice(list(arcs.TEMPLATES.values()))
    victim = rng.choice(tpl["victims"])
    letter = letter_for_level(sum(place.danger) // 2)
    q = _quest("missing", letter, tpl["board"].format(subject=victim, place=place.name), now, victim=victim,
               hall=hall, count=1)
    q["template"] = tpl["id"]
    return q


def _delve(world, store, wild, now, rng, hall=None):
    found = store.load_dungeons()
    if not found:
        return None
    d = rng.choice(found)
    f = rng.randrange(len(d["floors"]))
    letter = d["floors"][f]["letter"]
    return _quest("delve", letter, f"Clear floor {f + 1} of {d['name']}", now, dungeon=d["id"], floor=f)


def _dungeon_boss(world, store, wild, now, rng, hall=None):
    from engine.dungeons import D
    found = store.load_dungeons()
    if not found:
        return None
    d = rng.choice(found)
    q = _quest("dungeon_boss", d["boss_letter"], f"Slay {d['boss_name']}", now, dungeon=d["id"],
               multiplier=D["boss_bonus"], rank_credit=2)
    q["coins"], q["xp"] = round(q["coins"] * D["boss_bonus"]), round(q["xp"] * D["boss_bonus"])
    return q


# ---------- progress ----------

def held(q: dict, pack: list) -> int:
    if q["kind"] == "gather":
        return inv.count_of(pack, q["good"])
    if q["kind"] == "materials":
        return sum(i.quantity for i in pack if i.base == "raw_material" and i.material == q["material"])
    return q["progress"]


def done(q: dict, pack: list) -> bool:
    return held(q, pack) >= q["count"]


def progress_line(q: dict, pack: list, now: int) -> str:
    if q.get("deadline") is None:
        left = "no time limit"
    else:
        days = max(0, (q["deadline"] - now) // 1440)
        hours = max(0, (q["deadline"] - now) % 1440 // 60)
        left = f"{days}d {hours}h left" if q["deadline"] > now else "expired"
    status = "ready to turn in" if done(q, pack) else (
        "to deliver" if q["kind"] == "deliver" else "not yet" if q["kind"] in ("delve", "dungeon_boss", "missing")
        else f"{held(q, pack)}/{q['count']}")
    who = "" if q["guild"] else f" · for {q['issuer_name']}"
    return f"[{q['letter']}] {q['title']} - {status} · {left}{who}"


def map_offer(world, store, offer, issuer: str, issuer_name: str, now: int, guild: bool = False) -> dict | None:
    """Turn a request (hunt / gather / deliver) into a quest the engine can track, or None if nothing real fits."""
    what = offer.what.lower()
    count = max(1, min(10, offer.count or 1))
    common = {"guild": guild, "issuer": issuer, "issuer_name": issuer_name}
    if offer.kind == "hunt":
        for p in (pl for pl in world.places.values() if pl.danger):
            kept = store.load_place(p.id).roster            # (f424) read, not built: a roster is made only where the creature may be
            could = kept or list(p.anchors) + [f[0].id for f in world.creature_candidates(p.id, encounters.CREATURE_RULES["rarity_weight"],
                                                                                          encounters.CREATURE_RULES.get("fit"))]
            if not encounters.matching(world, could, what):
                continue
            match = encounters.matching(world, kept or encounters.ensure_roster(store, world, p.id), what)
            if match:
                c = world.bestiary[match[0]]
                letter = letter_for_level(sum(_overlap(c, p)) // 2)
                return _quest("hunt", letter, f"Hunt {count} {c.name if count == 1 else plural(c.name)} in {p.name}", now, place=p.id,
                              creature=c.id, count=count, **common)
    if offer.kind == "gather":
        good = inv.find([inv.make_good(g) for g in inv.GOODS], what)
        if good:
            return _quest("gather", "F", f"Bring {count} {good.name}", now, good=good.good, count=count, **common)
        mat = next((m for m in items.MATERIALS.values() if m.name.lower() in what), None)
        if mat:
            return _quest("materials", "F", f"Bring {count} {mat.name}", now, material=mat.id, count=count, **common)
    if offer.kind == "deliver" and offer.to:
        item = offer.item or "a sealed letter"
        return _quest("deliver", "F", f"Deliver {item} to {offer.to}", now, item=item, to_name=offer.to.split()[0],
                      to_role=offer.to.lower().replace("the ", ""), item_description=f"{item}, from {issuer_name}.",
                      **common)
    return None


def contract_reward(level: int) -> int:
    """What a contract pays at this level (copper), smoothed between the ranks and growing past the top one. A yardstick for prices
    that should keep pace with what the player earns."""
    import math
    ranks = sorted(((r["levels"][0], r["reward"]["coins"]) for r in G["ranks"].values()))
    level = max(1, level)
    if level >= ranks[-1][0]:
        from engine import items
        return round(ranks[-1][1] * items.level_growth(level) / items.level_growth(ranks[-1][0]))
    for (l0, c0), (l1, c1) in zip(ranks, ranks[1:]):
        if l0 <= level <= l1:
            return round(math.exp(math.log(c0) + (math.log(c1) - math.log(c0)) * (level - l0) / max(1, l1 - l0)))
    return ranks[0][1]
