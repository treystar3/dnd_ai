"""Live check against the real model (Ollama must be running with the game's model). Not part of the suite: it needs the model.

  python tools/live_check.py                    every scenario, independent runs (default --runs 3)
  python tools/live_check.py --runs 5
  python tools/live_check.py --mode continuity  the same questions asked again and again in one sitting: does she remember being asked?
  python tools/live_check.py --mode both
  python tools/live_check.py --vary             run 1 is the usual Bram and Isel; every later run gives them a different personality
                                                (temperaments, motive, habit, flaw, details), the same ones every time you use --vary

Independent runs reset what each character has said before every run, so the runs are separate samples of the model's variety.
Continuity runs keep everything, so repetition and "I already told you" are expected and judged as continuity, not as sameness.

Writes saves/live_check_report.md: every exchange as said, whether it came from the model or the written fallback, each refusal reason, every
model call's time, flags from a model judge (claims about the place nobody gave, archetype tics, objective-pushing, voices broken), and notes on
the same thing said across independent runs.
Nothing in a real save is touched."""
import argparse, collections, random, re, shutil, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
import llm.gateway as gw
import ui.console as uc

ap = argparse.ArgumentParser()
ap.add_argument("--runs", type=int, default=3)
ap.add_argument("--mode", choices=["independent", "continuity", "both"], default="independent")
ap.add_argument("--model", default="", help="run the game's characters on this model instead of config.MODEL (config.py is not changed)")
ap.add_argument("--report", default="live_check_report.md", help="the report's file name, in saves/")
ap.add_argument("--vary", action="store_true", help="a different personality pair for each run after the first (repeatable)")
ap.add_argument("--judge-model", default="", help="judge with this model instead of the game's (keeps the judge the same while comparing game models)")
args = ap.parse_args()
if args.model:
    config.MODEL = args.model

SAID, CALLS, REFUSED = [], [], []
uc.say = lambda t, s="": SAID.append((s or "", t))
uc.narrate = lambda t: SAID.append(("(narration)", t))
uc.note = lambda m, *a, **k: SAID.append(("(game)", str(m)))          # what the game tells the player, shown so a scene with no talk is still readable

real_chat = gw._client.chat
def timed_chat(**k):
    msgs = k.get("messages", [])
    if len(msgs) > 2 and "rejected" in msgs[-1].get("content", ""):
        why = msgs[-1]["content"].split("\n")[0][:200]
        raw = " ".join(str(msgs[-2].get("content", "")).split())[:400] if msgs[-2].get("role") == "assistant" else ""
        REFUSED.append(why + (f"\n    - the refused answer: {raw}" if raw else ""))
    t0 = time.time()
    try:
        r = real_chat(**k)
        CALLS.append((k.get("format", {}).get("title", "?"), time.time() - t0, True))
        return r
    except Exception:
        CALLS.append((k.get("format", {}).get("title", "?"), time.time() - t0, False))
        raise
gw._client.chat = timed_chat

try:
    if hasattr(gw._client, "list"):
        gw._client.list()
except Exception as e:
    sys.exit(f"Cannot reach Ollama ({e}). Start it, make sure the game's model '{config.MODEL}' is pulled, and run this again.")

import simlib
from engine import banter, mentor, quirks
from engine import party as rules
from npc.models import NPC
from npc.traits import load_traits
from scenes.world import WorldScene
from scenes.banter_actions import BanterActions
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

NAME = "live_check"
shutil.rmtree(ROOT / "saves" / NAME, ignore_errors=True)
store = CampaignStore.open_or_create(NAME)
store.meta.seed = 11; store.meta.turn = 1; store.meta.minutes = 1800; store.save_meta()
_real_client = gw._client                          # the test character is built the same way every time, without the model under test
simlib.install(simlib.Stub("warrior", 3))
ch, _ = simlib.make_character("warrior", random.Random(2))
gw._client = _real_client
store.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(store, load_world(), load_traits(), store.load_player())
config.TURN_LOG_PATH = str(ROOT / "saves" / NAME / "turns.jsonl")

FALLBACKS = gw.FALLBACKS          # the gateway records every call that gave up and left its caller to written lines, for every speaker

from pydantic import BaseModel
from llm.gateway import generate, LLMError


class Judgement(BaseModel):
    """A second reading of what the characters said, by the model itself, in place of word lists."""
    invented_place: bool = False          # someone states a fact about the place (its people, crime, history, buildings) that was not given
    pushes_objective: bool = False        # an answer to an unrelated or personal question ends by pushing the next task or command
    archetype_tic: bool = False           # a speaker makes their own temperament the subject (preaching faith, counting coin) unprompted
    out_of_voice: bool = False            # a speaker breaks their own given way of talking
    stock_phrase: bool = False            # prose: a stock phrase or ready-made fantasy wisdom
    flat: bool = False                    # prose: could be said by anyone, or reads as facts assembled into sentences
    vivid: bool = False                   # prose: at least one specific, particular detail only this person would say
    note: str = ""


