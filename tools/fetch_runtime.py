"""(f522) Fetch what the game runs its model on, each file checked against data/runtime/server.yaml: a llama-server build into
runtime/<build>/ and the model files into models/. A file whose size or sha256 differs from the pin is refused and removed, never
kept; a file already there with the right checksum is not fetched again. runtime/ and models/ are never in git.

    python tools/fetch_runtime.py --models                       # the chat model, its draft and the embedder (about 8.1 GB)
    python tools/fetch_runtime.py --build vulkan                 # this platform's Vulkan build
    python tools/fetch_runtime.py --build cuda --platform windows    # another platform's build (for packaging, f531)
    python tools/fetch_runtime.py --build cuda --from-source     # Linux CUDA: no release exists, so build the pinned commit (a pod)

Options: --settings (another settings file), --runtime-dir, --models-dir (other folders). Exit 1 when any file was refused or
failed; the others are still fetched."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml

from core import paths
from llm import runtime

CHUNK = 1 << 20


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dest: Path, sha: str, size: int) -> str | None:
    """Download url to dest, checking its size and checksum as it comes; None when it is right, else why it was refused (and nothing
    is left at dest). A file already at dest with the right checksum is kept as it is."""
    if dest.is_file() and dest.stat().st_size == size and sha256_of(dest) == sha:
        print(f"  have {dest.name} (checked)")
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    h, got = hashlib.sha256(), 0
    try:
        with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
            while True:
                chunk = r.read(CHUNK)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                got += len(chunk)
                if got > size:
                    break
    except Exception as e:
        part.unlink(missing_ok=True)
        return f"{dest.name}: the download failed ({type(e).__name__}: {e})"
    if got != size or h.hexdigest() != sha:
        part.unlink(missing_ok=True)
        return (f"{dest.name}: refused: {got} bytes with sha256 {h.hexdigest()[:16]}..., but the pin is {size} bytes with "
                f"{sha[:16]}...")
    os.replace(part, dest)
    print(f"  fetched {dest.name} ({got // 2 ** 20} MB, checksum right)")
    return None


def unpack(archive: Path, into: Path, exe: str) -> str | None:
    """The folder of the archive that holds llama-server, copied flat into `into`."""
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                z.extractall(t)
        else:
            with tarfile.open(archive) as z:
                z.extractall(t, filter="data") if sys.version_info >= (3, 12) else z.extractall(t)
        found = next((p for p in t.rglob(exe) if p.is_file()), None)
        src = found.parent if found is not None else t
        into.mkdir(parents=True, exist_ok=True)
        for p in src.iterdir():
            if p.is_file():
                shutil.copy2(p, into / p.name)
                if p.name == exe or p.suffix in ("", ".so"):
                    (into / p.name).chmod(0o755)
    return None


def build_from_source(cfg: dict, into: Path) -> str | None:
    """Linux CUDA: build llama-server at the pinned commit (as the pod sessions did), for every card from the 3060 (sm_86) up."""
    commit = cfg["llama_cpp"]["commit"]
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "llama.cpp"
        steps = [["git", "clone", "-q", "https://github.com/ggml-org/llama.cpp", str(src)],
                 ["git", "-C", str(src), "checkout", "-q", commit],
                 ["cmake", "-S", str(src), "-B", str(src / "build"), "-DGGML_CUDA=ON", f"-DCMAKE_CUDA_ARCHITECTURES={cuda_archs()}",
                  "-DLLAMA_CURL=OFF", "-DCMAKE_BUILD_TYPE=Release",
                  # (f522) the libraries found beside the program wherever it is copied, as llama.cpp's own release builds do; the
                  # default build path points into the folder deleted below, and the program would not start
                  "-DCMAKE_INSTALL_RPATH=$ORIGIN", "-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON"],
                 ["cmake", "--build", str(src / "build"), "--target", "llama-server", "-j", str(build_jobs())]]
        for step in steps:
            print("  $ " + " ".join(step))
            if subprocess.run(step).returncode != 0:
                return f"the source build failed at: {' '.join(step[:3])}"
        into.mkdir(parents=True, exist_ok=True)
        for p in (src / "build" / "bin").iterdir():
            if p.is_file():
                shutil.copy2(p, into / p.name)
    try:                                                # (f522) proven to start from where it now lives, its build folder gone
        ran = subprocess.run([str(into / "llama-server"), "--version"], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return f"the built llama-server does not start: {e}"
    if ran.returncode != 0:
        last = ((ran.stderr or "") + (ran.stdout or "")).strip().splitlines()[-1:] or ["no output"]
        return f"the built llama-server does not start: {last[0]}"
    return None


def build_jobs(cpu_max: Path = Path("/sys/fs/cgroup/cpu.max"), seen: int | None = None) -> int:
    """The source build's job count: the container's CPU quota rounded up (as tools/runpod_night.sh reads it), never more than the
    cores seen. (f614) a pod saw 96 cores with a quota of ten, and 96 jobs throttled each other."""
    if seen is None:
        seen = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 4)
    try:
        q, period = cpu_max.read_text().split()[:2]
        if q != "max":
            return max(1, min(seen, -(-int(q) // int(period))))
    except (OSError, ValueError):
        pass
    return seen


def cuda_archs() -> str:
    """The cards the source build is for: the 3060 (sm_86) and the 40-series (sm_89), and the 50-series (sm_120) when nvcc is 12.8 or
    newer (an older one refuses sm_120 at the configure step)."""
    try:
        out = subprocess.run(["nvcc", "--version"], capture_output=True, text=True, timeout=30).stdout or ""
    except (OSError, subprocess.SubprocessError):
        return "86;89;120"
    m = re.search(r"release (\d+)\.(\d+)", out)
    if m and (int(m.group(1)), int(m.group(2))) < (12, 8):
        print("  nvcc is older than 12.8: the build leaves out the 50-series cards (sm_120)")
        return "86;89"
    return "86;89;120"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--settings", default=str(runtime.SETTINGS))
    ap.add_argument("--build", choices=["cuda", "vulkan", "cpu"])
    ap.add_argument("--platform", choices=["windows", "linux"], default=runtime.platform())
    ap.add_argument("--from-source", action="store_true")
    ap.add_argument("--models", action="store_true")
    ap.add_argument("--runtime-dir", default=str(paths.RUNTIME))
    ap.add_argument("--models-dir", default=str(paths.MODELS))
    a = ap.parse_args(argv)
    cfg = yaml.safe_load(Path(a.settings).read_text(encoding="utf-8")) or {}
    problems: list[str] = []
    if a.models:
        for name, m in (cfg.get("models") or {}).items():
            why = fetch(m["source"], Path(a.models_dir) / m["file"], m["sha256"], int(m["size"]))
            if why:
                problems.append(why)
    if a.build:
        b = next((b for b in cfg.get("builds") or [] if b.get("id") == a.build and b.get("platform") == a.platform), None)
        into = Path(a.runtime_dir) / a.build
        exe = "llama-server.exe" if a.platform == "windows" else "llama-server"
        if b is None:
            problems.append(f"no {a.build} build for {a.platform} in the settings")
        elif b.get("from_source") or a.from_source:
            why = build_from_source(cfg, into)
            if why:
                problems.append(why)
        else:
            downloads = Path(a.runtime_dir) / ".downloads"
            for f in b.get("files") or []:
                archive = downloads / f["name"]
                why = fetch(cfg["llama_cpp"]["release"] + f["name"], archive, f["sha256"], int(f["size"]))
                if why:
                    problems.append(why)
                    continue
                unpack(archive, into, exe)
            if not problems:
                shutil.rmtree(downloads, ignore_errors=True)
                print(f"  {a.build} build in {into}")
    for p in problems:
        print("REFUSED " + p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
