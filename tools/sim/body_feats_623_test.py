"""(f623) Feats of the body: the model says how big, the engine says whether a body can (docs/design/19). The act's ruling rolled a
jump onto a roof and a portcullis raised by hand, because nothing in its path knew how big the feat was. Now a ruling names the feat
(a kind from data/rules/body.yaml and its size), and one reader (engine/body.py judge) settles it for the body that tries, on both
ruling paths: within easy reach, as ruled; within reach, at least a cost at fair or hard; past the limit, a no told from the table.
A drop past what a body lands unhurt is done and paid for, by one fall table for any being, and one that would kill is warned of
first and then is the game's one death. The feats here are not the ones the probe held.
Run: python tools/sim/body_feats_623_test.py"""
import copy
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import act, body, checks, combat, party, pools, pulse, ruling, targets
from llm.contracts import ActRuling, Ruling

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


K, F = body.K, body.F
person = lambda n, size="Medium": body.Body({a: n for a in ruling.ATTRS}, size)

# ---- the data
check("the table holds its eight kinds, each with a unit, what bounds it, its limits and its two refusals (a drop, never refused, has none)",
      set(K) == {"jump_up", "jump_across", "drop", "lift", "carry", "throw", "throw_far", "breath"} and body.problems() == []
      and all(("past" in v) == (k != F["kind"]) for k, v in K.items()), body.problems())
real = copy.deepcopy(body.B)
def broken(n, edit, word):
    edit(body.B)
    got = body.problems()
    check(f"...named at startup: {n}", any(word in p for p in got), got)
    for k, v in real.items():
        if isinstance(v, dict):
            body.B[k].clear()
            body.B[k].update(copy.deepcopy(v))
        else:
            body.B[k] = v
broken("a kind bounded by something that is no attribute", lambda B: B["kinds"]["lift"].__setitem__("by", ["muscle"]), "lift")
broken("limits that do not rise with the attribute", lambda B: B["kinds"]["carry"].__setitem__("limit", {10: 80, 15: 60, 30: 450}), "carry")
broken("a power that is no capability", lambda B: B["kinds"]["breath"].__setitem__("powers", ["gills"]), "breath")
broken("a kind with no words for its refusal", lambda B: B["kinds"]["throw"].__setitem__("nearly", ""), "throw")
broken("a size of body the fall does not know", lambda B: B["fall"]["size"].pop("Huge"), "Huge")
broken("bands out of order", lambda B: B["bands"].__setitem__("hard", 0.4), "bands")
broken("a landing that takes more than the fall", lambda B: B["fall"]["landing"].__setitem__("failure", [1.5, "badly"]), "landing")
broken("a landing with no word for how it went", lambda B: B["fall"]["landing"].__setitem__("partial", [0.75, ""]), "landing")
broken("a difficulty that is none of the three", lambda B: B["at_least"].__setitem__("effort", "trivial"), "at_least")
broken("one line alone for a death by falling", lambda B: B["fall"].__setitem__("died", ["It is {feet} feet."]), "died")
check("...and the table as it stands is clean again", body.problems() == [] and body.K is body.B["kinds"])

# ---- what a body can do: straight between the marks, on past the last, and down to nothing below the first
lim = lambda kind, n: round(body.limit(kind, person(n)), 2)
check("a limit is its mark at the mark", [lim("lift", n) for n in (10, 15, 30)] == [150, 250, 1000] and lim("jump_up", 15) == 6)
check("...straight between two marks", lim("lift", 20) == 500 and lim("breath", 12) == 62 and lim("jump_across", 22.5) == 19.5,
      (lim("lift", 20), lim("breath", 12), lim("jump_across", 22.5)))
check("...on past the last with no ceiling", lim("lift", 60) == 2500 and lim("lift", 90) == 4000 and lim("jump_up", 60) == 15
      and lim("drop", 60) == 51, (lim("lift", 60), lim("lift", 90), lim("drop", 60)))
check("...and below the first it falls away in proportion, never under nothing", lim("lift", 5) == 75 and lim("lift", 1) == 15)
check("a jump is bounded by the better of strength and dexterity",
      body.limit("jump_up", body.Body({**person(10).attrs, "dexterity": 30})) == 9 == body.limit("jump_up", body.Body({**person(10).attrs, "strength": 30})))

