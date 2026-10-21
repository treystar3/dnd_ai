"""Slot-based creation of a class's 15 starting actives.

The engine plans every slot first - its effect, tier, reach, resource, context and its rider, shape, buff, command or world
function - and the model is only asked to NAME and DESCRIBE each one. So an ability can no longer be described as one thing and
do another: the words are written for a mechanic that already exists (data/rules/ability_slots.yaml)."""

import collections
import random
from pathlib import Path

import yaml

from engine import ability_traits as AT
from engine import field

ROOT = Path(__file__).resolve().parent.parent
P = yaml.safe_load((ROOT / "data" / "rules" / "ability_slots.yaml").read_text(encoding="utf-8"))
COMBAT_EFFECTS = ("damage", "control", "defense", "mobility")
STRICT_MULTI = ("volley", "barrage", "flurry", "salvo", "hail of", "rain of", "series of", "sequence", "several", "multiple", "twin",
                "pair of", "dual", "double", "triple", "fusillade", "succession", "missiles", "rapid-fire", "rapid fire",
                "rapid strikes", "rapid thrusts", "rapid blows", "rapid stabs")
PLURAL_HITS = ("strikes", "thrusts", "slashes", "shots", "stabs", "blows", "hits", "bolts", "darts", "arrows", "knives", "punches",
               "kicks", "fireballs", "shards", "volleys", "jabs", "cuts")
SINGLE_HIT_OK = ("chain", "sweeping", "ricochet", "packhunt", "cleave")      # shapes whose ability may well read as striking several foes


# ---------- the plan ----------

def forbidden_reach(interp) -> set[str]:
    """Reaches the class's constraints rule out ("avoids melee", "never uses ranged attacks")."""
    out = set()
    for c in getattr(interp, "constraints", []) or []:
        c = c.lower()
        negative = any(w in c for w in ("avoid", "no ", "never", "not ", "without", "refuse", "won't", "cannot", "can't", "dislike"))
        if not negative:
            continue
        if "melee" in c or "close" in c or "hand-to-hand" in c:
            out |= {"melee", "extended"}
        if "ranged" in c or "range " in c or "distance" in c:
            out |= {"ranged"}
    return out


def _weighted(rng, table: dict, forbidden=(), allowed=None) -> str | None:
    opts = {k: w for k, w in table.items() if k not in forbidden and (allowed is None or k in allowed)}
    if not opts:
        return None
    return rng.choices(list(opts), weights=list(opts.values()))[0]


def _largest_remainder(total: int, weights: dict) -> dict:
    s = sum(weights.values()) or 1
    raw = {k: total * w / s for k, w in weights.items()}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: total - sum(out.values())]:
        out[k] += 1
    return out


def _base() -> dict:
    return {"effect": "", "tier": "light", "reach": "self", "resource": "stamina", "context": "combat", "rider": "", "shape": "",
            "buff": "", "buff_stat": "", "command": "", "field_use": "", "channel": False, "movement": "", "heal_form": "", "element": "",
            "expressions": [], "spell_form": "", "power": 0, "cost_percent": 0, "cast_turns": 0,
            "martial_form": "", "hits": 0, "maneuver": "",
            "summon_form": ""}


def _counts(interp, offers, minimum, buffs, commands, summons, healing, crafting) -> dict:
    selfish = healing + min(summons, 1) + crafting      # of the summons only the Bound one does anything outside a fight
    functions = min(len(offers.get("functions", [])), max(0, minimum - selfish))
    fixed = buffs + commands + summons + healing + crafting + functions
    return {"functions": functions, "remaining": P["total"] - fixed}


def _needed_riders_shapes(offers) -> int:
    return min(AT.T["need"]["riders"], len(offers["riders"])) + min(AT.T["need"]["shapes"], len(offers["shapes"]))


