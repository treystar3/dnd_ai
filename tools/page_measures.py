"""(f414) What a night's page showed, counted from the page. The night's Consistency section counted the engine's own counters: what the
gate mended, what the calls were sent back for, who the harness knew travelled with the player. The f395 review found what a reader met
that none of them saw: a refusal note followed by a passage that acted the refused thing out, the same engine sentence forty times a
run, a woman called he in a fight, an alley mouth on a country road, a matter ended by a kill elsewhere, "+0 XP" for a fight. These
detectors read what was shown each turn (turns_game.jsonl `shown`), where the player was and what the harness knew (turns.jsonl `state`,
run.json `cast`), and the model calls (llm_calls.jsonl), and share nothing with the gate's own patterns, so a fix is proven on the page.

    from tools import page_measures
    lines = page_measures.table(game_turns, turns, calls, info)       # markdown rows for summary.md
    lines = page_measures.continuity_table(game_turns, turns, info)   # (f474) memory and time: summary.md's Continuity rows

Rough by design, like the Consistency counts: they are for comparing nights, and each row says what it counts."""
from __future__ import annotations

import collections
import re
import statistics

STORY = ("narration", "speech")
GAME = ("note", "ledger", "wait")
# The game's own ways of saying it cannot do a thing (scenes/*). A reader meets them as the end of what they tried.
REFUSALS = re.compile(r"^(You have nothing like that you can use|There's no such place|There's no one here to give that to|That isn't in your "
                      r"item box|You aren't carrying anything matching|Nothing comes of that here|There's no item box here|"
                      r"You look about for .{1,80}, but nothing here goes by that name)", re.I)        # (f418) the no-such-place answer, reworded
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


# ---- (f474) continuity, read from the page: what people say of time passed, of having met, of what is owed, of a name they were told,
# of companions gone and of deeds done, against the truth the night recorded (turns.jsonl state: talk, owed, party, deeds, from
# tools/nightrun.py continuity_state; run.json bot.continuity_log, from the bot's own steps, f473). Rough like the rest: for comparing
# nights. Each count is a slip a reader would trip over, apart from the few rows that say they count what went right.
SPOKEN = re.compile(r'^([^:"()\n]{1,60}):\s+(.+)$')
MET_BEFORE = re.compile(r"\b(last time|since (?:we|you) (?:last )?(?:spoke|met|talked|were here|came)|we (?:last )?(?:spoke|met|talked)|"
                        r"you were (?:here|in|by)|you came (?:by|in|through)|(?:saw|seen) you|you told me|you said)\b", re.I)
SINCE = [(re.compile(p, re.I), b) for p, b in (
    (r"\byears\b|\ba year\b|\blast year\b", 6),
    (r"\bmonths\b|\ba month\b|\blast month\b", 5),
    (r"\bweeks\b|\ba fortnight\b", 4),
    (r"\b(?:a|one|last) week\b|\b(?:seven|eight|nine|ten) days\b", 3),
    (r"\b(?:two|three|four|five|six|a few|a couple of|several) days\b|\bthe other day\b", 2),
    (r"\byesterday\b|\blast night\b", 1),
    (r"\bthis morning\b|\bearlier today\b|\b(?:an|one|two|three|a few) hours?\b|\bjust now\b", 0))]
BUCKET_DAYS = (0, 1, 2, 7, 14, 30, 90)            # the calendar days at which each of SINCE's buckets begins
STRANGER = re.compile(r"\b(never seen you|don't (?:think I )?know you|who (?:are|might) you be|who are you|haven't met|a new face|"
                      r"you're new (?:here|in town|around)|what's your name|what do they call you|first time I've seen you)\b", re.I)
KNOWN = re.compile(r"\b((?:good|nice|glad) to see you again|see you again|welcome back|you're back|back again|as I told you|like I told you|"
                   r"as I said before|you again)\b", re.I)
STILL_OPEN = re.compile(r"\b(still waiting|have you (?:done|finished|seen to)|any luck with|any news of|did you get to|how goes|how's the|"
                        r"when will you|you said you would)\b", re.I)
NOW_DONE = re.compile(r"\b(thank you for|thanks for|you did it|it's done|you've done it|you finished|well done|you saw it through)\b", re.I)
CLOSED_AS = (("Completed:", "kept"), ("Work done:", "kept"), ("Abandoned:", "given up"), ("Contract expired:", "expired"))
CONTINUITY_GAP = 180                              # minutes: a conversation this long after the last is a new one
OPENING_GAP = 120                                 # minutes without a word from a speaker before their line opens a conversation
DEED_DAYS = 3                                     # how long after a deed a stranger's mention of it is counted


