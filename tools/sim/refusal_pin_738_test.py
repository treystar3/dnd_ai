"""(f738) A refused answer no longer pins its turn's stack in memory (docs/design/33_audit_fix_plan/long_save.md, LONG_SAVE-2).

A contract's validator raises ValueError; pydantic-core keeps that error inside the ValidationError where Python's collector cannot see
it, and its traceback holds every frame above the validator. The gateway kept the ValidationError past its except block, so the frames
of the line that asked (the world, the snapshots, the people copied) stayed alive for the rest of the sitting. It now keeps the reason
in words and lets the exception go. Held here:
- the finding's case: a real contract (StartingKit, a reply's check) refuses the first answer and the second is taken; what the
  calling frame held is collected, and forty such calls leave none alive;
- a call refused on every try lets its caller's frame go too, and its final error still says why (its cause carries the reason);
- the reason sent back to the model is the same words as before;
- the class: a stubbed play of three hundred typed lines (looks, waits, talk, walks, an improvised act), with refusals planted on the
  understanding and on speech beside the stub's own, leaves no ValidationError and no frame of a finished line alive.
Run: python tools/sim/refusal_pin_738_test.py"""
import gc
import sys
import weakref
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console(("narrate", "say", "note", "ledger", "out", "npc_says", "dialogue", "print"))
import config
from pydantic import ValidationError
from llm import gateway
from llm.contracts import NPCReply, StartingKit
from llm.gateway import LLMError

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


class Held:
    """Stands for what a line's frames hold: the decoded world, the snapshots, the people copied."""


def collected() -> None:
    gc.collect()
    gc.collect()


SENT_BACK: list = []                     # the words of each retry the gateway sent


def answers(title: str, drafts: list, last):
    def fn(u, k):
        if "rejected" in u:
            SENT_BACK.append(u)
        return drafts.pop(0) if drafts else last
    setattr(stub, f"a_{title}", fn)


def a_line(task, contract, drafts, last, context=None):
    """One line's frame asking the model two frames down: the weak reference to what it held, and what the call gave (no exception
    is returned: one would hold this frame by its traceback)."""
    held = Held()
    ref = weakref.ref(held)
    answers(contract.__name__, list(drafts), last)

    def below():
        return gateway.generate(task, "Answer.", "Answer the question.", contract, retries=2, validation_context=context, _quiet=True)
    try:
        got = below()
        out = ("taken", got)
    except LLMError as e:
        out = ("failed", type(e.__cause__).__name__, str(e.__cause__))
    return ref, out


KIT = {"weapons": ["longsword", "mace"]}
GOOD_KIT = {"weapon": "longsword"}
GOOD_REPLY = {"speech": "It is as it is.", "intent": "small_talk"}

# ---- the finding's case: the first answer refused by a real contract, the second taken
for label, task, contract, drafts, last, context in (
        ("a starting kit's weapon not on its list", "starting_kit", StartingKit, [{"weapon": "club"}], GOOD_KIT, KIT),
        ("a reply with markdown in its speech", "npc_conversation", NPCReply, [{"speech": "*It is as it is.*", "intent": "small_talk"}],
         GOOD_REPLY, None)):
    SENT_BACK.clear()
    ref, out = a_line(task, contract, drafts, last, context)
    collected()
    check(f"{label}, refused and then taken: the call gives the second answer", out[0] == "taken" and len(SENT_BACK) == 1, (out, SENT_BACK))
    check(f"...and what the calling line held is collected", ref() is None)
refs = [a_line("starting_kit", StartingKit, [{"weapon": "club"}], GOOD_KIT, KIT)[0] for _ in range(40)]
collected()
alive = sum(r() is not None for r in refs)
check("forty calls, each with one answer refused: nothing their lines held is alive", alive == 0, f"{alive} of 40 alive")

# ---- refused on every try: the frame goes, the reason stays
SENT_BACK.clear()
ref, out = a_line("starting_kit", StartingKit, [{"weapon": "club"}, {"weapon": "axe"}, {"weapon": "flail"}], GOOD_KIT, KIT)
collected()
REASON = "weapon must be one of the ids listed under WEAPON OPTIONS"
check("a call refused on every try fails", out[0] == "failed", out)
check("...its line's frame is collected", ref() is None)
check("...and its final error still says why: the cause carries the contract's reason, as words and not the exception",
      out[0] == "failed" and out[1] == "LLMError" and REASON in out[2], out)
