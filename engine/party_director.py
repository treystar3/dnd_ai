"""The party conversation director: who of the companions present gets the floor for a moment, and whom each answers.

The model writes how people speak; the engine decides who speaks and why. A moment (a Beat) is what happened: an idle topic, something
pressing, something grave, or a deed of the player's. Each companion present is scored on reasons the engine knows exactly - the moment
is about them, they have a view on what the player did, someone is hurt and looking after people is who they are, the moment is close in
meaning to their own life - and, in idle talk, on how much they feel like joining in, less a little if they spoke last time. Only those
with reason enough speak: a first, then a second, then (with a higher bar) a third. Feeling something is not saying it: a companion who
does not get the floor is still affected (their bond, their memory); they simply say nothing this time.

The plan also says whom each later speaker answers: one who sees a deed the other way answers the first speaker, not the player; someone
worried about a hurt companion answers them. It is put to the line writer as one short block, and the first speaker is checked.

Numbers live in data/world/banter.yaml director. This module never writes dialogue, keeps no canon and builds no character prompt."""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Beat:
    kind: str                                         # idle | pressing | grave | deed | said
    text: str                                         # what happened, in words (the hook, the deed, or what the player said)
    about: str | None = None                          # the member the moment is about
    stances: dict = field(default_factory=dict)       # member id -> approve | disapprove (a deed)
    weight: str = "light"                             # light | personal | heavy: a heavy moment is one everyone present has a say in
    named: list = field(default_factory=list)         # said: the others the player's words are about
    party: bool = False                               # said: the words concern everyone travelling together
    addressee: str | None = None                      # said: the one the player spoke to (already answered; not among those scored)
    concerns: str | None = None                       # whom it concerns, for how hard it hits (engine/severity.py): a member id, 'player', or None
    short: str = ""                                   # what happened, in a few words, for what it leaves behind ('Tamsin's death')
    in_fight: bool = False                            # it happened mid-fight: one outburst each


@dataclass
class Reaction:
    member_id: str
    score: float
    reasons: list = field(default_factory=list)       # (points, why)
    reasoned: bool = False                            # something real to say (not only feeling like talking): goes ahead of anyone without
    close: dict = field(default_factory=dict)         # how close the moment came to their own life, and to the others' (for the live check)


@dataclass
class Turn:
    speaker_id: str
    target: str                                       # "player", "party", or a member id
    purpose: str                                      # approve, disapprove, agree, disagree, look_after, answer, open


@dataclass
class Plan:
    beat: Beat
    reactions: list
    turns: list

    @property
    def speaker_ids(self) -> list:
        return [t.speaker_id for t in self.turns]


def D() -> dict:
    from engine import banter
    return banter.B["banter"]["director"]


def beat_from_hook(hook_kind: str, hook: str, about: dict | None, concerns: str | None = None, short: str = "") -> Beat:
    from engine import context
    kind = "grave" if hook_kind in context.GRAVE_HOOKS else ("pressing" if hook_kind in context.PRESSING_HOOKS else "idle")
    topic = (hook or "").split(": ", 1)[-1] if ": " in (hook or "") else (hook or "")      # the topic itself, not the hook's wording around it
    return Beat(kind, topic, about["id"] if about else None, weight=D()["hook_weight"].get(hook_kind, "light"),
                concerns=concerns or (about["id"] if about else None), short=short)


def beat_from_deed(text: str, stances: dict) -> Beat:
    return Beat("deed", text, None, dict(stances))


def beat_from_words(text: str, addressee: str, named: list, party: bool, weight: str) -> Beat:
    """The player said something to one companion; the others overheard. Whether they join in is theirs to have reason for."""
    return Beat("said", text, None, {}, weight if weight in ("light", "personal", "heavy") else "light", list(named), bool(party), addressee,
                concerns=named[0] if named else "player")


def beat_from_event(text: str, weight: str, concerns: str | None = None, short: str = "", in_fight: bool = False) -> Beat:
    """Something that happened in front of them - a death, a betrayal, something grim found: whoever raises it says how grave it is and
    whom it concerns. The same path for every kind of event."""
    return Beat("grave" if weight == "heavy" else ("pressing" if weight == "personal" else "idle"), text, None,
                weight=weight if weight in ("light", "personal", "heavy") else "light", concerns=concerns, short=short, in_fight=in_fight)


