"""Threads the engine builds itself (f331): the ordinary situations of the world, made without a model call.

The pulse (engine/pulse.py) starts situations - threads - away from the player. Four in five are normal and most of the rest uncommon:
wolves off the wood, a quarrel at the inn, a hard season, a windfall. Those the engine makes here from a template for the pressure's
kind (data/rules/threads.yaml): the pressure's own severity and scope decide the size of it, the place's own people and creatures play
the parts, and every line comes from a phrase table with its slots filled. A kind has several shapes (f341): a threat is predators at the
pens, or a demand for tribute, or a party lost in the wild, or a road cut; the engine draws one the place can fill, by weight, so the
seventeen threat pressures do not all open with the same three lines. The result is a ThreadProposal like the model's, complete
at birth, so everything downstream (doors, clues, paths, contracts, effects, news) runs the same for either maker. The model keeps the
rare and the campaign-sized, and takes over the normal ones only to re-tell them: when the player comes where a situation is, tell()
makes one call that rewrites the lines nothing has copied yet in the world's own words - never the title, which is the key the world
keeps its effects and memories under, and never a line already in the news or in somebody's head.

Why: a world that moves only when a model writes moves slowly and alike; a world whose ordinary life is the engine's own moves
differently on every seed, costs nothing while nobody watches, and still reads fresh where the player is."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml

from ui import console

ROOT = Path(__file__).resolve().parent.parent
T = yaml.safe_load((ROOT / "data" / "rules" / "threads.yaml").read_text(encoding="utf-8"))
SLOTS = ("town", "place", "wild", "neighbour", "road", "region", "season", "creature", "creatures", "role", "role2", "about", "good")
PLACE_SLOTS = ("town", "place", "wild", "neighbour", "road")
PERSON_SLOTS = ("role", "role2")
_SLOT = re.compile(r"\{([A-Za-z][a-z0-9]*)\}")
_SPLIT = re.compile(r",\s+(?:or |and )?|;\s+")


# ---------- words: the parts a place lends a situation

def fill(text: str, words: dict) -> str:
    """{slot} filled from words; {Slot} capitalises the first letter. A slot the place could not fill makes the line unusable: ''."""
    missing = []

    def one(m):
        key = m.group(1)
        v = words.get(key[0].lower() + key[1:])
        if not v:
            missing.append(key)
            return ""
        return (v[0].upper() + v[1:]) if key[0].isupper() else v
    out = _SLOT.sub(one, text)
    return "" if missing else out


def clause(description: str, rng: random.Random) -> str:
    """One clause of a pressure's description, as the thing that is happening: 'Caravan trouble - a caravan is delayed, robbed or lost'
    gives 'a caravan is robbed' or the like."""
    text = description.strip()
    if " - " in text:
        text = text.split(" - ", 1)[1]
    text = text.split(". ")[0].rstrip(".")
    bits = [b.strip().rstrip(".") for b in _SPLIT.split(text) if len(b.strip()) >= 12]
    pick = rng.choice(bits) if bits else text
    return pick[0].lower() + pick[1:] if pick else ""


def nearest_town(world, place_id: str) -> str:
    """The settlement a place belongs to, or the nearest one by the roads when the place is wild."""
    from engine import pulse
    top = pulse.town_of(world, place_id)
    if world.peoples_at(top) and not world.places[top].danger:
        return top
    best = None
    for pid, p in world.places.items():
        if p.parent or p.danger or not world.peoples_at(pid) or p.type == "road":
            continue
        found = world.path(top, pid)
        if found and (best is None or found[1] < best[0]):
            best = (found[1], pid)
    return best[1] if best else top


def wild_near(world, town: str, place_id: str) -> str:
    """The dangerous place the situation is in, or the nearest to the town: the place itself when it is wild, else a neighbour with danger."""
    if world.places[place_id].danger:
        return place_id
    links = dict(world.places[town].connects)
    for pid, p in world.places.items():
        if town in p.connects and pid not in links:
            links[pid] = p.connects[town]
    wilds = sorted((-world.places[pid].danger[1], m, pid) for pid, m in links.items()
                   if pid in world.places and world.places[pid].danger and world.places[pid].type != "road")       # the wildest first: a wood over a field
    if wilds:
        return wilds[0][2]
    region = world.places[town].region
    same = sorted(pid for pid, p in world.places.items() if p.danger and p.region == region and p.type != "road")
    return same[0] if same else ""


def neighbours_of(world, town: str) -> list[str]:
    """The settlements a town connects to, nearest first."""
    links = dict(world.places[town].connects)
    for pid, p in world.places.items():
        if town in p.connects and pid not in links:
            links[pid] = p.connects[town]
    towns = sorted((m, pid) for pid, m in links.items() if pid in world.places and not world.places[pid].danger and world.peoples_at(pid) and not world.places[pid].parent)
    return [pid for _, pid in towns]


def neighbour_of(world, town: str) -> str:
    near = neighbours_of(world, town)
    return near[0] if near else ""


def road_of(world, town: str, rng: random.Random) -> str:
    mine = sorted(r.id for r in world.roads.values() if town in (r.from_, r.to))
    return rng.choice(mine) if mine else ""


def people_of(store, world, town: str, rng: random.Random) -> list:
    """The town's people as (role, npc id) pairs: real people first, so clue holders bind at birth; then the roles the place is written with."""
    from engine import retrieval
    never = set(T.get("never_roles") or ())
    rows = [(r.role, r.id) for r in retrieval.people_in_town(store, world, town) if r.role not in never]
    seen = {role for role, _ in rows}
    for pid in retrieval.town_places(world, town):
        for role in world.places[pid].residents:
            if role not in seen and role not in never:
                rows.append((role, ""))
                seen.add(role)
    rng.shuffle(rows)
    rows.sort(key=lambda r: r[1] == "")                     # the real people first, in a random order
    return rows


