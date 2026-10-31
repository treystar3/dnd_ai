"""(f414) What a night's page showed, counted from the page. The night's Consistency section counted the engine's own counters: what the
gate mended, what the calls were sent back for, who the harness knew travelled with the player. The f395 review found what a reader met
that none of them saw: a refusal note followed by a passage that acted the refused thing out, the same engine sentence forty times a
run, a woman called he in a fight, an alley mouth on a country road, a matter ended by a kill elsewhere, "+0 XP" for a fight. These
detectors read what was shown each turn (turns_game.jsonl `shown`), where the player was and what the harness knew (turns.jsonl `state`,
run.json `cast`), and the model calls (llm_calls.jsonl), and share nothing with the gate's own patterns, so a fix is proven on the page.

    from tools import page_measures
    lines = page_measures.table(game_turns, turns, calls, info)       # markdown rows for summary.md

Rough by design, like the Consistency counts: they are for comparing nights, and each row says what it counts."""
from __future__ import annotations

import collections
import re
import statistics

STORY = ("narration", "speech")
GAME = ("note", "ledger", "wait")
# The game's own ways of saying it cannot do a thing (scenes/*). A reader meets them as the end of what they tried.
REFUSALS = re.compile(r"^(You have nothing like that you can use|There's no such place|There's no one here to give that to|That isn't in your "
                      r"item box|You aren't carrying anything matching|Nothing comes of that here|There's no item box here)", re.I)
MACHINERY = re.compile(r"[{}<>\[\]#*\\]|\b[a-z]+_[a-z_]*\b|\(Note:|\bNote:|\? Yes\b|\bRespond only\b|\bJSON\b")
HEAP = re.compile(r"(?:\(\s*(?:[a-z]+, )?\d+ damage[^)]*\)\s*){2,}", re.I)
URBAN = re.compile(r"\b(alley|alleys|market yard|cobbles?|cobbled|street|streets|stalls?|crates|barrels|doorway|shopfront)\b", re.I)
RAIN = re.compile(r"\b(rain|drizzle|downpour)\b[^.!?]*\b(falls?|lashes|lashing|drums?|drumming|beats?|soaks?|pours?|streams?|slicks?)\b", re.I)
SHELTER = re.compile(r"\b(roof|window|windows|shutters?|eaves|outside|door|doorway|thatch|beyond the walls)\b", re.I)
COLD = re.compile(r"\b(frost|frosted|snow|snowfall|sleet|freezing|icy|ice)\b", re.I)
HOT = re.compile(r"\b(sweltering|scorching|heat haze|baking heat|parched)\b", re.I)
WAS_ENDED = re.compile(r"^(.*?) is ended[ ,:-]+by way of '([^']*)'", re.I)
VICTORY = re.compile(r"^Victory\. \+(\d+) XP")
FOE_LEVEL = re.compile(r"\(lv (\d+)\)")
ESCAPED = re.compile(r"\b(slipped away|worked (?:his|her|their) bonds loose|slips (?:his|her|their) bonds|is gone, bonds and all)\b", re.I)
HANDED = re.compile(r"\btakes .{1,60} into custody\b| is (?:let go|put to the sword)\. Outlaws will hear\b", re.I)   # the settling notes (scenes/arc_actions.py), never the offer
PRONOUNS = {"he": re.compile(r"\b(he|him|his|himself)\b", re.I), "she": re.compile(r"\b(she|her|hers|herself)\b", re.I)}
STOP = set("the and that this with your from have they them their there what when where which would could should about into over just "
           "then than some more like look head back here want going take make tell know need also only even very will".split())


def _shown(row: dict) -> list[dict]:
    sh = row.get("shown") or []
    return sh if isinstance(sh, list) else []


