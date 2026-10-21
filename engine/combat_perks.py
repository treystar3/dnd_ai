"""Creation perks in a fight (f209): the character-defining rules a player is born with, each a few lines at a named hook that
engine/combat.py calls. A perk's id is its mechanic id in data/rules/passive_mechanics.yaml (where: creation); every number it uses
is in data/rules/perks.yaml. The hooks, in the order a blow passes through them:

    pick_target   an enemy choosing whom to strike          before_damage  a blow about to land, moved or capped
    on_outcome    the roll just made, forced up or down       after_damage   it has landed: what it fuels
    damage_mult   the blow's power, charged or not            on_status      an affliction about to take hold
    after_hit     the blow has landed: what follows it        dot_damage     an affliction ticking
    on_kill       something has fallen to it                  cost / can_use what an ability asks
    on_cast / after_cast / unmaking                           the player's own abilities, before and after they resolve

Each perk tells the player it fired, by the name they gave it, so a rule is never silent."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine import combat as C

ROOT = Path(__file__).resolve().parent.parent
P = yaml.safe_load((ROOT / "data" / "rules" / "perks.yaml").read_text(encoding="utf-8"))["combat"]
AFFLICTIONS = tuple(P["afflictions"])
VESSEL_TAKES = tuple(P["vessel_takes"])
TIER_CODE = {"light": 1, "moderate": 2, "heavy": 3}


# ---------- helpers ----------

def has(f: C.Fighter, mid: str, combat: C.Combat | None = None) -> float:
    """The perk's value if this fighter has it, else 0."""
    return C.mechanics(f, combat).get(mid, 0) if f is not None else 0


def tag(f: C.Fighter, mid: str) -> str:
    """The perk by the name the player gave it, for the narration."""
    return f"({f.mech_names.get(mid) or mid.replace('_', ' ').title()})"


def summon_of(combat: C.Combat) -> C.Fighter | None:
    """'Your summon': the player's Bound summon standing in this fight, else the newest one made in it (engine/summons.py)."""
    from engine import summons
    return summons.yours(combat)


def companion_of(combat: C.Combat) -> C.Fighter | None:
    """A companion - a tamed, living creature - standing in this fight, if any."""
    return next((a for a in combat.allies() if C.is_companion(a) and a.alive), None)


def player_of(combat: C.Combat) -> C.Fighter | None:
    try:
        return combat.player
    except StopIteration:
        return None


def _tick(f: C.Fighter, dot: str) -> int:
    from engine import afflictions
    return afflictions.tick(f, dot)


def _cast_key(move: C.Move) -> str:
    """What a spell is 'of', for the weave: its element when it has one, else its discipline."""
    return move.element or move.attribute or move.effect


# ---------- whom an enemy strikes ----------

def pick_target(combat: C.Combat, e: C.Fighter, targets: list[C.Fighter], rng: random.Random) -> C.Fighter | None:
    """A perk that decides an enemy's target outright; None leaves the choice to the enemy."""
    p = player_of(combat)
    if p is None or not p.alive:
        return None
    if e.counters.get("provoked") == combat.round and has(p, "provoke", combat):
        return p
    cen = e.counters.get("censured")
    if cen and cen[1] >= combat.round:                   # Censure (f268): its next action is aimed at whoever censured it
        e.counters.pop("censured", None)
        caster = combat.get(cen[0])
        if caster is not None and caster.alive and caster in targets:
            return caster
    if e.category in ("beast", "swarm") and has(p, "pack_alpha", combat):
        others = [t for t in targets if t is not p and t.alive]
        if others and companion_of(combat) is not None:
            return rng.choice(others)
    return None


# ---------- the roll ----------

def on_outcome(combat: C.Combat, att: C.Fighter, dfn: C.Fighter, outcome: str, rec: dict | None) -> str:
    """The attack roll just made, forced by a perk: a sure crit from hiding, a sure hit from a charged heavy, a cue, a weave."""
    A = C.mechanics(att, combat, dfn)
    if att.side == dfn.side:
        return outcome
    if "dread_ambusher" in A and ("unaware" in dfn.statuses or "concealed" in att.position_tags) and outcome != "crit":
        outcome = "crit"
        if rec is not None:
            rec["note"] = f"{tag(att, 'dread_ambusher')[1:-1]}: unseen, the strike is always critical"
        C.tell(combat, f"{C.who(dfn)} never saw it coming {tag(att, 'dread_ambusher')}")
    if "bulwark_engine" in A and outcome == "miss" and att.counters.get("tier_now") == TIER_CODE["heavy"] \
            and att.counters.get("bulwark", 0) >= P["bulwark_engine"]["sure_at"]:
        outcome = "hit"
        if rec is not None:
            rec["note"] = f"{tag(att, 'bulwark_engine')[1:-1]}: a fully charged heavy cannot miss"
    if att.counters.get("weave_crit") and outcome != "crit":
        att.counters.pop("weave_crit", None)
        outcome = "crit"
        if rec is not None:
            rec["note"] = f"{tag(att, 'threefold_weave')[1:-1]}: the third kind of magic in a row lands critical"
        C.tell(combat, f"three kinds of magic in a row, and the third finds the seam {tag(att, 'threefold_weave')}")
    p = player_of(combat)
    if outcome == "miss" and att.counters.get("tier_now") == TIER_CODE["heavy"] and "blood_for_blood" in A and "bleeding" in att.statuses:
        outcome = "hit"
        if rec is not None:
            rec["note"] = f"{tag(att, 'blood_for_blood')[1:-1]}: bleeding, the heavy cannot miss"
        C.tell(combat, f"blood running, {C.who(att)} {C.vb(att, 'do', 'does')} not miss {tag(att, 'blood_for_blood')}")
    if outcome == "miss" and "judgement" in A and dfn.counters.get("hurt_ally", -9) >= combat.round - 1:
        outcome = "hit"
        if rec is not None:
            rec["note"] = f"{tag(att, 'judgement')[1:-1]}: it hurt an ally, and the blow cannot miss"
        C.tell(combat, f"{C.who(dfn)} hurt one of {C.whose(att)} own, and judgement finds it {tag(att, 'judgement')}")
    if "quarry" in A and att is p and dfn.side == "enemy":
        q = combat.get(QUARRY.get(id(combat), "")) if QUARRY.get(id(combat)) else None
        if q is None or not q.alive or q.fled:
            QUARRY[id(combat)] = dfn.id
            C.tell(combat, f"{C.who(dfn)} is {C.whose(att)} quarry now {tag(att, 'quarry')}")
        if QUARRY.get(id(combat)) == dfn.id and outcome == "graze":
            outcome = "hit"
    if outcome == "miss" and "steady_aim" in A and _ranged_now(att) and _still(combat, att, "steady_round"):
        att.counters["steady_round"] = combat.round
        outcome = "hit"
        if rec is not None:
            rec["note"] = f"{tag(att, 'steady_aim')[1:-1]}: steadied, the shot cannot miss"
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'have', 'has')} not moved, and the shot is true {tag(att, 'steady_aim')}")
    if p is not None and p.alive and outcome in ("graze", "hit") and has(p, "coordinated_strike", combat) \
            and dfn.side == "enemy" and dfn.counters.get("coord", -9) != combat.round \
            and ((att is p and dfn.counters.get("struck_a", -9) == combat.round)
                 or (att.side == "ally" and dfn.counters.get("struck_p", -9) == combat.round)):
        dfn.counters["coord"] = combat.round
        outcome = "crit"
        if rec is not None:
            rec["note"] = f"{tag(p, 'coordinated_strike')[1:-1]}: the second blow of the pair"
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'strike', 'strikes')} in the opening the other made {tag(p, 'coordinated_strike')}")
    if outcome == "crit" and p is not None and p.alive and dfn.side in ("ally",) and has(p, "sanctuary_circle", combat) \
            and dfn.zone_id == p.zone_id and any(b.get("kind") == "stance" for b in p.buffs.values()):
        outcome = "hit"
        if rec is not None:
            rec["note"] = f"{tag(p, 'sanctuary_circle')[1:-1]}: no blow strikes true on this ground"
    if att.counters.get("cue") and outcome in ("graze", "hit"):
        att.counters.pop("cue", None)
        outcome = "crit"
        p = player_of(combat)
        if rec is not None and p is not None:
            rec["note"] = f"{tag(p, 'showstopper')[1:-1]}: following the cue"
        if p is not None:
            C.tell(combat, f"{C.who(att)} takes {C.whose(p)} cue and strikes true {tag(p, 'showstopper')}")
    return outcome


