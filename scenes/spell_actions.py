"""(f397) Learning a spell's next rank (engine/spells.py; data/rules/spells.yaml): from a spell book found in the world or bought from a
loremaster, or from a teacher (a guild instructor or a loremaster), once the character's level allows it. The new rank is a spell of its
own, of the same element and form, a rank higher; the model names it, told what rank it is (never a numeral, never another game's
naming), and the engine makes everything else. It takes the place of the rank below among the spells the character brings."""
from __future__ import annotations

import re

from engine import money, spells
from llm.contracts import SpellRankName
from llm.gateway import LLMError, generate
from scenes.intercepts import Intercept
from ui import console

BOOK_VERBS = re.compile(r"\b(read|reads|reading|study|studies|studying|open|opens|use|uses|learn|learns|pore over|leaf through)\b", re.I)

NAME_SYSTEM = """You name spells in a fantasy role-playing game. A spell the character already knows has grown: they have learned a
higher rank of it, a stronger working of the same magic. Give the new rank a name of its own.
- It keeps the spell's element and the way it is cast (its form), and it is grander and more dangerous than the rank before: a plain
  name at the low ranks (Fire Bolt), weightier at the middle ranks (Lava Lance, Flame Strike), a name for a master at the high ranks.
- A new name, not the old one with a word or a numeral added. Never a numeral.
- Never a naming pattern from another game (Fira, Firaga, Blizzara, Thundaga and the like).
- description: one sentence of how it looks and feels when it is cast, in the second person.
Respond only with JSON matching the schema."""


NAMED_SYSTEM = """You name a great spell in a fantasy role-playing game: a named working, rare and old, sealed in a codex found after a hard
fight. Give it a name of its own that fits its element and the way it is cast - two to four words, grand and specific (Starfall, The Drowning
Bell, Ashen Crown). Never a numeral, never another game's spell names (Ultima, Flare, Meteor, Holy, Firaga and the like).
description: one sentence of how it looks and feels when it is cast, in the second person.
Respond only with JSON matching the schema."""


