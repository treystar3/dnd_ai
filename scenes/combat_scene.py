"""Running a fight inside the game: start, rounds, and how it ends.

The engine (engine/combat.py) decides everything. The model only reads the player's words
and narrates the round from the engine's log.
"""

import re

from core.models import Item
import config
from engine import entities
from engine import ability_traits as AT
from engine import accessories, inventory, clock, combat, events, failures, items, ledger, loot, mentor, money, party, pools
from llm.contracts import AccessoryName, CombatIntent, GoddessLine, LegendaryName, LootName, Narration
from llm.gateway import LLMError, generate
from scenes import combat_prompts as cp
from scenes import goddess_prompts as gp
from scenes.voice import fresh
from ui import console
from engine import asked, streams
from services.fight import FightService, FightSpec, RoundIntent, ROLE_PROFILES, _Shape, whose_blow   # (f503) the fight's mechanics; the
#                                                                             helpers kept importable from here (party_actions, tests)  # noqa


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


def service_of(ws, dice=None) -> FightService:
    """(f503) The fight service over this scene's campaign: its store, its session's bus, its party service, the fight's stream (the
    scene's own die when it has one, so a test that steers sc.rng steers the service), the player's record, the world and the clock.
    Built per use, over the records as they stand now (a rollback reloads the player)."""
    session = getattr(ws, "session", None)
    return FightService(getattr(ws, "store", None), session.bus if session is not None else None, getattr(ws, "party_service", None),
                        dice or streams.get("combat"), getattr(ws, "player", None), getattr(ws, "world", None), lambda: ws.minutes)


def read_effect(words: str) -> str:
    """(f503) Which of the improvisation vocabulary the player is after: by meaning when the helper model is there (its embeddings: a
    model read, the scene's to make, handed to the service as the proposal it is), by their words when it is not
    (engine/combat_improv.py effect_by_words)."""
    from engine import combat_improv, relevance
    try:
        pick = relevance.pick(words, [v["about"] for v in combat_improv.EFFECTS.values()], 1, floor=0.3)
        if pick:
            return next(k for k, v in combat_improv.EFFECTS.items() if v["about"] == pick[0])
    except Exception:
        pass
    return combat_improv.effect_by_words(words)


