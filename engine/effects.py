"""(f499) What a fight remembers of itself between rounds, on the saved fight (pillar 1: a fight remembers the same in-process and after
a reload; decision 2): the player's quarry (one row a fight), who placed a withering affliction (one row an afflicted fighter), the last
heal (one row a fight). An ActiveEffect is a row of the fight's `effects` list (engine/combat.py Combat), written by the perks and the
heals and read back by them, so a mark is in the row the save holds, goes back with the row when a round rolls back, and goes with the
row when the fight ends. The list is capped at combat.yaml effects_keep: the oldest expired rows go first, then the oldest.

(f507) The rows a fighter carries too: every status (its rounds, who placed it, its strength: an ignite's burn a round, a wound's size,
a poison's stacks and the stacks that never fade), every buff and every curse is a row of the fighter's own `effects` list, and every
ground effect a row of the fight's, keyed by its zone. The old names (Fighter.statuses, status_from, ignite, poison, poison_fixed,
bleed, buffs, curses; Combat.zone_effects) are read-only views over the rows: a reader sees what the rows hold and nothing else, so a
wipe leaves no stale source and no stale strength behind. The writers are here and nowhere else (tools/purity.py effect_writes):
put_status, end_status, tick_status, set_strength and clear for statuses; put_buff and end_buff; put_curse and keep_curses; put_ground
and drop_ground. A row's slot says which view it belongs to; its id is slot:key, so a buff and a status of one name cannot collide."""
from __future__ import annotations

from typing import Callable

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class EffectDef(BaseModel):
    """(f504) A kind of effect a fight carries between rounds, as data/rules/active_effects.yaml declares it: its family (one of
    FAMILIES), how it ends (EXPIRY), what a second landing does (STACKING), and for a status the combat.yaml row that holds its stat
    deltas. Frozen: a kind is read, never changed in play."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    family: str
    expiry: str
    stacking: str
    deltas: str = ""


_T = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "active_effects.yaml").read_text(encoding="utf-8"))
_ST = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "stages.yaml").read_text(encoding="utf-8"))
ELIGIBLE: tuple[str, ...] = tuple(_ST["status_eligibility"])     # (f507) the stages a status passes before it lands, in order
FAMILIES: tuple[str, ...] = tuple(_T["families"])
EXPIRY: tuple[str, ...] = tuple(_T["expiry"])
STACKING: tuple[str, ...] = tuple(_T["stacking"])
KINDS: dict[str, EffectDef] = {k: EffectDef(id=k, **v) for k, v in _T["kinds"].items()}


class ActiveEffect(BaseModel):
    id: str                      # one a kind for the fight (quarry, last_heal), or one a fighter (withering:<fighter id>); (f507) slot:key
    kind: str                    # quarry | withering | last_heal; (f507) a status name, a buff's kind, curse, a ground effect's name
    family: str = ""             # mark | affliction | heal; (f507) the table's family (active_effects.yaml)
    slot: str = ""               # (f507) the view the row belongs to: status | buff | curse | ground; "" for the fight's own marks
    source: str = ""             # the fighter who placed it
    target: str = ""             # the fighter it is on
    until: int = 0               # the last round it holds for; 0 while the fight lasts
    left: int = 0                # rounds left, for a kind that counts down
    charges: int = 0             # uses left, for a kind that spends
    value: float = 0.0           # what it carries (a heal's size)
    data: dict = {}


def keep() -> int:
    from engine import combat
    return int(combat.RULES.get("effects_keep", 64))


def expired(e: ActiveEffect, round_: int) -> bool:
    return bool(e.until) and round_ > e.until


def put(combat, e: ActiveEffect) -> ActiveEffect:
    """Keep this row on the fight, in place of the row with its id, and the list within its cap."""
    rows = [r for r in combat.effects if r.id != e.id]
    rows.append(e)
    combat.effects = cap(rows, combat.round)
    return e


def cap(rows: list, round_: int, limit: int | None = None) -> list:
    """At most `limit` rows: the oldest expired go first, then the oldest."""
    limit = keep() if limit is None else limit
    rows = list(rows)
    while len(rows) > limit:
        gone = next((r for r in rows if expired(r, round_)), rows[0])
        rows.remove(gone)
    return rows


def get(combat, kind: str, target: str = "") -> ActiveEffect | None:
    """The row of this kind (on this fighter, when one is named), or None."""
    for r in combat.effects:
        if r.kind == kind and (not target or r.target == target):
            return r
    return None


def drop(combat, kind: str, target: str = "") -> None:
    combat.effects = [r for r in combat.effects if not (r.kind == kind and (not target or r.target == target))]


# ---------- (f507) the rows a fighter carries: statuses, buffs, curses ----------

SLOTS = ("status", "buff", "curse", "ground")
STRENGTHS = ("burning", "bleeding", "poisoned")      # the statuses with a strength of their own (engine/afflictions.py)


def rows(f, slot: str) -> list:
    """This fighter's rows of one slot, in the order they landed."""
    return [r for r in f.effects if r.slot == slot]


