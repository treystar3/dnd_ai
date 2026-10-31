"""(f416) One turn record every writer reads. A night's passages acted out steps the game had refused (a whetstone the player did not
have rasped along their blade; a dungeon they were not at was walked into), because the narrator was handed the player's words and never
told what did not happen; a refused cot stopped the sleep that came after it; a contract taken at the board, with no line shown, was
answered 'Nothing comes of that here'; and most refusals the page showed never reached the refusals log. Now a refusal is one call that
shows the note, keeps a row of what did not happen, logs it, and stops the rest of the line only when the rest rests on it; every narrator
is told the rows once, before the player's words; and a person answering the player reads everything the turn has settled."""
import ast, json, pathlib, random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 6))
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
for fn in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
import config
from engine import actions, ledger, refusals
from llm.contracts import ActionIntent as A, Narration
from npc.traits import load_traits
from scenes import combat_prompts as cp
import scenes.world as W
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

LOG = "saves/turn_record_416_refusals.jsonl"
config.REFUSALS_LOG, config.REFUSALS_LOG_PATH = True, LOG      # the stub turns the log off; this test reads it
pathlib.Path(LOG).unlink(missing_ok=True)
shutil.rmtree("saves/turn_record_416_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("turn_record_416_test")
store.meta.seed = 6; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(6))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("parth")

asked = []
real_fresh = W.fresh
W.fresh = lambda task, system, request, *a, **k: (asked.append((task, request)), Narration(text="You sit a while on the bench.") if task == "narrate"
                                                   else real_fresh(task, system, request, *a, **k))[1]
ws.audit_plan = lambda text, plan, raw=None: plan              # the plans below are the ones under test, as read
PLAN = []
ws.interpret = lambda text, hint="": [a.model_copy(deep=True) for a in PLAN]

def turn(text, plan):
    PLAN[:] = plan
    asked.clear(); NOTES.clear()
    ws.last_text = text
    ws.turn(text)
    return next((r for t, r in reversed(asked) if t == "narrate"), "")

# ---- a refused step is told as not done, before the player's words, and logged
n0 = sum(1 for r in refusals.SESSION if r["kind"] == "refused")
req = turn("I sit on a bench and sharpen my blade with my whetstone",
           [A(kind="other", summary="sit on a bench and sharpen the blade"), A(kind="use", item="whetstone", summary="use the whetstone")])
check("the player reads why the whetstone cannot be used", "You have nothing like that you can use." in NOTES, NOTES)
check("...and the passage is told it did not happen", "NOT DONE, never show it done: use the whetstone" in req, req[-700:])
did, ev, words = req.find("WHAT THE GAME DID THIS TURN"), req.find("GAME EVENT:"), req.find("PLAYER'S WORDS")
check("...what the game did comes before the event, and the player's words after, marked as only what they typed",
      0 <= did < ev < words and "only what the game did happens" in req[words:words + 120], (did, ev, words))
check("...the turn's record keeps the refused row", any(r["kind"] == "refused" and r["step"] == "use" for r in ledger.LAST), ledger.LAST)
logged = [r for r in refusals.SESSION if r["kind"] == "refused"]
check("...and the refusal is in the log, with the line and the reason", len(logged) == n0 + 1 and "whetstone" in logged[-1]["text"]
      and "nothing like that" in logged[-1]["why"], logged[-1:])
rows = [json.loads(l) for l in pathlib.Path(LOG).read_text().splitlines()] if pathlib.Path(LOG).exists() else []
check("...written to logs/refusals.jsonl", any(r["kind"] == "refused" and "whetstone" in r["text"] for r in rows), rows[-1:])

# ---- the rest of the line goes on unless it rests on the refused step
m0 = ws.minutes
turn("I lie down on my cot and sleep till dawn", [A(kind="use", item="cot", summary="lie down on the cot"),
                                                 A(kind="wait", wait_until="dawn", summary="sleep till dawn")])
check("a cot that cannot be used does not stop the sleep after it", "wait" in ws.ran and ws.minutes - m0 >= 120, (ws.ran, ws.minutes - m0))
turn("I retrieve my sword from the box and equip it", [A(kind="retrieve", item="sword", summary="take the sword from the item box"),
                                                       A(kind="equip", item="sword", summary="equip the sword")])
check("...but what comes of a step the game refused is not done either: no box, no sword to equip", "equip" not in ws.ran, ws.ran)
check("the steps nothing later rests on are few and declared in the table", {a.kind for a in actions.ACTIONS if not a.needed_by_rest}
      >= {"look", "use", "wait", "other"} and actions.BY_KIND["move"].needed_by_rest and actions.BY_KIND["buy"].needed_by_rest)

