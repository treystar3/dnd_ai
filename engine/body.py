"""(f623) What a body can do, and what a fall does to it (data/rules/body.yaml; docs/design/19).

What an attempt asks of the body is a reading of its own, apart from its ruling (f624): a kind and a size (`Feat`). The decision is
the engine's: `judge` reads the table for the body that tries and says how the ruling stands, on either ruling path. (f627) An
attempt is read in two calls (`attempt`): whether it is a feat, which kind and done to what; then, for a feat alone, how big that
thing is. They are measured (tools/reading_eval.py) and not yet called in play: `reading` still answers none, so in play the
table is not asked and no fall is paid for (docs/design/19 section 16). `fall` is
one table for any being: the share of its whole health a fall of some feet takes, from a small view of the body that a
character, a fighter of any kind and an ordinary person each give."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core import yamlio

B = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "body.yaml").read_text(encoding="utf-8"))
K, F = B["kinds"], B["fall"]
SIZES = ("Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan")
HOWS = ("none", "power", "free", "effort", "nearly", "past", "fall")


@dataclass(frozen=True)
class Body:
    """What the table reads of a being: its attributes and its size."""
    attrs: dict
    size: str = "Medium"


@dataclass(frozen=True)
class Feat:
    """What an attempt asks of the body that tries it: a kind from the table and its size in that kind's unit, or none."""
    kind: str = "none"
    size: float = 0


def read(kind: str = "none", size: float = 0) -> Feat:
    """A reading held to the table: a kind it does not hold, or a feat with no size, is no reading (ValueError)."""
    kind = (kind or "").strip().lower() or "none"
    if kind == "none":
        return Feat()
    if kind not in K:
        raise ValueError(f"a feat's kind is one of {', '.join(K)} or none, not {kind}")
    if not float(size or 0) > 0:
        raise ValueError("a feat of the body needs its size, one number above 0 in that kind's unit")
    return Feat(kind, float(size))


def reading(ws, actor_id: str, text: str) -> Feat:
    """What this attempt asks of the body of the one who tries, read from the player's words: the one place either ruling path gets
    it. (f624) No call reads it in play yet: none, and an attempt stands as ruled (docs/design/19 section 16)."""
    return Feat()


@dataclass(frozen=True)
class Judged:
    """An attempt's feat as the engine takes it. how: none (no feat of the body), power (a power they have does it), free (within easy
    reach: as ruled), effort (at least a cost, on `stakes`), nearly or past (a no, `answer`), fall (a drop past what they land unhurt:
    made, rolled on `stakes`, and `share` of their whole health is what it takes landed badly)."""
    how: str = "none"
    kind: str = ""
    size: float = 0
    limit: float = 0
    stakes: dict | None = None
    share: float = 0
    answer: str = ""


def of_character(c) -> Body:
    """A character's own body, with the attribute points their gear adds."""
    from engine import ruling, stats
    gear = stats.gear_attributes(c)
    return Body({a: stats.effective(c, a, gear) for a in ruling.ATTRS})


def of_fighter(f) -> Body:
    """Anyone as they stand in a fight: a creature, a hire, a companion, the character."""
    return Body(dict(f.attrs), f.size if f.size in F["size"] else "Medium")


def ordinary() -> Body:
    """One with no sheet of their own (a townsperson): an ordinary person."""
    from engine import ruling
    return Body({a: F["ordinary"] for a in ruling.ATTRS})


def limit(kind: str, body: Body) -> float:
    """The most this body can do of a kind: straight between the table's marks, straight on past the last, in proportion below the first."""
    spec = K[kind]
    x = max(float(body.attrs.get(a, F["ordinary"])) for a in spec["by"])
    marks = sorted((float(k), float(v)) for k, v in spec["limit"].items())
    if x <= marks[0][0]:
        return marks[0][1] * max(x, 0.0) / marks[0][0]
    (x0, y0), (x1, y1) = next(((a, b) for a, b in zip(marks, marks[1:]) if x <= b[0]), (marks[-2], marks[-1]))
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def unhurt(body: Body) -> float:
    """The height this body drops and lands unhurt: a bigger body falls harder."""
    return limit(F["kind"], body) * float(F["size"][body.size])


