"""(f785) Files only tools read leave the game's data hash (STARTUP_DATA-8, docs/design/33_audit_fix_plan/startup_data.md; data-13).

The data hash is game content only (f572, the owner's decision of 2026-11-10). data/rules/lora.yaml (a training run), data/rules/cards.yaml
(the graphics cards a night is timed on) and two tables of towns.yaml (districts_by_scale and anchors_by_scale, the town drafter's)
are named by no module of the game, only by the tools and the startup check (engine/names.py vocab() read every YAML under data/
without naming one, until f786 pointed it at game_data()); a change to them sent every kept recording to be made again. They now live in
data/tools, and what is not the game is said once: storage/statehash.py NOT_GAME, the folders at the top of data/ outside the hash
(data/replay, data/measured, data/runtime, data/tools), game_data(), the game's data files, which the hash reads and the data words
rule (hygiene.yaml data_words) skips by, and copy_data(), a copy of data/ without those folders for a test. Held here:
- in a copy of data/, a changed line in lora.yaml, in cards.yaml or in the drafter's tables moves no data hash; a changed rule in a
  game file still does, and so does a new file under data/rules; a file under each folder NOT_GAME names moves none;
- the hash reads exactly game_data(): a change to a file it lists moves the hash, one in a folder named tools deeper in data/ among
  them, and a change to any other file under data/ moves none;
- the fence, both sides: every file of the game's data is named by a module of the game (its file name, or for a file in a folder of
  its own the folder's path), engine/data_check.py set apart, since it names every file it holds; and no module of the game but the
  startup check names a file of data/tools, which no build will ship once SHIPPING-10 stages the build (today's carries it, and the
  check's rules held to it run there). A stray file planted under data/rules that nothing names, one only data_check names, and a
  module planted naming lora.yaml are each caught;
- the startup check's rules held to data/tools (lora.yaml's task names, the cards and the measured profile's card) are skipped in a
  tree without data/tools, and raise nothing;
- the data words rule skips the folders NOT_GAME names (data/runtime among them now: no string there is shown to a player) and
  hygiene.yaml keeps no list of its own; no file of the game or the tools names the moved files at their old places.
What the fence does not read: whether a module that names a file reads it (a docstring counts); a file named by a name built at run
time; a module that reads the whole tree without naming a file (tools/sim/names_vocab_786_test.py's fence holds that: such a read
goes through game_data()); a key inside a game file that only
a tool reads (districts_by_scale was that case: STARTUP_DATA-3's key check, data_check.keys_problems with scan_code over the game's
code, will hold it); and the tools' side (a file of data/tools that no tool reads).
Run: python tools/sim/datahash_tools_785_test.py"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 785))
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


NOT_GAME = getattr(statehash, "NOT_GAME", None)
game_data = getattr(statehash, "game_data", None)
check("(f785) storage/statehash.py names once what under data/ is not the game (NOT_GAME, with why), and lists the game's data files "
      "(game_data)", isinstance(NOT_GAME, dict) and {"replay", "measured", "runtime", "tools"} <= set(NOT_GAME)
      and all(isinstance(v, str) and len(v.split()) >= 4 for v in NOT_GAME.values()) and callable(game_data), NOT_GAME)
NOT_GAME = NOT_GAME if isinstance(NOT_GAME, dict) else {"replay": "", "measured": "", "runtime": ""}

# ---- the hash, on a copy of data/ (the recordings left out: they are large, and outside the hash either way)
tmp = Path(tempfile.mkdtemp(prefix="datahash_785_"))
copy_data = getattr(statehash, "copy_data", None)
if callable(copy_data):
    copy_data(tmp, leave_out=("replay",))                               # the other folders kept: what changes in them must move nothing
else:
    shutil.copytree("data", tmp / "data", ignore=shutil.ignore_patterns("replay"))
base = statehash.data_hash(tmp)
check("the copy hashes as the checkout does", base == statehash.data_hash(), (base[:12], statehash.data_hash()[:12]))


def holding(text: str) -> Path | None:
    """The one data file of the copy that holds this text, wherever it lives."""
    found = [f for f in sorted((tmp / "data").rglob("*.yaml")) if text in f.read_text(encoding="utf-8")]
    return found[0] if len(found) == 1 else None


def moves(f: Path | None, old: str, new: str) -> bool | str:
    """Whether the data hash moves when old becomes new in f; the file put back after."""
    if f is None:
        return "no single file holds it"
    text = f.read_text(encoding="utf-8")
    if old not in text:
        return f"{old!r} is not in {f.name}"
    f.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    try:
        return statehash.data_hash(tmp) != base
    finally:
        f.write_text(text, encoding="utf-8", newline="\n")


lora = next(iter(sorted((tmp / "data").rglob("lora.yaml"))), None)
cards = next(iter(sorted((tmp / "data").rglob("cards.yaml"))), None)
draft = holding("districts_by_scale:")
check("(f785) a changed line in lora.yaml (a training run's) moves no data hash", moves(lora, "prose_tasks", "prose_tasks_785") is False,
      (lora, moves(lora, "prose_tasks", "prose_tasks_785")))
check("(f785) ...nor one in cards.yaml (the graphics cards a night is timed on)", moves(cards, "bandwidth_gbs:", "bandwidth_gbs: 1  # ") is False,
      (cards, moves(cards, "bandwidth_gbs:", "bandwidth_gbs: 1  # ")))
check("(f785) ...nor one in the town drafter's tables (districts_by_scale, anchors_by_scale)", moves(draft, "hamlet:  [0, 1]", "hamlet:  [0, 2]") is False
      and draft is not None and draft.name != "towns.yaml", (draft, moves(draft, "hamlet:  [0, 1]", "hamlet:  [0, 2]")))
check("...while a changed rule in a game file still moves it (towns.yaml's nearby_minutes)",
      moves(tmp / "data" / "rules" / "towns.yaml", "nearby_minutes: 60", "nearby_minutes: 61") is True)
(tmp / "data" / "rules" / "new_785.yaml").write_text("a: 1\n", encoding="utf-8")
check("...and so does a new file under data/rules", statehash.data_hash(tmp) != base)
(tmp / "data" / "rules" / "new_785.yaml").unlink()
for folder in NOT_GAME:
    (tmp / "data" / folder).mkdir(exist_ok=True)
    (tmp / "data" / folder / "new_785.yaml").write_text("a: 1\n", encoding="utf-8")
check("...but a file under a folder NOT_GAME names moves none", statehash.data_hash(tmp) == base, sorted(NOT_GAME))
if callable(game_data):
    deep = tmp / "data" / "world" / "tools" / "deep_785.yaml"         # a folder of that name below the top is the game's
    deep.parent.mkdir()
    deep.write_text("a: 1\n", encoding="utf-8")
    here = statehash.data_hash(tmp)
    listed = set(game_data(tmp))
    worded = {tmp / "data" / rel for rel in statehash.wording(tmp)}     # read as data: a blank line there is no change
    plain = [f for f in sorted(listed) if f not in worded]
    sample = plain[::max(1, len(plain) // 8)] + [deep]
    outside = [f for f in sorted((tmp / "data").rglob("*")) if f.is_file() and f not in listed]

    def nudged(f: Path) -> bool:
        """Whether a line added at a file's end moves the hash; the file put back after."""
        b = f.read_bytes()
        f.write_bytes(b + b"\n")
        try:
            return statehash.data_hash(tmp) != here
        finally:
            f.write_bytes(b)
    still = [f.relative_to(tmp / "data").as_posix() for f in sample if not nudged(f)]
    moved = [f.relative_to(tmp / "data").as_posix() for f in outside if nudged(f)]
    check("the hash reads exactly game_data(): a change to a file it lists moves the hash (one in a folder named tools below the top "
          "among them), a change to any other file under data/ moves none", deep in listed and len(sample) >= 8
          and {f.relative_to(tmp / "data").parts[0] for f in outside} >= set(NOT_GAME) and not still and not moved, (still, moved))
    deep.unlink()
    deep.parent.rmdir()