def damage_mult(combat: C.Combat, att: C.Fighter, dfn: C.Fighter, mult: float, rec: dict | None) -> float:
    """The blow's power, by what the perks have charged into it."""
    A = C.mechanics(att, combat, dfn)
    if "bulwark_engine" in A and att.counters.get("tier_now") == TIER_CODE["heavy"] and att.counters.get("bulwark"):
        n = att.counters.pop("bulwark")
        mult = C.hit_step(rec, mult, f"{tag(att, 'bulwark_engine')[1:-1]} ({n} charges)", 1 + P["bulwark_engine"]["per_charge"] * n / 100)
        C.tell(combat, f"every blow {C.who(att)} took in the stance comes back out in this one {tag(att, 'bulwark_engine')}")
    if att.counters.get("drum"):
        att.counters.pop("drum", None)
        p = player_of(combat)
        if p is not None:
            mult = C.hit_step(rec, mult, tag(p, "war_drum")[1:-1], P["war_drum"]["mult"])
            C.tell(combat, f"{C.who(att)} strikes in the rhythm of {C.whose(p)} blow {tag(p, 'war_drum')}")
    if "thick_of_it" in A:
        n = sum(1 for o in combat.fighters if o.alive and o.id in att.engaged_with and o.side != att.side)
        if n > 1:
            mult = C.hit_step(rec, mult, f"{tag(att, 'thick_of_it')[1:-1]} ({n} on you)", 1 + A["thick_of_it"] * (n - 1) / 100)
    if att.counters.get("blood_cast") and "overchannel" in att.mech_names:
        mult = C.hit_step(rec, mult, tag(att, "overchannel")[1:-1], P["overchannel"]["power"])
    return mult


# ---------- after a blow lands ----------

def after_hit(combat: C.Combat, att: C.Fighter, dfn: C.Fighter, outcome: str, taken: float, rng: random.Random) -> None:
    """What follows a blow that landed: wounds torn open, afflictions detonated, lightning, the pack, cues and drums."""
    from engine import battlefield as bf
    p = player_of(combat)
    A = C.mechanics(att, combat, dfn)
    if att.side == dfn.side:
        return
    if "thermal_shock" in A and dfn.alive and taken > 0:
        el = att.hit_element or att.element
        pair = ("slowed", "burning") if el == "fire" else (("burning", "slowed") if el == "cold" else None)
        if pair and pair[0] in dfn.statuses:
            burst = 0.0
            for s in pair:
                left = dfn.statuses.pop(s, 0)
                if s == "burning":
                    from engine import afflictions
                    burst += left * afflictions.tick(dfn, "burning")
                    afflictions.ended(dfn, "burning")
                else:
                    burst += left * taken * P["thermal_shock"]["per_round"]
            if burst > 0:
                dealt = C.take_damage(combat, dfn, burst, att, rng, "magical")
                combat.log.append(f"{dfn.name} suffers a thermal shock: {dealt}")
                C.tell(combat, f"{el} meets its opposite in {C.who(dfn)} and both go off at once {tag(att, 'thermal_shock')}")
    conduct(combat, att, dfn, taken, rng)
    if taken > 0 and dfn.side == "enemy":
        if att is p:
            dfn.counters["struck_p"] = combat.round
        elif att.side == "ally":
            dfn.counters["struck_a"] = combat.round
    rust(combat, att, dfn, taken)
    if taken > 0 and att.spell_kind == "spell" and "arcane_precision" in A:
        dfn.counters["precise"] = 1
    if taken > 0 and "high_ground_hunter" in A and _ranged_now(att) and _high_or_hidden(combat, att):
        dfn.counters["pinned"] = combat.round + 1
    if outcome == "crit" and "dormant_venom" in A and (dfn.counters.get("venom_store") or "poisoned" in dfn.statuses) and dfn.alive:
        from engine import afflictions
        burst = dfn.counters.pop("venom_store", 0) + (dfn.statuses.pop("poisoned", 0) * afflictions.tick(dfn, "poisoned")
                                                       if "poisoned" in dfn.statuses else 0)
        afflictions.ended(dfn, "poisoned")
        dfn.counters.pop("dormant", None)
        if burst > 0:
            dealt = C.take_damage(combat, dfn, burst, att, rng, "physical")
            combat.log.append(f"the gathered venom in {dfn.name} bursts: {dealt} (Dormant Venom)")
            C.tell(combat, f"everything the poison had been saving in {C.who(dfn)} goes off at once {tag(att, 'dormant_venom')}")
    if att.side == "ally" and p is not None and p.alive and taken > 0 and p.max_mana and has(p, "shared_strength", combat) \
            and any(b.get("from") == p.id for b in att.buffs.values()):
        back = p.max_mana * has(p, "shared_strength", combat) / 100
        p.mana = min(p.max_mana, p.mana + back)
        C.tell(combat, f"{C.whose(att)} blow, struck under {C.whose(p)} blessing, sends strength back to {C.who(p)} {tag(p, 'shared_strength')}")
    if "storm_chosen" in A and "in_storm" in combat.conditions and taken > 0:
        others = [e for e in bf.standing(combat, dfn.zone_id) if e is not dfn and e.alive and bf.hostile(att, e)]
        if others:
            held, att.hit_element = att.hit_element, "lightning"
            for e in others:
                arc, _ = C.mitigate(e, taken * P["storm_chosen"]["arc"], "magical", att.level, combat, att)
                combat.log.append(f"lightning arcs to {e.name}: {C.take_damage(combat, e, arc, att, rng, 'magical')}")
            att.hit_element = held
            C.tell(combat, f"the storm answers: lightning leaps from the blow into {', '.join(C.who(e) for e in others)} {tag(att, 'storm_chosen')}")
    if att.summon_form and p is not None and p.alive and p.max_mana and taken > 0 and has(p, "bound_pair", combat):
        back = p.max_mana * P["bound_pair"]["mana"]
        p.mana = min(p.max_mana, p.mana + back)
        C.tell(combat, f"{C.whose(att)} blow sends {round(back)} mana back up the bond {tag(p, 'bound_pair')}")
    if att is p:
        if "provoke" in A and dfn.alive and dfn.side == "enemy":
            dfn.counters["provoked"] = combat.round
        if "showstopper" in A and outcome == "crit":
            for a in combat.allies():
                a.counters["cue"] = 1
            if combat.allies():
                C.tell(combat, f"the perfect strike is a cue, and every companion takes it {tag(p, 'showstopper')}")
        if "war_drum" in A and att.counters.get("tier_now") == TIER_CODE["heavy"]:
            for a in combat.allies():
                a.counters["drum"] = 1
    elif att.side == "ally" and p is not None and p.alive and dfn.side == "enemy" and dfn.alive and "pack_tactics" in C.mechanics(p, combat) \
            and dfn.id in p.engaged_with and p.counters.get("pack_round") != combat.round \
            and bf.attack_access(combat, p, dfn).ok:
        p.counters["pack_round"] = combat.round
        C.tell(combat, f"{C.who(att)} strikes, and you strike with it {tag(p, 'pack_tactics')}")
        C.apply_damage(combat, p, dfn, C.RULES["damage"]["multiplier"]["basic"], "strikes alongside", rng,
                       can_cleave=False, can_riposte=False, can_flurry=False, how="in the same breath")


