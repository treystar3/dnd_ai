"""(f774) A turned foe is on the player's side to every rule of harm, and turning a foe never wins a fight by itself (found by the code
audit, trace-fight-6: Dominate on the last standing undead ended the fight as a victory at once, the foe unhurt, and with two undead
dominating the second did the same; fight-abilities-9: a foe turned to the player's side was still a foe to sweeps, cleaves, arcs,
ground and Unmaking, and Dominate left it tied to the player). The kind: every rule that asks which side a fighter is on before it
harms, holds, blesses or ends the fight, and each way a foe is turned (Dominate, Dread Regent), comes back to itself or leaves. One
function in engine/battlefield.py says which side a fighter fights for now (is_foe, read by hostile; kin for a blessing), the turned
mark read there alone; one pair in engine/combat_perks.py turns a foe and turns it back (turn_foe, only while another foe of its side
stands; turn_back), and one function says whether the fight is won (combat.won), settling the turned first: one turned for a time is
a foe again once its side is gone, and one turned for good leaves. Whom a foe may strike is one rule (Combat.foes_of), so its old side
may strike a turned foe and nobody is held at the line by someone they cannot answer, and nobody out of the fight is picked or tied.
tools/purity.py fences a comparison of two fighters' sides, or the mark named, outside engine/battlefield.py and the turning pair.
The finder's case (Dominate on a lone undead, through the engine's round and through the service's own), then the rest of the kind:
a second undead dominated a round later; for each way in, the rules of harm a turned foe is spared by (its ties, an ability and a
plain attack named at it, a sweep, a cleave, an arc, burning ground, a flare, a summon's burst, Unmaking, a fall back's parting
blow); its blow on its old side (the mark, thorns, who hurt whom); blessings and heals (it is given nothing); its fall (no rout, no
Avenger, no thrall, no affliction carried on); the will lifting (its time up, its side gone by the player's blow and by an ally's
inside finish_round), told once and leaving no tie; one turned for good leaving; its old side striking it and held at the line by
it; a foe's targets never one out of the fight (left by f769); and the fence.
Run: python tools/sim/turned_side_774_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import battlefield as bf
from engine import battlefield_builder as bb
from engine import behaviors, combat, combat_perks, spellcraft, streams, summons
from engine import effects as fx
from engine.combat import Move
from scenes import combat_scene as cs
from scenes.combat_scene import CombatScene
from services.fight import RoundIntent
from tools import purity
from ui import console

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


won = getattr(combat, "won", None)
turn_foe = getattr(combat_perks, "turn_foe", None)
foes_of = getattr(combat.Combat, "foes_of", None)

DOM = Move(id="bend_the_dead", name="Bend the Dead", effect="damage", tier="heavy", reach="ranged", resource="mana",
           attribute="intelligence", element="necrotic", expressions=["dominate"])
BOLT = Move(id="plain_bolt", name="Plain Bolt", effect="damage", tier="moderate", reach="ranged", resource="mana",
            attribute="intelligence", element="fire", spell_form="bolt")
SWEEP = Move(id="wide_cut", name="Wide Cut", effect="damage", tier="moderate", reach="melee", resource="stamina", martial_form="sweep")
GROUND = Move(id="fire_floor", name="Fire Floor", effect="control", tier="heavy", reach="ranged", resource="mana",
              attribute="intelligence", element="fire", expressions=["burning_ground"])
FLARE = Move(id="flare_up_light", name="Flare", effect="control", tier="heavy", reach="ranged", resource="mana",
             attribute="intelligence", element="radiant", expressions=["flare"])
CALL = Move(id="call_spirit", name="Call Spirit", effect="summon", tier="moderate", reach="self", resource="mana",
            attribute="intelligence", summon_form="striker")
BURSTING = Move(id="call_volatile", name="Call Volatile", effect="summon", tier="moderate", reach="self", resource="mana",
                attribute="intelligence", summon_form="volatile", element="fire")
SHIFT = Move(id="slip_free", name="Slip Free", effect="mobility", movement="shift", tier="light", reach="self", resource="stamina")
ADVANCE = Move(id="drive_on", name="Drive On", effect="mobility", movement="relentless_advance", tier="light", reach="melee",
               resource="stamina")
RING = Move(id="ring_smite", name="Ring of Wrath", effect="relic", tier="moderate", reach="ranged", resource="mana", uses=9,
            relic={"kind": "smite", "name": "the ring's wrath", "params": {"mult": 150}})
ALONE = spellcraft.EXPR["dominate"]["alone"]


def player(*mechs, hp=10 ** 4, dmg=12, **kw):
    pairs = [x if isinstance(x, tuple) else (x, 1) for x in mechs]
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: 14 for a in combat.ATTRIBUTES}, hp=hp,
                          max_hp=hp, stamina=10 ** 5, max_stamina=10 ** 5, mana=10 ** 5, max_mana=10 ** 5, weapon_damage=dmg,
                          weapon_attrs=["strength"], hold=2, legendary=dict(pairs),
                          mech_names={m: m.replace("_", " ").title() for m, _ in pairs}, moves=kw.pop("moves", []), **kw)


def undead(i, hp=10 ** 5, **kw):
    d = dict(id=f"e{i}", name=f"skeleton {i}", side="enemy", level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp,
             max_hp=kw.pop("max_hp", hp), weapon_damage=kw.pop("dmg", 0.001), category="undead", behaviors={"fearless": 1}, hold=1)
    d.update(kw)
    return combat.Fighter(**d)


def friend(i=1, hp=10 ** 4, **kw):
    d = dict(id=f"ally_{i}", name=f"friend {i}", side="ally", level=5, attrs={a: 14 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
             stamina=200, max_stamina=200, weapon_damage=6, hold=2)
    d.update(kw)
    return combat.Fighter(**d)


def field(*fs, serial="ts", rnd=1):
    """Everyone on one even zone (the duel ground): the player and the allies at their side's front, the foes at theirs."""
    f = combat.Combat(fighters=list(fs), record=True, serial=serial)
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    f.opened = True
    f.round = rnd
    return f


