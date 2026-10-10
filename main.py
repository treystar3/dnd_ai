"""Play the game.

    python main.py            continue your saved game, or start a new one
    python main.py --new      start over (the old save is kept as a backup)
    python main.py --debug    show what the engine is deciding behind the scenes

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
    args = parser.parse_args()
    config.DEBUG = args.debug
    from llm.gateway import trim_log
    trim_log()

    try:
        world = load_world()
    except WorldError as e:
        print(e)
        sys.exit(1)
    catalog = load_traits()

    folder = SAVES_DIR / CAMPAIGN
    if args.new and folder.exists():
        backup = SAVES_DIR / f"{CAMPAIGN}_backup_{datetime.now():%Y%m%d_%H%M%S}"
        shutil.move(str(folder), str(backup))
        console.note(f"Previous game moved to {backup}")

    store = CampaignStore.open_or_create(CAMPAIGN)
    if store.player_exists():
        player = store.load_player()
        console.note(f"Continuing as {player.character.name}, {player.character.custom_class}.")
    else:
        character = ThresholdScene().run()
        player = PlayerState(character=character, location=world.start_location)
        store.save_player(player)

    WorldScene(store, world, catalog, player).run()


if __name__ == "__main__":
    try:
        main()
    except LLMError as e:
        print("\nThe model couldn't produce a usable answer and the game can't continue from this point.")
        print("If you were already playing, everything up to your last completed action is saved.")
        print("If you were still creating your character, nothing was saved - run main.py to start creation again.")
        print(f"(details: {e} - see logs/llm_calls.jsonl)")
    except KeyboardInterrupt:
        print("\nInterrupted. Progress up to the last completed action is saved.")
    except Exception as e:
        if "connect" in f"{type(e).__name__} {e}".lower():
            print("\nCan't reach Ollama. Install it from ollama.com, start it, and pull the model once:")
            print(f"    ollama pull {config.MODEL}")
        else:
            raise
    finally:
        if paths.FROZEN:
            input("\nPress Enter to close...")
