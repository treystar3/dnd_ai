"""(f727) The voice in every line; the engine decides when grammar slips (docs/design/28_phase4_plan.md A5; the owner's decision
of 17 November, the change to f410). Someone whose first tongue is not Common has that tongue's manner in every reply (their
words, their rhythm), and the engine rolls, reply by reply and on a die of its own, whether one slip of grammar shows: one
reply in two for a learner, one in six for one whose Common is good (data/rules/speech.yaml slip). The model is told which in
plain words either way. Before, one line told it the whole of the tongue's habits "in every line", and a model given that
either broke the grammar of every sentence or of none. For townsfolk and companions alike.
Run: python tools/sim/voice_slip_727_test.py"""
import copy
import random
import re
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
from engine import data_check, quirks, streams, voice_profile as vp

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


if not hasattr(vp, "slip") or not hasattr(vp, "manner"):
    check("the voice line and the slip are built (engine/voice_profile.py manner, slip)", False)
    sys.exit(1)
S = vp.S
TONGUES = {**quirks.Q["tongues"], **S["tongues"]}

# ---- the data: each tongue's manner (always) apart from its slips of grammar (rolled); the odds and the two lines
check("every tongue has a manner, and its slips of grammar apart from it as a list (none is allowed); none keeps the old habits",
      all(isinstance(t.get("manner"), str) and t["manner"].strip() and isinstance(t.get("slips"), list) and "habits" not in t for t in TONGUES.values()),
      {k: sorted(t) for k, t in TONGUES.items()})
check("...all behaviour, with no quoted words to copy", not [x for t in TONGUES.values() for x in [t["manner"], *t["slips"]] if re.search(r"['\"]\w", x)])
L = S["slip"]
check("the odds are data, by how well they speak Common: a learner slips at least as often as one whose Common is good; the lines for a slip and for none are data too",
      set(L["one_in"]) == {"learner", "fluent"} and 1 <= L["one_in"]["learner"] <= L["one_in"]["fluent"] and "{slip}" in L["shown"] and L["clean"].strip()
      and data_check.check() == [], (L, data_check.check()[:3]))
wrong_t, wrong_s = copy.deepcopy(TONGUES), copy.deepcopy(S["slip"])
wrong_s["one_in"]["learner"] = 0
wrong_s["shown"] = "Their grammar slips."
wrong_t["ironvein"]["habits"] = wrong_t["ironvein"].pop("manner")
wrong_t["rime"]["slips"] = "a small word left out"
wrong_t["salt"]["slips"] = ["says 'the boat' for everything"]
found = data_check.voice_problems(wrong_t, wrong_s)
check("odds under one, a slip's line with no place for the slip, a tongue with habits and no manner, slips that are no list or hold words to copy: each is refused",
      all(any(w in p for p in found) for w in ("slip.one_in", "slip.shown", "'ironvein': manner", "'rime': slips", "'salt': slips")) and data_check.voice_problems() == [], found)
real_voice = data_check.voice_problems
data_check.voice_problems = lambda *a, **k: ["voice: planted"]
try:
    at_start = data_check.check()
finally:
    data_check.voice_problems = real_voice
check("...and the check the game runs at startup runs this one, on the data's own tongues", at_start == ["voice: planted"], at_start[:3])


def speaker(culture="ironvein", fluency="learner", said=0, **more):
    return {"id": "h1", "name": "Brokur Durdal", "people": "dwarf", "said": [f"line {i}" for i in range(said)],
            "speech": {"people": "dwarf", "culture": culture, "fluency": fluency, "strength": "light", **more}}


# ---- the voice line: in every reply, the same, and none of the grammar
iron = TONGUES["ironvein"]
m = vp.manner(speaker())
check("a learner's voice is in every line and the same each time: the manner of their tongue",
      "in every line" in m and iron["manner"] in m and m == vp.manner(speaker(said=7)), m)
check("...and no slip of grammar is part of it (that is rolled, never 'in every line')", not any(s in m for s in iron["slips"]) and "verb" not in m, m)
check("one whose Common is good has a lighter touch of the same manner; one raised on Common, or with no tongue but Common, has no such line",
      "good" in vp.manner(speaker(fluency="fluent")) and iron["manner"] in vp.manner(speaker(fluency="fluent"))
      and vp.manner(speaker(fluency="native")) == "" and vp.manner(speaker(culture="heartland")) == "", vp.manner(speaker(fluency="fluent")))
check("the older voice prompt for a second tongue is given the manner, never the slips", iron["manner"] in quirks.tongue_prompt(speaker())
      and not any(s in quirks.tongue_prompt(speaker()) for s in iron["slips"]), quirks.tongue_prompt(speaker()))

# ---- the slip: the engine's roll, told in plain words either way
N = 1200


def rate(who):
    lines = [vp.slip(who, random.Random(k)) for k in range(N)]
    shown = [l for l in lines if "slips once" in l]            # the two lines' own words (speech.yaml slip)
    clean = [l for l in lines if "is clean" in l]
    return len(shown) / N, shown, clean, lines


r_l, shown, clean, lines = rate(speaker())
r_f, shown_f, clean_f, _ = rate(speaker(fluency="fluent"))
check("every reply of theirs is told one of two things: the grammar slips once, or it is clean", len(shown) + len(clean) == N and shown and clean, lines[:3])
check("a learner's slips in about one reply in `learner`, a good speaker's in about one in `fluent`",
      abs(r_l - 1 / L["one_in"]["learner"]) < 0.05 and abs(r_f - 1 / L["one_in"]["fluent"]) < 0.04, (r_l, r_f))