def _mask(line: str) -> str:
    return re.sub(r"\d+", "#", " ".join(line.split()))


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{5,}", (text or "").lower()) if w not in STOP}


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def measure(game_turns: list[dict], turns: list[dict], calls: list[dict], info: dict, world=None) -> dict:
    """Every count, as plain numbers and short examples."""
    from engine import clock
    if world is None:
        try:
            from world.loader import load_world
            world = load_world()
        except Exception:
            world = None
    state_by_turn = {str(r.get("turn")): (r.get("state") or {}) for r in turns}
    out: dict = {}

    # ---- the same line, word for word (digits aside): the engine's own, and narration that is the engine's in narration's clothes
    seen = collections.Counter()
    story_lines = 0
    for r in game_turns:
        for s in _shown(r):
            for line in (s.get("text") or "").split("\n"):
                line = line.strip()
                if len(line.split()) >= 3 and s.get("kind") in GAME + STORY:
                    seen[(s.get("kind") in GAME, _mask(line))] += 1
                    story_lines += s.get("kind") in STORY
    repeated = [(n, game, line) for (game, line), n in seen.items() if n >= 5]
    out["repeated"] = sorted(repeated, reverse=True)
    out["repeated_game_share"] = (sum(n for n, g, _ in repeated if g), sum(n for (g, _), n in seen.items() if g))

    # ---- a refusal, and then a passage that does the refused thing anyway; and whether the refusal was logged at all
    refused_turns = {str(r.get("turn")) for r in (info.get("_refusals") or [])}
    refusals, acted, unlogged = 0, [], 0
    for r in game_turns:
        sh = _shown(r)
        for i, s in enumerate(sh):
            if s.get("kind") in GAME and REFUSALS.match((s.get("text") or "").strip()):
                refusals += 1
                if str(r.get("turn")) not in refused_turns:
                    unlogged += 1
                after = " ".join(x.get("text") or "" for x in sh[i + 1:] if x.get("kind") == "narration")
                shared = _words(r.get("text", "")) & _words(after)
                if after and shared:
                    acted.append((r.get("turn"), (s.get("text") or "")[:50], sorted(shared)[:3]))
                break
    out["refusals"], out["refused_acted"], out["refusals_unlogged"] = refusals, acted, unlogged

    # ---- machinery and figures on the page; speech with nothing in it
    machinery, heaps, empty = [], 0, 0
    for r in game_turns:
        for s in _shown(r):
            if s.get("kind") not in STORY:
                continue
            text = s.get("text") or ""
            body = re.sub(r"^[^\n:]{1,60}: ", "", text) if s.get("kind") == "speech" else text
            m = MACHINERY.search(body)
            if m:
                machinery.append((r.get("turn"), m.group(0)))
            heaps += bool(HEAP.search(body))
            if s.get("kind") == "speech" and (not body.strip(' "') or body.strip(' ".') in ("None", "")):
                empty += 1
    out["machinery"], out["heaps"], out["empty_speech"] = machinery, heaps, empty

    # ---- places: city ground where there is none, rain under a roof, weather out of season
    roofed = {"inn", "guild", "temple", "shop", "smithy", "workshop", "palace", "guardpost", "home", "tavern", "shrine", "hall", "library"}
    urban, rain_in, season_off = [], [], []
    for r in game_turns:
        place = (world.places.get(r.get("place")) if world else None)
        ptype = getattr(place, "type", "") or ""
        wild = bool(getattr(place, "danger", None)) or ptype in ("road", "dungeon", "wild") or str(r.get("place", "")).startswith("road_")
        st = state_by_turn.get(str(r.get("turn")), {})
        season = clock.season(int(st["minutes"])) if st.get("minutes") is not None else ""
        for s in _shown(r):
            if s.get("kind") != "narration":
                continue
            for sent in _sentences(s.get("text")):
                if wild and URBAN.search(sent):
                    urban.append((r.get("turn"), URBAN.search(sent).group(0)))
                if ptype in roofed and RAIN.search(sent) and not SHELTER.search(sent):
                    rain_in.append((r.get("turn"), sent[:70]))
                if (season == "summer" and COLD.search(sent)) or (season == "winter" and HOT.search(sent)):
                    season_off.append((r.get("turn"), season, (COLD.search(sent) or HOT.search(sent)).group(0)))
    out["urban_in_wilds"], out["rain_indoors"], out["out_of_season"] = urban, rain_in, season_off

    # ---- people: a pronoun that is not theirs, by kind of person (run.json cast: hires, companions, captives, townsfolk met)
    cast = info.get("cast") or {}
    firsts = {n.split()[0]: n for n in cast if n and n.split()[0][:1].isupper()}
    slips = collections.Counter()
    sentences = collections.Counter()
    for r in game_turns:
        for s in _shown(r):
            if s.get("kind") != "narration":
                continue
            for sent in _sentences(s.get("text")):
                named = [n for f, n in firsts.items() if re.search(rf"\b{re.escape(f)}\b", sent)]
                if len(named) != 1:
                    continue
                who = cast[named[0]]
                pr = who.get("pronoun")
                other = {"he": "she", "she": "he"}.get(pr)
                if not other:
                    continue
                sentences[who.get("kind", "?")] += 1
                if PRONOUNS[other].search(sent) and not PRONOUNS[pr].search(sent):
                    slips[who.get("kind", "?")] += 1
    out["pronoun_slips"] = {k: (slips[k], sentences[k]) for k in sentences}

    # ---- matters: ended by pursuing them, or by accident (the player's line shares nothing with the matter or the way it ended)
    pursued, accident = [], []
    for r in game_turns:
        for s in _shown(r):
            m = WAS_ENDED.match((s.get("text") or "").strip()) if s.get("kind") in GAME else None
            if m:
                (pursued if _words(r.get("text", "")) & (_words(m.group(1)) | _words(m.group(2))) else accident).append(
                    (r.get("turn"), m.group(1)[:50]))
    out["ended_pursued"], out["ended_by_accident"] = pursued, accident

    # ---- marks left by acts nobody rolled; fights, their worth and their odds
    out["marks_shown"] = sum(1 for r in game_turns for s in _shown(r) if (s.get("text") or "").strip().startswith("Remembered here:"))
    xp, gaps = [], []
    level_at = {str(x.get("turn")): int(x.get("level") or 0) for x in turns}
    for r in game_turns:
        foes = []
        for s in _shown(r):
            t = (s.get("text") or "").strip()
            v = VICTORY.match(t)
            if v:
                xp.append(int(v.group(1)))
            foes += [int(x) for x in FOE_LEVEL.findall(t)]
        foes += list((state_by_turn.get(str(r.get("turn"))) or {}).get("foes") or [])     # (f414) recorded by tools/nightrun.py state_now
        lvl = level_at.get(str(r.get("turn")), 0) if foes else 0
        if foes and lvl:
            gaps.append(max(foes) - lvl)
    out["xp"] = xp
    out["level_gaps"] = gaps

    # ---- captives: escapes against hand-overs and releases
    esc = hand = 0
    for r in game_turns:
        for s in _shown(r):
            t = s.get("text") or ""
            esc += bool(ESCAPED.search(t))
            hand += bool(HANDED.search(t))
    out["captives_escaped"], out["captives_settled"] = esc, hand

    # ---- ASKED BEFORE handed to a speaker for a line that asked nothing
    asked_before = 0
    line_at = {str(r.get("turn")): r.get("text") or "" for r in game_turns}
    for c in calls:
        msgs = c.get("messages") or []
        user = str(msgs[1].get("content", "")) if len(msgs) > 1 else ""
        line = line_at.get(str(c.get("turn")), "")
        if "ASKED BEFORE" in user and c.get("attempt", 0) == 0 and line and "?" not in line:
            asked_before += 1
    out["asked_before_not_a_question"] = asked_before
    return out


