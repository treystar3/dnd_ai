"""Never refuse a line (f321): what the interpreter cannot name is an improvisation with a consequence; a line that cannot be read is
answered with a question in character, logged as a refusal, and the next line is read as the answer."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import world_improv, refusals, pools
from llm.contracts import ActionIntent
from ui import console
import engine.checks as _checks

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/improv_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("improv_test")
store.meta.seed = 2; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
char.level = 3
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square")
char = ws.player.character
narrated, notes = [], []
ws._narrate_now = lambda event, player_text="": narrated.append(event)
console.note = lambda t, *a, **k: notes.append(t)

# ---- reading what an improvisation is after
check("propping a door is read as blocking", world_improv.read_effect("I prop the door shut with the barrel") == "block")
check("kicking a chest open is read as forcing", world_improv.read_effect("I kick the chest open") == "force")
check("something none of the vocabulary fits is still an attempt", world_improv.read_effect("I juggle three turnips") == "attempt")
check("running through sword forms is practice, not an examination", world_improv.read_effect("I practise sword forms for an hour") == "practise", world_improv.read_effect("I practise sword forms for an hour"))
check("the odds come from the attribute that would do it", 10 <= world_improv.odds_for(char, "force") <= 90)

# ---- a success leaves a mark; the narrator is told it worked
_roll = _checks.roll
_checks.roll = lambda odds, rng=None, c=None: ("success", 1)
ws.on_other(ActionIntent(kind="other", summary="prop the door shut with the barrel"), "I prop the door shut with the barrel")
marks = store.load_place("trading_square").marks
check("a success leaves a lasting mark on the place", any("the way is blocked: prop the door shut with the barrel" in m for m in marks), marks)
check("...and the narrator is told it worked as a decided fact", narrated and "WORKS" in narrated[-1], narrated[-1:])

# ---- a failure is a real event
hp_before = pools.current(char, "health")
_checks.roll = lambda odds, rng=None, c=None: ("failure", 99)
narrated.clear()
ws.on_other(ActionIntent(kind="other", summary="climb onto the roof of the stall"), "I climb onto the roof of the stall")
check("a failed climb hurts and is told as a failure", pools.current(char, "health") < hp_before and "FAILS" in narrated[-1], (hp_before, pools.current(char, "health")))
from engine import law, clock
heat_before = law.current_heat(ws.player, "parth", clock.day(ws.minutes))
narrated.clear()
ws.on_other(ActionIntent(kind="other", summary="kick the shutter in"), "I kick the shutter in")
check("a failed forcing is loud: the watch hears of it", law.current_heat(ws.player, "parth", clock.day(ws.minutes)) > heat_before and "loudly" in narrated[-1])
_checks.roll = lambda odds, rng=None, c=None: ("partial", 50)
narrated.clear()
ws.on_other(ActionIntent(kind="other", summary="rig a snare at the gate"), "I rig a snare at the gate")
check("a partial is done roughly, and marked so", any(m.startswith("roughly, rigged: rig a snare") for m in store.load_place("trading_square").marks) and "half works" in narrated[-1])
_checks.roll = _roll

# ---- a line that cannot be read: the world asks
clerk = ws.present[0]
ws.partner = clerk
said = []
console.npc_says = lambda who, line, g="": said.append((who, line))
stub.a_Clarify = lambda u, k: {"speaker": clerk.id, "line": "Pay the fee, or something else?"}
refusals.SESSION.clear()
ws.ask_back("audit_failed", "i hand it over", "the plan named someone who is not here")
check("the one being spoken to asks, in one line, instead of a system note", said == [(clerk.label(), "Pay the fee, or something else?")] and not any("not sure" in n for n in notes), (said, notes[-1:]))
check("...the refusal is logged with what was asked", refusals.SESSION and refusals.SESSION[-1]["kind"] == "audit_failed" and refusals.SESSION[-1]["asked"].startswith("Pay the fee"))
check("...and the next line will be read as the answer", ws.pending_clarify == {"text": "i hand it over", "question": "Pay the fee, or something else?"})
hints = []
_interp = ws.interpret
ws.interpret = lambda text, hint="": (hints.append(hint), [ActionIntent(kind="look")])[1]
ws.turn("the fee")
check("the interpreter is told the question and reads both lines together", hints and "asked the player a question" in hints[0] and "i hand it over" in hints[0], hints[:1])
check("...and the question is spent once answered", ws.pending_clarify is None)
ws.interpret = _interp
ws.pending_clarify = {"text": "x", "question": "y"}
ws.ask_back("audit_failed", "still nothing", "unreadable")
check("asked once and still unread, the game says so plainly rather than asking again", ws.pending_clarify is None and refusals.SESSION[-1]["kind"] == "clarify_failed")
stub.a_Clarify = lambda u, k: {"speaker": "narrator", "line": ""}
ws.ask_back("talk_whom", "hello there", "said to no one in particular")
check("with no question to ask, the old note stands", any("not sure what you meant" in n for n in notes[-2:]))
check("#refusals sums the session", "refusal(s) this session" in refusals.summary() and "audit_failed" in refusals.summary())

# ---- (f342) a talk aimed at someone of this town who is not about at this hour: the engine says so, no question asked back
ws.pending_clarify = None
ws.enter("guild_house")
clerk_row = next((r for r in store.npc_rows(location="guild_house") if r.role == "guild_clerk"), None)
if clerk_row:
    store.meta.minutes = (store.meta.minutes // 1440) * 1440 + 23 * 60 + 1440           # eleven at night: the clerk's hours are 8 to 18
    ws.enter("guild_house")
    check("after hours the clerk is not about", all(n.id != clerk_row.id for n in ws.present))
    notes.clear(); before = len(refusals.LOG) if hasattr(refusals, "LOG") else None
    calls_before = stub.calls.get("Clarify", 0)
    r = ws.audit_plan("I ask the clerk what contracts are open for my rank.", [ActionIntent(kind="talk", target=clerk_row.id)])
    check("...so asking the clerk is answered by the engine: not about at this hour, and no question asked back",
          r is None and any("not about at this hour" in n for n in notes) and stub.calls.get("Clarify", 0) == calls_before, (r, notes[-2:]))
else:
    check("the guild house has a clerk to be out of hours", False, [(r.id, r.role) for r in store.npc_rows(location="guild_house")])

shutil.rmtree("saves/improv_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
