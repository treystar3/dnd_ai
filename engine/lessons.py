"""Slot-based lessons from a guild instructor.

Like creation (engine/ability_slots.py) the engine plans every lesson first - an ability with its effect, tier, reach, cost and trait,
or a passive trait with its stat and condition (or a mechanic) - and the model only NAMES and DESCRIBES them.

A request is read into a Want (what kind of thing, which effect or stat). Most of the options lean toward it; the rest are wildcards,
so the player is shown something they did not ask for too. Riders, shapes, buffs, functions and passives the character already has
are not offered again. No model code here: scenes/lesson_ask.py makes the calls. Data: data/rules/training.yaml."""

import random
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import yaml

from core.rules import STATS, TRIGGERS
from engine import ability_slots as AS
from engine import ability_traits as AT
from engine import field

ROOT = Path(__file__).resolve().parent.parent
T = yaml.safe_load((ROOT / "data" / "rules" / "training.yaml").read_text(encoding="utf-8"))
L = T["lessons"]
EFFECTS = list(L["effect_words"])
FAMILIES_BY_ARCHETYPE = {"warrior": ["warrior"], "mage": ["mage"], "rogue": ["rogue"], "support": ["healer"]}


# ---------- reading the request ----------

@dataclass
class Want:
    kind: str = "either"        # active | passive | either
    effect: str = ""
    stat: str = ""
    text: str = ""
    element: str = ""           # an element the request names: the lessons that answer it carry that element

    def words(self) -> set[str]:
        return {w for w in re.findall(r"[a-z]+", self.text.lower()) if len(w) >= 4}


def _has(text: str, words) -> bool:
    return any(re.search(rf"\b{re.escape(w)}", text) for w in words)


def from_words(text: str) -> Want:
    """The fallback reading, from word lists, when the model cannot be asked."""
    low = text.lower()
    effect = next((e for e, ws in L["effect_words"].items() if _has(low, ws)), "")
    stat = next((s for s, ws in L["stat_words"].items() if _has(low, ws) or re.search(rf"\b{s}\b", low)), "")
    if _has(low, L["passive_words"]):
        kind = "passive"
    elif _has(low, L["active_words"]) or effect:
        kind = "active"
    else:
        kind = "either"
    if kind == "active" and stat and not effect:
        kind = "either"
    from engine import elements as EL
    return Want(kind, effect, stat if kind != "active" else "", text, EL.of_text(low))


def from_model(read, text: str) -> Want:
    """A LessonWant from the model, with anything the engine does not know dropped."""
    kind = read.kind if read.kind in ("active", "passive", "either") else "either"
    effect = read.effect.strip().lower()
    stat = read.stat.strip().lower()
    from engine import elements as EL
    el = getattr(read, "element", "") or ""
    return Want(kind, effect if effect in EFFECTS else "", stat if stat in STATS else "", text, el if el in EL.ELEMENTS else "")


# ---------- what the character already has ----------

def view(c) -> SimpleNamespace:
    """The character as the class-fit helpers expect to see a class."""
    return SimpleNamespace(
        custom_class=c.custom_class, combat_identity="", summary=getattr(c, "class_summary", ""), themes=[],
        families=FAMILIES_BY_ARCHETYPE.get(c.archetype.value, ["warrior"]), archetype=c.archetype, focus="balanced",
        uses_companions=c.uses_companions, summoner=getattr(c, "summoner", False), constraints=[], primary_attributes=list(c.primary_attributes),
        casting_attribute=getattr(c, "casting_attribute", ""), elements=list(getattr(c, "elements", []) or []))


def mana_share(c, rng) -> float:
    known = [a for a in c.actives]
    if known:
        return sum(a.resource.value == "mana" for a in known) / len(known)
    return AS.P["mana_share"].get(c.archetype.value, 0.0)


# ---------- the plan ----------