# ---- the one reader, on feats the probe did not hold
def R(sense="yes", kind="none", size=0, requires=(), check_="", hard=""):
    return types.SimpleNamespace(sense=sense, requires=list(requires), stakes=types.SimpleNamespace(check=check_, hard=hard),
                                 feat=types.SimpleNamespace(kind=kind, size=size))
J = lambda n, r, have=(): body.judge(person(n), set(have), r)
strong = [J(30, R("yes", "lift", s)) for s in (400, 600, 900, 1100, 1300)]
check("a weight against a strong back: easily, with effort at fair, at hard, nearly, and never",
      [j.how for j in strong] == ["free", "effort", "effort", "nearly", "past"]
      and [j.stakes for j in strong[1:3]] == [{"check": "strength", "hard": "fair"}, {"check": "strength", "hard": "hard"}]
      and strong[3].answer == K["lift"]["nearly"] and strong[4].answer == K["lift"]["past"], [(j.how, j.stakes) for j in strong])
check("...the same weights against an ordinary back are all past it", {J(10, R("yes", "lift", s)).how for s in (400, 600, 900)} == {"past"})
table = []
for kind in K:
    if kind == F["kind"]:
        continue
    for n in (10, 15, 30, 60):
        top = body.limit(kind, person(n))
        got = [J(n, R("cost", kind, top * x, check_="stealth", hard="easy")) for x in (0.4, 0.7, 0.95, 1.1, 2)]
        if [j.how for j in got] != ["free", "effort", "effort", "nearly", "past"] or got[1].stakes != {"check": "stealth", "hard": "fair"} \
                or got[2].stakes != {"check": "stealth", "hard": "hard"} or got[0].stakes is not None:
            table.append((kind, n, [(j.how, j.stakes) for j in got]))
check("every kind at every body: the five bands by the share of the limit, the ruling's own check kept", not table, table[:3])
check("the ruling's own difficulty stands when it is the harder", J(30, R("cost", "lift", 600, check_="strength", hard="hard")).stakes["hard"] == "hard")
check("a feat that is none, of no kind the table knows, or of no size is not the body's to judge",
      [J(10, R("yes")).how, J(10, R("yes", "wingspan", 9)).how, J(10, R("yes", "lift", 0)).how] == ["none"] * 3)
check("a power that does the feat wins over the table; one that does not, does not",
      J(10, R("yes", "jump_up", 30, requires=["flight"]), have=["flight"]).how == "power"
      and J(10, R("yes", "lift", 5000, requires=["darkvision"]), have=["darkvision", "flight"]).how == "past"
      and J(10, R("yes", "breath", 900), have=["water_breathing"]).how == "power")

# ---- falling: one table for any being
fall = lambda b, feet: round(body.fall(b, feet), 3)
check("an ordinary person lands eight feet unhurt, loses a third at sixteen, two thirds at twenty four, all at thirty two",
      [fall(body.ordinary(), x) for x in (5, 8, 16, 24, 32, 300)] == [0, 0, 0.333, 0.667, 1, 1], [fall(body.ordinary(), x) for x in (5, 8, 16, 24, 32, 300)])
check("a body of dexterity 60 lands fifty one feet unhurt and none of them lands two hundred and four",
      body.unhurt(person(60)) == 51 and fall(person(60), 51) == 0 and 0 < fall(person(60), 120) < 1 and fall(person(60), 204) == 1)
check("a bigger body falls harder and a smaller one lighter, by its size",
      [round(body.unhurt(person(10, s)), 1) for s in body.SIZES] == [24, 12, 8, 6.4, 4.8, 4]
      and fall(person(10, "Tiny"), 30) < fall(person(10, "Small"), 30) < fall(person(10), 30) < fall(person(10, "Large"), 30) <= 1)
g = simlib.campaign("body_feats_623", seed=3, location="trading_square")
ws, store, world = g.scene, g.store, g.world
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})
c = ws.player.character
seen = {}
for cid, cr in world.bestiary.items():
    seen.setdefault(getattr(cr, "size", "Medium"), cid)
