"""(f522) The model server's children: llama-server started, watched and stopped by the game itself (GOALS.md, owner's decisions of
2026-11-05: llama.cpp's llama-server ships in the game's own folder, "started and stopped by the game itself", with the model files
in a Steam depot of their own; the context is two slots of 16,384 tokens, the turn's and the background's). Behind a switch until
f528: config.BACKEND 'runtime' (DND_BACKEND=runtime) makes main.py start the server; the default stays Ollama.

Where things live (core/paths.py): RUNTIME, the server builds (runtime/<build>/llama-server), and MODELS, the model files, both outside
data/; RUN, the game's own run files (run/game.lock, run/server.json, run/server.pid), outside logs/ (which players send). The
settings are data/runtime/server.yaml, outside the data hash (storage/statehash.py), as data/measured is: they describe how this
machine runs the model, not the game. runtime_problems() holds them to what the game needs.

Starting a child (spawn): every child is started from one long-lived thread (the spawner), so Linux's parent-death signal, which fires
when the thread that started a child ends, cannot fire when a short-lived loading thread ends. Each child gets a free loopback port, a
fresh --api-key, --no-webui; two slots with the context at twice the slot's (-np 2 -c 32768), --fit-ctx at the full context so the
fit step moves layers to the processor rather than shrinking the context (no -ngl: the fit decides it, every layer on the card when
it fits); --cache-ram capped from the settings; its own process group (Linux: a new session plus the parent-death signal; Windows: a
new process group, no window and a kill-on-close Job Object, never DETACHED_PROCESS), so Ctrl+C at the game never reaches it. Its
output goes to logs/llama-server.log and its tail to logs/crash.log when it dies. A child left by a crashed game is stopped before the
load, and only when its pid file's executable path is ours.

States: not_started, loading, ready, restarting, failed. load(progress) starts the chat server, waits for /health while reading the log's phases
(progress only ever rises), then reads /props, refusing a granted context below the settings' (the fit step may shrink it). A call
that finds the server gone restarts it once (that call is one failed try); a second death is 'failed'. close() is idempotent: it
cancels the calls in flight, stops every child and takes the run files away. main.py calls it from atexit and its finally; the
window's close and core/updates.py reach it through llm.backend.close().

One game at a time: main.py holds an OS lock on run/game.lock (GameLock); a second launch is told so in one plain line and exits. The
port and key go to run/server.json, so a developer tool can attach to the game's own server (attach()) and never starts a second
one while the game is open (refuse_unless_attached).

Under MERAVIA_NO_SERVER (the suite) nothing is ever spawned: load() raises NoServer."""

from __future__ import annotations

import json
import os
import queue
import re
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

import config
from core import paths
from llm import llama
from llm import worker as worker_mod
from llm.errors import Failure, NoServer

STATES = ("not_started", "loading", "ready", "restarting", "failed")
SETTINGS = Path(paths.BUNDLE) / "data" / "runtime" / "server.yaml"
PHASES = [("load_model: loading model", 0.10), ("threadpool init", 0.45), ("loading draft model", 0.60),
          ("initializing, n_slots", 0.85), ("model loaded", 0.95)]       # the log's phases, and how far through the load each is


def settings(path: Path | str | None = None) -> dict:
    return yaml.safe_load(Path(path or SETTINGS).read_text(encoding="utf-8")) or {}


def exe_name() -> str:
    return "llama-server.exe" if os.name == "nt" else "llama-server"


def no_server() -> bool:
    return os.environ.get("MERAVIA_NO_SERVER", "").strip() not in ("", "0")


# ------------------------------------------------------------------ the settings' check

