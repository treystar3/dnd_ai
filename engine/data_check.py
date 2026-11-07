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


GAME_DIRS = ("engine", "scenes", "npc", "llm", "character", "services")      # (f459) where the game asks the model; tools/*.py asks for its
#                                                                                  own ends. (f503) services/ too: a service asks nothing


def task_literals(dirs: tuple = GAME_DIRS, tools: bool = True) -> dict[str, list[str]]:
    """(f459) Every task name the code gives the gateway, generate("...") or fresh("..."), with where it is called: the one source the
    per-task tables (budget.yaml, audit_log.yaml, lora.yaml, hygiene.yaml, config.SAMPLING) are checked against, so none drifts."""
    import ast
    found: dict[str, list[str]] = {}
    files = [p for d in dirs for p in sorted((ROOT / d).rglob("*.py"))]
    if tools:
        files += sorted((ROOT / "tools").glob("*.py"))
    for p in files:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            f = node.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            a0 = node.args[0]
            if name in ("generate", "fresh") and isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                found.setdefault(a0.value, []).append(f"{p.relative_to(ROOT).as_posix()}:{node.lineno}")
    return found


def budget_problems(B: dict | None = None, found: dict | None = None) -> list[str]:
    """(f459) data/rules/budget.yaml: its numbers whole and above zero, every task the code calls in its table with a need and a size,
    no task in the table that nothing calls, and the four older per-task lists (the audit log's reasons, the voice lists, the
    narrator's tasks, the sampling table) subsets of it."""
    import config
    bad: list[str] = []
    B = _load("data/rules/budget.yaml") if B is None else B
    found = task_literals() if found is None else found
    from engine import asked as _asked                                 # (f485) what is asked outside an operation is a task the code asks for
    bad += _asked.problems(set(found))

    def need(ok, msg):
        if not ok:
            bad.append(msg)
    for k in ("limit_seconds", "margin_seconds", "floor_seconds", "reserve_seconds", "chars_per_token"):   # (f527) the embed price is the card's, measured
        need(isinstance(B.get(k), (int, float)) and not isinstance(B.get(k), bool) and B[k] > 0, f"budget.yaml {k}: needs a number above 0")
    if all(isinstance(B.get(k), (int, float)) for k in ("limit_seconds", "margin_seconds", "floor_seconds")):
        need(B["floor_seconds"] + B["margin_seconds"] < B["limit_seconds"], "budget.yaml: the floor and the margin must leave room under the limit")
    R = B.get("retention") or {}
    for k in ("operations", "deferred_turns"):
        need(isinstance(R.get(k), int) and not isinstance(R.get(k), bool) and R[k] > 0, f"budget.yaml retention.{k}: needs a whole number above 0")
    T = B.get("tasks")
    if not isinstance(T, dict) or not T:
        bad.append("budget.yaml tasks: needs a table of the model's tasks")
        return bad
    for name, spec in T.items():
        spec = spec or {}
        need(spec.get("need") in ("required", "optional", "tool"), f"budget.yaml tasks.{name}: need must be required, optional or tool")
        need(isinstance(spec.get("answer_tokens"), int) and spec.get("answer_tokens", 0) > 0, f"budget.yaml tasks.{name}: answer_tokens needs a whole number above 0")
        if spec.get("need") == "optional":
            need(spec.get("later") in ("deferred", "dropped"), f"budget.yaml tasks.{name}: an optional task says later: deferred or dropped")
        else:
            need("later" not in spec, f"budget.yaml tasks.{name}: only an optional task has a later")
    missing = sorted(set(found) - set(T))
    need(not missing, "budget.yaml tasks: the code calls tasks the table does not know: " + ", ".join(f"{t} ({found[t][0]})" for t in missing))
    unused = sorted(set(T) - set(found))
    need(not unused, "budget.yaml tasks: nothing in the code calls " + ", ".join(unused))
    lists = {
        "audit_log.yaml tasks": set((_load("data/rules/audit_log.yaml").get("tasks") or {})),
        "lora.yaml prose_tasks and speech_tasks": set((_load("data/rules/lora.yaml").get("prose_tasks") or []) + (_load("data/rules/lora.yaml").get("speech_tasks") or [])),
        "hygiene.yaml narrator_tasks": set(_load("data/rules/hygiene.yaml").get("narrator_tasks") or []),
        "config.SAMPLING": set(getattr(config, "SAMPLING", {})),
        "DND_THINK_TASKS (config.THINK_TASKS)": set(getattr(config, "THINK_TASKS", ())),     # (f533) a misspelt name would think nowhere
    }
    for where, names in lists.items():
        stray = sorted(names - set(T))
        need(not stray, f"{where} names tasks budget.yaml does not know (and so nothing calls): {', '.join(stray)}")
    reasons = set((_load("data/rules/audit_log.yaml").get("tasks") or {}))
    unexplained = sorted(set(T) - reasons)
    need(not unexplained, "audit_log.yaml tasks: no reason is given for " + ", ".join(unexplained))
    return bad


def baseline_problems(base: dict | None = None) -> list[str]:
    """(f475) data/measured/bundle_d_baseline.yaml, when it is there: its speech tasks are tasks budget.yaml knows, what it measured is
    among them, and each measure is a number where one is given. A renamed task would otherwise leave Bundle D's gate comparing nothing."""
    path = ROOT / "data" / "measured" / "bundle_d_baseline.yaml"
    if base is None:
        if not path.exists():
            return []
        base = _load("data/measured/bundle_d_baseline.yaml") or {}
    bad: list[str] = []
    known = set((_load("data/rules/budget.yaml").get("tasks") or {}))
    priced = base.get("priced_at")                                      # (f527) the speeds the gate prices at, whatever the card profile says now
    if not isinstance(priced, dict) or any(not isinstance(priced.get(k), (int, float)) or isinstance(priced.get(k), bool) or priced[k] <= 0
                                             for k in ("read_tps", "write_tps", "embed_seconds_per_text")):
        bad.append("bundle_d_baseline.yaml priced_at: needs read_tps, write_tps and embed_seconds_per_text above 0")
    listed = list(base.get("speech_tasks") or [])
    if not listed:
        bad.append("bundle_d_baseline.yaml speech_tasks: needs the tasks it measures")
    stray = sorted(set(listed) - known)
    if stray:
        bad.append("bundle_d_baseline.yaml speech_tasks: budget.yaml does not know " + ", ".join(stray))
    for task, m in (base.get("tasks") or {}).items():
        if task not in listed:
            bad.append(f"bundle_d_baseline.yaml tasks.{task}: not among its speech_tasks")
            continue
        for k in ("calls", "first_try", "p50", "p95", "max"):
            v = (m or {}).get(k)
            if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0):
                bad.append(f"bundle_d_baseline.yaml tasks.{task}.{k}: needs a number, not {v!r}")
    return bad


