"""(f385) The rest of what the third logged playthrough showed, and what its logs could not.
- The turn log did not say what the player was shown: notes, coins and refusals were missing, a turn with two narration calls did not
  say which was printed, a click in a pane left no trace, and a turn's time was when it ended. Each row now carries what was shown,
  when the turn began and how long it took, and any passage written twice; a # command that changed something is a row too.
- A turn that showed nothing at all says so in one line, and the refusal log keeps what ran.
- The fight narrator was told nothing of the player's side: one hire was she, he and they in one fight, and a mage's bolts became a
  crossbow's. Every ally is given with their pronoun, their look and what they fight with; a hire's gender, drawn with their name,
  is kept (and an older save's hires get theirs back). A hire called the player by another hire's name: that is sent back.
- A sahuagin that yielded was let go with nobody asked: a foe that yields now waits on the player's word. Fenris died and the talk
  after it never named him; a beast that only went down was talked over as dead.
- Parth's crowd line came back in every passage; the Greywood was north, west and west-north-west; Maren told an empty-handed player
  to draw; a beast-master built around a heavy bludgeon woke with no weapon; a hire asked a question back after nearly every reply."""
import json, random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import llm.gateway as gw
CALLS = []
_chat = gw._client.chat
def chat(*a, **k):
    CALLS.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import config
import ui.console as uc
NOTES = []
for f in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from pathlib import Path
from pydantic import ValidationError
from core.models import Companion
from engine import combat, exits, mentor, party, refusals, turnlog
from llm.contracts import CompanionReply, Exchange, Narration
from npc.traits import load_traits
from scenes import combat_prompts as cp, voice
from scenes.combat_scene import CombatScene
from scenes.world import WorldScene
from storage import migrations
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/playthrough3b_test", ignore_errors=True)
store = CampaignStore.open_or_create("playthrough3b_test")
store.meta.seed = 3; store.meta.minutes = 120; store.meta.turn = 1; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="trading_square", guild_rank="F"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("trading_square")
LOG = Path("saves/playthrough3b_test/turns.jsonl")
config.TURN_LOG_PATH = str(LOG)
def rows():
    return [json.loads(l) for l in LOG.read_text().splitlines()] if LOG.exists() else []

# ---- 1. what each turn showed
turnlog.begin(uc)
stub.plan = [{"kind": "look"}]
ws.turn("I look around")
uc.ledger("Found: a copper ring")
turnlog.end()
r = rows()[-1] if rows() else {}
check("a turn's row says what the player was shown, in order, with its kind", r.get("shown") and r["shown"][-1] == {"kind": "ledger", "text": "Found: a copper ring"}
      and any(s["kind"] == "narration" for s in r["shown"]), r.get("shown"))
check("...when the turn began, and how long it took", r.get("started") and isinstance(r.get("turn_seconds"), float), r)

calls = []
def gen(*a, **k):
    calls.append(a[2])
    return Narration(text='The woodcutter looks up. "The wolves took three sheep last week," he says.' if len(calls) == 1
                     else "The woodcutter looks up and points north.")
_g = voice.generate
voice.generate = gen
turnlog.begin(uc)
voice.fresh("narrate", "sys", "req", Narration, [], said="ask about the wolves")
turnlog.record(5, "ask about the wolves", "interpret")
turnlog.end()
voice.generate = _g
r = rows()[-1]
check("a passage written twice says why, and which the player read", r.get("rewrites") == [{"task": "narrate", "why": ["put words in someone's mouth"], "shown": "rewrite"}],
      r.get("rewrites"))
logged = []
real_log = gw._log
gw._log = lambda *a, **k: logged.append(dict(getattr(gw._tag, "fields", None) or {}))
with gw.tagged(rewrite_of_draft=["x"]):
    gw._log("narrate", 1, 0.1, [], "", None)
