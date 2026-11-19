"""(f729) The live gate before the measure of decide then speak (docs/design/28_phase4_plan.md A1's finding, A6). Two things the
first whole run showed the gate could not say:
- whether its leak count could have failed. The script's marked lines were all played where the town had no news yet, so the
  four that counted could only have leaked a posting. Now the gate says, of the marked lines answered aloud, how many had news
  or a happening around them (among what the line marks), holds that against a floor of its own (leak_lines_with_news: under
  it the leak count measures little), and says so in plain words when none had;
- what the reading before a reply costs (f725's npc_decide): its size and first tries, as a speaker's are measured, never
  counted among the speakers, and what a townsperson's reply reads in all (its reading and its speaking).
Run: python tools/sim/gate_leaks_729_test.py"""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import live_gate
from engine import data_check

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


if not hasattr(live_gate, "readings"):
    check("the gate measures the reading before a reply (tools/live_gate.py readings)", False)
    sys.exit(1)
F = live_gate.floors()


# ---- the reading before a reply: data says which tasks; measured as a speaker's are, apart from them
def call(task, chars, attempt=0, error=None):
    return {"task": task, "attempt": attempt, "chars": chars, "error": error}


calls = [call("npc_conversation", 9000), call("npc_conversation", 11000), call("npc_conversation", 10000, error="stiff"), call("npc_conversation", 10500, attempt=1),
         call("npc_decide", 4000), call("npc_decide", 5000, error="bad json"), call("npc_decide", 5200, attempt=1), call("npc_decide", 6000),
         call("hire_chat", 9000)]
check("gate.yaml says which calls read a line before someone speaks (readings: a kind and its budget tasks), and the startup check passes",
      (F.get("readings") or {}).get("townsperson") == ["npc_decide"] and data_check.gate_problems() == [], (F.get("readings"), data_check.gate_problems()))
check("...a reading of a task the budget does not know is refused, one for no kind of speaker the gate has, and the file without the table",
      data_check.gate_problems({**F, "readings": {"townsperson": ["no_such_task"]}}) and data_check.gate_problems({**F, "readings": {"reply": ["npc_decide"]}})
      and data_check.gate_problems({k: v for k, v in F.items() if k != "readings"}))
rd = live_gate.readings(calls)
check("the reading's first tries are measured as a speaker's are: how many, the share that stood, the median and 95th percentile of what they read",
      ((rd.get("townsperson") or {}).get("calls"), (rd.get("townsperson") or {}).get("first_try"), (rd.get("townsperson") or {}).get("p50")) == (3, round(2 / 3, 3), 5000), rd)
check("...and with no such call (the switch off) nothing is measured for it", live_gate.readings([call("npc_conversation", 9000)]) == {"townsperson": None})

NEWS = "Wolves took three sheep from the miller's upper pasture last night."
DAY = "The watch is out in force after the fire at the tannery."
POST = "Gargoyle roost above the quarry road"
ALL = ["news", "happenings", "board"]
full = {"news": [NEWS], "happenings": [DAY], "board": [POST]}
posted = {"news": [], "happenings": [], "board": [POST]}
lines = [
    {"say": "How much for a waterskin?", "shape": "talk", "tempts": ALL},
    {"say": "Who made that knife?", "shape": "talk", "tempts": ALL},
    {"say": "Can you put an edge on this?", "shape": "talk", "tempts": ALL},
    {"say": "How long have you had the forge?", "shape": "talk", "tempts": ["board"]},
    {"say": "What did you do before this work?", "shape": "talk", "tempts": ["news"]},
    {"say": "What's in the stew?", "shape": "talk", "tempts": ALL},
    {"say": "What's been going on in town?", "shape": "talk"},
]
rows = [
    {"n": 1, "text": "How much for a waterskin?", "kind": "talk", "seconds": 8.0, "around": full,
     "said": [["Merchant", "Four coppers. Did you hear, wolves took sheep from the upper pasture last night."]]},
    {"n": 2, "text": "Who made that knife?", "kind": "talk", "seconds": 8.0, "around": posted, "said": [["Merchant", "Old Hask at the smithy."]]},
    {"n": 3, "text": "Can you put an edge on this?", "kind": "talk", "seconds": 8.0, "around": {"news": [], "happenings": [DAY], "board": []},
     "said": [["Smith", "Leave it with me till noon."]]},
    {"n": 4, "text": "How long have you had the forge?", "kind": "talk", "seconds": 8.0, "around": full, "said": [["Smith", "Twenty years come spring."]]},
    {"n": 5, "text": "What did you do before this work?", "kind": "talk", "seconds": 8.0, "around": posted, "said": [["Pae", "Fished, mostly."]]},
    {"n": 6, "text": "What's in the stew?", "kind": "talk", "seconds": 8.0, "around": full},
    {"n": 7, "text": "What's been going on in town?", "kind": "talk", "seconds": 8.0, "around": full,
     "said": [["Innkeeper", "Wolves took three sheep from the miller's pasture, that's the talk."]]},
]
read = {"cases": 0, "right": 0, "share": None, "by_kind": {}, "model_failed": 0, "repairs": 0, "wrong": []}
info = {"checked": {"told": 0, "phantom": 0, "spoken": 6, "stiff": 0}, "speakers": live_gate.speakers(calls), "readings": rd}
m = live_gate.measures(read, rows, info, 60.0, game=set(), lines=lines)
sp = m["speech"]
lk = sp.get("leaks") or {}

