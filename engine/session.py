"""(f453) One campaign's session: born when the save opens, closing everything it owns.

The rebuild's Stage 2 as the owner decided it for Bundle B: the session is born when the save opens (CampaignStore.open_or_create runs
inside it, the migrations and the save's creation included), and nothing of one campaign reaches the next in the same process. Before
this, main.py opened the store, made the world, built the scene and installed the recorder one by one and closed two of them; a dozen
module bindings the scene had set (the journal, the stable ids, the companions' pronouns, the ledger's rows and totals, the dice's key,
the open turn, the casting cache, the planned anchors, the world's reactions) stayed as the last save left them for the next to find;
and a creation call or a backfill still running when the save closed ran on, so that had the next session's recorder been installed,
its answer would have been written down as that session's.

- CampaignSession.open(name) resets OWNED, opens the store (SaveTooNew propagates to the caller, who tells the player, as before) and
  presents the map: a CampaignWorld over the one authored World (world/campaign.py). OWNED is the list, declared once below, of the
  module bindings a campaign writes while it plays, each with how it is put back and how it is known to be clean. They are reset at
  open (a session never closed, after a crash, leaves nothing behind) and at close, never at adopt.
- adopt(store, world) wraps a store and a world a scene was built on the old way (a test's fixture, a harness, the hundred and twenty
  constructor sites the ratchet of f450 counts down): every scene has a session either way, and nothing is reset under the test's feet.
- scene(catalog, player) builds the WorldScene on the session's store and world; record() installs the recorder, which close() closes
  first, so the last input's state is written before the store goes.
- (f454) The session owns the event bus (engine/domain_events.py Bus) and makes it current while it plays: the scene's reactions and the
  journal subscribe on it, the scene's deeds and the party's changes are published on it, and close() clears it and leaves an IdleBus
  behind, which delivers to nobody and counts. A closed campaign's listeners never hear the next campaign's events.
- own(thread) hands the session a thread to wait for at close: the creation's background call (scenes/goddess.py), beside the save's own
  backfill jobs (npc/backfill.py threads). close() joins them all within config.CLOSE_WAIT_SECONDS and leaves the survivors in
  recording.ORPHANS: their answers go nowhere (backfill.drop forgot their jobs) and the recorder passes their calls through unrecorded,
  so a thread of save A is never written down as save B's. Then the store closes and OWNED is reset.

- (f455) begin_turn(scene) at the start of every turn and pane command, inside the transaction, keeps what a rollback cannot get from the
  database: the campaign's additions to the map (world.snapshot()) and the scene's private caches (its `_` attributes, deep-copied; the
  truth scene is rebuilt instead). rollback(scene) puts them back, takes the ledger's rows back with their totals, and clears the casting
  cache, before the scene reloads the rest from the rolled-back store. The owner's decision: a rolled-back turn takes back the world's
  additions, the ledger rows and every cache written mid-turn.

residue() names every owned binding not at its initial value: {} after a clean close, which the tests assert (simlib.residue). A new
module binding a campaign writes is added to OWNED, or the next test that opens two campaigns finds it there."""
from __future__ import annotations

import copy
import threading
import time
from typing import Callable

import config

UNSEEDED = "unseeded"


def _owned() -> list[tuple[str, Callable[[], None], Callable[[], bool], Callable[[], str]]]:
    """The module bindings a campaign writes while it plays: (name, put back, clean?, what it holds). Read at call time, since two of them
    (canon.IDS, ledger.LAST) are rebound rather than changed in place."""
    from engine import canon, enchanting, failures, ledger, names, operation, pulse, questions, spellcraft, streams, turnlog
    from npc import life
    return [
        ("canon.JOURNAL", lambda: setattr(canon, "JOURNAL", None), lambda: canon.JOURNAL is None, lambda: repr(canon.JOURNAL)),
        ("canon.IDS", lambda: canon.IDS.clear(), lambda: not canon.IDS, lambda: repr(dict(canon.IDS))),
        ("names.CAST", lambda: names.set_cast({}), lambda: not names.CAST, lambda: repr(dict(names.CAST))),
        ("enchanting.DISCOUNT", lambda: enchanting.DISCOUNT.update(percent=0), lambda: not enchanting.DISCOUNT.get("percent"),
         lambda: repr(dict(enchanting.DISCOUNT))),
        ("pulse.LAST", lambda: pulse.LAST.update(made_by=""), lambda: not pulse.LAST.get("made_by"), lambda: repr(dict(pulse.LAST))),
        ("failures._last", lambda: failures._last.clear(), lambda: not failures._last, lambda: repr(dict(failures._last))),
        ("questions._last", lambda: setattr(questions, "_last", ""), lambda: not questions._last, lambda: repr(questions._last)),   # (f460)
        ("operation.CURRENT", operation.reset, lambda: operation.CURRENT is None, lambda: repr(operation.CURRENT)),              # (f462)
        ("ledger", ledger.reset, lambda: not (ledger.ROWS or ledger.LAST or ledger.TOTALS),
         lambda: f"{len(ledger.ROWS)} rows, {len(ledger.LAST)} last, {sum(ledger.TOTALS.values())} counted"),
        ("streams", streams.reset, lambda: streams.key() == UNSEEDED, streams.key),
        ("turnlog._open", lambda: setattr(turnlog, "_open", None), lambda: turnlog._open is None, lambda: repr(turnlog._open)[:80]),
        ("spellcraft._CAST", lambda: spellcraft._CAST.clear(), lambda: not spellcraft._CAST, lambda: f"{len(spellcraft._CAST)} casting"),
        ("life._ANCHOR_SLOTS", lambda: life._ANCHOR_SLOTS.clear(), lambda: not life._ANCHOR_SLOTS, lambda: repr(dict(life._ANCHOR_SLOTS))),
    ]                                                      # (f454) the world's reactions live on the session's bus, cleared with it


