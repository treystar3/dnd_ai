"""Bug groups A-D: placeholders, work offers, narration post-check, audit rules, stat helpers."""
import sys
sys.path.insert(0, ".")
from llm.contracts import ActionIntent, WorkOffer
from engine import voice_rules, stats
from engine import intent_audit as ia

bad = []
def check(name, ok):
    if not ok:
        bad.append(name)

i = ActionIntent(kind="talk", target="none", destination="N/A", ability="null", item="nothing")
check("placeholders blank", i.target == "" and i.destination == "" and i.ability == "" and i.item == "")
check("real kept", ActionIntent(kind="talk", target="bob").target == "bob")
check("contradiction caught", voice_rules.contradicts_nothing("Gold coins spill into your purse, heavy and bright."))
check("plain text ok", not voice_rules.contradicts_nothing("You search, but find nothing at all."))
check("extreme cha", (lambda v: v["charisma"] == 30 and sum(v.values()) == stats.TOTAL and stats.check_allocation(v) is None)(
    stats.from_priorities(["charisma"], extreme=True)))
check("wants_extreme", stats.wants_extreme("everything into charisma, as far past the limit as possible"))
check("normal template", sum(stats.from_priorities(["strength"]).values()) == stats.TOTAL)

class S:
    def __init__(s, kind, **k):
        s.kind, s.target, s.ability, s.summary = kind, k.get("target", ""), "", ""
        s.item = s.ware = s.destination = s.speech = ""
    def model_dump(s, exclude=()):
        return {"kind": s.kind, "target": s.target}
plan = [S("work", target="")]
sit = ia.Situation(present={"a": "A"})
check("work no offer flagged", "work_without_offer" in ia.risk_flags("work for 5 gold", plan, sit))
sit.workers = {"a"}
check("work with offer calm", "work_without_offer" not in ia.risk_flags("work for 5 gold", plan, sit))

class Ask:
    def meaning(s, t, sit): return "x"
    def compare(s, t, m, d, r): return False, "no"
    def propose(s, t, h): return [S("talk", target="a"), S("talk", target="a2")]
sit2 = ia.Situation(present={"a": "A", "a2": "B"})
res = ia.audit("work for 5 gold", [S("work")], sit2, Ask())
check("audit may not add steps", res.status != "changed" or len(res.plan) <= 1)
print("FAILED: " + ", ".join(bad) if bad else "all ok")
sys.exit(1 if bad else 0)
