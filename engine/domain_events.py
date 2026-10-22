"""Typed events for the things that happen to the game's state, and a small synchronous bus that carries them.

A service (services/party.py first) changes the state and publishes an event saying what it did; whoever needs to know subscribes to
the event's type and is called at once, in the same transaction, in the order of subscription. The journal is one subscriber (every
event is a row in the campaign's event log, through engine.canon.journal); the tests are another (they read RECENT). Nothing waits in
a queue and nothing runs later: a turn is one transaction, and an event is part of the turn that caused it.

Rules:
  - an event is a frozen dataclass naming what happened, with ids rather than records: it is a fact, not a handle on the state
  - publish() is called after the state has changed, never before: a subscriber may read the state and must see the new one
  - a subscriber that raises stops the turn (the turn is rolled back by scenes/world.py): a bug here is not hidden
  - subscribers do not publish from inside a handler of the same event type (no cascades on one bus pass); a service publishes, a
    subscriber reads

Adding an event: declare the dataclass here with `kind` (the journal's kind), `actor` and `target` (ids), and text(); publish it from
the service that makes the change."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, fields
from typing import Callable


@dataclass(frozen=True)
class Event:
    kind: str = field(init=False, default="event")
    minute: int = 0

    @property
    def actor(self) -> str:
        return ""

    @property
    def target(self) -> str:
        return ""

    def text(self) -> str:
        return self.kind

    def data(self) -> dict:
        """The event's own fields (not kind or minute), for the journal row."""
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in ("kind", "minute")}


# ---- the party

@dataclass(frozen=True)
class MemberJoined(Event):
    kind: str = field(init=False, default="party_joined")
    member_id: str = ""
    name: str = ""
    role: str = ""
    fee: int = 0
    how: str = "hired"            # hired | companion (an npc who joins for a thread) | story (Maren)

    @property
    def actor(self) -> str:
        return "player"

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return {"hired": f"{self.name} was hired", "story": f"{self.name} came along"}.get(self.how, f"{self.name} joined the party")


@dataclass(frozen=True)
class MemberLeft(Event):
    kind: str = field(init=False, default="party_left")
    member_id: str = ""
    name: str = ""
    how: str = "dismissed"        # dismissed | disbanded | home (a companion whose thread ended) | gone

    @property
    def actor(self) -> str:
        return "player" if self.how == "dismissed" else ""

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return f"{self.name} was {self.how}" if self.how in ("dismissed", "disbanded") else f"{self.name} left the party ({self.how})"


@dataclass(frozen=True)
class MemberDied(Event):
    kind: str = field(init=False, default="party_died")
    member_id: str = ""
    name: str = ""
    how: str = "fight"
    in_fight: bool = True         # True: it happened in front of the others, mid-fight; False: found so when the fight ended

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return f"{self.name} was killed in a fight" if self.how == "fight" else f"{self.name} died: {self.how}"


@dataclass(frozen=True)
class MemberCarried(Event):
    kind: str = field(init=False, default="party_carried")
    member_id: str = ""
    name: str = ""

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return f"{self.name} went down and was carried out alive"


@dataclass(frozen=True)
class MemberPromoted(Event):
    kind: str = field(init=False, default="party_promoted")
    member_id: str = ""
    name: str = ""
    old_rank: str = ""
    new_rank: str = ""
    fee: int = 0

    @property
    def actor(self) -> str:
        return "player"

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return f"{self.name} was raised from {self.old_rank}-rank to {self.new_rank}-rank"


@dataclass(frozen=True)
class PartyModeChanged(Event):
    kind: str = field(init=False, default="party_mode")
    mode: str = "with"            # with | hold

    @property
    def actor(self) -> str:
        return "player"

    def text(self) -> str:
        return "the party moves with the player" if self.mode == "with" else "the party holds back"


# ---- what the player did that the world could notice (f330)
#
# A Deed is published once by the scene that saw it happen; engine/reactions.py subscribes what the world does about it (who remembers,
# what it does to standing, reputation and heat, which companions have a view, whether it goes in the deeds ledger), from the entry for
# its kind in data/rules/reactions.yaml. The words people remember are written here, by the event, from its own facts: the victim's line
# and a witness's line differ, and only the event knows what it was. `witnesses` are the ids of everyone who saw it, the one it was done
# to included when they did; `target` is that one. Adding a deed: a class here, a line in reactions.yaml, one publish() where it happens.

