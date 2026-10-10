"""Bringing NPCs to life: populating places, promoting NPCs when met, and conversation turns.

Everything the model proposes is checked here before it touches saved state.
"""

import random
import re

from llm.contracts import NPCProfile, NPCReply, ResidentSet
from llm.gateway import generate
from npc import prompts
from npc.models import NPC, Memory
from npc.traits import TraitCatalog, assign_traits, npc_rng
from storage.campaign import CampaignStore
from engine import money, clock, items, voice_rules, weather
from core.models import Item
from ui import console
from world.loader import World

TRUST_STEP_LIMIT = 5


def _unique_id(store: CampaignStore, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "npc"
    candidate, n = base, 2
    while store.npc_exists(candidate):
        candidate, n = f"{base}_{n}", n + 1
    return candidate


def populate_place(store: CampaignStore, world: World, place_id: str, catalog: TraitCatalog | None = None) -> list[NPC]:
    """Generate a place's residents the first time it is entered - and later, anyone the world files add to it."""
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
    if state.populated and not missing:
        return existing

    peoples = world.peoples_at(place_id)
    rng = random.Random(f"{store.meta.seed}:place:{place_id}:{len(existing)}")
    slots = []
    for role, count in missing.items():
        for _ in range(count if peoples else 0):
            people = rng.choices(list(peoples), weights=list(peoples.values()))[0]
            slots.append((role, world.roles[role].description, people, world.peoples[people].naming_style))

    npcs = []
    if slots:
        console.wait("People go about their day.")
        result = generate(
            "populate_place", prompts.RESIDENTS_SYSTEM,
            prompts.residents_request(place, world.summary, slots), ResidentSet, max_tokens=3000,
            validation_context={"slots": len(slots), "taken_names": store.npc_names()},
        )
        for r in sorted(result.residents, key=lambda r: r.slot):
            role, _, people, _ = slots[r.slot - 1]
            npc = NPC(
                id=_unique_id(store, r.name), name=r.name.strip(), people=people, role=role,
                location=place_id, epithet=r.epithet.strip(), description=r.description.strip(),
                activity=r.activity.strip(),
            )
            if catalog:
                assign_traits(npc, catalog, npc_rng(store.meta.seed, npc.id))
            store.save_npc(npc)
            npcs.append(npc)
        console.debug(f"populated {place_id}: {', '.join(f'{n.name} ({n.role})' for n in npcs)}")

    if not state.populated:
        state.first_visit_day = clock.day(store.meta.minutes)
    state.populated = True
    state.residents = [n.id for n in existing + npcs]
    store.save_place(state)
    return existing + npcs


def motive_roll(npc: NPC, store: CampaignStore) -> bool:
    """Whether this person has an active goal. Most don't - decided once, by their traits."""
    from engine.pulse import P
    m = P["motives"]
    chance = m["base_chance"] + sum(m["trait_shift"].get(t, 0) for t in npc.traits)
    return npc_rng(store.meta.seed, npc.id + ":motive").random() < max(0.0, min(0.9, chance))


def promote(npc: NPC, store: CampaignStore, world: World, catalog: TraitCatalog) -> None:
    """First real interaction: roll traits, set knowledge, and generate personality. Once only."""
    if npc.tier != "background":
        return
    assign_traits(npc, catalog, npc_rng(store.meta.seed, npc.id))
    groups = ["everyone", world.locals_group(npc.location), *world.roles[npc.role].knowledge_groups]
    npc.knowledge_groups = list(dict.fromkeys(g for g in groups if g))
    has_motive = motive_roll(npc, store)
    profile = generate(
        "npc_profile", prompts.PROFILE_SYSTEM,
        prompts.profile_request(npc, world.places[npc.location].name, catalog.describe(npc.traits), has_motive),
        NPCProfile, temperature=0.8,
    )
    npc.personality, npc.voice, npc.concern = profile.personality, profile.voice, profile.concern
    npc.motive = profile.motive.strip() if has_motive else ""
    npc.tier = "known"
    store.save_npc(npc)
    console.debug(f"promoted {npc.name}: traits {npc.traits}; knows {npc.knowledge_groups}")
    console.debug(f"  personality: {npc.personality} | concern: {npc.concern}")


def social_circle(npc: NPC, store: CampaignStore, world: World) -> tuple[list[str], list[str]]:
    """Who this NPC works alongside, and who else in their community they know by name."""
    community = world.locals_group(npc.location)
    here, known = [], []
    for other_id in store.list_npcs():
        if other_id == npc.id:
            continue
        other = store.load_npc(other_id)
        line = f"{other.name}, the {other.role.replace('_', ' ')}"
        if other.gone:
            if community and world.locals_group(other.location) == community:
                known.append(f"{line} - no longer here: {other.gone}")
            continue
        if other.location == npc.location:
            on_shift = clock.in_hours(store.meta.minutes, world.roles[other.role].hours)
            if on_shift:
                here.append(line)
            else:
                known.append(f"{line} (works here, but has gone home for now)")
        elif community and world.locals_group(other.location) == community:
            known.append(f"{line} (usually at {world.places[other.location].name})")
    return here, known


def converse(
    npc: NPC,
    store: CampaignStore,
    world: World,
    catalog: TraitCatalog,
    convo: list[tuple[str, str]],
    player_text: str,
    extra: list[str] = (),
    level: str = "short",
) -> tuple[NPCReply, list[str]]:
    """One conversation turn. Returns the reply and the ids of facts the player learned."""
    facts = world.facts_known_by(set(npc.knowledge_groups))
    here_with, people_known = social_circle(npc, store, world)
    reply = generate(
        "npc_conversation", prompts.CONVERSATION_SYSTEM,
        prompts.conversation_request(
            npc, world.places[npc.location], catalog.describe(npc.traits), facts, convo, player_text,
            [world.places[p].name for p in world.neighbors(npc.location)], here_with, people_known,
            f"day {clock.day(store.meta.minutes)}, {clock.period(store.meta.minutes)}, "
            f"weather: {weather.describe(store.meta.seed, store.meta.minutes)[1].lower()}",
            [f"{w.name}: {money.words(w.price)}" for w in world.roles[npc.role].sells]
            + [f"{i['name']} ({i['rarity']} work, level {i['item_level']}): "
               f"{money.words(items.price(Item.model_validate(i)))}" for i in npc.stock]
            + ([f"commissions: you make {', '.join(world.roles[npc.role].commissions)} gear to order"]
               if world.roles[npc.role].commissions else []),
            extra, voice_rules.npc(level)["length"],
        ),
        NPCReply, temperature=0.8, max_tokens=voice_rules.npc(level)["tokens"],
    )

    known_ids = {f.id for f in facts}
    revealed = [r for r in reply.reveals if r in known_ids]
    dropped = [r for r in reply.reveals if r not in known_ids]
    if dropped:
        console.debug(f"ignored reveals {npc.name} does not know: {dropped}")

    step = max(-TRUST_STEP_LIMIT, min(TRUST_STEP_LIMIT, reply.trust_change))
    npc.trust = max(0, min(100, npc.trust + step))

    if reply.told_own_name:
        npc.name_known_to_player = True
    claimed = reply.learned_player_name.strip()
    if claimed and claimed.lower() in player_text.lower():
        npc.knows_player_as = claimed
    elif claimed:
        console.debug(f"ignored name '{claimed}': the player never said it")

    if not npc.met_player:
        npc.met_player = True
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