check("a slip is one habit of their own tongue's grammar, once, in one sentence; a clean reply says so and leaves the voice to words and rhythm",
      all(any(s in l for s in iron["slips"]) and "one sentence" in l and "correct" in l for l in shown)
      and all("correct" in l and "words and rhythm" in l for l in clean), (shown[:1], clean[:1]))
check("a tongue with more than one slip shows one of them at a time, and each turns up", len(iron["slips"]) >= 2
      and all(sum(s in l for s in iron["slips"]) == 1 for l in shown) and all(any(s in l for l in shown) for s in iron["slips"]), iron["slips"])
none = next(k for k, t in TONGUES.items() if not t["slips"])
quiet = speaker(culture=next(c for c, s in S["cultures"].items() if s.get("tongue") == none))
dice = random.Random(5)
before = dice.getstate()
check("a tongue with no slip of grammar to show has none rolled and nothing said of grammar; nor has one raised on Common",
      vp.slip(quiet, dice) == "" and dice.getstate() == before and vp.manner(quiet) and vp.slip(speaker(fluency="native")) == ""
      and vp.slip(speaker(culture="heartland")) == "", (none, vp.slip(quiet, dice)))

# ---- a die of its own: no other roll moves, the same input rolls the same, and it moves on with what they have said
streams.begin(4, 1, "hello")
scene = streams.get("scene").getstate()
a, b = vp.slip(speaker(said=3)), vp.slip(speaker(said=3))
many = {vp.slip(speaker(said=k)) for k in range(40)}
check("with no die given the slip is rolled on its own: the scene's dice do not move, the same reply rolls the same, and replies differ as the talk goes on",
      streams.get("scene").getstate() == scene and a == b and {("slips once" in x) for x in many} == {True, False}, (a, many))
snap = streams.snapshot()
first = [vp.slip(speaker(said=k)) for k in range(12)]
streams.restore(snap)
check("...and an operation run again from its start (the dice put back) rolls each reply's the same", [vp.slip(speaker(said=k)) for k in range(12)] == first, first[:2])

# ---- a townsperson's reply: the kit, the voice line, this reply's line on grammar, then the rest as before
npc = types.SimpleNamespace(id="n1", name="Hesk Varley", people="dwarf", role="smith", gender="female", speech={}, said=[], heard=[], regard={}, concern="the forge",
                            motive="", activity="at the anvil")
vp.ensure_npc(npc, random.Random(1), "grey_mountains")
npc.speech.update(culture="ironvein", fluency="learner")
seen = []
for k in range(60):
    npc.said = [f"line {i}" for i in range(k)]
    fact, lines, material = vp.resident_lines(npc, random.Random(k), char_id="player")
    seen.append(lines)
grammar = [[l for l in ls if l.startswith("In this reply")] for ls in seen]
check("a townsperson with a tongue of their own is told their manner in every reply and exactly one line on grammar, slipped in some replies and clean in others",
      all(any("in every line" in l for l in ls) for ls in seen) and all(len(g) == 1 for g in grammar)
      and {("slips once" in g[0]) for g in grammar} == {True, False}, grammar[:2])
check("...about them, in their own pronoun", all(l.startswith("In this reply her Common") for g in grammar for l in g) and any("Her Common" in l for l in seen[0]), seen[0])
npc.speech.update(culture="heartland", fluency="native")
plain = vp.resident_lines(npc, random.Random(2), char_id="player")[1]
check("one raised on Common is told nothing of either", not any("In this reply" in l or "Common" in l for l in plain), plain)

# ---- a companion's reply
game = simlib.campaign("voice_slip_727", minutes=600, location="guild_house")
ws = game.scene
ws.enter(ws.player.location)
hire = {"id": "h_727", "name": "Brokur Durdal", "role": "fighter", "people": "dwarf", "blurb": "a broad smith turned sellsword", "temper": ["blunt", "dry"],
        "quirks": {"voice": "plain"}, "said": [], "level": 3, "bond": 0,
        "speech": vp.roll(random.Random(3), "dwarf", "ironvein", "learner")}
got = []
for k in range(40):
    hire["said"] = [f"line {i}" for i in range(k)]
    how, _ = ws.companion_parts(hire, "how is the road?")
    got.append(how)
check("a companion with a tongue of their own has the manner in every reply and one line on grammar, slipped in some and clean in others",
      all("in every line" in h and iron["manner"] in h for h in got) and all(len(re.findall(r"In this reply \w+ Common", h)) == 1 for h in got)
      and {("slips once" in h) for h in got} == {True, False}, got[0])
whole, _ = ws.companion_parts(hire)
check("...and where everything about them is given at once (no reply being made), the manner is there and no roll on grammar",
      iron["manner"] in whole and "In this reply" not in whole, whole)

# ---- a townsperson's parting line is a reply of theirs too
from engine import partings
one = sorted(ws.present, key=lambda n: n.id)[0]
vp.ensure_npc(one, random.Random(1), "grey_mountains")
one.speech.update(culture="ironvein", fluency="learner")
one.speech.pop("own_voice", None)
bye = str(partings.request(ws, one, "Farewell, then."))
check("a parting line is told the manner and this reply's line too", iron["manner"] in bye and len(re.findall(r"In this reply \w+ Common", bye)) == 1, bye[-700:])
game.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
