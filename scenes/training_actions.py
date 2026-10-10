"""Training at the guild: drills for experience, tutoring for lasting check bonuses, and learning new abilities."""

from pathlib import Path

import yaml

from engine import clock, leveling, money
from engine.abilities import materialize_active
from llm import prompts
from llm.contracts import LearnSet
from llm.gateway import LLMError, generate
from npc.models import Memory
from ui import console

ROOT = Path(__file__).resolve().parent.parent
T = yaml.safe_load((ROOT / "data" / "rules" / "training.yaml").read_text(encoding="utf-8"))
DISCIPLINE_WORDS = {
    "wisdom": ("heal", "holy", "divine", "faith", "prayer", "nature", "druid", "spirit", "blessing", "mend"),
    "charisma": ("pact", "song", "bard", "charm", "voice", "performance", "hex", "warlock", "illusion"),
    "intelligence": ("arcane", "fire", "frost", "ice", "lightning", "wizard", "rune", "elemental", "conjur"),
}


class TrainingActions:

    def instructor_here(self):
        return next((n for n in self.present if n.role == "guild_instructor"), None)

    def fee(self, amount: float) -> int:
        return round(amount * (1 if self.player.guild_rank else T["outsider_multiplier"]))

    def pay_for_training(self, fee: int, what: str) -> bool:
        c = self.player.character
        if c.coins < fee:
            console.note(f"{what.capitalize()} costs {money.words(fee)}; you have {money.words(c.coins)}.")
            self.halted = True
            return False
        c.coins -= fee
        return True

    def ability_slots(self) -> int:
        a = T["abilities"]
        return a["starting"] + self.player.character.level // a["levels_per_new"]

    def on_train(self, intent, text: str) -> None:
        teacher = self.instructor_here()
        if not teacher:
            console.note("Training is with the guild's instructor, at the guild house during working hours.")
            self.halted = True
            return
        words = f"{intent.item} {text}".lower()
        skill = next((s for s in T["tutoring"]["skills"] if s in words), None)
        if skill:
            self.tutor(teacher, skill, text)
        elif any(w in words for w in ("drill", "spar", "practice", "fight", "combat training", "experience", "exercise")):
            self.drill(teacher, text)
        elif self.asks_what(words):
            self.show_training()
        elif any(w in words for w in ("learn", "teach", "ability", "spell", "technique", "move", "magic")):
            self.offer_abilities(teacher, intent.item or text)
        else:
            self.show_training()

    @staticmethod
    def asks_what(words: str) -> bool:
        """'What can you teach me?' - a question about training, not a request for something particular."""
        vague = ("what can you teach", "what do you teach", "what training", "what can i learn", "what do you offer",
                 "what lessons", "how does training")
        return any(v in words for v in vague)

    def show_training(self) -> None:
        c = self.player.character
        d, t, a = T["drills"], T["tutoring"], T["abilities"]
        console.note("The instructor teaches:")
        console.note(f"  drills - {money.words(self.fee(d['fee_per_level'] * c.level))}, {d['hours']} hours, once a day")
        console.note(f"  tutoring in {', '.join(t['skills'])} - from {money.words(self.fee(t['base_fee']))}, "
                     f"{t['hours']} hours, +{t['bonus']}% each time up to +{t['cap']}%")
        console.note(f"  a new ability - {money.words(self.fee(a['base_fee'] + a['fee_per_level'] * c.level))}, "
                     f"{a['hours']} hours (you know {len(c.actives)} of {self.ability_slots()} you can hold)")

    def drill(self, teacher, text: str) -> None:
        c, d = self.player.character, T["drills"]
        day = clock.day(self.minutes)
        if c.level >= d["max_level"]:
            console.note("The instructor has nothing left to teach you in drills - the world is your teacher now.")
            self.halted = True
            return
        if c.last_drill_day == day:
            console.note("You've drilled today already. Come back tomorrow.")
            self.halted = True
            return
        fee = self.fee(d["fee_per_level"] * c.level)
        if not self.pay_for_training(fee, "a drill session"):
            return
        self.advance(d["hours"] * 60)
        xp = round(leveling.xp_to_next(c.level) * d["xp_share"] * (1 + (self.has("drillmaster") or 0) / 100))
        levels = leveling.gain_xp(c, xp)
        c.last_drill_day = day
        self.store.save_player(self.player)
        console.note(f"Drilled for {d['hours']} hours with {teacher.label()}. Paid {money.fmt(fee)}. +{xp} XP.")
        if levels:
            console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
        self.narrate(f"The player spends {d['hours']} hours sparring and drilling under {teacher.label()}'s eye - "
                     "sweat, bruises, and a few hard-won lessons.", text)

    def tutor(self, teacher, skill: str, text: str) -> None:
        c, t = self.player.character, T["tutoring"]
        have = c.trained.get(skill, 0)
        if have >= t["cap"]:
            console.note(f"There's nothing more the instructor can teach you about {skill}.")
            self.halted = True
            return
        fee = self.fee((t["base_fee"] + t["fee_per_session"] * (have // t["bonus"])) * (1 - self.mech("arcane_tutor") / 100))
        if not self.pay_for_training(fee, f"a lesson in {skill}"):
            return
        self.advance(t["hours"] * 60 // (2 if self.owns("meditative_study") else 1))
        c.trained[skill] = min(t["cap"], have + t["bonus"])
        self.store.save_player(self.player)
        console.note(f"Studied {skill} with {teacher.label()}. Paid {money.fmt(fee)}. "
                     f"{skill.capitalize()} +{c.trained[skill]}% from training.")
        self.narrate(f"The player spends {t['hours']} hours learning {skill} from {teacher.label()} - practice, "
                     "correction, and the knack of it starting to settle in.", text)

    def offer_abilities(self, teacher, request: str) -> None:
        c, a = self.player.character, T["abilities"]
        if len(c.actives) >= self.ability_slots():
            nxt = (len(c.actives) - a["starting"] + 1) * a["levels_per_new"]
            console.note(f"You can't take on another ability yet - you'll have room for one more at level {nxt}.")
            self.halted = True
            return
        console.wait(f"{teacher.label().capitalize()} considers what to teach you.")
        try:
            result = generate("learn_abilities", prompts.LEARN_SYSTEM, prompts.learn_user(c, request, a["options"]),
                              LearnSet, max_tokens=1500,
                              validation_context={"count": a["options"], "reserved_names": [x.name for x in c.actives]})
        except LLMError:
            console.note("The instructor can't settle on what to teach you right now. Ask again in a moment.")
            self.halted = True
            return
        self.learn_options = [materialize_active(p) for p in result.skills]
        self.learn_request = request
        fee = self.fee((a["base_fee"] + a["fee_per_level"] * c.level) * (1 - self.mech("spell_scholar") / 100))
        console.show_actives(self.learn_options)
        console.note(f"Learning one costs {money.words(fee)} and {a['hours']} hours. Say which you'll learn.")

    def on_learn_ability(self, intent, text: str) -> None:
        options = getattr(self, "learn_options", None)
        teacher = self.instructor_here()
        if not options or not teacher:
            console.note("Ask the instructor to teach you something first.")
            self.halted = True
            return
        import re
        words = f"{intent.item} {text}".lower()
        m = re.search(r"\b([1-9])\b", words)
        pick = options[int(m.group(1)) - 1] if m and int(m.group(1)) <= len(options) else \
            next((o for o in options if o.name.lower() in words), None)
        if not pick:
            console.note("Which one? Say its number or name.")
            self.halted = True
            return
        c, a = self.player.character, T["abilities"]
        fee = self.fee((a["base_fee"] + a["fee_per_level"] * c.level) * (1 - self.mech("spell_scholar") / 100))
        if not self.pay_for_training(fee, f"learning {pick.name}"):
            return
        if pick.resource.value == "mana":
            req = (self.learn_request or "").lower() + " " + pick.description.lower()
            pick.attribute = next((attr for attr, ws in DISCIPLINE_WORDS.items() if any(w in req for w in ws)),
                                  c.casting_attribute or "intelligence")
        self.advance(a["hours"] * 60 // (2 if self.owns("spell_scholar") else 1))
        c.actives.append(pick)
        self.learn_options = None
        teacher.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                       text=f"Taught the stranger {pick.name}."))
        self.store.save_npc(teacher)
        self.store.save_player(self.player)
        uses = f" (uses {pick.attribute})" if pick.attribute else ""
        console.note(f"Learned {pick.name}{uses}. Paid {money.fmt(fee)}.")
        self.narrate(f"The player spends {a['hours']} hours learning {pick.name} from {teacher.label()}: "
                     f"{pick.description}", text)
