"""(f717) What a test ran. tools/run_suite.py puts this folder on PYTHONPATH for each test it starts, so Python loads this file at
the start of that process (and of any process the test starts itself), and names the record to write in MERAVIA_RAN. Kept: every
function of the repo (MERAVIA_RAN_ROOT) the process entered, as (file, Class.method), a class's or a module's own lines as (file,
Class) and (file, <module>), every file under data/ it opened, and whether it started a Python process with an environment
that drops this record (`blind`: what that process ran is not known). Each function is seen once and its event switched off,
so the test runs at its own speed. With MERAVIA_RAN unset nothing is kept. A sitecustomize the interpreter had is loaded after.
(f779) And the fence, when MERAVIA_FENCE names its note (the runner names one for every test): no process of a test writes, moves
or removes anything under the project's own logs/ or recordings/, the owner's play. Such a write is refused (PermissionError) and
written in the note, and the runner fails the test, whatever the test made of the error. A name given with an open folder handle
(dir_fd, as rmtree on Linux gives) is read against that folder, and let through where the handle cannot be read; a write-mode
os.open(..., dir_fd=) is read against the working folder, since its audit event carries no dir_fd."""
import os
import sys

_out = os.environ.get("MERAVIA_RAN")
_here = os.path.dirname(os.path.abspath(__file__))


# (f779) per event, the argument holding the dir_fd of its first and second name (CPython's audit events; os.replace raises os.rename)
_FD_ARG = {"os.remove": (1,), "os.rmdir": (1,), "shutil.rmtree": (1,), "os.mkdir": (2,), "os.rename": (2, 3), "os.link": (2, 3),
           "os.symlink": (None, 2)}


def _dir_fd(event, args, which):
    """The open folder the event's name number `which` (0 the first, 1 the second) is relative to; None when it names a path whole."""
    at = _FD_ARG.get(event, ())
    i = at[which] if which < len(at) else None
    fd = args[i] if i is not None and len(args) > i else None
    return fd if isinstance(fd, int) and fd >= 0 else None


def _fd_dir(fd: int) -> str:
    """The folder an open folder handle names, read from /proc on Linux; elsewhere it raises, and the name is let through."""
    return os.readlink(f"/proc/self/fd/{fd}")


def _fence(note: str) -> None:
    root = os.path.dirname(os.path.dirname(_here))                     # the project this folder lies in
    guarded = tuple(os.path.normcase(os.path.realpath(os.path.join(root, d))) for d in ("logs", "recordings"))
    first = {"open", "os.mkdir", "os.remove", "os.rmdir", "os.truncate", "shutil.rmtree", "sqlite3.connect"}
    second = {"shutil.copyfile", "shutil.copytree", "os.link", "os.symlink"}   # (source, target): only the target is written
    flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | getattr(os, "O_TRUNC", 0)

    def inside(t, fd=None) -> str:
        if not isinstance(t, (str, bytes, os.PathLike)):
            return ""
        try:
            t = os.fsdecode(t)
            if isinstance(fd, int) and not os.path.isabs(t):           # (f779) a name relative to an open folder
                t = os.path.join(_fd_dir(fd), t)
            p = os.path.normcase(os.path.realpath(t))
        except (OSError, ValueError, TypeError):
            return ""
        return p if any(p == g or p.startswith(g + os.sep) for g in guarded) else ""

    noted = not inside(note)                                           # a note under the fence is never written (the runner refuses it)

    def hook(event, args):
        if event == "open":
            mode, fl = (list(args) + [None, None, None])[1:3]
            if not (isinstance(mode, str) and any(c in mode for c in "wax+") or mode is None and isinstance(fl, int) and fl & flags):
                return
        if event in first:
            targets = [(args[0] if args else None, _dir_fd(event, args, 0))]
        elif event in second:
            targets = [(args[1] if len(args) > 1 else None, _dir_fd(event, args, 1))]
        elif event == "os.rename":                                     # a move out of the folder takes a file from it
            targets = [(args[0], _dir_fd(event, args, 0)), (args[1], _dir_fd(event, args, 1))]
        else:
            return
        for t, fd in targets:
            p = inside(t, fd)
            if p:
                try:
                    if noted:
                        with open(note, "a", encoding="utf-8") as fh:
                            fh.write(f"{event} {p} (process {os.getpid()})\n")
                except OSError:
                    pass
                raise PermissionError(f"(f779) a test may not write under the project's own logs/ or recordings/: {event} {p}")

    sys.addaudithook(hook)


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


if os.environ.get("MERAVIA_FENCE"):
    _fence(os.environ["MERAVIA_FENCE"])
if _out and hasattr(sys, "monitoring"):
    _begin()
_next()
