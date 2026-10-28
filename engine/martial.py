"""Martial techniques (data/rules/martial.yaml, f233): a stamina ability's form (strike, sweep, flurry, windup, counter) and its
maneuver (trip, hamstring, rend, disarm, stagger, pin, shove, hook, sunder, feint) - deterministic, decided by size. Martial control
is one maneuver as the whole ability, contested."""
from __future__ import annotations

from pathlib import Path

import yaml

from engine import combat as C
from engine import ability_traits as AT

ROOT = Path(__file__).resolve().parent.parent
M = yaml.safe_load((ROOT / "data" / "rules" / "martial.yaml").read_text(encoding="utf-8"))
FORMS: dict = M["forms"]
MANEUVERS: dict = M["maneuvers"]
SIZES = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]


# ---- what the cards say -----------------------------------------------------------------------------------------------------

def is_technique(a) -> bool:
    """A martial technique: a stamina ability that is not a channeled strike."""
    return getattr(getattr(a, "resource", ""), "value", getattr(a, "resource", "")) == "stamina" and not getattr(a, "channel", False)


def flurry_total(hits: int) -> float:
    return float(M["flurry"]["total"].get(int(hits), M["flurry"]["total"][max(M["flurry"]["total"])]))


def form_text(fid: str, hits: int = 0) -> str:
    f = FORMS.get(fid)
    if not f:
        return ""
    each = round(flurry_total(hits) / hits * 100) if hits else 0
    return f["text"].format(share_pct=round(f.get("share", 1) * 100), hits=hits, each_pct=each,
                            mult_pct=round(f.get("mult", 1) * 100), weaken_pct=round((1 - f.get("weaken", 1)) * 100))


def maneuver_text(mid: str, tier) -> str:
    m = MANEUVERS.get(mid)
    if not m:
        return ""
    t = AT.tier_of(tier)
    return m["text"].format(pct=(m.get("pct") or {}).get(t, ""), cap=m.get("cap", ""))


def most_hits(families) -> int:
    table = M["flurry"]["most_hits"]
    found = [table[f] for f in (families or []) if f in table]
    return max(found) if found else int(M["flurry"]["default_most"])


# ---- size ---------------------------------------------------------------------------------------------------------------------

def _size(f) -> int:
    """Its size step, one larger while Enlarged."""
    base = SIZES.index(f.size) if getattr(f, "size", "") in SIZES else 2
    grown = any(b.get("kind") == "enlarge" for b in (getattr(f, "buffs", None) or {}).values())
    return min(len(SIZES) - 1, base + (1 if grown else 0))


def fits(att, t, mid: str) -> bool:
    """Whether this maneuver can work on this target at all: its size limit, blood, a weapon to knock aside."""
    m = MANEUVERS[mid]
    if "size_up" in m and _size(t) - _size(att) > int(m["size_up"]):
        return False
    if m.get("armed_only") and not armed(t):
        return False
    if mid == "rend":
        from engine import afflictions
        return not afflictions.bloodless(t)
    return True


def armed(f) -> bool:
    """Whether this fighter carries a weapon that can be knocked aside: by its kind if it has one, else people (the player, hirelings)."""
    if getattr(f, "category", ""):
        return f.category in M["armed_categories"]
    return f.side in ("player", "ally") and not getattr(f, "creature", "")


# ---- maneuvers --------------------------------------------------------------------------------------------------------------

def maneuver(combat, att, t, move, rng, contested: bool = False) -> bool:
    """The maneuver lands on a target already hit (or, for martial control, one that lost the contest). Returns True if it took."""
    mid = getattr(move, "maneuver", "")
    if not mid or mid not in MANEUVERS or t is None or not t.alive:
        return False
    m = MANEUVERS[mid]
    if not fits(att, t, mid):
        why = ("too big to " + m["label"].lower()) if "size_up" in m and _size(t) - _size(att) > int(m["size_up"]) else \
            ("has no weapon to knock aside" if m.get("armed_only") else "has no blood to spill")
        C.tell(combat, f"{C.who(t)} {why} ({m['label']})")
        return False
    if mid in ("stagger", "shove", "hook", "pin", "trip") and any(b.get("kind") == "stoneform" for b in (t.buffs or {}).values()):
        C.tell(combat, f"{C.who(t)} {C.vb(t, 'are', 'is')} stone - {m['label'].lower()} does nothing")
        return False
    if mid == "stagger":
        broke = []
        if t.winding:
            t.winding = {}
            broke.append("the blow it was winding up")
        if t.charging:
            t.charging = {}
            broke.append("what it was gathering")
        C.leave_open(combat, t)
        C.tell(combat, f"{C.who(t)} {C.vb(t, 'are', 'is')} knocked off balance"
               + (f" - {' and '.join(broke)} never comes" if broke else "") + f" ({m['label']})")
        return True
    if mid == "sunder":
        cut = min(float(m["cap"]), t.sundered + float(m["pct"][AT.tier_of(move.tier)]))
        if cut > t.sundered:
            t.sundered = cut
            C.tell(combat, f"{C.whose(t)} armor cracks under it ({m['label']}: {cut:g}% broken)")
        return True
    if mid in ("shove", "hook"):
        held = move.rider
        move.rider = mid
        try:
            C.apply_rider(combat, att, t, move, rng)
        finally:
            move.rider = held
        return True
    if "status" in m and C.add_status(combat, t, m["status"], int(m["rounds"]), att):
        if m["status"] == "grappled":
            from engine import battlefield as bf
            bf.engage(combat, att, t)
        combat.log.append(f"{t.name} is {m['status']} ({m['label']})")
        C.tell(combat, f"{C.who(t)} {C.STATUS_WORDS.get(m['status'], ('', 'is ' + m['status']))[0 if t.side == 'player' else 1]} ({m['label']})")
        return True
    return False


