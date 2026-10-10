"""Shapes the LLM is allowed to return. These are proposals, never state.

Set-level validators enforce the composition rules. Their error messages are
sent back to the model on retry, so they are written as instructions.
Per-request rules (reserved names, companion classes) arrive through the
validation context passed to llm.gateway.generate.
"""

from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, model_validator

from core.models import (
    COMPANION_TARGETS,
    NONCOMBAT_TARGETS,
    NONCOMBAT_TRIGGERS,
    POOL_TARGETS,
    Archetype,
    CompanionKind,
    CompanionRole,
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
    uses_companions: bool = False
    families: list[str] = []
    primary_attributes: list[Literal["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]] = []
    casting_attribute: Literal["", "intelligence", "wisdom", "charisma"] = ""

    @model_validator(mode="after")
    def known_families(self):
        self.primary_attributes = list(dict.fromkeys(self.primary_attributes))[:3]
        from core.rules import FAMILIES
        unknown = [f for f in self.families if f not in FAMILIES]
        if unknown:
            raise ValueError(f"unknown families {', '.join(unknown)}; choose from: {', '.join(FAMILIES)}")
        if len(self.families) > 3:
            raise ValueError("choose at most 3 families")
        return self


class CompanionProposal(BaseModel):
    name: str
    description: str
    kind: CompanionKind
    role: CompanionRole


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
    summons: CompanionProposal | None = None
    tags: list[str] = []
    rider: Literal[tuple([""] + list(_AT.RIDERS))] = ""
    shape: Literal[tuple([""] + list(_AT.SHAPES))] = ""
    buff: Literal[tuple([""] + list(_AT.BUFFS))] = ""
    buff_stat: Literal["", "armor", "ward", "both"] = ""
    command: Literal["", "focus", "guard", "press", "hold", "distract"] = ""
    field_use: FieldUse = ""

    @model_validator(mode="after")
    def summon_shape(self):
        from engine import ability_traits as AT
        if self.effect == Effect.BUFF:
            if not self.buff:
                raise ValueError(f"'{self.name}' is a buff ability and must say which buff it is (one of the buffs on offer)")
            self.context = UseContext.COMBAT
            self.reach = Reach.SELF
            if self.buff == "bulwark" and not self.buff_stat:
                self.buff_stat = "ward" if self.resource == "mana" else "armor"
        else:
            self.buff = self.buff_stat = ""
        if self.effect == Effect.COMMAND:
            self.command = self.command or "focus"
        else:
            self.command = ""
        if self.buff != "bulwark":
            self.buff_stat = ""
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
            raise ValueError(f"'{self.name}' is a summon ability and must include summons describing the companion")
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
        effects = [s.effect for s in self.skills]
        if Effect.COMMAND in effects and Effect.SUMMON not in effects:
            raise ValueError("command abilities need at least one summon ability so there is something to command")
        if ctx.get("uses_companions") and effects.count(Effect.SUMMON) < 2:
            raise ValueError("this class relies on companions: include at least 2 summon abilities")
        offered = ctx.get("offers")
        if offered:
            from engine import ability_traits as AT
            AT.repair_shapes(self.skills, offered["shapes"])
            for key, attr, label in (("riders", "rider", "rider"), ("shapes", "shape", "shape")):
                used = [getattr(x, attr) for x in self.skills if getattr(x, attr)]
                stray = [u for u in used if u not in offered[key]]
                if stray:
                    raise ValueError(f"{label} '{stray[0]}' was not on offer - use only: {', '.join(offered[key])}")
                need = min(AT.T["need"][key], len(offered[key]))
                if len(set(used)) < need:
                    raise ValueError(f"use at least {need} different {key} from those on offer ({', '.join(offered[key])}), "
                                     f"one per ability, on abilities they suit")
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
            if len(buffs) > 3:
                raise ValueError("no more than 3 buff abilities")
            if sum(1 for x in self.skills if x.rider or x.shape) > AT.T["max_decorated"]:
                raise ValueError(f"at most {AT.T['max_decorated']} abilities may carry a rider or a shape - leave several plain")
        functions = (offered or {}).get("functions") if offered else None
        if functions:
            from engine import field
            field.repair(self.skills, functions)
        required = ctx.get("min_noncombat", 3)
        selfish = (Effect.HEALING, Effect.CRAFTING, Effect.SUMMON)
        usable_outside = sum(bool(s.context != UseContext.COMBAT and (s.effect in selfish or s.field_use)) for s in self.skills)
        if usable_outside < required:
            raise ValueError(f"only {usable_outside} abilities are usable outside combat; at least {required} must have context out_of_combat AND "
                             f"a field_use taken from the functions on offer, a different one for each (healing, crafting and summon abilities need none)"
                             + (f". Functions on offer: {', '.join(functions)}" if functions else ""))
        return self


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


class PassiveSet(BaseModel):
    passives: list[PassiveProposal] = Field(min_length=15, max_length=15)

    @model_validator(mode="after")
    def composition(self, info: ValidationInfo):
        ctx = _ctx(info)
        all_ps = self.passives
        _check_names(all_ps, ctx.get("reserved_names", []))
        ps = [p for p in all_ps if p.kind == "stat"]
        mech = [p for p in all_ps if p.kind == "mechanic"]
        offered = ctx.get("offered", {})
        if offered:
            bad = sorted({p.mechanic for p in mech if p.mechanic not in offered})
            if bad:
                raise ValueError(f"not in OFFERED MECHANICS, use their ids (o1, o2, ...): {', '.join(bad)}")
        ids = [p.mechanic for p in mech]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"each offered mechanic may be used only once: {', '.join(dupes)}")
        need = ctx.get("min_mechanics", 0)
        if len(mech) < need:
            raise ValueError(f"only {len(mech)} passives are mechanics; at least {need} must be kind mechanic")
        banned = set(ctx.get("unavailable", []))
        used_banned = sorted({p.modifies.value for p in ps if p.modifies.value in banned}
                             | {p.trigger.value for p in ps if p.trigger.value in banned})
        if used_banned:
            raise ValueError(f"not available for this class, replace them: {', '.join(used_banned)}")
        if sum(p.modifies in POOL_TARGETS for p in ps) > 1:
            raise ValueError("at most 1 passive may modify max_health, max_stamina or max_mana")
        always_on = sum(p.trigger == Trigger.ALWAYS or p.modifies in POOL_TARGETS for p in ps)
        if always_on > 4:
            raise ValueError(f"{always_on} passives are always-on; at most 4 may use trigger always")
        required = ctx.get("min_noncombat", 4)
        world_mech = set(ctx.get("world_options", []))
        noncombat = sum(p.modifies in NONCOMBAT_TARGETS or p.trigger in NONCOMBAT_TRIGGERS for p in ps) \
            + sum(p.mechanic in world_mech for p in mech)
        if noncombat < required:
            raise ValueError(f"only {noncombat} passives matter outside combat; at least {required} must have a social, stealth, insight or lore modifier, or an out-of-combat trigger")
        if ctx.get("uses_companions"):
            companion = sum(p.modifies in COMPANION_TARGETS or p.trigger == Trigger.WITH_COMPANION_PRESENT for p in ps) \
                + sum(p.mechanic in set(ctx.get("companion_options", [])) for p in mech)
            if companion < 3:
                raise ValueError("this class relies on companions: at least 3 passives must modify companion_damage or companion_durability, or use trigger with_companion_present")
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


class ActionIntent(BaseModel):
    """How the interpreter reads one free-form player input in the world."""
    kind: Literal["move", "look", "search", "explore", "talk", "leave_conversation", "buy", "sell", "ability", "use", "drop",
                  "pick_up", "give", "show", "discard", "store", "retrieve", "equip", "forage", "craft", "commission",
                  "work", "harvest", "join_guild", "board", "accept_quest", "abandon_quest", "train", "learn_ability",
                  "delve", "leave_dungeon", "wait", "attack", "release", "other"]
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



    wait_minutes: int = 0
    wait_until: Literal["", "before dawn", "dawn", "morning", "midday", "afternoon", "evening", "night", "deep night"] = ""
    summary: str = ""



class CampIntent(BaseModel):
    """What the player means to do near an enemy camp they have not yet fought."""
    kind: Literal["scout", "sneak", "ambush", "bluff", "scare", "charge", "none"]
    target: str = ""
    method: list[Literal["cover", "darkness", "distraction", "patience", "disguise"]] = []
    summary: str = ""


class PartyIntent(BaseModel):
    """What the player means to do about hiring or directing adventurers who travel with them."""
    kind: Literal["list", "hire", "dismiss", "hold", "with", "status", "none"]
    target: str = ""
    summary: str = ""


class ActionPlan(BaseModel):
    """What the player does this message: one to three actions, in order."""
    actions: list[ActionIntent]

    @model_validator(mode="after")
    def at_most_three(self):
        if not self.actions:
            raise ValueError("give at least one action")
        self.actions = self.actions[:3]
        return self

class ResidentProposal(BaseModel):
    slot: int
    name: str
    epithet: str
    description: str
    activity: str


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


class NPCProfile(BaseModel):
    personality: str
    voice: str
    concern: str
    motive: str = ""


class GiftProposal(BaseModel):
    name: str
    description: str = ""
    kind: Literal["key", "quest"] = "key"
    for_whom: str = ""


class WorkOffer(BaseModel):
    task: str
    pay: int = 0            # copper
    minutes: int = 60


class QuestOffer(BaseModel):
    kind: Literal["hunt", "gather", "deliver"]
    what: str                 # the creature to hunt, or the thing to bring
    count: int = 1
    to: str = ""              # for deliver: who it goes to (a name or role)
    item: str = ""            # for deliver: what is carried


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
        if ctx.get("needs_companion"):
            if self.companion not in ctx.get("companions", []):
                raise ValueError("companion must be one of the ids listed under COMPANION OPTIONS")
            if not self.companion_name.strip():
                raise ValueError("give the companion a name")
        elif self.weapon not in ctx.get("weapons", []):
            raise ValueError("weapon must be one of the ids listed under WEAPON OPTIONS")
        return self


class CombatIntent(BaseModel):
    kind: Literal["attack", "ability", "item", "move", "defend", "flee", "tame", "other"]
    target: str = ""
    ability: str = ""
    item: str = ""
    move: Literal["", "closer", "back", "high_ground"] = ""
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


class DialogueFrame(BaseModel):
    """Narration around one line of NPC speech. The speech itself is printed by the engine, unchanged."""
    before: str = ""
    after: str = ""


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


class LearnSet(BaseModel):
    """A few abilities an instructor offers to teach."""
    skills: list[ActiveProposal]

    @model_validator(mode="after")
    def valid(self, info: ValidationInfo):
        ctx = _ctx(info)
        need = ctx.get("count", 3)
        if len(self.skills) != need:
            raise ValueError(f"offer exactly {need} abilities, not {len(self.skills)}")
        _check_names(self.skills, ctx.get("reserved_names", []), "abilities they already know")
        functions = ctx.get("functions")
        if functions is not None:
            from engine import field
            field.repair(self.skills, functions)
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
    kind: Literal["kill", "persuade", "clear", "contract"] = "kill"
    target: str = ""                # kill: a creature id from CREATURES. persuade: a person id from PEOPLE.
                                    # clear: a dungeon place id. contract: empty


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
    news: str              # what people are saying about it
    groups: list[str] = []  # who hears first (knowledge groups)
    stages: list[StageProposal]
    fallout: StageProposal  # what it leaves behind if no one deals with it (or how it simply ends)
    resolution: str = ""   # what would resolve it
    contract: QuestOffer | None = None   # a job the guild would post about it, if any
    paths: list[PathProposal] = []       # rare and campaign events: real ways to end it (the engine drops any that cannot work)
    triumph: StageProposal | None = None  # rare and campaign events: how the place is left if the adventurers end it
    boss_lines: BossLines | None = None   # campaign events with a boss spawn: what that boss says in the final fight

    @model_validator(mode="after")
    def staged(self, info: ValidationInfo):
        need = _ctx(info).get("stages")
        if need and len(self.stages) != need:
            raise ValueError(f"write exactly {need} stages, not {len(self.stages)}")
        return self


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
