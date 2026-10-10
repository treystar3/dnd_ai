"""Shared pieces for the playthrough simulation: a stand-in for the language model, the four test characters,
and instrumentation. The engine is real; only the model's writing is replaced."""

import json
import random
import re
import types
from pathlib import Path

import llm.gateway as gw

# ------------------------------------------------------------------ the stand-in model

NAME_COUNTER = [0]
NARR_COUNTER = [0]
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

    def a_NPCProfile(self, u, k):
        motive = "work toward a goal" if "THEY HAVE A MOTIVE: write one" in u else ""
        return {"personality": "Plain.", "voice": "Plain.", "concern": "A small worry.", "motive": motive}

    def a_NPCReply(self, u, k):
        out = {"speech": "Aye.", "intent": "small_talk"}
        if self.ask_help and "WORK YOU HAVE OFFERED" not in u:
            r = self.rng.random()
            if r < 0.5:
                out["offers_work"] = {"task": "haul sacks", "pay": self.rng.randint(15, 60), "minutes": 60}
            elif r < 0.8:
                out["offers_quest"] = {"kind": "hunt", "what": self.rng.choice(["wolves", "boars", "goblins", "bandits"]), "count": 3}
        return out

    def a_DialogueFrame(self, u, k):
        return {"before": "", "after": ""}

    def a_Narration(self, u, k):
        NARR_COUNTER[0] += 1
        return {"text": f"[scene {NARR_COUNTER[0]}]"}

    # ---- guild instructor
    def a_LearnSet(self, u, k):
        level = int(re.search(r"LEVEL: (\d+)", u).group(1))
        known = re.search(r"ABILITIES THEY KNOW: (.*)", u).group(1).split(", ")
        n = int(re.search(r"Offer exactly (\d+)", u).group(1))
        tiers = ["light", "moderate"] if level < 10 else ["moderate", "heavy"]
        magic = self.cls in ("mage", "summoner", "priest", "bard", "warlock", "paladin")
        out = []
        for i in range(n):
            NAME_COUNTER[0] += 1
            effect = ["damage", "damage", "defense"][i % 3]
            out.append({"name": f"Technique {NAME_COUNTER[0]}", "description": "A learned technique.", "effect": effect,
                        "tier": tiers[i % 2 if effect == "damage" else 0], "reach": "ranged" if magic else "melee",
                        "resource": "mana" if magic else "stamina", "context": "combat"})
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
        stages = [{"description": f"stage {i + 1} of {place} event {NAME_COUNTER[0]}", "effects": [effect() for _ in range(r.randint(0, 2))]}
                  for i in range(n)]
        out = {"title": f"Event {NAME_COUNTER[0]} at {place}", "place": place, "news": f"News of event {NAME_COUNTER[0]}.",
               "groups": r.sample(groups, 2), "stages": stages,
               "fallout": {"description": "it passed", "effects": [effect()]}, "resolution": "deal with it"}
        if r.random() < 0.3:
            out["contract"] = {"kind": "hunt", "what": r.choice(["wolves", "boars", "goblins", "giant spiders", "bandits"]), "count": 3}
        return out

    def a_MotiveStep(self, u, k):
        pid = re.search(r"PERSON: (\S+) -", u).group(1)
        r = self.rng
        status = r.choices(["continuing", "achieved", "abandoned"], weights=[7, 2, 1])[0]
        eff = [{"kind": "mood", "npc": pid, "text": "restless"}]
        return {"happened": "They made a small step.", "effects": eff, "status": status,
                "next_motive": "keep going" if status == "continuing" else "", "gossip": "People talk."}

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

    def a_CampIntent(self, u, k):
        import re as _re
        from scenes.camp_actions import keyword_intent, keyword_methods
        say = _re.search(r"THE PLAYER SAYS: (.*)", u, _re.S)
        text = say.group(1) if say else ""
        return {"kind": keyword_intent(text) or "none", "target": "", "method": keyword_methods(text), "summary": ""}

    def a_RoadEvent(self, u, k):
        hostile = "MUST BE: an ambush" in u
        stopped = "THE PLAYER IS STOPPED HERE" in u
        kind = "ambush" if hostile else self.rng.choice(["find", "meeting", "hazard", "sight", "aid"])
        out = {"title": f"Event {self.rng.randrange(10**5)}", "scene": "You see something on the road.", "kind": kind,
               "detail": "d", "check": "perception" if kind == "hazard" else "", "news": "Word spreads of trouble on the road." if self.rng.random() < 0.3 else "",
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
        need_c = re.search(r"at least (\d+) of the (?:offered )?mechanics (?:marked )?\(?companions", u)
        n_c = min(2, len(comp)) if self.cls == "summoner" else 0
        picks = comp[:n_c] + world[:2]
        for o in combat + world[2:] + comp[n_c:]:
            if len(picks) >= 8:
                break
            if o not in picks:
                picks.append(o)
        picks = picks[:8]
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


def install(stub: Stub):
    gw._client = types.SimpleNamespace(chat=stub.chat)


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
        actives=[("Call the Pack", "summon", "moderate", "self", "mana"), ("Hunt Together", "command", "light", "ranged", "mana"),
                 ("Spirit Dart", "damage", "light", "ranged", "mana")],
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


def make_character(cls_key: str, rng: random.Random):
    """Build a level-1 character the way creation would: abilities, drawn-and-chosen passives, stats, kit."""
    from character import creation
    from core.models import Ability, Archetype, Attributes, Character, Companion
    from engine import abilities, items
    from llm.contracts import ActiveProposal, ClassInterpretation, CompanionProposal
    spec = CLASSES[cls_key]
    interp = ClassInterpretation(archetype=Archetype(spec["archetype"]), custom_class=spec["name"], combat_identity="x", themes=["x"],
                                 summary="x", focus="balanced", uses_companions=(cls_key == "summoner"), families=spec["families"],
                                 primary_attributes=spec["primary"], casting_attribute=spec["casting"])
    actives = []
    for nm, effect, tier, reach, res in spec["actives"]:
        d = dict(name=nm, description="d", effect=effect, tier=tier, reach=reach, resource=res, context="combat")
        if effect == "summon":
            d["summons"] = CompanionProposal(name="Wolf", description="a grey wolf", kind="beast", role="striker")
        actives.append(abilities.materialize_active(ActiveProposal(**d)))
    for a in actives:
        if a.resource.value == "mana" and not a.attribute:
            a.attribute = spec["casting"] or "wisdom"
    passives = creation.generate_passives(interp, actives)
    attrs = {a: 10 for a in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")}
    for a, n in spec["points"].items():
        attrs[a] += n
    c = Character(name=spec["name"], archetype=Archetype(spec["archetype"]), custom_class=spec["name"], uses_companions=(cls_key == "summoner"),
                  primary_attributes=spec["primary"], casting_attribute=spec["casting"], attributes=Attributes(**attrs),
                  actives=actives, passives=passives, kit_given=True, coins=1000)
    c.equipment = {"main_hand": items.make(spec["weapon"], "common", 1)}
    if cls_key == "summoner":
        c.companions = [Companion(id="wolf", name="Grey Wolf", creature="wolf", kind="beast", role="striker", level=1,
                                  description="a grey wolf")]
    return c, spec
