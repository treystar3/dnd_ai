"""Plays a character from level 1 toward level 75 with the real engine and a stand-in model.

    python simbot.py <warrior|mage|summoner|artisan> <seed> [max_days] [max_steps] [wall_seconds]

Writes sim_out/<class>.jsonl (events) and sim_out/<class>_summary.json.
"""

import collections
import io
import json
import random
import shutil
import sys
import time
import traceback
from pathlib import Path
import os

CLS = sys.argv[1]
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 1
MAX_DAYS = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
MAX_STEPS = int(sys.argv[4]) if len(sys.argv) > 4 else 60000
WALL = float(sys.argv[5]) if len(sys.argv) > 5 else 3300.0
TARGET = int(os.environ.get("SIM_TARGET", 75)) if "os" in globals() else 75
HALL = os.environ.get("SIM_HALL", "guild_house")
OUT = Path("sim_out"); OUT.mkdir(exist_ok=True)

import simlib
STUB = simlib.Stub(CLS, SEED)
simlib.install(STUB)
if os.environ.get('SIM_KIND'):
    from engine import events as _ev
    for _k in _ev.C['kinds']:
        _ev.C['kinds'][_k]['weight'] = 1000 if _k == os.environ['SIM_KIND'] else 0

import ui.console as uc
NOTES = collections.deque(maxlen=80)
NOTE_COUNTS = collections.Counter()
ROAD = collections.Counter()


def _note(m, *a, **k):
    s = str(m)
    NOTES.append(s)
    if s.startswith("On the road - "):
        ROAD["events"] += 1
    elif s.startswith("You stop here, on the road"):
        ROAD["stops"] += 1
    elif s.startswith("You find somewhere new"):
        ROAD["found_places"] += 1
    elif s.startswith("You find a way"):
        ROAD["found_tracks"] += 1
    elif s.startswith("You get your breath back"):
        ROAD["resumed_after_fight"] += 1
    elif s.startswith("You take:"):
        ROAD["finds"] += 1
    elif s.startswith("It costs you"):
        ROAD["hazard_costs"] += 1
    NOTE_COUNTS[s.split(":")[0][:36]] += 1


uc.note = _note
for _n in ("narrate", "wait", "debug", "combat_panel", "show_status", "show_header"):
    if hasattr(uc, _n):
        setattr(uc, _n, lambda *a, **k: None)
uc.ask = lambda *a, **k: "y"
sys.stdout = io.StringIO()   # the game prints a lot; the bot reads state, not the screen

from core.models import Character
from engine import (events as bigev, deeds as deedlog, arcs, checks, clock, combat, crafting, dungeons, encounters, equipment, inventory as inv, items, leveling,
                    money, pools, pulse, quests)
from llm.gateway import LLMError
from npc.life import populate_place
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
import os
LAST_DANGER = [("?", 0.5)]
_orig_danger = combat.danger


def _danger(cmb, runs=80, seed=0):
    r = _orig_danger(cmb, runs=24, seed=seed)
    LAST_DANGER[0] = r
    return r


combat.danger = _danger

CUM = [0]
for _lv in range(1, 200):
    CUM.append(CUM[-1] + leveling.xp_to_next(_lv))
TIER = {"light": 1, "moderate": 2, "heavy": 3}
CONSUMABLE_GOODS = {"healing_draught", "mana_tonic", "bandage", "trail_ration"}


def total_xp(c) -> int:
    return CUM[c.level - 1] + c.xp


def p_hp(f) -> float:
    return f.player.hp / max(1, f.player.max_hp)


IMMORTAL = os.environ.get("SIM_IMMORTAL") == "1"
NORUN = os.environ.get("SIM_NORUN") == "1"          # the bot never flees a fight: it fights to the end whatever the odds
LIVE_FIGHT = [False]          # the player is only kept alive in a real fight, never inside the danger estimate
WOULD_DIE: list = []          # filled while the player is kept alive; read and cleared by fight_out
if IMMORTAL:
    _fighter_setattr = combat.Fighter.__setattr__

    def _immortal_setattr(self, name, value):
        if name == "hp" and LIVE_FIGHT[0] and getattr(self, "side", "") == "player" and value <= 0:
            WOULD_DIE.append(getattr(self, "max_hp", 0))
            value = max(1.0, self.max_hp * 0.3)           # carried on at 30% health so the fight still plays out
        _fighter_setattr(self, name, value)
    combat.Fighter.__setattr__ = _immortal_setattr