def fights_problems(data: dict | None = None) -> list[str]:
    """(f510) data/measured/bundle_e_fights.yaml, when it is there: its fight tasks and every task its rows count are tasks budget.yaml
    knows, its goldens are kept recordings, its numbers are numbers (an estimate, operations, re-runs, simulations never below zero)."""
    path = ROOT / "data" / "measured" / "bundle_e_fights.yaml"
    if data is None:
        if not path.exists():
            return []
        data = _load("data/measured/bundle_e_fights.yaml") or {}
    bad: list[str] = []
    known = set((_load("data/rules/budget.yaml").get("tasks") or {}))
    tasks = list(data.get("fight_tasks") or [])
    if not tasks:
        bad.append("bundle_e_fights.yaml fight_tasks: needs the tasks it measures")
    for t in sorted(set(tasks) - known):
        bad.append(f"bundle_e_fights.yaml fight_tasks: budget.yaml does not know {t}")
    limit = data.get("limit_seconds")
    if not isinstance(limit, (int, float)) or isinstance(limit, bool) or limit <= 0:
        bad.append(f"bundle_e_fights.yaml limit_seconds: needs a number above zero, not {limit!r}")
    replay = ROOT / "data" / "replay"                                # (f531) the kept recordings are a source tree's: a built game
    for name, rows in (data.get("goldens") or {}).items():          # ships without data/replay, and is not told they are missing
        if replay.exists() and not (replay / "sessions" / str(name) / "calls.jsonl.gz").exists():
            bad.append(f"bundle_e_fights.yaml goldens.{name}: no such recording is kept")
        for i, row in (rows or {}).items():
            for k in ("estimate", "operations", "reruns", "simulations"):
                v = (row or {}).get(k)
                if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                    bad.append(f"bundle_e_fights.yaml goldens.{name}.{i}.{k}: needs a number, not {v!r}")
            for t in sorted(set((row or {}).get("calls") or {}) - set(tasks)):
                bad.append(f"bundle_e_fights.yaml goldens.{name}.{i}: counts a call of '{t}', not one of its fight tasks")
    return bad


def model_problems(cfg=None, server: dict | None = None) -> list[str]:
    """(f527) config.MODEL and EMBED_MODEL are GGUF ids, each a file's stem in data/runtime/server.yaml (name and sha prefix): the id in
    the data hash names exactly the file the server is started on."""
    import config as _config
    cfg = cfg or _config
    server = _load("data/runtime/server.yaml") if server is None else server
    bad: list[str] = []
    models = (server or {}).get("models") or {}
    for role, ident in (("chat", getattr(cfg, "MODEL", "")), ("embed", getattr(cfg, "EMBED_MODEL", ""))):
        m = next((v for v in models.values() if (v or {}).get("role") == role), None)
        if m is None:
            bad.append(f"server.yaml models: no file with the role {role}")
            continue
        stem = str(m.get("file", "")).rsplit(".", 1)[0]
        prefix = str(ident).rsplit("-", 1)[-1]
        if ident != stem:
            bad.append(f"config.{'MODEL' if role == 'chat' else 'EMBED_MODEL'} is {ident!r}, not the {role} file's id {stem!r} (server.yaml)")
        elif not str(m.get("sha256", "")).startswith(prefix):
            bad.append(f"config.{'MODEL' if role == 'chat' else 'EMBED_MODEL'} {ident!r}: its sha prefix is not the {role} file's sha256")
    return bad


def sampling_problems(S: dict | None = None) -> list[str]:
    """(f527) data/rules/sampling.yaml: a base table, a task table and a retry step above 0 (the keys and ranges are llm/llama.py
    sampler_problems', the task names budget_problems')."""
    S = _load("data/rules/sampling.yaml") if S is None else S
    bad: list[str] = []
    if not isinstance(S.get("base"), dict) or not S["base"]:
        bad.append("sampling.yaml base: needs the table laid under every task's own values")
    if not isinstance(S.get("tasks"), dict):
        bad.append("sampling.yaml tasks: needs a table of tasks")
    step = S.get("retry_temperature_step")
    if isinstance(step, bool) or not isinstance(step, (int, float)) or not 0 < step <= 1:
        bad.append("sampling.yaml retry_temperature_step: needs a number above 0 and at most 1")
    return bad


def cards_problems(C: dict | None = None) -> list[str]:
    """(f527) data/rules/cards.yaml: the minimum cards named for each backend are cards the file knows, and every device pattern is a
    regular expression for a known card."""
    import re as _re
    C = _load("data/rules/cards.yaml") if C is None else C
    bad: list[str] = []
    cards = set((C or {}).get("cards") or {})
    minimum = (C or {}).get("minimum") or {}
    if not isinstance(minimum, dict) or not {"cuda", "vulkan"} <= set(minimum):
        bad.append("cards.yaml minimum: needs the minimum card for cuda and for vulkan")
    for backend, card in (minimum.items() if isinstance(minimum, dict) else []):
        if card not in cards:
            bad.append(f"cards.yaml minimum.{backend}: '{card}' is not in cards")
    for card, pat in ((C or {}).get("patterns") or {}).items():
        if card not in cards:
            bad.append(f"cards.yaml patterns: '{card}' is not in cards")
        try:
            _re.compile(str(pat))
        except _re.error as e:
            bad.append(f"cards.yaml patterns.{card}: not a regular expression ({e})")
    return bad