def fall(body: Body, feet: float) -> float:
    """The share of its whole health a fall of this many feet takes from this body, 0 to 1."""
    safe = unhurt(body)
    if feet <= safe:
        return 0.0
    if safe <= 0:
        return 1.0
    return min(1.0, (float(feet) - safe) / (safe * (float(F["dead_at"]) - 1)))


def landed(share: float, degree: str) -> float:
    """What a fall takes as it was landed. A fall that takes all of it takes all of it however it is landed."""
    return 1.0 if share >= 1 else share * float(F["landing"][degree][0] if degree in F["landing"] else 1)


def word(share: float) -> str:
    """What a fall took, in the narrator's words."""
    return next((w for top, w in F["told"] if share <= top), F["told"][-1][1])


def judge(body: Body, have: set, r, feat: Feat | None = None) -> Judged:
    """How a ruling stands for this body, by the feat read for the attempt. `have`: the capabilities of the one who tries."""
    from engine import ruling
    kind, size = getattr(feat, "kind", "none"), float(getattr(feat, "size", 0) or 0)
    if kind not in K or size <= 0:
        return Judged()
    spec = K[kind]
    if set(spec.get("powers") or ()) & set(have):
        return Judged("power", kind, size)
    falling = kind == F["kind"]
    top = unhurt(body) if falling else limit(kind, body)
    share = size / top if top > 0 else float("inf")
    own = getattr(getattr(r, "stakes", None), "hard", "") or ""
    attr = max(spec["by"], key=lambda a: body.attrs.get(a, 0))

    def stakes(hard: str) -> dict:
        return {"check": getattr(getattr(r, "stakes", None), "check", "") or attr,
                "hard": max([hard] + ([own] if own in ruling.HARDER else []), key=ruling.HARDER.index)}
    if falling and share > 1:
        return Judged("fall", kind, size, top, stakes(F["hard"]), fall(body, size))
    if share <= float(B["bands"]["effort"]):
        return Judged("free", kind, size, top)
    if share <= 1:
        return Judged("effort", kind, size, top, stakes(B["at_least"]["effort" if share <= float(B["bands"]["hard"]) else "hard"]))
    if share <= float(B["bands"]["nearly"]):
        return Judged("nearly", kind, size, top, answer=spec["nearly"])
    return Judged("past", kind, size, top, answer=spec["past"])


def with_effort(r, j: Judged):
    """A ruling made at least a cost on what the body's table says of it."""
    return r.model_copy(update={"sense": "cost", "stakes": type(r.stakes)(**j.stakes)})


def lines() -> str:
    """The kinds as a reading's instruction lists them."""
    return "\n".join(f"  {k}: {v['about']}, in {v['unit']}" for k, v in K.items())


def schema() -> dict:
    """A kind from the table with its size, or none, as one grammar (the size arms of tools/reading_eval.py)."""
    return {"anyOf": [{"type": "object", "required": ["kind"], "properties": {"kind": {"enum": ["none"]}}},
                      {"type": "object", "required": ["kind", "size"],
                       "properties": {"kind": {"enum": list(K)}, "size": {"type": "integer", "minimum": 1, "maximum": int(B["most"])}}}]}


# ---------- (f627) an attempt read: the feat, then the size of its thing

OWN = "self"                    # the body moving only itself: no kind of the table's, so the table reads it as no feat
ASKED = ("You are the dungeon master of a low-fantasy world of towns, roads and wilds. A player's character attempts something. "
         "Say whether it is a feat of their own body, and which. You do not rule on it: never whether it works.\n"
         "kind: when the attempt is done by the body's own strength or reach, its kind from FEATS. Only what their own body must "
         "do: with a lever, a winch or help, their share. \"none\" for everything else.\n")
THING = "thing: what it is done to or over, in a few words, as the player named it."


