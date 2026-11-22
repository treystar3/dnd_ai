"""(f793) B3: prose as plain text (data/rules/prose.yaml; docs/design/36_b3_plain_prose.md). Which task is answered as plain text,
the prompt's JSON sentence swapped for the passage's, the shape a plain answer must have, and the words a retry asks with. Pure: the
gateway asks, llm/llama.py builds the request, and the answer is wrapped into its contract (wrap) so every check reads it as before."""
from __future__ import annotations

import re
from pathlib import Path

from core import yamlio

RULES = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "prose.yaml").read_text(encoding="utf-8"))


def field_of(schema) -> str:
    """The one prose field a contract names (its PLAIN), '' when it names none."""
    return str(getattr(schema, "PLAIN", "") or "")


def field_for(task: str, schema) -> str:
    """The field a plain answer to this task fills, '' when the task is answered as JSON: it is switched on, may be plain with this
    very contract, and the contract names its field."""
    if task not in (RULES.get("plain_text") or ()):
        return ""
    if (RULES.get("can_be_plain") or {}).get(task) != getattr(schema, "__name__", ""):
        return ""
    return field_of(schema)


def system_for(system: str) -> str:
    """The prompt as a plain request sends it: its sentence asking for JSON swapped for the passage's."""
    for line in RULES.get("json_lines") or ():
        if line in system:
            return system.replace(line, RULES["plain_line"])
    return system


def shape_problem(text: str) -> str:
    """Why a plain answer is not a passage as the player will read it, '' when it is."""
    for s in RULES.get("shapes") or ():
        if re.search(s["pattern"], text or "", re.I | re.M):
            return s["reason"]
    return ""


def wrap(schema, field: str, text: str, context=None):
    """The plain answer as its contract, so every check that walks an answer's fields reads it (the contract's own validators too)."""
    return schema.model_validate({field: text.strip()}, context=context)


class Shape(ValueError):
    """A plain answer that is not a passage: its reason goes back to the model as a check's does."""


AGAIN = "Fix this and write the passage again."
CUT = "Write the passage again, complete."
