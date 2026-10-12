"""Running a fight inside the game: start, rounds, and how it ends.

The engine (engine/combat.py) decides everything. The model only reads the player's words
and narrates the round from the engine's log.
"""

import json
import math
import random
import re

from core.models import Item
import config
from engine import ability_traits as AT
from engine import accessories, bosses, inventory, clock, combat, death, events, items, leveling, loot, money, party, pools, taming
from llm.contracts import AccessoryName, CombatIntent, GoddessLine, LegendaryName, LootName, Narration
from llm.gateway import LLMError, generate
from scenes import combat_prompts as cp
from scenes import goddess_prompts as gp
from scenes.voice import fresh
from ui import console

ROLE_PROFILES = {
    "striker": {"strength": 14, "dexterity": 15, "constitution": 11, "intelligence": 6, "wisdom": 10, "charisma": 6},
    "guardian": {"strength": 15, "dexterity": 9, "constitution": 16, "intelligence": 6, "wisdom": 10, "charisma": 6},
    "rogue": {"strength": 10, "dexterity": 16, "constitution": 10, "intelligence": 8, "wisdom": 12, "charisma": 6},
    "healer": {"strength": 8, "dexterity": 11, "constitution": 12, "intelligence": 10, "wisdom": 16, "charisma": 10},
    "support": {"strength": 8, "dexterity": 12, "constitution": 11, "intelligence": 12, "wisdom": 14, "charisma": 12},
}


TAG = re.compile(r"\s*[\[\(\{]\s*h\d+\s*[\]\)\}]", re.IGNORECASE)
TAG_N = re.compile(r"\s*[\[\(\{]\s*h(\d+)\s*[\]\)\}]", re.IGNORECASE)


def place_figures(text: str, hits: list[dict], window: bool) -> str:
    """Swap each blow's tag in the narration for its figure, e.g. '(14 damage)'. Any figure the narrator left out goes on the end,
    so a blow is never without its number. In the window a figure is a hoverable token (⟦id|figure⟧); in the terminal plain text."""
    by_tag = {h['tag']: h for h in hits if h.get('figure')}
    used = set()
    def fig(h):
        return f"⟦{h['id']}|{h['figure']}⟧" if window else h['figure']
    def sub(m):
        h = by_tag.get('h' + m.group(1))
        if not h or h['tag'] in used:
            return ''
        used.add(h['tag'])
        return ' ' + fig(h)
    text = TAG_N.sub(sub, text)
    missing = [fig(h) for t, h in by_tag.items() if t not in used]
    return text + (' ' + ' '.join(missing) if missing else '')


class _Shape:
    """A minimal creature-like object for companions that aren't in the bestiary (summoned spirits)."""
    def __init__(self, comp):
        sizes = combat.RULES["creatures"].get("spirit", {}).get("size", {})
        self.id, self.name, self.size, self.category = comp.id, comp.name, sizes.get(getattr(comp, "tier", "light"), "Medium"), comp.kind or "spirit"
        self.profile = ROLE_PROFILES.get(comp.role, ROLE_PROFILES["striker"])
        self.attacks, self.temperament, self.group = ["strike"], "aggressive", (1, 1)


