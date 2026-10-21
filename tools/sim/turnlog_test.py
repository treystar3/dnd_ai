"""The turn log (engine/turnlog.py): every typed line is one row naming what handled it; an interpreted line carries each interpreter
call in full, keyed by turn like the model log; the session summary counts the lines and the model's tasks; a row promotes to a replay
case without losing the place or what was shown."""
import json, random, shutil, sys
sys.path.insert(0, ".")
import simlib
STUB = simlib.Stub("warrior", 5)
simlib.install(STUB)
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import turnlog
from llm import gateway
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/turnlog_test", ignore_errors=True)
store = CampaignStore.open_or_create("turnlog_test")
store.meta.seed = 3; store.meta.turn = 7; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
place = next(p for p in world.places.values() if p.type in ("inn", "shop") and not p.danger)     # a quiet room, not a guild hall
store.save_player(PlayerState(character=char, location=place.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
config.TURN_LOG_PATH = "saves/turnlog_test/turns.jsonl"
config.SESSION_STATS_PATH = "saves/turnlog_test/sessions.jsonl"
config.LOG_PATH = "saves/turnlog_test/llm_calls.jsonl"
turnlog.COUNTS.clear()
gateway.TALLY.clear()

STUB.plan = [{"kind": "look"}]
turn0 = store.meta.turn
ws.handle("I look around the place")
rows = [json.loads(l) for l in open(config.TURN_LOG_PATH, encoding="utf-8")]
check("an interpreted line is one row naming the interpreter", len(rows) == 1 and rows[0]["handled_by"] == "interpret" and rows[0]["text"] == "I look around the place", rows)
check("the row keeps the audit's fields", rows[0]["audit"] == "skipped" and rows[0]["final"] == [{"kind": "look"}] and rows[0]["place"] == place.id, rows[0])
calls = rows[0].get("interpreter") or []
check("the interpreter's call rides along in full", len(calls) == 1 and 'PLAYER TYPED: "I look around the place"' in calls[0]["request"], calls and list(calls[0]))
check("with the plan read back and what was shown", calls[0]["plan"] == [{"kind": "look"}] and calls[0]["place_name"] == place.name and isinstance(calls[0]["shown"], dict), calls[0] if calls else None)
model_rows = [json.loads(l) for l in open(config.LOG_PATH, encoding="utf-8")]
check("the model log carries the same turn as the key", any(r.get("turn") == turn0 and r["task"] == "interpret_action" for r in model_rows), [(r.get("turn"), r["task"]) for r in model_rows])

ws.handle("I ask the barkeep about the trial")               # away from a hall the trial intercept takes any line about a trial
rows = [json.loads(l) for l in open(config.TURN_LOG_PATH, encoding="utf-8")]
check("a line an intercept took is a row naming the intercept", len(rows) == 2 and rows[1]["handled_by"] == "trial" and rows[1]["text"] == "I ask the barkeep about the trial", rows[-1])
check("and carries no interpreter call", "interpreter" not in rows[1] and rows[1]["turn"] == turn0 + 1, rows[1])
check("the turn passed either way", store.meta.turn == turn0 + 2, store.meta.turn)

stats = turnlog.session_stats()
check("the session summary counts the lines by handler", stats["lines"] == {"interpret": 1, "trial": 1}, stats["lines"])
check("and the model's calls by task", stats["tasks"].get("interpret_action", {}).get("calls") == 1 and stats["tasks"]["interpret_action"]["failed"] == 0, stats["tasks"])
turnlog.write_session_stats()
lines = [l for l in open(config.SESSION_STATS_PATH, encoding="utf-8").read().splitlines() if l.strip()]
check("the summary is one line in the sessions log", len(lines) == 1 and json.loads(lines[0])["lines"]["trial"] == 1, lines)

from tools import replay
case = replay.promote_case(rows[0])
check("a row promotes to a case that keeps the place and the places shown", case["scene"].get("place") == place.name and case["scene"].get("places") == calls[0]["places"] and case["expect"] == [{"kind": "look"}], case)
check("an old-style row without interpreter calls still promotes", replay.promote_case({"text": "x", "raw": [], "final": [], "audit": "skipped"})["scene"] == {"present": {}, "abilities": [], "wildlife": False})

config.TURN_LOG = False
turnlog.COUNTS.clear()
ws.handle("I ask again about the trial")
rows = [json.loads(l) for l in open(config.TURN_LOG_PATH, encoding="utf-8")]
check("with the log off nothing is written but the session still counts", len(rows) == 2 and turnlog.COUNTS == {"trial": 1}, (len(rows), turnlog.COUNTS))
config.TURN_LOG = True

print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)
