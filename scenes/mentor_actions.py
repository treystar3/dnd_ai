"""The mentor in play: she comes over in Parth, finds out what you know of the guild, takes the player on a first contract, teaches
tracking and the fight, can be talked to throughout, and a troll that should not be there turns up. The rules and the state are in
engine/mentor.py; the fixed words are in data/world/mentor.yaml. Her free answers come from the model with a locked fact sheet, so
she can't invent a rule. The first hunt can't be lost: the player's health holds at 1."""
from engine import entities
from engine import combat, encounters, inventory, mentor, money, pools, voice_rules
import config
import re
from llm.contracts import MentorLines, MentorReply, MentorSpeech
from llm.gateway import LLMError, generate
from ui import console

JOIN_WORDS = re.compile(r"\b(fee|pay|sign|register|join|enrol|enroll|silver|coin|coins)\b")      # at the clerk's desk, the player's business

M = mentor.M
NAME = mentor.NAME


class MentorActions:
    from scenes.intercepts import Intercept as _I
    INTERCEPTS = (_I("mentor_intercept", 20, "mentor_intercept", "her stepping in on a newcomer's first move in Parth"),
                  _I("mentor_quoted", 60, "mentor_quoted_turn", "a line wholly in quotes with her beside you"),
                  _I("mentor_named", 70, "mentor_named_turn", "her name in the line and no action in it, or a question"),
                  _I("mentor_hunt", 90, "mentor_go_hunt", "setting out for the hunt with her"))

    def mentor_view(self, text: str = ""):
        """Her view of the moment from the truth layer (engine/truth.py, f315): the same scene everyone reads, as she may know it - Parth's
        people by name, the board as it is, what the town has and lacks."""
        from engine import truth
        view = truth.scene_of(self).view(truth.MAREN, "maren").asking(text)                  # (f375) the streets when asked
        console.debug("truth view for Maren: " + ", ".join(f"{h.split(' (')[0].lower()} {len(l)}" for h, l in view.sections()))
        return view

    def mentor_label(self) -> str:
        """What her lines are shown under: her name once she has given it, and until then what you can see of her (f273)."""
        return NAME if self.player.mentor.get("introduced") else M["unnamed"]

    def mentor_show(self, speech: str, reply_to: str = "", gesture: str = "") -> None:
        """Her words on the page the way anyone else's are (f274): the narrator frames them with what she is doing as she speaks, a
        sentence or two before and after (scenes/world.py narrate_dialogue), under her label. Without the narrator, the words alone.
        (f374) Like anyone else's, a frame is the exception (f347): her first words, the first in each stage of the lesson in each place,
        and the first once she has stopped weighing a stranger. The first playthrough framed every line she said, thirty frames in half
        an hour, and her hands went to the pommel and her weight shifted in a third of them."""
        label = self.mentor_label()
        speech = speech.strip()
        introduced = bool(self.player.mentor.get("introduced"))
        moment = f"maren:{mentor.stage(self.player) or 'meeting'}:{introduced}"
        narrated = getattr(config, "NARRATED_DIALOGUE", True) and getattr(config, "VOICED_MENTOR", True) and not self.combat
        if narrated and moment in self.__dict__.setdefault("_framed_here", set()):         # (a new place clears it: scenes/world.py enter)
            g = voice_rules.short_gesture(gesture or "")
            console.npc_says(label, speech, g)
            self.remember_narration(f'{label}: "{speech}"', {"type": "says", "speaker": label, "speech": speech, "gesture": g})
            return
        if narrated:
            self._framed_here.add(moment)
            from llm.contracts import DialogueFrame
            from scenes import world_prompts as wp
            from scenes.voice import fresh
            looks = M["frame"]["looks"]
            manner = M["frame"]["manner_warm"] if introduced else M["frame"]["manner_cold"]
            doing = M["frame"]["doing"].get(mentor.stage(self.player) or "meeting", M["frame"]["doing"]["meeting"])
            others = [f"{self.seen_as(n)}: {n.activity}" for n in self.present][:5]
            from engine import reach                         # (f344) her own gear and the place's things; tense while she weighs a stranger
            within = reach.within("", self.place.type, carries=M["frame"].get("carries", []))
            moment = reach.moment(wary="" if introduced else M["frame"].get("wary", "she does not yet know whether the stranger is a bandit"),
                                  fight=bool(self.combat))
            try:
                frame = fresh("dialogue_frame", wp.DIALOGUE_SYSTEM,
                              wp.dialogue_request(self.time_label(), self.place, others, label, looks, doing, manner, not introduced,
                                                  reply_to or "(listening)", speech, gesture, False, self.recent_narration, M["frame"]["shows"],
                                                  reach=within, moment=moment, already=self.shown_lines(),
                                                  why=["the first words between them" if not introduced else "a moment of her walking the player through the guild"],
                                                  who_is=entities.who_is_who(self, also=["maren"])),       # (f392)
                              DialogueFrame, self.recent_narration, fields=("before", "after"), max_tokens=config.PROSE_MAX_TOKENS,
                              context={"speaker": [mentor.NAME, label, "the woman", "she"], "others": self.other_names(mentor.NAME)})
                before, after = frame.before, frame.after
                if not introduced:                            # she has not given her name: the frame must not either
                    before, after = (re.sub(r"\bMaren( Holt)?\b", "the woman", x) for x in (before, after))
                console.dialogue(before, label, speech, after)
                self.remember_narration(" ".join(t for t in (before, after) if t.strip()),
                                        {"type": "dialogue", "before": before, "speaker": label, "speech": speech, "after": after})
                return
            except LLMError:
                pass
        console.say(speech, label)

    def mentor_say(self, *parts, beat: str = "", reply_to: str = "") -> None:
        """Everything she says without being interrupted, as one block under one name: a line, a list of lines, or several of either.
        What she says is written for her; the model puts it in her own words for the moment, inside the limits the engine checks.
        Lines marked Fixed (the guild's rules and figures) and very short ones are said exactly as written."""
        out = []
        for part in parts:
            for x in ([part] if isinstance(part, str) else list(part)):
                if x and str(x).strip():
                    out.append((str(x), isinstance(part, mentor.Fixed) or len(str(x).split()) < 5))
        if not out:
            return
        if getattr(config, "FREE_MENTOR", True) and not any(isinstance(part, mentor.Fixed) for part in parts) and sum(len(x.split()) for x, _ in out) >= 12:
            lines = [x for x, _ in out]
            keep = list(dict.fromkeys(re.findall(r"#\w+", " ".join(lines)) + re.findall(r"(?<![A-Za-z])'([^']{3,60})'(?![A-Za-z])", " ".join(lines))))
            if self.mentor_speak(lines, beat, must=keep, reply_to=reply_to):          # (f375) as many paragraphs, as long, as she needs
                return
        source = [x for x, fixed in out if not fixed]
        reply, voiced = self.mentor_voice(source, beat, reply_to) if source else ("", None)
        said, n = ([reply] if reply and voiced is not None else []), 0
        for x, fixed in out:
            if fixed or voiced is None:
                said.append(x)
            else:
                said.append(voiced[n])
                n += 1
        self.mentor_show("\n".join(said), reply_to)
        mentor.remember_said(self.player, " ".join(said))

    def mentor_speak(self, points: list[str], beat: str, must=(), reply_to: str = "", ends: str = "", ends_question: bool = False,
                     ranks=None) -> bool:
        """She says this in her own paragraphs, not line by line: the points are what to cover, the must lines are said word for word, and
        the engine checks the facts. True if the model's speech was used; False means nothing was said and the written lines should be."""
        if not getattr(config, "VOICED_MENTOR", True):
            return False
        points = [str(x) for x in points if x and str(x).strip()]
        try:
            r = generate("mentor_speech", mentor.speech_system(self.player),
                         mentor.speech_request(self.player, self.place.name, beat, points, list(must), (reply_to or "").strip(), ends),
                         MentorSpeech, temperature=0.8, max_tokens=config.PROSE_MAX_TOKENS, retries=1,
                         validation_context={"material": points, "must": list(must), "ends_question": ends_question, "ranks": ranks})
        except LLMError:
            return False
        self.mentor_show("\n\n".join(r.paragraphs), reply_to)
        mentor.remember_said(self.player, " ".join(r.paragraphs))
        return True

    def mentor_voice(self, source: list[str], beat: str, reply_to: str = "") -> tuple[str, list[str] | None]:
        """(her answer to what the player just said, the written lines in her words), or ("", None) to say them as written (a failed or
        refused answer never stops the scene)."""
        if not getattr(config, "VOICED_MENTOR", True):
            return "", None
        reply_to = (reply_to or "").strip()
        try:
            r = generate("mentor_voice", mentor.voice_system(self.player),
                         mentor.voice_request(self.player, self.place.name, beat, source, reply_to),
                         MentorLines, temperature=0.8, max_tokens=config.PROSE_MAX_TOKENS, retries=1,
                         validation_context={"source": source, "want_reply": bool(reply_to)})
        except LLMError:
            return "", None
        return (r.reply if reply_to else ""), r.lines

    def mentor_settle(self) -> None:
        """The tutorial is over: she keeps a record as a person of the world who remembers the player, and (f382) leaves Parth on the work
        the capital sent her to do; she is in no place, and the town hears she has gone."""
        if self.store.npc_exists("maren"):
            return
        hall = next((p.id for p in self.world.places.values() if p.type == "guild" and p.parent == M["gate"]["place"]), None) or self.player.location
        npc = mentor.make_npc(self.player, self.minutes, self.store.meta.turn, hall)
        self.store.save_npc(npc)
        mentor.moved_on(self.store, self.world, npc, self.minutes)

    def mentor_journal_entry(self):
        """While the lesson runs she is not yet a person of the world, but you know her name, so the journal has her: (town, entry) or None."""
        if mentor.stage(self.player) not in ("invite", "sign", "board", "hunt", "harvest") or self.store.npc_exists("maren"):
            return None
        from engine import pulse
        town = pulse.town_of(self.world, M["gate"]["place"])
        return town, {"name": mentor.NAME, "role": "A-rank adventurer", "place": self.where_name(town) if town else "", "line": M["journal_line"]}

    def mentor_look(self, interrupt: bool, said: str = "") -> None:
        """She notices the player and crosses to them. The narrator describes it from the facts about her; if the model fails or leaves out what
        matters (the sword, the crest), the written passage is used instead."""
        A = M["approach"]
        text = ""
        if getattr(config, "VOICED_MENTOR", True):
            from llm.contracts import Narration
            from scenes import world_prompts as wp
            from scenes.voice import fresh
            event = A["look_event"] + (" " + A["look_interrupt"] if interrupt else "")
            try:
                self.flush(self.last_text)
                r = fresh("narrate", wp.NARRATOR_SYSTEM,
                          wp.narration_request(self.time_label(), self.place, self.people_view(), event, (said or "").strip(), self.recent_narration, self.gear_line(),
                                               self.store.load_place(self.player.location).marks),
                          Narration, self.recent_narration)
                text = r.text.strip()
            except LLMError:
                text = ""
            low = text.lower()
            if not (text and "greatsword" in low and ("crest" in low or "badge" in low) and " a " in f" {low} " and "maren" not in low):
                text = ""
        if text:
            self.mentor_narrate(text)
            self.remember_narration(text)
            return
        self.mentor_narrate(A["narrate"])
        if interrupt:
            console.narrate(A["interrupt"])

    def mentor_person(self):
        """She as one of the people here while the lesson runs (she is not an NPC of the world yet): (label, description, what she is doing) or None."""
        if not self.mentor_with_you() or self.combat:
            return None
        at_table = mentor.stage(self.player) in ("invite", "sign", "board")
        return (mentor.NAME, "(human) A broad-shouldered woman in her middle years in dark plate with gold detailing and a greatsword on her back, "
                             "an A-rank adventurer. Manner: warm and wry, self-assured, observant, gently teasing, with an obvious soft spot for newcomers.",
                "waiting at her table in the guild town" if at_table else "travelling with the player, keeping watch beside them")

    def mentor_in_party(self) -> bool:
        return any(m.get("story") == "maren" for m in self.player.party)

    def mentor_join_party(self, how: str = "") -> None:
        """She is in the party for the whole hunt, free. She sits out the wolves and fights in the troll fight after the first round."""
        if self.mentor_in_party():
            return
        lvl = max(1, self.player.character.level)
        self.party_service.join({"id": "npc_maren", "name": mentor.NAME, "role": "fighter", "level": M["troll_sheet"]["level_mentor"], "rank": "A", "blurb": "Maren Holt, an A-rank adventurer",
                                 "story": "maren", "tutorial": True, "free": True}, how="story")
        self.store.save_player(self.player)
        console.note(how or f"{mentor.NAME} joins your party. (Free: she is showing you how it works.)")

    def mentor_leave_party(self) -> None:
        if self.mentor_in_party():
            self.party_service.dismiss([m for m in self.player.party if m.get("story") == "maren"], how="home")
            self.store.save_player(self.player)

    def mentor_hire(self, text: str) -> bool:
        """'Hire Maren' at the guild hall, as practice: it costs nothing. True if this line was that."""
        import re
        if mentor.stage(self.player) not in ("board", "hunt") or self.combat or self.mentor_in_party():
            return False
        low = text.lower()
        if not re.search(r"\b(hire|recruit|take on|sign up|join (me|my party)|come with me|bring)\b", low):
            return False
        if not (mentor.named(text) or re.search(r"\b(you|me)\b", low)):
            return False
        self.mentor_join_party("You hire Maren Holt, free of charge. She joins your party.")
        taken = "they have already taken the wolf hunt from the board, so there is nothing left to take" if mentor.has_contract(self.player) else "they have not yet taken the wolf hunt from the board"
        self.mentor_say(M["board_step"]["hired"], beat=f"the player has hired you as practice for how hiring works, and you are in their party for the hunt; {taken}")
        return True

    def mentor_narrate(self, text: str) -> None:
        """Scene text written in several paragraphs: each is narrated on its own, so the window spaces them like any other passage."""
        for para in str(text).strip().split("\n"):
            if para.strip():
                console.narrate(para.strip())

    def mentor_in_town(self) -> bool:
        p = self.place
        parent = p.parent
        return not self.combat and not self.player.delve and not p.danger and (p.id == M["gate"]["place"] or parent == M["gate"]["place"])

    def mentor_with_you(self) -> bool:
        """Is she close enough to talk to? On the road with you, or at her table in Parth while she waits for you to join."""
        st = mentor.stage(self.player)
        if self.player.delve:
            return False
        if st in ("hunt", "harvest"):
            return True
        return st in ("invite", "sign", "board") and (self.combat is None) and self.mentor_in_town()

    def mentor_seed(self):
        return self.store.meta.seed

    # ---------- talking to her ----------

    def mentor_talk(self, text: str) -> bool:
        """Anything the player says to her: the model answers as Maren from the engine's fact sheet. True if what they said meant they are
        ready to move on (the model's reading of it)."""
        text = (text or "").strip()
        reply, moves_on = "", False
        from engine import banter, quirks
        mine = [t for w, t in self.player.mentor.get("chat", []) if w == "Maren"]
        pm = self.player.mentor
        gesture = ""
        from engine import convo
        before = convo.find(pm, text)
        manner = "wryly; you are never unkind about anything painful"
        fix = ""
        view = self.mentor_view(text)
        for attempt in range(2):
            ctx = {"recent": convo.others_lately(mine, before), "gesture_state": quirks.gesture_state(pm, self.gesturers(pm)), "known": view.scene.known_words()}
            try:
                r = generate("mentor_chat", mentor.chat_system(),
                             mentor.chat_prompt(self.player, self.place.name, text, self.mentor_fight_facts(),
                                                unsaid=banter.unsaid_rule(mine, text) if not before else "",
                                                props=quirks.scene_props(None, self.place), leaned=quirks.leaned_on(pm),
                                                again=convo.again_fact(before) if before else "",
                                                again_how=convo.again_rule(manner) if before else "", fix=fix, truth_text=view.text()),
                             MentorReply, temperature=0.8, max_tokens=config.PROSE_MAX_TOKENS, validation_context=ctx, relaxed_context=dict(ctx, recent=[] if before else mine[-1:]))
            except LLMError:
                topic = mentor.pick_topic(text)
                if topic:
                    reply = " ".join(mentor.topic_text(topic))
                break
            from engine import canon
            fix = canon.settle(mentor.read_claims(self.player, r.speech, text, self.minutes // 1440), attempt) or mentor.check_figures(text, r.speech)
            console.debug(f"talk -> Maren (stage {mentor.stage(self.player)!r}): moves_on={r.moves_on} topics={sorted(mentor.topics_in(text))}" + (f" redraft: {fix}" if fix else ""))
            if fix:
                if attempt == 1 and mentor.check_figures(text, r.speech):      # a rule she keeps getting wrong: the rule itself, as written
                    reply = " ".join(mentor.topic_text(mentor.pick_topic(text)))
                    break
                continue
            reply, gesture, moves_on = r.speech, r.gesture, r.moves_on
            break
        if reply:
            convo.record(pm, text, reply, self.minutes)
        reply = reply or M["chat"]["fallback"]
        self.mentor_show(reply, text, quirks.bare_gesture(" ".join((gesture or "").split()).rstrip("."), NAME))
        quirks.note_line(pm, gesture)
        mentor.remember_chat(self.player, text, reply)
        self.store.save_player(self.player)
        return bool(moves_on)

    def mentor_fight_facts(self) -> str:
        """Who is in the fight and what is on them, so she can answer 'what does burning do?' about the thing the player is looking at."""
        if not self.combat:
            return ""
        f = self.combat.fight
        def line(x):
            states = ", ".join(f"{k} ({v} more rounds)" if v < 99 else k for k, v in x.statuses.items())
            return f"{x.name} ({combat.condition(x)}{', ' + states if states else ''})"
        foes = "; ".join(line(e) for e in f.fighters if e.side == "enemy" and e.alive) or "none left"
        return f"round {f.round}. You: {line(f.player)}. Enemies: {foes}."

    def mentor_wants_talk(self, intent, text: str) -> bool:
        """Is this line, said as talk, meant for her? Yes unless it plainly goes to someone else who is here."""
        if not self.mentor_with_you():
            return False
        if mentor.named(text):
            return True
        target = intent.target if intent.target not in ("", "none", "null") else ""
        npc = next((n for n in self.present if n.id == target), None) if target else None
        if npc and mentor.addresses(text, npc):               # they said who they mean
            return False
        return not self.partner or bool(self.player.mentor.get("last_voice"))   # otherwise, with her beside them, it is her they are talking to

    # ---------- the steps ----------

    def mentor_tick(self) -> None:
        """After every action: has the next step come due?"""
        st = mentor.stage(self.player)
        if st == "done" or self.combat or self.player.delve:
            return
        m = self.player.mentor
        here = self.player.location
        if not st:
            return                                         # she stops them on their first action in town, not on arrival: see mentor_intercept
        if st == "invite":
            if self.rank and not self.partner and self.mentor_in_town():
                self.mentor_joined()
            return
        if st == "sign":                                     # at the clerk's desk with her: signed in, she goes on; walked out, she waits in town
            if self.rank:
                self.mentor_joined(announce=False, lead=M["joined"]["speech"][0])
            elif self.place.type != "guild":
                self._mentor_wait(M["approach"])
            return
        if st == "board":
            if mentor.has_contract(self.player):
                self.mentor_taken()
            elif self.mentor_in_town() and not self.partner:
                m["waited"] = m.get("waited", 0) + 1
                if m["waited"] % 4 == 0:
                    self.mentor_say(mentor.line_from(self.player, M["board_step"]["waiting"]), beat="the player has not yet taken the wolf hunt from the board; nudge them to do so")
            return
        if st == "harvest":
            if self.mentor_in_town() and not self.partner:
                self.mentor_return()
            return
        if st == "hunt" and here == M["hunt"]["place"] and not m.get("briefed") and not m.get("found"):
            self.mentor_brief()

    def mentor_intercept(self, text: str) -> bool:
        """The first thing the player does in Parth: she steps into their path and whatever they meant to do waits. True if she did."""
        if text.lstrip().startswith(("#", "/")) or self.combat or self.player.delve or mentor.stage(self.player):
            return False
        if self.partner or not self.mentor_in_town() or not mentor.may_appear(self.player, self.minutes, self.player.location, self.place.parent):
            return False
        self.mentor_approach(interrupt=True, said=text)
        return True

    def mentor_approach(self, interrupt: bool = False, said: str = "") -> None:
        A = M["approach"]
        GT = M["guild_talk"]
        c = self.player.character
        self.mentor_look(interrupt, said)
        self.mentor_say(A["ask_first"], beat="you have just walked up to an armed stranger with no guild badge, and you ask what brings them to Parth", )                     # her first words are spoken, in her colour, under her name
        answer = (console.ask() or "").strip()               # she asks what brings them to Parth; whatever they say, she carries on
        if answer:
            mentor.remember_chat(self.player, answer, "")
        from engine import items
        weapon = c.equipment.get("main_hand")
        if weapon:
            weapon_line = mentor.text(A["weapon_line"]).format(weapon=items.base_of(weapon).name.lower())     # "a lute", not "a crude ash lute"
        else:
            weapon_line = mentor.text(A["no_weapon_line"])
        wname = items.base_of(weapon).name.lower() if weapon else ""
        gear = A["info_weapon"].format(weapon=wname) if weapon else A["info_no_weapon"]
        # she sizes them up (f273): whatever they said, an armed stranger with no badge gets her cold, pointed question first; only the answer
        # to that settles her. An evasive or hostile answer is pressed once more; then she makes up her mind
        beat_p = "you are sizing up an armed stranger; you are cold and guarded, giving nothing away, and whatever they said about why they are in Parth has not yet shown you whether they are a bandit"
        probe = [gear, *(A["info_probe_badged"] if self.rank else A["info_probe_unbadged"])]
        if not self.mentor_speak(probe, beat_p, reply_to=answer, ends_question=True, ends="the last paragraph asks the one pointed question"):
            self.mentor_say(A["speech_unbadged"][2:4] if not self.rank else A["speech_badged"], "So tell me: where did you come by that, and what do you do for a living?", reply_to=answer, beat=beat_p)
        proof = (console.ask() or "").strip()
        if proof:
            mentor.remember_chat(self.player, proof, "")
        for _ in range(3):                                    # a question back, a hostile word or nothing at all is no answer: still cold, she presses (f279)
            if mentor.is_question(proof):
                beat_q = "the stranger answered your question with a question of their own; you are still cold: give them a word or two, no name and nothing about yourself, and put your question to them again"
                if not self.mentor_speak(A["info_probe_question"], beat_q, reply_to=proof, ends_question=True, ends="the last paragraph puts your question again"):
                    self.mentor_say("Someone who asks the questions in this town. I asked first: where did you come by that, and what do you do?", beat=beat_q, reply_to=proof)
            elif self.mentor_read(proof)[1] or not proof:
                beat_q = "the stranger's answer did not settle you; still cold, press them once more"
                if not self.mentor_speak(A["info_probe_again"], beat_q, reply_to=proof, ends_question=True, ends="the last paragraph presses them once more"):
                    self.mentor_say("That is not much of an answer. Are you a bandit, or not?", beat=beat_q, reply_to=proof)
            else:
                break
            proof = (console.ask() or "").strip()
            if proof:
                mentor.remember_chat(self.player, proof, "")
        beat_a = ("the stranger has answered you and you are satisfied they are no bandit; the cold goes out of you, you react to what they said with your dry warmth, introduce yourself, and ask how well they know the guild")
        info = [*(A["info_thaw_badged"] if self.rank else A["info_thaw_unbadged"]), A["info_ask_know"]]
        self.player.mentor["introduced"] = True                 # from here her lines carry her name (f273)
        if not self.mentor_speak(info, beat_a, reply_to=proof, ends_question=True, ends="the last paragraph asks how well they know the guild (its ranks and the contract board)"):
            intro = [line.format(weapon_line=weapon_line) for line in A["speech_intro"] if line.strip() != "{weapon_line}" or weapon_line]
            badge = A["speech_badged"] if self.rank else A["speech_unbadged"]
            self.mentor_say(intro, badge, A["ask_know"], reply_to=proof, beat=beat_a)
        know = (console.ask() or "").strip()
        mentor.remember_chat(self.player, know, "") if know else None
        if mentor.says_yes(know):
            self.mentor_say(A["ask_sure"], beat="they say they know the guild; you check once more", reply_to=know)
            sure = (console.ask() or "").strip()
            mentor.remember_chat(self.player, sure, "") if sure else None
            if mentor.says_yes(sure):
                self.mentor_say(A["skip_leave"], beat="they know the guild, so you wish them well and leave them to it", reply_to=sure)
                self.mentor_narrate(A["skip_narrate"])
                self.player.mentor["skipped"] = True
                mentor.set_stage(self.player, "done")
                self.store.save_player(self.player)
                return
        # the guild, a piece at a time, as a conversation: she says a part, they answer, she goes on
        if not self.mentor_lecture(know):                     # the lesson ran its course: she waits for them to ask, or to make a move (f276)
            tries = 0
            while tries < 8:
                tries += 1
                text = console.ask()
                if mentor.wants_to_go_on(text):
                    break
                if self.mentor_talk(text):                  # she answers in her own voice (f270); if what they said meant 'let's go', they go
                    break
        self.mentor_escort()

    HOSTILE = r"\b(i am|i'm|im|yes)\b.*\bbandit|\brob(bed|bing)?\b|\bkill you\b|\bmind your own\b|\bnone of your\b|\bsteal|\bthreat|\bshut up\b|\bget lost\b|\bback off\b"

    def mentor_read(self, said: str) -> tuple[bool, bool]:
        """(settled, hostile): does what the stranger said put her at ease, and is it hostile. The model reads it; if it cannot, a plain
        fallback: hostile words are hostile, a word or two is not an answer, anything else settles her."""
        said = (said or "").strip()
        if not said:
            return False, False
        if getattr(config, "VOICED_MENTOR", True):
            from llm.contracts import StrangerRead
            try:
                r = generate("stranger_read", M["approach"]["read_system"], f'MAREN ASKED: what brings you to Parth, and what do you do?\nTHE STRANGER SAID: "{said[:300]}"',
                             StrangerRead, temperature=0.1, max_tokens=60, retries=1)
                return (r.settled and not r.hostile), r.hostile
            except LLMError:
                pass
        hostile = bool(re.search(self.HOSTILE, said.lower()))
        return (not hostile and len(said.split()) > 2), hostile

    def mentor_chunk(self, facts: list, beat: str, must: list, reply_to: str, ends: str = "", ranks=None) -> str:
        """One piece of the lecture, in her words, and the player's answer to it (which she answers if it is a question). The ranks are
        checked rank by rank (engine/mentor.py check_speech ranks:) rather than recited word for word (f275)."""
        flat = [str(x) for part in facts for x in ([part] if isinstance(part, str) else part) if str(x).strip()]
        if not self.mentor_speak(flat, beat, must=must, reply_to=reply_to, ends=ends, ranks=ranks):
            self.mentor_say(*facts, reply_to=reply_to, beat=beat)
        text = (console.ask() or "").strip()
        if text:
            mentor.remember_chat(self.player, text, "")
        return text

    def mentor_lecture(self, know: str) -> bool:
        """The guild, a piece at a time. True if the player cut it short by making a move (heading for the hall, saying let's go): the
        rest is left unsaid and she goes with them (f276)."""
        A = M["approach"]
        reply = know
        steps = [
            ([*A["info_chunk_ranks"], A["lesson_ranks"]], "you tell a newcomer, warmly, how the guild's ranks go", [],
             A["info_chunk_after"]),
        ]                                                   # (f302) the board is shown at the hall itself (board_step), not lectured on in the street
        for k, (facts, beat, must, ends) in enumerate(steps):      # (f294) joining is no lesson of its own: she takes them to sign in
            text = self.mentor_chunk(facts, beat, must, reply, ends)
            reply = ""
            if mentor.wants_to_go_on(text):
                continue
            if mentor.is_question(text):                    # a question is answered before she goes on (f270)
                if self.mentor_talk(text):
                    return True
            else:                                           # anything else (a nod, a remark, a move) is answered inside the next piece (f276)
                reply = text
                if self.mentor_talk_means_go(text):
                    return True
        fee = money.words(mentor.G["joining_fee"])
        flat = [x.format(fee=fee) for x in (A["info_chunk_end"] if not self.rank else A["info_chunk_end_member"])]
        if not self.mentor_speak(flat, "you have finished explaining the guild; you will take them to the hall and help them get registered, and they may ask you anything first",
                                 must=[fee] if not self.rank else [], reply_to=reply,
                                 ends="invites questions; it does not tell them what to say or type"):
            self.mentor_say(M["guild_talk"]["ask_anything"].format(fee=fee) if not self.rank else flat, beat="you have finished explaining the guild and will take them to the hall", reply_to=reply)
        return False

    def mentor_talk_means_go(self, text: str) -> bool:
        """Does this line, said while she is explaining the guild, mean they are making for the hall or ready to go? The model reads it
        (MentorReply.moves_on) without her answering; plainly going words settle it without the model."""
        import re as _re
        low = (text or "").lower()
        if _re.search(r"\b(head|go|walk|step|let'?s go|lets go|get going|i'?m ready|lead the way|take me)\b", low) and \
                _re.search(r"\b(inside|in|hall|guild|clerk|register|sign|on|go)\b", low):
            return True
        if not getattr(config, "VOICED_MENTOR", True) or len(low.split()) < 3:
            return False
        try:
            r = generate("mentor_chat", mentor.chat_system(), mentor.chat_prompt(self.player, self.place.name, text), MentorReply,
                         temperature=0.2, max_tokens=120, retries=0)
            return bool(r.moves_on)
        except LLMError:
            return False

    def mentor_escort(self) -> None:
        """She walks them to the guild hall herself, sees them signed into the register, and shows them the board there."""
        from llm.contracts import ActionIntent
        E = M["escort"]
        A = M["approach"]
        G = mentor.G
        was_member = bool(self.rank)
        self.mentor_say(E["member_say"] if was_member else E["say"], beat="you say you will walk them to the guild hall yourself")
        hall = next((p.id for p in self.world.places.values() if p.type == "guild" and p.parent == M["gate"]["place"]), None)
        found = self.world.path(self.player.location, hall) if hall else None
        if not found:
            self._mentor_wait(A)
            return
        console.narrate(E["walk"].strip())
        self.advance_quiet(max(1, found[1]))
        self.enter(hall)
        self.narrate(f"The player walks into {self.place.name} with Maren Holt, a broad woman in plate with a greatsword on her back, at their "
                     "side. Describe the hall and the people in it. Maren does not speak in this passage.")
        if not self.rank:
            if not self.clerk_here():
                self.mentor_say(E["closed"], beat="the guild hall clerk is not in, so you tell them to come back when it is open and sign in then")
                self._mentor_wait(A, say=False)
                return
            if self.player.character.coins < G["joining_fee"]:
                self.mentor_say(E["short"], beat="they cannot afford the joining fee, so you tell them to earn it and come back")
                self._mentor_wait(A, say=False)
                return
            clerk = self.clerk_here()
            self.mentor_clerk_exchange(clerk)
            from engine import banter as _bn
            manner = {"warm": "the clerk was kind to them", "cold": "the clerk was cold and rude to them and you put the clerk in their place",
                      "neutral": "the clerk was businesslike"}[_bn.manner(clerk)]
            fee = money.words(G["joining_fee"])
            beat = f"{manner}; now the register is out and you turn to the newcomer: it is their turn to pay the fee of {fee} and sign, and they may ask you anything first"
            if not self.mentor_speak([E["your_turn"].format(fee=fee)], beat, must=[fee]):
                self.mentor_say(E["your_turn"].format(fee=fee), beat=beat)
            mentor.set_stage(self.player, "sign")         # (f271) the player pays and signs themselves, or asks first; mentor_tick carries on
            self.store.save_player(self.player)
            return
        self.mentor_joined(announce=False, lead=[] if was_member else M["joined"]["speech"][0])

    def _mentor_wait(self, A, say: bool = True) -> None:
        """Could not do it today: she says where to go and waits in town."""
        if say:
            self.mentor_say(A["close"], beat="you tell them where to go to sign in at the guild hall, and that you will wait")
        console.narrate(A["leave"])
        mentor.set_stage(self.player, "invite")
        self.store.save_player(self.player)

    def mentor_quoted_turn(self, text: str) -> bool:
        """A line wholly in quotes, with her beside them, is said to her - unless, at the clerk's desk, it is about the fee: that is the clerk's."""
        said = text.strip()
        if not (self.mentor_with_you() and not self.partner and len(said) > 2 and said[0] in "\"\u201c" and said[-1] in "\"\u201d"
                and said.count(chr(34)) + said.count("\u201c") + said.count("\u201d") == 2):
            return False
        if mentor.stage(self.player) == "sign" and JOIN_WORDS.search(said.lower()):
            return False
        from engine import clock
        self.advance(clock.TALK_MINUTES)
        self.mentor_talk(said[1:-1].strip())
        return True

    def mentor_named_turn(self, text: str) -> bool:
        """Her name in the line and no action in it (or a question): said to her. An action with her name in it is an action."""
        low = text.strip().lower()
        from engine import actions as _actions
        if not (self.mentor_with_you() and mentor.named(text) and ("?" in text or not (self.TALK_ACTIONS.search(low) or _actions.first_person_action(text)))):
            return False
        from engine import clock
        self.advance(clock.TALK_MINUTES)
        self.mentor_talk(text)
        return True

    def mentor_go_hunt(self, text: str) -> bool:
        """With the hunt taken, 'let's go' (or naming the Greywood and a going word) sets out, whatever the interpreter makes of it."""
        import re
        from llm.contracts import ActionIntent
        if mentor.stage(self.player) != "hunt" or self.combat or self.player.location == M["hunt"]["place"] or not self.mentor_in_town():
            return False
        low = text.lower()
        going = re.search(r"\b(head|go|walk|travel|set (out|off)|off to|let'?s go|lets go|let us go|get going|(i am|i'm|im|we are|we're|am i|are we|are you) ready)\b", low)
        if not going or not ("greywood" in low or (mentor.named(text) or re.search(r"\blet'?s\b|\bready\b", low))):
            return False
        if re.search(r"\bwhen\b|\bwill (it|he|she|they)\b|\bready (yet|by|for)\b", low) and "greywood" not in low and "let" not in low:
            return False
        if "greywood" not in low:
            if re.search(r"\b(first|before|later|not yet|afterwards|after that)\b", low):      # "let's go to the market first" is not the hunt
                return False
            from engine import candidates, mapview
            town = mapview.top_of(self.world, self.player.location)
            if any(candidates.names_in(low, p.name) for pid, p in self.world.places.items()          # a line naming another place is a trip there
                   if pid != M["hunt"]["place"] and mapview.top_of(self.world, pid) != town):
                return False
        self.on_move(ActionIntent(kind="move", destination=M["hunt"]["place"], summary=text), text)
        return True

    def mentor_joined(self, announce: bool = True, lead=None) -> None:
        """They are in the guild. She tells them where the hunt is posted and waits for them to take it themselves."""
        J = M["joined"]
        B = M["board_step"]
        if announce:
            console.narrate(J["narrate"].strip() if self.place.type == "guild" else mentor.at(J, "narrate", self.place.type).strip())
        if mentor.has_contract(self.player):                  # they took the hunt from the board before she came to find them
            self.player.mentor.pop("posting", None)
            mentor.set_stage(self.player, "hunt")
            self.player.mentor.update({"briefed": False, "found": False})
            self.store.save_player(self.player)
            self.mentor_say(J["speech"][0] if announce else [], lead or [], B["already"], B["go"], beat="they have already taken the wolf hunt from the board; you are ready to go")
            return
        self.mentor_say(J["speech"][0] if announce else [], lead or [], B["explain"], beat="they have signed into the guild; you tell them to take the wolf hunt from the board, which is the only contract on it, and that you will wait until they have")
        self.player.mentor["posting"] = mentor.make_contract(self.minutes)
        self.player.mentor["waited"] = 0
        mentor.set_stage(self.player, "board")
        self.store.save_player(self.player)

    def mentor_taken(self) -> None:
        """The hunt is in their hands: now she walks with them."""
        B = M["board_step"]
        self.player.mentor.pop("posting", None)
        mentor.set_stage(self.player, "hunt")
        self.player.mentor.update({"briefed": False, "found": False})
        self.store.save_player(self.player)
        if not self.mentor_in_party():
            self.mentor_join_party(f"{mentor.NAME} falls in beside you and joins your party for the hunt. (Free.)")
        self.mentor_say(B["taken"], B["go"], beat="they have taken the wolf hunt; you tell them where the Greywood is and that you will keep pace")

    # ---------- tracking and the wolves ----------

    def mentor_brief(self) -> None:
        """Arriving in the Greywood: how to find what you are hunting."""
        console.narrate(M["arrive"]["narrate"].strip())
        self.mentor_say(mentor.line(self.player, "track", self.mentor_seed()), beat="you teach them to track wolves by searching the ground")
        self.player.mentor["briefed"] = True
        self.store.save_player(self.player)

    def mentor_search(self) -> bool:
        """The first search in the Greywood finds the wolves, as she taught. True if this search was the one."""
        m = self.player.mentor
        if mentor.stage(self.player) != "hunt" or self.player.location != M["hunt"]["place"] or m.get("found") or self.combat:
            return False
        if not m.get("briefed"):
            self.mentor_brief()
        self.advance(encounters.E["search_minutes"])
        m["found"] = True
        self.mentor_wolves()
        return True

    def mentor_wolves(self) -> None:
        from scenes.combat_scene import CombatScene
        H = M["hunt"]
        if not mentor.has_contract(self.player):
            self.player.quests.append(mentor.make_contract(self.minutes))
        console.narrate(M["arrive"]["found_narrate"].strip())
        self.mentor_say(mentor.line(self.player, "found", self.mentor_seed()), beat="the wolves have been found and are coming")
        creature = self.world.bestiary[H["creature"]]
        level = max(1, self.player.character.level)
        foes = [combat.fighter_from_creature(creature, level, "normal", f"e{i}", name=f"wolf {i + 1}") for i in range(H["count"])]
        for f in foes:
            f.yields_at = 0                       # these wolves fight to the end: the hunt is for killing all three
            f.behaviors = {**f.behaviors, "fearless": 1}          # ...and a pack that loses heart is still a wolf the hunt has not killed
        scene = CombatScene.begin(self, creature, foes, M["arrive"]["fight_how"])
        self.combat = scene
        scene.fight.mentor = True
        self.store.save_combat(scene.to_json())
        self.mentor_say(mentor.line(self.player, "start", self.mentor_seed()), beat="the wolves are on them; you tell them how to fight")

    def mentor_round(self, scene) -> None:
        """After each round of the scripted fight: the draught, the floor, and the lessons."""
        f = scene.fight
        if f.mentor_troll:
            if f.over or not f.mentor_in:
                return
            C = M["troll_combat"]
            if f.mentor_phase >= 1 and "hurt" not in f.mentor_beats:              # the blow landed on her: tell them to use a draught on her
                f.mentor_beats.append("hurt")
                if not any(i.good == M["hunt"]["potion"] for i in self.player.character.inventory):
                    self.to_pack(inventory.make_good(M["hunt"]["potion"]))
                    console.note(C["hurt_potion"])
                self.mentor_say(mentor.Fixed(C["hurt"]), beat="the troll's blow has landed on you and you are hurt; you tell the player to give you a healing draught, which costs them no turn")
            elif f.mentor_phase >= 2 and "orders" not in f.mentor_beats:         # she guarded them: now how to give a companion an order
                f.mentor_beats.append("orders")
                self.mentor_say(mentor.Fixed(C["orders"]), beat="you stood guard over the player for a round; you tell them how to give a companion an order, such as 'Maren, attack the troll', which costs no turn")
            elif "orders" in f.mentor_beats and not f.mentor_struck and f.mentor_stalls > 0 and f.mentor_ally.order != "focus":
                self.mentor_say(mentor.Fixed(C["orders_again"]), beat="the player has not yet ordered you to attack the troll")
            return
        if not f.mentor or f.over:
            return
        p = f.player
        seed = self.mentor_seed()
        if f.mentor_saved and "floor" not in f.mentor_beats:
            f.mentor_beats.append("floor")
            self.mentor_say(mentor.line(self.player, "floor", seed), beat="the player was nearly killed; you pulled them clear and give them a draught")
            if not any(i.good == M["hunt"]["potion"] for i in self.player.character.inventory):
                self.to_pack(inventory.make_good(M["hunt"]["potion"]))
                console.note(M["lessons"]["floor_potion"])
            return
        if "first_blood" not in f.mentor_beats and p.hp < p.max_hp and f.enemies():
            f.mentor_beats.append("first_blood")
            self.to_pack(inventory.make_good(M["hunt"]["potion"]))
            console.note("Maren tosses you a healing draught.")
            self.mentor_say(mentor.line(self.player, "first_blood", seed), beat="the player has been hurt; you tossed them a healing draught and tell them to drink it")
        elif "steady" not in f.mentor_beats and "first_blood" in f.mentor_beats and f.round >= 3 and len(f.enemies()) >= 2:
            f.mentor_beats.append("steady")
            self.mentor_say(mentor.line(self.player, "steady", seed), beat="the fight is going on; you steady them")

    def mentor_run_fails(self) -> str:
        """What happens when the player tries to run from the troll: the attempt is made, and it fails."""
        return mentor.line_from(self.player, M["troll_combat"]["run_fail"])

    def mentor_refuse(self, kind: str) -> None:
        """Running and taming are not on offer in the first hunt, and neither is talking to the wolves."""
        if self.combat and self.combat.fight.mentor_troll:
            self.mentor_say(mentor.line_from(self.player, M["troll_combat"]["no_talk" if kind in ("talk", "tame") else "no_run"]), beat="the player tried something that cannot be done against the troll")
            return
        self.mentor_say(mentor.line(self.player, "no_talk" if kind in ("talk", "tame") else "no_run", self.mentor_seed()), beat="the player tried to run from or talk to the wolves; you tell them it cannot be done on this hunt")

    # ---------- after the fight ----------

    def mentor_fight_over(self, outcome: str, fight) -> None:
        if not getattr(fight, "mentor", False):
            return
        if getattr(fight, "mentor_troll", False):
            if outcome == "victory":
                self.mentor_after_troll()
            return
        if outcome == "victory":
            self.mentor_wolves_down()
        else:
            self.player.mentor["found"] = False            # however it ended, another search starts the hunt again

    def mentor_wolves_down(self) -> None:
        """The last wolf drops and the fight is over. She tells them to skin the wolves; the troll comes when that is done."""
        beat = "the three wolves are dead; you tell the player to skin and butcher them, and that you will keep watch"
        fact, line, must = self.mentor_opening("wolves")
        if not self.mentor_speak([*M["skin"]["info"], *([fact] if fact else [])], beat, must=["skin the wolves", *must],
                                 ends="the last paragraph tells them to skin the wolves and that you will keep watch"):
            self.mentor_say(M["skin"]["speech"], *([line] if line else []), beat=beat)
        mentor.set_stage(self.player, "harvest")
        self.player.mentor["troll_done"] = False
        self.store.save_player(self.player)
        self.show_exits()

    def mentor_skinned(self) -> None:
        """The wolves are skinned, and the troll arrives just as the last hide comes away."""
        pm = self.player.mentor
        if mentor.stage(self.player) != "harvest" or pm.get("troll_done") or pm.get("troll") or self.combat or self.player.location != M["hunt"]["place"]:
            return
        self.mentor_troll()

    def mentor_troll(self) -> None:
        """A troll comes out of the trees: a real fight, with its level and health on the pane. Maren is in it from the start. Its blow lands on
        her and she asks for a draught; she guards the player for a round and says how a companion is given an order; then, the order given,
        she ends it with a blow that is rolled, recorded and shown like any other."""
        from scenes.combat_scene import CombatScene
        T = M["troll"]
        C = M["troll_combat"]
        S = M["troll_sheet"]
        console.narrate(T["narrate_arrive"].strip())
        self.mentor_say(T["speech_before"][0], beat="you are keeping watch while the player skins the wolves, and a troll, which should not be this far south, has come out of the trees; you are shocked and about to step in front of the player")
        foe = mentor.troll_fighter("engaged")
        creature = self.world.bestiary[S["creature"]]

        def prepare(fight):
            fight.mentor = True
            fight.mentor_troll = True
            fight.no_rewards = True
            m = mentor.maren_fighter()
            fight.mentor_ally = m
            combat.enters(fight, m)
            troll = next(iter(fight.enemies()), None)
            if troll is not None:
                from engine import battlefield as bf
                bf.engage(fight, m, troll)
            fight.mentor_in = True
            fight.mentor_hurt_line = C["hurt_narrate"]
            fight.mentor_guard_line = C["guard_narrate"]
            fight.mentor_strike_line = C["strike_narrate"].format(weapon=S["weapon_title"])
            for e in fight.enemies():
                e.always_miss = True

        self.player.mentor["troll"] = True
        scene = CombatScene.begin(self, creature, [foe], C["how"], prepare=prepare, told=T["narrate_arrive"].strip())
        self.combat = scene
        console.narrate(C["join_narrate"])
        self.store.save_combat(scene.to_json())

    def mentor_after_troll(self) -> None:
        """The troll is down. She says her piece and waits for the walk back to Parth."""
        T = M["troll"]
        console.narrate(T["aftermath"])
        beat = "you have just killed the troll; you speak of it and of the world growing more dangerous, and say you will walk back to Parth together. No advice or warnings"
        fact, line, must = self.mentor_opening("troll")
        if not self.mentor_speak([*M["harvest"]["info"], *([fact] if fact else [])], beat, must=["Parth", *must],
                                 ends="the last paragraph says you will walk back to Parth together to get them paid"):
            self.mentor_say(M["troll_combat"]["after_speech"], T["speech_after"], *([line] if line else []), M["harvest"]["speech"], beat=beat)
        self.player.mentor["troll"] = False
        self.player.mentor["troll_done"] = True
        mentor.set_stage(self.player, "harvest")
        self.store.save_player(self.player)
        self.show_exits()

    def mentor_return(self) -> None:
        """Back in Parth: she sends them to the clerk with the contract and goes about her business."""
        r = M["return"]
        console.narrate(r["narrate"].strip())
        beat = "you are back in Parth; you tell them to hand the contract in at the guild hall and say goodbye"
        fact, line, must = self.mentor_opening("return")
        if not self.mentor_speak([*r["info"], *([fact] if fact else [])], beat, must=["guild hall", *must]):
            self.mentor_say(*([line] if line else []), r["speech"], beat=beat)
        console.narrate(r["leave"])
        self.mentor_leave_party()
        self.mentor_settle()
        mentor.set_stage(self.player, "done")
        self.store.save_player(self.player)
