"""(f648) Every word pattern searched over the whole typed line on its way to a deed, found by reading the code.

A line enters the game by a few doors, each declared: the world's turn, the intercepts (scenes/intercepts.py), the plan's repairs
(scenes/plan_repairs.py), the handler of each kind of deed (engine/actions.py, on_<kind>) and the fight's turn. From each door the
census follows the line through every method of the scene and every function it is handed to, and counts each place a pattern, a
word or a test of the text is searched over it: a compiled pattern's search, match or findall, re.search, `word in line`, and
startswith or endswith. The line is the parameter it came in as, any plain form of it (lowered, stripped, set in a longer string),
the clauses it is split into, and what a function of ours gives back for it as text or in a record of text fields. It stops where the line becomes prose for the narrator (narrate, and the modules that clean a
passage), which no deed is decided by.

tools/sim/line_patterns_648_test.py holds the count file by file, and the count only falls (docs/design/21_play_faults_plan.md, B0).
Run: python tools/line_census.py          the count by file
     python tools/line_census.py --sites  and every place, with the door it was reached from"""
from __future__ import annotations

import ast
import importlib
import inspect
import re
import sys
import textwrap
import types
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAIN = {"lower", "strip", "casefold", "rstrip", "lstrip", "replace", "removeprefix", "removesuffix", "title", "capitalize"}
SEARCHES = {"search", "match", "fullmatch", "findall", "finditer"}
TESTS = {"startswith", "endswith", "find", "count", "index"}
PROSE = ("engine.hygiene", "engine.voice_rules", "scenes.voice")          # a passage's cleaning: no deed is decided there
OURS = ("scenes", "engine", "services")


def _local_imports(tree) -> dict:
    """What a function imports inside itself (`from engine import actions` names the module `actions`)."""
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for a in node.names:
                try:
                    out[a.asname or a.name] = importlib.import_module(f"{node.module}.{a.name}")
                except ImportError:
                    try:
                        out[a.asname or a.name] = getattr(importlib.import_module(node.module), a.name)
                    except (ImportError, AttributeError):
                        pass
        elif isinstance(node, ast.Import):
            for a in node.names:
                try:
                    out[a.asname or a.name.split(".")[0]] = importlib.import_module(a.name if a.asname else a.name.split(".")[0])
                except ImportError:
                    pass
    return out


def _resolve(owner, scope: dict, func):
    """The function a call names: (class, function) for the scene's own method, (None, function) for a module's or the file's."""
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id in ("self", "cls") and owner is not None:
            f = inspect.getattr_static(owner, func.attr, None)
            return owner, getattr(f, "__func__", f)
        mod = scope.get(func.value.id)
        if isinstance(mod, types.ModuleType):
            return None, getattr(mod, func.attr, None)
        if inspect.isclass(mod):
            f = inspect.getattr_static(mod, func.attr, None)
            return mod, getattr(f, "__func__", f)
    if isinstance(func, ast.Name):
        return None, scope.get(func.id)
    return None, None


def _is_line(node, names: set) -> bool:
    """The node is the line: a name that holds it, a plain or reworded form of it (lowered, stripped, a word replaced, re.sub over
    it, its words joined again, a slice of it), or a longer string it is set in."""
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in PLAIN:
        node = node.func.value
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in ("sub", "subn") and len(node.args) >= 3:
            return _is_line(node.args[2], names)
        if node.func.attr == "join" and node.args:
            return _is_line(node.args[0], names) or _split_of(node.args[0], names)
    if isinstance(node, ast.Subscript):
        return _is_line(node.value, names)
    if isinstance(node, (ast.List, ast.Tuple)):                         # (f653) a list of words the line is one of, joined
        return any(_is_line(e, names) for e in node.elts)
    if isinstance(node, ast.IfExp):                                     # (f653) the line, or something else
        return _is_line(node.body, names) or _is_line(node.orelse, names)
    if isinstance(node, ast.Name):
        return node.id in names
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) and _is_line(v.value, names) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_line(node.left, names) or _is_line(node.right, names)
    if isinstance(node, ast.BoolOp):
        return any(_is_line(v, names) for v in node.values)
    return False


