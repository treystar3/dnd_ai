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
STRICT = False


class Streams:
    """(f581) One set of dice: the named streams, the key they were last seeded from, and their snapshot. The process has one (DEFAULT,
    which the functions below are); it alone seeds the global random module. A second set beside it moves nothing of the first."""

    def __init__(self, process: bool = False):
        self._streams: dict[str, random.Random] = {}
        self._key = UNSEEDED
        self._process = process

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):                # (f581) a copy of a set of dice is that set: a copied holder never rolls a second one
        return self

    def _seed(self, name: str) -> str:
        return f"{self._key}:{name}"

    def _reseed(self) -> None:
        for name, r in self._streams.items():
            r.seed(self._seed(name))
        if self._process:
            random.seed(self._seed("global"))

    def begin(self, seed, step: int, said: str = "") -> None:
        """A new input: every stream starts again from (the campaign's seed, its count of inputs, the line typed). String seeds are
        hashed the same in every process. The process's set reseeds the global random module too, for anything that still rolls it."""
        self._key = f"{seed}:{step}:{said}"
        self._reseed()

    def reset(self) -> None:
        """(f453) A campaign opened or closed (engine/session.py): the key goes back to unseeded and every stream starts again from it,
        so nothing of the last campaign's dice reaches the next. STRICT is the recorder's and stays."""
        self._key = UNSEEDED
        self._reseed()

    def get(self, name: str) -> random.Random:
        """The stream of this name, made the first time it is asked for and reseeded at every input after."""
        r = self._streams.get(name)
        if r is None:
            r = self._streams[name] = random.Random(self._seed(name))
        return r

    def new_id(self, n: int = 8, stream: str = "ids") -> str:
        """A fresh id of n hex digits from the ids stream, in place of a uuid: the same turn makes the same ids. (f462) Or from a stream
        of the caller's naming (the operations' is "ops"), so drawing it moves no die the game already had."""
        return format(self.get(stream).getrandbits(4 * n), f"0{n}x")

    def key(self) -> str:
        """What the streams were last seeded from (for a recording's rows)."""
        return self._key

    def keyed(self, purpose: str, speaker: str = "", conversation: str = "", n: int = 0) -> random.Random:
        """(f476) A die of its own for one purpose (a brief's wording, a reply's pick), seeded from this input's key and the purpose, the
        speaker, the conversation and a count: drawing it moves no stream the game already rolls, so a speaker's brief can never shift
        a fight's dice, and the same input draws the same. Made fresh each call; nothing of it is kept."""
        return random.Random(f"{self._key}:keyed:{purpose}:{speaker}:{conversation}:{int(n)}")

    def snapshot(self) -> tuple:
        """(f485) Every stream's state as it stands, the global module's with them: an operation asked again from its start
        (engine/asked.py) meets the same dice."""
        return (self._key, {name: r.getstate() for name, r in self._streams.items()}, random.getstate() if self._process else None,
                id(self))

    def restore(self, snap: tuple) -> None:
        """(f485) The streams put back as snapshot() found them; one made since starts again from its seed, as if it had not been drawn."""
        key_then, states, global_state, owner = snap
        if owner != id(self):
            raise RuntimeError("a snapshot of another set of dice")
        if key_then != self._key:
            raise RuntimeError("the streams were reseeded between snapshot and restore")
        for name, r in self._streams.items():
            if name in states:
                r.setstate(states[name])
            else:
                r.seed(self._seed(name))
        if self._process and global_state is not None:
            random.setstate(global_state)


DEFAULT = Streams(process=True)
begin, reset, get, new_id, key, keyed, snapshot, restore = (DEFAULT.begin, DEFAULT.reset, DEFAULT.get, DEFAULT.new_id, DEFAULT.key,
                                                             DEFAULT.keyed, DEFAULT.snapshot, DEFAULT.restore)


def fixed(*parts) -> random.Random:
    """(f501) A die seeded by its declared parts alone, never the input: for what must hold across inputs (a hall's roster for the week,
    a companion's pronoun, chosen once from its id and name). The seed is the parts joined by ":", today's seed strings exactly, so
    nothing rolled this way moves. Made fresh each call; nothing of it is kept."""
    return random.Random(":".join(str(p) for p in parts))
