"""Element expressions and spell forms (data/rules/spellcraft.yaml, f227).

An elemental ability expresses its element: a damage expression rides on every hit it lands (whoever makes it - a spell, a melee
ability, a channeled strike), a control expression is the whole of a no-damage spell. A mana damage spell also has a form: one
target, an area, your own area, a curse that lands over time, or a charged blow released next turn. Area spells strike one area -
never the whole field."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine import combat as C
from engine import ability_traits as AT

ROOT = Path(__file__).resolve().parent.parent
S = yaml.safe_load((ROOT / "data" / "rules" / "spellcraft.yaml").read_text(encoding="utf-8"))
EXPR: dict = S["expressions"]
FORMS: dict = S["forms"]
GROUND = set(S.get("ground", []))
_RNG = random.Random()


# ---- what the cards say ---------------------------------------------------------------------------------------------------------

def _nums(spec: dict, tier) -> dict:
    t = AT.tier_of(tier)
    return {k: v[t] for k, v in spec.items() if isinstance(v, dict) and t in v}


def num(e: dict, tier, key: str, default=0):
    """A number from an expression's spec: per tier when it is a table, flat otherwise."""
    v = e.get(key, default)
    return v[AT.tier_of(tier)] if isinstance(v, dict) else v


def expression_text(eid: str, tier) -> str:
    e = EXPR.get(eid)
    if not e:
        return ""
    flat = {k: v for k, v in e.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    return e["text"].format(**{"cap": "", **flat, **_nums(e, tier)})


def form_text(fid: str) -> str:
    f = FORMS.get(fid)
    if not f:
        return ""
    return f["text"].format(share_pct=round(f.get("share", 1) * 100), total_pct=round(f.get("total", 1) * 100),
                            turns=f.get("turns", 0), mult_pct=round(f.get("mult", 1) * 100))


def of_element(element: str, kind: str) -> list[str]:
    """The expressions an element has, of one kind (damage or control)."""
    return [k for k, e in EXPR.items() if e["element"] == element and e["kind"] == kind]


def is_control(eid: str) -> bool:
    return EXPR.get(eid, {}).get("kind") == "control"


# ---- who an attack strikes ------------------------------------------------------------------------------------------------------

def form_of(move) -> str:
    """The form a damage move strikes in: its own, or a blast for the old area reach. (f397) A ranked spell strikes as its form's
    delivery (data/rules/spells.yaml): a lance as a bolt does, harder."""
    if getattr(move, "rank", 0):
        from engine import spells
        return spells.delivery(move)
    f = getattr(move, "spell_form", "") or ""
    if f:
        return f
    return "blast" if move.reach == "area" else "bolt"


def in_area(combat, att, zone_id: str, enemies: list) -> list:
    if combat.battlefield is None or not zone_id:
        return list(enemies)
    return [e for e in enemies if e.zone_id == zone_id]


def targets(combat, att, move, target, enemies: list) -> tuple[list, float]:
    """(who is struck, the share each takes) for a damage move."""
    form = form_of(move)
    ranked = bool(getattr(move, "rank", 0))
    if ranked and form in ("burst", "blast"):            # (f397) a ranked area spell's power is per foe; on a lone foe it spreads thin
        from engine import spells
        aim = target if target is not None and target.alive else (enemies[0] if enemies else None)
        hit = in_area(combat, att, att.zone_id if form == "burst" else (aim.zone_id if aim else ""), enemies) if (aim or form == "burst") else []
        return hit, (1.0 if len(hit) >= 2 else spells.lone(move))
    if form == "burst":
        return in_area(combat, att, att.zone_id, enemies), FORMS["burst"]["share"]
    if form == "blast":
        aim = target if target is not None and target.alive else (enemies[0] if enemies else None)
        if aim is None:
            return [], 1.0
        share = FORMS["blast"]["share"] if move.spell_form == "blast" else S.get("area_share", 0.7)
        return in_area(combat, att, aim.zone_id, enemies), share
    return ([target] if target else enemies[:1]), 1.0


def is_area(move) -> bool:
    return form_of(move) in ("blast", "burst")


# ---- the casting context: hits carry the expression of what is being used -----------------------------------------------------

_CAST: dict[int, dict] = {}


def exprs_of(move) -> list[str]:
    """Everything an ability's element does, in order (one today; a world-taught spell may carry several)."""
    return [e for e in (getattr(move, "expressions", None) or []) if e in EXPR]


def begin(att, move) -> None:
    hits = [e for e in exprs_of(move) if not is_control(e)]
    if hits:
        _CAST[id(att)] = {"exprs": hits, "tier": move.tier, "name": move.name, "once": set()}


def end(att) -> None:
    _CAST.pop(id(att), None)


def casting(att) -> list[str]:
    """The damage expressions riding on what this fighter is striking with right now."""
    return list((_CAST.get(id(att)) or {}).get("exprs", []))


def scorching(att) -> bool:
    """Scorch (f266): this blow burns straight through ward."""
    return "scorch" in casting(att)


def hit_mult(combat, att, dfn, mult: float, rec) -> float:
    """What an expression does to the size of the blow itself, before it lands (f266): Shatter, Blister, Smite."""
    ctx = _CAST.get(id(att))
    if not ctx:
        return mult
    for eid in ctx["exprs"]:
        e = EXPR[eid]
        n = _nums(e, ctx["tier"])
        if eid == "shatter" and "slowed" in dfn.statuses:
            mult = C.hit_step(rec, mult, "Shatter", 1 + n["pct"] / 100)
        elif eid == "blister" and dfn.corroded:
            mult = C.hit_step(rec, mult, "Blister", 1 + dfn.corroded / 100)
        elif eid == "smite" and getattr(dfn, "category", "") in ("undead", "fiend"):
            mult = C.hit_step(rec, mult, "Smite", 1 + n["pct"] / 100)
        elif eid == "fan_the_flames" and "burning" in dfn.statuses:
            mult = C.hit_step(rec, mult, "Fan the Flames", 1 + num(e, ctx["tier"], "pct") / 100)
        elif eid == "lethal_dose" and poison_stacks(dfn) >= int(e.get("stacks", 3)):
            mult = C.hit_step(rec, mult, "Lethal Dose", 1 + num(e, ctx["tier"], "pct") / 100)
        elif eid == "crushing_roots" and ("grappled" in dfn.statuses or "prone" in dfn.statuses):
            mult = C.hit_step(rec, mult, "Crushing Roots", 1 + num(e, ctx["tier"], "pct") / 100)
        elif eid == "judgement" and dfn.counters.get("hurt_ally", -9) >= combat.round - 1:
            mult = C.hit_step(rec, mult, "Judgement", 1 + num(e, ctx["tier"], "pct") / 100)
        elif eid == "storm_charge" and att.move_round == combat.round:
            mult = C.hit_step(rec, mult, "Storm Charge", 1 + num(e, ctx["tier"], "pct") / 100)
        elif eid == "sunlit_growth" and "in_daylight" in (combat.conditions or []) and "underground" not in (combat.conditions or []):
            mult = C.hit_step(rec, mult, "Sunlit Growth", 1 + num(e, ctx["tier"], "pct") / 100)
        elif eid == "blood_price":
            mult = C.hit_step(rec, mult, "Blood Price", 1 + num(e, ctx["tier"], "more") / 100)
        elif eid == "shatter_ward" and dfn.shield > 0:
            C.tell(combat, f"the cold cracks {C.whose(dfn)} barrier apart before the blow lands (Shatter Ward)")
            dfn.shield = 0.0
    return mult


def poison_stacks(f) -> int:
    return len(getattr(f, "poison", None) or []) + len(getattr(f, "poison_fixed", None) or [])


def _has(att, eid: str) -> bool:
    return eid in casting(att)


def etching(att) -> bool:
    """Etch (f268): the hit ignores half the target's armor and ward."""
    return _has(att, "etch")


def burning_through(att) -> bool:
    """Burn Through (f268): a defending target still takes full damage."""
    return _has(att, "burn_through")


def seeping(att) -> bool:
    """Seep (f268): the hit goes under the target's barrier."""
    return _has(att, "seep")


DEAD_OK = {"drain", "arc", "conduction", "spreading_flames", "barkskin_graft", "splash",         # these still do their work on a kill
           "jumping_spark", "death_feeds", "phoenix_spark", "soul_leech", "lifebloom", "shield_of_faith", "blood_price",
           "charged_step", "recharge", "shadowcloak", "stoke", "rallying_light", "cleanse", "pyre", "corrode_the_hold"}


def on_hit(combat, att, dfn, taken: float, rng) -> None:
    """A blow from an expressing ability has landed (apply_damage): each thing its element does, does its work."""
    ctx = _CAST.get(id(att))
    if not ctx:
        return
    for eid in ctx["exprs"]:
        if dfn.alive or eid in DEAD_OK:
            _express(combat, att, dfn, taken, rng, ctx, eid)


def _express(combat, att, dfn, taken: float, rng, ctx: dict, eid: str) -> None:
    tier, e = ctx["tier"], EXPR[eid]
    n = _nums(e, tier)
    if eid in ("ignite", "spreading_flames") and dfn.alive:
        C.add_status(combat, dfn, "burning", 2, att)
    if eid == "spreading_flames" and eid not in ctx["once"]:
        ctx["once"].add(eid)
        others = [o for o in in_area(combat, att, dfn.zone_id, combat.enemies() if att.side != "enemy" else _foes(combat, att))
                  if o is not dfn and o.alive]
        for o in others:
            C.add_status(combat, o, "burning", 2, att)
        if others:
            C.tell(combat, f"the fire leaps from {C.who(dfn)} to {_names(others)}")
    elif eid == "chill" and dfn.alive:
        C.add_status(combat, dfn, "slowed", int(n["rounds"]), att)
    elif eid in ("arc", "conduction") and eid not in ctx["once"] and taken > 0:
        ctx["once"].add(eid)
        pool = [o for o in in_area(combat, att, dfn.zone_id, _foes(combat, att)) if o is not dfn and o.alive]
        if eid == "arc":
            pool = sorted(pool, key=lambda o: o.hp)[:1]
        else:
            ties = set(dfn.engaged_with)
            pool = [o for o in pool if ties and set(o.engaged_with) & ties]
        for o in pool:
            share = n["pct"] / 100 * (e.get("metal", 1) if eid == "conduction" and _metal(o) else 1)
            if C.attuned(att, "lightning"):
                share *= C.ATTUNE["lightning"]                # an archon of storm arcs harder (f246)
            dealt = C.take_damage(combat, o, taken * share, att, rng, "magical")
            combat.log.append(f"{e['label']} from {att.name}'s {ctx['name']} hits {o.name}: {dealt} damage")
            C.tell(combat, f"the lightning {'jumps' if eid == 'arc' else 'runs'} on into {C.who(o)} for {dealt} ({e['label']})")
    elif eid == "envenom" and dfn.alive:
        C.add_status(combat, dfn, "poisoned", 3, att)
    elif eid == "corrode" and dfn.alive and not C.warded(dfn, "acid"):
        cut = min(e.get("cap", 75), dfn.corroded + n["pct"] * (C.ATTUNE["acid"] if C.attuned(att, "acid") else 1))
        if cut > dfn.corroded:
            dfn.corroded = cut
            C.tell(combat, f"the acid eats into {C.whose(dfn)} armor ({e['label']}: {cut:g}% gone)")
    elif eid == "wither" and dfn.alive:
        C.add_status(combat, dfn, "withered", int(n["rounds"]), att)
    elif eid == "drain" and att.alive and taken > 0:
        from engine import combat_perks
        healed, _ = combat_perks.mend(combat, att, att, taken * n["pct"] / 100 * (C.ATTUNE["drain"] if C.attuned(att, "necrotic") else 1))
        if healed:
            C.tell(combat, f"{ctx['name']} draws {healed} health back into {C.who(att)} ({e['label']})")
    elif eid == "illuminate" and dfn.alive:
        if C.add_status(combat, dfn, "illuminated", int(n["rounds"]), att):
            from engine import battlefield as bf
            bf.lose(dfn, "concealed")
            bf.lose(dfn, "covered")
    elif eid == "dazzle" and dfn.alive:
        C.add_status(combat, dfn, "blinded", 2, att)             # 2: so it is still blind when its own turn comes (f268)
    elif eid == "rot" and dfn.alive and taken > 0:             # (f266) maximum health lost for the fight
        cut = taken * n["pct"] / 100
        dfn.max_hp = max(1, round(dfn.max_hp - cut))
        dfn.hp = min(dfn.hp, dfn.max_hp)
        C.tell(combat, f"the flesh around the wound rots away - {C.whose(dfn)} body will not grow it back ({e['label']}: -{round(cut)} max health)")
    elif eid == "reap" and dfn.alive and att.side != "enemy" and not dfn.boss and dfn.rank != "boss":
        dfn.counters["reaped_by"], dfn.counters["reap_until"] = att.id, combat.round + int(n["rounds"])
    elif eid == "overload" and dfn.alive:
        mark = dfn.counters.get("overload")
        if mark and mark[0] == att.id and combat.round - mark[1] <= 1:
            dfn.counters.pop("overload")
            if C.add_status(combat, dfn, "stunned", 1, att):
                C.tell(combat, f"the charge in {C.who(dfn)} overloads and locks {C.vb(dfn, 'you', 'it')} rigid ({e['label']})")
        else:
            dfn.counters["overload"] = [att.id, combat.round]
    elif eid == "paralytic" and dfn.alive and len(getattr(dfn, "poison", []) or []) >= int(e.get("stacks", 3)):
        C.add_status(combat, dfn, "slowed", int(n["rounds"]), att)
    elif eid == "sickening" and dfn.alive:
        C.add_status(combat, dfn, "weakened", int(n["rounds"]), att)
    elif eid == "splash" and eid not in ctx["once"] and taken > 0:
        ctx["once"].add(eid)
        for o in [o for o in in_area(combat, att, dfn.zone_id, _foes(combat, att)) if o is not dfn and o.alive]:
            dealt = C.take_damage(combat, o, taken * n["pct"] / 100, att, rng, "magical")
            C.tell(combat, f"acid splashes over {C.who(o)} for {dealt} ({e['label']})")
    elif eid == "barkskin_graft" and att.alive and taken > 0:
        cap = att.max_hp * float(e.get("cap", 0.5))
        add = min(taken * n["pct"] / 100 * (C.ATTUNE["nature"] if C.attuned(att, "nature") else 1), max(0.0, cap - att.shield))
        if add > 0:
            att.shield += add
            C.tell(combat, f"bark creeps over {C.who(att)}, a barrier of {round(add)} ({e['label']})")
    elif eid == "vine_lash" and dfn.alive:
        from engine import battlefield as bf, martial
        if martial._size(dfn) > martial._size(att):
            C.tell(combat, f"the vines strain, but {C.who(dfn)} is too big to drag ({e['label']})")
        elif not bf.engaged_pair(att, dfn) and not __import__("engine.combat_perks", fromlist=["unmovable"]).unmovable(combat, dfn):
            if dfn.zone_id != att.zone_id:
                bf.enter_zone(combat, dfn, att.zone_id)
            elif dfn.row == "back":
                bf.to_row(combat, dfn, "loose")
            bf.engage(combat, att, dfn)
            C.tell(combat, f"vines whip round {C.who(dfn)} and haul {C.vb(dfn, 'you', 'it')} into the fight ({e['label']})")
    elif eid == "thornburst" and dfn.alive:
        C.add_status(combat, dfn, "bleeding", 3, att)
    else:
        _express_more(combat, att, dfn, taken, rng, ctx, eid)


def _express_more(combat, att, dfn, taken: float, rng, ctx: dict, eid: str) -> None:
    """The f268 batch: eighty more things an element can do on a hit."""
    from engine import battlefield as bf, afflictions, combat_perks
    tier, e, name = ctx["tier"], EXPR[eid], ctx["name"]
    N = lambda key, default=0: num(e, tier, key, default)
    crit = att.counters.get("last_outcome") == "crit"
    killed = not dfn.alive
    mine = [o for o in combat.fighters if o.alive and not o.fled and o is not att and not bf.hostile(att, o)]
    near_mine = [o for o in mine if o.zone_id == att.zone_id]
    foes_here = [o for o in in_area(combat, att, dfn.zone_id, _foes(combat, att)) if o.alive]
    # ---- fire
    if eid == "flashfire" and dfn.alive and "burning" in dfn.statuses:
        left = dfn.statuses.pop("burning") * afflictions.tick(dfn, "burning")
        afflictions.ended(dfn, "burning")
        dealt = C.take_damage(combat, dfn, left, att, rng, "magical")
        C.tell(combat, f"the fire on {C.who(dfn)} goes up all at once for {dealt} ({e['label']})")
    elif eid == "pyre":
        if dfn.alive:
            dfn.counters["pyre_by"] = att.id
        else:
            _pyre(combat, dfn, att)
    elif eid == "blowback" and dfn.alive and "grappled" not in dfn.statuses and not combat_perks.unmovable(combat, dfn):
        bf.slip_away(combat, dfn)
        C.tell(combat, f"the blast throws {C.who(dfn)} clear of the fight ({e['label']})")
    elif eid == "smolder" and dfn.alive:
        if C.add_status(combat, dfn, "burning", int(N("rounds", 4)), att):
            dfn.statuses["burning"] = max(dfn.statuses.get("burning", 0), int(N("rounds", 4)))
            dfn.ignite *= 0.5
    elif eid == "flare_up" and dfn.alive:
        if C.add_status(combat, dfn, "burning", 2, att) and crit:
            dfn.ignite *= 2
            C.tell(combat, f"the blow lands true and the fire flares twice as high ({e['label']})")
    elif eid == "stoke":
        att.counters["stoke"] = att.counters.get("stoke", 0) + 1
    elif eid == "last_ember" and dfn.alive and "burning" in dfn.statuses:
        dfn.statuses["burning"] += 1
        C.tell(combat, f"the embers on {C.who(dfn)} catch again ({e['label']})")
    elif eid == "phoenix_spark" and killed:
        att.counters["free_fire"] = 1
        C.tell(combat, f"the kill kindles something in {C.who(att)}: the next fire will cost nothing ({e['label']})")
    elif eid == "afterglow" and dfn.alive and "burning" in dfn.statuses:
        if C.add_status(combat, dfn, "illuminated", dfn.statuses["burning"], att):
            bf.lose(dfn, "concealed")
            bf.lose(dfn, "covered")
    # ---- cold
    elif eid == "cold_snap":
        for o in foes_here:
            C.add_status(combat, o, "slowed", 1, att)
    elif eid == "brittle" and dfn.alive:
        C.add_status(combat, dfn, "brittle", int(N("rounds", 2)), att)
    elif eid == "frostbite" and dfn.alive:
        dfn.counters["frostbite"] = [att.id, taken * N("pct", 10) / 100]
    elif eid == "frostweld" and dfn.alive:
        C.add_status(combat, dfn, "frostwelded", int(N("rounds", 2)), att)
    elif eid == "avalanche" and dfn.alive and not combat_perks.unmovable(combat, dfn) and combat.battlefield is not None:
        away = [z for z in combat.battlefield.adjacent(dfn.zone_id)
                if combat.battlefield.steps(z, att.zone_id) >= combat.battlefield.steps(dfn.zone_id, att.zone_id)]
        if away:
            bf.enter_zone(combat, dfn, away[0])
            C.tell(combat, f"{C.who(dfn)} {C.vb(dfn, 'are', 'is')} swept away to {combat.battlefield.zones[away[0]].name} ({e['label']})")
    elif eid == "hypothermia" and dfn.alive and "slowed" in dfn.statuses:
        dfn.statuses["slowed"] += 1
    elif eid == "superconductor" and dfn.alive:
        C.add_status(combat, dfn, "superconductive", int(N("rounds", 2)), att)
    elif eid == "numb_hands" and dfn.alive:
        C.add_status(combat, dfn, "numb_hands", int(N("rounds", 2)), att)
    elif eid == "snowdrift":
        _snowdrift(combat, att, dfn.zone_id, int(N("rounds", 2)), name)
    # ---- lightning
    elif eid == "galvanize" and dfn.alive and _metal(dfn):
        C.add_status(combat, dfn, "stunned", 1, att)
    elif eid == "spasm" and dfn.alive:
        if dfn.winding or dfn.charging:
            dfn.winding, dfn.charging = {}, {}
            C.tell(combat, f"{C.whose(dfn)} limbs jerk and whatever {C.vb(dfn, 'you were', 'it was')} readying is lost ({e['label']})")
        C.leave_open(combat, dfn)
    elif eid == "charged_step":
        att.counters["quick_until"] = combat.round + 1
        if att.pace != "fast":
            att.counters["pace_was"] = ["slow", "normal", "fast"].index(att.pace)
            att.pace = "fast"
    elif eid == "jumping_spark" and killed and foes_here:
        o = bf.closest(combat, att, foes_here) or foes_here[0]
        dealt = C.take_damage(combat, o, taken, att, rng, "magical")
        C.tell(combat, f"the bolt leaps from the fallen into {C.who(o)} for {dealt} ({e['label']})")
    elif eid == "recharge":
        for k in list(att.cooldowns):
            att.cooldowns[k] -= 1
            if att.cooldowns[k] <= 0:
                att.cooldowns.pop(k)
    elif eid == "conductor" and dfn.alive:
        C.add_status(combat, dfn, "conductive", int(N("rounds", 3)), att)
    elif eid == "jittered" and dfn.alive:
        C.add_status(combat, dfn, "jittered", int(N("rounds", 2)), att)
    elif eid == "ball_lightning" and combat.battlefield is not None and dfn.zone_id in combat.battlefield.zones:
        combat.zone_effects.setdefault(dfn.zone_id, {})["ball_lightning"] = {
            "until": combat.round + 1, "round": combat.round + 1, "by": att.id, "amount": taken * N("pct", 30) / 100, "name": name}
        C.tell(combat, f"a ball of lightning hangs over {combat.battlefield.zones[dfn.zone_id].name} ({e['label']})")
    # ---- poison
    elif eid == "virulent" and dfn.alive:
        C.add_status(combat, dfn, "poisoned", 3, att)
        C.add_status(combat, dfn, "poisoned", 3, att)
    elif eid == "festering" and dfn.alive and "poisoned" in dfn.statuses:
        dfn.statuses["poisoned"] += int(N("rounds", 2))
    elif eid == "nerve_toxin" and dfn.alive:
        C.add_status(combat, dfn, "shaky", int(N("rounds", 2)), att)
    elif eid == "contagion" and dfn.alive:
        dfn.counters["contagion"] = 1
    elif eid == "venom_spray":
        for o in foes_here:
            C.add_status(combat, o, "poisoned", 3, att)
    elif eid == "wasting" and dfn.alive:
        C.add_status(combat, dfn, "wasting", int(N("rounds", 3)), att)
    elif eid == "persistent_toxin" and dfn.alive:
        if C.add_status(combat, dfn, "poisoned", 3, att):
            dfn.poison_fixed = list(dfn.poison_fixed) + [dfn.poison.pop()]      # the stack just added: it will not fade
    elif eid == "anticoagulant" and dfn.alive and "bleeding" in dfn.statuses:
        dfn.bleed *= 2
        C.tell(combat, f"the blood runs thin and {C.whose(dfn)} wound gapes ({e['label']})")
    elif eid == "refined_venom" and dfn.alive:
        dfn.counters["refined_venom"] = 1
        C.add_status(combat, dfn, "poisoned", 3, att)
    # ---- acid
    elif eid == "lingering_acid" and dfn.alive and taken > 0:
        dfn.curses = list(dfn.curses) + [{"by": att.id, "per": taken * N("pct", 30) / 100 / 2, "left": 2, "name": name,
                                          "element": "acid", "exprs": [], "tier": tier}]
    elif eid == "strip" and dfn.alive:
        C.add_status(combat, dfn, "exposed", int(N("rounds", 2)), att)
    elif eid == "corrode_the_hold":
        if "grappled" in att.statuses or "frostwelded" in att.statuses:
            att.statuses.pop("grappled", None)
            att.statuses.pop("frostwelded", None)
            C.tell(combat, f"the acid eats through whatever held {C.who(att)}, and {C.vb(att, 'you are', 'it is')} free ({e['label']})")
    elif eid == "caustic_drip" and dfn.alive:
        dfn.counters["caustic_drip"] = [att.id, taken * N("pct", 10) / 100, combat.round + int(N("rounds", 2))]
    elif eid == "creeping_corrosion" and dfn.alive:
        dfn.counters["creeping"] = [int(N("rounds", 3)), N("pct", 5)]
    elif eid == "tarnish" and dfn.alive:
        dfn.counters["tarnished"] = int(N("hits", 2))
    elif eid == "caustic_venom" and dfn.alive:
        dfn.counters["caustic_venom"] = N("pct", 2)
    # ---- necrotic
    elif eid == "dread" and dfn.alive:
        C.add_status(combat, dfn, "frightened", int(N("rounds", 2)), att)
    elif eid == "marked_for_death" and dfn.alive:
        C.add_status(combat, dfn, "marked", int(N("rounds", 3)), att)
    elif eid == "soul_leech" and taken > 0:
        pets = [o for o in mine if o.side == "ally" and (o.summon_form or o.id.startswith("thrall"))]
        if pets:
            pet = min(pets, key=lambda o: o.hp / max(1, o.max_hp))
            healed, _ = combat_perks.mend(combat, att, pet, taken * N("pct", 30) / 100)
            if healed:
                C.tell(combat, f"stolen life flows into {C.who(pet)}: {healed} ({e['label']})")
    elif eid == "death_feeds" and killed:
        heal = round(att.max_hp * N("pct", 15) / 100)
        C.restore(combat, att, heal, att, rng)
        C.tell(combat, f"the death feeds {C.who(att)}: {heal} health ({e['label']})")
    elif eid == "entropy" and dfn.alive and dfn.buffs:
        for k, b in list(dfn.buffs.items()):
            b["rounds"] = int(b.get("rounds", 1)) - 1
            if b["rounds"] <= 0:
                dfn.buffs.pop(k)
        C.tell(combat, f"the magic on {C.who(dfn)} frays ({e['label']})")
    elif eid == "blood_price" and taken > 0:
        att.hp = max(1.0, att.hp - taken * N("pct", 10) / 100)
    elif eid == "dominate" and dfn.alive and dfn.side == "enemy" and getattr(dfn, "category", "") == "undead" and not dfn.boss:
        dfn.counters["turned"], dfn.counters["turned_until"] = 1, combat.round + int(N("rounds", 2))
        C.tell(combat, f"{C.who(dfn)} turns on its own side, a stronger will on it ({e['label']})")
    elif eid == "shadowcloak":
        if zone_hidden(combat, att.zone_id) and can_hide(combat, att) and "concealed" not in att.position_tags:
            bf.gain(att, "concealed")
            att.counters["rehid"] = 1
            C.tell(combat, f"{C.who(att)} {C.vb(att, 'fold', 'folds')} back into the shadows ({e['label']})")
    elif eid == "deaths_door" and dfn.alive and not dfn.boss and dfn.rank != "boss" and dfn.hp < dfn.max_hp * N("pct", 15) / 100:
        floor = 1 if ((combat.mentor and dfn.side == "player") or combat.duel) else 0
        dfn.hp = float(floor)
        C.tell(combat, f"death reaches for {C.who(dfn)} and does not let go ({e['label']})")
    elif eid == "life_theft" and dfn.alive:
        dfn.counters["life_theft"] = att.id
    # ---- radiant
    elif eid == "purge" and dfn.alive and dfn.buffs:
        k, b = next(iter(dfn.buffs.items()))
        dfn.buffs.pop(k)
        C.tell(combat, f"light burns {b.get('name') or 'a spell'} off {C.who(dfn)} ({e['label']})")
    elif eid == "cleanse":
        worst = next((s for s in combat_perks.AFFLICTIONS if s in att.statuses and not (s == "burning" and att.counters.get("holy_burn"))), None)
        if worst:
            att.statuses.pop(worst)
            afflictions.ended(att, worst)
            C.tell(combat, f"light washes the {worst.replace('_', ' ')} out of {C.who(att)} ({e['label']})")
    elif eid == "shield_of_faith" and taken > 0:
        for o in near_mine:
            add = min(taken * N("pct", 10) / 100, max(0.0, o.max_hp * 0.5 - o.shield))
            o.shield += add
    elif eid == "censure" and dfn.alive:
        dfn.counters["censured"] = [att.id, combat.round + 1]
    elif eid == "guiding_light" and dfn.alive:
        dfn.counters["guided"] = att.id
    elif eid == "daybreak":
        eff = combat.zone_effects.get(dfn.zone_id) or {}
        gone = [k for k in ("smoke", "overgrowth") if eff.pop(k, None)]
        if gone:
            C.tell(combat, f"light burns the {' and '.join(gone)} away ({e['label']})")
    elif eid == "rallying_light" and crit:
        for o in mine:
            o.counters["rallied"] = N("pct", 30)
        if mine:
            C.tell(combat, f"the flash lifts every ally's arm ({e['label']})")
    elif eid == "humbled" and dfn.alive:
        C.add_status(combat, dfn, "humbled", int(N("rounds", 2)), att)
    elif eid == "sunfire" and dfn.alive:
        if C.add_status(combat, dfn, "burning", 2, att):
            dfn.counters["holy_burn"] = 1
            if getattr(dfn, "category", "") in ("undead", "fiend"):
                dfn.ignite *= 1.5
    # ---- nature
    elif eid == "entangle" and dfn.alive:
        C.add_status(combat, dfn, "grappled", 2, att)
    elif eid == "spore_burst" and dfn.alive:
        C.add_status(combat, dfn, "befuddled", 2, att)
    elif eid == "lifebloom" and taken > 0:
        for o in near_mine:
            combat_perks.mend(combat, att, o, taken * N("pct", 15) / 100)
        if near_mine:
            C.tell(combat, f"life drawn from the blow flows into {_names(near_mine)} ({e['label']})")
    elif eid == "quake_strike" and dfn.alive:
        from engine import martial
        if martial._size(dfn) - martial._size(att) <= 1:
            C.add_status(combat, dfn, "prone", 1, att)
    elif eid == "seedburst" and dfn.alive and taken > 0:
        dfn.counters["seed"] = [att.id, combat.round + int(N("rounds", 2)), taken * N("pct", 60) / 100, name]
    elif eid == "pack_scent" and dfn.alive:
        C.add_status(combat, dfn, "scented", int(N("rounds", 2)), att)
    elif eid == "bramble_wrap" and dfn.alive:
        dfn.counters["bramble"] = [att.id, taken * N("pct", 10) / 100, combat.round + int(N("rounds", 2))]
    elif eid == "tangled_arms" and dfn.alive:
        C.add_status(combat, dfn, "tangled", 2, att)           # 2: statuses tick at the target's turn start, so this holds through its next turn


def _pyre(combat, dead, by) -> None:
    """Pyre (f268): the body burns where it fell."""
    from engine import afflictions
    bf = combat.battlefield
    if bf is None or dead.zone_id not in bf.zones or by is None:
        return
    rounds = int(num(EXPR["pyre"], "light", "rounds", 2))
    eff = combat.zone_effects.setdefault(dead.zone_id, {})
    eff["burning_ground"] = {"until": combat.round + rounds, "by": by.id, "power": afflictions.offensive_power(by, "intelligence"),
                             "pct": num(EXPR["burning_ground"], "light", "pct"), "name": "Pyre"}
    C.tell(combat, f"{C.whose(dead)} body goes up in flames where it fell, and the ground burns with it (Pyre)")


def _snowdrift(combat, att, zone, rounds, name) -> None:
    bf = combat.battlefield
    if bf is None or zone not in bf.zones:
        return
    eff = combat.zone_effects.setdefault(zone, {})
    buried = []
    for z in bf.adjacent(zone):
        e = bf.edge(zone, z)
        if e is not None and "difficult" not in e.tags:
            e.tags = list(e.tags) + ["difficult"]
            buried.append([zone, z])
    eff["snowdrift"] = {"until": combat.round + rounds, "by": att.id, "edges": buried, "name": name}
    C.tell(combat, f"snow piles waist-deep over {bf.zones[zone].name} (Snowdrift)")


def on_any_hit(combat, att, dfn, taken: float, rng) -> None:
    """A blow has landed, whoever made it and however: what the marks already on the two of them do (f268)."""
    if taken <= 0:
        return
    if "superconductive" in dfn.statuses and (att.hit_element or att.element) == "lightning" and not att.counters.get("arcing"):
        e = EXPR["superconductor"]
        others = [o for o in in_area(combat, att, dfn.zone_id, _foes(combat, att)) if o is not dfn and o.alive]
        att.counters["arcing"] = 1
        try:
            for o in others:
                dealt = C.take_damage(combat, o, taken * num(e, "light", "pct", 30) / 100, att, rng, "magical")
                C.tell(combat, f"the lightning runs through the ice into {C.who(o)} for {dealt} (Superconductor)")
        finally:
            att.counters.pop("arcing", None)


def on_attack(combat, att) -> None:
    """A fighter makes an attack: acid dripping on it bites (Caustic Drip, f268)."""
    drip = att.counters.get("caustic_drip")
    if drip and att.alive:
        by, amount, until = drip
        if until < combat.round:
            att.counters.pop("caustic_drip", None)
            return
        maker = combat.get(by)
        dealt = C.take_damage(combat, att, amount, maker, combat.rng if hasattr(combat, "rng") else _RNG, "magical")
        C.tell(combat, f"acid runs down {C.whose(att)} arm as {C.vb(att, 'you', 'it')} {C.vb(att, 'swing', 'swings')}: {dealt} (Caustic Drip)")


def on_move(combat, f) -> None:
    """A fighter moves: brambles bite (Bramble Wrap, f268)."""
    wrap = f.counters.get("bramble")
    if wrap and f.alive:
        by, amount, until = wrap
        if until < combat.round:
            f.counters.pop("bramble", None)
            return
        dealt = C.take_damage(combat, f, amount, combat.get(by), _RNG, "magical")
        C.tell(combat, f"the brambles tear at {C.who(f)} as {C.vb(f, 'you', 'it')} {C.vb(f, 'move', 'moves')}: {dealt} (Bramble Wrap)")


def turn_effects(combat, f, rng) -> None:
    """At the start of a fighter's turn: the marks that work on a timer (f268)."""
    rng = rng or _RNG
    fb = f.counters.get("frostbite")
    if fb:
        if "slowed" not in f.statuses or not f.alive:
            f.counters.pop("frostbite", None)
        else:
            dealt = C.take_damage(combat, f, fb[1], combat.get(fb[0]), rng, "magical")
            C.tell(combat, f"the frostbite eats at {C.who(f)}: {dealt} (Frostbite)")
    creep = f.counters.get("creeping")
    if creep and f.alive:
        left, pct = creep
        if left <= 0 or C.warded(f, "acid"):
            f.counters.pop("creeping", None)
        else:
            f.corroded = min(75, f.corroded + pct)
            f.counters["creeping"] = [left - 1, pct]
            C.tell(combat, f"the corrosion creeps further over {C.who(f)} ({f.corroded:g}% gone, Creeping Corrosion)")
    seed = f.counters.get("seed")
    if seed and f.alive and combat.round >= seed[1]:
        f.counters.pop("seed", None)
        dealt = C.take_damage(combat, f, seed[2], combat.get(seed[0]), rng, "magical")
        C.tell(combat, f"the seed in {C.who(f)} bursts: {dealt} ({seed[3]}, Seedburst)")
    if f.counters.get("turned") and f.counters.get("turned_until") is not None and f.counters["turned_until"] < combat.round:
        f.counters.pop("turned", None)
        f.counters.pop("turned_until", None)
        C.tell(combat, f"the will on {C.who(f)} lifts, and it remembers its own side")
    for key in ("caustic_drip", "bramble"):
        mark = f.counters.get(key)
        if mark and mark[2] < combat.round:
            f.counters.pop(key, None)


def on_tick(combat, f, dot: str) -> None:
    """A burn or a poison has just ticked on this fighter: what rides on the tick (Caustic Venom, f268)."""
    pct = f.counters.get("caustic_venom")
    if dot == "poisoned" and pct and f.alive and not C.warded(f, "acid"):
        cut = min(75, f.corroded + pct)
        if cut > f.corroded:
            f.corroded = cut


def tick_mult(f, dot: str) -> float:
    """How much harder a burn or poison hurts this fighter (Wasting, f268)."""
    if dot == "poisoned" and "wasting" in f.statuses:
        return 1 + num(EXPR["wasting"], "light", "pct", 50) / 100
    return 1.0


def on_death(combat, dead, killer) -> None:
    """A fighter has died, by a blow or an affliction: the marks on it that wait for death (f266, f268)."""
    if dead.counters.get("reaped_by"):
        reaped(combat, dead)
    by = dead.counters.pop("pyre_by", None)
    if by:
        _pyre(combat, dead, combat.get(by) or killer)
    if dead.counters.pop("contagion", None) and (dead.poison or dead.poison_fixed):
        from engine import battlefield as bf
        others = [o for o in combat.fighters if o.alive and not o.fled and o is not dead and o.side == dead.side]
        if others:
            nxt = bf.closest(combat, dead, others) or others[0]
            nxt.statuses["poisoned"] = max(nxt.statuses.get("poisoned", 0), dead.statuses.get("poisoned", 3))
            nxt.poison = list(nxt.poison) + list(dead.poison) + list(dead.poison_fixed)
            C.tell(combat, f"the poison does not die with {C.who(dead)}: it spreads to {C.who(nxt)} (Contagion)")


def blocked_attack(f, reach: str) -> str:
    """Why this fighter cannot make an attack of this reach right now (Numb Hands, Tangled Arms: f268); '' if it can."""
    if reach == "ranged" and "numb_hands" in f.statuses:
        return "numb hands: the fingers will not draw or throw"
    if reach in ("melee", "extended") and "tangled" in f.statuses:
        return "arms tangled in vines"
    return ""


def reaped(combat, dead) -> None:
    """A Reaped enemy that dies in time rises to fight for its reaper's side (f266)."""
    by, until = dead.counters.get("reaped_by"), dead.counters.get("reap_until", -1)
    if not by or combat.round > until or dead.boss:
        return
    dead.counters.pop("reaped_by", None)
    C.raise_thrall(combat, dead, reason="Reap")


def carried(combat, att, dfn, exprs: list[str], tier, name: str, taken: float, rng) -> None:
    """An element carried by something other than the ability being used - a weapon wreathed in it - does its work on a hit, by the
    same law as a spell's."""
    exprs = [e for e in exprs if e in EXPR and not is_control(e)]
    if not exprs:
        return
    held = _CAST.get(id(att))
    _CAST[id(att)] = {"exprs": exprs, "tier": tier, "name": name, "once": set()}
    try:
        on_hit(combat, att, dfn, taken, rng)
    finally:
        if held is not None:
            _CAST[id(att)] = held
        else:
            _CAST.pop(id(att), None)


def _foes(combat, att) -> list:
    from engine import battlefield as bf
    return [o for o in combat.fighters if o.alive and not o.fled and bf.hostile(att, o)]


def _hostile(a, b) -> bool:
    from engine import battlefield as bf
    return bf.hostile(a, b)


def _metal(f) -> bool:
    return bool(f.wears_metal) or f.armor_weight in ("medium", "heavy") or f.category == "construct"


def _names(fs: list) -> str:
    return " and ".join(C.who(f) for f in fs) if len(fs) <= 2 else f"{C.who(fs[0])} and {len(fs) - 1} more"


# ---- control expressions --------------------------------------------------------------------------------------------------------

def control(combat, att, move, target, rng) -> None:
    """A control spell with expressions: each changes the place or strips the creature; it deals no damage. Ground expressions
    always land; those on a creature share one contest."""
    exprs = [e for e in exprs_of(move) if is_control(e)]
    enemies = _foes(combat, att)
    t = target if target is not None and target.alive else (enemies[0] if enemies else None)
    zone = t.zone_id if t is not None else att.zone_id
    for eid in [e for e in exprs if e in GROUND]:
        n = _nums(EXPR[eid], move.tier)
        _ground(combat, att, move, eid, zone, t, int(n.get("rounds", 0)), n)
    on_them = [e for e in exprs if e not in GROUND]
    if not on_them:
        return
    if t is None:
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'reach', 'reaches')} for {move.name}, but there is no one to turn it on")
        return
    power = [move.attribute] if move.resource == "mana" and move.attribute else att.weapon_attrs
    grade = C.contest(att, t, power, rng)
    if grade == "none":
        combat.log.append(f"{att.name} uses {move.name} on {t.name}: resisted")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'turn', 'turns')} {move.name} on {C.who(t)}, but {C.vb(t, 'you shake', 'it shakes')} it off")
        return
    for eid in on_them:
        rounds = int(_nums(EXPR[eid], move.tier).get("rounds", 0))
        if grade == "partial" and rounds:
            rounds = max(1, rounds - 1)
        _on_creature(combat, att, move, eid, t, rounds)
    if grade == "partial":
        C.tell(combat, f"{C.who(t)} half {C.vb(t, 'shake', 'shakes')} it off")
    t.counters["controlled"] = t.counters.get("controlled", 0) + 1