gw._log = real_log
check("...and the rewrite's call in the model log is marked as replacing the draft", logged == [{"rewrite_of_draft": ["x"]}], logged)

n = len(rows())
turnlog.begin(uc)
turnlog.end(command=ws.command_row("#inventory", ws.player.location, ws.header_key()))
check("a pane that only shows a view is no row", len(rows()) == n)
turnlog.begin(uc)
before, bar = ws.player.location, ws.header_key()
ws.enter("guild_house")
turnlog.end(command=ws.command_row("#goto guild_house", before, bar))
r = rows()[-1]
check("a pane button that walks the player somewhere is a row, with what it changed", len(rows()) == n + 1 and r["handled_by"] == "command"
      and r["text"] == "#goto guild_house" and "place" in r["changed"], r)

# ---- 2. a turn that shows nothing
NOTES.clear()
real_look = ws.on_look
ws.on_look = lambda intent, text: None
stub.plan = [{"kind": "look"}]
ws.turn("I gaze at nothing in particular")
ws.on_look = real_look
check("a turn that showed nothing says so in one line", NOTES and "Nothing comes of that" in NOTES[-1], NOTES[-2:])
check("...and the refusal log keeps what ran", refusals.SESSION and refusals.SESSION[-1]["kind"] == "silent" and "look" in refusals.SESSION[-1]["why"],
      refusals.SESSION[-1:])
NOTES.clear()
stub.plan = [{"kind": "look"}]
ws.turn("I look around")
check("...and a turn that showed something does not", not any("Nothing came of that" in x for x in NOTES), NOTES)

# ---- 3. the player's side, as the fight narrator sees it
offers = party.roster(3, "guild_house", 0, 5, 100, [])
check("every hire on a roster has she or he, kept", offers and all(o.get("pronoun") in ("she", "he") for o in offers), [o.get("pronoun") for o in offers])
check("...and blurbs name no gender of their own", not any(w in o["blurb"] for o in offers for w in ("woman", "bowman")))
hired = party.new_hire(offers[0], 5, 0)
check("a hire made from an offer keeps it", hired.get("pronoun") == offers[0]["pronoun"])
old = dict(hired); old.pop("pronoun")
check("an older save's hire gets back the pronoun their week's roster drew", party.pronoun_of(old, 3, [f"guild_house:{old['id']}"]) == offers[0]["pronoun"],
      (old.get("pronoun"), offers[0]["pronoun"]))
mage = next((o for o in party.roster(3, "guild_house", 7, 5, 100, []) + offers if o["role"] == "mage"), None) or dict(offers[0], role="mage")
mage = party.new_hire(mage, 5, 0)
ws.player.party = [mage]
ws.player.character.companions = [Companion(id="c1", name="Fenris", creature="wolf", kind="beast", role="striker", level=3)]
me = combat.fighter_from_character(ws.player.character)
fen = combat.companion_fighter(world.bestiary["wolf"], 3, "ally_c1", "Fenris"); fen.side = "ally"
m_f = party.fighter(mage)
foe = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "e1", "reef shark", "engaged")
sc = CombatScene.__new__(CombatScene); sc.ws = ws; sc.fight = combat.Combat(fighters=[me, fen, m_f, foe], place="x", conditions=[])
looks = sc.ally_looks()
mine = next((l for l in looks if l.startswith(mage["name"])), "")
check("the narrator is told each hire's pronoun and what they fight with", f"({party.pronoun_pair(mage['pronoun'])})" in mine and "never a bow, a crossbow" in mine, looks)
check("...and the player's beast, as theirs, she or he, the same each time", any(l.startswith("Fenris (") and "the player's own wolf" in l for l in looks)
      and ws.player.character.companions[0].pronoun in ("she", "he"), looks)
