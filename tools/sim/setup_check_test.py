"""First-run checks: reading what is installed, judging the computer, and the screens that fix what is missing (all with fakes: nothing is downloaded)."""
import sys, os
sys.path.insert(0, ".")
from llm import setup_check as sc
from ui import console

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

os.environ.pop("OLLAMA_HOST", None)
check("default address", sc.base_url() == "http://127.0.0.1:11434")
os.environ["OLLAMA_HOST"] = "10.0.0.5"; check("a bare host gets scheme and port", sc.base_url() == "http://10.0.0.5:11434", sc.base_url())
os.environ["OLLAMA_HOST"] = "http://box:9999/"; check("a full address is kept", sc.base_url() == "http://box:9999")
os.environ.pop("OLLAMA_HOST")

check("the biggest card is chosen", sc.parse_nvidia("NVIDIA GeForce RTX 4070 SUPER, 12282\\nNVIDIA T400, 4096\\n".replace("\\n", "\n")) == ("NVIDIA GeForce RTX 4070 SUPER", 12282 / 1024))
check("no card", sc.parse_nvidia("") == ("", 0.0))
check("a 4070 Super is good", sc.advice({"gpu": "RTX 4070 Super", "vram_gb": 12})[0] == "good")
check("8 GB is tight", sc.advice({"gpu": "RTX 3060", "vram_gb": 8})[0] == "tight")
check("4 GB is low", sc.advice({"gpu": "GTX 1650", "vram_gb": 4})[0] == "low")
check("no card is unknown and slow", sc.advice({"gpu": "", "vram_gb": 0})[0] == "unknown")

# the screens, driven by scripted answers
shown, answers, bars = [], [], []
console.setup = lambda d: shown.append(d["title"])
console.setup_progress = lambda f, t: bars.append((f, t))
console.setup_done = lambda: shown.append("done")
console.ask = lambda main=False: answers.pop(0)
state = {"up": True, "model": True, "path": "ollama", "started": True}
sc.server_up = lambda: state["up"]
sc.model_present = lambda name="": state["model"]
sc.ollama_path = lambda: state["path"]
sc.hardware = lambda: {"gpu": "RTX 4070 Super", "vram_gb": 12.0, "ram_gb": 32, "disk_free_gb": 200}
def start():
    state["up"] = state["started"]; return state["started"]
sc.start_server = start

check("everything in place: straight in", sc.ensure_ready() is True and shown[-1] == "done")

shown.clear(); state.update(model=False); answers[:] = ["quit"]
check("model missing and the player quits", sc.ensure_ready() is False and "Download the game's model" in shown)

def fake_pull(cb, name=""):
    cb(0.5, "half"); cb(1.0, "done"); state["model"] = True
sc.pull_model = fake_pull
shown.clear(); bars.clear(); state["model"] = False; answers[:] = ["download"]
check("download pulls the model and goes on", sc.ensure_ready() is True and bars and bars[-1][0] == 1.0 and "Downloading gemma4:12b" in shown, shown)

def bad_pull(cb, name=""): raise RuntimeError("network down")
sc.pull_model = bad_pull
shown.clear(); state["model"] = False; answers[:] = ["download", "quit"]
check("a failed download offers to try again", sc.ensure_ready() is False and "The download stopped" in shown, shown)

shown.clear(); state.update(up=False, started=True, model=True)
check("Ollama installed but stopped is started for the player", sc.ensure_ready() is True and "Starting Ollama" in shown, shown)

shown.clear(); state.update(up=False, started=False, model=True); answers[:] = ["quit"]
check("Ollama that will not start is explained", sc.ensure_ready() is False and "Ollama would not start" in shown, shown)

shown.clear(); state.update(up=False, path="", started=False); answers[:] = ["quit"]
check("Ollama missing is explained", sc.ensure_ready() is False and "Ollama is needed" in shown, shown)

installed = {"n": 0}
def fake_install(cb):
    installed["n"] += 1; state["path"] = "ollama"; state["started"] = True; return True
sc.install_ollama = fake_install
shown.clear(); state.update(up=False, path="", started=True, model=True); answers[:] = ["install"]
if sys.platform == "win32":
    check("install runs the installer and goes on", sc.ensure_ready() is True and installed["n"] == 1, shown)
else:
    print("note: the install button is Windows-only; skipped on this system")
os.environ["DND_SKIP_SETUP"] = "1"; state.update(up=False, path="", model=False)
check("the skip switch passes straight through", sc.ensure_ready() is True)
print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)
