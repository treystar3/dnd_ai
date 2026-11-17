"""(f723) The measures phase 4's speech work is judged by (docs/design/28_phase4_plan.md, A1), taken by the live gate (f719):
- the size of the speaking prompt and the replies accepted on the first try, for a townsperson's reply and for a companion's:
  read from the run's call log by the measure the nights already use (tools/latency.py first_tries, f475); which tasks are
  which kind of speaker is data (data/replay/gate.yaml speakers);
- leaks: of the replies to the script's lines that ask about something else (a line's `tempts` names what would be a leak
  there: news, happenings, board), those that say a piece of it. The reply is the first thing said aloud in the line's turn, its
  words alone; a line counts only where the town had such a piece to bring up. Counted by the words of the piece, as a fact
  revealed is checked (npc/life.py carries), and roughly: at least two of its longer words.
Reading what the town had around a reply changes nothing: no posting, no model call, no write (tools/nightrun.py town_around).
Each measure has a floor in data/replay/gate.yaml, not set until the owner sets it.
Run: python tools/sim/gate_speech_723_test.py"""
import json
import shutil
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import yaml
import latency
import live_gate
import nightrun
from engine import ambient, data_check, pulse
from npc import life

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


# ---- one rule for "the speech carries the fact"
carries = getattr(life, "carries", lambda speech, text: None)
FACT = "Wolves took three sheep from the miller's upper pasture last night."
check("a speech that shares enough of a fact's own words carries it", carries("They say wolves got into the pasture and took sheep.", FACT) is True)
check("...one that does not, does not; nor does an empty one", carries("A waterskin is four coppers.", FACT) is False and carries("", FACT) is False)


# ---- sizes and first tries: the nights' measure, for one task or for a kind of speaker's tasks together
def call(task, chars, attempt=0, error=None):
    return {"task": task, "attempt": attempt, "chars": chars, "error": error}


calls = [call("npc_conversation", 20000), call("npc_conversation", 30000, error="stiff"), call("npc_conversation", 31000, attempt=1),
         call("npc_conversation", 26000), call("npc_conversation", 36000), call("hire_chat", 9000), call("hire_chat", 11000), call("narrate", 5000)]
first_tries = getattr(latency, "first_tries", lambda calls, tasks: None)
town = first_tries(calls, ("npc_conversation",)) or {}
check("a task's first tries: how many, the share that stood, the median and the 95th percentile of what they read (a retry is not counted: it reads the draft too)",
      (town.get("calls"), town.get("first_try"), town.get("p50"), town.get("p95")) == (4, 0.75, 30000, 36000), town)
check("...several tasks are measured together, and none of them called is nothing measured",
      (first_tries(calls, ("npc_conversation", "hire_chat")) or {}).get("calls") == 6 and first_tries(calls, ("npc_decide",)) is None)
night = latency.speech_measures(calls)
check("...and it is the nights' own measure: each speech task reads the same there", "npc_conversation" in night
      and all(night[t] == first_tries(calls, (t,)) for t in night), night)
speakers = getattr(live_gate, "speakers", lambda calls: {})
by = speakers(calls)
check("the gate's kinds of speaker and their tasks are data, and each kind is measured from the call log",
      set(live_gate.floors().get("speakers") or {}) == {"townsperson", "companion"} and (by.get("townsperson") or {}).get("p95") == 36000
      and (by.get("companion") or {}).get("first_try") == 1.0 and speakers([]) == {"townsperson": None, "companion": None}, by)
F = live_gate.floors()
check("...a kind with a task the budget does not know, or no kinds at all, is refused at startup",
      data_check.gate_problems({**F, "speakers": {"townsperson": ["no_such_task"]}}) and data_check.gate_problems({**F, "speakers": {}})
      and data_check.gate_problems(F) == [], data_check.gate_problems(F))

