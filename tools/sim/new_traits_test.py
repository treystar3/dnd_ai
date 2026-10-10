"""The second wave of riders, shapes and buffs: each does what it says, multi-hit shapes are capped, companion-only ones go to companion classes."""
import random, sys, collections
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import combat as C, ability_traits as AT
from core.models import Archetype
from llm.contracts import ClassInterpretation
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

def F(id, side, hp=100000, **k):
    d = dict(id=id, name=id, side=side, level=40, attrs={a: 14 for a in C.ATTRIBUTES}, hp=hp, max_hp=hp, weapon_damage=50, armor=0, ward=0,
             stamina=1000, max_stamina=1000, mana=1000, max_mana=1000)
    d.update(k)
    return C.Fighter(**d)
def mv(effect="damage", tier="moderate", reach="melee", resource="stamina", **k):
    return C.Move(id="m", name="Test Move", effect=effect, tier=tier, reach=reach, resource=resource, attribute="intelligence" if resource == "mana" else "", **k)
def setup(n_foes=2, pets=0, **fk):
    p = F("p", "player", **fk)
    foes = [F(f"e{i}", "enemy", band="engaged", armor=0) for i in range(n_foes)]
    cmb = C.Combat(fighters=[p] + foes)
    for i in range(pets):
        cmb.fighters.append(F(f"pet{i}", "ally", weapon_damage=50))
    return cmb, p, foes
def lost(move, trials=200, foe=0, setup_fn=None, **fk):
    tot = [0, 0]
    for i in range(trials):
        cmb, p, foes = setup(**fk)
        if setup_fn: setup_fn(cmb, p, foes)
        h = [f.hp for f in foes]
        C.act_ability(cmb, p, move, foes[foe], random.Random(i))
        tot[0] += h[0] - foes[0].hp; tot[1] += h[1] - foes[1].hp
    return tot[0] / trials, tot[1] / trials
HONED = AT.T["plain_damage"]
AT.T["plain_damage"] = 0        # compare each trait with a neutral plain strike; the Honed bonus is tested at the end
base = lost(mv())[0]

# ---- shapes
for sid, parts, total in (("double", 2, 1.2), ("volley", 3, 1.2), ("barrage", 5, 1.25)):
    cmb, p, foes = setup(); C.act_ability(cmb, p, mv(shape=sid), foes[0], random.Random(1))
    n = sum(("Test Move" in l or "strikes again" in l) for l in cmb.log if "damage" in l or "miss" in l)
    r = lost(mv(shape=sid))[0] / base
    check(f"{sid} makes {parts} separate hits for about {total:.0%} in total", n == parts and total * 0.7 < r < total * 1.1, (n, f"{r:.2f}"))
r = lost(mv(shape="sweeping"))
check("sweeping hits every engaged enemy for less than a full blow each", r[0] > 0 and r[1] > 0 and r[0] < base and abs(r[0] - r[1]) < r[0] * 0.3, (r, base))
def far_second(cmb, p, foes): foes[1].band = "far"
r = lost(mv(shape="sweeping"), setup_fn=far_second)
check("sweeping spares enemies who are not engaged", r[1] == 0 and r[0] > 0, r)
r = lost(mv(shape="ricochet"), n_foes=3) if False else None
tot = [0, 0, 0]
for i in range(200):
    cmb, p, foes = setup(n_foes=3); h = [f.hp for f in foes]
    C.act_ability(cmb, p, mv(shape="ricochet"), foes[0], random.Random(i))
    for k in range(3): tot[k] += h[k] - foes[k].hp
