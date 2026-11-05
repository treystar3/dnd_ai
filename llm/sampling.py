"""(f515) The sampling a call is made with, worked out once, in one place.

BASE is the table every night ran on (the owner's reading of "keep them as they are", Bundle F's survey answers, GOALS.md): what
Ollama sent for every request of the post-E night, measured from its own log. It is laid under a task's own values only when a
request is built for llama-server (f521); the Ollama-shaped source sends exactly today's options and never these keys (f527 moves the
table into data/ with the one re-bless).

resolve(task, temperature) gives a Plan: the task's tuned values from config.SAMPLING with config.TEMP_ADD and REPEAT_ADD applied
(shifted), its base temperature and the ceiling a retry may warm it to. Plan.at(attempt) is one try's Sampling. The order is today's
(llm/gateway.py before f515): the tuned values are read, the ceiling chosen by whether the task is tuned at all, and only then shifted,
so REPEAT_ADD reaches only a task that sets its own repeat penalty and an untuned task's ceiling stays 1.2."""

from dataclasses import dataclass, field

import config

BASE = {"top_k": 64, "top_p": 0.95, "min_p": 0.0, "typical_p": 1.0, "repeat_penalty": 1.0, "repeat_last_n": 64,
        "presence_penalty": 0.0, "frequency_penalty": 0.0, "dry_multiplier": 0.0, "xtc_probability": 0.0}
RETRY_TEMPERATURE_STEP = 0.15


def shifted(task: str, base: float, top: float, tuned: dict) -> tuple[float, float, dict]:
    """(f387) config.TEMP_ADD and REPEAT_ADD applied: warm calls warmer (their retry ceiling with them), set penalties firmer. The cold
    calls and the night bot's own lines are untouched."""
    add, rep = float(getattr(config, "TEMP_ADD", 0) or 0), float(getattr(config, "REPEAT_ADD", 0) or 0)
    if task in getattr(config, "BOT_TASKS", ()):
        return base, top, tuned
    if add and base >= getattr(config, "WARM_FROM", 0.5):
        base, top = min(1.5, base + add), min(1.5, top + add)
    if rep and "repeat_penalty" in tuned:
        tuned = dict(tuned, repeat_penalty=round(tuned["repeat_penalty"] + rep, 3))
    return base, top, tuned


@dataclass(frozen=True)
class Sampling:
    """One try's sampling: its temperature and the task's own explicit values (exactly today's options, apart from the machine's)."""
    temperature: float
    explicit: dict = field(default_factory=dict)

    def resolved(self) -> dict:
        """Every sampler value, BASE under the task's own: what llama-server is sent (f521), so none of its own defaults apply."""
        return {**BASE, **self.explicit, "temperature": self.temperature}


@dataclass(frozen=True)
class Plan:
    task: str
    base: float
    ceiling: float
    explicit: dict = field(default_factory=dict)

    def at(self, attempt: int) -> Sampling:
        return Sampling(temperature=min(self.ceiling, self.base + RETRY_TEMPERATURE_STEP * attempt), explicit=dict(self.explicit))


def resolve(task: str, temperature: float) -> Plan:
    table = getattr(config, "SAMPLING", {})
    tuned = dict(table.get(task, {}))
    base = tuned.pop("temperature", temperature)
    top = min(1.2, base + 0.1) if task in table else 1.2      # a retry warms a tuned task only a little
    base, top, tuned = shifted(task, base, top, tuned)
    return Plan(task=task, base=base, ceiling=top, explicit=tuned)
