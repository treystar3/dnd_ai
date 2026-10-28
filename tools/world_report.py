"""(f355) What the world did in a run, per game day, from the pulse log (config.PULSE_LOG_PATH, logs/pulse.jsonl).

    python tools/world_report.py logs/pulse.jsonl
    python tools/world_report.py logs/nightrun/<when>/pulse.jsonl

Every pulse event (a situation started, a stage, an ending, a motive step, a drift pass) and every one the player met (a moment, a scene
walked into, someone sent to find them, a line about the room changing, people met on their routine, a re-telling) is one row. The
report says, day by day, how much happened and how much of it was within reach of the player: the numbers to tune the pulse by, and
the ones that say whether the world is alive where the player is."""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PLAYER_KINDS = ("scene", "summons", "moment", "stay", "routine", "retold", "retell_failed")


def load(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def day_of(t: int) -> int:
    try:
        from engine import clock
        return clock.day(int(t))
    except Exception:
        return int(t) // 1440 + 1


def summarise(path: Path) -> str:
    rows = load(path)
    if not rows:
        return ""
    by_day: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    started, ended = [], collections.Counter()
    for r in rows:
        k = r.get("kind", "?")
        d = day_of(r.get("t", 0))
        c = by_day[d]
        if k == "thread":
            c["started"] += 1
            if r.get("reach"):
                c["reach"] += 1
            started.append(r)
        elif k == "end":
            c["ended"] += 1
            ended[r.get("how", "?")] += 1
        elif k in ("stage", "motive", "moment", "stay", "routine"):
            c[k] += 1
        elif k in ("scene", "summons"):
            c["doors"] += 1
        elif k == "retold":
            c["retold"] += 1
        elif k == "retell_failed":
            c["retell_failed"] += 1
    days = sorted(by_day)
    tot = collections.Counter()
    for c in by_day.values():
        tot.update(c)
    n_days = max(1, days[-1] - days[0] + 1) if days else 1
    lines = ["## The world", ""]
    lines.append(f"Over {n_days} game days: {tot['started']} situations started ({tot['reach']} within reach of the player), {tot['stage']} stages advanced, "
                 f"{tot['ended']} ended ({ended['player']} by the player, {ended['settled']} settled by others, {ended['ignored']} left to their fallout), {tot['motive']} motive steps; "
                 f"the player met {tot['doors']} doors (a scene or a summons), {tot['moment']} moments, {tot['stay']} lines of the room changing, "
                 f"{tot['routine']} times people on their routine; re-tellings {tot['retold']} succeeded, {tot['retell_failed']} failed.")
    lines.append("")
    lines.append(f"Per game day within reach: {tot['reach'] / n_days:.2f} situations started, {tot['doors'] / n_days:.2f} doors, "
                 f"{tot['moment'] / n_days:.2f} moments, {tot['stay'] / n_days:.1f} room-changing lines.")
    lines += ["", "| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |", "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for d in days:
        c = by_day[d]
        lines.append(f"| {d} | {c['started']} ({c['reach']}) | {c['stage']} | {c['ended']} | {c['motive']} | {c['doors']} | {c['moment']} | {c['stay']} | {c['routine']} |")
    if started:
        lines += ["", "Situations started:"]
        for r in started[-40:]:
            text = r.get("text", "")[:110]
            tag = "" if text.startswith("[") else f"[{r.get('tier', '?')}{'' if r.get('made_by') != 'engine' else ', engine'}] "     # the row's own tag, once
            lines.append(f"- day {day_of(r.get('t', 0))}: {tag}{text}" + (" (within reach)" if r.get("reach") else ""))
    return "\n".join(lines) + "\n"


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    text = summarise(Path(args[0]))
    print(text if text else "No world events in that log.")


if __name__ == "__main__":
    main()
