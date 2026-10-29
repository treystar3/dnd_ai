"""Prisoners, interrogation and arcs in play.

The engine decides what is true: who yields, what each person knows, whether they will say it, which step comes next, how
the story ends. The model voices people and describes scenes. It can never add a step to an arc."""

import random
import re

from engine import arcs, checks, clock, field, leveling, money, pulse, quests
from engine.arcs import A
from engine.arc_prompts import SYSTEM, user
from llm.contracts import ArcStory
from llm.gateway import LLMError, generate
from npc.life import _unique_id
from npc.models import NPC
from npc.traits import assign_traits, npc_rng
from ui import console

PR = A["prisoner"]


class ArcActions:

    # ---------- the story's state ----------

    def arc_data(self) -> dict:
        return self.store.load_arcs()

    def my_arc(self, data: dict | None = None):
        data = data or self.arc_data()
        return data, arcs.active(data)

    def story_node(self, arc: dict, nid: str) -> dict:
        return next((n for n in (arc["story"] or {}).get("nodes", []) if n["id"] == nid), {})

    def pname(self, nid: str) -> str:
        return self.world.places[nid].name if nid in self.world.places else nid

    # ---------- starting: the engine decides what this contract really is ----------

    def start_arc(self, q: dict) -> None:
        data = self.arc_data()
        c = self.player.character
        hall = q.get("hall") or self.guild_place_id()
        tier = quests.hall_tier(self.world, hall)["tier"]
        size, why = arcs.roll_scale(self.world, data, q["id"], self.store.meta.seed, c.level, self.rank, hall, self.minutes, tier)
        arc = arcs.build(self.world, self.store, q, hall, c.level, size, why, self.minutes, self.store.meta.seed)
        console.debug(f"arc: {len(arc['nodes'])} steps, {size} - {why}")
        arc["story"] = self.dress_arc(arc, q)
        data["arcs"].append(arc)
        self.store.save_arcs(data)
        s = arc["story"]
        q["arc"] = arc["id"]
        q["title"] = s["hook_title"]
        q["multiplier"] = A["contract_mult"][size]
        q["rank_credit"] = A["rank_credit"][size]
        q["deadline"] = None
        first = arcs.node(arc, "n1")
        tpl = arcs.TEMPLATES[arc["template"]]
        self.log_arc(arc, tpl["words"]["start"].format(name=s["victim_name"], looks=s["victim_looks"].rstrip("."),
                                                       place=self.pname(first["place"])))
        self.store.save_arcs(data)
        console.note(f"Lead: {arc['log'][-1]}")

    def dress_arc(self, arc: dict, q: dict) -> dict:
        """The one model call: names, clues and colour for a skeleton the engine already fixed."""
        nodes = []
        ns = arc["nodes"]
        for i, n in enumerate(ns):
            nodes.append({"id": n["id"], "kind": n["kind"], "role": n.get("role", ""), "people": n["people"],
                          "place_name": self.pname(n["place"]),
                          "next": self.pname(ns[i + 1]["place"]) if i + 1 < len(ns) else ""})
        taken = self.store.npc_names()
        tpl = arcs.TEMPLATES[arc["template"]]
        try:
            story = generate("arc_story", SYSTEM, user(tpl["truth"], arc["size"], arc["victim_phrase"], nodes, taken, tpl),
                             ArcStory, temperature=0.9, max_tokens=1800,
                             validation_context={"nodes": [n["id"] for n in ns], "taken": taken,
                                                 "named": [n["id"] for n in ns if n["kind"] != "site"]})
            out = story.model_dump()
        except LLMError as e:
            console.debug(f"arc story: model failed ({e}); using plain wording")
            out = self.plain_story(arc, nodes)
        out["nodes"] = [{**n} for n in out["nodes"]]
        return out

    def plain_story(self, arc: dict, nodes: list[dict]) -> dict:
        rng = random.Random(arc["id"])
        pool = [x for x in PR["names"] if x not in self.store.npc_names()]
        rng.shuffle(pool)
        tpl = arcs.TEMPLATES[arc["template"]]
        victim = arc["victim_phrase"]
        out = []
        for i, n in enumerate(nodes):
            clue = f"The trail leads on to {n['next']}." if n["next"] else "This is where it ends, and it was all for coin."
            name = "" if n["kind"] == "site" else (pool[i] if i < len(pool) else f"{pool[i % len(pool)]} {i + 1}")
            out.append({"id": n["id"], "title": f"Step {i + 1}", "clue": clue, "npc_name": name,
                        "npc_looks": "" if n["kind"] == "site" else "A weathered figure.",
                        "npc_manner": "" if n["kind"] == "site" else "Guarded and short."})
        person = tpl["subject_kind"] == "person"
        return {"hook_title": f"Find {victim}" if person else victim[:1].upper() + victim[1:],
                "title": "A Hidden Trade", "victim_name": "the missing one" if person else victim,
                "victim_looks": "a person who should be home" if person else "the heart of the matter",
                "premise": tpl["truth"].strip().split(". ")[0].rstrip(".") + ".", "nodes": out}

    def log_arc(self, arc: dict, text: str) -> None:
        arc["log"].append(text)

    # ---------- arriving: contacts are there, camps fight ----------

    def arc_enter(self, place_id: str) -> None:
        data, arc = self.my_arc()
        if not arc:
            return
        n = arcs.current(arc)
        if not n or n["place"] != place_id or n["kind"] != "contact":
            return
        if not n.get("npc") or not self.store.npc_exists(n["npc"]):
            self.spawn_cast(arc, n)
            self.store.save_arcs(data)
        elif n["status"] == "known":
            pass
        if n["status"] == "known":
            n["status"] = "active"
            self.store.save_arcs(data)
        self.refresh_present()

    def spawn_cast(self, arc: dict, n: dict) -> NPC:
        sn = self.story_node(arc, n["id"])
        name = sn.get("npc_name") or "a stranger"
        npc = NPC(id=_unique_id(self.store, name), name=name, people=n["people"], role=n["role"], location=n["place"],
                  epithet=f"the {n['role'].replace('_', ' ')}", description=sn.get("npc_looks", ""),
                  activity="going about their work, a little too watchfully", protected=True,
                  personality=sn.get("npc_manner", ""), knowledge_groups=list(self.world.roles[n["role"]].knowledge_groups) + ["outlaws"])
        assign_traits(npc, self.catalog, npc_rng(self.store.meta.seed, npc.id))
        self.store.save_npc(npc)
        ps = self.store.load_place(n["place"])
        ps.residents.append(npc.id)
        self.store.save_place(ps)
        n["npc"] = npc.id
        if n["place"] == self.player.location:
            self.residents = self.residents + [npc]
        return npc

    def arc_arrival(self) -> bool:
        """Called after arriving somewhere. A hideout fights, a site is searched, a finale is faced."""
        if self.combat:
            return False
        data, arc = self.my_arc()
        n = arcs.current(arc) if arc else None
        if not n or n["kind"] not in ("lair", "boss", "site") or n["place"] != self.player.location:
            return False
        tpl = arcs.TEMPLATES[arc["template"]]
        n["status"] = "active"
        self.store.save_arcs(data)
        if n["kind"] == "site":
            if arcs.site_body(self.store.meta.seed, arc, n):
                if self.question_site_body(data, arc, n, tpl):
                    return False
                if not n.get("body_seen"):
                    n["body_seen"] = True
                    self.store.save_arcs(data)
                    console.note("A body lies here, and it has something to tell - if only you could make it speak.")
            self.work_site(data, arc, n, tpl)
            return False
        if n["kind"] == "boss" and tpl["finale"] == "confront":
            if self.confront(data, arc, n, tpl):
                return False
            n["camp"] = n.get("camp") or self.camp_build(arc, n, tpl)       # the confrontation failed: it comes to blades
            return self.camp_battle(data, arc, n, tpl)
        return self.camp_enter(data, arc, n, tpl)

    def best_of(self, names: list[str], extra=()) -> tuple[str, float]:
        c = self.player.character
        scored = [(k, checks.chance(c, k, self.conditions(), extra=list(extra))[0]) for k in names]
        return max(scored, key=lambda x: x[1])

    def question_site_body(self, data: dict, arc: dict, n: dict, tpl: dict) -> bool:
        """A body at a site, and a character who can Speak with a Corpse: the dead give up the clue, no search needed."""
        ab = self.pay_field_ability("speak_corpse")
        if not ab:
            return False
        sn = self.story_node(arc, n["id"])
        place = self.pname(n["place"])
        self.field_cooldown_start(ab)
        self.advance(field.F["speak_corpse"]["minutes"])
        n["clue_given"] = True
        self.narrate(f"The player finds a body at {place} ({tpl['site_desc']}) and uses {ab.name} to question it. Describe the dead giving "
                     f"up what they knew, adding nothing beyond this: {sn.get('clue', '')}", "")
        console.note(f"{ab.name}: the dead tell you what the place was hiding.")
        self.advance_arc(data, arc, n, False, self.secret_text({"kind": "arc", "node": n["id"], "arc": arc["id"], "victim": ""}))
        return True

    def work_site(self, data: dict, arc: dict, n: dict, tpl: dict) -> None:
        """Search a place with the best fitting skill. Failures cost hours; three and the thread turns up another way, at a cost of days."""
        c = self.player.character
        sn = self.story_node(arc, n["id"])
        rng = random.Random(f"{self.store.meta.seed}:site:{arc['id']}:{n['id']}")
        skill, odds = self.best_of(n.get("check") or tpl["site_checks"])
        place = self.pname(n["place"])
        while True:
            degree, _ = checks.roll(odds, rng, c=c)
            n["attempts"] += 1
            console.debug(f"arc site {n['id']}: {skill} {odds:.0f}% -> {degree} (try {n['attempts']})")
            if degree in ("success", "strong success"):
                n["clue_given"] = True
                self.narrate(f"The player searches at {place} ({tpl['site_desc']}), relying on {skill}, and finds something. "
                             f"Describe the search and what turns up: {sn.get('clue', '')}", "")
                console.note(f"{skill.capitalize()} - {degree}: you find what the place was hiding.")
                self.advance_arc(data, arc, n, False, self.secret_text({"kind": "arc", "node": n["id"], "arc": arc["id"], "victim": ""}))
                return
            self.advance(A["site"]["hours_per_try"] * 60)
            if n["attempts"] >= A["max_attempts"]:
                console.note(f"You search {place} for hours and the place keeps its secret. You find the thread another way, at a cost of time.")
                n["clue_given"] = True
                self.advance_arc(data, arc, n, True, self.secret_text({"kind": "arc", "node": n["id"], "arc": arc["id"], "victim": ""}))
                return
            console.note(f"{skill.capitalize()} - {degree}: nothing yet. You keep looking.")

    def confront(self, data: dict, arc: dict, n: dict, tpl: dict) -> bool:
        """The finale as a reckoning: evidence and a skill. True if it is settled without a fight."""
        C = A["confront"]
        proper = sum(1 for x in arc["nodes"] if x["status"] == "done" and not x["partial"])
        evidence = min(C["evidence_cap"], proper * C["evidence_per_step"])
        skill, odds = self.best_of(tpl["confront_checks"], [("evidence", evidence)])
        rng = random.Random(f"{self.store.meta.seed}:confront:{arc['id']}")
        degree, _ = checks.roll(odds, rng, c=self.player.character)
        sn = self.story_node(arc, n["id"])
        who = sn.get("npc_name") or "the one behind it"
        console.debug(f"arc confront: {skill} {odds:.0f}% (evidence +{evidence}) -> {degree}")
        if degree not in ("success", "strong success"):
            console.note(f"You lay out what you know, but {who} does not break. It comes to blades. ({skill.capitalize()} - {degree})")
            self.narrate(f"The player confronts {who} ({sn.get('npc_looks', '')}) with what they have learned, but it is not enough. "
                         "Describe the confrontation failing and the moment steel is drawn.", "")
            return False
        console.note(f"{skill.capitalize()} - {degree}: your proof is too strong. {who} gives way.")
        self.finish_arc(data, arc, None, yielded=True)
        return True

    # ---------- after a fight with outlaws ----------

    def camp_fight_over(self, outcome: str, dead: list) -> None:
        info = getattr(self, "camp_fight", None)
        self.camp_fight = None
        c = self.player.character
        outlaws = [e for e in dead if e.category in A["people_categories"]]
        if outcome != "victory":
            return
        if info:
            data, arc = self.my_arc()
            if arc and arc["id"] == info["arc"]:
                n = arcs.node(arc, info["node"])
                leader = next((e for e in dead if e.name == info["leader"]), None)
                sn = self.story_node(arc, n["id"])
                if n["kind"] == "boss":
                    self.finish_arc(data, arc, leader if info.get("people", True) else None)
                    return
                if info.get("people", True):
                    self.standing_report("camp_cleared", None, self.pname(n["place"]))
                    self.make_prisoner(sn.get("npc_name") or info["leader"], sn.get("npc_looks", ""), arc=arc["id"], node=n["id"], named=True)
                    n["status"] = "active"
                    self.store.save_arcs(data)
                else:
                    console.note("Among what is left, you find what you came for.")
                    n["clue_given"] = True
                    self.advance_arc(data, arc, n, False, self.secret_text({"kind": "arc", "node": n["id"], "arc": arc["id"], "victim": ""}))
            return
        if not outlaws or getattr(self, "surrender_took", False):
            self.surrender_took = False
            return
        chance = max(PR["min_chance"], min(PR["max_chance"], PR["chance"] + self.player.outlaw_rep * PR["rep_chance_per_point"]))
        rng = random.Random(f"{self.store.meta.seed}:yield:{self.minutes}")
        if rng.random() < chance and self.place.type not in ("dungeon", "road"):
            who = max(outlaws, key=lambda e: e.level)
            tip = rng.random() < PR["tip_chance"]
            self.make_prisoner(rng.choice(PR["names"]), "", tip=tip, named=False, kind=who.name)

    def make_prisoner(self, name: str, looks: str, arc: str = "", node: str = "", tip: bool = False, named: bool = False,
                      kind: str = "outlaw") -> NPC:
        peoples = self.world.peoples_at(self.player.location) or {"human": 100}
        epithet = "the captured leader" if named else "the captured " + re.sub(r" ?\d+$", "", kind)
        npc = NPC(id=_unique_id(self.store, f"prisoner {name}"), name=name, people=max(peoples, key=peoples.get), role="prisoner",
                  location=self.player.location, epithet=epithet,
                  description=looks or "Bound, bloodied and watching you.", activity="sitting bound where you left them",
                  protected=True, name_known_to_player=named,
                  trust=max(0, min(100, PR["trust_start"] + self.player.outlaw_rep // 5)))
        assign_traits(npc, self.catalog, npc_rng(self.store.meta.seed, npc.id))
        self.store.save_npc(npc)
        ps = self.store.load_place(self.player.location)
        ps.residents.append(npc.id)
        self.store.save_place(ps)
        self.player.prisoners[npc.id] = {"deal": False, "arc": arc, "node": node, "tip": tip, "asked": 0, "day": clock.day(self.minutes)}
        self.store.save_player(self.player)
        self.residents = self.residents + [npc]
        self.refresh_present()
        console.note(f"{npc.label().capitalize()} throws down their weapon and yields. Question them, let them go, or put an end to it.")
        return npc

    def prisoner_here(self, intent=None) -> NPC | None:
        mine = [n for n in self.present if n.id in self.player.prisoners]
        if not mine:
            return None
        if intent is not None:
            hit = next((n for n in mine if n.id == getattr(intent, "target", "")), None)
            if hit:
                return hit
        return mine[0]

    # ---------- the secret a person holds, and whether they give it up ----------

    def secret_for(self, npc) -> dict | None:
        """What this person knows that the player wants, if anything: {"clue", "arc", "node", "kind"}."""
        data, arc = self.my_arc()
        if arc:
            n = arcs.current(arc)
            if n and not n["clue_given"]:
                pr = self.player.prisoners.get(npc.id)
                if (n["kind"] == "contact" and n.get("npc") == npc.id) or (pr and pr.get("node") == n["id"]):
                    return {"kind": "arc", "arc": arc["id"], "node": n["id"], "victim": arc["story"]["victim_name"]}
        pr = self.player.prisoners.get(npc.id)
        if pr and pr["tip"] and not pr.get("tip_given"):
            return {"kind": "tip"}
        return None

    def secret_lines(self, npc, speech: str) -> tuple[list[str], dict | None]:
        secret = self.secret_for(npc)
        pr = self.player.prisoners.get(npc.id)
        lines = []
        if pr:
            lines.append("You are the stranger's prisoner: you lost a fight and they took you alive. " +
                         ("They promised to spare you if you talk. " if pr["deal"] else "") +
                         "Behave as your nature would - defiant, bargaining, frightened or sly.")
            if any(w in speech.lower() for w in PR["deal_words"]):
                pr["deal"] = True
                lines.append("They have just promised to spare you.")
        if not secret:
            return lines, None
        ls = getattr(self, "last_social", None)
        degree = ls[1] if ls and ls[2] == npc.id and ls[0] in PR["gate_checks"] else None
        pressed = bool(ls and ls[2] == npc.id)
        gate = PR["gate_trust"]
        rep_open = False
        if secret["kind"] == "arc":
            data, arc = self.my_arc()
            if arc and arcs.TEMPLATES[arc["template"]]["rep_matters"] and not pr:
                M = A["rep_matters"]
                rep_open = self.player.outlaw_rep >= M["open_at"]
                if self.player.outlaw_rep <= M["shut_at"]:
                    gate += M["shut_extra_trust"]
        open_ = (pr and pr["deal"]) or degree in ("success", "strong success") or npc.trust >= gate or rep_open
        what = f"what this is about and who is behind it" if secret["kind"] == "arc" else "something worth knowing about the roads"
        if open_:
            clue = self.secret_text(secret)
            lines.append(f"[THE GAME HAS DECIDED: they have won you over. You tell them what you know now, in your own manner "
                         f"and words: {clue} Say all of it; add no other facts.]")
        elif degree == "partial":
            lines.append(f"[THE GAME HAS DECIDED: you are shaken. You almost say too much - let slip that you DO know {what}, "
                         "and nothing more. Do not say it.]")
        else:
            lines.append(f"[YOU KNOW {what}. You will not tell the stranger unless they persuade you, frighten you, or win your "
                         "trust. You may stall, bargain, bluff about small things, or refuse. Do not reveal or hint at what it is.]")
        return lines, {"open": bool(open_), "pressed": pressed, "secret": secret}

    def secret_text(self, secret: dict) -> str:
        if secret["kind"] == "tip":
            return "a way through the hills the locals do not know, or a place outlaws gather - one short, true sentence."
        data, arc = self.my_arc()
        n = arcs.node(arc, secret["node"])
        sn = self.story_node(arc, n["id"])
        nxt = arcs.node(arc, n["reveals"]) if n["reveals"] else None
        return sn.get("clue", "") + (f" (The next place is {self.pname(nxt['place'])}.)" if nxt else "")

    def secret_after(self, npc, pending: dict | None) -> None:
        self.last_social = None
        if not pending:
            return
        secret = pending["secret"]
        if pending["open"]:
            self.give_secret(npc, secret)
        elif pending["pressed"] and secret["kind"] == "arc":
            data, arc = self.my_arc()
            n = arcs.node(arc, secret["node"])
            n["attempts"] += 1
            if n["attempts"] >= A["max_attempts"]:
                self.trail_goes_cold(data, arc, n, npc)
            else:
                self.store.save_arcs(data)

    def give_secret(self, npc, secret: dict) -> None:
        if secret["kind"] == "tip":
            from engine import discovery
            data = self.store.load_discoveries()
            near = pulse.town_of(self.world, self.player.location)
            spot = next((p for p in self.world.neighbors(near) if p in self.world.places and self.world.places[p].danger), None) or self.player.location
            if discovery.add_lead(data, spot, "A way off the road the outlaws use, known to a captive.", self.minutes, random.Random(npc.id)):
                self.store.save_discoveries(data)
                console.note("You learn of a hidden way near here. (A lead - try exploring.)")
            self.player.prisoners[npc.id]["tip_given"] = True
            self.store.save_player(self.player)
            return
        data, arc = self.my_arc()
        n = arcs.node(arc, secret["node"])
        n["clue_given"] = True
        text = self.secret_text(secret)
        self.advance_arc(data, arc, n, False, text)
        self.store.save_player(self.player)

    def trail_goes_cold(self, data: dict, arc: dict, n: dict, npc) -> None:
        """They will not talk. The trail turns up another way - slower."""
        console.note(f"{npc.label().capitalize()} will say no more. You find the thread another way, at a cost of time.")
        n["clue_given"] = True
        text = self.secret_text({"kind": "arc", "node": n["id"], "arc": arc["id"], "victim": ""})
        self.advance_arc(data, arc, n, True, text)

    # ---------- moving the story along ----------

    def advance_arc(self, data: dict, arc: dict, n: dict, partial: bool, clue: str) -> None:
        was_revealed = arc["revealed"]
        nxt = arcs.complete_node(arc, n["id"], partial)
        if partial:
            self.advance_quiet(A["partial_cost_days"] * 1440)      # a half-answer costs days of legwork, not a deadline
        coins, xp = arcs.node_pay(self.rank or "F")
        c = self.player.character
        c.coins += coins
        levels = leveling.gain_xp(c, xp)
        line = clue + (f" Lead: {self.pname(nxt['place'])}." if nxt else "")
        self.log_arc(arc, line)
        console.note(f"You learn: {clue}")
        if nxt:
            console.note(f"Lead: {self.pname(nxt['place'])}.  (+{money.fmt(coins)}, +{xp} XP)")
        if levels:
            console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
        if arc["revealed"] and not was_revealed:
            self.reveal_arc(arc)
        self.store.save_arcs(data)

    def reveal_arc(self, arc: dict) -> None:
        s = arc["story"]
        for q in self.player.quests:
            if q.get("arc") == arc["id"]:
                q["title"] = f"{s['title']}"
        total = len(arc["nodes"])
        console.note(f"This is bigger than it looked. The trail now has a name: {s['title']} - {total} steps to its end.")
        state = self.store.load_world_state() or pulse.empty_state(self.minutes)
        towns = sorted({n["place"] for n in arc["nodes"] if n["kind"] == "contact"})
        self.arc_effects(arc, state, towns, failure=False)
        if towns:
            pulse.add_news(state, f"Word along the roads of trouble that has a name now: {s['title']}.", towns[0], self.minutes, ["everyone"])
        self.store.save_world_state(state)
        self.weight_hint = "rich"

    def arc_effects(self, arc: dict, state: dict, towns: list[str], failure: bool) -> None:
        """What the story does to the world: danger on the roads of its towns, or dearer goods in them, or nothing."""
        e = arcs.TEMPLATES[arc["template"]]["effect"]
        kind = e["kind"]
        if kind == "none" and not failure:
            return
        until = self.minutes + A["failure_days"] * 1440 if failure else self.minutes + A["effect_days"][arc["size"]] * 1440
        cause = f"{arc['story']['title']} ({arc['id']})" + (" grown bold" if failure else "") + " " + " ".join(arcs.TEMPLATES[arc["template"]].get("tags", []))
        if kind in ("danger", "none"):
            value = A["failure_danger"] if failure else round(e["value"] * A["effect_scale"].get(arc["size"], 0))
            if kind == "none" or not value:
                return
            for r in self.world.roads.values():
                if r.from_ in towns or r.to in towns:
                    state["effects"].append({"kind": "danger", "place": self.road_key(r), "value": value, "until": until,
                                             "cause": cause, "arc": arc["id"]})
        elif kind == "prices":
            value = A["effects"]["failure_prices"] if failure else round(e["value"] * A["effect_scale"].get(arc["size"], 0))
            if not value:
                return
            for t in towns:
                state["effects"].append({"kind": "prices", "place": t, "value": value, "until": until, "cause": cause, "arc": arc["id"]})

    def road_key(self, r) -> str:
        from engine import roads
        return roads.edge_key(self.world, r.from_, r.to)

    def finish_arc(self, data: dict, arc: dict, leader, yielded: bool = False) -> None:
        """The one behind it falls or gives way. The story is over."""
        s = arc["story"]
        tpl = arcs.TEMPLATES[arc["template"]]
        W = tpl["words"]
        last = arcs.node(arc, arc["nodes"][-1]["id"])
        last["status"] = "done"
        for n in arc["nodes"]:
            if n["status"] != "done":
                n["status"] = "done"
        coins, xp = arcs.reward(arc, next((q["letter"] for q in self.player.quests if q.get("arc") == arc["id"]), "F"))
        c = self.player.character
        c.coins += coins
        levels = leveling.gain_xp(c, xp)
        for q in self.player.quests:
            if q.get("arc") == arc["id"]:
                q["progress"] = 1
        arcs.finish(data, arc, "done", self.minutes)
        self.log_arc(arc, W["end"].format(name=s["victim_name"], premise=s["premise"]))
        state = self.store.load_world_state() or pulse.empty_state(self.minutes)
        for e in state["effects"]:
            if e.get("arc") == arc["id"]:
                e["until"] = self.minutes
        title = s["title"] if arc["revealed"] else s["hook_title"]
        pulse.add_news(state, W["news"].format(title=title, name=s["victim_name"]), self.player.location, self.minutes, ["everyone"])
        self.store.save_world_state(state)
        self.store.save_arcs(data)
        town = pulse.town_of(self.world, arc["hall"])
        self.reputation_add(town, 5 if arc["size"] != "simple" else 2)
        self.standing_report("arc_won", None, title)
        self.weight_hint = "major"
        console.note(f"{W['over'].format(name=s['victim_name'][:1].upper() + s['victim_name'][1:])} {title} is over. "
                     f"+{money.fmt(coins)}, +{xp} XP - hand in the contract at the guild.")
        if levels:
            console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
        gift = arcs.gift_companion(c, arc, self.world)
        if gift:
            c.companions.append(gift)
            console.note(f"{gift.description[:-1]} - it is yours now. It will fight at your side, though it is no bonded companion.")
            console.note(f"  {gift.name}: {arcs.perk_text(gift)}")
            self.narrate(f"As the story ends, an animal attaches itself to the player for good: {gift.description} "
                         "Describe the moment it chooses them.", "")
        sn = self.story_node(arc, last["id"])
        who = sn.get("npc_name") or "the leader"
        people = leader is not None or (yielded and tpl["leaders"] and
                                         self.world.bestiary[arcs.pick_creature(self.world, tpl["leaders"], c.level)].category in A["people_categories"])
        if people:
            self.make_prisoner(who, sn.get("npc_looks", ""), arc=arc["id"], node="", named=True)
        key = "yield_win" if yielded else "win"
        self.narrate(W[key].format(leader=who, name=s["victim_name"], looks=s["victim_looks"], premise=s["premise"]), "")
        self.party_disband(arc["id"], "the job is done")

    def fail_arc(self, arc: dict, why: str) -> None:
        data = self.arc_data()
        a = next((x for x in data["arcs"] if x["id"] == arc["id"]), None)
        if not a or a["state"] != "active":
            return
        arcs.finish(data, a, "failed", self.minutes)
        state = self.store.load_world_state() or pulse.empty_state(self.minutes)
        for e in state["effects"]:
            if e.get("arc") == a["id"]:
                e["until"] = self.minutes
        s = a["story"]
        if a["size"] != "simple":
            towns = sorted({n["place"] for n in a["nodes"] if n["kind"] == "contact"})
            self.arc_effects(a, state, towns, failure=True)
            pulse.add_news(state, f"{s['title'] if a['revealed'] else s['hook_title']} was never settled; things are worse for it.",
                           towns[0] if towns else "parth", self.minutes, ["everyone"])
        self.store.save_world_state(state)
        self.store.save_arcs(data)
        console.note(f"{s['title'] if a['revealed'] else s['hook_title']}: {why}. The trail is cold.")
        self.party_disband(a["id"], "the trail went cold")

    def arc_quest_gone(self, q: dict, why: str) -> None:
        if q.get("arc"):
            data = self.arc_data()
            a = next((x for x in data["arcs"] if x["id"] == q["arc"]), None)
            if a:
                self.fail_arc(a, why)

    def arc_tick(self) -> None:
        """Prisoners left behind don't wait forever."""
        if not self.player.prisoners:
            return
        today = clock.day(self.minutes)
        for nid, pr in list(self.player.prisoners.items()):
            if not self.store.npc_exists(nid):
                self.player.prisoners.pop(nid, None)
                continue
            if pr.get("escort"):
                continue
            npc = self.store.load_npc(nid)
            if npc.location == self.player.location or today - pr["day"] < 2:
                continue
            self.drop_prisoner(npc, "slipped their bonds in the night", partial_node=True)

    def bring_prisoners(self, place_id: str) -> None:
        """Bound prisoners you are escorting come with you to the next place."""
        for nid, pr in list(self.player.prisoners.items()):
            if not pr.get("escort") or not self.store.npc_exists(nid):
                continue
            npc = self.store.load_npc(nid)
            if npc.location == place_id:
                continue
            old = self.store.load_place(npc.location)
            if nid in old.residents:
                old.residents.remove(nid)
                self.store.save_place(old)
            npc.location = place_id
            npc.activity = "walking bound at your side"
            self.store.save_npc(npc)
            new = self.store.load_place(place_id)
            if nid not in new.residents:
                new.residents.append(nid)
                self.store.save_place(new)
            if all(r.id != nid for r in self.residents):
                self.residents = self.residents + [npc]
        self.refresh_present()

    def on_hand_over(self, intent, text: str) -> None:
        """Hand a prisoner to the watch: a guard has to be here. Pays by the prisoner's level; a posted bounty on that kind of creature counts."""
        from engine import law
        npc = self.prisoner_here(intent)
        if not npc:
            console.note("There is no prisoner here to hand over.")
            self.halted = True
            return
        guard = next((n for n in self.present if n.role in law.L["heat"]["guard_roles"] and n.id not in self.player.prisoners), None)
        if not guard:
            console.note("There is no one from the watch here to hand them to. Find a guard or a watch captain.")
            self.halted = True
            return
        pr = self.player.prisoners.get(npc.id, {})
        coins = max(1, pr.get("level", 1)) * PR["turn_in"]["coin_per_level"]
        bounty = next((q for q in self.player.quests if q["kind"] in ("hunt", "bounty") and q.get("creature") == pr.get("creature")
                       and q["progress"] < q["count"]), None) if pr.get("creature") else None
        if bounty:
            bounty["progress"] += 1
        self.player.character.coins += coins
        node_pending = pr.get("node")
        self.end_conversation()
        self.drop_prisoner(npc, "handed over to the watch", partial_node=bool(node_pending))
        self.standing_report("prisoner_handed_over", [guard], npc.label())
        console.note(f"{guard.label().capitalize()} takes {npc.label()} into custody. Paid: {money.fmt(coins)}"
                     + (" - and it counts toward your bounty." if bounty else "."))
        self.weight_hint = "brief"
        self.narrate(f"The player hands the bound captive {npc.name} over to {guard.name}, {guard.label()}. "
                     "Describe the handover.", text)
        self.store.save_player(self.player)

    def drop_prisoner(self, npc, how: str, partial_node: bool = False) -> None:
        pr = self.player.prisoners.pop(npc.id, None)
        self.store.save_player(self.player)
        pulse.remove_npc(self.store, self.world, npc, how, self.minutes)
        self.player = self.store.load_player()
        self.residents = [n for n in self.residents if n.id != npc.id]
        self.refresh_present()
        if pr and partial_node and pr.get("node"):
            data, arc = self.my_arc()
            n = arcs.node(arc, pr["node"]) if arc else None
            if n and n["status"] != "done" and not n["clue_given"]:
                n["clue_given"] = True
                self.advance_arc(data, arc, n, True, self.secret_text({"kind": "arc", "node": n["id"], "arc": arc["id"], "victim": ""}))

    # ---------- what you do with a prisoner ----------

    def on_release(self, intent, text: str) -> None:
        npc = self.prisoner_here(intent)
        if not npc:
            from engine import taming
            freed = taming.release(self.player.character, f"{intent.target} {intent.item} {text}")
            if freed:
                self.store.save_player(self.player)
                console.note(f"You release {freed.name} back to the wild.")
                self.narrate(f"The player lets their tamed companion {freed.name} go back to the wild. Describe the parting.", text)
                return
            console.note("There's no one here to let go.")
            self.halted = True
            return
        self.settle_prisoner(npc, "release", text)

    def execute_prisoner(self, npc, text: str) -> None:
        self.settle_prisoner(npc, "kill", text)

    def settle_prisoner(self, npc, how: str, text: str) -> None:
        R = A["outlaw_rep"]
        pr = self.player.prisoners.get(npc.id, {})
        if how == "release":
            delta = R["keep_deal"] if pr.get("deal") else R["spare"]
            verdict, tell = "let go", "slips away, glancing back once"
        else:
            delta = R["kill_after_deal"] if pr.get("deal") else R["kill_after_talk"] if pr.get("asked") else R["kill"]
            verdict, tell = "put to the sword", "falls"
        self.player.outlaw_rep = max(-100, min(100, self.player.outlaw_rep + delta))
        node_pending = pr.get("node")
        self.end_conversation()
        self.drop_prisoner(npc, f"{verdict} by the stranger", partial_node=bool(node_pending))
        state = self.store.load_world_state() or pulse.empty_state(self.minutes)
        broke = how == "kill" and pr.get("deal")
        news = (f"A traveler spared a captured outlaw." if how == "release" else
                f"A traveler broke a promise of mercy and killed a captive." if broke else "A traveler put a captive outlaw to the sword.")
        pulse.add_news(state, news, pulse.town_of(self.world, self.player.location), self.minutes, ["outlaws", "hunters"])
        self.store.save_world_state(state)
        console.note(f"{npc.label().capitalize()} is {verdict}. Outlaws will hear of it ({delta:+d} with them).")
        self.weight_hint = "brief"
        self.narrate(f"The player has {verdict} the captive {npc.name}, who {tell}. "
                     + ("They had been promised mercy. " if pr.get("deal") and how == "kill" else "")
                     + "Describe the moment.", text)
        self.store.save_player(self.player)

    # ---------- display ----------

    def arc_lines(self, q: dict) -> str | None:
        if not q.get("arc"):
            return None
        data, arc = self.my_arc()
        if not arc or arc["id"] != q["arc"]:
            return None
        return f"[{q['letter']}] {q['title']} - {arcs.step_text(arc)} · no time limit"

    def show_arc(self) -> None:
        data, arc = self.my_arc()
        if not arc:
            console.note("No chain or arc is running.")
            return
        s = arc["story"]
        console.note(f"{s['title'] if arc['revealed'] else s['hook_title']} - {arcs.step_text(arc)}")
        for line in arc["log"]:
            console.note(f"  - {line}")
        n = arcs.current(arc)
        if n:
            console.note(f"Next: {self.pname(n['place'])}.")
        camp = n.get("camp") if n else None
        if camp:
            mood = ("on its guard" if camp["alert"] >= 2 else "wary" if camp["alert"] else "unaware of you")
            up = sum(1 for g in camp["guards"] if g["state"] == "up")
            console.note(f"The hideout is {mood}." + (f" {up} guard{'s' if up != 1 else ''} still stand watch." if camp["scouted"] else ""))
        console.note("No time limit.")
