"""Ignite and poison (f227): one law for every source - a spell, a weapon rider, gear, a creature, a perk (data/rules/combat.yaml).

Ignite (burning) is a share of the hit that set it, dealt over a couple of rounds; only the strongest burns, so fire is about the size of
the hit. Poison (poisoned) adds a stack per poisoning; every stack deals the same flat amount - a share of its maker's offensive power -
however small the hit, there is no cap, and a new stack refreshes them all: poison is about how often you land.

Bleeding (f234) is an open wound: its size is a share of the hit that opened it, and it does nothing by itself - every physical hit the
bleeder takes afterwards, from anyone, makes it bleed its size again. Only the biggest wound counts; it closes after three rounds, or when
the bleeder is healed. Bleeding is about the size of the cut, paid out by every blow that follows. The bloodless cannot bleed."""
from __future__ import annotations

from engine import combat as C


def offensive_power(f, spell_attr: str = "") -> float:
    """What this fighter's blows are built from before the roll: weapon power (weapon damage + its attribute + flat damage) for a weapon,
    spell power (spell base for the level + spell power, times the casting attribute) for a spell - the one being cast now, or the one
    named by spell_attr."""
    if f is None:
        return 0.0
    if f.spell_kind == "spell" or spell_attr:
        if f.spell_kind == "spell":
            return f.weapon_damage * f.spell_mult
        focus = (f.weapon_damage if f.damage_type == "magical" else 0) + f.offhand_spell + C.flat_bonus(f, "spell_power", {"always"})
        base = C.RULES["spell_base_damage"] * C.growth(f.level) + focus
        return base * (1 + f.attrs.get(spell_attr, 10) / C.RULES["spell_attribute"])
    d = C.RULES["damage"]
    return f.weapon_damage + f.best_attr(f.weapon_attrs) * d["attribute_bonus"] + C.flat_bonus(f, "damage", {"always"})


def apply(combat, f, status: str, rounds: int, source) -> int:
    """A burn or a poisoning lands (add_status has passed its checks): set its strength. Returns the rounds it lasts."""
    from engine import combat_perks
    if status == "burning":
        I = C.RULES["ignite"]
        if "burning" not in f.statuses:
            f.ignite = 0
        hit = source.counters.get("last_hit", 0) if source is not None else 0
        if hit and source is not None and (source.hit_element or source.element) == "fire":
            hit /= max(0.01, C.element_factor(f, "fire"))   # a fire hit was already resisted; the burn is resisted once, as it ticks
        hit = hit or offensive_power(source)
        per = hit * I["share"] / I["rounds"] if hit else f.max_hp * C.RULES["statuses"]["burning"]["damage_percent"] / 100
        if C.attuned(source, "fire"):
            per *= C.ATTUNE["fire"]                          # an archon of fire burns hotter (f246)
        if source is not None and source.counters.get("stoke"):
            from engine import spellcraft as _ss
            e = _ss.EXPR["stoke"]
            per *= min(float(e.get("cap", 2.0)), 1 + e.get("pct", 25) / 100 * source.counters["stoke"])   # Stoke (f268)
        if source is not None and combat_perks.has(source, "firebrand", combat) and f.ignite:
            f.ignite += per                                  # Firebrand: your fires feed the burn instead of replacing it
            C.tell(combat, f"the fire on {C.who(f)} feeds on itself {combat_perks.tag(source, 'firebrand')}")
            return int(I["rounds"])
        if per >= f.ignite:
            f.ignite = per                                   # the strongest ignite burns; a weaker one changes nothing
            return int(I["rounds"])
        return f.statuses.get("burning", int(I["rounds"]))
    if status == "bleeding":
        B = C.RULES["bleed"]
        if "bleeding" not in f.statuses:
            f.bleed = 0
        hit = source.counters.get("last_hit", 0) if source is not None else 0
        hit = hit or offensive_power(source)
        size = hit * B["share"] if hit else f.max_hp * C.RULES["statuses"]["bleeding"]["damage_percent"] / 100
        if size > f.bleed:
            f.bleed = size                                   # one wound: the bigger cut replaces the smaller, and starts again
            return int(B["rounds"])
        return f.statuses.get("bleeding", int(B["rounds"]))  # a smaller cut changes nothing
    if status == "poisoned":
        P = C.RULES["poison"]
        if "poisoned" not in f.statuses:
            f.poison = []
        power = offensive_power(source)
        stack = power * P["share"] if power else f.max_hp * C.RULES["statuses"]["poisoned"]["damage_percent"] / 100
        f.poison = list(f.poison) + [stack] * (2 if C.attuned(source, "poison") else 1)   # an archon of poison doubles each dose
        return int(P["rounds"])                              # a new stack refreshes them all
    return rounds


ELEMENT = {"burning": "fire", "poisoned": "poison"}


def tick(f, dot: str) -> int:
    """This round's damage from a damage-over-time status. A burn or a poisoning gets past armor, shields and plain magic or physical
    resistance, but not past resistance to its own element: a fire elemental barely burns, a golem shrugs off most poison."""
    if dot == "burning" and f.ignite:
        raw = f.ignite
    elif dot == "poisoned" and (f.poison or f.poison_fixed):
        raw = sum(f.poison) + sum(f.poison_fixed)
    elif dot == "bleeding" and f.bleed:
        raw = f.bleed
    else:
        raw = f.max_hp * C.RULES["statuses"][dot]["damage_percent"] / 100
    if not (dot == "poisoned" and f.counters.get("refined_venom")):   # Refined Venom (f268): resistance does not count
        raw *= C.element_factor(f, ELEMENT.get(dot, ""))
    return max(1, round(raw)) if raw > 0 else 0


def ended(f, status: str) -> None:
    if status == "burning":
        f.ignite = 0
    elif status == "poisoned":
        f.poison = []
        f.poison_fixed = []
    elif status == "bleeding":
        f.bleed = 0
        if f.counters.pop("crippled", 0):
            f.statuses.pop("slowed", None)                   # Crippling Wounds (f312): the wound closed, and the limp goes with it


def bloodless(f) -> bool:
    return f.category in C.RULES["bleed"]["bloodless"]


def tear(combat, f, deep: float = 1.0, by: str = "") -> int:
    """A physical hit lands on an open wound: it bleeds its size (times deep: Open Wound tears twice as deep, f311), through armor and
    shields. Returns what it took."""
    if "bleeding" not in f.statuses or not f.alive:
        return 0
    from engine import combat_perks
    amount = combat_perks.dot_damage(f, "bleeding", tick(f, "bleeding")) * deep
    floor = 1 if ((combat.mentor and f.side == "player") or combat.duel) else 0
    before = f.hp
    f.hp = max(floor, f.hp - amount)
    lost = round(before - f.hp)
    if lost:
        combat.log.append(f"{f.name}'s wound tears: {lost}")
        C.tell(combat, f"the blow tears {C.whose(f)} wound open again - {lost} more blood lost" + (f" {by}" if by else ""))
    return lost


def bind(combat, f, how: str = "") -> bool:
    """The wound is closed: healed, cleansed or bandaged."""
    if "bleeding" not in f.statuses:
        return False
    f.statuses.pop("bleeding", None)
    ended(f, "bleeding")
    if how:
        C.tell(combat, f"{C.who(f)} {how}, and the bleeding stops")
    return True
