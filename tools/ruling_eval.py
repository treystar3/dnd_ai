"""(f395) How well the dungeon master rules, on the test set (data/replay/ruling_cases.yaml): the act's one ruling (engine/act.py),
the only path outside a fight; --path old is the ruling still asked on the road (engine/ruling.py ask).

    python tools/ruling_eval.py            offline: for every case with a `model` ruling, what the engine makes of it (its own grounds:
                                           what the character can do); the cases without one need the model and are counted, not run
    python tools/ruling_eval.py --live     the real model rules on every case (the game's own server, tools/runtime_cli.py): its sense against what a good dungeon
                                           master would say, and what it says the world needs
    python tools/ruling_eval.py --live --cases data/replay/ruling_cases_complex.yaml     (f534) the improvised actions of several steps
    python tools/ruling_eval.py --path old|both                    (f601) the old ruling instead, or both side by side:
                                           each scored on its sense alike (false acceptances, false rejections), with what the old
                                           one says the world needs and what the act's changes do apart; data/replay/ruling_cases_act.yaml
                                           holds the cases of things and of a situation's parts

A case may carry what it needs in the world (f601): `objects` lying where it is, `carried` things in hand (no item of the pack: only the
act's ruling sees them), `pack` goods in the pack (both see them), a `situation` with parts ({tier, people: [{here, stake, want, against}],
conditions: [{kind, label, by, by_kind, place}]}). Its line may name the situation's people as {person:<n>}; its `model` may name targets as
@object:<word>, @condition or @person:<n>; `moves` says, for each target named so, what the act should leave it as: a word, a list of
fair words (false among them: untouched too), {not: words}, or false (untouched).

(f616) A case may say what kind of act it is (`kind`, one of KINDS), and its kind decides what is fair. A `claim` is an act whose words
claim more than saying them could bring about (a title claimed, a crowd commanded, a person persuaded past reason): the corpus expects
a no, and on the act's path a yes or a cost that is bounded is right too, since its success goes no further than what it says it
comes to (`works`, f609) and it changes and makes nothing. The old ruling, whose success has no bound, is held to the no.

(f615) A case file with a line that repeats an example either ruling's prompt gives of a verdict (its `sense` lines: what is a yes,
a cost, a no) is refused, naming the line and the example: the corpus scores the verdict, so such a line scores the prompt. A line
repeats an example when it shares two or more content words with it, however the words are bent; an example of one word names a kind
of act (climbing), which the corpus is free to hold. The check is of words: a line that says the same in other words passes, and the
prompt's other examples (how to name a thing, what a change looks like) and the lists every request carries (capabilities, changes)
are the game's vocabulary, not examples of a verdict.

(f623) A case of kind `feat` says what a sensible table would name as the feat of the body (`feat`: "none", {kind, size: [low, high]},
or a list of fair answers) and the body it is tried with (`body`: one number for strength, dexterity and constitution, or some by
name). Its `expect` is what the body's table answers for that body: the table's arithmetic held still, not a ruling of the owner's.
(f624) A feat is a reading of its own, not a part of the ruling (engine/body.py reading). Offline the reading is the one the case's
`model` holds beside its ruling (`feat`), which must be one the case calls fair, or the file is refused. Live, no call reads a
feat yet, so a feat case is left unread and counted so: its `expect` is the table's answer to a reading. `named` scores a reading
against its case, for whatever measures one. `deadly: true`: the drop would kill that body, so in play it is warned of first and
then is a death; the measure holds the engine to saying so.

GOAL.md: "Investigate further into the cave" is met with more cave. "I grow wings and fly away" is not."""
from __future__ import annotations

import argparse
import os
import random
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml

CASES = ROOT / "data" / "replay" / "ruling_cases.yaml"
PATHS = ("old", "new")


KINDS = ("claim", "feat")                            # (f616) the kinds of act a case may say it is; each has its rule in side()
BODY = ("strength", "dexterity", "constitution")     # (f623) the attributes a case's `body` sets


def load(path=CASES) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