def plan(interp, offers: dict, minimum: int, rng: random.Random | None = None) -> list[dict]:
    """The 15 slots (dicts) for one new character. Each is complete except for its name and description."""
    rng = rng or random.SystemRandom()
    total = P["total"]
    arch = interp.archetype.value
    fams = set(interp.families or [])
    comp = bool(getattr(interp, "uses_companions", False))          # keeps companions: tamed, living
    summ = bool(getattr(interp, "summoner", False))                   # makes summons with magic
    focus = interp.focus

    summons = 1 + rng.choice([1, 2]) if summ else 0                   # its one Bound summon, and one or two made in the fight
    commands = min(len(offers.get("commands", [])), rng.choice([2, 2, 3])) if (comp or summ) else 0
    healing = 2 if arch == "support" else (1 if fams & {"healer", "paladin", "druid"} else 0)
    crafting = 2 if "artisan" in fams else 0
    buffs = min(len(offers["buffs"]), 1 if focus == "social" else 2)
    needed_dc = _needed_riders_shapes(offers)
    # make room for the combat abilities that carry riders and shapes
    for field_name, floor in (("buffs", 1), ("commands", 2), ("crafting", 0), ("summons", 2), ("commands", 1), ("summons", 1), ("healing", 1 if arch == "support" else 0)):
        while True:
            c = _counts(interp, offers, minimum, buffs, commands, summons, healing, crafting)
            if c["remaining"] >= needed_dc:
                break
            cur = locals()[field_name]
            if cur <= floor:
                break
            if field_name == "buffs":
                buffs -= 1
            elif field_name == "commands":
                commands -= 1
            elif field_name == "summons":
                summons -= 1
            elif field_name == "crafting":
                crafting -= 1
            else:
                healing -= 1
    c = _counts(interp, offers, minimum, buffs, commands, summons, healing, crafting)
    n_functions, remaining = c["functions"], c["remaining"]
    from engine import movement as _MV
    signatures = _MV.signatures_for(fams, bool(getattr(interp, "summoner", False)))
    signature = rng.choice(signatures) if signatures and remaining > needed_dc else ""
    if signature:
        remaining -= 1                                   # a class whose family has a signature move keeps one slot for it

    slots: list[dict] = []

    def add(**kw):
        s = _base()
        s.update(kw)
        slots.append(s)

    # ---- the fixed kinds ----
    import yaml as _ys
    SF = _ys.safe_load((ROOT / "data" / "rules" / "summons.yaml").read_text(encoding="utf-8"))["forms"]
    made_forms = rng.sample([f for f in SF if f != "bound"], max(0, summons - 1))
    for i in range(summons):
        if i == 0:
            add(effect="summon", tier=SF["bound"]["tiers"][0], reach="self", context="both", summon_form="bound")
        else:
            form = made_forms[i - 1]
            add(effect="summon", tier=rng.choice(SF[form]["tiers"]), reach="self", context="combat", summon_form=form)
    cmds = rng.sample(offers.get("commands", []), commands) if commands else []
    for cm in cmds:
        add(effect="command", tier="light", reach="self", context="combat", command=cm)
    import yaml as _yh
    HF = _yh.safe_load((ROOT / "data" / "rules" / "healing.yaml").read_text(encoding="utf-8"))["forms"]
    used_forms: list[str] = []
    for i in range(healing):
        tier = "light" if i == 0 else rng.choice(["moderate", "moderate", "heavy"])
        fits = [f for f, v in HF.items() if tier in v["tiers"] and f not in used_forms] or [f for f, v in HF.items() if tier in v["tiers"]]
        form = "mend" if i == 0 and "mend" in fits and rng.random() < 0.5 else rng.choice(fits)
        used_forms.append(form)
        add(effect="healing", tier=tier, reach="extended", context="both", heal_form=form)   # a heal reaches one ally or yourself
    for i in range(crafting):
        add(effect="crafting", tier="light", reach="self", context="out_of_combat")
    if signature:
        add(effect="mobility", tier=_MV.M["tier"], reach="self", context="combat", movement=signature)
    chosen_buffs = _pick_buffs(interp, offers["buffs"], buffs, rng)
    for b in chosen_buffs:
        if b not in offers["buffs"]:
            offers["buffs"].append(b)                   # a guaranteed Imbue is on offer, so the validator accepts it (f252)
    for b in chosen_buffs:
        add(effect="buff", tier="moderate", reach="self", context="combat", buff=b)      # a buff has one strength (f235)
    for fn in _pick_functions(interp, offers.get("functions", []), n_functions, rng):
        spec = dict(P["function_defaults"])
        spec.update(P["functions"].get(fn) or {})
        add(effect=spec["effect"], tier=spec["tier"], reach=spec["reach"], context=spec["context"], field_use=fn)

    # ---- the combat remainder ----
    weights = dict(P["mix"][focus])
    if comp or summ:
        weights["damage"] *= P["companion_damage_scale"]
    counts = _largest_remainder(remaining, weights)
    shortfall = max(0, P["min_damage"] - counts["damage"])
    for _ in range(min(shortfall, remaining)):
        donor = max((k for k in counts if k != "damage"), key=lambda k: counts[k])
        if counts[donor] > 0:
            counts[donor] -= 1
            counts["damage"] += 1
    forbidden = forbidden_reach(interp)
    usable_r, usable_s = _usable(offers, forbidden)
    ctl_riders = sum("control" in AT.RIDERS[r]["applies"] for r in usable_r)
    want_s, want_r = min(AT.T["need"]["shapes"], len(usable_s)), min(AT.T["need"]["riders"], len(usable_r))
    # enough damage abilities that the required shapes (damage only) and riders (damage, or the few that work on control) all have a home
    while counts["damage"] < want_s + max(0, want_r - min(counts["control"], ctl_riders)) and counts["damage"] < remaining:
        donor = max(("defense", "mobility", "control"), key=lambda k: counts[k] if (k != "control" or counts[k] > 1) else -1)
        if counts[donor] <= 0:
            break
        counts[donor] -= 1
        counts["damage"] += 1
    base_reach = P["reach"][arch]
    dmg = [dict(_base(), effect="damage") for _ in range(counts["damage"])]
    ctl = [dict(_base(), effect="control") for _ in range(counts["control"])]
    for _ in range(counts["defense"]):
        add(effect="defense", tier="light", reach="self", context="combat")
    # movement (engine/movement.py): the everyday moves by family lean, and one signature for a class whose family has one
    from engine import movement as MVE
    for kind in pick_moves(fams, counts["mobility"], rng):
        add(effect="mobility", tier=MVE.M["tier"], reach="self", context="combat", movement=kind)
    for _ in range(max(0, counts["mobility"] - len(MVE.EVERYDAY))):
        dmg.append(dict(_base(), effect="damage"))       # more movement than there are everyday moves: the rest fight
    _assign_traits(dmg, ctl, offers, interp, rng, forbidden, base_reach)
    slots += dmg + ctl

    # heavy and moderate tiers go to the combat attacks
    attacks = dmg + ctl
    heavy = min(max(0, P["heavy"][focus] - sum(1 for s in slots if s["tier"] == "heavy")), len(attacks))
    order = attacks[:]
    rng.shuffle(order)
    for s in order[:heavy]:
        s["tier"] = "heavy"
    for s in order[heavy:]:
        s["tier"] = "moderate" if rng.random() < P["moderate_chance"] else "light"
    for s in slots:
        if s["effect"] == "defense" and rng.random() < 0.25:
            s["tier"] = "moderate"

    _assign_resources(slots, interp, arch, fams, rng)
    buff_resources(slots)
    for s in slots:
        if s["effect"] == "summon":
            s["resource"] = "mana"                       # a summon is made out of magic
    _assign_channel(slots, interp, fams, rng)
    assign_elements(slots, list(getattr(interp, "elements", []) or []), list(interp.families or []), rng)
    split_poison_imbue(slots, offers)
    assign_expressions(slots, rng)
    assign_forms(slots, rng)
    assign_martial(slots, list(interp.families or []), rng)
    rng.shuffle(slots)
    for n, s in enumerate(slots, 1):
        s["n"] = n
    return slots