def _on_creature(combat, att, move, eid, t, rounds) -> None:
    if eid == "dissolve_barriers":
        lost = []
        if t.shield:
            t.shield = 0
            lost.append("shield")
        for k, b in list(t.buffs.items()):
            if b.get("kind") in ("stance", "bulwark", "manashield", "guard", "thorns", "distract"):
                t.buffs.pop(k)
                lost.append(b.get("name") or b.get("kind"))
        if t.defending:
            t.defending = 0
            lost.append("guard")
        combat.log.append(f"{att.name} uses {move.name} on {t.name}: {', '.join(lost) or 'nothing to strip'}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'loose', 'looses')} {move.name} on {C.who(t)}"
               + (f", and {_list(lost)} {'melt' if len(lost) > 1 else 'melts'} away" if lost else ", but it had raised no protection to strip"))
    elif eid == "petrify":
        if t.boss or t.rank == "boss":
            C.tell(combat, f"stone creeps over {C.who(t)} and cracks away - it will not be held ({move.name})")
        elif C.add_status(combat, t, "petrified", rounds, att):
            combat.log.append(f"{att.name} petrifies {t.name} for {rounds}")
            C.tell(combat, f"stone creeps over {C.who(t)} until {C.vb(t, 'you stand', 'it stands')} frozen - nothing can touch "
                   + ("you" if t.side == "player" else "it") + f", and {C.vb(t, 'you', 'it')} can do nothing ({move.name})")
    elif eid == "unravel_recovery":
        C.add_status(combat, t, "unraveled", rounds, att)          # (f263) its healing turns on it until this wears off
        combat.log.append(f"{att.name} uses {move.name} on {t.name}: unraveled for {rounds}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'loose', 'looses')} {move.name} on {C.who(t)}: for a while, every mending will tear at "
               + ("you" if t.side == "player" else "it") + " instead")


