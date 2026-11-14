"""(f626) How well the model reads what an attempt asks of the body, asked that alone (docs/design/19 section 14, step 3).

Every line of the ruling corpora is asked one thing, in a call of its own: whether it is a feat of the body, and which. Four
arms, so one session answers which reading, if any, is worth wiring:

    size         a kind from the body's table (data/rules/body.yaml) with its size, or none
    size+self    the same, with a kind for the body moving only itself, which the table reads as none
    thing        a kind with the thing it is done to, and no size (the size then kept on the thing: design 19 section 10, answer 4)
    thing+self   the same, with the kind for the body itself
    sized        (f627) the engine's own two calls, as play would make them (engine/body.py attempt): `thing+self`, then for a feat
                 the size of the thing it named

    python tools/reading_eval.py                           the stub's readings: the tool run whole, no model
    python tools/reading_eval.py --live --passes 2         the real model (the game's own server, tools/runtime_cli.py), each line twice
    python tools/reading_eval.py --live --arms size,thing --cases data/replay/ruling_cases_feat.yaml --out readings.jsonl

What is scored, and what is not:
- A case that says what a sensible table would name (`feat`, tools/ruling_eval.py) scores its reading: ok, the kind wrong, or (a
  size arm only) the kind right and the size outside its range. Arms are compared on the kind: a thing arm has no size to miss, and
  the words it gives for the thing are kept in the rows and judged by no one here.
- For a size, the table then answers with it for the case's own body, beside what it answers with the reading the case holds
  itself (`model.feat`): the same answer or not. A wrong reading that changes nothing counts as the same, so it is also counted
  over the readings whose kind was right alone.
- A case that says nothing of feats is counted as named a feat or not, and listed, for a person to read: never right or wrong.
- (f627) For a size, what the engine then answers: with the case's own ruling, whether its yes or no is the case's; and on the
  cases that say nothing, whether the table would refuse the act, for the case's own body and for an ordinary one. A fair act
  (one the case does not expect a no for) refused is the harm a wrong reading does. `gate` holds the engine's arm to the numbers
  docs/design/19 section 16 sets before anything is wired into play.
- The same case read as a feat on one pass and as none on another, or as another kind, is counted.

What the model is handed: the place's name and the player's line. The ruling it is compared with (f623) was handed the whole
scene, so this is a reading at its barest; one wired into play could be given more and needs its own measure. The kind's clause
and the size's are f623's words; the opening sentence is new, since the call is. The tool wires nothing into play."""
from __future__ import annotations

import argparse
import copy
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pydantic import BaseModel, model_validator

CASES = sorted((ROOT / "data" / "replay").glob("ruling_cases*.yaml"))
ARMS = {"size": ("size", False), "size+self": ("size", True), "thing": ("thing", False), "thing+self": ("thing", True)}
ENGINE = "sized"         # (f627) the engine's own two calls: scored as a size reading is
ALL = [*ARMS, ENGINE]
OWN = "self"             # the body moving only itself: no kind of the table's, so the table reads it as no feat
TITLE = "FeatReading"
TITLES = (TITLE, "FeatSize")
TASK = "ruling"          # the road's ruling's budget row, borrowed by the four arms: a tool's call is in no turn
GATE = {"verdict": 36, "fair_refused_plain": 2, "refuse": "I lift the portcullis with my bare hands."}   # docs/design/19 section 16


def measure_of(arm: str) -> str:
    return "size" if arm == ENGINE else ARMS[arm][0]


def asks(measure: str) -> str:
    from engine import body
    return {"size": "size: how big it is, as the world plainly is: one number in that kind's unit.", "thing": body.THING}[measure]


def own_line(measure: str) -> str:
    from engine import body
    return body.own_line(measure)


def system(measure: str, own: bool) -> str:
    """What one of the four arms is told, in the engine's own words for all they share (engine/body.py)."""
    from engine import body
    return (f"{body.ASKED}{asks(measure)}\n"
            f"FEATS (a kind: what its size measures):\n{body.lines()}" + (f"\n{own_line(measure)}" if own else ""))


def request(where: str, line: str) -> str:
    return f"WHERE: {where}\nTHE ATTEMPT: {line}"


class Reading(BaseModel):
    kind: str = "none"
    size: int = 0
    thing: str = ""