for folder in NOT_GAME:
    (tmp / "data" / folder / "new_785.yaml").unlink()

# ---- the fence: every file of the game's data is named by the game; no file of data/tools is
GAME_ROOTS = {"tools", "data", "docs", ".claude"}                       # as owned_state_633_test: the game is the rest
HARNESS = {"simlib", "simbot", "simreport", "smoke_test", "bestiary_check", "world_check"}
CHECK = "engine/data_check.py"                                          # names every file it holds: no reader by that
listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True, text=True,
                        encoding="utf-8", check=True).stdout.split()
texts = {p: Path(p).read_text(encoding="utf-8") for p in listed
         if p.split("/")[0] not in GAME_ROOTS and Path(p).stem not in HARNESS and Path(p).is_file()}


def unnamed(rels: list[str], sources: dict) -> list[str]:
    """The game's data files (paths under data/) that no module of the game names: by the file's name, or, for a file in a folder of
    its own below data/<folder>/, by that folder's path."""
    readers = [t for p, t in sources.items() if p != CHECK]
    out = []
    for rel in rels:
        parts = rel.split("/")
        folder = "/".join(parts[:-1]) + "/" if len(parts) >= 3 else None
        if not any(parts[-1] in t or (folder and folder in t) for t in readers):
            out.append(rel)
    return out


