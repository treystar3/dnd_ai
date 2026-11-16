"""(f648) Every word pattern searched over the whole typed line is counted, and every rule that reads the line has a line it must not
take (docs/design/21_play_faults_plan.md, B0). Found in play (docs/play/2026-11-15_play_findings.md sections 1 and 4): an ability's
own name ("Guard Breaker"), a companion named as an object ("behind Kennard's shield") and a common word ("point out the wires") each
fired an order, a retreat from a dungeon or a prayer, because a pattern matched anywhere in the line. The repairs were pinned only by
the case that made each, so a repair that catches too much passed. Held here:
- the census (tools/line_census.py): from each door a line comes in by (the turn, every intercept, every repair, every kind's
  handler, every answer to the world's question, the fight's turn), every place a pattern or a word is searched over the line,
  followed into what the line is handed to (by name, by a method reached through getattr with a prefix whether called there or
  later, that takes as many arguments as it is given, through what a function
  imports inside itself), over the line, a plain or reworded form of it, its clauses, and the line given back by a function of ours
  that returns text, or gives back in a record of its own (a NamedTuple's text fields); the reader finds what is read and
  nothing else, and reaches the places the findings named;
- what the census counts is every such search, not only those that decide a deed: a question mark, a command's mark, a word
  made singular are in it. It does not see: the line handed on by keyword or stored on the scene, read off a record by its field's
  name, compared with == or put on the left of `in`, or handed to the model (the model's reading is the interpreter's, not a pattern's);
- the count, file by file, as it stands: it only falls, and the table is lowered when one goes. A fix that adds a guard over
  the line (a question, a negation, who is addressed) may raise a file's count only beside a line in RAISED that names the
  feature and why. The count is per file, so one search swapped for another in the same file is not seen here;
- the corpus's other half (data/replay/interp_cases.yaml): every intercept and repair that reads the line's words has a case
  where it acts and a case it gets right that it must not take or change (not_by), but those the bench cannot stage and those
  held off only by a case owed, each named here, and those lists only shrink;
- a case the game gets wrong today is kept, marked owed to the fix that owes it with what it does today; it is counted as owed
  only while it goes wrong that way, the count only falls, and a case marked owed that comes out right is wrong until the mark
  comes off.
Run: python tools/sim/line_patterns_648_test.py"""
import re as _re
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from tools import interp_eval, line_census

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


# ---- the reader of the line finds what is searched over it, and nothing else
WORDS = _re.compile(r"\b(out|kneel)\b")


def helper(line):
    return WORDS.search(line)


def reword(line) -> str:
    return line.title()


class Fake:
    def door(self, text, plan):
        low = text.lower()
        if "?" in text or low.startswith("#"):                  # two
            return None
        self.step(plan, low)                                  # the line handed on as the second argument
        helper(f"{plan} {low}")                               # set in a longer string, and handed to a function of the file
        for clause in _re.split(r"[.;]", text):
            if WORDS.match(clause):                           # a clause of it
                return None
        WORDS.search(_re.sub(r"\s+", " ", low.replace("'", "")))      # reworded
        getattr(self, f"part_{plan}")(text)                   # a method reached by name
        later = getattr(self, f"bit_{plan}")                  # ...and one reached by name and called later
        later(text, plan)
        given = reword(text)                                  # given back by a function of ours that returns text
        WORDS.search(given)
        self.narrate(text)                                    # prose: not followed
        return self.untouched(plan)

    def step(self, plan, words):
        return "kneel" in words and plan

    def part_one(self, said):
        return said.endswith("!")

    def part_two(self, said, other):                          # takes more than the call passes: not reached
        return said.endswith("?")

    def bit_one(self, said, plan):
        return said.startswith("I")

    def untouched(self, plan):
        return WORDS.search(str(plan))

    def narrate(self, text):
        return WORDS.search(text)


got = line_census.sites(Fake, Fake.door, 0, ours=("__main__",))
where = sorted((s[3].split(".")[-1], s[4]) for s in got)
check("the reader finds a search over the line, a plain and a reworded form of it, a clause of it, the line set in a longer string "
      "and handed to a function, and a method reached by name",
      where == [("bit_one", "startswith"), ("door", "in"), ("door", "pattern"), ("door", "pattern"), ("door", "pattern"), ("door", "startswith"), ("helper", "pattern"),
                ("part_one", "endswith"), ("step", "in")], where)