def kinds(want: Want, n: int, rng, can_active: bool, can_passive: bool) -> list[tuple[str, bool]]:
    """(type, leans toward the request) for each option."""
    if not can_passive:
        return [("active", i < n - 1) for i in range(n)]
    if not can_active:
        return [("passive", i < n - 1) for i in range(n)]
    nb = max(1, min(L["biased"], n - 1))
    if want.kind == "active":
        biased = ["active"] * nb
    elif want.kind == "passive":
        biased = ["passive"] * nb
    else:
        biased = [("active", "passive")[i % 2] for i in range(nb)]
    out = [(t, True) for t in biased]
    for _ in range(n - nb):
        if want.kind == "active":
            t = "passive" if rng.random() < L["wildcard_passive"] else "active"
        elif want.kind == "passive":
            t = "active"
        else:
            t = rng.choice(["active", "passive"])
        out.append((t, False))
    return out


def _tier(level: int, rng, attack: bool = False) -> str:
    if attack and level >= L["heavy_level"] and rng.random() < L["heavy_chance"]:
        return "heavy"
    if level >= L["moderate_level"] and rng.random() < L["moderate_chance"]:
        return "moderate"
    return "light"


def _pick(rng, ids: list[str], table: dict, view_) -> str:
    return rng.choices(ids, weights=[AT._score(table[i], view_) for i in ids])[0]


def _function_slot(s: dict, effect: str, offers: dict, want: Want, biased: bool, view_, rng, only=None) -> bool:
    fns = offers["functions"]
    if not fns or (only is not None and not only):
        return False

    def spec_of(fn):
        spec = dict(AS.P["function_defaults"])
        spec.update(AS.P["functions"].get(fn) or {})
        return spec
    ids = list(only) if only is not None else ([fn for fn in fns if spec_of(fn)["effect"] == effect] or list(fns))
    words = want.words() if biased else set()

    def weight(fn):
        text = (fn + " " + field.F["functions"][fn]["blurb"]).lower().replace("_", " ")
        return AT._score(field.F["functions"][fn], view_) * (3 if words & set(re.findall(r"[a-z]+", text)) else 1)
    fn = rng.choices(ids, weights=[weight(i) for i in ids])[0]
    fns.remove(fn)
    spec = spec_of(fn)
    s.update(effect=spec["effect"], tier=spec["tier"], reach=spec["reach"], context=spec["context"], field_use=fn)
    return True