def grammar_problems() -> list[str]:
    """(f527) Every contract's schema converts to the grammar llama-server is sent (llm/gbnf.py), the many-reply ones built at run time
    included: a schema outside the converter's subset (a string pattern, say) is named here, before a call could be refused for it."""
    from llm import contracts, gbnf
    from pydantic import BaseModel
    bad: list[str] = []
    classes = [o for o in vars(contracts).values() if isinstance(o, type) and issubclass(o, BaseModel) and o is not BaseModel
               and o.__module__ == contracts.__name__]
    items = [(c.__name__, c) for c in classes] + [("NPCReplyMany(2)", contracts.many_reply(["a", "b"])),
                                                  ("NPCReplyMany(3, promised)", contracts.many_reply(["a", "b", "c"], promised=True))]
    for name, cls in items:
        try:
            gbnf.grammar(cls.model_json_schema())
        except gbnf.SchemaError as e:
            bad.append(f"contracts.{name}: its schema has no grammar ({str(e)[:160]})")
    return bad


def ceilings_problems(ceil: dict | None = None) -> list[str]:
    """(f490) data/measured/prompt_ceilings.yaml, when it is there: every speech task the baseline names has a ceiling, each a whole number
    of characters, none for a task the baseline does not name; the closing's marks name speech tasks and are numbers."""
    if ceil is None:
        if not (ROOT / "data" / "measured" / "prompt_ceilings.yaml").exists():
            return []
        ceil = _load("data/measured/prompt_ceilings.yaml") or {}
    bad: list[str] = []
    listed = set((_load("data/measured/bundle_d_baseline.yaml") or {}).get("speech_tasks") or [])
    tops = ceil.get("ceilings") or {}
    for task in sorted(listed - set(tops)):
        bad.append(f"prompt_ceilings.yaml ceilings: no ceiling for the speech task {task}")
    for task, v in tops.items():
        if task not in listed:
            bad.append(f"prompt_ceilings.yaml ceilings.{task}: not a speech task the baseline names")
        n = (v or {}).get("chars") if isinstance(v, dict) else None
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            bad.append(f"prompt_ceilings.yaml ceilings.{task}.chars: a whole number of characters above zero")
    marks = ceil.get("closing") or {}
    for task in sorted(set(marks.get("first_try_tasks") or []) - listed):
        bad.append(f"prompt_ceilings.yaml closing.first_try_tasks: {task} is not a speech task the baseline names")
    for k in ("first_try_points", "many_points", "npc_conversation_p95"):
        v = marks.get(k)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            bad.append(f"prompt_ceilings.yaml closing.{k}: a whole number")
    return bad


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
    regions_file = {r["id"] for r in _load("data/world/regions.yaml")}
    for r, weights in S.get("regions", {}).items():                                     # (f347) residents are raised by region too
        need(r in regions_file, f"speech.yaml regions: '{r}' is not a region in regions.yaml")
        for c, wt in (weights or {}).items():
            need(c in cultures, f"speech.yaml regions.{r}: culture '{c}' does not exist")
            need(isinstance(wt, (int, float)) and wt > 0, f"speech.yaml regions.{r}.{c}: weight must be above zero")
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
    for h, spec in (Q.get("habits") or {}).items():                  # (f379) where a habit can happen
        need(spec.get("where", "") in ("", "building", "open_air"), f"quirks.yaml habits.{h}: where is building or open_air, or absent for anywhere")
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
              "mundane", "personal", "shared", "remembered"):
        need(h in hooks, f"banter.yaml hooks: missing '{h}'")
    RM = B.get("banter", {}).get("remembered") or {}
    need(all(isinstance(RM.get(k), (int, float)) for k in ("where_they_fell", "at_rest")) and bool(RM.get("by_days"))
         and all(isinstance(x, (int, float)) for x in RM.get("by_days") or []),
         "banter.yaml remembered: where_they_fell, at_rest and by_days (weights for the dead remembered, by weeks since)")
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
        from scenes import intercepts as _ic
        for p_ in _ic.problems(_WS):
            need(False, p_)
        from scenes import plan_repairs as _pr                 # (f333) the plan repairs, declared like the intercepts
        for p_ in _pr.problems(_WS):
            need(False, p_)
    from engine import reach as _rc                          # (f344) what is within reach: real trades with tools, real place types
    for p_ in _rc.problems({r_["id"] for r_ in _load("data/world/roles.yaml")}, {p_.get("type", "") for p_ in _load("data/world/places.yaml")}):
        need(False, p_)
    from engine import threads as _th                        # (f331) the engine's own situations: templates, effect kinds, slots, the pressures that use them
    from llm.contracts import WorldEffect as _WE
    import typing as _ty
    _pl = {p_["id"] for p_ in _load("data/world/places.yaml")}
    _cr = {c_["id"] for c_ in _load("data/world/bestiary.yaml")}
    for p_ in _th.problems({pr["id"]: pr for pr in _load("data/world/pressures.yaml")}, _ty.get_args(_WE.model_fields["kind"].annotation), _pl, _cr):
        need(False, p_)
    from engine import domain_events as _de, reactions as _rx       # (f330) every reaction points into tables that exist
    _kinds = {getattr(c_, "kind", None) for c_ in _de.Deed.__subclasses__()} | {c_.__dataclass_fields__["kind"].default for c_ in _de.Deed.__subclasses__() if "kind" in c_.__dataclass_fields__}
    _law = _load("data/rules/law.yaml")
    _pulse_rules = _load("data/rules/pulse.yaml")
    _mk = (_pulse_rules.get("effects") or {}).get("marks_keep")
    need(isinstance(_mk, int) and not isinstance(_mk, bool) and _mk > 0,
         f"pulse.yaml effects.marks_keep: the most marks a place or a road keeps must be a whole number above 0 (it is {_mk!r})")   # (f540)
    for p_ in _rx.problems({k for k in _kinds if isinstance(k, str)}, set(Q.get("deeds") or {}), set(_load("data/rules/standing.yaml").get("deeds") or {}),
                           {k for k in (_pulse_rules.get("reputation") or {}) if k != "trust_per_point"}, set((_law.get("heat") or {}).get("gain") or {}),
                           set(_law.get("offenses") or {})):
        need(False, p_)
    from engine import world_improv as _wi                   # (f332) what an improvisation may make true
    for p_ in _wi.problems():
        need(False, p_)
    from engine import look as _look                          # (f388) a look for every people of the world, and no other
    from world.loader import authored as _lw                   # (f451) the one parse of the written world
    for p_ in _look.problems(_lw()):
        need(False, p_)
    PT_ = _load("data/rules/pastimes.yaml")
    _roles = {r_["id"] for r_ in _load("data/world/roles.yaml")}
    from engine import clock as _clock, doings as _doings, moments as _moments                 # (f348) doings by role and period; moments by place and period
    _types = {p_.get("type", "") for p_ in _load("data/world/places.yaml")}
    bad += _doings.problems(_roles, set(_clock.PERIOD_NAMES), _types | {"road", "dungeon", "home"})    # (f449) `at`: the kinds of place, the made ones too
    bad += _moments.problems(_roles, _types, set(_clock.PERIOD_NAMES))
    from engine import town_memory as _tm                                                       # (f484) every kind with a term and a cap
    bad += _tm.problems()
    from engine import brief as _brief                                                          # (f486) the brief's numbers and words
    bad += _brief.problems()
    from engine import voices as _voices                                                      # (f350) voice kits: behaviour, never sound
    bad += _voices.problems()
    RD_ = _load("data/rules/road.yaml")                                                       # (f427) what stops the walk, and who is there
    for k_ in RD_.get("stops", []):
        need(k_ in RD_.get("kinds", {}), f"road.yaml stops: '{k_}' is not a kind of happening (kinds)")
    need("sight" not in RD_.get("stops", []), "road.yaml stops: a passing sight never stops the walk (the owner, review Q2)")
    for k_, r_ in (RD_.get("stop_roles") or {}).items():
        need(r_ in _roles, f"road.yaml stop_roles.{k_}: '{r_}' is not a role")
    import string as _string                                                                  # (f541) the barrier's lines and where it lies
    _bar = RD_.get("barrier") or {}
    _at = _bar.get("at")
    need(isinstance(_at, (int, float)) and not isinstance(_at, bool) and 0 < _at < 1, f"road.yaml barrier.at: a share of the road between 0 and 1 ({_at!r})")
    _ar = _bar.get("ask_ratio")
    need(isinstance(_ar, (int, float)) and not isinstance(_ar, bool) and _ar >= 1, f"road.yaml barrier.ask_ratio: a ratio of 1 or more ({_ar!r})")
    for k_, allowed_ in {"meet": {"onward", "back", "round"}, "round": {"dest", "time"}, "none": {"dest"}, "around": {"road", "why"},
                         "refused": {"road", "why", "dest"}, "wayfinder": {"road", "why"}, "ask": {"road", "why", "dest", "time"}}.items():
        line_ = _bar.get(k_)
        if not isinstance(line_, str) or not line_.strip():
            need(False, f"road.yaml barrier.{k_}: a line is needed")
            continue
        try:
            got_ = {f_ for _, f_, _, _ in _string.Formatter().parse(line_) if f_}
        except ValueError as e_:
            need(False, f"road.yaml barrier.{k_}: {e_}")
            continue
        need(got_ <= allowed_, f"road.yaml barrier.{k_}: {sorted(got_ - allowed_)} are not among {sorted(allowed_)}")
    for path_ in (("hazard", "around_words"), ("aid", "help_words")):
        try:
            re.compile(RD_[path_[0]][path_[1]])
        except (KeyError, re.error) as e_:
            need(False, f"road.yaml {'.'.join(path_)}: {e_}")
    for t_ in Q.get("in_need", {}).get("kind", []) + Q.get("in_need", {}).get("hard", []):
        need(t_ in Q.get("blueprints", {}), f"quirks.yaml in_need: '{t_}' is not a temperament")
    from engine import voices as _vk                                                         # (f431) a blueprint line a kit forbids
    for t_, lines_ in (Q.get("blueprints") or {}).items():
        for b_ in lines_:
            for mark_ in b_.get("not_with_kit", []):
                ax_, _, op_ = mark_.partition(":")
                need(op_ in (_vk.AXES.get(ax_, {}).get("options") or {}), f"quirks.yaml blueprints.{t_}: not_with_kit '{mark_}' is no voice kit option")
    W_ = _load("data/rules/weather.yaml")                                                     # (f430) the season moves the temperature
    seasons_ = set(_load("data/rules/pulse.yaml")["seasons"]["order"])
    need(set(W_.get("by_season") or {}) == seasons_, f"weather.yaml by_season: needs exactly the seasons {sorted(seasons_)}")
    from engine import routines as _routines                                                  # (f352) routines by period and kind of place
    bad += _routines.problems(_types, set(_clock.PERIOD_NAMES), _roles)
    from engine import motives as _mo                                                        # (f360) known people's steps, by the trait their goal came from
    bad += _mo.problems(set(((_pulse_rules.get("drift") or {}).get("motives") or {}).get("seeds") or {}))
    from engine import consequences as _cq                                                   # (f359) the town answers the stranger's deeds
    bad += _cq.problems(_th.T["templates"], ("kill", "offense", "quest_done", "persuade", "deliver", "dungeon_cleared", "found", "defend", "settled"))
    from engine import starts as _starts                                                      # (f367) starting points for the night run
    bad += _starts.problems(set(_load("data/rules/standing.yaml")["groups"]), set(_pulse_rules["tiers"]), set(_load("data/rules/guild.yaml")["ranks"]))
    from engine import guard as _guard                                                        # (f364) the content guard's categories
    bad += _guard.problems()
    from engine import hygiene as _hygiene                                                    # (f391) the output gate's rules
    bad += _hygiene.problems()
    from engine import entities as _entities                                                  # (f392) the lifecycles
    bad += _entities.problems()
    from engine import ruling as _ruling                                                      # (f395) what a character can do beyond the ordinary
    bad += _ruling.problems()
    from engine import techniques as _techniques                                              # (f396) what hires can do in a fight
    bad += _techniques.problems()
    from engine import spells as _spells                                                      # (f397) the spellbook
    bad += _spells.problems()
    from engine import features as _features                                                  # (f394) the parts of places
    from world.loader import authored as _lw
    bad += _features.problems(_lw())
    from engine import trust as _trust                                                        # (f362) trust moved by the engine, by a reply's intent
    import typing as _typing
    from llm.contracts import NPCReply as _NPCReply
    bad += _trust.problems(set(_typing.get_args(_NPCReply.model_fields["intent"].annotation)))
    from engine import stay as _stay                                                          # (f351) the room changing mid-stay
    _wx = {c_["id"] for c_ in _load("data/rules/weather.yaml")["conditions"]}
    bad += _stay.problems(_wx, set(_clock.PERIOD_NAMES), _types)
    _degrees = set(_load("data/rules/checks.yaml")["degrees"])
    need(set((PT_.get("gamble") or {}).get("payout") or {}) == _degrees, "pastimes.yaml gamble.payout: one entry per degree in checks.yaml")
    need(all(r_ in _roles for r_ in (PT_.get("gamble") or {}).get("roles") or []), "pastimes.yaml gamble.roles: every role must be in roles.yaml")
    need(set((PT_.get("haggle") or {}).get("discount") or {}) <= _degrees and "failure" not in ((PT_.get("haggle") or {}).get("discount") or {}),
         "pastimes.yaml haggle.discount: degrees from checks.yaml, never failure (a failed haggle buys nothing)")
    need(all(k in (PT_.get("pray") or {}) for k in ("minutes", "temple_types")), "pastimes.yaml pray: needs minutes and temple_types")
    from engine import drift as _dr
    for p_ in _dr.problems({t_["id"] for t_ in _load("data/traits.yaml")}):
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

    # ---- (f346) the sounds names are built from (name_sounds.yaml): every people has them, every piece is letters, every kind builds
    from npc import names as _names
    sounds = (_load("data/world/name_sounds.yaml") or {}).get("peoples") or {}
    need(set(sounds) <= peoples_file, f"name_sounds.yaml: sounds for unknown peoples {sorted(set(sounds) - peoples_file)}")
    for people in sorted(peoples_file):
        r = sounds.get(people)
        need(r is not None, f"name_sounds.yaml: no sounds for the people '{people}'")
        if r is None:
            continue
        need(not r.get("family_from") or r["family_from"] in sounds, f"name_sounds.yaml {people}: family_from names an unknown people")
        table = r.get("syllables")
        if table is not None:
            need(isinstance(table, dict) and table and all(isinstance(n, int) and n >= 1 and isinstance(w, (int, float)) and w >= 0
                                                             for n, w in table.items()) and sum(table.values()) > 0,
                 f"name_sounds.yaml {people}: syllables must be counts from 1 up, each with a weight")
        for kind in ("male", "female") + (() if r.get("family_from") else ("family",)):
            forms = r.get(kind) or []
            need(bool(forms), f"name_sounds.yaml {people}: needs {kind} forms")
            for i, form in enumerate(forms):
                where = f"name_sounds.yaml {people} {kind} form {i + 1}"
                uses_middle = any(int(n) > 0 for n in (form.get("middles") or {0: 1}))
                for slot in ("first", "last") + (("middle",) if uses_middle else ()):
                    pieces = form.get(slot) or []
                    need(bool(pieces) and all(isinstance(x, str) and (x == "" or x.isalpha()) for x in pieces),
                         f"{where}: {slot} must be pieces of letters, or \"\" (quote On, No, Yes and Off, or YAML reads them as true/false)")
                    need(len({x.lower() for x in pieces if isinstance(x, str)}) == len(pieces), f"{where}: {slot} lists a piece twice")
            try:
                rng = _random.Random(f"check:{people}:{kind}")
                for _ in range(30):
                    _names.build(people, kind, rng)
            except Exception as e:
                need(False, f"name_sounds.yaml {people} {kind}: {e}")
            if isinstance(table, dict) and table:                     # every length the table asks for can be made
                made = {min(_names.syllables(n), max(table)) for n in _names.possible(people, kind)}
                need(all(n in made for n, w in table.items() if w), f"name_sounds.yaml {people} {kind}: syllables asks for names of "
                     f"{sorted(n for n, w in table.items() if w and n not in made)} syllables, and its sounds cannot make any")

    # ---- (f444) the cards a recording may be timed on
    for card, spec in ((_load("data/rules/cards.yaml") or {}).get("cards") or {}).items():
        need(all(isinstance((spec or {}).get(k), (int, float)) and spec[k] > 0 for k in ("bandwidth_gbs", "tflops", "memory_gb")),
             f"cards.yaml {card}: needs bandwidth_gbs, tflops and memory_gb above 0")

    # ---- (f446) the card profile Stage 3's turn budget reads: whole, and an estimate said to be one ((f459) under data/measured)
    prof = ROOT / "data" / "measured" / "card_profile.yaml"
    if prof.exists():
        P_ = _load("data/measured/card_profile.yaml") or {}
        cards_known = set(((_load("data/rules/cards.yaml") or {}).get("cards") or {}))
        need(P_.get("card") in cards_known, f"card_profile.yaml: card '{P_.get('card')}' is not in cards.yaml")
        need(not P_.get("scaled_from") or P_["scaled_from"] in cards_known, f"card_profile.yaml: scaled_from '{P_.get('scaled_from')}' is not in cards.yaml")
        for k in ("prompt_tokens_per_second", "answer_tokens_per_second", "embed_seconds_per_text", "median_turn_seconds", "longest_turn_seconds"):
            need(isinstance(P_.get(k), (int, float)) and P_[k] > 0, f"card_profile.yaml {k}: needs a number above 0")   # (f527) the embed price among them
    bad += cards_problems()                                              # (f527) the minimum cards and the device patterns

    # ---- (f475) Bundle D's baseline (data/measured, outside the hash): every task it measures is one the budget knows
    bad += baseline_problems()
    bad += ceilings_problems()                                      # (f490)

    # ---- (f478) how much of each kind of memory a person keeps
    from engine import memory as _memory
    bad += _memory.problems()

    # ---- (f480) what each person keeps of their view of each character
    from engine import regard as _regard
    bad += _regard.problems()

    # ---- (f481) offers and obligations: every family's reasons and memories name a final state of its lifecycle
    from engine import obligations as _obligations
    bad += _obligations.problems()

    # ---- (f477) how long ago, in words: bands ascending, no digits or dashes, every {n} covered
    from engine import clock as _clock
    bad += _clock.time_words_problems()

    # ---- (f437) what the player reads when a turn could not be taken: enough lines, all different, never machinery
    from engine import failures as _failures
    bad += _failures.problems()

    # ---- (f459) the turn budget's tunables, and the one table of the model's tasks every per-task list is checked against
    bad += budget_problems()

    # ---- (f460) the words that answer a question the world asked, how often one is asked, and the lines that let one go
    from engine import questions as _questions
    bad += _questions.problems()

    # ---- (f435) what someone said of themselves that the canon check could not be asked about waits, unsettled
    U = ((_load("data/rules/truth.yaml").get("canon") or {}).get("unsettled") or {})
    for k in ("cap", "again_per_keep"):
        need(isinstance(U.get(k), int) and not isinstance(U.get(k), bool) and U.get(k) > 0,
             f"truth.yaml canon.unsettled.{k}: needs a whole number above 0")

    # ---- (f499) what a fight keeps of itself between rounds: the cap on its rows
    ek = _load("data/rules/combat.yaml").get("effects_keep")
    need(isinstance(ek, int) and not isinstance(ek, bool) and ek > 0, "combat.yaml effects_keep: needs a whole number above 0")
    bad += tables_problems()                                           # (f504) the fight's tables, both ways
    bad += trigger_problems()                                          # (f507) the triggers held to the code that evaluates them
    bad += allowlist_problems()                                        # (f509) every table the fight reads, held to the code, both ways
    bad += fights_problems()                                           # (f510) the fight measures' shape
    from llm import llama as _llama
    bad += sampling_problems()                                         # (f527) data/rules/sampling.yaml's shape
    bad += _llama.sampler_problems()                                   # (f521) every sampler key one llama-server reads, in its range
    bad += model_problems()                                            # (f527) the model ids name the server's files
    bad += grammar_problems()                                          # (f527) every contract has its grammar
    from llm import runtime as _runtime
    bad += _runtime.runtime_problems()                                 # (f522) the server's settings hold what the game sends
    from llm import launch as _launch
    bad += _launch.problems()                                          # (f526) the load screen's lines, once the owner's are in
    return bad