def tie_all(f):
    for e in [x for x in f.fighters if x.side == "enemy"]:
        bf.engage(f, e, f.player)


def told(f, words) -> int:
    """How many lines of the story say these words (a line is told with its first letter raised)."""
    return sum(words.lower() in s.lower() for s in f.story)


def tied_to(f, t) -> bool:
    """Whether anyone holds a tie to t, or t to anyone."""
    return bool(t.engaged_with) or any(t.id in x.engaged_with for x in f.fighters)


def dominated(*others, p=None, seed=1, target=0):
    """A fight in which Dominate has landed and turned undead[target] (a cast for each seed until it does): (fight, player, foes)."""
    for s in range(seed, seed + 60):
        pl = p or player(moves=[DOM])
        foes = [undead(i + 1) for i in range(2)] + list(others)
        f = field(pl, *foes, serial=f"dm{s}")
        tie_all(f)
        combat.act_ability(f, pl, DOM, foes[target], random.Random(s))
        pl.cooldowns.clear()
        if foes[target].counters.get("turned"):
            return f, pl, foes
    raise AssertionError("Dominate never turned the undead in 60 casts")


def regent_turned(*others, p=None):
    """A fight in which the first foe broke and Dread Regent turned it instead: (fight, player, foes)."""
    pl = p or player("dread_regent")
    if "dread_regent" not in pl.legendary:
        pl.legendary["dread_regent"] = 1
    foes = [undead(i + 1) for i in range(2)] + list(others)
    f = field(pl, *foes, serial="rg")
    tie_all(f)
    behaviors._break(f, foes[0], False)                 # it breaks, and turns its coat instead of running
    assert foes[0].counters.get("turned") and not foes[0].fled
    return f, pl, foes


WAYS = {"Dominate": dominated, "Dread Regent": regent_turned}

streams.begin(7, 1, "I fight.")

# ---- 1. the finder's case: Dominate on a lone undead, through the engine's round (the service's own is section 11)
landed = turned = wins = said = paid = 0
for s in range(1, 80):
    p = player(moves=[DOM])
    u = undead(1)
    f = field(p, u, serial=f"lone{s}")
    tie_all(f)
    m0 = p.mana
    combat.act_ability(f, p, DOM, u, random.Random(s))
    if u.hp == u.max_hp:
        continue                                        # the blow went wide: nothing for its element to do
    landed += 1
    paid += p.mana < m0
    turned += bool(u.counters.get("turned")) or told(f, "turns on its own side") > 0
    said += told(f, ALONE) == 1 and f.story.index(next(x for x in f.story if ALONE.lower() in x.lower())) > 0
    combat.finish_round(f, random.Random(s))
    wins += f.over == "victory"
check("(Dominate's blow lands on the lone undead)", landed >= 20, landed)
check("Dominate on the last foe of its side turns nothing and tells no turning: the blow lands, and that is all", turned == 0,
      f"{turned} of {landed}")
check("...the player is told why, once, after the blow: there is no one of its own left for it to turn on (spellcraft.yaml)",
      said == landed, f"{said} of {landed}")
check("...the cast is paid, as any spell whose rider does not take", paid == landed, f"{paid} of {landed}")
check("...and the fight is not won by it: the undead stands, unhurt but for the blow, and fights on", wins == 0, f"{wins} of {landed}")

# ---- 2. two undead: the first dominated, the second dominated a round later turns nothing, and the fight is not won
f, p, foes = dominated()
u1, u2 = foes
f.round += 1
cast = 0
for s in range(1, 60):
    before = u2.hp
    combat.act_ability(f, p, DOM, u2, random.Random(100 + s))
    p.cooldowns.clear()
    if u2.hp < before:
        cast += 1
        if cast >= 5:
            break
