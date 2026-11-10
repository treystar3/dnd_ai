"""(f531) Groundwork for packaging and the depots: the game depot (the exe, data/ and the server's builds under runtime/) and the model
depot (models/*.gguf, the files data/runtime/server.yaml pins), with nothing of Ollama left in what is built or installed.

- core.paths in a frozen build: BUNDLE is where the packaged data is unpacked and APP the exe's folder; RUNTIME, MODELS and RUN sit
  beside the exe, never under the bundle's data/; MERAVIA_RUNTIME and MERAVIA_MODELS still name other folders.
- The startup check requires the kept recordings only where a replay folder exists (a source tree): a built game without data/replay
  passes, and a source tree missing a golden is still told.
- build_exe.bat ships runtime/cuda and runtime/vulkan (and the processor's build) beside the exe, never models/, and collects no Ollama.
- build_installer.bat writes the installer's model downloads from server.yaml (tools/installer_files.py: each file's source, name and
  sha256, checked by the installer); meravia.iss includes them and installs no Ollama; README_testers.md says so.
- The launchers (play.bat, nightrun.bat, eventrun.bat) fetch the server's files when they are missing, and look for no Ollama.
- CREDITS.md names llama.cpp, the model weights, the embedder and the GPU runtimes; HOSTED.md has the depot layout.

Run: python tools/sim/frozen_531_test.py"""

import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


# ---- core.paths in a frozen build
from core import paths
scratch = Path(tempfile.mkdtemp(prefix="frozen531_")).resolve()     # (f573) the long name: Windows' TEMP may be 8.3 (RUNNER~1)
bundle, app = scratch / "bundle", scratch / "app"
(bundle / "data").mkdir(parents=True)
app.mkdir()
saved = {"frozen": getattr(sys, "frozen", None), "meipass": getattr(sys, "_MEIPASS", None), "exe": sys.executable}
env_before = {k: os.environ.pop(k, None) for k in ("MERAVIA_RUNTIME", "MERAVIA_MODELS", "MERAVIA_RUN")}
try:
    sys.frozen = True
    sys._MEIPASS = str(bundle)
    sys.executable = str(app / "Meravia.exe")
    importlib.reload(paths)
    check("frozen: BUNDLE is where the data is unpacked, APP the exe's folder", paths.FROZEN and paths.BUNDLE == bundle and paths.APP == app,
          (paths.FROZEN, paths.BUNDLE, paths.APP))
    check("...and the server's builds, the model files and the run files sit beside the exe, never under the bundle's data/",
          paths.RUNTIME == app / "runtime" and paths.MODELS == app / "models" and paths.RUN == app / "run"
          and not any(str(p).startswith(str(bundle)) for p in (paths.RUNTIME, paths.MODELS, paths.RUN)), (paths.RUNTIME, paths.MODELS, paths.RUN))
    os.environ["MERAVIA_MODELS"] = str(scratch / "elsewhere")
    os.environ["MERAVIA_RUNTIME"] = str(scratch / "builds")
    importlib.reload(paths)
    check("...while MERAVIA_RUNTIME and MERAVIA_MODELS still name other folders (a developer's), frozen or not",
          paths.MODELS == scratch / "elsewhere" and paths.RUNTIME == scratch / "builds" and paths.RUN == app / "run", (paths.MODELS, paths.RUNTIME))
finally:
    for k in ("MERAVIA_RUNTIME", "MERAVIA_MODELS", "MERAVIA_RUN"):
        os.environ.pop(k, None)
        if env_before.get(k) is not None:
            os.environ[k] = env_before[k]
    if saved["frozen"] is None:
        delattr(sys, "frozen")
    else:
        sys.frozen = saved["frozen"]
    if saved["meipass"] is None:
        delattr(sys, "_MEIPASS")
    else:
        sys._MEIPASS = saved["meipass"]
    sys.executable = saved["exe"]
    importlib.reload(paths)
check("from source, both are the project folder again", not paths.FROZEN and paths.APP == ROOT and paths.BUNDLE == ROOT and paths.RUNTIME == ROOT / "runtime",
      (paths.APP, paths.RUNTIME))

