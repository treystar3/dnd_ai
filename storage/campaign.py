"""Campaign persistence. Everything generated during play is written here and becomes canon.

Layout:
    saves/<campaign>/campaign.json     name, seed, current day and turn
    saves/<campaign>/player.json       the player's character and location
    saves/<campaign>/places/<id>.json  which places have been populated, and by whom
    saves/<campaign>/npcs/<id>.json    one file per NPC

The rest of the game only talks to CampaignStore, so this can move to SQLite later
without changes elsewhere.
"""

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from core.models import Item, Character
from npc.models import NPC

SAVES_DIR = Path("saves")


class CampaignMeta(BaseModel):
    name: str
    seed: int
    day: int = 1
    turn: int = 0
    minutes: int = 0
    created: str


class PlaceState(BaseModel):
    id: str
    populated: bool = False
    roster: list[str] = []
    residents: list[str] = []
    first_visit_day: int | None = None
    marks: list[str] = []          # lasting changes the player made here (marked trees, a hidden cache...)
    ground: list[dict] = []        # items left here: {"item": Item data, "minute": when it was left}
    carcasses: list[dict] = []     # fallen creatures not yet skinned: {"creature", "level", "minute"}
    board: list[dict] = []         # guild contracts posted here
    extra_roles: dict[str, int] = {}  # people the world has brought here (arrivals), generated on the next visit
    hidden: list[dict] = []        # story objects the player went looking for here: {"name", "description", "worth", "taken"}
    locks: list[dict] = []         # locked rooms and containers here: {"id", "name", "quality", "owner", "state", "jam", "change_day"}
    bodies: list[dict] = []        # the fallen here, for Speak with a Corpse: {"creature", "name", "level", "category", "minute", "carried", "asked"}
    board_day: int = -1


