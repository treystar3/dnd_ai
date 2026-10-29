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
from llm.contracts import ActiveSet, ClassInterpretation
from llm.gateway import LLMError, generate

MIN_NONCOMBAT_ACTIVES = {"combat": 3, "balanced": 5, "social": 8}
MIN_NONCOMBAT_PASSIVES = {"combat": 4, "balanced": 5, "social": 7}
MIN_MECHANIC_PASSIVES = 6
OFFERED_MECHANICS = 18     # creation offers mechanics only (B8): flat stat passives stay learnable from trainers and gear
MIN_WORLD_OFFERED = 3
DRAW = __import__("yaml").safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "perks.yaml").read_text(encoding="utf-8"))["draw"]
SIGNATURE_OFFERED = 4      # drawn from the class's own families by thematic fit: the spine of every offer
ARCHETYPE_FAMILIES = {"warrior": ["warrior"], "mage": ["mage"], "rogue": ["rogue"], "support": ["healer"]}
PICKS = 3                  # abilities and passives the player keeps at creation, each
SAVE_PATH = Path("saves/character.json")


def interpret_concept(concept: str, who: str = "") -> ClassInterpretation:
    """`who` (f388): how the player already looks ("A stocky dwarf woman..."), so the reading does not make a dwarf woman 'a mountain of a
    man'."""
    from llm.contracts import AskedInterpretation
    text = (f"WHO THEY ARE (already chosen; describe them as this, never otherwise): {who}\n\nWHO THEY WANT TO BECOME: {concept}" if who else concept)
    got = generate("classify_concept", prompts.CLASSIFY_SYSTEM, text, AskedInterpretation, temperature=0.3)   # families required (f250)
    return ClassInterpretation(**got.model_dump())


def casting_attribute(interp: ClassInterpretation) -> str:
    if interp.casting_attribute:
        return interp.casting_attribute
    mental = [a for a in interp.primary_attributes if a in ("intelligence", "wisdom", "charisma")]
    return mental[0] if mental else "intelligence"


def generate_actives(interp: ClassInterpretation, rng: random.Random | None = None) -> list[Ability]:
    """Slot-based: the engine plans all 15 abilities (see engine/ability_slots.py); the model only names and describes them.
    The old single-call generation stays as a fallback if the planned set cannot be built."""
    minimum = MIN_NONCOMBAT_ACTIVES[interp.focus]
    from engine import ability_slots, ability_traits
    from llm.contracts import SlotNames
    offers = ability_traits.draw_offers(interp, rng, min_functions=minimum)
    try:
        slots = ability_slots.plan(interp, offers, minimum, rng)
        context = {"slots": slots, "strict": True}
        try:
            names = generate("generate_actives", prompts.SLOTS_SYSTEM, prompts.slots_user(interp, ability_slots.slot_lines(slots)),
                             SlotNames, max_tokens=2600, validation_context=context)
        except LLMError:
            context = {"slots": slots, "strict": False}       # the words do not quite match a slot: take them, the engine's slot stands
            names = generate("generate_actives", prompts.SLOTS_SYSTEM, prompts.slots_user(interp, ability_slots.slot_lines(slots)),
                             SlotNames, max_tokens=2600, retries=1, validation_context=context)
        result = ActiveSet.model_validate({"skills": [p.model_dump() for p in names.proposals(slots)]},
                                          context={"uses_companions": interp.uses_companions, "summoner": getattr(interp, "summoner", False), "min_noncombat": minimum, "offers": offers,
                                                   "planned": True})
    except (ValueError, KeyError):
        return _generate_actives_single(interp, minimum, offers)
    return _finish_actives(interp, result)


def _finish_actives(interp: ClassInterpretation, result: ActiveSet) -> list[Ability]:
    abilities = [materialize_active(p) for p in result.skills]
    discipline = casting_attribute(interp)
    for a in abilities:
        if a.resource.value == "mana":
            a.attribute = discipline
    return abilities


