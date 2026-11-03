"""(f489) The party among themselves: an exchange's system is the same whatever this exchange adds (its own rule, the rule that what they
said of themselves stands, which come at the end of the request, before the count of lines); the characters here are listed, each with a
pronoun; the party's own talk is asked with no operation open, the tail it runs in standing down to ask; how a beat hit each of them goes
back with a rolled-back operation; and a fallen companion is remembered from now in words."""
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import operation
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("shared_489", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter("guild_house")
SEEN = []
real = gateway._client


def chat(**k):
    SEEN.append((k["format"].get("title"), k["messages"][0]["content"], k["messages"][1]["content"],
                 operation.current().kind if operation.current() else None))
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
people = {"Bram": "a scarred sellsword", "Isel": "a quiet healer"}

# ---- one system for every exchange; what this one adds at the end, before the count
SEEN.clear()
ws.exchange(people, "They wait out the rain.", [], (2, 3))
ws.exchange(people, "They wait out the rain.", [], (2, 3), extra_rules="Nobody mentions the war.", members={"Bram": {"id": "h1", "name": "Bram"}})
ex = [s for s in SEEN if s[0] == "Exchange"]
check("an exchange's system is the same with and without a rule of its own and the rule that what they said stands", len(ex) == 2 and ex[0][1] == ex[1][1],
      [len(e[1]) for e in ex])
tail = ex[1][2] if len(ex) == 2 else ""
check("...the exchange's own rules come at the end of the request, before the count of lines", "FOR THIS EXCHANGE" in tail and "Nobody mentions the war." in tail
      and tail.index("FOR THIS EXCHANGE") < tail.index("WRITE 2 TO 3 LINES") and "THE PLAYER'S CHARACTER" not in tail, tail[-400:])

# ---- the characters here, each with a pronoun
c1, c2 = simlib.two_characters(ws)
c1.pronoun, c2.pronoun = "she", "they"
ws.characters = lambda: [c1, c2]
SEEN.clear()
ws.exchange(people, "They wait out the rain.", [], (2, 3))
del ws.characters
req = next((s[2] for s in SEEN if s[0] == "Exchange"), "")
check("the characters here are listed, each with a pronoun", f"{c1.name}, level {c1.level} (she)" in req and f"{c2.name}, level {c2.level} (they)" in req,
      [l for l in req.splitlines() if "level" in l][:3])

# ---- the party's talk asked with no operation open, the tail standing down to ask
from engine import asked
check("the party's own talk is named to be asked outside", {"exchange", "overheard", "pair_dynamic", "persona_details"} <= asked.tasks())
SEEN.clear()
ws.store.arm(True)
op, _ = ws.asked_operation("tail", "", lambda op: ws.exchange(people, "They wait out the rain.", [], (2, 3)), world=True)
ws.store.arm(False)
ex = [s for s in SEEN if s[0] == "Exchange"]
check("...and an exchange the tail asks for is made with no operation open", op.state == "committed" and ex and all(s[3] is None for s in ex), [s[3] for s in ex])

# ---- how a beat hit each of them goes back with its operation
ws.last_hits = {"Bram": 1}


def fails(op):
    ws.last_hits = {"Bram": 3, "Isel": 2}
    raise RuntimeError("the banter's operation fails")


ws.asked_operation("tail", "", fails, world=True)
check("a rolled-back operation takes back how a beat hit each of them", ws.last_hits == {"Bram": 1}, ws.last_hits)

# ---- a fallen companion remembered from now in words
src = open("scenes/banter_actions.py", encoding="utf-8").read()
check("a fallen companion is remembered from now in words, never a count of days", 'f"{days} days ago"' not in src and "clock.ago(d.get(\"minute\"" in src)

gateway._client = real
game.close()
import shutil
shutil.rmtree("saves/shared_489", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
