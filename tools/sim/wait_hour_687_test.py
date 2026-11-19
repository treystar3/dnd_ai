"""(f687) A wait until a clock hour waits until that hour (found in the second blind play: docs/play/2026-11-16_blind_play_journal.md).
`We wait here until eight in the morning.` at 5:37 stopped at 6:00, the start of "dawn": the reading only knew the times of day, and
the clerk the player waited for keeps 8 to 18.
Held here: an hour named in words or figures, with or without am/pm, "in the morning" or "at night", noon and midnight, is read to
its hour; a bare hour is the nearer of its two; the wait lasts until it; a line naming no hour waits as it did.
Run: python tools/sim/wait_hour_687_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from engine import clock
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


for text, want in (("We wait here until eight in the morning.", (8, False)), ("I wait till 3 pm.", (15, False)),
                   ("wait until 10 at night", (22, False)), ("We rest until noon", (12, False)), ("until midnight", (0, False)),
                   ("We wait until seven o'clock.", (7, True)), ("I wait an hour.", None), ("We wait until dawn.", None),
                   ("We wait until one of the guards leaves.", None), ("I wait till ten minutes pass.", None),
                   ("wait until 3 hours have passed", None), ("rest until eleventh bell", None), ("until twelve at night", (0, False)),
                   ("We wait until 8:00.", (8, True)), ("till 9 am", (9, False))):
    check(f"'{text}' is read as {want}", clock.hour_named(text) == want, clock.hour_named(text))

g = simlib.campaign("wait_hour_687", seed=3, location="trading_square")
ws = g.scene
ws.store.meta.minutes += (5 * 60 + 37 - clock.absolute(ws.store.meta.minutes) % 1440) % 1440
check("(it is 5:37)", clock.clock_time(ws.minutes).startswith("5:37"), clock.clock_time(ws.minutes))
ws.on_wait(A(kind="wait", wait_until="dawn"), "We wait here until eight in the morning.")
check("a wait until eight in the morning lasts until eight, not dawn", clock.hour(ws.minutes) == 8.0, clock.clock_time(ws.minutes))
ws.store.meta.minutes += (21 * 60 - clock.absolute(ws.store.meta.minutes) % 1440) % 1440
ws.on_wait(A(kind="wait", wait_until="morning"), "We wait until seven.")
check("a bare hour at night is the nearer seven, in the morning", clock.hour(ws.minutes) == 7.0, clock.clock_time(ws.minutes))
before = ws.minutes
ws.on_wait(A(kind="wait", wait_minutes=60), "I wait an hour.")
check("a line naming no hour waits as it did", ws.minutes - before == 60, ws.minutes - before)
import shutil; shutil.rmtree("saves/wait_hour_687", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
