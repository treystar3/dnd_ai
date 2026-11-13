"""(f620) The lines the engine keeps and hands on carry no dash. f617 took the dashes out of news and history at their writers; its review
found the same thing outside that class (docs/design/18 part F). Traced, most engine lines already pass a filter (the screen's story
outputs, the gateway, the narrator's event, a fight's tell). Four kinds did not: a townsperson's memory (17 sites build one), a hire's
memory, a fact of the truth layer (28 sites), and the fight's story where the improvised act wrote into it beside tell. Each kind now
takes the dashes out where it is made (npc/models.py Memory, engine/party.py remember, engine/truth.py Fact and present_lines,
engine/combat.py tell), so no site can put one in, and a ratchet reads what every prose task is sent.
Run: python tools/sim/kept_lines_dash_620_test.py"""
import gzip
import json
import random
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools/sim")
import simlib
stub = simlib.Stub("warrior", 3)
SENT = []                                   # every request the test's own play sends: (the answer's contract, the request's text)
_chat = stub.chat
def chat(**k):
    SENT.append((k["format"].get("title", "?"), "\n".join(str(m["content"]) for m in k["messages"] if m["role"] != "system")))
    return _chat(**k)
stub.chat = chat
simlib.install(stub)
simlib.quiet_console()
from core import yamlio
from engine import combat, combat_improv, hygiene, party, truth
from engine.domain_events import ContractDropped, Gift, Worked
from llm import contracts
from npc.models import Memory

ROOT = Path(__file__).resolve().parent.parent.parent
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


DASH = re.compile(r"—|–|--|\S[ \t]+-[ \t]+\S")
def dashed(text: str) -> bool:
    return bool(DASH.search(text or ""))


# ---- each maker, on lines of shapes no site writes
LINES = ["The stranger did the work I asked - mend the fence - and I paid.", "Saw the stranger at the mill — nobody else did.",
         "The road was shut -- the bridge was out.", "It took 3–5 days."]
made = [Memory(day=1, turn=1, text=x).text for x in LINES]
check("a townsperson's memory is kept without its dash, whoever makes it", not any(dashed(x) for x in made), made)
check("...the words all still there", "mend the fence" in made[0] and "I paid" in made[0] and "nobody else did" in made[1] and "3 to 5 days" in made[3], made)
check("...a hyphen inside a word is no dash, and a slot for a name is left as it is",
      Memory(day=1, turn=1, text="{them} sold me a well-made half-cloak.").text == "{them} sold me a well-made half-cloak.")
member = {"id": "h1", "name": "Bea"}
for i, x in enumerate(LINES):
    party.remember(member, 1, x, key=f"k{i}")
party.remember(member, 2, "They paid me - late - and I said so.", key="k0")           # the same memory, told anew
held = [m["text"] for m in member["memories"]]
check("a hire's memory is kept without its dash, new or told anew", len(held) == len(LINES) and not any(dashed(x) for x in held)
      and "late" in held[0], held)
facts = [truth.Fact("lately", x).text for x in LINES] + [truth.Fact(facet="here", text=LINES[0], id="x").text]
check("a fact of the truth layer carries no dash, whatever facet builds it", not any(dashed(x) for x in facts), facts)
fight = combat.Combat(fighters=[], place="greywood")
for x in LINES:
    combat.tell(fight, x[0].lower() + x[1:])
check("a fight's story carries no dash (f413), as before", len(fight.story) == len(LINES) and not any(dashed(x) for x in fight.story), fight.story)

# ---- the fight's story has one way in: the improvised act's own line goes through it
from engine.battlefield import BattleZone, Battlefield
from world.loader import authored
world0 = authored()
told = []
for seed in range(40):
    char, _ = simlib.make_character("warrior", random.Random(2))
    me = combat.fighter_from_character(char)
    troll = combat.fighter_from_creature(world0.bestiary["troll"], 3, "normal", "e1", name="the troll")
    f = combat.Combat(fighters=[me, troll], place="greywood")
    f.battlefield = Battlefield(zones={"z1": BattleZone(id="z1", name="open ground", tags=["open"])}, edges=[], start="z1")
    me.zone_id = troll.zone_id = "z1"
    combat_improv.resolve(f, me, troll, "I duck - then roll — away", random.Random(seed), effect="break_engagement")
    told += [(seed, x) for x in f.story]
