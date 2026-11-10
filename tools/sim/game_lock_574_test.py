"""(f574) "Is the game open?" (llm/runtime.py game_open) is asked by taking the game's lock and letting it go. Two tools that ask at
the same moment (three night runs started at once) could each find the lock held by the other's question and read it as an open game:
on GitHub's Windows runner the first night run stopped with "The game is open". A lock held only for a question is let go at once, so
the answer looks again for a moment before it says the game is open; a game that holds the lock is still open, however long it is asked."""
import sys, tempfile, threading, time
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 74))
from llm import runtime

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

run_dir = Path(tempfile.mkdtemp(prefix="gamelock_574_"))
check("with no game, the game is not open", runtime.game_open(run_dir) is False)

# ---- another tool's question holds the lock for a moment while this one asks
asker = runtime.GameLock(run_dir)
check("(the other question takes the lock)", asker.acquire())
threading.Timer(0.05, asker.release).start()
started = time.monotonic()
open_now = runtime.game_open(run_dir)
check("a question that holds the lock for a moment is not an open game", open_now is False, open_now)
check("...and the answer does not wait long", time.monotonic() - started < 2.0, time.monotonic() - started)

# ---- a game holds it
game = runtime.GameLock(run_dir)
check("(the game takes the lock)", game.acquire())
try:
    started = time.monotonic()
    check("a game that holds the lock is open", runtime.game_open(run_dir) is True)
    check("...said within a second", time.monotonic() - started < 1.0, time.monotonic() - started)
    check("...and a tool without --attach is refused", runtime.refuse_unless_attached(["tool.py"], run_dir) is not None)
finally:
    game.release()
check("once the game closes, it is not open", runtime.game_open(run_dir) is False)

# ---- many questions at once, as a night's runs start: none reads another's question as an open game
answers = []
def ask():
    answers.append(runtime.game_open(run_dir))
threads = [threading.Thread(target=ask) for _ in range(8)]
for t in threads:
    t.start()
for t in threads:
    t.join()
check("eight questions at once: every one says the game is not open", answers == [False] * 8, answers)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
