"""Mounts: buying one at a city stable, and choosing which one to ride."""

from engine import crafting, money, mounts, pulse
from ui import console


class MountActions:

    def stable_stock(self) -> list[tuple[dict, int]]:
        """(mount, price) for every mount the stable here has, or [] outside a city."""
        town = mounts.stable_town(self.world, self.player.location)
        if not town:
            return []
        off = crafting.mechanic(self.player.character, "haggler") + self.guild_perks()["shop_discount"]
        factor = max(0, 1 - off / 100) * pulse.price_factor(self.store, self.world, self.player.location, self.minutes)
        return [(m, round(m["price"] * factor)) for m in mounts.stock(self.world, self.store.meta.seed, town)]

    def show_stable(self) -> None:
        offers = self.stable_stock()
        if not offers:
            return
        c = self.player.character
        console.note("The stable here:")
        for m, price in offers:
            owned = any(x["id"] == m["id"] for x in self.player.mounts)
            need = f", needs level {m['min_level']}" if m["min_level"] > 1 else ""
            console.note(f"  {m['name']} - {money.fmt(price)} (journeys {round(m['speed'] * 100)}% shorter, "
                         f"{round(m['stamina'] * 100)}% less wearying{need})" + (" - you own one" if owned else ""))
        console.note("Say 'buy the courser' (or whichever you want). Your purse: " + money.fmt(c.coins))

    def show_mounts(self) -> None:
        """#mount: the mounts you own and the one you ride; and the stable if you are in a city."""
        if not self.player.mounts:
            console.note("You own no mount.")
        else:
            for m in self.player.mounts:
                on = " (riding)" if m["id"] == self.player.mount else ""
                console.note(f"  {m['name']}{on}: journeys {round(m['speed'] * 100)}% shorter, {round(m['stamina'] * 100)}% less wearying")
            if not self.player.mount:
                console.note("You are going on foot.")
            console.note("Say #mount followed by a name to ride it, or #mount none to go on foot.")
        self.show_stable()

    def mount_command(self, arg: str) -> None:
        arg = arg.strip().lower()
        if not arg:
            self.show_mounts()
            return
        if arg in ("none", "walk", "foot", "off", "dismount"):
            mounts.ride(self.player, "")
            self.store.save_player(self.player)
            console.note("You go on foot.")
            return
        pick = mounts.find(self.player.mounts, arg)
        if not pick:
            console.note("You don't own a mount like that." if self.player.mounts else "You own no mount.")
            return
        mounts.ride(self.player, pick["id"])
        self.store.save_player(self.player)
        console.note(f"You will ride {pick['name']}.")

    def mount_buy(self, intent, text: str) -> bool:
        """Buying a mount at a city stable. True if the purchase was about a mount."""
        words = f"{intent.ware} {intent.item} {text}".lower()
        offers = self.stable_stock()
        town = mounts.stable_town(self.world, self.player.location)
        everything = list(mounts.CATALOG.values())
        named = mounts.find([m for m, _ in offers], words)
        if not named and not mounts.WORDS.search(f"{intent.ware} {intent.item}"):
            return False
        if not town:
            if mounts.find(everything, words) or mounts.WORDS.search(f"{intent.ware} {intent.item}"):
                self.refuse("Mounts are sold at the stables of the great cities.")
                return True
            return False
        self.halted = True
        if not named:
            wanted = mounts.find(everything, words)
            if wanted:
                console.note(f"The stable here has no {wanted['name'].split(' ', 1)[-1]} for sale.")
            self.show_stable()
            return True
        mount, price = next((m, p) for m, p in offers if m["id"] == named["id"])
        c = self.player.character
        result = mounts.buy(self.player, c, mount, price)
        if result == "short":
            console.note(f"{mount['name'].capitalize()} costs {money.words(price)}; you have {money.words(c.coins)}.")
        elif result:
            console.note(result)
        else:
            self.store.save_player(self.player)
            console.note(f"You pay {money.fmt(price)} and lead away {mount['name']}. "
                         f"{'You ride it now. ' if self.player.mount == mount['id'] else 'Say #mount to choose which you ride. '}"
                         f"Purse: {money.fmt(c.coins)}")
            self.narrate(f"The player pays {money.words(price)} to a stablemaster for {mount['name']} and takes the reins. "
                         "Describe the animal and the first moments in the saddle.", text)
            self.halted = False
        return True
