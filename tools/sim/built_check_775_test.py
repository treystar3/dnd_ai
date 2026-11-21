"""(f775) A built game passes its own startup check, and a build that cannot is never handed over (audit: frontend-shipping-1,
speed-turn-2).

A built game carries data/ and no source: PyInstaller keeps the modules in its archive. Six readers of the startup check read the code's
.py files, so every start of a built game raised (FileNotFoundError for engine/combat_improv.py) and, with that one mended, refused itself
on 190 false problems (31 of them budget_problems' alone: a wrong answer, not a raise). The suite never saw it: it holds the check only
on the source tree. The check now reads source through one reader in engine/data_check.py (source, tree, modules) beside one fact,
built() (core.paths.FROZEN, asked at the call): in a build the reader answers None, so does every scan that reads through it, and the
rules that hold data to code skip their code rows while every data-only rule still runs. Held here:
- with the build fact set and the check's root a copied tree that holds data/ and no source, the whole check answers []; budget_problems
  alone on that tree does too;
- every scan answers None in a build and what the code holds from source; the scans are exactly the functions that call the reader;
- in a build each rule held to code still tells a planted data problem and skips its code rows; from source it tells both (the tasks
  asked outside are held to budget.yaml's own table in a build, to the code from source);
- from source a tree without its modules still fails loudly (a file read by name, a folder listed, a scan already cached);
- a syntactic guard over every game module: none but the reader calls ast.parse or inspect.getsource*, globs *.py, or reads or opens a
  .py whose name stands in its text; seen to catch each form, planted;
- a behavioural fence (an audit hook) under the whole check and the self-check run as a build: no .py is opened and no folder of the
  code is listed outside the import system, in whatever module the check calls; seen to catch, planted, what the guard's forms miss: a
  module's __file__ read or opened, a path held in a name, tokenize, linecache, a listing filtered by suffix or ending, a glob;
- the self-check (python main.py --check, Meravia.exe --check: core/selfcheck.py) answers 0 from source and in a built layout, 1 for a
  planted data problem, a page file missing, a build without its window library and a part that raises; it writes its log anew each
  run, takes no lock and starts nothing; main.py --check runs it alone;
- build_exe.bat runs the check from source before PyInstaller and the built game's on the folder as handed over, failing the build on
  either, and ships no log of its own check.
What the stub cannot see: a read of source on a path the check does not take on this data, or outside the check and the self-check;
the built game's own --check at the end of the build is the last net (a real build, on the owner's machine).
Run: python tools/sim/built_check_775_test.py"""
import ast
import contextlib
import copy
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import simlib                                                         # (f741) a saves folder of the test's own
from core import paths
from engine import data_check, items

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
    return repr(x) if isinstance(x, BaseException) else (x[:5] if isinstance(x, list) else x)


scratch = Path(tempfile.mkdtemp(prefix="built775_")).resolve()
built_tree = scratch / "built"                                        # what a build carries as files: data/, and no module of the game
shutil.copytree(ROOT / "data", built_tree / "data", ignore=shutil.ignore_patterns("__pycache__"))


@contextlib.contextmanager
def as_built(root: Path = built_tree):
    """The build fact set for the call and the check's root at a tree, both put back. core.paths is not reloaded as a build: llm/launch.py
    and llm/runtime.py fix their data paths when first imported and check() calls both, so a reload would hang on the order of imports."""
    was = paths.FROZEN, data_check.ROOT
    paths.FROZEN, data_check.ROOT = True, root
    try:
        yield
    finally:
        paths.FROZEN, data_check.ROOT = was


@contextlib.contextmanager
def from_source(root: Path):
    was = paths.FROZEN, data_check.ROOT
    paths.FROZEN, data_check.ROOT = False, root
    try:
        yield
    finally:
        paths.FROZEN, data_check.ROOT = was


@contextlib.contextmanager
def replaced(obj, name, value):
    was = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, was)