beings = {f"a {s.lower()} creature ({cid})": combat.fighter_from_creature(world.bestiary[cid], 5, "normal", "e1", cid) for s, cid in seen.items()}
member = party.roster(3, "trading_square", 1, 5, 500, [])[0]
beings["a hire"] = party.fighter(member)
beings["a companion"] = combat.companion_fighter(world.bestiary[seen["Medium"]], 5, "c1", "Ash")
beings["the character in a fight"] = combat.fighter_from_character(c)
off = []
for name, f in beings.items():
    b = body.of_fighter(f)
    u = body.unhurt(b)
    want = body.limit("drop", body.Body(b.attrs)) * F["size"][f.size]
    shares = [body.fall(b, u * x) for x in (0.5, 1, 2.5, 4, 9)]
    if b.size != f.size or abs(u - want) > 1e-6 or [round(x, 3) for x in shares] != [0, 0, 0.5, 1, 1]:
        off.append((name, b.size, u, want, shares))
check("every being that can stand in a fight gives its body, and falls by the same table: a creature of each size, a hire, a companion, "
      "the character", len(seen) >= 4 and len(beings) >= 7 and not off, (sorted(seen), off))
me = body.of_character(c)
check("a character gives their own body, with what their gear adds, and a townsperson an ordinary person's",
      me.size == "Medium" and all(me.attrs[a] >= getattr(c.attributes, a) for a in ruling.ATTRS)
      and body.ordinary().attrs["dexterity"] == F["ordinary"] and body.ordinary().size == "Medium")
check("what a fall took is told in the table's words, harder as it took more",
      [body.word(x) for x in (0.05, 0.2, 0.6, 1)] == [F["told"][0][1], F["told"][1][1], F["told"][2][1], F["told"][2][1]] and len(F["told"]) == 3)

# ---- the contract: a ruling names the feat, on both paths
T = targets.targets_for(ws, ws.acting)
ctx = act.context(ws, T)
ok = ActRuling.model_validate({"sense": "yes", "works": "x", "feat": {"kind": "Lift ", "size": 300}}, context=ctx)
check("a ruling names its feat: a kind from the table and a size", (ok.feat.kind, ok.feat.size) == ("lift", 300))
check("...an older kept ruling with none reads as no feat of the body", ActRuling.model_validate({"sense": "yes"}, context=ctx).feat.kind == "none"
      and Ruling.model_validate({"sense": "yes"}, context=ctx).feat.kind == "none")
check("...a feat of none carries no size", ActRuling.model_validate({"sense": "yes", "feat": {"kind": "none", "size": 9}}, context=ctx).feat.size == 0)
def refused(model, d):
    try:
        model.model_validate(d, context=ctx)
        return False
    except ValueError:
        return True
check("...a kind the table does not hold, or a feat with no size, is sent back, on either path",
      all(refused(m, {"sense": "yes", "feat": f}) for m in (ActRuling, Ruling) for f in ({"kind": "wingspan", "size": 3}, {"kind": "lift", "size": 0},
                                                                                         {"kind": "lift"})))
schema = act.shape(ws, T).model_json_schema()
feats = lambda s: {k for v in s["properties"]["feat"]["anyOf"] for k in v["properties"]["kind"]["enum"]}
check("the act's grammar has every ruling say its feat, a yes and a no alike, from the table's kinds or none",
      all("feat" in br["required"] and feats(br) == set(K) | {"none"} for br in schema["anyOf"]), [br["required"] for br in schema["anyOf"]])
road = ruling.shape().model_json_schema()
check("...and the road's grammar the same", "feat" in road["required"] and feats(road) == set(K) | {"none"} and road["title"] == "Ruling", road.get("required"))
asked = [act.request(ws, ws.acting, T, "lift the trough", "I lift the trough."), ruling.request(ws, "lift the trough", "I lift the trough.")]
check("both requests list the feats with what each one's size measures, and both prompts ask for it",
      all("FEATS" in a and all(f"  {k}: " in a and K[k]["unit"] in a for k in K) for a in asked) and "feat:" in act.SYSTEM and "feat:" in ruling.SYSTEM)