JUDGE_SYSTEM = (
    "You review a few lines of dialogue from a fantasy game for a developer. You are given the place, exactly what was asked or what was "
    "happening, each speaker's own way of talking and their own life, and the lines. Judge only these lines, strictly but fairly:\n"
    "invented_place: does anyone state a fact about the place itself (its people, its crime, its buildings, its history) that was not given? "
    "A figure of speech, a feeling, or a person's own body (\"my side is screaming\") is not a claim about the place.\n"
    "pushes_objective: when the question was personal or unrelated to the task, does the answer end by pushing the next task or a command?\n"
    "archetype_tic: does a speaker, unprompted, make their own temperament the subject (preaching faith, counting coin, boasting toughness) "
    "instead of reacting to the moment? Answering a question about themselves, by talking about themselves, is NOT a tic.\n"
    "out_of_voice: does a speaker break the way of talking given for THAT speaker? Judge each speaker only against their own way of talking. "
    "A way of talking describes tendencies: leaving out an optional habit (a curse, an oath, a word of their home tongue) in a line is never a "
    "break; only doing the opposite of what is given is.\n"
    "stock_phrase: does any line lean on a stock phrase or ready-made fantasy wisdom (a heavy burden, the path ahead, stand your ground)?\n"
    "flat: is the dialogue generic, something anyone could say, or does it read like given facts assembled into sentences?\n"
    "vivid: does at least one line carry a specific, particular detail or turn of phrase that only this person would say?\n"
    "note: one short sentence on the most important real problem, or empty.\n"
    'Respond only with JSON: {"invented_place": false, "pushes_objective": false, "archetype_tic": false, "out_of_voice": false, '
    '"stock_phrase": false, "flat": false, "vivid": false, "note": ""}'
)
PROSE = collections.Counter()


def judge(title: str, lines: list[tuple[str, str]], voices: dict[str, str], selves: dict[str, str] | None = None) -> Judgement | None:
    if not lines:
        return None
    asked = title.split(": ", 1)[1] if ": " in title and "?" in title else ""
    req = (f"PLACE: {w.place.name}, " + ", ".join(list(getattr(w.place, "visible", []) or [])[:6]) +
           (f"\nTHE PLAYER ASKED: {asked}" if asked else "") + f"\nWHAT WAS HAPPENING: {title}\nEACH SPEAKER'S OWN WAY OF TALKING:\n" + ("\n".join(f"  {k}: {v}" for k, v in voices.items()) or "  (none given)") +
           ("\nEACH SPEAKER'S OWN LIFE (theirs to speak of; a place named here is given, not invented):\n" + "\n".join(f"  {k}: {v}" for k, v in selves.items() if v)
            if selves and any(selves.values()) else "") +
           "\nLINES:\n" + "\n".join(f"  {who}: {' '.join(t.split())}" for who, t in lines))
    try:
        game_model = config.MODEL
        if args.judge_model:
            config.MODEL = args.judge_model
        try:
            return generate("live_judge", JUDGE_SYSTEM, req, Judgement, temperature=0.1, max_tokens=160, retries=1)
        finally:
            config.MODEL = game_model
    except LLMError:
        return None


from llm import embed as _embed
from llm import setup_check as _sc
if getattr(config, "EMBED_ENABLED", True) and hasattr(gw._client, "embed") and not _sc.model_present(config.EMBED_MODEL):
    print(f"Fetching the helper model {config.EMBED_MODEL} (about 270 MB) first...")
    try:
        _sc.pull_model(lambda f, t: None, name=config.EMBED_MODEL)
    except Exception as e:
        print(f"  could not fetch it ({e}); the word checks will be used")
out = ["# Live check against the real model", f"Helper model for meaning ({config.EMBED_MODEL}): {'in use' if _embed.available() else 'NOT available - the word checks were used'}", f"Model: {config.MODEL}  ·  runs per scenario: {args.runs}  ·  mode: {args.mode}" + ("  ·  personalities vary by run" if args.vary else ""), ""]
flags = []
notes = []
CANON_TALLY = collections.Counter()
guarded = []
FIXED = set()
JUDGE_LATER = []
lines_by = collections.defaultdict(list)            # (mode, title, speaker) -> lines across runs, for saturation and sameness

FRESH = tuple(__import__("engine.canon", fromlist=["HELD"]).HELD) + ("convo", "raised", "topics_used", "heavy_at", "_culture_key", "_culture", "banter_at", "started_at", "hit_by", "mood_for")   # what a speaker has accumulated in play: a separate game starts without it


def reset_state():
    """Independent runs: each is a separate game. Nobody has said anything yet, been asked anything, or said anything about themselves."""
    w.player.mentor["chat"], w.player.mentor["gestured"] = [], []
    for k in FRESH:
        w.player.mentor.pop(k, None)
    for m in w.player.party:
        m["said"], m["talk"], m["gestured"] = [], [], []
        for k in FRESH:
            m.pop(k, None)

# ---------- progress: how far along, and roughly how long is left (from the last run's timings when there was one) ----------
import json as _json
LAST = ROOT / "saves" / "live_check_last.json"
try:
    _last = _json.loads(LAST.read_text(encoding="utf-8"))
except (OSError, ValueError):
    _last = {}
PROG = {"done": 0, "per_mode": _last.get("per_mode", 24), "secs": _last.get("secs_per", 0.0), "t0": time.time(), "seen": 0}


def _fmt(secs: float) -> str:
    secs = max(0, int(secs))
    return f"{secs // 60}:{secs % 60:02d}"


def progress(title: str) -> None:
    modes_n = 2 if args.mode == "both" else 1
    total = max(PROG["done"], PROG["per_mode"] * modes_n * args.runs)
    elapsed = time.time() - PROG["t0"]
    per = elapsed / PROG["done"] if PROG["done"] else (PROG["secs"] or 0)
    left = (total - PROG["done"]) * per if per else 0
    width = 28
    fill = int(width * PROG["done"] / total) if total else 0
    eta = f"about {_fmt(left)} left" if per else "timing the first scenario..."
    line = f"[{'#' * fill}{'-' * (width - fill)}] {PROG['done']}/{total}  {_fmt(elapsed)} elapsed, {eta}  {title}"
    cols = shutil.get_terminal_size((120, 20)).columns - 1     # one row exactly: a line wider than the window wraps, and the carriage
    sys.__stdout__.write("\r" + line[:cols].ljust(cols))       # return then only goes back to its last row, smearing the bar across the screen
    sys.__stdout__.flush()