def tables_problems(AE: dict | None = None, ST: dict | None = None, CB: dict | None = None) -> list[str]:
    """(f504) The fight's tables held to the code both ways: every kind in active_effects.yaml has a family, an expiry and a stacking rule
    the table itself lists, a status kind's deltas name a combat.yaml statuses row and every statuses row has a kind; every stage a
    damage path in stages.yaml names has a function in engine/damage.py and every function there is named by a path; the hit steps are
    a list of names; (f507) every status eligibility stage named has a function in engine/effects.py and every function there is
    named; every stacking recipe has a function in engine/stacking.py and every function a recipe, with parts the recipe knows. Data
    cannot promise what code cannot run."""
    from engine import damage, stacking
    AE = _load("data/rules/active_effects.yaml") if AE is None else AE
    ST = _load("data/rules/stages.yaml") if ST is None else ST
    CB = _load("data/rules/combat.yaml") if CB is None else CB
    out: list[str] = []

    def need(ok, msg):
        if not ok:
            out.append(msg)

    fam, exp, stk = list(AE.get("families") or []), list(AE.get("expiry") or []), list(AE.get("stacking") or [])
    need(len(fam) == 6, f"active_effects.yaml families: six families, not {len(fam)}")
    statuses = CB.get("statuses") or {}
    kinds = AE.get("kinds") or {}
    status_kinds = set()
    for k, spec in kinds.items():
        spec = spec or {}
        need(spec.get("family") in fam, f"active_effects.yaml kinds.{k}: family '{spec.get('family')}' is not one of {', '.join(fam)}")
        need(spec.get("expiry") in exp, f"active_effects.yaml kinds.{k}: expiry '{spec.get('expiry')}' is not one of {', '.join(exp)}")
        need(spec.get("stacking") in stk, f"active_effects.yaml kinds.{k}: stacking '{spec.get('stacking')}' is not one of {', '.join(stk)}")
        need(set(spec) <= {"family", "expiry", "stacking", "deltas"}, f"active_effects.yaml kinds.{k}: unknown keys {sorted(set(spec) - {'family', 'expiry', 'stacking', 'deltas'})}")
        deltas = spec.get("deltas")
        if deltas:
            need(deltas == f"statuses.{k}" and k in statuses, f"active_effects.yaml kinds.{k}: deltas '{deltas}' is not a combat.yaml statuses row of that name")
            status_kinds.add(k)
        elif spec.get("family") == "status":
            need(False, f"active_effects.yaml kinds.{k}: a status kind needs its deltas row in combat.yaml statuses")
    for st in statuses:
        need(st in kinds and (kinds[st] or {}).get("family") == "status", f"combat.yaml statuses.{st}: no status kind of that name in active_effects.yaml")
    paths = ST.get("damage") or {}
    declared = set()
    for path, ids in paths.items():
        need(isinstance(ids, list) and ids and all(isinstance(i, str) for i in ids), f"stages.yaml damage.{path}: a list of stage names")
        for i in (ids or []):
            need(i in damage.STAGES, f"stages.yaml damage.{path}: '{i}' is no stage engine/damage.py can run")
            declared.add(i)
    for i in damage.STAGES:
        need(i in declared, f"stages.yaml damage: engine/damage.py has a stage '{i}' that no path names")
    for key in ("hit_steps", "status_eligibility"):
        v = ST.get(key)
        need(isinstance(v, list) and v and all(isinstance(i, str) and i for i in v), f"stages.yaml {key}: a list of names")
    from engine import effects
    for i in (ST.get("status_eligibility") or []):                        # (f507) each stage named has a function, each function is named
        need(i in effects.STAGES, f"stages.yaml status_eligibility: '{i}' is no stage engine/effects.py can run")
    for i in effects.STAGES:
        need(i in (ST.get("status_eligibility") or []), f"stages.yaml status_eligibility: engine/effects.py has a stage '{i}' the table does not name")
    recipes = ST.get("stacking") or {}
    for r, parts in recipes.items():
        need(r in stacking.RECIPES, f"stages.yaml stacking.{r}: no recipe of that name in engine/stacking.py")
        if r in stacking.RECIPES:
            need(isinstance(parts, list) and parts and all(p in stacking.PARTS[r] for p in parts), f"stages.yaml stacking.{r}: parts {parts} are not the recipe's {list(stacking.PARTS[r])}")
    for r in stacking.RECIPES:
        need(r in recipes, f"stages.yaml stacking: engine/stacking.py has a recipe '{r}' the table does not name")
    return out


