"""Field abilities in play: what an out-of-combat ability does, by its function (engine/field.py, data/rules/field.yaml).

Each use is one deliberate act with an immediate result. The engine decides the result; the model only describes it.
State lives in player.field: cd (ability id -> game minute it is ready), camp, haste, edge, shadow, scouted, lit, shows."""

import random

from engine import clock, dungeons, encounters, field, inventory as inv, money, pools, pulse
from engine.field import F, tier_value
from npc.models import Memory
from ui import console

LIGHT_WORDS = ("light", "glow", "illumin", "flame", "lantern", "radian", "torch", "shine", "luminous", "ember", "spark")
DARK_PENALTY_DEFAULT = 20


class FieldActionsBase:

    # ---------- bookkeeping ----------

    @property
    def fld(self) -> dict:
        return self.player.field

    def ensure_field_uses(self) -> None:
        """Older characters: give each non-combat ability its function, once."""
        c = self.player.character
        if field.classify(c):
            self.store.save_player(self.player)

    def field_ready_in(self, ability) -> int:
        return max(0, self.fld.get("cd", {}).get(ability.id, 0) - self.minutes)

    def field_cooldown_start(self, ability) -> None:
        self.fld.setdefault("cd", {})[ability.id] = self.minutes + field.cooldown_minutes(ability)

    # ---------- dispatch ----------

    def field_precheck(self, ability, intent, text: str) -> str | None:
        """A reason the ability cannot be used right now, or None. Nothing is spent when this refuses."""
        wait = self.field_ready_in(ability)
        if wait:
            return f"{ability.name} needs {clock.describe_duration(wait)} more before you can do it again."
        fn = ability.field_use
        if fn in ("read_the_room", "intimidate", "pickpocket") and not self.influence_target(intent):
            return "There's no one here to work on - say who you mean."
        if fn == "pickpocket" and self.fld.get("picked", {}).get(self.influence_target(intent).id) == clock.day(self.minutes):
            return "You've already tried them today. Their guard is up."
        if fn == "bind_beast":
            return f"{ability.name} is used in a fight, on a creature you face - wound one first, or hit it with all you have."
        if fn == "speak_corpse" and not self.bodies_here():
            return "There is no body here that can still answer you."
        if fn == "shelter" and not (self.place.danger or self.player.delve):
            return "There is no need to make camp here - this place already has shelter."
        if fn == "influence" and not self.influence_target(intent):
            return "There's no one here to work on - say who you mean."
        if fn == "showmanship":
            if not self.present:
                return "There's no audience here."
            if self.fld.get("shows", {}).get(self.show_key()):
                return "They've already had your act today in this place. Try another crowd, or another day."
        return None

    def field_apply(self, ability, intent, text: str) -> str | None:
        """Carry out the function. Returns what happened (for the narrator), or None if nothing came of it (refund)."""
        handler = getattr(self, f"field_{ability.field_use}", None)
        if not handler:
            return None
        out = handler(ability, intent, text)
        if out is not None:
            self.field_cooldown_start(ability)
        return out

    # ---------- scout ----------


    def field_scout(self, ability, intent, text: str) -> str | None:
        self.advance(5)
        d = self.dungeon_here()
        lit = any(w in f"{ability.name} {ability.description} {' '.join(ability.tags)}".lower() for w in LIGHT_WORDS)
        if d:
            nxt = dungeons.next_chamber(d)
            if nxt is None:
                console.note("Nothing is left below to look for - it is cleared to the bottom.")
                return None
            f, c = nxt
            ch = d["floors"][f]["chambers"][c]
            self.fld["scouted"] = {"dungeon": d["id"], "pos": [f, c]}
            seen = self.describe_chamber(ch, d, f, c)
            if lit and self.is_dark_theme(d):
                self.fld["lit"] = {"dungeon": d["id"], "until": self.minutes + F["scout"]["light_minutes"]}
                seen += " Your light holds the dark back for a while."
            console.note(f"You scout ahead: {seen}")
            return f"They scout ahead of them in {d['name']} and learn exactly this: {seen} Describe how they sense it, without adding anything."
        if self.place.danger:
            roster = encounters.ensure_roster(self.store, self.world, self.player.location)
            if not roster:
                console.note("You read the land and find nothing to fear here.")
                return "They read the land and find it quiet. Describe it, adding nothing."
            names = ", ".join(self.world.bestiary[r].name.lower() for r in roster)
            console.note(f"You read the signs: things that live here - {names}.")
            return f"They survey the wild around them and find signs of: {names}. Describe the signs only, nothing else."
        roles = sorted({n.role.replace("_", " ") for n in self.present if n.role})
        if not roles:
            console.note("You look the place over and see no one about.")
            return "They look the place over and see no one about."
        console.note(f"You size up the room: {', '.join(roles)}.")
        return f"They size up who is here by how they carry themselves: {', '.join(roles)}. Describe only what they notice."

    def describe_chamber(self, ch: dict, d: dict, f: int = -1, c: int = -1) -> str:
        kind = ch["kind"]
        if kind == "fight":
            name = self.world.bestiary[ch["creature"]].name.lower()
            if ch.get("boss"):
                return f"the master of this place waits ahead ({d['boss_name']}), with its guard."
            n = ch["count"]
            return f"{n} {name}{'' if n == 1 else 's'} hold the next chamber."
        return {"trap": "the next chamber is trapped - you see the trigger and will step around it.",
                "cache": "a cache lies hidden in the next chamber" + (" - and it is locked." if (f >= 0 and self.cache_locked(d, f, c)) else "."),
                "rest": "the next chamber is quiet and empty - a safe place to rest."}.get(kind, "nothing of note ahead.")

    # ---------- shelter ----------

    def camp_pos(self):
        dv = self.player.delve
        return [dv["floor"], dv["chamber"]] if dv else None

    def camp_active(self) -> bool:
        camp = self.fld.get("camp")
        return bool(camp and camp["loc"] == self.player.location and camp["until"] > self.minutes
                    and camp["pos"] == self.camp_pos())

    def field_shelter(self, ability, intent, text: str) -> str | None:
        self.advance(15)
        self.fld["camp"] = {"loc": self.player.location, "pos": self.camp_pos(), "until": self.minutes + F["shelter"]["lasts_minutes"]}
        console.note("You make camp. You can rest here undisturbed - sleep and you will wake fully restored.")
        return "They set up a safe camp using it, a hidden, defensible place to rest. Describe the camp coming together."

    # ---------- haste ----------

    def field_haste(self, ability, intent, text: str) -> str | None:
        self.fld["haste"] = {"until": self.minutes + F["haste"]["expires_minutes"], "tier": ability.tier.value}
        console.note("Your legs feel light. Set out within the hour and your next journey will be quicker and easier.")
        return "They gather themselves to move fast; the next stretch of road will go quickly. Describe the surge."

    def take_haste(self, walk: int) -> tuple[int, float]:
        """On setting out: shorten the walk and ease the fatigue. Returns (walk, fatigue factor)."""
        h = self.fld.get("haste")
        if not h:
            return walk, 1.0
        if h["until"] <= self.minutes:
            self.fld.pop("haste", None)
            return walk, 1.0
        if walk < 30:
            return walk, 1.0          # too short a trip to spend it on
        self.fld.pop("haste", None)
        cut = tier_value(F["haste"]["travel_cut_percent"], h["tier"])
        fat = tier_value(F["haste"]["fatigue_cut_percent"], h["tier"])
        faster = max(1, round(walk * (1 - cut / 100)))
        console.note(f"Your quickened step saves {clock.describe_duration(walk - faster)} on the road.")
        return faster, 1 - fat / 100

    # ---------- influence ----------

    def influence_target(self, intent):
        target = getattr(intent, "target", "")
        npc = next((n for n in self.present if n.id == target), None) or \
            (self.partner if self.partner in self.present else None) or \
            (self.present[0] if len(self.present) == 1 else None)
        return npc

    def field_influence(self, ability, intent, text: str) -> str | None:
        npc = self.influence_target(intent)
        if not npc:
            return None
        day = clock.day(self.minutes)
        tier = ability.tier.value
        done = self.fld.setdefault("infl_day", {})
        gain = 0 if done.get(npc.id) == day else tier_value(F["influence"]["trust_gain"], tier)
        done[npc.id] = day
        bonus = tier_value(F["influence"]["next_check_bonus"], tier)
        self.fld["edge"] = {"npc": npc.id, "bonus": bonus, "until": self.minutes + 120}
        if gain:
            npc.trust = min(100, npc.trust + gain)
            self.store.save_npc(npc)
        console.note(f"{npc.label().capitalize()} warms to you." if gain else
                     f"{npc.label().capitalize()} is already as won over as you can make them today, but they're listening.")
        return (f"They bring {ability.name} to bear on {npc.label()}, who softens toward them and is more willing to listen. "
                "Describe the effect on the person, subtly, without having them agree to anything yet.")

    def spend_edge(self, check: str, npc) -> None:
        e = self.fld.get("edge")
        if e and npc is not None and e["npc"] == npc.id:
            from engine import checks
            if check in e.get("only", checks.SOCIAL):
                self.fld.pop("edge", None)

    # ---------- shadow ----------

    def field_shadow(self, ability, intent, text: str) -> str | None:
        self.fld["shadow"] = {"until": self.minutes + F["shadow"]["expires_minutes"], "tier": ability.tier.value}
        if self.dungeon_here() or self.player.delve:
            console.note("You fade into the dark. The next creature you meet in here can be slipped past.")
        elif self.place.danger:
            console.note("You become hard to find. The next thing that would find you here passes by.")
        else:
            console.note("You become hard to notice. Your next attempt to go unseen is much easier.")
        return "They slip into the background, hard to notice. Describe how they fade from sight."

    def shadow_active(self) -> bool:
        s = self.fld.get("shadow")
        if s and s["until"] <= self.minutes:
            self.fld.pop("shadow", None)
            return False
        return bool(s)

    def use_shadow(self) -> None:
        self.fld.pop("shadow", None)

    # ---------- recall ----------

    def field_recall(self, ability, intent, text: str) -> str | None:
        place = self.place
        subject = f"{place.name} {' '.join(place.visible)} " + " ".join(
            self.world.places[n].name for n in self.world.neighbors(place.id) if n in self.world.places)
        subject += " " + " ".join(f"{n.label()} {n.role}" for n in self.present)
        degree = "strong success" if ability.tier.value == "heavy" else "success"
        out = self.lore(subject, degree)
        if not out.startswith("The player recalls"):
            console.note("You search what you know, but there is nothing more to recall about this place.")
            return None
        console.note("Something comes back to you. (Added to what you know.)")
        return out

    # ---------- showmanship ----------

    def show_key(self) -> str:
        return f"{self.player.location}:{clock.day(self.minutes)}"

    def field_showmanship(self, ability, intent, text: str) -> str | None:
        self.advance(20)
        self.fld.setdefault("shows", {})[self.show_key()] = 1
        degree = "strong success" if ability.tier.value == F["showmanship"]["strong_tier"] else "success"
        return self.performance(degree)

    # ---------- darkness ----------

    def is_dark_theme(self, d: dict) -> bool:
        return bool(dungeons.D["themes"].get(d["theme"], {}).get("dark"))

    def lit_now(self, d: dict) -> bool:
        lit = self.fld.get("lit")
        return bool(lit and lit["dungeon"] == d["id"] and lit["until"] > self.minutes)

    def scouted_here(self, d: dict, f: int, c: int) -> bool:
        s = self.fld.get("scouted")
        return bool(s and s["dungeon"] == d["id"] and s["pos"] == [f, c])

    def ensure_light(self, d: dict) -> None:
        """Going down into a dark place: light a torch if there's none burning."""
        if not self.is_dark_theme(d) or self.lit_now(d):
            return
        torch = inv.take(self.pack, "torch", 1)
        if torch:
            self.fld["lit"] = {"dungeon": d["id"], "until": self.minutes + dungeons.D["torch_minutes"]}
            left = sum(i.quantity for i in self.pack if i.good == "torch")
            console.note(f"You light a torch. ({left} left)")
        else:
            console.note(f"It is pitch black down here and you carry no light. You'll be feeling your way - "
                         f"spotting traps and finding things is harder (-{dungeons.D['dark_penalty']}). A torch from a chandler fixes that.")

    def darkness_penalty(self) -> int:
        """Negative modifier to perception while down in a dark dungeon with no light and nothing scouted."""
        d = self.dungeon_here()
        dv = self.player.delve
        if not d or not dv or not self.is_dark_theme(d) or self.lit_now(d):
            return 0
        if self.scouted_here(d, dv["floor"], dv["chamber"]):
            return 0
        return -dungeons.D["dark_penalty"]


