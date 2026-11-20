"""(f771) A trial of rank is decided only by its duellists, and one rule says who may stand in it (found by the code audit,
trace-fight-3: a summoner called the pack in a trial, the examiner's blow that would have ended one of the pack was taken by the duel's
floor for a duellist's, the fight ended "victory" and the player was promoted without striking a blow, 4 of 6 seeds; a poison tick on a
summon did the same; the Bound summon was kept at the door while its spell could be cast inside).
The owner, 2026-11-19 (GOALS.md's top decision row, docs/design/34_one_fall_step.md question 3 (a)): summons made in the fight stand
beside their summoner in a trial, a beaten one is unmade by the fall step and decides nothing, and the Bound summon walks in with the
summoner; companions and hires stay out, because a rank is won by the one who holds it.
Who decides is read from the fight as it stands: a player fighter, or a foe nobody summoned (engine/combat.py duellist). The duel's
floor and its ending hold and decide only for a duellist, on every path that can bring one to it: a blow, a tick, a rebound, and the
spell's own floor of Death's Door. Who may stand (engine/combat.py stands) is one rule with one key (data/rules/guild.yaml
trial.summons), asked by the door (services/fight.py begin and engine/summons.py join_bound) and by every summon made inside
(engine/summons.py refuse), so the two agree whichever way the key is set. FIGHT_ABILITIES-3's write-back of the bond runs at the
trial's end (services/fight.py close).
The finder's case (the pack called, the player only defending, through the real trial), then the kind: each one who is no duellist
at the floor (a made summon, the Bound summon, the spirit Blood Summons calls, a foe's own summon, a companion and a hire), by a blow, a
tick and a rebound, and a foe's summon past its yielding point; the duellists still deciding (the examiner floored by the player and by
the summoner's own summon, the player floored, each by a blow, a tick and a rebound); a second player fighter; each way in (the door
and the cast inside, with the key as the owner set it and turned the other way); the bond written back at the trial's end through
the real scene, saved and loaded; and the key checked at startup.
Run: python tools/sim/trial_duellists_771_test.py"""
import os
import random
import sys
from types import SimpleNamespace
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("summoner", 1)
simlib.install(stub)
SHOWN = simlib.quiet_console()
sys.stdout = open(os.devnull, "w", encoding="utf-8")         # the fight's panes; the checks go to the real stdout
from engine import battlefield_builder as bb, combat, data_check, party, quests, streams, summons
from engine import effects as fx
from engine import spellcraft as SC
from scenes import combat_scene as cs
from services.fight import FightSpec, RoundIntent
from storage import saves

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


rng = random.Random(3)
NOTE = "Your Bound summon was unmade in the fight."


def fighter(fid, side, hp=10 ** 4, name=None, **kw):
    attrs = {a: 12 for a in combat.ATTRIBUTES}
    return combat.Fighter(id=fid, name=name or fid, side=side, level=10, attrs=attrs, hp=hp, max_hp=kw.pop("max_hp", hp),
                          stamina=10 ** 4, max_stamina=10 ** 4, mana=10 ** 4, max_mana=10 ** 4, weapon_damage=12,
                          weapon_attrs=["strength"], hold=2, **kw)


def summoner(fid="player", bound=True):
    c, _ = simlib.make_character("summoner", random.Random(5))
    c.level = 10
    if fid != "player":
        c.id, c.name = fid, f"Second {fid}"
    if not bound:
        c.bound_broken = True
    p = combat.fighter_from_character(c, fid)
    p.mana = p.max_mana = 10 ** 5
    p.hp = p.max_hp = 10 ** 4
    return c, p


def trial(*fs, duel=True):
    f = combat.Combat(fighters=list(fs), players=[x.id for x in fs if x.side == "player"], record=True, serial="t771", duel=duel,
                      no_rewards=duel)
    combat.ensure_field(f)
    f.opened = True
    return f


def cast(f, p, mid):
    """A summon spell cast in the fight as a round casts it: (the refusal or None, the mana paid, the bodies it brought in)."""
    move = next(m for m in p.moves if m.id == mid)
    p.cooldowns = {}
    before, paid = list(f.fighters), p.mana
    why = combat.act_ability(f, p, move, None, rng)
    return why, paid - p.mana, [x for x in f.fighters if not any(x is b for b in before)]


