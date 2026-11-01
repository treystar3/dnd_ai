"""(f441) A recorded session played again through the real turn (tools/rerun.py), the rebuild's Stage 1: recorded in one process and
replayed in another (each with its own PYTHONHASHSEED), every input must match the recording, its state, its outcomes and its words.
A changed answer is found at the input that met it; a call asking in other words parts a strict replay but not a loose one, which
a stage that changes prompts uses to compare the state alone."""
import gzip, json, os, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

REC = Path("saves/rerun_441_rec")
shutil.rmtree(REC, ignore_errors=True)

def run(*args, hseed="2"):
    out = subprocess.run([sys.executable, "tools/rerun.py", *args], capture_output=True, text=True, timeout=900,
                         env={**os.environ, "PYTHONHASHSEED": hseed})
    return out.returncode, (out.stdout + out.stderr).strip().splitlines()[-1:] or [""]

code, said = run("--make", str(REC), "--inputs", "30", hseed="1")
check("a stub session of 30 inputs is recorded", code == 0 and (REC / "calls.jsonl.gz").exists(), said)
code, said = run(str(REC))
check("replayed in another process, every input matches: state, outcomes and words", code == 0 and said[0].startswith("all "), said)

def calls():
    with gzip.open(REC / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f]
def write(rows):
    with gzip.open(REC / "calls.jsonl.gz", "wt", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
original = calls()

# ---- a changed answer is found at the input that met it
rows = [dict(r) for r in original]
pick = next(r for r in rows if r["title"] == "Narration" and r["input"] >= 5 and not r.get("error"))
answer = json.loads(pick["answer"])
answer["text"] = "A crow lands on the fence, looks at you, and flies off again."
pick["answer"] = json.dumps(answer)
write(rows)
code, said = run(str(REC))
check("a changed answer parts the replay", code == 1 and said[0].startswith("parted at input"), said)
check("...at the input that met it", said[0].startswith(f"parted at input {pick['input']} "), (pick["input"], said))

# ---- a call asking in other words: a strict replay parts, a loose one compares the state alone
rows = [dict(r) for r in original]
other = next(r for r in rows if r["title"] == "ActionPlan" and r["input"] >= 3)
other["req"] = "0" * 64
write(rows)
code, said = run(str(REC))
check("a call that asks in other words parts a strict replay", code == 1 and "other words" in said[0], said)
code, said = run(str(REC), "--loose")
check("...but not a loose one, which compares the state and outcomes alone", code == 0 and said[0].startswith("all "), said)

write(original)
shutil.rmtree(REC, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
