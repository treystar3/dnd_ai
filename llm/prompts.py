"""Prompt text. Category lists are built from the engine enums so they never drift."""

from core.models import (
    COMPANION_TARGETS,
    NONCOMBAT_TARGETS,
    NONCOMBAT_TRIGGERS,
)
from core.rules import FAMILIES, STATS, TRIGGERS
from llm.contracts import ClassInterpretation


def _list(values) -> str:
    return ", ".join(v.value for v in values)


WORLD_RULES = """THE WORLD (Meravia) - everything you write must belong to it:
- It is a medieval high-fantasy world: swords, bows, magic, faith, beasts, guilds, alchemy and clockwork.
- Weapons that exist: clubs, daggers, spears, axes, maces, hammers, swords, lances, slings, bows, crossbows, staves, wands, charms, instruments, bare hands.
- Nothing powered by gunpowder or engines exists: no guns, firearms, rifles, pistols, cannons, bullets, grenades, explosives, electricity,
  motors, vehicles, computers or other modern technology. Alchemy, clockwork and spring-and-gear devices do exist.
- Bows, crossbows and slings need no arrows, bolts or stones: nobody in Meravia counts ammunition, carries a quiver or runs out, and
  nobody sells arrows. A bow in hand is always ready to shoot. Never say a character lacks arrows or must find some."""

# what every speaker is told (the narrator, townsfolk, hires, Maren); creation prompts get the concept rule below as well
WORLD_FACTS = WORLD_RULES + """
- If a concept needs something that does not exist (a gunslinger, a hacker, a pilot), translate it to the closest thing that does (a
  crossbow marksman, a trickster of locks and secrets, a rider) and write the translated class, never the missing thing."""

CLASSIFY_SYSTEM = """You interpret a player's character concept for a high-fantasy RPG.
Map the concept to exactly one archetype: warrior, mage, rogue, or support.
The archetype is the mechanical foundation; pick the one that best fits how the character fights or contributes.
Give the custom class a short evocative name. Use the player's own name for it if they gave one.
combat_identity is a few words on weapon and fighting style.
themes are 2-4 short thematic keywords.
summary is one or two sentences describing the class in-world.
focus is how the concept spends its time: combat (mostly fighting), balanced (fighting and life beyond it), or social (mostly people, performance, knowledge, trade or intrigue rather than fighting).
adapted: leave empty unless the concept needs something that does not exist in this world (see THE WORLD below). Then write one plain sentence saying what
  the player asked for and what you made of it instead (for example "Firearms do not exist here; I read this as a crossbow marksman."), and write the
  class name, combat_identity, themes and summary for the translated version only.
constraints are explicit limits or preferences the player stated, such as "avoids melee" or "never kills". Empty list if none. Never invent constraints.
uses_companions is true only if the concept relies on COMPANIONS: living creatures it has tamed, raised or bonded with - animals and
  beasts that grow with it (a beast-tamer, a falconer, a druid with a wolf). Never for things made with magic.
summoner is true only if the concept MAKES beings with magic to fight or act for it - conjured spirits, animated constructs or guardians,
  raised dead, elementals, familiars it created. A summon is made, not tamed: a summoner is never uses_companions for its summons.
  A concept can be both (a druid with a wolf who also calls up thorn spirits).
primary_attributes are the 2 or 3 attributes this concept relies on most, most important first:
  strength (heavy weapons, raw force), dexterity (finesse, bows, speed, agility), constitution (toughness, endurance),
  intelligence (arcane study and spellcraft), wisdom (faith, nature, perception), charisma (presence, performance, pacts).
casting_attribute is what powers this concept's magic, if it has any: intelligence (studied, arcane - wizards,
  artificers of spells), wisdom (faith, nature, spirits - clerics, druids, shamans), charisma (pacts, performance,
  innate gifts - warlocks, bards, sorcerers). Leave it empty only if the concept uses no magic at all.
elements: only if the concept names the element(s) its magic works in, list them from: fire, cold, lightning, poison, acid, necrotic,
  radiant, nature ("a fire mage" -> [fire]; "a druid of thorn and root" -> [nature]; "a witch of storm and frost" -> [lightning, cold]; "a plague doctor" -> [poison]). Leave it empty
  when the concept does not name one - never guess an element from mood alone.
families are one to three kinds of class this concept draws on, most important first. Choose from:
{families}
  A Dragoon might be warrior and ranger; a bard who heals, bard and healer; a necromancer with thralls, necromancer and
  summoner; a warlock bound to a dark patron, warlock and mage; a martial-arts monk, monk and rogue.
Respond only with JSON matching the schema.""".replace("{families}", "\n".join(f"  {k}: {v.description}" for k, v in FAMILIES.items())) + "\n\n" + WORLD_FACTS

