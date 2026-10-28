"""(f364) The credits: CREDITS.md as the game shows it (#credits, and the home page's Credits), from the bundle when the game is built."""
from __future__ import annotations

from core import paths


def text() -> str:
    for folder in (paths.BUNDLE, paths.APP):
        p = folder / "CREDITS.md"
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip()
            except OSError:
                continue
    return "Credits: see CREDITS.md."