class Bot:
    def __init__(self):
        self.rng = random.Random(SEED)
        self.world = load_world()
        shutil.rmtree(f"saves/sim_{CLS}", ignore_errors=True)
        self.store = CampaignStore.open_or_create(f"sim_{CLS}")
        self.store.meta.seed = SEED
        self.store.meta.turn = 1
        self.store.meta.minutes = 8 * 60
        self.store.save_meta()
        char, self.spec = simlib.make_character(CLS, self.rng, perks=True)       # the bots play with the perks a player would draw
        start = self.world.start_location
        self.store.save_player(PlayerState(character=char, location=start))
        self.ws = WorldScene(self.store, self.world, load_traits(), self.store.load_player())
        _orig_after = self.ws.party_after_fight
        def _count_fallen(fallen, *rest, _o=_orig_after, _bot=self):
            _bot.party_tally["fell"] += sum(1 for m in _bot.ws.player.party if f"ally_{m['id']}" in {a.id for a in fallen})
            _o(fallen, *rest)
        self.ws.party_after_fight = _count_fallen
        self.rarity_tally = collections.Counter()
        self.trials = []
        self.mana_stats = []
        self.legendaries = []
        _orig_pack = self.ws.to_pack
        def _tracked_pack(item, why="", _o=_orig_pack, _bot=self):
            if not item.good and items.base_of(item).slot != "none":
                _bot.rarity_tally[item.rarity] += 1
                if item.rarity == "legendary":
                    _bot.legendaries.append({"day": _bot.day, "lv": _bot.c.level, "name": item.name, "base": item.base,
                                             "effect": item.legendary_effect, "where": _bot.ws.player.location,
                                             "delve": bool(_bot.ws.player.delve), "titled": bool(getattr(item, "title", ""))})
            _o(item, why)
        self.ws.to_pack = _tracked_pack
        if os.environ.get("SIM_PHOENIX"):
            robe = items.make("robe", "legendary", 10, rng=random.Random(5)); robe.legendary_effect = "phoenix"; robe.name = "Test Shroud"
            self.ws.player.character.equipment["body"] = robe
        if os.environ.get("SIM_START_LEVEL"):           # jump ahead: a character who is already deep into the game
            target = int(os.environ["SIM_START_LEVEL"])
            while self.ws.player.character.level < target:
                leveling.gain_xp(self.ws.player.character, leveling.xp_to_next(self.ws.player.character.level))
            if os.environ.get("SIM_COINS"):
                self.ws.player.character.coins = int(os.environ["SIM_COINS"])
            if os.environ.get("SIM_RANK"):
                self.ws.player.guild_rank = os.environ["SIM_RANK"]
            if os.environ.get("SIM_START_AT"):
                start = os.environ["SIM_START_AT"]
        STUB.bot = self
        self.log_f = open(OUT / f"{CLS}.jsonl", "w")
        self.steps = 0
        self.fights = []
        self.deaths = []
        self.would_deaths = []
        self.tame_tries = 0
        self.zone_ban = {}
        self.cat_minutes = collections.Counter()
        self.income = collections.Counter()
        self.spend = collections.Counter()
        self.xp_src = collections.Counter()
        self.milestones = {}
        self.exceptions = {}
        self.exc_run = [None, 0]
        self.violations = {}
        self.blocked = 0
        self.enchants = []
        self.travel = []
        self.quest_log = []
        self.arc_log = []
        self.prisoner_seen = self.prisoner_spared = self.prisoner_killed = 0
        self.camp_tally = collections.Counter()
        self.party_tally = collections.Counter()
        self.wealth_buys = []
        self.dungeon_log = []
        self.tours = {}
        self.visited = collections.OrderedDict()
        self.last_day = -1
        self.last_guild_day = -99
        self.last_talk_day = -99
        self.big_log = []
        self.big_cool = {}
        self.npc_stats = collections.Counter()
        self.befriended = {}
        self.fight_coins = 0
        self.fight_xp = 0
        self.last_rate = 0.5
        self.flee_below = 0.3
        self.fled_open = False
        self.aborted = ""
        self.kills_by_place = collections.Counter()
        self.sells_refused = collections.Counter()
        self.t0 = time.time()
        self.ws.enter(start)

    # ------------------------------------------------------------ small helpers
    @property
    def c(self) -> Character:
        return self.ws.player.character

    @property
    def pack(self):
        return self.c.inventory

    @property
    def day(self) -> int:
        return clock.day(self.ws.minutes)

    @property
    def loc(self) -> str:
        return self.ws.player.location

    def frac(self, pool: str) -> float:
        return pools.current(self.c, pool) / max(1, pools.maximum(self.c, pool))

    def log(self, kind, **kw):
        rec = {"k": kind, "d": self.day, "lv": self.c.level, "loc": self.loc}
        rec.update(kw)
        self.log_f.write(json.dumps(rec, default=str) + "\n")

    def pulse_watch(self):
        """Record what the world's pulse does and what the character is in the middle of: threads starting, moving and ending,
        and, on reaching a town, what is going on there."""
        ws = self.ws
        st = self.store.load_world_state() or {}
        seen = self.__dict__.setdefault("pulse_seen", {})
        now = ws.minutes

        def eff(e):
            return {k: e[k] for k in ("kind", "place", "value", "days", "text", "npc", "role") if e.get(k)}

        for th in st.get("threads", []):
            key = th["id"]
            prev = seen.get(key)
            if prev is None:
                self.log("pulse", ev="start", tier=th["tier"], title=th["title"], at=th["place"], pressure=th.get("pressure"),
                         stages=len(th["stages"]), span_days=round((th["times"][-1] - th["times"][0]) / 1440, 1),
                         news=[n["text"] for n in st.get("news", [])[-1:]], first=th["stages"][0]["description"],
                         effects=[eff(e) for e in th["stages"][0]["effects"]], groups=th["groups"], pday=clock.day(th["made"]))
            elif th["stage"] != prev[0] and th["stage"] > 0:
                stg = th["stages"][th["stage"]]
                self.log("pulse", ev="stage", tier=th["tier"], title=th["title"], at=th["place"], stage=th["stage"] + 1,
                         text=stg["description"], effects=[eff(e) for e in stg["effects"]])
            if prev is not None and th["status"] != prev[1]:
                end = next((h["text"] for h in reversed(st.get("history", [])) if h["text"].startswith(th["title"])), "")
                self.log("pulse", ev="end", tier=th["tier"], title=th["title"], at=th["place"], status=th["status"], result=th.get("result"), fallen=th.get("fallen"), text=end,
                         fallout=[eff(e) for e in th["fallout"]["effects"]] if th["status"] == "ended" else [])
            seen[key] = (th["stage"], th["status"])
        town = pulse.town_of(self.world, self.loc)
        if self.world.places[town].type not in ("village", "town", "city"):
            self.pulse_town = None
        elif self.__dict__.get("pulse_town") != town:
            self.pulse_town = town
            here = [x["title"] for x in st.get("threads", []) if x["status"] == "active" and pulse.town_of(self.world, x["place"]) == town]
            fx = [{"kind": e["kind"], "value": e.get("value"), "days_left": round((e["until"] - now) / 1440, 1)}
                  for e in st.get("effects", []) if e["until"] > now and e.get("place") == town and e["kind"] in ("prices", "danger", "closed")]
            news = [n["text"] for n in st.get("news", []) if now - n["minute"] < 14 * 1440 and "everyone" in n["groups"]
                    and n["minute"] + pulse.travel_delay(self.world, n["origin"], self.loc) <= now][-3:]
            self.log("pulse", ev="arrive", town=town, situations=here, effects=fx, news=news,
                     contracts=len([q for q in ws.player.quests if q.get("thread")]))

    def count_good(self, gid: str) -> int:
        return inv.count_of(self.pack, gid)

    # ------------------------------------------------------------ acting in the world
    def act(self, intent: dict, text: str = "go", cat: str = "other"):
        ws = self.ws
        STUB.plan = [intent]
        m0, coins0, xp0 = ws.minutes, self.c.coins, total_xp(self.c)
        self.fight_coins = self.fight_xp = 0
        self.steps += 1
        try:
            ws.handle(text)
        except LLMError as e:
            self.note_exc("LLMError", str(e)[:120], None)
        ws.store.save_player(ws.player)
        if ws.combat:
            self.fight_out()
            if ws.player.prisoners:
                self.handle_prisoners()
        self.level_check()
        self.cat_minutes[cat] += max(0, ws.minutes - m0)
        d_coins = self.c.coins - coins0 - self.fight_coins
        if d_coins > 0:
            self.income[cat] += d_coins
        elif d_coins < 0:
            self.spend[cat] += -d_coins
        d_xp = total_xp(self.c) - xp0 - self.fight_xp
        if d_xp > 0:
            self.xp_src[cat] += d_xp
        self.tick()
        self.check_invariants()

    def tick(self):
        d = self.day
        if d != self.last_day:
            self.last_day = d
            c = self.c
            self.log("tick", xp=total_xp(c), coins=c.coins, rank=self.ws.player.guild_rank, deaths=c.deaths,
                     hp=round(self.frac("health"), 2), q=len(self.ws.player.quests))
        for lv in range(10, 170, 5):
            if self.c.level >= lv and lv not in self.milestones:
                self.milestones[lv] = {"day": self.day, "steps": self.steps, "deaths": self.c.deaths,
                                       "secs": round(time.time() - self.t0)}

    MONK_GIFTS = [(12, "ki_strike"), (35, "open_palm"), (60, "flowing_step"), (90, "still_water"), (120, "ki_strike")]

    def monk_gift(self):
        """Legendary wraps are rare drops; so the monk's effects get exercised, a monk bot comes across one at set levels and wears it if it is better."""
        if CLS != "monk":
            return
        c = self.c
        done = getattr(self, "_gifts", 0)
        if done < len(self.MONK_GIFTS) and c.level >= self.MONK_GIFTS[done][0]:
            lv, effect = self.MONK_GIFTS[done]
            from engine import loot as _loot
            it = items.make("hand_wraps", "legendary", c.level, rng=self.rng)
            _loot.roll_gear(it, self.rng)
            it.legendary_effect = effect
            c.inventory.append(it)
            self._gifts = done + 1
            self.log("monk_wraps", effect=effect, ilvl=c.level)

    def level_check(self):
        self.monk_gift()
        c = self.c
        if c.unspent_points <= 0:
            return
        names = list(self.spec["per_level"])
        weights = [self.spec["per_level"][a] for a in names]
        spend = {}
        left = c.unspent_points
        while left > 0:
            for a, w in zip(names, weights):
                give = min(w, left)
                if give:
                    spend[a] = spend.get(a, 0) + give
                    left -= give
        err = leveling.check_allocation(c, spend)
        if err:
            self.violation("allocate", err)
            return
        leveling.allocate(c, spend)

    # ------------------------------------------------------------ fighting
    def combat_choice(self) -> dict:
        ws = self.ws
        f = ws.combat.fight
        p = f.player
        c = self.c
        enemies = f.enemies()
        if not enemies:
            return {"kind": "attack", "target": ""}
        from engine import battlefield as bf
        tgt = min(enemies, key=lambda e: (e.hp, 0 if bf.attack_access(f, p, e).ok else 1))
        hpf = p.hp / max(1, p.max_hp)
        base = {"target": tgt.id, "summary": "bot"}
        if not NORUN and not f.player_acted and f.round == 1 and self.last_rate < self.flee_below:
            self.fled_open = True
            return dict(base, kind="flee")
        if c.uses_companions:
            from engine import taming
            weak = [e for e in enemies if e.hp <= e.max_hp * taming.T["max_health_share"]
                    and not taming.check(c, e, self.world.bestiary.get(e.creature))]
            if weak and hpf > 0.3 and self.tame_tries < 4:
                self.tame_tries += 1
                return dict(base, kind="tame", target=weak[0].id)
        pots = [i for i in c.inventory if i.good == "healing_draught"]
        if hpf < 0.4 and pots:
            return dict(base, kind="item", item="healing draught")
        if not NORUN and hpf < 0.2 and f.round > 2:
            return dict(base, kind="flee")
        moves = [m for m in p.moves if not combat.can_use(p, m, f)]
        allies = [x for x in f.fighters if x.side == "ally"]
        for m in moves:
            if m.effect == "summon" and (not allies or all(a.hp < a.max_hp * 0.4 for a in allies)):
                return dict(base, kind="ability", ability=m.id)
        for m in moves:
            if m.effect == "command" and allies and any(a.alive for a in allies):
                return dict(base, kind="ability", ability=m.id)
        if hpf < 0.5:
            for m in moves:
                if m.effect == "healing":
                    return dict(base, kind="ability", ability=m.id)
        for m in moves:                                   # a ring's or amulet's power: free, so it is spent when it helps
            if m.effect != "relic":
                continue
            kind, pid = m.relic["kind"], m.relic["id"]
            if kind in ("mend", "barrier") and hpf >= 0.6:
                continue
            if pid == "deathless" and hpf >= 0.35:
                continue
            if kind == "font" and not (p.max_mana and p.mana < p.max_mana * 0.5):
                continue
            if kind == "reset" and not p.cooldowns:
                continue
            return dict(base, kind="ability", ability=m.id)
        foes_near = [x for x in f.fighters if x.side == "enemy" and x.alive]
        for m in moves:                                   # a buff goes up before the blows, once, if the fight is worth it
            if m.effect == "buff" and m.id not in p.buffs and not p.counters.get("buffed_" + m.id) and foes_near and getattr(self, "last_rate", 1) < 0.9:
                if m.buff == "mend" and hpf > 0.85:
                    continue
                if not any(b.get("kind") == m.buff for b in p.buffs.values()):
                    p.counters["buffed_" + m.id] = 1
                    return dict(base, kind="ability", ability=m.id)
        dmg = [m for m in moves if m.effect == "damage"]
        if dmg:
            best = max(dmg, key=lambda m: TIER.get(m.tier, 1))
            return dict(base, kind="ability", ability=best.id, move="closer")
        return dict(base, kind="attack", move="closer")

    def fight_out(self):
        self.tame_tries = 0
        ws = self.ws
        f = ws.combat.fight
        c = self.c
        coins0, xp0, deaths0, hp0 = c.coins, total_xp(c), c.deaths, p_hp(f)
        before = {i.uid for i in c.inventory}
        foes = [(e.creature, e.level, e.rank) for e in f.enemies()]
        allies0 = [m['name'] for m in ws.player.party if m.get('npc')]
        spawn0 = [getattr(e, 'spawn', '') for e in f.enemies() if getattr(e, 'spawn', '')]
        label, rate = LAST_DANGER[0]
        self.last_rate = rate
        WOULD_DIE.clear()
        place = self.loc
        m0 = ws.minutes
        self.fled_open = False
        rounds = 0
        in_dungeon = bool(ws.player.delve)
        mana0 = f.player.mana / max(1, f.player.max_mana) if f.player.max_mana else None
        mana_min, dry = mana0, 0
        LIVE_FIGHT[0] = True
        while ws.combat and rounds < 250:
            rounds += 1
            if mana0 is not None:
                pl = f.player
                mana_min = min(mana_min, pl.mana / max(1, pl.max_mana))
                spells = [m for m in pl.moves if m.resource == "mana"]
                if spells and all((combat.can_use(pl, m, f) or "").startswith("Not enough") for m in spells):
                    dry += 1
            try:
                ws.handle("fight")
            except LLMError as e:
                self.note_exc("LLMError(combat)", str(e)[:100], None)
                break
            self.steps += 1
        LIVE_FIGHT[0] = False
        if ws.combat:
            self.violation("combat_stuck", f"fight did not end after {rounds} rounds at {place}")
            ws.combat = None
        died = c.deaths > deaths0
        outcome = "defeat" if died else ("fled" if f.over == "fled" else ("victory" if f.over == "victory" else str(f.over)))
        gained_xp = max(0, total_xp(c) - xp0) if not died else 0
        gained_coin = max(0, c.coins - coins0) if not died else 0
        found = [(i.rarity, i.name) for i in c.inventory if i.uid not in before and not i.good]
        goods = [i.name for i in c.inventory if i.uid not in before and i.good]
        self.fight_coins += gained_coin
        self.fight_xp += gained_xp
        self.income["fights"] += gained_coin
        self.xp_src["fights"] += gained_xp
        self.cat_minutes["fighting"] += max(0, ws.minutes - m0)
        if mana0 is not None:
            self.mana_stats.append((round(mana0, 2), round(mana_min, 2), dry, rounds))
        used = {k: v for k, v in f.player.relic_uses.items()}
        thr = any(x.id == "thrall" for x in f.fighters)
        rec = dict(place=place, foes=foes, relics_used=used, thrall=thr, rating=round(rate, 2), label=label, outcome=outcome, rounds=rounds,
                   xp=gained_xp, coins=gained_coin, items=found, goods=goods, hp_lost=round(max(0, hp0 - p_hp(f)), 2),
                   lv=c.level, dungeon=in_dungeon, fled_open=self.fled_open, realm_allies=allies0, event_spawn=bool(spawn0))
        rec["would_die"] = len(WOULD_DIE)
        self.fights.append(rec)
        self.log("fight", **{k: v for k, v in rec.items() if k != "lv"})
        if WOULD_DIE:
            self.would_deaths.append({"d": self.day, "lv": c.level, "place": place, "foes": foes, "rate": round(rate, 2), "times": len(WOULD_DIE), "outcome": outcome})
            self.log("would_die", place=place, foes=foes, rate=round(rate, 2), times=len(WOULD_DIE), outcome=outcome)
        if outcome == "victory":
            self.kills_by_place[place] += len(foes)
        if outcome == "defeat":
            self.on_death(place, foes, rate)
        elif outcome == "fled" and rate < 0.4:
            self.zone_ban[place] = c.level + 2

    def on_death(self, place, foes, rate):
        c = self.c
        self.deaths.append({"d": self.day, "place": place, "foes": foes, "rate": round(rate, 2), "lv": c.level})
        self.zone_ban[place] = c.level + 3
        self.log("death", place=place, foes=foes, rate=round(rate, 2))

    # ------------------------------------------------------------ moving
    def goto(self, dest: str, cat="travel") -> bool:
        if self.loc == dest:
            return True
        deaths0 = self.c.deaths
        for attempt in range(5):
            before, t0 = self.loc, self.ws.minutes
            self.act({"kind": "move", "destination": dest}, f"go to {dest}", cat)
            if self.c.deaths > deaths0:
                return False
            if self.loc == dest:
                self.travel.append({"from": before, "to": dest, "min": self.ws.minutes - t0, "d": self.day})
                self.arrived(dest)
                return True
            if self.loc == before:
                self.blocked += 1
                self.log("blocked", dest=dest, note=NOTES[-1][:90] if NOTES else "")
                self.act({"kind": "wait", "wait_minutes": 180}, "wait", "rest")
        return self.loc == dest

    def arrived(self, pid):
        if pid not in self.visited:
            self.visited[pid] = {"day": self.day, "lv": self.c.level}
            self.log("first_visit", place=pid)
        p = self.world.places.get(pid)
        if p and not p.danger and p.type != "dungeon":
            self.town_services()

    def path_minutes(self, a, b):
        r = self.world.path(a, b)
        return r[1] if r else None

    # ------------------------------------------------------------ town: gear, selling, potions, training
    def score(self, it) -> float:
        """How good a piece of gear is: its damage or protection, lifted by its properties and legendary effect. (It used to be
        its price, which let a level-14 legendary outrank a level-130 weapon.)"""
        if not it:
            return 0.0
        if os.environ.get("SIM_PRICE_SCORE"):
            return float(items.price(it))
        try:
            v = items.value(it) or 5 * items.scale(it)
            b = items.base_of(it)
            if getattr(b, "attributes", None) and getattr(b, "reach", None):
                ch = self.ws.player.character
                v += max(getattr(ch.attributes, a, 10) for a in b.attributes) * combat.RULES["damage"]["attribute_bonus"]
            mags = sum(abs(e.magnitude) for e in items.effects(it)) + sum(abs(p.magnitude) for p in getattr(it, "properties", []) if hasattr(p, "magnitude") and False)
            lift = (1.5 if it.relic else 1.0) * (1.3 if it.trait and it.trait.get("fight") else 1.0)
            return float(v) * (1 + mags / 150) * (1.15 if it.legendary_effect else 1.0) * lift
        except Exception:
            return float(items.price(it))

    def gear_pass(self) -> int:
        c = self.c
        n = 0
        for it in list(c.inventory):
            if it.good or it.base == "raw_material":
                continue
            try:
                b = items.base_of(it)
            except Exception:
                continue
            if b.slot == "none":
                continue
            if b.slot == "ring":
                rings = [c.equipment.get("ring_1"), c.equipment.get("ring_2")]
                cur = None if None in rings else min(rings, key=self.score)
            else:
                cur = c.equipment.get(b.slot)
            if self.score(it) > self.score(cur) * 1.1 and equipment.check(c, it) is None:
                if b.slot == "off_hand" and equipment.two_handed_equipped(c):
                    continue
                if self.steps % 5 == 0:
                    self.act({"kind": "equip", "item": it.name}, f"equip {it.name}", "shop")
                else:
                    equipment.equip(c, it)
                n += 1
        if n:
            self.log("gear", n=n, power=round(sum(self.score(i) for i in c.equipment.values())))
        return n

    def sell_pass(self):
        ws = self.ws
        if not any(self.world.roles[n.role].buys for n in ws.present):
            return
        if len(self.pack) < 6 and self.loc != HALL:
            return
        self.gear_pass()
        sold = 0
        for it in list(self.pack):
            if sold >= 24:
                break
            if it.good in CONSUMABLE_GOODS:
                continue
            if CLS in ("artisan", "smith") and it.base == "raw_material" and items.MATERIALS[it.material].family == "metal":
                continue
            key = inv.category(it)
            if self.sells_refused[(self.loc, key)] >= 2:
                continue
            n0 = len(self.pack)
            self.act({"kind": "sell", "item": it.name, "count": it.quantity}, f"sell {it.name}", "sales")
            sold += 1
            if len(self.pack) >= n0 and it in self.pack:
                self.sells_refused[(self.loc, key)] += 1

    def reserve(self) -> int:
        return 200 + 40 * self.c.level

    def buy_pass(self):
        ws = self.ws
        c = self.c
        try:
            offers = ws.stock_here()
        except Exception as e:
            self.note_exc("stock_here", repr(e)[:100], traceback.format_exc())
            return
        best = {}
        for npc, it, price in offers:
            try:
                b = items.base_of(it)
            except Exception:
                continue
            if b.slot == "none" or equipment.check(c, it) is not None:
                continue
            if b.slot == "off_hand" and equipment.two_handed_equipped(c):
                continue
            if b.slot == "ring":                  # the weaker of the two rings is the one a new ring would replace
                cur = min(self.score(c.equipment.get("ring_1")), self.score(c.equipment.get("ring_2")))
            else:
                cur = self.score(c.equipment.get(b.slot))
            if price <= c.coins - self.reserve() and self.score(it) > cur * 1.25 and self.score(it) > 0:
                gain = self.score(it) - cur
                if b.slot not in best or gain > best[b.slot][0]:
                    best[b.slot] = (gain, npc, it, price)
        for slot, (gain, npc, it, price) in list(best.items())[:4]:
            if price > c.coins - self.reserve():
                continue
            c0 = c.coins
            self.act({"kind": "buy", "target": npc.id, "ware": it.name, "item": it.name}, f"buy {it.name}", "gear")
            if c.coins < c0:
                self.log("bought", item=it.name, rarity=it.rarity, lvl=it.item_level, price=c0 - c.coins, slot=slot)
        self.gear_pass()
        if c.coins > 800:
            sellers = [n for n in ws.present if any(w.id == "healing_draught" for w in self.world.roles[n.role].sells)]
            tries = 0
            while sellers and self.count_good("healing_draught") < 4 and c.coins > 500 and tries < 6:
                tries += 1
                self.act({"kind": "buy", "target": sellers[0].id, "ware": "healing draught", "item": "healing draught"},
                         "buy potion", "potions")

    def train_pass(self):
        if self.loc != HALL or not self.ws.player.guild_rank or not self.ws.instructor_here():
            return
        c = self.c
        from scenes.training_actions import T
        if c.level < T["drills"]["max_level"] and c.last_drill_day != self.day and \
                c.coins > T["drills"]["fee_per_level"] * c.level + self.reserve():
            self.act({"kind": "train", "item": "drills"}, "drill", "training")
        if len(c.actives) < self.ws.ability_slots():
            fee = T["abilities"]["base_fee"] + T["abilities"]["fee_per_level"] * c.level
            if c.coins > fee + self.reserve():
                self.act({"kind": "train", "item": "teach me a new damaging technique"}, "learn", "training")
                opts = getattr(self.ws, "learn_options", None)
                if opts:
                    def val(i):
                        t = opts[i].tier
                        return (getattr(getattr(opts[i], "effect", None), "value", "") == "damage", TIER.get(t.value if hasattr(t, "value") else t, 1))
                    best = max(range(len(opts)), key=val)
                    self.act({"kind": "learn_ability", "item": str(best + 1)}, "choose", "training")
        for skill in ("insight", "perception"):
            if c.trained.get(skill, 0) < 6 and c.coins > 3 * self.reserve():
                self.act({"kind": "train", "item": skill}, f"tutor {skill}", "training")

    def enchant_pass(self):
        """Pay a town enchanter to enchant worn gear: best affordable option per item, keeping a purse reserve."""
        ws, c = self.ws, self.c
        if not any(n.role == "enchanter" for n in ws.present):
            return
        from engine import enchanting
        for it in list(c.equipment.values()):
            for _ in range(3):
                if len(it.enchantments) >= enchanting.slots(it):
                    break
                opts = [o for o in enchanting.available(c, it) if enchanting.check(c, it, o) is None
                        and enchanting.fee(it, o) <= max(0, c.coins - self.reserve())]
                if not opts:
                    break
                o = max(opts, key=lambda o: (bool(o.reagent), -enchanting.fee(it, o)))
                before = c.coins
                ok, msg = enchanting.enchant(c, it, o, self.rng)
                self.enchants.append({"d": self.day, "item": it.name, "opt": o.name, "ok": ok, "fee": before - c.coins})
                self.log("enchant", item=it.name, opt=o.name, ok=ok)
                self.spend["enchant"] += before - c.coins

    def town_services(self):
        """Run every service pass where the shops are: at the settlement itself, then in its market and workshop."""
        if getattr(self, "_servicing", False):
            return
        self._servicing = True
        try:
            self._town_services()
        finally:
            self._servicing = False

    def _town_services(self):
        here = self.world.places.get(self.loc)
        top = here
        while top and top.parent and top.parent in self.world.places:
            top = self.world.places[top.parent]
        spots = [self.loc]
        if top and self.loc != HALL and self.tours.get(top.id) != self.day:
            self.tours[top.id] = self.day                   # one round of the shops a day is plenty
            spots += [k for k, q in self.world.places.items()
                      if q.parent == top.id and k != self.loc and q.type in ("square", "shop", "smithy", "workshop", "yard")]
        origin = self.loc
        for spot in spots:
            if spot != self.loc and not self.goto(spot):
                continue
            self.town_pass()
        if self.loc != origin:
            self.goto(origin)

    def town_pass(self):
        try:
            self.sell_pass()
            self.buy_pass()
            self.enchant_pass()
            self.craft_pass()
            self.train_pass()
            self.wealth_pass()
        except LLMError as e:
            self.note_exc("LLMError(town)", str(e)[:100], None)

    def wealth_pass(self):
        """With gold to spare: a house where there is a land agent, a relic where there is a dealer."""
        from engine import property as prop
        ws, c = self.ws, self.c
        town = prop.town_of(self.world, self.loc)
        reserve = 20000
        agent = next((n for n in ws.present if n.role == "land_agent"), None)
        if agent and prop.for_sale(town) and town not in ws.player.homes and c.coins >= prop.P["homes"][town]["price"] + reserve:
            self.act({"kind": "buy", "ware": "house", "target": agent.id}, "buy a house", "wealth")
            if town in ws.player.homes:
                self.wealth_buys.append(("house", town, self.day))
        dealer = next((n for n in ws.present if self.world.roles[n.role].relics), None)
        if dealer:
            for item, price in prop.relics_in(ws.world, ws.store.meta.seed, town, ws.player.relics_bought):
                if c.coins >= price + reserve:
                    self.act({"kind": "buy", "ware": item.name, "target": dealer.id}, "buy a relic", "wealth")
                    if item.uid.replace("relic_", "") in ws.player.relics_bought:
                        self.wealth_buys.append(("relic", item.name, self.day))
                    break

    def craft_pass(self):
        """Artisans buy bars and craft gear when a forge and its smith are at hand."""
        if CLS not in ("artisan", "smith"):
            return
        ws = self.ws
        c = self.c
        place = ws.place
        sellers = [n for n in ws.present if any(w.kind == "material" for w in self.world.roles[n.role].sells)]
        if sellers and c.coins > self.reserve() + 900:
            ware = max((w for w in self.world.roles[sellers[0].role].sells if w.kind == "material"), key=lambda w: w.price)
            for _ in range(6):
                if c.coins < self.reserve() + ware.price:
                    break
                self.act({"kind": "buy", "target": sellers[0].id, "ware": ware.name, "item": ware.name}, "buy bars", "crafting")
        forge = place.stations.get("forge")
        if not forge or not any(n.role == forge["owner"] for n in ws.present):
            return
        for _ in range(4):
            mats = collections.Counter()
            for i in self.pack:
                if i.base == "raw_material" and items.MATERIALS[i.material].family == "metal":
                    mats[i.material] += i.quantity
            if not mats:
                return
            mat, have = max(mats.items(), key=lambda kv: items.MATERIALS[kv[0]].levels[0])
            options = [b for b in crafting.CRAFTABLE if b.family == "metal" and crafting.units_for(b) <= have
                       and b.slot in ("body", "main_hand", "head", "hands", "feet", "off_hand")]
            if not options:
                return
            base = max(options, key=lambda b: (b.slot == "body", crafting.units_for(b)))
            before = len(self.pack)
            self.act({"kind": "craft", "item": base.name}, f"craft {base.name}", "crafting")
            if not any(i.base == base.id for i in self.pack) and len(self.pack) >= before:
                return
            self.gear_pass()

    def mana_summary(self):
        m = self.mana_stats
        if not m:
            return {}
        n = len(m)
        rounds = sum(x[3] for x in m)
        return {"fights": n, "avg_start": round(sum(x[0] for x in m) / n, 2), "avg_low_point": round(sum(x[1] for x in m) / n, 2),
                "fights_hit_empty": sum(1 for x in m if x[1] < 0.1), "fights_with_dry_rounds": sum(1 for x in m if x[2]),
                "dry_round_share": round(sum(x[2] for x in m) / max(1, rounds), 3)}

    # ------------------------------------------------------------ resting
    def need_rest(self) -> bool:
        res = "mana" if self.spec["uses_magic"] else "stamina"
        return self.frac("health") < 0.55 or self.frac(res) < 0.12

    def nearest(self, pred):
        best = None
        for pid, p in self.world.places.items():
            if p.danger or p.type == "dungeon" or not pred(pid, p):
                continue
            m = self.path_minutes(self.loc, pid) if pid != self.loc else 0
            if m is not None and (best is None or m < best[0]):
                best = (m, pid)
        return best

    @staticmethod
    def has_inn(pid, p):
        return p.residents.get("innkeeper", 0) > 0

    def recover(self, local: bool = False):
        ws = self.ws
        c = self.c
        for _ in range(8):
            if not self.need_rest() and self.frac("health") > 0.8:
                return
            if self.count_good("healing_draught") >= 2 and self.frac("health") < 0.4 and self.loc != HALL:
                self.act({"kind": "use", "item": "healing draught"}, "drink", "rest")
                continue
            inn = None if local else self.nearest(self.has_inn)
            if inn and inn[0] <= 360 and self.loc != inn[1]:
                if not self.goto(inn[1], "travel"):
                    return
            keeper = next((n for n in ws.present if n.role == "innkeeper"), None)
            if keeper and c.coins >= 60:
                self.act({"kind": "buy", "target": keeper.id, "ware": "room", "item": "a room"}, "a room", "rest")
                self.act({"kind": "wait", "wait_minutes": 480}, "sleep", "rest")
            else:
                self.act({"kind": "wait", "wait_minutes": 480 if not ws.place.danger else 180}, "rest", "rest")

    # ------------------------------------------------------------ maintenance and rearming
    def unarmed(self) -> bool:
        return "main_hand" not in self.c.equipment

    def rearm(self):
        """After a death everything is gone: earn a little by honest work, then buy a weapon."""
        if not self.goto("parth"):
            return
        for _ in range(25):
            if not self.unarmed() or self.c.coins >= 400:
                break
            STUB.ask_help = True
            who = next(iter(self.ws.present), None)
            if not who:
                self.act({"kind": "wait", "wait_minutes": 120}, "wait", "work")
                continue
            self.act({"kind": "talk", "target": who.id, "speech": "Any work going?"}, "ask for work", "work")
            who = self.store.load_npc(who.id)
            if who.work_offer:
                self.act({"kind": "work", "target": who.id}, "do the work", "work")
            else:
                self.act({"kind": "wait", "wait_minutes": 60}, "wait", "work")
        STUB.ask_help = False
        for place in (HALL, "parth"):
            if self.unarmed() and self.goto(place):
                self.buy_for_weapon()

    def buy_for_weapon(self):
        c = self.c
        offers = [(n, i, p) for n, i, p in self.ws.stock_here() if items.base_of(i).slot == "main_hand" and p <= c.coins
                  and equipment.check(c, i) is None]
        if offers:
            n, i, p = max(offers, key=lambda o: self.score(o[1]))
            self.act({"kind": "buy", "target": n.id, "ware": i.name, "item": i.name}, "buy a weapon", "gear")
            self.gear_pass()

    def stalled(self) -> bool:
        xp = total_xp(self.c)
        if xp != getattr(self, "_sx", None):
            self._sx, self._sd = xp, self.day
            return False
        if self.day - self._sd >= 8:
            if not getattr(self, "_logged_stall", None) == self._sd:
                self._logged_stall = self._sd
                self.log("stall", equip=sorted(self.c.equipment), coins=self.c.coins, pack=len(self.pack), hp=self.frac("health"),
                         q=[(q["kind"], q["letter"], q.get("progress")) for q in self.ws.player.quests][:5], rank=self.ws.player.guild_rank)
                self.stalls = getattr(self, "stalls", 0) + 1
            return True
        return False

    def maintenance(self):
        if self.stalled():
            self.grind()
            return
        if self.unarmed() and not any(not i.good and i.base != "raw_material" and items.base_of(i).slot == "main_hand"
                                      for i in self.pack):
            self.rearm()
        else:
            self.gear_pass()
        if self.need_rest():
            self.recover()
        if len(self.pack) >= 17:
            t = self.nearest(lambda pid, p: any(self.world.roles[r].buys for r in p.residents))
            if t and self.goto(t[1]):
                self.town_services()

    # ------------------------------------------------------------ the guild
    def guild_visit(self):
        ws = self.ws
        if not self.goto(HALL, "travel"):
            return
        for _ in range(3):
            if ws.clerk_here():
                break
            self.act({"kind": "wait", "wait_until": "morning"}, "wait for the clerk", "guild")
        c = self.c
        if not ws.player.guild_rank and c.coins >= quests.G["joining_fee"] + 60 and ws.clerk_here():
            self.act({"kind": "join_guild"}, "join the guild", "guild")
            self.log("joined", coins=c.coins)
        self.people_pass()
        self.act({"kind": "board"}, "check the board", "guild")      # any action also turns in finished contracts
        self.last_guild_day = self.day
        self.town_services()
        if ws.player.guild_rank:
            self.trial_attempt()
            self.take_contracts()

    def trial_attempt(self):
        """Stand for the next rank whenever the numbers allow and the examiner is free."""
        ws = self.ws
        if not ws.trial_due() or self.minutes_now() < ws.player.trial.get("wait_until", -1):
            return
        deaths0, rank0 = self.c.deaths, ws.player.guild_rank
        try:
            ws.handle("I would like to take the trial for my next rank")
        except LLMError as e:
            self.note_exc("LLMError(trial)", str(e)[:100], None)
        if ws.combat:
            self.fight_out()
        won = ws.player.guild_rank != rank0
        self.trials.append({"rank": ws.player.guild_rank if won else rank0, "won": won, "level": self.c.level, "day": self.day})
        self.log("trial", rank=self.trials[-1]["rank"], won=won, level=self.c.level)
        if self.c.deaths > deaths0:
            self.violation("trial_death", "the trial killed the player")

    def minutes_now(self):
        return self.ws.minutes

    def feasible(self, q) -> bool:
        c = self.c
        if q["guild"] and not quests.at_or_below(q["letter"], self.ws.player.guild_rank):
            return False
        lv = c.level
        k = q["kind"]
        place = q.get("place")
        if k == "missing":
            return arcs.active(self.store.load_arcs()) is None or q.get("arc") is not None
        if k in ("delve", "dungeon_boss"):
            d = next((x for x in self.store.load_dungeons() if x["id"] == q["dungeon"]), None)
            if not d:
                return False
            if k == "delve" and (q["floor"] >= len(d["floors"]) or d["floors"][q["floor"]]["level"] > lv + 3
                                 or d["floors"][q["floor"]]["level"] < lv * 0.8):
                return False
            if k == "dungeon_boss" and (d["floors"][-1]["level"] + 2 > lv + 2 or d["floors"][-1]["level"] < lv * 0.8):
                return False
            place = d["place"]
        elif k in ("hunt", "bounty"):
            cr = self.world.bestiary[q["creature"]]
            foe = sum(quests._overlap(cr, self.world.places[q["place"]])) // 2
            if foe > lv + 5 or foe < lv * 0.8 - 3:          # a player skips contracts against things far beneath them
                return False
        elif k == "materials":
            if items.MATERIALS[q["material"]].levels[0] > lv + 5:
                return False
            place = self.material_place(q)
            if not place:
                return False
            if self.world.places[place].danger and self.world.places[place].danger[1] < lv * 0.6:
                return False                # a player does not walk back to starter ground for a low-level bounty
        elif k == "gather":
            place = self.herb_place(q)
            if not place:
                return False
        if place and q["guild"]:
            m = self.path_minutes(HALL, place)
            if m is None or (q.get("deadline") is not None and m * 2 > (q["deadline"] - q["posted"]) * 0.8):
                return False
        return True

    def take_contracts(self):
        ws = self.ws
        for _ in range(4):
            limit = quests.G["base_active"] + ws.guild_perks()["active"]
            mine = [q for q in ws.player.quests if q["guild"]]
            if len(mine) >= limit:
                return
            board = ws.ensure_board()
            have_big = any(q["kind"] in ("delve", "dungeon_boss") for q in mine)
            have_arc = any(q["kind"] == "missing" for q in mine)
            cands = [(i, q) for i, q in enumerate(board, 1) if self.feasible(q)
                     and not (have_big and q["kind"] in ("delve", "dungeon_boss")) and not (have_arc and q["kind"] == "missing")]
            if not cands:
                return
            idx, q = max(cands, key=lambda iq: (quests.LETTERS.index(iq[1]["letter"]), iq[1]["coins"]))
            n0 = len(ws.player.quests)
            self.act({"kind": "accept_quest", "item": str(idx)}, "take a contract", "guild")
            if len(ws.player.quests) > n0:
                self.log("quest_taken", qk=q["kind"], letter=q["letter"], title=q["title"], coins=q["coins"], xp=q["xp"])
            else:
                return

    # ------------------------------------------------------------ quest execution
    def quest_gone(self, q) -> bool:
        return not any(x["id"] == q["id"] for x in self.ws.player.quests)

    def live(self, q):
        return next((x for x in self.ws.player.quests if x["id"] == q["id"]), q)

    def run_quest(self, q):
        t0, d0 = self.ws.minutes, self.day
        ok = False
        try:
            k = q["kind"]
            if k in ("hunt", "bounty"):
                ok = self.do_hunt(q)
            elif k == "gather":
                ok = self.do_gather(q)
            elif k == "materials":
                ok = self.do_materials(q)
            elif k == "deliver":
                ok = self.do_deliver(q)
            elif k in ("delve", "dungeon_boss"):
                ok = self.do_delve(q)
            elif k == "missing":
                ok = self.do_arc(q)
        finally:
            self.quest_log.append({"kind": q["kind"], "letter": q["letter"], "title": q["title"], "ok": bool(ok),
                                   "days": round((self.ws.minutes - t0) / 1440, 1), "d": d0, "guild": q["guild"],
                                   "coins": q["coins"], "xp": q["xp"]})
            self.log("quest_run", qk=q["kind"], letter=q["letter"], ok=bool(ok), title=q["title"])
        if ok and not self.quest_gone(q):
            if q["guild"]:
                self.guild_visit()
            else:
                issuer = self.store.load_npc(q["issuer"])
                if self.goto(issuer.location):
                    self.act({"kind": "look"}, "look around", "social")
        elif not ok and not self.quest_gone(q) and (q["deadline"] is None or self.ws.minutes < q["deadline"]):
            self.act({"kind": "abandon_quest", "item": q["title"]}, "give up", "guild")


    # ------------------------------------------------------------ arcs: follow the trail to its end
    PRISONER_STYLE = {"paladin": "spare", "priest": "spare", "bard": "spare", "monk": "spare", "summoner": "spare",
                      "warrior": "mixed", "mage": "mixed", "smith": "mixed", "artisan": "mixed", "ranger": "mixed",
                      "warlock": "kill"}

    def best_social(self) -> str:
        c = self.c
        return max(("persuasion", "intimidation", "deception"),
                   key=lambda k: checks.chance(c, k, self.ws.conditions())[0])

    def arc_state(self):
        data, arc = self.ws.my_arc()
        return arc

    def do_arc(self, q) -> bool:
        ws = self.ws
        rec = {"title": q["title"], "d0": self.day, "lv0": self.c.level, "template": None, "size": None, "steps": [], "result": "?"}
        self.arc_log.append(rec)
        stuck, last = 0, None
        for _ in range(120):
            if self.quest_gone(q):
                rec["result"] = "quest gone"
                self.arc_note(rec)
                return False
            q = self.live(q)
            if q.get("progress", 0) >= q["count"]:
                rec["result"] = "done"
                return True
            arc = self.arc_state()
            if not arc or arc["id"] != q.get("arc"):
                rec["result"] = "arc ended elsewhere"
                return q.get("progress", 0) >= q["count"]
            rec["template"], rec["size"] = arc["template"], arc["size"]
            n = arcs.current(arc)
            if not n:
                rec["result"] = "no current node"
                return False
            sig = (n["id"], n["status"], n["attempts"], n["clue_given"])
            if sig == last:
                stuck += 1
            else:
                stuck, last = 0, sig
            if stuck >= 6:
                rec["result"] = f"stuck at {n['id']} {n['kind']} {n['status']}"
                return False
            if self.need_rest():
                self.recover()
            if self.c.level + 6 < arc["level"] * 0.6:
                rec["result"] = "outlevelled"
                return False
            rec["steps"].append((n["id"], n["kind"], n["status"], self.day))
            try:
                if n["kind"] == "contact":
                    self.arc_contact(arc, n)
                else:
                    self.arc_place(arc, n)
            except LLMError as e:
                self.note_exc("LLMError(arc)", str(e)[:100], None)
        rec["result"] = "step budget"
        return False

    def arc_note(self, rec):
        rec["notes"] = [n[:110] for n in list(NOTES)[-4:]]

    def arc_contact(self, arc, n):
        ws = self.ws
        if not self.goto(n["place"], "arc"):
            return
        arc = self.arc_state()
        n = arcs.node(arc, n["id"]) if arc else n
        npc = next((x for x in ws.present if x.id == n.get("npc")), None)
        for _ in range(3):
            if npc:
                break
            self.act({"kind": "wait", "wait_until": "morning" if self.rng.random() < 0.5 else "midday"}, "wait for them", "arc")
            npc = next((x for x in ws.present if x.id == n.get("npc")), None)
        if not npc:
            return
        for attempt in range(5):
            skill = self.best_social()
            self.act({"kind": "talk", "target": npc.id, "speech": "I'm looking into something. What do you know about it?",
                      "checks": [skill]}, "press them", "arc")
            arc = self.arc_state()
            if not arc or arcs.node(arc, n["id"])["status"] == "done":
                return

    def bot_recruit(self, n):
        """Characters who cannot sneak hire a party at the guild before going after a camp."""
        ws = self.ws
        if n["kind"] not in ("lair", "boss") or len(ws.player.party) >= 3 or self.c.coins < 8000:
            return
        sneak = checks.chance(self.c, "stealth", {"always", "out_of_combat"}, None, ws.check_bonuses("stealth", None, False, ""))[0]
        if sneak >= 40 and self.c.level >= 6:
            return
        hall = ws.guild_place_id()
        if not hall or not self.goto(hall, "arc"):
            return
        before = len(ws.player.party)
        self.act({"kind": "look"}, "recruit help from the guild, hire them all", "arc")
        self.party_tally["hired"] += len(ws.player.party) - before
        if ws.player.party:
            self.party_tally["runs"] += 1

    def arc_place(self, arc, n):
        ws = self.ws
        self.bot_recruit(n)
        if self.loc == n["place"]:
            near = next((p for p in self.world.neighbors(n["place"]) if p in self.world.places), None)
            if near and self.goto(near, "arc"):
                self.recover(local=True) if self.need_rest() else None
        if not self.goto(n["place"], "arc"):
            return
        self.camp_approach()
        self.handle_prisoners()

    CAMP_LOG = None

    def camp_approach(self):
        """Use the stealth approach when the character is good at it, else go in loud. Records what each try did."""
        ws = self.ws
        for _ in range(20):
            ctx = ws.camp_ctx()
            if not ctx or ws.combat:
                return
            data, arc, n = ctx
            camp = n["camp"]
            if _ and camp["alert"] >= 2:
                return                  # the camp is up and the fight did not finish it: back off and heal
            bonus = ws.check_bonuses("stealth", None, False, "")
            sneak = checks.chance(self.c, "stealth", {"always", "out_of_combat"}, None, bonus)[0]
            talk = max(checks.chance(self.c, k, {"always", "out_of_combat"}, None, ws.check_bonuses(k, None, False, ""))[0]
                       for k in ("deception", "intimidation"))
            if self.c.level < 6 or max(sneak, talk) < 35:
                text = "charge in"
            elif not camp["scouted"] and sneak >= 35:
                text = "scout the camp"
            elif sum(1 for g in camp["guards"] if g["state"] == "up") > 3 and sneak >= 40:
                text = "sneak up on a guard and knock them out"
            elif sneak >= 40:
                text = "ambush the leader from the shadows"
            elif talk >= 45 and ws.camp_leader_is_people(camp):
                text = "bluff my way in"
            else:
                text = "charge in"
            n0 = len(ws.camp_events or [])
            if ws.player.party and ws.player.party_mode == "with" and text != "charge in":
                ws.party_turn("have the party hold back and wait outside")
            self.act({"kind": "look"}, text, "arc")
            for ev in (ws.camp_events or [])[n0:]:
                self.camp_tally[f"{ev[0]}:{ev[1]}"] += 1
            self.camp_tally["charge" if text == "charge in" else "tries"] += 1

    def handle_prisoners(self):
        """Question, then spare or kill, whoever the player holds here."""
        if getattr(self, "_in_prisoners", False):
            return
        self._in_prisoners = True
        try:
            ws = self.ws
            for _ in range(3):
                p = ws.prisoner_here()
                if not p:
                    return
                style = self.PRISONER_STYLE.get(CLS, "mixed")
                self.prisoner_seen += 1
                for attempt in range(4):
                    skill = self.best_social()
                    deal = style != "kill" or attempt >= 2
                    speech = "Tell me what you know. I will let you go if you do." if deal else "Talk, or it goes badly."
                    self.act({"kind": "talk", "target": p.id, "speech": speech, "checks": [skill]}, "question the captive", "arc")
                    arc = self.arc_state()
                    pr = ws.player.prisoners.get(p.id)
                    if not pr or not pr.get("node") or (arc and all(x["status"] == "done" or x["id"] != pr["node"] for x in arc["nodes"])):
                        break
                spare = style == "spare" or (style == "mixed" and self.rng.random() < 0.6)
                if p.id in ws.player.prisoners:
                    if spare:
                        self.act({"kind": "release", "target": p.id}, "let the captive go", "arc")
                        self.prisoner_spared += 1
                    else:
                        self.act({"kind": "attack", "target": p.id}, "kill the captive", "arc")
                        self.prisoner_killed += 1
        finally:
            self._in_prisoners = False

    def do_hunt(self, q) -> bool:
        cr = self.world.bestiary[q["creature"]]
        if not self.goto(q["place"]):
            return False
        misses = 0
        for _ in range(120):
            if self.quest_gone(q) or quests.done(q, self.pack):
                break
            if self.need_rest():
                here = self.loc
                self.recover()
                if not self.goto(here):
                    return False
            p0 = q["progress"]
            self.act({"kind": "search", "seek": cr.name.lower()}, f"look for {cr.name.lower()}", "hunting")
            if self.loc != q["place"] and not self.goto(q["place"]):
                return False
            misses = 0 if q["progress"] > p0 else misses + 1
            if misses > 40:
                self.log("hunt_gaveup", title=q["title"])
                return False
        return quests.done(q, self.pack)

    def herb_place(self, q):
        g = inv.GOODS[q["good"]]
        best = None
        for pid, p in self.world.places.items():
            if p.biome in g.grows_in and p.danger and p.type != "dungeon" and p.danger[0] <= self.c.level + 3:
                m = self.path_minutes(self.loc, pid) if pid != self.loc else 0
                if m is not None and (best is None or m < best[0]):
                    best = (m, pid)
        return best[1] if best else None

    def do_gather(self, q) -> bool:
        place = self.herb_place(q)
        if not place or not self.goto(place):
            return False
        for _ in range(40):
            if self.quest_gone(q) or quests.done(q, self.pack):
                break
            if self.need_rest():
                here = self.loc
                self.recover()
                self.goto(here)
            self.act({"kind": "forage"}, "forage", "foraging")
        return quests.done(q, self.pack)

    def material_place(self, q):
        best = None
        for pid, p in self.world.places.items():
            if p.danger and p.type != "dungeon" and p.danger[0] <= self.c.level + 3:
                roster = encounters.ensure_roster(self.store, self.world, pid)
                if any(r in items.MATERIALS[q["material"]].drops_from for r in roster):
                    m = self.path_minutes(self.loc, pid) if pid != self.loc else 0
                    if m is not None and (best is None or m < best[0]):
                        best = (m, pid)
        return best[1] if best else None

    def do_materials(self, q) -> bool:
        place = self.material_place(q)
        if not place or not self.goto(place):
            return False
        roster = encounters.ensure_roster(self.store, self.world, place)
        sources = [r for r in items.MATERIALS[q["material"]].drops_from if r in roster]
        name = self.world.bestiary[sources[0]].name.lower()
        for _ in range(100):
            if self.quest_gone(q) or quests.done(q, self.pack):
                break
            if self.need_rest():
                here = self.loc
                self.recover()
                self.goto(here)
            self.act({"kind": "search", "seek": name}, f"look for {name}", "hunting")
            if self.loc != place and not self.goto(place):
                return False
            if self.store.load_place(place).carcasses:
                self.act({"kind": "harvest"}, "skin", "harvest")
        return quests.done(q, self.pack)

    def do_deliver(self, q) -> bool:
        place = q.get("place")
        if not place or not self.goto(place):
            return False
        for _ in range(4):
            self.act({"kind": "give", "target": "", "item": q["item"]}, "hand it over", "guild")
            if q["progress"] or self.quest_gone(q):
                break
            self.act({"kind": "wait", "wait_until": "morning"}, "wait for them", "guild")
        return bool(q["progress"])

    def do_delve(self, q) -> bool:
        ws = self.ws
        d = next((x for x in self.store.load_dungeons() if x["id"] == q["dungeon"]), None)
        if not d or not self.goto(d["place"]) or not self.goto(d["entrance"]):
            return False
        t0 = ws.minutes
        for _ in range(200):
            if self.quest_gone(q) or quests.done(q, self.pack):
                break
            d = next((x for x in self.store.load_dungeons() if x["id"] == q["dungeon"]), None)
            if not d or (q["deadline"] is not None and ws.minutes >= q["deadline"]):
                break
            if self.need_rest() or self.frac("health") < 0.65:
                if ws.player.delve and ws.player.delve.get("rest"):
                    self.act({"kind": "wait", "wait_minutes": 360}, "rest in the quiet chamber", "rest")
                else:
                    self.act({"kind": "leave_dungeon"}, "climb out", "delving")
                    self.recover(local=True)
                continue
            if dungeons.next_chamber(d) is None:
                break
            deaths0 = self.c.deaths
            self.act({"kind": "delve"}, "press on", "delving")
            if self.c.deaths > deaths0:
                self.dungeon_log.append({"dungeon": d["name"], "theme": d["theme"], "result": "died", "cleared": d["cleared"],
                                         "lv": self.c.level, "kind": q["kind"], "letters": dungeons.letters(d)})
                return False
            if self.loc != d["entrance"]:
                self.goto(d["entrance"])
        d = next((x for x in self.store.load_dungeons() if x["id"] == q["dungeon"]), d)
        done = quests.done(q, self.pack) or self.quest_gone(q)
        self.dungeon_log.append({"dungeon": d["name"] if d else "?", "theme": d["theme"] if d else "?",
                                 "result": "done" if done else "unfinished", "cleared": d["cleared"] if d else None,
                                 "floors": len(d["floors"]) if d else 0, "lv": self.c.level,
                                 "days": round((ws.minutes - t0) / 1440, 1), "kind": q["kind"],
                                 "letters": dungeons.letters(d) if d else ""})
        if ws.player.delve:
            self.act({"kind": "leave_dungeon"}, "climb out", "delving")
        return quests.done(q, self.pack)

    # ------------------------------------------------------------ grinding
    def pick_zone(self):
        lv = self.c.level
        cands = []
        recent = sum(1 for d in self.deaths if self.day - d["d"] <= 15)
        reach = lv * 0.55 if recent >= 3 else lv + 2          # after a run of deaths a sensible player drops back to easier ground to recover and farm
        for pid, p in self.world.places.items():
            if not p.danger or p.type == "dungeon" or pid == "cracked_plains":
                continue
            lo, hi = p.danger
            if self.zone_ban.get(pid, 0) > lv:
                continue
            if lo <= reach and hi >= lv * (0.3 if recent >= 3 else 0.7):
                m = self.path_minutes(self.loc, pid) if pid != self.loc else 0
                if m is not None:
                    # how far from your level the enemies there will typically be (they are drawn across the zone's range)
                    mids = []
                    for cr in self.world.bestiary.values():
                        if p.biome in cr.biomes and cr.roster is not False and not getattr(cr, "unique", False):
                            a, b = max(lo, cr.levels[0]), min(hi, cr.levels[1])
                            if a <= b:
                                mids.append((a + b) / 2)
                    if mids:      # what the zone's roster actually puts in front of you, not the width of its range
                        gap = abs(sum(mids) / len(mids) - lv)
                    else:
                        span = range(max(1, lo), max(lo, hi) + 1)
                        gap = sum(abs(x - lv) for x in span) / len(span)
                    cands.append((m, pid, gap))
        if cands and recent < 3:
            best = min(g for _, _, g in cands)
            cands = [(m, pid) for m, pid, g in cands if g <= best * 1.25 + 3]       # only the ground that fights at your level
        else:
            cands = [(m, pid) for m, pid, g in cands]
        if not cands:
            for pid, p in self.world.places.items():
                if p.danger and p.type != "dungeon" and pid != "cracked_plains" and p.danger[0] <= max(1, lv // 2):
                    m = self.path_minutes(self.loc, pid) if pid != self.loc else 0
                    if m is not None:
                        cands.append((m, pid))
        if not cands:
            return "greywood"
        cands.sort()
        return self.rng.choice(cands[:3])[1]

    def grind(self, kills=6):
        zone = self.pick_zone()
        if not self.goto(zone):
            return
        won0 = sum(1 for f in self.fights if f["outcome"] == "victory")
        for _ in range(40):
            if self.need_rest():
                self.recover()
                if self.loc != zone and not self.goto(zone):
                    return
            deaths0 = self.c.deaths
            self.act({"kind": "search"}, "look around", "hunting")
            if self.c.deaths > deaths0 or self.loc != zone:
                return
            if CLS in ("artisan", "smith") and self.store.load_place(self.loc).carcasses:
                self.act({"kind": "harvest"}, "skin", "harvest")
            if sum(1 for f in self.fights if f["outcome"] == "victory") - won0 >= kills or len(self.pack) >= 18:
                return

    # ------------------------------------------------------------ the main loop
    def need_guild(self) -> bool:
        ws = self.ws
        ps = ws.player
        c = self.c
        if any(quests.done(q, self.pack) for q in ps.quests):
            return True
        if not ps.guild_rank:
            return c.coins >= quests.G["joining_fee"] + 200 and self.day - self.last_guild_day >= 1
        limit = quests.G["base_active"] + ws.guild_perks()["active"]
        mine = sum(1 for q in ps.quests if q["guild"])
        return mine < limit and self.day - self.last_guild_day >= 2

    hop_checked = 0

    def best_hall(self):
        """The guild hall whose wilds fit the character's level best (the bot moves its base there, as a player would)."""
        lv = self.c.level
        lo, hi = lv * 0.75, lv * 1.15
        def score(h):
            return sum(max(0, min(hi, p.danger[1]) - max(lo, p.danger[0])) / (hi - lo) for p in quests.hall_wilds(self.world, h))
        halls = ["guild_house"] + sorted(h for h in self.world.places if h.endswith("_guild"))
        cur = HALL if HALL in halls else "guild_house"
        pick, top = cur, score(cur) + 0.25
        for h in halls:
            if h != cur and self.world.path(self.loc, h) and score(h) > top:
                pick, top = h, score(h)
        return pick

    def cycle(self):
        global HALL
        ws = self.ws
        if HALL == "guild_house" and self.c.level >= int(os.environ.get("SIM_FAR_LEVEL", 10 ** 6)):
            HALL = ("dunmarrow_guild", "cinderhold_guild", "hrimgard_guild")[SEED % 3]      # the character moves to a great hall
            self.log("moved_hall", hall=HALL, lv=self.c.level, day=self.day)
        if os.environ.get("SIM_HOP", "1") == "1" and self.c.level >= self.hop_checked + 5 and self.c.level >= 20:
            self.hop_checked = self.c.level
            best = self.best_hall()
            if best and best != HALL:
                self.log("moved_hall", hall=best, was=HALL, lv=self.c.level, day=self.day)
                HALL = best
        s0, m0 = self.steps, ws.minutes
        self.pulse_watch()
        self.maintenance()
        if self.need_guild():
            self.guild_visit()
        if self.big_pass():
            return
        pending = sorted((q for q in ws.player.quests if not quests.done(q, self.pack)), key=lambda q: q["deadline"] or 10 ** 12)
        ran = False
        for q in pending:
            if not q["guild"] and q["kind"] != "hunt":
                continue
            if self.feasible(q):
                self.run_quest(q)
                ran = True
                break
        if self.rng.random() < 0.25:
            ROAD["explore_tries"] += 1
            self.act({"kind": "explore", "seek": "a hidden path"}, "explore", "exploring")
        if not ran:
            if self.day - self.last_talk_day >= 4 and self.rng.random() < 0.3:
                self.social_stop()
            self.people_pass()
            self.grind()
        if self.steps == s0 and ws.minutes == m0:
            self.act({"kind": "wait", "wait_minutes": 60}, "idle", "other")

    def social_stop(self):
        """Ask around in a settlement: odd jobs and requests from the people who live there."""
        self.last_talk_day = self.day
        t = self.nearest(lambda pid, p: p.type in ("village", "town", "city") and pid != self.loc)
        if not t or t[0] > 2200 or not self.goto(t[1]):
            return
        STUB.ask_help = True
        who = next((n for n in self.ws.present if n.role != "guild_clerk"), None)
        if who:
            self.act({"kind": "talk", "target": who.id, "speech": "Need any help?"}, "ask", "social")
            who = self.store.load_npc(who.id)
            if who.work_offer:
                self.act({"kind": "work", "target": who.id}, "work", "work")
            elif who.quest_offer:
                self.act({"kind": "accept_quest", "target": who.id}, "accept", "social")
        STUB.ask_help = False


    # ------------------------------------------------------------ people and the big events
    def people_pass(self, limit=3):
        """Where the character stands, in a settlement: talk to people (and sometimes press them), now and then give a gift. This is
        what builds the trust that later brings allies to a fight."""
        ws = self.ws
        town = pulse.town_of(self.world, self.loc)
        if self.world.places[town].type not in ("village", "town", "city") or self.day == self.__dict__.get("people_day"):
            return
        self.people_day = self.day
        for n in [x for x in ws.present if x.role not in ("guild_clerk",)][:limit]:
            checks_ = [self.best_social()] if self.rng.random() < 0.5 else []
            self.act({"kind": "talk", "target": n.id, "speech": "How are things here? Anything I should know about?", "checks": checks_},
                     "talk", "social")
            self.npc_stats["talks"] += 1
            if checks_:
                self.npc_stats["checks"] += 1
            if self.c.coins > 5000 and self.rng.random() < 0.5:
                self.act({"kind": "give", "target": n.id, "item": "2 silver"}, "give 2 silver", "social")
                self.npc_stats["gifts"] += 1

    def befriend_master(self, th):
        """Win the trust of the guild master (and a few others) in the event's path, so they will stand with the character."""
        ws = self.ws
        cfg = bigev.E["allies"]
        towns = {pulse.town_of(self.world, th["place"]), *th.get("hit_towns", [])}
        halls = [p for p in self.world.places.values() if p.id in self.world.places and (p.residents or {}).get("guild_master")
                 and pulse.town_of(self.world, p.id) in towns]
        for hall in halls[:2]:
            if self.befriended.get(hall.id, -99) > self.day - 20:
                continue
            m = self.path_minutes(self.loc, hall.id)
            if m is None or m > 3 * 1440 or not self.goto(hall.id):
                continue
            self.befriended[hall.id] = self.day
            for n in [x for x in ws.present if x.role in cfg["roles"]][:2]:
                for _ in range(40):
                    n = self.store.load_npc(n.id)
                    if n.trust >= cfg["min_trust"] + 5 or self.c.coins < 600:
                        break
                    self.act({"kind": "give", "target": n.id, "item": "5 silver"}, "give 5 silver", "social")
                    self.npc_stats["gifts"] += 1
                    if self.rng.random() < 0.25:
                        self.act({"kind": "talk", "target": n.id, "speech": "I mean to face the trouble that threatens us all."}, "talk", "social")
                        self.npc_stats["talks"] += 1
                n = self.store.load_npc(n.id)
                self.npc_stats["trusted"] += n.trust >= cfg["min_trust"]
                self.log("befriend", npc=n.name, role=n.role, trust=n.trust, hall=hall.id)

    def big_pass(self) -> bool:
        """If a campaign or cataclysm has a boss out in the wild that the character can face, go and end it."""
        st = self.store.load_world_state() or {}
        now = self.ws.minutes
        for th in st.get("threads", []):
            if th["tier"] not in ("campaign", "cataclysm") or th["status"] != "active":
                continue
            if self.big_cool.get(th["id"], -1) > self.day:
                continue
            live = bigev.live_spawns(st, now, th["id"])
            boss = next((x for x in live if x["boss"]), None)
            treaty = next((p for p in th.get("paths", []) if p["kind"] == "treaty" and not p["done"]), None)
            war_peace = th.get("kind") == "war" and sum(map(ord, th["id"])) % 2 == 0     # half the bots' wars are talked through, half fought
            if th.get("kind") == "war" and not war_peace:
                treaty = None
            elif treaty and war_peace:
                boss = None
            if treaty and not boss and th["stage"] >= 1:
                self.log("big_start", tier=th["tier"], title=th["title"], boss=None, treaty=[l["name"] for l in th["leaders"]], stage=th["stage"] + 1,
                         hit=th.get("hit_towns"), fallen=th.get("fallen"))
                self.big_log.append({"d": self.day, "lv": self.c.level, "tier": th["tier"], "title": th["title"], "boss": None, "stage": th["stage"] + 1,
                                     "treaty": True})
                return self.make_peace(th["id"])
            if not boss or (boss.get("level") or 0) > self.c.level + 6 or (boss.get("level") or 0) < self.c.level - 40:
                continue
            if self.path_minutes(self.loc, boss["place"]) is None:
                continue
            self.log("big_start", tier=th["tier"], title=th["title"], boss=boss["name"], boss_lv=boss.get("level"), at=boss["place"],
                     stage=th["stage"] + 1, hit=th.get("hit_towns"), fallen=th.get("fallen"))
            self.big_log.append({"d": self.day, "lv": self.c.level, "tier": th["tier"], "title": th["title"], "boss": boss["name"],
                                 "boss_lv": boss.get("level"), "stage": th["stage"] + 1})
            if th["tier"] == "cataclysm":
                self.befriend_master(th)
                self.persuade_for(th)
            return self.hunt_boss(th["id"], boss["place"], boss["id"])
        return False

    def make_peace(self, tid) -> bool:
        """A war with no monster: go to each leader and press the case until they are won over."""
        d0, died0 = self.day, self.c.deaths
        for rounds in range(60):
            st = self.store.load_world_state() or {}
            th = next((x for x in st.get("threads", []) if x["id"] == tid), None)
            if not th or th["status"] != "active":
                break
            todo = [l for l in th["leaders"] if not bigev._won_over(st, th["made"], l["id"])]
            if not todo or self.day - d0 > 40:
                break
            n = self.store.load_npc(todo[0]["id"])
            ok_ = (not n.gone) and self.goto(n.location)
            here = next((x for x in self.ws.present if x.id == n.id), None)
            if rounds < 4 or rounds % 20 == 0:
                self.log("peace_step", n=rounds, npc=n.name, at=n.location, gone=n.gone, went=ok_, here=bool(here), loc_now=self.loc,
                         present=[x.role for x in self.ws.present][:6])
            if n.gone or not ok_:
                self.big_cool[tid] = self.day + 5
                break
            if not here:
                self.act({"kind": "wait", "wait_minutes": 120}, "wait", "social")
                continue
            self.act({"kind": "talk", "target": n.id, "speech": "Lay down your arms. Too many will die if this goes on.",
                      "checks": [self.best_social() if self.best_social() != "deception" else "persuasion"]}, "persuade", "social")
            self.npc_stats["treaty_tries"] += 1
        st = self.store.load_world_state() or {}
        th = next((x for x in st.get("threads", []) if x["id"] == tid), None)
        out = {"d": self.day, "lv": self.c.level, "title": th["title"] if th else "?", "status": th["status"] if th else "gone",
               "result": (th or {}).get("result"), "treaty_tries": rounds + 1}
        self.log("big_end", **out)
        self.big_log.append(out)
        if th and th["status"] == "active":
            self.big_cool.setdefault(tid, self.day + 4)
        return True

    def persuade_for(self, th):
        """Work the event from the people side: press someone in the first hit town (a persuade deed the judge can read)."""
        ws = self.ws
        for tid in th.get("hit_towns", [])[:1]:
            if self.path_minutes(self.loc, tid) is None or not self.goto(tid):
                continue
            for n in [x for x in ws.present if x.role != "guild_clerk"][:2]:
                self.act({"kind": "talk", "target": n.id, "speech": "Help us stand against the danger.", "checks": ["persuasion"]},
                         "persuade", "social")
                self.npc_stats["persuade_tries"] += 1

    def hunt_boss(self, tid, place, sid=None) -> bool:
        ws = self.ws
        deaths0, d0 = self.c.deaths, self.day
        wd0 = len(self.would_deaths)
        if not self.goto(place):
            return True
        for i in range(120):
            if self.need_rest():
                self.recover()
                if self.loc != place and not self.goto(place):
                    break
            st = self.store.load_world_state() or {}
            th = next((x for x in st.get("threads", []) if x["id"] == tid), None)
            if not th or th["status"] != "active":
                break
            self.act({"kind": "search"}, "look around", "hunting")
            if sid and next((x for x in (self.store.load_world_state() or {}).get("spawns", []) if x["id"] == sid), {"defeated": True})["defeated"]:
                break
            if self.c.deaths > deaths0:
                self.big_cool[tid] = self.day + 6
                break
            if len(self.would_deaths) > wd0:       # an immortal run counts a near-death as a loss: back off and level, as a real player would
                self.big_cool[tid] = self.day + 30
                break
            if self.day - d0 > 40:
                break
        st = self.store.load_world_state() or {}
        th = next((x for x in st.get("threads", []) if x["id"] == tid), None)
        out = {"d": self.day, "lv": self.c.level, "title": th["title"] if th else "?", "status": th["status"] if th else "gone",
               "result": (th or {}).get("result"), "died": self.c.deaths - deaths0, "searches": i + 1}
        self.log("big_end", **out)
        self.big_log.append(out)
        if th and th["status"] == "active":
            self.big_cool.setdefault(tid, self.day + 3)
        return True

    # ------------------------------------------------------------ errors, invariants
    def note_exc(self, name, msg, tb):
        sig = f"{name}: {msg}"[:200]
        e = self.exceptions.setdefault(sig, {"n": 0, "first_day": self.day, "lv": self.c.level, "loc": self.loc, "tb": tb or ""})
        e["n"] += 1
        if self.exc_run[0] == sig:
            self.exc_run[1] += 1
        else:
            self.exc_run = [sig, 1]

    def violation(self, name, msg):
        v = self.violations.setdefault(name, {"n": 0, "example": str(msg)[:200], "d": self.day})
        v["n"] += 1

    def check_invariants(self):
        c = self.c
        ws = self.ws
        if c.coins < 0: self.violation("negative_coins", c.coins)
        if c.health is not None and c.health > pools.maximum(c, "health") + 0.5: self.violation("health_over_max", c.health)
        if c.unspent_points < 0: self.violation("negative_points", c.unspent_points)
        if any(i.quantity <= 0 for i in c.inventory): self.violation("zero_quantity_item", "an item with quantity <= 0")
        if len(c.inventory) > ws.pack_slots() + 3: self.violation("pack_overflow", f"{len(c.inventory)} > {ws.pack_slots()}")
        if self.loc not in self.world.places: self.violation("bad_location", self.loc)
        uids = [i.uid for i in c.inventory] + [i.uid for i in c.equipment.values()]
        if len(uids) != len(set(uids)): self.violation("duplicate_item_uid", "same uid twice")
        for q in ws.player.quests:
            if q["progress"] > q["count"]: self.violation("quest_progress_over", q["title"])
        for slot, it in c.equipment.items():
            try:
                b = items.base_of(it)
                if not slot.startswith("ring") and b.slot != slot: self.violation("wrong_slot", f"{it.name} in {slot}")
            except Exception:
                self.violation("unknown_item_base", it.name)
        if ws.player.delve and self.world.places[self.loc].type != "dungeon":
            self.violation("delve_outside_dungeon", self.loc)

    # ------------------------------------------------------------ the run
    def done(self) -> str:
        if self.c.level >= TARGET: return f"reached level {TARGET}"
        if self.day >= MAX_DAYS: return f"time limit ({MAX_DAYS} days)"
        if self.steps >= MAX_STEPS: return f"step limit ({MAX_STEPS})"
        if len(self.deaths) >= 80: return "too many deaths (80)"
        if self.exc_run[1] >= 25: return f"stuck on a repeating error: {self.exc_run[0]}"
        if time.time() - self.t0 > WALL: return "wall-clock limit"
        return ""

    def run(self):
        while not self.done():
            try:
                self.cycle()
            except Exception as e:
                tb = traceback.format_exc()
                last = [l for l in tb.splitlines() if l.strip().startswith("File")][-1].strip()
                self.note_exc(type(e).__name__, f"{e} @ {last.split('/')[-1][:60]}", tb)
                self.ws.combat = None
                try:
                    self.act({"kind": "wait", "wait_minutes": 60}, "recover", "other")
                except Exception:
                    pass
        self.aborted = self.done()
        self.finish()

    # ------------------------------------------------------------ the survey and the summary
    def survey(self) -> dict:
        ws = self.ws
        out = {}
        for pid, p in self.world.places.items():
            rec = {"name": p.name, "type": p.type, "region": p.region, "biome": p.biome, "danger": p.danger,
                   "trade": p.trade_level, "stations": list(p.stations), "connects": dict(p.connects)}
            try:
                if p.danger and p.type != "dungeon":
                    roster = encounters.ensure_roster(self.store, self.world, pid)
                    rec["roster"] = roster
                    rec["categories"] = dict(collections.Counter(self.world.bestiary[r].category for r in roster))
                    rec["creature_levels"] = [self.world.bestiary[r].levels for r in roster]
                elif not p.danger and p.type != "dungeon":
                    npcs = populate_place(self.store, self.world, pid, ws.catalog)
                    rec["residents"] = sorted(collections.Counter(n.role for n in npcs).items())
                    rec["peoples"] = sorted(collections.Counter(n.people for n in npcs).items())
                    wares, stock = set(), []
                    for n in npcs:
                        role = self.world.roles[n.role]
                        wares |= {w.id for w in role.sells}
                        if role.stock:
                            prev = ws.player.location
                            ws.player.location = pid
                            ws.ensure_stock(n)
                            ws.player.location = prev
                            stock += [(i.base, i.rarity, i.item_level, items.price(i)) for i in crafting.stock_items(n)]
                    rec["wares"] = sorted(wares)
                    rec["stock"] = stock
                    rec["lore_group"] = self.world.locals_group(pid)
            except Exception as e:
                rec["survey_error"] = repr(e)[:120]
                self.note_exc("survey", f"{pid}: {e!r}"[:100], traceback.format_exc())
            out[pid] = rec
        return out

    def item_detail(self, i):
        b = items.base_of(i)
        return {"name": i.name, "base": i.base, "slot": b.slot, "rarity": i.rarity, "ilvl": i.item_level, "material": i.material,
                "gem": i.gem, "value": items.value(i), "price": items.price(i), "summary": items.summary(i),
                "effects": [f"+{e.magnitude}{chr(37) if e.modifies == 'recovery' else ''} {e.modifies}" + ("" if e.trigger == "always" else f" ({e.trigger})") for e in items.effects(i)],
                "flags": items.flags(i), "legendary": i.legendary_effect,
                "enchants": [(e.name, [f"+{p.magnitude}% {p.modifies}" for p in e.effects]) for e in i.enchantments]}

    def finish(self):
        ws = self.ws
        c = self.c
        st = self.store.load_world_state()
        npcs = [self.store.load_npc(i) for i in self.store.list_npcs()]
        threads = st.get("threads", [])
        summary = {
            "class": CLS, "seed": SEED, "end": self.aborted, "level": c.level, "day": self.day, "steps": self.steps,
            "secs": round(time.time() - self.t0), "deaths": self.deaths, "would_deaths": self.would_deaths, "milestones": self.milestones,
            "rank": ws.player.guild_rank, "guild_done": ws.player.guild_done, "coins": c.coins,
            "cat_minutes": dict(self.cat_minutes), "income": dict(self.income), "spend": dict(self.spend),
            "xp_src": dict(self.xp_src), "kills_by_place": dict(self.kills_by_place),
            "visited": {k: v for k, v in self.visited.items()}, "travel": self.travel, "quests": self.quest_log,
            "dungeons": self.dungeon_log, "blocked": self.blocked, "exceptions": self.exceptions,
            "violations": self.violations, "notes": dict(NOTE_COUNTS.most_common(60)), "stub_calls": STUB.calls,
            "fights": self.fights, "model_requests_seen": simlib.SEEN_TITLES,
            "gear_detail": {s_: self.item_detail(i) for s_, i in c.equipment.items()},
            "pack_gear": [self.item_detail(i) for i in c.inventory if not i.good and i.base != "raw_material"
                          and items.base_of(i).slot in ("neck", "ring")][:10],
            "enchants": self.enchants, "road": dict(ROAD),
            "arc_log": self.arc_log, "arcs_store": [{k: a[k] for k in ("template", "size", "state", "revealed", "why", "started", "ended") if k in a}
                                                    | {"nodes": [(n["kind"], n["status"], n["partial"], n["attempts"]) for n in a["nodes"]]}
                                                    for a in self.store.load_arcs()["arcs"]],
            "camp": dict(self.camp_tally),
            "big": self.big_log, "npc_stats": dict(self.npc_stats),
            "titles": ws.player.titles, "mounts": [m["name"] for m in ws.player.mounts],
            "cataclysms": st.get("cataclysms"),
            "rarity_found": dict(self.rarity_tally),
            "mana": self.mana_summary(),
            "legendaries": self.legendaries,
            "party": dict(self.party_tally),
            "prisoners": {"seen": self.prisoner_seen, "spared": self.prisoner_spared, "killed": self.prisoner_killed,
                          "outlaw_rep": ws.player.outlaw_rep},
            "wealth_buys": self.wealth_buys, "homes": list(ws.player.homes), "relics": list(ws.player.relics_bought),
            "equipment": {s: (i.name, i.rarity, i.item_level) for s, i in c.equipment.items()},
            "actives": [(a.name, a.tier.value, a.effect.value) for a in c.actives],
            "attributes": c.attributes.model_dump(),
            "passives": [(p.name, (p.mechanic or p.modifies.value) if p.modifies else p.mechanic) for p in c.passives],
            "reputation": ws.player.reputation, "trained": c.trained, "crafting_skill": c.crafting_skill,
            "pulse": {"threads": len(threads), "by_tier": dict(collections.Counter(t["tier"] for t in threads)),
                      "by_status": dict(collections.Counter(t["status"] for t in threads)),
                      "history": len(st.get("history", [])), "news": len(st.get("news", [])),
                      "effects_live": len([e for e in st.get("effects", []) if e["until"] > ws.minutes]),
                      "npcs_gone": [(n.name, n.role, n.gone) for n in npcs if n.gone],
                      "npcs_with_motive": sum(1 for n in npcs if n.motive),
                      "npcs_met": sum(1 for n in npcs if n.tier != "background"), "npcs_total": len(npcs),
                      "moods": sum(1 for n in npcs if n.mood), "relations": sum(len(n.relations) for n in npcs),
                      "campaign_events": [t["title"] for t in threads if t["tier"] == "campaign"]},
        }
        try:
            summary["survey"] = self.survey()
        except Exception as e:
            summary["survey_error"] = repr(e)
        (OUT / f"{CLS}_summary.json").write_text(json.dumps(summary, default=str, indent=1))
        self.log_f.close()


if __name__ == "__main__":
    bot = Bot()
    bot.run()
    sys.stdout = sys.__stdout__
    print(CLS, "ended:", bot.aborted, "| level", bot.c.level, "| day", bot.day, "| steps", bot.steps,
          "| deaths", len(bot.deaths), "| secs", round(time.time() - bot.t0))
