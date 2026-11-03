"""NPC records. Created when an NPC is generated, then saved and only ever updated."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


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
    kind: str = "experienced"   # (f478) experienced, witnessed, noticed, heard, told, own_life, ... (engine/memory.py KINDS)
    subject: str = "player"     # (f478) whom it is about: a character's id ("player" today), a person's, or "" for no one
    source: str = ""            # (f478) who it came from: self (seen or lived), a person's id, "town", "guild"
    about: str = ""             # (f478) what it is about, so the same thing again counts up (times) instead of filling the rows
    minute: int = -1            # (f478) when, to the minute (-1: only the day is known)
    times: int = 1
    state: str = ""             # (f483) a knows row's: held, or told:<character ids> once they have said it
    id: int | None = None


class Regard(BaseModel):
    """(f480) What one person makes of one character: kept per character id (NPC.regard), so a second character beside the first is a
    stranger to someone the first has known for years (GOALS.md, owner's decision 2026-11-03: a townsperson's view of each character is
    kept separate). Read through engine/regard.py (of), written through it (own; trust only by step, the one writer, which keeps why it
    moved in `moves`, capped in data/rules/regard.yaml)."""
    trust: int = 50
    met: bool = False
    first_met: int = -1           # the game minute they first met (-1: before this was kept, or not yet)
    last_talk_day: int = -1       # (f362) the game day of the last conversation: the first talk of a day moves trust (engine/trust.py)
    last_talk_at: int = -1        # (f382) the game minute of the last conversation: a talk opened long after it is a return (engine/recognition.py)
    knows_as: str = ""            # the name the character gave them, when it is not their own
    knows_as_source: str = ""     # who it came from: "self" (the character said it), or a person's id (f483)
    name_known: bool = False      # the character knows this person's name
    heard_of: dict = {}           # someone named this person to the character before they met: {"by": speaker, "day": n, "line": what was said}
    journal_note: str = ""        # one sentence about them for the character's journal, written by them in a normal reply
    note_trust: int = -1          # their trust in the character when the note was written
    note_mem: int = 0             # how many memories they had then; the note is rewritten after big changes
    easy_bonus: int = 0           # Easy Company: trust gained so far
    easy_day: int = -1
    moves: list[dict] = []        # the last trust moves, each {minute, n, cause, about}: why they feel as they do


class _Unmet(Regard):
    """(f480) The view of a character this person holds no record of: read-only, so a write through engine/regard.of() (instead of own)
    fails loudly instead of being lost."""
    model_config = ConfigDict(frozen=True)


# (f480) The per-player fields an NPC record carried before v12, and their names in Regard: a record written before v12 (an old save
# read by a migration before v12's own step, or a fixture) is read as the one character there was then, "player".
LEGACY_REGARD = {"trust": "trust", "met_player": "met", "last_talk_day": "last_talk_day", "last_talk_at": "last_talk_at",
                 "knows_player_as": "knows_as", "name_known_to_player": "name_known", "heard_of": "heard_of", "journal_note": "journal_note",
                 "note_trust": "note_trust", "note_mem": "note_mem", "easy_bonus": "easy_bonus", "easy_day": "easy_day"}


def legacy_regard(data: dict) -> dict:
    """(f480) A record's pre-v12 per-player fields moved into regard["player"]: only those that differ from a new Regard's, and the entry
    made only when one does (a person nobody had met or named keeps none). Used by migration v12 and when a pre-v12 record is read."""
    if not isinstance(data, dict) or not any(k in data for k in LEGACY_REGARD):
        return data
    data = dict(data)
    blank = Regard()
    moved = {}
    for old, new in LEGACY_REGARD.items():
        if old in data:
            v = data.pop(old)
            if v != getattr(blank, new):
                moved[new] = v
    if moved:
        regard = dict(data.get("regard") or {})
        regard["player"] = {**(regard.get("player") or {}), **moved}
        data["regard"] = regard
    return data


class NPC(BaseModel):
    id: str
    name: str
    people: str
    role: str
    location: str
    gender: str = ""
    tier: Literal["background", "known", "significant"] = "background"
    rank: str = ""                # (f374) an adventurer's guild rank when the record has one (Maren: A); a guild contractor without one is drawn from their id

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

    motive: str = ""              # an active goal that moves forward off-screen; most people have none
    mood: str = ""                # how they've been lately, set by what has happened to them
    mood_source: str = ""         # (f483) what gave them the mood: a matter, a motive, a moment, a town's fall (engine/circumstance.py)
    concern_state: str = ""       # (f483) active while it is on their mind; settled or let go once its cause has ended
    first_description: str = ""   # (f483) how they first looked, kept when a revision changes them (engine/identity.py)
    mood_until: int = 0           # (f331) the game minute a mood the world gave them fades (engine/drift.py); 0 for one with no clock yet
    motive_done_at: int = -1      # (f331) the minute a motive ended (achieved or given up), -1 for never; after a while a new one may take hold
    motive_since: int = 0         # (f334) the minute the motive took hold; 0 for one from before this was kept
    motive_step: int = 0          # (f360) how many steps the engine has moved their goal (data/rules/motives.yaml)
    relations: dict[str, dict] = {}  # other NPC id -> {"score": -100..100, "feeling": "..."}
    gone: str = ""                # if they've left the story: how ("left for Riverhaven", "taken", "killed by wolves")
    protected: bool = False       # the pulse may never remove them
    away_until: int = -1
    looks_away_until: int = -1    # a bribed person sees nothing until this game minute
    hidden: list[dict] = []       # story objects the player went looking for on this person: {"name", "description", "worth", "taken"}
    stock: list = []              # gear for sale (Item data), replaced on restock
    stock_day: int = -1           # day the current stock was laid out
    # (f481) work offered and requests made are offers in the registry (engine/obligations.py), each ending for a reason          # game minute until which they've stepped away (after ending a conversation)
    speech: dict = {}             # (f347) who they are when they speak: the culture that raised them and how it shows (engine/voice_profile.py); rolled when first spoken to
    said: list[str] = []          # (f347) their last few replies to the player, so they do not say the same thing twice (llm/contracts.py NPCReply)
    heard: list[str] = []         # (f347) what the player said to draw each of those, so the same question may get much the same answer
    memories: list[Memory] = []   # the window of what they remember (see Memory); the table npc_memory holds all of it
    memory_total: int = 0         # how many they hold in all (read from the table on load; not saved in the record)
    regard: dict[str, Regard] = {}  # (f480) what they make of each character, by the character's id (engine/regard.py)

    @model_validator(mode="before")
    @classmethod
    def _before_v12(cls, data):
        return legacy_regard(data)

    def label(self, who: str) -> str:
        """(f480) How the character `who` (an id) knows them: by name once that character knows it, else by look or trade."""
        r = self.regard.get(who)
        return self.name if r is not None and r.name_known else (self.epithet or f"the {self.role.replace('_', ' ')}")
