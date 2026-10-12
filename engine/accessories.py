"""Rings and amulets: lanes, traits, powers and gifts (data/rules/accessories.yaml).

An accessory is assembled from parts at the moment it is found, so no two are alike: a lane (what kind of wearer it suits), stats from that
lane, a trait mechanic, a limited-use power, and from epic a world gift. A boss's relic adds the boss kit's signature.
Everything lives on the Item: `properties` (the stats), `trait` and `relic`. The model only names it, from the story around it.
"""

import random
from pathlib import Path

import yaml

from core.models import Item
from engine import items

A = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "accessories.yaml").read_text(encoding="utf-8"))
JEWELRY_SLOTS = ("ring", "neck")


def is_accessory(item: Item) -> bool:
    return items.base_of(item).slot in JEWELRY_SLOTS


def _scaled(value: float, factor: float) -> float:
    return value if value == 0 else max(1, round(value * factor)) if value >= 5 else max(0.5, round(value * factor, 1))


def _legendary_text(mech_id: str, value: float, world: bool = False) -> str:
    le = next((x for x in items.LEGENDARY.values() if (x.world == mech_id if world else x.id == mech_id)), None)
    if not le:
        return mech_id.replace("_", " ")
    return le.description.format(value=f"{(value or le.value):g}")


def make_power(power_id: str, factor: float, uses: int, override: dict | None = None) -> dict:
    """A power with its numbers resolved for this rarity. `override` is a boss's own power (already written out)."""
    p = dict(override or A["powers"][power_id])
    scale = p.pop("scale", [])
    mech = dict(p.get("mech", {}))
    flat = {k: v for k, v in p.items() if k not in ("name", "kind", "text", "mech", "status", "collapse", "wide")}
    for k in scale:
        if k in flat:
            flat[k] = _scaled(flat[k], factor)
        if k in mech:
            mech[k] = _scaled(mech[k], factor)
    shown = {**flat, **mech}
    text = p["text"].format(**{k: (f"{v:g}" if isinstance(v, (int, float)) else v) for k, v in shown.items()})
    out = {"id": power_id, "name": p["name"], "kind": p["kind"], "uses": uses, "text": text,
           "params": {**flat, "mech": mech, **{k: p[k] for k in ("status", "collapse", "wide") if k in p}}}
    return out


def roll(item: Item, rng: random.Random, signature_kit: str = "") -> None:
    """Give a ring or amulet its stats, trait, power and gift. `signature_kit` makes it a boss's relic."""
    from engine import loot
    R = A["rarity"][item.rarity]
    slot = items.base_of(item).slot
    lane_id = rng.choice(A["slot_lanes"][slot])
    lane = A["lanes"][lane_id]
    extra = items.material_of(item).extra_properties if items.material_of(item) else 0
    item.properties = loot.roll_properties(item.rarity, rng, extra, only=lane["stats"], count=R["stats"] + extra)
    trait: dict = {"lane": lane_id, "label": lane["label"], "fight": {}, "world": {}, "text": []}
    if R["mech"]:
        mech_id = rng.choice(list(lane["mechs"]))
        v = _scaled(lane["mechs"][mech_id], R["mech"])
        trait["fight"][mech_id] = v
        trait["text"].append(_legendary_text(mech_id, v))
    if R["world"]:
        wid = rng.choice(list(lane["world"]))
        le = items.LEGENDARY[wid]                        # the lane lists wonders by name; the world answers to their mechanic
        v = lane["world"][wid]
        trait["world"][le.world] = v
        trait["text"].append(le.description.format(value=f"{(v or le.value):g}"))
    relic: dict = {}
    if R["power"]:
        relic = make_power(rng.choice(lane["powers"]), R["power"], R["uses"])
    if signature_kit:
        variants = A["bosses"].get(signature_kit) or A["bosses"]["default"]
        sig = rng.choice(variants)
        trait["signature"] = sig["id"]
        trait["kit"] = signature_kit if signature_kit in A["bosses"] else "default"
        for k, v in sig.get("fight", {}).items():
            trait["fight"][k] = trait["fight"].get(k, 0) + v
        trait["world"].update(sig.get("world", {}))
        if "text" in sig:
            trait["text"].append(sig["text"].format(value=f"{max(sig.get('fight', {'x': 0}).values()):g}"))
        if "power" in sig:
            relic = make_power(sig["id"], 1.0, R["uses"], override=sig["power"])
    item.trait = trait
    item.relic = relic


def boss_relic(kit: str, level: int, rng: random.Random) -> Item:
    """The relic a boss of this kit leaves behind: a legendary ring or amulet."""
    bases = [b for b in items.CATALOG.values() if b.slot in JEWELRY_SLOTS and b.min_level <= level]
    item = items.make(rng.choice(bases).id, "legendary", level, rng=rng)
    roll(item, rng, signature_kit=kit)
    return item


def fight(item: Item) -> dict[str, float]:
    return item.trait.get("fight", {}) if item.trait else {}


def world(item: Item) -> dict[str, float]:
    return item.trait.get("world", {}) if item.trait else {}


def lines(item: Item) -> list[str]:
    """What the item's trait and power do, one line each, for the item screen."""
    out = list(item.trait.get("text", [])) if item.trait else []
    if item.relic:
        r = item.relic
        out.append(f"Power - {r['name']} ({r['uses']}/fight): {r['text']}")
    return out
