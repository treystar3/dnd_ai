"""(f724) The engine's decision for a reply (docs/design/28_phase4_plan.md, A2; engine/reply.py, data/rules/reply.yaml). Before a
townsperson is asked to speak, the engine settles what it can without reading the line: how they are for this talk (the stance,
by its key), the move they make (weighted by the stance, their trust in this character and the habits of their voice; never the
same move three replies running; the game's own decisions force an answer), and what they could share (the lore picked for the
line as before, with the town's news, happenings and postings that bear on it or are asked for) with whether they would.
No model call is made for it, and behind its switch nothing a player reads changes: with the switch off nothing is rolled or
kept, and with it on the request for the reply is the one it was.
Run: python tools/sim/reply_decision_724_test.py"""
import copy
import random
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
SHOWN = simlib.quiet_console(("narrate", "say", "note", "ledger", "debug"))
from engine import actor, brief, data_check, regard, relevance, truth, voice_rules
from llm.gateway import LLMError
from world.loader import Fact

try:
    from engine import reply
except ImportError:
    reply = None

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


if reply is None:
    check("engine/reply.py is there", False)
    sys.exit(1)

# ---- the data: the switch is off as shipped, the tables are checked at startup
check("the switch is off as shipped, and the tables pass their check", reply.R.get("decide_then_speak") is False and reply.problems() == []
      and not [p for p in data_check.check() if "reply.yaml" in p], reply.problems())
D = copy.deepcopy(reply.R)
D["moves"]["by_stance"]["sulking"] = {"answer": 2}
D["moves"]["by_kit"]["questions"]["sometimes"] = {"ask_back": 2}
D["moves"]["kinds"]["sing"] = {"weight": 0}
D["moves"]["by_trust"]["low"]["shrug"] = 2
D["share"].pop("news")
found = reply.problems(D)
check("a stance or a habit of voice the game does not have, a move with no weight, a move not in the table, a kind with no rule: each is refused",
      all(any(w in p for p in found) for w in ("sulking", "sometimes", "moves.kinds", "by_trust.low", "share:")), found)
D = copy.deepcopy(reply.R)
D["moves"]["by_kit"]["refusing"] = None
D["share"]["news"] = {"gate": True}
D["share"]["secret"] = {"trust": 0}
D["share"]["board"] = "anyone"
D["moves"]["forced"] = ["answer"]
found = reply.problems(D)
check("a row of the wrong shape is reported, not fallen over", any("share.board" in p for p in found) and any("moves.forced" in p for p in found), found)
check("a habit of voice with nothing under it, a gate on anything but the secret, a secret with no gate: each is refused",
      all(any(w in p for p in found) for w in ("by_kit.refusing", "share.news", "share.secret")), found)
check("a line of the game's own that says what they must say is known by how it begins; what the turn has settled is no such line",
      reply.must_say(["", "[THE GAME HAS DECIDED: you are shaken. You almost say too much.]"]) is True
      and reply.must_say(["WHAT THE GAME HAS DECIDED THIS TURN (true; say nothing against it): the bread was bought.", ""]) is False)

# ---- the stance by its key
S = voice_rules.V["stances"]


class Person:
    id, activity, concern, motive, speech = "p1", "mending a net.", "the weir is silting up", "a buyer for the old boat", {}


texts = {k: S[k]["text"].format(activity="mending a net", concern=Person.concern, motive=Person.motive) for k in S}
kind = getattr(voice_rules, "stance_kind", lambda text: None)
check("the stance of a talk is read back by its key from the line it was told as, and no stance is 'none'",
      all(kind(t) == k for k, t in texts.items()) and kind("") == "none", {k: kind(t) for k, t in texts.items()})
check("...by the words before its colon: a talk kept from when the line ran otherwise after them is still its stance",
      kind("busy: your hands do not stop, in some older wording") == "busy" and kind(S["wary"]["text"].split(":")[0] + ": anything") == "wary"
      and kind("at ease") == "none")
check("...and two stances that begin alike are refused at startup (neither could be told from the other)",
      voice_rules.stance_problems() == [] and voice_rules.stance_problems({"a": {"text": "busy: x"}, "b": {"text": "busy at the bench: y"}}) != [])

# ---- the move: weighted by the stance, their trust, their voice
KIT = {"questions": "never"}
base = reply.weights("none", 50, {}, {"concern"})
check("every move is theirs when nothing bends it, at the table's weights", set(base) == set(reply.R["moves"]["kinds"])
      and base["answer"] == reply.R["moves"]["kinds"]["answer"]["weight"], base)
