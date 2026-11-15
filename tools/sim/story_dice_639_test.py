"""(f639) Only a story input takes a dice step (the owner, 2026-11-12: docs/design/17, question 17; docs/design/20_phase3_plan.md).
Every input reseeds the dice from the campaign's seed, a count and the line (engine/streams.py). The count was of every input, so
a pane's command between two lines of the story moved the dice of every line after it: the story depended on which panes were
looked at, and with a pinned pane on how the window was laid out. Held here:
- a story input's dice start from the count of story inputs alone: the same lines meet the same dice, and end in the same player,
  world, people and places, with any number of a pane's views looked at before, between and after them;
- every input is still counted (an operation says which input it belongs to), and a command's dice are its own: no two inputs of
  a play share a key, two of the same command running included;
- a line whose turn did not stand gives its step back, and meets the same dice when it is said again;
- a save from before has no count of story inputs: it starts from its count of inputs, so no key of its past is met again;
- the count is saved with the input, and a new campaign starts both at nothing;
- no dice of the game's are drawn from the count of every input but the command's own and the opening's.
Run: python tools/sim/story_dice_639_test.py"""
import ast
import json
import os
import random
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
SEED = 39
stub = simlib.Stub("warrior", SEED)
simlib.install(stub)
from engine import streams
from storage import statehash
from storage.campaign import DB_NAME, CampaignMeta, CampaignStore

STORY = 10                                               # lines of the story in a play
PLAYS = {                                                # the pane's commands asked before the nth line of the story (0: before the first)
    "alone": {},
    "views": {0: ["#stats"], 2: ["#inventory", "#inventory"], 3: ["#map"], 7: ["#journal", "#stats", "#party"], 10: ["#stats"]},
    "fails": {4: ["#stats"]},                            # ...and here the fifth line's turn fails and is said again
}


def play(name: str, kind: str, out: str) -> None:
    """The child: one play. What each input's dice started from, what the story showed, and what the save holds at the end."""
    import nightbot
    import ui.console as uc
    shown, now = [], {"i": -1, "story": False}
    for fn in ("narrate", "say", "note", "ledger"):
        uc.put(fn, lambda *a, _fn=fn, **k: shown.append((now["i"], now["story"], f"{_fn}:{a[0] if a else ''}")))
    uc.put("dialogue", lambda before, speaker, speech, after="", *a, **k: shown.append((now["i"], now["story"], f"dialogue:{speaker}:{speech}")))
    uc.put("panel", lambda *a, **k: False)
    streams.STRICT = True
    game = simlib.campaign(name, seed=SEED, turn=1, minutes=480)
    store, ws = game.store, game.scene
    bot = nightbot.Bot(ws, ws.world, random.Random(SEED), stub=stub, persona="wanderer")
    stub.bot = bot
    fail = {"on": False, "raised": 0}
    below = simlib.below()

    def chat(**k):
        if fail["on"] and k["format"].get("title") == "ActionPlan":
            fail["raised"] += 1
            raise ConnectionError("the model server cannot be reached")
        return below.chat(**k)

    simlib.stand_in(chat=chat)
    begun, real = [], ws.new_input

    def new_input(text, *a, **k):
        real(text, *a, **k)
        begun.append({"text": text, "key": streams.key(), "steps": store.meta.steps, "story": getattr(store.meta, "story_steps", None)})

    ws.new_input = new_input
    queue, told, last = [], [0], {"text": "I look around."}
    commands = {n: list(c) for n, c in PLAYS[kind].items()}

    def ask(*a, main=False, **k):
        if not main:
            return "yes"
        now["i"] += 1
        fail["on"] = False
        if commands.get(told[0]):
            now["story"] = False
            return commands[told[0]].pop(0)
        if told[0] >= STORY:
            now["story"] = False                         # the parting line is no line of the story's
            return "quit"
        now["story"] = True
        if "again" in last:                              # the line that failed, said again
            told[0] += 1
            return last.pop("again")
        text = bot.decide()[0]
        if kind == "fails" and told[0] == 4 and not fail["raised"]:
            fail["on"] = True                            # this line's turn fails and rolls back: it is not counted as told
            last["again"] = text
            return text
        told[0] += 1
        return text

    uc.put("ask", ask)
    ws.run()
    d = statehash.dump(store)
    ops = store.load_operations()["ops"]
    end = {"begun": begun, "steps": store.meta.steps, "story": getattr(store.meta, "story_steps", None), "raised": fail["raised"],
           "shown": [s for _, story, s in shown if story], "player": store.player_text(), "world": json.dumps(store.load_world_state()),
           "tables": {t: statehash._h(rows) for t, rows in d.items() if t in ("places", "npcs", "npc_memory", "entities")},
           "story_ops": [(o["id"], o["kind"]) for o in ops if not str(o["kind"]).startswith("command:")],
           "command_ops": [o["kind"] for o in ops if str(o["kind"]).startswith("command:")]}
    game.session.close()
    saved = CampaignStore.open_or_create(name)
    end["saved"] = (saved.meta.steps, getattr(saved.meta, "story_steps", None))
    saved.close()
    Path(out).write_text(json.dumps(end, ensure_ascii=False), encoding="utf-8")