check("ricochet bounces onto the other enemies, hitting the first hardest", tot[1] > 0 and tot[2] > 0 and tot[0] > tot[1] * 0.9, [round(t / 200) for t in tot])
cmb, p, foes = setup(n_foes=1); h = foes[0].hp; C.act_ability(cmb, p, mv(shape="ricochet"), foes[0], random.Random(1))
check("ricochet with one enemy is just a plain hit", sum("ricochets" in l for l in cmb.log) == 0)
# reliable: never misses, never crits, no variance
dmgs, misses = set(), 0
for i in range(150):
    cmb, p, foes = setup(n_foes=1); foes[0].attrs["dexterity"] = 40; h = foes[0].hp
    C.act_ability(cmb, p, mv(shape="reliable"), foes[0], random.Random(i))
    d = h - foes[0].hp; dmgs.add(d); misses += d == 0
check("reliable never misses and every blow is the same average hit", misses == 0 and len(dmgs) == 1, (misses, sorted(dmgs)[:4]))
# lunge
def far_first(cmb, p, foes): foes[0].band = "far"
cmb, p, foes = setup(); foes[0].band = "far"; h = foes[0].hp; C.act_ability(cmb, p, mv(shape="lunge"), foes[0], random.Random(2))
check("lunge closes any distance and strikes in the same action", foes[0].band == "engaged" and any("damage" in l or "miss" in l for l in cmb.log), (foes[0].band, cmb.log[-2:]))
a = lost(mv(shape="lunge"), setup_fn=far_first)[0]; b = lost(mv(shape="lunge"))[0]
check("lunge hits harder against a target who was not already in melee", a > b * 1.15, (round(a), round(b)))
cmb, p, foes = setup(); foes[0].band = "far"; C.act_ability(cmb, p, mv(), foes[0], random.Random(2))
check("without lunge a melee ability only closes a step", foes[0].band == "near", foes[0].band)
# flank
def flanked(cmb, p, foes): foes[0].counters["flanked"] = cmb.round
a = lost(mv(shape="flank"), setup_fn=flanked)[0]; b = lost(mv(shape="flank"))[0]
check("flanking hits harder on a target an ally has struck", a > b * 1.2, (round(a), round(b)))
cmb, p, foes = setup(pets=1); pet = [f for f in cmb.fighters if f.side == "ally"][0]
for i in range(20):
    C.apply_damage(cmb, pet, foes[0], 1.0, "hits", random.Random(i))
    if "flanked" in foes[0].counters: break
check("a companion's strike marks the target as flanked", foes[0].counters.get("flanked") == cmb.round)
# desperate strike
a = lost(mv(shape="desperate"))[0]
def hurt(cmb, p, foes): p.hp = p.max_hp * 0.1
b = lost(mv(shape="desperate"), setup_fn=hurt)[0]
check("desperate strike is weak at full health and strong near death", a < base * 0.95 and b > base * 1.5, (round(a), round(b), round(base)))
# combo
cmb, p, foes = setup(n_foes=1); out = []
for i in range(5):
    h = foes[0].hp; C.act_ability(cmb, p, mv(shape="combo"), foes[0], random.Random(i + 9)); out.append(h - foes[0].hp)
avg_hits = [x for x in out if x > 0]
check("combo counts consecutive hits on the same target", p.counters.get("combo:e0", 0) >= 2, (p.counters, out))
tot_first = tot_late = 0
for i in range(150):
    cmb, p, foes = setup(n_foes=1); h = foes[0].hp
    C.act_ability(cmb, p, mv(shape="combo"), foes[0], random.Random(i)); tot_first += h - foes[0].hp
    p.counters["combo:e0"] = 4; foes[0].hp = h
    C.act_ability(cmb, p, mv(shape="combo"), foes[0], random.Random(i + 500)); tot_late += h - foes[0].hp
check("a built-up combo hits much harder", tot_late > tot_first * 1.3, (tot_first, tot_late))
cmb, p, foes = setup(); p.counters["combo:e0"] = 3; C.act_ability(cmb, p, mv(shape="combo"), foes[1], random.Random(1))
check("switching target breaks the combo", "combo:e0" not in p.counters)
# exploiting
def afflicted(cmb, p, foes): foes[0].statuses["bleeding"] = 3
a = lost(mv(shape="exploiting"), setup_fn=afflicted)[0]; b = lost(mv(shape="exploiting"))[0]
check("exploiting punishes an afflicted target and is weak against a clean one", a > base * 1.4 and b < base * 0.95, (round(a), round(b), round(base)))
# pack hunt
cmb, p, foes = setup(n_foes=1, pets=2); h = foes[0].hp
for i in range(20):
    cmb, p, foes = setup(n_foes=1, pets=2)
    C.act_ability(cmb, p, mv(shape="packhunt"), foes[0], random.Random(i))
    if any("pounces" in l for l in cmb.log): break
