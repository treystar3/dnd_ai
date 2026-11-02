"""(f449) An exception the game must let through. Since f449 a turn survives any error: a model call that fails in any way is one failed
try (llm/gateway.py), and any exception a turn raises rolls the turn back, is told to the player in the narrator's words and is written
to logs/crash.log (scenes/world.py turn, engine/crashlog.py). Some exceptions are not faults but intent: the replay has parted from its
recording (tools/rerun.py Parted), a harness wants the game to stop here. Those subclass Interrupt, and every one of the catches above
re-raises it untouched. (The window closing is a SystemExit, ui/gui/bridge.py Closed, which no `except Exception` catches.)"""


class Interrupt(Exception):
    """Raised on purpose to stop what the game is doing; never swallowed as a failed try or a rolled-back turn."""