class CombatScene:
    def __init__(self, world_scene, fight: combat.Combat, creature_name: str):
        self.ws = world_scene
        self.fight = fight
        fight.record = True
        self.creature_name = creature_name
        self.rng = random.Random()
        self.tamed: list[str] = []

    # ---------- setup ----------

    @classmethod
    def allies(cls, ws, hold: bool = False) -> tuple[list, list]:
        """(allies who start in the fight, allies who arrive later). Companions always start; a party told to hold arrives late."""
        c = ws.player.character
        near = []
        for comp in c.companions:
            if comp.fallen and not comp.dead and ws.minutes >= comp.recover_at:
                comp.fallen = False
                console.note(f"{comp.name} is back on its feet.")
            if not comp.active:
                continue
            shape = ws.world.bestiary.get(comp.creature) or _Shape(comp)
            spirit = None if comp.creature in ws.world.bestiary else (comp.tier, comp.role)
            ally = combat.companion_fighter(shape, c.level, f"ally_{comp.id}", comp.name, spirit, gift=comp.source == "gift")
            near.append(ally)
        near = taming.strongest(near, c.level)
        members = [party.fighter(m) for m in ws.player.party]
        if hold and ws.player.party_mode == "hold":
            return near, members
        return near + members, []

    @classmethod
    def begin(cls, ws, creature, enemies: list[combat.Fighter], how: str, reserves: list[combat.Fighter] | None = None,
              wave: tuple[int, int, int] = (2, 2, 1)) -> "CombatScene":
        c = ws.player.character
        events.recruit_allies(ws, enemies)
        prep = ws.field_prep(enemies)
        fighters = [combat.fighter_from_character(c)]
        near, later = cls.allies(ws, hold=bool(getattr(ws, "camp_fight", None)))
        fighters += near
        tether_notes = ws.tether_for(near)
        fight = combat.Combat(fighters=fighters + enemies, place=ws.place.name, conditions=sorted(ws.conditions()))
        fight.record = True                 # keep a breakdown of every blow for the window's combat log
        fight.ally_reserves = later
        fight.ally_arrive = party.P["hold_arrival_round"]
        fight.gentle = pools.mechanic(c, "gentle_approach") is not None
        fight.reserves = list(reserves or [])
        fight.reinforce_every, fight.reinforce_count, fight.reinforce_from = wave
        scene = cls(ws, fight, creature.name)
        combat.opening(fight, scene.rng)
        opening_events = [TAG.sub("", e) for e in fight.story]          # the opening blows are logged, not narrated with figures
        fight.log, fight.story = [], []
        label, rate = combat.danger(fight)
        console.debug(f"danger estimate: {rate:.0%} win rate")
        manner = {"aggressive": "They mean to attack.",
                  "territorial": "It holds its ground and warns the player off - they could still back away.",
                  "passive": "It turns on the player."}[creature.temperament]
        where = enemies[0].band if enemies else "near"
        odds = {"trivial": "no real threat", "favorable": "the player should win this",
                "even": "a real fight that could go either way",
                "dangerous": "the player is likely to be badly hurt or worse",
                "deadly": "the player will very likely die if they stand and fight"}
        count = f"{len(enemies)} of them" if len(enemies) > 1 else "one"
        if reserves:
            count += f", and {len(reserves)} more in the camp who will come if the noise carries"
        event = (f"{how} {creature.name.lower()} - {count}, {where} from the player. {manner} "
                 f"THE ODDS: {odds.get(label, label)}.")
        if opening_events:
            event += " As the fight begins: " + "; ".join(opening_events)
        ws.narrate_with(cp.START_SYSTEM, event)
        for line in prep + tether_notes:
            console.note(line)
        if pools.mechanic(c, "keen_judge") is not None:
            label = f"{label} - you judge your odds at {rate:.0%}"
        scene.show(danger=label)
        ws.store.save_combat(scene.to_json())
        return scene

    def to_json(self) -> str:
        return json.dumps({"creature": self.creature_name, "fight": self.fight.model_dump()})

    @classmethod
    def resume(cls, ws, raw: str) -> "CombatScene":
        data = json.loads(raw)
        return cls(ws, combat.Combat(**data["fight"]), data["creature"])

    # ---------- display ----------

    def pane_data(self, danger: str = "") -> dict:
        """The fight as plain data for the window's combat pane."""
        f, p = self.fight, self.fight.player
        def fighter(x):
            return {"id": x.id, "name": x.name, "level": x.level, "hp": round(x.hp), "max_hp": x.max_hp, "band": x.band,
                    "statuses": [[k, v] for k, v in x.statuses.items()], "elevated": x.elevated,
                    "stamina": round(x.stamina), "max_stamina": x.max_stamina, "mana": round(x.mana), "max_mana": x.max_mana}
        moves = []
        for m in p.moves:
            left = p.cooldowns.get(m.id, 0)
            if m.id in p.cooldowns:                     # your turn starts by ticking cooldowns down, so judge it as it will be then
                p.cooldowns[m.id] = max(0, left - 1)
            problem = combat.can_use(p, m, f)
            if m.id in p.cooldowns:
                p.cooldowns[m.id] = left
            cooling = left > 1                      # at 1 the move is ready by the time you act
            if problem and not cooling:
                reason = problem
            elif cooling:
                reason = f"ready in {left - 1} turn{'s' if left - 1 != 1 else ''}"
            else:
                reason = ""
            moves.append({"id": m.id, "name": m.name, "resource": m.resource, "cost": combat.cost_of(p, m, f), "effect": m.effect,
                          "tier": m.tier, "cooldown": m.cooldown, "left": max(0, left - 1), "ready": not reason, "reason": reason})
        you = fighter(p)
        you["buffs"] = [[b.get("name", k), b.get("rounds", 0)] for k, b in p.buffs.items()]
        return {"round": f.round, "danger": danger, "enemies": [fighter(e) for e in f.enemies()],
                "reserves": len(f.reserves), "allies": [fighter(a) for a in f.allies()], "you": you,
                "moves": moves, "hits": f.hits}

    def show(self, danger: str = "") -> None:
        if console.combat_state(self.pane_data(danger)):
            return
        p = self.fight.player
        lines = []
        if danger:
            head, _, rest = danger.partition(" - ")
            lines.append(f"⚔ Danger: {head.upper()}" + (f" ({rest})" if rest else ""))
        for e in self.fight.enemies():
            status = f" · {', '.join(e.statuses)}" if e.statuses else ""
            lines.append(f"{e.name} (lv {e.level}) {console.meter(e.hp, e.max_hp)} {round(e.hp)}/{e.max_hp} · {e.band}{status}")
        if self.fight.reserves:
            lines.append(f"... {len(self.fight.reserves)} more of them are still in the camp")
        for a in self.fight.allies():
            lines.append(f"ally {a.name} {console.meter(a.hp, a.max_hp)} {round(a.hp)}/{a.max_hp}")
        you = f"you {console.meter(p.hp, p.max_hp)} {round(p.hp)}/{p.max_hp}  ST {round(p.stamina)}  MP {round(p.mana)}"
        if p.elevated:
            you += " · elevated"
        if p.statuses:
            you += f" · {', '.join(p.statuses)}"
        if p.buffs:
            you += " · " + ", ".join(f"{b['name']} ({b['rounds']})" for b in p.buffs.values())
        lines.append(you)
        console.combat_panel(lines)

    # ---------- a round ----------

    def interpret(self, text: str) -> CombatIntent:
        p = self.fight.player
        abilities = []
        for m in p.moves:
            ready = combat.can_use(p, m, self.fight)
            note = "ready" if not ready else ready.rstrip(".")
            if m.effect == "relic":
                left = max(0, m.uses - p.relic_uses.get(m.id, 0))
                abilities.append(f"{m.id}: {m.name} (a power of a ring or amulet you wear: {m.text} {left} use{'s' if left != 1 else ''} left) - {note}")
                continue
            extra = AT.describe(m)
            abilities.append(f"{m.id}: {m.name} ({m.tier} {m.effect}, {m.reach}, {combat.cost_of(p, m, self.fight)} {m.resource})"
                             f"{' [' + extra + ']' if extra else ''} - {note}")
        enemies = [f"{e.id}: {e.name}, {e.band}" for e in self.fight.enemies()]
        allies = [f"{a.id}: {a.name}" for a in self.fight.allies()]
        usable = [inventory.label(i) for i in self.ws.player.character.inventory
                  if i.good and inventory.GOODS[i.good].combat]
        from scenes import markup
        if markup.has_markup(text):
            text = f"{text}\nMARKUP (asterisks are actions, quotes are speech):\n{markup.describe(text)}"
        return generate("combat_interpret", cp.INTERPRET_SYSTEM, cp.interpret_request(abilities, enemies, text, usable, allies),
                        CombatIntent, temperature=0.2, max_tokens=200)

    def turn(self, text: str) -> None:
        f = self.fight
        p = f.player
        intent = self.interpret(text)
        console.debug(f"combat intent: {intent.model_dump(exclude_defaults=True)}")
        f.log, f.story, f.hits = [], [], []
        target = f.get(intent.target) if intent.target else None
        if not target or not target.alive or target.side != "enemy":
            target = min(f.enemies(), key=lambda e: combat.BANDS.index(e.band))

        if not combat.start_turn(p, f):
            f.log.append(f"{p.name} is unable to act")
            combat.tell(f, "you try to act, but your body will not answer")
        elif intent.kind == "ability":
            move = next((m for m in p.moves if m.id == intent.ability), None)
            binder = self.binding_ability(move)
            problem = None
            if binder:
                self.try_bind(move, binder, target)
            else:
                give = self.buff_recipients(move, intent.buff_for) if move else None
                problem = combat.act_ability(f, p, move, target, self.rng, give=give) if move else "You don't know that ability."
            if problem:
                console.note(problem + " You attack instead.")
                combat.act_attack(f, p, target, self.rng)
        elif intent.kind == "item":
            problem = self.use_item(intent.item or text)
            if problem:
                console.note(problem + " You attack instead.")
                combat.act_attack(f, p, target, self.rng)
        elif intent.kind == "move":
            combat.act_move(f, p, intent.move or "closer", target)
        elif intent.kind == "defend":
            combat.act_defend(f, p)
        elif intent.kind == "flee":
            combat.act_flee(f, self.rng)
        elif intent.kind == "tame":
            c = self.ws.player.character
            binder = taming.binder(c) if not c.uses_companions else None
            move = next((m for m in p.moves if binder and m.id == binder.id), None)
            if move:
                self.try_bind(move, binder, target)
            else:
                self.try_tame(target)
        elif intent.kind == "other":
            f.log.append(f"{p.name} tries something unusual ({intent.summary or text}) but it has no clear effect")
            combat.tell(f, f"you try something unexpected ({intent.summary or text}), but it changes nothing")
        else:
            combat.act_attack(f, p, target, self.rng)

        if intent.kind != "flee":
            f.player_acted = True
        if not f.over and not f.enemies() and not combat.muster(f):
            f.over = "victory"
        if not f.over:
            combat.finish_round(f, self.rng)

        self.narrate_round(text)
        self.sync_player()
        if f.over:
            self.finish()
        else:
            self.show()
            self.ws.store.save_combat(self.to_json())

    def buff_recipients(self, move, wish: str) -> list | None:
        """Who a buff ability goes on: the player (default), one ally, or the player and every ally."""
        if move.effect != "buff" or not wish or wish == "self":
            return None
        f = self.fight
        allies = f.allies()
        if wish == "all":
            return [f.player] + allies if allies else None
        one = next((a for a in allies if a.id == wish or a.name.lower() == wish.lower()), None)
        return [one] if one else None

    def binding_ability(self, move):
        """The character's Bind a Beast ability if this move is it."""
        if not move:
            return None
        return next((a for a in self.ws.player.character.actives if a.id == move.id and a.field_use == "bind_beast"), None)

    def try_bind(self, move, ability, target) -> None:
        """Bind a Beast: a taught ability, once a day, odds set by the creature and the ability's tier; the bond is permanent."""
        f, c = self.fight, self.ws.player.character
        p = f.player
        creature = self.ws.world.bestiary.get(target.creature)
        wait = self.ws.field_ready_in(ability)
        problem = taming.bind_check(c, target, creature) or combat.can_use(p, move, f) or \
            (f"{ability.name} needs {clock.describe_duration(wait)} more before you can do it again." if wait else "")
        if problem:
            console.note(problem + " You attack instead.")
            combat.act_attack(f, p, target, self.rng)
            return
        cost = combat.cost_of(p, move, f)
        if move.resource == "stamina":
            p.stamina -= cost
        else:
            p.mana -= cost
        self.ws.field_cooldown_start(ability)
        if self.rng.random() < taming.bind_chance(c, target, creature, ability.tier):
            comp = taming.bind(c, creature, target.name)
            f.fighters.remove(target)
            self.tamed.append(comp.name)
            f.log.append(f"{f.player.name} binds {target.name} with {ability.name}; it is now a companion")
            combat.tell(f, f"{target.name} stops fighting and settles beside you - it is yours now ({comp.name}, a new companion)")
            console.note(f"{comp.name} is bound to you as a companion.")
        else:
            f.log.append(f"{f.player.name} tries to bind {target.name} with {ability.name}, but it will not yield")
            combat.tell(f, f"you reach for {target.name} with {ability.name}, but it breaks free and snaps at you")

    def try_tame(self, target) -> None:
        f, c = self.fight, self.ws.player.character
        creature = self.ws.world.bestiary.get(target.creature)
        problem = taming.check(c, target, creature)
        if problem:
            console.note(problem + " You attack instead.")
            combat.act_attack(f, f.player, target, self.rng)
            return
        if self.rng.random() < taming.chance(c, target, creature):
            comp = taming.bind(c, creature, target.name)
            f.fighters.remove(target)
            self.tamed.append(comp.name)
            f.log.append(f"{f.player.name} tames {target.name}; it is now a companion")
            combat.tell(f, f"{target.name} stops fighting and settles beside you - it is yours now ({comp.name}, a new companion)")
            console.note(f"{comp.name} is bound to you as a companion.")
        else:
            f.log.append(f"{f.player.name} tries to tame {target.name}, but it will not yield")
            combat.tell(f, f"you reach for {target.name}, but it will not yield and snaps at you")

    def narrate_round(self, text: str) -> None:
        f = self.fight
        p = f.player
        foes = [f"{combat.who(e)}, {combat.condition(e)}" for e in f.fighters if e.side == "enemy" and e.alive]
        you = combat.condition(p) + (", up on high ground" if p.elevated else "")
        result = fresh("combat_narrate", cp.NARRATE_SYSTEM,
                       cp.narrate_request(self.ws.place.name, self.ws.time_label(), text, f.story,
                                          p.weapon_name, you, foes, f.round - 1, self.ws.gear_line(),
                                          self.ws.recent_narration),
                       Narration, self.ws.recent_narration, max_tokens=600)
        text_out = place_figures(result.text, f.hits, console.damage_tags)
        console.narrate(text_out)
        self.ws.remember_narration(TAG.sub("", result.text))
        if config.COMBAT_NUMBERS and not console.damage_tags:
            console.combat_numbers(f.log)

    def use_item(self, name: str) -> str | None:
        """Use a consumable mid-fight. It takes the player's turn."""
        c, p, f = self.ws.player.character, self.fight.player, self.fight
        item = inventory.find(c.inventory, name)
        if not item or not item.good or not inventory.GOODS[item.good].combat:
            return "You have nothing like that to use in a fight."
        g = inventory.GOODS[item.good]
        inventory.take(c.inventory, g.name, 1)
        pools_now = {"health": ("hp", "max_hp"), "mana": ("mana", "max_mana"), "stamina": ("stamina", "max_stamina")}
        for pool, pct in g.restores.items():
            cur, top = pools_now[pool]
            setattr(p, cur, min(getattr(p, top), getattr(p, cur) + getattr(p, top) * pct / 100))
        for status in g.cures:
            p.statuses.pop(status, None)
        f.log.append(f"{p.name} uses {g.name}")
        combat.tell(f, f"you use {g.name} ({g.description.lower().rstrip('.')})")
        return None

    def sync_player(self) -> None:
        c, p = self.ws.player.character, self.fight.player
        c.health, c.stamina, c.mana = float(p.hp), float(p.stamina), float(p.mana)
        if c.orenna_breath and not p.breath:
            c.orenna_breath = False
            from engine import orenna
            console.note(orenna.O["blessing"]["spent"])

    # ---------- endings ----------

    def companions_after_fight(self, fallen_ids: set[str]) -> None:
        """A bonded companion who went down is out for a day; a beast may not survive, a summoned spirit only disperses."""
        ws = self.ws
        c = ws.player.character
        rules = combat.RULES["creatures"]["companion_fall"]
        changed = False
        for comp in c.companions:
            if f"ally_{comp.id}" not in fallen_ids or not comp.active:
                continue
            changed = True
            comp.fallen = True
            comp.recover_at = ws.minutes + int(rules["recover_hours"] * 60)
            if comp.creature in ws.world.bestiary and self.rng.random() < rules["death_chance"]:
                comp.dead = True
                console.note(f"{comp.name} is dead. It fell protecting you.")
            elif comp.creature in ws.world.bestiary:
                console.note(f"{comp.name} is badly hurt and will need a day to recover.")
            else:
                console.note(f"{comp.name} disperses. It will return in a day, or sooner if you call it again.")
        if changed:
            ws.store.save_player(ws.player)

    def finish(self) -> None:
        f, ws = self.fight, self.ws
        ws.store.save_combat(None)
        ws.combat = None
        if f.hits:
            console.combat_state(self.pane_data())
        console.combat_state(None)
        rounds = f.round
        ws.advance_quiet(max(1, math.ceil(rounds * combat.RULES["round_seconds"] / 60)))
        dead = [e for e in f.fighters if e.side == "enemy" and not e.alive]
        fallen = [a for a in f.fighters if a.side == "ally" and a.id.startswith("ally_") and not a.alive]
        events.fallen_allies(ws, {a.id for a in fallen})
        ws.party_after_fight(fallen)
        self.companions_after_fight({a.id for a in fallen})
        if f.over == "victory":
            self.victory()
            ws.dungeon_fight_over("victory")
            ws.road_fight_over("victory")
            ws.camp_fight_over("victory", dead)
            ws.orenna_fight_over("victory")
        elif f.over == "fled":
            console.note("You got away.")
            ws.dungeon_fight_over("fled")
            ws.road_fight_over("fled")
            ws.camp_fight_over("fled", dead)
            ws.orenna_fight_over("fled")
            ws.recently_fled = True
        elif self.phoenix():
            ws.dungeon_fight_over("fled")
            ws.road_fight_over("fled")
            ws.camp_fight_over("fled", dead)
            ws.orenna_fight_over("fled")
            ws.recently_fled = True
        else:
            ws.dungeon_fight_over("defeat")
            ws.road_fight_over("defeat")
            ws.camp_fight_over("defeat", dead)
            ws.orenna_fight_over("defeat")
            self.defeat()
        events.release_allies(ws)
        ws.store.save_player(ws.player)

    def phoenix(self) -> bool:
        """A Phoenix item turns one killing blow aside every few days: half health, nothing lost, the fight is over."""
        ws = self.ws
        c = ws.player.character
        item = next((i for i in c.equipment.values() if i.legendary_effect == "phoenix"), None)
        if not item:
            return False
        day = clock.day(ws.minutes)
        wait = items.LEGENDARY["phoenix"].value
        if day - c.phoenix_day < wait:
            return False
        c.phoenix_day = day
        for pool in pools.POOLS:
            setattr(c, pool, float(pools.maximum(c, pool)) * (0.5 if pool == "health" else 1.0))
        console.note(f"The killing blow lands - and {items.display_name(item)} burns white. You rise from the ashes at half strength; "
                     f"the fight is over. (It cannot do this again for {wait:g} days.)")
        ws.narrate("A killing blow falls on the player, but their Phoenix relic flares and refuses it. They stagger up, alive, the "
                   "enemies recoiling or gone. Describe it in two vivid sentences.")
        return True

    def victory(self) -> None:
        c = self.ws.player.character
        dead = [e for e in self.fight.fighters if e.side == "enemy" and not e.alive]
        if not dead and self.tamed:
            console.note(f"The fight is over. {', '.join(self.tamed)} follows you now.")
            self.sync_player()
            return
        if not dead:
            if getattr(self.ws, "orenna_fight", None) != "executioner":
                console.note("They got away - nothing to show for it this time.")
            self.sync_player()
            return
        self.ws.record_kills(dead)
        if self.ws.place.danger and self.ws.owns("victors_name"):
            self.ws.reputation_add(self.ws.nearest_town(self.ws.player.location), 1)
        pack = combat.RULES["creatures"].get("pack", {})
        pack_xp = (pack.get("health", 1) + pack.get("damage", 1)) / 2
        ledger = 1 + (pools.mechanic(c, "deaths_ledger") or 0) / 100
        total_xp = round(sum(leveling.kill_xp(c.level, e.level, e.rank)
                             * (pack_xp if self.ws.world.bestiary[e.creature].group[0] >= 2 else 1)
                             * (ledger if e.category == "undead" else 1) for e in dead))
        coins, found = 0, []
        scavenger = pools.mechanic(c, "scavenger") or 0
        state = self.ws.store.load_place(self.ws.player.location)
        skinnable = 0
        bodies = {e.id: {"creature": e.creature, "name": e.name, "level": e.level, "category": e.category, "rank": e.rank,
                         "minute": self.ws.minutes, "asked": False} for e in dead}
        for e in dead:
            if e.rank == "boss":
                gained, prizes = loot.boss_drops(e, self.rng, loot.keeps_companions(c))
                coins += gained
                for prize in prizes:
                    if prize.rarity in ("rare", "epic", "legendary"):
                        self.name_item(prize, e.name)
                    found.append(prize)
                if prizes:
                    bodies[e.id]["carried"] = inventory.label(prizes[0])
                kit = (e.boss or {}).get("kit") or bosses.kit_for(e.category)
                tier = (e.boss or {}).get("tier") or "dungeon"
                if self.rng.random() < bosses.B["relic_chance"].get(tier, 0):
                    relic = accessories.boss_relic(kit, e.level, self.rng)
                    self.name_item(relic, e.name, self.story_around(e.name, e.boss or {"kit": kit, "tier": tier}))
                    found.append(relic)
                if loot.has_remains(e):
                    state.carcasses.append({"creature": e.creature, "level": e.level, "minute": self.ws.minutes})
                    skinnable += 1
                continue
            gained, item = loot.drops(e, self.rng, loot.keeps_companions(c))
            if loot.has_remains(e):
                state.carcasses.append({"creature": e.creature, "level": e.level, "minute": self.ws.minutes})
                skinnable += 1
            plunder = (pools.mechanic(c, "last_possessions") or 0) if e.category in ("hostile people", "person template") else 0
            coins += round(gained * (1 + scavenger / 100) * (1 + plunder / 100))
            lucky = pools.mechanic(c, "lucky_find") or 0
            if not item and lucky and self.rng.random() < lucky / 100:
                item = loot.drops(e, self.rng, loot.keeps_companions(c))[1]
            if item:
                if item.rarity in ("rare", "epic", "legendary"):
                    self.name_item(item, e.name)
                found.append(item)
                bodies[e.id]["carried"] = inventory.label(item)
        state.bodies = self.ws.keep_bodies(state.bodies + list(bodies.values()))
        self.ws.store.save_place(state)
        c.coins += coins
        for item in found:
            self.ws.to_pack(item)
        levels = leveling.gain_xp(c, total_xp)
        noticed = [items.display_name(i) if i.rarity == "legendary" else inventory.label(i) for i in found]
        if coins:
            noticed.append("a few coins")
        fallen = ", ".join(combat.who(e) for e in dead)
        aftermath = fresh(
            "combat_aftermath", cp.AFTERMATH_SYSTEM,
            f"PLACE: {self.ws.place.name}\nTIME AND WEATHER: {self.ws.time_label()}\nTHE PLAYER: {self.ws.gear_line()}\n"
            f"THE PLAYER IS: {combat.condition(self.fight.player)}\nTHE FALLEN: {fallen}\n"
            f"THE PLAYER FINDS: {', '.join(noticed) or 'nothing'}\n"
            "RECENT NARRATION:\n" + "\n".join(f"  - {r}" for r in self.ws.recent_narration[-3:]),
            Narration, self.ws.recent_narration, max_tokens=400)
        console.narrate(aftermath.text)
        self.ws.remember_narration(aftermath.text)
        console.note(f"Victory. +{total_xp} XP" + (f", {money.fmt(coins)}" if coins else ""))
        for item in found:
            if item.rarity == "legendary":
                console.legendary_reveal(item)
            else:
                console.note(f"Found: {item.name} ({item.rarity}) - {items.summary(item)}")
        if levels:
            console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
        if skinnable:
            console.note(f"The fallen can be skinned or butchered for {'their' if skinnable > 1 else 'its'} hide and meat - "
                         "say so if you want to.")

    FALLBACK_FIRST = ["Ashen", "Hollow", "Ember", "Gloam", "Thorn", "Dusk", "Varr", "Kestrel", "Wraith", "Sable", "Oath", "Rime"]
    FALLBACK_SECOND = ["fang", "bane", "ward", "song", "reach", "brand", "mourn", "keep", "bite", "light", "fall", "shard"]

    def fallback_name(self, item: Item, source: str) -> None:
        """The engine's own name for an item when the model cannot supply one. A failed naming must never cost the player the fight's rewards."""
        b = items.base_of(item)
        label = b.label or b.name
        if item.rarity != "legendary":
            item.name = f"{item.rarity.capitalize()} {label}"
            item.description = f"Taken from {source}."
            return
        taken = {t.lower() for t in self.ws.store.legendary_names()}
        rng = random.Random(f"{item.uid}:{len(taken)}")
        for _ in range(200):
            name = rng.choice(self.FALLBACK_FIRST) + rng.choice(self.FALLBACK_SECOND)
            if name.lower() not in taken:
                break
        else:
            name = f"{label} {len(taken) + 1}"
        item.name = name
        item.title = f"the {label.title()} of {source}"
        item.description = f"A {label} of uncommon make, carried off from {source}. No song has been sung of it yet."
        self.ws.store.add_legendary_name(item.name)

    def name_item(self, item: Item, source: str, story: str = "") -> None:
        try:
            if accessories.is_accessory(item) and (item.trait or item.relic):
                self.ask_accessory_name(item, source, story or self.story_around(source))
            else:
                self.ask_name(item, source)
        except LLMError:
            self.fallback_name(item, source)

    def story_around(self, source: str, boss=None) -> str:
        """What the playthrough knows that a relic's history can be built from: who fell, where, who carries it, what has been happening."""
        ws, c = self.ws, self.ws.player.character
        parts = [f"THE ONE WHO FELL: {source}" + (f" ({boss.get('kit')} kind, a {boss.get('tier')} foe)" if boss else ""),
                 f"WHERE: {ws.place.name}", f"WHO WILL WEAR IT: {c.name}, level {c.level}"]
        if boss and boss.get("lines", {}).get("fall"):
            parts.append(f"HOW IT FELL: {boss['lines']['fall']}")
        if boss and boss.get("lines", {}).get("intro"):
            parts.append(f"WHAT IT SAID WHEN IT CAME: {boss['lines']['intro']}")
        recent = ws.recent_narration[-3:]
        if recent:
            parts.append("WHAT HAS JUST HAPPENED:\n" + "\n".join(f"  - {r}" for r in recent))
        return "\n".join(parts)

    def ask_accessory_name(self, item: Item, source: str, story: str = "") -> None:
        """A ring or amulet is named, and its power named, from the playthrough's own story. Nothing about what it does is the model's to decide."""
        b = items.base_of(item)
        store = self.ws.store
        legendary = item.rarity == "legendary"
        lane = accessories.A["lanes"].get(item.trait.get("lane", ""), {})
        mat = items.material_of(item)
        what = f"{mat.name + ' ' if mat else ''}{b.label or b.name}" + (f" set with {items.GEMS[item.gem].name}" if item.gem else "")
        effect = items.LEGENDARY.get(item.legendary_effect)
        powers = "; ".join(accessories.lines(item)) or "none"
        named = generate(
            "accessory_name",
            "You name a ring or amulet in a fantasy role-playing game, and write where it came from. It must feel like it belongs to THIS "
            "story: use the people, places and events given, never invent famous names from outside them. name: one to three words, a proper "
            "name. title: " + ("a title beginning with 'the'. " if legendary else "leave empty. ") + "lore: one or two sentences of history that "
            "explain why the piece does what it does (its lane and its power), without numbers or game terms. power_name: two to four words naming "
            "the power in the voice of the piece's history (never a game term, never a boss's name, never 'ability'). "
            "Never reuse a name listed as taken. Respond only with JSON matching the schema.",
            f"PIECE: {what}\nSUITS: {lane.get('flavor', 'any wearer')}\nWHAT IT DOES: {powers}"
            + (f"\nWONDER: {effect.name} - {effect.text()}" if effect else "")
            + f"\nPOWER NOW CALLED: {item.relic.get('name', 'none') if item.relic else 'none'}\n"
            + (story or f"FOUND ON: {source}") + f"\nTAKEN NAMES: {', '.join(store.legendary_names()) or 'none'}",
            AccessoryName, temperature=0.95, max_tokens=300,
            validation_context={"taken": store.legendary_names(), "need_title": legendary, "need_power": bool(item.relic)},
        )
        item.name, item.title, item.description = named.name.strip(), named.title.strip() if legendary else "", named.lore.strip()
        if item.relic and named.power_name.strip():
            item.relic["name"] = named.power_name.strip()
        store.add_legendary_name(item.name)

    def ask_name(self, item: Item, source: str) -> None:
        b = items.base_of(item)
        props = "; ".join(items._describe_effect(e) for e in items.to_flat(
            [items.Effect(modifies=p.modifies, trigger=p.trigger, magnitude=p.magnitude) for p in item.properties], item.item_level))
        if item.rarity == "legendary":
            effect = items.LEGENDARY.get(item.legendary_effect)
            mat = items.material_of(item)
            store = self.ws.store
            named = generate(
                "legendary_name",
                "You name a legendary item in a fantasy role-playing game. It must feel singular, like a weapon or relic "
                "from a song. name: one to three words, a proper name (e.g. Vaelith, Dawnbreaker, The Grey Oath). "
                "title: a title beginning with 'the' (e.g. the Last Ember, Bane of Kings). lore: one or two sentences "
                "of history - who made or carried it and what it is remembered for. No numbers, no game terms. "
                "Never reuse a name listed as taken. Respond only with JSON matching the schema.",
                f"ITEM: {mat.name + ' ' if mat else ''}{b.label or b.name}\nPOWER: {effect.name + ' - ' + effect.text() if effect else 'none'}"
                f"\nPROPERTIES: {props}\nFOUND ON: {source}\nTAKEN NAMES: {', '.join(store.legendary_names()) or 'none'}",
                LegendaryName, temperature=0.95, max_tokens=250,
                validation_context={"taken": store.legendary_names()},
            )
            item.name, item.title, item.description = named.name.strip(), named.title.strip(), named.lore.strip()
            store.add_legendary_name(item.name)
            return
        named = generate("loot_name",
                         "Name a found item in a fantasy role-playing game. Short evocative name (2-4 words) and one "
                         "sentence of description. No numbers. Respond only with JSON matching the schema.",
                         f"ITEM: {item.rarity} {b.name}\nPROPERTIES: {props}\nFOUND ON: {source}",
                         LootName, temperature=0.9, max_tokens=150)
        item.name, item.description = named.name.strip(), named.description.strip()

    def defeat(self) -> None:
        ws = self.ws
        c = ws.player.character
        summary = death.die(c)
        lost = [f"half their gold ({summary['coins']} gone, {summary['kept']} kept)" if summary['coins_raw'] else "nothing - their purse was spared"]
        console.note("You have died.")
        console.wait("Darkness. Then the sourceless light of the Threshold, dimmer than you remember.")
        line = generate("goddess_line", gp.goddess_system(ws.goddess_knowledge()),
                        gp.narration_request("death", cp.THRESHOLD_EVENT.format(deaths=c.deaths, losses="; ".join(lost)), []),
                        GoddessLine, temperature=0.9)
        console.say(line.speech, "The Goddess")
        console.note("Lost: " + " · ".join(lost))
        days = combat.RULES["death"]["days_pass"]
        ws.advance_quiet(days * clock.MINUTES_PER_DAY)
        pools.fill_missing(c)
        ws.player.delve = None           # waking at the Threshold, never inside a dungeon
        ws.party_disband(None, "you fell")
        wake = c.last_rest if c.last_rest in ws.world.places else ws.world.start_location
        ws.enter(wake)
        ws.narrate(f"{days} days have passed in the world. The player wakes here, alive again, a lighter purse and nothing else lost. "
                   "They are thrown back by the goddess's failing light and wake with a sharp, ragged gasp. Describe waking, brief and stark.")
        ws.show_exits()
