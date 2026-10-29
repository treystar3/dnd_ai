"""What a new character wakes up with: a rudimentary weapon - or, for a class that keeps companions, a companion instead - and some coin.

A companion is a living creature, tamed, that grows with the player; it takes the weapon's place, unless the class's own words name the
weapon it fights with (f385: a beast-master whose class was "heavy bludgeon and rhythmic intimidation" woke with a worg and empty hands,
and punched its way through every fight); then it has both. (A summoner's Bound summon is not
part of the kit: it is made by its summon ability, engine/summons.py, and the summoner carries a weapon like anyone else.)

The model only chooses from lists. The engine builds the items, the companion and the purse.
"""

import re


from core.models import Character, Companion, Effect
from engine import items, money
from llm.contracts import StartingKit
from llm.gateway import generate
from world.loader import World

KIT_SYSTEM = """You equip a new character in a fantasy role-playing game with the plainest possible starting gear.
For an ordinary class, choose the one weapon id from WEAPON OPTIONS that best fits how they fight AND uses one of
  their STRONGEST ATTRIBUTES - a weapon driven by a weak attribute is nearly useless to them.
  HOW THEY FIGHT comes first: a spearman carries a spear whatever else they are, an archer a bow, a swordsman a sword.
  Casters use a focus (wand, staff, charm), performers an instrument, archers a bow or sling,
  and martial artists who fight bare-handed use hand wraps.
When COMPANION OPTIONS are listed, the class keeps a companion INSTEAD of a weapon: choose one creature id from them that fits
  their theme, give it a short fitting name, and leave weapon empty.
Respond only with JSON matching the schema."""

from llm.prompts import WORLD_FACTS
KIT_SYSTEM += "\n\n" + WORLD_FACTS

COMPANION_CATEGORIES = {"beast", "dragon", "monstrosity", "plant", "fey"}     # living things that grow - never made things


def weapon_options() -> list[items.BaseItem]:
    return [b for b in items.CATALOG.values() if b.is_weapon and not b.requires]


def companion_options(world: World) -> list:
    return [c for c in world.bestiary.values()
            if c.category in COMPANION_CATEGORIES and c.levels[0] <= 2 and not c.unique
            and c.roster and c.rarity in ("common", "uncommon") and "cracked_plains" not in c.biomes]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def weapon_words(b: items.BaseItem) -> set[str]:
    """The words a weapon answers to: its id, the words of its name and label, its tags, and the plain word inside a compound id
    (longsword: sword)."""
    out = {b.id} | set(b.tags) | set(re.findall(r"[a-z]+", f"{b.name} {b.label}".lower()))
    for w in list(out):
        for tail in ("sword", "axe", "bow", "staff", "hammer"):
            if w.endswith(tail) and w != tail:
                out.add(tail)
    return {w for w in out if len(w) >= 3}


AGENT_ENDINGS = ("", "s", "man", "men", "sman", "smen", "woman", "women", "er", "r", "ers", "rs")   # spearman, lancer, swordsmen, bows
CALLINGS = {"archer": "bow", "archers": "bow", "archery": "bow", "marksman": "bow", "knife": "dagger", "knives": "dagger",
            "bludgeon": "blunt", "bludgeons": "blunt", "cudgel": "club", "maul": "hammer", "mallet": "hammer", "flail": "blunt"}   # a calling or a plain word that names its weapon
GENERIC = {"heavy", "light", "simple", "thrown", "focus", "hand", "arcane", "warding", "blade"}     # (f385) words that fit many weapons and name none


def named_weapons(text: str, options: list) -> list:
    """The weapons the class's own words name: a word of theirs that is a weapon word, or one with an agent's ending on it (spearman,
    bowman, axeman, lancer, swordsman), or a calling that means one (archer). The engine decides this; the model only chooses among
    what fits, so a 'spearman hunter' is never handed a bow for the hunter in them."""
    said = {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) >= 3}
    said |= {CALLINGS[w] for w in said if w in CALLINGS}
    fits = []
    for b in options:
        words = weapon_words(b)
        if any(w == v + end for w in said for v in words for end in AGENT_ENDINGS):
            fits.append(b)
    return fits


