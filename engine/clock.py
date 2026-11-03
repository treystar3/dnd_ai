"""Game time. The clock counts minutes since the player first woke.

Every action costs time; the engine advances the clock, never the model.
All values here are tuning knobs.
"""

WAKE_HOUR = 8
MINUTES_PER_DAY = 24 * 60

LOOK_MINUTES = 2
TALK_MINUTES = 2
OTHER_MINUTES = 5
DEFAULT_WAIT_MINUTES = 30
MAX_WAIT_MINUTES = 16 * 60

PERIODS = [
    (0, "deep night"),
    (4, "before dawn"),
    (6, "dawn"),
    (8, "morning"),
    (11, "midday"),
    (13, "afternoon"),
    (17, "evening"),
    (20, "night"),
    (23, "deep night"),
]
PERIOD_NAMES = ["before dawn", "dawn", "morning", "midday", "afternoon", "evening", "night", "deep night"]
DARK_PERIODS = {"deep night", "before dawn", "night"}


def absolute(minutes: int) -> int:
    return WAKE_HOUR * 60 + minutes


def day(minutes: int) -> int:
    return absolute(minutes) // MINUTES_PER_DAY + 1


def hour(minutes: int) -> float:
    return (absolute(minutes) % MINUTES_PER_DAY) / 60


def period(minutes: int) -> str:
    h = hour(minutes)
    name = PERIODS[0][1]
    for start, label in PERIODS:
        if h >= start:
            name = label
    return name


def is_dark(minutes: int) -> bool:
    return period(minutes) in DARK_PERIODS


def minutes_until(minutes: int, target_period: str) -> int:
    """Minutes from now until the next start of target_period."""
    starts = sorted({s for s, label in PERIODS if label == target_period})
    now = absolute(minutes) % MINUTES_PER_DAY
    waits = [(s * 60 - now) % MINUTES_PER_DAY or MINUTES_PER_DAY for s in starts]
    return min(waits)


def in_hours(minutes: int, hours: tuple[int, int]) -> bool:
    """hours=(start, end); end may exceed 24 for past midnight, e.g. (7, 25) is 7:00 to 1:00."""
    start, end = hours
    h = hour(minutes)
    return start <= h < end or start <= h + 24 < end


def header(minutes: int, place_name: str) -> str:
    return f"{ordinal(day(minutes))} Day · {period(minutes).capitalize()} · {place_name}"


def describe_duration(m: int) -> str:
    if m < 60:
        return f"{m} minutes"
    hours, rest = divmod(m, 60)
    text = f"{hours} hour{'s' if hours != 1 else ''}"
    return text + (f" {rest} minutes" if rest else "")


def walk_words(m: int) -> str:
    """(f349) A distance the way a local says it: 'an hour's walk', 'a morning's walk', 'two days on the road'. The player's own map keeps
    its figures (describe_duration); nobody who lives here counts minutes."""
    if m < 20:
        return "a few minutes' walk"
    if m < 45:
        return "a short walk"
    if m < 90:
        return "an hour's walk"
    if m < 150:
        return "a couple of hours on foot"
    if m < 330:
        return "a morning's walk"
    if m < 480:
        return "half a day on foot"
    if m < 900:
        return "a day on the road"
    days = max(2, round(m / 600))
    names = ["two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
    return f"{names[days - 2]} days on the road" if days - 2 < len(names) else "a fortnight or more on the road"


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def clock_time(minutes: int) -> str:
    total = absolute(minutes) % MINUTES_PER_DAY
    h, m = divmod(total, 60)
    return f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def season(minutes: int) -> str:
    """The season, counting from the first day of the first season."""
    from engine.pulse import P
    s = P["seasons"]
    return s["order"][((day(minutes) - 1) // s["days_each"]) % len(s["order"])]


# ---- (f477, G1) how long ago, the way people put it (data/rules/time_words.yaml): by calendar day and season, never a day number
_TW: dict | None = None


def time_words() -> dict:
    global _TW
    if _TW is None:
        import yaml
        from pathlib import Path
        _TW = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "time_words.yaml").read_text(encoding="utf-8"))
    return _TW


def ago(then: int, now: int, who: str = "") -> str:
    """How long since the minute `then`, counted in calendar days ("yesterday" is the day before, whatever the hour), in the words of
    time_words.yaml. `who`: the one speaking; the same speaker puts the same span the same way every time (the wording is picked by a
    hash of who and the span; with no speaker, the first wording)."""
    days = max(0, day(now) - day(then))
    return ago_days(days, then, who)


def ago_day(then_day: int, now: int, who: str = "") -> str:
    """The same, from a calendar day (a memory keeps its day, not its minute)."""
    return ago_days(max(0, day(now) - int(then_day)), max(0, (int(then_day) - 1) * MINUTES_PER_DAY - WAKE_HOUR * 60), who)


def ago_days(days: int, then: int, who: str = "") -> str:
    import hashlib
    W = time_words()
    band = [b for b in W["bands"] if days >= b["from"]][-1]
    say = band["say"]
    k = int(hashlib.sha256(f"{who}:{band['from']}".encode("utf-8")).hexdigest(), 16) % len(say) if who else 0
    return say[k].format(n=(W.get("numbers") or {}).get(days, "some"), season=season(then))


def now_line(minutes: int, weather_word: str = "") -> str:
    """(f477) The hour as a person would know it: the part of the day, whether it is dark, the season, the weather. No day number."""
    parts = [period(minutes) + (", dark" if is_dark(minutes) and "night" not in period(minutes) else ""), season(minutes)]
    if weather_word:
        parts.append(f"weather: {weather_word}")
    return ", ".join(parts)


def time_words_problems(W: dict | None = None) -> list[str]:
    """(f477) The startup check: bands ascending from 0, each with a wording, no digits and no dashes in any (a person says "three days
    ago", never "3 days" or "day 12"), and every {n} band within the numbers given."""
    import re
    W = time_words() if W is None else W
    bad = []
    bands = W.get("bands") or []
    froms = [b.get("from") for b in bands]
    if not bands or froms[0] != 0 or any(not isinstance(f, int) for f in froms) or froms != sorted(set(froms)):
        bad.append("time_words.yaml bands: need whole-number `from`s, ascending from 0")
    nums = W.get("numbers") or {}
    for i, b in enumerate(bands):
        if not b.get("say"):
            bad.append(f"time_words.yaml bands[{i}]: needs at least one wording")
        for w in b.get("say") or []:
            if re.search(r"\d|[-\u2013\u2014]", str(w)):
                bad.append(f"time_words.yaml bands[{i}]: '{w}' has a digit or a dash")
            if "{n}" in str(w):
                top = froms[i + 1] if i + 1 < len(froms) else None
                need = range(b["from"], top) if top is not None else []
                if top is None or any(n not in nums for n in need):
                    bad.append(f"time_words.yaml bands[{i}]: '{w}' says {{n}}, but the numbers do not cover every day of its band")
    return bad