ACTIVES_SYSTEM = f"""You design level 1 ACTIVE abilities for a custom RPG class.
An active ability is something the character deliberately does in a moment.
Propose exactly 15 distinct abilities with unique names.
They must be appropriate for a beginner: grounded, modest, not world-shaking.
Make them varied so the player has a real choice.
You only choose categories; the game engine decides all numbers. Never include numbers in descriptions.

effect:
  damage, healing, control, mobility, utility: ordinary effects. (There are no defensive stances: a guard or ward is a buff.)
  influence: sways a person's feelings, beliefs or choices (calm, frighten, charm, persuade, unsettle).
  summon: calls or creates a companion that stays and acts on its own turns.
  command: directs the companions already present. Give it a command from the commands on offer (every command ability a different one).
  buff: a combat-only effect on the caster for a few rounds: raises armor or ward, reflects damage onto melee attackers, or
    mends them each turn. Reach is self and context is combat. Set buff to one of the buffs on offer.
  crafting: improves the next thing they make - forging, leatherwork, brewing, cooking. Only for classes that are
    about making things, and then include 2 or 3.
tier: light, moderate, or heavy. Most should be light or moderate; at most 3 heavy.
reach: self, melee, extended, ranged, or area.
resource: stamina for physical techniques, mana for spell ones.
context: combat, out_of_combat, or both. A utility ability is always out_of_combat.
  The request states how many abilities must be usable outside combat (out_of_combat or both): social, stealth, exploration, knowledge, performance or survival uses that fit the class.
  If the class focus is social, most of its abilities should be about people, performance, knowledge or intrigue, not fighting.
rider and shape: the request lists the riders and shapes on offer for this character. Use at least 3 different riders and
  at least 2 different shapes, each on an ability it suits, one rider or shape per ability (never both on one ability), and use
  only those on offer. Use each rider and each shape on ONE ability only - never repeat one. Leave at least 6 abilities plain. Riders go on damage or control abilities; shapes on single-target
  damage abilities (not reach area). Leave both empty on everything else.
  Name and describe each such ability so it fits what it does (a chilling rider belongs on a frost spell, a volley on a barrage).
  A rider or shape must match what the ability actually is and says: never put ricochet, chaining or sweeping on an ability described as
  one target, sweeping on a ranged spell, or reliable on something wild or chaotic. If nothing on offer suits an ability, leave it plain.
  Give a multi-hit shape to an ability whose description is several strikes (a rapid sequence of fireballs, a flurry, a spread of arrows),
  and never put some other shape on an ability that describes several hits. Multi-hit shapes (double, volley, barrage) must be named and described for THIS class: an archer's Multishot or Rain of Arrows,
  a monk's Flurry of Blows, a mage's Arcane Missiles, a rogue's Fan of Knives or Twin Stab, a warrior's Rapid Strikes - never a generic
  name. A barrage is five quick small hits, a double strike is two, a volley is three. Companion-only options (rouse, packhunt) are
  offered only to classes that fight with companions. Put a buff's flavor in its name (a mage's Mana Shield, a berserker's Blood Frenzy,
  a paladin's Flame Blade for elemental weapon - the element in an elemental weapon's name or description is the element it deals).
field_use: REQUIRED for every ability whose context is out_of_combat or both, except healing, crafting and summon
  abilities. It is what the ability does in the world outside a fight. The request lists the FUNCTIONS ON OFFER for this
  character: pick the one that fits the ability and use ONLY those. Two abilities may never share a function, so each
  function on offer is used at most once. If an ability fits none that are left, make it a combat ability (context combat)
  and leave field_use empty. A function that is "always on" still counts as one ability's field_use.
A world function such as phantom_steed (a spectral mount) or summon_labor (a servant to carry things) is effect utility with its
  field_use - never effect summon. Effect summon is only for a being the character makes with magic, and it needs summons.
summons: only for a summon ability, and required for it. Name and describe what it makes: name, one-sentence description.
  The engine has already decided its form (under "does") - depict that form; its size and element are the engine's too.

If the class makes summons: include at least one summon ability. If it keeps companions or makes summons, include 2 to 3 command abilities.
Name command abilities as evocative techniques, calls or signals, never in the form "Command: X".
The class constraints are absolute. If it says the character avoids melee, give no melee-reach abilities.
description is one sentence describing what the ability looks and feels like.
Respond only with JSON matching the schema."""

