"""(f627) The reading as two calls of its own, built and not yet called in play (docs/design/19 section 16). Asked alone the model
classifies best when no size is asked, and sizes best when told the thing and the unit (section 15). So engine/body.py reads an
attempt in two steps: the feat (a kind of the table's and the thing it is done to, the `thing+self` arm as it was measured), and,
only when a kind was named, the size of that thing in that kind's unit. tools/reading_eval.py runs them as play would (its arm
`sized`) and says what the table then answers: for the case's own body, and on the lines that say nothing of feats for an
ordinary body too, which is the gate before anything is wired.
Run: python tools/sim/feat_calls_627_test.py"""
import json
import shutil
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
held = simlib.install(stub)
simlib.quiet_console()
import yaml
from pathlib import Path
from engine import asked, body, data_check
from llm import gbnf
from llm.contracts import FeatReading, FeatSize
from tools import reading_eval as RE, ruling_eval

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)
def refused(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


# ---- the first call: the feat, as it was measured
check("the feat is asked in the words and the grammar of the arm that was measured, with the place and the line",
      body.FEAT_SYSTEM == RE.system("thing", True) and body.feat_shape().model_json_schema() == RE.shape("thing", True).model_json_schema()
      and body.feat_request("Trading Square", "I lift the trough.") == RE.request("Trading Square", "I lift the trough.") and body.OWN == RE.OWN)
MEASURED = ("You are the dungeon master of a low-fantasy world of towns, roads and wilds. A player's character attempts something. "
            "Say whether it is a feat of their own body, and which. You do not rule on it: never whether it works.\n"
            "kind: when the attempt is done by the body's own strength or reach, its kind from FEATS. Only what their own body must "
            "do: with a lever, a winch or help, their share. \"none\" for everything else.\n"
            "thing: what it is done to or over, in a few words, as the player named it.\n"
            f"FEATS (a kind: what its size measures):\n{body.lines()}\n"
            "  self: the body moving only itself, where none of those is the measure; it has no thing")
check("...word for word what the pod was asked (docs/design/19 section 15): another wording is another measure", body.FEAT_SYSTEM == MEASURED,
      body.FEAT_SYSTEM)
ctx = body.feat_context()
F = lambda **k: FeatReading.model_validate(k, context=ctx)
check("its contract holds a reading to the table: a kind it does not hold, or a feat with no thing, is no reading",
      refused(lambda: F(kind="wingspan", thing="it")) and refused(lambda: F(kind="lift")) and refused(lambda: F(kind="lift", thing="  "))
      and F(kind=" Lift ", thing=" the trough ").model_dump() == {"kind": "lift", "thing": "the trough"})
check("...and none, or the body's own kind, has no thing", F(kind="none", thing="x").thing == "" and F(kind=body.OWN, thing="x").model_dump()
      == {"kind": body.OWN, "thing": ""} and F().kind == "none")

# ---- the second call: the size of the thing named
asks = body.size_request("Trading Square", "I lift the portcullis with my bare hands.", "lift", "the portcullis")
check("the size is asked of the thing named, with what its kind measures and in its unit",
      asks == ("WHERE: Trading Square\nTHE ATTEMPT: I lift the portcullis with my bare hands.\nTHE THING: the portcullis\n"
               f"MEASURE: {body.K['lift']['about']}, in {body.K['lift']['unit']}"), asks)
check("...for every kind of the table", all(body.K[k]["about"] in body.size_request("x", "y", k, "z") and f", in {body.K[k]['unit']}"
                                           in body.size_request("x", "y", k, "z") for k in body.K))
check("its instruction asks one number, of the thing itself, and the body's share where a tool or other hands help",
      all(w in body.SIZE_SYSTEM for w in ("one number, in the unit asked", "the size of the thing itself", "only their share")), body.SIZE_SYSTEM)
check("...and names the help by its class, with no example of it", "a tool or other hands" in body.SIZE_SYSTEM
      and not any(w in body.SIZE_SYSTEM.lower() for w in ("lever", "winch", "rope", "pulley", "crowbar")), body.SIZE_SYSTEM)
check("neither instruction holds a dash", not any(d in s for s in (body.FEAT_SYSTEM, body.SIZE_SYSTEM) for d in ("—", "–", " - ")))
sz = body.size_shape().model_json_schema()
check("the size is one whole number from 1 to the table's most, and its grammar builds",
      sz["title"] == "FeatSize" and sz["required"] == ["size"] and sz["properties"]["size"] == {"type": "integer", "minimum": 1, "maximum": int(body.B["most"])}
      and '"\\"size\\""' in gbnf.grammar(sz), sz)
check("...and its contract refuses none, and a size past the table's most", refused(lambda: FeatSize.model_validate({"size": 0}))
      and FeatSize.model_validate({"size": 1200}, context=ctx).size == 1200
      and refused(lambda: FeatSize.model_validate({"size": int(body.B["most"]) + 1}, context=ctx))
      and refused(lambda: F(kind="lift", thing="x" * (int(body.B["thing_chars"]) + 1))))

# ---- an attempt read: one call for most, two for a feat
seen = []
def answers(feat, size=None):
    seen.clear()
    stub.a_FeatReading = lambda u, k: seen.append(("feat", u)) or feat
    stub.a_FeatSize = lambda u, k: seen.append(("size", u)) or size
r = None
answers({"kind": "none"})
r = body.attempt("Trading Square", "I haggle over the price of salt.")
check("an attempt that is no feat is read in one call: none", r == body.Read() and r.feat == body.Feat() and [t for t, _ in seen] == ["feat"], (r, seen))
answers({"kind": body.OWN})
r = body.attempt("Trading Square", "I climb the cliff above the cove.")
check("...the body's own kind is said so and is no feat of the table's: no size is asked",
      (r.said, r.feat, r.thing, r.lost) == (body.OWN, body.Feat(), "", "") and [t for t, _ in seen] == ["feat"], (r, seen))
answers({"kind": "lift", "thing": "the portcullis"}, {"size": 1200})
r = body.attempt("Trading Square", "I lift the portcullis with my bare hands.")
check("a feat is read in two: the kind and the thing, then the size of that thing in that kind's unit",
      (r.said, r.thing, r.feat, r.lost) == ("lift", "the portcullis", body.read("lift", 1200), "") and [t for t, _ in seen] == ["feat", "size"]
      and "THE THING: the portcullis" in seen[1][1] and "in pounds" in seen[1][1] and seen[0][1].startswith("WHERE: Trading Square"), (r, seen))
answers({"kind": "wingspan", "thing": "x"})
r = body.attempt("Trading Square", "I lift the portcullis.")
check("a feat the model cannot say is no reading, and says which call was lost", (r.feat, r.lost) == (body.Feat(), "feat") and "size" not in [t for t, _ in seen], r)
answers({"kind": "lift", "thing": "the portcullis"}, {"size": 0})
r = body.attempt("Trading Square", "I lift the portcullis.")
check("...as is a size it cannot say: the kind and the thing are kept, the table is handed none",
      (r.said, r.thing, r.feat, r.lost) == ("lift", "the portcullis", body.Feat(), "size"), r)

# ---- not called in play
answers({"kind": "lift", "thing": "the trough"}, {"size": 900})
check("no call reads a feat in play yet: the reading is none and the model is not asked",
      body.reading(None, "x", "I lift the trough.") == body.Feat() and not seen)
B = yaml.safe_load(Path("data/rules/budget.yaml").read_text(encoding="utf-8"))
check("the two calls are tasks the budget knows, as a tool's until they are played",
      all(B["tasks"].get(t, {}).get("need") == "tool" for t in ("feat_reading", "feat_size"))
      and all(any(w.startswith("engine/body.py:") for w in data_check.task_literals().get(t, [])) for t in ("feat_reading", "feat_size"))
      and not {"feat_reading", "feat_size"} & set(asked.tasks()), {t: B["tasks"].get(t) for t in ("feat_reading", "feat_size")})
held()

# ---- the measure runs them as play would
check("the tool has an arm for the engine's own two calls, beside the four that were tried", RE.ENGINE == "sized" and RE.ENGINE not in RE.ARMS
      and RE.ALL == [*RE.ARMS, RE.ENGINE] and RE.TITLES == ("FeatReading", "FeatSize"))
feat_case = {"line": "I lift the trough.", "at": "trading_square", "expect": "no", "kind": "feat", "body": 10,
             "feat": [{"kind": "lift", "size": [200, 900]}],
             "model": {"sense": "cost", "stakes": {"check": "strength", "hard": "fair"}, "feat": {"kind": "lift", "size": 400}}}
plain = {"line": "I haggle over the price of salt.", "at": "trading_square", "expect": "yes"}
absurd = {"line": "I lift the whole inn off the ground.", "at": "trading_square", "expect": "no"}
cases = [dict(c, file="x.yaml") for c in (feat_case, plain, absurd)]
b = ruling_eval.Bench(save="feat_calls_627")
def model(read):
    b.stub.a_FeatReading = lambda u, k: ({"kind": read(u)[0], "thing": "it"} if read(u)[0] not in ("none", body.OWN) else {"kind": read(u)[0]})
    b.stub.a_FeatSize = lambda u, k: {"size": read(u)[1]}
line_of = lambda u: u.split("THE ATTEMPT: ")[1].split("\n")[0]
model(lambda u: {"I lift the trough.": ("lift", 400), "I haggle over the price of salt.": ("lift", 170)}.get(line_of(u), ("lift", 50000)))
rows = RE.run(b, cases, [RE.ENGINE], passes=1, say=lambda *a: None)
one = lambda rs, line: next(r for r in rs if r["line"] == line)
t = one(rows, feat_case["line"])
check("a row of the engine's arm says the kind, the thing and the size, scored as a size reading is",
      (t["arm"], t["kind"], t["thing"], t["size"], t["score"], t["table"]) == ("sized", "lift", "it", 400, "ok", True) and not t["error"], t)
check("...and what the engine then answers with the case's own ruling: the case's yes or no, or not", t["verdict"] is True
      and one(rows, plain["line"])["verdict"] is None, t)
h = one(rows, plain["line"])
check("a line that says nothing of feats is told as it would go for its own body and for an ordinary one: a lift of 170 pounds stands for "
      "the bench's warrior and is refused a body of 10", (h["score"], h["refused"], h["refused_plain"], h["expect"]) == ("feat", False, True, "yes"), h)
a = one(rows, absurd["line"])
check("...a no the table refuses is no fair act refused", (a["refused"], a["refused_plain"], a["expect"]) == (True, True, "no"), a)
s = RE.summary(rows)["sized"]["passes"][0]
check("the summary counts the engine's yes or no against the cases that say, and the fair acts refused among those that do not, for each body",
      (s["verdict"], s["verdicted"], s["fair_refused"], s["fair_refused_plain"], s["unlabelled"], s["feat"]) == (1, 1, 0, 1, 2, 2), s)
told = "\n".join(RE.lines(RE.summary(rows)))
check("...and says so in plain words", "the engine's yes or no is the case's on 1 of 1" in told
      and "fair acts refused: 0 for the case's own body, 1 for an ordinary body" in told, told)
model(lambda u: ("lift", 40) if line_of(u) == feat_case["line"] else ("none", 0))
low = RE.run(b, cases, [RE.ENGINE], passes=1, say=lambda *a: None)
check("a size too small lets through what the case refuses: the engine's answer is not the case's",
      one(low, feat_case["line"])["score"] == "size" and one(low, feat_case["line"])["verdict"] is False
      and RE.summary(low)["sized"]["passes"][0]["verdict"] == 0, one(low, feat_case["line"]))
b.stub.a_FeatReading = lambda u, k: {"kind": "lift", "thing": "it"}
b.stub.a_FeatSize = lambda u, k: {"size": 0}
lost = RE.run(b, cases[:1], [RE.ENGINE], passes=1, say=lambda *a: None)
check("a reading lost at either call is a row with its error, never scored", lost[0]["error"] and lost[0]["score"] == ""
      and RE.summary(lost)["sized"]["passes"][0]["failed"] == 1, lost)

# ---- the gate (design 19 section 16)
G = RE.GATE
check("the gate is the one the plan states", (G["verdict"], G["fair_refused_plain"], G["refuse"]) == (36, 2, "I lift the portcullis with my bare hands."))
def made(verdicts, plain_refused, portcullis):
    rs = [{"case": i, "file": "f", "line": f"case {i}", "arm": "sized", "pass": 1, "labelled": True, "kind": "lift", "size": 5, "thing": "it",
           "score": "ok", "table": True, "verdict": i < verdicts, "refused": False, "refused_plain": False, "expect": "cost", "seconds": 0.1, "error": ""}
          for i in range(40)]
    rs += [{**rs[0], "case": 40 + i, "labelled": False, "score": "feat", "verdict": None, "table": None, "expect": "yes", "refused_plain": i < plain_refused}
           for i in range(99)]
    rs.append({**rs[0], "case": 200, "line": G["refuse"], "expect": "no", "verdict": portcullis, "refused": portcullis})
    return rs
ok_gate = RE.gate(made(36, 2, True))
check("it is met at 36 of the labelled, two fair acts refused an ordinary body, and the portcullis refused",
      ok_gate[1]["met"] and len(ok_gate) == 1, ok_gate)
check("...and not met a case short, a refusal over, or the portcullis let through",
      not RE.gate(made(34, 2, True))[1]["met"] and not RE.gate(made(40, 3, True))[1]["met"] and not RE.gate(made(40, 0, False))[1]["met"],
      (RE.gate(made(34, 2, True)), RE.gate(made(40, 3, True))))
check("...nor where the portcullis was never read", not RE.gate([r for r in made(40, 0, True) if r["line"] != G["refuse"]])[1]["met"])
lost = RE.gate(made(36, 2, True) + [{**made(0, 0, True)[40], "case": 300, "kind": "", "refused": None, "refused_plain": None, "error": "no feat"}])[1]
check("a lost reading stands as play would have it, and the gate says how many; beside it, the labelled noes the table refuses",
      lost["met"] and lost["lost"] == 1 and ok_gate[1]["lost"] == 0 and (ok_gate[1]["refused_no"], ok_gate[1]["no_cases"]) == (1, 1)
      and RE.gate(made(40, 0, False))[1]["refused_no"] == 0, lost)
b.clear()
b.close()

shutil.rmtree("saves/feat_calls_627", ignore_errors=True)
if bad:
    print(f"\n{len(bad)} FAILED: {bad}")
    sys.exit(1)
print("\nall ok")