# ---------- --vary: each run index has its own personality pair; what they say, remember and are stays with that pair ----------
PERSONA_FIELDS = rules.WHO + rules.lived_keys()          # everything that makes this pair who they are, and what they have lived (engine/party.py)
VARY = {"on": False, "run": 1, "store": {}, "need_rel": False, "shown": []}


def _rolled(m: dict, run: int, idx: int) -> dict:
    """A fresh personality for this member at this run index: the same every time --vary is used."""
    rng = random.Random(9000 + 97 * run + idx)
    temps = list(rules.P["temperaments"])
    t1 = rng.choice(temps)
    t2 = rng.choice([t for t in temps if t != t1])
    p = {"temper": [t1, t2], "motive": rng.choice(list(rules.P["motives"])), "line": rng.choice(rules.P["lines"]), "details": None,
         "said": [], "talk": [], "memories": [dict(x) for x in VARY["start_memories"][m["id"]]], "impression": "", "canon": [], "beliefs": [],
         "raised": {}, "gestured": []}
    tmp = {"id": m["id"], "motive": p["motive"]}
    quirks.roll(tmp, rng)
    q = tmp["quirks"]
    keep = VARY["forced"][m["id"]]                      # what the scenario titles promise (who approves of what, the voice) stays
    q.update({k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in keep.items()})
    p["quirks"] = q
    from engine import voice_profile                     # each run's pair are of different peoples; Isel is always raised with a tongue of her own
    people = ROTATION[idx][(run - 2) % len(ROTATION[idx])]
    p["people"] = people
    if idx != 1:                                         # Isel (index 1) always has a tongue of her own; the others any culture of their people
        p["speech"] = voice_profile.roll(rng, people)
    else:
        with_tongue = {c: wt for c, wt in voice_profile.S["peoples"][people].items() if voice_profile.S["cultures"][c].get("tongue")}
        culture = rng.choices(list(with_tongue), weights=list(with_tongue.values()))[0]
        p["speech"] = voice_profile.roll(rng, people, culture, rng.choice(["learner", "fluent", "fluent"]))
    return p


ROTATION = [["dwarf", "orc", "elf", "goliath", "halfling", "dragonborn"],          # Bram, runs 2 onward (run 1 is the usual human pair)
            ["genasi", "gnome", "dwarf", "half_elf", "elf", "human"],            # Isel
            ["halfling", "human", "goliath", "elf", "dwarf", "gnome"]]           # Tamsin, the third


def describe(m: dict, run: int) -> list[str]:
    """Everything rolled or written about this person, for the report."""
    sp, q = m.get("speech") or {}, m.get("quirks") or {}
    voice = q.get("voice", "")
    extra = {"curses": f" ({', '.join(quirks.my_curses(m))})", "swears_by": f" (by {q.get('oath', '')})", "nickname": f" (calls the player {q.get('nick', '')})",
             "figures": f" (from {q.get('trade', '')})"}.get(voice, "")
    lines = [f"- run {run}, {m['name']}: {sp.get('people', 'human').replace('_', '-')} raised in {sp.get('culture', '?')} "
             f"(Common: {sp.get('fluency', '?')}; culture shows {sp.get('strength', '?')}); temperament {', '.join(m.get('temper', []))}; "
             f"motive {m.get('motive')}; will not: {m.get('line', '')}",
             f"  - voice {voice}{extra}; habit {q.get('habit')}; approves of {q.get('likes')}, cannot stand {q.get('dislikes')}; flaw {q.get('flaw') or 'none'}",
             f"  - shows feelings: " + "; ".join(f"{e}: {t}" for e, t in (sp.get("tells") or {}).items()),
             f"  - toward others: " + "; ".join(f"{k}: {t}" for k, t in (sp.get("expression") or {}).items()),
             f"  - family: {__import__('engine.voice_profile', fromlist=['family']).family(m) or '(none rolled)'}",
             f"  - details: " + (" | ".join(f"[{g}] {d}" for d, g in __import__("engine.gravity", fromlist=["details"]).details(m)) or "(none written)"),
             f"  - detail subjects rolled: {', '.join(m.get('detail_kinds') or []) or '(none)'}",
             f"  - secrets: " + (" | ".join(m.get("secrets") or []) or "(none written: the written fallback for their motive)"),
             *[f"  - {label}: " + (" | ".join(x["text"] for x in m.get(key, [])) or "(none)") for label, key in
               (("backstory", "canon"), ("traits", "traits"), ("owns", "possessions"), ("means to", "intentions"), ("has promised", "commitments"),
                ("for now", "state_now"), ("believes", "beliefs"))]]
    return lines


def vary_to(run: int) -> None:
    if not (args.vary and VARY["on"]) or run == VARY["run"]:
        return
    crew = w.player.party
    for i, m in enumerate(crew):
        VARY["store"][(m["id"], VARY["run"])] = {k: m.get(k) for k in PERSONA_FIELDS}
    VARY["store"][("rel", VARY["run"])] = w.player.party_relations
    for i, m in enumerate(crew):
        p = VARY["store"].get((m["id"], run)) or _rolled(m, run, i)
        for k in PERSONA_FIELDS:
            if p.get(k) is None:
                m.pop(k, None)
            else:
                m[k] = p[k]
    w.player.party_relations = VARY["store"].get(("rel", run), {})
    VARY["run"] = run
    if VARY["need_rel"]:
        w.relations_seed()                                # writes only the pairs this run does not have yet (a third hire joining is new pairs)


