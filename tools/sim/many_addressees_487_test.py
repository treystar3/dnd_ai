"""(f487) Two or more characters to one townsperson: one call, what is said aloud once, then one block for each character, each landing on
that character's own view and their own told row; a block for someone who did not speak, a missing block and a name borrowed from another's
words are each sent back; the flat fallback (brief.yaml many_addressees: flat_each) makes one plain reply per character; and one speaker is
a plain NPCReply with no blocks."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 5)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import brief, regard
from llm import contracts
from npc import life
from pydantic import ValidationError

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- the contract: one block each, by id; nothing more, nothing missing, no borrowed name
M = contracts.many_reply(["player", "second"])
schema = M.model_json_schema()
check("the server's grammar holds the blocks' ids and their number", schema["$defs"]["NPCAnswer"]["properties"]["to"]["enum"] == ["player", "second"]
      and schema["properties"]["answers"].get("minItems") == 2 and schema["properties"]["answers"].get("maxItems") == 2, schema["properties"]["answers"])
ctx = {"to": ["player", "second"], "words": {"player": "I am Arwen.", "second": "Where is the inn?"}}
def sent_back(answers):
    try:
        M.model_validate({"speech": "Welcome.", "intent": "small_talk", "answers": answers}, context=ctx)
        return ""
    except ValidationError as e:
        return str(e)
check("a block for each is taken", sent_back([{"to": "player", "learned_name": "Arwen"}, {"to": "second"}]) == "")
check("a doubled block is sent back", "two blocks for player" in sent_back([{"to": "player"}, {"to": "player"}]))
check("a name learned from another's words is sent back", "not in what second said" in sent_back([{"to": "player"}, {"to": "second", "learned_name": "Arwen"}]))


def loose(answers):                                       # the checks under the grammar: what a server without it could send
    try:
        contracts.NPCReplyManyBase.model_validate({"speech": "Welcome.", "intent": "small_talk", "answers": answers}, context=ctx)
        return ""
    except ValidationError as e:
        return str(e)


check("a missing block is sent back", "no block for second" in loose([{"to": "player"}]), loose([{"to": "player"}])[:200])
check("a block for someone who did not speak is sent back", "third, who did not speak to you" in loose([{"to": "player"}, {"to": "third"}]))

# ---- in play: two characters, one call, each block on its own view
game = simlib.campaign("many_487", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter("guild_house")
c1, c2 = simlib.two_characters(ws)
npc = sorted((n for n in ws.present if n.role not in ("guild_clerk", "guild_master")), key=lambda n: n.id)[0]
before = dict(stub.calls)
stub.many_extra = [{"to": c1.id, "learned_name": "Arwen", "trust_change": 3, "remember": "Arwen asked after work."},
                   {"to": c2.id, "remember": "Their friend asked where to sleep.", "they_promised": "to pay for the room"}]
reply, _ = life.converse_many(npc, store, ws.world, ws.catalog, [], [(c1.id, "the stranger", "I am Arwen. Is there work going?"),
                                                                     (c2.id, "the stranger's friend", "And where might we sleep tonight?")],
                              pronouns={c1.id: "she", c2.id: "they"})
stub.many_extra = None
after = store.load_npc(npc.id)
made = {t: stub.calls.get(t, 0) - before.get(t, 0) for t in ("NPCReplyMany", "NPCReply")}
check("two speakers make one call with a block each", made == {"NPCReplyMany": 1, "NPCReply": 0}, made)
check("...the first's block lands on their own view: the name they gave, met", regard.of(after, c1.id).knows_as == "Arwen" and regard.of(after, c1.id).met
      and regard.of(after, c2.id).knows_as != "Arwen", (after.regard))
told1 = [r for r in simlib.remembered(store, npc.id, kind="told") if r["subject"] == c1.id]
told2 = [r for r in simlib.remembered(store, npc.id, kind="told") if r["subject"] == c2.id]
check("...each block's memory is its own character's told row", any("work" in r["text"] for r in told1) and any("sleep" in r["text"] for r in told2)
      and not any("sleep" in r["text"] for r in told1), (told1, told2))
check("...and a promise heard from the second is the second's", [r["subject"] for r in simlib.remembered(store, npc.id, kind="promise_heard")] == [c2.id])

# ---- the flat fallback: one plain reply per character, in order
keep = brief._B["townsfolk"]["many_addressees"]
brief._B["townsfolk"]["many_addressees"] = "flat_each"
before = dict(stub.calls)
out = life.converse_many(npc, store, ws.world, ws.catalog, [], [(c1.id, "the stranger", "Good day."), (c2.id, "the stranger's friend", "Good day to you.")])
brief._B["townsfolk"]["many_addressees"] = keep
made = {t: stub.calls.get(t, 0) - before.get(t, 0) for t in ("NPCReplyMany", "NPCReply")}
check("flat_each makes one plain reply per character", made == {"NPCReplyMany": 0, "NPCReply": 2} and isinstance(out, list) and len(out) == 2, made)

# ---- one speaker: NPCReply, with no blocks
before = dict(stub.calls)
reply, _ = life.converse_many(npc, store, ws.world, ws.catalog, [], [(c1.id, "the stranger", "Good evening.")])
made = {t: stub.calls.get(t, 0) - before.get(t, 0) for t in ("NPCReplyMany", "NPCReply")}
check("one speaker is a plain NPCReply, no blocks", made == {"NPCReplyMany": 0, "NPCReply": 1} and not hasattr(reply, "answers") or
      (made == {"NPCReplyMany": 0, "NPCReply": 1} and type(reply).__name__ == "NPCReply"), made)
check("...its one block, for the one commit path, is its own fields", reply.answers(c1.id)[0].to == c1.id and reply.answers(c1.id)[0].remember == reply.remember)
game.close()
import shutil
shutil.rmtree("saves/many_487", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
