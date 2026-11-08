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
    day = int(t) // 1440
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


def make_person(store, world, catalog, role: str, home: str, t: int, key: str):
    """Someone the situation needs, made a real person of `home` by the engine as ruling.appear makes one: their name, people and gender
    drawn as for any townsperson, their trade's own description, kept, and one of the place's residents."""
    from engine import doings
    from npc import life, names
    from npc.models import NPC
    from npc.traits import assign_traits, npc_rng
    rng = random.Random(f"{store.meta.seed}:situation:{key}:{role}:{home}")
    peoples = world.peoples_at(home) or {"human": 1}
    people = rng.choices(list(peoples), weights=list(peoples.values()))[0]
    name, gender = names.pick(people, store.npc_names(), rng)
    npc = NPC(id=life._unique_id(store, name), name=name, gender=gender, people=people, role=role, location=home,
              epithet=f"the {role.replace('_', ' ')}", description=world.roles[role].description.strip())
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
        if not home:                                                     # someone new (or the written place is full after all)
            row = _today(state, town, t)
            if row["n"] >= most:
                skipped.append((a, S["reasons"]["new_today"]))
                continue
            row["n"] += 1
            home = _home(world, town, th.get("place", ""))
        npc = make_person(store, world, catalog, a["who"], home, t, f"{th['id']}:{len(ids)}")
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
                        if f == "wanted_by":
                            skipped.append((a, S["reasons"]["unmade"]))
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

def held(store, npc_id: str) -> list:
    """The stock this person holds now, oldest first."""
    return [e for e in store.find_entities(kind="stock", state="held") if e.links.get("npc") == npc_id and e.data.get("count", 0) > 0]


def held_wares(store, npc_id: str) -> list:
    """What they hold, as wares a shop sells: the good, at its own price (the town's prices and the player's standing laid on by the
    shop, as for any ware). Its id says it is stock, so a sale takes one from it."""
    from engine import inventory
    from world.loader import Ware
    out = []
    for e in held(store, npc_id):
        g = inventory.GOODS.get(e.data.get("good", ""))
        if g is not None:
            out.append(Ware(id=f"stock:{g.id}", name=g.name, price=int(g.price), kind="item", item=g.id))
    return out


def give_stock(store, npc, good: str, count: int, th_id: str, t: int, load: bool = False):
    """They hold `count` of `good`, the situation's (a load when stranded): a stock entity, added to what they hold of it already."""
    from engine import entities, inventory
    ref = f"stock:{npc.id}:{good}"
    e = store.load_entity(ref)
    if e is not None and e.state == "held":
        e.data = {**e.data, "count": int(e.data.get("count", 0)) + int(count)}
        store.save_entity(e)
        return e
    return entities.begin(store, "stock", ref, f"{npc.name}'s {inventory.GOODS[good].name}"[:120], int(t), place=npc.location,
                          links={"npc": npc.id}, data={"good": good, "count": int(count), "thread": th_id, "load": bool(load)})


def take_stock(store, npc_id: str, good: str, n: int, minute: int, end: str = "sold_out") -> bool:
    """`n` taken from what they hold of `good` (sold, handed over, stolen); at none left it ends `end` (sold_out, lost). False when they
    hold none."""
    from engine import entities
    e = store.load_entity(f"stock:{npc_id}:{good}")
    if e is None or e.state != "held" or int(e.data.get("count", 0)) <= 0:
        return False
    left = int(e.data["count"]) - int(n)
    e.data = {**e.data, "count": max(0, left)}
    if left <= 0:
        entities.move(store, e, end, minute, "none left")
    else:
        store.save_entity(e)
    return True


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


