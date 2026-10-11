"""Checks in play: the engine rolls, shows the outcome DM-style, and tells the narrator and NPCs what happened."""

import random

from engine import checks, clock, money
from npc.life import promote
from npc.models import Memory
from ui import console

R = checks.RULES


class CheckActions:

    def check_triggers(self, check: str, talking: bool) -> set[str]:
        found = {"always", "out_of_combat"} | self.conditions()
        if talking:
            found.add("in_conversation")
        if check == "performance":
            found.add("while_performing")
        return found

    def resolve(self, check: str, npc=None, talking: bool = False, text: str = "", extra=()) -> str:
        odds, why = checks.chance(self.player.character, check, self.check_triggers(check, talking), npc,
                                  self.check_bonuses(check, npc, talking, text or getattr(self, "last_text", "")) + list(extra))
        degree, rolled = checks.roll(odds)
        today = clock.day(self.minutes)
        if check == "lore" and self.has("patron_whispers") is not None and self.player.character.whisper_day != today:
            self.player.character.whisper_day = today
            degree = "strong success"
        if check == "persuasion" and degree == "failure" and self.has("dark_charisma") is not None:
            degree = "partial"
        console.debug(f"{check}: {odds:.0f}% ({', '.join(why)}) - rolled {rolled}")
        self.spend_edge(check, npc)
        console.note(checks.label(check, degree))
        if degree == "failure":
            lucky = self.lucky_save()
            if lucky:
                degree = "success"
                console.note(f"A lucky break! You succeeded because of {lucky}.")
        return degree

    def target_npc(self, intent):
        return next((n for n in self.present if n.id == intent.target), None) or \
            (self.partner if self.partner in self.present else None)

    def run_checks(self, intent, text: str) -> bool:
        """Roll the checks an action calls for. Returns True if the checks fully handled the action."""
        self.last_text = text
        if intent.kind == "steal":          # a theft rolls its own bar (scenes/law_actions.py)
            return False
        wanted = [c for c in dict.fromkeys(intent.checks) if c in checks.CHECKS]
        if intent.kind == "give" and any(w in (intent.item or "").lower() for w in self.COIN_WORDS):
            wanted = [c for c in wanted if c != "persuasion"]       # offering coin rolls its own persuasion check (a bribe)
        if not wanted:
            return False
        npc = self.target_npc(intent)
        if npc and npc.tier == "background":
            promote(npc, self.store, self.world, self.catalog)
        events, handled = [], intent.kind in ("look", "other", "search") or not intent.kind
        for check in wanted:
            if check in checks.SOCIAL:
                if not npc:
                    continue
                degree = self.resolve(check, npc, talking=True)
                self.last_social = (check, degree, npc.id)
                self.pending_check = self.social_outcome(check, degree, npc)
                if intent.kind != "talk":
                    intent.kind, intent.target = "talk", npc.id
                    intent.speech = intent.speech or text
                handled = False
            elif check == "insight":
                if not npc:
                    continue
                events.append(self.insight(npc, self.resolve(check, npc)))
            elif check == "stealth":
                events.append(self.stealth(npc, self.resolve(check, npc)))
            elif check == "perception":
                events.append(self.perception(npc, self.resolve(check, npc)))
            elif check == "lore":
                events.append(self.lore(text, self.resolve(check)))
            elif check == "performance":
                events.append(self.performance(self.resolve(check)))
        if events and handled:
            self.narrate(" ".join(events), text)
        elif events:
            self.pending_beats = events
        return handled and bool(events)

    # ---------- outcomes ----------

    def social_outcome(self, check: str, degree: str, npc) -> str:
        what = {"persuasion": "persuade you", "intimidation": "intimidate you", "deception": "deceive you"}[check]
        effect = {
            ("persuasion", "strong success"): "You are genuinely and warmly persuaded, and agree to what they ask within reason.",
            ("persuasion", "success"): "You are persuaded and agree to what they ask within reason.",
            ("persuasion", "partial"): "You are tempted but not convinced - you agree only in part, or want something in return.",
            ("persuasion", "failure"): "You are not persuaded.",
            ("intimidation", "strong success"): "You are badly frightened and give them what they want.",
            ("intimidation", "success"): "You are cowed and comply, resentfully.",
            ("intimidation", "partial"): "You are shaken but hold your ground - you give a little, not all.",
            ("intimidation", "failure"): "You are not frightened. You are offended, and it shows.",
            ("deception", "strong success"): "You believe them completely.",
            ("deception", "success"): "You believe them.",
            ("deception", "partial"): "You half-believe them, but something nags at you.",
            ("deception", "failure"): "You see through the lie, and you know they lied to you.",
        }[(check, degree)]
        trust = {("intimidation", "failure"): -3, ("intimidation", "success"): -1, ("intimidation", "strong success"): -2,
                 ("deception", "failure"): -5, ("persuasion", "strong success"): 2}.get((check, degree), 0)
        if trust:
            npc.trust = max(0, min(100, npc.trust + trust))
            self.store.save_npc(npc)
        if check == "intimidation":
            self.reputation_change("threat")
        if (check, degree) == ("deception", "failure"):
            self.reputation_change("lie_caught")
            npc.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                       text="Caught the stranger in a lie."))
            self.store.save_npc(npc)
        if check in ("persuasion", "intimidation") and degree in ("strong success", "success"):
            from engine import deeds, events
            events.after_deed(self, deeds.log(self.store, "persuade", self.minutes, self.player.location, npc=npc.id,
                                              npc_name=npc.name, how=check, degree=degree))
        return f"[THE GAME HAS DECIDED: they are trying to {what}. {effect} Act on this.]"

    SCALE_TELLS = (" Match the tells to how serious the worry really is: an everyday worry (weather, prices, a bad crop, a sore back, "
                   "a slow week) shows as a passing frown, a sigh or a distracted glance; only grave trouble (danger, guilt, grief, fear for "
                   "someone's life) shows as real distress. Never exaggerate, and never turn a small worry into a dramatic scene.")

    def insight(self, npc, degree: str) -> str:
        who = npc.label()
        if degree == "strong success":
            return (f"The player reads {who} clearly. What weighs on them: {npc.concern} Their nature: "
                    f"{npc.personality} Show how the player picks this up from small tells, then state it plainly." + self.SCALE_TELLS)
        if degree == "success":
            return (f"The player reads {who} well enough: something is weighing on them - {npc.concern} "
                    "Show the tells that give it away, and let the player understand it." + self.SCALE_TELLS)
        if degree == "partial":
            return (f"The player senses {who} is worried about something, but can't tell what. Hint at the general "
                    "shape of it without naming it." + self.SCALE_TELLS)
        return f"The player watches {who} closely but can't read them at all. Nothing gives them away."

    def stealth(self, npc, degree: str) -> str:
        if degree in ("strong success", "success"):
            return "The player stays unnoticed." + (f" {npc.label()} has no idea they are being watched." if npc else "")
        if degree == "partial":
            return "The player is nearly spotted - a glance their way, a moment of doubt - but not quite."
        if npc:
            npc.trust = max(0, npc.trust - 3)
            self.reputation_change("caught_spying")
            npc.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                       text="Caught the stranger watching me from hiding."))
            self.store.save_npc(npc)
            return f"{npc.label()} notices the player watching and is unsettled by it."
        return "The player is noticed - someone or something turns their way."

    def perception(self, npc, degree: str) -> str:
        if degree == "failure":
            return "The player looks carefully but notices nothing out of the ordinary."
        if npc:
            extra = f" Something about it hints at this: {npc.concern}" if degree == "strong success" else ""
            return (f"The player studies {npc.label()} and notices real, telling details of how they look and act "
                    f"(only from: {npc.description} {npc.activity}).{extra}")
        return ("The player searches carefully and notices details others would miss - only from what is actually "
                "in the scene, its marks and anything lying here. Never invent hidden objects or secrets.")

    def lore(self, text: str, degree: str) -> str:
        if degree in ("failure", "partial"):
            return ("The player tries to remember what they know about this, and comes up empty."
                    if degree == "failure" else "The player half-remembers something about this, but can't place it.")
        c = self.player.character
        words = {w.strip(".,?!").lower() for w in text.split() if len(w) > 3}
        scored = []
        for fid, fact in self.world.lore.items():
            if fid in c.knowledge:
                continue
            hits = sum(1 for w in words if w in fact.text.lower())
            if hits:
                scored.append((hits, fid, fact))
        scored.sort(key=lambda x: -x[0])
        found = scored[: (2 if degree == "strong success" else 1) + (1 if self.has("scholars_memory") is not None else 0)]
        if not found:
            return "The player searches their memory, but they know nothing more about this than they did."
        for _, fid, _ in found:
            c.knowledge.append(fid)
        self.store.save_player(self.player)
        return "The player recalls: " + " ".join(f.text for _, _, f in found)

    def performance(self, degree: str) -> str:
        audience = [n for n in self.present]
        if not audience:
            return f"The player performs to no one in particular ({degree})."
        low, high = R["tips"][degree]
        tips = random.randint(low, high) if high else 0
        tips = round(tips * (1 + (self.has("crowd_pleaser") or 0) / 100
                             + ((self.has("crowd_draw") or 0) / 100 if self.companion_here() else 0)))
        if degree in ("strong success", "success"):
            if self.owns("sing_for_supper") and any(n.role == "innkeeper" for n in audience):
                self.player.free_room_day = clock.day(self.minutes)
                console.note("The innkeeper waves off the price of a room tonight.")
            if self.owns("songs_of_the_road"):
                for town in self.neighbor_towns(self.player.location):
                    self.reputation_add(town, 1)
        if degree in ("strong success", "success") and self.has("local_favorite") is not None:
            self.reputation_change("performed")
        if tips and self.place.danger is None:
            self.player.character.coins += tips
            console.note(f"Tips: {money.fmt(tips)}")
        if degree == "strong success":
            for n in audience[:4]:
                n.trust = min(100, n.trust + 1)
                self.store.save_npc(n)
        reaction = {"strong success": "The audience is delighted - applause, a few coins, warm looks.",
                    "success": "It goes over well - a few smiles and a coin or two.",
                    "partial": "A mixed reception - some listen, most go back to what they were doing.",
                    "failure": "It falls flat - awkward silence, a few winces."}[degree]
        return f"The player performs for the people here. {reaction}"
