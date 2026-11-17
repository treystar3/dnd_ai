"""(f724) The decision for a reply: what the engine settles before a townsperson is asked to speak (data/rules/reply.yaml;
docs/design/28_phase4_plan.md, Part A). How they are for this talk, the move they make, and what they could share with the one
in front of them and whether they would. Pure: nothing here writes or asks the model; the scene keeps the moves of the talk
under way (scenes/world.py), and a decision is made again for every reply."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core import yamlio

R = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "reply.yaml").read_text(encoding="utf-8"))
KINDS = ("lore", "clue", "news", "happening", "board", "secret")
FACETS = {"news": "news", "happenings": "happening", "board": "board"}      # the truth view's facet -> the kind of thing it holds
NEEDS = ("concern",)
DECIDED = "[THE GAME HAS DECIDED"                                           # how a line that says what they must say begins (npc/prompts.py)


def on() -> bool:
    """The switch (reply.yaml decide_then_speak): off, people speak as they did and nothing here is rolled or kept."""
    return bool(R.get("decide_then_speak"))


@dataclass(frozen=True)
class Candidate:
    """One thing they could say in this reply, and whether they would say it to this character."""
    id: str
    kind: str
    text: str
    share: bool
    why: str = ""                                # why not, when they would not


@dataclass
class Decision:
    speaker: str
    to: str                                      # the character spoken to (checklist 8: theirs, by id)
    stance: str = "none"                         # voice.yaml stances, by its key
    last: tuple = ()                             # the moves of this talk's last replies, oldest first
    forced: bool = False                         # the game has decided something they must say in this reply
    note: str = ""                               # (f726) the rule for the journal note, when one is due: the reading writes it
    around: tuple = ((), ())                     # the town's pieces for this reply (pieces): those asked for, those that may bear on it
    move: str = ""
    candidates: list = field(default_factory=list)
    given: tuple = ()                            # (f725) the game's lines for this reply that bear on what they do
    read: str = ""                               # who read the line: "model", or "engine" when the model's reading failed
    intent: str = ""                             # what the reading settled: what they do with the reply,
    shares: tuple = ()                           # ...which of the candidates they tell, by id,
    told_own_name: bool = False                  # ...whether they give their name,
    answer: object = None                        # ...and what it means for the one spoken to (llm/contracts.py NPCAnswer)
    dropped: tuple = ()                          # what the engine took out of the reading, and why

    def line(self) -> str:
        would = [c.id for c in self.candidates if c.share]
        held = [f"{c.id} ({c.why})" for c in self.candidates if not c.share]
        return (f"move {self.move}{' (the game decided)' if self.forced else ''}, stance {self.stance}; could share: {', '.join(would) or 'nothing'}"
                + (f"; would not: {', '.join(held)}" if held else "")
                + (f"; read by the {self.read}: intent {self.intent}, tells {', '.join(self.shares) or 'nothing'}" if self.read else "")
                + (f"; taken out: {'; '.join(self.dropped)}" if self.dropped else ""))


def must_say(lines) -> bool:
    """Whether the game has decided something they must say in this reply: one of the lines they are given says so, in the
    game's own words (a check's result, work handed in, a secret's gate opened or shaken)."""
    return any(DECIDED in (l or "") for l in lines)


def kind_of(fact) -> str:
    """What kind of thing a fact is, by its id: a clue of a matter, a piece of the town's (truth.py gives those their ids), else lore."""
    head = str(getattr(fact, "id", "")).split(":")[0]
    return head if head in ("clue", "news", "happening", "board") else "lore"