@dataclass(frozen=True)
class Deed(Event):
    kind: str = field(init=False, default="deed")
    place: str = ""
    witnesses: tuple[str, ...] = ()
    npc: str = ""                  # the one it was done to, when there is one
    name: str = ""                 # how they are known to the player (their label), for the lines

    @property
    def actor(self) -> str:
        return "player"

    @property
    def target(self) -> str:
        return self.npc

    @property
    def seen(self) -> bool:
        return bool(self.witnesses)

    def victim_line(self) -> str:
        """What the one it was done to remembers. '' when nothing."""
        return ""

    def witness_line(self) -> str:
        """What someone else who saw it remembers."""
        return ""

    def unseen_line(self) -> str:
        """What the one it was done to remembers when nobody saw it happen (a theft noticed only later)."""
        return ""

    def item_label(self) -> str:
        """What the tale names ({item} in standing.yaml)."""
        return ""

    def ledger_row(self) -> dict | None:
        """The row for the deeds ledger (engine/deeds.py), with the exact keys events.path_met and the judge read; None for no row."""
        return None


@dataclass(frozen=True)
class CreatureKilled(Deed):
    kind: str = field(init=False, default="kill")
    creature: str = ""
    level: int = 0
    rank: str = "normal"
    spawn: str = ""

    def text(self) -> str:
        return f"killed {self.creature} (level {self.level})"

    def ledger_row(self) -> dict | None:
        return {"kind": "kill", "creature": self.creature, "level": self.level, "rank": self.rank, "spawn": self.spawn}


@dataclass(frozen=True)
class Theft(Deed):
    kind: str = field(init=False, default="theft")
    item: str = ""
    took: bool = False
    story: bool = False            # a story object (a letter, a ledger), which weighs more than a loaf
    value: int = 0

    def text(self) -> str:
        return f"{'took' if self.took else 'tried to take'} {self.item}" + (f" from {self.name}" if self.name else "")

    def victim_line(self) -> str:
        return f"Caught the stranger {'taking' if self.took else 'trying to take'} {self.item} from me."

    def witness_line(self) -> str:
        return f"Saw the stranger {'took' if self.took else 'tried to take'} {self.item}" + (f" from {self.name}." if self.npc else ".")

    def unseen_line(self) -> str:
        return f"{self.item.capitalize()} has gone missing. I have no idea who took it." if self.took and self.npc else ""

    def item_label(self) -> str:
        return self.item

    def ledger_row(self) -> dict | None:
        if not self.witnesses:
            return None                                   # an unseen theft leaves no record anyone could read
        return {"kind": "offense", "offense": "theft", "item": self.item, "took": self.took, "witnesses": list(self.witnesses), "story": self.story}


@dataclass(frozen=True)
class BreakIn(Deed):
    kind: str = field(init=False, default="break_in")
    lock: str = ""
    opened: bool = False

    def text(self) -> str:
        return f"{'broke into' if self.opened else 'tried to break into'} {self.lock}"

    def victim_line(self) -> str:
        return f"Caught the stranger {'breaking into' if self.opened else 'trying to break into'} {self.lock}."

    def witness_line(self) -> str:
        return f"Saw the stranger {'break into' if self.opened else 'try to break into'} {self.lock}."

    def item_label(self) -> str:
        return self.lock

    def ledger_row(self) -> dict | None:
        if not self.witnesses:
            return None
        return {"kind": "offense", "offense": "break_in", "item": self.lock, "took": self.opened, "witnesses": list(self.witnesses), "story": False}


@dataclass(frozen=True)
class PersonHarmed(Deed):
    kind: str = field(init=False, default="assault")

    def text(self) -> str:
        return f"laid hands on {self.name}"

    def victim_line(self) -> str:
        return "The stranger laid hands on me."

    def witness_line(self) -> str:
        return f"Saw the stranger lay hands on {self.name}."

    def item_label(self) -> str:
        return self.name

    def ledger_row(self) -> dict | None:
        return {"kind": "offense", "offense": "assault", "target": self.npc, "witnesses": list(self.witnesses)}


@dataclass(frozen=True)
class FinePaid(Deed):
    kind: str = field(init=False, default="fine_paid")
    amount: int = 0

    def text(self) -> str:
        return f"paid the watch's fine ({self.amount} copper)"

    def victim_line(self) -> str:
        from engine import money
        return f"The stranger paid {money.words(self.amount)} to settle their crimes."


@dataclass(frozen=True)
class TalkedOut(Deed):
    kind: str = field(init=False, default="talked_out")

    def text(self) -> str:
        return "talked their way out of trouble with the watch"

    def victim_line(self) -> str:
        return "The stranger talked their way out of trouble with me."


