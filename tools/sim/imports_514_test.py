"""(f514, f532) The import chain is cut and the old model client is gone. Under a finder that refuses its packages (`ollama`, `httpx`):
the game imports and passes its startup data check; importing starts nothing (no thread, no process); under the suite's switch a call
fails at once as a missing server does (NoServer, a ConnectionError) and a generate() gives up as an LLMError, nothing imported; without
the switch the default is the game's own runtime, unstarted, and a call is unreachable; the kept recording replays whole. Then the fences:
no tracked file imports either package, and the old server's name is nowhere in the project but GOALS.md (the owner's decisions), the
kept recordings (data/replay), the suite's own absence checks (tools/sim/*_test.py), one comment in data/rules/sampling.yaml (in the
data hash, frozen until the bundle ends) and the model files' public source URLs in data/runtime/server.yaml (a content-addressed
registry, the digest the file's own checksum).

Each part runs in its own Python process, so what one imports cannot hide what another would.

Run: python tools/sim/imports_514_test.py"""

import ast
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
    for k in [k for k in e if k.startswith("DND_")]:
        e.pop(k)
    e.update(env)
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=900)
    return r.returncode, (r.stdout + r.stderr).strip()


OLD = ("ollama", "httpx")
REFUSE = """
import sys
class Refuse:
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in %r:
            raise ImportError('refused: ' + name)
sys.meta_path.insert(0, Refuse())
""" % (OLD,)

# ---- 1. the game imports, and passes its startup data check, with the old packages refused
rc, out = child(REFUSE + """
import engine.budget, engine.recording, llm.embed, llm.runtime, llm.launch, llm.llama, scenes.world, main
sys.path.insert(0, 'tools')
import runtime_cli
from engine import data_check
problems = data_check.check()
print('PROBLEMS', len(problems), problems[:3])
print('LOADED', [m for m in %r if m in sys.modules])
""" % (OLD,))
check("with the old packages refused, the budget, the recorder, the embedder, the runtime, the load screen, the adapter, the scene, main "
      "and the tools' helper all import", rc == 0, out[-600:])
check("...and the startup data check finds nothing", "PROBLEMS 0 []" in out, out[-600:])
check("...and neither package was loaded", "LOADED []" in out, out[-300:])

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
import engine.budget, engine.recording, llm.embed, llm.runtime, scenes.world, main
after = [t.name for t in threading.enumerate() if t.ident not in before]
print('THREADS', after)
print('PROCS', started)
""")
check("importing the game starts no thread", rc == 0 and "THREADS []" in out, out[-600:])
check("...and no process", "PROCS []" in out, out[-600:])

# ---- 3. under the suite's switch, a call fails as a missing server does, and nothing is imported or started
rc, out = child(REFUSE + """
import sys
from llm import backend, gateway
from llm.errors import NoServer
from llm.sampling import Sampling
from pydantic import BaseModel
class Read(BaseModel):
    x: str
print('SOURCE', backend.source().name)
from llm.errors import Failure
try:
    backend.chat([{'role': 'user', 'content': 'x'}], Read, Sampling(0.5), 50)
    print('CALL returned')
except Failure as e:
    print('CALL', e.kind, isinstance(e.__cause__, NoServer), isinstance(e.__cause__, ConnectionError))
except Exception as e:
    print('CALL', type(e).__name__)
try:
    gateway.generate('work_offer_read', 'Read the offer.', 'Morning.', Read, retries=0)
    print('GEN returned')
except gateway.LLMError as e:
    print('GEN LLMError', e.failure)
print('EMBEDDER', backend.facts()['embedder'], 'STATE', backend.state())
print('LOADED', [m for m in %r if m in sys.modules])
""" % (OLD,), MERAVIA_NO_SERVER="1")
check("under MERAVIA_NO_SERVER the default is the no-server source", "SOURCE no-server" in out, out[-600:])
check("...a call fails as unreachable, its cause the NoServer (a ConnectionError) a missing server raises", "CALL unreachable True True" in out, out[-600:])
check("...a generate() with no stand-in gives up as an LLMError, the model unreachable", "GEN LLMError unreachable" in out, out[-600:])
check("...it has no embedder and is not started", "EMBEDDER False STATE not_started" in out, out[-600:])
check("...and nothing was imported", "LOADED []" in out, out[-600:])

# ---- 4. without the switch the default is the game's own runtime, unstarted
rc, out = child(REFUSE + """
import sys, config
from llm import backend
from llm.errors import Failure
from llm.sampling import Sampling
from pydantic import BaseModel
class Read(BaseModel):
    x: str
print('BACKEND', config.BACKEND, 'SOURCE', backend.source().name)
try:
    backend.chat([{'role': 'user', 'content': 'x'}], Read, Sampling(0.5), 50)
    print('CALL returned')
except Failure as e:
    print('CALL', e.kind, 'not been started' in (e.detail or ''))
print('LOADED', [m for m in %r if m in sys.modules])
""" % (OLD,))
check("without the switch the default is the game's own runtime, unstarted: a call is unreachable and says so",
      "BACKEND runtime SOURCE runtime" in out and "CALL unreachable True" in out, out[-600:])
check("...and nothing was imported", "LOADED []" in out, out[-600:])

# ---- 5. the kept recording replays whole under the finder
rc, out = child(REFUSE + """
import sys
sys.path.insert(0, 'tools')
import rerun
out = rerun.replay(rerun.golden('stub_short'))
print('REPLAY', out['matched'], out['of'], out['parted'], [m for m in %r if m in sys.modules])
""" % (OLD,))
check("the kept recording replays whole with the old packages refused, importing neither", rc == 0 and "REPLAY 41 41 None []" in out, out[-800:])

# ---- 6. the fences: no tracked file imports either package; the old server's name is gone from the project
tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
tracked += subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
# (f532's review) a file not yet added is read too: the fence holds before the commit, not after it
imports = []
for rel in tracked:
    if not rel.endswith(".py"):
        continue
    try:
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        continue
    for n in ast.walk(tree):
        if isinstance(n, ast.Import) and any(a.name.split(".")[0] in OLD for a in n.names):
            imports.append(f"{rel}:{n.lineno}")
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] in OLD:
            imports.append(f"{rel}:{n.lineno}")
check("no tracked file imports the old client's packages", imports == [], imports[:10])
EXEMPT = {"GOALS.md"}
named = []
for rel in tracked:
    if not rel or rel in EXEMPT or rel.startswith("data/replay/") or (rel.startswith("tools/sim/") and rel.endswith("_test.py")):
        continue
    if rel.startswith("docs/research/"):
        continue                                            # (f606) research cites other projects' servers; it is no dependency
    try:
        text = (ROOT / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    for i, line in enumerate(text.splitlines(), 1):
        if "ollama" not in line.lower():
            continue
        if rel == "data/runtime/server.yaml" and "registry.ollama.ai" in line:
            continue                                        # the model files' public, content-addressed source
        if rel == "data/rules/sampling.yaml" and line.lstrip().startswith("#"):
            continue                                        # in the data hash, frozen until the bundle ends (f527)
        named.append(f"{rel}:{i}")
check("the old server is named nowhere in the project (but the owner's decisions, the kept recordings, the suite's own absence checks, the "
      "frozen sampling comment and the model files' source URLs)", named == [], named[:12])
check("requirements.txt lists neither package", not any(l.split(">=")[0].split("==")[0].strip() in OLD for l in (ROOT / "requirements.txt").read_text().splitlines()))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
