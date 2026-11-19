"""(f767) What is settled when a two-turn ability is begun reaches the turn it lands (found by the code audit, fight-abilities-5: a
charged spell or a wind-up technique lost every bonus fixed when it was begun. Archmage's Focus made a charged spell free and no
harder; Overchannel took the health and added nothing; a wind-up heavy's kill never set Headsman, and Blood for Blood, War Drum and
Bulwark Engine never saw a wind-up heavy; a third charged cast with Spell Echo began a second gathering and landed one blow). The
kind: every ability that takes more than one turn (a charged spell, a wind-up technique, a taught ability with a cast time of its
own) and every bonus, recipient or repeat decided when it is paid for. The test walks a table of perks, each on a plain ability and
on its gathered twin, and asks for the same effect on both. The table is fenced: every perk in engine/combat_perks.py that reads
what the ability is while it resolves (tier_now, reach_now, blood_cast, weave_crit) or runs as it is cast or after it (on_cast,
after_cast) must have a row, so a perk added later is caught. Second cases: Archmage's Focus; nothing paid or counted twice; a
caster striking from hiding is seen at the landing; a taught heal with a cast time named for an ally lands on the ally, and still
lands when no foe stands; a companion's gathered heal for the player; what was settled is lost with a broken gathering; and a
release after the fight is saved and read back keeps what was settled (a row from before keeps nothing, as before).
Run: python tools/sim/begun_and_landed_767_test.py"""
import ast
import random
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from core import yamlio
from engine import battlefield as bf
from engine import battlefield_builder as bb
from engine import combat
from engine import combat_perks as perks
from engine import effects as fx
from engine.combat import Move
from services.fight import FightService

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def player(*mechs, moves=(), hp=400, mana=10 ** 4, stam=10 ** 4, dmg=10, **kw):
    pairs = [x if isinstance(x, tuple) else (x, 1) for x in mechs]
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: 14 for a in combat.ATTRIBUTES}, hp=hp,
                          max_hp=kw.pop("max_hp", hp), stamina=stam, max_stamina=stam, mana=mana, max_mana=kw.pop("max_mana", max(mana, 100)),
                          weapon_damage=dmg, hold=2, legendary=dict(pairs), mech_names={m: m.replace("_", " ").title() for m, _ in pairs},
                          moves=list(moves), **kw)


def foe(i, hp=10 ** 6, **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp,
                          max_hp=kw.pop("max_hp", hp), weapon_damage=8, category=kw.pop("category", "hostile people"),
                          behaviors={"fearless": 1}, **kw)


def ally(aid, hp=100, max_hp=100, **kw):
    return combat.Fighter(id=aid, name=aid.replace("_", " "), side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=max_hp, weapon_damage=8, hold=1, **kw)


def fight(*fs):
    f = combat.Combat(fighters=list(fs), record=True, serial="bl")
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    f.opened = True
    return f


def close(f, a, b):
    """a and b toe to toe."""
    if b.zone_id != a.zone_id:
        bf.enter_zone(f, b, a.zone_id)
    bf.engage(f, a, b)


def spell(mid, **kw):
    kw.setdefault("reach", "ranged")
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=kw.pop("effect", "damage"), tier=kw.pop("tier", "heavy"),
                resource="mana", attribute="intelligence", **kw)


def skill(mid, **kw):
    kw.setdefault("reach", "melee")
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=kw.pop("effect", "damage"), tier=kw.pop("tier", "heavy"),
                resource="stamina", **kw)


def twin(m, gather):
    """The ability as it is, or its gathered twin: a charged spell, a wind-up technique, or a cast time of its own."""
    if not gather:
        return m
    if m.effect == "damage" and m.resource == "mana":
        return m.model_copy(update={"spell_form": "charged"})
    if m.effect == "damage":
        return m.model_copy(update={"martial_form": "windup"})
    return m.model_copy(update={"cast_turns": 2})


def finish(f, p, rng):
    """The caster's turns after a gathered ability is begun, until it lands (or breaks)."""
    n = 0
    while p.charging and n < 4:
        f.round += 1
        combat.start_turn(p, f, rng)
        p.counters.pop("cast_turn", None)
        n += 1


def use(f, p, m, target, rng, give=None):
    """The ability used, and for a gathered one the caster's turns after it until it lands. Returns the refusal, if any."""
    why = combat.act_ability(f, p, m, target, rng, give=give)
    finish(f, p, rng)
    return why


