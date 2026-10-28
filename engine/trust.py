"""(f362) Trust that moves: how a conversation changes a townsperson's trust in the player, decided by the engine from what happened.

Why: the model was asked to report a trust change with every reply and, told that ordinary talk is 0, reported 0 every time, so trust
never moved and nobody came to know the player. Now (data/rules/trust.yaml) the first talk of a day counts as getting acquainted, up to
a cap that talk alone cannot pass; how they chose to answer counts; and the model's own say still counts when it says anything.
Deeds move trust through the reactions bus (data/rules/reactions.yaml memory.trust), not here."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
T = yaml.safe_load((ROOT / "data" / "rules" / "trust.yaml").read_text(encoding="utf-8"))


def after_talk(npc, reply, day: int) -> int:
    """Apply this exchange's change to npc.trust and return it (0 when nothing moved). `reply` has intent and trust_change (llm/contracts.py
    NPCReply); `day` is the game day, kept on the record as last_talk_day."""
    K = T.get("talk") or {}
    step = 0
    cap = int(K.get("cap", 60))
    if day != getattr(npc, "last_talk_day", -1):
        if npc.trust < cap:
            step += int(K.get("new_day", 1))
        npc.last_talk_day = day
    step += int((K.get("intents") or {}).get(getattr(reply, "intent", "") or "", 0))
    limit = int(K.get("model_limit", 5))
    step += max(-limit, min(limit, int(getattr(reply, "trust_change", 0) or 0)))
    before = npc.trust
    npc.trust = max(0, min(100, npc.trust + step))
    return npc.trust - before


def problems(intents=()) -> list[str]:
    bad = []
    K = T.get("talk") or {}
    for k in ("new_day", "cap", "model_limit"):
        if not isinstance(K.get(k), int):
            bad.append(f"trust.yaml talk.{k}: needs a whole number")
    for name in (K.get("intents") or {}):
        if intents and name not in intents:
            bad.append(f"trust.yaml talk.intents: '{name}' is not an intent a reply can have")
    return bad
