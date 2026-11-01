"""(f443) What a turn costs on the card the game is built for, measured: tools/card_profile.py reads a recording's calls (Ollama's own
counts: tokens read and written and the time each took) and says each turn's cost, every turn over the minute, and the card's speeds,
kept for Stage 3's turn budget in data/rules/card_profile.yaml. A recording made elsewhere is re-timed on the card by tools/rerun.py
--time, which sends every recorded request to the card's model beside the replay and keeps the measures in timed.jsonl."""
import gzip, json, os, shutil, subprocess, sys, types
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import card_profile

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- a recording made on the card: its measures, read
REC = Path("saves/card_profile_443_rec")
shutil.rmtree(REC, ignore_errors=True)
REC.mkdir(parents=True)
(REC / "meta.json").write_text(json.dumps({"model": "gemma4:12b"}), encoding="utf-8")
tok = lambda p, e, s: {"prompt_eval_count": p, "prompt_eval_duration": int(p / 500 * 1e9), "eval_count": e, "eval_duration": int(e / 20 * 1e9),
                       "load_duration": int(0.05 * 1e9), "total_duration": int(s * 1e9)}
rows = [{"i": 0, "input": 1, "kind": "chat", "title": "ActionPlan", "seconds": 6.0, "tokens": tok(3000, 60, 6.0)},
        {"i": 1, "input": 1, "kind": "chat", "title": "Narration", "seconds": 14.0, "tokens": tok(2000, 250, 14.0)},
        {"i": 2, "input": 2, "kind": "chat", "title": "ActionPlan", "seconds": 7.0, "tokens": tok(3000, 60, 7.0)},
        {"i": 3, "input": 3, "kind": "chat", "title": "Narration", "seconds": 45.0, "tokens": tok(2500, 800, 45.0)},
        {"i": 4, "input": 3, "kind": "chat", "title": "NPCReply", "seconds": 30.0, "tokens": tok(7500, 300, 30.0)}]
with gzip.open(REC / "calls.jsonl.gz", "wt", encoding="utf-8") as f:
    f.writelines(json.dumps(r) + "\n" for r in rows)
m = card_profile.measure(REC)
check("each turn's cost is the sum of its calls", m["turns"] == 3 and m["longest_turn_s"] == 75.0 and m["median_turn_s"] == 20.0, m)
check("...and a turn over the minute is named", m["over"] == [(3, 75.0)], m["over"])
check("the card's speeds: tokens a second read and written, and a load", m["read_tps"] == 500.0 and m["write_tps"] == 20.0 and m["load_s"] == 0.05, m)
card_profile.PROFILE = REC / "card_profile.yaml"
card_profile.write(m, "RTX 3060 12GB", "gemma4:12b", REC.name)
import yaml
kept = yaml.safe_load(card_profile.PROFILE.read_text(encoding="utf-8"))
check("...kept for the turn budget to read", kept["card"] == "RTX 3060 12GB" and kept["prompt_tokens_per_second"] == 500.0
      and kept["answer_tokens_per_second"] == 20.0 and kept["turns_over_budget"] == 1, kept)
shutil.rmtree(REC, ignore_errors=True)

# ---- a recording made elsewhere, re-timed on the card beside its replay
REC2 = Path("saves/card_profile_443_stub")
shutil.rmtree(REC2, ignore_errors=True)
made = subprocess.run([sys.executable, "tools/rerun.py", "--make", str(REC2), "--inputs", "8"], capture_output=True, text=True, timeout=600,
                      env={**os.environ, "PYTHONHASHSEED": "1"})
check("a short stub session is recorded to re-time", made.returncode == 0, (made.stdout + made.stderr)[-400:])
asked = []
class Card:
    def __init__(self, host=None, timeout=None):
        self.host = host
    def chat(self, **k):
        asked.append(k)
        return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content="{}"), **tok(1200, 90, 5.0))
    def embed(self, **k):
        asked.append(k)
        return types.SimpleNamespace(embeddings=[[0.0]])
import ollama
ollama.Client = Card
import rerun
recorded = rerun.load(REC2)["calls"]
out = rerun.replay(REC2, on_call=rerun.timer(REC2, "http://the-card:11434"))
timed = [json.loads(l) for l in (REC2 / "timed.jsonl").read_text(encoding="utf-8").splitlines()]
check("the replay still matches while the card is asked beside it", out["parted"] is None and out["matched"] == out["of"], out)
check("...every recorded request is sent to the card, as recorded", len(asked) == len(recorded) == len(timed)
      and [a.get("messages") for a in asked] == [c["request"].get("messages") for c in recorded], (len(asked), len(recorded), len(timed)))
check("...and the card's measures are what the profile reads", card_profile.measure(REC2)["read_tps"] == 500.0)
shutil.rmtree(REC2, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