# ---- the behavioural fence: what the process itself does while the check runs as a build, whichever module does it
from game_files import game_files                                    # (f788) the game's own code, one definition for every fence
CODE_FOLDERS = tuple(sorted({p.parts[0] for p in game_files(with_tools=True) if len(p.parts) > 1}))   # the game's folders and tools/
WATCHING: list[list[str]] = []                                       # the list the fence notes into while it watches


def _fence(event, args):
    """An audit hook: while watched, every .py opened and every folder of the code listed or globbed for .py, outside the import system
    (which opens and lists the source of a module being imported, as a build's archive does without a file)."""
    if not WATCHING or not (event in ("open", "os.listdir", "os.scandir") or event.startswith("glob.glob")):
        return                                                       # the event first: sys._getframe below is an event too
    target = args[0] if args else None
    if not isinstance(target, (str, bytes, os.PathLike)):
        return                                                       # a file descriptor, or the working folder
    target = os.fsdecode(target)
    if event == "open":
        if not target.endswith(".py"):
            return
    elif event in ("os.listdir", "os.scandir"):
        p = Path(target)
        if p.name not in CODE_FOLDERS or "data" in p.parts:
            return
    elif event.startswith("glob.glob"):
        if ".py" not in target:
            return
    else:
        return
    f = sys._getframe(1)
    while f is not None:
        if "importlib" in f.f_code.co_filename:
            return
        f = f.f_back
    WATCHING[-1].append(f"{event} {target}")


sys.addaudithook(_fence)


@contextlib.contextmanager
def fenced():
    """What the fence notes while the block runs."""
    seen: list[str] = []
    WATCHING.append(seen)
    try:
        yield seen
    finally:
        WATCHING.remove(seen)


