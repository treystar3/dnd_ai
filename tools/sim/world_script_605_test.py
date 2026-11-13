"""(f605) What phase 2's plan asked of the world script (docs/design/14_phase2_plan.md, section 5 and f597's tests) and it lacked: an
act that moves a situation, on the act path, in one ruling (f600), beside the rest the script covers; and the count of the model's calls
over the whole play, asserted by kind, so a later change that multiplies them fails here and says which kind grew (risk 3: calls
multiply once the caps go). The script's own steps make an exact count (CALLS); the world's births over its days are held to a
ceiling (BIRTHS_MOST), so tuning births moves no pin; a kind of call not listed fails. world_script_579_test checks the count is the
same on two plays. A change that moves CALLS on purpose updates it and says why in its commit.
Run: python tools/sim/world_script_605_test.py"""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools/sim")
import world_script

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


CALLS = {"ActRuling": 1, "ActionPlan": 3, "AuditMeaning": 1, "AuditVerdict": 1, "JudgeVerdict": 2, "Narration": 4, "ResidentSet": 1}
BIRTHS_MOST = {"ThreadProposal": 2, "SituationParts": 1}   # the pulse's births over the script's days, as f605 measured them

d = world_script.run_apart("world_script_605")
check("the script covers an act that moves a matter, on the act path, in one ruling and no second",
      d["cover"].get("an act moved a matter, in one ruling") is True, sorted(d["cover"]))
check("...and everything else it covers still holds", all(d["cover"].values()), [k for k, v in d["cover"].items() if not v])
calls = d.get("calls") or {}
check("the script's own calls, by kind, are as measured: a change that multiplies them fails here",
      {k: calls.get(k) for k in CALLS} == CALLS, {k: (v, calls.get(k)) for k, v in CALLS.items() if calls.get(k) != v})
check("...the world's births over its days stay within their ceiling", all(calls.get(k, 0) <= v for k, v in BIRTHS_MOST.items()),
      {k: (v, calls.get(k)) for k, v in BIRTHS_MOST.items()})
check("...and no kind of call the script never made appears", set(calls) <= set(CALLS) | set(BIRTHS_MOST), sorted(set(calls) - set(CALLS)))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
