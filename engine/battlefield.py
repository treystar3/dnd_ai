"""The ground a fight is fought on: a handful of coarse zones (a trail, a rise, dense brush) joined by edges, each fighter standing in
exactly one zone, in a row of their side's local formation (front, back, or loose). This is the authoritative answer to "where is
everyone" that the narration, the pane and - from B2 on - reach, movement and protection all read.

Since B2 this is the only spatial law: engagement (explicit and symmetric), containment (a frontliner holds only so many), protection
(a backliner behind a working front cannot simply be walked to), reach and approach. Everything here is either a pure read over the
fight or one of the few named transitions; nothing else in the game writes zone_id, row, engaged_with or position_tags, a rule the
tests enforce by scanning the source. Nothing here rolls dice or calls a model.

THE MOVEMENT LAW (f223). Ordinary movement is baseline positioning, limited on purpose: a full action (move closer, fall back, take
high ground, interpose), or a restricted step that rides along with an action (one step toward the fight - never a climb, rough
ground or a guarding line, and none in heavy armor; a fall-back that is free only behind your own line). Movement abilities
(engine/movement.py) are how a character overcomes those limits: used alongside an action, one a turn, priced by cooldown, setup
or risk; the rare extreme relocation takes the whole turn. They only move - you, your allies, or who is fighting whom."""
from __future__ import annotations

from pydantic import BaseModel

TERRAIN_TAGS = ("open", "concealed", "cover", "elevated", "difficult", "narrow", "hazardous")
EDGE_TAGS = ("open", "doorway", "stairs", "climb", "jump", "difficult", "blocked")
ROWS = ("front", "back", "loose")
POSITION_TAGS = ("elevated", "covered", "concealed", "exposed")   # personal, temporary; a zone's tags are the ground's own


class BattleZone(BaseModel):
    id: str
    name: str
    tags: list[str] = []

    def has(self, tag: str) -> bool:
        return tag in self.tags


class BattleEdge(BaseModel):
    a: str
    b: str
    tags: list[str] = ["open"]


class Battlefield(BaseModel):
    zones: dict[str, BattleZone] = {}
    edges: list[BattleEdge] = []
    start: str = ""                 # the main zone: where the fight begins
    kind: str = ""                  # a big fight's field (f224): wild, camp or lair; "" for an ordinary one
    player_start: str = ""          # where the player and their allies begin (default: start)
    enemy_start: str = ""           # where the enemy begins (default: start)
    back: str = ""                  # where the enemy's leader or boss begins, and anything spotted from afar
    arrivals: str = ""              # where reinforcements come in from

    def adjacent(self, zone_id: str) -> list[str]:
        """The zones a way leads to from here. A blocked way is a wall: it joins nothing."""
        out = []
        for e in self.edges:
            if "blocked" in e.tags:
                continue
            if e.a == zone_id:
                out.append(e.b)
            elif e.b == zone_id:
                out.append(e.a)
        return out

    def connected(self, a: str, b: str) -> bool:
        return b in self.adjacent(a)

    def hard(self, a: str, b: str) -> bool:
        """A way that cannot be taken in stride: a climb, a jump, hard going on the way or in the ground it leads to. Crossing one is
        the work of a whole action, never of a free step."""
        e = self.edge(a, b)
        if e is not None and ({"climb", "jump", "difficult"} & set(e.tags)):
            return True
        dest = self.zones.get(b)
        return dest is not None and dest.has("difficult")

    def edge(self, a: str, b: str) -> BattleEdge | None:
        return next((e for e in self.edges if {e.a, e.b} == {a, b}), None)

    def steps(self, a: str, b: str) -> int:
        """Zone steps from a to b (0 for the same zone, 99 when there is no way)."""
        if a == b:
            return 0
        seen, frontier, n = {a}, [a], 0
        while frontier:
            n += 1
            frontier = [z for cur in frontier for z in self.adjacent(cur) if z not in seen and not (seen.add(z))]
            if b in frontier:
                return n
        return 99

    def describe(self) -> str:
        """The ground in one line per zone, for prompts and the pane."""
        out = []
        for zid, z in self.zones.items():
            mark = " (here)" if zid == self.start else ""
            tags = ", ".join(z.tags) if z.tags else "open"
            out.append(f"{z.name}{mark} - {tags}")
        return "\n".join(out)


