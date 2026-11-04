"""(f493) What the post-D night found, part 1: a townsperson's reply asks what was promised only when what was said may promise
something (brief.yaml promise.words), so a talk with no promise in it gives the model no field to fill; the field the server lets it
fill is held to brief.yaml promise.max_chars; what comes back is kept only as a promise in a few words, never the model's note to
itself; a plain reply drops a promise no one asked for; two characters at once ask it only when one of them may promise; the system
prompt no longer names the field; a promise asked for and made is kept as heard, from the one who made it; and a try cut at the
budget's deadline says the limit it had, not the client's."""
import shutil
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import brief
from llm import contracts, gateway
from npc import life, prompts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- the words that may promise
yes = ["I promise I'll look into it and come back to you", "Keep my place by the fire. I'll be back, I swear it", "You have my word.",
       "We’ll pay for the room tomorrow.", "Leave it to me."]
no = ["What is your name?", "Where can I find the inn?", "Will you tell me about the mill?", "I'm Arwen, from the coast.",
      "Swearing at the weather won't help."]
check("a line that may promise is told apart from one that does not", all(brief.promised(t) for t in yes) and not any(brief.promised(t) for t in no),
      ([t for t in yes if not brief.promised(t)], [t for t in no if brief.promised(t)]))
check("...two characters' lines are read together", brief.promised("Where do we sleep?", "We'll pay for the room.") and not brief.promised("Hello.", "Hi."))

# ---- what is kept of a promise: the night's own answers
kept = {"look into it and come back to me": "look into it and come back to me",
        "to pay double at the next town\nWait, let me re-read your rules.": "to pay double at the next town",
        "keep her place by the fire upon her return": "keep her place by the fire upon her return",
        "to look into it and come back to him\", ": "to look into it and come back to him",
        "I'll be back to help (if needed).": "I'll be back to help"}
junk = ["none_given_this_turn_yet", "empty", "None", "nothing reported yet in this exchange or previous turns",
        "they promised nothing yet in this conversation and no prompt to do so either (leave empty per instructions)",
        'empty", \n  "journal_note": "", \n  "gives": "empty"', "Wait, they said 'I'll be back', not promised",
        "keep his place by the fire when he returns and also keep watch over the pack and the cart and the mule all night long",
        "{them} owes me"]
got = {k: brief.promise_kept(k) for k in kept}
check("a promise is kept as its first clause, in a few words", all(got[k] == v for k, v in kept.items()), got)
check("...and the model's notes to itself are not kept", not any(brief.promise_kept(j) for j in junk), [j for j in junk if brief.promise_kept(j)])

# ---- the contracts
P = brief.rules()["promise"]
plain, asked = contracts.NPCReply.model_json_schema(), contracts.NPCReplyPromised.model_json_schema()
check("a plain townsfolk reply has no promise field for the model to fill", "they_promised" not in plain["properties"], sorted(plain["properties"]))
check("...the one that asks has it, held to brief.yaml's length by the server's grammar", asked["properties"]["they_promised"].get("maxLength") == P["max_chars"],
      asked["properties"].get("they_promised"))
check("...under the same title, the one contract to the stub and the recordings", plain["title"] == asked["title"] == "NPCReply")
check("...a plain reply drops a promise no one asked for; one that asks keeps it cleaned",
      contracts.NPCReply.model_validate({"speech": "Aye.", "intent": "share", "they_promised": "to pay"}).they_promised == ""
      and contracts.NPCReplyPromised.model_validate({"speech": "Aye.", "intent": "share", "they_promised": "to pay\nWait, no"}).answers("p")[0].they_promised == "to pay")
many, many_asked = contracts.many_reply(["a", "b"]).model_json_schema(), contracts.many_reply(["a", "b"], True).model_json_schema()
check("two characters at once: the blocks ask what was promised only when asked to", "they_promised" not in many["$defs"]["NPCAnswer"]["properties"]
      and many_asked["$defs"]["NPCAnswer"]["properties"]["they_promised"].get("maxLength") == P["max_chars"], sorted(many["$defs"]))
check("the system prompt no longer names the field (it comes with the line that may promise)", "they_promised" not in prompts.CONVERSATION_SYSTEM
      and "they_promised" in prompts.PROMISE_ASK)
