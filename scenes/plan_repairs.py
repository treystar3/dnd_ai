"""Plan repairs (f333): what the engine straightens in the interpreter's reading before any step runs.

Why: the live evaluator (tools/interp_eval.py --live) showed the model making the same few slips over and over, each one a habit rather
than a misunderstanding - the catalogue's own label "room from i1" copied into `ware`, the seller's id put in `destination`, an attack
added after the spell that already starts the fight, a `look` invented at the end of a line that never looks, a parting narrated as
speech, a hand of cards read as talk, "I use Mending Light" read as an item. Each habit here is one small rule the game applies itself;
the model is never asked twice. Every rule is pinned offline by a case in data/replay/interp_cases.yaml that carries the model's own
reading, so a rule that stops working is caught without a model.

The rules run in handle() after the narrated-talk and local-building repairs (scenes/world.py) and before the guild and bribe rewrites.
They only ever move a field, change a kind or drop a step; none adds a step the model did not read."""
from __future__ import annotations

import re

from engine import actions
from ui import console

GOING = re.compile(r"\b(go|goes|going|walk|head|travel|ride|set out|set off|make for|off to|over to|leave for|to the|towards?|visit|return)\b")
WITHIN = re.compile(r"\b(upstairs|downstairs|my room|the room|a room|the bar|the counter|a table|the table|the corner|the hearth|the fire|"
                    r"the window|the back room|the kitchen|the cellar|the loft|the stairs|a seat|a bench|the benches)\b")
CLIMB = re.compile(r"\b(climb|clamber|scale|scramble|haul (myself|me) up|pull (myself|me) up|get up onto)\b")
HIGH = re.compile(r"\b(roof|rooftop|wall|tree|ledge|rafters|chimney|eaves|balcony|cliff|rocks?|boulder)\b")
FISHING = re.compile(r"\b(fish|fishing|angling|angle for|cast (a|my) line|rod and line)\b")
OUT_OF_DUNGEON = re.compile(r"\b(out|surface|climb|back up|leave|exit|daylight|open air|turn back)\b")
GAMBLE = re.compile(r"\b(deal me in|hands? of cards|game of (dice|cards|chance)|roll (the |some )?dice|throw (the |some )?dice|"
                    r"play (some |a few |a hand of |at )?(cards|dice)|a wager|place a bet|double or nothing|for small stakes)\b")
HAGGLE = re.compile(r"\b(do better than that|come down (a bit|a little|on)|knock (something|a bit|a little) off|too (much|dear|steep|rich)|"
                    r"that's steep|cheaper|a better price|lower (the |your )?price|half that|take less|bring (the|that|your) price down|"
                    r"beat you down|meet me halfway|best price|for less)\b")
TRAIN = re.compile(r"\b(teach|taught|train|training|lessons?|drills?|tutor|tutoring|instruct)\b")
ASKING = re.compile(r"\b(me|my|i want|i'd like|i would like|can you|could you|will you|would you|i wish|i need)\b")
JOB = re.compile(r"\b((take|do|accept|start|finish|have) (the|that|this|your|my) (job|work|task)|put me to work|hire me|i'll work|"
                 r"ready to work|work for you)\b")
LOOKING = re.compile(r"\b(look|looks|looking|examine|inspect|see|watch|glance|study|survey|around|peer|gaze|check|take in|scan|notice|read|"
                     r"admire|observe|eye)\b")
PARTING = ("turn", "walk", "step", "nod", "wave", "leave", "move", "stop", "fall", "say", "go", "back")
RELEASE_WORDS = {"bond", "bonds", "rope", "ropes", "tie", "ties", "untie", "cut", "free", "loose", "prisoner", "captive", "unbind"}
STOP = {"the", "and", "what", "from", "can", "take", "taken", "look", "looking", "for", "with", "they", "that", "this", "into", "over",
        "there", "here", "then", "them", "his", "her", "its", "player", "their", "some", "much", "will", "would", "could"}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())).strip()


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) >= 4 and w not in STOP}