def place_fighters(fight) -> None:
    """Everyone begins on the field: ranged fighters at the back of their side, everyone else at the front; whoever was spotted at a
    distance (starts_far) begins loose in a side zone when there is one. The player's own formation preferences refine this later (B3);
    reserves are placed too, so they arrive already standing somewhere real."""
    bf = fight.battlefield
    if bf is None or not bf.zones:
        return
    mine = bf.player_start if bf.player_start in bf.zones else bf.start
    theirs = bf.enemy_start if bf.enemy_start in bf.zones else bf.start
    away = bf.back if bf.back in bf.zones else next((z for z in bf.zones if z != bf.start), bf.start)
    hide = next((z for z, zz in bf.zones.items() if zz.has("concealed") and z not in (bf.start, mine)), "")
    leader = None
    if bf.kind:
        enemies = [f for f in fight.fighters if f.side == "enemy"]
        leader = next((f for f in enemies if getattr(f, "boss", None) or f.rank == "boss"), None) or \
            (enemies[0] if bf.kind == "camp" and len(enemies) > 1 else None)
    perch = vantage(bf, theirs, mine) if bf.kind else ""
    for f in list(fight.fighters):
        if not f.zone_id or f.zone_id not in bf.zones:
            if hide and (f.side == "enemy" and getattr(f, "behaviors", None) and f.behaviors.get("stalk")
                         or f.side == "player" and "night_stalker" in getattr(f, "legendary", {})):
                f.zone_id, f.row = hide, "loose"
                gain(f, "concealed")
            elif getattr(f, "starts_far", False) or f is leader:
                f.zone_id, f.row = away, ("loose" if f is not leader else ("back" if f.reach == "ranged" else "front"))
            elif f.side == "enemy" and f.reach == "ranged" and perch:
                f.zone_id, f.row = perch, "back"
                if bf.zones[perch].has("elevated"):
                    gain(f, "elevated")
            else:
                f.zone_id = theirs if f.side == "enemy" else mine
                f.row = "back" if f.reach == "ranged" else "front"
            if bf.zones[f.zone_id].has("elevated"):
                gain(f, "elevated")                              # whoever begins on high ground holds it


def place_joiner(fight, f) -> None:
    """Someone joining mid-fight (a wave, a summon, a raised thrall, a boss's guard): tied to nobody, placed fresh. From afar they
    come in where reinforcements arrive; otherwise with their side - an ally beside the player, an enemy with its own."""
    f.engaged_with = []
    bf = fight.battlefield
    if bf is None or not bf.zones:
        return
    if f.starts_far:
        f.zone_id = bf.arrivals if bf.arrivals in bf.zones else next((z for z in bf.zones if z != bf.start), bf.start)
        f.row = "loose"
        return
    p = fight.player
    if f.side != "enemy" and p.zone_id in bf.zones:
        f.zone_id = p.zone_id
    else:
        f.zone_id = bf.enemy_start if f.side == "enemy" and bf.enemy_start in bf.zones else bf.start
    f.row = "back" if f.reach == "ranged" else "front"


def vantage(bf, theirs: str, mine: str) -> str:
    """On a big field, the high or covered ground nearest the enemy's side where its archers begin ('' when there is none)."""
    spots = [z for z, zz in bf.zones.items() if (zz.has("elevated") or zz.has("cover")) and z != mine]
    if not spots:
        return ""
    near = [z for z in spots if bf.steps(theirs, z) <= 1] or spots
    return min(near, key=lambda z: (not bf.zones[z].has("elevated"), bf.steps(theirs, z), z))


# ---------- reading the fight ----------
# "Hostile" is by side: the player and their allies are one side, enemies the other. Every read filters to the living who have not fled.

def hostile(a, b) -> bool:
    return (a.side == "enemy") != (b.side == "enemy")


def standing(fight, zone_id: str | None = None) -> list:
    return [f for f in fight.fighters if f.alive and not f.fled and (zone_id is None or f.zone_id == zone_id)]


