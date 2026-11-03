"""(f439) Every turn decided by the save, its seed and what was typed.

The rebuild checks each stage by replaying recorded sessions through the real turn (tools/rerun.py), and a turn only replays when
nothing in it is left to chance the save does not decide. Before this, the scene's and the fight's dice were unseeded, a dozen
other places made fresh unseeded generators or rolled the global random module, lessons drew from the machine's own entropy, and
the ids of items, contracts, threads and road stops were uuids that seeded draws of their own. Now each of them is a named stream
here, reseeded at every input from the campaign's seed, its count of inputs (CampaignMeta.steps, saved with the input, so a rolled
back one is taken back with it) and the line typed (begin), so:

- the same save and the same line give the same turn, in any process: a recorded session replays exactly;
- a line tried again after its turn rolled back meets the same dice, which is fair;
- two inputs never share a key, however alike, so ids made from the ids stream never repeat in a save;
- a different campaign seed plays differently: no two runs alike.

Character creation keeps the machine's entropy on purpose (the same idea twice gives different abilities); a recording starts after
it. The streams are objects that live for the whole run, so whatever holds one (the scene's rng, the fight's) is reseeded with it.
STRICT is set by a session that must replay exactly (a recording, the determinism test): the background work and the embedding
model's arrival, which otherwise land whenever they finish, are then fixed at an input's edge."""
from __future__ import annotations

import random

UNSEEDED = "unseeded"
_streams: dict[str, random.Random] = {}
_key = UNSEEDED
STRICT = False


def _seed(name: str) -> str:
    return f"{_key}:{name}"


def begin(seed, step: int, said: str = "") -> None:
    """A new input: every stream starts again from (the campaign's seed, its count of inputs, the line typed). String seeds are
    hashed the same in every process. The global random module is reseeded too, for anything that still rolls it."""
    global _key
    _key = f"{seed}:{step}:{said}"
    for name, r in _streams.items():
        r.seed(_seed(name))
    random.seed(_seed("global"))


def reset() -> None:
    """(f453) A campaign opened or closed (engine/session.py): the key goes back to unseeded and every stream starts again from it, so
    nothing of the last campaign's dice reaches the next. STRICT is the recorder's and stays."""
    global _key
    _key = UNSEEDED
    for name, r in _streams.items():
        r.seed(_seed(name))
    random.seed(_seed("global"))


def get(name: str) -> random.Random:
    """The stream of this name, made the first time it is asked for and reseeded at every input after."""
    r = _streams.get(name)
    if r is None:
        r = _streams[name] = random.Random(_seed(name))
    return r


def new_id(n: int = 8, stream: str = "ids") -> str:
    """A fresh id of n hex digits from the ids stream, in place of a uuid: the same turn makes the same ids. (f462) Or from a stream of
    the caller's naming (the operations' is "ops"), so drawing it moves no die the game already had."""
    return format(get(stream).getrandbits(4 * n), f"0{n}x")


def key() -> str:
    """What the streams were last seeded from (for a recording's rows)."""
    return _key


def keyed(purpose: str, speaker: str = "", conversation: str = "", n: int = 0) -> random.Random:
    """(f476) A die of its own for one purpose (a brief's wording, a reply's pick), seeded from this input's key and the purpose, the
    speaker, the conversation and a count: drawing it moves no stream the game already rolls, so a speaker's brief can never shift a
    fight's dice, and the same input draws the same. Made fresh each call; nothing of it is kept."""
    return random.Random(f"{_key}:keyed:{purpose}:{speaker}:{conversation}:{int(n)}")