def shape(measure: str, own: bool) -> type[Reading]:
    """An arm's reading in its own grammar: no feat (none, or the body's own kind), or a kind of the table's with its size or its thing."""
    from engine import body
    blank = ["none"] + ([OWN] if own else [])
    what = ({"size": body.schema()["anyOf"][1]["properties"]["size"]} if measure == "size"
            else {"thing": {"type": "string", "minLength": 1, "maxLength": int(body.B["thing_chars"])}})
    schema = {"title": TITLE, "anyOf": [{"type": "object", "required": ["kind"], "properties": {"kind": {"enum": blank}}},
                                        {"type": "object", "required": ["kind", measure],
                                         "properties": {"kind": {"enum": list(body.K)}, **what}}]}

    class Shaped(Reading):
        @classmethod
        def model_json_schema(cls, *a, **k) -> dict:
            return copy.deepcopy(schema)

        @model_validator(mode="after")
        def held(self):
            self.kind = (self.kind or "").strip().lower() or "none"
            if self.kind in blank:
                self.size, self.thing = 0, ""
                return self
            if self.kind not in body.K:
                raise ValueError(f"kind is one of {', '.join(blank + list(body.K))}")
            if measure == "size" and not self.size > 0:
                raise ValueError("a feat needs its size, one whole number above 0")
            if measure == "thing" and not self.thing.strip():
                raise ValueError("a feat needs its thing, in a few words")
            return self
    Shaped.__name__ = Shaped.__qualname__ = TITLE
    return Shaped


def kind_of(r) -> str:
    """The kind the table would take a reading as: the body's own kind is none of its own."""
    return "none" if r is None or r.kind in ("none", OWN) else r.kind


def feat(r):
    """A size reading as the table is handed it."""
    from engine import body
    return body.Feat() if kind_of(r) == "none" else body.read(r.kind, r.size)


def score(case: dict, r, measure: str) -> str:
    """A reading against its case. Where the case says what a sensible table would name: ok, kind (another kind, a feat where there
    is none, or none where there is one) or size (the kind right, the size outside its range; never said of a thing reading).
    Where it says nothing: feat or none, what was named, for a person to read."""
    from tools import ruling_eval
    kind = kind_of(r)
    if "feat" not in case:
        return "none" if kind == "none" else "feat"
    if measure == "size":
        return ruling_eval.named(case, feat(r))
    fair = ruling_eval.fair_feats(case["feat"])
    return "ok" if any((a == "none") == (kind == "none") and (a == "none" or a["kind"] == kind) for a in fair) else "kind"


def stands(b, f, plain: bool = False) -> bool:
    """Whether the table lets the attempt stand with this feat read for it, for the body of the case the bench was last put to;
    `plain`: for an ordinary body with that case's powers."""
    from engine import act, body
    who = b.ws.acting
    return body.judge(body.ordinary() if plain else act.own_body(b.ws, who), act.means(b.ws, who), None, f).how not in ("nearly", "past")


def verdict(b, case: dict, f) -> bool | None:
    """(f627) Whether the engine's yes or no, on the case's own ruling with this feat read for it, is the one the case expects.
    None where the case holds no ruling of its own."""
    from engine import act
    if not case.get("model"):
        return None
    T = b.targets()
    v = act.validate(b.ws, b.ws.acting, T, b.act_model(case, T), f)
    return v.ok == (case["expect"] != "no")


def ask(b, case: dict, arm: str):
    """One reading of one case in one arm, from whatever answers the bench: (the reading or None, the seconds it took, the error)."""
    from engine import body
    from llm.gateway import LLMError, generate
    b.put(case)
    t0 = time.perf_counter()
    if arm == ENGINE:
        got = body.attempt(b.ws.place.name, b.line(case))
        secs = time.perf_counter() - t0
        if got.lost:
            return None, secs, f"no {got.lost}"
        return Reading(kind=got.said, size=int(got.feat.size), thing=got.thing), secs, ""
    measure, own = ARMS[arm]
    try:
        r = generate(TASK, system(measure, own), request(b.ws.place.name, b.line(case)), shape(measure, own), temperature=0.3,
                     max_tokens=80, _quiet=True)
        return r, time.perf_counter() - t0, ""
    except LLMError as e:
        return None, time.perf_counter() - t0, f"{type(e).__name__}: {e}"[:200]


