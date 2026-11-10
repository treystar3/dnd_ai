"""(f575) The prose measures, per task, from any model call log (logs/llm_calls.jsonl, a night run's, live_check's): how much the writing
repeats itself. Used to hold a prose change against a baseline (docs/design/09, section A).

    python tools/prose_measure.py LOG [LOG...]                       the table, and sample passages
    python tools/prose_measure.py LOG... --json out.json             the numbers, kept to compare against
    python tools/prose_measure.py LOG... --against base.json         the table beside a kept baseline, with the change
    python tools/prose_measure.py LOG... --samples 4 --seed 1        how many sample passages a task (0: none), picked by a seed

Per task (narrate, combat_narrate, combat_opening, combat_aftermath, exchange, dialogue_frame, npc_conversation, hire_chat, and any other
whose answer carries prose), over the answers the game accepted (a row with no error):
    passages, words
    repeated phrases   distinct five-word runs found in two or more passages, per 1,000 words (scenes/voice.py stale_phrases' unit)
    repeated sentences sentences of four or more words said again in another passage, per 1,000 words
    shared openings    the share of passages whose first three words open another passage too
    worn words         words of the kind that wear (engine/worn.py: the seed words and the suffixed ones) found in 4 or more passages, the
                       count of such words, their uses per 1,000 words, and the most used
    stock phrases      scenes/voice.py STALE's phrases, per 1,000 words
Lower is better for every measure. No model is needed: it reads what was written."""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROSE = {"narrate": ("text",), "combat_narrate": ("text",), "combat_opening": ("text",), "combat_aftermath": ("text",),
         "npc_conversation": ("speech",), "hire_chat": ("speech",), "mentor_chat": ("speech",), "dialogue_frame": ("before", "after")}
ORDER = ["narrate", "combat_opening", "combat_narrate", "combat_aftermath", "exchange", "dialogue_frame", "npc_conversation", "hire_chat",
         "mentor_chat"]
MEASURES = [("passages", "passages", "d"), ("words", "words", "d"), ("phrases_per_k", "repeated phrases /1k", ".2f"),
            ("sentences_per_k", "repeated sentences /1k", ".2f"), ("openings_share", "shared openings", ".0%"),
            ("worn_count", "worn words", "d"), ("worn_per_k", "worn uses /1k", ".2f"), ("stock_per_k", "stock phrases /1k", ".2f")]
_WORDS = re.compile(r"[a-z']+")


def prose_of(task: str, answer) -> str:
    """The prose a task's answer carries: the narration's text, a reply's speech, a frame's before and after, an exchange's lines."""
    if isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except ValueError:
            return ""
    if not isinstance(answer, dict):
        return ""
    if task == "exchange":
        return " ".join(str(l.get("text", "")) for l in answer.get("lines") or [] if isinstance(l, dict)).strip()
    keys = PROSE.get(task) or next(((k,) for k in ("speech", "text") if isinstance(answer.get(k), str)), ())
    return " ".join(str(answer.get(k, "")) for k in keys).strip()


def load(paths: list[str]) -> dict[str, list[str]]:
    """Every accepted passage, by task, in the order written."""
    out: dict[str, list[str]] = defaultdict(list)
    for p in paths:
        if str(p).endswith(".gz"):                               # a kept log, compressed
            import gzip
            text = gzip.open(p, "rt", encoding="utf-8", errors="replace").read()
        else:
            text = Path(p).read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("error") or not r.get("task"):
                continue
            text = prose_of(r["task"], r.get("raw", r.get("answer")))
            if text:
                out[r["task"]].append(text)
    return dict(out)