def control(combat, att, move, target, rng) -> None:
    """Martial control: the maneuver is the whole ability, contested with the technique's attributes; a partial success still
    lands it, a round shorter where it has rounds."""
    enemies = [e for e in combat.fighters if e.alive and not e.fled and (e.side == "enemy") != (att.side == "enemy")]
    t = target if target is not None and target.alive else (enemies[0] if enemies else None)
    if t is None:
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'look', 'looks')} for someone to use {move.name} on, but there is no one")
        return
    m = MANEUVERS.get(move.maneuver, {})
    if not fits(att, t, move.maneuver):
        maneuver(combat, att, t, move, rng)                # says why it cannot work
        return
    grade = C.contest(att, t, att.weapon_attrs, rng)
    if grade == "none":
        combat.log.append(f"{att.name} uses {move.name} on {t.name}: resisted")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'try', 'tries')} {move.name} on {C.who(t)}, but {C.vb(t, 'you see', 'it sees')} it coming")
        return
    combat.log.append(f"{att.name} uses {move.name} on {t.name}" + (" (partial)" if grade == "partial" else ""))
    rounds = m.get("rounds")
    if grade == "partial" and rounds and rounds > 1:
        m = dict(m, rounds=rounds - 1)
        held = MANEUVERS[move.maneuver]
        MANEUVERS[move.maneuver] = m
        try:
            took = maneuver(combat, att, t, move, rng)
        finally:
            MANEUVERS[move.maneuver] = held
    else:
        took = maneuver(combat, att, t, move, rng)
    if took:
        t.counters["controlled"] = t.counters.get("controlled", 0) + 1
    if grade == "partial":
        C.tell(combat, f"{C.who(t)} half {C.vb(t, 'slip', 'slips')} it")


# ---- forms --------------------------------------------------------------------------------------------------------------------

def sweep_targets(combat, att, t) -> list:
    foes = [e for e in combat.fighters if e.alive and not e.fled and (e.side == "enemy") != (att.side == "enemy")]
    engaged = [e for e in foes if e.id in att.engaged_with]
    if t is not None and t.alive and t not in engaged and t.zone_id == att.zone_id:
        engaged = [t] + engaged
    return engaged or ([t] if t is not None else [])


def flurry(combat, att, t, move, mult, rng) -> bool:
    hits = max(2, int(getattr(move, "hits", 0) or 2))
    each = flurry_total(hits) / hits
    landed = False
    strikes: list[dict] = []
    s0, l0 = len(combat.story), len(combat.log)
    for i in range(hits):
        if not t.alive:
            break
        n0 = len(combat.hits)
        landed |= C.apply_damage(combat, att, t, mult * each, f"uses {move.name} on" if i == 0 else "strikes again at", rng,
                                 how=f"with {move.name}" if i == 0 else f"as {move.name} keeps coming",
                                 can_cleave=(i == 0), can_flurry=(i == 0))
        rec = combat.hits[n0] if len(combat.hits) > n0 else None          # the strike's own record is the first its call made
        if rec is not None and rec.get("att") == att.name and rec.get("dfn") == t.name:
            strikes.append(rec)
    one_attack(combat, att, t, move, strikes, hits, s0, l0)
    return landed