def own_line(has_no: str = "thing") -> str:
    """The body's own kind as a reading's list holds it: the class named, with no example of it (an example would be a line of
    the corpus the reading is measured on)."""
    return f"  {OWN}: the body moving only itself, where none of those is the measure; it has no {has_no}"


FEAT_SYSTEM = f"{ASKED}{THING}\nFEATS (a kind: what its size measures):\n{lines()}\n{own_line()}"
SIZE_SYSTEM = ("You are the dungeon master of a low-fantasy world of towns, roads and wilds. A player's character attempts a feat of "
               "their own body. Say how big it is, as the world plainly is: one number, in the unit asked. Give the size of what "
               "their own body must do: the size of the thing itself where they do it alone, and only their share of it where a "
               "tool or other hands help. Not what the character can do, and not whether it works.")


def feat_request(where: str, line: str) -> str:
    return f"WHERE: {where}\nTHE ATTEMPT: {line}"


def size_request(where: str, line: str, kind: str, thing: str) -> str:
    return f"{feat_request(where, line)}\nTHE THING: {thing}\nMEASURE: {K[kind]['about']}, in {K[kind]['unit']}"


def feat_context() -> dict:
    return {"kinds": list(K), "blank": ["none", OWN], "most": int(B["most"]), "thing_chars": int(B["thing_chars"])}


def _shaped(model, schema: dict):
    """A contract written against this grammar, under its own name (as an act's ruling is: engine/act.py shape)."""
    import copy

    class Shaped(model):
        @classmethod
        def model_json_schema(cls, *a, **k) -> dict:
            return copy.deepcopy(schema)
    Shaped.__name__ = Shaped.__qualname__ = model.__name__
    return Shaped


def feat_shape():
    """The feat in its grammar: no feat (none, or the body's own kind), or a kind of the table's with the thing it is done to."""
    from llm.contracts import FeatReading
    return _shaped(FeatReading, {"title": "FeatReading", "anyOf": [
        {"type": "object", "required": ["kind"], "properties": {"kind": {"enum": ["none", OWN]}}},
        {"type": "object", "required": ["kind", "thing"],
         "properties": {"kind": {"enum": list(K)}, "thing": {"type": "string", "minLength": 1, "maxLength": int(B["thing_chars"])}}}]})


def size_shape():
    from llm.contracts import FeatSize
    return _shaped(FeatSize, {"title": "FeatSize", "type": "object", "required": ["size"],
                              "properties": {"size": {"type": "integer", "minimum": 1, "maximum": int(B["most"])}}})


@dataclass(frozen=True)
class Read:
    """An attempt as the two calls read it. `feat`: what the table is handed. `said`: the kind as it was named (none, the body's
    own, or a kind of the table's) and `thing` what it is done to. `lost`: the call that gave no answer (feat or size), when the
    table is handed none for that."""
    feat: Feat = Feat()
    said: str = "none"
    thing: str = ""
    lost: str = ""


def attempt(where: str, line: str) -> Read:
    """What this attempt asks of the body, from the place's name and the player's words: one call for most, a second for a feat."""
    from llm.gateway import LLMError, generate
    from ui import console
    try:
        f = generate("feat_reading", FEAT_SYSTEM, feat_request(where, line), feat_shape(), temperature=0.3, max_tokens=80,
                     validation_context=feat_context())
    except LLMError as e:
        console.debug(f"feat reading: none ({e})")
        return Read(lost="feat")
    if f.kind not in K:
        return Read(said=f.kind)
    try:
        s = generate("feat_size", SIZE_SYSTEM, size_request(where, line, f.kind, f.thing), size_shape(), temperature=0.3, max_tokens=40,
                     validation_context=feat_context())
    except LLMError as e:
        console.debug(f"feat size: none ({e})")
        return Read(said=f.kind, thing=f.thing, lost="size")
    return Read(read(f.kind, s.size), f.kind, f.thing)


