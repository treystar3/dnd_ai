"""(f786) Name mending reads its ordinary words from the game's own files only (GATE-20, docs/design/33_audit_fix_plan/gate.md;
engine5-11).

engine/names.py near_miss leaves a capitalised word alone when it is an ordinary word, one the game's data writes in lower case
(vocab()), so "Wind" at the head of a sentence is never taken for the river Wend. vocab() read every YAML under data/: the recordings
and test cases (data/replay), what tools measured (data/measured), the machine's settings (data/runtime) and since f785 the tools'
own files (data/tools), untracked tool output among them. So a test case decided a mend: `bale`, a word of
data/replay/ruling_cases_act.yaml, stopped a model's "Bale" being mended to Bael, and a file a tool wrote changed mending while the
data hash said the game was the same. vocab() now reads every file of storage/statehash.py game_data(), the files the data hash reads
(their YAML and their JSON), so the two cannot part. Held here:
- vocab() is exactly the lower-case words of the game's data files: none that stands only in a folder NOT_GAME names, and every one
  of a game file, the JSON's among them ("mortal", which the goddess's own text uses);
- the finder's case: near_miss("Bale", {"Bael"}) is Bael, and the line is mended;
- in a copy of the game's data: a YAML added under data/replay, data/measured, data/runtime or data/tools changes neither the
  vocabulary nor the data hash, while a lower-case word added to data/world still blocks the mend, as it should;
- the fence: no module of the game reads the whole of data/ itself except storage/statehash.py game_data(), the one door, or a
  reader listed here with why. A whole read is an rglob, a glob, an iterdir, an os.walk, a scandir or a listdir of the data folder,
  or a glob module's glob or iglob of a "data/" pattern with a wildcard at its second part. The data folder is `x / "data"`,
  `x.joinpath("data")`, `Path(x, "data")`, `os.path.join(x, "data")` or the string "data", or a name set to one of those in the
  function, a function around it or the module. Planted and caught: an rglob of ROOT / 'data', an os.walk of 'data', an iterdir of
  a name set to BUNDLE / 'data' in a method, an rglob of a module constant inside a function, a joinpath, a Path(x, 'data') and a
  glob.glob of 'data/**'. A read through game_data() and one of data/world pass.
What the fence does not read: a data root that comes in as a parameter or an attribute, a path built from strings at run time
(an f-string, a concatenation), and a read of a game folder (data/world) that should have been narrower.
Run: python tools/sim/names_vocab_786_test.py"""
import ast
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 786))
from engine import names
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def words_of(files) -> set[str]:
    out: set[str] = set()
    for f in files:
        out |= set(names.WORD.findall(f.read_text(encoding="utf-8")))
    return out


ROOT = Path(".").resolve()
game = words_of(statehash.game_data())
outside = words_of(f for f in sorted((ROOT / "data").rglob("*")) if f.is_file() and f.suffix in (".yaml", ".yml", ".json")
                   and f.relative_to(ROOT / "data").parts[0] in statehash.NOT_GAME)
only_outside = outside - game
names._VOCAB.clear()
got = names.vocab()
check("(f786) vocab() holds no word that stands only in a folder NOT_GAME names (the recordings, what a tool measured, the machine's "
      "settings, the tools' own)", only_outside and not (got & only_outside), (len(only_outside), sorted(got & only_outside)[:12]))
check("...and every lower-case word of the game's own data files, their JSON's among them: it is exactly theirs",
      got == game and "mortal" in got, (len(got), len(game), sorted(game - got)[:8]))
check("(f786) the finder's case: a model's 'Bale' for Bael is mended, though 'bale' stands in a test case of data/replay",
      "bale" in only_outside and names.near_miss("Bale", {"Bael"}, set()) == "Bael"
      and names.mend_text("They say Bale is two days off.", {"Bael"}, set()) == "They say Bael is two days off.",
      ("bale" in only_outside, names.near_miss("Bale", {"Bael"}, set())))

