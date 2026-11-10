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
from engine import combat as C
from engine.combat import RULES, add_status, apply_damage, leave_open, tell, vb, who

REFLEXIVE = {"your": "yourself", "his": "himself", "her": "herself", "their": "themselves", "its": "itself"}   # (f570) by combat.possessive
CONTEST_ATTRS = ["dexterity", "intelligence"]     # (f569) what an improviser's control is pitted with, the attributes its odds read

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


def odds_for(p, effect: str, scant: bool = False) -> float:
    """(f568) The shared formula (engine/checks.py improv_odds) on the better of dexterity and intelligence; (f570) poor ground shifts it."""
    from engine import checks
    I = RULES["improv"]
    edge = max(p.attrs.get("dexterity", 10), p.attrs.get("intelligence", 10))
    shift = EFFECTS[effect]["odds"] + (I["scant_odds"] if scant else 0)
    return checks.improv_odds(edge, shift, I["base_odds"], I["min"], I["max"])


PLACE_WORDS = ("among", "between", "beyond", "beside", "behind", "under", "over", "in", "on", "inside", "below", "above")


def definite(name: str) -> str:
    """(f570) A zone's name as a definite, singular phrase, for any line's subject: 'a small clearing' is 'the small clearing', 'among
    the pillars' 'the ground among the pillars', 'fallen slabs' 'the ground of fallen slabs', 'open ground' 'the open ground'."""
    first, _, rest = name.partition(" ")
    if first.lower() in ("a", "an") and rest:
        return "the " + rest
    if first.lower() in ("the", "some") and rest:
        name = rest
    if first.lower() in PLACE_WORDS:
        return "the ground " + name
    last = name.split()[-1].lower()
    if (last.endswith("s") and not last.endswith("ss")) or " and " in name:
        return "the ground of " + name
    return "the " + name


def scant_ground(fight, p, target, effect: str) -> str | None:
    """(f570) The world's line when the ground is poor for this act (no zone tag of its needs where needs_in says), or None when it serves.
    Picked by the fight's log length, so a retry reads differently and no die is spent."""
    e = RULES["improv"]["effects"].get(effect) or {}
    if not e.get("needs") or not fight.battlefield:
        return None
    field = fight.battlefield
    if target is None and e.get("needs_in") == "target":
        target = fight.enemies()[0] if fight.enemies() else None
    at = target if e.get("needs_in") == "target" else p
    if at is None or at.zone_id not in field.zones:
        return None
    here = field.zones[at.zone_id]
    if any(here.has(tag) for tag in e["needs"]):
        return None
    near = next((field.zones[z] for z in field.adjacent(here.id) if any(field.zones[z].has(tag) for tag in e["needs"])), None)
    pool = RULES["improv"]["scant"][effect]["near" if near else "none"]
    line = pool[(len(fight.log) + len(effect)) % len(pool)]
    zone = definite(here.name)
    return line.format(Here=zone[:1].upper() + zone[1:], here=zone, near=definite(near.name) if near else "",
                       target=who(target) if target is not None else "them")


def resolve(fight, p, target, words: str, rng: random.Random, effect: str = "") -> None:
    """The player's whole action: what they are after (`effect`, as the scene read it; by their words when it gives none), rolled, and
    something made true either way. What they tried is told first, then (f570) any word on poor ground, then what came of it."""
    from engine import checks
    effect = effect or effect_by_words(words)
    scant = scant_ground(fight, p, target, effect)
    degree, rolled = checks.roll(odds_for(p, effect, bool(scant)), rng)
    good = degree in ("success", "strong success")
    partial = degree == "partial"
    fight.log.append(f"{p.name} improvises ({effect.replace('_', ' ')}{', poor ground' if scant else ''}): {degree}")
    tried = f"{who(p)} {vb(p, 'try', 'tries')} it ({words.strip() or effect.replace('_', ' ')})"
    if not good and not partial:
        bf.gain(p, "exposed")
        if scant:                                                # (f570) what was tried, the poor ground, then the failure
            tell(fight, tried[0].upper() + tried[1:])
            tell(fight, scant)
            tell(fight, f"it goes wrong - the moment is lost and {who(p)} {vb(p, 'are', 'is')} left exposed")
        else:
            tell(fight, f"{tried} and it goes wrong - the moment is lost and {who(p)} {vb(p, 'are', 'is')} left exposed")
        return
    told = len(fight.story)
    if scant:
        tell(fight, scant)
    if effect == "read_opening":
        t = target or (fight.enemies()[0] if fight.enemies() else None)
        if t is not None:
            leave_open(fight, t)
            tell(fight, f"{who(p)} {vb(p, 'see', 'sees')} the gap in {who(t)}'s guard - open to {C.possessive(p)} next blow"
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
        tell(fight, f"{who(p)} {vb(p, 'drag', 'drags')} something between {REFLEXIVE.get(C.possessive(p), 'themselves')} and them - cover, for now")
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
            grade = C.contest(p, t, CONTEST_ATTRS, rng)            # (f569) a control meets the target's resolve, worn down by repetition
            if grade == "none":
                tell(fight, f"{who(t)} {vb(t, 'hold', 'holds')} {C.possessive(t)} ground")
            else:
                bf.slip_away(fight, t)
                bf.gain(t, "exposed")
                if grade == "full" and not partial and add_status(fight, t, "prone", 1, p):
                    t.counters["controlled"] = t.counters.get("controlled", 0) + 1
                tell(fight, f"{who(t)} {vb(t, 'are', 'is')} driven stumbling out of position")
    elif effect == "disable":
        t = target
        grade = C.contest(p, t, CONTEST_ATTRS, rng) if t is not None else "none"      # (f569) as an ability's control
        if t is not None and grade == "none":
            tell(fight, f"{who(t)} {vb(t, 'shake', 'shakes')} it off")
        elif t is not None:
            brief = partial or grade == "partial"
            if add_status(fight, t, "slowed", 1 if brief else 2, p):
                t.counters["controlled"] = t.counters.get("controlled", 0) + 1
                tell(fight, f"it catches: {who(t)} {vb(t, 'are', 'is')} fouled and slowed" + (", if only briefly" if brief else ""))
    elif effect == "damage":
        t = target or (fight.enemies()[0] if fight.enemies() else None)
        if t is not None:
            apply_damage(fight, p, t, RULES.get("improv", {}).get("damage_mult", 0.8) * (0.5 if partial else 1.0),
                         "brings the surroundings down on", rng, can_cleave=False, can_riposte=False)
    if len(fight.story) > told:                                          # what was tried comes first, then what came of it
        fight.story.insert(told, tried[0].upper() + tried[1:])