check("...and nothing over what is not the line, and nothing in the prose it is told", not any(s[3].endswith(("untouched", "narrate")) for s in got), got)

# ---- the census reaches the places the findings named
found, by_door = line_census.census()
named = {f"{s[0]}:{fn.split('.')[-1]}" for s, (fn, what, door) in found.items()}
FINDINGS = {"scenes/plan_repairs.py:move_elsewhere": "4.1, leaving a dungeon", "scenes/plan_repairs.py:talk_to_deed": "4.2, praying",
            "scenes/combat_scene.py:orders_in": "1.1 to 1.5, an order", "engine/addressing.py:addressed": "1.1 to 1.5, who an order is said to",
            "scenes/combat_scene.py:own_part": "1.1, the player's own part", "scenes/arc_actions.py:yield_intercept": "2.7, a yielded foe",
            "scenes/party_actions.py:hire_wants_talk": "4.7, talk to a hire", "engine/intent_audit.py:risk_flags": "4.9, the audit's verbs",
            "engine/actions.py:takes_oneself": "f645, taking a thing oneself", "scenes/party_actions.py:party_dismiss": "a party dismissed by a name",
            "engine/partings.py:is_goodbye": "a goodbye", "scenes/law_actions.py:on_answer_law": "4.10, an answer to the game's question"}
FIXED: dict = {}          # {place: "fNNN: the fix that took it out of the census"}
check("the census reaches every place the findings named, but those a fix took out of it, each named with its fix",
      all(k in named or k in FIXED for k in FINDINGS) and all(k not in named for k in FIXED), {k: v for k, v in FINDINGS.items() if k not in named and k not in FIXED})
DOORS = ("fight:turn", "intercept:hire", "intercept:farewell", "answer:law", "on_use", "on_buy")
check("...from the door each is reached by", all(by_door.get(d, 0) > 0 for d in DOORS), {d: by_door.get(d) for d in DOORS})

# ---- the count, file by file: it only falls
CENSUS = {
    "engine/act.py": 1, "engine/actions.py": 4, "engine/brief.py": 1,
    "engine/candidates.py": 2, "engine/combat_improv.py": 1, "engine/convo.py": 2,
    "engine/crafting.py": 2, "engine/discovery.py": 2, "engine/elements.py": 1,
    "engine/encounters.py": 4, "engine/exits.py": 15, "engine/features.py": 3,
    "engine/intent_audit.py": 3, "engine/inventory.py": 2, "engine/lessons.py": 2,
    "engine/locks.py": 1, "engine/mentor.py": 9, "engine/mounts.py": 1,
    "engine/objects.py": 1, "engine/orenna.py": 1, "engine/partings.py": 2,
    "engine/party_director.py": 1, "engine/property.py": 1, "engine/questions.py": 1,
    "engine/severity.py": 3, "engine/situation_parts.py": 2, "engine/taming.py": 2,
    "engine/world_improv.py": 7, "scenes/arc_actions.py": 3, "scenes/camp_actions.py": 6,
    "scenes/combat_scene.py": 18, "scenes/explore_actions.py": 1, "scenes/field_actions.py": 9,
    "scenes/guild_actions.py": 2, "scenes/inventory_actions.py": 8, "scenes/law_actions.py": 3,
    "scenes/listening.py": 5, "scenes/markup.py": 2, "scenes/mentor_actions.py": 18,
    "scenes/part_actions.py": 5, "scenes/party_actions.py": 27, "scenes/passive_hooks.py": 3,
    "scenes/plan_repairs.py": 21, "scenes/property_actions.py": 2, "scenes/quirk_actions.py": 5,
    "scenes/road_actions.py": 1, "scenes/spell_actions.py": 6, "scenes/training_actions.py": 7,
    "scenes/trial_actions.py": 5, "scenes/world.py": 36,
}
RAISED = {                 # {file: (how many more, "fNNN: the guard it adds over the line, and why")}
    "engine/addressing.py": (24, "f649: who a line speaks to, read from where a name stands: it replaces the fight's searches for a name "
                                 "anywhere (combat_scene 21 to 18), and what the orders read is now only what is said to someone; "
                                 "f650: one more, a trade only when called; f653's reader sees seven more of its own places (a list or a "
                                 "choice holding the line); f654: four more, the player's own deed before a telling ('I charge and tell')"),
    "scenes/world.py": (1, "f656: the time of day a rest is asked until ('till dawn'), read once for the rest a line or a room asks for"),
    "scenes/arc_actions.py": (1, "f657: a blow at a foe who yielded, by the action table's verbs and the acting character's own abilities"),
    "scenes/party_actions.py": (3, "f674: a sentence of the player's own beside words to a companion (it starts with what they do, or names an ability; "
                                   "a speech tag is not one)"),
    "scenes/inventory_actions.py": (2, "f660: coin handed over read for the deed with a price it is for (the words that name the fee)"),
    "scenes/pastime_actions.py": (3, "f660: a haggle that only asks (a question with no word of buying) is a word with the seller, not a purchase"),
    "scenes/combat_scene.py": (6, "f659: the player's acts in a fight line beyond a draught (its parts, the consumable named) and the one foe "
                                  "the player's words name, kept as the target"),
}
now = line_census.by_file(found)
allowed = {f: CENSUS.get(f, 0) + RAISED.get(f, (0, ""))[0] for f in set(CENSUS) | set(RAISED)}
more = {f: (n, allowed.get(f, 0)) for f, n in now.items() if n > allowed.get(f, 0)}
check("no file searches the whole line more than it did (291 places in 51 files on the reader of f653, which also reads a list or a choice holding the line; re-based on the code before f653, whose repair file fell 25 to 21), but beside a raise named here",
      not more, {f: [f"{s[0]}:{s[1]} {fn} {what} (from {door})" for s, (fn, what, door) in sorted(found.items()) if s[0] == f] for f in more})
