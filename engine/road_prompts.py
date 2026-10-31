"""Prompts for road events: inventing what the player comes across between places. (f423) The prompt says "the player", never "a
traveler", so the one the scene is about is never taken for someone else on the road. (f427) What stops the walk is decided by the
engine by kind (data/rules/road.yaml stops), not by tier: the scene of a stop ends before the player acts."""

SYSTEM = """You are the unseen hand of a living fantasy world, deciding what the player comes across on the road.
Invent ONE happening on THIS stretch of road, at the given TIER, that could only happen here and now: it should
fit the road's character, the SEASON, the weather and time of day, the LORE, and what the world is already doing
(THE WORLD NOW). A good road event is specific and grounded - a thing seen, an obstacle, a stranger, a windfall,
a sign of something larger - not a generic "you meet a merchant". It need not be a threat.

TIER decides scale: normal - a small moment; uncommon - something worth remembering; rare - something big, that could
change a region for a while.

KIND: find (something left or lost by the road; detail says what), meeting (travelers or locals; detail says who and
what they say or want), hazard (an obstacle - weather, terrain, a washed-out ford, a fallen tree; detail says what, and
check says which skill gets the player past it), sight (something strange or beautiful or ominous to see; nothing to
do about it), aid (someone who needs help; detail says who and what with), ambush (a fight - see below).
When the event says it must be an ambush, the CREATURES are given: describe how they come at the player, naming
them, and nothing else about the outcome. Otherwise never include a fight.

Write:
  title: a short name for it.
  journey: the walk BEFORE the happening, second person, from THE JOURNEY: the player setting out (or already
    well on the way), the road under their feet and the country it crosses, the weather and the light, anyone walking with them (as
    WHO IS WITH THEM says, nothing more), and roughly how long they have been walking. The player should feel the road go by, so the
    happening comes in the middle of a journey, not out of nowhere. Never the happening itself, and never the arrival.
  scene: what the player sees and hears, in the second person ("You..."): concrete, no decisions or actions for the player; a rare
  TIER is a bigger moment, and the scene gives it room.  kind, detail, check (hazards only).
  meets_role: ONLY if the event says the player is stopped here - a role id from ROLES for someone who is there
    (a stranded merchant, a pilgrim, a patrol); always for someone in need or someone met. Otherwise leave empty.
When the player is stopped here, the scene ends on what is there and nothing more: what they do about it is theirs.
  news: one sentence of word the player picks up that is now known in the world, or empty.
  effects: usually none. You may use fact (text, groups), mark (place, text), danger (place = a ROAD id from
    ROADS, value -50..100, days): the road becomes more or less dangerous for a while - "bandits now hold the ford",
    or lead (text): word of somewhere off the road that is on no map - "a spring the drovers use, up the dry gully".
Never decide what the player does, says or feels, and never say how a fight ends.
Respond only with JSON matching the schema."""


def user(road_text: str, tier: str, season: str, when: str, sky: str, world_now: str, lore: str, must: str,
         checks: list[str], roles: list[str], roads: str, stops: bool, journey: str = "", company: list[str] = ()) -> str:
    return (f"ROAD: {road_text}\nTIER: {tier}\nSEASON: {season}\nTIME: {when}; weather: {sky}\n"
            + (f"THE JOURNEY: {journey}\n" if journey else "")
            + f"WHO IS WITH THEM (each one's pronoun and people: never write them otherwise): {'; '.join(company) if company else 'no one: they walk alone'}\n"
            f"THE WORLD NOW: {world_now or 'nothing in particular'}\nLORE: {lore or 'nothing special'}\n"
            f"MUST BE: {must}\n"
            f"{'THE PLAYER IS STOPPED HERE: give meets_role if someone is present.' if stops else 'The player keeps walking after this.'}\n"
            f"CHECKS: {', '.join(checks)}\nROLES: {', '.join(roles)}\nROADS: {roads}")
