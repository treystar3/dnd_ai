"""The trial of rank: when you have earned the next guild rank on paper, you win it in a duel with an examiner of that rank.

The engine decides who qualifies, who the examiner is and how the duel goes. Nobody can die in it: the blow that would kill ends
it and decides it, for either side. The model only voices the scene.
"""

import random
import re
from types import SimpleNamespace

from engine import clock, combat, money, party, pools, quests
from ui import console

G = quests.G
T = G["trial"]

ASK = re.compile(r"\b(trial|rank test|test for (my |the )?rank|take the test|advance my rank|promote me|promote my rank|rank me up|rank up|"
                 r"prove (myself|my worth)|duel (the |an )?examiner|next rank)\b", re.I)
# away from a hall only a line plainly about the player's own trial is answered; "the heretic's trial" is for whoever they are talking to
ASK_AWAY = re.compile(r"\b(take (the|my|a) trial|trial of rank|my trial|rank test|test for (my |the )?rank|take the test|advance my rank|"
                      r"promote me|promote my rank|rank me up|rank up|next rank|duel (the |an )?examiner)\b", re.I)
QUESTION = re.compile(r"\?|^\W*(what|how|when|where|do i|does|is|am i|can i|could i)\b", re.I)
STANDING = re.compile(r"\b(i'?d like|i would like|let me|i want|i will|i'?ll|ready to|take (the|my) (trial|test)|stand for|begin|start)\b", re.I)


