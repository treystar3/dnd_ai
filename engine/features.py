"""(f394) The parts of a place: where a player can go inside it (data/rules/features.yaml; GOAL.md: a world of places, not stages).

A wild place used to be a stage set: its description named "a second beach of glowing tidepools behind the first chamber" and "the dry
chamber", and Bumbo Claat walked to both and found walls the narrator made up, because nothing in the game knew they were there. A part
of a place is now a registry entity (kind feature, ref feature:<place>:<slug>): a name, a kind, what is there (`what`), the parts it
links to, how deep it lies, when it is open (the tide), and what it holds, rolled by the engine once, seeded.

Where parts come from, most authoritative first: the place's own list (places.yaml `features:`); the templates, which give a wild place
without one its first parts on the first visit; growth, a part at a time outward from where the player stands, when they go further in;
and adoption, when a passage of the narrator names one, or the player goes to one a place like this would have. Budgets keep the pace.
The player stands at a part (PlayerState.spot); everything here is the engine's, the model only tells it."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
F = yaml.safe_load((ROOT / "data" / "rules" / "features.yaml").read_text(encoding="utf-8"))
KIND_OF: dict[str, str] = {w: k for k, spec in F["kinds"].items() for w in spec["words"]}
PLAIN = set(F["plain"])
STOP = {"the", "a", "an", "of", "to", "in", "into", "at", "on", "by", "from", "and", "toward", "towards", "back", "over", "through",
        "go", "walk", "head", "move", "darkest", "deepest", "furthest", "far", "pocket", "end", "edge", "threshold", "mouth", "part",
        "corner", "this", "that", "there", "here", "its", "their", "with", "where", "which", "some", "other"}
DEEPER = re.compile(r"\b(deeper|further|farther|inner|inside|on in|further in|beyond|the back of|explore|explore further|go on|keep going)\b", re.I)
NATURAL = {"coast", "cave", "ruin", "hollow", "grove", "spring", "shrine", "overlook", "ford", "camp", "wilds", "forest", "swamp", "mine",
           "hills", "mountain", "lake", "river", "marsh", "moor", "wood", "woods", "beach", "valley", "pass", "glade", "barrow", "crypt"}


def leaving(text: str, place) -> bool:
    """'beyond the caves', 'outside the wood', 'away from here': the words are about somewhere other than this place."""
    words = [w for w in re.findall(r"[a-z]+", place.name.lower()) if w not in STOP and len(w) >= 3] + ["here", "this place", "it"]
    plain = [w for w in PLAIN if w in place.name.lower() or w in ("cave", "caves", "wood", "woods")]
    names = "|".join(re.escape(w) for w in words + plain)
    return bool(re.search(rf"\b(beyond|outside|past|away from|out of|leave|leaving|elsewhere than)\s+(the\s+)?({names})\b", (text or "").lower()))


def ref_of(place_id: str, slug: str) -> str:
    return f"feature:{place_id}:{slug}"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower().removeprefix("the ")).strip("_")[:40] or "part"


def grows_here(place) -> bool:
    """Whether a place is made of parts: anything wild, or with its own list; never a town or a building in one."""
    if place is None or place.type in ("road", "dungeon"):
        return False
    return bool(place.features) or bool(place.danger) or place.type in NATURAL or (place.biome not in (None, "urban") and not place.parent
                                                                                       and place.type not in ("town", "city", "village"))


def here(store, place_id: str) -> list:
    return [e for e in store.find_entities(kind="feature", place=place_id) if e.state != "gone"]


def depth(e) -> int:
    return int(e.data.get("depth", 0))


# ---------- the tide

def tide(minutes: int) -> tuple[str, int]:
    """('low' | 'high', minutes until it turns)."""
    T = F["tide"]
    phase = (minutes - T["first_high"]) % T["period"]
    mid = T["period"] / 2
    if abs(phase - mid) <= T["low_half_width"]:
        return "low", int(mid + T["low_half_width"] - phase)
    until = (mid - T["low_half_width"] - phase) if phase < mid else (T["period"] - phase + mid - T["low_half_width"])
    return "high", int(until)


def low_tide_text(minutes: int) -> str:
    """When the water is next out, in plain words: 'from about 10 in the morning until about 3 in the afternoon'."""
    from engine import clock
    state, until = tide(minutes)
    start = minutes if state == "low" else minutes + until
    end = start + (until if state == "low" else 2 * F["tide"]["low_half_width"])

    def at(m: int) -> str:
        h = (m // 60) % 24
        return f"about {h % 12 or 12} {'in the morning' if h < 12 else 'in the afternoon' if h < 18 else 'at night'}"
    return ("now, until " + at(end)) if state == "low" else f"from {at(start)} until {at(end)}"


def now_of(e, minutes: int) -> dict[str, int]:
    """(f395) What an attempt has made of this part that still holds: {state: until} (0: until something undoes it)."""
    return {k: int(u) for k, u in (e.data.get("now") or {}).items() if k in F["becomes"] and (not u or int(u) > minutes)}


def change(ws, e, becomes: str, degree: str = "success") -> str:
    """(f395) A part made different by an attempt (features.yaml becomes): kept on the part, told on the turn. The line told, or ''."""
    from engine import ledger
    spec = F["becomes"].get(becomes)
    if spec is None or e is None:
        return ""
    now = {k: u for k, u in (e.data.get("now") or {}).items() if k not in spec.get("undoes", []) and k != becomes}
    hours = spec.get("hours", 0) / (2 if degree == "partial" else 1)
    if spec.get("shows"):
        now[becomes] = int(ws.minutes + hours * 60) if hours else 0
    e.data["now"] = now
    ws.store.save_entity(e)
    said = f"{e.name[0].upper() + e.name[1:]} is {spec['shows'] or becomes} now" + (", for a while" if spec.get("shows") and hours else "") + "."
    ledger.add("changed", ref=e.ref, name=e.name, to=becomes, say=said)
    return said


def open_now(e, minutes: int) -> tuple[bool, str]:
    """Whether the way to this part is open now; when not, why and when it opens, in the world's words."""
    for k, until in now_of(e, minutes).items():
        if F["becomes"][k].get("shuts"):
            from engine import clock
            return False, (f"The way to {e.name} is {F['becomes'][k]['shows']}"
                           + (f"; it should be passable again in about {clock.describe_duration(max(15, round((until - minutes) / 15) * 15))}." if until else "."))
    if e.data.get("open") == "low_tide":
        state, until = tide(minutes)
        if state == "high":
            from engine import clock
            return False, (f"The tide is in over the way to {e.name}; the water should be out again in about "
                           f"{clock.describe_duration(max(15, round(until / 15) * 15))}.")
    return True, ""