def pieces(view, line: str) -> tuple[list, list]:
    """The town's news, its happenings and the board's postings as this viewer has them for this reply (engine/truth.py: each with
    an id; the ordinary day, 'nothing is posted' and what the player holds are no pieces): (whole, maybe). whole: those whose facet
    the line asks for (engine/brief.py asked; the board is in the view only then). maybe: the rest, which come in only if they bear
    on the line (brief.lore)."""
    from engine import brief
    whole, maybe = [], []
    for facet, kind in FACETS.items():
        if facet not in view.facets():
            continue
        found = [f for f in view.scene.facts(facet) if str(f.id).startswith(kind + ":") and view.viewer.sees(f)]
        (whole if facet == "board" or brief.asked("news", line) else maybe).extend(found)
    return whole, maybe


def weights(stance: str, trust: int, kit: dict, has=()) -> dict[str, float]:
    """Each move this person might make, with its weight: the table's, times what their stance, their trust in this character and
    the habits of their voice make of it. A move that needs what they lack, or comes to nothing, is not theirs."""
    M = R["moves"]
    T = M.get("by_trust") or {}
    band = "low" if trust < int((T.get("low") or {}).get("below", 0)) else "high" if trust >= int((T.get("high") or {}).get("from", 101)) else ""
    out = {}
    for move, spec in M["kinds"].items():
        if spec.get("needs") and spec["needs"] not in has:
            continue
        w = float(spec["weight"]) * float(((M.get("by_stance") or {}).get(stance) or {}).get(move, 1)) * float((T.get(band) or {}).get(move, 1))
        for axis, options in (M.get("by_kit") or {}).items():
            w *= float(((options or {}).get((kit or {}).get(axis, "")) or {}).get(move, 1))
        if w > 0:
            out[move] = w
    return out


def roll_move(w: dict[str, float], last, rng, forced: bool = False) -> str:
    """This reply's move, on its own die: never the one made `running` times running already, unless it is the only one they
    have; the forced move when the game has decided what must be said."""
    M = R["moves"]
    if forced or not w:
        return M["forced"]
    n = int(M["running"])
    run = list(last)[-n:]
    opts = dict(w)
    if len(run) == n and len(set(run)) == 1 and len(opts) > 1:
        opts.pop(run[0], None)
    return rng.choices(list(opts), weights=list(opts.values()))[0]


def would_share(kind: str, trust: int, gate: bool | None = None) -> tuple[bool, str]:
    """Whether they would tell this character a thing of this kind, and why not (reply.yaml share)."""
    spec = R["share"][kind]
    if spec.get("gate"):
        return bool(gate), "" if gate else "its gate is shut"
    need = spec.get("trust", 0)
    if need == "refusal":
        from engine import voice_rules
        need = int(voice_rules.V["exemplars"]["refusal_trust"])
    return trust >= need, "" if trust >= need else f"trust {trust}, under {need}"


def secret(pending: dict | None, text: str = "") -> list[Candidate]:
    """The secret they hold (scenes/arc_actions.py secret_lines), as a thing they could say: theirs to tell only while its gate is
    open, and while it is shut nothing of it is written down (the owner, f486)."""
    if not pending:
        return []
    ok, why = would_share("secret", 0, gate=bool(pending.get("open")))
    return [Candidate(f"secret:{pending['secret']['kind']}", "secret", text if ok else "", ok, why)]


def settle(decision: Decision, npc, picked, rng) -> Decision:
    """The decision made whole, once the person's voice is theirs and the lore for the line is picked: the move, and each thing
    picked as a candidate with whether they would share it."""
    from engine import regard, voices
    trust = regard.of(npc, decision.to).trust
    has = {"concern"} if getattr(npc, "concern", "") else set()
    decision.move = roll_move(weights(decision.stance, trust, voices.kit_of(npc.speech), has), decision.last, rng, decision.forced)
    found = []
    for f in picked:
        kind = kind_of(f)
        ok, why = would_share(kind, trust)
        found.append(Candidate(str(f.id), kind, f.text, ok, why))
    decision.candidates = found + [c for c in decision.candidates if c.kind == "secret"]
    return decision


def offered(decision: Decision) -> list[Candidate]:
    """(f725) What the reading of the line may choose from: the candidates they would share."""
    return [c for c in decision.candidates if c.share]


