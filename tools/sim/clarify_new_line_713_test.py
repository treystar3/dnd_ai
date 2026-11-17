"""(f713) A new deed is never read joined to an old question (found in the third blind play, 2026-11-16:
docs/play/2026-11-16_blind_play_journal.md). In Ironvein "ask the watchman" was asked back, then "I go to the market square and
look around" was read joined to it and asked back again, then `I go to the Cinder Mug and lean on the bar.` was read joined to both:
the audit added the earlier lines' steps and the party walked 810 minutes to Parth's trading square. A line after the world's
question was always read as its answer (f321), whatever it said.
Held here: after a question, a line that opens on the player's own deed ("I go...", "We walk...": engine/actions.py
first_person_action) is read alone, as the line it is, and the question is let go; an answer ("the one at the gate", "I mean the
watchman", "Yes, the trading square") is still read with the line it answers.
Run: python tools/sim/clarify_new_line_713_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("clarify_713", seed=4, location="trading_square")
ws = g.scene
ws.enter("trading_square")
seen = []
ws.interpret = lambda text, hint="": (seen.append((text, hint)), [A(kind="look", summary="look around")])[1]
ws.audit_plan = lambda text, plan, raw=None: plan
ws.repair = lambda text, plan: plan


def read(line):
    seen.clear()
    ws.__dict__["_pending_test"] = None
    ws.pending_clarify = {"text": "I step back outside and ask the watchman on the corner why grain's so short.",
                          "question": "Do you mean to ask a watchman, or are you looking for someone else?"}
    ws.understand(line)
    return seen[-1] if seen else ("", ""), getattr(ws, "line_text", "")


for line in ("I go to the Cinder Mug and lean on the bar.", "We walk back down to the gate.", "I cast Twin Flare at the stall."):
    (text, hint), joined = read(line)
    check(f"a deed of its own after a question is read alone: {line!r}", not hint and joined == line and "watchman" not in joined, (hint[:80], joined))
for line in ("the one at the gate", "I mean the watchman by the gate.", "Yes, the one on the corner.",
             "I go there.", "We head that way.", "I'll take the far one."):
    (text, hint), joined = read(line)
    check(f"...while an answer, a deed that points back at the question too, is read with the line it answers: {line!r}",
          "watchman" in hint and "watchman" in joined, (hint[:80], joined))

said = []
real_note = __import__("ui.console", fromlist=["note"]).note
import ui.console as uc
uc.put("note", lambda m, *a, **k: said.append(str(m)))
ws.pending_clarify = {"text": "ask the watchman", "question": "Which watchman?"}
ws.understand("I go to the Cinder Mug and lean on the bar.")
ws.last_text = "I go to the Cinder Mug and lean on the bar."
ws.__dict__.pop("_clarify_called", None)
gen_lines = []
import scenes.audit_actions as aa
real_gen = aa.generate
aa.generate = lambda *a, **k: __import__("types").SimpleNamespace(line="Which bar do you mean?", speaker="")
ws.ask_back("audit_failed", "I go to the Cinder Mug and lean on the bar.", "unclear")
aa.generate = real_gen
check("a new line read alone that is itself unclear gets its own question, never the old one's give-up",
      not any("Still not sure" in s for s in said) and (ws.pending_clarify or {}).get("question") == "Which bar do you mean?", (said, ws.pending_clarify))
check("...and the question keeps the line the player typed, never a join of earlier lines",
      (ws.pending_clarify or {}).get("text") == "I go to the Cinder Mug and lean on the bar.", ws.pending_clarify)
g.close()
shutil.rmtree("saves/clarify_713", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