def _list(xs: list) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _ground(combat, att, move, eid, zone, t, rounds, n) -> None:
    bf = combat.battlefield
    if bf is None or zone not in bf.zones:
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'loose', 'looses')} {move.name}, but there is no ground here for it to take")
        return
    name = bf.zones[zone].name
    eff = combat.zone_effects.setdefault(zone, {})
    until = combat.round + rounds
    if eid in ("thunderclap", "flare", "earthquake"):         # (f266) instant: everyone hostile there, now
        from engine import martial, battlefield as bfm
        hit = [f for f in combat.fighters if f.alive and not f.fled and f.zone_id == zone and _hostile(att, f)]
        for f in hit:
            if eid == "thunderclap":
                f.winding, f.charging = {}, {}
                C.leave_open(combat, f)
            elif eid == "flare":
                C.add_status(combat, f, "blinded", 2, att)
            elif martial._size(f) - martial._size(att) <= 1:
                C.add_status(combat, f, "prone", 1, att)
        combat.log.append(f"{att.name} uses {move.name} on {name}: {len(hit)} caught")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'loose', 'looses')} {move.name} - {EXPR[eid]['depict']}, across {name}"
               + (f", catching {_names(hit)}" if hit else ", but no enemy is there"))
        return
    if eid == "earthen_barricade":
        zone = att.zone_id                                  # the walls go up around where you stand
        name = bf.zones[zone].name
        eff = combat.zone_effects.setdefault(zone, {})
        walled = []
        for z in bf.adjacent(zone):
            e = bf.edge(zone, z)
            if e is not None and "climb" not in e.tags:
                e.tags = list(e.tags) + ["climb"]
                walled.append([zone, z])
        eff["earthen_barricade"] = {"until": until, "by": att.id, "edges": walled, "name": move.name}
        combat.log.append(f"{att.name} raises {move.name} around {name} for {rounds} rounds")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'raise', 'raises')} {move.name} - {EXPR[eid]['depict']}, all around {name}")
        return
    if eid == "freezing_surface":
        eff["frozen_until"], eff["by"] = max(eff.get("frozen_until", -9), until), att.id
    elif eid == "seal_the_way":
        sealed = _seal(combat, att, zone, until)
        if not sealed:
            C.tell(combat, f"{C.who(att)} {C.vb(att, 'raise', 'raises')} {move.name}, but there is no way to close")
            return
    else:
        power = 0.0
        if eid in ("burning_ground", "static_field", "toxic_cloud"):
            from engine import afflictions
            power = afflictions.offensive_power(att, move.attribute or "intelligence") if move.resource == "mana" \
                else afflictions.offensive_power(att)
        eff[eid] = {"until": until, "by": att.id, "power": power, "pct": n.get("pct", 0), "name": move.name}
        if eid == "reveal":
            from engine import battlefield as bfm
            for f in combat.fighters:
                if f.alive and f.zone_id == zone and "concealed" in f.position_tags:
                    bfm.lose(f, "concealed")
    combat.log.append(f"{att.name} uses {move.name} on {name} for {rounds} rounds")
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'loose', 'looses')} {move.name} - {EXPR[eid]['depict']}, across {name}")


