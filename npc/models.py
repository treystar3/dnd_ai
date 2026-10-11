"""NPC records. Created when an NPC is generated, then saved and only ever updated."""

from typing import Literal

from pydantic import BaseModel


class TraitChange(BaseModel):
    day: int
    removed: str
    added: str
    cause: str


class Memory(BaseModel):
    day: int
    turn: int
    text: str


class NPC(BaseModel):
    id: str
    name: str
    people: str
    role: str
    location: str
    tier: Literal["background", "known", "significant"] = "background"

    epithet: str = ""
    description: str = ""
    activity: str = ""

    traits: list[str] = []
    trait_history: list[TraitChange] = []
    personality: str = ""
    voice: str = ""
    concern: str = ""
    knowledge_groups: list[str] = []

    trust: int = 50
    motive: str = ""              # an active goal that moves forward off-screen; most people have none
    mood: str = ""                # how they've been lately, set by what has happened to them
    relations: dict[str, dict] = {}  # other NPC id -> {"score": -100..100, "feeling": "..."}
    gone: str = ""                # if they've left the story: how ("left for Riverhaven", "taken", "killed by wolves")
    protected: bool = False       # the pulse may never remove them
    easy_bonus: int = 0           # Easy Company: trust gained so far
    easy_day: int = -1
    name_known_to_player: bool = False
    knows_player_as: str = ""
    met_player: bool = False
    away_until: int = -1
    looks_away_until: int = -1    # a bribed person sees nothing until this game minute
    hidden: list[dict] = []       # story objects the player went looking for on this person: {"name", "description", "worth", "taken"}
    stock: list = []              # gear for sale (Item data), replaced on restock
    stock_day: int = -1           # day the current stock was laid out
    work_offer: dict | None = None  # paid work offered to the player: {task, pay, minutes}
    quest_offer: dict | None = None # a personal request offered to the player, waiting for a yes          # game minute until which they've stepped away (after ending a conversation)
    memories: list[Memory] = []

    def label(self) -> str:
        return self.name if self.name_known_to_player else (self.epithet or f"the {self.role.replace('_', ' ')}")
