"""Play the game.

    python main.py            the home page: continue, load another game, or start a new one
    python main.py --new      start a new character straight away (every other game stays saved)
    python main.py --debug    show what the engine is deciding behind the scenes
    python main.py --gui      play in a window instead of the terminal (needs: pip install pywebview; falls back to your browser)
    Meravia.exe               the built game opens its window by itself (--terminal for the text version)

On start the game checks for Ollama and its model and offers to install and download what is missing (MERAVIA_SKIP_SETUP=1 skips the check).

Type 'quit' to save and exit.
"""

import argparse
import sys

import os

import config
from core import paths
from core.version import VERSION

if paths.FROZEN:
    os.chdir(paths.APP)          # saves/ and logs/ live beside the exe
from npc.traits import load_traits
from scenes.goddess import ThresholdScene
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState, SaveTooNew
from storage import saves
from ui import console
from llm.gateway import LLMError, unload, warm
from world.loader import WorldError, authored, campaign_world


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
    import atexit
    atexit.register(unload)                        # however the game ends, the model does not stay in memory
    from engine import turnlog
    atexit.register(turnlog.write_session_stats)   # and the session leaves its one line in logs/sessions.jsonl
    try:
        if args.gui or (paths.FROZEN and not args.terminal):
            from ui import gui
            gui.launch(lambda bridge: guarded(lambda: play(args), bridge), title=config.GAME_TITLE)
        else:
            guarded(lambda: play(args), None)
    finally:
        unload()


def play(args):
    from llm.gateway import trim_log
    trim_log()

    from llm import setup_check
    if not setup_check.ensure_ready():
        return
    from llm import embed
    embed.pull_in_background()                     # the small helper model, fetched quietly the first time; the game does not wait for it
    warm()                                         # load the model while the player is at the title and typing their name

    from engine import data_check                  # the character data, checked as one system before anything uses it
    problems = data_check.check()
    if problems:
        console.out("The character data has problems (fix these in data/):\n" + "\n".join(f"  - {p}" for p in problems))
        sys.exit(1)
    try:
        written = authored()                       # (f434) the world as written: checked here, read by the home page, never played on
    except WorldError as e:
        console.out(str(e))
        sys.exit(1)
    catalog = load_traits()

    if not paths.FROZEN or args.terminal:
        from core import updates
        info = updates.available(timeout=3.0) if config.UPDATE_REPO and getattr(config, "UPDATE_CHECK", True) else None
        if info:
            console.note(f"A newer version ({info['version']}) is available (this is {info.get('current', VERSION)}): {info['page']}")
            if info.get("again"):
                console.note(f"It was installed already and the game still reports {info.get('current', VERSION)}: the installer on the release was "
                             "most likely built before its version number was raised. Installing it again will change nothing.")

    from scenes import home
    from npc import backfill
    choice = ("new", "") if args.new else None
    while True:
        console.combat_state(None)                 # a fight from the game just left must not linger in the window
        if choice is None:
            choice = home.choose(written)          # (f345) the home page: continue, load, new, delete, or quit
        kind, name = choice
        choice = None
        if kind == "quit":
            return
        if kind == "new":
            name = saves.new_name()
        try:
            store = CampaignStore.open_or_create(name)
        except SaveTooNew as e:
            console.note(str(e))
            continue
        saves.touch(name)
        console.home_done()
        world = campaign_world()                   # (f434) this campaign's own copy: what one save finds is never another's
        if store.player_exists():
            player = store.load_player()
            console.note(f"Continuing as {player.character.name}, {player.character.custom_class}.")
        else:
            character = ThresholdScene().run()
            if character is None:                      # Main menu during creation: there is no game yet, so a new one is not kept
                store.close()
                if kind == "new":
                    saves.discard(name)
                continue
            player = PlayerState(character=character, location=world.start_location)
            store.save_player(player)

        scene = WorldScene(store, world, catalog, player)
        rec = None
        if config.RECORD:                              # (f440) this session, kept so the real turn can replay it (tools/rerun.py)
            from engine import recording
            rec = recording.Recorder(store).install()
        try:
            scene.run()
        finally:
            if rec is not None:
                rec.close()
            store.close()                              # the database is written through as it goes; closing folds the write-ahead log in
            backfill.drop(store)                       # people still being written for this game must never reach the next one
        if getattr(scene, "to_menu", False):
            choice = None                              # the main menu: New game, Load and the rest are there
        else:
            return


def guarded(run, bridge):
    """Run the game and turn the known failures into readable messages (in the terminal or the window)."""
    try:
        run()
    except LLMError as e:
        console.out("\nThe model couldn't produce a usable answer and the game can't continue from this point.")
        console.out("If you were already playing, everything up to the start of your last action is saved; that action is not.")
        console.out("If you were still creating your character, nothing was saved - run main.py to start creation again.")
        console.out(f"(details: {e} - see logs/llm_calls.jsonl)")
        if bridge:
            bridge.failed = True
    except KeyboardInterrupt:
        console.out("\nInterrupted. Progress up to the start of the last action is saved; an action cut off partway is not.")
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
            console.out("\nSomething went wrong and the game has to stop. Progress up to the start of your last action is saved; that action is not.")
            console.out(traceback.format_exc())
        else:
            raise
    finally:
        if paths.FROZEN and not bridge:
            input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