def _generate_actives_single(interp: ClassInterpretation, minimum: int, offers: dict) -> list[Ability]:
    """The earlier flow: one call in which the model chooses every mechanic itself, then the engine repairs."""
    from engine import ability_traits
    result = generate(
        "generate_actives", prompts.ACTIVES_SYSTEM, prompts.actives_user(interp, minimum, ability_traits.offer_lines(offers)),
        ActiveSet, max_tokens=3600,
        validation_context={"uses_companions": interp.uses_companions, "summoner": getattr(interp, "summoner", False), "min_noncombat": minimum, "offers": offers},
    )
    return _finish_actives(interp, result)


class PassivesInBackground:
    """Passives only need the NAMES of the fifteen actives, so they are written while the player reads and picks abilities.
    result() waits for them (with a short note if they are not ready) and tries once more, blocking, if the background attempt failed."""

    def __init__(self, interp: ClassInterpretation, actives: list[Ability]):
        import threading
        self.interp, self.actives = interp, actives
        self.value: list[Passive] | None = None
        self.error: Exception | None = None
        self.done = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self) -> None:
        try:
            self.value = generate_passives(self.interp, self.actives)
        except Exception as e:                     # reported by result(), which retries
            self.error = e
        finally:
            self.done.set()

    @property
    def ready(self) -> bool:
        return self.done.is_set()

    def result(self) -> list[Passive]:
        self.done.wait()
        if self.value is not None:
            return self.value
        return generate_passives(self.interp, self.actives)


MECHANIC_PICKS = 15        # all fifteen offers are mechanics; the model themes them, the engine owns what they do
STAT_PICKS = 7             # trainers still teach stat passives (scenes/training_actions.py); creation no longer offers them


def generate_passives(interp: ClassInterpretation, actives: list[Ability], rng: random.Random | None = None) -> list[Passive]:
    """One step since B8: every offer is a mechanic - something that changes how a fight or a day plays, never a bare number. The model
    only names and describes the drawn mechanics; flat stat passives remain, at the trainers."""
    from llm.contracts import MechanicSet, PassiveProposal
    minimum = MIN_NONCOMBAT_PASSIVES[interp.focus]
    taken = [a.name for a in actives]
    offered = draw_mechanics(interp, rng)              # a given rng (the tests) makes the draw repeatable; play draws fresh
    lines = []
    for oid, o in offered.items():
        m = MECHANICS[o.mechanic]
        cond = f" - only when: {TRIGGERS[o.when].condition.rstrip('.').lower()}" if o.when else ""
        tag = " (companions)" if m.companion_only else ""
        lines.append(f"{oid}: {m.kind}{tag} - {m.describe(o.strength(1))}{cond}")
    companion_ids = [k for k, o in offered.items() if MECHANICS[o.mechanic].companion_only]
    min_companion_mech = min(3, len(companion_ids)) if (interp.uses_companions or getattr(interp, "summoner", False)) else 0
    world_ids = [k for k, o in offered.items() if MECHANICS[o.mechanic].kind == "world"]
    min_world_mech = min(max(2, minimum - 3), len(world_ids))
    count = min(MECHANIC_PICKS, len(offered))

    mechs = generate(
        "generate_passive_mechanics", prompts.MECH_PASSIVES_SYSTEM,
        prompts.mech_passives_user(interp, taken, lines, count, min_companion_mech, min_world_mech),
        MechanicSet, max_tokens=2600,
        validation_context={"offered": {k: o.mechanic for k, o in offered.items()}, "count": count,
                            "reserved_names": taken, "companion_options": companion_ids,
                            "min_companion": min_companion_mech, "world_options": world_ids, "min_world": min_world_mech},
    )
    out = []
    for c in mechs.passives:
        made = materialize_passive(PassiveProposal(name=c.name, description=c.description, kind="mechanic",
                                                   mechanic=c.option_id, tier=c.tier), offered)
        if made.mechanic == "sworn_enemy":
            made.subject = sworn_subject(interp)
            made.description = f"{made.description} (sworn against: {made.subject})"
        out.append(made)
    return out