check("one who never asks anything back never makes the move of asking back", "ask_back" not in reply.weights("none", 50, KIT, {"concern"}))
check("turning to their own trouble needs a trouble; nursing a grievance it is their likeliest move",
      "own_trouble" not in reply.weights("none", 50, {}, set()) and max(reply.weights("grievance", 50, {}, {"concern"}).items(), key=lambda x: x[1])[0] == "own_trouble",
      reply.weights("grievance", 50, {}, {"concern"}))
low, high = reply.weights("none", 10, {}, {"concern"}), reply.weights("none", 90, {}, {"concern"})
check("little trust makes a plain answer rarer and turning it aside commoner; much trust the other way",
      low["answer"] < base["answer"] < high["answer"] and low["deflect"] > base["deflect"] > high["deflect"], (low, high))
kept = reply.R["moves"]["by_kit"]
reply.R["moves"]["by_kit"] = {**kept, "refusing": None, "questions": {"never": None}}
try:
    lax = reply.weights("none", 50, {"questions": "never", "refusing": "flat"}, {"concern"})
except Exception as e:
    lax = repr(e)
reply.R["moves"]["by_kit"] = kept
check("a habit's table left empty bends nothing (the roll does not fall over on it)", lax == base, lax)
wary = reply.weights("wary", 50, {}, set())
check("wary, they ask what you want before they answer", wary["ask_back"] > base["ask_back"] and wary["answer"] < base["answer"], wary)

# ---- the roll: its own die, never three the same running, forced when the game has decided
RUN = int(reply.R["moves"]["running"])
seen, last, worst = set(), [], 0
for i in range(600):
    m = reply.roll_move(base, last, random.Random(f"m{i}"))
    last = (last + [m])[-8:]
    seen.add(m)
    tail = 1
    while tail < len(last) and last[-tail - 1] == m:
        tail += 1
    worst = max(worst, tail)
check("over many replies every move is made, and none more than the table's run in a row", seen == set(base) and worst <= RUN, (sorted(seen), worst))
check("the same die gives the same move", len({reply.roll_move(base, ["part"], random.Random("same")) for _ in range(5)}) == 1)
check("when the game has decided what must be said they answer, whatever the run", reply.roll_move(base, ["answer"] * 5, random.Random(1), forced=True) == "answer")
check("one with a single move makes it again (there is nothing else for them to do)", reply.roll_move({"answer": 1.0}, ["answer"] * 3, random.Random(1)) == "answer")

# ---- what they would share
gate = int(voice_rules.V["exemplars"]["refusal_trust"])
check("news is for someone they do not distrust (the line under which their examples are refusals); a clue, a happening in the street, a posting: for anyone",
      reply.would_share("news", gate - 1)[0] is False and reply.would_share("news", gate)[0] is True and reply.would_share("news", gate - 1)[1]
      and all(reply.would_share(k, 0)[0] for k in ("lore", "clue", "happening", "board")), reply.would_share("news", gate - 1))
shut = reply.secret({"open": False, "pressed": True, "secret": {"kind": "arc", "node": "n1"}}, "The seal was cut at the mill.")
opened = reply.secret({"open": True, "pressed": True, "secret": {"kind": "arc", "node": "n1"}}, "The seal was cut at the mill.")
check("a secret is theirs to tell only while its gate is open, and while it is shut nothing of it is written down",
      len(shut) == 1 and shut[0].share is False and shut[0].text == "" and opened[0].share is True and "mill" in opened[0].text and reply.secret(None) == [], (shut, opened))

# ---- the lore for the line, with the town's pieces: one ranking, the lore as it was
facts = [Fact(id=f"lore_{i}", text=f"The old mill number {i} grinds barley for the valley farms.", known_by=[]) for i in range(20)]
facts += [Fact(id="ford_toll", text="The ford below the bridge has a toll keeper who takes copper from carts.", known_by=[]),
          Fact(id="wolves_north", text="Wolves have come down from the northern ridge this winter.", known_by=[]),
          Fact(id="clue:t1:0", text="The miller's boy saw lantern light in the barn at night.", known_by=[])]
LINE = "Have you seen wolves near the ford, and who keeps the toll?"
news = [truth.Fact("news", "Wolves took three sheep from the upper pasture by the ford.", id="news:1"),
        truth.Fact("news", "The reeve's daughter is to marry at midsummer.", id="news:2"),
        truth.Fact("happenings", "A funeral crosses the square for the old ferryman.", id="happening:1")]
RANKED = []
real_ranked = relevance.ranked


def spy_ranked(query, items, floors=None):
    RANKED.append((query, list(items)))
    return real_ranked(query, items, floors)