# ---- in play: the act's path
told, rolled, shown = [], [], []
real_narrate, real_roll, real_odds = ws.narrate, checks.roll, ruling.odds
ws.narrate = lambda event, text="": told.append(event)
ruling.odds = lambda ws_, effect, r: rolled.append(dict(r)) or real_odds(ws_, effect, r)
import ui.console as uc
uc.ledger = lambda *a, **k: shown.append(str(a[0]) if a else "")
def attempt(text, d, roll="success"):
    stub.act_ruling = d
    checks.roll = lambda odds, rng=None, c=None: (roll, 1)
    told.clear(); rolled.clear(); shown.clear()
    with ws.operation("action:other", text) as op:
        ws.on_other(types.SimpleNamespace(kind="other", summary=text.rstrip(".").removeprefix("I ")), text)
    check(f"   (the line stood: {text})", op.state == "committed", op.state)
    return told[-1] if told else ""
def weak():
    for a in ("strength", "dexterity", "constitution"):
        setattr(c.attributes, a, 10)
    c.equipment = {}
    c.health = None
weak()
top = float(pools.maximum(c, "health"))
said = attempt("I lift the granary door off its hinges.", {"sense": "cost", "why": "x", "works": "It comes away.", "stakes": {"check": "strength", "hard": "fair"},
                                                           "feat": {"kind": "lift", "size": 900}})
check("a weight far past an ordinary back is never rolled: a no, in the table's words", not rolled and "does not happen" in said
      and K["lift"]["past"] in said, (rolled, said[-300:]))
said = attempt("I shove the stone trough upright.", {"sense": "yes", "why": "x", "works": "It stands.", "feat": {"kind": "lift", "size": 170}})
check("...one a little past it is told as nearly", not rolled and K["lift"]["nearly"] in said, (rolled, said[-300:]))
said = attempt("I hoist the sack of oats onto the cart.", {"sense": "yes", "why": "x", "works": "It lands on the boards.", "feat": {"kind": "lift", "size": 100}})
check("a plain yes within reach, with effort, is rolled on the feat's own attribute at fair", rolled == [{"check": "strength", "hard": "fair"}]
      and "WORKS" in said, (rolled, said[-200:]))
attempt("I heave the keg onto my shoulder.", {"sense": "cost", "why": "x", "works": "Up it goes.", "stakes": {"check": "constitution", "hard": "easy"},
                                              "feat": {"kind": "lift", "size": 140}})
check("...near the limit it is hard, whatever the ruling said, on the ruling's own check", rolled == [{"check": "constitution", "hard": "hard"}], rolled)
said = attempt("I pick up the candle stub.", {"sense": "yes", "why": "x", "works": "You have it.", "feat": {"kind": "lift", "size": 1}})
check("...and within easy reach a plain yes is still a plain yes", not rolled and "WORKS" in said, (rolled, said[-200:]))
c.capabilities = ["flight"]
said = attempt("I rise to the top of the bell tower.", {"sense": "yes", "why": "x", "works": "You stand on the roof.", "requires": ["flight"],
                                                        "feat": {"kind": "jump_up", "size": 60}})
check("a power the character has does the feat: the table is not asked", not rolled and "WORKS" in said, (rolled, said[-200:]))
c.capabilities = []
said = attempt("I stay down in the cistern until they have gone.", {"sense": "yes", "why": "x", "works": "They pass.", "requires": ["water_breathing"],
                                                                    "feat": {"kind": "breath", "size": 400}})
check("a held breath stands in for breathing water (f618), and the body still says how long: far too long is a no",
      not rolled and K["breath"]["past"] in said, (rolled, said[-300:]))
attempt("I duck under the weir gate.", {"sense": "yes", "why": "x", "works": "You come up beyond it.", "requires": ["water_breathing"],
                                        "feat": {"kind": "breath", "size": 30}})
check("...and a short one is the stand-in's own roll", rolled == [{"check": "constitution", "hard": "hard"}], rolled)

