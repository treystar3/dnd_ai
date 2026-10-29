"""(f348) What people are doing is the engine's: drawn from data/world/doings.yaml by role and period of the day, no two alike in a
place, held for the period and turned with it; a moment under way sets everyone's instead; a return visit is told who has moved on to
something else. The model is no longer asked for an activity."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 1); simlib.install(stub)
from engine import clock, data_check, doings
from npc import prompts
from llm.contracts import ResidentProposal
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

check("the data check passes doings.yaml", data_check.check() == [], data_check.check()[:3])
check("every role but the prisoner has at least three doings", all(len(doings.entries(r)) >= 3 for r in doings.D["by_role"]))
check("the model is not asked what anyone is doing", "activity:" not in prompts.RESIDENTS_SYSTEM and ResidentProposal.model_fields["activity"].default == "")

guard = types.SimpleNamespace(id="g1", role="guard", activity="", label=lambda: "the guard")
night = next(m for m in range(0, 1440, 30) if clock.period(m) == "night")
noon = next(m for m in range(0, 1440, 30) if clock.period(m) == "midday")
a = doings.doing_for(guard, 7, noon); b = doings.doing_for(guard, 7, noon + 10)
check("a doing holds for the period", a == b and a)
check("...and a guard at night is not checking papers at the gate", "papers" not in doings.doing_for(guard, 7, night) and all("papers" not in e["text"] for e in doings.options("guard", "night")))
days = {doings.doing_for(guard, 7, noon + d * 1440) for d in range(12)}
check("it turns from day to day", len(days) >= 3, days)
check("a different seed, a different draw", {doings.doing_for(guard, s, noon) for s in range(8)} != {a})
check("a role with no list falls to anyone's doings", doings.doing_for(types.SimpleNamespace(id="x", role="no_such_role", activity=""), 1, noon) in doings.D["anyone"])
whet = sum(1 for d in range(60) for s in range(3) if "sharpening" in doings.doing_for(guard, s, noon + d * 1440))
check("a guard sharpens a spear now and then, not for good", 0 < whet < 30, whet)
import re as _re
_all = list(doings.D["anyone"]) + [e["text"] for r in doings.D["by_role"] for e in doings.entries(r)]
check("(f375) every doing is a plain fact: two to five words, no second clause, no figure, no pronoun",
      all(2 <= len(t.split()) <= 5 and "," not in t and not _re.search(r"\b(as if|like a|his|her|him|she|he|their|them)\b", t) for t in _all),
      [t for t in _all if not 2 <= len(t.split()) <= 5 or "," in t])

# in a place: no two alike, saved on the record, the moment's doings over everyone's
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
from npc.traits import load_traits
from scenes.world import WorldScene
shutil.rmtree("saves/doings_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("doings_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.enter("tilted_plough")
acts = [n.activity for n in ws.present]
check("everyone present has a doing, none alike, none the stub's", acts and len(set(acts)) == len(acts) and "going about their work" not in acts, acts)
check("the record keeps it", all(store.load_npc(n.id).activity == n.activity for n in ws.present))
roles = {n.role for n in ws.present}
check("an innkeeper's doing is an innkeeper's", all(n.activity in [e["text"] for e in doings.entries(n.role)] + doings.D["anyone"] for n in ws.present), acts)
m = {"doings": {"all": "dancing, or stamping the time from a bench", "roles": {"innkeeper": "pulling ale as fast as the mugs come back"}}}
changed = doings.assign(store, ws.present, ws.minutes, moment=m, save=False)
check("a moment sets everyone's doing, by role where it says", all((n.activity == "pulling ale as fast as the mugs come back") == (n.role == "innkeeper") or n.activity == "dancing, or stamping the time from a bench" for n in ws.present), [(n.role, n.activity) for n in ws.present])
lines = doings.changed_lines(changed)
check("a return visit's line says what they do now and what they did then, to be shown, not reported (f374)", lines and " now, not " in lines[0]
      and "as when the player was last here" in lines[0] and "never report it as a change" in lines[0] and lines[0].endswith("."), lines)
doings.assign(store, ws.present, ws.minutes, save=False)
check("...and the moment over, their own doings come back", all(n.activity in [e["text"] for e in doings.entries(n.role)] + doings.D["anyone"] for n in ws.present))
shutil.rmtree("saves/doings_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
