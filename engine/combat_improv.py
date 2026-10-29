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

# what an improvisation can be FOR, each with the words its meaning is matched against and its odds shift
EFFECTS = {
    "read_opening": {"about": "watching it, studying how it moves, waiting for an opening, reading its guard, biding your time", "odds": 10},
    "break_engagement": {"about": "getting away, slipping free, putting something between you and them, escaping their reach", "odds": 0},
    "gain_position": {"about": "climbing, high ground, a vantage point, getting on top of something", "odds": 0},
    "create_cover": {"about": "cover, a shield of furniture or terrain, ducking behind something, blocking their line", "odds": 5},
    "distract": {"about": "distracting, feinting, throwing sand or a cloak, drawing its eyes away, a trick", "odds": 5},
    "force_move": {"about": "pushing, tripping, knocking them into or off something, driving them back", "odds": -5},
    "disable": {"about": "tangling, pinning, blinding, jamming, fouling their weapon or legs", "odds": -10},
    "damage": {"about": "hurting them with the surroundings: a dropped beam, a kicked brazier, a rockslide", "odds": -5},
}
FALLBACK_WORDS = {"read_opening": ("watch", "opening", "study", "wait for", "bide", "its guard", "a gap"),
                  "break_engagement": ("away", "escape", "between", "back off", "slip"),
                  "gain_position": ("climb", "high", "up ", "vantage", "leap onto", "on top"),
                  "create_cover": ("cover", "behind", "barricade", "shield"),
                  "distract": ("distract", "sand", "feint", "throw my", "trick", "eyes"),
                  "force_move": ("push", "shove", "trip", "knock", "drive"),
                  "disable": ("tangle", "pin", "blind", "net", "jam", "foul"),
                  "damage": ("drop", "kick", "topple", "collapse", "brazier", "rocks")}


def read_effect(words: str) -> str:
    """Which of the vocabulary the player is after, by meaning when the helper model is there, by words when it is not."""
    from engine import relevance
    try:
        pick = relevance.pick(words, [v["about"] for v in EFFECTS.values()], 1, floor=0.3)
        if pick:
            return next(k for k, v in EFFECTS.items() if v["about"] == pick[0])
    except Exception:
        pass
    low = words.lower()
    for k, ws in FALLBACK_WORDS.items():
        if any(w in low for w in ws):
            return k
    return "distract"


def odds_for(p, effect: str) -> float:
    base = RULES.get("improv", {}).get("base_odds", 55)
    edge = max(p.attrs.get("dexterity", 10), p.attrs.get("intelligence", 10))
    return max(10, min(90, base + EFFECTS[effect]["odds"] + 2 * (edge - 10) / 2))


def resolve(fight, p, target, words: str, rng: random.Random) -> None:
    """The player's whole action: read what they are after, roll it, and make something true either way."""
    from engine import checks
    effect = read_effect(words)
    degree, rolled = checks.roll(odds_for(p, effect))
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