# ---- told once, and to every narrator
ledger.begin()
ledger.add("took", say="The player has taken the contract 'Wolves at the Mill'.")
check("a row is told to one passage, and not again to the next", ledger.told() and not ledger.told())
check("...while what the turn has decided stays readable to a person answering", ledger.decided() == ["The player has taken the contract 'Wolves at the Mill'."])
ledger.begin()
ledger.add("refused", step="buy", what="buy a room", why="no room is free", say="NOT DONE, never show it done: buy a room (no room is free).")
asked.clear()
ws.narrate_with(cp.START_SYSTEM, "A wolf lopes out of the trees.")
check("the fight's opening and a sighting are told the turn's rows too", asked and "buy a room" in asked[-1][1], asked[-1:])
try:
    ledger.add("bought", say="x")
    check("a row of a kind nobody declared is refused", False)
except ValueError:
    check("a row of a kind nobody declared is refused", True)

# ---- a turn that showed nothing, but did something, is told
ledger.begin()
ledger.add("took", say="The player has taken the contract 'Wolves at the Mill' at the board; the clerk records it.")
asked.clear(); NOTES.clear()
ws.said_nothing("I take the wolves contract")
check("a turn that took a contract and showed nothing tells it, in the world", asked and "Wolves at the Mill" in asked[-1][1]
      and not any("Nothing comes of that" in n for n in NOTES), (asked[-1:], NOTES))
ledger.begin()
asked.clear(); NOTES.clear()
ws.said_nothing("I do the thing")
check("...and one that did nothing still says so", not asked and any("Nothing comes of that" in n for n in NOTES), NOTES)

# ---- taking a contract writes its row
hall = "guild_house"                                           # Parth's
from engine import clock
store.meta.minutes += round((12 - clock.hour(ws.minutes)) % 24 * 60)    # midday, when the clerk is at the desk
ws.enter(hall)
ws.player.guild_rank = "F"
board = ws.ensure_board()
post = next((q for q in board if q["letter"] == "F" and q["kind"] not in ("missing", "delve")), None)
ledger.begin()
if post is not None and ws.clerk_here():
    ws.on_accept_quest(A(kind="accept_quest", item=post["title"]), f"I take {post['title']}")
    check("taking a contract at the board keeps a row the turn can tell", any(r["kind"] == "took" and post["title"] in r["say"] for r in ledger.ROWS),
          ledger.ROWS)
else:
    check("taking a contract at the board keeps a row the turn can tell (a board and a clerk to test with)", False, (post, ws.clerk_here()))

# ---- a person answering reads what the turn has settled
heard = []
real_converse = W.converse
W.converse = lambda npc, store, world, catalog, convo, speech, ctx, **k: (heard.append(ctx), real_converse(npc, store, world, catalog, convo, speech, ctx, **k))[1]
npc = next((n for n in ws.present), None)
ledger.add("refused", step="sell", what="sell the wool hood", why="no one here buys cloth",
           say="NOT DONE, never show it done: sell the wool hood (no one here buys cloth).")
if npc is not None:
    ws.on_talk(A(kind="talk", target=npc.id, speech="So, will you take the hood?"), "So, will you take the hood?")
check("a person answering is told what the game has decided this turn", heard and any("WHAT THE GAME HAS DECIDED THIS TURN" in l
      and "wool hood" in l for l in heard[-1]), heard[-1][-2:] if heard else "no one to talk to")
W.converse = real_converse

# ---- no refusal goes unrecorded: a note and a halt are one call now
pairs = []
for p in pathlib.Path("scenes").glob("*.py"):
    src = p.read_text()
    lines = src.split("\n")
    for node in ast.walk(ast.parse(src)):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for a, b in zip(body, body[1:]):
            if (isinstance(a, ast.Expr) and isinstance(a.value, ast.Call) and getattr(a.value.func, "attr", "") == "note"
                    and getattr(getattr(a.value.func, "value", None), "id", "") == "console" and isinstance(b, ast.Assign)
                    and getattr(b.targets[0], "attr", "") == "halted" and getattr(b.value, "value", None) is True
                    and "the player's choice" not in lines[b.lineno - 1]):
                pairs.append(f"{p}:{a.lineno}")
check("every refusal in the scenes goes through refuse(), not a note and a halt", not pairs, pairs)

# ---- the log stays bounded
config.LOG_MAX_MB, keep = 0.0001, config.LOG_KEEP_ENTRIES
config.LOG_KEEP_ENTRIES = 5
for i in range(40):
    refusals.note("refused", f"line {i}", "a reason of some length to fill the file past its small test limit", "parth", i)
check("the refusals log is trimmed like the others", len(pathlib.Path(LOG).read_text().splitlines()) <= 6)
config.LOG_KEEP_ENTRIES = keep

W.fresh = real_fresh
store.close()
shutil.rmtree("saves/turn_record_416_test", ignore_errors=True)
pathlib.Path(LOG).unlink(missing_ok=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
