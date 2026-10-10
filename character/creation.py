"""Character-creation pipeline and rules.

The goddess scene and the smoke test both use these functions.
"""

import random
from pathlib import Path

from core.models import Ability, Attributes, Character, Effect, Passive
from character import fit
from core.rules import FAMILIES, MECHANICS, TRIGGERS
from engine.abilities import materialize_active, materialize_passive
from llm import prompts
from llm.contracts import ActiveSet, ClassInterpretation, PassiveSet
from llm.gateway import LLMError, generate

MIN_NONCOMBAT_ACTIVES = {"combat": 3, "balanced": 5, "social": 8}
MIN_NONCOMBAT_PASSIVES = {"combat": 4, "balanced": 5, "social": 7}
MIN_MECHANIC_PASSIVES = 6
OFFERED_MECHANICS = 14
MIN_WORLD_OFFERED = 3
SIGNATURE_OFFERED = 4      # drawn from the best thematic fits, so a class's signature options usually appear
ARCHETYPE_FAMILIES = {"warrior": ["warrior"], "mage": ["mage"], "rogue": ["rogue"], "support": ["healer"]}
PICKS = 2
SAVE_PATH = Path("saves/character.json")


def interpret_concept(concept: str) -> ClassInterpretation:
    return generate(
        "classify_concept", prompts.CLASSIFY_SYSTEM, concept,
        ClassInterpretation, temperature=0.3,
    )


def casting_attribute(interp: ClassInterpretation) -> str:
    if interp.casting_attribute:
        return interp.casting_attribute
    mental = [a for a in interp.primary_attributes if a in ("intelligence", "wisdom", "charisma")]
    return mental[0] if mental else "intelligence"


def generate_actives(interp: ClassInterpretation) -> list[Ability]:
    minimum = MIN_NONCOMBAT_ACTIVES[interp.focus]
    result = generate(
        "generate_actives", prompts.ACTIVES_SYSTEM, prompts.actives_user(interp, minimum),
        ActiveSet, max_tokens=3000,
        validation_context={"uses_companions": interp.uses_companions, "min_noncombat": minimum},
    )
    abilities = [materialize_active(p) for p in result.skills]
    discipline = casting_attribute(interp)
    for a in abilities:
        if a.resource.value == "mana":
            a.attribute = discipline
    return abilities


MECHANIC_PICKS = 8
STAT_PICKS = 7


