"""Plan repairs (f333): what the engine straightens in the interpreter's reading before any step runs, declared in one ordered table.

Why: the live evaluator (tools/interp_eval.py --live) showed the model making the same few slips over and over, each one a habit rather
than a misunderstanding - the catalogue's own label copied into `ware`, the seller's id put in `destination`, an attack added after the
spell that already starts the fight, a `look` invented at the end of a line that never looks, a parting narrated as speech, a hand of
cards read as talk, "I use Mending Light" read as an item. Each habit is one small rule the game applies itself; the model is never
asked twice. The rules grew into a second pipeline whose order decided meaning, the way the intercepts once were (scenes/intercepts.py),
so they are declared the same way: each mixin lists the repairs it owns (its REPAIRS tuple), the scene gathers them in order, repair()
runs them one after another, and every change is recorded by the rule's name - in the turn log (engine/turnlog.py `repairs`), in --debug,
and in the evaluator's count of which rules fire. data_check refuses to start a game whose table is inconsistent.

A repair is a scene method `fn(text, plan) -> list | None`: it may change the steps in place (None) or return the steps to keep. It only
ever moves a field, changes a kind, drops a step or (f417) puts a deal before the word said with it; none adds a step the model did not
read. Every rule here is pinned offline by a case
in data/replay/interp_cases.yaml that carries the model's own reading, so a rule that stops working is caught without a model."""
from __future__ import annotations

import re
from dataclasses import dataclass

from engine import actions
from ui import console


@dataclass(frozen=True)
class Repair:
    name: str                  # what the turn log and the evaluator call it
    order: int                 # lower runs first
    method: str                # the scene method: fn(text, plan) -> list | None
    note: str = ""             # what it straightens, for anyone reading the table


def gather(scene_class) -> tuple[Repair, ...]:
    """Every repair the scene's classes declare, in order of `order`."""
    found: list[Repair] = []
    for cls in scene_class.__mro__:
        found.extend(cls.__dict__.get("REPAIRS", ()))
    return tuple(sorted(found, key=lambda r: r.order))


def problems(scene_class) -> list[str]:
    """What does not agree: a method the scene lacks, a name or an order declared twice."""
    out = []
    table = gather(scene_class)
    names = [r.name for r in table]
    orders = [r.order for r in table]
    for n in sorted({n for n in names if names.count(n) > 1}):
        out.append(f"plan repair '{n}' is declared twice")
    for o in sorted({o for o in orders if orders.count(o) > 1}):
        out.append(f"plan repair order {o} is used twice: {', '.join(r.name for r in table if r.order == o)}")
    for r in table:
        if not callable(getattr(scene_class, r.method, None)):
            out.append(f"plan repair '{r.name}' names a method the scene lacks: {r.method}")
    return out


def describe(scene_class) -> list[str]:
    return [f"{r.order:>4}  {r.name:<16} {r.method}  {r.note}" for r in gather(scene_class)]


def brief(plan: list) -> str:
    """A plan in a few words, for the record of what a rule changed: 'talk:i1 buy:i1/meal'."""
    out = []
    for a in plan:
        d = a if isinstance(a, dict) else a.model_dump(exclude_defaults=True)
        what = d.get("target") or d.get("destination") or ""
        thing = d.get("ware") or d.get("item") or d.get("ability") or d.get("seek") or ""
        out.append(d.get("kind", "?") + (f":{what}" if what else "") + (f"/{thing[:18]}" if thing else ""))
    return " ".join(out) or "-"


