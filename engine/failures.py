"""(f437) What the player reads when the game could not take a turn. When a model call the turn needs fails every try, the turn is rolled
back (scenes/world.py turn, and a pane button's command): nothing happened, nothing is lost, and the player is told so in the narrator's
own words, never as machinery ("the model couldn't produce a usable answer") and never in the same words twice running. The lines are in
data/rules/failures.yaml. (f459) The rebuild's Stage 3 puts its "presentation that survives failure" here too: the plain lines that tell
an outcome that stood when its passage could not be written (stood_lines, one per ledger row, filled from the row's facts), a line of
several actions of which part stood (part_stood), an outcome shown late on the next load (shown_later), a fight round or a victory whose
telling did not come (round_stood, victory_stood), and the goddess's own words when hers could not be written (goddess_silent). None of
these is a turn not taken: lines() is the two lists the night counts as failed turns, and nothing else."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml
from engine import streams

F = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "failures.yaml").read_text(encoding="utf-8"))
MACHINERY = re.compile(r"\b(model|llm|json|error|errors|answer|server|crash|failed|failure|llama|gpu|vulkan|cuda|slot)\b", re.I)
_last: dict[str, str] = {}


def _pick(key: str, rng: random.Random | None) -> str:
    lines_ = F[key]
    pick = [l for l in lines_ if l != _last.get(key)] or lines_
    line = (rng or streams.get("scene")).choice(pick)
    _last[key] = line
    return line


def not_taken(rng: random.Random | None = None) -> str:
    """A line for a turn the game could not take: never the one shown last."""
    return _pick("turn_not_taken", rng)


def not_possible(rng: random.Random | None = None) -> str:
    """(f449) A line for a line the game has now failed to take twice running on its own fault: trying it again will not help, so the
    player is told to turn to something else (the fault itself is in logs/crash.log). Never the one shown last."""
    return _pick("turn_not_possible", rng)


def lines() -> list[str]:
    """Every line a turn not taken can show (the night tool counts them as failed turns). (f459) The stand-ins for an outcome that stood
    are not among them: a survived narration failure is never a failed turn."""
    return list(F["turn_not_taken"]) + list(F.get("turn_not_possible") or [])


# ---- (f459) presentation that survives failure: what stood, told plainly

PLACEHOLDER = re.compile(r"\{(\w+)\}")
DASH = re.compile(r"\u2014|\u2013|--| - ")
FACTS = {"what": "a bundle of herbs", "who": "the smith", "amount": "12 copper", "done": "the herbs bought", "xp": "40", "coins": "9 copper",
         "fallen": "the wolf", "found": "a worn knife", "foe": "wolf", "count": "two of them"}   # sample facts the startup check fills every template with
STAND_INS = {"stood_any": set(), "part_stood": {"done"}, "shown_later": set(), "round_stood": set(),
             "victory_stood": {"xp", "coins", "fallen", "found"}, "goddess_silent": set(),
             "fight_begun": {"foe", "count"}, "fight_let_go": set()}     # the placeholders each list may use; (f498) a fight's opening untold;
#                                                                           (f507) a saved fight this game could not take up again
STOOD_PLACEHOLDERS = {"what", "who", "amount"}


def _placeholders(line: str) -> set[str]:
    return set(PLACEHOLDER.findall(line))


def _fill(key: str, lines_: list[str], facts: dict, rng: random.Random | None) -> str:
    """One of the lines whose placeholders the facts can fill, never the one shown last for this key, filled."""
    facts = {k: str(v) for k, v in (facts or {}).items() if v not in (None, "")}
    fit = [l for l in lines_ if _placeholders(l) <= set(facts)]
    if not fit:
        return ""
    pick = [l for l in fit if l != _last.get(key)] or fit
    line = (rng or streams.get("scene")).choice(pick)
    _last[key] = line
    return line.format_map(facts)


def stood_lines(rows: list[dict], rng: random.Random | None = None) -> list[str]:
    """One plain line per ledger row telling that what it records stood, filled from the row's facts (labels, never ids; the rows gain a
    `facts` field with Bundle C's record). A row of a kind with no list, or with no facts a line needs, is told by stood_any."""
    out = []
    for r in rows or []:
        kind = r.get("kind", "")
        line = _fill(f"stood.{kind}", (F.get("stood") or {}).get(kind) or [], r.get("facts") or {}, rng) if kind else ""
        out.append(line or _fill("stood_any", F["stood_any"], {}, rng))
    return out


