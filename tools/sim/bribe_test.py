"""Bribes: coin offered for a favor is a persuasion roll helped by the offer's share of the person's wealth. Success takes the coins, otherwise they stay; the person remembers; failure costs trust."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import checks
from llm.contracts import ActionIntent
from npc.models import NPC
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)
shutil.rmtree("saves/bribe_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("bribe_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
place = next(p for p in world.places.values() if p.type != "dungeon")
store.save_player(PlayerState(character=char, location=place.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
talks = []
ws.on_talk = lambda intent, text: talks.append((intent.speech, ws.pending_check))
B = checks.RULES["bribe"]

def guard(traits=(), role="guard"):
    n = NPC(id="g1", name="Garran", people="human", role=role, location=place.id, traits=list(traits), trust=50)
    store.save_npc(n)
    return n
def offer(npc, amount, rolls, summary="lets me through the gate"):
    ws.player.character.coins = 100000
    talks.clear(); npc.memories = []
    seq = iter(rolls)
    checks.roll = lambda odds: next(seq)
    it = ActionIntent(kind="give", target=npc.id, item="silver", summary=summary)
    ws.offer_bribe(it, "I slip the guard some silver", npc, amount)
    return ws.player.character.coins

# 1. the bonus scales with the share of wealth
def bonus_for(role, amount):
    w = B["wealth"].get(role, B["default_wealth"])
    return max(B["floor"], min(B["cap"], B["per_percent"] * (amount / w * 100 - B["break_even"])))
check("a token offer is an insult (negative bonus)", bonus_for("guard", 20) < 0, bonus_for("guard", 20))
check("a bigger share of wealth is a bigger bonus", bonus_for("guard", 100) < bonus_for("guard", 300) < bonus_for("guard", 1000))
check("the same coin means more to a poor man than a rich one", bonus_for("farmer", 300) > bonus_for("noble", 300))
check("the bonus is capped", bonus_for("guard", 10**6) == B["cap"])

# 2. outcomes
g = guard()
left = offer(g, 500, [("success", 50)])
check("success takes the coins", left == 100000 - 500, left)
check("success remembered with what it was for", any("bribe" in m.text and "gate" in m.text and "persuaded" in m.text for m in g.memories), [m.text for m in g.memories])
check("success tells the npc it accepted", "persuaded" in talks[0][1] and "take" in talks[0][1])
g = guard()
left = offer(g, 500, [("failure", 99)])
check("failure keeps the coins", left == 100000, left)
check("failure costs trust", store.load_npc("g1").trust == 50 + B["trust"]["failure"], store.load_npc("g1").trust)
check("failure remembered", any("refused" in m.text and "gate" in m.text for m in g.memories))
check("failure tells the npc to refuse", "do NOT take" in talks[0][1])
g = guard()
left = offer(g, 500, [("partial", 40)])
check("partial keeps the coins and wants more", left == 100000 and "not enough" in talks[0][1])
check("a bribe is not a flat gift: no gift trust on failure", store.load_npc("g1").trust == 50)

# 3. odds respond to the person
seen = []
orig = checks.chance
def spy(c, check_, trig, npc=None, extra=()):
    r = orig(c, check_, trig, npc, extra); seen.append((r[0], [e for e in extra])); return r
checks.chance = spy
def odds_for(npc, amount):
    seen.clear(); offer(npc, amount, [("success", 50)])
    return seen[-1][0]
greedy, honest = guard(["greedy"]), guard(["honest"])
check("a greedy guard is easier than an honest one", odds_for(greedy, 400) > odds_for(honest, 400))
check("a captain is harder than a guard", odds_for(guard(role="watch_captain"), 400) < odds_for(guard(role="guard"), 400))
check("more coin, better odds", odds_for(guard(), 200) < odds_for(guard(), 1500))

# 4. giving coin with a favor goes through the bribe, plain giving does not
ws.offer_bribe = lambda intent, text, npc, amount: talks.append(("BRIBE", amount))
check("a favor is a bribe", ws.is_bribe(ActionIntent(kind="give", summary="so he lets me through"), "I give him 5 silver to let me pass"))
check("a plain gift is not", not ws.is_bribe(ActionIntent(kind="give", summary="Giving coins to a beggar"), "I give the beggar 2 silver"))
check("persuasion tag makes it a bribe", ws.is_bribe(ActionIntent(kind="give", checks=["persuasion"]), "here"))
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