SWORN_WORDS = {"dragon": ("dragon", "wyrm", "drake", "dragoon"), "undead": ("undead", "grave", "death", "bone", "ghost"),
               "beast": ("beast", "hunter", "wild", "wolf", "ranger"), "giant": ("giant", "troll", "mountain"),
               "fiend": ("demon", "devil", "fiend", "hell", "exorcist"), "hostile people": ("bandit", "outlaw", "war", "bounty")}


def sworn_subject(interp) -> str:
    """The foe-kind a Sworn Enemy perk is sworn against, read from the class's own themes; beasts when nothing says."""
    hay = " ".join(list(interp.themes or []) + [interp.custom_class, interp.combat_identity or ""]).lower()
    for category, words in SWORN_WORDS.items():
        if any(w in hay for w in words):
            return category
    return "beast"


def class_archetypes(interp: ClassInterpretation) -> set[str]:
    """Every archetype this character could realistically grow into: what they were classified as, what their own families lean
    (read from the families' options), and mage when they cast at all. A perk outside this set is a dead option for them, never a
    dormant one, and is not drawn. Derived from the data - nothing here is a hand list."""
    lean = DRAW["archetype_lean"]
    out = {interp.archetype.value}
    for fam in interp.families or ARCHETYPE_FAMILIES.get(interp.archetype.value, ["warrior"]):
        opts = [MECHANICS[o.mechanic] for o in FAMILIES[fam].options if o.mechanic in MECHANICS]
        tagged = [m for m in opts if m.suits.archetypes]
        for a in {a for m in tagged for a in m.suits.archetypes}:
            if sum(a in m.suits.archetypes for m in tagged) >= lean * max(1, len(tagged)):
                out.add(a)
    if getattr(interp, "casting_attribute", ""):
        out.add("mage")
    return out


def usable_by(m, archetypes: set[str]) -> bool:
    """A world perk, an untagged perk, or one tagged with any of the character's archetypes."""
    return m.kind == "world" or not m.suits.archetypes or bool(set(m.suits.archetypes) & archetypes)


