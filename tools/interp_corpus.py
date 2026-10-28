"""(f365) The interpreter's corpus from night runs: every line the bot typed, the scene it was typed in, and what the game made of it.

    python tools/interp_corpus.py --runs-dir logs/nightrun --out data/replay/interp_corpus.yaml
    python tools/interp_corpus.py --review data/replay/interp_corpus.yaml          the lines by kind, to read and correct
    python tools/interp_eval.py --corpus data/replay/interp_corpus.yaml --live      the measure: the model reads every line again

Why: the interpreter is the first thing a LoRA adapter would be trained for, and the only one whose answer can be scored exactly, but
its hand-written corpus (data/replay/interp_cases.yaml) is small. The night runs hold thousands of real typed lines with the plan the
audit accepted. This turns them into cases in the same shape: one per distinct line, the scene as the interpreter saw it (place, who was
present and their roles, the companions, who was being spoken to), the plan the model read (`plan`, for the offline run), and what ran
(`expect`: the kinds, and the first step's target or destination).

What the audit accepted is not always right. A case marked `reviewed: true` is kept as it is when the corpus is rebuilt, so corrections
by hand survive; everything else is regenerated from the runs. --review prints the lines grouped by kind for that reading: a line whose
`expect` is wrong gets the right answer written in and `reviewed: true`, and from then on the evaluator counts the model against the
right answer, not the accepted one."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml

HIRE = re.compile(r"^hire:\d+-\d+$")


def rows_of(run: Path) -> list[dict]:
    path = next((run / n for n in ("turns_game.jsonl", "turns.jsonl") if (run / n).exists()), None)
    if path is None:
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("handled_by") == "interpret" and r.get("final") and r.get("raw") and r.get("text"):
                out.append(r)
    return out


def norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def slug(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "_".join(words) + "_" + hashlib.sha1(norm(text).encode("utf-8")).hexdigest()[:6]


def signature(final: list[dict]) -> str:
    """What ran, as one string: the kinds, and the first step's target or destination."""
    first = final[0] if final else {}
    aim = first.get("target") or first.get("destination") or ""
    return " ".join(s.get("kind", "?") for s in final) + (f" @{aim}" if aim else "")


def case_of(row: dict, seen: int, run: str) -> dict:
    """A case from a turn row: the scene as the interpreter saw it, the plan the model read, what ran. Hires become the party, and their
    ids in the plan and the scene become the evaluator's own (h0, h1...)."""
    call = (row.get("interpreter") or [{}])[0]
    roles = {k: str(v).strip().lower().replace(" ", "_") for k, v in (call.get("roles") or {}).items()}     # ids, as roles.yaml has them
    present, party, hire_ids = [], [], {}
    for pid, label in (row.get("present") or {}).items():
        if HIRE.match(pid):
            hire_ids[pid] = f"h{len(party)}"
            party.append({"name": label, "role": roles.get(pid, "fighter")})
        else:
            present.append({"id": pid, "name": label, "role": roles.get(pid, "merchant")})

    def rid(x: str) -> str:
        return hire_ids.get(x, x)

    def step(s: dict) -> dict:
        out = {k: v for k, v in s.items() if v not in ("", None, [], {})}
        if "target" in out:
            out["target"] = rid(str(out["target"]))
        return out
    scene = {"place": row.get("place", "trading_square"), "present": present}
    if party:
        scene["party"] = party
    if row.get("partner"):
        scene["partner"] = rid(row["partner"])
    if row.get("last_spoken"):
        scene["last_spoken"] = rid(row["last_spoken"])
    final = [step(s) for s in row["final"]]
    first = final[0] if final else {}
    expect = {"handled_by": "interpret", "kinds": [s.get("kind") for s in final]}
    aim = {k: first[k] for k in ("target", "destination") if first.get(k)}
    if aim:
        expect["first"] = {"kind": first.get("kind"), **aim}
    return {"name": slug(row["text"]), "text": row["text"], "scene": scene, "plan": [step(s) for s in row["raw"]], "expect": expect,
            "seen": seen, "from": run}


