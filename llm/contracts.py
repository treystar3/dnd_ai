"""Shapes the LLM is allowed to return. These are proposals, never state.

Set-level validators enforce the composition rules. Their error messages are
sent back to the model on retry, so they are written as instructions.
Per-request rules (reserved names, companion classes) arrive through the
validation context passed to llm.gateway.generate.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, model_validator, PrivateAttr

from core.models import (
    COMPANION_TARGETS,
    NONCOMBAT_TARGETS,
    NONCOMBAT_TRIGGERS,
    POOL_TARGETS,
    Archetype,
    Effect,
    ModifierTarget,
    PowerTier,
    Reach,
    Trigger,
    UseContext,
)


def _ctx(info: ValidationInfo) -> dict:
    return info.context or {}


def _check_names(items, reserved: list[str], taken_by: str = "active abilities") -> None:
    names = [i.name.strip().lower() for i in items]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise ValueError(f"names must be unique; repeated: {', '.join(dupes)}")
    taken = {r.strip().lower() for r in reserved}
    clashes = sorted(set(names) & taken)
    if clashes:
        raise ValueError(f"these names are already used by {taken_by}, choose different ones: {', '.join(clashes)}")


class ClassInterpretation(BaseModel):
    archetype: Archetype
    custom_class: str
    combat_identity: str
    themes: list[str]
    summary: str
    focus: Literal["combat", "balanced", "social"] = "balanced"
    constraints: list[str] = []
    uses_companions: bool = False      # relies on tamed, living creatures (companions)
    summoner: bool = False             # makes summons with magic - never companions
    families: list[str] = []
    primary_attributes: list[Literal["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]] = []
    casting_attribute: Literal["", "intelligence", "wisdom", "charisma"] = ""
    elements: list[Literal["fire", "cold", "lightning", "poison", "acid", "necrotic", "radiant", "nature"]] = []   # the concept's named magic, if any
    adapted: str = ""          # set when the concept needed something this world lacks: what was asked and what it was made into

    @model_validator(mode="after")
    def known_families(self):
        self.primary_attributes = list(dict.fromkeys(self.primary_attributes))[:3]
        import re as _re
        if _re.fullmatch(r"\W*(none|n/?a|nothing|no|null|nil|not applicable|not adapted|no adaptation|unchanged)?\W*", self.adapted.strip().lower()):
            self.adapted = ""                       # "none", 'none",  ', "n/a" or only stray punctuation: nothing was adapted, and it stays hidden
        from core.rules import FAMILIES
        unknown = [f for f in self.families if f not in FAMILIES]
        if unknown:
            raise ValueError(f"unknown families {', '.join(unknown)}; choose from: {', '.join(FAMILIES)}")
        if len(self.families) > 3:
            raise ValueError("choose at most 3 families")
        return self


class AskedInterpretation(ClassInterpretation):
    """The classification as the model is asked for it: families and primary attributes are required, so a structured answer cannot
    leave them out (a Paladin left unclassified gets no paladin magic, no healing and the wrong casting attribute)."""
    families: list[str] = Field(min_length=1, max_length=3)
    primary_attributes: list[Literal["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]] = Field(min_length=1, max_length=3)
    uses_companions: bool          # (f260) answered every time: a Lich King that commands the dead makes summons
    summoner: bool
    elements: list[Literal["fire", "cold", "lightning", "poison", "acid", "necrotic", "radiant", "nature"]]


class SummonProposal(BaseModel):
    """The model's part of a summon: what the summoned being is called and looks like. Its form, size and element are the engine's."""
    name: str
    description: str = ""


from engine.field import FUNCTIONS as _FIELD_FUNCTIONS  # noqa: E402
from engine import ability_traits as _AT  # noqa: E402

FieldUse = Literal[tuple([""] + list(_FIELD_FUNCTIONS))]    # what an ability does outside combat (data/rules/field.yaml)


class ActiveProposal(BaseModel):
    name: str
    description: str
    effect: Effect
    tier: PowerTier
    reach: Reach
    resource: Literal["stamina", "mana"]
    context: UseContext
    summons: SummonProposal | None = None
    summon_form: str = ""      # for a summon: the engine-planned form (data/rules/summons.yaml); the model never chooses it
    tags: list[str] = []
    rider: Literal[tuple([""] + list(_AT.RIDERS))] = ""
    shape: Literal[tuple([""] + list(_AT.SHAPES))] = ""
    buff: Literal[tuple([""] + list(_AT.BUFFS))] = ""
    movement: str = ""
    heal_form: str = ""        # for healing: the engine-planned form (data/rules/healing.yaml); the model never chooses it
    expressions: list[str] = []  # what its element does (data/rules/spellcraft.yaml), engine-planned; the model never chooses it
    power: float = 0           # engine-set numbers of its own (0 = its tier's); the model never chooses them
    cost_percent: float = 0
    cast_turns: int = 0
    martial_form: str = ""     # a technique's form, its flurry hits and its maneuver - engine-planned (data/rules/martial.yaml)
    hits: int = 0
    maneuver: str = ""
    spell_form: str = ""       # a mana damage spell's form (bolt, blast, burst, curse, charged), engine-planned
    element: str = ""          # the engine-planned element (data/rules/elements.yaml); the model never chooses it
    buff_stat: Literal["", "armor", "ward", "both"] = ""
    command: Literal["", "focus", "guard", "press", "hold", "distract"] = ""
    field_use: FieldUse = ""
    channel: bool = False

    @model_validator(mode="after")
    def summon_shape(self):
        from engine import ability_traits as AT
        if self.effect == Effect.BUFF and not self.buff and not self.buff_stat and self.field_use:
            self.effect = Effect.UTILITY               # a buff with a world function and no combat buff is that world function (a blessing, a mount)
            self.context = UseContext.OUT_OF_COMBAT
        if self.effect == Effect.BUFF:
            self.buff_stat = ""                        # (f235) no buff has a stat; a missing buff is settled against the offer (ActiveSet)
            self.resource = type(self.resource)("mana")   # (f238) every buff is magic: it costs mana
            self.context = UseContext.COMBAT
            self.reach = Reach.SELF
        else:
            self.buff = self.buff_stat = ""
        if self.effect == Effect.COMMAND:
            self.command = self.command or "focus"
        else:
            self.command = ""
        if self.effect == Effect.SUMMON and self.summons is None and self.field_use:
            self.effect = Effect.UTILITY               # "call a phantom steed" is a world function, not a companion that fights
            self.context = UseContext.OUT_OF_COMBAT
        if self.effect not in (Effect.DAMAGE, Effect.CONTROL) or (self.rider and self.effect.value not in AT.RIDERS[self.rider]["applies"]):
            self.rider = ""
        if self.effect != Effect.DAMAGE or self.reach == Reach.AREA:
            self.shape = ""
        if self.effect == Effect.UTILITY:
            self.context = UseContext.OUT_OF_COMBAT   # a utility ability does nothing in a fight
        if self.effect in (Effect.HEALING, Effect.CRAFTING, Effect.SUMMON):
            self.field_use = ""
        elif self.effect == Effect.INFLUENCE and self.context != UseContext.COMBAT and not self.field_use:
            self.field_use = "influence"
        if self.context == UseContext.COMBAT:
            self.field_use = ""
        if self.effect == Effect.SUMMON and self.summons is None:
            raise ValueError(f"'{self.name}' is a summon ability and must include summons naming and describing what it makes")
        if self.effect != Effect.SUMMON:
            self.summons = None
        return self


class FieldAssignment(BaseModel):
    name: str
    function: FieldUse


class FieldAssignments(BaseModel):
    abilities: list[FieldAssignment]


class ActiveSet(BaseModel):
    skills: list[ActiveProposal] = Field(min_length=15, max_length=15)

    @model_validator(mode="after")
    def composition(self, info: ValidationInfo):
        ctx = _ctx(info)
        _check_names(self.skills, [])
        from engine import ability_traits as _T
        _T.repair_buffs(self.skills, (ctx.get("offers") or {}).get("buffs"))
        effects = [s.effect for s in self.skills]
        if ctx.get("summoner") and effects.count(Effect.SUMMON) < 1:
            raise ValueError("this class makes summons: include at least 1 summon ability")
        offered = ctx.get("offers")
        planned = bool(ctx.get("planned"))         # slot-based creation (f249): the engine's plan decided every trait - nothing is added or demanded
        if offered and not planned:
            from engine import ability_traits as AT
            for x in self.skills:                                  # a trait that was not on offer goes (the fill below replaces it)
                if x.rider and x.rider not in offered["riders"]:
                    x.rider = ""
                if x.shape and x.shape not in offered["shapes"]:
                    x.shape = ""
            AT.repair_shapes(self.skills, offered["shapes"])
            AT.dedupe_traits(self.skills)
            AT.fill_traits(self.skills, offered)
            for key, attr, label in (("riders", "rider", "rider"), ("shapes", "shape", "shape")):
                used = [getattr(x, attr) for x in self.skills if getattr(x, attr)]
                stray = [u for u in used if u not in offered[key]]
                if stray:
                    raise ValueError(f"{label} '{stray[0]}' was not on offer - use only: {', '.join(offered[key])}")
                need = min(AT.T["need"][key], len(offered[key]))
                if len(set(used)) < need:
                    raise ValueError(f"use at least {need} different {key} from those on offer ({', '.join(offered[key])}), "
                                     f"one per ability, on abilities they suit")
        if offered:
            from engine import ability_traits as AT
            cmds = [x.command for x in self.skills if x.effect == Effect.COMMAND]
            if len(set(cmds)) < len(cmds):
                raise ValueError("every command ability must use a different command from those on offer: " + ", ".join(offered.get("commands", [])))
            if any(c not in offered.get("commands", []) for c in cmds) and offered.get("commands"):
                raise ValueError("command abilities may only use: " + ", ".join(offered["commands"]))
            buffs = [x.buff for x in self.skills if x.effect == Effect.BUFF]
            if any(b not in offered["buffs"] for b in buffs):
                raise ValueError(f"buff abilities may only use: {', '.join(offered['buffs'])}")
            if offered["buffs"] and not buffs:
                raise ValueError(f"include at least {min(AT.T['need']['buffs'], len(offered['buffs']))} buff ability (effect buff) from those on offer")
            if len(buffs) > AT.T["max_buffs"]:
                raise ValueError(f"no more than {AT.T['max_buffs']} buff abilities")
            if not planned and sum(1 for x in self.skills if x.rider or x.shape) > AT.T["max_decorated"]:
                raise ValueError(f"at most {AT.T['max_decorated']} abilities may carry a rider or a shape - leave several plain")
        functions = (offered or {}).get("functions") if offered else None
        if functions:
            from engine import field
            field.repair(self.skills, functions)
        required = ctx.get("min_noncombat", 3)
        if functions:
            from engine import field
            field.fill(self.skills, functions, required)
        selfish = (Effect.HEALING, Effect.CRAFTING, Effect.SUMMON)
        usable_outside = sum(bool(s.context != UseContext.COMBAT and (s.effect in selfish or s.field_use)) for s in self.skills)
        if usable_outside < required:
            raise ValueError(f"only {usable_outside} abilities are usable outside combat; at least {required} must have context out_of_combat AND "
                             f"a field_use taken from the functions on offer, a different one for each (healing, crafting and summon abilities need none)"
                             + (f". Functions on offer: {', '.join(functions)}" if functions else ""))
        return self


class SlotText(BaseModel):
    slot: int
    name: str
    description: str
    summons: SummonProposal | None = None


def _slot_text_problems(skills, ctx) -> list[str]:
    """What is wrong with the model's names and descriptions for a set of planned slots (empty if nothing)."""
    slots = ctx.get("slots")
    if not slots:
        return []
    from engine import ability_slots as AS
    by_n = {s["n"]: s for s in slots}
    problems = []
    seen = [x.slot for x in skills]
    if sorted(seen) != sorted(by_n):
        raise ValueError(f"give exactly one entry for each number 1 to {len(by_n)}, each with its own slot number")
    for x in skills:
        s = by_n[x.slot]
        passive = s.get("type") == "passive"
        word = "passive trait" if passive else "ability"
        x.name, x.description = x.name.strip(), x.description.strip()
        if not x.name or not x.description:
            problems.append(f"{word} {x.slot} needs a name and a description")
            continue
        if x.name.lower().startswith("command:") or len(x.name) > 40:
            problems.append(f"{word} {x.slot}: the name must be a short evocative title, not '{x.name}'")
        if any(ch.isdigit() for ch in x.description):
            problems.append(f"{word} {x.slot}: no numbers in the description")
        if passive:
            continue
        if s["effect"] == "summon" and x.summons is None:
            problems.append(f"ability {x.slot} is a summon: name and describe what it makes in summons")
        if ctx.get("strict", True):
            why = AS.text_problem(s, x.name, x.description)
            if why:
                problems.append(why)
    try:
        _check_names(skills, ctx.get("reserved_names", []), "things they already know")
    except ValueError as e:
        problems.append(str(e))
    return problems