# ---- the measures, from rows made by hand
NEWS = "Wolves took three sheep from the miller's upper pasture last night."
DAY = "The spring market fills the square today with carts from the lowland farms."
POST = "Clear the gargoyle roost above the quarry road"
around = {"news": [NEWS], "happenings": [DAY], "board": [POST, "Smithy errand"]}
ALL = ["news", "happenings", "board"]
lines = [
    {"say": "I look around.", "shape": "look"},
    {"say": "How much for a waterskin?", "shape": "talk", "tempts": ALL},
    {"say": "Who made that knife?", "shape": "talk", "tempts": ALL},
    {"say": "Which of these jobs is closest?", "shape": "talk", "tempts": ["news"]},
    {"say": "What's been going on in town?", "shape": "talk"},
    {"say": "I ask the smith about the forge.", "shape": "talk", "tempts": ALL},
    {"say": "What's in the stew?", "shape": "talk", "tempts": ALL},
]
rows = [        # numbered as a run numbers them, not as the script does: a row is its line's by what was typed
    {"n": 2, "text": "#continue", "kind": "command", "seconds": 1.0, "said": [["Merchant", NEWS]], "around": around},
    {"n": 3, "text": "I look around.", "kind": "look", "seconds": 3.0, "told": ["The square is quiet."]},
    {"n": 4, "text": "How much for a waterskin?", "kind": "talk", "seconds": 8.0, "around": around,
     "said": [["Merchant", "Four coppers. Did you hear, wolves took sheep from the upper pasture last night."]]},
    {"n": 5, "text": "Who made that knife?", "kind": "talk", "seconds": 8.0, "around": around,
     "said": [["Merchant", "Old Hask at the smithy. Nothing more to tell."], ["Pae", "They say wolves took three sheep from the miller's pasture."]]},
    {"n": 6, "text": "Which of these jobs is closest?", "kind": "talk", "seconds": 8.0, "around": around,
     "said": [["Clerk", "The gargoyle roost above the quarry road is the nearest posting."]]},
    {"n": 7, "text": "What's been going on in town?", "kind": "talk", "seconds": 8.0, "around": around,
     "said": [["Innkeeper", "Wolves took three sheep from the miller's pasture, that's the talk."]]},
    {"n": 8, "text": "I ask the smith about the forge.", "kind": "talk", "seconds": 8.0, "around": around},
    {"n": 9, "text": "What's in the stew?", "kind": "talk", "seconds": 8.0, "around": {"news": [], "happenings": [], "board": []},
     "said": [["Cook", "Wolves took three sheep from the miller's upper pasture, they say."]]},
]
info = {"checked": {"told": 4, "phantom": 0, "spoken": 4, "stiff": 1}, "speakers": by}
read = {"cases": 0, "right": 0, "share": None, "by_kind": {}, "model_failed": 0, "repairs": 0, "wrong": []}
try:
    m = live_gate.measures(read, rows, info, 60.0, game=set(), lines=lines)
except TypeError as e:
    m = {"speech": {}, "error": str(e)}
sp = m["speech"]
check("the gate's speech measures carry each kind of speaker, the townsperson's 95th percentile, and the first tries over all of them",
      (sp.get("speakers") or {}).get("townsperson") == by.get("townsperson") and by.get("townsperson") and sp.get("townsperson_prompt_p95") == 36000
      and sp.get("first_try_share") == round(5 / 6, 3), (sp.get("speakers"), sp.get("townsperson_prompt_p95"), sp.get("first_try_share")))
leaks = sp.get("leaks") or {}
check("a leak is a reply, to a line that asks about something else, that says a piece of what the line marks: one of the three such lines answered here",
      leaks.get("lines") == 3 and leaks.get("leaked") == 1 and sp.get("leak_share") == round(1 / 3, 3), leaks)
check("...the reply is the first thing said (a companion's word after it is not it); a line that tempts only news is no leak for the posting it asks about; "
      "a piece met in one word is no match; a marked line with no reply, or with nothing in town to bring up, is not counted",
      [x.get("line") for x in leaks.get("examples") or []] == [4] and (leaks.get("examples") or [{}])[0].get("who") == "Merchant", leaks.get("examples"))
