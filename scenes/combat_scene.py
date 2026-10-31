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
from engine import entities
from engine import ability_traits as AT
from engine import accessories, bosses, inventory, clock, combat, death, events, items, ledger, leveling, loot, mentor, money, party, pools, taming
from llm.contracts import AccessoryName, CombatIntent, GoddessLine, LegendaryName, LootName, Narration
from llm.gateway import LLMError, generate
from scenes import combat_prompts as cp
from scenes import goddess_prompts as gp
from scenes.voice import fresh
from ui import console


def whose_blow(by: str) -> str:
    """(f412) 'the third pirate's blow', 'your blow': the blow that put someone down, from who struck it."""
    return "your blow" if by == "you" else f"{by}'s blow"


ROLE_PROFILES = {
    "striker": {"strength": 14, "dexterity": 15, "constitution": 11, "intelligence": 6, "wisdom": 10, "charisma": 6},
    "guardian": {"strength": 15, "dexterity": 9, "constitution": 16, "intelligence": 6, "wisdom": 10, "charisma": 6},
    "rogue": {"strength": 10, "dexterity": 16, "constitution": 10, "intelligence": 8, "wisdom": 12, "charisma": 6},
    "healer": {"strength": 8, "dexterity": 11, "constitution": 12, "intelligence": 10, "wisdom": 16, "charisma": 10},
    "support": {"strength": 8, "dexterity": 12, "constitution": 11, "intelligence": 12, "wisdom": 14, "charisma": 12},
}


# (f419) a marker the model wrapped in a parenthesis or wrote with a '#' ('([h3])', '(#h4)') is taken whole: before, the inner one was
# taken and '()' was left on the screen
TAG = re.compile(r"\s*(?:\(\s*[\[\{]\s*#?\s*h\d+\s*[\]\}]\s*\)|[\[\(\{]\s*#?\s*h\d+\s*[\]\)\}])", re.IGNORECASE)
TAG_N = re.compile(r"\s*(?:\(\s*[\[\{]\s*#?\s*h(\d+)\s*[\]\}]\s*\)|[\[\(\{]\s*#?\s*h(\d+)\s*[\]\)\}])", re.IGNORECASE)


def tag_number(m) -> int:
    """The blow a TAG_N match marks, whichever form it took."""
    return int(m.group(1) or m.group(2))


_END = re.compile(r"[.!?]+[\"'”’]*(?=\s|$)")
_STOPWORDS = {"that", "this", "with", "from", "into", "onto", "their", "them", "they", "your", "yours", "what", "when", "then", "than",
              "there", "here", "have", "were", "been", "upon", "over", "under", "each", "just", "only", "against", "across", "before", "after"}


