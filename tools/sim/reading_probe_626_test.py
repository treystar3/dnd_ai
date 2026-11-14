"""(f626) The measure of a feat's reading asked alone (docs/design/19 section 14, step 3; tools/reading_eval.py). The tool asks every
line of the ruling corpora whether it is a feat of the body, and which, in four arms (the kind with its size, or the kind with the
thing and no size; each with and without a kind for the body moving only itself), and scores each reading against its case, the
table's answer with it, and the same case read twice. It wires nothing into play.
Run: python tools/sim/reading_probe_626_test.py"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
from engine import body
from llm import backend, gbnf
from tools import reading_eval as RE, ruling_eval

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


# ---- the four arms: what each is asked and what it may write
check("four arms: the size or the thing, each with and without a kind for the body moving itself",
      RE.ARMS == {"size": ("size", False), "size+self": ("size", True), "thing": ("thing", False), "thing+self": ("thing", True)})
S = {arm: RE.shape(*spec).model_json_schema() for arm, spec in RE.ARMS.items()}
kinds = lambda sch: [br["properties"]["kind"]["enum"] for br in sch["anyOf"]]
check("the size arm writes what the table's own grammar writes: none, or a kind from the table with its size",
      S["size"]["anyOf"] == body.schema()["anyOf"] and S["size"]["title"] == "FeatReading", S["size"])
check("...with the kind for the body itself beside none, never with a size", kinds(S["size+self"]) == [["none", RE.OWN], list(body.K)]
      and "size" not in S["size+self"]["anyOf"][0]["properties"], kinds(S["size+self"]))
check("the thing arm has no size to write, and names the thing in a few words",
      all("size" not in br["properties"] for a in ("thing", "thing+self") for br in S[a]["anyOf"])
      and all(S[a]["anyOf"][1]["required"] == ["kind", "thing"] and S[a]["anyOf"][1]["properties"]["thing"].get("maxLength") for a in ("thing", "thing+self"))
      and kinds(S["thing"]) == [["none"], list(body.K)] and kinds(S["thing+self"]) == [["none", RE.OWN], list(body.K)], S["thing"])
G = {arm: gbnf.grammar(s) for arm, s in S.items()}
lit = lambda word: '"\\"' + word + '\\""'
check("every arm's grammar holds each kind of the table and none, the body's own kind only where the arm has it, a size or a thing as its arm",
      all(all(lit(k) in g for k in list(body.K) + ["none"]) for g in G.values()) and all((lit(RE.OWN) in G[a]) == RE.ARMS[a][1] for a in G)
      and all((lit("size") in G[a]) == (RE.ARMS[a][0] == "size") and (lit("thing") in G[a]) == (RE.ARMS[a][0] == "thing") for a in G))
P = {arm: RE.system(*spec) for arm, spec in RE.ARMS.items()}
check("every arm lists the table's kinds, each with what its size measures", all(body.lines() in p for p in P.values()))
check("...and asks for the kind and the size in the words f623's ruling was given for them",
      all("when the attempt is done by the body's own strength or reach, its kind from FEATS. Only what their own body must do: with a lever, "
          "a winch or help, their share. \"none\" for everything else." in p for p in P.values())
      and all(("\nsize: how big it is, as the world plainly is: one number in that kind's unit.\n" in P[a]) == (RE.ARMS[a][0] == "size") for a in P))
check("...the kind for the body itself is offered only where the arm has it", all((f"\n  {RE.OWN}:" in P[a]) == RE.ARMS[a][1] for a in P))
check("...and only the size arms ask for a size, only the thing arms for a thing",
      all(("\nsize:" in P[a]) == (RE.ARMS[a][0] == "size") and ("\nthing:" in P[a]) == (RE.ARMS[a][0] == "thing") for a in P))
check("no arm's words hold a dash", not any(d in p for p in P.values() for d in ("—", "–", " - ")))
corpus = [c for p in RE.CASES for c in ruling_eval.load(p)]
told_own = {m: ruling_eval.stems(RE.own_line(m)) - {RE.OWN} for m in ("size", "thing")}
shared = sorted({(w, c["line"]) for m in told_own for c in corpus for w in told_own[m] & ruling_eval.stems(c["line"])})
talk = "I buy the dock workers a round and ask, as if idly, who has been moving crates at night."
check("the body's own kind is named as a class, with no example of it: the one word its line shares with any corpus line is its own "
      "verb, in a line of talk that the word says nothing of",
      len(corpus) >= 139 and shared == [("mov", talk)] and not any(ch in RE.own_line(m) for m in told_own for ch in "()"), shared[:6])
check("the request is the place and the attempt, nothing else", RE.request("Trading Square", "I lift the trough.")
      == "WHERE: Trading Square\nTHE ATTEMPT: I lift the trough.")
R = lambda arm, **k: RE.shape(*RE.ARMS[arm]).model_validate(k)
def refused(fn):
    try:
        fn()
        return False
    except ValueError:
        return True
check("a reading is held to its arm: a kind the arm does not offer, a feat with no size, or one with no thing, is no reading",
      refused(lambda: R("size", kind=RE.OWN)) and refused(lambda: R("size", kind="wingspan", size=3)) and refused(lambda: R("size", kind="lift"))
      and refused(lambda: R("thing", kind="lift")) and R("size+self", kind=RE.OWN).kind == RE.OWN and R("thing", kind="lift", thing="the trough").thing)

# ---- scoring one reading
feat_case = {"line": "I lift the trough.", "at": "trading_square", "expect": "no", "kind": "feat", "body": 10,
             "feat": [{"kind": "lift", "size": [200, 900]}, {"kind": "carry", "size": [200, 900]}],
             "model": {"sense": "cost", "stakes": {"check": "strength", "hard": "fair"}, "feat": {"kind": "lift", "size": 400}}}
none_case = {"line": "I ask the clerk the way.", "at": "trading_square", "expect": "yes", "kind": "feat", "feat": "none"}
plain = {"line": "I haggle over the price of salt.", "at": "trading_square", "expect": "yes"}
check("a size reading is scored against its case: right, the kind wrong, the size wrong",
      [RE.score(feat_case, R("size", kind="lift", size=400), "size"), RE.score(feat_case, R("size", kind="throw", size=400), "size"),
       RE.score(feat_case, R("size", kind="lift", size=40), "size"), RE.score(feat_case, R("size"), "size")] == ["ok", "kind", "size", "kind"])
check("...a thing reading on its kind alone, any fair kind right", [RE.score(feat_case, R("thing", kind=k, thing="it"), "thing") for k in ("lift", "carry", "throw")]
      == ["ok", "ok", "kind"] and RE.score(none_case, R("thing"), "thing") == "ok" and RE.score(feat_case, R("thing"), "thing") == "kind")
check("...the body's own kind is no feat of the table's: right where the case says none, wrong where it names a feat",
      RE.score(none_case, R("size+self", kind=RE.OWN), "size") == "ok" and RE.score(feat_case, R("size+self", kind=RE.OWN), "size") == "kind"
      and RE.feat(R("size+self", kind=RE.OWN)) == body.Feat() and RE.feat(R("size", kind="lift", size=400)) == body.read("lift", 400))
check("a line whose case says nothing of feats is counted as named a feat or not, never right or wrong",
      [RE.score(plain, R("size", kind="lift", size=150), "size"), RE.score(plain, R("size"), "size"), RE.score(plain, R("size+self", kind=RE.OWN), "size")]
      == ["feat", "none", "none"])

# ---- the tool run whole, on the stub
b = ruling_eval.Bench(save="reading_probe_626")
asked = []
def reader(read):
    """The stub as a model: `read` gives a line's feat, {kind, size}, for an arm with or without the body's own kind."""
    def answer(u, k):
        asked.append(u)
        sch = json.dumps(k["format"])
        got = read(u.split("THE ATTEMPT: ")[1], f'"{RE.OWN}"' in sch)
        if got["kind"] in ("none", RE.OWN):
            return {"kind": got["kind"]}
        return {"kind": got["kind"], **({"thing": "it"} if '"thing"' in sch else {"size": got["size"]})}
    return answer
as_cases = lambda line, own: ({"I lift the trough.": {"kind": "lift", "size": 400}, "I ask the clerk the way.": {"kind": "none"}}
                              .get(line, {"kind": RE.OWN} if own else {"kind": "lift", "size": 150}))
b.stub.a_FeatReading = reader(as_cases)
cases = [dict(c, file="x.yaml") for c in (feat_case, none_case, plain)]
rows = RE.run(b, cases, list(RE.ARMS), passes=2, say=lambda *a: None)
check("every line is asked in every arm, each pass: one row a reading", len(rows) == 3 * 4 * 2 == len(asked)
      and {(r["arm"], r["pass"]) for r in rows} == {(a, p) for a in RE.ARMS for p in (1, 2)}, len(rows))
check("...asked with the place by its name and the line as the player wrote it",
      all(u.startswith("WHERE: ") and "trading_square" not in u and u.split("THE ATTEMPT: ")[1] in {c["line"] for c in cases} for u in asked), asked[:1])
one = lambda rs, arm, line, p=1: next(r for r in rs if (r["arm"], r["line"], r["pass"]) == (arm, line, p))
check("a row says what was read and how it scored, and for a size what the table answers with it beside the case's own reading",
      one(rows, "size", feat_case["line"])["kind"] == "lift" and one(rows, "size", feat_case["line"])["size"] == 400
      and one(rows, "size", feat_case["line"])["score"] == "ok" and one(rows, "size", feat_case["line"])["table"] is True
      and one(rows, "thing", feat_case["line"])["table"] is None and one(rows, "size", plain["line"])["score"] == "feat"
      and one(rows, "size", plain["line"])["table"] is None and one(rows, "thing", feat_case["line"])["thing"] == "it"
      and all(r["seconds"] >= 0 and not r["error"] for r in rows), one(rows, "size", feat_case["line"]))
T = RE.summary(rows)
s1, s2 = T["size"]["passes"][0], T["size+self"]["passes"][0]
check("the summary counts each arm and pass: the kind right of the cases that say, the table's answers, feats named where no case says",
      (s1["labelled"], s1["right"], s1["ok"], s1["kind"], s1["size"], s1["table"], s1["tabled"], s1["table_right"], s1["unlabelled"], s1["feat"],
       s1["own"], s1["failed"]) == (2, 2, 2, 0, 0, 2, 2, 2, 1, 1, 0, 0) and T["thing"]["passes"][1]["right"] == 2
      and T["thing"]["passes"][0]["tabled"] == 0 and T["size"]["moved"] == 0 and T["size"]["twice"] == 3, T["size"])
check("...and the body's own kind where it was read: no feat named, counted apart", (s2["feat"], s2["own"], s2["right"]) == (0, 1, 2), s2)
told = RE.lines(T)
check("the summary is told a line an arm and pass and one for the second reading, the arms compared on the kind",
      len(told) == 4 * 2 + 4 and all(sum(x.startswith(a + ",") for x in told) == 2 for a in RE.ARMS)
      and all("the kind right on 2" in x for x in told if ", pass " in x) and sum("the size too on" in x for x in told) == 4, told[:2])

# ---- a size that is wrong: the kind right, the table's answer another
said = []
b.stub.a_FeatReading = reader(lambda line, own: {"kind": "lift", "size": 40} if line == feat_case["line"] else {"kind": "none"})
small = RE.run(b, cases, ["size"], passes=1, say=said.append)
w = RE.summary(small)["size"]["passes"][0]
check("a size too small for its case is the kind right and the size wrong, and where it lets through what the case's own reading refuses, that is said",
      one(small, "size", feat_case["line"])["score"] == "size" and one(small, "size", feat_case["line"])["table"] is False
      and (w["right"], w["ok"], w["size"], w["table"], w["tabled"], w["table_right"]) == (2, 1, 1, 1, 2, 1)
      and sum("the table answers otherwise" in x for x in said) == 1, (w, said))
b.put(feat_case)
ten = (RE.stands(b, body.read("lift", 400)), RE.stands(b, body.read("lift", 40)), RE.stands(b, body.Feat()))
b.put({**feat_case, "body": 30})
check("...the table's answer is for the case's own body: a weight past a body of 10 is within one of 30",
      ten == (False, True, True) and RE.stands(b, body.read("lift", 400)) is True, ten)

# ---- the same case read twice
turn = [0]
def flips(line, own):
    turn[0] += 1
    return {"kind": "lift", "size": 400} if turn[0] <= 3 else {"kind": "none"}
b.stub.a_FeatReading = reader(flips)
moved = RE.summary(RE.run(b, cases, ["size"], passes=2, say=lambda *a: None))["size"]
check("the cases read as another kind the second time are counted", moved["moved"] == 3 and moved["twice"] == 3, moved)
turn[0] = 0
def wavers(line, own):
    turn[0] += 1
    return {"kind": "none"} if turn[0] <= 3 else {"kind": RE.OWN}
b.stub.a_FeatReading = reader(wavers)
still = RE.summary(RE.run(b, cases, ["size+self"], passes=2, say=lambda *a: None))["size+self"]
check("...none one time and the body's own kind the next is the same reading: no feat either time", still["moved"] == 0 and still["twice"] == 3
      and still["passes"][1]["own"] == 3, still)
b.stub.a_FeatReading = reader(lambda line, own: {"kind": "none"})
same = RE.summary(RE.run(b, [cases[2], cases[2]], ["size"], passes=2, say=lambda *a: None))["size"]
check("...a line a corpus holds twice is two cases, each read twice", same["twice"] == 2 and same["passes"][0]["unlabelled"] == 2, same)
b.stub.a_FeatReading = lambda u, k: {"kind": "wingspan", "size": 3}
lost = RE.run(b, cases[:1], ["size"], passes=2, say=lambda *a: None)
gone = RE.summary(lost)["size"]
check("a reading the model cannot give is a row too: counted, never scored, and not a case read twice",
      len(lost) == 2 and lost[0]["error"] and lost[0]["score"] == "" and gone["passes"][0]["failed"] == 1 and gone["twice"] == 0, lost)
b.clear()
b.close()

# ---- live: only the reading goes to the real model, by its title
got = []
def model(**k):
    got.append((k.get("format") or {}).get("title"))
    return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=json.dumps({"kind": "lift", "size": 250})))
b = ruling_eval.Bench(live=True, source=backend.StandIn(chat=model, name="the model"), save="reading_probe_626", ruled=(RE.TITLE,))
b.stub.a_FeatReading = lambda u, k: {"kind": "none"}
live = RE.run(b, cases[:1], ["size"], passes=1, say=lambda *a: None)
check("live, the reading is the real model's and nothing else is", got == [RE.TITLE] and live[0]["kind"] == "lift" and live[0]["size"] == 250, (got, live))
b.clear()
b.close()
check("the measure of rulings still passes its own two titles on by default",
      ruling_eval.Bench.__init__.__defaults__[-1] == ("Ruling", "ActRuling"), ruling_eval.Bench.__init__.__defaults__)

# ---- the tool as it is run
import yaml
tmp = Path(tempfile.mkdtemp(prefix="reading_probe_626_"))
(tmp / "cases.yaml").write_text(yaml.safe_dump([feat_case, none_case, plain]), encoding="utf-8")
(tmp / "bad.yaml").write_text(yaml.safe_dump([{**plain, "kind": "wingspan"}]), encoding="utf-8")
def tool(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = RE.main(list(argv))
    return code, out.getvalue(), err.getvalue()
simlib.Stub.a_FeatReading = lambda self, u, k: reader(as_cases)(u, k)
try:
    code, out, _ = tool("--cases", str(tmp / "cases.yaml"), "--arms", "size,thing+self", "--passes", "2", "--out", str(tmp / "rows.jsonl"))
finally:
    del simlib.Stub.a_FeatReading
kept = [json.loads(x) for x in (tmp / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
check("run from its command line it reads the files named, in the arms named, and keeps a row a reading",
      code == 0 and len(kept) == 3 * 2 * 2 and {r["arm"] for r in kept} == {"size", "thing+self"} and {r["file"] for r in kept} == {"cases.yaml"}
      and all(set(r) >= {"case", "line", "arm", "pass", "kind", "size", "thing", "score", "table", "seconds", "error"} for r in kept), (code, len(kept)))
check("...lists each feat named where the case says nothing, for a person to read, and tells the summary",
      "size: a feat named where the case says nothing (1):" in out and f"lift         {plain['line']}" in out
      and "thing+self: a feat named" not in out and "size, pass 2: of 2 cases that say, the kind right on 2 (the size too on 2)" in out
      and "thing+self: 0 of 3 cases read as another kind on a later pass" in out, out[-900:])
code_arm, _, err_arm = tool("--arms", "wingspan")
code_file, _, err_file = tool("--cases", str(tmp / "bad.yaml"))
check("...an arm it does not have, or a case file the measure of rulings would refuse, is refused in plain words",
      code_arm == 2 and "REFUSED" in err_arm and code_file == 2 and "REFUSED" in err_file and "wingspan" in err_file, (err_arm, err_file))
check("it reads all four ruling corpora by default", len(RE.CASES) == 4 and len(corpus) >= 139)
check("no call reads a feat in play: the probe wires nothing", body.reading(None, "x", "I lift the trough.") == body.Feat())

shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree("saves/reading_probe_626", ignore_errors=True)
if bad:
    print(f"\n{len(bad)} FAILED: {bad}")
    sys.exit(1)
print("\nall ok")
