"""The audit log (f314): every attempt of every model call is written, readable, under the turn it served; a rejected answer shows why;
the system prompt is written once in full and then by reference; typed prompts show their parts.
(f778) The audit log has one switch, config.AUDIT_LOG: audit_log.yaml holds none, a table planted with one decides nothing, and nothing
falls back to the table when config is asked. A source rule holds the kind in the forms it reads: a read of config (by whatever name the
file imports it) that falls back to a data table through a getattr default, an except that would catch config failing (bare, Exception,
AttributeError, ImportError, NameError), an `or` after a value of config's, or an if on whether config has the name; a table is a
loader's answer, a name bound to one, or one imported or read off another module, grown to a fixpoint. It reads every .py
git lists, tracked or not, outside docs/, .claude/, data/ and tools/sim/. The refusals log, whose switch has one home already, passes it
and obeys its switch as before."""
import sys, json, shutil, tempfile
sys.path.insert(0, ".")
import simlib
from pathlib import Path
import config
from llm import audit, gateway
from engine.prompt import Prompt
from pydantic import BaseModel, field_validator

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# a session file of our own, in a scratch folder (f778: outside the project's logs/)
SCRATCH = Path(tempfile.mkdtemp(prefix="audit_log_")).resolve()
audit.A["folder"] = str(SCRATCH / "audit_test")
for key, fn in (("LOG_PATH", "llm_calls.jsonl"), ("TURN_LOG_PATH", "turns.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl"), ("CRASH_LOG_PATH", "crash.log")):
    setattr(config, key, str(SCRATCH / "logs" / fn))               # (f778) the call log and the rest, here and not in the project's logs/
audit._path = None; audit._count = 0; audit._system_seen.clear(); audit._first_attempt.clear(); audit._full = False
config.AUDIT_LOG = True


class Reply(BaseModel):
    speech: str

    def spoken(self):
        return [("", self.speech)]

    @field_validator("speech")
    @classmethod
    def no_dragons(cls, v):
        if "dragon" in v:
            raise ValueError("no dragons here")
        return v


class FakeResponse:
    def __init__(self, text):
        self.message = type("M", (), {"content": text})()
        self.done_reason = "stop"


answers = iter(['{"speech": "a dragon lands"}', '{"speech": "a cart rolls by"}', '{"speech": "fine weather"}'])


class FakeClient:
    def chat(self, **kw):
        return FakeResponse(next(answers))


fake = simlib.stand_in(chat=FakeClient().chat, embed=None, name="audit_fake")     # (f518) the canned answers, as a source
audit.note_turn(7, "I look around")
p = Prompt().instruction("be brief", "HOW TO SPEAK").fact("it is raining", "WEATHER")
r = gateway.generate("narrate", "You are the narrator.", p, Reply, retries=2)
check("the call came back once the answer was acceptable", r.speech == "a cart rolls by")
audit.note_turn(8, "I ask the baker the way")
gateway.generate("narrate", "You are the narrator.", "plain user text", Reply, retries=0)

# (f315) the gateway sends back a line that names someone the speaker was not told of, with the complaint, and takes the redraft
answers = iter(['{"speech": "Go and see Oswin Lovell, he will sort you out."}', '{"speech": "Go and see Fenella Reeve at the desk."}'])
audit.note_turn(9, "who should i see?")
q = Prompt().fact("Fenella Reeve: the guild clerk, at her desk", "WHO IS HERE")
r = gateway.generate("npc_conversation", "You are a townsperson.", q, Reply, retries=1, validation_context={"known": {"maren", "holt"}})
check("a line naming someone the speaker was not told of is sent back, and the redraft taken", r.speech.startswith("Go and see Fenella"), r.speech)

text = Path(audit.path()).read_text(encoding="utf-8")
check("...and the log shows why", "'Oswin Lovell' is no one and nowhere you were told of" in text)
check("the file names the turn and what the player typed", '# Turn 7: "I look around"' in text and '# Turn 8: "I ask the baker the way"' in text)
check("why the call was made is in plain words", "the narrator describing what just happened" in text)
check("the rejected attempt is recorded with its reason", "attempt 1" in text and "rejected - speech: no dragons here" in text)
check("...and the accepted one after it", "attempt 2" in text and "**Verdict:** accepted" in text)
check("the system prompt is written in full once, then by reference", text.count("You are the narrator.") == 1 and "unchanged since #1" in text)
check("a typed prompt shows its parts", "[instruction · HOW TO SPEAK]" in text and "[fact · WEATHER]" in text)
check("the complaint sent back is shown", "Sent back with:" in text and "no dragons here" in text)
check("a retry does not repeat the prompt in full", "the same as #1" in text and text.count("[fact · WEATHER]") == 1)
check("answers are shown as formatted JSON", '"speech": "a cart rolls by"' in text)
check("#audit can say where it is", "calls recorded" in audit.summary())
check("every attempt was answered by the test's own stand-in", fake.live() and fake.src.calls["Reply"] == 5, dict(fake.src.calls))

