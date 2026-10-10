"""Where things live. Run from source, both are the project folder. Built into an exe, BUNDLE is where the packaged game data is unpacked
and APP is the folder holding the exe, where saves/ and logs/ are kept."""
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
APP = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent
