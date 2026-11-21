"""(f785) What a build may leave out (engine/data_check.py UNSHIPPED: data/tools and data/replay) fails loudly from source, and only a
built game without it skips the rules held to it. Held here, on a copy of the checkout (every file git tracks, as the working tree
holds it), each folder moved aside and back and its files planted and put back:
- in this tree, from source, the rules held to data/tools and data/replay are read and hold;
- data/tools: from source a tree without the folder, or without one file of it, raises FileNotFoundError naming the file, at the door
  (_tools), in budget_problems, cards_problems and check(); a built game without it skips the rules held to it, raising nothing; a
  build that carries it reads it and runs them (they need data, not source): a card and a task planted wrong are told, and a file of
  it gone raises as from source;
- data/replay: from source a tree without it raises FileNotFoundError naming gate.yaml in gate_problems and check(), and
  fights_problems tells each golden it names as no recording kept; a built game without it skips both, raising nothing; a build that
  carries it runs them: a quick gate planted at nothing is told;
- end to end, each a process of its own from source: the copy without data/tools, and without data/replay, answers main.py --check
  with 1, the data check's problem naming the file; the copy whole answers 0.
Run: python tools/sim/tools_door_785b_test.py"""
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import simlib                                                         # (f741, f779) saves and logs of the test's own
from core import paths
from engine import data_check

bad: list[str] = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def attempt(fn):
    """fn's answer, or the exception it raised."""
    try:
        return fn()
    except Exception as e:
        return e


def shown(x):
    return f"{type(x).__name__}: {x}" if isinstance(x, BaseException) else (x[:4] if isinstance(x, list) else x)


@contextlib.contextmanager
def at(root: Path, frozen: bool):
    """The check's root at a tree and the build fact set, both put back."""
    was = paths.FROZEN, data_check.ROOT
    paths.FROZEN, data_check.ROOT = frozen, root
    try:
        yield
    finally:
        paths.FROZEN, data_check.ROOT = was


def posix(s: str) -> str:
    """A text's paths written with forward slashes (an error's repr doubles Windows' backslashes)."""
    return s.replace(chr(92) * 2, "/").replace(chr(92), "/")


def raised_for(x, rel: str) -> bool:
    """x is a FileNotFoundError naming data/<rel>."""
    return isinstance(x, FileNotFoundError) and f"data/{rel}" in posix(str(x))


def about(found, *names: str) -> list[str]:
    """The problems found that name one of these files."""
    return [p for p in found if any(n in p for n in names)] if isinstance(found, list) else []


@contextlib.contextmanager
def moved(folder: Path):
    """The folder moved aside for the block, and back after."""
    aside = folder.with_name(folder.name + "_aside_785b")
    shutil.move(str(folder), str(aside))
    try:
        yield
    finally:
        shutil.move(str(aside), str(folder))


@contextlib.contextmanager
def planted(plants: dict):
    """Each file's first `old` made `new` for the block (each must hold it), and each put back after; yields whether all held it."""
    kept = {f: f.read_text(encoding="utf-8") for f in plants}
    ok = all(old != new and old in kept[f] for f, (old, new) in plants.items())
    for f, (old, new) in plants.items():
        f.write_text(kept[f].replace(old, new, 1), encoding="utf-8", newline="\n")
    try:
        yield ok
    finally:
        for f, text in kept.items():
            f.write_text(text, encoding="utf-8", newline="\n")


