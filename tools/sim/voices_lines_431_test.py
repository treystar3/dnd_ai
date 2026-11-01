"""(f431) Voices and lines the f425 night showed again and again: a hire told both to ask a question back and never to ask anything,
whose 13 replies sent back left lines like "You desire that I accompany you to the guild house. That is what I shall do."; every order
said back as a question ("Moving toward food? Yes, that is what I seek too."); "The guild here think well of you (trusted)." 29 to 42
times a run; 98 of 270 road walks opening "You have been walking for..."; and what got past both gates: "window_pane_", "parchment,#her",
a passage ending on "{", "]h1[", a line headed "REASON:", "kind: ambush, detail: 1 x ghost"."""
import json, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 31))
import ui.console as uc
SHOWN = []
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: SHOWN.append((_fn, str(a[0]) if a else "")))
uc.panel = lambda name, data: False
from pydantic import ValidationError
from engine import clock, hygiene, quirks, standing, voice_profile, voices
from llm.contracts import RoadEvent

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- one who never asks is never told to ask
kit = {"questions": "never", "opening": "echo"}
member = {"id": "h1", "name": "Hilsa", "temper": ["wary", "gentle"], "quirks": {"voice": ""}, "speech": {"kit": kit}}
speak = quirks.blueprint(member)
check("a hire who never asks back is not told to ask a question back before giving anything away", not any(l.startswith("Asks") for l in speak), speak)
check("...nor to say a question back as a question", not any("as a question" in l for l in voices.lines(kit)), voices.lines(kit))
check("...and an accent's 'checks they were understood' goes for them", "understood" in voices.drops(kit))
tongue = next((t for t in quirks.Q.get("tongues", {}).values() if "understood" in (t.get("habits") or "")), None)
if tongue is not None:
    real = voice_profile.tongue_of
    voice_profile.tongue_of = lambda m: tongue
    line = voice_profile.accent({"speech": {"kit": kit, "fluency": "fluent"}})
    voice_profile.tongue_of = real
    check("...in the accent they are told", line and "understood" not in line, line)
asker = {"questions": "after", "opening": "echo"}
check("one who may ask keeps the question back", any("as a question" in l for l in voices.lines(asker)))
check("echo is for a real question, never an order said back", all("never an order" in l for l in voices.lines(asker) if "repeats" in l))

# ---- the standing note once, and again only when it changes
import shutil as _sh
_sh.rmtree("saves/voices_lines_431_test", ignore_errors=True)
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
world = load_world()
store = CampaignStore.open_or_create("voices_lines_431_test")
store.meta.seed = 31; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(31))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("trading_square")
town, day = ws.standing_town(), clock.day(ws.minutes)
ws.player.standing.setdefault(town, {})["guild"] = [40.0, day]
def notes():
    SHOWN.clear()
    ws.standing_arrive()
    return [t for _, t in SHOWN if "think well of you" in t]
first, again = notes(), notes()
check("the guild's regard is said on arriving", len(first) == 1, first)
check("...and not again on the next arrival while it is the same", again == [], again)
ws.player.standing[town]["guild"] = [-40.0, day]
check("...and said again when it changes", len(notes()) == 1)
store.close()
_sh.rmtree("saves/voices_lines_431_test", ignore_errors=True)

# ---- a road walk never opens on the count of hours
ctx = {"hostile": False, "checks": ["perception"], "kind": "sight", "want_journey": True}
def road_ok(journey):
    try:
        RoadEvent.model_validate_json(json.dumps({"title": "T", "journey": journey, "scene": "A heron.", "kind": "sight"}), context=ctx)
        return True
    except ValidationError:
        return False
check("'You have been walking for nearly six hours' is sent back", not road_ok("You have been walking for nearly six hours since leaving the wetlands."))
check("...and 'For over five hours you have been trekking'", not road_ok("For over five hours you have been trekking the March."))
check("...a walk that opens on the road stands", road_ok("The Valley Road runs wide between the vineyards, Jorn a step behind you."))

# ---- what got past both gates
for raw, want, kind in (("two carts pass your window_pane_, their wheels", "window pane,", "id"),
                        ("the nearest parchment,#her eyes", "parchment, her", "broken"),
                        ("Hilsa shifts her weight beside you,{", "beside you,", "json"),
                        ("REASON: Thavathiel shows how he carries himself.\nThe road bends.", "The road bends.", "json"),
                        ("A ghost. kind: ambush, detail: 1 x ghost, creatures: ghost. It comes.", "A ghost. It comes.", "json"),
                        ("a blow ]h1[ lands", "a blow lands", "json")):
    got = hygiene.clean(raw)
    check(f"mended at the screen: {raw[:38]!r}", want in got and "_" not in got and "#" not in got and "{" not in got and "REASON" not in got, got)
    check(f"...and sent back at the gateway as {kind}", hygiene.problem("narrate", {"text": raw})[0] == kind, hygiene.problem("narrate", {"text": raw}))
check("a #command in the game's own note is left as typed", hygiene.clean("Use #inventory to see your items") == "Use #inventory to see your items")
check("an ellipsis stays an ellipsis", hygiene.clean("He waits... then nods.") == "He waits... then nods.")

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
