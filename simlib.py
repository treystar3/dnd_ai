"""Shared pieces for the playthrough simulation: a stand-in for the language model, the four test characters,
and instrumentation. The engine is real; only the model's writing is replaced."""

import json
import os
import random
import re
import types
from pathlib import Path

# ------------------------------------------------------------------ the stand-in model

NAME_COUNTER = [0]
NARR_COUNTER = [0]
MOMENT_COUNTER = [0]
SEEN_TITLES = {}


def _fill(s, root):
    """A minimal valid instance of a JSON schema (for any request the stand-in has no special answer for)."""
    if "$ref" in s:
        return _fill(root["$defs"][s["$ref"].split("/")[-1]], root)
    if "anyOf" in s:
        opts = [o for o in s["anyOf"] if o.get("type") != "null"]
        return _fill(opts[0], root) if opts else None
    if "enum" in s:
        return s["enum"][0]
    t = s.get("type")
    if t == "object":
        req = s.get("required", [])
        return {p: _fill(v, root) for p, v in s.get("properties", {}).items() if p in req}
    if t == "array":
        return [_fill(s["items"], root) for _ in range(s.get("minItems", 0))]
    if t == "string":
        return "x"
    if t in ("integer", "number"):
        return s.get("minimum", 1)
    if t == "boolean":
        return False
    return None