def generate_passives(interp: ClassInterpretation, actives: list[Ability]) -> list[Passive]:
    """Two simpler steps: theme 8 drawn mechanics, then write 7 stat passives around them."""
    from llm.contracts import MechanicSet, PassiveProposal, StatPassiveSet
    minimum = MIN_NONCOMBAT_PASSIVES[interp.focus]
    taken = [a.name for a in actives]
    offered = draw_mechanics(interp)
    lines = []
    for oid, o in offered.items():
        m = MECHANICS[o.mechanic]
        cond = f" - only when: {TRIGGERS[o.when].condition.rstrip('.').lower()}" if o.when else ""
        tag = " (companions)" if m.companion_only else ""
        lines.append(f"{oid}: {m.kind}{tag} - {m.describe(o.strength(1))}{cond}")
    companion_ids = [k for k, o in offered.items() if MECHANICS[o.mechanic].companion_only]
    min_companion_mech = min(2, len(companion_ids)) if interp.uses_companions else 0
    world_ids = [k for k, o in offered.items() if MECHANICS[o.mechanic].kind == "world"]
    min_world_mech = min(2, len(world_ids))

    mechs = generate(
        "generate_passive_mechanics", prompts.MECH_PASSIVES_SYSTEM,
        prompts.mech_passives_user(interp, taken, lines, MECHANIC_PICKS, min_companion_mech, min_world_mech),
        MechanicSet, max_tokens=1800,
        validation_context={"offered": {k: o.mechanic for k, o in offered.items()}, "count": MECHANIC_PICKS,
                            "reserved_names": taken, "companion_options": companion_ids,
                            "min_companion": min_companion_mech, "world_options": world_ids, "min_world": min_world_mech},
    )
    chosen = [offered[c.option_id] for c in mechs.passives]
    world_chosen = sum(MECHANICS[o.mechanic].kind == "world" for o in chosen)
    companion_chosen = sum(MECHANICS[o.mechanic].companion_only for o in chosen)

    stat_scores, trigger_scores = fit.stat_scores(interp), fit.trigger_scores(interp)
    unavailable = fit.excluded(stat_scores) + fit.excluded(trigger_scores)
    cap = 5 if interp.focus == "social" else 3
    min_noncombat = min(cap, max(0, minimum - world_chosen))
    min_companion_stat = max(0, 3 - companion_chosen) if interp.uses_companions else 0
    names = taken + [c.name for c in mechs.passives]

    from character import history
    past = history.recent_stats(history.load())
    variety = ("\nRECENT CHARACTERS LEANED ON THESE STATS - prefer others unless one is central to this class: "
               + ", ".join(past)) if past else ""

    def stat_step(noncombat: int, companion: int, always: int):
        return generate(
            "generate_passive_stats", prompts.STAT_PASSIVES_SYSTEM,
            prompts.stat_passives_user(interp, names, STAT_PICKS, noncombat, fit.best_fits(stat_scores),
                                       fit.best_fits(trigger_scores), unavailable, companion) + variety,
            StatPassiveSet, max_tokens=1800,
            validation_context={"count": STAT_PICKS, "reserved_names": names, "unavailable": unavailable,
                                "min_noncombat": noncombat, "min_companion": companion, "max_always": always},
        )

    try:
        stats = stat_step(min_noncombat, min_companion_stat, 3)
    except LLMError:
        stats = stat_step(max(0, min_noncombat - 2), min(1, min_companion_stat), 5)
    out = []
    for c in mechs.passives:
        out.append(materialize_passive(PassiveProposal(name=c.name, description=c.description, kind="mechanic",
                                                       mechanic=c.option_id, tier=c.tier), offered))
    for p in stats.passives:
        out.append(materialize_passive(PassiveProposal(name=p.name, description=p.description, kind="stat",
                                                       modifies=p.modifies, trigger=p.trigger, tier=p.tier)))
    history.record(interp.custom_class, list(interp.families), sorted({o.mechanic for o in offered.values()}),
                   [offered[c.option_id].mechanic for c in mechs.passives], [p.modifies for p in stats.passives])
    return out


def draw_mechanics(interp: ClassInterpretation, rng: random.Random | None = None, runs: list[dict] | None = None) -> dict:
    """A fresh selection from the class's families. Distinctive options are favored over ones many classes share,
    and options past characters had are avoided - so every playthrough, and every class, feels its own."""
    from character import history
    rng = rng or random.Random()
    runs = history.load() if runs is None else runs
    families = interp.families or ARCHETYPE_FAMILIES.get(interp.archetype.value, ["warrior"])
    pool, seen = [], set()
    for fam in families:
        for o in FAMILIES[fam].options:
            m = MECHANICS[o.mechanic]
            if o.key in seen or (m.companion_only and not interp.uses_companions):
                continue
            seen.add(o.key)
            pool.append(o)
    KIN_WEIGHT = 0.15
    kin_keys = set()
    for fam in families:
        for kin in FAMILIES[fam].kin:
            if kin in families:
                continue
            for o in FAMILIES[kin].options:
                m = MECHANICS[o.mechanic]
                if o.key in seen or (m.companion_only and not interp.uses_companions):
                    continue
                seen.add(o.key)
                kin_keys.add(o.key)
                pool.append(o)
    shared = {}
    for f in FAMILIES.values():
        for mech in {o.mechanic for o in f.options}:
            shared[mech] = shared.get(mech, 0) + 1
    weight = {o.key: (1 / shared.get(o.mechanic, 1)) ** 0.8 * history.factor(o.mechanic, runs)
              * (KIN_WEIGHT if o.key in kin_keys else 1) for o in pool}

    def pick(cands, n):
        cands, out = list(cands), []
        while cands and len(out) < n:
            o = rng.choices(cands, weights=[weight[c.key] for c in cands])[0]
            out.append(o)
            cands = [c for c in cands if c.mechanic != o.mechanic]
        return out

    scores = fit.mechanic_scores(interp)
    ranked = sorted([o for o in pool if o.key not in kin_keys], key=lambda o: -scores.get(o.mechanic, 0))
    top = [o for o in ranked[:SIGNATURE_OFFERED * 3] if scores.get(o.mechanic, 0) > 0]
    chosen = pick(top, SIGNATURE_OFFERED)
    world = [o for o in pool if MECHANICS[o.mechanic].kind == "world" and o not in chosen]
    chosen += pick(world, max(0, MIN_WORLD_OFFERED - sum(MECHANICS[o.mechanic].kind == "world" for o in chosen)))
    rest = [o for o in pool if o not in chosen]
    chosen += pick(rest, OFFERED_MECHANICS - len(chosen))
    rng.shuffle(chosen)
    return {f"o{i}": o for i, o in enumerate(chosen, 1)}


