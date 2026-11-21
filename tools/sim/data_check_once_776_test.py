"""(f776) The startup check parses each data file once, on the fast loader, and reads the source once a process (audit: speed-turn-1,
data-6, engine3-7, suite-speed-1).

The check took 9 to 12 s at every launch, after every edit of a data file and about 44 times a suite run: its strict loader was PyYAML's
pure-Python one while the game's own reads were already on libyaml's (f558), one check parsed 143 files 240 times, and the source scans
parsed the game's code again at every check. Now the strict loader is built on the loader core/yamlio.py picks; a check keeps what it
parsed (data files, source texts and syntax trees) for its own length and lets it go as it returns; and each scan of the code keeps its
answer for the process, by ROOT and the build fact. What is counted is data_check's own reads: a module the check calls reads its own
files, outside this. Held here:
- in one check data_check's own code reads each data file once and each source file at most once; in a second check it reads no source;
- the strict loader is on the fast loader, refuses a key given twice in a nested mapping with its line, and reads every data file to the
  same document as the pure-Python one; a file that fails to parse is told as the pure-Python loader told it (a tab, a bad indent);
- task_literals' filter on the text answers what a parse of every file answers, on this tree;
- no game module calls PyYAML's loaders but core/yamlio.py and the check's strict loaders (the fence is seen to catch each form, planted);
- no check changes a document it was handed; a replaced _load is honoured and leaves nothing behind; a planted broken reference is told
  as before;
- data edited inside one process is seen by the next check (a number, a trigger, and the world's biomes the triggers are held to);
- with ROOT at a copied tree the scans answer from that tree and not from the process's earlier answer, and back; an answer handed out is
  the asker's own;
- after a check, even one that raised, no syntax tree and no parsed file is held.
The seconds are measured outside the suite (timing noise here is about a quarter) and reported in the commit, not asserted.
Run: python tools/sim/data_check_once_776_test.py"""
import ast
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import simlib                                                         # (f741) a saves folder of the test's own
import yaml
from core import yamlio
from engine import data_check

bad: list[str] = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def attempt(fn):
    try:
        return fn()
    except Exception as e:
        return e


def shown(x):
    return repr(x) if isinstance(x, BaseException) else (x[:5] if isinstance(x, list) else x)


# ---- what data_check itself reads: an audit hook that counts each file opened by the check's own code (not a module it calls)
ROOT_S = os.path.normcase(str(ROOT))
DC_S = os.path.normcase(os.path.abspath(data_check.__file__))
COUNTING: list[Counter] = []


def _reads(event, args):
    if not COUNTING or event != "open":
        return                                                       # the event first: sys._getframe below is an event too
    target = args[0] if args else None
    if not isinstance(target, (str, bytes, os.PathLike)):
        return
    path = os.fsdecode(target)
    if not path.endswith((".yaml", ".yml", ".json", ".py")):
        return
    f = sys._getframe(1)
    while f is not None:                                             # the first frame of the project's own code is the reader
        name = f.f_code.co_filename
        if "importlib" in name:
            return                                                   # a module imported while the check runs, not a read of the check's
        if not name.startswith("<"):
            full = os.path.normcase(os.path.abspath(name))
            if full.startswith(ROOT_S) and "site-packages" not in full:
                break
        f = f.f_back
    if f is not None and os.path.normcase(os.path.abspath(f.f_code.co_filename)) == DC_S:
        COUNTING[-1][Path(path).resolve().as_posix()] += 1


sys.addaudithook(_reads)


def counted(fn):
    """What fn answers, and how often data_check's own code opened each file while it ran."""
    c = Counter()
    COUNTING.append(c)
    try:
        return attempt(fn), c
    finally:
        COUNTING.remove(c)


def under(c: Counter, folder: Path, suffix: str) -> Counter:
    base = folder.resolve().as_posix() + "/"
    return Counter({k: v for k, v in c.items() if k.startswith(base) and k.endswith(suffix)})


