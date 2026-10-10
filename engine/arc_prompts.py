"""The one model call an arc makes: dress a fixed skeleton in names, clues and colour."""

SYSTEM = """You write the story for a quest in a fantasy role-playing game. The game has already decided its SHAPE: a fixed list of
steps, each at a real place, in a fixed order. You may not add, remove, reorder or rename the steps. You only supply:
  hook_title: what the contract board said, in a few words. It must not hint at anything bigger than the hook.
  title: what the whole story is called once the player learns how big it is ("The Ring Along the Roads"). Short.
  victim_name, victim_looks: THE SUBJECT of the story - a missing person, an object, or the matter itself (a short noun phrase;
    for a matter or object, victim_looks is one line saying what it is like).
  premise: two sentences - what was really going on, as the player will understand at the end. Consistent with THE TRUTH.
  nodes: one entry per step, with the same id, in the same order:
    title: a short name for this step.
    clue: what the player learns at this step - one or two sentences. It must lead to the NEXT step's place and to nothing
      further ahead, so the trail is followed one link at a time. At the LAST step the clue is how the matter ends and what
      the whole affair was. Never mention a step number.
    npc_name: a contact: the person who knows it. A hideout or the last step: the leader or the one behind it. A search
      site has no person: leave npc_name empty. A name fitting the place's people.
    npc_looks: one sentence of appearance. npc_manner: one sentence of how they carry themselves and speak. (Empty for a site.)
Rules: use only the places and people given. Invent no new places, factions, creatures or magic beyond THE TRUTH. Every name
must be different and none may be on the taken list. Respond only with JSON matching the schema."""


def user(truth: str, scale: str, victim: str, nodes: list[dict], taken: list[str], tpl: dict | None = None) -> str:
    tpl = tpl or {}
    lines = []
    for n in nodes:
        k = n["kind"]
        if k == "contact":
            who = f"a {n['role'].replace('_', ' ')} ({n['people']}) who knows something"
        elif k == "site":
            who = f"a search of {tpl.get('site_desc', 'a place that may hold a clue')}; no person"
        elif k == "lair":
            who = f"{tpl.get('lair_desc', 'a hideout')}, with its leader ({n['people']})"
        else:
            who = f"THE FINALE: {tpl.get('boss_desc', 'the stronghold of the one behind it')}; the one behind it ({n['people']})"
        nxt = f"leads to {n['next']}" if n.get("next") else "the LAST step: the matter ends here"
        lines.append(f"  {n['id']}: {k} at {n['place_name']} - {who}; {nxt}")
    return (f"THE TRUTH (hidden from the player until they uncover it): {truth.strip()}\n"
            f"SIZE: {scale}\nTHE SUBJECT: {victim} (kind: {tpl.get('subject_kind', 'person')})\nSTEPS, in order:\n" + "\n".join(lines) +
            f"\nTAKEN NAMES: {', '.join(taken) or 'none'}")
