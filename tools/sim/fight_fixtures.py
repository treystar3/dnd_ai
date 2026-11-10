"""(f494) Fixtures of today's fight numbers (Bundle E, decision 10): fights played through the real scene under the stub, so their dice
are the campaign's own streams, with every round's blows (the hits records the window explains), the fight's log, each fighter's
resources, statuses, strengths, buffs and place, and at the end what was won; the stat sheets of every stub class at three levels; and
what the grid covered. Stage 8 rewrites the fight code with no number changed: these are the numbers it must keep.

    python3 tools/sim/fight_fixtures.py --record [SHARD...]     write tools/sim/fixtures/fights/*.json.gz (and sheets, coverage)
    python3 tools/sim/fight_fixtures.py [SHARD...]              compare: per case the first differing path and a count by key

A case is one fight from a fresh character: its class and level, the creature, its rank and number, what the player is given (mechanics
by id, a boss's kit and tier, statuses laid on at the first round, hires), how the player chooses (attack, or each ability in turn), and
its own clock and stream keys, so a case that changes never moves the cases after it. The grid is built from the data (every creature
family, every combat mechanic in groups, every status, the boss kits, hires), so it grows with the game. Files sit outside the data hash
(storage/statehash.py: tools/ is not data/), as sorted-key JSON with the data hash in a header; a re-record is accepted only with the
compare's printout read and named in its commit, as a golden's re-bless is."""
from __future__ import annotations

import gzip
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "tools" / "sim" / "fixtures" / "fights"
SHARDS = 4
MAX_ROUNDS = 14
LEVELS = (1, 10, 25)
SNAP = ("hp", "max_hp", "stamina", "max_stamina", "mana", "max_mana", "shield", "statuses", "status_from", "ignite", "poison",
        "poison_fixed", "bleed", "buffs", "cooldowns", "zone_id", "row", "fled", "surrendered", "hardening_stacks", "breath")
BOSSES = (("dragon", "campaign"), ("undead", "cataclysm"), ("giant", "leader"), ("fiend", "captain"), ("person", "leader"),
          ("construct", "campaign"))


def _classes() -> list[str]:
    import simlib
    return list(simlib.CLASSES)


def cases() -> list[dict]:
    """The grid, in a fixed order. Each case: id, cls, level, creature, rank, count, mechanics {id: value}, boss (kit, tier) or None,
    statuses [names] laid on at the first round (alternately on the first foe and the player), hires (count), chooser, n (its index)."""
    from core import rules
    from engine import combat
    from world.loader import load_world
    world = load_world()
    classes = _classes()
    fam: dict[str, list[str]] = {}
    for cid, c in sorted(world.bestiary.items()):
        fam.setdefault(getattr(c, "family", "") or "?", []).append(cid)
    out: list[dict] = []

    def add(**k):
        k.setdefault("rank", "normal")
        k.setdefault("count", 1)
        k.setdefault("mechanics", {})
        k.setdefault("boss", None)
        k.setdefault("statuses", [])
        k.setdefault("hires", 0)
        k.setdefault("chooser", "attack")
        k.setdefault("foe_level", k["level"])
        k.setdefault("start_hp", 1.0)                                  # the first foe's health at the start, as a share of its most
        k.setdefault("player_hp", 1)                                   # the player's health and most, as a multiple of what they have
        k["n"] = len(out)
        out.append(k)

    for i, (family, ids) in enumerate(sorted(fam.items())):                 # every family, a class and a level each
        add(id=f"family:{family}", cls=classes[i % len(classes)], level=LEVELS[i % len(LEVELS)], creature=ids[0],
            count=1 + i % 2, chooser="abilities" if i % 3 else "attack")
    mechs = sorted(rules.ENGINE_COMBAT_MECHANICS)
    values = {m["id"]: (m.get("values") or [1, 1])[-1] or 1 for m in rules.load_passive_mechanics() if m.get("kind") == "combat"} \
        if hasattr(rules, "load_passive_mechanics") else {}
    if not values:
        import yaml
        values = {m["id"]: (m.get("values") or [1, 1])[-1] or 1
                  for m in yaml.safe_load((ROOT / "data" / "rules" / "passive_mechanics.yaml").read_text(encoding="utf-8"))
                  if m.get("kind") == "combat"}
    for j in range(0, len(mechs), 6):                                        # every combat mechanic, six to a fight
        group = mechs[j:j + 6]
        add(id=f"mechanics:{group[0]}..{group[-1]}", cls="warrior", level=10, creature="bandit" if "bandit" in world.bestiary else ids[0],
            count=2, mechanics={m: values.get(m, 1) for m in group}, chooser="attack")
    statuses = sorted((combat.RULES.get("statuses") or {}).keys())
    for j in range(0, len(statuses), 3):                                     # every status, three to a fight
        add(id=f"statuses:{','.join(statuses[j:j + 3])}", cls="mage", level=10, creature="wolf", count=2, statuses=statuses[j:j + 3],
            chooser="abilities")
    for k, (kit, tier) in enumerate(BOSSES):                                 # the boss kits: phases, legendary actions and resistance
        add(id=f"boss:{kit}:{tier}", cls=classes[k % len(classes)], level=25, foe_level=5 if k % 2 else 10,
            creature=_boss_creature(world, kit), rank="boss", boss=(kit, tier), chooser="abilities",
            start_hp=0.06 if k % 2 else 0.52, player_hp=4 if k % 2 else 1)     # near bloodied, or past it with a player who lasts:
                                                                                  # the phases and the last stand come into play
    for k in range(4):                                                       # hires beside the player, against a pack
        add(id=f"hires:{k + 1}", cls=classes[(k * 3) % len(classes)], level=LEVELS[k % len(LEVELS)], creature="wolf", count=3,
            hires=1 + k % 2, chooser="abilities" if k % 2 else "attack")
    for k, rank in enumerate(("elite", "boss")):                             # the ranks alone
        add(id=f"rank:{rank}", cls="warrior", level=10, creature="troll" if "troll" in world.bestiary else "wolf", rank=rank)
    return out


