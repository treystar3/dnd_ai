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
    around: tuple = ((), ())                     # the town's pieces for this reply (pieces): those asked for, those that may bear on it
    move: str = ""
    candidates: list = field(default_factory=list)

    def line(self) -> str:
        would = [c.id for c in self.candidates if c.share]
        held = [f"{c.id} ({c.why})" for c in self.candidates if not c.share]
        return (f"move {self.move}{' (the game decided)' if self.forced else ''}, stance {self.stance}; could share: {', '.join(would) or 'nothing'}"
                + (f"; would not: {', '.join(held)}" if held else ""))


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
