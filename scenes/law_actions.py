"""Theft, force and the law as the world scene runs them. The dice, bars and numbers are in engine/law.py and data/rules/law.yaml.

A theft takes something that really exists - a ware on a stall, a piece of gear in stock, a story object already found on this person or
in this place - or, once per person or place, a story object the player went looking for that the model judges plausible. The model names
and describes that object; the engine owns whether it exists, what it is worth, and who sees what."""
import re

from core.models import KeyItem
from engine import voice_rules
from engine import checks, clock, inventory as inv, items, law, locks, money, pools, pulse, standing
from engine.domain_events import BreakIn, Bribe, FinePaid, Jailed, PersonHarmed, RanFromWatch, TalkedOut, Theft
from engine.combat import RULES as COMBAT_RULES
from llm.contracts import ObjectVerdict
from llm.gateway import generate
from ui import console

H = law.H

PLAUSIBLE_SYSTEM = """You decide whether something a player went looking for plausibly exists on a person or in a place in a role-playing game.
Say yes to ordinary belongings of that kind of person or place (a merchant keeps a ledger and letters, a priest a prayer book,
a smith their tools, a captain a seal, a hall a strongbox of papers). Say no to the absurd or magical (a dragon egg in a baker's
pocket), to anything vague ("something valuable", "anything"), and to money, food, drink, weapons and armor.
If plausible, give it a short name (two to four words), one plain sentence describing it (nothing magical unless the place is
holy or arcane), and its worth: trinket (little), ordinary, valuable, or priceless (a relic or a great secret).
If not, say why in a few words.
If the thing would be kept locked up (a ledger in a strongbox, a relic in a locked back room), set locked true and name what is locked in
behind ("the back room", "a strongbox"). If the player is asking for a KEY, set is_key true and put what it opens in behind;
a key is plausible when the holder would keep one (a shopkeeper's key to their own back room)."""


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
        return law.price_factor(self.heat_here()) * self.standing_price()

    def heat_trust(self) -> int:
        return H["first_meeting_trust"] if self.heat_here() >= H["tiers"]["cold"] else 0


    # ------------------------------------------------------------------ steal
    def watchers(self, owner) -> list:
        """Other people here who could see: not the owner, not anyone bribed to look away."""
        return [n for n in self.present if (not owner or n.id != owner.id) and n.looks_away_until <= self.minutes]

    def holder_record(self, owner):
        """(list of hidden objects, saver) for the person or place the player is going through."""
        if owner:
            return owner.hidden, lambda: self.store.save_npc(owner)
        where = self.player.location
        hidden = self.store.load_place(where).hidden

        def save():                                   # reload, so a lock changed since is not overwritten
            state = self.store.load_place(where)
            state.hidden = hidden
            self.store.save_place(state)
        return hidden, save

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
        searched = [(records, save)] + ([self.holder_record(None)] if owner else [])
        for recs, sv in searched:                     # a locked thing and its key live with the place, whoever owns them
            for rec in recs:
                if w_words & _words(rec["name"]):
                    return {"mode": "hidden", "record": rec, "save": sv, "value": law.worth_value(rec["worth"]), "label": rec["name"],
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
            nothing = self.create_object(owner, loot, wanted, text)
        # something kept behind a lock stays out of reach until the lock is open (a key opens it at once)
        if loot["mode"] == "hidden" and not nothing and loot["record"].get("lock"):
            blocked = self.lock_blocks(loot["record"]["lock"], text)
            if blocked:
                self.narrate(blocked, text)
                return
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
        from engine import world_perks
        degree = "failure" if nothing else world_perks.gamble(c, res["degree"])
        if world_perks.bad(c, degree) and not nothing:
            law.add_heat(self.player, self.town_here(), world_perks.P["all_or_nothing"]["bad_heat"], clock.day(self.minutes))
            console.note("A bad failure: the fumble is loud, and the town's heat rises (All or Nothing).")
        console.debug(f"steal: zone {zone}, window {res['window']}, score {res['score']:.0f}, bar {res['bar']:.0f}, "
                      f"x{res['mult']:.2f}, roll {res['roll']} -> {degree}{' (hopeless: the roll is skipped)' if res['hopeless'] else ''}")
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
        if took and loot["mode"] == "hidden" and loot["record"].get("opens"):
            self.key_taken(loot["record"]["opens"], day, bool(noticed))
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
                kind="key", source=owner.name if owner else self.place.name, day=clock.day(self.minutes), opens=rec.get("opens", "")))
            console.ledger(f"Key item taken: {rec['name']} - {rec['description']}")
        console.note(f"You take {loot['label']}.")

    def record_theft(self, loot, owner, noticed, took, degree, nothing, day, turn) -> None:
        """The world learns of it (engine/reactions.py): who saw it remembers and trusts less, the tale starts, the watch may hear."""
        self.notice(Theft(minute=self.minutes, place=self.player.location, witnesses=tuple(n.id for n in noticed),
                          npc=owner.id if owner else "", name=owner.label() if owner else "", item=loot["label"], took=took,
                          story=bool(loot["story"]), value=int(loot["value"] or 0)), owner, *noticed)

    def theft_event(self, loot, holder, degree, took, nothing, hopeless, owner, noticed) -> str:
        what = loot["label"]
        who = ", ".join(n.label() for n in noticed)
        if nothing:
            base = (f"The player quietly goes through {holder} looking for {what}, but {nothing}. Describe the search coming up "
                    f"empty. Do not invent anything they find. " + voice_rules.NOTHING)
        elif took:
            how = {"strong success": "smoothly and without a flicker of notice", "success": "cleanly",
                   "partial": "with a clumsy moment that could have given them away"}[degree]
            base = f"The player takes {what} from {holder}, {how}. Describe the lifting."
        else:
            base = (f"The player tries to take {what} from {holder} and cannot manage it"
                    + (" - it is far beyond their skill" if hopeless else "") + ". They come away empty-handed. "
                    f"Name only {what}: do not mention any other object, and not the player's own gear. " + voice_rules.NOTHING)
        if noticed:
            base += (f" {who} notice{'s' if len(noticed) == 1 else ''} what the player is doing and react: sharp words, alarm or"
                     f" a hard stare. Nobody draws a weapon or attacks; the game handles what comes next.")
        elif took:
            base += " Nobody notices. No one reacts."
        return base

    # ------------------------------------------------------------------ locks
    def place_state(self):
        return self.store.load_place(self.player.location)

    def lock_by_id(self, lock_id: str) -> dict | None:
        return next((l for l in self.place_state().locks if l["id"] == lock_id), None)

    def save_lock(self, lock: dict) -> None:
        state = self.place_state()
        state.locks = [lock if l["id"] == lock["id"] else l for l in state.locks]
        self.store.save_place(state)

    def lock_for(self, behind: str, owner, worth: str) -> dict | None:
        """The lock the model named: one already here that matches, or a new one (a place keeps only a few)."""
        state = self.place_state()
        found = locks.find(state.locks, behind, owner.id if owner else "")
        if found:
            return found
        if len(state.locks) >= law.L["lock"]["max_per_place"]:
            return None
        lock = locks.make(behind, owner.id if owner else "", worth, state.locks)
        state.locks.append(lock)
        self.store.save_place(state)
        return lock

    def create_object(self, owner, loot: dict, wanted: str, text: str) -> str:
        """The player went looking for something that does not exist yet. Ask whether it plausibly does; if so make it (behind a lock if
        it would be kept so). Returns why nothing turned up, or '' when the object now exists (loot is updated to point at it)."""
        c = self.player.character
        asked_key = "key" in _words(wanted or text) or "key" in (wanted or text).lower()
        every = loot["records"] + (self.holder_record(None)[0] if owner else [])
        plain = [r for r in every if not r.get("opens")]
        if plain and not asked_key:
            return "there is nothing else of the kind to be found here"
        try:
            verdict = self.judge_object(owner, wanted, text)
        except Exception:
            verdict = ObjectVerdict(plausible=False, reason="nothing turns up")
        name = verdict.name.strip()
        if not (verdict.plausible and name and self.story_object(name)
                and not any(k.name.lower() == name.lower() for k in c.key_items)):
            return (verdict.reason.strip() or "nothing of the kind is here") if not verdict.plausible else "nothing of the kind is here"
        rec = {"name": name, "description": verdict.description.strip(), "worth": verdict.worth, "taken": False}
        behind = verdict.behind.strip()
        if verdict.is_key:
            lock = self.lock_for(behind or "the locked door", owner, verdict.worth)
            if not lock:
                return "nothing of the kind is here"
            if any(r.get("opens") == lock["id"] for r in every):
                return "there is nothing else of the kind to be found here"
            rec["opens"] = lock["id"]
        else:
            if plain:
                return "there is nothing else of the kind to be found here"
            if verdict.locked and behind:
                lock = self.lock_for(behind, owner, verdict.worth)
                if lock:
                    rec["lock"] = lock["id"]
        if rec.get("lock") or rec.get("opens"):
            place_recs, loot["save"] = self.holder_record(None)
            place_recs.append(rec)
        else:
            loot["records"].append(rec)
        loot.update(mode="hidden", record=rec, value=law.worth_value(rec["worth"]), label=name, taken=False)
        loot["save"]()
        return ""

    def has_key(self, lock: dict) -> bool:
        return any(k.opens == lock["id"] for k in self.player.character.key_items)

    def lock_blocks(self, lock_id: str, text: str) -> str:
        """If the lock is still shut: an event line (nothing is taken). A usable key opens it quietly and returns ''."""
        lock = self.lock_by_id(lock_id)
        if not lock or locks.is_open(lock):
            return ""
        day = clock.day(self.minutes)
        if self.has_key(lock) and locks.key_fits(lock, day):
            self.open_lock(lock, "key")
            return ""
        changed = " Their key no longer fits - the lock has been changed." if self.has_key(lock) else ""
        console.note(f"{lock['name'].capitalize()} is locked.{changed}")
        return (f"The player reaches for what is kept in {lock['name']}, but it is locked and they cannot get at it.{changed} "
                f"Describe the closed door or lid. Do not invent anything they find; the lock must be opened first.")

    def open_lock(self, lock: dict, how: str) -> None:
        lock["state"] = "open"
        self.save_lock(lock)
        self.advance(law.L["lock"]["minutes"]["key"] if how == "key" else 0)
        if how == "key":
            console.note(f"Your key opens {lock['name']}.")

    def key_taken(self, lock_id: str, day: int, seen: bool) -> None:
        lock = self.lock_by_id(lock_id)
        if lock:
            locks.key_stolen(lock, day, seen)
            self.save_lock(lock)

    def pay_field_ability(self, fn: str):
        """The character's ability with this field function, if it is ready and they can pay for it - paid for. Else None."""
        c = self.player.character
        from engine import loadout
        ab = next((a for a in loadout.prepared(c) if a.field_use == fn), None)      # only what is brought
        if not ab or self.field_ready_in(ab):
            return None
        pool = ab.resource.value
        table = "ability_cost_percent" if pool == "mana" else "stamina_cost_percent"
        cost = pools.reference_pool(pool, c.level) * COMBAT_RULES[table][ab.tier.value] / 100
        if getattr(ab, "rank", 0):
            from engine import spells
            cost = spells.mana(ab)                      # (f397) a ranked spell's flat cost
        if pools.current(c, pool) < cost:
            console.note(f"You have no {pool} left for {ab.name}.")
            return None
        setattr(c, pool, pools.current(c, pool) - cost)
        return ab

    def pay_picklock(self) -> tuple[float, str]:
        """A picklock ability helps if the character has one and can pay for it. Returns (bonus percent of the window, its name)."""
        ab = self.pay_field_ability("picklock")
        if not ab:
            from engine import loadout
            if any(a.field_use == "picklock" for a in loadout.prepared(self.player.character)):
                console.note("You try it by hand.")
            return 0.0, ""
        return float(law.L["lock"]["picklock_bonus"][ab.tier.value]), ab.name

    def on_unlock(self, intent, text: str) -> None:
        state = self.place_state()
        owner = next((n for n in self.present if n.id == intent.target), None)
        what = (intent.item or "").strip() or text
        lock = locks.find(state.locks, what, owner.id if owner else "")
        c = self.player.character
        day, turn = clock.day(self.minutes), self.store.meta.turn
        if lock and locks.is_open(lock):
            self.narrate(f"The player goes to {lock['name']}; it is already open. Describe it.", text)
            return
        if not lock:
            lock = self.invent_lock(owner, what, text)
            if not lock:
                console.note("There is no lock here that you can find.")
                self.halted = True
                return
        L = law.L["lock"]
        lock_owner = next((n for n in self.present if n.id == lock["owner"]), None)
        if self.has_key(lock) and locks.key_fits(lock, day):
            self.open_lock(lock, "key")
            self.narrate(f"The player opens {lock['name']} with a key they carry. Describe it; nothing is found yet.", text)
            self.store.save_player(self.player)
            return
        changed = self.has_key(lock)
        # the roll
        zone = law.zone_level(self.world, self.player.location)
        triggers = self.check_triggers("stealth", False)
        extras = sum(v for _, v in self.check_bonuses("stealth", lock_owner, False, text))
        boost, tool = self.pay_picklock()
        bonus = checks.passive_points(c, "stealth", triggers) + getattr(c, "trained", {}).get("stealth", 0) + extras + boost
        watchers = self.watchers(lock_owner)
        force = self.owns("siege_breaker") and c.attributes.strength > c.attributes.dexterity
        if self.owns("siege_breaker") and tool:
            boost, tool = 0.0, ""                         # Siege Breaker needs no tools: force is the tool
        res = law.attempt(zone, c.attributes.strength if force else c.attributes.dexterity, bonus, 0, lock_owner is not None,
                          len(watchers), locks.difficulty(lock), checks.gear_points(c, "stealth", triggers))
        if self.owns("siege_breaker"):
            console.note("You put your strength to it instead of your skill (Siege Breaker).")
        from engine import world_perks
        degree = world_perks.gamble(c, res["degree"])
        console.debug(f"unlock: zone {zone}, window {res['window']}, score {res['score']:.0f}, bar {res['bar']:.0f}, "
                      f"x{res['mult']:.2f}, roll {res['roll']} -> {degree}{' (hopeless: the roll is skipped)' if res['hopeless'] else ''}")
        console.note(checks.label("Lock", degree))
        noticed = []
        if lock_owner and law.notices(degree, lock_owner.role, is_target=True):
            noticed.append(lock_owner)
        noticed += [w for w in watchers if law.notices(degree, w.role)]
        opened = degree != "failure"
        self.advance(L["minutes"][degree])
        if opened:
            lock["state"] = "open"
        else:
            locks.jam(lock)
        self.save_lock(lock)
        self.record_break_in(lock, lock_owner, noticed, opened, day, turn)
        self.narrate(self.unlock_event(lock, degree, opened, res["hopeless"], tool, changed, noticed), text)
        self.store.save_player(self.player)

    def invent_lock(self, owner, what: str, text: str) -> dict | None:
        """The player tries a lock nobody has mentioned. Ask whether this person or place plausibly has one; if so it exists now."""
        try:
            verdict = self.judge_object(owner, f"a locked {what}", f"{text} (is there plausibly a locked {what} here?)")
        except Exception:
            return None
        behind = verdict.behind.strip() or verdict.name.strip()
        if not (verdict.plausible and behind):
            return None
        return self.lock_for(behind, owner, verdict.worth)

    def record_break_in(self, lock, owner, noticed, opened, day, turn) -> None:
        self.notice(BreakIn(minute=self.minutes, place=self.player.location, witnesses=tuple(n.id for n in noticed),
                            npc=owner.id if owner else "", name=owner.label() if owner else "", lock=lock["name"], opened=opened), owner, *noticed)

    def unlock_event(self, lock, degree, opened, hopeless, tool, changed, noticed) -> str:
        what = lock["name"]
        by = f" with {tool}" if tool else ""
        if opened:
            how = {"strong success": "quickly and without a sound", "success": "after a little work",
                   "partial": "but not quietly - the metal scrapes and clicks"}[degree]
            base = f"The player works {what} open{by}, {how}. Describe the lock giving way. Do not say what lies beyond."
        else:
            base = (f"The player tries {what}{by} and cannot open it" + (" - it is far beyond their skill" if hopeless else "")
                    + ". The lock holds, and it feels a little tighter than before.")
        if changed:
            base += " Their stolen key no longer fits; the lock has been changed."
        if noticed:
            who = ", ".join(n.label() for n in noticed)
            base += (f" {who} notice{'s' if len(noticed) == 1 else ''} and react: sharp words, alarm or a hard stare. "
                     f"Nobody draws a weapon or attacks; the game handles what comes next.")
        return base

    # ------------------------------------------------------------------ force
    def after_force(self, intent, text: str) -> None:
        """Hands laid on someone: an assault. The target always knows; others may see."""
        npc = next((n for n in self.present if n.id == intent.target), None) or (self.partner if self.partner in self.present else None)
        if not npc:
            return
        seen = [w for w in self.watchers(npc) if law.notices("success", w.role, assault=True)]
        self.notice(PersonHarmed(minute=self.minutes, place=self.player.location, witnesses=tuple(n.id for n in [npc] + seen), npc=npc.id, name=npc.label()), npc, *seen)
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
        level = law.tier(heat + standing.heat_shift(self.player, town, day))
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
        if self.owns("above_the_law"):
            menu = (f"You are under arrest - but your kind are not jailed. Pay the fine ({money.fmt(fine)}); what your purse cannot cover, "
                    f"your name will. Or offer a bribe, or run.")
            pick = self.ask_choice({k: self.WORDS[k] for k in ("pay", "bribe", "run")}, menu)
        else:
            menu = (f"You are under arrest. Pay the fine ({money.fmt(fine)}), serve time in jail, offer a bribe, or run.")
            pick = self.ask_choice({k: self.WORDS[k] for k in ("pay", "jail", "bribe", "run")}, menu)
        self.settle(guard, town, pick, fine)

    def settle(self, guard, town: str, pick: str, fine: int) -> None:
        c, day = self.player.character, clock.day(self.minutes)
        heat = law.current_heat(self.player, town, day)
        seen = (guard.id,)
        if pick == "pay":
            if c.coins >= fine:
                c.coins -= fine
                law.set_heat(self.player, town, H["after_paid"], day)
                self.notice(FinePaid(minute=self.minutes, place=self.player.location, witnesses=seen, npc=guard.id, name=guard.label(), amount=fine), guard)
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
                self.notice(TalkedOut(minute=self.minutes, place=self.player.location, witnesses=seen, npc=guard.id, name=guard.label()), guard)
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
            self.notice(RanFromWatch(minute=self.minutes, place=self.player.location, witnesses=seen, npc=guard.id, name=guard.label()), guard)
            self.narrate(f"The player bolts from {guard.label()} and slips away through the crowd.", "")
        self.store.save_npc(guard)
        self.store.save_player(self.player)

    def settle_bribe(self, guard, town: str, fine: int) -> None:
        c, day = self.player.character, clock.day(self.minutes)
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
            self.notice(Bribe(minute=self.minutes, place=self.player.location, witnesses=(guard.id,), npc=guard.id, name=guard.label(), amount=fine,
                              worked=True, degree=degree, favor="forget what they knew", confrontation=True, guard=True), guard)
            console.ledger(f"The coins vanish. Purse: {money.fmt(c.coins)}")
            self.narrate(f"The player slips {guard.label()} {money.words(fine)}. The guard pockets it and turns away.", "")
        else:
            guard.trust = max(0, guard.trust + B["trust"][degree])
            self.notice(Bribe(minute=self.minutes, place=self.player.location, witnesses=(guard.id,), npc=guard.id, name=guard.label(), amount=fine,
                              worked=False, degree=degree, favor="forget what they knew", confrontation=True, guard=True), guard)
            console.note("The guard refuses. You are arrested.")
            self.arrest(guard, town, forced=True)

    def serve_time(self, guard, town: str, fine: int) -> None:
        c = self.player.character
        if self.owns("above_the_law"):
            return self.pay_in_standing(guard, town, fine)
        price = min(c.coins, round(fine * H["jail_fine_share"]))
        c.coins -= price
        self.advance(H["jail_days"] * 1440)
        law.set_heat(self.player, town, H["after_paid"], clock.day(self.minutes))
        self.notice(Jailed(minute=self.minutes, place=self.player.location, witnesses=(guard.id,), npc=guard.id, name=guard.label(), days=H["jail_days"]), guard)
        console.note(f"You serve {H['jail_days']} days and pay {money.fmt(price)}. Purse: {money.fmt(c.coins)}")
        self.narrate(f"The player spends {H['jail_days']} days in the town cells and is released with a stern warning. "
                     f"Describe the stay.", "")

    def pay_in_standing(self, guard, town: str, fine: int) -> None:
        """Above the Law: no cell, ever. The purse pays what it can; the rest comes off the player's name in this town."""
        from engine import pulse, world_perks
        c, day = self.player.character, clock.day(self.minutes)
        paid = min(c.coins, fine)
        c.coins -= paid
        owed = fine - paid
        lost = round(owed / 10000 * world_perks.P["above_the_law"]["standing_per_gold"]) if owed else 0
        if lost:
            self.reputation_add(pulse.town_of(self.world, town), -lost, spread=False)
        law.set_heat(self.player, town, H["after_paid"], day)
        self.notice(Jailed(minute=self.minutes, place=self.player.location, witnesses=(guard.id,), npc=guard.id, name=guard.label(), walked=True), guard)
        console.note(f"No cell for you. You pay {money.fmt(paid)}" + (f"; the rest ({money.fmt(owed)}) is paid in standing here ({-lost})" if owed else "")
                     + f". Purse: {money.fmt(c.coins)} (Above the Law)")
        self.narrate(f"The watch cannot hold the player: their kind are fined, not jailed. {guard.label()} takes {money.words(paid)}"
                     + (" and makes sure the whole street knows the rest went unpaid" if owed else "") + ".", "")
