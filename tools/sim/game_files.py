"""(f788) The game's own code: one definition for every fence that reads it (owned_state_633's, kept here).

The game is every .py git lists (tracked, or not yet added and not ignored) outside the folders NOT_GAME names and the harnesses at
the root. So a top-level package added later (a player at another machine, checklist 8) is the game's at once, for every fence. A
fence that reads the programs the project runs beside the game too (the tools and the root harnesses, never the tests) asks for them
by name: game_files(with_tools=True)."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOT_GAME = {                                    # the top folders that are no part of the game, each with why
    "tools": "the tools run by hand, and the tests with their fixtures (tools/sim)",
    "data": "what the code reads, checked by the startup check: no code",
    "docs": "the designs, the measures and the play notes",
    ".claude": "the agents' instructions and settings",
}
HARNESS = {"simlib", "simbot", "simreport", "smoke_test", "bestiary_check", "world_check"}   # at the root: run by hand or by the tests
TESTS = "tools/sim"                             # the tests: never the game, and never among the tools


def game_files(root: Path = ROOT, with_tools: bool = False) -> list[Path]:
    """The game's .py files under root, as paths relative to it, sorted. with_tools: the programs run beside the game too (tools/ but
    its tests, and the harnesses at the root), for a fence over every program the project runs."""
    listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "*.py"], cwd=root,
                            capture_output=True, text=True, encoding="utf-8", check=True).stdout.split("\0")
    out = []
    for rel in sorted(set(filter(None, listed))):
        p = Path(rel)
        if not (root / p).is_file():
            continue
        top = p.parts[0] if len(p.parts) > 1 else ""
        harness = len(p.parts) == 1 and p.stem in HARNESS
        tool = top == "tools" and not rel.startswith(TESTS + "/")
        if (harness or top in NOT_GAME) and not (with_tools and (harness or tool)):
            continue
        out.append(p)
    return out