GOING = re.compile(r"\b(go|goes|going|walk|head|travel|ride|set out|set off|make for|off to|over to|leave for|to the|towards?|visit|return)\b")
# (f420) "our rooms", "my quarters": a room in the inn, never a journey
WITHIN = re.compile(r"\b(upstairs|downstairs|my room|the room|a room|our rooms?|my quarters|our quarters|rooms?|quarters|the bar|the counter|a table|the table|the corner|the hearth|the fire|"
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
PRAYING = re.compile(r"\b(pray|prayer|prayers|kneel|kneels|light a candle|lights? a candle|candle for|altar|offering|give thanks|gives thanks|"
                     r"vow|blessing|the gods|the god|goddess)\b")
LOOKING = re.compile(r"\b(look|looks|looking|examine|inspect|see|watch|glance|study|survey|around|peer|gaze|check|take in|scan|notice|read|"
                     r"admire|observe|eye)\b")
PARTING = ("turn", "walk", "step", "nod", "wave", "leave", "move", "stop", "fall", "say", "go", "back")
RELEASE_WORDS = {"bond", "bonds", "rope", "ropes", "tie", "ties", "untie", "cut", "free", "loose", "prisoner", "captive", "unbind"}
STOP = {"the", "and", "what", "from", "can", "take", "taken", "look", "looking", "for", "with", "they", "that", "this", "into", "over",
        "there", "here", "then", "them", "his", "her", "its", "player", "their", "some", "much", "will", "would", "could"}


# (f429) a thing handed over for coin, or held out to be looked at; and the words that make it a gift after all
SELLING = re.compile(r"\b(how much|what (?:will|would|could|can) (?:you|he|she|they) (?:give|pay|offer)|for (?:some |a little |a few )?coins?\b|"
                     r"in exchange for (?:some |a little |a few )?(?:coin|money|silver|gold|copper)|(?:want|need|get|ask) (?:some )?coin|"
                     r"pay me|sell (?:it|this|them|him|her)|(?:buy|take) (?:it|this|them) off me|what (?:is|'s) it worth|for a price)", re.I)
SHOWING = re.compile(r"\b(to see what (?:he|she|they) (?:thinks?|makes?)|what (?:do|does) (?:you|he|she|they) (?:think|make) of|take a look|have a look|"
                     r"look (?:it )?over|to look at|appraise|for (?:his|her|their) (?:opinion|eye))", re.I)
GIFTING = re.compile(r"\b(keep it|keep them|it'?s yours|they'?re yours|a gift|as a gift|for free|no charge|as thanks|in thanks)\b", re.I)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())).strip()


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) >= 4 and w not in STOP}


