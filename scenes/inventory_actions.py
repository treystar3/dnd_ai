"""Things the player does with items: use, drop, pick up, give, store, retrieve, equip, forage, craft, sell.

Mixed into WorldScene, so every method can use the scene's state (player, place, store, narrate...).
"""

import random
import re

from core.models import Item, KeyItem
from engine import clock, crafting, encounters, equipment, inventory as inv, items, money, needs, pools, property as property_rules
from npc.models import Memory
from ui import console

R = inv.RULES


def quality_name(item: Item) -> str:
    """'uncommon bronze chain shirt' - without doubling 'crude crude'."""
    return item.name if item.name.lower().startswith(item.rarity) else f"{item.rarity} {item.name}"


class InventoryActions:

    # ---------- helpers ----------

    @property
    def pack(self) -> list[Item]:
        return self.player.character.inventory

    def to_pack(self, item: Item, why: str = "") -> None:
        """Add to the pack; anything that does not fit is left on the ground here."""
        leftover = inv.add(self.pack, item, self.pack_slots())
        if leftover:
            state = self.store.load_place(self.player.location)
            inv.leave_on_ground(state, leftover, self.minutes)
            self.store.save_place(state)
            console.note(f"No room in your pack - {inv.label(leftover)} left on the ground here.")

    def ground_here(self) -> list[Item]:
        state = self.store.load_place(self.player.location)
        before = len(state.ground)
        found = inv.ground_items(state, self.minutes)
        if len(state.ground) != before:
            self.store.save_place(state)
        return found

    def stash_cap(self) -> int:
        return R["stash_slots"] + property_rules.stash_bonus(self.player)

    def can_store(self) -> bool:
        return bool(getattr(self.place, "storage", False)) or \
            (self.place.type == "guild" and self.guild_perks()["storage"]) or self.box_open()

    def consume(self, item: Item) -> str:
        """Apply a consumable or food to the player outside combat. Returns a short description of the effect."""
        g = inv.GOODS[item.good]
        c = self.player.character
        restores = g.restores or ({"stamina": 10} if g.kind == "food" else {})
        felt = []
        medic = 1 + (self.has("field_medic") or 0) / 100 if g.kind != "food" else \
            1 + (self.has("raw_appetite") or 0) / 100
        for pool, pct in restores.items():
            pct = pct * medic
            top = pools.maximum(c, pool)
            setattr(c, pool, min(top, pools.current(c, pool) + top * pct / 100))
            felt.append(pool)
        if g.feeds:
            needs.eat(c, g.feeds)
            felt.append("hunger")
        if item.origin and g.kind == "food" and not inv.GOODS[item.good].drops_from and self.owns("symbiosis"):
            from engine import world_perks
            c.gift = {"family": item.origin, "mechanics": world_perks.gift_for(item.origin)}
            gift = ", ".join(k.replace("_", " ") for k in c.gift["mechanics"])
            console.note(f"The {item.origin.replace('_', ' ')}'s strength is in you until you sleep: {gift} (Symbiosis).")
            felt.append(f"and the {item.origin.replace('_', ' ')}'s gift ({gift})")
        return f"restoring {', '.join(felt)}" if felt else "to no real effect"

    def find_key(self, name: str) -> KeyItem | None:
        words = [w.rstrip("s") for w in name.lower().split() if w not in ("the", "my", "a", "an", "of")]
        best, score = None, 0
        for k in self.player.character.key_items:
            hit = sum(1 for w in words if w and w in k.name.lower())
            if hit > score:
                best, score = k, hit
        return best

    def refuse_key(self, name: str, what: str) -> bool:
        """If the player names a key item for something key items can't do, say so. Returns True if refused."""
        if inv.find(self.pack, name):
            return False
        key = self.find_key(name)
        if key:
            console.note(f"{key.name.capitalize()} is a {'quest' if key.kind == 'quest' else 'key'} item - you can't {what} it.")
            self.halted = True
            return True
        return False

    NOT_STORY = ("stew", "soup", "bread", "meal", "food", "ale", "beer", "wine", "drink", "meat", "potion", "draught",
                 "tonic", "bandage", "coin", "gold", "silver", "copper", "money", "sword", "axe", "spear", "bow",
                 "dagger", "armor", "armour", "shield", "helm", "hammer", "mace", "staff")

    def story_object(self, name: str) -> bool:
        """Key items are tokens, documents and keys - never food, drink, gear, remedies or money."""
        words = name.lower()
        return not any(re.search(rf"\b{w}", words) for w in self.NOT_STORY) and not inv.find(
            [inv.make_good(g) for g in inv.GOODS], name)

    def receive_key_item(self, gift, npc) -> None:
        c = self.player.character
        if any(k.name.lower() == gift.name.strip().lower() for k in c.key_items):
            return
        key = KeyItem(id=re.sub(r"[^a-z0-9]+", "_", gift.name.lower()).strip("_"), name=gift.name.strip(),
                      description=gift.description.strip(), kind=gift.kind, source=npc.name,
                      day=clock.day(self.minutes), for_whom=gift.for_whom.strip() if gift.kind == "quest" else "")
        c.key_items.append(key)
        npc.memories.append(Memory(importance=2, day=key.day, turn=self.store.meta.turn, text=f"I gave the stranger {key.name}."))
        self.store.save_npc(npc)
        self.store.save_player(self.player)
        meant = f" (meant for {key.for_whom})" if key.for_whom else ""
        console.note(f"{'Quest' if key.kind == 'quest' else 'Key'} item received: {key.name}{meant} - {key.description}")

    def is_recipient(self, npc, for_whom: str) -> bool:
        """Does this person match who a quest item was meant for - by name, first name or role?"""
        want = for_whom.lower().replace("the ", "").strip()
        if not want:
            return False
        names = {npc.name.lower(), npc.name.split()[0].lower(), npc.role.replace("_", " ").lower()}
        return any(n and (n in want or want in n) for n in names)

    def on_discard(self, intent, text: str) -> None:
        key = self.find_key(intent.item or text)
        if not key:
            if inv.find(self.pack, intent.item or text):
                self.on_drop(intent, text)
                return
            console.note("You don't have that.")
            self.halted = True
            return
        kind = "quest" if key.kind == "quest" else "key"
        console.note(f"{key.name.capitalize()} is a {kind} item. Discard it for good? (y/n)")
        if console.ask().lower() not in ("y", "yes"):
            console.note("Kept.")
            self.halted = True
            return
        c = self.player.character
        c.key_items.remove(key)
        unfinished = f" - it never reached {key.for_whom}" if key.for_whom else ""
        c.item_history.append(f"Got rid of {key.name}{unfinished} (day {clock.day(self.minutes)}).")
        self.store.save_player(self.player)
        console.ledger(f"Discarded: {key.name}.")
        self.narrate(f"The player gets rid of {key.name} for good.", text)

    def on_show(self, intent, text: str) -> None:
        npc = next((n for n in self.present if n.id == intent.target), None) or self.partner
        key = self.find_key(intent.item or text)
        thing = (f"{key.name} ({key.description})" if key else
                 (lambda i: f"{items.display_name(i)} ({items.summary(i)})" if i else "")(inv.find(self.pack, intent.item or text)))
        if not thing:
            console.note("You don't have that to show.")
            self.halted = True
            return
        if not npc or npc not in self.present:
            self.narrate(f"The player takes out {thing} and looks it over.", text)
            return
        intent.target = npc.id
        intent.speech = (intent.speech.strip() + " " if intent.speech.strip() else "") + f"[They show you {thing}.]"
        self.on_talk(intent, text)

    # ---------- actions ----------

    def on_use(self, intent, text: str) -> None:
        item = inv.find(self.pack, intent.item or text)
        if not item or not item.good or inv.GOODS[item.good].kind == "herb":
            console.note("You have nothing like that you can use." if not item else f"{items.display_name(item)} can't be used like that.")
            self.halted = True
            return
        used = inv.take(self.pack, inv.GOODS[item.good].name, 1)
        effect = self.consume(used)
        if self.frugal_save():
            self.to_pack(inv.make_good(used.good, 1) if not used.origin else used.model_copy(update={"quantity": 1}))
            effect += " - and somehow there is still one left (Frugal Hands)"
        self.store.save_player(self.player)
        self.narrate(f"The player uses {inv.GOODS[used.good].name} ({inv.GOODS[used.good].description}), {effect}.", text)

    def frugal_save(self) -> bool:
        """Frugal Hands: a consumable that is not used up, some of the time (the mechanic's value is the percent)."""
        return self.owns("frugal_hands") and random.random() * 100 < self.mech("frugal_hands")

    def on_drop(self, intent, text: str) -> None:
        if self.refuse_key(intent.item or text, "drop"):
            return
        item = inv.take(self.pack, intent.item or text, max(1, intent.count))
        if not item:
            console.note("You aren't carrying that.")
            self.halted = True
            return
        state = self.store.load_place(self.player.location)
        inv.leave_on_ground(state, item, self.minutes)
        self.salvage(item)
        self.store.save_place(state)
        self.store.save_player(self.player)
        console.ledger(f"Left here: {inv.label(item)}. Items left behind vanish after {R['ground_days']} days.")
        self.narrate(f"The player sets down {inv.label(item)} and leaves it here.", text)

    def on_pick_up(self, intent, text: str) -> None:
        state = self.store.load_place(self.player.location)
        item = inv.pick_up(state, intent.item or text, self.minutes)
        if not item:                                         # not an item the game keeps: an ordinary bit of the scenery is narrated, and kept nowhere
            from scenes import world_prompts as wp
            self.narrate(wp.SCENERY_PICKUP.format(thing=(intent.item or "it").strip()), text)
            return
        self.store.save_place(state)
        self.to_pack(item)
        self.store.save_player(self.player)
        self.narrate(f"The player picks up {inv.label(item)}.", text)

    COIN_WORDS = ("coin", "silver", "gold", "copper", "money", "payment", "fee")
    NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                    "eight": 8, "nine": 9, "ten": 10, "twenty": 20, "fifty": 50, "hundred": 100}

    def coin_amount(self, words: str) -> int | None:
        """'2 silver' -> 200, 'fifty copper' -> 50. None if no amount is named."""
        total = 0
        for num, coin in re.findall(r"(\d+|[a-z]+)\s+(gold|silver|copper)", words.lower()):
            n = int(num) if num.isdigit() else self.NUMBER_WORDS.get(num)
            if n:
                total += n * money.to_smallest(**{coin: 1})
        return total or None

    def pay_with_coins(self, intent, text: str, npc) -> None:
        """Handing over money: pays for what's being discussed, or is a gift of that amount."""
        c = self.player.character
        amount = self.coin_amount(intent.item or "") or self.coin_amount(text)
        wares = self.world.roles[npc.role].sells
        recent = " ".join(line for _, line in self.convo[-4:]).lower()
        ware = next((w for w in wares if amount and w.price == amount), None) or \
            next((w for w in wares if w.id in recent or w.name.lower().split()[-1] in recent), None)
        if ware:
            intent.target, intent.ware = npc.id, ware.id
            self.on_buy(intent, text)
            return
        if not amount:
            console.note("How much? Say an amount, or what you're paying for.")
            self.halted = True
            return
        if c.coins < amount:
            console.note(f"You only have {money.words(c.coins)}.")
            self.halted = True
            return
        if self.is_bribe(intent, text):
            self.offer_bribe(intent, text, npc, amount)
            return
        c.coins -= amount                                     # coin for nothing is a gift: taken, remembered, and the companions have a view
        from engine.domain_events import Gift
        self.notice(Gift(minute=self.minutes, place=self.player.location, witnesses=(npc.id,), npc=npc.id, name=npc.label(), coin=amount), npc)
        self.store.save_player(self.player)
        console.ledger(f"Gave {money.fmt(amount)} to {npc.label()}. Purse: {money.fmt(c.coins)}")
        intent.target = npc.id
        intent.speech = (intent.speech.strip() + " " if intent.speech.strip() else "") + \
            f"[They hand you {money.words(amount)}, asking nothing for it.]"
        self.on_talk(intent, text)

    BRIBE_WORDS = ("bribe", "look the other way", "blind eye", "let me through", "let me pass", "let me in", "keep quiet", "say nothing",
                   "forget", "overlook", "in exchange", "for your silence", "slip ", "grease", "so that you", "if you will", "to let")

    def is_bribe(self, intent, text: str) -> bool:
        low = f"{text} {intent.summary}".lower()
        return "persuasion" in intent.checks or any(w in low for w in self.BRIBE_WORDS)

    def offer_bribe(self, intent, text: str, npc, amount: int) -> None:
        """Coin offered for a favor: a persuasion roll, helped by how big the offer is next to what the person has. Success takes the coins
        (the favor only happens in the story); otherwise the coins stay, and a failure costs trust. The person remembers it either way."""
        from engine import checks as ck
        B = ck.RULES["bribe"]
        c = self.player.character
        wealth = B["wealth"].get(npc.role, B["default_wealth"])
        pct = amount / wealth * 100
        bonus = max(B["floor"], min(B["cap"], B["per_percent"] * (pct - B["break_even"])))
        extra = [(f"offer is {pct:.0f}% of their wealth", bonus)]
        mods = sum(B["traits"].get(t, 0) for t in npc.traits) + B["duty_roles"].get(npc.role, 0)
        if mods:
            extra.append(("character and duty", mods))
        degree = self.resolve("persuasion", npc, talking=True, text=text, extra=extra)
        favor = (intent.summary or "").strip().rstrip(".") or "do them a favor"
        paid = degree in ("strong success", "success")
        npc.trust = max(0, min(100, npc.trust + B["trust"][degree]))
        sum_ = money.words(amount)
        if paid:
            c.coins -= amount
            from engine import law
            npc.looks_away_until = self.minutes + law.N["look_away_minutes"]
            console.ledger(f"Gave {money.fmt(amount)} to {npc.label()}. Purse: {money.fmt(c.coins)}")
            effect = f"You are persuaded and take the {sum_}. You will do what they ask in the story, quietly."
        elif degree == "partial":
            effect = f"You are tempted by the {sum_} but it is not enough; you do NOT take it yet, and you want more or something else."
        else:
            effect = f"You refuse the {sum_} and think less of them for offering. You do NOT take it."
        from engine.domain_events import Bribe
        from engine import law as _law
        self.notice(Bribe(minute=self.minutes, place=self.player.location, witnesses=(npc.id,), npc=npc.id, name=npc.label(), amount=amount,
                          worked=paid, degree=degree, favor=favor, confrontation=False, guard=npc.role in _law.H["guard_roles"]), npc)
        console.debug(f"bribe: {sum_} is {pct:.1f}% of {npc.role} wealth {wealth}; bonus {bonus:+.0f}, traits/duty {mods:+d}; {degree}")
        self.store.save_npc(npc)
        self.store.save_player(self.player)
        self.last_social = ("persuasion", degree, npc.id)
        self.pending_check = f"[THE GAME HAS DECIDED: they offer you {sum_} to {favor}. {effect} Act on this.]"
        intent.target = npc.id
        intent.speech = (intent.speech.strip() + " " if intent.speech.strip() else "") + f"[They offer you {sum_}.]"
        self.on_talk(intent, text)

    TITHE_WORDS = ("tithe", "offering", "alms", "donat", "collection", "box", "plate")

    def tithe_box(self, intent, text: str) -> bool:
        """Coins into a temple's box. True if that is what this was (and it has been dealt with)."""
        from engine import standing
        named = (intent.item or "").lower()
        if self.place.type != "temple" or not any(w in named for w in self.COIN_WORDS) or inv.find(self.pack, named):
            return False
        low = f"{text} {intent.summary}".lower()
        if intent.target and any(n.id == intent.target for n in self.present) and not any(w in low for w in self.TITHE_WORDS):
            return False
        c = self.player.character
        amount = self.coin_amount(intent.item or "") or self.coin_amount(text)
        if not amount:
            console.note("How much? Say an amount.")
            self.halted = True
            return True
        if c.coins < amount:
            console.note(f"You only have {money.words(c.coins)}.")
            self.halted = True
            return True
        c.coins -= amount
        from engine.domain_events import Tithe
        self.notice(Tithe(minute=self.minutes, place=self.player.location, name=self.place.name, amount=amount, weight=standing.tithe_weight(amount)))
        self.store.save_player(self.player)
        console.note(f"You leave {money.fmt(amount)} in the tithe box. Purse: {money.fmt(c.coins)}")
        self.narrate(f"The player drops {money.words(amount)} into the tithe box at {self.place.name}. Two sentences, quiet and unhurried; "
                     f"nobody makes a fuss.", text)
        return True

    def on_give(self, intent, text: str) -> None:
        if self.tithe_box(intent, text):
            return
        from engine import mentor as _mt
        if not self.rank and self.clerk_here() and _mt.stage(self.player) == "sign" and not intent.target:
            from llm.contracts import ActionIntent                 # at the clerk's desk with Maren, coin held out is the joining fee (f283)
            self.on_join_guild(ActionIntent(kind="join_guild"), text)
            return
        npc = next((n for n in self.present if n.id == intent.target), None) or \
            (self.partner if self.partner in self.present else None)
        if not npc:
            key = self.find_key(intent.item or text)
            if key and key.for_whom:
                npc = next((n for n in self.present if self.is_recipient(n, key.for_whom)), None)
        if not npc or npc not in self.present:
            console.note("There's no one here to give that to.")
            self.halted = True
            return
        named = (intent.item or "").lower()
        if any(w in named for w in self.COIN_WORDS) and not inv.find(self.pack, named):
            self.pay_with_coins(intent, text, npc)
            return
        key = None if inv.find(self.pack, intent.item or text) else self.find_key(intent.item or text)
        if key:
            c = self.player.character
            c.key_items.remove(key)
            day = clock.day(self.minutes)
            delivered = key.kind == "quest" and self.is_recipient(npc, key.for_whom)
            if delivered:
                npc.trust = min(100, npc.trust + R["gift_trust"] + 1)
                c.item_history.append(f"Delivered {key.name} to {npc.name}, as {key.source} asked (day {day}).")
                console.ledger(f"Delivered: {key.name}.")
            else:
                meant = f" - it was meant for {key.for_whom}" if key.for_whom else ""
                c.item_history.append(f"Gave {key.name} to {npc.name}{meant} (day {day}).")
                console.ledger(f"Handed over: {key.name}{meant}.")
            from engine.domain_events import Delivered
            self.notice(Delivered(minute=self.minutes, place=self.player.location, witnesses=(npc.id,), npc=npc.id, name=npc.label(),
                                  item=key.name, asked_by=key.source, meant=delivered), npc)
            self.record_delivery(key, npc)
            self.store.save_player(self.player)
            intent.target = npc.id
            intent.speech = (intent.speech.strip() + " " if intent.speech.strip() else "") + \
                f"[They hand you {key.name} ({key.description}).]"
            self.on_talk(intent, text)
            return
        item = inv.take(self.pack, intent.item or text, 1)
        if not item:
            console.note("You aren't carrying that.")
            self.halted = True
            return
        from engine.domain_events import Gift                 # a thing given for nothing: taken, remembered, and the companions have a view
        self.notice(Gift(minute=self.minutes, place=self.player.location, witnesses=(npc.id,), npc=npc.id, name=npc.label(), item=inv.label(item)), npc)
        self.store.save_player(self.player)
        console.ledger(f"Gave {inv.label(item)} to {npc.label()}.")
        intent.target = npc.id
        intent.speech = (intent.speech.strip() + " " if intent.speech.strip() else "") + f"[They hand you {inv.label(item)}, asking nothing for it.]"
        self.on_talk(intent, text)

    def on_store(self, intent, text: str) -> None:
        if self.refuse_key(intent.item or text, "store"):
            return
        if not self.can_store():
            console.note("There's no item box here.")
            self.halted = True
            return
        item = inv.take(self.pack, intent.item or text, max(1, intent.count or 99))
        if not item:
            console.note("You aren't carrying that.")
            self.halted = True
            return
        leftover = inv.add(self.player.stash, item, self.stash_cap())
        if leftover:
            inv.add(self.pack, leftover, self.pack_slots() + 1)
            console.note(f"The item box is full - kept {inv.label(leftover)}.")
        self.store.save_player(self.player)
        console.ledger(f"Stored: {inv.label(item)}. Item box {len(self.player.stash)}/{self.stash_cap()}.")

    def on_retrieve(self, intent, text: str) -> None:
        if not self.can_store():
            console.note("There's no item box here.")
            self.halted = True
            return
        item = inv.take(self.player.stash, intent.item or text, max(1, intent.count or 99))
        if not item:
            console.note("That isn't in your item box.")
            self.halted = True
            return
        self.to_pack(item)
        self.store.save_player(self.player)
        console.ledger(f"Took from the item box: {inv.label(item)}.")

    def on_equip(self, intent, text: str) -> None:
        self.equip_command(intent.item or text)

    def companion_alive(self) -> bool:
        """A bound companion travels with the player (companions recover between fights)."""
        c = self.player.character
        return any(m.active for m in c.companions) or bool(c.bound_summon and not c.bound_broken)   # a companion, or the Bound summon

    def on_forage(self, intent, text: str) -> None:
        biome = self.place.biome
        herbs = [g for g in inv.GOODS.values() if biome in g.grows_in]
        if not herbs and not (biome in ("hills", "mountains") and self.owns("prospector")):
            self.narrate("The player looks for useful plants, but nothing worth gathering grows here.", text)
            return
        self.advance(R["forage_minutes"])
        if self.place.danger and self.maybe_encounter(
                encounters.E["chance_per_hour"] * R["forage_minutes"] / 60 * 2, "While you forage,"):
            return
        found = {}
        boost = (self.has("forager") or 0)
        if clock.season(self.minutes) in ("spring", "summer"):
            boost += self.has("green_hands") or 0
        if self.companion_alive():
            boost += self.has("familiar_forager") or 0
        if clock.season(self.minutes) in ("autumn", "winter"):
            boost += self.has("root_and_rot") or 0
        tries = random.randint(*R["forage_finds"])
        tries = int(tries * (1 + boost / 100) + (random.random() < (tries * boost / 100) % 1))
        for _ in range(tries):
            for g in herbs:
                if random.random() < g.grows_in[biome]:
                    found[g.id] = found.get(g.id, 0) + 1
                    break
        extras = []
        if self.place.danger and self.owns("hunters_larder") and random.random() < 0.35:
            meat = random.choice([g for g in inv.GOODS.values() if g.kind == "food" and g.drops_from] or [None])
            if meat:
                found[meat.id] = found.get(meat.id, 0) + 1
        if biome in ("hills", "mountains") and self.owns("prospector") and random.random() < 0.35:
            ore = random.choice(["bronze", "bog_iron", "iron"] if biome == "mountains" else ["bronze", "bog_iron"])
            extras.append(items.make_raw(ore))
        if not found and not extras:
            self.narrate("The player spends half an hour searching the ground for useful plants and finds nothing "
                         "worth taking this time.", text)
            return
        for extra in extras:
            self.to_pack(extra)
            found_note = items.MATERIALS[extra.material].name
            console.ledger(f"Among the stones: raw {found_note}.")
        for gid, n in found.items():
            self.to_pack(inv.make_good(gid, n))
        self.store.save_player(self.player)
        got = ", ".join(f"{n} {inv.GOODS[g].name}" for g, n in found.items())
        console.ledger(f"Gathered: {got}.")
        self.narrate(f"The player spends half an hour foraging and gathers {got}.", text)

    def on_craft(self, intent, text: str) -> None:
        recipe = inv.find_recipe(intent.item or text)
        if not recipe and crafting.find_base(intent.item or text):
            self.craft_gear(intent, text)
            return
        if not recipe:
            names = ", ".join(inv.GOODS[next(iter(r.makes))].name for r in inv.RECIPES.values())
            console.note(f"You don't know how to make that. You can make: {names}.")
            self.halted = True
            return
        missing = inv.can_craft(self.pack, recipe)
        if missing:
            console.note(f"You need {', '.join(missing)}.")
            self.halted = True
            return
        c = self.player.character
        origin = ""
        for ing in recipe.ingredients:
            saved = 1 if random.random() < crafting.mechanic(c, "thrifty") / 100 else 0
            herb = ing.good in inv.GOODS and inv.GOODS[ing.good].kind == "herb"
            if not saved and herb and random.random() < crafting.mechanic(c, "herb_wise") / 100:
                saved = 1
            taken = inv.remove_goods(self.pack, ing.good, ing.kind, max(0, ing.count - saved), ing.meat)
            if ing.meat:
                origin = next((t.origin for t in taken if t.origin), "")      # a meal keeps the beast it was made from
        extra = 1 if random.random() < (self.has("brewer") or 0) / 100 else 0
        for gid, n in recipe.makes.items():
            made = inv.make_good(gid, n + extra)
            made.origin = origin
            self.to_pack(made)
            if extra:
                console.ledger(f"A little extra: one more {inv.GOODS[gid].name}.")
        self.campfire_cook(recipe.makes)
        crafting.raise_skill(c, crafting.skill_gain(c, False))
        self.craft_boost = 0
        self.advance(round(R["craft_minutes"] * (1 - crafting.mechanic(c, "quick_hands") / 100)))
        self.store.save_player(self.player)
        made = ", ".join(f"{n} {inv.GOODS[g].name}" for g, n in recipe.makes.items())
        console.ledger(f"Made: {made}.")
        self.narrate(f"The player spends half an hour working and makes {made}.", text)

    def craft_gear(self, intent, text: str) -> None:
        c = self.player.character
        words = f"{intent.item} {text}"
        base = crafting.find_base(words)
        station = crafting.station_for(base)
        spot = self.place.stations.get(station)
        practiced = spot is None and self.owns("practiced_hands") and base.id in c.recipes_made
        field = spot is None and not practiced and self.owns("field_kit")
        if field or practiced:
            spot = {"owner": "", "fee": 0}
        if spot is None:
            where = [p.name for p in self.world.places.values() if station in p.stations]
            console.note(f"Making {base.name} needs a {station.replace('_', ' ')}"
                         + (f" - there's one at {', '.join(where)}." if where else "."))
            self.halted = True
            return
        owner = next((n for n in self.present if n.role == spot.get("owner")), None) if spot.get("owner") else None
        if spot.get("owner") and not owner:
            console.note(f"The {station.replace('_', ' ')} belongs to the {spot['owner'].replace('_', ' ')}, who isn't here right now.")
            self.halted = True
            return
        need = crafting.units_for(base)
        material, have = crafting.pick_material(self.pack, base.family, words, need)
        if not material:
            got = ", ".join(f"{n} {items.MATERIALS[m].name}" for m, n in have.items()) or "none"
            console.note(f"{base.name.capitalize()} takes {need} {base.family} materials of one kind. You have: {got}.")
            self.halted = True
            return
        fee = spot.get("fee", 0)
        if fee and self.owns("workshop_regular") and self.town_rep() >= 10:
            fee = 0
        if fee and c.coins < fee:
            console.note(f"Using the {station.replace('_', ' ')} costs {money.words(fee)}, and you have {money.words(c.coins)}.")
            self.halted = True
            return
        c.coins -= fee
        saved = sum(1 for _ in range(need) if random.random() < crafting.mechanic(c, "thrifty") / 100)
        crafting.use_material(self.pack, material, need - min(saved, need - 1))
        boost = getattr(self, "craft_boost", 0)
        skill = crafting.effective_skill(c) - (self.mech("field_kit") if field else 0)
        floor = "common" if self.owns("never_shoddy") else "crude"
        studied = c.studied.get(base.id) if self.owns("reverse_engineer") else None
        if studied and crafting.RARITY_ORDER.index(studied) > crafting.RARITY_ORDER.index(floor):
            floor = studied                               # Reverse Engineer: at least as fine as the piece you studied
        item = crafting.make_gear(base, material, skill, random.Random(), boost, floor=floor)
        item.source = "your own work"
        if not (field or practiced) and base.id not in c.recipes_made:
            c.recipes_made.append(base.id)                # Practiced Hands remembers what was made at a proper workshop
        self.craft_boost = 0
        before, after = crafting.raise_skill(c, crafting.skill_gain(c, True, material))
        self.to_pack(item)
        self.advance(round(crafting.RULES["gear_minutes"] * (1 - crafting.mechanic(c, "quick_hands") / 100)))
        self.store.save_player(self.player)
        paid = f" Paid {money.fmt(fee)} to use the {station.replace('_', ' ')}." if fee else (" No workshop needed - you have made this before (Practiced Hands)." if practiced else "")
        thrift = f" Saved {saved} material." if saved else ""
        console.ledger(f"Crafted: {quality_name(item)} (lv {item.item_level}).{paid}{thrift} "
                     f"Crafting skill {before:.0f} -> {after:.0f}.")
        self.narrate(f"The player spends a couple of hours {'with their tools, no workshop needed,' if practiced else 'at the ' + station.replace('_', ' ')} and makes "
                     f"{item.name} from {items.MATERIALS[material].name} - {item.rarity} work.", text)

    def on_commission(self, intent, text: str) -> None:
        c = self.player.character
        words = f"{intent.item} {text}"
        crafters = [n for n in self.present if self.world.roles[n.role].commissions]
        base = crafting.find_base(words, [f for n in crafters for f in self.world.roles[n.role].commissions])
        crafter = next((n for n in crafters if base and base.family in self.world.roles[n.role].commissions), None)
        if not crafter or not base:
            offers = "; ".join(f"{n.label()} makes {', '.join(self.world.roles[n.role].commissions)} gear" for n in crafters)
            console.note("No one here can make that." + (f" {offers}." if offers else ""))
            self.halted = True
            return
        need = crafting.units_for(base)
        own, have = crafting.pick_material(self.pack, base.family, words, need)
        said = words.lower()
        use_own = own and (any(w in said for w in ("my ", "these", "from the", "from my", "with my", "using", "mine"))
                           or items.MATERIALS[own].name in said)
        level_cap = self.place.trade_level
        material = own if use_own else items.choose_material(base.family, level_cap[1], plainest=True)
        role = self.world.roles[crafter.role]
        rng = random.Random()
        item = crafting.make_gear(base, material, role.craft_skill, rng, cap=None if use_own else level_cap)
        common_value = items.price(items.make(base.id, "common", item.item_level, material=material))
        materials_cost = 0 if use_own else need * items.price(items.make_raw(material))
        haggle = 1 - (crafting.mechanic(c, "haggler") + crafting.mechanic(c, "commission_broker")) / 100
        price = round((common_value * crafting.RULES["commission_labor"] + materials_cost) * haggle)
        if c.coins < price:
            console.note(f"{crafter.label()} would want {money.words(price)} for {base.name} in "
                         f"{items.MATERIALS[material].name}; you have {money.words(c.coins)}.")
            self.halted = True
            return
        c.coins -= price
        if use_own:
            crafting.use_material(self.pack, material, need)
        ready = self.minutes + round(crafting.RULES["commission_days"] * 1440
                                     * (1 - crafting.mechanic(c, "commission_broker") / 100))
        self.player.commissions.append({"npc": crafter.id, "npc_name": crafter.label(), "item": item.model_dump(),
                                        "ready": ready})
        crafter.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                       text=f"The stranger paid {money.words(price)} for me to make {base.name}."))
        self.store.save_npc(crafter)
        self.store.save_player(self.player)
        console.ledger(f"Commissioned {items.MATERIALS[material].name} {base.label or base.name} from {crafter.label()} "
                     f"for {money.fmt(price)}" + (" (your materials)" if use_own else "")
                     + ". Ready in about a day - collect it while they're at work.")
        self.narrate(f"The player pays {crafter.label()} {money.words(price)} to make {base.name} from "
                     f"{items.MATERIALS[material].name}. They agree it will be ready in a day or so.", text)

    def collect_commissions(self) -> None:
        """Hand over finished commissions when their maker is present."""
        here = {n.id for n in self.present}
        for order in list(self.player.commissions):
            if order["npc"] in here and order["ready"] <= self.minutes:
                item = Item.model_validate(order["item"])
                self.player.commissions.remove(order)
                self.to_pack(item)
                console.note(f"{order['npc_name'].capitalize()} hands over your commission: {quality_name(item)} "
                             f"(lv {item.item_level}).")
                self.store.save_player(self.player)

    def ensure_stock(self, npc) -> None:
        rule = self.world.roles[npc.role].stock
        if rule and crafting.restock_due(npc, rule, clock.day(self.minutes)):
            crafting.lay_out_stock(npc, rule, self.place.trade_level, clock.day(self.minutes), self.store.meta.seed)
            self.store.save_npc(npc)

    def stock_here(self) -> list[tuple]:
        """(npc, item, price) for every piece of gear on sale from merchants present."""
        out = []
        from engine import pulse
        haggle = max(0, 1 - (crafting.mechanic(self.player.character, "haggler") + self.guild_perks()["shop_discount"] + self.barter_pct()) / 100) \
            * pulse.price_factor(self.store, self.world, self.player.location, self.minutes) * self.heat_price()
        for n in self.present:
            if self.world.roles[n.role].stock:
                self.ensure_stock(n)
                out += [(n, i, round(items.price(i) * haggle * self.stock_multiplier(n, i))) for i in crafting.stock_items(n)]
            if self.world.roles[n.role].relics:
                town = property_rules.town_of(self.world, self.player.location)
                out += [(n, i, round(p * haggle)) for i, p in property_rules.relics_in(self.world, self.store.meta.seed, town, self.player.relics_bought)]
        return out

    BUSINESS_PLACES = ("shop", "smithy", "workshop", "inn", "yard", "town", "village", "square")     # small settlements and market squares are where their sellers work

    def show_shop(self) -> None:
        """What is for sale, but only inside a place of business and only from people you have met."""
        if self.place.type not in self.BUSINESS_PLACES:
            console.note("Nothing is sold here. Wares are shown at a shop, smithy, workshop, inn, caravan yard, market square or village.")
            return
        data = self.shop_data()
        if not data["sellers"]:
            if self.stable_stock():
                self.show_stable()
            else:
                who = self.trades_here()
                console.note(f"No one you have spoken to sells here yet. Trading here: {who}. Speak to them first." if who
                             else "No one is selling anything here right now.")
            return
        if console.panel("shop", data):                    # the window draws this one with Buy and Sell buttons
            self.show_stable()
            return
        for sl in data["sellers"]:
            console.note(f"{sl['name']}:")
            for w in sl["wares"]:
                more = " - ".join(x for x in (w["detail"], w["note"]) if x)
                console.note(f"  {w['name']}" + (f" ({more})" if more else "") + f" - {w['price_text']}")
            if sl["buys"]:
                console.note(f"  buys: {', '.join(sl['buys'])}")
        if data["sell"]:
            console.note("Your pack would fetch:")
            for x in data["sell"]:
                console.note(f"  {x['name']} - {x['total_text']} (from {x['buyer_name']})")
        self.show_stable()
        console.note(f"Your purse: {data['purse']}")

    def buy_from_stock(self, intent, text: str) -> bool:
        """Buy a piece of gear from a merchant's stock. Returns False if nothing in stock matches."""
        offers = self.stock_here()
        if not offers:
            return False
        named = inv.find([i for _, i, _ in offers], intent.ware or intent.item or text)
        if not named:
            return False
        npc, item, price = next(o for o in offers if o[1].uid == named.uid)
        self.buy_stock_item(npc, item, price, text)
        return True

    def on_sell(self, intent, text: str) -> None:
        if self.refuse_key(intent.item or text, "sell"):
            return
        item = inv.find(self.pack, intent.item or text)
        if not item:
            worn = equipment.find(self.player.character, intent.item or text, "equipped")
            console.note(f"{items.display_name(worn).capitalize()} is equipped. Unequip it first." if worn else "You aren't carrying that.")
            self.halted = True
            return
        cat = inv.category(item)
        buyers = [n for n in self.present if cat in self.world.roles[n.role].buys or "any" in self.world.roles[n.role].buys]
        buyer = next((n for n in buyers if n.id == intent.target), None) or \
            (sorted(buyers, key=lambda n: -(self.world.roles[n.role].buy_rate or R["sell_rate"]))[0] if buyers else None)
        if not buyer:
            console.note(f"No one here buys {cat}.")
            self.halted = True
            return
        sold = inv.take(self.pack, intent.item or text, max(1, intent.count))
        self.finish_sale(sold, buyer, text)