relevance.ranked = spy_ranked
before = brief.lore(facts, LINE, [])
alone = list(RANKED)
del RANKED[:]
try:
    shown, index = brief.lore(facts, LINE, [], also=news)
except TypeError as e:
    shown, index = [], str(e)
with_town = list(RANKED)
ids = [str(f.id) for f in shown]
check("the lore is ranked in the call it was (the same line, the same texts), and the town's pieces in a call of their own: only those that share a word with the line",
      len(alone) == 1 and with_town[:1] == alone and len(with_town) == 2 and with_town[1][1] == [news[0].text],
      (len(alone), [len(c[1]) for c in with_town]))
del RANKED[:]
only = [str(f.id) for f in brief.lore(facts[-1:], LINE, [], also=news)[0]]
check("...with no lore that bears on the line its ranking is not asked for, as before; the pieces' own is",
      len(RANKED) == 1 and set(RANKED[0][1]) <= {f.text for f in news} and only == ["clue:t1:0", "news:1"], (RANKED, only))
del RANKED[:]
brief.lore(facts, LINE, [], also=[], whole=news[1:])
check("...and with no piece that may bear on it, no call but the lore's", len(RANKED) == 1 and RANKED == alone, RANKED)
relevance.ranked = real_ranked
twins = [truth.Fact("news", facts[21].text, id="news:9"), truth.Fact("news", facts[21].text, id="news:10")]
dup = brief.lore(facts, LINE, [], also=twins + news, whole=[truth.Fact("happenings", facts[20].text, id="happening:9"), news[2], news[2]])[0]
check("a piece in the very words of lore they were given, or given twice, is in the reply's brief once: nothing is said to them twice",
      {"ford_toll", "wolves_north"} <= {str(f.id) for f in before[0]} and len([f.text for f in dup]) == len({f.text for f in dup})
      and not {"news:9", "news:10", "happening:9"} & {str(f.id) for f in dup} and [str(f.id) for f in dup].count("happening:1") == 1
      and [str(f.id) for f in dup if reply.kind_of(f) in ("lore", "clue")] == [str(f.id) for f in before[0]], [str(f.id) for f in dup])
check("the town's pieces are ranked beside the lore: the lore picked is the lore that was picked, and a piece that bears on the line comes with it",
      [i for i in ids if reply.kind_of(type("F", (), {"id": i})) in ("lore", "clue")] == [str(f.id) for f in before[0]] and "news:1" in ids, ids)
check("...a piece that does not bear on the line stays out, and no piece is named among what else they know",
      "news:2" not in ids and "happening:1" not in ids and index == before[1], (ids, index[:80]))
whole = brief.lore(facts, LINE, [], also=news[:1], whole=news[1:])[0] if shown else []
check("...a piece whose facet the line asks for comes in whole, bearing on it or not", {"news:2", "happening:1"} <= {str(f.id) for f in whole}, [str(f.id) for f in whole])
many = [truth.Fact("news", f"Wolves were seen at the ford toll again, the {n} time.", id=f"news:{i}") for i, n in enumerate(("first", "second", "third", "fourth", "fifth"))]
got = [str(f.id) for f in brief.lore(facts, LINE, [], also=many)[0]] if shown else []
check("...and of many that bear on it, no more than the brief's own number", 0 < sum(1 for i in got if i.startswith("news:")) <= int(brief.rules().get("town_pieces", 0)), got)
check("the line that asks for the news is known by its words, as the town's list and the board are", brief.asked("news", "Any news in town?")
      and brief.asked("news", "What have you heard lately?") and not brief.asked("news", "How much for a waterskin?"))
check("...and a line that only has a word of hearing or happening in it does not ask for the news",
      not any(brief.asked("news", l) for l in ("Did you hear me?", "What happened to your arm?", "Are you in trouble?", "Where did you hear that song?")))

