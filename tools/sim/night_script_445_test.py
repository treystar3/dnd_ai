"""(f445) The rented-card night script installs zstd before Ollama: Ollama's installer now unpacks with it, and the CUDA 12.4 image the
A4000 timing night ran on lacked it, so the night ended before its first line. The script still parses as shell."""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

src = Path("tools/runpod_night.sh").read_text(encoding="utf-8")
z, o = src.find("install -y -qq zstd"), src.find("ollama.com/install.sh")
check("zstd is installed when missing, before Ollama's installer runs", 0 <= z < o and "command -v zstd" in src[:z], (z, o))
check("the night script still parses as shell", subprocess.run(["bash", "-n", "tools/runpod_night.sh"]).returncode == 0)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
