"""(f468) The turn budget: the owner's decision that the longest turn finishes within 60 seconds of model time on the RTX 3060 12 GB
(GOALS.md, f459), kept by arithmetic, not by a clock. The suite has no clock and a replay must make the same choices as the recording,
so every call is priced from text alone: the prompt's characters and the answer's (or the task's expected size, data/rules/budget.yaml
tasks) over the card's measured speeds (data/measured/card_profile.yaml, or the speeds a recording's meta carries, tools/rerun.py).

One Budget is open per input (scenes/world.py new_input opens it, the executor closes it when the line is done): llm/gateway.py asks
allow() before a call's first attempt and charge()s after every attempt (a retry costs what it costs, decision 9). A required task
(the understanding, the outcome, the passage) is refused only when what is left is under the floor (BudgetSpent: the line is not taken,
or its passage is told by a stand-in); an optional task that does not fit after the reserve kept for the required calls still ahead is
deferred (Deferred, a later turn's: f469) or dropped (Dropped: the site's fallback stands now), as the table says. deadline() is what a
required call still running may take: the remainder, never under the floor; the gateway sets it on the client's own timeout.
Calls from other threads (the backfill's) are neither charged nor refused. The session owns CURRENT and LAST (engine/session.py).

This module imports no clock (an AST fence in tools/sim/budget_468_test.py keeps it so): a second here is an estimate, the same in every
process."""
from __future__ import annotations

import threading
from pathlib import Path

import yaml
from llm.errors import LLMError                     # (f514) from the module that imports no model client

ROOT = Path(__file__).resolve().parent.parent
B: dict = yaml.safe_load((ROOT / "data" / "rules" / "budget.yaml").read_text(encoding="utf-8"))
TASKS: dict = B.get("tasks") or {}
DEFAULT_PROFILE = {"read_tps": 756.8, "write_tps": 31.7}      # the f443 measurement, when no profile file is there


def load_profile() -> dict:
    """The card's speeds, from data/measured/card_profile.yaml (tools/card_profile.py --write): prompt and answer tokens a second."""
    p = ROOT / "data" / "measured" / "card_profile.yaml"
    try:
        m = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except OSError:
        m = {}
    read, write = m.get("prompt_tokens_per_second"), m.get("answer_tokens_per_second")
    return {"read_tps": float(read) if read else DEFAULT_PROFILE["read_tps"], "write_tps": float(write) if write else DEFAULT_PROFILE["write_tps"]}


PROFILE: dict = load_profile()


def need(task: str) -> str:
    """required | optional | tool, from the table; a task the table does not know is treated as required (the startup check keeps the
    table whole, engine/data_check.py)."""
    return (TASKS.get(task) or {}).get("need", "required")


def later(task: str) -> str:
    return (TASKS.get(task) or {}).get("later", "dropped")


def estimate(task: str, prompt_chars: int, answer_chars: int | None = None) -> float:
    """Seconds the call takes on the card, from text: the prompt read at the card's reading speed, the answer (its characters when it is
    known, else the task's expected size) written at its writing speed; chars_per_token is the one calibration."""
    cpt = float(B.get("chars_per_token") or 4.0)
    tokens_in = max(0, prompt_chars) / cpt
    tokens_out = (max(0, answer_chars) / cpt) if answer_chars is not None else float((TASKS.get(task) or {}).get("answer_tokens") or 200)
    return tokens_in / PROFILE["read_tps"] + tokens_out / PROFILE["write_tps"]


class BudgetError(LLMError):
    """A call the budget did not allow: a kind of LLMError, so every site's own fallback stands, but one the gateway files no refusal
    for and counts as no failure of the model's (generate())."""
    budget = True

    def __init__(self, task: str, why: str):
        super().__init__(f"{task}: {why}")
        self.task = task


class BudgetSpent(BudgetError):
    """A required call with less than the floor left: the line is not taken, or its passage is told by a stand-in."""


class Deferred(BudgetError):
    """An optional call that does not fit now and is a later turn's (f469 queues it; until then its site's fallback stands)."""


class Dropped(BudgetError):
    """An optional call that does not fit now and is not kept: its site's fallback stands."""


