"""(f560) The data hash names the game, not the machine's line endings: a checkout with CRLF text files (Windows, core.autocrlf)
hashes the same as one with LF, so a golden recorded on one replays on the other. Binary files are hashed as they are."""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 38))
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

tmp = Path(tempfile.mkdtemp(prefix="datahash_560_"))
shutil.copytree("data", tmp / "data", ignore=shutil.ignore_patterns("replay", "measured", "runtime"))
texts = [f for f in sorted((tmp / "data").rglob("*.yaml")) if b"\r\n" not in f.read_bytes()]
check("the copy has LF text files to convert", len(texts) > 10, len(texts))
lf = statehash.data_hash(tmp)
check("an LF copy of data/ hashes the same as this checkout", lf == statehash.data_hash())

for f in texts:
    f.write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
check("...and the same with every YAML file in CRLF", statehash.data_hash(tmp) == lf)

f = texts[0]
f.write_bytes(f.read_bytes() + b"# a changed rule\r\n")
check("a changed rule still changes the hash", statehash.data_hash(tmp) != lf)
f.write_bytes(f.read_bytes().replace(b"# a changed rule\r\n", b""))
check("...and taking the change out restores it", statehash.data_hash(tmp) == lf)

blob = tmp / "data" / "f560_blob.bin"
blob.write_bytes(b"\0\x01\r\n\x02")
with_crlf = statehash.data_hash(tmp)
blob.write_bytes(b"\0\x01\n\x02")
check("a binary file (one with a NUL byte) is hashed as it is, CRLF and all", statehash.data_hash(tmp) != with_crlf)

shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
