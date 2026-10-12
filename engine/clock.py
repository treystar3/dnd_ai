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