def on_kill(combat: C.Combat, att: C.Fighter | None, dfn: C.Fighter, rng: random.Random, echo: bool = False) -> None:
    """Something has fallen: the leap resets, the rot walks on, an echo rises, blood answers, the summon feeds."""
    from engine import battlefield as bf
    p = player_of(combat)
    if p is None or dfn.side != "enemy":
        return
    PM = C.mechanics(p, combat)
    if "plaguebearer" in PM:
        carried = {s: r for s, r in dfn.statuses.items() if s in AFFLICTIONS and r > 0}
        others = [e for e in combat.enemies() if e is not dfn]
        if carried and others:
            nxt = bf.closest(combat, dfn, others) or others[0]
            for s, r in carried.items():
                nxt.statuses[s] = max(nxt.statuses.get(s, 0), r)
            if "burning" in carried:
                nxt.ignite = max(nxt.ignite, dfn.ignite)          # the burn walks on at its strength
            if "poisoned" in carried:
                nxt.poison = list(nxt.poison) + list(dfn.poison)  # and every stack of the poison with it
            if "bleeding" in carried:
                nxt.bleed = max(nxt.bleed, dfn.bleed)
            combat.log.append(f"{', '.join(carried)} pass from {dfn.name} to {nxt.name} (Plaguebearer)")
            C.tell(combat, f"what was eating {C.who(dfn)} does not die with {C.vb(dfn, 'you', 'it')}: it crawls on to {C.who(nxt)} {tag(p, 'plaguebearer')}")
    if att is None:
        return
    if (att.hit_element or att.element) == "cold" and "frozen_ground" in C.mechanics(att, combat) and dfn.zone_id:
        rounds = int(C.mechanics(att, combat)["frozen_ground"] or 2)
        combat.zone_effects[dfn.zone_id] = {"frozen_until": combat.round + rounds, "by": att.id}
        C.tell(combat, f"where {C.who(dfn)} fell the ground freezes hard - anyone standing there will feel it {tag(att, 'frozen_ground')}")
    if att is p:
        if "deathleap" in PM and p.last_mobility:
            move = next((m for m in p.moves if m.id == p.last_mobility), None)
            if move is not None and (p.cooldowns.get(move.id, 0) > 0 or p.counters.get("last_mobility_cost")):
                p.cooldowns.pop(move.id, None)
                back = p.counters.pop("last_mobility_cost", 0)
                if move.resource == "stamina":
                    p.stamina = min(p.max_stamina, p.stamina + back)
                else:
                    p.mana = min(p.max_mana, p.mana + back)
                combat.log.append(f"{move.name} is ready again (Deathleap)")
                C.tell(combat, f"the kill resets {C.whose(p)} footing: {move.name} is ready again, its cost returned {tag(p, 'deathleap')}")
        if "grave_chorus" in PM and not echo:
            n = p.counters.get("echoes", 0)
            if n < P["grave_chorus"]["cap"]:
                p.counters["echoes"] = n + 1
                C.tell(combat, f"something of {C.who(dfn)} stays standing: a spectral echo, waiting on {C.whose(p)} next working {tag(p, 'grave_chorus')}")
        if "headsman" in PM and att.counters.get("tier_now") == TIER_CODE["heavy"]:
            p.counters["headsman"] = 1
            C.tell(combat, f"the head falls, and the next great blow will cost {C.who(p)} nothing {tag(p, 'headsman')}")
        from engine import spellcraft as _sc
        if "shadowstep" in PM and _sc.zone_hidden(combat, p.zone_id) and _sc.can_hide(combat, p) \
                and "concealed" not in p.position_tags:
            bf.gain(p, "concealed")
            p.counters["rehid"] = 1                       # hidden again by the kill: the strike does not give you away
            C.tell(combat, f"in the moment the body drops, {C.who(p)} {C.vb(p, 'are', 'is')} gone into the cover {tag(p, 'shadowstep')}")
        if "rampage" in PM and p.hp < p.max_hp * P["rampage"]["below"]:
            heal = round(p.max_hp * P["rampage"]["heal"])
            C.restore(combat, p, heal)
            combat.log.append(f"{p.name} is restored by the kill: +{heal} (Rampage)")
            C.tell(combat, f"the kill pours strength back into {C.who(p)}: {heal} health {tag(p, 'rampage')}")
    elif att.summon_form and "devourer" in PM:
        g = P["devourer"]["grow"]
        more = round(att.max_hp * g)
        att.max_hp += more
        C.restore(combat, att, more)
        att.weapon_damage *= 1 + g
        combat.log.append(f"{att.name} grows on the kill (Devourer)")
        C.tell(combat, f"{C.who(att)} feeds on the fallen and grows - bigger, harder, hungrier {tag(p, 'devourer')}")


