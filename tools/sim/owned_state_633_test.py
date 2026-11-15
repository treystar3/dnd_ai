"""(f633) No state without a home (docs/design/20_phase3_plan.md; engine/owned.py).
The session's list of what a campaign leaves behind was kept by hand, and a module name written while the game plays that
nobody added to it was found only when two campaigns in one process met it. Held here, for every name of its kind:
- every module-level name in the game's code that is written after import is declared in one table (engine/owned.py STATE) as
  the turn's, the actor's, the campaign's, the process's or one call's own, with what puts it back. This test reads the
  syntax tree of every file of the game and fails on a written name the table does not declare: a name rebound through
  `global`, a container changed in place, an attribute set on a module-level object, and a name of another module set or
  changed through any name that module was imported by, `setattr` with a computed name included;
- the scan itself is held on an example of each way a name is written, and of what is not a write;
- the table holds no dead row (each names a module-level binding that is there, or one of the turn's registers or, f634, of
  the actor's caches), and what the session puts back at a campaign's open and close is the table's rows, in its order;
- every place the game ties something to a thread (a thread id, a thread-local, the current thread, a context variable) is
  one of those listed below, each with its reason.
What the scan cannot see: a container handed to a function that changes it, an object changed through its own methods, a
class's attributes changed through an instance, a module reached by a computed name (engine/owned.py itself puts names back
that way, each of them a row). The table declares those it knows of (the dice, the event bus).
Run: python tools/sim/owned_state_633_test.py"""
import ast
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

NOT_GAME = {"tools", "data", "docs", ".claude"}                       # the tools, the tests and their fixtures are no part of the game
HARNESS = {"simlib", "simbot", "simreport", "smoke_test", "bestiary_check", "world_check"}     # at the root: harnesses, run by hand or by the tests
MUTATORS = {"append", "extend", "clear", "update", "pop", "popitem", "setdefault", "add", "remove", "discard", "insert", "sort", "reverse",
            "appendleft", "popleft", "extendleft", "rotate", "subtract", "move_to_end", "difference_update", "intersection_update",
            "symmetric_difference_update"}
FUNCTION = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def game_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True, text=True, check=True).stdout.split()
    return [Path(p) for p in out if p.split("/")[0] not in NOT_GAME and Path(p).stem not in HARNESS and Path(p).exists()]