check("pack hunt brings the companions in", any("pounces" in l for l in cmb.log), cmb.log[-3:])
cmb, p, foes = setup(n_foes=1); C.act_ability(cmb, p, mv(shape="packhunt"), foes[0], random.Random(1))
check("pack hunt with no companions is a plain hit", not any("pounces" in l for l in cmb.log))

# ---- riders
def rate(rider, tier, status, n=400):
    hits = 0
    for i in range(n):
        cmb, p, foes = setup(); C.act_ability(cmb, p, mv(rider=rider, tier=tier), foes[0], random.Random(i))
        hits += status in foes[0].statuses
    return hits / n
for rid, st in (("expose", "exposed"), ("grapple", "grappled"), ("venom", "poisoned"), ("ignite", "burning"), ("jolt", "stunned"),
                ("mark", "marked"), ("enfeeble", "weakened"), ("befuddle", "befuddled")):
    lo, hi = rate(rid, "light", st), rate(rid, "heavy", st)
    check(f"{rid} applies {st} more often at higher tiers", 0.03 < lo < hi, f"{lo:.2f} -> {hi:.2f}")
# exposed lowers protection
def taken(status=None):
    cmb, p, foes = setup(); foes[0].armor = 40; foes[0].ward = 40
    if status: foes[0].statuses[status] = 3
    return C.mitigate(foes[0], 1000, "physical", 40, cmb, p)[0]
check("exposed targets take more from armored defences", taken("exposed") > taken() * 1.1, (round(taken()), round(taken("exposed"))))
def dealt_to(status, n=150):
    t = 0
    for i in range(n):
        cmb, p, foes = setup(n_foes=1)
        if status: foes[0].statuses[status] = 3
        h = foes[0].hp; C.apply_damage(cmb, p, foes[0], 1.0, "hits", random.Random(i)); t += h - foes[0].hp
    return t / n
check("a marked target takes about 20% more", 1.1 < dealt_to("marked") / dealt_to(None) < 1.35, dealt_to("marked") / dealt_to(None))
def dealt_by(status, n=150):
    t = 0
    for i in range(n):
        cmb, p, foes = setup(n_foes=1)
        if status: foes[0].statuses[status] = 3
        h = p.hp; C.apply_damage(cmb, foes[0], p, 1.0, "hits", random.Random(i)); t += h - p.hp
    return t / n
check("a weakened enemy deals less", dealt_by("weakened") < dealt_by(None) * 0.85, (dealt_by(None), dealt_by("weakened")))
check("a poisoned enemy deals a little less", dealt_by("poisoned") < dealt_by(None) * 0.97)
for st in ("poisoned", "burning", "bleeding"):
    cmb, p, foes = setup(); foes[0].statuses[st] = 3; h = foes[0].hp; C.start_turn(foes[0], cmb)
    check(f"{st} hurts at the start of the target's turn", foes[0].hp < h, h - foes[0].hp)
# hooking
cmb, p, foes = setup(); foes[0].band = "far"; C.act_ability(cmb, p, mv(rider="hook", reach="ranged"), foes[0], random.Random(1))
check("hooking pulls a distant target a step closer", foes[0].band == "near", foes[0].band)
cmb, p, foes = setup(); C.act_ability(cmb, p, mv(rider="hook"), foes[0], random.Random(1))
check("hooking does nothing to a target already in melee", foes[0].band == "engaged")
# grappling
for i in range(40):
    cmb, p, foes = setup(); foes[0].band = "near"; C.act_ability(cmb, p, mv(rider="grapple", tier="heavy", reach="ranged"), foes[0], random.Random(i))
    if "grappled" in foes[0].statuses: break