def on_dot_death(combat: C.Combat, f: C.Fighter) -> None:
    """An enemy that succumbed to an affliction at the start of its turn: the player's afflictions, the player's kill."""
    from engine import battlefield as bf
    bf.release(combat, f)
    combat.log.append(f"{f.name} succumbs")
    C.tell(combat, f"{C.who(f)} succumbs to what was done to {C.vb(f, 'you', 'it')} and falls")
    p = player_of(combat)
    rng = random.Random(combat.round * 17 + len(combat.log))
    from engine import behaviors
    behaviors.morale_on_death(combat, f, rng)
    if f.counters.get("reaped_by"):
        from engine import spellcraft
        spellcraft.reaped(combat, f)                     # Reap (f266): a death by affliction counts too
    if p is not None:
        p.kill_round = combat.round
        on_kill(combat, p, f, rng)


# ---------- taking a blow ----------

def before_damage(combat: C.Combat, dfn: C.Fighter, amount: float, source: C.Fighter | None, rng: random.Random, damage_type: str) -> float:
    """A blow about to land, capped or shared out before it does."""
    p = player_of(combat)
    if p is None or amount <= 0:
        return amount
    if dfn is p and has(p, "unbreakable", combat):
        cap = p.max_hp * P["unbreakable"]["cap"]
        if amount > cap:
            C.tell(combat, f"the blow should have broken you, but nothing does {tag(p, 'unbreakable')}")
            amount = cap
    if dfn.side == "ally" and p.alive and has(p, "martyr", combat) and not p.counters.get("martyring") and source is not p:
        moved = amount * P["martyr"]["share"]
        amount -= moved
        p.counters["martyring"] = 1
        try:
            C.take_damage(combat, p, moved, source, rng, damage_type)
        finally:
            p.counters.pop("martyring", None)
        C.tell(combat, f"half of what was meant for {C.who(dfn)} lands on you instead {tag(p, 'martyr')}")
    if dfn is p and has(p, "shared_skin", combat) and not p.counters.get("sharing"):
        s = summon_of(combat)
        if s is not None and source is not s:
            moved = amount * P["shared_skin"]["share"]
            amount -= moved
            p.counters["sharing"] = 1
            try:
                C.take_damage(combat, s, moved, source, rng, damage_type)
            finally:
                p.counters.pop("sharing", None)
            C.tell(combat, f"a share of the hurt passes through the bond into {C.who(s)} {tag(p, 'shared_skin')}")
    return amount


def after_damage(combat: C.Combat, dfn: C.Fighter, dealt: int, source: C.Fighter | None) -> None:
    """A blow has landed: what the pain fuels."""
    if dealt > 0 and source is not None and source.side == "enemy" and dfn.side == "ally":
        source.counters["hurt_ally"] = combat.round
    if dealt <= 0 or not dfn.alive:
        return
    D = C.mechanics(dfn, combat, source)
    if "pain_engine" in D and dfn.max_mana:
        back = dealt * P["pain_engine"]["share"]
        dfn.mana = min(dfn.max_mana, dfn.mana + back)
        C.tell(combat, f"the pain burns into power: {round(back)} mana {tag(dfn, 'pain_engine')}")
    if "adrenaline" in D and dfn.max_stamina:
        back = dealt * P["adrenaline"]["share"]
        dfn.stamina = min(dfn.max_stamina, dfn.stamina + back)
        C.tell(combat, f"the hurt wakes {C.who(dfn)} up: {round(back)} stamina {tag(dfn, 'adrenaline')}")
    if "bulwark_engine" in D and any(b.get("kind") == "stance" for b in dfn.buffs.values()):
        dfn.counters["bulwark"] = dfn.counters.get("bulwark", 0) + 1
        n = dfn.counters["bulwark"]
        if n == P["bulwark_engine"]["sure_at"]:
            C.tell(combat, f"{C.whose(dfn)} stance has taken enough: the next heavy will not miss {tag(dfn, 'bulwark_engine')}")
        else:
            C.tell(combat, f"the stance drinks the blow in ({n} charge{'s' if n != 1 else ''}) {tag(dfn, 'bulwark_engine')}")
    if "flow_state" in D and not dfn.counters.get("hit_taken"):
        dfn.counters["hit_taken"] = 1
        C.tell(combat, f"the first blow lands, and the flow is broken {tag(dfn, 'flow_state')}")


# ---------- afflictions ----------

def on_status(combat: C.Combat, f: C.Fighter, status: str, rounds: int, source: C.Fighter | None) -> tuple[str, int] | None:
    """An affliction about to take hold. Returns what takes hold, or None when a perk turns it aside or passes it on."""
    F = C.mechanics(f, combat, source)
    if status in ("prone", "grappled") and unmovable(combat, f):
        C.tell(combat, f"{C.who(f)} {C.vb(f, 'do', 'does')} not budge {tag(f, 'juggernaut')}")
        return None
    if status == "slowed" and "frostborne" in F:
        f.counters["quick_until"] = combat.round + rounds
        if f.pace != "fast":
            f.counters["pace_was"] = ["slow", "normal", "fast"].index(f.pace)
            f.pace = "fast"
        C.tell(combat, f"the chill quickens {C.who(f)} instead of slowing {C.vb(f, 'you', 'it')} {tag(f, 'frostborne')}")
        return None
    if "red_mist" in F and f.hp < f.max_hp * P["red_mist"]["below"] and status in ("stunned", "frightened", "slowed"):
        C.tell(combat, f"{C.who(f)} {C.vb(f, 'do', 'does')} not even feel it {tag(f, 'red_mist')}")
        return None
    if "vessel" in F and status in VESSEL_TAKES and not f.counters.get("vesseling"):
        s = summon_of(combat)
        if s is not None and s is not f:
            f.counters["vesseling"] = 1
            try:
                took = C.add_status(combat, s, status, rounds, source)
            finally:
                f.counters.pop("vesseling", None)
            if took:
                C.tell(combat, f"it was meant for {C.who(f)}, but it is {C.who(s)} that {C.STATUS_WORDS[status][1]} {tag(f, 'vessel')}")
                return None
    S = C.mechanics(source, combat, f) if source is not None else {}
    if status == "poisoned" and "dormant_venom" in S:
        f.counters["dormant"] = 1
    if status in AFFLICTIONS and "withering" in S:
        f.counters["withered"] = 1
        WITHER[(id(combat), f.id)] = source.id
    if "deep_freeze" in S and status == "slowed" and "slowed" in f.statuses and not f.counters.get("freezing"):
        f.counters["freezing"] = 1
        try:
            froze = C.add_status(combat, f, "stunned", P["deep_freeze"]["stun_rounds"], source)
        finally:
            f.counters.pop("freezing", None)
        if froze:
            C.tell(combat, f"slowed twice over, {C.who(f)} {C.vb(f, 'grind', 'grinds')} to a halt {tag(source, 'deep_freeze')}")
    if "mirror_plate" in F and status in ("stunned", "prone") and source is not None and source.alive and source.side != f.side \
            and not f.counters.get("mirroring"):
        f.counters["mirroring"] = 1
        try:
            back = C.add_status(combat, source, status, rounds, None)
        finally:
            f.counters.pop("mirroring", None)
        if back:
            C.tell(combat, f"whatever {C.who(source)} did to {C.who(f)} comes back on {C.vb(source, 'you', 'it')} {tag(f, 'mirror_plate')}")
    return status, rounds


