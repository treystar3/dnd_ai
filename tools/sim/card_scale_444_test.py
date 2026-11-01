"""(f444) A measure scaled to the card the game is built for, when that card cannot be rented: Runpod has no RTX 3060, so a night is
recorded on the nearest card and every call's reading and writing time is scaled by the two cards' compute and memory bandwidth
(data/rules/cards.yaml), an estimate kept as one. And a night of several runs keeps a recording of each."""
import gzip, json, os, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import card_profile

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

C = card_profile.cards()
check("the cards the game is timed on are data, the target among them", "RTX 3060 12GB" in C and "RTX A4000" in C)
REC = Path("saves/card_scale_444_rec")
shutil.rmtree(REC, ignore_errors=True)
REC.mkdir(parents=True)
(REC / "meta.json").write_text(json.dumps({"model": "gemma4:12b"}), encoding="utf-8")
row = {"i": 0, "input": 1, "kind": "chat", "title": "Narration", "seconds": 10.0,
       "tokens": {"prompt_eval_count": 3000, "prompt_eval_duration": int(2e9), "eval_count": 200, "eval_duration": int(7e9), "load_duration": 0}}
with gzip.open(REC / "calls.jsonl.gz", "wt", encoding="utf-8") as f:
    f.write(json.dumps(row) + "\n")
src, dst = C["RTX A4000"], C["RTX 3060 12GB"]
read, write = src["tflops"] / dst["tflops"], src["bandwidth_gbs"] / dst["bandwidth_gbs"]
base, est = card_profile.measure(REC), card_profile.measure(REC, read, write)
check("a slower card takes longer to read a prompt, by the compute ratio", abs(est["read_tps"] - base["read_tps"] / read) < 0.2, (base, est))
check("...and to write an answer, by the bandwidth ratio", abs(est["write_tps"] - base["write_tps"] / write) < 0.2, (base, est))
want = 10.0 + 2.0 * (read - 1) + 7.0 * (write - 1)
check("...and the turn costs what its parts cost there, the rest as measured", abs(est["longest_turn_s"] - round(want, 1)) < 0.11,
      (est["longest_turn_s"], want))
card_profile.PROFILE = REC / "card_profile.yaml"
card_profile.write(est, "RTX 3060 12GB", "gemma4:12b", REC.name, "RTX A4000", "11.0 GB of 12 GB (fits)")
import yaml
kept = yaml.safe_load(card_profile.PROFILE.read_text(encoding="utf-8"))
check("the profile says it is an estimate, and from which card", kept["scaled_from"] == "RTX A4000" and "fits" in kept["fits"], kept)
shutil.rmtree(REC, ignore_errors=True)

# ---- the startup check keeps the cards whole
from engine import data_check
check("the startup check passes the cards as they are", not [p for p in data_check.check() if "cards.yaml" in p])

# ---- a night of several runs keeps a recording of each
OUT = Path("saves/card_scale_444_night")
shutil.rmtree(OUT, ignore_errors=True)
night = subprocess.run([sys.executable, "tools/nightrun.py", "--stub", "--runs", "2", "--turns", "3", "--record", "--out", str(OUT),
                        "--save", "card_scale_444"], capture_output=True, text=True, timeout=900)
kept = sorted(p.parent.parent.name for p in OUT.glob("*/recording/meta.json"))
check("a night of two runs keeps a recording of each", night.returncode == 0 and len(kept) == 2, (kept, (night.stdout + night.stderr)[-500:]))
shutil.rmtree(OUT, ignore_errors=True)
for p in Path("saves").glob("card_scale_444*"):
    shutil.rmtree(p, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
