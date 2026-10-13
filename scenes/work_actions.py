"""Odd jobs for NPCs, and skinning or butchering what you kill."""

import random
import re
from pathlib import Path

import yaml

from engine import clock, crafting, inventory as inv, items, loot, money, pools
from llm.contracts import WorkOffer
from llm.gateway import generate
from npc.models import Memory
from ui import console

ROOT = Path(__file__).resolve().parent.parent
W = yaml.safe_load((ROOT / "data" / "rules" / "work.yaml").read_text(encoding="utf-8"))


PAY_WORDS = re.compile(r"\b(pay|paid|wage|wages|coin|coins|copper|coppers|silver|gold|penny|pennies|reward|earn)\b", re.I)
TASK_WORDS = re.compile(r"\b(work|job|task|chore|chores|haul|carry|labou?r|help|clear|load|dig|chop|tend|mend|fetch|move)\b", re.I)


class WorkActions:

    def promises_pay(self, speech: str) -> bool:
        """Does an NPC's line promise pay for a task, whether or not the reply carried a structured offer?"""
        return bool(PAY_WORDS.search(speech) and TASK_WORDS.search(speech))

    def inferred_offer(self, npc, speech: str) -> WorkOffer:
        """The NPC promised pay without making a formal offer: read the task off what they said, at honest wages."""
        try:
            got = generate("work_offer_read",
                           "Read the villager's line. If they are offering the stranger paid work, give the task as a short phrase "
                           "(like 'load the grain onto the wagon'), how many minutes it should take, and the pay in copper "
                           "(0 if no amount was named). Respond only with JSON.",
                           f"{npc.label()} says: {speech}", WorkOffer, temperature=0.1, max_tokens=120)
            if got.task.strip():
                return got
        except Exception:
            pass
        return WorkOffer(task=f"help {npc.label()} with the work described", pay=0, minutes=60)

    def record_work_offer(self, offer, npc) -> None:
        """Keep an NPC's job offer, held to honest wages."""
        minutes = max(15, min(W["max_minutes"], offer.minutes or 60))
        fair = W["wage_per_hour"] * minutes / 60
        pay = round(max(fair * (1 - W["wage_spread"]), min(fair * (1 + W["wage_spread"]), offer.pay or fair)))
        npc.work_offer = {"task": offer.task.strip(), "pay": max(1, pay), "minutes": minutes}
        self.store.save_npc(npc)
        console.debug(f"Work offered: {offer.task.strip()} - {money.words(pay)}, about "
                     f"{clock.describe_duration(minutes)}.")

    def worker_for(self, intent):
        for nid in (intent.target, self.partner.id if self.partner else "", self.last_spoken or ""):
            npc = next((n for n in self.present if n.id == nid), None)
            if npc:
                return npc
        return next((n for n in self.present if n.work_offer), None)

    def on_work(self, intent, text: str) -> None:
        npc = self.worker_for(intent)
        c = self.player.character
        if npc and npc.work_offer:
            job = npc.work_offer
            tending = self.owns("tireless_tending")
            self.advance(job["minutes"] // 2 if tending else job["minutes"], exert=True)
            spend = 0 if tending else pools.maximum(c, "stamina") * W["stamina_per_hour"] / 100 * job["minutes"] / 60
            c.stamina = max(0, pools.current(c, "stamina") - spend)
            job["pay"] = round(job["pay"] * (1 + (pools.mechanic(c, "good_employer") or 0) / 100))
            c.coins += job["pay"]
            npc.trust = min(100, npc.trust + W["trust_on_finish"])
            npc.work_offer = None
            self.reputation_change("work_done")
            npc.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                       text=f"The stranger did the work I asked - {job['task']} - and I paid "
                                            f"{money.words(job['pay'])}."))
            self.store.save_npc(npc)
            self.store.save_player(self.player)
            console.note(f"Work done: {job['task']}. {npc.label().capitalize()} pays you {money.fmt(job['pay'])}. "
                         f"Purse: {money.fmt(c.coins)}")
            self.narrate(f"The player spends {clock.describe_duration(job['minutes'])} working: {job['task']}. When "
                         f"it's done, {npc.label()} pays them {money.words(job['pay'])} as agreed. Tell it as a short "
                         "passage of honest work and its end.", text)
            return
        tending = self.owns("tireless_tending")
        minutes = 30 if tending else 60
        self.advance(minutes, exert=True)
        if not tending:
            c.stamina = max(0, pools.current(c, "stamina") - pools.maximum(c, "stamina") * W["stamina_per_hour"] / 100)
        if npc:
            times = 2 if self.owns("helping_hand") else 1
            npc.trust = min(100, npc.trust + W["unpaid_trust"] * times)
            for _ in range(times):
                self.reputation_change("work_done")
            self.mercy_spreads()
            npc.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                       text="The stranger pitched in and helped me with my work, unasked and unpaid."))
            self.store.save_npc(npc)
        self.store.save_player(self.player)
        who = f" alongside {npc.label()}" if npc else ""
        self.narrate(f"The player spends an hour working{who}. No pay was agreed, so none changes hands - but the "
                     "help is noticed.", text)

    def on_harvest(self, intent, text: str) -> None:
        state = self.store.load_place(self.player.location)
        limit = W["carcass_hours"] * 60
        state.carcasses = [k for k in state.carcasses if self.minutes - k["minute"] < limit]
        if not state.carcasses:
            self.store.save_place(state)
            console.note("There's nothing here to skin or butcher.")
            self.halted = True
            return
        c = self.player.character
        chance = W["skin_chance"] + min(0.3, c.crafting_skill / 333)
        bonus = ((pools.mechanic(c, "scavenger") or 0) + (pools.mechanic(c, "butcher") or 0)) / 100
        found, bodies = [], len(state.carcasses)
        for k in state.carcasses:
            creature = self.world.bestiary.get(k["creature"])
            rounds = 2 if (self.owns("trophy_hunter") and creature and creature.size in ("Large", "Huge", "Gargantuan")) else 1
            for _ in range(rounds):
                for m in items.MATERIALS.values():
                    if k["creature"] in m.drops_from and random.random() < chance + bonus:
                        found.append(items.make_raw(m.id))
                for g in inv.GOODS.values():
                    if k["creature"] in g.drops_from and random.random() < chance + 0.2:
                        found.append(inv.make_good(g.id, random.randint(1, 2)))
            if creature:
                found += loot.found_materials(creature.category, k.get("level", 1), random, bonus)
            if self.owns("bone_collector") and random.random() < 0.6:
                found.append(items.make_raw("bone"))
        state.carcasses = []
        self.store.save_place(state)
        self.advance(W["skin_minutes"] * bodies, exert=True)
        crafting.raise_skill(c, 0.3 * bodies)
        for item in found:
            self.to_pack(item)
        self.store.save_player(self.player)
        got = ", ".join(inv.label(i) for i in found) or "nothing usable - the hides were too torn"
        console.note(f"Harvested: {got}.")
        self.narrate(f"The player spends {clock.describe_duration(W['skin_minutes'] * bodies)} skinning and butchering "
                     f"the fallen ({bodies}), and takes {got}.", text)