check("(the second undead is struck by Dominate five times)", cast >= 5, cast)
check("a second undead dominated while the first is turned: nothing turns, the last of its side stays its side's",
      not u2.counters.get("turned") and u2 in f.enemies(), u2.counters)
check("...and each landing says why", told(f, ALONE) == cast, (told(f, ALONE), cast))
combat.finish_round(f, random.Random(3))
check("...and the round ends with the fight not won", f.over != "victory", f.over)

# ---- 3. for each way in: every rule of harm spares a turned foe
for way, turn in WAYS.items():
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    check(f"{way}: the turned foe is tied to nobody, nor anybody to it (its ties to its old side and to the player end both ways)",
          not tied_to(f, t), (t.engaged_with, p.engaged_with))
    check(f"{way}: it is no foe of the player's: not among the foes, and the side function says it fights for the player",
          t not in f.enemies() and not bf.hostile(p, t) and bf.hostile(t, a), [e.id for e in f.enemies()])

    # an ability named at it goes at a foe
    p.moves = [DOM, BOLT]
    h0, a0 = t.hp, a.hp
    for s in range(1, 8):
        combat.act_ability(f, p, BOLT, t, random.Random(s))
        p.cooldowns.clear()
    check(f"{way}: an ability named at the turned foe goes at a foe of the player's", t.hp == h0 and a.hp < a0, (h0, t.hp, a0, a.hp))

    # a sweep at its old side
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    bf.engage(f, p, t)                                  # however it came to stand beside the player, still held in the press
    p.moves = [SWEEP]
    h0, a0 = t.hp, a.hp
    for s in range(1, 8):
        combat.act_ability(f, p, SWEEP, a, random.Random(s))
        p.cooldowns.clear()
    check(f"{way}: a sweep at its old side spares the turned foe, even pressed beside it", t.hp == h0 and a.hp < a0, (h0, t.hp, a0, a.hp))

    # a cleave from a blow on its old side, the turned foe at grips with that foe
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    for x in (p, t, a):
        bf.release(f, x)
    bf.engage(f, p, a)
    bf.engage(f, t, a)
    check(f"{way}: a cleave from the blow on its old side never carries into the turned foe", combat.cleave_target(f, p, a) is not t,
          combat.cleave_target(f, p, a))

    # an arc from a blow on its old side, the turned foe the weakest there
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    t.hp = 10
    h0 = t.hp
    p.casting = {"exprs": ["arc"], "tier": "moderate", "name": "arc", "once": []}
    try:
        spellcraft.on_hit(f, p, a, 100, random.Random(1))
    finally:
        spellcraft.end(p)
    check(f"{way}: lightning arcing from the blow on its old side spares the turned foe", t.hp == h0, (h0, t.hp))

    # the player's burning ground, and a flare across the zone
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    p.moves = [GROUND, FLARE]
    h0 = t.hp
    combat.act_ability(f, p, GROUND, a, random.Random(1))
    for s in range(3):
        combat.start_turn(t, f, random.Random(s))
    check(f"{way}: the player's burning ground spares the turned foe standing in it", t.hp == h0, (h0, t.hp, f.log[-3:]))
    for s in range(1, 8):
        combat.act_ability(f, p, FLARE, a, random.Random(s))
        p.cooldowns.clear()
    check(f"{way}: a flare across the zone does not blind the turned foe", "blinded" not in t.statuses, dict(t.statuses))

    # a summon's burst, and Unmaking
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    s_ = summons.make(f, p, BURSTING, form="volatile")[0]
    combat.enters(f, s_)
    h0 = t.hp
    summons.burst(f, s_, random.Random(1))
    check(f"{way}: a summon's burst spares the turned foe", t.hp == h0, (h0, t.hp))
    f, p, foes = turn(p=player("unmaking", moves=[CALL]))
    t, a = foes[0], foes[1]
    s_ = summons.make(f, p, CALL, form="striker")[0]
    combat.enters(f, s_)
    h0 = t.hp
    combat_perks.unmaking(f, p, CALL, random.Random(1))
    check(f"{way}: Unmaking spares the turned foe", t.hp == h0, (h0, t.hp))

    # falling back: no parting blow from the turned foe
    f, p, foes = turn()
    t = foes[0]
    for e in foes:
        fx.put_status(e, "stunned", 3)                  # (its old side would cut at the player as it pulls away: only the turned foe is asked)
    BLOWS = []
    _ad = combat.apply_damage
    combat.apply_damage = lambda c, att, dfn, *a_, **k: (BLOWS.append(att.id), _ad(c, att, dfn, *a_, **k))[1]
    try:
        combat.retreat(f, p, random.Random(1))
    finally:
        combat.apply_damage = _ad
    check(f"{way}: a player who falls back takes no parting blow from the turned foe", t.id not in BLOWS, (BLOWS, f.story[-3:]))



