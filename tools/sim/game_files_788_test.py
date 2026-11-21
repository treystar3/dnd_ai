"""(f788) One definition of the game's own code for every fence: tools/sim/game_files.py game_files(), owned_state_633's definition.

Held here:
- the definition, on a scratch repository: every .py git lists (tracked, or not yet added and not ignored) outside tools/, data/,
  docs/ and .claude/, and not a harness at the root, is the game's; a top-level package no fence names is among them at once; with
  with_tools=True the tools and the root harnesses are too, never the tests (tools/sim); an ignored file never is;
- no test keeps a definition of its own: no literal collection in tools/sim or in a root harness holds three or more of the game's
  folders, of the folders that are not the game, or of the root harnesses' names, but game_files.py's own (each form planted and
  caught); a fence that leaves a folder out on purpose says so beside game_files();
- the twelve fences of phase 6 each see a top-level package added later: on a copy of the checkout (every file git tracks and every
  .py not yet added, as the working tree holds them) made a repository of its own, a package planted with one of each thing they
  refuse is named by each, run there as a process of its own: owned_state_633, carried_faults_781, crash_log_781b, built_check_775,
  data_check_once_776, logs_beside_exe_777, log_caps_779, own_logs_779b, datahash_tools_785 and names_vocab_786 over the game,
  audit_log_test and updates_test over the game and the tools.
What this does not read: a fence that lists the code some other way than a literal (a folder list built at run time); a fence that
reads every file of the repository (prefs_636, registers_633 and the like: they see a new package already); and the planted package
against the fences beyond the twelve, which the rule above holds to game_files() instead.
Run: python tools/sim/game_files_788_test.py"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import simlib                                                         # (f741, f779) saves and logs of the test's own
from game_files import HARNESS, NOT_GAME, game_files

bad: list[str] = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True).stdout


scratch = Path(tempfile.mkdtemp(prefix="game_files_788_")).resolve()
try:
    # ---- the definition, on a scratch repository
    repo = scratch / "repo"
    TREE = ["main.py", "config.py", "simlib.py", "smoke_test.py", "engine/a.py", "engine/smoke_test.py", "multiplayer/__init__.py",
            "multiplayer/seat.py", "tools/rerun.py", "tools/suite_ran/sitecustomize.py", "tools/sim/x_test.py", "tools/sim/helper.py",
            "data/rules/y.py", "docs/z.py", ".claude/hooks/h.py", "engine/ignored_788.py", "engine/notes.txt"]
    for rel in TREE:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text("x = 1\n", encoding="utf-8")
    (repo / ".gitignore").write_text("engine/ignored_788.py\n", encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "add", "main.py", "engine/a.py", "tools/rerun.py")          # some tracked, the rest not yet added
    got = [p.as_posix() for p in game_files(repo)]
    tooled = [p.as_posix() for p in game_files(repo, with_tools=True)]
    game = ["config.py", "engine/a.py", "engine/smoke_test.py", "main.py", "multiplayer/__init__.py", "multiplayer/seat.py"]
    check("(f788) the game's files, on a scratch repository: every .py git lists outside tools/, data/, docs/ and .claude/ and not a "
          "harness at the root, tracked or not yet added; a top-level package no fence names among them; an ignored file not",
          got == game, got)
    check("...and with_tools=True the tools and the root harnesses too, never the tests (tools/sim)",
          tooled == sorted(game + ["simlib.py", "smoke_test.py", "tools/rerun.py", "tools/suite_ran/sitecustomize.py"]), tooled)
    TOPS = {p.parts[0] for p in game_files() if len(p.parts) > 1}
    roots = {p.as_posix() for p in game_files() if len(p.parts) == 1}
    check("...and on this checkout, at least the ten folders the fences read before, and main.py and config.py at the root",
          len(TOPS) >= 10 and {"engine", "scenes"} <= TOPS and {"main.py", "config.py"} <= roots, (sorted(TOPS), sorted(roots)))

    # ---- no test keeps a definition of its own
    def copies(text: str) -> list[int]:
        """The lines of each literal collection (a tuple, list or set, or a dict's keys) holding three or more of the game's folders, of
        the folders that are not the game (with or without their slash), or of the root harnesses' names."""
        out = []
        for n in ast.walk(ast.parse(text)):
            items = n.elts if isinstance(n, (ast.Tuple, ast.List, ast.Set)) else (n.keys if isinstance(n, ast.Dict) else [])
            names = {e.value.rstrip("/") for e in items if isinstance(e, ast.Constant) and isinstance(e.value, str)}
            if len(names & TOPS) >= 3 or len(names & set(NOT_GAME)) >= 3 or len(names & HARNESS) >= 3:
                out.append(n.lineno)
        return out
    PLANTED = {
        'GAME = ("core", "engine", "llm", "scenes", "storage", "world", "ui", "npc", "character", "services")\n': True,
        'NOT_GAME = {"tools", "data", "docs", ".claude"}\n': True,
        'HARNESS = {"simlib", "simbot", "simreport", "smoke_test", "bestiary_check", "world_check"}\n': True,
        'files = [f for f in listed if not f.startswith(("docs/", ".claude/", "data/", "tools/sim/"))]\n': True,
        'ROOTS = {"tools": 1, "data": 2, "docs": 3}\n': True,
        'for d in ("engine", "scenes", "services"):\n    pass\n': True,
        'stale = [p for p in listed if not p.startswith(("docs/", "data/replay/", ".claude/"))]\n': False,
        'DIRS = ("engine", "scenes")\nWORDS = ["core", "tools"]\n': False,
    }
    wrong = {src: copies(src) for src, want in PLANTED.items() if bool(copies(src)) != want}
    check("(f788) the rule catches a definition of the game's code of a fence's own, planted (the ten folders, three of them, the folders "
          "that are not the game as a set, a tuple of prefixes and a dict's keys, the harnesses), and passes two folders, or a prefix "
          "list for another end", not wrong, wrong)
    readers = sorted(f for f in set(git(ROOT, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "tools/sim/*.py").split("\0")
                                    + [f"{h}.py" for h in HARNESS])
                     if f and f != "tools/sim/game_files.py" and (ROOT / f).is_file())
    kept = {f: copies((ROOT / f).read_text(encoding="utf-8")) for f in readers}
    kept = {f: lines for f, lines in kept.items() if lines}
    check("...and no test in tools/sim, nor a harness at the root, keeps a definition of the game's code of its own: each reads "
          "game_files()", not kept and len(readers) > 500 and "simlib.py" in readers, kept)

    # ---- the twelve fences of phase 6 each see a top-level package added later
    copy = scratch / "copy"
    listed = git(ROOT, "ls-files", "-z", "--cached").split("\0") + git(ROOT, "ls-files", "-z", "--others", "--exclude-standard", "*.py").split("\0")
    for rel in sorted(set(filter(None, listed))):
        if (ROOT / rel).is_file():
            (copy / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, copy / rel)
    git(copy, "init", "-q")
    seat = copy / "multiplayer" / "seat.py"
    seat.parent.mkdir()
    (seat.parent / "__init__.py").write_text("", encoding="utf-8")
    seat.write_text('''"""(f788) Planted by game_files_788_test in a copy of the checkout: one of each thing a fence of the game's code refuses."""
import ast
import config
import yaml
from pathlib import Path
from core import yamlio

HERE = Path(__file__).resolve().parent.parent
SEAT_LOG = HERE / "logs" / "seats.log"
SEATS_LOG = "logs/seats.jsonl"
CARDS = "data/tools/cards.yaml"
T = yamlio.safe_load(open("data/rules/seats.yaml").read())
SEATS_KEEP = getattr(config, "SEATS_KEEP", T["keep"])
TAKEN = []


def take(seat):
    TAKEN.append(seat)


def leave(seat):
    try:
        seat.close()
    except Exception:
        pass


def rules(p):
    return yaml.safe_load(p.read_text()), ast.parse(p.read_text())


def every_word(root):
    return list((root / "data").rglob("*.yaml"))


def seat_log():
    return open(config.TURN_LOG_PATH)


def updates_on():
    return config.UPDATE_CHECK


class Seat:
    def ask(self, main=False, menu=False):
        return self.inbox.get().strip()
''', encoding="utf-8", newline="\n")
    FENCES = ["owned_state_633", "carried_faults_781", "crash_log_781b", "built_check_775", "data_check_once_776", "logs_beside_exe_777",
              "log_caps_779", "own_logs_779b", "datahash_tools_785", "names_vocab_786", "audit_log", "updates"]
    parts = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    path = os.pathsep.join([str(copy)] + [p for p in parts if Path(p).resolve() != ROOT])

    def run(name: str) -> tuple[str, str]:
        own = scratch / "own" / name
        (own / "saves").mkdir(parents=True)
        (own / "logs").mkdir(parents=True)
        env = dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONUTF8="1", MERAVIA_SAVES=str(own / "saves"), MERAVIA_LOGS=str(own / "logs"),
                   PYTHONPATH=path)
        try:
            p = subprocess.run([sys.executable, f"tools/sim/{name}_test.py"], cwd=copy, env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=300)
            return name, p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return name, f"FAIL {name} ran past 300 seconds in the copy"
    with ThreadPoolExecutor(max_workers=6) as pool:
        ran = list(pool.map(run, FENCES))
    blind = {name: [l for l in out.splitlines() if l.startswith("FAIL")][:2] or out[-300:]
             for name, out in ran if not any(l.startswith("FAIL") and "multiplayer" in l for l in out.splitlines())}
    check("(f788) each of the twelve fences of phase 6 sees a top-level package added later: run on a copy of the checkout with one "
          "planted, each fails naming it (the module's state written, a fault carried on past, a channel's ask, the source read, "
          "PyYAML's loader, a path joined onto the code's folder, a log no case holds, a log setting unplaced and with a second home, a "
          "file of data/tools named, the whole of data/ read, a config read falling back to a table, the update switch read)",
          not blind, blind)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
