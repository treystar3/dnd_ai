"""The party's mechanics in one place: who joins, who leaves, who is promoted, who goes down and whether they get up. The service changes
the player's record (party, coins, party_used, party_mode), applies the rules (engine.party) and publishes a typed event
(engine.domain_events) for each change; it writes nothing to the console and asks the model nothing. The scene (scenes/party_actions.py,
scenes/combat_scene.py) reads the player's words, calls the service, and tells the story of what came back.

Why: before this, hiring lived in one scene method, dismissing in another, dying in the combat scene and in the after-fight pass, each
with its own journal line and its own bookkeeping; a new rule about leaving the party had three places to be wrong in. Now a change to
what joining or dying means is made here, and whoever needs to know (the journal, the tests, later the director) subscribes to the event.

The service holds no state of its own: everything it changes is on the player's record, which the store saves at the end of the turn."""
from __future__ import annotations

import random
from typing import Callable

from engine import party as rules
from engine.domain_events import (MemberCarried, MemberDied, MemberJoined, MemberLeft, MemberPromoted, PartyModeChanged, publish)
from engine.party import P


class CannotAfford(Exception):
    def __init__(self, name: str, fee: int):
        super().__init__(f"{name} wants {fee} and the player cannot cover it")
        self.name, self.fee = name, fee


class PartyFull(Exception):
    pass


class PartyService:
    def __init__(self, player, now: Callable[[], int], seed: str | int = ""):
        self.player = player
        self.now = now                       # the game's minute, read when a change is made
        self.seed = seed

    # ---- reading

    @property
    def members(self) -> list[dict]:
        return self.player.party

    def hires(self) -> list[dict]:
        """The hired adventurers (not story companions, not Maren)."""
        return [m for m in self.player.party if m.get("permanent") and not m.get("story") and not m.get("npc") and not m.get("tutorial")]

    def is_full(self) -> bool:
        return len(self.player.party) >= P["max_party"]

    def find(self, member_id: str) -> dict | None:
        return next((m for m in self.player.party if str(m.get("id")) == str(member_id)), None)

    # ---- joining

    def hire(self, offer: dict, player_level: int) -> dict:
        """Take a roster offer into the party for its fee. Raises PartyFull or CannotAfford; returns the new member."""
        if self.is_full():
            raise PartyFull(P["max_party"])
        c = self.player.character
        if c.coins < offer["fee"]:
            raise CannotAfford(offer["name"], offer["fee"])
        c.coins -= offer["fee"]
        minute = self.now()
        member = rules.new_hire(offer, player_level, minute // 1440)
        from engine import quirks
        quirks.roll(member, random.Random(f"{self.seed}:{member['id']}"), self.player.owned)
        self.player.party.append(member)
        if offer.get("hall"):
            self.player.party_used.append(f"{offer['hall']}:{offer['id']}")
            self.player.party_used = self.player.party_used[-80:]
        publish(MemberJoined(minute=minute, member_id=member["id"], name=member["name"], role=member["role"], fee=offer["fee"]))
        return member

    def join(self, member: dict, how: str = "companion") -> dict:
        """Someone who joins without a fee: an npc companion for a thread, or a story member. The record is the caller's (it knows
        the thread); the service only adds it and says so."""
        if self.find(member["id"]) is None:
            self.player.party.append(member)
        publish(MemberJoined(minute=self.now(), member_id=member["id"], name=member["name"], role=member.get("role", ""), fee=0, how=how))
        return member

    # ---- leaving

    def dismiss(self, members: list[dict], how: str = "dismissed") -> list[dict]:
        """Remove these members; those who stay remember it. Returns who left."""
        gone = [m for m in members if m in self.player.party]
        if not gone:
            return []
        minute = self.now()
        for m in gone:
            self.player.party.remove(m)
            publish(MemberLeft(minute=minute, member_id=m["id"], name=m["name"], how=how))
        if how == "dismissed":
            for m in self.player.party:
                if m.get("permanent"):
                    rules.remember(m, minute // 1440, "They sent " + ", ".join(g["name"] for g in gone) + " away.", 2)
        if not self.player.party:
            self.player.party_mode = "with"
        return gone

    def disband(self, arc_id: str | None, why: str) -> list[dict]:
        """A thread's companions take their leave when it ends; the hires stay."""
        gone = [m for m in self.player.party if not (m.get("permanent") or (arc_id is not None and m.get("arc") != arc_id))]
        return self.dismiss(gone, how="disbanded") if gone else []

    # ---- going down

    def decide_down(self, member: dict, rng: random.Random, in_fight: bool = True) -> str:
        """A hire has gone down in a fight: dead, or carried out alive. Decided once (kept on them as down_fate until the fight is over,
        so the narration and the after-fight pass agree) and published at once, so those who saw it can react now. Returns the fate."""
        if member.get("down_fate"):
            return member["down_fate"]
        dead = rng.random() < P["death_when_down"]
        member["down_fate"] = "dead" if dead else "carried"
        minute = self.now()
        if dead:
            publish(MemberDied(minute=minute, member_id=member["id"], name=member["name"], how="fight", in_fight=in_fight))
        else:
            publish(MemberCarried(minute=minute, member_id=member["id"], name=member["name"]))
        return member["down_fate"]

    def kill(self, member: dict, how: str = "fight", in_fight: bool = False) -> None:
        """A member dies outright (no fate to decide: an old-style hireling who went down, a death outside a fight) and leaves the party."""
        publish(MemberDied(minute=self.now(), member_id=member["id"], name=member["name"], how=how, in_fight=in_fight))
        self.bury(member)

    def bury(self, member: dict) -> None:
        """A member whose fate was death leaves the party. (The death itself was published when it was decided.)"""
        if member in self.player.party:
            self.player.party.remove(member)
        member.pop("down_fate", None)
        if not self.player.party:
            self.player.party_mode = "with"

    # ---- standing

    def promote(self, member: dict, player_level: int) -> tuple[str, str, int]:
        """Pay to raise a hire a rank. Raises CannotAfford; the caller checks rules.promotion_block first. Returns (old, new, fee)."""
        fee = rules.promotion_fee(member)
        c = self.player.character
        if c.coins < fee:
            raise CannotAfford(member["name"], fee)
        c.coins -= fee
        old = member.get("rank") or rules.rank_of(member["level"])
        minute = self.now()
        rules.promote(member, player_level)
        from engine import money
        rules.remember(member, minute // 1440, f"They paid {money.words(fee)} to have me raised to {member['rank']}-rank.", 3)
        rules.set_mood(member, "pleased, standing a little taller, since their promotion", minute)
        member["impression"] = "Thinks the player backs their people with coin, not only words."
        publish(MemberPromoted(minute=minute, member_id=member["id"], name=member["name"], old_rank=old, new_rank=member["rank"], fee=fee))
        return old, member["rank"], fee

    def set_mode(self, mode: str) -> bool:
        """'with' or 'hold'. Returns False when there is no party to direct."""
        if not self.player.party:
            return False
        if self.player.party_mode != mode:
            self.player.party_mode = mode
            publish(PartyModeChanged(minute=self.now(), mode=mode))
        return True
