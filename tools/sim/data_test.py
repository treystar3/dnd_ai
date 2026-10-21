"""The character data is one system: every cross-reference resolves and every table keeps its rules (engine/data_check.py). The game
refuses to start otherwise; this keeps a broken edit from reaching a save."""
import sys
sys.path.insert(0, ".")
from engine import data_check
import yaml
bad = data_check.check()
try:
    yaml.load("a: 1\nb: 2\na: 3\n", Loader=data_check._Strict)
    bad.append("a key given twice in a data file is refused")
except ValueError:
    pass
for b in bad:
    print("FAIL", b)
print("\nFAILED: data has problems" if bad else "ALL PASS")
sys.exit(1 if bad else 0)