class CombatScene:
    def __init__(self, world_scene, fight: combat.Combat, creature_name: str):
        self.ws = world_scene
        self.fight = fight
        fight.record = True
        self.creature_name = creature_name
        self.rng = streams.get("combat")  # (f439) reseeded at every input

    @property
    def service(self) -> FightService:
        """(f503) The fight's mechanics (services/fight.py), over this campaign and this scene's die."""
        return service_of(self.ws, getattr(self, "rng", None))

    # (f499) What the player has read of the fight and who was tamed in it are the fight's own (engine/combat.py Combat shown, tamed):
    # in the row the save holds, back with the row when a round rolls back, gone with it when the fight ends.
    @property
    def fight_shown(self) -> list[str]:
        return self.fight.shown

    @fight_shown.setter
    def fight_shown(self, lines: list[str]) -> None:
        self.fight.shown = list(lines)

    @property
    def tamed(self) -> list[str]:
        return self.fight.tamed

    @tamed.setter
    def tamed(self, names: list[str]) -> None:
        self.fight.tamed = list(names)

    def note_ground_told(self, opening: bool = False) -> None:
        """(f571) A telling stood with the ground in it: noted on the fight as it stands now, as note_fight_shown is."""
        from engine import battlefield as bfm
        live = self.ws.combat
        bfm.note_ground_told(live.fight if live is not None and live.fight.serial == self.fight.serial else self.fight, opening=opening)

    def note_fight_shown(self, text: str) -> None:
        """(f349) After a passage: the ground and the place are given; the light if it was described; the look of each foe it described;
        the blade once it has gleamed. The next passage is told not to describe them again. (f498) Noted on the fight as it stands now:
        a telling runs on the scene that marked it, and the fight may have been resumed from the row since (a telling that stood down
        to ask is given back, scenes/world.py give_back), so the live scene of the same fight takes the note."""
        import re
        from engine import voice_rules
        live = self.ws.combat
        if live is not None and live is not self and live.fight.serial == self.fight.serial:
            live.note_fight_shown(text)
            return
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
        """(allies who start in the fight, allies who arrive later). Companions always start; a party told to hold arrives late.
        (f503) Mustered by the service; the notes and the habits of the moment are the scene's."""
        near, later, notes, formed = service_of(ws).allies(hold)
        for note in notes:
            console.note(note)
        if formed:
            ws.habits("fight_start")
        return near, later

    @classmethod
    def begin(cls, ws, creature, enemies: list[combat.Fighter], how: str, reserves: list[combat.Fighter] | None = None,
              wave: tuple[int, int, int] = (2, 2, 1), prepare=None, duel: str = "", big: str = "",
              initiated: bool = False, told: str = "") -> "CombatScene":
        # told (f404): the passage that already showed the foe arrive, a scripted entrance; the fight's opening is not narrated again
        c = ws.player.character
        if not duel:
            events.recruit_allies(ws, enemies)
        prep = [] if duel else ws.field_prep(enemies)
        near, later = ([], []) if duel else cls.allies(ws, hold=bool(getattr(ws, "camp_fight", None)))
        tether_notes = ws.tether_for(near)
        from engine import battlefield_builder
        ground = battlefield_builder.for_scene(ws, duel=bool(duel), big="" if duel else battlefield_builder.big_kind(enemies, reserves or [], big))
        prebuffs, stealth = [], ""
        if initiated and not duel:
            named = [i for i in (ws.fight_buffs() if hasattr(ws, "fight_buffs") else []) if i not in (c.prebuffs or [])]
            prebuffs = list(c.prebuffs or []) + named          # the player picked the moment: their buffs go up first (f247, f248)
            if big != "camp" and getattr(ws, "sneaking", False):     # they crept up on it: stealth decides surprise (a camp rolls its own)
                ws.sneaking = False
                stealth = ws.resolve("stealth")                # (f503) rolled here, on the checks stream; the service reads the degree
        spec = FightSpec(creature=creature, enemies=enemies, allies=near, later=later, battlefield=ground, place=ws.place.name,
                         conditions=sorted(ws.conditions()), reserves=list(reserves or []), wave=wave, duel=bool(duel),
                         prebuffs=prebuffs, stealth=stealth, initiated=initiated, prepare=prepare)
        fight, opening = service_of(ws).begin(spec)            # (f503) the fight built, its serial drawn once, the odds, the row saved
        prep += opening.notes
        scene = cls(ws, fight, creature.name)
        label, rate = opening.label, opening.rate
        console.debug(f"danger estimate: {rate:.0%} win rate")
        opening_events = [TAG.sub("", e) for e in opening.events]      # the opening blows are logged, not narrated with figures
        manner = {"aggressive": "They mean to attack.",
                  "territorial": "It holds its ground and warns the player off - they could still back away.",
                  "passive": "It turns on the player."}[creature.temperament]
        where = "far off" if enemies and all(e.starts_far for e in enemies) else "close at hand"
        odds = {"trivial": "no real threat", "favorable": "the player should win this",
                "even": "a real fight that could go either way",
                "dangerous": "the player is likely to be badly hurt or worse",
                "deadly": "the player will very likely die if they stand and fight"}
        from engine import battlefield as bfm
        brief = bfm.ground_brief(fight)                        # (f571) every fight's ground, a single open zone too, in plain words
        ground_text = f" THE GROUND: {brief}." if brief else ""
        count = f"{len(enemies)} of them" if len(enemies) > 1 else "one"
        if reserves:
            count += f", and {len(reserves)} more in the camp who will come if the noise carries"
        event = (f"{how} {creature.name.lower()} - {count}, {where} from the player. {manner}{ground_text} "
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
            facts = {"foe": creature.name.lower(), "count": failures.count_phrase(len(enemies))}
            ws.mark_passage("opening", ws.opening_telling(event, scene), lambda rng: failures.fight_begun(facts, rng))   # (f498) a telling
            # of its own, told once the fight's commit stands (Bundle C decision 1: a fight begun is never undone because its opening
            # could not be written; fight_begun stands in): the notes and the pane below keep their place on the page behind it
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
        ws.store.save_combat(scene.to_json())                  # the row as the telling left it (what was shown of the fight, f499)
        return scene

    def to_json(self) -> str:
        return FightService.row(self.fight, self.creature_name)

    @classmethod
    def resume(cls, ws, raw: str) -> "CombatScene | None":
        """The scene of a saved fight. (f503) A row that cannot be read is let go of, its reason in logs/crash.log: the fight is lost,
        never the game (the caller drops the row where it may write)."""
        fight, creature, why = FightService.resume(raw)
        if fight is None:
            from engine import crashlog
            crashlog.record(RuntimeError(f"the saved fight could not be read and was let go: {why}"), "fight row")
            return None
        return cls(ws, fight, creature)

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
        again = f.order_round == f.round and f.round and any(a.id in f.ordered for a in who)      # (f383) putting this turn's order right
        told = self.service.orders(f, who, kind, target)        # one order a turn is one command, even to the whole party
        for problem in told.problems:
            console.note(problem)
        if told.stopped:
            return
        if told.told:
            whom = next((a.name.split()[0] for a in f.allies() if a.id == target), "") if kind == "heal" else ""
            line = {"focus": "to attack {foe}", "guard": "to guard you", "hold": "to hold back", "back": "to get behind you",
                    "heal": "to tend their own wounds" if target == "self" else (f"to tend {whom}" if whom else "to tend you")}[kind]
            foe = next((e.name for e in f.enemies() if e.id == target), "")
            foe = ("the " + foe) if foe and foe[0].islower() else foe        # "the troll", "the wolf 1", but "Old Brannoch" as is
            console.narrate(("Instead, you tell " if again else "You tell ") + " and ".join(a.name.split()[0] for a in told.told) + " "
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
        effect = ""
        if intent.kind == "other":                             # (f503) an improvisation's effect: read by the helper model's embeddings when
            words = intent.summary or text                     # it is there (the scene's read, a proposal), kept across a restart (f500),
            effect = asked.compute(f"improv_effect:{words}", lambda: read_effect(words))      # handed to the service
        outcome = self.service.round(f, RoundIntent.of(intent, text, effect=effect))   # (f503) the round itself: the service's
        for note in outcome.notes:
            console.note(note)
        if outcome.kind == "talk":                             # words are a free action: the fight waits for the player's real move afterwards
            self.talked(outcome, text)
            return
        if outcome.kind == "free":                             # a movement on its own did not use the action - the player acts again
            self.narrate_round(text)
            self.sync_player()
            self.show()
            self.ws.store.save_combat(self.to_json())
            return
        self.narrate_round(text)
        self.sync_player()
        for m, _by in outcome.killed:                          # those who saw it react now, in the fight, not after it
            down = tuple(a.id[len("ally_"):] for a in f.fighters if a.side == "ally" and a.id.startswith("ally_") and not a.alive)
            self.ws.party_moment(f"{m['name']} has just been killed in front of them.", "heavy", m["id"], f"{m['name']}'s death",
                                 in_fight=True, exclude=down)
        self.ws.mentor_round(self)
        if f.over:
            self.finish()
        else:
            self.show()
            self.ws.store.save_combat(self.to_json())

    def talk(self, intent, target, text: str) -> None:
        """Words are a free action: the fight waits for the player's real move afterwards. (f503) The service tries them (a Challenger's
        call, a parley); the telling and the row are the scene's."""
        words = RoundIntent.of(intent, text)
        words.target = target.id if target is not None else words.target
        self.talked(self.service.round(self.fight, words), text)

    def talked(self, outcome, text: str) -> None:
        f = self.fight
        if outcome.problem:
            console.note(outcome.problem)
            return
        self.narrate_round(text)
        self.sync_player()
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
        """Hired companions who have just gone down, decided and told by the service (hires_down). Returns those killed. (Called on a bare
        stand-in by a test, severity_test: the service is built from its ws and die.)"""
        return [m for m, _by in service_of(self.ws, getattr(self, "rng", None)).hires_down(self.fight)]

    def binding_ability(self, move):
        """The character's Bind a Beast ability if this move is it."""
        return self.service.binding_ability(move)

    def try_bind(self, move, ability, target) -> None:
        """Bind a Beast (services/fight.py try_bind); the notes shown here."""
        notes: list[str] = []
        self.service.try_bind(self.fight, move, ability, target, notes)
        for note in notes:
            console.note(note)

    def try_tame(self, target) -> None:
        notes: list[str] = []
        self.service.try_tame(self.fight, target, notes)
        for note in notes:
            console.note(note)

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
        """(f464) The round's telling is a passage operation of its own, run once the round has committed (scenes/world.py mark_passage):
        the round stands whatever becomes of the telling, and a telling that cannot be written is round_stood in its place, the numbers
        carrying the blows."""
        place, when = self.ws.place.name, self.ws.time_label()        # the round's place and hour as they were: a death moves the player and the clock before the telling runs
        self.ws.mark_passage("round", lambda: self.narrate_round_now(text, place, when), failures.round_stood)

    def narrate_round_now(self, text: str, place: str | None = None, when: str | None = None) -> None:
        f = self.fight
        p = f.player
        foes, gone = self.foes_now()
        you = combat.condition(p) + (", up on high ground" if "elevated" in p.position_tags else "")
        from engine import battlefield as bfm, voice_rules
        boss = any(e.boss for e in f.fighters if e.side == "enemy" and e.alive) or any(e.startswith("BOSS") for e in f.story)
        result = fresh("combat_narrate", cp.NARRATE_SYSTEM,
                       cp.narrate_request(place or self.ws.place.name, when or self.ws.time_label(), text, f.story,
                                          p.weapon_name, you, foes, f.round - 1, self.ws.gear_line(),
                                          self.ws.recent_narration, ground=bfm.narrative_snapshot(f, changed_only=True),
                                          shown=self.fight_shown, worn=self.ws.worn_words("prose"),                         # (f349)
                                          looks=self.ability_looks(), allies=self.ally_looks(), gone=gone),                     # (f373, f385, f415)
                       Narration, self.ws.recent_narration, max_tokens=config.PROSE_MAX_TOKENS, worn=self.ws.worn_words("prose"), said=text)
        text_out = place_figures(result.text, f.hits, console.damage_tags, f.story)
        console.narrate(text_out)
        self.ws.remember_narration(TAG.sub("", result.text))
        self.note_ground_told()                                  # (f571) the telling stood: what it was given of the ground is told
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
        """Use a consumable mid-fight, on yourself or on a party member. It does not use up the action: see free_item. Frugal Hands (the
        scene's roll, on its own die) may keep the draught; the service drinks it."""
        item, problem = self.service.item_for(self.fight, name, target)
        if problem:
            return problem
        g = inventory.GOODS[item.good]
        frugal = self.ws.frugal_save()
        if frugal:
            console.note(f"Somehow there is still one {g.name} left (Frugal Hands).")
        self.last_figures, self.last_item = self.service.use_item(self.fight, item, target, frugal)
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
        """Attribute points spent in the middle of a fight: the fighter brought in line with the character (services/fight.py refresh)."""
        note = self.service.refresh(self.fight)
        if note:
            console.note(note)

    def sync_player(self) -> None:
        note = self.service.sync(self.fight)
        if note:
            console.note(note)

    # ---------- endings ----------

    def companions_after_fight(self, fallen_ids: set[str]) -> None:
        """A companion who went down is out for a day, and may not survive; a Bound summon unmade stays unmade (services/fight.py
        companions_after). The notes shown here."""
        for note in self.service.companions_after(self.fight, fallen_ids):
            console.note(note)

    def finish_duel(self) -> None:
        """A trial of rank is over: nobody dies, nothing is looted, and the hall tells you how it went."""
        f, ws = self.fight, self.ws
        ending = self.service.close(f)
        for note in ending.notes:
            console.note(note)
        ws.combat = None
        if f.hits:
            console.combat_state(self.pane_data())
        console.combat_state(None)
        ws.advance_quiet(ending.minutes)
        ws.trial_over(ending.outcome == "victory", f)
        ws.store.save_player(ws.player)

    def finish(self) -> None:
        f, ws = self.fight, self.ws
        if f.duel:
            self.finish_duel()
            return
        svc = self.service
        ending = svc.close(f)                                # (f503) the row dropped (with what the fight remembered of itself, f499), the
        ws.combat = None                                     # minutes it took, who fell; FightEnded published
        if f.hits:
            console.combat_state(self.pane_data())
        console.combat_state(None)
        ws.advance_quiet(ending.minutes)
        dead, fallen = ending.dead, ending.fallen
        events.fallen_allies(ws, set(ending.fallen_ids))
        ws.party_after_fight(fallen, f.fighters, f.over == "victory", any(e.level >= ws.player.character.level for e in f.fighters if e.side == "enemy"),
                             fight=f)                        # (f508) the service's end writes the party's record (hires, companions, the bound summon); the scene tells
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
        saved = self.service.phoenix()
        if saved is None:
            return False
        item, wait = saved
        console.note(f"The killing blow lands - and {items.display_name(item)} burns white. You rise from the ashes at half strength; "
                     f"the fight is over. (It cannot do this again for {wait:g} days.)")
        ws.narrate("A killing blow falls on the player, but their Phoenix relic flares and refuses it. They stagger up, alive, the "
                   "enemies recoiling or gone.")                                                   # (f415) no length (f375)
        return True

    def victory(self) -> None:
        if self.fight.no_rewards:
            self.sync_player()
            return
        ws, f, svc = self.ws, self.fight, self.service
        c = ws.player.character
        svc.yields(f, allowed=not getattr(ws, "camp_fight", None) and ws.place.type not in ("dungeon", "road"))
        dead = [e for e in f.fighters if e.side == "enemy" and not e.alive]
        yielded = [e for e in f.fighters if e.side == "enemy" and e.alive and e.surrendered]
        if not dead and not yielded and self.tamed:
            console.note(f"The fight is over. {', '.join(self.tamed)} follows you now.")
            self.sync_player()
            return
        if not dead and not yielded:
            if getattr(ws, "orenna_fight", None) != "executioner":
                console.note("They got away - nothing to show for it this time.")
            self.sync_player()
            return
        ws.record_kills(dead)
        if ws.place.danger and ws.owns("victors_name"):
            ws.reputation_add(ws.nearest_town(ws.player.location), 1)
        won = svc.rewards(f, dead, yielded)                   # (f503) the take under the engine's own names; the bodies and carcasses written
        found, skinnable, total_xp = won.found, won.skinnable, won.xp
        to_name = [(item, source, "codex" if kind == "codex" else (self.story_around(source, boss) if kind == "relic" else ""))
                   for item, source, kind, boss in won.to_name]     # (f502) a relic's story as the win found it: the naming asks in these words
        coins = ws.flaws_on_loot(won.coins)
        stowed, copies = [], {}
        for item in found:
            n0 = len(ws.pack)
            stowed.append(ws.to_pack(item))
            copies[item.uid] = [p.uid for p in ws.pack[n0:]]           # (f502) the pack's own copies of the find (engine/inventory.py add)
        levels = svc.award(total_xp, coins)                           # the coin the player gets and the experience, once the finds are stowed
        kept = [st.kept for st in stowed if st.kept is not None]           # (f502) the finds: the aftermath names them as the save holds them
        lying = [st.left for st in stowed if st.left is not None]          # once the naming has run (f417: left here, never pocketed)
        originals = {item.uid: item.model_dump() for item, _, _ in to_name}  # the engine's names: every attempt of the naming starts from them
        fallen = ", ".join(combat.who(e) for e in dead) or "no one - the rest yielded"
        if yielded:
            fallen += (f". THOSE WHO YIELDED (alive and beaten, waiting on the player's choice: tell nothing of what becomes of them): "
                       f"{', '.join(combat.who(e) for e in yielded)}")
        taken = self.take_prisoners(yielded)                               # (f464) the facts before the passage: they commit with the round
        self.ws.hold_yielded([e for e in yielded if e not in taken])         # (f385) the rest wait on the player's word
        facts = {"xp": str(total_xp), "coins": money.fmt(coins) if coins else "", "fallen": ", ".join(combat.who(e) for e in dead)}
        place, when = self.ws.place.name, self.ws.time_label()        # as they were at the win: what follows a fight may move the player
        if found:                                                      # (f502) the finds' names and their lines: an operation of their own,
            self.ws.mark_passage("naming", lambda: self.name_finds(to_name, found, copies, originals), None)   # after the win's commit, before the aftermath
        self.ws.mark_passage("aftermath", lambda: self.aftermath_now(dead, kept, lying, skinnable, fallen, place, when, coins, copies),
                             lambda rng: failures.victory_stood({**facts, "found": ", ".join(self.final_name(i, copies) for i in found)}, rng))   # (f464)
        console.ledger(f"Victory. +{total_xp} XP" + (f", {money.fmt(coins)}" if coins else ""))
        if levels:
            console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
            self.ws.ranks_in_reach(c.level - levels)                          # (f397) a new rank of spells, when one comes within reach
        if skinnable:
            console.note(f"The fallen can be skinned or butchered for {'their' if skinnable > 1 else 'its'} hide and meat - "
                         "say so if you want to.")

    @staticmethod
    def name_of(i) -> str:
        return items.display_name(i) if i.rarity == "legendary" else inventory.label(i)

    def final_name(self, item, copies: dict):
        """(f502) A find's name as the save holds it: the pack's copy (engine/inventory.py add gives the copy a uid of its own) once the
        naming has committed, the engine's name when it rolled back; a find left lying here, from the ground."""
        held = {p.uid: p for p in self.ws.pack}
        for uid in copies.get(item.uid, []):
            if uid in held:
                return self.name_of(held[uid])
        for g in self.ws.store.load_place(self.ws.player.location).ground:
            if (g.get("item") or {}).get("uid") == item.uid:
                return self.name_of(Item.model_validate(g["item"]))
        return self.name_of(item)

    def name_finds(self, to_name: list, found: list, copies: dict, originals: dict) -> None:
        """(f502) The naming operation, after the win commits: every find was committed under the engine's own name (fallback_name,
        plain_codex); here the model names the rare and better pieces and the codices (the five naming tasks are asked outside the
        operation, data/rules/budget.yaml asked_outside, so it runs again with each answer served), the taken list and the turn's record
        follow the name the item bears, and the Found lines are this operation's, shown at its commit, before the aftermath. A naming
        that fails leaves the engine's name; one that crashes rolls back and leaves it too. Every attempt starts from the engine's names
        (`originals`), whatever an earlier attempt left on the objects, so the attempts ask in the same words."""
        ws, store = self.ws, self.ws.store
        renamed = {}
        for item, source, story in to_name:
            fresh = Item.model_validate(originals[item.uid])
            for k in Item.model_fields:
                setattr(item, k, getattr(fresh, k))
            if item.rarity == "legendary":
                store.drop_legendary_name(item.name)                     # the engine's name let go while the model is asked: TAKEN NAMES
        for item, source, story in to_name:                               # is the save's other legendaries, as it read before this feature
            old = item.name
            try:
                if story == "codex":
                    ws.name_codex(item, source)
                elif accessories.is_accessory(item) and (item.trait or item.relic):
                    self.ask_accessory_name(item, source, story)          # (adds the name it gives to the taken list)
                else:
                    self.ask_name(item, source)
            except LLMError:
                if item.rarity == "legendary":
                    store.add_legendary_name(item.name)                   # the engine's name stands, and stays taken
                continue
            if item.name != old:
                renamed[item.uid] = (old, item)
                for held in ws.pack:                                      # the pack's own copies of the find take the name
                    if held.uid in copies.get(item.uid, []):
                        held.name, held.title, held.description, held.relic = item.name, item.title, item.description, item.relic
                        if getattr(item, "spell", None):
                            held.spell = item.spell
        if renamed:
            for r in ledger.ROWS:                                         # the turn's record follows the name
                hit = renamed.get(r.get("item"))
                if hit is not None and r.get("kind") == "gained":
                    r["say"] = f"{inventory.label(hit[1])} is in the player's pack now."
            state = store.load_place(ws.player.location)
            changed = False
            for g in state.ground:                                        # a find left lying here, named all the same
                hit = renamed.get((g.get("item") or {}).get("uid"))
                if hit is not None:
                    g["item"] = hit[1].model_dump()
                    changed = True
            for body in state.bodies:                                     # the body it was carried off
                for old, item in renamed.values():
                    if body.get("carried") == inventory.label(item.model_copy(update={"name": old})):
                        body["carried"] = inventory.label(item)
                        changed = True
            if changed:
                store.save_place(state)
        for item in found:
            if item.rarity == "legendary":
                console.legendary_reveal(item)
            else:
                console.ledger(f"Found: {item.name} ({item.rarity}) - {items.summary(item)}")

    def aftermath_now(self, dead: list, kept: list, left: list, skinnable: int, fallen: str, place: str = "", when: str = "",
                      coins: int = 0, copies: dict | None = None) -> None:
        """(f464) The passage after a fight won, written from the facts the round committed, as an operation of its own: the win stands
        whatever becomes of its telling (victory_stood in its place). `place` and `when` are the win's, captured when it was marked.
        (f502) `kept` and `left` are the finds, named here as the save holds them once the naming operation has run (final_name)."""
        from scenes import world_prompts as wp
        copies = copies or {}
        noticed = [self.final_name(i, copies) for i in kept] + (["a few coins"] if coins else [])
        noticed = [f"{x} (now theirs: show them taking it up)" for x in noticed]      # (f384) taken, not left lying for a 'pick up' to miss
        lying = [self.final_name(i, copies) for i in left]
        end_habits = self.ws.habits_due("fight_end")             # (f412) the companions' habits as it ends, folded into this passage
        aftermath = fresh(
            "combat_aftermath", cp.AFTERMATH_SYSTEM,
            self.aftermath_opening() +
            f"PLACE: {place or self.ws.place.name}\nTIME AND WEATHER: {when or self.ws.time_label()}\nTHE PLAYER: {self.ws.gear_line()}\n"
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

    def take_prisoners(self, yielded: list) -> list:
        """Foes who yielded: people can be bound and kept (questioned, let go, handed to the watch); the rest wait on the player (f385).
        (f503) Chosen and named by the service (captives: no more than walk bound at once, lifecycles.yaml captive.most_escorted; an arc's
        camp leader is taken by the camp's own way, arc_actions.camp_fight_over); made here (make_prisoner takes the record). Returns the
        fighters taken."""
        leader = (getattr(self.ws, "camp_fight", None) or {}).get("leader")
        taken = self.service.captives(self.fight, yielded, leader)
        if not taken:
            return [e for e in yielded if e.name == leader]
        self.ws.surrender_took = True
        for cap in taken:
            self.ws.make_prisoner(cap.name, "", tip=cap.tip, named=False, kind=cap.kind, fighter=cap)
        self.ws.store.save_player(self.ws.player)
        by_id = {e.id: e for e in yielded}
        return [by_id[cap.id] for cap in taken] + [e for e in yielded if e.name == leader]

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

    def goddess_now(self, said: list, event: str) -> None:
        """(f464) The goddess at a death: her words from the model, remembered against her next return; a passage operation of its own,
        goddess_silent in its place when they cannot be written."""
        ws = self.ws
        line = generate("goddess_line", gp.goddess_system(ws.goddess_knowledge()),
                        gp.narration_request("death", event, [("Orenna, on an earlier return", s) for s in said[-4:]]),
                        GoddessLine, temperature=0.9, validation_context={"said": said})
        ws.player.goddess_said = (said + [line.speech])[-8:]
        ws.store.save_player(ws.player)
        console.say(line.speech, "The Goddess")

    def defeat(self) -> None:
        ws = self.ws
        c = ws.player.character
        summary = self.service.fall(self.fight)                  # (f503) the death's price; PlayerFell published
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
        ws.mark_passage("goddess", lambda: self.goddess_now(said, event), failures.goddess_silent)   # (f464) her words, an operation of their own: the death stands either way
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
