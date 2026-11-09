"""(f450) The golden stub recording (data/replay/sessions/stub_short, kept since f441) replays exactly, as part of the suite. Before this
nothing in tools/sim replayed it: rerun_441_test records and replays a session of its own, and the golden was checked by hand before a
push. The rebuild's Bundle B moves the runtime out from under a recorded session feature by feature; this is the gate every feature
passes before it is pushed. A part here is read with `python3 tools/rerun.py --golden --rebless`, which prints what moved; the
recording is kept again only when the state of every input is unchanged and the builder can say which shown line moved and why.
(f495) Three kept recordings: stub_short (the night bot's walk), stub_party (the party's talk, from its script) and stub_fight (the
fights, from its script: a hire fighting and falling, a round that cannot be read and one that cannot be told, a draught mid-fight, a
boss's drops named, a level gained, a fight run from). Each script's census names what its recording must hold, and refuses one that
holds less: checked here on the kept recording, and on copies with a part taken out."""
import copy
import importlib.util
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# (f476) both kept recordings: stub_short (the night bot's walk) and stub_party (a script's: the party's talk and its claims, a lie, work,
# a request taken and given up, the party held back while a deed is done, a reply that fails and the line said again); (f495) stub_fight
for name in ("stub_short", "stub_party", "stub_fight"):
    out = subprocess.run([sys.executable, "tools/rerun.py", "--golden", name], capture_output=True, text=True, timeout=900)
    lines = [l for l in (out.stdout + out.stderr).splitlines() if l.strip()]
    last = lines[-1] if lines else ""
    check(f"{name} replays through the real turn: every input the same state, outcomes and words", out.returncode == 0
          and last.startswith("all ") and "inputs matched" in last, lines[-6:])
    check("...and it is the recording the tree was built on, not one made on other rules or content",
          not any("data hash differs" in l for l in lines), [l for l in lines if "hash" in l][:2])

# ---- (f495) the fight recording holds what its script promises, and its census refuses one that holds less
import rerun
spec = importlib.util.spec_from_file_location("script_stub_fight", Path("data/replay/scripts/stub_fight.py"))
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)
rec = rerun.load(rerun.golden("stub_fight"))
check("the kept stub_fight holds everything its census asks", script.census(rec) == [], script.census(rec))


def without(**how):
    r = copy.deepcopy(rec)
    if "title" in how:
        r["calls"] = [c for c in r["calls"] if c.get("title") != how["title"]]
    if "error_of" in how:
        for c in r["calls"]:
            if c.get("title") == how["error_of"]:
                c["error"] = None
    if "shown" in how:
        for t in r["turns"]:
            t["shown_text"] = [l for l in t.get("shown_text") or [] if how["shown"] not in l]
    if "dead" in how:
        for t in r["turns"]:
            ent = (t.get("rows") or {}).get("entities") or {}
            ent["added"] = {k: v for k, v in (ent.get("added") or {}).items() if '"hire", "dead"' not in str(v)}
    return script.census(r)


check("...the census refuses a recording without the victory", "the victory" in without(shown="Victory."))
check("...without the rare piece named, or the legendary, or the relic", "LootName" in without(title="LootName") and "LegendaryName" in without(title="LegendaryName")
      and "AccessoryName" in without(title="AccessoryName"))
check("...without the hire's death", "a hire's death" in without(dead=True))
check("...without the failed combat intent, or the failed telling", "a failed CombatIntent" in without(error_of="CombatIntent")
      and "a failed Narration" in without(error_of="Narration"))
check("...without the level gained, or the fight run from", "the level gained" in without(shown="LEVEL UP!") and "the fight run from" in without(shown="You got away."))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
