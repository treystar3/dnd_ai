"""Improvised combat actions (B7): "I kick the brazier over", "I throw sand in its eyes", "I put the fire between us". The model only
says what the player is trying to get (their words); this resolver decides what that is in the engine's small vocabulary, rolls the
check, and applies a legal, bounded effect through the battlefield and status primitives.

The law that keeps builds meaningful: AN ABILITY IS A PROMISE; AN IMPROVISATION IS A GAMBLE. The improvised version of anything an
ability does is check-gated, costs the whole action, lands weaker (shorter, smaller, never a stun), and a failure is a real event -
the action is lost and the player is left exposed for a round - never "nothing happens".

(f380) Each event says what the player tried, in their words, before what came of it: "it catches: the troll is fouled and slowed" alone,
for "I watch the troll and look for an opening", was told as a lance driven into its shoulder. And watching for an opening is a thing
of its own, not a reach for the nearest meaning (it had been read as fouling the troll's legs)."""
from __future__ import annotations

import random

from engine import battlefield as bf
from engine.combat import RULES, add_status, apply_damage, leave_open, tell, vb, who

# (f567) what an improvisation can be FOR, from combat.yaml improv.effects: its meaning, its odds shift, the words that name it
EFFECTS = {k: {"about": v["about"], "odds": v["odds"]} for k, v in RULES["improv"]["effects"].items()}
FALLBACK_WORDS = {k: tuple(v["words"]) for k, v in RULES["improv"]["effects"].items()}


def effect_by_words(words: str) -> str:
    """Which of the vocabulary the player is after, by the words they used. (f503) The reading by meaning, through the helper model's
    embeddings, is the scene's (scenes/combat_scene.py read_effect): a rule never asks a model."""
    low = words.lower()
    for k, ws in FALLBACK_WORDS.items():
        if any(w in low for w in ws):
            return k
    return "distract"


def odds_for(p, effect: str) -> float:
    base = RULES.get("improv", {}).get("base_odds", 55)
    edge = max(p.attrs.get("dexterity", 10), p.attrs.get("intelligence", 10))
    return max(10, min(90, base + EFFECTS[effect]["odds"] + 2 * (edge - 10) / 2))


def resolve(fight, p, target, words: str, rng: random.Random, effect: str = "") -> None:
    """The player's whole action: what they are after (`effect`, as the scene read it; by their words when it gives none), rolled, and
    something made true either way."""
    from engine import checks
    effect = effect or effect_by_words(words)
    degree, rolled = checks.roll(odds_for(p, effect), rng)
    good = degree in ("success", "strong success")
    partial = degree == "partial"
    fight.log.append(f"{p.name} improvises ({effect.replace('_', ' ')}): {degree}")
    tried = f"{who(p)} {vb(p, 'try', 'tries')} it ({words.strip() or effect.replace('_', ' ')})"
    if not good and not partial:
        bf.gain(p, "exposed")
        tell(fight, f"{tried} and it goes wrong - the moment is lost and {who(p)} {vb(p, 'are', 'is')} left exposed")
        return
    told = len(fight.story)
    if effect == "read_opening":
        t = target or (fight.enemies()[0] if fight.enemies() else None)
        if t is not None:
            leave_open(fight, t)
            tell(fight, f"{who(p)} {vb(p, 'see', 'sees')} the gap in {who(t)}'s guard - open to {'your' if p.side == 'player' else 'its'} next blow"
                 + (", if only for a moment" if partial else ""))
    elif effect == "break_engagement":
        bf.slip_away(fight, p)
        tell(fight, f"it works: {who(p)} {vb(p, 'slip', 'slips')} out of their reach" + (", barely" if partial else ""))
        if partial:
            bf.gain(p, "exposed")
    elif effect == "gain_position":
        field = fight.battlefield
        here = field.zones.get(p.zone_id) if field else None
        high = next((z for z in field.adjacent(p.zone_id) if field.zones[z].has("elevated")), None) if field else None
        if here is not None and here.has("elevated") or not field:
            bf.gain(p, "elevated")
        elif high and not partial:
            bf.enter_zone(fight, p, high)
        else:
            bf.gain(p, "elevated" if not partial else "exposed")
        tell(fight, f"{who(p)} {vb(p, 'scramble', 'scrambles')} up to a better spot" + (", though it costs some footing" if partial else ""))
    elif effect == "create_cover":
        bf.gain(p, "covered")
        tell(fight, f"{who(p)} {vb(p, 'drag', 'drags')} something between {'yourself' if p.side == 'player' else 'itself'} and them - cover, for now")
    elif effect == "distract":
        t = target or (fight.enemies()[0] if fight.enemies() else None)
        if t is not None:
            leave_open(fight, t)
            tell(fight, f"the trick works: {who(t)} {vb(t, 'are', 'is')} looking the wrong way - open, for a moment")
    elif effect == "force_move":
        t = target
        from engine import combat_perks
        if t is not None and combat_perks.unmovable(fight, t):
            tell(fight, f"{who(t)} {vb(t, 'do', 'does')} not move an inch {combat_perks.tag(t, 'juggernaut')}")
        elif t is not None:
            bf.slip_away(fight, t)
            bf.gain(t, "exposed")
            if not partial:
                add_status(fight, t, "prone", 1)
            tell(fight, f"{who(t)} {vb(t, 'are', 'is')} driven stumbling out of position")
    elif effect == "disable":
        t = target
        if t is not None and add_status(fight, t, "slowed", 1 if partial else 2):
            tell(fight, f"it catches: {who(t)} {vb(t, 'are', 'is')} fouled and slowed" + (", if only briefly" if partial else ""))
    elif effect == "damage":
        t = target or (fight.enemies()[0] if fight.enemies() else None)
        if t is not None:
            apply_damage(fight, p, t, RULES.get("improv", {}).get("damage_mult", 0.8) * (0.5 if partial else 1.0),
                         "brings the surroundings down on", rng, can_cleave=False, can_riposte=False)
    if len(fight.story) > told:                                          # what was tried comes first, then what came of it
        fight.story.insert(told, tried[0].upper() + tried[1:])