check("...and, apart from the marked lines, how many replies carried a piece of the town's news at all is reported",
      leaks.get("replies") == 6 and leaks.get("carried_news") == 3, leaks)
bare = live_gate.measures(read, [r for r in rows if r["n"] == 3], {"checked": {}, "speakers": speakers([])}, 60.0, game=set(), lines=lines)["speech"] if not m.get("error") else {}
check("with no speaking call and no marked line answered, each is not measured (never a nought that reads as a pass)",
      bare and bare.get("leak_share") is None and bare.get("leaked") is None and bare.get("first_try_share") is None and bare.get("townsperson_prompt_p95") is None, bare)

# ---- the script's marks, the floors, the report
tmp = Path(tempfile.mkdtemp(prefix="gate_speech_723_"))
script = tmp / "script.yaml"
script.write_text(yaml.safe_dump({"setup": {"seed": 19, "cls": "warrior", "start": "green", "party": 1},
                                  "lines": [{"say": "I look around.", "shape": "look"}, {"say": "How much for bread?", "shape": "talk", "tempts": ["gossip"]}]}), encoding="utf-8")
try:
    live_gate.load_script(script)
    refused = False
except SystemExit:
    refused = True
check("a script line marked to tempt something the gate cannot count is refused", refused)
NEW = ("leaks", "townsperson_prompt_p95_chars", "first_try_share")
check("the gate's floors have the three new measures, not set until the owner sets them", all(k in (F.get("floors") or {}) for k in NEW),
      [k for k in NEW if k not in (F.get("floors") or {})])
set_floors = {**F, "floors": {**{k: None for k in F["floors"]}, "leaks": 0, "townsperson_prompt_p95_chars": 14000, "first_try_share": 0.9}}
under = live_gate.held(m, set_floors) if not m.get("error") else []
check("each is held against its floor: a leak over none, a prompt over its size, a first-try share under its floor",
      len(under) == 3 and any(u.startswith("leaks:") for u in under) and any(u.startswith("townsperson_prompt_p95_chars:") for u in under)
      and any(u.startswith("first_try_share:") for u in under), under)
text = live_gate.report(m, under, set_floors, {"date": "2026-11-17", "model": "a-model", "mode": "the whole gate"}) if not m.get("error") else ""
check("the report gives the three in its table, each counted reply with who said it, and says how the leaks were counted",
      "Leaks" in text and "36000" in text and "first try" in text.lower() and "Merchant said" in text and "tempts" not in text, text[:600])

# ---- what the town had around a reply is read, never made
g = simlib.campaign("gate_speech_723", seed=5, location="guild_house")
ws = g.scene
gid = ws.hall_here()
town_around = getattr(nightrun, "town_around", lambda ws: {})
due = bool(gid) and g.store.load_place(gid).board_day < 0
before = (dict(stub.calls), g.store.load_place(gid).model_dump_json() if gid else "")
got = town_around(ws)
check("read where the hall's board is due to be posted, it posts none: no model call, the hall as it was, no posting to name",
      due and (dict(stub.calls), g.store.load_place(gid).model_dump_json()) == before and got.get("board") == [] and set(got) == {"news", "happenings", "board"},
      (due, got))
posted = ws.ensure_board()
ws.player.quests.append({"id": "held_723", "title": "The held errand of the test", "guild": True})
got = town_around(ws)
check("...once the game has posted, the board is its postings by their titles: not what the player holds, no 'nothing is posted'",
      posted and got.get("board") == [q["title"] for q in posted] and not any("held" in b or "nothing" in b for b in got.get("board") or []), got.get("board"))
kept = (pulse.happenings_at, ambient.lines)
pulse.happenings_at = lambda *a, **k: ["A funeral crosses the square for the old ferryman."]
ambient.lines = lambda *a, **k: ["Market day fills the square with carts."]
try:
    got = town_around(ws)
finally:
    pulse.happenings_at, ambient.lines = kept
check("...a happening is the town's own, not the ordinary day anyone can see (a line about market day is no leak)",
      any("funeral" in h for h in got.get("happenings") or []) and not any("Market day" in h for h in got.get("happenings") or []), got.get("happenings"))
