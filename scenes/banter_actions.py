"""People of the world talking to each other: Maren and the guild clerk at the register, and the party's hired companions among themselves.

The engine decides when they talk and what brought it up, from the real state of the party and the place; the model writes the lines;
the engine checks them. A temperament says how someone takes a thing, never what they talk about."""
from __future__ import annotations

import random

import config
from engine import banter, clock, money, mentor, pulse, quirks, weather
from engine import party as rules
from llm.contracts import Exchange, PairDynamic
from llm.gateway import generate, LLMError
from npc.models import Memory
from ui import console

BN = banter.B


class BanterActions:
    # ---------- the model writes an exchange ----------

    def exchange_view(self, people) -> "truth.View":
        """The ground an exchange stands on, from the truth layer (engine/truth.py, f315): the party's view of the moment - Maren's when she
        takes part, since she knows Parth's people by name - with the speakers themselves left out of WHO IS HERE (PEOPLE introduces them)."""
        from engine import truth
        viewer = truth.MAREN if mentor.NAME in people else truth.PARTY
        view = truth.scene_of(self).view(viewer, "banter").without(*people)
        console.debug("truth view for the exchange: " + ", ".join(f"{h.split(' (')[0].lower()} {len(l)}" for h, l in view.sections()))
        return view

    def exchange(self, people: dict[str, str], situation: str, material: list[str], lines: tuple[int, int], extra_rules: str = "",
                 hook: str = "", wants: dict[str, str] | None = None, recent: dict[str, list[str]] | None = None,
                 members: dict[str, dict] | None = None, between: str = "", holders: dict[str, dict] | None = None,
                 subtexts: dict[str, str] | None = None, shared: str = "", all_speak: bool = False, interaction: str = "",
                 first_speaker: str = "", moment: bool = False, silent_ok: tuple = (), must_name: str = "") -> list[tuple[str, str]] | None:
        """The model writes a short exchange between these people (name -> who they are); None if it fails or is turned off."""
        if not getattr(config, "VOICED_MENTOR", True):
            return None
        from engine import canon
        self._last_claims = []
        system = ("You write short dialogue between people in a fantasy world.\nRULES:\n" + "\n".join(f"- {r}" for r in BN["rules"] + BN["banter"]["rules"]) +
                  "\n- " + " ".join(quirks.Q["answer_first"].split()) +
                  (f"\n- {extra_rules}" if extra_rules else "") +
                  "\n\n" + quirks.style_block() +
                  "\n- Each line may carry a gesture, the body language of the speaker as they say it. " + quirks.GESTURE_RULE +
                  ("\n- Whatever specific thing someone says about themselves becomes true of them for good; never contradict anything "
                   "given as true of them." if members else "") +
                  '\n\nRespond only with JSON matching the schema: {"lines": [{"speaker": "name", "text": "what they say", "gesture": ""}]}.')
        from engine.prompt import Prompt
        c = self.player.character
        P_ = Prompt()
        P_.fact("\n".join(f"  {n}: {d[1] if isinstance(d, tuple) else d}" for n, d in people.items()), "PEOPLE")
        hows = {n: d[0] for n, d in people.items() if isinstance(d, tuple) and d[0]}
        if hows:
            P_.instruction("\n".join(f"  {n}: {h}" for n, h in hows.items()), "HOW EACH SPEAKS")
        P_.fact(f"{c.name}, level {c.level}", "THE PLAYER'S CHARACTER, WHO IS PRESENT")
        view = self.exchange_view(people)
        P_.fact(view.text())                                  # (f315) WHERE, WHO IS HERE, the town, what is happening: the truth layer's, like every speaker's
        P_.fact(situation, "WHAT IS HAPPENING")
        if between:
            P_.instruction(between, BN["banter"]["between_label"]["moment" if moment else "idle"])
        if shared:
            P_.fact(shared, "SOMETHING THEY SHARED")
        if hook:
            P_.fact(hook, "WHAT BROUGHT THIS UP")
        if wants:
            P_.instruction("\n".join(f"  {n}: {w}" for n, w in wants.items()), "WHAT EACH WANTS FROM THE MOMENT (never said outright)")
        if interaction:
            P_.instruction(interaction, "WHO TAKES THE FLOOR, AND WHOM EACH ANSWERS")
        if subtexts:
            P_.instruction("\n".join(f"  {n}: {t}" for n, t in subtexts.items()), quirks.Q["subtext_rule"])
        for n, lines_ in (recent or {}).items():
            rule = banter.unsaid_rule(lines_, hook or situation)
            if rule:
                P_.history(rule.replace("SAID LATELY BY YOU", f"SAID LATELY BY {n.upper()}"))
        holders = holders or {n: m for n, m in (members or {}).items()}
        notes = [quirks.voice_notes(m) for m in (members or {}).values()]
        notes = [x for x in notes if x]
        if notes:
            P_.instruction("\n".join(f"  - {x}" for x in notes), "WHOSE WORDS ARE WHOSE")
        for n, h in holders.items():
            lean = quirks.leaned_on(h)
            if lean:
                P_.history(lean.replace("BY THEM", f"BY {n.upper()}"))
        offers = {n: self.material_for(m) for n, m in (members or {}).items()}
        offers = {n: o for n, o in offers.items() if o}
        if offers:
            P_.material("\n".join(f"  {n}:\n" + quirks.material_block(o).replace("  - ", "    - ") for n, o in offers.items()),
                        "WORDS EACH MAY USE THIS TIME, AS THEY ARE (each person's are theirs alone; only if they fit; nobody has to)")
        P_.fact(("; ".join(list(getattr(self.place, "visible", []) or [])[:6]) or "nothing in particular") +
                ". WHAT EACH CARRIES: " + "; ".join(f"{n}: {quirks.carried(members.get(n) if members and n in members else None)}" for n in people if n in holders),
                "FOR A GESTURE ONLY - WHAT IS HERE")
        quiet = [n for n in people if n in silent_ok]
        if quiet:
            P_.instruction(f"{' and '.join(quiet)} may answer with no words: a line with empty text and only a gesture, or no line at all.", "WHO MAY SAY NOTHING")
        P_.instruction(f"WRITE {lines[0]} TO {lines[1]} LINES, speakers from: {', '.join(people)}.")
        ctx = {"speakers": list(people), "lines": lines, "all_speak": all_speak, "silent_ok": tuple(silent_ok), "first_speaker": first_speaker, "material": material + [hook or ""], "recent": recent or {},
               "members": members or {}, "player": self.player.character.name, "known": view.scene.known_words(), "must_name": must_name,
               "gesture_states": {n: quirks.gesture_state(h, [dict(o, name=on) for on, o in holders.items() if o is not h] + self.gesturers(h))
                                  for n, h in holders.items()}}
        try:
            r = generate("exchange", system, P_, Exchange, temperature=0.9, max_tokens=config.PROSE_MAX_TOKENS, retries=1, validation_context=ctx,
                         relaxed_context=dict(ctx, recent={n: l[-1:] for n, l in (recent or {}).items()}, kit=False))
        except LLMError:
            return None
        self._last_claims = [(l.speaker, l.text) for l in r.lines if l.text]     # what was said, for canon and for what they remember saying
        self._last_topic = (hook or "") + " " + situation
        for l in r.lines:
            if l.speaker in holders:
                quirks.note_line(holders[l.speaker], l.gesture)
        from engine import severity
        return [(l.speaker, quirks.shown(l.text, l.gesture, l.speaker) if (l.text or l.gesture) else severity.silent_line(l.speaker)) for l in r.lines]

    def show_exchange(self, lines: list[tuple[str, str]]) -> None:
        merged: list[list[str]] = []
        for who, text in lines:                                  # a person's lines that follow each other are one speech
            if merged and merged[-1][0] == who:
                merged[-1][1] += ("\n" if text.startswith("(") else " ") + text
            else:
                merged.append([who, text])
        by_name = {m["name"]: m for m in self.player.party if m.get("permanent")}
        from engine import severity
        before, after = self.exchange_frame(merged)                # (f325) the narrator opens and closes the exchange, as it frames anyone's words
        if before:
            console.narrate(before)
        self.note_party_said(len(merged))                                    # (f386)
        for who, text in merged:
            console.say(text, who)
            if severity.is_silent(text):                         # a gesture or silence: nothing was said to remember saying
                continue
            if who == mentor.NAME:
                mentor.remember_said(self.player, text)
            elif who in by_name:
                rules.said(by_name[who], text)
        if after:
            console.narrate(after)

    def exchange_frame(self, merged: list[list[str]]) -> tuple[str, str]:
        """(f325) How the party falls into talking and how it ends, from the narrator - one call for the whole exchange. ('', '') without it."""
        if not merged or not getattr(config, "NARRATED_DIALOGUE", True) or not getattr(config, "VOICED_MENTOR", True):
            return "", ""
        from llm.contracts import DialogueFrame
        from scenes import world_prompts as wp
        from scenes.voice import fresh
        from engine.party import P
        in_fight = bool(self.combat)
        speaking = {who for who, _ in merged}
        by_name = {m["name"]: m for m in self.player.party if m.get("permanent")}
        speakers = []
        for who in speaking:
            if who == mentor.NAME:
                speakers.append(f"{who}: an A-rank adventurer travelling with the player")
            elif who in by_name:
                m = by_name[who]
                speakers.append(f"{who}: {m.get('blurb', '')}, {self.temper_text(m)}; travelling with the player")
            else:
                n = next((x for x in self.present if x.name == who or x.label() == who), None)
                speakers.append(f"{who}: {n.activity}" if n else who)
        others = [f"{self.seen_as(n)}: {n.activity}" for n in self.present if n.name not in speaking and n.label() not in speaking][:4]
        spoken = [t for _, t in merged if not t.startswith("(")] or [t for _, t in merged]
        try:
            from engine import reach                            # (f344) what the place offers the party; tense in a fight
            frame = fresh("dialogue_frame", wp.EXCHANGE_SYSTEM,
                          wp.exchange_request(self.time_label(), self.place, speakers, others, spoken[0], spoken[-1], self.recent_narration,
                                              P["frame"]["exchange_fight" if in_fight else "exchange"], self.player.character.name,
                                              reach=reach.within("", self.place.type), moment=reach.moment(fight=in_fight)),
                          DialogueFrame, self.recent_narration, fields=("before", "after"), max_tokens=config.PROSE_MAX_TOKENS)
            after = "" if in_fight else frame.after
            self.remember_narration(" ".join(t for t in (frame.before, after) if t.strip()),
                                    {"type": "dialogue", "before": frame.before, "speaker": "", "speech": "", "after": after})
            return frame.before, after
        except LLMError:
            return "", ""

    # ---------- Maren and the clerk ----------

    def mentor_clerk_exchange(self, clerk) -> None:
        """Maren and the clerk talk about signing the newcomer up. The clerk's manner decides how it goes: kindness is teased back,
        rudeness is met with something drier and sharper. Maren uses the clerk's name, so the player learns it; her word counts for
        something with the clerk."""
        fee = money.words(mentor.G["joining_fee"])
        from npc.life import promote
        promote(clerk, self.store, self.world, self.catalog)        # (f299) the clerk becomes a person before Maren meets her: her personality sets how it goes
        m = banter.manner(clerk)
        console.debug(f"clerk exchange: {clerk.name} reads as {m}")
        who = clerk.name or clerk.label()
        clerk_desc = (f"{clerk.description or 'the guild clerk'} Personality: {clerk.personality or 'businesslike'}. Voice: {clerk.voice or 'plain'}. "
                      f"Mood lately: {clerk.mood or 'ordinary'}.")
        people = {mentor.NAME: (mentor.chat_system_persona() + " " + " ".join(quirks.Q["maren"]["blueprint"]),
                                f"Maren Holt, an A-rank adventurer. She has known {who} for years and calls them by name."),
                  who: f"The guild clerk, {who}. {clerk_desc}"}
        sit = BN["clerk"]["situation"].format(fee=fee) + " " + BN["clerk"]["manner"][m]
        recent = {mentor.NAME: [t for w, t in self.player.mentor.get("chat", []) if w == "Maren"]}
        lines = self.exchange(people, sit, [fee, sit], tuple(BN["clerk"]["lines"]), recent=recent, holders={mentor.NAME: self.player.mentor})
        if not lines:
            lines = [(mentor.NAME if k == "maren" else who, t) for k, t in banter.clerk_fallback(m, fee)]
        self.show_exchange(lines)
        day = clock.day(self.minutes)
        clerk.memories.append(Memory(day=day, turn=self.store.meta.turn, text="Maren Holt brought a newcomer in to be signed into the register and spoke for them."))
        clerk.trust = min(100, clerk.trust + BN["clerk"].get("vouch_trust", 10))
        clerk.met_player = True
        if clerk.name:
            clerk.name_known_to_player = True
        self.store.save_npc(clerk)

    # ---------- the party among themselves ----------

    def banter_crew(self) -> list[dict]:
        if self.combat or self.player.delve or mentor.tutorial_on(self.player) or self.player.party_mode != "with":
            return []
        return [m for m in self.player.party if m.get("permanent") and not m.get("story")]

    def banter_tick(self) -> None:
        """After every action: a fight just ended, a rest just finished, or the party has arrived somewhere new."""
        loc = self.player.location
        prev = getattr(self, "_banter_loc", None)
        self._banter_loc = loc
        due = getattr(self, "_banter_due", "")
        self._banter_due = ""
        crew = self.banter_crew()
        if not crew:
            return
        if self.party_said_now() >= BN["banter"].get("turn_lines", 2) and not (due == "fight" and (self.player.party_last_fight or {}).get("fallen")):
            return                                          # (f386) the party has said enough this turn already; a death is still talked over
        rng = random.Random(self.store.meta.seed * 7919 + self.minutes)
        last = getattr(self, "_hire_last", None)
        just_talked = bool(last) and last[1] >= self.store.meta.turn - 1        # (f307) they have just spoken with the player, this turn
        if just_talked and not (due == "fight" and (self.player.party_last_fight or {}).get("fallen")):
            return                                          # ...so they do not turn round and say it all again among themselves
        if due == "fight":                                 # a fight that mattered is talked over; an easy win, now and then and not straight after talk
            B_ = BN["banter"]
            if (self.player.party_last_fight or {}).get("fallen"):
                go = rng.randrange(100) < B_["fight_death_chance"]
            elif self.fight_mattered(crew):
                go = rng.randrange(100) < B_["fight_chance"]
            else:
                go = rng.randrange(100) < B_["fight_easy_chance"] and self.minutes - getattr(self, "_banter_last", -10**9) >= B_["fight_easy_cooldown"]
            if go:
                self._banter_last = self.minutes
                self.party_banter(crew, "fight")
            return
        if due == "rest":
            if rng.randrange(100) < BN["banter"]["rest_chance"] and self.minutes - getattr(self, "_banter_last", -10**9) >= 60:
                self._banter_last = self.minutes
                self.party_banter(crew, "rest")
            return
        if prev is None or prev == loc:
            return
        if self.minutes - getattr(self, "_banter_last", -10**9) < BN["banter"]["cooldown"]:
            return
        if rng.randrange(100) >= BN["banter"]["chance"]:
            return
        self._banter_last = self.minutes
        self.party_banter(crew, "travel")

    def fight_mattered(self, crew: list[dict]) -> bool:
        """Was the last fight one worth talking over: hard, lost, or someone came out of it badly hurt, carried, or fell?"""
        last = self.player.party_last_fight or {}
        if last.get("hard") or not last.get("won", True) or last.get("fallen") or last.get("carried"):
            return True
        return any(rules.health_now(m, self.minutes) < 0.6 for m in crew)

    def banter_hook(self, pick: list[dict], kind: str, rng: random.Random) -> tuple[str, str, dict | None]:
        """What brought the talk up, from the real state: (hook kind, hook text, the member it is about or None). The pressing things
        come first; when nothing presses, the place, the weather or nothing much."""
        from engine import context
        H = BN["banter"]["hooks"]
        now = self.minutes
        last = self.player.party_last_fight or {}
        fresh = last and now - last.get("minute", -10**9) <= 1440
        options: list[tuple[int, str, str, dict | None]] = []          # (weight, kind, text, member)
        for m in pick:
            h = rules.health_now(m, now)
            if (m["id"] in last.get("carried_ids", []) or ("carried_ids" not in last and m["name"] in last.get("carried", []))) and fresh:
                options.append((6, "carried", H["carried"].format(name=m["name"]), m))
            elif h < 0.6:
                options.append((5, "hurt", H["hurt"].format(name=m["name"], health=self.hurt_words(h).replace("you move", "they move")), m))
            if m.get("warned"):
                options.append((4, "warned", H["warned"].format(name=m["name"]), m))
            mood = rules.mood_now(m, now)
            if mood:
                options.append((2, "mood", H["mood"].format(name=m["name"], mood=mood), m))
        if fresh and kind == "fight" or (fresh and kind != "fight" and rng.random() < 0.5):
            if last.get("fallen"):
                what = (last.get("fallen_what") or {}).get(last["fallen"][0])        # (f385) a companion beast, said as what they were
                options.append((6, "fallen", H["fallen"].format(name=last["fallen"][0]) + (f" {last['fallen'][0]} was {what}." if what else ""), None))
            elif not last.get("won"):
                options.append((5, "lost_fight", H["lost_fight"], None))
            elif last.get("hard"):
                options.append((4, "hard_fight", H["hard_fight"], None))
        if kind == "fight" and options:
            top = max(w for w, *_ in options)
            options = [o for o in options if o[0] >= top - 1]
        pressing = any(k in context.PRESSING_HOOKS or k == "fallen" for _, k, _, _ in options)
        grave = any(k in context.GRAVE_HOOKS for _, k, _, _ in options)
        if not pressing or (not grave and kind != "fight" and rng.random() < 0.25):    # the small stuff when nothing presses; now and then after a
                                                                                        # hard fight, never beside a bad wound or a death
            news = self.party_news()
            if news and rng.random() < 0.5:
                options.append((1, "news", H["news"].format(news=rng.choice(news)), None))
            if kind == "travel" and getattr(self.place, "visible", None) and rng.random() < 0.6:
                options.append((1, "arrival", H["arrival"].format(thing=rng.choice(list(self.place.visible))), None))
            _, sky = weather.describe(self.store.meta.seed, now)
            options.append((1, "weather", H["weather"].format(period=clock.period(now), weather=sky.lower(), season=clock.season(now)), None))
            options.append((0.5, "mundane", H["mundane"], None))
            if kind != "fight":                                 # something of their own: the best small talk is about the people
                for m in pick:                                  # a promotion waiting is their own business, not something pressing: it comes up
                    if m.get("capped") and rules.next_rank(m.get("rank") or "") and context.due(m, "promotion", now):     # only with the small stuff
                        options.append((1, "promotion", H["promotion"].format(name=m["name"]) + " " + " ".join(quirks.Q["promotion_fact"].split()), m))
                    mem = [x for x in m.get("memories", []) if "player" in x["text"].lower()]     # so is something the player did a while back
                    if mem:
                        x = max(mem, key=lambda x: (x["weight"], x["day"]))
                        options.append((2, "player", H["player"].format(name=m["name"], memory=x["text"]), m))
                from engine import gravity                      # how heavy a topic may be decides whether it fits this moment
                mo = gravity.moment(kind, bool(fresh and (last.get("fallen") or not last.get("won", True))))
                scene = self.banter_scene()
                for m in pick:
                    got = self.personal_topic(m, rng, mo, scene=scene)
                    if got:
                        thing, g, touch = got
                        said = H["touched"].format(touch=touch[0].upper() + touch[1:], name=m["name"], thing=thing) if touch else \
                            H["personal"].format(name=m["name"], thing=thing)
                        options.append(((3 if touch else 1) * gravity.share(mo, g), "personal", said, m, g))     # (f382) touched by the scene
                job = next((q for q in self.player.quests if q.get("progress", 0) < q.get("count", 1)), None)
                if job and kind in ("travel", "rest"):          # (f382) the job they are on, what travelling together is for
                    options.append((2, "errand", H["errand"].format(job=job.get("title", "")), None))
                    mt = rules.P["motives"].get(m.get("motive", ""), "")
                    if mt and context.due(m, "motive", now):      # what drives them comes up unasked only from here, and only when due
                        options.append((gravity.share(mo, "personal"), "motive", H["motive"].format(name=m["name"], thing=f"{m['name'].split()[0]} {mt}"), m))
                got = self.shared_topic(pick, rng, mo)
                if got:                                         # something the two went through together
                    shared, g = got
                    options.append((3 * gravity.share(mo, g), "shared", H["shared"].format(a=pick[0]["name"], b=pick[1]["name"], thing=shared), None, g))
        options = [o for o in options if o[0] > 0]
        total = sum(o[0] for o in options)
        r = rng.uniform(0, total)
        chosen = options[-1]
        for o in options:
            r -= o[0]
            if r <= 0:
                chosen = o
                break
        if len(chosen) > 4 and chosen[4] == "heavy":            # a heavy thing raised unasked: not again for a while, by either of them
            from engine import gravity
            for m in ([chosen[3]] if chosen[3] is not None else pick):
                gravity.raised(m, "heavy", now)
        return chosen[1], chosen[2], chosen[3]

    PERSONAL_KEEP = 8                                           # how many of their own topics are remembered as used, so the next is new

    def personal_topic(self, m: dict, rng: random.Random, moment: str = "ease", scene=()) -> tuple[str, str, str] | None:
        """One thing of their own to talk about, with its weight and what here touched it ('' when nothing did): a detail written at hire,
        something they have said about themselves, or a belief; not one used lately, and only as heavy as the moment allows
        (engine/gravity.py). (f382) With the scene given, one that something in it is close to comes first."""
        from engine import gravity, relevance
        import config
        used = set(m.get("topics_used", []))
        pool = gravity.details(m) + [(c["text"], gravity.level(c.get("gravity"))) for c in m.get("canon", []) + m.get("traits", [])]
        pool += [(b["text"], "light") for b in m.get("beliefs", [])]
        pool = [(t, g) for t, g in pool if t not in used]
        touches = {}
        for t, g in pool[:8] if scene else ():
            hit = relevance.pick(t, list(scene), 1, floor=config.SIM_RELEVANT)
            if hit:
                touches[t] = hit[0]
        got = gravity.choose([(t, g) for t, g in pool if t in touches], moment, rng, m, self.minutes) if touches else None
        if got:
            return got[0], got[1], touches[got[0]]
        got = gravity.choose(pool, moment, rng, m, self.minutes)
        return (got[0], got[1], "") if got else None

    def banter_scene(self) -> list[str]:
        """(f382) What is in front of the party, as lines something of their own might be touched by: the place and what can be seen."""
        out = [f"{self.place.name}, a {self.place.type}"] + [str(v).rstrip(".") for v in self.place.visible]
        return [x for x in out if x.strip()]

    def shared_topic(self, pick: list[dict], rng: random.Random, moment: str = "ease") -> tuple[str, str] | None:
        """Something the pair went through together and has not talked over lately, with its weight, or None. A heavy one needs both of
        them to be ready to raise it."""
        from engine import gravity
        if len(pick) != 2:
            return None
        rel = self.relation(pick[0], pick[1]) or {}
        used = set(rel.get("topics_used", []))
        pool = [(h["text"], gravity.level(h.get("gravity"))) for h in rel.get("history", [])[-6:] if h["text"] not in used]
        if any(g == "heavy" for _, g in pool) and not all(gravity.heavy_allowed(m, self.minutes) for m in pick):
            pool = [(t, g) for t, g in pool if g != "heavy"]
        return gravity.choose(pool, moment, rng)

    def party_news(self) -> list[str]:
        try:
            class _P:
                knowledge_groups = ["adventurers"]
                location = self.player.location
            return pulse.news_for(self.store, self.world, _P(), self.minutes, 3)
        except Exception:
            return []

    def banter_wants(self, pick: list[dict], hook_kind: str, about: dict | None, kind: str, stances: dict | None = None) -> dict[str, str]:
        W = BN["banter"]["wants"]
        out = {}
        for m in pick:
            if hook_kind == "deed" and (stances or {}).get(m["id"]):
                key = "deed_" + stances[m["id"]]
            elif hook_kind in ("hurt", "carried"):
                key = "hurt_self" if m is about else "hurt_other"
            elif hook_kind == "promotion":
                key = "promotion_self" if m is about else "promotion_other"
            elif hook_kind in ("personal", "motive"):
                key = "personal_self" if m is about else "personal_other"
            elif hook_kind == "shared":
                key = "shared"
            elif hook_kind == "warned":
                key = "warned_self" if m is about else "warned_other"
            elif hook_kind in ("hard_fight", "lost_fight", "fallen"):
                key = hook_kind
            elif kind == "rest":
                key = "rest"
            elif kind == "travel":
                key = "arrival"
            else:
                key = "default"
            table = W.get(key, W["default"])
            temper = (m.get("temper") or [""])[0]
            out[m["name"]] = table.get(temper) or table.get("default") or W["default"]["default"]
        return out

    def companion_core(self, m: dict, query: str | None = None, scene: str = "talk", without: tuple = ()) -> str:
        """Who they are, for one scene, as one piece of text (for writing about them, or a summary). See companion_parts. without: kinds
        of record to leave out (a pair's summary leaves out what each thinks of the others, or the model copies it onto the new pair)."""
        how, facts = self.companion_parts(m, query, scene, without=without)
        return facts + (f" HOW THEY SPEAK: {how}" if how else "")

    def companion_parts(self, m: dict, query: str | None = None, scene: str = "talk", emotion: str = "", relation: str = "",
                        toward: str = "", hit: str = "", in_fight: bool = False, without: tuple = ()) -> tuple[str, str]:
        """Who they are, for one scene (engine/context.py), split by type (engine/prompt.py): (how they speak - instruction; who they are and
        what is on their mind - fact). With no query, everything. With a query, a small core plus only the records this scene carries: what
        bears on the moment, now and then one thing on their mind, and their background concerns only when the engine says they are due."""
        from engine import context, quirks
        self.quirked(m)
        from engine import voice_profile, severity
        rng_v = random.Random(f"{self.store.meta.seed}:{self.minutes}:{m['id']}:voice:{len(m.get('said', []))}")
        emotion = severity.emotion(hit) or emotion                      # devastated: their own way of breaking, over any other feeling
        struck = severity.register(hit, in_fight) if hit else ""
        speak = quirks.blueprint(m, rng_v if query is not None else None)
        v = quirks.voice_prompt(m, rng_v if query is not None else None)
        g = quirks.growth(m)
        from engine import voices
        kit = [f"{k[0].upper()}{k[1:]}." for k in voices.lines(voices.kit_of(m))]            # (f350) their kit: always, it is the voice
        mine = kit + ([f"In speech, {v}."] if v else []) + ([f"With the player, they have changed: {g}; let it show, never say it."] if g else [])
        room = self.HOW_BUDGET - len(speak) - len(mine) + len(kit)   # at most HOW_BUDGET lines on how they speak besides the kit, in any one reply
        profile = voice_profile.compile(m, rng_v, emotion, relation, toward, budget=room, feature=self.culture_now(m)) if query is not None else []
        how = " ".join(([struck] if struck else []) + speak + mine + profile)
        facts = f"A hired {m['role']}, {m.get('blurb', '')}." + (" " + voice_profile.who(m) if voice_profile.who(m) else "")
        records = [r for r in self.companion_records(m) if r.get("kind") not in without]
        rng = random.Random(f"{self.store.meta.seed}:{self.minutes}:{m['id']}")
        chosen, notes = context.select(m, records, "full" if query is None else scene, query, self.minutes, rng)
        facts += (" " + " ".join(chosen) if chosen else "")
        note = context.raised_note(notes)
        return how + (" " + note if note else ""), facts

    HOW_BUDGET = 6

    def hit_level(self, m: dict, beat, present: list[dict] | None = None) -> str:
        """How hard this moment hits them (engine/severity.py): from how grave it is and how close they are to whom it concerns."""
        from engine import party_director as director, severity
        if beat is None or not getattr(beat, "weight", "") or beat.weight == "light":
            return "composed"
        c = beat.concerns
        score = (self.relation(m, {"id": c}) or {}).get("score", 0) if c and c not in ("player", m["id"]) else None
        stands = bool(c is None and director.relevant(m, beat.text, present or [m]))
        return severity.level(beat.weight, severity.closeness(m, c, score, stands), told=beat.kind == "said")

    def leave_marks(self, present: list[dict], beat) -> None:
        """What a shaking or devastating moment leaves on everyone who saw it, spoken or not: once per moment."""
        from engine import severity
        if beat is None or not beat.short:
            return
        for m in present:
            severity.leave_mark(m, self.hit_level(m, beat, present), beat.short, f"{beat.concerns}:{beat.short}", self.minutes)

    def party_moment(self, what: str, weight: str, concerns: str | None = None, short: str = "", in_fight: bool = False,
                     exclude: tuple = ()) -> bool:
        """Something has just happened in front of the companions - one of them killed, a betrayal, something grim found. The same path
        for every kind of event: whoever raises it says how grave it is (light, personal, heavy) and whom it concerns. Who speaks is the
        director's (a heavy moment: everyone); how hard it hits each is engine/severity.py, from what the one it concerns is to them. In
        the middle of a fight, one outburst each. What it leaves (a mood that lasts, a memory) is left on everyone present, once."""
        from engine import party_director as director
        crew = [self.quirked(m) for m in self.player.party if m.get("permanent") and not m.get("story") and self.player.party_mode == "with"
                and m["id"] != concerns and m["id"] not in exclude]
        if not crew:
            return False
        beat = director.beat_from_event(what, weight, concerns, short, in_fight)
        self.last_hits = {m["name"]: self.hit_level(m, beat, crew) for m in crew}     # as it hit them, before it leaves its mark
        plan = director.plan(beat, crew, random.Random(f"{self.store.meta.seed}:{self.minutes}:moment:{short}"), must_start=False)
        self.last_plan = plan
        by_id = {m["id"]: m for m in crew}
        pick = [by_id[i] for i in plan.speaker_ids]
        shown = False
        if pick:
            S_ = BN["banter"]["situation"]
            sit = S_["fight_now" if in_fight else "witnessed"].format(place=self.place.name, what=what)
            span = (len(pick), len(pick)) if in_fight else None
            if len(pick) > 1:
                shown = bool(self.talk_among(crew, pick, plan, sit, "event", what, None, {}, "pressing", span=span))
            if not shown:
                for m in pick:
                    hit = self.hit_level(m, beat, crew)
                    line = self.companion_line(m, [what + (" " + sit if in_fight else "")], what, hit=hit, in_fight=in_fight, weight=weight)
                    if line:
                        from engine import severity
                        self.companion_show(m, line, what)
                        if not severity.is_silent(line):
                            rules.said(m, line)
                        severity.note_reaction(hit, severity.is_silent(line))
                        shown = True
                if shown:
                    director.spoke(plan, by_id, self.minutes)
        self.leave_marks(crew, beat)
        self.store.save_player(self.player)
        return shown

    def material_for(self, m: dict) -> list[str]:
        from engine import quirks
        rng = random.Random(f"{self.store.meta.seed}:{self.minutes}:{m['id']}:said{len(m.get('said', []))}")
        return quirks.material(m, rng, m.get("said", []), feature=self.culture_now(m))

    def culture_now(self, m: dict) -> tuple:
        """This reply's one feature of their culture, or none (engine/voice_profile.py culture_feature): rolled once per reply, so how they
        speak and what they are offered to say agree."""
        from engine import voice_profile
        sp = m.get("speech") or {}                          # the same moment for the same person: a different person (or profile) is a new roll
        key = f"{self.minutes}:{len(m.get('said', []))}:{m.get('id')}:{sp.get('culture')}:{sp.get('fluency')}:{sp.get('strength')}"
        if m.get("_culture_key") != key:
            kind, payload = voice_profile.culture_feature(m, random.Random(f"{self.store.meta.seed}:{key}:{m['id']}:culture"))
            m["_culture_key"], m["_culture"] = key, [kind, list(payload) if isinstance(payload, tuple) else payload]
        kind, payload = m["_culture"]
        return kind, (tuple(payload) if isinstance(payload, list) else payload)

    def companion_records(self, m: dict) -> list[dict]:
        """Everything the game knows about a hire, tagged (engine/context.py)."""
        from engine import canon, context, quirks, voice_profile
        recs = context.concerns_of(m, rules.P["motives"]) + voice_profile.origin_records(m)
        h, l, fl = quirks.habit_prompt(m), quirks.leanings(m), quirks.flaw_prompt(m)
        recs += [{"kind": "trait", "text": t} for t in ([f"A habit: {h}."] if h else []) + ([l] if l else []) + ([f"A weakness they know of: {fl}."] if fl else [])]
        from engine import gravity
        recs += [{"kind": "detail", "text": f"About them: {d}", "gravity": g} for d, g in gravity.details(m)]
        for o in self.player.party:                              # what they think of each other companion: comes in when the talk is about them
            if o is m or not o.get("permanent"):
                continue
            view = ((self.relation(m, o) or {}).get("views") or {}).get(m["id"])
            if view:
                recs.append({"kind": "view", "text": f"What you think of {o['name']}: {view}", "gravity": "light"})
        return recs + canon.records(m, self.minutes // 1440)

    def companion_concerns(self, m: dict) -> list[dict]:
        from engine import context
        return context.concerns_of(m, rules.P["motives"])

    def party_banter(self, crew: list[dict], kind: str = "travel") -> bool:
        """Talk among the companions travelling along. What it is about is chosen from everyone present; who of them speaks, and whom each
        answers, is the director's (engine/party_director.py)."""
        from engine import context, party_director as director
        rng = random.Random(self.store.meta.seed * 31 + self.minutes)
        G = BN["banter"]
        present = list(crew) if len(crew) <= G["most_speakers"] else rng.sample(crew, G["most_speakers"])
        for m in present:                                  # who they are is settled before what they talk about is chosen
            self.quirked(m)
        hook_kind, hook, about = self.banter_hook(present, kind, rng)
        topic = hook.replace(" " + " ".join(quirks.Q["promotion_fact"].split()), "")      # the rule the writer is given is not the topic
        concerns, short = None, ""
        if hook_kind == "fallen":                            # whom the death concerns: how hard it hits each is what the dead one was to them
            last = self.player.party_last_fight or {}
            concerns = (last.get("fallen_ids") or [None])[0]
            short = f"{last['fallen'][0]}'s death" if last.get("fallen") else ""
        plan = director.plan(director.beat_from_hook(hook_kind, topic, about, concerns, short), present, rng)
        self.last_plan = plan
        by_id = {m["id"]: m for m in present}
        pick = [by_id[i] for i in plan.speaker_ids]
        if not pick:
            return False
        wants = self.banter_wants(pick, hook_kind, about, kind)
        sit = G["situation"][kind].format(place=self.place.name)
        lines = self.talk_among(present, pick, plan, sit, hook_kind, hook, about, wants, context.scene_for_hook(hook_kind))
        if not lines:
            return False
        if hook_kind == "personal" and about is not None:
            thing = hook.split(": ", 1)[-1]
            about.setdefault("topics_used", []).append(thing)
            del about["topics_used"][:-self.PERSONAL_KEEP]
        if hook_kind == "motive" and about is not None:
            context.mark(about, "motive", self.minutes)
        if hook_kind == "shared" and len(pick) == 2:
            rel = self.relation(pick[0], pick[1])
            if rel is not None:
                rel.setdefault("topics_used", []).append(hook.split(": ", 1)[-1])
                del rel["topics_used"][:-self.PERSONAL_KEEP]
        for m in pick:
            if hook_kind == "promotion" and m is about:
                context.mark(m, "promotion", self.minutes)
        self.store.save_player(self.player)
        return True

    def talk_among(self, present: list[dict], pick: list[dict], plan, situation: str, hook_kind: str, hook: str, about: dict | None,
                   wants: dict, scene: str, span: tuple | None = None) -> list[tuple[str, str]] | None:
        """One exchange among the chosen speakers, with everyone else present named as listening: each speaker as they are for this moment
        (what they feel, how they are toward the others, what they think of each one present and of the player), how the speakers are with
        each other, and the director's plan of who opens and whom each answers. One model call; what they say about themselves is kept only
        if the exchange is the one shown. Returns the lines shown, or None."""
        from engine import canon, context, party_director as director, voice_profile
        G = BN["banter"]
        listening = [m for m in present if m not in pick]
        if len(pick) == 1:
            how_many = G["one_of_several"] if listening else G["alone"]
        else:
            how_many = G["pair"] if len(pick) == 2 else G["group"]
        sit = situation + " " + how_many
        if listening:
            sit += " Also here, listening, and not speaking this time: " + ", ".join(m["name"] for m in listening) + "."
        lo, hi = G["group_lines"] if len(pick) > 2 else (G["one_lines"] if len(pick) == 1 and listening else G["lines"])
        from engine import severity
        hits = {m["name"]: self.hit_level(m, plan.beat, present) if plan else "composed" for m in pick}
        silent_ok = tuple(n for n, lv in hits.items() if severity.may_be_silent(lv, plan.beat.weight if plan else ""))   # the director says who may react; this, who must speak
        struck = {m["name"] for m in pick if plan and severity.at_least(self.hit_level(m, plan.beat, present), severity.SV["repeat_free_from"])}
        recent = {m["name"]: ([] if m["name"] in struck else list(m.get("said", []))) for m in pick}   # someone this moment has shaken or devastated
                                                                                       # may say the name again: repeating it is the grief
        import itertools
        lines_between, shared = [], ""
        for a, b_ in itertools.combinations(pick, 2):           # every pair speaking: how those two are with each other
            rel = self.relation(a, b_)
            if rel and (rel.get("stale") or "views" not in rel):  # a relation from before views were kept is written again, once
                self.pair_rewrite(a, b_, rel)
            if not rel:
                continue
            lines_between.append(f"{rel['dynamic']} They are {rules.relation_words(rel.get('score', 0))}.")
            for m, o in ((a, b_), (b_, a)):
                lean = (rel.get("wants") or {}).get(m["id"])
                if lean:
                    whom = "the other" if len(pick) == 2 else o["name"].split()[0]
                    wants[m["name"]] = f"{wants.get(m['name'], '')}; and with {whom}, as always, {lean}".strip("; ")
        between = " ".join(lines_between)
        if hook_kind == "shared" and len(pick) == 2:             # what they went through together comes in only when it is the topic
            shared = hook.split(": ", 1)[-1]
        subtexts, feelings = {}, {}
        for m in pick:
            if hook_kind in ("hurt", "carried"):
                sit_kind = "hurt_self" if m is about else "caretaker"
            else:
                sit_kind = {"lost_fight": "lost", "hard_fight": "hard_win", "fallen": "fallen"}.get(hook_kind, "")
                if hook_kind == "warned" and m is about:
                    sit_kind = "warned_self"
            st = quirks.subtext(m, sit_kind) if sit_kind else ""
            if st:
                subtexts[m["name"]] = st
            feelings[m["name"]] = sit_kind
        people = {}
        for m in pick:                                           # who each is for this moment: what they feel, and how they are toward the others
            others = [o for o in present if o is not m]          # everyone else there, speaking or not; toward the one they feel most strongly about
            other = max(others, key=lambda o: abs((self.relation(m, o) or {}).get("score", 0)), default=None)
            score = (self.relation(m, other) or {}).get("score", 0) if other else 0
            beat = plan.beat if plan else None
            how, desc = self.companion_parts(m, hook, scene if (scene != "about" or m is about) else "ease",
                                             emotion=voice_profile.emotion_for(feelings.get(m["name"], "")),
                                             relation=voice_profile.relation_kind(score=score) if other else "",
                                             toward=other["name"].split()[0] if other else "",
                                             hit=self.hit_level(m, beat, present), in_fight=bool(beat and beat.in_fight))
            if m["name"] in silent_ok:
                how = (how + " " + " ".join(severity.SV["silent_rule"].split())).strip()
            for o in others:                                       # what they think of each other one present, and of the player
                view = ((self.relation(m, o) or {}).get("views") or {}).get(m["id"])
                if view:
                    desc += f" Of {o['name'].split()[0]}: {view}"
            if m.get("impression"):
                desc += f" Of the player: {m['impression']}"
            people[m["name"]] = (how, desc)
        names = {m["id"]: m["name"] for m in present}
        args = dict(hook=hook, wants=wants, recent=recent, members={m["name"]: m for m in pick}, between=between, subtexts=subtexts, shared=shared,
                    all_speak=len(pick) > 1, interaction=director.interaction(plan, names) if plan else "",
                    first_speaker=pick[0]["name"] if plan and len(pick) > 1 else "",
                    moment=hook_kind in context.PRESSING_HOOKS or hook_kind in ("said", "deed", "fallen", "event"), silent_ok=silent_ok,
                    must_name=((self.player.party_last_fight or {}).get("fallen") or [""])[0] if hook_kind == "fallen" else "")   # (f385)
        span = span or (len(pick), hi)                            # no minimum beyond each chosen speaker saying something: some people do not talk much
        span = (max(1, span[0] - len(silent_ok)), max(1, span[1]))  # those allowed silence are not counted toward the lines that must be written
        if plan and plan.beat.weight != "light":                  # as it hit each of them, before anything it leaves behind changes their records
            self.last_hits = {m["name"]: self.hit_level(m, plan.beat, present) for m in present}
        lines = self.exchange(people, sit, [sit], span, **args)
        pending = self.read_exchange_claims(pick) if lines else []
        bad = [p for p in pending if p.bad]
        if bad:                                                   # a line contradicted what is true of someone: write it once more, keeping nothing
            rule = " ".join(f"{p.member['name']}: {canon.conflict_rule(p.bad)}" for p in bad)
            again = self.exchange(people, sit, [sit], span, extra_rules=rule, **args)
            if again:
                lines = again
                pending = self.read_exchange_claims(pick)
        if not lines:
            return None
        for p in pending:                                        # the exchange that is shown: its claims are kept (any still contradicting, left out)
            p.commit()
        self.show_exchange(lines)
        for m in pick:
            for who, text in lines:
                if who == m["name"] and not severity.is_silent(text):
                    context.note_spoken(m, text, self.minutes, self.companion_concerns(m))
        for n, lv in hits.items():                               # how each of them answered a moment that weighed on them
            if lv != "composed":
                mine = [t for w, t in lines if w == n]
                severity.note_reaction(lv, bool(mine) and all(severity.is_silent(t) for t in mine) or not mine)
        if plan:
            director.spoke(plan, {m["id"]: m for m in present}, self.minutes)
            self.leave_marks(present, plan.beat)
        return lines

    def read_exchange_claims(self, pick: list[dict]) -> list:
        """What the last exchange's speakers said about themselves and the world, worked out but not yet kept (engine/canon.py): one
        Pending per speaker who said anything new. The caller keeps them once the exchange is the one shown."""
        from engine import canon
        day = self.minutes // 1440
        said = getattr(self, "_last_claims", [])
        topic = getattr(self, "_last_topic", "")
        talking = [m for m in pick if any(w == m["name"] for w, _ in said)] if canon.worth_reading(topic) else []
        if not talking:
            return []
        got = canon.extract([(w, t) for w, t in said if any(w == m["name"] for m in talking)], {m["name"]: canon.known(m) + canon.said_about_self(m) for m in talking})
        return [canon.review(m, [], [], day, buckets=got[m["name"]]) for m in talking if got.get(m["name"])]

    # ---------- how two hires are with each other ----------

    def relation(self, a: dict, b: dict) -> dict | None:
        return self.player.party_relations.get(rules.pair_key(a["id"], b["id"]))

    def relations_seed(self) -> None:
        """Every pair of hires travelling together has a line on how they are with each other, written once when they first share the road."""
        crew = [m for m in self.player.party if m.get("permanent") and not m.get("story")]
        R = BN["banter"]["relations"]
        for i, a in enumerate(crew):
            for b in crew[i + 1:]:
                key = rules.pair_key(a["id"], b["id"])
                if key in self.player.party_relations:
                    continue
                got = self.pair_dynamic(a, b)
                line, wants, views = (got if got else (self.pair_fallback(a, b), {}, {}))
                self.player.party_relations[key] = {"score": 0, "dynamic": line, "day": clock.day(self.minutes), "wants": wants, "views": views,
                                                    "history": [], "tier": rules.relation_words(0)}
                rules.remember(a, clock.day(self.minutes), f"I started travelling with {b['name']}.", 1)
                rules.remember(b, clock.day(self.minutes), f"I started travelling with {a['name']}.", 1)
        self.store.save_player(self.player)

    def pair_fallback(self, a: dict, b: dict) -> str:
        R = BN["banter"]["relations"]["pairs"]
        ta, tb = (a.get("temper") or [""])[0], (b.get("temper") or [""])[0]
        for key, line in R.items():
            x, _, y = key.partition("|")
            if (ta, tb) == (x, y):
                return line.format(a=a["name"], b=b["name"])
            if (tb, ta) == (x, y):
                return line.format(a=b["name"], b=a["name"])
        return R["default"].format(a=a["name"], b=b["name"])

    def pair_dynamic(self, a: dict, b: dict, history: list[str] | None = None, words: str = "") -> tuple[str, dict, dict] | None:
        """(the line on how two hires are with each other, {id: what each tends to want from the other}, {id: what each thinks of the other}),
        or None if the model fails."""
        if not getattr(config, "VOICED_MENTOR", True):
            return None
        from engine import canon
        self._last_claims = []
        system = ("Two hired adventurers travel together in a fantasy world. Write ONE or two plain sentences on how they are with each other: a "
                  "small, specific dynamic a traveller beside them would notice (who needles whom, who looks after whom, what they argue about, what "
                  "they will not say). Name both. Then, for each, a few words on what they tend to want from the other when they talk "
                  "(\"to get a rise out of her\", \"to see he eats\"), and one short line on what each privately thinks of the other, from inside "
                  "their own head (\"thinks she fusses, and is secretly glad of it\"); it need not be fair, and the two need not agree. Summarise only what is given: their manners, what each approves of and cannot stand, their "
                  "habits" + (", and what they have been through together, which counts most" if history else "") + ". Invent no new habit, skill, routine or task "
                  "either of them performs, contradict nothing given, and invent no history, places, numbers or names. No game words. "
                  'Respond only with JSON matching the schema: {"dynamic": "...", "first_wants": "...", "second_wants": "...", "first_thinks": "...", '
                  '"second_thinks": "..."}.')
        req = "\n".join(f"{m['name']}: {self.companion_core(m, without=('view', 'opinion'))}" for m in (a, b))   # all of who they are, but not
                                                                                       # what they think of anyone else: that was being copied onto the new pair
        from engine import canon
        said_of = [f"  {x['name'].split()[0]}, of {y['name'].split()[0]}: {t}" for x, y in ((a, b), (b, a)) for t in canon.opinions_of(x, y["id"])[-3:]]
        if said_of:                                      # what each has said of the other, in their own words: the best evidence of how they are
            req += "\nWHAT EACH HAS SAID OF THE OTHER:\n" + "\n".join(said_of)
        if history:
            req += "\nWHAT THEY HAVE BEEN THROUGH TOGETHER:\n" + "\n".join(f"  - {h}" for h in history[-5:])
        if words:
            req += f"\nTHEY ARE NOW: {words}"
        try:
            r = generate("pair_dynamic", system, req, PairDynamic, temperature=0.9, max_tokens=160, retries=1,
                         validation_context={"names": [a["name"], b["name"]]})
            return r.dynamic, {a["id"]: r.first_wants, b["id"]: r.second_wants}, {a["id"]: r.first_thinks, b["id"]: r.second_thinks}
        except LLMError:
            return None

    def pair_rewrite(self, a: dict, b: dict, rel: dict) -> None:
        """They have grown closer or further apart: the line is written again from what they have been through."""
        got = self.pair_dynamic(a, b, [h["text"] for h in rel.get("history", [])], rules.relation_words(rel.get("score", 0)))
        if got:
            rel["dynamic"], rel["wants"], rel["views"] = got
        rel["stale"] = False

    def pair_event(self, a: dict, b: dict, text: str, gravity: str = "light") -> None:
        """Something both of them went through, kept for the pair, with how heavy it is to talk about (engine/gravity.py)."""
        rel = self.relation(a, b)
        if not rel:
            return
        hist = rel.setdefault("history", [])
        hist.append({"day": clock.day(self.minutes), "text": text, "gravity": gravity})
        del hist[:-6]
        from engine import canon
        canon.journal("pair_event", a["id"], b["id"], text, gravity=gravity, score=rel.get("score", 0))

    def relations_shift(self, m: dict, delta: int) -> None:
        """Something shared moved how this hire is with the others."""
        for other in self.player.party:
            if other is m or not other.get("permanent") or other.get("story"):
                continue
            rel = self.player.party_relations.get(rules.pair_key(m["id"], other["id"]))
            if rel:
                rel["score"] = max(-60, min(60, rel.get("score", 0) + delta))
                tier = rules.relation_words(rel["score"])
                if tier != rel.get("tier"):
                    rel["tier"], rel["stale"] = tier, True