try:
    # ---- the finder's case: the whole check on a built tree, and the second case of the kind, a wrong answer and not a raise
    with as_built(), fenced() as opened:
        whole = attempt(data_check.check)
        budget = attempt(data_check.budget_problems)
    check("a built game passes its whole startup check: a tree with data/ and no source answers []", whole == [], shown(whole))
    check("...and budget_problems alone on that tree answers [] (no task 'nothing calls', none 'the code calls')", budget == [], shown(budget))
    check("...and in a build the whole check opens no .py and lists no folder of the code, in any module it calls", not opened, opened[:5])
    check("the build fact is asked when the check runs (core.paths.FROZEN now), not a file being absent",
          attempt(lambda: data_check.built()) is False and paths.FROZEN is False, shown(attempt(lambda: data_check.built())))

    # ---- every scan of the code: None in a build, what the code holds from source; the scans are the functions that call the reader
    SCANS = {
        "task_literals": lambda: data_check.task_literals(),
        "improv_handled": lambda: data_check.improv_handled(),
        "evaluated_triggers": lambda: data_check.evaluated_triggers(),
        "_literals": lambda: data_check._literals(["engine/spellcraft.py", "engine/combat.py"]),
        "_compared": lambda: data_check._compared("engine/relics.py", ("kind",)),
        "scan_code": lambda: data_check.scan_code(),
        "scan_code precise": lambda: data_check.scan_code(precise=True),
        "code_named": lambda: data_check.code_named(),
        "_read_keys": lambda: data_check._read_keys(),
    }
    with as_built():
        in_build = {k: attempt(f) for k, f in SCANS.items()}
    check("in a build every scan of the code answers None", all(v is None for v in in_build.values()),
          {k: shown(v) for k, v in in_build.items() if v is not None})
    here = {k: attempt(f) for k, f in SCANS.items()}
    check("...and from source each answers what the code holds, none empty",
          all(not isinstance(v, BaseException) and v for v in here.values()) and all(x for x in here["scan_code"]),
          {k: shown(v) for k, v in here.items() if isinstance(v, BaseException) or not v})
    READER = ("source", "tree", "modules")
    dc_tree = ast.parse(Path(data_check.__file__).read_text(encoding="utf-8"))
    calling = {f.name for f in dc_tree.body if isinstance(f, ast.FunctionDef) and f.name not in READER
               and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in READER for n in ast.walk(f))}
    check("the scans are exactly the functions that call the reader: a new one is listed here, or this fails",
          calling == {"task_literals", "improv_handled", "evaluated_triggers", "_literals", "_compared", "scan_code"}, sorted(calling))

    # ---- each rule held to code: in a build its data-only rows still tell, its code rows are skipped; from source both tell
    B = data_check._load("data/rules/budget.yaml")
    planted_b = {**B, "limit_seconds": "soon", "tasks": {**B["tasks"], "nobody_asks_this": {"need": "required", "answer_tokens": 10}}}
    with as_built():
        b_built = attempt(lambda: data_check.budget_problems(planted_b))
    b_src = attempt(lambda: data_check.budget_problems(planted_b))
    told = "budget.yaml limit_seconds: needs a number above 0"
    code_said = ("nothing in the code calls", "the code calls tasks", "is no task the code asks for")
    check("budget: in a build the rules of the data still tell (a number, a task the audit log gives no reason for), the code's rows are skipped",
          isinstance(b_built, list) and told in b_built and any("no reason is given for nobody_asks_this" in p for p in b_built)
          and not any(c in p for p in b_built for c in code_said), shown(b_built))
    check("...and from source both tell", isinstance(b_src, list) and told in b_src
          and any("nothing in the code calls" in p and "nobody_asks_this" in p for p in b_src), shown(b_src))
    planted_o = {**B, "asked_outside": list(B.get("asked_outside") or []) + ["moon_errand"]}
    with as_built():
        o_built = attempt(lambda: data_check.budget_problems(planted_o))
    o_src = attempt(lambda: data_check.budget_problems(planted_o))
    check("the tasks asked outside: in a build a name budget.yaml does not know is still told, held to the table",
          o_built == ["budget.yaml asked_outside: 'moon_errand' is no task budget.yaml knows"], shown(o_built))
    check("...and from source it is held to the code", o_src == ["budget.yaml asked_outside: 'moon_errand' is no task the code asks for"], shown(o_src))
    I = copy.deepcopy(data_check._load("data/rules/combat.yaml")["improv"])
    I["effects"]["moon_dance"] = {"odds": 1, "words": ["moon"]}       # no about, and no branch of the resolver
    with as_built():
        i_built = attempt(lambda: data_check.improv_problems(I))
    i_src = attempt(lambda: data_check.improv_problems(I))
    check("improvisations: in a build a row's own shape still tells, the resolver's rows are skipped",
          isinstance(i_built, list) and any("moon_dance: needs about" in p for p in i_built) and not any("resolver" in p for p in i_built), shown(i_built))
    check("...and from source both tell", isinstance(i_src, list) and any("moon_dance: needs about" in p for p in i_src)
          and any("moon_dance: the resolver" in p for p in i_src), shown(i_src))
    with as_built():
        t_built = attempt(lambda: data_check.trigger_problems([{"id": "when_the_moon_sings"}]))
    t_src = attempt(lambda: data_check.trigger_problems([{"id": "when_the_moon_sings"}]))
    check("triggers: the rule is all held to the code, skipped in a build and told from source",
          t_built == [] and isinstance(t_src, list) and any("when_the_moon_sings: no code evaluates it" in p for p in t_src), (shown(t_built), shown(t_src)))
    E = items.LegendaryEffect
    tables = {"legendary": {**items.LEGENDARY, "moonblade": E(id="moonblade", name="Moonblade", applies="weapon", description="x"),
                            "moonbane": E(id="moonbane", name="Moonbane", applies="weapon", category="moon folk", description="x")},
              "expressions": {"moonfire": {"element": "fire", "kind": "damage", "text": "{moonlight} burns"}},
              "martial": {"moon_step": {"status": "moonstruck", "moon_key": 1}}}
    with as_built():
        a_built = attempt(lambda: data_check.allowlist_problems(tables=tables))
    a_src = attempt(lambda: data_check.allowlist_problems(tables=tables))
    data_rows = ("moonbane: category 'moon folk'", "expressions.moonfire.text: unknown placeholder", "moon_step: status 'moonstruck'")
    code_rows = ("moonblade: nothing runs it", "spellcraft.yaml expressions.moonfire: nothing in engine/spellcraft.py",
                 "moon_step: the key 'moon_key' is one no game code reads")
    check("the allow-lists: in a build a category, a placeholder and a status are still held, the code's names skipped",
          isinstance(a_built, list) and all(any(r in p for p in a_built) for r in data_rows) and not any(any(r in p for p in a_built) for r in code_rows),
          shown(a_built))
    check("...and from source all six tell", isinstance(a_src, list) and all(any(r in p for p in a_src) for r in data_rows + code_rows), shown(a_src))
    with as_built():
        a_real = attempt(data_check.allowlist_problems)
    check("...and the real tables pass in a build (nothing read by name stands in for the code)", a_real == [], shown(a_real))

    # ---- a guard that holds today and must keep holding: from source a tree without its code fails loudly
    with from_source(built_tree):
        no_code = attempt(data_check.check)
        one_file = attempt(data_check.improv_handled)
        listed = attempt(data_check.task_literals)
        cached = attempt(data_check.scan_code)                       # answered for the real tree above, and kept for the process
    check("from source a tree without its modules still fails loudly: the whole check raises", isinstance(no_code, FileNotFoundError), shown(no_code))
    check("...a file read by name raises, naming it", isinstance(one_file, FileNotFoundError) and "combat_improv.py" in str(one_file), shown(one_file))
    check("...a folder of modules listed raises, not an empty answer", isinstance(listed, FileNotFoundError), shown(listed))
    check("...and a scan already kept for the process raises too", isinstance(cached, FileNotFoundError), shown(cached))

    # ---- the source guard: no game module but the reader reads the code's source
    def source_reads(text: str) -> list[tuple[int, str, str]]:
        """(line, what, the top-level name it stands in) for each read of the code's own source: ast.parse, inspect.getsource*, a glob
        of *.py, a .py file read or opened by name."""
        t = ast.parse(text)
        mods = {"ast": {"ast"}, "inspect": {"inspect"}}
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name in mods:
                        mods[a.name].add(a.asname or a.name)

        def is_mod(v, m):
            return (isinstance(v, ast.Name) and v.id in mods[m]) or (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                                                                      and v.func.id == "__import__" and v.args and isinstance(v.args[0], ast.Constant) and v.args[0].value == m)

        def names_py(node):
            return any(isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value.endswith(".py") for c in ast.walk(node))
        out = []
        for top in t.body:
            where = getattr(top, "name", "")
            for n in ast.walk(top):
                what = ""
                if isinstance(n, ast.Attribute) and n.attr == "parse" and is_mod(n.value, "ast"):
                    what = "ast.parse"
                elif isinstance(n, ast.Attribute) and n.attr.startswith("getsource") and is_mod(n.value, "inspect"):
                    what = "inspect." + n.attr
                elif isinstance(n, ast.ImportFrom) and n.module in ("ast", "inspect") and any(a.name == "parse" or a.name.startswith("getsource") for a in n.names):
                    what = f"from {n.module} import"
                elif isinstance(n, ast.Constant) and isinstance(n.value, str) and "*.py" in n.value:
                    what = "a glob of *.py"
                elif isinstance(n, ast.Call) and ((isinstance(n.func, ast.Attribute) and n.func.attr in ("read_text", "read_bytes", "open") and names_py(n.func.value))
                                                  or (isinstance(n.func, ast.Name) and n.func.id == "open" and n.args and names_py(n.args[0]))):
                    what = "a .py file read by name"
                if what:
                    out.append((n.lineno, what, where))
        return out

    planted = {"import ast\ndef f(p):\n    return ast.parse(p.read_text())\n": "ast.parse",
               "def f():\n    return __import__('ast').parse('x')\n": "ast.parse",
               "import inspect as ins\ndef f(g):\n    return ins.getsource(g)\n": "inspect.getsource",
               "from pathlib import Path\ndef f(r):\n    return list(Path(r).rglob('*.py'))\n": "a glob of *.py",
               "from pathlib import Path\nR = Path('.')\ndef f():\n    return (R / 'engine' / 'combat.py').read_text()\n": "a .py file read by name",
               "def f():\n    return open('engine/combat.py').read()\n": "a .py file read by name"}
    caught = {src: [w for _, w, _ in source_reads(src)] for src in planted}
    check("the guard catches each way of reading source, planted", all(want in caught[src] for src, want in planted.items()),
          {src: got for src, got in caught.items() if planted[src] not in got})
    files = [ROOT / p for p in game_files()]
    elsewhere, in_check = [], []
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        for line, what, where in source_reads(p.read_text(encoding="utf-8")):
            (in_check if rel == "engine/data_check.py" else elsewhere).append((rel, line, what, where))
    check("in the forms this guard reads, no game module but data_check reads the code's source (the fence below holds every other form)",
          not elsewhere and len(files) > 100, elsewhere[:5])
    check("...and in data_check only the reader does, which the guard sees doing it",
          in_check and all(where in READER for _, _, _, where in in_check), [x for x in in_check if x[3] not in READER][:5] or in_check)

    # ---- the fence sees what the guard cannot: each way of reading the code, planted, is noted while the check runs as a build
    import linecache
    import tokenize
    from engine import combat

    def own_file():
        Path(combat.__file__).read_text(encoding="utf-8")

    def open_file():
        open(data_check.__file__, encoding="utf-8").close()

    def path_in_a_name():
        for rel in ("engine/combat.py",):                             # scan_code's own shape: the path in a variable
            (ROOT / rel).read_text(encoding="utf-8")

    def tokenized():
        tokenize.open(combat.__file__).close()

    def by_line():
        linecache.clearcache()
        linecache.getline(combat.__file__, 1)

    def listed_by_suffix():
        return [p for p in (ROOT / "engine").iterdir() if p.suffix == ".py"]

    def listed_by_ending():
        return [n for n in os.listdir(ROOT / "scenes") if n.endswith(".py")]

    def globbed():
        import glob
        return glob.glob(str(ROOT / "llm" / "*.py"))
    noted = {}
    for fn in (own_file, open_file, path_in_a_name, tokenized, by_line, listed_by_suffix, listed_by_ending, globbed):
        with as_built(), fenced() as seen:
            fn()
        noted[fn.__name__] = list(seen)
    check("the fence notes each way of reading the code in a build, planted: a module's __file__ read or opened, a path held in a name, "
          "tokenize, linecache, a folder listed by suffix or ending, a glob", all(noted.values()), {k: v for k, v in noted.items() if not v})
    import importlib
    probe = scratch / "probe"
    probe.mkdir()
    (probe / "fence_probe_775.py").write_text("ANSWER = 42\n", encoding="utf-8")   # never compiled before: its source is read
    sys.path.insert(0, str(probe))
    try:
        with fenced() as seen:
            got = importlib.import_module("fence_probe_775").ANSWER
    finally:
        sys.path.remove(str(probe))
    check("...and not the import system, which reads a module's source when there is one to read", got == 42 and not seen, seen[:3])

    # ---- the self-check: python main.py --check, Meravia.exe --check
    try:
        from core import selfcheck
    except ImportError as e:
        selfcheck = None
        check("core/selfcheck.py is there, for main.py --check", False, repr(e))
    if selfcheck is not None:
        from ui.gui import server
        from llm import runtime
        logs = scratch / "logs"
        log = logs / "selfcheck.log"
        started: list[str] = []

        def no_process(*a, **k):
            started.append(f"a process: {a[:1]}")
            raise RuntimeError("the self-check starts no process")

        def no_lock(self):
            started.append("the game's lock")
            return False

        def run_quiet(**kw) -> tuple[int, str]:
            """The self-check's answer and its log, nothing printed; a lock taken or a process started is noted."""
            if log.exists():
                log.unlink()
            with contextlib.redirect_stdout(io.StringIO()), replaced(subprocess, "Popen", no_process), \
                    replaced(runtime.GameLock, "acquire", no_lock):
                code = selfcheck.run(log=log, **kw)
            return code, (log.read_text(encoding="utf-8") if log.exists() else "")

        stand_in = types.ModuleType("webview")                          # the window library: CI's Python has none
        had = sys.modules.get("webview", "absent")
        try:
            sys.modules["webview"] = stand_in
            code_src, text_src = run_quiet()
            check("the self-check passes from source on this tree: 0, and a log that says so", code_src == 0 and "PASSED" in text_src, text_src[-1500:])
            check("...it reads the data, the world as written, the traits and every file the window serves",
                  all(f"{part}: ok" in text_src for part in ("the data check", "the world as written", "the traits", "the window's files")), text_src[:800])
            check("...and takes no lock and starts no process (no model server)", not started, started)
            with as_built(), fenced() as opened_b:
                code_b, text_b = run_quiet()
            check("a built game passes its own self-check: 0, the window library loaded", code_b == 0 and "the window library: ok" in text_b
                  and "a built game" in text_b, text_b[-1500:])
            budget_file = built_tree / "data" / "rules" / "budget.yaml"
            kept = budget_file.read_text(encoding="utf-8")
            try:
                budget_file.write_text(kept.replace("\nlimit_seconds: 60", "\nlimit_seconds: soon", 1), encoding="utf-8")
                with as_built(), fenced() as opened_p:
                    code_p, text_p = run_quiet()
            finally:
                budget_file.write_text(kept, encoding="utf-8")
            check("a planted data problem: 1, and the log names it", code_p == 1 and told in text_p and "FAILED" in text_p, text_p[-1500:])
            web = scratch / "web"
            shutil.copytree(server.WEB, web)
            (web / "app.js").unlink()
            with replaced(data_check, "check", lambda: []), replaced(server, "WEB", web), as_built(), fenced() as opened_w:
                code_w, text_w = run_quiet()
            check("a page file missing: 1, and the log names it", code_w == 1 and "app.js" in text_w and "the window's files: 1 problem" in text_w, text_w[-1500:])
            check("...and none of these self-checks as a build opens a .py or lists a folder of the code (a part that raises is left out:"
                  " its trace reads the lines of source a build lacks, as traceback does anywhere)", not (opened_b or opened_p or opened_w),
                  (opened_b + opened_p + opened_w)[:5])
            sys.modules["webview"] = None                                # import webview now fails
            with replaced(data_check, "check", lambda: []), as_built():
                code_l, text_l = run_quiet()
            check("a built game without its window library: 1, and the log says so", code_l == 1 and "the window library: 1 problem" in text_l, text_l[-1500:])
            with replaced(data_check, "check", lambda: []):
                code_n, text_n = run_quiet()
            check("...from source the window library is not asked (the browser stands in for it there)", code_n == 0 and "window library" not in text_n, text_n[-800:])

            def raises():
                raise FileNotFoundError("engine/combat_improv.py")
            with replaced(data_check, "check", raises):
                code_r, text_r = run_quiet()
            check("a part that raises is a problem told, not a crash with no log: 1, the error and its trace in the log",
                  code_r == 1 and "FileNotFoundError: engine/combat_improv.py" in text_r and "Traceback" in text_r, text_r[-1500:])
            with replaced(data_check, "check", lambda: []):
                with contextlib.redirect_stdout(io.StringIO()):
                    selfcheck.run(log=log)
                    selfcheck.run(log=log)
            text_twice = log.read_text(encoding="utf-8")
            check("the log is written anew each run, so it does not grow", text_twice.count("its own check") == 1, text_twice[:400])
            said: list[str] = []
            with replaced(data_check, "check", lambda: []):
                selfcheck.run(log=log, say=said.append)
            check("...and what it wrote is handed whole to the way out its caller gives (it prints nothing itself)",
                  said == [log.read_text(encoding="utf-8").rstrip("\n")], said[:1])
            app_was = paths.APP
            held_logs = os.environ.pop("MERAVIA_LOGS", None)             # (f779) a player's game names no test's logs folder
            try:
                with replaced(paths, "APP", scratch / "exe_folder"):
                    where = selfcheck.log_path()
            finally:
                if held_logs is not None:
                    os.environ["MERAVIA_LOGS"] = held_logs
            check("its log lies beside the exe: logs/selfcheck.log under core.paths.APP, asked at the call",
                  where == scratch / "exe_folder" / "logs" / "selfcheck.log" and paths.APP == app_was, where)
        finally:
            if had == "absent":
                sys.modules.pop("webview", None)
            else:
                sys.modules["webview"] = had

        # ---- main.py --check runs the self-check alone, and its answer is the exit code
        import main as game_main
        from ui import console
        ran: list = []
        argv = sys.argv
        try:
            sys.argv = ["main.py", "--check"]
            with replaced(selfcheck, "run", lambda log=None, say=None: ran.append(("check", say)) or 1), \
                    replaced(game_main, "play", lambda args: ran.append("play")), \
                    replaced(game_main, "guarded", lambda run, bridge: ran.append("guarded")):
                exited = attempt(game_main.main)
        except SystemExit as e:
            exited = e
        finally:
            sys.argv = argv
        check("main.py --check runs the self-check and nothing of the game, tells it through the console, and exits with its answer",
              isinstance(exited, SystemExit) and exited.code == 1 and ran == [("check", console.out)], (shown(exited), ran))

    # ---- the build: a tree that fails its check is never built, and a build that fails its check is never handed over
    bat = [l.strip() for l in (ROOT / "build_exe.bat").read_text(encoding="utf-8").splitlines()]
    steps = [l for l in bat if l and not l.upper().startswith("REM")]

    def at(pred) -> int:
        return next((i for i, l in enumerate(steps) if pred(l)), -1)
    src_check = at(lambda l: "main.py --check" in l)
    pyinstaller = at(lambda l: "-m PyInstaller" in l)
    exe_check = at(lambda l: "Meravia.exe" in l and "--check" in l and "echo" not in l.lower())
    handed = at(lambda l: l.lower().startswith("echo built:"))
    last_copy = max((i for i, l in enumerate(steps) if "xcopy" in l.lower() or "dist\\meravia\\runtime\" (" in l.lower()), default=-1)
    check("build_exe.bat checks the tree from source before PyInstaller, and stops on a failed check",
          0 <= src_check < pyinstaller and steps[src_check].endswith("|| goto :fail"), steps[src_check] if src_check >= 0 else bat[:14])
    after = steps[exe_check:handed] if 0 <= exe_check < handed else []
    check("...then runs the built game's own check on the folder as handed over (after the server's builds are copied in, just before"
          " 'Built:'), failing the build on it",
          pyinstaller < last_copy < exe_check < handed and any("goto :fail" in l for l in after[1:])
          and any("selfcheck.log" in l and "not exist" in l and "goto :fail" in l for l in after)
          and not any(l.lower().startswith(("if exist \"runtime", "xcopy", "python -m")) for l in after), after or steps[pyinstaller:])
    check("...and the built game ships no log of its own check", any(l.lower().startswith("del ") and "dist\\Meravia\\logs\\selfcheck.log" in l for l in after), after)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