def two_zones(*fs):
    """The player and the turned foe on the near ground, its old side on the far, a way between."""
    f = combat.Combat(fighters=list(fs), record=True, serial="tz")
    f.battlefield = bf.Battlefield(zones={"z1": bf.BattleZone(id="z1", name="the near ground"),
                                          "z2": bf.BattleZone(id="z2", name="the far ground")},
                                   edges=[bf.BattleEdge(a="z1", b="z2")], start="z1")
    bf.place_fighters(f)
    f.opened = True
    return f


for way, turn in WAYS.items():
    # a movement named at the turned foe goes at the nearest foe: Shift pulls free of the foe and ties to no one turned
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    p.moves = [SHIFT]
    combat.act_ability(f, p, SHIFT, t, random.Random(1))
    check(f"{way}: Shift named at the turned foe does not tie the player to it", not tied_to(f, t)
          and not told(f, f"turns on {combat.who(t)}"), (p.engaged_with, t.engaged_with, f.story[-2:]))
    # Relentless Advance named at it drives on to the nearest foe, on the far ground
    pl = player("dread_regent", moves=[ADVANCE, DOM])
    t, a = undead(1, zone_id="z1"), undead(2, zone_id="z2")
    pl.zone_id = "z1"
    f = two_zones(pl, t, a)
    if way == "Dominate":
        for s_ in range(1, 60):
            combat.act_ability(f, pl, DOM, t, random.Random(s_))
            pl.cooldowns.clear()
            if t.counters.get("turned"):
                break
    else:
        behaviors._break(f, t, False)
    check(f"(Relentless Advance: {way} turned the near foe)", bool(t.counters.get("turned")))
    why = combat.act_ability(f, pl, ADVANCE, t, random.Random(2))
    check(f"{way}: Relentless Advance named at the turned foe drives on to the nearest foe, and ties to no one turned",
          why is None and pl.zone_id == "z2" and a.id in pl.engaged_with and not tied_to(f, t), (why, pl.zone_id, pl.engaged_with))
    # a relic's smite named at it strikes a foe
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    p.moves = [RING]
    h0 = t.hp
    combat.act_ability(f, p, RING, t, random.Random(3))
    went = [h.get("dfn") for h in f.hits if h.get("att") == p.name and h.get("label", "").startswith("unleashes")]
    check(f"{way}: a relic's smite named at the turned foe goes at a foe of the player's", t.hp == h0 and went == [a.name], (h0, t.hp, went))
    # Follow Through: the killing blow carries into a foe, never the turned one
    f, p, foes = turn(undead(3), p=player(("follow_through", 100), moves=[DOM], dmg=10 ** 4))
    t, a, b = foes[0], foes[1], foes[2]
    t.hp, a.hp = 5, 1
    h0 = t.hp
    for s_ in range(1, 40):
        combat.act_attack(f, p, a, random.Random(s_))
        if not a.alive:
            break
    went = [h.get("dfn") for h in f.hits if h.get("att") == p.name and h.get("label") == "carries on into"]
    check(f"{way}: Follow Through carries the killing blow into a foe of the player's, never into the turned foe",
          not a.alive and t.hp == h0 and went == [b.name], (a.alive, h0, t.hp, went))

# ---- 4. its blow on its old side: the mark counts, thorns answer, and it is who hurt them
for way, turn in WAYS.items():
    marked = thorned = hurt_by = 0
    for s in range(1, 30):
        f, p, foes = turn()
        t, b = foes[0], foes[1]
        t.weapon_damage = 5
        b.legendary["thorns"] = 100
        combat.add_status(f, b, "marked", 3, p)
        n0, t0 = len(f.hits), t.hp
        combat.apply_damage(f, t, b, 1.0, "turns on", random.Random(s))
        rec = next((h for h in f.hits[n0:] if h.get("att") == t.name and h.get("dfn") == b.name), None)
        if rec is None or rec.get("outcome") not in ("hit", "crit", "graze"):
            continue
        marked += any(st[0] == "Target marked" for st in rec.get("steps", []))
        thorned += t.hp < t0
        hurt_by += b.last_hurt_by == t.id
        if marked >= 3:
            break
    check(f"{way}: the turned foe's blow on a marked foe of its old side takes the mark", marked >= 3, marked)
    check(f"{way}: ...that foe's thorns answer it", thorned >= 3, thorned)
    check(f"{way}: ...and it is who last hurt that foe", hurt_by >= 3, hurt_by)

