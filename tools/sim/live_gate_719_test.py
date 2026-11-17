"""(f719) The live gate (tools/live_gate.py): the reading corpus and a played script of typed lines, measured in one command and held
against the owner's floors (data/replay/gate.yaml). Here with the stand-in model, which measures nothing real: what is held is that
the counts are counted, the script's lines are the ones played, each measure is worked out as it says, a floor not set is not held
and one set is, and a run that is not the whole gate on the real model writes nothing into data/measured or docs/measure."""
import json, shutil, sys, tempfile
from pathlib import Path
from typing import ClassVar
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 19))
import yaml
from pydantic import BaseModel
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

try:
    import live_gate
except ImportError as e:
    check("tools/live_gate.py is there", False, e)
    print("\nFAILED: " + ", ".join(bad))
    sys.exit(1)

# ---- the gateway counts what the gate reads
class Said(BaseModel):
    REPLY: ClassVar[bool] = True
    reply: str

    def spoken(self):
        return [("", self.reply)]


check("the gateway keeps the four counts", set(getattr(gateway, "CHECKED", {})) == {"told", "phantom", "spoken", "stiff"}, getattr(gateway, "CHECKED", None))
from engine import hygiene
stiff = next(iter(hygiene.H["speech"]["uncontracted"]))
answers = iter([json.dumps({"reply": f"Well, {stiff} what you asked of me, and {stiff} all there is to say on it, friend."}),
                json.dumps({"reply": "It's done, and that's all there is to it."}), json.dumps({"reply": "Aye, I'll come."})])
class Resp:
    def __init__(self, text):
        self.message = type("M", (), {"content": text})()
        self.done_reason = "stop"


held_stub = simlib.stand_in(chat=lambda **k: Resp(next(answers)), embed=None, name="gate_719")
before = dict(gateway.CHECKED)
try:
    from engine import budget
    budget.open()
    first = gateway.generate("hire_chat", "You speak as a companion.", "PLAYER SAID: is it done?", Said, retries=2, validation_context={})
    second = gateway.generate("hire_chat", "You speak as a companion.", "PLAYER SAID: will you come?", Said, retries=2, validation_context={})
finally:
    held_stub()
moved = {k: gateway.CHECKED[k] - before[k] for k in before}
check("two spoken replies answered are two counted, and the one sent back as stiff is one", moved == {"told": 0, "phantom": 0, "spoken": 2, "stiff": 1}, moved)
check("...the stiff one came back easy", "It's done" in first.reply and second.reply == "Aye, I'll come.", (first.reply, second.reply))
class Passage(BaseModel):
    text: str


from engine import phantoms
phantoms.use(lambda: ["awakened_tree", "wolf", "bat"])
REQ = "GAME STATE\nPLACE: the Greywood\nGAME EVENT: The player searches and finds fresh signs of wolf.\nRECENT NARRATION:\n  - the trees"
answers = iter([json.dumps({"text": "Among the trunks a bat drops from a bough and is gone."}), json.dumps({"text": "The wolf's prints are fresh in the mud."}),
                json.dumps({"text": "The wolf's prints lead on north."})])
held_stub = simlib.stand_in(chat=lambda **k: Resp(next(answers)), embed=None, name="gate_719")
before = dict(gateway.CHECKED)
try:
    gateway.generate("narrate", "You are the narrator.", REQ, Passage, retries=2)
    gateway.generate("narrate", "You are the narrator.", REQ, Passage, retries=2)
finally:
    held_stub()
    phantoms.use(lambda: [])
