"""Orenna / mythology pass part 1: opening, send-off, knowledge, lore, temples."""
import sys, json
sys.path.insert(0, ".")
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)
op = json.load(open("data/opening.json"))
g = [b for b in op if b["who"] == "goddess"]
check("first goddess beat says my child", "my child" in g[0]["text"].lower() if "text" in g[0] else "my child" in json.dumps(g[0]).lower())
check("last beat names Orenna and my child", all(w in json.dumps(op[-1]).lower() for w in ("i am orenna", "my child")))
check("no hurry line", "hurry" not in json.dumps(op).lower())
so = json.dumps(json.load(open("data/send_off.json")))
check("send-off has name and gasp", "{name}" in so and "gasp" in so)
gk = json.dumps(json.load(open("data/goddess_knowledge.json")))
check("her own name no longer withheld", "Her own name" not in gk)
import character.creation as cr, inspect
check("build_character grants orenna_name", "orenna_name" in inspect.getsource(cr.build_character))
lore = open("data/world/lore.yaml").read()
check("nameless shrine removed", "nameless_shrine" not in lore)
for god in ("Aurelan","Nhaelis","Kharun","Nythra","Isrenna","Throndar","Teluun","Maerith","Dahlira","Ashkar","Ixmara","Morrowen"):
    check("lore names "+god, god in lore)
pl = open("data/world/places.yaml").read()
check("parth alcove shrine gone", "rubbed smooth" not in pl)
for god in ("Sun Warden","Teluun","Dahlira","Ashkar","Maerith","Ixmara"):
    check("temple names "+god, god in pl)
from scenes.combat_prompts import THRESHOLD_EVENT
check("death event: weaker, not colder", "weaker" in THRESHOLD_EVENT.lower() or "thin" in THRESHOLD_EVENT.lower())
src = open("scenes/world.py").read()
check("npc blank-look line", "Orenna" in src)
import yaml
P={p["id"]:p for p in yaml.safe_load(pl)}
for c in ("eldervale","ironvein","frostholm","riverhaven","sunspire","valecourt","cinderhold","hrimgard","dunmarrow","brinewatch","amaranth"):
    check("city temple "+c, any(p.get("type")=="temple" and p.get("parent")==c for p in P.values()))
check("no Morrowen temple", not any("Morrowen" in " ".join(p.get("visible",[])) for p in P.values()))
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