def floored(f, who, by):
    """A blow that would end `who`, struck by `by` (the blow's own path, engine/damage.py)."""
    f.story = []
    combat.take_damage(f, who, who.hp * 10 + 100, by, rng)


def decides_nothing(name, f, who, ex, p):
    check(f"{name}: the trial goes on, decided by nobody", f.over == "", f.over)
    check(f"...{who.name} is unmade by the fall step, as in any fight", not who.alive and who.counters.get("dead"), (who.hp, who.counters))
    check("...its fall is told, and nothing tells the duel decided", any("falls" in s or "succumbs" in s or "collapses" in s for s in f.story)
          and not any("duel is decided" in s for s in f.story) and not any(l == f"{who.name} is beaten" for l in f.log), (f.story, f.log))
    check("...the summoner and the examiner still stand", p.alive and ex.alive and not ex.fled, (p.hp, ex.hp))


# ---- the rule, read from the fight as it stands
c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
_, _, pack = cast(f, p, "call_the_pack")
hire = fighter("ally_1-0", "ally", name="Tag Along", ally_role="fighter")
pet = fighter("ally_wolf", "ally", name="Grey Wolf")
check("the duellists: the player fighter and the foe nobody summoned", combat.duellist(f, p) and combat.duellist(f, ex))
check("...a summon, a companion and a hire are none", pack and not any(combat.duellist(f, x) for x in pack + [hire, pet]))
check("who may stand in a trial: the duellists and, as the owner set it, a summon; a companion and a hire never",
      all(combat.stands(f, x) for x in [p, ex] + pack) and not combat.stands(f, hire) and not combat.stands(f, pet))
check("...and in any other fight, everyone", all(combat.stands(trial(p, ex, duel=False), x) for x in (p, ex, hire, pet)))

# ---- each one who is no duellist, at the floor: decides nothing
c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
why, paid, pack = cast(f, p, "call_the_pack")
check("(the pack is called in the trial: not refused, its mana paid)", why is None and paid > 0 and len(pack) >= 2, (why, paid, pack))
floored(f, pack[0], ex)
decides_nothing("the finder's case, bare: the examiner's blow that would end one of the pack", f, pack[0], ex, p)

c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
summons.join_bound(f, c)
warden = summons.bound_of(f, p)
check("(the Warden walks into the trial with its summoner, the door asking the rule)", warden is not None)
floored(f, warden, ex)
decides_nothing("the Bound summon floored", f, warden, ex, p)
check("...it is destroyed as in any fight: its spell is refused until the trial is over",
      f.bound_fell and "destroyed in this fight" in (cast(f, p, "call_the_warden")[0] or ""), f.bound_fell)

c, p = summoner()
p.legendary["blood_summons"] = 1
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
why, _, spirit = cast(f, p, "call_the_pack")
check("(Blood Summons calls its spirit in the trial: not refused)", why is None and len(spirit) == 1 and spirit[0].name == "the blood-spirit",
      (why, [x.name for x in spirit]))
floored(f, spirit[0], ex)
decides_nothing("the blood-spirit floored", f, spirit[0], ex, p)

c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
mine = summons.make(f, ex, next(m for m in p.moves if m.id == "call_the_pack"), form="striker", name="the examiner's shade")[0]
mine.side, mine.summon_owner = "enemy", ex.id
combat.enters(f, mine)
check("(a foe's own summon is no duellist)", not combat.duellist(f, mine))
floored(f, mine, p)
decides_nothing("a foe's own summon floored by the player", f, mine, ex, p)

for who in (fighter("ally_wolf", "ally", name="Grey Wolf"), fighter("ally_1-0", "ally", name="Tag Along", ally_role="fighter")):
    c, p = summoner()
    ex = fighter("e1", "enemy", name="the examiner")
    f = trial(p, ex, who)
    floored(f, who, ex)
    check(f"a {'hire' if who.ally_role else 'companion'} at the floor of a trial (none passes the door, below) decides nothing",
          f.over == "" and not who.alive, (f.over, who.hp))

c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
_, _, pack = cast(f, p, "call_the_pack")
body = pack[0]
body.hp = 0.01
fx.put_status(body, "poisoned", 5)
f.story = []
combat.start_turn(body, f, rng)
decides_nothing("a poison tick on one of the pack", f, body, ex, p)