def buff_resources(slots: list[dict]) -> None:
    """Every buff is magic (f238): it costs mana, whatever the class's habits - every character has some mana - and has one strength."""
    for s in slots:
        if s.get("effect") == "buff" or s.get("field_use") == "pass_without_trace":
            s["resource"] = "mana"                                 # buffs, in a fight or out of one, are magic
        if s.get("effect") == "buff":
            s["tier"] = "moderate"


def _pick_buffs(interp, offered, n, rng) -> list[str]:
    close = sum(v for k, v in P["reach"][interp.archetype.value].items() if k in ("melee", "extended"))
    palette = set(getattr(interp, "elements", None) or [])
    def fits(b):
        B = AT.BUFFS[b]
        return not (B.get("no_melee") and close > 0.5) \
            and not (palette and B.get("element") and B["element"] not in palette) \
            and not (B.get("weapon") and not fighter(interp))    # (f251, f252, f267) Bladeward is no warrior's; a caster swings no blade
    ids = [b for b in offered if fits(b)]
    if len(ids) < n:                                   # too few of the offered suit it: the rest come from every buff that does
        spare = [b for b in AT.BUFFS if fits(b) and b not in ids]
        ids += rng.sample(spare, min(len(spare), n - len(ids)))
    if palette and fighter(interp) and n > 0:     # an element in the weapon: Imbue of it is always one (f252; fighters only, f260)
        rest = _pick_buffs_from([b for b in ids if b != "imbue"], interp, n - 1, rng)
        return ["imbue"] + rest
    return _pick_buffs_from(ids, interp, n, rng)


def _pick_buffs_from(ids, interp, n, rng) -> list[str]:
    ids = list(ids)
    out = []
    while ids and len(out) < n:
        pick = rng.choices(ids, weights=[AT._score(AT.BUFFS[i], interp) for i in ids])[0]
        out.append(pick)
        ids.remove(pick)
    return out


def _pick_functions(interp, offered, n, rng) -> list[str]:
    ids = list(offered)
    out = []
    while ids and len(out) < n:
        pick = rng.choices(ids, weights=[AT._score(field.F["functions"][i], interp) for i in ids])[0]
        out.append(pick)
        ids.remove(pick)
    return out


def _trait_reach(*traits) -> set | None:
    allowed = None
    for t in traits:
        if t and t.get("reach"):
            allowed = set(t["reach"]) if allowed is None else allowed & set(t["reach"])
    return allowed


def _set_reach(s, rng, forbidden, base_reach, allow_area=True):
    shape = AT.SHAPES.get(s["shape"]) if s["shape"] else None
    rider = AT.RIDERS.get(s["rider"]) if s["rider"] else None
    allowed = _trait_reach(shape, rider)
    table = {k: w for k, w in base_reach.items() if allow_area or k != "area"}
    if shape:
        table.pop("area", None)
    pick = _weighted(rng, table, forbidden, allowed)
    if pick is None:                                      # the class's habits leave nothing the trait allows: take what it allows
        pool = [r for r in (allowed or ["melee", "extended", "ranged", "area"]) if r not in forbidden and not (shape and r == "area")]
        pool = pool or [r for r in ("ranged", "area", "melee", "extended") if r not in forbidden and not (shape and r == "area")]
        pick = rng.choice(pool or ["ranged"])
    s["reach"] = pick


def _usable(offers, forbidden) -> tuple[list, list]:
    """The offered riders and shapes this class can use: a trait that needs a reach the class refuses is left out."""
    def ok(t):
        return not t.get("reach") or bool(set(t["reach"]) - set(forbidden))
    return ([r for r in offers["riders"] if ok(AT.RIDERS[r])], [x for x in offers["shapes"] if ok(AT.SHAPES[x])])