tried = [x for _, x in told if "duck" in x]
check("an improvised act's own words reach the story without their dashes, whether it works or not",
      len(tried) >= 40 and not any(dashed(x) for x in tried) and any(x.startswith("It works") for _, x in told)
      and any("goes wrong" in x for _, x in told), sorted({x for x in tried if dashed(x)})[:3] or tried[:2])
src = {f: f.read_text(encoding="utf-8") for d in ("engine", "scenes", "services", "npc") for f in (ROOT / d).glob("*.py")}
grows = re.compile(r"\.story(?:\.append|\.insert|\.extend|\s*\+=)")
writers = sorted(f.name for f, text in src.items() if grows.search(text))
check("...and the story grows in engine/combat.py alone (a new writer goes through tell)", writers == ["combat.py"], writers)
mem = re.compile(r"""["']memories["']\s*[\],)]\s*(?:\)\s*)?(?:\.append|\.insert|\.extend|\+=)|setdefault\(\s*["']memories["']""")
writers = sorted(f.name for f, text in src.items() if mem.search(text))
check("...and a hire's memories have the one writer", writers == ["party.py"], writers)

# ---- the class, played: the world script, then deeds whose titles and tasks hold a dash
import world_script
run = world_script.play("kept_lines_620", stub)
ws, store = run.game.scene, run.game.store
ws.player.guild_rank = "F"
ws.enter("guild_house")
hired = ws.party_service.hire(ws.party_roster()[0], ws.player.character.level)
ws.player.party_mode = "with"
party.remember(hired, 3, "We took the Hollow road - the short one - and it cost us.")
ws.enter(world_script.PLACE)
from engine import pulse, retrieval
people = store.load_npcs([r.id for r in retrieval.people_in_town(store, ws.world, pulse.town_of(ws.world, world_script.PLACE))[:3]])
ws.residents = ws.present = people
seen = tuple(n.id for n in people)
with ws.operation("test", "deeds with a dash in them"):
    ws.notice(Worked(minute=ws.minutes, place=world_script.PLACE, witnesses=seen, npc=people[0].id, name=people[0].name,
                     task="mend the fence — the long one - by the barn", paid=30), *people)
    ws.notice(Worked(minute=ws.minutes, place=world_script.PLACE, witnesses=seen, npc=people[1].id, name=people[1].name,
                     task="carry sacks - all of them", unasked=True), *people)
    ws.notice(ContractDropped(minute=ws.minutes, place=world_script.PLACE, witnesses=seen, npc=people[2].id, name=people[2].name,
                              quest="q620", title="Rats - in the granary", how="abandoned", guild=False), *people)
    ws.notice(Gift(minute=ws.minutes, place=world_script.PLACE, witnesses=seen, npc=people[0].id, name=people[0].name,
                   item="a loaf - still warm"), *people)
kept = [m.text for row in store.npc_rows() for n in store.load_npcs([row.id]) for m in n.memories] + [m.text for n in people for m in n.memories]
check("the world script plays whole, and no memory of anyone in the save carries a dash",
      all(run.cover.values()) and len(kept) > 20 and not any(dashed(x) for x in kept), (len(kept), sorted({x for x in kept if dashed(x)})[:3]))
check("...among them the work done and the job walked away from, remembered by the ones they were done to",
      any("mend the fence" in x and "I paid" in x for x in kept) and any("rats" in x and "walked away" in x for x in kept)
      and any("a loaf" in x and "still warm" in x for x in kept),
      [x for x in kept if "fence" in x or "sacks" in x or "rats" in x or "loaf" in x][:8])
check("...nor any memory a hire holds", len(hired["memories"]) >= 2 and not any(dashed(m["text"]) for m in hired["memories"]), hired["memories"])

sc = truth.scene_of(ws)
townsperson = people[0]
VIEWERS = {"townsfolk": truth.viewer_for_npc(townsperson, ws.world), "hire": truth.viewer_for_hire(f"hire:{hired['id']}"), "maren": truth.MAREN,
           "banter": truth.PARTY, "narrator": truth.NARRATOR}
check("every profile of the truth layer has its reader here", set(VIEWERS) == set(truth.T["profiles"]), sorted(set(truth.T["profiles"]) ^ set(VIEWERS)))
lines = {p: [l for name in truth.T["profiles"][p] for l in sc.view(v, p).lines(name)] + sc.view(v, p).streets() + sc.view(v, p).text().split("\n")
         for p, v in VIEWERS.items() if p in truth.T["profiles"]}
