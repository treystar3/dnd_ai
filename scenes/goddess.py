"""The Threshold: character creation as a role-played scene.

Each player turn:
  1. interpret  - the LLM reads what the player typed into a PlayerTurn
  2. engine     - this class validates it and decides what happens
  3. narrate    - the LLM voices the goddess, told only what the engine decided

The goddess never decides anything. All mechanics are shown by ui.console.

(f388) Before she speaks, the player says who they were: a people, he, she or they, and a look (engine/look.py), which the world sees from
then on. In the window every step is also a page (console.creation): cards to choose abilities and traits from, the attributes shaped
with buttons and the numbers they give, the goddess's last words over it all. The page answers with hidden lines ("create:picks 1 4 7",
"create:stats {...}") that are read here without a model call; anything typed is read as before.
"""

import json
import re
from enum import Enum

from character import creation
from core.models import Attributes, Character
from engine import stats
from llm.contracts import GoddessLine, PlayerTurn
from llm.gateway import LLMError, generate
from scenes import goddess_prompts as gp
from ui import console

from core.paths import BUNDLE
KNOWLEDGE_PATH = BUNDLE / "data" / "goddess_knowledge.json"
OPENING_PATH = BUNDLE / "data" / "opening.json"
SEND_OFF_PATH = BUNDLE / "data" / "send_off.json"
SPEAKER = "The Goddess"


class Step(str, Enum):
    WHO = "who"
    NAME = "name"
    CONCEPT = "concept"
    CONFIRM_CLASS = "confirm_class"
    ACTIVES = "actives"
    PASSIVES = "passives"
    STATS = "stats"
    CONFIRM_STATS = "confirm_stats"
    DONE = "done"


TABS = [("who", "Who you were"), ("name", "Name"), ("calling", "Calling"), ("abilities", "Abilities"), ("traits", "Traits"),
        ("body", "Body & mind"), ("return", "Return")]
TAB_OF = {"who": "who", "name": "name", "concept": "calling", "confirm_class": "calling", "actives": "abilities", "passives": "traits",
          "stats": "body", "confirm_stats": "body", "done": "return"}
# (f388) the card filters: which group an ability is in, by what it does
GROUPS = {"abilities": [("all", "All"), ("attack", "Attacks"), ("support", "Defence & support"), ("control", "Control"), ("healing", "Healing"),
                        ("outside", "Outside combat")],
          "traits": [("all", "All"), ("combat", "In a fight"), ("world", "Out in the world")]}
ATTRIBUTE_HINT = {"strength": "heavy weapons, raw force", "dexterity": "hit chance, dodging, crits", "constitution": "health and stamina",
                  "intelligence": "spells that use it", "wisdom": "perception, will", "charisma": "persuasion, prices, people"}

EXPECTS = {
    Step.WHO: "who they were: their people, he, she or they, and how they look",
    Step.NAME: "the player's name",
    Step.CONCEPT: "who they want to become: their fighting style, calling, or the kind of person they will be",
    Step.CONFIRM_CLASS: "whether the goddess's reading of their nature is right (confirm), or what should change (decline, with text)",
    Step.ACTIVES: "choosing exactly three of the numbered abilities",
    Step.PASSIVES: "choosing exactly three of the numbered traits",
    Step.STATS: "how to shape their body and mind: exact attribute numbers, or what matters most to them",
    Step.CONFIRM_STATS: "whether the attributes shown are right (confirm) or should change (decline)",
}


