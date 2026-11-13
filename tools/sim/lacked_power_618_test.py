"""(f618) A power the character lacks: the model names the need, the engine decides what lacking it means. f612 wrote the owner's ruling
("seeing in the dark can be a skill check using perception") into the corpus and left the engine refusing the act (the audit of
2026-11-13, docs/design/18 part B). Now a capability may say what stands in for it (data/rules/capabilities.yaml `without`: a check,
how hard, and how it is then done), and one reader (engine/ruling.py standing) settles every ruling on both paths: has it, as ruled;
lacks it with a stand-in, a cost rolled on that check; lacks it with none, a no in the capability's own words. A no that names the
power it wants is settled the same way, so whichever way the model rules the engine reaches one answer. The owner's four, 2026-11-12
and 2026-11-13: darkvision (perception, fair), invisibility (stealth, hard), reading a mind (insight, hard), breathing water
(constitution, hard).
Run: python tools/sim/lacked_power_618_test.py"""
import copy
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import act, checks, pulse, ruling, targets
from llm.contracts import ActRuling, Ruling

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


C = ruling.C
STOOD = {"darkvision": ("perception", "fair"), "invisibility": ("stealth", "hard"), "mind_reading": ("insight", "hard"),
         "water_breathing": ("constitution", "hard")}

# ---- the data
check("the owner's four say what stands in for them, each a real check and difficulty and how it is then done; no other does",
      {k: (v["without"]["check"], v["without"]["hard"]) for k, v in C.items() if v.get("without")} == STOOD
      and all(v["without"].get("told", "").strip() for v in C.values() if v.get("without")), {k: v.get("without") for k, v in C.items()})
check("the capabilities check clean", ruling.problems() == [], ruling.problems())
real = copy.deepcopy(C["darkvision"])
for wrong in ({"check": "sight", "hard": "fair", "told": "x"}, {"check": "perception", "hard": "beyond", "told": "x"},
              {"check": "perception", "hard": "fair", "told": ""}, "perception"):
    C["darkvision"]["without"] = wrong
    check(f"...a stand-in that is not a check, a difficulty and how it is done is named at startup ({wrong})",
          any("darkvision" in p and "without" in p for p in ruling.problems()), ruling.problems())
C["darkvision"] = real

# ---- the one reader, on every capability in the file
def R(sense, requires, check_="", hard=""):
    return types.SimpleNamespace(sense=sense, requires=list(requires), stakes=types.SimpleNamespace(check=check_, hard=hard))
table = []
for cap, spec in C.items():
    has = ruling.standing({cap}, R("yes", [cap]))
    lacks = ruling.standing(set(), R("yes", [cap]))
    want = ("stand_in", cap, {"check": STOOD[cap][0], "hard": STOOD[cap][1]}) if cap in STOOD else ("lacks", cap, None)
    if has != ("has", "", None) or lacks != want:
        table.append((cap, has, lacks))
check("every capability: had, the ruling stands as ruled; lacked, a cost on what stands in for it, or with nothing to stand in, a no",
      len(C) >= 12 and not table, table)
check("a ruling's own difficulty stands when it is the harder; an easier one gives way to the stand-in's",
      ruling.standing(set(), R("cost", ["darkvision"], "strength", "hard"))[2] == {"check": "perception", "hard": "hard"}
      and ruling.standing(set(), R("cost", ["darkvision"], "strength", "easy"))[2] == {"check": "perception", "hard": "fair"})
check("two lacked powers: one with nothing to stand in for it makes it a no; both with, the first's check at the harder difficulty",
      ruling.standing(set(), R("yes", ["darkvision", "flight"]))[:2] == ("lacks", "flight")
      and ruling.standing(set(), R("yes", ["darkvision", "invisibility"])) == ("stand_in", "darkvision", {"check": "perception", "hard": "hard"}))
check("a ruling that requires nothing, or only what they have, is as ruled",
      ruling.standing(set(), R("no", [])) == ("has", "", None) and ruling.standing({"flight"}, R("cost", ["flight"]))[0] == "has")

# ---- the act's path: a yes that names the power, and a no that names it, for every capability
g = simlib.campaign("lacked_power_618", seed=3, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})
T = targets.targets_for(ws, ws.acting)
c = ws.player.character
born_with = set(act.means(ws, ws.acting))
def ruled(d):
    return act.validate(ws, ws.acting, T, ActRuling.model_validate(d, context=act.context(ws, T)))
off = []
for cap, spec in C.items():
    if cap in born_with:
        continue
    yes = ruled({"sense": "yes", "why": "x", "works": "It is done.", "requires": [cap]})
    no = ruled({"sense": "no", "answer": "Nothing happens.", "requires": [cap]})
    c.capabilities = [cap]
    had = ruled({"sense": "yes", "why": "x", "works": "It is done.", "requires": [cap]})
    c.capabilities = []
    if not (had.ok and had.ruling.sense == "yes" and not had.without):
        off.append((cap, "had", had.ok, had.answer))
    if cap in STOOD:
        for name, v in (("yes", yes), ("no", no)):
            if not (v.ok and v.ruling.sense == "cost" and (v.ruling.stakes.check, v.ruling.stakes.hard) == STOOD[cap] and v.without == cap):
                off.append((cap, name, v.ok, v.answer, v.without))
    elif yes.ok or yes.answer != spec["lacking"] or no.ok or no.answer != "Nothing happens.":
        off.append((cap, "none", yes.ok, yes.answer, no.ok, no.answer))