def active_slot(c, view_, effect: str, offers: dict, want: Want, biased: bool, share: float, rng) -> dict:
    if effect == "defense":                         # no defense stances (f250): asked to be taught a guard, they learn a buff
        effect = "buff" if offers.get("buffs") else "damage"
    arch = c.archetype.value
    level = c.level
    s = AS._base()
    forbidden = AS.forbidden_reach(view_)
    if effect in ("utility", "influence"):
        if not _function_slot(s, effect, offers, want, biased, view_, rng):
            effect = "control"
    if effect == "summon" and not getattr(c, "summoner", False):
        effect = "damage"
    if effect == "control":
        fight_fns = [fn for fn in offers["functions"] if field.in_combat_function(fn)]
        named = want.words() & {w for fn in fight_fns for w in re.findall(r"[a-z]+", field.F["functions"][fn]["blurb"].lower())}
        if fight_fns and (named or rng.random() < L["fight_function_chance"]) and \
                _function_slot(s, "control", offers, want, biased, view_, rng, only=fight_fns):
            effect = "function"
    if effect == "function":
        pass
    elif effect in ("damage", "control"):
        s.update(effect=effect, context="combat")
        roll = rng.random()
        if effect == "damage":
            shapes = list(offers["shapes"])
            riders = [r for r in offers["riders"] if "damage" in AT.RIDERS[r]["applies"]]
            if shapes and roll < L["shape_chance"]:
                s["shape"] = _pick(rng, shapes, AT.SHAPES, view_)
                offers["shapes"].remove(s["shape"])
            elif riders and roll < L["shape_chance"] + L["rider_chance"]:
                s["rider"] = _pick(rng, riders, AT.RIDERS, view_)
                offers["riders"].remove(s["rider"])
        else:
            riders = [r for r in offers["riders"] if "control" in AT.RIDERS[r]["applies"]]
            if riders and rng.random() < 0.7:
                s["rider"] = _pick(rng, riders, AT.RIDERS, view_)
                offers["riders"].remove(s["rider"])
        AS._set_reach(s, rng, forbidden, AS.P["reach"][arch], allow_area=True)
        s["tier"] = _tier(level, rng, attack=True)
    elif effect == "mobility":
        owned = {a.movement for a in c.actives if getattr(a, "movement", "")}
        kinds = AS.pick_moves(view_.families, 1, rng, skip=owned)
        if kinds:
            from engine import movement as MVE
            s.update(effect="mobility", tier=MVE.M["tier"], reach="self", context="combat", movement=kinds[0])
        else:                                       # every everyday move is already known
            return active_slot(c, view_, "buff" if offers.get("buffs") else "damage", offers, want, biased, share, rng)
    elif effect == "healing":
        s.update(effect="healing", tier=_tier(level, rng), reach="self" if rng.random() < 0.5 else "extended", context="both")
    elif effect == "buff":
        if offers["buffs"]:
            b = _pick(rng, offers["buffs"], AT.BUFFS, view_)
            offers["buffs"].remove(b)
            s.update(effect="buff", tier="moderate", reach="self", context="combat", buff=b,     # one strength (f235)
                     resource="mana")                                    # every buff is magic (f238)
        else:
            return active_slot(c, view_, "damage", offers, want, biased, share, rng)
    elif effect == "summon":
        from engine import summons
        tier = rng.choice(["light", "moderate"]) if level >= L["moderate_level"] else "light"
        form = rng.choice(list(summons.FORMS))
        if tier not in summons.FORMS[form]["tiers"]:
            tier = summons.FORMS[form]["tiers"][0]
        s.update(effect="summon", tier=tier, reach="self", context="both" if form == "bound" else "combat", summon_form=form)
    elif effect == "crafting":
        s.update(effect="crafting", tier="light", reach="self", context="out_of_combat")
    if s["tier"] == "heavy" and level < L["heavy_level"]:
        s["tier"] = "moderate"
    if s["tier"] == "moderate" and level < L["moderate_level"]:
        s["tier"] = "light"
    s["resource"] = "mana" if (rng.random() < share or s["effect"] == "summon") else "stamina"
    s["type"] = "active"
    return s


def _wildcard_effect(c, rng, avoid: str) -> str:
    table = dict(L["wildcard_effects"])
    if not getattr(c, "summoner", False):
        table.pop("summon", None)
    if len(table) > 1:
        table.pop(avoid, None)
    return rng.choices(list(table), weights=list(table.values()))[0]


def _stat_triggers(stat_id: str, view_) -> list[str]:
    """The conditions that make sense for a stat: combat stats in a fight, the rest outside one."""
    from character import fit
    st = STATS[stat_id]
    if st.category == "pool":
        return ["always"]
    scores = fit.trigger_scores(view_)
    out = []
    for t in TRIGGERS.values():
        if scores.get(t.id, 0) <= fit.EXCLUDED + 5:
            continue
        if st.noncombat and t.context == "combat":
            continue
        if not st.noncombat and t.noncombat:
            continue
        if t.id not in L["common_triggers"] and scores.get(t.id, 0) < fit.FIT_THRESHOLD:
            continue
        out.append(t.id)
    return out or ["always"]


