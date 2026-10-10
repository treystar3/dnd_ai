"""Reading what a player means to do near an enemy camp. The model only reads the words; the engine decides what happens."""

SYSTEM = """You read what a player wants to do when they are hiding near an enemy camp they have not fought yet.
Choose exactly one kind:
  scout    - watch or study the camp, count the guards, look for a way in or a weakness.
  sneak    - quietly get to ONE guard and deal with him: kill, knock out, strangle, garrote, stab, lure him off alone and take him down.
  ambush   - get to the LEADER unseen and strike first (assassinate, kill, stab, or open with a spell or arrow at the leader from hiding).
  bluff    - pass as someone who belongs, or talk the camp into letting them in. Only works on people.
  scare    - threaten or frighten the guards into running. Only works on people.
  charge   - attack openly: rush in, shoot or cast from where they stand, anything loud, or a plain fight.
  none     - it is not about the camp at all: leaving, resting, eating, checking things, asking a question, talking about something else.
For sneak, target is the guard's name or number from the list, or "" for any guard. If the player's target is the leader or boss, the kind is ambush.
method lists ONLY things the player actually said they are using, from this fixed list - never add one they did not say:
  cover        - tall grass, bushes, rocks, trees, walls, shadows or crouching or crawling to stay hidden
  darkness     - night, fog, rain, moonless dark
  distraction  - a thrown stone, a decoy, a noise or fire elsewhere, luring a guard away
  patience     - waiting for a patrol to pass, timing the guards' rounds, taking their time
  disguise     - a disguise, stolen uniform, false papers, a pretended identity
summary is a few words. Respond only with JSON matching the schema."""


def user(text: str, guards: list[str], leader: str, people: bool, place: str, scene: str) -> str:
    shown = ", ".join(guards[:12]) + (f" (and {len(guards) - 12} more)" if len(guards) > 12 else "") if guards else "none left"
    return (f"THE CAMP: {'people' if people else 'creatures'}. GUARDS STILL STANDING: {shown}. THE LEADER: {leader}.\n"
            f"WHERE: {place}. {scene}\nTHE PLAYER SAYS: {text}")
