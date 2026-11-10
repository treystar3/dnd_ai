"""(f528) A fake of the game's runtime folder for the tests: runtime/<build>/llama-server launchers that list the devices FAKE_LIST_<build>
names and then serve a fake llama-server (tools/sim/fake_llama.py) answering every contract by its title with the stand-in model
(simlib.Stub; the title is read from the grammar's first line, as llm/llama.py grammar_of writes it) and every embedding with
simlib.FakeEmbedder; the model files as placeholders; and the environment that points core.paths at it (MERAVIA_RUNTIME,
MERAVIA_MODELS) for a child process, or the patch that points this process's core.paths at it.

    from fake_runtime import Layout, THE_3060
    lay = Layout(base)                            # writes runtime/{cuda,vulkan,cpu}/llama-server and models/*.gguf under base
    env = lay.env(cuda=[THE_3060])                # os.environ for a child: the layout, the devices, no MERAVIA_NO_SERVER
    lay.patch_paths()                             # this process: core.paths RUN/RUNTIME/MODELS/APP at the layout, the env for its children
    lay.restore()                                 # ...and back
    lay.bodies()                                  # every body the fakes were sent, with its path (FAKE_BODIES); lay.argv() every launch

The launchers also read FAKE_LOAD_SECONDS (the load's length), FAKE_LOAD_UNTIL (a file the chat server's load waits for), FAKE_GRANTED (the context the server grants a slot), FAKE_OFFLOAD (the
layers on the card, 49/49), FAKE_FAIL_FILE (a file whose presence makes the next chat server fail to load, once), FAKE_DELAY (seconds
before each answer) and FAKE_SEED (the stand-in's seed), as the f522 and f526 tests' launchers do."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "tools" / "sim"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THE_3060 = "  CUDA0: NVIDIA GeForce RTX 3060 (12287 MiB, 11200 MiB free)"


def bash() -> str:
    """(f573) A bash to run a shell script with. On Windows, Git's own: the "bash" on PATH may be WSL's launcher (System32), which
    has no Linux to run on a CI machine."""
    import shutil
    if os.name != "nt":
        return shutil.which("bash") or "bash"
    git = shutil.which("git")
    for up in Path(git).resolve().parents[:3] if git else []:        # Git\cmd\git.exe or Git\mingw64\bin\git.exe
        if (up / "bin" / "bash.exe").exists():
            return str(up / "bin" / "bash.exe")
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    raise RuntimeError("no Git bash found: install Git for Windows")


def write_exe(path: Path | str, script: str) -> Path:
    """(f561) A fake program running `script`: a shebang file on POSIX, pip's script launcher with the script appended on Windows."""
    import io, platform, zipfile
    path = Path(path)
    if os.name != "nt":
        path.write_text(script, encoding="utf-8", newline="\n")
        path.chmod(0o755)
        return path
    name = "t64-arm.exe" if platform.machine().upper() == "ARM64" else "t64.exe"
    try:
        from pip._vendor import distlib
    except ImportError:
        try:
            import distlib
        except ImportError:
            raise RuntimeError("the fake llama-server needs pip (or distlib) in this Python on Windows: python -m ensurepip") from None
    launcher = (Path(distlib.__file__).parent / name).read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("__main__.py", script)
    path.write_bytes(launcher + f'#!"{sys.executable}"\n'.encode("utf-8") + buf.getvalue())
    return path


def disable(path: Path | str) -> None:
    """(f561) A fake program that cannot start: not executable on POSIX, not a program on Windows."""
    path = Path(path)
    if os.name != "nt":
        path.chmod(0o644)
    else:
        path.write_bytes(b"not a program")


def alive(pid: int) -> bool:
    """(f561) Whether a process is running and not a zombie, on any OS."""
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        k.OpenProcess.restype = ctypes.c_void_p
        h = k.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        k.GetExitCodeProcess(ctypes.c_void_p(h), ctypes.byref(code)); k.CloseHandle(ctypes.c_void_p(h))
        return code.value == 259                            # STILL_ACTIVE
    try:
        st = Path(f"/proc/{pid}/status").read_text()
        return "State:\tZ" not in st and "State:\tX" not in st
    except OSError:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def kill(pid: int) -> None:
    """(f561) End a process outright, as a crash would (SIGKILL on POSIX, TerminateProcess on Windows)."""
    import signal
    try:
        os.kill(int(pid), getattr(signal, "SIGKILL", signal.SIGTERM))
    except OSError:
        pass


