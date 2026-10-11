"""Theft, force and the law as the world scene runs them. The dice, bars and numbers are in engine/law.py and data/rules/law.yaml.

A theft takes something that really exists - a ware on a stall, a piece of gear in stock, a story object already found on this person or
in this place - or, once per person or place, a story object the player went looking for that the model judges plausible. The model names
and describes that object; the engine owns whether it exists, what it is worth, and who sees what."""
import re

from core.models import KeyItem
from engine import checks, clock, deeds, inventory as inv, items, law, money, pulse
from llm.contracts import ObjectVerdict
from llm.gateway import generate
from npc.models import Memory
from ui import console

H = law.H

PLAUSIBLE_SYSTEM = """You decide whether something a player went looking for plausibly exists on a person or in a place in a role-playing game.
Say yes to ordinary belongings of that kind of person or place (a merchant keeps a ledger and letters, a priest a prayer book,
a smith their tools, a captain a seal, a hall a strongbox of papers). Say no to the absurd or magical (a dragon egg in a baker's
pocket), to anything vague ("something valuable", "anything"), and to money, food, drink, weapons and armor.
If plausible, give it a short name (two to four words), one plain sentence describing it (nothing magical unless the place is
holy or arcane), and its worth: trinket (little), ordinary, valuable, or priceless (a relic or a great secret).
If not, say why in a few words."""


def _words(text: str) -> set[str]:
    stop = {"the", "my", "a", "an", "some", "of", "his", "her", "their", "its", "our", "your", "from", "out", "off", "up", "and", "for", "to", "in", "take", "steal"}
    return {w.rstrip("s") for w in re.findall(r"[a-z]+", text.lower().replace("_", " ")) if len(w) > 2 and w not in stop}