FORCE = {"to": None}                     # the player's attack rolls forced to this outcome before the perks see them
_roll = combat.roll_attack


def _forced(att, dfn, c, rng, trace=None):
    out = _roll(att, dfn, c, rng, trace=trace)
    return (FORCE["to"], out[1]) if FORCE["to"] and att.side == "player" else out


combat.roll_attack = _forced


def blows(f, h0=0):
    return tuple(h["outcome"] for h in f.hits[h0:] if h["att_side"] == "player")


def told(f, words, since=0):
    return [i for i, s in enumerate(f.story) if i >= since and words in str(s)]


# ---- the table: each perk on a plain ability and on its gathered twin, the same effect on both
ROWS: dict[str, tuple] = {}


def row(name, want, what):
    def deco(fn):
        ROWS[name] = (fn, want, what)
        return fn
    return deco


@row("attuned_edge", "fire", "the weapon takes the spell's element")
def _(g):
    m = twin(spell("flare", element="fire"), g)
    p = player("attuned_edge", moves=[m])
    f = fight(p, foe(1))
    FORCE["to"] = "hit"
    use(f, p, m, f.get("e1"), random.Random(1))
    return p.attuned


@row("blood_for_blood", ("hit",), "bleeding, the heavy cannot miss")
def _(g):
    m = twin(skill("cleaver"), g)
    p = player("blood_for_blood", moves=[m])
    f = fight(p, foe(1))
    close(f, p, f.get("e1"))
    fx.put_status(p, "bleeding", 9)
    FORCE["to"] = "miss"
    use(f, p, m, f.get("e1"), random.Random(1))
    return blows(f)


@row("bound_pair", True, "the cast mends the summon")
def _(g):
    m = twin(spell("flare", element="fire"), g)
    p = player("bound_pair", moves=[m])
    s = ally("bound_shade", hp=50, summon_form="bound", summon_owner="player")
    f = fight(p, s, foe(1))
    FORCE["to"] = "hit"
    use(f, p, m, f.get("e1"), random.Random(1))
    return s.hp > 50


@row("bulwark_engine", (("hit",), False), "a fully charged heavy cannot miss, and spends its charges")
def _(g):
    m = twin(skill("cleaver"), g)
    p = player(("bulwark_engine", 20), moves=[m])
    p.counters["bulwark"] = perks.P["bulwark_engine"]["sure_at"]
    f = fight(p, foe(1))
    close(f, p, f.get("e1"))
    FORCE["to"] = "miss"
    use(f, p, m, f.get("e1"), random.Random(1))
    return blows(f), "bulwark" in p.counters


def _heal_fight(perk, *others):
    p = player(perk, hp=400)
    a1, a2 = ally("ally_one", hp=50), ally("ally_two", hp=10)
    f = fight(p, a1, a2, foe(1), *others)
    return f, p, a1, a2


MEND = Move(id="first_mend", name="First Mend", effect="healing", tier="moderate", resource="mana", attribute="wisdom", reach="ranged")


def _heal(g):
    return twin(Move(id="mend", name="Mend", effect="healing", tier="moderate", resource="mana", attribute="wisdom", reach="ranged"), g)


@row("consecration", (1, True, True), "the heal sears the undead at the healed one's side once, after this heal lands")
def _(g):
    u = foe(2, category="undead")
    f, p, a1, a2 = _heal_fight("consecration", u)
    close(f, a1, u)
    rng = random.Random(1)
    use(f, p, MEND, None, rng, give=[a1])                    # a heal before, so a stale figure would show
    mark, hp0 = len(f.log), u.hp
    use(f, p, _heal(g), None, rng, give=[a1])
    seared = [i for i, x in enumerate(f.log) if i >= mark and "seared by the healing" in x]
    healed = [i for i, x in enumerate(f.log) if i >= mark and x.startswith("you uses Mend on ally one: heals")]
    return len(seared), u.hp < hp0, bool(seared and healed and healed[0] < seared[0])


@row("echoing_mend", (1, True), "the mending carries on into the most wounded once, at half this heal")
def _(g):
    f, p, a1, a2 = _heal_fight("echoing_mend")
    rng = random.Random(1)
    use(f, p, MEND, None, rng, give=[a1])
    a1.hp, a2.hp = 50, 10
    mark, s0 = len(f.log), len(f.story)
    use(f, p, _heal(g), None, rng, give=[a1])
    lines = [x for x in f.log[mark:] if "(Echoing Mend)" in x]
    last = fx.get(f, "last_heal")
    want = round(round(last.value) * perks.P["echoing_mend"]["share"]) if last is not None else -1
    return len(lines), lines == [f"ally two is healed {want} (Echoing Mend)"]


