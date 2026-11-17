"""(f644) What a line says it did is read from what was committed (docs/design/21_play_faults_plan.md, A2; found in play:
docs/play/2026-11-15_play_findings.md 3.1, 3.3). The line that told which part of a typed line stood was built from a list of the
steps that finished, and a hand-in before a talk is no step: so a contract paid was told as "the first of it. The rest of the line
did not take". Held here:
- an operation of the player's says what it did as it runs, and a line told in part names what the operations that stood said, in
  order, and nothing else: a contract handed to the clerk whose reply fails; a deed, then a hand-in; three deeds failing at the
  second, and at the third; a walk, then a failure; a hand-in made inside a step the game said no to;
- a step the game said no to is told by its refusal and is not named as done: of the save only the count of turns moves;
- "nothing happened" is said only of a line that left the character as they were;
- a deed taken back because a spoken reply to it could not be written is told as that once the lines for it are in the data, and
  as a turn not taken until then; the night counts either as a turn not taken; from a pane's button too;
- over every line this test types: what the player is told agrees with what moved in the save.
Run: python tools/sim/line_stood_644_test.py"""
import dataclasses
import json
import pathlib
import random
import re
import shutil
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import config
import ui.console as uc
from engine import actor, failures, inventory, mentor, money, operation, quests
from llm.contracts import ActionIntent
from llm.gateway import LLMError
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


F = failures.F
NAME = "line_stood_644"
# The lines for a reply that did not come, and the phrase a walk is named by, are the owner's to read before they are data: the
# game is held here with a list of this test's own in their place, and again with none (the last section).
UNSAID = ["No reply came to that, and so it was not done; nothing was spent.", "The words that should have met that never came; all is as it was.",
          "That waited on a reply, and none came; nothing was given or taken.", "It did not take: no words came back for it, and nothing was paid.",
          "No word came back, so the moment was let go whole; nothing of yours was spent.", "The reply to that was lost, and the deed with it; all you had is yours."]
check("the data holds no line for a reply that did not come until the owner has read them, and the walk's phrase the owner read (f715)",
      "reply_not_come" not in F and F.get("walked") == "walked to {where}" and not failures.problems(), sorted(F)[:40])
F["reply_not_come"] = list(UNSAID)
import nightrun
real = simlib.below()
FAIL = {"titles": set()}
ASKED = []


def chat(**k):
    title = k["format"].get("title")
    ASKED.append(title)
    if title in FAIL["titles"]:
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


held = simlib.stand_in(chat=chat, embed=None)
g = simlib.campaign(NAME, cls="warrior", seed=3, minutes=120, location="guild_house")
config.TURN_LOG_PATH, config.CRASH_LOG_PATH = f"saves/{NAME}/turns.jsonl", f"saves/{NAME}/crash.log"
ws, store = g.scene, g.store
ws.enter("guild_house")
stub.plan = [{"kind": "look"}]
ws.turn("I look around.")                      # the board's first refresh at the hall is behind us
stub.plan = None
clerk = ws.clerk_here()
check("the hall has its clerk, and someone else", clerk is not None and any(n.id != getattr(clerk, "id", "") for n in ws.present))
cid = clerk.id
tid = sorted(n.id for n in ws.present if n.id != cid)[0]


def shape(template: str):
    """A stand-in's template as a pattern: its words, with whatever was named where a placeholder stands."""
    return re.compile("^" + re.sub(r"\\\{\w+\\\}", "(.+)", re.escape(template)) + "$", re.S)


def said(read: list, key: str):
    """The first line read that is one of this list's, and what it named: (line, named) or None."""
    for t in read:
        for template in F.get(key) or []:
            m = shape(template).match(t)
            if m:
                return t, (m.group(1) if m.groups() else "")
    return None


def character() -> dict:
    """The character as the save has them: where they are, what they carry and are owed, what is asked of them."""
    p = store.load_player()
    return {"at": p.location, "coins": p.character.coins, "xp": p.character.xp, "level": p.character.level, "health": p.character.health,
            "pack": sorted((i.good or i.name, i.quantity) for i in p.character.inventory), "quests": sorted(str(q["id"]) for q in p.quests)}