req = cp.narrate_request("x", "t", "hit it", ["You hit"], "fists", "fine", ["shark"], 2, allies=looks)
check("...under its own heading, to be kept as written", "ON THE PLAYER'S SIDE (keep each as written here" in req and mine in req)
desc = {n: d for _, n, d, _ in ws.hire_people()}
ws.player.party_mode = "with"
desc = {n: d for _, n, d, _ in ws.hire_people()}
check("the hire's pronoun is in what everyone else is told about them", party.pronoun_pair(mage["pronoun"]) in desc.get(mage["name"], ""), desc)

def reply(speech, others, said):
    try:
        CompanionReply.model_validate({"speech": speech, "gesture": ""}, context={"others": others, "said": said, "player": "Bumbo Claat"}); return ""
    except ValidationError as e:
        return str(e)
check("a hire who calls the player by another hire's name is sent back", "Do not call the player Salith" in reply("He isn't exactly looking for company, Salith.", ["Salith Yir"], "*talk to hermit*"))
check("...at the start of the line too", reply("Salith, he won't talk.", ["Salith Yir"], "what now") != "")
check("...but may name them when the player brought them up", reply("Ask Salith, then.", ["Salith Yir"], "what does Salith think") == ""
      and reply("He won't talk, Salith.", ["Salith Yir"], "ask Salith if the hermit talks") == "")
check("...and may speak of them freely", reply("Salith thinks the tide turns soon.", ["Salith Yir"], "what now") == "")
from scenes import party_prompts as ppr
p = ppr.talk_prompt("how", "core", "rel", [], [], [], "Bumbo Claat", "hello", others=["Salith Yir"]).render()
check("the hire is told whom they are talking with, and who is someone else", "YOU ARE TALKING WITH" in p and "Salith Yir is someone else" in p, p[:600])

# ---- 4. a foe that yields waits on the player
ws.enter("greywood")
from engine import quests
q = quests._quest("hunt", "F", "Hunt 2 wolves", ws.minutes, place="greywood", creature="wolf", count=2)
ws.player.quests = [q]
def yielded():
    e = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "e9", "the wolf", "engaged")
    e.hp, e.fled, e.surrendered = 3, True, True
    return e
NOTES.clear()
ws.hold_yielded([yielded()])
check("a foe that yielded asks the player: spare it, or finish it", NOTES and "Spare it, or finish it?" in NOTES[-1], NOTES)
stub.plan = [{"kind": "look"}]
ws.turn("finish it")
check("'finish it' kills it: it counts for the contract", q["progress"] == 1 and not ws.held_yield, q)
check("...and it can be skinned", any(c["creature"] == "wolf" for c in store.load_place("greywood").carcasses))
SEEN = []
real_notice = ws.notice
ws.notice = lambda d: (SEEN.append(d.kind), real_notice(d))[1]
ws.hold_yielded([yielded()])
ws.turn("let it go")
check("'let it go' spares it, and that is the deed the companions see", "spared" in SEEN and q["progress"] == 1, SEEN)
SEEN.clear()
ws.hold_yielded([yielded()])
ws.turn("don't kill it")
check("'don't kill it' is mercy", "spared" in SEEN, SEEN)
SEEN.clear(); NOTES.clear()
ws.hold_yielded([yielded()])
stub.plan = [{"kind": "look"}]
ws.turn("I look around the trees")
check("a line about something else: it slips away, and the line is read as usual", any("slips away" in x for x in NOTES) and "spared" not in SEEN
      and not ws.held_yield, NOTES)
ws.notice = real_notice
check("the fight no longer spares a yielded foe on its own", "Spared(" not in open("scenes/combat_scene.py").read())

# ---- the fallen, talked over by name
def ex(lines, must):
    try:
        Exchange.model_validate({"lines": [{"speaker": a, "text": b} for a, b in lines]},
                                context={"speakers": ["Merris Oxwick", "Salith Yir"], "lines": (2, 4), "material": [], "must_name": must}); return ""
    except ValidationError as e:
        return str(e)
