"""(f566) The model's call log can never fail a call, and the fights play to their numbers when it cannot be written.

One full suite in about sixty (2026-11-06) moved shard 2 of the fight fixtures (mechanics:vessel..withering, its second round not
fought). The suite runs four tests at once and every one logs its stub's calls to the same logs/llm_calls.jsonl, which sits near
LOG_MAX_MB, so each trims it often, and every trim went through one shared temp file: a trim could find that temp moved by another
process's (FileNotFoundError), or on Windows have its replace refused while another process held the log open (PermissionError).
gateway._log raised that out of a call already answered, past every site's LLMError fallback, and the fight round's operation rolled
back: the round was not fought and every number after it moved. Neither the background people (npc/backfill.py: simlib.install turns the
first-batch split off, so no job runs in the fixtures) nor the machine's load decide a fight. Now:

- trim_log never raises, and leaves the log whole and no temp of its own behind when the system refuses its replace;
- three processes appending to and trimming one over-full log at once raise nothing (before: hundreds of errors a second);
- shard 2 plays to its recorded numbers, with no turn rolled back, while every write of its call log is refused;
- generate() gives its answer when neither the call log nor the audit log can be written;
- a turn rolled back by a fault is named by the fixtures (its case and the error), not left to read as moved numbers."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/sim")
import config
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

scratch = Path(tempfile.mkdtemp(prefix="call_log_566_"))
config.CRASH_LOG_PATH = str(scratch / "crash.log")          # the faults this test makes stay out of logs/crash.log
config.LOG_PATH = str(scratch / "calls.jsonl")

# ---- a trim whose replace the system refuses
log = scratch / "trim.jsonl"
lines = [json.dumps({"n": i, "raw": "x" * 100}) for i in range(40)]
log.write_text("\n".join(lines) + "\n", encoding="utf-8")
keep_mb, keep_n = config.LOG_MAX_MB, config.LOG_KEEP_ENTRIES
config.LOG_MAX_MB, config.LOG_KEEP_ENTRIES = 0.001, 3       # about a kilobyte: this log is over it
real_replace = Path.replace

def refuse(self, target):
    raise PermissionError(13, "The process cannot access the file because it is being used by another process")

Path.replace = refuse
raised = None
try:
    gateway.trim_log(log)
except Exception as e:
    raised = e
finally:
    Path.replace = real_replace
check("a trim whose replace is refused (another process holds the log) raises nothing", raised is None, repr(raised))
check("...leaves the log whole", log.read_text(encoding="utf-8").splitlines() == lines)
check("...and no temp file of its own behind", not [p.name for p in scratch.iterdir() if p.name.endswith(".tmp")],
      [p.name for p in scratch.iterdir()])
gateway.trim_log(log)
check("a trim let through keeps the last entries", log.read_text(encoding="utf-8").splitlines() == lines[-3:])
config.LOG_MAX_MB, config.LOG_KEEP_ENTRIES = keep_mb, keep_n

# ---- three processes appending to and trimming one over-full log at once, as the suite's tests do
shared = scratch / "shared.jsonl"
code = r"""
import json, sys
sys.path[:0] = ["."]
import config
config.LOG_MAX_MB, config.LOG_KEEP_ENTRIES, config.LOG_PATH = 0.001, 5, sys.argv[1]
from llm import gateway
errors = []
for i in range(300):
    try:
        gateway._log("call_log_566", 0, 0.0, [{"role": "user", "content": "x" * 200}], "{}", None)
        gateway.trim_log()
    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
print(json.dumps({"errors": len(errors), "first": errors[:2]}))
"""
procs = [subprocess.Popen([sys.executable, "-c", code, str(shared)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
         for _ in range(3)]
outs = [p.communicate(timeout=300) for p in procs]
got = []
for out, err in outs:
    try:
        got.append(json.loads(out.strip().splitlines()[-1]))
    except (ValueError, IndexError):
        got.append({"errors": -1, "first": [err[-300:]]})
check("three processes appending to and trimming one over-full call log at once raise nothing", all(g["errors"] == 0 for g in got), got)
check("...and leave no temp file behind", not [p.name for p in scratch.iterdir() if p.name.endswith(".tmp")],
      [p.name for p in scratch.iterdir() if p.name.endswith(".tmp")])

# ---- shard 2 of the fight fixtures with every write of its call log refused (the shard's first play in this process, as in 494c)
import fight_fixtures as ff
refused = scratch / "refused"
refused.mkdir()
config.LOG_PATH = str(refused)                               # a folder: the system refuses every append (IsADirectory, or PermissionError)
writes = gateway._writes
records, _ = ff.play(2)
moved = [l for l in ff.compare(2, records) if not l.startswith("warning")]
check(f"shard 2 plays all {len(records)} of its fights to their recorded numbers while every write of its call log is refused",
      not moved, moved[:3])
check("...with no turn rolled back by a fault", not ff.FAULTS, ff.fault_lines())
check("...and the call log was refused all along (none of its writes stood)", gateway._writes == writes, gateway._writes - writes)

# ---- generate() answers when neither the call log nor the audit log can be written
from pydantic import BaseModel
import simlib
from llm import audit


class Reply(BaseModel):
    speech: str


class Answer:
    def __init__(self, text):
        self.message = type("M", (), {"content": text})()
        self.done_reason = "stop"


held = simlib.stand_in(chat=lambda **k: Answer('{"speech": "a cart rolls by"}'), embed=None, name="call_log_566")
audit_was = (config.AUDIT_LOG, audit._path, audit._full)
config.AUDIT_LOG, audit._path, audit._full = True, refused, False      # the audit's file a folder too: its append is refused
try:
    r = gateway.generate("narrate", "You are the narrator.", "plain user text", Reply, retries=0)
    err = None
except Exception as e:
    r, err = None, e
finally:
    config.AUDIT_LOG, audit._path, audit._full = audit_was
    held()
check("generate() gives its answer when neither the call log nor the audit log can be written", r is not None
      and r.speech == "a cart rolls by", repr(err))

# ---- a turn rolled back by a fault is named by the fixtures
first = next(c["id"] for c in ff.cases() if ff.shard_of(c) == 2)
config.LOG_PATH = str(scratch / "calls.jsonl")
real_log = gateway._log
fired = []

def failing_log(task, *a, **k):                              # the old failure put back for one call: an OSError out of an answered call
    if task == "combat_interpret" and not fired:
        fired.append(task)
        raise FileNotFoundError(2, "No such file or directory", "logs/llm_calls.tmp")
    return real_log(task, *a, **k)

gateway._log = failing_log
try:
    ff.play(2, only={first})
finally:
    gateway._log = real_log
check("a turn rolled back by a fault is named by the fixtures: its case and the error", fired and ff.FAULTS
      and ff.FAULTS[0]["case"] == first and "FileNotFoundError" in ff.FAULTS[0]["error"], (fired, ff.fault_lines()))

shutil.rmtree(scratch, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