def scenario(mode, title, fn, speakers_temper=None, maren_q=False, fixed=False):
    if fixed:
        FIXED.add(title)
    PROG["seen"] += 1
    for run in range(1, args.runs + 1):
        progress(f"[{mode}] {title} ({run}/{args.runs})")
        store.meta.seed = 11 + 7919 * (run - 1)          # each run its own dice (what brings talk up, weather), the same every time the check is run
        vary_to(run)
        if mode == "independent":
            reset_state()
        SAID.clear(); CALLS.clear(); FALLBACKS.clear(); REFUSED.clear()
        from engine import canon as _canon
        _canon.EVENTS.clear()
        t0 = time.time()
        err = ""
        w.last_plan = None
        w.last_hits = None
        w.last_interpret = None
        try:
            fn()
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        dt = time.time() - t0
        src = "FALLBACK (the model's answer was refused or failed, so written lines were used)" if FALLBACKS else "model"
        out.append(f"## [{mode}] {title} (run {run})")
        out.append(f"- source: **{src}**  ·  {dt:.1f}s total  ·  model calls: " + (", ".join(f"{t} {s:.1f}s{'' if ok else ' FAILED'}" for t, s, ok in CALLS) or "none"))
        if getattr(w, "last_plan", None) is not None:       # who the director gave the floor, and why each did or did not speak
            from engine import party_director as _pd
            _names = {m["id"]: m["name"] for m in w.player.party}
            out.extend(f"- {x}" if i == 0 else f"  {x}" for i, x in enumerate(_pd.explain(w.last_plan, _names)))
        li = getattr(w, "last_interpret", None)
        if li:                                             # what the interpreter was shown (engine/candidates.py), against the whole world
            out.append(f"- interpreter shown: {li['chars']} chars (~{li['chars'] // 4} tokens); places {li['places']} of {li['of_places']}; "
                       f"people elsewhere {li['people_away']} of {li['of_people_away']}" + (f"; left out: {', '.join(li['left_out'])}" if li["left_out"] else ""))
        if getattr(w, "last_hits", None):                  # how hard the moment hit each of them (engine/severity.py)
            out.append("- how hard it hit: " + ", ".join(f"{n.split()[0]} {lv}" for n, lv in w.last_hits.items()))
        for why in REFUSED:
            out.append(f"- answer refused: {why}")
        if err:
            out.append(f"- **ERROR**: {err}"); flags.append(f"{title}: {err}")
        CANON_TALLY["calls"] += sum(1 for t, _, _ in CALLS if t == "Extracted")
        for e in _canon.EVENTS:                           # what each claim about themselves became
            out.append(f"- canon ({e['who']}): {e['verdict']}: \"{e['claim']}\"" + (f" (against: \"{e['against']}\")" if e["against"] else ""))
            CANON_TALLY[e["verdict"]] += 1
        if FALLBACKS:
            if mode == "continuity" and REFUSED and all("said something very like" in r or "did that very thing" in r for r in REFUSED):
                guarded.append(f"[{mode}] {title} run {run}: the repetition guard refused every try, so it fell back")
            else:
                flags.append(f"[{mode}] {title} run {run}: fell back ({', '.join(FALLBACKS)})")
        out.append("")
        spoken = []
        for who, text in SAID:
            out.append(f"> **{who}**: {' '.join(text.split())}")
            if who in ("(narration)", "(game)"):
                continue
            lines_by[(mode, title, who)].append(text)
            spoken.append((who, text))
        PROG["done"] += 1
        present = {who for who, _ in spoken}
        from engine import voice_profile as _vp
        def _voice(m):                                    # a voice that shows only when the moment invites it is told to the judge as a tendency
            v = quirks.voice_prompt(m)
            spec = quirks.Q["voices"].get((m.get("quirks") or {}).get("voice", ""), {})
            return f"tends to (not in every line): {v}" if v and spec.get("kind") == "conditional" else v
        voices = {m["name"]: " ".join(x for x in (_vp.who(m), _voice(m)) if x) for m in w.player.party
                  if m["name"] in present and (_voice(m) or _vp.who(m))}
        if spoken and title not in FIXED:                # judged at the end, all together, so a separate judge model is loaded once
            out.append("")
            selves = {m["name"]: " ".join([r["text"] for r in _vp.origin_records(m)] + list(m.get("details") or [])) for m in w.player.party
                      if m["name"] in present}
            JUDGE_LATER.append((len(out) - 1, mode, title, run, spoken, (voices, selves), maren_q))
        out.append("")

def clerk(personality, voice, mood="", name="Odo"):
    n = NPC(id="clerk_live", name=name, people="human", role="guild_clerk", location="parth", personality=personality, voice=voice, mood=mood,
            description="A tidy clerk behind a worn desk.", trust=50)
    store.save_npc(n)
    return n

CLERKS = {"warm clerk": clerk("Kind, cheerful and welcoming to newcomers.", "Friendly and quick to smile."),
          "cold clerk": clerk("Curt, dismissive and bored by newcomers.", "Clipped and rude.", "sour"),
          "neutral clerk": clerk("Methodical and precise.", "Plain and businesslike.")}
crew = [{"id": "h1", "name": "Bram Voss", "role": "fighter", "level": 3, "rank": "F", "permanent": True, "temper": ["blunt", "dry"], "blurb": "a scarred sellsword",
         "motive": "rank", "line": "will not strike a foe who has yielded", "bond": 20, "capped": True, "memories": [], "said": [], "talk": []},
        {"id": "h2", "name": "Isel Quill", "role": "priest", "level": 3, "rank": "F", "permanent": True, "temper": ["gentle", "devout"], "blurb": "a quiet healer of the old faith",
         "motive": "protect", "line": "will not leave anyone behind in a fight", "bond": 35, "memories": [], "said": [], "talk": []}]
rules.remember(crew[0], 1, "I took their coin at the guild hall and signed on.", 2)
rules.remember(crew[1], 1, "I took their coin at the guild hall and signed on.", 2)
rules.remember(crew[0], 2, "They asked why I became a sellsword, and listened to the answer.", 2)
crew[0]["impression"] = "Thinks the player is green but does not pretend otherwise, which is something."

