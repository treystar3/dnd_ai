"""(f545 part 3) A situation's checked parts written into the world, through the game's own writers, so everything the tellings may name
is held by the game (pillar 1): the people (the town's own, one of its written trades made now, or someone new the engine makes and
names, at most new_per_town_day a day in one town), each with a worry and a mood that say what gave them; the ties between them, felt
both ways; what the situation lays on places and roads (a mark in its own few words when they are plain); and its evidence, each piece
a clue its holder knows in words that say how sure they are, or one lying at a place to be found by searching there. The situation's
end takes back the worries and moods it gave (pulse.end_thread); what the player took on and what people learned stay.

register() is the one entry: situations.check's accepted parts in, the registered parts out (on the thread as th["parts"]), and the
pulse's log told what was written and what could not be. A part that rests on someone who could not be made goes with them. Nothing
here is a clock (the owner): a worry lasts the situation, and nothing times out."""
from __future__ import annotations

import random
import re

from engine import situations

S = situations.S


def _R() -> dict:
    return S.get("register") or {}


def _pick(table: list, key: str) -> str:
    """A line of a phrase table, fixed by its key: the same situation tells the same part the same way, every run."""
    from engine import streams
    return streams.fixed("register", key).choice(table)


def _plain(label: str, ids: set[str]) -> bool:
    """A label fit to stand as a mark's own words: short, plain, no machinery, nothing the hygiene check would stop."""
    from engine import hygiene
    text = (label or "").strip()
    if not text or len(text) > int(_R().get("mark_most", 60)) or situations._raw(text, ids):
        return False
    return hygiene.problem("", {"text": text}) == ("", "")


def _name(store, world, ref: str) -> str:
    if store.npc_exists(ref):
        return store.load_npc(ref).name
    if ref in world.places:
        return world.places[ref].name
    if ref in world.roads:
        return world.roads[ref].name
    return ref.replace("_", " ")


def _today(state: dict, town: str, t: int) -> dict:
    """(the owner) How many new people situations have made in this town today, kept in the world's state so a reload keeps the count."""
    from engine import clock
    day = clock.day(int(t))                                          # (f545's review) the game's day, as ruling.appear counts it
    row = state.setdefault("situation_people", {}).setdefault(town, {"day": day, "n": 0})
    if row.get("day") != day:
        row.update(day=day, n=0)
    return row


def _home(world, town: str, place: str) -> str:
    """Where someone new to the town lives: the situation's own place when people live there, else the town itself."""
    from engine import pulse
    if place in world.places and pulse.town_of(world, place) == town and world.peoples_at(place):
        return place
    return town


def _written_place(store, world, town: str, role: str) -> str:
    """A place of the town written with this trade that has fewer of it made than written: where the town's own of that trade lives."""
    from engine import retrieval
    for pid in retrieval.town_places(world, town):
        wanted = int((world.places[pid].residents or {}).get(role) or 0)
        if not wanted:
            continue
        have = sum(1 for nid in store.load_place(pid).residents if store.npc_exists(nid) and store.load_npc(nid).role == role
                   and not store.load_npc(nid).gone)
        if have < wanted:
            return pid
    return ""


def make_person(store, world, catalog, role: str, home: str, t: int, key: str, anchor=None):
    """Someone the situation needs, made a real person of `home` by the engine as ruling.appear makes one: their name, people and gender
    drawn as for any townsperson, their trade's own description, kept, and one of the place's residents. (f545's review) One of the
    town's anchors (data/world/towns) is made as the town would make them: their own name and note, protected."""
    from engine import doings
    from npc import life, names
    from npc.models import NPC
    from npc.traits import assign_traits, npc_rng
    rng = random.Random(f"{store.meta.seed}:situation:{key}:{role}:{home}")
    peoples = world.peoples_at(home) or {"human": 1}
    people = rng.choices(list(peoples), weights=list(peoples.values()))[0]
    taken = store.npc_names()
    name, gender = names.pick(people, taken, rng)
    if anchor is not None and anchor.name and anchor.name not in taken:
        name = anchor.name
    desc = world.roles[role].description.strip() + (f" In this town: {anchor.note}" if anchor is not None and anchor.note else "")
    npc = NPC(id=life._unique_id(store, name), name=name, gender=gender, people=people, role=role, location=home,
              epithet=f"the {role.replace('_', ' ')}", description=desc)
    if anchor is not None:
        npc.anchor, npc.protected = anchor.note or anchor.role, True
    npc.activity = doings.doing_for(npc, store.meta.seed, int(t))
    if catalog:
        assign_traits(npc, catalog, npc_rng(store.meta.seed, npc.id))
    life.inner_life(npc, store, world)
    store.save_npc(npc)
    st = store.load_place(home)
    st.residents = list(st.residents) + [npc.id]
    store.save_place(st)
    return npc


def _people(store, world, catalog, state, th: dict, accepted: list[dict], t: int, town: str, skipped: list) -> dict[str, str]:
    """Each person part made a real person: the part's `who` -> their id. One the town cannot take in today is left out."""
    ids: dict[str, str] = {}
    most = int(_R().get("new_per_town_day", 2))
    for a in accepted:
        if a["kind"] != "person":
            continue
        if a["bind"] == "npc":
            ids[a["who"]] = a["who"]
            continue
        home = _written_place(store, world, town, a["who"]) if a["bind"] == "town" else ""
        anchor = None
        if home:
            from npc import life
            anchor = life._anchors_wanted(store, world, home).get(a["who"])
        if not home:                                                     # someone new (or the written place is full after all)
            row = _today(state, town, t)
            if row["n"] >= most:
                skipped.append((a, S["reasons"]["new_today"]))
                continue
            row["n"] += 1
            home = _home(world, town, th.get("place", ""))
        npc = make_person(store, world, catalog, a["who"], home, t, f"{th['id']}:{a['who']}", anchor=anchor)
        ids[a["who"]] = npc.id
    return ids


def _remap(accepted: list[dict], ids: dict[str, str], world, skipped: list) -> list[dict]:
    """The parts with each person's `who` made their id; a part resting on someone not made is dropped with them."""
    def person(ref: str) -> str | None:
        return ids.get(ref) if ref in ids else (None if ref and ref not in world.places and ref not in world.roads else ref)
    out = []
    for a in accepted:
        a = dict(a)
        k = a["kind"]
        if k == "person":
            if a["who"] not in ids:
                continue
            a["role"], a["who"] = (a["who"], ids[a["who"]]) if a["bind"] != "npc" else ("", a["who"])
        elif k == "resource":
            for f in ("holder", "wanted_by"):
                if a.get(f):
                    got = ids.get(a[f])
                    if got is None:
                        skipped.append((dict(a), S["reasons"]["unmade"]))   # (f545's review) noted, whether it goes or stays without them
                        if f == "wanted_by":
                            a = None
                            break
                        a[f] = ""
                    else:
                        a[f] = got
            if a is None:
                continue
        elif k == "tie":
            if a["a"] not in ids or a["b"] not in ids:
                skipped.append((a, S["reasons"]["unmade"]))
                continue
            a["a"], a["b"] = ids[a["a"]], ids[a["b"]]
        elif k == "condition" and a.get("by_kind") == "person":           # (f546) its controller made their id, or unknown without them
            got = ids.get(a.get("by", ""))
            a["by"], a["by_kind"] = (got, "person") if got else ("", "")
        elif k == "evidence":
            holder = ids.get(a["holder"]) if a.get("held") == "person" else a["holder"]
            points = person(a["points_to"])
            if not holder or points is None:
                skipped.append((a, S["reasons"]["unmade"]))
                continue
            a["holder"], a["points_to"] = holder, points
        out.append(a)
    return out


# ---------- what a person really holds (recommendation 2: a held good is a small stock they can sell, give or lose)

def held(store, npc_id: str, good: str = "") -> list:
    """The stock this person holds now (of `good`, when given), oldest first: one row a situation, so each goes with its own."""
    return [e for e in store.find_entities(kind="stock", state="held") if e.links.get("npc") == npc_id and e.data.get("count", 0) > 0
            and (not good or e.data.get("good") == good)]


def held_wares(store, npc_id: str) -> list:
    """What they hold, as wares a shop sells, one a good however many situations gave it: the good, at its own price (the town's prices
    and the player's standing laid on by the shop, as for any ware). Its id says it is stock, so a sale takes one from it."""
    from engine import inventory
    from world.loader import Ware
    out, seen = [], set()
    for e in held(store, npc_id):
        g = inventory.GOODS.get(e.data.get("good", ""))
        if g is not None and g.id not in seen:
            seen.add(g.id)
            out.append(Ware(id=f"stock:{g.id}", name=g.name, price=int(g.price), kind="item", item=g.id))
    return out


def wares(store, world, npc) -> list:
    """(f545's review) What this person sells: what they hold first, then their trade's own list without the goods they hold, so a good
    is one ware, sold from what they hold until it is gone and only then from the trade's stock."""
    mine = held_wares(store, npc.id)
    goods = {w.item for w in mine}
    return mine + [w for w in world.roles[npc.role].sells if not (w.kind == "item" and w.item in goods)]


def give_stock(store, npc, good: str, count: int, th_id: str, t: int):
    """They hold `count` of `good`, the situation's: a stock entity of that situation (f545's review: never added to another's, which
    its end would take away with its own)."""
    from engine import entities, inventory
    ref = f"stock:{npc.id}:{good}:{th_id}"
    e = store.load_entity(ref)
    if e is not None and e.state == "held":
        e.data = {**e.data, "count": int(e.data.get("count", 0)) + int(count)}
        store.save_entity(e)
        return e
    return entities.begin(store, "stock", ref, f"{npc.name}'s {inventory.GOODS[good].name}"[:120], int(t), place=npc.location,
                          links={"npc": npc.id}, data={"good": good, "count": int(count), "thread": th_id})


def take_stock(store, npc_id: str, good: str, n: int, minute: int, end: str = "sold_out") -> int:
    """`n` taken from what they hold of `good` (sold, handed over, stolen), the oldest first; a row with none left ends `end`
    (sold_out, lost). How many were taken (0 when they held none)."""
    from engine import entities
    took = 0
    for e in held(store, npc_id, good):
        if took >= n:
            break
        have = int(e.data.get("count", 0))
        k = min(have, int(n) - took)
        e.data = {**e.data, "count": have - k}
        took += k
        if have - k <= 0:
            entities.move(store, e, end, minute, "none left")
        else:
            store.save_entity(e)
    return took


def _count(key: str, span) -> int:
    from engine import streams
    lo, hi = span
    return streams.fixed("register", key).randint(int(lo), int(hi))