def _split_of(node, names: set) -> bool:
    """The node splits the line into clauses or words: line.split(), or re.split(pattern, line)."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "split"):
        return False
    return _is_line(node.func.value, names) or (len(node.args) > 1 and _is_line(node.args[1], names))


def _dispatched(owner, func, passed: int = 0) -> list:
    """The scene's methods a call reaches by name, getattr(self, f"party_{kind}"): every method of that prefix that takes as many
    arguments as the call passes."""
    if not (owner is not None and isinstance(func, ast.Call) and isinstance(func.func, ast.Name) and func.func.id == "getattr"
            and len(func.args) >= 2 and isinstance(func.args[0], ast.Name) and func.args[0].id == "self" and isinstance(func.args[1], ast.JoinedStr)):
        return []
    head = func.args[1].values[0] if func.args[1].values else None
    if not (isinstance(head, ast.Constant) and isinstance(head.value, str) and head.value):
        return []
    out = []
    for n in dir(owner):
        f = inspect.getattr_static(owner, n, None) if n.startswith(head.value) else None
        f = getattr(f, "__func__", f)
        if inspect.isfunction(f):
            positional = [p for p in inspect.signature(f).parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            if len(positional) - 1 == passed:                         # less the scene's own self
                out.append(f)
    return out


def sites(owner, fn, index: int, seen: set | None = None, door: str = "", ours: tuple = OURS) -> list[tuple]:
    """(file, line, column, function, what, door) for every search over the line in `fn` (its parameter `index` holds the line, the
    scene's own `self` not counted) and in everything it hands the line to."""
    seen = set() if seen is None else seen
    fn = getattr(fn, "__wrapped__", fn)
    if not inspect.isfunction(fn) or (fn, index) in seen or not fn.__module__.startswith(ours):
        return []
    if fn.__module__ in PROSE or fn.__name__.lstrip("_").startswith("narrate"):
        return []
    seen.add((fn, index))
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
    except (OSError, TypeError, SyntaxError):
        return []
    params = [a.arg for a in tree.args.args]
    if params and params[0] in ("self", "cls"):
        params = params[1:]
    if index >= len(params):
        return []
    names = {params[index]}
    scope = {**fn.__globals__, **_local_imports(tree)}
    re_names = {k for k, v in scope.items() if v is re} | {"re"}
    def gives_line(call) -> bool:
        """A function of ours handed the line that gives back text: the line reworded, or its parts (addressing.without, .clauses)."""
        if isinstance(call, ast.IfExp):                  # (f653) part = self.line_part(text, ...) if ... else ""
            return gives_line(call.body) or gives_line(call.orelse)
        while isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr in PLAIN:
            call = call.func.value                       # without(text, ...).replace(...) is still the line
        if not (isinstance(call, ast.Call) and any(_is_line(a, names) for a in call.args)):
            return False
        f = getattr(_resolve(owner, scope, call.func)[1], "__wrapped__", None)
        f = f or _resolve(owner, scope, call.func)[1]
        if not (inspect.isfunction(f) and f.__module__.startswith(ours)):
            return False
        back = str(f.__annotations__.get("return", "")).replace(" ", "")
        return back in ("str", "list[str]", "<class'str'>")

    def text_fields(call) -> list[int]:
        """(f649) The places of the text in each record a function of ours gives back for the line: list[Address], Address's `said`."""
        if not (isinstance(call, ast.Call) and any(_is_line(a, names) for a in call.args)):
            return []
        f = getattr(_resolve(owner, scope, call.func)[1], "__wrapped__", None)
        f = f or _resolve(owner, scope, call.func)[1]
        if not (inspect.isfunction(f) and f.__module__.startswith(ours)):
            return []
        m = re.fullmatch(r"list\[(\w+)\]", str(f.__annotations__.get("return", "")).replace(" ", ""))
        rec = f.__globals__.get(m.group(1)) if m else None
        fields = getattr(rec, "__annotations__", None) if inspect.isclass(rec) and hasattr(rec, "_fields") else None
        kind = lambda v: str(getattr(v, "__forward_arg__", v))                  # a record's fields read as text, or as ForwardRef('str')
        return [k for k, name in enumerate(rec._fields) if kind(fields.get(name, "")) in ("str", "<class 'str'>")] if fields else []

    grew = True
    while grew:
        grew = False
        for node in ast.walk(tree):
            new = []
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                    and (_is_line(node.value, names) or _split_of(node.value, names) or gives_line(node.value)):
                new.append(node.targets[0].id)
            elif isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.target, ast.Name) \
                    and (_is_line(node.iter, names) or _split_of(node.iter, names) or gives_line(node.iter)):
                new.append(node.target.id)
            elif isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.target, ast.Tuple):
                new += [node.target.elts[k].id for k in text_fields(node.iter)
                        if k < len(node.target.elts) and isinstance(node.target.elts[k], ast.Name)]
            for n in new:
                if n not in names:
                    names.add(n)
                    grew = True
    src = Path(inspect.getsourcefile(fn)).resolve()
    file = src.relative_to(ROOT).as_posix() if src.is_relative_to(ROOT) else src.name
    first = fn.__code__.co_firstlineno - 1
    aliases = {}                                          # handler = getattr(self, f"field_{x}"), called later as handler(...)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            calls = [c for c in ast.walk(tree) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == node.targets[0].id]
            got = [f for c in calls for f in _dispatched(owner, node.value, len(c.args))]
            if got:
                aliases[node.targets[0].id] = got
    out = []
    for node in ast.walk(tree):
        what = ""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            a = node.func.attr
            if a in SEARCHES:
                if isinstance(node.func.value, ast.Name) and node.func.value.id in re_names:
                    what = "re" if len(node.args) > 1 and _is_line(node.args[1], names) else ""
                elif node.args and _is_line(node.args[0], names):
                    what = "pattern"
            elif a in TESTS and _is_line(node.func.value, names):
                what = a
        elif isinstance(node, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in node.ops):
            if any(_is_line(c, names) for c in node.comparators):
                what = "in"
        if what:
            out.append((file, first + node.lineno, node.col_offset, fn.__qualname__, what, door))
        if isinstance(node, ast.Call):
            for i, arg in enumerate(node.args):
                if _is_line(arg, names):
                    o2, f2 = _resolve(owner, scope, node.func)
                    if f2 is not None:
                        out += sites(o2, f2, i, seen, door, ours)
                    held = aliases.get(node.func.id, ()) if isinstance(node.func, ast.Name) else ()
                    for f3 in [*_dispatched(owner, node.func, len(node.args)), *held]:
                        out += sites(owner, f3, i, seen, door, ours)
    return out


