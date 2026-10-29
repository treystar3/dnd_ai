"""(f380) What the second logged playthrough showed that f377-f379 had not already fixed.
- "I watch the troll and look for an opening" was read as fouling the troll's legs, the event said only "it catches: the troll is fouled
  and slowed", and the narrator wrote a lance driven into its shoulder. Watching for an opening is now a thing of its own, and every
  improvised event says what the player tried before what came of it.
- A round of a fight is no longer rewritten for trailing participles: 10 of 11 rounds were, the rewrites trailed as often as the drafts,
  and two lost a blow's marker.
- Walking into the guild hall, the narrator walked the room one person at a time (ten of them). The engine now gives it the first people
  the eye falls on and a number for the rest; a look still sees everyone.
- Maren, greatsword on her back, was 'counting arrows' from the contractors' list: she keeps doings of her own."""
import inspect, random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import llm.gateway as gw
CALLS = []
_chat = gw._client.chat
def chat(*a, **k):
    CALLS.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
for f in ("narrate", "note", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f, lambda *a, **k: None)
from engine import checks, clock, combat, combat_improv, doings
from npc.traits import load_traits
from scenes import combat_scene as cs
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()

# ---- watching for an opening
check("'I watch the troll and look for an opening' is watching for an opening",
      combat_improv.read_effect("I watch the troll and look for an opening") == "read_opening"
      and combat_improv.read_effect("The player watches the troll for an opening.") == "read_opening")
check("...and the other improvisations still read as themselves", combat_improv.read_effect("I throw sand in its eyes") == "distract"
      and combat_improv.read_effect("I jam my lance into its knee") == "disable")

def fight_with_troll():
    char, _ = simlib.make_character("warrior", random.Random(2))
    me = combat.fighter_from_character(char)
    troll = combat.fighter_from_creature(world.bestiary["troll"], 3, "normal", "e1", name="the troll")
    return combat.Combat(fighters=[me, troll], place="greywood"), me, troll

real_roll = checks.roll
checks.roll = lambda odds, *a, **k: ("success", 1)
fight, me, troll = fight_with_troll()
combat_improv.resolve(fight, me, troll, "I watch the troll and look for an opening", random.Random(1))
check("a good read leaves the troll open to the player's next blow", combat.is_open(troll, fight.round + 1), troll.counters)
check("...and the events say what the player tried, then what came of it",
      len(fight.story) == 2 and fight.story[0].startswith("You try it (I watch the troll") and "gap in" in fight.story[1]
      and "open to your next blow" in fight.story[1], fight.story)
fight, me, troll = fight_with_troll()
combat_improv.resolve(fight, me, troll, "I jam my lance into its knee", random.Random(1))
check("fouling a foe is told with the attempt before it", len(fight.story) == 2 and fight.story[0].startswith("You try it (I jam my lance")
      and "fouled and slowed" in fight.story[1], fight.story)
checks.roll = lambda odds, *a, **k: ("failure", 99)
fight, me, troll = fight_with_troll()
combat_improv.resolve(fight, me, troll, "I watch the troll and look for an opening", random.Random(1))
check("a failure is one event, with the attempt in it", len(fight.story) == 1 and "goes wrong" in fight.story[0]
      and "I watch the troll" in fight.story[0], fight.story)
checks.roll = real_roll

# ---- a round of a fight is not rewritten for trailing participles
check("no narration is rewritten for trailing participles (f382; fights first, f380)", "tails" not in inspect.signature(__import__("scenes.voice", fromlist=["fresh"]).fresh).parameters)

# ---- walking into the guild hall
shutil.rmtree("saves/playthrough2_test", ignore_errors=True)
store = CampaignStore.open_or_create("playthrough2_test")
store.meta.seed = 3; store.meta.minutes = 120; store.meta.turn = 1; store.save_meta()          # mid-morning: the hall is full
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="trading_square", guild_rank="F"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("guild_house")
ws.apply_backfill()
clerk = ws.clerk_here()
clerk.name_known_to_player = True
everyone = ws.people_view()
check("the hall has more people than the eye takes in at once", len(everyone) > ws.FIRST_SEEN, everyone)
first, more = ws.first_seen(everyone)
check("walking in, two are seen first and the rest are a number", len(first) == ws.FIRST_SEEN and more == len(everyone) - ws.FIRST_SEEN,
      (first, more))
check("...and the clerk the player knows by name is one of them", clerk.label() in [l for l, _, _ in first], (clerk.label(), first))
check("the same moment gives the same first sight", ws.first_seen(everyone) == (first, more))

def narration_asked(fn):
    CALLS.clear()
    fn()
    return next((m[-1]["content"] for t, m in CALLS if t == "Narration"), "")

unseen = [l for l, _, _ in everyone if l not in [f[0] for f in first]]
asked = narration_asked(lambda: ws._narrate_now("You walk into the guild hall.", "I head to the guild hall"))
check("the arrival passage is given the first people and a number for the rest",
      "the first the eye falls on, walking in" in asked and f"and {more} other" in asked and "never one by one" in asked
      and not any(f"  - {l}:" in asked for l in unseen), asked[asked.find("PEOPLE HERE"):][:900])
asked = narration_asked(lambda: ws._narrate_now("The player waits a moment.", "I wait"))
check("once the place is shown, the next passage is given everyone", all(f"  - {l}:" in asked for l, _, _ in everyone)
      and "never one by one" not in asked, asked[asked.find("PEOPLE HERE"):][:900])
ws.enter("trading_square"); ws.enter("guild_house"); ws.apply_backfill()
stub.plan = [{"kind": "look"}]
CALLS.clear()
ws.turn("I look around the hall")
asked = next((m[-1]["content"] for t, m in CALLS if t == "Narration"), "")
check("walking in and looking around sees the whole room", asked and "never one by one" not in asked
      and asked.count("Right now:") == len(ws.people_view()), asked[asked.find("PEOPLE HERE"):][:1400])

# ---- Maren's own doings
maren = types.SimpleNamespace(id="maren", role="guild_contractor", activity="")
seen = {doings.doing_for(maren, s, d * 1440 + m) for s in range(4) for d in range(20) for m in (120, 400, 700)}
own = {e["text"] for e in doings.entries("", "maren")}
check("Maren does what Maren does, never a contractor's arrows", seen <= own and "counting arrows" not in seen, seen - own)
check("...while the contractors keep theirs", "counting arrows" in {e["text"] for e in doings.entries("guild_contractor")})
check("a person's own doings are checked like a role's", not [p for p in doings.problems(set(doings.D["by_role"]), set(clock.PERIOD_NAMES))
                                                          if "by_person" in p])

store.close()
shutil.rmtree("saves/playthrough2_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