def status_row(f, status: str) -> ActiveEffect | None:
    for r in f.effects:
        if r.slot == "status" and r.kind == status:
            return r
    return None


def _whole(rounds, what: str) -> int:
    if rounds != int(rounds):
        raise ValueError(f"{what}: rounds are whole, not {rounds}")
    return int(rounds)


def _id_of(source) -> str:
    return "" if source is None else (source if isinstance(source, str) else source.id)


def put_status(f, status: str, rounds, source=None) -> ActiveEffect:
    """A status on this fighter for these rounds. A row it already has is refreshed in its place, its strength kept; a new row is
    appended, so the order the statuses landed in (the order they are worn down in) holds. The source, when given, is who placed it;
    when not, the row keeps the one it had."""
    left = _whole(rounds, status)
    r = status_row(f, status)
    if r is None:
        r = ActiveEffect(id=f"status:{status}", kind=status, slot="status", family="status", left=left, source=_id_of(source),
                         data={"stacks": [], "fixed": []} if status == "poisoned" else {})
        f.effects.append(r)
    else:
        r.left = left
        if source is not None:
            r.source = _id_of(source)
    return r


def end_status(f, status: str) -> int | None:
    """The status goes, its source and its strength with it. Returns the rounds it had left, or None when it was not there."""
    r = status_row(f, status)
    if r is None:
        return None
    f.effects.remove(r)
    return r.left


def tick_status(f, status: str, n: int = -1) -> int:
    """The rounds left move by n (worn down by one, lengthened by a perk). Returns what is left; the caller ends it at zero."""
    r = status_row(f, status)
    if r is None:
        raise KeyError(status)
    r.left += n
    return r.left


def set_strength(f, status: str, value, fixed=None) -> ActiveEffect | None:
    """The strength of a burn (the damage a round), a wound (its size) or a poisoning (its stacks, and with `fixed` the stacks that
    never fade). The affliction law sets it as the status lands, before add_status records the rounds: a status not yet on the fighter
    gets its row at no rounds, and the rounds follow at once. A strength of nothing on a status that is not there is nothing: no row."""
    r = status_row(f, status)
    if r is None:
        if not value and not fixed:
            return None
        r = put_status(f, status, 0)
    if status == "poisoned":
        r.data["stacks"] = list(value)
        if fixed is not None:
            r.data["fixed"] = list(fixed)
    else:
        r.value = float(value)
    return r


def clear(f) -> None:
    """Every status goes, each with its source and its strength (a Rescue, a boss's last stand). Buffs and curses stay."""
    f.effects[:] = [r for r in f.effects if r.slot != "status"]


# views: what the fighter's old names read from the rows

def statuses_of(f) -> dict[str, int]:
    return {r.kind: r.left for r in f.effects if r.slot == "status"}


def sources_of(f) -> dict[str, str]:
    return {r.kind: r.source for r in f.effects if r.slot == "status" and r.source}


def strength_of(f, status: str):
    """A burn's or a wound's strength (0.0 without the status); a poisoning's stacks, by reference ([] without)."""
    r = status_row(f, status)
    if status == "poisoned":
        return r.data["stacks"] if r is not None else []
    return r.value if r is not None else 0.0


def fixed_of(f) -> list:
    r = status_row(f, "poisoned")
    return r.data["fixed"] if r is not None else []


def put_buff(f, key: str, data: dict) -> ActiveEffect:
    """A timed effect (a stance, a command, a relic's power, a renew) under its key: the buff dict as the caller wrote it, held by the
    row by reference (its readers tick data["rounds"] in place). A row of the same key is replaced in its place; a new one appended.
    The kind is the table's when the dict names one, else relic_buff."""
    kind = data.get("kind") if data.get("kind") in KINDS else "relic_buff"
    r = ActiveEffect(id=f"buff:{key}", kind=kind, slot="buff", family=KINDS[kind].family)
    r.data = data                                        # the caller's dict itself, not a copy: its readers tick it in place
    for i, old in enumerate(f.effects):
        if old.id == r.id:
            f.effects[i] = r
            return r
    f.effects.append(r)
    return r


def end_buff(f, key: str) -> dict | None:
    """The buff goes. Returns its dict, or None when it was not there."""
    for r in f.effects:
        if r.slot == "buff" and r.id == f"buff:{key}":
            f.effects.remove(r)
            return r.data
    return None


def buffs_of(f) -> dict[str, dict]:
    return {r.id[5:]: r.data for r in f.effects if r.slot == "buff"}