c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
ex.legendary["retribution"] = 100
f = trial(p, ex)
_, _, pack = cast(f, p, "call_the_pack")
body = pack[0]
f.story = []
combat.take_damage(f, ex, body.hp * 3 + 10, body, rng)
decides_nothing("one of the pack undone by the examiner's Retribution", f, body, ex, p)

c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
mine = summons.make(f, ex, next(m for m in p.moves if m.id == "call_the_pack"), form="striker", name="the examiner's shade")[0]
mine.side, mine.summon_owner, mine.yields_at = "enemy", ex.id, 0.5
combat.enters(f, mine)
floored(f, mine, p)
check("a foe's own summon that yields at the blow that would end it: it leaves, and the trial goes on",
      f.over == "" and mine.alive and mine.fled and ex.alive, (f.over, mine.hp, mine.fled))

# ---- the duellists still decide, whatever brings them to the floor
c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
floored(f, ex, p)
check("the player's blow that would end the examiner: held at one, and the trial won", ex.hp == 1 and ex.alive and f.over == "victory",
      (ex.hp, f.over))
c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
_, _, pack = cast(f, p, "call_the_pack")
floored(f, ex, pack[0])
check("the summoner's own summon's blow that would end the examiner: held at one, and the trial won (a summon is the summoner's ability)",
      ex.hp == 1 and f.over == "victory", (ex.hp, f.over))
c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
ex.yields_at = 0.5
f = trial(p, ex)
floored(f, ex, p)
check("an examiner who would yield, struck a blow that would end them: the duel's floor decides first (held, won, not fled)",
      ex.hp == 1 and f.over == "victory" and not ex.fled, (ex.hp, f.over, ex.fled))
c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
floored(f, p, ex)
check("the examiner's blow that would end the player: held at one, and the trial lost", p.hp == 1 and p.alive and f.over == "defeat",
      (p.hp, f.over))
c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
ex.hp = 2.0
fx.put_status(ex, "poisoned", 5)
combat.start_turn(ex, f, rng)
check("a poison tick on the examiner: held at one, and the trial won", ex.hp == 1 and ex.alive and f.over == "victory", (ex.hp, f.over))

c, p = summoner()
p.legendary["retribution"] = 100
ex = fighter("e1", "enemy", name="the examiner")
ex.hp = 3.0
f = trial(p, ex)
f.story = []
combat.take_damage(f, p, 50, ex, rng)
check("the player's Retribution that would end the examiner: held at one, and the trial won", ex.hp == 1 and ex.alive and f.over == "victory",
      (ex.hp, f.over))
check("...nobody falls in it, and the rebound is told", not any("collapses" in s or "falls" in s for s in f.story)
      and any("rebounds into" in s for s in f.story) and not f.felled_by, (f.story, f.felled_by))
c, p = summoner()
p.hp = 3.0
ex = fighter("e1", "enemy", name="the examiner")
ex.legendary["retribution"] = 100
f = trial(p, ex)
combat.take_damage(f, ex, 50, p, rng)
check("the examiner's Retribution that would end the player: held at one, and the trial lost", p.hp == 1 and p.alive and f.over == "defeat",
      (p.hp, f.over))

c, p = summoner()
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, ex)
mine = summons.make(f, ex, next(m for m in p.moves if m.id == "call_the_pack"), form="striker", name="the examiner's shade")[0]
mine.side, mine.summon_owner = "enemy", ex.id
mine.hp, mine.max_hp = 5.0, 1000
combat.enters(f, mine)
ex.hp, ex.max_hp = 5.0, 1000
p.hit_element = p.element = "necrotic"


def deaths_door(target):
    """Death's Door carried by a blow too light to end anyone (it ends one under its share of health outright)."""
    for seed in range(60):
        if not target.alive or target.hp <= 1:
            return
        p.casting = {"exprs": ["deaths_door"], "tier": "moderate", "name": "Death's Door", "once": []}
        try:
            combat.apply_damage(f, p, target, 0.0001, "strikes", random.Random(seed), can_cleave=False)
        finally:
            SC.end(p)


deaths_door(mine)
check("Death's Door in a trial: a foe's own summon it reaches is ended and unmade, deciding nothing",
      not mine.alive and mine.counters.get("dead") and f.over == "", (mine.hp, f.over))
deaths_door(ex)
check("...the examiner it reaches is held by the spell's own floor, as the duel holds a duellist", ex.alive and ex.hp == 1, ex.hp)

