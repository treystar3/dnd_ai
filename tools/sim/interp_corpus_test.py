"""(f365) The interpreter's corpus from night runs: one case per distinct typed line with the scene, the plan read and what ran; hires become
the party under the evaluator's own ids; reviewed cases survive a rebuild; the cases run through the evaluator offline."""
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
sys.path.insert(0, "tools")
import interp_corpus
import yaml
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

base = Path("saves/interp_corpus_test"); shutil.rmtree(base, ignore_errors=True)
run = base / "night" / "20261028_0100_warrior_9"; run.mkdir(parents=True)
def row(text, raw, final, present, roles, partner="", last=""):
    return json.dumps({"turn": 1, "handled_by": "interpret", "text": text, "place": "parth", "present": present, "partner": partner, "last_spoken": last,
                       "raw": raw, "final": final, "interpreter": [{"roles": roles}]})
smith = {"patlie": "the soot-stained smith", "hire:0-0": "Lorelin Booth", "hire:0-3": "Jesoen Frost"}
roles = {"patlie": "smith"}
talk = [{"kind": "talk", "target": "patlie", "speech": "I ask about the news.", "summary": "asking"}]
(run / "turns_game.jsonl").write_text("\n".join([
    row("I go over to the smith and ask about the news.", talk + [{"kind": "look", "summary": "looking"}], talk, smith, roles),
    row("I go over to the smith and ask about the news.", talk, talk, smith, roles),                                  # the same line, read the same
    row("I go over to the smith and ask about the news.", [{"kind": "look", "summary": "x"}], [{"kind": "look", "summary": "x"}], smith, roles),   # ...and once another way
    row("I ask the archer with us how she is holding up.", [{"kind": "talk", "target": "hire:0-0", "speech": "How are you?"}], [{"kind": "talk", "target": "hire:0-0", "speech": "How are you?"}], smith, roles, partner="hire:0-0"),
    row("I take the road to Parth.", [{"kind": "move", "destination": "trading_square", "summary": "s"}], [{"kind": "move", "destination": "trading_square", "summary": "s"}], {"hire:0-0": "Lorelin Booth"}, {}),
    json.dumps({"turn": 9, "handled_by": "farewell", "text": "Goodbye.", "final": [], "raw": []}),
]) + "\n", encoding="utf-8")
cases = interp_corpus.build([run])
check("one case per distinct line, the commonest reading kept, the other readings noted", len(cases) == 3
      and next(c for c in cases if c["text"].startswith("I go over")).get("seen") == 3
      and next(c for c in cases if c["text"].startswith("I go over"))["expect"]["kinds"] == ["talk"]
      and next(c for c in cases if c["text"].startswith("I go over")).get("also") == ["look (1)"], cases)
c = next(c for c in cases if c["text"].startswith("I go over"))
check("the plan is the model's reading, what ran is the expectation, the first step's target with it",
      c["plan"][0]["kind"] == "talk" and len(c["plan"]) == 2 and c["expect"] == {"handled_by": "interpret", "kinds": ["talk"], "first": {"kind": "talk", "target": "patlie"}}, c)
check("the scene is the place, who was present with their roles, and the companions as the party",
      c["scene"]["place"] == "parth" and c["scene"]["present"] == [{"id": "patlie", "name": "the soot-stained smith", "role": "smith"}]
      and [p["name"] for p in c["scene"]["party"]] == ["Lorelin Booth", "Jesoen Frost"], c["scene"])
h = next(c for c in cases if "archer" in c["text"])
check("a hire's id becomes the evaluator's own, in the plan, the expectation and the scene", h["plan"][0]["target"] == "h0" and h["expect"]["first"]["target"] == "h0" and h["scene"]["partner"] == "h0", h)
m = next(c for c in cases if c["text"].startswith("I take"))
check("a move expects its destination", m["expect"]["first"] == {"kind": "move", "destination": "trading_square"}, m["expect"])

# a rebuild keeps what was reviewed
reviewed = dict(c, expect={"handled_by": "interpret", "kinds": ["talk"], "first": {"kind": "talk", "target": "patlie"}, "note": "right as accepted"}, reviewed=True)
again = interp_corpus.build([run], [reviewed, {"name": "old_case_000000", "text": "An old line.", "scene": {"place": "parth"}, "plan": [], "expect": {}}])
check("a reviewed case survives a rebuild as it is, and a case from a run no longer present is kept",
      next(x for x in again if x["name"] == c["name"]).get("reviewed") and any(x["name"] == "old_case_000000" for x in again) and len(again) == 4, [x["name"] for x in again])
out = base / "corpus.yaml"
code = interp_corpus.main([str(run), "--out", str(out)])
loaded = yaml.safe_load(out.read_text(encoding="utf-8"))
check("the file is written as YAML the evaluator reads", code == 0 and len(loaded) == 3 and out.read_text(encoding="utf-8").startswith("# (f365)"))
text = interp_corpus.review(loaded)
check("the review lists the lines by kind with how often each was seen", "## talk (2)" in text and "## move (1)" in text and "[  3]" in text, text[:300])

# ---- the cases run through the evaluator, offline
from tools import interp_eval
res = interp_eval.evaluate(loaded, live=False, quiet=True)
check("offline, every case reads right: the plan through the repairs gives what ran", res["right"] == 3, res)
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree("saves/interp_eval", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
