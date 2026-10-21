"""Improvised actions outside a fight (f321): what the interpreter cannot name becomes a gamble with a consequence, never an attempt
that changes nothing. The player's words are read for what they are after (data/rules/improv.yaml, by meaning), rolled on the attribute
that would do it, and something is made true either way: a mark on the place, a cost, a noise the watch hears of.

Mirrors engine/combat_improv.py: AN ABILITY IS A PROMISE; AN IMPROVISATION IS A GAMBLE."""
from __future__ import annotations

from pathlib import Path

import yaml

from ui import console

ROOT = Path(__file__).resolve().parent.parent
W = yaml.safe_load((ROOT / "data" / "rules" / "improv.yaml").read_text(encoding="utf-8"))


def read_effect(words: str) -> str:
    """Which of the vocabulary the player is after, by meaning when the helper model is there, else 'attempt'."""
    from engine import relevance
    named = {k: v["about"] for k, v in W["effects"].items() if v["about"]}
    try:
        pick = relevance.pick(words, list(named.values()), 1, floor=0.3)
        if pick:
            return next(k for k, a in named.items() if a == pick[0])
    except Exception:
        pass
    return "attempt"


def odds_for(c, effect: str) -> float:
    from engine import checks
    e = W["effects"][effect]
    attr = max(getattr(c.attributes, a) for a in e["attr"])
    R = checks.RULES
    raw = W["base_odds"] + (attr - R["attribute_center"]) * R["attribute_weight"] + e["odds"]
    return max(W["min"], min(W["max"], raw))


def what_of(words: str) -> str:
    """The thing attempted, for a mark: the player's words, trimmed of the 'I' and kept short."""
    w = " ".join((words or "").split())
    for lead in ("i try to ", "i attempt to ", "i'll ", "i will ", "i "):
        if w.lower().startswith(lead):
            w = w[len(lead):]
            break
    return w.rstrip(".!").strip()[:80]


def resolve(ws, words: str, text: str) -> None:
    """The whole action: read it, roll it, make something true, and tell the narrator what happened as a decided fact."""
    from engine import checks, pools, law, clock
    c = ws.player.character
    effect = read_effect(words or text)
    e = W["effects"][effect]
    odds = odds_for(c, effect)
    degree, rolled = checks.roll(odds, ws.rng, c=c)
    console.debug(f"improvised ({effect}): {odds:.0f}% - rolled {rolled}: {degree}")
    console.ledger(f"{effect.capitalize()} — {degree.replace('_', ' ')}")
    what = what_of(words or text)
    mark = e["mark"].format(what=what) if e["mark"] and what else ""
    if degree in ("success", "strong success"):
        if mark:
            ws.add_mark(mark)
        ws.advance(5)
        ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) WORKS" + (" cleanly and well" if degree == "strong success" else "")
                   + ". Show it done, as it would be seen, and what is different now. Nothing is gained that was not there, and no one is harmed.", text)
        return
    if degree == "partial":
        P = W["partial"]
        if mark:
            ws.add_mark("roughly, " + mark)
        ws.advance(P["minutes"])
        ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) half works - {P['text']}. Show it as it would be seen, "
                   "the flaw in it plain. Nothing is gained that was not there.", text)
        return
    F = W["fails"][e["fail"]]
    ws.advance(F["minutes"])
    if F.get("health_pct"):
        top = pools.maximum(c, "health")
        c.health = max(1.0, pools.current(c, "health") - top * F["health_pct"] / 100)
    if F.get("heat") and not ws.place.danger:
        law.add_heat(ws.player, ws.town_here(), F["heat"], clock.day(ws.minutes))
    if F.get("mark") and mark:
        ws.add_mark(F["mark"].format(mark=mark))
    ws.store.save_player(ws.player)
    ws.narrate(f"THE GAME HAS DECIDED: what the player attempts ({what}) FAILS - {F['text']}. Show the failure as it happens and what it "
               "costs them, and stop there; no one gives them anything, and nobody speaks beyond a look or a word.", text)