def problems(cases: list[dict]) -> list[str]:
    """(f616) What is wrong with a case file as a file: a kind this tool has no rule for, or a kind that contradicts what it expects."""
    out = []
    for c in cases:
        if "kind" in c and c["kind"] not in KINDS:
            out.append(f"\"{c['line']}\": kind {c['kind']!r} is not one of {', '.join(KINDS)}")
        if c.get("kind") == "claim" and c.get("expect") != "no":
            out.append(f"\"{c['line']}\": a claim expects a no (a bounded yes or cost is then right too)")
        if "bounded" in c:
            out.append(f"\"{c['line']}\": `bounded` is now the case's kind (kind: claim)")
        if c.get("kind") == "feat" or "feat" in c:        # (f623)
            from engine import body
            num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
            for a in fair_feats(c.get("feat")):
                if not (a == "none" or (isinstance(a, dict) and a.get("kind") in body.K and isinstance(a.get("size"), list)
                                        and len(a["size"]) == 2 and all(num(x) for x in a["size"]) and 0 < a["size"][0] < a["size"][1])):
                    out.append(f"\"{c['line']}\": feat is \"none\" or {{kind: one of {', '.join(body.K)}, size: [low, high]}}, or a list of them")
                    break
            else:
                try:
                    fair_own = "feat" not in (c.get("model") or {}) or named(c, reading(c)) == "ok"
                except ValueError:
                    fair_own = False
                if not fair_own:
                    out.append(f"\"{c['line']}\": its own reading names a feat the case does not call fair")
        if "deadly" in c and not (c.get("kind") == "feat" and isinstance(c["deadly"], bool)):
            out.append(f"\"{c['line']}\": deadly is true or false, on a feat case")
        if "body" in c and not (isinstance(c["body"], int) and c["body"] > 0
                                or isinstance(c["body"], dict) and c["body"] and set(c["body"]) <= set(BODY)):
            out.append(f"\"{c['line']}\": body is one number, or some of {', '.join(BODY)} by name")
    return out


def fair_feats(spec) -> list:
    return spec if isinstance(spec, list) else [spec]


def reading(case: dict):
    """(f624) The reading a case's own `model` holds beside its ruling: what the table is handed offline. No feat where it holds none."""
    from engine import body
    own = (case.get("model") or {}).get("feat") or {}
    return body.read(own.get("kind", "none"), own.get("size", 0))


def unread(case: dict, live: bool) -> bool:
    """(f624) Whether a case cannot be scored this way: a feat case live, since no call reads a feat and its `expect` answers a reading."""
    return bool(live and case.get("kind") == "feat")


def named(case: dict, feat) -> str | None:
    """(f623) A reading against what the case says a sensible table would name: "ok"; "kind" (another kind, or a feat where there
    is none); "size" (the kind right, the size outside its range). None when the case says nothing of it."""
    if "feat" not in case:
        return None
    kind, size = feat.kind, float(feat.size or 0)
    out = "kind"
    for a in fair_feats(case["feat"]):
        if a == "none":
            if kind == "none":
                return "ok"
        elif a["kind"] == kind:
            if a["size"][0] <= size <= a["size"][1]:
                return "ok"
            out = "size"
    return out


# (f615) The small words of the language, which say nothing of what an act is: never counted as shared.
SMALL = frozenset("""the and but for nor yet from with without into onto over under down off out all any one what which who whom whose that
this these those they them their there here then than when where while have has had does did done can could will would may might must shall
should are was were been being its his her him she you your our come comes came get gets got try tries""".split())
# ...and the verbs whose past is another word, each as its plain form.
BENT = {"made": "make", "broke": "break", "broken": "break", "lit": "light", "won": "win", "sat": "sit", "swam": "swim", "swum": "swim",
        "dug": "dig", "ran": "run", "went": "go", "gone": "go", "took": "take", "taken": "take", "gave": "give", "given": "give",
        "said": "say", "told": "tell", "found": "find", "held": "hold", "left": "leave", "lost": "lose", "brought": "bring",
        "bought": "buy", "sold": "sell", "thought": "think", "caught": "catch", "threw": "throw", "thrown": "throw", "stole": "steal",
        "stolen": "steal", "hid": "hide", "hidden": "hide", "rose": "rise", "risen": "rise", "fell": "fall", "fallen": "fall",
        "drew": "draw", "drawn": "draw", "sang": "sing", "sung": "sing", "spoke": "speak", "spoken": "speak", "wrote": "write",
        "written": "write", "flew": "fly", "flown": "fly", "grew": "grow", "grown": "grow", "knew": "know", "known": "know",
        "saw": "see", "seen": "see", "ate": "eat", "eaten": "eat", "drank": "drink", "drunk": "drink", "built": "build",
        "sent": "send", "kept": "keep", "slept": "sleep", "fought": "fight", "stood": "stand", "struck": "strike", "woke": "wake"}


