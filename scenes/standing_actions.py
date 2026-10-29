"""Standing and rumors in the scene: deeds the world saw become news and move how the groups of a town regard the player;
#standing shows it as words, #rumors what is being said, #correct sets a false tale straight. Rules: engine/standing.py."""
from __future__ import annotations

from engine import checks, clock, pulse, standing
from ui import console

GROUP_NAMES = {"guards": "the watch", "guild": "the guild", "merchants": "the merchants", "outlaws": "the outlaws",
               "temple": "the temple", "nobility": "the nobles", "mages": "the mages"}


class StandingActions:
    def standing_town(self) -> str:
        return pulse.town_of(self.world, self.player.location)

    def standing_report(self, kind: str, witnesses: list | None = None, item: str = "", weight: float = 1.0) -> None:
        """A deed the world saw (or a public one). Quietly moves standing here and starts the tale on its way."""
        town = self.standing_town()
        entry = standing.report(self.store, self.world, self.player, kind, town, self.world.places[self.player.location].name,
                                self.player.character.name, self.minutes, clock.day(self.minutes), witnesses, item, weight,
                                seed=self.store.meta.seed)
        if entry:
            console.debug(f"standing: {kind} in {town} -> {standing.standings(self.player, town, clock.day(self.minutes))}"
                          f"{' (told twisted)' if entry['deed']['twisted'] else ''}")

    def standing_arrive(self) -> None:
        """Arriving in a town: tales that have reached it since the last visit land, and the groups with strong feelings let you know."""
        town, day = self.standing_town(), clock.day(self.minutes)
        landed = standing.arrivals(self.store, self.world, self.player, town, self.minutes, day)
        if landed:
            console.debug(f"standing: news arrived in {town}: " + ", ".join(f"{g} {d:+.1f}" for g, d in landed))
        for group, v in standing.strongest(self.player, town, day):
            who = GROUP_NAMES[group]
            console.note(f"{who.capitalize()} here {'think well of you' if v > 0 else 'do not think well of you'} ({standing.word(v)}).")

    def standing_price(self) -> float:
        return standing.price_factor(self.player, self.standing_town(), clock.day(self.minutes))

    def standing_trust(self, npc) -> int:
        return standing.trust_shift(self.player, self.standing_town(), npc.knowledge_groups, clock.day(self.minutes))

    def standing_line(self, npc) -> str:
        """For a person's prompt: how their own groups regard the stranger."""
        town, day = self.standing_town(), clock.day(self.minutes)
        parts = [f"{GROUP_NAMES[g]} regard the stranger as {standing.word(standing.value(self.player, town, g, day))}"
                 for g in npc.knowledge_groups if g in standing.GROUPS and abs(standing.value(self.player, town, g, day)) >= 10]
        return ("Among the groups you belong to: " + "; ".join(parts) + ". Let it colour how warm or guarded you are.") if parts else ""

    # ---------- commands ----------

    def standing_data(self) -> dict:
        """(f327) The window's Standing pane: this town's regard and its groups, what is said of you here, the other towns, your titles."""
        town, day = self.standing_town(), clock.day(self.minutes)
        wild = bool(self.world.places[town].danger)
        groups = [] if wild else [{"name": GROUP_NAMES[g].capitalize(), "value": standing.value(self.player, town, g, day), "word": w}
                                  for g, w in standing.standings(self.player, town, day)]
        rumors = [] if wild else [{"n": n, "text": e["text"], "twisted": bool(e.get("deed", {}).get("twisted"))} for n, e in enumerate(self.rumor_items(), 1)]
        elsewhere = [{"name": self.world.places[t].name, "value": r, "word": self.reputation_words(t)}
                     for t, r in sorted(self.player.reputation.items(), key=lambda x: -abs(x[1]))
                     if t != town and t in self.world.places and self.world.places[t].type in ("town", "city", "village") and abs(r) >= 5]
        return {"wild": wild, "town": self.world.places[town].name, "value": self.player.reputation.get(town, 0), "word": self.reputation_words(town),
                "groups": groups, "rumors": rumors, "elsewhere": elsewhere, "titles": list(self.player.titles)}

    def show_standing(self) -> None:
        if console.panel("standing", self.standing_data()):
            return
        town, day = self.standing_town(), clock.day(self.minutes)
        name = self.world.places[town].name
        if self.world.places[town].danger:
            console.note("Nobody out here keeps a tally of you.")
            return
        console.note(f"In {name}, townsfolk regard you as: {self.reputation_words(town)}.")
        rows = standing.standings(self.player, town, day)
        if not rows:
            console.note("No group here has formed an opinion of you.")
            return
        for group, w in rows:
            console.note(f"  {GROUP_NAMES[group].capitalize()}: {w}")

    def rumor_items(self) -> list[dict]:
        return standing.about_you(self.store, self.world, self.standing_town(), self.minutes)[:6]

    def show_rumors(self) -> None:
        town = self.standing_town()
        mine = self.rumor_items()
        if mine:
            console.note(f"What is being said about you in {self.world.places[town].name}:")
            for n, e in enumerate(mine, 1):
                console.note(f"  {n}. {e['text']}")
            console.note("If a tale is wrong, #correct <number> tries to set it straight.")
        else:
            console.note("Nobody here is talking about you.")
        here = type("Listener", (), {"knowledge_groups": [g for g in [self.world.locals_group(self.player.location)] if g], "location": self.player.location})()
        world_news = [t for t in pulse.news_for(self.store, self.world, here, self.minutes, 8) if t not in {e["text"] for e in mine}][:3]
        if world_news:
            console.note("And other talk around town:")
            for t in world_news:
                console.note(f"  - {t}")

    def correct_rumor(self, args: str) -> None:
        self._correct_rumor(args)
        if console.windowed():
            with console.scope("#standing"):                     # (f327) the pane's Correct button: the pane is drawn again
                self.show_standing()

    def _correct_rumor(self, args: str) -> None:
        mine = self.rumor_items()
        if not args.strip().isdigit() or not 1 <= int(args) <= len(mine):
            console.note("Which tale? Type #rumors for the list, then #correct <number>.")
            return
        entry = mine[int(args) - 1]
        deed = entry["deed"]
        listeners = [n for n in self.present if n.role not in ("guard",)] or self.present
        if not listeners:
            console.note("There is nobody here to tell.")
            return
        self.advance(standing.S["spread"]["correct_minutes"])
        odds = checks.chance(self.player.character, "persuasion", self.conditions(), npc=listeners[0])[0]
        degree, _ = checks.roll(odds, c=self.player.character)
        if not deed["twisted"]:
            console.note("Those who tell it have it right. There is nothing to correct.")
            return
        if degree in ("strong success", "success"):
            standing.correct(self.store, self.player, deed["id"], self.minutes)
            self.narrate("The player takes the time to set a false tale about themselves straight, and it is believed.", "")      # (f384) no length
            console.note("You set the record straight. The tale is told true from now on.")
        else:
            console.note("You argue your case, but the tale has a life of its own. Nobody is convinced.")
