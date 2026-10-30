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

# ---- (f396) the narrator writes no dashes
check("a dash before the rest of a thought is a colon", hygiene.undash("You turn \u2014 the wolf is already there.") == "You turn: the wolf is already there.")
check("a pair around an aside are commas", hygiene.undash("Three of them \u2014 no, four \u2014 circle the fire.") == "Three of them, no, four, circle the fire.")
check("a dash before 'and' is a comma", hygiene.undash("You reach the ridge\u2014and stop.") == "You reach the ridge, and stop.")
check("speech broken off ends in an ellipsis", hygiene.undash('"Wait\u2014" she says.') == '"Wait..." she says.')
check("a spaced hyphen and a double hyphen are dashes; a hyphenated word is not",
      hygiene.undash("A half-elf watches you - hand on the hilt - and says nothing.") == "A half-elf watches you, hand on the hilt, and says nothing."
      and hygiene.undash("One thing is clear -- the bridge is out.") == "One thing is clear: the bridge is out.")
check("a dash opening a line is dropped, the line capitalised", hygiene.undash("He waits.\n\u2014 and then the door opens.") == "He waits.\nAnd then the door opens.")
check("a range is 'to'", hygiene.undash("It is 3\u20135 miles north.") == "It is 3 to 5 miles north.")
answers = iter(['{"text": "The gate creaks \u2014 then holds."}'])
gw._client = types.SimpleNamespace(chat=lambda **k: types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=next(answers))))
got = gw.generate("narrate", "You narrate.", "The gate.", Narration)
check("a narrator's answer reaches the game without its dashes", got.text == "The gate creaks, then holds.", got.text)
# (f403) speakers too: a townsperson's, a hire's, Maren's
reply = NPCReply.model_construct(speech="He's just near enough to see from where we are standing\u2014he does his trade-work by the river market.",
                                 gesture="She smiles \u2014 briefly \u2014 and turns.")
hygiene.undash_answer("npc_conversation", reply)
check("a speaker's answer reaches the game without dashes, speech and gesture", "\u2014" not in reply.speech + reply.gesture
      and "standing: he does his trade-work" in reply.speech and reply.gesture == "She smiles, briefly, and turns.", (reply.speech, reply.gesture))
check("a stammer is an ellipsis", hygiene.undash('"I\u2014I don\'t know."') == '"I... I don\'t know."', hygiene.undash('"I\u2014I don\'t know."'))
check("...and a thought broken off", hygiene.undash("I was going to \u2014 no. Never mind.") == "I was going to... no. Never mind.",
      hygiene.undash("I was going to \u2014 no. Never mind."))
check("a dash before 'just' is a comma", hygiene.undash("Depends on what you need\u2014just so we're clear, I sell nothing fancy.")
      == "Depends on what you need, just so we're clear, I sell nothing fancy.")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    console.narrate("The tide turns \u2014 slowly.")
    console.say("I \u2014 I don't know.", "Osric")
    console.npc_says("Brokur", "Gear is what I do\u2014best.", "He sets the hammer down \u2014 slowly.")
    console.note("Learned Fire Bolt - rank II.")
out = buf.getvalue()
check("the screen gets no dash from the narrator or from anyone speaking", "turns: slowly" in out and "I... I don't know" in out
      and "\u2014" not in out and "do: best" in out, out)
check("...the game's own notes keep theirs", "Fire Bolt - rank II" in out, out)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