def problems() -> list[str]:
    """body.yaml's shape, checked at startup."""
    from engine import ruling
    bad = []
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    bands = B.get("bands") or {}
    if not (set(bands) == {"effort", "hard", "nearly"} and all(num(v) for v in bands.values())
            and 0 < bands["effort"] < bands["hard"] < 1 < bands["nearly"]):
        bad.append("body.yaml bands: effort, hard and nearly, rising, with hard under 1 and nearly over it")
    least = B.get("at_least") or {}
    if not (set(least) == {"effort", "hard"} and set(least.values()) <= set(ruling.HARDER)
            and ruling.HARDER.index(least["effort"]) <= ruling.HARDER.index(least["hard"])):
        bad.append(f"body.yaml at_least: effort and hard, each one of {', '.join(ruling.HARDER)}, hard no easier than effort")
    for name in ("most", "thing_chars"):
        if not (isinstance(B.get(name), int) and not isinstance(B.get(name), bool) and B[name] > 0):
            bad.append(f"body.yaml {name}: a whole number above 0")
    kinds = B.get("kinds") or {}
    for k, spec in kinds.items():
        by = spec.get("by")
        if not (isinstance(by, list) and by and set(by) <= set(ruling.ATTRS)):
            bad.append(f"body.yaml {k} by: one or two attributes ({', '.join(ruling.ATTRS)})")
        marks = spec.get("limit")
        if not (isinstance(marks, dict) and len(marks) >= 2 and all(num(a) and num(v) and a > 0 and v > 0 for a, v in marks.items())
                and [v for _, v in sorted(marks.items())] == sorted(set(marks.values()))):
            bad.append(f"body.yaml {k} limit: two or more marks, attribute to the most it can do, the limit rising with the attribute")
        for name in ("about", "unit") + (() if k == (B.get("fall") or {}).get("kind") else ("past", "nearly")):
            if not str(spec.get(name) or "").strip():
                bad.append(f"body.yaml {k}: needs {name}")
        if not set(spec.get("powers") or ()) <= set(ruling.C):
            bad.append(f"body.yaml {k} powers: only names from capabilities.yaml")
    fl = B.get("fall") or {}
    if fl.get("kind") not in kinds:
        bad.append("body.yaml fall kind: the kind whose limit is the height landed unhurt")
    sizes = fl.get("size") or {}
    if not (set(sizes) == set(SIZES) and all(num(v) and v > 0 for v in sizes.values())):
        bad.append(f"body.yaml fall size: a number above 0 for each of {', '.join(SIZES)}")
    if not (num(fl.get("dead_at")) and fl["dead_at"] > 1 and num(fl.get("ordinary")) and fl["ordinary"] > 0 and fl.get("hard") in ruling.HARDER):
        bad.append(f"body.yaml fall: dead_at above 1, ordinary above 0, hard one of {', '.join(ruling.HARDER)}")
    landing = fl.get("landing") or {}
    if not (set(landing) == {"strong success", "success", "partial", "failure"}
            and all(isinstance(v, list) and len(v) == 2 and num(v[0]) and 0 < v[0] <= 1 and str(v[1]).strip() for v in landing.values())):
        bad.append("body.yaml fall landing: strong success, success, partial and failure, each [the part of the share it takes, above 0 "
                   "and at most 1; how it was landed]")
    told = fl.get("told")
    if not (isinstance(told, list) and told and all(isinstance(x, list) and len(x) == 2 and num(x[0]) and str(x[1]).strip() for x in told)
            and [x[0] for x in told] == sorted({x[0] for x in told}) and told[-1][0] >= 1):
        bad.append("body.yaml fall told: [share, word] rows, the shares rising to 1")
    if not (num(fl.get("same_drop")) and 0 < fl["same_drop"] <= 1):
        bad.append("body.yaml fall same_drop: above 0 and at most 1")
    for name in ("warned", "warned_line"):
        if "{feet}" not in str(fl.get(name) or ""):
            bad.append(f"body.yaml fall {name}: a line that says the {{feet}}")
    died = fl.get("died")
    if not (isinstance(died, list) and len(died) >= 3 and all("{feet}" in str(x) for x in died)):
        bad.append("body.yaml fall died: three or more lines, each saying the {feet}")
    return bad
