"""The intent audit gate: invariants, risk flags, the model audit's outcomes and failure paths, the clarify fallback in the scene, the turn log, the replay cases."""
import json, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import intent_audit as ia
from llm.contracts import ActionIntent as A
from tools import replay
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

sit = ia.Situation(present={"clerk1": "the clerk", "guard1": "the guard"}, abilities={"heal": "Heal"}, place="Hall")

class Ask:
    def __init__(self, matches=True, proposals=(), boom=False):
        self.matches, self.proposals, self.boom, self.calls = matches, list(proposals), boom, []
    def meaning(self, t, s):
        self.calls.append("meaning")
        if self.boom: raise TimeoutError("down")
        return "m"
    def compare(self, t, m, d, r):
        self.calls.append("compare"); return self.matches, "why"
    def propose(self, t, h):
        self.calls.append("propose")
        if self.boom: raise TimeoutError("down")
        return self.proposals.pop(0) if self.proposals else []

# invariants
dup = [A(kind="talk", target="clerk1", speech="hi"), A(kind="talk", target="clerk1", speech="hi", summary="again")]
check("exact duplicates are dropped", len(ia.fix(dup)) == 1)
two = [A(kind="harvest", item="bear", summary="skin the bear"), A(kind="other", summary="Skin the bear!")]
check("an 'other' that only restates a step is dropped", [s.kind for s in ia.fix(two)] == ["harvest"])
check("different speech is not a duplicate", len(ia.fix([A(kind="talk", target="clerk1", speech="a"), A(kind="talk", target="clerk1", speech="b")])) == 2)
check("a target who is not here is a problem", bool(ia.problems([A(kind="talk", target="smith")], sit)))
check("a target who is here is fine", not ia.problems([A(kind="talk", target="clerk1")], sit))
check("wildlife is a valid target only when present", not ia.problems([A(kind="attack", target="wildlife")], ia.Situation(wildlife=True)) and bool(ia.problems([A(kind="attack", target="wildlife")], sit)))
check("an ability the player lacks is a problem", bool(ia.problems([A(kind="ability", ability="fireball")], sit)) and not ia.problems([A(kind="ability", ability="Heal")], sit))
check("an empty target is not a problem", not ia.problems([A(kind="talk")], sit))

# risk flags
def flags(text, plan): return ia.risk_flags(text, plan, sit)
check("a calm single step has no risk", flags("I go north", [A(kind="move", destination="x")]) == [])
check("a plain purchase has no risk", flags("I buy bread", [A(kind="buy", ware="bread")]) == [])
check("several steps are risky", "multi_intent" in flags("a and b", [A(kind="look"), A(kind="wait")]))
check("'other' is risky", "other_intent" in flags("x", [A(kind="other")]))
check("money with a talk is risky", "money_context" in flags("I give 5 silver", [A(kind="talk", target="guard1")]))
check("a known verb with no matching step is risky", any(f.startswith("unmatched_verb") for f in flags("I attack the guard", [A(kind="talk", target="guard1")])))
check("a known verb that is matched is not", not any(f.startswith("unmatched_verb") for f in flags("I attack the guard", [A(kind="attack", target="guard1")])))
check("a purchase the player never mentioned is risky", "unmentioned_buy" in flags("pay the fee", [A(kind="buy", ware="trail_rations")]))
check("a room buy from 'sleep' is not unmentioned", "unmentioned_buy" not in flags("I want to sleep", [A(kind="buy", ware="room")]))
check("a step that cannot happen is risky", "invalid_step" in flags("x", [A(kind="talk", target="ghost")]))
check("describe names the people", "the clerk" in ia.describe([A(kind="talk", target="clerk1")], sit))

