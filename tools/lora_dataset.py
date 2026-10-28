"""(f361) A night run's logs as training data.

    python tools/lora_dataset.py logs/nightrun/20261027_1825 logs/nightrun/20261027_2146 --out lora/data
    python tools/lora_dataset.py --runs-dir logs/nightrun --out lora/data --holdout logs/nightrun/20261027_2222

Every call the game made is a row of the run's llm_calls.jsonl: the prompt, the answer, the validator's reason when it was sent back,
and the retry that passed as the next row. This reads those rows, groups them back into calls, and writes two kinds of file per task:

  <out>/train/<task>.sft.jsonl     accepted answers to learn from: {"messages": [system, user, assistant]}
  <out>/train/<task>.pairs.jsonl   a rejected draft and the answer that replaced it, same prompt: {"prompt", "chosen", "rejected"}
                                   (the gateway's retries, and the narrator's rewrites from scenes/voice.py fresh)

The newest run is held out by default (--holdout names one; --no-holdout keeps everything for training) and lands under <out>/eval/
in the same shapes, for tools/lora_eval.py. <out>/summary.md says what was kept and what was dropped, and why.

--prompts short (the default) replaces each task's long system prompt with the short one in data/rules/lora.yaml, so a model trained on
it learns to behave as if the rules were there; --prompts full keeps the game's own, which needs runs logged with LOG_FULL_PROMPTS on
(tools/nightrun.py sets it; an older run's shortened prompts are skipped under full and counted).

Accepted answers are filtered once more by the habits the game only nudges (lora.yaml filters): a passage ending two sentences on a
trailing participle, a reply opening on 'Well,', a line trailing off twice. The draft a rewrite replaced is never learned from, only
paired. Nothing here calls a model."""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml

L = yaml.safe_load((ROOT / "data" / "rules" / "lora.yaml").read_text(encoding="utf-8"))
SHORTENED = "[...shortened in log]"
REWRITE_MARK = "\n\nYOUR DRAFT "          # scenes/voice.py fresh and the narrator's strict retry add this to the request they re-ask


# ---------------------------------------------------------------- reading a run