class SlotNames(BaseModel):
    """The model's part of slot-based creation: a name and a description for each of the 15 planned abilities."""
    skills: list[SlotText] = Field(min_length=15, max_length=15)

    @model_validator(mode="after")
    def composition(self, info: ValidationInfo):
        problems = _slot_text_problems(self.skills, _ctx(info))
        if problems:
            raise ValueError("; ".join(problems[:6]))
        return self

    def proposals(self, slots: list[dict]) -> list["ActiveProposal"]:
        by_n = {x.slot: x for x in self.skills}
        out = []
        for s in sorted(slots, key=lambda s: s["n"]):
            x = by_n[s["n"]]
            out.append(ActiveProposal(
                name=x.name, description=x.description, effect=s["effect"], tier=s["tier"], reach=s["reach"],
                resource=s["resource"], context=s["context"], summons=x.summons if s["effect"] == "summon" else None,
                rider=s["rider"], shape=s["shape"], buff=s["buff"], buff_stat=s["buff_stat"], command=s["command"],
                field_use=s["field_use"], channel=bool(s.get("channel")), movement=s.get("movement", ""),
                heal_form=s.get("heal_form", ""), element=s.get("element", ""), summon_form=s.get("summon_form", ""),
                expressions=list(s.get("expressions") or []), spell_form=s.get("spell_form", ""),
                power=s.get("power", 0), cost_percent=s.get("cost_percent", 0), cast_turns=s.get("cast_turns", 0),
                martial_form=s.get("martial_form", ""), hits=s.get("hits", 0), maneuver=s.get("maneuver", "")))
        return out


class PassiveProposal(BaseModel):
    name: str
    description: str
    kind: Literal["stat", "mechanic"] = "stat"
    modifies: ModifierTarget | None = None
    trigger: Trigger | None = None
    mechanic: str = ""             # for kind mechanic: the id of one of the OFFERED MECHANICS (o1, o2, ...)
    tier: Literal["light", "moderate"]
    tags: list[str] = []

    @model_validator(mode="after")
    def shape(self):
        if self.kind == "stat" and self.mechanic and self.modifies is None:
            self.kind = "mechanic"
        if self.kind == "stat" and (self.modifies is None or self.trigger is None):
            raise ValueError(f"'{self.name}' is a stat passive and needs modifies and trigger")
        if self.kind == "mechanic" and not self.mechanic:
            raise ValueError(f"'{self.name}' is a mechanic passive and needs a mechanic id")
        return self