class FieldFunctions:
    """The newer functions (data/rules/field.yaml): each is one deliberate act with an immediate, engine-decided result."""

    # ---------- trapfinder, picklock: below ----------

    def chambers_ahead(self, d: dict):
        """(floor, chamber, chamber dict) for every chamber not yet cleared, from the next one down."""
        nxt = dungeons.next_chamber(d)
        if nxt is None:
            return
        f0, c0 = nxt
        for f in range(f0, len(d["floors"])):
            chambers = d["floors"][f]["chambers"]
            for c in range(c0 if f == f0 else 0, len(chambers)):
                yield f, c, chambers[c]

    @staticmethod
    def where_chamber(f: int, c: int, first: tuple) -> str:
        return "the next chamber" if (f, c) == first else f"floor {f + 1}, chamber {c + 1}"

    def field_trapfinder(self, ability, intent, text: str) -> str | None:
        d = self.dungeon_here()
        if not d:
            console.note("There are no traps to feel out here - save it for a dungeon.")
            return None
        ahead = list(self.chambers_ahead(d))
        if not ahead:
            console.note("It is cleared to the bottom - nothing is left to find.")
            return None
        for f, c, ch in ahead:
            if ch["kind"] == "trap" and not ch.get("disarmed"):
                ch["disarmed"] = True
                self.save_dungeon(d)
                self.advance(F["trapfinder"]["minutes"])
                where = self.where_chamber(f, c, ahead[0][:2])
                console.note(f"You feel out the trap in {where} and disarm it for good.")
                return (f"They sense a hidden trap in {where} of {d['name']} and quietly disarm it. "
                        "Describe how they find and defuse it, fitting the place.")
        console.note("You feel through the stone and find no more traps below.")
        return None

    # ---------- beastspeak ----------

    def field_beastspeak(self, ability, intent, text: str) -> str | None:
        if not self.place.danger:
            console.note("There are no wild creatures here to speak with.")
            return None
        roster = encounters.ensure_roster(self.store, self.world, self.player.location)
        beasts = [self.world.bestiary[r].name.lower() for r in roster if self.world.bestiary[r].category == "beast"]
        if not beasts:
            console.note("Nothing that lives here answers to you - no beasts, only worse.")
            return None
        mins = tier_value(F["beastspeak"]["calm_minutes"], ability.tier)
        self.fld["calm"] = {"loc": self.player.location, "until": self.minutes + mins}
        self.advance(5)
        console.note(f"The animals tell you what lives here: {', '.join(beasts)}. They will leave you be for {clock.describe_duration(mins)}.")
        return (f"They speak with the animals around them, who tell them of {', '.join(beasts)} nearby and agree to keep away. "
                "Describe the wordless exchange, adding no other facts.")

    def beasts_calm(self, creature) -> bool:
        c = self.fld.get("calm")
        return bool(c and c["loc"] == self.player.location and c["until"] > self.minutes and creature.category == "beast")

    # ---------- swift step ----------

    def field_swift_step(self, ability, intent, text: str) -> str | None:
        self.fld["swift"] = {"until": self.minutes + F["swift_step"]["expires_minutes"], "tier": ability.tier.value}
        console.note("You lighten your tread. Set out within the hour and you will arrive fresher, with fewer troubles on the way.")
        return "They fall into a light, careful stride that wastes nothing. Describe the quiet readiness."

    def take_swift(self, walk: int) -> float:
        """On setting out: ease the fatigue and thin out the trouble on the road. Returns the fatigue factor."""
        sw = self.fld.get("swift")
        self.journey_event_factor = 1.0
        if not sw:
            return 1.0
        if sw["until"] <= self.minutes:
            self.fld.pop("swift", None)
            return 1.0
        if walk < 30:
            return 1.0
        self.fld.pop("swift", None)
        self.journey_event_factor = 1 - tier_value(F["swift_step"]["event_cut_percent"], sw["tier"]) / 100
        console.note("Your light step keeps you fresh and the road quiet.")
        return 1 - tier_value(F["swift_step"]["fatigue_cut_percent"], sw["tier"]) / 100

    # ---------- barter ----------

    def field_barter(self, ability, intent, text: str) -> str | None:
        pct = tier_value(F["barter"]["discount_percent"], ability.tier)
        self.fld["barter"] = {"pct": pct, "until": self.minutes + F["barter"]["expires_minutes"]}
        console.note(f"You have the measure of the market. Your next purchase or sale goes {pct}% better, if you make it soon.")
        return "They settle into the easy confidence of someone about to strike a bargain. Describe it in a line."

    def barter_pct(self) -> int:
        b = self.fld.get("barter")
        if not b:
            return 0
        if b["until"] <= self.minutes:
            self.fld.pop("barter", None)
            return 0
        return b["pct"]

    def use_barter(self) -> None:
        if self.barter_pct():
            self.fld.pop("barter", None)
            console.note("Your bargaining pays off.")

    # ---------- read the room ----------

    def field_read_the_room(self, ability, intent, text: str) -> str | None:
        npc = self.influence_target(intent)
        if not npc:
            return None
        self.advance(F["read_the_room"]["minutes"])
        trust = ("distrusts you" if npc.trust < 30 else "is wary of you" if npc.trust < 45 else "is neutral toward you" if npc.trust < 60
                 else "likes you" if npc.trust < 80 else "trusts you")
        mood = npc.mood or "even"
        weighs = npc.concern or "nothing you can make out"
        console.note(f"{npc.label().capitalize()}: mood {mood}; what weighs on them - {weighs}; {trust}.")
        return (f"They read {npc.label()} closely. Their mood is: {mood}. What weighs on them: {weighs}. They {trust.replace('you', 'the player')}. "
                "Describe the small signs the player notices, without having the person say any of it aloud.")

    # ---------- intimidate ----------

    def field_intimidate(self, ability, intent, text: str) -> str | None:
        npc = self.influence_target(intent)
        if not npc:
            return None
        bonus = tier_value(F["intimidate"]["bonus"], ability.tier)
        self.fld["edge"] = {"npc": npc.id, "bonus": bonus, "until": self.minutes + F["intimidate"]["expires_minutes"],
                            "only": ["intimidation"]}
        npc.trust = max(0, npc.trust - F["intimidate"]["trust_cost"])
        self.store.save_npc(npc)
        console.note(f"{npc.label().capitalize()} shrinks back from you. Your next attempt to frighten them will be far easier.")
        return (f"They bring {ability.name} to bear on {npc.label()}, looming, letting menace do the work. Describe the person "
                "flinching, without having them yield anything yet.")

    # ---------- pickpocket ----------

    def field_pickpocket(self, ability, intent, text: str) -> str | None:
        npc = self.influence_target(intent)
        if not npc:
            return None
        P = F["pickpocket"]
        c = self.player.character
        self.fld.setdefault("picked", {})[npc.id] = clock.day(self.minutes)
        prior = self.fld.get("shadow")
        self.fld["shadow"] = {"until": self.minutes + 1, "tier": ability.tier.value}
        try:
            degree = self.resolve("stealth", None)
        finally:
            if prior:
                self.fld["shadow"] = prior
            else:
                self.fld.pop("shadow", None)
        self.advance(5)
        if degree in ("strong success", "success", "partial"):
            share = P["strong_share"] if degree == "strong success" else 1.0 if degree == "success" else P["partial_share"]
            coins = max(1, round(random.randint(*P["coins_per_level"]) * max(1, c.level) * share))
            c.coins += coins
            if degree == "partial":
                npc.trust = max(0, npc.trust - P["trust_loss"]["partial"])
                self.store.save_npc(npc)
            console.note(f"You lift {money.fmt(coins)} from {npc.label()}." + (" They almost felt it." if degree == "partial" else ""))
            return (f"They quietly lift a purse from {npc.label()} and walk off with {money.words(coins)}. "
                    "Describe the sleight of hand, and that the person does not notice."
                    + (" The person nearly feels it." if degree == "partial" else ""))
        npc.trust = max(0, npc.trust - P["trust_loss"]["failure"])
        npc.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                   text="The stranger tried to pick my pocket, and I caught them at it."))
        self.store.save_npc(npc)
        self.reputation_change("threat")
        console.note(f"{npc.label().capitalize()} catches your hand. They will not forget it.")
        return (f"They reach for {npc.label()}'s purse and are caught. Describe the person's hand closing on their wrist, "
                "and the cold look that follows. They get nothing.")

    # ---------- commune ----------

    # ---------- speak with a corpse ----------

    def keep_bodies(self, bodies: list[dict]) -> list[dict]:
        """The fallen a place still remembers: recent ones, the newest few."""
        S = F["speak_corpse"]
        limit = S["keep_days"] * 1440
        live = [b for b in bodies if self.minutes - b["minute"] < limit]
        return live[-S["max_bodies"]:]

    def bodies_here(self) -> list[dict]:
        state = self.store.load_place(self.player.location)
        return [b for b in self.keep_bodies(state.bodies) if not b.get("asked")]

    def field_speak_corpse(self, ability, intent, text: str) -> str | None:
        S = F["speak_corpse"]
        state = self.store.load_place(self.player.location)
        state.bodies = self.keep_bodies(state.bodies)
        fresh = [b for b in state.bodies if not b.get("asked")]
        if not fresh:
            console.note("There is no body here that can still answer you.")
            return None
        low = f"{intent.target} {intent.item} {text}".lower()
        body = next((b for b in fresh if b["creature"].replace("_", " ") in low or b["name"].lower() in low), None) or fresh[-1]
        body["asked"] = True
        self.store.save_place(state)
        self.advance(S["minutes"])
        age = (self.minutes - body["minute"]) / 1440
        who = body["name"].lower()
        facts = [f"it was {who}, of about level {body['level']}"]
        if age < S["stale_days"]:
            facts.append(f"it fell {clock.describe_duration(self.minutes - body['minute'])} ago, to the player's own hand")
        if age < S["fresh_days"]:
            facts.append(f"it carried {body['carried']}" if body.get("carried") else "it carried nothing of worth")
        line = "; ".join(facts)
        console.note(f"The dead answer: {line}.")
        vague = " The memory is faint; describe only fragments." if age >= S["stale_days"] else ""
        return (f"They kneel by the body of {who} and ask it to speak. All they learn: {line}.{vague} "
                "Describe the whispering of the dead, adding no facts beyond these.")

    def field_commune(self, ability, intent, text: str) -> str | None:
        st = self.store.load_world_state() or {}
        live = [t for t in st.get("threads", []) if t.get("status") == "active"]
        if not live:
            console.note("You reach out, and the land is quiet. Nothing stirs.")
            return None
        live.sort(key=lambda t: -t.get("stage", 0))
        tales = []
        for t in live[: tier_value(F["commune"]["max_tales"], ability.tier)]:
            place = self.world.places.get(t.get("place"))
            tales.append(f"{t['title']}" + (f" (near {place.name})" if place else ""))
        self.advance(F["commune"]["minutes"])
        console.note("Something answers. You learn of: " + "; ".join(tales) + ".")
        return ("They reach out beyond themselves and are answered with troubles brewing nearby: " + "; ".join(tales)
                + ". Describe how the knowledge comes to them, vaguely, adding no detail beyond this.")

    # ---------- tinker ----------

    def field_tinker(self, ability, intent, text: str) -> str | None:
        made = []
        for gid, table in F["tinker"]["makes"].items():
            n = tier_value(table, ability.tier)
            if n > 0 and gid in inv.GOODS:
                self.to_pack(inv.make_good(gid, n))
                made.append(f"{n} {inv.GOODS[gid].name}" + ("s" if n > 1 and not inv.GOODS[gid].name.endswith("s") else ""))
        self.advance(F["tinker"]["minutes"])
        console.note(f"You rig up from scraps: {', '.join(made)}.")
        return f"They set to work with whatever is at hand and put together {', '.join(made)}. Describe the quick, clever work."

    # ---------- treat ----------

    def field_treat(self, ability, intent, text: str) -> str | None:
        c = self.player.character
        top, cur = pools.maximum(c, "health"), pools.current(c, "health")
        fallen = [m for m in c.companions if m.fallen and not m.dead]
        if cur >= top * 0.999 and not fallen:
            console.note("There is nothing to tend - you are whole and your companions are on their feet.")
            return None
        gain = top * tier_value(F["treat"]["heal_percent"], ability.tier) / 100
        c.health = min(top, cur + gain)
        st = pools.maximum(c, "stamina")
        c.stamina = min(st, pools.current(c, "stamina") + st * tier_value(F["treat"]["stamina_percent"], ability.tier) / 100)
        for m in fallen:
            m.fallen = False
        self.advance(F["treat"]["minutes"])
        note = f" {', '.join(m.name for m in fallen)} {'is' if len(fallen) == 1 else 'are'} back on {'its' if len(fallen) == 1 else 'their'} feet." if fallen else ""
        console.note("You tend your wounds." + note)
        return "They bind and tend wounds with practiced hands." + (f" {', '.join(m.name for m in fallen)} rises, restored." if fallen else "")

    # ---------- bless ----------

    def field_bless(self, ability, intent, text: str) -> str | None:
        B = F["bless"]
        self.fld["bless"] = {"bonus": tier_value(B["bonus"], ability.tier), "until": self.minutes + B["lasts_minutes"]}
        console.note(f"Favor settles on you. Every check you make for the next {clock.describe_duration(B['lasts_minutes'])} is a little likelier to go your way.")
        return "They call down favor on themselves, and something warm settles over them. Describe it quietly."

    def blessed_bonus(self) -> int:
        b = self.fld.get("bless")
        if not b:
            return 0
        if b["until"] <= self.minutes:
            self.fld.pop("bless", None)
            return 0
        return b["bonus"]

    # ---------- summon labor ----------

    def field_summon_labor(self, ability, intent, text: str) -> str | None:
        mins = tier_value(F["summon_labor"]["open_minutes"], ability.tier)
        self.fld["box"] = {"until": self.minutes + mins}
        console.note(f"A servant arrives bearing your item box. You can store and take things for {clock.describe_duration(mins)}.")
        return "They summon a servant who appears at once, carrying their chest from home. Describe the arrival."

    def box_open(self) -> bool:
        b = self.fld.get("box")
        if b and b["until"] <= self.minutes:
            self.fld.pop("box", None)
            return False
        return bool(b)

    # ---------- picklock ----------

    def cache_locked(self, d: dict, f: int, c: int) -> bool:
        ch = d["floors"][f]["chambers"][c]
        if ch["kind"] != "cache" or ch.get("picked"):
            return False
        return random.Random(f"{d['id']}:{d['made']}:{f}:{c}:lock").random() < F["picklock"]["locked_chance"]

    def field_picklock(self, ability, intent, text: str) -> str | None:
        d = self.dungeon_here()
        if not d:
            console.note("There's no lock here worth your trouble.")
            return None
        ahead = list(self.chambers_ahead(d))
        for f, c, ch in ahead:
            if self.cache_locked(d, f, c):
                ch["picked"] = True
                self.save_dungeon(d)
                self.advance(F["picklock"]["minutes"])
                where = self.where_chamber(f, c, ahead[0][:2])
                console.note(f"You work the lock on the cache in {where} - it holds more than a plain one.")
                return (f"They find a locked cache in {where} of {d['name']} and work its lock open. "
                        "Describe the tumblers giving way, without saying what is inside.")
        console.note("No locked cache lies ahead.")
        return None

    # ---------- lucky ----------

    def lucky_save(self) -> str:
        """Lucky Break: the first failed check(s) of each day go your way. Returns the passive's name when one is saved."""
        per_day = int(self.has("lucky_break") or 0)
        if not per_day:
            return ""
        today = clock.day(self.minutes)
        used = self.fld.get("lucky", {})
        if used.get("day") != today:
            used = {"day": today, "n": 0}
        if used["n"] >= per_day:
            return ""
        used["n"] += 1
        self.fld["lucky"] = used
        return next((p.name for p in self.player.character.passives if p.mechanic == "lucky_break"), "Luck")

    # ---------- size up, snare ----------

    def field_size_up(self, ability, intent, text: str) -> str | None:
        d = self.dungeon_here()
        c = self.player.character
        if d:
            nxt = next(((f, k, ch) for f, k, ch in self.chambers_ahead(d)), None)
            if not nxt or nxt[2]["kind"] != "fight":
                console.note("Nothing waits in the next chamber to size up.")
                return None
            ch = nxt[2]
            gap = ch["level"] - c.level
            creature = self.world.bestiary[ch["creature"]].name.lower()
            word = ("a poor match for you" if gap <= -3 else "an even match" if gap < 3 else "a hard fight" if gap < 8 else "far beyond you")
            what = f"{ch['count']} {creature}{'' if ch['count'] == 1 else 's'} ahead - {word}"
        elif self.place.danger:
            roster = encounters.ensure_roster(self.store, self.world, self.player.location)
            if not roster:
                console.note("Nothing here is worth sizing up.")
                return None
            what = "the creatures of these parts: " + ", ".join(self.world.bestiary[r].name.lower() for r in roster)
        else:
            console.note("There's no foe here to size up.")
            return None
        self.fld["sized"] = {"loc": self.player.location, "tier": ability.tier.value,
                             "until": self.minutes + F["size_up"]["lasts_minutes"]}
        self.advance(5)
        console.note(f"You size up {what}. You have found the weak point; the next fight here will go easier.")
        return f"They study the foe and judge it: {what}. Describe the measuring look, and that they've found where it is weakest."

    def field_snare(self, ability, intent, text: str) -> str | None:
        if not (self.place.danger or self.dungeon_here()):
            console.note("There's nothing to catch in a safe place like this.")
            return None
        self.fld["snare"] = {"loc": self.player.location, "tier": ability.tier.value,
                             "until": self.minutes + F["snare"]["lasts_minutes"]}
        self.advance(15)
        console.note("You lay your snares. The next creature you fight here will start the fight already hurt.")
        return "They lay snares and tripwires with practiced care. Describe the quiet work."

    def field_prep(self, enemies: list) -> list[str]:
        """Called as a fight begins: spend a laid snare and a found weak point on these enemies."""
        notes = []
        for key in ("sized", "snare"):
            s = self.fld.get(key)
            if not s:
                continue
            if s["until"] <= self.minutes:
                self.fld.pop(key, None)
                continue
            if s["loc"] != self.player.location:
                continue
            self.fld.pop(key, None)
            if key == "sized":
                cut = tier_value(F["size_up"]["armor_cut_percent"], s["tier"]) / 100
                for e in enemies:
                    e.armor = round(e.armor * (1 - cut))
                    e.ward = round(e.ward * (1 - cut))
                notes.append("You strike where you judged it weakest - its defenses are thinner.")
            else:
                cut = tier_value(F["snare"]["hurt_percent"], s["tier"]) / 100
                for e in enemies:
                    e.hp = max(1, round(e.hp * (1 - cut)))
                notes.append("Your snare catches them - they come at you already hurt.")
        return notes

    # ---------- revivify ----------

    def field_revivify(self, ability, intent, text: str) -> str | None:
        c = self.player.character
        down = sorted((m for m in c.companions if m.dead or m.fallen), key=lambda m: not m.dead)
        if not down:
            console.note("None of your companions needs reviving.")
            return None
        m = down[0]
        m.dead = m.fallen = False
        m.recover_at = 0
        self.advance(F["revivify"]["minutes"])
        console.note(f"{m.name} draws breath and rises, whole.")
        return f"They call {m.name} back, and it rises at their side as if nothing had happened. Describe the moment."

    # ---------- word of recall ----------

    def note_town(self, place_id: str) -> None:
        """Remember the settlements you have stood in, most recent last."""
        town = pulse.town_of(self.world, place_id)
        if self.world.places[town].danger:
            return
        towns = self.fld.setdefault("towns", [])
        if town in towns:
            towns.remove(town)
        towns.append(town)

    def field_word_of_recall(self, ability, intent, text: str) -> str | None:
        here = pulse.town_of(self.world, self.player.location)
        dest = next((t for t in reversed(self.fld.get("towns", [])) if t != here), None)
        if not dest or dest not in self.world.places:
            console.note("There is no town you have left that you could return to yet.")
            return None
        self.advance(F["word_of_recall"]["minutes"])
        self.end_conversation()
        self.last_spoken = None
        self.player.delve = None
        self.enter(dest)
        console.note(f"The world folds, and you stand in {self.world.places[dest].name}.")
        return (f"They speak the word and the world folds around them; they step out in {self.place.name}. "
                f"Describe the arrival in a sentence or two.{self.brevity()}")

    # ---------- phantom steed ----------

    def field_phantom_steed(self, ability, intent, text: str) -> str | None:
        S = F["phantom_steed"]
        tier = ability.tier.value
        self.player.mounts = [m for m in self.player.mounts if m["id"] != "phantom_steed"]
        self.player.mounts.append({"id": "phantom_steed", "name": "your phantom steed", "speed": tier_value(S["speed"], tier),
                                   "stamina": tier_value(S["stamina"], tier)})
        self.player.mount = "phantom_steed"
        console.note(f"Your phantom steed answers and you mount. Journeys are {round(tier_value(S['speed'], tier) * 100)}% shorter "
                     f"and {round(tier_value(S['stamina'], tier) * 100)}% less wearying. It cannot die.")
        return "A spectral steed gathers out of the air and stands ready for them to ride. Describe it in a sentence."


class FieldActions(FieldActionsBase, FieldFunctions):
    pass
