"""Where things live. Run from source, both are the project folder. Built into an exe, BUNDLE is where the packaged game data is unpacked
and APP is the folder holding the exe, where saves/ and logs/ are kept."""
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
APP = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent

# (f522) The model server's files and the game's own run files, all outside data/: RUNTIME holds the llama-server builds
# (runtime/<build>/llama-server), MODELS the model files (their own Steam depot), RUN the lock and the running server's port and key
# (outside logs/, which players send). Beside the exe in a built game, in the project folder from source; never in git.
RUNTIME = APP / "runtime"
MODELS = APP / "models"
RUN = APP / "run"