SLOTS_SYSTEM = f"""You name and describe the level 1 ACTIVE abilities of a custom RPG class.
The game engine has already decided exactly what each of the 15 numbered abilities does: its kind, power, reach, cost and special effect.
Your job is only to give each one a NAME and a one-sentence DESCRIPTION, written for the class, so that the ability reads as exactly what
the engine made - nothing more, nothing less.

For every numbered ability:
- name: a short evocative title of 1 to 4 words, in the class's own voice. Every name unique. Never "Command: X". No numbers.
- description: ONE sentence of what it looks and feels like, no numbers. Depict the mechanic given under "does" and follow "write it as".
  Do not add anything the ability does not do: no extra hits, no area effect, no healing, no mount, no companion, no status effect it lacks.
  A single-blow ability is one strike or one blast at one target. A several-strikes ability is a flurry, volley or series, named to suit the class.
  A defense, mobility, buff or self ability acts on the caster alone. An outside-combat function is shown by what the description does
  (looking ahead, making camp, working a lock, bargaining), so the name and description should make that function obvious.
- slot: the ability's number, exactly as given.
- summons: only for a summon ability, and required for it. Name and describe what it makes: name, one-sentence description.
    The engine has already decided its form (under "does") - depict that form; its size and element are the engine's too.
Flavor every name and description from the class's own themes and magic, never from another class's: a holy paladin's quick step is
holy or martial, never shadowy; a necromancer's is never holy. The words under "does" say what happens, not what it should look like.
Make the 15 sound varied, and keep them grounded for a beginner. Respect the class constraints (if the character avoids melee, never
depict melee fighting). If the class uses companions, name command abilities as evocative calls or signals.
Respond only with JSON matching the schema."""

def slots_user(interp: ClassInterpretation, slot_text: str) -> str:
    return class_context(interp) + "\n\nTHE 15 ABILITIES (the engine has decided these - name and describe each):\n" + slot_text + \
        "\n\nName and describe all 15."


_STAT_LINES = "\n".join(f"  {s.id}: {s.covers}" for s in STATS.values())
_TRIGGER_LINES = "\n".join(f"  {t.id}: {t.condition}" for t in TRIGGERS.values())

PASSIVES_SYSTEM = f"""You design level 1 PASSIVE traits for a custom RPG class.
A passive is NOT an action. It is a quality, instinct, or piece of training that changes how the character performs.
Never describe the character performing a move. Describe what they are, know, or have become.
Propose exactly 15 distinct passives with unique names, written in the class's own theme and voice.

There are two kinds of passive:

kind "mechanic": changes HOW something works. Pick one of the OFFERED MECHANICS in the request, by its id
  (o1, o2, ...), and make it the class's own: give it a name and description that fit the theme
  (a Dragoon's counterattack is not a bard's). Some offered mechanics only work under a condition - let the
  name and description reflect it. The game sets the strength from the tier. Each id may be used at most once.

kind "stat": a steady edge. Choose what it improves (modifies) and when (trigger):
  modifies:
{_STAT_LINES}
  trigger:
{_TRIGGER_LINES}

Rules:
- The request states how many passives must be mechanics. Mechanics are what make a class feel unique, so favor
  the ones that fit, and avoid the generic.
- At most 1 stat passive may modify max_health, max_stamina or max_mana, and it must use trigger always.
- At most 4 stat passives may use trigger always.
- The request states how many passives must matter outside combat: world mechanics, or stat passives that modify
  {_list(NONCOMBAT_TARGETS)}, or use trigger {_list(NONCOMBAT_TRIGGERS)}.
- If the class uses companions, at least 3 passives must strengthen companions: modify {_list(COMPANION_TARGETS)},
  use trigger with_companion_present, or be an offered mechanic marked (companions).
- Never reuse any name listed as already taken, and never use anything listed as not available.
tier: light or moderate only. Most should be light.
For a stat passive leave mechanic empty; for a mechanic passive leave modifies and trigger empty.
description is one sentence of in-world flavor: where the quality comes from or how it feels. Do not restate numbers.
Respond only with JSON matching the schema."""


