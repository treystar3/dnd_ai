"""(f542) A situation's parts (Stage 4, the owner's decisions of 2026-11-07 in GOALS.md): the engine's check of what the model proposed
(llm/contracts.py SituationParts), part by part, and the fixed render of what passed.

check() is pure: it reads the store and the world and writes nothing. It takes the parts in the order proposed, people first, and drops
a part that fails with its reason while the rest stand: a person neither of the town nor a role the world has, one gone, the player, a
trade no situation casts, the same person twice, or past the caps by tier (data/rules/situations.yaml). A role is the town's own of that
trade first: a person of it already made, else one the town's places are written with (bind "town", made when the place is first
entered, as a clue settles on its role); only a trade the town has none of is someone new for the engine to make (bind "new"), within
the tier's cap. A good the world does not have; a holder, a tie's end or what evidence points to that is not of the situation; a place or
road the world does not have, or prices on a road (the pulse lays prices on a town); a closure of the only way between two places, the
roads already shut and those this proposal shuts counted, when the situation offers no way through it; words that name the game's
machinery: each dropped alone. Evidence held by a person may be false (rolled once on the die passed in, against its certainty's
chance; a sure piece never false; the proposing model is never told); evidence lying at a place is only ever sure, since a false piece
is only ever a claim its holder makes.

(f545 part 5) What the model writes whatever the prompt says is read as it meant, before any of that: a trade it numbered or tagged
("merchant_1", "trade: guard") is the trade, a name of its own is the trade its label names (the name never kept), and a label of words
joined by underscores is those words (trade_of, plain). An id of the world in a label stays machinery.

Each accepted part is a dict with its kind and v (the shape's version), and for f545 what it binds to: a person's bind ("npc": who is an
id; "town": who is a trade the town has, its person found or made when bound; "new": who is a trade for the engine to make), evidence's
held ("person" or "place"). An evidence part carries its truth: it is never handed to the model that proposed the parts.

render() makes the SITUATION PARTS lines from the names, trades and goods of the world, never an id, one line per part from the phrase
tables, each drawn on streams.fixed(key, "parts", i), so a situation's lines are the same every time they are told.

(f543) prompt() is what the model is shown to propose them (the lists it may name, each in a fixed order, ids beside names; the system text is
pulse_prompts.PARTS_SYSTEM, which gives every word of the closed lists), and propose() the one call that asks, then checks: asked in
play from f547, measured with thinking off and on first (tools/situation_ab.py, f544)."""
from __future__ import annotations

import collections
import random
import re
from pathlib import Path

import yaml
from core import yamlio

from engine import hygiene, retrieval, roads, streams

ROOT = Path(__file__).resolve().parent.parent
S = yamlio.safe_load((ROOT / "data" / "rules" / "situations.yaml").read_text(encoding="utf-8"))
TIERS = ("normal", "uncommon", "rare", "campaign")
V = 1


def _raw(text: str, ids: set[str]) -> bool:
    """Words that name the game's machinery: a snake_case or coded id, a placeholder, or an id of the world or the store."""
    if not text:
        return False
    if "_" in text or hygiene.SNAKE.search(text) or hygiene.CODED.search(text) or hygiene.PLACEHOLDER.search(text):
        return True
    return any(w in ids for w in text.lower().replace(",", " ").replace(".", " ").split())


def plain(label: str, world, store=None) -> str:
    """(f545 part 5) A label written as words joined by underscores ("flooded_field_owner", as the model writes one in a fifth of its
    answers whatever the prompt says) is those words: "flooded field owner". An id of the world or the store stays as written, so the
    check still refuses it as machinery."""
    s = (label or "").strip()
    if not re.fullmatch(r"[A-Za-z]+(?:_[A-Za-z]+)+", s) or s.isupper():
        return s                                                     # (f545's review) "UNKNOWN_PERSON" is machinery, not words
    tokens = s.lower().split("_")
    if set(tokens) & set(S.get("machinery_words") or ()):
        return s                                                     # ...and so is "npc_marker"
    for i in range(len(tokens)):                                     # an id inside it that is no name ("celesen_wickmore_debt", a
        for j in range(i + 1, len(tokens) + 1):                      # road stop's code), never a place named as its id ("the greywood",
            run = "_".join(tokens[i:j])                              # "watch tower": f545's review)
            spot = world.places.get(run) or world.roads.get(run)
            if (spot is not None and _snake(spot.name) != run) or (j - i > 1 and store is not None and store.npc_exists(run)):
                return s
    return s.replace("_", " ")


def _snake(name: str) -> str:
    """A name as an id is written from it: "The Watch Tower" -> "watch_tower"."""
    return re.sub(r"[^a-z0-9]+", "_", re.sub(r"^the ", "", (name or "").lower().strip())).strip("_")


_CUT = re.compile(r",|;|:|\(| of | who | whose | with | at | in | on | from | for | to | against | by | and | near | over | under ")


def _head(label: str) -> str:
    """The words a label names its person by: before any "of", "with", comma and the like, and after a possessive ("the chandler's
    rival" is a rival; "widow of the guard" a widow; "a prisoner, once the smith" a prisoner)."""
    text = _CUT.split(" " + (label or "").lower().strip() + " ")[0]
    if "'s " in text + " " or "' " in text + " ":
        text = re.split(r"'s?\s", text + " ")[-1]
    return text


def trade_of(who: str, label: str, world, never=frozenset()) -> str:
    """(f545 part 5) The trade a proposal meant by a `who` that is neither an id nor a trade as written, or "": a trade it numbered or
    tagged ("merchant_1", "scout_01", "trade: guard", "new_scout"), else - a name of its own ("marek_vane") - the trade its label's
    head names, its last word or two ("greedy merchant", "an old elven warden"; never a word after "of" or before a possessive). A
    trade no situation casts is no one, never read on into another. The name is never kept (the engine names the people it makes);
    the person is cast as that trade, the town's own first, like any other."""
    def found(r: str) -> str | None:
        return None if r not in world.roles else ("" if r in never else r)
    w = re.sub(r"^(?:trade:\s*|new[_ ]|an? |the )", "", (who or "").strip().lower())
    got = found(re.sub(r"[_ ]?\d+$", "", w).replace(" ", "_"))
    if got is not None:
        return got
    head_words, all_words = set(re.findall(r"[a-z]+", _head(label))), set(re.findall(r"[a-z]+", (label or "").lower()))
    if (all_words & set(S.get("not_of_trade") or ())) or (head_words & set(S.get("not_of_trade_head") or ())):
        return ""                                                    # (f545's reviews) "the late miller", "a miller, now dead": no living
                                                                     # trade; "not" only in its head ("a miller who would not sell")
    words = re.findall(r"[a-z]+", _head(label))
    for cand in ([f"{words[-2]}_{words[-1]}"] if len(words) >= 2 else []) + words[-1:]:
        got = found(cand)
        if got is not None:
            return got
    return ""


