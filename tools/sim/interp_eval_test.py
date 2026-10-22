"""The interpretation corpus (tools/interp_eval.py, data/replay/interp_cases.yaml) reads right offline: every line goes where it should."""
import sys
sys.path.insert(0, ".")
from tools import interp_eval
out = interp_eval.evaluate(interp_eval.load_cases(), live=False)
print("\nALL PASS" if not out["wrong"] else f"\n{len(out['wrong'])} FAILED: {out['wrong']}")
sys.exit(1 if out["wrong"] else 0)
