"""Slot-based ability creation: the plan is always valid, and the whole pipeline (faked model) yields abilities that match their slots."""
import random, sys, collections, json
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from core.models import Archetype, Effect, UseContext
from llm.contracts import ClassInterpretation, ActiveSet, SlotNames
from engine import ability_slots as AS, ability_traits as AT, field
from character import creation
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

def interp(arch, fams, focus="balanced", pack=False, constraints=()):
    return ClassInterpretation(archetype=Archetype(arch), custom_class="X", combat_identity="x", themes=["spear", "sky"], summary="x",
                               families=list(fams), focus=focus, uses_companions=pack, constraints=list(constraints),
                               summoner=pack and bool(set(fams) & {"summoner", "necromancer"}))    # a conjurer makes summons; a tamer keeps companions
CLASSES = [("warrior", ["warrior"], "combat", False, []), ("warrior", ["warrior", "paladin"], "balanced", False, []),
           ("mage", ["mage"], "combat", False, []), ("mage", ["mage", "warlock"], "social", False, []),
           ("rogue", ["rogue"], "balanced", False, []), ("rogue", ["rogue", "bard"], "social", False, []),
           ("support", ["healer"], "balanced", False, []), ("support", ["healer", "druid"], "social", False, []),
           ("mage", ["necromancer", "summoner"], "balanced", True, []), ("warrior", ["ranger", "druid"], "combat", True, []),
           ("support", ["summoner", "leader"], "social", True, []), ("warrior", ["artisan"], "balanced", False, []),
           ("mage", ["mage"], "balanced", False, ["avoids melee combat"]), ("rogue", ["ranger"], "combat", False, ["never uses ranged attacks"])]

