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
    SCOUT = "scout"
    SUPPORT = "support"


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


class CompanionTemplate(BaseModel):
    id: str
    name: str
    description: str
    kind: CompanionKind
    role: CompanionRole
    tier: PowerTier
    health: int
    damage: int


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
    potency: int
    cost: int
    cooldown: int
    companion: CompanionTemplate | None = None
    attribute: str = ""   # for mana abilities: the attribute of the magic discipline it belongs to


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
    quantity: int = 1       # stack size for goods and raw materials


class KeyItem(BaseModel):
    """A story object: a pendant, a map, a ledger, a letter. Takes no pack slot, can't be sold or dropped, survives death."""
    id: str
    name: str
    description: str = ""
    kind: Literal["key", "quest"] = "key"     # quest items are tied to a task; key items are simply yours
    source: str = ""                           # who gave it, or where it came from
    day: int = 0
    for_whom: str = ""                         # quest items: who it is meant to reach


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
    uses_companions: bool = False
    primary_attributes: list[str] = []
    casting_attribute: str = ""
    attributes: Attributes = Attributes()
    actives: list[Ability] = []
    passives: list[Passive] = []
    knowledge: list[str] = []
    unspent_points: int = 0
    xp: int = 0
    deaths: int = 0
    last_rest: str = ""
    health: float | None = None
    stamina: float | None = None
    mana: float | None = None
    coins: int = 0  # in copper; see engine/money.py
    equipment: dict[str, Item] = {}
    inventory: list[Item] = []
    key_items: list[KeyItem] = []
    item_history: list[str] = []               # key and quest items delivered or let go, for the journal
    crafting_skill: float = 0                  # 0-100, grows with practice
    trained: dict[str, int] = {}               # lasting check bonuses from tutoring, by check
    last_drill_day: int = -1
    patron_gift_day: int = -100
    whisper_day: int = -1                      # patron's whisper: the day it was last used
    phoenix_day: int = -10000                  # the day a Phoenix item last brought the wearer back from a killing blow
    companions: list[Companion] = []
    allocation_log: list[AllocationRecord] = []
    kit_given: bool = False
    location: str = "unknown"
    aspirations: list[str] = []


class GameState(BaseModel):
    day: int = 1
    turn: int = 0
    pulse_meter: float = 0.0
    player: Character | None = None