check("brief.yaml's promise block is checked", not [b for b in brief.problems() if "promise" in b], brief.problems())
keep = dict(P)
P["max_words"], P["words"] = 0, ["I'll"]
named = [b for b in brief.problems() if "promise" in b]
P.clear(); P.update(keep)
check("...a broken one is named", len(named) == 2, named)

# ---- in play: one talk with no promise, one with
game = simlib.campaign("promise_493", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter(ws.player.location)
CALLS = []
real = gateway._client


def chat(**k):
    if k["format"].get("title") in ("NPCReply", "NPCReplyMany"):
        CALLS.append(k)
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
npc = sorted((n for n in ws.present if n.role not in ("guild_clerk", "guild_master")), key=lambda n: n.id)[0]
stub.reply_extra = {"they_promised": "to pay you back"}
stub.plan = [{"kind": "talk", "target": npc.id, "speech": "What is your name?"}]
ws.turn('I say, "What is your name?"')
first = CALLS[-1] if CALLS else {"format": {"properties": {}}, "messages": [{}, {"content": ""}]}
check("a line with no promise: the reply's format has no promise field", CALLS and "they_promised" not in first["format"]["properties"],
      sorted(first["format"].get("properties", {})))
check("...the request does not ask for one", "A PROMISE?" not in first["messages"][1]["content"])
check("...and a promise the reply carried anyway is not kept", not simlib.remembered(store, npc.id, kind="promise_heard"),
      simlib.remembered(store, npc.id, kind="promise_heard"))
stub.reply_extra = {"they_promised": "to bring the herbs by nightfall\nWait, let me re-read the rules."}
stub.plan = [{"kind": "talk", "target": npc.id, "speech": "I'll bring your herbs by nightfall, I promise."}]
ws.turn('I say, "I\'ll bring your herbs by nightfall, I promise."')
stub.plan, stub.reply_extra = None, None
second = CALLS[-1]
check("a line that may promise: the format has the field, held to its length", second["format"]["properties"].get("they_promised", {}).get("maxLength")
      == P["max_chars"], second["format"]["properties"].get("they_promised"))
check("...the request asks for it, after what they said", second["messages"][1]["content"].rfind("A PROMISE?") > second["messages"][1]["content"].rfind("THEY SAY:"))
heard = simlib.remembered(store, npc.id, kind="promise_heard")
check("...and the promise is kept as heard, from the one who made it, without the model's note", len(heard) == 1 and heard[0]["source"] == ws.acting
      and "herbs by nightfall" in heard[0]["text"] and "Wait" not in heard[0]["text"], heard)

# ---- two characters at once
c1, c2 = simlib.two_characters(ws)
n0 = len(CALLS)
life.converse_many(npc, store, ws.world, ws.catalog, [], [(c1.id, "the stranger", "Is there work going?"),
                                                          (c2.id, "the stranger's friend", "And where might we sleep tonight?")])
life.converse_many(npc, store, ws.world, ws.catalog, [], [(c1.id, "the stranger", "Is there work going?"),
                                                          (c2.id, "the stranger's friend", "We'll pay for the room.")])
blocks = [((k["format"].get("$defs") or {}).get("NPCAnswer") or {}).get("properties", {}) for k in CALLS[n0:]]
check("two characters: the blocks ask what was promised only when one of them may promise", len(blocks) == 2 and "they_promised" not in blocks[0]
      and "they_promised" in blocks[1], [sorted(b) for b in blocks])
gateway._client = real
game.close()
shutil.rmtree("saves/promise_493", ignore_errors=True)

# ---- a try cut at the budget's deadline says the limit it had
keep_client = gateway._client
gateway._client = types.SimpleNamespace(_client=types.SimpleNamespace(timeout=120))
words = gateway.timeout_words(44.2)
gateway._client = keep_client
check("a try cut at the turn's deadline says so, with the limit it had", words == "timed out after 44s (what was left of the turn's time)", words)
check("...and with no deadline set, the client's own", gateway.timeout_words(None) == f"timed out after {gateway.config.REQUEST_TIMEOUT}s")

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
