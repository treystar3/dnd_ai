"""Draft a profile for each town that has none (f317): data/world/towns/<id>.yaml, written by the model from what the world already says
of the town - its places and what is visible there, who lives there, its pressures, the lore its people know, its region - in the shape
engine/towns.py reads (see data/world/towns/parth.yaml for the shape, and data/rules/towns.yaml for what a profile does).

Every draft is checked against the map the way the loader checks a profile (world/loader._check_towns): a landmark must stand at one of
the town's places, an anchor's role must be one the town has, the scale and guard words must be ones the truth layer knows, the festivals
must be on the calendar. What does not fit is dropped from the draft and said. The file is a DRAFT: read it, cut what is wrong, keep what
is good. Nothing here is final until you have read it.

    python tools/draft_towns.py                 every town without a profile
    python tools/draft_towns.py --town kelpmoor  one town (--overwrite to replace a profile that exists)
    python tools/draft_towns.py --dry           show the drafts without writing them

Needs the model (Ollama) running, like the game."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml
from pydantic import BaseModel, field_validator

from world.loader import load_world, Town, _check_towns, _chain

SYSTEM = """You write the profile of one town in a fantasy world, from what the world already says of it. The profile gives the town an
identity the game can use: a character the narrator colours scenes with, named things people can point to, quarters they give directions
by, the few people who make the town what it is, the trouble underneath that situations grow from, a secret, and the town's own holidays.
Be specific and grounded in the material given; invent nothing that contradicts it, and nothing grand - a town's trouble is a feud, a
debt, a road, a fear, not a dark lord. Describe, never instruct. Plain words; no sayings, no morals; concrete things - trades, goods,
streets, weather, noise - never abstractions (legacy, hierarchy, grace, order).

THE TOWN'S PLACES list only the people the game has written down by name: a few. The town itself holds what its SIZE says - a village a
few hundred, a town a thousand or two, a city tens of thousands, the capital the most in the kingdom - and nearly all of them are
ordinary people: carters, washerwomen, apprentices, dockhands, soldiers, beggars, clerks, cooks. The profile is about the town as a whole,
its many first; whoever rules it, however grand, is one thread among several, never the whole cloth.

Write:
  character: one paragraph, three or four sentences: what the town is like, what it lives on, who its people mostly are and how they
    are, what sits at the edge of their talk.
  landmarks: three or four named things anyone there can point to - a bridge, a well, a gate, an old tree, a hall - each {name, where, note}:
    where is one of the ids under WHERE A LANDMARK MAY STAND, exactly as written; note is one line on what it is.
  districts: the quarters people give directions by - as many as DISTRICTS says for a place this size - short, lower case, this
    town's own: a village has a lane or two with names, a city has wards, markets, a dock quarter, a hill the rich keep to.
  anchors: the people who make the town what it is - as many as ANCHORS says for a place this size - each {role, note}: role is one
    from ROLES THE TOWN HAS, each role once; note is one line on who they are in the town - their standing, their habit, what they
    want - with no name and no he or she (the game decides both). Where the town has a monarch, they are an anchor, and so is
    whoever keeps their door.
  trouble: two or three things wrong underneath, each one sentence, grown from the PRESSURES and the LORE.
  secret: one thing the town keeps, in a sentence or two; nobody says it aloud.
  festivals: one or two holidays of the town's own, each {name, season, day, days}: season from SEASONS, day 1 to DAYS_EACH, days 1 to 3;
    not in the first ten days of spring, where the story begins.
  scale: one of SCALES, for how big and busy it is. guard: one of GUARDS, for how much of the watch is about.
  crowd: how the streets look at four times - market (the busy hours of the day), easing (the day ending), quiet (night) and empty
    (deep night) - each one plain sentence that says WHO is about and HOW MANY, in this town's own terms, with every word spelled out
    (cart drivers, not drivers). The shape: market "Carts are queueing on the bridge, the square is full of stalls, and cart drivers are
    eating in the inn."; empty "The streets are empty but for a dog and the watch." A line that names no people and no number (bells,
    lanterns, stillness, shadows) is wrong.
