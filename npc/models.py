"""NPC records. Created when an NPC is generated, then saved and only ever updated."""

from typing import Literal

from pydantic import BaseModel


class TraitChange(BaseModel):
    day: int
    removed: str
    added: str
    cause: str


class Memory(BaseModel):
    """One thing a person remembers. Kept as rows of the campaign's npc_memory table, not in the person's record: the record carries only
    the window the game reads (storage.campaign.MEMORY_WINDOW), the table keeps the rest. importance: 1 routine (bought bread), 2 worth
    keeping (a gift, a job done), 3 defining (a crime against them, a death, a betrayal): a defining memory is never pushed out of the
    window by routine ones. id: the row, once saved; None for a memory made this turn."""
    day: int
    turn: int
    text: str
    importance: int = 1
    kind: str = "event"
    id: int | None = None


class NPC(BaseModel):
    id: str
    name: str
    people: str
    role: str
    location: str
    gender: str = ""
    tier: Literal["background", "known", "significant"] = "background"

    epithet: str = ""
    description: str = ""
    activity: str = ""

    traits: list[str] = []
    trait_history: list[TraitChange] = []
    personality: str = ""
    voice: str = ""
    concern: str = ""
    concern_from: str = ""        # (f317) the matter (thread id) that put the concern there; the profile writer leaves such a concern alone
    anchor: str = ""              # (f317) one of the town's anchors (data/world/towns/<id>.yaml): the note that says who they are in the town
    knowledge_groups: list[str] = []

    trust: int = 50
    motive: str = ""              # an active goal that moves forward off-screen; most people have none
    mood: str = ""                # how they've been lately, set by what has happened to them
    mood_until: int = 0           # (f331) the game minute a mood the world gave them fades (engine/drift.py); 0 for one with no clock yet
    motive_done_at: int = -1      # (f331) the minute a motive ended (achieved or given up), -1 for never; after a while a new one may take hold
    motive_since: int = 0         # (f334) the minute the motive took hold; 0 for one from before this was kept
    motive_step: int = 0          # (f360) how many steps the engine has moved their goal (data/rules/motives.yaml)
    relations: dict[str, dict] = {}  # other NPC id -> {"score": -100..100, "feeling": "..."}
    gone: str = ""                # if they've left the story: how ("left for Riverhaven", "taken", "killed by wolves")
    protected: bool = False       # the pulse may never remove them
    easy_bonus: int = 0           # Easy Company: trust gained so far
    easy_day: int = -1
    name_known_to_player: bool = False
    knows_player_as: str = ""
    met_player: bool = False
    last_talk_day: int = -1       # (f362) the game day of the last conversation: the first talk of a day moves trust (engine/trust.py)
    away_until: int = -1
    looks_away_until: int = -1    # a bribed person sees nothing until this game minute
    hidden: list[dict] = []       # story objects the player went looking for on this person: {"name", "description", "worth", "taken"}
    stock: list = []              # gear for sale (Item data), replaced on restock
    stock_day: int = -1           # day the current stock was laid out
    journal_note: str = ""        # one sentence about them for the player's journal, written by them in a normal reply
    note_trust: int = -1          # their trust in the player when the note was written
    note_mem: int = 0             # how many memories they had then; the note is rewritten after big changes
    work_offer: dict | None = None  # paid work offered to the player: {task, pay, minutes}
    quest_offer: dict | None = None # a personal request offered to the player, waiting for a yes          # game minute until which they've stepped away (after ending a conversation)
    heard_of: dict = {}           # someone else named them to the player before they met: {"by": speaker, "day": n, "line": what was said}
    speech: dict = {}             # (f347) who they are when they speak: the culture that raised them and how it shows (engine/voice_profile.py); rolled when first spoken to
    said: list[str] = []          # (f347) their last few replies to the player, so they do not say the same thing twice (llm/contracts.py NPCReply)
    heard: list[str] = []         # (f347) what the player said to draw each of those, so the same question may get much the same answer
    memories: list[Memory] = []   # the window of what they remember (see Memory); the table npc_memory holds all of it
    memory_total: int = 0         # how many they hold in all (read from the table on load; not saved in the record)

    def label(self) -> str:
        return self.name if self.name_known_to_player else (self.epithet or f"the {self.role.replace('_', ' ')}")