def register(store, world, state: dict, th: dict, accepted: list[dict], t: int, *, catalog=None, ways: bool = False,
             reach=frozenset()) -> list[dict]:
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
        circumstance.set_mood(n, _pick(R["moods"][a["stake"]], f"{th['id']}:mood:{i}"), t, f"thread:{th['id']}")
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
    for i, a in enumerate(parts):
        if a["kind"] != "condition":
            continue
        own = _plain(a.get("label", ""), ids_world)
        text = a["label"].strip() if own else _pick(R["marks"], f"{th['id']}:mark:{i}").format(place=_name(store, world, a["on"]))
        e = {"kind": a["what"], "place": a["on"], "days": days, "text": text if a["what"] in ("mark", "closed") else ""}
        if a["what"] in ("danger", "prices"):
            e["value"] = int(R[a["what"]])
        a["result"] = pulse.apply_one(store, world, None, state, e, th.get("tier", "rare"), t, title, thread_id=th["id"], ways=ways)
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
            pulse.apply_one(store, world, None, state, {"kind": "prices", "place": town, "value": int(R[a["state"]]), "good": g,
                                                        "days": days}, th.get("tier", "rare"), t, title, thread_id=th["id"])
        if a.get("holder"):
            a["count"] = _count(f"{th['id']}:{a['state']}:{i}", R["load" if a["state"] == "stranded" else "stock"])
            give_stock(store, store.load_npc(a["holder"]), g, a["count"], th["id"], t, load=a["state"] == "stranded")
        name = inventory.GOODS[g].name
        if a["state"] == "wanted":                                       # the one who wants it asks for it
            n = _count(f"{th['id']}:wanted:{i}", R["wanted"])
            a["request"] = {"npc": a["wanted_by"], "kind": "gather", "good": g, "count": n, "title": f"Bring {n} {name}"}
        elif a["state"] == "stranded" and a.get("holder"):            # the one whose load it is asks for it to be carried
            to = _target(store, world, town, g, parts, a["holder"])
            if to:
                a["request"] = {"npc": a["holder"], "kind": "deliver", "good": g, "to": to,
                                "title": f"Deliver a load of {name} to {store.load_npc(to).name}"}
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
                                "true": a["true"], "points_to": a["points_to"], "part": True})
            matters.hold(store, th, len(th["clues"]) - 1, a["holder"], t)    # theirs to know, in words that say how sure they are
        a["clue"] = len(th["clues"]) - 1
    th["parts"] = parts
    pulselog.note("parts", f"{title}: {len(parts)} parts in the world" + (f", {len(skipped)} not" if skipped else ""),
                  thread=th["id"], kept=[{k: v for k, v in a.items() if k not in ("true", "made_true")} for a in parts],
                  skipped=[{"part": p, "why": why} for p, why in skipped])
    return parts


def ask(ws, npc) -> None:
    """(the talk, when a character speaks with someone) What this person needs of the situation they are in, asked of the one speaking:
    a request opened for them (obligations: request), waiting on their yes, as any request a person makes. Never when they already
    have one open with this character, nor for a part this character has taken on or that is done."""
    from engine import inventory, obligations, quests
    if obligations.current(ws.store, "request", npc.id, ws.acting) is not None:
        return
    state = ws.store.load_world_state()
    taken = {q.get("part") for q in ws.player.quests}
    for th in state.get("threads", []):
        if th.get("status") != "active":
            continue
        for i, a in enumerate(th.get("parts") or []):
            r = a.get("request")
            key = f"{th['id']}:{i}"
            if not r or r["npc"] != npc.id or a.get("done") or key in taken:
                continue
            common = {"guild": False, "issuer": npc.id, "issuer_name": npc.name, "part": key}
            if r["kind"] == "gather":
                q = quests._quest("gather", "F", r["title"], ws.minutes, good=r["good"], count=r["count"], **common)
            else:
                to = ws.store.load_npc(r["to"])
                item = f"a load of {inventory.GOODS[r['good']].name}"
                q = quests._quest("deliver", "F", r["title"], ws.minutes, item=item, to_name=to.name.split()[0], to_role=to.role,
                                  item_description=f"{item}, from {npc.name}.", **common)
            obligations.open_(ws.store, "request", npc.id, ws.acting, q["title"], ws.minutes, terms=q, key=f"part:{key}:{ws.acting}")
            return


def release(store, th: dict, status: str, t: int) -> None:
    """(the situation's end, from pulse.end_thread) The worries and moods its parts gave its people go with it: a worry settled when it
    ended well, let go when it did not; a mood it gave fades now; what they still hold of it moves on (stock released); a request
    nobody said yes to is let go. What the player took on and what people learned stay."""
    from engine import circumstance, entities, obligations
    for e in store.find_entities(kind="stock", state="held"):
        if e.data.get("thread") == th["id"]:
            entities.move(store, e, "released", t, "the situation is over")
    for e in obligations.open_ones(store, "request"):
        if str((e.data.get("terms") or {}).get("part", "")).startswith(f"{th['id']}:"):
            obligations.close(store, e, "released", "over", t)
    for a in th.get("parts") or []:
        if a.get("kind") != "person" or not store.npc_exists(a["who"]):
            continue
        n = store.load_npc(a["who"])
        changed = circumstance.release_concern(n, th["id"], "settled" if status == "resolved" else "let_go", t)
        if n.mood_source == f"thread:{th['id']}":
            circumstance.clear_mood(n)
            changed = True
        if changed:
            store.save_npc(n)


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
    for k in ("stock", "load", "wanted"):
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
    for k in ("new_today", "unmade"):
        if not (S.get("reasons") or {}).get(k):
            bad.append(f"situations.yaml reasons.{k}: a reason is needed")
    return bad
