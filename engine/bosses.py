"""Boss fights: legendary actions, legendary resistance, a signature move, a bloodied phase, a last stand, and a voice.

A boss is a Fighter with `boss` set (see make()). The combat engine calls the hooks here at the right moments:
  opening()        -> intro()
  enemy_turn()     -> refresh() at the start, own_turn() after its ordinary attack
  finish_round()   -> legendary() at the end of every other creature's turn
  add_status()     -> resisted()
  take_damage()    -> last_stand() before a killing blow lands, then after_damage() (bloodied, falling)
All numbers are in data/rules/bosses.yaml.
"""

import random
from pathlib import Path

import yaml

from engine import combat as C

B = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "bosses.yaml").read_text(encoding="utf-8"))


def kit_for(category: str) -> str:
    return B["category_kit"].get(category, "default")


def make(kit: str, tier: str, name: str, lines: dict | None = None) -> dict:
    """The boss state carried on a Fighter. `lines` (intro, bloodied, last_stand, fall) override the kit's own."""
    k = B["kits"].get(kit) or B["kits"]["default"]
    t = B["tiers"][tier]
    nm = name[:1].upper() + name[1:]
    spoken = {**k["lines"], **{key: v for key, v in (lines or {}).items() if v}}
    return {"kit": kit if kit in B["kits"] else "default", "tier": tier, "la": t["actions"], "la_max": t["actions"], "lr": t["resist"],
            "phase": 0, "stand_used": False, "fell": False, "sig_ready": False, "guards": 0,
            "lines": {key: v.replace("{name}", nm) for key, v in spoken.items()}}


BEAT = {"intro": "BOSS ENTRANCE", "bloodied": "BOSS TURNING POINT - it is badly hurt and changes",
        "last_stand": "BOSS LAST STAND - it should be dead and is not", "fall": "BOSS FALLS"}


def _say(combat, f, key: str) -> None:
    """Tell a beat of the fight, and what the boss says in it. The narrator is told which beats are set-pieces (see combat_prompts)."""
    line = f.boss["lines"].get(key)
    C.tell(combat, f"{BEAT[key]}: {C.who(f)}" + (f' says aloud: "{line}"' if line else ""))
    if line:
        combat.log.append(line)


def _kit(f):
    return B["kits"][f.boss["kit"]]


def _text(f, template: str) -> str:
    nm = f.name[:1].upper() + f.name[1:]
    return template.replace("{name}", nm)


def _targets(combat):
    return [t for t in [combat.player] + combat.allies() if t.alive]


def intro(combat, rng) -> None:
    for e in combat.enemies():
        if e.boss:
            _say(combat, e, "intro")


def refresh(e) -> None:
    e.boss["la"] = e.boss["la_max"]


def resisted(combat, f, status: str) -> bool:
    """Legendary resistance: a boss turns aside the first few attempts to stun, frighten or pin it."""
    if not f.boss or status not in B["negative_statuses"] or f.boss["lr"] <= 0:
        return False
    f.boss["lr"] -= 1
    left = f.boss["lr"]
    combat.log.append(f"{f.name} resists ({status}); {left} resistance(s) left")
    C.tell(combat, f"{C.who(f)} {C.vb(f, 'shrug', 'shrugs')} off the {status} like a man shaking off rain"
           + (" - but that was the last time it will" if left == 0 else ""))
    return True


def last_stand(combat, f) -> bool:
    """The first killing blow does not kill: the boss stays up, hurt and dangerous. Returns True if it did."""
    if not f.boss or f.boss["stand_used"] or not B["tiers"][f.boss["tier"]]["last_stand"]:
        return False
    cfg = B["last_stand"]
    f.boss["stand_used"] = True
    f.boss["phase"] = 3
    f.hp = max(1, round(f.max_hp * cfg["hp_pct"] / 100))
    f.statuses.clear()
    f.weapon_damage *= cfg["damage"]
    f.boss["la"] = f.boss["la_max"]
    f.boss["sig_ready"] = True
    combat.log.append(f"{f.name} makes a last stand")
    _say(combat, f, "last_stand")
    return True


def after_damage(combat, f) -> None:
    """Called after a boss has taken damage: the bloodied turn, and the fall."""
    if not f.boss:
        return
    if f.hp <= 0:
        if not f.boss["fell"]:
            f.boss["fell"] = True
            _say(combat, f, "fall")
        return
    if f.boss["phase"] == 0 and f.hp <= f.max_hp * B["bloodied_at"]:
        cfg = B["bloodied"]
        f.boss["phase"] = 1
        f.weapon_damage *= cfg["damage"]
        f.shield += f.max_hp * cfg["shield_pct"] / 100
        f.boss["sig_ready"] = True
        combat.log.append(f"{f.name} is bloodied")
        _say(combat, f, "bloodied")