# ---- the leak count says whether it could have failed
check("of the marked lines answered aloud where the town had something, the gate counts those that had news or a happening among what the line marks",
      lk.get("lines") == 4 and lk.get("with_news") == 2 and sp.get("leak_lines_with_news") == 2, lk)
check("...a line marked for postings alone is not one of them though news was around; nor is one with only a posting around; a line not answered aloud counts nowhere",
      lk.get("leaked") == 1 and [x.get("line") for x in lk.get("examples") or []] == [1], lk)
none = live_gate.measures(read, [r for r in rows if r["n"] in (2, 4)], info, 60.0, game=set(), lines=lines)["speech"]
bare = live_gate.measures(read, [r for r in rows if r["n"] == 7], info, 60.0, game=set(), lines=lines)["speech"]
check("with marked lines answered and none of them near news, the count is nought, not nothing; with no marked line answered at all it is not measured",
      none.get("leak_lines_with_news") == 0 and none["leaks"]["lines"] == 2 and bare.get("leak_lines_with_news") is None, (none.get("leaks"), bare.get("leaks")))
check("the floors have it, not set until the owner sets it, and the startup check knows it",
      "leak_lines_with_news" in (F.get("floors") or {}) and "leak_lines_with_news" in live_gate.HELD and live_gate.HELD["leak_lines_with_news"][1] is True, sorted(F.get("floors") or {}))
set_floors = {**F, "floors": {**{k: None for k in F["floors"]}, "leak_lines_with_news": 3}}
under = live_gate.held(m, set_floors)
check("held against its floor, more being better: two such lines under a floor of three is a miss, and three would pass",
      len(under) == 1 and under[0].startswith("leak_lines_with_news:")
      and live_gate.held(m, {**F, "floors": {**{k: None for k in F["floors"]}, "leak_lines_with_news": 2}}) == [], under)
about = {"date": "2026-11-17", "model": "a-model", "mode": "the whole gate"}
text = live_gate.report(m, under, set_floors, about)
quiet = live_gate.report({**m, "speech": none}, [], F, about)
check("the report gives the count in its table and beside the leaks, in words",
      "news or a happening" in text and "| 2 | 3 |" in text and "2 of those lines" in text, text[:900])
check("...and where no marked line had news around, it says the count could only have failed on a posting",
      "only have failed on a posting" in quiet and "only have failed on a posting" not in text, quiet[-700:])

# ---- the reading in the measures and the report
town = (sp.get("speakers") or {}).get("townsperson") or {}
check("the measures carry the reading apart from the speakers: the first tries over all speakers do not count it",
      (sp.get("readings") or {}).get("townsperson") == rd["townsperson"] and set(sp.get("speakers") or {}) == {"townsperson", "companion"}
      and (sp["speakers"]["townsperson"] or {}).get("calls") == 3 and sp.get("first_try_share") == round(3 / 4, 3),
      (sp.get("readings"), sp.get("first_try_share")))
check("...and roughly what a townsperson's reply reads in all: the median of its speaking and of its own reading, added",
      sp.get("townsperson_reads_in_all_p50") == town.get("p50") + rd["townsperson"]["p50"], (sp.get("townsperson_reads_in_all_p50"), town, rd))
other_kind = live_gate.measures(read, rows, {**info, "readings": {"companion": rd["townsperson"]}}, 60.0, game=set(), lines=lines)["speech"]
check("...a reading before another kind of speaker is not added to the townsperson's", other_kind.get("townsperson_reads_in_all_p50") == town.get("p50"), other_kind.get("townsperson_reads_in_all_p50"))
alone = live_gate.measures(read, rows, {**info, "readings": live_gate.readings([])}, 60.0, game=set(), lines=lines)["speech"]
check("with no reading (the switch off) a reply reads in all what its speaking reads", alone.get("townsperson_reads_in_all_p50") == town.get("p50"), alone.get("townsperson_reads_in_all_p50"))
check("the report has a row for the reading under the speakers and says roughly what a reply reads in all",
      "| the reading before a townsperson's reply | 3 | 5000 |" in text and f"roughly {town.get('p50') + 5000} characters in all" in text, text[-1500:])
old = live_gate.measures(read, rows, {"checked": {}, "speakers": live_gate.speakers(calls)}, 60.0, game=set(), lines=lines)["speech"]
check("a run's record from before the reading was measured still reads: nothing measured for it", old.get("readings") == {} and old.get("townsperson_reads_in_all_p50") == town.get("p50"), old.get("readings"))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