def creature_of(store, world, wild: str, rng: random.Random):
    """One creature of the wild's own roster, singular name and id; None when the wild has none."""
    from engine import encounters
    if not wild or not world.places[wild].danger:
        return None
    roster = [c for c in encounters.ensure_roster(store, world, wild) if c in world.bestiary and not world.bestiary[c].unique]
    if not roster:
        return None
    cid = rng.choice(roster)
    return cid, world.bestiary[cid].name.lower()


def words_for(store, world, place, pressure, rng: random.Random, t: int, template: dict | None = None) -> dict:
    """Every slot the place can fill, as names, with the ids they stand for under 'ids'."""
    from engine import clock, inventory, quests
    fixed = dict(pressure.words) if pressure else {}
    town = fixed.get("town") if fixed.get("town") in world.places else nearest_town(world, place.id)
    wild = fixed.get("wild") if fixed.get("wild") in world.places else wild_near(world, town, place.id)
    neighbour = neighbour_of(world, town)
    road = road_of(world, town, rng)
    words = {"town": world.places[town].name, "place": place.name, "region": world.regions[place.region].name, "season": clock.season(t),
             "wild": world.places[wild].name if wild else "", "neighbour": world.places[neighbour].name if neighbour else "",
             "road": world.roads[road].name if road else ""}
    ids = {"town": town, "place": place.id, "wild": wild, "neighbour": neighbour, "road": road}
    if fixed.get("creature") in world.bestiary:
        found = (fixed["creature"], world.bestiary[fixed["creature"]].name.lower())
    else:
        found = creature_of(store, world, wild, rng)
    if found:
        ids["creature"] = found[0]
        words["creature"] = found[1]
        words["creatures"] = quests.plural(found[1])
    people = people_of(store, world, town, rng)
    for slot, (role, nid) in zip(PERSON_SLOTS, people[:2]):
        words[slot] = role.replace("_", " ")
        ids[slot] = nid or role                                 # a person when there is one, else the role: engine/matters.py binds it later
        ids[slot + "_role"] = role
    goods = sorted(g.id for g in inventory.GOODS.values() if g.kind in ("herb", "food"))
    if goods:
        gid = rng.choice(goods)
        words["good"] = inventory.GOODS[gid].name
        ids["good"] = gid
    about = clause(pressure.description, rng) if pressure else ""
    if not about and template:
        about = fill(rng.choice(template.get("abouts") or ["a quiet trouble"]), words)
    words["about"] = about
    for k, v in fixed.items():                                  # a pressure's own words win where they are plain text
        if k not in ids and k in SLOTS:
            words[k] = v
    words["ids"] = ids
    return words


# ---------- the template, and what it needs