def must(decision: Decision) -> list[str]:
    """(f725) What the game has decided they tell in this reply, whatever is read: a secret whose gate is open."""
    return [c.id for c in offered(decision) if c.kind == "secret"]


def most(move: str) -> int:
    """(f725) How many of the things they could tell this move lets them tell (reply.yaml)."""
    return int(R["moves"]["kinds"][move]["most"])


def says(move: str) -> str:
    """(f725) The move in plain words, as the model is told it."""
    return str(R["moves"]["kinds"][move]["says"])


def gift(gives, intent: str, story):
    """(f725) The gift, if it stands: a named story object (story: the scene's rule of what one is), and not one they are
    bargaining over. Else None. The one rule, for a reply's gift and a reading's."""
    if gives is None or story is None or not (gives.name or "").strip() or intent == "bargain" or not story(gives.name):
        return None
    return gives


def take(decision: Decision, got, who: str, story=None, fair=None) -> Decision:
    """(f725) The model's reading of the line (llm/contracts.py NPCDecision), written into the decision after the engine's checks:
    an id that was not offered is dropped, as is one over what the move lets them tell; what the game decided they tell is told;
    a gift only of a story object; paid work and a request never together; an offer of nothing is none; sharing with nothing
    left to tell is ordinary talk. (f726) One who lies tells none of what is so; what the game decided they tell is told truly;
    paid work is the engine's figures (fair: the scene's rule of an honest offer, None for no real task) before they speak of
    it; a delivery to no one is no request."""
    ids = [c.id for c in offered(decision)]
    forced = must(decision)
    intent = got.intent
    named = list(dict.fromkeys(got.shares))
    free = [i for i in named if i in ids and i not in forced]
    picked = free[: most(decision.move)]
    dropped = [f"{i}: not offered" for i in named if i not in ids] + [f"{i}: more than this move tells" for i in free if i not in picked]
    if intent == "lie" and picked:
        dropped += [f"{i}: a lie tells none of it" for i in picked]
        picked = []
    if forced and intent in ("lie", "withhold", "refuse"):
        dropped.append(f"intent {intent}: the game decided they tell it")
        intent = "share"
    ans = got.answers(who)[0]
    if ans.offers_work is not None:
        task = ans.offers_work.task.strip()
        ans.offers_work = (fair(ans.offers_work) if fair is not None else ans.offers_work) if task else None
        if task and ans.offers_work is None:
            dropped.append(f"the work '{task}': no real task")
    if ans.offers_quest is not None and (not ans.offers_quest.what.strip() or ans.offers_work is not None
                                         or (ans.offers_quest.kind == "deliver" and not ans.offers_quest.to.strip())):
        if ans.offers_work is not None:
            dropped.append("the request: never with paid work")
        elif ans.offers_quest.what.strip():
            dropped.append("the request: a delivery to no one")
        ans.offers_quest = None
    if ans.gives is not None and gift(ans.gives, intent, story) is None:
        dropped.append(f"the gift '{ans.gives.name}': no story object, or offered for sale")
        ans.gives = None
    decision.read, decision.shares = "model", tuple(forced + picked)
    decision.intent = intent if decision.shares or intent != "share" else "small_talk"
    decision.told_own_name, decision.answer, decision.dropped = bool(got.told_own_name), ans, tuple(dropped)
    return decision


def fallback(decision: Decision, answer) -> Decision:
    """(f725) The reading failed: the engine's own candidates are the whole decision. They tell what was picked for the line, in
    its order, as far as the move lets them; the reply comes to the move's intent (ordinary talk when there is nothing to tell);
    nothing is offered, given, learned or promised (answer: the empty block for the one spoken to)."""
    forced = must(decision)
    picked = [c.id for c in offered(decision) if c.id not in forced][: most(decision.move)]
    intent = str(R["moves"]["kinds"][decision.move]["intent"])
    decision.read, decision.shares = "engine", tuple(forced + picked)
    decision.intent = intent if decision.shares or intent != "share" else "small_talk"
    decision.told_own_name, decision.answer, decision.dropped = False, answer, ()
    return decision


