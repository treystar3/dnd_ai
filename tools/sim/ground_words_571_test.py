"""(f571) The narrator is told what each zone's ground is like, in plain words from its tags (battlefields.yaml tag_words), in the
fight's opening and in every round, a single open zone included: so the prose and the cover rule (f570) read the same ground. A
hazardous zone says its own hazard where the data names one (hazards), else treacherous footing. The block is headed as facts to show
only when they matter, in the narrator's own words. Nothing the engine hands over for open ground speaks of walls or crates, and no
tag phrase stands word for word in a recorded fight's narrations."""
import gzip, json, random, re, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 71)
simlib.install(stub)
from pathlib import Path
from engine import battlefield as bf, battlefield_builder as bb, combat, data_check
from engine.battlefield import BattleEdge, BattleZone, Battlefield
from scenes import combat_prompts as cp
from world.loader import authored

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = authored()
W = bb.B["tag_words"]
FURNITURE = re.compile(r"\b(walls?|crates?|barrels?|pillars?|carts?|boulders?|furniture|tables?|trees?|rubble)\b", re.I)

# ---- the words: every tag has its phrase, and a zone reads as its tags
check("every terrain tag has plain words", set(W) == set(bf.TERRAIN_TAGS), set(bf.TERRAIN_TAGS) ^ set(W))
open_zone = BattleZone(id="z1", name="the forest trail", tags=["open"])
line = bf.ground_words(open_zone)
check("an open zone is named and said by what it is good for", line.startswith("the forest trail") and W["open"] in line, line)
check("...a zone with no tags reads as open", W["open"] in bf.ground_words(BattleZone(id="z", name="the street", tags=[])))
check("...and the zone called open ground does not say it twice", bf.ground_words(BattleZone(id="z", name="open ground", tags=["open"])).count("open ground") == 1,
      bf.ground_words(BattleZone(id="z", name="open ground", tags=["open"])))
both = bf.ground_words(BattleZone(id="z", name="a jumble of boulders", tags=["cover", "difficult"]))
check("a zone with two tags says both", W["cover"] in both and W["difficult"] in both, both)
check("no raw tag list is handed over", "(cover, difficult)" not in both and "[cover" not in both, both)

# ---- hazards: the zone's own where the data names it, treacherous footing otherwise
H = bb.B["hazards"]
named = next(iter(H))
check("a hazardous zone with a hazard of its own says it", H[named] in bf.ground_words(BattleZone(id="z", name=named, tags=["hazardous"])))
plain = bf.ground_words(BattleZone(id="z", name="a nameless stretch", tags=["hazardous"]))
check("...another says treacherous footing that can wound", "treacherous footing that can wound" in plain, plain)
check("...a repeated zone further on keeps its own hazard", H[named] in bf.ground_words(BattleZone(id="z", name=named + bb.FURTHER, tags=["hazardous"])))
real_B = dict(bb.B)
bb.B.pop("hazards")
try:
    check("...and data with no hazards section falls back, never crashing a fight", "treacherous footing" in bf.ground_words(BattleZone(id="z", name=named, tags=["hazardous"])))
finally:
    bb.B.clear(); bb.B.update(real_B)

# ---- the heading: said once in each fight system prompt, not in every request
check("the fight's two system prompts say how the ground is to be used", cp.GROUND_HEAD in cp.NARRATE_SYSTEM and cp.GROUND_HEAD in cp.START_SYSTEM
      and "own words" in cp.GROUND_HEAD and "never in these words" in cp.GROUND_HEAD, cp.GROUND_HEAD)

def fight_on(zones, edges=()):
    char, _ = simlib.make_character("warrior", random.Random(2))
    me = combat.fighter_from_character(char)
    wolf = combat.fighter_from_creature(world.bestiary["wolf"], 1, "normal", "e1", name="wolf")
    f = combat.Combat(fighters=[me, wolf], place="greywood")
    f.battlefield = Battlefield(zones={z.id: z for z in zones}, edges=list(edges), start=zones[0].id)
    me.zone_id = wolf.zone_id = zones[0].id
    return f

# ---- a round: who stands where always; what a place is like only when it changed or someone newly stands there
OPEN = W["open"].split(": ", 1)[-1]
boulders = BattleZone(id="z2", name="a jumble of boulders", tags=["cover", "difficult"])
f = fight_on([open_zone, boulders], [BattleEdge(a="z1", b="z2")])
full = bf.narrative_snapshot(f)
check("asked whole, the ground says the open zone's words beside who stands there", OPEN in full and "wolf" in full, full)
check("...and open ground hands over no walls or crates", not FURNITURE.search(full), FURNITURE.findall(full))
bf.ground_brief(f)
check("building the opening's ground notes nothing: a telling that never stands leaves it untold", f.ground_told == {}, f.ground_told)
snap = bf.narrative_snapshot(f, changed_only=True)
check("...so a round after an opening never told (failed, or a scripted entrance) is given the ground whole, empty zones too",
      OPEN in snap and W["cover"] in snap and "a jumble of boulders" in snap, snap)
