"""The adventurers' guild and quests in play: joining, the board, contracts, turn-ins, ranks and perks,
and personal requests from the people of the world."""

import random
import re

from core.models import KeyItem
from engine import clock, combat, inventory as inv, leveling, money, quests
from npc.models import Memory
from ui import console

G = quests.G


class GuildActions:

    # ---------- state ----------

    @property
    def rank(self) -> str:
        return self.player.guild_rank

    def guild_perks(self) -> dict:
        return quests.perks(self.rank)

    GUILD_ROLES = ("guild_clerk", "guild_master", "guild_contractor", "guild_instructor", "quartermaster")

    def guild_knowledge(self, npc) -> list[str]:
        """What a guild person knows for certain about how the guild works, from its real rules, and (for the clerk and master, who keep the
        register) where this stranger stands. Without it the model has the clerk shrug at a question every clerk could answer."""
        if npc.role not in self.GUILD_ROLES:
            return []
        out = [f"THE GUILD'S RULES (you know them well; answer questions about them plainly and exactly, with these numbers): joining costs "
               f"{money.words(G['joining_fee'])} at the clerk's desk and starts you at rank F. Ranks run F, E, D, C, B, A, S. "
               f"A member holds {G['base_active']} contracts at once. Only the guild's own contracts count toward promotion; "
               "personal requests from townsfolk pay less and do not count."]
        for letter in quests.LETTERS[1:]:
            need = G["ranks"][letter]["requires"]
            below = quests.LETTERS[quests.LETTERS.index(letter) - 1]
            out.append(f"Rank {letter}: you must be level {need['level']} and have finished {need['completed']} guild contracts at rank {below} or higher. "
                       f"It brings: {quests.describe_perks(letter)}.")
        if npc.role in ("guild_clerk", "guild_master"):
            if not self.rank:
                out.append("The stranger has not joined the guild.")
            else:
                nxt = quests.next_rank(self.rank)
                if nxt:
                    need = G["ranks"][nxt]["requires"]
                    counted = sum(n for l, n in self.player.guild_done.items() if quests.LETTERS.index(l) >= quests.LETTERS.index(self.rank))
                    lvl = self.player.character.level
                    lvl_need, done_need = need["level"], need["completed"]
                    lvl_text = "met" if lvl >= lvl_need else f"{lvl_need - lvl} levels to go"
                    done_text = "met" if counted >= done_need else f"{done_need - counted} more to go"
                    out.append(f"The stranger is a rank {self.rank} member, level {lvl}, with {counted} qualifying contracts finished. "
                               f"For rank {nxt} they need level {lvl_need} ({lvl_text}) and {done_need} contracts ({done_text}). "
                               "Your register shows this; tell them.")
                else:
                    out.append(f"The stranger holds the highest rank, {self.rank}.")
        return out

    def clerk_here(self):
        return next((n for n in self.present if n.role == "guild_clerk"), None)

    def guild_place_id(self) -> str | None:
        """The hall you're standing in, or else the first one (the home hall)."""
        if self.place.type == "guild":
            return self.place.id
        return next((p.id for p in self.world.places.values() if p.type == "guild"), None)

    def ensure_board(self) -> list[dict]:
        gid = self.guild_place_id()
        if not gid:
            return []
        state = self.store.load_place(gid)
        day = clock.day(self.minutes)
        if state.board_day < 0 or day >= state.board_day + G["board_refresh_days"]:
            tier = quests.hall_tier(self.world, gid)
            size = G["board_size"] + self.guild_perks()["board"] + tier["size"]
            rng = random.Random(f"{self.store.meta.seed}:board:{gid}:{day}")
            kept = []
            if state.board_day >= 0:
                passes = min(3, max(1, (day - state.board_day) // max(1, G["board_refresh_days"])))
                dungeons = {d["id"] for d in self.store.load_dungeons()}
                for q in state.board:
                    if q.get("dungeon") and q["dungeon"] not in dungeons:
                        continue
                    if q.get("thread") or rng.random() < G["board_keep"] ** passes:
                        kept.append(q)
            state.board = quests.post_board(self.world, self.store, self.minutes, size, rng, self.rank or "F", gid,
                                            existing=kept[:size])
            state.board_day = day
            self.store.save_place(state)
        return state.board

    # ---------- display ----------

    def board_data(self) -> dict:
        """Everything the board pane shows, as plain data: each posting with whether it can be taken now and why not,
        the contracts held, and any personal request someone here has for the player."""
        c = self.player.character
        board = self.ensure_board()
        bonus = self.guild_perks()["reward_bonus"]
        rank = self.rank or "F"
        clerk = self.clerk_here()
        limit = G["base_active"] + self.guild_perks()["active"]
        held_guild = sum(1 for x in self.player.quests if x["guild"])
        looking = any(x["kind"] == "missing" for x in self.player.quests)
        postings = []
        for n, q in enumerate(board, 1):
            coins, xp = quests.reward(q["letter"], True, bonus)
            mult = q.get("multiplier", 1)
            why = ""
            if not self.rank:
                why = "Join the guild first."
            elif not clerk:
                why = "The clerk must be here to record it."
            elif not quests.at_or_below(q["letter"], rank):
                why = f"Rank {q['letter']} - you are rank {self.rank}."
            elif held_guild >= limit:
                why = f"You hold {limit} guild contracts already."
            elif q["kind"] == "missing" and looking:
                why = "You are already looking for someone."
            postings.append({"id": q["id"], "n": n, "letter": q["letter"], "title": q["title"],
                             "reward": money.fmt(round(coins * mult)), "xp": round(xp * mult),
                             "limit": "no time limit" if q.get("deadline", 1) is None
                             else f"{G['ranks'][q['letter']]['deadline_days'] + q.get('extra_days', 0)} days",
                             "ok": not why, "why": why})
        held = [{"id": q["id"], "n": n, "letter": q["letter"], "title": q["title"], "guild": bool(q["guild"]),
                 "line": quests.progress_line(q, self.pack, self.minutes)}
                for n, q in enumerate(self.player.quests, 1)]
        requests = [{"npc": n.id, "name": n.label(), "letter": n.quest_offer["letter"], "title": n.quest_offer["title"]}
                    for n in self.present if n.quest_offer]
        return {"member": bool(self.rank), "rank": self.rank, "fee": money.fmt(G["joining_fee"]),
                "fee_ok": c.coins >= G["joining_fee"], "clerk": bool(clerk), "postings": postings, "held": held,
                "requests": requests, "purse": money.fmt(c.coins)}

    def show_board(self) -> None:
        data = self.board_data()
        if console.panel("board", data):                   # the window draws this one with Accept buttons
            return
        board = self.ensure_board()
        bonus = self.guild_perks()["reward_bonus"]
        rank = self.rank or "F"
        console.note(f"THE CONTRACT BOARD - your rank: {self.rank or 'not a member (joining fee ' + money.words(G['joining_fee']) + ')'}")
        for n, q in enumerate(board, 1):
            coins, xp = quests.reward(q["letter"], True, bonus)
            coins, xp = round(coins * q.get("multiplier", 1)), round(xp * q.get("multiplier", 1))
            lock = "" if quests.at_or_below(q["letter"], rank) else "  (above your rank)"
            console.note(f"  {n}. [{q['letter']}] {q['title']} - {money.fmt(coins)}, {xp} XP, "
                         f"{'no time limit' if q.get('deadline', 1) is None else str(G['ranks'][q['letter']]['deadline_days'] + q.get('extra_days', 0)) + ' days'}{lock}")
        if not board:
            console.note("  (nothing posted)")

    def board_click(self, text: str) -> None:
        """The pane's hidden commands:  #boardaccept <posting id>   #boardabandon <contract id>   #boardrequest <npc id>   #boardjoin."""
        from llm.contracts import ActionIntent
        parts = text.split()
        cmd = parts[0].lower()
        if cmd == "#boardaccept" and len(parts) >= 2:
            board = self.ensure_board()
            n = next((i for i, q in enumerate(board, 1) if q["id"] == parts[1]), 0)
            if n:
                self.on_accept_quest(ActionIntent(kind="accept_quest", item=str(n)), "")
            else:
                console.note("That contract is no longer on the board.")
        elif cmd == "#boardabandon" and len(parts) >= 2:
            n = next((i for i, q in enumerate(self.player.quests, 1) if q["id"] == parts[1]), 0)
            if n:
                self.on_abandon_quest(ActionIntent(kind="abandon_quest", item=str(n)), "")
            else:
                console.note("You no longer hold that.")
        elif cmd == "#boardrequest" and len(parts) >= 2:
            npc = next((x for x in self.present if x.id == parts[1] and x.quest_offer), None)
            if npc:
                self.take_personal(npc)
            else:
                console.note("That request is no longer open.")
        elif cmd == "#boardjoin":
            self.on_join_guild(ActionIntent(kind="join_guild"), "")
        self.halted = False
        with console.scope("#board"):
            self.show_board()

    def show_quests(self) -> None:
        if not self.player.quests:
            console.note("You have no contracts or requests in hand.")
        for q in self.player.quests:
            console.note(self.arc_lines(q) or quests.progress_line(q, self.pack, self.minutes))
        if self.rank:
            nxt = quests.next_rank(self.rank)
            if nxt:
                need = G["ranks"][nxt]["requires"]
                counted = sum(n for l, n in self.player.guild_done.items()
                              if quests.LETTERS.index(l) >= quests.LETTERS.index(self.rank))
                console.note(f"Guild rank {self.rank}. To reach {nxt}: level {need['level']} (you are "
                             f"{self.player.character.level}), {need['completed']} contracts at {self.rank} or higher "
                             f"(you have {counted}).")

    # ---------- joining and contracts ----------

    def on_join_guild(self, intent, text: str) -> None:
        clerk = self.clerk_here()
        c = self.player.character
        if not clerk:
            console.note("You'd need to find the guild clerk to sign the register.")
            self.halted = True
            return
        if self.rank:
            console.note(f"You're already a member, rank {self.rank}.")
            return
        if c.coins < G["joining_fee"]:
            console.note(f"The joining fee is {money.words(G['joining_fee'])}; you have {money.words(c.coins)}.")
            self.halted = True
            return
        c.coins -= G["joining_fee"]
        self.player.guild_rank = "F"
        self.give_badge("F")
        clerk.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                     text="Signed the stranger into the guild register at rank F."))
        self.store.save_npc(clerk)
        self.store.save_player(self.player)
        console.note(f"You join the adventurers' guild at rank F. Paid {money.fmt(G['joining_fee'])}. "
                     "Type #board to see the contracts, #quests for yours.")
        self.narrate(f"The player pays {clerk.label()} the joining fee and signs the guild register. They are given a "
                     "rank-F guild badge.", text)

    def give_badge(self, letter: str) -> None:
        c = self.player.character
        c.key_items = [k for k in c.key_items if k.id != "guild_badge"]
        c.key_items.append(KeyItem(id="guild_badge", name=f"guild badge (rank {letter})",
                                   description=f"A stamped tin badge marking a rank-{letter} member of the adventurers' guild.",
                                   source="the adventurers' guild", day=clock.day(self.minutes)))

    def pick_posting(self, board: list[dict], words: str) -> dict | None:
        m = re.search(r"\b(\d+)\b", words)
        if m and 1 <= int(m.group(1)) <= len(board):
            return board[int(m.group(1)) - 1]
        best, score = None, 0
        for q in board:
            hit = sum(1 for w in re.findall(r"[a-z]+", words.lower()) if len(w) > 3 and w[:5] in q["title"].lower())
            if hit > score:
                best, score = q, hit
        return best

    def on_accept_quest(self, intent, text: str) -> None:
        npc = next((n for n in self.present if n.id == intent.target and n.quest_offer), None) or \
            next((n for n in self.present if n.quest_offer), None)
        if npc and not self.clerk_here():
            self.take_personal(npc)
            return
        if not self.rank:
            console.note(f"Only guild members can take contracts. Joining costs {money.words(G['joining_fee'])} - "
                         "ask the clerk.")
            self.halted = True
            return
        if not self.clerk_here():
            console.note("Contracts are taken from the board, with the clerk to record them.")
            self.halted = True
            return
        board = self.ensure_board()
        q = self.pick_posting(board, f"{intent.item} {text}")
        if not q:
            self.show_board()
            self.halted = True
            return
        if not quests.at_or_below(q["letter"], self.rank):
            console.note(f"That's a rank-{q['letter']} contract; you're rank {self.rank}.")
            self.halted = True
            return
        if q["kind"] == "delve":
            dd = next((x for x in self.store.load_dungeons() if x["id"] == q.get("dungeon")), None)
            if dd is None or q.get("floor", 0) >= len(dd["floors"]):
                console.note("That posting is out of date - the place has been remade. The clerk strikes it from the board.")
                board[:] = [x for x in board if x is not q]
                self.halted = True
                return
        limit = G["base_active"] + self.guild_perks()["active"]
        if sum(1 for x in self.player.quests if x["guild"]) >= limit:
            console.note(f"You can hold {limit} guild contracts at once - finish or abandon one first.")
            self.halted = True
            return
        if q["kind"] == "missing" and any(x["kind"] == "missing" for x in self.player.quests):
            console.note("You are already looking for someone. Finish or drop that contract first.")
            self.halted = True
            return
        board.remove(q)
        gid = self.guild_place_id()
        state = self.store.load_place(gid)
        state.board = board
        self.store.save_place(state)
        days = G["ranks"][q["letter"]]["deadline_days"] + q.get("extra_days", 0)
        q["deadline"] = None if q.get("deadline", 1) is None else self.minutes + days * 1440
        if q["kind"] == "deliver":
            self.player.character.key_items.append(KeyItem(
                id=f"quest_{q['id']}", name=q["item"], description=q["item_description"], kind="quest",
                source="the adventurers' guild", day=clock.day(self.minutes), for_whom=q["to_role"].replace("_", " ")))
        self.player.quests.append(q)
        self.store.save_player(self.player)
        console.note(f"Contract taken: [{q['letter']}] {q['title']}. "
                     + ("No time limit." if q["deadline"] is None else f"Due in {days} days."))
        if q["kind"] == "missing":
            q["hall"] = gid
            self.start_arc(q)
            self.store.save_player(self.player)

    def on_abandon_quest(self, intent, text: str) -> None:
        q = self.pick_posting(self.player.quests, f"{intent.item} {text}")
        if not q:
            console.note("You have no contract like that.")
            self.halted = True
            return
        self.player.quests.remove(q)
        self.player.character.key_items = [k for k in self.player.character.key_items if k.id != f"quest_{q['id']}"]
        self.store.save_player(self.player)
        console.note(f"Abandoned: {q['title']}.")
        self.arc_quest_gone(q, "you walked away from it")

    def on_board(self, intent, text: str) -> None:
        if self.place.type != "guild":
            console.note("The contract board is at the guild house.")
            return
        self.show_board()

    # ---------- progress ----------

    def record_kills(self, dead) -> None:
        from engine import deeds, events
        for e in dead:
            deed = deeds.log(self.store, "kill", self.minutes, self.player.location, creature=e.creature, level=e.level,
                             rank=e.rank, spawn=getattr(e, "spawn", ""))
            if getattr(e, "spawn", ""):
                for s in events.on_kills(self.store, [e], self.minutes, self.world):
                    console.note(f"{s['name'].capitalize()} is dead." if s["boss"] else f"The {s['name']} that were troubling this place are broken.")
            events.after_deed(self, deed)
        changed = False
        for q in self.player.quests:
            if q["kind"] in ("hunt", "bounty") and q.get("place") in (self.player.location, None):
                n = sum(1 for e in dead if e.creature == q["creature"])
                if n and q["progress"] < q["count"]:
                    q["progress"] = min(q["count"], q["progress"] + n)
                    changed = True
                    console.note(f"{q['title']}: {q['progress']}/{q['count']}")
        if changed:
            self.store.save_player(self.player)

    def record_delivery(self, key, npc) -> None:
        from engine import deeds, events
        events.after_deed(self, deeds.log(self.store, "deliver", self.minutes, self.player.location, item=key.name, npc=npc.id,
                                          npc_name=npc.name))
        for q in self.player.quests:
            if q["kind"] == "deliver" and q.get("item") == key.name:
                to = (q.get("to_role") or "").replace("_", " ")
                if npc.role.replace("_", " ") == to or (q.get("to_name") and q["to_name"] in npc.name):
                    q["progress"] = 1
                    console.note(f"{q['title']}: delivered" + (" - collect your pay from the guild clerk." if q["guild"] else "."))
                    self.store.save_player(self.player)

    def bounty_encounter(self) -> bool:
        """While searching where a bounty's target lives, the target may come to you."""
        for q in self.player.quests:
            if q["kind"] == "bounty" and q["progress"] < 1 and q.get("place") == self.player.location \
                    and random.random() < G["bounty_draw_chance"]:
                creature = self.world.bestiary[q["creature"]]
                level = q.get("scale") or min(self.place.danger[1], creature.levels[1])
                foe = combat.fighter_from_creature(creature, level, "elite", "e1", f"{creature.name.lower()} (bounty)", "near")
                from scenes.combat_scene import CombatScene
                self.combat = CombatScene.begin(self, creature, [foe], "Your search draws out your quarry:")
                return True
        return False

    def expire_quests(self) -> None:
        for q in list(self.player.quests):
            if q.get("deadline") is not None and q["deadline"] <= self.minutes and not quests.done(q, self.pack):
                self.player.quests.remove(q)
                self.player.character.key_items = [k for k in self.player.character.key_items if k.id != f"quest_{q['id']}"]
                console.note(f"Contract expired: {q['title']}. The reward is forfeit.")
                self.arc_quest_gone(q, "time ran out")
                self.store.save_player(self.player)

    def turn_in(self) -> None:
        """Pay out finished contracts when the clerk (or a personal request's giver) is present."""
        clerk = self.clerk_here()
        present = {n.id: n for n in self.present}
        bonus = self.guild_perks()["reward_bonus"]
        c = self.player.character
        for q in list(self.player.quests):
            payer = clerk if q["guild"] else present.get(q["issuer"])
            if not payer or not quests.done(q, self.pack):
                continue
            if q["kind"] == "gather":
                inv.remove_goods(self.pack, q["good"], "", q["count"])
            elif q["kind"] == "materials":
                from engine import crafting
                crafting.use_material(self.pack, q["material"], q["count"])
            coins, xp = quests.reward(q["letter"], q["guild"], bonus if q["guild"] else 0)
            coins, xp = round(coins * q.get("multiplier", 1)), round(xp * q.get("multiplier", 1))
            if q["kind"] in ("hunt", "bounty", "dungeon_boss") and self.has("blood_price"):
                coins = round(coins * (1 + self.has("blood_price") / 100))
            coins = round(coins * self.contract_multiplier(q))
            c.coins += coins
            levels = leveling.gain_xp(c, xp)
            self.player.quests.remove(q)
            if q.get("thread"):
                from engine import deeds, events
                if self.owns("rally_the_town"):
                    self.reputation_change("contract_done", q.get("place") or self.player.location)
                events.after_deed(self, deeds.log(self.store, "quest_done", self.minutes, q.get("place") or self.player.location,
                                                  thread=q["thread"], title=q["title"]))
            if q["guild"]:
                self.player.guild_done[q["letter"]] = self.player.guild_done.get(q["letter"], 0) + q.get("rank_credit", 1)
                self.reputation_change("contract_done")
                self.standing_report("contract_done", None, q["title"])
            else:
                payer.trust = min(100, payer.trust + 3)
                self.reputation_change("request_done")
            payer.memories.append(Memory(day=clock.day(self.minutes), turn=self.store.meta.turn,
                                         text=f"The stranger finished {q['title'].lower()}; I paid {money.words(coins)}."))
            self.store.save_npc(payer)
            console.note(f"Completed: [{q['letter']}] {q['title']}. {payer.label().capitalize()} pays "
                         f"{money.fmt(coins)} - +{xp} XP.")
            if levels:
                console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
            self.promote_if_due()
        self.store.save_player(self.player)

    def promote_if_due(self) -> None:
        if not self.rank:
            return
        nxt = quests.promotion_due(self.rank, self.player.character.level, self.player.guild_done,
                                   1 if self.owns("born_to_rank") else 0)
        if nxt:
            self.player.guild_rank = nxt
            self.give_badge(nxt)
            console.note(f"PROMOTED to guild rank {nxt}! New perks: {quests.describe_perks(nxt)}.")

    # ---------- personal requests ----------

    def record_quest_offer(self, offer, npc) -> None:
        q = self.map_request(offer, npc)
        if not q:
            console.debug(f"ignored request '{offer.what}' - not something the game can track")
            return
        npc.quest_offer = q
        self.store.save_npc(npc)
        console.note(f"Request offered: [{q['letter']}] {q['title']} - {money.words(q['coins'])}, {q['xp']} XP. "
                     "Say yes to take it on.")

    def map_request(self, offer, npc) -> dict | None:
        return quests.map_offer(self.world, self.store, offer, npc.id, npc.name, self.minutes, guild=False)

    def take_personal(self, npc) -> None:
        q = npc.quest_offer
        npc.quest_offer = None
        self.store.save_npc(npc)
        if q.get("deadline", 1) is not None:
            q["deadline"] = self.minutes + G["ranks"][q["letter"]]["deadline_days"] * 1440
        if q["kind"] == "deliver":
            self.player.character.key_items.append(KeyItem(
                id=f"quest_{q['id']}", name=q["item"], description=q["item_description"], kind="quest",
                source=npc.name, day=clock.day(self.minutes), for_whom=q.get("to_role", "")))
        self.player.quests.append(q)
        self.store.save_player(self.player)
        console.note(f"Request taken: [{q['letter']}] {q['title']} (for {npc.name}). "
                     + ("No time limit." if q.get("deadline") is None else f"Due in {G['ranks'][q['letter']]['deadline_days']} days."))
