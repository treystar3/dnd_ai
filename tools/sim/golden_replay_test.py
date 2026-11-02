"""(f450) The golden stub recording (data/replay/sessions/stub_short, kept since f441) replays exactly, as part of the suite. Before this
nothing in tools/sim replayed it: rerun_441_test records and replays a session of its own, and the golden was checked by hand before a
push. The rebuild's Bundle B moves the runtime out from under a recorded session feature by feature; this is the gate every feature
passes before it is pushed. A part here is read with `python3 tools/rerun.py --golden --rebless`, which prints what moved; the
recording is kept again only when the state of every input is unchanged and the builder can say which shown line moved and why."""
import subprocess, sys
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

out = subprocess.run([sys.executable, "tools/rerun.py", "--golden"], capture_output=True, text=True, timeout=900)
lines = [l for l in (out.stdout + out.stderr).splitlines() if l.strip()]
last = lines[-1] if lines else ""
check("the golden recording replays through the real turn: every input the same state, outcomes and words", out.returncode == 0
      and last.startswith("all ") and "inputs matched" in last, lines[-6:])
check("...and it is the recording the tree was built on, not one made on other rules or content",
      not any("data hash differs" in l for l in lines), [l for l in lines if "hash" in l][:2])
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
