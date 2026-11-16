"""(f675) The budget's word on a call made inside a restartable operation is kept across its attempts, as the call's answer is (found in
the second blind play: docs/play/2026-11-16_blind_play_journal.md, the undone bear hide hand-in). Handing in a contract crashed again and
again: "Drift: hire_chat: the request at this point differs from the one asked". The give ruled on a situation the first attempt (the
budget had room), the ruling was asked outside and charged, and the attempt run again for its answer found no room: the ruling waited,
the next call came where the ruling's had been, and the operation was thrown away as drift. What the budget says inside an operation is
read once, at its first attempt; outside any operation it is read as before.
Run: python tools/sim/budget_kept_675_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
simlib.quiet_console()
from engine import asked, budget

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


def verdict(task="event_judge", chars=4000):
    try:
        budget.allow(task, chars)
        return None
    except budget.BudgetError as e:
        return type(e).__name__


b = budget.open(limit=600)
s = asked._Serving()
asked.begin(s)
first = verdict()
b.spent = 10_000                                        # what was asked outside between the attempts was charged
asked.begin(s)                                          # the operation runs again for its answer
again = verdict()
asked.end()
check("an optional call the first attempt had room for still has it when the operation runs again", first is None and again is None,
      (first, again))
check("outside any operation the budget is read as it is now", verdict() == "Dropped", verdict())

s2 = asked._Serving()
asked.begin(s2)
spent = verdict()
b.spent = 0
asked.begin(s2)
check("a refusal the first attempt met is met again, the same kind, though room came since", spent == "Dropped" and verdict() == "Dropped",
      spent)
asked.end()

b.spent = 10_000
s3 = asked._Serving()
asked.begin(s3)
check("a required call over the floor is refused inside as well", verdict("interpret_action") == "BudgetSpent", verdict("interpret_action"))
asked.end()
budget.close()

# the whole loop, as the executor runs it (scenes/world.py asked_operation): a body that asks the budget, then a call asked outside,
# charged between the attempts, then a call made inside; the attempt run again is served and stands, with no drift
b = budget.open(limit=600)
serve, runs, need = asked._Serving(), [], None
for attempt in range(4):
    asked.begin(serve)
    try:
        room = verdict("dialogue_frame", 3000)
        first = asked.call("npc_conversation", asked.key("npc_conversation", "sys", "what is said", "Reply"), lambda: "an answer")
        then = asked.call("hire_chat", asked.key("hire_chat", "sys", "a companion's word", "Reply"), lambda: "a word")
        runs.append((room, first, then))
        break
    except asked.NeedAnswer as e:
        need = e
    except asked.Drift as e:
        runs.append(("drift", str(e)))
        break
    finally:
        asked.end()
    serve.answers.append((need.key, need.ask(), None))
    b.spent += 400                                       # each answer asked outside is charged: no room is left after the first
check("through the executor's loop an operation asked twice outside stands, the budget's room as its first attempt found it",
      runs == [(None, "an answer", "a word")], runs)
budget.close()

asked.key("t", "s", "the river is low", "X"), asked.key("t", "s", "the river is high", "X")
said = asked.moved(asked.key("t", "s", "the river is low", "X"), asked.key("t", "s", "the river is high", "X"))
check("a drift's note names the lines of the request that moved", "-the river is low" in said and "+the river is high" in said, said)
check("a drift against a computed entry says the order of the asks moved", "order" in asked.moved("allow:event_judge", "0123abcd"),
      asked.moved("allow:event_judge", "0123abcd"))
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
