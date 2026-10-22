"""Replay cases through the intent audit gate.
    python tools/replay.py                       recorded model replies, instant, no model needed (this is what the test suite runs)
    python tools/replay.py --live                the real model reads every case from scratch; reports how often the final plan is right
    python tools/replay.py --promote logs/turns.jsonl -1     print a case stub from a logged turn (edit 'expect' and add it to data/replay/cases.yaml)
Cases live in data/replay/cases.yaml."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml

from engine import intent_audit as ia
from llm.contracts import ActionIntent

CASES = Path(__file__).resolve().parent.parent / "data" / "replay" / "cases.yaml"


def load_cases(path=CASES) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def situation(case: dict) -> ia.Situation:
    sc = case.get("scene", {})
    present = {k: str(v) for k, v in (sc.get("present") or {}).items()}
    abil = {a.lower(): a for a in sc.get("abilities", [])}
    sit = ia.Situation(present=present, abilities=abil, place=sc.get("place", "somewhere"), wildlife=bool(sc.get("wildlife")))
    sit.lines = [f"Place: {sit.place}.", "People here: " + (", ".join(present.values()) or "no one") + "."]
    return sit


def steps(raw: list[dict]) -> list[ActionIntent]:
    return [ActionIntent(**r) for r in raw]


class Recorded:
    """Replies written down in the case. A proposal list that runs out repeats its last plan."""
    def __init__(self, rec: dict):
        self.rec, self.n = rec or {}, 0

    def meaning(self, text, sit):
        return self.rec.get("meaning", "")

    def compare(self, text, meaning, described, risk):
        return bool(self.rec.get("matches", True)), self.rec.get("reason", "")

    def propose(self, text, hint):
        props = self.rec.get("proposals") or []
        if not props:
            raise RuntimeError("no recorded proposal")
        plan = props[min(self.n, len(props) - 1)]
        self.n += 1
        return steps(plan)


def matches(final: list, expect: list[dict]) -> bool:
    if len(final) != len(expect):
        return False
    for step, want in zip(final, expect):
        got = step.model_dump()
        if any(str(got.get(k, "")).lower() != str(v).lower() for k, v in want.items()):
            return False
    return True


def run_case(case: dict, ask, raw=None) -> ia.Result:
    return ia.audit(case["text"], raw if raw is not None else steps(case["raw"]), situation(case), ask)


def deterministic(cases=None, quiet=False) -> list[str]:
    bad = []
    for case in cases or load_cases():
        res = run_case(case, Recorded(case.get("audit")))
        ok = res.status == case["status"] and (res.status == "failed" or matches(res.plan, case["expect"]))
        if not quiet:
            print(("ok   " if ok else "FAIL ") + case["name"], "" if ok else f"{res.status} {[s.kind for s in res.plan]} {res.reason}")
        if not ok:
            bad.append(case["name"])
    return bad


def live(cases=None) -> None:
    """Ask the real model: read the text from scratch, then run the gate with real audit calls."""
    from scenes import world_prompts as wp
    from llm.gateway import generate
    from llm.contracts import ActionPlan, AuditMeaning, AuditVerdict
    from scenes import audit_actions as aa

    def interpret(case, text, hint=""):
        sc = case.get("scene", {})
        people = [(k, str(v), "") for k, v in (sc.get("present") or {}).items()]
        req = wp.interpret_request("Day 1 10:00", sc.get("place", "somewhere"), [(p, p) for p in sc.get("places", [])], people, [], None, None,
                                   text, sc.get("wares", []), sc.get("abilities", []), sc.get("pack", []), [], None, [], [], [], "", hint)
        return generate("interpret_action", wp.INTERPRET_SYSTEM, req, ActionPlan, temperature=0.2, max_tokens=700).actions

    right = audited = fixed = broke = 0
    cases = cases or load_cases()
    for case in cases:
        class Ask:
            def meaning(s, text, sit):
                return generate("audit_meaning", aa.MEANING_SYSTEM, "\n".join(sit.lines) + f'\nPLAYER TYPED: "{text}"', AuditMeaning,
                                temperature=0.1, retries=1, max_tokens=120).meaning

            def compare(s, text, meaning, described, risk):
                v = generate("audit_compare", aa.COMPARE_SYSTEM,
                             f'PLAYER TYPED: "{text}"\nPLAYER MEANT: {meaning}\nPLAN:\n{described}\nTHINGS TO WATCH: {", ".join(risk)}',
                             AuditVerdict, temperature=0.1, retries=1, max_tokens=160)
                return v.matches, v.reason

            def propose(s, text, hint):
                return interpret(case, text, hint)
        first = interpret(case, case["text"])
        before = matches(ia.fix(first), case["expect"])
        res = run_case(case, Ask(), first)
        after = res.status != "failed" and matches(res.plan, case["expect"])
        right += after
        audited += res.status != "skipped"
        fixed += (not before) and after
        broke += before and not after
        print(("ok   " if after else "FAIL ") + f"{case['name']:34} audit={res.status:9} calls={res.calls} "
              f"{[s.kind for s in first]} -> {[s.kind for s in res.plan]}  {res.verdict or res.reason}")
    n = len(cases)
    print(f"\n{right}/{n} right in the end; audit ran on {audited}; it repaired {fixed} and broke {broke} that were already right.")


def promote_case(e: dict) -> dict:
    """A replay case from one turn-log row (engine/turnlog.py): the scene as the gate saw it and, when the row carries the interpreter's
    calls, the place, the places and the catalogues the model was shown, so --live rebuilds the same request."""
    scene = {"present": e.get("present", {}), "abilities": e.get("abilities", []), "wildlife": e.get("wildlife", False)}
    calls = e.get("interpreter") or []
    first = calls[0] if calls else {}
    if e.get("place_name") or first.get("place_name"):
        scene["place"] = e.get("place_name") or first.get("place_name")
    if first.get("places"):
        scene["places"] = list(first["places"])
    for key in ("wares", "pack"):
        if (first.get("shown") or {}).get(key):
            scene[key] = list(first["shown"][key])
    return {"name": "promoted_turn", "text": e["text"], "scene": scene, "raw": e.get("raw") or [], "expect": e.get("final") or [],
            "status": e.get("audit", "unchanged")}


def promote(path: str, index: int) -> None:
    lines = [l for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [json.loads(l) for l in lines]
    rows = [r for r in rows if r.get("handled_by", "interpret") == "interpret"]       # only a line the model read can be a case
    print(yaml.safe_dump([promote_case(rows[index])], sort_keys=False, allow_unicode=True))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--promote", nargs=2, metavar=("LOG", "INDEX"))
    a = ap.parse_args()
    if a.promote:
        promote(a.promote[0], int(a.promote[1]))
    elif a.live:
        live()
    else:
        sys.exit(1 if deterministic() else 0)