moved = {k: gateway.CHECKED[k] - before[k] for k in before}
check("two passages answered are two counted, and the one sent back for a creature not there is one", moved == {"told": 2, "phantom": 1, "spoken": 0, "stiff": 0}, moved)
from engine import owned
answers = iter([json.dumps({"reply": f"Well, {stiff} what you asked of me, and {stiff} all there is to say on it, friend."})] + ["not an answer at all"] * 12)
held_stub = simlib.stand_in(chat=lambda **k: Resp(next(answers)), embed=None, name="gate_719")
before = dict(gateway.CHECKED)
lost = False
try:
    budget.open()
    gateway.generate("hire_chat", "You speak as a companion.", "PLAYER SAID: is it done?", Said, retries=2, validation_context={})
except Exception:
    lost = True
finally:
    held_stub()
moved = {k: gateway.CHECKED[k] - before[k] for k in before}
check("a reply sent back as stiff whose call then fails is still counted, once", lost and moved == {"told": 0, "phantom": 0, "spoken": 1, "stiff": 1}, (lost, moved))
from engine import owned
check("the counts are declared the process's, with the other tallies", "llm.gateway.CHECKED" in owned.STATE)

# ---- each measure, on rows made by hand
rows = [{"kind": "talk", "seconds": 10, "stand_ins": [], "where": "Parth",
         "told": ["The square is loud. A man called Quillon waves at Osric Vane from the well, and Parth goes on about its day.",
                  "She says, \"Come here.\" Then Pae nods.  Later the Wend bridge is behind you. (Maybe not.) Yes... \"Where now?\" asks Ilse, and Dornwick answers.\n\nRain comes in."]},
        {"kind": "talk", "seconds": 20, "stand_ins": []}, {"kind": "walk", "seconds": 30, "stand_ins": ["passage"]},
        {"kind": "walk", "seconds": 70, "combat": True, "stand_ins": []}, {"kind": "steps", "seconds": 61, "stand_ins": [], "hesitated": True}]
t = live_gate.timing(rows, 60)
check("time is by the turn's shape, a line inside a fight filed as the fight's", set(t["by_shape"]) == {"talk", "walk", "steps", "fight"} and t["by_shape"]["talk"] == {"n": 2, "median": 15.0, "p95": 20.0}, t["by_shape"])
check("...with the lines over the limit, the stand-ins shown and the lines the model failed", (t["over_limit"], t["stand_ins"], t["model_failed"], t["inputs"]) == (2, 1, 1, 5), t)
info = {"character": "Ilse Marr", "cast": {"Osric Vane": {}}, "party": [{"name": "Pae"}], "checked": {"told": 4, "phantom": 1, "spoken": 10, "stiff": 3}, "reason": "turn limit (5)"}
game = live_gate.game_names()
check("the game's own names are known from its data: a town, a landmark's word", {"parth", "wend", "greywood"} <= game and "quillon" not in game and "dornwick" not in game)
told = [x for r in rows for x in r.get("told") or []]
strange = live_gate.unknown_names(told, live_gate.known_names(info, rows, game))
check("a name the game does not hold is counted; a person's, a place's, a landmark's, and a word that opens a sentence, a quotation or a line are not",
      strange == ["Quillon", "Dornwick"], strange)
read = {"cases": 10, "right": 9, "share": 0.9, "by_kind": {"talk": {"right": 9, "of": 10}}, "model_failed": 0, "repairs": 2, "wrong": ["x"]}
m = live_gate.measures(read, rows, info, 60, game)
check("the measures are worked out as they say: a passage is one telling, whatever blank lines it holds",
      m["inventions"]["phantoms_per_100"] == 25.0 and m["inventions"]["passages_shown"] == 2 and m["inventions"]["unknown_names_per_100"] == 100.0
      and m["speech"]["stiff_sent_back_share"] == 0.3 and m["time"]["over_limit"] == 2, (m["inventions"], m["speech"]))
empty = {"cases": 0, "right": 0, "share": None, "by_kind": {}, "model_failed": 0, "repairs": 0, "wrong": []}
none = live_gate.measures(empty, [], {"checked": {}}, 60, game)
check("...and a measure with nothing under it is not a nought", none["speech"]["stiff_sent_back_share"] is None and none["inventions"]["phantoms_per_100"] is None
      and none["time"]["p95_seconds"] is None and none["reading"]["share"] is None)