# ---- 5. blessings and heals: a turned foe is spared, never one of the player's own
for way, turn in WAYS.items():
    f, p, foes = turn(friend(1))
    t, a = foes[0], foes[1]
    al = f.get("ally_1")
    for x in (t, al):
        x.hp = x.max_hp / 2
    h_t, h_a = t.hp, al.hp
    p.casting = {"exprs": ["lifebloom", "shield_of_faith"], "tier": "moderate", "name": "bloom", "once": []}
    try:
        spellcraft.on_hit(f, p, a, 200, random.Random(1))
    finally:
        spellcraft.end(p)
    check(f"{way}: Lifebloom and Shield of Faith from the player's blow mend and ward an ally, and give the turned foe nothing",
          t.hp == h_t and not t.shield and al.hp > h_a and al.shield > 0, (t.hp, h_t, t.shield, al.hp, h_a, al.shield))
    p.counters["last_outcome"] = "crit"
    p.casting = {"exprs": ["rallying_light"], "tier": "moderate", "name": "rally", "once": []}
    try:
        spellcraft.on_hit(f, p, a, 200, random.Random(1))
    finally:
        spellcraft.end(p)
    check(f"{way}: Rallying Light lifts an ally's arm and not the turned foe's", al.counters.get("rallied") and not t.counters.get("rallied"),
          (al.counters.get("rallied"), t.counters.get("rallied")))

# ---- 6. its fall: no rout among the foes, no Avenger, no thrall, no affliction carried on to its old side
def leader_pack(turned_leader: bool):
    p = player("avenger", ("thrall", 1), "plaguebearer")
    lead = undead(1, level=9, rank="elite", behaviors={}, category="hostile people")
    rest = [undead(i, level=3, behaviors={}, category="hostile people") for i in (2, 3, 4)]
    f = field(p, lead, *rest, serial="lp")
    tie_all(f)
    if turned_leader:
        if turn_foe is not None:
            turn_foe(f, lead, None, "it turns")
        else:
            lead.counters["turned"] = 1
            bf.release(f, lead)
    return f, p, lead, rest


broke_t = broke_u = 0
for s in range(1, 41):
    for turned_leader in (True, False):
        f, p, lead, rest = leader_pack(turned_leader)
        lead.hp = 1
        combat.side_damage(f, lead, 50, rest[0], random.Random(s), "physical", told="the blow falls")
        n = sum(1 for e in rest if e.fled)
        if turned_leader:
            broke_t += n
            if s == 1:
                check("a turned foe's fall wakes no Avenger", not p.counters.get("avenging") and not p.counters.get("avenger_used"),
                      p.counters)
        else:
            broke_u += n
check("(the leader of its side falling routs the rest, when it was not turned)", broke_u > 0, broke_u)
check("a turned foe's fall rolls no rout among the foes: none of its old side breaks at it", broke_t == 0, broke_t)
f, p, lead, rest = leader_pack(True)
lead.hp = 0
combat.credit(f, p, lead, random.Random(1))
check("a turned foe's death is no foe's death to the player's kill: no thrall rises from it",
      not any(x.id.startswith("thrall") for x in f.fighters), [x.id for x in f.fighters])
f, p, lead, rest = leader_pack(True)
lead.hp = 1
combat.add_status(f, lead, "poisoned", 3, p)
combat.side_damage(f, lead, 50, rest[0], random.Random(1), "physical", told="the blow falls")
check("(the turned foe falls to its old side, poisoned)", not lead.alive)
check("...and Plaguebearer carries nothing from it on to its old side: it was no foe of the player's",
      not any("poisoned" in e.statuses for e in rest), [dict(e.statuses) for e in rest])
for way, turn in WAYS.items():
    f, p, foes = turn(friend(1))
    t, a, al = foes[0], foes[1], f.get("ally_1")
    t.hp = 1
    combat.add_status(f, t, "poisoned", 3, p)
    t.counters["contagion"] = 1
    check(f"({way}: the turned foe is poisoned by the player, under Contagion)", "poisoned" in t.statuses and bool(t.poison))
    combat.side_damage(f, t, 50, a, random.Random(1), "physical", told="the blow falls")
    check(f"({way}: ...and falls to its old side)", not t.alive)
    check(f"{way}: its poison passes to no one: not to the player's side it fought for, nor to its old side",
          not any("poisoned" in x.statuses for x in (p, al, a)) and not told(f, "Contagion"),
          ([dict(x.statuses) for x in (p, al, a)], f.story[-3:]))
f, p, foes = regent_turned(undead(3))
t, x, y = foes
x.hp = 1
combat.add_status(f, x, "poisoned", 3, p)
x.counters["contagion"] = 1
combat.side_damage(f, x, 50, p, random.Random(1), "physical", told="the blow falls")
check("a foe that falls under Contagion passes its poison to a foe of its side, never to the foe turned",
      "poisoned" in y.statuses and "poisoned" not in t.statuses, (dict(y.statuses), dict(t.statuses)))
f = field(player("avenger"), friend(1), undead(1), serial="av")
al = f.get("ally_1")
al.hp = 1
combat.side_damage(f, al, 50, f.get("e1"), random.Random(1), "physical", told="the blow falls")
check("(an ally's fall still wakes Avenger)", f.player.counters.get("avenging") == 1, f.player.counters)