# a second player fighter (checklist 8): a duellist of its own, and its summon none
c, p = summoner()
c2, p2 = summoner("p2")
ex = fighter("e1", "enemy", name="the examiner")
f = trial(p, p2, ex)
_, _, pack2 = cast(f, p2, "call_the_pack")
check("a second player fighter is a duellist; its summon is none", combat.duellist(f, p2) and pack2 and not combat.duellist(f, pack2[0]))
floored(f, pack2[0], ex)
check("...its summon floored decides nothing", f.over == "" and not pack2[0].alive, f.over)
floored(f, p2, ex)
check("...and it floored is held at one and loses the trial", p2.hp == 1 and f.over == "defeat", (p2.hp, f.over))

# ---- the ways in: the door, and the cast inside, with the key as set and turned the other way
NAME = "trial_duellists_door"
g = simlib.campaign(NAME, cls="summoner", seed=7, location="parth")
ws = g.scene
ws.enter("parth")
cd = ws.player.character
svc = cs.service_of(ws, random.Random(11))
wolf = ws.world.bestiary["wolf"]


def door(duel=True):
    """The fight service's begin for a trial (or an ordinary fight), handed a companion and a hire beside the player and one more told to
    hold back: (the fight, the fighters in it)."""
    svc.characters = [cd]
    examiner = fighter("e1", "enemy", name="the examiner")
    near = [combat.companion_fighter(wolf, cd.level, "ally_wolf", "Grey Wolf"),
            party.fighter({"id": "1-0", "name": "Tag Along", "role": "fighter", "level": 1})]
    later = [party.fighter({"id": "1-1", "name": "Late Comer", "role": "archer", "level": 1})]
    f, _ = svc.begin(FightSpec(creature=SimpleNamespace(name="the examiner", temperament="aggressive"), enemies=[examiner], allies=near,
                               later=later, battlefield=bb.duel_ground("the practice yard"), place="the practice yard", duel=duel))
    svc.store.save_combat(None)
    return f, sorted(x.id for x in f.fighters)


cd.bound_broken = False
f, ids = door()
warden_id = next((x.id for x in f.fighters if x.summon_form == "bound"), "")
check("the door of a trial: the player, the examiner and the Warden walk in; the companion and the hire wait outside",
      warden_id and ids == sorted(["player", "e1", warden_id]) and not f.ally_reserves, (ids, [a.id for a in f.ally_reserves]))
check("...everyone in it may stand by the rule", all(combat.stands(f, x) for x in f.fighters))
f, ids = door(duel=False)
check("...the same door to an ordinary fight lets them all in, as before", {"ally_wolf", "ally_1-0"} <= set(ids) and len(f.ally_reserves) == 1
      and any(x.summon_form == "bound" for x in f.fighters), (ids, f.ally_reserves))
cd.bound_broken = True
f, ids = door()
check("a summoner whose bond is broken: the Warden does not walk in", not any(x.summon_form == "bound" for x in f.fighters), ids)
p = f.player
for mid, what in (("call_the_warden", "the Bound spell"), ("call_the_pack", "a summon made in it")):
    why, paid, new = cast(f, p, mid)
    check(f"{what} cast in the trial: not refused, paid for, and it stands", why is None and paid > 0 and new and all(x.alive for x in new),
          (mid, why, paid))
cd.bound_broken = False

T = quests.G["trial"]
kept = dict(T)
LINE = "A test's own refusal line for a trial that keeps summons out."
T["summons"], T["summons_refused"] = False, LINE
try:
    f, ids = door()
    check("the key turned the other way: the door keeps the Warden out of a trial", not any(x.summon_form == "bound" for x in f.fighters), ids)
    p = f.player
    for mid, what in (("call_the_warden", "the Bound spell"), ("call_the_pack", "a summon made in it")):
        why, paid, new = cast(f, p, mid)
        check(f"...and the cast agrees: {what} is refused in the key's own words, nothing paid", why == LINE and paid == 0 and not new, (why, paid))
    p.legendary["blood_summons"] = 1
    why, paid, new = cast(f, p, "call_the_pack")
    check("...and Blood Summons is refused the same", why == LINE and paid == 0 and not new and p.hp == p.max_hp, (why, paid))
    f, ids = door(duel=False)
    p = f.player
    check("...while an ordinary fight takes the Warden at the door and refuses no cast", any(x.summon_form == "bound" for x in f.fighters)
          and cast(f, p, "call_the_pack")[0] is None)