def _seal(combat, att, zone, until) -> list:
    bf = combat.battlefield
    if zone == att.zone_id:
        ways = [z for z in bf.adjacent(zone)]
    elif bf.connected(att.zone_id, zone):
        ways = [att.zone_id]
    else:
        here = bf.steps(zone, att.zone_id)
        ways = [z for z in bf.adjacent(zone) if bf.steps(z, att.zone_id) < here][:1]
    sealed = []
    for z in ways:
        e = bf.edge(zone, z)
        if e is not None and "blocked" not in e.tags:
            e.tags = list(e.tags) + ["blocked"]
            sealed.append([zone, z])
    if sealed:
        combat.zone_effects.setdefault(zone, {}).setdefault("sealed", []).extend({"until": until, "edge": s} for s in sealed)
    return sealed


def revealed(combat, zone_id: str) -> bool:
    eff = (getattr(combat, "zone_effects", None) or {}).get(zone_id) or {}
    r = eff.get("reveal")
    return bool(r) and r["until"] >= combat.round


def _active(combat, zone_id: str, eid: str) -> bool:
    z = ((getattr(combat, "zone_effects", None) or {}).get(zone_id) or {}).get(eid)
    return bool(z) and z.get("until", -1) >= combat.round


def zone_hidden(combat, zone_id: str) -> bool:
    """Whether this ground hides those in it from outside: concealing ground or Overgrowth, unless light has been flooded over it."""
    bf = combat.battlefield
    return bf is not None and zone_id in bf.zones and (bf.zones[zone_id].has("concealed") or _active(combat, zone_id, "overgrowth")) \
        and not revealed(combat, zone_id)


