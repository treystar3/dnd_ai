"""(f718) The data hash in two parts. `data` is the rules: every file under data/ as before, with a mark where each string stood
that data/rules/wording.yaml declares as wording (a line's words, by which the engine decides nothing). `words` is those strings
alone. A recording keeps both. The kept recordings are held to `data` only, so a reworded line no longer forces them to be made
again; the replay itself still parts when a word a recording drew has changed. A line's place is still a rule: its key, how many
lines its list holds, whether it is empty. Whatever nobody listed is rules."""
import contextlib, io, json, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 18))
import yaml
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

tmp = Path(tempfile.mkdtemp(prefix="datahash_718_"))
shutil.copytree("data", tmp / "data", ignore=shutil.ignore_patterns("replay", "measured", "runtime"))
both = getattr(statehash, "data_hashes", None)
if both is None:
    check("statehash.data_hashes gives the two digests", False)
    print("\nFAILED: " + ", ".join(bad))
    sys.exit(1)
base = both(tmp)
check("two digests, the rules' and the wording's, and data_hash is the rules'",
      set(base) == {"data", "words"} and base["data"] != base["words"] and statehash.data_hash(tmp) == base["data"] and statehash.words_hash(tmp) == base["words"])
check("...read the same twice, and the same from this checkout", both(tmp) == base and both() == base, (both(), base))


def moved(rel: str, old: str, new: str) -> set[str]:
    """Which digests move when old becomes new in the file, the file put back after."""
    f = tmp / "data" / rel
    text = f.read_text(encoding="utf-8")
    if text.count(old) != 1:
        return {f"({text.count(old)} of {old!r} in {rel})"}
    f.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    got = both(tmp)
    f.write_text(text, encoding="utf-8", newline="\n")
    return {k for k in got if got[k] != base[k]}


def y(rel: str):
    return yaml.safe_load((tmp / "data" / rel).read_text(encoding="utf-8"))


told, stay, fails = y("rules/told.yaml"), y("rules/stay.yaml"), y("rules/failures.yaml")
line = told["approach"][0]
check("a told line reworded moves the wording and not the rules", moved("rules/told.yaml", line, line + " At a run.") == {"words"})
check("...a failure line the same", moved("rules/failures.yaml", fails["turn_not_taken"][0], "Nothing came of it. Once more.") == {"words"})
moments, body, voice = y("rules/moments.yaml"), y("rules/body.yaml"), y("rules/voice.yaml")
ends = next(sh["ends"] for sh in moments["shapes"] if sh.get("ends"))
past = next(k["past"] for k in body["kinds"].values() if k.get("past"))
check("...and a line found under any key of its kind (a * in the list)",
      moved("rules/moments.yaml", f'"{ends}"', '"It is over, and the room breathes out."') == {"words"}
      and moved("rules/body.yaml", f'"{past}"', '"You try, and it is far beyond you."') == {"words"}
      and moved("rules/voice.yaml", f'"{voice["no_words"][0]}"', '"{speaker} only looks at you."') == {"words"})
# ---- a line's place is a rule
check("a new kind of told line moves the rules: code must draw it", "data" in moved("rules/told.yaml", "approach:", 'newly_told:\n  - "A line nobody has read yet."\napproach:'))
check("a line added to a list moves the rules: a line is drawn by the count",
      "data" in moved("rules/failures.yaml", "turn_not_taken:\n", 'turn_not_taken:\n  - "One more line than there was."\n'))
check("a kind under another name moves the rules: the engine finds a line by its key", "data" in moved("rules/failures.yaml", "\nturn_not_possible:", "\nturn_never_possible:"))
check("a line emptied moves the rules: code may ask whether there is one", "data" in moved("rules/moments.yaml", f'"{ends}"', '""'))
check("...and a comment in a wording file moves neither", moved("rules/told.yaml", "approach:", "# a note to the next writer\napproach:") == set())
top = told["flight_words"][0][0]
check("a number in a wording file is still a rule", moved("rules/told.yaml", f"[{top}, ", f"[{top + 1}, ") == {"data"})
words_at = told["flight_words"][0][1]
check("...and so is where it stands beside its words", "data" in moved("rules/told.yaml", f'[{top}, "{words_at}"]', f'["{words_at}", {top}]'))
check("a line of a file's listed key moves the wording alone", moved("rules/stay.yaml", stay["lines"]["arrive_in"][0], "{label} walks in.") == {"words"})
check("...and a number of that same file the rules alone", moved("rules/stay.yaml", f"gap_turns: {stay['gap_turns']}", f"gap_turns: {stay['gap_turns'] + 1}") == {"data"})
check("a changed number in a rules file moves the rules alone", moved("rules/road.yaml", "leg_hours: 6", "leg_hours: 7") == {"data"})
road = y("rules/road.yaml")
check("a sentence in a file nobody listed is rules", moved("rules/road.yaml", road["barrier"]["ask"], road["barrier"]["ask"] + " Well?") == {"data"})
(tmp / "data" / "rules" / "new_table.yaml").write_text('said: "A sentence in a file made today."\n', encoding="utf-8")
with_new = both(tmp)
check("...and so is a whole new file", with_new["data"] != base["data"] and with_new["words"] == base["words"])
(tmp / "data" / "rules" / "new_table.yaml").unlink()
decl = (tmp / "data" / "rules" / "wording.yaml").read_text(encoding="utf-8")
check("the list of wording is itself a rule: adding to it moves the rules",
      "data" in moved("rules/wording.yaml", "rules/told.yaml:", 'rules/weather.yaml: ["**"]\n  rules/told.yaml:'))