def _goods() -> dict:
    """(f545) The goods a situation may name, in situations.yaml's order (trade goods first), each the world's own Good."""
    from engine import inventory
    return {g: inventory.GOODS[g] for g in S.get("goods") or () if g in inventory.GOODS}


def within_reach(world, town: str, rows=()) -> set[str]:
    """(f545) The situation's goods a player could get hold of in `town` without the situation: one a trade of the town sells (its
    places' written trades and its people's), or one the land about it gives (f545's review: a herb that grows, or meat from a creature
    that lives, in the country of the town's places and the places one road from them - no moonpetal in the desert)."""
    roles = {r.role for r in rows}
    here = set(retrieval.town_places(world, town)) if town else set()
    for pid in here:
        roles |= set(world.places[pid].residents or {})
    near = here | {n for pid in here for n in world.neighbors(pid)}
    biomes = {world.places[p].biome for p in near if p in world.places and world.places[p].biome}
    sold = {w.item for r in roles if r in world.roles for w in world.roles[r].sells if w.kind == "item" and w.item}

    def land(good) -> bool:
        return bool(set(good.grows_in or {}) & biomes) or any(set(world.bestiary[c].biomes) & biomes for c in good.drops_from or ()
                                                             if c in world.bestiary)
    return {g for g, good in _goods().items() if g in sold or land(good)}


def controller(p, person_of, world, store, ids: set[str]) -> dict:
    """(f546) Who or what imposes a condition and could lift it (the owner, 2026-11-08: "who or what controls the relevant conditions"
    - a person, a faction, a mechanism or an environmental condition): one of the situation's people by their id, or a few plain words
    for a group, a creature, a mechanism or nature. A person the parts do not hold, or words that name the game's machinery, leave it
    unknown ({by: "", by_kind: ""}), never the part dropped."""
    by, kind = (getattr(p, "by", "") or "").strip(), getattr(p, "by_kind", "") or ""
    if not by:
        return {"by": "", "by_kind": ""}
    who = person_of(by)
    if kind in ("", "person"):
        return {"by": who, "by_kind": "person"} if who else {"by": "", "by_kind": ""}
    words = plain(by, world, store)
    if not words or _raw(words, ids) or who:
        return {"by": who, "by_kind": "person"} if who else {"by": "", "by_kind": ""}
    return {"by": " ".join(words.split()[:6]), "by_kind": kind}


def established(state: dict, th: dict) -> list[str]:
    """(f546) What the situation's own prose has already made true, in its own sentences: the news it was born with, its stages so far,
    what is really going on, and the clues its people hold (the owner, 2026-11-08: the parts, made after the prose, "must agree with
    established facts")."""
    out = [n.get("text", "") for n in (state or {}).get("news", []) if n.get("thread") == th.get("id")][:2]
    out += [(s or {}).get("description", "") for s in (th.get("stages") or [])[:int(th.get("stage", 0)) + 1]]
    out += [th.get("truth", "")] + [(c or {}).get("text", "") for c in th.get("clues") or [] if not (c or {}).get("part")]
    seen, keep = set(), []
    for x in out:
        x = " ".join((x or "").split())
        if x and x.lower() not in seen:
            seen.add(x.lower())
            keep.append(x)
    return keep


AGREE_SYSTEM = ("You compare a short statement about a situation in a fantasy world with what is already established about that situation. "
                "same: it says what is already established, in other words. contradicts: it and an established statement cannot both be "
                "true. new: it adds something that is not already there and fits with it. Respond only with JSON matching the schema: "
                "{\"verdict\": \"new\", \"which\": 0}.")


def against(label: str, facts: list[str]) -> str:
    """(f546) Whether a part's words, a reader may see, agree with what the situation established: 'ok' when nothing established is close
    to them in meaning, or the check finds no contradiction; 'contradicts'; or 'unverified' when the check could not be asked (fail
    closed, as the canon check does: the engine's own words stand instead). One small call, only for words near an established line;
    (f546's review) its own task, optional and asked outside, never counted against the turn's required time."""
    import config
    from engine import canon
    if not label or not facts:
        return "ok"
    sims = canon._sims(label, facts)
    if sims is None:
        from engine import relevance
        near = relevance.pick(label, facts, k=3)
    else:
        near = [f for v, f in sorted(zip(sims, facts), key=lambda x: -x[0]) if v >= config.SIM_CANON][:3]
    if not near:
        return "ok"
    from llm.contracts import CanonCheck
    from llm.gateway import LLMError, generate
    listed = "\n".join(f"{i + 1}. {f}" for i, f in enumerate(near))
    try:
        r = generate("situation_agree", AGREE_SYSTEM, f"ALREADY ESTABLISHED:\n{listed}\n\nNEW STATEMENT: {label}", CanonCheck, temperature=0.1,
                     retries=1, max_tokens=40)
    except LLMError:
        return "unverified"
    return "contradicts" if r.verdict == "contradicts" else "ok"