def read_words(text: str, addressee: str, reply: str, others: list[dict]) -> tuple[list, bool, str]:
    """What the player's words to one companion mean for the others present, read by the model from meaning alone: whom of the others they
    are about, whether they concern everyone travelling together, and how heavy they are. ([], False, 'light') if the read fails."""
    from llm.contracts import Overheard
    from llm.gateway import generate, LLMError
    names = [o["name"] for o in others]
    req = (f"THE PLAYER SAID, TO {addressee}: {' '.join(text.split())}\n" + (f"{addressee} ANSWERED: {' '.join(reply.split())}\n" if reply else "") +
           "ALSO PRESENT, LISTENING: " + ", ".join(names))
    try:
        r = generate("overheard", D()["read_words"], req, Overheard, temperature=0.1, retries=1, max_tokens=120, validation_context={"names": names})
    except LLMError:
        return [], False, "light"
    ids = [o["id"] for o in others if o["name"] in r.about and named(text, o["name"])]     # the words must name them: the model's read
    return ids, r.party, r.weight                                                         # alone once put the only listener in every time


def named(text: str, name: str) -> bool:
    """Do the player's words name this person: their full name or their first name, as a word?"""
    import re
    parts = [name] + [p for p in name.split()[:1] if len(p) > 2]
    return any(re.search(rf"\b{re.escape(p)}\b", text or "", re.I) for p in parts)


def caretaker(member: dict) -> bool:
    C = D()["caretaker"]
    return bool(set(member.get("temper") or []) & set(C["tempers"])) or member.get("role") in C["roles"]


def records(member: dict) -> list[str]:
    """What is known of their own life: their details, what they have said of themselves, what they remember."""
    return list(member.get("details") or []) + [x["text"] for k in ("canon", "traits", "memories") for x in member.get(k, [])]


def relevant(member: dict, text: str, present: list[dict] | None = None, bystanders: list[dict] | None = None, out: dict | None = None) -> bool:
    """Is the moment close in meaning to their own life in particular? Only their own records: what one companion was told privately is
    never another's. Any line is somewhat close to anyone's life, so it counts only when it stands out: clearly closer to their records
    than to those of everyone else present (bystanders too: the one the player was speaking to). The names of those present are taken
    out first: 'Bram is hurt' is not close to 'I started travelling with Bram'. out, if given, gets the two closenesses."""
    import re
    import config
    from engine import relevance
    everyone = [m for m in (present or [member]) + list(bystanders or [])]
    names = {p for m in everyone for p in m.get("name", "").split() if len(p) > 2}
    strip = (lambda t: re.sub(r"\b(" + "|".join(map(re.escape, names)) + r")\b", "", t)) if names else (lambda t: t)
    theirs = [strip(o) for m in everyone if m["id"] != member["id"] for o in records(m)]
    ok, a, b = relevance.stands_out(strip(text or ""), [strip(o) for o in records(member)], theirs, config.SIM_TOPIC, config.SIM_STANDOUT)
    if out is not None:
        out.update(mine=a, theirs=b)
    return ok


def evaluate(member: dict, beat: Beat, present: list[dict], rng: random.Random, bystanders: list[dict] | None = None) -> Reaction:
    S = D()["score"]
    r = Reaction(member["id"], 0.0, [])

    def add(points, why, chatter=False):
        r.score += points
        r.reasons.append((round(points), why))
        if points > 0 and not chatter:
            r.reasoned = True

    if beat.weight == "heavy" and beat.kind == "said":   # the player opened up: those who know them answer, by how well (not a shared moment)
        from engine import severity
        close = severity.closeness(member, "player")
        pts = S["opened_up"].get(close, 0)
        if pts:
            add(pts, f"the player opened up about something heavy, and they {D()['say']['know_player'][close]}")
    elif beat.weight == "heavy":
        add(S["heavy"], "a moment everyone has a say in")
    if beat.kind == "said":                              # overheard: only real reasons, never feeling like talking - it is not their conversation
        if member["id"] in beat.named:
            add(S["subject"], "the player's words are about them")
        if beat.party:
            add(S["party"], "it concerns all of them")
        if relevant(member, beat.text, present, bystanders, out=r.close):
            add(S["relevant_said"], "close to their own life")
        return r
    if beat.about == member["id"]:
        add(S["subject"], "the moment is about them")
    st = beat.stances.get(member["id"])
    if st:
        add(S["stance"], f"{'approves of' if st == 'approve' else 'cannot stand'} what the player did")
    if beat.kind in ("grave", "pressing") and beat.about and beat.about != member["id"] and caretaker(member):
        add(S["caretaker"], "someone is hurt, and they look after people")
    if beat.kind in ("grave", "pressing") and not beat.about:
        add(S["shared"], "they were in it too")
    if relevant(member, beat.text, present, bystanders, out=r.close):
        add(S["relevant"], "close to their own life")
    if beat.kind == "idle":
        add(rng.uniform(0, S["small_talk"]), "feels like talking", chatter=True)
        latest = max((m.get("banter_at", -1) for m in present), default=-1)
        if latest >= 0 and member.get("banter_at") == latest:
            add(S["spoke_last"], "spoke last time")
        latest_start = max((m.get("started_at", -1) for m in present), default=-1)
        if latest_start >= 0 and member.get("started_at") == latest_start:
            add(S["started_last"], "opened last time")
    return r