def _boss_creature(world, kit: str) -> str:
    want = {"dragon": "dragon", "undead": "undead_lord", "giant": "giant", "fiend": "demon", "person": "warlord", "construct": "construct"}
    fam = want.get(kit, "")
    ids = sorted(cid for cid, c in world.bestiary.items() if getattr(c, "family", "") == fam)
    return ids[0] if ids else "troll"


def shard_of(case: dict) -> int:
    return case["n"] % SHARDS


# ---------- running a case

def _fighter(f) -> dict:
    data = f.model_dump(mode="json")      # (f497) a snapshot by the fields' types: a dict held by reference showed every round the fight's
    flat = {k: v for part in data.values() if isinstance(part, dict) for k, v in part.items()}   # (f508) the dump is nested by part
    out = {k: flat[k] if k in flat else _norm(getattr(f, k)) for k in SNAP}   # end state (the live object went on changing it), and a float
    #                                     left as an int read 0 live, 0.0 resumed; (f507) statuses, strengths and buffs are views over the rows
    if getattr(f, "boss", None):
        out["boss"] = {k: f.boss.get(k) for k in ("phase", "la", "lr", "stand_used", "fell", "guards")}
    return out


def _hires(n: int, level: int) -> list[dict]:
    roles = ["fighter", "priest", "archer", "mage"]
    return [{"id": f"h{i + 1}", "name": f"Hire {i + 1}", "role": roles[i % len(roles)], "level": level, "rank": "E", "permanent": True,
             "temper": ["blunt"], "blurb": "a hired hand", "active": True} for i in range(n)]


