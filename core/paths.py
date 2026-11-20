"""Where things live. Run from source, both are the project folder. Built into an exe, BUNDLE is where the packaged game data is unpacked
and APP is the folder holding the exe, where saves/ and logs/ are kept. (f531) The game depot holds the exe, data/ and the server's builds
under runtime/; the model files under models/ are a depot of their own: both beside the exe, never inside the bundle. (f777) No file
the game writes is placed from a module's own __file__, which in a built game lies inside the bundle: what was placed from __file__ or
joined onto APP by hand goes through written(). The logs and saves named relative to the working folder rely on main.py putting it at
APP in a build; RUN, RUNTIME and MODELS are placed here."""
import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
APP = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent

# (f522) The model server's files and the game's own run files, all outside data/: RUNTIME holds the llama-server builds
# (runtime/<build>/llama-server), MODELS the model files (their own Steam depot), RUN the lock and the running server's port and key
# (outside logs/, which players send). Beside the exe in a built game, in the project folder from source; never in git. (f528)
# MERAVIA_RUNTIME, MERAVIA_MODELS and MERAVIA_RUN name other folders for a developer (a night on a rented box with the files elsewhere,
# the suite's fakes, whose child processes must never probe the developer's own run/); a player never sets them.
RUNTIME = Path(os.environ.get("MERAVIA_RUNTIME") or APP / "runtime")
MODELS = Path(os.environ.get("MERAVIA_MODELS") or APP / "models")
RUN = Path(os.environ.get("MERAVIA_RUN") or APP / "run")


def written(rel) -> Path:
    """Where a file the game writes by name is placed (crash.log, the refusals, the audit log, the recordings, selfcheck.log, the
    model server's logs): a relative path under APP, asked at the call, so it lies beside the exe in a built game; an absolute path (a
    test's, a night tool's) as it is."""
    p = Path(rel)
    return p if p.is_absolute() else Path(APP) / p