if len(sys.argv) > 1 and sys.argv[1] == "--play":
    play(*sys.argv[2:5])
    sys.exit(0)

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def apart(kind: str) -> dict:
    name = f"story_dice_639_{kind}"
    out = Path("saves") / f"{name}.json"
    done = subprocess.run([sys.executable, __file__, "--play", name, kind, str(out)], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    if done.returncode != 0 or not out.exists():
        raise RuntimeError(f"the play '{kind}' failed:\n{done.stdout[-1500:]}\n{done.stderr[-3000:]}")
    return json.loads(out.read_text(encoding="utf-8"))


with ThreadPoolExecutor(3) as pool:                      # each play in a process of its own (the stand-in model counts what it invents)
    alone, views, fails = pool.map(apart, ("alone", "views", "fails"))


def story(run) -> list[dict]:
    return [b for b in run["begun"] if not b["text"].startswith("#")]


def commands(run) -> list[dict]:
    return [b for b in run["begun"] if b["text"].startswith("#")]


n_views = sum(len(c) for c in PLAYS["views"].values())
check(f"each play told its {STORY} lines of the story, and the one with views asked its {n_views} commands among them",
      len(story(alone)) == len(story(views)) == STORY and len(commands(views)) == n_views and not commands(alone)
      and [b["text"] for b in story(alone)] == [b["text"] for b in story(views)], ([b["text"] for b in story(alone)], [b["text"] for b in story(views)]))

# ---- a story input's dice start from the count of story inputs alone
check("a line of the story starts its dice from the seed, the count of story inputs and the line", [b["key"] for b in story(alone)]
      == [f"{SEED}:{i + 1}:{b['text']}" for i, b in enumerate(story(alone))], [b["key"] for b in story(alone)][:3])
apart_at = next((i for i, (x, y) in enumerate(zip(story(alone), story(views))) if x["key"] != y["key"]), None)
check("the same lines meet the same dice with a pane's views looked at before, between and after them", apart_at is None,
      (apart_at, story(alone)[apart_at or 0]["key"], story(views)[apart_at or 0]["key"]))
check("...and the story shows the same words", alone["shown"] == views["shown"] and len(alone["shown"]) > STORY // 2,
      next(((x, y) for x, y in zip(alone["shown"], views["shown"]) if x != y), (len(alone["shown"]), len(views["shown"]))))
check("...and ends in the same player, the same world, the same people and places", alone["player"] == views["player"] and alone["world"] == views["world"]
      and alone["tables"] == views["tables"] and len(alone["player"] or "") > 1000, [t for t in alone["tables"] if alone["tables"][t] != views["tables"][t]])
check("...with the same operations of the story under the same ids", alone["story_ops"] == views["story_ops"] and len(alone["story_ops"]) >= STORY,
      (len(alone["story_ops"]), len(views["story_ops"])))

# ---- every input is still counted, and a command's dice are its own
check("every input is counted, a command with the rest; the story's count is of its lines", (alone["steps"], alone["story"]) == (STORY, STORY)
      and (views["steps"], views["story"]) == (STORY + n_views, STORY) and [b["steps"] for b in views["begun"]] == list(range(1, STORY + n_views + 1)),
      (alone["steps"], alone["story"], views["steps"], views["story"]))
check("a command is an operation of its own input, as before", len(views["command_ops"]) == n_views and not alone["command_ops"], views["command_ops"])
keys = [b["key"] for b in views["begun"]]
check("no two inputs of a play share a key: two of the same command running have dice of their own, and none has a line's",
      len(set(keys)) == len(keys) and all(b["key"] == f"{SEED}:{b['steps']}:{b['text']}" for b in commands(views)), keys[:6])
check("the counts are saved with the input", tuple(views["saved"]) == (views["steps"], views["story"]) and tuple(alone["saved"]) == (STORY, STORY), views["saved"])

# ---- a line whose turn did not stand
tried = [b for b in fails["begun"] if not b["text"].startswith("#")]
twice = [(x, y) for x, y in zip(tried, tried[1:]) if x["text"] == y["text"] and x["story"] == y["story"]]
check("a line whose turn failed gives its step back and meets the same dice when it is said again", fails["raised"] > 0 and len(twice) == 1
      and twice[0][0]["key"] == twice[0][1]["key"] and fails["story"] == STORY and len(tried) == STORY + 1, (fails["raised"], [(b["text"][:20], b["story"]) for b in tried]))
check("...and the play goes on to the same end as the one that did not fail: the same player and world", fails["player"] == alone["player"]
      and fails["world"] == alone["world"] and fails["shown"][-3:] == alone["shown"][-3:], (len(fails["shown"]), len(alone["shown"])))

# ---- a save from before, and a new one
old = CampaignMeta.model_validate({"name": "x", "seed": 5, "created": "", "steps": 37, "turn": 30})
new = CampaignMeta(name="y", seed=5, created="")
check("a save from before starts its count of story inputs from its count of inputs; a new campaign starts both at nothing",
      (old.steps, getattr(old, "story_steps", None)) == (37, 37) and (new.steps, getattr(new, "story_steps", None)) == (0, 0),
      (getattr(old, "story_steps", None), getattr(new, "story_steps", None)))
check("...and a count that is saved is kept as it is", getattr(CampaignMeta.model_validate({"name": "x", "seed": 5, "created": "", "steps": 37, "story_steps": 30}),
                                                        "story_steps", None) == 30)
folder = Path("saves/story_dice_639_kept")
shutil.rmtree(folder, ignore_errors=True)
folder.mkdir(parents=True)
shutil.copyfile("data/replay/saves_v16/world_script.db", folder / DB_NAME)
kept = CampaignStore.open_or_create(folder.name)
raw = json.loads(kept._kv_text("campaign"))
check("a save kept from version 16 has no count of story inputs, and opens with it at its count of inputs", "story_steps" not in raw and raw["steps"] > 0
      and getattr(kept.meta, "story_steps", None) == kept.meta.steps == raw["steps"], (raw.get("steps"), getattr(kept.meta, "story_steps", None)))
kept.close()

# ---- a scene's own inputs, with no model asked: what waits for a later turn, a command that rolls, a save from before going on
from engine import operation as _op
KEEP = int(_op.RETENTION["deferred_turns"])
game = simlib.campaign("story_dice_639_ages", seed=SEED, turn=1, minutes=480)
store, ws = game.store, game.scene
tried = []
ws.run_deferred_one = lambda kind, data: tried.append(kind)
ws.new_input("I look around.", story=True)
ws.defer("waits", {})
for _ in range(KEEP + 2):
    ws.new_input("#stats", story=False)
ws.new_input("I wait.", story=True)
ws.run_deferred()
check(f"what a line left for a later turn is still tried at the next line, with {KEEP + 2} of a pane's views looked at between (more than the turns it may wait)",
      tried == ["waits"] and store.load_deferred() == [], (tried, store.load_deferred(), store.meta.steps, store.meta.story_steps))
tried.clear()
ws.new_input("#inventory", story=False)
ws.defer("of a command", {})                             # left by a command: its age is the story's too
ws.defer("old", {})
for i in range(KEEP):
    ws.new_input(f"I walk on, {i}.", story=True)
ws.run_deferred()
check(f"...one a command left is tried {KEEP} lines of the story later", sorted(tried) == ["of a command", "old"], tried)
tried.clear()
ws.defer("too old", {})
for i in range(KEEP + 1):
    ws.new_input(f"I rest, {i}.", story=True)
ws.run_deferred()
check(f"...and one is dropped untried {KEEP + 1} lines of the story later, as before", tried == [] and store.load_deferred() == [], (tried, store.load_deferred()))


def rolls() -> list:
    return [streams.get("scene").random(), streams.get("combat").random(), streams.new_id(), streams.new_id(stream="ops"), random.random(),
            streams.keyed("frame_stand_in", "someone", "", store.meta.story_steps).random()]


at = (store.meta.steps, store.meta.story_steps)
ws.new_input("I draw my blade.", story=True)
first = (streams.key(), rolls())
store.meta.steps, store.meta.story_steps = at            # the same line met again, this time after a command that rolled dice of its own
ws.new_input("#stats", story=False)
theirs = rolls()
ws.new_input("I draw my blade.", story=True)
check("a command that rolls dice and makes ids of its own leaves the next line every die it would have had", (streams.key(), rolls()) == first
      and theirs != first[1], (first[0], streams.key()))
before = CampaignMeta.model_validate({k: v for k, v in store.meta.model_dump().items() if k != "story_steps"} | {"steps": 37})
store.meta = before
met = []
for text, is_story in (("I go on.", True), ("#stats", False), ("I go on.", True), ("#map", False), ("I stop.", True)):
    ws.new_input(text, story=is_story)
    met.append(streams.key())
check("a save from before goes on from its count: its story's keys come after every key it has had, and none is met twice",
      met == [f"{SEED}:38:I go on.", f"{SEED}:39:#stats", f"{SEED}:39:I go on.", f"{SEED}:41:#map", f"{SEED}:40:I stop."] and len(set(met)) == 5, met)
game.session.close()
shutil.rmtree("saves/story_dice_639_ages", ignore_errors=True)

# ---- the source keeps it so
reads = {}
for d in ("engine", "scenes", "npc", "services", "storage", "world", "llm", "ui"):
    for p in sorted(Path(d).rglob("*.py")):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr == "steps" and (
                    (isinstance(node.value, ast.Name) and node.value.id == "meta") or (isinstance(node.value, ast.Attribute) and node.value.attr == "meta")):
                reads.setdefault(p.as_posix(), []).append(node.lineno)
check("the campaign's count of every input is read where it was and nowhere new: the scene's four (the count, a command's dice, the opening's, "
      "an operation's input) and the recorder's four", {f: len(v) for f, v in reads.items()} == {"scenes/world.py": 4, "engine/recording.py": 4}, reads)
found = {}
for d in ("engine", "scenes", "npc", "services", "storage", "world", "llm", "ui"):
    for p in sorted(Path(d).rglob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            dice = isinstance(fn, ast.Attribute) and (fn.attr in ("begin", "keyed", "new_id") and isinstance(fn.value, ast.Name) and fn.value.id == "streams")
            if dice and any(isinstance(x, ast.Attribute) and x.attr == "steps" for a in list(node.args) + [k.value for k in node.keywords] for x in ast.walk(a)):
                found.setdefault(p.as_posix(), []).append(node.lineno)
check("no dice of the game's are drawn from the count of every input but the command's own and the opening's (scenes/world.py, twice)",
      {f: len(v) for f, v in found.items()} == {"scenes/world.py": 2}, found)

for kind in PLAYS:
    shutil.rmtree(f"saves/story_dice_639_{kind}", ignore_errors=True)
    Path(f"saves/story_dice_639_{kind}.json").unlink(missing_ok=True)
shutil.rmtree(folder, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
