"""The audit gate as the world scene uses it: the facts it checks against, the three model calls, the player-facing fallback and the turn log."""
import time

import config
from engine import intent_audit as ia
from llm.contracts import AuditMeaning, AuditVerdict, Clarify
from llm.gateway import generate
from ui import console

MEANING_SYSTEM = """You read one line a player typed in a role-playing game and say, in one short plain sentence, what they want to do.
Use only their words and the scene facts. Do not add actions they did not ask for, and do not invent items or people."""

CLARIFY_SYSTEM = """A line the player typed in a role-playing game could not be acted on. Ask them, in one short line and in character, what they
meant - as the person they are speaking to would ask it, or, when nobody is being spoken to, as a plain beat from the narrator in which
nobody speaks. Offer the one or two readings that fit the scene ("Pay the fee, or something else?"). Never explain the game, never say
'I'm not sure', never list options with numbers. speaker: the id of the one being spoken to when there is one, else 'narrator'."""

COMPARE_SYSTEM = """You check whether a PLAN does what a PLAYER MEANT in a role-playing game.
matches = true if the plan carries out what they meant, even loosely or in different words.
matches = false only if the plan does something else, adds an action they did not ask for, or leaves out something they asked for.
Money paid for a service (a fee, a registration, a bribe, a tip) is not the same as buying goods from a shop.
Give a short reason."""


class AuditActions:

    def situation(self) -> ia.Situation:
        sit = ia.Situation(
            present=__import__("engine.truth", fromlist=["scene_of"]).scene_of(self).present_ids(),   # (f313) the one list everyone reads
            abilities={k: a.name for a in self.player.character.actives for k in (a.id.lower(), a.name.lower())},
            place=self.place.name, wildlife=bool(self.wildlife),
            partner=self.partner.label() if self.partner else "",
            workers={n.id for n in self.present if n.work_offer})
        sit.lines = [f"Place: {sit.place}.", "People here: " + (", ".join(sit.present.values()) or "no one") + ".",
                     "Talking with: " + (sit.partner or "no one") + ".",
                     "Pack: " + (", ".join(self.pack_names()) or "empty") + "."]
        return sit

    def pack_names(self) -> list[str]:
        try:
            from engine import inventory as inv
            return [inv.label(i) for i in self.pack]
        except Exception:
            return []

    # --- the three model calls the gate is handed ---
    def audit_asker(self):
        scene = self

        class Ask:
            def meaning(self, text, sit):
                return generate("audit_meaning", MEANING_SYSTEM, "\n".join(sit.lines) + f'\nPLAYER TYPED: "{text}"',
                                AuditMeaning, temperature=0.1, retries=1, max_tokens=120).meaning

            def compare(self, text, meaning, described, risk):
                v = generate("audit_compare", COMPARE_SYSTEM,
                             f'PLAYER TYPED: "{text}"\nPLAYER MEANT: {meaning}\nPLAN:\n{described}\nTHINGS TO WATCH: {", ".join(risk)}',
                             AuditVerdict, temperature=0.1, retries=1, max_tokens=160)
                return v.matches, v.reason

            def propose(self, text, hint):
                return scene.interpret(text, hint)
        return Ask()

    def audit_plan(self, text: str, plan: list, raw_plan: list | None = None) -> list | None:
        """The plan after the audit, or None when it could not be made sense of (the player is asked to reword; nothing happens)."""
        start = time.perf_counter()
        sit = self.situation()
        if getattr(config, "AUDIT_ENABLED", True):
            res = ia.audit(text, plan, sit, self.audit_asker())
        else:
            res = ia.Result("skipped", plan)
        self.log_turn(text, sit, raw_plan, res, time.perf_counter() - start)
        if res.status == "changed":
            console.debug(f"audit changed the plan: {res.verdict or res.reason}")
        if res.status == "failed":
            console.debug(f"audit could not make sense of the plan: {res.reason}")
            self.ask_back("audit_failed", text, res.reason, res.meaning)                 # (f321) the world asks; no system note
            return None
        if res.status == "unsure":                                                      # (f332) flagged, and the check itself could not be made: fail closed
            console.debug(f"audit could not be made on a flagged plan: {res.reason}")
            self.ask_back("audit_unsure", text, "the line looked like it might mean something else, and it could not be checked", res.meaning)
            return None
        return res.plan

    def ask_back(self, kind: str, text: str, why: str, meaning: str = "") -> None:
        """(f321) A line that could not be read is answered with one question in character - from the one being spoken to, or a beat from
        the narrator - and the player's next line is read together with this one. Every one is logged as a refusal."""
        from engine import refusals
        if getattr(self, "pending_clarify", None):                       # asked once already and still unread: say so plainly, once
            refusals.note("clarify_failed", text, why, self.player.location, self.store.meta.turn)
            self.pending_clarify = None
            console.note("That still didn't come through - try it in different words.")
            return
        people = ", ".join(f"{n.id}: {n.label()}" for n in self.present) or "nobody"
        partner = self.partner.id if self.partner else ""
        asked = ""
        try:
            req = (f'PLAYER TYPED: "{text}"\n' + (f"A READING OF IT: {meaning}\n" if meaning else "") + f"WHY IT COULD NOT BE ACTED ON: {why}\n"
                   f"PEOPLE HERE (id: name): {people}\nSPEAKING WITH: {partner or 'nobody'}\nPLACE: {self.place.name}")
            r = generate("clarify", CLARIFY_SYSTEM, req, Clarify, temperature=0.4, retries=1, max_tokens=120)
            asked = " ".join(r.line.split())
            if asked:
                who = next((n for n in self.present if n.id == r.speaker), None) or (self.partner if r.speaker == partner else None)
                if who is not None:
                    console.npc_says(who.label(), asked, "")
                else:
                    console.narrate(asked)
        except Exception as e:
            console.debug(f"clarify: no question ({e})")
        if not asked:
            console.note("I'm not sure what you meant - could you say it another way?")
        refusals.note(kind, text, why, self.player.location, self.store.meta.turn, asked)
        self.pending_clarify = {"text": text, "question": asked}

    def log_turn(self, text, sit, raw_plan, res, seconds):
        """The interpreted line's row in the turn log (engine/turnlog.py): the scene the gate checked against, the plan as read and as
        it ran, the audit's verdict, and every interpreter call made for the line in full."""
        self.handled(text, "interpret",
                     place_name=sit.place, scene=sit.lines, present=sit.present, abilities=sorted(set(sit.abilities)), wildlife=sit.wildlife,
                     partner=self.partner.id if self.partner else "", last_spoken=self.last_spoken or "",
                     raw=raw_plan, final=[s.model_dump(exclude_defaults=True) for s in res.plan],
                     risk=res.risk, audit=res.status, meaning=res.meaning, described=res.described,
                     verdict=res.verdict, reason=res.reason, calls=res.calls, seconds=round(seconds, 2),
                     interpreter=list(getattr(self, "interpret_calls", [])))
