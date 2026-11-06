"""(f528) The game plays on its own llama-server: main.play under a fake runtime (tools/sim/fake_runtime.py: fake launchers serving a fake
llama-server that answers every contract with the stand-in model, by the title the grammar names).

- The default source is the game's own runtime: with nothing put in, every call is unreachable and says so, there is no embedder,
  nothing is started; under the suite's switch the default never reaches a live server. A stand-in's PASS goes to the source beneath it.
- main.play: the home page shows while the model loads; Continue waits behind the one loading line, then the game goes on; every request
  of the turn carries the whole sampler table, thinking off, the grammar (and no response_format), the model's GGUF id; quitting leaves
  no child, the lock let go, the default source back.
- A granted context below the settings' is refused in plain words: the could-not-wake page, no machinery in any line, Quit ends the start.
- (f532) A connection fault outside a turn is the generic page in the window and the error itself in the terminal: no old wording.

Run: python tools/sim/plays_on_llama_528_test.py"""

import os
import re
import shutil
import sys
import tempfile
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "sim"))

import config
from llm import backend, launch, llama, runtime, sampling
from llm.errors import Failure
from pydantic import BaseModel

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


class Read(BaseModel):
    x: str


def req():
    return backend.ChatRequest(messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], schema=Read,
                               sampling=sampling.resolve("stranger_read", 0.1).at(0), max_tokens=40)


def kind_of(fn):
    try:
        fn()
        return None
    except Failure as f:
        return f.kind, f.detail


# ---- the default source
check("the settings' default is the game's own runtime", config.BACKEND == "runtime")
check("under the suite's switch the default never reaches a live server", os.environ.get("MERAVIA_NO_SERVER") and backend.source().name == "no-server")
no_server_before = os.environ.pop("MERAVIA_NO_SERVER", None)
src = backend.source()
got = kind_of(lambda: src.chat(req()))
check("with nothing started, the default is unstarted: a call is unreachable and says so", src.name == "runtime" and got is not None
      and got[0] == "unreachable" and "not been started" in got[1], (src.name, got))
check("...there is no embedder, and the state says not started", backend.facts()["embedder"] is False and backend.state() == "not_started")
import simlib
one = simlib.stand_in(chat=lambda **k: types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content='{"x": "one"}')), name="one")
two = simlib.stand_in(chat=lambda **k: backend.PASS, name="two")
check("a stand-in's PASS goes to the source beneath it", backend.chat(req().messages, Read, req().sampling, 40).text == '{"x": "one"}'
      and backend.under(two.src) is one.src and backend.under(one.src) is src)
two()
one()

# ---- the fake runtime, and the game played on it
from fake_runtime import Layout, THE_3060
base = Path(tempfile.mkdtemp(prefix="plays528_"))
lay = Layout(base)
GO = base / "go"                                            # the chat server's load waits for this file: the home page is drawn first
lay.patch_paths(cuda=[THE_3060], FAKE_LOAD_SECONDS="1.0", FAKE_SEED="3", FAKE_LOAD_UNTIL=str(GO))
config.UPDATE_CHECK = False                                 # no release is looked for
NAME = "plays528"
game = simlib.campaign(NAME, "warrior", seed=3)             # a save with a character, for Continue
game.close()

import main as game_main
from scenes import home
from ui import console

said: list[str] = []
lines: list[str] = []
seen: list[float] = []
at_home: list[bool] = []
choices: list[tuple] = []
real = {k: getattr(console, k) for k in ("out", "note", "ask", "setup_progress")}
real_choose = home.choose


def choose(world):
    screen = launch.SCREEN.get("screen")
    at_home.append(screen is not None and not screen.ready())
    GO.write_text("")                                       # the player chose: now the load may finish
    return choices.pop(0) if choices else ("quit", "")


def quiet_console():
    console.out = lambda text="": said.append(str(text))
    console.note = lambda message, *a, **k: said.append(str(message))
    console.ask = lambda main=False, menu=False: lines.pop(0) if lines else "quit"
    console.setup_progress = lambda f, t: seen.append(f)
    home.choose = choose


def loud_console():
    for k, v in real.items():
        setattr(console, k, v)
    home.choose = real_choose