modes = ["independent", "continuity"] if args.mode == "both" else [args.mode]
for mode in modes:
    # Maren and the clerk
    for label, c in CLERKS.items():
        scenario(mode, f"Maren and the {label} at the register", lambda c=c: w.mentor_clerk_exchange(c))

    # the party: quiet road, hurt companion, after a hard fight, resting, with and without a relation line
    w.player.party = [dict(m) for m in crew]; w.player.party_mode = "with"
    live = w.player.party
    from engine import quirks
    for m in live:                                       # every quirk is set before anything is written about them, the relation line included
        quirks.roll(m, random.Random(m["id"]))
    live[0]["quirks"].update({"likes": "harvest", "dislikes": "flee", "voice": "curses", "curses": ["ashes and rot", "gutless tick", "damn", "shit"],
                              "reacted": {}, "told": 0})
    live[1]["quirks"].update({"likes": "spare", "dislikes": "harvest", "voice": "plain", "reacted": {}, "told": 0})
    from engine import voice_profile                     # run 1's pair: Bram from the heartland; Isel from the Rimelands, still learning Common
    live[0]["people"], live[0]["speech"] = "human", voice_profile.roll(random.Random(41), "human", "heartland")
    live[1]["people"], live[1]["speech"] = "human", voice_profile.roll(random.Random(42), "human", "rimelands", "learner")
    out.append(f"- Bram's quirks: {live[0]['quirks']['habit']}, voice {live[0]['quirks']['voice']}, flaw {live[0]['quirks']['flaw'] or 'none'}, "
               f"approves of {live[0]['quirks']['likes']}, cannot stand {live[0]['quirks']['dislikes']}; Isel's: {live[1]['quirks']['habit']}, voice "
               f"{live[1]['quirks']['voice']}, flaw {live[1]['quirks']['flaw'] or 'none'}, approves of {live[1]['quirks']['likes']}, cannot stand "
               f"{live[1]['quirks']['dislikes']}. Bram is waiting on a promotion throughout (it should not take over his talk).")
    w.player.party_relations = {}
    if args.vary:
        VARY.update({"on": True, "run": 1, "store": {}, "need_rel": False,
                     "start_memories": {m["id"]: [dict(x) for x in m.get("memories", [])] for m in live},
                     "forced": {live[0]["id"]: {k: live[0]["quirks"][k] for k in ("likes", "dislikes", "voice", "curses", "reacted", "told")},
                                live[1]["id"]: {k: live[1]["quirks"][k] for k in ("likes", "dislikes", "voice", "reacted", "told")}}})
    scenario(mode, "Party arrives, nothing pressing (no relation line yet)", lambda: w.party_banter(live, "travel"))
    w.relations_seed()
    VARY["need_rel"] = True
    _rel = w.player.party_relations.get(rules.pair_key('h1', 'h2'), {})
    out.append(f"- relation line written: {_rel.get('dynamic', '(none)')}  ·  wants: {_rel.get('wants', {})}")
    scenario(mode, "Party arrives, with their relation", lambda: w.party_banter(live, "travel"))
    live[0]["hp_frac"], live[0]["hp_at"] = 0.35, w.minutes
    w.player.party_last_fight = {"minute": w.minutes - 30, "won": True, "hard": True, "hurt": ["Bram Voss"], "carried": [], "fallen": []}
    w.pair_event(live[0], live[1], "came through a hard fight side by side; Isel bound Bram's ribs afterwards.")
    rules.set_mood(live[0], "sore, and quieter than usual, after coming out of the last fight badly hurt", w.minutes)
    scenario(mode, "After a hard fight, Bram hurt", lambda: w.party_banter(live, "fight"))
    scenario(mode, "Resting, Bram still hurt", lambda: w.party_banter(live, "rest"))
    scenario(mode, "One companion alone, hurt", lambda: w.party_banter([live[0]], "travel"))
    live[0]["hp_frac"] = 1.0; live[0]["mood"] = ""
    w.player.party_last_fight = {}
    scenario(mode, "Talking to Bram: why did you become a sellsword?", lambda: w.hire_talk(live[0], "Why did you become a sellsword?"))
    scenario(mode, "Talking to Isel: do you think we should take the troll job?", lambda: w.hire_talk(live[1], "Do you think we should take the troll job?"))
    scenario(mode, "Talking to Bram: my brother was killed by bandits", lambda: w.hire_talk(live[0], "My brother was killed by bandits last winter."))
    # quirks: a reaction to a deed, and a secret told
    def _deed(d):
        for m in live:
            m["quirks"]["reacted"] = {}
        w.deed(d)
    scenario(mode, "The player skins the wolves: Bram approves, Isel does not", lambda: _deed("harvest"))
    scenario(mode, "The player runs from a fight: Bram does not approve", lambda: _deed("flee"))
    def _secret():
        live[1]["bond"] = 35; live[1]["quirks"]["told"] = 0
        w.secrets()
    scenario(mode, "Isel, now trusting, tells her first secret", _secret, fixed=True)
    # the new voices: a curser and someone whose first tongue is not English
    out.append(f"- PROFANITY is '{config.PROFANITY}'; Bram's curses allowed: {quirks.my_curses(live[0])}; Isel speaks the tongue of {quirks.tongue(live[1])['home']}")
    live[0]["hp_frac"], live[0]["hp_at"] = 0.4, w.minutes
    scenario(mode, "Talking to Bram (curses), hurt: how is the wound?", lambda: w.hire_talk(live[0], "How is the wound holding up?"))
    scenario(mode, "Talking to Isel (second tongue): where are you from?", lambda: w.hire_talk(live[1], "Where are you from, originally?"))
    scenario(mode, "Talking to Isel (second tongue): what do you think of Bram?", lambda: w.hire_talk(live[1], "What do you make of Bram?"))
    scenario(mode, "Banter with a curser and a second tongue, Bram hurt", lambda: w.party_banter(live, "rest"))
    live[0]["hp_frac"] = 1.0

    # a third hire: the whole party, player and three companions
    third = {"id": "h3", "name": "Tamsin Reed", "role": "ranger", "level": 3, "rank": "F", "permanent": True, "temper": ["wary", "cheerful"],
             "blurb": "a lean tracker with a patched cloak", "motive": "wander", "line": "will not take from the poor", "bond": 15,
             "memories": [], "said": [], "talk": []}
    rules.remember(third, 3, "I took their coin at the guild hall and signed on.", 2)
    quirks.roll(third, random.Random("h3"))
    third["quirks"].update({"likes": "loot_dead", "dislikes": "bribe", "reacted": {}, "told": 0})
    third["people"], third["speech"] = "human", voice_profile.roll(random.Random(43), "human", "heartland")
    live.append(third)
    if args.vary:
        VARY["start_memories"]["h3"] = [dict(x) for x in third["memories"]]
        VARY["forced"]["h3"] = {k: third["quirks"][k] for k in ("likes", "dislikes", "reacted", "told")}
        VARY["store"][("h3", 1)] = {k: third.get(k) for k in PERSONA_FIELDS}       # she joins mid-check: her own self is run 1's
        if VARY["run"] != 1:                                                    # and the run now showing gets its own roll of her
            p_ = _rolled(third, VARY["run"], 2)
            for k in PERSONA_FIELDS:
                if p_.get(k) is None:
                    third.pop(k, None)
                else:
                    third[k] = p_[k]
    out.append(f"- Tamsin joins: {third['quirks']['habit']}, voice {third['quirks']['voice']}, approves of {third['quirks']['likes']}, cannot stand "
               f"{third['quirks']['dislikes']}. All three are there for every exchange below; the director decides who speaks (its reasons are shown).")
    def _talk(kind):
        w.relations_seed()
        return w.party_banter(live, kind)
    scenario(mode, "Three companions: Tamsin joins, arriving together", lambda: _talk("travel"))
    def _later(fn, minutes=180):                          # a separate moment: otherwise a fresh game at the same minute is the same scene again
        store.meta.minutes += minutes
        try:
            return fn()
        finally:
            store.meta.minutes -= minutes
    scenario(mode, "Three companions: on the road again, later in the day", lambda: _later(lambda: _talk("travel")))
    scenario(mode, "Three companions: resting, nothing pressing", lambda: _talk("rest"))
    scenario(mode, "Talking to Tamsin: what brought you to the guild?", lambda: w.hire_talk(third, "What brought you to the guild?"))
    scenario(mode, "Talking to Tamsin: what do you make of Bram and Isel?", lambda: w.hire_talk(third, "What do you make of Bram and Isel?"))
    scenario(mode, "Talking to Bram: what do you make of Tamsin?", lambda: w.hire_talk(live[0], "What do you make of Tamsin?"))
    scenario(mode, "Three companions: the player skins a kill (Bram approves, Isel does not, Tamsin has no view)", lambda: _deed("harvest"))
    scenario(mode, "Three companions: the player loots the dead (only Tamsin has a view)", lambda: _deed("loot_dead"))
    scenario(mode, "Three companions: the player runs from a fight (Bram does not approve)", lambda: _deed("flee"))
    live[0]["hp_frac"], live[0]["hp_at"] = 0.35, w.minutes
    scenario(mode, "Three companions: at rest, Bram badly hurt", lambda: _talk("rest"))
    live[0]["hp_frac"] = 1.0
    w.player.party_last_fight = {"minute": w.minutes - 20, "won": False, "hard": True, "hurt": [], "carried": [], "fallen": []}
    scenario(mode, "Three companions: after a lost fight", lambda: _talk("fight"))
    w.player.party_last_fight = {}
    # the player speaks to one of three: whether the others join in depends on what was said (the director's read is shown)
    scenario(mode, "Speaking to Bram, all three there: small talk ('nice boots') - nobody else should join", lambda: w.hire_talk(live[0], "Nice boots. New?"))
    scenario(mode, "Speaking to Bram, all three there: about Isel - Isel may join", lambda: w.hire_talk(live[0], "Isel patched you up well after that last fight, didn't she?"))
    def _her():                                           # one of Tamsin's own details, put as a question to Bram
        d = ((live[2].get("details") or ["They grew up in hill country, tracking deer."])[0]).rstrip(".")
        first, _, rest = d.partition(" ")                  # "She spent her mornings..." -> "spent her mornings...", whoever the detail names
        return rest if first.lower() in ("they", "she", "he", live[2]["name"].split()[0].lower()) else d[0].lower() + d[1:]
    scenario(mode, "Speaking to Bram, all three there: something close to Tamsin's own life - Tamsin may join",
             lambda: w.hire_talk(live[0], f"Bram, you ever meet anyone who {_her()}?"))
    scenario(mode, "Speaking to Bram, all three there: a question for the whole party - everyone should answer", lambda: w.hire_talk(live[0], "We leave at dawn for the troll job. Everyone ready for it?"))
    scenario(mode, "Speaking to Bram, all three there: heavy words - everyone should have a say",
             lambda: w.hire_talk(live[0], "I keep thinking about the boy at the ford. We could have saved him, and we didn't."))
    # how heavy the moment is: a death, everyone has a say; picking up a rock, nobody says a thing
    # how hard a moment hits: one path for a death, a betrayal, something grim; by what the one it concerns is to each of them
    def _close():                                         # Bram close to Tamsin, Isel cool toward her
        w.relations_seed()
        w.relation(live[0], third)["score"], w.relation(live[1], third)["score"] = 40, -10
    def _killed():                                        # what the fight calls the moment a hire is killed: the two left react at once
        _close()
        return w.party_moment(f"{third['name']} has just been killed in front of them.", "heavy", third["id"], f"{third['name']}'s death", in_fight=True)
    scenario(mode, "Mid-fight: Tamsin is killed in front of them (Bram close to her, Isel cool toward her) - one outburst each, at once", _killed)
    def _after():                                         # the same fight, over: she is gone, and it is always talked over
        _close()
        at = live.index(third)
        live.remove(third)
        w.player.party_last_fight = {"minute": w.minutes - 5, "won": True, "hard": True, "hurt": [], "carried": [], "fallen": [third["name"]],
                                     "fallen_ids": [third["id"]]}
        try:
            return _talk("fight")
        finally:
            live.insert(at, third)
            w.player.party_last_fight = {}
    scenario(mode, "After that fight: Tamsin is dead - Bram devastated, Isel sobered", _after)
    scenario(mode, "A betrayal: the clerk who signed them on sold their route to bandits (concerns nobody in particular)",
             lambda: w.party_moment("They have just learned that Odo, the guild clerk who signed them on, sold the party's route to the bandits "
                                    "who ambushed them.", "heavy", None, "Odo's betrayal"))
    scenario(mode, "Something grim: a family chained in a cellar, long dead",
             lambda: w.party_moment("They have just forced open a cellar door and found a family chained to the wall, long dead.", "heavy", None,
                                    "what was in the cellar"))
    def _rock():
        w._banter_due = ""; w._banter_last = w.minutes
        w.mentor_intercept = lambda t: False                # the check's game never met Maren: her first meeting would wait on the keyboard
        try:
            w.handle("I pick up a smooth grey rock from the side of the road and turn it over in my hand.")
        finally:
            del w.mentor_intercept
    scenario(mode, "Three companions: the player picks up a rock - nobody should react", _rock)
    vary_to(1)
    out.append(f"- Bram's details: {live[0].get('details', [])}")
    out.append(f"- Isel's details: {live[1].get('details', [])}")
    if len(live) > 2:
        out.append(f"- Tamsin's details: {live[2].get('details', [])}")
    out.append(f"- pair history: {[h['text'] for h in w.player.party_relations.get(rules.pair_key('h1', 'h2'), {}).get('history', [])]}")
    for key, rel in sorted(w.player.party_relations.items()):          # each pair, and what each of the two thinks of the other
        names = {m["id"]: m["name"].split()[0] for m in live}
        views = "; ".join(f"{names.get(i, i)} thinks: {v}" for i, v in (rel.get("views") or {}).items())
        out.append(f"- {' & '.join(names.get(i, i) for i in key.split('|')) if '|' in key else key}: {rel.get('dynamic', '')}  ·  {views or '(no views)'}")
    out.append("- Bram's memories now: " + "; ".join(x["text"] + (f" (x{x['count']})" if x.get("count", 1) > 1 else "") for x in live[0].get("memories", [])))
    out.append(f"- Bram's impression now: {live[0].get('impression', '')}")
    out.append(f"- Bram's canon (what he has said about himself): {[c['text'] for c in live[0].get('canon', [])]}")
    out.append(f"- Isel's canon: {[c['text'] for c in live[1].get('canon', [])]}  ·  beliefs: {[b['text'] for b in live[0].get('beliefs', []) + live[1].get('beliefs', [])]}")
    out.append(f"### Who they were ({mode})")
    for run in range(1, (args.runs if args.vary else 1) + 1):
        for m in live:
            if run == 1:
                out += describe(m, 1)
            else:
                snap = VARY["store"].get((m["id"], run)) or {}         # that run's own state on a neutral base: a field it lacks is shown as absent
                stored = {k: v for k, v in m.items() if k not in PERSONA_FIELDS}
                stored.update({k: v for k, v in snap.items() if v is not None})
                out += describe(stored, run)
    if args.vary:
        VARY["on"] = False
    out.append("")
    w.player.party = []

    # Maren after the hire
    mentor.set_stage(w.player, "board")
    w.player.mentor["last_voice"] = True
    orig_with = w.mentor_with_you
    w.mentor_with_you = lambda: True
    for q in ("Why are you helping me?", "What is your rank?", "Are you worried about the wolves?", "Do you have family?"):
        scenario(mode, f"Maren in Parth answers: {q}", lambda q=q: w.mentor_talk(q), maren_q=True)
    scenario(mode, "Maren in Parth answers a rules question: how does hit chance work?", lambda: w.mentor_talk("How does hit chance work?"))
    scenario(mode, "Maren in Parth: the walk to the hall", lambda: w.mentor_say(mentor.M["escort"]["say"], beat="you say you will walk them to the guild hall yourself"), fixed=True)
    w.mentor_with_you = orig_with

