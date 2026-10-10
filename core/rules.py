"""Game rules loaded from data/rules/. These files are the single source of truth.

ModifierTarget and Trigger are built from stats.yaml and triggers.yaml at import time,
so adding a stat or trigger to the YAML makes it available everywhere: the skill
generator, the validators and the engine.
"""

from enum import Enum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

RULES_DIR = Path(__file__).resolve().parent.parent / "data" / "rules"

ATTRIBUTES = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
ARCHETYPES = ("warrior", "mage", "rogue", "support")


class Suits(BaseModel):
    archetypes: list[str] = []
    themes: list[str] = []


class StatDef(BaseModel):
    id: str
    category: Literal["combat", "pool", "restoration", "exploration", "social", "knowledge", "companion"]
    effect: Literal["chance", "scale"]
    attribute: str | list[str] | None
    opposed_by: str | None = None
    noncombat: bool = False
    covers: str
    suits: Suits = Suits()

    @property
    def attributes(self) -> list[str]:
        if self.attribute is None:
            return []
        return [self.attribute] if isinstance(self.attribute, str) else list(self.attribute)


class TriggerDef(BaseModel):
    id: str
    condition: str
    checks: str
    context: Literal["combat", "out_of_combat", "anywhere"]
    noncombat: bool = False
    suits: Suits = Suits()


class RulesError(Exception):
    pass


def _load(path: Path, model) -> dict:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    items, problems = {}, []
    for i, entry in enumerate(raw, 1):
        try:
            item = model(**entry)
        except ValidationError as e:
            for err in e.errors():
                problems.append(f"{path.name} entry {i}: {'.'.join(map(str, err['loc']))}: {err['msg']}")
            continue
        if item.id in items:
            problems.append(f"{path.name}: duplicate id '{item.id}'")
        items[item.id] = item
    if problems:
        raise RulesError("\n".join(problems))
    return items


def _validate(stats: dict[str, StatDef], triggers: dict[str, TriggerDef]) -> None:
    problems = []
    for s in stats.values():
        for a in s.attributes:
            if a != "weapon" and a not in ATTRIBUTES:
                problems.append(f"stats.yaml {s.id}: unknown attribute '{a}'")
        if s.opposed_by and s.opposed_by not in stats:
            problems.append(f"stats.yaml {s.id}: opposed_by '{s.opposed_by}' is not a stat")
    for item in list(stats.values()) + list(triggers.values()):
        for a in item.suits.archetypes:
            if a not in ARCHETYPES:
                problems.append(f"{item.id}: suits unknown archetype '{a}'")
    if "always" not in triggers:
        problems.append("triggers.yaml must define 'always'")
    if problems:
        raise RulesError("Rules files have problems:\n" + "\n".join(f"  - {p}" for p in problems))


STATS: dict[str, StatDef] = _load(RULES_DIR / "stats.yaml", StatDef)
TRIGGERS: dict[str, TriggerDef] = _load(RULES_DIR / "triggers.yaml", TriggerDef)
_validate(STATS, TRIGGERS)

ModifierTarget = Enum("ModifierTarget", {s.upper(): s for s in STATS}, type=str)
Trigger = Enum("Trigger", {t.upper(): t for t in TRIGGERS}, type=str)

POOL_TARGETS = frozenset(ModifierTarget(s.id) for s in STATS.values() if s.category == "pool")
COMPANION_TARGETS = frozenset(ModifierTarget(s.id) for s in STATS.values() if s.category == "companion")
NONCOMBAT_TARGETS = frozenset(ModifierTarget(s.id) for s in STATS.values() if s.noncombat)
NONCOMBAT_TRIGGERS = frozenset(Trigger(t.id) for t in TRIGGERS.values() if t.noncombat)


class MechanicDef(BaseModel):
    id: str
    kind: Literal["combat", "world"]
    values: tuple[float, float]
    text: str
    companion_only: bool = False
    suits: Suits = Suits()

    def describe(self, value: float) -> str:
        return self.text.format(value=f"{value:g}")