# ---- the startup check without data/replay
from engine import data_check
built = scratch / "built"
for rel in ("data/rules/budget.yaml", "data/measured/bundle_e_fights.yaml"):
    (built / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / rel, built / rel)
real_root = data_check.ROOT
try:
    data_check.ROOT = built
    without = data_check.fights_problems()
    (built / "data" / "replay" / "sessions").mkdir(parents=True)
    with_folder = data_check.fights_problems()
finally:
    data_check.ROOT = real_root
check("a built game without data/replay passes the fights check: the goldens are a source tree's", without == [], without)
check("...and a source tree missing a golden is still told", any("no such recording is kept" in p for p in with_folder), with_folder)
check("the startup check passes on the source tree", data_check.check() == [], data_check.check()[:3])

# ---- what is built and installed
exe_bat = (ROOT / "build_exe.bat").read_text(encoding="utf-8")
check("build_exe.bat collects no Ollama", "ollama" not in exe_bat.lower())
check("...and carries the server's builds beside the exe: cuda and vulkan (and the processor's), never the model files",
      "runtime\\cuda" in exe_bat and "runtime\\vulkan" in exe_bat and "runtime\\cpu" in exe_bat
      and not any("copy" in l.lower() and "models" in l.lower() and not l.strip().lower().startswith("rem") for l in exe_bat.splitlines()), exe_bat[-900:])
inst_bat = (ROOT / "build_installer.bat").read_text(encoding="utf-8")
check("build_installer.bat writes the installer's model downloads from server.yaml before Inno Setup runs",
      "installer_files.py" in inst_bat and inst_bat.index("installer_files.py") < inst_bat.index("meravia.iss"))
import installer_files
from llm import runtime
cfg = runtime.settings()
text = installer_files.pascal(cfg)
check("the include names every model file with its source and its sha256, for the installer to check",
      all(m["file"] in text and m["sha256"] in text and m["source"] in text for m in cfg["models"].values())
      and "AddModelDownloads" in text and "ModelsPresent" in text and "InstallModels" in text, text[:400])
out = installer_files.write(scratch / "models.iss", cfg)
check("...written with Windows line ends, and --check reads it back as current",
      out.read_bytes().count(b"\r\n") > 3 and installer_files.main(["--check", "--out", str(out)]) == 0)
(scratch / "models.iss").write_text("stale", encoding="utf-8")
check("...and a stale include is caught", installer_files.main(["--check", "--out", str(scratch / "models.iss")]) == 1)
iss = (ROOT / "installer" / "meravia.iss").read_text(encoding="utf-8")
check("meravia.iss installs no Ollama, includes the model downloads and installs them", "ollama" not in iss.lower()
      and '#include "models.iss"' in iss and "AddModelDownloads(DownloadPage)" in iss and "InstallModels" in iss and "ModelsPresent" in iss)
readme = (ROOT / "installer" / "README_testers.md").read_text(encoding="utf-8")
check("README_testers.md names no Ollama and says the installer downloads the model files", "ollama" not in readme.lower() and "model files" in readme)
for name in ("play.bat", "nightrun.bat", "eventrun.bat"):
    src = (ROOT / name).read_text(encoding="utf-8")
    check(f"{name} looks for no Ollama and fetches the server's files when they are missing", "ollama" not in src.lower()
          and "fetch_runtime.py" in src and "runtime_problems" in src, name)
credits = (ROOT / "CREDITS.md").read_text(encoding="utf-8")
check("CREDITS.md names llama.cpp (MIT), the model weights, the embedder and the GPU runtimes",
      "llama.cpp" in credits and "MIT" in credits and "Gemma" in credits and "nomic" in credits.lower() and "CUDA" in credits and "Vulkan" in credits)
hosted = (ROOT / "tools" / "HOSTED.md").read_text(encoding="utf-8")
check("HOSTED.md has the depot layout: the game depot and the model depot", "game depot" in hosted and "model depot" in hosted)
gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
check("the generated include is never kept in git", "installer/models.iss" in gi)

shutil.rmtree(scratch, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