StatName = Literal["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]


class StatValues(BaseModel):
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int


class PlayerTurn(BaseModel):
    """How the interpreter reads one thing the player typed. The engine decides what it means."""
    kind: Literal["answer", "question", "confirm", "decline", "other"]
    text: str = ""
    picks: list[int] = []
    stats: StatValues | None = None
    priorities: list[StatName] = []
    question: str = ""


class GoddessLine(BaseModel):
    speech: str

    @model_validator(mode="after")
    def not_as_before(self, info: ValidationInfo):
        """(f349) She has said things on earlier returns (the context's `said`): this line opens on none of their openings. Four of five
        deaths in one run began 'Again...'."""
        said = [s for s in (_ctx(info).get("said") or []) if s]
        if not said:
            return self
        def head(t: str) -> str:
            return " ".join(re.findall(r"[a-z']+", (t or "").lower())[:3])
        mine = head(self.speech)
        first = mine.split()[:1]
        if any(mine and mine == head(s) for s in said) or (first and first[0] in ("again", "so", "back") and any(head(s).split()[:1] == first for s in said)):
            raise ValueError("you have opened that way on an earlier return; she remembers every one, and this time begins elsewhere")
        return self


PLACEHOLDERS = {"", "none", "null", "n/a", "na", "nil", "nothing", "unknown", "undefined", "-", "--", "no one", "nobody"}


def blank_placeholders(*fields: str):
    """A before-validator: a model that fills an optional text field with 'none', 'n/a' or 'null' means it left it empty."""
    def clean(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            for f in fields:
                v = data.get(f)
                if isinstance(v, str) and v.strip().strip(".\"'").lower() in PLACEHOLDERS:
                    data[f] = ""
        return data
    return model_validator(mode="before")(classmethod(clean))


def as_lists(*fields: str):
    """A before-validator: a list field given as one string, or as null, is read as a list of that string, or an empty list."""
    def clean(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            for f in fields:
                v = data.get(f)
                if v is None and f in data:
                    data[f] = []
                elif isinstance(v, str):
                    data[f] = [] if v.strip().strip(".\"'").lower() in PLACEHOLDERS or not v.strip() else [v]
                elif isinstance(v, list):
                    data[f] = [str(x) for x in v if x is not None]
        return data
    return model_validator(mode="before")(classmethod(clean))


from engine.actions import KINDS as _ACTION_KINDS  # noqa: E402

class ActionIntent(BaseModel):
    """How the interpreter reads one free-form player input in the world."""
    kind: Literal[_ACTION_KINDS]                        # every kind the game has (engine/actions.py), declared once there
    destination: str = ""
    target: str = ""
    speech: str = ""
    seek: str = ""
    ware: str = ""
    ability: str = ""
    item: str = ""
    count: int = 1
    mark: str = ""
    checks: list[str] = []



    force: bool = False         # they put hands on someone: grab, shove, pin, strike (not a fight; a fight is attack)

    wait_minutes: int = 0
    wait_until: Literal["", "before dawn", "dawn", "morning", "midday", "afternoon", "evening", "night", "deep night"] = ""
    summary: str = ""

    _blank = blank_placeholders("destination", "target", "seek", "ware", "ability", "item", "mark")



class ObjectVerdict(BaseModel):
    """Whether a person or place plausibly holds something the player went looking for, and what exactly it is."""
    plausible: bool
    name: str = ""
    description: str = ""
    worth: Literal["trinket", "ordinary", "valuable", "priceless"] = "ordinary"
    reason: str = ""
    locked: bool = False       # the thing is kept behind a lock (a strongbox, a back room)
    behind: str = ""           # what is locked: "the back room", "a strongbox" (also set for a key: what it opens)
    is_key: bool = False       # the thing the player wants is the key to `behind`


class Clarify(BaseModel):
    """(f321) When a line cannot be read, the world asks one short question in character instead of a system note. speaker is the id of
    someone present (the one being spoken to, when there is one), or 'narrator' for a beat with nobody addressing the player."""
    speaker: str = "narrator"
    line: str = ""

    _blank = blank_placeholders("line")


class PlayerLine(BaseModel):
    """(f368) What the night bot types next (tools/nightbot.py): one line as a player would type it, from the scene, the goal and what
    the game just said. The names the goal turns on (must_name in the context: a place, a person, a creature) must be in it, or the
    game would read the line as something else."""
    line: str = ""

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        self.line = " ".join(self.line.split())
        if not self.line:
            raise ValueError("write the one line the player types")
        if len(self.line) > 240 or len(self.line.split()) > 45:
            raise ValueError("one or two short sentences: under 240 characters")
        low = self.line.lower()
        if low.startswith(("the player", "you ", "the game", "as the player", "narrator")):
            raise ValueError("write it in the first person, as the player types it: 'I ...', or the words they say")
        for name in _ctx(info).get("must_name") or []:
            if name and name.lower() not in low:
                raise ValueError(f"the line must name {name}")
        return self


class AuditMeaning(BaseModel):
    """One plain sentence: what the player wants to do."""
    meaning: str


class AuditVerdict(BaseModel):
    """Whether a described plan does what the player meant."""
    matches: bool
    reason: str = ""


class CampIntent(BaseModel):
    """What the player means to do near an enemy camp they have not yet fought."""
    kind: Literal["scout", "sneak", "ambush", "bluff", "scare", "charge", "none"]
    target: str = ""
    method: list[Literal["cover", "darkness", "distraction", "patience", "disguise"]] = []
    summary: str = ""


class PartyIntent(BaseModel):
    """What the player means to do about hiring or directing adventurers who travel with them."""
    kind: Literal["list", "hire", "promote", "dismiss", "hold", "with", "status", "none"]
    target: str = ""
    summary: str = ""


class ActionPlan(BaseModel):
    """What the player does this message: one to three actions, in order. More than three are kept aside (f332: the scene tells the player
    what was not done) rather than refused, since the gateway would only retry the whole reading."""
    actions: list[ActionIntent]
    _dropped: list = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def at_most_three(self):
        if not self.actions:
            raise ValueError("give at least one action")
        self._dropped = list(self.actions[3:])
        self.actions = self.actions[:3]
        return self

    @property
    def dropped(self) -> list:
        return list(self._dropped)

class MomentDoing(BaseModel):
    who: str                        # a role present ("innkeeper"), or "everyone"
    doing: str                      # a short phrase with no subject: "pulling ale as fast as the mugs come back"


def _like_seen(line: str, seen: list[str]) -> str:
    """A past moment this line is too like, by meaning when the helper model is there (config.SIM_RESTATE), else by a shared run of
    five words; or ''."""
    seen = [s for s in seen if s and s.strip()]
    if not seen:
        return ""
    import config
    from llm import embed
    sims = embed.whole(line, seen)
    if sims is not None:
        best = max(range(len(sims)), key=lambda i: sims[i]) if sims else None
        return seen[best] if best is not None and sims[best] >= config.SIM_RESTATE else ""
    from engine import banter
    mine = banter.grams(line, 5)
    for old in seen:
        if mine & banter.grams(old, 5):
            return old
    return ""


class MomentProposal(BaseModel):
    """(f348) A moment as the model writes it (engine/moments.py): the engine has set the shape, the place, the people and whether
    anyone comes with it; the model makes it particular, and never like one this playthrough has seen (the context's `seen`)."""
    title: str
    line: str
    doings: list[MomentDoing] = []
    visitor_epithet: str = ""
    visitor_look: str = ""
    visitor_doing: str = ""
    mishap: str = ""
    memory: str

    _blank = blank_placeholders("visitor_epithet", "visitor_look", "visitor_doing", "mishap")

    @model_validator(mode="after")
    def particular(self, info: ValidationInfo):
        ctx = _ctx(info)
        if not 1 <= len(self.title.split()) <= 8:
            raise ValueError("title: two to six words, the way the town will name it")
        if not self.line.strip() or len(self.line.split()) > 70:
            raise ValueError("line: one or two sentences, under about sixty words")
        if not self.memory.strip():
            raise ValueError("memory: one line the town will keep of it")
        if re.search(r"\d", self.title + self.line + self.memory):
            raise ValueError("no figures: say it in words, or leave the number out")
        from scenes.voice import STALE
        low = self.line.lower()
        worn = next((s for s in STALE if s in low), "")
        if worn:
            raise ValueError(f"'{worn}' is a stock phrase: say what is actually there")
        roles = set(ctx.get("roles") or []) | {"everyone"}
        labels = {str(k).lower(): v for k, v in (ctx.get("labels") or {}).items()}          # how each is known -> their role
        for d in self.doings:
            w = d.who.strip().lower().replace(" ", "_")
            if w not in roles:
                plain = re.sub(r"^(the|a|an)[ _]", "", w).replace("_", " ")
                found = next((role for lab, role in labels.items() if re.sub(r"^(the|a|an) ", "", lab) == plain), "")
                if not found and plain:                                                 # 'herbalist' for 'the wiry herbalist': the one it can mean
                    near = [role for lab, role in labels.items() if lab.endswith(" " + plain) or plain in lab.split()]
                    found = near[0] if len(near) == 1 else ""
                if not found:
                    raise ValueError(f"doings.who '{d.who}' is nobody here: one of {', '.join(sorted(roles))}")
                w = found
            d.who = w
            if not d.doing.strip() or len(d.doing.split()) > 14:
                raise ValueError("a doing is a short phrase, under fourteen words")
            if re.match(r"^(he|she|they|the|a|an|i|we|you)\b", d.doing.strip(), re.I):
                raise ValueError("a doing has no subject: 'pulling ale as fast as the mugs come back', not 'the innkeeper pulls ale'")
        if ctx.get("visitor"):
            if not (self.visitor_epithet.strip() and self.visitor_look.strip() and self.visitor_doing.strip()):
                raise ValueError("the visitor needs an epithet, a look and a doing")
            if len(self.visitor_epithet.split()) > 5:
                raise ValueError("visitor_epithet: two to four words, how the player would name them before learning their name")
        elif self.visitor_epithet.strip() or self.visitor_look.strip() or self.visitor_doing.strip():
            raise ValueError("no visitor comes with this: leave visitor_epithet, visitor_look and visitor_doing empty")
        if ctx.get("mishap") and not self.mishap.strip():
            raise ValueError("say how the player is caught in it as they come in (mishap)")
        if self.title.strip().lower() in {t.strip().lower() for t in ctx.get("titles") or []}:
            raise ValueError(f"'{self.title}' has been seen in this game already: something new")
        hit = _like_seen(self.line, list(ctx.get("seen") or []))
        if hit:
            raise ValueError(f"too like a moment this game has seen already ('{hit[:80]}'): something new, of a different kind")
        from engine import truth
        for text in (self.title, self.line, self.memory, self.visitor_look, self.visitor_doing, self.mishap):
            run = truth.coined(text, ctx.get("given", ""), ctx.get("known", frozenset()))
            if run:
                raise ValueError(f"'{run}' is no one and nowhere you were given: name only the people and places given, and describe anyone else without a name")
        return self


class ResidentProposal(BaseModel):
    slot: int
    name: str
    epithet: str
    description: str
    activity: str = ""              # (f348) ignored: the engine decides what they are doing (engine/doings.py)


class ResidentSet(BaseModel):
    residents: list[ResidentProposal]

    @model_validator(mode="after")
    def composition(self, info: ValidationInfo):
        ctx = _ctx(info)
        slots = ctx.get("slots", len(self.residents))
        if sorted(r.slot for r in self.residents) != list(range(1, slots + 1)):
            raise ValueError(f"give exactly one resident for each slot from 1 to {slots}")
        _check_names(self.residents, ctx.get("taken_names", []), "other people in this world")
        return self


class MentorReply(BaseModel):
    speech: str
    gesture: str = ""
    moves_on: bool = False          # the player was saying they are ready to go on or get moving, not asking or telling her something

    _blank = blank_placeholders("gesture")

    def spoken(self):
        return [("", self.speech)]

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        from engine import banter, quirks
        self.speech = " ".join(self.speech.split())
        if not self.speech or len(self.speech) > 900:
            raise ValueError("answer in one to four short sentences")
        hit = banter.repeats(self.speech, _ctx(info).get("recent", []))
        if hit:
            raise ValueError(f"you have said something very like '{hit}' lately: say it differently, or say something else")
        self.gesture = quirks.keep_gesture(self.gesture, _ctx(info).get("gesture_state", {}), "Maren Holt")
        return self


class CompanionReply(BaseModel):
    """A hired adventurer answering the player: what they say, what they do, and anything from this exchange worth keeping."""
    speech: str = ""
    gesture: str = ""
    remember: str = ""
    impression: str = ""

    _blank = blank_placeholders("speech", "gesture", "remember", "impression")

    def spoken(self):
        return [("", self.speech)] if self.speech else []

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        from engine import banter
        self.speech = " ".join(self.speech.split()).strip('"\u201c\u201d')
        self.gesture = " ".join(self.gesture.split())
        quiet = bool(_ctx(info).get("silent_ok"))           # hit hard enough that silence is an answer (engine/severity.py)
        if re.fullmatch(r"[(\[]?\s*(silence|silent|says nothing|nothing|no (verbal )?(response|reply|answer))\s*[)\]]?\.?", self.speech, re.I) or \
                (self.speech and not re.search(r"[A-Za-z]", self.speech)):
            self.speech = ""
        if not self.speech and not self.gesture and not quiet:
            raise ValueError("give speech, or a gesture if they say nothing")
        if "*" in self.speech or '"' in self.speech:
            raise ValueError("speech is plain words: no asterisks or quotation marks")
        from engine import quirks
        member = _ctx(info).get("member") or {}
        if self.speech:
            _no_tics(self.speech, (member.get("said") or [""])[-1])          # (f349) no opener twice running, one trailing-off at most
        st = _ctx(info).get("gesture_state", {})
        kept = quirks.keep_gesture(self.gesture, dict(st, gesture_now=True) if (quiet and not self.speech) else st, member.get("name", ""))
        if self.gesture and not kept and not self.speech and not quiet:
            raise ValueError("say something: that gesture was just made, or cannot be shown now")
        self.gesture = kept
        if len(self.remember.split()) > 30:
            raise ValueError("remember is one short sentence")
        if len(self.impression.split()) > 25:
            raise ValueError("impression is one short line")
        ctx = _ctx(info)
        hit = banter.repeats(self.speech, ctx.get("recent", []))
        if hit:
            raise ValueError(f"you have said something very like '{hit}' lately: say it differently, or say something else")
        hit = banter.echoes(self.speech, ctx.get("heard", []))          # (f382) another companion just said it
        if hit:
            raise ValueError(f"someone else has just said '{hit}': answer in your own words")
        if ctx.get("member"):
            from engine import quirks, voices
            why = quirks.voice_check(ctx["member"], self.speech, ctx.get("player", ""), ctx.get("recent", [])) or \
                ("" if ctx.get("kit") is False else voices.check_member(ctx["member"], self.speech))     # (f350) their kit; let go on the relaxed pass
            if why:
                raise ValueError(why)
        why = answers_first(self.speech, ctx.get("answer_to"))
        if why:
            raise ValueError(why)
        retell = ctx.get("retell")
        if retell:
            why = retells(self.speech, retell)
            if why:
                raise ValueError(why)
        else:
            for w in ctx.get("must", []):
                if w.lower() not in self.speech.lower():
                    raise ValueError(f"keep the word '{w}': it is the same thing being told")
        return self


def _first_sentence(text: str) -> str:
    import re
    parts = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return parts[0] if parts else text


def answers_first(speech: str, answer_to: dict | None) -> str:
    """When the player has told them something that matters: the reply's opening must be about that, closer in meaning to what the player
    said than to anything else in the scene (the weather, the place, the fight). Judged by the helper model; without it, not judged."""
    if not answer_to or not speech:
        return ""
    from llm import embed
    import config
    scene = [s for s in answer_to.get("scene", []) if s]
    near = embed.whole(answer_to["said"], scene) if scene else []
    if near is None:
        return ""
    scene = [s for s, v in zip(scene, near) if v < config.SIM_RELEVANT]      # a scene line about the same thing the player said is not 'elsewhere'
    sims = embed.whole(_first_sentence(speech), [answer_to["said"]] + scene)
    if not sims or not scene:
        return ""
    if max(sims[1:]) - sims[0] > config.SIM_ANSWER_MARGIN:
        return "the player just told you something that matters to them: your first words answer that, before anything about where you are"
    return ""


def retells(speech: str, retell: dict) -> str:
    """A secret retold must be that secret, in their own words: closer in meaning to it than to anything else of theirs (their other secret,
    their details). Judged by the helper model; without it, by its rarest words (must, in the context)."""
    from llm import embed
    others = [o for o in retell.get("others", []) if o and o != retell["text"]]
    sims = embed.whole(speech, [retell["text"]] + others)
    if sims is None:
        from engine import quirks
        for w in quirks.must_words(retell["text"]):
            if w.lower() not in speech.lower():
                return f"keep the word '{w}': it is the same thing being told"
        return ""
    import config
    if (others and sims[0] < max(sims[1:])) or (not others and sims[0] < config.SIM_RELEVANT):
        return "tell the thing you decided to tell, in your own words: " + retell["text"]
    return ""


class MentorLines(BaseModel):
    lines: list[str]
    reply: str = ""

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        from engine import mentor
        self.lines = [" ".join(x.split()) for x in self.lines]
        self.reply = " ".join(self.reply.split())
        ctx = _ctx(info)
        if ctx.get("source") is not None:
            why = mentor.check_voice(ctx["source"], self.lines)
            if why:
                raise ValueError(why)
        if ctx.get("want_reply"):
            why = mentor.check_reply(self.reply)
            if why:
                raise ValueError(why)
        return self


class MentorSpeech(BaseModel):
    paragraphs: list[str]

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        from engine import mentor
        self.paragraphs = [" ".join(x.split()) for x in self.paragraphs if x and x.strip()]
        why = mentor.check_speech(self.paragraphs, _ctx(info))
        if why:
            raise ValueError(why)
        return self


class NPCProfile(BaseModel):
    personality: str
    voice: str = ""                 # (f350) unused now: how they talk is the engine's voice kit
    concern: str
    motive: str = ""


class GiftProposal(BaseModel):
    name: str
    description: str = ""
    kind: Literal["key", "quest"] = "key"
    for_whom: str = ""

    _blank = blank_placeholders("name", "description", "for_whom")


class WorkOffer(BaseModel):
    task: str
    pay: int = 0            # copper
    minutes: int = 60

    _blank = blank_placeholders("task")


class QuestOffer(BaseModel):
    kind: Literal["hunt", "gather", "deliver"]
    what: str                 # the creature to hunt, or the thing to bring
    count: int = 1
    to: str = ""              # for deliver: who it goes to (a name or role)
    item: str = ""            # for deliver: what is carried

    _blank = blank_placeholders("what", "to", "item")


def _not_said_again(speech: str, info: ValidationInfo) -> None:
    """(f347) A townsperson does not say the same thing twice. The context's `recent` holds their last few replies (less any drawn by the
    same question, which may fairly get much the same answer); a reply that means what one of them meant is sent back. By meaning when the
    helper model is there (engine/banter.repeats), else by a shared run of words. A reply of a few words ('Aye.') is let be."""
    recent = _ctx(info).get("recent") or []
    if not recent or len((speech or "").split()) < 5:
        return
    from engine import banter
    hit = banter.repeats(speech, list(recent))
    if hit:
        raise ValueError(f"you have said something very like '{hit}' lately; say something new, or say less")


_OPENERS = ("well", "oh", "ah", "aye", "hm", "hmm", "hmph", "right", "now", "look", "see", "ha", "heh", "so", "listen", "mm", "mhm", "eh", "huh")


def opener_of(speech: str) -> str:
    """(f349) The stock word a line opens on ('Well, ...', 'Well now, ...', 'Oh. ...', 'Aye, ...'), or '' when it opens on its matter. A
    plain yes or no is an answer, not a tic."""
    low = re.sub(r"^[\s\"\u201c']+", "", (speech or "").lower())
    m = re.match(r"([a-z]+)\b[\s,.!?;:-]", low + " ")
    return m.group(1) if m and m.group(1) in _OPENERS else ""


def _no_tics(speech: str, last: str = "") -> None:
    """(f349) A speaker does not open two lines running on the same stock word, and trails off at most once in a line: the five-hour run
    had one mouth in five opening 'Well...' twice running, and a reply in four with the dots doing the work the words should. `last` is
    the line they said before this one."""
    if (speech or "").count("...") + (speech or "").count("\u2026") >= 2:
        raise ValueError("at most one trailing-off in a reply: say the rest in words, or end the sentence")
    o = opener_of(speech)
    if o and last and opener_of(last) == o:
        raise ValueError(f"you opened your last line on '{o.capitalize()}' too; open this one on what you have to say")


class NPCReply(BaseModel):
    speech: str
    gesture: str = ""
    intent: Literal["small_talk", "share", "withhold", "lie", "bargain", "help", "refuse", "threaten", "leave"]
    reveals: list[str] = []
    trust_change: int = 0
    told_own_name: bool = False
    learned_player_name: str = ""
    remember: str = ""
    gives: GiftProposal | None = None
    offers_work: WorkOffer | None = None
    offers_quest: QuestOffer | None = None
    journal_note: str = ""

    _blank = blank_placeholders("gesture", "remember", "learned_player_name", "journal_note")

    def spoken(self):
        return [("", self.speech)]

    @model_validator(mode="after")
    def clean_note(self):
        """(f299) A journal note is the player's line about this person. One written in the speaker's own voice ("I must...") or carrying
        stray instructions ("[THE GAME HAS DECIDED...]") is dropped: the plain line from what is known stands until a good one comes."""
        import re as _re
        n = " ".join((self.journal_note or "").split())
        if "[" in n or "]" in n or _re.search(r"\b(I|I'm|I've|I'll|my|me|myself)\b", n):
            n = ""
        self.journal_note = n
        return self

    @model_validator(mode="after")
    def said_again(self, info: ValidationInfo):
        if "*" in self.speech or "_" in self.speech:
            raise ValueError("plain speech only: no asterisks, underscores or markdown in what is said")
        _no_tics(self.speech, _ctx(info).get("last") or "")
        from engine import voices
        why = voices.check(_ctx(info).get("kit") or {}, self.speech)                         # (f350) their own way of talking
        if why:
            raise ValueError(why)
        hit = voices.house_hit(self.speech, _ctx(info).get("house") or ())
        if hit:
            raise ValueError(f"'{hit}' is how everyone in this town has been talking lately; say it your own way")
        from engine import worn as _worn
        lean = _worn.leaned_on(self.speech, list(_ctx(info).get("worn") or [])) if len(self.speech.split()) >= 12 else []
        if len(lean) >= 2:                                                                     # (f349) the worn words are heard, not only told
            raise ValueError(f"'{lean[0]}' and '{lean[1]}' are words everyone here has worn out lately; find other words")
        _not_said_again(self.speech, info)
        return self


_PARTING_STOP = {"you", "then", "the", "a", "and", "to", "of", "your", "on", "in", "now", "well", "right", "good", "day", "go", "be", "it", "that",
                 "with", "for", "there", "out", "off", "all", "so", "do", "my", "me", "i"}


def _parting_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", (text or "").lower()) if w not in _PARTING_STOP and len(w) > 2}


def parting_like(speech: str, heard: list[str]) -> str:
    """(f347) A parting heard lately in this town that this one is the same as: two content words shared, or all of this one's inside
    it ('Safe travels.' after 'Safe travels, friend.'). The ordinary repeat guard skips lines this short, and the chorus was across people."""
    mine = _parting_words(speech)
    if not mine:
        return ""
    for old in heard:
        theirs = _parting_words(old)
        if theirs and (len(mine & theirs) >= 2 or mine <= theirs):
            return old
    return ""


class Parting(BaseModel):
    """(f347) One short line said by the person the player is leaving, in answer to a goodbye. No frame follows it. The context's
    `heard` holds the partings said lately by anyone in this town: a chorus of 'safe travels' across people is sent back."""
    speech: str
    gesture: str = ""

    _blank = blank_placeholders("gesture")

    def spoken(self):
        return [("", self.speech)]

    @model_validator(mode="after")
    def short_and_new(self, info: ValidationInfo):
        if not self.speech.strip():
            raise ValueError("say something, even a word")
        if "*" in self.speech or "_" in self.speech:
            raise ValueError("plain speech only: no asterisks, underscores or markdown in what is said")
        _not_said_again(self.speech, info)
        hit = parting_like(self.speech, list(_ctx(info).get("heard") or []))
        if hit:
            raise ValueError(f"someone here said much the same when the player left lately ('{hit}'): part your own way, in other words, or with only a nod")
        return self


class Narration(BaseModel):
    text: str


class StartingKit(BaseModel):
    """The model picks from lists the engine provides; the engine builds the actual items."""
    weapon: str = ""
    companion: str = ""
    companion_name: str = ""

    @model_validator(mode="after")
    def from_lists(self, info: ValidationInfo):
        ctx = _ctx(info)
        if ctx.get("weapons") and self.weapon not in ctx["weapons"]:
            raise ValueError("weapon must be one of the ids listed under WEAPON OPTIONS")
        if ctx.get("needs_companion"):
            if self.companion not in ctx.get("companions", []):
                raise ValueError("companion must be one of the ids listed under COMPANION OPTIONS")
            if not self.companion_name.strip():
                raise ValueError("give the companion a name")
            self.weapon = ""                                       # a companion takes the weapon's place
        elif self.weapon not in ctx.get("weapons", []):
            raise ValueError("weapon must be one of the ids listed under WEAPON OPTIONS")
        return self


class CombatIntent(BaseModel):
    kind: Literal["attack", "ability", "item", "move", "defend", "interpose", "flee", "tame", "talk", "other"]
    approach: Literal["", "intimidate", "persuade", "deceive"] = ""      # for talk
    target: str = ""
    ability: str = ""
    item: str = ""
    move: Literal["", "closer", "back", "high_ground"] = ""
    step: Literal["", "advance", "withdraw"] = ""     # movement that rides along with another action ("fall back and shoot")
    movement: str = ""        # a movement ability (its id) used on the way, alongside the action (engine/movement.py)
    buff_for: str = ""        # a buff or heal ability's recipient: "" or "self" (the player), or one id from ALLIES (single-target)
    summary: str = ""


class LootName(BaseModel):
    name: str
    description: str


class AccessoryName(BaseModel):
    """A ring or amulet named from the story around it. power_name names its power, if it has one."""
    name: str
    title: str = ""
    lore: str
    power_name: str = ""

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        ctx = _ctx(info)
        if self.name.strip().lower() in {t.lower() for t in ctx.get("taken", [])}:
            raise ValueError(f"the name '{self.name}' already belongs to another item; choose a new one")
        if ctx.get("need_title") and not self.title.strip():
            raise ValueError("give the item a title")
        if ctx.get("need_power") and not self.power_name.strip():
            raise ValueError("name the power: two to four words, lore-appropriate, no numbers")
        return self


class LegendaryName(BaseModel):
    name: str
    title: str
    lore: str

    @model_validator(mode="after")
    def unique(self, info: ValidationInfo):
        taken = {t.lower() for t in _ctx(info).get("taken", [])}
        if self.name.strip().lower() in taken:
            raise ValueError(f"the name '{self.name}' already belongs to another legendary item; choose a new one")
        if not self.title.strip():
            raise ValueError("give the item a title")
        return self


_BACK_TO_WORK = re.compile(r"\b(returns?|returning|turns? back|turning back|goes back|going back|gets? back|getting back|resum\w*|"
                           r"picks? up (?:the|his|her|their) \w+ again|back to (?:his|her|their|the) (?:work|task|tasks|ledger|net|nets|forge|anvil|"
                           r"whetstone|pot|stew|polishing|sharpening|sweeping|mending|counter|parchment|bench)|"
                           r"continues? (?:his|her|their) (?:work|sharpening|polishing|sweeping|mending|scrubbing))\b", re.I)


class DialogueFrame(BaseModel):
    """Narration around one line of NPC speech. The speech itself is printed by the engine, unchanged. (f347) Two things the model
    will not hold to when merely told: the frame never shows the character going back to what they were doing, and it never opens on
    another person's name (the context's `speaker` are the speaker's names; `others`, everyone else present)."""
    before: str = ""
    after: str = ""

    @model_validator(mode="after")
    def about_them_and_not_their_work(self, info: ValidationInfo):
        m = _BACK_TO_WORK.search(self.after or "")
        if m:
            raise ValueError(f"after shows them going back to what they were doing ('{m.group(0)}'): end on what the words changed, "
                             "or leave after empty")
        ctx = _ctx(info)
        mine = {str(s).split()[0].lower() for s in ctx.get("speaker", ()) if str(s).strip()}
        theirs = {str(o).split()[0].lower(): str(o) for o in ctx.get("others", ()) if str(o).strip()}
        for field in (self.before, self.after):
            first = (field or "").strip().split(" ")[0].strip(",.;:'\"").lower()
            first = re.sub(r"['’]s$", "", first)
            if first in theirs and first not in mine and first not in ("the", "a", "an"):
                who = ctx.get("speaker", ["the speaker"])[0]
                raise ValueError(f"the frame is about {who}, but it opens on {theirs[first]}: write it about {who}, by name or as they are known")
        return self


class MechanicChoice(BaseModel):
    option_id: str = Field(description="The id of one of the OFFERED MECHANICS, like o4")
    name: str
    description: str
    tier: Literal["light", "moderate"]


class MechanicSet(BaseModel):
    """Step one of passives: choose and theme mechanics from the offered list."""
    passives: list[MechanicChoice]

    @model_validator(mode="after")
    def valid(self, info: ValidationInfo):
        ctx = _ctx(info)
        offered: dict[str, str] = ctx.get("offered", {})          # option id -> mechanic id
        by_mechanic = {}
        for oid, mid in offered.items():
            by_mechanic.setdefault(mid, oid)
        for p in self.passives:
            raw = p.option_id.strip().lower()
            if raw in offered:
                p.option_id = raw
            elif raw.replace(" ", "_") in by_mechanic:
                p.option_id = by_mechanic[raw.replace(" ", "_")]
            elif raw.isdigit() and f"o{raw}" in offered:
                p.option_id = f"o{raw}"
        bad = sorted({p.option_id for p in self.passives if p.option_id not in offered})
        if bad:
            raise ValueError(f"option_id must be one of {', '.join(offered)}; these are not: {', '.join(bad)}")
        need = ctx.get("count", 8)
        if len(self.passives) != need:
            raise ValueError(f"choose exactly {need} offered mechanics, not {len(self.passives)}")
        ids = [p.option_id for p in self.passives]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"each offered mechanic may be chosen only once: {', '.join(dupes)}")
        _check_names(self.passives, ctx.get("reserved_names", []))
        world = set(ctx.get("world_options", []))
        need_world = ctx.get("min_world", 0)
        if need_world and sum(i in world for i in ids) < need_world:
            raise ValueError(f"choose at least {need_world} of the offered mechanics marked world")
        companion = set(ctx.get("companion_options", []))
        need_companion = ctx.get("min_companion", 0)
        if need_companion and sum(i in companion for i in ids) < need_companion:
            raise ValueError(f"choose at least {need_companion} of the offered mechanics marked (companions)")
        return self


class StatPassive(BaseModel):
    name: str
    description: str
    modifies: ModifierTarget
    trigger: Trigger
    tier: Literal["light", "moderate"]


class StatPassiveSet(BaseModel):
    """Step two of passives: steady stat edges."""
    passives: list[StatPassive]

    @model_validator(mode="after")
    def valid(self, info: ValidationInfo):
        ctx = _ctx(info)
        ps = self.passives
        need = ctx.get("count", 7)
        if len(ps) != need:
            raise ValueError(f"write exactly {need} stat passives, not {len(ps)}")
        _check_names(ps, ctx.get("reserved_names", []), "other abilities and passives")
        banned = set(ctx.get("unavailable", []))
        used_banned = sorted({p.modifies.value for p in ps if p.modifies.value in banned}
                             | {p.trigger.value for p in ps if p.trigger.value in banned})
        if used_banned:
            raise ValueError(f"not available for this class, replace them: {', '.join(used_banned)}")
        if sum(p.modifies in POOL_TARGETS for p in ps) > 1:
            raise ValueError("at most 1 passive may modify max_health, max_stamina or max_mana")
        always_on = sum(p.trigger == Trigger.ALWAYS or p.modifies in POOL_TARGETS for p in ps)
        max_always = ctx.get("max_always", 3)
        if always_on > max_always:
            raise ValueError(f"{always_on} passives use trigger always; at most {max_always} may - give the rest a "
                             "fitting condition such as in_conversation, out_of_combat or in_settlements")
        required = ctx.get("min_noncombat", 0)
        noncombat = sum(p.modifies in NONCOMBAT_TARGETS or p.trigger in NONCOMBAT_TRIGGERS for p in ps)
        if noncombat < required:
            raise ValueError(f"only {noncombat} matter outside combat; at least {required} must. Change one or more of "
                             "the others to modify insight, persuasion, intimidation, deception, stealth, lore or "
                             "performance, or use trigger in_conversation, in_settlements, in_wilderness or out_of_combat")
        companion_needed = ctx.get("min_companion", 0)
        if companion_needed:
            companion = sum(p.modifies in COMPANION_TARGETS or p.trigger == Trigger.WITH_COMPANION_PRESENT for p in ps)
            if companion < companion_needed:
                raise ValueError(f"at least {companion_needed} must modify companion_damage or companion_durability, "
                                 "or use trigger with_companion_present")
        return self


class LessonWant(BaseModel):
    """What a player's request for a lesson is after, read by a small model call (the engine has a word list as a fallback)."""
    kind: Literal["active", "passive", "either"] = "either"
    effect: str = ""            # damage, control, defense, mobility, healing, buff, utility, influence, summon or crafting
    stat: str = ""              # a passive stat the request names (stealth, perception, ...)
    element: Literal["", "fire", "cold", "lightning", "poison", "acid", "necrotic", "radiant", "nature"] = ""   # the element the request names


class LessonNames(BaseModel):
    """The model's part of a lesson: a name and a description for each planned lesson (ability or passive trait)."""
    skills: list[SlotText] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def composition(self, info: ValidationInfo):
        problems = _slot_text_problems(self.skills, _ctx(info))
        if problems:
            raise ValueError("; ".join(problems[:6]))
        return self


# ---------- the pulse: the world moving on its own ----------

class WorldEffect(BaseModel):
    """One mechanical change the engine knows how to make. Unknown references are dropped by the engine."""
    kind: Literal["relation", "mood", "move", "leave", "arrive", "trait", "prices", "danger", "closed", "mark",
                  "loot", "fact", "lead", "spawn", "camp", "seal"]
    npc: str = ""          # a person id from PEOPLE
    other: str = ""        # relation: the other person's id
    place: str = ""        # a place id from PLACES
    text: str = ""         # mood / leave reason / mark / fact text / closed reason
    value: int = 0         # relation change, prices or danger percent
    days: int = 0          # how long a temporary effect lasts
    role: str = ""         # arrive: the role of whoever arrives
    add: str = ""          # trait: trait id to add
    remove: str = ""       # trait: trait id to remove
    groups: list[str] = []  # fact: who knows it
    creature: str = ""     # spawn: a creature id from CREATURES that now haunts the place
    boss: bool = False     # spawn: one dangerous named creature (true) or a few ordinary ones (false)


class StageProposal(BaseModel):
    description: str       # what is happening now, as it would be seen and heard
    effects: list[WorldEffect] = []


class PathProposal(BaseModel):
    """One way the adventurers could end a situation. The engine checks `kind` and `target` against the real world."""
    name: str                       # a short name for the way ("Slay the horror")
    how: str = ""                   # one sentence on what it takes
    kind: Literal["kill", "persuade", "clear", "contract", "find"] = "kill"
    target: str = ""                # kill: a creature id from CREATURES. persuade: a person id from PEOPLE.
                                    # clear: a dungeon place id. contract: empty. find: a place id from PLACES (f317)


class ClueProposal(BaseModel):
    """(f317) One thing someone of the place knows about the situation, in their own words - what they would say if asked, or let slip.
    holder is a person id from PEOPLE, or a role (innkeeper, shepherd) when the right person is not yet made."""
    text: str
    holder: str = ""

    _blank = blank_placeholders("holder")


class MoreBehind(BaseModel):
    """(f322) What a plain-looking job turns out to be the edge of."""
    truth: str = ""
    reveal: str = ""
    clue: str = ""
    path: PathProposal | None = None

    _blank = blank_placeholders("truth", "reveal", "clue")


class PostingStakes(BaseModel):
    id: str
    reason: str
    result: str = ""
    more: MoreBehind | None = None

    _blank = blank_placeholders("result")


class BoardStakes(BaseModel):
    """(f322) The reasons and results for a board's new postings, one entry per posting id given."""
    postings: list[PostingStakes]

    @model_validator(mode="after")
    def known_ids(self, info: ValidationInfo):
        ids = set(_ctx(info).get("ids", []))
        if ids:
            self.postings = [p for p in self.postings if p.id in ids]
            if not self.postings:
                raise ValueError("write one entry per posting, with the posting's id as given")
        return self


class BossLines(BaseModel):
    """What a set-piece boss says, in its own voice, tied to the story that led here. One short spoken sentence or two each."""
    intro: str = ""         # as the fight begins: the last speech, the challenge
    bloodied: str = ""      # when it is first badly hurt
    last_stand: str = ""    # when it should have died and refuses to
    fall: str = ""          # its last words
    captain_intro: str = ""  # (a war leader only) what its war captains cry as they close in


class ThreadProposal(BaseModel):
    title: str
    place: str
    kind: Literal["threat", "social", "economic", "natural", "nature", "trade", "work", "politics", "mystery", "fortune"] = "social"   # (f323) what sort of thing it is
    news: str              # what people are saying about it
    groups: list[str] = []  # who hears first (knowledge groups)
    stages: list[StageProposal]
    fallout: StageProposal  # what it leaves behind if no one deals with it (or how it simply ends)
    resolution: str = ""   # what would resolve it
    contract: QuestOffer | None = None   # a job the guild would post about it, if any
    paths: list[PathProposal] = []       # real ways to end it (the engine drops any that cannot work); every tier (f317)
    triumph: StageProposal | None = None  # rare and campaign events: how the place is left if the adventurers end it
    boss_lines: BossLines | None = None   # campaign events with a boss spawn: what that boss says in the final fight
    truth: str = ""                       # (f317) what is really going on, which the people may not know in full
    clues: list[ClueProposal] = []        # (f317) what one to three people know, in their words
    reveal: str = ""                      # (f317) with a contract: what the one who finishes it finds that the job did not say

    @model_validator(mode="after")
    def staged(self, info: ValidationInfo):
        need = _ctx(info).get("stages")
        if need and len(self.stages) != need:
            raise ValueError(f"write exactly {need} stages, not {len(self.stages)}")
        self.clues = [c for c in self.clues if c.text.strip()][:3]
        return self

    def spoken(self):
        """(f323) Everything the writer says that the world will repeat, checked like speech: nothing named that was not given."""
        out = [("news", self.news), ("truth", self.truth), ("reveal", self.reveal), ("fallout", self.fallout.description)]      # the title is a name, written in capitals
        out += [(f"stage {i + 1}", st.description) for i, st in enumerate(self.stages)]
        out += [(f"clue {i + 1}", c.text) for i, c in enumerate(self.clues)]
        if self.triumph:
            out.append(("triumph", self.triumph.description))
        return [(k, t) for k, t in out if t]


class ThreadTelling(BaseModel):
    """(f331) A situation the engine built, re-told in the world's own words when the player comes where it is (engine/threads.py tell).
    The facts are the engine's and stay: the same place, the same creature, the same people by their trades, the same outcome. Only the
    lines nothing has copied yet are given, numbered, and each comes back re-told in its place; an empty string keeps the line as it was."""
    stages: list[str]               # one per STAGE given, in order (required: the model left it out every time it was optional)
    fallout: str = ""
    truth: str = ""
    clues: list[str]                # one per CLUE given, in order, in that person's own words to a stranger who asked
    reveal: str = ""
    resolution: str = ""

    _blank = blank_placeholders("fallout", "truth", "reveal", "resolution")

    @model_validator(mode="after")
    def counted(self, info: ValidationInfo):
        ctx = _ctx(info)
        need_s, need_c = ctx.get("stages"), ctx.get("clues")
        if need_s == 0:
            self.stages = []                       # nothing was asked for: the model writes one anyway, and that is not a reason to refuse the rest (f369)
        elif need_s is not None and len(self.stages) != need_s:
            raise ValueError(f"write exactly {need_s} stages, one for each STAGE given, in order (an empty string keeps one as it is)")
        if need_c == 0:
            self.clues = []
        elif need_c is not None and len(self.clues) != need_c:
            raise ValueError(f"write exactly {need_c} clues, one for each CLUE given, in order (an empty string keeps one as it is)")
        return self

    def spoken(self):
        out = [("fallout", self.fallout), ("truth", self.truth), ("reveal", self.reveal), ("resolution", self.resolution)]
        out += [(f"stage {i + 1}", t) for i, t in enumerate(self.stages)] + [(f"clue {i + 1}", t) for i, t in enumerate(self.clues)]
        return [(k, t) for k, t in out if t]


class CataclysmStage(BaseModel):
    name: str              # a short name for this stage ("The Ash-Cloud Rise")
    description: str       # what is happening by then, concrete, two sentences at most
    signs: str = ""        # what ordinary people notice and say, one sentence


class CataclysmPath(BaseModel):
    id: str                # one of the path ids the engine gave (PATHS)
    name: str
    how: str = ""


class CataclysmProposal(BaseModel):
    """The telling of a cataclysm. The engine has already decided WHERE it goes, WHEN, who is at risk and what the boss is."""
    title: str
    news: str              # the first rumour, one sentence
    antagonist: str = ""   # the name of the power behind it (a dragon's name, a warlord, a plague-queen...)
    stages: list[CataclysmStage]
    paths: list[CataclysmPath] = []
    triumph: str = ""      # how the world looks if the adventurers end it, two sentences
    ignored: str = ""      # how the world looks if nobody does, two sentences
    keepsake: str = ""     # a name for the thing survivors give the hero (an heirloom's name)
    boss_lines: BossLines | None = None          # the BOSS, if there is one
    side_lines: list[BossLines] = []             # one per war leader, in the order LEADERS were listed

    def spoken(self):
        """(f324) Everything the telling says that the world will repeat, checked like speech."""
        out = [("news", self.news), ("triumph", self.triumph), ("ignored", self.ignored)]
        out += [(f"stage {i + 1}", st.description) for i, st in enumerate(self.stages)] + [(f"signs {i + 1}", st.signs) for i, st in enumerate(self.stages)]
        return [(k, t) for k, t in out if t]

    @model_validator(mode="after")
    def staged(self, info: ValidationInfo):
        need = _ctx(info).get("stages")
        if need and len(self.stages) != need:
            raise ValueError(f"write exactly {need} stages, not {len(self.stages)}")
        return self


class JudgeVerdict(BaseModel):
    """Did the player's deeds end an event? Decided from the ledger of deeds only."""
    verdict: Literal["resolved", "partial", "no"]
    reason: str            # one sentence naming which deeds did it (or why not)
    ending: Literal["victory", "truce", "sealed", "evacuated", "other"] = "other"


class MotiveStep(BaseModel):
    happened: str          # what they did or what happened to them, off-screen
    effects: list[WorldEffect] = []
    status: Literal["continuing", "achieved", "abandoned"] = "continuing"
    next_motive: str = ""  # their goal now, if it continues or changes
    gossip: str = ""       # what others might say about it, if anything


class RoadEvent(BaseModel):
    """Something that happens on the road. The model describes it; the engine rolls any check, loot or fight."""
    title: str
    scene: str                     # what the player sees and hears, two or three sentences, second person
    kind: Literal["find", "meeting", "hazard", "sight", "aid", "ambush"]
    detail: str = ""               # find: what is found. hazard: the obstacle. meeting/aid: who, and what they say or need
    check: str = ""                # hazard: the check that would get the player through (see CHECKS)
    meets_role: str = ""           # a person who is here, as a role id from ROLES (only given when the event stops the player)
    news: str = ""                 # one sentence of word the player picks up, now known in the world
    effects: list[WorldEffect] = []

    @model_validator(mode="after")
    def valid(self, info: ValidationInfo):
        ctx = _ctx(info)
        if ctx.get("hostile") and self.kind != "ambush":
            raise ValueError("this event is a hostile encounter: kind must be ambush")
        if not ctx.get("hostile") and self.kind == "ambush":
            raise ValueError("this event is NOT a fight: pick find, meeting, hazard, sight or aid")
        if self.kind == "hazard" and self.check not in ctx.get("checks", []):
            raise ValueError(f"a hazard needs a check, one of: {', '.join(ctx.get('checks', []))}")
        return self


class DiscoveryProposal(BaseModel):
    """Something found off the map: a small place, or a shorter way between two known places."""
    found: bool                        # false if, honestly, there is nothing here to find
    kind: Literal["place", "track"] = "place"
    name: str = ""                     # "the hunters' hollow", "the smugglers' steps"
    place_type: str = ""               # place: one of the PLACE TYPES
    description: str = ""              # place: what can be seen there. track: what the way is like. Two or three sentences
    to: str = ""                       # track: the place id it leads to, from REACHABLE
    residents: list[str] = []          # place: up to two role ids from ROLES who live or work there, if anyone does
    news: str = ""                     # one sentence of what locals might say about it

    @model_validator(mode="after")
    def valid(self, info: ValidationInfo):
        ctx = _ctx(info)
        if not self.found:
            return self
        if not self.name.strip() or not self.description.strip():
            raise ValueError("a find needs a name and a description")
        if self.kind == "place" and self.place_type not in ctx.get("types", []):
            raise ValueError(f"place_type must be one of: {', '.join(ctx.get('types', []))}")
        if self.kind == "track" and self.to not in ctx.get("reachable", []):
            raise ValueError(f"a track must lead to one of: {', '.join(ctx.get('reachable', []))}")
        bad = [r for r in self.residents if r not in ctx.get("roles", [])]
        if bad:
            raise ValueError(f"unknown roles: {', '.join(bad)}")
        return self


class ArcNodeStory(BaseModel):
    id: str
    title: str = ""            # a short name for this step ("The Gull and Anchor")
    clue: str = ""             # what the player learns here, one or two sentences, pointing at the next place and nothing further
    npc_name: str = ""         # contact: the person's name. lair or boss: the leader's name
    npc_looks: str = ""        # one sentence of appearance
    npc_manner: str = ""       # one sentence of how they speak and carry themselves


class ArcStory(BaseModel):
    """The story the engine's skeleton is dressed in. Written once; the engine never lets it grow."""
    hook_title: str            # what the contract said: "Find Mira, the miller's daughter"
    title: str                 # what the story is called once its size is revealed: "The Ring Along the Roads"
    victim_name: str
    victim_looks: str = ""
    premise: str               # two sentences: what was really going on, as the player will learn it at the end
    nodes: list[ArcNodeStory]

    @model_validator(mode="after")
    def valid(self, info: ValidationInfo):
        ctx = _ctx(info)
        want = ctx.get("nodes", [])
        if want:
            if [n.id for n in self.nodes] != want:
                raise ValueError(f"nodes must be exactly these ids, in this order: {', '.join(want)}")
            named = set(ctx.get("named", want))
            for n in self.nodes:
                if not n.clue.strip() or (n.id in named and not n.npc_name.strip()):
                    raise ValueError(f"node {n.id} needs a clue" + (" and an npc_name" if n.id in named else ""))
            names = [n.npc_name.strip().lower() for n in self.nodes if n.npc_name.strip()] + [self.victim_name.strip().lower()]
            if len(set(names)) != len(names):
                raise ValueError("every name must be different")
            taken = {t.lower() for t in ctx.get("taken", [])}
            if any(n in taken for n in names):
                raise ValueError("a name is already taken: pick different names")
        return self


class ExchangeLine(BaseModel):
    speaker: str
    text: str = ""                # empty: they say nothing (allowed only for those the moment hit hard enough: engine/severity.py)
    gesture: str = ""

    _blank = blank_placeholders("text", "gesture")


class Exchange(BaseModel):
    """People of the world talking to each other: who may speak, how many lines, and no facts that were not given."""
    lines: list[ExchangeLine]

    def spoken(self):
        return [(l.speaker, l.text) for l in self.lines]

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        from engine import banter
        why = banter.check_exchange(self, _ctx(info))
        if why:
            raise ValueError(why)
        return self


class PairDynamic(BaseModel):
    """One line on how two hired adventurers are with each other, what each tends to want from the other, and what each privately thinks of
    the other (their view, in their own head: it may not be fair, and the two need not agree)."""
    dynamic: str
    first_wants: str = ""
    second_wants: str = ""
    first_thinks: str = ""
    second_thinks: str = ""

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        import re as _re
        from engine import mentor
        self.dynamic = " ".join(self.dynamic.split()).strip('"\u201c\u201d')
        self.first_wants = " ".join(self.first_wants.split())[:100]
        self.second_wants = " ".join(self.second_wants.split())[:100]
        self.first_thinks = " ".join(self.first_thinks.split()).strip('"\u201c\u201d')
        self.second_thinks = " ".join(self.second_thinks.split()).strip('"\u201c\u201d')
        if not self.first_thinks or not self.second_thinks:
            raise ValueError("for each of them, one short line on what they privately think of the other")
        for t in (self.first_thinks, self.second_thinks):
            if len(t.split()) > 25 or _re.search(r"\d", t) or "*" in t:
                raise ValueError("each view is one short line, at most twenty-five words, with no numbers")
            if set(_re.findall(r"[a-z]+", t.lower())) & mentor.BANNED_WORDS:
                raise ValueError("do not talk about a game or its parts")
        n = len(self.dynamic.split())
        if not 8 <= n <= 45:
            raise ValueError("one or two sentences, 8 to 45 words")
        if _re.search(r"\d", self.dynamic) or "*" in self.dynamic or '"' in self.dynamic:
            raise ValueError("plain words: no numbers, asterisks or quotation marks")
        if set(_re.findall(r"[a-z]+", self.dynamic.lower())) & mentor.BANNED_WORDS:
            raise ValueError("do not talk about a game or its parts")
        for name in _ctx(info).get("names", []):
            if name.split()[0].lower() not in self.dynamic.lower():
                raise ValueError(f"name both of them: {', '.join(_ctx(info).get('names', []))}")
        return self


class Overheard(BaseModel):
    """What the player's words to one companion mean for the others listening: whom of them they are about, whether they concern the whole
    party, how heavy they are."""
    about: list[str] = []
    party: bool = False
    weight: Literal["light", "personal", "heavy"] = "light"

    @model_validator(mode="before")
    @classmethod
    def _loose(cls, data):
        if isinstance(data, dict):
            g = str(data.get("weight", "") or "").lower().strip()
            data["weight"] = g if g in ("light", "personal", "heavy") else "light"
            a = data.get("about") or []
            data["about"] = [a] if isinstance(a, str) else [str(x) for x in a if x]
            p = data.get("party")
            data["party"] = p if isinstance(p, bool) else str(p).lower().strip() in ("true", "yes", "1")
        return data

    @model_validator(mode="after")
    def _known(self, info: ValidationInfo):
        names = (info.context or {}).get("names") or []
        out = []
        for a in self.about:                               # a first name, or the full one: only those listening count
            hit = [n for n in names if a.strip().lower() in (n.lower(), n.split()[0].lower())]
            if hit and hit[0] not in out:
                out.append(hit[0])
        self.about = out
        return self


class ExtractedFact(BaseModel):
    """One claim from what was said: who said it, whom it is about (subject), what kind of fact, the claim, how heavy it is to talk about,
    how long it stays true (lasts: years - their past, family, a lasting trait or conviction; while - weeks: a plan, a debt, an ongoing
    situation; now - only here and today: where they are, what they are doing) and whether it is common knowledge anyone would know.
    subject is 'self' (the speaker), 'player', 'world', or the name of someone else."""
    speaker: str
    subject: str = "self"
    kind: Literal["backstory", "trait", "possession", "intention", "commitment", "moment", "world"] = "backstory"
    text: str
    weight: Literal["light", "personal", "heavy"] = "personal"
    lasts: Literal["years", "while", "now"] = "years"
    common: bool = False

    @model_validator(mode="before")
    @classmethod
    def older_kinds(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            k = str(data.get("kind", "") or "").lower().strip()
            k = {"life": "backstory", "now": "moment", "self": "backstory", "past": "backstory", "history": "backstory", "possessions": "possession",
                 "intentions": "intention", "plan": "intention", "promise": "commitment", "debt": "commitment", "state": "moment"}.get(k, k)
            if data.get("about") == "world":
                k = "world"
            data["kind"] = k if k in ("backstory", "trait", "possession", "intention", "commitment", "moment", "world") else "backstory"
            g = str(data.get("weight", "") or "").lower().strip()
            data["weight"] = g if g in ("light", "personal", "heavy") else "personal"
            if "text" not in data and "claim" in data:          # the schema calls it claim
                data["text"] = data["claim"]
            subj = " ".join(str(data.get("subject", "self") or "self").split())
            low = subj.lower()
            if low in ("self", "me", "myself", "speaker", "themselves", "themself") or low == str(data.get("speaker", "")).lower():
                subj = "self"
            elif low in ("player", "you", "the player"):
                subj = "player"
            elif low in ("world", "the world", "place", "people", "general"):
                subj = "world"
            data["subject"] = subj
            if subj == "world":
                data["kind"] = "world"
            l = str(data.get("lasts", "") or "").lower().strip()
            l = {"lasting": "years", "forever": "years", "always": "years", "long": "years", "weeks": "while", "days": "while", "season": "while",
                 "today": "now", "moment": "now", "current": "now", "temporary": "while"}.get(l, l)
            data["lasts"] = l if l in ("years", "while", "now") else ("now" if data["kind"] == "moment" else "years")
            cm = data.get("common")
            data["common"] = cm if isinstance(cm, bool) else str(cm).lower().strip() in ("true", "yes", "1")
        return data


class Extracted(BaseModel):
    """New, specific facts someone just stated, by speaker; usually none."""
    facts: list[ExtractedFact] = []

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        names = _ctx(info).get("speakers", [])
        if names:
            by_first = {n.split()[0].lower(): n for n in names}
            for f in self.facts:
                f.speaker = by_first.get(f.speaker.split()[0].lower() if f.speaker.split() else "", f.speaker)
            self.facts = [f for f in self.facts if f.speaker in names]
        self.facts = self.facts[:4]
        return self


class CanonCheck(BaseModel):
    """A new statement against what is already true of a person: the same fact again, a contradiction, or something new; which listed fact
    (1-based) it repeats or contradicts, 0 if none."""
    verdict: Literal["same", "contradicts", "new"] = "new"
    which: int = 0


class StrangerRead(BaseModel):
    """Maren's read of what an armed stranger just said to her: does it settle her, or is it hostile."""
    settled: bool                   # a plain, believable answer: they are a traveller or newcomer, not a bandit
    hostile: bool = False           # a threat, an admission of banditry, or telling her to mind her own business


def _one_off(a: str, b: str) -> bool:
    """One letter added, dropped or changed, or two side by side swapped (a misspelling, not another word)."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:i] + l[i + 1:] == s for i in range(len(l)))


def mend_names(text: str, names: list[str]) -> str:
    """A capitalised word one letter off a name they were given ('Rimlands' for 'Rimelands') is that name, misspelt: put right, not refused.
    Only words of five letters or more, so a short real word is never turned into a name."""
    import re as _re
    given = [n for n in names if len(n) >= 5]
    def fix(m):
        w = m.group(0)
        hit = next((n for n in given if _one_off(w.lower(), n.lower())), None)
        return hit or w
    return _re.sub(r"\b[A-Z][a-z]{4,}\b", fix, text)


class PersonaDetails(BaseModel):
    """Five small personal details for a hire, and their two secrets, written once together: no names of people, no numbers."""
    details: list[str]
    secrets: list[str] = []
    weights: list[str] = []          # how heavy each detail is to talk about, as written (engine/gravity.py); the subject's weight if missing

    @model_validator(mode="after")
    def check(self, info: ValidationInfo):
        import re as _re
        from engine import mentor
        w = [str(x or "").lower().strip() for x in (self.weights or [])]
        self.weights = w if len(w) == len(self.details) and all(x in ("light", "personal", "heavy") for x in w) else []
        allowed = set(_ctx(info).get("names", [])) | {"I", "He", "She", "They", "His", "Her", "Their", "It", "A", "An", "The", "When", "As", "On",
                                                      "In", "At", "Every", "Once", "After", "Before", "If"}
        names = list(_ctx(info).get("names", []))
        self.details = [mend_names(" ".join(d.split()).strip('"'), names) for d in self.details if d and d.strip()]
        if len(self.details) != 5:
            raise ValueError("write exactly five details, one sentence each, one for each subject")
        for d in self.details:
            if len(d.split()) > 30:
                raise ValueError("each detail is one short sentence")
            if _re.search(r"\d", d):
                raise ValueError("no numbers")
            caps = [w for w in _re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]+", d) if w not in allowed]
            if caps:
                raise ValueError(f"no names of people or places ('{caps[0]}'): describe them instead")
            meta = set(_re.findall(r"[a-z]+", d.lower())) & (mentor.BANNED_WORDS - {"game", "model", "engine", "player"})
            if meta:                                       # a game of dice, a carved model, a lute player are all of the world
                raise ValueError(f"no words about the game itself ('{sorted(meta)[0]}')")
        want = _ctx(info).get("secrets", 0)
        self.secrets = [mend_names(" ".join(x.split()).strip('"'), names) for x in self.secrets if x and x.strip()][:want]
        if want and len(self.secrets) != want:
            raise ValueError(f"write {want} secrets, one for each secret theme, in the first person")
        for x in self.secrets:
            if len(x.split()) > 45 or _re.search(r"\d", x):
                raise ValueError("each secret is one or two sentences, with no numbers")
            caps = [w for w in _re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]+", x) if w not in allowed]
            if caps:
                raise ValueError(f"no names of people in a secret ('{caps[0]}')")
        return self