def weapon_named(text: str, options: list) -> list:
    """(f385) The weapons a class's words name by a word of the weapon's own (hammer, bow, bludgeon), not one that fits many (heavy,
    light): what a companion class carries besides its companion."""
    said = {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) >= 3}
    said |= {CALLINGS[w] for w in said if w in CALLINGS}
    return [b for b in options if any(w == v + end for w in said for v in weapon_words(b) - GENERIC for end in AGENT_ENDINGS)]


def give_starting_kit(c: Character, class_text: str, uses_companions: bool, world: World) -> str:
    """Equip the character. Returns a plain description of what they received, for the narrator."""
    rules = items.RULES
    c.coins += money.to_smallest(**rules["starting_coins"])
    c.kit_given = True
    purse = money.fmt(money.to_smallest(**rules["starting_coins"]))

    made = next((a for a in c.actives if a.effect == Effect.SUMMON and a.id == c.bound_summon), None)
    bound = (f" {(made.summoned.name if made.summoned else made.name)}, the summon they made, stands bound to them."
             if made is not None else "")
    creatures = companion_options(world) if uses_companions else []
    if creatures:
        kit = _ask_kit(c, class_text, uses_companions, [], creatures)
        creature = world.bestiary[kit.companion]
        name = kit.companion_name.strip()
        c.companions.append(Companion(id=_slug(name) or creature.id, name=name, creature=creature.id,
                                      kind=creature.category, description=f"a {creature.name.lower()}",
                                      source="bonded before the player woke"))
        armed = weapon_named(f"{c.concept} {c.combat_identity} {c.custom_class}", weapon_options())
        if armed:                                                   # (f385) the class names what it fights with: it carries that too
            chosen = armed[0].id if len(armed) == 1 else _ask_kit(c, class_text, False, armed, []).weapon
            weapon = items.make(chosen, rules["starting_rarity"])
            c.equipment[items.base_of(weapon).slot] = weapon
            return (f"A {creature.name.lower()} named {name} is with them, bonded to them - their companion - and a {weapon.name} lies "
                    f"beside them; they carry a small purse of {purse}.{bound}")
        return (f"A {creature.name.lower()} named {name} is with them, bonded to them - their companion, in place of any weapon -"
                f" and they carry a small purse of {purse}.{bound}")
    options = weapon_options()
    if any(getattr(a, "channel", False) for a in c.actives):      # its channeled strikes need a melee weapon in hand (f260)
        options = [b for b in options if b.reach in ("melee", "extended") and b.damage == "physical"] or options
    named = named_weapons(f"{c.concept} {c.combat_identity} {c.custom_class}", options)        # (f342) a spearman carries a spear: the words decide
    if named:
        options = named
    if len(options) == 1:
        chosen = options[0].id
    else:
        chosen = _ask_kit(c, class_text, False, options, []).weapon
    weapon = items.make(chosen, rules["starting_rarity"])
    c.equipment[items.base_of(weapon).slot] = weapon
    return f"A {weapon.name} lies beside them, and they carry a small purse of {purse}.{bound}"


def _ask_kit(c: Character, class_text: str, uses_companions: bool, weapons: list, creatures: list):
    attrs = sorted(((a, getattr(c.attributes, a)) for a in type(c.attributes).model_fields), key=lambda x: -x[1])
    lines = [f"CLASS: {class_text}", f"RELIES ON COMPANIONS: {'yes' if uses_companions else 'no'}",
             f"STRONGEST ATTRIBUTES: {', '.join(f'{a} {v}' for a, v in attrs[:2])}"]
    if c.casting_attribute:
        lines.append(f"MAGIC USES: {c.casting_attribute} - a caster's focus should use this attribute "
                     "(wand: intelligence, charm: wisdom, lute: charisma).")
    if creatures:
        lines.append("COMPANION OPTIONS:\n" + "\n".join(f"  {b.id}: {b.name} ({b.category}, {b.size})" for b in creatures))
    if weapons:
        lines.append("WEAPON OPTIONS:\n" + "\n".join(f"  {b.id}: {b.name} ({b.reach}, {'/'.join(b.attributes)}, {', '.join(b.tags)})" for b in weapons))
    return generate(
        "starting_kit", KIT_SYSTEM, "\n".join(lines), StartingKit, temperature=0.3, max_tokens=200,
        validation_context={"needs_companion": bool(creatures), "weapons": [b.id for b in weapons],
                            "companions": [b.id for b in creatures]},
    )