args = types.SimpleNamespace(new=False, debug=False, gui=False, terminal=False)
try:
    quiet_console()
    choices[:] = [("continue", NAME)]
    lines[:] = ["look", "quit"]
    t0 = time.monotonic()
    game_main.play(args)
    took = time.monotonic() - t0
    screen = launch.SCREEN.get("screen")
    child = screen.rt.chat.proc if screen is not None and screen.rt is not None and screen.rt.chat is not None else None
    loading = launch.line("loading")
    check("the home page shows while the model loads", at_home == [True], at_home)
    check("Continue waits behind the one loading line, then the game goes on", said.count(loading) == 1
          and any(s.startswith("Continuing as") for s in said) and said.index(loading) < next(i for i, s in enumerate(said) if s.startswith("Continuing as")),
          said[:6])
    check("the progress shows only while Continue waits, rising to ready", seen and seen == sorted(seen) and seen[-1] == 1.0, seen)
    bodies = lay.bodies()
    chats = [b for b in bodies if b.get("path") == "/v1/chat/completions"]
    check("the turn's requests reached the game's own server", len(chats) >= 2, len(chats))
    check("every request carries the whole sampler table, in one fixed order", chats and all(all(k in b for k in llama.SAMPLER_KEYS) for b in chats)
          and all([k for k in b if k in llama.SAMPLER_KEYS] == list(llama.SAMPLER_KEYS) for b in chats), [list(b) for b in chats[:1]])
    check("...thinking off, the grammar (headed by the title) and no response_format, the model's GGUF id",
          chats and all(b.get("chat_template_kwargs") == {"enable_thinking": False} and str(b.get("grammar", "")).startswith("# Meravia ")
                        and "response_format" not in b and b.get("model") == config.MODEL and "cache_prompt" in b for b in chats),
          {k: str(v)[:60] for k, v in chats[0].items() if k != "messages"} if chats else None)
    check("...each in the turn's slot or the background's, never another", chats and all(b.get("id_slot") in (0, 1) for b in chats),
          sorted({b.get("id_slot") for b in chats}))
    check("the embedder was started on the chat's card and asked too", any(a[0] == "cuda" and "--embeddings" in a for a in lay.argv())
          and any(b.get("path") == "/v1/embeddings" and b.get("input") for b in bodies), (len(lay.argv()), [b.get("path") for b in bodies][:6]))
    check("no line a player saw names the machinery", not any(re.search(r"\b(llama|server|slot|grammar|cuda|json)\b", s, re.I) for s in said), said)

    # the game closes as main() does
    launch.stop()
    runtime.stop_for_game()
    end = time.monotonic() + 10
    while child is not None and child.poll() is None and time.monotonic() < end:
        time.sleep(0.1)
    relock = runtime.GameLock(lay.run_dir)
    check("quitting leaves no child, the lock let go, the default source back", child is not None and child.poll() is not None and relock.acquire()
          and backend.source().name == "runtime" and not (lay.run_dir / "server.json").exists(), (child and child.poll(), backend.source().name))
    relock.release()
    launch.SCREEN.clear()

    # ---- a granted context below the settings' is refused in plain words
    said.clear(); seen.clear(); at_home.clear()
    os.environ["FAKE_GRANTED"] = "8192"
    os.environ["FAKE_LOAD_SECONDS"] = "0.2"
    os.environ.pop("FAKE_LOAD_UNTIL", None)
    lay.bodies_log.unlink(missing_ok=True)
    choices[:] = [("continue", NAME)]
    lines[:] = ["quit"]                                     # the could-not-wake page's choice
    game_main.play(args)
    could_not = launch.line("could_not_wake")
    from engine import failures
    check("a granted context below the settings' ends the start with the could-not-wake page, Quit chosen", could_not in said
          and not any(s.startswith("Continuing as") for s in said), said)
    check("...its choices offered as the owner's lines", any(launch.line("try_again") in s for s in said) and any(launch.line("quit") in s for s in said), said)
    check("...and no line carries the reason: it names the machinery", not any(failures.MACHINERY.search(s) for s in said), said)
    check("...no request reached the model", lay.bodies() == [])
    launch.stop()
    runtime.stop_for_game()
    relock = runtime.GameLock(lay.run_dir)
    check("the lock is let go after the refusal", relock.acquire())
    relock.release()
    launch.SCREEN.clear()
    os.environ.pop("FAKE_GRANTED", None)

    # ---- (f532) a connection fault outside a turn: no old server's wording
    said.clear()

    def dies():
        raise ConnectionError("Failed to connect")
    raised = None
    try:
        game_main.guarded(dies, None)
    except ConnectionError as e:
        raised = e
    bridge = types.SimpleNamespace(failed=False)
    game_main.guarded(dies, bridge)
    check("a connection fault outside a turn is raised to the terminal and the generic page to the window, never the old server's words",
          raised is not None and bridge.failed is True and not any("install" in s.lower() or "pull" in s.lower() for s in said)
          and any("Something went wrong" in s for s in said), said)
finally:
    loud_console()
    launch.stop()
    runtime.stop_for_game()
    lay.restore()
    if no_server_before is not None:
        os.environ["MERAVIA_NO_SERVER"] = no_server_before
    shutil.rmtree(ROOT / "saves" / NAME, ignore_errors=True)
    shutil.rmtree(base, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
