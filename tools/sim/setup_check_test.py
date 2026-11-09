"""(f532) What this machine has (llm/setup_check.py), for the load screen's lines: the memory, a number of gigabytes, and nothing else:
nothing here installs, downloads or asks a server any more (the game ships its own model server and model files, and the load screen,
llm/launch.py, says in the owner's words what is missing); the card comes from the server's own device list, not from here."""
import sys
sys.path.insert(0, ".")
from llm import setup_check as sc

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

ram = sc.ram_gb()
check("the memory is a number of gigabytes", isinstance(ram, float) and ram >= 0.0, ram)
check("the load screen reads it from here", "setup_check.ram_gb()" in open("llm/launch.py", encoding="utf-8").read())
check("nothing here installs, downloads, asks a server or reads the card any more",
      not any(hasattr(sc, n) for n in ("ensure_ready", "pull_model", "install_ollama", "download_ollama", "server_up", "model_present",
                                       "base_url", "start_server", "advice", "hardware", "parse_nvidia")))
print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)
