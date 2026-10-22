"""How the world learns what the player did (f330): the subscribers to the deeds the scenes publish.

Every deed of the player's that the world could notice is published once, as a typed event (engine/domain_events.py, the Deed family),
by the scene that saw it happen. This module subscribes what the world does about it, from the entry for its kind in
data/rules/reactions.yaml: who remembers it and how hard (and what it costs them in trust), what it does to standing, reputation and
heat, which companions have a view on it, and whether it goes into the deeds ledger that ends events (engine/deeds.py, run through
events.after_deed). The words people remember are the event's own (its victim's line, its witnesses' line): only the event knows what
it was. What a deed does is data; a new way for the world to notice something is a line in the table and one publish() call.

Bound to the scene (register(ws)). People are reached through ws.npc_by_id, which hands back the scene's own held copy of anyone standing
here: the scene saves those at the end of the turn, and a second copy loaded from the store would be overwritten by that save. Hires are
reached through ws.player.party. The adapters validate and skip (a kind with no entry, a town that is no place, a deed in a lawless place,
a person who is gone) and never swallow: a bug in a reaction stops the turn, as the bus promises. Tools that run without a scene publish
into silence; nothing is registered there."""
from __future__ import annotations

from pathlib import Path

import yaml

from engine import domain_events as de
from ui import console

R = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "reactions.yaml").read_text(encoding="utf-8"))
KINDS: dict[str, dict] = {k: (v or {}) for k, v in R["kinds"].items()}
AFTER_DEED = ("kill", "persuade", "deliver", "quest_done", "dungeon_cleared", "found", "defend")     # the ledger kinds that can end an event

_OFF: list = []                  # how to unsubscribe what is registered now (one scene at a time: a new game, a test's fresh scene)


def register(ws) -> None:
    """Subscribe the world's reactions, bound to this scene. Registering again (another scene) replaces the earlier binding."""
    unregister()
    rx = Reactions(ws)
    for fn in (rx.ledger, rx.memories, rx.standing, rx.reputation, rx.heat, rx.hires):
        _OFF.append(de.subscribe(de.Deed, fn))


def unregister() -> None:
    for off in _OFF:
        off()
    _OFF.clear()


def rule(kind: str) -> dict:
    return KINDS.get(kind) or {}


def _flagged(table, e) -> list:
    """A table's values whose flag (an attribute of the event) holds: {inn: inn, late: sleep_late} on a Rested deed."""
    if isinstance(table, str):
        return [table]
    return [v for flag, v in (table or {}).items() if getattr(e, flag, False)]