g.close()

# ---- the night run keeps who said what, the words alone; the gateway's own log is what the measure reads
import config
from llm import gateway
from llm.contracts import Narration
from ui import console
(tmp / "r").mkdir()
run = nightrun.Run(tmp / "r", 0, 0, live=False)
run.install_console()
try:
    console.now("npc_says")("Merchant", "Four coppers.", "shrugs")
    console.now("dialogue")("He leans on the counter.", "Merchant", "Take it or leave it.", "He turns away.")
    console.now("say")("Leave it, then.", "Pae")
    console.now("narrate")("The stall is quiet.")
finally:
    for name, fn in run.real.items():
        console.put(name, fn)
    for f in (run.turn_file, run.transcript, run.errors):
        f.close()
check("what is said aloud in a turn is kept as who and the words alone: no label, no gesture, none of the narration around it",
      run.turn_said == [["Merchant", "Four coppers."], ["Merchant", "Take it or leave it."], ["Pae", "Leave it, then."]]
      and any("Four coppers. (shrugs)" in x for x in run.passage), run.turn_said)
log_was = config.LOG_PATH
config.LOG_PATH = str(tmp / "calls.jsonl")
real, tries = stub.a_Narration, []


def second_time(u, k):
    tries.append(1)
    return {"wrong": 1} if len(tries) == 2 else real(u, k)


stub.a_Narration = second_time
try:
    gateway.generate("narrate", "S" * 100, "U" * 400, Narration)
    gateway.generate("narrate", "S" * 100, "U" * 200, Narration)
finally:
    stub.a_Narration, config.LOG_PATH = real, log_was
got = first_tries(latency.load(tmp / "calls.jsonl"), ("narrate",)) or {}
check("the gateway's own log is what the measure reads: two calls, one that needed a second try, each first try's size",
      len(tries) == 3 and (got.get("calls"), got.get("first_try"), got.get("p50"), got.get("max")) == (2, 0.5, 300, 500), (len(tries), got))

# ---- the stand-in model plays a marked script (it never talks: the rows' shape and the gate's file are what is checked)
lines2 = [{"say": "I look around.", "shape": "look"}, {"say": "I ask my companion what they make of this place.", "shape": "talk", "tempts": ["news"]},
          {"say": "I look around again.", "shape": "look"}]
script.write_text(yaml.safe_dump({"setup": {"seed": 19, "cls": "warrior", "start": "green", "party": 1}, "lines": lines2}), encoding="utf-8")
rc = live_gate.main(["--stub", "--script", str(script), "--out", str(tmp / "run"), "--no-reading"])
play = tmp / "run" / "play"
played = [json.loads(l) for l in (play / "turns.jsonl").read_text(encoding="utf-8").splitlines()] if (play / "turns.jsonl").exists() else []
out = json.loads((tmp / "run" / "live_gate.json").read_text(encoding="utf-8")) if (tmp / "run" / "live_gate.json").exists() else {}
info2 = json.loads((play / "run.json").read_text(encoding="utf-8")) if (play / "run.json").exists() else {}
check("each row of a played script carries what was said aloud in its turn; the run's record is the night's own, with nothing of the gateway's added",
      rc == 0 and len(played) == 3 and all(isinstance(r.get("said"), list) for r in played) and "sizes" not in info2 and "tally" not in info2,
      [(r.get("said"), r.get("around")) for r in played][:3])
check("...and the gate's own file has the speech measures, each kind of speaker read from the run's call log (nobody spoke: not measured)",
      {"speakers", "townsperson_prompt_p95", "first_try_share", "leaks", "leak_share"} <= set(out.get("speech") or {}) and (play / "llm_calls.jsonl").exists()
      and out["speech"]["speakers"] == speakers(latency.load(play / "llm_calls.jsonl")) and set(out["speech"]["speakers"]) == {"townsperson", "companion"},
      (sorted(out.get("speech") or {}), (out.get("speech") or {}).get("speakers")))
shutil.rmtree(tmp, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
