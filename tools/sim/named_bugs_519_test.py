"""(f519) Two named bugs from Bundle F's survey.

- The canon check failed open: CanonCheck's verdict defaulted to 'new', so an empty answer ({}) kept a claim nobody had checked as who
  that person is (against f435: the canon fails closed). The verdict now has no default: {} is refused, the check failing every try
  reads the claim as unverified, and vet() neither keeps it nor sends it back: it waits, unsettled, as when the model cannot be asked.
- tools/event_eval.py's summary of the model's calls ran dict() over the gateway's OUTCOMES, which are 3-tuples, so it raised and was
  swallowed and the live summary never had its counts. A reader that unpacks them gives the counts per task.

Run: python tools/sim/named_bugs_519_test.py"""

import copy
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import simlib
stub = simlib.Stub("bard", 19)
simlib.install(stub)

from pydantic import ValidationError

from engine import canon
from llm.contracts import CanonCheck

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


# ---- 1. the canon check fails closed on an empty answer
try:
    CanonCheck.model_validate_json("{}")
    refused = False
except ValidationError:
    refused = True
check("an empty answer to the canon check is refused: the verdict has no default", refused)
check("...and the schema the model is held to names the verdict as required", "verdict" in CanonCheck.model_json_schema().get("required", []))
check("...while a real verdict still reads", CanonCheck.model_validate_json('{"verdict": "same", "which": 1}').verdict == "same")

real = simlib.below()          # the stub answering now, taken before the empty-answering source goes in over it
ANSWER = {"text": "{}"}


def chat(**k):
    if k["format"].get("title") == "CanonCheck":
        return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=ANSWER["text"]))
    return real.chat(**k)


empty = simlib.stand_in(chat=chat, name="empty canon check")
facts = ["I lost my brother to the sea when I was twelve."]
claim = "My brother taught me to sail before the sea took him."
verdict, hit = canon.judge(claim, facts)
check("a model answering {} to the canon check, every try, leaves the claim unverified, never new", verdict == "unverified" and hit == ""
      and empty.src.calls["CanonCheck"] >= 1, (verdict, hit, dict(empty.src.calls)))

details = ["They grew up in a fishing village on the Kelp coast."]
member = {"name": "Hilsa", "details": list(details), "canon": [{"text": facts[0], "day": 1}]}
before = copy.deepcopy(member["canon"])
keep, contradicting, unsure = canon.vet(member, [claim], details, who="Hilsa")
check("...vet() neither keeps it nor sends it back as contradicting: it is the claim that could not be checked",
      keep == [] and contradicting == [] and unsure == [claim], (keep, contradicting, unsure))
sent_back = canon.keep(member, [claim], [], 5, details, None, "Hilsa")
check("...and kept as nothing: who they are is untouched, the claim waits unsettled, nothing is sent back",
      member["canon"] == before and claim in [u["text"] for u in member.get("unsettled", [])] and sent_back == [],
      (member["canon"], member.get("unsettled"), sent_back))

ANSWER["text"] = '{"verdict": "new", "which": 0}'
verdict, _ = canon.judge(claim, facts)
check("...while the same source answering a verdict of new is still read as new", verdict == "new", verdict)
empty()

# ---- 2. event_eval's tally of the model's calls
import event_eval
planted = [("thread_proposal", True, 1), ("thread_proposal", False, 3), ("judge_verdict", True, 2), ("thread_proposal", True, 2)]
got = event_eval.model_calls(planted)
check("event_eval's reader gives the model's calls per task from the gateway's (task, succeeded, attempts) outcomes",
      got == {"judge_verdict": {"calls": 1, "failed": 0, "attempts": 2}, "thread_proposal": {"calls": 3, "failed": 1, "attempts": 6}}, got)
try:
    dict(planted)
    old_raised = False
except (TypeError, ValueError):
    old_raised = True
check("...where dict() over them, what the summary did before, raises (and was swallowed)", old_raised)
check("...and the live summary uses the reader", "model_calls(getattr(gateway, \"OUTCOMES\"" in (ROOT / "tools/event_eval.py").read_text(encoding="utf-8"))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