# ---- (f778) one switch: config.AUDIT_LOG alone decides whether a call is written
import ast, subprocess, yaml
table = yaml.safe_load(Path("data/rules/audit_log.yaml").read_text(encoding="utf-8"))
check("(f778) audit_log.yaml holds no switch of its own: the audit log's one is config.AUDIT_LOG", "enabled" not in table, sorted(table))


def written(on: bool, planted: bool) -> int:
    """How many calls the audit writes for one call made, with config.AUDIT_LOG at `on` and `enabled: planted` put in the loaded table."""
    global answers
    answers = iter(['{"speech": "a gull calls over the harbour"}'])
    held_table, held_switch = dict(audit.A), config.AUDIT_LOG
    audit.A["enabled"], config.AUDIT_LOG = planted, on
    try:
        before = audit._count
        gateway.generate("narrate", "You are the narrator.", "plain user text", Reply, retries=0)
        return audit._count - before
    finally:
        audit.A.clear()
        audit.A.update(held_table)
        config.AUDIT_LOG = held_switch


check("...a call is written with config.AUDIT_LOG on, though the table says enabled: false (a table decides nothing)",
      written(True, False) == 1)
check("...and none with it off, though the table says enabled: true", written(False, True) == 0)
held_switch = config.AUDIT_LOG
del config.AUDIT_LOG
try:
    try:
        fell_back = audit.enabled()
    except AttributeError as e:
        fell_back = e
finally:
    config.AUDIT_LOG = held_switch
check("...and no read falls back to the table: with config.AUDIT_LOG gone, enabled() answers nothing from audit_log.yaml",
      isinstance(fell_back, AttributeError), fell_back)
fake()

LOADERS = {"safe_load", "load", "loads", "_load", "read_text"}       # what reads a data file into a table


def is_loader(c) -> bool:
    return isinstance(c, ast.Call) and ((isinstance(c.func, ast.Name) and c.func.id in LOADERS)
                                        or (isinstance(c.func, ast.Attribute) and c.func.attr in LOADERS))