# ---- 7. the will lifting: its time up; its side gone by the player's blow, and by an ally's inside finish_round
f, p, foes = dominated()
t, a = foes
bf.engage(f, t, a)                                   # it has been fighting its old side
f.round = t.counters["turned_until"] + 1
s0 = len(f.story)
combat.enemy_turn(f, t, random.Random(1))
check("Dominate's rounds run out: the will lifts, told once, and it is a foe again", not t.counters.get("turned") and t in f.enemies()
      and told(f, "the will on") == 1, (t.counters, f.story[s0:]))
check("...with no tie left to the foe it fought while turned", a.id not in t.engaged_with and t.id not in a.engaged_with,
      (t.engaged_with, a.engaged_with, f.story[s0:]))
check("...and the field holds together", bf.validate(f) == [], bf.validate(f))

f, p, foes = dominated()
t, a = foes
a.hp = 1
s0 = len(f.story)
for s in range(1, 40):
    combat.act_attack(f, p, a, random.Random(s))
    if not a.alive or a.fled:
        break
check("(the player's blow fells the last of the turned foe's side)", not a.alive)
over = won(f) if won else (not f.enemies() and not combat.muster(f))
check("the last unturned foe felled by the player while the other is dominated: the fight is not won", not over, over)
check("...the will lifts at once and it is a foe again, told once, tied to nobody", not t.counters.get("turned") and t in f.enemies()
      and told(f, "the will on") == 1 and not tied_to(f, t), (t.counters, f.story[s0:]))

lifted = shown = 0
for s in range(1, 60):
    f, p, foes = dominated(friend(1, weapon_damage=500), seed=s)
    t, a = foes[0], foes[1]
    a.hp = 1
    combat.finish_round(f, random.Random(s))
    if a.alive:
        continue
    lifted += 1
    if f.over == "victory" or t.counters.get("turned") or told(f, "the will on") != 1 or t.fled:
        shown = shown or (s, f.over, t.counters, f.story[-5:])
        break
    if lifted >= 5:
        break
check("(an ally's blow fells the last unturned foe inside finish_round)", lifted > 0, lifted)
check("...the round ends with the fight not won, and the dominated foe a foe again, told once (not fled)", shown == 0, shown)

# a wave in reserve: the side is not gone, so nothing settles at the turned foe's turn, and the won fight brings the wave up
for way, turn in WAYS.items():
    f, p, foes = turn()
    t, a = foes[0], foes[1]
    f.reserves = [undead(9)]
    a.hp = 1
    combat.side_damage(f, a, 50, p, random.Random(1), "physical", told="the blow falls")
    f.round += 1
    s0 = len(f.story)
    combat.enemy_turn(f, t, random.Random(1))
    check(f"{way}: its standing side felled with a wave in reserve, the turned foe stays turned at its turn, and nothing is told of it",
          bool(t.counters.get("turned")) and not t.fled and not told(f, "the will on") and not told(f, "old side broken"),
          (t.counters, t.fled, f.story[s0:]))
    over = won(f) if won else True
    check(f"{way}: ...the fight is not won: the wave comes up, and the turned foe still fights for the player",
          not over and f.get("e9") in f.enemies() and bool(t.counters.get("turned")), (over, [e.id for e in f.enemies()], t.counters))
p = player(moves=[DOM])
u = undead(1)
f = field(p, u, serial="wave")
f.reserves = [undead(9)]
for s in range(1, 60):
    combat.act_ability(f, p, DOM, u, random.Random(s))
    p.cooldowns.clear()
    if u.counters.get("turned"):
        break
check("Dominate on the last standing undead with a wave in reserve turns it: its side is not gone", bool(u.counters.get("turned")),
      u.counters)
check("...and the fight is not won: the wave comes", not (won(f) if won else True) and f.get("e9") in f.enemies())

# a turned foe's turn asks reaches, as a foe's does: one a floor held in its own strike this action is no one to strike again
f, p, foes = regent_turned()
t, a = foes
act = combat.OpenAction()
act.floored.append((t, a))
n0 = len(f.hits)
with combat.in_progress(f, act):
    combat_perks.turned_turn(f, t, random.Random(1))
check("a turned foe does not strike again one a floor held in its own strike this action, and stays turned",
      not [h for h in f.hits[n0:] if h.get("att") == t.name] and bool(t.counters.get("turned")), (f.hits[n0:], t.counters))

# one turned for good: with its side gone it leaves, and the fight is won
f, p, foes = regent_turned()
t, a = foes
a.hp = 1
for s in range(1, 40):
    combat.act_attack(f, p, a, random.Random(s))
    if not a.alive:
        break
s0 = len(f.story)
over = won(f) if won else False
check("Dread Regent's turned foe with its side gone: it leaves, told once, released, and the fight is won",
      over and t.fled and told(f, "its old side broken") == 1 and not tied_to(f, t), (over, t.fled, f.story[s0:]))