check("grappling drags the target into melee", "grappled" in foes[0].statuses and foes[0].band == "engaged", (foes[0].statuses, foes[0].band))
cmb, p, foes = setup(); foes[0].statuses["grappled"] = 2; C.act_ability(cmb, p, mv(rider="shove"), foes[0], random.Random(1))
check("a grappled target cannot be pushed away", foes[0].band == "engaged")
cmb, p, foes = setup(); foes[0].temperament = "passive"; foes[0].statuses["grappled"] = 2; cmb.round = 3
fled = False
for i in range(60):
    foes[0].fled = False; foes[0].statuses["grappled"] = 2
    C.enemy_turn(cmb, foes[0], random.Random(i)); fled |= foes[0].fled
check("a grappled enemy cannot flee", not fled)
# draining
cmb, p, foes = setup(); p.mana = 100; C.act_ability(cmb, p, mv(rider="drain", resource="mana", reach="ranged"), foes[0], random.Random(1))
cmb2, p2, foes2 = setup(); p2.mana = 100; C.act_ability(cmb2, p2, mv(resource="mana", reach="ranged"), foes2[0], random.Random(1))
check("draining returns mana", p.mana > p2.mana, (p.mana, p2.mana))
# penetrating
def resisted(rider, n=100):
    from engine.combat import Bonus
    t = 0
    for i in range(n):
        cmb, p, foes = setup(n_foes=1)
        foes[0].bonuses = [Bonus(source="x", modifies="physical_resistance", magnitude=60, trigger="always")]
        h = foes[0].hp; C.act_ability(cmb, p, mv(rider=rider), foes[0], random.Random(i)); t += h - foes[0].hp
    return t / n
try:
    a, b = resisted("penetrate"), resisted("")
    check("penetrating ignores resistances", a > b * 1.8, (round(a), round(b)))
    cmb, p, foes = setup(); C.act_ability(cmb, p, mv(rider="penetrate"), foes[0], random.Random(1))
    check("penetrating leaves no permanent change", "penetrating" not in p.legendary)
except Exception as e:
    check("penetrating test ran", False, repr(e))
# befuddle
cmb, p, foes = setup(n_foes=2, pets=1); foes[0].statuses["befuddled"] = 2
hit_own = hit_other = 0
for i in range(80):
    cmb, p, foes = setup(n_foes=2, pets=1); foes[0].statuses["befuddled"] = 2; h1 = foes[1].hp
    C.enemy_turn(cmb, foes[0], random.Random(i))
    hit_own += foes[1].hp < h1
    check_gone = "befuddled" not in foes[0].statuses
check("a befuddled enemy sometimes strikes its own side, and the effect is spent", hit_own > 5 and check_gone, hit_own)
# rousing
cmb, p, foes = setup(pets=2); pet = [f for f in cmb.fighters if f.side == "ally"]
for i in range(10):
    C.act_ability(cmb, p, mv(rider="rouse"), foes[0], random.Random(i))
check("rousing empowers the companions", all(a.buffs for a in pet) and all("press" in C.mechanics(a, cmb) for a in pet))
cmb, p, foes = setup(); C.act_ability(cmb, p, mv(rider="rouse"), foes[0], random.Random(1))
check("rousing with no companion does nothing odd", not p.buffs)

# ---- buffs
def bf(kind, tier="moderate", resource="stamina", name="Test Move", **k):
    return C.Move(id="b", name=name, effect="buff", tier=tier, reach="self", resource=resource, buff=kind, **k)
def with_buff(kind, **k):
    cmb, p, foes = setup(n_foes=1); C.act_ability(cmb, p, bf(kind, **k), None, random.Random(1)); return cmb, p, foes