def _sense(text: str) -> set[str]:
    """The words of a line that say what happened in it, cut to their stems: 'wolves' and 'wolf', 'sweeps' and 'sweep' meet."""
    out = set()
    for w in re.findall(r"[a-z]{4,}", (text or "").lower()):
        if w in _STOPWORDS:
            continue
        for end in ("ing", "ed", "es", "s"):
            if w.endswith(end) and len(w) - len(end) >= 4:
                w = w[:-len(end)]
                break
        out.add("wolf" if w == "wolve" else w)
    return out


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Where each sentence of the passage starts and ends, its closing quote included; the spaces and line breaks between are left out."""
    spans, start = [], 0
    for m in _END.finditer(text):
        if text[start:m.end()].strip():
            spans.append((start, m.end()))
        start = m.end()
    if text[start:].strip():
        spans.append((start, len(text.rstrip())))
    return spans


def seat_missing(text: str, hits: list[dict], story: list[str]) -> str:
    """(f377) Each blow's tag the narrator left out, put back at the end of the sentence that tells that blow, rather than on the end of
    the passage, where a killing blow's figure read as belonging to the last miss. The sentence is found between the blows told before
    and after it (the tags keep the events' order), as the one sharing most of the engine's own words for that blow (its story line:
    who struck, with what, at whom, how it ended); with nothing shared, the last sentence before the next blow. Nothing else in the
    passage moves."""
    want = sorted(int(h["tag"][1:]) for h in hits if h.get("figure") and str(h.get("tag", "")).startswith("h") and h["tag"][1:].isdigit())
    for k in want:
        spans = _sentence_spans(text)
        if not spans:
            return text
        at = {}
        for i, (a, b) in enumerate(spans):
            for m in TAG_N.finditer(text[a:b]):
                at.setdefault(tag_number(m), i)
        if k in at:
            continue
        before = [i for n, i in at.items() if n < k]
        after = [i for n, i in at.items() if n > k]
        lo, hi = (max(before) + 1 if before else 0), (min(after) if after else len(spans))
        if lo >= hi and after:                         # told in the same sentence as the blow after it: just before that blow's tag
            a, b = spans[hi]
            nxt = next(m for m in TAG_N.finditer(text[a:b]) if tag_number(m) > k)
            text = text[:a + nxt.start()] + f" [h{k}]" + text[a + nxt.start():]
            continue
        told = _sense(TAG_N.sub("", next((s for s in story if f"[h{k}]" in s), "")))
        window = range(lo, hi) if lo < hi else [len(spans) - 1]          # after every blow told: the last sentence
        best = max(window, key=lambda i: (len(told & _sense(TAG_N.sub("", text[spans[i][0]:spans[i][1]]))), i))
        a, b = spans[best]
        m = re.search(r"([.!?]+)([\"'”’]*)$", text[a:b])
        cut = b if not m or m.group(2) else a + m.start()  # before the full stop; after a closing quote, never inside the words said
        text = text[:cut] + f" [h{k}]" + text[cut:]
    return text


def place_figures(text: str, hits: list[dict], window: bool, story: list[str] = ()) -> str:
    """Swap each blow's tag in the narration for its figure, e.g. '(14 damage)'. (f377) A blow's tag the narrator left out is put back
    on the sentence that tells it (seat_missing); any figure still without a place goes on the end, so a blow is never without its
    number. In the window a figure is a hoverable token (⟦id|figure⟧); in the terminal plain text."""
    text = seat_missing(text, hits, list(story))
    by_tag = {h['tag']: h for h in hits if h.get('figure')}
    used = set()
    def fig(h):
        return f"⟦{h['id']}|{h['figure']}⟧" if window else h['figure']
    def sub(m):
        h = by_tag.get(f'h{tag_number(m)}')
        if not h or h['tag'] in used:
            return ''
        used.add(h['tag'])
        return ' ' + fig(h)
    text = TAG_N.sub(sub, text)
    missing = [fig(h) for t, h in by_tag.items() if t not in used]
    return text + (' ' + ' '.join(missing) if missing else '')


class _Shape:
    """A minimal creature-like stand-in for a companion whose kind is missing from the bestiary."""
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
        self.fight_shown: list[str] = []            # (f349) what the player has read in this fight: the ground, the light, each foe's look

    def note_fight_shown(self, text: str) -> None:
        """(f349) After a passage: the ground and the place are given; the light if it was described; the look of each foe it described;
        the blade once it has gleamed. The next passage is told not to describe them again."""
        import re
        from engine import voice_rules
        low = (text or "").lower()
        if not low.strip():
            return
        def add(line):
            if line not in self.fight_shown:
                self.fight_shown.append(line)
        add("the ground and the place: given; name only what changes")
        if any(re.search(rf"\b{w}\w*", low) for w in voice_rules.V.get("weather_words", [])) or re.search(r"\b(light|dark|shadow|glow|gleam|dim)\w*", low):
            add("the light and the weather")
        if re.search(r"\b(blade|edge|steel|sword|axe|spear|knife|dagger|mace|hammer|bow|arrow|staff)\b", low) and re.search(r"\b(gleam|glint|catch|flash|shine|bright|silver)\w*", low):
            add("the gleam of a blade")
        for e in self.fight.fighters:
            if e.side != "enemy":
                continue
            head = combat.who(e).split()[-1].lower()
            if len(head) >= 4 and re.search(rf"\b{re.escape(head)}s?\b", low):
                add(f"the look of {combat.who(e)}: what it is, its size and bearing")

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
            ally = combat.companion_fighter(shape, c.level, f"ally_{comp.id}", comp.name, gift=comp.source == "gift")
            near.append(ally)
        near = taming.strongest(near, c.level)
        for note in party.sync_levels(ws.player.party, c.level):
            console.note(note)
        members = [party.fighter(m, minutes=ws.minutes) for m in ws.player.party if not m.get("tutorial")]
        if members and not (hold and ws.player.party_mode == "hold"):
            ws.habits("fight_start")
        if hold and ws.player.party_mode == "hold":
            return near, members
        return near + members, []

    @classmethod
    def begin(cls, ws, creature, enemies: list[combat.Fighter], how: str, reserves: list[combat.Fighter] | None = None,
              wave: tuple[int, int, int] = (2, 2, 1), prepare=None, duel: str = "", big: str = "",
              initiated: bool = False, told: str = "") -> "CombatScene":
        # told (f404): the passage that already showed the foe arrive, a scripted entrance; the fight's opening is not narrated again
        c = ws.player.character
        if not duel:
            events.recruit_allies(ws, enemies)
        prep = [] if duel else ws.field_prep(enemies)
        fighters = [combat.fighter_from_character(c)]
        from engine import spells
        for m in fighters[0].moves:                       # (f397) a named spell cast within its days is not ready this fight
            a = next((x for x in c.actives if x.id == m.id), None)
            if a is not None and spells.day_locked(c, a, ws.minutes):
                fighters[0].cooldowns[m.id] = 10 ** 6
        near, later = ([], []) if duel else cls.allies(ws, hold=bool(getattr(ws, "camp_fight", None)))
        fighters += near
        tether_notes = ws.tether_for(near)
        fight = combat.Combat(fighters=fighters + enemies, place=ws.place.name, conditions=sorted(ws.conditions()))
        fight.record = True                 # keep a breakdown of every blow for the window's combat log
        from engine import battlefield, battlefield_builder
        fight.battlefield = battlefield_builder.for_scene(ws, duel=bool(duel),
                                                          big="" if duel else battlefield_builder.big_kind(enemies, reserves or [], big))
        if duel:
            fight.duel, fight.no_rewards = True, True
        fight.ally_reserves = later
        fight.ally_arrive = party.P["hold_arrival_round"]
        fight.gentle = pools.mechanic(c, "gentle_approach") is not None
        fight.reserves = list(reserves or [])
        fight.reinforce_every, fight.reinforce_count, fight.reinforce_from = wave
        if not duel:
            from engine import summons
            summons.join_bound(fight, c)     # the Bound summon walks in with them, whole (unless it was unmade and not yet made again)
        battlefield.place_fighters(fight)
        scene = cls(ws, fight, creature.name)
        if initiated and not duel:
            named = [i for i in (ws.fight_buffs() if hasattr(ws, "fight_buffs") else []) if i not in (c.prebuffs or [])]
            prep += combat.prebuff(fight, list(c.prebuffs or []) + named, scene.rng)   # the player picked the moment: their buffs go up first (f247, f248)
            if big != "camp" and getattr(ws, "sneaking", False):     # they crept up on it: stealth decides surprise (a camp rolls its own)
                ws.sneaking = False
                degree = ws.resolve("stealth")
                if degree in ("success", "strong success"):
                    caught = combat.surprise(fight)
                    if caught:
                        combat.tell(fight, ", ".join(combat.who(e) for e in caught) + (" never see" if len(caught) > 1 else " never sees")
                                    + " you coming - caught unaware")
                else:
                    combat.tell(fight, "they see you coming at the last moment - no surprise")
        combat.opening(fight, scene.rng)
        opening_events = [TAG.sub("", e) for e in fight.story]          # the opening blows are logged, not narrated with figures
        fight.log, fight.story = [], []
        label, rate = combat.danger(fight)
        console.debug(f"danger estimate: {rate:.0%} win rate")
        if prepare:
            prepare(fight)                  # a scripted fight sets itself up after the estimate, so the estimate is of the fight as it looks
        manner = {"aggressive": "They mean to attack.",
                  "territorial": "It holds its ground and warns the player off - they could still back away.",
                  "passive": "It turns on the player."}[creature.temperament]
        where = "far off" if enemies and all(e.starts_far for e in enemies) else "close at hand"
        odds = {"trivial": "no real threat", "favorable": "the player should win this",
                "even": "a real fight that could go either way",
                "dangerous": "the player is likely to be badly hurt or worse",
                "deadly": "the player will very likely die if they stand and fight"}
        ground = ""
        if fight.battlefield and len(fight.battlefield.zones) > 1:
            from engine import battlefield as bfm
            names = [f"{z.name}{' (' + ', '.join(z.tags) + ')' if z.tags else ''}" for z in fight.battlefield.zones.values()]
            ground = f" THE GROUND: {names[0]}, with {', '.join(names[1:])} close by."
            if fight.battlefield.kind:                       # a big field: say where everyone stands, so the scale is told right
                ground = " THE GROUND (a wide field): " + bfm.narrative_snapshot(fight).replace("\n", "; ") + "."
        elif fight.battlefield and fight.battlefield.zones[fight.battlefield.start].has("narrow"):
            ground = f" THE GROUND: {fight.battlefield.zones[fight.battlefield.start].name} - narrow, only a few can come at one person at once."
        count = f"{len(enemies)} of them" if len(enemies) > 1 else "one"
        if reserves:
            count += f", and {len(reserves)} more in the camp who will come if the noise carries"
        event = (f"{how} {creature.name.lower()} - {count}, {where} from the player. {manner}{ground} "
                 f"THE ODDS: {odds.get(label, label)}.") if not duel else (
                 f"{duel} Neither fighter means to kill: the first clean blow that would end the other decides it. THE ODDS: {odds.get(label, label)}.")
        if opening_events:
            event += " As the fight begins: " + "; ".join(opening_events)
        start_habits = ws.habits_due("fight_start")             # (f412) the companions' habits as it begins, told in the opening
        if told:                                             # (f404) a scripted entrance already showed it: told once, not twice
            ws.remember_narration(told)
            scene.note_fight_shown(told)
        else:
            if start_habits:
                from scenes import world_prompts as wp
                event += f" {wp.HABITS_HEAD}: {' '.join(start_habits)}"
            ws.narrate_with(cp.START_SYSTEM, event)
            scene.note_fight_shown(ws.recent_narration[-1] if ws.recent_narration else "")      # (f349) the opening passage is read
        for line in prep + tether_notes:
            console.note(line)
        if pools.mechanic(c, "keen_judge") is not None:
            label = f"{label} - you judge your odds at {rate:.0%}"
        sworn = next((p.subject for p in c.passives if p.mechanic == "sworn_enemy" and p.subject), "")
        if sworn and getattr(creature, "category", "") == sworn:
            pace_word = {"slow": "slow - it cannot follow a quick step", "fast": "fast - it will run you down",
                         "normal": "no quicker than you"}[enemies[0].pace if enemies else "normal"]
            label = f"{label} - a sworn foe: you read it at a glance ({rate:.0%} odds, {pace_word})"
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

    def spot(self, x) -> str:
        """Where someone stands, in a few plain words: whom they are on, their row, or which part of the field they are in."""
        f = self.fight
        p = f.player
        if x.engaged_with:
            if p.id in x.engaged_with and x.side == "enemy":
                return "on you"
            names = [o.name.split()[0] for o in f.fighters if o.id in x.engaged_with and o.alive]
            return f"tied up with {names[0]}" if names else "in the melee"
        here = f.battlefield.zones.get(x.zone_id).name if f.battlefield and x.zone_id in f.battlefield.zones else ""
        if f.battlefield and x.zone_id != p.zone_id:
            return f"at {here}" if here else "at a distance"
        return {"front": "at the front", "back": "at the back", "loose": "moving loose"}[x.row] if x.row in ("front", "back", "loose") else "near"

    @staticmethod
    def status_label(x, status: str) -> str:
        """A status as the pane names it: poison says its stacks, and which of them will not fade (f268)."""
        if status == "poisoned":
            n, fixed = len(x.poison) + len(x.poison_fixed), len(x.poison_fixed)
            return f"poisoned ({n} stack{'s' if n != 1 else ''}" + (f", {fixed} won't fade" if fixed else "") + ")"
        return status.replace("_", " ")

    def pane_data(self, danger: str = "") -> dict:
        """The fight as plain data for the window's combat pane."""
        f, p = self.fight, self.fight.player
        def fighter(x):
            return {"id": x.id, "name": x.name, "level": x.level, "hp": round(x.hp), "max_hp": x.max_hp, "where": self.spot(x),
                    "zone": f.battlefield.zones[x.zone_id].name if f.battlefield and x.zone_id in f.battlefield.zones else "",
                    "row": x.row, "engaged": list(x.engaged_with),
                    "statuses": [[self.status_label(x, k), v] for k, v in x.statuses.items()], "elevated": "elevated" in x.position_tags,
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
            moves.append({"id": m.id, "name": m.name, "resource": m.resource, "cost": combat.cost_of(p, m, f),
                          "stamina_cost": combat.stamina_part(p, m, f), "effect": m.effect,
                          "tier": m.tier, "cooldown": m.cooldown, "left": max(0, left - 1), "ready": not reason, "reason": reason,
                          "tip": self.move_tip(m)})
        items_now = []
        for it in self.ws.player.character.inventory:
            if not it.good or not inventory.GOODS[it.good].combat:
                continue
            g = inventory.GOODS[it.good]
            reason = "not allowed in a trial" if f.duel else ("one item a turn" if f.item_round == f.round else "")
            effect = ", ".join([f"restores {pct:g}% {pool}" for pool, pct in g.restores.items()] + [f"cures {c}" for c in g.cures])
            items_now.append({"name": g.name, "qty": it.quantity, "text": effect or g.description, "ready": not reason, "reason": reason})
        you = fighter(p)
        you["buffs"] = [[b.get("name", k), b.get("rounds", 0)] for k, b in p.buffs.items()]
        return {"round": f.round, "danger": danger, "enemies": [fighter(e) for e in f.enemies()],
                "reserves": len(f.reserves), "allies": [fighter(a) for a in f.allies()], "you": you,
                "moves": moves, "items": items_now, "hits": f.hits, "over": f.over or ""}

    def move_tip(self, m) -> list:
        """(f405) An ability's full card on hover, as the character pane shows it; a relic's power by what it does."""
        c = self.ws.player.character
        a = next((x for x in c.actives if x.id == m.id), None)
        if a is not None:
            return console.ability_tip(a, c.level)
        return [["h", m.name]] + ([["", m.text]] if getattr(m, "text", "") else [])

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
            lines.append(f"{e.name} (lv {e.level}) {console.meter(e.hp, e.max_hp)} {round(e.hp)}/{e.max_hp} · {self.spot(e)}{status}")
        if self.fight.reserves:
            lines.append(f"... {len(self.fight.reserves)} more of them are still in the camp")
        for a in self.fight.allies():
            lines.append(f"ally {a.name} {console.meter(a.hp, a.max_hp)} {round(a.hp)}/{a.max_hp}")
        if self.fight.battlefield and len(self.fight.battlefield.zones) > 1:
            zs = self.fight.battlefield.zones
            lines.append("ground: " + " · ".join(f"{z.name}{' (' + ', '.join(z.tags) + ')' if z.tags else ''}" for z in zs.values()))
        you = f"you {console.meter(p.hp, p.max_hp)} {round(p.hp)}/{p.max_hp}  ST {round(p.stamina)}  MP {round(p.mana)}"
        if "elevated" in p.position_tags:
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
            if m.effect == "mobility":
                from engine import movement as _mv
                extra = ("[movement, whole turn] " if _mv.whole_turn(m) else "[movement, alongside an action] ") + extra
            grade = __import__("engine.spells", fromlist=["grade"]).grade(m)       # (f397) a spell's rank and form; (f400) none for a buff
            abilities.append(f"{m.id}: {m.name} ({(grade + ' ') if grade else ''}{m.effect}, {m.reach}, {combat.cost_of(p, m, self.fight)} {m.resource}"
                             + (f" + {combat.stamina_part(p, m, self.fight)} stamina" if combat.stamina_part(p, m, self.fight) else "") + ")"
                             f"{' [' + extra + ']' if extra else ''} - {note}")
        enemies = [f"{e.id}: {e.name}, {self.spot(e)}" for e in self.fight.enemies()]
        allies = [f"{a.id}: {a.name}" for a in self.fight.allies()] + \
                 [f"{a.id}: {a.name} (fallen)" for a in self.fight.fighters if a.side == "ally" and not a.alive and not a.counters.get("dead")]
        usable = [inventory.label(i) for i in self.ws.player.character.inventory
                  if i.good and inventory.GOODS[i.good].combat]
        from scenes import markup
        if markup.has_markup(text):
            text = f"{text}\nMARKUP (asterisks are actions, quotes are speech):\n{markup.describe(text)}"
        return generate("combat_interpret", cp.INTERPRET_SYSTEM, cp.interpret_request(abilities, enemies, text, usable, allies),
                        CombatIntent, temperature=0.2, max_tokens=200)

    ORDER_WORDS = (                                  # (f384) any form of the verb ("Fenris attacks the troll"), and the ways a blow is asked for
        ("hold", r"\b(hold (back|off|here)|stay back|hang back|stand down|stand back|keep back|stay out of it)\b"),
        ("back", r"\b(behind me|fall back|to the back|back row)\b"),                 # (f406) "get behind me": the back row, still acting
        ("heal", r"\b(heal|mend|tend|patch me|bandage|look after me)(?:s|es|ed|ing)?\b"),
        ("guard", r"\b(guard|protect|cover|shield|watch over|defend me|stay (close|near|with) me|stand (by|with) me|have my back|watch my back)(?:s|es|ed|ing)?\b"),
        ("focus", r"\b(take|attack|kill|hit|focus|target|go for|strike|cut down|finish off|shoot|loose|bite|maul|savage|tear into|grab|seize|pin|"
                  r"tackle|charge|rush|fire (?:a |an |your |another )?(?:bolt|arrow|shot)|fire at|open fire|hold [^,.;]*\bdown)(?:s|es|ed|ing)?\b"),
    )

    NOT = r"\b(don'?t|do not|stop|quit|no more|never|not|no longer|cease)\b"
    INSTEAD = {"heal": "focus", "guard": "focus", "hold": "focus", "focus": "hold", "back": "focus"}      # told only what not to do: the other thing

    def order_kind(self, low: str) -> str:
        """(f383) Which order the line gives, read past the ones it says not to give: "do not heal me anymore, focus on attacking" was read
        as heal, the first pattern in the table to match anywhere. An order inside a clause with a not before it, or anymore after it, is
        not given; of the rest the first in the line is. A line that only says what not to do gives the other thing (stop healing: fight)."""
        import re
        hits = []
        for k, pat in self.ORDER_WORDS:
            for m in re.finditer(pat, low):
                start = max(low.rfind(c, 0, m.start()) for c in (",", ";", ".", " but ", " then ", " and ", " instead"))
                ends = [i for i in (low.find(c, m.end()) for c in (",", ";", ".", " but ", " then ", " and ")) if i >= 0]
                before, after = low[max(0, start):m.start()], low[m.end():min(ends) if ends else len(low)]
                hits.append((m.start(), k, bool(re.search(self.NOT, before)) or bool(re.search(r"\b(anymore|any more|no longer)\b", after))))
        plain = sorted(h for h in hits if not h[2])
        if plain:
            return plain[0][1]
        return self.INSTEAD[sorted(hits)[0][1]] if hits else ""

    def order_of(self, text: str):
        """('ally', kind, enemy id) when the line is an order to a party member by name (or to the party), else None. No model call: a plain
        pattern, so an order never costs a turn or a wait."""
        import re
        if "?" in text:                                  # a question is for talking, not an order
            return None
        low = " " + text.lower() + " "
        allies = [a for a in self.fight.allies() if a.alive and (a.ally_role or combat.is_companion(a))]       # (f384) the animal companion too
        if not allies:
            return None
        named = [a for a in allies if re.search(r"\b" + re.escape(a.name.split()[0].lower()) + r"\b", low)]
        everyone = bool(re.search(r"\b(everyone|all of you|you all|party|you two|you both|team)\b", low))
        if not named and not everyone:
            return None
        kind = self.order_kind(low)
        if not kind:
            return None
        target = ""
        if kind == "heal":                                   # (f406) "heal yourself", "Jorn, heal Bryn": who the heal is for
            if re.search(r"\b(yourself|yourselves|himself|herself|themselves|themself|your own)\b", low):
                target = "self"
            elif len(named) >= 2:
                order = sorted(named, key=lambda a: low.find(a.name.split()[0].lower()))
                return [order[0]], kind, order[1].id
        if kind == "focus":
            foes = [e for e in self.fight.enemies() if e.alive and not e.fled]
            hit = next((e for e in foes if e.name.lower() in low or any(w in low for w in (e.name.lower().split()[-1],))), None)
            target = (hit or next((e for e in foes if e.id == self.fight.focus), None) or (foes[0] if foes else None))
            target = target.id if target else ""
        return (named or allies), kind, target

    def give_orders(self, who, kind: str, target: str) -> None:
        f = self.fight
        told = []
        again = f.order_round == f.round and f.round and any(a.id in f.ordered for a in who)      # (f383) putting this turn's order right
        for a in who:
            problem = combat.give_order(f, a, kind, target, same_command=bool(told))     # one order a turn is one command, even to the whole party
            if problem:
                console.note(problem)
                if "already given" in problem:
                    return
                continue
            told.append(a)
        if told:
            whom = next((a.name.split()[0] for a in f.allies() if a.id == target), "") if kind == "heal" else ""
            line = {"focus": "to attack {foe}", "guard": "to guard you", "hold": "to hold back", "back": "to get behind you",
                    "heal": "to tend their own wounds" if target == "self" else (f"to tend {whom}" if whom else "to tend you")}[kind]
            foe = next((e.name for e in f.enemies() if e.id == target), "")
            foe = ("the " + foe) if foe and foe[0].islower() else foe        # "the troll", "the wolf 1", but "Old Brannoch" as is
            console.narrate(("Instead, you tell " if again else "You tell ") + " and ".join(a.name.split()[0] for a in told) + " "
                            + line.format(foe=foe or "their foe") + ".")
        self.show()
        self.ws.store.save_combat(self.to_json())

    def turn(self, text: str, forced=None) -> None:
        """One player turn. forced is an intent already decided (a fight opened with an ability, f248): it is not interpreted."""
        f = self.fight
        p = f.player
        if forced is not None:
            self.act(forced, text)
            return
        if self.ally_for_item(text):
            from llm.contracts import CombatIntent
            self.free_item(CombatIntent(kind="item", item=text), text)
            return
        order = self.order_of(text)
        if order:
            self.give_orders(*order)
            mine = self.own_part(text, order[0])
            if mine and self.ws.combat is self and not f.over:      # (f406) "Jorn, heal yourself. I use spark bolt": both are done
                self.act(self.interpret(mine), mine)
            return
        intent = self.interpret(text)
        self.act(intent, text)

    def own_part(self, text: str, told) -> str:
        """(f406) The player's own action in a line that also gives an order: the clauses that do not name whoever was told, and that say
        what the player does ('I cast...', 'I use...', or an ability of theirs by name). '' when the line is only the order. A night's play
        had 'Jorn, heal yourself. I use spark bolt' give the order and drop the spell, and the player typed the spell again."""
        import re
        names = [a.name.split()[0].lower() for a in told]
        moves = [m.name.lower() for m in self.fight.player.moves if m.name]
        clauses = re.split(r'(?<=[.!;])\s+|["\u201c\u201d]+|\s+(?:and then|then|while)\s+|\s+and\s+(?=i\b)', text, flags=re.I)
        mine = []
        for c in clauses:
            c = (c or "").strip(" .,;:!")
            low = c.lower()
            if not low or any(re.search(r"\b" + re.escape(n) + r"\b", low) for n in names):
                continue
            if re.match(r"(i|i'll|i'm|i will|let me|now i|and i)\b", low) or any(m in low for m in moves):
                mine.append(c)
        return ". ".join(mine)

    def outside_ability(self, intent, text: str) -> str:
        """(f373) The note for an ability of the player's that works only outside a fight, when the line uses it here; '' otherwise. Beast
        Command used on a wolf mid-fight was answered with Maren's 'they're wolves, they won't listen', as if the player had only talked."""
        from core.models import UseContext
        c = self.ws.player.character
        low = text.lower()
        for a in getattr(c, "actives", []) or []:
            named = a.id == getattr(intent, "ability", "") or (a.name and re.search(rf"\b{re.escape(a.name.lower())}\b", low))
            if named and a.context == UseContext.OUT_OF_COMBAT and not any(m.id == a.id for m in self.fight.player.moves):
                return (f"{a.name} works outside a fight, not in one: {a.description.strip()} "
                        "Use it once the fight is over; for now, pick one of your fighting abilities from the panel.")
        return ""

    def act(self, intent, text: str) -> None:
        f = self.fight
        p = f.player
        console.debug(f"combat intent: {intent.model_dump(exclude_defaults=True)}")
        away = self.outside_ability(intent, text)
        if away:                                                            # (f373) a power for outside a fight: say so, and no turn passes
            console.note(away)
            return
        if f.mentor and intent.kind == "tame" or (f.mentor and not f.mentor_troll and intent.kind == "flee"):
            self.ws.mentor_refuse(intent.kind)
            return
        if f.mentor and (intent.kind == "talk" or (intent.kind == "other" and (mentor.named(text) or "?" in text))):   # she can be talked to mid-fight, free of a turn; the wolves cannot
            foe = f.get(intent.target) if intent.target else None
            if foe and foe.side == "enemy" and not mentor.named(text) and "?" not in text:       # a question is for her; only a plea or a taunt is for the wolf
                self.ws.mentor_refuse("talk")
            else:
                self.ws.mentor_talk(text)
                self.show()
            return
        hire = self.ws.hire_named(text) if intent.kind in ("talk", "other") else None
        if hire and not self.ws.TALK_ACTIONS.search(text.lower()):    # (f308) a word to a companion mid-fight: they answer, and it costs no turn
            self.ws.hire_talk(hire, text)
            self.show()
            return
        if intent.kind == "item":
            self.free_item(intent, text)
            return
        f.log, f.story, f.hits = [], [], []
        target = f.get(intent.target) if intent.target else None
        if intent.kind != "interpose" and (not target or not target.alive or target.side != "enemy" or target.fled):
            from engine import battlefield as bf
            target = bf.closest(f, p, f.enemies())
        if intent.kind == "talk":
            self.talk(intent, target, text)
            return

        again = p.counters.pop("acting_again", None)       # a movement used on its own: this is the same turn's action
        if not again and not combat.start_turn(p, f, self.rng):
            if not p.counters.pop("cast_turn", None):      # a charged spell going off (or breaking) is the whole turn
                f.log.append(f"{p.name} is unable to act")
                combat.tell(f, "you try to act, but your body will not answer")
        elif self.alongside(intent, target):
            pass                                          # the movement was the whole of what they did: the action is still to come
        elif not p.counters.get("moved_now") and self.apply_step(intent, target):
            pass                                          # the step took the whole round (the movement law); the action waits
        elif intent.kind == "ability":
            move = next((m for m in p.moves if m.id == intent.ability), None)
            binder = self.binding_ability(move)
            problem = None
            if binder:
                self.try_bind(move, binder, target)
            else:
                give = self.buff_recipients(move, intent.buff_for) if move and move.effect != "mobility" else \
                    ([a for a in [self.movement_ally(intent)] if a] or None)
                problem = combat.act_ability(f, p, move, target, self.rng, give=give) if move else "You don't know that ability."
            if problem:
                console.note(problem + " You attack instead.")
                combat.act_attack(f, p, target, self.rng)
        elif intent.kind == "move":
            combat.act_move(f, p, intent.move or "closer", target)
        elif intent.kind == "defend":
            combat.act_defend(f, p)
        elif intent.kind == "interpose":
            ward = next((a for a in f.allies() if a.id == intent.target), None) or                 next((a for a in f.allies() if intent.target and intent.target.lower() in a.name.lower()), None) or                 min(f.allies(), key=lambda a: a.hp / max(1, a.max_hp), default=None)
            combat.act_interpose(f, p, ward)
        elif intent.kind == "flee":
            if f.mentor_troll:
                combat.act_flee_blocked(f, self.ws.mentor_run_fails())
            else:
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
            from engine import combat_improv
            combat_improv.resolve(f, p, target, intent.summary or text, self.rng)
        else:
            combat.act_attack(f, p, target, self.rng)

        if intent.kind != "flee":
            f.player_acted = True
        if not f.over and not f.enemies() and not combat.muster(f):
            f.over = "victory"
        p.counters.pop("moved_now", None)
        if p.counters.pop("free_action", None) and not f.over:   # a movement on its own did not use the action - the player acts again
            self.narrate_round(text)
            self.sync_player()
            self.show()
            self.ws.store.save_combat(self.to_json())
            return
        if not f.over:
            combat.finish_round(f, self.rng)
        killed = self.hires_down()

        self.narrate_round(text)
        self.sync_player()
        for m in killed:                                   # those who saw it react now, in the fight, not after it
            down = tuple(a.id[len("ally_"):] for a in f.fighters if a.side == "ally" and a.id.startswith("ally_") and not a.alive)
            self.ws.party_moment(f"{m['name']} has just been killed in front of them.", "heavy", m["id"], f"{m['name']}'s death",
                                 in_fight=True, exclude=down)
        self.ws.mentor_round(self)
        if f.over:
            self.finish()
        else:
            self.show()
            self.ws.store.save_combat(self.to_json())

    def down_but_alive(self) -> list[str]:
        """(f412) The player's companions on the ground at the end of a fight, alive: they are carried out, and the passage after the fight
        shows them so (a night's narration had one walking by the water and talking, the same turn he was carried out)."""
        f = self.fight
        return [m["name"] for m in self.ws.player.party if m.get("down_fate") == "carried"
                and (a := f.get(f"ally_{m['id']}")) is not None and not a.alive]

    def on_their_feet(self) -> list[str]:
        """(f415) The player's own still standing when a fight ends, and how hurt each is: the passage after a fight was told who died and
        who is carried, never who walks away, or how hurt. Summons and risen foes are left out: they are the player's
        doing, not companions."""
        f = self.fight
        return [f"{a.name}, {combat.condition(a)}" for a in f.fighters
                if a.side == "ally" and a.alive and not a.fled and not a.summon_form and not a.id.startswith("thrall")]

    def hires_down(self) -> list[dict]:
        """Hired companions who have just gone down: whether each is dead is decided now (kept on them until the fight is over), so the
        narration shows it as it happens and those who saw it can react at once. Returns those killed."""
        f = self.fight
        killed = []
        for m in self.ws.player.party:
            if not m.get("permanent") or m.get("story") or m.get("tutorial") or m.get("npc"):
                continue
            a = f.get(f"ally_{m['id']}")
            if a is None:
                continue
            if a.alive:                                     # standing: any fate left from a fight that ended some other way is stale
                m.pop("down_fate", None)
                continue
            if m.get("down_fate"):                          # already decided when they went down
                continue
            by = f.felled_by.get(a.id, "")                  # (f412) the blow was the foe's: never the player's, never another companion's
            if self.ws.party_service.decide_down(m, self.rng, in_fight=True) == "dead":
                a.counters["dead"] = 1                      # beyond any healing: a Rescue cannot raise the dead
                combat.tell(f, f"{a.name} takes a killing blow{' from ' + by if by else ''} and does not get up: {a.name} is dead"
                               + (f" (killed by {by}, not by you)" if by and by != "you" else ""))
                killed.append(m)
                self.ws.mourn(m, by)
            else:
                combat.tell(f, entities.gendered(f"{a.name} goes down hard{' under ' + whose_blow(by) if by else ''} and lies still: alive, but "
                                                 "out of the fight, and they will have to be carried",            # (f422) in their own pronoun
                                                 party.pronoun_of(m, self.ws.store.meta.seed, self.ws.player.party_used)))
        return killed

    def talk(self, intent, target, text: str) -> None:
        """Words are a free action: the fight waits for the player's real move afterwards."""
        from engine import combat_perks, parley
        f = self.fight
        if combat_perks.challenge(f, text, self.rng):       # Challenger: the words were a call to single combat, and it was answered
            self.narrate_round(text)
            self.sync_player()
            self.show()
            self.ws.store.save_combat(self.to_json())
            return
        problem = parley.attempt(f, target, intent.approach, self.ws.player.character, self.rng)
        if problem:
            console.note(problem)
            return
        if not f.enemies() and not combat.muster(f):
            f.over = "victory"
        self.narrate_round(text)
        self.sync_player()
        if f.over:
            self.finish()
        else:
            self.show()
            self.ws.store.save_combat(self.to_json())

    def buff_recipients(self, move, wish: str) -> list | None:
        """Who a blessing or a heal goes on: the player (default) or one ally - single-target (f217, f219). A Rescue may name a fallen
        ally: they are the one creature a heal can reach on the ground."""
        if move.effect not in ("buff", "healing") or not wish or wish == "self":
            return None
        f = self.fight
        allies = f.allies()
        if move.effect == "healing" and getattr(move, "heal_form", "") == "rescue":
            allies = allies + [a for a in f.fighters if a.side == "ally" and not a.alive and not a.counters.get("dead")]
        if wish == "all":
            console.note(f"{move.name} falls on one at a time - name who it is for. You cast it on yourself.")
            return None
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

    def alongside(self, intent, target) -> bool:
        """A movement ability used on the way (engine/movement.py): it resolves first, and the turn's action follows. Returns True when
        the movement was all the player did, so the action is still theirs to take (the round waits for it). A whole-turn movement
        is not handled here: it is the turn's ability."""
        from engine import movement
        f, p = self.fight, self.fight.player
        mid = intent.movement or (intent.ability if intent.kind == "ability" else "")
        move = next((m for m in p.moves if m.id == mid and m.effect == "mobility"), None)
        if move is None or movement.whole_turn(move):
            return False
        alone = not intent.movement
        if move.movement == "shift":
            ranged = p.reach == "ranged" or (intent.kind == "ability" and any(m.id == intent.ability and m.reach in ("ranged", "area")
                                                                                for m in p.moves))
            if intent.step == "withdraw" or ranged:
                p.counters["shift_back"] = 1
        ally = self.movement_ally(intent)
        problem = combat.act_ability(f, p, move, target, self.rng, give=[ally] if ally else None)
        p.counters.pop("shift_back", None)
        if problem:
            console.note(problem)
            return False if not alone else self.act_again()
        p.counters["moved_now"] = 1
        return self.act_again() if alone else False

    def act_again(self) -> bool:
        p = self.fight.player
        p.counters["free_action"] = 1
        p.counters["acting_again"] = 1
        return True

    def movement_ally(self, intent):
        f = self.fight
        for key in (intent.target, intent.buff_for):
            a = next((x for x in f.allies() if key and (x.id == key or key.lower() in x.name.lower())), None)
            if a is not None:
                return a
        return None

    def apply_step(self, intent, target) -> bool:
        """The step that rides along with an action, priced by the movement law: toward the fight is free; away costs the round
        (parting blows and all) unless your own line covers you; in heavy armor, moving is the round's work either way.
        Returns True when the step consumed the action."""
        f, p = self.fight, self.fight.player
        from engine import battlefield as bf
        if not intent.step or intent.kind in ("move", "flee", "talk"):
            return False
        if intent.step == "advance":
            if p.pace == "slow":
                story = (bf.approach(f, p, target) if target else "") or "moves up"
                f.log.append(f"{p.name} {story}")
                combat.tell(f, f"in that armor, moving is the work of the round: you {story} and ready yourself")
                return True
            story = combat.advance_step(f, p, target)
            if story:
                f.log.append(f"{p.name} {story}")
                combat.tell(f, f"you {story}")
            return False
        covered = any(not bf.hostile(p, o) and bf.can_hold(o) for o in bf.standing(f, p.zone_id))
        threatened = bool(bf.engaged(f, p)) or any(bf.hostile(p, o) for o in bf.standing(f, p.zone_id))
        if (covered or not threatened) and p.pace != "slow":
            story = bf.withdraw(f, p)
            f.log.append(f"{p.name} {story}")
            combat.tell(f, f"you {story}")
            return False
        story = combat.retreat(f, p, self.rng)
        f.log.append(f"{p.name} {story}")
        combat.tell(f, f"backing away is the work of the round: you {story}")
        return True

    def ability_looks(self) -> list[str]:
        """(f373) The player's abilities this round's events name, each with its own description: 'Lance Volley' alone was told as a lance
        hurled in a volley of throws, with magic humming; its card says three quick strikes."""
        story = " ".join(self.fight.story)
        out = []
        for a in getattr(self.ws.player.character, "actives", []) or []:
            if a.name and len((a.description or "").split()) >= 3 and re.search(rf"\b{re.escape(a.name)}\b", story):   # (f424) a word or two shows nothing
                out.append(f"{a.name}: {a.description.strip()}")
        return out[:3]

    def ally_looks(self) -> list[str]:
        """(f385) Everyone on the player's side as the narrator must keep them: who they are to look at, she, he or it, and what they fight
        with. Nothing said it before: one hire was she, he and they in one fight, and a mage's bolts became a crossbow's."""
        ws, f = self.ws, self.fight
        members = {f"ally_{m['id']}": m for m in ws.player.party}
        comps = {f"ally_{c.id}": c for c in getattr(ws.player.character, "companions", None) or []}
        out = []
        for a in f.fighters:
            if a.side != "ally" or a is f.player:
                continue
            n = len(out)
            m = members.get(a.id) if a.ally_role else None
            if m is None and a.name == mentor.NAME:
                m = {"sheet": "maren", "name": a.name, "blurb": "a guild veteran", "people": "human"}
            if m is not None:
                p = party.pronoun_of(m, ws.store.meta.seed, ws.player.party_used)
                folk = entities.people_word(ws.world, m.get("people", ""))                      # (f392) and their people
                out.append(f"{a.name} ({party.pronoun_pair(p)}{', ' + folk if folk else ''}): {m.get('blurb', '').strip()}; fights with {party.fights_as(m)}")
            elif (c := comps.get(a.id)) is not None and combat.is_companion(a):
                kind_of = ws.world.bestiary[c.creature].name.lower() if c.creature in ws.world.bestiary else (c.kind or "beast")
                out.append(f"{a.name} ({party.pronoun_pair(party.companion_pronoun(c))}): the player's own {kind_of}"
                           + (f", {c.description.strip().rstrip('.')}" if c.description else "") + "; fights with teeth, claws and weight")
            elif a.summon_form or a.id.startswith("thrall"):
                out.append(f"{a.name} (it/its): {'summoned by the player' if a.summon_form else 'a fallen foe risen to fight for the player'}")
            if len(out) > n:                                    # (f415) and how hurt they are now, which nothing said before
                out[-1] += "; NOW: " + ("down, out of the fight" if not a.alive else "gone from the fight" if a.fled else combat.condition(a))
        return out

    def foes_now(self) -> tuple[list[str], list[str]]:
        """(f415) The foes as the narrator must keep them: those still fighting, with how hurt each is, and those alive but out of it. Before,
        a foe who had yielded or fled was still under FOES NOW with its wounds, as if it fought on, and one turned by the player's magic
        (Dominate, Dread Regent) was listed as a foe like any other."""
        fighting, out = [], []
        for e in self.fight.fighters:
            if e.side != "enemy" or not e.alive:
                continue
            if e.surrendered:
                out.append(f"{combat.who(e)} has yielded: beaten, unarmed and out of the fight")
            elif e.fled:
                out.append(f"{combat.who(e)} has fled and is gone")
            elif e.counters.get("turned"):
                fighting.append(f"{combat.who(e)}, {combat.condition(e)}, turned: it fights for the player now, against its own side")
            else:
                fighting.append(f"{combat.who(e)}, {combat.condition(e)}")
        return fighting, out

    def narrate_round(self, text: str) -> None:
        f = self.fight
        p = f.player
        foes, gone = self.foes_now()
        you = combat.condition(p) + (", up on high ground" if "elevated" in p.position_tags else "")
        from engine import battlefield as bfm, voice_rules
        boss = any(e.boss for e in f.fighters if e.side == "enemy" and e.alive) or any(e.startswith("BOSS") for e in f.story)
        result = fresh("combat_narrate", cp.NARRATE_SYSTEM,
                       cp.narrate_request(self.ws.place.name, self.ws.time_label(), text, f.story,
                                          p.weapon_name, you, foes, f.round - 1, self.ws.gear_line(),
                                          self.ws.recent_narration, ground=bfm.narrative_snapshot(f),
                                          shown=self.fight_shown, worn=self.ws.worn_words("prose"),                         # (f349)
                                          looks=self.ability_looks(), allies=self.ally_looks(), gone=gone),                     # (f373, f385, f415)
                       Narration, self.ws.recent_narration, max_tokens=config.PROSE_MAX_TOKENS, worn=self.ws.worn_words("prose"), said=text)
        text_out = place_figures(result.text, f.hits, console.damage_tags, f.story)
        console.narrate(text_out)
        self.ws.remember_narration(TAG.sub("", result.text))
        self.note_fight_shown(result.text)
        if config.COMBAT_NUMBERS and not console.damage_tags:
            console.combat_numbers(f.log)

    ITEM_VERBS = r"\b(give|hand|toss|throw|pass|use|drink|feed|pour|apply|administer|let)\b"

    def ally_for_item(self, text: str):
        """The party member a consumable is meant for, when the line names one ('give Maren a healing draught'), else None."""
        import re
        if "?" in text or not re.search(self.ITEM_VERBS, text.lower()):
            return None
        low = text.lower()
        c = self.ws.player.character
        if not any(i.good and inventory.GOODS[i.good].combat and (inventory.GOODS[i.good].name.lower() in low or re.search(r"\b(draught|draft|potion|elixir|tonic|salve|philtre)\b", low)) for i in c.inventory):
            return None
        return next((a for a in self.fight.allies() if a.alive and a.ally_role and re.search(r"\b" + re.escape(a.name.split()[0].lower()) + r"\b", low)), None)

    def use_item(self, name: str, target: "combat.Fighter | None" = None) -> str | None:
        """Use a consumable mid-fight, on yourself or on a party member. It does not use up the action: see free_item."""
        c, p, f = self.ws.player.character, target or self.fight.player, self.fight
        item = inventory.find(c.inventory, name)
        if not item and target is not None:                    # 'give Maren a healing draught': the whole line is the name
            low = name.lower()
            usable = [i for i in c.inventory if i.good and inventory.GOODS[i.good].combat]
            item = next((i for i in usable if inventory.GOODS[i.good].name.lower() in low), None) or next((i for i in usable if "health" in inventory.GOODS[i.good].restores), None)
        if not item or not item.good or not inventory.GOODS[item.good].combat:
            return "You have nothing like that to use in a fight."
        g = inventory.GOODS[item.good]
        if self.ws.frugal_save():
            console.note(f"Somehow there is still one {g.name} left (Frugal Hands).")
        else:
            inventory.take(c.inventory, g.name, 1)
        pools_now = {"health": ("hp", "max_hp"), "mana": ("mana", "max_mana"), "stamina": ("stamina", "max_stamina")}
        self.last_figures = []
        from engine import combat_perks
        for pool, pct in g.restores.items():
            cur, top = pools_now[pool]
            before, maximum = getattr(p, cur), getattr(p, top)
            shielded = 0
            if pool == "health":
                gained, shielded = combat_perks.mend(f, f.player, p, maximum * pct / 100)
            else:
                setattr(p, cur, min(maximum, before + maximum * pct / 100))
                gained = round(getattr(p, cur) - before)
            rec = combat.new_heal(f, p, f"uses {g.name} on", pool, gained, [
                [g.name, f"restores {pct:g}% of {'your' if p is f.player else p.name.split()[0] + chr(39) + 's'} maximum {pool} ({round(maximum)})"],
                [f"{pool} before and after", f"{round(before)} to {round(getattr(p, cur))}"]]
                + ([["barrier (Overabundance)", f"+{shielded}"]] if shielded else []))
            self.last_figures.append(rec or {"id": "", "figure": f"(+{gained} {pool})"})
        cured = [st for st in g.cures if p.statuses.pop(st, None) is not None]
        if cured:
            rec = combat.new_heal(f, p, f"uses {g.name} on", "", 0, [[g.name, f"cures {', '.join(cured)}"]])
            if rec:
                rec["figure"] = f"(cured {', '.join(cured)})"
            self.last_figures.append(rec or {"id": "", "figure": f"(cured {', '.join(cured)})"})
        f.log.append(f"{f.player.name} uses {g.name}" + ("" if p is f.player else f" on {p.name}"))
        self.last_item = g
        return None

    def free_item(self, intent, text: str) -> None:
        """A draught or other consumable: one a turn, and it does not use up the action - the player is asked what they do next."""
        f = self.fight
        if f.duel:
            console.note("No potions or draughts in a trial: you face the examiner with what you carry in your hands.")
            return
        from engine import combat_perks
        p = f.player
        used = p.counters.get("items_used", 0) if (f.item_round == f.round and p.counters.get("items_round") == f.round) else 0
        if used >= combat_perks.item_limit(f, p):
            console.note("You have already used an item this turn. Do something else, and you can use another on your next turn."
                         if used == 1 else "Two items is all even you can manage in a turn. Do something else.")
            return
        ally = self.ally_for_item(text)
        problem = self.use_item(intent.item or text, ally)
        if problem:
            console.note(problem)
            return
        f.item_round = f.round
        p.counters["items_round"], p.counters["items_used"] = f.round, used + 1
        g = self.last_item
        figs = " ".join((f"⟦{h['id']}|{h['figure']}⟧" if console.damage_tags and h["id"] else h["figure"]) for h in self.last_figures)
        who = f"You give {ally.name.split()[0]} {g.name}" if ally else f"You use {g.name}"
        console.narrate(f"{who} ({g.description.lower().rstrip('.')}). {figs}".strip())
        self.sync_player()
        self.show()
        self.ws.store.save_combat(self.to_json())

    def refresh_player(self) -> None:
        """Attribute points spent in the middle of a fight: bring the fighter's maximums, attributes and defences in line with the character,
        and add what each maximum gained to the current value (the same rule as outside a fight), so the bars and spell costs agree."""
        c, p = self.ws.player.character, self.fight.player
        fresh = combat.fighter_from_character(c)
        for cur, top in (("hp", "max_hp"), ("stamina", "max_stamina"), ("mana", "max_mana")):
            gained = getattr(fresh, top) - getattr(p, top)
            setattr(p, top, getattr(fresh, top))
            if gained > 0:
                setattr(p, cur, min(getattr(p, top), getattr(p, cur) + gained))
        p.attrs = fresh.attrs
        p.ward, p.armor = fresh.ward, fresh.armor
        self.sync_player()

    def sync_player(self) -> None:
        c, p = self.ws.player.character, self.fight.player
        c.health, c.stamina, c.mana = float(p.hp), float(p.stamina), float(p.mana)
        for mid in p.counters.pop("day_cast", []):      # (f397) a named spell cast: the day is kept, for its cooldown in days
            c.spell_days = {**c.spell_days, mid: self.ws.minutes}
        if c.orenna_breath and not p.breath:
            c.orenna_breath = False
            from engine import orenna
            console.note(orenna.O["blessing"]["spent"])

    # ---------- endings ----------

    def companions_after_fight(self, fallen_ids: set[str]) -> None:
        """A companion who went down is out for a day, and may not survive. A Bound summon unmade in the fight stays unmade until
        its spell is cast again."""
        ws = self.ws
        c = ws.player.character
        from engine import summons
        note = summons.after_fight(c, self.fight)
        if note:
            console.note(note)
            ws.store.save_player(ws.player)
        rules = combat.RULES["creatures"]["companion_fall"]
        changed = False
        last = getattr(ws.player, "party_last_fight", None)
        last = last if (last or {}).get("minute") == ws.minutes else None
        for comp in c.companions:
            if f"ally_{comp.id}" not in fallen_ids or not comp.active:
                continue
            changed = True
            comp.fallen = True
            comp.recover_at = ws.minutes + int(rules["recover_hours"] * 60)
            p = party.companion_pronoun(comp)
            if self.rng.random() < rules["death_chance"]:
                comp.dead = True
                console.note(f"{comp.name} is dead. {'It' if p == 'it' else p.capitalize()} fell protecting you.")
                if last is not None:                           # (f385) what the party will talk over: the player's own animal, by name
                    kind_of = ws.world.bestiary[comp.creature].name.lower() if comp.creature in ws.world.bestiary else (comp.kind or "animal")
                    last.setdefault("fallen_what", {})[comp.name] = f"the player's own {kind_of}"
            else:
                console.note(f"{comp.name} is badly hurt and will need a day to recover.")
                if last is not None and comp.name in last.get("fallen", []):      # (f385) down, not dead: no wake is held for them
                    i = last["fallen"].index(comp.name)
                    last["fallen"].pop(i)
                    if i < len(last.get("fallen_ids", [])):
                        last["fallen_ids"].pop(i)
                    last.setdefault("hurt", []).append(comp.name)
        if changed:
            ws.store.save_player(ws.player)

    def finish_duel(self) -> None:
        """A trial of rank is over: nobody dies, nothing is looted, and the hall tells you how it went."""
        f, ws = self.fight, self.ws
        for x in f.fighters:
            if x.alive and x.hp < 1:
                x.hp = 1
        self.sync_player()
        won = f.over == "victory"
        ws.store.save_combat(None)
        ws.combat = None
        if f.hits:
            console.combat_state(self.pane_data())
        console.combat_state(None)
        ws.advance_quiet(max(1, math.ceil(f.round * combat.RULES["round_seconds"] / 60)))
        ws.trial_over(won, f)
        ws.store.save_player(ws.player)

    def finish(self) -> None:
        f, ws = self.fight, self.ws
        if f.duel:
            self.finish_duel()
            return
        from engine import needs
        needs.fight(ws.player.character)
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
        ws.party_after_fight(fallen, f.fighters, f.over == "victory", any(e.level >= ws.player.character.level for e in f.fighters if e.side == "enemy"))
        self.companions_after_fight({a.id for a in fallen})
        if f.over == "victory" and not f.no_rewards:
            dead_ = [e for e in f.fighters if e.side == "enemy" and not e.alive]
            from engine.domain_events import LootedDead
            if any(e.category in loot.L["coin_categories"] for e in dead_):
                ws.notice(LootedDead(minute=ws.minutes, place=ws.player.location))      # (f310) only the dead who carry coin, not wolves
        elif f.over == "fled" and not f.mentor:
            from engine.domain_events import Fled
            ws.notice(Fled(minute=ws.minutes, place=ws.player.location))
        if f.over == "victory":
            self.victory()
            ws.dungeon_fight_over("victory")
            ws.road_fight_over("victory")
            ws.camp_fight_over("victory", dead, [e for e in f.fighters if e.side == "enemy" and e.alive and e.surrendered])
            ws.orenna_fight_over("victory")
            ws.mentor_fight_over("victory", f)
            ws.assault_fight_over("victory")
        elif f.over == "fled":
            if not f.mentor:
                console.note("You got away.")
            ws.dungeon_fight_over("fled")
            ws.road_fight_over("fled")
            ws.camp_fight_over("fled", dead)
            ws.orenna_fight_over("fled")
            ws.mentor_fight_over("fled", f)
            ws.assault_fight_over("fled")
            ws.recently_fled = True
        elif self.phoenix():
            ws.dungeon_fight_over("fled")
            ws.road_fight_over("fled")
            ws.camp_fight_over("fled", dead)
            ws.orenna_fight_over("fled")
            ws.assault_fight_over("fled")
            ws.recently_fled = True
        else:
            ws.dungeon_fight_over("defeat")
            ws.road_fight_over("defeat")
            ws.camp_fight_over("defeat", dead)
            ws.orenna_fight_over("defeat")
            ws.assault_fight_over("defeat")
            self.defeat()
        if f.over in ("victory", "fled") and ws.player.party:
            ws.tend_after_fight()                          # (f396) a priest on their feet sees to the wounds
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
                   "enemies recoiling or gone.")                                                   # (f415) no length (f375)
        return True

    def victory(self) -> None:
        if self.fight.no_rewards:
            self.sync_player()
            return
        c = self.ws.player.character
        self.survivor_yields()
        dead = [e for e in self.fight.fighters if e.side == "enemy" and not e.alive]
        yielded = [e for e in self.fight.fighters if e.side == "enemy" and e.alive and e.surrendered]
        if not dead and not yielded and self.tamed:
            console.note(f"The fight is over. {', '.join(self.tamed)} follows you now.")
            self.sync_player()
            return
        if not dead and not yielded:
            if getattr(self.ws, "orenna_fight", None) != "executioner":
                console.note("They got away - nothing to show for it this time.")
            self.sync_player()
            return
        self.ws.record_kills(dead)
        if self.ws.place.danger and self.ws.owns("victors_name"):
            self.ws.reputation_add(self.ws.nearest_town(self.ws.player.location), 1)
        pack = combat.RULES["creatures"].get("pack", {})
        pack_xp = (pack.get("health", 1) + pack.get("damage", 1)) / 2
        deaths_ledger = 1 + (pools.mechanic(c, "deaths_ledger") or 0) / 100
        total_xp = round(sum(leveling.kill_xp(c.level, e.level, e.rank)
                             * (pack_xp if self.ws.world.bestiary[e.creature].group[0] >= 2 else 1)
                             * (deaths_ledger if e.category == "undead" else 1) for e in dead))
        total_xp += round(sum(leveling.kill_xp(c.level, e.level, e.rank) for e in yielded) * combat.RULES["talk"]["surrender_reward"])
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
                from engine import spells
                codex = spells.codex_drop(e.level, self.rng, e.element)          # (f397) now and then, a codex: a named spell
                if codex is not None:
                    self.ws.name_codex(codex, e.name)
                    found.append(codex)
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
        from engine import spells
        for e in dead:
            book = spells.book_drop(e.level, e.rank, self.rng)               # (f397) now and then, a spell book of the rank its level allows
            if book is not None:
                found.append(book)
        state.bodies = self.ws.keep_bodies(state.bodies + list(bodies.values()))
        self.ws.store.save_place(state)
        coins = self.ws.flaws_on_loot(coins)
        c.coins += coins
        stowed = [self.ws.to_pack(item) for item in found]
        levels = leveling.gain_xp(c, total_xp)
        name_of = lambda i: items.display_name(i) if i.rarity == "legendary" else inventory.label(i)
        noticed = [name_of(st.kept) for st in stowed if st.kept is not None]
        lying = [name_of(st.left) for st in stowed if st.left is not None]    # (f417) no room: left here, and told so, never pocketed
        if coins:
            noticed.append("a few coins")
        noticed = [f"{x} (now theirs: show them taking it up)" for x in noticed]      # (f384) taken, not left lying for a 'pick up' to miss
        fallen = ", ".join(combat.who(e) for e in dead) or "no one - the rest yielded"
        if yielded:
            fallen += (f". THOSE WHO YIELDED (alive and beaten, waiting on the player's choice: tell nothing of what becomes of them): "
                       f"{', '.join(combat.who(e) for e in yielded)}")
        from scenes import world_prompts as wp
        end_habits = self.ws.habits_due("fight_end")             # (f412) the companions' habits as it ends, folded into this passage
        aftermath = fresh(
            "combat_aftermath", cp.AFTERMATH_SYSTEM,
            self.aftermath_opening() +
            f"PLACE: {self.ws.place.name}\nTIME AND WEATHER: {self.ws.time_label()}\nTHE PLAYER: {self.ws.gear_line()}\n"
            f"THE PLAYER IS: {combat.condition(self.fight.player)}\nTHE FALLEN: {fallen}\n"
            + (f"THE PLAYER'S OWN WHO DIED IN THIS FIGHT (their companions; the passage does not pass over them, and gives each death to the "
               f"one named, never to the player): {'; '.join(lost)}\n"
               if (lost := [f"{e.name} ({e.pronoun}, {entities.people_word(self.ws.world, e.people)}"
                            + (f"; killed by {by}" if (by := self.killer_of(e)) else "") + ")"
                            for e in self.ws.store.find_entities(kind="hire", state="dead") if e.since >= self.ws.minutes - 30]) else "")
            + (f"DOWN BUT ALIVE (the player's companions, on the ground and carried from here: they do not stand, walk or talk at length): "
               f"{', '.join(carried)}\n" if (carried := self.down_but_alive()) else "")
            + (f"ON THEIR FEET (the player's companions still standing, and how hurt: a fact for when they come in, not a pose each): "
               f"{'; '.join(feet)}\n" if (feet := self.on_their_feet()) else "")
            + (f"{entities.WHO_HEAD}: {'; '.join(who)}\n" if (who := entities.who_is_who(self.ws)) else "")
            + (("WHAT THE GAME DID THIS TURN (true; tell it, and nothing that contradicts it): " + " ".join(done) + "\n")
               if (done := ledger.told(but=("gained", "left"))) else "") +            # (f416) the finds are told below, under their own heads
            f"THE PLAYER FINDS: {'; '.join(noticed) or 'nothing'}\n"                  # (f417) '; ': a name can hold a comma
            + (f"LEFT LYING HERE (no room in the player's pack: they see it and leave it; never taken, pocketed or carried): "
               f"{'; '.join(lying)}\n" if lying else "")
            + (f"{wp.HABITS_HEAD}: {' '.join(end_habits)}\n" if end_habits else "")
            + self.aftermath_facts(dead, skinnable) +
            "RECENT NARRATION:\n" + "\n".join(f"  - {r}" for r in self.ws.recent_narration[-3:]),
            Narration, self.ws.recent_narration, max_tokens=config.PROSE_MAX_TOKENS, worn=self.ws.worn_words("prose"))
        self.ws.__dict__.setdefault("_after_starts", []).append(" ".join(aftermath.text.split()[:5]))
        del self.ws._after_starts[:-4]
        after_text = self.ws.unnamed(aftermath.text)                 # (f419) a name the player was never told stays hidden here too
        console.narrate(after_text)
        self.ws.remember_narration(after_text)
        taken = self.take_prisoners(yielded)
        self.ws.hold_yielded([e for e in yielded if e not in taken])         # (f385) the rest wait on the player's word
        console.ledger(f"Victory. +{total_xp} XP" + (f", {money.fmt(coins)}" if coins else ""))
        for item in found:
            if item.rarity == "legendary":
                console.legendary_reveal(item)
            else:
                console.ledger(f"Found: {item.name} ({item.rarity}) - {items.summary(item)}")
        if levels:
            console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
            self.ws.ranks_in_reach(c.level - levels)                          # (f397) a new rank of spells, when one comes within reach
        if skinnable:
            console.note(f"The fallen can be skinned or butchered for {'their' if skinnable > 1 else 'its'} hide and meat - "
                         "say so if you want to.")

    def aftermath_opening(self) -> str:
        """(f412) Where the passage after a fight begins, chosen by the engine and never the last two places, and how the last few began:
        the night's runs opened some 200 such passages with 'Silence rushes back', 'The heavy thud' or 'The roar of', and went round the
        companions one pose each."""
        AF = combat.RULES["aftermath"]
        used = self.ws.__dict__.setdefault("_after_opened", [])
        with_party = any(m.get("permanent") for m in self.ws.player.party) and self.ws.player.party_mode == "with"
        choices = [o for o in AF["openings"] if o not in used[-AF["not_again"]:] and (with_party or "companion" not in o)]
        pick = self.rng.choice(choices or AF["openings"])
        used.append(pick)
        del used[:-6]
        starts = self.ws.__dict__.get("_after_starts") or []
        return (f"OPEN ON: {pick}\n"
                + (f"DO NOT BEGIN LIKE THESE (how the last passages after a fight began): {' / '.join(starts[-3:])}\n" if starts else ""))

    def killer_of(self, ent) -> str:
        """(f412) Who struck a fallen companion down in this fight, as the story named them; '' when the fight did not record it."""
        mid = str(getattr(ent, "ref", "")).split(":", 1)[-1]
        return self.fight.felled_by.get(f"ally_{mid}", "")

    def aftermath_facts(self, dead: list, skinnable: int) -> str:
        """(f404) What the after-fight passage keeps to: the bodies lie where they fell, whole (a night's play had wolves burnt to ash and
        then skinned for three hides), and whatever the fight's magic called up ends with it (Ghostly Afterburn's echoes hovered on after
        the last wolf fell, and Maren turned to look at them)."""
        out = ""
        if dead:
            out += ("THE BODIES: each of the fallen lies where it fell, its body whole: burnt, cut or broken, never ash, dust or gone"
                    + ("; they can still be skinned and butchered" if skinnable else "") + "\n")
        echoes = self.fight.player.counters.pop("echoes", 0)
        if echoes:
            out += (f"WHAT THE FIGHT CALLED UP (gone now): the spectral echo{'es' if echoes != 1 else ''} the kills left "
                    f"fade{'s' if echoes == 1 else ''} as the fight ends, with nothing left to repeat\n")
        return out

    def survivor_yields(self) -> None:
        """(f392) A won fight against outlaws can leave one who lives and yields (arcs.yaml prisoner.chance): chosen here among the fallen,
        before the after-fight passage is written, so the story and the captive agree. It used to be rolled afterwards, among the dead:
        a night's run had an outlaw narrated dead and then throwing down his weapon. An arc's camp has its leader's own way."""
        from engine.arcs import A as R
        ws, f = self.ws, self.fight
        if getattr(ws, "camp_fight", None) or ws.place.type in ("dungeon", "road"):
            return
        fallen = [e for e in f.fighters if e.side == "enemy" and not e.alive and e.category in R["people_categories"]]
        if not fallen or any(e.alive and e.surrendered for e in f.fighters if e.side == "enemy"):
            return
        PR = R["prisoner"]
        chance = max(PR["min_chance"], min(PR["max_chance"], PR["chance"] + ws.player.outlaw_rep * PR["rep_chance_per_point"]))
        if random.Random(f"{ws.store.meta.seed}:yield:{ws.minutes}").random() < chance:
            who = max(fallen, key=lambda e: e.level)
            who.hp, who.surrendered = 1, True

    def take_prisoners(self, yielded: list) -> list:
        """Foes who yielded: people can be bound and kept (questioned, let go, handed to the watch); the rest wait on the player (f385).
        (f392) No more than walk bound at once (lifecycles.yaml captive.most_escorted): the rest wait on the player's word like any foe
        who yields. An arc's camp leader is taken by the camp's own way (arc_actions.camp_fight_over). Returns those taken."""
        from engine import entities
        from engine.arcs import A as R
        room = entities.L["captive"]["most_escorted"] - len(self.ws.escorted())
        leader = (getattr(self.ws, "camp_fight", None) or {}).get("leader")
        ppl = sorted([e for e in yielded if e.category in R["people_categories"] and e.name != leader], key=lambda e: -e.level)[:max(0, room)]
        if not ppl:
            return [e for e in yielded if e.name == leader]
        self.ws.surrender_took = True
        rng = random.Random(f"{self.ws.store.meta.seed}:surrender:{self.ws.minutes}")
        taken = {n.split()[0].lower() for n in self.ws.store.npc_names() if n}            # (f422) no two captives, or a captive and a
        for e in ppl:                                                                       # townsman, share a name in one save
            free = [n for n in R["prisoner"]["names"] if n.split()[0].lower() not in taken] or R["prisoner"]["names"]
            name = rng.choice(free)
            taken.add(name.split()[0].lower())
            kind = re.sub(r" ?\d+$", "", re.sub(r"\s*\([^)]*\)", "", e.name)).strip()            # (f422) no "(bounty)" on what they are
            self.ws.make_prisoner(name, "", tip=rng.random() < R["prisoner"]["tip_chance"], named=False, kind=kind, fighter=e)
        self.ws.store.save_player(self.ws.player)
        return ppl + [e for e in yielded if e.name == leader]

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
        if ws.captives_lost("got away while their captor lay dead"):                 # (f392) nobody waits bound beside a corpse
            lost.append("the captives they held, who got away")
        console.note("You have died.")
        console.wait("Darkness. Then the sourceless light of the Threshold, dimmer than you remember.")
        said = list(getattr(ws.player, "goddess_said", []))                        # (f349) she remembers what she said on earlier returns
        event = cp.THRESHOLD_EVENT.format(deaths=c.deaths, losses="; ".join(lost))
        if said:
            event += (" She remembers every earlier return and what she said then (below, as RECENT CONVERSATION): this time she begins"
                      " elsewhere, on a different image, and never repeats an opening.")
        line = generate("goddess_line", gp.goddess_system(ws.goddess_knowledge()),
                        gp.narration_request("death", event, [("Orenna, on an earlier return", s) for s in said[-4:]]),
                        GoddessLine, temperature=0.9, validation_context={"said": said})
        ws.player.goddess_said = (said + [line.speech])[-8:]
        console.say(line.speech, "The Goddess")
        console.ledger("Lost: " + " · ".join(lost))
        days = combat.RULES["death"]["days_pass"]
        ws.advance_quiet(days * clock.MINUTES_PER_DAY)
        pools.fill_missing(c)
        ws.player.delve = None           # waking at the Threshold, never inside a dungeon
        ws.party_disband(None, "you fell")
        wake = c.last_rest if c.last_rest in ws.world.places else ws.world.start_location
        ws.enter(wake)
        ws.narrate(f"{days} days have passed in the world. The player wakes here, alive again, a lighter purse and nothing else lost. "
                   "They are thrown back by the goddess's failing light and wake with a sharp breath. Describe waking, stark: the first "
                   "breath, said only once in the whole passage, then what they see.")
        ws.show_exits()