def check(parts, store, world, tier: str, rng: random.Random, *, town: str, ways: bool, now: int,
          players=()) -> tuple[list[dict], list[tuple[dict, str]]]:
    """(accepted parts, dropped (part, reason)). `town` is the situation's town (its people are found first for a role); `ways` whether
    the situation offers the player a way through it (a closure of an only way needs one); `now` the minute it is born at; `players`
    the ids of every character playing (none of them is ever a part)."""
    players = {players} if isinstance(players, str) else set(players or ())
    from engine import pulse
    caps, why = S["caps"], S["reasons"]
    never = set(S.get("never_roles") or ())
    accepted: list[dict] = []
    dropped: list[tuple[dict, str]] = []

    def named(name: str, key: str) -> bool:                                  # "the Greywood" is greywood's name, not an id
        n = name.lower()
        return n == key or n.removeprefix("the ") == key
    ids = {pid for pid, pl in world.places.items() if not named(pl.name, pid)} | {rid for rid, r in world.roads.items() if not named(r.name, rid)}
    rows = retrieval.people_in_town(store, world, town) if town else []
    written = collections.Counter()                                          # the town's trades as its places are written, unmade or not
    for pid in (retrieval.town_places(world, town) if town else []):
        for role, n in (world.places[pid].residents or {}).items():
            written[role] += int(n or 1)
    used: set[str] = set()
    trades_used = collections.Counter()
    who_of: dict[str, str] = {}                                              # what the proposal called someone -> who they are

    def room(kind: str) -> str:                                             # (f550) a cap of null is none
        most = caps["parts"].get(tier)
        if most is not None and len(accepted) >= most:
            return "parts_cap"
        if kind == "person":
            return "people_cap" if caps.get("people") is not None and sum(a["kind"] == "person" for a in accepted) >= caps["people"] else ""
        return "kind_cap" if caps.get("each_other") is not None and sum(a["kind"] == kind for a in accepted) >= caps["each_other"] else ""

    def drop(part, reason: str) -> None:
        dropped.append((part.model_dump() if hasattr(part, "model_dump") else dict(part), why[reason]))

    def add(part: dict) -> None:
        accepted.append({**part, "v": V})

    new = 0
    stances = S.get("stances") or {}
    refused = {tuple(x) for x in stances.get("refused") or ()}
    lifted = {tuple(x) for x in stances.get("lifted") or ()}
    by_name = {r.name.lower(): r.id for r in (retrieval.people_in_town(store, world, town, gone=None) if town else [])}   # (f545's
                                                                             # review) a town person written by their name, gone or not

    def known(w: str) -> str:
        return w if store.npc_exists(w) else by_name.get(w.lower().replace("_", " ").strip(), "")

    def stands(x) -> bool:                                                   # a person part named outright that its own checks keep
        w = (x.who or "").strip()
        if not known(w) or w.lower() in ("player", "the player", "you") or w in players or _raw(plain(x.label, world, store), ids) \
                or (x.stake, x.want) in refused:
            return False
        n = store.load_npc(known(w))
        return not n.gone and n.role not in never
    reserved = {known((x.who or "").strip()) for x in parts.people if stands(x)}   # never cast for a trade read elsewhere
    placed: set[str] = set()                                                 # the trades someone not yet of the town stands for
    for p in parts.people:
        w = (p.who or "").strip()
        label = plain(p.label, world, store)
        if w.lower() in ("player", "the player", "you") or w in players:
            drop(p, "player"); continue
        if _raw(label, ids):
            drop(p, "raw_id"); continue
        if (p.stake, p.want) in refused:
            drop(p, "contrary"); continue                                    # (f545) one who blocks an end to it does not want it ended
        if known(w):
            n = store.load_npc(known(w))
            if n.gone:
                drop(p, "gone"); continue
            if n.role in never:
                drop(p, "not_a_person"); continue
            person, bind = n.id, "npc"
        elif (trade := w if w in world.roles and w not in never else trade_of(w, label, world, never)):
            free = next((r.id for r in rows if r.role == trade and r.id not in used and r.id not in reserved), "")
            if free:
                person, bind = free, "npc"                                   # (the owner) the town's own of that trade first...
            elif trades_used[trade] + sum(1 for r in rows if r.role == trade) < written[trade]:
                person, bind = trade, "town"                                 # ...one its places are written with, not yet met...
            else:
                person, bind = trade, "new"                                  # ...and only past them someone new
        else:
            drop(p, "not_a_person"); continue
        if (bind == "npc" and person in used) or w in who_of or (bind != "npc" and person in placed):
            drop(p, "twice"); continue                                       # (f545 part 5) one not yet of the town a trade, whatever
                                                                             # order the proposal names them in
        full = room("person")
        if full:
            drop(p, full); continue
        if bind == "new" and new >= caps["new_people"].get(tier, 0):
            drop(p, "new_cap"); continue
        new += bind == "new"
        if bind == "npc":
            used.add(person)
        else:
            trades_used[person] += 1
            placed.add(person)
        who_of[w] = person
        who_of.setdefault(person, person)                                    # named later by the id it bound to, it is the same person
        condition = "" if (p.want, p.condition) in lifted else p.condition    # (f545) one who wants coin needs no condition of pay
        add({"kind": "person", "who": person, "bind": bind, "new": bind == "new", "stake": p.stake, "want": p.want,
             "condition": condition, "holds": p.holds if p.holds in _goods() else "", "label": label,
             **({"lifted": p.condition} if condition != p.condition else {})})

    def person_of(ref: str) -> str:
        return who_of.get((ref or "").strip(), "")

    for p in parts.resources:
        if p.good not in _goods():
            drop(p, "not_a_good"); continue
        holder = person_of(p.holder) if p.holder else ""
        if p.holder and not holder:
            drop(p, "no_holder"); continue
        wanter = person_of(p.wanted_by) if p.state == "wanted" else ""      # (f545) a wanted good names who wants it, one of the situation
        if p.state == "wanted" and not wanter:
            drop(p, "no_wanter"); continue
        if wanter and holder == wanter:
            holder = ""                                     # (f545's review) "wanted, held by X" meant X wants it: nobody has it to hand
        label = plain(p.label, world, store)
        if _raw(label, ids):
            drop(p, "raw_id"); continue
        full = room("resource")
        if full:
            drop(p, full); continue
        add({"kind": "resource", "good": p.good, "state": p.state, "holder": holder, "wanted_by": wanter, "label": label})
    pairs: set[tuple] = set()
    for p in parts.ties:
        a, b = person_of(p.a), person_of(p.b)
        if not a or not b:
            drop(p, "no_end"); continue
        if a == b:
            drop(p, "self_tie"); continue
        if (frozenset((a, b)), p.tie) in pairs:
            drop(p, "twice"); continue
        full = room("tie")
        if full:
            drop(p, full); continue
        pairs.add((frozenset((a, b)), p.tie))
        add({"kind": "tie", "a": a, "b": b, "tie": p.tie})
    shut = pulse.shut_roads(store.load_world_state() or {}, world, now) if parts.conditions else set()
    priced: set[str] = set()                                                 # (f546's fourth review) a price rise is its town's
    for p in parts.conditions:
        on_road = p.on in world.roads
        if not (pulse.known(world, p.on) or on_road) or (on_road and p.kind == "prices"):
            drop(p, "not_a_place"); continue
        if p.kind == "prices":
            if pulse.town_of(world, p.on) in priced:
                drop(p, "twice"); continue                                   # a second rise in one town is the same rise, said twice
            priced.add(pulse.town_of(world, p.on))
        if p.kind == "closed" and on_road and not ways and not roads.way_round(world, p.on, shut):
            drop(p, "only_way"); continue
        label = plain(p.label, world, store)
        if _raw(label, ids):
            drop(p, "raw_id"); continue
        full = room("condition")
        if full:
            drop(p, full); continue
        if p.kind == "closed" and on_road:
            shut = shut | {p.on}                                             # two closures of one proposal never cut a town off between them
        add({"kind": "condition", "on": p.on, "what": p.kind, "label": label, **controller(p, person_of, world, store, ids)})
    for p in parts.evidence:
        holder, held = person_of(p.holder), "person"
        if not holder and pulse.known(world, p.holder):
            holder, held = p.holder, "place"
        if not holder:
            drop(p, "no_holder"); continue
        if held == "place" and p.certainty != "sure":
            drop(p, "claim_at_place"); continue
        points = person_of(p.points_to) or (p.points_to if pulse.known(world, p.points_to) or p.points_to in world.roads else "")
        if not points:
            drop(p, "points_nowhere"); continue
        label = plain(p.label, world, store)
        if not label or _raw(label, ids):
            drop(p, "raw_id"); continue
        full = room("evidence")
        if full:
            drop(p, full); continue
        add({"kind": "evidence", "holder": holder, "held": held, "points_to": points, "certainty": p.certainty, "label": label,
             "true": not (held == "person" and lies(holder, points, accepted))})        # (f557) a lie by incentive, never a roll
    settle(accepted, within_reach(world, town, rows))
    return accepted, dropped


