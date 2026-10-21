"""Houses and basecamps: buying a home from a land agent, paying for upgrades, and what a home gives back."""

import re

from engine import clock, inventory as inv, money, pools, property as prop
from engine.property import P
from ui import console

BUY_WORDS = re.compile(r"\b(house|home|cottage|property|deed|townhouse|villa|longhouse|lodge|estate|lot)\b")


class PropertyActions:

    def ensure_homes(self) -> None:
        prop.register(self.world, self.player)

    def home_here(self) -> dict | None:
        return self.player.homes.get(prop.town_of(self.world, self.player.location))

    def home_ruined(self) -> bool:
        return self.place.type == "home" and bool((self.home_here() or {}).get("ruined"))

    def rebuild_cost(self) -> int:
        from engine import events
        town = prop.town_of(self.world, self.player.location)
        return round(P["homes"][town]["price"] * events.C["home"]["rebuild_share"])

    def show_home(self) -> None:
        town = prop.town_of(self.world, self.player.location)
        c = self.player.character
        here = self.home_here() if self.place.type == "home" else None
        ups = []
        if here:
            for uid, u in P["upgrades"].items():
                here_ok = not u.get("towns") or town in u["towns"]
                ups.append({"id": uid, "name": u["name"], "text": u["text"], "state": "built" if uid in here["upgrades"] else "far" if not here_ok else "price",
                            "price": money.short(u["price"])})
        if console.panel("home", {"owned": [{"town": self.world.places[t].name, "name": P["homes"][t]["name"], "day": hh["day"], "upgrades": [P["upgrades"][u]["name"] for u in hh["upgrades"] if u in P["upgrades"]], "ruined": bool(hh.get("ruined"))}
                                            for t, hh in self.player.homes.items()],
                                  "for_sale": {"name": P["homes"][town]["name"], "price": money.short(P["homes"][town]["price"])} if prop.for_sale(town) and town not in self.player.homes else None,
                                  "here": bool(here), "upgrades": ups, "purse": money.fmt(c.coins)}):
            return
        if self.player.homes:
            for t, h in self.player.homes.items():
                console.note(f"You own {P['homes'][t]['name']} in {self.world.places[t].name}"
                             + (f" - upgrades: {', '.join(h['upgrades'])}." if h["upgrades"] else "."))
        else:
            console.note("You own no property yet.")
        if prop.for_sale(town) and town not in self.player.homes:
            console.note(f"For sale here: {P['homes'][town]['name']} - {money.fmt(P['homes'][town]['price'])}. "
                         f"A land agent handles it; say 'buy a house'.")
        if self.place.type == "home":
            h = self.home_here()
            for uid, u in P["upgrades"].items():
                here_ok = not u.get("towns") or town in u["towns"]
                state = "built" if uid in h["upgrades"] else money.fmt(u["price"]) if here_ok else "far-lands houses only"
                console.note(f"  {u['name']} ({state}): {u['text']}")
            console.note("Say 'buy a garden' (or workshop, strongroom, hearth) to build one.")
        console.note(f"Your purse: {money.fmt(c.coins)}")

    def property_buy(self, intent, text: str) -> bool:
        """Handles buying a deed, or an upgrade when standing in your own home. True if it was a property purchase."""
        words = f"{intent.ware} {intent.item} {text}".lower()
        c = self.player.character
        if self.place.type == "home":
            if self.home_ruined():
                if not re.search(r"\b(rebuild|repair|restore|mend)\b", words):
                    console.note(f"Your house is a ruin. Say 'rebuild the house' ({money.fmt(self.rebuild_cost())}).")
                    self.halted = True
                    return True
                cost = self.rebuild_cost()
                if c.coins < cost:
                    console.note(f"Rebuilding costs {money.words(cost)}; you have {money.words(c.coins)}.")
                else:
                    c.coins -= cost
                    self.home_here()["ruined"] = False
                    self.ensure_homes()
                    self.store.save_player(self.player)
                    console.note(f"You pay {money.fmt(cost)} and the builders get to work. Your house stands again. "
                                 f"Purse: {money.fmt(c.coins)}")
                    self.narrate("The player pays builders to raise their ruined house again. Describe the new beams and the "
                                 "door hung back on its hinges in two sentences.", text)
                self.halted = True
                return True
            uid = prop.find_upgrade(words)
            if not uid:
                return False
            h = self.home_here()
            u = P["upgrades"][uid]
            town = prop.town_of(self.world, self.player.location)
            if uid in h["upgrades"]:
                console.note(f"You already have a {u['name']} here.")
            elif u.get("towns") and town not in u["towns"]:
                where = ", ".join(self.world.places[t].name for t in u["towns"] if t in self.world.places)
                console.note(f"No builder here can raise a {u['name']}. That work is done only in the far lands ({where}), "
                             f"and only on a house you own there.")
            elif c.coins < u["price"]:
                console.note(f"A {u['name']} costs {money.words(u['price'])}; you have {money.words(c.coins)}.")
            else:
                c.coins -= u["price"]
                h["upgrades"].append(uid)
                self.ensure_homes()
                self.store.save_player(self.player)
                console.note(f"You pay for a {u['name']}: {money.fmt(u['price'])}. Purse: {money.fmt(c.coins)}")
                self.narrate(f"The player pays builders and craftsmen {money.words(u['price'])} to add a {u['name']} to their "
                             f"house. {u['text']} Describe the work being finished in two sentences.", text)
                return True
            self.halted = True
            return True
        if not BUY_WORDS.search(words):
            return False
        town = prop.town_of(self.world, self.player.location)
        if not prop.for_sale(town):
            console.note("No houses are for sale here. Land is sold only in the far lands, to those who have earned a place there."
                         if town in P["homes"] else "No houses are for sale here.")
            self.halted = True
            return True
        agent = next((n for n in self.present if n.role == P["agent_role"]), None)
        if not agent:
            console.note("The land agent isn't here right now.")
            self.halted = True
            return True
        if town in self.player.homes:
            console.note("You already own a house here. Walk over to it to build.")
            self.halted = True
            return True
        h = P["homes"][town]
        if c.coins < h["price"]:
            console.note(f"{h['name'].capitalize()} costs {money.words(h['price'])}; you have {money.words(c.coins)}.")
            self.halted = True
            return True
        c.coins -= h["price"]
        self.player.homes[town] = {"day": clock.day(self.minutes), "upgrades": [], "last_garden": -1, "last_hearth": -1}
        self.ensure_homes()
        self.store.save_player(self.player)
        console.note(f"You buy {h['name']}: {money.fmt(h['price'])}. It is called 'your house in {self.world.places[town].name}' "
                     f"now; you can sleep there free, and keep your item box in it. Type #home.")
        self.weight_hint = "major"
        self.narrate(f"The player buys {h['name']} from {agent.label()} for {money.words(h['price'])} and is handed the key. "
                     "Describe the signing and the first look at the door in two or three sentences.", text)
        return True

    def home_arrival(self) -> None:
        """What a house gives when you walk in: garden herbs, a hot meal."""
        h = self.home_here()
        if self.place.type != "home" or not h or h.get("ruined"):
            return
        today = clock.day(self.minutes)
        if "garden" in h["upgrades"] and h.get("last_garden", -1) < today:
            grown = []
            lo, hi = P["garden_herbs"]
            herbs = [g for g in inv.GOODS.values() if g.kind == "herb"
                     and (not self.place.biome or self.place.biome in g.grows_in or not g.grows_in)] or \
                    [g for g in inv.GOODS.values() if g.kind == "herb"]
            if herbs:
                for _ in range(self.rng.randint(lo, hi)):
                    g = self.rng.choice(herbs)
                    self.to_pack(inv.make_good(g.id, 1))
                    grown.append(g.name)
                console.note("From the garden: " + ", ".join(grown) + ".")
            h["last_garden"] = today
        if ("hearth" in h["upgrades"] or "banquet_hall" in h["upgrades"]) and h.get("last_hearth", -1) < today:
            c = self.player.character
            share = max([P["hearth_restore"]] + [P["upgrades"][u].get("restore", 0) for u in h["upgrades"]])
            mana_share = max([0] + [P["upgrades"][u].get("restore_mana", 0) for u in h["upgrades"]])
            for pool, frac in (("stamina", share), ("health", share), ("mana", mana_share)):
                if frac:
                    top = pools.maximum(c, pool)
                    setattr(c, pool, min(top, pools.current(c, pool) + top * frac))
            console.note("A hot meal at your own hearth restores you.")
            h["last_hearth"] = today
        self.store.save_player(self.player)