finally:
    T.clear()
    T.update(kept)
check("data/rules/guild.yaml trial.summons as the owner set it: summons stand in a trial", T.get("summons") is True)
check("the key is checked at startup: the table as it stands passes", data_check.trial_problems(T) == [], data_check.trial_problems(T))
check("...a key that is not true or false is refused", data_check.trial_problems({**T, "summons": "yes"}) != [])
check("...and false without the line its refusal is told in is refused", data_check.trial_problems({**T, "summons": False}) != []
      and data_check.trial_problems({**T, "summons": False, "summons_refused": LINE}) == [])
g.close()
saves.drop(NAME)

def real_trial(name, seed, broken=False):
    """A stub summoner of level 10, due rank E, with a hire in the party (and its companion), takes the trial at the hall."""
    g = simlib.campaign(name, cls="summoner", seed=seed)
    ws = g.scene
    c = ws.player.character
    c.level, c.bound_broken = 10, broken
    ws.player.guild_rank = "F"
    ws.player.guild_done = {"F": 5}
    ws.player.party = [{"id": "1-0", "name": "Tag Along", "role": "fighter", "level": 8, "rank": "F", "blurb": "x", "permanent": True,
                        "base_level": 8, "hired_at": 10, "bond": 20}]
    ws.store.meta.minutes = 1440 * 30 + 600
    ws.enter("guild_house")
    SHOWN.clear()
    ws.trial_start("E")
    return g, ws


g, ws = real_trial("trial_duellists_start", 1)
f = ws.combat.fight
start = sorted(x.side + (":" + x.summon_form if x.summon_form else "") for x in f.fighters)
check("the real trial begins with the duellists and the Warden: the companion and the hire wait outside",
      start == ["ally:bound", "enemy", "player"], start)
note = next((t for k, t in SHOWN if k == "note" and t.startswith("Trial for rank")), "")
check("the trial's note names the duellists as the ones whose end decides it, not any fighter",
      "the first blow that would end either of you decides it" in note and "a fighter" not in note, note)
ws.combat.finish()
g.close()
saves.drop("trial_duellists_start")

# ---- the finder's case, through the real trial: the pack called, then the player only defends, six seeds. As the finder ran it, the
# Warden is not in it (its bond broken; the door then kept it out of every trial), so the dice are the finder's until a summon falls.
BEATEN, WENT_ON = [], []                             # the summons beaten in them; the seeds where the trial went on past one
for seed in range(1, 7):
    NAME = f"trial_duellists_{seed}"
    g, ws = real_trial(NAME, seed, broken=True)
    f = ws.combat.fight
    svc = ws.combat.service
    p = f.player
    beaten = []
    svc.round(f, RoundIntent(kind="ability", ability="call_the_pack"))
    called = [x for x in f.fighters if x.summon_form == "swarm"]
    rounds = 1
    while not f.over and rounds < 40:
        beaten += [l for l in f.log if l.endswith(" is beaten")]
        fell = sum(1 for x in f.fighters if x.counters.get("fell"))
        svc.round(f, RoundIntent(kind="defend"))
        if not f.over and sum(1 for x in f.fighters if x.counters.get("fell")) > fell:
            WENT_ON.append(seed)                     # a summon beaten this round, and the trial still undecided
        rounds += 1
    beaten += [l for l in f.log if l.endswith(" is beaten")]
    BEATEN.extend(x.name for x in f.fighters if x.summon_form and x.counters.get("fell"))
    ex = f.enemies()[0] if f.enemies() else f.get("e1")
    over = f.over
    gone = [x for x in f.fighters if x.summon_form and not x.alive]
    SHOWN.clear()
    ws.combat.finish()
    promoted = ws.player.guild_rank == "E"
    check(f"seed {seed}: the pack called, the player only defending: decided only by a duellist ({over}, {beaten})",
          called and all(l in (f"{p.name} is beaten", f"{ex.name} is beaten") for l in beaten)
          and (over != "victory" or ex.hp <= 1) and (over != "defeat" or p.hp <= 1) and promoted == (over == "victory"),
          (over, beaten, ex.hp, p.hp, promoted))
    check(f"seed {seed}: ...every summon beaten in it was unmade",
          all(x.counters.get("dead") for x in gone), [(x.name, x.hp, x.counters) for x in gone])
    g.close()
    saves.drop(NAME)