def _stat_candidates(c, view_, want: Want, biased: bool) -> list[str]:
    from character import fit
    scores = fit.stat_scores(view_)
    allowed = [s for s in STATS if scores.get(s, 0) > fit.EXCLUDED + 5 and STATS[s].category != "pool"]
    if biased:
        if want.stat and want.stat in STATS:
            return [want.stat] + [s for s in allowed if s != want.stat]
        named = [s for s in L["effect_stats"].get(want.effect, []) if s in allowed]
        if named:
            return named + [s for s in allowed if s not in named]
    best = fit.best_fits(scores, 12)
    best = [s for s in best if s in allowed]
    return best + [s for s in allowed if s not in best]


def passive_slot(c, view_, want: Want, biased: bool, index: int, taken: set, used_mech: set, rng, mechs: dict) -> dict | None:
    """A stat passive or a mechanic passive; None if nothing new is left to teach."""
    owned_stat = {(p.modifies.value if p.modifies else "", p.trigger.value if p.trigger else "") for p in c.passives if not p.mechanic}
    owned_mech = {p.mechanic for p in c.passives if p.mechanic} | used_mech
    tier = "moderate" if c.level >= L["moderate_level"] and rng.random() < L["moderate_chance"] else "light"
    mech_first = (biased and not want.stat and not L["effect_stats"].get(want.effect) and index % 2 == 1) or \
                 (not biased and rng.random() < 0.5)
    order = ["mechanic", "stat"] if mech_first else ["stat", "mechanic"]
    for kind in order:
        if kind == "mechanic":
            pool = [(oid, o) for oid, o in mechs.items() if o.mechanic not in owned_mech]
            if pool:
                oid, o = rng.choice(pool)
                used_mech.add(o.mechanic)
                return {"type": "passive", "kind": "mechanic", "tier": tier, "mechanic": oid, "option": o,
                        "modifies": "", "trigger": ""}
        else:
            cands = _stat_candidates(c, view_, want, biased)
            from character import fit
            tscores = fit.trigger_scores(view_)
            for stat in cands:
                trigs = [t for t in _stat_triggers(stat, view_) if (stat, t) not in owned_stat and (stat, t) not in taken]
                if not trigs:
                    continue
                trig = rng.choices(trigs, weights=[(3 if t == "always" else 1) + max(0, tscores.get(t, 0)) for t in trigs])[0]
                taken.add((stat, trig))
                return {"type": "passive", "kind": "stat", "tier": tier, "modifies": stat, "trigger": trig,
                        "mechanic": "", "option": None}
    return None


def plan(c, want: Want, rng: random.Random | None = None, n: int | None = None, can_active: bool = True,
         can_passive: bool = True) -> list[dict]:
    """The lessons on offer (dicts), each complete except for its name and description."""
    rng = rng or random.SystemRandom()
    n = n or T["abilities"]["options"]
    view_ = view(c)
    types = kinds(want, n, rng, can_active, can_passive)
    have = {x for x in ([a.rider for a in c.actives] + [a.shape for a in c.actives]) if x}
    owned_fn = {a.field_use for a in c.actives if a.field_use}
    owned_buffs = {a.buff for a in c.actives if a.buff}
    offers = AT.draw_offers(view_, rng, sizes={"riders": 3, "shapes": 2, "buffs": 2, "functions": 3}, skip=have, owned_functions=owned_fn,
                            level=c.level, lesson=True)
    offers["buffs"] = [b for b in offers["buffs"] if b not in owned_buffs]
    mechs = {}
    if any(t == "passive" for t, _ in types):
        from character.creation import draw_mechanics
        mechs = draw_mechanics(view_, rng, where="taught")    # the world teaches the plainer fare; perks are creation's
    share = mana_share(c, rng)
    slots, taken, used_mech = [], set(), set()
    used_effects = set()
    for i, (typ, biased) in enumerate(types):
        if typ == "active":
            if biased:
                effect = want.effect or _wildcard_effect(c, rng, "")
                if effect in used_effects and want.effect:
                    effect = want.effect          # the request is the request: several options may share it
            else:
                effect = _wildcard_effect(c, rng, want.effect)
            s = active_slot(c, view_, effect, offers, want, biased, share, rng)
            used_effects.add(s["effect"])
        else:
            s = passive_slot(c, view_, want, biased, i, taken, used_mech, rng, mechs)
            if s is None and can_active:
                s = active_slot(c, view_, _wildcard_effect(c, rng, want.effect), offers, want, False, share, rng)
            if s is None:
                continue
        s["biased"] = biased
        slots.append(s)
    # elements are the engine's: the class's palette (or its families' lean); a lesson answering a request that named an element carries it
    AS.assign_elements(slots, view_.elements, view_.families, rng)
    for s in slots:
        if want.element and s["biased"] and AS.elemental(s):
            s["element"] = want.element
    AS.buff_resources(slots)
    AS.split_poison_imbue(slots, offers)
    AS.assign_expressions(slots, rng)                     # what each element does, and each damage spell's form (engine/spellcraft.py)
    from engine import spells
    for s in slots:
        s["rank"] = spells.highest_rank(c.level)          # (f397) a teacher teaches a new spell at the rank the level allows
    AS.assign_forms(slots, rng)
    AS.assign_martial(slots, list(view_.families or []), rng)   # a technique's form and maneuver (engine/martial.py)
    rng.shuffle(slots)
    for k, s in enumerate(slots, 1):
        s["n"] = k
    return slots


