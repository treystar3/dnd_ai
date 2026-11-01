"""(f435) The canon check fails closed. What someone says about themselves near something already true of them is checked once for a
contradiction (engine/canon.py judge); when the model could not be asked, the claim was taken as new and kept as their canon: who they
are, for good, never checked. Now it waits, unsettled: not true of them, not offered back, nothing about them changed; and the next time
something about them is kept (a model call about them has just answered), a few waiting claims are checked again: new ones are kept,
repeats and contradictions let go, never sent back."""
import copy, json, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("bard", 35)
simlib.install(stub)
from engine import canon
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

MODE = {"check": "down"}
real = gateway._client
def chat(**k):
    if k["format"].get("title") == "CanonCheck":
        if MODE["check"] == "down":
            raise ConnectionError("the model server cannot be reached")
        out = {"verdict": MODE["check"], "which": 1 if MODE["check"] != "new" else 0}
        return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=json.dumps(out)))
    return real.chat(**k)
gateway._client = types.SimpleNamespace(chat=chat)

details = ["They grew up in a fishing village on the Kelp coast."]
member = {"name": "Hilsa", "details": list(details), "canon": [{"text": "I lost my brother to the sea when I was twelve.", "day": 1}]}
claim = "My brother taught me to sail before the sea took him."
texts = lambda key: [x["text"] for x in member.get(key, [])]

# ---- the model down: the claim waits, and nothing about them changes
held = copy.deepcopy(member["canon"])
sent_back = canon.keep(member, [claim], [], 5, details, None, "Hilsa")
check("a claim the check could not be asked about is not kept as who they are", claim not in texts("canon"), texts("canon"))
check("...it waits, unsettled", claim in texts("unsettled"), member.get("unsettled"))
check("...what was true of them is untouched", member["canon"] == held)
check("...and the line is not sent back as contradicting", sent_back == [], sent_back)
check("...the record says it went unverified", any(e["claim"] == claim and e["verdict"] == "unverified" for e in canon.EVENTS[-5:]), canon.EVENTS[-3:])
check("...it is never offered back as true", not any(claim in r["text"] for r in canon.records(member, 5)))
check("...nor weighed against as a fact", claim not in canon.known(member, details))
check("...but the extractor knows it was said", claim in canon.said_about_self(member))
canon.keep(member, [claim], [], 5, details, None, "Hilsa")
check("said again, it waits once", texts("unsettled").count(claim) == 1, texts("unsettled"))

# ---- a cap on what waits
cap = canon.UNSETTLED["cap"]
for i in range(cap):
    canon.keep(member, [f"My brother and I sailed the boat called {w}." for w in (f"Gull{i}", f"Tern{i}")], [], 6, details, None, "Hilsa")
check(f"no more than {cap} claims wait, the oldest let go first", len(member["unsettled"]) == cap and claim not in texts("unsettled"),
      len(member["unsettled"]))

# ---- the model back: a few are checked again each time something is kept
first_two = texts("unsettled")[:canon.UNSETTLED["again_per_keep"]]
MODE["check"] = "new"
canon.keep(member, [], [], 7, details, None, "Hilsa")
check("with the model back, the oldest waiting claims are checked again and kept when new",
      all(c in texts("canon") for c in first_two) and not any(c in texts("unsettled") for c in first_two), (first_two, texts("canon")[-3:]))
check(f"...{canon.UNSETTLED['again_per_keep']} at a time", len(member["unsettled"]) == cap - len(first_two), len(member["unsettled"]))
nxt = texts("unsettled")[0]
MODE["check"] = "contradicts"
sent_back = canon.keep(member, [], [], 8, details, None, "Hilsa")
check("one that contradicts what is true of them is let go, never kept", nxt not in texts("canon") and nxt not in texts("unsettled"))
check("...and never sent back: the line it came from was said long ago", sent_back == [], sent_back)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
