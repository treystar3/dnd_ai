"""How long the narrator and the people of the world should speak. The engine decides; the model fills the space."""

from pathlib import Path

import yaml

V = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "voice.yaml").read_text(encoding="utf-8"))


def narration(weight: str | None) -> dict:
    return V["narration"].get(weight or "normal", V["narration"]["normal"])


def npc_level(npc, player_text: str, convo: list, extra: list, first: bool) -> str:
    """short / medium / long, from what the moment asks for."""
    P = V["points"]
    low = player_text.lower()
    score = 0
    score += len(player_text.split()) >= P["long_player_message_words"]
    score += any(w in low for w in P["open_question"])
    score += min(2, sum(w in low for w in P["weighty"]))
    score += first
    score += npc.trust >= P["trust"]
    score += len(convo) >= P["long_conversation_turns"] * 2
    score += bool(extra) and any("quest" in str(e).lower() or "work" in str(e).lower() for e in extra)
    quiet = any(t in V["quiet_traits"] for t in getattr(npc, "traits", []))
    level = "short" if score == 0 else "medium" if score <= 2 else "long"
    if quiet and level == "long":
        level = "medium"
    return level


def npc(level: str) -> dict:
    return V["npc"][level]
