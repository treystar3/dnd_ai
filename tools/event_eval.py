"""How the big events play out, measured: a corpus of event scenarios, each walked through by a character (tools/event_trial.py) and
judged against what should happen - the counterpart of tools/interp_eval.py for campaigns and cataclysms.

A case names a character's level, a campaign or a cataclysm of a kind, how long to give it and how the character goes at it (a path to
prefer, or ignoring it), and what should come of it: that it starts, how far it gets, who ends it, the path, the reward, how many
towns fall, what the day-by-day must mention, and that the world checks out afterwards (storage/invariants.py).

Offline the stand-in model writes the campaign's stages, paths and boss and the cataclysm's prose, so a case says whether the engine
carries an event to its end. With --live the real model writes them while everything else stays stubbed, so the same judgements say
whether what the model writes can be played to its end: the paths it names, the creatures it picks, the telling the engine checks.

  python tools/event_eval.py                     every case, offline
  python tools/event_eval.py --live              the model writes the events (needs Ollama)
  python tools/event_eval.py --only war,plague   cases whose names contain either
  python tools/event_eval.py --quiet             the summary only

Case (data/replay/event_cases.yaml): name, tier (campaign | cataclysm), kind, pressure, level, seed, days, path, ignore, from_stage,
  expect: started, status (one or a list), result (one or a list), min_stage, won_path (a word of the path's name), reward (true/false),
          titles (true), fallen_at_least, fallen_at_most, acted (words that must appear in what the character did), lines (words that must
          appear in the day-by-day), problems (how many the checker may find; 0)."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CASES = ROOT / "data" / "replay" / "event_cases.yaml"
LIVE_TITLES = {"ThreadProposal", "CataclysmProposal", "JudgeVerdict", "ThreadTelling"}     # what the model writes for an event; the rest stays stubbed


def load_cases(path=CASES) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


def route_live() -> None:
    """The stand-in answers everything but the event's own calls, which reach the real model (as tools/interp_eval.py does for the interpreter)."""
    import types
    import simlib
    from llm import gateway as gw
    real = gw._client
    stub = simlib.Stub("warrior", 3)
    simlib.install(stub)
    stub_chat = stub.chat

    def chat(**k):
        if (k.get("format") or {}).get("title") in LIVE_TITLES:
            return real.chat(**k)
        return stub_chat(**k)
    gw._client = types.SimpleNamespace(chat=chat)


def judge(got: dict, expect: dict) -> list[str]:
    """What is wrong with the outcome, in words; empty when it is right."""
    bad = []
    want = lambda k: expect[k] if isinstance(expect[k], list) else [expect[k]]
    if "started" in expect and bool(got["started"]) != bool(expect["started"]):
        bad.append("never started" if expect["started"] else "started when it should not")
    if "status" in expect and got["status"] not in want("status"):
        bad.append(f"status {got['status']!r}, not {expect['status']!r}")
    if "result" in expect and got["result"] not in want("result"):
        bad.append(f"result {got['result']!r}, not {expect['result']!r}")
    if "min_stage" in expect and got["stage"] < int(expect["min_stage"]):
        bad.append(f"reached stage {got['stage']}, not {expect['min_stage']}")
    if "won_path" in expect and str(expect["won_path"]).lower() not in (got["won_path"] + " " + got.get("won_path_id", "")).lower():
        bad.append(f"path met {got['won_path']!r} ({got.get('won_path_id', '')}), not one with {expect['won_path']!r}")   # the id is the engine's, the name the writer's
    if "reward" in expect and bool(got["reward"]) != bool(expect["reward"]):
        bad.append("no reward" if expect["reward"] else "a reward when there should be none")
    if "titles" in expect and bool(got["titles"]) != bool(expect["titles"]):
        bad.append("no title" if expect["titles"] else "a title when there should be none")
    if "fallen_at_least" in expect and len(got["fallen"]) < int(expect["fallen_at_least"]):
        bad.append(f"{len(got['fallen'])} town(s) fell, fewer than {expect['fallen_at_least']}")
    if "fallen_at_most" in expect and len(got["fallen"]) > int(expect["fallen_at_most"]):
        bad.append(f"{len(got['fallen'])} town(s) fell, more than {expect['fallen_at_most']}")
    for w in expect.get("acted") or []:
        if not any(str(w).lower() in a.lower() for a in got["acted"]):
            bad.append(f"the character never {w!r}")
    for w in expect.get("lines") or []:
        if not any(str(w).lower() in l.lower() for l in got["lines"]):
            bad.append(f"the days never say {w!r}")
    if "problems" in expect and len(got["problems"]) > int(expect["problems"]):
        bad.append(f"{len(got['problems'])} invariant problem(s): " + "; ".join(got["problems"][:2]))
    return bad


def group_of(case: dict) -> str:
    return case.get("tier", "campaign") + (f":{case['kind']}" if case.get("kind") else "")


def evaluate(cases: list[dict], live: bool = False, quiet: bool = False) -> dict:
    from tools import event_trial as et
    if live:
        route_live()
    results, wrong = [], []
    start = time.time()
    for case in cases:
        out = et.run(case.get("tier", "campaign"), case.get("kind", ""), int(case.get("level", 60)), case.get("cls", "warrior"), int(case.get("seed", 5)),
                     case.get("pressure", ""), int(case.get("days", 150)), bool(case.get("ignore")), case.get("path", ""), live,
                     save="event_eval", quiet=True, act_from_stage=int(case.get("from_stage", 2)))
        bad = judge(out, case.get("expect") or {})
        results.append((case["name"], out, bad))
        if bad:
            wrong.append(case["name"])
        if not quiet:
            print(("ok   " if not bad else "FAIL ") + f"{case['name']:<34} " + et.verdict(out) + ("" if not bad else "\n     <- " + "; ".join(bad)))
            if live:
                print(f"     model wrote: {out['title']!r}; paths {[p for p, _ in out['paths']]}")
            if not out["started"]:
                for l in out["lines"][-3:]:
                    print(f"     {l[:200]}")
    n = len(cases)
    by: dict[str, list[int]] = {}
    for case, (_, _, bad) in zip(cases, results):
        row = by.setdefault(group_of(case), [0, 0])
        row[1] += 1
        row[0] += not bad
    summary = {"cases": n, "right": n - len(wrong), "wrong": wrong, "by_kind": {k: f"{r}/{t}" for k, (r, t) in sorted(by.items())},
               "seconds": round(time.time() - start, 1)}
    if live:
        try:
            from llm import gateway
            summary["model_calls"] = dict(getattr(gateway, "OUTCOMES", {}) or {})
        except Exception:
            pass
    if not quiet:
        print(f"\n{summary['right']}/{n} right in {summary['seconds']}s" + (" (live: the model wrote the events)" if live else " (offline: the stand-in wrote them)"))
        print("by kind: " + ", ".join(f"{k} {v}" for k, v in summary["by_kind"].items()))
        if summary.get("model_calls"):
            print("model calls: " + ", ".join(f"{k} {v}" for k, v in summary["model_calls"].items()))
        if wrong:
            print("wrong: " + ", ".join(wrong))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated words; a case runs when its name contains one")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--cases", default=str(CASES))
    a = ap.parse_args()
    cases = load_cases(a.cases)
    if a.only:
        keys = [k.strip() for k in a.only.split(",") if k.strip()]
        cases = [c for c in cases if any(k in c["name"] for k in keys)]
    out = evaluate(cases, live=a.live, quiet=a.quiet)
    return 1 if out["wrong"] else 0


if __name__ == "__main__":
    sys.exit(main())