ENGINE_COMBAT_MECHANICS = {
    "riposte", "aegis", "retribution", "vampiric", "executioner", "relentless", "regeneration", "last_stand",
    "hardening", "triumph", "windwalker", "phantom", "echoing", "unburdened", "cleave", "spellblade", "frostbite",
    "rending", "thunderous", "first_blood", "unyielding", "sanctified", "fearsome", "second_wind", "opportunist",
    "beastbane", "gravewarden", "giantsbane", "dragonslayer", "hellbane", "warbreaker", "dragonward", "graveward",
    "guardian", "bulwark", "spellmirror", "stormcaller", "wardbreaker", "hellward", "giantward", "killer_instinct",
    "piercing", "bloodlust", "battle_rhythm", "soul_harvest", "blinding", "terrify", "barrier", "mana_shield",
    "rally", "inspire", "battle_cry", "flurry", "deflect", "hex", "blood_pact",
}
ENGINE_WORLD_MECHANICS = {"trusted_face", "beast_friend", "danger_sense", "scavenger", "trailblazer", "keen_judge",
                          "tracker", "lucky_find", "thrifty", "masterwork", "quick_hands", "quick_study", "haggler",
                          "drillmaster", "veterans_eye", "town_defender", "safe_camp", "blood_price", "butcher",
                          "cache_hunter", "trap_sense", "forager", "wayfinder", "arcane_appraiser", "scholars_memory",
                          "dread_name", "grave_robber", "green_hands", "field_medic", "brewer", "good_employer",
                          "crowd_pleaser", "local_favorite", "familiar_forager", "oathbound", "almsgiver", "inner_calm",
                          "ascetic", "patron_whispers", "dark_charisma", "commission_broker", "lucky_break",
                          *""" weapon_wise soldiers_bearing campaigner victors_name delvers_wage night_watch helping_hand
                          road_warden shelter_earned patient_watch keeper_of_oaths raw_appetite wild_presence trophy_hunter
                          blood_warm restless fence_friend night_prowler second_look weather_wise hunters_larder game_warden
                          old_haunts bookish mana_well marked_by_gift spell_scholar arcane_echoes arcane_tutor deaths_ledger
                          bone_collector tomb_sleeper unsettling_presence last_possessions memento_mori speaker_for_wild
                          root_and_rot herb_wise bedside_manner apothecary mercy_remembered tireless_tending recruiter
                          born_to_rank rally_the_town quartermasters_friend silver_tongue sing_for_supper songs_of_the_road
                          gossips_ear stage_presence old_ballads easy_company faithful_guardian pack_instinct crowd_draw sniffer
                          second_eyes gentle_approach pack_beast mood_reader shared_rest honest_face righteous_hunt sanctuary
                          pilgrims_pace still_mind long_road_walker meditative_study quiet_step light_pack patrons_gift
                          forbidden_lore night_bound patron_dreams warded material_eye workshop_regular field_kit salvager
                          signature_work never_shoddy prospector known_craftsman""".split()}

MECHANICS: dict[str, MechanicDef] = _load(RULES_DIR / "passive_mechanics.yaml", MechanicDef)
_unknown = [m.id for m in MECHANICS.values()
            if m.id not in (ENGINE_COMBAT_MECHANICS if m.kind == "combat" else ENGINE_WORLD_MECHANICS)]
if _unknown:
    raise RulesError(f"passive_mechanics.yaml: the engine doesn't know how to run: {', '.join(_unknown)}")


class FamilyOption(BaseModel):
    mechanic: str
    when: str = ""
    values: tuple[float, float] | None = None

    @property
    def key(self) -> str:
        return f"{self.mechanic}@{self.when}" if self.when else self.mechanic

    def strength(self, tier_index: int) -> float:
        return (self.values or MECHANICS[self.mechanic].values)[tier_index]


class Family(BaseModel):
    description: str
    kin: list[str] = []        # kindred families whose options may occasionally be offered too
    options: list[FamilyOption]


def _load_families() -> dict[str, Family]:
    raw = yaml.safe_load((RULES_DIR / "passive_families.yaml").read_text(encoding="utf-8"))["families"]
    families, problems = {}, []
    for fid, data in raw.items():
        fam = Family(**data)
        for o in fam.options:
            if o.mechanic not in MECHANICS:
                problems.append(f"passive_families.yaml {fid}: unknown mechanic '{o.mechanic}'")
            if o.when and o.when not in TRIGGERS:
                problems.append(f"passive_families.yaml {fid}: unknown trigger '{o.when}'")
        families[fid] = fam
    if problems:
        raise RulesError("\n".join(problems))
    return families


FAMILIES: dict[str, Family] = _load_families()


def as_you(condition: str) -> str:  # noqa: C901
    """Turn a trigger condition into second person for the player: 'The character is above...' -> 'you are above...'."""
    text = condition.rstrip(".")
    if text.lower().startswith("the first round"):
        return "in the first round of a fight"
    for old, new in (("The character's", "your"), ("the character's", "your"), ("The character is", "you are"),
                     ("the character is", "you are"), ("The character", "you"), ("the character", "you"),
                     ("their target", "your target"), ("their health", "your health"), ("since their last turn", "since your last turn")):
        text = text.replace(old, new)
    return text[0].lower() + text[1:]