def _assign_traits(dmg, ctl, offers, interp, rng, forbidden, base_reach):
    need = AT.T["need"]
    cap = AT.T["max_decorated"]
    riders, shapes = _usable(offers, forbidden)
    ctl_ok = [r for r in riders if "control" in AT.RIDERS[r]["applies"]]
    need_r = min(need["riders"], len(riders))
    # shapes take damage abilities; leave enough free damage abilities and control abilities for the riders
    ns_cap = max(0, len(dmg) - max(0, need_r - min(len(ctl), len(ctl_ok))))
    ns = min(len(shapes), ns_cap, rng.randint(need["shapes"], need["shapes"] + 1))
    chosen_shapes, pool = [], shapes[:]
    while pool and len(chosen_shapes) < ns:
        pick = rng.choices(pool, weights=[AT._score(AT.SHAPES[i], interp) for i in pool])[0]
        chosen_shapes.append(pick)
        pool.remove(pick)
    rng.shuffle(dmg)
    for s, sh in zip(dmg, chosen_shapes):
        s["shape"] = sh
    free = [s for s in dmg if not s["shape"]]
    capacity = min(len(free) + min(len(ctl), len(ctl_ok)), cap - len(chosen_shapes))
    nr = min(len(riders), capacity, max(need["riders"], rng.randint(need["riders"], need["riders"] + 2)))
    chosen = []
    ctl_pool = ctl_ok[:]
    # a control ability takes a rider that works on control; the rest go to plain damage abilities
    n_ctl = min(len(ctl), len(ctl_pool), nr)                      # every control ability that can carry a rider does
    for s in ctl[:n_ctl]:
        pick = rng.choices(ctl_pool, weights=[AT._score(AT.RIDERS[i], interp) for i in ctl_pool])[0]
        s["rider"] = pick
        chosen.append(pick)
        ctl_pool.remove(pick)
        riders.remove(pick)
    for s in free:
        if len(chosen) >= nr or not riders:
            break
        pick = rng.choices(riders, weights=[AT._score(AT.RIDERS[i], interp) for i in riders])[0]
        s["rider"] = pick
        chosen.append(pick)
        riders.remove(pick)
    for s in dmg + ctl:
        _set_reach(s, rng, forbidden, base_reach, allow_area=True)


def fighter(interp) -> bool:
    return interp.archetype.value in ("warrior", "rogue")


def mixed(interp) -> bool:
    """A weapon class with magic of its own: a hybrid family, or a fighter that also draws on a casting family (f252)."""
    fams = set(interp.families or [])
    return bool(fams & set(P["hybrid_families"])) or (fighter(interp) and bool(fams & set(P["caster_families"])))


def _assign_resources(slots, interp, arch, fams, rng):
    share = P["mana_share"][arch]
    for fam, v in P["hybrid_families"].items():
        if fam in fams and share < v:
            share = v
    if mixed(interp) and fighter(interp):
        share = max(share, P["mixed_share"])
    magical = {"healing": 0, "summon": 1, "command": 2, "control": 3, "influence": 4, "buff": 5, "damage": 6, "utility": 7,
               "defense": 8, "mobility": 9, "crafting": 10}
    ranked = sorted(slots, key=lambda s: (magical.get(s["effect"], 9), rng.random()))
    n_mana = round(share * len(slots))
    for i, s in enumerate(ranked):
        s["resource"] = "mana" if i < n_mana else "stamina"


def _channel_reach(s, forbidden=()) -> list[str]:
    """The melee reaches this attack could take, given what its shape and rider allow."""
    allowed = _trait_reach(AT.SHAPES.get(s["shape"]) if s["shape"] else None, AT.RIDERS.get(s["rider"]) if s["rider"] else None)
    return [r for r in ("melee", "extended") if (allowed is None or r in allowed) and r not in forbidden]


def _assign_channel(slots, interp, fams, rng):
    """Some single-target attacks become channeled: mana struck through the weapon, at melee or extended reach."""
    C = P["channel"]
    if not fighter(interp) or getattr(interp, "uses_companions", False):
        return                                  # (f260) a channeled strike needs a melee weapon: casters carry a focus, tamers a companion
    banned = forbidden_reach(interp)
    able = [s for s in slots if s["effect"] == "damage" and s["reach"] != "area" and _channel_reach(s, banned)]
    hybrid = mixed(interp)
    if hybrid:
        pool = [s for s in able if s["resource"] == "mana"]
        chosen = [s for s in pool if rng.random() < C["hybrid_chance"]]
        if not chosen and able:
            chosen = [rng.choice(pool or able)]
        if fighter(interp) and getattr(interp, "elements", None):        # a fighter with an element strikes with it (f252)
            want = rng.choice(P["element_channel"])
            spare = [s for s in able if s not in chosen]
            chosen += rng.sample(spare, max(0, min(len(spare), want - len(chosen))))
    elif fighter(interp) and getattr(interp, "elements", None) and able:     # a fighter with an element strikes with it (f252)
        chosen = rng.sample(able, min(len(able), rng.choice(P["element_channel"])))
    else:
        chosen = [rng.choice(able)] if able and rng.random() < C["other_chance"] else []
    for s in chosen:
        reaches = _channel_reach(s, banned)
        if s["reach"] not in reaches:
            s["reach"] = rng.choice(reaches)
        s["resource"] = "mana"
        s["channel"] = True