def stems(text: str) -> set[str]:
    """The content words of a text, each cut to its stem: summoning and summon, conjuring and conjure, digging and dig, made and make."""
    out = set()
    for w in re.findall(r"[a-z]+", text.lower()):
        w = BENT.get(w, w)
        if len(w) < 3 or w in SMALL:
            continue
        for end in ("ing", "ed", "es", "s"):
            if w.endswith(end) and len(w) - len(end) >= 3:
                w = w[:-len(end)]
                if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "aeiouls":    # digging, barred, sitting: the doubled letter
                    w = w[:-1]
                break
        out.add(w[:-1] if w.endswith("e") and len(w) > 3 else w)
    return out


def examples(prompt: str) -> list[str]:
    """The examples a prompt gives of a verdict: what stands in brackets in its `sense` lines, each item of each list."""
    m = re.search(r"\n\s*sense:(.*?)\n\s*why:", prompt, re.S)
    return [x.strip() for group in re.findall(r"\(([^()]*)\)", " ".join(m.group(1).split()) if m else "") for x in group.split(",") if x.strip()]


def prompts() -> dict[str, str]:
    """The prompts the corpus measures a model under: the act's one ruling, and the road's."""
    from engine import act, ruling
    return {"the act's ruling": act.SYSTEM, "the road's ruling": ruling.SYSTEM}


