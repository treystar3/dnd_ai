"""Speaking to an enemy mid-fight. Free: it does not use the player's turn. One try per enemy, win or lose.
intimidate: a hurt or outmatched foe yields (people surrender and can be taken prisoner; others bolt).
persuade:   the foe stands down and walks away.
deceive:    the foe hesitates and loses its next turn.
The engine rolls; the narrator only describes what happened."""

import random

from engine import behaviors, checks
from engine import combat as C

T = C.RULES["talk"]
APPROACHES = ("intimidate", "persuade", "deceive")


def why_not(target) -> str | None:
    """Why this enemy cannot be spoken to, or None."""
    if target.boss:
        return f"{target.name.capitalize()} is past parley - it will fight."
    fam = behaviors.FAMILIES.get(target.family, {})
    if fam.get("talk") is False or target.category not in T["categories"]:
        return f"{target.name.capitalize()} cannot be reasoned with - it only understands the fight."
    if target.talked:
        return f"You have already spoken to {target.name}. Words will not work again this fight."
    return None


def odds(character, combat, target, approach: str) -> tuple[float, list[str]]:
    p = combat.player
    extra = []
    share = target.hp / max(1, target.max_hp)
    if share <= 0.25:
        extra.append(("it is badly hurt", T["hurt"]["quarter"]))
    elif share <= 0.5:
        extra.append(("it is hurt", T["hurt"]["half"]))
    elif approach == "intimidate":
        extra.append(("it is unhurt", T["unhurt_intimidate"]))
    mine = 1 + len(combat.allies())
    theirs = len(combat.enemies())
    if mine > theirs:
        extra.append(("you outnumber them", T["numbers"]))
    elif theirs > mine:
        extra.append(("they outnumber you", -T["numbers"]))
    gap = target.level - p.level
    if gap > 0:
        extra.append(("it outclasses you", T["level_gap"] * gap))
    if target.rank == "elite":
        extra.append(("an elite", T["elite"]))
    extra.append((f"{target.temperament}", T["temperament"].get(target.temperament, 0)))
    if approach == "persuade":
        if target.temperament == "aggressive":
            extra.append(("hungry for a fight", T["persuade_aggressive"]))
        if "fearless" in target.behaviors:
            extra.append(("unshakeable", T["fearless_persuade"]))
    return checks.chance(character, T["checks"][approach], {"always"}, extra=extra)


def attempt(combat, target, approach: str, character, rng: random.Random) -> str | None:
    """Try it. Returns an error line when the words cannot be tried (nothing happens), else None."""
    if approach not in APPROACHES:
        approach = "persuade"
    bad = why_not(target)
    if bad:
        return bad
    if approach == "intimidate" and "fearless" in target.behaviors:
        target.talked = True
        C.tell(combat, f"you try to frighten {C.who(target)}, but it has no fear in it")
        combat.log.append(f"{target.name} cannot be frightened")
        return None
    chance, why = odds(character, combat, target, approach)
    degree, roll = checks.roll(chance, rng)
    target.talked = True
    ok = degree in ("success", "strong success")
    combat.log.append(f"talk ({approach}) {chance:.0f}% rolled {roll}: {degree} [{', '.join(why)}]")
    C.tell(combat, f"you speak to {C.who(target)} ({ {'intimidate': 'a threat', 'persuade': 'reason and persuasion', 'deceive': 'a lie'}[approach]})")
    if not ok:
        C.tell(combat, {"intimidate": f"{C.who(target)} laughs it off and does not back down",
                        "persuade": f"{C.who(target)} will not listen",
                        "deceive": f"{C.who(target)} sees through it"}[approach])
        return None
    if approach == "intimidate":
        yields = behaviors.can_surrender(target) or target.category in ("hostile people", "person template", "monstrous race")
        behaviors._break(combat, target, yields)
        if degree == "strong success" or target.level >= max([e.level for e in combat.enemies()] + [0]):
            behaviors.morale(combat, target, rng)
    elif approach == "persuade":
        target.fled = True
        combat.log.append(f"{target.name} stands down")
        C.tell(combat, f"{C.who(target)} lowers {C.whose(target)} guard, thinks it over, and stands down - it leaves the fight")
    else:
        if C.add_status(combat, target, "stunned", int(T["hesitate_rounds"])):
            C.tell(combat, f"{C.who(target)} is caught off guard by the lie and hesitates, wrong-footed")
    return None