def elemental(s: dict) -> bool:
    """Whether a planned ability carries an element: magic that strikes or binds, a channeled blow, or a weapon wreathed in an element."""
    return bool(s.get("channel")) or (s.get("resource") == "mana" and s.get("effect") in ("damage", "control", "summon")) or \
        (s.get("effect") == "buff" and s.get("buff") in ("imbue", "attunement"))


def assign_elements(slots: list[dict], palette: list[str], families: list[str], rng: random.Random) -> None:
    """The engine sets every elemental ability's element. A concept that named its magic draws only from that palette; otherwise the
    class's families lean the draw, and a share carry no element at all (data/rules/elements.yaml)."""
    from engine import elements as EL
    lean = [e for f in families for e in EL.R["family_lean"].get(f, [])]
    for s in slots:
        if not elemental(s):
            s["element"] = ""
        elif palette:
            s["element"] = rng.choice(palette)
        elif s.get("effect") != "buff" and rng.random() < EL.R["unaligned"]:     # an elemental weapon always has its element
            s["element"] = ""
        else:
            s["element"] = rng.choice(lean or EL.ELEMENTS)


COATINGS = {"poison": "envenom", "acid": "acidcoat"}


def split_poison_imbue(slots: list[dict], offers: dict | None = None) -> None:
    """Poison and acid are not Imbue's elements (f242): they are coatings put on a weapon - Envenom Weapon and Acid Coating - which add
    no damage of their own. An Imbue planned with one becomes that coating (or, if the class already has it, takes fire instead)."""
    for s in slots:
        coat = COATINGS.get(s.get("element", "")) if s.get("effect") == "buff" and s.get("buff") == "imbue" else None
        if not coat:
            continue
        if any(o.get("buff") == coat for o in slots if o is not s):
            s["element"] = "fire"
        else:
            s["buff"], s["element"], s["expressions"] = coat, "", []
            if offers is not None and coat not in offers.get("buffs", []):
                offers["buffs"] = list(offers.get("buffs", [])) + [coat]


def assign_expressions(slots: list[dict], rng: random.Random) -> None:
    """An elemental ability expresses its element (data/rules/spellcraft.yaml): a damage expression on a strike or a wreathed weapon,
    a control expression for a binding spell, which then deals no damage. The expression takes the place of a generic rider."""
    from engine import spellcraft as SC, elements as EL
    for s in slots:
        s["expressions"] = []
        el = s.get("element")
        if not el:
            continue
        kind = "control" if s.get("effect", "") == "control" else \
            "damage" if s.get("effect", "") == "damage" or (s.get("effect", "") == "buff" and s.get("buff") == "imbue") else ""
        if not kind:
            continue
        pool = SC.of_element(el, kind)
        near = [e for n in EL.neighbors(el) for e in SC.of_element(n, kind)]       # the wheel (f266): what its neighbors do
        if near and rng.random() < EL.BORROW:
            pool = near                                    # a borrowed effect: the damage stays this element's own
        if kind == "control":
            taken = {e for x in slots if x is not s and x.get("effect") == "control" for e in (x.get("expressions") or [])}
            if not [e for e in pool if e not in taken]:
                pool = [e for e in SC.of_element(el, "control") + near if e not in taken]   # a control spell of its own or a neighbor's left
            if not pool:                                   # (f263) nothing left to bind with: it becomes an attack
                s["effect"] = "damage"
                pool = SC.of_element(el, "damage")
        if pool:
            kind = s.get("effect", "")                     # spells of one kind share the element's effects out evenly (f252, f263, f265)
            used = collections.Counter(e for x in slots if x is not s and x.get("effect") == kind for e in (x.get("expressions") or []))
            least = min(used.get(e, 0) for e in pool)
            pool = [e for e in pool if used.get(e, 0) == least]
            s["expressions"] = [rng.choice(pool)]          # one today; a world-taught ability may carry several
            if s.get("effect", "") in ("damage", "control") and s.get("rider", ""):
                _rehome_rider(slots, s.get("rider", ""))
                s["rider"] = ""
            if s.get("effect", "") == "control" and SC.is_control(s["expressions"][0]) and s.get("reach", "") in ("self",):
                s["reach"] = "ranged"