def put_curse(f, data: dict) -> ActiveEffect:
    """A curse laid on this fighter (they stack: each casting is its own row), its dict held by reference."""
    n = 1 + max((int(r.id.split(":")[1]) for r in f.effects if r.slot == "curse"), default=0)
    r = ActiveEffect(id=f"curse:{n}", kind="curse", slot="curse", family=KINDS["curse"].family, source=str(data.get("by", "")),
                     left=_whole(data.get("left", 0), "curse"))
    r.data = data
    f.effects.append(r)
    return r


def keep_curses(f, keep: list) -> None:
    """Only these curses (the dicts the rows hold) stay: the rest have done their work."""
    f.effects[:] = [r for r in f.effects if r.slot != "curse" or any(r.data is d for d in keep)]


def curses_of(f) -> list:
    return [r.data for r in f.effects if r.slot == "curse"]


# ---------- (f507) the ground a fight carries: one row a zone and effect ----------

def put_ground(combat, zone: str, kind: str, data: dict, key: str = "") -> ActiveEffect:
    """A ground effect on a zone (frozen ground, a pyre's fire, a drift, a barricade, a seal on one edge: `key` tells the edges apart),
    its dict held by reference. A row of the same zone, kind and key is replaced."""
    until = data.get("until", data.get("frozen_until", 0)) or 0
    r = ActiveEffect(id=f"ground:{kind}@{zone}" + (f":{key}" if key else ""), kind=kind, slot="ground", target=zone,
                     family=KINDS[kind].family if kind in KINDS else "", until=int(until) if until == int(until) else 0)
    r.data = data
    return put(combat, r)


def ground_rows(combat, zone: str | None = None) -> list:
    return [r for r in combat.effects if r.slot == "ground" and (zone is None or r.target == zone)]


def drop_ground(combat, zone: str, kind: str | None = None, row_id: str | None = None) -> None:
    """The ground effects of a zone go: all of them, those of one kind, or the one row named."""
    combat.effects = [r for r in combat.effects if not (r.slot == "ground" and r.target == zone and (kind is None or r.kind == kind)
                                                        and (row_id is None or r.id == row_id))]


def ground_of(combat) -> dict[str, dict]:
    """The view: {zone: {effect name: its dict}}, the seals of a zone gathered as a list under "sealed"."""
    out: dict[str, dict] = {}
    for r in combat.effects:
        if r.slot != "ground":
            continue
        zone = out.setdefault(r.target, {})
        if r.kind == "sealed":
            zone.setdefault("sealed", []).append(r.data)
        else:
            zone[r.kind] = r.data
    return out


# ---------- (f507) eligibility: the stages a status passes before it lands (data/rules/stages.yaml status_eligibility) ----------

class Landing:
    """What a status landing carries through the stages: the fight, the fighter it is landing on, the status and the rounds (a stage
    may change either: an archon's chill lasts longer, a perk turns one affliction into another), the source when the caller knows it,
    the fighter's mechanics, and the element behind the status (a burn's fire, the hit element behind a chill or a cut)."""

    def __init__(self, combat, f, status: str, rounds, source):
        from engine import combat as C
        self.combat, self.f, self.status, self.rounds, self.source = combat, f, status, rounds, source
        self.fm = C.mechanics(f, combat)
        self.element = C.ELEMENT_STATUS.get(status) or ((source.hit_element or source.element) if source is not None
                                                     and status in ("slowed", "blinded", "bleeding", "prone", "petrified") else "")


def unyielding(l: Landing):
    from engine import combat as C
    if "unyielding" in l.fm and l.status in ("stunned", "prone"):
        l.combat.log.append(f"{l.f.name} stands firm (Unyielding)")
        C.tell(l.combat, f"{C.who(l.f)} {C.vb(l.f, 'stand', 'stands')} firm, unshaken (Unyielding)")
        return False


def earthshaker(l: Landing):
    if "earthshaker" in l.fm and l.status == "prone":
        return False


def stoneform(l: Landing):
    from engine import combat as C
    if "stoneform" in l.fm and l.status in ("stunned", "prone", "grappled"):
        C.tell(l.combat, f"{C.who(l.f)} {C.vb(l.f, 'stand', 'stands')} like stone, unmoved (Stoneform)")
        return False


def iron_will(l: Landing):
    from engine import combat as C
    f = l.f
    if "iron_will" in l.fm and l.status in ("stunned", "prone", "slowed", "frightened", "blinded") and f.counters.get("shrugged", 0) < l.fm["iron_will"]:
        f.counters["shrugged"] = f.counters.get("shrugged", 0) + 1
        l.combat.log.append(f"{f.name} shrugs it off (Iron Will)")
        C.tell(l.combat, f"{C.who(f)} {C.vb(f, 'shrug', 'shrugs')} it off as if it were nothing, and the effort sharpens {C.whose(f)} resolve (Iron Will)")
        return False


