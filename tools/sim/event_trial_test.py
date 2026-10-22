"""The event corpus (tools/event_eval.py, data/replay/event_cases.yaml) plays out right offline: a character goes through a campaign and
through cataclysms of each kind, ends them by the sword or by treaty or leaves them to run their course, and the world is sound after each."""
import sys
sys.path.insert(0, ".")
from tools import event_eval
out = event_eval.evaluate(event_eval.load_cases(), live=False)
print("\nALL PASS" if not out["wrong"] else f"\n{len(out['wrong'])} FAILED: {out['wrong']}")
sys.exit(1 if out["wrong"] else 0)