def class_context(interp: ClassInterpretation) -> str:
    constraints = "; ".join(interp.constraints) if interp.constraints else "none"
    return (
        f"Archetype: {interp.archetype.value}\n"
        f"Class: {interp.custom_class}\n"
        f"Combat identity: {interp.combat_identity}\n"
        f"Themes: {', '.join(interp.themes)}\n"
        f"Summary: {interp.summary}\n"
        f"Families: {', '.join(interp.families) or 'unspecified'}\n"
        f"Focus: {interp.focus}\n"
        f"Constraints: {constraints}\n"
        f"Elements: {', '.join(getattr(interp, 'elements', []) or []) or 'any'}\n"
        f"Keeps companions (tamed, living): {'yes' if interp.uses_companions else 'no'}\n"
        f"Makes summons (with magic): {'yes' if getattr(interp, 'summoner', False) else 'no'}"
    )


def actives_user(interp: ClassInterpretation, min_noncombat: int, offers: str = "") -> str:
    return (
        class_context(interp)
        + (f"\n\n{offers}" if offers else "")
        + f"\n\nRequired: at least {min_noncombat} abilities usable outside combat."
        + "\nGenerate 15 active abilities."
    )


MECH_PASSIVES_SYSTEM = """You design level 1 PASSIVE traits for a custom RPG class. A passive is a quality, instinct
or piece of training - never an action the character performs.

The request lists OFFERED MECHANICS, each with an id like o4. Choose the requested number of them - the ones that
best fit this class - and make each the class's own:
  option_id: the offered id you chose, exactly as written (o4).
  name: a short evocative name in the class's theme. A Dragoon's counterattack and a bard's are named differently.
  description: one sentence of in-world flavor - where the quality comes from or how it feels. If the mechanic only
    works under a condition, let the flavor reflect it. No numbers.
  tier: light or moderate. Most should be light.
Never reuse a name listed as already taken. Respond only with JSON matching the schema."""


def mech_passives_user(interp, taken: list[str], offered_lines: list[str], count: int, min_companion: int,
                       min_world: int = 0) -> str:
    extra = f"\nAt least {min_world} must be world mechanics." if min_world else ""
    extra += f"\nAt least {min_companion} must be mechanics marked (companions)." if min_companion else ""
    return (
        class_context(interp)
        + f"\nNames already taken: {', '.join(taken)}"
        + "\n\nOFFERED MECHANICS:\n" + "\n".join(f"  {line}" for line in offered_lines)
        + f"\n\nChoose exactly {count}.{extra}"
    )


STAT_PASSIVES_SYSTEM = f"""You design level 1 PASSIVE traits for a custom RPG class: steady edges in one stat.
A passive is a quality, instinct or piece of training - never an action the character performs.

Each passive has:
  modifies - the one thing it improves:
{_STAT_LINES}
  trigger - when it applies:
{_TRIGGER_LINES}
  name - short and evocative, in the class's theme.
  description - one sentence of in-world flavor. No numbers.
  tier - light or moderate. Most should be light.

Rules:
- At most 1 may modify max_health, max_stamina or max_mana, and it must use trigger always.
- At most 3 may use trigger always. Prefer conditions that fit the class.
- The request says how many must matter outside combat: modify {_list(NONCOMBAT_TARGETS)},
  or use trigger {_list(NONCOMBAT_TRIGGERS)}.
- Vary what they modify. Never reuse a name listed as taken, never use anything listed as not available.
Respond only with JSON matching the schema."""


