"""(f348) What a person is doing when the player sees them: the engine decides, from data/world/doings.yaml.

A resident's activity used to be one sentence the model wrote when the place was peopled, kept for good: every armed person in a town
was sharpening a blade, and was still sharpening it days later, in every narration and every frame. Now each present person's doing is
drawn by the engine from their role's list for the period of the day (seeded by person, day and period, so it holds for the period and
turns with it), no two people in a place doing the same thing, and a moment under way (engine/moments.py) may set everyone's instead.
The model writes the look; the doing reaches it as RIGHT NOW, like any fact."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
D = yaml.safe_load((ROOT / "data" / "world" / "doings.yaml").read_text(encoding="utf-8"))
STILL = ("prisoner",)                         # roles whose doing the story sets (a prisoner walks bound at your side)


def entries(role: str, person: str = "") -> list[dict]:
    """A person's own doings when they have them (by_person, f380), else their role's, else anyone's."""
    raw = (D.get("by_person") or {}).get(person) or (D.get("by_role") or {}).get(role) or D["anyone"]
    return [e if isinstance(e, dict) else {"text": e} for e in raw]


def options(role: str, period: str, person: str = "", place_type: str = "") -> list[dict]:
    """The doings open to this role at this period: those for the period, else those for any time, else anyone's. (f449) An entry with
    `at` (kinds of place) is open only at a place of one of those kinds: a farmer in the town square is not walking a furrow there
    (the owner's log: "The sun-browned reaper comes along, and is soon walking a furrow", said in Parth). With no place kind given,
    every entry is open."""
    all_ = [e for e in entries(role, person) if not e.get("at") or not place_type or place_type in e["at"]]
    out = [e for e in all_ if not e.get("when") or period in e["when"]]
    return out or [e for e in all_ if not e.get("when")] or [{"text": t} for t in D["anyone"]]


def pick(role: str, period: str, rng: random.Random, taken=(), person: str = "", place_type: str = "") -> str:
    opts = options(role, period, person, place_type)
    fresh = [e for e in opts if e["text"] not in taken] or [{"text": t} for t in D["anyone"] if t not in taken] or opts
    return rng.choices(fresh, weights=[float(e.get("weight", 1)) for e in fresh])[0]["text"]


def override(moment: dict | None, role: str) -> str:
    """What a moment under way has this role doing, or ''."""
    if not moment:
        return ""
    d = moment.get("doings") or {}
    if role in (d.get("roles") or {}):
        return d["roles"][role]
    if role in (d.get("except") or []):
        return ""
    return d.get("all", "")


def doing_for(npc, seed, minutes: int, taken=(), moment: dict | None = None, place_type: str = "") -> str:
    """This person's doing now: the moment's if one is on, else their own for the period, held for the period."""
    from engine import clock
    over = override(moment, npc.role)
    if over:
        return over
    period = clock.period(minutes)
    rng = random.Random(f"{seed}:doing:{npc.id}:{clock.day(minutes)}:{period}")
    return pick(npc.role, period, rng, taken, person=npc.id, place_type=place_type)


def assign(store, people: list, minutes: int, moment: dict | None = None, save: bool = True, visiting=(), place_type: str = "") -> list[tuple]:
    """Give each present person their doing, no two alike; the record is saved when it changed. Returns [(npc, before, after)] for
    those that changed (a revisit's 'what has changed' line is built from them). (f352) `visiting`: the ids of those here on their
    routine, who do what people do at a place of this kind rather than their trade."""
    from engine import clock, routines
    taken, changed = set(), []
    for n in sorted(people, key=lambda x: x.id):
        if n.role in STILL:
            continue
        if n.id in visiting and not override(moment, n.role):
            new = routines.doing_at(place_type, random.Random(f"{store.meta.seed}:visit:{n.id}:{clock.day(minutes)}:{clock.period(minutes)}"), taken)
        else:
            new = doing_for(n, store.meta.seed, minutes, taken, moment, place_type)    # (f449) a trade's doing only where it fits
        taken.add(new)
        if new != (n.activity or ""):
            changed.append((n, n.activity or "", new))
            n.activity = new
            if save:
                store.save_npc(n)
    return changed


def changed_lines(changed: list[tuple], most: int = 2) -> list[str]:
    """For the narrator, on a return visit: who is doing something else since the player last saw them, as what they do now. (f374) Told
    as 'since the player was last here, X has gone from A to B', the narrator wrote it back as a report ('Since your last visit, Maren
    Holt now scrapes mud from a cloak'); told as the present, it is shown."""
    out = []
    for n, before, after in changed:
        if before and after and before != after:
            out.append(f"{n.label()} is {after.rstrip('.')} now, not {before.rstrip('.')}, which is what they were doing on the player's last "
                       "visit; show it, never report it as a change.")             # (f423) never read as the player's own deed
    return out[:most]


def problems(roles: set[str], periods: set[str], place_types: set[str] = frozenset()) -> list[str]:
    """What is wrong with doings.yaml: a role the world lacks, a period the clock lacks, an empty text, a role with too few doings,
    (f449) a kind of place in `at` the world lacks, or a role whose every doing is bound to a place (it needs some for anywhere)."""
    bad = []
    if not isinstance(D.get("anyone"), list) or len(D["anyone"]) < 4:
        bad.append("doings.yaml anyone: needs at least four doings for anyone")
    lists = [(f"by_role.{r}", r, raw) for r, raw in (D.get("by_role") or {}).items()] + \
        [(f"by_person.{p}", "", raw) for p, raw in (D.get("by_person") or {}).items()]          # (f380) a person's own, checked the same way
    for where, role, raw in lists:
        if role and role not in roles:
            bad.append(f"doings.yaml by_role: '{role}' is not a role in roles.yaml")
        texts = []
        for e in raw or []:
            e = e if isinstance(e, dict) else {"text": e}
            if not str(e.get("text", "")).strip():
                bad.append(f"doings.yaml {where}: an entry has no text")
            texts.append(e.get("text"))
            for w in e.get("when") or []:
                if w not in periods:
                    bad.append(f"doings.yaml {where}: '{w}' is not a period of the day")
            if "weight" in e and not (isinstance(e["weight"], (int, float)) and e["weight"] > 0):
                bad.append(f"doings.yaml {where}: a weight must be above zero")
            if "at" in e and (not isinstance(e["at"], list) or not e["at"]):
                bad.append(f"doings.yaml {where}: `at` must list kinds of place")
            for t in (e.get("at") or []) if isinstance(e.get("at"), list) else []:
                if place_types and t not in place_types:
                    bad.append(f"doings.yaml {where}: '{t}' in `at` is not a kind of place the world has")
        if raw and all(isinstance(e, dict) and e.get("at") for e in raw):
            bad.append(f"doings.yaml {where}: every doing is bound to a place; a person seen elsewhere needs some")
        if len(texts) != len(set(texts)):
            bad.append(f"doings.yaml {where}: a doing is listed twice")
        if len(texts) < 3:
            bad.append(f"doings.yaml {where}: fewer than three doings")
    for role in sorted(roles - set(D.get("by_role") or {}) - set(STILL)):
        bad.append(f"doings.yaml by_role: the role '{role}' has no doings")
    return bad