class PlayerState(BaseModel):
    character: Character
    location: str
    room: str = ""            # place id of a rented room
    room_until: int = -1      # game minute the rental ends
    stash: list[Item] = []    # the item box, reachable from any place with storage
    commissions: list[dict] = []   # gear ordered from crafters: {npc, npc_name, item, ready}
    guild_rank: str = ""           # "" until they join; then F, E, D, C, B, A or S
    guild_done: dict[str, int] = {}  # guild contracts completed, by letter
    quests: list[dict] = []        # contracts and personal requests taken on (see engine/quests.py)
    delve: dict | None = None      # inside a dungeon: {"dungeon", "floor", "chamber", "rest"}
    reputation: dict[str, int] = {}  # how each town regards the player, -100..100
    visited: list[str] = []        # places the player has been
    free_room_day: int = -1        # Sing for Your Supper: a room is owed tonight
    outlaw_rep: int = 0            # how outlaws regard you (-100..100): what you do with those you beat
    prisoners: dict[str, dict] = {}  # captives you hold, by npc id: {"deal", "arc", "node", "tip", "asked"}
    homes: dict[str, dict] = {}    # houses bought, by town id: {"day", "upgrades": [...], "last_garden", "last_hearth"}
    relics_bought: list[str] = []  # named relics already bought (one of each exists)
    party: list[dict] = []         # hired adventurers with you: {"id", "name", "role", "level", "blurb", "arc"} (engine/party.py)
    party_mode: str = "with"       # "with" - they move and fight beside you; "hold" - they wait outside a camp and come when the alarm rings
    party_used: list[str] = []     # roster ids already hired or lost, so they do not reappear
    titles: list[str] = []         # honorifics earned by ending campaigns and cataclysms
    mounts: list[dict] = []        # mounts owned: {"id", "name", "speed", "stamina"} (see data/rules/events.yaml)
    mount: str = ""                # id of the mount ridden, if any
    field: dict = {}               # field-ability state (scenes/field_actions.py): cd, camp, haste, edge, shadow, scouted, lit, shows
    heat: dict[str, dict] = {}     # how wanted you are, by town id: {"heat", "day"} (engine/law.py)
    standing: dict[str, dict] = {}   # how the groups of each town regard you, hidden: town -> group -> [value, day] (engine/standing.py)
    orenna: dict = {}                    # progress of the quest Orenna (engine/orenna.py)
    standing_seen: dict[str, dict] = {}  # deed news already felt in far towns: news id -> town -> {group: change}
    confronted: dict[str, int] = {}  # town id -> the last day guards stopped you there
    road: dict | None = None       # stopped on the road: {"id", "from", "to", "place", "log", "text", "resume"}


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class CampaignStore:
    def __init__(self, root: Path, meta: CampaignMeta):
        self.root = root
        self.meta = meta

    @classmethod
    def open_or_create(cls, name: str, saves_dir: Path = SAVES_DIR) -> "CampaignStore":
        root = saves_dir / name
        meta_path = root / "campaign.json"
        if meta_path.exists():
            meta = CampaignMeta.model_validate_json(meta_path.read_text(encoding="utf-8"))
        else:
            meta = CampaignMeta(
                name=name,
                seed=random.SystemRandom().randrange(2**31),
                created=datetime.now(timezone.utc).isoformat(),
            )
            _write_atomic(meta_path, meta.model_dump_json(indent=2))
        return cls(root, meta)

    def save_meta(self) -> None:
        _write_atomic(self.root / "campaign.json", self.meta.model_dump_json(indent=2))

    def load_world_state(self) -> dict:
        path = self.root / "world_state.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def save_world_state(self, state: dict) -> None:
        _write_atomic(self.root / "world_state.json", json.dumps(state, indent=1))

    def load_dungeons(self) -> list[dict]:
        path = self.root / "dungeons.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    def save_dungeons(self, dungeons: list[dict]) -> None:
        _write_atomic(self.root / "dungeons.json", json.dumps(dungeons, indent=1))

    def load_arcs(self) -> dict:
        path = self.root / "arcs.json"
        base = {"arcs": [], "last_end": -10 ** 9}
        return {**base, **json.loads(path.read_text(encoding="utf-8"))} if path.exists() else base

    def save_arcs(self, data: dict) -> None:
        _write_atomic(self.root / "arcs.json", json.dumps(data, indent=1))

    def load_discoveries(self) -> dict:
        path = self.root / "discoveries.json"
        base = {"places": [], "tracks": [], "leads": []}
        return {**base, **json.loads(path.read_text(encoding="utf-8"))} if path.exists() else base

    def save_discoveries(self, data: dict) -> None:
        _write_atomic(self.root / "discoveries.json", json.dumps(data, indent=1))

    def _npc_path(self, npc_id: str) -> Path:
        return self.root / "npcs" / f"{npc_id}.json"

    def npc_exists(self, npc_id: str) -> bool:
        return self._npc_path(npc_id).exists()

    def load_npc(self, npc_id: str) -> NPC:
        return NPC.model_validate_json(self._npc_path(npc_id).read_text(encoding="utf-8"))

    def save_npc(self, npc: NPC) -> None:
        _write_atomic(self._npc_path(npc.id), npc.model_dump_json(indent=2))

    def list_npcs(self) -> list[str]:
        folder = self.root / "npcs"
        return sorted(p.stem for p in folder.glob("*.json")) if folder.exists() else []

    def npc_names(self) -> list[str]:
        return [self.load_npc(i).name for i in self.list_npcs()]

    def load_place(self, place_id: str) -> PlaceState:
        path = self.root / "places" / f"{place_id}.json"
        if path.exists():
            return PlaceState.model_validate_json(path.read_text(encoding="utf-8"))
        return PlaceState(id=place_id)

    def save_place(self, state: PlaceState) -> None:
        _write_atomic(self.root / "places" / f"{state.id}.json", state.model_dump_json(indent=2))

    def player_exists(self) -> bool:
        return (self.root / "player.json").exists()

    def load_player(self) -> PlayerState:
        return PlayerState.model_validate_json((self.root / "player.json").read_text(encoding="utf-8"))

    def save_player(self, player: PlayerState) -> None:
        _write_atomic(self.root / "player.json", player.model_dump_json(indent=2))
        self.save_meta()            # the clock and turn count live beside the player; saving one without the other lost the time on reload

    def legendary_names(self) -> list[str]:
        path = self.root / "legendaries.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    def add_legendary_name(self, name: str) -> None:
        _write_atomic(self.root / "legendaries.json", json.dumps(self.legendary_names() + [name], indent=2))

    def save_combat(self, combat_json: str | None) -> None:
        path = self.root / "combat.json"
        if combat_json is None:
            path.unlink(missing_ok=True)
        else:
            _write_atomic(path, combat_json)

    def save_story(self, recent: list[str], shown: dict) -> None:
        _write_atomic(self.root / "story.json", json.dumps({"recent": recent, "shown": shown}))

    def load_story(self) -> tuple[list[str], dict]:
        path = self.root / "story.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            recent = [t for t in data.get("recent", []) if isinstance(t, str)]
            shown = data.get("shown", {})
            if isinstance(shown, str):
                shown = {"type": "narration", "text": shown}
            return recent, shown if isinstance(shown, dict) else {}
        except (OSError, ValueError, AttributeError):
            return [], {}

    def load_combat(self) -> str | None:
        path = self.root / "combat.json"
        return path.read_text(encoding="utf-8") if path.exists() else None