def zone_covered(combat, zone_id: str) -> bool:
    """Whether this ground counts as cover against ranged attacks right now: its own cover, or an Earthen Barricade (f266)."""
    bf = combat.battlefield
    return bf is not None and zone_id in bf.zones and (bf.zones[zone_id].has("cover") or _active(combat, zone_id, "earthen_barricade"))


def smoked(combat, att, dfn) -> bool:
    """An attack into or out of Smoke (f266): from one area to another, with smoke on either end."""
    return att.zone_id != dfn.zone_id and (_active(combat, att.zone_id, "smoke") or _active(combat, dfn.zone_id, "smoke"))


def can_hide(combat, f) -> bool:
    """Whether this fighter can be concealed at all right now: not lit up, not standing in revealed ground."""
    return "illuminated" not in f.statuses and not revealed(combat, f.zone_id)


def expire(combat) -> None:
    """Ground effects run out: a seal's wall comes down, a fire, a charge, a cloud or a light ends."""
    bf = combat.battlefield
    for zone, eff in list(combat.zone_effects.items()):
        for s in list(eff.get("sealed", [])):
            if s["until"] < combat.round:
                e = bf.edge(*s["edge"]) if bf is not None else None
                if e is not None and "blocked" in e.tags:
                    e.tags = [t for t in e.tags if t != "blocked"]
                eff["sealed"].remove(s)
        if "sealed" in eff and not eff["sealed"]:
            eff.pop("sealed")
        wall = eff.get("earthen_barricade")
        if wall and wall["until"] < combat.round and bf is not None:
            for a, b in wall.get("edges", []):
                e = bf.edge(a, b)
                if e is not None and "climb" in e.tags:
                    e.tags = [t for t in e.tags if t != "climb"]
        drift = eff.get("snowdrift")
        if drift and drift["until"] < combat.round and bf is not None:
            for a, b in drift.get("edges", []):
                e = bf.edge(a, b)
                if e is not None and "difficult" in e.tags:
                    e.tags = [t for t in e.tags if t != "difficult"]
        for k in [k for k, v in eff.items() if isinstance(v, dict) and v.get("until", 99) < combat.round]:
            eff.pop(k)
        if "frozen_until" in eff and eff["frozen_until"] < combat.round:
            eff.pop("frozen_until")
            eff.pop("by", None)
        if not eff:
            combat.zone_effects.pop(zone, None)


