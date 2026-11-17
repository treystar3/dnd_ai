"""(f717) What a test ran. tools/run_suite.py puts this folder on PYTHONPATH for each test it starts, so Python loads this file at
the start of that process (and of any process the test starts itself), and names the record to write in MERAVIA_RAN. Kept: every
function of the repo (MERAVIA_RAN_ROOT) the process entered, as (file, Class.method), a class's or a module's own lines as (file,
Class) and (file, <module>), every file under data/ it opened, and whether it started a Python process with an environment
that drops this record (`blind`: what that process ran is not known). Each function is seen once and its event switched off,
so the test runs at its own speed. With MERAVIA_RAN unset nothing is kept. A sitecustomize the interpreter had is loaded after."""
import os
import sys

_out = os.environ.get("MERAVIA_RAN")
_here = os.path.dirname(os.path.abspath(__file__))


def _begin() -> None:
    import atexit
    import json
    root = os.path.normcase(os.path.abspath(os.environ.get("MERAVIA_RAN_ROOT", "."))) + os.sep
    ran, data, blind = set(), set(), []
    mon, tool = sys.monitoring, 4                          # 4: an id no debugger, coverage tool or profiler takes

    def inside(name) -> str:
        """The path under the repo, with forward slashes; "" for anything else."""
        if not isinstance(name, str) or name.startswith("<"):
            return ""
        full = os.path.abspath(name)
        if not os.path.normcase(full).startswith(root):
            return ""
        rel = full[len(root):].replace(os.sep, "/")
        return "" if rel.startswith((".", "tools/suite_ran/")) or "/site-packages/" in rel else rel     # not this file: every test loads it

    def started(code, offset):
        rel = inside(code.co_filename)
        if rel:
            names = code.co_qualname.split(".<locals>")[0].split(".")
            while names and names[-1].startswith("<"):     # a lambda, a comprehension, the module's body: its owner's own lines
                names.pop()
            ran.add((rel, ".".join(names) or "<module>"))
        return mon.DISABLE

    def opened(event, args):
        try:
            if event == "open" and args:
                rel = inside(args[0])
                if rel.startswith("data/"):
                    data.add(rel)
            elif event == "subprocess.Popen" and len(args) > 3 and args[3] is not None and not blind:
                first = str(args[0] or (args[1] if isinstance(args[1], str) else (list(args[1]) or [""])[0]))
                if not args[0] and isinstance(args[1], str):               # Windows: one command line, its program first
                    first = first[1:].split('"')[0] if first.startswith('"') else first.split(" ")[0]
                env = args[3]
                if "python" in os.path.basename(first).lower() and (env.get("MERAVIA_RAN") != _out or _here not in str(env.get("PYTHONPATH", ""))):
                    blind.append(True)
        except Exception:
            pass

    def write() -> None:
        try:
            with open(f"{_out}.{os.getpid()}.json", "w", encoding="utf-8") as fh:
                json.dump({"ran": sorted(ran), "data": sorted(data), "blind": bool(blind)}, fh)
        except OSError:
            pass

    try:
        mon.use_tool_id(tool, "meravia_ran")
    except ValueError:
        return
    mon.register_callback(tool, mon.events.PY_START, started)
    mon.set_events(tool, mon.events.PY_START)
    sys.addaudithook(opened)
    atexit.register(write)


def _next() -> None:
    """The sitecustomize this one stands in front of, if the interpreter has one."""
    import importlib.machinery
    import importlib.util
    spec = importlib.machinery.PathFinder.find_spec("sitecustomize", [p for p in sys.path if os.path.abspath(p or ".") != _here])
    if spec is not None and spec.loader is not None:
        spec.loader.exec_module(importlib.util.module_from_spec(spec))


if _out and hasattr(sys, "monitoring"):
    _begin()
_next()
