"""(f359) The player as a cause, without the model: what they have done lately can start a situation at their town.

Why: the pulse placed its situations near the player but never answered them. The deeds ledger reached only the model-written tiers,
which were nearly never written, so twenty wolves killed changed nothing in the town that lost sheep to them. Now a small table
(data/rules/consequences.yaml) says which runs of deeds the town notices, and each pulse tick the engine checks it: the deeds of the last
few days, grouped as the rule says, at the player's town or in its region; a rule met starts a situation from its own template (marked
consequence: true in threads.yaml, so chance never draws it), with the deeds' own creature in its words, through the door the rule names.
A cooldown keeps the same answer from coming twice."""
from __future__ import annotations

import random
import types
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
C = yaml.safe_load((ROOT / "data" / "rules" / "consequences.yaml").read_text(encoding="utf-8"))


def _group(deeds: list[dict], same: str) -> tuple[str, int]:
    """The biggest group of deeds by the `same` field, (value, count); ('', len) when nothing groups them."""
    if not same:
        return "", len(deeds)
    counts: dict[str, int] = {}
    for d in deeds:
        v = str(d.get(same) or "")
        if v:
            counts[v] = counts.get(v, 0) + 1
    if not counts:
        return "", 0
    best = max(counts, key=lambda k: (counts[k], k))
    return best, counts[best]


def met(state: dict, world, town: str, t: int) -> list[tuple[dict, dict]]:
    """Every rule the deeds of the last days satisfy at this town, with the words its situation is built with."""
    from engine import deeds, pulse
    out = []
    last = state.get("consequence_last") or {}
    region = world.places[town].region if town in world.places else ""
    for rule in C.get("rules") or []:
        spec = rule.get("deeds") or {}
        if t - last.get(f"{rule['id']}:{town}", -10 ** 9) < int(rule.get("cooldown_days", 10)) * 1440:
            continue
        rows = deeds.since(state, t - int(spec.get("days", 7)) * 1440, (spec.get("kind"),))
        if spec.get("where", "town") == "town":
            rows = [d for d in rows if pulse.town_of(world, d.get("place") or "") == town]
        else:
            rows = [d for d in rows if (d.get("place") or "") in world.places and world.places[d["place"]].region == region]
        value, n = _group(rows, spec.get("same", ""))
        if n >= int(spec.get("count", 1)):
            words = {}
            if spec.get("same") == "creature" and value in world.bestiary:
                words["creature"] = value
            out.append((rule, words))
    return out


def pressure_for(rule: dict, town: str, words: dict):
    """A pressure-shaped record for the situation: the rule's template, the town as its place, the deeds' words fixed."""
    from engine import threads
    tpl = threads.T["templates"].get(rule["template"]) or {}
    return types.SimpleNamespace(id=f"consequence:{rule['id']}", place=town, kind=threads.kind_of(rule["template"]),
                                 description="", weight=1.0, severity=tuple(rule.get("severity", [1, 2])), scope="local", campaign=False,
                                 reward=[], template=rule["template"], words=dict(words), consequence=True, _tpl=tpl)


def tick(store, world, catalog, state: dict, t: int, rng: random.Random) -> bool:
    """One pulse tick: the first rule met at the player's town starts its situation. True when one did."""
    from engine import pulse
    if not store.player_exists():
        return False
    town = pulse.home_town(world, store.load_player().location)          # (f376) on a stop on the road, the end it is nearer: never the stop
    if not pulse.known(world, town) or world.places[town].danger or not world.peoples_at(town):
        return False
    for rule, words in met(state, world, town, t):
        pulse.LAST["made_by"] = ""
        if rule.get("tier") == "campaign":                                # (f363) a campaign earned by play, the model's as every campaign is
            if state.get("campaign"):
                continue
            ok = pulse.start_campaign_for(store, world, catalog, state, t, rng, town, rule.get("door", ""))
            retry = int(rule.get("cooldown_days", 10)) * 1440 - int(C.get("retry_days", 1)) * 1440
            state.setdefault("consequence_last", {})[f"{rule['id']}:{town}"] = t if ok else t - retry
            if ok:
                th = state["threads"][-1]
                th["consequence"], th["earned"] = rule["id"], True
                from engine import pulselog
                pulselog.note("consequence", f"{th['title']} - a campaign earned by the stranger's deeds ({rule['id']})", place=town, tier="campaign")
                return True
            continue
        ok = pulse.start_thread(store, world, catalog, state, t, rng, tier="normal", made_by="engine",
                                pressure=pressure_for(rule, town, words), door=rule.get("door", ""))
        state.setdefault("consequence_last", {})[f"{rule['id']}:{town}"] = t
        if ok:
            state["threads"][-1]["consequence"] = rule["id"]
            from engine import pulselog
            pulselog.note("consequence", f"{state['threads'][-1]['title']} - the town answers the stranger's deeds ({rule['id']})", place=town)
            return True
    return False


def problems(templates: dict, deed_kinds=()) -> list[str]:
    bad = []
    for r in C.get("rules") or []:
        if r.get("tier") == "campaign":                                                  # (f363) no template: the model writes a campaign
            if r.get("template"):
                bad.append(f"consequences.yaml {r.get('id')}: a campaign rule names no template")
            if r.get("door") not in ("summons", "word", ""):
                bad.append(f"consequences.yaml {r.get('id')}: door is summons or word")
            if (r.get("deeds") or {}).get("kind") not in (deed_kinds or ((r.get("deeds") or {}).get("kind"),)):
                bad.append(f"consequences.yaml {r.get('id')}: '{(r.get('deeds') or {}).get('kind')}' is not a kind of deed")
            continue
        if r.get("template") not in templates:
            bad.append(f"consequences.yaml {r.get('id')}: '{r.get('template')}' is not a template")
        elif not templates[r["template"]].get("consequence"):
            bad.append(f"consequences.yaml {r.get('id')}: its template must be marked consequence: true in threads.yaml")
        if r.get("door") not in ("summons", "word", ""):
            bad.append(f"consequences.yaml {r.get('id')}: door is summons or word")
        spec = r.get("deeds") or {}
        if deed_kinds and spec.get("kind") not in deed_kinds:
            bad.append(f"consequences.yaml {r.get('id')}: '{spec.get('kind')}' is not a kind of deed")
        if spec.get("where", "town") not in ("town", "region"):
            bad.append(f"consequences.yaml {r.get('id')}: where is town or region")
    return bad
