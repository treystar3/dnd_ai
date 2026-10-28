"""What the model's calls and the game's turns cost, from the logs.

    python tools/latency.py RUN_DIR                    a night run's folder (tools/nightrun.py): calls and turns, written to RUN_DIR/summary.md
    python tools/latency.py --calls logs/llm_calls.jsonl   any call log on its own (a real session's, for instance)

The call log carries one row per attempt: its task, its wall seconds and, since the gateway began keeping them, Ollama's own
counts (`tokens`: prompt and written tokens, the milliseconds each took, a model load). A night run adds turns.jsonl, one row per
typed line with its wall time, the time to its first word, and the calls it took.
"""
from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path


def load(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    return vs[min(len(vs) - 1, int(round(q * (len(vs) - 1))))]


def fmt(x: float, places: int = 1) -> str:
    return f"{x:.{places}f}"


def calls_table(rows: list[dict]) -> list[str]:
    """Per task: calls, how many needed a retry, seconds per attempt, tokens, speeds, loads. Sorted by the time spent."""
    by: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        by[r.get("task", "?")].append(r)
    lines = ["| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    table = []
    for task, rs in by.items():
        calls = sum(1 for r in rs if r.get("attempt", 0) == 0) or len(rs)
        retried = sum(1 for r in rs if r.get("attempt", 0) > 0)
        rejected = sum(1 for r in rs if r.get("error"))
        secs = [float(r.get("seconds") or 0) for r in rs]
        toks = [r["tokens"] for r in rs if isinstance(r.get("tokens"), dict)]
        prompt = [t.get("prompt", 0) for t in toks]
        out = [t.get("out", 0) for t in toks]
        read_s = sum(t.get("read_ms", 0) for t in toks) / 1000
        write_s = sum(t.get("write_ms", 0) for t in toks) / 1000
        loads = sum(1 for t in toks if t.get("load_ms", 0) > 500)
        table.append((sum(secs), f"| {task} | {calls} | {retried} | {rejected} | {fmt(pct(secs, .5))} | {fmt(pct(secs, .9))} | "
                      f"{int(statistics.median(prompt)) if prompt else '-'} | {int(statistics.median(out)) if out else '-'} | "
                      f"{fmt(sum(prompt) / read_s, 0) if read_s else '-'} | {fmt(sum(out) / write_s, 1) if write_s else '-'} | {loads} | {fmt(sum(secs), 0)} |"))
    table.sort(key=lambda t: -t[0])
    lines += [t[1] for t in table]
    total = sum(float(r.get("seconds") or 0) for r in rows)
    lines.append(f"\n{len(rows)} attempts for {sum(1 for r in rows if r.get('attempt', 0) == 0)} calls, {fmt(total / 60, 1)} minutes in the model in all.")
    if not any(isinstance(r.get("tokens"), dict) for r in rows):
        lines.append("No token counts in this log: it was written before the gateway kept Ollama's counts, or by a stand-in model.")
    return lines


def turns_table(rows: list[dict]) -> list[str]:
    """Per kind of line the bot typed: how many, how long they took, how long to the first word, calls per turn."""
    by: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        by[r.get("kind", "?")].append(r)
    lines = ["| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for kind, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        secs = [float(r.get("seconds") or 0) for r in rs]
        first = [float(r["first_word"]) for r in rs if r.get("first_word") is not None]
        calls = [int(r.get("chat_calls") or 0) for r in rs]
        model = [float(r.get("chat_seconds") or 0) for r in rs]
        lines.append(f"| {kind} | {len(rs)} | {fmt(pct(secs, .5))} | {fmt(pct(secs, .9))} | {fmt(pct(first, .5)) if first else '-'} | "
                     f"{fmt(pct(first, .9)) if first else '-'} | {fmt(statistics.mean(calls), 1) if calls else '-'} | "
                     f"{fmt(statistics.mean(model), 1) if model else '-'} | {sum(int(r.get('retries') or 0) for r in rs)} | "
                     f"{sum(1 for r in rs if r.get('hesitated') or r.get('error'))} |")
    secs = [float(r.get("seconds") or 0) for r in rows]
    model = sum(float(r.get("chat_seconds") or 0) for r in rows)
    embeds = sum(int(r.get("embed_calls") or 0) for r in rows)
    embed_s = sum(float(r.get("embed_seconds") or 0) for r in rows)
    lines.append(f"\n{len(rows)} turns in {fmt(sum(secs) / 60, 1)} minutes; {fmt(100 * model / sum(secs), 0) if sum(secs) else '-'}% of it in the model; "
                 f"{embeds} embedding calls taking {fmt(embed_s, 1)} s; {sum(int(r.get('background_calls') or 0) for r in rows)} calls on background threads.")
    slow = sorted(rows, key=lambda r: -float(r.get("seconds") or 0))[:5]
    if slow:
        lines.append("\nSlowest turns:")
        for r in slow:
            lines.append(f"- {fmt(float(r.get('seconds') or 0))} s, {r.get('kind')}, {r.get('chat_calls')} calls, at {r.get('where')}: \"{r.get('text', '')[:70]}\"")
    return lines


def play_table(rows: list[dict], info: dict, pulse: list[dict]) -> list[str]:
    """(f368) How player-like the run was: the measures the night bot's goals and words are judged by (tools/nightbot.py)."""
    n = len(rows)
    share = lambda a, b: f"{a} of {b} ({round(100 * a / b)}%)" if b else "-"
    texts = [r.get("text", "") for r in rows]
    src = collections.Counter(r.get("source") for r in rows if r.get("source"))
    with_passage = [r for r in rows if "refers" in r]
    talk = [r for r in rows if r.get("kind") == "talk"]
    bot = info.get("bot") or {}
    done, dropped = bot.get("goals_done") or {}, bot.get("goals_dropped") or {}
    goals = collections.Counter((r.get("goal") or "-").split(":")[0] for r in rows)
    ended = sum(1 for p in pulse if p.get("kind") == "end" and p.get("how") == "player")
    waits = sum(1 for r in rows if r.get("kind") == "wait")
    lines = ["| Measure | Value |", "| --- | --- |",
             f"| Distinct lines | {share(len(set(texts)), n)} |",
             f"| Lines the model wrote | {src.get('model', 0)} (template {src.get('template', 0)}; model failed {bot.get('model_failed', 0)}, {fmt(float(bot.get('model_seconds') or 0), 0)} s) |",
             f"| Lines picking up the passage before | {share(sum(1 for r in with_passage if r.get('refers')), len(with_passage))}; in talk {share(sum(1 for r in talk if r.get('refers')), len(talk))} |",
             f"| Contracts taken / finished | {bot.get('contracts_taken', 0)} / {bot.get('contracts_done', 0)} |",
             f"| Situations met / followed / ended by the player | {bot.get('doors_seen', 0)} / {bot.get('doors_followed', 0)} / {ended} |",
             f"| Goals finished / given up | {sum(done.values())} / {sum(dropped.values())}"
             + (" (" + ", ".join(f"{k} {done.get(k, 0)}/{dropped.get(k, 0)}" for k in sorted(set(done) | set(dropped))) + ")" if done or dropped else "") + " |",
             f"| Deaths (above the level band) | {info.get('deaths', bot.get('deaths', 0))} ({bot.get('deaths_above_band', 0)}) |",
             f"| Fights | {bot.get('fights', sum(1 for r in rows if r.get('kind') == 'fight'))} |",
             f"| Waits | {share(waits, n)} |",
             f"| Places visited | {bot.get('places', len({r.get('where') for r in rows}))} |"]
    if goals:
        lines.append("\nTurns by goal: " + ", ".join(f"{k} {v}" for k, v in goals.most_common()))
    return lines


def summarise(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    calls = load(run_dir / "llm_calls.jsonl")
    turns = load(run_dir / "turns.jsonl")
    pulse = load(run_dir / "pulse.jsonl")
    game_turns = load(run_dir / "turns_game.jsonl")
    info = {}
    if (run_dir / "run.json").exists():
        info = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    lines = [f"# Night run: {run_dir.name}", ""]
    if info:
        lines.append(f"{info.get('character', '?')}, {info.get('class', '?')}, level {info.get('level', '?')}, {info.get('deaths', 0)} deaths; "
                     f"{info.get('turns', len(turns))} turns in {info.get('hours', '?')} hours; stopped: {info.get('reason', '?')}; "
                     + (f"starting as {info['start']}, playing as {info.get('persona', '?')}; " if info.get("start") else "") +
                     f"model {info.get('model', '?')}" + (" (stand-in)" if info.get("stub") else "") + ".")
        lines.append("")
    lines += ["## Turns", ""]
    lines += turns_table(turns) if turns else ["No turns recorded."]
    if game_turns:
        handled = collections.Counter(r.get("handled_by", "?") for r in game_turns)
        lines += ["", "Lines by what read them: " + ", ".join(f"{k} {n}" for k, n in handled.most_common())]
    lines += ["", "## Play", ""] + play_table(turns, info, pulse) if turns else []
    lines += ["", "## Calls by task", ""]
    lines += calls_table(calls) if calls else ["No calls recorded."]
    text = "\n".join(lines) + "\n"
    (run_dir / "summary.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--calls":
        rows = load(Path(args[1] if len(args) > 1 else "logs/llm_calls.jsonl"))
        print("\n".join(calls_table(rows)) if rows else "No calls in that log.")
        return
    print(summarise(Path(args[0])))


if __name__ == "__main__":
    main()