def draw_mechanics(interp: ClassInterpretation, rng: random.Random | None = None,
                   where: str = "creation") -> dict:
    """A fresh selection, memoryless and ungated by the rolled abilities (the world teaches abilities too, so a perk whose fuel is
    missing is an invitation). Families are a lean, not a wall: the signature slots come from the class's own families by thematic
    fit, and the rest is drawn from every perk the character could ever use - own families weigh most, kin next, the rest of the
    world least (data/rules/perks.yaml draw:). The only perks never drawn are dead ones: outside every archetype the character
    could grow into (class_archetypes), or a companion perk for a class without companions."""
    rings = DRAW["rings"]
    rng = rng or random.Random()
    families = interp.families or ARCHETYPE_FAMILIES.get(interp.archetype.value, ["warrior"])
    archetypes = class_archetypes(interp)
    own = {o.mechanic for f in families for o in FAMILIES[f].options}
    kin = {o.mechanic for f in families for k in FAMILIES[f].kin if k not in families for o in FAMILIES[k].options} - own
    option_of = {}
    for f in list(families) + [k for f in families for k in FAMILIES[f].kin] + list(FAMILIES):
        for o in FAMILIES[f].options:
            option_of.setdefault(o.mechanic, o)               # the option a perk is offered through: its own family's first
    pool = []
    for mid, o in option_of.items():
        m = MECHANICS.get(mid)
        if m is None or m.where != where or (m.companion_only and not (interp.uses_companions or getattr(interp, "summoner", False))):
            continue
        if set(m.needs) & set(DRAW.get("dormant_needs") or []):
            continue                                          # its fuel does not exist yet (stances): never drawn
        if any(not getattr(interp, flag, False) for need, flag in (DRAW.get("class_needs") or {}).items() if need in m.needs):
            continue                                          # its fuel is not this class's (a summon perk for a non-summoner, f269)
        if mid not in own and mid not in kin and where != "creation":
            continue                                          # instructors teach within the class's families; creation reaches further
        if mid not in own and not usable_by(m, archetypes):
            continue                                          # beyond the class's own families, only what it could ever use
        pool.append(o)
    shared = {}
    for f in FAMILIES.values():
        for mech in {o.mechanic for o in f.options}:
            shared[mech] = shared.get(mech, 0) + 1
    ring = {o.key: rings["own"] if o.mechanic in own else rings["kin"] if o.mechanic in kin else rings["foreign"] for o in pool}
    power = DRAW.get("shared_power", 0.8)                     # how much a perk one family owns outweighs one many share (perks.yaml draw)
    weight = {o.key: (1 / shared.get(o.mechanic, 1)) ** power * ring[o.key] for o in pool}

    def pick(cands, n):
        cands, out = list(cands), []
        while cands and len(out) < n:
            o = rng.choices(cands, weights=[weight[c.key] for c in cands])[0]
            out.append(o)
            cands = [c for c in cands if c.mechanic != o.mechanic]
        return out

    scores = fit.mechanic_scores(interp)
    ranked = sorted([o for o in pool if o.mechanic in own], key=lambda o: -scores.get(o.mechanic, 0))
    top = [o for o in ranked[:SIGNATURE_OFFERED * 3] if scores.get(o.mechanic, 0) > 0]
    chosen = pick(top, SIGNATURE_OFFERED)
    taken = {o.mechanic for o in chosen}
    world = [o for o in pool if MECHANICS[o.mechanic].kind == "world" and o.mechanic not in taken]
    chosen += pick(world, max(0, MIN_WORLD_OFFERED - sum(MECHANICS[o.mechanic].kind == "world" for o in chosen)))
    taken = {o.mechanic for o in chosen}
    rest = [o for o in pool if o.mechanic not in taken]
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


def check_active_picks(options: list[Ability], picks: list[int], keeps_companions: bool = False) -> str | None:
    """A command needs something to command: the companion a tamer wakes with (the kit), or a summon ability among the picks."""
    error = _check_pick_numbers(options, picks)
    if error:
        return error
    chosen = [options[n - 1] for n in picks]
    effects = {a.effect for a in chosen}
    if Effect.COMMAND in effects and Effect.SUMMON not in effects and not keeps_companions:
        return "a command ability needs something to command, so it must be paired with a summon ability."
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
    concept: str = "",
    who: dict | None = None,
) -> Character:
    """`who` (f388): the first page's choices (engine/look.py clean): people, pronoun, look, and the sentence the world sees."""
    from engine import look as look_mod
    seen = look_mod.clean(who) if who else None
    return Character(
        pronoun=seen["pronoun"] if seen else "",
        people=seen["people"] if seen else "",
        look={k: seen[k] for k in ("look", "flags", "extra")} if seen else {},
        look_text=look_mod.describe(seen) if seen else "",
        name=name,
        archetype=interp.archetype,
        custom_class=interp.custom_class,
        class_summary=interp.summary,
        combat_identity=getattr(interp, "combat_identity", "") or "",
        concept=concept,
        uses_companions=interp.uses_companions, summoner=bool(getattr(interp, "summoner", False)),
        primary_attributes=list(interp.primary_attributes),
        elements=list(getattr(interp, "elements", []) or []),
        casting_attribute=casting_attribute(interp) if any(a.resource.value == "mana" for a in actives) else "",
        attributes=attributes,
        actives=actives,
        passives=passives,
        bound_summon=next((a.id for a in actives if a.summon_form == "bound"), ""),    # a summoner wakes with its Bound summon made
        aspirations=[aspiration] if aspiration else [],
        knowledge=["orenna_name"],        # the goddess at the Threshold gave her name; nobody living has heard it
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
