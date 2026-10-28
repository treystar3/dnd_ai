"""(f364) The line the game draws around what the model writes, and the record a store asks for: the content guard at the gateway (a hit is a
rejection sent back; every try failing leaves the written fallback; a row in the refusals log), the #report command that saves what the
player saw with the calls behind it, the credits shown in the game and on the home page, creature names that are nobody's trademark, and a
switch that turns the release check off for a build whose updates come another way."""
import json, random, shutil, sys, types
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 1); simlib.install(stub)
import config
from engine import guard, refusals
from llm import gateway
from llm.contracts import NPCReply, Narration
from llm.gateway import LLMError
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the guard on its own
check("the categories are data, each with words and a reason", guard.problems() == [] and {"sexual", "slurs", "self_harm", "hate"} <= set(guard.PATTERNS), guard.problems())
check("the game's own matter passes: a fight, blood, a theft, a death", guard.check(["She drives the knife in to the hilt and he dies in the mud, bleeding."]) == ("", "")
      and guard.check(["The thief slips the purse from his belt and is gone."]) == ("", ""))
check("sexual content is caught, as a whole word", guard.check(["They go off to fuck in the hayloft."])[0] == "sexual" and guard.check(["The Sussex road is long."]) == ("", ""))
check("a slur is caught", guard.check(["Nobody serves a kike here."])[0] == "slurs")
check("instruction in harming oneself is caught", guard.check(["Why not kill yourself and be done?"])[0] == "self_harm")
check("the real world's hatreds are caught", guard.check(["He raises his arm: heil Hitler."])[0] == "hate")
check("a long stem matches its forms, a short word only itself", guard.check(["masturbating"])[0] == "sexual" and guard.check(["sexton", "cockerel", "dickens"]) == ("", ""))
check("the tasks that only read the player's own words are not judged", not guard.guarded("interpret_action") and guard.guarded("npc_conversation") and guard.guarded("narrate"))
foul_memory = NPCReply(speech="Aye.", intent="small_talk", remember="he asked about fucking")
check("every string in an answer is read, a memory as much as the speech", any(s.startswith("he asked") for s in guard.strings_of(foul_memory))
      and guard.check(guard.strings_of(foul_memory))[0] == "sexual")

# ---- at the gateway
class Foul:
    def __init__(self): self.calls = 0
    def chat(self, **k):
        self.calls += 1
        return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=json.dumps({"speech": "Come to bed with me, stranger, and fuck.", "intent": "small_talk"})))
_client = gateway._client
gateway._client = foul = Foul()
refusals.SESSION.clear()
try:
    gateway.generate("npc_conversation", "sys", "req", NPCReply, retries=1, _quiet=True)
    got = None
except LLMError as e:
    got = e
gateway._client = _client
check("an answer outside the line is sent back on every try and the caller is left to its written fallback", isinstance(got, LLMError) and foul.calls == 2, (got, foul.calls))
check("...and each hit is a row in the refusals log, naming the category", any(r["kind"] == "guarded" and r["why"].startswith("sexual:") for r in refusals.SESSION), refusals.SESSION[-2:])
clean = gateway.generate("narrate", "sys", "req", Narration, retries=0, _quiet=True)
check("a clean answer passes as before", bool(clean.text))

# ---- #report, #credits, the home page
from npc.traits import load_traits
from scenes import home
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import load_world
shutil.rmtree("saves/guard_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("guard_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
notes, outs = [], []
console.note = lambda t, *a, **k: notes.append(t); console.narrate = lambda t: None; console.out = lambda t, *a, **k: outs.append(t)
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.player.mentor["never"] = True
ws.enter("parth")
ws.remember_narration("A passage the player did not like.")
config.REPORTS_PATH = "saves/guard_test/reports"
config.LOG_PATH = "saves/guard_test/llm_calls.jsonl"
Path(config.LOG_PATH).write_text(json.dumps({"turn": ws.store.meta.turn, "task": "narrate", "attempt": 0, "error": None, "raw": '{"text": "A passage the player did not like."}'}) + "\n", encoding="utf-8")
ws.command("#report that passage was out of place")
files = sorted(Path(config.REPORTS_PATH).glob("*.json"))
rep = json.loads(files[-1].read_text(encoding="utf-8")) if files else {}
check("#report saves what was just read, the note and the calls behind it, and sends nothing anywhere",
      len(files) == 1 and rep.get("note") == "that passage was out of place" and rep.get("shown") == ["A passage the player did not like."] and rep.get("calls")
      and rep["calls"][0]["task"] == "narrate" and any("Nothing is sent anywhere" in n for n in notes), (rep, notes[-1:]))
check("...and is a row in the refusals log", any(r["kind"] == "reported" for r in refusals.SESSION))
ws.command("#credits")
check("#credits shows who made what the game is built from", outs and "System Reference Document" in outs[-1] and "Literata" in outs[-1], outs[-1][:100] if outs else outs)
page = home.page(world)
check("the home page carries the credits, and the window has a place to show them", "System Reference Document" in page.get("credits", "")
      and 'id="homecredits"' in Path("ui/gui/web/index.html").read_text(encoding="utf-8") and 'homeGo("credits")' in Path("ui/gui/web/app.js").read_text(encoding="utf-8"))
check("the built game carries the credits file", 'CREDITS.md' in Path("build_exe.bat").read_text(encoding="utf-8"))
check("#help names both", "#report" in Path("ui/console.py").read_text(encoding="utf-8") and "#credits" in Path("ui/console.py").read_text(encoding="utf-8"))

# ---- names and the update switch
names = " ".join(c.name.lower() for c in world.bestiary.values())
check("no creature carries a name that is a trademark outside the SRD", "mind flayer" not in names and "mindrender" in names
      and all(c.family != "mind_flayer" for c in world.bestiary.values()))
check("a store build can turn the release check off", getattr(config, "UPDATE_CHECK", None) is True and 'getattr(config, "UPDATE_CHECK", True)' in Path("main.py").read_text(encoding="utf-8"))

shutil.rmtree("saves/guard_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