def runtime_problems(cfg: dict | None = None, check_files: bool = False, runtime: Path | None = None, models: Path | None = None) -> list[str]:
    """What the settings must hold for the game to run: each slot's context holds the largest prompt the game sends (its ceiling, in
    characters, at the budget's characters a token) and twice the largest answer (the validation retry resends the draft); exactly one
    embedder; every file named once with its checksum and size; and, outside the tests (check_files), the files present."""
    cfg = settings() if cfg is None else cfg
    bad: list[str] = []
    s = cfg.get("server") or {}
    slot_ctx, slots = s.get("slot_ctx"), s.get("slots")
    if not isinstance(slot_ctx, int) or slot_ctx <= 0 or not isinstance(slots, int) or slots < 1:
        return ["data/runtime/server.yaml server: slot_ctx and slots must be whole numbers above zero"]
    need = needed_context()
    if slot_ctx < need:
        bad.append(f"data/runtime/server.yaml server.slot_ctx: {slot_ctx} tokens cannot hold the largest prompt and twice the largest answer "
                   f"({need} tokens)")
    for k in ("batch", "ubatch", "cache_ram_mib", "start_seconds", "hang_seconds", "restarts", "max_cancels"):
        v = s.get(k)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            bad.append(f"data/runtime/server.yaml server.{k}: a whole number, zero or more")
    idle = s.get("resume_idle_seconds")
    if isinstance(idle, bool) or not isinstance(idle, (int, float)) or idle < 0:
        bad.append("data/runtime/server.yaml server.resume_idle_seconds: a number of seconds, zero or more")
    models_ = cfg.get("models") or {}
    embedders = [k for k, m in models_.items() if (m or {}).get("role") == "embed"]
    if len(embedders) != 1:
        bad.append(f"data/runtime/server.yaml models: exactly one embedder (role embed), not {len(embedders)}")
    for role in ("chat", "draft"):
        if not any((m or {}).get("role") == role for m in models_.values()):
            bad.append(f"data/runtime/server.yaml models: no model with role {role}")
    files = [("models." + k, m) for k, m in models_.items()] + \
            [(f"builds.{b.get('id')}.{b.get('platform')}", f) for b in cfg.get("builds") or [] for f in b.get("files") or []]
    for where, f in files:
        f = f or {}
        if not re.fullmatch(r"[0-9a-f]{64}", str(f.get("sha256") or "")):
            bad.append(f"data/runtime/server.yaml {where}: a sha256 of 64 hex characters")
        if not isinstance(f.get("size"), int) or f.get("size", 0) <= 0:
            bad.append(f"data/runtime/server.yaml {where}: a size in bytes")
    if check_files and not no_server():
        for k, m in models_.items():
            if not ((models or paths.MODELS) / str(m.get("file") or "")).is_file():
                bad.append(f"the model file {m.get('file')} is missing from {models or paths.MODELS}")
        if not any(((runtime or paths.RUNTIME) / str(b.get("id")) / exe_name()).is_file() for b in cfg.get("builds") or []
                   if b.get("platform") == platform()):
            bad.append(f"no llama-server build in {runtime or paths.RUNTIME}")
    return bad


def needed_context() -> int:
    """The tokens one slot must hold: the largest prompt ceiling the game measures (data/measured/prompt_ceilings.yaml) at the budget's
    characters a token, plus twice the largest answer any call asks for (config's and the generate() sites' max_tokens)."""
    import math
    root = Path(paths.BUNDLE)
    try:
        ceilings = yaml.safe_load((root / "data" / "measured" / "prompt_ceilings.yaml").read_text(encoding="utf-8")) or {}
        chars = max(int((v or {}).get("chars") or 0) for v in (ceilings.get("ceilings") or {}).values())
    except Exception:
        chars = 36500
    try:
        cpt = float((yaml.safe_load((root / "data" / "rules" / "budget.yaml").read_text(encoding="utf-8")) or {}).get("chars_per_token") or 4.0)
    except Exception:
        cpt = 4.0
    return math.ceil(chars / cpt) + 2 * largest_answer()


