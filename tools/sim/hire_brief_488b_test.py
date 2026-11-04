"""(f488, part 2) A hire's brief in its order: what holds through a talk first (who they are, what presses on them, the moment as they know
it, the one who hired them with their pronoun, what is open between them), then the talk so far, then this line's tail (what they
remember and what it brings to mind of them, how they speak, last, then the words said to them). The town's list and the board come in
full only when the line is about them ("where are you from?" asks about the speaker, not the town), and the checks read the list
whether it was given or not. What is open is the promises and debts they hold and an errand they wait on, always, and never repeated
among what is brought to mind. The talk window only grows until it is full, then turns a page. How they speak is held to voice_habits,
from data. The gesture's props point at WHERE instead of repeating it. And the goldens are no dearer than before Bundle D."""
import json
import sys
import types
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 8)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import config
from engine import brief, canon, obligations
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

log = Path("saves/hire_brief_488b_calls.jsonl")
log.unlink(missing_ok=True)
config.LOG_PATH = str(log)
game = simlib.campaign("hire_brief_488b", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter("guild_house")
SEEN = []
real = gateway._client


def chat(**k):
    if k["format"].get("title") == "CompanionReply":
        SEEN.append(k["messages"][1]["content"])
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
h1 = {"id": "h1", "name": "Bram Hollin", "role": "fighter", "level": 3, "permanent": True, "temper": ["blunt"], "blurb": "a scarred sellsword",
      "active": True}
ws.player.party, ws.player.party_mode = [h1], "with"
ws.player.character.pronoun = "she"
store.save_player(ws.player)


def say(line: str) -> str:
    SEEN.clear()
    stub.plan = [{"kind": "talk", "target": "hire:h1", "speech": line}]
    ws.turn(f'I say to Bram, "{line}"')
    stub.plan = None
    return SEEN[0] if SEEN else ""


# ---- the order: what holds first, the talk, then the tail; the words said last
req = say("Where did you learn to fight?")
heads = ["WHO YOU ARE", "RIGHT NOW", "WHERE", "YOU ARE TALKING WITH", "HOW YOU ARE WITH", "WHAT WAS SAID LATELY", "WHAT YOU REMEMBER",
         "HOW YOU SPEAK", "SAYS TO YOU"]
at = [req.rfind(h + ":") if h == "SAYS TO YOU" else req.find(h) if h == "HOW YOU ARE WITH" else req.find(h + ":") for h in heads]
check("a hire's brief opens on who they are, then what holds through the talk, then the talk, then the tail, the words said to them last",
      req and all(a >= 0 for a in at) and at == sorted(at) and req.rstrip().endswith('Where did you learn to fight?"'), list(zip(heads, at)))
check("...and how they speak comes after what they remember, not at the head", 0 <= req.find("WHAT YOU REMEMBER:") < req.find("HOW YOU SPEAK:"))
check("the one who hired them is spoken of in the character's own pronoun", "the one who hired you. Speak of them as she" in req, req[req.find("YOU ARE TALKING WITH"):][:160])

# ---- the town's list and the board only when the line is about them
check("a line about the speaker's own life brings in neither the town's list nor the board",
      "WHAT THIS TOWN HAS" not in req and "ON THE GUILD BOARD" not in req)
check("...nor does \"where are you from?\", for a townsperson either", not brief.asked("town", "And where are you from, Bram?")
      and brief.asked("town", "Where can we sleep tonight?"))
req = say("Where can we sleep tonight?")
check("a line about the town brings in its list", "WHAT THIS TOWN HAS" in req and "ON THE GUILD BOARD" not in req)
req = say("Is there any work on the board for us?")
check("a line about work brings in the board", "ON THE GUILD BOARD" in req)
before = sum(1 for _ in log.open(encoding="utf-8")) if log.exists() else 0
stub.a_CompanionReply = lambda u, k: {"speech": "We could ask at the smithy by the bridge."}
req = say("What do you make of the rain?")
del stub.a_CompanionReply
rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()[before:]] if log.exists() else []
sent_back = [r.get("error") or "" for r in rows if r.get("task") == "hire_chat" and r.get("error")]
check("with the town's list left out, a smithy the town does not have is still sent back", "WHAT THIS TOWN HAS" not in req
      and any("smithy" in e for e in sent_back), sent_back[:2])