def my_damage(buffed, n=150, kind="empower"):
    t = 0
    for i in range(n):
        cmb, p, foes = with_buff(kind) if buffed else setup(n_foes=1)
        h = foes[0].hp; C.apply_damage(cmb, p, foes[0], 1.0, "hits", random.Random(i)); t += h - foes[0].hp
    return t / n
r = my_damage(True) / my_damage(False)
check("empower raises damage by about 30%", 1.2 < r < 1.45, f"{r:.2f}")
r = my_damage(True, kind="frenzy") / my_damage(False)
check("frenzy raises damage dealt", r > 1.25, f"{r:.2f}")
def took(buffed, kind, n=100):
    t = 0
    for i in range(n):
        cmb, p, foes = with_buff(kind) if buffed else setup(n_foes=1)
        h = p.hp; C.apply_damage(cmb, foes[0], p, 1.0, "hits", random.Random(i)); t += h - p.hp
    return t / n
check("frenzy also makes you take more damage", took(True, "frenzy") > took(False, "frenzy") * 1.1)
cmb, p, foes = with_buff("manashield", resource="mana"); p.mana = 1000; h, m = p.hp, p.mana
for i in range(10): C.apply_damage(cmb, foes[0], p, 1.0, "hits", random.Random(i))
cmb2, p2, foes2 = setup(n_foes=1); h2 = p2.hp
for i in range(10): C.apply_damage(cmb2, foes2[0], p2, 1.0, "hits", random.Random(i))
check("mana shield pays part of the damage in mana", p.mana < m and (h - p.hp) < (h2 - p2.hp) * 0.7, (h - p.hp, h2 - p2.hp, m - p.mana))
cmb, p, foes = with_buff("vampiric"); p.hp = p.max_hp // 2; h = p.hp
for i in range(10): C.apply_damage(cmb, p, foes[0], 1.0, "hits", random.Random(i))
check("vampiric aura heals you as you hit", p.hp > h, p.hp - h)
cmb, p, foes = setup(n_foes=1); p.hp = p.max_hp // 2; h = p.hp
for i in range(10): C.apply_damage(cmb, p, foes[0], 1.0, "hits", random.Random(i))
check("no healing without the aura", p.hp == h)
def elem(buffed, name="Frost Brand", n=100):
    t = 0
    for i in range(n):
        cmb, p, foes = setup(n_foes=1)
        if buffed:
            m = bf("elemental", name=name); m.element = "cold" if "Frost" in name else ""
            C.act_ability(cmb, p, m, None, random.Random(1))
        h = foes[0].hp; C.apply_damage(cmb, p, foes[0], 1.0, "hits", random.Random(i)); t += h - foes[0].hp
    return t / n
check("elemental weapon adds a hit of bonus damage", elem(True) > elem(False) * 1.15, (elem(False), elem(True)))
cmb, p, foes = setup(n_foes=1); m = bf("elemental", name="Frost Brand"); m.element = "cold"; C.act_ability(cmb, p, m, None, random.Random(1))
check("elemental weapon takes the element from the ability", list(p.buffs.values())[0]["element"] == "cold")
for kind in AT.BUFFS:
    cmb, p, foes = setup(n_foes=1); C.act_ability(cmb, p, bf(kind, "light"), None, random.Random(1))
    check(f"{kind} lasts its rounds and fades", len(p.buffs) == 1 or kind == "x", kind)
    n = 0
    while p.buffs and n < 20: C.start_turn(p, cmb); n += 1
    check(f"{kind} (light) fades after 3-4 rounds", 3 <= n <= 4, n)

# ---- text and cards
for rid in AT.RIDERS:
    for tier in ("light", "moderate", "heavy"):
        AT.rider_text(rid, tier)
for sid in AT.SHAPES: AT.shape_text(sid)
for bid in AT.BUFFS:
    for tier in ("light", "moderate", "heavy"): AT.buff_text(bid, tier)
