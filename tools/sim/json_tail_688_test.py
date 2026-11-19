"""(f688) A field's closing quote left at the end of a passage is cut on the way to the screen (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md: a passage ended 'its paint peeling in streaks down towards the doorframe.",').
Held here: a passage ending in a quote, or a quote and a comma, that no opening quote answers is cut back to its last word; a
passage ending in someone's quoted words, its quotes even, is left as it is.
Run: python tools/sim/json_tail_688_test.py"""
import sys
sys.path.insert(0, ".")
from engine import hygiene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


cases = [
    ("The Tilted Plough sits ahead. A crooked plough hangs above the entrance, its paint peeling down towards the doorframe.\",",
     "The Tilted Plough sits ahead. A crooked plough hangs above the entrance, its paint peeling down towards the doorframe."),
    ("Rain falls on the square.\"", "Rain falls on the square."),
    ("Emlily looks up. \"It is done.\"", "Emlily looks up. \"It is done.\""),
    ("The sign reads \"Closed\", and nobody answers.", "The sign reads \"Closed\", and nobody answers."),
    ("Pae turns. “Wait for me.\"", "Pae turns. “Wait for me.\""),
]
for text, want in cases:
    got = hygiene.clean(text)
    check(f"{text[-40:]!r} is shown as {want[-40:]!r}", got == want, got)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