# ---- the floors
F = live_gate.floors()
check("data/replay/gate.yaml loads and passes its check, no floor set yet", live_gate.floors_problems(F) == [] and all(v is None for v in F["floors"].values()), live_gate.floors_problems(F))
check("...a floor nobody knows fails the check, as do one that is no number and a share over 1",
      live_gate.floors_problems({"floors": {**F["floors"], "other": 1}, "quick": F["quick"]}) and live_gate.floors_problems({"floors": {**F["floors"], "over_limit": "few"}, "quick": F["quick"]})
      and live_gate.floors_problems({"floors": {**F["floors"], "reading_share": 90}, "quick": F["quick"]}))
check("a floor not set is not held", live_gate.held(m, F) == [])
set_ = {"floors": {**F["floors"], "reading_share": 0.95, "over_limit": 0, "stiff_sent_back_share": 0.5}, "quick": F["quick"]}
under = live_gate.held(m, set_)
check("a set floor the measures miss is named, and one they meet is not", len(under) == 2 and any("reading_share" in u for u in under) and any("over_limit" in u for u in under), under)
check("...and a set floor with nothing measured under it is missed, not passed", any("stiff_sent_back_share: not measured" in u for u in live_gate.held(none, set_)), live_gate.held(none, set_))
text = live_gate.report(m, under, set_, {"date": "2026-11-17", "model": "a-model", "mode": "the whole gate"})
check("the report says what is under a floor, and holds no dash", "Under a floor" in text and "0.95" in text and chr(0x2014) not in text and chr(0x2013) not in text)
from engine import data_check
src = Path(data_check.__file__).read_text(encoding="utf-8")
check("the game's startup check holds the floors' file", "gate_problems()" in src and data_check.check() == [], data_check.check()[:3])
check("...and a measured file of another shape is a problem named, not a fault", any("live_gate.yaml" in x for x in data_check.gate_problems(F, measured=["a list"]))
      and any("live_gate.yaml" in x for x in data_check.gate_problems(F, measured={"reading": {}})) and not data_check.gate_problems(F, measured=m))

cases = [{"name": f"{k}{i}", "expect": {"kinds": [k]}} for k, n in (("talk", 9), ("move", 3), ("look", 1)) for i in range(n)]
picked = live_gate.pick_cases(cases, 6, lambda c: c["expect"]["kinds"][0])
check("a quick run's cases are drawn evenly by kind, the same every time", sorted(c["name"] for c in picked) == ["look0", "move0", "move1", "move2", "talk0", "talk1"]
      and picked == live_gate.pick_cases(cases, 6, lambda c: c["expect"]["kinds"][0]), [c["name"] for c in picked])

# ---- what is the whole gate, and what is kept of it
import argparse
whole = argparse.Namespace(stub=False, quick=False, cases=0, lines=0, no_reading=False, script=str(live_gate.SCRIPT))
check("a run with no cut, on the gate's own script, is the whole gate", live_gate.partial(whole, read) == [])
for cut in ({"stub": True}, {"quick": True}, {"cases": 12}, {"lines": 3}, {"no_reading": True}, {"script": "another.yaml"}):
    check(f"...and not with {next(iter(cut))}", len(live_gate.partial(argparse.Namespace(**{**vars(whole), **cut}), read)) == 1)
check("...nor when the model failed most of the reading", live_gate.partial(whole, {**read, "model_failed": 6}) != [])
check("a script played to its last line did not end early", live_gate.ended_early(5, 0, rows, info) == "" and live_gate.ended_early(40, 5, rows, info) == "")
check("...one the server ended did, and one cut short of its lines", "the model server failed" in live_gate.ended_early(5, 0, rows, {**info, "reason": "the model server failed"})
      and "5 of 40" in live_gate.ended_early(40, 0, rows, info))