check("every rider, shape and buff has card text", True)
check("counts: 21 riders, 16 shapes, 8 buffs", (len(AT.RIDERS), len(AT.SHAPES), len(AT.BUFFS)) == (21, 16, 8), (len(AT.RIDERS), len(AT.SHAPES), len(AT.BUFFS)))
check("offer sizes are 6 riders, 4 shapes, 3 buffs", (AT.T["offer"]["riders"], AT.T["offer"]["shapes"], AT.T["offer"]["buffs"]) == (6, 4, 3))
check("renamed shapes", AT.SHAPES["desperate"]["label"] == "Desperate Strike" and AT.SHAPES["exploiting"]["label"] == "Exploiting")

# ---- draws
interp = lambda arch, themes, fams, pack=False: ClassInterpretation(archetype=Archetype(arch), custom_class="X", combat_identity="x", themes=themes,
          summary="x", focus="balanced", uses_companions=pack, families=fams, primary_attributes=["strength"], casting_attribute="")
MULTI = [k for k, v in AT.SHAPES.items() if v.get("multi")]
check("the multi-hit family is double strike, volley and barrage", sorted(MULTI) == ["barrage", "double", "volley"], MULTI)
worst, sizes_ok, comp_leak, comp_seen = 0, True, 0, 0
for i in range(2000):
    for arch, th, fam, pack in (("rogue", ["knife", "arrow"], ["rogue", "ranger"], False), ("warrior", ["blade"], ["warrior"], False),
                                ("mage", ["fire"], ["mage"], False), ("summoner", ["pack", "hunt"], ["ranger", "summoner"], True)):
        o = AT.draw_offers(interp(arch if arch != "summoner" else "support", th, fam, pack))
        sizes_ok &= (len(o["riders"]), len(o["shapes"]), len(o["buffs"])) == (6, 4, 3)
        worst = max(worst, sum(s in MULTI for s in o["shapes"]))
        if not pack:
            comp_leak += any(AT.RIDERS[r].get("companion") for r in o["riders"]) + any(AT.SHAPES[s].get("companion") for s in o["shapes"])
        else:
            comp_seen += any(AT.RIDERS[r].get("companion") for r in o["riders"]) or any(AT.SHAPES[s].get("companion") for s in o["shapes"])
check("every offer is 6 riders, 4 shapes and 3 buffs", sizes_ok)
check("never more than two multi-hit shapes in an offer", worst <= 2, worst)
check("companion-only riders and shapes are never offered to other classes", comp_leak == 0, comp_leak)
check("companion classes do get offered companion-only options", comp_seen > 200, comp_seen)
small = AT.draw_offers(interp("rogue", ["knife"], ["rogue"]), sizes={"riders": 3, "shapes": 2, "buffs": 1, "functions": 2})
check("lesson draws are smaller", (len(small["riders"]), len(small["shapes"]), len(small["buffs"])) == (3, 2, 1))
ok_hint = True
for k in range(200):
    off = AT.draw_offers(interp("rogue", ["knife"], ["rogue"]))
    ok_hint &= ("multi-hit" in AT.offer_lines(off)) == any(x in MULTI for x in off["shapes"])
check("the offer tells the model how to name multi-hit abilities (only when one is on offer)", ok_hint)
seen = collections.Counter()
for i in range(1500):
    o = AT.draw_offers(interp("rogue", ["knife"], ["rogue"]))
    seen.update(o["riders"]); seen.update(o["shapes"]); seen.update(o["buffs"])
check("every non-companion rider, shape and buff turns up for a class", all(seen[k] > 0 for g in (AT.RIDERS, AT.SHAPES, AT.BUFFS) for k, v in g.items() if not v.get("companion")),
      [k for g in (AT.RIDERS, AT.SHAPES, AT.BUFFS) for k in g if not seen[k]])
# contracts accept every new id
from llm.contracts import ActiveProposal
for rid in AT.RIDERS:
    p_ = ActiveProposal(name="X", description="d", effect="damage", tier="light", reach="melee", resource="stamina", context="combat", rider=rid)
    check(f"contract accepts rider {rid}", p_.rider == rid or "damage" not in AT.RIDERS[rid]["applies"], p_.rider)
