"""(f391) The output gate: the machinery never shows in the story.
Two nights put the game's workings in front of the player: a reasoning fragment and a JSON brace at the end of a passage, "mud_r_{road}",
"silks_1827359406-bdcc-...", 'find_the_sinkhole', a literal backslash-n, "The player pulls out...", "my own shadow" in the narrator's
voice. The gateway sends an answer carrying any of these back; every line on its way to the screen is mended, whoever draws it."""
import contextlib, io, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
import llm.gateway as gw
from engine import hygiene, world_improv
from llm.contracts import Narration, NPCReply
from ui import console
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- mending what reaches the screen
c = hygiene.clean
check("a reasoning fragment and JSON after the passage are cut off",
      c('outcropping of stone.", 100%_matched: true} Or similar logic if required... wait, I need to follow the JSON output precisely.* } \n```json\n{')
      == "outcropping of stone.")
check("a passage still wrapped in its JSON is unwrapped", c('{ "text": "The watchman shifts his grip."}') == "The watchman shifts his grip.")
check("a template's placeholder and a stray underscore are made words", c("deep tracks in the mud_r_{road}. Carts cross the stone arches_.") ==
      "deep tracks in the mud. Carts cross the stone arches.")
check("a code on a word is dropped", c("You stand by the silks_1827359406-bdcc-4e2a and wait.") == "You stand by the silks and wait.")
check("an id is said as words", c("The matter ended by way of 'find_the_sinkhole'.") == "The matter ended by way of 'find the sinkhole'.")
check("a written backslash-n is a real line break", c("rain.\\n\\nThe mud clings") == "rain.\n\nThe mud clings")
check("'the player' is 'you', with the verb to match", c("The player pulls out a map. The player's boots are wet. The player is tired.") ==
      "You pull out a map. Your boots are wet. You are tired.")
check("...and in the engine's own lines", c("Lookie turns their back on the player without thinking.") == "Lookie turns their back on you without thinking.")
check("a lute player is left alone, and so is a command the player types", c("The lute player of Parth nods.") == "The lute player of Parth nods."
      and c("Type #goto trading_square to walk there.") == "Type #goto trading_square to walk there.")
check("plain prose is untouched", c("You push open the door; the inn is warm, loud, and smells of smoke.") == "You push open the door; the inn is warm, loud, and smells of smoke.")
check("what was mended is counted", hygiene.REPAIRS["json"] >= 2 and hygiene.REPAIRS["player"] >= 2 and hygiene.REPAIRS["id"] >= 2, dict(hygiene.REPAIRS))

# ---- every line on the way out, whoever draws it
out = io.StringIO()
with contextlib.redirect_stdout(out):
    console.narrate("The player pulls out a map.")
    console.note("The way through the cracked_plains is closed.")
check("the terminal's own output is gated", "You pull out a map." in out.getvalue() and "cracked plains" in out.getvalue(), out.getvalue())
SEEN = []
real = console.note
console.note = lambda m, *a, **k: SEEN.append(m)
console.guard_outputs()
console.note("Remembered here: The player takes out their journal")
check("a harness that puts its own output in place is gated once it asks", SEEN == ["Remembered here: You take out their journal"], SEEN)
console.guard_outputs()
console.note("x")
check("...and gating twice is a no-op", SEEN[-1] == "x" and getattr(console.note, "inner", None) is not None and not getattr(console.note.inner, "gated", False))
console.note = real
check("an improvised act's mark speaks of 'you', not 'the player'", world_improv.what_of("The player takes out their journal and sketches the gate.")
      == "take out your journal and sketches the gate", world_improv.what_of("The player takes out their journal and sketches the gate."))

# ---- at the gateway: the answer is sent back
check("the narrator's 'I' and 'my' outside quotes are found", hygiene.problem("narrate", {"text": "I see my own shadow stretch."})[0] == "first_person")
check("...but not inside someone's quoted speech", hygiene.problem("narrate", {"text": 'She says, "I am here, my friend."'}) == ("", ""))
check("a speaker may say 'I'", hygiene.problem("npc_conversation", {"speech": "I am here, my friend."}) == ("", ""))
check("ids in an answer's own fields (what it reveals) are not prose", hygiene.problem("npc_conversation", {"speech": "Fair enough.", "reveals": ["parth_on_trade_road"]}) == ("", ""))
answers = iter(['{"text": "Rain turns the square to slick patches in the mud_r_{road}."}', '{"text": "Rain turns the square to slick patches of mud."}'])
SENT = []
def chat(**k):
    SENT.append(k["messages"])
    return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=next(answers)))
gw._client = types.SimpleNamespace(chat=chat)
got = gw.generate("narrate", "You narrate.", "The square in the rain.", Narration)
check("a passage with a template's placeholder is sent back and written again", got.text == "Rain turns the square to slick patches of mud." and len(SENT) == 2, got.text)
check("...told why, the word named", "braces" in SENT[1][-1]["content"] and "{road}" in SENT[1][-1]["content"], SENT[1][-1]["content"])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