g = fight_on([open_zone, boulders], [BattleEdge(a="z1", b="z2")])
bf.note_ground_told(g)                                         # that round stood
check("...and once it stood, the empty zones it was given are told as well", set(g.ground_told) == {"z1", "z2"}, g.ground_told)
bf.note_ground_told(f, opening=True)                           # the opening stood: every zone is told
snap = bf.narrative_snapshot(f, changed_only=True)
check("the round after the opening: who stands where, and no words for ground already told", "the forest trail: " in snap and "wolf" in snap
      and OPEN not in snap, snap)
req = cp.narrate_request("Greywood", "noon", "I attack", ["you strike the wolf"], "a sword", "barely touched", ["wolf"], 1, ground=snap)
check("...the request carries no heading of its own", cp.GROUND_HEAD not in req and "THE GROUND NOW" in req, req[:300])
bf.note_ground_told(f)
f.player.zone_id = "z2"
snap = bf.narrative_snapshot(f, changed_only=True)
check("someone newly stands among the boulders: that zone says what it is like", W["cover"] in snap and W["difficult"] in snap, snap)
check("...and the zone they left, with no one new, does not", OPEN not in snap, snap)
check("...asked again before the telling stands, it asks in the same words", bf.narrative_snapshot(f, changed_only=True) == snap)
bf.note_ground_told(f)
check("...and once it stood, with no one moved, the next round says neither", W["cover"] not in bf.narrative_snapshot(f, changed_only=True))
f.battlefield.zones["z1"] = BattleZone(id="z1", name="the forest trail", tags=["hazardous"])
snap = bf.narrative_snapshot(f, changed_only=True)
check("a zone whose state changed says what it is like now", W["hazardous"] in snap, snap)
bf.note_ground_told(f)
check("the fight keeps one entry a zone and no more", set(f.ground_told) == {"z1", "z2"} and f.ground_told["z2"][1] == ["player"], f.ground_told)
f.player.zone_id = "z1"; bf.note_ground_told(f); f.player.zone_id = "z2"
check("...and one who comes back to an emptied zone stands there newly", W["cover"] in bf.narrative_snapshot(f, changed_only=True))
f = fight_on([open_zone])

# ---- the opening: a single open zone is told too
brief = bf.ground_brief(f)
check("the opening tells a single open zone", "the forest trail" in brief and W["open"] in brief, brief)
f2 = fight_on([open_zone, BattleZone(id="z2", name="a jumble of boulders", tags=["cover", "difficult"])], [BattleEdge(a="z1", b="z2")])
brief2 = bf.ground_brief(f2)
check("...and every zone when there are more, the near ones as close by", W["cover"] in brief2 and "close by" in brief2, brief2)
check("a fight with no battlefield says nothing of the ground", bf.ground_brief(type("F", (), {"battlefield": None})()) == "")

# ---- every open main zone in the data: nothing handed over speaks of walls or crates
seen, hits = 0, []
for fam in bb.FAMILIES:
    for z in bb.B[fam]["main"]:
        if set(z.get("tags", [])) <= {"open"}:
            seen += 1
            ff = fight_on([BattleZone(id="z1", name=z["name"], tags=list(z.get("tags", [])))])
            text = bf.ground_brief(ff) + "\n" + bf.narrative_snapshot(ff)
            beyond = text.replace(z["name"], "")                 # the zone's own name is the data's ("the cart road"), not furniture
            if FURNITURE.search(beyond) or W["open"].split(": ", 1)[-1] not in text:
                hits.append((z["name"], FURNITURE.findall(beyond)))
check(f"all {seen} open main zones: the open words, and no walls or crates", seen > 10 and not hits, hits)

# ---- in a real fight: the opening and each round's prompt carry it
prompts = []
real = stub.a_Narration
stub.a_Narration = lambda u, k: prompts.append(u) or real(u, k)
game = simlib.campaign("ground_words_571", cls="warrior", seed=3, location="south_fields")
ws = game.scene
ws.enter("south_fields")
creature = world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "wolf", "near")
foe.behaviors["fearless"] = 1
foe.hp = foe.max_hp = 200
ws.wildlife = (creature, [foe])
stub.plan = [{"kind": "attack", "target": "wolf"}]
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
ws.turn("I attack the wolf.")
fz = ws.combat.fight
start = fz.battlefield.zones[fz.battlefield.start]
opening = [p for p in prompts if "THE GROUND" in p]
check("the fight's opening prompt carries the whole ground", opening and bf.ground_words(start) in opening[0], (len(prompts), [p[:200] for p in prompts]))
n = len(prompts)
ws.turn("I attack the wolf.")
rounds = [p for p in prompts[n:] if "THE GROUND NOW" in p]
check("...a round's says who stands where, and nothing of ground the opening told", rounds and start.name in rounds[0]
      and not any(w.split(": ", 1)[-1] in rounds[0] for w in W.values()), [p[:400] for p in prompts[n:]])
