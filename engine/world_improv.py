"""Improvised actions outside a fight (f321): what the interpreter cannot name becomes a gamble with a consequence, never an attempt
that changes nothing. The player's words are read for what they are after (data/rules/improv.yaml, by meaning), rolled on the attribute
that would do it, and something is made true either way: a mark on the place, a cost, a noise the watch hears of.

Mirrors engine/combat_improv.py: AN ABILITY IS A PROMISE; AN IMPROVISATION IS A GAMBLE."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ui import console

ROOT = Path(__file__).resolve().parent.parent
W = yaml.safe_load((ROOT / "data" / "rules" / "improv.yaml").read_text(encoding="utf-8"))


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


def odds_for(c, effect: str) -> float:
    from engine import checks
    e = W["effects"][effect]
    attr = max(getattr(c.attributes, a) for a in e["attr"])
    R = checks.RULES
    raw = W["base_odds"] + (attr - R["attribute_center"]) * R["attribute_weight"] + e["odds"]
    return max(W["min"], min(W["max"], raw))


CHANGE_KINDS = ("closed", "danger", "news")


def apply_changes(ws, effect: str, what: str, degree: str) -> list[str]:
    """(f332) What a success makes true besides its mark: the effect's `changes` (improv.yaml), applied to the world's state. A partial
    applies closed and danger at half and spreads no word. Returns what was done, for the debug line."""
    from engine import pulse
    specs = W["effects"][effect].get("changes") or []
    if not specs:
        return []
    half = degree == "partial"
    state = ws.store.load_world_state()
    if not state:
        return []
    here = ws.player.location
    place = ws.world.places.get(here)
    fmt = {"what": what or "it", "place": place.name if place else here}
    done = []
    for ch in specs:
        kind = ch.get("kind")
        if kind == "closed":
            minutes = max(1, int(ch.get("minutes", 60)) // (2 if half else 1))
            state["effects"].append({"kind": "closed", "place": here, "value": 0, "until": ws.minutes + minutes,
                                     "text": (ch.get("text") or "{what}").format(**fmt), "cause": "improvised"})
            done.append(f"closed {minutes}m")
        elif kind == "danger":
            if not (place and place.danger):
                continue
            value = round(int(ch.get("value", 0)) / (2 if half else 1))
            if value:
                state["effects"].append({"kind": "danger", "place": here, "value": value, "until": ws.minutes + max(1, int(ch.get("days", 1))) * 1440,
                                         "cause": "improvised"})
                done.append(f"danger {value:+d}")
        elif kind == "news" and not half:
            groups = [ws.world.locals_group(here) or "everyone" if g == "locals" else g for g in ch.get("groups") or ["everyone"]]
            pulse.add_news(state, (ch.get("text") or "").format(**fmt), here, ws.minutes, [g for g in groups if g in ws.world.knowledge_groups] or ["everyone"])
            done.append("news")
    if done:
        ws.store.save_world_state(state)
    return done


def problems() -> list[str]:
    """What is wrong with improv.yaml's changes: a kind the engine cannot apply, or a field it needs missing; a `needs` that is no pattern."""
    bad = []
    for name, e in (W.get("effects") or {}).items():
        try:
            re.compile(e.get("needs") or "")
        except re.error as x:
            bad.append(f"improv.yaml {name}: needs is not a pattern ({x})")
    need = {"closed": ("minutes",), "danger": ("value", "days"), "news": ("text",)}
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


def resolve(ws, words: str, text: str) -> None:
    """The whole action: read it, roll it, make something true, and tell the narrator what happened as a decided fact."""
    from engine import checks, pools
    c = ws.player.character
    effect = read_effect(words or text)
    if effect == "pose":                                    # (f386) shown, and nothing else: no roll, no mark, nothing barred
        ws.advance(1)
        ws.narrate(f"THE GAME HAS DECIDED: the player does a small thing ({what_of(words or text)}) and nothing comes of it: it changes nothing "
                   "and nobody makes anything of it. Show it in passing, as it would be seen.", text)
        return
    e = W["effects"][effect]
    odds = odds_for(c, effect)
    degree, rolled = checks.roll(odds, ws.rng, c=c)
    console.debug(f"improvised ({effect}): {odds:.0f}% - rolled {rolled}: {degree}")
    console.ledger(f"{effect.capitalize()} — {degree.replace('_', ' ')}")
    what = what_of(words or text)
    mark = e["mark"].format(what=what) if e["mark"] and what else ""
    from engine.domain_events import Improvised
    failed = degree not in ("success", "strong success", "partial")
    ws.notice(Improvised(minute=ws.minutes, place=ws.player.location, effect=effect, degree=degree, what=what, mark=mark,
                         heat=float(W["fails"][e["fail"]].get("heat", 0) or 0) if failed else 0.0))
    if degree in ("success", "strong success"):
        if mark:
            ws.add_mark(mark)
        changed = apply_changes(ws, effect, what, degree)
        if changed:
            console.debug(f"improvised ({effect}): made true - {', '.join(changed)}")
        ws.advance(5)
        ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) WORKS" + (" cleanly and well" if degree == "strong success" else "")
                   + ". Show it done, as it would be seen, and what is different now. Nothing is gained that was not there, and no one is harmed.", text)
        return
    if degree == "partial":
        P = W["partial"]
        if mark:
            ws.add_mark("roughly, " + mark)
        apply_changes(ws, effect, what, degree)
        ws.advance(P["minutes"])
        ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) half works - {P['text']}. Show it as it would be seen, "
                   "the flaw in it plain. Nothing is gained that was not there.", text)
        return
    F = W["fails"][e["fail"]]
    ws.advance(F["minutes"])
    if F.get("health_pct"):
        top = pools.maximum(c, "health")
        c.health = max(1.0, pools.current(c, "health") - top * F["health_pct"] / 100)
    if F.get("mark") and mark:
        ws.add_mark(F["mark"].format(mark=mark))
    ws.store.save_player(ws.player)
    ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) FAILS - {F['text']}. Show the failure as it happens and what it "
               "costs them, and stop there; no one gives them anything, and nobody speaks beyond a look or a word.", text)