class Stub:
    """Answers every model request. `bot` supplies the player's decisions (actions in the world and in fights)."""

    def __init__(self, cls_kind: str, seed: int):
        self.bot = None
        self.cls = cls_kind
        self.rng = random.Random(seed)
        self.plan = [{"kind": "look"}]
        self.calls = {}
        self.ask_help = False

    def chat(self, **k):
        t = k["format"].get("title", "?")
        u = k["messages"][-1]["content"]
        self.calls[t] = self.calls.get(t, 0) + 1
        SEEN_TITLES[t] = SEEN_TITLES.get(t, 0) + 1
        fn = getattr(self, f"a_{t}", None)
        out = fn(u, k) if fn else _fill(k["format"], k["format"])
        return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=json.dumps(out)))

    # ---- the player's side
    def a_ActionPlan(self, u, k):
        return {"actions": self.plan or [{"kind": "look"}]}

    def a_Ruling(self, u, k):
        """(f395) The dungeon master's ruling: what a test or a scene gives (self.ruling), else it makes sense and is rolled for, as every
        improvised act was before there was a ruling."""
        return getattr(self, "ruling", None) or {"sense": "cost", "why": "", "needs": [], "requires": []}

    def a_CombatIntent(self, u, k):
        return self.bot.combat_choice()

    # ---- people
    def a_ResidentSet(self, u, k):
        roles = re.findall(r"slot \d+: (\w+)", u)
        out = []
        for i, r in enumerate(roles):
            NAME_COUNTER[0] += 1
            out.append({"slot": i + 1, "name": f"{r.title().replace('_', '')} Z{NAME_COUNTER[0]}", "epithet": f"the {r.replace('_', ' ')}",
                        "description": "A person.", "activity": "going about their work"})
        return {"residents": out}

    def a_MentorLines(self, u, k):
        first = next((m["content"] for m in k["messages"] if m["role"] == "user"), u)       # a retry's last message is the complaint, not the lines
        lines = re.findall(r"^\d+\. (.*)$", first.split("LINES TO SAY", 1)[-1], re.M)
        reply = "Fair enough." if "THE PLAYER JUST SAID" in first else ""
        if getattr(self, "reply", None) is not None and reply:
            reply = self.reply
        if getattr(self, "voice", None):
            return {"lines": self.voice(lines), "reply": reply}
        return {"lines": lines, "reply": reply}

    def a_MentorSpeech(self, u, k):
        first = next((m["content"] for m in k["messages"] if m["role"] == "user"), u)
        body = first.split("POINTS TO COVER", 1)[-1].split("WORD FOR WORD", 1)[0]
        pts = re.findall(r"^\d+\. (.*)$", body, re.M)
        musts = re.findall(r"^  - (.*)$", first.split("WORD FOR WORD", 1)[-1].split("HOW IT ENDS")[0], re.M)
        if getattr(self, "speech", None):
            return {"paragraphs": self.speech(pts, musts)}
        step = 2 if len(pts) <= 4 else 3
        paras = [" ".join(pts[i:i + step]) for i in range(0, len(pts), step)]
        have = " ".join(paras)
        missing = [m for m in musts if m and m not in have]
        if missing:
            paras.append(" ".join(missing))
        ends = first.split("HOW IT ENDS:", 1)[-1] if "HOW IT ENDS:" in first else ""
        if " asks " in " " + ends.lower() and not paras[-1].rstrip().endswith("?"):
            paras[-1] = paras[-1].rstrip(". ") + "?"
        return {"paragraphs": paras}

    def a_Exchange(self, u, k):
        first = next((m["content"] for m in k["messages"] if m["role"] == "user"), u)
        names = [x.strip() for x in first.rsplit("speakers from:", 1)[-1].strip().rstrip(".").split(",")]
        if getattr(self, "exchange", None):
            return {"lines": self.exchange(names, first)}
        lo = int(re.search(r"WRITE (\d+) TO", first).group(1))
        said = ["Well, here we are.", "So it seems.", "Quiet enough, for now.", "Could be worse.", "Mind the mud.", "We will see."]   # (f382) one line said
        return {"lines": [{"speaker": names[i % len(names)], "text": said[i % len(said)]} for i in range(max(lo, 2))]}          # twice is sent back

    def a_CompanionReply(self, u, k):
        if getattr(self, "companion", None):
            return self.companion(u)
        return {"speech": "That is how it is with me.", "gesture": "", "remember": "", "impression": ""}

    def a_CanonCheck(self, u, k):
        if getattr(self, "canon", None):
            return self.canon(u)
        return {"verdict": "new", "which": 0}

    def a_Overheard(self, u, k):
        if getattr(self, "overheard", None):
            return self.overheard(u)
        return {"about": [], "party": False, "weight": "light"}

    def a_Extracted(self, u, k):
        if getattr(self, "extract", None):
            return self.extract(u)
        return {"facts": []}

    def a_PersonaDetails(self, u, k):
        return {"details": ["They grew up in a fishing village on a cold coast.", "They love bread burnt at the edges.",
                            "A pale scar crosses one thumb, from a gutting knife.", "They hum when they clean their gear.",
                            "They think often of an older sister who married young."],
                "secrets": ["I still owe a boatwright for the net I lost the night my father drowned.", "I let my sister take the blame for it, and she has never said a word."],
                "weights": ["personal", "light", "light", "light", "light"]}

    def a_PairDynamic(self, u, k):
        names = [ln.split(":", 1)[0].strip() for ln in u.splitlines() if ":" in ln][:2]
        a, b = (names + ["One", "Other"])[:2]
        return {"dynamic": f"{a} says the hard thing and {b} softens it after, and neither of them would admit the arrangement works.",
                "first_wants": "to get a rise out of the other", "second_wants": "to see the other eats",
                "first_thinks": f"thinks {b} fusses, and is secretly glad of it", "second_thinks": f"thinks {a} is kinder than he lets on"}

    def a_StrangerRead(self, u, k):
        said = u.split("THE STRANGER SAID:", 1)[-1].lower()
        import re as _re
        hostile = bool(_re.search(r"bandit|rob|kill you|mind your own|none of your|steal|threat", said))
        return {"settled": not hostile and len(said.split()) > 3, "hostile": hostile}

    def a_MentorReply(self, u, k):
        return {"speech": "Keep your eyes on the ground and your hand near your weapon."}

    def a_NPCProfile(self, u, k):
        motive = "work toward a goal" if "THEY HAVE A MOTIVE: write one" in u else ""
        return {"personality": "Plain.", "voice": "Plain.", "concern": "A small worry.", "motive": motive}

    def a_NPCReply(self, u, k):
        out = {"speech": "It is as it is.", "intent": "small_talk", **(getattr(self, "reply_extra", None) or {})}   # (f482) a test's planted words
        if self.ask_help and "WORK YOU HAVE OFFERED" not in u:
            r = self.rng.random()
            if r < 0.5:
                out["offers_work"] = {"task": "haul sacks", "pay": self.rng.randint(15, 60), "minutes": 60}
            elif r < 0.8:
                out["offers_quest"] = {"kind": "hunt", "what": self.rng.choice(["wolves", "boars", "goblins", "bandits"]), "count": 3}
        return out

    def a_NPCReplyMany(self, u, k):
        """(f487) One block per character the format names, or what a test planted (many_extra: a list of blocks, as given)."""
        ids = (((k["format"].get("$defs") or {}).get("NPCAnswer") or {}).get("properties") or {}).get("to", {}).get("enum") or []
        blocks = getattr(self, "many_extra", None) or [{"to": t} for t in ids]
        return {"speech": "It is as it is.", "intent": "small_talk", "answers": blocks}

    def a_DialogueFrame(self, u, k):
        return {"before": "", "after": ""}

    def a_MomentProposal(self, u, k):
        """(f348) A moment of the shape asked for, different each time, with the visitor and the mishap when they are asked for."""
        MOMENT_COUNTER[0] += 1
        n = MOMENT_COUNTER[0]
        roles = re.findall(r"^  - ([a-z_]+): ", u, re.M)
        out = {"title": f"the stir number {n}".replace(str(n), ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"][(n - 1) % 10]),
               "line": f"Stir {['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'][(n - 1) % 10]}: a small thing has the place's attention, and the {roles[0] if roles else 'people'} most of all.",
               "doings": [{"who": "everyone", "doing": "watching the stir with arms folded"}] + ([{"who": roles[0], "doing": "being in the middle of the stir"}] if roles else []),
               "memory": f"the stir that was number {['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'][(n - 1) % 10]}"}
        if "A VISITOR comes with it" in u:
            out.update(visitor_epithet="a dusty stranger", visitor_look="A stranger in a dusty coat.", visitor_doing="standing in the middle of it")
        if "MISHAP:" in u:
            out["mishap"] = "A mug goes past the player's ear as they come in."
        return out

    def a_Narration(self, u, k):
        NARR_COUNTER[0] += 1
        return {"text": f"[scene {NARR_COUNTER[0]}]"}

    # ---- guild instructor
    def a_LessonWant(self, u, k):
        req = re.search(r'THEY ASKED TO LEARN: "(.*)"', u).group(1).lower()
        return {"kind": "passive" if "passive" in req or "trait" in req else "active",
                "effect": "" if "passive" in req or "trait" in req else "damage", "stat": ""}

    def a_LessonNames(self, u, k):
        out = []
        for m in re.finditer(r"^(\d+)\. (\w+)", u, re.M):
            NAME_COUNTER[0] += 1
            row = {"slot": int(m.group(1)), "name": f"Technique {NAME_COUNTER[0]}", "description": "A learned technique."}
            if m.group(2) == "SUMMON":
                row["summons"] = {"name": f"Spirit {NAME_COUNTER[0]}", "description": "A spirit made of will."}
            out.append(row)
        return {"skills": out}

    # ---- the pulse
    def a_ThreadProposal(self, u, k):
        place = re.search(r"PLACE: (\S+) -", u).group(1)
        n = int(re.search(r"STAGES: (\d+)", u).group(1))
        people = [p.split(":")[0].strip() for p in (re.search(r"PEOPLE \(id: who\): (.*)", u).group(1).split("; ")) if ":" in p]
        places = re.search(r"PLACES: (.*)", u).group(1).split(", ")
        groups = re.search(r"GROUPS: (.*)", u).group(1).split(", ")
        traits = re.search(r"TRAITS: (.*)", u).group(1).split(", ")
        NAME_COUNTER[0] += 1
        r = self.rng

        def effect():
            kind = r.choice(["prices", "danger", "closed", "mark", "loot", "arrive", "mood", "relation", "fact",
                             "prices", "danger", "mark", "mood", "relation", "leave", "trait", "move"])
            e = {"kind": kind, "place": place}
            if kind == "prices": e.update(value=r.choice([-20, 15, 30, 45]), days=r.randint(2, 20))
            elif kind == "danger": e.update(place=r.choice(places), value=r.choice([-40, 30, 70]), days=r.randint(2, 20))
            elif kind == "closed": e.update(place=r.choice(places), days=r.randint(1, 6), text="a blockage")
            elif kind == "mark": e.update(text=f"a lasting change {NAME_COUNTER[0]}")
            elif kind == "loot": e.update(text="a cart")
            elif kind == "arrive": e.update(role=r.choice(["merchant", "farmer", "scout", "baker", "fisher"]), text="a newcomer")
            elif kind == "fact": e.update(text="a fact", groups=r.sample(groups, 2))
            elif people:
                e.update(npc=r.choice(people), other=r.choice(people), text="a change", value=r.choice([-10, 10]),
                         add=r.choice(traits), remove=r.choice(traits), role="x")
                if kind == "move": e["place"] = r.choice(places)
            return e
        pname = re.search(r"PLACE: \S+ - (.*?) \(", u).group(1)
        pres = re.search(r"PRESSURES HERE: (.*)", u).group(1)
        seeds = [d for d in pres.split("; ") if d and d != "none in particular"]
        part = ""
        if seeds:
            d = r.choice(seeds).rstrip(".")
            rest = d.split(" - ", 1)[1] if " - " in d else d
            bits = [b.strip() for b in re.split(r", (?:or |and )?| or ", rest) if len(b.strip()) > 8]
            part = r.choice(bits) if bits else d
        part = (part[0].upper() + part[1:]) if part else f"A quiet trouble in {pname}"
        steps = ["word spreads through {p}", "it worsens and {p} takes sides", "it comes to a head in {p}"]
        stages = [{"description": f"{part}: " + steps[min(i, 2)].format(p=pname), "effects": [effect() for _ in range(r.randint(0, 2))]}
                  for i in range(n)]
        out = {"title": f"{pname}: {part}"[:90], "place": place, "news": f"They are talking in {pname}: {part.lower()}.",
               "groups": r.sample(groups, 2), "stages": stages,
               "fallout": {"description": f"it passes, leaving {pname} changed", "effects": [effect()]}, "resolution": "deal with it"}
        cm = re.search(r"CREATURES \(id: name, levels\): (.*)", u)
        if cm and n >= 3:
            cid = cm.group(1).split(":")[0].strip()
            out["stages"][1]["effects"].append({"kind": "spawn", "place": place, "creature": cid, "boss": True, "days": 30})
            out["stages"][2]["effects"].append({"kind": "spawn", "place": place, "creature": cid, "boss": False, "days": 30})
            out["paths"] = [{"name": "Slay it", "how": "kill it", "kind": "kill", "target": cid}, {"name": "Take the job", "how": "do the job", "kind": "contract"}]
            out["triumph"] = {"description": "peace returns", "effects": []}
            out["boss_lines"] = {"intro": "Three winters I have starved this valley, and you have come to take the last of it from me?",
                                 "bloodied": "You bleed me, little thing? Then the valley will bleed with me.",
                                 "last_stand": "No. I will not die with my work half done.", "fall": "The hunger ends... and I am almost glad."}
            out["contract"] = {"kind": "hunt", "what": "wolves", "count": 3}
        elif r.random() < 0.3:
            out["contract"] = {"kind": "hunt", "what": r.choice(["wolves", "boars", "goblins", "giant spiders", "bandits"]), "count": 3}
        return out

    def a_ThreadTelling(self, u, k):
        stages = re.findall(r"^STAGE \d+: (.*)$", u, re.M)
        clues = re.findall(r"^CLUE \d+ \(.*?\): (.*)$", u, re.M)
        one = lambda key: (re.search(rf"^{key}: (.*)$", u, re.M).group(1) if re.search(rf"^{key}: ", u, re.M) else "")
        told = lambda t: ("(retold) " + t) if t else ""
        return {"stages": [told(t) for t in stages], "clues": [told(t) for t in clues], "fallout": told(one("FALLOUT")),
                "truth": told(one("TRUTH")), "reveal": told(one("REVEAL")), "resolution": told(one("RESOLUTION"))}

    def a_CataclysmProposal(self, u, k):
        n = int(re.search(r"STAGES: (\d+)", u).group(1))
        ids = re.search(r"PATHS \(write one for each id\): (.*)", u).group(1).split(", ")
        return {"title": "The Great Trouble", "news": "Dark rumours reach the towns.", "antagonist": "Vorthax the Old",
                "stages": [{"name": f"Stage {i + 1}", "description": f"The trouble worsens, step {i + 1}.", "signs": "People whisper."} for i in range(n)],
                "paths": [{"id": i, "name": f"Path {i}", "how": "Do the deed."} for i in ids],
                "triumph": "The land breathes again.", "ignored": "The land is scarred.", "keepsake": "the Ember Crown",
                "boss_lines": {"intro": "You come too late, little hero. The world was mine before you were born.", "bloodied": "You bleed me? Then I shall bleed the world!",
                               "last_stand": "Not yet. Not while a single ember remains.", "fall": "So it ends... as it began, in fire."},
                "side_lines": [{"intro": "I raised this banner for my people, and I will not lower it.", "bloodied": "Then let the banners fall together.",
                                "last_stand": "Back to your places! I am not finished!", "fall": "Tell them... I wanted only peace.",
                                "captain_intro": "For the banner! Cut them down!"}] * 2}

    def a_JudgeVerdict(self, u, k):
        return {"verdict": getattr(self, "verdict", "no"), "reason": "the ledger shows it", "ending": "victory"}

    def a_MotiveStep(self, u, k):
        pid = re.search(r"PERSON: (\S+) -", u).group(1)
        r = self.rng
        status = r.choices(["continuing", "achieved", "abandoned"], weights=[7, 2, 1])[0]
        eff = [{"kind": "mood", "npc": pid, "text": "restless"}]
        return {"happened": "They made a small step.", "effects": eff, "status": status,
                "next_motive": "keep going" if status == "continuing" else "",
                "gossip": self.rng.choice(["People talk.", "There is a new tale at the well.", "The market has it one way, the inn another.",
                                           "Somebody saw something on the road.", "The old ones say it was always coming.", "Nobody will say it to their face."])}

    # ---- character creation (used by setup only)
    def a_DiscoveryProposal(self, u, k):
        import re as _re
        if self.rng.random() < 0.25:
            return {"found": False}
        safe = [x.strip() for x in _re.search(r"PLACE TYPES \(safe\): (.*)", u).group(1).split(",")]
        wild_s = _re.search(r"PLACE TYPES \(wild, only off a wild place\): (.*)", u).group(1)
        wild = [x.strip() for x in wild_s.split(",")] if wild_s.strip() != "none here" else []
        reach = _re.findall(r"(\w+): [^;,]*?, (\d+) min", _re.search(r"REACHABLE \(id: name, minutes by the existing way\): (.*)", u).group(1))
        NAME_COUNTER[0] += 1
        n = NAME_COUNTER[0]
        if reach and self.rng.random() < 0.4:
            return {"found": True, "kind": "track", "name": f"the Hidden Way {n}", "description": "A narrow track.", "to": reach[0][0], "news": "Some say there is a shorter way."}
        return {"found": True, "kind": "place", "name": f"the Quiet Spot {n}", "place_type": self.rng.choice(safe + wild),
                "description": "A small, quiet place.", "residents": ["hunter"] if self.rng.random() < 0.3 else [], "news": "Folk talk of it."}

    def a_ArcStory(self, u, k):
        import re as _re
        steps = _re.findall(r"\n  (n\d+): (\w+)", u)
        subj = _re.search(r"THE SUBJECT: (.*?) \(kind: (\w+)\)", u)
        NAME_COUNTER[0] += 1
        n = NAME_COUNTER[0]
        person = subj and subj.group(2) == "person"
        return {"hook_title": (f"Find Mira {n}, the miller's daughter" if person else f"Trouble {n}"),
                "title": f"The Long Trail {n}", "victim_name": (f"Mira{n}" if person else f"the matter of {n}"),
                "victim_looks": "a girl of twenty with ink-stained fingers" if person else "a thing with many threads",
                "premise": "It was never what it looked like. Someone was behind it for coin.",
                "nodes": [{"id": i, "title": f"Step {i}", "clue": f"Clue {i}: the trail runs on.",
                           "npc_name": "" if kd == "site" else f"Npc{n}x{i}",
                           "npc_looks": "" if kd == "site" else "A watchful figure.",
                           "npc_manner": "" if kd == "site" else "Guarded."} for i, kd in steps]}

    def a_LegendaryName(self, u, k):
        taken = u.split("TAKEN NAMES:")[-1]
        for _ in range(500):
            name = self.rng.choice(["Vael", "Mor", "Thar", "Isil", "Dren", "Kor", "Syl", "Bran"]) + self.rng.choice(["ith", "oth", "wyn", "gar", "iel", "mund", "dra"])
            if name.lower() not in taken.lower():
                break
        return {"name": name, "title": "the Test of Ages", "lore": "Forged in a story the stand-in model made up."}

    def a_AccessoryName(self, u, k):
        r = self.a_LegendaryName(u, k)
        return {"name": r["name"], "title": r["title"], "lore": "Made in the story the stand-in model told.", "power_name": "The Stand-in's Gift"}

    def a_CampIntent(self, u, k):
        import re as _re
        from scenes.camp_actions import keyword_intent, keyword_methods
        say = _re.search(r"THE PLAYER SAYS: (.*)", u, _re.S)
        text = say.group(1) if say else ""
        return {"kind": keyword_intent(text) or "none", "target": "", "method": keyword_methods(text), "summary": ""}

    def a_PartyIntent(self, u, k):
        import re as _re
        from scenes.party_actions import keyword_party
        say = _re.search(r"THE PLAYER SAYS: (.*)", u, _re.S)
        text = say.group(1) if say else ""
        return {"kind": keyword_party(text) or "none", "target": text, "summary": ""}

    def a_RoadEvent(self, u, k):
        hostile = "MUST BE: an ambush" in u
        stopped = "THE PLAYER IS STOPPED HERE" in u
        told = re.search(r"KIND: (\w+)", u)
        kind = "ambush" if hostile else (told.group(1) if told else "sight" if "kind sight" in u.lower() else
                                         self.rng.choice(["find", "meeting", "hazard", "sight", "aid"]))
        out = {"title": f"Event {self.rng.randrange(10**5)}", "journey": "You walk on, the road long under your feet.",
               "scene": "You see something on the road.", "kind": kind,
               "detail": "d", "news": self.rng.choice(["Word spreads of trouble on the road.", "A cart came in late and its driver would not say why.",
                                        "Travellers are going in company now.", "The watch rode out along the road at dawn."]) if self.rng.random() < 0.3 else "",
               "meets_role": "merchant" if stopped and not hostile else "", "effects": []}
        if self.rng.random() < 0.25:
            out["effects"] = [{"kind": "danger", "place": "kings_road", "value": 30, "days": 5}]
        elif self.rng.random() < 0.25:
            out["effects"] = [{"kind": "lead", "place": "", "text": "A hidden path leads off the road up the hillside."}]
        return out

    def a_MechanicSet(self, u, k):
        lines = re.findall(r"\n?\s*(o\d+): (world|combat)( \(companions\))?", u)
        comp = [o for o, _, c in lines if c]
        world = [o for o, kd, c in lines if kd == "world" and not c]
        combat = [o for o, kd, c in lines if kd == "combat" and not c]
        count = int(m.group(1)) if (m := re.search(r"Choose exactly (\d+)", u)) else 8
        need_c = int(m.group(1)) if (m := re.search(r"At least (\d+) must be mechanics marked \(companions\)", u)) else \
            (min(2, len(comp)) if self.cls == "summoner" else 0)
        need_w = int(m.group(1)) if (m := re.search(r"At least (\d+) must be world mechanics", u)) else 2
        picks = comp[:need_c] + world[:need_w]
        for o in combat + world[need_w:] + comp[need_c:]:
            if len(picks) >= count:
                break
            if o not in picks:
                picks.append(o)
        picks = picks[:count]
        return {"passives": [{"option_id": o, "name": f"Mech{self.rng.randrange(10**6)}{i}", "description": "d", "tier": "light"}
                             for i, o in enumerate(picks)]}

    STAT_POOL = [("damage", "always"), ("accuracy", "first_round_of_combat"), ("defense", "while_defending"),
                 ("perception", "in_wilderness"), ("insight", "in_conversation"), ("persuasion", "in_conversation"),
                 ("lore", "out_of_combat"), ("recovery", "out_of_combat"), ("evasion", "when_attacked"),
                 ("stealth", "out_of_combat"), ("intimidation", "in_conversation"), ("resolve", "at_low_health"),
                 ("deception", "in_settlements"), ("max_health", "always"), ("max_mana", "always"), ("max_stamina", "always")]
    POOLS = {"max_health", "max_mana", "max_stamina"}
    NONC_T = {"in_conversation", "in_settlements", "in_wilderness", "out_of_combat"}
    NONC_M = {"insight", "persuasion", "intimidation", "deception", "stealth", "lore", "performance"}

    def a_StatPassiveSet(self, u, k):
        banned = set()
        m = re.search(r"Not available for this class: (.*)", u)
        if m:
            banned = {x.strip() for x in m.group(1).split(",")}
        need_nc = int(mm.group(1)) if (mm := re.search(r"At least (\d+) must matter outside combat", u)) else 3
        need_co = int(m2.group(1)) if (m2 := re.search(r"At least (\d+) must strengthen companions", u)) else 0
        spec = CLASSES[self.cls]
        cand = []
        if need_co:
            cand += [("companion_damage", "always"), ("companion_durability", "in_wilderness"), ("damage", "with_companion_present")]
        cand += list(spec["stats"]) + self.STAT_POOL
        out, seen = [], set()
        pools = always = nc = 0
        for mod, trg in cand:
            if mod in banned or trg in banned or (mod, trg) in seen:
                continue
            is_pool = mod in self.POOLS
            is_always = trg == "always" or is_pool
            if is_pool and pools >= 1:
                continue
            if is_always and always >= 3:
                continue
            seen.add((mod, trg))
            out.append((mod, trg))
            pools += is_pool
            always += is_always
            nc += (mod in self.NONC_M or trg in self.NONC_T)
            if len(out) == 7:
                break
        return {"passives": [{"name": f"Edge{self.rng.randrange(10**6)}{i}", "description": "d", "modifies": m_, "trigger": t_,
                              "tier": "light"} for i, (m_, t_) in enumerate(out)]}


class Held:
    """(f518) A stand-in put in as the model's source (llm/backend.py use): call it (or undo(), or leave its with-block) to take exactly
    it away again; live() says whether it is the one answering now. .src is the StandIn, .src.calls what it answered."""

    def __init__(self, src):
        from llm import backend
        self.src = src
        self._undo = backend.use(src)

    def __call__(self) -> None:
        self._undo()

    undo = __call__

    def live(self) -> bool:
        from llm import backend
        return backend.source() is self.src

    def __enter__(self) -> "Held":
        return self

    def __exit__(self, *exc) -> None:
        self._undo()


KEEP = object()


def _top_stand_in():
    from llm import backend
    src = backend.source()
    return src if isinstance(src, backend.StandIn) else None


def below():
    """(f518) The stand-in answering now, in the old client's shape (.chat(**k), .embed(**k)): what a test's wrapper calls through to,
    where it read the old client before. Raises when no stand-in is installed (a wrapper over nothing would reach no model at all)."""
    top = _top_stand_in()
    if top is None:
        raise RuntimeError("no stand-in is installed: simlib.install(stub) first (simlib.below)")
    return types.SimpleNamespace(chat=top.chat_fn, embed=top.embed_fn)


def stand_in(chat=KEEP, embed=KEEP, facts: dict | None = None, name: str = "stand-in", below=None) -> Held:
    """(f518) Put in a stand-in source answering with these functions (the old client's shape), where a test assigned the old client's
    before. KEEP (the default) takes the function of the stand-in answering now (its embedder survives a new chat, and a missing one
    stays missing); None drops it; facts are added to its own. Returns the Held: call it to take it away again."""
    from llm import backend
    top = _top_stand_in()
    if chat is KEEP:
        chat = top.chat_fn if top is not None else None
    if embed is KEEP:
        embed = top.embed_fn if top is not None else None
    return Held(backend.StandIn(chat=chat, embed=embed, facts={**(top._facts if top is not None else {}), **(facts or {})}, name=name,
                                below=below))


def install(stub: Stub) -> Held:
    """The stub as the model's source (f518: a StandIn through llm/backend.py, no longer a patch on the client), with the suite's
    settings. Returns the Held: call it to take the stub away again."""
    from llm import backend
    held = Held(backend.StandIn(chat=stub.chat, name="stub"))
    import config
    config.AUDIT_LOG = False         # a stubbed run is not a session anyone audits; keep logs/audit/ for real play
    config.REFUSALS_LOG = False
    from ui import console as _c
    _c.ledger = lambda m: _c.note(m)     # (f325) under the stub, a ledger line is a note: the tests that watch notes see it
    from npc import life
    life.FIRST_BATCH = None          # tests see a place's whole population at once unless they turn the split on
    return held


# ------------------------------------------------------------------ the four characters

CLASSES = {
    "warrior": dict(
        name="Ironbound Vanguard", archetype="warrior", families=["warrior", "guardian"], primary=["strength", "constitution"],
        casting="", points={"strength": 18, "constitution": 14, "dexterity": 8}, per_level={"strength": 2, "constitution": 2, "dexterity": 1},
        weapon="longsword", armor=("chain_shirt", "body"), uses_magic=False,
        actives=[("Brutal Strike", "damage", "moderate", "melee", "stamina"), ("Shield Wall", "defense", "light", "self", "stamina"),
                 ("Cleaving Sweep", "damage", "light", "melee", "stamina")],
        stats=[("damage", "always"), ("max_health", "always"), ("defense", "while_defending"), ("accuracy", "first_round_of_combat"),
               ("intimidation", "in_conversation"), ("perception", "in_wilderness"), ("resolve", "at_low_health")]),
    "mage": dict(
        name="Pyromancer", archetype="mage", families=["mage"], primary=["intelligence", "constitution"], casting="intelligence",
        points={"intelligence": 22, "constitution": 10, "dexterity": 8}, per_level={"intelligence": 3, "constitution": 1, "dexterity": 1},
        weapon="quarterstaff", armor=("robe", "body"), uses_magic=True,
        actives=[("Flame Tongue", "damage", "moderate", "extended", "mana"), ("Ignite", "damage", "light", "ranged", "mana"),
                 ("Frost Ward", "defense", "light", "self", "mana")],
        stats=[("damage", "always"), ("max_mana", "always"), ("lore", "out_of_combat"), ("evasion", "when_attacked"),
               ("perception", "in_wilderness"), ("insight", "in_conversation"), ("recovery", "out_of_combat")]),
    "summoner": dict(
        name="Beastcaller", archetype="support", families=["summoner", "ranger"], primary=["charisma", "wisdom"], casting="wisdom",
        points={"charisma": 14, "wisdom": 14, "constitution": 12}, per_level={"charisma": 2, "wisdom": 2, "constitution": 1},
        weapon="spear", armor=("leather", "body"), uses_magic=True,
        actives=[("Call the Pack", "summon", "moderate", "self", "mana", {"summon_form": "swarm"}),
                 ("Call the Warden", "summon", "moderate", "self", "mana", {"summon_form": "bound"}),
                 ("Hunt Together", "command", "light", "ranged", "mana"), ("Spirit Dart", "damage", "light", "ranged", "mana")],
        stats=[("companion_damage", "always"), ("companion_durability", "always"), ("max_health", "always"), ("perception", "in_wilderness"),
               ("damage", "with_companion_present"), ("persuasion", "in_conversation"), ("recovery", "out_of_combat")]),
    "priest": dict(
        name="Dawnwarden", archetype="support", families=["healer", "paladin"], primary=["wisdom", "constitution"], casting="wisdom",
        points={"wisdom": 18, "constitution": 14, "strength": 8}, per_level={"wisdom": 2, "constitution": 2, "strength": 1},
        weapon="mace", armor=("chain_shirt", "body"), uses_magic=True,
        actives=[("Radiant Smite", "damage", "moderate", "ranged", "mana"), ("Mending Light", "healing", "light", "self", "mana"),
                 ("Warding Prayer", "defense", "light", "self", "mana")],
        stats=[("damage", "always"), ("max_mana", "always"), ("resolve", "at_low_health"),
               ("insight", "in_conversation"), ("recovery", "out_of_combat"), ("persuasion", "in_conversation")]),
    "ranger": dict(
        name="Pathstalker", archetype="rogue", families=["ranger"], primary=["dexterity", "wisdom"], casting="",
        points={"dexterity": 18, "wisdom": 12, "constitution": 10}, per_level={"dexterity": 2, "wisdom": 1, "constitution": 2},
        weapon="shortbow", armor=("leather", "body"), uses_magic=False,
        actives=[("Piercing Shot", "damage", "moderate", "ranged", "stamina"), ("Hunter's Step", "mobility", "light", "self", "stamina"),
                 ("Volley", "damage", "light", "ranged", "stamina")],
        stats=[("damage", "always"), ("accuracy", "always"), ("perception", "in_wilderness"), ("stealth", "out_of_combat"),
               ("max_health", "always"), ("evasion", "when_attacked"), ("lore", "in_wilderness")]),
    "bard": dict(
        name="Silvertongue", archetype="support", families=["bard", "leader"], primary=["charisma", "dexterity"], casting="charisma",
        points={"charisma": 18, "dexterity": 12, "constitution": 10}, per_level={"charisma": 2, "dexterity": 1, "constitution": 2},
        weapon="lute", armor=("leather", "body"), uses_magic=True,
        actives=[("Cutting Verse", "damage", "moderate", "ranged", "mana"), ("Rousing Chorus", "defense", "light", "self", "mana"),
                 ("Dissonant Chord", "damage", "light", "ranged", "mana")],
        stats=[("damage", "always"), ("max_mana", "always"), ("persuasion", "in_conversation"), ("deception", "in_settlements"),
               ("lore", "out_of_combat"), ("evasion", "when_attacked"), ("insight", "in_conversation")]),
    "artisan": dict(
        name="Forgewright", archetype="support", families=["artisan", "warrior"], primary=["strength", "intelligence"], casting="",
        points={"strength": 14, "constitution": 14, "intelligence": 12}, per_level={"strength": 2, "constitution": 2, "intelligence": 1},
        weapon="warhammer", armor=("scale", "body"), uses_magic=False,
        actives=[("Forgeborn Blow", "damage", "moderate", "melee", "stamina"), ("Tempering Focus", "crafting", "light", "self", "stamina"),
                 ("Anvil Guard", "defense", "light", "self", "stamina")],
        stats=[("crafting", "always"), ("damage", "always"), ("max_health", "always"), ("defense", "while_defending"),
               ("max_stamina", "always"), ("insight", "in_settlements"), ("persuasion", "in_settlements")]),
    "smith": dict(
        name="Forgewright", archetype="support", families=["artisan", "warrior"], primary=["strength", "intelligence"], casting="",
        points={"strength": 14, "constitution": 14, "intelligence": 12}, per_level={"strength": 2, "constitution": 2, "intelligence": 1},
        weapon="warhammer", armor=("scale", "body"), uses_magic=False,
        actives=[("Forgeborn Blow", "damage", "moderate", "melee", "stamina"), ("Tempering Focus", "crafting", "light", "self", "stamina"),
                 ("Anvil Guard", "defense", "light", "self", "stamina")],
        stats=[("crafting", "always"), ("damage", "always"), ("max_health", "always"), ("defense", "while_defending"),
               ("max_stamina", "always"), ("insight", "in_settlements"), ("persuasion", "in_settlements")]),
    "paladin": dict(
        name="Oathsworn", archetype="warrior", families=["paladin", "guardian"], primary=["strength", "wisdom"], casting="wisdom",
        points={"strength": 14, "wisdom": 12, "constitution": 14}, per_level={"strength": 2, "wisdom": 1, "constitution": 2},
        weapon="mace", armor=("chainmail", "body"), uses_magic=True,
        actives=[("Smite Evil", "damage", "moderate", "melee", "stamina"), ("Lay on Hands", "healing", "light", "self", "mana"),
                 ("Shield of Faith", "defense", "light", "self", "mana")],
        stats=[("damage", "always"), ("max_health", "always"), ("defense", "while_defending"), ("resolve", "at_low_health"),
               ("persuasion", "in_conversation"), ("insight", "in_conversation"), ("recovery", "out_of_combat")]),
    "monk": dict(
        name="Still Water", archetype="warrior", families=["monk", "rogue"], primary=["dexterity", "wisdom"], casting="",
        points={"dexterity": 16, "wisdom": 12, "constitution": 12}, per_level={"dexterity": 2, "wisdom": 2, "constitution": 1},
        weapon="hand_wraps", armor=("clothes", "body"), uses_magic=False,
        actives=[("Flowing Palm", "damage", "moderate", "melee", "stamina"), ("Wind Step", "mobility", "light", "self", "stamina"),
                 ("Stillness", "defense", "light", "self", "stamina")],
        stats=[("damage", "always"), ("evasion", "when_attacked"), ("max_stamina", "always"), ("perception", "in_wilderness"),
               ("insight", "in_conversation"), ("stealth", "out_of_combat"), ("recovery", "out_of_combat")]),
    "warlock": dict(
        name="Pactbound", archetype="mage", families=["warlock", "necromancer"], primary=["charisma", "constitution"], casting="charisma",
        points={"charisma": 20, "constitution": 12, "dexterity": 6}, per_level={"charisma": 3, "constitution": 1, "dexterity": 1},
        weapon="wand", armor=("robe", "body"), uses_magic=True,
        actives=[("Eldritch Blast", "damage", "moderate", "extended", "mana"), ("Hex", "damage", "light", "ranged", "mana"),
                 ("Dark Ward", "defense", "light", "self", "mana")],
        stats=[("damage", "always"), ("max_mana", "always"), ("intimidation", "in_conversation"), ("deception", "in_settlements"),
               ("lore", "out_of_combat"), ("evasion", "when_attacked"), ("insight", "in_conversation")]),
}


TRAIT_ACTIVES = {
    "warrior": [("Stoneskin", "buff", "moderate", "self", "stamina", {"buff": "bulwark", "buff_stat": "armor"}),
                ("Reactive Plates", "buff", "light", "self", "stamina", {"buff": "thorns"}),
                ("Rending Cleave", "damage", "moderate", "melee", "stamina", {"rider": "rend"}),
                ("Finishing Blow", "damage", "heavy", "melee", "stamina", {"shape": "finisher"})],
    "mage": [("Mage Armor", "buff", "moderate", "self", "mana", {"buff": "bulwark", "buff_stat": "ward"}),
             ("Chain Lightning", "damage", "moderate", "ranged", "mana", {"shape": "chain"}),
             ("Frostbolt", "damage", "light", "ranged", "mana", {"rider": "chill"})],
    "bard": [("Verse of Mending", "buff", "light", "self", "mana", {"buff": "mend"}),
             ("Barbed Barrage", "damage", "moderate", "ranged", "mana", {"shape": "volley"}),
             ("Silver Ward", "buff", "moderate", "self", "mana", {"buff": "bulwark", "buff_stat": "ward"})],
}


def make_character(cls_key: str, rng: random.Random, perks: bool = False):
    """Build a level-1 character the way creation would: abilities, stats, kit - and, with perks=True, a seeded draw of creation perks
    (the balance bots). A test character is plain: no perks unless the test gives it some, so no rule a test pins is quietly changed by
    an All or Nothing or an Above the Law that happened to be drawn."""
    from character import creation
    from core.models import Ability, Archetype, Attributes, Character, Companion
    from engine import abilities, items
    from llm.contracts import ActiveProposal, ClassInterpretation, SummonProposal
    spec = CLASSES[cls_key]
    interp = ClassInterpretation(archetype=Archetype(spec["archetype"]), custom_class=spec["name"], combat_identity="x", themes=["x"],
                                 summary="x", focus="balanced", uses_companions=(cls_key == "summoner"), summoner=(cls_key == "summoner"), families=spec["families"],
                                 primary_attributes=spec["primary"], casting_attribute=spec["casting"])
    actives = []
    extra = TRAIT_ACTIVES.get(cls_key, []) if os.environ.get("SIM_TRAITS") == "1" else []
    for nm, effect, tier, reach, res, *more in list(spec["actives"]) + extra:
        d = dict(name=nm, description=f"a {tier} {effect.replace('_', ' ')} worked at {reach.replace('_', ' ')} reach, drawing on {res}",   # (f424) words
                 effect=effect, tier=tier, reach=reach, resource=res, context="combat")                                                     # a reader can see
        if more:
            d.update(more[0])
        if effect == "summon":
            d["summons"] = (SummonProposal(name="Stone Warden", description="a guardian of living stone")
                            if "Warden" in nm else SummonProposal(name="Spirit Pack", description="a pack of spirit hounds"))
        actives.append(abilities.materialize_active(ActiveProposal(**d)))
    for a in actives:
        if a.resource.value == "mana" and not a.attribute:
            a.attribute = spec["casting"] or "wisdom"
    passives = []
    if perks:
        offered = creation.generate_passives(interp, actives, rng)      # seeded: the same character for the same seed, every run
        # it keeps as many as a player would pick (creation.PICKS), world ones first: the fighter stays plain in a fight (f209)
        from core.rules import MECHANICS as _M
        offered.sort(key=lambda p_: 0 if _M.get(p_.mechanic) and _M[p_.mechanic].kind == "world" else 1)
        passives = offered[:creation.PICKS]
    attrs = {a: 10 for a in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")}
    for a, n in spec["points"].items():
        attrs[a] += n
    c = Character(name=spec["name"], archetype=Archetype(spec["archetype"]), custom_class=spec["name"], uses_companions=(cls_key == "summoner"), summoner=(cls_key == "summoner"),
                  primary_attributes=spec["primary"], casting_attribute=spec["casting"], attributes=Attributes(**attrs),
                  actives=actives, passives=passives, kit_given=True, coins=1000)
    c.equipment = {"main_hand": items.make(spec["weapon"], "common", 1)}
    if cls_key == "summoner":
        c.companions = [Companion(id="wolf", name="Grey Wolf", creature="wolf", kind="beast", role="striker", level=1,
                                  description="a grey wolf")]
        c.bound_summon = next((a.id for a in actives if a.summon_form == "bound"), "")     # the Warden: its Bound summon
    return c, spec


# ------------------------------------------------------------------ (f450) the suite's one way to open a campaign

class Game:
    """One campaign opened for a test (campaign()): its session (f453: engine/session.py, the store and the world are its), the trait
    catalog and the player, and the scene built on them the first time it is asked for. close() closes the session, as main.py does
    when a campaign ends. The rebuild's Bundle B changes only the inside of this class and of campaign(): a test that opens its campaign
    here never changes again when the runtime does."""

    def __init__(self, name: str, session, catalog, player):
        self.name, self.session, self.catalog, self.player = name, session, catalog, player
        self.store, self.world = session.store, session.world
        self._scene = None

    @property
    def scene(self):
        if self._scene is None:
            self._scene = self.session.scene(self.catalog, self.player)
        return self._scene

    def close(self) -> None:
        self.session.close()

    def crash_after_commit(self, kind: str) -> None:
        """(f467) The next operation of this kind that commits stops the game right after its commit and before its telling (an Interrupt
        out of the executor, scenes/world.py operation): the save holds the outcome and its presentation entry, and the next load tells
        it (recover_unshown). The one injection point for the recovery tests."""
        self.scene.crash_after_commit = kind


def campaign(name: str, cls: str = "warrior", seed: int = 1, minutes: int = 600, turn: int = 1, location: str | None = None,
             never_mentor: bool = True, fresh: bool = True, char_seed: int | None = None) -> Game:
    """Open a campaign the way the tests did by hand in a hundred files: a fresh save folder (unless fresh=False, for a save copied
    into place), its seed, clock and turn, a level-1 character of one of the stub's classes, standing where the world starts or at
    `location`, with Maren kept away unless asked for. Returns the Game; `.scene` builds the WorldScene on first use."""
    import shutil
    from engine.session import CampaignSession
    from npc.traits import load_traits
    from storage.campaign import PlayerState
    if fresh:
        shutil.rmtree(f"saves/{name}", ignore_errors=True)
    session = CampaignSession.open(name)                     # (f453) born when the save opens, as in main.py
    store, world = session.store, session.world
    if not store.player_exists():
        store.meta.seed, store.meta.turn, store.meta.minutes = seed, turn, minutes
        store.save_meta()
        char, _ = make_character(cls, random.Random(seed if char_seed is None else char_seed))
        player = PlayerState(character=char, location=location or world.start_location)
        if never_mentor:
            player.mentor["never"] = True
        store.save_player(player)
    return Game(name, session, load_traits(), store.load_player())


def residue() -> dict:
    """(f453) Every binding a session owns that is not at its initial value, by name with what it holds: {} after a clean close."""
    from engine import session
    return session.residue()


def quiet_console(kinds=("narrate", "say", "note", "ledger")) -> list:
    """Mute the console's story outputs and collect what would have been shown, as (kind, text), the four lines every test repeated."""
    from ui import console
    shown: list = []
    for fn in kinds:
        setattr(console, fn, lambda *a, _fn=fn, **k: shown.append((_fn, str(a[0]) if a else "")))
    console.panel = lambda *a, **k: False
    return shown


# ---- (f476) the proof bench: what a person remembers and owes, read through the store by what it is, never by its wording
# Bundle D types memory rows (f478) and turns offers, requests and commitments into obligations (f481). Tests that ask by kind and
# about stay true across those steps: until the rows carry a kind of their own, the kind is read from today's wording (LEGACY_KIND),
# and from then on from the row. Asking for something the save does not record yet (a source, a state) is refused, never a quiet pass.
LEGACY_KIND = (("(my own life) ", "own_life"), ("Saw ", "witnessed"))


def _memory_columns(store) -> set:
    with store._lock:
        return {r[1] for r in store._db.execute("PRAGMA table_info(npc_memory)").fetchall()}


def _legacy_kind(text: str, turn: int) -> str:
    for head, kind in LEGACY_KIND:
        if text.startswith(head):
            return kind
    if turn == -1 and text.startswith("I dealt with "):              # an anchor settling a matter (engine/pulse.py): their own life
        return "own_life"
    if re.search(r" settled .+\.$| was asked about .+, and let it be\.$", text):   # a matter's holders hear how it ended (engine/matters.py)
        return "heard"
    return "experienced"


def remembered(store, holder: str, *, kind: str | None = None, subject: str | None = None, about: str | None = None,
               source: str | None = None, state: str | None = None) -> list[dict]:
    """(f476) The rows a person remembers, every one (not only the window their record carries), oldest first, that match: kind
    (experienced, witnessed, noticed, heard, told, own_life...), subject (whom it is about: "player" today), about (words in it),
    source and state (once the save records them). Each row: {id, day, turn, kind, importance, text, subject}."""
    cols = _memory_columns(store)
    for asked, col in ((source, "source"), (state, "state")):
        if asked is not None and col not in cols:
            raise ValueError(f"the save does not record a memory's {col} yet (Bundle D f478 adds it)")
    pick = ["id", "day", "turn", "kind", "importance", "text"] + [c for c in ("subject", "source", "state") if c in cols]
    with store._lock:
        rows = store._db.execute(f"SELECT {', '.join(pick)} FROM npc_memory WHERE npc_id = ? AND forgotten = 0 ORDER BY id", (holder,)).fetchall()
    out = []
    for r in rows:
        row = dict(zip(pick, r))
        if "subject" not in cols:                                     # before f478: the kind and the subject from the wording
            row["kind"] = _legacy_kind(row["text"], int(row["turn"]))
            row["subject"] = "player" if row["kind"] in ("experienced", "witnessed") else ""
        if kind is not None and row["kind"] != kind:
            continue
        if subject is not None and row.get("subject") != subject:
            continue
        if about is not None and about.lower() not in str(row["text"]).lower():
            continue
        if source is not None and row.get("source") != source:
            continue
        if state is not None and row.get("state") != state:
            continue
        out.append(row)
    return out


def obligation(store, holder: str, about: str | None = None, minutes: int | None = None) -> list[dict]:
    """(f476) What a person is owed or offers, in one shape: {id, kind, state, title}. (f481) The offers from the registry, open or ended
    (offered, taken, released, withdrawn, with the reason it ended); the contracts in the player's hand that they posted (taken); a
    hire's commitments (active). `about`: words in its title."""
    out = []
    from engine import obligations                            # (f481) the offers in the registry, open and ended
    for e in store.find_entities(kind="offer"):
        if e.links.get("npc") == holder:
            out.append({"id": e.data.get("key", e.ref), "kind": e.data.get("family", ""),
                        "state": "open" if (e.data.get("family"), e.state) == ("work", "offered") else e.state,   # the words tests always read
                        "title": str(e.data.get("title", "")), "reason": (e.history[-1][3] if e.history else "")})
    p = store.load_player()
    if p is not None:
        out += [{"id": q["id"], "kind": q.get("kind", ""), "state": "taken", "title": q.get("title", "")}
                for q in p.quests if q.get("issuer") == holder]
        for m in p.party:
            if m.get("id") == holder or m.get("name") == holder:
                out += [{"id": f"commitment:{holder}:{i}", "kind": "commitment", "state": "active", "title": str(c.get("text", c) if isinstance(c, dict) else c)}
                        for i, c in enumerate(m.get("commitments") or [])]
    return [o for o in out if about is None or about.lower() in o["title"].lower()]


def reset_person(store, holder: str) -> None:
    """(f476) A person remembers nothing: every row of theirs deleted, and the window their record carries emptied."""
    with store._lock:
        store._db.execute("DELETE FROM npc_memory WHERE npc_id = ?", (holder,))       # autocommit, as the store's own writes
    if store.npc_exists(holder):
        n = store.load_npc(holder)
        n.memories = []
        store.save_npc(n)


def heard_by(store, about: str) -> list[str]:
    """(f476) Who holds something they heard or were told of `about` (sorted ids): the rows a person did not see for themselves."""
    with store._lock:
        ids = sorted({r[0] for r in store._db.execute("SELECT DISTINCT npc_id FROM npc_memory WHERE forgotten = 0").fetchall()})
    return [nid for nid in ids if remembered(store, nid, kind="heard", about=about) or remembered(store, nid, kind="told", about=about)]


class FakeEmbedder:
    """(f476) A stand-in embedding model: each word of three letters or more lands in one of 64 places by its hash, so texts that share
    words are near and the vectors are the same in every process (md5, never hash()). From tools/sim/embed_test.py."""
    def __init__(self, synonyms: dict | None = None):
        self.synonyms = dict(synonyms or {})
        self.calls: list[int] = []

    def vec(self, text: str) -> list[float]:
        import hashlib
        v = [0.0] * 64
        for w in str(text).lower().replace("clustering: ", "").split():
            w = self.synonyms.get(w.strip(".,?!'"), w.strip(".,?!'"))
            if len(w) >= 3:
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
        return v

    def embed(self, model=None, input=None, **k):
        texts = list(input or [])
        self.calls.append(len(texts))
        return {"embeddings": [self.vec(t) for t in texts]}


def two_characters(ws):
    """(f476) The player's character and a second one beside them, for tests whose subject is a list of characters (Bundle D keys
    regard, obligations and memories by character). The second has an id of their own ("second", f480)."""
    return ws.player.character, _second_character(ws)


def _second_character(ws):
    other, _ = make_character("mage", random.Random(f"second:{ws.player.character.name}"))
    other.name = "Second " + other.name.split()[-1] if other.name else "Second Traveller"
    other.id = "second"                                      # (f480) a character of their own, by id
    return other


def offer(store, holder: str, family: str, terms: dict, who: str = "player", minute: int | None = None):
    """(f481) An offer in the registry for a test, from the person `holder` to the character `who`: what tests set as npc.work_offer
    ("work") or npc.quest_offer ("request") before offers ended for a reason. An old offer's hour (until) is dropped: nothing ends by age."""
    from engine import obligations
    t = {k: v for k, v in dict(terms).items() if k != "until"}
    return obligations.open_(store, family, holder, who, str(t.get("task") or t.get("title") or family), store.meta.minutes if minute is None else minute,
                             terms=t)


def offered(store, holder: str, family: str, who: str = "player") -> dict | None:
    """(f481) The terms of the offer of this family that `holder` has standing for `who`, or None."""
    from engine import obligations
    e = obligations.current(store, family, holder, who)
    return dict(e.data["terms"]) if e is not None else None


def end_offer(store, holder: str, family: str, who: str = "player") -> None:
    """(f481) A test's standing offer ended, as when the one who made it is gone."""
    from engine import obligations
    e = obligations.current(store, family, holder, who)
    if e is not None:
        obligations.close(store, e, "withdrawn" if family == "work" else "released", "gone", store.meta.minutes)


def view(npc, who: str = "player"):
    """(f480) A person's view of a character (npc/models.py Regard), to read or set in a test: what the tests read as npc.trust,
    npc.met_player, npc.knows_player_as and the rest before views were kept per character. The view is made when it is not there."""
    from engine import regard
    return regard.own(npc, who)