def engaged_pair(a, b) -> bool:
    return b.id in a.engaged_with and a.alive and b.alive and not a.fled and not b.fled


def engaged(fight, f) -> list:
    """The living opponents tied up with this fighter, closest first by nothing in particular (stable order)."""
    return [o for o in standing(fight) if o.id in f.engaged_with and hostile(f, o)]


def hold_of(f) -> int:
    """How many enemies this fighter can hold at the line now: its own hold, and more while Enlarged (data/rules/ability_traits.yaml)."""
    from engine.ability_traits import BUFFS
    grown = any(b.get("kind") == "enlarge" for b in (getattr(f, "buffs", None) or {}).values())
    return int(f.hold) + (int(BUFFS.get("enlarge", {}).get("hold", 0)) if grown and f.hold > 0 else 0)


def can_hold(f) -> bool:
    """A frontliner holds the line only while on their feet and their wits: stunned or prone, their holds mean nothing - unless their
    grip is sworn deeper than their senses (stubborn_hold)."""
    return f.alive and not f.fled and f.row == "front" and hold_of(f) > 0 and \
        (not ({"stunned", "prone"} & set(f.statuses)) or "stubborn_hold" in getattr(f, "legendary", {}))


def containment(fight, zone_id: str, attacking_side_enemy: bool) -> dict:
    """Who is held at the line, derived fresh (nothing stored): in this zone, the defenders' frontliners each contain up to their hold
    of the hostile melee fighters there - those already engaged with a holder first, the rest in stable order. attacker id -> holder id,
    None for the uncontained, who have an opening toward the backline (and spend their own action taking it)."""
    defenders = [f for f in standing(fight, zone_id) if (f.side == "enemy") != attacking_side_enemy]
    attackers = [f for f in standing(fight, zone_id) if (f.side == "enemy") == attacking_side_enemy and f.reach != "ranged"]
    holders = {f.id: hold_of(f) for f in defenders if can_hold(f)}
    out: dict = {}
    for a in sorted(attackers, key=lambda x: (not any(h in x.engaged_with for h in holders), x.id)):
        pick = next((h for h in a.engaged_with if holders.get(h, 0) > 0), None) or             next((h for h, cap in holders.items() if cap > 0), None)
        if pick:
            holders[pick] -= 1
        out[a.id] = pick
    return out


def contained(fight, att) -> bool:
    return containment(fight, att.zone_id, att.side == "enemy").get(att.id) is not None


def protected(fight, dfn) -> bool:
    """A backliner behind a working front of their own side, in their own zone, cannot simply be walked to."""
    return dfn.row == "back" and any(can_hold(f) and not hostile(f, dfn) for f in standing(fight, dfn.zone_id))


class Access:
    """Whether an attack can be made now, and if not, whether a step would help: ok, or can_approach with why."""
    def __init__(self, ok: bool, can_approach: bool = False, why: str = ""):
        self.ok, self.can_approach, self.why = ok, can_approach, why


def attack_access(fight, att, dfn, reach: str | None = None) -> Access:
    """The one answer to "can this attack be made from here". Melee needs the same zone and either engagement, an unprotected target,
    or an opening through the line (the attacker uncontained); extended reach strikes past the line in its zone; ranged crosses zones
    unless the target's zone is concealed from outside; area and self always resolve (their targeting is the caller's)."""
    reach = reach or att.reach
    bf = fight.battlefield
    if reach in ("area", "self"):
        return Access(True)
    if reach == "ranged":
        from engine import spellcraft
        if bf is not None and att.zone_id != dfn.zone_id and "illuminated" not in dfn.statuses and (
                spellcraft.zone_hidden(fight, dfn.zone_id) or "concealed" in dfn.position_tags):
            return Access(False, can_approach=True, why="out of sight")
        return Access(True)
    if bf is not None and att.zone_id != dfn.zone_id:
        return Access(False, can_approach=bf.steps(att.zone_id, dfn.zone_id) < 99, why="in another part of the field")
    if reach == "extended":
        return Access(True)
    if crowded_out(fight, att, dfn):
        return Access(False, can_approach=False, why="crowded out: there is no room to come at them in the press")
    if engaged_pair(att, dfn) or not protected(fight, dfn):
        return Access(True)
    if not contained(fight, att):
        return Access(False, can_approach=True, why="behind the line, but there is an opening")
    holder = containment(fight, att.zone_id, att.side == "enemy").get(att.id)
    name = next((f.name for f in fight.fighters if f.id == holder), "the line")
    return Access(False, can_approach=False, why=f"held at the line by {name}")


