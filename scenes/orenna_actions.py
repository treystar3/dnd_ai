"""The quest Orenna in play: the trigger, the contact, the ruin, the order, the three trails, the Executioner, the High Keeper
and the blessing. The rules and the state are in engine/orenna.py; every word shown is fixed in data/world/orenna.yaml."""
import re

from core.models import KeyItem
from engine import clock, combat, orenna
from ui import console

O = orenna.O
SETTLED = ("town", "city", "village")


class OrennaActions:

    # ---------- small helpers ----------

    def orenna_say(self, speaker: str, lines) -> None:
        for line in ([lines] if isinstance(lines, str) else lines):
            console.say(line, speaker)

    def orenna_lore(self, fact: str) -> None:
        known = self.player.character.knowledge
        if fact not in known:
            known.append(fact)

    def orenna_city(self, slot) -> str:
        return self.world.places[slot].name

    def orenna_settled(self) -> bool:
        p = self.world.places.get(self.player.location)
        return bool(p) and p.type in SETTLED and not p.danger and not self.combat and not self.player.delve

    # ---------- the trigger ----------

    def orenna_named(self, speech: str) -> None:
        """Called whenever the player speaks to someone. At level 50, saying her name starts the quest - it waits for the player
        to say it; nothing is ever offered unprompted."""
        if not orenna.name_said(speech) or not orenna.can_start(self.player):
            return
        cities = orenna.pick_cities(self.world, self.store.meta.seed)
        self.player.orenna.update(stage="named", due=orenna.due_minutes(self.minutes, self.store.meta.seed), evidence=0.0,
                                  meeting=cities["meeting"], trails=cities["trails"], trails_done=[], executioner=False)
        self.store.save_player(self.player)
        console.debug("orenna: the name was said; the contact will come")

    def orenna_tick(self) -> None:
        """After every action: has the next step of the quest come due?"""
        st = orenna.stage(self.player)
        if not st or st == "done" or self.combat:
            return
        if st == "leaving":
            self.orenna_leave()
            return
        o = self.player.orenna
        here = self.player.location
        if st in ("named", "contact") and self.minutes >= o.get("due", 0) and self.orenna_settled():
            self.orenna_contact()
        elif st == "order" and here == o["meeting"] and self.orenna_settled():
            self.orenna_order()
        elif st == "trails" and self.orenna_settled():
            for i, city in enumerate(o["trails"]):
                if city == here and i not in o["trails_done"]:
                    self.orenna_trail(i)
                    break
        elif st == "registry" and here == O["keeper_city"] and self.orenna_settled():
            self.orenna_registry()
        elif st == "confront" and here == O["keeper_city"] and self.orenna_settled() and self.minutes >= o.get("retry", 0):
            self.orenna_confront()

    # ---------- the contact and the ruin ----------

    def orenna_contact(self) -> None:
        C = O["contact"]
        name = O["contact_name"]
        orenna.set_stage(self.player, "contact")
        console.narrate(C["arrive"].strip())
        console.say(C["ask"], "The stranger")
        console.ask()
        console.narrate(C["after"].strip())
        self.orenna_say(name, C["speech"])
        console.note("Go with them to the ruin? (y/n)")
        if console.ask().lower() not in ("y", "yes"):
            console.say(C["decline"], name)
            self.player.orenna["due"] = self.minutes + 24 * 60
            self.store.save_player(self.player)
            return
        console.say(C["go"], name)
        d = orenna.ruin_dungeon(self.world, self.player.character.level, self.minutes, self.store.meta.seed)
        known = [x for x in self.store.load_dungeons() if x["id"] != d["id"]]
        self.store.save_dungeons(known + [d])
        self.ensure_dungeons()
        self.advance(C["travel_minutes"])
        self.player.delve = None
        orenna.set_stage(self.player, "ruin")
        self.enter(d["entrance"])
        self.store.save_player(self.player)
        console.note(f"{name} brings you to {d['name']}. Go down when you are ready.")
        self.show_exits()

    def orenna_floor_done(self, d: dict, f: int) -> None:
        R = O["ruin"]
        spec = R["floors"][f]
        console.ledger(f"Floor {f + 1} cleared: {spec['title']}.")
        console.narrate(spec["mural"].strip())
        self.orenna_lore(spec["lore"])
        if f + 1 < len(d["floors"]):
            console.note(f"Stairs lead down to floor {f + 2}.")
            return
        self.orenna_say(O["contact_name"], R["after_speech"])
        o = self.player.orenna
        city = self.orenna_city(o["meeting"])
        console.say(R["to_order"].format(city=city), O["contact_name"])
        self.give_order_coin()
        console.note(R["coin_given"])
        orenna.set_stage(self.player, "leaving")

    def orenna_leave(self) -> None:
        """Odrin leads the player out by a hidden road, so the walk back from a place no ordinary traveller could survive is not the player's to make."""
        o = self.player.orenna
        self.player.delve = None
        self.advance(O["contact"]["travel_minutes"])
        orenna.set_stage(self.player, "order")
        self.enter(o["meeting"])
        console.note(f"{O['contact_name']} leads you out by a road you could not have found alone, and you arrive in {self.orenna_city(o['meeting'])}.")
        self.store.save_player(self.player)
        self.orenna_order()

    def give_order_coin(self) -> None:
        c = self.player.character
        coin = O["coin"]
        if not any(k.id == coin["id"] for k in c.key_items):
            c.key_items.append(KeyItem(id=coin["id"], name=coin["name"], description=coin["description"], kind="key",
                                       source=O["contact_name"], day=clock.day(self.minutes)))

    # ---------- the order and the three trails ----------

    def orenna_order(self) -> None:
        S = O["order"]
        o = self.player.orenna
        console.narrate(S["arrive"].strip())
        self.orenna_say("The eldest", S["speech"][:2])
        console.say(S["speech"][2], "The eldest")
        t1, t2, t3 = (self.orenna_city(c) for c in o["trails"])
        console.note(S["task"].format(t1=t1, t2=t2, t3=t3))
        self.orenna_lore(S["lore"])
        orenna.set_stage(self.player, "trails")
        self.store.save_player(self.player)

    def orenna_trail(self, i: int) -> None:
        T = O["trails"][i]
        o = self.player.orenna
        city = self.orenna_city(o["trails"][i])
        console.narrate(T["arrive"].format(city=city))
        degree = self.resolve(T["check"])
        console.narrate(T["results"].get(degree, T["results"]["failure"]))
        orenna.add_evidence(self.player, degree)
        self.orenna_lore(T["lore"])
        o["trails_done"].append(i)
        if len(o["trails_done"]) >= 2 and not o["executioner"]:
            self.orenna_executioner()
        if len(o["trails_done"]) >= 3 and o["executioner"] and orenna.stage(self.player) == "trails":
            orenna.set_stage(self.player, "registry")
            console.note("The dead point one way. Lethoria keeps the register of bound services.")
        self.store.save_player(self.player)

    def orenna_executioner(self) -> None:
        E = O["executioner"]
        o = self.player.orenna
        o["executioner"] = True
        console.narrate(E["arrive"].strip())
        self.orenna_say("The man in plain cloth", E["speech"])
        self.orenna_lore(E["lore"])
        console.note(E["press"])
        if console.ask().lower() not in ("y", "yes"):
            console.narrate(E["leave"])
            return
        console.say(E["warn"], "The man in plain cloth")
        creature = self.world.bestiary["bound_executioner"]
        foe = combat.fighter_from_creature(creature, self.player.character.level + 1, "elite", "e1", "the Bound Executioner", "near")
        foe.yields_at, foe.yield_text = E["yield_at"], E["yield_story"]
        self.orenna_fight = "executioner"
        from scenes.combat_scene import CombatScene
        console.narrate(E["fight_intro"])
        self.combat = CombatScene.begin(self, creature, [foe], "Facing you,")

    # ---------- the register and the High Keeper ----------

    def orenna_registry(self) -> None:
        R = O["registry"]
        console.narrate(R["arrive"].strip())
        degree = self.resolve(R["check"])
        console.narrate(R["results"].get(degree, R["results"]["failure"]))
        orenna.add_evidence(self.player, degree)
        self.orenna_lore(R["lore"])
        orenna.set_stage(self.player, "confront")
        self.store.save_player(self.player)
        self.orenna_confront()

    def orenna_confront(self) -> None:
        from engine import bosses
        K = O["confront"]
        o = self.player.orenna
        console.narrate(K["arrive"].strip())
        self.orenna_say("The High Keeper", K["speech"])
        strong = orenna.evidence_text(self.player) == "strong"
        if strong:
            console.narrate(K["strong_evidence"])
        console.narrate(K["begin"])
        keeper_c = self.world.bestiary["high_keeper"]
        exec_c = self.world.bestiary["bound_executioner"]
        lvl = self.player.character.level + 2
        keeper = combat.fighter_from_creature(keeper_c, lvl, "boss", "e1", "the High Keeper", "near")
        keeper.boss = bosses.make("person", "leader", "the High Keeper", K["lines"])
        keeper.boss["seal"] = True
        keeper.boss["evidence"] = float(o.get("evidence", 0.0))
        if strong:
            keeper.boss["guards"] = bosses.B["max_guards"]      # his witnesses are gone: no one steps in to defend him
        bound = combat.fighter_from_creature(exec_c, lvl - 1, "elite", "e2", "the Bound Executioner", "near")
        bound.bound = True
        self.orenna_fight = "keeper"
        from scenes.combat_scene import CombatScene
        self.combat = CombatScene.begin(self, keeper_c, [keeper, bound], "Before you,", big="lair")

    def orenna_fight_over(self, outcome: str) -> None:
        kind = getattr(self, "orenna_fight", None)
        self.orenna_fight = None
        if not kind:
            return
        if kind == "executioner":
            if outcome == "victory":
                console.narrate(O["executioner"]["yield"])
            return
        if outcome == "victory":
            self.orenna_finish()
        else:
            self.player.orenna["retry"] = self.minutes + 360
            self.store.save_player(self.player)

    # ---------- the blessing ----------

    def orenna_finish(self) -> None:
        B = O["blessing"]
        self.orenna_say("Odrin Kesh", O["confront"]["after"][1:])
        console.narrate(O["confront"]["after"][0])
        self.advance(8 * 60)
        console.narrate(B["arrive"].strip())
        console.say(B["line"], "Orenna")
        c = self.player.character
        c.orenna_breath = True
        self.orenna_lore(B["lore"])
        orenna.set_stage(self.player, "done")
        console.note(f"{B['gain']} {B['text']}")
        self.store.save_player(self.player)