def stood_any(rng: random.Random | None = None) -> str:
    """(f464) One plain line that the deed stands, when its telling could not be written and no row of it has facts to fill a line from."""
    return _fill("stood_any", F["stood_any"], {}, rng)


def part_stood(done: str, rng: random.Random | None = None) -> str:
    """The line for a typed line of several actions of which some stood and a later one did not: `done` names what stood."""
    return _fill("part_stood", F["part_stood"], {"done": done}, rng)


def shown_later(rng: random.Random | None = None) -> str:
    """Before an outcome shown on the next load, once: it happened before the game closed and was never told."""
    return _fill("shown_later", F["shown_later"], {}, rng)


def fight_let_go(rng: random.Random | None = None) -> str:
    """(f507) A fight saved mid-round that could not be taken up again (an older shape, an unreadable row): let go, told once at load."""
    return _fill("fight_let_go", F["fight_let_go"], {}, rng)


def round_stood(rng: random.Random | None = None) -> str:
    """A fight round whose telling could not be written: the numbers carry the blows."""
    return _fill("round_stood", F["round_stood"], {}, rng)


def victory_stood(facts: dict | None = None, rng: random.Random | None = None) -> str:
    """A fight won whose aftermath could not be written: the win stands, with what facts there are (xp, coins, fallen, found)."""
    return _fill("victory_stood", F["victory_stood"], facts or {}, rng)


def goddess_silent(rng: random.Random | None = None) -> str:
    """The goddess at a death whose words could not be written: her own lines, in her voice."""
    return _fill("goddess_silent", F["goddess_silent"], {}, rng)


# ---- (f525) creation and the opening go on through an outage. Each list is read with an empty default: until the owner has read its
# lines (f527 adds them to failures.yaml) behaviour is today's, so a creation call failing still shows today's line, and a goddess
# line or the opening narration failing still ends the game.

CREATION_FAILS = ("interpret", "concept", "gifts", "traits")      # the four places creation tells the player a call failed
CREATION_STEPS = ("name", "concept", "confirm_class", "actives", "passives", "stats", "confirm_stats")   # the steps she speaks on (the
# farewell is the fixed send-off, data/send_off.json, never a written line)


def creation_line(kind: str, rng: random.Random | None = None) -> str | None:
    """(f525) The goddess's own words when a creation call failed (the player's line not read, the concept not read, the gifts or the
    traits not shaped): nothing is lost, the step is asked again. None until the owner's lines are in, so today's line stands."""
    got = (F.get("creation_fail") or {}).get(kind) or []
    return _pick_from(f"creation_fail.{kind}", got, rng) if got else None


def creation_stand_in(step: str, rng: random.Random | None = None) -> str | None:
    """(f525) What the goddess says for the step she is on when her own words could not be written; the page moves on. None until the
    owner's lines are in."""
    got = (F.get("creation_stand_in") or {}).get(step) or []
    return _pick_from(f"creation_stand_in.{step}", got, rng) if got else None


def opening_untold(rng: random.Random | None = None) -> str | None:
    """(f525) The narrator's plain line when the game's opening passage (the first waking, or where a loaded game left off) could not be
    written: the game reaches its first line all the same. None until the owner's lines are in."""
    got = F.get("opening_untold") or []
    return _pick_from("opening_untold", got, rng) if got else None


def _pick_from(key: str, lines_: list, rng: random.Random | None) -> str:
    pick = [l for l in lines_ if l != _last.get(key)] or lines_
    line = (rng or streams.get("scene")).choice(pick)
    _last[key] = line
    return line