class LawActions:
    # ------------------------------------------------------------------ heat bookkeeping
    def town_here(self) -> str:
        return pulse.town_of(self.world, self.player.location)

    def lawless_here(self) -> bool:
        return bool(self.world.places[self.town_here()].danger)

    def heat_here(self) -> int:
        return law.current_heat(self.player, self.town_here(), clock.day(self.minutes))

    def heat_price(self) -> float:
        return law.price_factor(self.heat_here())

    def heat_trust(self) -> int:
        return H["first_meeting_trust"] if self.heat_here() >= H["tiers"]["cold"] else 0

    def heat_line(self) -> str:
        return law.tier(self.heat_here())

    # ------------------------------------------------------------------ steal
    def watchers(self, owner) -> list:
        """Other people here who could see: not the owner, not anyone bribed to look away."""
        return [n for n in self.present if (not owner or n.id != owner.id) and n.looks_away_until <= self.minutes]

    def holder_record(self, owner):
        """(list of hidden objects, saver) for the person or place the player is going through."""
        if owner:
            return owner.hidden, lambda: self.store.save_npc(owner)
        state = self.store.load_place(self.player.location)
        return state.hidden, lambda: self.store.save_place(state)

    def find_loot(self, owner, wanted: str, text: str) -> dict:
        """What the player is reaching for: something real if there is a match, otherwise nothing yet."""
        name = wanted or text
        offers = [o for o in self.stock_here() if not owner or o[0].id == owner.id]
        w_words = _words(name)
        best, best_hits = None, 0
        for o in offers:
            hits = len(w_words & _words(f"{items.display_name(o[1])} {o[1].good} {o[1].material} {items.base_of(o[1]).name}"))
            if hits > best_hits:
                best, best_hits = o, hits
        if best:
            npc, item, price = best
            return {"mode": "stock", "npc": npc, "item": item, "value": items.price(item), "label": item.name, "story": False}
        for n in ([owner] if owner else []) + [n for n in self.present if not owner or n.id != owner.id]:
            for w in self.world.roles[n.role].sells:
                if w.kind in ("item", "material") and w.item and w_words & (_words(w.name) | _words(w.id)):
                    return {"mode": "ware", "npc": n, "ware": w, "value": w.price, "label": w.name, "story": False}
        records, save = self.holder_record(owner)
        for rec in records:
            if w_words & _words(rec["name"]):
                return {"mode": "hidden", "record": rec, "save": save, "value": law.worth_value(rec["worth"]), "label": rec["name"],
                        "story": True, "taken": rec.get("taken", False), "owner": owner}
        return {"mode": "new", "records": records, "save": save, "value": 0, "label": wanted or "something", "story": True, "owner": owner}

    def judge_object(self, owner, wanted: str, text: str) -> ObjectVerdict:
        who = (f"{owner.label()}, a {owner.role.replace('_', ' ')}. {owner.description} {owner.activity}".strip() if owner
               else f"the place itself: {self.place.name} ({self.place.type})")
        place = f"{self.place.name} ({self.place.type})"
        return generate("plausible_object", PLAUSIBLE_SYSTEM,
                        f"HOLDER: {who}\nPLACE: {place}\nTHE PLAYER IS LOOKING FOR: {wanted or text}\nPLAYER TYPED: \"{text}\"",
                        ObjectVerdict, temperature=0.3, retries=1, max_tokens=200)

    def on_steal(self, intent, text: str) -> None:
        owner = next((n for n in self.present if n.id == intent.target), None)
        wanted = (intent.item or intent.ware or "").strip()
        loot = self.find_loot(owner, wanted, text)
        c = self.player.character
        day, turn = clock.day(self.minutes), self.store.meta.turn
        nothing = ""
        if loot["mode"] == "hidden" and loot["taken"]:
            nothing = f"{loot['label']} is already gone - the player took it earlier"
        elif loot["mode"] == "new":
            if loot["records"]:
                nothing = "there is nothing else of the kind to be found here"
            else:
                try:
                    verdict = self.judge_object(owner, wanted, text)
                except Exception:
                    verdict = ObjectVerdict(plausible=False, reason="nothing turns up")
                name = verdict.name.strip()
                if not (verdict.plausible and name and self.story_object(name)
                        and not any(k.name.lower() == name.lower() for k in c.key_items)):
                    nothing = (verdict.reason.strip() or "nothing of the kind is here") if not verdict.plausible \
                        else "nothing of the kind is here"
                else:
                    rec = {"name": name, "description": verdict.description.strip(), "worth": verdict.worth, "taken": False}
                    loot["records"].append(rec)
                    loot.update(mode="hidden", record=rec, value=law.worth_value(rec["worth"]), label=name, taken=False)
                    loot["save"]()
        holder = owner.label() if owner else f"the {self.place.name}"
        # the roll
        zone = law.zone_level(self.world, self.player.location)
        triggers = self.check_triggers("stealth", False)
        extras = sum(v for _, v in self.check_bonuses("stealth", owner, False, text))
        bonus = checks.passive_points(c, "stealth", triggers) + getattr(c, "trained", {}).get("stealth", 0) + extras
        target_pct = -sum(checks.RULES["traits"].get(t, {}).get("stealth", 0) for t in owner.traits) if owner else 0
        watchers = self.watchers(owner)
        value = loot["value"]
        res = law.attempt(zone, c.attributes.dexterity, bonus, value, owner is not None, len(watchers), target_pct,
                          checks.gear_points(c, "stealth", triggers))
        degree = "failure" if nothing else res["degree"]
        console.debug(f"steal: zone {zone}, window {res['window']}, score {res['score']:.0f}, bar {res['bar']:.0f}, "
                      f"x{res['mult']:.2f}, roll {res['roll']} -> {degree}{' (hopeless)' if res['hopeless'] else ''}")
        console.note(checks.label("Theft", degree))
        # who sees
        noticed = []
        if owner and law.notices(degree, owner.role, is_target=True):
            noticed.append(owner)
        noticed += [w for w in watchers if law.notices(degree, w.role)]
        took = (not nothing) and degree != "failure"
        if took:
            self.take_loot(loot, owner, holder)
        self.record_theft(loot, owner, noticed, took, degree, nothing, day, turn)
        self.narrate(self.theft_event(loot, holder, degree, took, nothing, res["hopeless"], owner, noticed), text)
        self.store.save_player(self.player)

    def take_loot(self, loot: dict, owner, holder: str) -> None:
        mode = loot["mode"]
        if mode == "stock":
            item, npc = loot["item"], loot["npc"]
            if item.uid.startswith("relic_"):
                self.player.relics_bought.append(item.uid[len("relic_"):])
            else:
                from engine import crafting
                crafting.remove_from_stock(npc, item.uid)
            self.store.save_npc(npc)
            self.to_pack(item)
        elif mode == "ware":
            w = loot["ware"]
            self.to_pack(items.make_raw(w.item) if w.kind == "material" else inv.make_good(w.item, 1))
        else:
            rec = loot["record"]
            rec["taken"] = True
            loot["save"]()
            self.player.character.key_items.append(KeyItem(
                id=re.sub(r"[^a-z0-9]+", "_", rec["name"].lower()).strip("_"), name=rec["name"], description=rec["description"],
                kind="key", source=owner.name if owner else self.place.name, day=clock.day(self.minutes)))
            console.note(f"Key item taken: {rec['name']} - {rec['description']}")
        console.note(f"You take {loot['label']}.")

    def record_theft(self, loot, owner, noticed, took, degree, nothing, day, turn) -> None:
        what = loot["label"]
        for n in noticed:
            seen = "tried to take" if not took else "took"
            n.memories.append(Memory(day=day, turn=turn, text=f"Saw the stranger {seen} {what}" +
                                     (f" from {owner.label()}." if owner and n.id != owner.id else ".") if n.id != (owner.id if owner else None)
                                     else f"Caught the stranger {'taking' if took else 'trying to take'} {what} from me."))
            n.trust = max(0, n.trust - (15 if owner and n.id == owner.id else 5))
            self.store.save_npc(n)
        if owner and took and owner not in noticed:
            owner.memories.append(Memory(day=day, turn=turn, text=f"{what.capitalize()} has gone missing. I have no idea who took it."))
            self.store.save_npc(owner)
        if not noticed:
            return
        guard = any(n.role in H["guard_roles"] for n in noticed)
        victim = bool(owner and owner in noticed)
        story = loot["story"]
        deeds.log(self.store, "offense", self.minutes, self.player.location, offense="theft", item=what, took=took,
                  witnesses=[n.id for n in noticed], story=story)
        if not self.lawless_here():
            gain = law.offense_heat("theft", loot["value"], story, only_passersby=not (victim or guard))
            heat = law.add_heat(self.player, self.town_here(), gain, clock.day(self.minutes))
            console.debug(f"offense: heat +{gain:.0f} -> {heat} in {self.town_here()}")

    def theft_event(self, loot, holder, degree, took, nothing, hopeless, owner, noticed) -> str:
        what = loot["label"]
        who = ", ".join(n.label() for n in noticed)
        if nothing:
            base = (f"The player quietly goes through {holder} looking for {what}, but {nothing}. Describe the search coming up "
                    f"empty. Do not invent anything they find.")
        elif took:
            how = {"strong success": "smoothly and without a flicker of notice", "success": "cleanly",
                   "partial": "with a clumsy moment that could have given them away"}[degree]
            base = f"The player takes {what} from {holder}, {how}. Describe the lifting in two or three sentences."
        else:
            base = (f"The player tries to take {what} from {holder} and cannot manage it"
                    + (" - it is far beyond their skill" if hopeless else "") + ". They come away empty-handed.")
        if noticed:
            base += (f" {who} notice{'s' if len(noticed) == 1 else ''} what the player is doing and react: sharp words, alarm or"
                     f" a hard stare. Nobody draws a weapon or attacks; the game handles what comes next.")
        elif took:
            base += " Nobody notices. No one reacts."
        return base

    # ------------------------------------------------------------------ force
    def after_force(self, intent, text: str) -> None:
        """Hands laid on someone: an assault. The target always knows; others may see."""
        npc = next((n for n in self.present if n.id == intent.target), None) or (self.partner if self.partner in self.present else None)
        if not npc:
            return
        day, turn = clock.day(self.minutes), self.store.meta.turn
        seen = [w for w in self.watchers(npc) if law.notices("success", w.role, assault=True)]
        noticed = [npc] + seen
        for n in noticed:
            n.memories.append(Memory(day=day, turn=turn, text=("The stranger laid hands on me." if n.id == npc.id
                                                              else f"Saw the stranger lay hands on {npc.label()}.")))
            n.trust = max(0, n.trust - (10 if n.id == npc.id else 5))
            self.store.save_npc(n)
        deeds.log(self.store, "offense", self.minutes, self.player.location, offense="assault", target=npc.id,
                  witnesses=[n.id for n in noticed])
        guard = any(n.role in H["guard_roles"] for n in noticed)
        if not self.lawless_here():
            gain = law.offense_heat("assault", 0, False, only_passersby=not (npc in noticed or guard) or False)
            heat = law.add_heat(self.player, self.town_here(), gain, day)
            console.debug(f"offense: assault, heat +{gain:.0f} -> {heat} in {self.town_here()}")
        if law.fights_back(npc.role, npc.traits):
            console.debug(f"{npc.label()} fights back")
            self.narrate(f"{npc.label()} does not take it. They break free and hit back, shoving the player away and shouting for "
                         f"help. No one is killed; keep it to a scuffle of a few seconds.", text)
            if npc.role in H["guard_roles"]:
                self.arrest(npc, self.town_here(), forced=True)

    # ------------------------------------------------------------------ the law catches up
    def law_check(self) -> None:
        """After each turn: a guard who sees you while you are wanted in this town comes for you (once a day per town)."""
        if self.combat or self.lawless_here():
            return
        town, day = self.town_here(), clock.day(self.minutes)
        heat = law.current_heat(self.player, town, day)
        level = law.tier(heat)
        if level in ("clear", "cold") or self.player.confronted.get(town) == day:
            return
        guard = next((n for n in self.present if n.role in H["guard_roles"] and n.looks_away_until <= self.minutes), None)
        if not guard:
            return
        self.player.confronted[town] = day
        self.store.save_player(self.player)
        if level == "wanted":
            self.arrest(guard, town)
        else:
            self.law_confront(guard, town)

    def ask_choice(self, options: dict[str, tuple[str, ...]], menu: str) -> str:
        for _ in range(3):
            console.note(menu)
            said = console.ask().lower()
            for key, words in options.items():
                if any(re.search(rf"\b{w}", said) for w in words):
                    return key
            console.note("The guard waits for a straight answer.")
        return "run"

    WORDS = {"pay": ("pay", "fine", "settle", "coin"), "talk": ("talk", "persuade", "convince", "explain", "argue", "plead", "reason"),
             "bribe": ("bribe", "slip", "grease", "sweeten"), "run": ("run", "flee", "escape", "bolt", "dash"),
             "jail": ("jail", "cell", "prison", "serve", "time")}

    def law_confront(self, guard, town: str) -> None:
        heat = law.current_heat(self.player, town, clock.day(self.minutes))
        fine = law.fine(heat)
        self.narrate(f"{guard.label()} steps into the player's path: word of their thieving has reached the watch. Describe the guard "
                     f"stopping them, stern, hand near a weapon but not drawing it. Do not resolve anything; the game will.", "")
        menu = (f"The watch wants {money.fmt(fine)}. You can: pay the fine, talk your way out, offer a bribe, or run.")
        pick = self.ask_choice({k: self.WORDS[k] for k in ("pay", "talk", "bribe", "run")}, menu)
        self.settle(guard, town, pick, fine)

    def arrest(self, guard, town: str, forced: bool = False) -> None:
        heat = law.current_heat(self.player, town, clock.day(self.minutes))
        fine = law.fine(heat)
        self.narrate(f"{guard.label()} and the watch take hold of the player: they are wanted here. Describe the arrest in two "
                     f"sentences. Do not resolve anything; the game will.", "")
        menu = (f"You are under arrest. Pay the fine ({money.fmt(fine)}), serve time in jail, offer a bribe, or run.")
        pick = self.ask_choice({k: self.WORDS[k] for k in ("pay", "jail", "bribe", "run")}, menu)
        self.settle(guard, town, pick, fine)

    def settle(self, guard, town: str, pick: str, fine: int) -> None:
        c, day, turn = self.player.character, clock.day(self.minutes), self.store.meta.turn
        heat = law.current_heat(self.player, town, day)
        remember = lambda t: guard.memories.append(Memory(day=day, turn=turn, text=t))
        if pick == "pay":
            if c.coins >= fine:
                c.coins -= fine
                law.set_heat(self.player, town, H["after_paid"], day)
                remember(f"The stranger paid {money.words(fine)} to settle their crimes.")
                console.note(f"You pay {money.fmt(fine)}. Purse: {money.fmt(c.coins)}")
                self.narrate(f"The player pays {guard.label()} {money.words(fine)}. The guard counts it and lets them go with a warning.", "")
            else:
                console.note("You cannot cover the fine.")
                self.serve_time(guard, town, fine)
        elif pick == "jail":
            self.serve_time(guard, town, fine)
        elif pick == "talk":
            degree = self.resolve("persuasion", guard, talking=True)
            relief = H["talk_relief"].get(degree, 0)
            if relief:
                law.set_heat(self.player, town, heat - relief, day)
                remember("The stranger talked their way out of trouble with me.")
                self.narrate(f"The player talks {guard.label()} down. The guard relents with a warning. Keep it short.", "")
            elif degree == "partial":
                console.note("The guard is not swayed - he wants the fine.")
                self.settle(guard, town, "pay", fine)
            else:
                console.note("The guard is not swayed. You are arrested.")
                self.arrest(guard, town, forced=True)
        elif pick == "bribe":
            self.settle_bribe(guard, town, fine)
        else:
            law.add_heat(self.player, town, H["gain"]["run"], day)
            remember("The stranger ran from the watch.")
            self.narrate(f"The player bolts from {guard.label()} and slips away through the crowd. Keep it brief.", "")
        self.store.save_npc(guard)
        self.store.save_player(self.player)

    def settle_bribe(self, guard, town: str, fine: int) -> None:
        c, day, turn = self.player.character, clock.day(self.minutes), self.store.meta.turn
        if c.coins < fine:
            console.note("You cannot cover that.")
            return self.arrest(guard, town, forced=True)
        B = checks.RULES["bribe"]
        wealth = B["wealth"].get(guard.role, B["default_wealth"])
        pct = fine / wealth * 100
        bonus = max(B["floor"], min(B["cap"], B["per_percent"] * (pct - B["break_even"])))
        degree = self.resolve("persuasion", guard, talking=True, extra=[(f"offer is {pct:.0f}% of their wealth", bonus)])
        if degree in ("strong success", "success"):
            c.coins -= fine
            law.set_heat(self.player, town, law.current_heat(self.player, town, day) - H["bribe_relief"], day)
            guard.looks_away_until = self.minutes + law.N["look_away_minutes"]
            guard.memories.append(Memory(day=day, turn=turn, text=f"Took {money.words(fine)} from the stranger to forget what I knew."))
            console.note(f"The coins vanish. Purse: {money.fmt(c.coins)}")
            self.narrate(f"The player slips {guard.label()} {money.words(fine)}. The guard pockets it and turns away. Keep it brief.", "")
        else:
            guard.trust = max(0, guard.trust + B["trust"][degree])
            guard.memories.append(Memory(day=day, turn=turn, text="The stranger tried to bribe me. I did not take it."))
            console.note("The guard refuses. You are arrested.")
            self.arrest(guard, town, forced=True)

    def serve_time(self, guard, town: str, fine: int) -> None:
        c, day = self.player.character, clock.day(self.minutes)
        price = min(c.coins, round(fine * H["jail_fine_share"]))
        c.coins -= price
        self.advance(H["jail_days"] * 1440)
        law.set_heat(self.player, town, H["after_paid"], clock.day(self.minutes))
        guard.memories.append(Memory(day=day, turn=self.store.meta.turn, text="The stranger spent time in the cells."))
        console.note(f"You serve {H['jail_days']} days and pay {money.fmt(price)}. Purse: {money.fmt(c.coins)}")
        self.narrate(f"The player spends {H['jail_days']} days in the town cells and is released with a stern warning. "
                     f"Describe the stay in two or three sentences.", "")