def run(b, cases: list[dict], arms: list[str], passes: int = 1, say=print) -> list[dict]:
    """Every case in every arm, `passes` times over, an arm at a time (its instruction stays the server's cached prefix). One row a
    reading: what was read, how it scored, and for a size on a case that says, whether the table answers as with the case's own."""
    from tools import ruling_eval
    rows = []
    for p in range(1, passes + 1):
        for arm in arms:
            measure = measure_of(arm)
            for i, c in enumerate(cases):
                r, secs, err = ask(b, c, arm)
                row = {"case": i, "file": c.get("file", ""), "line": c["line"], "arm": arm, "pass": p, "labelled": "feat" in c,
                       "expect": c["expect"], "kind": getattr(r, "kind", ""), "size": getattr(r, "size", 0), "thing": getattr(r, "thing", ""),
                       "score": "" if r is None else score(c, r, measure), "table": None, "verdict": None, "refused": None,
                       "refused_plain": None, "seconds": round(secs, 2), "error": err}
                if r is not None and measure == "size":
                    row["refused"], row["refused_plain"] = not stands(b, feat(r)), not stands(b, feat(r), plain=True)
                    if "feat" in c:
                        row["table"] = stands(b, feat(r)) == stands(b, ruling_eval.reading(c))
                        row["verdict"] = verdict(b, c, feat(r))
                rows.append(row)
                read = "no reading" if r is None else " ".join(str(x) for x in (r.kind, r.size or "", r.thing) if x != "")
                say(f"  {arm:<10} {p}  {row['score'] or '?':<5} {read:<28} {b.line(c)}"
                    + ("" if row["table"] is not False else "  [the table answers otherwise]"))
    return rows


def summary(rows: list[dict]) -> dict:
    """The counts, an arm and a pass at a time. `right`: the kind right (ok, or the size alone wrong), what arms are compared on.
    `table` of `tabled`: the table's answer the same as with the case's own reading; `table_right` of `right`: over the readings
    whose kind was right. `verdict` of `verdicted`: the engine's yes or no the case's. `fair_refused`, `fair_refused_plain`: of
    the cases that say nothing and expect no no, those the table would refuse, for the case's own body and an ordinary one. For
    each arm, `moved` of the `twice` cases read on every pass: read as another kind, the body's own kind being none."""
    out = {}
    for arm in dict.fromkeys(r["arm"] for r in rows):
        mine = [r for r in rows if r["arm"] == arm]
        passes = []
        for p in sorted({r["pass"] for r in mine}):
            got = [r for r in mine if r["pass"] == p and not r["error"]]
            said = [r for r in got if r["labelled"]]
            free = [r for r in got if not r["labelled"]]
            right = [r for r in said if r["score"] in ("ok", "size")]
            passes.append({"pass": p, "labelled": len(said), **{k: sum(r["score"] == k for r in said) for k in ("ok", "kind", "size")},
                           "right": len(right), "table": sum(r["table"] is True for r in said),
                           "tabled": sum(r["table"] is not None for r in said), "table_right": sum(r["table"] is True for r in right),
                           "verdict": sum(r.get("verdict") is True for r in said), "verdicted": sum(r.get("verdict") is not None for r in said),
                           "fair_refused": sum(1 for r in free if r.get("refused") and r.get("expect") != "no"),
                           "fair_refused_plain": sum(1 for r in free if r.get("refused_plain") and r.get("expect") != "no"),
                           "unlabelled": len(free), "feat": sum(r["score"] == "feat" for r in free),
                           "own": sum(r["kind"] == OWN for r in got), "failed": sum(1 for r in mine if r["pass"] == p and r["error"]),
                           "seconds": round(statistics.median([r["seconds"] for r in got]), 2) if got else 0})
        by = {}
        for r in mine:                                         # by its place: a corpus may hold a line twice
            by.setdefault(r["case"], {})[r["pass"]] = None if r["error"] else ("none" if r["kind"] in ("none", OWN) else r["kind"])
        twice = [v for v in by.values() if len(v) > 1 and None not in v.values()]
        out[arm] = {"passes": passes, "twice": len(twice), "moved": sum(len(set(v.values())) > 1 for v in twice)}
    return out


def lines(total: dict) -> list[str]:
    out = []
    for arm, t in total.items():
        for s in t["passes"]:
            out.append(f"{arm}, pass {s['pass']}: of {s['labelled']} cases that say, the kind right on {s['right']}"
                       + (f" (the size too on {s['ok']})" if measure_of(arm) == "size" else "")
                       + (f"; the table answers as with the case's own reading on {s['table']} of {s['tabled']}, and on "
                          f"{s['table_right']} of the {s['right']} with the kind right" if s["tabled"] else "")
                       + (f"; the engine's yes or no is the case's on {s['verdict']} of {s['verdicted']}" if s["verdicted"] else "")
                       + f"; of {s['unlabelled']} that say nothing, a feat named on {s['feat']}"
                       + (f" (fair acts refused: {s['fair_refused']} for the case's own body, {s['fair_refused_plain']} for an ordinary "
                          f"body)" if measure_of(arm) == "size" else "")
                       + f"; the body's own kind {s['own']} times; "
                         f"{s['failed']} with no reading; {s['seconds']} s a reading at the median")
        if t["twice"]:
            out.append(f"{arm}: {t['moved']} of {t['twice']} cases read as another kind on a later pass")
    return out


