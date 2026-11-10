"""(f445, f529) The rented-card night script runs the nights on the engine the game ships with: it fetches the game's own model server and
model files by their pinned checksums (tools/fetch_runtime.py, each fetch tried again on a failure), checks they are in place, installs
no Ollama and names none, records one run a night, splits the container's cores among the runs at once, and still parses as shell."""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fake_runtime
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

src = Path("tools/runpod_night.sh").read_text(encoding="utf-8")
check("the night script installs no Ollama and names none", "ollama" not in src.lower())
check("...fetches the model files and the server's build by their pins, each fetch tried again on a failure",
      "fetch --models" in src and "fetch --build" in src and "fetch_runtime.py" in src and "try $n of 6" in src)
check("...checks the files are in place before the night begins", "runtime_problems(check_files=True)" in src)
check("...records one run a night (--record once, to tools/nightrun.py, which gives it to its first run alone)", src.count("--record") == 1)
check("...splits the quota's cores among the runs at once, each server its share", "CORES / PARALLEL" in src and "DND_NUM_THREAD" in src)
check("...and installs the CUDA compiler only for the build from source", "cuda-nvcc" in src and 'if [ "$BUILD" = "cuda" ]' in src)
check("...the 12.8 compiler (the 50-series cards need it: an older nvcc leaves sm_120 out), pointed at ahead of the image's own",
      "cuda-nvcc-12-8" in src and "export CUDACXX=/usr/local/cuda-12.8/bin/nvcc" in src
      and src.index("/usr/local/cuda-12.8/bin/nvcc --version") < src.index("cuda-nvcc-12-8"))     # installed only when 12.8's is not here
check("the night script still parses as shell", subprocess.run([fake_runtime.bash(), "-n", "tools/runpod_night.sh"]).returncode == 0)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