def _cim(where: str, **env) -> list[int]:
    q = f"Get-CimInstance Win32_Process | Where-Object {{ {where} }} | ForEach-Object {{ $_.ProcessId }}"
    r = subprocess.run(["powershell", "-NoProfile", "-Command", q], capture_output=True, text=True, env=dict(os.environ, **env))
    if r.returncode != 0:                                   # (f561) a probe that cannot look must not read as "none left"
        raise RuntimeError(f"process probe failed: {r.stderr.strip()[-300:]}")
    return [int(x) for x in r.stdout.split() if x.strip().isdigit() and int(x) != os.getpid()]


def windows_processes(image: Path | str, needle: str = "") -> list[int]:
    """(f561) Windows: the processes started from `image` whose command line holds `needle`."""
    return _cim("$_.ExecutablePath -eq $env:FAKE_IMAGE -and $_.CommandLine.Contains($env:FAKE_NEEDLE)", FAKE_IMAGE=str(image), FAKE_NEEDLE=needle)


def processes_under(folder: Path | str) -> list[int]:
    """(f561) The processes whose command line names `folder` (pgrep -f on POSIX)."""
    if os.name == "nt":
        return _cim("$_.CommandLine -and $_.CommandLine.Contains($env:FAKE_UNDER)", FAKE_UNDER=str(folder))
    r = subprocess.run(["pgrep", "-f", "--", str(folder)], capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"pgrep failed: {r.stderr.strip()}")
    return [int(x) for x in r.stdout.split()]


LAUNCHER = """#!{py}
import os, sys, time, json, threading
sys.path.insert(0, {root!r})
sys.path.insert(0, {sim!r})
args = sys.argv[1:]
build = os.path.basename(os.path.dirname(os.path.abspath(sys.argv[0])))
if os.environ.get("FAKE_ARGV"):
    with open(os.environ["FAKE_ARGV"], "a") as f:
        f.write(json.dumps([build] + args) + "\\n")
if "--list-devices" in args:
    print("Available devices:")
    for l in json.loads(os.environ.get("FAKE_LIST_" + build, "[]")):
        print(l)
    sys.exit(0)
port, key = int(args[args.index("--port") + 1]), args[args.index("--api-key") + 1]
fail = os.environ.get("FAKE_FAIL_FILE", "")
if fail and os.path.exists(fail) and "--embeddings" not in args:
    os.remove(fail)
    print("error: failed to load the model", flush=True); sys.exit(3)
ctx = int(args[args.index("-c") + 1]) // int(args[args.index("-np") + 1]) if "-np" in args else 2048
granted = int(os.environ.get("FAKE_GRANTED", "0") or 0) or ctx
from fake_llama import FakeLlama
import simlib
from llm import contracts
stub = simlib.Stub("warrior", int(os.environ.get("FAKE_SEED", "1") or 1))
emb = simlib.FakeEmbedder()
lock = threading.Lock()
bodies = os.environ.get("FAKE_BODIES", "")
delay = float(os.environ.get("FAKE_DELAY", "0") or 0)

def title_of(body):
    first = (body.get("grammar") or "").split("\\n", 1)[0].split()
    return first[2] if len(first) >= 3 and first[1] == "Meravia" else ""

def script(path, body, n):
    if bodies:
        with lock, open(bodies, "a") as f:
            f.write(json.dumps({{"path": path, **body}}) + "\\n")
    if path == "/v1/embeddings":
        return {{"vectors": [emb.vec(t) for t in body.get("input") or []], "delay": delay}}
    t = title_of(body)
    cls = getattr(contracts, t, None)
    fmt = cls.model_json_schema() if cls is not None else {{"title": t}}
    with lock:
        r = stub.chat(messages=body.get("messages") or [], format=fmt, options={{}})
    return {{"content": r.message.content, "delay": delay}}

try:
    fake = FakeLlama(key=key, slot_ctx=granted, port=port, loading=10 ** 9, script=script)
except OSError:
    print("main: couldn't bind HTTP server socket", flush=True); sys.exit(1)
until = os.environ.get("FAKE_LOAD_UNTIL", "")
while until and "--embeddings" not in args and not os.path.exists(until):   # the chat server's load waits for the test's go-ahead
    time.sleep(0.05)
time.sleep(float(os.environ.get("FAKE_LOAD_SECONDS", "0.2") or 0))
if "--embeddings" not in args and "-lv" in args and int(args[args.index("-lv") + 1]) >= 4:
    print("load_tensors: offloaded " + os.environ.get("FAKE_OFFLOAD", "49/49") + " layers to GPU", flush=True)
print("0.04.015 I srv    load_model: initializing, n_slots = 2, n_ctx_slot = " + str(granted), flush=True)
fake.loading = 0
print("0.04.120 I srv  server_run_i: model loaded", flush=True)
while True:
    time.sleep(1)
"""