check("a listed file that cannot be read as data is hashed whole, as rules", moved("rules/told.yaml", "approach:", "approach: [unclosed\nother:") == {"data", "words"})
check("...and so is one holding a value with no plain reading (a date)", moved("rules/told.yaml", "approach:", "made: 2026-11-17\napproach:") == {"data", "words"})
f = tmp / "data" / "rules" / "told.yaml"
f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
check("line endings move neither", both(tmp) == base)

# ---- the startup check holds the list to the tree
problems = statehash.wording_problems()
check("the startup check passes the list as it stands", problems == [], problems[:3])
check("...a listed file that is not there is named", any("nowhere.yaml" in p for p in statehash.wording_problems({"rules/nowhere.yaml": ["**"]})))
check("...and a key that holds no words", any("no_such_key" in p for p in statehash.wording_problems({"rules/stay.yaml": ["no_such_key"]})))
from engine import data_check
check("...and the game's own startup check runs it", "wording_problems" in Path(data_check.__file__).read_text(encoding="utf-8"))

# ---- a recording keeps both, and a replay holds it to the rules alone
import rerun
from engine import recording, told as told_lines
src = Path(recording.__file__).read_text(encoding="utf-8")
check("a recording keeps the wording's digest beside the rules'", "**statehash.data_hashes()" in src)
for name in ("stub_short", "stub_party", "stub_fight"):
    meta = json.loads((rerun.golden(name) / "meta.json").read_text(encoding="utf-8"))
    check(f"{name} was made on these rules, and keeps the wording it was made on", meta.get("data") == base["data"] and len(meta.get("words", "")) == 64,
          (str(meta.get("data"))[:12], base["data"][:12]))

asked = {"n": 1}
real_digest = statehash.digest


def digest(*a, **k):
    """The replay reads the state once after each input: counting those tells which input a told line was shown in."""
    asked["n"] += 1
    return real_digest(*a, **k)


statehash.digest = digest
real_say = told_lines.say
drawn: list[int] = []


def run(folder: Path, say) -> tuple[dict, str]:
    asked["n"] = 1
    drawn.clear()
    told_lines.say = say
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            out = rerun.replay(folder)
    finally:
        told_lines.say = real_say
    return out, err.getvalue()


def noting(kind, n=0, **facts):
    drawn.append(asked["n"])
    return real_say(kind, n, **facts)


def reworded(kind, n=0, **facts):
    drawn.append(asked["n"])
    return real_say(kind, n, **facts) + " Truly."


shows = None
for name in ("stub_fight", "stub_party", "stub_short"):
    copy = tmp / name
    shutil.copytree(rerun.golden(name), copy)
    meta = json.loads((copy / "meta.json").read_text(encoding="utf-8"))
    meta["words"] = "0" * 64                                   # made on other wording, the same rules
    (copy / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8", newline="\n")
    out, err = run(copy, noting)
    check(f"a recording made on other wording is replayed whole when nothing it drew has changed ({name})",
          out["parted"] is None and out["matched"] == out["of"] and out.get("words") == "other" and out.get("data") == "same", out["parted"])
    check("...with no warning that the rules differ", "data hash differs" not in err, err[:200])
    if drawn and shows is None:
        shows = (copy, drawn[0])
check("a kept recording shows a told line (the next check needs one)", shows is not None)
if shows:
    copy, at = shows
    out, err = run(copy, reworded)
    # a fight keeps its told lines with its state until its round is shown, so the parting is that input or a later one of the fight
    check(f"...and parts once a line it drew is reworded: drawn in input {at}, never before it",
          bool(out["parted"]) and out["parted"]["input"] >= at and ("shown other words" in out["parted"]["why"] or "state differs" in out["parted"]["why"]),
          out["parted"])
    meta = json.loads((copy / "meta.json").read_text(encoding="utf-8"))
    meta["data"] = "1" * 64
    (copy / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8", newline="\n")
    out, err = run(copy, noting)
    check("a recording made on other rules is still warned of", "data hash differs" in err and out.get("data") == "other", err[:200])

shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
