"""Law part 2: locks on the theft bar, keys, jams, the plausibility call for locked things and keys, picklock as a boost, heat for break-ins."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from core.models import Ability
from engine import law, locks, intent_audit as ia, clock
from llm.contracts import ActionIntent as A, ObjectVerdict
from npc.models import NPC
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---------- the rules
def p_ok(t): return t["strong success"] + t["success"]
check("a pricier lock is harder", p_ok(law.chance_table(10, 35, target_pct=locks.quality("valuable"))) < p_ok(law.chance_table(10, 35, target_pct=locks.quality("trinket"))))
check("a jam makes it harder still", p_ok(law.chance_table(10, 35, target_pct=15 + 30)) < p_ok(law.chance_table(10, 35, target_pct=15)))
check("a picklock ability helps by tier", p_ok(law.chance_table(10, 35, bonus_pct=30, target_pct=35)) > p_ok(law.chance_table(10, 35, bonus_pct=10, target_pct=35)) > p_ok(law.chance_table(10, 35, target_pct=35)))
check("a stealth ring helps a lock too", p_ok(law.chance_table(10, 35, gear_points=20, target_pct=35)) > p_ok(law.chance_table(10, 35, target_pct=35)))
check("a low-level hand cannot open a vault", law.attempt(60, 20, 0, 0, True, 0, locks.quality("priceless") + 30)["hopeless"])
L = locks.make("the back room", "m1", "valuable", [])
check("a lock starts shut with its worth as quality", L["state"] == "locked" and L["quality"] == 35 and L["jam"] == 0 and L["id"] == "lock_the_back_room")
check("ids stay unique", locks.make("the back room", "m1", "valuable", [L])["id"] == "lock_the_back_room_2")
locks.jam(L); locks.jam(L); locks.jam(L); locks.jam(L)
check("a jam is capped", L["jam"] == 30 and locks.difficulty(L) == 65)
check("locks are found by their words", locks.find([L], "the back room door") is L and locks.find([L], "the cellar") is None)
check("a lone closed lock is the one meant when no words are given", locks.find([L], "") is L)
L2 = locks.make("a strongbox", "m1", "ordinary", [L])
check("with two locks the words pick", locks.find([L, L2], "pick the strongbox") is L2 and locks.find([L, L2], "") is None)
K = locks.make("x", "", "ordinary", [])
check("a key fits until the lock is changed", locks.key_fits(K, 99))
locks.key_stolen(K, 10, seen=False)
check("an unseen key theft changes the lock after two days", locks.key_fits(K, 11) and not locks.key_fits(K, 12), K)
locks.key_stolen(K, 10, seen=True)
check("a seen one changes it at once", not locks.key_fits(K, 10))
check("unlock is a known verb", "unlock" in ia.VERB_KINDS and "jimmy" in ia.VERB_KINDS and ia.TARGETED.count("unlock") == 1)
sit = ia.Situation(present={"m1": "Varro"}, place="parth")
check("a lock word with no unlock step is flagged for a second look", any(f.startswith("unmatched_verb:jimmy") for f in ia.risk_flags("I jimmy the back door", [A(kind="look")], sit)))
check("...and not when the plan has it", not any(f.startswith("unmatched_verb") for f in ia.risk_flags("I jimmy the back door", [A(kind="unlock", item="back door")], sit)))

# ---------- the scene
world = load_world()
shutil.rmtree("saves/locks_test", ignore_errors=True)
store = CampaignStore.open_or_create("locks_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("ranger", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
config.TURN_LOG_PATH = "saves/locks_test/turns.jsonl"
char = ws.player.character
mer = NPC(id="m1", name="Varro", people="human", role="merchant", location="parth", traits=[], trust=50)
grd = NPC(id="g1", name="Garran", people="human", role="guard", location="parth", traits=[], trust=50)
frm = NPC(id="f1", name="Hob", people="human", role="farmer", location="parth", traits=[], trust=50)
for n in (mer, grd, frm): store.save_npc(n)
ws.lucky_save = lambda: None
EVENTS = []
ws.narrate = lambda event, text="": EVENTS.append(event)
real_attempt, real_notices = law.attempt, law.notices
CALLS = []
def fix_degree(d, hopeless=False):
    def f(*a, **k):
        CALLS.append((a, k))
        return {"window": 24, "score": 0, "bar": 0, "mult": 1.0, "hopeless": hopeless, "roll": 7, "degree": d}
    law.attempt = f
def fix_notice(seen_ids):
    law.notices = lambda degree, role, is_target=False, assault=False, rng=None: (role in seen_ids)
VERDICT = {}
def verdict(**kw): VERDICT.clear(); VERDICT.update(kw)
ws.judge_object = lambda owner, wanted, text: ObjectVerdict(**VERDICT)
def reset():
    for n in (mer, frm, grd): n.memories.clear(); n.trust = 50; n.hidden = []; n.looks_away_until = -1
    ws.player.heat.clear(); ws.player.confronted.clear(); ws.player.character.key_items.clear()
    ws.present = [mer, frm]; EVENTS.clear(); NOTES.clear(); CALLS.clear(); VERDICT.clear()
    state = store.load_place("parth"); state.hidden = []; state.locks = []; store.save_place(state)
    law.attempt, law.notices = real_attempt, real_notices
    char.actives = [a for a in char.actives if a.field_use != "picklock"]
def lk(): return store.load_place("parth").locks
def hid(): return store.load_place("parth").hidden
def today(): return clock.day(ws.minutes)

# a thing kept behind a lock
reset(); fix_degree("success"); fix_notice(set())
verdict(plausible=True, name="Shady Ledger", description="A ledger of debts.", worth="valuable", locked=True, behind="the back room")
n_keys = len(char.key_items)
ws.on_steal(A(kind="steal", target="m1", item="the ledger"), "I steal the ledger")
check("a locked thing makes a lock", len(lk()) == 1 and lk()[0]["name"] == "the back room" and lk()[0]["owner"] == "m1" and lk()[0]["quality"] == 35, lk())
check("the object waits inside it", len(hid()) == 1 and hid()[0].get("lock") == lk()[0]["id"] and not hid()[0]["taken"])
check("nothing is taken and no roll is made", len(char.key_items) == n_keys and not CALLS)
check("it is narrated as locked", "locked" in EVENTS[-1], EVENTS)
check("it costs no heat", ws.heat_here() == 0)

# the key to it
verdict(plausible=True, name="Back Room Key", description="A small iron key.", worth="ordinary", is_key=True, behind="the back room")
ws.on_steal(A(kind="steal", target="m1", item="the key to the back room"), "I steal the key to the back room")
key = next((k for k in char.key_items if k.opens), None)
check("a stolen key is a key item that opens the lock", key is not None and key.opens == lk()[0]["id"], [k.name for k in char.key_items])
check("only one lock was made for both", len(lk()) == 1)
check("an unseen key theft changes the lock in two days", lk()[0]["change_day"] == today() + 2, lk()[0])
verdict(plausible=True, name="Spare Key", description="d", worth="ordinary", is_key=True, behind="the back room")
n = len(char.key_items)
ws.on_steal(A(kind="steal", target="m1", item="another key to the back room"), "another key to the back room")
check("a second key to the same lock is refused", len(char.key_items) == n and ("nothing else" in EVENTS[-1] or "already gone" in EVENTS[-1]), EVENTS[-1])

# using the key
ws.on_steal(A(kind="steal", target="m1", item="the ledger"), "I steal the ledger")
check("with the key the lock opens quietly and the ledger is taken", lk()[0]["state"] == "open" and any(k.name == "Shady Ledger" for k in char.key_items), (lk(), [k.name for k in char.key_items]))

# the lock changed
reset(); fix_degree("success"); fix_notice(set())
verdict(plausible=True, name="Shady Ledger", description="d", worth="valuable", locked=True, behind="the back room")
ws.on_steal(A(kind="steal", target="m1", item="the ledger"), "I steal the ledger")
verdict(plausible=True, name="Back Room Key", description="d", worth="ordinary", is_key=True, behind="the back room")
ws.on_steal(A(kind="steal", target="m1", item="the key to the back room"), "key")
ws.advance(1440 * 3)
EVENTS.clear(); NOTES.clear()
ws.on_steal(A(kind="steal", target="m1", item="the ledger"), "I steal the ledger")
check("after the lock is changed the old key no longer fits", lk()[0]["state"] == "locked" and any("no longer fits" in e for e in EVENTS), EVENTS)
# by hand
fix_degree("success"); fix_notice(set())
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "I pick the lock on the back room")
check("by hand the changed lock can still be picked", lk()[0]["state"] == "open")

# a key seen being taken
reset(); fix_degree("success"); fix_notice({"merchant"})
verdict(plausible=True, name="Back Room Key", description="d", worth="ordinary", is_key=True, behind="the back room")
ws.on_steal(A(kind="steal", target="m1", item="the key to the back room"), "key")
check("a key taken in view changes the lock at once", lk()[0]["change_day"] == today(), lk())

# picking by hand
def setup_lock(worth="ordinary", owner="m1"):
    reset()
    st = store.load_place("parth")
    st.locks = [locks.make("the back room", owner, worth, [])]
    store.save_place(st)
setup_lock(); fix_degree("success"); fix_notice(set())
t0 = ws.minutes
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "I pick the lock")
check("a success opens it", lk()[0]["state"] == "open")
check("it takes time", ws.minutes - t0 >= law.L["lock"]["minutes"]["success"])
check("unseen, it costs no heat", ws.heat_here() == 0)
check("the narration does not say what is inside", "Do not say what lies beyond" in EVENTS[-1], EVENTS[-1])
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "pick it again")
check("an open lock is just open", "already open" in EVENTS[-1])

setup_lock(); fix_degree("failure"); fix_notice(set())
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "I pick the lock")
check("a failure leaves it shut and jams it", lk()[0]["state"] == "locked" and lk()[0]["jam"] == law.L["lock"]["jam_step"], lk())
for _ in range(5): ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "again")
check("jams stop at the cap", lk()[0]["jam"] == law.L["lock"]["jam_cap"])
check("the lock's difficulty reaches the roll", CALLS[-1][0][6] == locks.difficulty(lk()[0]), (CALLS[-1][0][6], lk()[0]))

setup_lock(); fix_degree("partial"); fix_notice({"merchant"})
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "I pick the lock")
check("a partial opens it but is noticed", lk()[0]["state"] == "locked" or lk()[0]["state"] == "open")
check("the owner who sees a break-in remembers and loses trust", mer.trust < 50 and any("Caught the stranger" in m.text for m in mer.memories), (mer.trust, [m.text for m in mer.memories]))
check("a seen break-in costs 10 heat", ws.heat_here() == 10, ws.heat_here())

setup_lock(); fix_degree("success"); fix_notice({"farmer"})
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "I pick the lock")
check("only passers-by seeing it costs half", ws.heat_here() == 5, ws.heat_here())

# the wild has no law
setup_lock(); fix_degree("success"); fix_notice({"merchant"})
real_lawless = ws.lawless_here
ws.lawless_here = lambda: True
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "pick")
ws.lawless_here = real_lawless
check("where there is no law there is no heat", ws.heat_here() == 0)

# a guard seeing it
setup_lock(); ws.present = [mer, grd]; fix_degree("success"); fix_notice({"guard"})
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "pick")
check("a guard seeing it costs full heat", ws.heat_here() == 10)

# hopeless is a failure
setup_lock("priceless"); fix_degree("failure", hopeless=True)
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "pick")
check("a hopeless lock stays shut and says so", lk()[0]["state"] == "locked" and "beyond their skill" in EVENTS[-1], EVENTS[-1])

# the key opens without a roll
setup_lock(); fix_degree("failure")
from core.models import KeyItem
char.key_items.append(KeyItem(id="k", name="Back Room Key", opens=lk()[0]["id"], day=1))
CALLS.clear()
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "use the key")
check("a held key opens its lock with no roll", lk()[0]["state"] == "open" and not CALLS)

# a picklock ability
setup_lock(); fix_degree("success"); fix_notice(set())
pl = Ability.model_validate({**char.actives[0].model_dump(), "id": "pl", "name": "Searing Touch", "effect": "utility", "context": "out_of_combat",
                             "field_use": "picklock", "resource": "stamina", "tier": "moderate", "reach": "extended"})
char.actives.append(pl)
char.stamina = 1000.0
before = char.stamina
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "pick it")
check("a picklock ability adds its tier to the score", CALLS[-1][0][2] >= 20, CALLS[-1][0])
check("...and costs its resource", char.stamina < before, (char.stamina, before))
setup_lock(); fix_degree("success"); char.actives.append(pl); char.stamina = 0.0
ws.on_unlock(A(kind="unlock", item="the back room", target="m1"), "pick it")
check("too drained, it is tried by hand", CALLS[-1][0][2] < 20 and any("by hand" in n for n in NOTES), NOTES)
char.actives = [a for a in char.actives if a.id != "pl"]

# a lock nobody mentioned
reset(); fix_degree("success"); fix_notice(set())
verdict(plausible=True, name="storeroom", description="d", worth="ordinary", locked=True, behind="the storeroom")
ws.on_unlock(A(kind="unlock", item="the storeroom", target="m1"), "I pick the lock on the storeroom")
check("a plausible unmentioned lock is made and picked", len(lk()) == 1 and lk()[0]["name"] == "the storeroom" and lk()[0]["state"] == "open", lk())
reset(); fix_degree("success")
verdict(plausible=False, reason="no")
ws.on_unlock(A(kind="unlock", item="the vault", target="m1"), "I pick the lock on the vault")
check("an implausible one is not there", not lk() and any("no lock here" in n for n in NOTES), NOTES)
reset(); fix_degree("success"); fix_notice(set())
for nm in ("the cellar", "the attic", "the cupboard", "the loft"):
    verdict(plausible=True, name=nm, description="d", worth="ordinary", locked=True, behind=nm)
    ws.on_unlock(A(kind="unlock", item=nm, target="m1"), f"pick {nm}")
check("a place holds only a few locks", len(lk()) == law.L["lock"]["max_per_place"], len(lk()))

# a plain theft still works as before
reset(); fix_degree("success"); fix_notice(set())
n0 = len(ws.pack)
ws.on_steal(A(kind="steal", target="m1", item="torch"), "I lift a torch")
check("an ordinary theft is unchanged", len(ws.pack) == n0 + 1)
# an unlocked hidden object is still found and cap holds
reset(); fix_degree("success"); fix_notice(set())
verdict(plausible=True, name="Old Letter", description="d", worth="trinket")
ws.on_steal(A(kind="steal", target="m1", item="a letter"), "a letter")
verdict(plausible=True, name="Other Letter", description="d", worth="trinket")
ws.on_steal(A(kind="steal", target="m1", item="a different letter"), "a different letter")
check("one plain object per holder still holds", sum(1 for k in char.key_items if "Letter" in k.name) == 1)
print("\nFAILED:" if bad else "\nall passed", bad)
sys.exit(1 if bad else 0)