# ---- a drop: done, and paid for
mins = ws.minutes
said = attempt("I hop down from the cart bed.", {"sense": "yes", "why": "x", "works": "You are down.", "feat": {"kind": "drop", "size": 5}})
check("a short drop within what they land is judged like any feat: with effort, on dexterity", rolled == [{"check": "dexterity", "hard": "fair"}]
      and pools.current(c, "health") == top and "THE FALL" not in said, (rolled, pools.current(c, "health"), top))
said = attempt("I let go of the gutter and drop to the yard.", {"sense": "cost", "why": "x", "works": "You are in the yard.", "stakes": {"check": "stealth", "hard": "easy"},
                                                                "fail": "noise", "feat": {"kind": "drop", "size": 16}})
lost = top - pools.current(c, "health")
check("a drop past what they land unhurt is made, rolled at hard on the ruling's check, and landed well takes half its share",
      rolled == [{"check": "stealth", "hard": "hard"}] and abs(lost - top / 3 * 0.5) < 0.51 and "WORKS" in said, (rolled, lost, top))
check("...the narrator is told the fall and what it took in the table's words, and never that no one is harmed",
      "THE FALL" in said and body.word(1 / 6) in said and "16 feet" in said and "no one is harmed" not in said, said[-500:])
check("...and the player is shown what it cost", any("health" in x for x in shown), shown)
c.health = None
said = attempt("I swing off the signpost arm and drop to the square.", {"sense": "cost", "why": "x", "works": "You are down.", "fail": "hurt",
                                                                       "feat": {"kind": "drop", "size": 16}}, "failure")
lost = top - pools.current(c, "health")
check("...landed badly it takes its whole share and no more (the ruling's own knock is not added)", abs(lost - top / 3) < 0.51 and "THE FALL" in said
      and body.word(1 / 3) in said and "FAILS" in said and "They land badly" in said, (lost, top, said[-400:]))
c.health = None
said = attempt("I climb out of the loft window and let myself fall.", {"sense": "cost", "why": "x", "works": "You are down.", "fail": "hurt",
                                                                      "feat": {"kind": "drop", "size": 16}}, "partial")
lost = top - pools.current(c, "health")
check("...landed roughly it takes three quarters of it, and is told as rough, never as well", abs(lost - top / 3 * 0.75) < 0.51
      and "They land roughly" in said and "land well" not in said, (lost, top, said[-300:]))
c.health = top * 0.25
said = attempt("I roll off the awning to the cobbles.", {"sense": "cost", "why": "x", "works": "You are down.", "fail": "hurt",
                                                         "feat": {"kind": "drop", "size": 16}}, "failure")
check("a fall that would kill only if landed badly leaves them at 1, as every harm outside a fight does", pools.current(c, "health") == 1.0
      and c.deaths == 0, (pools.current(c, "health"), c.deaths))

# ---- a drop that would kill: warned first, then the game's one death
c.health = None
c.coins = 1000
home = c.last_rest if c.last_rest in world.places else world.start_location
mins, deaths = ws.minutes, c.deaths
said = attempt("I step off the top of the bell tower.", {"sense": "cost", "why": "x", "works": "You are down.", "stakes": {"check": "dexterity", "hard": "fair"},
                                                         "feat": {"kind": "drop", "size": 90}})
check("a drop no landing saves is not made the first time: no roll, no harm, no time, and the telling stops at the edge",
      not rolled and pools.current(c, "health") == top and ws.minutes == mins and c.deaths == deaths and "has not jumped" in said
      and "90 feet" in said, (rolled, pools.current(c, "health"), ws.minutes - mins, said[-400:]))
check("...the player is shown it plainly, and the warning is kept for this character at this place",
      any("90 feet" in x and "kill" in x for x in shown) and act.warned(ws, ws.acting)
      and store.load_fall_warned() == {ws.acting: {"place": "trading_square", "feet": 90}}, (shown, store.load_fall_warned()))
with ws.operation("action:go", "a walk") as op:
    ws.enter("docks" if "docks" in world.places else next(p for p in world.places if p != "trading_square" and not world.places[p].danger))
    ws.enter("trading_square")
