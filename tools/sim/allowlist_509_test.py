"""(f509) The allow-list widened to every table the fight reads, held to the code that runs it, both ways (engine/data_check.py
allowlist_problems, run at every startup with the rest of the check): legendary effects (engine/legendary.py: by name, by category,
by a world mechanic, else enabled: false), spellcraft expressions, relic powers, summon forms, boss kits' options, martial maneuvers,
movement kinds, healing forms, passive mechanics (the refusal that lived at core/rules.py import). The real tables pass, read by pattern
and by the syntax tree alike; for each table a copy with one unknown id makes the check name the table and the id; a handler with no
row is named; every combat mechanic is exercised by a fixture case. Nothing stays in the process."""
import gzip
import json
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import yaml
from core import rules
from engine import combat, data_check, items, legendary, martial, spellcraft, summons

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- the real tables pass, read by pattern and by the syntax tree alike
fast, precise = data_check.allowlist_problems(), data_check.allowlist_problems(precise=True)
check("every table the fight reads is held to the code, both ways, and holds today", fast == [] and precise == [], (fast[:3], precise[:3]))
lits_f, keys_f = data_check.scan_code()
lits_p, keys_p = data_check.scan_code(precise=True)
ids = set(items.LEGENDARY) | set(spellcraft.EXPR)
check("the two readings of the code agree on every id a table names, and on every row key the tables use",
      {i for i in ids if i in lits_f} == {i for i in ids if i in lits_p} and all((k in keys_f) == (k in keys_p) for row in list(summons.FORMS.values()) + list(martial.MANEUVERS.values()) for k in row),
      (sorted({i for i in ids if (i in lits_f) != (i in lits_p)})[:10]))
check("the check runs at startup with the rest, and the import-time refusal is gone from core/rules.py",
      "bad += allowlist_problems()" in open("engine/data_check.py", encoding="utf-8").read() and "raise RulesError(f\"passive_mechanics.yaml" not in open("core/rules.py", encoding="utf-8").read()
      and data_check.check() == [])

# ---- legendary effects: by name, by category, by a world mechanic, else enabled: false
E = items.LegendaryEffect
named = data_check.code_named()
cats = data_check.creature_categories()
world = set(rules.ENGINE_WORLD_MECHANICS)
check("how an effect is handled: named by the code, a slayer's category, a wonder's world mechanic, or nothing",
      legendary.how_handled(items.LEGENDARY["hex"], named, cats, world) == "named" and legendary.how_handled(items.LEGENDARY["dragonslayer"], named, cats, world) == "category"
      and legendary.how_handled(items.LEGENDARY["wellspring"], named, cats, world) == "world"
      and legendary.how_handled(E(id="moonblade", name="Moonblade", applies="weapon", description="x"), named, cats, world) == "")
planted = {**items.LEGENDARY, "moonblade": E(id="moonblade", name="Moonblade", applies="weapon", description="x")}
probs = data_check.allowlist_problems(tables={"legendary": planted})
check("an enabled effect nothing runs is named, and told to say enabled: false", any("moonblade" in m and "enabled: false" in m for m in probs), probs)
check("...and one that says so is let be", data_check.allowlist_problems(tables={"legendary": {**items.LEGENDARY, "moonblade": E(id="moonblade", name="Moonblade", applies="weapon", description="x", enabled=False)}}) == [])
probs = data_check.allowlist_problems(tables={"legendary": {**items.LEGENDARY, "moonbane": E(id="moonbane", name="Moonbane", applies="weapon", category="moon folk", description="x")}})
check("a slayer of a category the bestiary lacks is named", any("moonbane" in m and "moon folk" in m for m in probs), probs)
probs = data_check.allowlist_problems(tables={"legendary": {**items.LEGENDARY, "moon_charm": E(id="moon_charm", name="Moon Charm", applies="jewelry", world="moon_reading", description="x")}})
check("a wonder of a world mechanic the engine lacks is named", any("moon_charm" in m and "moon_reading" in m for m in probs), probs)
check("no enabled effect is a promise the code cannot keep: all 116 are handled", sum(1 for e in items.LEGENDARY.values() if e.enabled and not legendary.how_handled(e, named, cats, world)) == 0
      and len(items.LEGENDARY) == 116)

