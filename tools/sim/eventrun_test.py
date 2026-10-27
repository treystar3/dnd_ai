"""tools/eventrun.py forces a campaign and plays toward its end with the stand-in model: the event starts, the bot goes where it is and
types lines about it, time passes between lines so the stages turn, the report says what the model wrote and what happened."""
import json, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, ".")
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

out = Path("saves/eventrun_test/out")
shutil.rmtree("saves/eventrun_test", ignore_errors=True)
shutil.rmtree("saves/eventrun_test_game", ignore_errors=True)
r = subprocess.run([sys.executable, "tools/eventrun.py", "campaign", "--stub", "--turns", "60", "--level", "40", "--seed", "5", "--days", "90",
                    "--hours", "1", "--out", str(out), "--save", "eventrun_test_game"], capture_output=True, text=True, timeout=1500)
check("the run finishes on its own", r.returncode == 0, (r.stdout[-1500:], r.stderr[-2500:]))
info = json.loads((out / "run.json").read_text(encoding="utf-8")) if (out / "run.json").exists() else {}
check("the campaign started and the run knows its title", info.get("started") and info.get("title"), info)
rows = [json.loads(l) for l in (out / "turns.jsonl").read_text(encoding="utf-8").splitlines()] if (out / "turns.jsonl").exists() else []
check("lines were typed, of the event's kinds", rows and {x["kind"] for x in rows} & {"move", "talk", "hunt", "look", "fight", "persuade"}, [x["kind"] for x in rows][:20])
report = (out / "report.md").read_text(encoding="utf-8") if (out / "report.md").exists() else ""
check("the report has the event as written, a timeline, the judge and the checklist",
      all(h in report for h in ("## The event as the model wrote it", "**Stages**", "**Paths**", "## Timeline", "## The judge", "## Outcome checklist")), report[:800])
check("the bot asked about the matter by name where it is, before going after its paths",
      info.get("title", "") and any(info["title"] in x["text"] and x["kind"] == "talk" for x in rows), [x["text"] for x in rows][:8])
check("the timeline records what the engine did: the moment, the hunt, a path met or the stages turning",
      any(k in report for k in ("PATH MET", "STAGE 2/", "moment:", "is put into")), [l for l in report.splitlines() if l.startswith("- day")][:12])
check("the event was resolved by play, or is still going", info.get("status") in ("resolved", "active", "ended"), info.get("status"))
check("the character set out with a full party", len(info.get("party", [])) == 3 and "| Party |" in report, info.get("party"))
summary = (out / "summary.md").read_text(encoding="utf-8") if (out / "summary.md").exists() else ""
check("the calls are summarised, the proposal among them", "pulse_thread" in summary, summary[-600:])
shutil.rmtree("saves/eventrun_test", ignore_errors=True)
shutil.rmtree("saves/eventrun_test_game", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
