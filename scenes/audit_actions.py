"""The audit gate as the world scene uses it: the facts it checks against, the three model calls, the player-facing fallback and the turn log."""
import re
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
            workers={n.id for n in self.present if n.work_offer}, people_at=self.people_at)
        sit.lines = [f"Place: {sit.place}.", "People here: " + (", ".join(sit.present.values()) or "no one") + ".",
                     "Talking with: " + (sit.partner or "no one") + ".",
                     "Pack: " + (", ".join(self.pack_names()) or "empty") + "."]
        return sit

    def people_at(self, place: str) -> set[str]:
        """(f384) Who is found at a place, by id, name, label and work, lower case: what a talk after a walk may be aimed at."""
        low = (place or "").strip().lower()
        pid = place if place in self.world.places else next((p for p, pl in self.world.places.items() if pl.name.lower() in (low, f"the {low}")), "")
        if not pid:
            return set()
        out = set()
        for rid in self.store.load_place(pid).residents:
            try:
                n = self.store.load_npc(rid)
            except Exception:
                continue
            if n.gone:
                continue
            role = n.role.replace("_", " ")
            out |= {n.id.lower(), n.name.lower(), n.label().lower(), role, role.split()[-1]}
        return out

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
        row = self.absent_known(plan, sit)
        if row is not None:                                                        # (f342) the clerk at night, the smith at the inn: the engine knows where they are
            console.debug(f"audit: {row.label()} is not here; the engine says where they are")
            self.log_turn(text, sit, raw_plan, ia.Result("answered", plan, reason=f"'{row.id}' is not here: the engine said where they are"), time.perf_counter() - start)
            self.go_to_person(row, text)
            return None
        if getattr(config, "AUDIT_ENABLED", True):
            res = ia.audit(text, plan, sit, self.audit_asker())
        else:
            res = ia.Result("skipped", ia.fix(plan))              # the model calls are off; the plain repairs (repeats, an 'other' restating a step) still run
        if res.status in ("skipped", "unchanged") and len(res.plan) != len(plan):   # the audit's own repair (intent_audit.fix) is recorded like the others
            from scenes import plan_repairs
            self.__dict__.setdefault("repairs", []).append({"rule": "audit_fix", "before": plan_repairs.brief(plan), "after": plan_repairs.brief(res.plan)})
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

    def absent_known(self, plan: list, sit):
        """(f342) A one-step talk aimed at someone of this town who is not here (the clerk after hours, the smith at the inn of an evening):
        the engine knows where they are, so it says so or walks there (go_to_person) instead of spending two audit calls and asking the
        player what they meant, which one run did twice for "I ask the clerk what contracts are open". The row, or None."""
        if len(plan) != 1 or getattr(plan[0], "kind", "") != "talk":
            return None
        probs = ia.problems(plan, sit)
        m = re.search(r"aimed at '([^']+)', who is not here", probs[0]) if len(probs) == 1 else None
        if not m or not self.store.npc_exists(m.group(1)):
            return None
        from engine import mapview, retrieval
        top = mapview.top_of(self.world, self.player.location)
        if not top or self.world.places[top].danger:
            return None
        return next((r for r in retrieval.people_in_town(self.store, self.world, top) if r.id == m.group(1)), None)

    def report_content(self, note: str) -> str:
        """(f364) The player flags what they just read: the last passages and lines shown, the player's note, and the model calls of the last
        few turns are saved together under REPORTS_PATH, and nothing is sent anywhere. The file is theirs to send, and the record a store
        asks for. Returns the path."""
        import json
        from datetime import datetime
        from pathlib import Path
        from engine import refusals
        folder = Path(getattr(config, "REPORTS_PATH", "logs/reports"))
        folder.mkdir(parents=True, exist_ok=True)
        turn = self.store.meta.turn
        calls = []
        try:
            lines = Path(config.LOG_PATH).read_text(encoding="utf-8").splitlines()[-400:]
            for line in lines:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row.get("turn"), int) and row["turn"] >= turn - 3:
                    calls.append({k: row.get(k) for k in ("turn", "task", "attempt", "error", "raw")})
        except OSError:
            pass
        report = {"time": datetime.now().isoformat(timespec="seconds"), "save": getattr(self.store, "name", ""), "turn": turn,
                  "place": self.player.location, "note": note,
                  "shown": list(getattr(self, "recent_narration", [])[-6:]),
                  "said": list(getattr(self.partner, "said", [])[-3:]) if getattr(self, "partner", None) else [],
                  "calls": calls[-24:]}
        path = folder / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_turn{turn}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        refusals.note("reported", note or "(no note)", "the player flagged what was shown", self.player.location, turn)
        console.note(f"Reported. What you just read, your note and the calls behind it are saved in {path}. Nothing is sent anywhere.")
        return str(path)

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
                     repairs=list(getattr(self, "repairs", [])), interpreter=list(getattr(self, "interpret_calls", [])))