COUNT_WORDS = ("one alone", "two of them", "three of them", "four of them", "five of them", "six of them", "seven of them", "eight of them",
               "nine of them", "ten of them")


def count_phrase(n: int) -> str:
    """(f498) How many came: 'one alone', 'two of them', ... '14 of them'."""
    return COUNT_WORDS[n - 1] if 1 <= n <= len(COUNT_WORDS) else f"{n} of them"


def fight_begun(facts: dict | None = None, rng: random.Random | None = None) -> str:
    """(f498) A fight begun whose opening could not be written: the fight is on (its row saved, its pane shown) and the player is told so
    in the narrator's words, with who came ({foe}) and how many ({count}); the round's telling then carries the blows."""
    return _fill("fight_begun", F["fight_begun"], facts or {}, rng)


def problems(data: dict | None = None) -> list[str]:
    """For engine/data_check.py: enough lines, all different, none of them machinery. (f459) The stand-ins too: every list present with
    at least six lines, every placeholder one its list may use, every template filled by the sample facts with no brace left over, no
    dash (the page carries none, engine/hygiene.py undash), and a stood list for every kind of ledger row."""
    d = F if data is None else data
    bad = []

    def look(key: str, got, least: int, allowed: set[str] | None):
        if not isinstance(got, list) or len(got) < least or not all(isinstance(l, str) and l.strip() for l in got):
            bad.append(f"failures.yaml {key}: needs at least {least} lines of text")
            return
        if len({l.strip().lower() for l in got}) != len(got):
            bad.append(f"failures.yaml {key}: a line is there twice")
        for l in got:
            hit = MACHINERY.search(l)
            if hit:
                bad.append(f"failures.yaml {key}: '{l}' speaks of the machinery ('{hit.group(0)}'); say it in the world's words")
            if allowed is None:
                continue
            if DASH.search(l):
                bad.append(f"failures.yaml {key}: '{l}' carries a dash; the page carries none")
            stray = _placeholders(l) - allowed
            if stray:
                bad.append(f"failures.yaml {key}: '{l}' names {sorted(stray)}, which this list cannot fill")
                continue
            try:
                filled = l.format_map(FACTS)
            except (KeyError, ValueError, IndexError) as e:
                bad.append(f"failures.yaml {key}: '{l}' cannot be filled ({e})")
                continue
            if "{" in filled or "}" in filled:
                bad.append(f"failures.yaml {key}: '{l}' leaves a brace when filled")
    for key, least in (("turn_not_taken", 6), ("turn_not_possible", 3)):
        look(key, d.get(key) if isinstance(d, dict) else None, least, None)
    for key, allowed in STAND_INS.items():
        look(key, d.get(key) if isinstance(d, dict) else None, 6, allowed)
    for key in ("creation_fail", "creation_stand_in"):                 # (f525) empty until the owner reads them; checked once they are in
        got = d.get(key) if isinstance(d, dict) else None
        names = CREATION_FAILS if key == "creation_fail" else CREATION_STEPS
        if got is not None and not isinstance(got, dict):
            bad.append(f"failures.yaml {key}: one list per {'kind' if key == 'creation_fail' else 'step'}")
            continue
        for name, lines_ in (got or {}).items():
            if name not in names:
                bad.append(f"failures.yaml {key}.{name}: no such {'kind' if key == 'creation_fail' else 'step'} (one of {', '.join(names)})")
            elif lines_:
                look(f"{key}.{name}", lines_, 3, set())
    if isinstance(d, dict) and d.get("opening_untold"):
        look("opening_untold", d.get("opening_untold"), 3, set())
    stood = d.get("stood") if isinstance(d, dict) else None
    if not isinstance(stood, dict):
        bad.append("failures.yaml stood: needs one list per kind of ledger row")
    else:
        from engine import ledger
        for kind in ledger.KINDS:
            look(f"stood.{kind}", stood.get(kind), 6, STOOD_PLACEHOLDERS)
        for kind in sorted(set(stood) - set(ledger.KINDS)):
            bad.append(f"failures.yaml stood.{kind}: no such kind of ledger row")
    return bad
