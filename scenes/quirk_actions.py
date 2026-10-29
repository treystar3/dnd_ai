"""Quirks in play: habits shown at their moment, reactions to the player's deeds, flaws that cost something, errands asked once trust is
there, secrets told as it grows, and Maren's own small habits and the things she lets slip. The engine decides when; the model, when
it speaks, puts it in the character's words; the written line stands when it fails."""
from __future__ import annotations

import random
import re

import config
from engine import clock, money, quirks
from engine import party as rules
from llm.contracts import CompanionReply
from llm.gateway import generate, LLMError
from scenes import party_prompts as ppr
from ui import console

YES = re.compile(r"^\W*(yes|yeah|aye|sure|fine|go on|go ahead|of course|all right|alright|ok|okay|take it|take your time|do it|you may|granted)\b", re.I)
NO = re.compile(r"^\W*(no|not now|later|another time|we can't|we cannot|there's no time|no time|keep moving|not today)\b", re.I)
ANSWER_TAIL = 6                 # an answer may carry this many words after the yes or no ("yes, of course", "no, not now") and no action


def is_answer(rx: re.Pattern, text: str) -> bool:
    """The line is that answer and nothing more: "Okay, let's head to the inn first" starts like a yes but is a plan of its own."""
    m = rx.match(text)
    if not m:
        return False
    rest = text[m.end():].lower()
    from engine import actions
    return len(re.findall(r"[a-z']+", rest)) <= ANSWER_TAIL and not actions.ACTION_RE.search(rest)


def deed_situation(scene, deed: str) -> str:
    from engine import banter
    return banter.B["banter"]["situation"]["deed"].format(place=scene.place.name, deed=deed)