def lies(holder: str, points: str, parts: list[dict]) -> bool:
    """(f557, the owner, 8 Nov: "some characters have an incentive to lie") Whether a person's claim is a lie: only when they have a
    reason to deceive - their stake or their want is served by others believing it (situations.yaml lies), or it points at someone
    they are at odds with - and never a claim against themselves. No roll: the same parts always give the same answer."""
    if not holder or points == holder:
        return False
    L = S.get("lies") or {}
    me = next((a for a in parts if a.get("kind") == "person" and a.get("who") == holder), None)
    if me is not None and (me.get("stake") in set(L.get("stakes") or ()) or me.get("want") in set(L.get("wants") or ())):
        return True
    return any(a.get("kind") == "tie" and a.get("tie") in set(L.get("ties") or ()) and {a.get("a"), a.get("b")} == {holder, points}
               for a in parts)


def settle(accepted: list[dict], reach=frozenset()) -> None:
    """(f545) What the whole situation decides of its parts, once every part is in, so nothing kept is a locked door or a lie no one can
    find out. A condition the situation offers no way to meet is lifted, and the person helps freely: told needs a piece of evidence
    someone else holds (a person, or a place), given needs a good that person wants which the player can get: one someone else of the
    situation has, or one `reach` holds (within_reach: sold in the town, or given by the land). A false piece of evidence stands only
    beside a true one that points elsewhere, so the player can weigh one against the other; else it is true after all. Each piece is
    weighed against the others as the engine first decided them, never as this pass leaves them, so the outcome does not hang on the
    order the pieces were proposed in. Each change is noted on the part (lifted, made_true) for the pulse's log."""
    evidence = [a for a in accepted if a["kind"] == "evidence"]
    has: dict[str, set] = collections.defaultdict(set)                         # good -> who of the situation has it
    for a in accepted:
        if a["kind"] == "person" and a.get("holds"):
            has[a["holds"]].add(a["who"])
        elif a["kind"] == "resource" and a.get("holder"):
            has[a["good"]].add(a["holder"])

    def to_hand(r, who) -> bool:
        return r["good"] in reach or bool(has[r["good"]] - {who})
    for a in accepted:
        if a["kind"] != "person" or not a.get("condition"):
            continue
        if a["condition"] == "told" and not any(e["holder"] != a["who"] for e in evidence):
            a["lifted"], a["condition"] = "told", ""
        elif a["condition"] == "given" and not any(r["kind"] == "resource" and r.get("wanted_by") == a["who"] and to_hand(r, a["who"])
                                                   for r in accepted):
            a["lifted"], a["condition"] = "given", ""
    first = [e["true"] for e in evidence]                                    # (f545's review) as decided, before any is made true
    for i, e in enumerate(evidence):
        if not first[i] and not any(j != i and first[j] and o["points_to"] != e["points_to"] for j, o in enumerate(evidence)):
            e["true"], e["made_true"] = True, True


def render(accepted: list[dict], store, world, key: str, with_truth: bool = False) -> str:
    """SITUATION PARTS: one line per accepted part, names and goods never ids. `with_truth` adds whether each piece of evidence holds
    (for a telling; never for the model that proposed the parts)."""
    P = S["phrases"]
    lines = []

    def trade(role: str) -> str:
        t = role.replace("_", " ")
        return P["new_person"].format(a="an" if t[:1].lower() in "aeiou" else "a", trade=t)

    def name(who: str) -> str:
        if store.npc_exists(who):
            return store.load_npc(who).name
        if who in world.places:
            return world.places[who].name
        if who in world.roads:
            return world.roads[who].name
        return trade(who)

    def good(g: str) -> str:
        gd = _goods().get(g)
        return gd.name if gd else g.replace("_", " ")

    for i, a in enumerate(accepted):
        rng = streams.fixed(key, "parts", i)
        k = a["kind"]
        if k == "person":
            line = rng.choice(P["stake"][a["stake"]]).format(name=name(a["who"])) + " " + rng.choice(P["want"][a["want"]])
            if a.get("condition"):
                line += ", " + rng.choice(P["condition"][a["condition"]])
            if a.get("holds"):
                line += ", " + rng.choice(P["holds"]).format(good=good(a["holds"]))
        elif k == "resource":
            line = rng.choice(P["state"][a["state"]]).format(good=good(a["good"]))
            if a.get("holder"):
                line += ", " + rng.choice(P["held_by"]).format(name=name(a["holder"]))
            if a.get("wanted_by"):
                line += ", " + rng.choice(P["wanted_by"]).format(name=name(a["wanted_by"]))
        elif k == "tie":
            line = rng.choice(P["tie"][a["tie"]]).format(name=name(a["a"]), other=name(a["b"]))
        elif k == "condition":
            line = rng.choice(P["kind"][a["what"]]).format(place=name(a["on"]))
        else:
            table = P["lies"] if a.get("held") == "place" else P["certainty"][a["certainty"]]
            line = rng.choice(table).format(holder=name(a["holder"]), label=a["label"].strip().rstrip("."), points=name(a["points_to"]))
            if with_truth:
                line += ". " + rng.choice(P["is_true"] if a.get("true", True) else P["is_false"]).rstrip(".")
        lines.append("- " + line[:1].upper() + line[1:].rstrip(".") + ".")
    return ("SITUATION PARTS:\n" + "\n".join(lines)) if lines else ""



# ---------- (f543) the proposal: what the model is shown, and the one call that asks it

