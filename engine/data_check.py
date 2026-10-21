"""The game's hand-edited character data, checked as one system when the game starts.

Speech, quirks, banter, party and peoples refer to each other by name: a people names cultures, a culture names a tongue, a tongue offers
words, a temperament needs personality lines, a motive has secrets. A typo in any of them would otherwise surface hundreds of turns later as
a missing line or a silent fallback. check() lists every broken reference and every rule a table must keep; the game refuses to start on
any, and the test suite runs it too.

Adding to the data needs no change here unless a new kind of cross-reference is added; then it belongs here, beside the others."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
QUOTED = re.compile(r"(?:^|[\s(])['\"\u2018\u201c]\w[^'\"\u2019\u201d]*['\"\u2019\u201d]")   # a quoted phrase in a behaviour line: the model quotes it back


class _Strict(yaml.SafeLoader):
    """A loader that refuses a key given twice in one mapping: plain YAML keeps the last silently, so one table quietly replaces another."""


def _no_dupes(loader, node, deep=False):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in seen:
            raise ValueError(f"the key '{key}' is given twice (line {k.start_mark.line + 1})")
        seen.add(key)
    return loader.construct_mapping(node, deep)


_Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dupes)


def _load(rel: str):
    return yaml.load((ROOT / rel).read_text(encoding="utf-8"), Loader=_Strict)


def check() -> list[str]:
    broken = []
    for f in sorted((ROOT / "data").rglob("*.yaml")):              # every data file, not only the ones cross-checked below
        try:
            _load(str(f.relative_to(ROOT)))
        except Exception as e:
            broken.append(f"{f.relative_to(ROOT).as_posix()}: {e}")
    if broken:
        return broken
    S = _load("data/rules/speech.yaml")
    Q = _load("data/rules/quirks.yaml")
    B = _load("data/world/banter.yaml")
    P = _load("data/rules/party.yaml")
    MT = _load("data/world/mentor.yaml")
    peoples_file = {p["id"] for p in _load("data/world/peoples.yaml")}
    bad: list[str] = []

    def need(ok, msg):
        if not ok:
            bad.append(msg)

    # ---- peoples and cultures
    cultures = S.get("cultures", {})
    tongues = {**Q.get("tongues", {}), **S.get("tongues", {})}
    for p in S.get("hire_peoples", {}):
        need(p in peoples_file, f"speech.yaml hire_peoples: '{p}' is not a people in peoples.yaml")
        need(p in S.get("peoples", {}), f"speech.yaml hire_peoples: '{p}' has no cultures under peoples")
    for p, weights in S.get("peoples", {}).items():
        need(p in peoples_file, f"speech.yaml peoples: '{p}' is not a people in peoples.yaml")
        for c, wt in (weights or {}).items():
            need(c in cultures, f"speech.yaml peoples.{p}: culture '{c}' does not exist")
            need(isinstance(wt, (int, float)) and wt > 0, f"speech.yaml peoples.{p}.{c}: weight must be above zero")
    for c, spec in cultures.items():
        need(isinstance(spec.get("home"), str) and spec["home"], f"speech.yaml cultures.{c}: needs a home")
        t = spec.get("tongue", "")
        need(not t or t in tongues, f"speech.yaml cultures.{c}: tongue '{t}' is not defined in quirks.yaml or speech.yaml")
        need(bool(spec.get("dialect")), f"speech.yaml cultures.{c}: needs at least one dialect line")
        for line in spec.get("dialect", []):
            need(not QUOTED.search(line), f"speech.yaml cultures.{c}.dialect: behaviour only, no quoted words: {line!r}")
        need(isinstance(spec.get("sayings", []), list), f"speech.yaml cultures.{c}: sayings must be a list")
        need(isinstance(spec.get("imagery", []), list), f"speech.yaml cultures.{c}: imagery must be a list")
    seen: dict[str, str] = {}
    for t, spec in tongues.items():
        words = spec.get("words", {}) or {}
        need(bool(spec.get("home")), f"tongue '{t}': needs a home")
        need(bool(spec.get("habits")) and not QUOTED.search(spec.get("habits", "")), f"tongue '{t}': habits must describe behaviour, no quoted words")
        for w in spec.get("offer", []) or []:
            need(w in words, f"tongue '{t}': offers '{w}', which is not one of its words")
        for w in words:
            need(w not in seen, f"the word '{w}' belongs to both '{seen.get(w)}' and '{t}'")
            seen[w] = t

    # ---- the profile tables
    strengths = set(S.get("strength", {}).get("weights", {}))
    need(strengths == {"light", "moderate", "strong"}, "speech.yaml strength.weights: needs light, moderate and strong")
    need(set(S.get("culture", {}).get("show", {})) == strengths, "speech.yaml culture.show: needs a chance for every strength")
    need(set(S.get("culture", {}).get("weights", {})) == {"dialect", "transfer_learner", "transfer_fluent", "saying", "imagery", "word"},
         "speech.yaml culture.weights: needs dialect, transfer_learner, transfer_fluent, saying, imagery and word")
    need(set(S.get("fluency", {}).get("weights", {})) == {"native", "fluent", "learner"}, "speech.yaml fluency.weights: needs native, fluent and learner")
    for g in ("imagery_gap", "saying_gap", "word_gap"):
        need(isinstance(S.get(g), int) and S[g] >= 0, f"speech.yaml {g}: a whole number of lines, zero or more")
    need(set(Q.get("material") or {}) == {"curse", "oath"},
         "quirks.yaml material: only curse and oath are read; sayings and home words go by speech.yaml culture (one system, not two)")
    for e in (S.get("emotions") or {}).values():
        need(e in S.get("tells", {}), f"speech.yaml emotions: '{e}' has no tells")
    for e, opts in (S.get("tells") or {}).items():
        need(bool(opts), f"speech.yaml tells.{e}: needs at least one way of showing it")
        for o in opts or []:
            need(not QUOTED.search(o), f"speech.yaml tells.{e}: behaviour only, no quoted words: {o!r}")
    for k, opts in (S.get("expression") or {}).items():
        need(bool(opts), f"speech.yaml expression.{k}: needs at least one way of showing it")
    bgs = S.get("backgrounds", {})
    for b, spec in bgs.items():
        need((spec or {}).get("weight", 0) > 0 and (spec or {}).get("family"), f"speech.yaml backgrounds.{b}: needs a weight above zero and a family")
    for c, mults in (S.get("culture_backgrounds") or {}).items():
        need(c in cultures, f"speech.yaml culture_backgrounds: culture '{c}' does not exist")
        for b, mlt in (mults or {}).items():
            need(b in bgs, f"speech.yaml culture_backgrounds.{c}: background '{b}' does not exist")
            need(isinstance(mlt, (int, float)) and mlt >= 0, f"speech.yaml culture_backgrounds.{c}.{b}: must be zero or more")

    # ---- temperaments, voices, motives
    temps = set(P.get("temperaments", {}))
    motives = set(P.get("motives", {}))
    need(bool(P.get("lines")), "party.yaml: needs at least one line a hire will not cross")
    tiers = [n for _, n in P.get("bond", {}).get("tiers", [])]
    for t in tiers:
        need(bool((P["bond"].get("regard") or {}).get(t)), f"party.yaml bond.regard: tier '{t}' needs a line on how they are with the player")
    for t in temps:
        need(len(Q.get("blueprints", {}).get(t, [])) >= 2, f"quirks.yaml blueprints: temperament '{t}' needs at least two lines")
        for key in ("say", "quip"):
            need(bool(P["temperaments"][t].get(key)), f"party.yaml temperaments.{t}: needs '{key}'")
    for t, lines in (Q.get("blueprints") or {}).items():
        need(t in temps, f"quirks.yaml blueprints: '{t}' is not a temperament in party.yaml")
        for b in lines:
            need(not QUOTED.search(b["say"]), f"quirks.yaml blueprints.{t}: behaviour only, no quoted words: {b['say']!r}")
            for v in b.get("not_with", []):
                need(v in Q.get("voices", {}), f"quirks.yaml blueprints.{t}: not_with names unknown voice '{v}'")
    voices = Q.get("voices", {})
    need(any(spec.get("weight", 1) > 0 for spec in voices.values()), "quirks.yaml voices: at least one voice must have a weight above zero")
    kinds_v = {"persistent", "conditional", "offered"}
    need(set(Q.get("voice_show", {})) == {"conditional"}, "quirks.yaml voice_show: needs a chance for conditional voices")
    for v, spec in voices.items():
        need("prompt" in spec, f"quirks.yaml voices.{v}: needs a prompt (may be empty)")
        need(spec.get("kind") in kinds_v, f"quirks.yaml voices.{v}: kind must be persistent, conditional or offered")
        need(not QUOTED.search(spec.get("prompt", "").replace("{", "")), f"quirks.yaml voices.{v}: behaviour only, no quoted words")
        w = spec.get("weight", 1)
        need(isinstance(w, (int, float)) and w >= 0, f"quirks.yaml voices.{v}: weight must be zero or more")
    for table in ("secret_themes", "secret_fallback"):
        for m in (Q.get(table) or {}):
            need(m in motives, f"quirks.yaml {table}: '{m}' is not a motive in party.yaml")
    for m in motives:
        need(len((Q.get("secret_themes") or {}).get(m, [])) == 2, f"quirks.yaml secret_themes: motive '{m}' needs two themes (trusted, devoted)")
        need(len((Q.get("secret_fallback") or {}).get(m, [])) == 2, f"quirks.yaml secret_fallback: motive '{m}' needs two written fallbacks")
    H = Q.get("habituation") or {}
    for k in ("react_chance", "bond_share"):
        vals = H.get(k) or []
        need(bool(vals) and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in vals) and vals == sorted(vals, reverse=True),
             f"quirks.yaml habituation.{k}: a list of chances from 0 to 1, never rising (it wears in, it does not come back)")
    for m in (Q.get("errands") or {}):
        need(m in motives, f"quirks.yaml errands: '{m}' is not a motive in party.yaml")
    for table in ("repeat_manner",):
        need("default" in Q.get(table, {}), f"quirks.yaml {table}: needs a default")
    for sit, table in (Q.get("subtext") or {}).items():
        need("default" in (table or {}), f"quirks.yaml subtext.{sit}: needs a default")
    kinds = Q.get("detail_kinds", {})
    levels = ("light", "personal", "heavy")
    need(bool(Q.get("detail_first")), "quirks.yaml: needs detail_first")
    need(Q.get("detail_first_gravity") in levels, "quirks.yaml detail_first_gravity: light, personal or heavy")
    need(isinstance(kinds, dict) and len(kinds) >= 4, "quirks.yaml detail_kinds: needs at least four subjects, each with its weight")
    for k, g in (kinds.items() if isinstance(kinds, dict) else []):
        need(g in levels, f"quirks.yaml detail_kinds: '{k}' has weight '{g}'; it must be light, personal or heavy")
    AT = Q.get("answer_told") or {}
    need(bool(AT.get("about")), "quirks.yaml answer_told: needs 'about', what the player must be telling them, for the meaning check")
    need(bool(AT.get("rule")) and all(k in (Q.get("subtext") or {}) for k in AT.get("when", [])),
         "quirks.yaml answer_told: needs a rule, and 'when' may name only situations in subtext")

    # ---- Maren: where things stand, and what she waits for, apart
    ch = MT.get("chat") or {}
    need(bool(ch.get("objective_about")), "mentor.yaml chat.objective_about: needs what talk about the next step sounds like, for the meaning check")
    for st, spec in (ch.get("stages") or {}).items():
        need(bool((spec or {}).get("state")) and bool((spec or {}).get("objective")), f"mentor.yaml chat.stages.{st}: needs a state and an objective")

    # ---- banter
    hooks = B.get("banter", {}).get("hooks", {})
    for h in ("hurt", "carried", "hard_fight", "lost_fight", "fallen", "promotion", "warned", "player", "mood", "news", "arrival", "weather",
              "mundane", "personal", "shared"):
        need(h in hooks, f"banter.yaml hooks: missing '{h}'")
    R = S.get("regard", {})
    need(all(isinstance(R.get(k), (int, float)) and 0 <= R[k] <= 1 for k in ("show", "emotional")),
         "speech.yaml regard: needs show and emotional, each a chance from 0 to 1")
    wants = B.get("banter", {}).get("wants") or {}
    for key in ("personal_self", "personal_other", "shared", "hurt_self", "hurt_other", "hard_fight", "lost_fight", "fallen",
                "promotion_self", "promotion_other", "warned_self", "warned_other", "arrival", "rest", "default"):
        need(key in wants, f"banter.yaml wants: missing '{key}'")
    BB = B.get("banter", {})
    need(all(isinstance(BB.get(k), (int, float)) for k in ("fight_chance", "fight_easy_chance", "fight_easy_cooldown")),
         "banter.yaml banter: needs fight_chance, fight_easy_chance and fight_easy_cooldown")
    need(bool(BB.get("group")) and BB.get("most_speakers") in (2, 3),
         "banter.yaml banter: needs group (what three talking together is) and most_speakers (2 or 3)")
    from engine import actions as _ac
    from scenes import world_prompts as _wp
    try:
        from scenes.world import WorldScene as _WS
    except Exception as e:                            # the scene cannot import: that is its own failure, reported as one problem
        need(False, f"the scene cannot be imported to check the action registry against it: {e}")
    else:
        for p_ in _ac.problems(_WS, _wp.INTERPRET_SYSTEM):
            need(False, p_)
    from engine import candidates as _cd
    need({"most_places", "places_by_meaning", "place_floor", "most_people", "people_by_meaning", "person_floor", "about_floor", "about", "always_if_short",
          "generic_words", "named_town_types", "nearest_of_kind"} <= set(_cd.I) and set(_cd.I["about"]) == {"wares", "abilities", "pack", "recipes", "buyers", "stash"},
         "interpret.yaml: needs the counts and floors, an 'about' sentence for wares, abilities, pack, recipes, buyers and stash, generic_words, named_town_types")
    from engine import severity as _sv
    SVD = _sv.SV
    need(set(SVD.get("level") or {}) == {"light", "personal", "heavy"} and all(set(row) == {"self", "close", "known", "distant"}
         and set(row.values()) <= set(_sv.LEVELS) for row in (SVD.get("level") or {}).values()),
         "severity.yaml level: light, personal and heavy, each with self, close, known and distant, each a level (composed, sobered, shaken, devastated)")
    need(SVD.get("repeat_free_from") in _sv.LEVELS and set((BB.get("director") or {}).get("score", {}).get("opened_up") or {}) == {"close", "known", "distant"}
         and set(((BB.get("director") or {}).get("say") or {}).get("know_player") or {}) == {"close", "known", "distant"},
         "severity.yaml repeat_free_from (a level); banter.yaml director score.opened_up and say.know_player (close, known, distant)")
    need(set(SVD.get("register") or {}) == set(_sv.LEVELS) and isinstance(SVD.get("in_fight"), str) and isinstance(SVD.get("memory"), str)
         and all(set(v) == {"mood", "hours"} for v in (SVD.get("after") or {}).values()) and SVD.get("closeness", {}).get("nobody") in ("close", "known", "distant"),
         "severity.yaml: register for every level, in_fight, memory, after (mood and hours) and closeness")
    from engine import voice_profile as _vp
    need("devastated" in (_vp.S.get("tells") or {}), "speech.yaml tells: needs devastated (how each person breaks)")
    need({"witnessed", "fight_now"} <= set(BB.get("situation") or {}) and isinstance(BB.get("fight_death_chance"), int),
         "banter.yaml banter: situation witnessed and fight_now, and fight_death_chance")
    DR = BB.get("director") or {}
    need(all(isinstance(DR.get(k), (int, float)) for k in ("first", "second", "third", "tie_band")) and DR.get("first", 0) <= DR.get("third", 0),
         "banter.yaml director: needs first, second, third (third the highest bar) and tie_band")
    need(set(DR.get("score") or {}) == {"subject", "stance", "caretaker", "shared", "relevant", "relevant_said", "party", "heavy", "opened_up", "small_talk",
                                        "spoke_last", "started_last"},
         "banter.yaml director.score: needs subject, stance, caretaker, shared, relevant, relevant_said, party, heavy, opened_up, small_talk, spoke_last and started_last")
    need(set(DR.get("most") or {}) == {"idle", "pressing", "grave", "deed", "said"} and all(1 <= v <= 3 for v in (DR.get("most") or {}).values()),
         "banter.yaml director.most: idle, pressing, grave, deed and said, each 1 to 3")
    need(all(v in ("light", "personal", "heavy") for v in (DR.get("hook_weight") or {}).values()) and isinstance(DR.get("read_words"), str)
         and set(DR.get("hook_weight") or {}) <= set(((BB.get("hooks") or {}))),
         "banter.yaml director: hook_weight (each a hook, each light, personal or heavy) and read_words (how the player's words are read)")
    need(set(DR.get("say") or {}) >= {"first_player", "first_party", "approve", "disapprove", "agree", "disagree", "look_after", "answer"},
         "banter.yaml director.say: needs a phrase for every part of a plan")
    need(bool((DR.get("caretaker") or {}).get("tempers") is not None and (DR.get("caretaker") or {}).get("roles") is not None),
         "banter.yaml director.caretaker: needs tempers and roles")
    need("deed" in (BB.get("situation") or {}), "banter.yaml situation: needs deed")
    gl = BB.get("group_lines") or []
    need(len(gl) == 2 and 3 <= gl[0] <= gl[1], "banter.yaml banter.group_lines: [fewest, most], at least three so each of the three speaks")
    G = B.get("banter", {}).get("gravity") or {}
    for mo in ("arrival", "ease", "rest", "after_loss"):
        row = (G.get("unasked") or {}).get(mo) or {}
        need(set(row) == {"light", "personal", "heavy"} and all(isinstance(v, (int, float)) and v >= 0 for v in row.values()) and any(row.values()),
             f"banter.yaml gravity.unasked.{mo}: needs light, personal and heavy, each zero or more, not all zero")
    need(G.get("heavy_needs") in [n for _, n in P.get("bond", {}).get("tiers", [])], "banter.yaml gravity.heavy_needs: must be a bond tier in party.yaml")
    need(isinstance(G.get("heavy_gap_days"), (int, float)) and G["heavy_gap_days"] >= 0, "banter.yaml gravity.heavy_gap_days: zero or more")
    need(set(G.get("asked_margin") or {}) == {"light", "personal", "heavy"}, "banter.yaml gravity.asked_margin: needs light, personal and heavy")
    for key, table in wants.items():
        need("default" in (table or {}), f"banter.yaml wants.{key}: needs a default")

    # ---- the ground fights are fought on (battlefields.yaml): every family well-formed, every tag a real one
    from engine import battlefield as _bf
    from engine import battlefield_builder as _bb
    import random as _random
    need(set(_bb.B.get("sides") or {}) == {"none", "one", "two"} and abs(sum((_bb.B["sides"] or {}).values()) - 1.0) < 1e-6,
         "battlefields.yaml sides: none, one and two, adding up to 1")
    need("default" in _bb.B, "battlefields.yaml: needs a default family")
    for fam in _bb.FAMILIES:
        spec = _bb.B[fam] or {}
        need(bool(spec.get("main")) and bool(spec.get("side")), f"battlefields.yaml {fam}: needs main and side zones")
        for z in (spec.get("main") or []) + (spec.get("side") or []):
            need(bool(z.get("name")) and all(t in _bf.TERRAIN_TAGS for t in z.get("tags", [])),
                 f"battlefields.yaml {fam}: '{z.get('name', '?')}' needs a name and known tags")
            need(z.get("way", "open") in _bf.EDGE_TAGS, f"battlefields.yaml {fam}: '{z.get('name', '?')}' has an unknown way")
        f = _bb.build(fam, _random.Random(7))
        probs = _bf.validate(type("F", (), {"battlefield": f, "fighters": []})())
        need(not probs, f"battlefields.yaml {fam}: a built field has problems: {probs}")
    return bad


def assert_ok() -> None:
    bad = check()
    if bad:
        raise ValueError("The character data has problems:\n" + "\n".join(f"  - {b}" for b in bad))