check("...and every raise names its feature and why", all(n > 0 and _re.match(r"f\d{3}: \S", why) for n, why in RAISED.values()), RAISED)
fewer = {f: (now.get(f, 0), n) for f, n in allowed.items() if now.get(f, 0) < n}
check("...and where one has gone, the table here is lowered to the count", not fewer, fewer)

# ---- the corpus's other half
cases = interp_eval.load_cases()
by_name = {c["name"]: c for c in cases}
out = interp_eval.evaluate(cases, quiet=True, save="line_patterns_648")
rules = {d.split(":", 1)[1] for d in by_door if d.startswith(("intercept:", "repair:"))}
reading = {d.split(":", 1)[1] for d, n in by_door.items() if n and d.startswith(("intercept:", "repair:"))}
UNSTAGED = {"camp": "the bench has no arc's camp to stand at", "mentor_intercept": "the bench keeps Maren away; it reads only a command's mark",
            "yielded": "the bench has no fight that ended with a foe yielding; B2 tests it in a fight of its own"}
OWED_ONLY: dict = {}       # rules held off today only by a case they get wrong
check("every intercept and repair that reads the line's words is seen acting on a case it gets right",
      not (reading - set(out["acted"]) - set(UNSTAGED)), sorted(reading - set(out["acted"]) - set(UNSTAGED)))
check("...and is held off a case it gets right", not (reading - set(out["held_off"]) - set(UNSTAGED) - set(OWED_ONLY)),
      sorted(reading - set(out["held_off"]) - set(UNSTAGED) - set(OWED_ONLY)))
check("the rules the bench cannot stage (3 when this was built) and those held off only by an owed case (1, none after f650) only grow fewer, and each reads the line",
      len(UNSTAGED) <= 3 and len(OWED_ONLY) <= 0 and set(UNSTAGED) | set(OWED_ONLY) <= reading, sorted((set(UNSTAGED) | set(OWED_ONLY)) - reading))
check("...and one held off by an owed case is still held off by one", all(any(r in ((by_name[n].get("expect") or {}).get("not_by") or []) for n in out["owed"])
                                                                         for r in OWED_ONLY), OWED_ONLY)
held = {r for c in cases for r in (c.get("expect") or {}).get("not_by") or []}
check("every rule a case holds off is a rule the game has", held <= rules, sorted(held - rules))
check("the corpus is right apart from what it owes", not out["wrong"], out["wrong"])

