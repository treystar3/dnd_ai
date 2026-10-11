"""The audit gate as the world scene uses it: the facts it checks against, the three model calls, the player-facing fallback and the turn log."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from engine import intent_audit as ia
from llm.contracts import AuditMeaning, AuditVerdict
from llm.gateway import generate, trim_log
from ui import console

MEANING_SYSTEM = """You read one line a player typed in a role-playing game and say, in one short plain sentence, what they want to do.
Use only their words and the scene facts. Do not add actions they did not ask for, and do not invent items or people."""

COMPARE_SYSTEM = """You check whether a PLAN does what a PLAYER MEANT in a role-playing game.
matches = true if the plan carries out what they meant, even loosely or in different words.
matches = false only if the plan does something else, adds an action they did not ask for, or leaves out something they asked for.
Money paid for a service (a fee, a registration, a bribe, a tip) is not the same as buying goods from a shop.
Give a short reason."""


class AuditActions:
    audit_writes = 0

    def situation(self) -> ia.Situation:
        sit = ia.Situation(
            present={n.id: n.label() for n in self.present},
            abilities={k: a.name for a in self.player.character.actives for k in (a.id.lower(), a.name.lower())},
            place=self.place.name, wildlife=bool(self.wildlife),
            partner=self.partner.label() if self.partner else "")
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
            console.note("I'm not sure what you meant - could you say it another way? (" + res.reason + ")")
            return None
        return res.plan

    def log_turn(self, text, sit, raw_plan, res, seconds):
        try:
            path = Path(getattr(config, "TURN_LOG_PATH", "logs/turns.jsonl"))
            path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "time": datetime.now(timezone.utc).isoformat(), "turn": self.store.meta.turn, "text": text,
                "scene": sit.lines, "present": sit.present, "abilities": sorted(set(sit.abilities)), "wildlife": sit.wildlife, "raw": raw_plan,
                "final": [s.model_dump(exclude_defaults=True) for s in res.plan],
                "risk": res.risk, "audit": res.status, "meaning": res.meaning, "described": res.described,
                "verdict": res.verdict, "reason": res.reason, "calls": res.calls, "seconds": round(seconds, 2),
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            AuditActions.audit_writes += 1
            if AuditActions.audit_writes % 50 == 1:
                trim_log(path)
        except OSError:
            pass