def words(decision: Decision) -> list[str]:
    """(f726) The decision in plain words, as the one who speaks is told it (reply.yaml): the move, what the reading settled, and
    what they give: their name, a thing, paid work at the engine's figures, a request."""
    T = R["tells"]
    out = [says(decision.move)]
    if str(R["intents"].get(decision.intent) or "").strip():
        out.append(R["intents"][decision.intent])
    if decision.told_own_name:
        out.append(T["name"])
    a = decision.answer
    if a is not None and a.gives is not None:
        out.append(T["gift"].format(name=a.gives.name.strip(), description=a.gives.description.strip().rstrip(".")))
    if a is not None and a.offers_work is not None:
        out.append(T["work"].format(task=a.offers_work.task.strip(), minutes=a.offers_work.minutes, pay=a.offers_work.pay))
    if a is not None and a.offers_quest is not None:
        q = a.offers_quest
        out.append(T[q.kind].format(what=q.what.strip(), count=q.count, item=q.item.strip() or T["yours"], to=q.to.strip()))
    return out


def told(decision: Decision) -> list[str]:
    """(f726) What they tell in this reply: the decided things in full, in the order decided. No id: an id is the engine's."""
    by = {c.id: c for c in decision.candidates}
    return [" ".join(by[i].text.split()) for i in decision.shares if i in by and by[i].text.strip()]


TELLS = {"name": (), "yours": (), "gift": ("name", "description"), "work": ("task", "minutes", "pay"), "hunt": ("what", "count"), "gather": ("what", "count"),
         "deliver": ("item", "to")}                                          # each telling, and the figures its words must have a place for


