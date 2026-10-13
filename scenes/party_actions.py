"""The party: hire adventurers at the guild for a fortified camp, direct them, and lose them.

The engine decides who is free, what they cost, how they fight and who falls. The model only reads the player's words and
describes the scene.
"""

import re

from engine import arcs, party as rules, quests
from engine.party import P
from llm.contracts import PartyIntent
from llm.gateway import LLMError, generate
from scenes import party_prompts as ppr
from engine import clock, money
from ui import console

G = quests.G

# Cheap pre-filter: the model is only asked when the words could be about a party at all.
HINTS = ("recruit", "hire", "party", "adventurer", "hireling", "mercenar", "sellsword", "join me", "come with", "come along",
         "accompany", "back me up", "escort", "dismiss", "disband", "hold back", "stay back", "hang back", "wait outside",
         "stay behind", "bring them", "send them", "sword for hire", "swords for hire", "fighters", "companions from")

KEYWORDS = [
    ("dismiss", ("dismiss", "disband", "send them away", "send them home", "let them go", "part ways", "release the party")),
    ("hold", ("wait outside", "hold back", "stay back", "hang back", "stay behind", "keep them back", "hold the party", "wait here")),
    ("with", ("bring them in", "come with me", "come along", "stay close", "all together", "march together", "with me")),
    ("hire", ("hire", "recruit", "sign up", "bring along", "take with", "engage")),
    ("list", ("who is available", "who's available", "what adventurers", "roster", "see the adventurers", "list", "who is for hire", "who can i hire")),
    ("status", ("my party", "who is with me", "who's with me")),
]


def keyword_party(text: str) -> str | None:
    low = text.lower()
    for kind, words in KEYWORDS:
        if any(w in low for w in words):
            return kind
    return None


