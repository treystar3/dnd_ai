"""(f425) A night can set the model's context per call (DND_NUM_CTX), so six runs sharing one card reserve no more memory than three did;
without it the game keeps its own 32,768. The night's launcher accepts it like the other DND_ settings."""
import os, subprocess, sys
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def ctx(env):
    e = {k: v for k, v in os.environ.items() if k != "DND_NUM_CTX"} | env
    return subprocess.run([sys.executable, "-c", "import config; print(config.NUM_CTX)"], capture_output=True, text=True, env=e).stdout.strip()

check("the game's own context is 32,768", ctx({}) == "32768", ctx({}))
check("a night sets it with DND_NUM_CTX", ctx({"DND_NUM_CTX": "16384"}) == "16384", ctx({"DND_NUM_CTX": "16384"}))
check("...and an empty one leaves the game's own", ctx({"DND_NUM_CTX": ""}) == "32768")
import re
src = open("tools/runpod_jupyter.py", encoding="utf-8").read()
check("the night's launcher passes DND_NUM_CTX=16384 on", re.fullmatch(r"DND_[A-Z_]+=[0-9.+-]+", "DND_NUM_CTX=16384") is not None
      and "--env" in src)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