problems = collections.Counter()
chan = collections.Counter(); chan_runs = collections.Counter()
runs = 0
for arch, fams, focus, pack, cons in CLASSES:
    ic = interp(arch, fams, focus, pack, cons)
    minimum = creation.MIN_NONCOMBAT_ACTIVES[focus]
    for seed in range(60):
        rng = random.Random(seed)
        offers = AT.draw_offers(ic, rng, min_functions=minimum)
        slots = AS.plan(ic, offers, minimum, rng)
        runs += 1
        tag = f"{arch}/{'+'.join(fams)}/{focus}/{pack}/{seed}"
        def bad_(why): problems[why] += 1; (problems[why] <= 1) and print("   ", why, tag)
        if len(slots) != 15 or sorted(s["n"] for s in slots) != list(range(1, 16)): bad_("15 numbered slots"); continue
        riders = [s["rider"] for s in slots if s["rider"]]; shapes = [s["shape"] for s in slots if s["shape"]]
        if len(set(riders)) != len(riders) or len(set(shapes)) != len(shapes): bad_("a rider or shape repeated")
        n_expr = sum(1 for s in slots if (s.get("expressions") or s.get("maneuver")) and s["effect"] in ("damage", "control"))
        if len(set(riders)) + n_expr < min(3, len(offers["riders"])): bad_("fewer than 3 riders or expressions")
        if any(s["rider"] and s.get("expressions") and s["effect"] in ("damage", "control") for s in slots): bad_("rider beside an expression")
        _SC, _EL = __import__("engine.spellcraft", fromlist=["x"]), __import__("engine.elements", fromlist=["x"])
        if any(e and _SC.EXPR[e]["element"] not in [s.get("element")] + _EL.neighbors(s.get("element")) for s in slots for e in s.get("expressions") or []):
            bad_("expression from beyond the element's neighbors (f266)")
        n_forms = sum(1 for s in slots if s.get("martial_form") in ("flurry", "sweep"))       # an old multi-hit or sweeping shape became a form (f233)
        if len(set(shapes)) + n_forms < min(2, len(offers["shapes"])): bad_("fewer than 2 shapes")
        if any(s.get("martial_form") == "flurry" and not (2 <= s["hits"] <= 6) for s in slots): bad_("flurry hits out of range")
        if any(s.get("resource") == "stamina" and not s.get("channel") and s["effect"] in ("damage", "control") and s["rider"] for s in slots): bad_("a technique with a chance rider")
        if sum(1 for s in slots if s["rider"] or s["shape"]) > AT.T["max_decorated"]: bad_("over decorated")
        if any(s["rider"] and s["shape"] for s in slots): bad_("rider and shape together")
        buffs = [s for s in slots if s["effect"] == "buff"]
        if not (1 <= len(buffs) <= AT.T["max_buffs"]) or len({s["buff"] for s in buffs}) != len(buffs): bad_("buff count or repeat")
        fns = [s["field_use"] for s in slots if s["field_use"]]
        if len(fns) != len(set(fns)) or any(f not in offers["functions"] for f in fns): bad_("function repeat or not offered")
        outside = sum(1 for s in slots if s["context"] != "combat")
        if outside < minimum: bad_(f"only {outside} usable outside combat, need {minimum}")
        if sum(1 for s in slots if s["tier"] == "heavy") > 3: bad_("over 3 heavy")
        for s in slots:
            if s["shape"] and (s["effect"] != "damage" or s["reach"] == "area"): bad_("shape on wrong slot")
            if s["rider"] and s["effect"] not in AT.RIDERS[s["rider"]]["applies"]: bad_("rider on wrong effect")
            if s["shape"] and AT.SHAPES[s["shape"]].get("reach") and s["reach"] not in AT.SHAPES[s["shape"]]["reach"]: bad_("shape reach")
            if s["rider"] and AT.RIDERS[s["rider"]].get("reach") and s["reach"] not in AT.RIDERS[s["rider"]]["reach"]: bad_("rider reach")
            if s["effect"] in ("buff", "defense", "mobility") and s["reach"] != "self": bad_("self slot with reach")
            if s["field_use"] and s["effect"] in ("healing", "crafting", "summon"): bad_("selfish slot with a function")
            if s["effect"] == "damage" and not s["field_use"] and s["context"] != "combat": bad_("damage out of combat")
        forb = AS.forbidden_reach(ic)
        if any(s["reach"] in forb for s in slots if s["effect"] in ("damage", "control")): bad_("constraint reach broken")
        if ic.summoner and sum(s.get("summon_form") == "bound" for s in slots) != 1: bad_("summoner without exactly one Bound summon")
        if not ic.summoner and any(s["effect"] == "summon" for s in slots): bad_("summons for a class that does not make them")
        if pack:
            if sum(s["effect"] == "command" for s in slots) < 1: bad_("companion class without commands")
            cm = [s["command"] for s in slots if s["effect"] == "command"]
            if len(cm) != len(set(cm)) or not cm: bad_("commands")
        else:
            if any(s["effect"] in ("summon", "command") for s in slots): bad_("companion slot for a solo class")
        if arch == "support" and not any(s["effect"] == "healing" for s in slots): bad_("healer without healing")
        if sum(s["effect"] == "damage" for s in slots) < 1: bad_("no damage at all")
        if any(s["effect"] == "damage" for s in slots) and not pack and sum(s["effect"] == "damage" for s in slots) < 2: bad_("one damage")
        if arch == "warrior" and not [f for f in fams if f in ("paladin", "druid", "ranger")] and any(s["resource"] == "mana" and not s["channel"] and s["effect"] != "buff" for s in slots): bad_("warrior with mana")
        if any(s["channel"] and not (s["effect"] == "damage" and s["resource"] == "mana" and s["reach"] in ("melee", "extended")) for s in slots): bad_("a channeled slot that is not a melee mana strike")
        chan[(arch, tuple(fams), pack)] += sum(1 for s in slots if s["channel"]); chan_runs[(arch, tuple(fams), pack)] += 1
        if arch == "mage" and any(s["resource"] == "stamina" for s in slots) and not pack: bad_("mage with stamina")
        # the whole thing builds through the existing validator
        props = []
        for s in slots:
            from llm.contracts import ActiveProposal
            kw = dict(name=f"N{s['n']}", description="d", effect=s["effect"], tier=s["tier"], reach=s["reach"], resource=s["resource"],
                      context=s["context"], rider=s["rider"], shape=s["shape"], buff=s["buff"], command=s["command"], field_use=s["field_use"])
            if s["effect"] == "summon": kw["summons"] = dict(name="C", description="d", kind="beast", role="striker")
            props.append(kw)
        try:
            res = ActiveSet.model_validate({"skills": props}, context={"uses_companions": pack, "summoner": ic.summoner, "min_noncombat": minimum, "offers": offers, "planned": True})
            got = [(p.effect.value, p.rider, p.shape, p.buff, p.field_use, p.reach.value, p.context.value) for p in res.skills]
            want = [(s["effect"], s["rider"], s["shape"], s["buff"], s["field_use"], s["reach"], s["context"]) for s in slots]
            # a planned set goes through untouched (f249): the old validator no longer adds riders or shapes of its own
            if got != want:
                bad_("validator changed the plan")
                if problems["validator changed the plan"] <= 3:
                    for g, w in zip(got, want):
                        if g != w: print("       got", g, "want", w)
        except Exception as e:
            bad_("validator rejected the plan: " + str(e)[:150])