NUMBERS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
ORDINALS = {2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh", 8: "eighth"}
LANDS = ("hit", "crit", "graze")


def flurry_figure(strikes: list[dict]) -> str:
    """One figure for a flurry: '(3 hits, 15 damage)', '(2 of 3 hits, 1 critical, 14 damage +2 from the open wound, bleeding)'."""
    made = len(strikes)
    landed = [r for r in strikes if r.get("outcome") in LANDS]
    if not landed:
        return f"({made} strikes, all missed)"
    crits = sum(1 for r in landed if r["outcome"] == "crit")
    total = sum(int(r.get("final") or 0) for r in landed)
    bleed = sum(int(r.get("bleed") or 0) for r in strikes)
    inflicted = list(dict.fromkeys(s for r in strikes for s in r.get("inflicted", [])))
    count = f"{made} hits" if len(landed) == made else f"{len(landed)} of {made} hits"
    return (f"({count}" + (f", {crits} critical" if crits else "") + f", {total} damage"
            + (f" +{bleed} from the open wound" if bleed else "") + "".join(f", {s}" for s in inflicted) + ")")


def one_attack(combat, att, t, move, strikes: list[dict], planned: int, s0: int, l0: int) -> None:
    """(f371) A flurry is one attack: its strikes' lines in the story become one line with one marker, their records one record with one
    figure (each strike kept in `parts`, for the working on hover), their lines in the combat log one line. Without records (the odds being
    simulated) nothing is told, so nothing is merged."""
    if not combat.record or len(strikes) < 2:
        return
    import re
    head = strikes[0]
    tags = {r["tag"] for r in strikes}
    parts = [dict(r) for r in strikes]
    made = len(strikes)
    landed = [r for r in strikes if r.get("outcome") in LANDS]
    crits = sum(1 for r in landed if r["outcome"] == "crit")
    grazes = sum(1 for r in landed if r["outcome"] == "graze")
    total = sum(int(r.get("final") or 0) for r in landed)
    num = lambda n: NUMBERS.get(n, str(n))
    if len(landed) == made:
        how = "both land" if made == 2 else "every one lands"
    elif not landed:
        how = "both miss" if made == 2 else "none of them lands"
    else:
        wide = made - len(landed)
        how = f"{num(len(landed))} {'lands' if len(landed) == 1 else 'land'} and {num(wide)} {'goes' if wide == 1 else 'go'} wide"
    if crits:
        how += ", one of them a perfect strike" if crits == 1 else f", {num(crits)} of them perfect strikes"
    elif grazes and grazes == len(landed):
        how += ", only glancing"
    line = f"{C.who(att)} {C.vb(att, 'use', 'uses')} {move.name} on {C.who(t)}, {num(made)} strikes in one motion: {how}"
    if landed:
        line += f" - together {C.severity(total, t.max_hp)}"
    if t.alive:
        line += f" - {C.who(t)} {C.vb(t, 'are', 'is')} {C.condition(t)}"
    elif made < planned:
        line += f" - {C.who(t)} {C.vb(t, 'are', 'is')} down before the {ORDINALS.get(made + 1, 'next')} strike can follow"
    line = line[0].upper() + line[1:] + f" [{head['tag']}]"
    kept, at = [], None
    for s in combat.story[s0:]:
        m = re.search(r" \[(h\d+)\]$", s)
        if m and m.group(1) in tags:
            if at is None:
                at = len(kept)
            continue
        kept.append(s)
    kept.insert(at if at is not None else 0, line)
    combat.story[s0:] = kept
    head.update(label=f"uses {move.name} on", parts=parts, planned=planned, final=total,
                outcome="crit" if crits else ("hit" if landed else "miss"), figure=flurry_figure(strikes))
    head.pop("bleed", None)
    head.pop("inflicted", None)
    combat.hits[:] = [h for h in combat.hits if h is head or h.get("tag") not in tags]
    own = (f"{att.name} uses {move.name} on {t.name}:", f"{att.name} strikes again at {t.name}:")
    lines = [l for l in combat.log[l0:] if not l.startswith(own)]
    combat.log[l0:] = [f"{att.name} uses {move.name} on {t.name}: {head['figure'][1:-1]}"] + lines


def ready_counter(combat, att, move) -> None:
    att.counters["counter_round"] = combat.round
    att.counter_move = move.model_dump()
    combat.log.append(f"{att.name} readies {move.name}")
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'settle', 'settles')} into {move.name}, waiting for someone to come at {'you' if att.side == 'player' else 'it'}")


def countering(att, dfn) -> bool:
    """Whether this defender is ready to meet this attacker's blow (engaged, and its counter is still standing)."""
    from engine import battlefield as bf
    return bool(dfn.counter_move) and (att.side == "enemy") != (dfn.side == "enemy") and bf.engaged_pair(att, dfn) and dfn.alive


def strike_back(combat, dfn, att, rng) -> None:
    move = C.Move(**dfn.counter_move)
    dfn.counter_move = {}
    if not att.alive or not dfn.alive:
        return
    mult = (move.power or C.RULES["damage"]["multiplier"][move.tier]) * FORMS["counter"]["mult"]
    C.tell(combat, f"{C.who(dfn)} {C.vb(dfn, 'meet', 'meets')} it with {move.name}")
    if C.apply_damage(combat, dfn, att, mult, "answers with", rng, how=f"with {move.name}", can_riposte=False, can_cleave=False):
        maneuver(combat, dfn, att, move, rng)
