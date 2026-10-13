"""Creature families in a fight: how a wolf, a wyvern and a bandit each behave. The numbers live in data/world/families.yaml;
this is the engine that carries them out. A family is a few traits - gear-style mechanics (rending, terrify...) plus behaviours
(flank, dive, breath, surrender...). Bosses keep their own kits (engine/bosses.py)."""

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent / "data"
FAMILIES: dict = yaml.safe_load((ROOT / "world" / "families.yaml").read_text(encoding="utf-8"))["families"]

CAP_CORRODE = 30            # armor never wears more than this percent in one fight
SURRENDER_ODDS = 0.45       # the chance, each turn once below its threshold, that it yields
FLEE_ODDS = 0.5
DRINK_ODDS = 0.6
GUARD_ODDS = 0.5
DRAUGHT = 0.30              # share of its health a healing draught restores
KEEP_RANGE_EVERY = 3         # a caster gives ground every third blow, so a fighter who has to chase it still gets to swing
MORALE_ODDS = 0.35          # the others, when the strongest of them breaks


def apply(f, creature) -> None:
    """Give an enemy fighter its family's traits."""
    fam = FAMILIES.get(getattr(creature, "family", "") or "")
    if not fam or f.boss:
        return
    f.family = creature.family
    f.weapon_damage *= fam.get("power", 1.0)           # keeps a family's tricks from changing how hard its fights are overall
    f.behaviors = dict(fam.get("behaviors", {}))
    for k, v in fam.get("legendary", {}).items():
        f.legendary[k] = f.legendary.get(k, 0) + v


def beh(f, name: str, default: float = 0.0) -> float:
    return f.behaviors.get(name, default)


def text_for(f) -> str:
    return FAMILIES.get(f.family, {}).get("text", "")


def can_surrender(f) -> bool:
    return "surrender" in f.behaviors and "fearless" not in f.behaviors


def _hurt(f, share: float) -> bool:
    return f.hp <= f.max_hp * share


def _break(combat, f, surrender: bool) -> None:
    from engine import combat as C
    f.fled = True
    f.surrendered = surrender
    if surrender:
        combat.log.append(f"{f.name} yields")
        C.tell(combat, f"{C.who(f)} throws down {C.whose(f)} weapon and yields")
    else:
        combat.log.append(f"{f.name} flees")
        C.tell(combat, f"{C.who(f)} breaks and runs")


def morale(combat, source, rng: random.Random) -> None:
    """When the strongest of a group breaks, the rest may break with it."""
    from engine import combat as C
    rest = [e for e in combat.enemies() if e is not source]
    if not rest or any(e.level > source.level for e in rest):
        return
    for e in rest:
        if e.boss or "fearless" in e.behaviors or rng.random() >= MORALE_ODDS:
            continue
        _break(combat, e, can_surrender(e))
        C.tell(combat, f"{C.who(e)} loses heart seeing {C.who(source)} break")


def pre_turn(combat, e, target, rng: random.Random) -> bool:
    """Choices made before it strikes: bolt, yield, drink, guard, or loose a signature attack. True if the turn is spent."""
    from engine import combat as C
    if not e.family or e.boss:
        return False
    fearless = "fearless" in e.behaviors
    s = beh(e, "surrender")
    if s and not fearless and _hurt(e, s) and rng.random() < SURRENDER_ODDS:
        _break(combat, e, True)
        morale(combat, e, rng)
        return True
    s = beh(e, "flee_low")
    if s and not fearless and _hurt(e, s) and rng.random() < FLEE_ODDS and "grappled" not in e.statuses:
        _break(combat, e, False)
        morale(combat, e, rng)
        return True
    s = beh(e, "use_item")
    if s and _hurt(e, s) and not e.counters.get("drank") and rng.random() < DRINK_ODDS:
        e.counters["drank"] = 1
        heal = round(e.max_hp * DRAUGHT)
        e.hp = min(e.max_hp, e.hp + heal)
        combat.log.append(f"{e.name} drinks a draught: +{heal}")
        C.tell(combat, f"{C.who(e)} pulls a flask from {C.whose(e)} belt and drinks, the worst of the hurt easing")
        return True
    s = beh(e, "defend_low")
    if s and _hurt(e, s) and rng.random() < GUARD_ODDS:
        C.act_defend(combat, e)
        return True
    every = int(beh(e, "breath_every", 0))
    if beh(e, "breath") and every and combat.round % every == 0:
        _area(combat, e, rng, beh(e, "breath"), "breath", f"{C.who(e)} rears back and looses {C.whose(e)} breath over everyone")
        return True
    every = int(beh(e, "surge_every", 0))
    if beh(e, "surge") and every and combat.round % every == 0 and C.in_reach(e, target):
        C.tell(combat, f"{C.who(e)} gathers itself and surges at {C.who(target)}")
        C.apply_damage(combat, e, target, beh(e, "surge"), "surges against", rng)
        after_hit(combat, e, target, True, rng)
        return True
    every = int(beh(e, "slam_every", 0))
    if beh(e, "slam") and every and combat.round % every == 0 and C.in_reach(e, target):
        C.tell(combat, f"{C.who(e)} heaves up a crushing blow for {C.who(target)}")
        hit = C.apply_damage(combat, e, target, beh(e, "slam"), "slams", rng)
        if hit and target.alive and rng.random() < 0.3 and C.add_status(combat, target, "stunned", 1):
            C.tell(combat, f"{C.who(target)} {C.STATUS_WORDS['stunned'][0 if target.side == 'player' else 1]}")
        after_hit(combat, e, target, hit, rng)
        return True
    return False