# ---------- what a part holds

def roll_holds(world, store, place, kind: str, rng: random.Random, want: str = "") -> dict:
    """What a new part holds, by weight: a safe place grows no lairs or hazards; a lair is one of the place's own creatures."""
    from engine import encounters
    weights = dict(F["holds"])
    if not place.danger:
        weights.pop("lair", None); weights.pop("hazard", None)
    pick = want or rng.choices(list(weights), weights=list(weights.values()))[0]
    if pick == "lair":
        roster = encounters.ensure_roster(store, world, place.id) if place.danger else []
        if not roster:
            return {"holds": "none"}
        return {"holds": "lair", "creature": rng.choice(roster)}
    if pick == "cache":
        return {"holds": "cache", "sign": rng.choice(F["caches"])}
    if pick == "clue":
        return {"holds": "clue", "clue": rng.choice(F["clues"])}
    if pick == "hazard":
        h = rng.choice(F["hazards"])
        return {"holds": "hazard", "hazard": h["what"], "check": h["check"], "cost": h["cost"]}
    if pick == "resource":
        from engine import inventory
        goods = [g.id for g in inventory.GOODS.values() if place.biome and place.biome in (g.grows_in or [])]
        return {"holds": "resource", "good": rng.choice(goods)} if goods else {"holds": "none"}
    return {"holds": "none"}


# ---------- making parts

def register(ws, place_id: str, name: str, kind: str, what: str, state: str, origin: str, depth_: int = 0, links: list | None = None,
             extra: dict | None = None, rng: random.Random | None = None):
    """A part, kept: in the registry, in its first state, published. What it holds is rolled now unless the spec says."""
    from engine import entities, ledger
    place = ws.world.places[place_id]
    ref = ref_of(place_id, slug(name))
    old = ws.store.load_entity(ref)
    if old is not None:
        return old
    rng = rng or random.Random(f"{ws.store.meta.seed}:{ref}")
    data = {"kind": kind, "what": what, "depth": depth_, "links": list(links or []), "origin": origin, "made": ws.minutes}
    data.update(extra or {})
    for k, v in roll_holds(ws.world, ws.store, place, kind, rng, want=data.get("holds", "")).items():
        data.setdefault(k, v)                                     # what the place's own list says is kept; the roll fills the rest
    e = entities.begin(ws.store, "feature", ref, name, ws.minutes, place=place_id, data=data)
    if state != "unseen":
        e = entities.move(ws.store, e, state, ws.minutes, origin)
    for other in data["links"]:                                    # a link goes both ways
        o = ws.store.load_entity(other)
        if o is not None and ref not in o.data.get("links", []):
            o.data["links"] = o.data.get("links", []) + [ref]
            ws.store.save_entity(o)
    if origin not in ("authored", "first_visit"):
        ledger.add("made", ref=ref, name=name, how=origin, say=f"{name} is real now: {what}")
    return e