def build(runs: list[Path], existing: list[dict] | None = None, world=None) -> list[dict]:
    """Cases from the runs, one per distinct line, merged over what exists: reviewed cases are kept as they are. A line typed somewhere the
    world has no record of (a road made for one journey) cannot be staged again and is left out."""
    if world is None:
        from world.loader import load_world
        world = load_world()
    by_line: dict[str, list[tuple[dict, str]]] = collections.defaultdict(list)
    for run in runs:
        for r in rows_of(run):
            if r.get("place") in world.places:
                by_line[norm(r["text"])].append((r, run.name))
    fresh: dict[str, dict] = {}
    for key, rows in by_line.items():
        sigs = collections.Counter(signature(r["final"]) for r, _ in rows)
        usual = sigs.most_common(1)[0][0]
        row, run = next((r, n) for r, n in rows if signature(r["final"]) == usual)
        c = case_of(row, len(rows), run)
        if len(sigs) > 1:
            c["also"] = [f"{s} ({n})" for s, n in sigs.most_common()[1:4]]       # the line was read other ways too: worth a look
        fresh[c["name"]] = c
    kept: dict[str, dict] = {}
    for c in existing or []:
        if c.get("reviewed"):
            kept[c["name"]] = c
        elif c["name"] not in fresh:
            kept[c["name"]] = c                                                    # from a run no longer in the folder
    out = {**fresh, **kept}
    return sorted(out.values(), key=lambda c: (((c.get("expect") or {}).get("kinds") or ["~"])[0], -int(c.get("seen", 0)), c["name"]))


def review(cases: list[dict]) -> str:
    lines = [f"{len(cases)} lines, {sum(1 for c in cases if c.get('reviewed'))} reviewed", ""]
    by_kind: dict[str, list[dict]] = collections.defaultdict(list)
    for c in cases:
        by_kind[((c.get("expect") or {}).get("kinds") or ["?"])[0]].append(c)
    for kind, cs in sorted(by_kind.items()):
        lines.append(f"## {kind} ({len(cs)})")
        for c in cs:
            first = (c.get("expect") or {}).get("first") or {}
            aim = first.get("target") or first.get("destination") or ""
            mark = "reviewed" if c.get("reviewed") else ("also " + "; ".join(c["also"]) if c.get("also") else "")
            lines.append(f"- [{c.get('seen', 0):>3}] {c['text']!r:<70} -> {' '.join((c.get('expect') or {}).get('kinds') or [])}{(' @' + aim) if aim else ''}  {mark}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", nargs="*", help="night-run folders")
    ap.add_argument("--runs-dir", help="a folder of night runs")
    ap.add_argument("--out", default="data/replay/interp_corpus.yaml")
    ap.add_argument("--review", metavar="CORPUS", help="print the lines of this corpus by kind and stop")
    args = ap.parse_args(argv)
    if args.review:
        try:
            print(review(yaml.safe_load(Path(args.review).read_text(encoding="utf-8")) or []))
        except BrokenPipeError:                                                     # piped into head: enough was read
            pass
        return 0
    runs = [Path(p) for p in args.runs]
    if args.runs_dir:
        runs += sorted(p for p in Path(args.runs_dir).iterdir() if p.is_dir())
    runs = [r for r in runs if rows_of(r)]
    if not runs:
        print("no runs with interpreted turns: name night-run folders, or --runs-dir logs/nightrun")
        return 2
    out = Path(args.out)
    existing = yaml.safe_load(out.read_text(encoding="utf-8")) if out.exists() else []
    cases = build(runs, existing or [])
    out.parent.mkdir(parents=True, exist_ok=True)
    head = ("# (f365) The interpreter's corpus from night runs (tools/interp_corpus.py): one case per distinct typed line, the scene as the\n"
            "# interpreter saw it, the plan the model read, and what ran. Rebuilt from the runs; a case marked reviewed: true is kept as it is,\n"
            "# so write the right answer into `expect` and mark it when the accepted reading was wrong. tools/interp_eval.py --corpus runs it.\n")
    out.write_text(head + yaml.safe_dump(cases, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    print(f"{len(cases)} cases from {len(runs)} run(s) -> {out} ({sum(1 for c in cases if c.get('reviewed'))} reviewed kept)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