def kind_of(key: str) -> str:
    """The kind a template tells: its own `kind`, else its key (a kind's base template is keyed by the kind itself)."""
    tpl = T["templates"].get(key) or {}
    return tpl.get("kind") or key


def shapes(kind: str) -> list[str]:
    """Every template that tells a situation of this kind: the base one first, then the other shapes in the order written."""
    keys = [k for k in T["templates"] if kind_of(k) == kind]
    return sorted(keys, key=lambda k: k != kind)


def template_for(pressure, kind: str, words: dict, rng: random.Random | None = None) -> tuple[str, dict] | None:
    """The template named by the pressure, else one of its kind's shapes the place can fill, drawn by weight (f341; the base shape when
    no rng is given); when none fits, the kind's base template falls back, until one fits."""
    key = pressure.template if pressure and pressure.template else ""
    if not key:
        fits = [k for k in shapes(kind or "social") if all(words.get(n) for n in T["templates"][k].get("needs", []))]
        if fits:
            k = fits[0] if rng is None else rng.choices(fits, weights=[float(T["templates"][x].get("weight", 1) or 1) for x in fits])[0]
            return k, T["templates"][k]
        key = kind or "social"
    seen = set()
    while key and key not in seen and key in T["templates"]:
        seen.add(key)
        tpl = T["templates"][key]
        if all(words.get(n) for n in tpl.get("needs", [])):
            return key, tpl
        key = tpl.get("fallback", "")
    return None


def _range(spec, rng: random.Random, scale: float = 1.0) -> int:
    if isinstance(spec, (list, tuple)):
        lo, hi = spec
        v = rng.randint(min(lo, hi), max(lo, hi))
    else:
        v = int(spec or 0)
    return round(v * scale)


def _line(spec, words: dict, rng: random.Random) -> str:
    if not spec:
        return ""
    lines = spec if isinstance(spec, list) else [spec]
    options = [fill(l, words) for l in lines]
    options = [o for o in options if o]
    return rng.choice(options) if options else ""


def _title(tpl: dict, words: dict, rng: random.Random, state: dict, place_id: str) -> str:
    """A title no situation at this place already wears, among those the place can fill; when every one is taken, the chosen one
    'again'. The title is the name the world keeps a situation's effects and memories under, so two alike here would read as one."""
    used = {x.get("title") for x in state.get("threads", []) if x.get("place") == place_id}
    options = [o for o in (fill(l, words) for l in (tpl.get("titles") or [])) if o]
    fresh = [o for o in options if o not in used]
    if fresh:
        return rng.choice(fresh)
    if options:
        return rng.choice(options) + " again"
    return words["about"].capitalize()


def _effect(spec: dict, words: dict, rng: random.Random, scale: float):
    """One effect from its template: slots resolved to ids, numbers rolled and scaled. None when a slot it needs is not filled."""
    from llm.contracts import WorldEffect
    ids = words["ids"]
    e = {"kind": spec["kind"]}
    for key in ("place", "npc", "other"):
        if key in spec:
            v = ids.get(spec[key], "")
            if key != "place" and v and v == ids.get(spec[key] + "_role"):        # a role with nobody of it yet: no person to touch
                v = ""
            if not v:
                return None
            e[key] = v
    if "role" in spec:
        e["role"] = spec["role"]
    if "value" in spec:
        e["value"] = _range(spec["value"], rng, scale)
    if "days" in spec:
        e["days"] = max(1, _range(spec["days"], rng))
    if "text" in spec:
        e["text"] = _line(spec["text"], words, rng)
        if not e["text"]:
            return None
    if "groups" in spec:
        e["groups"] = [words["groups_locals"] if g == "locals" else g for g in spec["groups"]]
    try:
        return WorldEffect(**e)
    except Exception as err:                                    # a template written wrong: data_check catches it before play; here it is only dropped
        console.debug(f"threads: dropped a templated effect ({err})")
        return None