def zone_turn(combat, f, rng=None) -> None:
    """A fighter starts their turn on ground a spell has changed: burning, charged or poisoned ground does its work."""
    expire(combat)
    eff = combat.zone_effects.get(f.zone_id) or {}
    rng = rng or _RNG
    for eid in ("burning_ground", "static_field"):
        z = eff.get(eid)
        if z and f.alive:
            _zone_hurt(combat, f, z, eid, rng)
    z = eff.get("toxic_cloud")
    if z and f.alive:
        maker = combat.get(z["by"])
        if maker is None or _hostile(maker, f):
            C.add_status(combat, f, "poisoned", 3, maker)
    z = eff.get("ball_lightning")
    if z and f.alive and z.get("round") == combat.round:
        maker = combat.get(z["by"])
        if maker is None or _hostile(maker, f):
            dealt = C.take_damage(combat, f, z["amount"], maker, rng, "magical")
            C.tell(combat, f"the ball of lightning bursts over {C.who(f)} for {dealt} ({z['name']})")
    z = eff.get("grasping_dead")
    if z and f.alive:
        maker = combat.get(z["by"])
        if (maker is None or _hostile(maker, f)) and C.add_status(combat, f, "grappled", 2, maker):   # 2: worn down at this same turn-start
            C.tell(combat, f"dead hands close on {C.who(f)} and hold {C.vb(f, 'you', 'it')} fast ({z['name']})")
    z = eff.get("caustic_pool")
    if z and f.alive:
        maker = combat.get(z["by"])
        if (maker is None or _hostile(maker, f)) and not C.warded(f, "acid"):
            cut = min(75, f.corroded + z["pct"])
            if cut > f.corroded:
                f.corroded = cut
                C.tell(combat, f"the acid eats at {C.whose(f)} armor where {C.vb(f, 'you stand', 'it stands')} ({z['name']}: {cut:g}% gone)")