@row("grave_chorus", (("hit", "hit"), 0), "an echo waiting repeats the working as a second blow")
def _(g):
    m = twin(skill("cleaver"), g)
    p = player("grave_chorus", moves=[m])
    p.counters["echoes"] = 1
    f = fight(p, foe(1))
    close(f, p, f.get("e1"))
    FORCE["to"] = "hit"
    use(f, p, m, f.get("e1"), random.Random(1))
    return blows(f), p.counters.get("echoes", 0)


@row("headsman", (True, True, 0, False), "a heavy's kill makes the next heavy free, and the next heavy spends it")
def _(g):
    m = twin(skill("cleaver"), g)
    p = player("headsman", moves=[m])
    f = fight(p, foe(1, hp=5), foe(2))
    e1 = f.get("e1")
    close(f, p, e1)
    close(f, p, f.get("e2"))
    FORCE["to"] = "hit"
    rng = random.Random(1)
    use(f, p, m, e1, rng)
    killed, armed = not e1.alive, bool(p.counters.get("headsman"))
    f.round += 1
    st = p.stamina
    combat.act_ability(f, p, m, f.get("e2"), rng)
    paid = round(st - p.stamina)
    finish(f, p, rng)
    return killed, armed, paid, bool(p.counters.get("headsman"))


@row("high_ground_hunter", True, "a ranged blow from high ground pins its target")
def _(g):
    m = twin(skill("longshot", reach="ranged"), g)
    p = player("high_ground_hunter", moves=[m])
    f = fight(p, foe(1))
    bf.gain(p, "elevated")
    FORCE["to"] = "hit"
    use(f, p, m, f.get("e1"), random.Random(1))
    return bool(f.get("e1").counters.get("pinned"))


@row("lasting_word", (True, 1, True), "the blessing lasts the fight, told once and after it is on")
def _(g):
    m = twin(Move(id="ward_song", name="Ward Song", effect="buff", buff="thorns", tier="moderate", resource="mana",
                  attribute="wisdom", reach="ranged"), g)
    p = player("lasting_word", moves=[m])
    f = fight(p, foe(1))
    s0 = len(f.story)
    use(f, p, m, None, random.Random(1))
    lines, on = told(f, "will not fade while the fight lasts", s0), told(f, "in Ward Song", s0)
    return (p.buffs.get(m.id, {}).get("rounds") == perks.P["lasting_word"]["rounds"], len(lines),
            bool(lines and on and on[0] < lines[0]))


@row("ley_tether", True, "standing fast, the spell is drawn up from the ground")
def _(g):
    m = twin(spell("flare", element="fire"), g)
    p = player(("ley_tether", 50), moves=[m])
    f = fight(p, foe(1))
    f.round, p.move_round = 5, 0
    FORCE["to"] = "hit"
    use(f, p, m, f.get("e1"), random.Random(1))
    return bool(p.counters.get("tether_round"))


@row("mending_rhythm", (3, 1, True), "the third heal reaches the company once, after that heal lands")
def _(g):
    f, p, a1, a2 = _heal_fight("mending_rhythm")
    rng = random.Random(1)
    s0 = len(f.story)
    m = _heal(g)
    for _i in range(3):
        a1.hp = 50
        use(f, p, m, None, rng, give=[a1])
        f.round += 1
    rhythm, heals = told(f, "third mending in its rhythm", s0), told(f, "wounds begin to close", s0)
    return p.counters.get("heals_cast"), len(rhythm), bool(rhythm and len(heals) >= 3 and heals[2] < rhythm[0])


@row("overcast", (1, True), "a spell on cooldown is forced at twice the price, told once")
def _(g):
    m = twin(spell("flare", element="fire", cooldown=3), g)
    p = player("overcast", moves=[m])
    f = fight(p, foe(1))
    base = combat.cost_of(p, m, f)
    p.cooldowns[m.id] = 2
    s0, mana = len(f.story), p.mana
    FORCE["to"] = "hit"
    use(f, p, m, f.get("e1"), random.Random(1))
    return len(told(f, "it anyway, at twice the price", s0)), mana - p.mana >= 2 * base - 1