def _area(combat, e, rng, mult: float, label: str, intro: str) -> None:
    from engine import combat as C
    C.tell(combat, intro)
    foes = [f for f in [combat.player] + combat.allies() if f.alive]
    for t in foes:
        C.apply_damage(combat, e, t, mult, f"{label}s over", rng, can_cleave=False, can_riposte=False, can_flurry=False)


def attack_mult(combat, e, target) -> tuple[float, list[str]]:
    """The multiplier on its ordinary blow this turn, and what made it."""
    if not e.family or e.boss:
        return 1.0, []
    m, why = 1.0, []
    if beh(e, "flank") and len(combat.enemies()) >= 2:
        m *= 1 + beh(e, "flank") / 100
        why.append("presses in with the rest")
    if beh(e, "pounce") and not e.counters.get("struck"):
        m *= 1 + beh(e, "pounce") / 100
        why.append("strikes from ambush")
    if beh(e, "dive") and e.counters.get("dive", 1):
        m *= 1 + beh(e, "dive") / 100
        e.counters["dive"] = 0
        why.append("swoops in")
    if beh(e, "frenzy") and target.hp < target.max_hp * 0.5:
        m *= 1 + beh(e, "frenzy") / 100
        why.append("is driven harder by the scent of blood")
    if beh(e, "rage") and e.hp < e.max_hp * 0.5:
        m *= 1 + beh(e, "rage") / 100
        why.append("grows wilder with every wound")
    return m, why


def charge_bonus(e) -> float:
    """Closing the distance and striking in the same turn: a charge or a dive."""
    return 1 + max(beh(e, "charge"), beh(e, "dive")) / 100 if e.family and not e.boss else 1.0


def closes_and_strikes(e) -> bool:
    return bool(e.family and not e.boss and (beh(e, "charge") or beh(e, "dive")))


def sweeps(combat, e, rng) -> bool:
    """A swarm strikes everyone against it at once."""
    from engine import combat as C
    if not e.family or e.boss or not beh(e, "sweep"):
        return False
    foes = [f for f in [combat.player] + combat.allies() if f.alive and C.in_reach(e, f)]
    if not foes:
        return False
    C.tell(combat, f"{C.who(e)} boils over everyone in reach at once")
    for t in foes:
        hit = C.apply_damage(combat, e, t, beh(e, "sweep"), "swarms over", rng, can_cleave=False, can_riposte=False, can_flurry=False)
        after_hit(combat, e, t, hit, rng)
    return True


def after_hit(combat, e, target, landed: bool, rng: random.Random) -> None:
    """What a landed blow does besides damage: poison, seize, scatter the mind, wear armor, drain stamina."""
    from engine import combat as C
    if not e.family or e.boss:
        return
    e.counters["struck"] = 1
    if not landed or not target.alive:
        return
    for key, status, rounds in (("venom", "poisoned", 3), ("grapple", "grappled", 2), ("befuddle", "befuddled", 1)):
        chance = beh(e, key)
        if chance and status not in target.statuses and rng.uniform(0, 100) < chance and C.add_status(combat, target, status, rounds):
            combat.log.append(f"{target.name} is {status}")
            C.tell(combat, f"{C.who(target)} {C.STATUS_WORDS[status][0 if target.side == 'player' else 1]}")
    c = beh(e, "corrode")
    if c and target.armor > 0 and target.counters.get("corroded", 0) < CAP_CORRODE:
        step = min(c, CAP_CORRODE - target.counters.get("corroded", 0))
        target.counters["corroded"] = target.counters.get("corroded", 0) + step
        target.armor *= 1 - step / 100
        C.tell(combat, f"{C.whose(e)} touch eats at {C.whose(target)} armor")
    d = beh(e, "drain")
    if d and target.max_stamina:
        target.stamina = max(0, target.stamina - target.max_stamina * d / 100)
        C.tell(combat, f"{C.whose(target)} strength drains away under {C.whose(e)} touch")


def after_turn(combat, e, rng) -> None:
    """Withdrawing: a flyer wheels out of reach every few rounds; a caster steps back."""
    from engine import combat as C
    if not e.family or e.boss or not e.alive or e.fled:
        return
    hover = int(beh(e, "hover", 0))
    if hover and beh(e, "dive"):
        e.counters["since"] = e.counters.get("since", 0) + 1
        if e.counters["since"] >= hover and e.band == "engaged":
            e.counters["since"] = 0
            e.counters["dive"] = 1
            e.band = "near"
            C.tell(combat, f"{C.who(e)} wheels back up and out of reach")
            return
    if beh(e, "keep_range") and e.band == "engaged":
        e.counters["back"] = e.counters.get("back", 0) + 1
        if e.counters["back"] >= KEEP_RANGE_EVERY:
            e.counters["back"] = 0
            e.band = "near"
            C.tell(combat, f"{C.who(e)} steps back to keep its distance")