def _zone_hurt(combat, f, z, eid, rng) -> None:
    maker = combat.get(z["by"])
    if maker is not None and not _hostile(maker, f):
        return                                              # your own ground spares your side
    amount = z["power"] * z["pct"] / 100
    if amount <= 0:
        return
    element = "fire" if eid == "burning_ground" else "lightning"
    held = maker.hit_element if maker is not None else ""
    if maker is not None:
        maker.hit_element = element
    dealt = C.take_damage(combat, f, amount, maker, rng, "magical")
    if maker is not None:
        maker.hit_element = held
    combat.log.append(f"{z['name']} hurts {f.name}: {dealt} damage")
    C.tell(combat, f"{z['name']} {'burns' if eid == 'burning_ground' else 'shocks'} {C.who(f)} for {dealt}")


def on_cross(combat, f, old: str, new: str) -> None:
    """Someone steps into or out of charged ground (battlefield.enter_zone)."""
    if not getattr(combat, "zone_effects", None) or old == new:
        return
    for zone in (old, new):
        z = (combat.zone_effects.get(zone) or {}).get("static_field")
        if z and z["until"] >= combat.round and f.alive:
            _zone_hurt(combat, f, z, "static_field", _RNG)
            return


# ---- curses and charged spells --------------------------------------------------------------------------------------------------