MISSING = re.compile(r"\b(fail(ed|s)? to use|did not use|didn't use|does not use|doesn't use|without (using|any)|no (curse|oath)|lack(s|ed)?|never uses?)\b.*\b(curses?|oaths?|swear\w*|native|home tongue|tongue words?)\b", re.I)


MISSING2 = re.compile(r"\b(does not|doesn't|did not|didn't|never|fails? to|failed to)\s+(curse|swear)", re.I)


def only_missing_habit(note: str) -> bool:
    return bool(note and (MISSING.search(note) or MISSING2.search(note)))


# the judge reads every scenario now, after the game's model is done
for k, (pos, mode, title, run, spoken, voices, maren_q) in enumerate(JUDGE_LATER):
    progress(f"judging {k + 1}/{len(JUDGE_LATER)}")
    j = judge(title, spoken, *voices)
    if not j:
        continue
    PROSE["judged"] += 1
    for x in ("stock_phrase", "flat", "vivid"):
        PROSE[x] += bool(getattr(j, x))
    found = [x for x in ("invented_place", "pushes_objective", "archetype_tic", "out_of_voice") if getattr(j, x)]
    if "out_of_voice" in found and only_missing_habit(j.note):        # leaving out an optional curse or oath is not a break, whatever the judge says
        found.remove("out_of_voice")
    if not maren_q:
        found = [x for x in found if x != "pushes_objective"]
    if found:
        out[pos] = f"- judge: {', '.join(found)}" + (f" ({j.note})" if j.note else "")
        flags.append(f"[{mode}] {title} run {run}: judge says {', '.join(found)}" + (f": {j.note}" if j.note else ""))