def dotted(node) -> str | None:
    """a.b.c as the text "a.b.c"; None for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = dotted(node.value)
        return None if head is None else f"{head}.{node.attr}"
    return None


class Source:
    """One module read for the rule: the names it gives config (its own `import config [as X]`), the modules and names it imports,
    and the names bound to a data table, grown to a fixpoint (a loader's answer, a name bound to one, a table imported from another
    module or read off it as module.NAME). `index` holds each module's tables, by its dotted name."""

    def __init__(self, text, index: dict):
        self.t = text if isinstance(text, ast.AST) else ast.parse(text)
        self.config, self.mods, self.names = set(), {}, {}
        for n in ast.walk(self.t):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name == "config":
                        self.config.add(a.asname or "config")
                    elif a.asname:
                        self.mods[a.asname] = a.name
                    else:
                        self.mods[a.name.split(".")[0]] = a.name.split(".")[0]
            elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
                for a in n.names:
                    full = f"{n.module}.{a.name}"
                    if full in index:
                        self.mods[a.asname or a.name] = full
                    else:
                        self.names[a.asname or a.name] = (n.module, a.name)
        self.index, self.tables = index, set()
        for _ in range(8):
            grew = {tg.id for n in ast.walk(self.t) if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None
                    and self.reads_table(n.value) for tg in (n.targets if isinstance(n, ast.Assign) else [n.target]) if isinstance(tg, ast.Name)}
            if grew <= self.tables:
                break
            self.tables |= grew

    def reads_table(self, node) -> bool:
        for x in ast.walk(node):
            if is_loader(x) or (isinstance(x, ast.Name) and x.id in self.tables):
                return True
            if isinstance(x, ast.Name) and x.id in self.names and self.names[x.id][1] in self.index.get(self.names[x.id][0], ()):
                return True
            d = dotted(x) if isinstance(x, ast.Attribute) else None
            if d and d.split(".")[0] in self.mods:
                module, _, name = (self.mods[d.split(".")[0]] + d[len(d.split(".")[0]):]).rpartition(".")
                if name in self.index.get(module, ()):
                    return True
        return False

    def is_config_value(self, node) -> bool:
        """node is itself a value read off config: config.NAME, or getattr(config, NAME[, default])."""
        return ((isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in self.config)
                or (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr" and node.args
                    and isinstance(node.args[0], ast.Name) and node.args[0].id in self.config))

    def reads_config(self, node) -> bool:
        return any((isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id in self.config)
                   or (isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id in ("getattr", "hasattr") and x.args
                       and isinstance(x.args[0], ast.Name) and x.args[0].id in self.config) for x in ast.walk(node))

    def asks_whether_set(self, test) -> bool:
        """A test of whether config has the name: hasattr(config, ...), or a read of config compared with None."""
        return any((isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "hasattr" and x.args
                    and isinstance(x.args[0], ast.Name) and x.args[0].id in self.config)
                   or (isinstance(x, ast.Compare) and any(isinstance(c, ast.Constant) and c.value is None for c in x.comparators)
                       and self.reads_config(x.left)) for x in ast.walk(test))

    def second_homes(self) -> list[tuple[int, str]]:
        """Each place a read of config falls back to a data table, with its form: a getattr default, an except, an `or`, an if."""
        out = []
        for n in ast.walk(self.t):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) == 3
                    and isinstance(n.args[0], ast.Name) and n.args[0].id in self.config and self.reads_table(n.args[2])):
                out.append((n.lineno, "a getattr default"))
            elif (isinstance(n, ast.Try) and any(self.reads_config(s) for s in n.body)
                  and any(self.reads_table(s) for h in n.handlers if catches_config(h) for s in h.body)):
                out.append((n.lineno, "an except"))
            elif (isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or) and self.is_config_value(n.values[0])
                  and any(self.reads_table(v) for v in n.values[1:])):
                out.append((n.lineno, "an or"))
            elif (isinstance(n, (ast.IfExp, ast.If)) and self.asks_whether_set(n.test)
                  and any(self.reads_table(s) for part in (n.body, n.orelse) for s in (part if isinstance(part, list) else [part]))):
                out.append((n.lineno, "an if"))
        return out


CONFIG_FAULTS = {"Exception", "BaseException", "AttributeError", "ImportError", "ModuleNotFoundError", "NameError"}


def catches_config(h) -> bool:
    """A handler that would catch config failing to answer (a name or the module missing): bare, or one of CONFIG_FAULTS. One for a
    model's failure (LLMError) is no fallback of config's."""
    kinds = [] if h.type is None else (h.type.elts if isinstance(h.type, ast.Tuple) else [h.type])
    return h.type is None or any((dotted(k) or "").rsplit(".", 1)[-1] in CONFIG_FAULTS for k in kinds)


def module_name(rel: str) -> str:
    return rel[:-3].replace("/", ".").removesuffix(".__init__")


files = [f for f in subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True,
                                   text=True, encoding="utf-8").stdout.split()
         if not f.startswith(("docs/", ".claude/", "data/", "tools/sim/")) and Path(f).is_file()]
trees = {f: ast.parse(Path(f).read_text(encoding="utf-8")) for f in files}
index: dict = {module_name(f): set() for f in files}
for _ in range(4):                                                   # a table read off another module's table: grown across modules
    before = {k: set(v) for k, v in index.items()}
    for f, tree in trees.items():
        index[module_name(f)] = Source(tree, index).tables
    if index == before:
        break


def homes(text: str) -> list:
    return Source(text, index).second_homes()