NOT_TAKEN = ("turn_not_taken", "turn_not_possible", "reply_not_come")
RAN = []


def typed(text: str, plan, fail=(), first=None):
    """One line typed at the prompt, as the player types it: what they read, what the turn log says stood, and what moved (the
    tables of the save that differ). `first` is done once the game is waiting at the prompt, before the line is typed."""
    stub.plan, FAIL["titles"] = plan, set(fail)
    before, was, minute = statehash.dump(store), character(), ws.minutes
    script = [text, "quit"]

    def ask(*a, **k):
        if len(script) == 2 and first is not None:
            first()
        return script.pop(0) if script else "quit"
    uc.put("ask", ask)
    n = len(SHOWN)
    del ASKED[:]
    try:
        ws.run()
    finally:
        stub.plan, FAIL["titles"] = None, set()
    rows = [json.loads(l) for l in pathlib.Path(config.TURN_LOG_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
    now = character()
    diff = statehash.changes(before, statehash.dump(store))
    moved = sorted(f"{t}.{row}.{col.split('.')[-1]}" for t, kinds in diff.items() for rows in kinds.values() for row, cols in rows.items()
                   for col in (cols if isinstance(cols, dict) else [""]))
    rec = {"text": text, "same": not moved, "moved": moved, "was": was, "now": now, "minutes": ws.minutes - minute,
           "read": [t for k, t in SHOWN[n:]], "stood": rows[-1].get("stood"), "failed": [o.kind for o in ws.line_failed],
           "kinds": [o.kind for o in ws.line_ops], "asked": list(ASKED)}
    rec["part"] = said(rec["read"], "part_stood")
    rec["nothing"] = next((said(rec["read"], k) for k in NOT_TAKEN if said(rec["read"], k)), None)
    RAN.append(rec)
    return rec


def owed(title: str, creature: str = "wolf") -> dict:
    """A guild contract, finished and not yet handed in (as tools/sim/clerk_test.py makes one)."""
    q = quests._quest("hunt", "F", title, ws.minutes, place="greywood", creature=creature, count=3)
    q["progress"] = 3
    ws.player.quests = ws.player.quests + [q]
    store.save_player(ws.player)
    return q


def names(rec, *wanted, never=()):
    """The part line names these, in this order, and none of those."""
    if rec["part"] is None:
        return False
    told, at = rec["part"][1], -1
    for w in wanted:
        if told.find(w, at + 1) < 0:
            return False
        at = told.find(w, at + 1)
    return not any(x in told for x in never)


SAY = {"kind": "talk", "target": cid, "speech": "The wolves are dead. I am here for the pay.", "summary": "a word with the clerk"}
LOOK = {"kind": "look", "summary": "a look around the hall"}
WAIT = {"kind": "wait", "summary": "a while spent waiting"}
SEARCH = {"kind": "search", "summary": "a search of the benches"}

# ---- the record: an operation says what it did, and the old list of finished steps is gone
check("an operation holds what it said it did, the scene keeps no list of finished steps, and what it did is no part of the saved record",
      "did" in {f.name for f in dataclasses.fields(operation.Operation)} and "line_done" not in actor.FIELDS and "line_done" not in ws.ROLLED
      and callable(getattr(ws, "line_stood", None)) and callable(getattr(operation, "did", None))
      and all("did" not in o.record() and "speech" not in o.record() for o in ws.line_ops) and ws.line_ops)
operation.did("said to nobody")
check("what is said outside any operation is said to nobody", "said to nobody" not in ws.line_stood())

# ---- 3.1: a finished contract handed to the clerk, and the clerk's reply fails. What was paid is what the line names
owed("Hunt 3 wolves in the Greywood")
a = typed("I hand in my contract to the clerk.", [dict(SAY)], fail={"NPCReply"})
paid = a["now"]["coins"] - a["was"]["coins"]
check("a contract handed in whose reply fails: the line stood in part, the pay and the contract's end kept",
      a["stood"] == "part" and paid > 0 and not a["now"]["quests"] and "action:handin" in a["kinds"] and a["failed"] == ["action:talk"]
      and "NPCReply" in a["asked"], (a["stood"], paid, a["kinds"], a["failed"]))
check("...and the player reads that the hand-in stood, by the contract's name and what it paid",
      names(a, "Hunt 3 wolves in the Greywood", money.words(paid), never=(SAY["summary"], "spoke with")), a["read"][-3:])
check("...never 'the first of it', and never that nothing happened", not any("the first of it" in t for t in a["read"]) and a["nothing"] is None, a["read"][-3:])

# ---- as in play: a deed first, then the hand-in, then the reply fails. Both are named, in order
owed("Hunt 3 boars by the mill", "boar")
b = typed('I look around the hall and say, "The boars are dead."', [dict(LOOK), dict(SAY, speech="The boars are dead.")], fail={"NPCReply"})
check("a deed, then a hand-in whose reply fails: both are named, the deed first, and the talk that did not stand is not",
      b["stood"] == "part" and names(b, "looked around", "Hunt 3 boars by the mill", money.words(b["now"]["coins"] - b["was"]["coins"]), never=(SAY["summary"], "spoke with")),
      (b["stood"], b["read"][-3:]))

# ---- three deeds: the line names what stood, in order, and nothing of what did not
def failing(intent, text):
    raise LLMError("its telling could not be written")


ws.on_search = failing
second = typed("I look around, search the benches, then wait a while.", [dict(LOOK), dict(SEARCH), dict(WAIT)])
third = typed("I look around, wait a while, then search the benches.", [dict(LOOK), dict(WAIT), dict(SEARCH)])
del ws.on_search
check("three deeds failing at the second: the first is named, and neither the one that failed nor the one never begun",
      second["stood"] == "part" and second["part"] is not None and second["part"][1] == "looked around", (second["stood"], second["part"]))     # (f715) clauses
check("three deeds failing at the third: the first two are named, in order, and the third is not",
      third["stood"] == "part" and third["part"] is not None and third["part"][1] == "looked around, then waited a while", (third["stood"], third["part"]))

# ---- a step the game said no to: told by its refusal, not named as done
def refusing(intent, text):
    ws.refuse("There is nothing of that kind to be done here.", needed_by_rest=False)


ws.on_search, kept_wait, ws.on_wait = refusing, ws.on_wait, failing
no = typed("I search the benches, then wait a while.", [dict(SEARCH), dict(WAIT)])
ws.on_wait = kept_wait
del ws.on_search
check("a step the game said no to, then one that fails: the refusal is read, the step is not named as done, and the line is told as not taken",
      no["stood"] == "none" and no["part"] is None and said(no["read"], "turn_not_taken") is not None
      and any("nothing of that kind" in t for t in no["read"]), (no["stood"], no["read"][-3:]))
COUNTED = ["kv.campaign.steps", "kv.campaign.story_steps", "kv.campaign.turn"]
check("...the character and the clock are as they were: of the save, only the count of turns and steps moved (the refusal was a turn, and was read)",
      no["was"] == no["now"] and no["minutes"] == 0 and no["moved"] == COUNTED, (no["minutes"], no["moved"]))

# ---- a hand-in made inside a step the game said no to is named, and the step is not (the pay is not hidden by the refusal)
owed("Hunt 3 stags past the ford", "stag")
ws.on_give, ws.on_search = refusing, failing
hand = typed("I give the clerk the stag's antlers, then search the benches.",
             [{"kind": "give", "target": cid, "item": "antlers", "summary": "the antlers given over"}, dict(SEARCH)])
del ws.on_give, ws.on_search
got = hand["now"]["coins"] - hand["was"]["coins"]
check("a step refused that handed work in on the way, then one that fails: the pay is kept and named, and the refused step is not",
      hand["stood"] == "part" and got > 0 and names(hand, "Hunt 3 stags past the ford", money.words(got), never=("the antlers given over", SEARCH["summary"]))
      and any("nothing of that kind" in t for t in hand["read"]), (hand["stood"], got, hand["read"][-3:]))

# ---- 3.3: a deed taken back because the reply to it could not be written says so
ws.to_pack(inventory.make_good(mentor.M["hunt"]["potion"]))
store.save_player(ws.player)
thing = inventory.GOODS[mentor.M["hunt"]["potion"]].name
GIFT = {"kind": "give", "target": tid, "item": thing, "summary": "a gift"}
gift = typed(f"I give them my {thing}.", [dict(GIFT)], fail={"NPCReply"})
check("a gift whose reply fails is not taken: the save as it was, the thing still carried",
      gift["stood"] == "none" and gift["same"] and "NPCReply" in gift["asked"] and gift["failed"] == ["action:give"]
      and any(i.good == mentor.M["hunt"]["potion"] for i in ws.player.character.inventory), (gift["stood"], gift["same"], gift["failed"], gift["asked"][-4:]))
check("...and the player reads that it was the reply that did not come: not the plain line for a turn not taken",
      said(gift["read"], "reply_not_come") is not None and not said(gift["read"], "turn_not_taken") and gift["part"] is None, gift["read"][-3:])
HELLO = {"kind": "talk", "target": tid, "speech": "Good day to you.", "summary": "a greeting"}
word = typed('I say, "Good day to you."', [dict(HELLO)], fail={"NPCReply"})
check("a word whose reply fails, nothing handed in, is told the same way", word["stood"] == "none" and word["same"] and said(word["read"], "reply_not_come") is not None,
      (word["stood"], word["same"], word["read"][-2:]))
frame = typed('I say, "Good day to you again."', [dict(HELLO, speech="Good day to you again.")], fail={"NPCProfile", "DialogueFrame"})
check("a talk that fails on what nobody speaks (who they are, how the line is framed) is told in the plain line: it was no reply that was lost",
      frame["stood"] == "none" and frame["same"] and {"NPCProfile", "DialogueFrame"} & set(frame["asked"]) and "NPCReply" not in frame["asked"][-1:]
      and said(frame["read"], "turn_not_taken") is not None and not said(frame["read"], "reply_not_come"), (frame["stood"], frame["same"], frame["read"][-2:], frame["asked"]))

# ---- which words are a reply is said by the contract itself: a telling that is checked like speech is no reply to the player
from llm import contracts as K
REPLIES = sorted(n for n, k in vars(K).items() if isinstance(k, type) and getattr(k, "REPLY", False))
check("the contracts that are someone's reply to the player say so themselves, and one checked like speech for another reason does not",
      REPLIES == ["CompanionReply", "MentorReply", "NPCReply", "NPCReplyManyBase", "NPCReplyPromised", "Parting"]
      and all(hasattr(getattr(K, n), "spoken") for n in ("ThreadTelling", "ThreadProposal", "CataclysmProposal", "Exchange")), REPLIES)
kept_search = ws.on_search


def telling(intent, text):
    from llm import gateway
    gateway.generate("thread_telling", "Tell it.", "What is said of it in the town.", K.ThreadTelling)


ws.on_search = telling
told = typed("I search the benches for word of it.", [dict(SEARCH)], fail={"ThreadTelling"})
ws.on_search = kept_search
check("a deed that fails on a telling checked like speech is told in the plain line: no reply was waited on",
      told["stood"] == "none" and "ThreadTelling" in told["asked"] and said(told["read"], "turn_not_taken") is not None
      and not said(told["read"], "reply_not_come"), (told["stood"], told["asked"][-3:], told["read"][-2:]))

# ---- a pane's button that waits on someone's reply is told the same way
kept_command = ws.command
ws.command = lambda text: ws.on_talk(ActionIntent(kind="talk", target=tid, speech="A word, if you will."), text)
pane = typed("#greet", None, fail={"NPCReply"})
ws.command = kept_command
check("a pane's button whose reply fails: nothing of it stands, and the player reads that the reply did not come",
      pane["same"] and "NPCReply" in pane["asked"] and said(pane["read"], "reply_not_come") is not None and not said(pane["read"], "turn_not_taken"),
      (pane["same"], pane["read"][-2:], pane["asked"][-3:]))

# ---- told as before: a line that was not read, and a first deed whose own telling failed
unread = typed("I look about me.", [dict(LOOK)], fail={"ActionPlan"})
kept_look, ws.on_look = ws.on_look, failing
untold = typed("I look about me again.", [dict(LOOK)])
ws.on_look = kept_look
for name, rec in (("a line that could not be read", unread), ("a first deed whose own telling failed", untold)):
    check(f"{name} is a turn not taken, told in the plain line, not as a reply that did not come",
          rec["stood"] == "none" and rec["same"] and (said(rec["read"], "turn_not_taken") or said(rec["read"], "turn_not_possible")) is not None
          and not said(rec["read"], "reply_not_come"), (rec["stood"], rec["same"], rec["read"][-2:], rec["asked"][-3:]))

# ---- a line that stands whole says none of it
whole = typed("I look around once more.", [dict(LOOK)])
check("a line that stands whole reads no stand-in for what stood or did not", whole["stood"] == "all" and ws.line_stood() == ["looked around"]
      and whole["nothing"] is None and whole["part"] is None, (whole["stood"], ws.line_stood(), whole["read"][-2:]))
plain = typed("I take my leave of the talk.", [{"kind": "leave_conversation"}])
check("a step with no summary of its own is named in words, never by the engine's name for it", not any("_" in d for d in ws.line_stood()), ws.line_stood())

# ---- what an operation said it did goes with it when it does not stand
with ws.operation("action:look", "a look that fails") as gone:
    operation.did("said, and then it failed")
    raise LLMError("its telling could not be written")
check("an operation that did not stand is never named, whatever it had said of itself", gone.state == "rolled_back" and gone in ws.line_failed
      and gone.did == ["said, and then it failed"] and "said, and then it failed" not in ws.line_stood() and ws.line_outcome() is not True,
      (gone.state, ws.line_stood()))

# ---- a walk, then a failure: the line says where the walk went (someone of this town who is elsewhere: the engine walks to them)
other = sorted(n.id for n in ws.present if n.id not in (cid, tid))[0]
def elsewhere():
    npc = store.load_npc(other)
    npc.location, npc.away_until = "parth_temple", 0
    store.save_npc(npc)
    ws.present = [n for n in ws.present if n.id != other]
    ws.residents = [n for n in ws.residents if n.id != other]
    ws.partner, ws.last_spoken = None, other                 # the one last spoken with, since gone to the temple


where = ws.world.places["parth_temple"].name
ws.on_search = failing
walk = typed('I go to them and say, "A word, if you have a moment," then search the place.',
             [{"kind": "talk", "speech": "A word, if you have a moment."}, dict(SEARCH)], first=elsewhere)
del ws.on_search
check("a walk, then a step that fails: the walk stands, and the player reads where it went, in the one phrase for it",
      walk["stood"] == "part" and walk["now"]["at"] == "parth_temple" and walk["was"]["at"] == "guild_house" and "action:go" in walk["kinds"]
      and names(walk, F["walked"].format(where=where), never=(SEARCH["summary"],)), (walk["stood"], walk["now"]["at"], walk["kinds"], walk["read"][-3:]))

# ---- over every line typed here: what the player is told agrees with what moved in the save
wrong = []
for rec in RAN:
    earned = rec["now"]["coins"] - rec["was"]["coins"]
    if rec["nothing"] and rec["was"] != rec["now"]:
        wrong.append(("said nothing happened, and the character is not as they were", rec["text"]))
    if rec["nothing"] and not rec["same"] and not (rec["moved"] == COUNTED and any("nothing of that kind" in t for t in rec["read"])):
        wrong.append(("said nothing happened, and more of the save moved than the count of a turn whose refusal the player read", rec["text"], rec["moved"]))
    if earned > 0 and rec["stood"] != "all" and not (rec["part"] and money.words(earned) in rec["part"][1]):
        wrong.append(("coin was paid and the line does not say so", rec["text"], earned))
    if rec["now"]["at"] != rec["was"]["at"] and rec["stood"] != "all" and not (rec["part"] and ws.world.places[rec["now"]["at"]].name in rec["part"][1]):
        wrong.append(("the character is somewhere else and the line does not say so", rec["text"]))
    if rec["part"] and rec["was"] == rec["now"] and rec["minutes"] == 0:
        wrong.append(("named a part, and nothing moved", rec["text"]))
    if not rec["text"].startswith("#") and (rec["stood"] == "none" and not rec["nothing"] or rec["stood"] == "part" and not rec["part"]
                                             or rec["stood"] == "all" and (rec["nothing"] or rec["part"])):
        wrong.append(("the turn log and the line disagree", rec["text"], rec["stood"], rec["read"][-2:]))
    if rec["nothing"] and rec["part"]:
        wrong.append(("said both", rec["text"]))
check(f"over the {len(RAN)} lines typed here, what the player is told agrees with what moved: coin paid and a walk made are named, and nothing happened "
      "is said only of a character left as they were",
      len(RAN) >= 14 and {r["stood"] for r in RAN} >= {"all", "part", "none"} and not wrong, wrong)

# ---- a place the world has no name for is named by what it is called, never left unsaid
ws.enter("guild_house")
with ws.operation("action:go", "a walk off the map") as far:
    ws.player_of(ws.acting).location = "the_old_mill"
ws.player_of(ws.acting).location = "guild_house"
store.save_player(ws.player)
check("a walk to a place the world has no name for still says where", far.state == "committed" and far.did == [F["walked"].format(where="the old mill")], (far.state, far.did))
with ws.operation("action:go", "a walk that says what it is") as told:
    operation.did("the long way round to the mill")
    ws.player_of(ws.acting).location = "the_old_mill"
ws.player_of(ws.acting).location = "guild_house"
store.save_player(ws.player)
check("an operation that said what it did is not named a second time as a walk", told.did == ["the long way round to the mill"], told.did)
with ws.operation("world", "the world's own turn", world=True) as theirs:
    ws.player_of(ws.acting).location = "parth_temple"
ws.player_of(ws.acting).location = "guild_house"
store.save_player(ws.player)
check("an operation of the world's is never named as the player's deed", theirs.did == [] and not any(where in d for d in ws.line_stood()[-1:]), theirs.did)

# ---- the lines themselves, the night's count, and the start-up check
rng = random.Random(1)
check("a reply that did not come has its lines, each counted by the night as a turn not taken",
      set(UNSAID) <= set(failures.lines()) and failures.reply_not_come(rng) in UNSAID and all(l in nightrun.HESITATIONS for l in UNSAID))
d = {k: (list(v) if isinstance(v, list) else v) for k, v in F.items()}
whole_ok = failures.problems(d)
d["reply_not_come"] = UNSAID[:2]
short = failures.problems(d)
d["reply_not_come"] = UNSAID[:-1] + ["The model failed to answer; nothing was spent."]
machine = failures.problems(d)
d["reply_not_come"] = list(UNSAID)
d["walked"] = "the walk there"
nowhere = failures.problems(d)
check("the start-up check holds them once they are in: a short list, a line that speaks of the machinery, a walk that names no place",
      not whole_ok and any("reply_not_come" in p for p in short) and any("reply_not_come" in p for p in machine) and any("walked" in p for p in nowhere),
      (whole_ok[:2], short[:1], machine[:1], nowhere[:1]))

# ---- until they are in the data: the plain line, drawn as it always was, and a walk named by its place alone
del F["reply_not_come"], F["walked"]
late = typed('I say, "Good day to you, one last time."', [dict(HELLO, speech="Good day to you, one last time.")], fail={"NPCReply"})
check("with no lines for it in the data, a reply that did not come is told in the plain line for a turn not taken, and nothing else changes",
      late["stood"] == "none" and late["same"] and said(late["read"], "turn_not_taken") is not None and failures.reply_not_come(rng) is None
      and failures.walked("the temple") == "the temple" and not failures.problems(), (late["stood"], late["read"][-2:]))

held()
g.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
