"""Approaching a hideout: scout it, take guards out one by one, bluff or scare your way in, or strike from cover.

The engine decides everything: who is in the camp, what each attempt does, how alert the camp is, and who is caught
off guard when the fight starts. The model only describes it. A camp is built once per story step and remembered, so
guards you remove stay gone and the alert level carries over (falling by one for each day you stay away).
"""

import random

import re

from engine import arcs, checks, clock, combat, leveling
from engine import party as party_rules
from engine.arcs import A
from llm.contracts import CampIntent
from llm.gateway import LLMError, generate
from scenes import camp_prompts as cpr
from ui import console

CA = A["camp_approach"]

ORDINALS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}

# What the player may say, in the order they are tried. The more specific phrases come first.
WORDS = [
    ("ambush", ("ambush", "strike from", "from the shadows", "from cover", "backstab", "assassinate", "sneak attack",
                "surprise attack", "strike the leader", "kill the leader", "take out the leader", "attack the leader",
                "stab the leader", "go for the leader", "sneak up on the leader", "sneak to the leader",
                "sneak up on the boss", "kill the boss", "attack the boss")),
    ("bluff", ("bluff", "disguise", "pose as", "pretend", "pass as", "pass myself", "talk my way", "talk past",
               "deceive", "walk in as", "claim to be", "lie to", "play along", "walk right in")),
    ("scare", ("intimidate", "threaten", "scare", "make them flee", "warn them off", "drive them off", "demand they")),
    ("charge", ("charge", "storm", "rush in", "burst in", "kick in", "head on", "head-on", "go in loud",
                "fight my way", "attack openly", "assault")),
    ("scout", ("scout", "survey", "observe", "reconnoit", "case the", "spy on", "scan the", "study the camp",
               "watch the camp", "watch the guards", "count the guards", "look over", "look at the camp")),
    ("sneak", ("sneak", "creep", "silent", "quietly", "knock out", "take out", "pick off", "dispatch", "strangle",
               "garrote", "slit", "subdue", "stealth", "take down", "kill the guard", "kill a guard")),
    ("charge", ("attack", "fight", "cast ", "shoot", "loose an", "fire at", "throw ")),
]


METHOD_WORDS = {
    "cover": ("grass", "bush", "brush", "shadow", "behind", "rock", "tree", "wall", "crouch", "crawl", "hide", "hedge", "undergrowth"),
    "darkness": ("dark", "night", "moonless", "fog", "mist", "rain", "dusk"),
    "distraction": ("distract", "throw a", "toss a", "decoy", "diversion", "noise", "lure", "draw away"),
    "patience": ("wait", "patient", "patrol passes", "rotation", "timing", "bide", "watch for a gap"),
    "disguise": ("disguise", "uniform", "pose as", "false papers", "pretend", "dressed as"),
}


def keyword_intent(text: str) -> str | None:
    low = f" {text.lower()} "
    for kind, words in WORDS:
        if any(w in low for w in words):
            return kind
    return None


def keyword_methods(text: str) -> list[str]:
    low = text.lower()
    return [m for m, words in METHOD_WORDS.items() if any(w in low for w in words)]


