"""(f348) The one model call a moment makes: the engine has decided that something is going on here, its shape and its mechanics; the
model writes what it is - for this place, this hour, these people - told everything this playthrough has already seen."""
from __future__ import annotations

from llm.prompts import WORLD_RULES

MOMENT_SYSTEM = """You invent one small thing going on in a place of a fantasy world at the moment the player walks in.
The game has decided its shape (THE SHAPE), where and when it is, who is present and whether anyone has come with it. You make it
particular: this place, this hour, these people, never the stock version of the shape, and never anything like a moment under
ALREADY SEEN IN THIS GAME. Think of what would actually be going on here today, and say it plainly.

Rules:
- Present tense, plain words, no names you were not given. Anyone new is an unnamed figure ("two drovers", "a boy", "an old woman").
- Nothing that changes the world: no one dies, nothing burns, no arrest, no monster, no god, nothing taken from the player, nobody
  present is harmed. It is a scene, not an event; the game's own events are elsewhere.
- Use only this world's terms (no real-world gods, holy days, months, weekdays, songs or places).
- No figures.

Give:
  title: two to six words, the way the town will name it afterwards ("the night the fiddler came", "the pig under the well").
  line: what is going on, one or two sentences, for the narrator and for everyone in the place: what the player sees and hears as
    they come in. Concrete; one or two particulars that could only be here.
  doings: what the people here are doing meanwhile, as short phrases with no subject ("pulling ale as fast as the mugs come back"):
    one with who "everyone", and one for any person whose part is different, with who = their role word exactly as it stands before
    the colon under PEOPLE HERE (innkeeper, smith...), never how they are known and never a name.
  visitor_epithet, visitor_look, visitor_doing: only when A VISITOR is given: how the player would name them before learning their
    name (two to four words), one sentence of how they look, and what they are doing. Otherwise leave all three empty.
  mishap: only when MISHAP is asked for: one sentence of how the player is caught in it as they come in (a knock, a splash, a
    shove), never a wound that matters. Otherwise empty.
  memory: one line the town will keep of it afterwards, in the past tense ("the night the fiddler had the Plough dancing").
""" + WORLD_RULES + """
Respond only with JSON matching the schema."""


def moment_request(ws, shape: dict, visitor_role: str, seen: list[dict]) -> str:
    """The place as it is now, the people and their roles, the shape, and everything this playthrough has seen."""
    from engine import weather
    from npc import life
    place = ws.place
    visible = "\n".join(f"  - {v}" for v in place.visible) or "  (nothing in particular)"
    people = "\n".join(f"  - {n.role}: {n.label()}. {n.description} Doing now: {n.activity}" for n in ws.present) or "  (no one)"
    town = "\n".join(life.town_lines(ws.store, ws.world, ws.player.location))
    from engine import truth
    here = truth.scene_of(ws).view(truth.NARRATOR, "narrator")
    already = [h for h in here.lines("happenings")]
    past = "\n".join(f"  - {s.get('title', '?')}: {s.get('line', '')}" for s in seen) or "  (nothing yet: this is the first)"
    return (
        f"WORLD: {ws.world.summary.strip()}\n\n"
        f"PLACE: {place.name} ({place.type})\n{visible}\n"
        + (f"{town}\n" if town else "")
        + f"TIME: {ws.time_label()}, weather {weather.describe(ws.store.meta.seed, ws.minutes)[1].lower()}\n"
        f"PEOPLE HERE (each is 'role: how they are known'; doings.who is that role word exactly as it stands, or everyone; in the line, name them only as they are known):\n{people}\n"
        + (("ALREADY GOING ON HERE (do not contradict it):\n" + "\n".join(f"  - {a}" for a in already) + "\n") if already else "")
        + f"\nTHE SHAPE: {shape['brief']}\n"
        + (f"A VISITOR comes with it, a {visitor_role.replace('_', ' ')} from the road: give their epithet, look and doing.\n" if visitor_role else "No visitor: no one new of any account; leave the visitor fields empty.\n")
        + ("MISHAP: the player may be caught in it as they come in; say how.\n" if any(e.get("kind") == "hurt" for e in shape.get("effects") or []) else "")
        + f"\nALREADY SEEN IN THIS GAME (never these again, nor anything like them):\n{past}\n"
    )