# ---- the eight other tables: a planted unknown id is named each way
probs = data_check.allowlist_problems(tables={"expressions": {**spellcraft.EXPR, "moonfire": {"element": "fire", "kind": "damage", "label": "Moonfire", "text": "x", "depict": "x"}}})
check("an expression nothing runs is named", any("spellcraft.yaml expressions.moonfire" in m for m in probs), probs)
probs = data_check.allowlist_problems(handled={"expressions_compared": data_check._compared("engine/spellcraft.py", ("eid",)) | {"eclipse"}})
check("...and a handler with no expression", any("eclipse" in m and "spellcraft.yaml does not name" in m for m in probs), probs)
AC = yaml.safe_load(open("data/rules/accessories.yaml", encoding="utf-8"))
AC2 = json.loads(json.dumps(AC)); AC2["powers"]["moon"] = {"name": "a moon's touch", "kind": "moon", "text": "x"}
probs = data_check.allowlist_problems(tables={"relics": AC2})
check("a relic power of a kind no handler runs is named", any("accessories.yaml" in m and "'moon'" in m for m in probs), probs)
probs = data_check.allowlist_problems(handled={"relics": data_check._compared("engine/relics.py", ("kind",)) | {"eclipse"}})
check("...and a relic handler no power uses", any("engine/relics.py handles a power kind 'eclipse'" in m for m in probs), probs)
forms = json.loads(json.dumps(summons.FORMS)); forms["striker"]["moonlit"] = True
probs = data_check.allowlist_problems(tables={"summons": forms})
check("a summon form's key no code reads is named", any("summons.yaml forms.striker" in m and "'moonlit'" in m for m in probs), probs)
forms = json.loads(json.dumps(summons.FORMS)); forms["moon"] = {"bodies": 1}
probs = data_check.allowlist_problems(tables={"summons": forms})
check("...and a form with no summon kind", any("summons.yaml forms.moon" in m for m in probs), probs)
BS = yaml.safe_load(open("data/rules/bosses.yaml", encoding="utf-8"))
BS2 = json.loads(json.dumps(BS)); BS2["kits"]["dragon"]["legendary"].append({"name": "Moon Roar", "kind": "moon", "text": "x"})
probs = data_check.allowlist_problems(tables={"bosses": BS2})
check("a boss option of a kind _do cannot run is named", any("bosses.yaml kits.dragon" in m and "'moon'" in m for m in probs), probs)
probs = data_check.allowlist_problems(handled={"bosses": data_check._compared("engine/bosses.py", ("kind",)) | {"eclipse"}})
check("...and a boss handler no kit uses", any("engine/bosses.py _do handles an option kind 'eclipse'" in m for m in probs), probs)
MT = json.loads(json.dumps(martial.MANEUVERS)); MT["trip"]["moonlit"] = 1; MT["pin"]["status"] = "moonstruck"
probs = data_check.allowlist_problems(tables={"martial": MT})
check("a maneuver's key no code reads, and a status the rules lack, are named", any("maneuvers.trip" in m and "'moonlit'" in m for m in probs) and any("maneuvers.pin" in m and "moonstruck" in m for m in probs), probs)
probs = data_check.allowlist_problems(handled={"martial_named": {"eclipse"}})
check("...and a maneuver the code names that the table lacks", any("engine/martial.py names a maneuver 'eclipse'" in m for m in probs), probs)
MV = yaml.safe_load(open("data/rules/movement.yaml", encoding="utf-8")); MV2 = json.loads(json.dumps(MV)); MV2["kinds"]["moonwalk"] = {"label": "Moonwalk"}
probs = data_check.allowlist_problems(tables={"movement": MV2})
check("a movement kind with no handler is named", any("movement.yaml kinds.moonwalk" in m for m in probs), probs)
probs = data_check.allowlist_problems(handled={"movement": data_check._compared("engine/movement.py", ("kind",)) | {"eclipse"}})
check("...and a movement handler the table lacks", any("engine/movement.py handles a movement kind 'eclipse'" in m for m in probs), probs)
HL = yaml.safe_load(open("data/rules/healing.yaml", encoding="utf-8")); HL2 = json.loads(json.dumps(HL)); HL2["forms"]["moon"] = {"share": 1}
probs = data_check.allowlist_problems(tables={"healing": HL2})
check("a healing form with no handler is named", any("healing.yaml forms.moon" in m for m in probs), probs)
probs = data_check.allowlist_problems(handled={"healing": data_check._compared("engine/healing.py", ("form",)) | {"mend", "eclipse"}})
check("...and a healing handler the table lacks; mend, the plain form, is the else arm and counts", any("engine/healing.py handles a healing form 'eclipse'" in m for m in probs) and not any("'mend'" in m for m in probs), probs)
PM = {**rules.MECHANICS, "moon_sense": rules.MechanicDef(id="moon_sense", kind="combat", values=(1, 2), text="x")}
probs = data_check.allowlist_problems(tables={"mechanics": PM})
check("a passive mechanic the engine cannot run is refused here, as it was at import", any("passive_mechanics.yaml moon_sense: the engine doesn't know how to run it" in m for m in probs), probs)
probs = data_check.allowlist_problems(handled={"mechanics_combat": set(rules.ENGINE_COMBAT_MECHANICS) | {"eclipse"}})
check("...and an engine set entry that is neither a mechanic nor a legendary effect is named; cleave, a legendary effect, is not", any("core/rules.py names a mechanic 'eclipse'" in m for m in probs) and not any("'cleave'" in m for m in probs), probs)
check("every table is one of the nine", data_check.ALLOW_TABLES == ("legendary", "expressions", "relics", "summons", "bosses", "martial", "movement", "healing", "mechanics"))

# ---- every combat mechanic is exercised by a fixture case
given = set()
for s in range(4):
    given |= set(json.load(gzip.open(f"tools/sim/fixtures/fights/shard{s}.json.gz"))["coverage"]["mechanics_given"])
combat_m = {m.id for m in rules.MECHANICS.values() if m.kind == "combat"}
check("every combat mechanic (137) is given to a fighter in a recorded fixture case", combat_m <= given and len(combat_m) == 137, sorted(combat_m - given)[:10])
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