class QuirkActions:
    from scenes.intercepts import Intercept as _I
    INTERCEPTS = (_I("errand", 10, "errand_intercept", "the yes or no to an errand a companion just asked"),)
    # ---------- the roll, for new hires and old saves ----------

    def quirked(self, m: dict) -> dict:
        if not m.get("quirks") or m["quirks"].get("voice") not in quirks.Q["voices"]:
            quirks.roll(m, random.Random(f"{self.store.meta.seed}:{m['id']}"))
        if m.get("permanent") and not m.get("story") and (not m.get("speech") or not m["speech"].get("kit")):
            from engine import voice_profile, voices         # who they are and where they come from, before anything is written about them
            voice_profile.ensure(m, random.Random(f"{self.store.meta.seed}:{m['id']}:speech"), voices.kits_in_party(self.player.party, m))   # (f350)
        if "details" not in m and m.get("permanent") and not m.get("story"):
            m["details"] = []                               # set first, so a failure is not retried on every line
            m["details"] = self.persona_details(m)
        return m

    def persona_details(self, m: dict) -> list[str]:
        """Five small, specific personal things about a hire, written once when they sign on, so they have something of their own to talk
        about that is the same every time. None if the model cannot write them within the rules."""
        if not getattr(config, "VOICED_MENTOR", True):
            return []
        from llm.contracts import PersonaDetails
        quirks.detail_subjects(m, random.Random(f"{self.store.meta.seed}:{m['id']}:details"))
        taken = [d for o in self.player.party if o is not m for d in (o.get("details") or [])]
        from engine import voice_profile
        home_names = re.findall(r"\b[A-Z][a-z]+", voice_profile.culture(m).get("home", ""))
        themes = quirks.secret_themes(m)
        try:
            r = generate("persona_details", quirks.Q["details_system"], quirks.details_request(m, None, taken), PersonaDetails, max_tokens=520, retries=1,
                         validation_context={"names": [m["name"].split()[0], m["name"].split()[-1]] + home_names, "secrets": len(themes)})
            if r.secrets:
                m["secrets"] = r.secrets
            if r.weights:
                m["detail_weights"] = r.weights
            return r.details
        except LLMError:
            return []

    def quirk_crew(self) -> list[dict]:
        if self.combat or self.player.delve:
            return []
        return [self.quirked(m) for m in self.player.party if m.get("permanent") and not m.get("story") and self.player.party_mode == "with"]

    def quirk_rng(self, salt: str = "") -> random.Random:
        return random.Random(f"{self.store.meta.seed}:{self.minutes}:{salt}")

    # ---------- the moments ----------

    def quirk_tick(self) -> None:
        """After every action: arriving somewhere new brings habits, a braggart's trouble, an errand, and a view on where you have come."""
        loc = self.player.location
        prev = getattr(self, "_quirk_loc", None)
        self._quirk_loc = loc
        if prev is None or prev == loc or self.combat or self.player.delve:
            return
        self.habits("arrival")
        self.flaws_on_arrival()
        from engine.domain_events import Visited
        self.notice(Visited(minute=self.minutes, place=loc, place_type=self.place.type))
        self.errands()

    def rest_quirks(self, sleeping: bool) -> None:
        """At the end of a rest: habits, the inn's cost, a late morning, something told, and Maren's small attentions."""
        self.habits("rest")
        from engine.domain_events import Rested
        self.notice(Rested(minute=self.minutes, place=self.player.location, inn=sleeping and self.place.type == "inn",
                           late=sleeping and clock.period(self.minutes) in ("midday", "afternoon", "evening"), slept=sleeping))
        self.flaws_at_rest(sleeping)
        self.secrets()
        self.mentor_rest_habit()

    # ---------- habits ----------

    def habits(self, when: str) -> None:
        """Each companion's habit, if this is its moment."""
        crew = [self.quirked(m) for m in self.player.party if m.get("permanent") and not m.get("story")] if when in ("fight_start", "fight_end") else self.quirk_crew()
        for m in crew:
            weapon = (rules.P["roles"].get(m["role"], {}).get("attacks") or ["blade"])[0]
            line = quirks.habit_line(m, when, self.quirk_rng(m["id"]), weapon=weapon, danger=bool(self.place.danger), day=clock.day(self.minutes),
                                     place_type=self.place.type)
            if line:
                console.narrate(line)

    # ---------- deeds ----------

    def deed(self, deed: str) -> None:
        """The player did something the companions might have a view on. Everyone with a view is affected (bond, memory); who of them says
        so is the director's (engine/party_director.py): often one, sometimes two who see it differently and answer each other, now and then
        all three. Several speakers are one exchange, one model call."""
        from engine import party_director as director
        day = clock.day(self.minutes)
        crew = self.quirk_crew()
        rng = self.quirk_rng(deed + ":react")
        stances = {m["id"]: how for m in crew for how in [quirks.reaction(m, deed, day, rng)] if how}
        if not stances:
            return
        text = quirks.Q["deeds"][deed]
        plan = director.plan(director.beat_from_deed(text, stances), crew, self.quirk_rng(deed + ":plan"), must_start=False)
        self.last_plan = plan
        speaking = set(plan.speaker_ids)
        for m in crew:                                       # feeling something is not saying it: everyone with a view is changed by it
            if m["id"] in stances:
                quirks.react(m, deed, stances[m["id"]], day, spoke=m["id"] in speaking)
        by_id = {m["id"]: m for m in crew}
        pick = [by_id[i] for i in plan.speaker_ids]
        if len(pick) > 1:
            sit = deed_situation(self, deed=text)
            wants = self.banter_wants(pick, "deed", None, "deed", stances)
            if self.talk_among(crew, pick, plan, sit, "deed", f"The player has just been {text}.", None, wants, "pressing"):
                self.store.save_player(self.player)
                return
        for m in pick:                                       # one speaker (or the exchange failed): each says it on their own
            how = stances[m["id"]]
            now = [f"the player has just been {text}, in front of you, and you {'approve' if how == 'approve' else 'do not approve'}; you say so in your own way, "
                   "without a speech about it"]
            said = self.companion_line(m, now, f"(the player was {text})")
            if not said:
                said = quirks.reaction_fallback(deed, how, self.quirk_rng(deed))
            self.companion_show(m, said, f"(the player was {text})")
            rules.said(m, said)
            self._hire_last = (m.get("name"), self.store.meta.turn)   # (f310) the party has had its say: no second round of banter this turn
        if pick:
            director.spoke(plan, by_id, self.minutes)
        self.store.save_player(self.player)

    def chime_in(self, m: dict, text: str, reply: str) -> None:
        """The player spoke to one companion with others listening. Whether any of the others joins in is the director's, on real reasons
        only: the words are about them, they concern the whole party, they are close to their own life, or they are heavy enough that
        everyone has a say. Often nobody does. Several who join are one exchange."""
        from engine import banter, party_director as director
        others = [o for o in self.quirk_crew() if o is not m]
        if not others:
            self.last_plan = None
            return
        named, party, weight = director.read_words(text, m["name"], reply, others)
        plan = director.plan(director.beat_from_words(text, m["id"], named, party, weight), others, self.quirk_rng("chime:" + text), must_start=False,
                             bystanders=[m])
        self.last_plan = plan
        if not plan.speaker_ids:
            return
        by_id = {o["id"]: o for o in others}
        pick = [by_id[i] for i in plan.speaker_ids]
        first = m["name"].split()[0]
        said = f'The player has just said to {first}: "{" ".join(text.split())}"' + (f' {first} answered: "{" ".join(reply.split())}"' if reply else "")
        if len(pick) > 1:
            sit = banter.B["banter"]["situation"]["said"].format(place=self.place.name, addressee=first)
            scene = "pressing" if weight == "heavy" else "ease"
            if self.talk_among([m] + others, pick, plan, sit, "said", said, None, {}, scene):
                self.store.save_player(self.player)
                return
        for o in pick:                                       # one joins (or the exchange failed): each says it on their own
            now = [f"{said}. You were listening, and you join in, speaking to {first} or the player, with "
                   f"something of your own: never {first}'s words again, or the same turn of phrase"]
            hit = self.hit_level(o, plan.beat, others)
            line = self.companion_line(o, now, text, hit=hit, weight=plan.beat.weight)
            if line:
                from engine import severity
                self.companion_show(o, line, text)
                if not severity.is_silent(line):
                    rules.said(o, line)
                severity.note_reaction(hit, severity.is_silent(line))
        director.spoke(plan, by_id, self.minutes)
        self.store.save_player(self.player)

    def gesturers(self, me: dict | None = None) -> list[dict]:
        """Everyone present whose gestures count against a new one: the hires travelling along, and Maren when she is with you."""
        out = [m for m in self.player.party if m.get("permanent") and m is not me]
        try:
            from engine import mentor
            if self.mentor_with_you() and self.player.mentor is not me:
                out.append({"name": mentor.NAME, "gestured": self.player.mentor.get("gestured", [])})
        except Exception:
            pass
        return out

    def companion_line(self, m: dict, now: list[str], heard: str, must: list[str] | None = None, retell: dict | None = None,
                       hit: str = "", in_fight: bool = False, weight: str = "") -> str:
        """One line from a companion about something that is happening, through the same path as talking to them. '' if the model fails."""
        if not getattr(config, "VOICED_MENTOR", True):
            return ""
        from engine import banter
        player = quirks.nickname(m) or self.player.character.name
        q = " ".join(now) + " " + heard
        from engine import voice_profile
        how, core = self.companion_parts(m, q, "pressing", relation=voice_profile.relation_kind(bond_tier=rules.bond_tier(m)), toward="the player",
                                         hit=hit, in_fight=in_fight)
        from engine import severity
        lately = [] if hit and severity.at_least(hit, severity.SV["repeat_free_from"]) else m.get("said", [])   # shaken or devastated: they may repeat themselves
        quiet = severity.may_be_silent(hit, weight) and not must        # hit hard enough, or a moment grave enough, that a word or nothing is an answer
        if quiet:
            how = (how + " " + " ".join(severity.SV["silent_rule"].split())).strip()
        view = self.hire_view(m)
        ctx = {"recent": lately, "member": m, "player": self.player.character.name, "must": must or [], "retell": retell, "silent_ok": quiet,
               "others": self.fellow_names(m), "said": heard if isinstance(heard, str) else "",                       # (f385)
               "gesture_state": quirks.gesture_state(m, self.gesturers(m)), "known": view.scene.known_words()}
        from engine import canon, context
        fix = ""
        for attempt in range(2):                             # the same rule as talking to them: a line that contradicts canon is written again
            try:
                r = generate("hire_chat", ppr.TALK_SYSTEM,
                             ppr.talk_prompt(how, core, self.hire_relation(m), now + self.hire_now(m, heard), rules.pick_memories(m, q, day=self.minutes // 1440),
                                             m.get("talk", [])[-4:], player, heard, unsaid=banter.unsaid_rule(lately, q),
                                             notes=quirks.voice_notes(m, solo=True), props=quirks.scene_props(m, self.place), leaned=quirks.leaned_on(m),
                                             offers=self.material_for(m), fix=fix, truth_text=view.text(), others=self.fellow_names(m)),
                             CompanionReply, temperature=0.85, max_tokens=config.PROSE_MAX_TOKENS, retries=1, validation_context=ctx, relaxed_context=dict(ctx, recent=lately[-1:]))
            except LLMError:
                return ""
            fix = canon.settle(canon.read(m, m["name"], r.speech, q, self.minutes // 1440), attempt)
            if fix:
                continue
            quirks.note_line(m, r.gesture)
            if r.speech:
                context.note_spoken(m, r.speech, self.minutes, self.companion_concerns(m))
                return quirks.shown(r.speech, r.gesture, m["name"])
            if quiet:                                        # no words: what their body does, or silence, is the answer
                return quirks.shown("", r.gesture, m["name"]) if r.gesture else severity.silent_line(m["name"])
            return ""
        return ""

    # ---------- flaws ----------

    def flaws_at_rest(self, sleeping: bool) -> None:
        """A drinker at an inn pays for it in the morning."""
        if self.place.type != "inn" or not sleeping:
            return
        F = quirks.Q["flaws"]["drinker"]
        for m in self.quirk_crew():
            if quirks.flaw(m) == "drinker" and self.quirk_rng("drink" + m["id"]).randrange(100) < F["chance"]:
                m["hungover_until"] = self.minutes + F["hours"] * 60
                console.narrate(F["line"].format(name=m["name"].split()[0], **quirks.pronouns(m)))
                rules.remember(m, clock.day(self.minutes), "I drank too much at the inn and was no use the next morning.", 1, key="drink")

    def flaws_on_arrival(self) -> None:
        """A braggart starts something in a room."""
        if self.place.type not in ("inn", "guild"):
            return
        F = quirks.Q["flaws"]["braggart"]
        day = clock.day(self.minutes)
        for m in self.quirk_crew():
            if quirks.flaw(m) != "braggart" or m.get("bragged_day") == day:
                continue
            if self.quirk_rng("brag" + m["id"]).randrange(100) >= F["chance"]:
                continue
            m["bragged_day"] = day
            c = self.player.character
            cost = min(F["cost"], c.coins)
            c.coins -= cost
            console.narrate(F["line"].format(name=m["name"].split()[0], cost=money.fmt(cost) if cost else "nothing, since you have nothing", **quirks.pronouns(m)))
            rules.remember(m, day, "I got into it with someone in a room and they paid to settle it.", 2, key="brag")
            self.store.save_player(self.player)

    def flaws_on_loot(self, coins: int) -> int:
        """Light fingers around a fresh take: the coin the player actually gets."""
        F = quirks.Q["flaws"]["pocket"]
        if coins < 20:
            return coins
        day = clock.day(self.minutes)
        for m in [self.quirked(x) for x in self.player.party if x.get("permanent") and not x.get("story")]:
            if quirks.flaw(m) != "pocket":
                continue
            rng = self.quirk_rng("pocket" + m["id"])
            if rng.randrange(100) >= F["chance"]:
                continue
            share = round(coins * rng.uniform(*F["share"]))
            if rng.randrange(100) < F["caught"]:
                console.narrate(F["line_caught"].format(name=m["name"].split()[0], **quirks.pronouns(m)))
                rules.remember(m, day, F["memory_caught"], 3)
                m["bond"] = m.get("bond", 0) - 1
            else:
                coins -= share
                m["pocketed"] = m.get("pocketed", 0) + share
                rules.remember(m, day, F["memory_quiet"], 2)
            break
        return coins

    # ---------- errands ----------

    def errand_here(self, m: dict, E: dict) -> bool:
        where = E.get("where")
        t = self.place.type
        if where == "guild":
            return t == "guild"
        if where == "shrine":
            return t in ("shrine", "temple")
        if where == "town_other":
            return t in ("city", "major", "rich") and self.player.location != rules.P.get("home", "parth") and self.player.location not in m.setdefault("seen_towns", []) \
                and self.player.location != "parth"
        if where == "anywhere":
            return not self.place.danger
        return False

    def errands(self) -> None:
        """On arriving somewhere: a companion who trusts you may ask their one small thing. The next thing you say answers them."""
        if getattr(self, "_errand", None):
            return
        day = clock.day(self.minutes)
        for m in self.quirk_crew():
            E = quirks.errand(m)
            if not E or m["quirks"].get("errand_day") == day or not self.errand_here(m, E):
                continue
            extra = {"sum": money.words(E["cost"])} if "cost" in E else {}
            ask = quirks.errand_text(m, "ask", **extra)
            console.say(ask, m["name"])
            rules.said(m, ask)
            m["quirks"]["errand_day"] = day
            self._errand = (m, E)
            console.note(f"[{m['name'].split()[0]} is asking something of you. Say yes, or no.]")
            self.store.save_player(self.player)
            return

    def errand_intercept(self, text: str) -> bool:
        """The player's answer to an errand just asked. True if the line was that answer."""
        pending = getattr(self, "_errand", None)
        if not pending:
            return False
        m, E = pending
        self._errand = None
        day = clock.day(self.minutes)
        extra = {"sum": money.words(E["cost"])} if "cost" in E else {}
        if is_answer(YES, text):
            c = self.player.character
            if "cost" in E:
                if c.coins < E["cost"]:
                    console.note(f"You cannot cover {money.fmt(E['cost'])}.")
                    console.say(quirks.errand_text(m, "no_line", **extra).replace(m["name"].split()[0] + " ", "", 1), m["name"])
                    m["quirks"]["errand"] = "no"
                    rules.remember(m, day, quirks.errand_text(m, "memory_no", **extra), 2)
                    self.store.save_player(self.player)
                    return True
                c.coins -= E["cost"]
            if E.get("minutes"):
                self.advance_quiet(E["minutes"])
            console.narrate(quirks.errand_text(m, "yes_line", **extra))
            m["quirks"]["errand"] = "yes"
            m["bond"] = m.get("bond", 0) + 3
            rules.remember(m, day, quirks.errand_text(m, "memory_yes", **extra), 3)
            if E.get("where") == "town_other":
                m.setdefault("seen_towns", []).append(self.player.location)
            self.store.save_player(self.player)
            return True
        if is_answer(NO, text):
            console.narrate(quirks.errand_text(m, "no_line", **extra))
            m["quirks"]["errand"] = "no"
            m["bond"] = m.get("bond", 0) - 1
            rules.remember(m, day, quirks.errand_text(m, "memory_no", **extra), 3)
            self.store.save_player(self.player)
            return True
        return False                                        # something else: the ask stands unanswered and they let it lie for today

    # ---------- secrets ----------

    def secrets(self) -> None:
        """At a rest: a companion who has come to trust you tells you something, once."""
        for m in self.quirk_crew():
            s = quirks.secret_due(m)
            if not s:
                continue
            others = list(m.get("secrets") or []) + list(m.get("details") or [])     # it must be this secret, not another thing of theirs
            said = self.companion_line(m, [f"you have decided to tell the player this, now, in your own words, keeping its meaning: {s}"], "(a quiet moment)",
                                       retell={"text": s, "others": others})
            self.companion_show(m, said or s, "(a quiet moment)")
            rules.said(m, said or s)
            quirks.told(m, clock.day(self.minutes), s)
            self.store.save_player(self.player)
            return

    # ---------- Maren ----------

    def mentor_rest_habit(self) -> None:
        if not self.mentor_with_you() or self.combat or self.quirk_rng("maren").randrange(100) >= 50:
            return
        console.narrate(self.quirk_rng("maren-line").choice(quirks.Q["maren"]["rest_habits"]))

    def mentor_opening(self, beat: str) -> tuple[str, str, list[str]]:
        """(fact for the model, line for the fallback, words that must survive) for one of her beats; ('', '', []) if already told."""
        O = (quirks.Q["maren"].get("opening") or {}).get(beat)      # (f289) none now: she says these things only when asked
        told = self.player.mentor.setdefault("opened", [])
        if not O or beat in told:
            return "", "", []
        told.append(beat)
        return O["fact"], O["line"], quirks.must_words(O["line"], 1)