# ---- what is owed
check("the cases owed only grow fewer (8 when the corpus's other half was built, none after f654)", len(out["owed"]) <= 0, out["owed"])
FIX = _re.compile(r"[A-H]\d?( \d\.\d+)?: \S")
check("...each owed to a named fix of the plan, with what it does today", all(FIX.match(str(by_name[n]["owed"].get("fix", ""))) and by_name[n]["owed"].get("now")
                                                                             for n in out["owed"]),
      {n: by_name[n]["owed"] for n in out["owed"] if not (FIX.match(str(by_name[n]["owed"].get("fix", ""))) and by_name[n]["owed"].get("now"))})
check("...and each says what must not take it, or what it should do instead", all((by_name[n].get("expect") or {}).get("not_by") or (by_name[n].get("expect") or {}).get("kinds")
                                                                                 for n in out["owed"]), out["owed"])
road = by_name["road_question_is_talk"]
right_now = dict(road, name="marked_owed_but_right", owed={"fix": "B2: test", "now": {"handled_by": "exit"}})
wrong_as_owed = dict(road, name="wrong_as_owed", owed={"fix": "B2: test", "now": {"handled_by": "interpret"}}, expect={"handled_by": "exit"})
wrong_otherwise = dict(road, name="wrong_another_way", owed={"fix": "B2: test", "now": {"handled_by": "hire"}}, expect={"handled_by": "exit"})
unrepaired = dict(road, name="owed_a_repair_that_did_not_act", owed={"fix": "B2: test", "now": {"handled_by": "interpret", "repairs": ["exit"]}},
                  expect={"handled_by": "exit"})
mark = interp_eval.evaluate([right_now, wrong_as_owed, wrong_otherwise, unrepaired], quiet=True, save="line_patterns_648")
check("a case marked owed that comes out right is wrong until the mark comes off; wrong as it is owed, owed; wrong another way, wrong",
      mark["wrong"] == ["marked_owed_but_right", "wrong_another_way", "owed_a_repair_that_did_not_act"] and mark["owed"] == ["wrong_as_owed"], mark)
check("...and an owed case is counted wrong in the table by kind, not right", mark["by_kind"] == {"talk": "1/1", "intercept:exit": "0/3"}, mark["by_kind"])
given = by_name["the_thing_named_is_the_thing_given"]
made_wrong = dict(given, name="made_owed_acting", expect={"handled_by": "interpret", "first": {"item": "healing draught"}, "not_by": ["hire"]},
                  owed={"fix": "B2: test", "now": {"first": {"item": "bandage"}}})
alone = interp_eval.evaluate([made_wrong], quiet=True, save="line_patterns_648")
check("a rule that acts or is held off only on a case it gets wrong is not seen acting or held off",
      alone["owed"] == ["made_owed_acting"] and "grounded_item" not in alone["acted"] and "hire" not in alone["held_off"], alone)
exit_case = by_name["a_gate_by_direction_is_the_way_out"]
taken = dict(exit_case, name="made_owed_taken", expect={"handled_by": "interpret"}, owed={"fix": "B2: test", "now": {"handled_by": "exit"}})
took = interp_eval.evaluate([taken], quiet=True, save="line_patterns_648")
check("an intercept that takes an owed line is counted as taking a line not its own", took["intercept_took_wrongly"] == 1, took)
walk = by_name["a_walk_over_before_an_order_is_no_journey"]
changed = dict(walk, name="held_off_but_changed", expect={"kinds": ["buy"], "not_by": ["move_to_present"]})
check("a repair named as one that must not change the line, and changing it, is wrong, though what ran is right",
      interp_eval.evaluate([changed], quiet=True, save="line_patterns_648")["wrong"] == ["held_off_but_changed"])
held_off = dict(road, name="held_off_but_taken", expect={"not_by": ["interpret"]})
check("a rule named as one that must not take the line, and taking it, is wrong",
      interp_eval.evaluate([held_off], quiet=True, save="line_patterns_648")["wrong"] == ["held_off_but_taken"])

shutil.rmtree("saves/line_patterns_648", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