def _check_pick_numbers(options: list, picks: list[int]) -> str | None:
    if len(picks) != PICKS or len(set(picks)) != PICKS:
        return f"exactly {PICKS} different choices are needed."
    bad = [n for n in picks if not 1 <= n <= len(options)]
    if bad:
        return f"there is no option numbered {', '.join(map(str, bad))}."
    return None


def check_active_picks(options: list[Ability], picks: list[int]) -> str | None:
    error = _check_pick_numbers(options, picks)
    if error:
        return error
    chosen = [options[n - 1] for n in picks]
    effects = {a.effect for a in chosen}
    if Effect.COMMAND in effects and Effect.SUMMON not in effects:
        return "a command ability needs a companion to command, so it must be paired with a summon ability."
    return None


def check_passive_picks(options: list[Passive], picks: list[int]) -> str | None:
    return _check_pick_numbers(options, picks)


def build_character(
    name: str,
    interp: ClassInterpretation,
    actives: list[Ability],
    passives: list[Passive],
    attributes: Attributes,
    aspiration: str | None,
) -> Character:
    return Character(
        name=name,
        archetype=interp.archetype,
        custom_class=interp.custom_class,
        class_summary=interp.summary,
        uses_companions=interp.uses_companions,
        primary_attributes=list(interp.primary_attributes),
        casting_attribute=casting_attribute(interp) if any(a.resource.value == "mana" for a in actives) else "",
        attributes=attributes,
        actives=actives,
        passives=passives,
        aspirations=[aspiration] if aspiration else [],
    )


def save_character(character: Character, path: Path = SAVE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(character.model_dump_json(indent=2), encoding="utf-8")
    return path


ATTRIBUTE_USES = {
    "strength": "heavy weapon attacks and raw force",
    "dexterity": "finesse weapons, bows, dodging and critical hits",
    "constitution": "health and stamina",
    "intelligence": "mana and arcane spells",
    "wisdom": "resisting fear and charm, and divine or natural magic",
    "charisma": "presence, performance and pact magic",
}


def attribute_guidance(interp: ClassInterpretation, actives: list[Ability]) -> list[str]:
    """Plain advice on which attributes this class actually uses, from its concept and its chosen abilities."""
    lines = []
    if interp.primary_attributes:
        main = ", ".join(f"{a} ({ATTRIBUTE_USES[a]})" for a in interp.primary_attributes)
        lines.append(f"Your {interp.custom_class} relies most on: {main}.")
    if any(a.resource.value == "mana" for a in actives):
        discipline = casting_attribute(interp)
        lines.append(f"Your spells belong to a discipline powered by {discipline}: every one of them uses {discipline} "
                     f"to land and to hit hard. Spells you learn later from other disciplines may use another attribute.")
    if not any(a.resource.value == "mana" for a in actives) and "intelligence" not in interp.primary_attributes:
        lines.append("None of your chosen abilities use mana, so intelligence matters little to you for now.")
    lines.append("Constitution sets your health and stamina for every class.")
    return lines