check("the warning is dropped when they leave the place", not act.warned(ws, ws.acting) and store.load_fall_warned() == {}, store.load_fall_warned())
attempt("I step off the top of the bell tower.", {"sense": "cost", "why": "x", "works": "You are down.", "feat": {"kind": "drop", "size": 90}})
check("...so back again they are warned again", not rolled and act.warned(ws, ws.acting) and c.deaths == deaths)
weak()
c.health = top * 0.1
attempt("I slide off the low roof of the smokehouse.", {"sense": "cost", "why": "x", "works": "You are down.", "feat": {"kind": "drop", "size": 16}})
check("a wounded character is warned of a lesser fall that would take all they have left even landed well, though warned of the tower: "
      "a warning is of that drop", not rolled and store.load_fall_warned()[ws.acting]["feet"] == 16 and c.deaths == deaths
      and "has not jumped" in told[-1], (rolled, store.load_fall_warned(), c.deaths))
c.health = None
attempt("I drop off the smokehouse roof after all.", {"sense": "cost", "why": "x", "works": "You are down.", "feat": {"kind": "drop", "size": 16}})
check("healed, that drop is survived, and making it spends the warning: the next deadly drop here is warned of afresh",
      rolled and c.deaths == deaths and store.load_fall_warned() == {}, (rolled, c.deaths, store.load_fall_warned()))
c.health = None
attempt("I jump from the bell tower's top to the stones.", {"sense": "cost", "why": "x", "works": "You are down.", "feat": {"kind": "drop", "size": 110}})
check("...warned afresh", not rolled and c.deaths == deaths and store.load_fall_warned()[ws.acting]["feet"] == 110)
shown_all = simlib.quiet_console()
uc.ledger = lambda *a, **k: shown.append(str(a[0]) if a else "")
attempt("I throw myself from the bell tower.", {"sense": "cost", "why": "x", "works": "You are down.", "feat": {"kind": "drop", "size": 95}})
check("warned, a deadly drop tried again here is made, however it is worded: the game's one death, never rolled",
      not rolled and c.deaths == deaths + 1 and c.coins == 500 and ws.player.location == home
      and ws.minutes - mins >= combat.RULES["death"]["days_pass"] * 1440, (rolled, c.deaths, c.coins, ws.player.location, ws.minutes - mins))
check("...told as a fall in the engine's own words before the Threshold, and the warning is spent",
      any(t in {x.format(feet="95") for x in F["died"]} for k, t in shown_all if k == "narrate") and store.load_fall_warned() == {},
      ([t for k, t in shown_all if k == "narrate"][:2], store.load_fall_warned()))
try:
    act.act(ws, "someone_else", "jump", "I jump.")
    other = False
except ValueError:
    other = True
check("an act is still played for the scene's own character only", other)
ws.narrate, checks.roll, ruling.odds = real_narrate, real_roll, real_odds