def evaluated_triggers() -> set[str]:
    """(f507) Every trigger id the code can make true, read from the code: the string literals of engine/combat.py active_triggers,
    scenes/world.py conditions and scenes/check_actions.py check_triggers, the creature-category triggers (engine/combat.py
    CATEGORY_TRIGGERS), and in_<biome> for every biome the world data names (conditions builds it from the place's biome)."""
    import ast
    found: set[str] = set()
    for rel, fn in (("engine/combat.py", "active_triggers"), ("scenes/world.py", "conditions"), ("scenes/check_actions.py", "check_triggers")):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == fn:
                found |= {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    from engine import combat
    found |= set(combat.CATEGORY_TRIGGERS.values())
    biomes: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "biome" and isinstance(v, str):
                    biomes.add(v)
                if k == "biomes" and isinstance(v, list):
                    biomes.update(b for b in v if isinstance(b, str))
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for f in sorted((ROOT / "data" / "world").rglob("*.yaml")):
        walk(_load(str(f.relative_to(ROOT))))
    found |= {f"in_{b}" for b in biomes}
    return found


def trigger_problems(T: list | None = None) -> list[str]:
    """(f507) triggers.yaml held to the code both ways: a trigger no code evaluates must say dormant: true (creation, gear and lessons
    never offer it; an old character's passive still loads), and one the code evaluates must not."""
    T = _load("data/rules/triggers.yaml") if T is None else T
    live = evaluated_triggers()
    out = []
    for t in T or []:
        tid, dormant = (t or {}).get("id"), bool((t or {}).get("dormant"))
        if tid in live and dormant:
            out.append(f"triggers.yaml {tid}: says dormant, but the code evaluates it")
        if tid not in live and not dormant:
            out.append(f"triggers.yaml {tid}: no code evaluates it; mark it dormant: true, or evaluate it")
    return out


# ---------- (f509) the allow-lists: every table the fight reads, held to the code that runs it, both ways ----------

def _literals(paths) -> set[str]:
    """Every string constant in these modules' syntax trees."""
    import ast
    out: set[str] = set()
    for rel in paths:
        for n in ast.walk(ast.parse((ROOT / rel).read_text(encoding="utf-8"))):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                out.add(n.value)
    return out


def _compared(rel: str, names: tuple[str, ...]) -> set[str]:
    """Every string a module compares one of these names against (`kind == "smite"`, `eid in ("a", "b")`): what its dispatch handles."""
    import ast
    out: set[str] = set()
    for c in ast.walk(ast.parse((ROOT / rel).read_text(encoding="utf-8"))):
        if isinstance(c, ast.Compare) and isinstance(c.left, ast.Name) and c.left.id in names:
            for comp in c.comparators:
                if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                    out.add(comp.value)
                elif isinstance(comp, (ast.Tuple, ast.List, ast.Set)):
                    out |= {x.value for x in comp.elts if isinstance(x, ast.Constant) and isinstance(x.value, str)}
    return out


GAME_CODE = ("engine", "scenes", "services", "npc", "character", "llm")     # (f509) where a row's key or an id may be read by name
_SCAN: dict = {}


def scan_code(precise: bool = False) -> tuple[set[str], set[str]]:
    """(f509) What the game's code names: (every string it holds, every row key it reads by name: x["key"], x.get("key")), over
    GAME_CODE. By default read by pattern with the comments stripped (a tenth of a second, for the check at every startup); precise,
    read from the syntax tree (two seconds, for the suite's test, which holds the two readings to one verdict). Cached: the code does
    not change while a process runs."""
    import ast
    import re
    if precise in _SCAN:
        return _SCAN[precise]
    lits, keys = set(), set()
    for d in GAME_CODE:
        for p in sorted((ROOT / d).glob("*.py")):
            text = p.read_text(encoding="utf-8")
            if precise:
                for n in ast.walk(ast.parse(text)):
                    if isinstance(n, ast.Constant) and isinstance(n.value, str):
                        lits.add(n.value)
                    elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str):
                        keys.add(n.slice.value)
                    elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args \
                            and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                        keys.add(n.args[0].value)
            else:
                code = "\n".join(line.split("#")[0] for line in text.split("\n"))
                lits |= set(re.findall(r'["\']([A-Za-z_][\w ]*)["\']', code))
                for a, b in re.findall(r'\[["\']([a-z_]+)["\']\]|\.get\(["\']([a-z_]+)["\']', code):
                    keys.add(a or b)
    _SCAN[precise] = (lits, keys)
    return lits, keys


