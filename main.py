"""Play the game.

    python main.py            the home page: continue, load another game, or start a new one
    python main.py --new      start a new character straight away (every other game stays saved)
    python main.py --debug    show what the engine is deciding behind the scenes
    python main.py --gui      play in a window instead of the terminal (needs: pip install pywebview; falls back to your browser)
    Meravia.exe               the built game opens its window by itself (--terminal for the text version)

On start the game starts its own model server from runtime/ and models/ (data/runtime/server.yaml, llm/runtime.py) and shows the home
page while it loads; Continue waits for it behind one line, New Game's first pages open at once (f528).

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
from engine.session import CampaignSession
from npc.traits import load_traits
from scenes.goddess import ThresholdScene
from storage.campaign import PlayerState, SaveTooNew
from storage import saves
from ui import console
from llm.errors import Cancelled, LLMError                     # (f514) from the module that imports no model client
from world.loader import WorldError, authored


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
    from engine import turnlog
    atexit.register(turnlog.write_session_stats)   # and the session leaves its one line in logs/sessions.jsonl
    try:
        if args.gui or (paths.FROZEN and not args.terminal):
            from ui import gui
            gui.launch(lambda bridge: guarded(lambda: play(args), bridge), title=config.GAME_TITLE)
        else:
            guarded(lambda: play(args), None)
    finally:
        if config.BACKEND != "llama":                  # (f528) the game's own server stops with the game
            from llm import launch, runtime
            launch.stop()                              # (f526) the load screen's server, when it started one
            runtime.stop_for_game()                    # (f522) ...or the one started before the page (the dormant case)


def play(args):
    from llm.gateway import trim_log
    trim_log()

    screen = None
    if config.BACKEND == "llama":                  # (f521) a llama-server started by hand: wait for it, and start nothing
        from llm import backend
        try:
            backend.load()
        except Exception as e:
            console.out(f"The llama-server at DND_LLAMA_URL could not be reached ({e}).")
            return
    else:                                          # (f528) the game as it ships: its own llama-server (f522), loaded behind the home page
        from llm import launch, runtime
        if launch.screen_on():                     # (f526) the owner's lines are in: the load runs behind the home page
            screen = launch.Screen(say=console.out, ask=console.ask,
                                   progress=lambda f: console.setup_progress(f, launch.line("loading") or ""),   # only while it waits
                                   uncover=lambda: console.creation_done())    # (f539) creation's page, over the could-not-wake page
            if not screen.begin():
                return
            launch.SCREEN["screen"] = screen
            import atexit
            atexit.register(launch.stop)
        elif not runtime.start_for_game(say=console.out):   # a tree without the lines (the dormant case): the load before the page
            return

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
            name = saves.new_name()                    # (f526) New Game's first pages open while the model loads; its first call waits
        elif screen is not None:
            console.home_done()                        # (f539) the home page goes first: the loading line, the could-not-wake page and
            if not screen.wait():                      # its choices are told in the story it would cover. Continue waits for the load
                return                                 # behind the loading line (Try again, or Quit)
        try:
            session = CampaignSession.open(name)       # (f453) the campaign's session: its store, its map (f434: its own, never another
        except SaveTooNew as e:                        # save's), the work it starts in the background, and what it closes when it ends
            console.note(str(e))
            continue
        saves.touch(name)
        console.home_done()
        if screen is not None:
            screen.flush()                             # (f526's review) what the load said, now, on this thread, at a page's edge;
                                                       # (f539) after the home page has gone, whose going clears the window's story
        store, world = session.store, session.world
        if store.player_exists():
            player = store.load_player()
            console.note(f"Continuing as {player.character.name}, {player.character.custom_class}.")
        else:
            character = ThresholdScene(session=session).run()
            if character is None:                      # Main menu during creation: there is no game yet, so a new one is not kept
                session.close()
                if kind == "new":
                    saves.discard(name)
                continue
            player = PlayerState(character=character, location=world.start_location)
            store.save_player(player)

        if screen is not None:
            screen.flush()                             # (f539) a load that finished during creation: its warning before the story
        scene = session.scene(catalog, player)
        if config.RECORD:                              # (f440) this session, kept so the real turn can replay it (tools/rerun.py)
            session.record()
        try:
            scene.run()
        finally:
            session.close()                            # the recorder, the background work, the database (written through as it goes;
                                                       # closing folds the write-ahead log in) and every binding this campaign set
        if getattr(scene, "to_menu", False):
            choice = None                              # the main menu: New game, Load and the rest are there; the server stays loaded
        else:
            return


def guarded(run, bridge):
    """Run the game and turn the known failures into readable messages (in the terminal or the window)."""
    try:
        run()
    except Cancelled:
        pass                                           # (f516) the game closing took its call back: nothing failed, nothing to say
    except LLMError as e:
        from engine import crashlog
        crashlog.record(e, "outside a turn: the model gave no usable answer")             # (f449) written down, so the logs sent carry it
        console.out("\nThe model couldn't produce a usable answer and the game can't continue from this point.")
        console.out("If you were already playing, what the world had settled before it stopped is saved, and is told when you come back.")
        console.out("If you were still creating your character, nothing was saved - run main.py to start creation again.")
        console.out(f"(details: {e} - see logs/llm_calls.jsonl and logs/crash.log)")
        if bridge:
            bridge.failed = True
    except KeyboardInterrupt:
        console.out("\nInterrupted. What the world had settled before it stopped is saved, and is told when you come back.")
    except SystemExit:
        raise
    except Exception as e:
        from engine import crashlog
        crashlog.record(e, "outside a turn")                   # (f449) a fault in a turn no longer reaches here (scenes/world.py turn); these are the rest
        if bridge:
            bridge.failed = True
        if bridge:
            import traceback
            console.out("\nSomething went wrong and the game has to stop. What the world had settled before it stopped is saved, and is told when you come back.")
            console.out("The details are written to logs/crash.log.")
            console.out(traceback.format_exc())
        else:
            raise
    finally:
        if paths.FROZEN and not bridge:
            input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