# ---- in play: off, nothing is rolled or kept; on, the decision is made and the request is the one it was
game = simlib.campaign("reply_decision_724", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter(ws.player.location)
REQ = []
real = simlib.below()


def chat(**k):
    if k["format"].get("title") == "NPCReply":
        REQ.append(k["messages"][1]["content"])
    return real.chat(**k)


spy = simlib.stand_in(chat=chat)
npc = sorted((n for n in ws.present if n.role not in ("guild_clerk", "guild_master")), key=lambda n: n.id)[0]


def say(words):
    stub.plan = [{"kind": "talk", "target": npc.id, "speech": words}]
    ws.turn(f'I say, "{words}"')
    stub.plan = None


def asked_of_the_model(fn):
    before = dict(stub.calls)
    fn()
    return {k: v - before.get(k, 0) for k, v in stub.calls.items() if v != before.get(k, 0)}


say("Fine weather today.")
off_calls = asked_of_the_model(lambda: say("A quiet morning for it."))
check("with the switch off nothing is decided or kept: no decision, no moves, the talk's record as it was",
      getattr(ws, "decision", None) is None and not getattr(ws, "moves", None) and "moves" not in ws.talk_record() and len(REQ) == 2,
      (getattr(ws, "decision", None), getattr(ws, "moves", None), ws.talk_record().keys()))
check("the talk's moves are the scene's and the decision the line's, each declared with what a failed operation does with it (put back)",
      "moves" in actor.ATTRS and actor.ATTRS["moves"].how == actor.ROLLED and "decision" not in actor.ATTRS
      and "decision" in actor.FIELDS and actor.FIELDS["decision"].marks == {actor.LINE, actor.ROLLED})

reply.R["decide_then_speak"] = True
try:
    on_calls = asked_of_the_model(lambda: say("And how is trade?"))
    d = getattr(ws, "decision", None)
    check("with it on, the reply has its decision: who speaks, to whom, how they are, the move, what they could share",
          d is not None and d.speaker == npc.id and d.to == ws.acting and d.stance == voice_rules.stance_kind(ws.stance)
          and d.move in reply.R["moves"]["kinds"] and all(c.kind in reply.KINDS and isinstance(c.share, bool) for c in d.candidates),
          d)
    check("...made by the engine: the reply's own call and (f725) the one reading of the line, and nothing a reply did not ask for before",
          on_calls.get("NPCReply") == 1 and on_calls.get("NPCDecision", 0) <= 1 and set(on_calls) <= set(off_calls) | {"DialogueFrame", "NPCDecision"}
          and "NPCReply" in off_calls and "NPCDecision" not in off_calls, (off_calls, on_calls))
    check("...a line that asks nothing of the board has no posting among what they could share; one that asks for work has",
          not any(c.kind == "board" for c in d.candidates), [c.id for c in d.candidates])
    check("...the move is kept with the talk, in the scene and in its record", ws.moves == [d.move] and ws.talk_record().get("moves") == [d.move], (ws.moves, ws.talk_record()))
    check("...and the engine says what it decided where the debug console shows it", any(k == "debug" and "decided: move " + d.move in str(t) for k, t in SHOWN), [t for k, t in SHOWN if k == "debug"][-3:])
    say("Is there any work going on the board?")
    check("...and asked for work, the postings are theirs to share", any(c.kind == "board" and c.share for c in ws.decision.candidates),
          [c.id for c in ws.decision.candidates])
    made = [d.move, ws.decision.move]
    for words in ("Is the road north safe?", "Who keeps the hall?", "Have you family here?", "Do you get many travellers?", "What do you make of the weather?"):
        say(words)
        made.append(ws.decision.move)
    runs = max(sum(1 for _ in g) for _, g in __import__("itertools").groupby(made))
    check("over a talk no move is made more than the table's run in a row, and the scene keeps only the run", runs <= RUN and ws.moves == made[-RUN:], (made, ws.moves))
    ws.moves = ["answer"] * RUN
    say("And the harvest, how was it?")
    free = ws.decision
    ws.moves = ["answer"] * RUN
    stub.plan = [{"kind": "talk", "target": npc.id, "speech": "Come now, you can tell me.", "checks": ["persuasion"]}]
    ws.turn('I lean in and say, "Come now, you can tell me."')          # a check rolled in the turn: the game decides how it went
    stub.plan = None
    check("in play, a reply after the run of one move makes another; when the game has decided what they must say, they answer whatever the run",
          free.forced is False and free.move != "answer" and ws.decision.forced is True and ws.decision.move == "answer"
          and "(the game decided)" in ws.decision.line(), (free.line(), ws.decision.line()))
    rec = ws.talk_record()
    ws._talk_saved = dict(rec)
    ws.end_conversation()
    ended = list(ws.moves)
    ws.restore_talk()
    check("the talk ended, its moves are gone; a save opened mid-talk has its moves again", ended == [] and rec["moves"] and ws.moves == rec["moves"], (ended, ws.moves))
    ws._talk_saved = {**rec, "moves": ["quiet", "joke", "part", "answer", "deflect"]}
    ws.end_conversation()
    ws.restore_talk()
    check("...and no more of them than the run, whatever the save holds", ws.moves == ["quiet", "joke", "part", "answer", "deflect"][-RUN:], ws.moves)
    stub.plan = [{"kind": "look"}]
    ws.turn("I look around.")
    stub.plan = None
    check("a line in which no one replies has no decision: it is the line's, never one left over", ws.decision is None, ws.decision)

    # the request is the one it was: the same person, line and dice, with the decision and without
    from npc import life
    from engine import streams
    view = truth.scene_of(ws).view(truth.viewer_for_npc(npc, ws.world), "townsfolk")
    args = (npc, store, ws.world, ws.catalog, list(ws.convo), "Have you heard any news of the road?", [], view.text(), "", None, [], None, ws.acting, "she")

    def request(decision):
        rng = random.Random("req")
        return str(life._request(*args[:9], rng, *args[10:], decision=decision)[0] if decision is not None else life._request(*args[:9], rng, *args[10:])[0])

    plain = request(None)
    d2 = reply.Decision(npc.id, ws.acting, around=reply.pieces(view, "Have you heard any news of the road?"))
    check("the request for the reply is the same with the decision and without (nothing a player reads changes)",
          request(d2) == plain and "Have you heard" in plain and d2.move in reply.R["moves"]["kinds"], d2.line())

    # the same with news in town and a happening in the street: the pieces have ids, come in only as they bear, and the request is the one it was
    from engine import pulse
    real_window, real_happen = pulse.news_window, pulse.happenings_at
    row = {"minute": ws.minutes, "origin": ws.player.location, "groups": ["everyone"], "times": 1}
    pulse.news_window = lambda *a, **k: [{**row, "text": "Wolves were seen on the north road by the gate."}, {**row, "text": "The chandler's cat had kittens in the loft."}]
    pulse.happenings_at = lambda *a, **k: ["A funeral crosses the square for the old ferryman."]
    try:
        town = truth.Scene(ws)
        view = town.view(truth.viewer_for_npc(npc, ws.world), "townsfolk")
        view.drop |= {"town", "board"}                       # as the scene has it for a line that asks for neither
        named = {facet: [str(f.id) for f in town.facts(facet)] for facet in ("news", "happenings")}
        check("the town's news and what is happening in its streets carry ids of their kind; the ordinary day has none",
              named["news"] == ["news:0", "news:1"] and [i for i in named["happenings"] if i] == ["happening:0"], named)
        ASK = "Is the north road safe from wolves these days?"
        whole, maybe = reply.pieces(view, ASK)
        told, _ = reply.pieces(view, "Any news in town?")
        check("a line about something else has them as what may bear on it; a line that asks for the news has them whole",
              not whole and {"news:0", "news:1", "happening:0"} <= {str(f.id) for f in maybe} and {"news:0", "news:1"} <= {str(f.id) for f in told},
              ([str(f.id) for f in whole], [str(f.id) for f in maybe], [str(f.id) for f in told]))
        say(ASK)
        in_play = [c.id for c in ws.decision.candidates]
        check("...in play, the scene's own decision has the piece that bears on the line and neither of the others",
              "news:0" in in_play and "news:1" not in in_play and "happening:0" not in in_play, in_play)
        args = (npc, store, ws.world, ws.catalog, list(ws.convo), ASK, [], view.text(), "", None, [], None, ws.acting, "she")
        plain = request(None)
        d4 = reply.Decision(npc.id, ws.acting, around=(whole, maybe))
        with_town = request(d4)
        got = [c.id for c in d4.candidates]
        check("...the request is still the one it was, and of the town's pieces only the one that bears on the line is theirs to share",
              with_town == plain and "north road" in plain and "news:0" in got and "news:1" not in got and "happening:0" not in got, got)
    finally:
        pulse.news_window, pulse.happenings_at = real_window, real_happen
    regard.own(npc, ws.acting).trust = 5
    d3 = reply.settle(reply.Decision(npc.id, ws.acting), npc, [truth.Fact("news", "Wolves at the ford.", id="news:1"), Fact(id="ford_toll", text="A toll.", known_by=[])],
                      random.Random(3))
    check("one who trusts the character little could say the news and would not; the lore of their circles is still theirs to tell",
          [(c.id, c.kind, c.share) for c in d3.candidates] == [("news:1", "news", False), ("ford_toll", "lore", True)] and "would not" in d3.line(), d3.line())

    # a reply that fails: the talk's moves as they were, the line with no decision
    from engine import voices
    real_heard = voices.heard
    ws.moves = was = ["part"]

    def fall(*a, **k):
        raise LLMError("the model failed")

    voices.heard = fall
    try:
        say("And what of the winter stores?")
    finally:
        voices.heard = real_heard
    check("a reply that failed leaves the talk's moves as they were and the line with no decision (both put back)",
          ws.moves == was and ws.decision is None, (was, ws.moves, ws.decision))
finally:
    reply.R["decide_then_speak"] = False
spy()
game.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
