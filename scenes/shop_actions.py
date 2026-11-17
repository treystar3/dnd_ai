import re
"""Buying and selling as plain actions: the typed commands ("buy the sword", "sell the pelts") and the shop pane's buttons
both end here, so prices, haggling, merchant memory and saving are the same either way.

Mixed into WorldScene. A button click runs quietly: one line in the log, no narrated scene and no model call."""

from engine import clock, crafting, inventory as inv, items, money, needs, pools, pulse
from engine import regard                                   # (f480)
from engine.names import cap_first
from scenes.inventory_actions import quality_name
from ui import console

R = inv.RULES


class ShopActions:

    # ---------- what a ware costs / what a pack item fetches ----------

    def price_of(self, base: float, seller=None, kind: str = "", good: str = "") -> int:
        """(f418) What a thing sold here costs the player, now: a ware, a piece of stock, a relic, a mount. Every quote a person gives,
        every list the player or the interpreter is shown, and every charge is this one sum, so the figure named is the figure taken.
        Before, four sums disagreed: a hungry town's bowl was quoted at its old price and charged a third more, the stock left out the
        guild's and the ascetic's discounts, a stable ignored what the town thought of the player. kind: a room or a meal takes the
        discounts that are theirs."""
        c = self.player.character
        off = crafting.mechanic(c, "haggler") + self.barter_pct() + self.guild_perks()["room_discount" if kind == "room" else "shop_discount"]
        if kind in ("room", "meal"):
            off += crafting.mechanic(c, "ascetic")
        if seller is not None and seller.role == "quartermaster":
            off += self.mech("quartermasters_friend")
        return round(base * max(0, 1 - off / 100) * pulse.price_factor(self.store, self.world, self.player.location, self.minutes, good)
                     * self.heat_price() * getattr(self, "haggle_factor", 1.0))                  # (f332) a price a haggle won

    @staticmethod
    def with_level(item, text: str) -> str:
        """(f672) A row's words with the item's level written once: the summary's own when it has one, else put first. The page sets the
        dot after it (app.js tidy): "lv 6 · · lv 6" was the level written by the shop, the summary and the page."""
        return text if text.startswith("lv ") else f"lv {item.item_level} {text}"

    def wares_of(self, npc) -> list:
        """(f545) What this person sells: their trade's list, and what they really hold of a good (a situation's stock, sold until it is
        gone). Every reader of a seller's wares asks here."""
        from engine import situation_parts
        return situation_parts.wares(self.store, self.world, npc)          # (f545's review) what they hold first, a good one ware

    def ware_asked(self, wares, wanted: str):
        """(f545's review) The ware a buyer asks for: by its id, or the words asked being in its name, or what is asked ending in the
        ware's own word ("some rope", "a sack of salt"); never a ware whose word only sits inside another ("clothes", "salted pork", "a
        rope ladder", "grain alcohol")."""
        if not wanted:
            return None
        head = inv.asked_head(wanted)                    # (f655) "a room for the night" asks for a room, never the night
        return next((w for w in wares if w.id == wanted), None) or \
            next((w for w in wares if re.search(rf"\b{re.escape(inv.asked_part(wanted))}\b", inv.asked_part(w.name))), None) or \
            next((w for w in wares if head and head in inv.ware_words(w)
                  and head in {inv._head(w.name), inv.asked_head(w.name), inv._head(w.id.replace("_", " "))}
                  | ({inv._head(inv.GOODS[w.item].name)} if w.kind == "item" and w.item in inv.GOODS else set())), None)

    def quote_ware(self, seller, ware, announce: bool = False):
        """The ware with its price after haggling, guild discount, the town's prices and your heat (price_of)."""
        ware = ware.model_copy(update={"price": self.price_of(ware.price, seller, ware.kind, ware.item if ware.kind == "item" else "")})
        if ware.kind == "room" and ((self.owns("shelter_earned") and self.town_rep() >= 30)
                                    or self.player.free_room_day == clock.day(self.minutes)):
            ware = ware.model_copy(update={"price": 0})
            if announce:
                console.note("The room is yours tonight, free. " + ("You're well thought of here."
                             if self.player.free_room_day != clock.day(self.minutes) else "Your song paid for it."))
        return ware

    def sell_rate(self, item, buyer) -> float:
        rate = (self.world.roles[buyer.role].buy_rate or R["sell_rate"]) * \
            (1 + (crafting.mechanic(self.player.character, "haggler") + self.barter_pct()) / 100)
        if item.base != "raw_material" and not item.good and self.has("veterans_eye"):
            rate *= 1 + self.has("veterans_eye") / 100
        return rate * self.sell_multiplier(item)

    def sell_total(self, item, buyer, quantity: int | None = None) -> int:
        qty = item.quantity if quantity is None else quantity
        return max(1, round(inv.unit_value(item) * qty * self.sell_rate(item, buyer)))

    def best_buyer(self, item, people=None):
        cat = inv.category(item)
        people = self.present if people is None else people
        buyers = [n for n in people if cat in self.world.roles[n.role].buys or "any" in self.world.roles[n.role].buys]
        return max(buyers, key=lambda n: self.world.roles[n.role].buy_rate or R["sell_rate"], default=None)

    # ---------- doing it ----------

    SINGLY = "That is sold one at a time. Ask for one."
    ROOM_SINGLY = "Rooms go one at a time, for one night. Ask for a room."
    MOST_AT_ONCE = 99                                         # (f646) how_many's own most (scenes/inventory_actions.py)

    @staticmethod
    def count_asked(intent) -> int:
        """(f646) How many a purchase asks for: the reading's own count, never a number read out of a name ("a meal for the two of
        us", "Blade of Seven Stars"), which would spend coin nobody offered."""
        return max(1, int(getattr(intent, "count", 1) or 1))

    def one_only(self, intent) -> bool:
        """(f646) A thing sold singly (a piece of gear, a mount, a house) asked for in a number: refused in a line, before anything
        is paid."""
        if self.count_asked(intent) <= 1:
            return False
        self.refuse(self.SINGLY)
        return True

    def held_of(self, seller, ware) -> list:
        """(f646) The rows of what this seller holds of a ware sold from their own stock."""
        from engine import situation_parts
        return situation_parts.held(self.store, seller.id, ware.item)

    @staticmethod
    def several(name: str, n: int, measure: bool = False) -> str:
        """(f646) A ware by its number, as a person would say it: "a jar of wine" is "three jars of wine", "bandage" "two bandages";
        and a good sold by measure under its bare name ("salt") is "three measures of salt"."""
        from engine import mentor, quests
        if n <= 1:
            return name
        bare = re.sub(r"^(?:a|an|the|some)\s+", "", name.strip(), flags=re.I)
        word = next((w for w, k in mentor.WORD_NUM.items() if k == n), str(n))
        if measure:
            return f"{word} measures of {bare}"
        head, of, rest = bare.partition(" of ")
        return f"{word} {head if head.endswith('s') else quests.plural(head)}{of}{rest}"

    def ware_several(self, ware, n: int) -> str:
        """(f646) A seller's ware by its number (several). What they hold goes by the good's bare name ("wine"): it is said as the
        trades sell it ("jars of wine"), or by measure when no trade does and it is a good of that kind."""
        good = inv.GOODS.get(ware.item) if ware.kind == "item" else None
        name = ware.name
        if good is not None and name == good.name:
            name = next((w.name for r in self.world.roles.values() for w in r.sells if w.kind == "item" and w.item == good.id), name)
        return self.several(name, n, measure=good is not None and bool(good.mass) and name == good.name)

    @staticmethod
    def set_down(st, what: str) -> str:
        """(f646) Several bought and the pack too full (f417): none of them fit, or only some."""
        none = st.kept is None
        return f"They have {what}, but no room to carry {'them' if none else 'all of them'}: {'they are' if none else 'the rest is'} set down here."

    def buy_ware(self, seller, ware, text: str = "", quiet: bool = False, count: int = 1) -> bool:
        """Pay for a seller's listed ware (food, rooms, materials, goods), `count` of it (f646). ware is the unpriced listing."""
        c = self.player.character
        n = held = max(1, int(count))                         # (f646) held: how many of them come out of what the seller holds
        if n > 1 and ware.kind == "room":                     # (f646) before the quote: a free room is not announced and then refused
            self.refuse(self.ROOM_SINGLY)
            return False
        if n > self.MOST_AT_ONCE:                             # (f646) refused, never cut to what is sold and charged for that
            self.refuse(f"No one sells more than {self.MOST_AT_ONCE} of a thing at once.")
            return False
        ware = self.quote_ware(seller, ware, announce=True)
        if n > 1:                                             # (f646) a count asked for is kept whole, or refused in a line
            total = ware.price * n
            if ware.id.startswith("stock:"):                  # what they hold first; the rest from their trade's own list, at its price
                have = sum(int(e.data.get("count", 0)) for e in self.held_of(seller, ware))
                trade = next((w for w in self.world.roles[seller.role].sells if w.kind == "item" and w.item == ware.item), None)
                if have < n and trade is None:
                    self.refuse(f"{cap_first(seller.label(self.acting))} has only {'the one' if have == 1 else self.ware_several(ware, have)} to sell.")
                    return False
                held = min(have, n)
                if held < n:
                    total = ware.price * held + self.quote_ware(seller, trade).price * (n - held)
            if c.coins < total:
                self.refuse(f"{cap_first(self.ware_several(ware, n))} come to {money.words(total)}, and you have {money.words(c.coins)}.")
                return False
            ware = ware.model_copy(update={"price": total, "name": self.ware_several(ware, n)})
        if c.coins < ware.price:
            if quiet:
                console.note(f"You can't afford {ware.name} ({money.fmt(ware.price)}). Purse: {money.fmt(c.coins)}")
            else:
                self.narrate(f"The player tries to pay {seller.label(self.acting)} for {ware.name}, which costs {money.words(ware.price)}, "
                             f"but they only have {money.words(c.coins)}. Show the awkward moment.", text)
                self.halted = True
            return False
        if ware.kind == "room" and self.player.room == self.player.location and self.player.room_until > self.minutes:
            self.refuse("You already have a room here until mid-morning tomorrow. No charge.")
            return False
        c.coins -= ware.price
        self.use_barter()                                    # (f418) the price it bought was the bargained one
        effect = ""
        if ware.kind == "room":
            now = clock.absolute(self.minutes)
            nights_end = (now // 1440 + 1) * 1440 + 10 * 60 - clock.absolute(0)
            self.player.room, self.player.room_until = self.player.location, nights_end
            effect = "They are shown a small room upstairs that is theirs until mid-morning tomorrow."
        elif ware.kind == "material" and ware.item:
            st = self.to_pack(items.make_raw(ware.item).model_copy(update={"quantity": n}))
            effect = (f"They take {ware.name}." if st.left is None
                      else f"They have {ware.name}, but no room to carry it: it is set down here." if n == 1 else self.set_down(st, ware.name))
        elif ware.kind == "item" and ware.item:
            if ware.id.startswith("stock:"):                          # (f545) from what they hold: that many fewer, until it is gone
                from engine import situation_parts
                situation_parts.take_stock(self.store, seller.id, ware.item, held, self.minutes, "sold_out")
            st = self.to_pack(inv.make_good(ware.item, n))           # (f417) a full pack: it is bought, and set down here, not pocketed
            what = inv.GOODS[ware.item].name if n == 1 else ware.name
            effect = (f"They put {what} in their pack." if st.left is None
                      else f"They have {what}, but no room in their pack for it: it is set down here." if n == 1 else self.set_down(st, what))
        elif ware.kind in ("meal", "drink"):
            meal = needs.N["meal"]
            share = {"stamina": 0.25, "health": meal["health"] / 100} if ware.kind == "meal" else {"stamina": 0.08, "health": 0.0}
            for _ in range(n):                                        # (f646) each one paid for is eaten or drunk
                for pool, part in share.items():
                    top = pools.maximum(c, pool)
                    setattr(c, pool, min(top, pools.current(c, pool) + top * part))
                needs.eat(c, meal["feeds"] if ware.kind == "meal" else 5)
            effect = "They eat and feel restored." if ware.kind == "meal" else "They drink."
            from engine import world_perks
            if ware.kind in world_perks.P["tavern_ear"]["wares"]:
                self.tavern_ear(seller)
        from engine.domain_events import Traded
        self.notice(Traded(minute=self.minutes, place=self.player.location, witnesses=(seller.id,), npc=seller.id, name=seller.label(self.acting),
                           item=ware.name, coins=ware.price, bought=True), seller)
        self.store.save_player(self.player)
        from engine import ledger                       # (f417) settled: what the seller says after it, and the passage, read it
        ledger.add("paid", to=seller.id, amount=ware.price, say=f"The player has paid {seller.label(self.acting)} for {ware.name}; it is settled.",
                   facts={"who": seller.label(self.acting), "amount": money.fmt(ware.price), "what": ware.name})          # (f464) for the stand-in line
        console.ledger(f"Paid {money.fmt(ware.price)} for {ware.name}. Purse: {money.fmt(c.coins)}")
        if quiet:
            if ware.kind == "room":
                console.note("A room upstairs is yours until mid-morning tomorrow.")
            elif ware.kind in ("meal", "drink"):
                console.note("You eat, and feel better for it." if ware.kind == "meal" else "You drink.")   # (f712) the player's, not the narrator's
        else:
            self.narrate(f"The player pays {seller.label(self.acting)} for {ware.name}, and the coins change "
                         f"hands. {effect} Describe the exchange.", text)
        return True

    def buy_stock_item(self, npc, item, price: int, text: str = "", quiet: bool = False) -> bool:
        """Buy a piece of gear (or a relic) from a merchant's stock at the quoted price."""
        c = self.player.character
        if c.coins < price:
            if quiet:
                console.note(f"You can't afford {item.name} ({money.fmt(price)}). Purse: {money.fmt(c.coins)}")
            else:
                self.narrate(f"The player wants {item.name} from {npc.label(self.acting)}, which costs {money.words(price)}, but they "
                             f"only have {money.words(c.coins)}. Show the moment.", text)
                self.halted = True
            return False
        c.coins -= price
        self.use_barter()
        if item.uid.startswith("relic_"):
            self.player.relics_bought.append(item.uid[len("relic_"):])
        else:
            crafting.remove_from_stock(npc, item.uid)
        from engine.domain_events import Traded
        self.notice(Traded(minute=self.minutes, place=self.player.location, witnesses=(npc.id,), npc=npc.id, name=npc.label(self.acting),
                           item=item.name, coins=price, bought=True), npc)
        st = self.to_pack(item)
        self.store.save_player(self.player)
        from engine import ledger
        ledger.add("paid", to=npc.id, amount=price, say=f"The player has bought {item.name} from {npc.label(self.acting)}; it is settled.",   # (f417)
                   facts={"who": npc.label(self.acting), "amount": money.fmt(price), "what": item.name})                    # (f464) for the stand-in line
        console.note(f"Bought {quality_name(item)} (lv {item.item_level}) for {money.fmt(price)}. "
                     f"Purse: {money.fmt(c.coins)}")
        if item.uid.startswith("relic_"):
            self.weight_hint = "major"
        if not quiet:
            self.narrate(f"The player buys {item.name} from {npc.label(self.acting)}."
                         + (" Their pack is full: it is set down here, not carried." if st.left is not None else ""), text)
        return True

    def finish_sale(self, sold, buyer, text: str = "", quiet: bool = False) -> int:
        """Pay for an item already taken out of the pack. Returns what was paid."""
        paid = self.sell_total(sold, buyer)
        self.salvage(sold)
        self.known_work_sold(sold)
        self.player.character.coins += paid
        self.use_barter()
        from engine.domain_events import Traded
        self.notice(Traded(minute=self.minutes, place=self.player.location, witnesses=(buyer.id,), npc=buyer.id, name=buyer.label(self.acting),
                           item=inv.label(sold), coins=paid, bought=False), buyer)
        self.store.save_player(self.player)
        from engine import ledger
        ledger.add("received", by=buyer.id, amount=paid,                                                  # (f417)
                   say=f"{buyer.label(self.acting)} has bought {inv.label(sold)} from the player and paid for it; it is settled.")
        console.note(f"Sold {inv.label(sold)} to {buyer.label(self.acting)} for {money.fmt(paid)}. Purse: {money.fmt(self.player.character.coins)}")
        if not quiet:
            self.narrate(f"The player sells {inv.label(sold)} to {buyer.label(self.acting)}, who pays for it.", text)
        return paid

    def take_stack(self, first):
        """Remove a whole stack (every item that stacks with first) from the pack."""
        if inv.stack_size(first) == 1:
            self.pack.remove(first)
            return first
        total = 0
        for have in [b for b in self.pack if inv.same_stack(b, first)]:
            total += have.quantity
            self.pack.remove(have)
        return first.model_copy(update={"quantity": total})

    # ---------- the shop pane ----------

    def met_sellers(self) -> list:
        roles = self.world.roles
        return [n for n in self.present if regard.of(n, self.acting).met and (self.wares_of(n) or roles[n.role].stock or roles[n.role].relics)]

    def trades_here(self) -> str:
        """(f328) Who sells here that you have not spoken to yet, and what they deal in: 'the smith (gear), Pell the carter (trail ration, torch)'."""
        roles = self.world.roles
        out = []
        for n in self.present:
            r = roles[n.role]
            sells = self.wares_of(n)
            if regard.of(n, self.acting).met or not (sells or r.stock or r.relics):
                continue
            deals = [re.sub(r"^(a|an) ", "", w.name) for w in sells][:3] + (["gear"] if r.stock else []) + (["relics"] if r.relics else [])
            more = "…" if len(sells) > 3 else ""
            out.append(f"{n.label(self.acting)} ({', '.join(deals)}{more})")
        return ", ".join(out)

    def shop_data(self) -> dict:
        """Everything the shop pane shows, as plain data: who sells what at what price, and what each pack item would fetch."""
        c = self.player.character
        from engine import equipment
        offers = self.stock_here()
        sellers = []
        for n in self.met_sellers():
            role = self.world.roles[n.role]
            lines = []
            for w in self.wares_of(n):
                q = self.quote_ware(n, w)
                lines.append({"kind": "ware", "key": w.id, "name": w.name, "detail": w.kind if w.kind not in ("item", "material") else "",
                              "price": q.price, "price_text": money.fmt(q.price), "price_short": money.short(q.price), "afford": c.coins >= q.price, "note": ""})
            for o_npc, i, price in offers:
                if o_npc.id != n.id:
                    continue
                need = equipment.level_needed(i)
                note = f"needs you at level {need} to equip" if c.level < need else ""
                relic = i.uid.startswith("relic_")
                lines.append({"kind": "stock", "key": i.uid, "name": f"{i.name}, {i.title}" if relic else quality_name(i), "rarity": i.rarity,
                              "detail": self.with_level(i, i.description if relic else items.summary(i)[:90]),
                              "price": price, "price_text": money.fmt(price), "price_short": money.short(price), "afford": c.coins >= price, "note": note})
            sellers.append({"id": n.id, "name": n.label(self.acting), "wares": lines,
                            "buys": [b for b in role.buys if b != "any"] or (["anything"] if "any" in role.buys else [])})
        sell = []
        present = [n for n in self.present if regard.of(n, self.acting).met]     # (f480)
        for it in self.pack:
            buyer = self.best_buyer(it, present)
            if not buyer:
                continue
            total = self.sell_total(it, buyer)
            sell.append({"uid": it.uid, "name": inv.label(it), "detail": items.summary(it)[:90], "qty": it.quantity, "rarity": it.rarity,
                         "total": total, "total_text": money.fmt(total), "total_short": money.short(total), "buyer": buyer.id, "buyer_name": buyer.label(self.acting),
                         "legendary": it.rarity == "legendary"})
        return {"purse": money.fmt(c.coins), "sellers": sellers, "sell": sell}

    def shop_click(self, text: str) -> None:
        """The pane's hidden commands:  #shopbuy ware|stock <seller id> <key>   #shopsell <buyer id> <item uid>."""
        parts = text.split()
        present = {n.id: n for n in self.present}
        done = False
        if parts[0].lower() == "#shopbuy" and len(parts) >= 4:
            seller = present.get(parts[2])
            if seller and parts[1] == "ware":
                ware = next((w for w in self.wares_of(seller) if w.id == parts[3]), None)
                if ware:
                    self.buy_ware(seller, ware, quiet=True)
                    done = True
            elif seller and parts[1] == "stock":
                offer = next((o for o in self.stock_here() if o[0].id == seller.id and o[1].uid == parts[3]), None)
                if offer:
                    self.buy_stock_item(offer[0], offer[1], offer[2], quiet=True)
                    done = True
        elif parts[0].lower() == "#shopsell" and len(parts) >= 3:
            buyer = present.get(parts[1])
            item = next((i for i in self.pack if i.uid == parts[2]), None)
            cat_ok = buyer and item and (inv.category(item) in self.world.roles[buyer.role].buys or "any" in self.world.roles[buyer.role].buys)
            if cat_ok:
                self.finish_sale(self.take_stack(item), buyer, quiet=True)
                done = True
        if not done:
            console.note("That is no longer on offer.")
        with console.scope("#shop"):
            self.show_shop()
