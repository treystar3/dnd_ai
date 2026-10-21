"""The meaning checks: with the helper model, repetition, asking again, gestures, Maren's subjects and a clerk's manner are judged by
meaning; without it, by the simple fallbacks; and a failing helper turns itself off instead of breaking a turn. A stand-in embedder is used:
each word is a direction, so lines that share words point the same way."""
import sys, math, hashlib
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from llm import embed
from engine import banter, mentor, quirks
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

check("without the helper model, nothing is available and the fallbacks answer", not embed.available() and banter.repeats("We should find an inn before dark.", ["That wolf bit deep into my arm."]) == "")
check("...the word routing still finds Maren's subjects", "combat" in mentor.topics_in("how does hit chance work"))

SYN = {"promoted": "rank", "promotion": "rank", "ranks": "rank", "climb": "rank", "high": "rank", "guild": "rank"}
def vec(t):
    v = [0.0] * 64
    for w in t.lower().replace("clustering: ", "").split():
        w = SYN.get(w.strip(".,?!'"), w.strip(".,?!'"))
        if len(w) < 3:
            continue
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
    return v
calls = []
class Fake:
    def embed(self, model, input, keep_alive=None):
        calls.append(len(input))
        return {"embeddings": [vec(t) for t in input]}
import llm.gateway as gw
real = gw._client
gw._client = Fake()
embed._state.update(ok=True, failed=False)
config.SIM_REPEAT, config.SIM_ASKED, config.SIM_GESTURE, config.SIM_TOPIC = 0.9, 0.7, 0.85, 0.3

check("a sentence meaning the same as one said lately is a repeat", banter.repeats("That wolf bit deep into my arm.", ["Well. That wolf bit deep into my arm."]) != "")
check("a different sentence is not", banter.repeats("We should find an inn before dark.", ["That wolf bit deep into my arm."]) == "")
check("asking the same thing in other words is asking again", banter.asked_again("How high up are you in the guild?", ["What rank are you in the guild?"]))
check("a different question is not", not banter.asked_again("Do you have family back home?", ["What rank are you in the guild?"]))
check("the same gesture in other words is refused", quirks.gesture_ok("He leans heavily against the stone wall", ["Bram leans against the stone wall"], "Bram Voss") != "")
check("a new gesture is fine", quirks.gesture_ok("wipes his blade on his sleeve", ["Bram leans against the stone wall"]) == "")
n0 = sum(calls)
banter.repeats("That wolf bit deep into my arm.", ["Well. That wolf bit deep into my arm."])
check("lines already seen are not sent again", sum(calls) == n0)

class Broken:
    def embed(self, **k):
        raise ConnectionError("gone")
gw._client = Broken()
embed._cache.clear()
check("a failing helper falls back to the word checks for the session, without an error", banter.repeats("Keep your hand on your hilt now.", ["Something else."]) == "" and not embed.available())
gw._client = real
embed._state.update(ok=None, failed=False)

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")

import sys as _sys
_sys.exit(1 if bad else 0)