def build(store, world, state: dict, place, pressure, tier: str, rng: random.Random, t: int):
    """A complete proposal for a situation at this place, at this tier, or None when no template can be filled here.
    Returns (proposal, info) where info carries the template key, the severity and the words used, for the thread record."""
    from engine import pulse
    from llm.contracts import ClueProposal, PathProposal, QuestOffer, StageProposal, ThreadProposal
    kind = pressure.kind if pressure else rng.choices(list(T["kind_weights"]), weights=list(T["kind_weights"].values()))[0]
    words = words_for(store, world, place, pressure, rng, t, T["templates"].get(kind))
    found = template_for(pressure, kind, words, rng)
    if not found:
        return None
    key, tpl = found
    if not pressure or not words.get("about"):                   # no description to take a clause from: the shape's own abouts
        words["about"] = fill(rng.choice(tpl.get("abouts") or ["a quiet trouble"]), words) or "a quiet trouble"
    words["groups_locals"] = world.locals_group(place.id) or "everyone"
    severity = rng.randint(*pressure.severity) if pressure else rng.randint(1, 3)
    scale = T["severity_scale"][severity] * T["tier_scale"].get(tier, 1.0)
    n = pulse.P["tiers"][tier]["stages"]
    specs = list(tpl["stages"])
    while len(specs) < n:
        specs.append(specs[-1])
    stages, streets = [], []
    for spec in specs[:n]:
        line = _line(spec["lines"], words, rng)
        if not line:
            return None
        effects = [e for e in (_effect(x, words, rng, scale) for x in spec.get("effects", [])) if e]
        stages.append(StageProposal(description=line, effects=effects))
        streets.append(_street(spec, words, world, rng))                                        # (f357) what the stage looks like in the streets
    fall = tpl["fallout"]
    fallout = StageProposal(description=_line(fall["lines"], words, rng) or "It ran its course.",
                            effects=[e for e in (_effect(x, words, rng, scale) for x in fall.get("effects", [])) if e])
    ids = words["ids"]
    clues = []
    for c in (tpl.get("clues") or [])[:T["clues_most"]]:
        holder = ids.get(c["holder"], "")
        text = _line(c["lines"], words, rng)
        if holder and text:
            clues.append(ClueProposal(text=text, holder=holder))
    contract = None
    cs = tpl.get("contract")
    if cs:
        what = words.get(cs["what"], "")
        if what:
            contract = QuestOffer(kind=cs["kind"], what=what, count=_range(cs.get("count", 1), rng))
    paths = []
    for ps in tpl.get("paths") or []:
        target = ""
        if ps["kind"] == "contract":
            if not contract:
                continue
        elif ps["kind"] == "kill":
            target = ids.get("creature", "")
        elif ps["kind"] == "persuade":
            target = ids.get(ps["target"], "")
            if target == ids.get(ps["target"] + "_role"):             # nobody of that trade is made yet: engine/events.py would drop it anyway
                target = ""
        elif ps["kind"] == "find":
            target = ids.get(ps["target"], "")
            if ps["target"] == "road" or (target and target not in world.places):
                target = ids.get("wild") or ids.get("town", "")
        if ps["kind"] != "contract" and not target:
            continue
        paths.append(PathProposal(name=fill(ps.get("name", ps["kind"]), words) or ps["kind"], how=fill(ps.get("how", ""), words),
                                  kind=ps["kind"], target=target))
    scope = (pressure.scope if pressure else "local")
    groups = [words["groups_locals"] if g == "locals" else g for g in T["scope"].get(scope, T["scope"]["local"])["groups"]]
    proposal = ThreadProposal(
        title=_title(tpl, words, rng, state, place.id)[:90], place=place.id, kind=kind,
        news=_line(tpl["news"], words, rng) or f"There is talk in {words['town']}: {words['about']}.",
        groups=list(dict.fromkeys(groups)), stages=stages, fallout=fallout,
        resolution=_line(tpl.get("resolution"), words, rng), contract=contract, paths=paths,
        truth=_line(tpl.get("truth"), words, rng), clues=clues, reveal=_line(tpl.get("reveal"), words, rng) if contract else "")
    info = {"template": key, "severity": severity, "words": {k: v for k, v in words.items() if k != "ids" and v}, "ids": ids, "streets": streets}
    return proposal, info


# ---------- (f357) the streets: what a stage looks like where the player walks

STREET_PLACES = ("square", "inn", "temple", "guild", "shop", "smithy", "workshop", "yard", "guardpost")