def largest_answer() -> int:
    import ast
    most = max(int(getattr(config, "MAX_TOKENS", 0) or 0), int(getattr(config, "PROSE_MAX_TOKENS", 0) or 0))
    root = Path(paths.BUNDLE)
    for d in ("engine", "scenes", "npc", "character", "llm", "services"):
        for p in sorted((root / d).rglob("*.py")):
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, OSError):
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.keyword) and n.arg == "max_tokens" and isinstance(n.value, ast.Constant) and isinstance(n.value.value, int):
                    most = max(most, n.value.value)
    return most


def platform() -> str:
    return "windows" if os.name == "nt" else "linux"


# ------------------------------------------------------------------ starting a child

def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def chat_argv(exe: Path, cfg: dict, port: int, key: str, models: Path) -> list[str]:
    s, m = cfg["server"], cfg["models"]
    chat = next(v for v in m.values() if v.get("role") == "chat")
    draft = next((v for v in m.values() if v.get("role") == "draft"), None)
    ctx = int(s["slots"]) * int(s["slot_ctx"])
    argv = [str(exe), "--model", str(models / chat["file"]), "--host", "127.0.0.1", "--port", str(port), "--api-key", key, "--no-webui",
            "--jinja", "-np", str(s["slots"]), "-c", str(ctx), "--fit", "on", "--fit-ctx", str(ctx),
            "--cache-ram", str(s["cache_ram_mib"]), "--flash-attn", "auto", "-b", str(s["batch"]), "-ub", str(s["ubatch"])]
    if draft is not None:
        argv += ["--spec-type", "draft-mtp", "--spec-draft-n-max", str(s.get("draft_n_max", 3)), "--spec-draft-backend-sampling",
                 "--spec-draft-model", str(models / draft["file"])]
    threads = int(s.get("threads") or 0) or int(getattr(config, "NUM_THREAD", 0) or 0)
    if threads:
        argv += ["-t", str(threads)]
    return argv


def _pdeathsig():                                   # Linux: the child is told to end when the thread that started it ends
    try:
        import ctypes
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0)     # PR_SET_PDEATHSIG
    except Exception:
        pass


class _Job:
    """Windows: a Job Object that kills every process in it when the game's last handle to it closes (the game ending however it ends)."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k = k
        self.handle = k.CreateJobObjectW(None, None)

        class LIMITS(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("r", "w", "o", "rt", "wt", "ot")]

        class EXT(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", LIMITS), ("IoInfo", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
        info = EXT()
        info.BasicLimitInformation.LimitFlags = 0x2000      # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        k.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info))   # JobObjectExtendedLimitInformation

    def add(self, proc) -> None:
        self.k.AssignProcessToJobObject(self.handle, int(proc._handle))


class Spawner:
    """The one long-lived thread every child is started from."""

    def __init__(self):
        self._q: queue.Queue = queue.Queue()
        self._job = None
        self._thread = threading.Thread(target=self._run, name="llama-spawner", daemon=True)
        self._thread.start()

    def _run(self):
        while True:
            argv, log, env, box = self._q.get()
            try:
                box["proc"] = self._start(argv, log, env)
            except BaseException as e:      # handed back to the caller
                box["error"] = e
            finally:
                box["done"].set()

    def _start(self, argv, log, env):
        kw = dict(stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, close_fds=True)
        if os.name == "nt":
            kw["creationflags"] = 0x00000200 | 0x08000000             # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
            proc = subprocess.Popen(argv, **kw)
            if self._job is None:
                self._job = _Job()
            self._job.add(proc)
            return proc
        return subprocess.Popen(argv, start_new_session=True, preexec_fn=_pdeathsig, **kw)

    def start(self, argv, log, env=None) -> subprocess.Popen:
        box = {"done": threading.Event()}
        self._q.put((argv, log, env, box))
        box["done"].wait()
        if "error" in box:
            raise box["error"]
        return box["proc"]


_SPAWNER: Spawner | None = None
_SPAWNER_LOCK = threading.Lock()


def spawner() -> Spawner:
    global _SPAWNER
    with _SPAWNER_LOCK:
        if _SPAWNER is None:
            _SPAWNER = Spawner()
        return _SPAWNER


# ------------------------------------------------------------------ a child left by a crashed game

def exe_of(pid: int) -> str | None:
    """The executable a running process was started from, or None (not running, or not ours to read)."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            h = k.OpenProcess(0x1000, False, int(pid))                 # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return None
            try:
                buf = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(buf))
                return buf.value if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)) else None
            finally:
                k.CloseHandle(h)
        return os.path.realpath(os.readlink(f"/proc/{int(pid)}/exe"))
    except (OSError, ValueError, AttributeError):
        return None