Write as someone who has been there would tell a friend, not as a chronicler: not "lives on the polished surface of royal favour" but
"lives on the court: half the city feeds, dresses, carts for and cleans up after the other half".
Invent no geography: rivers, roads, hills and woods are only those THE TOWN'S PLACES and NEARBY name. Names under ALREADY USED belong
to other towns; this town has its own.
Respond only with JSON matching the schema."""


class LandmarkDraft(BaseModel):
    name: str
    where: str
    note: str = ""


class AnchorDraft(BaseModel):
    role: str
    note: str = ""


class FestivalDraft(BaseModel):
    name: str
    season: str
    day: int = 1
    days: int = 1


class CrowdDraft(BaseModel):
    market: str = ""
    easing: str = ""
    quiet: str = ""
    empty: str = ""


class ProfileDraft(BaseModel):
    character: str
    landmarks: list[LandmarkDraft] = []
    districts: list[str] = []
    anchors: list[AnchorDraft] = []
    trouble: list[str] = []
    secret: str = ""
    festivals: list[FestivalDraft] = []
    scale: str = ""
    guard: str = ""
    crowd: CrowdDraft = CrowdDraft()

    @field_validator("character")
    @classmethod
    def some_character(cls, v):
        if len(v.split()) < 20:
            raise ValueError("the character needs a real paragraph")
        return v


def town_places(world, top: str) -> list:
    return [p for p in world.places.values() if _chain(world.places, p)[-1].id == top]


def used_elsewhere(world, top) -> list[str]:
    """Landmarks, districts and festivals the other towns' profiles already use."""
    out = []
    for t in world.towns.values():
        if t.id == top.id:
            continue
        out += [l.name for l in t.landmarks] + list(t.districts) + [f.name for f in t.festivals]
    return out


towns_rules = yaml.safe_load((ROOT / "data" / "rules" / "towns.yaml").read_text(encoding="utf-8"))


def districts_for(scale: str, rules: dict) -> str:
    lo, hi = rules.get("districts_by_scale", {}).get(scale, [2, 3])
    return f"{lo} to {hi}" if lo != hi else str(lo)


def anchors_for(scale: str, rules: dict) -> str:
    lo, hi = rules.get("anchors_by_scale", {}).get(scale, [3, 3])
    return f"{lo} to {hi}" if lo != hi else str(lo)


def scale_guess(top, truth: dict) -> str:
    """The scale the truth layer would give the town from its type, for the writer to start from (truth.yaml scale_by_type)."""
    return top.scale or truth["scale_by_type"].get(top.type, "village")