check("on the act's path, every capability the character was not born with: had, a plain yes; lacked with a stand-in, a cost on its "
      "check whether the ruling said yes or no; lacked with none, a no (the capability's words, or the ruling's own)", len(born_with) < len(C) and not off, off)
check("a no that names no power stands as the model gave it", not ruled({"sense": "no", "answer": "The wall is a wall."}).ok)
schema = act.shape(ws, T).model_json_schema()
no_branch = schema["anyOf"][1]
check("the grammar has a no say what power it wants, if any, so the engine can settle it", "requires" in no_branch["required"]
      and set(C) <= set(no_branch["properties"]["requires"]["items"]["enum"]), no_branch["required"])

# ---- in play: rolled on the stand-in's check, told how it is done, never refused; an act other than the one the owner ruled on
told, rolled = [], []
real_narrate, real_roll, real_odds = ws.narrate, checks.roll, ruling.odds
ws.narrate = lambda event, text="": told.append(event)
ruling.odds = lambda ws_, effect, r: rolled.append(dict(r)) or real_odds(ws_, effect, r)
def attempt(text, d, roll="success"):
    stub.act_ruling = d
    checks.roll = lambda odds, rng=None, c=None: (roll, 1)
    told.clear(); rolled.clear()
    with ws.operation("action:other", text) as op:
        ws.on_other(types.SimpleNamespace(kind="other", summary=text.rstrip(".").removeprefix("I ")), text)
    return told[-1] if told else ""
said = attempt("I search the rocks for crabs in the dark.", {"sense": "yes", "why": "eyes for the dark", "works": "You find a crab under a flat stone.",
                                                               "requires": ["darkvision"]})
check("a yes that needs darkvision, by one without it, is rolled on perception at fair and told as done without it",
      rolled == [{"check": "perception", "hard": "fair"}] and "WORKS" in said and C["darkvision"]["without"]["told"] in said
      and C["darkvision"]["lacking"] not in said, (rolled, said[-400:]))
said = attempt("I feel my way down the unlit stair.", {"sense": "no", "answer": "It is black as pitch.", "requires": ["darkvision"]}, "failure")
check("...a no that names darkvision is rolled the same way, and a failure is a failure, not a refusal", rolled == [{"check": "perception", "hard": "fair"}]
      and "FAILS" in said and "black as pitch" not in said, (rolled, said[-300:]))
said = attempt("I slip past the stallholders unseen.", {"sense": "cost", "why": "x", "works": "No one marks you.", "requires": ["invisibility"],
                                                         "stakes": {"check": "dexterity", "hard": "easy"}, "fail": "noticed"})
check("...another of the four: unseen without the power is stealth at hard, told as cover and shadow", rolled == [{"check": "stealth", "hard": "hard"}]
      and C["invisibility"]["without"]["told"] in said, (rolled, said[-300:]))
said = attempt("I grow wings and fly over the square.", {"sense": "yes", "why": "x", "works": "You fly.", "requires": ["flight"]})
check("...and a power with nothing to stand in for it is still a no, never rolled", not rolled and "does not happen" in said, (rolled, said[-300:]))
ws.narrate, checks.roll, ruling.odds = real_narrate, real_roll, real_odds

# ---- the road's ruling: the same reader
import ui.console as uc
shown = []
for fn in ("note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: shown.append((_fn, str(a[0]) if a else "")))
hz = {"tier": "normal", "what": "A drowned stretch of the road, black water over the stones.", "behind": "parth"}
def road(d):
    stub.ruling = d
    shown.clear()
    before = ws.minutes
    real = checks.roll
    checks.roll = lambda odds, rng=None, c=None: ("success", 1)
    try:
        ws.get_past(dict(hz), "I keep going")
    finally:
        checks.roll = real
    return ws.minutes - before, [t for _, t in shown]
spent, lines = road({"sense": "no", "why": "", "answer": "You cannot breathe down there.", "requires": ["water_breathing"]})
check("on the road, a no for want of a power with a stand-in is pressed past on its check, not sent the long way round",
      not any("no pushing straight through" in t for t in lines) and any(t.startswith("Constitution") for t in lines), (spent, lines))
spent, lines = road({"sense": "cost", "why": "", "requires": ["water_breathing"], "stakes": {"check": "strength", "hard": "easy"}})
check("...a cost that needs it is rolled on the stand-in's check too", any(t.startswith("Constitution") for t in lines), lines)
spent, lines = road({"sense": "cost", "why": "", "requires": ["flight"], "stakes": {"check": "strength", "hard": "easy"}})
check("...and a ruling that needs a power with nothing to stand in for it sends them round", spent > 0
      and any("no pushing straight through" in t for t in lines), (spent, lines))
c.capabilities = ["flight"]
spent, lines = road({"sense": "cost", "why": "", "requires": ["flight"], "stakes": {"check": "strength", "hard": "easy"}})
check("...unless they have it", any(t.startswith("Strength") for t in lines) and not any("no pushing straight through" in t for t in lines), lines)
c.capabilities = []

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
