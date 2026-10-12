"""Slot-based creation of a class's 15 starting actives.

The engine plans every slot first - its effect, tier, reach, resource, context and its rider, shape, buff, command or world
function - and the model is only asked to NAME and DESCRIBE each one. So an ability can no longer be described as one thing and
do another: the words are written for a mechanic that already exists (data/rules/ability_slots.yaml)."""

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
SINGLE_HIT_OK = ("chain", "sweeping", "ricochet", "packhunt")      # shapes whose ability may well read as striking several foes


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
            "buff": "", "buff_stat": "", "command": "", "field_use": ""}


def _counts(interp, offers, minimum, buffs, commands, summons, healing, crafting) -> dict:
    selfish = healing + summons + crafting
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
    comp = bool(getattr(interp, "uses_companions", False))
    focus = interp.focus

    summons = rng.choice([2, 3]) if comp else 0
    commands = min(len(offers.get("commands", [])), rng.choice([2, 2, 3])) if comp else 0
    healing = 2 if arch == "support" else (1 if fams & {"healer", "paladin", "druid"} else 0)
    crafting = 2 if "artisan" in fams else 0
    buffs = min(len(offers["buffs"]), 1 if focus == "social" else 2)
    needed_dc = _needed_riders_shapes(offers)
    # make room for the combat abilities that carry riders and shapes
    for field_name, floor in (("buffs", 1), ("commands", 2), ("crafting", 0), ("summons", 2), ("commands", 1), ("healing", 1 if arch == "support" else 0)):
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

    slots: list[dict] = []

    def add(**kw):
        s = _base()
        s.update(kw)
        slots.append(s)

    # ---- the fixed kinds ----
    for i in range(summons):
        add(effect="summon", tier=rng.choice(["light", "moderate"]), reach="self", context="both")
    cmds = rng.sample(offers.get("commands", []), commands) if commands else []
    for cm in cmds:
        add(effect="command", tier="light", reach="self", context="combat", command=cm)
    for i in range(healing):
        add(effect="healing", tier="light" if i == 0 else "moderate", reach="self" if i == 0 else "extended", context="both")
    for i in range(crafting):
        add(effect="crafting", tier="light", reach="self", context="out_of_combat")
    chosen_buffs = _pick_buffs(interp, offers["buffs"], buffs, rng)
    for b in chosen_buffs:
        add(effect="buff", tier="moderate" if rng.random() < 0.3 else "light", reach="self", context="combat", buff=b)
    for fn in _pick_functions(interp, offers.get("functions", []), n_functions, rng):
        spec = dict(P["function_defaults"])
        spec.update(P["functions"].get(fn) or {})
        add(effect=spec["effect"], tier=spec["tier"], reach=spec["reach"], context=spec["context"], field_use=fn)

    # ---- the combat remainder ----
    weights = dict(P["mix"][focus])
    if comp:
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
    for _ in range(counts["mobility"]):
        add(effect="mobility", tier="light", reach="self", context="combat")
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
        if s["effect"] in ("defense", "mobility") and rng.random() < 0.25:
            s["tier"] = "moderate"

    _assign_resources(slots, interp, arch, fams, rng)
    rng.shuffle(slots)
    for n, s in enumerate(slots, 1):
        s["n"] = n
    return slots


def _pick_buffs(interp, offered, n, rng) -> list[str]:
    ids = list(offered)
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


def _assign_resources(slots, interp, arch, fams, rng):
    share = P["mana_share"][arch]
    for fam, v in P["hybrid_families"].items():
        if fam in fams and share < v:
            share = v
    magical = {"healing": 0, "summon": 1, "command": 2, "control": 3, "influence": 4, "buff": 5, "damage": 6, "utility": 7,
               "defense": 8, "mobility": 9, "crafting": 10}
    ranked = sorted(slots, key=lambda s: (magical.get(s["effect"], 9), rng.random()))
    n_mana = round(share * len(slots))
    for i, s in enumerate(ranked):
        s["resource"] = "mana" if i < n_mana else "stamina"


# ---------- what the model is told ----------

def mechanic_text(s: dict) -> str:
    """What this slot does, in the words the model needs to write for it."""
    E = P["effects"]
    eff = s["effect"]
    parts = []
    if eff == "damage":
        parts.append(E["damage_area"] if s["reach"] == "area" else E["damage_single"])
    elif eff == "summon" or eff == "command":
        parts.append(E[eff])
    elif eff != "buff" and not (s["field_use"] and eff == "utility") and not field.in_combat_function(s["field_use"]):
        parts.append(E.get(eff, eff))
    if s["buff"]:
        b = s["buff"]
        txt = "raises armor, ward or both" if b == "bulwark" else AT.buff_text(b, s["tier"])
        parts.append(f"{AT.BUFFS[b]['label']}: {txt}")
    if s["command"]:
        parts.append(f"{AT.COMMANDS[s['command']]['label']}: {AT.command_text(s['command'], s['tier'])}")
    if s["shape"]:
        sh = s["shape"]
        parts.append(f"{AT.SHAPES[sh]['label']}: {AT.shape_text(sh)}")
    if s["rider"]:
        r = s["rider"]
        parts.append(f"{AT.RIDERS[r]['label']}: {AT.rider_text(r, s['tier'])}")
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
    elif s["effect"] == "damage" and not (sh in SINGLE_HIT_OK) and s["reach"] != "area":
        notes.append("ONE blow at ONE target - do not describe several hits")
    if sh and sh in P["depict"]:
        notes.append(P["depict"][sh])
    if s["buff"] and s["buff"] in P["depict"]:
        notes.append(P["depict"][s["buff"]])
    if s["buff"] == "bulwark":
        notes.append("armor-like for a physical class, ward-like for a magical one")
    if s["effect"] == "damage" and s["reach"] == "area":
        notes.append("hits an area, not a single target")
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

def text_problem(s: dict, name: str, description: str) -> str:
    """Why this name and description do not suit the slot's mechanic. Empty if they do."""
    text = f"{name} {description}".lower()
    sh = s["shape"]
    if s["effect"] == "damage" and s["reach"] != "area" and sh not in SINGLE_HIT_OK:
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
    if s["effect"] != "summon" and s["field_use"] != "phantom_steed" and any(w in text for w in ("steed", "mount ", "mounted")):
        return f"'{name}' mentions a mount, which ability {s['n']} does not do"
    return ""
