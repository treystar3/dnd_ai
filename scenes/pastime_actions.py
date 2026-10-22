"""Pastimes (f332): praying, gambling and haggling as actions of their own - three things players kept typing that the interpreter could
only file under `other` (an improvisation with a roll and a mark) or turn into talk. Each is now a kind in engine/actions.py with a handler
here, a rule in data/rules/pastimes.yaml, and a deed the world notices (engine/domain_events.py Prayed, Gambled; a haggle that lands is a
Traded like any purchase).

Haggle is the one that cuts across another system: a buy with a persuasion check first. engine/checks run as `checks` on an intent turn a
social check into talk (scenes/check_actions.py run_checks); haggle rolls the check itself and then buys, so bargaining ends with a price."""
from __future__ import annotations

from pathlib import Path

import yaml

from engine import checks, clock, money
from ui import console

ROOT = Path(__file__).resolve().parent.parent
PT = yaml.safe_load((ROOT / "data" / "rules" / "pastimes.yaml").read_text(encoding="utf-8"))


class PastimeActions:
    haggle_factor = 1.0                 # (f332) the price a haggle won, read by the quoting (scenes/shop_actions.py quote_ware) for one purchase

    # ---------- pray

    def on_pray(self, intent, text: str) -> None:
        """A prayer or a small rite, at a temple or anywhere: the faith of the place colours it, the priest hears it, the companions see it."""
        from engine import faith
        from engine.domain_events import Prayed
        P = PT["pray"]
        at_temple = self.place.type in P["temple_types"]
        god = faith.god_of(self.world, self.player.location)
        priest = next((n for n in self.present if n.role in ("priest", "acolyte", "water_priest")), None)
        self.advance(P["minutes"])
        self.notice(Prayed(minute=self.minutes, place=self.player.location, witnesses=tuple(n.id for n in self.present),
                           npc=priest.id if priest else "", name=priest.label() if priest else "", god=god["name"] if god else "", temple=at_temple),
                    *([priest] if priest else []))
        self.store.save_player(self.player)
        where = f"at {self.place.name}" + (", before its altar" if at_temple else "")
        tone = (f" The faith here is {god['name']}: it cares for {god['cares']}; its faithful reach for {god['imagery']}; in daily life, {god['habits']}."
                if god else " No god is named here; the prayer is the player's own.")
        self.weight_hint = "rich"
        self.narrate(f"THE PLAYER PRAYS {where}: {intent.summary or text}.{tone} Show it as it would be seen - the posture, the quiet, what the "
                     f"place does around them" + (f"; {priest.label()} notices and lets them be" if priest else "") + ". Nobody answers from on high; "
                     "nothing is gained but the moment. Two or three sentences.", text)

    # ---------- gamble

    def on_gamble(self, intent, text: str) -> None:
        """Dice or cards with whoever will play: a stake, a roll with the house's edge and a little wit, coin won or lost, and a word that goes round."""
        from engine.domain_events import Gambled
        G = PT["gamble"]
        c = self.player.character
        who = next((n for n in self.present if n.id == intent.target), None) or next((n for n in self.present if n.role in G["roles"]), None)
        if who is None:
            console.note("Nobody here will play.")
            self.halted = True
            return
        stake = self.coin_amount(intent.item or "") or self.coin_amount(text) or G["default_stake"]
        stake = min(stake, int(c.coins * G["max_share"]))
        if stake <= 0:
            console.note(f"You have nothing to stake. Purse: {money.fmt(c.coins)}")
            self.halted = True
            return
        odds = G["odds"] + (c.attributes.wisdom - checks.RULES["attribute_center"]) * G["insight_weight"]
        degree, rolled = checks.roll(max(checks.RULES["min"], min(checks.RULES["max"], odds)), self.rng, c=c)
        console.debug(f"gamble: {odds:.0f}% - rolled {rolled}: {degree}; stake {stake}")
        won = round(stake * G["payout"][degree])
        c.coins = max(0, c.coins + won)
        self.advance(G["minutes"])
        self.notice(Gambled(minute=self.minutes, place=self.player.location, witnesses=(who.id,), npc=who.id, name=who.label(), amount=stake, won=won), who)
        self.store.save_player(self.player)
        console.ledger((f"Won {money.fmt(won)}" if won > 0 else f"Lost {money.fmt(-won)}" if won < 0 else "Broke even") + f" at {money.fmt(stake)} a throw. Purse: {money.fmt(c.coins)}")
        outcome = ("WINS, and well" if degree == "strong success" else "WINS" if won > 0 else "LOSES the stake" if won < 0 else "comes out even")
        self.narrate(f"THE GAME HAS DECIDED: the player gambles {money.words(stake)} with {who.label()} ({intent.summary or text}) and {outcome}. "
                     "Show the play as it would be seen - hands, dice or cards, the faces round the table - and the coin changing hands. "
                     "Nothing else is won or lost. Two or three sentences.", text)

    # ---------- haggle

    def on_haggle(self, intent, text: str) -> None:
        """Bargaining before a purchase: a persuasion check against the seller; a landing one buys at the price it won, a failing one buys nothing
        and the seller thinks a little less of the stranger."""
        H = PT["haggle"]
        sellers = [n for n in self.present if self.world.roles[n.role].sells or self.world.roles[n.role].stock]
        seller = next((n for n in sellers if n.id == intent.target), None) or (sellers[0] if sellers else None)
        if seller is None:
            console.note("No one here is selling anything.")
            self.halted = True
            return
        if seller.tier == "background":
            from npc.life import promote
            promote(seller, self.store, self.world, self.catalog)
        degree = self.resolve("persuasion", seller, talking=False, text=text)
        self.last_social = ("persuasion", degree, seller.id)
        factor = H["discount"].get(degree)
        if factor is None:
            seller.trust = max(0, seller.trust + H["annoyed_trust"])
            self.advance(clock.TALK_MINUTES)
            self.narrate(f"THE GAME HAS DECIDED: the player tries to beat {seller.label()} down on a price ({intent.summary or text}) and gets nowhere: "
                         "the price stands and the seller is a little cooler for being asked. Show the exchange briefly; nothing is bought.", text)
            return
        self.haggle_factor = factor
        try:
            console.note(f"{seller.label()} comes down {round((1 - factor) * 100)}%.")
            intent.target = seller.id
            self.on_buy(intent, text)
        finally:
            self.haggle_factor = 1.0