class Reactions:
    def __init__(self, ws):
        self.ws = ws

    # ---- where and when

    def town(self, e: de.Deed) -> str:
        from engine import pulse
        return pulse.town_of(self.ws.world, e.place or self.ws.player.location)

    def lawless(self, e: de.Deed) -> bool:
        """No law and no standing here: the scene's own rule for where the player stands (scenes/law_actions.py), the map's for elsewhere."""
        if not e.place or e.place == self.ws.player.location:
            return bool(self.ws.lawless_here())
        town = self.town(e)
        return town not in self.ws.world.places or bool(self.ws.world.places[town].danger)

    def day(self, e: de.Deed) -> int:
        from engine import clock
        return clock.day(e.minute)

    def people(self, ids) -> list:
        return [n for n in (self.ws.npc_by_id(i) for i in ids) if n is not None and not n.gone]

    # ---- the deeds ledger: what can end an event

    def ledger(self, e: de.Deed) -> None:
        if not rule(e.kind).get("ledger"):
            return
        row = e.ledger_row()
        if not row:
            return
        from engine import deeds, events
        row = dict(row)
        deed = deeds.log(self.ws.store, row.pop("kind"), e.minute, e.place or self.ws.player.location, **row)
        if deed["kind"] in AFTER_DEED:
            events.after_deed(self.ws, deed)

    # ---- who remembers

    def memories(self, e: de.Deed) -> None:
        m = rule(e.kind).get("memory")
        if not m:
            return
        day, turn = self.day(e), self.ws.store.meta.turn
        for nid in e.witnesses:
            role = "victim" if nid == e.target else "witness"
            spec = m.get(role)
            if not spec:
                continue
            line = e.victim_line() if role == "victim" else e.witness_line()
            if line:
                self.remember(nid, line, spec, day, turn)
        if e.target and e.target not in e.witnesses and m.get("unseen_victim"):
            line = e.unseen_line()
            if line:
                self.remember(e.target, line, m["unseen_victim"], day, turn)

    def remember(self, nid: str, text: str, spec: dict, day: int, turn: int) -> None:
        from npc.models import Memory
        n = self.ws.npc_by_id(nid)
        if n is None or n.gone:
            return
        n.memories.append(Memory(importance=int(spec.get("importance", 1)), day=day, turn=turn, text=text))
        if spec.get("trust"):
            n.trust = max(0, min(100, n.trust + int(spec["trust"])))
        self.ws.store.save_npc(n)

    # ---- standing: the tale starts on its way

    def standing(self, e: de.Deed) -> None:
        s = rule(e.kind).get("standing")
        if not s:
            return
        if s.get("only") and not getattr(e, s["only"], False):
            return
        from engine import standing as st
        kind = s["kind"]
        if kind not in st.DEEDS or self.lawless(e):
            return
        weight = self.weight(s.get("weight"), e)
        if weight <= 0:
            return
        from engine import clock
        ws = self.ws
        place = ws.world.places.get(e.place or ws.player.location)
        entry = st.report(ws.store, ws.world, ws.player, kind, self.town(e), place.name if place else "", ws.player.character.name,
                          e.minute, clock.day(e.minute), self.people(e.witnesses), e.item_label(), weight, seed=ws.store.meta.seed)
        if entry:
            console.debug(f"standing: {kind} in {self.town(e)} -> {st.standings(ws.player, self.town(e), clock.day(e.minute))}"
                          f"{' (told twisted)' if entry['deed']['twisted'] else ''}")

    def weight(self, how, e: de.Deed) -> float:
        if how == "story_or_valuable":
            from engine import law
            return 1.5 if getattr(e, "story", False) or getattr(e, "value", 0) > law.H["valuable_over"] else 1.0
        if how == "event":
            return float(getattr(e, "weight", 0.0))
        return 1.0

    # ---- reputation: the town's regard

    def reputation(self, e: de.Deed) -> None:
        r = rule(e.kind).get("reputation")
        for key in _flagged(r, e):
            self.ws.reputation_change(key, e.place or None)

    # ---- heat: how wanted it makes them

    def heat(self, e: de.Deed) -> None:
        h = rule(e.kind).get("heat")
        if not h or self.lawless(e):
            return
        from engine import law
        H = law.H
        gain = 0.0
        if "event" in h:
            gain = float(getattr(e, "heat", 0.0))
        elif not e.witnesses:
            return                                        # nobody saw: the watch never hears of it
        else:
            people = self.people(e.witnesses)
            victim = any(n.id == e.target for n in people)
            guard = any(n.role in H["guard_roles"] for n in people)
            if "offense" in h:
                gain = law.offense_heat(h["offense"], getattr(e, "value", 0), getattr(e, "story", False), only_passersby=not (victim or guard))
            elif "gain" in h:
                gain = H["gain"][h["gain"]] * (H["passerby_share"] if not (victim or guard) else 1)
        if not gain:
            return
        heat = law.add_heat(self.ws.player, self.town(e), gain, self.day(e))
        console.debug(f"offense: {e.kind}, heat +{gain:.0f} -> {heat} in {self.town(e)}")

    # ---- the companions' view

    def hires(self, e: de.Deed) -> None:
        for deed in _flagged(rule(e.kind).get("hire"), e):
            self.ws.deed(deed)