def _street(spec: dict, words: dict, world, rng: random.Random) -> dict:
    """A stage's doings (all: at the situation's place; the cast by role, town-wide), the cast placed (`at`: npc id -> place id, only for a
    real person and a place the town has), and the scene shape, filled from the situation's words."""
    ids = words["ids"]
    out = {"doings": {"all": "", "roles": {}}, "cast": {}, "scene": spec.get("scene", "")}
    d = spec.get("doings") or {}
    if d.get("all"):
        out["doings"]["all"] = fill(d["all"], words).rstrip(".")
    for slot in PERSON_SLOTS:
        if d.get(slot) and words.get(slot):
            text = fill(d[slot], words).rstrip(".")
            if text:
                out["doings"]["roles"][ids.get(slot + "_role", words[slot].replace(" ", "_"))] = text
    from engine import retrieval
    town = ids.get("town", "")
    for slot, ptype in (spec.get("at") or {}).items():
        nid = ids.get(slot, "")
        if slot in PERSON_SLOTS and nid and nid != ids.get(slot + "_role") and town:
            places = [pid for pid in retrieval.town_places(world, town) if world.places[pid].type == ptype]
            if places:
                out["cast"][nid] = rng.choice(places)
    return out


def street_now(state: dict, world, place_id: str, now: int) -> tuple[dict | None, dict]:
    """What the running situations here have the streets doing: a doings override in a moment's shape for this place (the first that
    has one), and the cast placed, town-wide: {npc id: place id}."""
    from engine import pulse
    town = pulse.town_of(world, place_id)
    over, cast = None, {}
    for th in state.get("threads", []):
        if th["status"] != "active" or not th.get("streets"):
            continue
        tt = th.get("town") or pulse.town_of(world, th["place"])
        if tt != town and th["place"] not in (place_id, town):
            continue
        st = th["streets"][th["stage"]] if th["stage"] < len(th["streets"]) else None
        if not st:
            continue
        cast.update(st.get("cast") or {})
        d = st.get("doings") or {}
        mine = {"all": d.get("all", "") if place_id in (th["place"], tt) else "", "roles": dict(d.get("roles") or {})}   # everyone: in the streets and at the situation's own place
        if over is None and (mine["all"] or mine["roles"]):
            over = {"doings": mine}
    return over, cast


def scene_shape(th: dict):
    """(f357) The moment shape a situation's current stage names, with the situation's own words as its brief and its written fallback;
    None when the stage names none."""
    from engine import moments
    st = (th.get("streets") or [None] * 99)[th["stage"]] if th.get("streets") and th["stage"] < len(th["streets"]) else None
    sid = (st or {}).get("scene", "")
    base = next((s for s in moments.M.get("shapes") or [] if s["id"] == sid), None) if sid else None
    if not base:
        return None
    shape = dict(base)
    stage = th["stages"][th["stage"]]["description"]
    d = (st or {}).get("doings") or {}
    shape["brief"] = f"{stage} It is part of a situation the town knows as: {th['title']}. " + base.get("brief", "")
    shape["written"] = {"title": th["title"], "line": stage, "memory": th["title"],
                        "doings": ([{"who": "everyone", "doing": d["all"]}] if d.get("all") else []) + [{"who": r, "doing": x} for r, x in (d.get("roles") or {}).items()]}
    shape["visitor"] = None
    return shape


# ---------- (f356) the signs of a situation in the streets, day by day

def signs_for(th: dict, day_i: int) -> str:
    """The sign of an engine-built situation on its day_i-th day of the current stage (1 = the second day): one of its kind's lines in
    turn, filled with the situation's own words, or '' on the first day, for a model-written one, or when none fills."""
    if day_i < 1 or th.get("made_by") != "engine" or not th.get("words"):
        return ""
    lines = (T.get("signs") or {}).get(kind_of(th.get("template") or th.get("kind") or ""), [])
    filled = [x for x in (fill(l, th["words"]) for l in lines) if x]
    return filled[(day_i - 1) % len(filled)] if filled else ""


# ---------- the re-telling, when the player comes where it is

def untold(th: dict) -> dict:
    """The lines of a thread nothing has copied yet: stages not yet advanced to (the first, while it is current), the fallout, the truth,
    the clues not yet found and not in anyone's head (a word door's first clue is its holder's concern), the reveal, the resolution."""
    stages = [i for i in range(len(th["stages"])) if i > th["stage"] or (i == 0 and th["stage"] == 0)]
    clues = [i for i, c in enumerate(th.get("clues", [])) if not c["found"] and not (i == 0 and th.get("door") == "word")]
    return {"stages": stages, "clues": clues, "fallout": th["status"] == "active", "truth": not th.get("revealed"),
            "reveal": bool(th.get("reveal")) and not th.get("revealed"), "resolution": True}