def request(world, top, truth: dict, pulse: dict) -> str:
    places = town_places(world, top.id)
    lines = []
    for p in sorted(places, key=lambda x: (x.id != top.id, x.name)):
        res = ", ".join(f"{k} x{v}" if v > 1 else k for k, v in p.residents.items()) or "nobody in particular"
        vis = " ".join(" ".join(v.split()) for v in p.visible)
        lines.append(f"  {p.id} - {p.name} ({p.type}): {vis} Lives here: {res}.")
    roles = sorted({r for p in places for r in p.residents})
    group = top.locals_group or ""
    lore = [" ".join(f.text.split()) for f in world.lore.values() if group and group in f.known_by]
    pressures = [p.description for p in world.pressures.values() if p.place in {q.id for q in places} | {top.region}]
    near = []
    for other, minutes in top.connects.items():
        q = world.places.get(other)
        if q:
            near.append(f"{q.name} ({q.type}, {minutes} minutes)")
    region = world.regions[top.region]
    capital = any(r.ruled_by and top.name.lower() in r.ruled_by.lower() for r in world.regions.values())
    ids = [p.id for p in sorted(places, key=lambda x: (x.id != top.id, x.name))]
    where = (f"{top.id} (the town is one place: every landmark stands at {top.id})" if len(ids) == 1 else ", ".join(ids))
    used = used_elsewhere(world, top)
    return (f"TOWN: {top.id} - {top.name} ({top.type}), in {region.name}: {' '.join(region.description.split())}"
            + (f" Ruled by {region.ruled_by}." if region.ruled_by else "")
            + (" THIS IS THE CAPITAL OF THE KINGDOM: the crown sits here, and so does everyone who feeds, serves and sells to it." if capital else "") + "\n"
            f"WORLD: {' '.join(world.summary.split())}\n"
            f"THE TOWN'S PLACES:\n" + "\n".join(lines) + "\n"
            f"WHERE A LANDMARK MAY STAND: {where}\n"
            f"ROLES THE TOWN HAS: {', '.join(roles)}\n"
            + (f"ALREADY USED (other towns'): {', '.join(used)}\n" if used else "")
            + f"NEARBY: {'; '.join(near) or 'nothing close'}\n"
            f"PRESSURES: {' '.join(pressures) or 'none written'}\n"
            f"LORE ITS PEOPLE KNOW: {' '.join(lore[:8]) or 'nothing in particular'}\n"
            f"SIZE: its scale is {scale_guess(top, truth)} unless its places say otherwise\n"
            f"DISTRICTS: {districts_for(scale_guess(top, truth), towns_rules)} quarters\n"
            f"ANCHORS: {anchors_for(scale_guess(top, truth), towns_rules)} people\n"
            f"SCALES: {', '.join(truth['crowd'])}\nGUARDS: {', '.join(truth['guard_lines'])}\n"
            f"SEASONS: {', '.join(pulse['seasons']['order'])}\nDAYS_EACH: {pulse['seasons']['days_each']}")


def fit(world, top, draft: ProfileDraft, truth: dict, pulse: dict) -> tuple[dict, list[str]]:
    """The draft cut to what the map allows, and what was cut."""
    mine = {p.id for p in town_places(world, top.id)}
    roles = {r for p in town_places(world, top.id) for r in p.residents}
    dropped = []
    out = {"id": top.id, "character": " ".join(draft.character.split())}
    marks = []
    for l in draft.landmarks:
        where = l.where if l.where in mine else top.id              # not a place of the town: it stands in the town itself
        if l.where not in mine:
            dropped.append(f"landmark '{l.name}' was at '{l.where}', not a place of the town: placed at {top.id} (change it if it belongs at one of the town's places)")
        marks.append({"name": l.name.strip(), "where": where, "note": " ".join(l.note.split())})
    out["landmarks"] = marks
    _, most = towns_rules.get("districts_by_scale", {}).get(draft.scale if draft.scale in truth["crowd"] else scale_guess(top, truth), [2, 3])
    out["districts"] = [d.strip().lower() for d in draft.districts if d.strip()][:most + 1]
    anchors = []
    _, most_anchors = towns_rules.get("anchors_by_scale", {}).get(draft.scale if draft.scale in truth["crowd"] else scale_guess(top, truth), [3, 3])
    for a in draft.anchors:
        if a.role in roles and a.role not in {x["role"] for x in anchors}:
            anchors.append({"role": a.role, "note": " ".join(a.note.split())})
        elif a.role in roles:
            dropped.append(f"anchor role '{a.role}' given twice")
        else:
            dropped.append(f"anchor role '{a.role}' (the town has no such resident)")
    if "monarch" in roles and "monarch" not in {x["role"] for x in anchors}:
        anchors.insert(0, {"role": "monarch", "note": "rules the kingdom from here"})
        dropped.append("the one who rules was missing from the anchors: added, with a note to write")
    out["anchors"] = anchors[:most_anchors + 1]
    out["trouble"] = [" ".join(t.split()) for t in draft.trouble if t.strip()][:4]
    out["secret"] = " ".join(draft.secret.split())
    fests = []
    for f in draft.festivals:
        if f.season in pulse["seasons"]["order"] and 1 <= f.day <= pulse["seasons"]["days_each"]:
            fests.append({"name": f.name.strip(), "season": f.season, "day": f.day, "days": max(1, min(3, f.days))})
        else:
            dropped.append(f"festival '{f.name}' ({f.season} {f.day}: not on the calendar)")
    out["festivals"] = fests
    if draft.scale in truth["crowd"]:
        out["scale"] = draft.scale
    elif draft.scale:
        dropped.append(f"scale '{draft.scale}' (not one of {', '.join(truth['crowd'])})")
    if draft.guard in truth["guard_lines"]:
        out["guard"] = draft.guard
    elif draft.guard:
        dropped.append(f"guard '{draft.guard}' (not one of {', '.join(truth['guard_lines'])})")
    slots = set(truth["periods"].values())
    crowd = {k: " ".join(v.split()) for k, v in draft.crowd.model_dump().items() if k in slots and v.strip()}
    if crowd:
        out["crowd"] = crowd
    return out, dropped