def gate(rows: list[dict]) -> dict:
    """(f627) The engine's arm against GATE, a pass at a time: enough of the engine's answers the case's, few enough fair acts
    refused an ordinary body among the cases that say nothing, and the one line that must be refused, refused. A reading that was
    lost counts as play would have it, the attempt standing as ruled, and `lost` says how many. Beside the gate, not of it:
    `refused_no` of the `no_cases` labelled cases that expect a no, refused for the case's own body."""
    out = {}
    mine = [r for r in rows if r["arm"] == ENGINE]
    for p in sorted({r["pass"] for r in mine}):
        got = [r for r in mine if r["pass"] == p]
        right = sum(r["verdict"] is True for r in got if r["labelled"])
        fair = sum(1 for r in got if not r["labelled"] and r["refused_plain"] and r["expect"] != "no")
        must = next((r["refused"] for r in got if r["line"] == GATE["refuse"]), None)
        noes = [r for r in got if r["labelled"] and r["expect"] == "no"]
        out[p] = {"verdict": right, "fair_refused_plain": fair, "refused": must, "lost": sum(bool(r["error"]) for r in got),
                  "refused_no": sum(r["refused"] is True for r in noes), "no_cases": len(noes),
                  "met": right >= GATE["verdict"] and fair <= GATE["fair_refused_plain"] and must is True}
    return out


def main(argv=None) -> int:
    from tools import ruling_eval, runtime_cli
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--cases", nargs="+", default=[str(p) for p in CASES], help="the case files (every ruling corpus by default)")
    ap.add_argument("--arms", default=",".join(ALL), help=f"some of {', '.join(ALL)}")
    ap.add_argument("--passes", type=int, default=1, help="how many times each line is read in each arm")
    ap.add_argument("--out", default="", help="a file for the rows, one JSON object a line")
    runtime_cli.add_args(ap)
    a = ap.parse_args(argv)
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    if not arms or set(arms) - set(ALL) or a.passes < 1:
        print(f"REFUSED: --arms is some of {', '.join(ALL)}, --passes at least 1", file=sys.stderr)
        return 2
    cases = []
    for path in a.cases:
        found = ruling_eval.load(path)
        wrong = ruling_eval.problems(found)
        if wrong:
            for x in wrong:
                print(f"REFUSED {path}: {x}", file=sys.stderr)
            return 2
        cases += [dict(c, file=Path(path).name) for c in found]
    server = runtime_cli.load(a) if a.live else None
    b = ruling_eval.Bench(live=a.live, source=server.source if server is not None else None, save=f"reading_eval_{os.getpid()}",
                          ruled=TITLES)
    try:
        rows = run(b, cases, arms, a.passes)
    finally:
        b.clear()
        b.close()
        if server is not None:
            server.close()
    if a.out:
        Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    print()
    for arm in arms:
        named = sorted({(r["line"], r["kind"]) for r in rows if r["arm"] == arm and r["score"] == "feat"})
        if named:
            print(f"{arm}: a feat named where the case says nothing ({len(named)}):")
            for line, kind in named:
                print(f"    {kind:<12} {line}")
    print()
    for x in lines(summary(rows)):
        print(x)
    for p, g in gate(rows).items():
        print(f"the gate, pass {p}: {'met' if g['met'] else 'NOT met'}: the engine's yes or no the case's on {g['verdict']} (at least "
              f"{GATE['verdict']}); fair acts refused an ordinary body {g['fair_refused_plain']} (at most {GATE['fair_refused_plain']}); "
              f"\"{GATE['refuse']}\" " + {True: "refused", False: "NOT refused", None: "with no reading"}[g["refused"]]
              + f". Beside the gate: {g['lost']} readings lost; of the {g['no_cases']} labelled cases that expect a no, the table refuses "
              f"{g['refused_no']}")
        for r in rows:
            if r["arm"] == ENGINE and r["pass"] == p and not r["labelled"] and r["refused_plain"] and r["expect"] != "no":
                print(f"    refused an ordinary body: {r['kind']} {r['size']} ({r['thing']})  {r['line']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
