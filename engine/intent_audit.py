"""The intent audit gate. The interpreter reads what the player typed into a plan; before the engine acts on it, the plan passes three layers.

1. invariants - cheap, always on, no model: drop duplicates, and mark steps that name someone who isn't here or an ability the player doesn't have.
2. risk flags - decide whether the plan looks risky enough to be worth a second opinion (several steps, an 'other', money words, an invalid step,
   a common verb with no matching step, a purchase the player never mentioned). A calm plan skips the audit and costs nothing.
3. the audit - two independent readings compared. The model first says in one sentence what the player wants (seeing only their words and the
   scene, not the plan), then is asked whether that matches a plain-English description of the plan. If not it proposes a new plan,
   which goes back through the invariants. If the proposal is still invalid, the player is asked to put it another way.

The model never decides facts (who is here, what exists); the engine does. This module has no model code: the three model calls are handed in."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from engine.actions import TARGETED                  # the kinds aimed at someone who must be here: declared with the action (engine/actions.py)
from engine.actions import VERB_KINDS as _TABLE_VERBS
MONEY = re.compile(r"\b(gold|silver|copper|coins?|fee|pay|paid|price|cost|costs|owe|bribe|tip)\b|\d+\s*(g|s|c)\b")

# the verbs each kind of action declares (engine/actions.py): a verb in the text should show up as one of its kinds in the plan
VERB_KINDS: dict[str, tuple[str, ...]] = dict(_TABLE_VERBS)
VERB_KINDS["board"] = VERB_KINDS.get("board", ()) + ("move",)            # "board the ferry" is a move
# thefts and acts of force the plan might not show (words come from data/rules/law.yaml)
from engine import law as _law
for _w in _law.L["words"]["steal"]:
    VERB_KINDS.setdefault(_w, ("steal",))
for _w in _law.L["words"]["unlock"]:
    VERB_KINDS.setdefault(_w, ("unlock", "steal"))
FORCE_WORDS = set(_law.L["words"]["force"])


@dataclass
class Situation:
    """What the engine knows is true right now. Only facts, nothing the model said."""
    present: dict[str, str] = field(default_factory=dict)     # id -> label of people here
    abilities: dict[str, str] = field(default_factory=dict)   # id -> name of usable abilities
    place: str = ""
    partner: str = ""
    wildlife: bool = False
    workers: set[str] = field(default_factory=set)            # ids of people here with a work offer standing
    lines: list[str] = field(default_factory=list)            # plain scene facts shown to the model
    people_at: object = None                                  # (f384) place -> the ids, names and roles of who is found there, or None

    def knows_target(self, target: str) -> bool:
        t = target.strip().lower()
        return not t or t in self.present or (t == "wildlife" and self.wildlife)

    def found_at(self, place: str, target: str) -> bool:
        """(f384) Is the one a step is aimed at found where an earlier step of the plan takes the player?"""
        return bool(self.people_at and place and target) and target.strip().lower() in self.people_at(place)


class AuditAsk(Protocol):
    def meaning(self, text: str, sit: Situation) -> str: ...
    def compare(self, text: str, meaning: str, described: str, risk: list[str]) -> tuple[bool, str]: ...
    def propose(self, text: str, hint: str) -> list: ...


@dataclass
class Result:
    status: str                       # skipped | unchanged | changed | failed | unsure (f332: flagged, and the audit could not be made)
    plan: list
    reason: str = ""
    risk: list[str] = field(default_factory=list)
    meaning: str = ""
    described: str = ""
    verdict: str = ""
    calls: int = 0


def _key(step) -> tuple:
    """What makes two steps the same step. (f420) An improvised act is nothing but its summary, so for 'other' the summary counts:
    without it, the audit's own corrected reading ("attempts to grow wings and fly away") compared equal to the joke it replaced and
    was thrown away, and two improvised acts in one line were merged into one."""
    d = step.model_dump(exclude={"summary", "mark", "checks"})
    if step.kind == "other":
        d["summary"] = " ".join(re.sub(r"[^a-z0-9' ]+", " ", (step.summary or "").lower()).split())
    return tuple(sorted((k, str(v)) for k, v in d.items()))


def problems(plan: list, sit: Situation) -> list[str]:
    """Things that cannot be true in the scene as it is, one line each."""
    out = []
    there = ""                                                # (f384) where an earlier step walks to: "go to the hall and hand it to the clerk"
    for i, s in enumerate(plan, 1):
        if s.kind == "move" and getattr(s, "destination", ""):
            there = s.destination
        if s.kind in TARGETED and s.target and not sit.knows_target(s.target) and not sit.found_at(there, s.target):
            out.append(f"step {i} ({s.kind}) is aimed at '{s.target}', who is not here")
        if s.kind == "ability" and s.ability and sit.abilities and s.ability.strip().lower() not in sit.abilities:
            out.append(f"step {i} uses ability '{s.ability}', which the player does not have")
    return out


def fix(plan: list) -> list:
    """Drop exact repeats, an 'other' that only restates another step, and a later step with nothing of its own (no target, item,
    ware, words...) whose summary is an earlier step's summary word for word ("I put 2 silver in the tithe box" as a give and again
    as a pray)."""
    seen, out = set(), []
    for s in plan:
        k = _key(s)
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    said = {re.sub(r"\W+", " ", s.summary.lower()).strip() for s in out if s.kind != "other" and s.summary.strip()}
    kept = [s for s in out if not (s.kind == "other" and re.sub(r"\W+", " ", s.summary.lower()).strip() in said)]
    bare = lambda s: not any(getattr(s, f, "") for f in ("destination", "target", "speech", "seek", "ware", "ability", "item"))
    told, final = set(), []
    for s in kept:
        summary = re.sub(r"\W+", " ", s.summary.lower()).strip()
        if summary and summary in told and bare(s):
            continue
        told.add(summary)
        final.append(s)
    return final or kept or out


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 3}


def _mentions(text: str, *names: str) -> bool:
    """Does the text mention any word of these names (by its first four letters, so 'rations' meets 'ration')?"""
    stems = {w[:4] for n in names for w in re.findall(r"[a-z]+", n.lower().replace("_", " ")) if len(w) >= 3}
    return bool(stems) and any(w[:4] in stems for w in _words(text))


def party_proposal(plan: list) -> bool:
    """(f420) "Gallen, let's head for the guild hall" read as a word to the companion and the walk it names is one thing said and done,
    not two intents to check: the audit flagged it, asked again, and the walk was lost."""
    from engine import actions
    if len(plan) != 2:
        return False
    talk = next((a for a in plan if a.kind == "talk" and str(a.target).startswith("hire:")), None)
    deed = next((a for a in plan if a.kind in ("move", "search", "explore")), None)
    if talk is None or deed is None:
        return False
    words = actions.BY_KIND[deed.kind].verbs + actions.BY_KIND[deed.kind].words + ("let's", "lets", "head", "make our way", "look for", "hunt")
    low = (talk.speech or "").lower()
    return any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in words)


def risk_flags(text: str, plan: list, sit: Situation) -> list[str]:
    flags = []
    low = text.lower()
    kinds = {s.kind for s in plan}
    if len(plan) >= 2 and not party_proposal(plan):
        flags.append("multi_intent")
    if "other" in kinds:
        flags.append("other_intent")
    if MONEY.search(low) and kinds & {"buy", "sell", "give", "talk", "other", "work", "commission"}:
        flags.append("money_context")
    if problems(plan, sit):
        flags.append("invalid_step")
    if "work" in kinds and not sit.workers and MONEY.search(low):
        flags.append("work_without_offer")
    words = _words(low)
    if words & FORCE_WORDS and not any(getattr(s, "force", False) for s in plan) and "attack" not in kinds:
        flags.append("unmarked_force")
    for verb, ok in VERB_KINDS.items():
        if verb in words and not kinds & set(ok):
            flags.append(f"unmatched_verb:{verb}")
            break
    for s in plan:
        if s.kind == "buy" and (s.ware or s.item) and not _mentions(f"{text} {s.summary}", s.ware, s.item) \
                and not words & {"sleep", "room", "eat", "meal", "drink", "food", "bed", "stay", "night", "lodging"}:
            flags.append("unmentioned_buy")
            break
    return flags


def describe(plan: list, sit: Situation) -> str:
    """The plan as plain English, so a model can compare it with what the player meant."""
    parts = []
    for i, s in enumerate(plan, 1):
        who = sit.present.get(s.target, s.target)
        bits = [s.kind.replace("_", " ")]
        if who:
            bits.append(f"aimed at {who}")
        for label, v in (("item", s.item), ("ware", s.ware), ("ability", s.ability), ("destination", s.destination)):
            if v:
                bits.append(f"{label} '{v}'")
        if getattr(s, "force", False):
            bits.append("using physical force")
        if s.speech:
            bits.append(f'saying "{s.speech[:80]}"')
        if s.summary:
            bits.append(f"({s.summary[:80]})")
        parts.append(f"{i}. " + " ".join(bits))
    return "\n".join(parts)


def audit(text: str, plan: list, sit: Situation, ask: AuditAsk) -> Result:
    plan = fix(plan)
    risk = risk_flags(text, plan, sit)
    if not risk:
        return Result("skipped", plan)
    res = Result("unchanged", plan, risk=risk)
    bad = problems(plan, sit)
    described = describe(plan, sit)
    res.described = described
    hint, why = "", ""
    try:
        if not bad:
            res.meaning = ask.meaning(text, sit)
            ok, why = ask.compare(text, res.meaning, described, risk)
            res.calls += 2
            res.verdict = why
            if ok:
                return res
            hint = (f"A second reading of the player's words was: {res.meaning} "
                    f"The first plan was:\n{described}\nIt did not match because: {why}")
        else:
            hint = "The first plan cannot happen: " + "; ".join(bad) + "."
        for attempt in range(2):
            proposal = fix(ask.propose(text, hint))
            res.calls += 1
            still = problems(proposal, sit)
            if not still and len(proposal) > len(plan):
                still = ["the new plan has more steps than the first; only remove or correct steps, never add"]
            if not still:
                if [_key(s) for s in proposal] == [_key(s) for s in plan]:
                    return res
                if not why.strip() and not bad:
                    res.verdict = "audit change with no reason ignored"
                    return res
                res.status, res.plan = "changed", proposal
                return res
            hint += " Your last try also failed: " + "; ".join(still) + "."
        res.reason = "; ".join(still)
    except Exception as e:                      # the model is down or rambling
        res.reason = f"{type(e).__name__}: {e}"
        if not bad:                             # (f332) a flagged plan nobody could check does not run on a shrug: the world asks instead
            res.status, res.verdict = "unsure", "audit unavailable"
            return res
    res.status = "failed"
    return res