def tell(store, world, state: dict, th: dict, t: int) -> bool:
    """One model call re-tells an engine-built thread's untold lines in the world's own words, and marks it told. False when nothing was
    changed (nothing left to tell, the model failed, or tried too lately). The templated lines stand whenever the model does not."""
    from engine import pulse_prompts as pp, truth
    from llm.contracts import ThreadTelling
    from llm.gateway import LLMError, generate
    if th.get("made_by") != "engine" or th.get("told"):
        return False
    retry = T.get("telling", {}).get("retry_hours", 12) * 60
    if t - th.get("told_at", -10 ** 9) < retry:
        return False
    th["told_at"] = t
    u = untold(th)
    if not u["stages"] and not u["clues"] and not u["truth"]:
        th["told"] = True
        return False
    words = th.get("words", {})
    parts = [f"TITLE (keep it): {th['title']}", f"PLACE: {world.places[th['place']].name}" if th["place"] in world.places else "",
             f"KIND: {th.get('kind', '')}, {th['tier']}, severity {th.get('severity', 2)} of 5",
             "THE PARTS: " + "; ".join(f"{k}: {v}" for k, v in words.items() if k in ("town", "wild", "creature", "creatures", "role", "role2", "road", "neighbour", "season"))]
    for i in u["stages"]:
        parts.append(f"STAGE {u['stages'].index(i) + 1}: {th['stages'][i]['description']}")
    if u["fallout"]:
        parts.append(f"FALLOUT: {th['fallout']['description']}")
    if u["truth"] and th.get("truth"):
        parts.append(f"TRUTH: {th['truth']}")
    for i in u["clues"]:
        c = th["clues"][i]
        who = c.get("holder", "")
        if store.npc_exists(who):
            who = store.load_npc(who).role
        parts.append(f"CLUE {u['clues'].index(i) + 1} (the {who.replace('_', ' ')} says): {c['text']}")
    if u["reveal"]:
        parts.append(f"REVEAL: {th['reveal']}")
    if th.get("resolution"):
        parts.append(f"RESOLUTION: {th['resolution']}")
    parts.append("PLACES: " + ", ".join(sorted(k for k, v in world.places.items() if v.type != "road")))
    parts.append("CREATURES: " + ", ".join(sorted({c.name for c in world.bestiary.values()}))[:3000])
    shape = {"stages": [f"<STAGE {n + 1} re-told>" for n in range(len(u["stages"]))], "fallout": "<FALLOUT re-told>" if u["fallout"] else "",
             "truth": "<TRUTH re-told>" if u["truth"] and th.get("truth") else "", "clues": [f"<CLUE {n + 1} re-told>" for n in range(len(u["clues"]))],
             "reveal": "<REVEAL re-told>" if u["reveal"] else "", "resolution": "<RESOLUTION re-told>" if th.get("resolution") else ""}
    import json as _json
    parts.append("WRITE EXACTLY THIS SHAPE, every key present, one string per line given and nothing else inside any string: " + _json.dumps(shape))
    try:
        told = generate("thread_telling", pp.TELLING_SYSTEM, "\n".join(p for p in parts if p), ThreadTelling, temperature=0.9, max_tokens=900,
                        validation_context={"stages": len(u["stages"]), "clues": len(u["clues"]), "known": truth.world_words(world)})
    except LLMError as e:
        console.debug(f"threads: {th['title']} keeps its own words ({e})")
        from engine import pulselog
        pulselog.mark("retell_failed", th["title"], t, place=th["place"])                               # (f355)
        return False
    changed = False
    for n, i in enumerate(u["stages"]):
        if told.stages[n].strip():
            th["stages"][i]["description"] = told.stages[n].strip()
            changed = True
    if u["fallout"] and told.fallout.strip():
        th["fallout"]["description"] = told.fallout.strip()
        changed = True
    if u["truth"] and told.truth.strip():
        th["truth"] = told.truth.strip()
        changed = True
    for n, i in enumerate(u["clues"]):
        if told.clues[n].strip():
            th["clues"][i]["text"] = told.clues[n].strip()
            changed = True
    if u["reveal"] and told.reveal.strip():
        th["reveal"] = told.reveal.strip()
        changed = True
    if told.resolution.strip():
        th["resolution"] = told.resolution.strip()
        changed = True
    th["told"] = True
    console.debug(f"threads: {th['title']} re-told ({len(u['stages'])} stages, {len(u['clues'])} clues)")
    from engine import pulselog
    pulselog.mark("retold", th["title"], t, place=th["place"], changed=changed)                         # (f355)
    return changed