def assign_martial(slots: list[dict], families: list[str], rng: random.Random) -> None:
    """A technique (a stamina ability that is not channeled) gets its form - strike, sweep, flurry, windup or counter - and most get a
    maneuver in place of a chance rider; a martial control ability is one maneuver, contested (data/rules/martial.yaml)."""
    from engine import martial as MA
    most = MA.most_hits(families)

    def fitting(ids, s):                                       # a maneuver only at the reaches it makes sense at (f251)
        return [k for k in ids if not MA.MANEUVERS[k].get("reach") or s.get("reach") in MA.MANEUVERS[k]["reach"]] or list(ids)
    can_control = [k for k, m in MA.MANEUVERS.items() if m.get("control")]
    for s in slots:
        s["martial_form"], s["hits"], s["maneuver"] = "", 0, ""
        if s.get("resource") != "stamina" or s.get("channel"):
            continue
        eff = s.get("effect", "")
        if eff == "control":
            s["maneuver"] = rng.choice(fitting(can_control, s))
            s["rider"] = ""
            continue
        if eff != "damage":
            continue
        sh = s.get("shape", "")
        if sh == "chain":                                      # a technique does not arc like lightning (f251): a blade cleaves, a shot ricochets
            want = "cleave" if s.get("reach") in ("melee", "extended") else "ricochet"
            used = {x.get("shape") for x in slots if x is not s}
            spare = [k for k, v in AT.SHAPES.items() if k not in used and not v.get("parts") and k not in ("chain", "sweeping")
                     and (not v.get("reach") or s.get("reach") in v["reach"])]
            sh = s["shape"] = want if want not in used else (rng.choice(spare) if spare else "")
        parts = (AT.SHAPES.get(sh) or {}).get("parts")
        if parts:                                              # an old multi-hit shape becomes a flurry of that many
            s["martial_form"], s["hits"], s["shape"] = "flurry", max(2, min(most, int(parts))), ""
        elif sh == "sweeping":
            s["martial_form"], s["shape"] = "sweep", ""
        elif sh:
            s["martial_form"] = "strike"                        # a shape stays on a strike
        elif s.get("reach") == "area":
            s["martial_form"] = "sweep"                        # a technique's "area" is everyone around you
        else:
            w = dict(MA.M["form_weights"])
            if s.get("reach") not in ("melee", "extended"):
                w.pop("sweep", None)
                w.pop("counter", None)                         # a counter waits for someone engaged with you (f251)
            s["martial_form"] = _weighted(rng, w) or "strike"
            if s["martial_form"] == "flurry":
                s["hits"] = rng.randint(2, most)
        if s["martial_form"] == "sweep" and s.get("reach") == "area":
            s["reach"] = "melee"
        if rng.random() < MA.M["maneuver_share"]:
            s["maneuver"] = rng.choice(fitting(list(MA.MANEUVERS), s))
            s["rider"] = ""
        elif s.get("rider"):
            s["rider"] = ""                                    # techniques carry maneuvers, not chance riders
    need = AT.T["need"]["riders"]                              # as many abilities do something besides damage as riders once guaranteed
    done = sum(1 for s in slots if s.get("effect") in ("damage", "control") and (s.get("rider") or s.get("expressions") or s.get("maneuver")))
    for s in slots:
        if done >= need:
            break
        if s.get("effect") == "damage" and s.get("martial_form") and not s.get("maneuver"):
            s["maneuver"] = rng.choice(fitting(list(MA.MANEUVERS), s))
            done += 1


def _rehome_rider(slots: list[dict], rider: str) -> None:
    """A rider displaced by an element's expression moves to a plain ability without an element that can carry it, if there is one."""
    r = AT.RIDERS[rider]
    if any(x.get("rider", "") == rider and not x.get("expressions") for x in slots if x is not None):
        return
    for x in slots:
        if x.get("element") or x.get("rider", "") or x.get("shape", "") or x.get("effect", "") not in r["applies"]:
            continue
        if r.get("reach") and x.get("reach", "") not in r["reach"]:
            continue
        x["rider"] = rider
        return


def assign_forms(slots: list[dict], rng: random.Random) -> None:
    """A mana damage spell (not a channeled strike) gets its form: bolt, blast, burst, curse or charged (data/rules/spellcraft.yaml)."""
    from engine import spellcraft as SC
    W = SC.S["form_weights"]
    for s in slots:
        s["spell_form"] = ""
        if s.get("effect", "") != "damage" or s.get("resource", "") != "mana" or s.get("channel"):
            continue
        if s.get("reach", "") == "area":
            s["spell_form"] = _weighted(rng, W["area"]) or "blast"
        elif s.get("shape", ""):
            s["spell_form"] = "bolt"
        else:
            s["spell_form"] = _weighted(rng, W["single"], forbidden=("curse",) if s.get("rider", "") else ()) or "bolt"


# ---------- what the model is told ----------

def pick_moves(families, n: int, rng: random.Random, skip=()) -> list[str]:
    """Up to n different everyday movement abilities, leaning toward the ones the class's families favor."""
    from engine import movement as MVE
    fams = set(families or [])
    pool = [k for k in MVE.EVERYDAY if k not in skip]
    out = []
    while pool and len(out) < n:
        w = [1 + 2 * len(fams & set(MVE.KINDS[k].get("fits", []))) for k in pool]
        k = rng.choices(pool, weights=w)[0]
        out.append(k)
        pool.remove(k)
    return out