def plan(beat: Beat, present: list[dict], rng: random.Random, must_start: bool = True, bystanders: list[dict] | None = None) -> Plan:
    """Who speaks, in order, and whom each answers. With must_start, someone always opens (idle talk the game has decided to have); a deed
    with nobody holding a view gets nobody."""
    G = D()
    reactions = [evaluate(m, beat, present, rng, bystanders) for m in present]
    jitter = {r.member_id: rng.uniform(0, G["tie_band"]) for r in reactions}      # close scores are as good as equal
    order = sorted(reactions, key=lambda r: (not r.reasoned, -(r.score + jitter[r.member_id])))   # something to say beats feeling chatty
    bars = [G["first"], G["second"], G["third"]]
    most = len(present) if beat.weight == "heavy" else min(G["most"].get(beat.kind, 2), len(present))
    chosen = []
    for r in order:
        if len(chosen) >= most:
            break
        if r.score >= bars[min(len(chosen), 2)] or (not chosen and must_start and beat.kind != "deed"):
            chosen.append(r.member_id)
    if beat.about in [m["id"] for m in present]:          # the one the moment is about opens it: their topic, their wound, their worry
        chosen = [beat.about] + [c for c in chosen if c != beat.about][:max(0, most - 1)]
    turns = []
    for i, mid in enumerate(chosen):
        st = beat.stances.get(mid)
        if i == 0:
            if beat.kind == "said":                       # joining in what the player and the one they spoke to were saying
                turns.append(Turn(mid, beat.addressee or "player", "join"))
            else:
                turns.append(Turn(mid, "player" if beat.kind == "deed" else "party", st or "open"))
            continue
        first = chosen[0]
        if beat.kind == "deed" and st and beat.stances.get(first):
            turns.append(Turn(mid, first, "agree" if st == beat.stances[first] else "disagree"))
        elif beat.kind in ("grave", "pressing") and beat.about and mid != beat.about and beat.about in chosen[:i]:
            turns.append(Turn(mid, beat.about, "look_after"))
        else:
            turns.append(Turn(mid, chosen[i - 1], "answer"))
    return Plan(beat, reactions, turns)


def interaction(p: Plan, names: dict) -> str:
    """The plan, put to the line writer in a few plain lines: who opens, to whom, and whom each later speaker answers."""
    if len(p.turns) < 2:
        return ""
    S = D()["say"]
    out = []
    for i, t in enumerate(p.turns):
        a = names[t.speaker_id]
        if i == 0 and t.purpose == "join":
            out.append(S["join"].format(a=a, b=names.get(t.target, t.target)) + ".")
        elif i == 0:
            head = S["first_player" if t.target == "player" else "first_party"].format(a=a)
            out.append(head + (f", {S[t.purpose]}" if t.purpose in ("approve", "disapprove") else "") + ".")
        else:
            out.append(S[t.purpose].format(a=a, b=names.get(t.target, t.target)) + ".")
    return " ".join(out)


def spoke(p: Plan, members: dict, now: int) -> None:
    """After an exchange: who spoke, and who opened, for the next one's 'spoke last time'."""
    for i, mid in enumerate(p.speaker_ids):
        m = members.get(mid)
        if m is not None:
            m["banter_at"] = now
            if i == 0:
                m["started_at"] = now


def explain(p: Plan, names: dict) -> list[str]:
    """Why each spoke or did not, for the live check (never shown to a player)."""
    extra = [x for x in ((p.beat.weight if p.beat.weight != "light" else ""), ("about " + ", ".join(names.get(i, i) for i in p.beat.named) if p.beat.named else ""),
                         ("the whole party" if p.beat.party else "")) if x]
    out = [f"director: {p.beat.kind}{' (' + '; '.join(extra) + ')' if extra else ''} - {p.beat.text[:90]}"]
    chosen = p.speaker_ids
    for r in sorted(p.reactions, key=lambda r: -r.score):
        why = ", ".join(f"{'+' if pts >= 0 else ''}{pts} {w}" for pts, w in r.reasons) or "nothing in particular"
        role = ""
        if r.member_id in chosen:
            t = p.turns[chosen.index(r.member_id)]
            role = f"SPEAKS #{chosen.index(r.member_id) + 1} -> {names.get(t.target, t.target)} [{t.purpose}]"
        close = f"  [own life {r.close['mine']:.2f} vs others' {r.close['theirs']:.2f}]" if r.close else ""
        out.append(f"  {names.get(r.member_id, r.member_id)}: {round(r.score)} ({why}) {role or 'silent'}{close}")
    return out