# ---- a copy of the game's data, read by vocab() through game_data() pointed at it
tmp = Path(tempfile.mkdtemp(prefix="names_786_"))
statehash.copy_data(tmp)
real_game_data = statehash.game_data
statehash.game_data = lambda root=tmp: real_game_data(root)
try:
    names._VOCAB.clear()
    before, hashed = set(names.vocab()), statehash.data_hash(tmp)
    for folder in statehash.NOT_GAME:
        (tmp / "data" / folder).mkdir(exist_ok=True)
        (tmp / "data" / folder / "planted_786.yaml").write_text("note: the zorblex of the vale\n", encoding="utf-8")
    names._VOCAB.clear()
    after = set(names.vocab())
    check("(f786) a YAML added under each folder NOT_GAME names changes neither the vocabulary nor the data hash",
          "zorblex" not in after and after == before and statehash.data_hash(tmp) == hashed, ("zorblex" in after, len(after - before)))
    mended = names.near_miss("Bale", {"Bael"}, set())
    (tmp / "data" / "world" / "planted_786.yaml").write_text("note: a bale of hay and a zorblex\n", encoding="utf-8")
    names._VOCAB.clear()
    check("...while a lower-case word added to data/world is ordinary at once, and still blocks the mend, as it should",
          mended == "Bael" and {"bale", "zorblex"} <= names.vocab() and names.near_miss("Bale", {"Bael"}, set()) == "",
          (mended, names.near_miss("Bale", {"Bael"}, set())))
finally:
    statehash.game_data = real_game_data
    names._VOCAB.clear()
    shutil.rmtree(tmp, ignore_errors=True)

# ---- the fence: a whole read of data/ goes through game_data()
NOT_GAME_ROOTS = {"tools", "data", "docs", ".claude"}                   # as owned_state_633_test: the game is the rest
HARNESS = {"simlib", "simbot", "simreport", "smoke_test", "bestiary_check", "world_check"}
READS = {"rglob", "glob", "iterdir", "walk", "scandir", "listdir"}
LISTED = {                                                              # (file, function): why it reads the whole of data/ itself
    ("storage/statehash.py", "game_data"): "the door: the game's data files, every file under data/ but NOT_GAME's folders",
    ("engine/data_check.py", "check"): "the startup check parses every YAML file under data/, in two halves: data/runtime and "
                                       "data/measured are read in play, so one that does not parse is a fault of the game's; data/replay "
                                       "and data/tools are parsed only because today's build ships them, to be narrowed when SHIPPING-10 "
                                       "stages the build without them",
}


def is_root(node, roots: set) -> bool:
    """The data folder itself: `x / "data"`, `x.joinpath("data")`, `Path(x, "data")`, `os.path.join(x, "data")`, the string
    "data", or a name in roots (set to one of those in this function, one around it or the module)."""
    if isinstance(node, ast.Constant):
        return node.value in ("data", "data/")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return isinstance(node.right, ast.Constant) and node.right.value == "data"
    if isinstance(node, ast.Call) and node.args and getattr(node.func, "id", getattr(node.func, "attr", "")) in ("Path", "PurePath",
                                                                                                             "joinpath", "join"):
        return is_root(node.args[-1], roots)                             # the last part named decides: Path(x, "data", "world") is no root
    return isinstance(node, ast.Name) and node.id in roots


def whole_glob(call) -> bool:
    """The glob module's glob or iglob of a "data/" pattern with a wildcard at its second part (data/**, data/*.yaml)."""
    f = call.func
    named = (isinstance(f, ast.Name) and f.id in ("glob", "iglob")) or (isinstance(f, ast.Attribute) and f.attr in ("glob", "iglob")
                                                                      and isinstance(f.value, ast.Name) and f.value.id == "glob")
    if not named or not call.args or not isinstance(call.args[0], ast.Constant) or not isinstance(call.args[0].value, str):
        return False
    parts = call.args[0].value.replace("\\", "/").split("/")
    return parts[0] == "data" and len(parts) > 1 and any(c in parts[1] for c in "*?[")


SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def own(scope):
    """The nodes of one scope, not those of the functions and classes defined inside it (those are yielded, not entered)."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        n = stack.pop()
        yield n
        if not isinstance(n, SCOPES):
            stack.extend(ast.iter_child_nodes(n))


def whole_reads(src: str) -> list[str]:
    """The functions of a module (dotted, "<module>" at the top) that read the whole of data/ themselves."""
    out: set[str] = set()

    def visit(scope, where, outer: set):
        nodes = list(own(scope))
        roots = set(outer) | {t.id for n in nodes if isinstance(n, ast.Assign) and is_root(n.value, set(outer))
                              for t in n.targets if isinstance(t, ast.Name)}
        for n in nodes:
            if isinstance(n, ast.Call) and (whole_glob(n) or (isinstance(n.func, ast.Attribute) and n.func.attr in READS and is_root(
                    n.args[0] if n.func.attr in ("walk", "scandir", "listdir") and n.args else n.func.value, roots))):
                out.add(where)
            elif isinstance(n, SCOPES):
                visit(n, n.name if where == "<module>" else f"{where}.{n.name}", roots)
    visit(ast.parse(src), "<module>", set())
    return sorted(out)


listed_py = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True, text=True,
                           encoding="utf-8", check=True).stdout.split()
found = [(p, fn) for p in listed_py if p.split("/")[0] not in NOT_GAME_ROOTS and Path(p).stem not in HARNESS and Path(p).is_file()
         for fn in whole_reads(Path(p).read_text(encoding="utf-8"))]
check("(f786) no module of the game reads the whole of data/ but through statehash.game_data(), or with its reason listed here",
      not [f for f in found if f not in LISTED], [f for f in found if f not in LISTED])
check("...and every reader listed is still there", not [k for k in LISTED if k not in found], [k for k in LISTED if k not in found])
PLANTED = {
    "from pathlib import Path\nROOT = Path(__file__).parent\ndef words():\n    return [p for p in (ROOT / 'data').rglob('*.yaml')]\n": ["words"],
    "import os\ndef walk_it():\n    for d, _, fs in os.walk('data'):\n        pass\n": ["walk_it"],
    "from core.paths import BUNDLE\nclass Book:\n    def pages(self):\n        d = BUNDLE / 'data'\n        return list(d.iterdir())\n": ["Book.pages"],
    "from pathlib import Path\nROOT = Path(__file__).resolve().parent.parent / 'data'\ndef rules():\n    return list(ROOT.rglob('*.yaml'))\n": ["rules"],
    "def load(base):\n    return list(base.joinpath('data').rglob('*'))\n": ["load"],
    "from pathlib import Path\nfrom core.paths import BUNDLE\ndef load():\n    return sorted(Path(BUNDLE, 'data').glob('**/*.yaml'))\n": ["load"],
    "import glob\ndef load():\n    return glob.glob('data/**/*.yaml', recursive=True)\n": ["load"],
    "from storage import statehash\ndef words():\n    return [p for p in statehash.game_data() if p.suffix == '.yaml']\n": [],
    "from pathlib import Path\nROOT = Path('.')\ndef places():\n    return sorted((ROOT / 'data' / 'world').rglob('*.yaml'))\n": [],
    "import glob\ndef load():\n    return glob.glob('data/world/*.yaml')\n": [],
    "from pathlib import Path\nROOT = Path('.') / 'data'\ndef arcs():\n    return (ROOT / 'rules' / 'arcs.yaml').read_text()\n": [],
}
wrong = {i: (whole_reads(src), want) for i, (src, want) in enumerate(PLANTED.items()) if whole_reads(src) != want}
check("...planted: an rglob of ROOT / 'data', an os.walk of 'data', an iterdir of a name set to BUNDLE / 'data' in a method, an rglob "
      "of a module constant inside a function, a joinpath, a Path(x, 'data') and a glob.glob of 'data/**' are caught; a read through "
      "game_data(), one of data/world (an rglob, a glob) and a module constant read file by file pass", not wrong, wrong)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