for k in sorted(chan):
    print("   channeled per character", k, round(chan[k] / chan_runs[k], 2))
fighter_k = lambda k: k[0] in ("warrior", "rogue") and not k[2]
hy = [chan[k] / chan_runs[k] for k in chan if fighter_k(k) and set(k[1]) & set(AS.P["hybrid_families"])]
ot = [chan[k] / chan_runs[k] for k in chan if not (fighter_k(k) and set(k[1]) & set(AS.P["hybrid_families"]))]
check("every hybrid fighter gets a channeled attack on average", all(v >= 1 for v in hy), hy)
check("casters, tamers and plain fighters never get one (f249, f260: a channeled strike needs a melee weapon)", all(v == 0 for v in ot), ot)
odd = collections.Counter()
for arch, fams, focus, pack, cons in CLASSES:
    ic = interp(arch, fams, focus, pack, cons)
    for seed in range(40):
        rng = random.Random(seed)
        plan_ = AS.plan(ic, AT.draw_offers(ic, rng, min_functions=creation.MIN_NONCOMBAT_ACTIVES[focus]), creation.MIN_NONCOMBAT_ACTIVES[focus], rng)
        ctl_ex = [e for s in plan_ if s["effect"] == "control" for e in s.get("expressions") or []]
        if len(ctl_ex) != len(set(ctl_ex)): odd["two control spells that do the same thing"] += 1
        for s in plan_:
            if s.get("shape") == "chain" and s["resource"] == "stamina" and not s.get("channel"): odd["a technique that chains"] += 1
            if s.get("shape") == "ricochet" and s["reach"] != "ranged": odd["ricochet not ranged"] += 1
            if s.get("shape") == "cleave" and s["reach"] not in ("melee", "extended"): odd["cleave not melee"] += 1
            if s.get("martial_form") == "counter" and s["reach"] not in ("melee", "extended"): odd["a counter at range"] += 1
            from engine import martial as _MA
            mr = (_MA.MANEUVERS.get(s.get("maneuver", "")) or {}).get("reach")
            if mr and s["reach"] not in mr: odd[f"{s['maneuver']} at {s['reach']} reach"] += 1
            if s.get("buff") == "bladeward" and arch in ("warrior", "rogue"): odd["Bladeward on a fighter"] += 1
            if s.get("buff") in ("imbue", "envenom", "acidcoat") and arch not in ("warrior", "rogue"): odd["a weapon buff on a caster (f267)"] += 1
check("techniques cleave or ricochet, never chain; counters and grabs are close; no Bladeward for fighters (f251)", not odd, dict(odd))
# ---- a fighter with an element carries it in the weapon; a fighter with a casting family is a mixed class (f252)
def _el(arch, fams, el):
    return ClassInterpretation(archetype=Archetype(arch), custom_class="X", combat_identity="x", themes=["x"], summary="x",
                               families=list(fams), focus="balanced", elements=list(el))
short = collections.Counter()
for name, ic in (("fire swordsman", _el("warrior", ["warrior"], ["fire"])), ("lightning samurai", _el("warrior", ["warrior", "mage"], ["lightning"])),
                 ("venom rogue", _el("rogue", ["rogue"], ["poison"]))):
    for seed in range(30):
        rng = random.Random(seed)
        offers = AT.draw_offers(ic, rng, min_functions=5)
        sl = AS.plan(ic, offers, 5, rng)
        if not any((s.get("buff") == "imbue" and s.get("element") in ic.elements) or AS.COATINGS.get(ic.elements[0]) == s.get("buff") for s in sl): short[f"{name}: no weapon buff of its element"] += 1
        if not any(s.get("channel") and s.get("element") in ic.elements for s in sl): short[f"{name}: no channeled strike of its element"] += 1
        if any(s.get("buff") == "frostarmor" for s in sl) and "cold" not in ic.elements: short[f"{name}: Frost Armor off its element"] += 1
        if name == "lightning samurai" and not any(s["resource"] == "mana" and s["effect"] in ("damage", "control") and not s.get("channel") for s in sl):
            short["lightning samurai: no spells of its own"] += 1
        if any(b not in offers["buffs"] for b in (s.get("buff") for s in sl) if b): short[f"{name}: a buff not on offer"] += 1
check("an elemental fighter gets its element through the weapon; a fighter with a casting family casts too", not short, dict(short))
check(f"{runs} plans across {len(CLASSES)} class types are all valid", not problems, dict(problems))