def stat_passives_user(interp, taken: list[str], count: int, min_noncombat: int, fit_stats: list[str],
                       fit_triggers: list[str], unavailable: list[str], min_companion: int) -> str:
    lines = [class_context(interp),
             f"Names already taken: {', '.join(taken)}",
             f"Best-fit modifies for this class: {', '.join(fit_stats) or 'no strong preference'}",
             f"Best-fit triggers for this class: {', '.join(fit_triggers) or 'no strong preference'}"]
    if unavailable:
        lines.append(f"Not available for this class: {', '.join(unavailable)}")
    lines.append(f"\nWrite exactly {count}. At least {min_noncombat} must matter outside combat.")
    if min_companion:
        lines.append(f"At least {min_companion} must strengthen companions (companion_damage, companion_durability, "
                     "or trigger with_companion_present).")
    return "\n".join(lines)


LESSON_SYSTEM = f"""You are a guild instructor - a retired adventurer - naming the lessons you offer a member.
The game engine has already decided exactly what each numbered lesson teaches: an ABILITY (what it does, its power, reach, cost
and special effect) or a PASSIVE TRAIT (a lasting quality). Your job is only to give each one a NAME and a one-sentence
DESCRIPTION, written for the member's class and what they asked to learn, so it reads as exactly what the engine made - nothing more.

For every numbered lesson:
- name: a short evocative title of 1 to 4 words. Every name unique, and different from what they already know. No numbers.
- description: ONE sentence, no numbers. For an ability, depict the mechanic under "does" and follow "write it as"; add nothing it does not do
  (no extra hits, area effect, healing, mount, companion or status). A single-blow ability is one strike or blast at one target.
  An ability on the caster alone has no target. An outside-combat function shows in what the description does.
  For a PASSIVE TRAIT describe what the character IS, KNOWS or HAS BECOME - never an action they take.
- slot: the lesson's number, exactly as given.
- summons: only for a summon ability, and required for it. Name and describe what it makes: name, one-sentence description.
    The engine has already decided its form (under "does") - depict that form; its size and element are the engine's too.
Respect the class and its habits (if the character avoids melee, never depict melee fighting). Grounded and practical for their level.
Respond only with JSON matching the schema."""


def lesson_user(c, request: str, slot_text: str) -> str:
    known = ", ".join([a.name for a in c.actives] + [p.name for p in c.passives]) or "none"
    return (f"CLASS: {c.custom_class} ({c.archetype.value})\nLEVEL: {c.level}\n"
            f"MAIN ATTRIBUTES: {', '.join(c.primary_attributes) or 'unspecified'}\n"
            f"THEY ALREADY KNOW: {known}\n"
            f'THEY ASKED TO LEARN: "{request}"\n\nTHE LESSONS (the engine has decided these - name and describe each):\n{slot_text}\n\n'
            "Name and describe every lesson.")


WANT_SYSTEM = """A player asked a guild instructor to teach them something. Say what they are after.
kind: "active" for something they do on purpose (a spell, technique, move), "passive" for a lasting quality (a knack, instinct, resistance,
being better at something), "either" if the request does not say.
effect: for an active, the one that fits best - damage, control, mobility, healing, buff (a guard or ward is a buff), utility, influence, summon or crafting;
empty if the request is open.
stat: for a passive, the one it improves - accuracy, evasion, defense, damage, movement, resolve, recovery, perception, stealth, insight,
persuasion, intimidation, deception, performance, lore, crafting - empty if none is named.
element: the element the request names, from fire, cold, lightning, poison, acid, necrotic, radiant, nature - empty if it names none.
Respond only with JSON matching the schema."""


def want_user(c, request: str) -> str:
    return f'CLASS: {c.custom_class}\nTHEY ASKED TO LEARN: "{request}"'


def _field_functions() -> str:
    from engine.field import F
    return "\n".join(f"{fn}: {spec['blurb']}" for fn, spec in F["functions"].items())


FIELD_SYSTEM = f"""You assign each ability its function outside combat. The functions are:
{_field_functions()}
For each ability given, choose the one function that fits it best. If it truly could not be used outside a fight, answer with an empty string.
Respond only with JSON matching the schema."""


def field_user(abilities) -> str:
    lines = [f"- {a.name} ({a.effect.value}, {a.reach.value}): {a.description}" for a in abilities]
    return "Abilities:\n" + "\n".join(lines)


for _name in ("ACTIVES_SYSTEM", "SLOTS_SYSTEM", "PASSIVES_SYSTEM", "MECH_PASSIVES_SYSTEM", "STAT_PASSIVES_SYSTEM"):
    globals()[_name] = globals()[_name] + "\n\n" + WORLD_FACTS