def ensure(ws, place_id: str) -> None:
    """A place's parts, made once: its own list, or the templates' first few for a wild place without one."""
    place = ws.world.places.get(place_id)
    if not grows_here(place) or here(ws.store, place_id):
        return
    if place.features:
        refs = {spec["id"]: ref_of(place_id, slug(spec["name"])) for spec in place.features}
        for spec in place.features:
            extra = {k: spec[k] for k in ("open", "clue", "tags", "entry") if k in spec}
            if spec.get("holds") or spec.get("entry"):
                extra["holds"] = spec.get("holds") or "none"          # the way in holds nothing unless the place says
            register(ws, place_id, spec["name"], spec["kind"], spec["what"], "known", "authored",
                     depth_=0 if spec.get("entry") else 1, links=[refs[l] for l in spec.get("links", []) if l in refs], extra=extra)
        return
    rng = random.Random(f"{ws.store.meta.seed}:{place_id}:first")
    entry = None
    for i in range(F["budget"]["first_visit"]):
        e = grow(ws, place_id, entry, rng, origin="first_visit", state="known" if i == 0 else "unseen")
        if e is None:
            break
        if i == 0:
            e.data["entry"] = True
            ws.store.save_entity(e)
            entry = e


def kinds_here(place) -> list[str]:
    return F["grows"].get(place.biome or "", F["grows"]["default"])


def room(ws, place_id: str) -> bool:
    """Whether the place may grow another part now: its whole budget, and its pace this hour."""
    have = here(ws.store, place_id)
    if len(have) >= F["budget"]["most"]:
        return False
    lately = [e for e in have if e.data.get("origin") not in ("authored", "first_visit") and ws.minutes - int(e.data.get("made", 0)) < 60]
    return len(lately) < F["budget"]["per_hour"]


def grow(ws, place_id: str, frm, rng: random.Random, origin: str = "grown", state: str = "known", deeper: bool = True):
    """A new part of the place, linked to `frm` and a step deeper: of a kind this place has, named for how it looks, holding what the
    engine rolls. None when the place is full or has grown its share this hour."""
    place = ws.world.places[place_id]
    if origin != "first_visit" and not room(ws, place_id):
        return None
    kinds = kinds_here(place)
    if deeper:
        kinds = [k for k in kinds if F["kinds"][k]["deeper"]] or kinds
    taken = {e.name for e in here(ws.store, place_id)}
    for _ in range(12):
        kind = rng.choice(kinds[:3] * 2 + kinds)                  # the first kinds listed are the likelier
        noun = F["kinds"][kind]["words"][0]
        name = f"the {rng.choice(F['looks'].get(kind, ['hidden']))} {noun}"
        if name not in taken:
            break
    else:
        return None
    d = depth(frm) + 1 if frm is not None else 0
    what = (f"A {name.removeprefix('the ')} {'further in, past ' + frm.name if frm is not None else 'at the edge of ' + place.name}.")
    return register(ws, place_id, name, kind, what, state, origin, depth_=d, links=[frm.ref] if frm is not None else [], rng=rng)


def adopt(ws, place_id: str, name: str, kind: str, origin: str, frm=None):
    """A part named into being (by the narrator, or by the player going to one a place like this would have): kept, within the budget.
    None when the place is full."""
    if not room(ws, place_id):
        return None
    frm = frm or spot_of(ws)
    what = f"{name[0].upper() + name[1:]}, part of {ws.world.places[place_id].name}."
    return register(ws, place_id, name, kind, what, "known", origin, depth_=depth(frm) + (1 if F["kinds"][kind]["deeper"] else 0) if frm else 1,
                    links=[frm.ref] if frm is not None else [])


# ---------- reading words