check("...and the six are not empty: summons were beaten in them, and a trial went on past a summon beaten in its round",
      len(BEATEN) > 0 and len(WENT_ON) > 0, (BEATEN, WENT_ON))

# ---- the guild's rules, as a guild person knows them: the trial decided by the end of either duellist, not any fighter
ws_rules = simlib.campaign("trial_duellists_rules", cls="summoner", seed=3)
rules = [l for l in ws_rules.scene.guild_knowledge(SimpleNamespace(role="guild_clerk")) if "trial" in l]
check("the guild's rules say neither duellist can die and the blow that would end either decides it, never any fighter",
      rules and all("where neither of you can die (the blow that would end either of you decides it)" in l and "a fighter" not in l
                    and "nobody can die" not in l for l in rules), rules[:1])
ws_rules.close()
saves.drop("trial_duellists_rules")

# ---- the end: the bond written back at the trial's end, through the real scene, saved and loaded
NAME = "trial_duellists_scene"
g = simlib.campaign(NAME, cls="summoner", seed=494)
ws, store = g.scene, g.store
seed = store.meta.seed
pick = {"ability": "", "then": "attack"}


def choose(u, k):
    f = ws.combat.fight
    up = f.enemies()
    target = up[0].id if up else ""
    if pick["ability"] and f.player.cooldowns.get(pick["ability"], 0) <= 0:
        mid, pick["ability"] = pick["ability"], ""
        return {"kind": "ability", "ability": mid, "target": target}
    return {"kind": pick["then"], "target": target}


stub.a_CombatIntent = choose


def scene_trial(n, rank, due, kill=False, ability=""):
    """One trial through the scene: asked for at the hall, played by the turn, ended by the scene. Returns (the Warden walked in, it
    stood at the last round, the rank after, the notes shown, the character loaded from the save)."""
    ws.player.guild_rank = rank
    ws.player.guild_done = due
    ws.player.trial = {}
    store.save_player(ws.player)
    streams.begin(seed, 100000 + n, f"trial{n}")
    SHOWN.clear()
    ws.handle("I'd like to take the trial")
    sc = ws.combat
    f = sc.fight
    walked = summons.bound_of(f, f.player) is not None
    if kill and walked:
        b = summons.bound_of(f, f.player)
        combat.take_damage(f, b, b.hp * 10, f.get("e1"), rng, "magical")
    f.player.max_hp = f.player.hp = f.player.max_hp * 8
    pick["ability"], pick["then"] = ability, "attack"
    store.save_combat(sc.to_json())
    stood = None
    for r in range(30):
        if ws.combat is None:
            break
        if r == 2:
            for e in ws.combat.fight.enemies():
                e.hp = 1.0
            store.save_combat(ws.combat.to_json())
        streams.begin(seed, 1000 * n + r + 1, f"t{n}r{r + 1}")
        ws.turn("I fight on")
        if ws.combat is not None:
            stood = summons.bound_of(ws.combat.fight, ws.combat.fight.player) is not None
    if ws.combat is not None:
        store.save_combat(None)
        ws.combat = None
    return walked, stood, ws.player.guild_rank, [t for k, t in SHOWN if k == "note"], store.load_player().character


ws.player.character.level = 10
ws.player.character.bound_broken = True
ws.player.location = "guild_house"
ws.enter("guild_house")
ws.store.meta.minutes = 1440 * 30 + 600
walked, stood, rank, notes, saved = scene_trial(1, "F", {"F": 5}, ability="call_the_warden")
check("the scene, a trial with the bond broken: the Warden does not walk in; its spell is cast in the trial and it stands",
      not walked and stood, (walked, stood))
check("...the trial won, the character loaded from the save carries the mended bond, and no note says it was unmade",
      rank == "E" and not saved.bound_broken and not any(NOTE in n for n in notes), (rank, saved.bound_broken, notes))
ws.player.character.level = 25
walked, stood, rank, notes, saved = scene_trial(2, "E", {"E": 5}, kill=True)
check("the scene, the next trial: the Warden mended in the last walks in, and is beaten in this one", walked, saved.bound_broken)
check("...the trial decided by the duellists all the same (won), the save carries the broken bond, and the note is shown",
      rank == "D" and saved.bound_broken and any(NOTE in n for n in notes), (rank, saved.bound_broken, notes))
g.close()
saves.drop(NAME)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
