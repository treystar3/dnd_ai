"""Permanent hires: a fee by rank, growth at half your pace up to the top of their rank, promotion, wounds and trust, and leaving."""
import sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import party as P, quests
from ui import console
bad = []
_out = sys.stdout
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""), file=_out)
    if not ok: bad.append(n)

fees = [P.rank_fee(r, "fighter") for r in quests.G["ranks"]]
check("a fighter costs 5 silver at F and four times more for each rank up", fees == [500 * 4 ** i for i in range(7)], fees)
check("priests and mages cost more than fighters", P.rank_fee("C", "priest") > P.rank_fee("C", "fighter") and P.rank_fee("C", "mage") > P.rank_fee("C", "priest"))
check("the fee is the same anywhere inside a rank", P.fee({"level": 26, "role": "fighter"}) == P.fee({"level": 44, "role": "fighter"}))
check("an S-rank costs about 205 gold", abs(fees[-1] - 2048000) < 1, fees[-1])

offer = {"id": "1-0", "name": "Test Hire", "role": "fighter", "level": 5, "rank": "F", "blurb": "x", "temper": ["blunt"], "motive": "coin", "line": "x"}
m = P.new_hire(offer, 10, 3)
party = [m]
check("a new hire is permanent, keeps no job and starts with trust from their temperament", m["permanent"] and "arc" not in m and m["bond"] == P.P["bond"]["start"] + P.P["temperaments"]["blunt"]["start"], m["bond"])
P.sync_levels(party, 14)
check("they gain a level for every two of yours", m["level"] == 7, m["level"])
notes = P.sync_levels(party, 100)
check("they stop at the top of their rank band", m["level"] == 9 and m["capped"], m["level"])
check("and say so", any("promoted" in n for n in notes), notes)
check("an F-rank hire reaches the cap long before you reach 150", m["level"] < 10)
check("promotion is refused while they do not trust you or have not fought beside you", bool(P.promotion_block(m)), P.promotion_block(m))
m["bond"], m["fights_since"] = 40, 6
check("promotion is open once they trust you and have fought beside you", P.promotion_block(m) == "")
check("promotion costs the difference between the two ranks", P.promotion_fee(m) == 2000 - 500, P.promotion_fee(m))
P.promote(m, 100)
check("a promoted hire is the next rank, at its first level, uncapped and with a fresh count of fights", m["rank"] == "E" and m["level"] == 10 and not m["capped"] and m["fights_since"] == 0, (m["rank"], m["level"]))
P.sync_levels(party, 120)
check("they then grow again from there", m["level"] == 20, m["level"])
total = sum(P.rank_fee(r, "fighter") for r in ["F"]) + sum(P.promotion_fee({"rank": r, "level": 1, "role": "fighter"}) for r in "FEDCBA")
check("training a hire from F to S costs what hiring an S-rank does, so there is no cheap way round", total == P.rank_fee("S", "fighter"), total)
s = P.new_hire({**offer, "level": 160, "rank": "S"}, 150, 0)
P.sync_levels([s], 200)
check("an S-rank has no cap", s["level"] == 160 + 25 and not s["capped"], s["level"])

