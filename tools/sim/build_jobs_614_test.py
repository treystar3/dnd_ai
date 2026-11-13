"""(f614) The pod's source build runs as many jobs as the container's CPU quota allows, not one for every core it can see. The f613 pod
saw 96 cores with a quota of about ten (cgroup cpu.max 1020000 100000); `cmake --build -j 96` throttled itself and the setup took 73
minutes against 28 the time before (docs/measure/2026-11-12_phase2_pod.md section 9). tools/runpod_night.sh already reads the quota for
the server's threads; the build now does the same.
Run: python tools/sim/build_jobs_614_test.py"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


spec = importlib.util.spec_from_file_location("fetch_runtime_614", ROOT / "tools" / "fetch_runtime.py")
fr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fr)

base = Path(tempfile.mkdtemp(prefix="build_jobs_614_"))
def quota(text):
    p = base / "cpu.max"
    p.write_text(text)
    return p


check("a quota of 10.2 cores on a host of 96 builds with 11 jobs, rounded up as the night script does",
      fr.build_jobs(quota("1020000 100000\n"), seen=96) == 11, fr.build_jobs(quota("1020000 100000\n"), seen=96))
check("...no quota (max) builds with every core seen", fr.build_jobs(quota("max 100000\n"), seen=96) == 96)
check("...nor does a quota above the cores seen add any", fr.build_jobs(quota("20000000 100000\n"), seen=16) == 16)
check("...no quota file (Windows, cgroup v1) or one that cannot be read builds with every core seen",
      fr.build_jobs(base / "absent", seen=8) == 8 and fr.build_jobs(quota("nonsense"), seen=8) == 8)
check("...and never fewer than one job", fr.build_jobs(quota("1000 100000\n"), seen=96) == 1)

steps = []
def fake_run(argv, *a, **k):
    steps.append([str(x) for x in argv])
    if argv[0] == "nvcc":
        return subprocess.CompletedProcess(argv, 0, stdout="release 12.8, V12.8.61", stderr="")
    if "--build" in argv:
        b = Path(argv[argv.index("--build") + 1]) / "bin"
        b.mkdir(parents=True, exist_ok=True)
        (b / "llama-server").write_text("x")
    return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
real_run, real_jobs = fr.subprocess.run, fr.build_jobs
fr.subprocess.run, fr.build_jobs = fake_run, lambda *a, **k: 11
try:
    fr.build_from_source({"llama_cpp": {"commit": "39febd2"}}, base / "built")
finally:
    fr.subprocess.run, fr.build_jobs = real_run, real_jobs
shutil.rmtree(base, ignore_errors=True)
build = next((st for st in steps if st[0] == "cmake" and "--build" in st), [])
check("the source build takes its job count from the quota", build[build.index("-j") + 1:][:1] == ["11"] if "-j" in build else False, build)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