def menus(store, world, state: dict, place, t: int, ways: bool = False) -> dict:
    """(f543) What a proposal at `place` may name, each list in a fixed order so the same world gives the same prompt: the town's
    people (the trades no situation casts left out, as check drops them; those at the situation's own place first, the rest in an
    order drawn from the situation's place and day, so a big town offers different people to different situations, at most
    proposal.people_most), the trades the town has besides them (its places' written trades nobody has met, and the trades of its
    people not listed: check finds or makes the town's own), the other trades of the world (someone new), the town's places and the
    places one road away, the roads that touch the town (those shut now, and, with no way through offered, those that are the only
    way between their ends, said so), and the goods."""
    import hashlib
    from engine import pulse
    town = pulse.town_of(world, place.id)
    never = set(S.get("never_roles") or ())
    rows = [n for n in retrieval.people_in_town(store, world, town) if n.role not in never]
    day = int(t) // 1440
    rows.sort(key=lambda n: (n.location != place.id, hashlib.sha1(f"{place.id}:{day}:{n.id}".encode()).hexdigest()))
    shown = rows[:int(S["proposal"]["people_most"])]
    listed = {n.role for n in shown}
    here = [pid for pid in retrieval.town_places(world, town) if pulse.known(world, pid)]
    town_trades = {role for pid in here for role in (world.places[pid].residents or {})} | {n.role for n in rows}
    written = sorted(town_trades - listed - never)
    others = sorted(r for r in world.roles if r not in never and r not in town_trades)
    touching = sorted(rid for rid, r in world.roads.items() if town in (r.from_, r.to))
    near = sorted({world.roads[rid].to if world.roads[rid].from_ == town else world.roads[rid].from_ for rid in touching} - set(here))
    shut = pulse.shut_roads(state or {}, world, t)
    only = set() if ways else {rid for rid in touching if rid not in shut and not roads.way_round(world, rid, shut)}
    return {"town": town, "people": shown, "written": written, "others": others,
            "places": [pid for pid in sorted(here) + near if pulse.known(world, pid)], "roads": touching, "shut": shut, "only": only,
            "goods": list(_goods())}


def prompt(store, world, state: dict, place, tier: str, t: int, trouble: str = "", ways: bool = False,
           established_lines=()) -> tuple[str, str]:
    """(f543) The proposal's system and user text: lean, ids beside names so the parts can be checked, every list in a fixed order.
    `ways` as check takes it: with none offered, a road that is the only way between its ends is said to be one. (f546) The lines the
    situation's prose has already made true, when it has any, are given as what nothing proposed may contradict."""
    from engine import clock, pulse
    from engine import pulse_prompts as pp
    m = menus(store, world, state, place, t, ways)
    caps, spec = S["caps"], S["proposal"]
    going = [x["title"] for x in (state or {}).get("threads", []) if x.get("status") == "active"
             and pulse.town_of(world, x.get("place") or "") == m["town"]][-int(spec["going_most"]):]
    region = world.regions[place.region].name if place.region in world.regions else ""

    def road(rid):
        r = world.roads[rid]
        mark = " (shut now)" if rid in m["shut"] else (" (the only way between its ends: it cannot be closed)" if rid in m["only"] else "")
        return f"{rid}: {r.name}, {r.from_} - {r.to}{mark}"
    lines = [f"TIER: {tier}",
             f"PLACE: {place.id} - {place.name}" + (f", {region}" if region else ""),
             f"SEASON: {clock.season(t)}",
             f"THE TROUBLE: {trouble.strip() or 'nothing set: whatever fits the place, the season and what is already going on'}",
             *([f"ALREADY ESTABLISHED (true: propose nothing that contradicts it): {' '.join(established_lines)}"] if established_lines else []),
             f"ALREADY GOING ON HERE: {'; '.join(going) or 'nothing'}",
             f"PEOPLE (id: name, trade): {'; '.join(f'{n.id}: {n.name}, {n.role}' for n in m['people']) or 'none known'}",
             f"TRADES OF THE TOWN: {', '.join(m['written']) or 'none besides the people above'}"]
    new = caps["new_people"].get(tier, 0)
    if new:
        lines.append(f"OTHER TRADES: {', '.join(m['others'])}")
    lines += [f"PLACES (id: name): {'; '.join(f'{pid}: {world.places[pid].name}' for pid in m['places'])}",
              "ROADS (id: name, from - to): " + ("; ".join(road(rid) for rid in m["roads"]) or "none"),
              f"GOODS (id: name): {'; '.join(f'{g}: {_goods()[g].name}' for g in m['goods'])}",
              how_many(tier)]
    return pp.PARTS_SYSTEM, "\n".join(lines)


def how_many(tier: str) -> str:
    """(f550) How many parts the prompt asks for: the tier's caps where it has them, else as many as the situation needs; the new
    people's cap always (a cap of null is none)."""
    caps = S["caps"]
    new = caps["new_people"].get(tier, 0)
    most, people, other = caps["parts"].get(tier), caps.get("people"), caps.get("each_other")
    newly = f"at most {new} of its people from OTHER TRADES" if new else "none of its people from outside the town"
    if most is None and people is None and other is None:
        return f"HOW MANY: as many parts as this situation needs; {newly}"
    bits = [f"{most} parts in all" if most is not None else "as many parts as the situation needs"]
    if people is not None:
        bits.append(f"{people} people")
    bits.append(newly)
    if other is not None:
        bits.append(f"{other} of each other kind")
    return "AT MOST: " + "; ".join(bits)


def propose(store, world, state: dict, place, tier: str, t: int, rng: random.Random, *, trouble: str = "", ways: bool = False,
            players=(), established_lines=()):
    """(f543) Ask the model for a situation's parts and check them: (the answer, accepted, dropped). An LLMError (or the budget's) is
    the caller's to catch: a situation stands on the engine's own build without parts. (f546) Asked in play by a birth's own operation
    (engine/situation_parts.py birth), with what the situation's prose established."""
    from engine import pulse
    from llm.contracts import SituationParts
    from llm.gateway import generate
    system, user = prompt(store, world, state, place, tier, t, trouble, ways, established_lines)
    spec = S["proposal"]
    parts = generate("situation_parts", system, user, SituationParts, temperature=float(spec["temperature"]),
                     max_tokens=int(spec["max_tokens"]))
    accepted, dropped = check(parts, store, world, tier, rng, town=pulse.town_of(world, place.id), ways=ways, now=t, players=players)
    return parts, accepted, dropped


def arms() -> dict:
    """(f543) The arms the proposal's thinking is measured in, by name: {think, budget (None uncapped or off)}."""
    return {name: {"think": bool((a or {}).get("think")), "budget": (a or {}).get("budget")}
            for name, a in ((S.get("thinking") or {}).get("arms") or {}).items()}


