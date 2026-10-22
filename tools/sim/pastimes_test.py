"""Pastimes (f332, scenes/pastime_actions.py): praying, gambling and haggling are actions of their own. A prayer at a temple is seen by the
priest and the companions; a gamble stakes coin against the house's edge and the world remembers who played; a haggle is a persuasion check
that lands at a price or buys nothing; every number is in data/rules/pastimes.yaml and every deed goes through the bus."""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.models import NPC
from npc.traits import load_traits
from llm.contracts import ActionIntent
from engine import actions, checks, money
from scenes import pastime_actions as pa
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/pastimes_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("pastimes_test")
store.meta.seed = 2; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.coins = 10000
store.save_player(PlayerState(character=char, location="parth_temple"))
ws = WorldScene(store, world, load_traits(), store.load_player())
narrated, notes, deeds = [], [], []
ws._narrate_now = lambda event, player_text="": narrated.append(event)
_note = console.note
console.note = lambda t, *a, **k: notes.append(t)
ws.deed = lambda d: deeds.append(d)
ws.store.meta.minutes = 4 * 60                                          # noon
priest = NPC(id="pr1", name="Brother Aldo", people="human", role="priest", location="parth_temple", tier="known"); store.save_npc(priest)
inn = NPC(id="in1", name="Hollis", people="human", role="innkeeper", location="tilted_plough", tier="known", trust=50); store.save_npc(inn)
check("pray, gamble and haggle are kinds the game declares, with handlers and prompt lines", all(k in actions.KINDS for k in ("pray", "gamble", "haggle"))
      and all(hasattr(ws, f"on_{k}") for k in ("pray", "gamble", "haggle")) and actions.problems(WorldScene, __import__("scenes.world_prompts", fromlist=["x"]).INTERPRET_SYSTEM) == [])

# ---- pray
ws.player.location = "parth_temple"
ws.residents = ws.present = [priest]
t0 = ws.minutes
ws.on_pray(ActionIntent(kind="pray", summary="pray for a safe road"), "I kneel and pray for a safe road")
check("a prayer takes its time and is shown with the faith of the place", ws.minutes == t0 + pa.PT["pray"]["minutes"] and narrated and "PRAYS" in narrated[-1] and "faith here is" in narrated[-1], narrated[-1:][0][:120] if narrated else "")
check("...the priest remembers the stranger at their altar", any("stopped to pray" in m.text for m in priest.memories), [m.text for m in priest.memories])
check("...the companions see a stop at a shrine", deeds == ["shrine"], deeds)
check("...and it is in the journal as a deed", any(r["kind"] == "prayed" for r in store.journal_tail(5)), [r["kind"] for r in store.journal_tail(5)])
deeds.clear(); narrated.clear()
ws.player.location = "trading_square"; ws.residents = ws.present = []
ws.on_pray(ActionIntent(kind="pray", summary="a word of thanks"), "I say a word of thanks")
check("a prayer anywhere else is the player's own moment: no shrine for the companions", deeds == [] and narrated and "PRAYS" in narrated[-1])

# ---- gamble
ws.player.location = "tilted_plough"; ws.residents = ws.present = [inn]
c = ws.player.character
_roll = checks.roll
checks.roll = lambda odds, rng=None, c=None: ("strong success", 1)
c.coins = 10000; narrated.clear()
ws.on_gamble(ActionIntent(kind="gamble", target="in1", item="2 silver", summary="dice with the innkeeper"), "I throw dice with Hollis for 2 silver")
check("a strong hand doubles the stake", c.coins == 10000 + 2 * 200 and "WINS, and well" in narrated[-1], (c.coins, narrated[-1:][0][:80] if narrated else ""))
checks.roll = lambda odds, rng=None, c=None: ("failure", 99)
c.coins = 10000
ws.on_gamble(ActionIntent(kind="gamble", target="in1", summary="dice"), "I throw dice")
check("a losing throw costs the default stake", c.coins == 10000 - pa.PT["gamble"]["default_stake"] and "LOSES" in narrated[-1], c.coins)
c.coins = 100
ws.on_gamble(ActionIntent(kind="gamble", target="in1", item="5 gold", summary="dice"), "I stake 5 gold")
check("nobody stakes more than half the purse, whatever they said", c.coins == 100 - int(100 * pa.PT["gamble"]["max_share"]), c.coins)
check("...the one who played remembers, and the companions see gambling", any("dice" in m.text for m in inn.memories) and "gambling" in deeds, (inn.memories[-1:], deeds))
ws.residents = ws.present = [priest]
ws.halted = False
ws.on_gamble(ActionIntent(kind="gamble", summary="dice"), "I throw dice")
check("with nobody who will play, nothing is staked", ws.halted and any("Nobody here will play" in n for n in notes))
checks.roll = _roll

# ---- haggle
ws.residents = ws.present = [inn]
ws.halted = False
bought = []
ws.buy_ware = lambda seller, ware, text="", quiet=False: bought.append((seller.id, ws.quote_ware(seller, ware).price, ware.price)) or True
ws.resolve = lambda check, npc=None, talking=False, text="", extra=(): "success"
room = next(w for w in world.roles["innkeeper"].sells if w.kind == "room")
ws.on_haggle(ActionIntent(kind="haggle", target="in1", ware=room.id, summary="haggle over the room"), "I haggle with Hollis over the room")
check("a haggle that lands buys at the price it won", bought and bought[-1][1] == round(room.price * pa.PT["haggle"]["discount"]["success"]), bought)
check("...and the price goes back to normal afterwards", ws.quote_ware(inn, room).price == room.price and ws.haggle_factor == 1.0)
bought.clear(); narrated.clear()
trust0 = inn.trust
ws.resolve = lambda check, npc=None, talking=False, text="", extra=(): "failure"
ws.on_haggle(ActionIntent(kind="haggle", target="in1", ware=room.id, summary="haggle"), "I haggle")
check("a haggle that fails buys nothing, and the seller is a little cooler", not bought and inn.trust == trust0 + pa.PT["haggle"]["annoyed_trust"] and "gets nowhere" in narrated[-1], (bought, inn.trust))

console.note = _note
shutil.rmtree("saves/pastimes_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