class PartyActions:

    # ---------- when the guild will send help ----------

    def party_wanted(self):
        """The (data, arc, node) of a story that has led to a fortified camp, else None."""
        data, arc = self.my_arc()
        n = arcs.current(arc) if arc else None
        if not n or n["kind"] not in ("lair", "boss"):
            return None
        return data, arc, n

    def at_guild_hall(self) -> bool:
        return self.place.type == "guild" and bool(self.rank)

    def party_notice(self) -> None:
        if not self.at_guild_hall() or len(self.player.party) >= P["max_party"]:
            return
        if not self.party_wanted():
            return
        console.note("The clerk has heard where your trail leads: a fortified camp. The guild keeps adventurers who will go with you "
                     "for a fee - say 'recruit help' to see who is free.")

    def party_roster(self) -> list[dict]:
        c = self.player.character
        coins = G["ranks"][self.rank or "F"]["reward"]["coins"]
        return rules.roster(self.store.meta.seed, self.place.id, self.minutes // 1440, c.level, coins, self.player.party_used)

    # ---------- reading the player ----------

    def party_read(self, text: str, offered: list[dict]) -> PartyIntent:
        try:
            return generate("party_intent", ppr.SYSTEM,
                            ppr.user(text, [f"{i}. {m['name']} ({m['role']})" for i, m in enumerate(offered, 1)],
                                     [f"{m['name']} ({m['role']})" for m in self.player.party]),
                            PartyIntent, temperature=0.2, max_tokens=100)
        except LLMError:
            return PartyIntent(kind=keyword_party(text) or "none")

    def party_turn(self, text: str) -> bool:
        """Handle hiring and directing a party. False means it is not about the party."""
        if self.combat or text.lstrip().startswith(("#", "/")):
            return False
        low = text.lower()
        if not any(h in low for h in HINTS):
            return False
        here = self.at_guild_hall()
        if not here and not self.player.party:
            return False
        offered = self.party_roster() if here else []
        intent = self.party_read(text, offered)
        kind = intent.kind
        if kind == "none":
            return False
        if kind in ("list", "hire") and not here:
            console.note("Hirelings are found at the adventurers' guild hall.")
            return True
        getattr(self, f"party_{kind}")(intent.target, text, offered)
        self.store.save_player(self.player)
        return True

    # ---------- the actions ----------

    def party_lines(self) -> list[str]:
        return [f"{m['name']} - {m['role']}, level {m['level']}" for m in self.player.party]

    ROLE_NOTE = {"striker": "hits hard", "guardian": "sturdy, hits softly", "rogue": "quick, bleeds what it hits",
                 "healer": "mends you and your allies", "support": "bolsters your allies' strikes"}
    NAME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '.,!-]{0,23}$")

    def companion_row(self, comp) -> dict:
        from engine import combat
        from scenes.combat_scene import CombatScene, _Shape
        c = self.player.character
        shape = self.world.bestiary.get(comp.creature) or _Shape(comp)
        spirit = None if comp.creature in self.world.bestiary else (comp.tier, comp.role)
        f = combat.companion_fighter(shape, c.level, f"ally_{comp.id}", comp.name, spirit, gift=comp.source == "gift")
        if comp.dead:
            state = "Dead - only a revival brings it back"
        elif comp.fallen:
            wait = max(0, comp.recover_at - self.minutes)
            state = "Fallen - back on its feet in " + clock.describe_duration(wait) if wait else "Fallen - ready to rise"
        else:
            state = "Ready"
        role = getattr(comp.role, "value", comp.role) or "striker"
        return {"id": comp.id, "name": comp.name, "role": role, "note": self.ROLE_NOTE.get(role, ""), "kind": comp.kind or "beast",
                "level": c.level, "state": state, "ok": comp.active, "hp": round(f.max_hp), "damage": round(f.weapon_damage),
                "armor": round(f.armor), "ward": round(f.ward), "description": comp.description}

    def party_data(self) -> dict:
        return {"companions": [self.companion_row(m) for m in self.player.character.companions],
                "adventurers": [{"name": m["name"], "role": m["role"], "level": m["level"]} for m in self.player.party],
                "mode": ("moving beside you" if self.player.party_mode == "with" else "holding back, ready to come if there is trouble")
                        if self.player.party else ""}

    def show_party(self) -> None:
        data = self.party_data()
        if console.panel("party", data):
            return
        if not data["companions"] and not data["adventurers"]:
            console.note("You have no party.")
            return
        for m in data["companions"]:
            console.note(f"  {m['name']} - {m['role']} ({m['kind']}), level {m['level']}: {m['hp']} health, {m['damage']} damage, "
                         f"{m['armor']} armor, {m['ward']} ward. {m['state']}.")
        if data["adventurers"]:
            console.note("Your party: " + "; ".join(self.party_lines()) + f". They are {data['mode']}.")
        if data["companions"]:
            console.note("  #name <companion> = <new name>   to rename one")

    def party_status(self, target: str, text: str, offered: list[dict]) -> None:
        self.show_party()

    def rename_companion(self, text: str) -> None:
        """#compname <id> <new name> from the pane, or #name <companion> = <new name> from the keyboard."""
        c = self.player.character
        raw = text.split(maxsplit=1)[1] if " " in text.strip() else ""
        if "=" in raw:
            who, new = (x.strip() for x in raw.split("=", 1))
            comp = next((m for m in c.companions if m.name.lower() == who.lower() or m.id == who), None) or \
                next((m for m in c.companions if who and who.lower() in m.name.lower()), None)
        else:
            parts = raw.split(maxsplit=1)
            comp = next((m for m in c.companions if parts and m.id == parts[0]), None)
            new = parts[1].strip() if len(parts) > 1 else ""
        if not comp:
            console.note("You have no such companion. (#name <companion> = <new name>)")
        elif not self.NAME_OK.match(new):
            console.note("A name is 1 to 24 letters, numbers, spaces and simple punctuation.")
        elif any(o is not comp and o.name.lower() == new.lower() for o in c.companions) or \
                any(m["name"].lower() == new.lower() for m in self.player.party):
            console.note(f"Someone in your party is already called {new}.")
        else:
            old, comp.name = comp.name, new
            self.store.save_player(self.player)
            console.note(f"{old} is now called {new}.")
        with console.scope("#party"):
            self.show_party()

    def party_list(self, target: str, text: str, offered: list[dict]) -> None:
        if not self.party_wanted():
            console.note("The clerk shrugs: the guild sends fighters out on a fortified job, and you have word of none yet. "
                         "Come back when your trail leads to a camp.")
            return
        if len(self.player.party) >= P["max_party"]:
            console.note(f"Your party is full ({P['max_party']}).")
            return
        console.note("Free adventurers (paid up front, they stay until this job is done):")
        for i, m in enumerate(offered, 1):
            console.note(f"  {i}. {m['name']} - {m['role']}, level {m['level']}: {m['blurb']}. {money.fmt(m['fee'])}")
        if not offered:
            console.note("  (nobody is free this week)")

    def party_pick(self, target: str, text: str, offered: list[dict]) -> list[dict]:
        pool = offered
        if not pool:
            return []
        hay = f"{target} {text}".lower()
        if re.search(r"\b(all|everyone|them all|as many)\b", hay):
            return list(pool)
        got = [m for m in pool if m["name"].lower() in hay or m["name"].split()[0].lower() in hay]
        for m in pool:
            if m["role"] in hay and m not in got:
                got.append(m)
        for num in re.findall(r"\b(\d+)\b", target or ""):
            if 1 <= int(num) <= len(pool) and pool[int(num) - 1] not in got:
                got.append(pool[int(num) - 1])
        return got

    def party_hire(self, target: str, text: str, offered: list[dict]) -> None:
        wanted = self.party_wanted()
        if not wanted:
            console.note("The guild will not send fighters out without a fortified job to send them to.")
            return
        if len(self.player.party) >= P["max_party"]:
            console.note(f"Your party is full ({P['max_party']}).")
            return
        picks = self.party_pick(target, text, offered)
        if not picks:
            self.party_list(target, text, offered)
            console.note("Say who: a name, a number, or a role.")
            return
        data, arc, n = wanted
        c = self.player.character
        hired = []
        for m in picks:
            if len(self.player.party) >= P["max_party"]:
                break
            if c.coins < m["fee"]:
                console.note(f"{m['name']} wants {money.fmt(m['fee'])} and you cannot cover it.")
                continue
            c.coins -= m["fee"]
            member = {k: m[k] for k in ("id", "name", "role", "level", "blurb")}
            member["arc"] = arc["id"]
            self.player.party.append(member)
            self.player.party_used.append(f"{m['hall']}:{m['id']}")
            self.player.party_used = self.player.party_used[-80:]
            hired.append(m)
            console.note(f"{m['name']} takes the coin ({money.fmt(m['fee'])}) and joins you.")
        if hired:
            self.narrate("[THE GAME HAS DECIDED: the player hires " + ", ".join(f"{m['name']} ({m['blurb']})" for m in hired) +
                         " at the guild hall; they will go with the player to the camp.] Describe the brief meeting and the "
                         "group setting out, in two or three sentences.", text)

    def party_dismiss(self, target: str, text: str, offered: list[dict]) -> None:
        if not self.player.party:
            console.note("You have no party.")
            return
        hay = f"{target} {text}".lower()
        gone = [m for m in self.player.party if m["name"].lower() in hay or m["name"].split()[0].lower() in hay or m["role"] in hay]
        if not gone or re.search(r"\b(all|everyone|party|disband)\b", hay):
            gone = list(self.player.party)
        for m in gone:
            self.player.party.remove(m)
        console.note(f"{', '.join(m['name'] for m in gone)} part ways with you. No refund.")
        self.narrate(f"[THE GAME HAS DECIDED: the player sends {', '.join(m['name'] for m in gone)} away; they leave.] Describe it in a sentence.", text)

    def party_hold(self, target: str, text: str, offered: list[dict]) -> None:
        if not self.player.party:
            console.note("You have no party.")
            return
        self.player.party_mode = "hold"
        console.note("Your party will hold back and come running if the alarm goes up. They make no noise for you to answer for.")

    def party_with(self, target: str, text: str, offered: list[dict]) -> None:
        if not self.player.party:
            console.note("You have no party.")
            return
        self.player.party_mode = "with"
        console.note("Your party moves beside you. Together you are loud.")

    # ---------- what happens to them ----------

    def party_after_fight(self, fallen: list) -> None:
        """Hirelings who went down in the fight do not get back up."""
        if not self.player.party or not fallen:
            return
        ids = {a.id for a in fallen}
        lost = [m for m in self.player.party if f"ally_{m['id']}" in ids and not m.get("npc")]
        for m in lost:
            self.player.party.remove(m)
            console.note(f"{m['name']} has fallen.")
        if lost:
            self.store.save_player(self.player)

    def party_disband(self, arc_id: str | None, why: str) -> None:
        keep = [m for m in self.player.party if arc_id is not None and m.get("arc") != arc_id]
        gone = [m for m in self.player.party if m not in keep]
        self.player.party = keep
        if gone:
            console.note(f"{', '.join(m['name'] for m in gone)} {'takes' if len(gone) == 1 else 'take'} their leave ({why}).")
            if not keep:
                self.player.party_mode = "with"
            self.store.save_player(self.player)
