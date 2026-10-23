"""Is a newer release out? Reads the newest GitHub release of config.UPDATE_REPO (public repositories only; nothing is sent but the request).

Releases carry the installer as an attached file whose name ends in _setup.exe. The game shows an Update button; installing downloads that file,
runs it quietly and closes the game so the installer can replace it. Saves live beside the exe and are left alone by the installer.

An install is remembered (saves/update_attempt.json: which version was installed, from which). If the game comes back still reporting the
old version and the same release is still the newest, the update did not take - the usual cause is an installer built before
core/version.py was raised, so the release's game thinks it is older than the release - and the offer says so instead of looping."""

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from pathlib import Path

import config
from core.version import VERSION

SETUP_SUFFIX = "_setup.exe"


def parse(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", version.split("-")[0])[:4]) or (0,)


def newer(latest: str, current: str = VERSION) -> bool:
    a, b = parse(latest), parse(current)
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def latest_release(repo: str = "", timeout: float = 4.0) -> dict | None:
    """{'version', 'notes', 'url' (the installer file or '' ), 'page'} for the newest release, or None."""
    repo = repo or config.UPDATE_REPO
    if not repo:
        return None
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "dnd_ai-update-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    tag = str(data.get("tag_name", "")).lstrip("vV")
    if not tag:
        return None
    asset = next((a for a in data.get("assets", []) if str(a.get("name", "")).lower().endswith(SETUP_SUFFIX)), None)
    return {"version": tag, "notes": str(data.get("body") or "")[:1200], "url": (asset or {}).get("browser_download_url", ""),
            "page": data.get("html_url") or f"https://github.com/{repo}/releases"}


def attempt_file() -> Path:
    from core import paths
    return paths.APP / "saves" / "update_attempt.json"


def note_attempt(info: dict) -> None:
    """Remember the update being installed now, and the version it was installed over."""
    try:
        attempt_file().parent.mkdir(parents=True, exist_ok=True)
        attempt_file().write_text(json.dumps({"version": info.get("version", ""), "from": VERSION,
                                              "time": __import__("datetime").datetime.now().isoformat(timespec="minutes")}), encoding="utf-8")
    except OSError:
        pass


def attempted() -> dict | None:
    try:
        return json.loads(attempt_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def available(repo: str = "", timeout: float = 4.0) -> dict | None:
    """The newest release when it is newer than this game, with `current` (this game's version) and, when this very release was already
    installed and the game still reports the version it was installed over, `again`: {from, time} - the update did not take."""
    info = latest_release(repo, timeout)
    if not info or not newer(info["version"]):
        return None
    info["current"] = VERSION
    last = attempted()
    if last and last.get("version") == info["version"] and not newer(VERSION, last.get("from", "")):
        info["again"] = {"from": last.get("from", ""), "time": last.get("time", "")}
    return info


def check_in_background(on_found) -> None:
    """Look once, off the game's thread; on_found(info) runs only if there is something newer."""
    def work():
        info = available()
        if info:
            on_found(info)
    if config.UPDATE_REPO:
        threading.Thread(target=work, daemon=True, name="update-check").start()


def install(info: dict, progress, quit_game) -> str | None:
    """Download the installer and hand over to it. Returns a problem text, or None once the installer has started.
    Not in a built Windows app (or no installer attached): open the release page instead."""
    from core import paths
    if sys.platform != "win32" or not paths.FROZEN or not info.get("url"):
        webbrowser.open(info.get("page", ""))
        return None
    target = Path(tempfile.gettempdir()) / "dnd_ai_setup.exe"
    try:
        with urllib.request.urlopen(info["url"], timeout=30) as r, open(target, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk); done += len(chunk)
                progress((done / total) if total else 0.0, f"Downloading {done / 2 ** 20:.0f} MB")
        subprocess.Popen([str(target), "/SILENT", "/CLOSEAPPLICATIONS", "/NORESTART"], close_fds=True)
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    note_attempt(info)
    quit_game()
    threading.Timer(10.0, lambda: os._exit(0)).start()       # the installer needs the exe free; the game saves after every action
    return None