def _target(store, world, town: str, good: str, parts: list[dict], holder: str) -> str:
    """Who a stranded load is to be carried to: one of the situation who wants that good, else someone of the town who deals in it (a
    trade that sells it, or one that buys anything); '' when the town has nobody."""
    from engine import retrieval
    want = next((r["wanted_by"] for r in parts if r["kind"] == "resource" and r["good"] == good and r.get("wanted_by")
                 and r["wanted_by"] != holder), "")
    if want:
        return want
    for n in sorted(retrieval.people_in_town(store, world, town), key=lambda n: n.id):
        role = world.roles.get(n.role)
        if n.id != holder and role and (any(w.item == good for w in role.sells) or "any" in role.buys):
            return n.id
    return ""


def mood_source(th_id: str) -> str:
    """(f545's review) The cause a part's mood is kept with: its own, so the situation's end (and drift's sweep) lets go only the moods
    its parts gave, never another the same situation gave by other means (the pride of the one who settled it)."""
    return f"parts:{th_id}"


def register(store, world, state: dict, th: dict, accepted: list[dict], t: int, *, catalog=None, ways: bool = False,
             reach=None) -> list[dict]:
    """Write the checked parts of the situation `th` into the world (its people, worries and moods, ties, conditions and evidence), keep
    them on the thread as th["parts"], and return them. `ways` as check took it (a closure of an only way needs one); `reach` the goods
    within the player's reach, for settling what the parts that could not be made leave behind. Saves the people and places it
    touches; the caller saves `state`."""
    from engine import circumstance, matters, pulse, pulselog
    town = th.get("town") or pulse.town_of(world, th["place"])
    state.setdefault("effects", [])
    skipped: list = []
    ids = _people(store, world, catalog, state, th, accepted, t, town, skipped)
    parts = _remap(accepted, ids, world, skipped)
    if reach is None:                                                      # (f545's review) as check() judged it: the town's reach
        from engine import retrieval
        reach = situations.within_reach(world, town, retrieval.people_in_town(store, world, town))
    situations.settle(parts, reach)                                        # a condition whose key went with an unmade person is lifted
    R = _R()
    title = th.get("title", "")
    live = {x["id"] for x in state.get("threads", []) if x.get("status") == "active" and x.get("id") != th["id"]}
    for i, a in enumerate(parts):
        if a["kind"] != "person":
            continue
        n = store.load_npc(a["who"])
        theirs = n.concern_from or ""
        if not (theirs in live or theirs.startswith("quest:")):          # never over a worry another situation or a job gave them
            circumstance.set_concern(n, _pick(R["worries"][a["want"]], f"{th['id']}:worry:{i}").format(title=title), th["id"])
            a["worry"] = True
        circumstance.set_mood(n, _pick(R["moods"][a["stake"]], f"{th['id']}:mood:{i}"), t, mood_source(th["id"]))
        store.save_npc(n)
    for a in parts:
        if a["kind"] == "tie":
            for end, other, side in ((a["a"], a["b"], "a"), (a["b"], a["a"], "b")):
                value, feeling = R["ties"][a["tie"]][side]
                if value or feeling:
                    pulse.apply_one(store, world, None, state, {"kind": "relation", "npc": end, "other": other, "value": int(value),
                                                                "text": feeling}, th.get("tier", "rare"), t, title, thread_id=th["id"])
    ids_world = set(world.places) | set(world.roads)
    end = int((th.get("times") or [t])[-1])
    days = max(1, -(-(end - int(t)) // 1440))
    before = list(state.get("effects", []))                           # (f545's review) held, so no new effect takes an old one's id
    for i, a in enumerate(parts):
        if a["kind"] != "condition":
            continue
        own = _plain(a.get("label", ""), ids_world)
        text = a["label"].strip() if own else _pick(R["marks"], f"{th['id']}:mark:{i}").format(place=_name(store, world, a["on"]))
        e = {"kind": a["what"], "place": a["on"], "days": days, "text": text if a["what"] in ("mark", "closed") else ""}
        if a["what"] in ("danger", "prices"):
            e["value"] = int(R[a["what"]])
        where = pulse.town_of(world, a["on"]) if a["what"] == "prices" else a["on"]    # (f546's third review) a price rise is the town's
        same = next((x for x in state["effects"] if x.get("thread") == th["id"] and x.get("kind") == a["what"] and x.get("place") == where
                     and "of_part" not in x and not x.get("good") and not x.get("lifted") and int(x.get("until", 0)) > int(t)
                     and a["what"] != "mark" and (a["what"] == "closed" or int(x.get("value", 0)) > 0)), None)   # (f546's fourth
                                                                 # review) only a harm is this harm: a price drop, a safer road, never
        if same is not None:                                            # (f546's second review) what its telling already laid there is
            same["of_part"] = i                                         # this condition: tagged its own, never laid a second time,
            same["part"] = True                                         # (f546's third review) and the parts' own from now on: it
            same["until"] = max(int(same.get("until", 0)), int(t) + days * 1440)   # lasts the situation's span, renewed with it
            a["result"], a["at"] = "held", same.get("place", a["on"])
            a["text"] = text if a["what"] in ("mark", "closed") else ""
            continue
        had = list(state["effects"])
        a["result"] = pulse.apply_one(store, world, None, state, e, th.get("tier", "rare"), t, title, thread_id=th["id"], ways=ways)
        for x in state["effects"]:
            if not any(x is h for h in had):
                x["of_part"] = i                                        # (f546) this condition's own: one closure lifted alone
                a["at"] = x.get("place", a["on"])                       # where it lies in the world (a price rise: its town)
        a["text"] = text if a["what"] in ("mark", "closed") else ""
    from engine import inventory
    for i, a in enumerate(parts):                                         # what each person holds is theirs, to sell until it is gone
        if a["kind"] == "person" and a.get("holds"):
            give_stock(store, store.load_npc(a["who"]), a["holds"], _count(f"{th['id']}:stock:{i}", R["stock"]), th["id"], t)
    for i, a in enumerate(parts):
        if a["kind"] != "resource":
            continue
        g = a["good"]
        if a["state"] in ("scarce", "stranded"):                       # that good dearer in the town while it lasts
            had = list(state["effects"])
            pulse.apply_one(store, world, None, state, {"kind": "prices", "place": town, "value": int(R[a["state"]]), "good": g,
                                                        "days": days}, th.get("tier", "rare"), t, title, thread_id=th["id"])
            for e in state["effects"]:
                if not any(e is h for h in had):
                    e["of_part"] = i                                    # (f545's review) this part's own: its end lifts this one
        if a.get("holder") and a["state"] == "scarce":               # a scarce good to hand, theirs to sell while it lasts; (the owner)
            a["count"] = _count(f"{th['id']}:{a['state']}:{i}", R["stock"])   # a stranded load is a price rise, a worry and a request:
            give_stock(store, store.load_npc(a["holder"]), g, a["count"], th["id"], t)   # no store of its own
        name = inventory.GOODS[g].name
        if a["state"] == "wanted":                                       # the one who wants it asks for it
            n = _count(f"{th['id']}:wanted:{i}", R["wanted"])
            a["request"] = {"npc": a["wanted_by"], "kind": "gather", "good": g, "count": n, "title": f"Bring {n} {name}"}
        elif a["state"] == "stranded" and a.get("holder"):            # the one whose load it is asks for it to be carried
            to = _target(store, world, town, g, parts, a["holder"])
            if to:
                a["request"] = {"npc": a["holder"], "kind": "deliver", "good": g, "to": to,
                                "title": f"Deliver a load of {name} to {store.load_npc(to).name}"}
            else:
                skipped.append((dict(a), S["reasons"]["no_carrier"]))   # (f545's review) a price rise and a worry, and nobody to carry it to
    for e in state.get("effects", []):                                     # (f545's review) the parts' own effects last its span,
        if e.get("thread") == th["id"] and not any(e is b for b in before):   # renewed with it when it is put off (pulse.tick_threads)
            e["part"] = True
    th.setdefault("clues", [])
    for i, a in enumerate(parts):
        if a["kind"] != "evidence":
            continue
        words = {"label": a["label"].strip().rstrip("."), "points": _name(store, world, a["points_to"])}
        if a["held"] == "place":
            text = _pick(R["evidence"]["lies"], f"{th['id']}:lies:{i}").format(**words)
            th["clues"].append({"text": text[:1].upper() + text[1:], "holder": "", "npc": "", "place": a["holder"], "found": False,
                                "label": words["label"], "certainty": a["certainty"], "true": a["true"], "points_to": a["points_to"],
                                "part": True})
        else:
            text = _pick(R["evidence"][a["certainty"]], f"{th['id']}:evidence:{i}").format(**words)
            th["clues"].append({"text": text, "holder": "", "npc": a["holder"], "found": False, "certainty": a["certainty"],
                                "label": words["label"], "true": a["true"], "points_to": a["points_to"], "part": True})
            matters.hold(store, th, len(th["clues"]) - 1, a["holder"], t)    # theirs to know, in words that say how sure they are
        a["clue"] = len(th["clues"]) - 1
    th["parts"] = parts
    th.setdefault("heart", heart(th, parts, state, t, town))             # (f546) the original facts, written once
    have = {(x.get("kind"), x.get("target")) for x in th.setdefault("paths", [])}
    th["paths"].extend(x for x in part_paths(store, world, th, parts, town) if (x["kind"], x["target"]) not in have)
    pulselog.note("parts", f"{title}: {len(parts)} parts in the world" + (f", {len(skipped)} not" if skipped else ""),
                  thread=th["id"], kept=[{k: v for k, v in a.items() if k not in ("true", "made_true")} for a in parts],
                  skipped=[{"part": p, "why": why} for p, why in skipped])
    return parts


# ---------- (f546) the heart, the engine's own parts, the agreement with the prose, and births

def heart(th: dict, parts: list[dict], state: dict, t: int, town: str = "") -> dict:
    """(f546) The situation's original facts, written once and never again (the owner, 2026-11-08: objectives "derived from their
    original facts: what threatens the situation, what is at stake, and who or what controls the relevant conditions"): what threatens
    it (each harmful condition with who or what imposes it - its parts' and (f546's review) those its own telling laid that no part
    holds - each person who blocks an end to it, each creature or band its ways must defeat) and what is at stake (each person it harms,
    each good it puts at stake, the place it is at and its town). The objective, the threat and the ending are read against this
    (f549), never against the parts as they come to stand."""
    H = S.get("heart") or {}
    kinds, states = set(H.get("threat_kinds") or ()), set(H.get("stake_states") or ())
    threats, stakes = [], []
    for i, a in enumerate(parts):
        if a["kind"] == "condition" and a.get("what") in kinds:
            threats.append({"part": i, "kind": "condition", "what": a["what"], "on": a["on"], "at": a.get("at") or a["on"],
                            "by": a.get("by", ""), "by_kind": a.get("by_kind", "")})
        elif a["kind"] == "person" and a.get("stake") == "blocks":
            threats.append({"part": i, "kind": "person", "who": a["who"]})
        elif a["kind"] == "person" and a.get("stake") == "harmed":
            stakes.append({"part": i, "kind": "person", "who": a["who"]})
        elif a["kind"] == "resource" and a.get("state") in states:
            stakes.append({"part": i, "kind": "resource", "good": a["good"], "state": a["state"]})
    held = {(x["what"], x.get("at") or x["on"]) for x in threats if x["kind"] == "condition"}   # where each lies (a price rise: its town)
    for e in (state or {}).get("effects", []):                            # (f546's review) what its telling laid, no part's
        if e.get("thread") == th.get("id") and e.get("kind") in kinds and "of_part" not in e and not e.get("lifted") \
                and int(e.get("until", 0)) > int(t) and (e["kind"], e.get("place", "")) not in held:
            held.add((e["kind"], e.get("place", "")))                     # (f546's second review) one condition, one threat
            by, by_kind = _laid_by(state, th, e, t)
            threats.append({"kind": "condition", "what": e["kind"], "on": e.get("place", ""), "by": by, "by_kind": by_kind,
                            "effect": f"{e['kind']}@{e.get('place', '')}"})
    for p in th.get("paths") or []:
        if p.get("kind") in ("kill", "horde") and (p.get("target") or p.get("spawn")):
            threats.append({"kind": "creature", "target": p.get("target", ""), "spawn": p.get("spawn", "")})
    stakes.append({"kind": "place", "place": th.get("place", ""), "town": town or th.get("town", "")})
    return {"threats": threats, "stakes": stakes, "made": int(t)}


def _laid_by(state: dict, th: dict, e: dict, t: int) -> tuple[str, str]:
    """(f546) Who or what imposes a condition the engine laid for a situation: the creature it set loose, for a closure or a danger;
    nature, for a natural situation's; else unknown."""
    from engine import events
    if th.get("kind") in ("natural", "nature"):
        return "", "nature"
    spawn = next(iter(events.live_spawns(state, t, th.get("id", ""))), None)
    if spawn and e.get("kind") in ("closed", "danger"):
        return spawn.get("name", ""), "creature"
    return "", ""


def adopt(store, world, state: dict, th: dict, t: int) -> list[dict]:
    """(f546) The parts the engine can build from what it already holds, for a rare, campaign or cataclysm situation that has none (an
    old save's, a cataclysm, a birth whose call failed past its tries; the owner: such situations need "stronger handling than simple
    completion detection"): the people its ways must win over, the conditions it already lays on places and roads (each tagged its own,
    its controller the creature it set loose or nature where it is one), and the evidence its living people hold. Written as its parts
    (none, when it holds nothing of the kind: then it is done with, never looked at again) and its heart, with nothing new laid on the
    world and no model call."""
    from engine import pulse
    parts: list[dict] = []
    seen: set[str] = set()

    def alive(who: str) -> bool:
        return bool(who) and store.npc_exists(who) and not store.load_npc(who).gone

    def person(who: str, stake: str, want: str) -> None:
        if who not in seen and alive(who):
            seen.add(who)
            parts.append({"kind": "person", "who": who, "bind": "npc", "new": False, "stake": stake, "want": want, "condition": "",
                          "holds": "", "label": "", "role": "", "engine": True})
    for p in th.get("paths") or []:
        if p.get("done"):
            continue
        if p.get("kind") == "persuade":
            person(p.get("target", ""), "can_fix", "safety")
        elif p.get("kind") == "treaty":
            for w in [x for x in (p.get("target") or "").split(",") if x]:
                person(w, "blocks", "rid_of_rival")
    for e in state.get("effects", []):
        if e.get("thread") != th["id"] or e.get("kind") not in ("closed", "danger", "prices", "mark") or int(e.get("until", 0)) <= int(t) \
                or e.get("lifted") or e.get("place") not in set(world.places) | set(world.roads):
            continue
        by, kind = _laid_by(state, th, e, t)
        e["of_part"] = len(parts)
        parts.append({"kind": "condition", "on": e["place"], "what": e["kind"], "label": "", "text": e.get("text", ""), "by": by,
                      "by_kind": kind, "engine": True})
    for i, c in enumerate(th.get("clues") or []):
        if alive(c.get("npc", "")):
            parts.append({"kind": "evidence", "holder": c["npc"], "held": "person", "points_to": th.get("place", ""), "label": "",
                          "certainty": c.get("certainty") or "they say", "true": c.get("true", True), "clue": i, "engine": True})
    th["parts"] = parts
    th["parts_by"] = "engine"
    th.setdefault("heart", heart(th, parts, state, t, th.get("town") or pulse.town_of(world, th.get("place", ""))))
    th.pop("parts_due", None)
    from engine import pulselog
    pulselog.note("parts", f"{th.get('title', '')}: {len(parts)} parts the engine holds", thread=th["id"], kept=parts, skipped=[])
    return parts


SHOWN = {"condition": ("mark", "closed"), "evidence": None}      # (f546's review) the parts whose words a reader may see: a mark's or a
                                                                 # closure's own words, and every piece of evidence


def agree(store, world, state: dict, th: dict, accepted: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """(f546) The checked parts held to what the situation's prose already established (the owner, 2026-11-08: made after the prose,
    they "must agree with established facts"): a person the prose sent away is no part of it; words a reader may see (a mark's or a
    closure's, a piece of evidence's) that contradict an established line, or could not be checked, are not kept - a condition takes
    the engine's own words instead, a piece of evidence is dropped. Words no reader sees are never checked. Returns (kept, refused with
    the reason)."""
    facts = situations.established(state, th)
    sent = {e.get("npc") for st in (th.get("stages") or [])[:int(th.get("stage", 0)) + 1] for e in ((st or {}).get("effects") or [])
            if e.get("kind") == "leave" and e.get("npc")}
    why = S["reasons"]["contradicts"]
    kept, refused = [], []
    for a in accepted:
        if a["kind"] == "person" and a.get("bind") == "npc" and a["who"] in sent:
            refused.append((a, why))
            continue
        shown = a["kind"] in SHOWN and (SHOWN[a["kind"]] is None or a.get("what") in SHOWN[a["kind"]])
        if shown and a.get("label") and situations.against(a["label"], facts) != "ok":
            if a["kind"] == "evidence":
                refused.append((a, why))
                continue
            a = {**a, "label": ""}
        kept.append(a)
    return kept, refused


def _unparted(x: dict) -> bool:
    """(f546's review) A situation not yet given its parts: none recorded at all, so one the engine found nothing to build from (its
    parts an empty list) is done with."""
    return x.get("status") == "active" and "parts" not in x


def adoptable(state: dict) -> list[dict]:
    """(f546) The live situations of the adopting tiers with no parts and no birth still due, oldest first."""
    B = S.get("births") or {}
    tries, tiers, born = int(B.get("tries", 3)), set(B.get("adopt_tiers") or ()), set(B.get("tiers") or ())
    return sorted((x for x in (state or {}).get("threads", []) if _unparted(x) and x.get("tier") in tiers
                   and (not isinstance(x.get("parts_due"), int) or x["parts_due"] >= tries or x.get("tier") not in born)),
                  key=lambda x: (int(x.get("made", 0)), x["id"]))      # (f546's second review) a tier no longer born: adopted, whatever its due


def due(state: dict) -> dict | None:
    """(f546) The oldest birth still due its parts, if any."""
    B = S.get("births") or {}
    tries, tiers = int(B.get("tries", 3)), set(B.get("tiers") or ())
    return next(iter(sorted((x for x in (state or {}).get("threads", []) if _unparted(x) and x.get("tier") in tiers
                             and isinstance(x.get("parts_due"), int) and x["parts_due"] < tries),
                            key=lambda x: (int(x.get("made", 0)), x["id"]))), None)


def waiting(state: dict) -> bool:
    """(f546) Whether there is anything for the parts operations to do; none is opened otherwise, so an input with nothing born commits
    what it always did."""
    return bool(adoptable(state)) or due(state) is not None


def adopt_all(ws) -> bool:
    """(f546) The adoption operation's body: every situation adoptable now takes the engine's own parts. No call, so it stands apart
    from a birth that may fail."""
    state = ws.store.load_world_state() or {}
    rows = adoptable(state)
    for th in rows:
        adopt(ws.store, ws.world, state, th, ws.minutes)
    if rows:
        ws.store.save_world_state(state)
    return bool(rows)


def missed(ws, tid: str, why: str = "its operation did not stand") -> None:
    """(f546's reviews) A birth that did not stand - its call failed, it kept or made no part, or its operation failed for any reason -
    counts as one of its tries, here, in an operation of its own, so no birth is asked for more than births.tries times. Past them it
    is adoptable, and the adoption (an operation of its own, after) gives it the engine's own parts."""
    from engine import pulse, pulselog
    state = ws.store.load_world_state() or {}
    th = pulse.thread_of(state, tid)
    if th is None or not _unparted(th) or not isinstance(th.get("parts_due"), int):
        return
    th["parts_due"] = int(th["parts_due"]) + 1
    pulselog.note("miss", f"{th.get('title', '')}: no parts this time ({why})", thread=tid)
    ws.store.save_world_state(state)


def birth(ws, tid: str) -> bool:
    """(f546) The birth operation's body, after the input's tail (scenes/world.py): the situation `tid`, due its parts, asks the model
    for them with what its prose established, outside any transaction, and registers what the check and the agreement keep. True when
    it took parts; False when there was nothing to do (a fight on, no longer due). A birth that takes none - its call failed, its place
    is gone, the check and the agreement kept no part, or (f546's second review) registering made none of them - raises LLMError, so
    its operation is rolled back whole (people made, effects laid) and the caller spends one of its tries apart."""
    from engine import pulse, pulselog
    from llm.gateway import LLMError
    if getattr(ws, "combat", None):
        return False
    store, world = ws.store, ws.world
    state = store.load_world_state() or {}
    th = pulse.thread_of(state, tid)
    if th is None or not _unparted(th):
        return False
    place = world.places.get(th.get("place", ""))
    if place is None:
        raise LLMError("the situation's place is gone")
    pressure = world.pressures.get(th.get("pressure") or "")
    trouble = pressure.description if pressure else th.get("title", "")
    ways = pulse.ways_through(state, th["id"])
    _, accepted, dropped = situations.propose(store, world, state, place, th["tier"], ws.minutes,
                                              random.Random(f"{store.meta.seed}:parts:{th['id']}"), trouble=trouble, ways=ways,
                                              players=tuple(c.id for c in ws.characters()),
                                              established_lines=situations.established(state, th))
    kept, refused = agree(store, world, state, th, accepted)
    if refused:
        pulselog.note("parts", f"{th.get('title', '')}: {len(refused)} parts against what its telling established",
                      thread=th["id"], kept=[], skipped=[{"part": p, "why": w} for p, w in refused])
    if not kept:
        raise LLMError("every part it proposed was dropped")
    register(store, world, state, th, kept, ws.minutes, catalog=ws.catalog, ways=ways)
    if not th["parts"]:
        raise LLMError("none of the parts it kept could be made")       # (f546's second review) never an empty heart for good
    th.pop("parts_due", None)
    refresh(ws, th)
    store.save_world_state(state)
    return True


# ---------- (f547) the ruling: an act's changes, checked as a chain, kept through the game's own writers

def heard_by(act: dict) -> set[str]:
    """(f547) Who an act reached: the person it was done to or said to, and everyone there who saw or heard it."""
    return ({act.get("npc") or ""} | set(act.get("witnesses") or ())) - {""}


def trouble_near(world, th: dict, parts: list[dict], town: str = "") -> tuple[list[str], list[str]]:
    """Where a situation's trouble is: the town's places and the wild on its doorstep, the places it makes dangerous, and the roads it
    makes dangerous - or, with none of those, the roads out of the town. (places, roads), each sorted."""
    from engine import towns
    town = town or th.get("town") or pulse_town(world, th.get("place", ""))      # (f547's third review) the town the ways were laid in
    danger = {a["on"] for a in parts if a.get("kind") == "condition" and a.get("what") == "danger" and a.get("on")}
    own = {x for x in (th.get("place"), th.get("wild")) if x and x in world.places}                  # and the situation's own place
    near = sorted(((set(towns.town_places(world, town)) if town in world.places else set()) | danger | own) - set(world.roads))
    roads_near = sorted(danger & set(world.roads)) or sorted(rid for rid, r in world.roads.items() if town in (r.from_, r.to))
    return near, roads_near


def pulse_town(world, place: str) -> str:
    from engine import pulse
    return pulse.town_of(world, place) if place in world.places else ""


def concerns(parts: list[dict], i: int, who: str) -> bool:
    """(f547's second review) Whether part `i` (1-based) is about the person `who`: a condition they impose, goods they hold or want, a
    tie with them at one end, a person tied to them, or evidence they hold or that points to them."""
    a = parts[i - 1] if 1 <= i <= len(parts) else None
    if a is None or not who:
        return False
    k = a.get("kind")
    if k == "condition":
        return a.get("by") == who
    if k == "resource":
        return who in (a.get("holder"), a.get("wanted_by"))
    if k == "tie":
        return who in (a.get("a"), a.get("b"))
    if k == "evidence":
        return who in (a.get("holder"), a.get("points_to"))
    if k == "person":
        return any(t.get("kind") == "tie" and {t.get("a"), t.get("b")} == {who, a.get("who")} for t in parts)
    return False


def ruled(store, th: dict, act: dict, changes: list[dict], world=None) -> tuple[list[dict], list[tuple[dict, str]]]:
    """(f547) The changes a ruling proposed for the act, checked in their order as one chain (the owner, 2026-11-08: "The engine
    validates prerequisites, presence, knowledge, authority, resources, and established world facts before committing them"): a change
    that does not hold is dropped with its reason, and so is every change that needs it; the rest stand, up to rulings.most. Reads the
    save, writes nothing, asks nothing. Returns (kept, dropped with the reason).
    (f547's second review) One rule moves a person set against the one acting (refusing, hostile, committed, as they stood before this
    act): something beyond words must reach them - force, coin, goods or a deed done for them, evidence shown to them, or a change in
    the world that concerns them, made in this act or since they took that stance (moved). One committed is moved only by evidence
    or force. A warning carries fear to the one warned, never the player's words (rulings.warned_may). `world` places a rescue by
    force where the trouble is; without it, only the situation's own place."""
    RU, why = S["rulings"], S["reasons"]
    CH = RU["changes"]
    parts = th.get("parts") or []
    by = act.get("by") or ""
    heard = set(heard_by(act))                                 # who the act itself reached
    reached = set(heard)                                       # (f547's review) and whoever a kept warning reached
    words = bool(act.get("words_only"))
    failed = "fail" in (act.get("degree") or "")
    tier = th.get("tier", "rare")
    wont, cooperative, goods, violence = set(RU["wont"]), set(RU["cooperative"]), set(RU["goods_acts"]), set(RU["force_acts"])
    kept: list[dict] = []
    dropped: list[tuple[dict, str]] = []
    ok: set[int] = set()
    seen: set[int] = set()
    will: dict[int, str] = {}                                  # a person part's willingness toward `by`, as this chain leaves it

    def part(k):
        return parts[k - 1] if isinstance(k, int) and 1 <= k <= len(parts) else None

    def alive(a) -> bool:
        return a is not None and a.get("kind") == "person" and store.npc_exists(a["who"]) and not store.load_npc(a["who"]).gone

    def base(k: int) -> str:                                   # (f547's review) as they stood before this act: no chain launders it
        return ((part(k) or {}).get("willing") or {}).get(by, "")

    def earlier(k: int, word: str) -> bool:
        return any(x["becomes"] == word and x["part"] == k for x in kept)

    def found(k: int) -> bool:
        a = part(k)
        clues = th.get("clues") or []
        held = bool(a and a.get("kind") == "evidence" and isinstance(a.get("clue"), int) and a["clue"] < len(clues)
                    and clues[a["clue"]].get("found"))
        return bool(a and not destroyed(k) and (held or earlier(k, "found")))

    def destroyed(k: int) -> bool:                             # (f547's third review) a piece destroyed is gone for good
        a = part(k) or {}
        clues = th.get("clues") or []
        clue = clues[a["clue"]] if a.get("kind") == "evidence" and isinstance(a.get("clue"), int) and a["clue"] < len(clues) else {}
        return a.get("now") == "destroyed" or bool(clue.get("destroyed")) or earlier(k, "destroyed")

    def shown(c: dict) -> bool:                                # evidence shown: the found piece it names, or (f547's third review)
        if found(int(c.get("about") or 0)):                    # one this chain found or showed first, among what it rests on
            return True
        needs = set(c.get("needs") or ())
        return any(x["n"] in needs and (x.get("because") == "evidence" or (x["becomes"] in ("found", "tested") and found(x["part"])))
                   for x in kept)

    def here(on: str) -> bool:                                 # (f547's third review) the act was at that place, or at a stop on
        place = act.get("place") or ""                         # that road
        if not place or not on:
            return False
        if place == on:
            return True
        if world is not None and on in world.roads:
            from engine import roads
            return roads.on_road(world, place, on)
        return False

    def payee():
        return next((x for x in parts if x.get("kind") == "person" and x.get("who") == act.get("npc")), None)

    def authority(k: int, a: dict) -> bool:                    # (the owner) "the authority or ability to withdraw his soldiers"
        actor = part(k)
        if not alive(actor):
            return False
        me = actor["who"]
        if a["kind"] == "condition":
            boss = a.get("by", "")
            if a.get("by_kind") == "person":
                return boss == me or any(t.get("kind") == "tie" and t.get("tie") == "employs" and t.get("a") == me and t.get("b") == boss
                                         for t in parts)
            return a.get("by_kind") == "group" and actor.get("stake") == "blocks"     # a band's leader commands it
        if a["kind"] == "person":                                # one who holds the harm over another lets them go
            return actor.get("stake") == "blocks" or any(c.get("kind") == "condition" and c.get("by") == me for c in parts)
        return False

    def asks(to: dict) -> int:                                 # (f547's third review) one set against the player is not had for less
        dear = to.get("condition") == "paid" or ((to.get("willing") or {}).get(by, "") in wont)     # than one who sells their help
        return max(1, int(S["register"]["ways"]["pay"].get(tier, 0))) if dear else 1

    def employs(boss: str, man: str) -> bool:
        return any(t.get("kind") == "tie" and t.get("tie") == "employs" and t.get("a") == boss and t.get("b") == man for t in parts)

    def since(k: int) -> int:                                  # when they took the stance they hold toward `by`
        a = part(k) or {}
        return int((a.get("willing_at") or {}).get(by, th.get("made", 0)) or 0)

    def moved(k: int, c: dict) -> set[str]:                    # (f547's reviews) everything beyond words that reached them
        me = (part(k) or {}).get("who", "")
        to = act.get("npc") or ""
        out = set()
        if not words and to and (to == me or employs(to, me)):
            if act.get("kind") in goods:
                if int(act.get("coin") or 0) >= max(asks(payee() or {}), asks(part(k) or {})):
                    out.add("coin")
                if act.get("item") and int(act.get("count") or 1) > 0 and to == me:
                    out.add("goods")
            elif to == me:                                     # done to them: violence, or a deed done for them (moves one who
                out.add("force" if act.get("kind") in violence else "deed")    # refuses, never one committed)
        if not words and act.get("kind") in violence and me in heard:
            out.add("force")                                   # violence they saw done
        if c.get("because") == "evidence" and shown(c):
            out.add("evidence")
        if any(x["part"] == k and x.get("because") == "evidence" for x in kept):
            out.add("evidence")                                # shown to them earlier in this act (checked when kept)
        if any(gain(x, k) and concerns(parts, x["part"], me) for x in kept):
            out.add("world")
        if any(gain(r, k) and int(r.get("minute") or 0) > since(k) and concerns(parts, int(r.get("part") or 0), me)
               for r in th.get("changes") or ()):
            out.add("world")                                   # (f547's second review) a change since they took their stance
        return out

    def gain(x: dict, k: int) -> bool:                         # a change in the world for the player's side, not made by the one
        row = CH.get(x.get("becomes")) or {}                   # moved (k), nor in their own part
        return row.get("layer") in ("world", "action") and bool(row.get("better")) and int(x.get("part") or 0) != k \
            and int(x.get("who") or 0) != k

    def unmoved(k: int, c: dict) -> str:                       # the reason one set against `by` stays so, or ""
        stand = base(k)
        if stand not in wont:
            return ""
        how = moved(k, c)
        if stand == "committed":
            return "" if how & {"evidence", "force"} else why["still_committed"]
        return "" if how else why["still_refusing"]

    def where_trouble() -> bool:                               # (f547's second review) an act of violence where the trouble is
        place = act.get("place") or ""
        if words or act.get("kind") not in violence:
            return False
        if place and place == th.get("place"):
            return True
        if world is None or not place:
            return False
        from engine import roads
        near, on = trouble_near(world, th, parts)              # (f547's third review) the town the ways were laid in
        return place in near or any(roads.on_road(world, place, r) for r in on)

    def problem(c: dict) -> str:
        n, w = c.get("n"), c.get("becomes")
        row = CH.get(w) or {}
        if n in seen:
            return why["twice"]
        if any(x not in ok for x in c.get("needs") or ()):
            return why["rests_on"]
        a, k, who = part(c.get("part")), c.get("part"), int(c.get("who") or 0)
        if a is None or a["kind"] not in row.get("kinds", ()):
            return why["no_part"]
        if a["kind"] == "person" and not alive(a):
            return why["gone"]
        actor = row.get("actor")
        if (actor == "act" and who) or (actor == "self" and who != k) or (actor == "person" and not who):
            return why["not_actor"]
        if who and not alive(part(who)):
            return why["not_actor"]
        layer = row.get("layer")
        because = c.get("because") or "words"
        if layer in ("belief", "feeling", "willingness") and a["who"] not in reached:
            return why["not_heard"]
        if who and part(who)["who"] not in reached:
            return why["not_heard"]
        warned_only = {x for x in reached - heard}               # (f547's second review) a warning carries fear, not the player's words
        if ((a.get("kind") == "person" and a["who"] in warned_only and layer != "world") or (who and part(who)["who"] in warned_only)) \
                and w not in set(RU["warned_may"]):
            return why["not_heard"]
        if not who and layer in ("world", "action"):
            if words or because in ("words", "coin"):            # (f547's review) the player's own hand changes the world, never
                return why["words_only"]                          # a word or a coin by itself
            if a["kind"] == "person" and a["who"] not in heard and not (because == "force" and where_trouble()):
                return why["not_heard"]                          # one freed by the player's own hand: where the act was, or freed by
            hand = by_hand(a, w)                                 # force where the trouble is (their captor beaten); (f547's third
            if hand:                                             # review) anything else, by a hand that was there and could
                return hand
        if failed and row.get("better"):
            return why["failed_act"]
        if a["kind"] == "evidence" and w != "destroyed" and destroyed(k):
            return why["no_evidence"]                          # (f547's third review) a destroyed piece is never found again
        if done_already(a, k, w):
            return why["already"]                              # (f547's third review) a change that changes nothing counts for nothing
        if because == "coin":                                  # (f547's review) the coin went to someone: the one changed or the
            to = payee()                                       # one acting must be them (or, the second review, their employer),
            doer = part(who)["who"] if who else ""             # and it must reach what they ask
            if to is None or (a.get("who") != to["who"] and doer != to["who"] and not (doer and employs(to["who"], doer))):
                return why["unpaid"]
            if int(act.get("coin") or 0) < max(asks(to), asks(part(who)) if who else 1):
                return why["unpaid"]                           # paid through the one they answer to, still their own price
        if because == "goods" and not (act.get("item") and int(act.get("count") or 1) > 0 and act.get("kind") in goods):
            return why["no_goods"]
        if because == "force" and words:
            return why["words_only"]
        if because == "evidence" and not shown(c):
            return why["no_evidence"]                          # (f547's reviews) the piece shown, by its number or among its needs
        if because == "earlier" and not c.get("needs"):
            return why["rests_on"]
        if w in ("lifted", "safe") and who and not authority(who, a):
            return why["no_authority"]
        if w in ("given_up", "moved", "lost") and who and a.get("holder") != part(who)["who"]:
            return why["no_means"]
        if w == "moved" and not who and not (act.get("item") or earlier(k, "given_up")):
            return why["no_means"]
        if w == "tested" and not found(k):
            return why["no_evidence"]
        if w == "warns" and not ((part(int(c.get("about") or 0)) or {}).get("kind") == "person" and int(c.get("about") or 0) != k):
            return why["no_part"]
        if w == "warns" and not alive(part(int(c.get("about") or 0))):
            return why["gone"]                                 # (f547's third review) no one warns the dead
        if who and w in cooperative:
            if will.get(who) in wont:                          # set against the player by this very act
                return why["unwilling"]
            if unmoved(who, c):                                # (f547's second review) as they stood before it, unless moved: no
                return why["unwilling"]                        # worse stance in between launders it
        if layer == "willingness" and base(k) in wont and w != base(k) and (base(k) == "committed" or w not in wont):
            stuck = unmoved(k, c)                              # (f547's third review) out of a stance set against the player - to
            if stuck:                                          # wary, terrified or open, or a committed one to anything - only as
                return stuck                                   # they are moved, never by words that soften them first
        return ""

    def by_hand(a: dict, w: str) -> str:                       # (f547's third review) what the player's own hand may change: only
        kind = a.get("kind")                                   # where it is, and as the one who holds it allows
        if kind == "condition":
            if not here(a.get("on", "")):
                return why["not_there"]
            how = "force" if act.get("kind") in violence else "work"           # one held by someone is broken only by force; a flood
            return "" if how in RU["hand_lifts"].get(a.get("by_kind") or "world", ()) else why["no_means"]   # is not beaten
        if kind == "evidence":
            at = a.get("holder", "")
            return "" if (at in heard if a.get("held") == "person" else here(at)) else why["not_there"]
        if kind == "resource":
            if w == "moved" and act.get("item"):
                from engine import inventory
                return "" if inventory.is_good(act["item"]) == a.get("good") else why["no_means"]
            return "" if a.get("holder") in heard or here(a.get("holder", "")) else why["not_there"]
        if kind == "tie":
            return "" if {a.get("a"), a.get("b")} & heard else why["not_heard"]
        return ""

    def done_already(a: dict, k: int, w: str) -> bool:        # a change in the world or a deed that is already so
        if CH[w]["layer"] not in ("world", "action"):
            return False
        if earlier(k, w) or a.get("now") == {"flees": "fled", "surrenders": "surrendered", "joins": "joined"}.get(w, w):
            return True
        clues = th.get("clues") or []
        return w == "found" and a.get("kind") == "evidence" and isinstance(a.get("clue"), int) and a["clue"] < len(clues) \
            and bool(clues[a["clue"]].get("found"))

    for c in sorted((dict(x) for x in changes), key=lambda x: (int(x.get("n") or 0))):
        reason = problem(c)
        seen.add(c.get("n"))
        if not reason and len(kept) >= int(RU["most"]):
            reason = why["too_many"]
        if reason:
            dropped.append((c, reason))
            continue
        ok.add(c["n"])
        kept.append(c)
        layer = CH[c["becomes"]]["layer"]
        if layer == "willingness":
            will[c["part"]] = c["becomes"]
        if c["becomes"] == "warns":
            reached.add(part(int(c["about"]))["who"])            # (f547's review) the one warned heard it: they may answer at once
    return kept, dropped


def set_against(th: dict, npc_id: str, by: str) -> bool:
    """(f547's third review) Whether this person of the situation stands against the one acting (refusing, hostile or committed): their
    yes is not given by a way met until something moves them (a ruling)."""
    wont = set(S["rulings"]["wont"])
    return any(a.get("kind") == "person" and a.get("who") == npc_id and (a.get("willing") or {}).get(by, "") in wont
               for a in th.get("parts") or ())


def _npc(ws, nid: str):
    """The scene's own copy of a person when it holds one (it saves it at the turn's end), else the store's."""
    held = ws.npc_by_id(nid) if hasattr(ws, "npc_by_id") else None
    return held or ws.store.load_npc(nid)


def keep_changes(ws, state: dict, th: dict, act: dict, kept: list[dict]) -> None:
    """(f547) The checked changes written through the game's own writers: what a person now believes (a told memory, what someone said,
    never what is, and the part's record), how they feel (trust through regard.step, a mood with the parts' cause), what they will do
    (the part's willingness toward the one who acted), what they did (fled, surrendered, joined, warned someone), and what changed in
    the world (a condition lifted by its own effects, goods moved or lost, a tie broken or mended, evidence found, tested or destroyed).
    Each kept change goes on the situation's record (th["changes"], a window). The caller saves `state`."""
    from engine import circumstance, clock, memory, pulse, regard
    RU = S["rulings"]
    parts = th.get("parts") or []
    by = act.get("by") or ""
    t = int(ws.minutes)
    name = char_name(ws, by)
    dirty: dict[str, object] = {}

    def person(a):
        n = dirty.get(a["who"]) or _npc(ws, a["who"])
        dirty[a["who"]] = n
        return n
    for c in kept:
        a, w = parts[c["part"] - 1], c["becomes"]
        key = f"{th['id']}:{c['n']}:{t}"
        if w in ("believes", "doubts"):
            a.setdefault("beliefs", {}).setdefault(by, []).append({"becomes": w, "about": int(c.get("about") or 0), "minute": t})
            memory.keep(person(a), _pick(RU["beliefs"][w], key).format(name=name), day=clock.day(t), turn=-1, kind="told", subject=by,
                        source=by, about=f"belief:{th['id']}:{c['part']}", minute=t)
        elif w in ("warmer", "colder"):
            regard.step(person(a), by, int(RU["trust"]) * (1 if w == "warmer" else -1), "situation", about=th["id"], minute=t)
        elif w in ("afraid", "angry", "grateful"):
            circumstance.set_mood(person(a), _pick(RU["moods"][w], key), t, mood_source(th["id"]))
        elif RU["changes"][w]["layer"] == "willingness":
            a.setdefault("willing", {})[by] = w
            a.setdefault("willing_at", {})[by] = t                # (f547's second review) when they took it: what changes after moves them
        elif w in ("flees", "surrenders", "joins"):
            a["now"] = {"flees": "fled", "surrenders": "surrendered", "joins": "joined"}[w]
        elif w == "warns":
            other = parts[int(c["about"]) - 1]
            if (other.get("willing") or {}).get(by, "") not in RU["wont"]:
                other.setdefault("willing", {})[by] = "wary"
                other.setdefault("willing_at", {})[by] = t
            memory.keep(person(other), _pick(RU["warned"], key).format(name=store_name(ws, a["who"]), who=name), day=clock.day(t), turn=-1,
                        kind="told", subject=by, source=a["who"], about=f"warned:{th['id']}:{c['part']}", minute=t)
        elif w in ("safe", "lifted", "moved", "given_up", "lost", "broken", "mended", "tested", "found", "destroyed"):
            if a.get("now") != "destroyed":                     # (f547's third review) what is destroyed stays so
                a["now"] = w
            if w in ("lifted", "moved", "given_up"):
                for e in state.get("effects", []):
                    if e.get("thread") == th["id"] and e.get("of_part") == c["part"] - 1 and not e.get("lifted"):
                        e["until"], e["lifted"] = min(int(e.get("until", t)), t), True
            if w in ("broken", "mended"):                       # (f547's review) on the copies this keeps, which are what is saved
                value = int(RU["trust"]) * (1 if w == "mended" else -1)
                for end, other in ((a["a"], a["b"]), (a["b"], a["a"])):
                    if ws.store.npc_exists(end) and ws.store.npc_exists(other):
                        n = person({"who": end})
                        r = dict(n.relations.get(other) or {"score": 0, "feeling": ""})
                        r["score"], r["since"] = max(-100, min(100, int(r.get("score", 0)) + value)), t
                        n.relations[other] = r
            clue = (th.get("clues") or [])[a["clue"]] if a.get("kind") == "evidence" and isinstance(a.get("clue"), int) \
                and a["clue"] < len(th.get("clues") or []) else None
            if clue is not None and w in ("found", "tested"):
                if not clue.get("found"):                       # (f547's reviews) found as the game finds a clue: told by its holder
                    holder = clue.get("npc") or ""              # (matters.mark_found: as the player knows them, and their knowing
                    told = bool(holder) and holder == act.get("npc") and ws.store.npc_exists(holder)    # marked told), or found by
                    clue["found"], clue["by"] = True, (_npc(ws, holder).label(by) if told else name)   # hand (the finder's name)
                    th["touched"] = th["answered"] = True
                    if told:
                        ws.store.set_memory_state(holder, "knows", f"thread:{th['id']}:{a['clue']}", f"told:{by}")
                if w == "tested":
                    clue["tested"] = True                       # its truth shown: the engine's (clue["true"]), never the ruling's
            if clue is not None and w == "destroyed":
                clue["destroyed"] = True
        th["changes"] = (list(th.get("changes") or []) + [{"n": c["n"], "part": c["part"], "who": int(c.get("who") or 0), "becomes": w,
                                                           "by": by, "act": act.get("kind", ""), "minute": t}])[-int(RU["window"]):]
    for n in dirty.values():
        ws.store.save_npc(n)


def char_name(ws, cid: str) -> str:
    """A player character's name, by id; "the stranger" for none here."""
    for c in (ws.characters() if hasattr(ws, "characters") else ()):
        if getattr(c, "id", "") == cid:
            return c.name
    me = getattr(getattr(ws, "player", None), "character", None)
    return me.name if me is not None and getattr(me, "id", "") == cid else "the stranger"


def store_name(ws, nid: str) -> str:
    """A person's name for a line, the scene's copy first."""
    return _npc(ws, nid).name if ws.store.npc_exists(nid) else "someone"


def act_of(ws, deed: dict) -> dict:
    """(f547) The act a deed was, for a ruling: its kind, who acted, whom it was done to, who was there, the coin or goods handed over,
    how it went, and whether it was words alone. Read from the deed and the scene, as they stand."""
    RU = S["rulings"]
    from engine import deeds
    here = sorted({n.id for n in (getattr(ws, "present", None) or []) if getattr(n, "id", "")})
    place = deed.get("place", "")
    shown = ws.world.places[place].name if place in getattr(ws.world, "places", {}) else place    # (f547's second review) its name
    beaten = deed.get("kind") == "offense" and deed.get("offense") == "assault"                   # (f547's second review) one beaten is
    npc = deed.get("npc") or (deed.get("target", "") if beaten else "")                           # the one it was done to
    return {"kind": "assault" if beaten else deed.get("kind", ""), "by": deed.get("by") or getattr(ws, "acting", ""), "npc": npc,
            "witnesses": here, "place": place, "coin": int(deed.get("coin") or 0), "item": deed.get("item", ""),
            "count": int(deed.get("count") or 1), "degree": deed.get("degree", ""),
            "words_only": deed.get("kind", "") in set(RU["words_only_acts"]),
            "text": deed.get("text") or deeds.describe(dict(deed, place=shown))}   # (f547's review) what it was: the creature, the job


def parts_lines(store, world, th: dict, by: str = "") -> list[str]:
    """(f547) The situation's parts, numbered as a ruling names them, each with what the check holds it to - who imposes a condition and
    in what words, what an adopted piece of evidence says - and what has changed in it so far, toward the one acting (`by`) only;
    never a clue's truth."""
    parts = th.get("parts") or []
    clues = th.get("clues") or []
    out = []
    for i, a in enumerate(parts):
        one = situations.render([a], store, world, f"{th['id']}:rule:{i}").split("\n", 1)[-1].removeprefix("- ") or a.get("kind", "")
        extra = []
        if a.get("kind") == "condition":
            if a.get("label") or a.get("text"):
                extra.append(f"\"{a.get('label') or a.get('text')}\"")
            if a.get("by_kind") == "person" and a.get("by"):
                extra.append(f"imposed by {store_name_s(store, a['by'])}")
            elif a.get("by"):
                extra.append(f"imposed by {a['by']} ({a.get('by_kind')})")
        if a.get("kind") == "evidence" and not a.get("label") and isinstance(a.get("clue"), int) and a["clue"] < len(clues):
            one = f"{store_name_s(store, a['holder']) if a.get('held') == 'person' else 'At ' + a['holder']} knows: {clues[a['clue']].get('text', '')}"
        notes = [a["now"]] if a.get("now") else []
        if by and (a.get("willing") or {}).get(by):
            notes.append(f"{a['willing'][by]} toward the player")
        line = f"{i + 1}. {one.rstrip('.')}" + (f" ({'; '.join(extra)})" if extra else "") + "."
        out.append(line + (f" Now: {', '.join(notes)}." if notes else ""))
    return out


def store_name_s(store, nid: str) -> str:
    """A person's name from the save, for a line the model reads."""
    return store.load_npc(nid).name if store.npc_exists(nid) else "someone"


def rule(ws, state: dict, th: dict, act: dict):
    """(f547) The dungeon master's ruling on one act against a situation's parts: the model proposes the changes, the engine checks
    them as a chain (ruled) and keeps what holds (keep_changes). Returns (the verdict, kept, dropped). An LLMError is the caller's."""
    from engine import pulse_prompts as pp, pulselog
    from llm.contracts import JudgeVerdict
    from llm.gateway import generate
    names = {n.id: n.name for n in (getattr(ws, "present", None) or []) if getattr(n, "id", "")}
    who = names.get(act.get("npc", "")) or (store_name(ws, act["npc"]) if act.get("npc") else "no one in particular")
    lines = [f"  what: {act.get('kind', '')}" + (f" - {act['text']}" if act.get("text") else ""), f"  to: {who}",
             f"  there: {', '.join(sorted(names.values())) or 'no one else'}",
             f"  handed over: {act['coin']} copper" if act.get("coin") else "  handed over: no coin",
             f"  given: {act['item']}" if act.get("item") else "  given: nothing", f"  how it went: {act.get('degree') or 'done'}"]
    v = generate("event_judge", pp.JUDGE_PARTS_SYSTEM, pp.judge_parts_request(th, parts_lines(ws.store, ws.world, th, act.get("by", "")), lines),
                 JudgeVerdict, temperature=0.3, max_tokens=int(S["rulings"].get("max_tokens", 900)))
    kept, dropped = ruled(ws.store, th, act, [c.model_dump() for c in v.changes], world=ws.world)
    keep_changes(ws, state, th, act, kept)
    pulselog.note("ruled", f"{th.get('title', '')}: {len(kept)} kept, {len(dropped)} dropped", thread=th["id"],
                  kept=kept, dropped=[{"change": c, "why": w} for c, w in dropped])
    return v, kept, dropped


def met_way(ws, state: dict, th: dict, path: dict, by: str) -> None:
    """(f547, the owner, 2026-11-08: the engine-checked ways stay "the instant, certain cases") A person's condition met - paid, given,
    trusted, told, protected, or won over - is a certain change, made with no model call: they are open to the one who met it, and
    the record says what met it; one who blocked an end to it and is won over stands aside, lifting what they impose. Whether the
    situation is then over is the world's to say (f549)."""
    parts = th.get("parts") or []
    i = next((j for j, a in enumerate(parts) if a.get("kind") == "person" and a.get("who") == path.get("target")), None)
    if i is None:
        return
    a = parts[i]
    a.setdefault("willing", {})[by] = "open"
    a.setdefault("willing_at", {})[by] = int(ws.minutes)
    a.setdefault("met", {})[by] = path.get("need") or ("won over" if path.get("kind") == "persuade" else "asked")
    kept = [{"n": 1, "part": i + 1, "who": 0, "becomes": "open", "because": "earlier", "needs": []}]
    if a.get("stake") == "blocks":
        for j, c in enumerate(parts):
            if c.get("kind") == "condition" and c.get("by_kind") == "person" and c.get("by") == a["who"] and c.get("now") != "lifted":
                kept.append({"n": len(kept) + 1, "part": j + 1, "who": i + 1, "becomes": "lifted", "because": "earlier", "needs": [1]})
    keep_changes(ws, state, th, {"kind": "way", "by": by, "npc": a["who"]}, kept[1:])
    th["changes"] = (list(th.get("changes") or []) + [{"n": 1, "part": i + 1, "who": 0, "becomes": "open", "by": by, "act": "way",
                                                       "minute": int(ws.minutes)}])[-int(S["rulings"]["window"]):]


# ---------- (part 4, recommendation 1) the parts are ways through

def part_paths(store, world, th: dict, parts: list[dict], town: str) -> list[dict]:
    """The situation's own ways to an end: one who could set it right, once their condition is met (a path of kind part), and one who
    stands in the way, once won over (a persuade path); the can-fix first, at most register.ways.most. A protected one is kept safe by a
    kill where the trouble is: the town's places and the wild on its doorstep, the places the situation makes dangerous, and the roads
    it makes dangerous (a fight on one is at a stop on it) - or, with no road made dangerous, the roads out of the town. Trusted starts
    from what each character had earned with them before it began (trust_known: those who had met them), and for one met since from
    where the first meeting left them (trust_from, at the first word), so only trust earned counts, never a first meeting's."""
    from engine import inventory
    W = _R()["ways"]
    near, roads_near = trouble_near(world, th, parts, town)
    out = []
    for stake in ("can_fix", "blocks"):
        for i, a in enumerate(parts):
            if a["kind"] != "person" or a["stake"] != stake or len(out) >= int(W["most"]):
                continue
            n = store.load_npc(a["who"])
            want = next((r["good"] for r in parts if r["kind"] == "resource" and r.get("wanted_by") == a["who"]), "")
            need = a.get("condition", "") if stake == "can_fix" else ""
            how = W["how"]["blocks" if stake == "blocks" else need].format(name=n.name, good=inventory.GOODS[want].name if want else "")
            path = {"id": f"{th['id']}:way:{i}", "name": W["name"][stake].format(name=n.name), "how": how,
                    "kind": "part" if stake == "can_fix" else "persuade", "target": a["who"], "need": need, "good": want,
                    "near": near, "roads": roads_near, "spawn": "", "done": False}
            if need == "trusted":
                path["trust_known"] = sorted(cid for cid, r in n.regard.items() if r.met)
            out.append(path)
    return out


def _given(path: dict, state: dict, thread: dict) -> bool:
    """(f545's review) "given": the good they want, as much of it as their own request asks (each gift is one), handed to them; or their
    request for it handed in; or a stranded load of it carried to them as its owner asked and that request handed in."""
    from engine import deeds, inventory
    who, good = path["target"], path.get("good", "")
    parts = thread.get("parts") or []
    if any(a.get("kind") == "resource" and a.get("done") and a.get("good") == good
           and (a.get("wanted_by") == who or (a.get("request") or {}).get("to") == who) for a in parts):
        return True
    want = next((a for a in parts if a.get("kind") == "resource" and a.get("wanted_by") == who and a.get("good") == good), None)
    count = int(((want or {}).get("request") or {}).get("count") or 1)
    gifts = [d for d in deeds.since(state, thread["made"] + 1, ["gift"])
             if d.get("npc") == who and inventory.is_good(d.get("item") or "") == good]
    return bool(good) and sum(max(1, int(d.get("count") or 1)) for d in gifts) >= count


def need_met(path: dict, state: dict, thread: dict, by: str = "") -> bool:
    """(events.path_met, kind part) Whether the condition of the one who could set it right is met by what the player has done since the
    situation began: asked them (a persuasion that landed), paid them (coin handed over or a bribe that bought the favour, at least
    register.ways.pay for the tier), given them what they want (_given), earned their trust, told them what the evidence shows (both
    noted by heard()), or kept them safe (a kill where the trouble is, noted by killed()). Their yes is theirs to give: events.after_deed
    reads this only for a deed done with them (the player with them), so a condition met elsewhere waits for the player's next word."""
    from engine import deeds
    since, who, need = thread["made"], path["target"], path.get("need", "")
    mine = lambda kinds: [d for d in deeds.since(state, since + 1, kinds) if d.get("npc") == who]   # (f545's review) after its
                                                                                                    # birth, never in that minute
    if need == "":
        return any(d.get("degree") in ("success", "strong success") for d in mine(["persuade"]))
    if need == "paid":
        pay = int(_R()["ways"]["pay"].get(thread.get("tier", "rare"), 0))
        return sum(int(d.get("coin") or 0) for d in mine(["gift", "bribe"])) >= pay
    if need == "given":
        return _given(path, state, thread)
    if need in ("trusted", "told", "protected"):                    # (f545's review) met by the character now with them, whose doing
        return bool(path.get(need)) and (not by or path.get(need) == by)   # the end is
    return False


def _words(text: str, least: int = 2) -> set[str]:
    """A line's own words, as a clue's telling is matched: two letters or more ("an ox", "ox tracks"), the filler of told_skip left out
    (its short function words with it: "in", "on", "by"), a plural as its one."""
    skip = set(_R()["ways"].get("told_skip") or ())
    out = set()
    for w in re.findall(rf"[a-z]{{{least},}}", (text or "").lower()):
        if w not in skip:
            out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def clue_head(label: str) -> str:
    """(f545's reviews) The word that says what a clue is: the last word of its head ("tracks" by the watch tower), stepping back past
    a participle or a word that says its state ("a body found in the well", "a door forced open": register.ways.told_not_head, or a
    word of six letters or more ending in -ed); for a label that opens with where it is ("at the watch tower: tracks"), the head of
    what follows its first comma, colon or semicolon."""
    text = (label or "").lower()
    head = situations._head(text)
    if not re.findall(r"[a-z]+", head) and re.search(r"[,:;]", text):
        head = situations._head(re.split(r"[,:;]", text, maxsplit=1)[1])
    skip = set(_R()["ways"].get("told_not_head") or ()) | set(_R()["ways"].get("told_skip") or ())
    words = re.findall(r"[a-z]+", head)
    while len(words) > 1 and (words[-1] in skip or (len(words[-1]) >= 6 and words[-1].endswith("ed"))):
        words.pop()
    return words[-1] if words else ""


def told_by(speech: str, clue: dict, store, world) -> bool:
    """(f545's review) Whether a line tells a clue: by what the clue is, never by the filler its telling is phrased in, nor by the name
    of where it points with one common word beside it. Its own words, all of them up to two, one fewer from three, at most
    register.ways.told_words; a one-word clue with a word of what it points to as well; a clue with no word of its own, its words
    whole."""
    label = (clue.get("label") or "").strip().lower()
    own, said = _words(label), _words(speech)
    if not own:
        return bool(label) and label in (speech or "").lower()
    head = sorted(_words(clue_head(label)))                                              # (f545's review) what the clue is - "tracks"
    if head and not set(head) & said:                                                    # by the watch tower - said, never only
        return False                                                                     # where it is
    need = min(int(_R()["ways"]["told_words"]), len(own) - (1 if len(own) >= 3 else 0))
    if len(own & said) < need:
        return False
    return len(own) > 1 or bool(_words(_name(store, world, clue.get("points_to") or "")) & said)


def _open_ways(state: dict, npc_id: str):
    for th in state.get("threads", []):
        if th.get("status") != "active":
            continue
        for p in th.get("paths") or []:
            if p.get("kind") == "part" and p["target"] == npc_id and not p["done"]:
                yield th, p


def heard(ws, npc, speech: str) -> None:
    """(the talk, after the reply) What talking with them may meet - a found clue of their situation said to them that they did not hold
    themselves (told), or trust earned since the situation began (trusted) - noted on the path; then, the player being with them, every
    way they open is looked at again, so a condition met elsewhere (paid, kept safe) is answered with their yes now."""
    from engine import events, regard
    state = ws.store.load_world_state()
    W = _R()["ways"]
    moved, theirs = False, False
    for th, p in _open_ways(state, npc.id):
        theirs = True
        if p.get("need") == "trusted" and not p.get("trusted"):
            now = int(regard.of(npc, ws.acting).trust)
            if ws.acting in (p.get("trust_known") or ()):          # known before it began: trust earned then counts
                ok = now >= int(W["trust"])
            else:                                                  # met since: where they stood at the first word, a first meeting's
                base = p.setdefault("trust_from", {})              # trust handed out, never earned
                if ws.acting not in base:
                    base[ws.acting], moved = now, True
                b = base[ws.acting]
                ok = now >= min(100, max(int(W["trust"]), b + int(W["trust_gain"]))) and (now > b or b >= 100)
            if ok:
                p["trusted"], moved = ws.acting, True
        if p.get("need") == "told" and not p.get("told"):
            if any(c.get("found") and c.get("npc") != npc.id and told_by(speech, c, ws.store, ws.world) for c in th.get("clues") or []):
                p["told"], moved = ws.acting, True
    if moved:
        ws.store.save_world_state(state)
    if theirs:
        events.after_deed(ws, {"kind": "heard", "minute": ws.minutes, "place": ws.player.location, "npc": npc.id, "by": ws.acting})


def killed(ws, state: dict, deed: dict) -> bool:
    """(events.after_deed, a kill) A kill where a situation's trouble is keeps safe the one who asked for that (protected), noted on
    their path; their yes comes when the player is next with them. True when a path was noted."""
    from engine import roads
    place = deed.get("place") or ""
    noted = False
    for th in state.get("threads", []):
        if th.get("status") != "active":
            continue
        for p in th.get("paths") or []:
            if p.get("kind") == "part" and p.get("need") == "protected" and not p["done"] and not p.get("protected") \
                    and (place in (p.get("near") or ()) or any(roads.on_road(ws.world, place, r) for r in p.get("roads") or ())):
                p["protected"], noted = ws.acting, True
    return noted


def part_done(ws, q: dict) -> None:
    """(the hand-in of a situation's request) That part of the situation is done, for everyone: its own price rise lifted for good (never
    renewed), the one who asked no longer worried by it, the same request still open to another character let go. Then the situation's
    ways are looked at again."""
    from engine import circumstance, events, obligations
    key = str(q.get("part") or "")
    tid, _, i = key.rpartition(":")
    state = ws.store.load_world_state()
    th = next((x for x in state.get("threads", []) if x["id"] == tid and x.get("status") == "active"), None)
    if th is None or not i.isdigit() or int(i) >= len(th.get("parts") or []):
        return
    a = th["parts"][int(i)]
    a["done"] = True
    for e in state.get("effects", []):
        if e.get("thread") == tid and e.get("kind") == "prices" and e.get("of_part") == int(i):
            e["until"], e["lifted"] = min(e["until"], ws.minutes), True
    for e in obligations.open_ones(ws.store, "request"):
        if str((e.data.get("terms") or {}).get("part", "")) == key:
            obligations.close(ws.store, e, "released", "over", ws.minutes, remember=False)   # done by another: nothing to say yes to
    asker = (a.get("request") or {}).get("npc", "")
    if asker and ws.store.npc_exists(asker):
        n = ws.npc_by_id(asker) or ws.store.load_npc(asker)            # the scene's own copy, which the turn's end saves
        if circumstance.release_concern(n, tid, "settled", ws.minutes):
            ws.store.save_npc(n)
    ws.store.save_world_state(state)
    events.after_deed(ws, {"kind": "part_done", "minute": ws.minutes, "place": ws.player.location, "npc": asker})


def ask(ws, npc) -> None:
    """(the talk, when a character speaks with someone) What this person needs of the situation they are in, asked of the one speaking:
    a request opened for them (obligations: request), waiting on their yes, as any request a person makes - and, as any (the owner,
    2026-11-03), refused when a new conversation opens without it taken, released with its reason. Never asked again of a character who
    let it go or said no; never while they have one open with this character; never for a part that is done, or that a character has
    taken on (one load, one carrier)."""
    from engine import inventory, obligations, quests
    if obligations.current(ws.store, "request", npc.id, ws.acting) is not None:
        return
    state = ws.store.load_world_state()
    skip = {q.get("part") for q in ws.player.quests} | carried(ws.store)
    skip.discard("")
    for th in state.get("threads", []):
        if th.get("status") != "active":
            continue
        for i, a in enumerate(th.get("parts") or []):
            r = a.get("request")
            key = f"{th['id']}:{i}"
            if not r or r["npc"] != npc.id or a.get("done") or key in skip or ws.acting in (a.get("declined") or ()):
                continue
            if r["kind"] == "deliver" and (not ws.store.npc_exists(r["to"]) or ws.store.load_npc(r["to"]).gone):
                continue                                             # (f545's review) never a load to carry to the dead
            common = {"guild": False, "issuer": npc.id, "issuer_name": npc.name, "part": key}
            if r["kind"] == "gather":
                q = quests._quest("gather", "F", r["title"], ws.minutes, good=r["good"], count=r["count"], **common)
            else:
                to = ws.store.load_npc(r["to"])
                item = f"a load of {inventory.GOODS[r['good']].name}"
                q = quests._quest("deliver", "F", r["title"], ws.minutes, item=item, to_name=to.name, to_role="", to_id=to.id,
                                  item_description=f"{item}, from {npc.name}, for {to.name}.", **common)   # for the one named, no other
            obligations.open_(ws.store, "request", npc.id, ws.acting, q["title"], ws.minutes, terms=q, key=f"part:{key}:{ws.acting}")
            return


def carried(store) -> set[str]:
    """(f545's review) The parts some character has said yes to and still holds: their live contracts' (terms.part), so one given up or
    done is free again, and none lapses with an old record's trimming."""
    from engine import obligations
    return {str((e.data.get("terms") or {}).get("part", "")) for e in obligations.open_ones(store, "contract")} - {""}


def taken(store, key: str, who: str, t: int) -> None:
    """(f545's review) A character said yes to a part's request: the same request still open to anyone else is let go - one load, one
    carrier."""
    from engine import obligations
    for e in obligations.open_ones(store, "request"):
        if str((e.data.get("terms") or {}).get("part", "")) == key and e.data.get("with") != who:
            obligations.close(store, e, "released", "over", t, remember=False)


def decline(store, key: str, who: str) -> None:
    """(f545's review) A character let a part's request go (a new conversation without a yes, or the job given up): kept on the part
    itself, so that person never asks them for it again, however long ago it was (the offers' records are trimmed; the part is not)."""
    tid, _, i = str(key or "").rpartition(":")
    state = store.load_world_state() or {}
    th = next((x for x in state.get("threads", []) if x["id"] == tid), None)
    if th is None or not i.isdigit() or int(i) >= len(th.get("parts") or []):
        return
    a = th["parts"][int(i)]
    if who not in (a.get("declined") or []):
        a["declined"] = list(a.get("declined") or []) + [who]
        store.save_world_state(state)


ENDED_KEPT = 500             # (f545's review) the ended situations with parts drift's sweep can still find, newest kept


def release(store, th: dict, status: str, t: int, state: dict | None = None) -> None:
    """(the situation's end, from pulse.end_thread) The worries and moods its parts gave its people go with it: a worry settled when it
    ended well, let go when it did not; a mood its parts gave fades now; what they still hold of it moves on (stock released); a request
    nobody said yes to is let go. What the player took on and what people learned stay. The end is kept (state's parts_ended) for drift's
    sweep, so a copy saved late is put right however long after."""
    from engine import circumstance, entities, obligations
    if state is not None:
        ended = state.setdefault("parts_ended", {})
        ended[th["id"]] = status
        for old in list(ended)[:-ENDED_KEPT]:
            del ended[old]
    for e in store.find_entities(kind="stock", state="held"):
        if e.data.get("thread") == th["id"]:
            entities.move(store, e, "released", t, "the situation is over")
    for e in obligations.open_ones(store, "request"):
        if str((e.data.get("terms") or {}).get("part", "")).startswith(f"{th['id']}:"):
            obligations.close(store, e, "released", "over", t, remember=False)      # not "had no yes": the matter ended
    for a in th.get("parts") or []:
        if a.get("kind") != "person" or not store.npc_exists(a["who"]):
            continue
        n = store.load_npc(a["who"])
        changed = circumstance.release_concern(n, th["id"], "settled" if status == "resolved" else "let_go", t)
        if n.mood_source == mood_source(th["id"]):
            circumstance.clear_mood(n)
            changed = True
        if changed:
            store.save_npc(n)


FELT = ("concern", "concern_from", "concern_state", "mood", "mood_source", "mood_until")


def refresh(ws, th: dict) -> None:
    """(f545) The situation's end released its people's worries and moods in the store; a scene that holds a copy of one of them (and
    will save it at the end of the turn) takes the same, so the save does not bring the worry back."""
    for a in th.get("parts") or []:
        if a.get("kind") != "person" or not ws.store.npc_exists(a["who"]):
            continue
        held, fresh = ws.npc_by_id(a["who"]), ws.store.load_npc(a["who"])
        if held is not None and held is not fresh:
            for f in FELT:
                setattr(held, f, getattr(fresh, f))


def sweep(state: dict, npc, t: int) -> bool:
    """(f545, drift's pass) A worry or a mood a situation's parts gave, left after that situation ended (a copy saved after the end was
    told), is let go now: the ends kept in parts_ended, however long ago. A mood the situation gave by other means (the pride of the one
    who settled it) is not the parts' and lasts its own days. True when it changed them."""
    from engine import circumstance
    ended = dict(state.get("parts_ended") or {})
    ended.update({x["id"]: x["status"] for x in state.get("threads", []) if x.get("parts") and x.get("status") != "active"})
    changed = False
    if npc.concern and npc.concern_from in ended:
        changed |= circumstance.release_concern(npc, npc.concern_from, "settled" if ended[npc.concern_from] == "resolved" else "let_go", t)
    src = npc.mood_source or ""
    if src.startswith("parts:") and src[6:] in ended:
        circumstance.clear_mood(npc)
        changed = True
    return changed


def problems() -> list[str]:
    """(f545) The register block of situations.yaml: its numbers, its phrase tables (four lines or more, each with its own slots), a
    feeling for each end of every tie, and its changes inside the pulse's own limits."""
    from engine import pulse
    bad = []
    R = _R()
    L = S.get("lists") or {}
    lim = pulse.P["effects"]
    whole = lambda v, lo, hi: isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi
    if not whole(R.get("new_per_town_day"), 0, 10):
        bad.append("situations.yaml register.new_per_town_day: a whole number from 0 to 10")
    for k in ("danger", "prices"):
        if not whole(R.get(k), 1, int(lim[k]["max"])):
            bad.append(f"situations.yaml register.{k}: a whole number from 1 to pulse.yaml's effects.{k}.max")
    if not whole(R.get("mark_most"), 8, 200):
        bad.append("situations.yaml register.mark_most: a whole number from 8 to 200")
    for k in ("stock", "wanted"):
        v = R.get(k)
        if not (isinstance(v, list) and len(v) == 2 and whole(v[0], 1, 50) and whole(v[1], 1, 50) and v[0] <= v[1]):
            bad.append(f"situations.yaml register.{k}: [least, most], whole numbers from 1 to 50")
    for k in ("scarce", "stranded"):
        if not whole(R.get(k), 1, int(lim["prices"]["max"])):
            bad.append(f"situations.yaml register.{k}: a whole number from 1 to pulse.yaml's effects.prices.max")

    sample = {"title": "The price of salt", "place": "the ford", "label": "a cut rope", "points": "the mill"}

    def table(where: str, got, slots: set) -> None:
        if not isinstance(got, list) or len(got) < 4:
            bad.append(f"situations.yaml register.{where}: four lines or more")
            return
        for line in got:
            bad.extend(situations._line_problems(f"register.{where}", line, slots, {k: sample[k] for k in slots}))
    table("marks", R.get("marks"), {"place"})
    for want in L.get("wants") or ():
        table(f"worries.{want}", (R.get("worries") or {}).get(want), {"title"})
    for stake in L.get("stakes") or ():
        table(f"moods.{stake}", (R.get("moods") or {}).get(stake), set())
    for c in list(L.get("certainties") or ()) + ["lies"]:
        table(f"evidence.{c}", (R.get("evidence") or {}).get(c), {"label", "points"})
    for tie in L.get("ties") or ():
        for side in ("a", "b"):
            got = ((R.get("ties") or {}).get(tie) or {}).get(side)
            ok = isinstance(got, list) and len(got) == 2 and whole(got[0], int(lim["relation"]["min"]), int(lim["relation"]["max"])) \
                and isinstance(got[1], str) and (bool(got[1].strip()) or got[0] == 0)
            if not ok:
                bad.append(f"situations.yaml register.ties.{tie}.{side}: [a change within pulse.yaml's relation limits, the feeling]")
    Wy = R.get("ways") or {}
    if not whole(Wy.get("most"), 0, 6) or not whole(Wy.get("trust"), 51, 100) or not whole(Wy.get("told_words"), 1, 10) \
            or not whole(Wy.get("trust_gain"), 1, 50):
        bad.append("situations.yaml register.ways: most (0 to 6), trust (51 to 100: above a stranger's 50), trust_gain (1 to 50: earned "
                   "since the situation began), told_words (1 to 10), whole numbers")
    nh = Wy.get("told_not_head")
    if not isinstance(nh, list) or not all(isinstance(w, str) and re.fullmatch(r"[a-z]+", w) for w in nh):
        bad.append("situations.yaml register.ways.told_not_head: a list of lowercase words")
    skip = Wy.get("told_skip")
    if not isinstance(skip, list) or not all(isinstance(w, str) and re.fullmatch(r"[a-z]{2,}", w) for w in skip):
        bad.append("situations.yaml register.ways.told_skip: a list of lowercase words of two letters or more (quote one YAML reads as "
                   "something else: \"on\", \"no\", \"off\")")
    if set((Wy.get("pay") or {})) != set(situations.TIERS) or not all(whole(v, 1, 100000) for v in (Wy.get("pay") or {}).values()):
        bad.append("situations.yaml register.ways.pay: copper, a whole number above 0, for each tier")
    for k in ("can_fix", "blocks"):
        bad.extend(situations._line_problems(f"register.ways.name.{k}", (Wy.get("name") or {}).get(k), {"name"}, {"name": "Hollis"}))
    for k in [""] + list(L.get("conditions") or ()) + ["blocks"]:
        slots = {"name", "good"} if k == "given" else {"name"}
        bad.extend(situations._line_problems(f"register.ways.how.{k or 'none'}", (Wy.get("how") or {}).get(k), slots,
                                             {"name": "Hollis", "good": "salt"}))
    for k in ("new_today", "unmade", "no_carrier"):
        if not (S.get("reasons") or {}).get(k):
            bad.append(f"situations.yaml reasons.{k}: a reason is needed")
    return bad