def _ex(items, n=3, fmt=lambda x: str(x)) -> str:
    return "; ".join(fmt(x) for x in items[:n])


def table(game_turns: list[dict], turns: list[dict], calls: list[dict], info: dict, world=None) -> list[str]:
    """The page, counted: markdown rows for summary.md."""
    m = measure(game_turns, turns, calls, info, world)
    lines = ["| Measure (read from what was shown) | Value |", "| --- | --- |"]
    rep, (g_rep, g_all) = m["repeated"], m["repeated_game_share"]
    lines.append(f"| Lines shown 5+ times word for word (digits aside) | {len(rep)} lines, {sum(n for n, _, _ in rep)} times; "
                 f"{g_rep} of the game's {g_all} own lines ({round(100 * g_rep / g_all) if g_all else 0}%)"
                 + (f"; most: {_ex(rep, 3, lambda x: f'{x[2][:48]!r} x{x[0]}')}" if rep else "") + " |")
    lines.append(f"| Refusals shown / then acted out in the passage / never logged | {m['refusals']} / {len(m['refused_acted'])} / "
                 f"{m['refusals_unlogged']}" + (f" (e.g. turn {_ex(m['refused_acted'], 2, lambda x: f'{x[0]} {x[2]}')})" if m["refused_acted"] else "") + " |")
    lines.append(f"| Story lines with machinery in them / figure heaps / empty speech | {len(m['machinery'])} / {m['heaps']} / {m['empty_speech']}"
                 + (f" (e.g. {_ex(m['machinery'], 4, lambda x: repr(x[1]))})" if m["machinery"] else "") + " |")
    lines.append(f"| City ground in the wilds / rain under a roof / weather out of season | {len(m['urban_in_wilds'])} / {len(m['rain_indoors'])} / "
                 f"{len(m['out_of_season'])} |")
    ps = m["pronoun_slips"]
    lines.append("| Sentences naming one person, with the other gender's pronoun, by kind | "
                 + ("; ".join(f"{k} {a} of {b}" for k, (a, b) in sorted(ps.items())) or "no one named") + " |")
    lines.append(f"| Matters the player ended: pursued / by accident | {len(m['ended_pursued'])} / {len(m['ended_by_accident'])}"
                 + (f" (by accident: {_ex(m['ended_by_accident'], 2, lambda x: x[1])})" if m["ended_by_accident"] else "") + " |")
    xp = m["xp"]
    lines.append(f"| Fights won / for +0 XP / XP median and most | {len(xp)} / {sum(1 for x in xp if x == 0)} / "
                 f"{int(statistics.median(xp)) if xp else 0} and {max(xp) if xp else 0} |")
    gaps = m["level_gaps"]
    lines.append(f"| Fight turns with a foe 10+ levels above the player | "
                 + (f"{sum(1 for g in gaps if g >= 10)} of {len(gaps)}, the widest {max(gaps):+d}" if gaps else "not recorded on this night") + " |")
    lines.append(f"| Marks shown from acts (Remembered here) | {m['marks_shown']} |")
    lines.append(f"| Captives escaped / handed over or let go | {m['captives_escaped']} / {m['captives_settled']} |")
    lines.append(f"| A speaker told ASKED BEFORE for a line that asked nothing | {m['asked_before_not_a_question']} |")
    return lines
