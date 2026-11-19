"""(f661) What the engine decided against or beside what the player asked, said to the player in the game's own voice: one line of
several for each kind (data/rules/told.yaml), drawn without a die so a replay reads the same, its facts filled in. The narrator is
still told by the code that decided; this line does not depend on the passage saying it."""
from pathlib import Path

from core import yamlio

T = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "told.yaml").read_text(encoding="utf-8"))
WORDS = ("flight_words",)                  # tables of words, not lines


def say(kind: str, n: int = 0, **facts) -> str:
    """One line of this kind, the n-th of its lines (round, turn or minute: any count that moves), with the facts in it."""
    lines = T[kind]
    s = lines[n % len(lines)].format(**facts)
    return s[:1].upper() + s[1:]


def odds(chance: float) -> str:
    """A chance in percent, in words."""
    return next((w for top, w in T["flight_words"] if chance <= top), T["flight_words"][-1][1])


def problems(t: dict | None = None) -> list[str]:
    """Start-up check: every kind is a list of lines, no dash in any, the words' bands rising to 100."""
    t = T if t is None else t
    bad = []
    for kind, lines in t.items():
        if kind in WORDS:
            tops = [top for top, _ in lines]
            if tops != sorted(tops) or tops[-1] != 100:
                bad.append(f"told.yaml {kind}: the bands must rise to 100")
            continue
        if not lines or not all(isinstance(l, str) and l.strip() for l in lines):
            bad.append(f"told.yaml {kind}: no lines")
        if any(chr(0x2014) in l or chr(0x2013) in l for l in lines):
            bad.append(f"told.yaml {kind}: a dash in a line")
    return bad