scratch = Path(tempfile.mkdtemp(prefix="tools_door_785b_")).resolve()
tree = scratch / "tree"                                               # every file git tracks, as the working tree holds it
try:
    tracked = subprocess.run(["git", "ls-files", "-z", "--cached"], capture_output=True, text=True, encoding="utf-8",
                             check=True).stdout.split("\0")
    for rel in filter(None, tracked):
        if (ROOT / rel).is_file():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, tree / rel)
    tools_dir, replay_dir = tree / "data" / "tools", tree / "data" / "replay"
    check("(the copy holds the game's code, data/tools and data/replay)", (tree / "engine" / "data_check.py").is_file()
          and (tools_dir / "lora.yaml").is_file() and (tools_dir / "cards.yaml").is_file() and (replay_dir / "gate.yaml").is_file())
    env = dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONUTF8="1")

    def self_check() -> tuple[int, str]:
        p = subprocess.run([sys.executable, "main.py", "--check"], cwd=tree, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        return p.returncode, p.stdout + p.stderr

    # ---- in this tree, from source: the rules held to both folders are read and hold
    with at(ROOT, False):
        here = attempt(data_check.check)
        read = attempt(lambda: (data_check._tools("lora.yaml"), data_check._tools("cards.yaml")))
        gate = attempt(data_check.gate_problems)
        fights = attempt(data_check.fights_problems)
    check("(f785) in this tree, from source, the door reads lora.yaml and cards.yaml, and the rules held to data/tools and data/replay hold",
          isinstance(read, tuple) and all(isinstance(t, dict) and t for t in read) and isinstance(here, list)
          and not about(here, "lora.yaml", "cards.yaml", "gate.yaml", "bundle_e_fights.yaml") and gate == [] and fights == [],
          (shown(read), shown(here), shown(gate), shown(fights)))

    # ---- data/tools
    with moved(tools_dir):
        with at(tree, False):
            door = attempt(lambda: data_check._tools("lora.yaml"))
            budget = attempt(data_check.budget_problems)
            cards = attempt(data_check.cards_problems)
            whole = attempt(data_check.check)
        with at(tree, True):
            built_door = attempt(lambda: data_check._tools("lora.yaml"))
            built_got = attempt(lambda: data_check.budget_problems() + data_check.cards_problems() + data_check.check())
        code, out = self_check()
    check("(f785) from source, a tree without data/tools fails loudly: the door raises FileNotFoundError naming the file, and so do "
          "budget_problems (lora.yaml), cards_problems and check() (cards.yaml), never 0 problems",
          raised_for(door, "tools/lora.yaml") and raised_for(budget, "tools/lora.yaml") and raised_for(cards, "tools/cards.yaml")
          and raised_for(whole, "tools/cards.yaml"), (shown(door), shown(budget), shown(cards), shown(whole)))
    check("...while a built game without data/tools has no file at the door and skips the rules held to it, raising nothing",
          built_door is None and isinstance(built_got, list) and not about(built_got, "lora.yaml", "cards.yaml"),
          (shown(built_door), shown(built_got)))
    check("(f785) ...and the copy without data/tools, run from source in a process of its own, answers main.py --check with 1, the data "
          "check's problem naming data/tools/cards.yaml", code == 1 and "the data check: 1 problem" in out and "FileNotFoundError" in out
          and "data/tools/cards.yaml" in posix(out), (code, out[-600:]))
    with moved(tools_dir / "cards.yaml"):
        with at(tree, False):
            cards = attempt(data_check.cards_problems)
            lora = attempt(lambda: data_check._tools("lora.yaml"))
        with at(tree, True):
            built_cards = attempt(data_check.cards_problems)
    check("(f785) with data/tools there but cards.yaml gone, from source it raises naming cards.yaml, the file beside it read; and a "
          "build carrying data/tools is held to it whole, raising the same", raised_for(cards, "tools/cards.yaml")
          and isinstance(lora, dict) and raised_for(built_cards, "tools/cards.yaml"), (shown(cards), shown(lora), shown(built_cards)))
    with at(tree, True):
        door = attempt(lambda: (data_check._tools("lora.yaml"), data_check._tools("cards.yaml")))
        clean = attempt(data_check.check)
    with planted({tools_dir / "cards.yaml": ("  cuda: RTX 3060 12GB", "  cuda: RTX 785 nowhere"),
                  tools_dir / "lora.yaml": ("prose_tasks: [narrate,", "prose_tasks: [narrate_785, narrate,")}) as held:
        with at(tree, True):
            told = about(attempt(data_check.check), "lora.yaml", "cards.yaml")
    check("(f785) a built game carrying data/tools reads it at the door and runs the rules held to it: clean, it passes them; a card and a "
          "task planted wrong in them are told (the cards' minimum, lora.yaml's task names)",
          held and isinstance(door, tuple) and all(isinstance(t, dict) and t for t in door) and isinstance(clean, list)
          and not about(clean, "lora.yaml", "cards.yaml") and any("minimum.cuda" in p and "RTX 785 nowhere" in p for p in told)
          and any("lora.yaml" in p and "narrate_785" in p for p in told), (shown(door), shown(clean), told))

    # ---- data/replay
    with moved(replay_dir):
        with at(tree, False):
            gate = attempt(data_check.gate_problems)
            fights = attempt(data_check.fights_problems)
            whole = attempt(data_check.check)
        with at(tree, True):
            built_gate = attempt(data_check.gate_problems)
            built_fights = attempt(data_check.fights_problems)
            built_whole = attempt(data_check.check)
        code, out = self_check()
    check("(f785) from source, a tree without data/replay fails loudly: gate_problems and check() raise FileNotFoundError naming "
          "gate.yaml, and fights_problems tells each golden it names as no recording kept",
          raised_for(gate, "replay/gate.yaml") and raised_for(whole, "replay/gate.yaml") and isinstance(fights, list)
          and any("goldens." in p and "no such recording is kept" in p for p in fights), (shown(gate), shown(whole), shown(fights)))
    check("...while a built game without data/replay skips both, raising nothing", built_gate == [] and built_fights == []
          and isinstance(built_whole, list) and not about(built_whole, "gate.yaml", "bundle_e_fights.yaml"),
          (shown(built_gate), shown(built_fights), shown(built_whole)))
    check("(f785) ...and the copy without data/replay, run from source in a process of its own, answers main.py --check with 1, the "
          "data check's problem naming data/replay/gate.yaml", code == 1 and "FileNotFoundError" in out
          and "data/replay/gate.yaml" in posix(out), (code, out[-600:]))
    with planted({replay_dir / "gate.yaml": ("  cases: 60", "  cases: 0")}) as held:
        with at(tree, True):
            told = attempt(data_check.gate_problems)
    check("(f785) a built game carrying data/replay runs the rules held to it: a quick gate planted at nothing is told",
          held and isinstance(told, list) and any("quick.cases" in p for p in told), shown(told))

    code, out = self_check()
    check("...and the copy whole, from source, answers main.py --check with 0", code == 0 and "PASSED" in out, (code, out[-600:]))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