class CampActions:
    from scenes.intercepts import Intercept as _I
    INTERCEPTS = (_I("camp", 50, "camp_turn", "what the player does at an enemy camp they have not yet fought", after="camp_took"),)

    def camp_took(self) -> None:
        """After a camp turn: the dungeons it may have opened, and the world moving on."""
        self.ensure_dungeons()
        self.run_pulse()
    camp_events: list = None

    # ---------- the camp's state ----------

    def camp_ctx(self):
        """(data, arc, node) when the player stands at a hideout they have started to approach, else None."""
        if self.combat:
            return None
        data, arc = self.my_arc()
        n = arcs.current(arc) if arc else None
        if not n or n["kind"] not in ("lair", "boss") or n["place"] != self.player.location or not n.get("camp"):
            return None
        return data, arc, n

    def camp_log(self, action: str, degree: str) -> None:
        if self.camp_events is None:
            self.camp_events = []
        self.camp_events.append((action, degree))

    def camp_build(self, arc: dict, n: dict, tpl: dict) -> dict:
        which = "boss" if n["kind"] == "boss" else "lair"
        rng = random.Random(f"{self.store.meta.seed}:camp:{arc['id']}:{n['id']}")
        base = self.player.character.level
        bestiary = self.world.bestiary
        leader_id = arcs.pick_creature(self.world, tpl["leaders"], base)
        rules = combat.RULES["creatures"]
        leader_c = bestiary[leader_id]
        kind = "people" if leader_c.category in A["people_categories"] else "other"
        bulk = rules["size_health"].get(leader_c.size, 1) * rules["size_damage"].get(leader_c.size, 4.0) / 4.0
        leader_lv = max(1, round(base * A["leader_level"][which] / max(1.0, bulk) ** 0.5))
        ranked = arcs.ranked(self.world, tpl["minions"], base)[:2]
        guards = []
        for i in range(rng.randint(*A["camp_size"][kind][which])):
            guards.append({"creature": rng.choice(ranked), "name": f"{tpl['minion_name']} {i + 1}", "state": "up",
                           "level": max(1, round(base * rng.uniform(*A["camp_level"][kind][which])))})
        sn = self.story_node(arc, n["id"])
        return {"base": base, "leader": {"creature": leader_id, "level": leader_lv, "name": sn.get("npc_name") or "the camp leader"},
                "guards": guards, "alert": 0, "edge": 0, "scouted": False, "removed": 0, "day": clock.day(self.minutes)}

    def camp_get(self, data: dict, arc: dict, n: dict, tpl: dict) -> dict:
        """The camp of this step, built on first sight, rescaled if nothing has happened and you have grown, rested by the days away."""
        camp = n.get("camp")
        pristine = camp and camp["alert"] == 0 and not camp["scouted"] and all(g["state"] == "up" for g in camp["guards"])
        if not camp or (pristine and abs(self.player.character.level - camp["base"]) > 0.25 * camp["base"]):
            camp = n["camp"] = self.camp_build(arc, n, tpl)
        today = clock.day(self.minutes)
        gone = (today - camp["day"]) // CA["decay_days"]
        if gone > 0 and camp["alert"] > 0:
            camp["alert"] = max(0, camp["alert"] - gone)
        camp["day"] = today if gone > 0 or camp["alert"] == 0 else camp["day"]
        self.store.save_arcs(data)
        return camp

    def camp_leader_is_people(self, camp: dict) -> bool:
        return self.world.bestiary[camp["leader"]["creature"]].category in A["people_categories"]

    def camp_enemies(self, camp: dict, tpl: dict, which: str, surprise: str = "none", far: bool = False) -> tuple[list, list]:
        """(the first wave, the reserves). The first wave is the leader and a few guards; the rest arrive while the fight lasts."""
        start = "far" if far else "near"
        guards = []
        for i, g in enumerate(camp["guards"]):
            if g["state"] == "up":
                guards.append(combat.fighter_from_creature(self.world.bestiary[g["creature"]], g["level"], "normal",
                                                           f"e{i + 1}", g["name"], start))
        ld = camp["leader"]
        leader = combat.fighter_from_creature(self.world.bestiary[ld["creature"]], ld["level"],
                                              "boss" if which == "boss" else "elite", "e0", ld["name"], start)
        first = guards[:A["camp_waves"]["first"]]
        reserves = guards[A["camp_waves"]["first"]:]
        if surprise == "all":
            for f in first:
                f.statuses["unaware"] = 1
        if surprise in ("all", "leader"):
            leader.statuses["unaware"] = 1
        return [leader] + first, reserves

    def camp_roll(self, check: str, extra: list, label: str) -> str:
        c = self.player.character
        bonus = list(self.check_bonuses(check, None, False, getattr(self, "last_text", "") or "")) + list(extra) \
            + list(getattr(self, "camp_bonus", None) or [])
        odds, why = checks.chance(c, check, self.check_triggers(check, False), None, bonus)
        degree, rolled = checks.roll(odds, c=c)
        console.debug(f"camp {label}: {check} {odds:.0f}% ({', '.join(why)}) - rolled {rolled}")
        console.note(checks.label(check, degree))
        self.camp_log(label, degree)
        return degree

    def camp_level_mod(self, rule: dict, enemy_level: int) -> float:
        lo, hi = rule["level_cap"]
        return max(lo, min(hi, (self.player.character.level - enemy_level) * rule["level_weight"]))

    def camp_party_mod(self, kind: str) -> list:
        """What travelling with a band of hirelings does to an approach. Told to hold back, they cost nothing."""
        members = self.player.party
        if not members:
            return []
        st = party_rules.P["stealth"]
        if kind == "scout":
            bonus = party_rules.scout_bonus(members)
            return [("scouts in the party", bonus)] if bonus else []
        if self.player.party_mode == "hold":
            return []
        if kind in ("sneak", "ambush"):
            pen = party_rules.sneak_penalty(members)
            return [("a group is loud", pen)] if pen else []
        if kind == "bluff":
            return [("an armed company", st["bluff_each"] * len(members))]
        if kind == "scare":
            return [("an armed company", st["scare_each"] * len(members))]
        return []

    def camp_common(self, rule: dict, camp: dict) -> list:
        out = []
        if camp["alert"]:
            out.append(("camp on edge", -rule.get("alert_penalty", 0) * camp["alert"]))
        if camp["edge"]:
            out.append(("scouted", camp["edge"]))
        if rule.get("night_bonus") and clock.is_dark(self.minutes):
            out.append(("night", rule["night_bonus"]))
        return out

    # ---------- arriving ----------

    def camp_enter(self, data: dict, arc: dict, n: dict, tpl: dict) -> bool:
        """Come within sight of a hideout. Returns True only if the camp is already waiting and the fight starts at once."""
        camp = self.camp_get(data, arc, n, tpl)
        if camp["alert"] >= CA["alarm"]:
            self.narrate("The player returns to a camp that is on its guard. Its people have been waiting for them. "
                         "Describe the tense moment as the camp rises to meet them.", "")
            return self.camp_battle(data, arc, n, tpl)
        sn = self.story_node(arc, n["id"])
        what = tpl["boss_desc"] if n["kind"] == "boss" else tpl["lair_desc"]
        wary = " The camp is wary; someone has been looking out." if camp["alert"] else ""
        self.narrate(f"Following the trail, the player comes within sight of {what}, at {self.place.name}, held by "
                     f"{sn.get('npc_name', 'a hard-eyed leader')} ({sn.get('npc_looks', '')}). They have NOT been seen yet.{wary} "
                     "Describe the place from the cover where the player stands, and hint at watchers without counting them. "
                     "Do not start a fight and do not decide what the player does.", "")
        self.camp_options(camp, tpl)
        return False

    def camp_options(self, camp: dict, tpl: dict) -> None:
        people = self.camp_leader_is_people(camp)
        up = sum(1 for g in camp["guards"] if g["state"] == "up")
        opts = ["scout the camp"] if not camp["scouted"] else []
        if up:
            opts.append("sneak up on a guard")
        if people and up:
            opts += ["bluff your way in", "scare the guards off"]
        elif people:
            opts.append("bluff your way in")
        opts += ["ambush the leader", "charge in"]
        console.note("You have not been seen. You could: " + " · ".join(opts) + " - or describe your own way, or go elsewhere.")

    # ---------- reading the player ----------

    def camp_scene(self) -> tuple[str, str]:
        """(biome, a line about the light and weather) - what the model may know about the surroundings."""
        parent = self.world.places.get(self.place.parent) if self.place.parent else None
        biome = self.place.biome or (parent.biome if parent else "") or ""
        cond = self.conditions()
        light = "It is night." if "at_night" in cond else "It is daylight."
        return biome, f"{light}{' It is raining or stormy.' if 'in_bad_weather' in cond else ''} Terrain: {biome or 'unknown'}."

    def camp_read(self, text: str, camp: dict) -> CampIntent:
        """The model reads the player's words; if it cannot, plain keywords do."""
        biome, scene = self.camp_scene()
        guards = [g["name"] for g in camp["guards"] if g["state"] == "up"]
        try:
            return generate("camp_intent", cpr.SYSTEM,
                            cpr.user(text, guards, camp["leader"]["name"], self.camp_leader_is_people(camp), self.place.name, scene),
                            CampIntent, temperature=0.2, max_tokens=150)
        except LLMError:
            return CampIntent(kind=keyword_intent(text) or "none", method=keyword_methods(text))

    def camp_target(self, camp: dict, text: str, named: str = "") -> dict | None:
        up = [g for g in camp["guards"] if g["state"] == "up"]
        if not up:
            return None
        for hay in (named.lower(), text.lower()):
            if not hay:
                continue
            for g in up:
                if g["name"].lower() in hay:
                    return g
            for word, idx in ORDINALS.items():
                if re.search(rf"\b{word}\b", hay) and idx <= len(camp["guards"]) and camp["guards"][idx - 1]["state"] == "up":
                    return camp["guards"][idx - 1]
            m = re.search(r"\b(\d+)\b", hay)
            if m and 1 <= int(m.group(1)) <= len(camp["guards"]) and camp["guards"][int(m.group(1)) - 1]["state"] == "up":
                return camp["guards"][int(m.group(1)) - 1]
        return up[0]

    def camp_methods(self, tags: list[str], kind: str, camp: dict) -> tuple[list, int]:
        """Turn what the player described into a small bonus, but only for what the scene truly offers."""
        rule = CA["methods"]
        biome, _ = self.camp_scene()
        cond = self.conditions()
        found, notes, minutes = [], [], 0
        for tag in dict.fromkeys(tags):
            ok, why = True, ""
            if tag == "cover":
                ok, why = biome in rule["cover_biomes"], "There is nothing out here to hide behind."
            elif tag == "darkness":
                ok, why = ("at_night" in cond or "in_bad_weather" in cond), "It is too bright out to hide in the dark."
            elif tag == "distraction":
                ok, why = bool(self.player.character.inventory) or camp["scouted"], "You have nothing to make a distraction with."
            elif tag == "disguise":
                ok, why = kind == "bluff", "A disguise will not help with this."
            elif tag == "patience":
                minutes += rule["patience_hours"] * 60
            if ok:
                found.append((tag, rule["bonus"]))
            else:
                notes.append(why)
        total = 0
        out = []
        for tag, amount in found:
            take = min(amount, rule["cap"] - total)
            if take > 0:
                total += take
                out.append((tag, take))
        for why in notes:
            console.note(why)
        if out:
            console.note("Your approach helps: " + ", ".join(f"{t} (+{v})" for t, v in out) + ".")
        return out, minutes

    def camp_turn(self, text: str) -> bool:
        """Handle a camp action in the player's words. False means this is not about the camp: carry on as normal."""
        ctx = self.camp_ctx()
        if not ctx or text.lstrip().startswith(("#", "/")):
            return False
        data, arc, n = ctx
        tpl = arcs.TEMPLATES[arc["template"]]
        camp = self.camp_get(data, arc, n, tpl)
        intent = self.camp_read(text, camp)
        if intent.kind == "none":
            return False
        kind = intent.kind
        if kind == "sneak" and re.search(r"\b(leader|boss|captain|chief)\b", f"{intent.target}".lower()):
            kind = "ambush"
        self.last_text = text
        if camp["alert"] >= CA["alarm"]:
            return self.camp_battle(data, arc, n, tpl) or True
        methods, extra_minutes = self.camp_methods(intent.method, kind, camp)
        self.camp_bonus = methods
        if extra_minutes:
            self.advance_quiet(extra_minutes)
        try:
            getattr(self, f"camp_{kind}")(data, arc, n, tpl, camp, text, intent.target)
        finally:
            self.camp_bonus = []
        self.store.save_arcs(data)
        return True

    # ---------- raising the alarm ----------

    def camp_raise(self, data, arc, n, tpl, camp, amount: int, event: str, text: str) -> bool:
        """Raise the alert. At the alarm level the fight starts now. Returns True if it did."""
        camp["alert"] = min(CA["alarm"], camp["alert"] + amount)
        camp["day"] = clock.day(self.minutes)
        self.store.save_arcs(data)
        if camp["alert"] >= CA["alarm"]:
            self.narrate(event + " The alarm is raised: the camp turns on the player. Describe the moment it goes wrong. "
                         "Do not describe the fight itself.", text)
            self.camp_battle(data, arc, n, tpl)
            return True
        return False

    # ---------- the actions ----------

    def camp_scout(self, data, arc, n, tpl, camp, text, target: str = "") -> None:
        if camp["scouted"]:
            console.note("You have learned what you can from out here. Time to act.")
            return
        self.advance_quiet(CA["scout"]["hours"] * 60)
        degree = self.camp_roll(CA["scout"]["check"], self.camp_common(CA["scout"], camp) + self.camp_party_mod("scout"), "scout")
        people = self.camp_leader_is_people(camp)
        if degree == "failure":
            if not self.camp_raise(data, arc, n, tpl, camp, 1,
                                   "[THE GAME HAS DECIDED: the player's scouting fails and someone in the camp glimpses movement "
                                   "and grows wary. Nothing is learned.]", text):
                self.narrate("[THE GAME HAS DECIDED: the player's scouting fails and someone in the camp glimpses movement "
                             "and grows wary. Nothing is learned. The camp has not seen who it is.]", text)
                console.note("Someone out there is watching the treeline now. The camp is wary.")
            return
        guards = [g for g in camp["guards"] if g["state"] == "up"]
        camp["scouted"] = True
        if degree == "partial":
            camp["edge"] = max(camp["edge"], CA["scout"]["edge_partial"])
            console.note(f"You make out {len(guards)} guard{'s' if len(guards) != 1 else ''} and a leader, and not much more.")
            self.narrate(f"[THE GAME HAS DECIDED: the player gets a partial look: {len(guards)} guards and a leader, nothing "
                         "about their habits.] Describe what the player can make out.", text)
            return
        camp["edge"] = CA["scout"]["edge"] + (5 if degree == "strong success" else 0)
        lvls = [g["level"] for g in guards]
        listing = (f"{len(guards)} (lv {min(lvls)}" + (f"-{max(lvls)}" if max(lvls) != min(lvls) else "") + ")") if guards else "none"
        ld = camp["leader"]
        flaw = random.Random(f"{arc['id']}:{n['id']}").choice(
            ["a watch that dozes at the far end", "a back way in that nobody covers", "a lookout who is half drunk",
             "a gap in the picket where the ground falls away"])
        first, reserves = self.camp_enemies(camp, tpl, "boss" if n["kind"] == "boss" else "lair")
        label, rate = combat.danger(self.camp_fight_sim(first, reserves))
        console.note(f"Guards: {listing}. Leader: {ld['name']} (lv {ld['level']}). Charging in looks: {label.upper()}.")
        console.note(f"You spot {flaw} - it will help you get close.")
        if label in ("dangerous", "deadly") and len(self.player.party) < party_rules.P["max_party"]:
            console.note("That is a garrison, not a gang. The guild hires out adventurers for a job like this.")
        self.narrate(f"[THE GAME HAS DECIDED: the player scouts well. They count {len(guards)} guards and the leader "
                     f"{ld['name']}, and notice {flaw}. Charging in would be {label}.] Describe what the player sees and works out, "
                     "from cover. Add no new characters.", text)

    def camp_fight_sim(self, enemies: list, reserves: list):
        from scenes.combat_scene import CombatScene
        c = self.player.character
        near, later = CombatScene.allies(self, hold=self.player.party_mode == "hold")
        fighters = [combat.fighter_from_character(c)] + near
        cmb = combat.Combat(fighters=fighters + [e.model_copy(deep=True) for e in enemies], place=self.place.name,
                            conditions=sorted(self.conditions()))
        cmb.reserves = [r.model_copy(deep=True) for r in reserves]
        cmb.ally_reserves, cmb.ally_arrive = later, party_rules.P["hold_arrival_round"]
        cmb.reinforce_every, cmb.reinforce_count = A["camp_waves"]["every"], A["camp_waves"]["count"]
        return cmb

    def camp_sneak(self, data, arc, n, tpl, camp, text, target: str = "") -> None:
        g = self.camp_target(camp, text, target)
        if not g:
            console.note("No guards are left - only the leader. You could ambush them, or charge in.")
            return
        rule = CA["sneak"]
        self.advance_quiet(rule["hours"] * 60)
        extra = self.camp_common(rule, camp) + [("level", self.camp_level_mod(rule, g["level"]))] + self.camp_party_mod("sneak")
        degree = self.camp_roll(rule["check"], extra, "sneak")
        who = g["name"]
        if degree == "failure":
            g["state"] = "up"
            self.camp_raise(data, arc, n, tpl, camp, CA["fail_alert"],
                            f"[THE GAME HAS DECIDED: the player's attempt to silence {who} fails - a cry, a clatter, a shout.]", text)
            return
        g["state"] = "down"
        xp = round(leveling.kill_xp(self.player.character.level, g["level"], "normal") * rule["xp_share"])
        gained = leveling.gain_xp(self.player.character, xp)
        console.note(f"{who} is dealt with. +{xp} XP" + (f" - LEVEL UP! You are now level {self.player.character.level}." if gained else ""))
        left = sum(1 for x in camp["guards"] if x["state"] == "up")
        tail = f" {left} guard{'s' if left != 1 else ''} left." if left else " Only the leader remains."
        console.note(tail.strip())
        camp["removed"] = camp.get("removed", 0) + 1
        noisy = degree == "partial"
        self.narrate(f"[THE GAME HAS DECIDED: the player silently takes out {who}." +
                     (" It is not clean - there is a clatter, a held breath - but nobody comes." if noisy else " Clean and quiet.") +
                     "] Describe it in keeping with the player's words and abilities. Nobody else notices.", text)
        if noisy and self.camp_raise(data, arc, n, tpl, camp, CA["partial_alert"],
                                     "[THE GAME HAS DECIDED: the noise carries and the camp stirs.]", text):
            return
        if camp["removed"] % CA["missing_every"] == 0 and left:
            if self.camp_raise(data, arc, n, tpl, camp, 1, "[THE GAME HAS DECIDED: someone in the camp notices that men have gone missing and calls out.]", text):
                return
            console.note("Someone has noticed men are missing. The camp is on edge.")
        elif noisy and camp["alert"]:
            console.note("The camp is on edge now.")

    def camp_strike(self, data, arc, n, tpl, camp, degree: str, text: str, how: str) -> None:
        """Turn a degree of success into how the fight begins. how: ambush | bluff."""
        surprise, far = {"strong success": ("all", False), "success": ("leader", False),
                         "partial": ("none", True), "failure": ("none", False)}[degree]
        if degree == "failure":
            camp["alert"] = CA["alarm"]
        desc = {
            ("ambush", "all"): "The player gets close unseen and strikes from cover; every one of them is caught unaware.",
            ("ambush", "leader"): "The player gets close unseen and falls on the leader before they can react.",
            ("ambush", "none"): "The player is seen as they close in, at a distance, and the camp rushes to meet them.",
            ("bluff", "all"): "The bluff is perfect: the camp waves the player in, and they strike with everyone off guard.",
            ("bluff", "leader"): "The bluff holds long enough to get the player face to face with the leader, who is caught off guard.",
            ("bluff", "none"): "The bluff wears thin halfway in; the camp turns on the player from a distance.",
        }
        key = (how, surprise if not (surprise == "none" and degree == "failure") else "none")
        line = desc[key] if degree != "failure" else ("The player is seen and the camp is on them." if how == "ambush"
                                                      else "The lie is caught at once, and the camp turns on the player.")
        self.narrate(f"[THE GAME HAS DECIDED: {line}] Describe this moment and end as steel is drawn.", text)
        if surprise != "none":
            console.note("You catch them off guard - you will have the first moment." if surprise == "all"
                         else "You catch the leader off guard - you will have the first moment against them.")
        self.camp_battle(data, arc, n, tpl, surprise=surprise, far=far)

    def camp_ambush(self, data, arc, n, tpl, camp, text, target: str = "") -> None:
        rule = CA["ambush"]
        up = sum(1 for g in camp["guards"] if g["state"] == "up")
        self.advance_quiet(rule["hours"] * 60)
        extra = self.camp_common(rule, camp) + [("level", self.camp_level_mod(rule, camp["leader"]["level"])),
                                                 ("guards", -rule["guard_penalty"] * up)] + self.camp_party_mod("ambush")
        degree = self.camp_roll(rule["check"], extra, "ambush")
        self.camp_strike(data, arc, n, tpl, camp, degree, text, "ambush")

    def camp_bluff(self, data, arc, n, tpl, camp, text, target: str = "") -> None:
        if not self.camp_leader_is_people(camp):
            console.note("There is nobody here to talk to. What lives here will not be fooled by words.")
            return
        rule = CA["bluff"]
        up = sum(1 for g in camp["guards"] if g["state"] == "up")
        self.advance_quiet(rule["hours"] * 60)
        rep = max(-rule["rep_cap"], min(rule["rep_cap"], self.player.outlaw_rep * rule["rep_weight"]))
        extra = self.camp_common(rule, camp) + [("guards", -rule["guard_penalty"] * up), ("known to outlaws", rep)] + self.camp_party_mod("bluff")
        best = max(rule["checks"], key=lambda k: checks.chance(self.player.character, k, self.check_triggers(k, False), None,
                                                              list(self.check_bonuses(k, None, False, text)) + extra + list(getattr(self, "camp_bonus", None) or []))[0])
        degree = self.camp_roll(best, extra, "bluff")
        self.camp_strike(data, arc, n, tpl, camp, degree, text, "bluff")

    def camp_scare(self, data, arc, n, tpl, camp, text, target: str = "") -> None:
        if not self.camp_leader_is_people(camp):
            console.note("Nobody here will be frightened off by words.")
            return
        guards = [g for g in camp["guards"] if g["state"] == "up"]
        if not guards:
            console.note("There are no guards left to scare off. The leader stands alone.")
            return
        rule = CA["scare"]
        self.advance_quiet(rule["hours"] * 60)
        avg = round(sum(g["level"] for g in guards) / len(guards))
        extra = self.camp_common(rule, camp) + [("level", self.camp_level_mod(rule, avg)), ("leader near", -rule["leader_penalty"])] + self.camp_party_mod("scare")
        degree = self.camp_roll(rule["check"], extra, "scare")
        if degree == "failure":
            camp["alert"] = CA["alarm"]
            self.narrate("[THE GAME HAS DECIDED: the player's threat is laughed off and the camp takes up arms.] "
                         "Describe it and end as steel is drawn.", text)
            self.camp_battle(data, arc, n, tpl)
            return
        share = {"strong success": 0.75, "success": 0.5, "partial": 0.25}[degree]
        fled = sorted(guards, key=lambda g: g["level"])[:max(1, round(len(guards) * share))]      # the weakest nerves go first
        for g in fled:
            g["state"] = "fled"
        camp["alert"] = max(camp["alert"], 1) if degree != "partial" else min(CA["alarm"] - 1, camp["alert"] + 1)
        if degree == "strong success":
            camp["edge"] += 10
        names = ", ".join(g["name"] for g in fled)
        left = sum(1 for g in camp["guards"] if g["state"] == "up")
        console.note(f"{names} run{'s' if len(fled) == 1 else ''} off into the dark." + (" The leader is shaken." if degree == "strong success" else "")
                     + (f" {left} guard{'s' if left != 1 else ''} left." if left else " Only the leader remains."))
        self.narrate(f"[THE GAME HAS DECIDED: the player's menace works. {names} lose their nerve and flee"
                     + (", and the leader is visibly shaken" if degree == "strong success" else "") + ".] "
                     "Describe it. The leader is still in the camp, and now knows something is wrong.", text)

    def camp_charge(self, data, arc, n, tpl, camp, text, target: str = "") -> None:
        camp["alert"] = CA["alarm"]
        self.narrate("The player does not bother with stealth and goes straight in. They are seen at once. "
                     "Describe the moment the camp rises to meet them, and end as steel is drawn.", text)
        self.camp_battle(data, arc, n, tpl)

    # ---------- the fight ----------

    def camp_battle(self, data: dict, arc: dict, n: dict, tpl: dict, surprise: str = "none", far: bool = False) -> bool:
        which = "boss" if n["kind"] == "boss" else "lair"
        camp = self.camp_get(data, arc, n, tpl)
        camp["alert"] = CA["alarm"]
        camp["day"] = clock.day(self.minutes)
        self.store.save_arcs(data)
        enemies, reserves = self.camp_enemies(camp, tpl, which, surprise, far)
        leader = enemies[0]
        leader_c = self.world.bestiary[camp["leader"]["creature"]]
        self.camp_fight = {"arc": arc["id"], "node": n["id"], "leader": leader.name,
                           "people": leader_c.category in A["people_categories"]}
        self.weight_hint = "rich"
        from scenes.combat_scene import CombatScene
        self.combat = CombatScene.begin(self, leader_c, enemies, "At the hideout," if n["kind"] == "lair" else "At the end of the trail,",
                                        reserves=reserves, wave=(A["camp_waves"]["every"], A["camp_waves"]["count"],
                                              A["camp_waves"]["quiet_start"].get(surprise, 1)), big="camp", initiated=True)
        return True