def _strike(combat, e, target, mult: float, rng, label: str = "strikes") -> bool:
    return C.apply_damage(combat, e, target, mult, label, rng, can_cleave=False, can_riposte=False, can_flurry=False)


def _weakest(combat):
    return min(_targets(combat), key=lambda t: t.hp / max(1, t.max_hp))


def _guards(combat, e, n: int) -> int:
    made = 0
    for _ in range(n):
        if e.boss["guards"] >= B["max_guards"]:
            break
        e.boss["guards"] += 1
        g = e.model_copy(deep=True)
        g.id = f"{e.id}_guard{e.boss['guards']}"
        g.name = f"one of {e.name}'s guard"
        g.boss, g.spawn, g.rank = {}, "", "normal"
        g.max_hp = g.hp = max(1, round(e.max_hp * B["guard_share"]))
        g.weapon_damage = e.weapon_damage * 0.5
        g.shield, g.statuses, g.cooldowns, g.band = 0, {}, {}, "near"
        combat.fighters.append(g)
        made += 1
    return made


def _do(combat, e, opt: dict, rng, mult: float) -> None:
    """Carry out one legendary or signature option."""
    kind = opt["kind"]
    combat.log.append(f"{e.name}: {opt['name']}")
    C.tell(combat, ("BOSS SIGNATURE MOVE: " if opt is _kit(e)["signature"] else "BOSS ACTS BETWEEN TURNS: ") + _text(e, opt["text"]))
    targets = _targets(combat)
    if not targets:
        return
    if kind == "strike":
        _strike(combat, e, combat.player if rng.random() < 0.7 or len(targets) == 1 else rng.choice(targets), mult or B["legendary_strike"], rng)
    elif kind == "smite":
        _strike(combat, e, _weakest(combat), mult or B["legendary_strike"] * 1.8, rng, "smites")
    elif kind == "rend":
        t = combat.player
        if _strike(combat, e, t, mult or B["legendary_strike"] * 1.3, rng, "rends") and t.alive:
            C.add_status(combat, t, "bleeding", 3)
    elif kind == "sweep":
        for t in targets:
            _strike(combat, e, t, mult, rng, "engulfs")
    elif kind == "cow":
        t = combat.player
        if not C.resist(e, t, ["charisma", "wisdom"], rng) and opt.get("status") not in t.statuses:
            if C.add_status(combat, t, opt["status"], 2):
                C.tell(combat, f"you are {opt['status']}")
        else:
            C.tell(combat, "you hold firm against it")
    elif kind == "bolster":
        e.shield += e.max_hp * 0.05
    elif kind == "mend":
        heal = round(e.max_hp * 0.06)
        e.hp = min(e.max_hp, e.hp + heal)
        C.tell(combat, f"its wounds close ({heal})")
    elif kind == "summon":
        n = _guards(combat, e, 2)
        e.shield += e.max_hp * 0.03
        if not n:
            _strike(combat, e, combat.player, 1.0, rng)


def legendary(combat, rng) -> None:
    """One legendary action, taken at the end of someone else's turn."""
    for e in combat.enemies():
        if not e.boss or e.boss["la"] <= 0 or {"stunned", "prone"} & set(e.statuses):
            continue
        opts = [o for o in _kit(e)["legendary"] if o["cost"] <= e.boss["la"]]
        if not opts:
            continue
        weights = []
        for o in opts:
            w = 1.0
            if o["kind"] == "mend":
                w = 2.5 if e.hp < e.max_hp * 0.7 else 0.0
            elif o["kind"] == "bolster":
                w = 1.5 if e.shield <= 0 else 0.1
            elif o["kind"] == "cow":
                w = 0.2 if o.get("status") in combat.player.statuses else 1.0
            elif o["kind"] == "smite":
                w = 1.4
            weights.append(w)
        if sum(weights) <= 0:
            continue
        o = rng.choices(opts, weights=weights)[0]
        e.boss["la"] -= o["cost"]
        _do(combat, e, o, rng, 0.0)
        if not combat.player.alive:
            return


def own_turn(combat, e, target, rng) -> None:
    """After its ordinary attack on its own turn: the extra blow, and the signature move when it comes round."""
    t = B["tiers"][e.boss["tier"]]
    if t["extra"] > 0 and target.alive:
        _strike(combat, e, target, t["extra"], rng, "follows through")
    due = combat.round >= 2 and (combat.round - 2) % B["signature_every"] == 0
    if (due or e.boss["sig_ready"]) and combat.player.alive:
        e.boss["sig_ready"] = False
        sig = _kit(e)["signature"]
        _do(combat, e, sig, rng, sig.get("mult", 0.0))
