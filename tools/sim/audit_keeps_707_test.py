"""(f707) What the audit would add that the player's words never ask for is dropped, and the rest of its correction is weighed as it
stands: a sound first reading is never refused over the audit's own addition (found in the third blind play, 2026-11-16:
docs/play/2026-11-16_blind_play_journal.md). "We set off for Ironvein to hand in the snake bounty." was read as a move, the talk that
only narrated it dropped; the audit wanted the talk back ("The player tells the group they are heading to Ironvein"), f699 refused
that addition twice, and the player was asked "Are you telling the group we're leaving, or are you asking to start the trek?".
Held here: a correction whose only change is an unasked step leaves the first reading as it was (unchanged); a correction that sets a
step right and adds an unasked one keeps the step set right and drops the addition; an addition the words do ask for stands (f699).
Run: python tools/sim/audit_keeps_707_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
simlib.quiet_console()
from engine import intent_audit as ia
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


class Ask:
    def __init__(self, proposal):
        self.proposal = proposal
    def meaning(self, t, s):
        return "they tell the group they are heading off, and go"
    def compare(self, t, m, d, r):
        return False, "the plan leaves out telling the group"
    def propose(self, t, h):
        return [s.model_copy(deep=True) for s in self.proposal]


sit = ia.Situation(present={"hire:0-0": "Morm", "smith1": "the smith"}, place="the Greyhollow foothills")


def run(text, plan, proposal, flag="multi_intent"):
    real = ia.risk_flags
    ia.risk_flags = lambda *a, **k: real(*a, **k) or [flag]
    try:
        r = ia.audit(text, plan, sit, Ask(proposal))
    finally:
        ia.risk_flags = real
    return r.status, [(s.kind, s.destination or s.target) for s in r.plan], r.reason


go = "We set off for Ironvein to hand in the snake bounty."
move = [A(kind="move", destination="ironvein", summary="Travel to Ironvein")]
tell = A(kind="talk", target="hire:0-0", speech="We set off for Ironvein.", summary="The player tells the group they are heading to Ironvein")
st, steps, why = run(go, move, move + [tell])
check("a sound move is never refused over the audit's own unasked talk: the first reading stands", st == "unchanged" and steps == [("move", "ironvein")],
      (st, steps, why))
st, steps, why = run(go, move, [tell] + move)
check("...whichever side of the move the audit puts it", st == "unchanged" and steps == [("move", "ironvein")], (st, steps, why))

wrong = [A(kind="move", destination="ironvein_mine", summary="go to the mine")]
st, steps, why = run("We go to Ironvein.", wrong, [A(kind="move", destination="ironvein", summary="go to Ironvein"),
                                                  A(kind="attack", target="smith1", summary="attack the smith")])
check("a correction that sets a step right and adds an unasked deed keeps the step set right, the deed dropped",
      st == "changed" and steps == [("move", "ironvein")], (st, steps, why))

room = "We walk to Ironvein and sleep until morning."
st, steps, why = run(room, move, move + [A(kind="wait", wait_until="morning", summary="sleep until morning")])
check("an addition the words ask for still stands (f699)", st == "changed" and [k for k, _ in steps] == ["move", "wait"], (st, steps, why))

look = [A(kind="move", destination="ironvein", summary="go to Ironvein"), A(kind="look")]
st, steps, why = run("I take the wolf hunt.", look, look + [A(kind="accept_quest", item="wolf hunt", summary="take the wolf hunt")])
check("an addition that names the line's own words (a new kind of deed) is still asked back, never dropped", st == "failed", (st, steps, why))
st, steps, why = run("I take the wolf hunt.", look, look + [A(kind="accept_quest", item="wolf hunt"), tell])
check("...and so is a correction holding both such a deed and an invented one", st == "failed", (st, steps, why))
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
