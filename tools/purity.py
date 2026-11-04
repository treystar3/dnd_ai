"""(f476) The fence around Bundle D's pure modules: the builders that turn what was read from the save into a speaker's brief, a recall or
a conversation's next step, and decide nothing else. Each is a function of what it is given, so it may not reach the save, a scene or the
model, the clock or a uuid; may not draw dice except from its own keyed stream (engine/streams.py keyed); and may not let an order come
from a set's iteration or an object's id(), the orders that change from one process to the next and would part a replay.

    from tools import purity
    purity.problems(path)            # -> ["engine/brief.py:42: iterates a set unsorted", ...]

tools/sim/fence_476_test.py runs it on every module in PURE that exists; Bundle D adds each pure module to PURE as it is written."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PURE = ["engine/brief.py", "engine/recall.py", "engine/conversation.py", "engine/time_words.py"]   # grows as Bundle D writes them
FORBIDDEN_IMPORTS = ("storage", "scenes", "llm.gateway", "time", "datetime", "uuid")
RANDOM_OK = {"keyed"}                         # streams.keyed(...) is the one die a pure module may roll
# (f501) The DICE fence: the fight modules may roll only the streams (streams.get, keyed, fixed, new_id) and the two named constants, a
# scratch estimate's own die (engine/combat.py danger, Random(seed)) and the mentor probe's steady roll (Random(0)); never a die seeded by
# what was logged or by the clock (decision 5: nothing in play is seeded by what was logged). services/fight.py joins when f503 writes it.
DICE = ["engine/combat.py", "engine/combat_perks.py", "engine/spellcraft.py", "engine/behaviors.py", "engine/healing.py",
        "engine/afflictions.py", "engine/relics.py", "engine/bosses.py", "engine/summons.py", "engine/martial.py", "engine/movement.py",
        "engine/parley.py", "engine/party.py", "scenes/combat_scene.py", "services/fight.py"]
DICE_CONSTANTS = {("engine/combat.py", "random.Random(seed)"), ("engine/combat.py", "random.Random(0)")}
# (f503) The fight service (services/fight.py) under the dependency rule: scenes coordinate services; services use rules and
# repositories; a service writes nothing to the console, asks the model nothing, reads no clock, and names its dependencies once.
FIGHT = "services/fight.py"
FIGHT_FORBIDDEN = ("scenes", "ui", "llm.gateway", "llm.embed", "time", "datetime")
FIGHT_DEPENDS = ("store", "bus", "party", "streams")
# (f503) The write-path rule (tools/sim/battlefield_test.py): nothing outside the battlefield law writes spatial state. The directories
# it reads include services/.
WRITE_SCAN_DIRS = ("engine", "scenes", "npc", "services")
SPATIAL = ("zone_id", "row", "engaged_with", "position_tags", "band", "elevated")


def _imports(tree: ast.AST) -> list[tuple[int, str]]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(node.lineno, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            out.append((node.lineno, mod))
            if mod in ("", "llm"):
                out += [(node.lineno, f"{mod}.{a.name}".lstrip(".")) for a in node.names]
    return out


def _is_set(node: ast.AST) -> bool:
    return isinstance(node, (ast.Set, ast.SetComp)) or (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                                                         and node.func.id in ("set", "frozenset"))


def problems_in(source: str, name: str = "<source>") -> list[str]:
    tree = ast.parse(source)
    bad = []
    for line, mod in _imports(tree):
        if any(mod == f or mod.startswith(f + ".") for f in FORBIDDEN_IMPORTS):
            bad.append(f"{name}:{line}: imports {mod}")
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.comprehension)) and _is_set(node.iter):
            bad.append(f"{name}:{getattr(node, 'lineno', getattr(node.iter, 'lineno', 0))}: iterates a set unsorted")
        if isinstance(node, ast.Name) and node.id == "id" and isinstance(node.ctx, ast.Load):
            bad.append(f"{name}:{node.lineno}: orders by id()")              # called, or handed on as a sort key
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "random":
                bad.append(f"{name}:{node.lineno}: " + ("makes its own Random" if f.attr in ("Random", "SystemRandom") else f"rolls random.{f.attr}")
                           + " (draw from streams.keyed)")
            if isinstance(f, ast.Name) and f.id == "Random":
                bad.append(f"{name}:{node.lineno}: makes its own Random (draw from streams.keyed)")
            if isinstance(f, ast.Attribute) and f.attr in ("get", "new_id") and isinstance(f.value, ast.Name) and f.value.id == "streams":
                bad.append(f"{name}:{node.lineno}: draws streams.{f.attr} (a pure module draws only streams.keyed)")
        if isinstance(node, (ast.ListComp, ast.GeneratorExp)) and any(_is_set(g.iter) for g in node.generators):
            pass                                                      # reported once, through its comprehension
    return sorted(set(bad), key=lambda b: (int(b.split(":")[1]) if b.split(":")[1].isdigit() else 0, b))


def problems(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    rel = p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.name
    return problems_in(p.read_text(encoding="utf-8"), rel)


def check_all() -> list[str]:
    """Every pure module that exists, fenced."""
    out = []
    for rel in PURE:
        if (ROOT / rel).exists():
            out += problems(rel)
    return out


def dice_problems_in(source: str, name: str = "<source>") -> list[str]:
    """(f501) Every die a fight module makes outside the streams: random.Random(...) and random.<roll>(...) calls, less the named constants."""
    tree = ast.parse(source)
    lines = source.splitlines()
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        is_random = isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "random"
        is_bare = isinstance(f, ast.Name) and f.id in ("Random", "SystemRandom")
        if not (is_random or is_bare):
            continue
        text = lines[node.lineno - 1][node.col_offset:].split(",")[0].split(")")[0] + ")"
        if (name, text) in DICE_CONSTANTS:
            continue
        what = "makes its own Random" if (is_bare or f.attr in ("Random", "SystemRandom")) else f"rolls random.{f.attr}"
        bad.append(f"{name}:{node.lineno}: {what} (draw from the streams: get, keyed, fixed or new_id)")
    return sorted(set(bad), key=lambda b: (int(b.split(":")[1]) if b.split(":")[1].isdigit() else 0, b))


def check_dice() -> list[str]:
    """(f501) Every fight module that exists, under the DICE rule."""
    out = []
    for rel in DICE:
        p = ROOT / rel
        if p.exists():
            out += dice_problems_in(p.read_text(encoding="utf-8"), rel)
    return out


def fight_problems_in(source: str, name: str = FIGHT) -> list[str]:
    """(f503) What the fight service may not do: import scenes, ui, the model's gateway or embedder, or the clock; write to the console;
    print; roll a die outside the streams; depend on anything but store, bus, party and streams (its DEPENDS tuple, read as written)."""
    tree = ast.parse(source)
    bad = []
    for line, mod in _imports(tree):
        if any(mod == f or mod.startswith(f + ".") for f in FIGHT_FORBIDDEN):
            bad.append(f"{name}:{line}: imports {mod}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "console":
            bad.append(f"{name}:{node.lineno}: writes to the console (console.{node.attr})")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            bad.append(f"{name}:{node.lineno}: prints")
    bad += dice_problems_in(source, name)
    depends = [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "DEPENDS" for t in n.targets)]
    try:
        names = tuple(ast.literal_eval(depends[0].value)) if depends else ()
    except Exception:
        names = ()
    if names != FIGHT_DEPENDS:
        bad.append(f"{name}: DEPENDS names {names or 'nothing'}; the service depends on {', '.join(FIGHT_DEPENDS)} and nothing else")
    return sorted(set(bad), key=lambda b: (int(b.split(":")[1]) if b.split(":")[1].isdigit() else 0, b))


def check_fight() -> list[str]:
    """(f503) The fight service, fenced."""
    p = ROOT / FIGHT
    return fight_problems_in(p.read_text(encoding="utf-8"), FIGHT) if p.exists() else [f"{FIGHT} is missing"]


def spatial_writes_in(text: str, rel: str) -> list[str]:
    """(f503) The write-path rule on one module's source: every write of a fighter's zone, row, engagement or position tags outside the
    battlefield law (engine/battlefield.py), less combat.enters, the one sanctioned writer (it places a mid-fight joiner)."""
    import re
    if rel == "engine/battlefield.py":
        return []
    out = []
    for m in re.finditer(r"\.(" + "|".join(SPATIAL) + r")\s*=(?!=)", text):
        line = text[:m.start()].count("\n") + 1
        if rel == "engine/combat.py" and "def enters" in text[max(0, m.start() - 800):m.start()] and m.group(1) in ("zone_id", "row", "engaged_with"):
            continue
        out.append(f"{rel}:{line} writes .{m.group(1)}")
    return out


def spatial_writes() -> list[str]:
    """(f503) The write-path rule over every game module (WRITE_SCAN_DIRS), services/ included."""
    out = []
    for d in WRITE_SCAN_DIRS:
        for py in sorted((ROOT / d).glob("*.py")):
            rel = py.relative_to(ROOT).as_posix()
            out += spatial_writes_in(py.read_text(encoding="utf-8"), rel)
    return out
