"""(f368) The night bot: a player with goals, a persona, and words of its own.

Why: the bot that played the first nights rolled a die every turn and never remembered why it was anywhere. Over twelve hours it took
no contract to its end, walked past every situation the world put in front of it, asked the same seven questions, and died on roads
far above its level because it judged a town safe by the town and not by the road to it. Those are not the gaps of a player, so the
logs could not show how the game treats one: the campaign paths, the consequence rules and the summons were never exercised on purpose.

What a player keeps that the die did not:
  goals      a stack. Take a contract, go where it points, hunt or gather, come back, report. Follow a situation the world told them
             about (a thread the player has met: its paths say what would end it - a creature to kill, someone to persuade, a place
             to clear or find, a contract on the board). Go and see an unvisited place. Retreat home after a death and keep away from
             where it happened for a few days.
  judgement  the level band: a wild place is fought when its creatures top out near the character's level, and a road between two
             towns is taken only when the wild places that road's trouble comes from (engine/roads.nearby_wilds, what the game
             itself rolls from) fit the same band. How far above their level they will go is the persona's.
  needs      a draught when hurt in the wild, a meal when hungry, a bed when tired or when night falls in a town, draughts bought
             when few, loot sold, a better piece of gear put on.
  a persona  weights over all of the above (PERSONAS): the five bots of a night play differently, and a night rotates through them
             the way it rotates the starting points (data/rules/starts.yaml).
  words      every line is written from the state (the place, the person, the creature, the contract), never a fixed sentence alone;
             in a live run the model writes the line itself from the persona, the goal and what the game just said
             (llm/contracts.PlayerLine), so a conversation's second line picks up the first's answer. The template stands in when
             the model cannot, and is the stand-in model's answer in the test suite.

The bot never reads what the player could not know: a situation is followed only once the game has brought it to them (the thread's
`touched`), a contract's place is on the posting, a person's whereabouts are asked of the world by going there.
"""
from __future__ import annotations

import collections
import random
import re
import time

PERSONAS = {
    "steady":   {"text": "a working adventurer: you take a job, do it, and come back for the pay; you talk when there is something to ask",
                 "band": 6, "talk": 2, "job": 1.0, "doors": 0.7, "hunt": 0.4, "roam": 0.5, "trade": 0.8, "chat": 0.7, "improv": 0.5, "indoors": 0.6},
    "talker":   {"text": "curious about people: you ask, follow up on what they say, and remember names; work comes up in talk",
                 "band": 4, "talk": 4, "job": 0.5, "doors": 1.0, "hunt": 0.2, "roam": 0.6, "trade": 0.5, "chat": 2.0, "improv": 0.8, "indoors": 0.7},
    "wanderer": {"text": "you want to see what is over the next hill: the road more than the board, and a look at everything",
                 "band": 8, "talk": 2, "job": 0.4, "doors": 0.8, "hunt": 0.5, "roam": 2.0, "trade": 0.6, "chat": 0.6, "improv": 1.2, "indoors": 0.3},
    "hunter":   {"text": "you live for the fight: you hunt above your level, take bounties, and spend your coin on gear and draughts",
                 "band": 14, "talk": 1, "job": 1.0, "doors": 0.5, "hunt": 2.0, "roam": 0.6, "trade": 1.2, "chat": 0.3, "improv": 0.3, "indoors": 0.2},
    "careful":  {"text": "you take no chances: you fight below your level, sleep indoors, keep draughts by you, and ask before you act",
                 "band": 0, "talk": 3, "job": 0.8, "doors": 0.9, "hunt": 0.1, "roam": 0.3, "trade": 1.0, "chat": 1.0, "improv": 0.4, "indoors": 1.0},
}
ROTATION = ["steady", "talker", "wanderer", "hunter", "careful"]
ROAD_SLACK = 6                 # a road's wilds may top out this far past the band: the character deters what is well below them
AVOID_DAYS = 3                 # after a death: keep away from where it happened
STOP = {"the", "you", "your", "a", "an", "it", "its", "he", "his", "she", "her", "they", "their", "there", "as", "when", "but", "and", "then",
        "what", "who", "where", "that", "this", "in", "on", "at", "with", "for", "from", "of", "to", "by", "i", "we", "no", "yes", "not", "if",
        "so", "or", "is", "are", "was", "were", "be", "do", "does", "did", "have", "has", "had", "one", "some", "all", "any", "here", "now", "the player"}


def persona_for(seed: int) -> str:
    return ROTATION[(seed - 1) % len(ROTATION)]


def notable(passage: str) -> set[str]:
    """The words a passage gives a player to pick up: names and other capitalised words that are not just sentence openers."""
    out = set()
    for m in re.finditer(r"\b([A-Z][a-z']{2,})\b", passage or ""):
        w = m.group(1)
        if w.lower() not in STOP:
            out.add(w.lower())
    return out


def refers_to(line: str, passage: str, names: list[str]) -> bool:
    """Does the line pick up something from the passage before it, or name someone or something the scene shows?"""
    words = set(re.findall(r"[a-z']{3,}", (line or "").lower()))
    pool = notable(passage)
    for n in names:
        for w in re.findall(r"[a-z']{3,}", (n or "").lower()):
            if w not in STOP:
                pool.add(w)
    return bool(words & pool)


