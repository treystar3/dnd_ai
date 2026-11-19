"""(f395) Grounded listening (BUILD_PLAN.md slice 2: LISTEN): what the player's words are about is what the game acts on.

Two nights read by people who knew nothing of the game: "I hand over the coins" gave away silverleaf, because the pack held a thing
whose name has 'silver' in it and the reading said so; offering a quarterstaff for sale handed over a bone wand; "ask the hermit who he
is" went to a companion who had spoken last; and a nod was answered with a speech, because it was read as words. Three repairs, run with
the others (scenes/plan_repairs.py): an item is one the line names, a nod is a gesture, and words go to the person the line names."""
from __future__ import annotations

import re

from scenes.plan_repairs import Repair

GENERIC = {"item", "thing", "things", "stuff", "some", "small", "crude", "common", "fine", "good", "worn", "old", "used"}


def said(name: str, low: str) -> bool:
    """Whether the line names this thing: a word of its name (four letters or more) in the line, whole, or one ending in the line's word."""
    words = [w for w in re.findall(r"[a-z]+", (name or "").lower()) if len(w) >= 4 and w not in GENERIC]
    line = {l for l in re.findall(r"[a-z]+", low) if len(l) >= 4 and l not in GENERIC}
    return any(w in line or any(w.endswith(l) for l in line) for w in words)        # 'sword' names a longsword; 'silver' is no silverleaf


class Listening:
    REPAIRS = (
        Repair("grounded_item", 57, "grounded_item", "a thing given, sold, dropped or shown is one the line names: 'the coins' is coin, never the silverleaf in the pack (f395)"),
        Repair("gesture_only", 85, "gesture_only", "a nod, a shrug, a wave at someone, with no words said, is a gesture, not speech (f395)"),
        Repair("to_the_named", 145, "to_the_named", "words to the person the line names go to them, not to a companion who spoke last (f395)"),
    )
    ITEM_KINDS = ("give", "sell", "drop", "show", "equip", "store")
    GESTURE = re.compile(r"\b(nod|nods|nodded|nodding|shrug|shrugs|shrugged|wave|waves|waved|bow|bows|bowed|smile|smiles|smiled|wink|winks|"
                         r"winked|grin|grins|grinned|frown|frowns|salute|salutes|tip my hat|raise my hand|thumbs up)\b", re.I)
    SPEAKING = re.compile(r"[\"“”]|\b(say|says|said|ask|asks|asked|tell|tells|told|reply|replies|answer|shout|whisper|call|greet|thank|"
                          r"apologi[sz]e|speak|talk|explain|introduce)\w*\b", re.I)

    def grounded_item(self, text: str, plan: list) -> None:
        from engine import inventory as inv
        low = (text or "").lower()
        for a in plan:
            if a.kind not in self.ITEM_KINDS or not a.item or said(a.item, low):
                continue
            named = next((inv.label(i) for i in self.pack if said(inv.label(i), low)), None)
            if named:
                a.item = named                                    # the staff they named, not the wand the reading picked
            elif a.kind == "give" and self.coin_word(low) and not self.is_coin(a.item):
                a.item = "coins"                                  # coin they named, not a thing whose name has 'silver' in it

    def is_coin(self, item: str) -> bool:
        return bool(self.coin_amount(item or "")) or bool(re.fullmatch(r"(the\s+|some\s+|my\s+)?(coins?|money|gold|silver|copper|payment|fee)",
                                                                        (item or "").lower().strip()))

    def gesture_only(self, text: str, plan: list) -> None:
        if not self.GESTURE.search(text or "") or self.SPEAKING.search(text or ""):
            return
        for a in plan:
            if a.kind == "talk" and not re.search(r"[a-z]", re.sub(self.GESTURE, "", re.sub(r"\*|\b(i|at|to|the|a|him|her|them|my|head|and)\b", "", (a.speech or "").lower()))):
                a.kind, a.summary, a.speech = "other", (text or "").strip("* ").strip() or "a gesture", ""

    def to_the_named(self, text: str, plan: list) -> None:
        """A talk aimed at a companion goes to the one the line speaks to ("ask the hermit who he is"), when that is someone else here.
        (f650) Spoken to, as engine/addressing.py reads it; a talk to anyone the line speaks to stays theirs. When the line speaks to no
        one, the older rule: a person it names or by trade, unless it names the companion."""
        from engine import addressing
        if not any(a.kind == "talk" and str(a.target).startswith("hire:") for a in plan):
            return
        people = self.addressees_here()
        found = [a for a in addressing.addressed(text or "", people) if a.who != (addressing.PARTY,)]
        found += [b for a in found if a.mine for b in addressing.addressed(a.mine, people) if b.who != (addressing.PARTY,)]   # "..., then I ask Bram"
        everyone = {w for a in found for w in a.who}
        to = found[0].who if found else None
        for a in plan:
            if a.kind != "talk" or not str(a.target).startswith("hire:"):
                continue
            if to is not None:                             # (f650) the line speaks to someone: it is theirs; of two of a trade, the one already talking
                talking = [w for w in to if w in (getattr(self.partner, "id", None), self.last_spoken)]
                pick = a.target if a.target in everyone else (to[0] if len(to) == 1 else (talking[0] if talking else None))
                if pick:
                    a.target = pick
                continue
            hire = self.hire_by_id(a.target)
            if hire and re.search(rf"\b{re.escape(hire['name'].split()[0].lower())}\b", (text or "").lower()):
                continue
            who = self.named_here(text)
            if who and not who.startswith("hire:") and who != a.target:
                a.target = who

    def addressees_here(self) -> dict:
        """(f650) Everyone here the line can speak to, with the forms of their name: a person by their trade, and by name once the acting
        character knows it; a companion by name, and as "my companion" when there is one."""
        from engine import regard
        out = {}
        for n in self.present:
            role = n.role.replace("_", " ")
            known = regard.of(n, self.acting).name_known and n.name
            out[n.id] = [f"the {role}", f"~{role}"] + ([n.name.lower(), n.name.split()[0].lower()] if known else [])   # "~": only when called
        hires = [m for m in self.player_of(self.acting).party if m.get("permanent") and m.get("name")]
        for m in hires:
            out[f"hire:{m['id']}"] = [m["name"].lower(), m["name"].split()[0].lower()] + (["my companion", "my friend"] if len(hires) == 1 else [])
        return out
