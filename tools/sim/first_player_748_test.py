"""(f748) The fight's rules gain no new read of the first player fighter (docs/design/33_audit_fix_plan/fight_core.md FIGHT_CORE-9,
the audit's engine2-9). A fight holds several player fighters in shape only (the owner, 2026-11-04), and its rules still address
the first of them as combat.player: whom the foes strike, whether the foes' phase runs, fleeing, guards, inspire. Multiplayer
(docs/design/17, M3) rewrites them to take the fighter they mean; until then none is added. The engine's reads of the one player
are counted one way (tools/sim/player_reads.py) and held per file by one fence (tools/sim/acting_character_630_test.py): the
scene's player, and the fight's first player fighter beside it. Proven here on source texts, measured against the engine as it
stands, on engine/damage.py beside engine/combat.py, where the audit found it (once either reads it no more, a made-up source of
known count stands in for it):
- one more read in the file is refused, named by its file, and not taken for a fall;
- one fewer asks for the file's figure to be lowered, and is not taken for a rise;
- a new engine file that reads it is refused;
- every way the engine reads a fight's first player is counted: the fight by its names, a fight held by a blow or a scene, by
  getattr, by a parameter typed as the fight, as self inside the Combat class, twice on one line; and what is not the fight's
  first player is not: the scene's player (counted on its own), the fight's list of player fighters and its side, a fighter's
  side named "player", an actor's player, a parameter typed as something else.
Run: python tools/sim/first_player_748_test.py"""
import ast
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
from player_reads import engine_reads, unrecorded

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


ROOT = Path(__file__).resolve().parent.parent.parent
real = {p.relative_to(ROOT).as_posix(): ast.parse(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "engine").rglob("*.py"))}


def fight(trees: dict) -> dict:
    """The fence's count of a fight's first player fighter read, per engine file."""
    return engine_reads(trees).get("fight", {})


def with_file(name: str, text: str) -> dict:
    return {**real, name: ast.parse(text)}


def counted(source: str) -> int:
    return fight({"engine/shape.py": ast.parse(source)}).get("engine/shape.py", 0)


now = fight(real)
# (f748) a case file that reads it no more is stood in for by a made-up source of known count, so the proof outlives the debt
STAND_IN = "def _aimed(combat):\n    return combat.player\n\n\ndef _held(b):\n    return b.combat.player.alive\n"
check("a made-up source of known count is counted, to stand in for a case file once it reads the fight's first player no more",
      counted(STAND_IN) == 2, counted(STAND_IN))
cases = {name: (ROOT / name).read_text(encoding="utf-8") if now.get(name) else STAND_IN for name in ("engine/combat.py", "engine/damage.py")}
for name in cases:
    print(f"     {name}: " + (f"as it stands, {now[name]} reads" if now.get(name) else "reads it no more; the made-up source stands in"))

# ---- one more, one fewer: the case that found it (engine/combat.py) and a second file of the kind (engine/damage.py)
ADDED = "\n\ndef _aimed(combat):\n    return combat.player\n"
for name, text in cases.items():
    base = fight(with_file(name, text))
    n = base.get(name, 0)
    over, fell = unrecorded(fight(with_file(name, text + ADDED)), base)
    check(f"one more read of the fight's first player in {name} is refused, named by its file", over == {name: (n + 1, n)} and not fell,
          (over, fell))
    fewer, cut = re.subn(r"\bcombat\.player\b", "fighter", text, count=1)
    over, fell = unrecorded(fight(with_file(name, fewer)), base)
    check(f"...and one fewer asks for {name}'s figure to be lowered", cut == 1 and fell == {name: (n - 1, n)} and not over, (cut, over, fell))
over, fell = unrecorded(fight(with_file("engine/new_rule.py", "def aim(combat):\n    return combat.player.id\n")), now)
check("a new engine file that reads it is refused", over == {"engine/new_rule.py": (1, 0)} and not fell, (over, fell))

# ---- every way the engine reads it is counted
SHAPES = {
    "the fight by its name": ("def f(combat):\n    return combat.player\n", 1),
    "the fight by its other name": ("def f(fight):\n    return fight.player\n", 1),
    "a fight held by a blow": ("def f(b):\n    return b.combat.player\n", 1),
    "a fight held by a scene": ("def f(self):\n    return self.fight.player\n", 1),
    "by getattr": ("def f(combat):\n    return getattr(combat, 'player', None)\n", 1),
    "a parameter typed as the fight": ("def f(c: 'Combat'):\n    return c.player\n", 1),
    "a parameter typed as the fight by its module": ("def f(c: combat.Combat | None = None):\n    return c.player\n", 1),
    "self inside the Combat class": ("class Combat:\n    def first(self):\n        return self.player.id\n", 1),
    "twice on one line": ("def f(combat):\n    return combat.player if combat.player.alive else None\n", 2),
}
for what, (source, n) in SHAPES.items():
    check(f"counted: {what}", counted(source) == n, (counted(source), n))
NOT = {
    "the scene's player": "def f(ws):\n    return ws.player\n",
    "the fight's list of player fighters": "def f(combat):\n    return combat.player_fighters()\n",
    "the fight's side": "def f(combat):\n    return [x for x in combat.player_side()]\n",
    "a fighter's side named": "def f(x):\n    return x.side == 'player'\n",
    "an actor's player": "class Actor:\n    def name(self):\n        return self.player.character.id\n",
    "a parameter typed as something else": "def f(c: 'CombatScene'):\n    return c.player\n",
}
for what, source in NOT.items():
    check(f"not counted: {what}", counted(source) == 0, counted(source))
scene = engine_reads({"engine/shape.py": ast.parse(NOT["the scene's player"])}).get("scene", {})
check("...the scene's player is counted on its own, as before", scene == {"engine/shape.py": 1}, scene)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