def _read_keys(precise: bool = False) -> set[str]:
    """Every key the game's code reads from a row by name."""
    return scan_code(precise)[1]


def code_named(precise: bool = False) -> set[str]:
    """Every string the game's code names (what it can run by name)."""
    return scan_code(precise)[0]


def creature_categories() -> set[str]:
    """Every creature category the engine knows: the keys of combat.yaml creatures.natural_armor (the bestiary's rows are held to them
    elsewhere in this check)."""
    from engine import combat
    return set((combat.RULES.get("creatures") or {}).get("natural_armor") or {})


ALLOW_TABLES = ("legendary", "expressions", "relics", "summons", "bosses", "martial", "movement", "healing", "mechanics")


def allowlist_problems(tables: dict | None = None, handled: dict | None = None, precise: bool = False) -> list[str]:
    """(f509) Every table the fight reads, held to the code that runs it, both ways: legendary effects (engine/legendary.py: by name,
    category or world mechanic, else enabled: false), spellcraft expressions (each named by engine/spellcraft.py or engine/combat.py;
    each the dispatch compares is in the table), relic powers (the kinds engine/relics.py use dispatches), summon forms (each row's
    keys ones engine/summons.py reads; the forms the summon family of active_effects.yaml names), boss kits' options (the kinds
    engine/bosses.py _do runs), martial maneuvers (each row's keys ones engine/martial.py reads, its status a combat.yaml status, each
    maneuver the code names in the table), movement kinds (engine/movement.py), healing forms (engine/healing.py, mend the plain one),
    passive mechanics (core/rules.py's engine sets: the refusal that lived at import, and a set entry that is neither a mechanic nor a
    legendary effect). `tables` and `handled` override a table or the code's side, for the test's planted ids; `precise` reads the
    code by its syntax tree (scan_code)."""
    from core import rules
    from engine import items, legendary, summons, martial, spellcraft, combat as _cb
    T = tables or {}
    H = handled or {}
    out: list[str] = []

    def need(ok, msg):
        if not ok:
            out.append(msg)
    # legendary effects
    effects = T.get("legendary") or items.LEGENDARY
    out += legendary.problems(effects, H.get("legendary") or code_named(precise), creature_categories(), set(rules.ENGINE_WORLD_MECHANICS))
    # spellcraft expressions
    EXPR = T.get("expressions") or spellcraft.EXPR
    named = H.get("expressions") or _literals(["engine/spellcraft.py", "engine/combat.py"])
    compared = H.get("expressions_compared") or _compared("engine/spellcraft.py", ("eid",))
    for eid in EXPR:
        need(eid in named or eid in compared, f"spellcraft.yaml expressions.{eid}: nothing in engine/spellcraft.py or engine/combat.py runs it")
    for eid in sorted(compared):
        need(eid in EXPR, f"engine/spellcraft.py handles an expression '{eid}' that spellcraft.yaml does not name")
    # relic powers
    AC = T.get("relics") or _load("data/rules/accessories.yaml")
    kinds_used: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("kind"), str) and "text" in o:
                kinds_used.add(o["kind"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(AC)
    relic_kinds = H.get("relics") or _compared("engine/relics.py", ("kind",))
    for k in sorted(kinds_used):
        need(k in relic_kinds, f"accessories.yaml: a power of kind '{k}' has no handler in engine/relics.py")
    for k in sorted(relic_kinds):
        need(k in kinds_used, f"engine/relics.py handles a power kind '{k}' that no power in accessories.yaml uses")
    # summon forms
    forms = T.get("summons") or summons.FORMS
    form_keys = H.get("summons") or _read_keys(precise)              # read by name anywhere in the game's code
    AE = _load("data/rules/active_effects.yaml")
    summon_kinds = {k for k, v in (AE.get("kinds") or {}).items() if (v or {}).get("family") == "summon"}
    for form, row in forms.items():
        need(form in summon_kinds, f"summons.yaml forms.{form}: no summon kind of that name in active_effects.yaml")
        for key in (row or {}):
            need(key in form_keys, f"summons.yaml forms.{form}: the key '{key}' is one no game code reads")
    for k in sorted(summon_kinds):
        need(k in forms, f"active_effects.yaml kinds.{k}: a summon kind with no form in summons.yaml")
    # boss options
    BS = T.get("bosses") or _load("data/rules/bosses.yaml")
    boss_kinds = H.get("bosses") or _compared("engine/bosses.py", ("kind",))
    used = set()
    for kit, spec in (BS.get("kits") or {}).items():
        for opt in [spec.get("signature")] + list(spec.get("legendary") or []):
            if opt:
                used.add(opt.get("kind"))
                need(opt.get("kind") in boss_kinds, f"bosses.yaml kits.{kit}: an option of kind '{opt.get('kind')}' has no handler in engine/bosses.py _do")
    for k in sorted(boss_kinds):
        need(k in used, f"engine/bosses.py _do handles an option kind '{k}' that no kit in bosses.yaml uses")
    # martial maneuvers
    MT = T.get("martial") or martial.MANEUVERS
    man_keys = H.get("martial") or _read_keys(precise)
    statuses = set((_cb.RULES.get("statuses") or {}))
    for mid, row in MT.items():
        for key in (row or {}):
            need(key in man_keys, f"martial.yaml maneuvers.{mid}: the key '{key}' is one no game code reads")
        if (row or {}).get("status"):
            need(row["status"] in statuses, f"martial.yaml maneuvers.{mid}: status '{row['status']}' is no combat.yaml status")
    for m in sorted(H.get("martial_named") or _compared("engine/martial.py", ("maneuver", "mid", "man"))):
        need(m in MT, f"engine/martial.py names a maneuver '{m}' that martial.yaml does not have")
    # movement kinds
    MV = T.get("movement") or _load("data/rules/movement.yaml")
    move_kinds = H.get("movement") or _compared("engine/movement.py", ("kind",))
    for k in (MV.get("kinds") or {}):
        need(k in move_kinds, f"movement.yaml kinds.{k}: no handler in engine/movement.py")
    for k in sorted(move_kinds):
        need(k in (MV.get("kinds") or {}), f"engine/movement.py handles a movement kind '{k}' that movement.yaml does not name")
    # healing forms
    HL = T.get("healing") or _load("data/rules/healing.yaml")
    heal_forms = H.get("healing") or (_compared("engine/healing.py", ("form",)) | {"mend"})     # mend is the plain form, the else arm
    for f in (HL.get("forms") or {}):
        need(f in heal_forms, f"healing.yaml forms.{f}: no handler in engine/healing.py")
    for f in sorted(heal_forms):
        need(f in (HL.get("forms") or {}), f"engine/healing.py handles a healing form '{f}' that healing.yaml does not name")
    # passive mechanics (the refusal that lived at core/rules.py import)
    PM = T.get("mechanics") or rules.MECHANICS
    combat_set, world_set = H.get("mechanics_combat") or rules.ENGINE_COMBAT_MECHANICS, H.get("mechanics_world") or rules.ENGINE_WORLD_MECHANICS
    for m in PM.values():
        need(m.id in (combat_set if m.kind == "combat" else world_set), f"passive_mechanics.yaml {m.id}: the engine doesn't know how to run it")
    for mid in sorted((combat_set | world_set) - set(PM) - set(items.LEGENDARY)):
        need(False, f"core/rules.py names a mechanic '{mid}' that is neither a passive mechanic nor a legendary effect")
    return out


def assert_ok() -> None:
    bad = check()
    if bad:
        raise ValueError("The character data has problems:\n" + "\n".join(f"  - {b}" for b in bad))