# ---------- what the model is told ----------

def passive_of(s: dict, name: str = "x", description: str = "x"):
    """The Passive this slot becomes (also used to show the model what it does)."""
    from engine.abilities import materialize_passive
    from llm.contracts import PassiveProposal
    offered = {s["mechanic"]: s["option"]} if s["kind"] == "mechanic" else None
    p = PassiveProposal(name=name, description=description, kind=s["kind"], modifies=s["modifies"] or None,
                        trigger=s["trigger"] or None, mechanic=s["mechanic"], tier=s["tier"])
    return materialize_passive(p, offered)


def slot_line(s: dict) -> str:
    if s["type"] == "active":
        return AS.slot_line(s)
    does = passive_of(s).effect_text()
    return (f"{s['n']}. PASSIVE TRAIT - {s['tier']}\n     does: {does}\n"
            "     write it as: a quality, instinct or piece of training the character has - NOT an action they perform")


def slot_lines(slots: list[dict]) -> str:
    return "\n".join(slot_line(s) for s in slots)


# ---------- turning the model's words into the real thing ----------

def build(slots: list[dict], names) -> list:
    """Abilities and Passives, in slot order, from the plan and the model's names and descriptions."""
    from engine.abilities import materialize_active
    from llm.contracts import ActiveProposal
    by_n = {x.slot: x for x in names.skills}
    out = []
    for s in sorted(slots, key=lambda s: s["n"]):
        x = by_n[s["n"]]
        if s["type"] == "passive":
            out.append(passive_of(s, x.name, x.description))
            continue
        out.append(materialize_active(ActiveProposal(
            name=x.name, description=x.description, effect=s["effect"], tier=s["tier"], reach=s["reach"], resource=s["resource"],
            context=s["context"], summons=x.summons if s["effect"] == "summon" else None, rider=s["rider"], shape=s["shape"],
            buff=s["buff"], buff_stat=s["buff_stat"], command=s["command"], field_use=s["field_use"], channel=bool(s.get("channel")),
            movement=s.get("movement", ""), heal_form=s.get("heal_form", ""), element=s.get("element", ""),
            summon_form=s.get("summon_form", ""), expressions=list(s.get("expressions") or []), spell_form=s.get("spell_form", ""),
            power=s.get("power", 0), cost_percent=s.get("cost_percent", 0), cast_turns=s.get("cast_turns", 0),
            martial_form=s.get("martial_form", ""), hits=s.get("hits", 0), maneuver=s.get("maneuver", ""), rank=int(s.get("rank") or 0))))
    return out