sys.__stdout__.write("\n")

# sameness across independent runs, and archetype saturation
for (mode, title, who), lines in lines_by.items():
    if len(lines) < 2:
        continue
    if mode == "independent" and title not in FIXED:
        from llm import embed
        pairs = 0
        if embed.available():
            for i in range(len(lines)):
                for k in range(i + 1, len(lines)):
                    c = embed.closest(lines[i], [lines[k]])
                    if c and c[0] >= config.SIM_REPEAT:
                        pairs += 1
            if pairs >= 3:
                notes.append(f"[independent] {title}: {who} says much the same thing in {pairs} pairs of separate runs")
        else:
            runs_with = collections.Counter()
            for l in lines:
                for g in banter.grams(l):
                    runs_with[g] += 1
            common = [g for g, n in runs_with.items() if n >= 3]
            if common:
                notes.append(f"[independent] {title}: {who} reuses a phrase in {max(runs_with[g] for g in common)} of {len(lines)} lines across separate runs: "
                             + "; ".join("'" + " ".join(g) + "'" for g in sorted(common, key=lambda g: -runs_with[g])[:3]))

out.append(f"- Maren's facts for 'Why are you helping me?': {len(mentor.facts(w.player, 'Parth', 'Why are you helping me?').split())} words "
           f"(for 'how does hit chance work': {len(mentor.facts(w.player, 'Parth', 'how does hit chance work').split())})")
