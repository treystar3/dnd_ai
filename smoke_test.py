"""Phase 1 smoke test: concept -> class -> 15 actives -> 15 passives.

Usage:
    python smoke_test.py
    python smoke_test.py "A grave knight who draws power from fallen comrades"
"""

import sys
import time

import config
from character.creation import generate_actives, generate_passives, interpret_concept
from character import fit
from ui.console import show_actives, show_class, show_passives

DEFAULT_CONCEPT = (
    "I want to be a Dragoon. A warrior who fights with a spear, uses acrobatic "
    "attacks, and eventually wants to become capable of fighting dragons."
)


def timed(label, fn):
    start = time.perf_counter()
    result = fn()
    print(f"[{label}: {time.perf_counter() - start:.1f}s]")
    return result


def main():
    concept = " ".join(sys.argv[1:]) or DEFAULT_CONCEPT
    print(f"Model: {config.MODEL}\nConcept: {concept}\n")

    interp = timed("classify", lambda: interpret_concept(concept))
    show_class(interp)
    print(interp.summary)
    print(f"Best-fit stats:    {', '.join(fit.best_fits(fit.stat_scores(interp)))}")
    print(f"Best-fit triggers: {', '.join(fit.best_fits(fit.trigger_scores(interp)))}")

    actives = timed("actives", lambda: generate_actives(interp))
    show_actives(actives)

    passives = timed("passives", lambda: generate_passives(interp, actives))
    show_passives(passives)


if __name__ == "__main__":
    main()