LOADED = "import config\nfrom core import yamlio\nA = yamlio.safe_load(open('data/rules/x.yaml').read())\n"
planted = {
    LOADED + "def on():\n    return getattr(config, 'X_LOG', A.get('enabled', True))\n": True,
    "import config\nT = _load('data/rules/x.yaml')\nN = getattr(config, 'X_KEEP', T['keep'])\n": True,
    "import config, yaml\nN = getattr(config, 'X_KEEP', yaml.safe_load(open('data/rules/x.yaml'))['keep'])\n": True,
    LOADED + "def enabled():\n    try:\n        return bool(config.X_LOG)\n    except Exception:\n        return bool(A.get('enabled', True))\n": True,
    LOADED + "N = getattr(config, 'X_KEEP', None) or A['keep']\n": True,
    LOADED + "N = config.X_KEEP if hasattr(config, 'X_KEEP') else A['keep']\n": True,
    LOADED + "if getattr(config, 'X_KEEP', None) is None:\n    N = A['keep']\nelse:\n    N = config.X_KEEP\n": True,
    LOADED + "if not hasattr(config, 'X_KEEP'):\n    N = 1\nelse:\n    N = 2\nif hasattr(config, 'X_KEEP'):\n    M = config.X_KEEP\nelse:\n    M = A['keep']\n": True,
    LOADED + "H = A['tasks']\nT = H['narrate']\nN = getattr(config, 'X_KEEP', T['k'])\n": True,
    "import config\nfrom engine.combat import RULES\nN = getattr(config, 'X_KEEP', RULES['k'])\n": True,
    "import config\nfrom engine import combat\nN = getattr(config, 'X_KEEP', combat.RULES['k'])\n": True,
    "import config\nimport engine.combat\nN = getattr(config, 'X_KEEP', engine.combat.RULES['k'])\n": True,
    "import config as settings\nfrom core import yamlio\nA = yamlio.safe_load(open('x.yaml').read())\nN = getattr(settings, 'X', A['k'])\n": True,
    "import yaml\ncfg = yaml.safe_load(open('x.yaml'))\nT = yaml.safe_load(open('y.yaml'))\nN = cfg.get('a') if isinstance(cfg.get('a'), dict) else T\n"
    "M = getattr(cfg, 'X', T['k'])\n": False,
    "import config\nKEEP = 5\nN = getattr(config, 'X_KEEP', KEEP)\nM = getattr(config, 'X_ON', True)\nP = getattr(config, 'X_PATH', 'logs/x.log')\n"
    "Q = config.X_KEEP or 5\nR = config.X_KEEP if hasattr(config, 'X_KEEP') else 3\ntry:\n    S = config.X_KEEP\nexcept AttributeError:\n    S = 3\n": False,
    LOADED + "def tell(n):\n    try:\n        return ask(n, max_tokens=config.X_MAX)\n    except LLMError:\n        return A['fallback_line']\n"
    "def long(n):\n    return n >= config.X_MAX or 'narrate' in A['tasks']\n": False,
}
caught = {src: bool(homes(src)) == want for src, want in planted.items()}
check("the source rule catches each form of a config read that falls back to a data table, planted (a getattr default, an except"
      " that would catch config failing, an or after a value of config's, an if on whether config has the name; a table's name, one"
      " derived from it, one imported or read off its module; config by another name), and passes a plain fallback, a dict that is"
      " not config, a model's failure caught and a comparison", all(caught.values()), [s for s, ok in caught.items() if not ok])
AS_IT_WAS = ("from pathlib import Path\nfrom core import yamlio\nROOT = Path(__file__).resolve().parent.parent\n"      # llm/audit.py before f778
             "A = yamlio.safe_load((ROOT / 'data' / 'rules' / 'audit_log.yaml').read_text(encoding='utf-8'))\n\n\n"
             "def enabled() -> bool:\n    try:\n        import config\n        return bool(getattr(config, 'AUDIT_LOG', A.get('enabled', True)))\n"
             "    except Exception:\n        return bool(A.get('enabled', True))\n")
check("...and finds both of the finding's own fallbacks in the audit log as it was, the getattr default and the except",
      sorted(w for _, w in homes(AS_IT_WAS)) == ["a getattr default", "an except"], homes(AS_IT_WAS))
second_home = [f"{f}:{line} ({how})" for f in files for line, how in homes(trees[f])]
check("in the files the rule reads (every .py git lists, tracked or not, outside docs/, .claude/, data/ and tools/sim/), no read of"
      " config falls back to a data table by these forms: each setting has one home", not second_home and len(files) > 200, second_home)
check("the refusals log, whose switch has one home already, passes the rule", not homes(trees["engine/refusals.py"]))
from engine import refusals
held = {k: getattr(config, k) for k in ("REFUSALS_LOG", "REFUSALS_LOG_PATH")}
config.REFUSALS_LOG_PATH = str(SCRATCH / "refusals.jsonl")
try:
    config.REFUSALS_LOG = False
    refusals.note("refused", "f778 probe, off", "the switch is off")
    off = refusals.path().is_file()
    config.REFUSALS_LOG = True
    refusals.note("refused", "f778 probe, on", "the switch is on")
    on_rows = refusals.path().read_text(encoding="utf-8").splitlines() if refusals.path().is_file() else []
finally:
    for k, v in held.items():
        setattr(config, k, v)
    del refusals.SESSION[-2:]
check("...and obeys it as before: nothing written with config.REFUSALS_LOG off, its row with it on",
      not off and len(on_rows) == 1 and "f778 probe, on" in on_rows[0], (off, on_rows))

shutil.rmtree(SCRATCH, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
