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
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


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


REFUSAL_WORDS = re.compile(r"\b(closed|not|no|nothing|can't|cannot|isn't|aren't|don't|nowhere|already|too|need|unknown|refuse)\b", re.I)
PRONOUNS = {"he": re.compile(r"\b(he|him|his|himself)\b", re.I), "she": re.compile(r"\b(she|her|hers|herself)\b", re.I)}


def _prose(calls: list[dict]) -> list[tuple[int, str, str]]:
    """(turn, task, text) for the prose of every accepted answer."""
    from engine import hygiene
    out = []
    for r in calls:
        if r.get("error") or not r.get("raw") or r.get("task") == "player_line":     # the bot's own lines are not the game's
            continue
        try:
            value = json.loads(r["raw"])
        except ValueError:
            continue
        for t in hygiene.prose_of(value):
            if t:
                out.append((int(r.get("turn") or 0), r.get("task", "?"), t))
    return out


def consistency_table(rows: list[dict], calls: list[dict], info: dict) -> list[str]:
    """(f391) What a reader of the night would trip over, counted: the machinery in the text, refusals said again and again, what the
    game believed against where the player was, captives held, people who left the party and were never spoken of again, and companions
    called by the wrong pronoun or people. Rough by design (a sentence may be about two people); the counts are for comparing nights."""
    from engine import hygiene
    lines = ["| Measure | Value |", "| --- | --- |"]
    reasons = {v.split(":")[0][:40]: k for k, v in hygiene.H["reasons"].items()}
    at_model = collections.Counter()
    for r in calls:
        err = str(r.get("error") or "")
        hit = next((k for head, k in reasons.items() if err.startswith(head)), None)
        if hit:
            at_model[hit] += 1
        elif err.startswith("write every word in English"):
            at_model["script"] += 1
    screen = info.get("hygiene") or {}
    lines.append(f"| Machinery sent back by the gateway | {sum(at_model.values())}" + (f" ({', '.join(f'{k} {v}' for k, v in at_model.most_common())})" if at_model else "") + " |")
    lines.append(f"| Machinery mended at the screen | {sum(screen.values())}" + (f" ({', '.join(f'{k} {v}' for k, v in sorted(screen.items()))})" if screen else "") + " |")
    keyed = []
    for r in rows:
        keys = {re.sub(r"\d+", "#", n.lower())[:90] for n in r.get("notes") or [] if REFUSAL_WORDS.search(n)}
        keyed.append(keys)
    longest, worst, again = 0, "", 0
    run: dict[str, int] = {}
    for i, keys in enumerate(keyed):
        run = {k: run.get(k, 0) + 1 for k in keys}
        for k, n in run.items():
            if n > longest:
                longest, worst = n, k
        if any(sum(1 for prev in keyed[max(0, i - 10):i] if k in prev) >= 2 for k in keys):
            again += 1
    lines.append(f"| Turns ending on a refusal said at least twice in the last ten | {again} |")
    lines.append(f"| Longest run of one refusal | {longest}" + (f' ("{worst[:70]}")' if worst else "") + " |")
    lines.append(f"| Goals the bot gave up on meeting the same refusal twice | {(info.get('bot') or {}).get('blocked', 0)} |")
    lines += goal_lines(rows, info)
    states = [r.get("state") or {} for r in rows]
    stale = sum(1 for s in states if s.get("delve") and not s.get("at_dungeon"))
    held, run_hold = 0, 0
    for s in states:
        run_hold = run_hold + 1 if s.get("party") and s.get("party_mode", "with") != "with" else 0
        held = max(held, run_hold)
    lines.append(f"| Turns the game believed the player was in a dungeon they had left | {stale} |")
    lines.append(f"| Longest run of the party held back | {held} turns |")
    lines.append(f"| Captives held at once (most) / longest held | {max((s.get('prisoners', 0) for s in states), default=0)} / "
                 f"{max((s.get('prisoner_days', 0) for s in states), default=0)} days |")
    prose = _prose(calls)
    left = []
    for a, b in zip(rows, rows[1:]):
        gone = set((a.get("state") or {}).get("party") or []) - set((b.get("state") or {}).get("party") or [])
        for name in gone:
            first = name.split()[0]
            after = sum(1 for t, _, text in prose if t > int(b.get("turn") or 0) and re.search(rf"\b{re.escape(first)}\b", text))
            left.append(f"{name} (turn {b.get('turn')}): named {after} times after")
    lines.append(f"| Left the party, and named afterwards | {'; '.join(left) if left else 'nobody left'} |")
    cast = info.get("cast") or {}
    firsts = {n.split()[0]: n for n in cast}
    from engine import look
    peoples = {spec["word"]: p for p, spec in look.L["peoples"].items()}
    wrong_pr = collections.Counter()
    wrong_pe = collections.Counter()
    for _, task, text in prose:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            named = [n for f, n in firsts.items() if re.search(rf"\b{re.escape(f)}\b", sent)]
            if len(named) != 1:
                continue
            who = cast[named[0]]
            pr = who.get("pronoun")
            other = {"he": "she", "she": "he"}.get(pr)
            if other and PRONOUNS[other].search(sent) and not PRONOUNS[pr].search(sent):
                wrong_pr[(named[0], task)] += 1
            for word, pid in peoples.items():
                if who.get("people") and pid != who["people"] and re.search(rf"\b{re.escape(word)}\b", sent, re.I):
                    wrong_pe[(named[0], task)] += 1
    def top(c):
        return "; ".join(f"{n} in {t} {v}" for (n, t), v in c.most_common(4))
    lines.append(f"| Companion sentences with the other gender's pronoun | {sum(wrong_pr.values())}" + (f" ({top(wrong_pr)})" if wrong_pr else "") + " |")
    lines.append(f"| Companion sentences naming another people | {sum(wrong_pe.values())}" + (f" ({top(wrong_pe)})" if wrong_pe else "") + " |")
    return lines