# ---- the road's ruling: the same reader
ws.enter("trading_square")
weak()
noted = []
for fn in ("note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: noted.append((_fn, str(a[0]) if a else "")))
hz = {"tier": "normal", "what": "A span of the bridge gone, the river loud below.", "behind": "parth"}
def road_past(d, roll="success"):
    stub.ruling = d
    noted.clear(); rolled.clear()
    checks.roll = lambda odds, rng=None, c=None: (roll, 1)
    ruling.odds = lambda ws_, effect, r: rolled.append(dict(r)) or real_odds(ws_, effect, r)
    ws.get_past(dict(hz), "I keep going")
    checks.roll, ruling.odds = real_roll, real_odds
road_past({"sense": "cost", "why": "x", "stakes": {"check": "dexterity", "hard": "fair"}, "feat": {"kind": "jump_across", "size": 30}})
check("on the road a jump past the body's limit is no way through: they go around", not rolled and any("no pushing straight through" in t for _, t in noted),
      (rolled, noted))
road_past({"sense": "yes", "why": "x", "feat": {"kind": "jump_across", "size": 7}})
check("...one within reach near the limit is rolled at hard on the feat's attribute", rolled == [{"check": "strength", "hard": "hard"}]
      or rolled == [{"check": "dexterity", "hard": "hard"}], rolled)
road_past({"sense": "yes", "why": "x", "feat": {"kind": "jump_across", "size": 2}})
check("...and one within easy reach walks on", not rolled and not noted, (rolled, noted))
road_past({"sense": "cost", "why": "x", "stakes": {"check": "dexterity", "hard": "fair"}, "feat": {"kind": "drop", "size": 60}})
check("...a drop that would hurt is not jumped on the road: around", not rolled and any("no pushing straight through" in t for _, t in noted), (rolled, noted))

# ---- the measure reads the feat
sys.path.insert(0, "tools")
from tools import ruling_eval
case = {"line": "I lift the trough.", "at": "trading_square", "expect": "no", "kind": "feat", "feat": {"kind": "lift", "size": [200, 900]}}
named = lambda spec, kind, size: ruling_eval.named({**case, "feat": spec}, types.SimpleNamespace(feat=types.SimpleNamespace(kind=kind, size=size)))
check("the measure reads a ruling's feat against a case: the kind right and the size inside its range",
      [named(case["feat"], "lift", 300), named(case["feat"], "carry", 300), named(case["feat"], "lift", 60), named("none", "none", 0),
       named("none", "lift", 20)] == ["ok", "kind", "size", "ok", "kind"])
check("...and a case may hold more than one fair answer", named(["none", {"kind": "lift", "size": [10, 150]}], "none", 0) == "ok"
      and named(["none", {"kind": "lift", "size": [10, 150]}], "lift", 90) == "ok" and named(["none", {"kind": "lift", "size": [10, 150]}], "lift", 900) == "size")
check("a feat case with no feat, a kind the table does not hold or a range that is not two rising numbers is refused as a file",
      not ruling_eval.problems([case]) and all(ruling_eval.problems([{**case, "feat": f}]) for f in ({"kind": "wingspan", "size": [1, 2]}, {"kind": "lift", "size": 5},
                                                                                                     {"kind": "lift", "size": [9, 2]}, None))
      and ruling_eval.problems([{k: v for k, v in case.items() if k != "feat"}]) and "feat" in ruling_eval.KINDS)
FEATS = ruling_eval.ROOT / "data" / "replay" / "ruling_cases_feat.yaml"
mine = ruling_eval.load(FEATS)
flat = lambda f: f if isinstance(f, list) else [f]
check("the corpus holds forty feat cases: every kind of the table, a good share that are no feat of the body, each with a body and a ruling to try offline",
      len(mine) >= 40 and {a["kind"] for x in mine for a in flat(x["feat"]) if isinstance(a, dict)} == set(K)
      and sum(1 for x in mine if x["feat"] == "none") >= 10 and all(x.get("kind") == "feat" and "body" in x and x.get("model") for x in mine)
      and not ruling_eval.problems(mine), (len(mine), sum(1 for x in mine if x["feat"] == "none"), ruling_eval.problems(mine)))
import subprocess
run = subprocess.run([sys.executable, "tools/ruling_eval.py", "--cases", str(FEATS)], capture_output=True, text=True, encoding="utf-8")
check("...and offline the table answers every one of them as the case says, the deadly drop called deadly",
      run.returncode == 0 and f"{len(mine)} of {len(mine)} right" in run.stdout and run.stdout.count("deadly: warned, then a death") == 1
      and "WRONG" not in run.stdout, (run.returncode, run.stdout[-900:], run.stderr[-600:]))
lie = {**mine[0], "model": {**mine[0]["model"], "feat": {"kind": "lift", "size": 40}}}
check("...a case whose own ruling names a feat its case does not call fair is refused as a file, and so is a deadly that is no feat case",
      any("own ruling" in p for p in ruling_eval.problems([lie])) and ruling_eval.problems([{"line": "x", "expect": "no", "deadly": True}]))
check("the file says what its expectations are: the table's arithmetic, not the owner's rulings", "NOT rulings of the owner's" in FEATS.read_text(encoding="utf-8"))

if bad:
    print(f"\n{len(bad)} FAILED: {bad}")
    sys.exit(1)
print("\nall ok")