def _bucket(days: int) -> int:
    return max(i for i, d in enumerate(BUCKET_DAYS) if days >= d)


def _claimed(sent: str) -> int | None:
    return next((b for rx, b in SINCE if rx.search(sent)), None)


def _spoken(game_turns: list[dict]):
    """(f474) Every line a person spoke, as (index, turn, speaker as shown, words), in the order shown."""
    i = 0
    for r in game_turns:
        for s in _shown(r):
            if s.get("kind") != "speech":
                continue
            for line in (s.get("text") or "").split("\n"):
                m = SPOKEN.match(line.strip())
                if m:
                    i += 1
                    yield i, r.get("turn"), m.group(1).strip(), m.group(2).strip().strip('"')


def continuity(game_turns: list[dict], turns: list[dict], info: dict) -> dict:
    """(f474) The eight continuity counts, C1 to C8, as plain numbers and short examples."""
    states = [(t.get("turn"), t.get("state") or {}) for t in turns]
    by_turn = {str(t): s for t, s in states}
    prev_of: dict[str, dict] = {}
    for (_, a), (t, _) in zip(states, states[1:]):
        prev_of[str(t)] = a
    ids: dict[str, str] = {}                                              # a speaker as shown -> who they are
    talks: dict[str, set] = collections.defaultdict(set)                  # who -> the minutes they were talked with
    for _, s in states:
        for nid, p in (s.get("talk") or {}).items():
            if p.get("label"):
                ids.setdefault(p["label"], nid)
            if int(p.get("last_talk_at", -1)) >= 0:
                talks[nid].add(int(p["last_talk_at"]))
    firsts = {lab.split()[0]: nid for lab, nid in ids.items() if lab.split() and lab.split()[0][:1].isupper()}

    def who(label: str) -> str:
        return ids.get(label) or (firsts.get(label.split()[0]) if label.split() else "") or ""

    def minutes(turn) -> int | None:
        m = by_turn.get(str(turn), {}).get("minutes")
        return int(m) if m is not None else None

    spoken = [(i, t, lab, words, who(lab), minutes(t)) for i, t, lab, words in _spoken(game_turns)]
    for _, _, _, _, nid, m in spoken:
        if nid and m is not None:
            talks[nid].add(m)
    out: dict = {}

    # C1: time spoken of since the last meeting, against the calendar
    c1, c1_all = [], 0
    for _, t, lab, words, nid, m in spoken:
        if not nid or m is None:
            continue
        before = [x for x in talks.get(nid, ()) if x <= m - CONTINUITY_GAP]
        for sent in _sentences(words):
            claim = _claimed(sent) if MET_BEFORE.search(sent) else None
            if claim is None or not before:
                continue
            c1_all += 1
            real = _bucket(m // 1440 - max(before) // 1440)
            if abs(claim - real) >= 2:
                c1.append((t, lab, sent[:70], claim, real))
    out["c1_time_slips"], out["c1_time_spoken"] = c1, c1_all

    # C2: a conversation's opening, as a stranger to someone met, or as an old friend to someone never met
    c2_stranger, c2_known, last_said = [], [], {}
    for _, t, lab, words, nid, m in spoken:
        if not nid or m is None:
            continue
        opening = nid not in last_said or m - last_said[nid] >= OPENING_GAP
        last_said[nid] = m
        before = (prev_of.get(str(t)) or {}).get("talk", {}).get(nid)
        if not opening or before is None:
            continue
        if before.get("met") and STRANGER.search(words):
            c2_stranger.append((t, lab, STRANGER.search(words).group(0)))
        elif not before.get("met") and KNOWN.search(words):
            c2_known.append((t, lab, KNOWN.search(words).group(0)))
    out["c2_met_as_stranger"], out["c2_stranger_as_met"] = c2_stranger, c2_known

    # C3-C5: what is owed, as it opens and closes (turns.jsonl state.owed)
    lines_at = {str(r.get("turn")): [ln.strip() for s in _shown(r) for ln in (s.get("text") or "").split("\n") if ln.strip()] for r in game_turns}
    closed: dict[str, dict] = {}
    open_at: dict[str, dict[str, dict]] = {}
    vanished, lapsed, last = [], 0, {}
    reasoned, ended_for = 0, {}                                           # (f481) ends the game recorded with a reason (state.closed)
    for t, s in states:
        for c in s.get("closed") or []:
            if c.get("id") and c.get("reason"):
                ended_for[c["id"]] = c["reason"]
        here = {p for p in (s.get("talk") or {})}
        now = {o["id"]: o for o in (s.get("owed") or []) if o.get("id")}
        open_at[str(t)] = now
        for oid, o in last.items():
            gone = oid not in now
            if o.get("kind") in ("work", "request") and o.get("holder") not in here:
                continue                                                  # out of sight, not closed
            if o.get("state") == "open" and now.get(oid, {}).get("state") == "lapsed":
                lapsed += 1
            if not gone:
                continue
            if o.get("kind") == "request" and any(n.get("holder") == o.get("holder") and n.get("state") == "taken" for n in now.values()):
                continue                                                  # taken up: it is a contract now
            tw = _words(o.get("title", ""))
            said = [x for x in lines_at.get(str(t), []) if tw & _words(x)]
            how = next((k for x in said for head, k in CLOSED_AS if x.startswith(head)), "other" if said else "unsaid")
            if how == "unsaid" and oid in ended_for:
                how = "reasoned"                                          # (f481) ended for a reason the holder can give, not vanished
                reasoned += 1
            if how == "unsaid":
                vanished.append((t, o.get("kind"), o.get("title", "")[:50]))
            closed[oid] = {**o, "closed": t, "how": how, "minute": s.get("minutes")}
        last = now
    out["c5_vanished"], out["c5_lapsed"], out["c5_reasoned"] = vanished, lapsed, reasoned
    open_as_done, done_as_open = [], []
    for _, t, lab, words, nid, m in spoken:
        if not nid:
            continue
        for o in open_at.get(str(t), {}).values():
            if o.get("holder") == nid and o.get("state") in ("taken", "open") and NOW_DONE.search(words) and _words(o.get("title", "")) & _words(words):
                open_as_done.append((t, lab, o.get("title", "")[:40]))
        for o in closed.values():
            if o.get("holder") == nid and _turn_after(t, o["closed"]) and STILL_OPEN.search(words) and _words(o.get("title", "")) & _words(words):
                done_as_open.append((t, lab, o.get("title", "")[:40], o["how"]))
    out["c3_open_as_done"], out["c3_closed_as_open"] = open_as_done, done_as_open
    raised = collections.Counter()
    met_after = collections.Counter()
    for o in closed.values():
        if o.get("holder") in ("", "guild") or o["how"] == "unsaid":
            continue
        nxt = next((words for _, t, lab, words, nid, m in spoken if nid == o["holder"] and _turn_after(t, o["closed"])), None)
        if nxt is None:
            continue
        met_after[o["how"]] += 1
        raised[o["how"]] += bool(_words(o.get("title", "")) & _words(nxt))
    out["c4_raised"] = {k: (raised[k], met_after[k]) for k in met_after}

    # C6: the false name the player gave (the bot's one lie, and the turn it set it straight)
    log = (info.get("bot") or {}).get("continuity_log") or {}
    c6 = {"planted": 0, "kept": 0, "spread": 0, "after": 0, "narrated": 0, "examples": []}
    for p in log.get("plants") or []:
        token = p.get("token") or ""
        if not token:
            continue
        c6["planted"] += 1
        fixed = next((c.get("turn") for c in log.get("corrections") or [] if c.get("npc") == p.get("npc") and c.get("token") == token), None)
        rx = re.compile(rf"\b{re.escape(token.split()[0])}\b")
        for _, t, lab, words, nid, m in spoken:
            if not rx.search(words) or not _turn_after(t, p.get("turn"), same=True):
                continue
            late = fixed is not None and _turn_after(t, fixed)
            kind = "after" if late else ("kept" if nid == p.get("npc") else "spread")
            c6[kind] += 1
            if kind != "kept":
                c6["examples"].append((t, lab, kind))
        for r in game_turns:
            if _turn_after(r.get("turn"), p.get("turn")):
                c6["narrated"] += sum(bool(rx.search(s.get("text") or "")) for s in _shown(r) if s.get("kind") == "narration")
        c6["corrected"] = c6.get("corrected", 0) + (fixed is not None)
    out["c6_false_name"] = c6

    # C7: a companion who left, named in the story's lines afterwards (narration as if there; speech of them)
    c7 = []
    for (_, a), (t, b) in zip(states, states[1:]):
        for name in set(a.get("party") or []) - set(b.get("party") or []):
            if not name.strip():
                continue
            back = next((t2 for t2, s2 in states if _turn_after(t2, t) and name in (s2.get("party") or [])), None)
            rx = re.compile(rf"\b{re.escape(name.split()[0])}\b")
            nar = spk = 0
            for r in game_turns:
                if not _turn_after(r.get("turn"), t) or (back is not None and not _turn_after(back, r.get("turn"))):
                    continue
                for s in _shown(r):
                    if s.get("kind") in STORY and rx.search(s.get("text") or ""):
                        nar += s.get("kind") == "narration"
                        spk += s.get("kind") == "speech"
            c7.append((name, t, nar, spk))
    out["c7_left_named"] = c7

    # C8: a deed spoken of by a townsperson who did not see it, within days (the witnesses speaking of it are counted apart)
    heard, seen = [], 0
    for t, s in states:
        for d in s.get("deeds") or []:
            dw = _words(d.get("text", "")) - _words(" ".join(ids))
            if len(dw) < 2 or d.get("minute") is None:
                continue
            for _, t2, lab, words, nid, m in spoken:
                if not nid or m is None or not _turn_after(t2, t) or m - int(d["minute"]) > DEED_DAYS * 1440 or nid == d.get("target"):
                    continue
                if len(dw & _words(words)) >= 2:
                    if nid in (d.get("witnesses") or []):
                        seen += 1
                    else:
                        heard.append((t2, lab, d.get("kind", ""), sorted(dw & _words(words))[:3]))
    out["c8_unseen_spoken_of"], out["c8_witnesses_spoke"] = heard, seen
    return out


def _turn_after(t, ref, same: bool = False) -> bool:
    try:
        return int(t) > int(ref) or (same and int(t) == int(ref))
    except (TypeError, ValueError):
        return False


def continuity_table(game_turns: list[dict], turns: list[dict], info: dict) -> list[str]:
    """(f474) The continuity counts: markdown rows for summary.md's "Continuity (from the page)"."""
    m = continuity(game_turns, turns, info)
    if not any((t.get("state") or {}).get("talk") is not None for t in turns):
        return ["Not recorded on this night (turns.jsonl has no talk state: a night from before f473, or run with --no-continuity)."]
    lines = ["| Continuity (read from what was shown, against what the night recorded) | Value |", "| --- | --- |"]
    c1 = m["c1_time_slips"]
    lines.append(f"| C1 Time since the last meeting, said two steps or more from the calendar / times it was said | {len(c1)} / {m['c1_time_spoken']}"
                 + (f" (e.g. {_ex(c1, 2, lambda x: f'turn {x[0]} {x[1]}: {x[2]!r}')})" if c1 else "") + " |")
    s, k = m["c2_met_as_stranger"], m["c2_stranger_as_met"]
    lines.append(f"| C2 Openings: someone met greets the player as a stranger / someone never met, as known | {len(s)} / {len(k)}"
                 + (f" (e.g. {_ex(s + k, 2, lambda x: f'turn {x[0]} {x[1]}: {x[2]!r}')})" if s or k else "") + " |")
    a, b = m["c3_open_as_done"], m["c3_closed_as_open"]
    lines.append(f"| C3 What is owed, spoken of wrongly by its holder: open as done / closed as still open | {len(a)} / {len(b)}"
                 + (f" (e.g. {_ex(a + b, 2, lambda x: f'turn {x[0]} {x[1]}: {x[2]}')})" if a or b else "") + " |")
    r = m["c4_raised"]
    lines.append("| C4 A kept or broken matter raised by its holder the next time they speak (raised of met), by how it ended | "
                 + ("; ".join(f"{h} {x} of {n}" for h, (x, n) in sorted(r.items())) or "none met again") + " |")
    v = m["c5_vanished"]
    lines.append(f"| C5 Owed things gone with no line saying so / work offers left to lapse / ended for a reason the game kept (f481) | "
                 f"{len(v)} / {m['c5_lapsed']} / {m.get('c5_reasoned', 0)}"
                 + (f" (e.g. {_ex(v, 2, lambda x: f'turn {x[0]} {x[1]} {x[2]!r}')})" if v else "") + " |")
    c6 = m["c6_false_name"]
    lines.append("| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | "
                 + (f"{c6['kept']} / {c6['spread']} / {c6['after']} / {c6['narrated']} (planted {c6['planted']}, set straight {c6.get('corrected', 0)})"
                    if c6["planted"] else "no false name given on this night") + " |")
    c7 = m["c7_left_named"]
    lines.append("| C7 Left the party, then named in narration / in speech before rejoining | "
                 + ("; ".join(f"{n} (turn {t}): {a} / {b}" for n, t, a, b in c7[:4]) or "nobody left") + " |")
    h = m["c8_unseen_spoken_of"]
    lines.append(f"| C8 A deed spoken of within {DEED_DAYS} days by someone who did not see it / by its witnesses (rough) | {len(h)} / {m['c8_witnesses_spoke']}"
                 + (f" (e.g. {_ex(h, 2, lambda x: f'turn {x[0]} {x[1]} {x[2]}')})" if h else "") + " |")
    return lines