# ---- what is open: their promises and debts and an errand they wait on, always, never also brought to mind
m = ws.player.party[0]
canon.keep_commitments(m, ["I owe them five silver from the dice at the Plough"], ws.minutes // 1440, "Bram")
store.save_player(ws.player)
e = obligations.open_(store, "errand", "hire:h1", ws.acting, "Could you fetch my whetstone from the inn?", ws.minutes, terms={"errand": "fetch"})
req = say("Nice weather for it.")
opened = req[req.find("WHAT IS OPEN BETWEEN YOU:"):req.find("WHAT WAS SAID LATELY:")] if "WHAT IS OPEN BETWEEN YOU:" in req else ""
check("what they owe is open between them, whatever the line", "five silver" in opened, opened)
check("...and so is the errand they wait to hear about", "whetstone" in opened, opened)
check("...never also among what the line brings to mind", req.count("five silver") == 1, req.count("five silver"))
canon.release_commitments(ws.player.party[0], "let_go", ws.minutes // 1440)
obligations.close(store, e, "released", "no_answer", ws.minutes)
store.save_player(ws.player)
req = say("Nice weather for it, still.")
check("a promise let go and an errand answered are no longer open", "five silver" not in req and "whetstone" not in req)

# ---- the talk window only grows until it is full, then a page turns
H = brief.rules("hire")
talks = []
for i in range(H["talk_window"] // 2 + 2):
    r = say(f"Tell me one more thing, number {i}.")
    talks.append(r[r.find("WHAT WAS SAID LATELY:"):r.find("WHAT YOU REMEMBER:")])
lines = [[l for l in t.splitlines()[1:] if l.strip()] for t in talks]
grew = [i for i in range(1, len(lines)) if lines[i][:len(lines[i - 1])] == lines[i - 1] and len(lines[i]) > len(lines[i - 1])]
turned = [i for i in range(1, len(lines)) if len(lines[i]) < len(lines[i - 1])]
check("between page turns, each reply's talk is the last one's and what was said since", grew, [len(x) for x in lines])
check("...and once full, the window turns a page to its last talk_turn lines", turned and all(len(lines[i]) <= H["talk_turn"] + 2 for i in turned)
      and max(len(x) for x in lines) <= H["talk_window"], [len(x) for x in lines])

# ---- how they speak is held to voice_habits, from data; the props point at WHERE
keep = H["voice_habits"]
H["voice_habits"] = 1
few = say("Ready when you are.")
H["voice_habits"] = keep
lots = say("Ready when you are, then.")
part = lambda r: r[r.find("HOW YOU SPEAK:"):].split("\n\n")[0]
check("how they speak is held to voice_habits lines from data", part(few).count(". ") < part(lots).count(". "), (part(few), part(lots)))
check("the gesture's props point at WHERE, never repeat its lines", "WHAT IS HERE: only what WHERE gives." in lots
      and not any(v in lots.split("FOR A GESTURE ONLY")[1] for v in (ws.place.visible or [])[:1]))
check("brief.yaml's hire numbers pass the startup check", brief.problems() == [], brief.problems())

gateway._client = real
game.close()
import shutil
shutil.rmtree("saves/hire_brief_488b", ignore_errors=True)
log.unlink(missing_ok=True)

# ---- and the goldens are no dearer than before Bundle D
import latency
held = latency.gate()
check("every input with a speech call in both goldens is at or below its price before Bundle D", held and not any(held.values()), held)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