def lay_curse(combat, att, dfn, move, mult: float, rng) -> None:
    """A curse: its damage is fixed now, and comes over the target's next turns. It cannot miss."""
    F = FORMS["curse"]
    total, turns = F["total"], int(F["turns"])
    if getattr(move, "rank", 0):                         # (f397) a ranked curse: its form's power is the whole of it
        from engine import spells
        total, turns = 1.0, int(spells.FORMS[spells.form_of(move)].get("turns", turns))
    trig = C.active_triggers(att, combat, dfn)
    dmg = C.raw_damage(att, mult * total, trig, rng, steady=True)
    taken, _ = C.mitigate(dfn, dmg, att.damage_type, att.level, combat, att)
    per = taken / turns
    dfn.curses = list(dfn.curses) + [{"by": att.id, "per": per, "left": turns, "name": move.name,
                                      "element": move.element, "exprs": exprs_of(move), "tier": move.tier}]
    combat.log.append(f"{att.name} lays {move.name} on {dfn.name}: {round(per)} a turn for {turns} turns")
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'lay', 'lays')} {move.name} on {C.who(dfn)}, and it settles in to do its work")


def curse_turn(combat, f, rng=None) -> None:
    rng = rng or _RNG
    keep = []
    for c in f.curses:
        if not f.alive:
            break
        maker = combat.get(c["by"])
        held = maker.hit_element if maker is not None else ""
        if maker is not None:
            maker.hit_element = c.get("element", "")
        dealt = C.take_damage(combat, f, c["per"], maker, rng, "magical")
        if maker is not None:
            maker.hit_element = held
            hits = [e for e in c.get("exprs", []) if e in EXPR and not is_control(e)]
            if hits and maker.alive:
                maker.counters["last_hit"] = int(dealt)
                _CAST[id(maker)] = {"exprs": hits, "tier": c["tier"], "name": c["name"], "once": set()}
                on_hit(combat, maker, f, dealt, rng)
                end(maker)
        combat.log.append(f"{c['name']} gnaws at {f.name}: {dealt} damage")
        C.tell(combat, f"{c['name']} gnaws at {C.who(f)} for {dealt}")
        c["left"] -= 1
        if c["left"] > 0:
            keep.append(c)
    f.curses = keep


def cast_turns(move) -> int:
    """How many turns using this takes, the turn it is begun on included: its own count if it has one, two for a charged spell,
    otherwise one."""
    own = int(getattr(move, "cast_turns", 0) or 0)
    if own:
        return max(1, own)
    return 2 if form_of(move) == "charged" or getattr(move, "martial_form", "") == "windup" else 1


def wind_up(combat, att, move, target) -> None:
    turns = cast_turns(move)
    att.charging = {"move": move.model_dump(), "target": target.id if target is not None else "", "round": combat.round,
                    "left": turns - 1}
    combat.log.append(f"{att.name} winds up {move.name}")
    more = "all of next turn" if turns == 2 else f"all of the next {turns - 1} turns"
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'begin', 'begins')} to gather {move.name} - it will take {more} to finish, "
                   f"and a stun or a fall will break it")


def release(combat, f, rng=None) -> bool:
    """At the start of the caster's turn while a spell is being gathered: a stun or a fall breaks it (the turn is lost to that anyway);
    otherwise the turn goes to it - gathering on, or, on its last turn, going off. It cannot be dropped. Returns True when the turn
    went to it."""
    ch = f.charging
    if not ch or not f.alive:
        f.charging = {}
        return False
    move = C.Move(**ch["move"])
    if "stunned" in f.statuses or "prone" in f.statuses:
        f.charging = {}
        combat.log.append(f"{f.name}'s {move.name} is broken")
        C.tell(combat, f"the {move.name} {C.who(f)} was gathering comes apart - {C.vb(f, 'you were', 'it was')} knocked out of it")
        return False
    ch["left"] = int(ch.get("left", 1)) - 1
    if ch["left"] > 0:
        combat.log.append(f"{f.name} keeps gathering {move.name}")
        C.tell(combat, f"{C.who(f)} {C.vb(f, 'keep', 'keeps')} gathering {move.name} - "
                       + ("one more turn" if ch["left"] == 1 else f"{ch['left']} more turns"))
        return True
    f.charging = {}
    foes = _foes(combat, f)
    t = next((e for e in foes if e.id == ch["target"]), None) or (foes[0] if foes else None)
    if t is None:
        C.tell(combat, f"the {move.name} {C.who(f)} gathered finds no one left to strike, and fades")
        return True
    C.tell(combat, f"{C.who(f)} {C.vb(f, 'release', 'releases')} {move.name}")
    f.counters["charged_release"] = 1
    try:
        C._act_ability(combat, f, move, t, rng or _RNG, None, True)
    finally:
        f.counters.pop("charged_release", None)
    return True
