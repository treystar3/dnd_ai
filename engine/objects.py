"""(f592) Things in the world as saved entities (docs/design/05 section 5.2; data/rules/objects.yaml).

A thing a ruling makes for an attempt is an entity of kind `object` (lifecycle in data/rules/lifecycles.yaml), ref
`object:<place>:<slug>`, lying at its place (`here`), carried by a character (`carried`, the owner its id), hidden or broken where it
lies; destroyed or gone, its row is deleted. The place keeps its words as a mark while it lies there.
Its tags (cover, heavy, flammable, ...) are read from the words of its name and what it is, so a ruling can be checked against what a
thing can do. Unowned things the world made are capped per place and fade when nobody touches them; carried ones are capped per
character. Every function takes the character's id, never the one player.
"""
from __future__ import annotations

import re
from pathlib import Path

from core import yamlio
from core.models import Entity
from engine import entities

O = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "objects.yaml").read_text(encoding="utf-8"))
LYING = ("here", "broken")                     # what can be seen where it lies (a hidden thing is found first)
_STOP = {"the", "a", "an", "of", "some", "my", "that", "this", "it", "up", "pick", "take", "grab", "lift", "and", "to", "from"}


def _words(text: str) -> set[str]:
    return {w.rstrip("s") if len(w) > 3 else w for w in re.findall(r"[a-z]+", (text or "").lower()) if w not in _STOP}


def tags_for(name: str, what: str = "") -> list[str]:
    """What a thing can be used as or for, by the words of its name and what it is (objects.yaml tags)."""
    words = _words(f"{name} {what}")
    return [t for t, ws in (O.get("tags") or {}).items() if words & {w.rstrip("s") for w in ws}]


_COUNTS = r"(?:the|a|an|some|one|two|three|four|five|six|several|a few|a pair of|\d+)"


def name_of(name: str) -> str:
    """'the' and what the thing is, with the article or count it came with taken off: 'some salt' is 'the salt'."""
    bare = re.sub(rf"^(?:{_COUNTS}\s+)+", "", (name or "").strip(), flags=re.I).strip()
    return f"the {bare}" if bare else "the thing"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", re.sub(r"^(the|a|an|some)\s+", "", (name or "").strip().lower())).strip("_")[:40] or "thing"


def make(store, place: str, name: str, what: str = "", made_by: str = "ruled", minute: int = 0, part: str = "", owner: str = "",
         mark: str = "") -> Entity:
    """A thing, kept where it lies; a second of the same name at the same place gets its own ref. Unowned ones past the place's cap go,
    the oldest untouched first. `mark`: the words the place keeps of it (its marks), taken off when it leaves."""
    base = f"object:{place}:{_slug(name_of(name))}"
    ref, n = base, 1
    while store.load_entity(ref) is not None:
        n += 1
        ref = f"{base}:{n}"
    name = name_of(name)
    e = entities.begin(store, "object", ref, name, minute, place=place, owner=owner,
                       data={"what": (what or "").strip(), "tags": tags_for(name, what), "made_by": made_by, "part": part,
                             "touched": minute, "how": made_by, "mark": mark})
    trim(store, place, minute)
    return store.load_entity(ref) or e


def _unmark(store, e) -> None:
    """A thing gone from where it was made takes its words off that place, so no passage tells it lying there still; words another
    thing lying there shares stay."""
    mark, place = e.data.get("mark", ""), e.place
    e.data["mark"] = ""
    if not mark or not place:
        return
    if any(o.ref != e.ref and (o.data.get("mark") or "").lower() == mark.lower() for o in here(store, place)):
        return
    st = store.load_place(place)
    kept = [m for m in st.marks if m.lower() != mark.lower()]
    if kept != st.marks:
        st.marks = kept
        store.save_place(st)


def lying_unmarked(store, place: str, now: int | None = None) -> list[str]:
    """The things lying at a place that its marks do not tell (set down there, or their words since dropped from the place), as the
    narrator is given them."""
    marks = {m.lower() for m in store.load_place(place).marks}
    return [f"{e.name}{' (broken)' if e.state == 'broken' else ''}" + (f": {e.data['what']}" if e.data.get("what") else "")
            for e in here(store, place, now) if (e.data.get("mark") or "").lower() not in marks]