def run_case(game, stub, case: dict, cover: dict) -> dict:
    """One fight, start to end, through the scene. Returns its record."""
    import simlib
    from engine import bosses, combat, streams
    from scenes import combat_scene as cs
    ws, store = game.scene, game.store
    char, _ = simlib.make_character(case["cls"], random.Random(1000 + case["n"]))
    char.level = case["level"]
    ws.player.character = char
    ws.player.party = _hires(case["hires"], case["level"])
    ws.player.party_mode = "with"
    store.meta.minutes = 600 + 10 * case["n"]
    store.meta.turn = 1 + 100 * case["n"]
    store.save_meta()
    store.save_player(ws.player)
    ws.combat = None
    seed = store.meta.seed
    base = 100000 * (case["n"] + 1)
    streams.begin(seed, base, f"case:{case['id']}")
    creature = ws.world.bestiary[case["creature"]]
    foes = [combat.fighter_from_creature(creature, case["foe_level"], case["rank"], f"e{i + 1}", name=f"{creature.name} {i + 1}")
            for i in range(case["count"])]
    if case["boss"]:
        kit, tier = case["boss"]
        foes[0].boss = bosses.make(kit, tier, foes[0].name)
    if case["start_hp"] < 1.0:
        foes[0].hp = max(1, round(foes[0].max_hp * case["start_hp"]))
    sc = cs.CombatScene.begin(ws, creature, foes, "It is on you:")
    ws.combat = sc
    fight = sc.fight
    me = fight.player
    if case["player_hp"] != 1:
        me.max_hp = me.max_hp * case["player_hp"]
        me.hp = me.max_hp
    for m, v in case["mechanics"].items():
        me.legendary[m] = me.legendary.get(m, 0) + v
        me.mech_names.setdefault(m, m.replace("_", " ").title())
    for i, s in enumerate(case["statuses"]):
        target = fight.enemies()[0] if i % 2 == 0 and fight.enemies() else me
        combat.add_status(fight, target, s, 3, source=me if target is not me else (fight.enemies() or [None])[0])
    store.save_combat(sc.to_json())
    record = {"id": case["id"], "case": {k: case[k] for k in case if k != "n"}, "danger": list(cover.pop("_danger", ()) or ()),
              "start": {f.id: _fighter(f) for f in fight.fighters}, "rounds": []}
    xp0, coins0 = char.xp, getattr(char, "coins", 0)
    pack0 = [getattr(i, "uid", "") for i in getattr(char, "inventory", [])]
    carcasses0 = len(getattr(ws.place, "carcasses", []) or [])
    turn = {"r": 0, "last": None}

    def choose(u, k):
        f = ws.combat.fight if ws.combat is not None else fight
        foes_up = [e for e in f.enemies()]
        target = foes_up[0].id if foes_up else ""
        if case["chooser"] == "abilities" and turn["last"] != "stuck":
            moves = [m for m in (f.player.moves if f.player else []) if getattr(m, "id", "")]
            if moves:
                m = moves[turn["r"] % len(moves)]
                return {"kind": "ability", "ability": m.id, "target": target}
        return {"kind": "attack", "target": target}

    stub.a_CombatIntent = choose
    live = {"fight": fight}
    real_resume = cs.CombatScene.resume

    def resume(ws_, raw):                                              # (f497) the round's line stands down at its reading and the fight is
        scene = real_resume(ws_, raw)                                  # resumed from the row: a new object, the one the round then runs on,
        live["fight"] = scene.fight                                    # and the one the record reads (the numbers are the same either way)
        return scene

    cs.CombatScene.resume = resume
    try:
        for r in range(MAX_ROUNDS):
            if ws.combat is None:
                break
            before = fight.round
            streams.begin(seed, base + r + 1, f"round:{r + 1}")
            ws.turn("I fight on")
            fight = live["fight"]
            turn["r"] += 1
            turn["last"] = "stuck" if (ws.combat is not None and ws.combat.fight.round == before) else None
            f = ws.combat.fight if ws.combat is not None else fight
            for h in f.hits or []:                                     # what fired, by the name the window shows it under
                for step in (h.get("steps") or []) + (h.get("extras") or []):
                    cover["labels"].add(str(step[0]))
            for x in f.fighters:
                if getattr(x, "boss", None):
                    cover["boss_phases"].add(f"{case['boss'][0] if case['boss'] else '?'}:{x.boss.get('phase')}")
            record["rounds"].append({"round": f.round, "hits": json.loads(json.dumps(f.hits or [], default=str)), "log": list(f.log or []),
                                     "fighters": {x.id: _fighter(x) for x in f.fighters}})
    finally:
        cs.CombatScene.resume = real_resume
    after = store.load_player().character
    place = ws.place
    record["end"] = {"over": getattr(fight, "over", None), "rounds": fight.round, "still_fighting": ws.combat is not None,
                     "xp": after.xp - xp0, "coins": getattr(after, "coins", 0) - coins0, "level": after.level,
                     "found": [{"name": getattr(i, "name", ""), "base": getattr(i, "base", ""), "rarity": str(getattr(i, "rarity", "")),
                                "legendary": [getattr(e, "id", str(e)) for e in (getattr(i, "legendary", None) or [])]}
                               for i in getattr(after, "inventory", []) if getattr(i, "uid", "") not in pack0],
                     "carcasses": len(getattr(place, "carcasses", []) or []) - carcasses0}
    if ws.combat is not None:                                         # a fight still standing at the cap: let it go, so the next case is clean
        store.save_combat(None)
        ws.combat = None
    cover["families"].add(getattr(creature, "family", "") or "?")
    cover["classes"].add(case["cls"])
    cover["mechanics_given"].update(case["mechanics"])
    return record


def sheets() -> dict:
    """The stat sheet (engine/statsheet.py) of every stub class at each of LEVELS, from a character built as creation builds one."""
    import simlib
    from engine import combat, statsheet
    out = {}
    for cls in _classes():
        for lv in LEVELS:
            char, _ = simlib.make_character(cls, random.Random(7))
            char.level = lv
            out[f"{cls}:{lv}"] = statsheet.sheet(combat.fighter_from_character(char))
    return out