class ThresholdScene:
    def __init__(self):
        self.knowledge = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
        self.system = gp.goddess_system(self.knowledge)
        self.step = Step.NAME
        self.transcript: list[tuple[str, str]] = []
        self.name = ""
        self.concept = ""
        self.interp = None
        self.active_options = []
        self.passive_options = []
        self.passives_job = None
        self.actives = []
        self.passives = []
        self.values: dict[str, int] = {}
        self.character: Character | None = None
        self.who_choice: dict | None = None                # (f388) the first page's choices (engine/look.py clean)
        self.last_line = ""                                # her last words, for the page
        self.drawn = False                                 # a window is drawing the pages

    def run(self) -> Character | None:
        """The character made, or None when the player goes back to the main menu (#menu) before it is finished."""
        if not self.who():
            return None
        self.opening()
        self.show()
        while self.step != Step.DONE:
            text = console.ask(menu=True)
            from llm import audit
            audit.note_turn(-1, f"(creation) {text}")      # the Threshold's calls, filed under what the player answered (f314)
            if text.lower() in {"quit", "exit", "/quit", "/exit"}:
                console.out("\nYou leave the Threshold. No character was saved - run main.py to begin again.")
                raise SystemExit(0)
            if text.lower() in {"#menu", "#mainmenu", "#saves"}:
                console.note("No character was made. Back to the main menu.")
                return None
            if not text:
                continue
            if text.startswith("create:"):                  # (f388) a button on the page: read without the model
                turn = self.structured(text)
                if turn is not None:
                    getattr(self, f"on_{self.step.value}")(turn)
                continue
            self.transcript.append(("Player", text))
            try:
                turn = self.interpret(text)
            except LLMError as e:
                console.debug(str(e))
                self.tell("The model couldn't make sense of that. Try saying it another way.")
                continue
            if turn.kind == "question":
                self.answer_question(turn.question or text)
                continue
            getattr(self, f"on_{self.step.value}")(turn)
        return self.character

    # ---------- (f388) who they were, and the pages ----------

    def who(self) -> bool:
        """The first page, before the goddess speaks: a people, he, she or they, and a look. False when the player goes back to the menu."""
        from engine import look
        self.step = Step.WHO
        if not self.show():                                 # the terminal: the same choices, as text
            page = look.page()
            console.narrate(page["intro"])
            console.note("Who were you? Your people: " + ", ".join(p["name"] for p in page["peoples"]) + ". Say which, whether others say "
                         "he, she or they, and how you look (build, age, hair, anything else) - or press Enter to be surprised.")
        while True:
            text = console.ask(menu=True)
            if text.lower() in {"quit", "exit", "/quit", "/exit"}:
                console.out("\nYou leave the Threshold. No character was saved - run main.py to begin again.")
                raise SystemExit(0)
            if text.lower() in {"#menu", "#mainmenu", "#saves"}:
                console.note("No character was made. Back to the main menu.")
                return False
            if text.startswith("create:who"):
                try:
                    choice = look.clean(json.loads(text[len("create:who"):].strip() or "{}"))
                except (ValueError, TypeError):
                    continue
            elif not text.strip():
                if self.drawn:
                    continue
                choice = look.surprise()
            else:
                choice = look.from_text(text)
            break
        self.who_choice = choice
        seen = look.describe(choice)
        console.note(f"How the world sees you: {seen}")
        self.system = gp.goddess_system(self.knowledge, seen)
        self.step = Step.NAME
        return True

    def seen(self) -> str:
        from engine import look
        return look.describe(self.who_choice) if self.who_choice else ""

    def structured(self, text: str) -> PlayerTurn | None:
        """A line from the page's buttons, read without the model: the name or calling as typed into the page, a yes, three picks, or the
        attributes shaped (which finish creation, since the page showed every number already)."""
        head, _, rest = text.partition(" ")
        rest = rest.strip()
        if head == "create:name" and self.step == Step.NAME and rest:
            self.transcript.append(("Player", rest))
            return PlayerTurn(kind="answer", text=rest)
        if head == "create:calling" and self.step in (Step.CONCEPT, Step.CONFIRM_CLASS) and rest:
            self.transcript.append(("Player", rest))
            return PlayerTurn(kind="answer" if self.step == Step.CONCEPT else "decline", text=rest)
        if head == "create:confirm" and self.step in (Step.CONFIRM_CLASS, Step.CONFIRM_STATS):
            self.transcript.append(("Player", "Yes."))
            return PlayerTurn(kind="confirm")
        if head == "create:picks" and self.step in (Step.ACTIVES, Step.PASSIVES):
            picks = [int(n) for n in re.findall(r"\d+", rest)]
            options = self.active_options if self.step == Step.ACTIVES else self.passive_options
            self.transcript.append(("Player", " and ".join(options[n - 1].name for n in picks if 0 < n <= len(options))))
            return PlayerTurn(kind="answer", picks=picks)
        if head == "create:stats" and self.step in (Step.STATS, Step.CONFIRM_STATS):
            try:
                values = {k: int(v) for k, v in json.loads(rest).items() if k in stats.STAT_NAMES}
            except (ValueError, TypeError, AttributeError):
                return None
            error = stats.check_allocation({k: values.get(k, stats.BASE) for k in stats.STAT_NAMES})
            if error:
                self.tell(f"That can't be done: {error}")
                self.show()
                return None
            self.values = {k: values.get(k, stats.BASE) for k in stats.STAT_NAMES}
            self.transcript.append(("Player", "This is how I'll be made."))
            self.finish()
            return None
        return None

    def tell(self, message: str) -> None:
        """A note to the player: in the story, and on the page when one is drawn (a note behind the page is a note nobody reads)."""
        console.note(message)
        if self.drawn:
            self.show(note=message)

    def show(self, wait: str = "", note: str = "") -> bool:
        """The page for the step the scene is at, drawn by a window (console.creation); False in the terminal, which prints as before."""
        data = {"step": self.step.value, "tab": TAB_OF[self.step.value], "tabs": TABS, "goddess": self.last_line, "wait": wait,
                "note": note, "seen": self.seen()}
        try:
            data.update(self.page())
        except Exception as e:                              # a page that cannot be drawn leaves the conversation, never the game
            console.debug(f"creation page: {e}")
        self.drawn = bool(console.creation(data))
        return self.drawn

    def page(self) -> dict:
        from engine import look
        s = self.step
        if s == Step.WHO:
            return {"who": look.page()}
        if s == Step.NAME:
            return {"ask": {"label": "Your name", "placeholder": "What were you called?", "button": "This is my name", "send": "create:name"}}
        if s == Step.CONCEPT:
            return {"ask": {"label": "Who do you want to become?", "multiline": True, "button": "This is who I'll be", "send": "create:calling",
                            "placeholder": "a spearman who hunts beasts for coin; a river priest who heals; a thief who sings..."}}
        if s == Step.CONFIRM_CLASS and self.interp is not None:
            i = self.interp
            return {"reading": {"name": i.custom_class, "kind": i.archetype.value, "identity": i.combat_identity, "themes": list(i.themes),
                                "summary": i.summary},
                    "ask": {"label": "Not quite? Tell her what to change", "multiline": True, "button": "Read me again", "send": "create:calling",
                            "placeholder": "more of a healer; no magic, just steel..."},
                    "confirm": "Yes, that is me"}
        if s == Step.ACTIVES and self.active_options:
            return {"cards": self.cards(self.active_options, "abilities"), "groups": self.groups("abilities", self.active_options),
                    "pick": 3, "title": "Choose 3 abilities", "button": "Take these three"}
        if s == Step.PASSIVES and self.passive_options:
            return {"cards": self.cards(self.passive_options, "traits"), "groups": self.groups("traits", self.passive_options),
                    "pick": 3, "title": "Choose 3 traits", "button": "Take these three"}
        if s in (Step.STATS, Step.CONFIRM_STATS) and self.interp is not None:
            return {"body": self.body()}
        return {}

    @staticmethod
    def group_of(o, kind: str) -> str:
        if kind == "traits":
            from core.rules import MECHANICS
            m = MECHANICS.get(getattr(o, "mechanic", "") or "")
            return m.kind if m is not None else "combat"
        if getattr(o, "context", None) is not None and o.context.value == "out_of_combat":
            return "outside"
        e = o.effect.value
        return {"damage": "attack", "control": "control", "healing": "healing"}.get(e, "support")

    def groups(self, kind: str, options: list) -> list:
        counts = {}
        for o in options:
            g = self.group_of(o, kind)
            counts[g] = counts.get(g, 0) + 1
        return [[g, label, len(options) if g == "all" else counts.get(g, 0)] for g, label in GROUPS[kind] if g == "all" or counts.get(g)]

    def cards(self, options: list, kind: str) -> list[dict]:
        out = []
        for n, o in enumerate(options, 1):
            if kind == "traits":
                out.append({"n": n, "name": o.name, "group": self.group_of(o, kind), "cost": "", "line": "", "text": o.effect_text(),
                            "tip": console.passive_tip(o)})
                continue
            facts = console._ability_facts(o, 1)
            cost = next((f for f in facts if re.search(r"\d+ (stamina|mana)", f)), "")
            line = [x for x in facts if x not in (cost,) and not x.startswith("deals ") and x != console.CONTEXT_WORD.get(o.context.value)]
            from engine import field
            text = field.fight_text(o) or field.outside_text(o)
            if not text and o.effect.value == "damage":
                text = next((f for f in facts if f.startswith("deals ")), "").capitalize()
            if not text and o.effect.value == "healing":
                from engine import healing
                text = healing.card_text(o)
                text = text[:1].upper() + text[1:]
            out.append({"n": n, "name": o.name, "group": self.group_of(o, kind), "cost": re.sub(r"\s*\([A-Z]{3}\)", "", cost),
                        "line": " · ".join(line), "text": (text or o.description).rstrip(".") + ".", "tip": console.ability_tip(o)})
        return out

    def body(self) -> dict:
        """The attributes page: each attribute's place in this class, the suggestion, and what the page needs to work out the pools and
        the hit chance as the player shapes them (the same sums as engine/pools.py and the stats sheet)."""
        from character.creation import casting_attribute as class_cast
        from core.models import Trigger
        from engine import combat, pools
        i = self.interp
        uses_mana = any(a.resource.value == "mana" for a in self.actives)
        cast = class_cast(i) if uses_mana else ""
        mains = list(i.primary_attributes)
        suggest = stats.from_priorities(mains)
        probe = Character(name=self.name or "you", archetype=i.archetype, custom_class=i.custom_class, actives=list(self.actives),
                          passives=list(self.passives), casting_attribute=cast, attributes=Attributes(**suggest))
        pool = {}
        for p in pools.POOLS:
            rule = pools.RULES.pools[p]
            pct, flat = pools._bonus_parts(probe, rule.modifier, {Trigger.ALWAYS.value})
            pool[p] = {"base": rule.base, "w": dict(rule.attributes), "pct": pct, "flat": flat}
        m = pools.RULES.mana_casting
        pool["mana"].update(cast=pools.casting_attribute(probe), cast_w=m["cast_weight"], other_w=m["other_weight"], mental=list(pools.MENTAL))
        hit = {}
        for v in range(stats.BASE, stats.CAP + 1):
            probe.attributes = Attributes(**dict(suggest, dexterity=v))
            f = combat.fighter_from_character(probe)
            attr = f.best_attr(f.weapon_attrs)
            foe = combat.Fighter(id="equal", name="an equal foe", side="enemy", level=f.level, attrs={a: attr for a in combat.ATTRIBUTES}, hp=1, max_hp=1)
            hit[v] = round(combat.hit_parts(f, foe, combat.Combat(fighters=[f, foe]))[0])
        rows = []
        for a in stats.STAT_NAMES:
            note = ("main for your class" if a in mains else "your spells use it" if a == cast else
                    "none of your abilities use it" if a == "intelligence" and not uses_mana else "")
            rows.append({"id": a, "label": a.capitalize(), "hint": ATTRIBUTE_HINT.get(a, ""), "main": a in mains, "note": note})
        article = "an" if i.custom_class[:1].lower() in "aeiou" else "a"
        return {"rows": rows, "base": stats.BASE, "cap": stats.CAP, "total": stats.TOTAL, "values": self.values or {a: stats.BASE for a in stats.STAT_NAMES},
                "suggested": suggest, "suggest_label": f"Suggested for {article} {i.custom_class}", "pools": pool, "hit": hit,
                "describe": "tough and strong, a little wise", "button": "This is how I'll be made"}

    def opening(self) -> None:
        """The fixed opening: what happened and what comes next, the same every time. The goddess then answers whatever the player says."""
        self.play(OPENING_PATH)

    def play(self, path, **fill) -> None:
        for beat in json.loads(path.read_text(encoding="utf-8")):
            text = beat["text"].format(**fill) if fill else beat["text"]
            if beat["who"] == "goddess":
                console.say(text, SPEAKER)
                self.transcript.append(("Goddess", text))
                self.last_line = text
            else:
                console.narrate(text)

    def speak(self, event: str) -> None:
        line = generate(
            "goddess_line", self.system,
            gp.narration_request(EXPECTS.get(self.step, "farewell"), event, self.transcript),
            GoddessLine, temperature=0.9,
        )
        console.say(line.speech, SPEAKER)
        self.transcript.append(("Goddess", line.speech))
        self.last_line = line.speech
        if self.step != Step.DONE:
            self.show()                                     # (f388) the page follows her: the step she has moved to, her words over it

    def interpret(self, text: str) -> PlayerTurn:
        return generate(
            "interpret_creation_input", gp.INTERPRET_SYSTEM,
            gp.interpret_request(self.step.value, EXPECTS[self.step], self.options_text(), text),
            PlayerTurn, temperature=0.2, max_tokens=300,
        )

    def options_text(self) -> str:
        if self.step == Step.ACTIVES:
            return "\n".join(f"{i}. {a.name}: {a.description}" for i, a in enumerate(self.active_options, 1))
        if self.step == Step.PASSIVES:
            return "\n".join(f"{i}. {p.name}: {p.description}" for i, p in enumerate(self.passive_options, 1))
        if self.step == Step.STATS:
            return f"Attributes: {', '.join(stats.STAT_NAMES)}. {stats.rules_text()}"
        return ""

    def answer_question(self, question: str) -> None:
        extra = ""
        if self.step in (Step.ACTIVES, Step.PASSIVES):
            extra = f" The options the player can see are:\n{self.options_text()}"
        self.speak(
            f"The player asked: {question}. Answer only from what you know, then gently "
            f"return to the current step.{extra}"
        )

    def redirect(self) -> None:
        if self.step == Step.STATS:
            console.show_stat_rules(getattr(self, "guidance", []))
        self.speak(
            "What the player said does not answer the current step. Respond "
            f"in character, and return them to it: {EXPECTS[self.step]}."
        )

    def on_name(self, turn: PlayerTurn) -> None:
        name = turn.text.strip().strip(".!\"'") if turn.kind == "answer" else ""
        if not name or len(name) > 40:
            self.redirect()
            return
        self.name = name
        self.step = Step.CONCEPT
        self.speak(
            f"The player's name is {name}. Say it back once, softly, as if holding it. Then, hurriedly, ask who they wish to "
            "become, so that you can give their life a shape to carry back."
        )

    def on_concept(self, turn: PlayerTurn) -> None:
        if turn.kind not in ("answer", "decline") or not turn.text.strip():
            self.redirect()
            return
        self.concept = turn.text.strip()
        self.read_class()

    def read_class(self) -> None:
        console.wait("She regards you in silence for a long moment.")
        if self.drawn:
            self.show(wait="She regards you in silence for a long moment.")
        try:
            self.interp = creation.interpret_concept(self.concept, self.seen())
        except LLMError as e:
            console.debug(str(e))
            self.tell("The model couldn't read that concept this time. Nothing is lost - describe it again.")
            self.step = Step.CONCEPT
            return
        console.show_class(self.interp)
        self.step = Step.CONFIRM_CLASS
        self.speak(
            f"You perceive the player's nature as: {self.interp.custom_class}. {self.interp.summary} "
            "Tell them what you see in them in your own words, without game terms, as the shape their life already has, "
            "and ask whether you have seen them truly."
            + (f" The player asked for something this world does not have. {self.interp.adapted} Say, gently and in your own words, that the "
               "thing they named has no place in Meravia and what you see in them instead." if self.interp.adapted else "")
        )

    def on_confirm_class(self, turn: PlayerTurn) -> None:
        if turn.kind == "confirm":
            console.wait("Threads of possibility gather in the dark around her hands.")
            if self.drawn:
                self.show(wait="Threads of possibility gather in the dark around her hands.")
            try:
                self.active_options = creation.generate_actives(self.interp)
            except LLMError as e:
                console.debug(str(e))
                console.wait("The threads slip through her fingers and scatter.")
                self.tell("The model couldn't shape your gifts this time. Nothing is lost - say yes again to retry.")
                return
            self.step = Step.ACTIVES
            console.show_actives(self.active_options)
            self.speak(
                "The player accepted your reading. The game now shows them fifteen techniques "
                "they might carry back: what is already in them, drawn out. Invite them, quickly, to choose three."
            )
            self.passives_job = creation.PassivesInBackground(self.interp, self.active_options)   # written while they read
        elif turn.kind in ("decline", "answer") and turn.text.strip():
            self.concept += f"\nRefinement: {turn.text.strip()}"
            self.read_class()
        else:
            self.speak("Ask the player whether you have seen them truly, or what you have misjudged.")

    def on_actives(self, turn: PlayerTurn) -> None:
        error = creation.check_active_picks(self.active_options, turn.picks,
                                            keeps_companions=bool(getattr(self.interp, "uses_companions", False)))
        if error:
            self.speak(f"The player's choice cannot be accepted: {error} Explain gently and ask them to choose again.")
            return
        job = getattr(self, "passives_job", None)
        if job is not None and not job.ready:
            console.wait("Threads of possibility are still settling in her hands.")
        try:
            self.passive_options = job.result() if job is not None else creation.generate_passives(self.interp, self.active_options)
        except LLMError as e:
            console.debug(str(e))
            self.tell("The model couldn't shape your innate traits this time. Nothing is lost - choose your three techniques again to retry.")
            self.passives_job = None
            return
        self.passives_job = None
        self.actives = [self.active_options[n - 1] for n in turn.picks]
        self.step = Step.PASSIVES
        console.show_passives(self.passive_options)
        self.speak(
            f"The player chose {' and '.join(a.name for a in self.actives)}. Acknowledge it. "
            "The game now shows fifteen innate traits. Invite them to choose three."
        )

    def on_passives(self, turn: PlayerTurn) -> None:
        error = creation.check_passive_picks(self.passive_options, turn.picks)
        if error:
            self.speak(f"The player's choice cannot be accepted: {error} Explain gently and ask them to choose again.")
            return
        self.passives = [self.passive_options[n - 1] for n in turn.picks]
        self.step = Step.STATS
        self.guidance = creation.attribute_guidance(self.interp, self.actives)
        console.show_stat_rules(self.guidance)
        self.speak(
            f"The player chose {' and '.join(p.name for p in self.passives)}. Acknowledge it. "
            "Now their body and mind must be shaped. Ask what kind of body and mind they wish to return with."
        )

    def on_stats(self, turn: PlayerTurn) -> None:
        if turn.stats:
            values = turn.stats.model_dump()
        elif turn.priorities:
            values = stats.from_priorities(turn.priorities + list(self.interp.primary_attributes), extreme=stats.wants_extreme(turn.text))
        else:
            self.redirect()
            return
        console.show_sheet(values)
        error = stats.check_allocation(values)
        if error:
            self.tell(f"That can't be done: {error}")
            console.show_stat_rules(getattr(self, "guidance", []))
            self.speak(f"That shaping is not possible: {error} Say plainly what the limit is ({stats.rules_text()}) and ask them to try again.")
            return
        self.values = values
        self.step = Step.CONFIRM_STATS
        self.speak("The game has shown the shape of their body and mind. Ask whether this is how they wish to be made.")

    def on_confirm_stats(self, turn: PlayerTurn) -> None:
        if turn.kind != "confirm" and (turn.stats or turn.priorities):      # 'No. strength 10, ...' already says what they want instead
            self.step = Step.STATS
            self.on_stats(turn)
            return
        if turn.kind == "confirm":
            self.finish()
        elif turn.kind == "decline":
            self.step = Step.STATS
            console.show_stat_rules(getattr(self, "guidance", []))
            self.speak("The player wants to change it. Ask how they would rather be made.")
        else:
            self.redirect()

    def finish(self) -> None:
        self.character = creation.build_character(
            self.name, self.interp, self.actives, self.passives,
            Attributes(**self.values), None, concept=self.concept, who=self.who_choice,
        )
        path = creation.save_character(self.character)
        self.step = Step.DONE
        console.creation_done()                             # (f388) the pages close; the send-off is told in the story
        console.note(f"Character saved to {path}")
        self.play(SEND_OFF_PATH, name=self.name)
