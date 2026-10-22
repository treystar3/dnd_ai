"""The intercepts that read a line before the model does (scenes/world.py handle()) take only what is theirs. Each ordinary sentence
here once went to the wrong place: a question about a road left town, a gift to a hire became small talk, 'I don't want to join'
paid the fee. The turn log (engine/turnlog.py) says who took each line, so that is what is checked."""
import json, random, shutil, sys
sys.path.insert(0, ".")
import simlib
STUB = simlib.Stub("warrior", 5)
simlib.install(STUB)
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import actions, exits, mentor
from engine import party as party_rules
from llm.contracts import ActionIntent as A
from npc.models import NPC
from npc.traits import load_traits
from scenes import quirk_actions
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/intercept_test", ignore_errors=True)
store = CampaignStore.open_or_create("intercept_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 120; store.save_meta()      # mid-morning: the clerk and the guard are at work
char, _ = simlib.make_character("warrior", random.Random(1))
char.level = 10
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
config.TURN_LOG_PATH = "saves/intercept_test/turns.jsonl"
config.AUDIT_ENABLED = False                      # the plan runs as read: what matters here is who read the line
RAN, MOVES, TALKED, HIRE = [], [], [], []
for k in actions.KINDS:
    setattr(ws, f"on_{k}", lambda intent, text, k=k: RAN.append((k, intent)))
ws.run_checks = lambda intent, text: False
ws.on_move = lambda intent, text: MOVES.append(intent.destination)
ws.mentor_talk = lambda t: TALKED.append(t)
ws.hire_talk = lambda m, t: HIRE.append((m["name"], t))
PLAN = [A(kind="look")]
ws.interpret = lambda text, hint="": [a.model_copy(deep=True) for a in PLAN]      # fresh intents: the rewrites change them in place

def who(text):
    """Run the line; return what took it, from the turn log."""
    RAN.clear(); MOVES.clear(); TALKED.clear(); HIRE.clear(); NOTES.clear()
    ws.handle(text)
    rows = [json.loads(l) for l in open(config.TURN_LOG_PATH, encoding="utf-8")]
    return rows[-1]["handled_by"] if rows and rows[-1]["text"] == text else "nothing"

# ---- the one verb table
check("the audit's verbs come from the action table", actions.VERB_KINDS["give"] == ("sell", "give", "show") and "heal" in actions.VERB_KINDS and actions.VERB_KINDS["sleep"] == ("buy", "wait"), actions.VERB_KINDS.get("give"))
check("the talk intercepts' action words come from the same table, plus the party's own", ws.TALK_ACTIONS.search("i give bram a draught") and ws.TALK_ACTIONS.search("i heal bram") and ws.TALK_ACTIONS.search("i wait an hour")
      and ws.TALK_ACTIONS.search("dismiss tavi") and ws.TALK_ACTIONS.search("set out at dawn") and not ws.TALK_ACTIONS.search("you saved my ass back there, thank you"))
from engine import intent_audit as ia
check("the audit still knows a theft word from law.yaml", any(k == ("steal",) for k in ia.VERB_KINDS.values()))

# ---- ways out of town: a question is not a departure, a leaving word is a whole word
check("'tell me about the Red Road' does not leave Parth", exits.match(world, "parth", "Tell me about the Red Road")[0] is None)
check("'what do you know about the north?' does not leave either", exits.match(world, "parth", "What do you know about the north?") == (None, ""))
check("'any gossip from the west?' does not", exits.match(world, "parth", "Any gossip from the west?") == (None, ""))
check("'I take the Red Road east' leaves east", (exits.match(world, "parth", "I take the Red Road east")[0] or {}).get("dir") == "east")
check("'I'm heading out the north road' leaves north", (exits.match(world, "parth", "I'm heading out the north road")[0] or {}).get("dir") == "north")
check("'I go north' leaves north", (exits.match(world, "parth", "I go north")[0] or {}).get("dir") == "north")
check("through the scene, the road question is read by the model", who("Tell me about the Red Road") == "interpret" and RAN and RAN[0][0] == "look")

# ---- the trial, away from a hall and at one
check("a priest's heretic has a trial too, and that line is for the priest", who("I ask the priest about the heretic's trial") == "interpret")
check("asking for your own trial away from a hall is answered", who("I'd like to take the trial") == "trial" and any("guild hall" in n for n in NOTES), NOTES)
ws.pending_clarify = {"text": "x", "question": "y"}
who("I'd like to take the trial")
check("a line an intercept takes spends a question the world had asked", ws.pending_clarify is None)
ws.player.location = "guild_house"
ws.player.guild_rank = "F"; ws.player.guild_done = {"F": 5}
check("the rank is due on paper", ws.trial_due() == "E", ws.trial_due())
check("'what do I need for the next rank?' at the hall is answered, not fought", who("What do I need for the next rank?") == "trial" and ws.combat is None and any("rank E" in n for n in NOTES), NOTES)
check("'I'd like to take the trial' at the hall still steps into the ring", who("I'd like to take the trial") == "trial" and ws.combat is not None)
ws.combat = None; ws.store.save_combat(None)
ws.player.location = "trading_square"

# ---- Maren: named and no action in the line is said to her; an action with her name in it is an action
mentor.set_stage(ws.player, "hunt")
check("she is with you on the hunt", ws.mentor_with_you() and ws.mentor_in_town())
check("'Maren, let's head to the Greywood' sets out for the Greywood", who("Maren, let's head to the Greywood") == "mentor_hunt" and MOVES == ["greywood"], (MOVES, TALKED))
check("'let's go to the market first' is not the hunt", who("Let's go to the market first") == "interpret" and not MOVES, MOVES)
check("'I'm ready, let's go' is the hunt", who("I'm ready, let's go") == "mentor_hunt" and MOVES == ["greywood"])
check("'you saved my ass back there maren, thank you' is said to her", who("you saved my ass back there maren, thank you") == "mentor_named" and TALKED)
check("'Maren, how far is it?' is asked of her", who("Maren, how far is it?") == "mentor_named" and TALKED)
check("'I show Maren the wolf pelts' is a show, not a chat", who("I show Maren the wolf pelts") == "interpret" and not TALKED)
check("'I buy Maren a drink' is a buy", who("I buy Maren a drink") == "interpret" and not TALKED)
mentor.set_stage(ws.player, "harvest")
check("a line wholly in quotes beside her is said to her", who('"so, tell me about yourself"') == "mentor_quoted" and TALKED == ["so, tell me about yourself"], TALKED)

# ---- at the clerk's desk, the fee is the player's business with the clerk
clerk = NPC(id="c1", name="Ida Marrow", people="human", role="guild_clerk", location="guild_house", traits=[], trust=50); store.save_npc(clerk)
ws.player.location = "guild_house"; ws.player.guild_rank = ""
ws.residents = ws.present = [clerk]                 # residents too: the clock moving re-reads who is present from them
mentor.set_stage(ws.player, "sign")
PLAN[:] = [A(kind="talk", target="c1", speech="here you are")]
check("'\"Here's the joining fee.\"' quoted at the desk pays the clerk, not Maren", who('"Here\'s the joining fee."') == "interpret" and RAN and RAN[0][0] == "join_guild" and not TALKED, (RAN, TALKED))
check("'I hand over the three silver' at the desk still joins", who("I hand over the three silver") == "interpret" and RAN and RAN[0][0] == "join_guild", RAN)
mentor.set_stage(ws.player, "")
check("'I don't want to join the guild' stays talk", who("I don't want to join the guild") == "interpret" and RAN and RAN[0][0] == "talk", RAN)
check("'I'll register later, the fee's too steep' stays talk", who("I'll register later, the fee's too steep") == "interpret" and RAN and RAN[0][0] == "talk", RAN)
check("'I pay the fee and sign the register' joins", who("I pay the fee and sign the register") == "interpret" and RAN and RAN[0][0] == "join_guild", RAN)
ws.residents = ws.present = []

# ---- a hire: named with no action is talk; an action is an action; a follow-up is talk unless it is an action
bram = {"id": "1-0", "name": "Bram Tollis", "role": "fighter", "level": 8, "rank": "F", "blurb": "x", "permanent": True, "base_level": 8,
        "hired_at": 10, "bond": 20, "quirks": {}, "motive": "coin"}
ws.player.party = [bram]
PLAN[:] = [A(kind="look")]
check("'Bram, how are you holding up?' is for Bram", who("Bram, how are you holding up?") == "hire" and HIRE, HIRE)
check("'I give Bram a healing draught' is a give", who("I give Bram a healing draught") == "interpret" and not HIRE)
check("'I heal Bram with Mending Light' is an ability", who("I heal Bram with Mending Light") == "interpret" and not HIRE)
for line in ("I wait an hour", "I look around", "I drink a healing draught", "I pick up the rope"):
    ws._hire_last = ("Bram Tollis", ws.store.meta.turn - 1)
    check(f"'{line}' after Bram spoke is an action, not an answer to him", who(line) == "interpret" and not HIRE, HIRE)
ws._hire_last = ("Bram Tollis", ws.store.meta.turn - 1)
check("'where are you from?' after Bram spoke goes on with him", who("where are you from?") == "hire" and HIRE, HIRE)

# ---- an errand: only an answer is an answer
quirk_actions.quirks.errand_text = lambda *a, **k: "x"
quirk_actions.rules.remember = lambda *a, **k: None
ws._errand = (bram, {})
check("'Okay, let's head to the inn first' is a plan of its own, not a yes", who("Okay, let's head to the inn first") == "interpret" and not any("x" == n for n in NOTES))
ws._errand = (bram, {})
check("'Yes, of course' is a yes", who("Yes, of course") == "errand" and bram["quirks"].get("errand") == "yes")
ws._errand = (bram, {})
check("'no, not now' is a no", who("no, not now") == "errand" and bram["quirks"].get("errand") == "no")
ws.player.party = []

# ---- a coin mentioned is not a coin offered
guard = NPC(id="g1", name="Garran", people="human", role="guard", location="trading_square", traits=[], trust=50); store.save_npc(guard)
ws.player.location = "trading_square"
ws.residents = ws.present = [guard]
PLAN[:] = [A(kind="talk", target="g1", speech="x")]
check("'Don't forget the 2 silver I paid you yesterday' stays talk", who("Don't forget the 2 silver I paid you yesterday") == "interpret" and RAN and RAN[0][0] == "talk", RAN)
check("'I offer the guard 2 silver to look the other way' is a give", who("I offer the guard 2 silver to look the other way") == "interpret" and RAN and RAN[0][0] == "give" and RAN[0][1].item == "2 silver", RAN)

print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)
