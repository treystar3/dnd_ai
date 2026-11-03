"""(f457) The bots' harness lives at the repository root (simbot.py). Nine tests import it as a sibling module from this folder, so this
file stays, and is that module: loading it loads the root one under the same name."""
import importlib.util
import pathlib
import sys

_path = pathlib.Path(__file__).resolve().parents[2] / "simbot.py"
_spec = importlib.util.spec_from_file_location("simbot", _path)
_module = importlib.util.module_from_spec(_spec)
sys.modules["simbot"] = _module                   # whoever imported this name gets the root module, this file's shell discarded
_spec.loader.exec_module(_module)
