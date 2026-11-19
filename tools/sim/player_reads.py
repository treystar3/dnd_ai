"""The engine's reads of the one player, counted one way. tools/sim/acting_character_630_test.py holds the figure for each file and
runs the fence over the code as it stands: a count only falls, and one that fell is lowered there. Multiplayer (docs/design/17, M1
and M3) rewrites what is counted here to take a character's or a fighter's id.
- players_read(node, names, also): the lines where a scene's player is read (ws.player, scene.player, x.ws.player, getattr).
- fight_players_read(node): the lines where a fight's first player fighter is read (combat.player and its kin).
- engine_reads(trees): for each engine file, how many reads of each kind it holds: "scene", the scene's player; "fight", a
  fight's first player fighter.
- unrecorded(found, recorded): the files whose count is past their figure, and the figures a fallen count leaves standing.
"""
import ast
import re

SCENE = ("ws", "scene", "self")
FIGHT = ("combat", "fight")                              # (f748) the names a fight goes by in the engine, and what holds one


def _reads(node, names, via=(), attrs=("player",)) -> list:
    """The nodes that read one of `attrs` off a receiver named in `names` or held as an attribute named in `via`, or by getattr."""
    held = lambda v: isinstance(v, ast.Name) and v.id in names or isinstance(v, ast.Attribute) and v.attr in via
    return [n for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr in attrs and held(n.value)
            or isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 2
            and held(n.args[0]) and isinstance(n.args[1], ast.Constant) and n.args[1].value in attrs]


def players_read(node, names=SCENE, also=()) -> list[int]:
    """The lines where a scene's player is read: ws.player, scene.player, self.player, x.ws.player, or getattr(ws, "player"). With
    `also`, the scene's other names for the one player's (ws.place, ws.acting)."""
    return sorted(n.lineno for n in _reads(node, names, ("ws",), ("player",) + tuple(also)))


def fight_players_read(node) -> list[int]:
    """The lines where a fight's first player fighter is read: combat.player or fight.player, a fight held by something else
    (b.combat.player, self.fight.player), by getattr, by a parameter typed as the fight, and self.player inside the Combat class.
    Not seen, so the fence is not the whole of it: the first of the fight's list taken by hand (next(iter(combat.player_fighters())),
    combat.player_side()[0]) and the fight under a name of no type (c = combat; c.player)."""
    found = {id(n): n for n in _reads(node, FIGHT, FIGHT)}
    for n in ast.walk(node):
        if isinstance(n, ast.ClassDef) and n.name == "Combat":
            found.update((id(r), r) for r in _reads(n, ("self",)))
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = n.args.posonlyargs + n.args.args + n.args.kwonlyargs
            typed = tuple(a.arg for a in args if a.annotation is not None and re.search(r"\bCombat\b", ast.unparse(a.annotation)))
            if typed:
                found.update((id(r), r) for r in _reads(n, typed))
    return sorted(n.lineno for n in found.values())


def engine_reads(trees: dict) -> dict[str, dict[str, int]]:
    """For each kind of read, the engine files that hold any and how many: {kind: {file: count}}."""
    kinds = {"scene": lambda t: players_read(t, ("ws", "scene")), "fight": fight_players_read}
    counts = {kind: {name: len(count(tree)) for name, tree in trees.items() if name.startswith("engine/")} for kind, count in kinds.items()}
    return {kind: {name: n for name, n in found.items() if n} for kind, found in counts.items()}


def unrecorded(found: dict[str, int], recorded: dict[str, int]) -> tuple[dict, dict]:
    """The files whose count is past their figure (a file not recorded may hold none), and the figures that stand above a count
    that fell: each as {file: (found, recorded)}."""
    over = {f: (n, recorded.get(f, 0)) for f, n in found.items() if n > recorded.get(f, 0)}
    fell = {f: (found.get(f, 0), n) for f, n in recorded.items() if found.get(f, 0) < n}
    return over, fell