def mechanic_text(s: dict) -> str:
    """What this slot does, in the words the model needs to write for it."""
    E = P["effects"]
    eff = s["effect"]
    parts = []
    if eff == "mobility" and s.get("movement"):
        from engine import movement as MVE
        parts.append(f"{MVE.KINDS[s['movement']]['depict']} - only movement: it deals no damage and does nothing to anyone")
    if s.get("element"):
        parts.append(f"it is {s['element']} - name and describe it as {s['element']}, and as nothing else")
    elif elemental(s) or eff == "damage":
        parts.append("it carries no element: plain " + ("force" if s.get("resource") == "mana" else "steel, muscle and skill")
                     + " - do not name or describe it as fire, frost, lightning, poison, acid, rot, holy light or thorn and root")
    if eff == "healing" and s.get("heal_form"):
        import yaml as _y
        HF = _y.safe_load((ROOT / "data" / "rules" / "healing.yaml").read_text(encoding="utf-8"))["forms"]
        parts.append(f"a heal for yourself or one ally: {HF[s['heal_form']]['depict']}")
    elif eff == "damage":
        parts.append(E["damage_area"] if s["reach"] == "area" else E["damage_single"])
        if s["reach"] == "ranged" and weapon_at_range(s):
            parts.append(E["damage_at_range"])                # (f287) a weapon technique at range is a throw or a shot, not a lunge
    elif eff == "summon":
        import yaml as _yf
        SF = _yf.safe_load((ROOT / "data" / "rules" / "summons.yaml").read_text(encoding="utf-8"))["forms"]
        parts.append(f"{E[eff]}: {SF.get(s.get('summon_form') or 'striker', {}).get('depict', '')}")
    elif eff == "command":
        parts.append(E[eff])
    elif eff != "buff" and not (eff == "control" and s.get("expressions")) and not (s["field_use"] and eff == "utility") and not field.in_combat_function(s["field_use"]):
        parts.append(E.get(eff, eff))
    if s["buff"]:
        b = s["buff"]
        txt = AT.imbue_text(s.get("element", ""), s.get("expressions") or [], s["tier"]) if b == "imbue" else \
            AT.attunement_text(s.get("element", "")) if b == "attunement" else AT.buff_text(b)
        parts.append(f"{AT.BUFFS[b]['label']}: {txt}")
    if s["command"]:
        parts.append(f"{AT.COMMANDS[s['command']]['label']}: {AT.command_text(s['command'], s['tier'])}")
    if s["shape"]:
        sh = s["shape"]
        parts.append(f"{AT.shape_label(sh, s.get('reach', ''))}: {AT.shape_text(sh)}")
    if s["rider"]:
        r = s["rider"]
        parts.append(f"{AT.RIDERS[r]['label']}: {AT.rider_text(r, s['tier'])}")
    if s.get("spell_form") and s["spell_form"] != "bolt":
        from engine import spellcraft as SC
        parts.append(f"{SC.FORMS[s['spell_form']]['label']}: {SC.form_text(s['spell_form'])}")
    from engine import spellcraft as SC
    for eid in s.get("expressions") or []:
        x = SC.EXPR[eid]
        if x["kind"] == "control":
            parts.append(f"{x['label']}: {x['depict']} - it {SC.expression_text(eid, s['tier'])} It deals NO damage")
        else:
            parts.append(f"{x['label']}: {x['depict']} - it {SC.expression_text(eid, s['tier'])}")
    if int(s.get("cast_turns") or 0) > 1:
        parts.append(f"takes {s['cast_turns']} turns to gather before it goes off")
    if s.get("martial_form") and s["martial_form"] != "strike":
        from engine import martial as MA
        parts.append(f"{MA.FORMS[s['martial_form']]['label']}: {MA.form_text(s['martial_form'], s.get('hits', 0))}")
    if s.get("maneuver"):
        from engine import martial as MA
        m = MA.MANEUVERS[s["maneuver"]]
        parts.append(f"{m['label']}: {m['depict']} - it {MA.maneuver_text(s['maneuver'], s['tier'])}"
                     + (" It deals NO damage" if s["effect"] == "control" else ""))
    if s.get("channel"):
        parts.append("Channeled: magic struck through the wielded weapon - it hits with the weapon's power and the spell's, and gets past armor or ward, whichever is weaker")
    if s["field_use"]:
        where = "in a fight" if field.in_combat_function(s["field_use"]) else "outside combat"
        parts.append(f"{where} - {field.label(s['field_use'])}: {field.blurb(s['field_use'])}")
    return "; ".join(parts)


