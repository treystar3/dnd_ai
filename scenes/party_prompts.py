"""Reading what a player wants to do about their hired party. The model only reads the words."""

SYSTEM = """You read what a player wants to do about hiring or directing adventurers who travel with them. Choose one kind:
  list    - see who is available to hire, ask what adventurers the guild has.
  hire    - take one or more of the listed adventurers on. target is their name, number in the list, role (fighter, archer, priest, rogue, mage), or "all".
  dismiss - send one or more of their party away or disband it. target is a name, role, or "all".
  hold    - tell the party to wait outside, hang back, stay out of sight, or come in only if there is trouble.
  with    - tell the party to stay close, come along, move in together.
  status  - ask who is in the party.
  none    - it is not about the party (buying, talking to someone, taking a contract, anything else).
Respond only with JSON matching the schema."""


def user(text: str, offered: list[str], members: list[str]) -> str:
    return (f"AVAILABLE TO HIRE: {', '.join(offered) or 'nobody right now'}.\n"
            f"IN THE PLAYER'S PARTY: {', '.join(members) or 'nobody'}.\nTHE PLAYER SAYS: {text}")