def on_status_end(f: C.Fighter, status: str) -> None:
    from engine import afflictions
    afflictions.ended(f, status)


def dot_damage(f: C.Fighter, dot: str, amount: int) -> int:
    if dot == "poisoned" and f.counters.get("dormant"):
        f.counters["venom_store"] = f.counters.get("venom_store", 0) + amount
        return 0
    return amount


# ---------- what an ability asks ----------

def cost(combat: C.Combat | None, f: C.Fighter, move: C.Move, cost: float) -> float:
    """An ability's cost, by the perks: heavies as lights in the red, free lights in the flow, a cooldown bought through."""
    F = C.mechanics(f, combat)
    if "red_mist" in F and move.tier == "heavy" and f.hp < f.max_hp * P["red_mist"]["below"]:
        table = C.RULES["stamina_cost_percent" if move.resource == "stamina" else "ability_cost_percent"]
        cost *= table["light"] / table["heavy"]
    if "flow_state" in F and move.tier == "light" and not f.counters.get("hit_taken"):
        cost = 0
    if "headsman" in F and move.tier == "heavy" and f.counters.get("headsman"):
        cost = 0
    if "ley_tether" in F and move.resource == "mana" and combat is not None and _still(combat, f, "tether_round"):
        cost *= 1 - F["ley_tether"] / 100
    if "overcast" in F and f.cooldowns.get(move.id, 0) > 0:
        cost *= P["overcast"]["cost"]
    return cost


def may_overcast(combat: C.Combat | None, f: C.Fighter, move: C.Move) -> bool:
    return bool(has(f, "overcast", combat)) and f.cooldowns.get(move.id, 0) > 0


# ---------- the player's own abilities ----------

def on_cast(combat: C.Combat, att: C.Fighter, move: C.Move, echo: bool, cost_paid: float = 0) -> None:
    """The cost is paid and the ability is about to resolve: the echo and the weave count it, the bond answers it, the leap is
    remembered (before it lands, so a kill made by the leap itself resets it)."""
    A = C.mechanics(att, combat)
    if echo:
        return
    if "headsman" in A and move.tier == "heavy" and att.counters.pop("headsman", None):
        C.tell(combat, f"the great blow comes without effort {tag(att, 'headsman')}")
    if "ley_tether" in A and move.resource == "mana" and _still(combat, att, "tether_round"):
        att.counters["tether_round"] = combat.round
        C.tell(combat, f"standing fast, {C.who(att)} {C.vb(att, 'draw', 'draws')} the spell up from the ground beneath {tag(att, 'ley_tether')}")
    if "attuned_edge" in A and move.resource == "mana" and move.element and att.attuned != move.element:
        att.attuned = move.element
        C.tell(combat, f"{C.whose(att)} weapon takes on the {move.element} of the spell {tag(att, 'attuned_edge')}")
    if move.effect == "mobility":
        att.last_mobility = move.id
        att.counters["last_mobility_cost"] = int(cost_paid)
    if move.resource == "mana":
        att.recent_casts = (att.recent_casts + [move.id])[-3:]
        run = P["spell_echo"]["run"]
        if "spell_echo" in A and len(att.recent_casts) >= run and len(set(att.recent_casts[-run:])) == 1:
            att.counters["echo_now"] = 1
            att.recent_casts = []
        if "threefold_weave" in A and len(att.recent_casts) >= P["threefold_weave"]["run"]:
            keys = [_cast_key(m) for mid in att.recent_casts[-3:] for m in att.moves if m.id == mid]
            if len(keys) == 3 and len(set(keys)) == 3:
                att.counters["weave_crit"] = 1
                att.recent_casts = []
        if "bound_pair" in A:
            s = summon_of(combat)
            if s is not None and s.hp < s.max_hp:
                heal, _ = mend(combat, att, s, round(s.max_hp * P["bound_pair"]["heal"]))
                C.tell(combat, f"the casting flows down the bond, and {C.who(s)} mends ({heal}) {tag(att, 'bound_pair')}")
    if att.counters.get("overcasting"):
        att.counters.pop("overcasting", None)
        C.tell(combat, f"{move.name} is not ready, and {C.who(att)} {C.vb(att, 'force', 'forces')} it anyway, at twice the price {tag(att, 'overcast')}")