# audit outcomes
calm = [A(kind="move", destination="x")]
a = Ask(); r = ia.audit("I go north", calm, sit, a)
check("a calm turn is skipped with no model calls", r.status == "skipped" and a.calls == [], (r.status, a.calls))
risky = [A(kind="talk", target="guard1", speech="here"), A(kind="buy", ware="trail_rations")]
a = Ask(matches=True); r = ia.audit("I give the guard 5 silver", risky, sit, a)
check("a plan the audit agrees with is left alone (two calls)", r.status == "unchanged" and a.calls == ["meaning", "compare"] and len(r.plan) == 2, (r.status, a.calls))
a = Ask(matches=False, proposals=[[A(kind="give", target="guard1", item="5 silver")]]); r = ia.audit("I give the guard 5 silver", risky, sit, a)
check("a mismatch takes the valid proposal", r.status == "changed" and [s.kind for s in r.plan] == ["give"] and a.calls == ["meaning", "compare", "propose"], (r.status, a.calls))
a = Ask(matches=False, proposals=[[A(kind="talk", target="guard1")] * 1 and [A(kind="talk", target="guard1", speech="here"), A(kind="buy", ware="trail_rations")]])
r = ia.audit("I give the guard 5 silver", risky, sit, a)
check("a proposal identical to the plan counts as unchanged", r.status == "unchanged", r.status)
bad_plan = [A(kind="talk", target="ghost")]
a = Ask(proposals=[[A(kind="talk", target="clerk1")]]); r = ia.audit("hello ghost", bad_plan, sit, a)
check("an impossible plan skips straight to a proposal", r.status == "changed" and a.calls == ["propose"], (r.status, a.calls))
a = Ask(proposals=[[A(kind="talk", target="ghost")], [A(kind="talk", target="clerk1")]]); r = ia.audit("hello ghost", bad_plan, sit, a)
check("a second try is allowed", r.status == "changed" and a.calls == ["propose", "propose"], (r.status, a.calls))
a = Ask(proposals=[[A(kind="talk", target="ghost")], [A(kind="talk", target="ghost2")]]); r = ia.audit("hello ghost", bad_plan, sit, a)
check("two bad proposals fail with a reason", r.status == "failed" and "not here" in r.reason, (r.status, r.reason))
a = Ask(boom=True); r = ia.audit("I give the guard 5 silver", risky, sit, a)
check("a model that is down fails open on a possible plan", r.status == "unchanged" and len(r.plan) == 2, (r.status, r.reason))
a = Ask(boom=True); r = ia.audit("hello ghost", bad_plan, sit, a)
check("a model that is down cannot rescue an impossible plan", r.status == "failed", r.status)

# the scene
from engine import checks
from npc.models import NPC
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
world = load_world()
shutil.rmtree("saves/audit_test", ignore_errors=True)
store = CampaignStore.open_or_create("audit_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
place = next(p for p in world.places.values() if p.type != "dungeon")
store.save_player(PlayerState(character=char, location=place.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True                 # the mentor is not what this test is about
config.TURN_LOG_PATH = "saves/audit_test/turns.jsonl"
guard = NPC(id="g1", name="Garran", people="human", role="guard", location=place.id, traits=[], trust=50); store.save_npc(guard)
ws.present = [guard]
ran = []
for k in ("on_talk", "on_give", "on_buy", "on_other"):
    setattr(ws, k, lambda intent, text, k=k: ran.append((k, intent.kind)))
ws.run_checks = lambda intent, text: False
ws.interpret = lambda text, hint="": [A(kind="talk", target="g1", speech="x"), A(kind="buy", ware="trail_rations", count=2)]
class SceneAsk(Ask): pass
ws.audit_asker = lambda: SceneAsk(matches=False, proposals=[[A(kind="give", target="g1", item="5 silver")]])
turn0 = store.meta.turn
ws.handle("I give the guard 5 silver to look away")
check("the changed plan is what runs", ran == [("on_give", "give")], ran)
check("the turn passed", store.meta.turn == turn0 + 1)
log = [json.loads(l) for l in open(config.TURN_LOG_PATH)]
check("the turn is logged with raw and final plans", len(log) == 1 and [s["kind"] for s in log[0]["raw"]] == ["talk", "buy"] and [s["kind"] for s in log[0]["final"]] == ["give"] and log[0]["audit"] == "changed", log)
check("the log keeps who was here for promoting", log[0]["present"] == {"g1": guard.label()}, log[0].get("present"))

ran.clear(); NOTES.clear(); turn0 = store.meta.turn
ws.interpret = lambda text, hint="": [A(kind="talk", target="ghost", speech="x")]
ws.audit_asker = lambda: SceneAsk(matches=False, proposals=[[A(kind="talk", target="ghost")], [A(kind="talk", target="ghost")]])
ws.handle("hello ghost")
check("a failed audit asks the player to reword", any("say it another way" in n for n in NOTES), NOTES)
check("a failed audit runs nothing and spends no turn", ran == [] and store.meta.turn == turn0 and not ws.buffering, (ran, store.meta.turn))

ran.clear(); NOTES.clear()
config.AUDIT_ENABLED = False
ws.interpret = lambda text, hint="": [A(kind="talk", target="g1", speech="x"), A(kind="buy", ware="trail_rations", count=2)]
ws.audit_asker = lambda: (_ for _ in ()).throw(AssertionError("audit should be off"))
ws.handle("I give the guard 5 silver to look away")
check("with the audit off the plan runs as read", [r[0] for r in ran] == ["on_talk", "on_buy"], ran)
config.AUDIT_ENABLED = True

# replay cases
badcases = replay.deterministic(quiet=True)
check("every recorded replay case passes", not badcases, badcases)
check("there are at least the four seed cases", len(replay.load_cases()) >= 4)

print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)