def tools_named(rels: list[str], sources: dict) -> list[str]:
    """The modules of the game, the startup check set apart, that name a file of data/tools."""
    return sorted({f"{p} ({rel})" for rel in rels for p, t in sources.items() if p != CHECK and rel.split("/")[-1] in t})


ROOT = Path(".").resolve()
game_rels = [f.relative_to(ROOT / "data").as_posix() for f in (game_data() if callable(game_data) else [])]
tools_rels = [f.relative_to(ROOT / "data").as_posix() for f in sorted((ROOT / "data" / "tools").rglob("*")) if f.is_file()] \
    if (ROOT / "data" / "tools").is_dir() else []
check("(f785) every file of the game's data is named by a module of the game (data_check set apart): a file only the tools read lives "
      "under data/tools", game_rels and not unnamed(game_rels, texts), unnamed(game_rels, texts))
check("(f785) ...and no module of the game but the startup check names a file of data/tools, which no build will ship once SHIPPING-10 "
      "stages the build (today's carries it, and the check's rules held to it run there)",
      tools_rels and not tools_named(tools_rels, texts), (tools_rels, tools_named(tools_rels, texts)))
check("...planted: a stray file under data/rules that nothing names is caught, and so is one only data_check names; one a module of "
      "the game names passes", unnamed(["rules/stray_785.yaml", "rules/checked_785.yaml", "rules/read_785.yaml", "world/rooms_785/inn.yaml"],
                                       {**texts, CHECK: texts.get(CHECK, "") + " checked_785.yaml",
                                        "engine/planted_785.py": "read_785.yaml data/world/rooms_785/"})
      == ["rules/stray_785.yaml", "rules/checked_785.yaml"])
check("...planted: a module of the game that names a file of data/tools is caught",
      tools_named(["tools/lora.yaml"], {"engine/planted_785.py": 'Path("data/tools/lora.yaml")'}) == ["engine/planted_785.py (tools/lora.yaml)"])

# ---- the startup check's rules held to data/tools are skipped where there is none
from engine import data_check
tools_of = getattr(data_check, "_tools", None)
check("(f785) engine/data_check.py reads data/tools through one door (_tools)", callable(tools_of))
if callable(tools_of):
    bare = Path(tempfile.mkdtemp(prefix="datahash_785_bare_"))
    statehash.copy_data(bare)                                          # the game's data alone: no data/tools
    real_root = data_check.ROOT
    data_check.ROOT = bare
    try:
        none_there = tools_of("lora.yaml") is None and tools_of("cards.yaml") is None
    finally:
        data_check.ROOT = real_root
    data_check._tools = lambda name: None                              # a tree without data/tools, for the rules that read through it
    try:
        got, why = data_check.budget_problems() + data_check.cards_problems() + data_check.check(), ""
    except Exception as e:
        got, why = [], f"{type(e).__name__}: {e}"
    finally:
        data_check._tools = tools_of
    check("(f785) ...which answers None in a tree without data/tools, and the rules held to it are skipped there, raising nothing",
          none_there and not why and not [p for p in got if "lora.yaml" in p or "cards.yaml" in p], (none_there, why, got[:4]))
    check("...while in this tree they are read and hold", tools_of("lora.yaml") and tools_of("cards.yaml")
          and not [p for p in data_check.check() if "lora.yaml" in p or "cards.yaml" in p])
    shutil.rmtree(bare, ignore_errors=True)

# ---- the data words rule skips by the same list, and nothing names the moved files at their old places
from engine import hygiene
words = Path(tempfile.mkdtemp(prefix="datahash_785_words_"))
for folder in ("world", *NOT_GAME):
    (words / folder).mkdir()
    (words / folder / "lines.yaml").write_text("said: It runs at dawn - and never after dark.\n", encoding="utf-8")
got = data_check.data_words_problems(root=words, table={"not_told": {}})
check("(f785) the data words rule skips the folders NOT_GAME names (data/runtime and data/tools among them) and reads the rest",
      [p.split()[0] for p in got] == ["data/world/lines.yaml"], got)
check("...and hygiene.yaml keeps no list of its own", "skip" not in (hygiene.H.get("data_words") or {}), list(hygiene.H.get("data_words") or {}))
shutil.rmtree(words, ignore_errors=True)
OLD = re.compile(r"rules\W{1,8}(lora|cards)\.yaml")
stale = [p for p in subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py", "*.md", "*.bat"],
                                   capture_output=True, text=True, encoding="utf-8", check=True).stdout.split()
         if not p.startswith(("docs/", "data/replay/", ".claude/")) and p != "tools/sim/datahash_tools_785_test.py" and Path(p).is_file()
         and OLD.search(Path(p).read_text(encoding="utf-8"))]
check("(f785) no file of the game or the tools names lora.yaml or cards.yaml at its old place under data/rules", not stale, stale)

shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
