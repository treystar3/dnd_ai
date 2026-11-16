"""(f633) Whose every piece of state outside a save is, and what puts it back (docs/design/20_phase3_plan.md).

STATE declares every module-level name in the game's code that is written after import, and each of the turn's registers and
of the actor's caches and preferences (engine/actor.py Registers, Caches, Prefs): whose it is (`scope`) and what puts it back (`resets`, in words). A
row the session puts back when a campaign opens or closes also says how (`put_back`), when it is clean and what it holds:
engine/session.py reset() and residue() are those rows and nothing else. tools/sim/owned_state_633_test.py reads the syntax tree of the game's code and fails
on a written name that is not a row here, so the next one cannot arrive unnoticed.

The scopes:
- TURN: one line's, or one input's. The registers are where it belongs; a row of this scope on a module name is one still to
  move there.
- ACTOR: one character's. The caches are where it belongs, the process's one set while a scene has one character; so are a
  player's preferences, which only the player puts back.
- CAMPAIGN: the save's that is open, put back when it closes.
- PROCESS: this run of the program's: a data file read once, a tally written out at the end, a switch the start-up set, a seam
  something installed and takes out itself.
- CALL: one call's own on its thread, put back as the call returns.

A scope says whose a name is, not where it lives: the turn's registers and the actor's caches have moved, and this is the list
the rest start from."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable

TURN, ACTOR, CAMPAIGN, PROCESS, CALL = "turn", "actor", "campaign", "process", "call"
SCOPES = (TURN, ACTOR, CAMPAIGN, PROCESS, CALL)
SESSION = "the session, when a campaign opens or closes"
READ_ONCE = "nothing: a data file read once, the same for every campaign"
TALLY = "nothing: this run's tally, capped or written out at its end"


@dataclass(frozen=True)
class Row:
    scope: str
    resets: str                                        # what puts it back, in words
    put_back: Callable[[], None] | None = None         # ...and how, where the session does (engine/session.py reset)
    clean: Callable[[], bool] | None = None            # whether it is as a new process holds it
    what: Callable[[], str] | None = None              # what it holds, for the residue


def _at(key: str):
    mod, _, name = key.rpartition(".")
    return getattr(importlib.import_module(mod), name)


def _call(key: str, *args, **kwargs):
    return _at(key)(*args, **kwargs)


def emptied(key: str, scope: str, count: str = "") -> Row:
    """A container the session empties in place; `count` names what it counts in the residue, where its whole text is too long."""
    return Row(scope, SESSION, lambda: _at(key).clear(), lambda: not _at(key),
               (lambda: f"{len(_at(key))} {count}") if count else (lambda: repr(dict(_at(key)) if hasattr(_at(key), "keys") else _at(key))))


def rebound(key: str, scope: str, value) -> Row:
    """A name the session sets back to the value a new process has."""
    mod, _, name = key.rpartition(".")
    return Row(scope, SESSION, lambda: setattr(importlib.import_module(mod), name, value), lambda: _at(key) == value, lambda: repr(_at(key)))


def field(held, scope: str, name: str) -> Row:
    """One field of the process's registers or caches: put back as a new set holds it."""
    fresh = held.FRESH[name]
    return Row(scope, SESSION, lambda: setattr(held, name, fresh()), lambda: getattr(held, name) == fresh(), lambda: repr(getattr(held, name))[:80])


HELD = "engine.actor."                                 # a row for a field of the registers, the caches or the preferences: engine.actor.<Class>.<field>


def _fields() -> dict[str, Row]:
    from engine import actor
    return {f"{HELD}{type(held).__name__}.{name}": field(held, scope, name)
            for held, scope in ((actor.SHARED, TURN), (actor.SHARED_CACHES, ACTOR)) for name in held.FRESH}


def _prefs() -> dict[str, Row]:
    """(f636) A player's preferences: the actor's, and nothing but the player puts one back."""
    from engine import actor
    by = {"debug": "#debug, or --debug at the start", "numbers": "#numbers", "dialogue": "#dialogue"}
    return {f"{HELD}Prefs.{name}": Row(ACTOR, f"the player ({by[name]})") for name in actor.SHARED_PREFS.FRESH}