HEADER = """# {name} - the town's profile. DRAFTED by tools/draft_towns.py from places.yaml, pressures.yaml and lore.yaml: read it, cut what is
# wrong, keep what is good. The shape is explained in parth.yaml; what a profile does is explained in data/rules/towns.yaml.
"""


def write_profile(path: Path, data: dict, name: str) -> None:
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=130, default_flow_style=False)
    path.write_text(HEADER.format(name=name) + "\n" + body, encoding="utf-8")


def check_file(world, path: Path) -> list[str]:
    """The loader's own check, on the file just written."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    w = {"towns": {raw["id"]: Town(**raw)}, "places": world.places, "roles": world.roles}
    _check_towns(w, problems)
    return problems


def draft(world, top, truth: dict, pulse: dict, generate) -> ProfileDraft:
    return generate("town_profile", SYSTEM, request(world, top, truth, pulse), ProfileDraft, temperature=0.8, max_tokens=1800, retries=2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--town", help="one town's id")
    ap.add_argument("--overwrite", action="store_true", help="replace a profile that already exists")
    ap.add_argument("--dry", action="store_true", help="show the drafts, write nothing")
    args = ap.parse_args(argv)
    world = load_world()
    truth = yaml.safe_load((ROOT / "data" / "rules" / "truth.yaml").read_text(encoding="utf-8"))
    pulse = yaml.safe_load((ROOT / "data" / "rules" / "pulse.yaml").read_text(encoding="utf-8"))
    folder = ROOT / "data" / "world" / "towns"
    folder.mkdir(parents=True, exist_ok=True)
    towns = [p for p in world.places.values() if not p.parent and p.type in ("town", "city", "village")]
    if args.town:
        towns = [p for p in towns if p.id == args.town]
        if not towns:
            print(f"no town called '{args.town}'")
            return 1
    from llm.gateway import generate, LLMError
    done = 0
    for top in towns:
        path = folder / f"{top.id}.yaml"
        if path.exists() and not args.overwrite and not (args.town and args.dry):
            print(f"{top.name}: has a profile already ({path.name}); --overwrite to replace it")
            continue
        print(f"{top.name}: drafting...", flush=True)
        try:
            d = draft(world, top, truth, pulse, generate)
        except LLMError as e:
            print(f"  the model gave nothing usable ({e}); skipped")
            continue
        data, dropped = fit(world, top, d, truth, pulse)
        for x in dropped:
            print(f"  note: {x}")
        if args.dry:
            print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=130))
            continue
        write_profile(path, data, top.name)
        problems = check_file(world, path)
        if problems:
            print("  the loader would refuse this file; it has been removed:")
            for pr in problems:
                print(f"    - {pr}")
            path.unlink()
            continue
        done += 1
        print(f"  wrote {path.relative_to(ROOT)}: {len(data['landmarks'])} landmarks, {len(data['anchors'])} anchors, "
              f"{len(data['trouble'])} troubles, {len(data['festivals'])} festivals")
    print(f"\n{done} profile(s) written. Read them before you play: they are drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
