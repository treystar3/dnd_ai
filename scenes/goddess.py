"""The Threshold: character creation as a role-played scene.

Each player turn:
  1. interpret  - the LLM reads what the player typed into a PlayerTurn
  2. engine     - this class validates it and decides what happens
  3. narrate    - the LLM voices the goddess, told only what the engine decided

The goddess never decides anything. All mechanics are shown by ui.console.
"""

import json
from enum import Enum
from pathlib import Path

from character import creation
from core.models import Attributes, Character
from engine import stats
from llm.contracts import GoddessLine, PlayerTurn
from llm.gateway import LLMError, generate
from scenes import goddess_prompts as gp
from ui import console

KNOWLEDGE_PATH = Path("data/goddess_knowledge.json")
SPEAKER = "The Goddess"


class Step(str, Enum):
    NAME = "name"
    CONCEPT = "concept"
    CONFIRM_CLASS = "confirm_class"
    ACTIVES = "actives"
    PASSIVES = "passives"
    STATS = "stats"
    CONFIRM_STATS = "confirm_stats"
    ASPIRATION = "aspiration"
    DONE = "done"


EXPECTS = {
    Step.NAME: "the player's name",
    Step.CONCEPT: "who they want to become: their fighting style, calling, or the kind of person they will be",
    Step.CONFIRM_CLASS: "whether the goddess's reading of their nature is right (confirm), or what should change (decline, with text)",
    Step.ACTIVES: "choosing exactly two of the numbered abilities",
    Step.PASSIVES: "choosing exactly two of the numbered traits",
    Step.STATS: "how to shape their body and mind: exact attribute numbers, or what matters most to them",
    Step.CONFIRM_STATS: "whether the attributes shown are right (confirm) or should change (decline)",
    Step.ASPIRATION: "an optional aspiration, something they hope to achieve in their new life (decline if none)",
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
        self.actives = []
        self.passives = []
        self.values: dict[str, int] = {}
        self.character: Character | None = None

    def run(self) -> Character:
        console.wait("Darkness. Then, slowly, a soft and sourceless light.")
        self.speak(
            "The player has just awoken here. They died moments ago. Tell them so, gently. "
            "Tell them it was not their time, and that you are offering a second chance. "
            "Then ask their name."
        )
        while self.step != Step.DONE:
            text = console.ask()
            if text.lower() in {"quit", "exit", "/quit", "/exit"}:
                print("\nYou leave the Threshold. No character was saved - run main.py to begin again.")
                raise SystemExit(0)
            if not text:
                continue
            self.transcript.append(("Player", text))
            try:
                turn = self.interpret(text)
            except LLMError as e:
                console.debug(str(e))
                console.note("The model couldn't make sense of that. Try saying it another way.")
                continue
            if turn.kind == "question":
                self.answer_question(turn.question or text)
                continue
            getattr(self, f"on_{self.step.value}")(turn)
        return self.character

    def speak(self, event: str) -> None:
        line = generate(
            "goddess_line", self.system,
            gp.narration_request(EXPECTS.get(self.step, "farewell"), event, self.transcript),
            GoddessLine, temperature=0.9,
        )
        console.say(line.speech, SPEAKER)
        self.transcript.append(("Goddess", line.speech))

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
        self.speak(
            "What the player said does not answer the current step. Respond briefly, "
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
            f"The player's name is {name}. Acknowledge it. Tell them you can give them a "
            "beginning but not a destiny, and ask who they wish to become."
        )

    def on_concept(self, turn: PlayerTurn) -> None:
        if turn.kind not in ("answer", "decline") or not turn.text.strip():
            self.redirect()
            return
        self.concept = turn.text.strip()
        self.read_class()

    def read_class(self) -> None:
        console.wait("She regards you in silence for a long moment.")
        try:
            self.interp = creation.interpret_concept(self.concept)
        except LLMError as e:
            console.debug(str(e))
            console.note("The model couldn't read that concept this time. Nothing is lost - describe it again.")
            self.step = Step.CONCEPT
            return
        console.show_class(self.interp)
        self.step = Step.CONFIRM_CLASS
        self.speak(
            f"You perceive the player's nature as: {self.interp.custom_class}. {self.interp.summary} "
            "Tell them what you see in them in your own words, without game terms, "
            "and ask whether you have seen them truly."
        )

    def on_confirm_class(self, turn: PlayerTurn) -> None:
        if turn.kind == "confirm":
            console.wait("Threads of possibility gather in the dark around her hands.")
            try:
                self.active_options = creation.generate_actives(self.interp)
                self.passive_options = creation.generate_passives(self.interp, self.active_options)
            except LLMError as e:
                console.debug(str(e))
                console.wait("The threads slip through her fingers and scatter.")
                console.note("The model couldn't shape your gifts this time. Nothing is lost - say yes again to retry.")
                return
            self.step = Step.ACTIVES
            console.show_actives(self.active_options)
            self.speak(
                "The player accepted your reading. The game now shows them fifteen techniques "
                "they might carry back. Invite them to choose two."
            )
        elif turn.kind in ("decline", "answer") and turn.text.strip():
            self.concept += f"\nRefinement: {turn.text.strip()}"
            self.read_class()
        else:
            self.speak("Ask the player whether you have seen them truly, or what you have misjudged.")

    def on_actives(self, turn: PlayerTurn) -> None:
        error = creation.check_active_picks(self.active_options, turn.picks)
        if error:
            self.speak(f"The player's choice cannot be accepted: {error} Explain gently and ask them to choose again.")
            return
        self.actives = [self.active_options[n - 1] for n in turn.picks]
        self.step = Step.PASSIVES
        console.show_passives(self.passive_options)
        self.speak(
            f"The player chose {' and '.join(a.name for a in self.actives)}. Acknowledge it briefly. "
            "The game now shows fifteen innate traits. Invite them to choose two."
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
            f"The player chose {' and '.join(p.name for p in self.passives)}. Acknowledge it briefly. "
            "Now their body and mind must be shaped. Ask what kind of body and mind they wish to return with."
        )

    def on_stats(self, turn: PlayerTurn) -> None:
        if turn.stats:
            values = turn.stats.model_dump()
        elif turn.priorities:
            values = stats.from_priorities(turn.priorities + list(self.interp.primary_attributes))
        else:
            self.redirect()
            return
        console.show_sheet(values)
        error = stats.check_allocation(values)
        if error:
            self.speak(f"That shaping is not possible: {error} Explain gently and ask them to try again.")
            return
        self.values = values
        self.step = Step.CONFIRM_STATS
        self.speak("The game has shown the shape of their body and mind. Ask whether this is how they wish to be made.")

    def on_confirm_stats(self, turn: PlayerTurn) -> None:
        if turn.kind == "confirm":
            self.step = Step.ASPIRATION
            self.speak(
                "The player accepted. Ask, lightly, whether there is something they hope to achieve "
                "in their new life. Make clear it is not required."
            )
        elif turn.kind == "decline":
            self.step = Step.STATS
            console.show_stat_rules(getattr(self, "guidance", []))
            self.speak("The player wants to change it. Ask how they would rather be made.")
        else:
            self.redirect()

    def on_aspiration(self, turn: PlayerTurn) -> None:
        if turn.kind == "answer" and turn.text.strip():
            self.finish(turn.text.strip())
        elif turn.kind == "decline":
            self.finish(None)
        else:
            self.redirect()

    def finish(self, aspiration: str | None) -> None:
        self.character = creation.build_character(
            self.name, self.interp, self.actives, self.passives,
            Attributes(**self.values), aspiration,
        )
        path = creation.save_character(self.character)
        self.step = Step.DONE
        hope = f"Their aspiration: {aspiration}." if aspiration else "They named no aspiration."
        self.speak(
            f"Creation is complete. {hope} Bid them farewell as they are sent back to the living world. "
            "Their memory of this place begins to fade. Do not say where they will wake."
        )
        console.note(f"Character saved to {path}")