def rows_of(path: Path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def calls_of(rows: list[dict]) -> list[list[dict]]:
    """Rows grouped back into calls: attempt 0 opens a call; the rows after it with rising attempts and the same system and user
    messages belong to it, even with other calls' rows (background threads) between them."""
    open_calls: dict[tuple, list[dict]] = {}
    calls: list[list[dict]] = []
    for r in rows:
        msgs = r.get("messages") or []
        if len(msgs) < 2 or "task" not in r:
            continue
        key = (r["task"], msgs[0].get("content", ""), msgs[1].get("content", ""))
        if r.get("attempt", 0) == 0 or key not in open_calls:
            call = [r]
            open_calls[key] = call
            calls.append(call)
        else:
            open_calls[key].append(r)
    return calls


def accepted(call: list[dict]) -> dict | None:
    return next((r for r in call if not r.get("error")), None)


def prompt_of(call: list[dict]) -> tuple[str, str]:
    m = call[0]["messages"]
    return m[0].get("content", ""), m[1].get("content", "")


# ---------------------------------------------------------------- the habits an accepted answer must not carry

def strings_in(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings_in(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings_in(v)]
    return []


def habits(task: str, raw: str) -> str:
    """Why an accepted answer is still not learned from, or ''."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return "not json"
    text = " ".join(strings_in(data))
    F = L.get("filters") or {}
    if task in (L.get("prose_tasks") or []):
        from scenes.voice import STALE, participle_tails
        if len(participle_tails(text)) > int(F.get("max_tails", 1)):
            return "participle tails"
        low = text.lower()
        if any(s in low for s in STALE):
            return "stock phrase"
    if task in (L.get("speech_tasks") or []):
        from llm.contracts import opener_of
        speech = data.get("speech") or data.get("line") or text
        if not F.get("stock_opener", False) and opener_of(speech):
            return "stock opener"
        if speech.count("...") + speech.count("…") > int(F.get("max_dots", 1)):
            return "trailing off"
    return ""


def reason_key(error: str) -> str:
    """A rejection reason as a category: the message without the names and quotes that change per call."""
    e = re.sub(r"'[^']*'", "'_'", error or "")
    e = re.sub(r"\(.*?\)", "", e)
    return " ".join(e.split())[:60]


def nudge_heads(nudge: str) -> str:
    heads = re.findall(r"(?:^|YOUR DRAFT ALSO |YOUR DRAFT )([A-Z][A-Z' ,-]{5,}?)(?::|\s\(|\.)", nudge)
    return "; ".join(h.strip() for h in heads)[:60] or "rewrite"


# ---------------------------------------------------------------- building

def system_for(task: str, system: str, prompts: str) -> str | None:
    """The system prompt an example carries: the short one for the task, or the logged one in full. None when full was asked and the
    log only kept the start."""
    if prompts == "short":
        S = L.get("short_system") or {}
        return S.get(task) or S.get("default") or ""
    if system.endswith(SHORTENED):
        return None
    return system


def build(runs: list[Path], holdout: list[Path], out: Path, prompts: str = "short", tasks: list[str] | None = None) -> dict:
    """Write the files. Returns the counts that summary.md is written from."""
    tasks = tasks or list(L.get("tasks") or [])
    counts: dict = {"train": collections.defaultdict(collections.Counter), "eval": collections.defaultdict(collections.Counter),
                    "reasons": collections.defaultdict(collections.Counter), "runs": {"train": [str(r) for r in runs], "eval": [str(r) for r in holdout]}}
    files: dict[tuple[str, str, str], list[str]] = collections.defaultdict(list)
    for split, group in (("train", runs), ("eval", holdout)):
        for run in group:
            path = run / "llm_calls.jsonl"
            if not path.exists():
                continue
            calls = [c for c in calls_of(rows_of(path)) if c[0]["task"] in tasks]
            by_prompt: dict[tuple[str, str], list[dict]] = {}
            superseded: set[int] = set()
            for call in calls:
                task = call[0]["task"]
                system, user = prompt_of(call)
                c = counts[split][task]
                c["calls"] += 1
                ok = accepted(call)
                if ok is None:
                    c["gave up"] += 1
                # the gateway's retries: each rejected attempt against the one that passed
                for i in range(1, len(call)):
                    if call[i - 1].get("error") and not call[i].get("error"):
                        counts["reasons"][task][reason_key(call[i - 1]["error"])] += 1
                        sys_text = system_for(task, system, prompts)
                        if sys_text is not None:
                            files[(split, task, "pairs")].append(json.dumps(
                                {"prompt": [{"role": "system", "content": sys_text}, {"role": "user", "content": user}],
                                 "chosen": [{"role": "assistant", "content": call[i]["raw"]}],
                                 "rejected": [{"role": "assistant", "content": call[i - 1]["raw"]}]}, ensure_ascii=False))
                            c["pairs (retry)"] += 1
                # the narrator's rewrite: the draft it replaced is the rejected side
                if REWRITE_MARK in user and ok is not None:
                    base, _, nudge = user.partition(REWRITE_MARK)
                    draft = by_prompt.get((task, base))
                    draft_ok = accepted(draft) if draft else None
                    if draft_ok is not None:
                        superseded.add(id(draft))
                        counts["reasons"][task][nudge_heads(nudge)] += 1
                        sys_text = system_for(task, system, prompts)
                        if sys_text is not None:
                            files[(split, task, "pairs")].append(json.dumps(
                                {"prompt": [{"role": "system", "content": sys_text}, {"role": "user", "content": base}],
                                 "chosen": [{"role": "assistant", "content": ok["raw"]}],
                                 "rejected": [{"role": "assistant", "content": draft_ok["raw"]}]}, ensure_ascii=False))
                            c["pairs (rewrite)"] += 1
                    user = base                           # the example is the original request answered well
                by_prompt[(task, user)] = call
            for call in calls:
                task = call[0]["task"]
                c = counts[split][task]
                ok = accepted(call)
                if ok is None or id(call) in superseded:
                    if ok is not None:
                        c["dropped: draft a rewrite replaced"] += 1
                    continue
                system, user = prompt_of(call)
                if REWRITE_MARK in user:
                    user = user.partition(REWRITE_MARK)[0]
                sys_text = system_for(task, system, prompts)
                if sys_text is None:
                    c["dropped: system prompt shortened in the log"] += 1
                    continue
                why = habits(task, ok["raw"])
                if why:
                    c[f"dropped: {why}"] += 1
                    continue
                files[(split, task, "sft")].append(json.dumps(
                    {"messages": [{"role": "system", "content": sys_text}, {"role": "user", "content": user}, {"role": "assistant", "content": ok["raw"]}]},
                    ensure_ascii=False))
                c["sft"] += 1
                if ok.get("attempt", 0) == 0:
                    c["sft (first try)"] += 1
    for (split, task, kind), lines in files.items():
        d = out / split
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{task}.{kind}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.md").write_text(summary(counts, prompts), encoding="utf-8")
    return counts


def summary(counts: dict, prompts: str) -> str:
    lines = [f"# LoRA data ({prompts} prompts)", ""]
    for split in ("train", "eval"):
        lines.append(f"## {split}: {len(counts['runs'][split])} run(s)")
        lines.append("")
        for r in counts["runs"][split]:
            lines.append(f"- {r}")
        lines.append("")
        lines.append("| Task | Calls | Learned from (first try) | Pairs retry | Pairs rewrite | Dropped |")
        lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
        for task, c in sorted(counts[split].items()):
            dropped = ", ".join(f"{k.removeprefix('dropped: ')} {v}" for k, v in sorted(c.items()) if k.startswith("dropped"))
            lines.append(f"| {task} | {c['calls']} | {c['sft']} ({c['sft (first try)']}) | {c['pairs (retry)']} | {c['pairs (rewrite)']} | {dropped} |")
        lines.append("")
    lines.append("## What the pairs teach (rejection reasons, both splits)")
    lines.append("")
    for task, cnt in sorted(counts["reasons"].items()):
        lines.append(f"- **{task}**: " + "; ".join(f"{k} ({v})" for k, v in cnt.most_common(8)))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- command line

def run_dirs(args) -> tuple[list[Path], list[Path]]:
    runs = [Path(p) for p in args.runs]
    if args.runs_dir:
        runs += sorted(p for p in Path(args.runs_dir).iterdir() if (p / "llm_calls.jsonl").exists())
    runs = sorted({r.resolve() for r in runs}, key=lambda p: p.name)
    holdout = [Path(args.holdout).resolve()] if args.holdout else ([] if args.no_holdout or len(runs) < 2 else [runs[-1]])
    runs = [r for r in runs if r not in holdout]
    return runs, holdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", nargs="*", help="night-run folders (each holds llm_calls.jsonl)")
    ap.add_argument("--runs-dir", help="a folder of night runs: every subfolder with a log")
    ap.add_argument("--out", default="lora/data")
    ap.add_argument("--holdout", help="the run kept for evaluation (default: the newest, when there are two or more)")
    ap.add_argument("--no-holdout", action="store_true")
    ap.add_argument("--prompts", choices=("short", "full"), default="short")
    ap.add_argument("--tasks", help="comma-separated; default from data/rules/lora.yaml")
    args = ap.parse_args(argv)
    runs, holdout = run_dirs(args)
    if not runs and not holdout:
        print("no runs: name night-run folders, or --runs-dir logs/nightrun")
        return 2
    counts = build(runs, holdout, Path(args.out), args.prompts, [t.strip() for t in args.tasks.split(",")] if args.tasks else None)
    print(summary(counts, args.prompts))
    print(f"written under {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