def writing_note(s: dict) -> str:
    """How the words must treat this slot, so they match it."""
    notes = []
    sh = s["shape"]
    if sh and AT.SHAPES[sh].get("multi"):
        n = AT.SHAPES[sh]["parts"]
        notes.append(f"SEVERAL strikes ({n} quick hits) - name and describe it as a flurry, volley or series of strikes, to suit the class "
                     f"({AT.SHAPES[sh]['hint']})")
    elif s["effect"] == "damage" and not (sh in SINGLE_HIT_OK) and s["reach"] != "area" and s.get("martial_form") not in ("flurry", "sweep"):
        notes.append("ONE blow at ONE target - do not describe several hits")
    if sh and sh in P["depict"]:
        notes.append(P["depict"][sh])
    if s["buff"] and s["buff"] in P["depict"]:
        notes.append(P["depict"][s["buff"]])
    if s.get("channel"):
        notes.append("a blow with the character's own weapon, charged with magic that suits the class (fire, holy, shadow, force...) - not a thrown spell")
    if s["effect"] == "damage" and s["reach"] == "area":
        notes.append("hits an area, not a single target")
    mf = s.get("martial_form")
    if mf == "flurry":
        notes.append(f"exactly {s.get('hits', 2)} quick strikes in a row - name and describe it as a flurry or combination of that many blows")
    elif mf == "sweep":
        notes.append("one sweeping blow through everyone close around the user")
    elif mf == "windup":
        notes.append("a slow, heavy blow the user sets themselves for, then brings down - a telegraphed, all-in strike")
    elif mf == "counter":
        notes.append("a readied stance that waits for an attacker and answers its blow - NOT a strike thrown first")
    if s.get("spell_form") == "curse":
        notes.append("lingering harm that works on the target over several turns, not an instant blast")
    elif s.get("spell_form") == "charged":
        notes.append("gathered over a moment and then released all at once - a slow, heavy working")
    elif s.get("spell_form") == "burst":
        notes.append("bursts out from the caster into everyone close around them")
    from engine import spellcraft as SC
    if any(SC.is_control(e) for e in s.get("expressions") or []) and s["effect"] == "control":
        notes.append("it does NOT harm anyone directly - " + "; ".join(SC.EXPR[e]["depict"] for e in s["expressions"]))
    if s["reach"] == "self":
        notes.append("on the caster only; no target")
    return "; ".join(notes)


def slot_line(s: dict) -> str:
    cost = "mana" if s["resource"] == "mana" else "stamina"
    ctx = {"combat": "combat only", "out_of_combat": "outside combat", "both": "combat and outside"}[s["context"]]
    reach = "on yourself" if s["reach"] == "self" else f"{s['reach']} reach"
    head = f"{s['n']}. {s['effect'].upper()} - {s['tier']} - {reach} - {cost} - {ctx}"
    lines = [head, f"     does: {mechanic_text(s)}"]
    note = writing_note(s)
    if note:
        lines.append(f"     write it as: {note}")
    return "\n".join(lines)


def slot_lines(slots: list[dict]) -> str:
    return "\n".join(slot_line(s) for s in slots)


# ---------- checking the model's words against the plan ----------

def weapon_at_range(s: dict) -> bool:
    """A ranged attack made with the weapon, not a spell: a technique (stamina) or a channeled strike."""
    return s["reach"] == "ranged" and (s.get("resource") != "mana" or bool(s.get("channel")))


def reads_close(text: str) -> bool:
    """Does this read as a blow at someone right beside you rather than an attack from a distance? By meaning, through the helper model;
    when it is not there, nothing is judged."""
    from llm import embed
    E = P["effects"]
    sims = embed.whole(text, [E["reads_close"], E["reads_far"]])
    return bool(sims) and sims[0] > sims[1] + 0.03


def text_problem(s: dict, name: str, description: str) -> str:
    """Why this name and description do not suit the slot's mechanic. Empty if they do."""
    text = f"{name} {description}".lower()
    sh = s["shape"]
    if s["effect"] == "damage" and s.get("martial_form") == "flurry":
        if not (any(w in text for w in STRICT_MULTI) or any(w in text for w in PLURAL_HITS)):
            return f"'{name}' must read as SEVERAL strikes (it is a flurry of {s.get('hits', 2)} hits) - name and describe a flurry or combination"
    elif s["effect"] == "damage" and s["reach"] != "area" and sh not in SINGLE_HIT_OK and s.get("martial_form") != "sweep":
        multi_words = any(w in text for w in STRICT_MULTI)
        if sh and AT.SHAPES[sh].get("multi"):
            if not (multi_words or any(w in text for w in PLURAL_HITS)):
                return f"'{name}' must read as SEVERAL strikes (it is a {AT.SHAPES[sh]['label']}): {AT.SHAPES[sh]['hint']}"
        elif multi_words:
            return f"'{name}' reads as several hits, but ability {s['n']} is ONE blow at one target - name and describe a single strike"
    class _A:
        pass
    a = _A()
    a.name, a.description, a.reach, a.shape, a.rider = name, description, s["reach"], sh, s["rider"]
    why = AT.fit_problem(a)
    if why:
        return f"ability {s['n']}: {why}"
    from engine import elements as EL
    reads = EL.of_text(text)                              # the words only CHECK the narration; the element is the slot's
    if reads and reads != s.get("element") and (elemental(s) or s["effect"] == "damage"):      # a plain technique too (f272)
        return (f"'{name}' reads as {reads}, but ability {s['n']} is " + (f"{s['element']}" if s.get("element") else "plain physical, with no element")
                + " - name and describe it to match")
    if s["effect"] == "damage" and weapon_at_range(s) and reads_close(f"{name}. {description}"):
        return (f"'{name}' reads as a blow at someone right beside the user, but ability {s['n']} is made from a distance - "
                "name and describe a throw, a shot, or a strike that reaches across the gap")
    if s["effect"] != "summon" and s["field_use"] != "phantom_steed" and any(w in text for w in ("steed", "mount ", "mounted")):
        return f"'{name}' mentions a mount, which ability {s['n']} does not do"
    return ""
