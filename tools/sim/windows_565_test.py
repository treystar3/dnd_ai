"""(f565) The suite and the game's tools behave the same on Windows as on Linux: every test runs in UTF-8 whatever the shell, the fake
llama-server is a program this OS can start, files kept in git or compared byte for byte are written with LF, and a glyph printed to a
redirected console never crashes the game."""
import ast, importlib.util, os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 61))

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

ROOT = Path(".").resolve()
tmp = Path(tempfile.mkdtemp(prefix="win565_"))
plain = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}

# ---- every test the suite runs is in UTF-8, whatever the shell that started the suite
spec = importlib.util.spec_from_file_location("run_suite", ROOT / "tools" / "run_suite.py")
run_suite = importlib.util.module_from_spec(spec); spec.loader.exec_module(run_suite)
probe = tmp / "glyph_probe_test.py"
probe.write_text("import sys\nprint('⚔ ₲ ✓', sys.flags.utf8_mode)\nprint(open(__file__).read()[:3])\n", encoding="utf-8")
saved = dict(os.environ); os.environ.clear(); os.environ.update(plain)
try:
    name, rc, _ = run_suite.run_one(probe, tmp, 60)
finally:
    os.environ.clear(); os.environ.update(saved)
out = (tmp / f"{probe.name}.out").read_text(encoding="utf-8", errors="replace")
check("a test prints glyphs and reads UTF-8 files under the suite, with no UTF-8 setting in the shell", rc == 0 and "⚔ ₲ ✓ 1" in out, out[-300:])

# ---- the fake llama-server is a program this OS starts
sys.path.insert(0, str(ROOT / "tools" / "sim"))
import fake_runtime
from llm import runtime
exe = tmp / "cuda" / runtime.exe_name()
exe.parent.mkdir()
fake_runtime.write_exe(exe, "#!python\nimport os, sys\nprint('fake', os.path.basename(os.path.dirname(os.path.abspath(sys.argv[0]))), sys.argv[1:])\n")
r = subprocess.run([str(exe), "--port", "8"], capture_output=True, text=True, timeout=60)
check("the fake server starts as a program, sees its arguments and knows its build folder", r.returncode == 0 and "fake cuda ['--port', '8']" in r.stdout,
      (r.returncode, r.stdout, r.stderr[-300:]))

# ---- files kept in git or compared byte for byte are written with LF
spec = importlib.util.spec_from_file_location("card_profile", ROOT / "tools" / "card_profile.py")
card_profile = importlib.util.module_from_spec(spec); spec.loader.exec_module(card_profile)
card_profile.PROFILE = tmp / "card_profile.yaml"
card_profile.write({"calls": 1, "turns": 1, "read_tps": 1.0, "write_tps": 1.0, "embed_s": 0.1, "load_s": 1.0, "median_turn_s": 1.0,
                    "p95_turn_s": 1.0, "longest_turn_s": 1.0, "over": []}, "card", "model", "source")
check("the measured card profile is written with LF", b"\r\n" not in card_profile.PROFILE.read_bytes())

LF_WRITERS = ["engine/recording.py", "tools/card_profile.py", "tools/rerun.py", "tools/situation_ab.py", "tools/think_ab.py", "tools/nightrun.py"]
def text_writes(path):
    """Every write_text, and every open/gzip.open in a text write mode, without newline=."""
    out = []
    for node in ast.walk(ast.parse((ROOT / path).read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or not isinstance(node.func, (ast.Attribute, ast.Name)):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        where = list(node.args[:2]) + [k.value for k in node.keywords if k.arg == "mode"]   # open(p, "w"), path.open("a" if x else "w")
        mode = "".join(c.value for a in where for c in ast.walk(a) if isinstance(c, ast.Constant) and isinstance(c.value, str)
                       and c.value and set(c.value) <= set("rwaxbt+")) or None
        writes = name == "write_text" or (name == "open" and isinstance(mode, str) and ("w" in mode or "a" in mode) and "b" not in mode)
        if writes and not any(k.arg == "newline" for k in node.keywords):
            out.append(f"{path}:{node.lineno}")
    return out
loose = [w for p in LF_WRITERS for w in text_writes(p)]
check("recordings, data/measured and the A/B packs are written with newline='\\n' at every text write", not loose, loose)

# ---- a glyph to a redirected console never crashes the game
r = subprocess.run([sys.executable, "-c", "import main; main.utf8_streams(); print('⚔ the road → north')"], cwd=ROOT, env=plain,
                   capture_output=True, timeout=120)
check("the game's streams take any glyph when its output is redirected", r.returncode == 0 and "⚔".encode("utf-8") in r.stdout,
      (r.returncode, r.stderr[-400:]))

import shutil
shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