# ---------- checks

def problems(pressures: dict | None = None, effect_kinds=(), place_ids=(), creature_ids=()) -> list[str]:
    """What is wrong with data/rules/threads.yaml and the pressures that use it: a template missing a part, an effect kind the pulse cannot
    apply, a slot no one fills, a fallback that is not a template, a pressure naming a template or words that do not exist."""
    bad = []
    tpls = T.get("templates") or {}
    kinds = set(effect_kinds)

    def slots_in(text: str, where: str):
        for m in _SLOT.finditer(text or ""):
            key = m.group(1)
            if key[0].lower() + key[1:] not in SLOTS:
                bad.append(f"threads.yaml {where}: no slot called {{{key}}}")

    def lines_ok(spec, where):
        for l in (spec if isinstance(spec, list) else [spec] if spec else []):
            slots_in(l, where)

    always = {"town", "place", "region", "season", "about", "role", "role2", "good"}        # slots every place fills

    def fillable(spec, where, needs):
        """At least one line that needs only the slots this place is sure to have: else a town with no road, no neighbour or no
        creature cannot build the situation at all."""
        lines = spec if isinstance(spec, list) else [spec] if spec else []
        ok = always | set(needs) | ({"creatures"} if "creature" in needs else set())
        if lines and not any(all(m.group(1)[0].lower() + m.group(1)[1:] in ok for m in _SLOT.finditer(l)) for l in lines):
            bad.append(f"threads.yaml {where}: every line needs a slot the template does not require ({', '.join(sorted(set(needs)))})")

    for kind, lines in (T.get("signs") or {}).items():                                      # (f356) the signs, by kind
        if kind not in tpls:
            bad.append(f"threads.yaml signs: '{kind}' is not a kind with a base template")
        lines_ok(lines, f"signs {kind}")
        fillable(lines, f"signs {kind}", [])
    for kind in (T.get("kind_weights") or {}):
        if not (T.get("signs") or {}).get(kind):
            bad.append(f"threads.yaml signs: the kind '{kind}' has no sign lines")
    shape_ids = set()
    try:
        from engine import moments as _m
        shape_ids = {s["id"] for s in _m.M.get("shapes") or []}
    except Exception:
        pass
    for key, tpl in tpls.items():
        for part in ("titles", "news", "stages", "fallout"):
            if not tpl.get(part):
                bad.append(f"threads.yaml {key}: needs {part}")
        for si, st in enumerate(tpl.get("stages") or []):                                   # (f357) the streets
            for who, text in (st.get("doings") or {}).items():
                if who not in ("all",) + PERSON_SLOTS:
                    bad.append(f"threads.yaml {key} stage {si + 1} doings: '{who}' is not all, role or role2")
                lines_ok(text, f"{key} stage {si + 1} doings")
            for who, ptype in (st.get("at") or {}).items():
                if who not in PERSON_SLOTS or ptype not in STREET_PLACES:
                    bad.append(f"threads.yaml {key} stage {si + 1} at: a cast slot (role, role2) and a kind of place in a town ({', '.join(STREET_PLACES)})")
            if st.get("scene") and shape_ids and st["scene"] not in shape_ids:
                bad.append(f"threads.yaml {key} stage {si + 1} scene: '{st['scene']}' is not a moment shape")
        kind = tpl.get("kind") or key
        if kind not in tpls or (tpls[kind].get("kind") or kind) != kind:
            bad.append(f"threads.yaml {key}: its kind '{kind}' has no base template of that name")
        if "weight" in tpl and (not isinstance(tpl["weight"], (int, float)) or tpl["weight"] <= 0):
            bad.append(f"threads.yaml {key}: weight must be a positive number")
        needs = tpl.get("needs") or []
        fillable(tpl.get("titles"), f"{key} titles", needs); fillable(tpl.get("news"), f"{key} news", needs)
        for si, st in enumerate(tpl.get("stages") or []):
            fillable(st.get("lines"), f"{key} stage {si + 1}", needs)
        fillable((tpl.get("fallout") or {}).get("lines"), f"{key} fallout", needs)
        lines_ok(tpl.get("titles"), f"{key} titles"); lines_ok(tpl.get("news"), f"{key} news")
        for n in tpl.get("needs", []):
            if n not in SLOTS:
                bad.append(f"threads.yaml {key} needs: no slot called {n}")
        fb = tpl.get("fallback")
        if fb and fb not in tpls:
            bad.append(f"threads.yaml {key}: fallback '{fb}' is not a template")
        if tpl.get("needs") and not fb:
            bad.append(f"threads.yaml {key}: a template with needs must name a fallback")
        for si, st in enumerate(tpl.get("stages") or []):
            lines_ok(st.get("lines"), f"{key} stage {si + 1}")
            for e in st.get("effects", []) + (tpl.get("fallout") or {}).get("effects", []):
                if kinds and e.get("kind") not in kinds:
                    bad.append(f"threads.yaml {key}: effect kind '{e.get('kind')}' is not one the pulse applies")
                for k in ("place", "npc", "other"):
                    if k in e and e[k] not in SLOTS:
                        bad.append(f"threads.yaml {key}: effect {e.get('kind')} names the slot '{e[k]}', which does not exist")
                lines_ok(e.get("text"), f"{key} effect {e.get('kind')}")
        lines_ok((tpl.get("fallout") or {}).get("lines"), f"{key} fallout")
        for part in ("resolution", "truth", "reveal", "abouts"):
            lines_ok(tpl.get(part), f"{key} {part}")
        for c in tpl.get("clues") or []:
            if c.get("holder") not in PERSON_SLOTS:
                bad.append(f"threads.yaml {key}: a clue's holder must be role or role2")
            lines_ok(c.get("lines"), f"{key} clue")
        for p in tpl.get("paths") or []:
            if p.get("kind") not in ("kill", "persuade", "find", "contract"):
                bad.append(f"threads.yaml {key}: path kind '{p.get('kind')}' is not kill, persuade, find or contract")
            if p.get("kind") in ("persuade", "find") and p.get("target") not in SLOTS:
                bad.append(f"threads.yaml {key}: a {p.get('kind')} path's target must be a slot")
            lines_ok(p.get("name"), f"{key} path"); lines_ok(p.get("how"), f"{key} path")
        cs = tpl.get("contract")
        if cs and (cs.get("kind") not in ("hunt", "gather") or cs.get("what") not in ("creature", "good")):
            bad.append(f"threads.yaml {key}: a contract is hunt (what: creature) or gather (what: good)")
    for k in T.get("kind_weights") or {}:
        if k not in tpls:
            bad.append(f"threads.yaml kind_weights: '{k}' is not a template")
    if set(T.get("severity_scale") or {}) != {0, 1, 2, 3, 4, 5}:
        bad.append("threads.yaml severity_scale: needs 0 to 5")
    for sc, row in (T.get("scope") or {}).items():
        if not isinstance(row, dict) or not row.get("groups"):
            bad.append(f"threads.yaml scope {sc}: needs groups")
    for pr in (pressures or {}).values():
        tkey = pr.get("template") if isinstance(pr, dict) else pr.template
        wds = (pr.get("words") if isinstance(pr, dict) else pr.words) or {}
        pid = pr.get("id") if isinstance(pr, dict) else pr.id
        if tkey and tkey not in tpls:
            bad.append(f"pressures.yaml {pid}: template '{tkey}' is not in threads.yaml")
        for k, v in wds.items():
            if k not in SLOTS:
                bad.append(f"pressures.yaml {pid}: words names the slot '{k}', which does not exist")
            elif k in PLACE_SLOTS and place_ids and v not in place_ids:
                bad.append(f"pressures.yaml {pid}: words {k}: '{v}' is not a place")
            elif k == "creature" and creature_ids and v not in creature_ids:
                bad.append(f"pressures.yaml {pid}: words creature: '{v}' is not in the bestiary")
    return bad