def after_cast(combat: C.Combat, att: C.Fighter, move: C.Move, target: C.Fighter | None, rng: random.Random,
               give: list[C.Fighter] | None, echo: bool, cost_paid: float) -> None:
    """The ability has resolved: buffs that last, heals that spread, the leap remembered, and the repeats an echo or a chorus owe."""
    A = C.mechanics(att, combat)
    p = player_of(combat)
    att.counters.pop("weave_crit", None)
    if move.effect == "buff" and "lasting_word" in A:
        for r in (give or [att]):
            if move.id in r.buffs:
                r.buffs[move.id]["rounds"] = P["lasting_word"]["rounds"]
        C.tell(combat, f"{move.name} will not fade while the fight lasts {tag(att, 'lasting_word')}")
    if move.effect == "healing":
        from engine import healing as _heal
        healed_id, amount = _heal.LAST.get(id(combat), (att.id, 0.0))
        healed = combat.get(healed_id) or att
        amount = round(amount)
        if "mending_rhythm" in A and not echo:
            att.counters["heals_cast"] = att.counters.get("heals_cast", 0) + 1
            if att.counters["heals_cast"] % 3 == 0:
                for a in [x for x in combat.allies() if x.alive]:
                    mend(combat, att, a, amount)
                C.tell(combat, f"the third mending in its rhythm reaches the whole company {tag(att, 'mending_rhythm')}")
        if "echoing_mend" in A:
            hurt = [a for a in combat.allies() if a.alive and a.hp < a.max_hp]
            if hurt:
                t = min(hurt, key=lambda a: a.hp / max(1, a.max_hp))
                half, _ = mend(combat, att, t, round(amount * P["echoing_mend"]["share"]))
                combat.log.append(f"{t.name} is healed {half} (Echoing Mend)")
                C.tell(combat, f"the mending carries on into {C.who(t)} ({half}) {tag(att, 'echoing_mend')}")
        if "consecration" in A:
            undead = [combat.get(i) for i in healed.engaged_with]
            undead = [u for u in undead if u is not None and u.alive and u.category == "undead"]
            if undead:
                held, att.hit_element = att.hit_element, P["consecration"]["element"]
                for u in undead:
                    burn, _ = C.mitigate(u, amount * P["consecration"]["share"], "magical", att.level, combat, att)
                    combat.log.append(f"{u.name} is seared by the healing: {C.take_damage(combat, u, burn, att, rng, 'magical')}")
                att.hit_element = held
                C.tell(combat, f"the same light that mends {C.who(att)} sears the dead that press {C.vb(att, 'you', 'them')} {tag(att, 'consecration')}")
    if echo:
        return
    if att.counters.pop("echo_now", None):
        C.tell(combat, f"{move.name}, three times running - and the third time it happens twice {tag(att, 'spell_echo')}")
        C.act_ability(combat, att, move, target, rng, give=give, echo=True)
    if att is p and move.effect == "damage" and att.counters.get("echoes"):
        n = att.counters.pop("echoes")
        C.tell(combat, f"{n} spectral echo{'es' if n != 1 else ''} repeat{'s' if n == 1 else ''} the working {tag(att, 'grave_chorus')}")
        for _ in range(n):
            if combat.enemies():
                C.act_ability(combat, att, move, target if target is not None and target.alive else None, rng, give=give, echo=True)


def unmaking(combat: C.Combat, att: C.Fighter, move: C.Move, rng: random.Random) -> bool:
    """A summon spell cast while what it made still stands: it detonates. True when it did (no new summon is made). Never the
    Bound summon - only the ones made in the fight."""
    if not has(att, "unmaking", combat):
        return False
    from engine import summons
    mine = [f for f in summons.made(combat, att) if f.summon_of == move.id]
    if not mine:
        return False
    s = mine[0]
    from engine import battlefield as bf
    power = C.RULES["spell_base_damage"] * C.growth(att.level) * C.RULES["damage"]["multiplier"][P["unmaking"]["tier"]]
    victims = [e for e in bf.standing(combat, s.zone_id) if e.alive and bf.hostile(s, e)] if combat.battlefield else combat.enemies()
    for e in victims:
        hit, _ = C.mitigate(e, power, "magical", att.level, combat, att)
        combat.log.append(f"{e.name} is caught in the unmaking: {C.take_damage(combat, e, hit, att, rng, 'magical')}")
    for f in mine:
        f.hp = 0
        f.counters["dead"] = 1
        bf.release(combat, f)
    combat.log.append(f"{s.name} is unmade")
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'speak', 'speaks')} {move.name} with {C.who(s)} already standing, and {C.vb(s, 'you come', 'it comes')} apart in a burst that takes "
           + (", ".join(C.who(e) for e in victims) if victims else "nothing but the air") + f" with it {tag(att, 'unmaking')}")
    return True


def failed_threat(combat: C.Combat, target: C.Fighter) -> None:
    """A threat that did not land, from someone whose threats always leave a mark."""
    p = player_of(combat)
    if p is not None and has(p, "fearmonger", combat) and target.alive and C.add_status(combat, target, "frightened", P["fearmonger"]["rounds"], p):
        combat.log.append(f"{target.name} is frightened all the same (Fearmonger)")
        C.tell(combat, f"{C.who(target)} laughs it off - and keeps glancing at you all the same, afraid {tag(p, 'fearmonger')}")


def item_limit(combat: C.Combat, p: C.Fighter) -> int:
    return int(P["two_fisted"]["items"]) if has(p, "two_fisted", combat) else 1


# ---------- healing ----------

def mend(combat: C.Combat, healer: C.Fighter | None, target: C.Fighter, amount: float) -> tuple[int, int]:
    """Healing applied through the perks: what lands as health, and what Overabundance keeps as a barrier instead of wasting.
    Every heal in a fight - a healing ability, a draught, a mend that carries on - comes through here."""
    if "unraveled" in target.statuses:                    # necrotic unravelling (f263): the heal deals its amount as damage instead
        if "withered" in target.statuses:
            from engine import healing as _heal
            amount *= _heal.wither_factor(target)
        C.restore(combat, target, amount, healer)
        return 0, 0
    if "withered" in target.statuses:
        from engine import healing as _heal
        amount *= _heal.wither_factor(target)
    if healer is not None and has(healer, "triage", combat) and target.hp < target.max_hp * 0.25:
        amount *= 2
        worst = next((s_ for s_ in AFFLICTIONS if s_ in target.statuses), None)
        if worst:
            target.statuses.pop(worst)
        C.tell(combat, f"{C.who(healer)} {C.vb(healer, 'see', 'sees')} how close {C.who(target)} came, and the healing runs double"
               + (f", lifting the {worst} too" if worst else "") + f" {tag(healer, 'triage')}")
    if amount > 0 and "bleeding" in target.statuses:
        from engine import afflictions
        afflictions.bind(combat, target, "is mended")    # any heal closes an open wound
    before = target.hp
    target.hp = min(target.max_hp, target.hp + amount)
    healed = round(target.hp - before)
    over = amount - (target.hp - before)
    shielded = 0
    if over > 0.5 and healer is not None and has(healer, "overabundance", combat):
        cap = target.max_hp * P["overabundance"]["cap"]
        room = max(0.0, cap - target.shield)
        shielded = round(min(over, room))
        if shielded > 0:
            target.shield += shielded
            combat.log.append(f"{target.name} gains a barrier of {shielded} (Overabundance)")
            C.tell(combat, f"the healing {C.who(target)} {C.vb(target, 'do', 'does')} not need does not go to waste: it hardens into a barrier "
                   f"({shielded}) {tag(healer, 'overabundance')}")
    return healed, shielded


# ---------- the challenge ----------

CHALLENGE_WORDS = ("single combat", "one on one", "one-on-one", "alone", "challenge", "duel", "champion", "your best", "just you and me",
                   "face me", "fight me")


