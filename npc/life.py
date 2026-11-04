"""Bringing NPCs to life: populating places, promoting NPCs when met, and conversation turns.

Everything the model proposes is checked here before it touches saved state.
"""

import random
import re
import config

from llm.contracts import NPCProfile, NPCReply, ResidentSet
from llm.gateway import generate
from npc import land, names, prompts
from npc.models import NPC, Memory
from npc.traits import TraitCatalog, assign_traits, npc_rng
from storage.campaign import CampaignStore
from engine import money, clock, items, weather
from core.models import Item
from ui import console
from world.loader import World
from engine import streams



def _unique_id(store: CampaignStore, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "npc"
    candidate, n = base, 2
    while store.npc_exists(candidate):
        candidate, n = f"{base}_{n}", n + 1
    return candidate


FIRST_BATCH = 4          # how many residents the blocking call on arrival creates; the rest are made while the player reads


def _plan(store: CampaignStore, world: World, place_id: str):
    """Who this place still needs: (state, the residents it has, the slots to fill)."""
    state = store.load_place(place_id)
    existing = [store.load_npc(i) for i in state.residents]
    existing = [n for n in existing if not n.gone]
    place = world.places[place_id]
    have = {}
    for n in existing:
        have[n.role] = have.get(n.role, 0) + 1
    wanted = dict(place.residents)
    for role, n in state.extra_roles.items():
        wanted[role] = wanted.get(role, 0) + n
    from engine import events
    for role in events.vacant_roles(store, place_id, store.meta.minutes):
        wanted.pop(role, None)          # a post emptied by a disaster stays empty for a while before someone takes it up
    missing = {role: count - have.get(role, 0) for role, count in wanted.items() if count > have.get(role, 0)}
    peoples = world.peoples_at(place_id)
    rng = random.Random(f"{store.meta.seed}:place:{place_id}:{len(existing)}")
    slots = []
    taken = store.npc_names()
    anchors = _anchors_wanted(store, world, place_id)
    for role, count in missing.items():
        for _ in range(count if peoples else 0):
            people = rng.choices(list(peoples), weights=list(peoples.values()))[0]
            anchor = anchors.pop(role, None)
            name, gender = names.pick(people, taken, rng)
            if anchor and anchor.name and anchor.name not in taken:
                name = anchor.name
            taken.append(name)
            desc = world.roles[role].description + (f" In this town: {anchor.note}" if anchor and anchor.note else "")
            slots.append((role, desc, people, name, gender))
            if anchor:
                _ANCHOR_SLOTS[(place_id, name)] = anchor.note or anchor.role
    return state, existing, missing, slots


_ANCHOR_SLOTS: dict[tuple[str, str], str] = {}      # (place, name) -> the anchor's note, between planning and making


def _anchors_wanted(store: CampaignStore, world: World, place_id: str) -> dict:
    """(f317) The town's anchors (data/world/towns/<id>.yaml) whose role this place fills and who are not yet made: role -> Anchor."""
    t = world.town(place_id)
    if not t or not t.anchors:
        return {}
    from engine import retrieval
    made = {store.load_npc(r.id).anchor for r in retrieval.people_in_town(store, world, t.id)}      # the living only: a lost anchor is made again
    roles_here = set(world.places[place_id].residents)
    out = {}
    for a in t.anchors:
        if a.role in roles_here and (a.note or a.role) not in made and a.role not in out:
            out[a.role] = a
    return out


def _first_slots(store: CampaignStore, world: World, slots: list, count: int) -> list:
    """The few worth making before the scene is described: people on shift now, those who serve the player (a clerk, an innkeeper, a smith) first."""
    def rank(slot):
        role = world.roles[slot[0]]
        serves = bool(role.sells or role.stock or role.buys or role.commissions or role.relics or slot[0].startswith("guild_"))
        anchor = any(n == slot[3] for _, n in _ANCHOR_SLOTS)                     # (f317) the town's anchors are made first
        return (not anchor, not clock.in_hours(store.meta.minutes, role.hours), not serves)
    return sorted(slots, key=rank)[:count] if len(slots) > count else slots


def town_lines(store: CampaignStore, world: World, place_id: str) -> list[str]:
    """What the people of this town are told about it (engine/towns.py, f316). Read on the main thread; the model call may run elsewhere."""
    from engine import towns
    return towns.resident_lines(world, place_id, towns.condition(store, world, place_id, store.meta.minutes))


def _ask(place, world: World, slots: list, town: list[str] = ()) -> ResidentSet:
    """The model call for a set of residents. Touches no game state, so it can run on a background thread."""
    return generate(
        "populate_place", prompts.RESIDENTS_SYSTEM,
        prompts.residents_request(place, world.summary, slots, town), ResidentSet, max_tokens=3000,
        validation_context={"slots": len(slots)},
    )


def _apply(store: CampaignStore, world: World, catalog: TraitCatalog | None, place_id: str, slots: list, result: ResidentSet) -> list[NPC]:
    """Turn the model's answer into saved people and add them to the place."""
    from engine import doings
    state = store.load_place(place_id)
    existing = [n for n in (store.load_npc(i) for i in state.residents) if not n.gone]
    npcs = []
    taken = {n.activity for n in existing}
    for r in sorted(result.residents, key=lambda r: r.slot):
        role, _, people, name, gender = slots[r.slot - 1]
        if name in store.npc_names():
            continue
        npc = NPC(
            id=_unique_id(store, name), name=name, gender=gender, people=people, role=role,
            location=place_id, epithet=r.epithet.strip(), description=r.description.strip(),
        )
        npc.activity = doings.doing_for(npc, store.meta.seed, store.meta.minutes, taken)      # (f348) the engine's, from birth; it turns with the day
        taken.add(npc.activity)
        anchor = _ANCHOR_SLOTS.pop((place_id, name), "")
        if anchor:                                           # (f317) one of the town's anchors: named for what they are, never removed by the world
            npc.anchor, npc.protected = anchor, True
        if catalog:
            assign_traits(npc, catalog, npc_rng(store.meta.seed, npc.id))
        inner_life(npc, store, world)                        # (f334) the engine's share of a person, from birth
        store.save_npc(npc)
        npcs.append(npc)
    console.debug(f"populated {place_id}: {', '.join(f'{n.name} ({n.role})' for n in npcs)}")
    if not state.populated:
        state.first_visit_day = clock.day(store.meta.minutes)
    state.populated = True
    state.residents = [n.id for n in existing] + [n.id for n in npcs]
    store.save_place(state)
    return existing + npcs


def populate_place(store: CampaignStore, world: World, place_id: str, catalog: TraitCatalog | None = None,
                   first_batch: int | None = None) -> list[NPC]:
    """Generate a place's residents the first time it is entered - and later, anyone the world files add to it.
    With first_batch, only that many are made now (see _first_slots); start_backfill makes the rest."""
    from npc import backfill
    backfill.settle(store, world, catalog, place_id)
    state, existing, missing, slots = _plan(store, world, place_id)
    if state.populated and not missing:
        return existing
    if slots:
        console.busy_text("People go about their day.")          # (f423) the waiting indicator's words, not a line of the story
        if first_batch:
            slots = _first_slots(store, world, slots, first_batch)
        return _apply(store, world, catalog, place_id, slots, _ask(world.places[place_id], world, slots, town_lines(store, world, place_id)))
    if not state.populated:
        state.first_visit_day = clock.day(store.meta.minutes)
    state.populated = True
    state.residents = [n.id for n in existing]
    store.save_place(state)
    return existing


def unfinished(store: CampaignStore, world: World, place_id: str) -> bool:
    """Whether people are still missing from a place that has been entered."""
    state, _, _, slots = _plan(store, world, place_id)
    return state.populated and bool(slots)


def motive_roll(npc: NPC, store: CampaignStore) -> bool:
    """Whether this person has an active goal. Most don't - decided once, by their traits."""
    from engine.pulse import P
    m = P["motives"]
    chance = m["base_chance"] + sum(m["trait_shift"].get(t, 0) for t in npc.traits)
    return npc_rng(store.meta.seed, npc.id + ":motive").random() < max(0.0, min(0.9, chance))


def inner_life(npc: NPC, store: CampaignStore, world: World) -> None:
    """(f334) The engine's share of a person, given at birth so a town has texture before anyone in it is spoken to: the circles they
    hear news from, and - for the share their traits allow (motive_roll) - a goal in the engine's words (data/rules/pulse.yaml
    drift.motives.seeds). The rest start the clock by which the drift (engine/drift.py) may hand them one later. The model's share -
    personality, voice, concern, the goal in their own words - still waits for the first real conversation (promote). Once only."""
    from engine import drift
    if not npc.knowledge_groups:
        groups = ["everyone", world.locals_group(npc.location), *world.roles[npc.role].knowledge_groups]
        npc.knowledge_groups = list(dict.fromkeys(g for g in groups if g))
    if npc.motive or npc.motive_done_at >= 0 or npc.motive_since:
        return
    now = store.meta.minutes
    if motive_roll(npc, store):
        npc.motive = drift.motive_for(npc, world, drift.rules().get("motives") or {}, npc_rng(store.meta.seed, npc.id + ":goal"))
        npc.motive_since = now
    else:
        npc.motive_done_at = now


def promote(npc: NPC, store: CampaignStore, world: World, catalog: TraitCatalog) -> None:
    """First real interaction: roll traits, set knowledge, and generate personality. Once only. (f334) The engine's goal, when they
    have one, is kept in meaning: the profile restates it in their own words."""
    if npc.tier != "background":
        return
    if not npc.traits:
        assign_traits(npc, catalog, npc_rng(store.meta.seed, npc.id))
    inner_life(npc, store, world)                            # an older save's person, or one made without a catalogue
    has_motive = bool(npc.motive) or motive_roll(npc, store)
    from engine import voices
    ensure_speech(npc, store, world)                         # (f350) how they talk is the engine's: the profile is written to agree with it
    profile = generate(
        "npc_profile", prompts.PROFILE_SYSTEM,
        prompts.profile_request(npc, world.places[npc.location].name, catalog.describe(npc.traits), has_motive,
                                town_lines(store, world, npc.location) + ([f"WHO THEY ARE IN THIS TOWN: {npc.anchor}"] if npc.anchor else []),
                                motive_so_far=npc.motive, how=voices.lines(voices.kit_of(npc.speech))),
        NPCProfile, temperature=0.8,
    )
    npc.personality, npc.voice = profile.personality, profile.voice
    if not npc.concern_from:                                 # (f317) a concern a matter gave them stays
        from engine import circumstance                      # (f483) their own, from who they are
        circumstance.set_concern(npc, profile.concern, "profile")
    if not npc.first_description and npc.description:        # (f483) how they first looked, kept through any revision
        npc.first_description = npc.description
    npc.motive = (profile.motive.strip() or npc.motive) if has_motive else ""
    if npc.motive and not npc.motive_since:
        npc.motive_since = store.meta.minutes
    npc.tier = "known"
    store.save_npc(npc)
    console.debug(f"promoted {npc.name}: traits {npc.traits}; knows {npc.knowledge_groups}")
    console.debug(f"  personality: {npc.personality} | concern: {npc.concern}")


def ensure_speech(npc: NPC, store: CampaignStore, world: World) -> dict:
    """(f350) Their speech profile and voice kit, once: the kit drawn to differ from everyone else's in their town (engine/voices.py). The
    town's kits are only read when theirs is still to be drawn."""
    from engine import voice_profile, voices
    taken = () if voices.kit_of(npc.speech) else voices.kits_in_town(store, world, npc)
    return voice_profile.ensure_npc(npc, npc_rng(store.meta.seed, npc.id), world.places[npc.location].region, taken)


def social_circle(npc: NPC, store: CampaignStore, world: World) -> tuple[list[str], list[str]]:
    """Who this NPC works alongside, and who else in their community they know by name."""
    from engine import retrieval
    community = world.locals_group(npc.location)
    here, known = [], []
    rows = {r.id: r for r in retrieval.people_at(store, npc.location, gone=None, exclude=(npc.id,))}      # those here, and the community
    for r in retrieval.community(store, world, community, exclude=(npc.id,)):
        rows.setdefault(r.id, r)
    from engine import routines
    seed, now = store.meta.seed, store.meta.minutes
    for other in rows.values():
        line = f"{other.name}, the {other.role.replace('_', ' ')}"
        if other.gone:
            if community and world.locals_group(other.location) == community:
                known.append(f"{line} - no longer here: {other.gone}")
            continue
        usual = routines.usual_line(world, seed, other)                                 # (f352) 'at the Tilted Plough most evenings'
        if other.location == npc.location:
            on_shift = clock.in_hours(now, world.roles[other.role].hours) and not routines.away(world, seed, other, now)
            if on_shift:
                here.append(line)
            elif routines.away(world, seed, other, now):
                known.append(f"{line} (works here; {usual}, and that is where they are at this hour)")
            else:
                known.append(f"{line} (works here, but has gone home for now" + (f"; {usual}" if usual else "") + ")")
        elif community and world.locals_group(other.location) == community:
            known.append(f"{line} (usually at {world.places[other.location].name}" + (f"; {usual}" if usual else "") + ")")
    return here, known


def note_mentions(speaker: NPC, speech: str, store: CampaignStore, who: str) -> list[str]:
    """People the speaker named aloud who the character `who` has not met (or does not know by name) are noted as heard of by that
    character (f480: on their view), with what was said. Matches a full name, or a first name of 5+ letters that only one person has.
    Returns the names newly noted."""
    from engine import regard
    import re
    text = " ".join(speech.split())
    if not text:
        return []
    from engine import retrieval
    added = []
    for row in retrieval.named_in(store, text, exclude=(speaker.id,)):            # the index's names against the words; nothing parsed
        if row.heard_of or (row.met_player and row.name_known_to_player):     # by the index (any character): a cheap first pass
            if not store.npc_exists(row.id):
                continue
            seen = regard.of(store.load_npc(row.id), who)
            if seen.heard_of or (seen.met and seen.name_known):
                continue
        first = row.name.split()[0]
        m = re.search(r"\b(?:" + "|".join([re.escape(row.name), re.escape(first)]) + r")\b", text, re.I)
        if not m:
            continue
        o = store.load_npc(row.id)                        # only the one named is read in full
        sentences = re.split(r"(?<=[.!?])\s+", text)
        line = next((s for s in sentences if m.group(0).lower() in s.lower()), text)
        regard.own(o, who).heard_of = {"by": speaker.label(who), "day": clock.day(store.meta.minutes), "line": line[:200].strip(),
                                       "source": speaker.id, "certainty": "hearsay"}          # (f482) a name heard is hearsay, with its teller
        store.save_npc(o)
        added.append(o.name)
    return added


def _offered(store, npc, who: str) -> dict | None:
    """(f481) The work this person has offered the character and that still stands (engine/obligations.py), for WORK YOU HAVE OFFERED."""
    from scenes.work_actions import offer_open
    return offer_open(store, npc, who)


def _request(npc, store, world, catalog, convo, player_text, extra, truth_text, stance, rng, worn, wares, who, pronoun, promised=False):
    """(f487) A townsperson's request for one reply, whichever contract it goes under: the lore for the line, how they talk, what they
    sell, the request itself; promised (f493): what was said may promise them something, so the reply asks what. Returns (prompt,
    facts, recent)."""
    from engine import banter, matters, voice_profile
    from engine import circumstance                         # (f483) by the circles they were raised among and the place they live now
    every = world.facts_known_by(circumstance.groups(world, npc)) + matters.clue_facts(store, world, npc)      # (f317) what they know of the town's matters
    from engine import brief                                # (f486) the lore that bears on this line, every clue held, and the rest named
    facts, index = brief.lore(every, player_text, [w for _, w in convo])
    extra = list(extra) + ([index] if index else [])
    _, people_known = social_circle(npc, store, world)
    here_with = []                                          # (f313) who is here comes with the truth text, as this person knows them
    rng = rng or streams.get("scene")
    from engine import voices
    ensure_speech(npc, store, world)                                                                      # (f347, f350) where they were raised, how they talk
    voice_fact, voice_lines, material = voice_profile.resident_lines(npc, rng, char_id=who)
    recent = [s for h, s in zip(npc.heard[-6:], npc.said[-6:]) if not banter.asked_again(player_text, [h])]   # the same question may get much the same answer
    prompt = prompts.conversation_prompt(
            npc, world.places[npc.location], catalog.describe(npc.traits), facts, convo, player_text,
            [world.places[p].name for p in world.neighbors(npc.location)], here_with, people_known,
            clock.now_line(store.meta.minutes, weather.describe(store.meta.seed, store.meta.minutes)[1].lower()),   # (f477) no day number
            wares if wares is not None else
            [f"{w.name}: {money.words(w.price)}" for w in world.roles[npc.role].sells]
            + [f"{i['name']} ({i['rarity']} work, level {i['item_level']}): "
               f"{money.words(items.price(Item.model_validate(i)))}" for i in npc.stock]
            + ([f"commissions: you make {', '.join(world.roles[npc.role].commissions)} gear to order"]
               if world.roles[npc.role].commissions else []),
            extra, land.land_lines(world, npc.location) if brief.asked("land", player_text, npc.role) else [], truth_text=truth_text,   # (f486) when asked
            stance=stance, voice_fact=voice_fact, voice_lines=voice_lines, material=material,
            unsaid=banter.unsaid_rule(list(npc.said), player_text), worn=list(worn), now=store.meta.minutes, who=who,
            work=_offered(store, npc, who), pronoun=pronoun, promised=promised,
        )
    return prompt, facts, recent


def converse(
    npc: NPC,
    store: CampaignStore,
    world: World,
    catalog: TraitCatalog,
    convo: list[tuple[str, str]],
    player_text: str,
    extra: list[str] = (),
    truth_text: str = "",
    known=frozenset(),
    stance: str = "",
    rng: random.Random | None = None,
    worn: list[str] = (),
    house: set[str] | list[str] = (),
    wares: list[str] | None = None,
    *,
    who: str,
    pronoun: str = "",
    given_also: list[str] = (),
) -> tuple[NPCReply, list[str]]:
    """One conversation turn. Returns the reply and the ids of facts the player learned. truth_text is this person's view of the moment
    from the truth layer (engine/truth.py, f313): who is here, what the town has, the board, happenings, news; known is the words of the
    names the scene allows (f315) - the gateway sends back a reply that names anyone or anywhere else. stance (f347) is how they are for
    this conversation (scenes/world.py rolls it when the talk begins); rng draws this reply's lines on how they talk. wares (f418): what they
    sell at what the game will charge (scenes/inventory_actions.py wares_said); without it, the list's own prices."""
    from engine import brief
    promised = brief.promised(player_text)                  # (f493) the promise field only when the line may make one
    prompt, facts, recent = _request(npc, store, world, catalog, convo, player_text, extra, truth_text, stance, rng, worn, wares, who, pronoun,
                                     promised)
    from engine import voices
    from llm.contracts import NPCReplyPromised
    reply = generate(
        "npc_conversation", prompts.CONVERSATION_SYSTEM, prompt,
        NPCReplyPromised if promised else NPCReply, temperature=0.8, max_tokens=config.PROSE_MAX_TOKENS,
        validation_context={"known": known, "recent": recent, "last": npc.said[-1] if npc.said else "",      # (f349) last: no opener twice running
                            "given_also": list(given_also),        # (f486) the town's list, for the checks, given or not
                            "kit": voices.kit_of(npc.speech), "house": set(house), "worn": list(worn)},      # (f350) their kit; how everyone here talks; the worn words
        relaxed_context={"known": known},                   # the fallback ladder: once more without the repeat guard before giving up
    )
    from engine import partings
    partings.remember(npc, player_text, reply.speech)       # (f347) kept for the repeat guard and the written parting

    known_ids = {f.id for f in facts}
    import re as _re
    spoken = set(_re.findall(r"[a-z]{5,}", reply.speech.lower()))
    by_id = {f.id: f for f in facts}

    def conveyed(fid: str) -> bool:
        """The speech must actually carry the fact: it shares enough of the fact's own words (a fact merely claimed is not learned)."""
        words = set(_re.findall(r"[a-z]{5,}", by_id[fid].text.lower()))
        return len(words & spoken) >= min(3, max(1, len(words) // 4))

    revealed = [r for r in reply.reveals if r in known_ids and conveyed(r)]
    dropped = [r for r in reply.reveals if r not in revealed]
    if dropped:
        console.debug(f"ignored reveals {npc.name} does not know: {dropped}")

    step, seen = apply_answer(npc, store, reply.answers(who)[0], who, player_text, reply.intent, reply.told_own_name, reply.speech)
    store.save_npc(npc)

    console.debug(
        f"{npc.name}: intent={reply.intent} trust {seen.trust} ({step:+d}) reveals={revealed} "
        f"remember={reply.remember!r}"
    )
    return reply, revealed


def apply_answer(npc: NPC, store: CampaignStore, ans, who: str, words: str, intent: str, told_own_name: bool, speech: str):
    """(f487) What one reply means for one character `who`, the one commit path of NPCReply (its one block) and NPCReplyMany (a block
    each): their trust, their meeting, the name they gave in their own words, when they last spoke, the names the speech mentioned to
    them, what they promised, what to remember of them. Returns (the trust step, their view)."""
    import types as _types
    from engine import regard, trust as _trust
    step = _trust.after_talk(npc, _types.SimpleNamespace(intent=intent, trust_change=ans.trust_change), clock.day(store.meta.minutes), who,
                             store.meta.minutes)                                      # (f362) the engine moves trust from what happened
    seen = regard.of(npc, who)                                # (f480) this character's view: trust, name, the meeting, the hour
    if step:
        from engine import canon
        canon.journal("trust", who, npc.id, f"{npc.name}'s trust moved {step:+d} to {seen.trust}", step=step, trust=seen.trust)

    seen = regard.meet(npc, who, store.meta.minutes)
    if told_own_name:
        seen.name_known = True
    claimed = (ans.learned_name or "").strip()
    if claimed and claimed.lower() in (words or "").lower():
        seen.knows_as, seen.knows_as_source = claimed, "self"
        from engine import memory                            # (f482) what they were told, by whom: a claim, never a fact
        memory.keep(npc, f"{{them}} told me their name is {claimed}.", day=clock.day(store.meta.minutes), turn=store.meta.turn, kind="told",
                    subject=who, source=who, about=f"name:{who}", minute=store.meta.minutes)
    elif claimed:
        console.debug(f"ignored name '{claimed}': the player never said it")

    seen.last_talk_at = store.meta.minutes                   # (f382) when they last spoke: the next talk, long after, is a return
    for name in note_mentions(npc, speech, store, who):
        console.debug(f"{npc.name} named {name}: noted as heard of")
    if (ans.they_promised or "").strip():                   # (f486, G4) a promise made to them in words: theirs to remember, a claim
        from engine import memory
        memory.keep(npc, f"{{them}} promised me: {ans.they_promised.strip()}", day=clock.day(store.meta.minutes), turn=store.meta.turn,
                    kind="promise_heard", subject=who, source=who, minute=store.meta.minutes, importance=2)
    if (ans.remember or "").strip():                        # (f482) what this talk gave them to keep: what they were told, by whom
        from engine import memory
        memory.keep(npc, ans.remember.strip(), day=clock.day(store.meta.minutes), turn=store.meta.turn, kind="told", subject=who,
                    source=who, minute=store.meta.minutes)
    return step, seen


def converse_many(npc: NPC, store: CampaignStore, world: World, catalog: TraitCatalog, convo: list[tuple[str, str]], speakers: list,
                  extra: list[str] = (), truth_text: str = "", known=frozenset(), stance: str = "", rng: random.Random | None = None,
                  worn: list[str] = (), house=(), wares: list[str] | None = None, pronouns: dict | None = None, given_also: list[str] = ()):
    """(f487) Two or more characters to one townsperson in one line: `speakers` is [(character id, how they are known, their words)].
    What is said aloud comes once; each character has a block of what it means for them (NPCReplyMany), committed through the one path
    (apply_answer) against each one's own view. One speaker is converse() as ever. With brief.yaml many_addressees: flat_each, one
    NPCReply per speaker in order instead (the named fallback, chosen from the night's measure). Returns (reply, revealed) for one call,
    or a list of them for flat_each."""
    from engine import brief, regard
    if len(speakers) < 2:
        cid, _label, words = speakers[0]
        return converse(npc, store, world, catalog, convo, words, extra, truth_text, known, stance, rng, worn, house, wares, who=cid,
                        pronoun=(pronouns or {}).get(cid, ""), given_also=given_also)
    if brief.rules().get("many_addressees", "one_call") == "flat_each":
        return [converse(npc, store, world, catalog, convo, words, extra, truth_text, known, stance, rng, worn, house, wares, who=cid,
                         pronoun=(pronouns or {}).get(cid, ""), given_also=given_also) for cid, _label, words in speakers]
    ids = [cid for cid, _, _ in speakers]
    words = {cid: w for cid, _, w in speakers}
    said = " ".join(f'{label} ({cid}): "{w}"' for cid, label, w in speakers)
    block = ("THE ONES YOU ARE TALKING WITH (give each one block in answers, by their id): "
             + "; ".join(f"{cid}: {label}, {prompts.trust_words(regard.of(npc, cid).trust)}"
                         + (f", speak of them as {(pronouns or {}).get(cid)}" if (pronouns or {}).get(cid) else "") for cid, label, _ in speakers))
    promised = brief.promised(*words.values())               # (f493) the blocks' promise field only when a line may make one
    prompt, facts, recent = _request(npc, store, world, catalog, convo, said, list(extra) + [block], truth_text, stance, rng, worn, wares,
                                     ids[0], (pronouns or {}).get(ids[0], ""), promised)
    from engine import voices
    from llm import contracts
    reply = generate(
        "npc_conversation", prompts.CONVERSATION_SYSTEM, prompt, contracts.many_reply(ids, promised), temperature=0.8,
        max_tokens=config.PROSE_MAX_TOKENS,
        validation_context={"known": known, "recent": recent, "last": npc.said[-1] if npc.said else "", "given_also": list(given_also),
                            "kit": voices.kit_of(npc.speech), "house": set(house), "worn": list(worn), "to": ids, "words": words},
        relaxed_context={"known": known, "to": ids, "words": words},
    )
    from engine import partings
    partings.remember(npc, said, reply.speech)
    import re as _re
    by_id, spoken = {f.id: f for f in facts}, set(_re.findall(r"[a-z]{5,}", reply.speech.lower()))
    revealed = [r for r in reply.reveals if r in by_id and len(set(_re.findall(r"[a-z]{5,}", by_id[r].text.lower())) & spoken)
                >= min(3, max(1, len(set(_re.findall(r"[a-z]{5,}", by_id[r].text.lower()))) // 4))]     # carried by the speech, as converse asks
    for ans in sorted(reply.answers, key=lambda a: ids.index(a.to)):     # in the order they spoke
        apply_answer(npc, store, ans, ans.to, words[ans.to], reply.intent, reply.told_own_name, reply.speech)
    store.save_npc(npc)
    return reply, revealed


def manner(npc: NPC, catalog: TraitCatalog, store: CampaignStore) -> str:
    """How someone comes across from a distance, from their traits. Rolls traits for older saves that lack them."""
    if not npc.traits:
        assign_traits(npc, catalog, npc_rng(store.meta.seed, npc.id))
        if store.writable():
            store.save_npc(npc)
        else:
            store.save_npc_later(npc)                     # (f470) read during the understanding, outside any operation: the next operation saves it
    return ", ".join(t.replace("_", " ") for t in npc.traits)


PARTING = re.compile(
    r"\b(good ?bye|farewell|good (day|night|morning|evening|luck|journey)|fare ye well|fare thee well|safe (travels|journey|road)|"
    r"take care|be (off|gone)|off with you|go (away|on with you)|begone|leave me|let me be|leave it be|get (out|lost|away)|"
    r"(i|we)('ve| have)? (got|have|must|need to|gotta) (work|go|be)|i('m| am) (busy|leaving|going)|must be (going|off)|"
    r"(see|catch) you|until next|till next|that('s| is) (all|enough)|enough (of|talk)|no more|nothing more to (say|add)|"
    r"don't (bother|waste)|stop (bothering|pestering)|piss off|shove off|walk away|and now,? if you|if you('ll| will) excuse me|excuse me)\b",
    re.IGNORECASE)


def has_parting(speech: str) -> bool:
    """Whether what an NPC said actually ends the talk: a goodbye, an excuse, a flat dismissal. Nobody walks off in silence."""
    return bool(PARTING.search(speech))