def _shingles(text: str, n: int = 5) -> set[str]:
    w = _WORDS.findall(text.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def _sentences(text: str) -> list[str]:
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        norm = " ".join(_WORDS.findall(s.lower()))
        if len(norm.split()) >= 4:
            out.append(norm)
    return out


def _opening(text: str) -> str:
    return " ".join(_WORDS.findall(text.lower())[:3])


def measure(passages: list[str]) -> dict:
    """The measures of one task's passages."""
    from engine import worn as worn_mod
    from scenes.voice import STALE
    words = sum(len(_WORDS.findall(p.lower())) for p in passages)
    per_k = 1000.0 / max(1, words)
    runs = Counter(s for p in passages for s in _shingles(p))
    repeated = {s: n for s, n in runs.items() if n >= 2}
    sent = Counter(s for p in passages for s in set(_sentences(p)))
    again = {s: n for s, n in sent.items() if n >= 2}
    opens = Counter(_opening(p) for p in passages if _opening(p))
    shared = sum(n for o, n in opens.items() if n >= 2)
    watch = worn_mod.Watch(keep=max(1, len(passages)))
    for p in passages:
        watch.add(p)
    counts = watch.counts()
    least = int(worn_mod.W.get("least", 4))
    worn = sorted(((w, n) for w, n in counts.items() if n >= least), key=lambda kv: (-kv[1], kv[0]))
    stock = sum(p.lower().count(s) for p in passages for s in STALE)
    return {"passages": len(passages), "words": words,
            "phrases_per_k": round(len(repeated) * per_k, 3), "sentences_per_k": round(sum(n - 1 for n in again.values()) * per_k, 3),
            "openings_share": round(shared / max(1, len(passages)), 3),
            "worn_count": len(worn), "worn_per_k": round(sum(n for _, n in worn) * per_k, 3), "stock_per_k": round(stock * per_k, 3),
            "top_phrases": [s for s, _ in sorted(repeated.items(), key=lambda kv: (-kv[1], kv[0]))[:8]],
            "top_sentences": [s for s, _ in sorted(again.items(), key=lambda kv: (-kv[1], kv[0]))[:5]],
            "top_openings": [o for o, n in opens.most_common(5) if n >= 2], "top_worn": [w for w, _ in worn[:8]]}


def measure_all(by_task: dict[str, list[str]]) -> dict[str, dict]:
    tasks = [t for t in ORDER if t in by_task] + sorted(t for t in by_task if t not in ORDER)
    return {t: measure(by_task[t]) for t in tasks}


def _fmt(v, f: str) -> str:
    return format(v, f) if v is not None else "-"


def table(result: dict[str, dict], base: dict[str, dict] | None = None) -> list[str]:
    head = ["task"] + [label for _, label, _ in MEASURES]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for task, m in result.items():
        cells = [task]
        for key, _label, f in MEASURES:
            cell = _fmt(m.get(key), f)
            b = (base or {}).get(task, {}).get(key)
            if base is not None and b is not None and key not in ("passages", "words"):
                d = m[key] - b
                cell += f" ({'+' if d >= 0 else ''}{_fmt(d, f)})"
            cells.append(cell)
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def details(result: dict[str, dict]) -> list[str]:
    out = []
    for task, m in result.items():
        bits = [f"repeated phrases: {', '.join(m['top_phrases'][:5]) or 'none'}",
                f"openings: {', '.join(m['top_openings']) or 'none'}", f"worn: {', '.join(m['top_worn']) or 'none'}"]
        out.append(f"- **{task}**: " + "; ".join(bits))
    return out


def samples(by_task: dict[str, list[str]], n: int, seed: int) -> list[str]:
    out = []
    for task in [t for t in ORDER if t in by_task] + sorted(t for t in by_task if t not in ORDER):
        rng = random.Random(f"{seed}:{task}")
        picked = rng.sample(by_task[task], min(n, len(by_task[task])))
        out.append(f"\n### {task}")
        out += [f"> {p}\n" for p in picked]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--json", default="")
    ap.add_argument("--against", default="")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    by_task = load(a.logs)
    if not by_task:
        print("no prose in these logs")
        return 1
    result = measure_all(by_task)
    base = json.loads(Path(a.against).read_text(encoding="utf-8"))["tasks"] if a.against else None
    print("\n".join(table(result, base) + [""] + details(result)))
    if a.samples:
        print("\n## Sample passages" + "\n".join(samples(by_task, a.samples, a.seed)))
    if a.json:
        Path(a.json).write_text(json.dumps({"logs": a.logs, "tasks": result}, indent=1), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