def doors():
    """(name, class, method, the index of the line among its parameters) for every way a typed line comes in."""
    from engine import actions
    from scenes import plan_repairs
    from scenes.combat_scene import CombatScene
    from scenes.world import WorldScene
    yield "turn", WorldScene, "turn", 0
    for ic in WorldScene.INTERCEPT_TABLE:
        yield f"intercept:{ic.name}", WorldScene, ic.method, 0
    for r in plan_repairs.gather(WorldScene):
        yield f"repair:{r.name}", WorldScene, r.method, 0
    for a in actions.ACTIONS:
        yield f"on_{a.kind}", WorldScene, f"on_{a.kind}", 1
    for n in sorted(n for n in dir(WorldScene) if n.startswith("on_answer_")):      # an answer to the world's own question (take_line)
        yield f"answer:{n[len('on_answer_'):]}", WorldScene, n, 1
    yield "fight:turn", CombatScene, "turn", 0


def census() -> tuple[dict, dict]:
    """(every place, each once: {(file, line, column): (function, what, the first door it was found from)}, and each door's own count)."""
    found, by_door = {}, {}
    for name, owner, method, index in doors():
        f = inspect.getattr_static(owner, method)
        got = sites(owner, getattr(f, "__func__", f), index, set(), name)
        by_door[name] = len({(s[0], s[1], s[2]) for s in got})
        for s in got:
            found.setdefault((s[0], s[1], s[2]), (s[3], s[4], s[5]))
    return found, by_door


def by_file(found: dict) -> dict:
    return dict(sorted(Counter(k[0] for k in found).items()))


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tools" / "sim"))
    import simlib
    simlib.install(simlib.Stub("warrior", 1))
    found, by_door = census()
    if "--sites" in sys.argv:
        for (f, ln, col), (fn, what, door) in sorted(found.items()):
            print(f"{f}:{ln}  {fn}  {what}  (from {door})", file=sys.__stdout__)
    for f, n in sorted(by_file(found).items(), key=lambda x: -x[1]):
        print(f"{n:4d}  {f}", file=sys.__stdout__)
    print(f"{len(found)} places in {len(by_file(found))} files", file=sys.__stdout__)
