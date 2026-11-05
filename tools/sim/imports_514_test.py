"""(f514) The import chain is cut: the game imports, and checks its data, with the model's client packages absent; importing starts
nothing; the client is built on its first call, never under the suite's switch; and the gateway reads a failed try's kind without
importing the client's packages.

Each part runs in its own Python process, so what one imports cannot hide what another would.

Run: python tools/sim/imports_514_test.py"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


def child(code: str, **env) -> tuple[int, str]:
    e = dict(os.environ, PYTHONPATH=str(ROOT))
    e.pop("MERAVIA_NO_SERVER", None)
    e.update(env)
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout + r.stderr).strip()


REFUSE = """
import sys
class Refuse:
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in ('ollama', 'httpx'):
            raise ImportError('refused: ' + name)
sys.meta_path.insert(0, Refuse())
"""

# ---- 1. the game imports, and passes its startup data check, with ollama and httpx refused
rc, out = child(REFUSE + """
import engine.budget, engine.recording, llm.embed, scenes.world, main
from engine import data_check
problems = data_check.check()
print('PROBLEMS', len(problems), problems[:3])
print('LOADED', 'ollama' in sys.modules, 'httpx' in sys.modules)
""")
check("with ollama and httpx refused, the budget, the recorder, the embedder, the scene and main all import", rc == 0, out[-600:])
check("...and the startup data check finds nothing (the chain through engine/data_check.py's scene import is cut)",
      "PROBLEMS 0 []" in out, out[-600:])
check("...and neither package was loaded", "LOADED False False" in out, out[-300:])

# ---- 2. importing starts nothing: no thread, no process
rc, out = child("""
import subprocess, threading
started = []
real_init = subprocess.Popen.__init__
def spy(self, *a, **k):
    started.append(a[0] if a else k.get('args'))
    return real_init(self, *a, **k)
subprocess.Popen.__init__ = spy
before = {t.ident for t in threading.enumerate()}
import engine.budget, engine.recording, llm.embed, scenes.world, main
after = [t.name for t in threading.enumerate() if t.ident not in before]
print('THREADS', after)
print('PROCS', started)
from llm import gateway
print('BUILT', gateway._client.built())
""")
check("importing the game starts no thread", rc == 0 and "THREADS []" in out, out[-600:])
check("...and no process", "PROCS []" in out, out[-600:])
check("...and builds no model client", "BUILT False" in out, out[-300:])

# ---- 3. under the suite's switch, nothing is ever built and a call fails as a missing server does
rc, out = child("""
import sys
from llm import gateway
c = gateway._client
print('HAS', hasattr(c, 'embed'), hasattr(c, 'chat'), hasattr(c, 'list'))
try:
    c.chat(model='m', messages=[])
    print('CALL returned')
except ConnectionError as e:
    print('CALL ConnectionError')
except Exception as e:
    print('CALL', type(e).__name__)
from pydantic import BaseModel
class Read(BaseModel):
    x: str
try:
    gateway.generate('work_offer_read', 'Read the offer.', 'Morning.', Read, retries=0)
    print('GEN returned')
except gateway.LLMError:
    print('GEN LLMError')
print('BUILT', c.built(), 'ollama' in sys.modules, 'httpx' in sys.modules)
""", MERAVIA_NO_SERVER="1")
check("under MERAVIA_NO_SERVER the client still answers hasattr for its methods (chat, embed, list) without building",
      "HAS True True True" in out, out[-600:])
check("...a call raises ConnectionError, what a missing server raises", "CALL ConnectionError" in out, out[-600:])
check("...a generate() with no stand-in gives up as an LLMError", "GEN LLMError" in out, out[-600:])
check("...and nothing was built or imported", "BUILT False False False" in out, out[-600:])

# ---- 4. without the switch the client is built on first use, with the server's extra fields kept
rc, out = child("""
from llm import gateway
c = gateway._client
print('BEFORE', c.built())
real = c.real()
import ollama
print('TYPE', type(real).__name__, isinstance(real, ollama.Client))
print('EXTRA', ollama.ChatResponse.model_config.get('extra'))
print('SAME', c.real() is real)
""")
check("without the switch the client is not built until it is used", "BEFORE False" in out, out[-600:])
check("...then it is the real client, built once", "TYPE Client True" in out and "SAME True" in out, out[-600:])
check("...and the server's extra fields (the cached-prompt count) are kept", "EXTRA allow" in out, out[-600:])

# ---- 5. a method wrapped in place (a test's or a recording script's stand-in; the recorder, the busy light and the night counter are
#      layers since f517) is called, and putting it back restores it
rc, out = child("""
from llm import gateway
c = gateway._client
saved = c.chat
c.chat = lambda **k: 'wrapped'
print('WRAPPED', c.chat(model='m'))
c.chat = saved
try:
    c.chat(model='m', messages=[])
except ConnectionError:
    print('RESTORED ConnectionError')
print('BUILT', c.built())
""", MERAVIA_NO_SERVER="1")
check("a method assigned over the lazy client is the one called", "WRAPPED wrapped" in out, out[-600:])
check("...and putting the saved one back restores the lazy call", "RESTORED ConnectionError" in out and "BUILT False" in out, out[-600:])

# ---- 6. a failed try's kind is read without the packages, and the same as before with them
rc, out = child("""
import sys
from llm import gateway
print('PLAIN', gateway._transport(ConnectionError('x')), gateway._transport(ValueError('x')))
import httpx, ollama
print('HTTPX', gateway._transport(httpx.ReadTimeout('slow')), gateway._transport(httpx.ConnectError('down')))
print('OLLAMA', gateway._transport(ollama.ResponseError('repeat limit', 500)))
""")
check("without the packages loaded: a ConnectionError is the server's failure, anything else the call's",
      "PLAIN (False, True) (False, False)" in out, out[-600:])
check("with them: an httpx timeout is a timed-out try, a connect error the server's", "HTTPX (True, True) (False, True)" in out, out[-600:])
check("...and Ollama's own error is the server's", "OLLAMA (False, True)" in out, out[-600:])

# ---- 7. one LLMError for every caller; the new kinds
rc, out = child("""
from llm import errors, gateway
from engine import budget
from core.interrupts import Interrupt
print('SAME', gateway.LLMError is errors.LLMError)
print('CANCEL', issubclass(errors.Cancelled, Interrupt), issubclass(errors.Cancelled, errors.LLMError))
f = errors.Failure('too_big', 'context exceeded', legacy=('ResponseError', 'x'))
print('FAILURE', f.kind, f.detail, f.legacy)
try:
    errors.Failure('nonsense')
    print('BADKIND accepted')
except ValueError:
    print('BADKIND refused')
""")
check("the gateway's LLMError is the one in llm/errors.py, so every except clause still catches it", "SAME True" in out, out[-600:])
check("a cancel is an Interrupt and not an LLMError (never a failed try)", "CANCEL True False" in out, out[-600:])
check("a failure carries its kind, detail and the old client's error", "FAILURE too_big context exceeded ('ResponseError', 'x')" in out, out[-600:])
check("...and an unknown kind is refused", "BADKIND refused" in out, out[-600:])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
