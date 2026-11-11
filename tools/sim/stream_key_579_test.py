"""(f579) The dice key, pinned as text. Every input's dice start from "<seed>:<count of inputs>:<the line typed>", each named stream from
that key and its name, the global module from the key and "global"; a keyed die from the key, its purpose, speaker, conversation and
count; a fixed die from its parts alone. The kept recordings hold this only by replaying: nothing named the strings, so a reshaped key
that happened to replay would pass. The foundations bundle moves the streams behind an object (and multiplayer M1 puts the character's
id in the key, on purpose, with a re-record): this is the line that move must keep, and the one M1 edits.
Run: python tools/sim/stream_key_579_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import streams

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def same(r, seed, n=5):
    """The die draws what a fresh one seeded with this text draws."""
    want = random.Random(seed)
    return [r.random() for _ in range(n)] == [want.random() for _ in range(n)]

streams.reset()
check("before any input the key is 'unseeded'", streams.key() == "unseeded" and streams.UNSEEDED == "unseeded", streams.key())
check("...and a stream made then starts from 'unseeded:<its name>'", same(streams.get("pin579_early"), "unseeded:pin579_early"))

held = streams.get("pin579_held")                       # a reference held across inputs, as the scene's and the fight's are
streams.begin(7, 3, "look")
check("an input's key is '<seed>:<count of inputs>:<the line typed>'", streams.key() == "7:3:look", streams.key())
check("each stream is seeded '<key>:<its name>'", same(streams.get("pin579_a"), "7:3:look:pin579_a"))
check("a stream held from before the input is the same object, reseeded with it", streams.get("pin579_held") is held
      and same(held, "7:3:look:pin579_held"))
streams.begin(7, 3, "look")
check("the global random module is seeded '<key>:global'", same(random, "7:3:look:global"))
streams.begin(7, 3, "look")
want = random.Random("7:3:look:ids")
check("an id is hex digits drawn from the 'ids' stream", streams.new_id() == format(want.getrandbits(32), "08x")
      and streams.new_id(12) == format(want.getrandbits(48), "012x"))
want = random.Random("7:3:look:ops")
check("...or from a stream of the caller's naming, moving no other", streams.new_id(12, "ops") == format(want.getrandbits(48), "012x")
      and same(streams.get("pin579_a"), "7:3:look:pin579_a"))

check("a keyed die is seeded '<key>:keyed:<purpose>:<speaker>:<conversation>:<count>'",
      same(streams.keyed("brief", "n1", "c2", 4), "7:3:look:keyed:brief:n1:c2:4") and same(streams.keyed("pick"), "7:3:look:keyed:pick:::0"))
before = streams.get("pin579_a").getstate()
streams.keyed("brief", "n1").random()
check("...and drawing it moves no stream", streams.get("pin579_a").getstate() == before)
check("a fixed die is seeded by its parts joined with ':'", same(streams.fixed("roster", 12, "hall"), "roster:12:hall"))
streams.begin(8, 9, "another line")
check("...whatever the input", same(streams.fixed("roster", 12, "hall"), "roster:12:hall"))
streams.begin(7, 3, "look")

streams.begin("7", 3, "look")
check("a seed given as text makes the same key as the number", streams.key() == "7:3:look" and same(streams.get("pin579_a"), "7:3:look:pin579_a"))
streams.begin(7, 4, "look")
check("the next input, however alike, has another key", streams.key() == "7:4:look" and same(held, "7:4:look:pin579_held"))
streams.begin(7, 4, "")
check("a line of nothing still has its key", streams.key() == "7:4:")

streams.begin(7, 5, "wait")
snap = streams.snapshot()
first = [held.random(), random.random(), streams.new_id()]
streams.restore(snap)
check("a snapshot put back meets the same dice, the global module's with them", [held.random(), random.random(), streams.new_id()] == first)
streams.begin(7, 6, "wait")
try:
    streams.restore(snap)
    refused = False
except RuntimeError:
    refused = True
check("...and is refused once the streams have been reseeded", refused)

streams.reset()
check("a campaign closed puts the key back to 'unseeded', every stream with it", streams.key() == "unseeded"
      and same(held, "unseeded:pin579_held") and same(random, "unseeded:global"))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