@dataclass(frozen=True)
class RanFromWatch(Deed):
    kind: str = field(init=False, default="ran_from_watch")

    def text(self) -> str:
        return "ran from the watch"

    def victim_line(self) -> str:
        return "The stranger ran from the watch."


@dataclass(frozen=True)
class Jailed(Deed):
    kind: str = field(init=False, default="jailed")
    days: int = 0
    walked: bool = False           # Above the Law: no cell; they paid what they could and walked

    def text(self) -> str:
        return "walked free of the cells, their kind being fined, not jailed" if self.walked else f"spent {self.days} days in the cells"

    def victim_line(self) -> str:
        return ("The stranger's kind do not see the inside of a cell. They paid what they could and walked." if self.walked
                else "The stranger spent time in the cells.")


@dataclass(frozen=True)
class Bribe(Deed):
    kind: str = field(init=False, default="bribe")
    amount: int = 0
    worked: bool = False
    degree: str = ""
    favor: str = ""
    confrontation: bool = False    # offered to the watch that had stopped them, not slipped to someone in talk
    guard: bool = False            # the one bribed keeps the law

    def text(self) -> str:
        return f"{'bribed' if self.worked else 'tried to bribe'} {self.name} ({self.amount} copper)"

    def victim_line(self) -> str:
        from engine import money
        sum_ = money.words(self.amount)
        if self.confrontation:
            return f"Took {sum_} from the stranger to forget what I knew." if self.worked else "The stranger tried to bribe me. I did not take it."
        if self.worked:
            return f"Took {sum_} from the stranger as a bribe ({self.favor}). I was persuaded."
        if self.degree == "partial":
            return f"The stranger offered {sum_} to {self.favor}. It was not enough; I held out for more."
        return f"The stranger tried to bribe me with {sum_} ({self.favor}). I refused, and I trust them less for it."

    @property
    def worked_on_guard(self) -> bool:
        return self.worked and self.guard


@dataclass(frozen=True)
class Tithe(Deed):
    kind: str = field(init=False, default="tithe")
    amount: int = 0
    weight: float = 0.0

    def text(self) -> str:
        return f"left a tithe of {self.amount} copper"

    def item_label(self) -> str:
        return self.name


@dataclass(frozen=True)
class Prayed(Deed):
    """(f332) A prayer or a small rite; npc is the priest who saw it, if one did."""
    kind: str = field(init=False, default="prayed")
    god: str = ""
    temple: bool = False           # at a temple: the companions see a stop at a shrine

    def text(self) -> str:
        return "prayed" + (f" to {self.god}" if self.god else "") + (" at the temple" if self.temple else "")

    def victim_line(self) -> str:
        return "The stranger stopped to pray" + (f" to {self.god}" if self.god else "") + (", here before the altar." if self.temple else ".")


@dataclass(frozen=True)
class Gambled(Deed):
    """(f332) Dice or cards with someone here: amount staked, won (+) or lost (-) in copper."""
    kind: str = field(init=False, default="gambled")
    amount: int = 0
    won: int = 0

    def text(self) -> str:
        return f"gambled {self.amount} copper and {'won' if self.won > 0 else 'lost' if self.won < 0 else 'broke even'}"

    def victim_line(self) -> str:
        from engine import money
        return (f"Played the stranger at dice for {money.words(self.amount)}; they " + ("took my coin." if self.won > 0 else "lost theirs." if self.won < 0 else "broke even."))


@dataclass(frozen=True)
class Gift(Deed):
    kind: str = field(init=False, default="gift")
    item: str = ""
    coin: int = 0

    def text(self) -> str:
        return f"gave {self.name} {self.item or str(self.coin) + ' copper'}"

    def victim_line(self) -> str:
        from engine import money
        return f"The stranger gave me {self.item or money.words(self.coin)}, asking nothing for it."


@dataclass(frozen=True)
class Delivered(Deed):
    kind: str = field(init=False, default="deliver")
    item: str = ""
    asked_by: str = ""
    meant: bool = False            # it was meant for them

    def text(self) -> str:
        return f"delivered {self.item} to {self.name}"

    def victim_line(self) -> str:
        return (f"The stranger delivered {self.item} to me, as {self.asked_by} asked." if self.meant
                else f"The stranger handed me {self.item}.")

    def ledger_row(self) -> dict | None:
        return {"kind": "deliver", "item": self.item, "npc": self.npc, "npc_name": self.name}


@dataclass(frozen=True)
class ContractTaken(Deed):
    kind: str = field(init=False, default="contract_taken")
    quest: str = ""
    title: str = ""

    def text(self) -> str:
        return f"took on {self.title}"