def _faded(e, now: int) -> bool:
    return (not e.owner and e.data.get("made_by") != "authored"
            and now - int(e.data.get("touched", e.since)) >= int(O["fade_days"]) * 1440)


def here(store, place: str, now: int | None = None) -> list[Entity]:
    """The things lying at a place that can be seen, oldest first; with `now`, never one that has faded (trim takes its row later)."""
    rows = store.find_entities(kind="object", state=LYING, place=place)
    return [e for e in rows if not _faded(e, now)] if now is not None else rows


def carried(store, cid: str) -> list[Entity]:
    """The things a character carries that are no item of the pack."""
    return store.find_entities(kind="object", state="carried", owner=cid)


def find(things: list, phrase: str):
    """The thing a phrase means among these, by the words of its name, then of what it is; None when none is meant."""
    words = _words(phrase)
    if not words:
        return None
    best, score = None, 0
    for e in things:
        own, said = _words(e.name), _words(e.data.get("what", ""))
        s = 3 * len(words & own) + len(words & said - own)
        if s > score:
            best, score = e, s
    return best if score >= 3 else None


def take(store, e, cid: str, minute: int) -> str:
    """A character picks a thing up: '' when carried, else why not ('heavy', 'full')."""
    if "heavy" in e.data.get("tags", []):
        return "heavy"
    if len(carried(store, cid)) >= int(O["carried_most"]):
        return "full"
    _unmark(store, e)
    e.owner = cid
    e.data["touched"] = minute
    entities.move(store, e, "carried", minute, "picked up")
    return ""


def drop(store, e, place: str, minute: int) -> None:
    """A character sets a thing down where they stand: it lies there, nobody's (the cap and the fading apply to it again)."""
    e.owner, e.place = "", place
    e.data["touched"] = minute
    entities.move(store, e, "here", minute, "set down")
    trim(store, place, minute)


def change(store, e, to: str, minute: int, why: str = "") -> None:
    """A thing broken, hidden, found or destroyed, as its lifecycle allows (ValueError when it does not; picking up is take()).
    Destroyed or gone, its row is deleted: nothing of it is left to find."""
    if to == "carried":
        raise ValueError("a thing is carried by take(), which names who carries it")
    if to not in (entities.L["object"].get("moves") or {}).get(e.state, []):
        raise ValueError(f"an object cannot go from {e.state} to {to}")
    if to in ("gone", "destroyed"):
        _unmark(store, e)
    e.data["touched"] = minute
    entities.move(store, e, to, minute, why)
    if entities.final(e):
        store.delete_entity(e.ref)


def trim(store, place: str, minute: int) -> int:
    """Unowned, unauthored things at a place: those untouched past fade_days go, then the oldest untouched past per_place. Returns how
    many went."""
    rows = [e for e in store.find_entities(kind="object", state=("here", "hidden", "broken"), place=place)
            if not e.owner and e.data.get("made_by") != "authored"]
    gone = [e for e in rows if _faded(e, minute)]
    keep = sorted((e for e in rows if e not in gone), key=lambda e: (int(e.data.get("touched", e.since)), e.ref))
    gone += keep[:max(0, len(keep) - int(O["per_place"]))]
    for e in gone:
        change(store, e, "gone", minute, "faded")
    return len(gone)


def problems() -> list[str]:
    """(f592) objects.yaml's shape: tags as lists of words, the caps whole numbers above 0, and the lifecycle's states the code uses."""
    bad = []
    for t, ws in (O.get("tags") or {}).items():
        if not (isinstance(ws, list) and ws and all(isinstance(w, str) and w for w in ws)):
            bad.append(f"objects.yaml tags.{t}: needs a list of words")
    for k in ("per_place", "carried_most", "fade_days"):
        v = O.get(k)
        if not (isinstance(v, int) and not isinstance(v, bool) and v > 0):
            bad.append(f"objects.yaml {k}: needs a whole number above 0")
    if "heavy" not in (O.get("tags") or {}):
        bad.append("objects.yaml tags: needs 'heavy' (a heavy thing is never carried off)")
    spec = entities.L.get("object") or {}
    need = {"here", "carried", "hidden", "broken", "destroyed", "gone"}
    if not need <= set(spec.get("states") or ()):
        bad.append(f"lifecycles.yaml object: needs the states {sorted(need)}")
    return bad