def named_part(phrase: str) -> tuple[str, str] | None:
    """('the rear tunnel', 'tunnel') for a phrase that names a part of a place by a kind's word with a word of its own before it; None for
    'the cave', 'the walls', a bare 'tunnel'."""
    words = re.findall(r"[a-z'-]+", (phrase or "").lower())
    for i in range(len(words) - 1, -1, -1):
        w = words[i]
        kind = KIND_OF.get(w)
        if not kind or w in PLAIN:
            continue
        mods = []
        for m in reversed(words[max(0, i - 2):i]):
            if m in STOP or m in KIND_OF or m in PLAIN or len(m) < 3:
                break
            mods.insert(0, m)
        if not mods:
            return None
        return "the " + " ".join(mods + [w]), kind
    return None


def find(ws, phrase: str, place_id: str = ""):
    """The part of this place a phrase means, or None: by the words of its name, its kind's words breaking ties."""
    place_id = place_id or ws.player.location
    words = {w for w in re.findall(r"[a-z]+", (phrase or "").lower()) if w not in STOP and len(w) >= 3}
    if not words:
        return None
    best, score = None, 0
    for e in here(ws.store, place_id):
        own = {w for w in re.findall(r"[a-z]+", e.name.lower()) if w not in STOP}
        kind_words = set(F["kinds"].get(e.data.get("kind", ""), {}).get("words", []))
        tags = set(e.data.get("tags", []))
        said = {w for w in re.findall(r"[a-z]+", e.data.get("what", "").lower()) if len(w) >= 4 and w not in STOP}
        s = (3 * len(words & (own - kind_words)) + len(words & (own & kind_words)) + (1 if words & kind_words else 0)
             + 2 * len(words & tags) + len(words & said - own - tags))       # what it is and how it looks count too: 'the glowing pools'
        if s > score:
            best, score = e, s
    return best if score >= 3 or (best is not None and score >= 2 and len(words) <= 2) else None


def spot_of(ws):
    s = getattr(ws.player, "spot", "") or ""
    e = ws.store.load_entity(s) if s.startswith(f"feature:{ws.player.location}:") else None
    return e if e is not None and e.state != "gone" else None


def entry_of(ws, place_id: str):
    parts = here(ws.store, place_id)
    return next((e for e in parts if e.data.get("entry")), None) or next((e for e in parts if depth(e) == 0), None)


# ---------- what writers are told

def lines(ws) -> list[str]:
    """The parts of this place the player knows, for the narrator and the interpreter: where they stand, what each is, what is closed."""
    at = spot_of(ws)
    out = []
    for e in sorted(here(ws.store, ws.player.location), key=depth):
        if e.state == "unseen":
            continue
        ok, why = open_now(e, ws.minutes)
        shows = [F["becomes"][k]["shows"] for k in now_of(e, ws.minutes) if F["becomes"][k].get("shows") and not F["becomes"][k].get("shuts")]
        out.append(f"{e.name}{' (where the player stands)' if at is not None and e.ref == at.ref else ''}: {e.data.get('what', '')}"
                   + (f" Now {', '.join(shows)}." if shows else "") + ("" if ok else f" Closed now: {why}"))
    return out


def candidates(ws) -> list[tuple[str, str]]:
    """(ref, label) of the parts of this place the player could go to, for the interpreter's PLACES."""
    out = []
    for e in here(ws.store, ws.player.location):
        if e.state == "unseen":
            continue
        out.append((e.ref, f"{e.name} (a part of {ws.place.name})"))
    return out


def problems(world) -> list[str]:
    bad = []
    for k, spec in F["becomes"].items():
        for u in spec.get("undoes", []):
            if u not in F["becomes"]:
                bad.append(f"features.yaml becomes {k}: undoes '{u}', which is not listed")
    for k in F["kinds"]:
        if k not in F["looks"]:
            bad.append(f"features.yaml: kind '{k}' has no looks to name it by")
    for biome, kinds in F["grows"].items():
        for k in kinds:
            if k not in F["kinds"]:
                bad.append(f"features.yaml grows {biome}: '{k}' is no kind")
    for p in world.places.values():
        ids = {s.get("id") for s in p.features}
        for s in p.features:
            if s.get("kind") not in F["kinds"]:
                bad.append(f"places.yaml {p.id}: part '{s.get('id')}' has no known kind ({s.get('kind')})")
            for l in s.get("links", []):
                if l not in ids:
                    bad.append(f"places.yaml {p.id}: part '{s.get('id')}' links to '{l}', which is not one of its parts")
            for k in s.get("now", []):
                if k not in F["becomes"]:
                    bad.append(f"places.yaml {p.id}: part '{s.get('id')}' starts '{k}', which features.yaml becomes does not list")
            if s.get("open") not in (None, "low_tide"):
                bad.append(f"places.yaml {p.id}: part '{s.get('id')}' opens at '{s.get('open')}', which the engine does not know")
    return bad