class TrialActions:
    from scenes.intercepts import Intercept as _I
    INTERCEPTS = (_I("trial", 30, "trial_turn", "a word about your own trial of rank"),)

    def trial_due(self) -> str | None:
        """The rank this member has earned on paper (level and contracts), if any: it is theirs once they win the trial."""
        if not self.rank:
            return None
        return quests.promotion_due(self.rank, self.player.character.level, self.player.guild_done, 1 if self.owns("born_to_rank") else 0)

    def at_guild_hall_here(self) -> bool:
        return self.place.type == "guild" and bool(self.rank)

    def trial_notice(self, on_arrival: bool = False) -> None:
        nxt = self.trial_due()
        if not nxt:
            return
        t = self.player.trial
        day = clock.day(self.minutes)
        if on_arrival and (not self.at_guild_hall_here() or t.get("told_day") == day):
            return
        t["told_day"] = day
        where = "" if self.at_guild_hall_here() else " at a guild hall"
        console.note(f"You have earned rank {nxt} on paper. To hold it you must win a trial against an examiner of that rank"
                     f"{where}: say \"I'd like to take the trial\".")
        self.store.save_player(self.player)

    def trial_turn(self, text: str) -> bool:
        """'I'd like to take the trial': True when the line was about it."""
        if self.combat or text.lstrip().startswith(("#", "/")) or not ASK.search(text):
            return False
        if not self.at_guild_hall_here():
            if ASK_AWAY.search(text):
                console.note("Trials of rank are held at a guild hall.")
                return True
            return False
        if self.rank == quests.LETTERS[-1]:
            console.note(f"You already hold the highest rank, {self.rank}.")
            return True
        nxt = self.trial_due()
        if QUESTION.search(text) and not STANDING.search(text):     # "what do I need for the next rank?" asks; it does not step into the ring
            if nxt:
                console.note(f"You have earned rank {nxt} on paper. To hold it you must win a trial against an examiner of that rank: "
                             f"say \"I'd like to take the trial\".")
                return True
            nxt = quests.next_rank(self.rank)
        if not nxt:
            nxt = quests.next_rank(self.rank)
            need = G["ranks"][nxt]["requires"]
            counted = sum(n for l, n in self.player.guild_done.items() if quests.LETTERS.index(l) >= quests.LETTERS.index(self.rank))
            lvl = self.player.character.level
            console.note(f"The register says you are not ready to stand for rank {nxt}: level {need['level']} (you are {lvl}) and "
                         f"{need['completed']} contracts at {self.rank} or higher (you have {counted}).")
            return True
        wait = self.player.trial.get("wait_until", -1)
        if self.minutes < wait:
            console.note(f"No examiner will see you yet. Come back in {clock.describe_duration(wait - self.minutes)}.")
            return True
        self.trial_start(nxt)
        return True

    def examiner(self, nxt: str) -> tuple[combat.Fighter, str]:
        """The one who tests you: a guild member of the next rank, built like any adventurer, a little above you if you are above the bar."""
        t = self.player.trial
        tries = t.get("tries", 0)
        rng = random.Random(f"{self.store.meta.seed}:trial:{nxt}:{tries}")
        role = rng.choice(T["roles"])
        level = max(G["ranks"][nxt]["requires"]["level"], self.player.character.level) + T["level_edge"][nxt]
        master = nxt == quests.LETTERS[-1]
        if master:
            level += T["master_edge"]
        name = None
        if master:
            gm = next((n for n in self.present if n.role == "guild_master"), None)
            name = gm.name if gm else None
        name = name or f"{rng.choice(party.P['names']['first'])} {rng.choice(party.P['names']['last'])}"
        member = {"id": f"trial-{nxt}", "name": name, "role": role, "level": level}
        f = combat.fighter_from_creature(party.Shape(member), level, T["rank"], "e1", name, "engaged")
        f.side = "enemy"
        return f, role

    def trial_start(self, nxt: str) -> None:
        c = self.player.character
        t = self.player.trial
        f, role = self.examiner(nxt)
        t.update(pending=nxt, examiner=f.name, tries=t.get("tries", 0) + 1,
                 pools={p: float(getattr(c, p)) for p in pools.POOLS})
        self.store.save_player(self.player)
        master = nxt == quests.LETTERS[-1]
        label = "the guild master" if master else f"a rank-{nxt} guild member"
        console.note(f"Trial for rank {nxt}: you face {f.name}, {label}. Nobody dies here: the first blow that would end a fighter decides it. "
                     "No potions or draughts. Your companions and hired party wait outside.")
        intro = (f"The player stands in the guild hall's practice yard for the trial of rank {nxt}, facing {f.name}, {label}, who fights "
                 f"as a {role}.")
        scene = SimpleNamespace(name=f.name, temperament="aggressive")
        from scenes.combat_scene import CombatScene
        self.combat = CombatScene.begin(self, scene, [f], "", duel=intro)

    def trial_over(self, won: bool, fight) -> None:
        c = self.player.character
        t = self.player.trial
        nxt, who = t.pop("pending", None), t.get("examiner", "the examiner")
        saved = t.pop("pools", {})
        for p, v in saved.items():                      # the blades were blunted: you walk out as you walked in
            setattr(c, p, v)
        if won and nxt:
            self.player.guild_rank = nxt
            self.give_badge(nxt)
            t["tries"] = 0
            console.note(f"PROMOTED to guild rank {nxt}! New perks: {quests.describe_perks(nxt)}.")
            self.narrate(f"[THE GAME HAS DECIDED: the player won the trial for guild rank {nxt}; {who}, the examiner, lowers their blade and "
                         "concedes, and the hall marks the player's new rank. The blows were pulled and nobody is hurt.] Describe the moment in "
                         "two or three sentences.", "")
        else:
            wait = T["retry_days"] * clock.MINUTES_PER_DAY
            t["wait_until"] = self.minutes + wait
            console.note(f"You lose the trial. You keep rank {self.rank}. You may stand again in {clock.describe_duration(wait)}.")
            self.narrate(f"[THE GAME HAS DECIDED: the player lost the trial for guild rank {nxt}; {who}, the examiner, stops the blow and "
                         "tells the player plainly what they lacked. The blows were pulled and nobody is hurt.] Describe the moment in two or "
                         "three sentences.", "")
        self.store.save_player(self.player)