STATE: dict[str, Row] = {
    # ---- the turn's registers (the operation, the ledger, the budget, the turn log's open turn, the serving, the owner) and the
    # actor's caches (the journal, the ids, the claims' events and sink, the cast, the lines said last, the discount)
    **_fields(),
    **_prefs(),

    # ---- the open campaign's
    "engine.pulse.LAST": Row(CAMPAIGN, SESSION, lambda: _at("engine.pulse.LAST").update(made_by="", attempted=""),
                             lambda: not (_at("engine.pulse.LAST").get("made_by") or _at("engine.pulse.LAST").get("attempted")),
                             lambda: repr(dict(_at("engine.pulse.LAST")))),
    "engine.severity.REACTIONS": emptied("engine.severity.REACTIONS", CAMPAIGN, "reactions"),
    "engine.streams.DEFAULT": Row(CAMPAIGN, SESSION, lambda: _call("engine.streams.reset"), lambda: _call("engine.streams.key") == "unseeded",
                                  lambda: _call("engine.streams.key")),            # the process's dice: keyed by the campaign's seed and its input
    "npc.life._ANCHOR_SLOTS": emptied("npc.life._ANCHOR_SLOTS", CAMPAIGN),
    # (f476) a warm one changes what the budget charges and which embed calls a replay expects
    "llm.embed._cache": emptied("llm.embed._cache", CAMPAIGN, "vectors"),
    "engine.domain_events._current": Row(CAMPAIGN, "the session: its own bus while it plays, an idle one once it has closed (domain_events.use)"),
    "engine.domain_events.RECENT": Row(CAMPAIGN, "the session, with the bus it is the recent events of (domain_events.use)"),
    "npc.backfill._jobs": Row(CAMPAIGN, "the session's close, which forgets the save's jobs (backfill.drop); keyed by save, so one save never reads another's"),
    "engine.streams.STRICT": Row(CAMPAIGN, "the recorder: set as it is installed and cleared as it closes, which the session does first"),

    # ---- one line's or one input's, still module names
    "llm.gateway._SEEN": Row(TURN, "the next input begun (gateway._place, by the count of inputs begun): this input's calls so far, by task"),
    "llm.audit._turn": Row(TURN, "the next line (audit.note_turn): the line the audited calls are headed by"),
    "engine.pulselog._tick": Row(TURN, "the next tick of the pulse (pulselog.begin)"),

    # ---- one call's own
    "engine.martial.MANEUVERS": Row(CALL, "the same call: a move's own form put over the table's while it is resolved, and the table's put back"),
    "llm.backend._lane": Row(CALL, "the block that set it (backend.lane), per thread: the lane and the session of the call being made"),
    "llm.backend._task": Row(CALL, "the block that set it (backend.task), per thread: the task of the call being made"),
    "llm.gateway._TASK": Row(CALL, "the next call on the same thread: the task, the shape and the seed of the call being made"),
    "llm.gateway._tag": Row(CALL, "the block that set it (gateway.tagged), per thread: fields added to the call log's rows"),

    # ---- this run's: tallies and logs kept in memory
    "engine.turnlog.COUNTS": Row(PROCESS, TALLY + " (logs/sessions.jsonl): lines by who handled them"),
    "engine.turnlog._writes": Row(PROCESS, "nothing: rows written to the turn log, to trim it every so often"),
    "llm.gateway.TALLY": Row(PROCESS, TALLY + " (logs/sessions.jsonl): each task's calls, failures and attempts"),
    "llm.gateway.OUTCOMES": Row(PROCESS, TALLY + ": the last few hundred calls and how each ended"),
    "llm.gateway.FALLBACKS": Row(PROCESS, TALLY + ": the tasks that gave up, for the live check"),
    "llm.gateway._writes": Row(PROCESS, "nothing: rows written to the call log, to trim it every so often"),
    "engine.names.REPAIRS": Row(PROCESS, TALLY + ": names and pronouns mended, for a night's summary"),
    "engine.names.BY_TASK": Row(PROCESS, TALLY + ": names mended by task"),
    "engine.hygiene.REPAIRS": Row(PROCESS, TALLY + ": what was mended on the way to the screen"),
    "engine.crashlog.SESSION": Row(PROCESS, TALLY + ": this run's faults, for the tests and the night tools"),
    "engine.refusals.SESSION": Row(PROCESS, "nothing, and it has no cap: this run's refusals, one for each filed; an operation that runs again takes "
                                            "back the ones its first attempt filed"),
    "engine.pulselog.LOG": Row(PROCESS, "its own cap (pulselog.clear is a harness's): the pulse's last few hundred rows; an operation that runs again takes back its own"),
    "engine.streams.BEGUN": Row(PROCESS, "nothing: how many inputs this run has begun; only whether it moved is read"),
    "engine.recording.ORPHANS": Row(PROCESS, "each thread's own end: the threads closed sessions left running, so their calls are never the next save's"),
    "llm.audit._path": Row(PROCESS, "nothing: this run's audit file, named when the first call is audited"),
    "engine.phantoms._names": Row(PROCESS, "nothing: the bestiary's names, read once (f701)"),
    "engine.phantoms._source": rebound("engine.phantoms._source", CAMPAIGN, None),     # (f701) the scene's place's creatures
    "llm.audit._count": Row(PROCESS, "nothing: the audit file's entry numbers"),
    "llm.audit._turn_written": Row(PROCESS, "nothing: the last heading the audit file was given"),
    "llm.audit._system_seen": Row(PROCESS, "nothing: where the audit file last wrote each task's system prompt in full"),
    "llm.audit._first_attempt": Row(PROCESS, "nothing: the audit entry of each task's latest first attempt"),
    "llm.audit._full": Row(PROCESS, "nothing: the audit file reached its size, said once"),

    # ---- this run's: switches and seams
    "engine.budget.PROFILE": Row(PROCESS, "budget.priced puts back what it changed: the card's speeds every estimate is made at"),
    "engine.budget.SLOW": Row(PROCESS, "the model server: set as it starts below the minimum card, cleared as it stops (llm/launch.py, llm/runtime.py)"),
    "llm.backend._sources": Row(PROCESS, "each handle takes out its own (backend.use): where a model call is answered from"),
    "llm.backend._layers": Row(PROCESS, "each handle takes out its own (backend.wrap): what wraps every model call"),
    "llm.backend._added": Row(PROCESS, "nothing: the order sources and layers were added in"),
    "llm.backend._switched": Row(PROCESS, "backend.forget_switch: the llama-server source the environment names, built on first use"),
    "llm.embed._state": Row(PROCESS, "nothing in play (embed.reset is a harness's): whether the embedder failed, and whose vectors the cache holds"),
    "llm.launch.SCREEN": Row(PROCESS, "the start-up itself: the loading screen handed from main.py to the launch, taken once"),
    "llm.runtime._GAME": Row(PROCESS, "runtime's own stop: the game's model server, its lock and its place among the sources"),
    "llm.runtime._SPAWNER": Row(PROCESS, "nothing: the one spawner of server processes, made on first use"),
    "ui.console._process": Row(PROCESS, "the window's bridge, which installs its page and puts back the channel it found (ui/gui/bridge.py). What stands in for an output is set on a channel, never on the module, and put back by what set it: an operation's hold as it ends, the question fence at the turn's end, the recorder at its close"),
    "ui.console._PLAIN": Row(PROCESS, "nothing: the outputs as the module writes them, filled as it loads"),

    # ---- this run's: read once, or worked out once and kept
    "engine.asked._TASKS": Row(PROCESS, READ_ONCE),
    "engine.asked._MOST": Row(PROCESS, READ_ONCE),
    "engine.asked._SEEN": Row(PROCESS, "nothing: the requests lately hashed, only for a drift's debug note, capped at twice asked_max (f675)"),
    "engine.brief._B": Row(PROCESS, READ_ONCE),
    "engine.clock._TW": Row(PROCESS, READ_ONCE),
    "engine.memory._CAPS": Row(PROCESS, READ_ONCE),
    "engine.obligations._F": Row(PROCESS, READ_ONCE),
    "engine.presence._V": Row(PROCESS, READ_ONCE),
    "engine.regard._RULES": Row(PROCESS, READ_ONCE),
    "engine.town_memory._K": Row(PROCESS, READ_ONCE),
    "engine.mapview._MAP": Row(PROCESS, READ_ONCE),
    "engine.names._VOCAB": Row(PROCESS, READ_ONCE + " (the words of the data files, for telling a name from a word)"),
    "engine.truth.FACETS": Row(PROCESS, "nothing: the facets a scene can be asked for, filled as the modules that define them are imported"),
    "engine.combat._LIFT_CACHE": Row(PROCESS, "nothing: worked out from the rules alone, the same for every campaign"),
    "engine.data_check._SCAN": Row(PROCESS, "nothing: the start-up check's reading of the source, kept for its own run"),
    "engine.mapview._LAYOUT_MEMO": Row(PROCESS, "its own cap: keyed by what a layout reads and never by a world, so two saves on one map share it"),
    "engine.weather._CHAIN": Row(PROCESS, "nothing, and it has no cap: a seed's weather, one entry for each block of days asked for, so it grows with "
                                          "the campaign's age; keyed by seed, so one campaign never reads another's"),
    "llm.llama._GRAMMARS": Row(PROCESS, "its own cap: a schema's grammar, the same whoever asks"),
}


def label(key: str) -> str:
    """A row's name in the session's residue: the module and the name, or `registers.<name>`, `caches.<name>`, `prefs.<name>`."""
    if key.startswith(HELD) and key.count(".") == 3:
        cls, name = key[len(HELD):].split(".")
        return f"{cls.lower()}.{name}"
    return key.split(".", 1)[1]