def _kill(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(int(pid))], capture_output=True, timeout=10)
        else:
            os.kill(int(pid), signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass


def stop_stale(run_dir: Path, ours: Path) -> list[int]:
    """Stop the children a crashed game left (run/server.pid), each only when its executable is the one recorded and lies under our
    runtime folder; returns the pids stopped. The pid file goes either way."""
    p = run_dir / "server.pid"
    stopped = []
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return stopped
    root = os.path.realpath(str(ours))
    for r in rows if isinstance(rows, list) else []:
        pid, exe = int(r.get("pid") or 0), str(r.get("exe") or "")
        now = exe_of(pid) if pid else None
        if now and os.path.realpath(exe) == os.path.realpath(now) and os.path.realpath(now).startswith(root + os.sep):
            _kill(pid)
            stopped.append(pid)
    try:
        p.unlink()
    except OSError:
        pass
    return stopped


# ------------------------------------------------------------------ one game at a time

class GameLock:
    """An OS lock on run/game.lock, held while the game runs: a second game cannot start a second server on the same card."""

    def __init__(self, run_dir: Path | None = None):
        self.path = Path(run_dir or paths.RUN) / "game.lock"
        self._fh = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "a+")
        try:
            if os.name == "nt":
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False
        self._fh = fh
        return True

    def release(self) -> None:
        if self._fh is not None:
            try:
                if os.name == "nt":
                    import msvcrt
                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self._fh.close()
            self._fh = None


def game_open(run_dir: Path | None = None) -> bool:
    """Whether a game holds the lock now (another process, or this one)."""
    lock = GameLock(run_dir)
    if lock.acquire():
        lock.release()
        return False
    return True


def attach(run_dir: Path | None = None) -> llama.LlamaServer:
    """A source on the running game's own server (run/server.json), for a developer tool started with --attach."""
    p = Path(run_dir or paths.RUN) / "server.json"
    try:
        info = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Failure("unreachable", "no game's server to attach to (run/server.json)") from e
    embed = llama.Server(int(info["embed_port"]), info.get("embed_key", "")) if info.get("embed_port") else None
    return llama.LlamaServer(llama.Server(int(info["port"]), info.get("key", "")), embed,
                             machine={"slot_ctx": info.get("slot_ctx"), "slots": {"foreground": 0, "background": 1, "input": 0}})


def refuse_unless_attached(argv: list[str], run_dir: Path | None = None) -> str | None:
    """A developer tool's start-up check: while the game is open, a tool runs only with --attach (it never starts a second server);
    returns the refusal's words, or None to go on."""
    if "--attach" in argv:
        return None
    if game_open(run_dir):
        return "The game is open, and its model server with it: run this tool with --attach to use that server, or close the game first."
    return None


# ------------------------------------------------------------------ the runtime

class Child:
    def __init__(self, name: str, argv: list[str], port: int, key: str, proc: subprocess.Popen, log_path: Path):
        self.name, self.argv, self.port, self.key, self.proc, self.log_path = name, argv, port, key, proc, log_path

    def alive(self) -> bool:
        return self.proc.poll() is None