class Bot:
    """Types what a player would, from what the scene shows and what they mean to do."""

    QUESTIONS = ["What's been happening around here lately?", "Do you know of any work going?", "What do you make of the roads these days?",
                 "Who runs things in this town?", "Tell me about yourself.", "Any news from the other towns?", "What should a stranger steer clear of here?",
                 "How long have you been here?", "What do you do when the day's work is done?", "Who here would you trust with your life?",
                 "What's the oldest thing in this place?", "Is there anything you need done?", "Where would you go, if you could go anywhere?",
                 "What do people here argue about?", "Have you seen anything strange lately?", "Who should I meet while I'm here?"]
    TOPICS = ["the town", "work", "the road ahead", "the news", "their trade", "the weather lately"]
    IMPROV = ["I fish in the river for supper.", "I whistle an old marching tune.", "I climb the nearest tree for a look around.",
              "I carve a mark into the signpost.", "I try my luck at a game of dice.", "I practise sword forms for an hour.",
              "I sketch the view in my notebook.", "I check my boots for wear and mend a strap."]
    WILD_IMPROV = ["I climb up onto the ledge above me for a better look.", "I light a torch and hold it up to the dark.",   # (f395) sense, in the wild
                   "I wedge a rock into the gap behind me.", "I wade into the shallows to see what is there.",
                   "I dig at the loose earth by the wall.", "I call out to see if anyone is here."]
    OUTLANDISH = ["I grow wings and fly away.", "I summon a dragon to carry me.", "I turn the nearest stone into gold.",   # (f395) the ruling's no
                  "I walk straight through the wall."]
    SEARCH = ["I carefully search the area for tracks.", "I look around.", "I listen for anything unusual.", "I take a good look at the people here."]
    LEAVE = ["Thanks, I'll let you get on.", "That's all I wanted to know. Good day.", "I'd best be moving on."]
    JOB_KINDS = ("hunt", "bounty", "gather", "materials")

    def __init__(self, ws, world, rng: random.Random, stub=None, persona: str = "", run=None):
        self.ws, self.world, self.rng, self.stub, self.run = ws, world, rng, stub, run
        self.persona = persona
        self.P = dict(PERSONAS.get(persona) or PERSONAS["steady"])
        self.talks = 0                               # lines said in the conversation open now
        self.spoken_to: collections.deque = collections.deque(maxlen=6)
        self.been: collections.deque = collections.deque(maxlen=8)
        self.visited: set[str] = set()
        self.here_for = 0                            # turns spent at this place
        self.asked_hires: dict = {}                  # companion name -> the game day they were last asked how they are
        self.last_loc = ""
        self.last_text = ""
        self.goals: list[dict] = []
        self.given_up: set[str] = set()              # quest and path ids the bot stopped trying
        self.avoid: dict[str, int] = {}              # place -> the minute it may be gone to again
        self.seen_threads: set[str] = set()
        self.tried_gear: set[str] = set()
        self.hall_of: dict[str, str] = {}            # quest id -> the hall it was taken from
        self.home = ""
        self.recent: collections.deque = collections.deque(maxlen=8)
        self.meta: dict = {}
        self.stats = {"persona": persona, "lines": {"model": 0, "template": 0}, "refers": 0, "refers_talk": 0, "talk_lines": 0, "with_passage": 0,
                      "contracts_taken": 0, "contracts_done": 0, "doors_seen": 0, "doors_followed": 0, "goals_done": collections.Counter(),
                      "goals_dropped": collections.Counter(), "deaths": 0, "deaths_above_band": 0, "waits": 0, "fights": 0, "clarified": 0,
                      "model_failed": 0, "model_seconds": 0.0, "blocked": 0}
        self.refused_last: set[str] = set()          # (f391) the refusals the game showed last turn
        try:
            self.deaths_seen = self.c.deaths
            self.done_seen = sum(self.ws.player.guild_done.values())
            self.held_seen = {q["id"] for q in self.ws.player.quests}
            from engine import pulse
            self.home = pulse.town_of(world, self.ws.player.location)
        except Exception:
            self.deaths_seen, self.done_seen, self.held_seen = 0, 0, set()
        from engine import actions
        self.kinds = set(getattr(actions, "KINDS", ()) or ())

    # ---- the character and the scene
    @property
    def c(self):
        return self.ws.player.character

    def hp(self) -> float:
        from engine import pools
        return (self.c.health or 0) / max(1, pools.maximum(self.c, "health"))

    def where(self) -> str:
        p = self.world.places.get(self.ws.player.location)
        return p.name if p else self.ws.player.location

    def place(self):
        return self.world.places.get(self.ws.player.location)

    def band_text(self) -> str:
        p = self.place()
        return f"{p.danger[0]}-{p.danger[1]}" if p and p.danger else ""

    def names_here(self) -> list[str]:
        out = [n.label() for n in self.ws.present] + [m.get("name", "") for m in self.ws.player.party]
        p = self.place()
        if p:
            out.append(p.name)
        return out

    def passage(self) -> str:
        rows = getattr(self.run, "passage", None) or []
        return "\n".join(x for x in rows if x).strip()

    def intend(self, kind: str, **fields) -> dict:
        """The plan the stand-in interpreter answers with (the real model reads the words); an unknown kind becomes a look."""
        return {"kind": kind if kind in self.kinds else "look", **fields}

    def state(self) -> dict:
        try:
            return self.ws.store.load_world_state() or {}
        except Exception:
            return {}

    # ---- the level band: what the character can fight, and which roads they can take
    def fits(self, place_id: str) -> bool:
        p = self.world.places.get(place_id)
        if p is None:
            return False
        if self.avoid.get(place_id, -1) > self.ws.minutes:
            return False
        if not p.danger:
            return True
        return p.danger[1] <= self.c.level + self.P["band"]

    def leg_ok(self, a: str, b: str) -> bool:
        from engine import roads
        limit = self.c.level + self.P["band"] + ROAD_SLACK
        wilds = roads.nearby_wilds(self.world, a, b)
        return all(self.world.places[w].danger[1] <= limit and self.avoid.get(w, -1) <= self.ws.minutes for w in wilds)

    def route(self, target: str) -> list[str] | None:
        """The hops to a place when every one of them, and every road between, fits the band; else None."""
        here = self.ws.player.location
        if target == here:
            return []
        found = self.world.path(here, target) if here in self.world.places else None
        if not found:
            return None
        hops = found[0][1:] if found[0] and found[0][0] == here else found[0]
        prev = here
        for h in hops:
            if not self.fits(h) or not self.leg_ok(prev, h):
                return None
            prev = h
        return hops

    REFUSAL = re.compile(r"\b(closed|not|no|nothing|can't|cannot|isn't|aren't|don't|nowhere|already|too|need|unknown)\b", re.I)

    def read_refusals(self) -> None:
        """(f391) The same refusal two turns running means what the bot is after cannot be done now: it gives that goal up and keeps away
        from its place for a day, as a player would, instead of asking 741 times (a night's run did, at a closed way out of a mine)."""
        notes = getattr(self.run, "turn_notes", None) or []
        keys = {re.sub(r"\d+", "#", n.lower())[:90] for n in notes if self.REFUSAL.search(n)}
        if keys & self.refused_last and self.goals:
            g = self.goals.pop()
            self.stats["goals_dropped"][g["kind"]] += 1
            self.stats["blocked"] += 1
            if g.get("place"):
                self.avoid[g["place"]] = self.ws.minutes + 1440
            keys = set()
        self.refused_last = keys

    # ---- what happened since the last line: deaths, contracts, doors
    def watch(self) -> None:
        self.read_refusals()
        c = self.c
        if c.deaths > self.deaths_seen:
            self.stats["deaths"] += c.deaths - self.deaths_seen
            self.deaths_seen = c.deaths
            dead_at = self.last_loc
            p = self.world.places.get(dead_at)
            if p and p.danger and p.danger[0] > c.level:
                self.stats["deaths_above_band"] += 1
            until = self.ws.minutes + AVOID_DAYS * 1440
            if dead_at:
                self.avoid[dead_at] = until
            for g in self.goals:
                if g.get("place"):
                    self.avoid[g["place"]] = until
            for g in self.goals:
                self.stats["goals_dropped"][g["kind"]] += 1
            self.goals = []
            if self.home and self.ws.player.location != self.home:
                self.goals.append({"kind": "retreat", "place": self.home, "tries": 0})
        done = sum(self.ws.player.guild_done.values())
        if done > self.done_seen:
            self.stats["contracts_done"] += done - self.done_seen
            self.done_seen = done
        held = {q["id"] for q in self.ws.player.quests}
        new = held - self.held_seen
        if new:
            self.stats["contracts_taken"] += len(new)
            for qid in new:
                self.hall_of[qid] = self.ws.hall_here() or self.ws.player.location
        self.held_seen = held
        for th in self.state().get("threads", []):
            if th.get("touched") and th["id"] not in self.seen_threads:
                self.seen_threads.add(th["id"])
                self.stats["doors_seen"] += 1

    # ---- one line
    def decide(self) -> tuple[str, str]:
        t0 = time.perf_counter()
        self.watch()
        text, intent, kind = self.choose()
        same = self.__dict__.setdefault("_same", collections.deque(maxlen=4))
        same.append(text)
        if len(same) == same.maxlen and len(set(same)) == 1:              # the same line four times running is a loop, whatever it is: break it
            same.clear()
            if self.ws.combat:
                alive = [e for e in self.ws.combat.fight.enemies() if e.alive]
                tgt = min(alive, key=lambda e: e.hp) if alive else None
                text, intent, kind = (f"I attack {tgt.name}." if tgt else "I attack."), {"kind": "attack", "target": tgt.id if tgt else "", "summary": "bot"}, "fight"
            else:
                text, intent, kind = "I look around.", self.intend("look"), "look"
        goal = self.meta.get("goal", "") if self.meta.get("_fresh") else ""
        passage = self.passage()
        source = "template"
        if self.persona and self.stub is None and self.run is not None and kind != "fight" and text not in self.OUTLANDISH:   # (f395) said as is
            line = self.model_line(text, intent, kind, passage)
            if line:
                text, source = line, "model"
        self.stats["lines"][source] += 1
        refers = bool(passage) and refers_to(text, passage, self.names_here())
        if passage:
            self.stats["with_passage"] += 1
            self.stats["refers"] += int(refers)
        if kind == "talk":
            self.stats["talk_lines"] += 1
            self.stats["refers_talk"] += int(refers)
        if kind == "wait":
            self.stats["waits"] += 1
        if kind == "fight":
            self.stats["fights"] += 1
        self.meta = {"goal": goal, "persona": self.persona, "source": source, "refers": refers, "band": self.band_text(),
                     "bot_seconds": round(time.perf_counter() - t0, 2)}
        self.recent.append(text)
        if self.stub is not None:
            self.stub.plan = [intent]
        self.last_text = text
        loc = self.ws.player.location
        self.here_for = self.here_for + 1 if loc == self.last_loc else 0
        self.last_loc = loc
        self.visited.add(loc)
        if loc not in self.been:
            self.been.append(loc)
        return text, kind

    def label(self, goal: str) -> None:
        self.meta = {"goal": goal, "_fresh": True}

    def choose(self) -> tuple[str, dict, str]:
        ws = self.ws
        self.meta = {}
        if ws.combat:
            self.label("fight")
            return self.fight_line()
        if getattr(ws, "pending_clarify", None):
            self.stats["clarified"] += 1
            self.label("clarify")
            return "I look around.", self.intend("look"), "look"
        if ws.partner is not None:
            return self.talk_step()
        need = self.need_step()
        if need:
            return need
        p = self.place()
        fresh = [n for n in ws.present if n.id not in self.spoken_to]
        if p is not None and p.danger is None and fresh and self.here_for <= 1 and self.rng.random() < self.P["chat"] * 0.35:
            return self.idle(only="talk")                                 # just arrived: a word with whoever is here before the job
        if not self.goals:
            self.new_goal()
        guard = 0
        while self.goals and guard < 6:
            guard += 1
            step = self.pursue(self.goals[-1])
            if step:
                return step
        return self.idle()

    # ---- a conversation
    def talk_step(self) -> tuple[str, dict, str]:
        ws, rng = self.ws, self.rng
        partner = ws.partner
        g = self.goals[-1] if self.goals else {}
        self.talks += 1
        if g.get("kind") == "persuade" and g.get("npc") == partner.id:
            g["tries"] = g.get("tries", 0) + 1
            self.label("follow:persuade")
            if self.path_done(g):
                self.finish(g)
                self.talks = 0
                return rng.choice(["Thank you. That is all I ask.", "Good. I knew you would see it.", "I'll hold you to that."]), self.intend("leave_conversation"), "leave"
            if g["tries"] > 4:
                self.given_up.add(g["path"])
                self.stats["goals_dropped"]["follow"] += 1
                self.goals.pop()
                self.talks = 0
                return rng.choice(self.LEAVE), self.intend("leave_conversation"), "leave"
            ask = rng.choice([f"I need your help with {g['title']}. Will you stand with me on it?", f"You could end {g['title']}, or help me do it. Will you?",
                              f"Think of what {g['title']} is costing this place. Help me put it right."])
            return f'"{ask}"', self.intend("talk", target=partner.id, speech=ask, checks=["persuasion"]), "talk"
        if g.get("kind") == "report":
            self.label("report")
            self.talks = 0
            self.stats["goals_done"]["report"] += 1
            self.goals.pop()
            return rng.choice(self.LEAVE), self.intend("leave_conversation"), "leave"
        self.label("idle:talk")
        q = self.question_for(g) if self.talks <= self.P["talk"] else ""
        if q:
            return f'"{q}"', self.intend("talk", target=partner.id, speech=q), "talk"
        self.talks = 0
        return rng.choice(self.LEAVE), self.intend("leave_conversation"), "leave"

    def question_for(self, g: dict) -> str:
        """(f391) A question this person has not been asked before, ever: the night's runs put the same seven questions to one rider
        thirty-five times, and the game's answers to that measured the bot, not the game."""
        partner = getattr(self.ws, "partner", None)
        asked = self.__dict__.setdefault("_asked_of", {}).setdefault(getattr(partner, "id", ""), [])
        title = g.get("title") or ""
        pool = [f"What do you know about {title}?", f"Who would know more about {title}?", f"What would it take to settle {title}?"] \
            if g.get("kind") == "follow" and title and self.rng.random() < 0.6 else list(self.QUESTIONS)
        fresh = [q for q in pool if q not in asked]
        if not fresh:
            return ""
        q = self.rng.choice(fresh)
        asked.append(q)
        return q

    # ---- needs
    def need_step(self) -> tuple[str, dict, str] | None:
        from engine import clock, inventory as inv
        ws, c, rng = self.ws, self.c, self.rng
        p = self.place()
        if p is None:
            return None
        in_town = p.danger is None
        pack = c.inventory
        draughts = inv.count_of(pack, "healing_draught")
        hp = self.hp()
        if hp < 0.45 and draughts and (p.danger or ws.wildlife):
            self.label("need:heal")
            return "I drink a healing draught.", self.intend("use", item="healing draught"), "heal"
        hungry = c.hunger >= 60
        if hungry and p.type == "inn":
            self.label("need:eat")
            return "I order a hot meal.", self.intend("buy", ware="meal"), "eat"
        if hungry and inv.count_of(pack, "trail_ration"):
            self.label("need:eat")
            return "I eat a trail ration.", self.intend("use", item="trail ration"), "eat"
        tired = c.fatigue >= 60
        dark = clock.period(ws.minutes) in ("night", "deep night")
        if tired or (hp < 0.5 and in_town) or (dark and in_town and rng.random() < self.P["indoors"]):
            self.label("need:rest")
            return self.rest_line(p)
        if in_town and p.type in ("shop", "inn", "guild", "smithy", "workshop", "town", "village", "city"):
            trade = self.trade_step(p)
            if trade:
                return trade
        return None

    def trade_step(self, p) -> tuple[str, dict, str] | None:
        """Draughts bought when few, loot sold, better gear worn: when the persona cares and the coin is there."""
        from engine import inventory as inv
        ws, c, rng = self.ws, self.c, self.rng
        if rng.random() > self.P["trade"] * 0.5:
            return None
        sellers = [(n, w) for n in ws.present for w in self.world.roles[n.role].sells]
        draught = next(((n, w) for n, w in sellers if w.item == "healing_draught"), None)
        if draught and inv.count_of(c.inventory, "healing_draught") < 2 and c.coins >= draught[1].price * 2:
            self.label("need:buy")
            return f"I buy a healing draught from {draught[0].label()}.", self.intend("buy", ware="healing draught", target=draught[0].id), "shop"
        loot = [i for i in c.inventory if not i.good and i.base != "raw_material" and i.uid not in self.tried_gear]
        gear = [i for i in loot if i.item_level >= 1]
        worn = [i.item_level for i in c.equipment.values() if i is not None]
        if gear and worn:
            best = max(gear, key=lambda i: i.item_level)
            if best.item_level >= min(worn) + 3:
                self.tried_gear.add(best.uid)
                self.label("need:equip")
                return f"I put on the {best.name}.", self.intend("equip", item=best.name), "gear"
        buyers = [n for n in ws.present if self.world.roles[n.role].buys]
        if buyers and loot:
            item = min(loot, key=lambda i: i.item_level)
            cat = inv.category(item)
            buyer = next((n for n in buyers if cat in self.world.roles[n.role].buys or "any" in self.world.roles[n.role].buys), None)
            if buyer and item.item_level + 5 < max(worn or [1]):
                self.tried_gear.add(item.uid)
                self.label("need:sell")
                return f"I sell the {item.name} to {buyer.label()}.", self.intend("sell", item=item.name, target=buyer.id), "shop"
        return None

    def rest_line(self, p) -> tuple[str, dict, str]:
        if p.type == "inn":
            return "I take a room and sleep until morning.", self.intend("wait", wait_until="dawn"), "rest"
        inn = next((x for x in self.world.neighbors(p.id) if self.world.places[x].type == "inn"), None)
        if inn and p.danger is None:
            return f"I walk over to {self.world.places[inn].name}.", self.intend("move", destination=inn), "move"
        return "I make camp and rest until morning.", self.intend("wait", wait_until="dawn"), "rest"

    # ---- goals
    def new_goal(self) -> None:
        ws, rng, P = self.ws, self.rng, self.P
        held = [q for q in ws.player.quests if q["kind"] in self.JOB_KINDS and q["id"] not in self.given_up]
        if held:
            from engine import quests
            q = sorted(held, key=lambda q: not quests.done(q, self.ws.pack))[0]
            self.goals.append({"kind": "contract", "quest": q["id"], "tries": 0})
            return
        follow = self.doable_thread()
        if follow and rng.random() < P["doors"]:
            self.goals.append({"kind": "follow", "thread": follow["id"], "title": follow["title"], "tries": 0})
            self.stats["doors_followed"] += 1
            return
        hall = ws.hall_here()
        if hall and self.contract_to_take() and rng.random() < P["job"] * 0.8:
            self.goals.append({"kind": "board", "place": hall, "tries": 0})
            return
        if not hall and rng.random() < P["job"] * 0.25:
            home_hall = self.nearest_hall()
            if home_hall and self.route(home_hall) is not None:
                self.goals.append({"kind": "go", "place": home_hall, "why": "work", "tries": 0})
                return
        if rng.random() < P["roam"] * 0.3:
            fresh = self.unvisited()
            if fresh:
                self.goals.append({"kind": "go", "place": fresh, "why": "see", "tries": 0})
                return
        if rng.random() < P["hunt"] * 0.3:
            wild = self.hunting_ground()
            if wild:
                self.goals.append({"kind": "hunt", "place": wild, "tries": 0})

    def pursue(self, g: dict) -> tuple[str, dict, str] | None:
        kind = g["kind"]
        step = getattr(self, f"goal_{kind}", None)
        if step is None:
            self.goals.remove(g)
            return None
        out = step(g)
        if out is None and g in self.goals and g.get("_done"):
            self.goals.remove(g)
        return out

    def finish(self, g: dict, how: str = "done") -> None:
        if how != "quiet":
            self.stats["goals_done" if how == "done" else "goals_dropped"][g["kind"]] += 1
        if g in self.goals:
            self.goals.remove(g)

    def go_step(self, g: dict, place: str, why: str = "") -> tuple[str, dict, str] | None:
        """A line toward a place, or None when there (or when it cannot be reached inside the band: the goal is dropped)."""
        if self.ws.player.location == place:
            return None
        hops = self.route(place)
        if hops is None:
            self.finish(g, "dropped")
            return None
        g["tries"] = g.get("tries", 0) + 1
        if g["tries"] > 8 and not g.get("_long"):
            self.finish(g, "dropped")
            return None
        dest = self.world.places[place]
        verb = self.rng.choice(["I set out for", "I take the road to", "I head for", "I make for"]) if dest.danger is None and len(hops) > 1 \
            else self.rng.choice(["I walk over to", "I head to", "I go to"])
        tail = {"work": " to see what work the board has.", "see": ", to see the place.", "retreat": " and get off these roads."}.get(why, "")
        return f"{verb} {dest.name}{tail or '.'}", self.intend("move", destination=place), "move"

    def goal_go(self, g: dict):
        self.label("go:" + g.get("why", ""))
        step = self.go_step(g, g["place"], g.get("why", ""))
        if step is None and g in self.goals:
            self.finish(g)
        return step

    def goal_retreat(self, g: dict):
        self.label("retreat")
        g["_long"] = True
        step = self.go_step(g, g["place"], "retreat")
        if step is None and g in self.goals:
            self.finish(g)
        return step

    def goal_board(self, g: dict):
        self.label("board")
        if self.ws.player.location != g["place"]:
            return self.go_step(g, g["place"], "work")
        wait = self.clerk_wait(g)
        if wait is not None:
            return wait or None
        take = self.contract_to_take()
        self.finish(g, "quiet")                                      # the measure is the contract taken (watch), not the asking
        if not take:
            return None
        return f"I take the contract: {take['title']}.", self.intend("accept_quest", item=take["title"]), "board"

    def clerk_wait(self, g: dict):
        """At the hall with no clerk at the desk: wait a while for them, a few times, then let the goal go. None when the clerk is here."""
        if self.ws.clerk_here() is not None:
            return None
        g["waited"] = g.get("waited", 0) + 1
        if g["waited"] > 3:
            self.finish(g, "quiet")
            return ""
        return "I wait for the clerk to come back to the desk.", self.intend("wait", wait_minutes=60), "wait"

    def goal_contract(self, g: dict):
        from engine import quests
        ws = self.ws
        q = next((x for x in ws.player.quests if x["id"] == g["quest"]), None)
        if q is None:
            self.finish(g)                                            # turned in, or gone
            return None
        self.label(f"contract:{q['kind']}")
        if quests.done(q, ws.pack):
            hall = self.hall_of.get(q["id"]) or self.nearest_hall()
            self.finish(g)
            if hall:
                self.goals.append({"kind": "report", "place": hall, "title": q["title"], "tries": 0})
            return None
        g["tries"] = g.get("tries", 0) + 1
        if g["tries"] > 24 or (q.get("deadline") and q["deadline"] <= ws.minutes):
            self.given_up.add(q["id"])
            self.finish(g, "dropped")
            return None
        if q["kind"] in ("hunt", "bounty", "materials"):
            if "place" not in g:
                g["place"], g["creature_id"] = self.job_site(q)
            place, cid = g["place"], g["creature_id"]
            if not place:
                self.given_up.add(q["id"]); self.finish(g, "dropped"); return None
            if ws.player.location != place:
                g["_long"] = True
                step = self.go_step(g, place)
                if step is None and g not in self.goals:
                    self.given_up.add(q["id"])
                return step
            creature = self.world.bestiary.get(cid) if cid else None
            return self.hunt_line(creature.name if creature else "", cid)
        if q["kind"] == "gather":
            from engine import inventory as inv
            good = inv.GOODS.get(q["good"])
            biomes = set((good.grows_in or {}).keys()) if good else set()
            spots = [p for p in self.world.places.values() if p.danger and p.type != "road" and p.biome in biomes and self.fits(p.id)]
            spot = self.nearest(spots)
            if not spot:
                self.given_up.add(q["id"]); self.finish(g, "dropped"); return None
            if ws.player.location != spot:
                g["_long"] = True
                return self.go_step(g, spot)
            return f"I forage for {good.name if good else q['title']}.", self.intend("forage", item=good.name if good else ""), "forage"
        self.given_up.add(q["id"])
        self.finish(g, "dropped")
        return None

    def job_site(self, q: dict) -> tuple[str | None, str]:
        """Where a hunting job is done and what is hunted: the posting's place and creature, or for a material, the nearest place in the
        band where a creature that drops it lives."""
        if q["kind"] in ("hunt", "bounty"):
            return (q.get("place") if q.get("place") in self.world.places else self.hunting_ground()), q.get("creature", "")
        from engine import items
        m = items.MATERIALS.get(q.get("material", ""))
        town = self.home or self.ws.player.location
        for cid in (m.drops_from if m else []):
            place = self.where_lives(cid, town, anywhere=True)
            if place:
                return place, cid
        return None, ""                                                   # nothing that drops it lives within reach: not a job for now

    def goal_report(self, g: dict):
        ws = self.ws
        self.label("report")
        if ws.player.location != g["place"]:
            g["_long"] = True
            return self.go_step(g, g["place"])
        clerk = ws.clerk_here()
        if clerk is None:
            wait = self.clerk_wait(g)
            return wait or None
        line = f"I report to {clerk.label()}: {g['title']} is done."
        return line, self.intend("talk", target=clerk.id, speech=f"{g['title']} - it's done. I'm here for the pay."), "talk"

    def goal_hunt(self, g: dict):
        self.label("hunt")
        if self.ws.player.location != g["place"]:
            return self.go_step(g, g["place"])
        g["tries"] = g.get("tries", 0) + 1
        if g["tries"] > 6:
            self.finish(g)
            return None
        return self.hunt_line("")

    def goal_follow(self, g: dict):
        """A situation the world brought to the player: take its paths as they open, one at a time."""
        from engine import events
        state = self.state()
        th = next((t for t in state.get("threads", []) if t["id"] == g["thread"]), None)
        self.label("follow")
        if th is None or th.get("status") != "active":
            self.finish(g)
            return None
        for path in th.get("paths") or []:
            if path.get("done") or path["id"] in self.given_up:
                continue
            try:
                if events.path_met(path, state, th):
                    continue
            except Exception:
                pass
            sub = self.path_goal(th, path, state)
            if sub:
                self.goals.append(sub)
                return None
            self.given_up.add(path["id"])
        self.finish(g, "dropped" if any(not p.get("done") for p in th.get("paths") or []) else "done")
        return None

    def path_goal(self, th: dict, path: dict, state: dict) -> dict | None:
        kind = path["kind"]
        base = {"path": path["id"], "thread": th["id"], "title": th["title"], "how": path.get("how", ""), "tries": 0}
        if kind == "kill":
            spawn = next((s for s in state.get("spawns", []) if s["id"] == path.get("spawn")), None) if path.get("spawn") else None
            place = spawn["place"] if spawn else self.where_lives(path.get("target", ""), th["place"])
            creature = self.world.bestiary.get(spawn["creature"] if spawn and spawn.get("creature") else path.get("target", ""))
            if place and self.fits(place):
                return {"kind": "kill", "place": place, "creature": creature.name if creature else (spawn or {}).get("name", ""),
                        "creature_id": creature.id if creature else "", **base}
        elif kind == "persuade":
            if self.ws.store.npc_exists(path["target"]):
                n = self.ws.store.load_npc(path["target"])
                if not n.gone and n.location in self.world.places:
                    return {"kind": "persuade", "npc": n.id, "place": n.location, **base}
        elif kind == "clear":
            if path["target"] in self.world.places and self.fits(path["target"]):
                return {"kind": "clear", "place": path["target"], **base}
        elif kind == "find":
            if path["target"] in self.world.places and self.fits(path["target"]):
                return {"kind": "find", "place": path["target"], **base}
        elif kind == "contract":
            hall = self.nearest_hall()
            if hall:
                return {"kind": "posting", "place": hall, **base}
        return None

    def path_done(self, g: dict) -> bool:
        from engine import events
        state = self.state()
        th = next((t for t in state.get("threads", []) if t["id"] == g["thread"]), None)
        if th is None or th.get("status") != "active":
            return True
        path = next((p for p in th.get("paths") or [] if p["id"] == g["path"]), None)
        if path is None or path.get("done"):
            return True
        try:
            return events.path_met(path, state, th)
        except Exception:
            return False

    def path_step(self, g: dict, limit: int) -> tuple[str, dict, str] | None | bool:
        """The shared part of a path goal: done, dropped, or on the way. Returns a line, None when at the place, or False when over."""
        if self.path_done(g):
            self.finish(g)
            return False
        g["tries"] = g.get("tries", 0) + 1
        if g["tries"] > limit:
            self.given_up.add(g["path"])
            self.finish(g, "dropped")
            return False
        if self.ws.player.location != g["place"]:
            g["_long"] = True
            step = self.go_step(g, g["place"])
            if step is None and g not in self.goals:
                self.given_up.add(g["path"])
                return False
            return step
        return None

    def goal_kill(self, g: dict):
        self.label("follow:kill")
        step = self.path_step(g, 12)
        return None if step is False else step if step else self.hunt_line(g.get("creature", ""), g.get("creature_id", ""))

    def goal_persuade(self, g: dict):
        self.label("follow:persuade")
        step = self.path_step(g, 12)
        if step is not None:
            return None if step is False else step
        n = next((x for x in self.ws.present if x.id == g["npc"]), None)
        if n is None:
            return "I wait for a while, watching the door.", self.intend("wait", wait_minutes=60), "wait"
        self.talks = 1
        ask = f"I need your help with {g['title']}. Will you help me end it?"
        return f"I go to {n.label()} and ask for their help with {g['title']}.", self.intend("talk", target=n.id, speech=ask, checks=["persuasion"]), "talk"

    def goal_clear(self, g: dict):
        self.label("follow:clear")
        step = self.path_step(g, 40)
        if step is not None:
            return None if step is False else step
        ws = self.ws
        d = ws.dungeon_here()
        if d:
            if self.hp() < 0.5 and ws.player.delve:
                return f"I climb back out of {d['name']} to rest.", self.intend("leave_dungeon"), "delve"
            return f"I go down into {d['name']}.", self.intend("delve"), "delve"
        return self.hunt_line("")

    def goal_find(self, g: dict):
        self.label("follow:find")
        step = self.path_step(g, 8)
        if step is not None:
            return None if step is False else step
        return f"I search {self.where()} carefully for any sign of {g['title']}.", self.intend("search", seek=g["title"]), "search"

    def goal_posting(self, g: dict):
        self.label("follow:contract")
        step = self.path_step(g, 10)
        if step is not None:
            return None if step is False else step
        wait = self.clerk_wait(g)
        if wait is not None:
            return wait or None
        try:
            board = self.ws.ensure_board()
        except Exception:
            board = []
        q = next((x for x in board if x.get("thread") == g["thread"]), None)
        if q is None or any(x["id"] == q["id"] for x in self.ws.player.quests):
            self.finish(g, "done" if q is None else "done")
            return None
        return f"I take the contract: {q['title']}.", self.intend("accept_quest", item=q["title"]), "board"

    # ---- hunting
    def hunt_line(self, creature: str, creature_id: str = "") -> tuple[str, dict, str]:
        """Attack what is in view when it is the quarry (or when anything will do, or the persona fights whatever comes); else search on."""
        ws = self.ws
        if ws.wildlife:
            seen = ws.wildlife[1][0] if ws.wildlife[1] else None
            name = seen.name if seen else ws.wildlife[0].name.lower()
            quarry = not creature_id or ws.wildlife[0].id == creature_id or self.P["hunt"] >= 1.0
            if quarry:
                return f"I attack the {name}.", self.intend("attack"), "fight"
        here = self.where()
        if creature:
            from engine import quests
            them = quests.plural(creature).lower()
            text = self.rng.choice([f"I search {here} for {them}.", f"I keep looking for {them} around {here}.", f"I follow any tracks of {them} through {here}.",
                                    f"I work my way through {here}, watching for {them}."])
            return text, self.intend("search", seek=creature), "search"
        text = self.rng.choice([f"I search {here} for anything worth hunting.", f"I beat through {here} looking for game.", f"I scout {here} for tracks."])
        return text, self.intend("search"), "search"

    def where_lives(self, creature_id: str, town: str, anywhere: bool = False) -> str | None:
        """The nearest wild place in the band whose roster has the creature, looking first around its town (its region, unless anywhere)."""
        from engine import encounters
        if not creature_id:
            return None
        region = "" if anywhere else (self.world.places[town].region if town in self.world.places else "")
        spots = [p for p in self.world.places.values() if p.danger and p.type not in ("road", "dungeon") and self.fits(p.id)
                 and (not region or p.region == region)]
        spots = sorted(spots, key=lambda p: (self.world.path(town, p.id) or ([], 10 ** 9))[1]) if town in self.world.places else spots
        for p in spots[:20 if anywhere else 12]:
            try:
                if creature_id in encounters.ensure_roster(self.ws.store, self.world, p.id):
                    return p.id
            except Exception:
                continue
        return None

    def hunting_ground(self) -> str | None:
        here = self.ws.player.location
        spots = [p for p in self.world.places.values() if p.danger and p.type not in ("road", "dungeon") and self.fits(p.id)
                 and p.danger[1] >= self.c.level - 8]
        return self.nearest(spots, here)

    def nearest(self, places, here: str = "") -> str | None:
        here = here or self.ws.player.location
        if here not in self.world.places:
            return None
        best, dist = None, 10 ** 9
        for p in places:
            found = self.world.path(here, p.id) if p.id != here else ([], 0)
            if found and found[1] < dist:
                best, dist = p.id, found[1]
        return best

    def nearest_hall(self) -> str | None:
        return self.nearest([p for p in self.world.places.values() if p.type == "guild"])

    def unvisited(self) -> str | None:
        towns = [p for p in self.world.places.values() if not p.parent and p.type not in ("road", "dungeon") and p.id not in self.visited
                 and self.fits(p.id)]
        fits = [p for p in towns if self.route(p.id) is not None]
        return self.nearest(fits) if fits else None

    def doable_thread(self) -> dict | None:
        """A situation the player has met, still open, with a path left to take."""
        for th in self.state().get("threads", []):
            if th.get("status") != "active" or not th.get("touched") or th["id"] in self.given_up:
                continue
            if any(not p.get("done") and p["id"] not in self.given_up for p in th.get("paths") or []):
                return th
        return None

    def contract_to_take(self) -> dict | None:
        """(f366) A posting of the player's rank or below they do not already hold, when they hold fewer than two; None otherwise."""
        from engine import quests
        ws = self.ws
        if not ws.player.guild_rank or sum(1 for q in ws.player.quests if q.get("guild")) >= 2:
            return None
        try:
            board = ws.ensure_board()
        except Exception:
            return None
        held = {q.get("title") for q in ws.player.quests}
        fits = [q for q in board if quests.at_or_below(q["letter"], ws.player.guild_rank) and q["title"] not in held and q["kind"] in self.JOB_KINDS
                and (not q.get("place") or self.fits(q["place"]))]
        return self.rng.choice(fits) if fits else None

    # ---- nothing in particular: the small change of a day
    def parts_line(self) -> tuple[str, dict, str]:
        """(f394) Into the place: a part of it not walked yet, a part the last passage named, further in, or a search where they stand."""
        from engine import features
        ws, rng = self.ws, self.rng
        parts = [e for e in features.here(ws.store, ws.player.location) if e.state in ("known",) and e.ref != ws.player.spot]
        named = features.named_part(self.passage() or "")
        r = rng.random()
        if parts and r < 0.4:
            e = rng.choice(parts)
            return rng.choice([f"I go over to {e.name}.", f"I head for {e.name}.", f"Let's take a look at {e.name}."]), \
                self.intend("move", destination=e.ref), "move"
        if named and r < 0.55:
            return f"I go to {named[0]}.", self.intend("move", destination=named[0]), "move"
        if r < 0.85:
            return rng.choice(["I go further in.", "I push on, deeper in.", "I see what lies beyond.", "I explore further."]), \
                self.intend("explore", seek="further in"), "move"
        return rng.choice(["I search where I stand.", "I look closely around this spot.", "I search this place carefully."]), \
            self.intend("search"), "search"

    def idle(self, only: str = "") -> tuple[str, dict, str]:
        ws, rng, P = self.ws, self.rng, self.P
        p = self.place()
        in_town = p is None or p.danger is None
        present = [n for n in ws.present if n.id not in self.spoken_to]
        options: list[tuple[float, str]] = []
        if only == "talk" and present:
            options.append((1, "talk"))
        if present:
            options.append(((35 if in_town else 15) * P["chat"], "talk"))
        options.append((15 if in_town and self.here_for < 4 else 40, "move"))
        if p is not None and p.type == "guild":
            options.append((20 * P["job"], "board"))
        if p is not None and p.type in ("shop", "smithy", "workshop", "inn"):
            options.append((15 * P["trade"], "shop"))
        options += [(10 * P["improv"], "improv"), (8 if in_town else 20, "search"), (3, "wait")]
        from engine import features as _features
        if p is not None and _features.grows_here(p):
            options.append((18 * P.get("roam", 1), "parts"))      # (f394) a curious player goes into a place, not only through it
        from engine import clock as _clock
        today = _clock.day(ws.minutes)
        unasked = [m for m in ws.player.party if self.asked_hires.get(m.get("name")) != today]
        if unasked:
            options.append((8, "hire"))                 # a check-in at most once a game day per companion: a real player does not nag
        pick = "talk" if only == "talk" and present else rng.choices([o[1] for o in options], weights=[max(0.01, o[0]) for o in options])[0]
        self.label("idle:" + pick)
        if pick == "talk":
            n = rng.choice(present)
            self.spoken_to.append(n.id)
            self.talks = 1
            topic = rng.choice(self.TOPICS)
            asked = self.__dict__.setdefault("_asked_of", {}).setdefault(n.id, [])
            q = rng.choice([x for x in self.QUESTIONS if x not in asked] or self.QUESTIONS)
            asked.append(q)
            return f"I go over to {n.label()} and ask about {topic}.", self.intend("talk", target=n.id, speech=q), "talk"
        if pick == "move":
            return self.move_line(p)
        if pick == "parts":
            return self.parts_line()
        if pick == "board":
            take = self.contract_to_take()
            if take and rng.random() < 0.6:
                return f"I take the contract: {take['title']}.", self.intend("accept_quest", item=take["title"]), "board"
            text = rng.choice(["I read the contract board.", "I ask the clerk what contracts are open for my rank.", "I look over the board for a job I can take."])
            return text, self.intend("look"), "board"
        if pick == "shop":
            text = rng.choice(["I look over the wares.", "I ask what a good blade would cost me.", "I order a meal and listen to the talk."])
            return text, self.intend("look"), "shop"
        if pick == "improv":
            from engine import features as _f
            r = rng.random()
            pool = self.OUTLANDISH if r < 0.12 else self.WILD_IMPROV if (p is not None and _f.grows_here(p) and r < 0.6) else self.IMPROV
            text = rng.choice([t for t in pool if t != self.last_text] or pool)
            return text, self.intend("other", summary=text), "improv"
        if pick == "search":
            text = rng.choice(self.SEARCH)
            return text, self.intend("search" if "search" in text else "look"), "search"
        if pick == "hire":
            m = rng.choice(unasked)
            self.asked_hires[m.get("name")] = today
            return f"I ask {m.get('name', 'my companion')} how they're holding up.", self.intend("look"), "hire"
        return "I wait an hour.", self.intend("wait", wait_minutes=60), "wait"

    def move_line(self, p) -> tuple[str, dict, str]:
        rng, world = self.rng, self.world
        if p is None:
            return "I look around.", self.intend("look"), "look"
        here = p.id
        near = [x for x in world.neighbors(here) if x in world.places and self.fits(x)]
        local = [x for x in near if world.places[x].parent == here or x == p.parent or (p.parent and world.places[x].parent == p.parent)]
        roads = [x for x in near if x not in local and self.leg_ok(here, x)]
        fresh = lambda xs: [x for x in xs if x not in self.been] or xs
        if local and (not roads or rng.random() < 0.65):
            dest = rng.choice(fresh(local))
            text = rng.choice([f"I walk over to {world.places[dest].name}.", f"I head to {world.places[dest].name}."])
        elif roads:
            dest = rng.choice(fresh(roads))
            text = rng.choice([f"I set out for {world.places[dest].name}.", f"I take the road to {world.places[dest].name}."])
        else:
            return "I look around.", self.intend("look"), "look"
        return text, self.intend("move", destination=dest), "move"

    # ---- a fight: the same choices a player makes, said as a player says them
    def fight_line(self) -> tuple[str, dict, str]:
        choice = self.combat_choice()
        f = self.ws.combat.fight
        target = next((e for e in f.enemies() if e.id == choice.get("target")), None)
        name = target.name if target else "the nearest enemy"
        kind = choice["kind"]
        if kind == "item":
            return "I drink a healing draught.", {}, "fight"
        if kind == "flee":
            return "I run for it.", {}, "fight"
        if kind == "ability":
            move = next((m for m in f.player.moves if m.id == choice["ability"]), None)
            if move:
                return f"I use {move.name} on {name}.", {}, "fight"
        return self.rng.choice([f"I attack {name}.", f"I strike at {name}.", f"I go for {name}."]), {}, "fight"

    def combat_choice(self) -> dict:
        """The decision as a CombatIntent (the stand-in model answers with it; the words above are what the real one reads)."""
        from engine import combat
        f = self.ws.combat.fight
        p = f.player
        enemies = [e for e in f.enemies() if e.alive]
        if not enemies:
            return {"kind": "attack", "target": "", "summary": "bot"}
        tgt = min(enemies, key=lambda e: e.hp)
        hpf = p.hp / max(1, p.max_hp)
        base = {"target": tgt.id, "summary": "bot"}
        if hpf < 0.5 and f.item_round != f.round and any(i.good == "healing_draught" for i in self.c.inventory):
            return dict(base, kind="item", item="healing draught")           # one a round: the game refuses a second, and the bot once drank 1,155 times running
        if (hpf < 0.35 and f.round > 1) or (len(enemies) >= 3 and f.round == 1 and any(e.rank != "normal" for e in enemies)):
            return dict(base, kind="flee")
        usable = [m for m in p.moves if not combat.can_use(p, m, f)]
        if hpf < 0.5:
            for m in usable:
                if m.effect == "healing":
                    return dict(base, kind="ability", ability=m.id)
        if hpf < 0.6 and f.round > 1:
            for m in usable:
                if m.effect == "defense" and m.id not in p.buffs:
                    return dict(base, kind="ability", ability=m.id)
        damage = [m for m in usable if m.effect == "damage"]
        if damage and self.rng.random() < 0.7:
            return dict(base, kind="ability", ability=self.rng.choice(damage).id, move="closer")
        return dict(base, kind="attack", move="closer")

    # ---- the words: the model writes the line from the persona, the goal and what the game just said
    def goal_sentence(self, text: str, intent: dict, kind: str) -> tuple[str, list[str]]:
        """What the line is for, in plain words, and the names it must carry so the game reads it as meant."""
        ws, world = self.ws, self.world
        k = intent.get("kind", kind)
        label = lambda nid: next((n.label() for n in ws.present if n.id == nid), "")
        if k == "move":
            dest = world.places.get(intent.get("destination", ""))
            name = dest.name if dest else intent.get("destination", "")
            return f"go to {name}", [name]
        if k == "talk":
            who = label(intent.get("target", "")) or (ws.partner.label() if ws.partner else "them")
            if ws.partner is not None and intent.get("checks"):
                return f"you are talking with {who}; persuade them: {intent.get('speech', '')}", []
            if ws.partner is not None:
                return f"you are talking with {who}; say your next line: answer or follow up on what they just said, or ask what you want to know ({intent.get('speech', '')})", []
            must = [who.split()[-1]] if who and who.lower().startswith("the ") else ([who.split()[0]] if who else [])
            return f"go over to {who} and start talking: {intent.get('speech', '')}", must
        if k == "leave_conversation":
            return "end the conversation and take your leave", []
        if k == "accept_quest":
            return f"tell the clerk you take the contract '{intent.get('item', '')}' from the board", [w for w in re.findall(r"[A-Za-z]{4,}", intent.get("item", ""))[:2]]
        if k == "search":
            seek = intent.get("seek", "")
            return (f"search this place for {seek}" if seek else "search this place"), ([seek] if seek else [])
        if k == "attack":
            name = text.replace("I attack the ", "").rstrip(".")
            return f"attack the {name}", [name.split()[0]]
        if k == "wait":
            return ("sleep until morning" if intent.get("wait_until") else "wait a while"), []
        if k == "use":
            return f"use a {intent.get('item', '')}", [intent.get("item", "").split()[-1]] if intent.get("item") else []
        if k == "buy":
            who = label(intent.get("target", ""))
            ware = intent.get("ware", "")
            return f"buy {ware}" + (f" from {who}" if who else ""), [ware.split()[-1]] if ware else []
        if k == "sell":
            who = label(intent.get("target", ""))
            return f"sell your {intent.get('item', '')}" + (f" to {who}" if who else ""), [intent.get("item", "").split()[-1]] if intent.get("item") else []
        if k == "equip":
            return f"put on or wield your {intent.get('item', '')}", [intent.get("item", "").split()[-1]] if intent.get("item") else []
        if k == "forage":
            return f"forage here for {intent.get('item', 'herbs')}", [intent.get("item", "").split()[-1]] if intent.get("item") else []
        if k == "delve":
            return "go down into the dungeon here", ["down"]
        if k == "leave_dungeon":
            return "climb back out of the dungeon", ["out"]
        if k == "other":
            return f"do something of your own here, for instance: {text}", []
        if k == "look":
            return f"something small and in character, like: {text}", []
        return text, []

    def model_line(self, text: str, intent: dict, kind: str, passage: str) -> str:
        from engine.prompt import Prompt
        from llm.contracts import PlayerLine
        from llm.gateway import generate
        c = self.c
        goal, must = self.goal_sentence(text, intent, kind)
        must = [m for m in must if m]
        system = (f"You are playing a text role-playing game as {c.name}, level {c.level}. You are {self.P['text']}. "
                  "Write the one line you type next, the way a real player types: first person, present tense, one or two short sentences in plain "
                  "words. Say what you do, or what you say, and nothing more: never describe what happens next, never quote the game's words back "
                  "to it, never address the game. When you speak to someone, pick up on something they or the game just said when you can.")
        p = Prompt()
        party = ", ".join(m.get("name", "") for m in self.ws.player.party)
        here = ", ".join(n.label() for n in self.ws.present[:8]) or "nobody"
        p.fact(f"Where you are: {self.where()}. Here: {here}. With you: {party or 'nobody'}. Your health: {int(self.hp() * 100)}%.", "SCENE")
        if passage:
            p.history(passage[-1400:], "THE GAME JUST SAID")
        if self.recent:
            p.history("\n".join(self.recent), "LINES YOU TYPED LATELY (say it differently)")
        p.instruction(f"What you mean to do now: {goal}." + (f" Your line must name {', '.join(must)}." if must else ""), "NOW")
        t0 = time.perf_counter()
        try:
            out = generate("player_line", system, p, PlayerLine, temperature=0.9, retries=1, validation_context={"must_name": must},
                           max_tokens=90, _quiet=True)
            line = out.line.strip()
        except Exception:
            line = ""
        self.stats["model_seconds"] += time.perf_counter() - t0
        if not line:
            self.stats["model_failed"] += 1
        return line

    def report(self) -> dict:
        s = dict(self.stats)
        s["goals_done"] = dict(self.stats["goals_done"])
        s["goals_dropped"] = dict(self.stats["goals_dropped"])
        s["places"] = len(self.visited)
        return s
