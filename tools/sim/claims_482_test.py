"""(f482) Claims with a source and a certainty (GOALS.md S1 and S5: a spoken claim never becomes fact). What a person is told in talk is a
told row, by whom, with "yesterday" struck from it; the name a character gives is told too, beside their view's knows_as and its source;
the claim is held by the one told and no one else, and moves neither what anyone knows nor the character's standing; a name heard in
town talk is hearsay, with its teller; a hire's word about the world is theirs; news says how sure it is (an engine fact sure, words the
model wrote "they say", a twisted tale rumour) and a tale told again keeps its first teller; and no rule reads a claim (the fence)."""
import ast
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 8)
simlib.install(stub)
shown = simlib.quiet_console()
from engine import memory, pulse, regard
from npc.models import NPC

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("claims_482", minutes=900)
ws, store = game.scene, game.store
ws.enter(ws.player.location)
n = NPC(id="c1", name="Wenna Tull", people="human", role="farmer", location=ws.player.location)
o = NPC(id="c2", name="Bors Hale", people="human", role="farmer", location=ws.player.location)
store.save_npc(n); store.save_npc(o)
ws.present = [store.load_npc("c1"), store.load_npc("c2")] + [p for p in ws.present if p.id not in ("c1", "c2")]

# ---- what a person is told: a told row, by whom, with the day's time words struck
stub.plan = [{"kind": "talk", "target": "c1", "speech": "I am Arwen, a baron's daughter."}]
stub.reply_extra = {"remember": "Yesterday the stranger said they are a baron's daughter.", "learned_player_name": "Arwen"}
ws.turn('I say to Wenna Tull, "I am Arwen, a baron\'s daughter."')
stub.plan, stub.reply_extra = None, None
rows = simlib.remembered(store, "c1", kind="told")
daughter = [r for r in rows if "baron" in r["text"]]
named = [r for r in rows if "Arwen" in r["text"]]
check("what they were told is a told row, about and from the character, sure only that it was said", len(daughter) == 1
      and daughter[0]["subject"] == ws.acting and daughter[0]["source"] == ws.acting and memory.certainty("told") == "they say", rows)
check("...with 'yesterday' struck from it", daughter and "yesterday" not in daughter[0]["text"].lower(), daughter)
check("the name the character gave is told too, beside their view's name and its source", len(named) == 1 and named[0]["source"] == ws.acting
      and regard.of(store.load_npc("c1"), ws.acting).knows_as == "Arwen" and regard.of(store.load_npc("c1"), ws.acting).knows_as_source == "self",
      (named, store.load_npc("c1").regard))
check("...held by the one told and no one else", not simlib.remembered(store, "c2", about="baron")
      and not any(r["kind"] == "told" for r in simlib.remembered(store, "c2", about="Arwen")))
check("(f485) ...while the one standing by keeps the name said aloud, as heard: hearsay, from the character",
      [(r["kind"], r["source"]) for r in simlib.remembered(store, "c2", about="Arwen")] == [("heard", ws.acting)]
      and regard.of(store.load_npc("c2"), ws.acting).heard_of.get("certainty") == "hearsay", simlib.remembered(store, "c2", about="Arwen"))
news = " ".join(x.get("text", "") for x in (store.load_world_state() or {}).get("news", []))
check("...and it moves nothing else: the claim is in no news, no fact of the world and nothing any rule reads",
      "baron" not in news.lower() and "Arwen" not in news
      and not any("baron" in f.text.lower() for f in ws.world.lore.values()), news[:300])

# ---- a name heard in town talk is hearsay, with its teller
from npc.life import note_mentions
speaker = store.load_npc("c2")
regard.own(speaker, ws.acting).name_known = True
added = note_mentions(speaker, "That would be Wenna Tull. She keeps the far field.", store, ws.acting)
heard = regard.of(store.load_npc("c1"), ws.acting).heard_of
check("a name heard in talk is hearsay, with its teller", added == ["Wenna Tull"] and heard.get("certainty") == "hearsay" and heard.get("source") == "c2",
      (added, heard))

# ---- a hire's word about the world is theirs
from engine import canon
m = {"id": "h1", "name": "Ghak Skurz", "memories": []}
canon.review(m, [], ["The bridge at Riverhaven was built by dwarves."], 5, who="Ghak Skurz").commit()
check("a hire's word about the world is kept as theirs, never the world's", m.get("beliefs") and m["beliefs"][-1]["source"] == "self"
      and m["beliefs"][-1]["certainty"] == "their word", m.get("beliefs"))

# ---- news says how sure it is; a tale told again keeps its first teller
state = {"news": []}
pulse.add_news(state, "The mill wheel broke.", "parth", 100, ["everyone"])
pulse.add_news(state, "Wolves took a lamb, they say.", "parth", 110, ["everyone"], certainty="they say", source="c2")
pulse.add_news(state, "Wolves took a lamb, they say.", "parth", 120, ["everyone"], certainty="they say", source="c1")
check("an engine fact is sure; words the model wrote are 'they say'", state["news"][0]["certainty"] == "sure"
      and state["news"][-1]["certainty"] == "they say", state["news"])
check("...and a tale told again keeps its first teller", len(state["news"]) == 2 and state["news"][-1]["source"] == "c2" and state["news"][-1]["times"] == 2)
MODEL_WRITTEN = {"engine/pulse.py": 5, "engine/events.py": 4, "engine/matters.py": 1, "scenes/road_actions.py": 3, "scenes/explore_actions.py": 1,
                 "engine/stakes.py": 1, "engine/motives.py": 1, "scenes/arc_actions.py": 1}
said = {}
for f in MODEL_WRITTEN:
    for node in ast.walk(ast.parse(Path(f).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == "add_news":
            if any(k.arg == "certainty" and getattr(k.value, "value", "") == "they say" for k in node.keywords):
                said[f] = said.get(f, 0) + 1
check("the news the model words (a situation's telling, a road's news, gossip, a verdict) says 'they say'", said == MODEL_WRITTEN, said)
from engine import standing
check("a deed's tale carries who tells it, and a twisted one is rumour", '"certainty": "rumour" if twisted else "they say"' in Path("engine/standing.py").read_text())
check("the news cap is in data", pulse.NEWS_KEEP == pulse.P["news"]["keep"])
game.close()
import shutil
shutil.rmtree("saves/claims_482", ignore_errors=True)

# ---- the fence: no rule reads a claim; only what offers a person their own memories back may
CLAIMS = set(memory.CLAIMS)
ALLOWED = {"engine/memory.py"}
leaks = []
for d in ("engine", "scenes", "npc", "services", "world"):
    for p in Path(d).rglob("*.py"):
        if str(p) in ALLOWED:
            continue
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute) and node.left.attr == "kind" \
                    and not (isinstance(node.left.value, ast.Name) and node.left.value.id == "beat"):     # a party beat's kind is not a memory's
                for c in node.comparators:
                    vals = [c.value] if isinstance(c, ast.Constant) else [e.value for e in getattr(c, "elts", []) if isinstance(e, ast.Constant)]
                    if CLAIMS & set(v for v in vals if isinstance(v, str)):
                        leaks.append(f"{p}:{node.lineno}")
        text = p.read_text(encoding="utf-8")
        for k in CLAIMS:
            if f"kind = '{k}'" in text or f"kind='{k}'" in text:
                leaks.append(f"{p}: SQL on {k}")
check("no rule reads a claim (the fence)", leaks == [], leaks)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
