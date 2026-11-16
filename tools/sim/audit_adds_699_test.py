"""(f699) The audit may add a step the player's own words ask for, never a deed they did not (the owner's choice, 2026-11-16, from the
second blind play: docs/play/2026-11-16_blind_play_journal.md). The audit's correction was refused whenever it had more steps than the
first reading ("only remove or correct steps, never add"), and the player was asked questions about the audit's own disagreement:
"Do you mean to head to the Tilted Plough now, or are you suggesting a different route?" for "I buy a room and we sleep until morning";
"Do you mean to accept the contract, or are you trying to modify the list of targets?" for three hunts taken in one line.
Held here: a longer correction stands when every step it has that the first reading lacks is of a kind the first reading already holds,
or of a kind the action table lets the audit add (a wait: the sleep that was said), and its own words share a word with the line; a
new kind of deed (a gift of coin, an attack, a purchase not in the first reading) or a repeat the line never names is refused as before.
Run: python tools/sim/audit_adds_699_test.py"""
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
        return "what they meant"
    def compare(self, t, m, d, r):
        return False, "the reading left part of the line out"
    def propose(self, t, h):
        return [s.model_copy(deep=True) for s in self.proposal]


sit = ia.Situation(present={"inn1": "the innkeeper", "guard1": "the guard"}, place="the Tilted Plough")


def run(text, plan, proposal):
    real = ia.risk_flags
    ia.risk_flags = lambda *a, **k: real(*a, **k) or ["multi_intent"]      # every case here is audited: the rule under test is reached
    try:
        r = ia.audit(text, plan, sit, Ask(proposal))
    finally:
        ia.risk_flags = real
    return r.status, [s.kind for s in r.plan], r.reason


room = "We go to the Tilted Plough. I buy a room for the night and we sleep until morning."
first = [A(kind="move", destination="tilted_plough", summary="go to the Tilted Plough"), A(kind="buy", ware="room", target="inn1", summary="buy a room")]
st, kinds, why = run(room, first, first + [A(kind="wait", wait_until="morning", summary="sleep until morning")])
check("the sleep the line says, added to a room bought, stands", st == "changed" and kinds == ["move", "buy", "wait"], (st, kinds, why))

hunts = "I take the wolf hunt, the boar hunt and the bear hunt."
two = [A(kind="accept_quest", item="wolf hunt"), A(kind="accept_quest", item="boar hunt")]
st, kinds, why = run(hunts, two, two + [A(kind="accept_quest", item="bear hunt")])
check("the third of a list the line names, added, stands", st == "changed" and kinds == ["accept_quest"] * 3, (st, kinds, why))

st, kinds, why = run(room, first, first + [A(kind="give", item="5 silver", target="guard1", summary="tip the guard")])
check("a new kind of deed the line never asks for (coin to the guard) is refused", st == "failed", (st, kinds, why))
st, kinds, why = run(room, first, first + [A(kind="attack", target="guard1", summary="attack the guard")])
check("...and an attack", st == "failed", (st, kinds, why))
st, kinds, why = run("We go to the Tilted Plough and sleep for eight hours.", first[:1], first[:1] + [A(kind="wait", wait_minutes=480, summary="sleep")])
check("a sleep said with no hour named, added, stands", st == "changed" and kinds == ["move", "wait"], (st, kinds, why))
st, kinds, why = run(room, first, first + [A(kind="buy", ware="ale", target="inn1", summary="buy an ale for the night")])
check("a repeat of a kind already read, that the line never names (an ale), is refused", st == "failed", (st, kinds, why))
st, kinds, why = run("I take the wolf hunt.", [A(kind="move", destination="parth", summary="go to Parth"), A(kind="look")],
                     [A(kind="move", destination="parth", summary="go to Parth"), A(kind="look"), A(kind="accept_quest", item="wolf hunt")])
check("a contract taken where the first reading took none is a new kind: refused", st == "failed", (st, kinds, why))
sit.present["guard2"] = "the gate guard"
st, kinds, why = run(room, first, first + [A(kind="buy", ware="room", target="guard1", summary="buy a room for the guard")])
check("a second buy on a word the first already claims ('room') is refused", st == "failed", (st, kinds, why))
pay = "I pay the innkeeper 5 silver for a room."
gave = [A(kind="give", item="5 silver", target="inn1", summary="pay the innkeeper")]
st, kinds, why = run(pay, gave, gave + [A(kind="give", item="5 silver", target="guard1", summary="pay the guard")])
check("...and a second payment of the same silver to someone else", st == "failed", (st, kinds, why))
hit = [A(kind="attack", target="guard1", summary="attack the guard")]
st, kinds, why = run("I attack the guard.", hit, hit + [A(kind="attack", target="guard2", summary="attack the gate guard")])
check("...and an attack on a second target who only shares a word ('guard')", st == "failed", (st, kinds, why))
rest = [A(kind="wait", wait_minutes=480, summary="rest")]
st, kinds, why = run("I rest until morning.", rest, rest + [A(kind="wait", wait_until="morning", summary="sleep until morning")])
check("...and a second wait: the night is slept once", st == "failed", (st, kinds, why))
st, kinds, why = run("I ask the innkeeper about rooms and sleep until morning.", [A(kind="talk", target="guard1", speech="any rooms?")],
                     [A(kind="talk", target="inn1", speech="any rooms?"), A(kind="wait", wait_until="morning", summary="sleep")])
check("a corrected step is a correction, not an addition: the talk set right and the sleep added stand",
      st == "changed" and kinds == ["talk", "wait"], (st, kinds, why))
st, kinds, why = run("Second Wind, then I wait for the patrol.", [A(kind="talk", target="hire:0-0", speech="Second Wind, then I wait for the patrol.")],
                     [A(kind="ability", ability="second_wind"), A(kind="wait", wait_minutes=60, summary="wait for the patrol")])
check("a step set right as another kind is a correction, and the wait the line asks for, added, stands",
      st == "changed" and kinds == ["ability", "wait"], (st, kinds, why))
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