def is_challenge(text: str) -> bool:
    """Whether the player's words mean a challenge to single combat: by meaning when the helper model is there, by words when not."""
    from engine import relevance
    try:
        if relevance.pick(text, [P["challenger"]["about"]], 1, floor=0.3):
            return True
    except Exception:
        pass
    low = (text or "").lower()
    return any(w in low for w in CHALLENGE_WORDS)


def challenge(combat: C.Combat, text: str, rng: random.Random) -> bool:
    """Challenger: the player calls for single combat in a fight with people. Their leader steps out to face the player alone; the rest
    stand down - out of the fight, bound by the result - and the player's own companions hold back. True when it happened."""
    from engine import battlefield as bf
    p = player_of(combat)
    if p is None or not has(p, "challenger", combat) or p.counters.get("challenged"):
        return False
    foes = combat.enemies()
    people = [e for e in foes if e.category in P["challenger"]["people"] and not e.boss]
    if len(foes) < 2 or len(people) != len(foes) or not is_challenge(text):
        return False
    p.counters["challenged"] = 1
    leader = max(people, key=lambda e: (e.rank == "elite", e.level, e.max_hp))
    rest = [e for e in people if e is not leader]
    for e in rest:
        bf.release(combat, e)
        e.fled = True
        e.counters["stood_down"] = 1
    for a in combat.allies():
        if a.ally_role != "mentor":
            a.order = "hold"
    combat.focus = leader.id
    combat.log.append(f"{p.name} calls for single combat: {leader.name} accepts; {', '.join(e.name for e in rest)} stand down (Challenger)")
    C.tell(combat, f"you call for single combat, and the call carries: {C.who(leader)} steps out to answer it alone, and "
           f"{', '.join(C.who(e) for e in rest)} {'stands' if len(rest) == 1 else 'stand'} down to watch, bound by whatever comes of it"
           + (f" - {', '.join(a.name for a in combat.allies())} hold back" if combat.allies() else "") + f" {tag(p, 'challenger')}")
    return True


# ---------- the glass cannon and the conduit ----------

def crit_chance(combat: C.Combat, att: C.Fighter, crit: float) -> float:
    """Glass Cannon: a spell's chance to crit, multiplied."""
    if att.spell_kind == "spell" and has(att, "glass_cannon", combat):
        return crit * P["glass_cannon"]["crit_mult"]
    return crit


def crit_cap_mult(combat: C.Combat, att: C.Fighter) -> float:
    """...and the ceiling on crit chance moves with it, so the doubling is real at the top as well."""
    if att.spell_kind == "spell" and has(att, "glass_cannon", combat):
        return P["glass_cannon"]["crit_mult"]
    return 1.0


def conduct(combat: C.Combat, att: C.Fighter, dfn: C.Fighter, taken: float, rng: random.Random) -> None:
    """Conduit: a spell leaps on - one more enemy for each affliction on the one it struck, at half strength. A leap never leaps."""
    from engine import battlefield as bf
    if att.spell_kind != "spell" or taken <= 0 or att.counters.get("conducting") or not has(att, "conduit", combat):
        return
    n = sum(1 for s in dfn.statuses if s in AFFLICTIONS)
    others = [e for e in combat.enemies() if e is not dfn and e.alive]
    if not n or not others:
        return
    others.sort(key=lambda e: 0 if e.zone_id == dfn.zone_id else 1)
    hit = others[:n]
    att.counters["conducting"] = 1
    try:
        for e in hit:
            leap, _ = C.mitigate(e, taken * P["conduit"]["share"], "magical", att.level, combat, att)
            combat.log.append(f"the spell leaps to {e.name}: {C.take_damage(combat, e, leap, att, rng, 'magical')} (Conduit)")
    finally:
        att.counters.pop("conducting", None)
    C.tell(combat, f"the afflictions on {C.who(dfn)} carry the spell on into {', '.join(C.who(e) for e in hit)} {tag(att, 'conduit')}")


# ---------- round two (f217): movement, stillness, ground and the turncoat ----------

QUARRY: dict[int, str] = {}           # fight -> the player's quarry (kept off the fighters so a save never carries a stale mark)
WITHER: dict[tuple, str] = {}         # (fight, fighter) -> who placed the withering afflictions


def _ranged_now(att: C.Fighter) -> bool:
    """Whether the blow being made right now is a ranged one: an ability's reach while it resolves, else the weapon's."""
    reach = att.counters.get("reach_now")
    if reach:
        return reach in (1, 3)                            # 1 ranged, 2 melee/extended, 3 area
    return att.reach == "ranged"


def _still(combat: C.Combat, f: C.Fighter, key: str) -> bool:
    """A full round without moving, and without spending this stillness already: Steady Aim and Ley Tether each keep their own."""
    return combat.round - max(f.move_round, f.counters.get(key, -9)) >= 2


def _high_or_hidden(combat: C.Combat, att: C.Fighter) -> bool:
    bf = combat.battlefield
    zone = bf.zones.get(att.zone_id) if bf is not None else None
    return "elevated" in att.position_tags or "concealed" in att.position_tags or bool(zone and zone.has("elevated"))


def unmovable(combat: C.Combat | None, f: C.Fighter) -> bool:
    """Juggernaut: in heavy armor, nothing moves you. Stoneform: nothing moves stone."""
    if any(b.get("kind") == "stoneform" for b in (f.buffs or {}).values()):
        return True
    return f.armor_weight == "heavy" and bool(has(f, "juggernaut", combat))


def held_fast(combat: C.Combat, e: C.Fighter) -> bool:
    """An enemy that cannot step away: engaged with a juggernaut, or the player's quarry."""
    if QUARRY.get(id(combat)) == e.id and any(o.side == "player" and has(o, "quarry", combat) for o in combat.fighters):
        return True
    if "frostwelded" in e.statuses:
        return True                                      # Frostweld (f268)
    return any(o.alive and o.id in e.engaged_with and unmovable(combat, o) for o in combat.fighters)


def pinned(combat: C.Combat, e: C.Fighter) -> bool:
    """High Ground Hunter: no free step this round."""
    return e.counters.get("pinned", -9) >= combat.round


def sees_through_cover(fight, att: C.Fighter, dfn: C.Fighter) -> bool:
    """Cover that does not count against this attacker: a spell at a target your spells have already found (Arcane Precision), or a
    shot from high or hidden ground (High Ground Hunter)."""
    A = C.mechanics(att, fight)
    if "arcane_precision" in A and att.spell_kind == "spell" and dfn.counters.get("precise"):
        return True
    return "high_ground_hunter" in A and _high_or_hidden(fight, att)