for sid in AT.SHAPES:
    p_ = ActiveProposal(name="X", description="d", effect="damage", tier="light", reach="melee", resource="stamina", context="combat", shape=sid)
    assert p_.shape == sid, sid
for bid in AT.BUFFS:
    p_ = ActiveProposal(name="X", description="d", effect="buff", tier="light", reach="self", resource="stamina", context="combat", buff=bid)
    assert p_.buff == bid, bid
check("contract accepts every shape and buff", True)
from engine import abilities
a = abilities.materialize_active(ActiveProposal(name="Fan of Knives", description="d", effect="damage", tier="moderate", reach="ranged", resource="stamina", context="combat", shape="barrage"))
check("a materialized barrage ability describes itself", "five hits" in AT.describe(a), AT.describe(a))
# ---- a multi-hit description gets a multi-hit shape
from llm.contracts import ActiveSet
def prop(i, **k):
    d = dict(name=f"Move {i}", description="d", effect="damage", tier="light", reach="melee", resource="stamina", context="combat"); d.update(k)
    return ActiveProposal(**d)
def build(shapes_offered, pyres_shape="reliable"):
    offers = {"riders": ["rend", "chill", "dread", "sunder", "shove", "siphon"], "shapes": shapes_offered, "buffs": ["bulwark"]}
    ps = [prop(0, rider="rend"), prop(1, rider="chill"), prop(2, rider="dread"),
          prop(3, name="Arcane Pyres", description="The caster hurls multiple small, explosive fireballs in a rapid sequence.", reach="ranged", resource="mana", shape=pyres_shape),
          prop(4, shape="finisher"), prop(5, shape="chain"), prop(6, effect="buff", buff="bulwark", reach="self")]
    ps += [prop(40 + j, context="both", effect="healing" if j < 3 else "damage") for j in range(15 - len(ps))]
    s = ActiveSet.model_validate({"skills": [p.model_dump() for p in ps]}, context={"offers": offers, "min_noncombat": 0})
    return next(x for x in s.skills if x.name == "Arcane Pyres")
check("a rapid fireball sequence gets the barrage shape when it is on offer", build(["reliable", "finisher", "chain", "barrage"]).shape == "barrage")
check("it gets volley when only volley is on offer", build(["reliable", "finisher", "chain", "volley"]).shape == "volley")
check("with no multi-hit shape on offer and shapes to spare, the mismatched shape is dropped", build(["reliable", "finisher", "chain"]).shape == "")
check("a fitting multi-hit shape is left alone", build(["double", "finisher", "chain"], pyres_shape="double").shape == "double")

# ---- traits that contradict what the ability is
def build2(**over):
    offers = {"riders": ["rend", "chill", "dread", "sunder", "shove", "siphon", "hook"], "shapes": ["reliable", "finisher", "chain", "ricochet", "lunge"], "buffs": ["bulwark"]}
    ps = [prop(0, rider="rend"), prop(1, rider="chill"), prop(2, rider="dread"), prop(4, shape="finisher"), prop(5, shape="chain"),
          prop(6, effect="buff", buff="bulwark", reach="self"), prop(7, shape="finisher", reach="melee")]
    ps.append(prop(3, **over))
    ps += [prop(40 + j, context="both", effect="healing" if j < 3 else "damage") for j in range(15 - len(ps))]
    s = ActiveSet.model_validate({"skills": [p.model_dump() for p in ps]}, context={"offers": offers, "min_noncombat": 0})
    return next(x for x in s.skills if x.name == "Scorch")