@row("overchannel", (True, True), "a spell paid in blood lands harder, and the blood is paid once")
def _(g):
    m = twin(spell("flare", element="fire"), g)
    p = player(("overchannel", 2), moves=[m], mana=0, max_mana=100)
    f = fight(p, foe(1))
    FORCE["to"] = "hit"
    rng = random.Random(1)
    combat.act_ability(f, p, m, f.get("e1"), rng)
    hp_paid = p.hp
    finish(f, p, rng)
    stepped = any(s[0] == "Overchannel" for h in f.hits if h["att_side"] == "player" for s in h["steps"])
    return stepped, p.hp == hp_paid and p.hp < 400


@row("spell_echo", ([1, 1, 2], 1), "the third cast of the same spell goes off twice, told once")
def _(g):
    m = twin(spell("flare", element="fire"), g)
    p = player("spell_echo", moves=[m])
    f = fight(p, foe(1))
    FORCE["to"] = "hit"
    rng = random.Random(1)
    per, s0 = [], len(f.story)
    for _i in range(3):
        h0 = len(f.hits)
        use(f, p, m, f.get("e1"), rng)
        per.append(len(f.hits) - h0)
        f.round += 1
    return per, len(told(f, "three times running", s0))


@row("steady_aim", ("hit",), "standing still, the ranged shot cannot miss")
def _(g):
    m = twin(skill("longshot", reach="ranged"), g)
    p = player("steady_aim", moves=[m])
    f = fight(p, foe(1))
    f.round, p.move_round = 5, 0
    FORCE["to"] = "miss"
    use(f, p, m, f.get("e1"), random.Random(1))
    return blows(f)


@row("threefold_weave", "crit", "the third kind of magic in a row lands critical")
def _(g):
    one, two = spell("flare", element="fire", tier="light"), spell("rime", element="cold", tier="light")
    third = twin(spell("thunderhead", element="lightning"), g)
    p = player("threefold_weave", moves=[one, two, third])
    f = fight(p, foe(1))
    FORCE["to"] = "hit"
    rng = random.Random(1)
    for m in (one, two):
        use(f, p, m, f.get("e1"), rng)
        f.round += 1
    h0 = len(f.hits)
    use(f, p, third, f.get("e1"), rng)
    return "".join(blows(f, h0)) if len(blows(f, h0)) == 1 else blows(f, h0)


@row("war_drum", True, "a heavy that lands sets each companion's next blow to the drum")
def _(g):
    m = twin(skill("cleaver"), g)
    p = player("war_drum", moves=[m])
    w = ally("ally_wolf")
    f = fight(p, w, foe(1))
    close(f, p, f.get("e1"))
    FORCE["to"] = "hit"
    use(f, p, m, f.get("e1"), random.Random(1))
    return bool(w.counters.get("drum"))


for name, (fn, want, what) in ROWS.items():
    plain, gathered = fn(False), fn(True)
    check(f"{name}: {what} (plain)", plain == want, (plain, want))
    check(f"{name}: ...and the same on its gathered twin", gathered == want, (gathered, want))
FORCE["to"] = None


# ---- the fence: every perk that reads what the ability is while it resolves, or runs as it is cast or after it, has a row
def fenced() -> dict[str, set[str]]:
    src = Path("engine/combat_perks.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    ids = {m["id"] for m in yamlio.safe_load(Path("data/rules/passive_mechanics.yaml").read_text(encoding="utf-8"))
           if m.get("where") != "taught"}                       # a creation perk; a taught mechanic is combat.py's
    keys = {"tier_now", "reach_now", "blood_cast", "weave_crit"}

    def strings(node):
        return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}

    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    helpers = {k for k, fn in funcs.items() if k.startswith("_") and strings(fn) & keys}     # _ranged_now reads reach_now

    def reads(node):
        return bool(strings(node) & keys) or any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in helpers
                                                for n in ast.walk(node))

    found: dict[str, set[str]] = {}
    for k, fn in funcs.items():
        if k in helpers:
            continue
        if k in ("on_cast", "after_cast"):
            for pid in strings(fn) & ids:
                found.setdefault(pid, set()).add(k)
            continue
        for n in ast.walk(fn):
            if isinstance(n, ast.If) and reads(n.test):
                for pid in strings(n) & ids:
                    found.setdefault(pid, set()).add(k)
    return found