check("the talk after a death that never names the dead is sent back", "says Fenris's name" in ex([("Merris Oxwick", "They won't be coming back from this."),
                                                                                                  ("Salith Yir", "No. They won't.")], "Fenris"))
check("...and names them, it stands", ex([("Merris Oxwick", "Fenris held the line to the end."), ("Salith Yir", "He did.")], "Fenris") == "")
ws.player.party_last_fight = {"minute": ws.minutes, "won": True, "fallen": ["Fenris"], "fallen_ids": ["c1"]}
comp = ws.player.character.companions[0]
sc.rng = types.SimpleNamespace(random=lambda: 0.99)
sc.companions_after_fight({"ally_c1"})
check("a beast that only went down is not talked over as dead", "Fenris" not in ws.player.party_last_fight["fallen"] and "Fenris" in ws.player.party_last_fight.get("hurt", []),
      ws.player.party_last_fight)
comp.fallen, comp.dead = False, False
ws.player.party_last_fight = {"minute": ws.minutes, "won": True, "fallen": ["Fenris"], "fallen_ids": ["c1"]}
sc.rng = types.SimpleNamespace(random=lambda: 0.0)
sc.companions_after_fight({"ally_c1"})
check("...one that died is, as the player's own animal", ws.player.party_last_fight["fallen"] == ["Fenris"]
      and ws.player.party_last_fight.get("fallen_what", {}).get("Fenris") == "the player's own wolf", ws.player.party_last_fight)
ws.player.character.companions = []

# ---- 5. data and voice
ws.enter("greywood")
ws.enter("trading_square")                                  # a fresh visit to Parth
def streets_given():
    CALLS.clear()
    ws._narrate_now("The player waits.", "I wait")
    asked = next((m[-1]["content"] for t, m in CALLS if t == "Narration"), "")
    return any(" ".join(c.split()) in asked for c in world.places["parth"].crowd.values())
first = streets_given()
check("Parth's crowd goes to the narrator once a visit to the town", first and not streets_given(), first)
ws.enter("guild_house")
check("...walking into the hall, still the same visit: not again", not streets_given())
ws.enter("greywood"); ws.enter("trading_square")
check("...and again on the next visit", streets_given())
check("Parth's crowd has no drivers eating in the inn", "drivers" not in world.places["parth"].crowd["market"])
way = exits.sector_of(exits._heading(world, "parth", "greywood"))
check("the Greywood is where the map puts it: northwest of Parth", way == "northwest", way)
said = open("data/world/mentor.yaml").read() + open("data/world/towns/parth.yaml").read() + open("data/world/places.yaml").read()
check("...Maren, the town and the place agree with it", "half an hour west of" not in said and "To the north, the dark edge" not in said
      and "conversation about the north" not in said and said.count("half an hour northwest of Parth") == 2)
ws.player.character.equipment.pop("main_hand", None)
ws.player.mentor["said"] = {}
check("Maren tells an empty-handed player to get their hands up, not to draw", mentor.empty_handed(ws.player.character)
      and all("Draw" not in mentor.line(ws.player, "found", s) for s in range(4)))
check("...and nobody is called armed for it", "armed stranger" not in open("data/world/mentor.yaml").read())
from character import kit
check("a beast-master built around a heavy bludgeon carries one", {"club", "mace", "warhammer"} == {b.id for b in kit.weapon_named(
      "Heavy bludgeon and rhythmic intimidation Beast-Breaker Bard", kit.weapon_options())})
check("...while words that name no weapon name none (the model chooses one: everyone wakes armed, f389)",
      kit.weapon_named("A tamer who fights beside her wolves", kit.weapon_options()) == [])
from engine import voices
check("a hire asks a question back now and then, not every time", all(voices.AXES["questions"]["options"][k]["text"].startswith("now and then, not every time")
                                                                      for k in ("after", "first")))
check("the save version moves on with it", migrations.CURRENT >= 8)

store.close()
shutil.rmtree("saves/playthrough3b_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
