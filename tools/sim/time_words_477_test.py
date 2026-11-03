"""(f477, GOALS.md G1) Time from now, in words: one converter (engine/clock.py ago, data/rules/time_words.yaml) counts calendar days and
seasons and never says a day number; the same speaker puts the same span the same way; the townsfolk's memories and sense of the hour,
the parting, the arrival, recognition, the fallen and what the player did lately are told through it; a town memory written with its
date is read without it; and the startup check refuses digits, dashes and bands out of order."""
import gzip
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
from engine import clock, matters, recognition

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

D = clock.MINUTES_PER_DAY
table = {d: clock.ago(0, d * D) for d in (0, 1, 3, 9, 20, 45, 130)}
check("the converter's table: today, yesterday, days, a week, weeks, a season, a year", table == {
    0: "earlier today", 1: "yesterday", 3: "three days ago", 9: "about a week ago", 20: "some weeks ago", 45: "last spring",
    130: "a year or more back"}, table)
check("...counted by calendar day: an hour before dawn's turn of the day is yesterday", clock.ago(clock.day(D) * D - clock.WAKE_HOUR * 60 - 30,
      clock.day(D) * D - clock.WAKE_HOUR * 60 + 30) == "yesterday")
check("...and a memory's day gives the same as its minute", all(clock.ago_day(clock.day(m), n) == clock.ago(m, n) for m, n in
      ((600, 600 + 3 * D), (100, 100 + 20 * D), (0, 45 * D), (D * 7 + 5, D * 8 + 900))))
said = {clock.ago(0, 3 * D, who=w) for w in ("farmer_1", "smith_2", "innkeeper_3", "merchant_4")}
check("speakers put a span their own way, and each the same way every time", len(said) == 2 and
      all(clock.ago(0, 3 * D, who=w) == clock.ago(0, 3 * D, who=w) for w in ("farmer_1", "smith_2")), said)
check("no wording has a digit", not any(re.search(r"\d", clock.ago(0, d * D, who=f"p{i}")) for d in range(0, 200, 3) for i in range(4)))
check("the hour as a person knows it: part of the day, the season, the weather, and no number",
      not re.search(r"\d", clock.now_line(600, "light rain")) and "spring" in clock.now_line(600, "light rain"), clock.now_line(600, "light rain"))
check("recognition speaks through the converter", recognition.ago(20 * D, 10 * D) == clock.ago(10 * D, 20 * D))
check("a town memory written with its date is read without it", matters._undated("The wolf pack: settled by Hob (spring, day 12)") ==
      "The wolf pack: settled by Hob")
for bad_table, why in (({"bands": [{"from": 0, "say": ["3 days ago"]}]}, "digit"), ({"bands": [{"from": 0, "say": ["a day - or so"]}]}, "dash"),
                       ({"bands": [{"from": 2, "say": ["x"]}, {"from": 0, "say": ["y"]}]}, "ascending"),
                       ({"bands": [{"from": 0, "say": ["now"]}, {"from": 2, "say": ["{n} days ago"]}, {"from": 9, "say": ["later"]}],
                         "numbers": {2: "two"}}, "numbers")):
    check(f"the startup check refuses a table with a {why} problem", any(why[:5] in p or (why == "ascending" and "ascending" in p) for p in clock.time_words_problems(bad_table)),
          clock.time_words_problems(bad_table))
check("...and passes the one in data", clock.time_words_problems() == [])

day_n = re.compile(r"\bday \d+\b")
for name in ("stub_short", "stub_party"):
    with gzip.open(Path("data/replay/sessions") / name / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
        calls = [json.loads(l) for l in f]
    speech = [c for c in calls if c.get("title") in ("NPCReply", "Parting")]
    dated = [c["i"] for c in speech if any(day_n.search(str(m.get("content") or "")) for m in (c.get("request") or {}).get("messages") or [])]
    check(f"{name}: no townsperson's reply or parting is told a day number", speech and not dated, dated)
    parting = [c for c in calls if c.get("title") == "Parting"]
    check(f"{name}: a parting is told the hour", not parting or all("NOW:" in str(c["request"]["messages"]) for c in parting))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