h = P.new_hire(offer, 10, 3)
h["bond"] = 10
P.after_fight([(h, 0.8)], True, False, 1000)
check("a fight won together builds trust", h["bond"] == 11, h["bond"])
P.after_fight([(h, 0.8)], True, True, 1000)
check("a hard one builds more", h["bond"] == 13, h["bond"])
P.after_fight([(h, 0.1)], True, False, 1000)
check("a fight that leaves them nearly dead costs trust", h["bond"] == 11, h["bond"])
check("their wounds are remembered", abs(h["hp_frac"] - 0.1) < 1e-9)
check("they mend with time", P.health_now(h, 1000 + P.P["heal_minutes"] // 2) > 0.5 and P.health_now(h, 1000 + P.P["heal_minutes"]) == 1.0)
q = P.new_hire(offer, 10, 3)
q["bond"] = 1
notes = []
for _ in range(4):
    notes += P.after_fight([(q, 0.1)], False, False, 5)
check("low trust brings a warning, once", q["warned"] and sum("not sure" in n for n in notes) == 1, notes)
check("and then they do not go: they turn cold toward the player instead", not hasattr(P, "quitters") and q["bond"] < 0 and P.bond_tier(q) == "cold", (q["bond"], P.bond_tier(q)))
from engine import voice_profile as _vp
check("...which shows in how they are with the player", _vp.relation_kind(bond_tier="cold") == "irritation" and "stopped expecting better" in P.P["bond"]["regard"]["cold"])

sys.argv = ["x", "warrior", "2", "1", "1", "1"]
import simbot
b = simbot.Bot(); ws = b.ws
ws.store.meta.minutes = 5000
ws.player.character.level = 30
ws.player.party = [P.new_hire(offer, 30, 0), {"id": "old", "name": "Old Style", "role": "archer", "level": 5, "blurb": "x", "arc": "a1"}]
ws.player.party[0]["hp_frac"], ws.player.party[0]["hp_at"] = 0.5, 5000
fa = P.fighter(ws.player.party[0], minutes=5000)
check("a hurt hire enters the next fight hurt", abs(fa.hp / fa.max_hp - 0.5) < 0.02, fa.hp / fa.max_hp)
fb = P.fighter(ws.player.party[0], minutes=5000 + 480)
check("and mended once the time has passed", fb.hp == fb.max_hp)
ws.party_disband("a1", "the job is done")
check("the end of a job sends away the old-style hire, never the permanent one", [x["name"] for x in ws.player.party] == ["Test Hire"], ws.player.party)
ws.party_disband(None, "you fell")
check("dying yourself does not send them away", len(ws.player.party) == 1)
random.seed(3)
n_dead = 0
for i in range(200):
    ws.player.party = [P.new_hire({**offer, "id": f"x{i}"}, 30, 0)]
    f = P.fighter(ws.player.party[0], minutes=0)
    f.hp = 0
    ws.party_after_fight([f], [f], True, False)
    n_dead += 0 if ws.player.party else 1
check("a hire who goes down dies about half the time and is otherwise carried out", 70 <= n_dead <= 130, n_dead)
ws.player.party = [P.new_hire(offer, 30, 0)]
ws.player.party[0].update(capped=True, bond=40, fights_since=6)
ws.player.party[0]["rank"] = "F"
ws.player.character.coins = 100000
ws.party_promote("Test", "promote Test", [])
check("promote works from the party and takes the fee", ws.player.party[0]["rank"] == "E" and ws.player.character.coins == 100000 - 1500, (ws.player.party[0]["rank"], ws.player.character.coins))
row = ws.adventurer_row(ws.player.party[0])
check("the party pane row carries trust, temperament, the line they hold and health, never what drives them", all(k in row for k in ("bond", "temper", "line", "health")) and "motive" not in row, row)
said = []
_say = console.say
console.say = lambda t, who=None, *a, **k: said.append((who, t))
ws.player.party = [P.new_hire({**offer, "name": "Tavi Harl"}, 30, 0)]
ws.player.party[0]["bond"] = 10
before = ws.player.party[0]["bond"]
ws.handle("Tavi, how are you holding up?")
check("speaking to a hire by name gets an answer from them", bool(said) and said[-1][0] == "Tavi Harl", said)
check("and it is remembered and builds a little trust, once a day", ws.player.party[0]["talk"] and ws.player.party[0]["bond"] == before + 1, ws.player.party[0]["bond"])
ws.handle("Tavi, what do you want out of this?")
check("a second talk the same day adds no more", ws.player.party[0]["bond"] == before + 1)
console.say = _say
_odd = P.unclassified(ws.player.party[0])
check("every field on a hire is classified in engine/party.py (who they are, what play gave them, or the engine's numbers)", not _odd, _odd)
print("FAILED" if bad else "ALL PASS", bad, file=_out)
sys.exit(1 if bad else 0)