def element_ward(l: Landing):
    """An archon of the element behind the status shrugs it off (Attunement, f246)."""
    from engine import combat as C
    if l.element and C.warded(l.f, l.element):
        C.tell(l.combat, f"{C.who(l.f)}, an archon of {l.element}, {C.vb(l.f, 'shrug', 'shrugs')} it off (Attunement)")
        return False


def attune_extend(l: Landing):
    """An archon's chills, witherings and lights last a round longer (f246)."""
    from engine import combat as C
    if l.element and C.attuned(l.source, l.element) and l.status in ("slowed", "withered", "unraveled", "illuminated", "blinded"):
        l.rounds += 1


def sanctified(l: Landing):
    from engine import combat as C
    if "sanctified" in l.fm and l.status in ("bleeding", "frightened"):
        l.combat.log.append(f"{l.f.name} is untouched by it (Sanctified)")
        C.tell(l.combat, f"a holy calm keeps {C.who(l.f)} untouched (Sanctified)")
        return False


def boss_resisted(l: Landing):
    """Legendary resistance: a boss turns aside the first few attempts (engine/bosses.py resisted spends a charge)."""
    if l.f.boss:
        from engine import bosses
        if bosses.resisted(l.combat, l.f, l.status):
            return False


def perk_transform(l: Landing):
    """The perks that change how an affliction lands (engine/combat_perks.py on_status): turned aside, passed on, or made another."""
    from engine import combat_perks
    landed = combat_perks.on_status(l.combat, l.f, l.status, l.rounds, l.source)
    if landed is None:
        return False
    l.status, l.rounds = landed


def bloodless(l: Landing):
    """Nothing to bleed (combat.yaml bleed.bloodless)."""
    if l.status == "bleeding":
        from engine import afflictions
        if afflictions.bloodless(l.f):
            return False


def affliction_law(l: Landing):
    """Ignite, poison and bleeding: one law for every source (engine/afflictions.py apply sets the strength and gives the rounds)."""
    if l.status in STRENGTHS:
        from engine import afflictions
        l.rounds = afflictions.apply(l.combat, l.f, l.status, l.rounds, l.source)


def record(l: Landing):
    """The status is on the fighter: its row, its rounds, its source."""
    put_status(l.f, l.status, l.rounds, l.source)


def crippling_chain(l: Landing):
    """Crippling Wounds (f312): an open wound from a foe with it slows for as long as it stays open."""
    from engine import combat as C
    f, source = l.f, l.source
    if l.status == "bleeding" and source is not None and source.side != f.side and "crippling_wounds" in C.mechanics(source, l.combat) \
            and f.alive and land(l.combat, f, "slowed", l.rounds, source):
        f.counters["crippled"] = 1
        C.tell(l.combat, f"the wound drags at {C.who(f)}, and {C.vb(f, 'you slow', 'it slows')} (Crippling Wounds)")


def winding_cancel(l: Landing):
    """A stun or a fall interrupts a blow being wound up."""
    from engine import combat as C
    f = l.f
    if l.status in ("stunned", "prone") and f.winding:
        f.winding = {}
        C.leave_open(l.combat, f)
        l.combat.log.append(f"{f.name}'s wound-up blow is interrupted")
        C.tell(l.combat, f"the blow {C.who(f)} was winding up never falls - {C.who(f)} {C.vb(f, 'are', 'is')} left open")


STAGES: dict[str, Callable[[Landing], object]] = {
    "unyielding": unyielding, "earthshaker": earthshaker, "stoneform": stoneform, "iron_will": iron_will, "element_ward": element_ward,
    "attune_extend": attune_extend, "sanctified": sanctified, "boss_resisted": boss_resisted, "perk_transform": perk_transform,
    "bloodless": bloodless, "affliction_law": affliction_law, "record": record, "crippling_chain": crippling_chain,
    "winding_cancel": winding_cancel}


def land(combat, f, status: str, rounds, source=None) -> bool:
    """A status lands unless a stage turns it aside: the stages stages.yaml status_eligibility names, in order, each returning False
    to refuse. True when it took hold. This is engine/combat.py add_status."""
    l = Landing(combat, f, status, rounds, source)
    for name in ELIGIBLE:
        if STAGES[name](l) is False:
            return False
    return True


def eligible(combat, f, status: str, rounds, source=None) -> tuple[str, int] | None:
    """The stages before the affliction law alone (what turns a status aside, what it becomes), for a status copied rather than dealt
    (Contagion carries a dead fighter's stacks to a neighbour: no new dose, no record here). The status and rounds that would land,
    or None when the fighter is spared."""
    l = Landing(combat, f, status, rounds, source)
    for name in ELIGIBLE[:ELIGIBLE.index("affliction_law")]:
        if STAGES[name](l) is False:
            return None
    return l.status, l.rounds