class Budget:
    def __init__(self, limit: float | None = None, margin: float | None = None, floor: float | None = None, reserve: float | None = None):
        self.limit = float(B["limit_seconds"] if limit is None else limit)
        self.margin = float(B["margin_seconds"] if margin is None else margin)
        self.floor = float(B["floor_seconds"] if floor is None else floor)
        self.reserve = float(B["reserve_seconds"] if reserve is None else reserve)
        self.spent = 0.0                       # estimated seconds charged so far, every attempt counted
        self.required_seconds = 0.0            # ...of which the required path's (the understanding, the outcome, its passage, their embeds)
        self.owner = threading.get_ident()     # the turn's thread: another thread's calls are not this budget's
        self.passage_ahead = True              # the reserve is kept while a required passage is still to come (scenes/world.py passage_shown)
        self.charges: list[tuple[str, float]] = []
        self.deferred: list[str] = []
        self.dropped: list[str] = []
        self.refused: list[str] = []

    def mine(self) -> bool:
        return threading.get_ident() == self.owner

    def remaining(self) -> float:
        return self.limit - self.margin - self.spent

    def allow(self, task: str, prompt_chars: int) -> None:
        """Before a call's first attempt. Raises BudgetSpent, Deferred or Dropped; returns for a call that may be made."""
        if not self.mine():
            return
        kind = need(task)
        if kind == "tool":
            return
        left = self.remaining()
        if kind == "required":
            if left < self.floor:
                self.refused.append(task)
                raise BudgetSpent(task, f"the turn's budget is spent ({left:.0f} s left, the floor is {self.floor:.0f} s)")
            return
        keep = self.reserve if self.passage_ahead else 0.0
        cost = estimate(task, prompt_chars)
        if cost > left - keep:
            if later(task) == "deferred":
                self.deferred.append(task)
                raise Deferred(task, f"deferred to a later turn ({cost:.0f} s wanted, {left:.0f} s left with {keep:.0f} s kept back)")
            self.dropped.append(task)
            raise Dropped(task, f"dropped this turn ({cost:.0f} s wanted, {left:.0f} s left with {keep:.0f} s kept back)")

    def charge(self, task: str, prompt_chars: int, answer_chars: int | None = None) -> float:
        """After every attempt, what it cost: the prompt as read, the answer as written (or the task's expected size when there was
        none). Returns the seconds charged."""
        if not self.mine() or need(task) == "tool":
            return 0.0
        cost = estimate(task, prompt_chars, answer_chars)
        self.spent += cost
        if need(task) == "required":
            self.required_seconds += cost
        self.charges.append((task, cost))
        return cost

    def embed(self, texts: int) -> float:
        """One embedding call: its texts at the card's seconds a text; part of the required path (the checks the outcome needs)."""
        if not self.mine() or texts <= 0:
            return 0.0
        cost = texts * float(B.get("embed_seconds_per_text") or 0.0)
        self.spent += cost
        self.required_seconds += cost
        self.charges.append(("embed", cost))
        return cost

    def deadline(self) -> float:
        """What a required call still running may take: the remainder, never under the floor."""
        return max(self.floor, self.remaining())

    def summary(self) -> dict:
        return {"estimated": int(round(self.spent)), "required": round(self.required_seconds, 1), "deferred": list(self.deferred),
                "dropped": list(self.dropped), "refused": list(self.refused), "calls": len(self.charges)}


CURRENT: Budget | None = None
LAST: dict = {}                    # the last closed budget's summary, with the stand-ins the line showed (the turn log and the night tool read it)


def open(**kw) -> Budget:
    global CURRENT
    CURRENT = Budget(**kw)
    return CURRENT


def close(stand_ins: list | None = None) -> dict:
    """The input is done: its budget closes and its summary is kept as LAST."""
    global CURRENT
    b, CURRENT = CURRENT, None
    LAST.clear()
    if b is not None:
        LAST.update(b.summary(), stand_ins=list(stand_ins or []))
    return dict(LAST)


def reset() -> None:
    """(engine/session.py) A campaign opened or closed: no budget stays open, nothing of the last is kept."""
    global CURRENT
    CURRENT = None
    LAST.clear()


def allow(task: str, prompt_chars: int) -> None:
    if CURRENT is not None:
        CURRENT.allow(task, prompt_chars)


def charge(task: str, prompt_chars: int, answer_chars: int | None = None) -> float:
    return CURRENT.charge(task, prompt_chars, answer_chars) if CURRENT is not None else 0.0


def embed(texts: int) -> float:
    return CURRENT.embed(texts) if CURRENT is not None else 0.0


def deadline() -> float | None:
    """The open budget's deadline for the calling thread's call; None with no budget open, or from another thread."""
    return CURRENT.deadline() if CURRENT is not None and CURRENT.mine() else None


def passage_shown() -> None:
    """The line's required passage has been shown (or stood in for): the reserve is no longer kept from the optional calls after it."""
    if CURRENT is not None:
        CURRENT.passage_ahead = False