scratch = Path(tempfile.mkdtemp(prefix="once776_")).resolve()
try:
    # ---- one check reads each data file once and each source file at most once; a second check reads no source
    first, c1 = counted(data_check.check)
    second, c2 = counted(data_check.check)
    data_files = sorted(p.resolve().as_posix() for p in (ROOT / "data").rglob("*.yaml"))
    d1 = under(c1, ROOT / "data", ".yaml")
    check("the check passes on this tree, twice", first == [] and second == [], (shown(first), shown(second)))
    check("in one check data_check's own code opens each data file once, every one of them", sorted(d1) == data_files
          and max(d1.values(), default=0) == 1, (len(d1), len(data_files), sum(d1.values()), d1.most_common(4)))
    s1, s2 = under(c1, ROOT, ".py"), under(c2, ROOT, ".py")
    check("...and each source file at most once", s1 and max(s1.values()) == 1, s1.most_common(4))
    check("in a second check in the process it opens no source: each scan's answer is kept for the process",
          not s2 and max(under(c2, ROOT / "data", ".yaml").values(), default=0) == 1, (s2.most_common(4), len(s2)))
    check("...and parses the data again, once each (an edited file is read anew)", sorted(under(c2, ROOT / "data", ".yaml")) == data_files)

    # ---- the loader: fast, strict, and reading every file as before
    Fast = getattr(yaml, "CSafeLoader", None) or yaml.SafeLoader
    check("the strict loader is built on the loader core/yamlio.py picks (libyaml's when PyYAML has it)",
          issubclass(data_check._Strict, yamlio._Loader) and issubclass(data_check._Strict, Fast), data_check._Strict.__mro__[:3])
    nested = "top:\n  a: 1\n  b:\n    c: 2\n    c: 3\n"
    told = attempt(lambda: yaml.load(nested, Loader=data_check._Strict))
    check("a key given twice in a nested mapping is refused, with its line", isinstance(told, ValueError)
          and "the key 'c' is given twice (line 5)" in str(told), shown(told))

    class OldStrict(yaml.SafeLoader):
        pass
    OldStrict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data_check._no_dupes)
    differ = [p for p in (Path(f) for f in data_files)
              if yaml.load(p.read_text(encoding="utf-8"), Loader=OldStrict) != data_check._load(p.relative_to(ROOT.resolve()).as_posix())]
    check("every data file loads to the same document on the fast loader as on the pure-Python one", len(data_files) > 100 and not differ, differ[:5])

    # ---- a file that fails to parse is told as before: the pure-Python loader's words, with the line and its caret
    faulty = scratch / "faulty"
    shutil.copytree(ROOT / "data", faulty / "data", ignore=shutil.ignore_patterns("__pycache__"))
    budget_rel = "data/rules/budget.yaml"
    budget_text = (ROOT / budget_rel).read_text(encoding="utf-8")
    faults = {"a tab": budget_text.replace("\nlimit_seconds: 60", "\n\tlimit_seconds: 60", 1),
              "a bad indent": budget_text.replace("\n  deferred_turns: 3", "\n deferred_turns: 3", 1)}
    for what, text in faults.items():
        (faulty / budget_rel).write_text(text, encoding="utf-8")
        old = attempt(lambda: yaml.load(text, Loader=OldStrict))
        fast = attempt(lambda: yaml.load(text, Loader=data_check._Strict))
        data_check.ROOT = faulty
        try:
            told_now = attempt(data_check.check)
        finally:
            data_check.ROOT = ROOT
        check(f"a file with {what} is told word for word as the pure-Python loader told it, its line and caret with it",
              text != budget_text and isinstance(old, yaml.MarkedYAMLError) and told_now == [f"{budget_rel}: {old}"] and "^" in str(old),
              (shown(told_now), str(old)[:300], str(fast)[:300]))
    check("...where the fast loader's own words name no tab (the case is real)", "'\\t'" in str(attempt(lambda: yaml.load(faults["a tab"], Loader=OldStrict)))
          and (Fast is yaml.SafeLoader or "'\\t'" not in str(attempt(lambda: yaml.load(faults["a tab"], Loader=data_check._Strict)))))

    # ---- task_literals' filter on the text answers what a parse of every file answers
    full: dict[str, list[str]] = {}
    for p in [p for d in data_check.GAME_DIRS for p in sorted((ROOT / d).rglob("*.py"))] + sorted((ROOT / "tools").glob("*.py")):
        try:
            parsed = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(parsed):
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                fn = node.func
                if (fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")) in ("generate", "fresh"):
                    full.setdefault(node.args[0].value, []).append(f"{p.relative_to(ROOT).as_posix()}:{node.lineno}")
    filtered = data_check.task_literals()
    check("task_literals, parsing only the files whose text calls generate or fresh, answers what a parse of every file answers",
          filtered == full and len(full) > 40, (sorted(set(full) ^ set(filtered or {}))[:5], len(full)))

    # ---- the fence: no game module calls PyYAML's loaders but core/yamlio.py and the check's strict loader
    LOADERS = {"load", "safe_load", "full_load", "unsafe_load", "load_all", "safe_load_all", "full_load_all", "unsafe_load_all"}
    from game_files import game_files                                # (f788) the game's own code, one definition for every fence

    def yaml_loads(text: str) -> list[tuple[int, str]]:
        """(line, the top-level name it stands in) for each call of one of PyYAML's loaders, by name, through an alias or __import__."""
        t = ast.parse(text)
        names = {"yaml"} | {a.asname or a.name for n in ast.walk(t) if isinstance(n, ast.Import) for a in n.names if a.name == "yaml"}
        bare = {a.asname or a.name for n in ast.walk(t) if isinstance(n, ast.ImportFrom) and n.module == "yaml" for a in n.names if a.name in LOADERS}

        def is_yaml(v):
            return (isinstance(v, ast.Name) and v.id in names) or (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "__import__"
                                                                     and v.args and isinstance(v.args[0], ast.Constant) and v.args[0].value == "yaml")
        out = []
        for top in t.body:
            for n in ast.walk(top):
                if isinstance(n, ast.Call) and ((isinstance(n.func, ast.Attribute) and n.func.attr in LOADERS and is_yaml(n.func.value))
                                                or (isinstance(n.func, ast.Name) and n.func.id in bare)):
                    out.append((n.lineno, getattr(top, "name", "")))
        return out
    planted = ["import yaml\nX = yaml.load(open('a').read(), Loader=yaml.SafeLoader)\n", "X = __import__('yaml').safe_load('a: 1')\n",
               "def f():\n    import yaml as _y\n    return _y.safe_load('a: 1')\n", "from yaml import full_load\nX = full_load('a: 1')\n",
               "import yaml as Y\nX = list(Y.safe_load_all('a: 1'))\n"]
    check("the fence catches each way of calling PyYAML's loader, planted", all(yaml_loads(src) for src in planted),
          [src for src in planted if not yaml_loads(src)])
    files = [ROOT / p for p in game_files()]
    loose = []
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        for line, where in yaml_loads(p.read_text(encoding="utf-8")):
            if rel == "core/yamlio.py" or (rel == "engine/data_check.py" and where in ("_load", "_why")):
                continue
            loose.append(f"{rel}:{line} ({where or 'module'})")
    check("no game module calls PyYAML's loaders but core/yamlio.py and the check's strict loaders (data_check._load, and _why for a file"
          " that failed)", not loose and len(files) > 100, loose)

    # ---- no check changes a document; a replaced _load is honoured and leaves nothing behind; a broken reference told as before
    handed: list[tuple[str, object]] = []
    real_load = data_check._load

    def keeping(rel):
        doc = real_load(rel)
        handed.append((Path(rel).as_posix(), doc))
        return doc
    data_check._load = keeping
    try:
        kept_answer = data_check.check()
    finally:
        data_check._load = real_load
    changed = sorted({rel for rel, doc in handed if doc != yaml.load((ROOT / rel).read_text(encoding="utf-8"), Loader=OldStrict)})
    check("no check changes a document it was handed (each is the same as the file, after the check)", kept_answer == [] and len(handed) > 200
          and not changed, (shown(kept_answer), len(handed), changed[:5]))

    def planting(rel):
        doc = real_load(rel)
        if Path(rel).as_posix() == "data/rules/speech.yaml":
            return {**doc, "peoples": {**doc["peoples"], "moon_folk": {"moon_culture": 1}}}
        return doc
    data_check._load = planting
    try:
        planted_answer = data_check.check()
    finally:
        data_check._load = real_load
    check("a replaced _load is honoured, and a planted broken reference is told as before",
          "speech.yaml peoples: 'moon_folk' is not a people in peoples.yaml" in planted_answer
          and "speech.yaml peoples.moon_folk: culture 'moon_culture' does not exist" in planted_answer, shown(planted_answer))
    after = data_check.check()
    check("...and nothing of it stays for the next check", after == [], shown(after))

    # ---- a copied source tree: the scans answer from it; data edited inside the process is seen
    src = scratch / "src"
    for d in sorted(set(data_check.GAME_DIRS) | set(data_check.GAME_CODE)):
        shutil.copytree(ROOT / d, src / d, ignore=shutil.ignore_patterns("__pycache__"))
    (src / "tools").mkdir()
    for p in (ROOT / "tools").glob("*.py"):
        shutil.copy(p, src / "tools" / p.name)
    shutil.copytree(ROOT / "data", src / "data", ignore=shutil.ignore_patterns("__pycache__"))
    (src / "engine" / "moon_776.py").write_text('def moon(row, gateway):\n    gateway.generate("narrate", row)\n'
                                                '    return row["moon_key_planted"], row.get("moon_get_planted"), "moon_literal_planted"\n', encoding="utf-8")
    real_lits, real_keys = data_check.scan_code()
    real_narrate = data_check.task_literals()["narrate"]
    data_check.ROOT = src
    try:
        lits, keys = data_check.scan_code()
        lits_p, keys_p = data_check.scan_code(precise=True)
        narrate = data_check.task_literals()["narrate"]
    finally:
        data_check.ROOT = ROOT
    back_lits, back_keys = data_check.scan_code()
    check("with ROOT at a copied tree the scans answer from that tree, not from the process's earlier answer",
          "moon_literal_planted" in lits and {"moon_key_planted", "moon_get_planted"} <= keys and {"moon_key_planted", "moon_get_planted"} <= keys_p
          and any(w.startswith("engine/moon_776.py:") for w in narrate), (sorted(keys - real_keys)[:5], narrate[-2:]))
    check("...and back at the real tree from the real tree's", "moon_literal_planted" not in back_lits and "moon_key_planted" not in back_keys
          and "moon_literal_planted" not in real_lits and not any(w.startswith("engine/moon_776.py") for w in real_narrate))
    mine = data_check.task_literals()
    mine["narrate"].append("nowhere.py:1")
    check("an answer handed out is the asker's own: changing it changes no later answer",
          "nowhere.py:1" not in data_check.task_literals()["narrate"])

    def on_copy():
        data_check.ROOT = src
        try:
            return attempt(data_check.check)
        finally:
            data_check.ROOT = ROOT
    base = on_copy()
    check("the copied tree passes the check", base == [], shown(base))
    budget = src / "data" / "rules" / "budget.yaml"
    kept = budget.read_text(encoding="utf-8")
    budget.write_text(kept.replace("\nlimit_seconds: 60", "\nlimit_seconds: soon", 1), encoding="utf-8")
    edited = on_copy()
    budget.write_text(kept, encoding="utf-8")
    mended = on_copy()
    check("a data file edited inside the process is seen by the next check, and its mending by the one after",
          isinstance(edited, list) and "budget.yaml limit_seconds: needs a number above 0" in edited and mended == [], (shown(edited), shown(mended)))
    with open(src / "data" / "rules" / "triggers.yaml", "a", encoding="utf-8") as fh:
        fh.write("\n- id: in_moonmarsh\n  condition: In the moon marsh.\n  checks: none\n  context: anywhere\n"
                 "  suits: {archetypes: [], themes: []}\n")
    unheld = on_copy()
    (src / "data" / "world" / "moon_776.yaml").write_text("biome: moonmarsh\n", encoding="utf-8")
    held = on_copy()
    check("a trigger added to the data is held to the code at the next check",
          isinstance(unheld, list) and any("in_moonmarsh: no code evaluates it" in p for p in unheld), shown(unheld))
    check("...and a biome added to the world makes it one the code evaluates: the scan keeps the code's half, never the data's",
          held == [], shown(held))

    # ---- after a check, even one that raised, nothing parsed is held
    data_only = scratch / "data_only"
    shutil.copytree(ROOT / "data", data_only / "data", ignore=shutil.ignore_patterns("__pycache__"))
    data_check.ROOT = data_only
    try:
        raised = attempt(data_check.check)
    finally:
        data_check.ROOT = ROOT
    check("a check from source on a tree without its code still raises", isinstance(raised, FileNotFoundError), shown(raised))

    def held_trees(x, depth=0) -> int:
        if isinstance(x, ast.AST):
            return 1
        if depth > 4:
            return 0
        if isinstance(x, dict):
            return sum(held_trees(k, depth + 1) + held_trees(v, depth + 1) for k, v in x.items())
        if isinstance(x, (list, tuple, set, frozenset)):
            return sum(held_trees(v, depth + 1) for v in x)
        return 0
    trees_held = sum(held_trees(v) for k, v in vars(data_check).items() if not k.startswith("__"))
    check("...and after it no syntax tree is held by data_check, and no check's store of parsed files is left open",
          trees_held == 0 and getattr(data_check, "_ONCE", None) is None, (trees_held, type(getattr(data_check, "_ONCE", None))))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