seen = fenced()
check("(the fence reads the perks: Headsman, War Drum, Overchannel, Threefold Weave and Steady Aim among them)",
      {"headsman", "war_drum", "overchannel", "threefold_weave", "steady_aim", "lasting_word"} <= set(seen), sorted(seen))
missing = {k: sorted(v) for k, v in seen.items() if k not in ROWS}
check("every such perk has a row in the table (a perk added later is caught here)", not missing, missing)


# ---- Archmage's Focus: the first spell's share lands with the blow, gathered or not
def first_spell(m, share, seeds=range(1, 13)):
    out = []
    for sd in seeds:
        p = player(moves=[m])
        if share:
            p.legendary["archmage"] = share
        f = fight(p, foe(1))
        e = f.get("e1")
        FORCE["to"] = "hit"
        use(f, p, m, e, random.Random(sd))
        out.append(e.max_hp - e.hp)
    FORCE["to"] = None
    return sum(out) / len(out)


bolt = spell("spark", element="lightning")
for g in (False, True):
    m = twin(bolt, g)
    without, with_ = first_spell(m, 0), first_spell(m, 50)
    check(f"Archmage's Focus: the first spell, {'gathered' if g else 'plain'}, lands half again as hard", 1.4 < with_ / max(1, without) < 1.6,
          (without, with_))

# ---- nothing paid or counted twice, and the beginning spends what it settled
m = twin(spell("thunderhead", element="lightning", cooldown=2), True)
p = player(("archmage", 50), moves=[m])
f = fight(p, foe(1))
rng = random.Random(3)
mana0 = p.mana
combat.act_ability(f, p, m, f.get("e1"), rng)
check("a gathered spell's beginning pays and counts it (Archmage's Focus spent there, its share kept for the landing)",
      p.archmage_used and p.spells_cast == 1 and p.recent_casts == [m.id] and p.cooldowns.get(m.id) == 3 and p.mana == mana0
      and p.charging.get("archmage") == 50,
      (p.archmage_used, p.spells_cast, p.recent_casts, p.cooldowns, mana0 - p.mana, p.charging.get("archmage")))
q = player(moves=[m])
g = fight(q, foe(1))
combat.act_ability(g, q, m, g.get("e1"), random.Random(3))
check("...and one cast without it keeps no share", q.charging.get("archmage") == 0 and q.mana < 10 ** 4,
      (q.charging.get("archmage"), q.mana))
f.round += 1
combat.start_turn(p, f, rng)
check("...and its landing pays and counts nothing again", p.spells_cast == 1 and p.recent_casts == [m.id] and p.mana == mana0
      and not p.charging and blows(f), (p.spells_cast, p.recent_casts, mana0 - p.mana, p.charging, blows(f)))
check("...nor leaves the landing's reading behind", not any(k in p.counters for k in ("tier_now", "reach_now", "blood_cast", "weave_crit",
                                                                                         "echo_now", "echo_cast")), p.counters)

# ---- striking from hiding: the caster is seen once the gathered blow lands
for g in (False, True):
    m = twin(spell("spark", element="lightning"), g)
    p = player(moves=[m])
    f = fight(p, foe(1))
    bf.gain(p, "concealed")
    use(f, p, m, f.get("e1"), random.Random(2))
    check(f"striking from hiding gives the caster away ({'gathered' if g else 'plain'})", "concealed" not in p.position_tags and blows(f),
          (p.position_tags, blows(f)))

# ---- second case: a taught heal with a cast time, named for an ally
heal = _heal(True)
p = player(hp=300, max_hp=400, moves=[heal])
a = ally("ally_one", hp=40)
f = fight(p, a, foe(1))
rng = random.Random(4)
combat.act_ability(f, p, heal, None, rng, give=[a])
check("a heal with a cast time begins to gather (nothing healed yet)", p.charging and a.hp == 40 and p.hp == 300, (p.charging, a.hp, p.hp))
f.round += 1
combat.start_turn(p, f, rng)
check("...and lands on the ally it was named for, not the caster", a.hp > 40 and p.hp == 300, (a.hp, p.hp, f.story[-3:]))

p = player(hp=300, max_hp=400, moves=[heal])
a = ally("ally_one", hp=40)
e = foe(1)
f = fight(p, a, e)
rng = random.Random(4)
combat.act_ability(f, p, heal, None, rng, give=[a])
e.hp = 0                                                      # the last foe falls while it is gathered
f.round += 1
combat.start_turn(p, f, rng)
check("a gathered heal still lands when no foe stands (it needs none)", a.hp > 40 and not told(f, "finds no one left"), (a.hp, f.story[-3:]))

