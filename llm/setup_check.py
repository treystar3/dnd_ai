"""First-run checks: is Ollama installed and running, is the model here, can this computer run it.

main.py calls ensure_ready() before the game starts. Anything missing is fixed through a short screen (a page in the window, plain text in
the terminal) that offers to install Ollama and download the model, with a progress bar. Nothing here touches the game itself."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import config
from ui import console

OLLAMA_SETUP_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_PAGE = "https://ollama.com/download"
MODEL_GB = 9                    # about what the model takes to download; the exact size shows once the download starts
DISK_NEEDED_GB = 12             # the model plus room to work
VRAM_GOOD_GB = 10               # the whole model sits on the graphics card
VRAM_TIGHT_GB = 6               # part of it does
QUIT_WORDS = {"quit", "q", "exit", "no", "n"}


def base_url() -> str:
    host = os.environ.get("OLLAMA_HOST", "").strip() or "127.0.0.1:11434"
    if "://" not in host:
        host = "http://" + host
    if host.rstrip("/").count(":") < 2:
        host = host.rstrip("/") + ":11434"
    return host.rstrip("/")


def _get(path: str, timeout: float = 3.0):
    try:
        with urllib.request.urlopen(base_url() + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def server_up() -> bool:
    return _get("/api/version") is not None


def model_present(name: str = "") -> bool:
    name = name or config.MODEL
    data = _get("/api/tags") or {}
    have = {m.get("name", "") for m in data.get("models", [])}
    return name in have or (":" not in name and name + ":latest" in have)


def ollama_path() -> str:
    found = shutil.which("ollama")
    if found:
        return found
    for var, sub in (("LOCALAPPDATA", "Programs/Ollama/ollama.exe"), ("ProgramFiles", "Ollama/ollama.exe")):
        base = os.environ.get(var)
        if base and (Path(base) / sub).exists():
            return str(Path(base) / sub)
    return ""


def start_server(wait: float = 25.0) -> bool:
    """Start Ollama in the background if it is installed but not running."""
    if server_up():
        return True
    exe = ollama_path()
    if not exe:
        return False
    flags = (getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)) if sys.platform == "win32" else 0
    try:
        subprocess.Popen([exe, "serve"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
    except OSError:
        return False
    end = time.time() + wait
    while time.time() < end:
        if server_up():
            return True
        time.sleep(0.5)
    return False


# ---------- this computer ----------
def parse_nvidia(text: str) -> tuple[str, float]:
    """The biggest card in nvidia-smi's 'name, MiB' lines, as (name, GB). ('', 0) if none."""
    best = ("", 0.0)
    for line in text.strip().splitlines():
        name, _, mem = line.rpartition(",")
        try:
            gb = float(mem.strip()) / 1024
        except ValueError:
            continue
        if gb > best[1]:
            best = (name.strip(), gb)
    return best


def ram_gb() -> float:
    try:
        if sys.platform == "win32":
            import ctypes

            class MEM(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("avail", ctypes.c_ulonglong),
                            ("pt", ctypes.c_ulonglong), ("pa", ctypes.c_ulonglong), ("vt", ctypes.c_ulonglong), ("va", ctypes.c_ulonglong),
                            ("ext", ctypes.c_ulonglong)]
            m = MEM(); m.length = ctypes.sizeof(MEM)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.total / 2 ** 30
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
    except Exception:
        return 0.0


def hardware() -> dict:
    gpu, vram = "", 0.0
    exe = shutil.which("nvidia-smi")
    if exe:
        try:
            out = subprocess.run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=8,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            gpu, vram = parse_nvidia(out)
        except Exception:
            pass
    try:
        free = shutil.disk_usage(Path.home()).free / 2 ** 30
    except OSError:
        free = 0.0
    return {"gpu": gpu, "vram_gb": round(vram, 1), "ram_gb": round(ram_gb(), 1), "disk_free_gb": round(free, 1)}


def advice(hw: dict) -> tuple[str, str]:
    """('good' | 'tight' | 'low' | 'unknown', a sentence for the player)."""
    vram = hw.get("vram_gb", 0)
    if not hw.get("gpu"):
        return "unknown", ("No NVIDIA graphics card was found. The game can still run on the processor, but replies will be slow. "
                           "(An AMD or Apple graphics card is not detected here and may work fine.)")
    if vram >= VRAM_GOOD_GB:
        return "good", f"{hw['gpu']} ({vram:.0f} GB) is plenty for the game's model."
    if vram >= VRAM_TIGHT_GB:
        return "tight", f"{hw['gpu']} ({vram:.0f} GB) can only hold part of the model, so replies will be slower than they should be."
    return "low", f"{hw['gpu']} ({vram:.0f} GB) is too small for the model. The game will run mostly on the processor and be very slow."