class PlanRepairs:

    def repair_plan(self, text: str, plan: list) -> list:
        """The habits, each straightened in turn; the order is the order the slips feed one another (a field moved before a kind is
        changed, a kind changed before a restating step is dropped, a target named last for whatever still lacks one)."""
        here = {n.id: n for n in self.present}
        self.tidy_fields(plan, here)
        plan = self.one_goodbye(plan)
        self.quiet_parting(plan)
        self.talk_to_deed(text, plan, here)
        self.use_to_ability(plan)
        self.move_elsewhere(text, plan)
        plan = self.fishing(text, plan)
        plan = self.drop_restatements(text, plan)
        self.name_the_target(text, plan)
        return plan

    # ---------- fields

    def tidy_fields(self, plan: list, here: dict) -> None:
        """"room from i1" is the catalogue's own label, copied: the ware is the room, the seller is i1. A person's id in `destination`
        is the target. The place they already stand in, named as a destination on a step that is not a move, is nothing."""
        here_names = {norm(self.place.name), norm(self.place.name).removeprefix("the "), self.player.location}
        for a in plan:
            for f in ("ware", "item"):
                m = re.match(r"^(.*?)\s+from\s+(\S+)$", getattr(a, f).strip(), re.I)
                if m and (m.group(2) in here or self.hire_by_id(m.group(2))):
                    setattr(a, f, m.group(1).strip())
                    if a.kind in actions.TARGETED and not a.target:
                        a.target = m.group(2)
            d = a.destination.strip()
            if a.kind != "move" and d:
                if d in here or self.hire_by_id(d):
                    if a.kind in actions.TARGETED and not a.target:
                        a.target = d
                    a.destination = ""
                elif norm(d) in here_names:
                    a.destination = ""

    # ---------- conversation

    def one_goodbye(self, plan: list) -> list:
        """"Thanks, that's all. Goodbye." read as a talk and then a leave_conversation is one parting, said to the one they were talking
        with: the words go on the leaving step, which says them in parting (on_leave_conversation)."""
        partner = self.partner.id if self.partner else ""
        for k in range(len(plan) - 1):
            a, b = plan[k], plan[k + 1]
            if a.kind == "talk" and b.kind == "leave_conversation" and partner and a.target in ("", partner) and b.target in ("", partner):
                b.speech = b.speech.strip() or a.speech
                b.target = partner
                console.debug("a talk and a leave_conversation to the same person: one parting")
                return plan[:k] + plan[k + 1:]
        return plan

    @staticmethod
    def quiet_parting(plan: list) -> None:
        """"I turn away from Osric and say nothing more" put in a leave_conversation's speech is narration, not words said in parting."""
        for a in plan:
            if a.kind == "leave_conversation" and a.speech.strip():
                said = re.sub(r"^\W*(?:i|we)\s+(?:try to |will |'ll )?", "", a.speech.strip().lower())
                lead = re.findall(r"[a-z']+", said)[:2]
                if lead and lead[0] in PARTING:
                    console.debug(f"a parting narrated, not spoken: {a.speech[:50]!r}")
                    a.speech = ""

    # ---------- a talk that is a deed

    def talk_to_deed(self, text: str, plan: list, here: dict) -> None:
        """A talk whose words are a pastime or a request the game has a kind for: a hand of cards is gamble, beating a price down is
        haggle (when a ware of the seller's is named), asking the instructor to teach is train, taking the job offered is work."""
        low = text.lower()
        question = low.strip().endswith("?")
        for a in plan:
            if a.kind != "talk" or (a.target and a.target not in here):
                continue
            who = here.get(a.target)
            if GAMBLE.search(low):
                a.kind = "gamble"
                console.debug(f"a talk that is a game: {text[:50]!r}")
            elif HAGGLE.search(low) and not question:
                sellers = [n for n in here.values() if self.world.roles[n.role].sells]
                seller = who if who in sellers else (sellers[0] if sellers and who is None else None)
                ware = self.ware_named(low, seller) if seller is not None else ""
                if ware:
                    a.kind, a.ware, a.target = "haggle", ware, seller.id
                    console.debug(f"a talk that bargains over {ware}: haggle")
            elif TRAIN.search(low) and ASKING.search(low) and (not question or self.asks_what(low)):
                teacher = who if who is not None and who.role == "guild_instructor" else (self.instructor_here() if who is None else None)
                if teacher is not None:
                    a.kind, a.target, a.item = "train", teacher.id, a.item or a.speech
                    console.debug("a talk asking the instructor to teach: train")
            elif JOB.search(low) and who is not None and not question and not re.search(r"\b(don'?t|do not|won'?t|not|never)\b", low):
                a.kind = "work"
                console.debug(f"a talk taking up {who.label()}'s job: work")

    def ware_named(self, low: str, seller) -> str:
        """The id of the seller's ware the line names ("the room"), '' when none or several."""
        hits = []
        for w in self.world.roles[seller.role].sells:
            names = {w.id.replace("_", " ")} | {t for t in re.findall(r"[a-z]+", w.name.lower()) if len(t) > 3}
            if any(re.search(rf"\b{re.escape(n)}s?\b", low) for n in names):
                hits.append(w.id)
        return hits[0] if len(hits) == 1 else ""

    # ---------- things and abilities

    def use_to_ability(self, plan: list) -> None:
        """"I use Mending Light on myself": an ability named as if it were an item in the pack is the ability."""
        from engine import inventory as inv, loadout
        for a in plan:
            if a.kind != "use" or not a.item.strip():
                continue
            named = a.item.strip().lower()
            hit = next((ab for ab in loadout.prepared(self.player.character) if named in (ab.name.lower(), ab.id.lower())), None)
            if hit is not None and inv.find(self.pack, a.item) is None:
                a.kind, a.ability, a.item = "ability", hit.id, ""
                console.debug(f"'{named}' used as an item is the ability {hit.id}")

    # ---------- going nowhere

    def move_elsewhere(self, text: str, plan: list) -> None:
        """A move that is not a journey: in a delve, out means leave_dungeon; a roof or a wall is a climb (other); upstairs, the bar, a
        table, their room is within the place (look)."""
        low = text.lower()
        for a in plan:
            if a.kind != "move":
                continue
            dest = a.destination.strip()
            if self.player.delve and OUT_OF_DUNGEON.search(low):
                a.kind, a.destination = "leave_dungeon", ""
                console.debug("a move while delving, with the words of climbing out: leave_dungeon")
                continue
            if dest in self.world.places or any(dest.lower() == pl.name.lower() or dest.lower() == pl.name.lower().removeprefix("the ")
                                                 for pl in self.world.places.values()):
                continue
            if HIGH.search(dest.lower()) and (CLIMB.search(low) or not GOING.search(low)):
                a.kind, a.destination, a.summary = "other", "", a.summary or text
                console.debug(f"'{dest}' is not a place but a climb: other")
            elif WITHIN.search(dest.lower()) or WITHIN.search(low) and not self.local_person(dest):
                a.kind, a.destination = "look", ""
                console.debug(f"'{dest}' is within this place: look")

    def fishing(self, text: str, plan: list) -> list:
        """"I fish in the river for my supper" is one attempt where they stand: not a hunt for fish (search) and not a journey to the
        water, unless they said they go."""
        low = text.lower()
        if not FISHING.search(low):
            return plan
        kept = []
        for a in plan:
            if a.kind in ("search", "forage", "look") and FISHING.search(f"{a.seek} {a.summary} {a.item}".lower()):
                a.kind, a.seek, a.summary = "other", "", a.summary or text
            elif a.kind == "move" and not GOING.search(low):
                console.debug(f"fishing: the move to {a.destination} was not asked for")
                continue
            kept.append(a)
        return kept or plan

    # ---------- a step restating another

    def drop_restatements(self, text: str, plan: list) -> list:
        """Steps the model adds that only say again what another step does: an attack after the ability that opens the fight; the
        ingredient 'used' beside the craft that uses it; the material 'given' beside the commission made from it; cutting the bonds
        beside the release; a look or search after the harvest, about the same beast; a look nobody asked for at the end of a line."""
        from engine import items, loadout
        low = text.lower()
        kept: list = []
        materials = {v.name.lower() for v in items.MATERIALS.values()} | {k.lower().replace("_", " ") for k in items.MATERIALS}
        brought = {ab.id: ab for ab in loadout.prepared(self.player.character)}

        def opens_a_fight(b) -> bool:                   # a damaging ability starts the fight itself; a buff or a heal does not
            ab = brought.get(b.ability.strip().lower())
            return ab is not None and ab.effect.value not in ("buff", "healing", "crafting", "utility")
        for k, a in enumerate(plan):
            before = plan[:k]
            why = ""
            if a.kind == "attack" and any(b.kind == "ability" and opens_a_fight(b) and (not a.target or not b.target or a.target == b.target) for b in before):
                why = "the ability opens the fight"
            elif a.kind == "use" and any(b.kind == "craft" and norm(a.item) and norm(a.item) in norm(f"{b.summary} {b.item}") for b in plan if b is not a):
                why = "the ingredient of the craft"
            elif a.kind == "give" and any(b.kind == "commission" for b in plan) \
                    and any(w in materials for w in re.findall(r"[a-z]+", a.item.lower().replace("raw", ""))) \
                    and not re.search(r"\b(gift|present|keep it|for you)\b", low):
                why = "the material of the commission"
            elif a.kind == "other" and any(b.kind == "release" for b in plan) and set(re.findall(r"[a-z]+", a.summary.lower())) & RELEASE_WORDS:
                why = "the release itself"
            elif a.kind in ("look", "search", "other") and any(b.kind == "harvest" and words(a.summary) & words(f"{b.item} {b.summary}") for b in before):
                why = "the harvest itself"
            elif a.kind == "look" and k and not a.seek.strip() and len(plan) > 1 and not LOOKING.search(low) and not a.checks:
                why = "a look the line never asked for"
            if why:
                console.debug(f"dropped a {a.kind} step that restates {why}: {a.summary[:50]!r}")
                continue
            kept.append(a)
        return kept or plan

    # ---------- who it is for

    def name_the_target(self, text: str, plan: list) -> None:
        """A step aimed at someone, with nobody named in it, is for the one person the line names ("I hand the guard a silver")."""
        for a in plan:
            if a.kind in actions.TARGETED and a.kind != "attack" and not a.target:
                who = self.named_here(text)
                if who:
                    a.target = who
