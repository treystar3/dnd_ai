"""(f526) The load screen and slow machines: what the game does between its window opening and its first model call, and how it plays
on a machine below the minimum card. Behind the switch until f528 (only DND_BACKEND=runtime reaches it), and dormant until f527: the
player's lines live in data/rules/launch.yaml, which the owner reads first; with no lines there, main.py starts the server as f522 does
(the could-not-wake and already-open lines of llm/runtime.py) and nothing here is shown.

The owner's decisions of 5 Nov (GOALS.md, Bundle F's survey and design rows):
- The home page shows while the model loads; Continue waits for it behind one plain loading line, and the load is never inside the 60
  seconds. New Game's who-you-were page and fixed opening open while it loads; its first model call waits behind the same line.
- At the minimum: an NVIDIA card of 12 GB or more through CUDA, or any card of 16 GB or more through Vulkan, with the whole model on the
  card. Faster cards play the minimum card's game, faster. Below it the game still plays, with one plain line on the load screen that
  it will be slow, once each launch: only the time limits are lifted (budget.deadline() is None, and a call outside a turn keeps the
  hang guard of data/runtime/server.yaml, 30 minutes, not the 120 seconds), and turns are still priced as on the minimum card, so a
  slow machine plays the 3060's game, slowly but whole.
- A supported card that cannot load the model offers "Play slowly on the processor" beside Try again and Quit; a machine that cannot
  hold the model at all is told the memory it needs.

The device ladder (the build is chosen, then the device): the CUDA build when --list-devices shows an NVIDIA device; otherwise the
Vulkan build, on the device with the most memory; otherwise the processor build."""

from __future__ import annotations

import math
import re
import threading
from pathlib import Path

import yaml

from core import paths

LINES_PATH = Path(paths.BUNDLE) / "data" / "rules" / "launch.yaml"
KEYS = {                     # each line the screen can show, and the placeholders it may fill
    "loading": set(),        # the one line while Continue (or a model call) waits for the load
    "slow": set(),           # the slow-machine warning, once each launch
    "damaged": {"why"},      # the game's own files are missing or wrong (runtime_problems)
    "could_not_wake": {"why"},   # the load failed: the page above Try again and Quit
    "already_open": set(),   # a second copy of the game
    "no_memory": {"needed"},  # the machine cannot hold the model at all, even on the processor
    "try_again": set(), "quit": set(), "slowly": set(),   # the could-not-wake page's choices
}


