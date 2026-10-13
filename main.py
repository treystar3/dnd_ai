"""Play the game.

    python main.py            continue your saved game, or start a new one
    python main.py --new      start over (the old save is kept as a backup)
    python main.py --debug    show what the engine is deciding behind the scenes
    python main.py --gui      play in a window instead of the terminal (needs: pip install pywebview; falls back to your browser)
    dnd_ai.exe                the built game opens its window by itself (--terminal for the text version)

On start the game checks for Ollama and its model and offers to install and download what is missing (DND_SKIP_SETUP=1 skips the check).

Type 'quit' to save and exit.
"""

import argparse
import shutil
import sys
from datetime import datetime

import os

import config
from core import paths

if paths.FROZEN:
    os.chdir(paths.APP)          # saves/ and logs/ live beside the exe
from npc.traits import load_traits
from scenes.goddess import ThresholdScene
from scenes.world import WorldScene
from storage.campaign import SAVES_DIR, CampaignStore, PlayerState
from ui import console
from llm.gateway import LLMError
from world.loader import WorldError, load_world

CAMPAIGN = "main"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", action="store_true", help="start a new game")
    parser.add_argument("--debug", action="store_true", help="show engine decisions")
    parser.add_argument("--gui", action="store_true", help="play in a window instead of the terminal")
    parser.add_argument("--terminal", action="store_true", help="play in the terminal (the built app opens a window by default)")
    args = parser.parse_args()
    config.DEBUG = args.debug
    for name in ("stdout", "stderr"):          # a windowed build has no console: keep stray prints from crashing it
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))
    if args.gui or (paths.FROZEN and not args.terminal):
        from ui import gui
        gui.launch(lambda bridge: guarded(lambda: play(args), bridge))
    else:
        guarded(lambda: play(args), None)


def play(args):
    from llm.gateway import trim_log
    trim_log()

    from llm import setup_check
    if not setup_check.ensure_ready():
        return

    try:
        world = load_world()
    except WorldError as e:
        console.out(str(e))
        sys.exit(1)
    catalog = load_traits()

    if not paths.FROZEN or args.terminal:
        from core import updates
        info = updates.available(timeout=3.0) if config.UPDATE_REPO else None
        if info:
            console.note(f"A newer version ({info['version']}) is available: {info['page']}")

    new_game = args.new
    while True:
        folder = SAVES_DIR / CAMPAIGN
        if new_game and folder.exists():
            backup = SAVES_DIR / f"{CAMPAIGN}_backup_{datetime.now():%Y%m%d_%H%M%S}"
            shutil.move(str(folder), str(backup))
            console.note(f"Previous game moved to {backup}")
        new_game = False
        console.combat_state(None)                 # a fight from the game just left must not linger in the window

        store = CampaignStore.open_or_create(CAMPAIGN)
        if store.player_exists():
            player = store.load_player()
            console.note(f"Continuing as {player.character.name}, {player.character.custom_class}.")
        else:
            character = ThresholdScene().run()
            player = PlayerState(character=character, location=world.start_location)
            store.save_player(player)

        scene = WorldScene(store, world, catalog, player)
        scene.run()
        if not getattr(scene, "restart", False):
            return
        new_game = True


def guarded(run, bridge):
    """Run the game and turn the known failures into readable messages (in the terminal or the window)."""
    try:
        run()
    except LLMError as e:
        console.out("\nThe model couldn't produce a usable answer and the game can't continue from this point.")
        console.out("If you were already playing, everything up to your last completed action is saved.")
        console.out("If you were still creating your character, nothing was saved - run main.py to start creation again.")
        console.out(f"(details: {e} - see logs/llm_calls.jsonl)")
        if bridge:
            bridge.failed = True
    except KeyboardInterrupt:
        console.out("\nInterrupted. Progress up to the last completed action is saved.")
    except SystemExit:
        raise
    except Exception as e:
        if bridge:
            bridge.failed = True
        if "connect" in f"{type(e).__name__} {e}".lower():
            console.out("\nCan't reach Ollama. Install it from ollama.com, start it, and pull the model once:")
            console.out(f"    ollama pull {config.MODEL}")
        elif bridge:
            import traceback
            console.out("\nSomething went wrong and the game has to stop. Progress up to your last completed action is saved.")
            console.out(traceback.format_exc())
        else:
            raise
    finally:
        if paths.FROZEN and not bridge:
            input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
