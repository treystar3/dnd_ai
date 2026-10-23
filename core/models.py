"""Authoritative game state. Only engine code constructs or mutates these."""

from enum import Enum

from typing import Literal

from pydantic import BaseModel, Field


class Archetype(str, Enum):
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    SUPPORT = "support"


class Effect(str, Enum):
    DAMAGE = "damage"
    HEALING = "healing"
    CONTROL = "control"
    DEFENSE = "defense"
    MOBILITY = "mobility"
    UTILITY = "utility"
    INFLUENCE = "influence"
    SUMMON = "summon"
    COMMAND = "command"
    CRAFTING = "crafting"
    BUFF = "buff"


class PowerTier(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class Reach(str, Enum):
    SELF = "self"
    MELEE = "melee"
    EXTENDED = "extended"
    RANGED = "ranged"
    AREA = "area"


class Resource(str, Enum):
    STAMINA = "stamina"
    MANA = "mana"


class UseContext(str, Enum):
    COMBAT = "combat"
    OUT_OF_COMBAT = "out_of_combat"
    BOTH = "both"


class CompanionKind(str, Enum):
    SPIRIT = "spirit"
    BEAST = "beast"
    UNDEAD = "undead"
    ELEMENTAL = "elemental"
    CONSTRUCT = "construct"
    HUMANOID = "humanoid"


class CompanionRole(str, Enum):
    STRIKER = "striker"
    GUARDIAN = "guardian"
    ROGUE = "rogue"
    HEALER = "healer"
    SUPPORT = "support"

    @classmethod
    def _missing_(cls, value):
        if value == "scout":
            return cls.ROGUE
        return None


from core.rules import (  # noqa: E402  - stats and triggers are defined in data/rules/*.yaml
    COMPANION_TARGETS,
    NONCOMBAT_TARGETS,
    NONCOMBAT_TRIGGERS,
    POOL_TARGETS,
    ModifierTarget,
    Trigger,
)


class Attributes(BaseModel):
    strength: int = Field(10, ge=1)
    dexterity: int = Field(10, ge=1)
    constitution: int = Field(10, ge=1)
    intelligence: int = Field(10, ge=1)
    wisdom: int = Field(10, ge=1)
    charisma: int = Field(10, ge=1)


class Summoned(BaseModel):
    """What a summon ability makes, as the model named and described it. Its form and size are the engine's (engine/summons.py)."""
    name: str
    description: str = ""


class Ability(BaseModel):
    id: str
    name: str
    description: str
    effect: Effect
    tier: PowerTier
    reach: Reach
    resource: Resource
    context: UseContext
    tags: list[str] = []
    cost: int
    cooldown: int
    summon_form: str = ""        # for a summon: the form it makes - bound, sentinel, striker, swarm, totem, decoy, volatile
    summoned: Summoned | None = None   # for a summon: what it makes, as named
    attribute: str = ""   # for mana abilities: the attribute of the magic discipline it belongs to
    rider: str = ""       # an extra thing it does when it lands (engine/ability_traits.py)
    shape: str = ""       # how a damage ability delivers its damage
    buff: str = ""        # for the buff effect: bulwark, thorns or mend
    command: str = ""     # for the command effect: focus, guard, press or hold
    buff_stat: str = ""   # for bulwark: armor, ward or both
    channel: bool = False  # a mana strike delivered through the wielded weapon (engine/combat.py)
    movement: str = ""     # for mobility: the engine-owned movement kind it performs (data/rules/movement.yaml)
    heal_form: str = ""    # for healing: how it restores - mend, renew, ward, cleanse, transfer or rescue (data/rules/healing.yaml)
    expressions: list[str] = []   # what its element does: each rides on every hit, or is part of a control spell (data/rules/spellcraft.yaml)
    power: float = 0       # its own damage multiplier in place of its tier's (0 = the tier's) - for abilities taught with their own numbers
    cost_percent: float = 0  # its own cost, a percent of the pool, in place of its tier's (0 = the tier's)
    cast_turns: int = 0    # turns it takes to use, the first included (0 = one, or two for a charged spell)
    martial_form: str = ""  # a technique: strike, sweep, flurry, windup or counter (data/rules/martial.yaml)
    hits: int = 0          # a flurry: how many hits
    maneuver: str = ""     # a technique's maneuver: trip, hamstring, rend, disarm, stagger, pin, shove, hook, sunder or feint
    spell_form: str = ""   # a mana damage spell: bolt, blast, burst, curse or charged (data/rules/spellcraft.yaml)
    element: str = ""      # the element it carries, set by the engine when it was planned; the model only narrates it
    field_use: str = ""   # what it does outside combat: scout, shelter, haste, influence, shadow, recall or showmanship (engine/field.py)


class Passive(BaseModel):
    """Either a stat bonus (modifies + trigger + magnitude) or a mechanic (mechanic + value)."""
    id: str
    name: str
    description: str
    modifies: ModifierTarget | None = None
    trigger: Trigger | None = None
    tier: PowerTier
    tags: list[str] = []
    magnitude: int = 0
    mechanic: str = ""
    when: str = ""
    value: float = 0
    subject: str = ""     # a perk's chosen subject, when it has one (Sworn Enemy: the creature category)

    def effect_text(self) -> str:
        if self.mechanic:
            from core.rules import MECHANICS, TRIGGERS, as_you
            m = MECHANICS.get(self.mechanic)
            text = m.describe(self.value) if m else self.mechanic
            if self.when and self.when in TRIGGERS:
                cond = as_you(TRIGGERS[self.when].condition)
                text = f"{text.rstrip('.')} - only {'' if cond.startswith('in the first') else 'when '}{cond}."
            return text
        when = "always" if self.trigger.value == "always" else self.trigger.value.replace("_", " ")
        return f"+{self.magnitude}% {self.modifies.value.replace('_', ' ')}, {when}"


class ItemProperty(BaseModel):
    modifies: str
    trigger: str = "always"
    magnitude: int


class Enchantment(BaseModel):
    id: str
    name: str
    suffix: str = ""
    effects: list[ItemProperty] = []
    flags: dict[str, float] = {}


class Item(BaseModel):
    """A specific item. Its numbers are computed from its base, rarity and level by engine/items.py."""
    uid: str
    base: str
    name: str
    rarity: str = "common"
    item_level: int = 1
    source: str = ""                           # "your own work" for gear the player crafted
    material: str = ""
    gem: str = ""
    properties: list[ItemProperty] = []
    description: str = ""
    title: str = ""
    legendary_effect: str = ""
    trait: dict = {}        # a ring or amulet's always-on gift: {"id", "text", "effects", "fight", "world"} (engine/accessories.py)
    relic: dict = {}        # a ring or amulet's power: {"id", "name", "text", "kind", "value", "uses", "cooldown"} (engine/relics.py)
    enchantments: list[Enchantment] = []
    good: str = ""          # for goods (herbs, food, consumables): the id in goods.yaml
    origin: str = ""        # for meat and what is cooked from it: the family of the beast it came from, when the player hunted it (Symbiosis)
    quantity: int = 1       # stack size for goods and raw materials
    reforged: bool = False  # its rolls have been reforged once; never again


class KeyItem(BaseModel):
    """A story object: a pendant, a map, a ledger, a letter. Takes no pack slot, can't be sold or dropped, survives death."""
    id: str
    name: str
    description: str = ""
    kind: Literal["key", "quest"] = "key"     # quest items are tied to a task; key items are simply yours
    source: str = ""                           # who gave it, or where it came from
    day: int = 0
    for_whom: str = ""                         # quest items: who it is meant to reach
    opens: str = ""                            # a key: the id of the lock it opens (see engine/locks.py)


class Companion(BaseModel):
    id: str
    name: str
    creature: str = ""
    kind: str = ""
    role: str = ""
    level: int = 1
    description: str = ""
    source: str = ""
    tier: str = "light"          # the power tier of the ability that summoned it (a spirit's size follows it)
    health: int = 0              # the stored template numbers; the role-and-tier build of a summoned spirit
    damage: int = 0
    perks: dict[str, float] = {}  # world bonuses the creature brings: passive mechanic id -> value (a gifted animal)
    fallen: bool = False         # went down in a fight; sits out until recover_at (or is called back by its summon ability)
    recover_at: int = 0          # game minute when a fallen companion is on its feet again
    dead: bool = False           # a beast that did not survive being downed; only a revival brings it back

    @property
    def active(self) -> bool:
        return not (self.fallen or self.dead)


class AllocationRecord(BaseModel):
    level: int
    spend: dict[str, int]


class Character(BaseModel):
    id: str = "player"
    name: str
    level: int = 1
    archetype: Archetype
    custom_class: str
    class_summary: str = ""
    combat_identity: str = ""                  # how the class fights, in the reading's words ("Spear and mobility"): the kit answers to it
    concept: str = ""                          # the player's own words at the Threshold ("a centaur spearman hunter")
    uses_companions: bool = False      # keeps companions: tamed, living creatures that grow with them
    summoner: bool = False             # makes summons with magic (engine/summons.py); a summon is never a companion
    bound_summon: str = ""             # the summon ability whose Bound summon walks with them now
    bound_broken: bool = False         # that Bound summon was unmade in a fight and has not been cast again
    primary_attributes: list[str] = []
    casting_attribute: str = ""
    elements: list[str] = []                   # the concept's named element palette: abilities learned later draw from it too
    attributes: Attributes = Attributes()
    actives: list[Ability] = []                # the book: every ability learned (engine/loadout.py)
    prepared: list[str] = []                   # the ids of the abilities brought - spells and techniques each have their own room
    book_seen: list[str] = []                  # abilities the loadout has already considered (a newly learned one comes along if there is room)
    loadout_day: int = 0                       # the day the loadout was last changed (once a day)
    loadout_free: bool = True                  # the first change costs nothing
    prebuffs: list[str] = []                   # combat buffs cast as the opening of a fight you start yourself (#prebuff, f247)
    loadout_room: int = 0                      # the room the loadout last had (when a level brings more, the book fills it)
    passives: list[Passive] = []
    knowledge: list[str] = []
    unspent_points: int = 0
    xp: int = 0
    deaths: int = 0
    last_rest: str = ""
    hunger: float = 0.0                        # 0 fed .. 100 famished (engine/needs.py)
    fatigue: float = 0.0                       # 0 rested .. 100 collapsing
    health: float | None = None
    stamina: float | None = None
    mana: float | None = None
    coins: int = 0  # in copper; see engine/money.py
    equipment: dict[str, Item] = {}
    inventory: list[Item] = []
    key_items: list[KeyItem] = []
    item_history: list[str] = []               # key and quest items delivered or let go, for the journal
    crafting_skill: float = 0                  # no upper bound, grows with practice (slowly once high)
    trained: dict[str, int] = {}               # lasting check bonuses from tutoring, by check
    last_drill_day: int = -1
    patron_gift_day: int = -100
    whisper_day: int = -1                      # patron's whisper: the day it was last used
    recipes_made: list[str] = []               # gear bases made at a workshop, which Practiced Hands can make anywhere after
    studied: dict[str, str] = {}               # Reverse Engineer: gear bases studied overnight -> the finest rarity studied of each
    gift: dict = {}                            # Symbiosis: {"family", "mechanics": {id: value}} from a meal of your own hunt, until you sleep
    orenna_breath: bool = False                # the blessing of Orenna's Last Breath, unspent (see data/world/orenna.yaml)
    phoenix_day: int = -10000                  # the day a Phoenix item last brought the wearer back from a killing blow
    companions: list[Companion] = []
    allocation_log: list[AllocationRecord] = []
    kit_given: bool = False
    location: str = "unknown"
    aspirations: list[str] = []

