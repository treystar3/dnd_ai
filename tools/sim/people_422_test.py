"""(f422) People and captives, as the f395 night's readers met them. Two captives, or a captive and a townsman, shared a name; '(bounty)' was
said as part of one; the dead and departed could still be here; 'Albert bain' and 'Gen webb' (str.capitalize); a she was told 'they have its
way of talking'; temperaments ran together with 'and'; one board had two hires with the same blurb; 'Thanks, Odly' was answered as a
question asked before, and the asked-again line told them 'they are still true'; 'None.' was printed under a name; a frame retold the
words it framed; a question asked 'end the current quest'; the errand's '[X is asking something of you. Say yes, or no.]'; 'ask the clerk
after a name. Corwin.'; and 'hand them to the watch' for one man."""
import pathlib, random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 12))
import ui.console as uc
SHOWN = []
uc.narrate = lambda t, *a, **k: SHOWN.append(("narrate", str(t)))
uc.npc_says = lambda speaker, speech, gesture="", *a, **k: SHOWN.append(("says", f"{speaker}: {speech}"))
for fn in ("say", "note", "ledger", "dialogue"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import combat, convo, entities, names, party, quirks, voice_profile
from llm.contracts import Clarify, DialogueFrame, NPCReply
from npc.traits import load_traits
from scenes.world import WorldScene
from storage import invariants
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- names and capitals
check("a first-letter capital leaves the rest as written", names.cap_first("albert Bain of Riverhaven") == "Albert Bain of Riverhaven")
f = combat.Fighter.model_construct(name="bandit captain (bounty)", side="enemy", boss=False)
check("a tag such as '(bounty)' is not said as part of a foe", combat.who(f) == "the bandit captain", combat.who(f))
PAT = re.compile(r"(?:label\(\)|\.name|\['name'\]|\[\"name\"\]|display_name\([^)]*\))\.capitalize\(\)")
hits = [f"{p}:{i + 1}" for p in list(pathlib.Path("scenes").glob("*.py")) + list(pathlib.Path("engine").glob("*.py"))
        for i, l in enumerate(p.read_text(encoding="utf-8").split("\n")) if PAT.search(l)]
check("no name or label goes through str.capitalize()", not hits, hits)
src = pathlib.Path("scenes/combat_scene.py").read_text(encoding="utf-8")
check("a captive's name is drawn apart from every name already in the save", "store.npc_names()" in src and "taken.add(" in src)

# ---- the scene
shutil.rmtree("saves/people_422_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("people_422_test")
store.meta.seed = 12; store.meta.turn = 1; store.meta.minutes = 720; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(12))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("tilted_plough")
someone = next(iter(ws.residents), None)
if someone is not None:
    someone.gone = "died"
    ws.refresh_present()
check("the dead and departed are not among who is here", someone is not None and all(n.id != someone.id for n in ws.present))
if someone is not None:
    someone.gone = ""
    ws.refresh_present()

# ---- in their own pronoun
npc = next((n for n in ws.present if not (n.speech or {}).get("own_voice")), None)
if npc is not None:
    from npc.life import ensure_speech
    ensure_speech(npc, store, world)
    npc.gender = "female"
    lines = [l for k in range(12) for l in voice_profile.resident_lines(npc, random.Random(k))[1]]
    theys = [l for l in lines if re.search(r"\b(they|them|their|themselves)\b", l, re.I)]
    check("what a townswoman is told about how she talks is said of her as she", lines and not theys, theys[:3])
else:
    check("what a townswoman is told about how she talks is said of her as she (someone to try)", False)
for kind in ("voices.yaml", "speech.yaml"):
    text = pathlib.Path("data/rules", kind).read_text(encoding="utf-8")
    check(f"{kind}: the listener is named, so gendering the speaker cannot rewrite them",
          "what they want is their own business" not in text and "calls them lad" not in text and "asks for their opinion" not in text)
from scenes.party_actions import P as PARTY
check("temperaments are each their own clause", ws.temper_text({"temper": ["blunt", "wary"]})
      == PARTY["temperaments"]["blunt"]["say"] + "; " + PARTY["temperaments"]["wary"]["say"])
board = party.roster(12, "guild_house", 3, 5, 100, [])
per = {}
for m in board:
    per.setdefault(m["role"], []).append(m["blurb"])
check("no two hires on one board share a blurb", all(len(b) == len(set(b)) for b in per.values()), per)

# ---- asked before: questions only
holder = {}
convo.record(holder, "Thanks, Odly", "Any time.", 1)
convo.record(holder, "Where were you born?", "In the hills.", 2)
check("only a question is kept to be asked again", [e["asked"] for e in holder["convo"]] == ["Where were you born?"], holder)
check("...and a line that asks nothing is never 'asked before'", convo.find(holder, "Thanks, Odly") is None
      and convo.find(holder, "where were you born?") is not None)
check("the asked-again line no longer says 'they are still true'", "still true" not in convo.again_rule("plainly"))
check("no companion is told they may be harsh or cutting", not re.search(r"\b(harsh|cutting)\b", " ".join(quirks.Q["repeat_manner"].values())))

# ---- what is said, and its frame
for speech in ("None.", "", "...", "n/a"):
    try:
        NPCReply.model_validate({"speech": speech, "intent": "small_talk"})
        check(f"a reply of {speech!r} is sent back", False)
    except Exception:
        check(f"a reply of {speech!r} is sent back", True)
check("...unless what they do is the answer", NPCReply.model_validate({"speech": "", "gesture": "shrugs", "intent": "small_talk"}).gesture == "shrugs")
SHOWN.clear()
if npc is not None:
    ws.show_speech(npc.label(), types.SimpleNamespace(speech="", gesture="shrugs and turns back to the bar"), npc)
check("...and no name is printed over an empty line", SHOWN and SHOWN[-1][0] == "narrate" and "shrugs" in SHOWN[-1][1], SHOWN)
said = "The road north is closed until the thaw, I hear."
try:
    DialogueFrame.model_validate({"before": "She wipes the bar.", "after": "The road north is closed until the thaw, she says again."},
                                 context={"speaker": ["Hollis"], "others": [], "speech": said})
    check("a frame that retells the words it frames is sent back", False)
except Exception as e:
    check("a frame that retells the words it frames is sent back", "repeats the words said" in str(e), str(e))
check("...one that does not, stands", DialogueFrame.model_validate({"before": "She wipes the bar.", "after": "She looks to the door."},
                                                                  context={"speaker": ["Hollis"], "others": [], "speech": said}).after)
try:
    Clarify.model_validate({"speaker": "narrator", "line": "Do you want to end the current quest?"})
    check("a question back is never asked in the game's words", False)
except Exception:
    check("a question back is never asked in the game's words", True)

# ---- the lines
qsrc = pathlib.Path("scenes/quirk_actions.py").read_text(encoding="utf-8")
check("the errand ask has no bracketed note under it", "is asking something of you. Say yes, or no." not in qsrc)
check("the clerk ask names whom it is after", "ask the clerk after {target}." in quirks.Q["errands"]["revenge"]["ask"])
asrc = pathlib.Path("scenes/arc_actions.py").read_text(encoding="utf-8")
check("one who yields is handed to the watch as him or her", "hand {w['them']} to the watch" in asrc and '"hand them to the watch' not in asrc)

# ---- a ghost captive is found by the check
from core.models import Entity
store.save_entity(Entity(ref="captive:ghost1", kind="captive", name="the captured bandit", state="escorted", owner="player", place="parth",
                         links={"npc": "nobody_here"})) if hasattr(store, "save_entity") else None
probs = invariants.validate_campaign(store, world) if hasattr(store, "save_entity") else []
check("a captive walking with the player who is no one in the save is found by #check", any(p.where == "entities.captive" for p in probs)
      or not hasattr(store, "save_entity"), [str(p) for p in probs][:3])

store.close()
shutil.rmtree("saves/people_422_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
