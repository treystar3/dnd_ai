"""The party: hire adventurers at the guild for a fortified camp, direct them, and lose them.

The engine decides who is free, what they cost, how they fight and who falls. The model only reads the player's words and
describes the scene. The changes themselves (joining, leaving, promotion, going down) are made by services/party.py, which publishes
a typed event for each (engine/domain_events.py); this file reads the words and tells what happened.
"""

import random
import re

from engine import arcs, party as rules, quests
from engine.party import P
from llm.contracts import CompanionReply, PartyIntent
from llm.gateway import LLMError, generate
from scenes import party_prompts as ppr
from engine import clock, money
from ui import console

G = quests.G

# Cheap pre-filter: the model is only asked when the words could be about a party at all.
HINTS = ("recruit", "hire", "party", "adventurer", "hireling", "mercenar", "sellsword", "join me", "come with", "come along",
         "accompany", "back me up", "escort", "dismiss", "disband", "hold back", "stay back", "hang back", "wait outside",
         "stay behind", "bring them", "send them", "sword for hire", "swords for hire", "fighters", "companions from", "promote", "promotion", "rank up")

KEYWORDS = [
    ("promote", ("promote", "promotion", "rank up", "put their name forward")),
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
        from engine import mentor
        if mentor.tutorial_on(self.player):
            return []                                         # during her lesson the only adventurer for hire is Maren (f283), as the board holds only her hunt
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
        if self.companion_join(text):                       # (f309) hiring is the Board pane's alone; asking a friend along is still talk
            return True
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
        if kind in ("list", "hire"):
            return False                                    # (f309) talk about hiring is just talk; the hiring itself is done in the Board pane
        getattr(self, f"party_{kind}")(intent.target, text, offered)
        self.store.save_player(self.player)
        return True

    # ---------- people who join you because they want to ----------

    def companion_join(self, text: str) -> bool:
        """'Maren, come with me': a person of the world who likes you enough joins the party, unpaid, and stays until dismissed."""
        import re
        from engine import mentor
        low = text.lower()
        if self.combat or not self.store.npc_exists("maren") or not mentor.named(text):
            return False
        if not re.search(r"\b(join (me|us|my party)|come with (me|us)|come along|travel with (me|us)|walk with (me|us)|be in my party|recruit|hire)\b", low):
            return False
        if any(m.get("npc") == "maren" for m in self.player.party):
            return False
        n = self.store.load_npc("maren")
        if n.gone or not any(p.id == n.id for p in self.present):
            return False
        if len(self.player.party) >= P["max_party"]:
            console.note(f"Your party is full ({P['max_party']}).")
            return True
        if n.trust < 50:
            self.mentor_say("Not yet. Ask me again when I know you better.", beat="the player asks you to join them again but you do not trust them enough yet")
            return True
        old = self.store.load_place(n.location)
        old.residents = [r for r in old.residents if r != n.id]
        self.store.save_place(old)
        self.party_service.join({"id": "npc_maren", "name": n.name, "role": "fighter", "level": mentor.M["troll_sheet"]["level_mentor"], "rank": "A",
                                 "blurb": "Maren Holt, an A-rank adventurer", "npc": n.id, "sheet": "maren", "stay": True})
        self.store.save_player(self.player)
        console.note(f"{n.name} joins your party. She comes for her own reasons, and she is not paid. If she is hurt badly enough, she may not get up.")
        self.mentor_say("Fine. Someone has to keep you out of trouble. Lead on.", beat="the player has asked you to travel with them and you agree, dryly")
        return True

    def companion_home(self, npc_id: str) -> None:
        """A companion who leaves the party stays where they were let go, if that is a settlement; else they go back where they came from."""
        n = self.store.load_npc(npc_id)
        spot = next((pid for pid in (self.player.location, self.here_top()) if pid and self.store.load_place(pid).populated), "")
        st = self.store.load_place(spot) if spot else None
        if st:
            if n.id not in st.residents:
                st.residents.append(n.id)
                self.store.save_place(st)
            n.location = spot
            self.store.save_npc(n)
        else:
            home = self.store.load_place(n.location)
            if n.id not in home.residents:
                home.residents.append(n.id)
                self.store.save_place(home)

    # ---------- the actions ----------

    def temper_text(self, m: dict) -> str:
        return " and ".join(P["temperaments"][t]["say"] for t in m.get("temper", []) if t in P["temperaments"]) or "keeps to themselves"

    def hire_facts(self, m: dict) -> dict:
        """What the game knows about a permanent hire: the plain facts a voice would be given."""
        return {"temper": self.temper_text(m), "line": m.get("line", ""),                # never the motive: the player learns it from them
                "bond": rules.bond_tier(m), "health": round(rules.health_now(m, self.minutes) * 100)}

    def party_lines(self) -> list[str]:
        out = []
        for m in self.player.party:
            line = f"{m['name']} - {m['role']}, rank {m.get('rank') or rules.rank_of(m['level'])}, level {m['level']}"
            if m.get("permanent"):
                line += f", {rules.bond_tier(m)}"
                if rules.health_now(m, self.minutes) < 0.95:
                    line += f", {round(rules.health_now(m, self.minutes) * 100)}% health"
                if m.get("capped") and rules.next_rank(m.get("rank") or ""):
                    line += f", ready for promotion ({money.fmt(rules.promotion_fee(m))})"
            out.append(line)
        return out

    ROLE_NOTE = {"striker": "hits hard", "guardian": "sturdy, hits softly", "rogue": "quick, bleeds what it hits",
                 "healer": "mends you and your allies", "support": "bolsters your allies' strikes"}
    NAME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '.,!-]{0,23}$")

    def companion_row(self, comp) -> dict:
        from engine import combat
        from scenes.combat_scene import CombatScene, _Shape
        c = self.player.character
        shape = self.world.bestiary.get(comp.creature) or _Shape(comp)
        f = combat.companion_fighter(shape, c.level, f"ally_{comp.id}", comp.name, gift=comp.source == "gift")
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

    def adventurer_row(self, m: dict) -> dict:
        row = {"name": m["name"], "role": m["role"], "level": m["level"], "rank": m.get("rank") or rules.rank_of(m["level"])}
        if m.get("permanent"):
            row.update(self.hire_facts(m))
            row["promote"] = money.fmt(rules.promotion_fee(m)) if m.get("capped") and rules.next_rank(row["rank"]) else ""
        from engine import statsheet
        row["tip"] = statsheet.lines(self.member_sheet(m), notes=False)
        return row

    def party_data(self) -> dict:
        for note in rules.sync_levels(self.player.party, self.player.character.level):
            console.note(note)
        return {"companions": [self.companion_row(m) for m in self.player.character.companions],
                "adventurers": [self.adventurer_row(m) for m in self.player.party],
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
        if len(self.player.party) >= P["max_party"]:
            console.note(f"Your party is full ({P['max_party']}).")
            return
        console.note("Adventurers free to sign on (paid once, they stay with you until you part ways, and they grow as you do):")
        for i, m in enumerate(offered, 1):
            who = (m.get("people") or "human").replace("_", "-")
            console.note(f"  {i}. {m['name']} - {who} {m['role']}, rank {m['rank']}, level {m['level']}: {m['blurb']}, {self.temper_text(m)}. "
                         f"{money.fmt(m['fee'])}")
        if not offered:
            from engine import mentor
            console.note("  (only Maren, for now: say 'hire Maren')" if mentor.tutorial_on(self.player) and not self.mentor_in_party() else "  (nobody is free this week)")

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

    def party_hire(self, target: str, text: str, offered: list[dict], exact: dict | None = None) -> None:
        """exact: the one roster entry a pane button names (f329) - never matched by name, so two people sharing a first name are not both hired."""
        if len(self.player.party) >= P["max_party"]:
            console.note(f"Your party is full ({P['max_party']}).")
            return
        picks = [exact] if exact else self.party_pick(target, text, offered)
        if not picks:
            self.party_list(target, text, offered)
            console.note("Say who: a name, a number, or a role.")
            return
        from services.party import CannotAfford, PartyFull
        svc = self.party_service
        hired = []
        for m in picks:
            try:
                svc.hire(m, self.player.character.level)
            except PartyFull:
                break
            except CannotAfford:
                console.note(f"{m['name']} wants {money.fmt(m['fee'])} and you cannot cover it.")
                continue
            hired.append(m)
            console.note(f"{m['name']} takes the coin ({money.fmt(m['fee'])}) and signs on with you.")
        if hired:
            self.relations_seed()
            self.narrate("[THE GAME HAS DECIDED: the player hires " + ", ".join(f"{m['name']} ({m['blurb']})" for m in hired) +
                         " at the guild hall; they will travel with the player from now on. Their manner: " +
                         "; ".join(f"{m['name']} {self.temper_text(m)}" for m in hired) +
                         ".] Describe the brief meeting and the group setting out, in two or three sentences.", text)

    TALK_ACTIONS = re.compile(r"\b(hire|recruit|dismiss|disband|promote|attack|kill|hit|fight|steal|rob|search|skin|butcher|loot|walk|go|head|travel|buy|sell|rest|sleep)\b")

    def hire_people(self) -> list[tuple[str, str, str, str]]:
        """The hired adventurers travelling with the player, as people here: (id, name, description, what they are doing). Nobody is listed
        while the party holds back, or in a fight (the fight has its own view)."""
        if self.combat or self.player.party_mode != "with":
            return []
        out = []
        for m in self.player.party:
            if not m.get("permanent") or m.get("story"):
                continue
            rank = m.get("rank") or rules.rank_of(m["level"])
            out.append((f"hire:{m['id']}", m["name"], f"(a hired {m['role']}, rank {rank}) {m.get('blurb', '')} Manner: {self.temper_text(m)}.",
                        "travelling with the player, close at hand"))
        return out

    def hire_by_id(self, hid: str) -> dict | None:
        key = (hid or "").split(":", 1)[-1] if str(hid).startswith("hire:") else ""
        return next((m for m in self.player.party if key and str(m.get("id")) == key and m.get("permanent")), None)

    def hire_named(self, text: str) -> dict | None:
        """The permanent hire the player is speaking to by name, if any."""
        low = text.lower()
        for m in self.player.party:
            if m.get("permanent") and re.search(rf"\b{re.escape(m['name'].split()[0].lower())}\b", low):
                return m
        return None

    def hire_said_marks(self) -> dict:
        """What each hire has said so far, to see afterwards who spoke up on their own this turn."""
        return {m.get("name"): len(m.get("said", [])) + (hash(m["said"][-1]) if m.get("said") else 0) for m in self.player.party if m.get("permanent")}

    def note_hire_spoke(self, before: dict) -> None:
        """(f291) A hire who spoke up on their own after the player's line (banter, a remark, an errand) is who an answer goes to next."""
        for m in self.player.party:
            if m.get("permanent") and before.get(m.get("name")) != len(m.get("said", [])) + (hash(m["said"][-1]) if m.get("said") else 0):
                self._hire_last = (m.get("name"), self.store.meta.turn - 1)

    def hire_followup(self, text: str) -> dict | None:
        """(f290) A line that goes on with the hire the player spoke to last turn: no one named, not an action, said straight after. 'No,
        where are you from?' is still for Orrin, not for a stranger by the pillar."""
        last = getattr(self, "_hire_last", None)
        if not last or last[1] != self.store.meta.turn - 1:
            return None
        low = text.strip().lower()
        if self.TALK_ACTIONS.search(low) or any(self.npc_addressed(text, n) for n in self.present):
            return None
        return next((m for m in self.player.party if m.get("permanent") and m.get("name") == last[0]), None)

    def npc_addressed(self, text: str, npc) -> bool:
        from engine import mentor
        return mentor.addresses(text, npc)

    def hire_wants_talk(self, text: str) -> dict | None:
        if self.combat or text.lstrip().startswith(("#", "/")):
            return None
        m = self.hire_named(text)
        if not m:
            return self.hire_followup(text)
        first = m["name"].split()[0].lower()
        low = text.strip().lower()
        direct = "?" in text or low.startswith((first, f"ask {first}", f"tell {first}", f"say to {first}"))
        return m if direct or not self.TALK_ACTIONS.search(low) else None

    @staticmethod
    def hurt_words(h: float) -> str:
        return "badly hurt, and it shows in how you move" if h < 0.35 else ("hurt, and it shows" if h < 0.6 else "a little stiff from old hurts")

    def hire_now(self, m: dict, query: str | None = None) -> list[str]:
        """What presses on them at this moment, from the game's state. With a query, the background things (a promotion waiting, a mild
        ache) are only there when the moment is about them; a bad wound always is."""
        from engine import clock, relevance
        out = []
        h = rules.health_now(m, self.minutes)
        if h < 0.6 or (h < 0.95 and (query is None or relevance.pick(query, ["your wound, your health, how you are holding up"], 1))):
            out.append("you are " + self.hurt_words(h))
        mood = rules.mood_now(m, self.minutes)
        if mood:
            out.append(f"you are {mood}")
        last = self.player.party_last_fight or {}
        if last and self.minutes - last.get("minute", -10**9) <= 1440:
            how = "lost" if not last.get("won") else ("won, and it was a hard one" if last.get("hard") else "won easily")
            out.append(f"the last fight, {clock.describe_duration(self.minutes - last['minute'])} ago, was {how}")
        if m.get("warned"):
            out.append("you have told the player plainly that this might not be worth it")
        return out                                           # (f315) where they are, who is here and the board come with their truth view (hire_view)

    def hire_view(self, m: dict):
        """Their view of the moment from the truth layer (engine/truth.py): the same scene the narrator and the townsfolk read, as a hired
        adventurer may know it - the party by name, the townsfolk as the player knows them, the board wherever the guild's people are."""
        from engine import truth
        view = truth.scene_of(self).view(truth.viewer_for_hire(f"hire:{m['id']}"), "hire")
        console.debug(f"truth view for {m['name']}: " + ", ".join(f"{h.split(' (')[0].lower()} {len(l)}" for h, l in view.sections()))
        return view

    def hire_feeling(self, m: dict, text: str) -> str:
        """The situation that gives this moment real feeling for them, or ''."""
        from engine import relevance
        h = rules.health_now(m, self.minutes)
        from engine import quirks
        if relevance.pick(text, [quirks.Q["answer_told"]["about"]], 1, floor=0.6):
            return "painful_told"
        if h < 0.6:
            return "hurt_self"
        if m.get("warned"):
            return "warned_self"
        return ""

    def hire_subtext(self, m: dict, text: str) -> str:
        """What they feel and will not say, when there is real feeling in the moment."""
        from engine import quirks
        kind = self.hire_feeling(m, text)
        if not kind:
            return ""
        st = quirks.subtext(m, kind)
        return f"{quirks.Q['subtext_rule']}: {st}" if st else ""

    def hire_relation(self, m: dict) -> str:
        tier = rules.bond_tier(m)
        words = P["bond"]["regard"].get(tier, tier)
        return words + (f". {m['impression']}" if m.get("impression") else "")

    def companion_show(self, m: dict, shown: str, reply_to: str = "") -> None:
        """(f325) A companion's words on the page the way Maren's and the townsfolk's are: the narrator frames them with what they do as
        they speak - a sentence or two before and after, a single beat in a fight - under their name. Without the narrator, the words
        with their gesture as before. `shown` is quirks.shown's form: an optional (gesture) paragraph, then the speech."""
        import config
        speech, gesture = shown.strip(), ""
        if speech.startswith("(") and "\n" in speech:
            g, speech = speech.split("\n", 1)
            gesture, speech = g.strip().strip("()").strip(), speech.strip()
        elif speech.startswith("(") and speech.endswith(")") and speech.count("(") == 1:
            gesture, speech = speech.strip("()").strip(), ""
        name = m["name"]
        if speech and getattr(config, "NARRATED_DIALOGUE", True) and getattr(config, "VOICED_MENTOR", True):
            from llm.contracts import DialogueFrame
            from scenes import world_prompts as wp
            from scenes.voice import fresh
            in_fight = bool(self.combat)
            others = [f"{n.label()}: {n.activity}" for n in self.present][:4] + [f"{o['name']}: travelling with the player" for o in self.player.party
                                                                                 if o is not m and o.get("permanent") and not o.get("story")][:3]
            looks = f"({(m.get('people') or 'human').replace('_', '-')} {m.get('role', '')}, rank {m.get('rank', 'F')}) {m.get('blurb', '')}".strip()
            doing = "in the fight beside the player" if in_fight else "travelling with the player, close at hand"
            try:
                frame = fresh("dialogue_frame", wp.DIALOGUE_SYSTEM,
                              wp.dialogue_request(self.time_label(), self.place, others, name, looks, doing, self.temper_text(m), False,
                                                  reply_to or "(listening)", speech, gesture, False, self.recent_narration,
                                                  P["frame"]["fight" if in_fight else "talk"]),
                              DialogueFrame, self.recent_narration, fields=("before", "after"), max_tokens=300 if in_fight else 400)
                after = "" if in_fight else frame.after
                console.dialogue(frame.before, name, speech, after)
                self.remember_narration(" ".join(t for t in (frame.before, after) if t.strip()),
                                        {"type": "dialogue", "before": frame.before, "speaker": name, "speech": speech, "after": after})
                return
            except LLMError:
                pass
        console.say(shown, name)

    def hire_talk(self, m: dict, text: str) -> None:
        """What the player says to a hire: the model answers as them from who they are, how they are with the player, what presses now
        and what they remember. Anything worth keeping from the exchange is kept, on the same call."""
        from engine import banter
        self._hire_last = (m.get("name"), self.store.meta.turn)       # the next line may go on with them (hire_followup)
        console.debug(f"talk -> {m['name']} (hire, {m.get('role')}, rank {m.get('rank')}): mood={rules.mood_now(m, self.minutes)!r} "
                      f"relation={self.hire_relation(m)[:120]!r}")
        console.debug(f"  memories used: {rules.pick_memories(m, text, day=self.minutes // 1440)}")
        recent = m.setdefault("talk", [])
        player = self.player.character.name
        reply, gesture = "", ""
        from engine import quirks
        self.quirked(m)
        called = quirks.nickname(m) or player
        from engine import canon, context, convo
        before = convo.find(m, text)
        now = self.hire_now(m, text)
        day = self.minutes // 1440
        fix = ""
        from engine import voice_profile
        feeling = self.hire_feeling(m, text)
        how, core = self.companion_parts(m, text, emotion=voice_profile.emotion_for(feeling),
                                         relation=voice_profile.relation_kind(bond_tier=rules.bond_tier(m)), toward="the player")
        answer_to = None
        if feeling in quirks.Q["answer_told"]["when"]:          # they told them something that matters: it is answered first, whatever is felt
            answer_to = {"said": text, "scene": list(now)}
            now = [quirks.Q["answer_told"]["rule"]] + now
        view = self.hire_view(m)
        for attempt in range(2):
            ctx = {"recent": convo.others_lately(m.get("said", []), before), "member": m, "player": player,
                   "gesture_state": quirks.gesture_state(m, self.gesturers(m)), "answer_to": answer_to, "known": view.scene.known_words()}
            try:
                r = generate("hire_chat", ppr.TALK_SYSTEM,
                             ppr.talk_prompt(how, core, self.hire_relation(m), now, rules.pick_memories(m, text, day=self.minutes // 1440), recent[-8:], called, text,
                                             unsaid=banter.unsaid_rule(m.get("said", []), text) if not before else "",
                                             notes=quirks.voice_notes(m, solo=True), props=quirks.scene_props(m, self.place), leaned=quirks.leaned_on(m),
                                             subtext=self.hire_subtext(m, text), offers=self.material_for(m),
                                             again=convo.again_fact(before) if before else "",
                                             again_how=convo.again_rule(quirks.repeat_manner(m)) if before else "", fix=fix, truth_text=view.text()),
                             CompanionReply, temperature=0.8, max_tokens=320, retries=1, validation_context=ctx,
                             relaxed_context=dict(ctx, recent=[] if before else m.get("said", [])[-1:], answer_to=None))
            except LLMError:
                reply = P["temperaments"][(m.get("temper") or ["dry"])[0]].get("quip", "")
                break
            fix = canon.settle(canon.read(m, m["name"], r.speech, text, day), attempt)
            if fix:                                             # it contradicted what is true of them: once more, told what is true; nothing kept
                continue
            reply, gesture = r.speech, r.gesture
            console.debug(f"{m['name']} (hire): remember={r.remember!r} impression={r.impression!r}")
            if r.remember:
                rules.remember(m, day, r.remember, 2, kind="fact")
            if r.impression:
                m["impression"] = r.impression
            break
        if reply:
            context.note_spoken(m, reply, self.minutes, self.companion_concerns(m))
            convo.record(m, text, reply, self.minutes)
        if gesture and not reply:
            console.narrate(f"{m['name']} {gesture.rstrip('.')}.")
        elif reply:
            self.companion_show(m, quirks.shown(reply, gesture, m["name"]), text)          # (f325) framed like Maren's and the townsfolk's
            rules.said(m, reply)
        quirks.note_line(m, gesture)
        said = [["Player", text[:250]]] + ([[m["name"].split()[0], reply[:300]]] if reply else ([[m["name"].split()[0], f"({gesture})"]] if gesture else []))
        recent += said
        del recent[:-12]
        if self.player.party_mode == "with":               # (f290) the others travelling with you heard it: 'what about you?' has something to follow on from
            for o in self.player.party:
                if o is m or not o.get("permanent") or o.get("story"):
                    continue
                log = o.setdefault("talk", [])
                log += [[f"Player (to {m['name'].split()[0]})", text[:250]]] + said[1:]
                del log[:-12]
        if reply and m.get("permanent"):                    # the others travelling along heard it: whether any joins in is theirs to have reason for
            self.chime_in(m, text, reply)
        day = self.minutes // 1440
        if m.get("talked_day") != day:
            m["talked_day"] = day
            m["bond"] = m.get("bond", 0) + 1
        self.store.save_player(self.player)

    def party_promote(self, target: str, text: str, offered: list[dict]) -> None:
        hay = f"{target} {text}".lower()
        mine = [m for m in self.player.party if m.get("permanent")]
        pick = [m for m in mine if m["name"].lower() in hay or m["name"].split()[0].lower() in hay or m["role"] in hay] or \
               ([mine[0]] if len(mine) == 1 else [])
        if not pick:
            console.note("Say who: a name, or a role." if mine else "You have no hired adventurers to promote.")
            return
        m = pick[0]
        why = rules.promotion_block(m)
        if why:
            console.note(why)
            return
        from services.party import CannotAfford
        try:
            old, _, fee = self.party_service.promote(m, self.player.character.level)
        except CannotAfford as e:
            console.note(f"Putting {m['name']} forward costs {money.fmt(e.fee)} and you cannot cover it.")
            return
        console.note(f"{m['name']} is promoted from {old}-rank to {m['rank']}-rank ({money.fmt(fee)}). Level {m['level']}.")
        self.narrate(f"[THE GAME HAS DECIDED: the player pays for {m['name']} to be raised from {old}-rank to {m['rank']}-rank at the guild. "
                     f"Their manner: {self.temper_text(m)}.] Describe the moment in two sentences.", text)

    def party_dismiss(self, target: str, text: str, offered: list[dict]) -> None:
        if not self.player.party:
            console.note("You have no party.")
            return
        hay = f"{target} {text}".lower()
        gone = [m for m in self.player.party if m["name"].lower() in hay or m["name"].split()[0].lower() in hay or m["role"] in hay]
        if not gone or re.search(r"\b(all|everyone|party|disband)\b", hay):
            gone = list(self.player.party)
        if any(m.get("tutorial") for m in gone):
            console.note("Maren shakes her head. \"Not until the job is done.\"")
            gone = [m for m in gone if not m.get("tutorial")]
            if not gone:
                return
        gone = self.party_service.dismiss(gone)
        for m in gone:
            if m.get("npc") and m.get("stay"):
                self.companion_home(m["npc"])
        console.note(f"{', '.join(m['name'] for m in gone)} part ways with you. No refund.")
        self.narrate(f"[THE GAME HAS DECIDED: the player sends {', '.join(m['name'] for m in gone)} away; they leave.] Describe it in a sentence.", text)

    def party_hold(self, target: str, text: str, offered: list[dict]) -> None:
        if not self.player.party:
            console.note("You have no party.")
            return
        self.party_service.set_mode("hold")
        console.note("Your party will hold back and come running if the alarm goes up. They make no noise for you to answer for.")

    def party_with(self, target: str, text: str, offered: list[dict]) -> None:
        if not self.player.party:
            console.note("You have no party.")
            return
        self.party_service.set_mode("with")
        console.note("Your party moves beside you. Together you are loud.")

    # ---------- what happens to them ----------

    def party_after_fight(self, fallen: list, fighters=(), won: bool = False, hard: bool = False) -> None:
        """Who went down, who limps on, whose trust moved. Old-style hirelings who went down do not get back up; a permanent hire may be carried out."""
        import random
        if not self.player.party:
            return
        svc = self.party_service
        ids = {a.id for a in fallen}
        by_id = {a.id: a for a in fighters}
        seen, changed = [], False
        for m in list(self.player.party):
            if m.get("npc") or m.get("tutorial"):
                continue
            fid = f"ally_{m['id']}"
            if fid in ids:
                if m.get("permanent"):                           # decided the moment they went down (combat), else now, after the fact
                    fate = svc.decide_down(m, random, in_fight=False)
                    if fate == "carried":
                        m.pop("down_fate", None)
                        seen.append((m, 0.05))
                        console.note(f"{m['name']} is carried out of the fight, badly hurt but alive.")
                        continue
                    svc.bury(m)
                else:
                    svc.kill(m)                                  # an old-style hireling who went down does not get back up
                console.note(f"{m['name']} has fallen.")
                changed = True
            elif m.get("permanent") and fid in by_id:
                a = by_id[fid]
                seen.append((m, a.hp / a.max_hp if a.max_hp else 1.0))
        for note in rules.after_fight(seen, won, hard, self.minutes):
            console.note(note)
        for m, _ in seen:
            m["fights_total"] = m.get("fights_total", 0) + 1
        if seen:
            self.habits("fight_end")
        if seen or ids:
            self.player.party_last_fight = {"minute": self.minutes, "won": won, "hard": hard,
                                            "hurt": [m["name"] for m, frac in seen if frac < 0.6], "carried": [m["name"] for m, frac in seen if frac <= 0.05],
                                            "hurt_ids": [m["id"] for m, frac in seen if frac < 0.6], "carried_ids": [m["id"] for m, frac in seen if frac <= 0.05],
                                            "fallen": [a.name for a in fallen if a.id.startswith("ally_") and a.id not in {f"ally_{m['id']}" for m, _ in seen}],
                                            "fallen_ids": [a.id[len("ally_"):] for a in fallen if a.id.startswith("ally_") and a.id not in {f"ally_{m['id']}" for m, _ in seen}]}
            self._banter_due = "fight"
            if hard and won:
                for m, _ in seen:
                    self.relations_shift(m, 1)
            crew = [m for m, _ in seen if not m.get("story")]
            for i, a in enumerate(crew):
                for b in crew[i + 1:]:
                    carried = [x["name"].split()[0] for x, f in seen if x in (a, b) and f <= 0.05]
                    if carried:
                        self.pair_event(a, b, f"{carried[0]} was carried out of a fight and the other saw it happen.", "heavy")
                    elif hard and won:
                        self.pair_event(a, b, "came through a hard fight side by side.")
                    elif not won:
                        self.pair_event(a, b, "came off worse in a fight together.", "personal")
        if changed or seen:
            self.store.save_player(self.player)

    def party_disband(self, arc_id: str | None, why: str) -> None:
        gone = self.party_service.disband(arc_id, why)
        if gone:
            console.note(f"{', '.join(m['name'] for m in gone)} {'takes' if len(gone) == 1 else 'take'} their leave ({why}).")
            self.store.save_player(self.player)