tmp = Path(tempfile.mkdtemp(prefix="live_gate_719_"))
live_gate.keep(text, m, under, {"date": "2026-11-17", "model": "a-model"}, measured=tmp / "live_gate.yaml", reports=tmp)
kept = yaml.safe_load((tmp / "live_gate.yaml").read_text(encoding="utf-8"))
check("the whole gate's run is kept as the startup check reads it, with its dated report", not data_check.gate_problems(F, measured=kept) and kept["measured"] == "2026-11-17"
      and kept["speech"]["stiff_sent_back_share"] == 0.3 and (tmp / "2026-11-17_live_gate.md").read_text(encoding="utf-8") == text)

# ---- the whole command, on the stand-in model
script = tmp / "script.yaml"
lines = [{"say": "I look around.", "shape": "look"}, {"say": "I ask whoever is nearest what they have heard.", "shape": "talk"},
         {"say": "I walk on a little way.", "shape": "walk"}, {"say": "I sit down and wait.", "shape": "camp"}]
script.write_text(yaml.safe_dump({"setup": {"seed": 19, "cls": "warrior", "start": "green", "party": 1}, "lines": lines}), encoding="utf-8")
measured, reports = live_gate.MEASURED, sorted(p.name for p in live_gate.REPORTS.glob("*live_gate*"))
stamp = measured.stat().st_mtime if measured.exists() else None
check("with no script the gate says so and leaves 2", live_gate.main(["--stub", "--script", str(tmp / "none.yaml"), "--out", str(tmp / "a")]) == 2)
rc = live_gate.main(["--stub", "--script", str(script), "--out", str(tmp / "run"), "--cases", "12"])
check("the gate runs on the stand-in model and leaves 0: no floor is set", rc == 0, rc)
played = [json.loads(l) for l in (tmp / "run" / "play" / "turns.jsonl").read_text(encoding="utf-8").splitlines()] if (tmp / "run" / "play" / "turns.jsonl").exists() else []
check("the script's lines are the lines played, in order, each filed under its shape",
      [(r["text"], r["kind"]) for r in played] == [(l["say"], l["shape"]) for l in lines], [(r.get("text"), r.get("kind")) for r in played])
check("...each turn took its line (none failed) and kept the passages it showed", played and not any(r.get("hesitated") for r in played) and all("told" in r for r in played)
      and any(r["told"] for r in played), [(r.get("hesitated"), r.get("told")) for r in played])
out = json.loads((tmp / "run" / "live_gate.json").read_text(encoding="utf-8")) if (tmp / "run" / "live_gate.json").exists() else {}
check("its record holds the reading by kind, the counts and the time", out.get("reading", {}).get("cases") == 12 and out["reading"]["by_kind"]
      and set(out["inventions"]) >= {"passages_checked", "phantoms", "unknown_names", "passages_shown"} and out["time"]["inputs"] == 4 and "stiff" in out["speech"]
      and out["inventions"]["passages_shown"] >= 1, list(out))
check("...and says it is no measure", "stand-in" in out.get("about", {}).get("mode", ""))
rc = live_gate.main(["--stub", "--script", str(script), "--out", str(tmp / "cut"), "--no-reading", "--lines", "2"])
cut_rows = (tmp / "cut" / "play" / "turns.jsonl").read_text(encoding="utf-8").splitlines() if (tmp / "cut" / "play" / "turns.jsonl").exists() else []
check("--lines plays the script's first lines and no more, and is no early end", rc == 0 and len(cut_rows) == 2, (rc, len(cut_rows)))
check("a run that is not the whole gate on the real model writes nothing into data/measured or docs/measure",
      (measured.stat().st_mtime if measured.exists() else None) == stamp and sorted(p.name for p in live_gate.REPORTS.glob("*live_gate*")) == reports)
shutil.rmtree(tmp, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
