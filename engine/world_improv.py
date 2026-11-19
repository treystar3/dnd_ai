"""What an act outside a fight makes true besides its own changes (f321; engine/act.py rules and rolls it since f603): the player's words
read for what they are after (data/rules/improv.yaml, by meaning), and on a success the place's mark and the effect's changes."""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from core import yamlio

from engine import worldstate
from ui import console

ROOT = Path(__file__).resolve().parent.parent
W = yamlio.safe_load((ROOT / "data" / "rules" / "improv.yaml").read_text(encoding="utf-8"))


def read_effect(words: str) -> str:
    """Which of the vocabulary the player is after, by meaning when the helper model is there, else 'attempt'. (f386) A reading whose
    `needs` words the line lacks gives way to the next closest; a line that is only a gesture or a pose is 'pose'."""
    from engine import relevance
    named = {k: v["about"] for k, v in W["effects"].items() if v.get("about")}
    try:
        for p in relevance.pick(words, list(named.values()), 3, floor=0.3):
            k = next(k for k, a in named.items() if a == p)
            need = W["effects"][k].get("needs")
            if k == "pose" or not need or re.search(need, words or "", re.I):
                return k
    except Exception:
        pass
    if is_pose(words):
        return "pose"
    return next((k for k, e in W["effects"].items() if e.get("needs") and re.search(e["needs"], words or "", re.I)), "attempt")


def is_pose(words: str) -> bool:
    """(f386) A gesture or a pose and nothing more: none of the effects' own words, and a word of standing, leaning, watching..."""
    if not re.search(W["pose_words"], words or "", re.I):
        return False
    return not any(re.search(e["needs"], words or "", re.I) for k, e in W["effects"].items() if e.get("needs") and k != "practise")


def is_rest(words: str) -> bool:
    """(f386) A line that only sleeps or rests: a rest, not a gamble (going to sleep was rolled as hiding)."""
    return bool(re.search(W["rest_words"], words or "", re.I))


def asks_camp(words: str) -> bool:
    """(f716) A line that asks to make camp for its sleep."""
    return bool(re.search(W["camp_words"], words or "", re.I)) and not re.search(W["camp_refused"], words or "", re.I)


def asks_room(words: str) -> bool:
    """(f695) A line that asks to take a room or a bed to sleep in, and does not say no to one."""
    return bool(re.search(W["room_words"], words or "", re.I)) and not re.search(W["room_refused"], words or "", re.I)


def odds_for(c, effect: str) -> float:
    from engine import checks
    e = W["effects"][effect]
    attr = max(getattr(c.attributes, a) for a in e["attr"])
    return checks.improv_odds(attr, e["odds"], W["base_odds"], W["min"], W["max"])


CHANGE_KINDS = ("closed", "danger", "news", "vantage")