# ---------- recording and comparing

def _path(shard: int) -> Path:
    return OUT / f"shard{shard}.json.gz"


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, sort_keys=True, indent=0, default=str).encode("utf-8")
    with gzip.GzipFile(filename="", mode="wb", fileobj=path.open("wb"), mtime=0) as f:     # no name or time inside: the same fights, the same bytes
        f.write(data)


def _read(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _norm(obj):
    """What a record looks like once written and read: JSON's own types, as the stored file holds them."""
    return json.loads(json.dumps(obj, sort_keys=True, default=str))


def play(shard: int, only: set[str] | None = None) -> tuple[list[dict], dict]:
    """Every case of a shard (or only those named), in order, in one campaign. Returns the records and the coverage."""
    import simlib
    stub = simlib.Stub("warrior", 1)
    simlib.install(stub)
    simlib.quiet_console()
    from engine import combat
    cover = {"labels": set(), "boss_phases": set(), "families": set(), "classes": set(), "mechanics_given": set(), "statuses": set()}
    real_add = combat.add_status

    def add_status(c, f, s, rounds, source=None):
        took = real_add(c, f, s, rounds, source)
        if took:
            cover["statuses"].add(s)
        return took

    combat.add_status = add_status
    real_danger = combat.danger

    def danger(fight):                                                # what the fight's start estimated, as the scene read it
        import time
        t0 = time.perf_counter()
        got = real_danger(fight)
        TIMES.append(time.perf_counter() - t0)                        # (f508) its wall time, printed by --time when run by hand
        cover["_danger"] = got
        return got

    combat.danger = danger
    from engine import crashlog
    FAULTS.clear()
    playing = {"case": "(entering the town)"}
    real_record = crashlog.record

    def record_fault(exc, where, **context):                        # (f566) a fault the game went on without: a turn's operation rolled
        FAULTS.append({"case": playing["case"], "where": where, "operation": context.get("operation", ""),   # back, its round not fought
                       "error": f"{type(exc).__name__}: {exc}"[:200]})
        return real_record(exc, where, **context)

    crashlog.record = record_fault
    import os
    import shutil
    name = f"fight_fixtures_{shard}_{os.getpid()}"                    # (f566) a save of this process's own: two runs of one shard at once
    shutil.rmtree(ROOT / "saves" / name, ignore_errors=True)          # (the suite runs four tests together; a run by hand beside it) never
    #                                                                   share a database or delete each other's; the name decides no number
    records = []
    game = None
    try:
        game = simlib.campaign(name, cls="warrior", seed=494, location="parth")
        game.scene.enter("parth")
        for case in cases():
            if shard_of(case) == shard and (only is None or case["id"] in only):
                playing["case"] = case["id"]
                records.append(run_case(game, stub, case, cover))
    finally:
        combat.add_status = real_add
        combat.danger = real_danger
        crashlog.record = real_record
        if game is not None:
            game.close()
        shutil.rmtree(ROOT / "saves" / name, ignore_errors=True)
    return records, {k: sorted(v) for k, v in cover.items() if not k.startswith("_")}


def header() -> dict:
    from storage import statehash
    return {"feature": "f494", "data_hash": statehash.data_hash()}


def first_difference(a, b, path: str = "") -> str:
    """The first path where two records part, with both values: round, hit tag, key, old -> new."""
    if type(a) is not type(b):
        return f"{path}: {str(a)[:80]} -> {str(b)[:80]}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                return f"{path}.{k}: {'missing' if k not in a else str(a[k])[:80]} -> {'missing' if k not in b else str(b[k])[:80]}"
            d = first_difference(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return ""
    if isinstance(a, list):
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f"{path}[{i}]")
            if d:
                return d
        if len(a) != len(b):
            return f"{path}: {len(a)} items -> {len(b)}"
        return ""
    return "" if a == b else f"{path}: {str(a)[:80]} -> {str(b)[:80]}"


def keys_moved(a, b, path: str = "", out: dict | None = None) -> dict:
    """Every leaf key that differs, counted by its last name: the shape of a diff at a glance."""
    out = {} if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out[str(k)] = out.get(str(k), 0) + 1
            else:
                keys_moved(a[k], b[k], str(k), out)
    elif isinstance(a, list) and isinstance(b, list):
        for x, y in zip(a, b):
            keys_moved(x, y, path, out)
        if len(a) != len(b):
            out[path or "length"] = out.get(path or "length", 0) + 1
    elif a != b:
        out[path or "value"] = out.get(path or "value", 0) + 1
    return out


def compare(shard: int, records: list[dict], only: set[str] | None = None) -> list[str]:
    """Lines naming each case that moved, its first difference and its keys; empty when every case is as recorded. With only, the
    cases named alone."""
    path = _path(shard)
    if not path.exists():
        return [f"shard {shard}: no fixture recorded ({path.name})"]
    kept = _read(path)
    out = []
    if kept.get("header", {}).get("data_hash") != header()["data_hash"]:
        out.append(f"warning: shard {shard} was recorded on other rules or content (its data hash differs)")
    old = {r["id"]: r for r in kept["cases"] if only is None or r["id"] in only}
    new = {r["id"]: r for r in _norm(records)}
    for cid in sorted(set(old) | set(new)):
        if cid not in old or cid not in new:
            out.append(f"{cid}: {'new case' if cid not in old else 'case gone'}")
            continue
        d = first_difference(old[cid], new[cid])
        if d:
            moved = keys_moved(old[cid], new[cid])
            out.append(f"{cid}: first at {d}; keys moved: " + ", ".join(f"{k} {n}" for k, n in sorted(moved.items(), key=lambda x: -x[1])[:8]))
    return [l for l in out if not l.startswith("warning")] + [l for l in out if l.startswith("warning")]


TIMES: list[float] = []     # (f508) danger's wall time per case of the shard last played, in order (--time prints them; no clock in tests)
FAULTS: list[dict] = []     # (f566) every fault the game recorded (engine/crashlog.py) while the shard last played: case, where, operation,
#                             error. A rolled-back turn is a round not fought, which reads as moved numbers; a fight played clean has none


def fault_lines(limit: int = 5) -> list[str]:
    """(f566) The faults of the shard last played, one line each, for a failed check or the compare's printout."""
    return [f"{f['case']}: {f['where']}/{f['operation'] or '-'}: {f['error']}" for f in FAULTS[:limit]]


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    record = "--record" in sys.argv
    shards = [int(a) for a in args] or list(range(SHARDS))
    moved = 0
    for s in shards:
        TIMES.clear()
        records, cover = play(s)
        if "--time" in sys.argv:                                      # (f508) by hand: how long the odds took, case by case
            for r, t in zip(records, TIMES):
                print(f"  danger {t:6.2f}s  {r['id']}")
            print(f"  danger total {sum(TIMES):.1f}s over {len(TIMES)} cases")
        if record and FAULTS:                                         # (f566) a turn rolled back is a round not fought: never the numbers kept
            print(f"shard {s}: not recorded, {len(FAULTS)} turn(s) rolled back by a fault (logs/crash.log has the tracebacks)")
            for l in fault_lines():
                print("  " + l)
            moved += 1
        elif record:
            _write(_path(s), {"header": header(), "cases": _norm(records), "coverage": cover})
            print(f"shard {s}: {len(records)} cases recorded")
        else:
            for l in fault_lines():
                print(f"  fault: {l}")
            lines = compare(s, records)
            moved += sum(1 for l in lines if not l.startswith("warning"))
            print(f"shard {s}: {len(records)} cases, " + (f"{sum(1 for l in lines if not l.startswith('warning'))} moved" if lines else "all as recorded"))
            for l in lines:
                print("  " + l)
    if record and set(shards) == set(range(SHARDS)):
        _write(OUT / "sheets.json.gz", {"header": header(), "sheets": _norm(sheets())})
        print("sheets recorded")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main())