def taught(cases: list[dict], under: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    """(f615) The lines that repeat a prompt's example of a verdict, each (line, prompt, example): two or more content words shared."""
    out = []
    for name, prompt in (prompts() if under is None else under).items():
        marks = [(ex, stems(ex)) for ex in examples(prompt)]
        for c in cases:
            have = stems(c["line"])
            out += [(c["line"], name, ex) for ex, st in marks if len(st & have) >= 2]
    return out


class Dry:
    """(f619) The scene as the engine's writers may read it, for a dry run: its people the store's own copies (never the scene's), and
    nothing saved. A store call it does not know stops the run, so a write added to a writer cannot slip into the measure's world."""
    READS = frozenset({"npc_exists", "load_npc", "meta"})
    WRITES = frozenset({"save_npc", "set_memory_state"})

    class Store:
        def __init__(self, store):
            self._store = store

        def __getattr__(self, name):
            if name in Dry.WRITES:
                return lambda *a, **k: None
            if name in Dry.READS:
                return getattr(self._store, name)
            raise AttributeError(f"the dry run met a store call it does not know ({name}): say in tools/ruling_eval.py Dry whether it reads or writes")

    def __init__(self, ws):
        self.minutes, self.world, self.player, self.acting, self.present = ws.minutes, ws.world, ws.player, ws.acting, list(ws.present)
        self.store = Dry.Store(ws.store)


class Bench:
    def __init__(self, live: bool = False, save: str = "ruling_eval", source=None, ruled=("Ruling", "ActRuling")):
        import simlib
        from llm import backend
        self.stub = simlib.Stub("warrior", 4)
        self.unstub = simlib.install(self.stub)              # (f518) the stub as the model's source; its Held takes it away again
        self.unlive = None
        if live:                                             # (f518) the titles in `ruled` are passed on to the real model (f529: the server `source`); the rest stays stubbed
            stub_chat = self.stub.chat
            self.unlive = simlib.stand_in(chat=lambda **k: backend.PASS if (k.get("format") or {}).get("title") in ruled else stub_chat(**k),
                                          name="ruling_eval live", below=source)
        import config
        import ui.console as uc
        for f in ("narrate", "say", "npc_says", "dialogue", "ledger", "note"):
            setattr(uc, f, lambda *a, **k: None)
        config.AUDIT_ENABLED = False
        config.REFUSALS_LOG = False
        from engine.session import CampaignSession
        from npc.traits import load_traits
        from storage.campaign import PlayerState
        self.save = save
        shutil.rmtree(ROOT / "saves" / save, ignore_errors=True)
        self.session = CampaignSession.open(save)                           # (f457) the campaign's session, as main.py opens it
        self.store, self.world = self.session.store, self.session.world
        self.store.meta.seed = 4; self.store.meta.minutes = 720; self.store.save_meta()
        char, _ = simlib.make_character("warrior", random.Random(1))
        char.level = 10
        self.store.save_player(PlayerState(character=char, location="trading_square"))
        self.ws = self.session.scene(load_traits(), self.store.load_player())
        self.ws.player.mentor["never"] = True
        self.pack = list(self.ws.player.character.inventory)  # (f601) the pack as it starts: each case's goods on top, taken off after
        self.attrs = {a: getattr(self.ws.player.character.attributes, a) for a in BODY}   # (f623) the body as it starts, for a case that sets none
        self.made: list[str] = []                            # (f601) what a case put in the world, taken away after it
        self.sit = ""
        self.names: list[str] = []
        self.was_present = None
        self.n = 0
        self.last = None                                     # (f610) the act's ruling and the engine's check of the case just ruled

    def put(self, case: dict) -> None:
        from engine import inventory
        ws = self.ws
        self.last = None
        self.clear()                                         # (f601) the last case's world first, then the move
        if ws.player.location != case["at"]:
            ws.enter(case["at"])
        ws.player.character.capabilities = list(case.get("means") or [])
        spec = case.get("body")                              # (f623) the body the case is tried with
        for a in BODY:
            setattr(ws.player.character.attributes, a, int(spec if isinstance(spec, int) else (spec or {}).get(a, self.attrs[a])))
        ws.player.character.inventory = list(self.pack) + [inventory.make_good(g) for g in case.get("pack") or ()]
        if case.get("objects") or case.get("carried") or case.get("situation"):
            self.furnish(case)

    def line(self, case: dict) -> str:
        """(f601) The case's line, its {person:<n>} the situation's people by name, as the player would name them."""
        out = case["line"]
        for i, name in enumerate(self.names, 1):
            out = out.replace(f"{{person:{i}}}", name)
        return out

    def furnish(self, case: dict) -> None:
        """(f601) The things and the situation a case needs, in one operation of the scene's own."""
        from engine import objects
        ws, store = self.ws, self.store
        with ws.operation("ruling_eval", "a case's world") as op:
            for name in case.get("objects") or ():
                self.made.append(objects.make(store, case["at"], name, minute=ws.minutes).ref)
            for name in case.get("carried") or ():
                e = objects.make(store, case["at"], name, minute=ws.minutes)
                self.made.append(e.ref)
                why = objects.take(store, e, ws.acting, ws.minutes)
                if why:
                    raise RuntimeError(f"{name} cannot be carried ({why}): {case['line']}")
            if case.get("situation"):
                self.situate(case)
        if op.state != "committed":
            raise RuntimeError(f"the case's world did not stand: {case['line']}")

    def situate(self, case: dict) -> None:
        from engine import pulse, retrieval, situation_parts, situations
        from llm.contracts import SituationParts
        ws, store, world = self.ws, self.store, self.world
        spec = case["situation"]
        town = pulse.town_of(world, case["at"])
        if not ws.residents:
            ws.enter(case["at"])                             # (f601) its people, as the game's own arrival makes them
        folk = retrieval.people_in_town(store, world, town)
        if not ws.present:                                   # (f601) someone there: the place's own people, for this case
            self.was_present = []
            away = sum(1 for x in spec.get("people") or () if not x.get("here", True))
            ws.present = list(ws.residents[:max(1, len(ws.residents) - away)][:3])   # (f601) one held out for each away
        here = {n.id for n in ws.present}
        near = [n for n in ws.present]
        far = [n for n in folk if n.id not in here]
        people = []
        for p in spec.get("people") or ():
            pool = near if p.get("here", True) else far
            who = next((n.id for n in pool if n.id not in {x["who"] for x in people}), None)
            if who is None:
                raise RuntimeError(f"no one to stand in the case's situation: {case['line']}")
            people.append({"who": who, "stake": p["stake"], "want": p["want"]})
        conds = [{**{k: v for k, v in c.items() if k != "place"}, "on": c.get("place") or case["at"]} for c in spec.get("conditions") or ()]
        self.n += 1
        self.sit = f"ruling_eval_{self.n}"
        state = store.load_world_state() or {}
        for k, v in pulse.empty_state(ws.minutes).items():
            state.setdefault(k, v)
        tier = spec.get("tier", "normal")
        th = {"id": self.sit, "title": spec.get("title", "Trouble"), "tier": tier, "place": case["at"], "times": [ws.minutes, ws.minutes + 9 * 1440],
              "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Trouble.", "effects": []}],
              "kind": spec.get("kind", "unrest"), "groups": ["everyone"], "fallout": {"description": "It runs its course.", "effects": []}}
        state.setdefault("threads", []).append(th)
        acc, _ = situations.check(SituationParts.model_validate({"people": people, "conditions": conds}), store, world, tier, random.Random(7),
                                  town=town, ways=False, now=ws.minutes, players=(ws.acting,))
        situation_parts.register(store, world, state, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
        mine = [a for a in th["parts"] if a.get("kind") == "person"]
        if [a["who"] for a in mine] != [p["who"] for p in people]:
            raise RuntimeError(f"the case's people did not all stand: {case['line']}")
        if [(a.get("on"), a.get("label")) for a in th["parts"] if a.get("kind") == "condition"] != [(c["on"], c["label"]) for c in conds]:
            raise RuntimeError(f"the case's conditions did not stand as written: {case['line']}")
        for p, a in zip(spec.get("people") or (), mine):
            if p.get("against"):
                a.setdefault("willing", {})[ws.acting] = p["against"]
        self.names = [store.load_npc(a["who"]).name for a in mine]
        store.save_world_state(state)

    def clear(self) -> None:
        """(f601) The last case's things and situation gone, and what the situation laid on the world with it, so no case sees another's."""
        if self.was_present is not None:
            self.ws.present, self.was_present = self.was_present, None
        self.names = []
        if not (self.made or self.sit):
            return
        from engine import pulse
        with self.ws.operation("ruling_eval", "a case's world cleared"):
            for ref in self.made:
                self.store.delete_entity(ref)
            if self.sit:
                state = self.store.load_world_state() or {}
                th = pulse.thread_of(state, self.sit)
                if th is not None:
                    pulse.end_thread(self.store, state, th, "resolved", "", self.ws.minutes)
                    self.store.save_world_state(state)
        self.made, self.sit = [], ""

    def targets(self):
        from engine import targets
        return targets.targets_for(self.ws, self.ws.acting)

    def resolve(self, code: str, T) -> str:
        """(f601) A case's @name for a target, as the scene codes it now."""
        if not isinstance(code, str) or not code.startswith("@"):
            return code
        kind, _, word = code[1:].partition(":")
        rows = [t for t in T.rows if t.kind == kind and (kind not in ("condition", "person") or t.ref.startswith(self.sit + "#"))]
        if kind == "object":
            rows = [t for t in rows if word.lower() in t.line.lower()]
        elif word:
            rows = rows[int(word) - 1:int(word)]
        if not rows:
            raise RuntimeError(f"no target for {code}: {[t.line for t in T.rows]}")
        return rows[0].code

    def act_model(self, case: dict, T):
        from engine import act
        from llm.contracts import ActRuling
        m = dict(case["model"])
        m["uses"] = [self.resolve(u, T) for u in m.get("uses") or ()]
        m["changes"] = [{**ch, **{k: self.resolve(ch[k], T) for k in ("target", "who", "about", "to") if ch.get(k)}}
                        for ch in m.get("changes") or ()]
        return ActRuling.model_validate({"answer": "x", **m}, context=act.context(self.ws, T))

    def moved(self, case: dict, T, v) -> bool | None:
        """(f601) Whether what the act leaves each named target as is what the case says (by target, never by the ruling's own numbering,
        so a live ruling is measured too): (f619) its kept changes and what follows from them, which is the engine's to say and no
        ruling's. None when the case says nothing of it."""
        if "moves" not in case:
            return None
        kept = v.ruling.changes if v.ok else []
        after = self.follows(T, v) if kept else {}
        for name, want in case["moves"].items():
            code = self.resolve(name, T)
            got = {ch.becomes for ch in kept if (T.get(ch.target) and T.get(ch.target).code) == code} | after.get(code, set())
            if not fair(want, got):
                return False
        return True

    def follows(self, T, v) -> dict[str, set]:
        """(f619) What would follow from the act's kept changes were it to succeed, by target: the engine's own writers
        (situation_parts.keep_changes, follow) run on a copy of each situation with a scene that never writes (Dry)."""
        import copy
        from engine import act, situation_parts
        state = copy.deepcopy(self.store.load_world_state() or {})
        dry = Dry(self.ws)
        sits: dict[str, list] = {}
        for ch in v.ruling.changes:
            t = T.get(ch.target)
            if t is not None and t.code.startswith("s") and "." in t.code:
                sits.setdefault(t.code.split(".")[0], []).append(ch)
        out: dict[str, set] = {}
        for scode, chs in sits.items():
            th = next((x for x in state.get("threads", []) if x["id"] == T.get(scode).ref), None)
            if th is None:
                continue
            situation_parts.keep_changes(dry, state, th, act.acted(self.ws, self.ws.acting), act.part_rows(scode, chs, v.ruling.stakes.check))
            for i, word in situation_parts.follow(dry.store, state, th, self.ws.minutes):
                if word:
                    out.setdefault(f"{scode}.{i + 1}", set()).add(word)
        return out

    def offline(self, case: dict, path: str = "old"):
        """What the engine makes of the case's own ruling: 'yes' or 'no', and on the new path whether its changes do what the case says
        (None for that when it says nothing); None when the case has no ruling."""
        from engine import ruling
        from llm.contracts import Ruling
        if not case.get("model"):
            return None
        self.put(case)
        if path == "new":
            from engine import act
            T = self.targets()
            v = act.validate(self.ws, self.ws.acting, T, self.act_model(case, T), reading(case))
            self.last = v
            return ("yes" if v.ok else "no"), self.moved(case, T, v)
        m = {k: v for k, v in case["model"].items() if k in ("sense", "requires", "why", "needs", "stakes")}   # the old path makes no changes
        r = Ruling.model_validate({"answer": "x", **m}, context={"capabilities": list(ruling.C)})
        return "yes" if self.road(r, reading(case)) else "no"

    def road(self, r, feat=None) -> bool:
        """(f623) The road's ruling as the game takes it: the engine's own grounds, then what lacking a power and what a body mean."""
        from engine import ruling
        return bool(ruling.verdict(self.ws, r)["ok"]) and ruling.settled(self.ws, self.ws.acting, r, feat).sense != "no"

    def live(self, case: dict, path: str = "old"):
        """The model's ruling and the engine's yes or no; on the new path also whether its changes do what the case says."""
        from engine import ruling
        self.put(case)
        line = self.line(case)
        if path == "new":
            from engine import act
            T = self.targets()
            r = act.ask(self.ws, self.ws.acting, T, line, line)
            if r is None:
                return None, None, None
            v = act.validate(self.ws, self.ws.acting, T, r)
            self.last = v
            return r, ("yes" if v.ok else "no"), self.moved(case, T, v)
        r = ruling.ask(self.ws, line, line)
        if r is None:
            return None, None, None
        return r, ("yes" if self.road(r) else "no"), None

    def bounded(self, case: dict) -> bool:
        """(f610, f616) Whether the act's ruling just made is bounded, on a case whose kind allows that (a claim): it stands, as a yes or
        a cost, says what it comes to, and changes and makes nothing (a need that stands is made real before the roll)."""
        v = self.last
        return bool(case.get("kind") == "claim" and v is not None and v.ok and (v.ruling.works or "").strip()
                    and not v.ruling.changes and not v.ruling.needs)

    def close(self) -> None:
        self.session.close()
        if self.unlive is not None:
            self.unlive()                   # (f518) this bench's stand-ins away again, the live route first
        self.unstub()
        shutil.rmtree(ROOT / "saves" / self.save, ignore_errors=True)


def fair(want, got: set) -> bool:
    """(f607) What a case allows a target to become: one word (exactly that), a list (one or more of them, nothing else; with false among
    them, untouched too: f611), {not: words} (anything but these, untouched included), or false (untouched)."""
    if want is False:
        return not got
    if isinstance(want, dict):
        if set(want) != {"not"} or not isinstance(want["not"], list):
            raise ValueError(f"a case's moves is a word, a list of words, {{not: [words]}} or false, not {want!r}")
        return not got & set(want["not"])
    if isinstance(want, list):
        return (bool(got) or False in want) and got <= {w for w in want if w is not False}
    return got == {want}


class Tally:
    """(f601) One path's score, its sense alike for both: right, a no taken for a yes (a false acceptance), a yes refused (a false
    rejection), no ruling; and apart, what the old one says the world needs and what the act's changes do, where the case says."""
    def __init__(self):
        self.right = self.accepted = self.rejected = self.none = 0
        self.needs_missed = self.changes_wrong = self.known = self.retire = 0
        self.deadly_wrong = 0                                # (f623) a drop the engine did not call deadly as its case does
        self.unread = 0                                      # (f624) feat cases left unread: no call reads a feat

    def add(self, want: str, got: str | None, needs_ok: bool | None = None, moves_ok: bool | None = None, known: bool = False) -> bool:
        if got is None:
            self.none += 1
            return False
        if known and got == want and needs_ok is not False:  # (f601) the decided gap alone: the sense right, only the changes off
            if moves_ok is False:
                self.known += 1
                return False
            self.retire += 1                                  # (f601) the engine now does what was decided: the label is retired
        if got == want:
            self.right += 1
        elif want == "no":
            self.accepted += 1
        else:
            self.rejected += 1
        self.needs_missed += needs_ok is False
        self.changes_wrong += got == want and moves_ok is False   # (f601) a refused act changes nothing: counted once, as refused
        return got == want and needs_ok is not False and moves_ok is not False

    @property
    def wrong(self) -> int:
        return self.accepted + self.rejected + self.changes_wrong + self.retire + self.deadly_wrong

    def line(self, path: str, live: bool) -> str:
        return (f"{path}: {self.right} of {self.right + self.accepted + self.rejected} right; false acceptances {self.accepted}, "
                f"false rejections {self.rejected}" + (f"; needs missed {self.needs_missed}" if path == "old" and live else "")
                + (f"; changes wrong {self.changes_wrong}" if path == "new" else "")
                + (f"; {self.known} known, awaiting their feature" if self.known else "")
                + (f"; {self.retire} known now right: retire the label" if self.retire else "")
                + (f"; {self.none} with no ruling" if live else f"; {self.none} need the model")
                + (f"; deadly drops wrong {self.deadly_wrong}" if self.deadly_wrong else "")
                + (f"; {self.unread} feat cases unread (no call reads a feat)" if self.unread else ""))


def judge(b: Bench, c: dict, live: bool) -> tuple[str | None, bool, str]:
    """The old path, as it always scored: what it got, whether that is right (live: and the needs it named), and how to show it."""
    want = "no" if c["expect"] == "no" else "yes"
    if live:
        r, got, _ = b.live(c, "old")
        if got is None:
            return None, False, "?"
        needs = sorted({n.kind for n in r.needs})
        ok = got == want and (want == "no" or set(c.get("needs") or []) <= set(needs) or not c.get("needs"))
        return got, ok, f"{r.sense}{' (engine: no)' if got == 'no' and r.sense != 'no' else ''}, needs {needs or '-'}"
    got = b.offline(c, "old")
    return got, got == want, got or "-"


def side(b: Bench, c: dict, path: str, live: bool, tally: Tally) -> str:
    """(f601) One case on one path, scored on its sense alike, with the needs (old) and the changes (new) apart: how to show it."""
    want = "no" if c["expect"] == "no" else "yes"
    needs_ok = moves_ok = None
    if unread(c, live):                                  # (f624) its `expect` answers a reading, and none is made
        tally.unread += 1
        return f"{path} --  {'unread':<20}"
    if live:
        r, got, moves_ok = b.live(c, path)
        if r is not None and path == "old" and want != "no" and c.get("needs"):
            needs_ok = set(c["needs"]) <= {n.kind for n in r.needs}
        shown = "?" if r is None else f"{r.sense}{' (engine: no)' if got == 'no' and r.sense != 'no' else ''}"
    else:
        out = b.offline(c, path)
        got, moves_ok = (out if path == "new" and out is not None else (out, None))
        shown = got or "-"
    if path == "new" and c.get("kind") == "feat" and b.last is not None:   # (f623) a deadly drop, as its case says
        if bool(c.get("deadly")) != bool(b.last.deadly):
            tally.deadly_wrong += 1
            shown += ", deadly WRONG"
        elif b.last.deadly:
            shown += ", deadly: warned, then a death"
    if path == "new" and want == "no" and got == "yes" and b.bounded(c):   # (f610, f616) a claim, its success no further than its ruling
        want, shown = "yes", f"{b.last.ruling.sense}, bounded"
    if path == "new" and got == "yes" and getattr(b.last, "without", ""):  # (f618) done without a power, on what stands in for it
        shown += f", without {b.last.without}"
    known, retire = tally.known, tally.retire
    ok = tally.add(want, got, needs_ok, moves_ok, known=bool(c.get("known")) and path == "new")   # (f601) the gap is the act engine's
    shown += {True: ", moves ok", False: ", moves WRONG"}.get(moves_ok, "") + (", needs missed" if needs_ok is False else "")
    mark = "?  " if got is None else ("KNW" if tally.known > known else ("OLD" if tally.retire > retire else ("ok " if ok else "BAD")))
    return f"{path} {mark} {shown:<20}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--cases", default=str(CASES), help="(f534) another case file, e.g. data/replay/ruling_cases_complex.yaml")
    ap.add_argument("--path", default="new", choices=("old", "new", "both"),
                    help="(f608) the act's ruling (as the game rules), the old one (the road's), or both side by side")
    from tools import runtime_cli
    runtime_cli.add_args(ap)
    a = ap.parse_args()
    cases = load(a.cases)
    found = taught(cases)                                       # (f615) a line that repeats a prompt's example scores the prompt
    wrong_file = problems(cases) + [f"\"{line}\" repeats an example of {name}'s prompt (\"{ex}\")" for line, name, ex in found]
    if wrong_file:
        for x in wrong_file:
            print(f"REFUSED {a.cases}: {x}", file=sys.stderr)
        return 2
    paths = PATHS if a.path == "both" else (a.path,)
    server = runtime_cli.load(a) if a.live else None            # (f529) the game's own server, as the game starts it
    b = Bench(live=a.live, source=server.source if server is not None else None,
              save=f"ruling_eval_{os.getpid()}")   # (f610) its own save: the suite runs several at once
    tally = {p: Tally() for p in paths}
    right = wrong = skipped = 0
    try:
        for c in cases:
            want = "no" if c["expect"] == "no" else "yes"
            if a.path == "old":                                  # (f395) the old path's output, as it always read
                if unread(c, a.live):                            # (f624)
                    print(f"  --   {c['line']}  (a feat case: no call reads a feat)")
                    skipped += 1
                    continue
                got, ok, shown = judge(b, c, a.live)
                if got is None:
                    if a.live:
                        print(f"  ?    {c['line']}  (the model gave no ruling)")
                    skipped += 1
                    continue
                if a.live:
                    print(f"  {'ok ' if ok else 'BAD'}  {b.line(c)}  -> {shown}"
                          + (f"  [wanted {c['expect']}, needs {c.get('needs') or '-'}]" if not ok else ""))
                else:
                    print(f"  {'ok ' if ok else 'BAD'}  {b.line(c)}  (means: {c.get('means') or 'none'}) -> {got}" + (f"  [wanted {want}]" if not ok else ""))
                right += ok
                wrong += not ok
                continue
            cells = [side(b, c, p, a.live, tally[p]) for p in paths]
            print(f"  {' | '.join(cells)}  {b.line(c)}  [wanted {c['expect']}" + (f", moves {c['moves']}" if "moves" in c else "") + "]"
                  + (f"\n        known: {c['known']}" if c.get("known") else ""))
    finally:
        b.clear()
        b.close()
        if server is not None:
            server.close()
    if a.path == "old":
        print(f"\n{right} of {right + wrong} right" + (f"; {skipped} need the model (--live)" if skipped and not a.live else "")
              + (f"; {skipped} with no ruling" if skipped and a.live else ""))
        return 0 if not wrong or a.live else 1
    print()
    for p in paths:
        print(tally[p].line(p, a.live))
    return 0 if a.live or not any(t.wrong for t in tally.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