@dataclass(frozen=True)
class ContractDone(Deed):
    kind: str = field(init=False, default="contract_done")
    quest: str = ""
    title: str = ""
    thread: str = ""
    guild: bool = True
    coins: int = 0
    letter: str = ""

    def text(self) -> str:
        return f"finished {self.title}"

    @property
    def request(self) -> bool:
        return not self.guild

    def victim_line(self) -> str:
        from engine import money
        return f"The stranger finished {self.title.lower()}; I paid {money.words(self.coins)}."

    def item_label(self) -> str:
        return self.title

    def ledger_row(self) -> dict | None:
        return {"kind": "quest_done", "thread": self.thread, "title": self.title} if self.thread else None


@dataclass(frozen=True)
class ContractDropped(Deed):
    kind: str = field(init=False, default="contract_dropped")
    quest: str = ""
    title: str = ""
    how: str = "abandoned"         # abandoned | expired
    guild: bool = True

    def text(self) -> str:
        return f"{'walked away from' if self.how == 'abandoned' else 'let time run out on'} {self.title}"

    def victim_line(self) -> str:
        return (f"The stranger took on my job - {self.title.lower()} - and walked away from it." if self.how == "abandoned"
                else f"The stranger took on my job - {self.title.lower()} - and let the time run out.")


@dataclass(frozen=True)
class Persuaded(Deed):
    kind: str = field(init=False, default="persuade")
    how: str = "persuasion"        # persuasion | intimidation
    degree: str = ""

    def text(self) -> str:
        done = self.degree in ("strong success", "success")
        verb = ("persuaded" if done else "tried to persuade") if self.how == "persuasion" else ("intimidated" if done else "tried to intimidate")
        return f"{verb} {self.name}"

    @property
    def intimidation(self) -> bool:
        return self.how == "intimidation"

    def ledger_row(self) -> dict | None:
        if self.degree not in ("strong success", "success"):
            return None
        return {"kind": "persuade", "npc": self.npc, "npc_name": self.name, "how": self.how, "degree": self.degree}


@dataclass(frozen=True)
class LieCaught(Deed):
    kind: str = field(init=False, default="lie_caught")

    def text(self) -> str:
        return f"was caught lying to {self.name}"

    def victim_line(self) -> str:
        return "Caught the stranger in a lie."


@dataclass(frozen=True)
class CaughtSpying(Deed):
    kind: str = field(init=False, default="caught_spying")

    def text(self) -> str:
        return f"was caught watching {self.name}"

    def victim_line(self) -> str:
        return "Caught the stranger watching me from hiding."


@dataclass(frozen=True)
class Pickpocketed(Deed):
    kind: str = field(init=False, default="pickpocket")
    coins: int = 0
    caught: bool = False

    def text(self) -> str:
        return f"{'was caught picking' if self.caught else 'picked'} {self.name}'s pocket"

    def victim_line(self) -> str:
        return "The stranger tried to pick my pocket, and I caught them at it." if self.caught else ""


@dataclass(frozen=True)
class Improvised(Deed):
    kind: str = field(init=False, default="improvised")
    effect: str = ""
    degree: str = ""
    what: str = ""
    mark: str = ""
    heat: float = 0.0              # the noise it made, as heat (engine/world_improv.py fails)

    def text(self) -> str:
        return f"improvised ({self.effect}: {self.what}) - {self.degree}"


@dataclass(frozen=True)
class Traded(Deed):
    kind: str = field(init=False, default="trade")
    item: str = ""
    coins: int = 0
    bought: bool = True            # the player bought (else sold)

    def text(self) -> str:
        return f"{'bought' if self.bought else 'sold'} {self.item} ({self.coins} copper)"

    def victim_line(self) -> str:
        from engine import money
        return (f"Sold the stranger {self.item} for {money.words(self.coins)}." if self.bought
                else f"Bought {self.item} from the stranger for {money.words(self.coins)}.")


@dataclass(frozen=True)
class Worked(Deed):
    kind: str = field(init=False, default="worked")
    task: str = ""
    paid: int = 0
    unasked: bool = False

    def text(self) -> str:
        return f"worked for {self.name}: {self.task}" if not self.unasked else f"pitched in with {self.name}'s work, unasked"

    def victim_line(self) -> str:
        from engine import money
        if self.unasked:
            return "The stranger pitched in and helped me with my work, unasked and unpaid."
        return f"The stranger did the work I asked - {self.task} - and I paid {money.words(self.paid)}."


@dataclass(frozen=True)
class Trained(Deed):
    kind: str = field(init=False, default="trained")
    ability: str = ""

    def text(self) -> str:
        return f"was taught {self.ability} by {self.name}"

    def victim_line(self) -> str:
        return f"Taught the stranger {self.ability}."


