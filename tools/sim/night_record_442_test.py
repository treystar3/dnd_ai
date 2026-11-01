"""(f442) A night run can keep its recording (tools/nightrun.py --record): a short stub night recorded in its log folder replays to the
same state, outcomes and words (tools/rerun.py). And what the player's own side asks of the model while deciding its line (the night
bot writing its words, live) is left out of the recording, since a replay feeds the line itself; a call from another thread in that
time (the background residents) is the game's and is kept."""
import json, os, shutil, subprocess, sys, threading, types, gzip
from pathlib import Path
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

OUT = Path("saves/night_record_442")
shutil.rmtree(OUT, ignore_errors=True)
night = subprocess.run([sys.executable, "tools/nightrun.py", "--stub", "--turns", "14", "--record", "--seed", "4", "--out", str(OUT),
                        "--save", "night_record_442"], capture_output=True, text=True, timeout=900, env={**os.environ, "PYTHONHASHSEED": "3"})
check("a stub night of 14 turns runs with --record", night.returncode == 0 and (OUT / "recording" / "meta.json").exists(),
      (night.stdout + night.stderr)[-800:])
again = subprocess.run([sys.executable, "tools/rerun.py", str(OUT / "recording")], capture_output=True, text=True, timeout=900,
                       env={**os.environ, "PYTHONHASHSEED": "5"})
said = (again.stdout + again.stderr).strip().splitlines()[-1:] or [""]
check("...and its recording replays to the same state, outcomes and words", again.returncode == 0 and said[0].startswith("all "), said)
shutil.rmtree(OUT, ignore_errors=True)
shutil.rmtree("saves/night_record_442", ignore_errors=True)

# ---- the player's side deciding its line is not recorded; another thread's call in that time is
import simlib
stub = simlib.Stub("warrior", 42)
simlib.install(stub)
import ui.console as uc
from engine import recording
from llm import gateway
from storage.campaign import CampaignStore
shutil.rmtree("saves/night_record_442_unit", ignore_errors=True)
store = CampaignStore.open_or_create("night_record_442_unit")
fmt = lambda title: {"title": title, "type": "object", "properties": {}}
def ask(*a, **k):
    gateway._client.chat(model="m", messages=[{"role": "user", "content": "the bot's own line"}], format=fmt("PlayerLine"))
    t = threading.Thread(target=lambda: gateway._client.chat(model="m", messages=[], format=fmt("ResidentSet")))
    t.start(); t.join()
    return "I look around."
gateway._client = types.SimpleNamespace(chat=lambda **k: types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content="{}")))
uc.ask = ask
rec = recording.Recorder(store, folder=Path("saves/night_record_442_unit_rec")).install()
uc.ask(main=True)
rec.close()
with gzip.open(Path("saves/night_record_442_unit_rec") / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
    titles = [json.loads(l)["title"] for l in f]
check("the bot's own words are left out of the recording", "PlayerLine" not in titles, titles)
check("...while a background call made in that time is kept", "ResidentSet" in titles, titles)
store.close()
shutil.rmtree("saves/night_record_442_unit", ignore_errors=True)
shutil.rmtree("saves/night_record_442_unit_rec", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