flat = [l[4:] if l.startswith("  - ") else l for ls in lines.values() for l in ls]                     # the view's own list mark is no dash
check("no line of the truth view, under any profile, carries a dash", all(len(ls) > 4 for ls in lines.values())
      and not any(dashed(x) for x in flat), sorted({x for x in flat if dashed(x)})[:4])
check("...among them the deeds read back from the event log, which carried one",
      any("mend the fence" in x for x in lines["narrator"]) and any("mend the fence" in x for x in lines["townsfolk"])
      and any("Rats, in the granary" in x for x in lines["narrator"]), [x for x in lines["narrator"] if "stranger" in x][:6])
check("...and the strangers a townsperson sees beside the player", any("a stranger here with the one in front of you" in x for x in lines["townsfolk"]),
      lines["townsfolk"][:8])

# ---- the ratchet, at the model's door: what every prose task is sent, in the kept recordings and in this play
READINGS = {"ActionPlan", "CombatIntent", "CampIntent", "PartyIntent"}     # a reading of the player's words: its "speech" is theirs, and it is never shown


def prose_task(title: str) -> bool:
    """A task whose answer the player reads as prose: its contract has a prose field (data/rules/hygiene.yaml), however deep."""
    cls = getattr(contracts, title, None)
    if cls is None or title in READINGS:
        return False
    def keys(s):
        if isinstance(s, dict):
            for k, v in s.items():
                if k == "properties" and isinstance(v, dict):
                    yield from v
                yield from keys(v)
        elif isinstance(s, list):
            for v in s:
                yield from keys(v)
    return bool(set(keys(cls.model_json_schema())) & hygiene.PROSE)


def data_words() -> str:
    """Every string that stands in data/ and holds a dash, each on a line of its own, in small letters: the world's authored words
    (places, lore, roads, sayings) and the rules' own wording. They are a class of their own, still open (docs/design/18 part F,
    question 2), and not lines the engine writes."""
    out = []
    def walk(v):
        if isinstance(v, str):
            if dashed(v):
                out.append(" ".join(v.lower().split()))
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(k), walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
    for f in sorted((ROOT / "data").rglob("*.yaml")):
        if "measured" in f.parts or "replay" in f.parts:
            continue
        walk(yamlio.safe_load(f.read_text(encoding="utf-8")))
    return "\n".join(out)


AROUND = re.compile(r"((?:[^\s]+[ \t]+){0,2}[^\s]+)[ \t]*(—|–|--|(?<=[ \t])-(?=[ \t]))[ \t]*([^\s]+(?:[ \t]+[^\s]+){0,2})")
# The labels and rules a request's builder writes itself, which keep their dashes (GOALS.md, f413: "the game's own notes, lists and
# labels keep theirs"). Each is the label's own dash with the words that make it that label, named with why it is no story line; only
# that span is let through, never the rest of its line. A dash that is none of these, no list mark and no string of data/ is in a line
# the engine handed a prose task: filter it where it is made, or, if it is a label, name it here.
LABELS = [
    (r"^PLACE: [^:;.]+? - ", "the place's name, then what is seen of it"),
    (r"^ROAD: [^:;.]+? - ", "the road's name, then what it is"),
    (r"^ROADS \(id: (name, )?from - to\)", "a list's own head"),
    (r"\b[a-z_]+: [a-z_]+ - [a-z_]+(?=;|$)", "a road by its id, and the ids of its two ends"),
    (r"^(POWER|WONDER|ITEM): [^:;.]+? - ", "a power's name, then what it does"),
    (r"; Power - ", "a power's name, then what it does"),
    (r"^THE MOMENT: \w+ - ", "the moment's word, then why"),
    (r"^THE FRAME SHOWS: [^.]*? - ", "a rule for the frame"),
    (r"^FOR A GESTURE ONLY - WHAT (THEY CARRY|IS HERE)", "a head"),
    (r"^(RIGHT NOW|HOW YOU TALK|FOR THIS EXCHANGE|WHAT YOU REMEMBER|WORDS YOU MAY USE THIS TIME, AS THEY ARE \(only if they fit\)"
     r"|WHAT OTHERS HERE SAID LATELY WHEN THE PLAYER LEFT \(not these, nor the like of them\)): - ", "a list of one, its mark after the head"),
    (r"(?<=[:;] )[^:;]+?: (he|she|they|it), [\w -]+? - (?=a |an |the )", "WHO IS WHO: each one's pronoun and people, then what they are"),
    (r"^ALREADY SHOWN THIS VISIT \(the player has read these here; do not describe them again - say what is new\)", "a rule in a head"),
    (r"^WHAT YOU SELL \(fixed prices - quote them exactly", "a rule in a head"),
    (r"^What you're working toward \(private - share it only if it comes up naturally\)", "a rule for the speaker"),
    (r"These are loose notes, not lines to quote - vary your own words", "a rule for the speaker (faith)"),
    (r"(his|her|their) usual manner shows through cracks - even a hard", "a rule for the exchange"),
]
# Known and open, named so it is seen: a line of what a speaker also knows right now (scenes/world.py npc_context), where the game's
# own word for a town's regard ("unknown - just a stranger", shown as a label in the standing pane too) is handed over inside a fact.
# Those lines mix rules and facts and were left as written by the plan; this one is for the owner to rule on.
OPEN = [
    (r"^How people around here regard the stranger: unknown - just a stranger\.", "the town's regard, in the game's label for it"),
]
LABELS = [(re.compile(p), why) for p, why in LABELS + OPEN]
MARK = re.compile(r"^\s*-\s+")