# ---- 8. its old side strikes it, and holds nobody at the line it cannot answer
for way, turn in WAYS.items():
    struck = idle = past = held = 0
    for s in range(1, 41):
        f, p, foes = turn()
        t, a = foes[0], foes[1]
        for x in f.fighters:
            bf.release(f, x)
        bf.to_row(f, p, "back")
        bf.to_row(f, t, "front")
        held += bf.containment(f, a.zone_id, True).get(a.id) == t.id
        t0 = t.hp
        combat.enemy_turn(f, a, random.Random(s))
        struck += t.hp < t0 or any(h.get("att") == a.name and h.get("dfn") == t.name for h in f.hits)
        past += any(h.get("att") == a.name and h.get("dfn") == p.name for h in f.hits)
        idle += told(f, "held at the line") > 0
    check(f"{way}: the turned foe at the front holds its old side at the line, as any fighter of the player's side does", held == 40, held)
    check(f"{way}: its old side strikes the turned foe that stands in front of the player", struck == 40, struck)
    check(f"{way}: ...never reaches the player behind it, and no foe stands idle, held by a fighter it may not strike",
          past == 0 and idle == 0, (past, idle))

# ---- 9. (left by f769) whom a foe may strike: never one out of the fight, by its blow, its breath or its sweep
STRUCK = []
_ad = combat.apply_damage


def spy(c, att, dfn, *a_, **k):
    STRUCK.append((att.id, dfn.id, combat.in_fight(dfn)))
    return _ad(c, att, dfn, *a_, **k)


combat.apply_damage = spy
picked = tied = 0
try:
    for s in range(1, 61):
        p, gone, here = player(), friend(1), friend(2)
        w = undead(1, dmg=1, category="beast")
        f = field(p, gone, here, w, serial=f"left{s}")
        combat.leave(f, gone, "fled")
        STRUCK.clear()
        combat.enemy_turn(f, w, random.Random(s))
        picked += any(d == gone.id for _, d, _ in STRUCK)
        tied += w.id in gone.engaged_with or gone.id in w.engaged_with or bool(bf.validate(f))
    check("a foe never picks an ally who has left the fight as its target", picked == 0, picked)
    check("...nor ties itself to them", tied == 0, tied)
    p, gone, here = player(), friend(1), friend(2)
    w = undead(1, dmg=1, category="beast", family="swarm_test", behaviors={"sweep": 0.9, "fearless": 1})
    f = field(p, gone, here, w, serial="left_sw")
    combat.leave(f, gone, "fled")
    STRUCK.clear()
    behaviors.sweeps(f, w, random.Random(1))
    behaviors._area(f, w, random.Random(1), 1.0, "breath", "it breathes")
    check("a swarm's sweep and a breath go over everyone against it in the fight, and no one who has left it",
          STRUCK and not [x for x in STRUCK if not x[2]], STRUCK)
finally:
    combat.apply_damage = _ad
if foes_of is not None:
    f, p, foes = regent_turned()
    t, a, b = foes[0], foes[1], foes[1]
    check("one rule says whom each may strike: a foe its old side's turned foe among the player's side, the turned foe its old side, "
          "the player the foes", [x.id for x in f.foes_of(a)] == ["player", t.id] and [x.id for x in f.foes_of(t)] == [a.id]
          and [x.id for x in f.foes_of(p)] == [a.id], ([x.id for x in f.foes_of(a)], [x.id for x in f.foes_of(t)]))
else:
    check("one rule says whom each may strike (Combat.foes_of)", False, "missing")

# ---- 10. the fence: two fighters' sides compared, or the mark named, outside the side function and the turning pair
fence = getattr(purity, "side_problems", None)
fence_in = getattr(purity, "side_problems_in", None)
check("the game compares no two fighters' sides and names no turned mark outside engine/battlefield.py and the turning pair",
      fence is not None and fence() == [], fence() if fence else "missing")
if fence_in is not None:
    text = open("engine/movement.py", encoding="utf-8").read()
    typed = text + "\n\ndef _mine(a, b):\n    return a.side == b.side\n"
    check("a comparison of two fighters' sides typed into a copy of engine/movement.py is named",
          any("movement.py" in x and "side" in x for x in fence_in(typed, "engine/movement.py")), fence_in(typed, "engine/movement.py"))
    typed = text + "\n\ndef _mine(a, b):\n    return (a.side == \"enemy\") != (b.side == \"enemy\")\n"
    check("...and so is one made through the side's name on each", bool(fence_in(typed, "engine/movement.py")))
    typed = text + "\n\ndef _mine(a):\n    return a.counters.get(\"turned\")\n"
    check("...and the turned mark read there", bool(fence_in(typed, "engine/movement.py")))
    typed = text + "\n\ndef _mine(a):\n    return a.side == \"enemy\"\n"
    check("...and, in the engine, a side compared with \"enemy\" (a foe turned keeps that name: ask is_foe)",
          any("enemy" in x for x in fence_in(typed, "engine/movement.py")), fence_in(typed, "engine/movement.py"))
    check("...but not in the fight's books outside the engine, nor a side compared with \"ally\"",
          fence_in(typed, "scenes/combat_scene.py") == []
          and fence_in(text + "\n\ndef _mine(a):\n    return a.side == \"ally\"\n", "engine/movement.py") == [])
    check("...and the one function the fence lets compare with \"enemy\" says why",
          all(why for why in purity.SIDE_KIND_FUNCTIONS.values()) and ("engine/damage.py", "fall_line") in purity.SIDE_KIND_FUNCTIONS)
    check("...while a side compared with a named side (what kind a fighter is) is not", fence_in(text, "engine/movement.py") == [],
          fence_in(text, "engine/movement.py"))