class Layout:
    def __init__(self, base: Path | str, cfg: dict | None = None):
        from llm import runtime
        self.base = Path(base)
        self.cfg = runtime.settings() if cfg is None else cfg
        self.rt_dir, self.models_dir = self.base / "runtime", self.base / "models"
        self.run_dir, self.app = self.base / "run", self.base / "app"
        self.argv_log, self.bodies_log = self.base / "argv.jsonl", self.base / "bodies.jsonl"
        for b in ("cuda", "vulkan", "cpu"):
            (self.rt_dir / b).mkdir(parents=True, exist_ok=True)
            write_exe(self.rt_dir / b / runtime.exe_name(), LAUNCHER.format(py=sys.executable, root=str(ROOT), sim=str(SIM)))
        self.models_dir.mkdir(exist_ok=True)
        for m in (self.cfg.get("models") or {}).values():
            (self.models_dir / m["file"]).write_bytes(b"gguf")
        self._saved: dict | None = None
        self._env_before: dict | None = None

    def env(self, cuda=None, vulkan=None, **extra) -> dict:
        """os.environ for a child process on this layout: the folders (the run folder too, so a child's lock probe never reaches the
        developer's own run/), the devices each build lists, the logs, no MERAVIA_NO_SERVER."""
        e = dict(os.environ)
        e.pop("MERAVIA_NO_SERVER", None)
        e.update(MERAVIA_RUNTIME=str(self.rt_dir), MERAVIA_MODELS=str(self.models_dir), MERAVIA_RUN=str(self.run_dir), FAKE_ARGV=str(self.argv_log),
                 FAKE_BODIES=str(self.bodies_log), FAKE_LIST_cuda=json.dumps(list(cuda or [])), FAKE_LIST_vulkan=json.dumps(list(vulkan or [])))
        e.update({k: str(v) for k, v in extra.items()})
        return e

    def patch_paths(self, cuda=None, vulkan=None, **extra) -> None:
        """This process on the layout: core.paths at it, and its environment as env() gives a child's (the launchers it spawns read it)."""
        from core import paths
        self._saved = {k: getattr(paths, k) for k in ("RUN", "RUNTIME", "MODELS", "APP")}
        paths.RUN, paths.RUNTIME, paths.MODELS, paths.APP = self.run_dir, self.rt_dir, self.models_dir, self.app
        self._env_before = dict(os.environ)
        new = self.env(cuda, vulkan, **extra)            # (f561) built before the clear: Windows sockets need SystemRoot
        os.environ.clear()
        os.environ.update(new)

    def restore(self) -> None:
        from core import paths
        if self._saved is not None:
            for k, v in self._saved.items():
                setattr(paths, k, v)
            self._saved = None
        if self._env_before is not None:
            os.environ.clear()
            os.environ.update(self._env_before)
            self._env_before = None

    def bodies(self) -> list[dict]:
        if not self.bodies_log.exists():
            return []
        return [json.loads(l) for l in self.bodies_log.read_text(encoding="utf-8").splitlines() if l.strip()]

    def argv(self) -> list[list]:
        if not self.argv_log.exists():
            return []
        return [json.loads(l) for l in self.argv_log.read_text(encoding="utf-8").splitlines() if l.strip()]