class SpellActions:
    INTERCEPTS = (Intercept("spell_book", 75, "spell_book_turn", "reading a spell book the player carries (f397)"),)

    def spell_book_turn(self, text: str) -> bool:
        """'I study the tome of the third circle': a spell book in the pack, named, with a reading verb, is read; never left to a guess.
        A codex the same."""
        if getattr(self, "combat", None) or not BOOK_VERBS.search(text or ""):
            return False
        from engine import inventory as inv
        low = (text or "").lower()
        codex = next((i for i in self.pack if spells.is_codex(i) and re.search(r"\bcodex\b", low)), None)
        if codex is not None:
            self.read_codex(codex, text)
            return True
        book = next((i for i in self.pack if spells.book_rank(i) and (inv.GOODS[i.good].name in low or re.search(r"\b(tome|spell ?book|grimoire|codex)\b", low))), None)
        if book is None:
            return False
        self.read_spell_book(book, text)
        return True

    def rank_teacher(self):
        return next((n for n in self.present if spells.teaches(n)), None)

    def name_rank(self, t, rank: int) -> tuple[str, str]:
        """The model's name and description for rank `rank` of the line `t` heads; plain ones when it cannot give them."""
        c = self.player.character
        line = spells.lines(c).get(t.line or t.id) or [t]
        req = (f"THE SPELL: {t.name} - {t.description}\n"
               f"ITS ELEMENT: {t.element or 'none: plain force'}\nITS FORM: {spells.FORMS[spells.form_of(t)]['label']}: "
               f"{spells.form_text(spells.form_of(t))}\n"
               f"ITS RANKS SO FAR: {', '.join(f'{a.name} (rank {spells.numeral(a.rank)})' for a in line)}\n"
               f"THE NEW RANK: {spells.numeral(rank)} of {spells.numeral(spells.TOP)}\n"
               f"THE CHARACTER: {c.custom_class or c.archetype.value}")
        try:
            r = generate("spell_rank", NAME_SYSTEM, req, SpellRankName, temperature=0.8, retries=2, max_tokens=200,
                         validation_context={"taken": [a.name for a in c.actives]})
            return r.name, r.description
        except LLMError:
            return "", ""

    def learn_rank(self, line: str, how: str, text: str, hours: float) -> object | None:
        """The next rank of a line, learned: named, put in the book, brought in place of the rank below, the time spent."""
        c = self.player.character
        t = spells.top(c, line)
        r = spells.next_rank(c, line)
        if t is None or r is None:
            return None
        name, description = self.name_rank(t, r)
        new = spells.learn(c, line, name, description)
        if new is None:
            return None
        self.advance(int(hours * 60))
        self.store.save_player(self.player)
        console.note(f"Learned {new.name}: {spells.card(new)}, {spells.mana(new)} mana. It takes the place of {t.name} among the spells you "
                     f"bring; {t.name} stays in your book.")
        self.narrate(f"The player spends {hours:g} hours {how}, and learns {new.name}, a stronger working of {t.name}: {new.description} "
                     "Show the study and the first time it answers them.", text)
        return new

    # ---- a spell book
    def read_spell_book(self, item, text: str) -> None:
        from engine import inventory as inv
        c = self.player.character
        rank = spells.book_rank(item)
        good = inv.GOODS[item.good]
        ready = spells.learnable(c, rank)
        if not ready:
            self.halted = True
            if spells.learn_level(rank) > c.level:
                console.note(f"You can follow the first pages of the {good.name}, but the working is beyond you until level "
                             f"{spells.learn_level(rank)}.")
            elif not spells.lines(c):
                console.note(f"The {good.name} deepens spells you already know, and you know none it could deepen.")
            else:
                below = [a.name for a in (spells.top(c, l) for l in spells.lines(c)) if a is not None and a.rank < rank - 1]
                console.note(f"The {good.name} teaches rank {spells.numeral(rank)}; none of your spells is at rank {spells.numeral(rank - 1)} "
                             "to take it" + (f" ({', '.join(below)} must grow first)." if below else "."))
            return
        line = self.pick_line(ready, text)
        if line is None:
            self.halted = True
            console.note(f"The {good.name} could deepen " + ", ".join(a.name for _, a, _r in ready) +
                         ". Say which: 'I study the tome for " + ready[0][1].name + "'.")
            return
        inv.take(self.pack, good.name, 1)
        self.learn_rank(line, f"studying the {good.name}", text, spells.S["teach"]["hours"])

    def pick_line(self, ready: list, text: str) -> str | None:
        """The line the words name, or the only one there is."""
        low = (text or "").lower()
        named = [line for line, a, _r in ready if any(w in low for w in re.findall(r"[a-z]{4,}", spells.plain_name(a.name).lower()))]
        if len(named) == 1:
            return named[0]
        return ready[0][0] if len(ready) == 1 else None

    # ---- a teacher
    def offer_ranks(self, teacher, text: str) -> None:
        c = self.player.character
        ready = spells.learnable(c)
        if not ready:
            self.halted = True
            ahead = spells.waiting(c)
            if ahead:
                soonest = min(ahead, key=lambda x: spells.learn_level(x[2]))
                console.note(f"{teacher.label().capitalize()} shakes their head: you are not ready for more yet. Rank "
                             f"{spells.numeral(soonest[2])} of {soonest[1].name} is within reach at level {spells.learn_level(soonest[2])}.")
            else:
                console.note(f"{teacher.label().capitalize()} has no deeper working to teach you: your spells are at their highest rank, "
                             "or you know none that grow by rank.")
            return
        self.rank_options = ready
        console.note(f"{teacher.label().capitalize()} can teach you:")
        for i, (line, a, r) in enumerate(ready, 1):
            console.note(f"  {i}. {a.name} to rank {spells.numeral(r)} ({spells.FORMS[spells.form_of(a)]['label'].lower()}) - "
                         f"{money.words(self.fee(spells.teacher_fee(r)))}, {spells.S['teach']['hours']} hours")
        console.note("Say which you'll learn.")

    def take_rank_lesson(self, intent, text: str) -> bool:
        """The player picks one of the ranks a teacher offered. True if the line was about them."""
        ready = getattr(self, "rank_options", None)
        teacher = self.rank_teacher()
        if not ready or not teacher:
            return False
        words = f"{intent.item} {text}".lower()
        m = re.search(r"\b([1-9])\b", words)
        line = ready[int(m.group(1)) - 1][0] if m and int(m.group(1)) <= len(ready) else self.pick_line(ready, words)
        if line is None:
            console.note("Which one? Say its number or name.")
            self.halted = True
            return True
        r = spells.next_rank(self.player.character, line)
        fee = self.fee(spells.teacher_fee(r))
        if not self.pay_for_training(fee, f"rank {spells.numeral(r)}"):
            return True
        self.rank_options = None
        new = self.learn_rank(line, f"learning from {teacher.label()}", text, spells.S["teach"]["hours"])
        if new is not None:
            console.note(f"Paid {money.fmt(fee)}.")
        return True

    # ---- a codex: a named spell
    def name_codex(self, item, found_with: str = "") -> None:
        """The model names the spell a codex holds when it is found; a plain name when it cannot."""
        sp = item.spell
        req = (f"ITS ELEMENT: {sp['element']}\nITS FORM: {spells.FORMS[sp['form']]['label']}: {spells.form_text(sp['form'])}\n"
               f"FOUND: {('after ' + found_with) if found_with else 'in the world'}")
        try:
            r = generate("named_spell", NAMED_SYSTEM, req, SpellRankName, temperature=0.9, retries=2, max_tokens=200,
                         validation_context={"taken": [a.name for a in self.player.character.actives]})
            sp["name"], sp["description"] = r.name, r.description
        except LLMError:
            sp["name"] = f"The {sp['element'].capitalize()} {spells.FORMS[sp['form']]['label']}"
            sp["description"] = ""
        item.name = spells.codex_name(item)

    def read_codex(self, item, text: str) -> None:
        c = self.player.character
        why = spells.can_read(c, item)
        if why:
            console.note(why)
            self.halted = True
            return
        self.pack.remove(item)
        a = spells.learn_named(c, item)
        self.advance(int(spells.S["teach"]["hours"] * 60))
        self.store.save_player(self.player)
        console.note(f"Learned {a.name}: a named {spells.FORMS[spells.form_of(a)]['label'].lower()}, {spells.mana(a)} mana, once a fight and "
                     f"then not again for {a.cooldown_days} day{'s' if a.cooldown_days != 1 else ''}.")
        self.narrate(f"The player spends hours over the {item.name}, and learns {a.name}: {a.description} The codex is spent in the learning. "
                     "Show the study, and the first stirring of the working.", text)

    # ---- telling the player
    def ranks_in_reach(self, old_level: int) -> None:
        """At a level-up: a rank that has just come within reach, said once."""
        c = self.player.character
        new = [r for r, spec in spells.RANKS.items() if old_level < spec["learn"] <= c.level]
        if new and spells.lines(c):
            r = max(new)
            console.note(f"Rank {spells.numeral(r)} spells are now within your reach: a spell book of that circle, or a teacher (a guild "
                         "instructor or a loremaster), can deepen the spells you know.")