def measured_problems(doc: dict | None = None) -> list[str]:
    """(f543) data/measured/situation_thinking.yaml, when a run has written it (outside the data hash): its task one the budget knows,
    every arm one situations.yaml names, each measure a number where one is given, and the verdict off or a measured arm that passed
    the rule; a report, never a crash."""
    path = ROOT / "data" / "measured" / "situation_thinking.yaml"
    if doc is None:
        if not path.exists():
            return []
        try:
            doc = yamlio.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            return [f"situation_thinking.yaml: not YAML ({str(e).splitlines()[0]})"]
    if not isinstance(doc, dict):
        return ["situation_thinking.yaml: a table of the task, its arms and the verdict"]
    bad = []
    tasks = (yamlio.safe_load((ROOT / "data" / "rules" / "budget.yaml").read_text(encoding="utf-8")) or {}).get("tasks") or {}
    if doc.get("task") not in tasks:
        bad.append(f"situation_thinking.yaml task: '{doc.get('task')}' is not a task budget.yaml knows")
    known = set(arms())
    measured = doc.get("arms")
    if not isinstance(measured, dict) or not measured:
        bad.append("situation_thinking.yaml arms: needs the arms it measured")
        measured = {}
    for name, row in measured.items():
        if name not in known:
            bad.append(f"situation_thinking.yaml arms.{name}: not an arm situations.yaml names ({sorted(known)})")
        if not isinstance(row, dict):
            bad.append(f"situation_thinking.yaml arms.{name}: a table of its measures")
            continue
        for k, v in row.items():
            if k in ("accepted_per_proposal", "finished_share", "p50_card_seconds", "p90_card_seconds", "preferred_share") and v is not None \
                    and (not isinstance(v, (int, float)) or isinstance(v, bool)):
                bad.append(f"situation_thinking.yaml arms.{name}.{k}: a number ({v!r})")
    verdict = doc.get("verdict")
    if verdict not in known:
        bad.append(f"situation_thinking.yaml verdict: '{verdict}' is not an arm situations.yaml names")
    elif verdict != "off" and not (isinstance(measured.get(verdict), dict) and measured[verdict].get("passes") is True):
        bad.append(f"situation_thinking.yaml verdict: '{verdict}' is not a measured arm that passed the rule")
    return bad


# The slots every line of a table must carry (data_check holds them), and the sample that fills them all.
NEEDS = {"stake": {"name"}, "want": set(), "condition": set(), "tie": {"name", "other"}, "state": {"good"}, "kind": {"place"},
         "certainty": {"holder", "label", "points"}}
FLAT_NEEDS = {"holds": {"good"}, "held_by": {"name"}, "wanted_by": {"name"}, "lies": {"holder", "label", "points"}, "is_true": set(),
              "is_false": set()}
SAMPLE = {"name": "Hollis", "other": "Maud", "good": "salt", "place": "the ford", "holder": "Hollis", "label": "a cut rope",
          "points": "the toll keeper", "trade": "bargeman", "a": "a"}


def _line_problems(where: str, line, needs: set, sample: dict | None = None) -> list[str]:
    """A phrase line: words, with the slots `needs` and none outside `sample`'s (the render's own, by default)."""
    import string
    SAMPLE = sample if sample is not None else globals()["SAMPLE"]
    if not isinstance(line, str) or not line.strip():
        return [f"situations.yaml {where}: a line of words is needed ({line!r})"]
    try:
        slots = {f for _, f, _, _ in string.Formatter().parse(line) if f is not None}
    except ValueError as e:
        return [f"situations.yaml {where}: '{line}' ({e})"]
    bad = [f"situations.yaml {where}: '{line}' names {sorted(slots - set(SAMPLE))}, not among {sorted(SAMPLE)}"] if slots - set(SAMPLE) else []
    if needs - slots:
        bad.append(f"situations.yaml {where}: '{line}' leaves out {sorted(needs - slots)}")
    if not bad:
        out = line.format(**SAMPLE)
        if "{" in out or "}" in out or "_" in out:
            bad.append(f"situations.yaml {where}: '{line}' leaves machinery")
    return bad


# (f543's review) Where in PARTS_SYSTEM each list's words are given: from the field's own label to the next one, so a word is held to
# its own field (a stake word in the stakes, never found by chance in "kind" or "only ever sure").
SEGMENTS = {"stakes": ("stake:", "want:"), "wants": ("want:", "condition:"), "conditions": ("condition:", "holds:"),
            "resource_states": ("resources:", "ties:"), "ties": ("ties:", "conditions: each"), "place_kinds": ("conditions: each", "evidence:"),
            "certainties": ("certainty -", "Evidence lying"), "controllers": ("by_kind:", "evidence:")}


def rulings_problems(c=None) -> list[str]:
    """(f547) The ruling's words held equal to the contract's both ways, each with a layer, the kinds it may change, who may do it and
    whether it is a gain; the reasons a change may rest on likewise; the lists that name some of them; and the phrases each kept
    change is told in, four lines or more."""
    import typing
    if c is None:
        from llm import contracts as c
    bad = []
    RU = S.get("rulings") or {}
    ch = RU.get("changes") or {}
    lit = lambda f: set(typing.get_args(c.RulingChange.model_fields[f].annotation))
    if set(ch) != lit("becomes"):
        bad.append(f"situations.yaml rulings.changes: {sorted(set(ch) ^ lit('becomes'))} differ from the contract's RulingChange.becomes")
    for w, row in ch.items():
        row = row or {}
        if row.get("layer") not in ("belief", "feeling", "willingness", "action", "world"):
            bad.append(f"situations.yaml rulings.changes.{w}.layer: belief, feeling, willingness, action or world")
        if not isinstance(row.get("kinds"), list) or not row["kinds"] or not set(row["kinds"]) <= {"person", "resource", "tie", "condition",
                                                                                                   "evidence"}:
            bad.append(f"situations.yaml rulings.changes.{w}.kinds: some of person, resource, tie, condition and evidence")
        if row.get("actor") not in ("act", "person", "self", "either"):
            bad.append(f"situations.yaml rulings.changes.{w}.actor: act, person, self or either")
        if not isinstance(row.get("better"), bool):
            bad.append(f"situations.yaml rulings.changes.{w}.better: true or false")
    if set(RU.get("because") or ()) != lit("because"):
        bad.append("situations.yaml rulings.because: the contract's RulingChange.because, both ways")
    eb = RU.get("engine_because")
    if not (isinstance(eb, list) and eb and not set(eb) & set(RU.get("because") or ())):
        bad.append("situations.yaml rulings.engine_because: a list of what the engine alone sets, none of rulings.because")
    will = {w for w, row in ch.items() if (row or {}).get("layer") == "willingness"}
    if not set(RU.get("wont") or ()) <= will or not RU.get("wont"):
        bad.append("situations.yaml rulings.wont: some of the willingness words")
    if not set(RU.get("cooperative") or ()) <= set(ch) or not RU.get("cooperative"):
        bad.append("situations.yaml rulings.cooperative: some of the change words")
    from engine import budget
    expected = int((budget.TASKS.get("event_judge") or {}).get("answer_tokens") or 0)
    if not isinstance(RU.get("max_tokens"), int) or isinstance(RU.get("max_tokens"), bool) or RU["max_tokens"] < 1.5 * expected:
        bad.append(f"situations.yaml rulings.max_tokens: at least half again the answer budget.yaml expects ({expected} tokens)")
    if not isinstance(RU.get("words_only_acts"), list) or not RU["words_only_acts"]:
        bad.append("situations.yaml rulings.words_only_acts: the acts that are words alone")
    if not isinstance(RU.get("goods_acts"), list) or not RU["goods_acts"]:
        bad.append("situations.yaml rulings.goods_acts: the acts that hand goods over")
    if not isinstance(RU.get("force_acts"), list) or not RU["force_acts"] or set(RU["force_acts"]) & set(RU.get("goods_acts") or ()) \
            or set(RU["force_acts"]) & set(RU.get("words_only_acts") or ()):
        bad.append("situations.yaml rulings.force_acts: the acts of violence, none of them words or goods (f547's second review)")
    hl = RU.get("hand_lifts") or {}
    if set(hl) != set(S.get("lists", {}).get("controllers") or ()) | {"world"} \
            or any(not isinstance(v, list) or not v or not set(v) <= {"force", "work"} for v in hl.values()):
        bad.append("situations.yaml rulings.hand_lifts: each controller (lists.controllers) and world, with force and/or work")
    if not RU.get("warned_may") or not set(RU["warned_may"]) <= set(ch) or set(RU["warned_may"]) & set(RU.get("cooperative") or ()) \
            or any((ch.get(w) or {}).get("layer") in ("belief", "world") for w in RU["warned_may"]):
        bad.append("situations.yaml rulings.warned_may: some of the change words, none cooperative, no belief and nothing in the world")
    for k in ("no_part", "not_actor", "not_heard", "words_only", "failed_act", "unpaid", "no_goods", "no_evidence", "no_authority",
              "no_means", "unwilling", "still_committed", "still_refusing", "rests_on", "gone", "twice", "too_many", "not_there", "already"):
        if not (S.get("reasons") or {}).get(k):
            bad.append(f"situations.yaml reasons.{k}: a reason is needed (f547, the ruling's)")
    for k in ("most", "window", "trust"):
        if not isinstance(RU.get(k), int) or isinstance(RU.get(k), bool) or RU[k] < 1:
            bad.append(f"situations.yaml rulings.{k}: a whole number above 0")
    for table, keys, slots in (("beliefs", ("believes", "doubts"), {"name"}), ("moods", ("afraid", "angry", "grateful"), set())):
        for k in keys:
            got = (RU.get(table) or {}).get(k)
            if not isinstance(got, list) or len(got) < 4:
                bad.append(f"situations.yaml rulings.{table}.{k}: four lines or more")
                continue
            for line in got:
                bad += _line_problems(f"rulings.{table}.{k}", line, slots, {"name": "Hollis"})
    got = RU.get("warned")
    if not isinstance(got, list) or len(got) < 4:
        bad.append("situations.yaml rulings.warned: four lines or more")
    else:
        for line in got:
            bad += _line_problems("rulings.warned", line, {"name", "who"}, {"name": "Hollis", "who": "Maud"})
    return bad