def rust(combat: C.Combat, att: C.Fighter, dfn: C.Fighter, taken: float) -> None:
    """Curse of Rust: with no metal on you, each hit strips armor off them, stacking to a cap."""
    if taken <= 0 or att.wears_metal or dfn.side == att.side or not has(att, "curse_of_rust", combat):
        return
    cap = int(P["curse_of_rust"]["cap"])
    n = dfn.counters.get("rust", 0)
    if n >= cap:
        return
    if "rust_base" not in dfn.counters:
        dfn.counters["rust_base"] = int(round(dfn.armor * 100))
    n += 1
    dfn.counters["rust"] = n
    dfn.armor = dfn.counters["rust_base"] / 100 * max(0.0, 1 - has(att, "curse_of_rust", combat) * n / 100)
    C.tell(combat, f"{C.whose(dfn)} armor flakes away where {C.who(att)} struck ({n}/{cap}) {tag(att, 'curse_of_rust')}")


def on_turn_start(combat: C.Combat, f: C.Fighter) -> None:
    """At the start of a fighter's turn: Frostborne's quickening runs out, frozen ground chills whoever stands on it, and the
    quarry cannot keep hiding."""
    if f.counters.get("quick_until") is not None and f.counters["quick_until"] < combat.round:
        f.counters.pop("quick_until")
        was = f.counters.pop("pace_was", None)
        if was is not None:
            f.pace = ["slow", "normal", "fast"][was]
    eff = combat.zone_effects.get(f.zone_id)
    if eff and eff.get("frozen_until", -9) >= combat.round and f.alive:
        by = combat.get(eff.get("by", "")) if eff.get("by") else None
        C.add_status(combat, f, "slowed", 2, by)         # 2: it is worn down at the end of this same turn-start, so it holds this turn
    elif eff and "frozen_until" in eff and eff["frozen_until"] < combat.round:
        eff.pop("frozen_until", None)
        eff.pop("by", None)
        if not eff:
            combat.zone_effects.pop(f.zone_id, None)
    if f.side == "player":
        q = combat.get(QUARRY.get(id(combat), "")) if QUARRY.get(id(combat)) else None
        if q is not None and q.alive and "concealed" in q.position_tags:
            from engine import battlefield as bf
            bf.lose(q, "concealed")
            C.tell(combat, f"{C.who(q)} cannot hide from {C.who(f)} {tag(f, 'quarry')}")


def withering_holds(combat: C.Combat, f: C.Fighter, status: str) -> bool:
    """Withering: an affliction does not wear off while whoever placed it shares ground with its bearer."""
    if status not in AFFLICTIONS or not f.counters.get("withered"):
        return False
    w = combat.get(WITHER.get((id(combat), f.id), ""))
    return w is not None and w.alive and w.zone_id == f.zone_id


def feral(att: C.Fighter, combat: C.Combat) -> float:
    """Feral Form: while a blessing you cast on yourself lasts, a weapon blow carries your spell power - the channel's share of it."""
    if not has(att, "feral_form", combat) or not any(b.get("from") == att.id and b.get("kind") not in ("stance",) for b in att.buffs.values()):
        return 0.0
    attr = max(att.attrs.get(a, 10) for a in ("intelligence", "wisdom", "charisma"))
    mult = 1 + attr / C.RULES["spell_attribute"]
    gear = att.offhand_spell + C.flat_bonus(att, "spell_power", {"always"})
    return C.RULES["channel"]["bonus"] * (C.RULES["spell_base_damage"] * C.growth(att.level) + gear) * mult


def blood_summon(combat: C.Combat, att: C.Fighter, move: C.Move, rng: random.Random) -> bool:
    """Blood Summons: with no summon standing, a summon spell calls a striker from your blood instead - a tier stronger, lasting the
    whole fight. True when it did (the spell's own summon is not made)."""
    if not has(att, "blood_summons", combat) or summon_of(combat) is not None:
        return False
    from engine import summons
    tiers = ["light", "moderate", "heavy"]
    tier = tiers[min(2, tiers.index(move.tier) + 1)] if move.tier in tiers else "heavy"
    price = round(att.max_hp * P["blood_summons"]["health"])
    if att.hp <= price:
        return False
    att.hp -= price
    for s_ in summons.make(combat, att, move, form="striker", tier=tier, until=0, name="the blood-spirit"):
        C.enters(combat, s_)
    combat.log.append(f"{att.name} pays {price} health for a blood-spirit (Blood Summons)")
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'open', 'opens')} a vein and {move.name} answers in blood: a spirit stands, stronger than it "
           f"should be, for as long as this fight lasts {tag(att, 'blood_summons')}")
    return True


def turn_coat(combat: C.Combat, f: C.Fighter) -> bool:
    """Dread Regent: the first enemy to break and run turns on its own side instead. True when it turned (it does not flee)."""
    p = player_of(combat)
    if p is None or not p.alive or p.counters.get("regent") or not has(p, "dread_regent", combat) or f.boss:
        return False
    if not any(e is not f for e in combat.enemies()):
        return False
    p.counters["regent"] = 1
    f.counters["turned"] = 1
    from engine import battlefield as bf
    bf.release(combat, f)
    combat.log.append(f"{f.name} turns on its own side (Dread Regent)")
    C.tell(combat, f"{C.who(f)} breaks - and instead of running, turns on its own side in terror {tag(p, 'dread_regent')}")
    return True


def turned_turn(combat: C.Combat, e: C.Fighter, rng: random.Random) -> None:
    """A turned enemy's turn: it goes for the nearest of its former side, and leaves once none remain."""
    from engine import battlefield as bf
    others = [o for o in combat.enemies() if o is not e]
    if not others:
        e.fled = True
        C.tell(combat, f"{C.who(e)} flees, its old side broken")
        return
    t = bf.closest(combat, e, others) or others[0]
    if not bf.attack_access(combat, e, t).ok:
        bf.approach(combat, e, t)
        return
    C.apply_damage(combat, e, t, C.RULES["damage"]["multiplier"]["basic"], "turns on", rng, can_cleave=False, can_riposte=False,
                   can_flurry=False, how="in its terror")


def familiar_access(combat: C.Combat, att: C.Fighter, aim: C.Fighter, move: C.Move, quiet: bool = False):
    """Familiar's Eyes: a spell you cannot get at from where you stand may be cast from where your summon stands. Returns the access
    from there when it is open, else None."""
    if not has(att, "familiars_eyes", combat):
        return None
    s_ = summon_of(combat)
    if s_ is None:
        return None
    from engine import battlefield as bf
    a = bf.attack_access(combat, s_, aim, move.reach)
    if a.ok:
        if not quiet:
            C.tell(combat, f"{C.who(att)} {C.vb(att, 'cast', 'casts')} through {C.whose(s_)} eyes {tag(att, 'familiars_eyes')}")
        return a
    return None