out += ["", "## Prose (the judge's reading of every scenario it judged)",
        f"- judged: {PROSE['judged']}  ·  vivid (a specific detail only this person would say): {PROSE['vivid']}  ·  "
        f"stock phrases: {PROSE['stock_phrase']}  ·  flat or generic: {PROSE['flat']}"]
out += ["", "## Canon (what speakers said about themselves, and what became of it)",
        f"- extraction calls: {CANON_TALLY['calls']}",
        f"- canon: backstory {CANON_TALLY['backstory']}  ·  traits {CANON_TALLY['trait']}  ·  (refused: the same as something known "
        f"{CANON_TALLY['same']}, only what they were given {CANON_TALLY['given']}, contradicted what was known {CANON_TALLY['contradicts']}, said of themselves but not theirs {CANON_TALLY['not about them']})",
        f"- dropped as not worth keeping: common knowledge {CANON_TALLY['common knowledge']}  ·  a fact of the scene, not a belief "
        f"{CANON_TALLY['a fact of the scene, not a belief']}",
        f"- opinions of a particular person (the player, a companion, someone they know): {CANON_TALLY['opinion']}  ·  ongoing situations: "
        f"{CANON_TALLY['situation']}",
        f"- not canon: possessions {CANON_TALLY['possession']}  ·  intentions {CANON_TALLY['intention']}  ·  commitments "
        f"{CANON_TALLY['commitment']}  ·  just for now {CANON_TALLY['moment']}  ·  beliefs about the world {CANON_TALLY['belief']}  ·  "
        f"said again (refreshed) {sum(v for k, v in CANON_TALLY.items() if k.endswith('(again)'))}"]
from engine import severity as _sev
_byl = collections.defaultdict(lambda: [0, 0])
for _lv, _silent in _sev.REACTIONS:                   # every reaction to a moment that weighed on them, over the whole check
    _byl[_lv][0] += 1
    _byl[_lv][1] += _silent
out += ["", "## Silence (reactions with no words or no line at all, by how hard the moment hit; allowed from " + _sev.SV["may_be_silent_from"] + " up)",
        "- " + ("  ·  ".join(f"{lv}: {_byl[lv][1]} silent of {_byl[lv][0]}" for lv in _sev.LEVELS if lv in _byl) or "no weighty moments reacted to")]
out += ["", "## Flags", *(f"- {f}" for f in sorted(set(flags)) or ["none"])]
out += ["", "## Fell back only because of the repetition guard (continuity runs ask the same thing again on purpose)", *(f"- {g}" for g in guarded or ["none"])]
out += ["", "## Notes: the same phrase across separate runs (each run is a separate game, so a player would not see this)", *(f"- {n}" for n in sorted(set(notes)) or ["none"])]
path = ROOT / "saves" / args.report
path.write_text("\n".join(out) + "\n", encoding="utf-8")
progress("finished")
sys.__stdout__.write("\n")
try:
    modes_n = 2 if args.mode == "both" else 1
    LAST.write_text(_json.dumps({"per_mode": PROG["seen"] // modes_n, "secs_per": (time.time() - PROG["t0"]) / max(1, PROG["done"])}), encoding="utf-8")
except OSError:
    pass
print(f"Done in {_fmt(time.time() - PROG['t0'])}. {len(set(flags))} flag(s). Report: {path}")
for f in sorted(set(flags)):
    print("  -", f)
shutil.rmtree(ROOT / "saves" / NAME, ignore_errors=True)