def prompt_problems(lists: dict) -> list[str]:
    """(f543) The proposal is told every word it may use, each as a whole word inside its own field's lines."""
    import re
    from engine import pulse_prompts as pp
    text, bad = pp.PARTS_SYSTEM, []
    for name, words in lists.items():
        start, end = SEGMENTS.get(name, ("", ""))
        a = text.find(start) if start else -1
        b = text.find(end, a + len(start)) if a >= 0 else -1
        if a < 0 or b < 0:
            bad.append(f"pulse_prompts.PARTS_SYSTEM: the lines for lists.{name} ('{start}' to '{end}') are not found")
            continue
        seg = text[a:b]
        for w in words or ():
            if not re.search(rf"(?<![\w_]){re.escape(w)}(?![\w_])", seg):
                bad.append(f"situations.yaml lists.{name}: '{w}' is not among the words the proposal's prompt gives for it "
                           f"(pulse_prompts.PARTS_SYSTEM, from '{start}')")
    return bad


def problems() -> list[str]:
    """(f542) The lists held equal to the contract's Literals both ways, the caps and chances sound, every phrase table filled, each of
    its lines carrying its own slots and no others; a report, never a crash."""
    import typing
    from llm import contracts as c
    bad = []
    L = S.get("lists") or {}
    for key in ("machinery_words", "not_of_trade", "not_of_trade_head"):
        mw = S.get(key)
        if not isinstance(mw, list) or not all(isinstance(w, str) and re.fullmatch(r"[a-z]+", w) for w in mw):
            bad.append(f"situations.yaml {key}: a list of lowercase words (quote one YAML reads as something else: \"null\", \"false\")")

    def lit(model, field) -> set:
        return {x for x in typing.get_args(model.model_fields[field].annotation) if x != ""}
    for name, model, field in (("stakes", c.PartPerson, "stake"), ("wants", c.PartPerson, "want"), ("conditions", c.PartPerson, "condition"),
                               ("ties", c.PartTie, "tie"), ("resource_states", c.PartResource, "state"),
                               ("place_kinds", c.PartCondition, "kind"), ("certainties", c.PartEvidence, "certainty"),
                               ("controllers", c.PartCondition, "by_kind")):
        got = set(L.get(name) or ())
        if got != lit(model, field):
            bad.append(f"situations.yaml lists.{name}: {sorted(got)} differs from the contract's {sorted(lit(model, field))}")
    effects = set(typing.get_args(c.WorldEffect.model_fields["kind"].annotation))
    for k in lit(c.PartCondition, "kind"):
        if k not in effects:
            bad.append(f"the contract's PartCondition kind '{k}' is not an effect the pulse applies")
    caps = S.get("caps") or {}
    whole = lambda n, least: isinstance(n, int) and not isinstance(n, bool) and n >= least
    for t, none_ok in (("parts", True), ("new_people", False)):                # (f550) a part cap may be null (none); new people never
        table = caps.get(t) or {}
        for tier in TIERS:
            n = table.get(tier)
            if tier not in table or not (whole(n, 0) or (none_ok and n is None)):
                bad.append(f"situations.yaml caps.{t}.{tier}: a whole number of 0 or more" + (", or null for none" if none_ok else "")
                           + f" ({n!r})")
    for t in ("people", "each_other"):
        if t not in caps or not (caps[t] is None or whole(caps[t], 1)):
            bad.append(f"situations.yaml caps.{t}: a whole number of 1 or more, or null for none")
    from engine import inventory                                         # (f545) the goods a situation turns on: the world's, never kit
    G = S.get("goods")
    if not isinstance(G, list) or not G:
        bad.append("situations.yaml goods: a list of the goods a situation may name")
    else:
        for g in G:
            if g not in inventory.GOODS:
                bad.append(f"situations.yaml goods: '{g}' is not a good of data/world/goods.yaml")
            elif inventory.GOODS[g].kind in ("book", "codex"):
                bad.append(f"situations.yaml goods: '{g}' is the player's kit (a {inventory.GOODS[g].kind}), never a situation's cargo")
        if len(set(G)) != len(G):
            bad.append("situations.yaml goods: a good listed twice")
    if "false_chance" in S:
        bad.append("situations.yaml false_chance: a lie is never a roll (the owner, 8 Nov); say who has a reason to lie in lies")
    LI = S.get("lies")
    if not isinstance(LI, dict) or set(LI) != {"stakes", "wants", "ties"}:
        bad.append("situations.yaml lies: stakes, wants and ties, each a list (and nothing else)")
        LI = {}
    for key, lst in (("stakes", "stakes"), ("wants", "wants"), ("ties", "ties")):
        got = LI.get(key)
        if not isinstance(got, list) or not set(got) <= set(L.get(lst) or ()):
            bad.append(f"situations.yaml lies.{key}: some of lists.{lst}")
    P = S.get("phrases") or {}
    tables = {"stake": L.get("stakes"), "want": L.get("wants"), "condition": L.get("conditions"), "tie": L.get("ties"),
              "state": L.get("resource_states"), "kind": L.get("place_kinds"), "certainty": L.get("certainties")}
    for table, keys in tables.items():
        for k in keys or ():
            got = (P.get(table) or {}).get(k) if isinstance(P.get(table), dict) else None
            if not isinstance(got, list) or len(got) < 4:
                bad.append(f"situations.yaml phrases.{table}.{k}: four lines or more, so nothing is told the same way twice running")
                continue
            for line in got:
                bad += _line_problems(f"phrases.{table}.{k}", line, NEEDS[table])
    for flat, needs in FLAT_NEEDS.items():
        got = P.get(flat)
        if not isinstance(got, list) or len(got) < 4:
            bad.append(f"situations.yaml phrases.{flat}: four lines or more")
            continue
        for line in got:
            bad += _line_problems(f"phrases.{flat}", line, needs)
    bad += _line_problems("phrases.new_person", P.get("new_person"), {"a", "trade"})
    bad += prompt_problems(L)
    spec = S.get("proposal") or {}
    if not isinstance(spec.get("temperature"), (int, float)) or isinstance(spec.get("temperature"), bool) or not 0 <= spec["temperature"] <= 1.5:
        bad.append("situations.yaml proposal.temperature: a number between 0 and 1.5")
    for k in ("max_tokens", "people_most", "going_most"):
        if not isinstance(spec.get(k), int) or isinstance(spec.get(k), bool) or spec[k] < 1:
            bad.append(f"situations.yaml proposal.{k}: a whole number above 0")
    from engine import budget
    expected = int((budget.TASKS.get("situation_parts") or {}).get("answer_tokens") or 0)
    if isinstance(spec.get("max_tokens"), int) and spec["max_tokens"] < 1.5 * expected:
        bad.append(f"situations.yaml proposal.max_tokens: at least half again the answer budget.yaml expects ({expected} tokens), so the "
                   "long answers are not cut off (f545's re-test: answers reached 900)")
    T = S.get("thinking") or {}
    A = T.get("arms") or {}
    if not isinstance(A.get("off"), dict) or A["off"].get("think") is not False:
        bad.append("situations.yaml thinking.arms.off: the arm every other is read against, thinking off")
    for name, a in A.items():
        b = (a or {}).get("budget")
        if (a or {}).get("think") is not True and name != "off":
            bad.append(f"situations.yaml thinking.arms.{name}: an arm other than off thinks")
        if b is not None and (not isinstance(b, int) or isinstance(b, bool) or b < 1 or not (a or {}).get("think")):
            bad.append(f"situations.yaml thinking.arms.{name}.budget: a whole number above 0, on an arm that thinks")
    for k, lo, hi in (("prefer_share", 0.5, 1), ("slot_seconds", 1, 3600)):
        v = T.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not lo <= v <= hi:
            bad.append(f"situations.yaml thinking.{k}: a number from {lo} to {hi}")
    bad += measured_problems()
    st = S.get("stances")                                                # (f545) the stances refused and the conditions lifted, in the lists' words
    if not isinstance(st, dict) or set(st) != {"refused", "lifted"} or not all(isinstance(st[k], list) for k in st):
        bad.append("situations.yaml stances: refused and lifted, each a list of pairs (and nothing else)")
        st = {}
    for which, cols in (("refused", (("stakes", "stake"), ("wants", "want"))), ("lifted", (("wants", "want"), ("conditions", "condition")))):
        for pair in st.get(which) or []:
            if not isinstance(pair, list) or len(pair) != 2 or any(w not in (L.get(lst) or ()) for w, (lst, _) in zip(pair, cols)):
                bad.append(f"situations.yaml stances.{which}: {pair!r} is not a [{cols[0][1]}, {cols[1][1]}] pair of the lists' words")
    for k in ("not_a_person", "gone", "player", "twice", "people_cap", "new_cap", "parts_cap", "kind_cap", "not_a_good", "no_holder",
              "no_end", "self_tie", "not_a_place", "only_way", "points_nowhere", "raw_id", "claim_at_place", "contrary", "no_wanter",
              "contradicts"):
        if not (S.get("reasons") or {}).get(k):
            bad.append(f"situations.yaml reasons.{k}: a reason is needed")
    B = S.get("births") or {}                                            # (f546) births and the engine's own parts
    if not isinstance(B.get("tiers"), list) or not set(B["tiers"]) <= {"normal", "uncommon", "rare", "campaign"}:
        bad.append("situations.yaml births.tiers: of normal, uncommon, rare and campaign")
    if not isinstance(B.get("reach_tiers"), list) or not set(B["reach_tiers"]) <= set(B.get("tiers") or ()):
        bad.append("situations.yaml births.reach_tiers: some of births.tiers (born once a character can meet them)")
    if not isinstance(B.get("tries"), int) or isinstance(B.get("tries"), bool) or B["tries"] < 1:
        bad.append("situations.yaml births.tries: a whole number above 0")
    if not isinstance(B.get("adopt_tiers"), list) or not set(B["adopt_tiers"]) <= {"normal", "uncommon", "rare", "campaign", "cataclysm"}:
        bad.append("situations.yaml births.adopt_tiers: of the tiers only")
    elif isinstance(B.get("tiers"), list) and not set(B["tiers"]) <= set(B["adopt_tiers"]):
        bad.append("situations.yaml births.adopt_tiers: every tier of births.tiers, so a birth past its tries takes the engine's own parts")
    H = S.get("heart") or {}
    if not isinstance(H.get("threat_kinds"), list) or not H["threat_kinds"] or not set(H["threat_kinds"]) <= set(L.get("place_kinds") or ()):
        bad.append("situations.yaml heart.threat_kinds: some of lists.place_kinds")
    if not isinstance(H.get("stake_states"), list) or not set(H["stake_states"]) <= set(L.get("resource_states") or ()):
        bad.append("situations.yaml heart.stake_states: some of lists.resource_states")
    bad += rulings_problems(c)
    return bad
