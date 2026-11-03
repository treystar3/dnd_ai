"""(f454) The event bus belongs to the session. One bus served every campaign opened in a process: its subscribers (the world's reactions
bound to the last scene, the journal bound to the last store) and its recent events stayed from one save to the next, and the journal's
switch was the process's, never reset. Now engine/domain_events.py has a Bus; the session owns one (engine/session.py) and makes it
current while it plays; the scene's reactions, its journal, its deeds (WorldScene.notice) and the party's changes (services/party.py)
are on it; close() clears it and leaves an IdleBus, which delivers to nobody, raises nothing and counts. Two campaigns in one process:
nothing A's listeners heard reaches them from B, and nothing between the two is lost silently."""
import pathlib, re, shutil, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 54)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import domain_events as de, entities, party as rules
from services.party import PartyService

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

for n in ("bus_454_a", "bus_454_b"):
    shutil.rmtree(f"saves/{n}", ignore_errors=True)
check("between campaigns the current bus is idle: nothing published so far was dropped", isinstance(de.current(), de.IdleBus) and de.current().dropped == 0)

# ---- A: its bus, its listeners, its events
a = simlib.campaign("bus_454_a", cls="warrior", seed=54)
ws = a.scene
bus_a = a.session.bus
check("the session owns a bus, current while it plays, with the journal and the scene's eight reactions on it", isinstance(bus_a, de.Bus)
      and de.current() is bus_a and de.RECENT is bus_a.recent and bus_a.journal_on and bus_a.subscribers() == 9, bus_a.subscribers())
heard_a = []
de.subscribe(de.Event, lambda e: heard_a.append(e.kind))
ws.name_ids()
ws.player.party = []
c = ws.player.character
c.coins = 50000
svc = ws.party_service
offers = rules.roster(ws.store.meta.seed, "guild_house", 30, c.level, 50000, [])
m1 = svc.hire(offers[0], c.level)
check("hiring through the scene's service publishes on the session's bus", [e.kind for e in bus_a.recent] == ["party_joined"] and heard_a == ["party_joined"]
      and svc._bus is bus_a, ([e.kind for e in bus_a.recent], heard_a))
rows = ws.store.journal_tail(5, kind="party_joined")
check("...and the journal on that bus wrote the row into A's event log", bool(rows) and rows[-1]["target"] == m1["id"], rows[-1:] if rows else rows)
svc.dismiss([m1])
check("...as does dismissing", heard_a == ["party_joined", "party_left"] and ws.store.journal_tail(5, kind="party_left"), heard_a)
n_a = len(heard_a)
rows_a = len(ws.store.journal_tail(50))

a.close()
idle = de.current()
check("A closed: its bus is cleared and the current bus is idle", bus_a.subscribers() == 0 and not bus_a.journal_on and len(bus_a.recent) == 0
      and isinstance(idle, de.IdleBus) and de.RECENT is idle.recent)
de.publish(de.MemberLeft(minute=1, member_id="x", name="Nobody", how="dismissed"))
check("...an event published between campaigns is dropped and counted, never raised, never heard by A's listeners", idle.dropped == 1 and len(heard_a) == n_a
      and not de.RECENT)

# ---- B: its own bus; A hears nothing of it
b = simlib.campaign("bus_454_b", cls="warrior", seed=55)
wb = b.scene
bus_b = b.session.bus
check("B's bus is its own, empty, current, with only its journal and its reactions", bus_b is not bus_a and de.current() is bus_b and len(bus_b.recent) == 0
      and bus_b.journal_on and bus_b.subscribers() == 9, bus_b.subscribers())
wb.name_ids()
wb.player.party = []
cb = wb.player.character
cb.coins = 50000
svcb = wb.party_service
offers_b = rules.roster(wb.store.meta.seed, "guild_house", 30, cb.level, 50000, [])
mb = svcb.hire(offers_b[0], cb.level)
svcb.dismiss([mb])
check("B's hiring and dismissing reach B's journal and B's reactions, and never A's listeners", len(heard_a) == n_a
      and [e.kind for e in bus_b.recent] == ["party_joined", "party_left"] and wb.store.journal_tail(5, kind="party_left"), heard_a[n_a:])
check("...and A's event log gained nothing", (lambda: __import__("sqlite3").connect("saves/bus_454_a/campaign.db").execute("SELECT count(*) FROM event_log").fetchone()[0])() == rows_a)
e = entities.begin(wb.store, "captive", "captive:b1", "Skarn", wb.minutes, pronoun="he", people="orc", owner="player", links={"npc": "b1"})
check("the registry, which has a store and no scene, publishes on the current bus: B's", any(ev.kind == "state_changed" and ev.ref == "captive:b1" for ev in bus_b.recent)
      and not any(getattr(ev, "ref", "") == "captive:b1" for ev in bus_a.recent))

# ---- the bus's own contracts, per bus
de.clear()
check("clear() empties the current bus and turns its journal off", bus_b.subscribers() == 0 and not bus_b.journal_on and len(bus_b.recent) == 0)
de.journal_everything(); de.journal_everything()
check("journal_everything() subscribes again, once", bus_b.subscribers() == 1 and bus_b.journal_on)
before = len(wb.store.journal_tail(50, kind="party_joined"))
svcb.hire(offers_b[1], cb.level)
check("...and the next event is a row again", len(wb.store.journal_tail(50, kind="party_joined")) == before + 1)
def boom(e):
    raise RuntimeError("bug in a subscriber")
off = de.subscribe(de.MemberJoined, boom)
try:
    svcb.hire(offers_b[2], cb.level); check("a raising subscriber is not hidden", False)
except RuntimeError:
    check("a raising subscriber is not hidden", True)
off()
loose = PartyService(wb.player, lambda: wb.minutes, wb.store.meta.seed)
check("a service given no bus publishes on the current one", loose._bus is None and loose._publish(de.PartyModeChanged(minute=1, mode="follow")) is bus_b.recent[-1])
check("nothing was dropped while a campaign was open", idle.dropped == 1)
b.close()
check("B closed: idle again, A's and B's buses both empty", isinstance(de.current(), de.IdleBus) and bus_b.subscribers() == 0 and bus_a.subscribers() == 0)

# ---- the sources: no module-level bus state, and the three writers on the session's bus
src = pathlib.Path("engine/domain_events.py").read_text(encoding="utf-8")
check("the module keeps no subscribers or journal switch of its own", "_SUBSCRIBERS" not in src and "_JOURNAL_ON" not in src)
party = pathlib.Path("services/party.py").read_text(encoding="utf-8")
check("the party service imports no module-level publish and publishes through the bus it was given", not re.search(r"import .*\bpublish\b", party)
      and party.count("self._publish(") == 8, party.count("self._publish("))
check("the scene's deeds go on its session's bus", "self.session.bus.publish(event)" in pathlib.Path("scenes/world.py").read_text(encoding="utf-8"))
rx = pathlib.Path("engine/reactions.py").read_text(encoding="utf-8")
check("the reactions subscribe on the session's bus and keep their offs on the session", "session.bus" in rx and "_OFF" not in rx and "session.reaction_offs" in rx)
for n in ("bus_454_a", "bus_454_b"):
    shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
