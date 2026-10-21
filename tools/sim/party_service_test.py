"""The party's mechanics go through one service (services/party.py) and each change is a typed event (engine/domain_events.py) that the
journal records: hiring, dismissing, promotion, going down in a fight (dead or carried), the party's mode. The scene only narrates."""
import random
import sys
sys.path.insert(0, ".")
sys.argv = ["x", "warrior", "2", "1", "1", "1"]
import simbot
from engine import domain_events as ev, party as rules
from services.party import CannotAfford, PartyFull, PartyService
from ui import console as _c
_c.note = lambda t, *a, **k: None
b = simbot.Bot(); ws = b.ws; c = ws.player.character; sys.stdout = sys.__stdout__
c.level = 12; c.coins = 50000
ws.store.meta.minutes = 1440 * 30 + 600
ws.name_ids()
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)
def kinds():
    return [e.kind for e in ev.RECENT]

ws.player.party = []
svc = ws.party_service
check("the scene's service is over the player's record", svc.player is ws.player and isinstance(svc, PartyService))
offers = rules.roster(ws.store.meta.seed, "guild_house", 30, c.level, 50000, [])
check("a roster to hire from", len(offers) >= 3, len(offers))

ev.RECENT.clear()
before = c.coins
m1 = svc.hire(offers[0], c.level)
check("hiring takes the fee, adds the member, marks the roster entry used and publishes MemberJoined",
      c.coins == before - offers[0]["fee"] and m1 in ws.player.party and f"guild_house:{offers[0]['id']}" in ws.player.party_used
      and kinds() == ["party_joined"] and ev.RECENT[-1].member_id == m1["id"] and ev.RECENT[-1].fee == offers[0]["fee"], (kinds(), c.coins, before))
rows = ws.store.journal_tail(5, kind="party_joined")
check("the journal subscriber wrote the row", rows and rows[-1]["target"] == m1["id"] and "hired" in rows[-1]["text"], rows[-1:] if rows else rows)

c.coins = 0
try:
    svc.hire(offers[1], c.level); check("cannot afford is refused", False)
except CannotAfford as e:
    check("cannot afford is refused, nothing changes", e.fee == offers[1]["fee"] and len(ws.player.party) == 1 and kinds() == ["party_joined"])
c.coins = 50000
m2 = svc.hire(offers[1], c.level); m3 = svc.hire(offers[2], c.level)
try:
    svc.hire(offers[3] if len(offers) > 3 else offers[0], c.level); check("a full party is refused", False)
except PartyFull:
    check("a full party is refused", len(ws.player.party) == 3)

ev.RECENT.clear()
gone = svc.dismiss([m3])
check("dismissing removes them, publishes MemberLeft(dismissed), and those who stay remember it",
      gone == [m3] and m3 not in ws.player.party and kinds() == ["party_left"] and ev.RECENT[-1].how == "dismissed"
      and any("sent" in x["text"] and m3["name"] in x["text"] for x in m1["memories"]), (kinds(), m1["memories"][-1:]))

ev.RECENT.clear()
why = rules.promotion_block(m1)
m1["capped"] = True; m1["bond"] = 999; m1["fights_since"] = 99
old_rank = m1["rank"]
before = c.coins
o, n, fee = svc.promote(m1, c.level)
check("promotion takes the fee, raises the rank and publishes MemberPromoted",
      o == old_rank and m1["rank"] == n and n != o and c.coins == before - fee and kinds() == ["party_promoted"] and ev.RECENT[-1].new_rank == n, (o, n, fee, kinds()))

ev.RECENT.clear()
rng = random.Random(0)
fates = {}
for seed in range(40):
    m2.pop("down_fate", None)
    fates[seed] = svc.decide_down(m2, random.Random(seed), in_fight=True)
    check_once = seed == 0
check("going down is decided once per fight and both fates occur over seeds",
      set(fates.values()) == {"dead", "carried"} and all(k in ("party_died", "party_carried") for k in kinds()) and len(kinds()) == 40, set(fates.values()))
m2["down_fate"] = "carried"
ev.RECENT.clear()
check("an already-decided fate is not decided or published again", svc.decide_down(m2, random.Random(1)) == "carried" and kinds() == [])
m2.pop("down_fate", None)
dead_seed = next(s for s, f in fates.items() if f == "dead")
ev.RECENT.clear()
svc.decide_down(m2, random.Random(dead_seed), in_fight=True)
died = ev.RECENT[-1]
check("a death mid-fight is published at once, in_fight, before they leave the party",
      died.kind == "party_died" and died.in_fight and m2 in ws.player.party and m2["down_fate"] == "dead")
svc.bury(m2)
check("burying removes them without a second event", m2 not in ws.player.party and kinds() == ["party_died"] and "down_fate" not in m2)
rows = ws.store.journal_tail(3, kind="party_died")
check("the death is in the journal", rows and rows[-1]["target"] == m2["id"], rows[-1:] if rows else rows)

ev.RECENT.clear()
check("mode changes publish once, and not when unchanged",
      svc.set_mode("hold") and ws.player.party_mode == "hold" and svc.set_mode("hold") and kinds() == ["party_mode"])
svc.set_mode("with")
ws.player.party = []
check("no party: nothing to direct", svc.set_mode("hold") is False)

# a subscriber of its own, and one that raises stops the turn rather than being swallowed
seen = []
off = ev.subscribe(ev.MemberLeft, lambda e: seen.append(e.member_id))
c.coins = 50000
m4 = svc.hire(offers[0], c.level)
svc.dismiss([m4])
check("a typed subscriber hears only its type", seen == [m4["id"]], seen)
off()
def boom(e): raise RuntimeError("bug in a subscriber")
off2 = ev.subscribe(ev.MemberJoined, boom)
try:
    svc.hire(offers[1], c.level); check("a raising subscriber is not hidden", False)
except RuntimeError:
    check("a raising subscriber is not hidden", True)
off2()

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