# ---------- installing and downloading ----------
def download_ollama(on_progress) -> str:
    target = Path(tempfile.gettempdir()) / "OllamaSetup.exe"
    with urllib.request.urlopen(OLLAMA_SETUP_URL, timeout=30) as r, open(target, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk); done += len(chunk)
            on_progress((done / total) if total else 0.0, f"Downloading Ollama  {done / 2 ** 20:.0f} MB")
    return str(target)


def install_ollama(on_progress) -> bool:
    """Download Ollama's own Windows installer and run it quietly. Windows may ask permission once."""
    if sys.platform != "win32":
        return False
    setup = download_ollama(on_progress)
    on_progress(1.0, "Installing Ollama - Windows may ask for permission...")
    subprocess.run([setup, "/SILENT", "/NORESTART"], check=False)
    end = time.time() + 120
    while time.time() < end and not ollama_path():
        time.sleep(1)
    return bool(ollama_path())


def pull_model(on_progress, name: str = "") -> None:
    import ollama
    name = name or config.MODEL
    last = 0.0
    for ev in ollama.Client(host=base_url()).pull(name, stream=True):
        get = (lambda k: getattr(ev, k, None)) if not isinstance(ev, dict) else ev.get
        status, done, total = get("status") or "", get("completed") or 0, get("total") or 0
        if total and time.time() - last < 0.2 and done < total:
            continue
        last = time.time()
        on_progress((done / total) if total else 0.0,
                    f"{status}  {done / 2 ** 30:.1f} / {total / 2 ** 30:.1f} GB" if total else status)


# ---------- the screen ----------
def _choice(title: str, lines: list[str], buttons: list[tuple[str, str]]) -> str:
    console.setup({"title": title, "lines": lines, "buttons": [list(b) for b in buttons], "progress": None})
    answer = console.ask().strip().lower()
    return "quit" if answer in QUIT_WORDS else answer


def _progress_runner(title: str, work) -> str | None:
    """Run work(on_progress) with the progress bar showing; returns an error text or None."""
    console.setup({"title": title, "lines": [], "buttons": [], "progress": {"frac": 0.0, "text": "Starting..."}})
    try:
        work(console.setup_progress)
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return None


def ensure_ready() -> bool:
    """True when the game can start; False when the player chose to quit. Fixes what it can along the way."""
    if os.environ.get("DND_SKIP_SETUP"):
        return True
    try:
        while True:
            if not server_up():
                if ollama_path():
                    console.setup({"title": "Starting Ollama", "lines": ["Ollama is installed. Starting it..."], "buttons": [], "progress": None})
                    if start_server():
                        continue
                    pick = _choice("Ollama would not start", ["Ollama is installed but did not start. Open it from the Start menu, then check again."],
                                   [("Check again", "retry"), ("Quit", "quit")])
                    if pick == "quit":
                        return False
                    continue
                lines = ["The game talks to a local AI program called Ollama, and it is not installed on this computer.",
                         f"It is free, about 1 GB, and runs entirely on your machine. ({OLLAMA_PAGE})"]
                buttons = ([("Install Ollama", "install")] if sys.platform == "win32" else []) + [("Check again", "retry"), ("Quit", "quit")]
                if sys.platform != "win32":
                    lines.append("Install it from the page above, start it, then check again.")
                pick = _choice("Ollama is needed", lines, buttons)
                if pick == "quit":
                    return False
                if pick == "install":
                    error = _progress_runner("Installing Ollama", lambda cb: install_ollama(cb))
                    if error or not ollama_path():
                        _choice("Ollama was not installed", [error or "The installer did not finish.", f"You can install it yourself from {OLLAMA_PAGE}."],
                                [("Check again", "retry"), ("Quit", "quit")])
                continue
            if model_present():
                console.setup_done()
                return True
            hw = hardware()
            level, note = advice(hw)
            lines = [f"The game needs one AI model, {config.MODEL}, downloaded once (roughly {MODEL_GB} GB).", note]
            if hw["disk_free_gb"] and hw["disk_free_gb"] < DISK_NEEDED_GB:
                lines.append(f"Only {hw['disk_free_gb']:.0f} GB of disk space is free here; about {DISK_NEEDED_GB} GB is needed.")
            pick = _choice("Download the game's model", lines, [("Download", "download"), ("Quit", "quit")])
            if pick == "quit":
                return False
            if pick == "download":
                error = _progress_runner(f"Downloading {config.MODEL}", pull_model)
                if error:
                    pick = _choice("The download stopped", [error, "You can try again; it picks up where it left off."], [("Try again", "retry"), ("Quit", "quit")])
                    if pick == "quit":
                        return False
    finally:
        console.setup_done()
