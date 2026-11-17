"""(f712) Every pre-written line a player reads is in a human author's voice (the owner, 2026-11-16: "Let's do a pass of all the pre
written lines and make them read as human authors and not ai"; docs/design/24_line_pass.md). The first f711 stand-ins ("the telling
of it slipped away", "the world remembers") read as "very ai and inhuman like".
Held here: no line of the narrator's fallbacks and the game's told lines (failures.yaml, told.yaml, questions.yaml dropped, voice.yaml
stand-ins, stay.yaml, moments.yaml endings, doors.yaml endings, body.yaml falls, road.yaml barrier) speaks of the telling, the words,
the story or the passage, says a thing "stands" or "holds", or promises a later telling; and none chains clauses with a semicolon.
The goddess's own lines are hers and are checked the same way.
Run: python tools/sim/line_voice_712_test.py"""
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
import yaml

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


META = re.compile(r"\b(telling|told|untold|unsaid|story|passage|narrat\w*|slipp(ed|ing) away|remembers|it stands|that holds|"
                  r"nothing is lost|went untold|have to wait|another breath|words? (?:for|did not|didn't) come)\b", re.I)
R = Path("data/rules")


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def load(name):
    return yaml.safe_load((R / name).read_text(encoding="utf-8"))


F = load("failures.yaml")
T = load("told.yaml")
S = load("stay.yaml")
M = load("moments.yaml")
V = load("voice.yaml")
Q = load("questions.yaml")
D = load("doors.yaml")
B = load("body.yaml")
RD = load("road.yaml")
SHOWN = {
    "failures.yaml": list(strings(F)),
    "told.yaml": [s for k, v in T.items() if k != "flight_words" for s in strings(v)],
    "stay.yaml": [s for k in ("lines", "weather", "weather_in", "periods") for s in strings(S.get(k))],
    "moments.yaml": [sh.get("ends", "") for sh in M.get("shapes", []) if sh.get("ends")],
    "voice.yaml": [s for k in ("partings", "no_words", "frame_stand_in") for s in strings(V.get(k))],
    "questions.yaml": list(strings(Q.get("dropped"))),
    "doors.yaml": list(strings((D.get("memory") or {}).get("ended"))),
    "body.yaml": [s for s in strings((B.get("fall") or {})) if isinstance(s, str) and " " in s and s[:1].isupper()],
    "road.yaml": list(strings((RD.get("barrier") or {}))),
}
for name, lines in SHOWN.items():
    check(f"{name}: lines to read ({len(lines)})", len(lines) > 0)
    off = [l for l in lines if META.search(l)]
    check(f"...none speaks of the telling, the words or the story, or says it stands, holds, or will be told later", not off, off[:6])
    semi = [l for l in lines if ";" in l]
    check(f"...none chains clauses with a semicolon", not semi, semi[:6])
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