def reset() -> None:
    """Every owned binding put back to its initial value: a campaign is opening or has closed."""
    for _, put_back, _, _ in _owned():
        put_back()


def residue() -> dict[str, str]:
    """Every owned binding not at its initial value, by name, with what it holds: {} after a clean close."""
    return {name: what() for name, _, clean, what in _owned() if not clean()}


class CampaignSession:
    def __init__(self, store, world, adopted: bool = False):
        from engine.domain_events import Bus, use
        from world.campaign import CampaignWorld
        self.store = store
        self.world = world if isinstance(world, CampaignWorld) else CampaignWorld(world)   # (f451) a bare World is wrapped: one writer
        self.adopted = adopted
        self.bus = Bus()                                   # (f454) this campaign's events, and who listens: current while it plays
        use(self.bus)
        self.recorder = None
        self.closed = False
        self._threads: list[threading.Thread] = []
        self._turn = None                                  # (f455) what the turn being played may have to give back

    @classmethod
    def open(cls, name: str, saves_dir=None) -> "CampaignSession":
        """The session of the save of this name, made if there is none: the one way the game opens a campaign (main.py, tools/rerun.py,
        simlib.campaign). Nothing of a session before this one in the process, closed or not, reaches it."""
        from storage.campaign import SAVES_DIR, CampaignStore
        from world.campaign import CampaignWorld
        from world.loader import authored
        reset()
        store = CampaignStore.open_or_create(name, saves_dir or SAVES_DIR)     # SaveTooNew propagates: the caller tells the player
        return cls(store, CampaignWorld(authored()))

    @classmethod
    def adopt(cls, store, world) -> "CampaignSession":
        """A session over a store and a world a scene was handed the old way (WorldScene(store, world, catalog, player)): the scene has
        a session, and what the test or the harness set up around it stands."""
        return cls(store, world, adopted=True)

    def scene(self, catalog, player):
        from scenes.world import WorldScene
        return WorldScene(self.store, self.world, catalog, player, session=self)

    def record(self, apart: bool = False, folder=None):
        """(f440) Record this session, so the real turn can replay it (tools/rerun.py); closed first when the session closes."""
        from engine import recording
        if self.recorder is None:
            self.recorder = recording.Recorder(self.store, folder=folder).install(apart=apart)
        return self.recorder

    def own(self, thread: threading.Thread | None) -> threading.Thread | None:
        """A background thread of this campaign's (the creation's call for the passives), waited for at close."""
        if thread is not None:
            self._threads.append(thread)
        return thread

    def threads(self) -> list[threading.Thread]:
        """This campaign's background threads still running: the ones handed over, and the save's backfill jobs."""
        from npc import backfill
        return [t for t in self._threads + backfill.threads(self.store) if t.is_alive()]

    def close(self) -> None:
        """The campaign ends in this process: the recorder is closed, the background work is waited for (config.CLOSE_WAIT_SECONDS in all)
        and what is still running is orphaned, the save's jobs are forgotten, the store is closed and every owned binding is put back.
        Closing twice does nothing the second time."""
        if self.closed:
            return
        self.closed = True
        from engine import recording
        from npc import backfill
        if self.recorder is not None:
            self.recorder.close()
            self.recorder = None
        deadline = time.monotonic() + float(getattr(config, "CLOSE_WAIT_SECONDS", 2))
        for t in self.threads():
            t.join(max(0.0, deadline - time.monotonic()))
        recording.orphan(self.threads())                  # the survivors: their answers go nowhere, their calls are never the next save's
        self._threads.clear()
        backfill.drop(self.store)
        self.store.close()
        from engine.domain_events import IdleBus, use
        self.bus.clear()                                   # (f454) its listeners hear nothing more; between campaigns, nobody listens
        use(IdleBus())
        reset()

    # ---- (f455) a rolled-back turn takes back everything

    def begin_turn(self, scene) -> None:
        """The turn (or the pane command) begins, inside its transaction: the map's additions and the scene's private caches as they
        stand, so a rollback can put back what the database's rollback cannot. The truth scene (`_truth`) is left out: the next read
        builds it again from the restored state."""
        held = {}
        for k, v in scene.__dict__.items():
            if not k.startswith("_") or k == "_truth":
                continue
            try:
                held[k] = copy.deepcopy(v)
            except Exception:                          # a cache that cannot be copied is kept by reference: the turn may change it in place
                held[k] = v
        self._turn = (self.world.snapshot(), held)

    def rollback(self, scene) -> None:
        """The turn rolled back (scenes/world.py reload_after_rollback, first thing): the map's additions, the scene's private caches,
        the ledger's rows and totals and the casting cache go back to the turn's start. The store's reload follows."""
        from engine import ledger, spellcraft
        ledger.rollback()
        spellcraft._CAST.clear()
        if self._turn is None:
            return
        snap, held = self._turn
        self._turn = None
        self.world.restore(snap)
        for k in [k for k in scene.__dict__ if k.startswith("_")]:
            del scene.__dict__[k]
        scene.__dict__.update(held)

    def __repr__(self) -> str:
        return f"CampaignSession({self.store.meta.name!r}{', adopted' if self.adopted else ''}{', closed' if self.closed else ''})"