def module_of(path: Path) -> str:
    parts = list(path.with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def own(node):
    """The nodes of this function or module itself, not those of a function defined inside it."""
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        yield n
        if not isinstance(n, FUNCTION):
            stack.extend(ast.iter_child_nodes(n))


def bindings(tree) -> dict[str, int]:
    """Every name bound at module level, with its line: assignments, functions and classes. What a class binds in its own body
    is the class's, not the module's."""
    top = {}
    stack = list(ast.iter_child_nodes(tree))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            top.setdefault(n.name, n.lineno)
            continue
        if isinstance(n, ast.Lambda):
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            top.setdefault(n.id, n.lineno)
        stack.extend(ast.iter_child_nodes(n))
    return top


def imports(node, mods: set, env: dict) -> None:
    """The game's modules and their names this scope imports, under the names it gives them."""
    for n in own(node):
        if isinstance(n, ast.ImportFrom) and n.module and not n.level:
            for a in n.names:
                if f"{n.module}.{a.name}" in mods:
                    env[a.asname or a.name] = ("module", f"{n.module}.{a.name}")
                elif n.module in mods:
                    env[a.asname or a.name] = ("name", n.module, a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name in mods:
                    env[a.asname or a.name.split(".")[0]] = ("module", a.name) if a.asname or "." not in a.name else ("package", a.name.split(".")[0])


def chain(node):
    """What a store or a changing call hangs from: the name at its root, and the attributes on the way out (None for a subscript)."""
    path = []
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        path.append(node.attr if isinstance(node, ast.Attribute) else None)
        node = node.value
    return (node.id, path[::-1]) if isinstance(node, ast.Name) else (None, [])


def writes(source: str, here: str, mods: set) -> set[tuple[str, str, str]]:
    """Every write a function of this module makes to a module-level name: (module, name, how). Module-level code is the
    import itself and is not counted."""
    tree = ast.parse(source)
    top = bindings(tree)
    found = set()

    def target(env, name, path):
        kind = env.get(name)
        if kind is None:
            return None
        if kind[0] == "top":
            return here, name, path
        if kind[0] == "name":
            return kind[1], kind[2], path
        if kind[0] == "package":                            # `import engine.ledger`, then engine.ledger.X
            for i in range(len(path), 0, -1):
                if None not in path[:i] and ".".join([kind[1], *path[:i]]) in mods:
                    return (".".join([kind[1], *path[:i]]), path[i], path[i + 1:]) if len(path) > i and path[i] else None
            return None
        if kind[0] == "module":
            return (kind[1], path[0], path[1:]) if path and path[0] else None
        return None

    def visit(fn, outer):
        env = dict(outer)
        if not isinstance(fn, ast.Lambda):
            declared = {name for n in own(fn) if isinstance(n, ast.Global) for name in n.names}
        else:
            declared = set()
        a = fn.args
        params = [x.arg for x in a.args + a.kwonlyargs + a.posonlyargs] + ([a.vararg.arg] if a.vararg else []) + ([a.kwarg.arg] if a.kwarg else [])
        stored = {n.id for n in own(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        inner = {n.name for n in own(fn) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        for name in set(params) | stored | inner:
            env[name] = ("local",)
        imports(fn, mods, env)
        for name in declared:
            env[name] = ("top",)
        for n in own(fn):
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)) and n.id in declared:
                found.add((here, n.id, "rebound"))
            elif isinstance(n, (ast.Attribute, ast.Subscript)) and isinstance(n.ctx, (ast.Store, ast.Del)):
                name, path = chain(n)
                t = target(env, name, path) if name else None
                if t:
                    found.add((t[0], t[1], "changed" if t[2] or env[name][0] in ("top", "name") else "rebound"))
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in MUTATORS:
                name, path = chain(n.func.value)
                t = target(env, name, path) if name else None
                if t:
                    found.add((t[0], t[1], "changed"))
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("setattr", "delattr") and len(n.args) >= 2 \
                    and isinstance(n.args[0], ast.Name) and env.get(n.args[0].id, ("",))[0] == "module":
                given = n.args[1]
                found.add((env[n.args[0].id][1], given.value if isinstance(given, ast.Constant) else "*", "rebound"))
        for n in own(fn):
            if isinstance(n, FUNCTION):
                visit(n, env)

    base = {name: ("top",) for name in top}
    imports(tree, mods, base)
    for n in own(tree):
        if isinstance(n, FUNCTION):
            visit(n, base)
    return found


# ---- the scan, held on an example of each way a name is written
MODS = {"engine.a", "engine.b", "engine"}
CAUGHT = {
    "a name rebound through global": ("X = 0\ndef f():\n    global X\n    X = 1\n", ("engine.a", "X")),
    "a name added to through global": ("X = 0\ndef f():\n    global X\n    X += 1\n", ("engine.a", "X")),
    "a list appended to": ("X = []\ndef f(v):\n    X.append(v)\n", ("engine.a", "X")),
    "a dict's key set": ("X = {}\ndef f(k, v):\n    X[k] = v\n", ("engine.a", "X")),
    "a key deleted": ("X = {}\ndef f(k):\n    del X[k]\n", ("engine.a", "X")),
    "a slice replaced": ("X = []\ndef f():\n    X[:] = []\n", ("engine.a", "X")),
    "a list inside a dict appended to": ("X = {'a': []}\ndef f(v):\n    X['a'].append(v)\n", ("engine.a", "X")),
    "an attribute set on a module-level object": ("import threading\nX = threading.local()\ndef f(v):\n    X.serving = v\n", ("engine.a", "X")),
    "a class's attribute set": ("class C:\n    n = 0\ndef f():\n    C.n = 1\n", ("engine.a", "C")),
    "a write in a method": ("X = {}\nclass C:\n    def m(self):\n        X.clear()\n", ("engine.a", "X")),
    "a write in a function inside a function": ("X = []\ndef f():\n    def g():\n        X.append(1)\n    return g\n", ("engine.a", "X")),
    "a write in a lambda": ("X = {}\nf = lambda: X.update(a=1)\n", ("engine.a", "X")),
    "another module's name set": ("from engine import b\ndef f():\n    b.Y = 1\n", ("engine.b", "Y")),
    "another module's name set under another name": ("from engine import b as other\ndef f():\n    other.Y = 1\n", ("engine.b", "Y")),
    "another module's container changed": ("def f():\n    from engine import b\n    b.Y.clear()\n", ("engine.b", "Y")),
    "another module's key set": ("import engine.b as other\ndef f():\n    other.Y['k'] = 1\n", ("engine.b", "Y")),
    "the module's path spelled whole": ("import engine.b\ndef f():\n    engine.b.Y = 1\n", ("engine.b", "Y")),
    "a name imported from another module, changed": ("from engine.b import Y\ndef f():\n    Y.append(1)\n", ("engine.b", "Y")),
    "setattr on another module": ("from engine import b\ndef f():\n    setattr(b, 'Y', 1)\n", ("engine.b", "Y")),
    "setattr with a computed name": ("from engine import b\ndef f(name):\n    setattr(b, name, 1)\n", ("engine.b", "*")),
}
PASSED = {
    "a read": "X = {}\ndef f(k):\n    return X.get(k), X[k], len(X)\n",
    "a local of the same name": "X = []\ndef f():\n    X = []\n    X.append(1)\n    return X\n",
    "a parameter of the same name as an imported module": "def g():\n    from engine import b\n    return b\ndef f(b):\n    b.Y = 1\n    b.rows.append(2)\n",
    "an attribute of an argument": "def f(self, other):\n    self.rows.append(1)\n    other.name = 'x'\n",
    "module-level code": "X = {}\nX['a'] = 1\nX.update(b=2)\n",
    "a name outside the game": "import os\ndef f():\n    os.environ['A'] = 'b'\n",
    "another module's function called": "from engine import b\ndef f():\n    b.reset()\n    b.Y.get(1)\n",
}
missed = {k: sorted(writes(src, "engine.a", MODS)) for k, (src, want) in CAUGHT.items() if want not in {(m, n) for m, n, _ in writes(src, "engine.a", MODS)}}
check("the scan sees every way a module-level name is written after import", not missed, missed)
wrong = {k: sorted(writes(src, "engine.a", MODS)) for k, src in PASSED.items() if writes(src, "engine.a", MODS)}
check("...and takes none of what is not a write for one", not wrong, wrong)
names = bindings(ast.parse("X = 1\nif X:\n    Y: int = 2\nclass C:\n    held = {}\n    def m(self):\n        Z = 3\ndef f():\n    W = 4\n"))
check("a module's names are what it binds itself, never what a class or a function binds inside", set(names) == {"X", "Y", "C", "f"}, names)

# ---- the game's code against the table
try:
    from engine import owned
except ImportError as e:
    check("the table is there (engine/owned.py)", False, e)
    print("\nFAILED: " + ", ".join(bad))
    sys.exit(1)
from engine import actor, session

FILES = game_files()
PATHS = {module_of(p): p for p in FILES}
TREES = {m: ast.parse(p.read_text(encoding="utf-8")) for m, p in PATHS.items()}
written: dict[tuple[str, str], set] = {}
for m, p in PATHS.items():
    for mod, name, how in writes(p.read_text(encoding="utf-8"), m, set(PATHS)):
        written.setdefault((mod, name), set()).add(f"{how} in {m}")
check("(the scan read the game: its packages and the two modules at the root, never the tools or the tests)", len(FILES) > 200
      and {"main", "config", "engine.session", "scenes.world", "llm.gateway", "ui.console", "character.creation"} <= set(PATHS)
      and not any(m.split(".")[0] in ("tools", "simlib") for m in PATHS), len(FILES))
undeclared = {f"{m}.{n}": sorted(how) for (m, n), how in sorted(written.items()) if f"{m}.{n}" not in owned.STATE}
check("every module-level name the game writes after import is declared in the table", not undeclared, undeclared)

REGISTER, CACHE = "engine.actor.Registers.", "engine.actor.Caches."
HELD = {REGISTER: actor.Registers, CACHE: actor.Caches}
dead = []
for key, row in owned.STATE.items():
    if key.startswith(owned.HELD) and key.count(".") == 3:
        if key.rsplit(".", 1)[1] not in HELD.get(key.rsplit(".", 1)[0] + ".", actor.Held).FRESH:
            dead.append(key)
        continue
    mod, _, name = key.rpartition(".")
    if mod not in TREES or (name not in bindings(TREES[mod]) if name != "*" else (mod, "*") not in written):
        dead.append(key)
check("the table holds no dead row: each names a module-level binding that is there, or one of the registers or the caches", not dead, dead)
check("every one of the turn's registers is a row, the turn's", all(owned.STATE.get(REGISTER + f) and owned.STATE[REGISTER + f].scope == owned.TURN
                                                                   for f in actor.Registers.FRESH), sorted(actor.Registers.FRESH))
check("(f634) every one of the actor's caches is a row, the actor's, and nothing else is the actor's any more",
      {k for k, r in owned.STATE.items() if r.scope == owned.ACTOR} == {CACHE + f for f in actor.Caches.FRESH} and len(actor.Caches.FRESH) == 8,
      sorted(k for k, r in owned.STATE.items() if r.scope == owned.ACTOR))
shape = [k for k, r in owned.STATE.items() if r.scope not in owned.SCOPES or not r.resets.strip()
         or len({r.put_back is None, r.clean is None, r.what is None}) != 1]
check("every row says whose it is and what puts it back, and one the session puts back says how, when it is clean and what it holds", not shape, shape)
scopes = {s: sum(1 for r in owned.STATE.values() if r.scope == s) for s in owned.SCOPES}
check("each of the five scopes is used", all(scopes.values()) and set(owned.SCOPES) == {owned.TURN, owned.ACTOR, owned.CAMPAIGN, owned.PROCESS, owned.CALL}, scopes)

# ---- the rows found unowned before this (the plan's section 2, item 8) are declared
FIRST = ["engine.turnlog.COUNTS", "engine.streams.BEGUN", "llm.gateway._SEEN", "llm.gateway.TALLY", "llm.gateway.OUTCOMES", "llm.gateway.FALLBACKS",
         "engine.names.REPAIRS", "engine.names.BY_TASK", "engine.hygiene.REPAIRS", "engine.crashlog.SESSION", "engine.refusals.SESSION",
         "llm.audit._count", "llm.audit._turn", "npc.backfill._jobs", "engine.domain_events.RECENT", REGISTER + "shown", REGISTER + "serving"]
check("what nobody owned before this is in the table", all(k in owned.STATE for k in FIRST), [k for k in FIRST if k not in owned.STATE])

# ---- the session's reset and residue are the table's
mine = [(owned.label(k), r) for k, r in owned.STATE.items() if r.put_back is not None]
check("what the session puts back at a campaign's open and close is the table's rows, in its order", [n for n, *_ in session._owned()] == [n for n, _ in mine]
      and len(mine) >= 25, ([n for n, *_ in session._owned()][:5], len(mine)))
session_tree = TREES["engine.session"]
check("...and the session keeps no list of its own", not any(isinstance(n, ast.Lambda) for n in ast.walk(session_tree)),
      [n.lineno for n in ast.walk(session_tree) if isinstance(n, ast.Lambda)])
session.reset()
check("after a reset every row the session puts back is clean", session.residue() == {}, session.residue())
before = {k: r.clean() for k, r in owned.STATE.items() if r.clean is not None}
check("...by its own word", all(before.values()), [k for k, ok in before.items() if not ok])

# ---- where the game ties something to a thread
THREAD_SITES = {
    "engine.actor:Registers.claim": "the thread that plays the turn, taken by the first of a budget, an operation or a serving to open",
    "engine.actor:Registers.mine": "...and asked of every call: off that thread there is no turn",
    "engine.actor:<module>": "the actor bound on this thread (a context variable: each thread has its own)",
    "engine.streams:<module>": "the set of dice that answers on this thread (a context variable)",
    "engine.recording:Recorder.install.ask": "the thread asking for the next line, while it asks",
    "engine.recording:Recorder._layer": "...a call that thread makes meanwhile, or a closed session's thread makes, is passed through unrecorded",
    "llm.backend:<module>": "the lane and the task of the call being made on this thread (thread-locals, put back as the call returns)",
    "llm.gateway:<module>": "the task and the log's tags of the call being made on this thread (thread-locals)",
    "llm.gateway:trim_log": "a temp file's name, so two threads trimming at once never share one",
    "llm.llama:LlamaServer._flag": "a call in flight, by the thread making it, so a cancel reaches that call alone",
    "llm.llama:LlamaServer._done": "...forgotten as the call ends",
    "llm.worker:_Call.__init__": "the thread a waiting call belongs to: the Thread itself, since an id is used again once its thread ends",
    "llm.worker:Worker.__init__": "whether this thread's foreground call is being sent (a thread-local of the worker)",
    "llm.worker:Worker.background": "the calling thread's place among the background calls waiting for the card",
}
THREADY = {"get_ident", "current_thread", "local", "ContextVar"}


def thread_sites(tree) -> set[str]:
    out = set()

    def walk(node, where):
        for n in ast.iter_child_nodes(node):
            inner = where
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                inner = n.name if where == "<module>" else f"{where}.{n.name}"
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in THREADY and isinstance(n.func.value, ast.Name) \
                    and n.func.value.id in ("threading", "contextvars"):
                out.add(where)
            walk(n, inner)
    walk(tree, "<module>")
    return out


sites = {f"{m}:{w}" for m, tree in TREES.items() for w in thread_sites(tree)}
check("every place the game ties something to a thread is one of those listed, each with its reason", sites == set(THREAD_SITES),
      {"not listed": sorted(sites - set(THREAD_SITES)), "listed and gone": sorted(set(THREAD_SITES) - sites)})
bare = [m for m, tree in TREES.items() for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module in ("threading", "contextvars")
        and {a.name for a in n.names} & THREADY]
check("...none of them imported bare, where the list would not see it", not bare, bare)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