def hit_modifiers(fight, att, dfn) -> list[list]:
    """Position's word on an attack roll, as (label, points) steps: high ground, firing into cover from outside, a screened backline."""
    steps = []
    from engine.combat import RULES
    if "elevated" in att.position_tags and "elevated" not in dfn.position_tags:
        steps.append(["high ground", RULES["elevated_accuracy"]])
    if "exposed" in dfn.position_tags:
        steps.append(["they are exposed", RULES["opening"]["accuracy"] // 2])
    if "illuminated" in dfn.statuses:
        steps.append(["they are lit up", RULES.get("illuminated_accuracy", 10)])
        return steps                                       # lit up: no cover, no screen protects them (engine/spellcraft.py)
    from engine import spellcraft as _sc
    if _sc.smoked(fight, att, dfn):                        # attacks into or out of Smoke (f266)
        steps.append(["through smoke", -int(_sc.EXPR["smoke"].get("accuracy", 30))])
    if att.reach == "ranged":
        bf = fight.battlefield
        from engine import spellcraft as _sc
        if bf is not None and att.zone_id != dfn.zone_id and (_sc.zone_covered(fight, dfn.zone_id)
                                                              or "covered" in dfn.position_tags):
            from engine import combat_perks
            if not combat_perks.sees_through_cover(fight, att, dfn):      # some perks find a way past ordinary cover
                steps.append(["firing into cover", -RULES["hit"].get("cover", 0)])
        if protected(fight, dfn) and not engaged_pair(att, dfn):
            steps.append(["a screened backline", -RULES["hit"].get("screened_backline", 0)])
    return steps


def pace_of(size: str = "Medium", category: str = "", armor_weight: str = "") -> str:
    """slow, normal or fast (data/rules/combat.yaml pace): bulk and kind for creatures, the armor they carry for people."""
    from engine.combat import RULES
    P = RULES.get("pace") or {}
    if armor_weight:
        return (P.get("armor") or {}).get(armor_weight, "normal")
    if size in P.get("slow_sizes", ()) or category in P.get("slow_categories", ()):
        return "slow"
    if category in P.get("fast_categories", ()):
        return "fast"
    return "normal"


def crowded_out(fight, att, dfn) -> bool:
    """In a narrow place there is only so much room: once enough are already on one defender, another cannot come at them too."""
    bf = fight.battlefield
    if bf is None or dfn.zone_id not in bf.zones or not bf.zones[dfn.zone_id].has("narrow"):
        return False
    from engine.combat import RULES
    cap = int(RULES.get("narrow_cap", 2))
    on_them = [o for o in standing(fight, dfn.zone_id) if hostile(o, dfn) and dfn.id in o.engaged_with and o.reach != "ranged"]
    return len(on_them) >= cap and att.id not in dfn.engaged_with


def narrative_snapshot(fight) -> str:
    """The field in a few plain lines, one per zone with someone in it, for the narrator and the pane: who stands where, who is tied up
    with whom. The event list says what happened; this stops anyone being written somewhere they are not."""
    bf = fight.battlefield
    if bf is None or not bf.zones:
        return ""
    out = []
    for zid, z in bf.zones.items():
        here = [f for f in standing(fight, zid)]
        if not here:
            continue
        bits = []
        for f in here:
            tied = [o.name for o in here if o.id in f.engaged_with]
            bits.append(f.name + (f" (fighting {tied[0]})" if tied else (f" ({f.row})" if f.row != "loose" else "")))   # (f419) not '(on X)'
        tags = f" [{', '.join(z.tags)}]" if z.tags else ""
        out.append(f"{z.name}{tags}: " + ", ".join(bits))
    return "\n".join(out)


def steps_between(fight, a, b) -> int:
    """Zone steps between two fighters (0 on a bare field)."""
    bf = fight.battlefield
    if bf is None or not a.zone_id or not b.zone_id:
        return 0
    return bf.steps(a.zone_id, b.zone_id)


def closest(fight, f, among: list) -> "object | None":
    """The nearest of these to f: the engaged first, then by zone steps, then the worst hurt."""
    bf = fight.battlefield
    if not among:
        return None
    return min(among, key=lambda o: (0 if engaged_pair(f, o) else 1,
                                     bf.steps(f.zone_id, o.zone_id) if bf is not None else 0, o.hp))


# ---------- the transitions (the only writers) ----------

def engage(fight, a, b) -> None:
    if a.zone_id != b.zone_id:
        return
    if b.id not in a.engaged_with:
        a.engaged_with.append(b.id)
    if a.id not in b.engaged_with:
        b.engaged_with.append(a.id)


def disengage(fight, a, b) -> None:
    if b.id in a.engaged_with:
        a.engaged_with.remove(b.id)
    if a.id in b.engaged_with:
        b.engaged_with.remove(a.id)


def release(fight, f) -> None:
    """Every engagement this fighter is in ends (they fell, fled, or slipped away)."""
    for o in fight.fighters:
        if f.id in o.engaged_with:
            o.engaged_with.remove(f.id)
    f.engaged_with = []


def gain(f, tag: str) -> None:
    if tag in ("concealed", "covered") and "illuminated" in getattr(f, "statuses", {}):
        return                                             # lit up, they cannot hide or take cover (engine/spellcraft.py)
    if tag in POSITION_TAGS and tag not in f.position_tags:
        f.position_tags.append(tag)


def lose(f, tag: str) -> None:
    if tag in f.position_tags:
        f.position_tags.remove(tag)


def enter_zone(fight, f, zone_id: str) -> None:
    """Crossing into another zone ends every engagement and sheds position; arriving alone, they stand loose."""
    if fight.battlefield is None or zone_id not in fight.battlefield.zones:
        return
    if "frostwelded" in getattr(f, "statuses", {}) and zone_id != f.zone_id:
        return                                          # Frostweld (f268): its feet are frozen to the ground
    release(fight, f)
    old, f.zone_id = f.zone_id, zone_id
    from engine import spellcraft as _scm
    _scm.on_move(fight, f)                               # brambles bite as it moves (f268)
    from engine import spellcraft
    spellcraft.on_cross(fight, f, old, zone_id)            # charged ground bites whoever crosses into or out of it
    f.row = "loose"
    f.position_tags = [t for t in f.position_tags if t not in ("elevated", "covered", "concealed")]
    if fight.battlefield.zones[zone_id].has("elevated"):
        gain(f, "elevated")


def to_row(fight, f, row: str) -> None:
    if row in ROWS:
        f.row = row


BREACH = "slips past the line"


def approach(fight, att, dfn, hard_ok: bool = True) -> str:
    """One step toward a target, whatever that means from here: cross toward their zone, or press through to someone protected
    (engaging them if there is an opening - the BREACH story; the blow always waits for the next round). Returns the story of the
    step, '' if there was nothing to do. With hard_ok False (a free step), a climb or hard going cannot be taken."""
    bf = fight.battlefield
    att.move_round = fight.round
    if bf is not None and att.zone_id != dfn.zone_id:
        path = [z for z in bf.adjacent(att.zone_id) if bf.steps(z, dfn.zone_id) < bf.steps(att.zone_id, dfn.zone_id)
                and (hard_ok or not bf.hard(att.zone_id, z))]
        if not path:
            return ""
        hard_way = bf.hard(att.zone_id, path[0])
        enter_zone(fight, att, path[0])
        return f"{'struggles across to' if hard_way else 'crosses to'} {bf.zones[path[0]].name}"
    if protected(fight, dfn) and not engaged_pair(att, dfn):
        if not hard_ok:
            return ""                                     # a line is never slipped in stride: breaching is the work of an action
        if contained(fight, att):
            holder = containment(fight, att.zone_id, att.side == "enemy").get(att.id)
            name = next((x.name for x in fight.fighters if x.id == holder), "the line")
            return f"presses toward the back, but {name} holds the line"
        if att.row == "front":
            to_row(fight, att, "loose")
        engage(fight, att, dfn)
        return BREACH
    engage(fight, att, dfn)
    return ""


def slip_away(fight, f) -> None:
    """Out of everyone's grasp without leaving the zone (a flyer wheeling up, a skirmisher stepping back): engagements end, and they
    stand loose."""
    if "frostwelded" in getattr(f, "statuses", {}):
        return                                          # Frostweld (f268): no stepping away
    release(fight, f)
    if f.row != "back":
        to_row(fight, f, "loose")
    from engine import spellcraft as _scm
    _scm.on_move(fight, f)


def withdraw(fight, f) -> str:
    """One step away from the enemy: out of engagement and to the back of their own side, or out of a zone with hostiles into a calmer
    adjacent one. B3 prices this (the parting blow, the action); here it is only the legal move itself."""
    bf = fight.battlefield
    f.move_round = fight.round
    if "frostwelded" in getattr(f, "statuses", {}):
        return "cannot move: frozen to the ground"      # Frostweld (f268)
    release(fight, f)
    from engine import spellcraft as _scm
    _scm.on_move(fight, f)
    if bf is not None and any(hostile(f, o) for o in standing(fight, f.zone_id)):
        calmer = [z for z in bf.adjacent(f.zone_id) if not any(hostile(f, o) for o in standing(fight, z))]
        if f.row != "back" and any(not hostile(f, o) and can_hold(o) for o in standing(fight, f.zone_id)):
            to_row(fight, f, "back")
            return "falls back behind the line"
        if calmer:
            enter_zone(fight, f, calmer[0])
            return f"falls back to {bf.zones[calmer[0]].name}"
    to_row(fight, f, "back")
    return "falls back, opening distance"


def validate(fight) -> list[str]:
    """Everything about the battlefield that must be true and is not, one line each. A fight without a battlefield (an old save, a
    bare simulation) has nothing to check. Run by the tests and #check; never repairs anything."""
    out: list[str] = []
    bf = fight.battlefield
    if bf is None:
        return out
    if not bf.zones:
        return ["a battlefield with no zones"]
    if bf.start not in bf.zones:
        out.append(f"the start zone '{bf.start}' is not among the zones")
    for zid, z in bf.zones.items():
        if z.id != zid:
            out.append(f"zone '{zid}' says its id is '{z.id}'")
        for t in z.tags:
            if t not in TERRAIN_TAGS:
                out.append(f"zone '{zid}' has unknown terrain '{t}'")
    for e in bf.edges:
        for end in (e.a, e.b):
            if end not in bf.zones:
                out.append(f"an edge touches '{end}', which is not a zone")
        if e.a == e.b:
            out.append(f"an edge joins '{e.a}' to itself")
        for t in e.tags:
            if t not in EDGE_TAGS:
                out.append(f"the edge {e.a}-{e.b} has unknown way '{t}'")
    if bf.start in bf.zones:
        reachable = {z for z in bf.zones if bf.steps(bf.start, z) < 99}
        for z in set(bf.zones) - reachable:
            out.append(f"zone '{z}' cannot be reached from the start")
    by_id = {f.id: f for f in fight.fighters}
    for f in fight.fighters:
        if not f.alive or f.fled:
            continue
        if f.zone_id not in bf.zones:
            out.append(f"{f.id} stands in '{f.zone_id}', which is not a zone of this battlefield")
        if f.row not in ROWS:
            out.append(f"{f.id} is in row '{f.row}'")
        if getattr(f, "hold", 0) < 0:
            out.append(f"{f.id} has a hold below zero")
        for t in f.position_tags:
            if t not in POSITION_TAGS:
                out.append(f"{f.id} carries unknown position '{t}'")
        for oid in f.engaged_with:
            o = by_id.get(oid)
            if o is None or not o.alive or o.fled:
                out.append(f"{f.id} is engaged with '{oid}', who is not standing")
            elif f.id not in o.engaged_with:
                out.append(f"{f.id} is engaged with {oid}, but not the other way around")
            elif o.zone_id != f.zone_id:
                out.append(f"{f.id} is engaged with {oid} across zones")
    return out
