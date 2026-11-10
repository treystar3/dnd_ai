"""(f572) The data hash is the game's content only: the files under data/, the model and the save schema. The version is not in it: a
release that changes no content leaves every golden's hash as it was (the version is kept in each recording's meta, and the replay
itself catches a change in the code). A changed data file, model or save schema still changes the hash."""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 72))
import config
from core import version
from engine import recording
from storage import migrations, statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

tmp = Path(tempfile.mkdtemp(prefix="datahash_572_"))
shutil.copytree("data", tmp / "data", ignore=shutil.ignore_patterns("replay", "measured", "runtime"))
base = statehash.data_hash(tmp)

real_version = version.VERSION
try:
    version.VERSION = "99.9.9.9"
    check("a new version leaves the data hash as it was", statehash.data_hash(tmp) == base and statehash.data_hash() == statehash.data_hash())
finally:
    version.VERSION = real_version

real_model = config.MODEL
try:
    config.MODEL = real_model + "-another"
    check("another model changes it", statehash.data_hash(tmp) != base)
finally:
    config.MODEL = real_model

real_schema = migrations.CURRENT
try:
    migrations.CURRENT = real_schema + 1
    check("another save schema changes it", statehash.data_hash(tmp) != base)
finally:
    migrations.CURRENT = real_schema

rules = next(f for f in sorted((tmp / "data").rglob("*.yaml")))
rules.write_bytes(rules.read_bytes() + b"\n# a changed rule\n")
check("a changed data file changes it", statehash.data_hash(tmp) != base)
rules.write_bytes(rules.read_bytes().replace(b"\n# a changed rule\n", b""))
check("...and taking the change out restores it", statehash.data_hash(tmp) == base)

src = Path(recording.__file__).read_text(encoding="utf-8")
check("a recording still keeps the version in its meta, beside the hash", '"version": VERSION' in src and '"data": statehash.data_hash()' in src)

shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