# ---- the whole pipeline with a faked model ----
from llm import gateway
import character.creation as cr
calls = []
def fake_generate_factory(mode):
    def fake(task, system, user, schema, **kw):
        calls.append((task, schema.__name__, kw.get("retries")))
        ctx = kw["validation_context"]
        if schema is SlotNames:
            slots = ctx["slots"]
            out = []
            for s in slots:
                base = {"damage": "Strike", "control": "Hinder", "buff": "Surge", "defense": "Guard", "mobility": "Dash", "healing": "Mend",
                        "summon": "Call", "command": "Signal", "crafting": "Forge", "influence": "Sway", "utility": "Trick"}[s["effect"]]
                desc = "A plain move."
                if s["shape"] and AT.SHAPES[s["shape"]].get("multi"):
                    desc = "A flurry of strikes."
                if mode == "bad" and s["shape"] and AT.SHAPES[s["shape"]].get("multi"):
                    desc = "A single clean cut."
                e = {"slot": s["n"], "name": f"{base} {s['n']}", "description": desc}
                if s["effect"] == "summon":
                    e["summons"] = {"name": "Pal", "description": "d", "kind": "beast", "role": "striker"}
                out.append(e)
            try:
                return schema.model_validate({"skills": out}, context=ctx)
            except ValueError as e:
                raise cr.LLMError(str(e))
        raise cr.LLMError("single call")
    return fake
for mode in ("good", "bad"):
    for arch, fams, focus, pack, cons in CLASSES[:6] + CLASSES[8:11]:
        ic = interp(arch, fams, focus, pack, cons)
        calls.clear()
        cr.generate = fake_generate_factory(mode)
        try:
            abilities = cr.generate_actives(ic, random.Random(7))
            ok = len(abilities) == 15
        except Exception as e:
            ok = False; print("   ", mode, arch, fams, repr(e)[:200])
        if not ok:
            check(f"pipeline {mode} {arch}/{fams}", False); continue
        names = [a.name for a in abilities]
        ok = len(set(names)) == 15
        mins = creation.MIN_NONCOMBAT_ACTIVES[focus]
        outside = sum(1 for a in abilities if a.context != UseContext.COMBAT)
        ok = ok and outside >= mins and not any(a.rider and (a.maneuver or a.expressions) for a in abilities)   # nothing added on top of the plan (f249)
        if mode == "bad":
            ok = ok and ((len(calls) == 2 and calls[1][2] == 1) or len(calls) == 1)
        check(f"pipeline {mode} {arch}/{'+'.join(fams)}/{focus}", ok, str([(c[1], c[2]) for c in calls]))

# strict contract rejects mismatches, lenient accepts
ic = interp("warrior", ["warrior"], "combat")
rng = random.Random(3)
offers = AT.draw_offers(ic, rng, min_functions=3)
slots = AS.plan(ic, offers, 3, rng)
def build(descs, strict=True):
    out = [{"slot": s["n"], "name": f"Move {s['n']}", "description": descs.get(s["n"], "A plain move.")} for s in slots]
    for o, s in zip(out, slots):
        if s["effect"] == "summon": o["summons"] = {"name": "P", "description": "d", "kind": "beast", "role": "striker"}
    return SlotNames.model_validate({"skills": out}, context={"slots": slots, "strict": strict})
single = next(s for s in slots if s["effect"] == "damage" and not s["shape"] and s["reach"] != "area" and s.get("martial_form") not in ("flurry", "sweep"))
try:
    build({single["n"]: "A flurry of rapid blows."}); check("a flurry on a single-blow slot is refused", False)
except ValueError as e:
    check("a flurry on a single-blow slot is refused", "ONE blow" in str(e), str(e)[:100])
build({single["n"]: "A flurry of rapid blows."}, strict=False); check("lenient mode takes it", True)
multi = next((s for s in slots if s["shape"] and AT.SHAPES[s["shape"]].get("multi")), None)
if multi:
    try:
        build({multi["n"]: "A calm single thrust."}); check("a single thrust on a multi-hit slot is refused", False)
    except ValueError as e:
        check("a single thrust on a multi-hit slot is refused", "SEVERAL" in str(e))
try:
    build({1: "x 12"}); check("numbers refused", False)
except ValueError:
    check("numbers refused", True)
# the prompt shows each slot's mechanic
txt = AS.slot_lines(slots)
check("prompt lists all 15 with mechanics", all(f"\n{n}. " in "\n" + txt for n in range(1, 16)) and "does:" in txt)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