def families() -> set[str]:
    """Every creature family the bestiary has."""
    from world.loader import load_world
    return {getattr(c, "family", "") or "?" for c in load_world().bestiary.values()}


def kept_coverage() -> dict:
    """What the recorded grid covered, over every shard."""
    cov: dict[str, set] = {}
    for s in range(SHARDS):
        path = _path(s)
        if path.exists():
            for k, v in _read(path).get("coverage", {}).items():
                cov.setdefault(k, set()).update(v)
    return cov


def shard_test(shard: int, check) -> None:
    """A suite test for one shard (tools/sim/fight_fixtures_494*_test.py): every case of it plays to its recorded numbers."""
    records, _ = play(shard)
    lines = compare(shard, records)
    moved = [l for l in lines if not l.startswith("warning")]
    for l in lines:
        if l.startswith("warning"):
            print("  " + l, file=sys.__stdout__)
    check(f"shard {shard}: every one of its {len(records)} fights plays to its recorded numbers", not moved, moved[:5])
    check(f"shard {shard}: no turn of its fights was rolled back by a fault (f566)", not FAULTS, fault_lines())
    check(f"shard {shard}: its cases are the grid's", sorted(r["id"] for r in records)
          == sorted(c["id"] for c in cases() if shard_of(c) == shard))