def lines() -> dict:
    """data/rules/launch.yaml's lines, or {} until the owner's are in (f527)."""
    try:
        got = yaml.safe_load(LINES_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return got if isinstance(got, dict) else {}


def line(key: str, **fill) -> str | None:
    text = lines().get(key)
    if not isinstance(text, str) or not text.strip():
        return None
    for k, v in fill.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def screen_on() -> bool:
    """The load screen is on once the owner's lines are in (every key has its line); until then main.py starts the server as before."""
    got = lines()
    return all(isinstance(got.get(k), str) and got[k].strip() for k in KEYS)


def problems() -> list[str]:
    """The startup check of data/rules/launch.yaml, once it is there: every line known, placeholders its own, no machinery, no dash."""
    if not LINES_PATH.exists():
        return []
    from engine.failures import DASH, MACHINERY
    bad = []
    got = lines()
    if not got:
        return ["data/rules/launch.yaml: a mapping of the load screen's lines"]
    for k, text in got.items():
        if k not in KEYS:
            bad.append(f"data/rules/launch.yaml {k}: no such line (one of {', '.join(sorted(KEYS))})")
            continue
        if not isinstance(text, str) or not text.strip():
            bad.append(f"data/rules/launch.yaml {k}: a line of text")
            continue
        if MACHINERY.search(text.replace("{why}", "").replace("{needed}", "")):
            bad.append(f"data/rules/launch.yaml {k}: '{text}' speaks of the machinery; say it in the world's words")
        if DASH.search(text):
            bad.append(f"data/rules/launch.yaml {k}: '{text}' carries a dash; the page carries none")
        stray = set(re.findall(r"\{(\w+)\}", text)) - KEYS[k]
        if stray:
            bad.append(f"data/rules/launch.yaml {k}: '{text}' names {sorted(stray)}, which this line cannot fill")
    missing = [k for k in KEYS if k not in got]
    if missing:
        bad.append(f"data/rules/launch.yaml: no line for {', '.join(missing)}")
    return bad


# ------------------------------------------------------------------ the devices, the ladder, the class

_DEVICE = re.compile(r"^\s*(?P<api>CUDA|Vulkan|ROCm|HIP|SYCL|Metal|BLAS)(?P<n>\d+)\s*:\s*(?P<name>.+?)\s*\((?P<mib>\d+)\s*MiB", re.I)


def parse_devices(listed: list[str]) -> list[dict]:
    """--list-devices' lines as devices: {id: 'CUDA0', api: 'cuda', name, mib}."""
    out = []
    for l in listed or []:
        m = _DEVICE.match(l)
        if m:
            api = m.group("api").lower()
            out.append({"id": f"{m.group('api')}{m.group('n')}", "api": api, "name": m.group("name").strip(), "mib": int(m.group("mib"))})
    return out


def choose_build(present: list[str], listed: dict) -> tuple[str | None, str | None]:
    """(build, device id) by the ladder, from the builds whose program is here and each one's --list-devices: CUDA with an NVIDIA
    device; else Vulkan on its device with the most memory; else the processor."""
    if "cuda" in present:
        cuda = [d for d in parse_devices(listed.get("cuda") or []) if d["api"] == "cuda"]
        if cuda:
            return "cuda", None
    if "vulkan" in present:
        vk = [d for d in parse_devices(listed.get("vulkan") or []) if d["api"] == "vulkan"]
        if vk:
            return "vulkan", max(vk, key=lambda d: d["mib"])["id"]
    if "cpu" in present:
        return "cpu", None
    return (present[0], None) if present else (None, None)


def classify(build: str | None, device: dict | None, offloaded: str | None, cfg: dict) -> dict:
    """The machine's class: 'minimum' (at or above the minimum card, the game played at its pace) or 'below' (slow: the time limits
    lifted). At the minimum means the whole model on the card, and the card an NVIDIA one of minimum_cuda_mib through CUDA or any of
    minimum_vulkan_mib through Vulkan (data/runtime/server.yaml machine)."""
    m = cfg.get("machine") or {}
    whole = False
    if offloaded and "/" in str(offloaded):
        done, total = str(offloaded).split("/", 1)
        whole = int(done) >= int(total) > 0
    mib = int((device or {}).get("mib") or 0)
    name = str((device or {}).get("name") or "")
    if build == "cuda" and device and mib >= int(m.get("minimum_cuda_mib", 12000)) and whole:
        cls, why = "minimum", ""
    elif build == "vulkan" and device and mib >= int(m.get("minimum_vulkan_mib", 16000)) and whole:
        cls, why = "minimum", ""
    elif not device:
        cls, why = "below", "no graphics card the model can use"
    elif not whole:
        cls, why = "below", f"part of the model on the processor ({offloaded} layers on {name})"
    else:
        cls, why = "below", f"{name} has {mib} MiB, under the minimum"
    return {"class": cls, "slow": cls != "minimum", "device": name or "processor", "why": why}


def memory_needed_gib(cfg: dict) -> int:
    """What the model files take in memory, with a quarter more for the context and the program: told to a machine that cannot hold
    them at all."""
    total = sum(int((v or {}).get("size") or 0) for v in (cfg.get("models") or {}).values())
    return int(math.ceil(total * 1.25 / 2 ** 30))


def apply_slow(slow: bool, cfg: dict, source=None) -> None:
    """Below the minimum: no wall-clock cut inside a turn (budget.deadline() is None) and the hang guard outside one, on the source's
    chat server; the budget's arithmetic is untouched, so the game played is the minimum card's."""
    from engine import budget
    budget.SLOW = bool(slow)
    hang = float((cfg.get("server") or {}).get("hang_seconds") or 1800)
    srv = getattr(source, "chat_server", None)
    if srv is not None:
        srv.no_deadline = hang if slow else None


# ------------------------------------------------------------------ the load screen

class Screen:
    """The load behind the home page. begin() takes the lock, checks the files, makes the game's server the interface's source and
    starts the load on its own thread, returning at once, so the home page is drawn while it runs and New Game's first pages open; a
    model call made meanwhile waits behind the loading line (llm/runtime.py chat_call). wait() is Continue's: the loading line once,
    then True at ready, or the could-not-wake page with Try again, Play slowly on the processor (when a card failed and the processor
    build is here) and Quit. The slow warning is said once this launch, when the load finds the machine below the minimum."""

    def __init__(self, say, ask, runtime_factory=None, progress=None):
        self.say, self.ask, self.progress = say, ask, progress
        self.factory = runtime_factory
        self.rt = None
        self.lock = None
        self.undo = None
        self.thread: threading.Thread | None = None
        self.error: BaseException | None = None
        self.done = threading.Event()
        self.shown = 0.0
        self.warned = False
        self.told_loading = False

    def _tell(self, frac: float) -> None:
        if frac > self.shown and not self.done.is_set():     # progress only rises, and stops at ready
            self.shown = frac
            if self.progress is not None:
                self.progress(frac)

    def begin(self, build: str | None = None) -> bool:
        """The lock and the files, then the load on its own thread. False (with the line said) when another game is open or the files
        are damaged; the game then ends."""
        from llm import backend, runtime
        if self.lock is None:
            lock = runtime.GameLock()
            try:
                held = lock.acquire()
            except OSError as e:
                self.say(line("damaged", why=f"run/ ({e})") or runtime.COULD_NOT_WAKE.format(why=e))
                return False
            if not held:
                self.say(line("already_open") or runtime.ALREADY_OPEN)
                return False
            bad = runtime.runtime_problems(check_files=True)
            if bad:
                lock.release()
                self.say(line("damaged", why="; ".join(bad[:3])) or runtime.COULD_NOT_WAKE.format(why="; ".join(bad[:3])))
                return False
            self.lock = lock
        if self.rt is not None:
            self.rt.close()                                 # Try again, or the processor: the failed load's children are gone
        if self.undo is not None:
            self.undo()
        self.rt = (self.factory or runtime.Runtime)()
        if build:
            self.rt.build = build
        self.rt.on_wait = self.loading_line
        self.rt.on_ready = self._ready
        self.undo = backend.use(runtime.Managed(self.rt))   # a call made while it loads waits for it, never reaches another source
        self.error, self.shown = None, 0.0
        self.done.clear()

        def run():
            try:
                self.rt.load(self._tell)
            except BaseException as e:             # told by wait(); the details are in logs/llama-server.log
                self.error = e
            finally:
                self.done.set()
        self.thread = threading.Thread(target=run, name="load", daemon=True)
        self.thread.start()
        return True

    def ready(self) -> bool:
        return self.done.is_set() and self.error is None

    def loading_line(self) -> None:
        """The one loading line, once per wait (Continue's, or a model call made while the model loads)."""
        if not self.told_loading:
            self.told_loading = True
            text = line("loading")
            if text:
                self.say(text)

    def _ready(self, facts: dict) -> None:
        """The load is done: the slow warning, once each launch, on a machine below the minimum."""
        self.told_loading = False
        if facts.get("slow") and not self.warned:
            self.warned = True
            text = line("slow")
            if text:
                self.say(text)

    def wait(self) -> bool:
        """Continue chosen: True at ready; False when the player quits from the could-not-wake page (or the load never began)."""
        if self.thread is None:
            return False
        while True:
            if not self.done.is_set():
                self.loading_line()
                self.done.wait()
            self.told_loading = False
            if self.error is None:
                return True
            choice = self._could_not_wake()
            if choice == "quit":
                self.close()
                return False
            if not self.begin(build="cpu" if choice == "slowly" else self.rt.build):   # Try again: the same build again
                return False

    def _could_not_wake(self) -> str:
        from llm import runtime
        from llm.errors import Failure, NoServer
        e = self.error
        why = (e.detail or e.kind) if isinstance(e, Failure) else str(e) if isinstance(e, NoServer) else f"{type(e).__name__}: {e}"
        if not isinstance(e, (Failure, NoServer)):
            from engine import crashlog
            crashlog.record(e, "starting the model server")
        cfg = self.rt.cfg if self.rt is not None else {}
        from llm import setup_check
        try:
            ram = setup_check.ram_gb()
        except Exception:
            ram = 0.0
        need = memory_needed_gib(cfg)
        if ram and ram < need:
            self.say(line("no_memory", needed=need) or runtime.COULD_NOT_WAKE.format(why=f"{need} GB of memory needed"))
        else:
            self.say(line("could_not_wake", why=why) or runtime.COULD_NOT_WAKE.format(why=why))
        cpu_here = self.rt is not None and self.rt.build != "cpu" and (self.rt.runtime / "cpu" / runtime.exe_name()).is_file()
        options = [("try_again", "again")] + ([("slowly", "slowly")] if cpu_here else []) + [("quit", "quit")]
        for i, (key, _) in enumerate(options, 1):
            self.say(f"  {i}. {line(key) or key}")
        while True:
            got = str(self.ask() or "").strip().lower()
            for i, (key, name) in enumerate(options, 1):
                if got in (str(i), name, (line(key) or "").strip().lower()):
                    return name

    def close(self) -> None:
        if self.undo is not None:
            self.undo()
            self.undo = None
        if self.rt is not None:
            self.rt.close()
        if self.lock is not None:
            self.lock.release()
            self.lock = None


SCREEN: dict = {}


def stop() -> None:
    """main.py's finally and atexit: the screen's server stopped and its lock let go, twice safe."""
    s = SCREEN.pop("screen", None)
    if s is not None:
        s.close()