def strays(text: str, words: str) -> list[str]:
    """The lines of a request that carry a dash which is no list mark, no label's own and no string of data/ (the dash with the two
    words either side of it, as data/ holds them)."""
    out = []
    for raw in text.split("\n"):
        line = MARK.sub("", raw).strip()
        if not dashed(line):
            continue
        rest = line
        for p, _ in LABELS:
            rest = p.sub(" | ", rest)
        if any(" ".join(m.group(0).lower().split()) not in words for m in AROUND.finditer(rest)):
            out.append(line)
    return out


words = data_words()
recorded = []
for calls in sorted((ROOT / "data" / "replay" / "sessions").glob("*/calls.jsonl.gz")):
    for row in map(json.loads, gzip.open(calls, "rt", encoding="utf-8")):
        if row.get("kind") == "chat":
            recorded.append((row["title"], "\n".join(str(m["content"]) for m in row["request"]["messages"] if m["role"] != "system")))
titles = {t for t, _ in recorded + SENT}
unknown = sorted(t for t in titles if getattr(contracts, t, None) is None)
prose = [(t, text) for t, text in recorded + SENT if prose_task(t)]
check("the recordings and this play are read: every contract is known, and many are prose", not unknown and len(recorded) > 200
      and len(SENT) > 10 and len({t for t, _ in prose}) >= 8, (unknown, len(recorded), len(SENT), sorted({t for t, _ in prose})))
found = {}
for t, text in prose:
    for line in strays(text, words):
        found.setdefault((t, line[:160]), 0)
        found[(t, line[:160])] += 1
check("no prose task is sent a dashed line that is not a label, a list mark or a string of data/ (the ratchet)",
      not found, "\n     " + "\n     ".join(f"{t} x{n}: {line}" for (t, line), n in list(found.items())[:60]))
probe = "YOUR MEMORIES OF THEM:\n  - earlier today: The stranger did the work I asked - mend the fence by the barn - and I paid 30 copper.\n" \
        "WHAT IS HAPPENING: the stranger acted (bar the granary door) - success"
check("...and the ratchet does catch a memory or a fact with a dash, were one sent", len(strays(probe, words)) == 2, strays(probe, words))
probe = ["PLACE: Parth - Timber houses - and a mill that burned", "THE MOMENT: tense - they took it - a loaf",
         "WHO IS WHO (each one's pronoun and people: never write them otherwise): Ghak Skurz: he, orc - a hired mage - who took it"]
check("...nor does a label let the rest of its line through", all(strays(x, words) for x in probe), [x for x in probe if not strays(x, words)])
carried = [MARK.sub("", raw).strip() for _, text in prose for raw in text.split("\n") if dashed(raw)]
unused = [p.pattern for p, _ in LABELS if not any(p.search(line) for line in carried)]
check("...every label it names is one a request really carries (a label gone is taken off the list)", not unused, unused)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
