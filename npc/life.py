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
        npc.concern = profile.concern
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


def note_mentions(speaker: NPC, speech: str, store: CampaignStore) -> list[str]:
    """People the speaker named aloud who the player has not met (or does not know by name) are noted as heard of, with what was said.
    Matches a full name, or a first name of 5+ letters that only one person has. Returns the names newly noted."""
    import re
    text = " ".join(speech.split())
    if not text:
        return []
    from engine import retrieval
    added = []
    for row in retrieval.named_in(store, text, exclude=(speaker.id,)):            # the index's names against the words; nothing parsed
        if row.heard_of or (row.met_player and row.name_known_to_player):
            continue
        first = row.name.split()[0]
        m = re.search(r"\b(?:" + "|".join([re.escape(row.name), re.escape(first)]) + r")\b", text, re.I)
        if not m:
            continue
        o = store.load_npc(row.id)                        # only the one named is read in full
        sentences = re.split(r"(?<=[.!?])\s+", text)
        line = next((s for s in sentences if m.group(0).lower() in s.lower()), text)
        o.heard_of = {"by": speaker.name if speaker.name_known_to_player else speaker.label(), "day": clock.day(store.meta.minutes),
                      "line": line[:200].strip()}
        store.save_npc(o)
        added.append(o.name)
    return added


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
) -> tuple[NPCReply, list[str]]:
    """One conversation turn. Returns the reply and the ids of facts the player learned. truth_text is this person's view of the moment
    from the truth layer (engine/truth.py, f313): who is here, what the town has, the board, happenings, news; known is the words of the
    names the scene allows (f315) - the gateway sends back a reply that names anyone or anywhere else. stance (f347) is how they are for
    this conversation (scenes/world.py rolls it when the talk begins); rng draws this reply's lines on how they talk. wares (f418): what they
    sell at what the game will charge (scenes/inventory_actions.py wares_said); without it, the list's own prices."""
    from engine import banter, matters, voice_profile
    facts = world.facts_known_by(set(npc.knowledge_groups)) + matters.clue_facts(store, world, npc)      # (f317) what they know of the town's matters
    _, people_known = social_circle(npc, store, world)
    here_with = []                                          # (f313) who is here comes with the truth text, as this person knows them
    rng = rng or random.Random()
    from engine import voices
    ensure_speech(npc, store, world)                                                                      # (f347, f350) where they were raised, how they talk
    voice_fact, voice_lines, material = voice_profile.resident_lines(npc, rng)
    recent = [s for h, s in zip(npc.heard[-6:], npc.said[-6:]) if not banter.asked_again(player_text, [h])]   # the same question may get much the same answer
    reply = generate(
        "npc_conversation", prompts.CONVERSATION_SYSTEM,
        prompts.conversation_prompt(
            npc, world.places[npc.location], catalog.describe(npc.traits), facts, convo, player_text,
            [world.places[p].name for p in world.neighbors(npc.location)], here_with, people_known,
            f"day {clock.day(store.meta.minutes)}, {clock.period(store.meta.minutes)}, "
            f"weather: {weather.describe(store.meta.seed, store.meta.minutes)[1].lower()}",
            wares if wares is not None else
            [f"{w.name}: {money.words(w.price)}" for w in world.roles[npc.role].sells]
            + [f"{i['name']} ({i['rarity']} work, level {i['item_level']}): "
               f"{money.words(items.price(Item.model_validate(i)))}" for i in npc.stock]
            + ([f"commissions: you make {', '.join(world.roles[npc.role].commissions)} gear to order"]
               if world.roles[npc.role].commissions else []),
            extra, land.land_lines(world, npc.location), truth_text=truth_text,
            stance=stance, voice_fact=voice_fact, voice_lines=voice_lines, material=material,
            unsaid=banter.unsaid_rule(list(npc.said), player_text), worn=list(worn),
        ),
        NPCReply, temperature=0.8, max_tokens=config.PROSE_MAX_TOKENS,
        validation_context={"known": known, "recent": recent, "last": npc.said[-1] if npc.said else "",      # (f349) last: no opener twice running
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

    from engine import trust as _trust
    step = _trust.after_talk(npc, reply, clock.day(store.meta.minutes))      # (f362) the engine moves trust from what happened; the model's say counts within its limit
    if step:
        from engine import canon
        canon.journal("trust", "player", npc.id, f"{npc.name}'s trust moved {step:+d} to {npc.trust}", step=step, trust=npc.trust)

    if reply.told_own_name:
        npc.name_known_to_player = True
    claimed = reply.learned_player_name.strip()
    if claimed and claimed.lower() in player_text.lower():
        npc.knows_player_as = claimed
    elif claimed:
        console.debug(f"ignored name '{claimed}': the player never said it")

    if not npc.met_player:
        npc.met_player = True
    npc.last_talk_at = store.meta.minutes                   # (f382) when they last spoke: the next talk, long after, is a return
    for name in note_mentions(npc, reply.speech, store):
        console.debug(f"{npc.name} named {name}: noted as heard of")
    if reply.remember.strip():
        npc.memories.append(Memory(day=clock.day(store.meta.minutes), turn=store.meta.turn, text=reply.remember.strip()))
    store.save_npc(npc)

    console.debug(
        f"{npc.name}: intent={reply.intent} trust {npc.trust} ({step:+d}) reveals={revealed} "
        f"remember={reply.remember!r}"
    )
    return reply, revealed


def manner(npc: NPC, catalog: TraitCatalog, store: CampaignStore) -> str:
    """How someone comes across from a distance, from their traits. Rolls traits for older saves that lack them."""
    if not npc.traits:
        assign_traits(npc, catalog, npc_rng(store.meta.seed, npc.id))
        store.save_npc(npc)
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