live = ws.combat.fight
check("...what was told is on the live fight after each turn", set(live.ground_told) >= {live.battlefield.start}, live.ground_told)
mem = ws.fight_memory()
ws.give_back(None, [], mem)
check("...and a fight given back after a stood-down operation still has it", ws.combat.fight.ground_told == mem[3] and mem[3], (mem[3], ws.combat.fight.ground_told))

# ---- a fight saved before f571: its row has no ground_told; it loads with an empty memory and its next round is told the ground whole
from services.fight import FightService
row = json.loads(ws.store.load_combat())
row["fight"].pop("ground_told", None)
old, _name, why = FightService.resume(json.dumps(row))
check("a fight saved before f571 loads, with nothing told of its ground", old is not None and old.ground_told == {}, why)
snap = bf.narrative_snapshot(old, changed_only=True)
check("...and its next round is given every occupied zone's words", all(bf.ground_words(old.battlefield.zones[z]) in snap
      for z in old.battlefield.zones if bf.standing(old, z)), snap)
mem = ws.fight_memory()
ws.give_back(None, [], mem[:3])
check("...and a fight memory taken before f571 (three parts) gives back an empty one", ws.combat is not None and ws.combat.fight.ground_told == {})
game.close()
stub.a_Narration = real
stub.plan = None

# ---- no tag phrase stands word for word in a recorded fight's narrations
phrases = list(W.values()) + list(H.values()) + ["treacherous footing that can wound"]
told, copied = 0, []
for calls in sorted(Path("data/replay/sessions").glob("*/calls.jsonl.gz")):
    for raw in gzip.open(calls, "rt", encoding="utf-8"):
        row = json.loads(raw)
        if str(row.get("task", "")).startswith("combat_") and "interpret" not in str(row.get("task")):
            told += 1
            answer = str(row.get("answer", "")).lower()
            copied += [(calls.parent.name, p) for p in phrases if p.lower() in answer]
check(f"no tag phrase is copied into any of {told} recorded fight narrations", told > 0 and not copied, copied)

# ---- held at start-up
check("the real data has no problems", data_check.ground_word_problems() == [], data_check.ground_word_problems())
import copy
B = copy.deepcopy({"tag_words": W, "hazards": H})
del B["tag_words"]["narrow"]
B["tag_words"]["cover"] = "things to duck behind — solid ones"
B["hazards"]["a zone nobody wrote"] = "it bites"
found = data_check.ground_word_problems(B)
for what in ("narrow", "dash", "a zone nobody wrote"):
    check(f"the start-up check names it: {what}", any(what in p for p in found), found)

# ---- the price: the gate holds on the re-kept baseline, and --rekeep sets only what the owner accepted
sys.path.insert(0, "tools")
import latency, tempfile, yaml
check("the gate holds: no fight input dearer than its kept price, every one under the limit", not any(latency.gate().values())
      and not any(latency.over_limit(base=latency._yaml(latency.BASELINE)).values()), latency.gate())
with tempfile.TemporaryDirectory() as d:
    kept = Path(d) / "baseline.yaml"
    text = Path(latency.BASELINE).read_text(encoding="utf-8")
    kept.write_text(text, encoding="utf-8", newline="")
    N = "f999: a reason, owner accepts up to 1 s"
    check("--rekeep with nothing dearer writes nothing", "nothing written" in latency.rekeep(0.2, N, path=kept) and kept.read_text(encoding="utf-8") == text)
    base = yaml.safe_load(text)
    i = next(k for k in base["estimates"]["stub_fight"] if k in latency.fight_inputs(latency.GOLDENS / "stub_fight"))
    was = base["estimates"]["stub_fight"][i]
    at = text.index("  stub_fight:", text.index("estimates:"))
    cheap = text[:at] + text[at:].replace(f"    {i}: {was}", f"    {i}: {round(was - 1.0, 1)}", 1)
    kept.write_text(cheap, encoding="utf-8", newline="")
    said = latency.rekeep(0.2, N, path=kept)
    check("...an input a whole second dearer is refused, nothing written", said.startswith("refused") and kept.read_text(encoding="utf-8") == cheap, said)
    said = latency.rekeep(1.0, "", path=kept)
    check("...a re-keep with no reason is refused, nothing written", said.startswith("refused") and "--note" in said
          and kept.read_text(encoding="utf-8") == cheap, said)
    said = latency.rekeep(1.0, N, path=kept, limit=was - 0.5)
    check("...one that would carry an input over the limit is refused, nothing written", said.startswith("refused")
          and kept.read_text(encoding="utf-8") == cheap, said)
    said = latency.rekeep(1.0, N, path=kept, today="2026-01-01")
    after = kept.read_text(encoding="utf-8")
    check("...and within what was accepted it is set to today's price, that line alone (and the note)", f"input {i} " in said
          and yaml.safe_load(after) == yaml.safe_load(text), said)
    head = after[:after.index("#   priced_at:")]
    check("--note writes the date, the reason, the cost and the inputs set into the estimates' header, as comments",
          "2026-01-01" in head and "f999: a reason, owner accepts up to 1 s" in head and f"stub_fight inputs {i}" in head
          and yaml.safe_load(after) == yaml.safe_load(text), head[-400:])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