def apply_changes(ws, effect: str, what: str, degree: str) -> list[str]:
    """(f332) What a success makes true besides its mark: the effect's `changes` (improv.yaml), applied to the world's state. A partial
    applies closed and danger at half and spreads no word. Returns what was done, for the debug line."""
    from engine import pulse
    specs = W["effects"][effect].get("changes") or []
    if not specs:
        return []
    half = degree == "partial"
    state = ws.store.load_world_state()
    if not state and not any(ch.get("kind") == "vantage" for ch in specs):      # (f704) a view needs no world's state
        return []
    here = ws.player_of(ws.acting).location
    place = ws.world.places.get(here)
    fmt = {"what": what or "it", "place": place.name if place else here}
    done = []
    for ch in specs:
        kind = ch.get("kind")
        if not state and kind != "vantage":
            continue
        if kind == "closed":
            minutes = max(1, int(ch.get("minutes", 60)) // (2 if half else 1))
            worldstate.add_effect(state, {"kind": "closed", "place": here, "value": 0, "until": ws.minutes + minutes,
                                     "text": (ch.get("text") or "{what}").format(**fmt), "cause": "improvised"})
            done.append(f"closed {minutes}m")
        elif kind == "danger":
            if not (place and place.danger):
                continue
            value = round(int(ch.get("value", 0)) / (2 if half else 1))
            if value:
                worldstate.add_effect(state, {"kind": "danger", "place": here, "value": value, "until": ws.minutes + max(1, int(ch.get("days", 1))) * 1440,
                                         "cause": "improvised"})
                done.append(f"danger {value:+d}")
        elif kind == "news" and not half:
            groups = [ws.world.locals_group(here) or "everyone" if g == "locals" else g for g in ch.get("groups") or ["everyone"]]
            pulse.add_news(state, (ch.get("text") or "").format(**fmt), here, ws.minutes, [g for g in groups if g in ws.world.knowledge_groups] or ["everyone"])
            done.append("news")
        elif kind == "vantage" and re.search(ch.get("view_words") or "(?!)", what or "", re.I):
            seen = vantage(ws, ch, half)            # (f704) a height looked out from: what is really there to see
            if seen:
                done.append("vantage " + "; ".join(seen))
    if state and any(not d.startswith("vantage") for d in done):
        ws.store.save_world_state(state)
    return done


def vantage(ws, ch: dict, half: bool) -> list[str]:
    """(f704) What can be made out from a height, as "Name (to the north, half a day's walk)": only from open ground (ch['from']),
    out of a delve, by day; only places that can be seen from outside (ch['seen']: never under the ground), within the walk; the
    ones the player has not heard of first. Those are heard of now."""
    from engine import clock, exits, mapview
    me = ws.player_of(ws.acting)
    place = ws.world.places.get(me.location)
    if place is None or me.delve or place.type not in set(ch["from"]) or clock.is_dark(ws.minutes):
        return []
    top = mapview.top_of(ws.world, me.location)
    known = set(me.visited) | set(me.heard)
    near = sorted((pid in known, found[1], pid) for pid, pl in ws.world.places.items()
                  if pid != top and not pl.parent and pl.type in set(ch["seen"])
                  for found in [ws.world.path(top, pid)] if found and found[1] <= int(ch["minutes"]))
    out = []
    for _, minutes, pid in near[:max(1, int(ch["most"]) // (2 if half else 1))]:
        ws.hear(pid)
        way = exits.sector_of(exits._heading(ws.world, top, pid))
        out.append(f"{ws.world.places[pid].name} (to the {way}, {clock.walk_words(minutes)})")
    return out


def problems() -> list[str]:
    """What is wrong with improv.yaml's changes: a kind the engine cannot apply, or a field it needs missing; a `needs` that is no pattern;
    a kind with nothing to tell the narrator; a stands_for word that is no change of the act's."""
    from engine import features, targets
    bad = [f"improv.yaml told: needs a line for {k}" for k in CHANGE_KINDS if not str((W.get("told") or {}).get(k) or "").strip()]
    words = set(targets.CH["changes"]) | set(features.F["becomes"]) | set(targets.CH["changes"]["access"]["args"])
    bad += [f"improv.yaml {name}: stands_for '{w}' is no change the act can make" for name, e in (W.get("effects") or {}).items()
            for w in e.get("stands_for") or [] if w not in words]
    for name, e in (W.get("effects") or {}).items():
        try:
            re.compile(e.get("needs") or "")
        except re.error as x:
            bad.append(f"improv.yaml {name}: needs is not a pattern ({x})")
    need = {"closed": ("minutes",), "danger": ("value", "days"), "news": ("text",), "vantage": ("minutes", "most", "view_words", "from", "seen")}
    if "{names}" not in str((W.get("told") or {}).get("vantage") or ""):
        bad.append("improv.yaml told.vantage: needs {names}")
    for name, e in (W.get("effects") or {}).items():
        for ch in e.get("changes") or []:
            kind = ch.get("kind")
            if kind not in CHANGE_KINDS:
                bad.append(f"improv.yaml {name}: change kind '{kind}' is not one of {', '.join(CHANGE_KINDS)}")
                continue
            for f in need[kind]:
                if f not in ch:
                    bad.append(f"improv.yaml {name}: a {kind} change needs {f}")
    return bad


def what_of(words: str) -> str:
    """The thing attempted, for a mark: the player's words, trimmed of the 'I' and kept short."""
    w = " ".join((words or "").split())
    if w.lower().startswith("the player "):                 # (f391) a summary in the third person: "The player takes out their journal"
        from engine import hygiene
        w = hygiene.second_person(w, whole=True)[4:]
    for lead in ("i try to ", "i attempt to ", "i'll ", "i will ", "i "):
        if w.lower().startswith(lead):
            w = w[len(lead):]
            break
    return w.rstrip(".!").strip()[:80]


def land(ws, words: str, degree: str, refused: set[str] = frozenset()) -> list[str]:
    """(f603) What an act that worked makes true besides its own changes (improv.yaml effects; the owner kept them): the effect its words
    read as and the place's mark, rough on a partial. A gesture leaves nothing, nor an effect that stands for a change the engine refused
    (`refused`: those change words). Returns what the narrator is told of it."""
    from engine import asked
    if degree not in ("success", "strong success", "partial"):
        return []
    effect = asked.compute(f"improv_effect:{words}", lambda: read_effect(words))   # (f500) read once a line
    if effect == "pose" or effect not in W["effects"]:
        return []
    if set(W["effects"][effect].get("stands_for") or []) & set(refused):
        return []
    e, what = W["effects"][effect], what_of(words)
    mark = e["mark"].format(what=what) if e["mark"] and what else ""
    mark = ("roughly, " if degree == "partial" and mark else "") + mark
    if mark:
        ws.add_mark(mark)
    changed = apply_changes(ws, effect, what, degree)
    if changed:
        console.debug(f"improvised ({effect}): made true - {', '.join(changed)}")
    return ([mark] if mark else []) + [W["told"][c.split()[0]].format(names=c.split(" ", 1)[-1]) for c in changed]