class PlanRepairs:
    REPAIRS = (
        Repair("tidy_fields", 60, "tidy_fields", "'room from i1' is the catalogue's label: the ware is the room, the seller the target; a person's id in destination is the target"),
        Repair("one_goodbye", 70, "one_goodbye", "a talk and a leave_conversation to the one they were speaking with is one parting"),
        Repair("quiet_parting", 80, "quiet_parting", "a parting narrated as speech ('I turn away') is not words said"),
        Repair("talk_to_deed", 90, "talk_to_deed", "a talk that is a hand of cards, a price beaten down, a lesson asked for or a job taken is that deed"),
        Repair("give_for_coin", 95, "give_for_coin", "a thing handed over for coin is a sale, and one held out to be looked at is shown: never a gift (f429)"),
        Repair("use_to_ability", 100, "use_to_ability", "an ability named as if it were an item in the pack is the ability"),
        Repair("move_elsewhere", 110, "move_elsewhere", "out of a delve is leave_dungeon; a roof is a climb (other); upstairs or the bar is look"),
        Repair("fishing", 120, "fishing", "fishing is one attempt where they stand, not a hunt for fish or a journey to the water"),
        Repair("drop_restatements", 130, "drop_restatements", "a step that only says again what another does goes: the attack after the spell, the ingredient beside the craft, a look nobody asked for"),
        Repair("buy_what_was_named", 135, "buy_what_was_named", "a piece of stock the line never named, bought beside the asking for something else, goes: the asking stands (f342)"),
        Repair("name_the_target", 140, "name_the_target", "a step aimed at someone, with nobody named in it, is for the one person the line names"),
        Repair("deal_then_word", 165, "deal_then_word", "a word to someone, then a deal with them: the deal is settled first, so what they say knows how it went (f417)"),
    )
    DEALS = ("buy", "sell", "give", "show", "work", "accept_quest", "commission", "haggle", "gamble", "train")
    GOING = ("move", "explore", "delve", "leave_dungeon")

    # ---------- the runner

    def repair(self, text: str, plan: list) -> list:
        """Every repair in its declared order; each change recorded under the rule's name (self.repairs, for the turn log)."""
        self.repairs = []
        for r in self.REPAIR_TABLE:
            before = [a.model_dump(exclude_defaults=True) for a in plan]
            out = getattr(self, r.method)(text, plan)
            if out is not None:
                plan = out
            after = [a.model_dump(exclude_defaults=True) for a in plan]
            if after != before:
                was, now = brief(before), brief(after)
                self.repairs.append({"rule": r.name, "before": was, "after": now})
                console.debug(f"repair {r.name}: {was} -> {now}")
        return plan

    def here_map(self) -> dict:
        return {n.id: n for n in self.present}

    # ---------- fields

    def tidy_fields(self, text: str, plan: list) -> None:
        """"room from i1" is the catalogue's own label, copied: the ware is the room, the seller is i1. A person's id in `destination`
        is the target. The place they already stand in, named as a destination on a step that is not a move, is nothing."""
        here = self.here_map()
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

    def one_goodbye(self, text: str, plan: list) -> list | None:
        """"Thanks, that's all. Goodbye." read as a talk and then a leave_conversation is one parting, said to the one they were talking
        with: the words go on the leaving step, which says them in parting (on_leave_conversation)."""
        partner = self.partner.id if self.partner else ""
        for k in range(len(plan) - 1):
            a, b = plan[k], plan[k + 1]
            if a.kind == "talk" and b.kind == "leave_conversation" and partner and a.target in ("", partner) and b.target in ("", partner):
                b.speech = b.speech.strip() or a.speech
                b.target = partner
                return plan[:k] + plan[k + 1:]
        return None

    def quiet_parting(self, text: str, plan: list) -> None:
        """"I turn away from Osric and say nothing more" put in a leave_conversation's speech is narration, not words said in parting."""
        for a in plan:
            if a.kind == "leave_conversation" and a.speech.strip():
                said = re.sub(r"^\W*(?:i|we)\s+(?:try to |will |'ll )?", "", a.speech.strip().lower())
                lead = re.findall(r"[a-z']+", said)[:2]
                if lead and lead[0] in PARTING:
                    a.speech = ""

    def deal_then_word(self, text: str, plan: list) -> list | None:
        """(f417) A word to someone and a deal with them in one line ("I ask the smith if he takes cloth, and sell him the hood") are done
        deal first, so the answer is given knowing how it went: a night's smith said he did not deal in cloth and then bought the hood,
        an innkeeper agreed to a room that was never let. Steps after a journey are left where they are."""
        partner = self.partner.id if self.partner else ""
        for k, a in enumerate(plan):
            who = a.target or partner
            if a.kind != "talk" or not who:
                continue
            last = None
            for j, b in enumerate(plan[k + 1:], k + 1):
                if b.kind in self.GOING:
                    break
                if b.kind in self.DEALS and (b.target == who or (not b.target and b.kind not in actions.TARGETED)):
                    last = j                         # a deal aimed at them; a buy with no one named may be from anyone
            if last is not None:
                return plan[:k] + plan[k + 1:last + 1] + [a] + plan[last + 1:]
        return None

    # ---------- a talk that is a deed

    def talk_to_deed(self, text: str, plan: list) -> None:
        """A talk whose words are a pastime or a request the game has a kind for: a hand of cards is gamble, beating a price down is
        haggle (when a ware of the seller's is named), asking the instructor to teach is train, taking the job offered is work."""
        here = self.here_map()
        low = text.lower()
        question = low.strip().endswith("?")
        for a in plan:
            if a.kind != "talk" or (a.target and a.target not in here):
                continue
            who = here.get(a.target)
            if GAMBLE.search(low):
                a.kind = "gamble"
            elif HAGGLE.search(low) and not question:
                sellers = [n for n in here.values() if self.world.roles[n.role].sells]
                seller = who if who in sellers else (sellers[0] if sellers and who is None else None)
                ware = self.ware_named(low, seller) if seller is not None else ""
                if ware:
                    a.kind, a.ware, a.target = "haggle", ware, seller.id
            elif TRAIN.search(low) and ASKING.search(low) and (not question or self.asks_what(low)):
                teacher = who if who is not None and who.role == "guild_instructor" else (self.instructor_here() if who is None else None)
                if teacher is not None:
                    a.kind, a.target, a.item = "train", teacher.id, a.item or a.speech
            elif JOB.search(low) and who is not None and not question and not re.search(r"\b(don'?t|do not|won'?t|not|never)\b", low):
                a.kind = "work"
        for a in plan:                                                # an 'other' that is a small rite is a prayer, anywhere
            if a.kind == "other" and PRAYING.search(f"{a.summary} {low}".lower()) and not question:
                a.kind = "pray"

    def give_for_coin(self, text: str, plan: list) -> None:
        """(f429) The f425 night gave four things away that the player meant to sell or show: "I hand over my ash longbow and ask the
        clerk how much he'll give me for it", "offer him my wool hood in exchange for some coin", "offer him my boar hide cap to see what
        he thinks of it". A give of a thing (never coin) whose line asks for coin is a sale; one held out to be looked at is a show.
        Words that make it a gift ("keep it", "it's yours") leave it a gift."""
        low = text.lower()
        if GIFTING.search(low):
            return
        for a in plan:
            if a.kind != "give" or not a.item or self.coin_word(a.item):
                continue
            if SELLING.search(low):
                a.kind = "sell"
            elif SHOWING.search(low):
                a.kind = "show"

    def ware_named(self, low: str, seller) -> str:
        """The id of the seller's ware the line names ("the room"), '' when none or several."""
        hits = []
        for w in self.world.roles[seller.role].sells:
            names = {w.id.replace("_", " ")} | {t for t in re.findall(r"[a-z]+", w.name.lower()) if len(t) > 3}
            if any(re.search(rf"\b{re.escape(n)}s?\b", low) for n in names):
                hits.append(w.id)
        return hits[0] if len(hits) == 1 else ""

    # ---------- things and abilities

    def use_to_ability(self, text: str, plan: list) -> None:
        """"I use Mending Light on myself": an ability named as if it were an item in the pack is the ability."""
        from engine import inventory as inv, loadout
        for a in plan:
            if a.kind != "use" or not a.item.strip():
                continue
            named = a.item.strip().lower()
            hit = next((ab for ab in loadout.prepared(self.player.character) if named in (ab.name.lower(), ab.id.lower())), None)
            if hit is not None and inv.find(self.pack, a.item) is None:
                a.kind, a.ability, a.item = "ability", hit.id, ""

    # ---------- going nowhere

    def move_elsewhere(self, text: str, plan: list) -> None:
        """A move that is not a journey: in a delve, out means leave_dungeon; a roof or a wall is a climb (other); upstairs, the bar, a
        table, their room is within the place (look)."""
        low = text.lower()
        for a in plan:
            if a.kind != "move":
                continue
            dest = a.destination.strip()
            if self.player.delve and self.dungeon_here() and OUT_OF_DUNGEON.search(low):        # (f392) in one, standing at its mouth
                a.kind, a.destination = "leave_dungeon", ""
                continue
            if dest in self.world.places or any(dest.lower() == pl.name.lower() or dest.lower() == pl.name.lower().removeprefix("the ")
                                                 for pl in self.world.places.values()):
                continue
            if HIGH.search(dest.lower()) and (CLIMB.search(low) or not GOING.search(low)):
                a.kind, a.destination, a.summary = "other", "", a.summary or text
            elif WITHIN.search(dest.lower()) or WITHIN.search(low) and not self.local_person(dest):
                a.kind, a.destination = "look", ""

    def fishing(self, text: str, plan: list) -> list | None:
        """"I fish in the river for my supper" is one attempt where they stand: not a hunt for fish (search) and not a journey to the
        water, unless they said they go."""
        low = text.lower()
        if not FISHING.search(low):
            return None
        kept = []
        for a in plan:
            if a.kind in ("search", "forage", "look") and FISHING.search(f"{a.seek} {a.summary} {a.item}".lower()):
                a.kind, a.seek, a.summary = "other", "", a.summary or text
            elif a.kind == "move" and not GOING.search(low):
                continue
            kept.append(a)
        return kept or plan

    # ---------- a step restating another

    def drop_restatements(self, text: str, plan: list) -> list | None:
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
            elif a.kind == "use" and any(b.kind == "craft" for b in plan) and \
                    (any(w in materials for w in re.findall(r"[a-z]+", a.item.lower().replace("raw", "")))
                     or any(b.kind == "craft" and (words(a.item.replace("raw", "")) & words(f"{b.summary} {b.item}")) for b in plan if b is not a)):
                why = "the ingredient or material of the craft"
            elif a.kind == "talk" and any(b.kind == "steal" and (not b.target or not a.target or b.target == a.target) for b in plan if b is not a) \
                    and (not norm(a.speech) or norm(a.speech) not in norm(low)) and '"' not in low:
                why = "a word to the mark the line never said"
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

    def buy_what_was_named(self, text: str, plan: list) -> list | None:
        """"I ask to buy arrows" read as a talk and a buy of a crude shortbow: the model, finding no arrows, reached for the nearest thing
        on the shelf. A buy of stock (gear, not a good off a role's list) whose name shares no word with the line, in a plan that also
        asks the same seller, is dropped; the asking stands, and the seller answers in their own words. A good (food, a draught, a
        room) is left alone: "something to eat" names no ware and still means the loaf."""
        from engine import inventory
        said = {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 3}

        def plain(name: str) -> str:                              # "Trail Rations" and trail_ration are one good
            return re.sub(r"[^a-z]+", "_", (name or "").lower()).strip("_").rstrip("s")
        goods = {plain(g.id) for g in inventory.GOODS.values()} | {plain(g.name) for g in inventory.GOODS.values()}
        for role in self.world.roles.values():                    # and so is anything on a trade's own list: a room, a draught, a meal
            goods |= {plain(w.id) for w in role.sells} | {plain(w.name) for w in role.sells}
        out = []
        for a in plan:
            if a.kind == "buy" and a.ware and plain(a.ware) not in goods \
                    and any(b.kind == "talk" and b is not a and (not a.target or not b.target or b.target == a.target) for b in plan):
                ware_words = {w for w in re.findall(r"[a-z]+", a.ware.lower()) if len(w) >= 3}
                if not any(w == v or (len(v) >= 3 and (w.endswith(v) or v.endswith(w))) for w in said for v in ware_words):
                    continue
            out.append(a)
        return out if len(out) != len(plan) else None

    def name_the_target(self, text: str, plan: list) -> None:
        """A step aimed at someone, with nobody named in it, is for the one person the line names ("I hand the guard a silver")."""
        for a in plan:
            if a.kind in actions.TARGETED and a.kind != "attack" and not a.target:
                who = self.named_here(text)
                if who:
                    a.target = who
