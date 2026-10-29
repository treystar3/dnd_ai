"""(f392) A captive has a lifecycle: taken only from someone who lived and yielded, escorted at the player's side, and then handed over,
released, put to death, or slipped away - never bound forever. Two nights showed a berserker walked bound for a thousand turns, an outlaw
narrated among the dead and then throwing down his weapon, and the game offering to butcher bandits for hide and meat."""
import random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import llm.gateway as gw
SENT = []
_chat = gw._client.chat
def chat(*a, **k):
    SENT.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
NOTES = []
for f in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import combat as C, entities
from engine.arcs import A
from npc.traits import load_traits
from scenes import combat_scene as cs
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/captive_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("captive_test")
store.meta.seed = 4; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 10
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")

def scene(cids, lvl=10):
    me = C.fighter_from_character(ws.player.character)
    foes = [C.fighter_from_creature(world.bestiary[c], lvl, "normal", f"e{i}", name=f"{c} {i + 1}") for i, c in enumerate(cids)]
    fight = C.Combat(fighters=[me] + foes, place="parth")
    return cs.CombatScene(ws, fight, cids[0]), fight, foes

# ---- the one who lives and yields is chosen before anyone is told who fell
PR = A["prisoner"]
saved = dict(PR)
PR.update(chance=1.0, min_chance=1.0, max_chance=1.0)
sc, f, foes = scene(["bandit", "bandit", "bandit"])
foes[1].level = 12
for e in foes:
    e.hp = 0
f.over = "victory"
SENT.clear(); NOTES.clear()
sc.victory()
PR.clear(); PR.update(saved)
after = [m for t, m in SENT if t == "Narration"]
told = after[-1][-1]["content"] if after else ""
fallen_line = re.search(r"THE FALLEN: (.*)", told).group(1) if "THE FALLEN" in told else ""
check("a fight won against outlaws can leave one who lives and yields: the strongest of them", foes[1].alive and foes[1].surrendered and not foes[0].alive)
check("...and the after-fight passage is told he yielded, not that he fell",
      "THOSE WHO YIELDED" in fallen_line and foes[1].name not in fallen_line.split("THOSE WHO YIELDED")[0], fallen_line[:300])
caps = store.find_entities(kind="captive")
check("...and he is taken as a captive in the registry, escorted", len(caps) == 1 and caps[0].state == "escorted" and caps[0].owner == "player"
      and caps[0].links.get("fighter") == foes[1].id, [(c.ref, c.state) for c in caps])
cap_id = caps[0].links["npc"]
npc = store.load_npc(cap_id)
check("...a person of their own: a gender, a people, a pronoun kept", npc.gender in ("male", "female") and npc.people
      and caps[0].pronoun == entities.GENDER[npc.gender], (npc.gender, npc.people, caps[0].pronoun))
check("...whose yielding is told with their own pronoun", any(re.search(r"throws down (his|her) weapon", n) for n in NOTES), NOTES)
check("people's bodies are not offered for butchering, and leave no carcass", not any("butcher" in n for n in NOTES)
      and not store.load_place("parth").carcasses, (NOTES, store.load_place("parth").carcasses))
check("the captive is here, and in the cast every writer is told", any(n.id == cap_id for n in ws.present)
      and any(l.startswith(f"{npc.name}: ") for l in entities.cast_lines(ws)), entities.cast_lines(ws))

# ---- no prisoner from the dead
before = len(store.find_entities(kind="captive"))
sc2, f2, foes2 = scene(["bandit"])
foes2[0].hp = 0
ws.camp_fight_over("victory", [foes2[0]])
check("a camp fight's end makes no prisoner of the dead", len(store.find_entities(kind="captive")) == before)

# ---- escorted: they come along, and no more than three walk bound
dest = next(p for p in world.places if p != "parth" and world.places[p].type in ("town", "city", "village"))
ws.enter(dest)
check("an escorted captive comes along to the next place", store.load_npc(cap_id).location == dest and any(n.id == cap_id for n in ws.present))
for i in range(2):
    ws.make_prisoner(f"Extra{i}", "", kind="bandit")
sc3, f3, foes3 = scene(["bandit"])
foes3[0].hp, foes3[0].surrendered = 1, True
taken = sc3.take_prisoners([foes3[0]])
check("with three walking bound, a fourth who yields is not taken: they wait on the player's word", taken == [] and len(ws.escorted()) == 3, ws.escorted())

# ---- they work at their bonds
X = entities.L["captive"]["escape"]
saved_x = dict(X)
X.update(chance_per_day=1.0, chance_most=1.0)
ws.store.meta.minutes += 3 * 1440
NOTES.clear()
ws.arc_tick()
X.clear(); X.update(saved_x)
left = store.find_entities(kind="captive", state="escaped")
check("a captive held for days slips away, told, and kept as escaped", left and any("slipped away" in n for n in NOTES) and not ws.escorted(),
      ([(e.name, e.state) for e in store.find_entities(kind="captive")], NOTES))
check("...and the player no longer holds them", not any(e.links.get("npc") in ws.player.prisoners for e in left))

# ---- what the player chooses: hand over, release, put to death; and death frees them
a = ws.make_prisoner("Hollis", "", kind="bandit")
ws.settle_prisoner(a, "release", "I let him go.")
check("a released captive is kept as released, with why", store.load_entity(f"captive:{a.id}").state == "released"
      and store.load_entity(f"captive:{a.id}").history[-1][2] == "released")
b = ws.make_prisoner("Marek", "", kind="bandit")
ws.settle_prisoner(b, "kill", "I end it.")
check("one put to death is kept as executed", store.load_entity(f"captive:{b.id}").state == "executed")
c_ = ws.make_prisoner("Skarn", "", kind="orc war chief")
check("a captive's kind names their people: an orc war chief is an orc", store.load_npc(c_.id).people == "orc", store.load_npc(c_.id).people)
check("when the player dies, the captives they held get away", ws.captives_lost("got away while their captor lay dead") == 1
      and store.load_entity(f"captive:{c_.id}").state == "escaped")

store.close()
shutil.rmtree("saves/captive_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