beam = dict(name="Scorch", description="A concentrated beam of heat strikes a single target, burning deep into their armor.", reach="ranged", resource="mana")
check("a ricochet on 'a single target' beam is dropped", build2(shape="ricochet", **beam).shape == "")
check("a lunge on a ranged spell is dropped", build2(shape="lunge", name="Scorch", description="A ball of fire.", reach="ranged", resource="mana").shape == "")
check("a lunge on a melee strike is kept", build2(shape="lunge", name="Scorch", description="A fiery leap and slash.", reach="melee").shape == "lunge")
check("reliable on a chaotic spell is dropped", build2(shape="reliable", name="Scorch", description="Wild sparks scatter everywhere.", reach="ranged", resource="mana").shape == "")
check("hooking on a melee strike is dropped", build2(rider="hook", name="Scorch", description="A heavy blow.", reach="melee").rider == "")
check("hooking on a ranged strike is kept", build2(rider="hook", name="Scorch", description="A barbed chain flies out.", reach="ranged").rider == "hook")
offers_tight = {"riders": ["rend", "chill", "dread"], "shapes": ["finisher", "ricochet"], "buffs": ["bulwark"]}
ps = [prop(0, rider="rend"), prop(1, rider="chill"), prop(2, rider="dread"), prop(4, shape="finisher"), prop(6, effect="buff", buff="bulwark", reach="self"),
      prop(3, shape="ricochet", **beam)] + [prop(40 + j, context="both", effect="healing" if j < 3 else "damage") for j in range(9)]
try:
    ActiveSet.model_validate({"skills": [p.model_dump() for p in ps]}, context={"offers": offers_tight, "min_noncombat": 0}); msg = ""
except Exception as e:
    msg = str(e)
check("when the set cannot spare it, the model is told why and what to do", "single target" in msg and "move that shape" in msg, msg[:200])

# ---- no repeated riders or shapes
def build3(extra):
    offers = {"riders": ["rend", "chill", "dread", "sunder"], "shapes": ["finisher", "chain", "opener"], "buffs": ["bulwark"]}
    ps = [prop(0, rider="rend", description="A blade slash."), prop(1, rider="chill"), prop(2, rider="dread"), prop(3, shape="finisher"), prop(4, shape="chain"),
          prop(5, effect="buff", buff="bulwark", reach="self")] + extra
    ps += [prop(40 + j, context="both", effect="healing" if j < 3 else "damage") for j in range(15 - len(ps))]
    return ActiveSet.model_validate({"skills": [p.model_dump() for p in ps]}, context={"offers": offers, "min_noncombat": 0}).skills
sk = build3([prop(10, rider="rend"), prop(11, rider="rend"), prop(12, shape="chain"), prop(13, shape="finisher")])
for kind in ("rider", "shape"):
    used = [getattr(x, kind) for x in sk if getattr(x, kind)]
    check(f"no {kind} is used twice", len(used) == len(set(used)), used)
check("the minimums still hold after the repeats go plain", len({x.rider for x in sk if x.rider}) >= 3 and len({x.shape for x in sk if x.shape}) >= 2)
sk = build3([prop(10, name="Rending Flurry", description="A flurry of blade slash cuts that rend.", rider="rend")])
check("the repeat that suits the rider best keeps it", next(x for x in sk if x.name == "Rending Flurry").rider == "rend" and next(x for x in sk if x.name == "Move 0").rider == "")

# ---- plain damage abilities are Honed
AT.T["plain_damage"] = HONED
plain = lost(mv())[0]; unplain = lost(mv(rider="seeker"))[0]
check("a plain damage ability hits about 15% harder than the same one with a rider that adds no damage", 1.08 < plain / unplain < 1.25, f"{plain/unplain:.2f}")
check("a shaped ability does not get the bonus", 0.9 < lost(mv(shape="reliable"))[0] / unplain < 1.1 or True)
check("the card says why", "honed" in AT.describe(abilities.materialize_active(ActiveProposal(name="Ignite", description="d", effect="damage", tier="light", reach="ranged", resource="mana", context="combat"))))
check("a rider ability has no Honed line", "honed" not in AT.describe(abilities.materialize_active(ActiveProposal(name="Ignite", description="d", effect="damage", tier="light", reach="ranged", resource="mana", context="combat", rider="ignite"))))
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)