def problems(rules: dict | None = None) -> list[str]:
    """Start-up check of data/rules/reply.yaml."""
    from engine import voice_rules, voices
    D = R if rules is None else rules
    bad = []
    if not isinstance(D.get("decide_then_speak"), bool):
        bad.append("reply.yaml decide_then_speak: true or false")
    M = D.get("moves") or {}
    kinds = M.get("kinds") or {}
    if not isinstance(M.get("running"), int) or isinstance(M.get("running"), bool) or M["running"] < 1:
        bad.append("reply.yaml moves.running: a whole number, at least 1")
    if not kinds or not all(isinstance(s, dict) and isinstance(s.get("weight"), (int, float)) and not isinstance(s.get("weight"), bool)
                            and s["weight"] > 0 and s.get("needs", NEEDS[0]) in NEEDS for s in kinds.values()):
        bad.append(f"reply.yaml moves.kinds: each move with a weight above 0, and needs (if any) one of {', '.join(NEEDS)}")
    import typing
    from llm.contracts import NPCDecision                                    # (f725) a move comes to an intent a reply has
    intents = set(typing.get_args(NPCDecision.model_fields["intent"].annotation))
    for move, s in kinds.items():
        if not isinstance(s, dict):
            continue
        if not isinstance(s.get("most"), int) or isinstance(s.get("most"), bool) or s["most"] < 0:
            bad.append(f"reply.yaml moves.kinds.{move}.most: how many things the move tells, a whole number from 0")
        if s.get("intent") not in intents:
            bad.append(f"reply.yaml moves.kinds.{move}.intent: one of a reply's intents ({', '.join(sorted(intents))})")
        if not isinstance(s.get("says"), str) or not s["says"].strip():
            bad.append(f"reply.yaml moves.kinds.{move}.says: the move in plain words")
    G = D.get("decide") or {}
    for k in ("lines", "max_tokens"):
        if not isinstance(G.get(k), int) or isinstance(G.get(k), bool) or G[k] < 1:
            bad.append(f"reply.yaml decide.{k}: a whole number above zero")
    if not isinstance(G.get("memories"), int) or isinstance(G.get("memories"), bool) or G["memories"] < 0:
        bad.append("reply.yaml decide.memories: a whole number from 0")
    said = D.get("intents") or {}                                           # (f726) the decision in plain words
    if set(said) != intents or not all(isinstance(v, str) for v in said.values()):
        bad.append(f"reply.yaml intents: one line of words (or none) for each of a reply's intents ({', '.join(sorted(intents))})")
    K2 = D.get("speak") or {}
    if not isinstance(K2.get("lived"), int) or isinstance(K2.get("lived"), bool) or K2["lived"] < 0:
        bad.append("reply.yaml speak.lived: how many things of their own days the one who speaks is given, a whole number from 0")
    T2 = D.get("tells") or {}
    for k, fields in TELLS.items():
        if not isinstance(T2.get(k), str) or not T2[k].strip() or not all("{" + f + "}" in T2[k] for f in fields):
            bad.append(f"reply.yaml tells.{k}: its words, with a place for each of {', '.join(fields) or 'nothing'}")
    if not isinstance(G.get("temperature"), (int, float)) or isinstance(G.get("temperature"), bool) or not 0 <= G["temperature"] <= 2:
        bad.append("reply.yaml decide.temperature: a number from 0 to 2")
    if not isinstance(M.get("forced"), str) or M["forced"] not in kinds or (kinds.get(M["forced"]) or {}).get("needs"):
        bad.append("reply.yaml moves.forced: one of the moves, and one that needs nothing")

    def table(where: str, t) -> None:
        if not isinstance(t, dict) or not all(m in kinds and isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0 for m, v in t.items()):
            bad.append(f"reply.yaml moves.{where}: each of its moves is one of moves.kinds, times a number from 0 up")

    for stance, t in (M.get("by_stance") or {}).items():
        if stance not in (voice_rules.V.get("stances") or {}):
            bad.append(f"reply.yaml moves.by_stance.{stance}: voice.yaml has no such stance")
        table(f"by_stance.{stance}", t)
    T = M.get("by_trust") or {}
    for band, edge in (("low", "below"), ("high", "from")):
        t = dict(T.get(band) or {})
        if not isinstance(t.pop(edge, None), int):
            bad.append(f"reply.yaml moves.by_trust.{band}.{edge}: a whole number")
        table(f"by_trust.{band}", t)
    if set(T) - {"low", "high"}:
        bad.append("reply.yaml moves.by_trust: low and high")
    for axis, options in (M.get("by_kit") or {}).items():
        if axis not in voices.AXES:
            bad.append(f"reply.yaml moves.by_kit.{axis}: voices.yaml has no such axis")
            continue
        if not isinstance(options, dict) or not options:
            bad.append(f"reply.yaml moves.by_kit.{axis}: its options, each with its moves")
            continue
        for option, t in options.items():
            if option not in voices.AXES[axis]["options"]:
                bad.append(f"reply.yaml moves.by_kit.{axis}.{option}: voices.yaml has no such option")
            table(f"by_kit.{axis}.{option}", t)
    S = D.get("share") or {}
    if set(S) != set(KINDS):
        bad.append(f"reply.yaml share: one row for each of {', '.join(KINDS)}")
    for kind, spec in S.items():
        if not isinstance(spec, dict):
            bad.append(f"reply.yaml share.{kind}: a row (trust: a number or refusal; the secret's is gate: true)")
            continue
        need = spec.get("trust")
        if kind == "secret" or spec.get("gate") is not None:
            if kind != "secret" or spec.get("gate") is not True:
                bad.append(f"reply.yaml share.{kind}: gate: true is the secret's rule, and only the secret's (scenes/arc_actions.py opens it)")
        elif need != "refusal" and (not isinstance(need, int) or isinstance(need, bool) or not 0 <= need <= 100):
            bad.append(f"reply.yaml share.{kind}: trust from 0 to 100, or refusal")
    return bad