@dataclass(frozen=True)
class JoinedGuild(Deed):
    kind: str = field(init=False, default="joined_guild")

    def text(self) -> str:
        return "joined the adventurers' guild at rank F"

    def victim_line(self) -> str:
        return "Signed the stranger into the guild register at rank F."


@dataclass(frozen=True)
class Rested(Deed):
    kind: str = field(init=False, default="rest")
    inn: bool = False
    late: bool = False
    slept: bool = False

    def text(self) -> str:
        return ("slept" if self.slept else "rested") + (" at an inn" if self.inn else "") + (", past midday" if self.late else "")


@dataclass(frozen=True)
class Visited(Deed):
    kind: str = field(init=False, default="visited")
    place_type: str = ""

    def text(self) -> str:
        return f"came to a {self.place_type}"

    @property
    def shrine(self) -> bool:
        return self.place_type in ("shrine", "temple")


@dataclass(frozen=True)
class Harvested(Deed):
    kind: str = field(init=False, default="harvested")
    creature: str = ""

    def text(self) -> str:
        return f"skinned and butchered {self.creature}"


@dataclass(frozen=True)
class Spared(Deed):
    kind: str = field(init=False, default="spared")

    def text(self) -> str:
        return "spared a foe who yielded"


@dataclass(frozen=True)
class LootedDead(Deed):
    kind: str = field(init=False, default="looted_dead")

    def text(self) -> str:
        return "picked over the dead for coin"


@dataclass(frozen=True)
class Fled(Deed):
    kind: str = field(init=False, default="fled")

    def text(self) -> str:
        return "ran from a fight"


@dataclass(frozen=True)
class DungeonCleared(Deed):
    kind: str = field(init=False, default="dungeon_cleared")
    dungeon: str = ""
    boss: str = ""

    def text(self) -> str:
        return f"cleared {self.dungeon} and killed {self.boss}" if self.boss else f"cleared {self.dungeon}"

    def ledger_row(self) -> dict | None:
        return {"kind": "dungeon_cleared", "dungeon": self.dungeon}


@dataclass(frozen=True)
class ClueFound(Deed):
    kind: str = field(init=False, default="found")
    thread: str = ""
    what: str = ""

    def text(self) -> str:
        return f"found {self.what}"

    def ledger_row(self) -> dict | None:
        return {"kind": "found", "thread": self.thread, "what": self.what}


@dataclass(frozen=True)
class GateHeld(Deed):
    kind: str = field(init=False, default="defend")
    thread: str = ""
    town: str = ""

    def text(self) -> str:
        return f"held the gate of {self.town}"

    def ledger_row(self) -> dict | None:
        return {"kind": "defend", "thread": self.thread, "town": self.town}


@dataclass(frozen=True)
class PlaceDiscovered(Deed):
    kind: str = field(init=False, default="discovered")
    found: str = ""                # the new place's id
    what: str = "place"            # place | track

    def text(self) -> str:
        return f"found {self.name or self.found}" + (" (a way through)" if self.what == "track" else "")


# ---- the bus

_SUBSCRIBERS: dict[type, list[Callable[[Event], None]]] = {}
RECENT: deque = deque(maxlen=64)       # the last events published, newest last (tests and the live check read these)


def subscribe(event_type: type, fn: Callable[[Event], None]) -> Callable[[], None]:
    """Call fn for every event of this type (or a subclass of it; Event itself for everything). Returns a function that unsubscribes."""
    lst = _SUBSCRIBERS.setdefault(event_type, [])
    if fn not in lst:
        lst.append(fn)

    def off() -> None:
        if fn in lst:
            lst.remove(fn)
    return off


def publish(event: Event) -> Event:
    """Deliver the event to every subscriber of its type and its bases, in subscription order, now. Returns the event."""
    RECENT.append(event)
    for cls in type(event).__mro__:
        for fn in list(_SUBSCRIBERS.get(cls, ())):
            fn(event)
    return event


def clear() -> None:
    """Forget every subscriber and the recent events (tests)."""
    _SUBSCRIBERS.clear()
    RECENT.clear()


_JOURNAL_ON = False


def journal_everything() -> None:
    """Every event becomes a row in the campaign's event log (engine.canon.journal, bound by the scene). Idempotent."""
    global _JOURNAL_ON
    if _JOURNAL_ON:
        return
    from engine import canon

    def to_journal(e: Event) -> None:
        canon.journal(e.kind, e.actor, e.target, e.text(), **e.data())
    subscribe(Event, to_journal)
    _JOURNAL_ON = True