p = player(hp=300, max_hp=400, moves=[heal])
a = ally("ally_one", hp=40)
f = fight(p, a, foe(1))
rng = random.Random(4)
combat.act_ability(f, p, heal, None, rng, give=[a])
combat.leave(f, a, "fled")                                    # the one it was named for leaves the fight while it is gathered
f.round += 1
combat.start_turn(p, f, rng)
check("...and one whose ally has left by then mends the caster (healing.cast's rule)", p.hp > 300 and a.hp == 40, (p.hp, a.hp))

# a companion's gathered heal for the player: the same path, by whoever is acting
w = ally("ally_priest", hp=100, mana=10 ** 4, max_mana=10 ** 4, moves=[heal])
p = player(hp=200, max_hp=400)
f = fight(p, w, foe(1))
rng = random.Random(5)
combat.act_ability(f, w, heal, None, rng, give=[p])
f.round += 1
combat.start_turn(w, f, rng)
check("a companion's gathered heal lands on the player it was named for", p.hp > 200 and not w.charging, (p.hp, w.charging))

# ---- a gathering broken keeps nothing: what it settled is not left for the next spell
one, two = spell("flare", element="fire", tier="light"), spell("rime", element="cold", tier="light")
third = twin(spell("thunderhead", element="lightning"), True)
p = player("threefold_weave", "spell_echo", moves=[one, two, third, spell("glint", element="lightning", tier="light")])
f = fight(p, foe(1))
FORCE["to"] = "hit"
rng = random.Random(6)
for m in (one, two):
    use(f, p, m, f.get("e1"), rng)
    f.round += 1
combat.act_ability(f, p, third, f.get("e1"), rng)
fx.put_status(p, "stunned", 1)
f.round += 1
combat.start_turn(p, f, rng)
check("(a stun breaks the gathering)", not p.charging and told(f, "comes apart"), (p.charging, f.story[-2:]))
p.counters.pop("cast_turn", None)
fx.end_status(p, "stunned")
f.round += 1
h0 = len(f.hits)
use(f, p, p.moves[3], f.get("e1"), rng)
check("...and the next spell finds no critical left over from it", blows(f, h0) == ("hit",), blows(f, h0))
FORCE["to"] = None


# ---- a release after the fight is saved and read back keeps what was settled
def reopened(f):
    back, _, why = FightService.resume(FightService.row(f, "foe"))
    assert back is not None, why
    return back


m = twin(spell("flare", element="fire"), True)
p = player(("overchannel", 2), moves=[m], mana=0, max_mana=100)
f = fight(p, foe(1))
rng = random.Random(7)
FORCE["to"] = "hit"
combat.act_ability(f, p, m, f.get("e1"), rng)
f = reopened(f)
p = f.player
f.round += 1
combat.start_turn(p, f, rng)
check("a charged spell paid in blood, saved and read back mid-gathering, still lands harder",
      any(s[0] == "Overchannel" for h in f.hits if h["att_side"] == "player" for s in h["steps"]), [h["steps"] for h in f.hits])

p = player(hp=300, max_hp=400, moves=[heal])
f = fight(p, ally("ally_one", hp=40), foe(1))
combat.act_ability(f, p, heal, None, rng, give=[f.get("ally_one")])
f = reopened(f)
f.round += 1
combat.start_turn(f.player, f, rng)
check("...and a gathered heal read back lands on the ally it was named for", f.get("ally_one").hp > 40 and f.player.hp == 300,
      (f.get("ally_one").hp, f.player.hp))

m = twin(spell("flare", element="fire"), True)
p = player(("overchannel", 2), moves=[m], mana=0, max_mana=100)
f = fight(p, foe(1))
combat.act_ability(f, p, m, f.get("e1"), rng)
p.charging = {k: p.charging[k] for k in ("move", "target", "round", "left")}      # a row written before: nothing settled in it
f = reopened(f)
f.round += 1
combat.start_turn(f.player, f, rng)
check("a row from before lands as it did before: the blow, with nothing settled", blows(f) and not any(
    s[0] == "Overchannel" for h in f.hits for s in h["steps"]) and not f.player.charging, (blows(f), f.player.charging))
FORCE["to"] = None

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