class Runtime:
    """The game's model servers: the chat server (and, with f524, the embedder), their states, their files."""

    def __init__(self, cfg: dict | None = None, runtime: Path | None = None, models: Path | None = None, run_dir: Path | None = None,
                 logs: Path | None = None, build: str | None = None):
        self.cfg = settings() if cfg is None else cfg
        self.runtime = Path(runtime or paths.RUNTIME)
        self.models = Path(models or paths.MODELS)
        self.run_dir = Path(run_dir or paths.RUN)
        self.logs = Path(logs or (Path(paths.APP) / "logs"))
        self.build = build
        self.state = "not_started"
        self.chat: Child | None = None
        self.source: llama.LlamaServer | None = None
        self.restarts_left = int((self.cfg.get("server") or {}).get("restarts", 1))
        self.facts_: dict = {}
        self.worker = None
        self._lock = threading.RLock()
        self._closed = False

    # -- files
    def exe(self) -> Path:
        """This machine's llama-server: the build asked for, else the first of this platform's builds whose program is here."""
        builds = [b for b in self.cfg.get("builds") or [] if b.get("platform") == platform()]
        ids = [self.build] if self.build else [str(b.get("id")) for b in builds]
        for i in ids:
            p = self.runtime / str(i) / exe_name()
            if p.is_file():
                self.build = str(i)
                return p
        raise Failure("unreachable", f"no llama-server build in {self.runtime}")

    def devices(self, exe: Path) -> list[str]:
        """What the build can run on (--list-devices), one line a device."""
        try:
            out = subprocess.run([str(exe), "--list-devices"], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return []
        lines = [l.strip() for l in (out.stdout or "").splitlines() + (out.stderr or "").splitlines()]
        return [l for l in lines if l and not l.lower().startswith("available devices")]

    def _write_run_files(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        c = self.chat
        info = {"port": c.port, "key": c.key, "pid": c.proc.pid, "slot_ctx": self.facts_.get("slot_ctx"), "build": self.build}
        (self.run_dir / "server.json").write_text(json.dumps(info), encoding="utf-8")
        (self.run_dir / "server.pid").write_text(json.dumps([{"pid": c.proc.pid, "exe": c.argv[0]}]), encoding="utf-8")

    def _remove_run_files(self) -> None:
        for name in ("server.json", "server.pid"):
            try:
                (self.run_dir / name).unlink()
            except OSError:
                pass

    # -- starting and waiting
    def _spawn_chat(self) -> Child:
        exe = self.exe()
        self.logs.mkdir(parents=True, exist_ok=True)
        log_path = self.logs / "llama-server.log"
        port, key = free_port(), secrets.token_urlsafe(24)
        argv = chat_argv(exe, self.cfg, port, key, self.models)
        with open(log_path, "ab") as log:
            log.write(f"\n---- llama-server starting on port {port}\n".encode("utf-8"))
            log.flush()
            proc = spawner().start(argv, log)
        return Child("chat", argv, port, key, proc, log_path)

    def _tail(self, child: Child, n: int = 4000) -> str:
        try:
            with open(child.log_path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - n))
                return f.read().decode("utf-8", errors="replace")
        except OSError:
            return ""

    def _phase(self, child: Child, start_at: int) -> float:
        try:
            with open(child.log_path, "rb") as f:
                f.seek(start_at)
                text = f.read().decode("utf-8", errors="replace")
        except OSError:
            return 0.0
        got = 0.0
        for marker, at in PHASES:
            if marker in text:
                got = max(got, at)
        return got

    def load(self, progress=None) -> None:
        """Start the chat server and wait until it is ready; progress(fraction) only ever rises, and ends at 1.0."""
        if no_server():
            raise NoServer("MERAVIA_NO_SERVER is set: no model server is started")
        with self._lock:
            if self.state == "ready":
                return
            self._closed = False
            self.state = "loading"
            shown = [0.0]

            def tell(x):
                if progress is not None and x > shown[0]:
                    shown[0] = x
                    progress(x)
            try:
                stop_stale(self.run_dir, self.runtime)
                exe = self.exe()
                self.facts_["devices"] = self.devices(exe)
                tell(0.02)
                try:
                    log_start = os.path.getsize(self.logs / "llama-server.log")
                except OSError:
                    log_start = 0
                self.chat = self._spawn_chat()
                self._write_run_files()
                limit = float((self.cfg.get("server") or {}).get("start_seconds") or 300)
                server = llama.Server(self.chat.port, self.chat.key)
                start = time.monotonic()
                binds = 0
                while True:
                    if not self.chat.alive():
                        if "couldn't bind" in self._tail(self.chat) and binds < 3:
                            binds += 1                  # the port was taken between choosing it and binding it: another, never a failed load
                            self.chat = self._spawn_chat()
                            self._write_run_files()
                            server = llama.Server(self.chat.port, self.chat.key)
                            continue
                        self._crash_note(self.chat)
                        raise Failure("unreachable", "llama-server ended while it loaded")
                    h = server.health()
                    if h == "ready":
                        break
                    if time.monotonic() - start > limit:
                        raise Failure("loading", f"the model was still loading after {int(limit)} s")
                    tell(self._phase(self.chat, log_start))
                    time.sleep(0.1)
                self._props(server)
                s = self.cfg.get("server") or {}
                self.source = llama.LlamaServer(server, None, machine={"slot_ctx": self.facts_["slot_ctx"],
                                                                       "slots": {"foreground": 0, "background": 1, "input": 0}},
                                                worker=self.worker or worker_mod.Worker(int(s.get("max_cancels", 3)),
                                                                                        float(s.get("resume_idle_seconds", 2))))
                self.worker = self.source.worker               # (f523) one worker for the session, kept across a restart
                self._write_run_files()
                self.state = "ready"
                tell(1.0)
            except BaseException:
                self.state = "failed"
                self._stop_children()
                raise

    def _props(self, server: llama.Server) -> None:
        want = int((self.cfg.get("server") or {}).get("slot_ctx") or 0)
        status, payload, _, _ = server.request("GET", "/props", None, 10.0)
        settings_ = (payload or {}).get("default_generation_settings") or {} if isinstance(payload, dict) else {}
        granted = int(settings_.get("n_ctx") or 0)
        self.facts_.update(slot_ctx=granted or want, slots=(payload or {}).get("total_slots") if isinstance(payload, dict) else None,
                           build=self.build, offloaded=self._offloaded())
        if granted and granted < want:
            raise Failure("too_big", f"the model server granted {granted} tokens a slot, under the {want} the game needs: "
                                     "the card's memory is too small for the context")

    def _offloaded(self) -> str | None:
        m = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", self._tail(self.chat, 200000)) if self.chat else []
        return f"{m[-1][0]}/{m[-1][1]}" if m else None

    def _crash_note(self, child: Child) -> None:
        try:
            self.logs.mkdir(parents=True, exist_ok=True)
            with open(self.logs / "crash.log", "a", encoding="utf-8") as f:
                f.write(f"\n---- llama-server ({child.name}) ended with code {child.proc.poll()} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(self._tail(child, 3000) + "\n")
        except OSError:
            pass

    # -- calls, restarts
    def chat_call(self, req, deadline=None):
        """A chat through the server; a server found gone is restarted once (this call one failed try), a second death is 'failed'."""
        src = self.source
        if self.state != "ready" or src is None:
            if self.state in ("loading", "restarting"):
                self._wait_ready()
                src = self.source
            else:
                raise Failure("unreachable", f"the model server is {self.state}")
        try:
            return src.chat(req, deadline=deadline)
        except Failure as f:
            if f.kind == "unreachable" and self.chat is not None and not self.chat.alive():
                self._died()
            raise

    def _wait_ready(self, limit: float = 600.0) -> None:
        start = time.monotonic()
        while self.state in ("loading", "restarting") and time.monotonic() - start < limit:
            time.sleep(0.1)
        if self.state != "ready":
            raise Failure("unreachable", f"the model server is {self.state}")

    def _died(self) -> None:
        with self._lock:
            if self.chat is None or self.chat.alive():
                return
            self._crash_note(self.chat)
            if self.restarts_left <= 0:
                self.state = "failed"
                self._remove_run_files()
                return
            self.restarts_left -= 1
            self.state = "restarting"          # a call made meanwhile waits for the new server (chat_call), as during a load
            self.chat = None
            try:
                self._closed = False
                self.load()
            except Exception:
                self.state = "failed"

    # -- stopping
    def _stop_children(self) -> None:
        c = self.chat
        if c is not None and c.alive():
            try:
                if os.name == "nt":
                    c.proc.terminate()
                else:
                    os.killpg(c.proc.pid, signal.SIGTERM)
            except OSError:
                pass
            try:
                c.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    c.proc.kill()
                    c.proc.wait(timeout=5)
                except (OSError, subprocess.SubprocessError):
                    pass
        self._remove_run_files()

    def close(self) -> None:
        """Cancel the calls in flight, stop every child, take the run files away. Safe to call twice, and from any thread."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self.source is not None:
                self.source.cancel()
            self._stop_children()
            if self.state != "failed":
                self.state = "not_started"

    def facts(self) -> dict:
        return {"source": "llama-server", "model": config.MODEL, "embed_model": config.EMBED_MODEL, "embedder": False,
                "state": self.state, **self.facts_}


class Managed:
    """The runtime as a source on the interface (llm/backend.py): its calls go to the server it started, its close stops it."""

    name = "llama-server"

    def __init__(self, rt: Runtime):
        self.rt = rt

    def chat(self, req, deadline=None):
        return self.rt.chat_call(req, deadline)

    def embed(self, texts):
        raise Failure("unreachable", "no embedder until f524")

    def load(self, progress=None):
        self.rt.load(progress)

    def close(self):
        self.rt.close()

    def state(self):
        return self.rt.state

    def facts(self):
        return self.rt.facts()

    def cancel(self, thread_ident=None):
        return self.rt.source.cancel(thread_ident) if self.rt.source is not None else 0

    def promote(self, thread_ident):
        if self.rt.source is not None:
            self.rt.source.promote(thread_ident)

    def cancel_session(self, key):
        return self.rt.source.cancel_session(key) if self.rt.source is not None else 0

    def reopen_session(self, key):
        if self.rt.source is not None:
            self.rt.source.reopen_session(key)


# ------------------------------------------------------------------ the game's own server (main.py, behind the switch until f528)

# The two lines a player could see from here, until f526 and f527 move them into data/rules/launch.yaml once the owner has read them.
# Only DND_BACKEND=runtime reaches them before f528.
ALREADY_OPEN = "Meravia is already open in another window."
COULD_NOT_WAKE = "The game could not start its model ({why}). The details are in logs/llama-server.log."

_GAME: dict = {}


def start_for_game(progress=None, say=print) -> bool:
    """main.py's start: the lock, the files checked, the server loaded and made the interface's source. False (with one plain line said)
    when another game holds the lock or the server could not start; the game then ends."""
    from llm import backend
    lock = GameLock()
    if not lock.acquire():
        say(ALREADY_OPEN)
        return False
    problems = runtime_problems(check_files=True)
    if problems:
        lock.release()
        say(COULD_NOT_WAKE.format(why="; ".join(problems[:3])))
        return False
    rt = Runtime()
    try:
        rt.load(progress)
    except Failure as f:
        lock.release()
        say(COULD_NOT_WAKE.format(why=f.detail or f.kind))
        return False
    _GAME.update(rt=rt, lock=lock, undo=backend.use(Managed(rt)))
    import atexit
    atexit.register(stop_for_game)
    return True


def stop_for_game() -> None:
    """Stop the game's server and let the lock go: safe to call twice, and from atexit, main's finally and an update's exit alike."""
    rt, lock, undo = _GAME.pop("rt", None), _GAME.pop("lock", None), _GAME.pop("undo", None)
    if rt is not None:
        rt.close()
    if undo is not None:
        undo()
    if lock is not None:
        lock.release()