def goal_lines(rows: list[dict], info: dict) -> list[str]:
    """(f393) GOAL.md, counted: facades met (the player reached for something the place or the passage named, and nothing was there),
    dead ends (looked for something unnamed, found nothing), attempts the game made room for (the turn's record: made), attempts it
    said no to in the world (refused), and additions per hour of play. The refusals log and each turn's record are the sources."""
    refs = info.get("_refusals") or []
    kinds = collections.Counter(r.get("kind") for r in refs)
    outcomes = collections.Counter(o.get("kind") for r in rows for o in (r.get("outcomes") or []))
    hours = float(info.get("hours") or 0) or 1.0
    return [f"| Facades met / dead ends | {kinds.get('facade', 0)} / {kinds.get('dead_end', 0)} |",
            f"| Attempts the world made room for / said no to in the world | {outcomes.get('made', 0)} / {kinds.get('refused', 0)} |",
            f"| Additions to the world per hour | {outcomes.get('made', 0) / hours:.1f} |"]


def summarise(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    calls = load(run_dir / "llm_calls.jsonl")
    turns = load(run_dir / "turns.jsonl")
    pulse = load(run_dir / "pulse.jsonl")
    game_turns = load(run_dir / "turns_game.jsonl")
    info = {}
    if (run_dir / "run.json").exists():
        info = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    info["_refusals"] = load(run_dir / "refusals.jsonl")          # (f393)
    lines = [f"# Night run: {run_dir.name}", ""]
    if info:
        lines.append(f"{info.get('character', '?')}, {info.get('class', '?')}, level {info.get('level', '?')}, {info.get('deaths', 0)} deaths; "
                     f"{info.get('turns', len(turns))} turns in {info.get('hours', '?')} hours; stopped: {info.get('reason', '?')}; "
                     + (f"starting as {info['start']}, playing as {info.get('persona', '?')}; " if info.get("start") else "") +
                     f"model {info.get('model', '?')}" + (" (stand-in)" if info.get("stub") else "")
                     + (f", warm calls {(info.get('sampling') or {}).get('temp_add', 0):+g} temperature and {(info.get('sampling') or {}).get('repeat_add', 0):+g} repeat penalty"
                        if any((info.get("sampling") or {}).values()) else "") + ".")
        lines.append("")
    lines += ["## Turns", ""]
    lines += turns_table(turns) if turns else ["No turns recorded."]
    if game_turns:
        handled = collections.Counter(r.get("handled_by", "?") for r in game_turns)
        lines += ["", "Lines by what read them: " + ", ".join(f"{k} {n}" for k, n in handled.most_common())]
    lines += ["", "## Play", ""] + play_table(turns, info, pulse) if turns else []
    if turns:
        lines += ["", "## Consistency", ""] + consistency_table(turns, calls, info)
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