else:
    check("the fence names a side compared by hand (purity.side_problems_in)", False, "missing")

# ---- 11. the service's own round (the finder's path): Dominate on a lone undead, a plain attack named at a turned foe, the will
# lifting and one turned for good leaving, after the player's blow
console.put("combat_state", lambda data: False)
console.put("combat_panel", lambda lines: None)
game = simlib.campaign("turned_side_774", cls="warrior", seed=7, location="parth")
ws = game.scene
ws.enter("parth")
creature = ws.world.bestiary["skeleton"]


def service_fight(n=1, hp=10 ** 6):
    foes = []
    for i in range(n):
        s_ = combat.fighter_from_creature(creature, 3, "normal", f"e{i + 1}", name=f"skeleton {i + 1}")
        s_.hp = s_.max_hp = hp
        s_.weapon_damage = 0.001
        s_.behaviors["fearless"] = 1
        foes.append(s_)
    ws.narrate_with = lambda *a, **k: None
    sc = CombatScene.begin(ws, creature, foes, "It is on you:")
    ws.combat = sc
    f = sc.fight
    for a in f.allies():
        a.order = "hold"                                  # the companions hold back: the player's own action is measured
    p = f.player
    p.moves = list(p.moves) + [DOM]
    p.mana = p.max_mana = 10 ** 5
    return f, cs.service_of(ws), foes


def service_round(f, svc, n, **intent):
    streams.begin(ws.store.meta.seed, n, "I act.")
    with ws.operation("test:round", "I act."):
        svc.round(f, RoundIntent(words="I act.", **intent))


landed = wins = 0
for s in range(10):
    f, svc, (u,) = service_fight(1)
    service_round(f, svc, 60 + s, kind="ability", ability=DOM.id, target="e1")
    if u.hp == u.max_hp:
        continue
    landed += 1
    wins += f.over == "victory" or bool(u.counters.get("turned"))
check("(the service: Dominate's blow lands on the lone skeleton)", landed >= 3, landed)
check("the service's round: Dominate on the lone skeleton turns nothing and wins nothing", wins == 0, f"{wins} of {landed}")

f, svc, (t, a) = service_fight(2)
p = f.player
for s in range(1, 60):
    combat.act_ability(f, p, DOM, t, random.Random(s))
    p.cooldowns.clear()
    if t.counters.get("turned"):
        break
check("(the service: one skeleton dominated)", bool(t.counters.get("turned")))
fx.put_status(a, "stunned", 3)                         # its old side does not act: the player's own blow is measured
h0 = t.hp
service_round(f, svc, 80, kind="attack", target=t.id)
mine = [h for h in f.hits if h.get("att") == p.name]           # the round's own blows
check("the service's round: a plain attack named at the turned skeleton goes at a foe of the player's",
      t.hp == h0 and mine and all(h.get("dfn") != t.name for h in mine), (h0, t.hp, [h.get("dfn") for h in mine]))

f, svc, (t, a) = service_fight(2)
p = f.player
for s in range(1, 60):
    combat.act_ability(f, p, DOM, t, random.Random(s))
    p.cooldowns.clear()
    if t.counters.get("turned"):
        break
a.hp = 1
for n in range(90, 110):
    s0 = len(f.story)
    service_round(f, svc, n, kind="attack", target=a.id)
    if not a.alive or f.over:
        break
check("(the service: the player fells the last skeleton not turned)", not a.alive)
check("the service's round: the last of its side felled, the dominated skeleton's will lifts and the fight goes on",
      f.over != "victory" and not t.counters.get("turned") and told(f, "the will on") == 1, (f.over, t.counters, f.story[s0:]))

f, svc, (t, a) = service_fight(2)
p = f.player
p.legendary["dread_regent"] = 1
behaviors._break(f, t, False)
check("(the service: Dread Regent turned one skeleton)", bool(t.counters.get("turned")) and not t.fled)
a.hp = 1
for n in range(120, 140):
    s0 = len(f.story)
    service_round(f, svc, n, kind="attack", target=a.id)
    if not a.alive or f.over:
        break
check("the service's round: Dread Regent's turned skeleton with its side gone leaves, told once, and the fight is won",
      f.over == "victory" and t.fled and told(f, "its old side broken") == 1, (f.over, t.fled, f.story[s0:]))
ws.combat = None
game.close()

check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