check("the reason sent back to the model is the same words as before", bool(SENT_BACK) and all(
    s == f"That answer was rejected: {REASON}\nFix this and respond again with the complete JSON." for s in SENT_BACK), SENT_BACK)

# ---- the class: a few hundred typed lines, refusals on the understanding and on speech, and nothing of a finished line left
PLACE = "trading_square"
collected()
before = sum(1 for o in gc.get_objects() if isinstance(o, ValidationError))   # a count: an id can be reused once its object dies
planted = {"ActionPlan": 0, "NPCReply": 0}
asked = {"ActionPlan": 0, "NPCReply": 0}
sent_back = {"ActionPlan": 0, "NPCReply": 0}
plan_real, reply_real = simlib.Stub.a_ActionPlan.__get__(stub), simlib.Stub.a_NPCReply.__get__(stub)


def planting(title, real, spoil, every):
    def fn(u, k):
        if "rejected" in u:
            sent_back[title] += 1
            return real(u, k)
        asked[title] += 1
        if asked[title] % every == 0:
            planted[title] += 1
            return spoil(real(u, k))
        return real(u, k)
    setattr(stub, f"a_{title}", fn)


planting("ActionPlan", plan_real, lambda out: {"actions": []}, 4)                          # "give at least one action"
planting("NPCReply", reply_real, lambda out: dict(out, speech=f"*{out['speech']}*"), 2)    # "plain speech only"
g = simlib.campaign("refusal_pin_play", seed=7, location=PLACE)
config.TURN_LOG_PATH = "saves/refusal_pin_play/turns.jsonl"
ws = g.scene
ws.enter(PLACE)
LINES, failed, visited, kinds = 300, [], set(), {}
for i in range(LINES):
    here, step = ws.player.location, i % 6
    visited.add(here)
    who = [n.id for n in ws.present]
    out = [n for n in ws.world.neighbors(here) if n != here]
    if step == 1 and who:
        stub.plan = [{"kind": "talk", "target": who[i % len(who)], "speech": "Good day to you. Any news?"}]
    elif step == 2:
        stub.plan = [{"kind": "wait", "wait_minutes": 30}]
    elif step == 3 and out:
        stub.plan = [{"kind": "move", "destination": out[i % len(out)]}]
    elif step == 4:
        stub.plan = [{"kind": "other", "summary": "I study the old stones underfoot."}]
    elif step == 5 and here != PLACE:
        stub.plan = [{"kind": "move", "destination": PLACE}]
    else:
        stub.plan = [{"kind": "look"}]
    kind = stub.plan[0]["kind"]
    try:
        if ws.turn("a line") is True:
            kinds[kind] = kinds.get(kind, 0) + 1
    except Exception as e:
        failed.append((i, kind, repr(e)[:200]))
check(f"the play's {LINES} lines all ran, each kind of line taken, over more than one place",
      not failed and set(kinds) == {"look", "talk", "wait", "move", "other"} and len(visited) >= 2, (failed[:3], kinds, visited))
check("...answers were refused on the understanding and on speech, and each was sent back",
      planted["ActionPlan"] >= 40 and planted["NPCReply"] >= 5 and sent_back["ActionPlan"] >= planted["ActionPlan"]
      and sent_back["NPCReply"] >= planted["NPCReply"], (planted, sent_back, asked))
collected()
left = [o for o in gc.get_objects() if isinstance(o, ValidationError)]
check("after the play no ValidationError is alive", len(left) <= before,
      f"{len(left)} alive against {before} before: {[str(o).splitlines()[0] for o in left[:3]]}")
del left
code = type(ws).turn.__wrapped__.__code__
lines_held = sum(1 for o in gc.get_objects() if type(o).__name__ == "frame" and o.f_code is code)
check("...and no frame of a finished line is alive", lines_held == 0, f"{lines_held} lines' frames alive")
g.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
